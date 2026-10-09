"""WebSocket: PIN sessions and admin CRUD (docs/ws-api.md)."""

from datetime import date

import pytest

from custom_components.chores_and_rewards.logic import Status

from .conftest import TEST_PIN

P = "chores_and_rewards/"
MON = date(2026, 10, 12)  # Monday


# Frozen from the start, so HA's test access token is issued in "fake now" too.
pytestmark = pytest.mark.freeze_time("2026-10-12 08:00:00+00:00")  # Mon 10:00 Oslo


@pytest.fixture
async def ws(freezer, hass, hass_ws_client, setup_entry):
    entry = await setup_entry()
    client = await hass_ws_client(hass)
    client.entry = entry
    return client


async def call(client, type_, **data):
    await client.send_json_auto_id({"type": P + type_, **data})
    return await client.receive_json()


async def ok(client, type_, **data):
    msg = await call(client, type_, **data)
    assert msg["success"], msg
    return msg["result"]


async def err(client, type_, **data):
    msg = await call(client, type_, **data)
    assert not msg["success"], msg
    return msg["error"]["code"]


async def unlock(client):
    return (await ok(client, "pin/unlock", pin=TEST_PIN))["token"]


# --- PIN ----------------------------------------------------------------------


async def test_unlock_status_lock(ws):
    """AC-7.1."""
    token = await unlock(ws)
    assert (await ok(ws, "pin/status", token=token))["valid"]
    await ok(ws, "pin/lock", token=token)
    assert not (await ok(ws, "pin/status", token=token))["valid"]


async def test_wrong_pin_and_lockout(ws):
    """AC-7.2."""
    for _ in range(4):
        assert await err(ws, "pin/unlock", pin="0000") == "wrong_pin"
    assert await err(ws, "pin/unlock", pin="0000") == "locked_out"
    assert await err(ws, "pin/unlock", pin=TEST_PIN) == "locked_out"


async def test_parent_commands_need_token(ws):
    """AC-7.3."""
    assert await err(ws, "admin/list", token="bogus") == "invalid_token"
    assert await err(ws, "admin/list") == "invalid_format"  # token is required by schema


async def test_non_admin_refused(hass, hass_ws_client, setup_entry, hass_read_only_access_token):
    await setup_entry()
    client = await hass_ws_client(hass, hass_read_only_access_token)
    assert await err(client, "pin/unlock", pin=TEST_PIN) == "unauthorized"


async def test_not_loaded(hass, hass_ws_client, setup_entry):
    entry = await setup_entry()
    await hass.config_entries.async_unload(entry.entry_id)
    client = await hass_ws_client(hass)
    assert await err(client, "pin/unlock", pin=TEST_PIN) == "not_loaded"


# --- CRUD ---------------------------------------------------------------------


async def test_admin_list_seeded(ws):
    token = await unlock(ws)
    data = await ok(ws, "admin/list", token=token)
    assert [c["name"] for c in data["currencies"]] == ["Skjermtid", "Ukepenger"]
    assert data["kids"] == [] and data["chores"] == []
    assert data["settings"]["pin_timeout_seconds"] == 300


async def test_kid_crud_with_max(ws):
    token = await unlock(ws)
    kid = (await ok(ws, "admin/kid/save", token=token, name=" Ada ", max={"1": 120}))["id"]
    await ok(
        ws, "admin/kid/save", token=token, kid_id=kid, name="Ada", sort=2, max={"1": None, "2": 50}
    )
    kids = (await ok(ws, "admin/list", token=token))["kids"]
    assert kids == [{"id": kid, "name": "Ada", "sort": 2, "active": True, "max": {"2": 50}}]
    assert await err(ws, "admin/kid/save", token=token, kid_id=999, name="X") == "not_found"
    assert await err(ws, "admin/kid/save", token=token, name="  ") == "invalid_format"
    await ok(ws, "admin/kid/delete", token=token, kid_id=kid)
    assert (await ok(ws, "admin/list", token=token))["kids"] == []
    assert await err(ws, "admin/kid/delete", token=token, kid_id=kid) == "not_found"


async def test_currency_crud(ws):
    token = await unlock(ws)
    cid = (
        await ok(
            ws,
            "admin/currency/save",
            token=token,
            name="Stjerner",
            unit="★",
            payout_weekday=6,
            can_be_lost=False,
            cap_mode="fixed",
            default_max=10,
        )
    )["id"]
    await ok(
        ws,
        "admin/currency/save",
        token=token,
        currency_id=cid,
        name="Stjerner",
        unit="★",
        payout_weekday=6,
        can_be_lost=True,
        cap_mode="pot",
        active=False,
    )
    cur = next(c for c in (await ok(ws, "admin/list", token=token))["currencies"] if c["id"] == cid)
    assert cur["cap_mode"] == "pot" and cur["can_be_lost"] and not cur["active"]
    assert cur["default_max"] is None
    bad = dict(name="X", unit="x", payout_weekday=7, can_be_lost=False, cap_mode="fixed")
    assert await err(ws, "admin/currency/save", token=token, **bad) == "invalid_format"
    await ok(ws, "admin/currency/delete", token=token, currency_id=cid)
    assert len((await ok(ws, "admin/list", token=token))["currencies"]) == 2
    assert await err(ws, "admin/currency/delete", token=token, currency_id=cid) == "not_found"
    assert (
        await err(
            ws, "admin/currency/save", token=token, currency_id=cid, **{**bad, "payout_weekday": 1}
        )
        == "not_found"
    )


