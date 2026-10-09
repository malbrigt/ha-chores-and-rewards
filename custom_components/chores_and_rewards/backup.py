"""Backup platform: flush SQLite's write-ahead log before HA takes a backup.

After a checkpoint the main .db file holds all committed data, so the copy in the
backup is consistent. Writes are not blocked during the backup (kids can still tap).
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_pre_backup(hass: HomeAssistant) -> None:
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        store = entry.runtime_data
        async with store.lock:
            await hass.async_add_executor_job(store.db.checkpoint)


async def async_post_backup(hass: HomeAssistant) -> None:
    """Nothing to undo."""
