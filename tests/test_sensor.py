"""Balance sensors (spec §12, AC-12.1)."""

from datetime import timedelta

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .ws_helpers import chore, ok, unlock

pytestmark = pytest.mark.freeze_time("2026-10-12 08:00:00+00:00")  # Mon 10:00 Oslo


async def settle(hass, freezer):
    """Let the 1 s refresh debouncer run."""
    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def test_sensors_follow_kids_currencies_and_balances(hass, ws, freezer):
    token = await unlock(ws)
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada", max={"1": 60}))["id"]
    await settle(hass, freezer)
    screen = hass.states.get("sensor.ada_skjermtid")
    money = hass.states.get("sensor.ada_ukepenger")
    assert screen.state == "0" and money.state == "0"
    assert screen.attributes["unit_of_measurement"] == "min"
    assert screen.attributes["cap"] == 60 and screen.attributes["week"] == "2026-10-12"
    assert screen.attributes["icon"] == "mdi:tablet"

    await ok(ws, "admin/chore/save", token=token, **chore([ada]))
    inst = (await ok(ws, "get_state"))["board"][str(ada)]["chores"][0]
    await ok(ws, "set_done", instance_id=inst["id"], done=True)
    await settle(hass, freezer)
    assert hass.states.get("sensor.ada_skjermtid").state == "30"
    assert hass.states.get("sensor.ada_ukepenger").state == "10"

    # Adjustments update the sensor too.
    await ok(ws, "parent/adjust", token=token, kid_id=ada, currency_id=1, amount=5, note="x")
    await settle(hass, freezer)
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
    await settle(hass, freezer)
    assert registry.async_get("sensor.ada_ukepenger") is None
    await ok(ws, "admin/kid/delete", token=token, kid_id=ada)
    await settle(hass, freezer)
    assert registry.async_get("sensor.ada_skjermtid") is None


async def test_new_kid_gets_sensors_and_unload(hass, ws, freezer):
    token = await unlock(ws)
    await ok(ws, "admin/kid/save", token=token, name="Bo")
    await settle(hass, freezer)
    assert hass.states.get("sensor.bo_skjermtid") is not None
    assert await hass.config_entries.async_unload(ws.entry.entry_id)
    await settle(hass, freezer)
    assert hass.states.get("sensor.bo_skjermtid").state == "unavailable"


async def test_one_device_per_kid_follows_rename_and_delete(hass, ws, freezer):
    """Quality scale: has_entity_name + devices; stale devices are removed."""
    token = await unlock(ws)
    ada = (await ok(ws, "admin/kid/save", token=token, name="Ada"))["id"]
    await settle(hass, freezer)
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    entry = entities.async_get("sensor.ada_skjermtid")
    device = devices.async_get(entry.device_id)
    assert device.name == "Ada"
    assert hass.states.get("sensor.ada_skjermtid").attributes["friendly_name"] == "Ada Skjermtid"

    await ok(ws, "admin/kid/save", token=token, kid_id=ada, name="Ada Marie")
    await settle(hass, freezer)
    assert devices.async_get(entry.device_id).name == "Ada Marie"
    assert entities.async_get("sensor.ada_skjermtid") is not None  # entity_id is stable

    await ok(ws, "admin/kid/delete", token=token, kid_id=ada)
    await settle(hass, freezer)
    assert devices.async_get(entry.device_id) is None
    assert entities.async_get("sensor.ada_skjermtid") is None
