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

# Longest cooldown for an extra chore: two weeks. Also a CHECK in the schema (D51).
MAX_COOLDOWN_DAYS = 14


class Status(StrEnum):
    PENDING = "pending"
    DONE = "done"
    MISSED = "missed"
    EXCUSED = "excused"
    REJECTED = "rejected"


class CapMode(StrEnum):
    FIXED = "fixed"  # hard weekly max (per-kid override or currency default)
    POT = "pot"  # max = sum of the kid's scheduled chore values this week


class WeekStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


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
    decimals: int = 0  # amounts are integers in this minor unit: 2 → cents (D50)


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
    # Extras only: done on day D, by any kid → open again on day D + this (0 = no limit, D51).
    cooldown_days: int = 0
    can_tick_ahead: bool = False  # expected only: may be ticked on a future day (D52)


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
    status_at: str | None = None  # ISO UTC time of the last status change
    currency_id: int | None = None  # extra chores: the one currency it earns (D49)
    cooldown_days: int = 0  # snapshot of Chore.cooldown_days (D51)


@dataclass(frozen=True)
class Balance:
    earned: int  # raw sum of done values
    lost: int  # sum of missed/rejected expected values (0 if the currency can't be lost)
    refilled: int  # won back by extra chores, never more than `lost` (D49)
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


def tick_ahead_until(today: date) -> date:
    """Last day a chore may be ticked ahead: Sunday of next week (D52)."""
    return week_start(today) + timedelta(days=13)


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
        cooldown_days=chore.cooldown_days,
    )


def cooldown_span(day: date, cooldown_days: int) -> tuple[date, date]:
    """First and last day on which a completion would put a row on `day` on cooldown."""
    reach = timedelta(days=max(cooldown_days - 1, 0))
    return day - reach, day + reach


def on_cooldown(inst: Instance, rows: Iterable[Instance]) -> Instance | None:
    """The done row that keeps `inst` on cooldown (the nearest one), or None if it is free.

    A chore done on day D can be done again on day D + cooldown_days, whoever did it (D51).
    So another row of the same chore that is done fewer days away than that blocks this
    one. Both directions count: a late tick for an earlier day is blocked by a later
    completion too, which keeps any two completions at least cooldown_days apart. With
    1, only the other kids' rows of the same day are blocked. A done row is never blocked.
    """
    if not inst.cooldown_days or inst.status is Status.DONE:
        return None

    def days_away(other: Instance) -> int:
        return abs((other.day - inst.day).days)

    blocking = [
        i
        for i in rows
        if i.chore_id == inst.chore_id
        and i.status is Status.DONE
        and (i.kid_id, i.day) != (inst.kid_id, inst.day)
        and days_away(i) < inst.cooldown_days
    ]
    return min(blocking, key=lambda i: (days_away(i), i.day, i.kid_id), default=None)


# --- State transitions --------------------------------------------------------


def finalize(inst: Instance) -> Instance:
    """End of day: pending expected → missed. Bonus is never missed (AC-5.4)."""
    if inst.type is ChoreType.EXPECTED and inst.status is Status.PENDING:
        return replace(inst, status=Status.MISSED)
    return inst


def undo_status(inst: Instance, today: date) -> Status:
    """What a done chore becomes when unticked: open today, ahead or bonus, else missed again."""
    if inst.day >= today or inst.type is ChoreType.BONUS:
        return Status.PENDING
    return Status.MISSED


def is_late(day: date, changed_on: date) -> bool:
    """A change made after the chore's own day, e.g. a forgotten tick fixed later (D43)."""
    return changed_on > day


def transition(
    inst: Instance, target: Status, actor: Actor, today: date, can_tick_ahead: bool = False
) -> Instance:
    """Apply a status change if the rules allow it, else raise RuleError.

    Both kids and parents: any day up to today in the open week (D8).
    Kids: tick (pending/missed → done) or untick (done → undo_status) (AC-6.1, AC-6.2).
    Parents: also excuse, reject a completion (AC-7.4), reset today or mark a past day missed.
    Ahead (D52): a chore that allows it may be ticked, unticked, rejected or reset on a
    future day up to `tick_ahead_until`; nothing else happens to a day that hasn't come.
    """
    if inst.day > today and not (
        can_tick_ahead
        and inst.day <= tick_ahead_until(today)
        and target in (Status.DONE, Status.REJECTED, Status.PENDING)
    ):
        raise RuleError("future_day")
    if week_start(inst.day) < week_start(today):
        raise RuleError("week_closed")

    if actor is Actor.KID:
        tick = target is Status.DONE and inst.status in (Status.PENDING, Status.MISSED)
        untick = inst.status is Status.DONE and target is undo_status(inst, today)
        if not (tick or untick):
            raise RuleError("not_allowed")
        return replace(inst, status=target)

    if target is Status.REJECTED and inst.status is not Status.DONE:
        raise RuleError("not_done")
    if target is Status.PENDING and inst.day < today:
        raise RuleError("not_today")
    if target is Status.MISSED and (inst.type is ChoreType.BONUS or inst.day == today):
        raise RuleError("not_allowed")
    return replace(inst, status=target)


