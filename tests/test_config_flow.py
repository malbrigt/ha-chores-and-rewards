"""Config flow, reconfigure flow, setup errors and setup/unload."""

import sqlite3
from unittest.mock import patch

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


async def test_reconfigure_resets_pin(hass):
    """An HA admin changes the PIN via Reconfigure; the entry reloads (D40)."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_PIN_HASH: hash_pin("1111")})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"pin": "99", "pin_confirm": "99"}
    )
    assert result["errors"] == {"pin": "invalid_pin"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"pin": "9999", "pin_confirm": "9999"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert verify_pin("9999", entry.data[CONF_PIN_HASH])
    assert entry.state is ConfigEntryState.LOADED
    log = await entry.runtime_data.async_read(lambda r: r.list_audit(actions=["pin_reset"]))
    assert len(log) == 1


async def test_setup_errors_are_translated(hass):
    """A newer schema can't be fixed by retrying; a busy/broken file can."""
    from custom_components.chores_and_rewards.db import SchemaTooNewError

    for error, state in (
        (SchemaTooNewError("v9"), ConfigEntryState.SETUP_ERROR),
        (sqlite3.OperationalError("disk I/O error"), ConfigEntryState.SETUP_RETRY),
    ):
        entry = MockConfigEntry(domain=DOMAIN, data={CONF_PIN_HASH: "x"})
        entry.add_to_hass(hass)
        with patch("custom_components.chores_and_rewards.db.Database.migrate", side_effect=error):
            await hass.config_entries.async_setup(entry.entry_id)
        assert entry.state is state
        await hass.config_entries.async_remove(entry.entry_id)


async def test_setup_and_unload(hass):  # uses temp config dir via conftest
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_PIN_HASH: hash_pin("1234")})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
