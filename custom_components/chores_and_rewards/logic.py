"""Chore rules. Pure Python: no Home Assistant imports, so it is easy to test."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import StrEnum

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def is_valid_pin(pin: str, min_len: int = 4, max_len: int = 8) -> bool:
    """Return True if the PIN is min_len..max_len digits."""
    return pin.isdigit() and min_len <= len(pin) <= max_len


def hash_pin(pin: str) -> str:
    """Hash a PIN with a random salt. Format: scrypt$<salt hex>$<hash hex>."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(pin.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    """Check a PIN against a stored hash in constant time."""
    try:
        algo, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    digest = hashlib.scrypt(pin.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return hmac.compare_digest(digest.hex(), digest_hex)


# --- Domain model -------------------------------------------------------------


class ChoreType(StrEnum):
    EXPECTED = "expected"
    BONUS = "bonus"


class Slot(StrEnum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    ANYTIME = "anytime"


SLOT_ORDER = (Slot.MORNING, Slot.AFTERNOON, Slot.ANYTIME)


class Status(StrEnum):
    PENDING = "pending"
    DONE = "done"
    MISSED = "missed"
    EXCUSED = "excused"
    REJECTED = "rejected"


class CapMode(StrEnum):
    FIXED = "fixed"  # hard weekly max (per-kid override or currency default)
    POT = "pot"  # max = sum of the kid's scheduled chore values this week


class Actor(StrEnum):
    KID = "kid"
    PARENT = "parent"


@dataclass(frozen=True)
class Kid:
    id: int
    name: str
    sort: int = 0
    active: bool = True


@dataclass(frozen=True)
class Currency:
    id: int
    name: str
    unit: str
    payout_weekday: int  # 0 = Monday
    can_be_lost: bool
    cap_mode: CapMode = CapMode.FIXED
    default_max: int | None = None
    icon: str = ""
    active: bool = True
    sort: int = 0


@dataclass(frozen=True)
class Chore:
    id: int
    name: str
    type: ChoreType
    kid_ids: frozenset[int]
    weekdays: frozenset[int]  # 0 = Monday; empty = every day
    slot: Slot
    values: Mapping[int, int]  # currency_id -> value
    icon: str = ""
    description: str = ""
    active: bool = True
    sort: int = 0


@dataclass(frozen=True)
class Instance:
    """One chore for one kid on one day. Name and values are snapshotted (D6)."""

    kid_id: int
    chore_id: int
    day: date
    type: ChoreType
    slot: Slot
    name: str
    values: Mapping[int, int]
    status: Status = Status.PENDING
    icon: str = ""
    id: int | None = None  # set once stored


@dataclass(frozen=True)
class Balance:
    earned: int  # raw sum of done values
    lost: int  # sum of missed/rejected expected values (0 if the currency can't be lost)
    adjustments: int
    cap: int | None  # None = no cap
    total: int  # what the kid has: clamped to 0..cap


class RuleError(Exception):
    """A rule refused the action. `code` is stable and used by the API/UI."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


# --- Weeks and days -----------------------------------------------------------


def week_start(day: date) -> date:
    """Monday of the week containing `day`. Used as the week key."""
    return day - timedelta(days=day.weekday())


def week_days(start: date) -> list[date]:
    """The 7 dates Monday..Sunday from a week start."""
    return [start + timedelta(days=i) for i in range(7)]


def days_to_finalize(last_finalized: date | None, today: date) -> list[date]:
    """Past days not yet finalized, oldest first (catch-up if HA was off).

    `None` means a fresh install: nothing in the past to process.
    """
    if last_finalized is None:
        return []
    days = []
    d = last_finalized + timedelta(days=1)
    while d < today:
        days.append(d)
        d += timedelta(days=1)
    return days


def weeks_to_close(open_weeks: Iterable[date], today: date) -> list[date]:
    """Open week starts that have fully passed (D1: auto-close at Monday 00:00)."""
    current = week_start(today)
    return sorted(w for w in set(open_weeks) if w < current)


# --- Scheduling ---------------------------------------------------------------


def is_scheduled(chore: Chore, kid_id: int, day: date) -> bool:
    """True if this active chore is assigned to the kid on that weekday."""
    if not chore.active or kid_id not in chore.kid_ids:
        return False
    return not chore.weekdays or day.weekday() in chore.weekdays


def instances_for_day(chores: Iterable[Chore], kid_ids: Iterable[int], day: date) -> list[Instance]:
    """Fresh pending instances for every kid × scheduled chore on `day`."""
    kids = list(kid_ids)
    return [
        snapshot(chore, kid, day)
        for chore in chores
        for kid in kids
        if is_scheduled(chore, kid, day)
    ]


def snapshot(chore: Chore, kid_id: int, day: date) -> Instance:
    """Copy a chore's current definition onto a pending instance."""
    return Instance(
        kid_id=kid_id,
        chore_id=chore.id,
        day=day,
        type=chore.type,
        slot=chore.slot,
        name=chore.name,
        values=dict(chore.values),
        icon=chore.icon,
    )


def group_by_slot(instances: Iterable[Instance]) -> dict[Slot, list[Instance]]:
    """Expected instances grouped morning → afternoon → anytime (bonus excluded)."""
    groups: dict[Slot, list[Instance]] = {slot: [] for slot in SLOT_ORDER}
    for inst in instances:
        if inst.type is ChoreType.EXPECTED:
            groups[inst.slot].append(inst)
    return groups


# --- State transitions --------------------------------------------------------


def finalize(inst: Instance) -> Instance:
    """End of day: pending expected → missed. Bonus is never missed (AC-5.4)."""
    if inst.type is ChoreType.EXPECTED and inst.status is Status.PENDING:
        return replace(inst, status=Status.MISSED)
    return inst


def transition(
    inst: Instance, target: Status, actor: Actor, today: date, open_week: date | None = None
) -> Instance:
    """Apply a status change if the rules allow it, else raise RuleError.

    Kids: done/undo, today only (AC-6.1, AC-6.2).
    Parents: any day up to today in the open week (D8); reject only a completion (AC-7.4).
    """
    if inst.day > today:
        raise RuleError("future_day")
    if actor is Actor.KID:
        if inst.day != today:
            raise RuleError("not_today")
        allowed = {Status.PENDING: {Status.DONE}, Status.DONE: {Status.PENDING}}
        if target not in allowed.get(inst.status, set()):
            raise RuleError("not_allowed")
        return replace(inst, status=target)

    week = open_week if open_week is not None else week_start(today)
    if week_start(inst.day) != week:
        raise RuleError("week_closed")
    if target is Status.REJECTED and inst.status is not Status.DONE:
        raise RuleError("not_done")
    if target is Status.PENDING and inst.day != today:
        raise RuleError("not_today")
    if target is Status.MISSED and (inst.type is ChoreType.BONUS or inst.day == today):
        raise RuleError("not_allowed")
    return replace(inst, status=target)


# --- Balances -----------------------------------------------------------------


def _value(inst: Instance, currency_id: int) -> int:
    return inst.values.get(currency_id, 0)


def week_pot(
    instances: Iterable[Instance],
    chores: Iterable[Chore],
    kid_id: int,
    week: date,
    today: date,
    currency_id: int,
) -> int:
    """Sum of values on offer this week: snapshots up to today, schedule for later days."""
    total = sum(_value(i, currency_id) for i in instances if i.kid_id == kid_id)
    chore_list = list(chores)
    for day in week_days(week):
        if day > today:
            total += sum(
                chore.values.get(currency_id, 0)
                for chore in chore_list
                if is_scheduled(chore, kid_id, day)
            )
    return total


def resolve_cap(currency: Currency, kid_max: int | None, pot: int) -> int | None:
    """Weekly cap for one kid and currency (D4)."""
    if currency.cap_mode is CapMode.POT:
        return pot
    return kid_max if kid_max is not None else currency.default_max


def compute_balance(
    currency: Currency, instances: Iterable[Instance], adjustments: int, cap: int | None
) -> Balance:
    """Balance for one kid and currency over one week's instances (D5)."""
    earned = lost = 0
    for inst in instances:
        value = _value(inst, currency.id)
        if inst.status is Status.DONE:
            earned += value
        elif (
            currency.can_be_lost
            and inst.type is ChoreType.EXPECTED
            and inst.status in (Status.MISSED, Status.REJECTED)
        ):
            lost += value
    capped = earned if cap is None else min(earned, cap)
    total = max(0, capped - lost + adjustments)
    if cap is not None:
        total = min(total, cap)
    return Balance(earned=earned, lost=lost, adjustments=adjustments, cap=cap, total=total)


# --- Payout -------------------------------------------------------------------


def payout_warnings(chore: Chore, currencies: Iterable[Currency]) -> list[int]:
    """Currency ids this chore pays on a day after that currency's payout day (AC-5.5).

    A warning only; saving is never blocked.
    """
    days = chore.weekdays or frozenset(range(7))
    return [
        c.id
        for c in currencies
        if chore.values.get(c.id, 0) > 0 and any(d > c.payout_weekday for d in days)
    ]


def is_payout_day(currency: Currency, day: date) -> bool:
    return currency.active and day.weekday() == currency.payout_weekday
