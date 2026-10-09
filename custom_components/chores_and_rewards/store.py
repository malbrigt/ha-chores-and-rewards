"""The store: glues db.py and logic.py to Home Assistant.

All DB work runs in the executor. Writes are serialized by one asyncio.Lock so the
midnight job and a kid's tap can never interleave.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import date, timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import EVENT_UPDATED, SIGNAL_UPDATED, SYSTEM_USER
from .db import Database, Repo
from .logic import days_to_finalize, finalize, instances_for_day, week_start, weeks_to_close

_LOGGER = logging.getLogger(__name__)


class ChoresStore:
    """Owns the database and the daily rollover."""

    def __init__(self, hass: HomeAssistant, db: Database) -> None:
        self.hass = hass
        self.db = db
        self.lock = asyncio.Lock()

    @staticmethod
    def today() -> date:
        """Today in HA's configured timezone (D16)."""
        return dt_util.now().date()

    async def async_start(self) -> None:
        """Migrate the schema, then catch up on any days missed while HA was off."""
        version = await self.hass.async_add_executor_job(self.db.migrate)
        _LOGGER.debug("Database at schema v%s: %s", version, self.db.path)
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

    @callback
    def async_notify(self) -> None:
        self.hass.bus.async_fire(EVENT_UPDATED)
        async_dispatcher_send(self.hass, SIGNAL_UPDATED)

    async def async_rollover(self) -> None:
        """Finalize past days, close finished weeks, create today's chores. Idempotent."""
        today = self.today()
        changed = await self.async_write(lambda repo: rollover(repo, today), notify=False)
        if changed:
            _LOGGER.info("Rollover processed %s day(s) up to %s", changed, today)
        self.async_notify()


def rollover(repo: Repo, today: date) -> int:
    """Synchronous rollover in one transaction. Returns the number of days finalized.

    - Each past day not yet finalized gets its instances (created if HA was off that day),
      then pending expected chores become missed (AC-5.3, AC-6.3).
    - Weeks before the current one are closed (D1, AC-9.2).
    - Today's instances are created (D6).
    """
    last = repo.last_finalized()
    if last is None:  # fresh install: nothing in the past to judge
        last = today - timedelta(days=1)
        repo.set_last_finalized(last)
    days = days_to_finalize(last, today)
    if days:
        kids = [k.id for k in repo.list_kids()]
        chores = repo.list_chores()
        for day in days:
            repo.insert_instances(instances_for_day(chores, kids, day), week_start(day))
            for inst in repo.list_instances(day=day):
                done = finalize(inst)
                if done.status is not inst.status:
                    assert inst.id is not None
                    repo.set_status(inst.id, done.status, by=SYSTEM_USER)
            repo.set_last_finalized(day)
    for week in weeks_to_close(repo.open_weeks(), today):
        repo.close_week(week, by=SYSTEM_USER)
        repo.audit("close_week", user_id=SYSTEM_USER, entity="week", entity_id=week, note="auto")
    ensure_today(repo, today)
    return len(days)


def ensure_today(repo: Repo, today: date) -> None:
    """Create today's instances for current kids/chores (safe to call any time)."""
    week = week_start(today)
    repo.ensure_week(week)
    kids = [k.id for k in repo.list_kids()]
    repo.insert_instances(instances_for_day(repo.list_chores(), kids, today), week)
