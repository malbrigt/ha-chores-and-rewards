"""WebSocket: board state, kid taps, week grid, live updates (step 6)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .ws_helpers import call, chore, err, kid_board, midnight, ok, unlock

pytestmark = pytest.mark.freeze_time("2026-10-12 08:00:00+00:00")  # Mon 10:00 Oslo
OSLO = ZoneInfo("Europe/Oslo")
MON = date(2026, 10, 12)
TUE = date(2026, 10, 13)
SCREEN, MONEY = "1", "2"


async def _family(ws, screen_max=60):
    """Ada with a morning + afternoon expected chore and a daily bonus chore."""
    token = await unlock(ws)
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada", max={SCREEN: screen_max}))["id"]
    await ok(ws, "admin/chore/save", token=token, **chore([ada]))  # afternoon 30 min / 10 kr
    await ok(
        ws,
        "admin/chore/save",
        token=token,
        **chore([ada], name="Re opp sengen", slot="morning", values={SCREEN: 10}),
    )
    await ok(
        ws,
        "admin/chore/save",
        token=token,
        **chore(
            [ada],
            name="Vaske vinduer",
            chore_type="bonus",
            slot="anytime",
            weekdays=[],
            values={MONEY: 50},
        ),
    )
    return ada


async def _board(ws, **kw):
    return await ok(ws, "get_state", **kw)


async def test_get_state_board(ws):
    """AC-8.1: expected chores by slot, bonus apart; AC-8.2 balance data."""
    ada = await _family(ws)
    state = await _board(ws)
    assert (state["today"], state["week"], state["week_status"]) == (
        "2026-10-12",
        "2026-10-12",
        "open",
    )
    assert [k["name"] for k in state["kids"]] == ["Ada"]
    kid = state["board"][str(ada)]
    assert [(c["name"], c["slot"]) for c in kid["chores"]] == [
        ("Re opp sengen", "morning"),
        ("Oppvask", "afternoon"),
    ]
    assert [b["name"] for b in kid["bonus"]] == ["Vaske vinduer"]
    assert kid["balances"][SCREEN] == {
        "earned": 0,
        "lost": 0,
        "refilled": 0,
        "adjustments": 0,
        "cap": 60,
        "total": 0,
    }
    # Pot: 5 × 10 kr dishes + 7 × 50 kr windows.
    assert kid["balances"][MONEY]["cap"] == 5 * 10 + 7 * 50


async def test_tap_done_undo_and_live_update(ws):
    """AC-6.1, AC-6.2, AC-5.2."""
    ada = await _family(ws)
    await ws.send_json_auto_id({"type": "chores_and_rewards/subscribe"})
    sub = await ws.receive_json()
    assert sub["success"]

    dishes = (await _board(ws))["board"][str(ada)]["chores"][1]
    await ws.send_json_auto_id(
        {"type": "chores_and_rewards/set_done", "instance_id": dishes["id"], "done": True}
    )
    # The pushed event and the command result may arrive in either order.
    msgs = [await ws.receive_json(), await ws.receive_json()]
    result = next(m for m in msgs if m["type"] == "result")
    event = next(m for m in msgs if m["type"] == "event")
    assert result["result"]["instance"]["status"] == "done"
    assert event["id"] == sub["id"] and event["event"] == {"event": "updated"}

    bal = (await _board(ws))["board"][str(ada)]["balances"]
    assert bal[SCREEN]["total"] == 30 and bal[MONEY]["total"] == 10

    await ws.send_json_auto_id(
        {"type": "chores_and_rewards/set_done", "instance_id": dishes["id"], "done": False}
    )
    assert {(await ws.receive_json())["type"] for _ in range(2)} == {"result", "event"}
    assert (await _board(ws))["board"][str(ada)]["balances"][SCREEN]["total"] == 0


async def test_bonus_earns_and_cap_applies(ws):
    """AC-4.1: screen time stops at the kid's max."""
    ada = await _family(ws, screen_max=35)
    kid = (await _board(ws))["board"][str(ada)]
    for inst in [*kid["chores"], *kid["bonus"]]:
        await ok(ws, "set_done", instance_id=inst["id"], done=True)
    bal = (await _board(ws))["board"][str(ada)]["balances"]
    assert bal[SCREEN]["earned"] == 40 and bal[SCREEN]["total"] == 35
    assert bal[MONEY]["total"] == 60


