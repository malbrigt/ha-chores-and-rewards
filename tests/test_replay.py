"""D46: the full usage of the integration can be replayed from the audit log."""

import pytest

from .replay import replay, snapshot
from .ws_helpers import chore, err, kid_board, midnight, ok, unlock

pytestmark = pytest.mark.freeze_time("2026-10-12 08:00:00+00:00")  # Mon 10:00 Oslo


async def test_every_change_is_replayable_from_the_audit_log(hass, ws, freezer):
    # PIN usage (no state, but part of usage).
    await err(ws, "pin/unlock", pin="0000")
    token = await unlock(ws)

    # Admin: kids, currencies, chores, settings — create, edit, deactivate, delete.
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada", max={"1": 120}))["id"]
    bo = (await ok(ws, "admin/kid/save", token=token, name="Bo"))["id"]
    cato = (await ok(ws, "admin/kid/save", token=token, name="Cato"))["id"]
    cur = dict(
        name="Stjerner", unit="★", payout_weekday=6, can_be_lost=False, cap_mode="fixed", decimals=1
    )
    stars = (await ok(ws, "admin/currency/save", token=token, **cur, default_max=10))["id"]
    await ok(ws, "admin/currency/save", token=token, currency_id=stars, **cur, sort=3)
    dishes = (await ok(ws, "admin/chore/save", token=token, **chore([ada, bo])))["id"]
    bonus = dict(name="Vinduer", chore_type="bonus", slot="anytime", weekdays=[])
    windows = (
        await ok(
            ws,
            "admin/chore/save",
            token=token,
            **chore([ada, cato], **bonus, values={"1": 20, "2": 50}),
        )
    )["id"]
    bed = (await ok(ws, "admin/chore/save", token=token, **chore([cato], name="Seng")))["id"]
    # Edit: rename (resync pending), drop Bo (delete his pending row), add a star value.
    await ok(
        ws,
        "admin/chore/save",
        token=token,
        chore_id=dishes,
        **chore([ada], name="Oppvask!", values={"1": 30, "2": 10, str(stars): 1}),
    )
    await ok(ws, "admin/chore/delete", token=token, chore_id=bed)  # deletes Cato's pending
    await ok(ws, "admin/kid/save", token=token, kid_id=bo, name="Bo", active=False)
    await ok(ws, "admin/kid/save", token=token, kid_id=bo, name="Bo", active=True)
    await ok(ws, "admin/settings/save", token=token, settings={"idle_seconds": 90})

    # Kid taps and parent decisions.
    ada_rows = await kid_board(ws, ada)
    dish, win = ada_rows["chores"][0], ada_rows["bonus"][0]
    await ok(ws, "set_done", instance_id=dish["id"], done=True)
    await ok(ws, "set_done", instance_id=win["id"], done=True)
    await ok(ws, "set_done", instance_id=win["id"], done=False)
    await ok(ws, "parent/set_status", token=token, instance_id=dish["id"], status="rejected")
    await ok(ws, "parent/adjust", token=token, kid_id=ada, currency_id=1, amount=15, note="Bonus")
    await ok(ws, "parent/payout", token=token, kid_id=ada, currency_id=1, paid=True)
    await ok(ws, "parent/payout", token=token, kid_id=ada, currency_id=1, paid=False)
    await ok(ws, "parent/payout", token=token, kid_id=ada, currency_id=2, paid=True)
    await ok(ws, "pin/lock", token=token)

    # Midnight: missed + new day; a kid fixes yesterday (late).
    await midnight(hass, freezer, 13, hour=18)
    yesterday = await ok(ws, "get_state", day="2026-10-12")
    # Ada's dishes were rejected (−30 min), so the extra can win screen time back (D49).
    win = yesterday["board"][str(ada)]["bonus"][0]
    await ok(ws, "set_done", instance_id=win["id"], done=True, currency_id=1)
    token = await unlock(ws)
    await ok(ws, "parent/close_week", token=token)
    await ok(ws, "parent/reopen_week", token=token)
    await ok(ws, "admin/currency/delete", token=token, currency_id=stars)
    await ok(ws, "admin/kid/delete", token=token, kid_id=cato)
    await ok(ws, "admin/chore/delete", token=token, chore_id=windows)

    # HA "off" until next Tuesday: catch-up, auto-close, new week.
    await midnight(hass, freezer, 20, hour=7)

    store = ws.entry.runtime_data
    log = await store.async_read(lambda r: r.list_audit(100_000))
    actions = {e["action"] for e in log}
    for expected in (
        "db_created", "currency_save", "currency_delete", "kid_save", "kid_delete",
        "chore_save", "chore_delete", "settings_save", "week_open", "close_week",
        "reopen_week", "instance_create", "instance_update", "instance_delete", "check",
        "uncheck", "set_status", "auto_missed", "adjust", "payout", "payout_undo",
        "rollover", "pin_unlock", "pin_wrong_pin", "pin_lock",
    ):  # fmt: skip
        assert expected in actions, expected

    rebuilt = replay(log)
    actual = await store.async_read(snapshot)
    for key in actual:
        assert rebuilt[key] == actual[key], key
    assert actual["instances"] and actual["payouts"] and actual["adjustments"]
