"""Helpers for WebSocket tests."""

P = "chores_and_rewards/"
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
