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
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .audit import AuditAction
from .const import CONF_PIN_HASH, SIGNAL_UPDATED, SYSTEM_USER
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
    start = last = repo.last_finalized()
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
                    repo.audit(
                        "auto_missed",
                        user_id=SYSTEM_USER,
                        entity="instance",
                        entity_id=inst.id,
                        before={"status": inst.status.value},
                        after={"status": done.status.value, "chore": inst.name},
                        kid_id=inst.kid_id,
                        day=day,
                    )
            repo.set_last_finalized(day)
    new_last = repo.last_finalized()
    if new_last != start:  # D46: the progress marker is replayable too
        repo.audit(
            "rollover",
            user_id=SYSTEM_USER,
            after={"last_finalized": new_last.isoformat() if new_last else None},
            day=new_last,
        )
    for week in weeks_to_close(repo.open_weeks(), today):
        repo.close_week(week, by=SYSTEM_USER)
        repo.audit("close_week", user_id=SYSTEM_USER, entity="week", day=week, note="auto")
    ensure_today(repo, today)
    repo.optimize()  # once a day, under the write lock (sqlite.org: run periodically)
    return len(days)


def ensure_today(repo: Repo, today: date, by: str | None = SYSTEM_USER) -> None:
    """Create today's instances for current kids/chores (safe to call any time).

    Nothing is created in a week that was closed early (D31).
    """
    repo.ensure_week(week_start(today), by=by)
    if repo.week_status(week_start(today)) == "closed":
        return
    kids = [k.id for k in repo.list_kids()]
    repo.insert_instances(instances_for_day(repo.list_chores(), kids, today), by=by)


def refresh_today_for_chore(
    repo: Repo, chore_id: int, today: date, by: str | None = SYSTEM_USER
) -> None:
    """Bring today's rows in line with an edited/deleted chore (D7). History is untouched."""
    chore = repo.get_chore(chore_id)
    kids = [k.id for k in repo.list_kids()]
    keep = [k for k in kids if chore is not None and is_scheduled(chore, k, today)]
    repo.delete_pending(chore_id, today, keep_kids=keep, by=by)
    if chore is not None:
        repo.resync_pending(chore, today, by=by)
    ensure_today(repo, today, by=by)


def refresh_today_for_kid(
    repo: Repo, kid_id: int, today: date, by: str | None = SYSTEM_USER
) -> None:
    """Drop today's pending rows for an inactive/deleted kid, or create them for an active one."""
    kid = repo.get_kid(kid_id)
    if kid is None or not kid.active:
        repo.delete_pending_for_kid(kid_id, today, by=by)
    ensure_today(repo, today, by=by)


# --- Read models --------------------------------------------------------------


def _sort_key(inst: Instance) -> tuple[int, int, int]:
    """Bonus last; expected by slot (morning → afternoon → anytime); then creation order."""
    bonus = 1 if inst.type is ChoreType.BONUS else 0
    return (bonus, SLOT_ORDER.index(inst.slot), inst.id or 0)


def week_balances(repo: Repo, week: date, today: date) -> dict[int, dict[int, Balance]]:
    """Balance per active kid and currency for one week (D4, D5).

    Loads everything once (instances, chores, currencies, maxes, adjustments) and then
    uses the pure rules in logic.py, so the cost doesn't grow with kids × currencies.
    """
    currencies = repo.list_currencies()
    chores = repo.list_chores()
    maxes = repo.all_kid_max()
    adjustments = repo.adjustment_totals(week)
    by_kid: dict[int, list[Instance]] = {}
    for inst in repo.list_instances(week=week):
        by_kid.setdefault(inst.kid_id, []).append(inst)
    out: dict[int, dict[int, Balance]] = {}
    for kid in repo.list_kids():
        mine = by_kid.get(kid.id, [])
        out[kid.id] = {}
        for c in currencies:
            pot = week_pot(mine, chores, kid.id, week, today, c.id)
            cap = resolve_cap(c, maxes.get((kid.id, c.id)), pot)
            out[kid.id][c.id] = compute_balance(c, mine, adjustments.get((kid.id, c.id), 0), cap)
    return out


def kid_balances(repo: Repo, kid_id: int, week: date, today: date) -> dict[int, Balance]:
    """Balances for one kid (empty if the kid is inactive or deleted)."""
    return week_balances(repo, week, today).get(kid_id, {})


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
    balances = week_balances(repo, week, today)
    out = {}
    for kid in kids:
        mine = [i for i in rows if i.kid_id == kid.id]
        out[kid.id] = KidBoard(
            chores=[i for i in mine if i.type is ChoreType.EXPECTED],
            bonus=[i for i in mine if i.type is ChoreType.BONUS],
            balances=balances.get(kid.id, {}),
        )
    return out


def week_grid(repo: Repo, kid_id: int, week: date) -> list[dict]:
    """One row per chore seen that week, with the instance per day (AC-8.3)."""
    rows: dict[int, dict] = {}
    for inst in sorted(repo.list_instances(week=week, kid_id=kid_id), key=_sort_key):
        row = rows.setdefault(
            inst.chore_id,
            {"chore_id": inst.chore_id, "type": inst.type, "slot": inst.slot, "days": {}},
        )
        row["name"] = inst.name  # latest snapshot wins
        row["days"][inst.day] = inst
    return list(rows.values())