async def test_midnight_loss_then_kid_fixes_yesterday(hass, ws, freezer):
    """AC-3.2, AC-5.3; D8: a kid can fix a forgotten tick later in the week, audited as late."""
    ada = await _family(ws)
    kid = (await _board(ws))["board"][str(ada)]
    bed, dishes = kid["chores"]
    await ok(ws, "set_done", instance_id=dishes["id"], done=True)

    freezer.move_to(datetime(2026, 10, 13, 18, 0, 0, tzinfo=OSLO))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = await _board(ws)
    assert state["today"] == "2026-10-13"
    bal = state["board"][str(ada)]["balances"]
    assert (bal[SCREEN]["earned"], bal[SCREEN]["lost"], bal[SCREEN]["total"]) == (30, 10, 20)
    assert bal[MONEY]["lost"] == 0  # allowance can't be lost (AC-3.3)

    # Forgotten bed on Monday: ticked on Tuesday → done, flagged late.
    res = await ok(ws, "set_done", instance_id=bed["id"], done=True)
    assert res["instance"]["status"] == "done" and res["instance"]["late"]
    # Unticking a past chore makes it missed again, not pending.
    res = await ok(ws, "set_done", instance_id=dishes["id"], done=False)
    assert res["instance"]["status"] == "missed"
    bal = (await _board(ws))["board"][str(ada)]["balances"][SCREEN]
    assert (bal["earned"], bal["lost"]) == (10, 30)

    store = ws.entry.runtime_data
    log = await store.async_read(lambda r: r.list_audit(actions=["check", "uncheck"]))
    taps = [(e["action"], e["day"], e["late"], e["kid_id"]) for e in log[:3]]
    assert taps == [
        ("uncheck", "2026-10-12", True, ada),
        ("check", "2026-10-12", True, ada),
        ("check", "2026-10-12", False, ada),
    ]
    assert '"chore": "Re opp sengen"' in log[1]["after"]


async def test_kid_cannot_touch_last_week_or_parent_decisions(hass, ws, freezer):
    ada = await _family(ws)
    dishes = (await _board(ws))["board"][str(ada)]["chores"][1]
    token = await unlock(ws)
    await ok(ws, "parent/set_status", token=token, instance_id=dishes["id"], status="excused")
    assert await err(ws, "set_done", instance_id=dishes["id"], done=True) == "not_allowed"
    freezer.move_to(datetime(2026, 10, 19, 9, 0, 0, tzinfo=OSLO))  # next Monday
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert await err(ws, "set_done", instance_id=dishes["id"], done=True) == "week_closed"


async def test_get_week_grid(hass, ws, freezer):
    """AC-8.3."""
    ada = await _family(ws)
    dishes = (await _board(ws))["board"][str(ada)]["chores"][1]
    await ok(ws, "set_done", instance_id=dishes["id"], done=True)
    freezer.move_to(datetime(2026, 10, 13, 0, 0, 0, tzinfo=OSLO))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    week = await ok(ws, "get_week", kid_id=ada)
    assert week["week"] == "2026-10-12" and len(week["days"]) == 7
    rows = {r["name"]: r for r in week["rows"]}
    assert list(rows) == ["Re opp sengen", "Oppvask", "Vaske vinduer"]
    assert rows["Oppvask"]["cells"] == {"2026-10-12": "done", "2026-10-13": "pending"}
    assert rows["Oppvask"]["ids"]["2026-10-12"] == dishes["id"]
    assert rows["Re opp sengen"]["cells"]["2026-10-12"] == "missed"
    assert rows["Vaske vinduer"]["cells"]["2026-10-12"] == "pending"  # never missed
    assert week["balances"][SCREEN]["total"] == 20

    prev = await ok(ws, "get_week", kid_id=ada, week="2026-10-07")
    assert prev["week"] == "2026-10-05" and prev["rows"] == [] and prev["week_status"] is None
    assert await err(ws, "get_week", kid_id=999) == "not_found"