def chore(kid_ids, **kw):
    base = {
        "name": "Oppvask",
        "chore_type": "expected",
        "slot": "afternoon",
        "weekdays": [0, 1, 2, 3, 4],
        "kid_ids": kid_ids,
        "values": {"1": 30, "2": 10},
    }
    return {**base, **kw}


async def _today(client):
    store = client.entry.runtime_data
    return await store.async_read(lambda r: r.list_instances(day=MON))


async def test_chore_save_creates_todays_rows_and_warns(ws):
    """AC-5.5 warning; D7 today's rows follow edits."""
    token = await unlock(ws)
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada"))["id"]
    bo = (await ok(ws, "admin/kid/save", token=token, name="Bo"))["id"]
    res = await ok(ws, "admin/chore/save", token=token, **chore([ada, bo]))
    assert res["warnings"] == []
    assert {i.kid_id for i in await _today(ws)} == {ada, bo}

    # Edit: rename, drop Bo, add Sunday (after both payout days) → warnings.
    res = await ok(
        ws,
        "admin/chore/save",
        token=token,
        chore_id=res["id"],
        **chore([ada], name="Oppvask!", weekdays=[0, 6]),
    )
    assert res["warnings"] == [1, 2]
    rows = await _today(ws)
    assert [(i.kid_id, i.name) for i in rows] == [(ada, "Oppvask!")]


async def test_chore_edit_keeps_done_rows(ws):
    token = await unlock(ws)
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada"))["id"]
    cid = (await ok(ws, "admin/chore/save", token=token, **chore([ada])))["id"]
    store = ws.entry.runtime_data
    inst = (await _today(ws))[0]
    await store.async_write(lambda r: r.set_status(inst.id, Status.DONE, by="kid"))
    await ok(
        ws, "admin/chore/save", token=token, chore_id=cid, **chore([ada], name="New", active=False)
    )
    rows = await _today(ws)
    assert [(i.name, i.status) for i in rows] == [("Oppvask", Status.DONE)]
    await ok(ws, "admin/chore/delete", token=token, chore_id=cid)
    assert len(await _today(ws)) == 1  # history kept
    assert await err(ws, "admin/chore/delete", token=token, chore_id=cid) == "not_found"


async def test_chore_save_validates_refs(ws):
    token = await unlock(ws)
    assert await err(ws, "admin/chore/save", token=token, **chore([999])) == "not_found"
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada"))["id"]
    bad_cur = chore([ada], values={"99": 5})
    assert await err(ws, "admin/chore/save", token=token, **bad_cur) == "not_found"
    bad_slot = chore([ada], slot="night")
    assert await err(ws, "admin/chore/save", token=token, **bad_slot) == "invalid_format"
    assert (
        await err(ws, "admin/chore/save", token=token, chore_id=42, **chore([ada])) == "not_found"
    )


async def test_kid_deactivate_drops_pending_today(ws):
    token = await unlock(ws)
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada"))["id"]
    await ok(ws, "admin/chore/save", token=token, **chore([ada]))
    assert len(await _today(ws)) == 1
    await ok(ws, "admin/kid/save", token=token, kid_id=ada, name="Ada", active=False)
    assert await _today(ws) == []
    await ok(ws, "admin/kid/save", token=token, kid_id=ada, name="Ada", active=True)
    assert len(await _today(ws)) == 1


async def test_settings_save(ws):
    token = await unlock(ws)
    res = await ok(
        ws,
        "admin/settings/save",
        token=token,
        settings={"idle_seconds": 90, "pin_timeout_seconds": 60},
    )
    assert res["settings"]["idle_seconds"] == 90
    assert ws.entry.runtime_data.sessions.timeout == 60
    assert (
        await err(ws, "admin/settings/save", token=token, settings={"bogus": 1}) == "invalid_format"
    )
    assert (
        await err(ws, "admin/settings/save", token=token, settings={"idle_seconds": 1})
        == "invalid_format"
    )


async def test_admin_actions_are_audited(ws):
    """AC-7.7."""
    token = await unlock(ws)
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada"))["id"]
    await ok(ws, "admin/kid/save", token=token, kid_id=ada, name="Ada B")
    await ok(ws, "admin/settings/save", token=token, settings={"clean_hands_enabled": False})
    log = await ws.entry.runtime_data.async_read(lambda r: r.list_audit())
    assert [e["action"] for e in log] == ["settings_save", "kid_save", "kid_save"]
    assert log[1]["before"] and '"Ada B"' in log[1]["after"]
    assert all(e["user_id"] for e in log)
