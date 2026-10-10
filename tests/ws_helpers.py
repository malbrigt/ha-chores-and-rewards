"""Helpers for WebSocket tests."""

from datetime import datetime
from zoneinfo import ZoneInfo

from pytest_homeassistant_custom_component.common import async_fire_time_changed

P = "chores_and_rewards/"
OSLO = ZoneInfo("Europe/Oslo")
TEST_PIN = "1234"


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


async def midnight(hass, freezer, day, hour=0):
    """Jump to 2026-10-<day> <hour>:00 Oslo and let HA's time listeners run."""
    freezer.move_to(datetime(2026, 10, day, hour, 0, 0, tzinfo=OSLO))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def kid_board(client, kid_id, **kw):
    """One kid's board from get_state: {chores, bonus, balances}."""
    return (await ok(client, "get_state", **kw))["board"][str(kid_id)]
