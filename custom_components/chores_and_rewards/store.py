"""The store: Home Assistant glue around the database, plus the read models.

All DB work runs in the executor. Writes are serialized by one asyncio.Lock so the
midnight job and a kid's tap can never interleave. Use cases live in actions.py (D47).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from . import actions
from .audit import AuditAction
from .const import CONF_PIN_HASH, SIGNAL_UPDATED
from .db import Database, Repo
from .sessions import PinSessions

_LOGGER = logging.getLogger(__name__)


class ChoresStore:
    """Owns the database and the daily rollover."""

    def __init__(self, hass: HomeAssistant, db: Database, entry: ConfigEntry) -> None:
        self.hass = hass
        self.db = db
        self.entry = entry
        self.lock = asyncio.Lock()
        self.backup_in_progress = False  # set by backup.py while it holds the lock
        self.sessions = PinSessions()

    @property
    def pin_hash(self) -> str:
        return str(self.entry.data[CONF_PIN_HASH])

    def apply_settings(self, settings: dict[str, Any]) -> None:
        """Settings that live in memory (the PIN session timeout)."""
        self.sessions.timeout = settings["pin_timeout_seconds"]

    @staticmethod
    def today() -> date:
        """Today in HA's configured timezone (D16)."""
        return dt_util.now().date()

    async def async_start(self) -> None:
        """Migrate the schema, then catch up on any days missed while HA was off."""
        version = await self.hass.async_add_executor_job(self.db.migrate)
        _LOGGER.debug("Database at schema v%s: %s", version, self.db.path)
        self.apply_settings(await self.async_read(lambda repo: repo.get_settings()))
        await self.async_rollover()

    async def async_read[T](self, fn: Callable[[Repo], T]) -> T:
        """Run a read-only query (WAL allows reads alongside writes)."""
        return await self.hass.async_add_executor_job(self.db.run, fn)

    async def async_write[T](self, fn: Callable[[Repo], T], notify: bool = True) -> T:
        """Run a write transaction under the lock, then tell listeners."""
        async with self.lock:
            result = await self.hass.async_add_executor_job(self.db.run, fn)
        if notify:
            self.async_notify()
        return result

    async def async_audit(self, action: AuditAction, user_id: str | None, **kwargs: Any) -> None:
        """Audit an event that changes no stored state (e.g. PIN usage). No update event."""
        await self.async_write(
            lambda repo: repo.audit(action, user_id=user_id, **kwargs), notify=False
        )

    @callback
    def async_notify(self) -> None:
        """Tell the panel and sensors that data changed (internal signal only, D47)."""
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)

    async def async_ensure_current(self) -> None:
        """Safety net: run the rollover if the midnight job was missed (e.g. clock jump)."""
        last = await self.async_read(lambda repo: repo.last_finalized())
        if last is None or last < self.today() - timedelta(days=1):
            await self.async_rollover()

    async def async_rollover(self) -> None:
        """Finalize past days, close finished weeks, create today's chores. Idempotent."""
        today = self.today()
        changed = await self.async_write(lambda repo: actions.rollover(repo, today), notify=False)
        if changed:
            _LOGGER.info("Rollover processed %s day(s) up to %s", changed, today)
        self.async_notify()
