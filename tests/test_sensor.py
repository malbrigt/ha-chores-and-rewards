"""Balance sensors (spec §12, AC-12.1)."""

import pytest
from homeassistant.helpers import entity_registry as er

from .ws_helpers import chore, ok, unlock

pytestmark = pytest.mark.freeze_time("2026-10-12 08:00:00+00:00")  # Mon 10:00 Oslo


async def test_sensors_follow_kids_currencies_and_balances(hass, ws):
    token = await unlock(ws)
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada", max={"1": 60}))["id"]
    await hass.async_block_till_done()
    screen = hass.states.get("sensor.ada_skjermtid")
    money = hass.states.get("sensor.ada_ukepenger")
    assert screen.state == "0" and money.state == "0"
    assert screen.attributes["unit_of_measurement"] == "min"
    assert screen.attributes["cap"] == 60 and screen.attributes["week"] == "2026-10-12"
    assert screen.attributes["icon"] == "mdi:tablet"

    await ok(ws, "admin/chore/save", token=token, **chore([ada]))
    inst = (await ok(ws, "get_state"))["board"][str(ada)]["chores"][0]
    await ok(ws, "set_done", instance_id=inst["id"], done=True)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.ada_skjermtid").state == "30"
    assert hass.states.get("sensor.ada_ukepenger").state == "10"

    # Adjustments update the sensor too.
    await ok(ws, "parent/adjust", token=token, kid_id=ada, currency_id=1, amount=5, note="x")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.ada_skjermtid").state == "35"

    # Deactivating a currency removes its sensors; deleting the kid removes the rest.
    registry = er.async_get(hass)
    await ok(
        ws,
        "admin/currency/save",
        token=token,
        currency_id=2,
        name="Ukepenger",
        unit="kr",
        payout_weekday=5,
        can_be_lost=False,
        cap_mode="pot",
        active=False,
    )
    await hass.async_block_till_done()
    assert registry.async_get("sensor.ada_ukepenger") is None
    await ok(ws, "admin/kid/delete", token=token, kid_id=ada)
    await hass.async_block_till_done()
    assert registry.async_get("sensor.ada_skjermtid") is None


async def test_new_kid_gets_sensors_and_unload(hass, ws):
    token = await unlock(ws)
    await ok(ws, "admin/kid/save", token=token, name="Bo")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bo_skjermtid") is not None
    assert await hass.config_entries.async_unload(ws.entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.bo_skjermtid").state == "unavailable"
