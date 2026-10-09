"""WebSocket: parent actions behind the PIN (step 7)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .ws_helpers import chore, err, ok, unlock

pytestmark = pytest.mark.freeze_time("2026-10-12 08:00:00+00:00")  # Mon 10:00 Oslo
OSLO = ZoneInfo("Europe/Oslo")
SCREEN, MONEY = "1", "2"


async def _setup(ws):
    token = await unlock(ws)
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada", max={SCREEN: 120}))["id"]
    await ok(ws, "admin/chore/save", token=token, **chore([ada], weekdays=[]))  # 30 min / 10 kr
    state = await ok(ws, "get_state")
    return token, ada, state["board"][str(ada)]["chores"][0]


async def _balance(ws, ada, cur=SCREEN):
    return (await ok(ws, "get_state"))["board"][str(ada)]["balances"][cur]


async def _midnight(hass, freezer, day):
    freezer.move_to(datetime(2026, 10, day, 0, 0, 0, tzinfo=OSLO))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_reject_counts_as_missed_and_is_audited(ws):
    """AC-7.4, AC-7.7."""
    token, ada, dishes = await _setup(ws)
    await ok(ws, "set_done", instance_id=dishes["id"], done=True)
    assert (await _balance(ws, ada))["total"] == 30
    res = await ok(
        ws, "parent/set_status", token=token, instance_id=dishes["id"], status="rejected"
    )
    assert res["instance"]["status"] == "rejected"
    bal = await _balance(ws, ada)
    assert (bal["earned"], bal["lost"], bal["total"]) == (0, 30, 0)
    entries = (await ok(ws, "parent/audit", token=token, limit=1))["entries"]
    assert entries[0]["action"] == "set_status" and '"rejected"' in entries[0]["after"]


async def test_excused_and_refusals(ws):
    """AC-7.5, D19."""
    token, ada, dishes = await _setup(ws)
    await ok(ws, "parent/set_status", token=token, instance_id=dishes["id"], status="excused")
    assert (await _balance(ws, ada))["total"] == 0
    code = await err(
        ws, "parent/set_status", token=token, instance_id=dishes["id"], status="rejected"
    )
    assert code == "not_done"
    code = await err(
        ws, "parent/set_status", token=token, instance_id=dishes["id"], status="missed"
    )
    assert code == "not_allowed"  # not before midnight
    assert await err(
        ws, "parent/set_status", instance_id=dishes["id"], status="done", token="x"
    ) == ("invalid_token")
    assert await err(ws, "parent/set_status", token=token, instance_id=999, status="done") == (
        "not_found"
    )


async def test_parent_fixes_yesterday(hass, ws, freezer):
    """D8: parent can mark a past day done; kid can't."""
    token, ada, dishes = await _setup(ws)
    await _midnight(hass, freezer, 13)
    assert (await _balance(ws, ada))["lost"] == 30
    assert await err(ws, "set_done", instance_id=dishes["id"], done=True) == "not_today"
    token = await unlock(ws)  # the fake clock moved past the session timeout
    await ok(ws, "parent/set_status", token=token, instance_id=dishes["id"], status="done")
    bal = await _balance(ws, ada)
    assert (bal["earned"], bal["lost"]) == (30, 0)


async def test_adjust_with_note(ws):
    """AC-7.6."""
    token, ada, _ = await _setup(ws)
    kw = {"token": token, "kid_id": ada, "currency_id": 1}
    await ok(ws, "parent/adjust", **kw, amount=15, note="Hjalp bestemor")
    assert (await _balance(ws, ada))["total"] == 15
    await ok(ws, "parent/adjust", **kw, amount=-40, note="Krangel")
    assert (await _balance(ws, ada))["total"] == 0  # never below 0
    assert await err(ws, "parent/adjust", **kw, amount=5, note="  ") == "invalid_format"
    assert await err(ws, "parent/adjust", **kw, amount=0, note="x") == "invalid_format"
    assert await err(ws, "parent/adjust", **{**kw, "kid_id": 99}, amount=5, note="x") == "not_found"
    assert (
        await err(ws, "parent/adjust", **{**kw, "currency_id": 99}, amount=5, note="x")
        == "not_found"
    )
    payouts = await ok(ws, "parent/payouts", token=token)
    assert [a["note"] for a in payouts["adjustments"]] == ["Hjalp bestemor", "Krangel"]


