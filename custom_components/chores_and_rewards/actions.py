"""Use cases: one function per thing a user, a parent or the clock can do (D47).

Each runs inside one DB transaction (`store.async_write`) and returns plain data.
Rules come from logic.py and storage from db.py. Every state change is audited here
or in db.py with enough data to replay it (D46). WebSocket handlers only validate
input, call one of these and serialize the result. No Home Assistant imports.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Any

from .audit import AuditAction
from .const import SYSTEM_USER
from .db import Repo
from .logic import (
    Actor,
    Chore,
    ChoreType,
    Currency,
    Instance,
    Kid,
    RuleError,
    Status,
    WeekStatus,
    days_to_finalize,
    earn_options,
    finalize,
    instances_for_day,
    is_late,
    is_scheduled,
    payout_warnings,
    taken_by,
    transition,
    undo_status,
    week_start,
    weeks_to_close,
)
from .serialize import chore_json, currency_json, kid_json
from .views import kid_balances


class NotFound(Exception):
    """Unknown or deleted id."""


@dataclass(frozen=True)
class Ctx:
    """Who acts, and what day it is (HA's local date)."""

    by: str | None  # HA user id, or SYSTEM_USER for the clock
    today: date


def require[T](value: T | None) -> T:
    if value is None:
        raise NotFound
    return value


def _require_open(repo: Repo, week: date) -> None:
    if repo.week_status(week) is not WeekStatus.OPEN:
        raise RuleError("week_closed")


# --- Chore status ----------------------------------------------------------------


def _record_status(
    repo: Repo, action: AuditAction, ctx: Ctx, old: Instance, new: Instance, status_by: str | None
) -> Instance:
    """Store a status change and audit it with the chore's day and a late flag (D43)."""
    instance_id = require(new.id)
    status_at = repo.set_status(instance_id, new.status, status_by, new.currency_id)
    repo.audit(
        action,
        user_id=ctx.by,
        entity="instance",
        entity_id=instance_id,
        before={"status": old.status.value, "currency_id": old.currency_id},
        after={"status": new.status.value, "chore": new.name, "currency_id": new.currency_id},
        kid_id=new.kid_id,
        day=new.day,
        late=is_late(new.day, ctx.today),
    )
    return replace(new, status_at=status_at)


def _earns(repo: Repo, ctx: Ctx, inst: Instance, status: Status, wanted: int | None) -> int | None:
    """The currency a done extra chore earns: the kid's pick, else the first option (D49).

    Expected chores earn all their values (None), and so does anything not done.
    """
    if status is not Status.DONE or inst.type is not ChoreType.BONUS:
        return None
    balances = kid_balances(repo, inst.kid_id, week_start(inst.day), ctx.today)
    options = earn_options(inst, repo.list_currencies(), balances)
    if wanted is None:
        return options[0] if options else None
    if wanted not in options:
        raise RuleError("nothing_lost" if wanted in inst.values else "not_allowed")
    return wanted


def _require_free(repo: Repo, inst: Instance, status: Status) -> None:
    """A once-a-day extra already done by another kid that day can't be done again (D51)."""
    if status is Status.DONE and taken_by(inst, repo.list_instances(day=inst.day)) is not None:
        raise RuleError("taken")


def set_done(
    repo: Repo, ctx: Ctx, instance_id: int, done: bool, currency_id: int | None = None
) -> Instance:
    """Kid tap: tick or untick any day of the open week, no approval (AC-6.1, AC-6.2, D8).

    Ticking an extra chore earns one currency, `currency_id` if given (AC-6.6, D49).
    """
    inst = require(repo.get_instance(instance_id))
    _require_open(repo, week_start(inst.day))
    target = Status.DONE if done else undo_status(inst, ctx.today)
    new = transition(inst, target, Actor.KID, ctx.today)
    _require_free(repo, inst, target)
    new = replace(new, currency_id=_earns(repo, ctx, inst, target, currency_id))
    action = AuditAction.CHECK if done else AuditAction.UNCHECK
    return _record_status(repo, action, ctx, inst, new, status_by=Actor.KID.value)


def set_status(
    repo: Repo, ctx: Ctx, instance_id: int, status: Status, currency_id: int | None = None
) -> Instance:
    """Parent: reject, mark done/excused/missed, or reset today (AC-7.4, AC-7.5, D19)."""
    inst = require(repo.get_instance(instance_id))
    _require_open(repo, week_start(inst.day))
    new = transition(inst, status, Actor.PARENT, ctx.today)
    _require_free(repo, inst, status)
    new = replace(new, currency_id=_earns(repo, ctx, inst, status, currency_id))
    return _record_status(repo, AuditAction.SET_STATUS, ctx, inst, new, status_by=ctx.by)


# --- Admin ---------------------------------------------------------------------------


def save_kid(repo: Repo, ctx: Ctx, kid: Kid, maxes: dict[int, int | None]) -> int:
    """Create (id 0) or update a kid and their weekly maximums."""
    before = None
    if kid.id:
        old = require(repo.get_kid(kid.id))
        before = kid_json(old, repo.kid_max(old.id))
    kid_id = repo.save_kid(kid)
    for currency_id, weekly_max in maxes.items():
        repo.set_kid_max(kid_id, currency_id, weekly_max)
    after = kid_json(require(repo.get_kid(kid_id)), repo.kid_max(kid_id))
    repo.audit(
        AuditAction.KID_SAVE,
        user_id=ctx.by,
        entity="kid",
        entity_id=kid_id,
        before=before,
        after=after,
        kid_id=kid_id,
    )
    refresh_today_for_kid(repo, ctx, kid_id)
    return kid_id


def delete_kid(repo: Repo, ctx: Ctx, kid_id: int) -> None:
    kid = require(repo.get_kid(kid_id))
    repo.delete_kid(kid.id)
    repo.audit(
        AuditAction.KID_DELETE,
        user_id=ctx.by,
        entity="kid",
        entity_id=kid.id,
        before=kid_json(kid),
        kid_id=kid.id,
    )
    refresh_today_for_kid(repo, ctx, kid.id)


def save_currency(repo: Repo, ctx: Ctx, currency: Currency) -> int:
    """Create (id 0) or update a currency. Its decimals are fixed once it exists (D50)."""
    old = require(repo.get_currency(currency.id)) if currency.id else None
    if old is not None and old.decimals != currency.decimals:
        raise RuleError("decimals_locked")  # would reinterpret every stored amount
    before = currency_json(old) if old else None
    currency_id = repo.save_currency(currency)
    repo.audit(
        AuditAction.CURRENCY_SAVE,
        user_id=ctx.by,
        entity="currency",
        entity_id=currency_id,
        before=before,
        after=currency_json(require(repo.get_currency(currency_id))),
    )
    return currency_id


def delete_currency(repo: Repo, ctx: Ctx, currency_id: int) -> None:
    currency = require(repo.get_currency(currency_id))
    repo.delete_currency(currency.id)
    repo.audit(
        AuditAction.CURRENCY_DELETE,
        user_id=ctx.by,
        entity="currency",
        entity_id=currency.id,
        before=currency_json(currency),
    )


def save_chore(repo: Repo, ctx: Ctx, chore: Chore) -> tuple[int, list[int]]:
    """Create (id 0) or update a chore. Returns its id and payout-day warnings (AC-5.5)."""
    known_kids = {k.id for k in repo.list_kids(True)}
    known_currencies = {c.id for c in repo.list_currencies(True)}
    if not chore.kid_ids <= known_kids or not set(chore.values) <= known_currencies:
        raise NotFound
    if chore.once_a_day and chore.type is not ChoreType.BONUS:
        raise RuleError("not_allowed")  # an expected chore is every kid's own (D51)
    before = chore_json(require(repo.get_chore(chore.id))) if chore.id else None
    chore_id = repo.save_chore(chore)
    saved = require(repo.get_chore(chore_id))
    repo.audit(
        AuditAction.CHORE_SAVE,
        user_id=ctx.by,
        entity="chore",
        entity_id=chore_id,
        before=before,
        after=chore_json(saved),
    )
    refresh_today_for_chore(repo, ctx, chore_id)
    return chore_id, payout_warnings(saved, repo.list_currencies())


def delete_chore(repo: Repo, ctx: Ctx, chore_id: int) -> None:
    chore = require(repo.get_chore(chore_id))
    repo.delete_chore(chore.id)
    repo.audit(
        AuditAction.CHORE_DELETE,
        user_id=ctx.by,
        entity="chore",
        entity_id=chore.id,
        before=chore_json(chore),
    )
    refresh_today_for_chore(repo, ctx, chore.id)


def save_settings(repo: Repo, ctx: Ctx, changes: dict[str, Any]) -> dict[str, Any]:
    before = repo.get_settings()
    for key, value in changes.items():
        repo.set_setting(key, value)
    after = repo.get_settings()
    repo.audit(
        AuditAction.SETTINGS_SAVE, user_id=ctx.by, entity="settings", before=before, after=after
    )
    return after


# --- Money and weeks -------------------------------------------------------------------


def adjust(repo: Repo, ctx: Ctx, kid_id: int, currency_id: int, amount: int, note: str) -> int:
    """Adjust this week's balance with a required note (AC-7.6)."""
    require(repo.get_kid(kid_id))
    require(repo.get_currency(currency_id))
    week = week_start(ctx.today)
    _require_open(repo, week)
    adjustment_id = repo.add_adjustment(week, kid_id, currency_id, amount, note, by=ctx.by)
    repo.audit(
        AuditAction.ADJUST,
        user_id=ctx.by,
        entity="adjustment",
        entity_id=adjustment_id,
        after={"week": week.isoformat(), "currency_id": currency_id, "amount": amount},
        note=note,
        kid_id=kid_id,
        day=ctx.today,
    )
    return adjustment_id


def payout(
    repo: Repo, ctx: Ctx, week: date, kid_id: int, currency_id: int, paid: bool
) -> int | None:
    """Tick "paid"/"entered" (stores the balance at this moment, D11) or untick it.

    Allowed for closed weeks too: late payouts happen (D32). Returns the stored amount.
    """
    require(repo.get_kid(kid_id))
    require(repo.get_currency(currency_id))
    amount = None
    if paid:
        amount = require(kid_balances(repo, kid_id, week, ctx.today).get(currency_id)).total
        repo.record_payout(week, kid_id, currency_id, amount, by=ctx.by)
    else:
        repo.undo_payout(week, kid_id, currency_id)
    repo.audit(
        AuditAction.PAYOUT_UNDO if amount is None else AuditAction.PAYOUT,
        user_id=ctx.by,
        entity="payout",
        after={"week": week.isoformat(), "currency_id": currency_id, "amount": amount},
        kid_id=kid_id,
        day=week,
    )
    return amount


def close_week(repo: Repo, ctx: Ctx) -> None:
    """Close the current week early (D1). It freezes: no taps, no midnight losses (D31)."""
    week = week_start(ctx.today)
    _require_open(repo, week)
    repo.close_week(week, by=ctx.by)
    repo.audit(AuditAction.CLOSE_WEEK, user_id=ctx.by, entity="week", note="manual", day=week)


def reopen_week(repo: Repo, ctx: Ctx) -> None:
    """Undo an early close of the current week (warn, don't block: mistakes happen)."""
    week = week_start(ctx.today)
    if repo.week_status(week) is not WeekStatus.CLOSED:
        raise RuleError("not_allowed")
    repo.reopen_week(week)
    repo.audit(AuditAction.REOPEN_WEEK, user_id=ctx.by, entity="week", day=week)
    ensure_today(repo, ctx)


# --- The clock and today's rows --------------------------------------------------------


def rollover(repo: Repo, today: date) -> int:
    """Finalize past days, close finished weeks, create today's rows. Returns days finalized.

    - Each past day not yet finalized gets its instances (created if HA was off that day),
      then pending expected chores become missed (AC-5.3, AC-6.3).
    - Weeks before the current one are closed (D1, AC-9.2).
    - Today's instances are created (D6). Idempotent.
    """
    ctx = Ctx(SYSTEM_USER, today)
    start = last = repo.last_finalized()
    if last is None:  # fresh install: nothing in the past to judge
        last = today - timedelta(days=1)
        repo.set_last_finalized(last)
    days = days_to_finalize(last, today)
    if days:
        kids = [k.id for k in repo.list_kids()]
        chores = repo.list_chores()
        for day in days:
            if repo.week_status(week_start(day)) is WeekStatus.CLOSED:  # frozen (D31)
                repo.set_last_finalized(day)
                continue
            repo.insert_instances(instances_for_day(chores, kids, day))
            for inst in repo.list_instances(day=day):
                done = finalize(inst)
                if done.status is not inst.status:
                    _record_status(repo, AuditAction.AUTO_MISSED, ctx, inst, done, SYSTEM_USER)
            repo.set_last_finalized(day)
    new_last = repo.last_finalized()
    if new_last != start:  # the progress marker is replayable too (D46)
        repo.audit(
            AuditAction.ROLLOVER,
            user_id=SYSTEM_USER,
            after={"last_finalized": new_last.isoformat() if new_last else None},
            day=new_last,
        )
    for week in weeks_to_close(repo.open_weeks(), today):
        repo.close_week(week, by=SYSTEM_USER)
        repo.audit(
            AuditAction.CLOSE_WEEK, user_id=SYSTEM_USER, entity="week", day=week, note="auto"
        )
    ensure_today(repo, ctx)
    repo.optimize()  # once a day, under the write lock (sqlite.org: run periodically)
    return len(days)


def ensure_today(repo: Repo, ctx: Ctx) -> None:
    """Create today's instances for current kids/chores (safe to call any time).

    Nothing is created in a week that was closed early (D31).
    """
    week = week_start(ctx.today)
    repo.ensure_week(week, by=ctx.by)
    if repo.week_status(week) is WeekStatus.CLOSED:
        return
    kids = [k.id for k in repo.list_kids()]
    repo.insert_instances(instances_for_day(repo.list_chores(), kids, ctx.today), by=ctx.by)


def refresh_today_for_chore(repo: Repo, ctx: Ctx, chore_id: int) -> None:
    """Bring today's rows in line with an edited/deleted chore (D7). History is untouched."""
    chore = repo.get_chore(chore_id)
    kids = [k.id for k in repo.list_kids()]
    keep = [k for k in kids if chore is not None and is_scheduled(chore, k, ctx.today)]
    repo.delete_pending(chore_id, ctx.today, keep_kids=keep, by=ctx.by)
    if chore is not None:
        repo.resync_pending(chore, ctx.today, by=ctx.by)
    ensure_today(repo, ctx)


def refresh_today_for_kid(repo: Repo, ctx: Ctx, kid_id: int) -> None:
    """Drop today's pending rows for an inactive/deleted kid, or create them for an active one."""
    kid = repo.get_kid(kid_id)
    if kid is None or not kid.active:
        repo.delete_pending_for_kid(kid_id, ctx.today, by=ctx.by)
    ensure_today(repo, ctx)