# --- Balances -----------------------------------------------------------------


def _value(inst: Instance, currency_id: int) -> int:
    """What the instance is worth in a currency. An extra earns only its chosen one (D49)."""
    if inst.currency_id is not None and inst.currency_id != currency_id:
        return 0
    return inst.values.get(currency_id, 0)


def week_pot(
    instances: Iterable[Instance],
    chores: Iterable[Chore],
    kid_id: int,
    week: date,
    today: date,
    currency_id: int,
) -> int:
    """Sum of values on offer this week: stored rows (snapshots, and chores ticked ahead,
    D52), plus the schedule for later days that have no row yet."""
    mine = [i for i in instances if i.kid_id == kid_id]
    total = sum(_value(i, currency_id) for i in mine)
    stored = {(i.chore_id, i.day) for i in mine}
    chore_list = list(chores)
    for day in week_days(week):
        if day > today:
            total += sum(
                chore.values.get(currency_id, 0)
                for chore in chore_list
                if is_scheduled(chore, kid_id, day) and (chore.id, day) not in stored
            )
    return total


def major_units(amount: int, decimals: int) -> int | float:
    """A stored minor-unit amount as a plain number for display: 150, 2 → 1.5 (D50)."""
    return amount / 10**decimals if decimals else amount


def resolve_cap(currency: Currency, kid_max: int | None, pot: int) -> int | None:
    """Weekly cap for one kid and currency (D4)."""
    if currency.cap_mode is CapMode.POT:
        return pot
    return kid_max if kid_max is not None else currency.default_max


def compute_balance(
    currency: Currency, instances: Iterable[Instance], adjustments: int, cap: int | None
) -> Balance:
    """Balance for one kid and currency over one week's instances (D5).

    Extra chores in a currency that can be lost only refill what was lost (D49).
    """
    earned = lost = refill = 0
    for inst in instances:
        value = _value(inst, currency.id)
        if inst.status is Status.DONE:
            if inst.type is ChoreType.BONUS and currency.can_be_lost:
                refill += value
            else:
                earned += value
        elif (
            currency.can_be_lost
            and inst.type is ChoreType.EXPECTED
            and inst.status in (Status.MISSED, Status.REJECTED)
        ):
            lost += value
    refilled = min(refill, lost)
    capped = earned if cap is None else min(earned, cap)
    total = max(0, capped - lost + refilled + adjustments)
    if cap is not None:
        total = min(total, cap)
    return Balance(
        earned=earned,
        lost=lost,
        refilled=refilled,
        adjustments=adjustments,
        cap=cap,
        total=total,
    )


def earn_options(
    inst: Instance, currencies: Iterable[Currency], balances: Mapping[int, Balance]
) -> list[int]:
    """Currencies a done extra chore may earn, payment first, then refills (D49).

    A currency that can't be lost is payment and always on offer. One that can be lost is
    refill only: on offer while the kid still has some of it to win back this week.
    """
    payment, refill = [], []
    for c in currencies:
        if inst.values.get(c.id, 0) <= 0:
            continue
        if not c.can_be_lost:
            payment.append(c.id)
        elif (b := balances.get(c.id)) is not None and b.lost > b.refilled:
            refill.append(c.id)
    return payment + refill


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


def payout_day(currency: Currency, week: date) -> date:
    """The date in `week` when this currency is paid out."""
    return week + timedelta(days=currency.payout_weekday)


def after_payout(amount_due: int, paid: int | None) -> int:
    """Earned since the payout was ticked; the parent settles it by hand (§5, D11)."""
    return max(0, amount_due - paid) if paid is not None else 0