async def test_payout_tick_after_payout_and_undo(hass, ws, freezer):
    """AC-9.1, D11: amount stored at tick time; later earnings shown as after_payout."""
    token, ada, dishes = await _setup(ws)
    await ok(ws, "set_done", instance_id=dishes["id"], done=True)

    def item(data, cur):
        return next(i for i in data["items"] if i["kid_id"] == ada and i["currency_id"] == int(cur))

    data = await ok(ws, "parent/payouts", token=token)
    screen = item(data, SCREEN)
    assert screen["amount_due"] == 30 and screen["paid"] is None
    assert screen["payout_day"] == "2026-10-16" and not screen["is_payout_day"]

    res = await ok(ws, "parent/payout", token=token, kid_id=ada, currency_id=1, paid=True)
    assert res == {"amount": 30}
    await ok(ws, "parent/adjust", token=token, kid_id=ada, currency_id=1, amount=10, note="ekstra")
    screen = item(await ok(ws, "parent/payouts", token=token), SCREEN)
    assert screen["paid"]["amount"] == 30 and screen["after_payout"] == 10

    await ok(ws, "parent/payout", token=token, kid_id=ada, currency_id=1, paid=False)
    assert item(await ok(ws, "parent/payouts", token=token), SCREEN)["paid"] is None
    assert await err(ws, "parent/payout", token=token, kid_id=99, currency_id=1, paid=True) == (
        "not_found"
    )


async def test_payout_day_flag_and_late_payout(hass, ws, freezer):
    """Friday is screen-time payout day; last week can still be paid after auto-close."""
    token, ada, dishes = await _setup(ws)
    await ok(ws, "set_done", instance_id=dishes["id"], done=True)
    freezer.move_to(datetime(2026, 10, 16, 9, tzinfo=OSLO))  # Friday
    token = await unlock(ws)
    data = await ok(ws, "parent/payouts", token=token)
    flags = {i["currency_id"]: i["is_payout_day"] for i in data["items"]}
    assert flags == {1: True, 2: False}

    await _midnight(hass, freezer, 19)  # next Monday: last week auto-closed
    token = await unlock(ws)
    last = await ok(ws, "parent/payouts", token=token, week="2026-10-12")
    assert last["week_status"] == "closed"
    res = await ok(
        ws, "parent/payout", token=token, kid_id=ada, currency_id=1, paid=True, week="2026-10-12"
    )
    assert res["amount"] == 0  # 30 earned Monday, Tue-Sun missed: clamped at 0
    assert (await ok(ws, "parent/payouts", token=token, week="2026-10-12"))["items"][0]["paid"]
    # The new week is open, so adjustments go there.
    await ok(ws, "parent/adjust", token=token, kid_id=ada, currency_id=1, amount=1, note="x")


async def test_close_week_freezes_and_reopen(hass, ws, freezer):
    """D1, D31: early close blocks taps and midnight losses; reopen undoes it."""
    token, ada, dishes = await _setup(ws)
    await ok(ws, "parent/close_week", token=token)
    assert (await ok(ws, "get_state"))["week_status"] == "closed"
    assert await err(ws, "parent/close_week", token=token) == "week_closed"
    assert await err(ws, "set_done", instance_id=dishes["id"], done=True) == "week_closed"
    assert (
        await err(ws, "parent/set_status", token=token, instance_id=dishes["id"], status="done")
        == "week_closed"
    )
    kw = {"token": token, "kid_id": ada, "currency_id": 1, "amount": 5, "note": "x"}
    assert await err(ws, "parent/adjust", **kw) == "week_closed"

    await _midnight(hass, freezer, 13)
    state = await ok(ws, "get_state")
    assert state["board"][str(ada)]["chores"] == []  # no rows in a frozen week
    assert state["board"][str(ada)]["balances"][SCREEN]["lost"] == 0  # Monday not missed

    token = await unlock(ws)
    await ok(ws, "parent/reopen_week", token=token)
    assert len((await ok(ws, "get_state"))["board"][str(ada)]["chores"]) == 1
    assert await err(ws, "parent/reopen_week", token=token) == "not_allowed"


async def test_auto_close_audit_and_limit(hass, ws, freezer):
    token, _, _ = await _setup(ws)
    entries = (await ok(ws, "parent/audit", token=token))["entries"]
    assert [e["action"] for e in entries] == ["chore_save", "kid_save"]
    assert await err(ws, "parent/audit", token=token, limit=0) == "invalid_format"