async def test_get_state_other_day(ws):
    ada = await _family(ws)
    state = await _board(ws, day="2026-10-11")
    assert state["day"] == "2026-10-11" and state["week"] == "2026-10-05"
    assert state["board"][str(ada)]["chores"] == []


async def test_safety_net_rollover_on_read(ws):
    """If the midnight job never ran, a read catches up."""
    ada = await _family(ws)
    store = ws.entry.runtime_data
    await store.async_write(lambda r: r.set_last_finalized(MON - timedelta(days=3)))
    await _board(ws)
    assert await store.async_read(lambda r: r.last_finalized()) == MON - timedelta(days=1)
    assert ada


async def test_closed_week_refuses_taps(ws):
    ada = await _family(ws)
    dishes = (await _board(ws))["board"][str(ada)]["chores"][1]
    store = ws.entry.runtime_data
    await store.async_write(lambda r: r.close_week(MON, by="test"))
    assert await err(ws, "set_done", instance_id=dishes["id"], done=True) == "week_closed"
    assert await err(ws, "set_done", instance_id=9999, done=True) == "not_found"


async def test_subscribe_works_for_normal_user(
    hass, hass_ws_client, setup_entry, hass_read_only_access_token
):
    """D14."""
    await setup_entry()
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json_auto_id({"type": "chores_and_rewards/subscribe"})
    assert (await client.receive_json())["success"]


async def test_instances_carry_status_at(ws):
    """D35: the panel needs status_at to decide on the uncheck confirmation."""
    ada = await _family(ws)
    inst = (await _board(ws))["board"][str(ada)]["chores"][0]
    assert inst["status_at"] is None
    res = await ok(ws, "set_done", instance_id=inst["id"], done=True)
    assert res["instance"]["status_at"].startswith("2026-10-12T08:00")


async def test_get_state_future_day_preview(ws):
    """D37: a future day shows the schedule as an unsaved preview."""
    ada = await _family(ws)
    state = await _board(ws, day="2026-10-14")  # Wednesday
    assert state["is_preview"]
    kid = state["board"][str(ada)]
    assert [c["name"] for c in kid["chores"]] == ["Re opp sengen", "Oppvask"]
    assert all(c["id"] is None and c["status"] == "pending" for c in kid["chores"])
    assert not (await _board(ws))["is_preview"]
    store = ws.entry.runtime_data
    assert await store.async_read(lambda r: r.list_instances(day=date(2026, 10, 14))) == []


async def test_extra_pays_or_refills_a_loss(hass, ws, freezer):
    """AC-6.6, AC-6.7, D49: an extra earns one currency; screen time only to win back a loss."""
    ada = await _family(ws, screen_max=60)
    token = await unlock(ws)
    extra = chore(
        [ada],
        name="Trash",
        chore_type="bonus",
        slot="anytime",
        weekdays=[],
        values={SCREEN: 15, MONEY: 1},
    )
    await ok(ws, "admin/chore/save", token=token, **extra)
    trash = next(i for i in (await kid_board(ws, ada))["bonus"] if i["name"] == "Trash")

    # Nothing lost yet: screen time isn't on offer, the tick pays allowance.
    assert await err(ws, "set_done", instance_id=trash["id"], done=True, currency_id=1) == (
        "nothing_lost"
    )
    res = await ok(ws, "set_done", instance_id=trash["id"], done=True)
    assert res["instance"]["currency_id"] == 2
    res = await ok(ws, "set_done", instance_id=trash["id"], done=False)
    assert res["instance"]["currency_id"] is None

    # Monday's chores are missed at midnight (−40 min). On Tuesday the trash wins 15 back.
    await midnight(hass, freezer, 13, 18)
    trash = next(i for i in (await kid_board(ws, ada))["bonus"] if i["name"] == "Trash")
    res = await ok(ws, "set_done", instance_id=trash["id"], done=True, currency_id=1)
    assert res["instance"]["currency_id"] == 1
    bal = (await kid_board(ws, ada))["balances"]
    assert (bal[SCREEN]["lost"], bal[SCREEN]["refilled"]) == (40, 15)
    assert bal[MONEY]["total"] == 0  # the trash paid screen time, not allowance

    log = await ws.entry.runtime_data.async_read(lambda r: r.list_audit(actions=["check"]))
    assert '"currency_id": 1' in log[0]["after"]


