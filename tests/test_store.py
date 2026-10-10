"""Store, midnight rollover, catch-up, auto week close, backup and diagnostics."""

from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.chores_and_rewards import backup, diagnostics
from custom_components.chores_and_rewards.const import EVENT_UPDATED
from custom_components.chores_and_rewards.logic import Chore, ChoreType, Slot, Status

OSLO = ZoneInfo("Europe/Oslo")
FRI = date(2026, 10, 9)
MON = date(2026, 10, 12)
TUE = date(2026, 10, 13)


def at(day: date, hour=10, minute=0, second=0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, second, tzinfo=OSLO)


async def _seed(store):
    """One kid with an every-day expected chore and a weekend bonus chore."""

    def seed(repo):
        kid = repo.add_kid("Ada")
        repo.add_chore(
            Chore(
                0,
                "Dishes",
                ChoreType.EXPECTED,
                frozenset({kid}),
                frozenset(),
                Slot.AFTERNOON,
                {1: 30},
            )
        )
        repo.add_chore(
            Chore(
                0,
                "Windows",
                ChoreType.BONUS,
                frozenset({kid}),
                frozenset({5, 6}),
                Slot.ANYTIME,
                {2: 50},
            )
        )
        return kid

    kid = await store.async_write(seed)
    await store.async_rollover()  # create today's rows for the new data
    return kid


async def _instances(store, **kw):
    return await store.async_read(lambda r: r.list_instances(**kw))


async def test_setup_creates_db_and_today(hass, setup_entry, freezer, tmp_path):
    freezer.move_to(at(MON))
    entry = await setup_entry()
    store = entry.runtime_data
    assert (tmp_path / "chores_and_rewards.db").exists()
    await _seed(store)
    rows = await _instances(store, day=MON)
    assert [(i.name, i.status) for i in rows] == [("Dishes", Status.PENDING)]
    assert await store.async_read(lambda r: r.last_finalized()) == date(2026, 10, 11)


async def test_midnight_marks_missed_and_creates_next_day(hass, setup_entry, freezer):
    """AC-5.3: undone expected → missed at midnight; next day's rows appear."""
    freezer.move_to(at(MON, 23, 59, 59))
    entry = await setup_entry()
    store = entry.runtime_data
    await _seed(store)
    events = []
    hass.bus.async_listen(EVENT_UPDATED, events.append)

    freezer.move_to(at(TUE, 0, 0, 0))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert [i.status for i in await _instances(store, day=MON)] == [Status.MISSED]
    assert [i.status for i in await _instances(store, day=TUE)] == [Status.PENDING]
    assert await store.async_read(lambda r: r.last_finalized()) == MON
    assert events


async def test_done_chore_survives_midnight(hass, setup_entry, freezer):
    freezer.move_to(at(MON))
    store = (await setup_entry()).runtime_data
    await _seed(store)
    inst = (await _instances(store, day=MON))[0]
    await store.async_write(lambda r: r.set_status(inst.id, Status.DONE, by="kid"))
    freezer.move_to(at(TUE, 0, 0, 0))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert (await _instances(store, day=MON))[0].status is Status.DONE


async def test_catch_up_three_days_across_monday(hass, setup_entry, freezer):
    """AC-6.3, AC-9.2: HA off Fri evening → Tue; every day processed once, week closed."""
    freezer.move_to(at(FRI, 18))
    entry = await setup_entry()
    store = entry.runtime_data
    await _seed(store)
    assert await hass.config_entries.async_unload(entry.entry_id)

    freezer.move_to(at(TUE, 7))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    store = entry.runtime_data

    rows = await _instances(store)
    by_day = {}
    for i in rows:
        by_day.setdefault(i.day, []).append((i.name, i.status))
    assert by_day[FRI] == [("Dishes", Status.MISSED)]
    # Sat/Sun were never seen live: created during catch-up, bonus stays pending (AC-5.4).
    assert sorted(by_day[date(2026, 10, 10)]) == [
        ("Dishes", Status.MISSED),
        ("Windows", Status.PENDING),
    ]
    assert by_day[MON] == [("Dishes", Status.MISSED)]
    assert by_day[TUE] == [("Dishes", Status.PENDING)]
    weeks = {w["start"]: w["status"] for w in await store.async_read(lambda r: r.list_weeks())}
    assert weeks == {"2026-10-05": "closed", "2026-10-12": "open"}
    audit = await store.async_read(lambda r: r.list_audit(actions=["close_week"]))
    assert [(a["day"], a["note"]) for a in audit] == [("2026-10-05", "auto")]
    missed = await store.async_read(lambda r: r.list_audit(actions=["auto_missed"]))
    assert sorted(a["day"] for a in missed) == [
        "2026-10-09",
        "2026-10-10",
        "2026-10-11",
        "2026-10-12",
    ]
    marker = await store.async_read(lambda r: r.list_audit(actions=["rollover"]))
    assert '"last_finalized": "2026-10-12"' in marker[0]["after"]


async def test_restart_same_day_is_idempotent(hass, setup_entry, freezer):
    freezer.move_to(at(MON))
    entry = await setup_entry()
    store = entry.runtime_data
    await _seed(store)
    before = await _instances(store)
    for _ in range(2):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    store = entry.runtime_data
    assert await _instances(store) == before


async def test_unload_stops_midnight_job(hass, setup_entry, freezer):
    freezer.move_to(at(MON))
    entry = await setup_entry()
    await _seed(entry.runtime_data)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    with patch("custom_components.chores_and_rewards.store.ChoresStore.async_rollover") as rollover:
        freezer.move_to(at(TUE, 0, 0, 0))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    rollover.assert_not_called()


async def test_dst_change_night(hass, setup_entry, freezer):
    """Clocks go back at 03:00 on 25 Oct in Oslo; midnight rollover is unaffected."""
    sat, sun = date(2026, 10, 24), date(2026, 10, 25)
    freezer.move_to(at(sat, 23))
    store = (await setup_entry()).runtime_data
    await _seed(store)
    freezer.move_to(at(sun, 0, 0, 0))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    freezer.move_to(at(sun, 3, 30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert await store.async_read(lambda r: r.last_finalized()) == sat


async def test_backup_checkpoints(hass, setup_entry, freezer):
    freezer.move_to(at(MON))
    entry = await setup_entry()
    with patch.object(entry.runtime_data.db, "checkpoint") as checkpoint:
        await backup.async_pre_backup(hass)
        await backup.async_post_backup(hass)
    checkpoint.assert_called_once()


async def test_diagnostics_redacts_pin(hass, setup_entry, freezer):
    freezer.move_to(at(MON))
    entry = await setup_entry()
    await _seed(entry.runtime_data)
    diag = await diagnostics.async_get_config_entry_diagnostics(hass, entry)
    assert diag["entry"]["pin_hash"] == "**REDACTED**"
    assert diag["db"]["counts"]["kids"] == 1
    assert diag["db"]["open_weeks"] == ["2026-10-12"]
    assert diag["db"]["schema_version"] == 1
