"""Config flow, options flow and setup/unload."""

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores_and_rewards.const import CONF_PIN_HASH, DOMAIN
from custom_components.chores_and_rewards.logic import hash_pin, verify_pin


async def _start(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow_creates_entry(hass):
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"pin": "1234", "pin_confirm": "1234"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert verify_pin("1234", result["data"][CONF_PIN_HASH])
    assert "pin" not in result["data"]


async def test_user_flow_errors(hass):
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"pin": "12", "pin_confirm": "12"}
    )
    assert result["errors"] == {"pin": "invalid_pin"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"pin": "1234", "pin_confirm": "4321"}
    )
    assert result["errors"] == {"pin_confirm": "pin_mismatch"}


async def test_single_instance(hass):
    MockConfigEntry(domain=DOMAIN, data={CONF_PIN_HASH: "x"}).add_to_hass(hass)
    result = await _start(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_options_flow_resets_pin(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_PIN_HASH: hash_pin("1111")})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"pin": "9999", "pin_confirm": "9999"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert verify_pin("9999", entry.data[CONF_PIN_HASH])


async def test_setup_and_unload(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_PIN_HASH: hash_pin("1234")})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
