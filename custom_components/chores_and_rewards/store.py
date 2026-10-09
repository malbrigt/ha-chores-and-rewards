"""The store: glues db.py and logic.py to Home Assistant.

All DB work runs in the executor. Writes are serialized by one asyncio.Lock so the
midnight job and a kid's tap can never interleave.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import EVENT_UPDATED, SIGNAL_UPDATED, SYSTEM_USER
from .db import Database, Repo
from .logic import (
    SLOT_ORDER,
    Balance,
    ChoreType,
    Instance,
    compute_balance,
    days_to_finalize,
    finalize,
    instances_for_day,
    is_scheduled,
    resolve_cap,
    week_pot,
    week_start,
    weeks_to_close,
)
from .sessions import PinSessions

_LOGGER = logging.getLogger(__name__)


class ChoresStore:
    """Owns the database and the daily rollover."""

    def __init__(self, hass: HomeAssistant, db: Database) -> None:
        self.hass = hass
        self.db = db
        self.lock = asyncio.Lock()
        self.sessions = PinSessions()

    @staticmethod
    def today() -> date:
        """Today in HA's configured timezone (D16)."""
        return dt_util.now().date()

    async def async_start(self) -> None:
        """Migrate the schema, then catch up on any days missed while HA was off."""
        version = await self.hass.async_add_executor_job(self.db.migrate)
        _LOGGER.debug("Database at schema v%s: %s", version, self.db.path)
        settings = await self.async_read(lambda repo: repo.get_settings())
        self.sessions.timeout = settings["pin_timeout_seconds"]
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

    async def async_ensure_current(self) -> None:
        """Safety net: run the rollover if the midnight job was missed (e.g. clock jump)."""
        last = await self.async_read(lambda repo: repo.last_finalized())
        if last is None or last < self.today() - timedelta(days=1):
            await self.async_rollover()

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
            if repo.week_status(week_start(day)) == "closed":  # closed early: frozen (D31)
                repo.set_last_finalized(day)
                continue
            repo.insert_instances(instances_for_day(chores, kids, day))
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
    """Create today's instances for current kids/chores (safe to call any time).

    Nothing is created in a week that was closed early (D31).
    """
    repo.ensure_week(week_start(today))
    if repo.week_status(week_start(today)) == "closed":
        return
    kids = [k.id for k in repo.list_kids()]
    repo.insert_instances(instances_for_day(repo.list_chores(), kids, today))


def refresh_today_for_chore(repo: Repo, chore_id: int, today: date) -> None:
    """Bring today's rows in line with an edited/deleted chore (D7). History is untouched."""
    chore = repo.get_chore(chore_id)
    kids = [k.id for k in repo.list_kids()]
    keep = [k for k in kids if chore is not None and is_scheduled(chore, k, today)]
    repo.delete_pending(chore_id, today, keep_kids=keep)
    if chore is not None:
        repo.resync_pending(chore, today)
    ensure_today(repo, today)


def refresh_today_for_kid(repo: Repo, kid_id: int, today: date) -> None:
    """Drop today's pending rows for an inactive/deleted kid, or create them for an active one."""
    kid = repo.get_kid(kid_id)
    if kid is None or not kid.active:
        repo.delete_pending_for_kid(kid_id, today)
    ensure_today(repo, today)


# --- Read models --------------------------------------------------------------


def _sort_key(inst: Instance) -> tuple[int, int, int]:
    """Bonus last; expected by slot (morning → afternoon → anytime); then creation order."""
    bonus = 1 if inst.type is ChoreType.BONUS else 0
    return (bonus, SLOT_ORDER.index(inst.slot), inst.id or 0)


def kid_balances(repo: Repo, kid_id: int, week: date, today: date) -> dict[int, Balance]:
    """Balance per active currency for one kid and week (D4, D5)."""
    instances = repo.list_instances(week=week, kid_id=kid_id)
    chores = repo.list_chores()
    maxes = repo.kid_max(kid_id)
    out = {}
    for currency in repo.list_currencies():
        pot = week_pot(instances, chores, kid_id, week, today, currency.id)
        cap = resolve_cap(currency, maxes.get(currency.id), pot)
        adjustments = repo.adjustment_total(week, kid_id, currency.id)
        out[currency.id] = compute_balance(currency, instances, adjustments, cap)
    return out


@dataclass(frozen=True)
class KidBoard:
    chores: list[Instance]  # expected, ordered by slot
    bonus: list[Instance]
    balances: dict[int, Balance]


def board(repo: Repo, day: date, today: date) -> dict[int, KidBoard]:
    """Per kid: expected chores and bonus chores for `day`, plus that week's balances.

    Future days have no rows yet, so they get an unsaved preview from the schedule (D37).
    """
    week = week_start(day)
    kids = repo.list_kids()
    found = repo.list_instances(day=day)
    if day > today and not found:
        found = instances_for_day(repo.list_chores(), [k.id for k in kids], day)
    rows = sorted(found, key=_sort_key)
    out = {}
    for kid in kids:
        mine = [i for i in rows if i.kid_id == kid.id]
        out[kid.id] = KidBoard(
            chores=[i for i in mine if i.type is ChoreType.EXPECTED],
            bonus=[i for i in mine if i.type is ChoreType.BONUS],
            balances=kid_balances(repo, kid.id, week, today),
        )
    return out


def week_grid(repo: Repo, kid_id: int, week: date) -> list[dict]:
    """One row per chore seen that week, with a status cell per day (AC-8.3)."""
    rows: dict[int, dict] = {}
    for inst in sorted(repo.list_instances(week=week, kid_id=kid_id), key=_sort_key):
        row = rows.setdefault(
            inst.chore_id,
            {
                "chore_id": inst.chore_id,
                "type": inst.type,
                "slot": inst.slot,
                "cells": {},
                "ids": {},
            },
        )
        row["name"] = inst.name  # latest snapshot wins
        row["cells"][inst.day] = inst.status
        row["ids"][inst.day] = inst.id
    return list(rows.values())
