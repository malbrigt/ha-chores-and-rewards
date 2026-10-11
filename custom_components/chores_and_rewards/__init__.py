"""Chores and Rewards: a chores and rewards tracker for Home Assistant."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from . import websocket_api
from .const import (
    DB_FILENAME,
    DOMAIN,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_URL,
    STATIC_URL,
    panel_title,
)
from .db import Database, SchemaTooNewError
from .store import ChoresStore

_LOGGER = logging.getLogger(__name__)

type ChoresConfigEntry = ConfigEntry[ChoresStore]

PLATFORMS = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register WebSocket commands and the static frontend path once.

    HA has no way to unregister either, so they live for the whole HA run.
    """
    websocket_api.async_register(hass)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), cache_headers=False)]
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ChoresConfigEntry) -> bool:
    """Open the database, catch up, and schedule the midnight rollover."""
    store = ChoresStore(hass, Database(hass.config.path(DB_FILENAME)), entry)
    try:
        await store.async_start()
    except SchemaTooNewError as err:
        raise ConfigEntryError(translation_domain=DOMAIN, translation_key="database_newer") from err
    except sqlite3.Error as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="database_unavailable",
            translation_placeholders={"error": str(err)},
        ) from err
    entry.runtime_data = store

    @callback
    def _midnight(_now: datetime) -> None:
        # Tracked by the entry: unload waits for a running rollover to finish.
        entry.async_create_task(hass, store.async_rollover(), "rollover")

    # Fires at 00:00:00 in HA's local timezone.
    entry.async_on_unload(async_track_time_change(hass, _midnight, hour=0, minute=0, second=0))
    await _async_register_panel(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_register_panel(hass: HomeAssistant, entry: ChoresConfigEntry) -> None:
    """Sidebar panel. The ?v= query busts the browser cache on upgrades."""
    version = (await async_get_integration(hass, DOMAIN)).version
    if not frontend.async_panel_exists(hass, PANEL_URL):
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title=panel_title(hass.config.language),
            sidebar_icon=PANEL_ICON,
            module_url=f"{STATIC_URL}/panel.js?v={version}",
            require_admin=False,  # D14: the tablet may run as a normal HA user
            config={"version": str(version)},
        )
    entry.async_on_unload(
        lambda: frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
    )


async def async_unload_entry(hass: HomeAssistant, entry: ChoresConfigEntry) -> bool:
    """Unload a config entry. Listeners are removed via async_on_unload."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