async def test_once_a_day_extra_goes_to_the_first_kid(ws):
    """AC-6.8, AC-5.7, D51: one kid takes a once-a-day extra; others see who, and can't."""
    token = await unlock(ws)
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada"))["id"]
    bo = (await ok(ws, "admin/kid/save", token=token, name="Bo"))["id"]
    extra = {"chore_type": "bonus", "slot": "anytime", "weekdays": [], "values": {MONEY: 10}}
    dust = chore([ada, bo], name="Dust", once_a_day=True, **extra)
    await ok(ws, "admin/chore/save", token=token, **dust)
    await ok(ws, "admin/chore/save", token=token, **chore([ada, bo], name="Trash", **extra))
    assert (
        await err(ws, "admin/chore/save", token=token, **chore([ada], name="Bed", once_a_day=True))
        == "not_allowed"
    )  # an expected chore is every kid's own

    async def row(kid, name):
        return next(i for i in (await kid_board(ws, kid))["bonus"] if i["name"] == name)

    await ok(ws, "set_done", instance_id=(await row(ada, "Dust"))["id"], done=True)
    bo_dust = await row(bo, "Dust")
    assert (bo_dust["taken_by"], (await row(ada, "Dust"))["taken_by"]) == (ada, None)
    assert await err(ws, "set_done", instance_id=bo_dust["id"], done=True) == "taken"
    assert (
        await err(ws, "parent/set_status", token=token, instance_id=bo_dust["id"], status="done")
        == "taken"
    )

    # The trash (setting off) is open to every kid.
    await ok(ws, "set_done", instance_id=(await row(ada, "Trash"))["id"], done=True)
    await ok(ws, "set_done", instance_id=(await row(bo, "Trash"))["id"], done=True)

    # A parent reject frees it again; so does an untick.
    ada_dust = await row(ada, "Dust")
    await ok(ws, "parent/set_status", token=token, instance_id=ada_dust["id"], status="rejected")
    assert (await row(bo, "Dust"))["taken_by"] is None
    await ok(ws, "set_done", instance_id=bo_dust["id"], done=True)
    assert (await row(ada, "Dust"))["taken_by"] == bo
    await ok(ws, "set_done", instance_id=bo_dust["id"], done=False)
    assert (await row(ada, "Dust"))["taken_by"] is None


async def _homework(ws, **kw):
    """Ada with Homework (Mon–Fri, 20 min) that can be ticked ahead (D52)."""
    token = await unlock(ws)
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada", max={SCREEN: 300}))["id"]
    hw = chore([ada], name="Homework", values={SCREEN: 20}, can_tick_ahead=True, **kw)
    hw_id = (await ok(ws, "admin/chore/save", token=token, **hw))["id"]
    return token, ada, hw, hw_id


async def test_tick_ahead_creates_the_row_and_counts_in_its_own_week(ws):
    """AC-6.9, D52: homework done Monday can be ticked for the rest of this and next week."""
    _, ada, _, hw = await _homework(ws)

    async def ahead(day):
        return await call(ws, "tick_ahead", kid_id=ada, chore_id=hw, day=day)

    tue = await ok(ws, "tick_ahead", kid_id=ada, chore_id=hw, day="2026-10-13")
    assert (tue["instance"]["day"], tue["instance"]["status"]) == ("2026-10-13", "done")
    assert (await kid_board(ws, ada))["balances"][SCREEN]["earned"] == 20  # counts now
    nxt = await ok(ws, "tick_ahead", kid_id=ada, chore_id=hw, day="2026-10-23")  # next Friday
    assert (await kid_board(ws, ada))["balances"][SCREEN]["earned"] == 20  # not this week
    week = await ok(ws, "get_week", kid_id=ada, week="2026-10-19")
    assert week["balances"][SCREEN]["earned"] == 20
    assert week["week_status"] == "open"

    for day, code in [
        ("2026-10-12", "future_day"),  # today: a normal tap
        ("2026-10-26", "future_day"),  # past next week
        ("2026-10-17", "not_scheduled"),  # Saturday
    ]:
        assert (await ahead(day))["error"]["code"] == code, day

    # Untick goes back to pending (not missed); ticking ahead again reuses the row.
    res = await ok(ws, "set_done", instance_id=tue["instance"]["id"], done=False)
    assert res["instance"]["status"] == "pending"
    again = await ok(ws, "tick_ahead", kid_id=ada, chore_id=hw, day="2026-10-13")
    assert again["instance"]["id"] == tue["instance"]["id"]

    # The board for Wednesday and the week grid show unsaved previews to tick.
    wed = (await kid_board(ws, ada, day="2026-10-14"))["chores"]
    assert [(i["name"], i["id"], i["can_tick_ahead"]) for i in wed] == [("Homework", None, True)]
    grid = (await ok(ws, "get_week", kid_id=ada))["rows"][0]
    assert grid["can_tick_ahead"] and grid["ids"]["2026-10-14"] is None
    assert (grid["cells"]["2026-10-13"], grid["cells"]["2026-10-14"]) == ("done", "pending")
    assert nxt["instance"]["status"] == "done"


async def test_tick_ahead_refusals(ws):
    """AC-6.9, D52: only expected chores with the setting can be ticked ahead."""
    token, ada, _, _ = await _homework(ws)
    plain = (await ok(ws, "admin/chore/save", token=token, **chore([ada], name="Dishes")))["id"]
    err_ = await call(ws, "tick_ahead", kid_id=ada, chore_id=plain, day="2026-10-13")
    assert err_["error"]["code"] == "future_day"
    extra = chore([ada], name="Trash", chore_type="bonus", slot="anytime", can_tick_ahead=True)
    assert await err(ws, "admin/chore/save", token=token, **extra) == "not_allowed"


async def test_rows_ticked_ahead_follow_the_chore(ws):
    """D52: a day that hasn't come follows chore edits; the rollover keeps the tick."""
    token, ada, hw, hw_id = await _homework(ws)
    for day in ("2026-10-13", "2026-10-14", "2026-10-20"):
        await ok(ws, "tick_ahead", kid_id=ada, chore_id=hw_id, day=day)

    # Renamed: the future rows follow and stay done.
    await ok(ws, "admin/chore/save", token=token, chore_id=hw_id, **{**hw, "name": "Lekser"})
    week = await ok(ws, "get_week", kid_id=ada)
    assert [(r["name"], r["cells"].get("2026-10-14")) for r in week["rows"]] == [("Lekser", "done")]
    # Wednesday dropped from the schedule: that tick goes, the others stay.
    await ok(
        ws,
        "admin/chore/save",
        token=token,
        chore_id=hw_id,
        **{**hw, "name": "Lekser", "weekdays": [0, 1, 3, 4]},
    )
    cells = (await ok(ws, "get_week", kid_id=ada))["rows"][0]["cells"]
    assert ("2026-10-13" in cells, "2026-10-14" in cells) == (True, False)
    # Setting turned off: no more rows ahead.
    await ok(
        ws,
        "admin/chore/save",
        token=token,
        chore_id=hw_id,
        **{**hw, "name": "Lekser", "can_tick_ahead": False},
    )
    nxt = await ok(ws, "get_week", kid_id=ada, week="2026-10-19")
    assert nxt["rows"] == []
    log = await ws.entry.runtime_data.async_read(
        lambda r: r.list_audit(actions=["instance_delete"])
    )
    assert len(log) == 3  # Wednesday, Tuesday and next Tuesday, each audited (D46)


async def test_tick_ahead_survives_midnight(hass, ws, freezer):
    """D52: when the day comes the done row is kept, never marked missed."""
    _, ada, _, hw_id = await _homework(ws)
    await ok(ws, "tick_ahead", kid_id=ada, chore_id=hw_id, day="2026-10-13")
    await midnight(hass, freezer, 14)  # Monday and Tuesday are finalized
    cells = (await ok(ws, "get_week", kid_id=ada))["rows"][0]["cells"]
    assert (cells["2026-10-12"], cells["2026-10-13"]) == ("missed", "done")
