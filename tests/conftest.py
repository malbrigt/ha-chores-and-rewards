"""Shared fixtures."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.chores_and_rewards.const import CONF_PIN_HASH, DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"

TEST_PIN = "1234"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let HA load integrations from custom_components/."""
    return


@pytest.fixture(autouse=True)
async def isolated_config(hass, tmp_path):
    """Keep the SQLite file in a temp dir and use the family's timezone."""
    hass.config.config_dir = str(tmp_path)
    await hass.config.async_set_time_zone("Europe/Oslo")


@pytest.fixture(scope="session")
def pin_hash():
    from custom_components.chores_and_rewards.logic import hash_pin

    return hash_pin(TEST_PIN)


@pytest.fixture
async def setup_entry(hass, pin_hash):
    """Factory: add and set up the integration, return the config entry."""

    async def _setup():
        entry = MockConfigEntry(domain=DOMAIN, data={CONF_PIN_HASH: pin_hash})
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup
