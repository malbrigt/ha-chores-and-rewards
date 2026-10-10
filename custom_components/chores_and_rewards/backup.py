"""Backup platform: keep the SQLite file consistent while HA copies /config.

Like the recorder: block writes and flush the write-ahead log before the backup, and
allow writes again afterwards. A kid's tap during a backup simply waits (D23).
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_pre_backup(hass: HomeAssistant) -> None:
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        store = entry.runtime_data
        await store.lock.acquire()
        store.backup_in_progress = True
        try:
            await hass.async_add_executor_job(store.db.checkpoint)
        except Exception:
            store.backup_in_progress = False
            store.lock.release()
            raise


async def async_post_backup(hass: HomeAssistant) -> None:
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        store = entry.runtime_data
        if store.backup_in_progress:
            store.backup_in_progress = False
            store.lock.release()
