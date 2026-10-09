"""Chores and Rewards: a chores and rewards tracker for Home Assistant."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from .const import DB_FILENAME
from .db import Database
from .store import ChoresStore

_LOGGER = logging.getLogger(__name__)

type ChoresConfigEntry = ConfigEntry[ChoresStore]


async def async_setup_entry(hass: HomeAssistant, entry: ChoresConfigEntry) -> bool:
    """Open the database, catch up, and schedule the midnight rollover."""
    store = ChoresStore(hass, Database(hass.config.path(DB_FILENAME)))
    await store.async_start()
    entry.runtime_data = store

    @callback
    def _midnight(_now: datetime) -> None:
        # Tracked by the entry: unload waits for a running rollover to finish.
        entry.async_create_task(hass, store.async_rollover(), "rollover")

    # Fires at 00:00:00 in HA's local timezone.
    entry.async_on_unload(async_track_time_change(hass, _midnight, hour=0, minute=0, second=0))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ChoresConfigEntry) -> bool:
    """Unload a config entry. Listeners are removed via async_on_unload."""
    return True
