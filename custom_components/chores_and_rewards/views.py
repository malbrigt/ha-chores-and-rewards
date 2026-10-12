"""Read models: what the panel, sensors and payouts show, computed from the database.

Pure: no Home Assistant imports. Balances are computed for all kids at once from a
fixed number of queries, using the rules in logic.py (D4, D5).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .db import Repo
from .logic import (
    SLOT_ORDER,
    Balance,
    ChoreType,
    Instance,
    after_payout,
    compute_balance,
    instances_for_day,
    is_payout_day,
    payout_day,
    resolve_cap,
    taken_by,
    week_pot,
    week_start,
)


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
    taken: dict[int, int]  # instance id -> the kid who already did it (once a day, D51)


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
            taken={
                i.id: kid_id
                for i in mine
                if i.id is not None and (kid_id := taken_by(i, rows)) is not None
            },
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


@dataclass(frozen=True)
class PayoutItem:
    kid_id: int
    currency_id: int
    amount_due: int
    paid_amount: int | None
    paid_at: str | None
    after_payout: int
    payout_day: date
    is_payout_day: bool


def payout_items(repo: Repo, week: date, today: date) -> list[PayoutItem]:
    """Amount per kid and currency for a week, with paid state (AC-9.1, D11)."""
    paid = {(p["kid_id"], p["currency_id"]): p for p in repo.list_payouts(week)}
    currencies = repo.list_currencies()
    balances = week_balances(repo, week, today)
    current_week = week == week_start(today)
    items = []
    for kid in repo.list_kids():
        for c in currencies:
            record = paid.get((kid.id, c.id))
            due = balances[kid.id][c.id].total
            amount = record["amount"] if record else None
            items.append(
                PayoutItem(
                    kid_id=kid.id,
                    currency_id=c.id,
                    amount_due=due,
                    paid_amount=amount,
                    paid_at=record["done_at"] if record else None,
                    after_payout=after_payout(due, amount),
                    payout_day=payout_day(c, week),
                    is_payout_day=current_week and is_payout_day(c, today),
                )
            )
    return items
