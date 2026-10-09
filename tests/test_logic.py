"""Domain rules in logic.py. Pure: no hass fixture needed."""

from dataclasses import replace
from datetime import date

import pytest

from custom_components.chores_and_rewards.logic import (
    Actor,
    CapMode,
    Chore,
    ChoreType,
    Currency,
    RuleError,
    Slot,
    Status,
    compute_balance,
    days_to_finalize,
    finalize,
    group_by_slot,
    instances_for_day,
    is_payout_day,
    is_scheduled,
    payout_warnings,
    resolve_cap,
    snapshot,
    transition,
    week_days,
    week_pot,
    week_start,
    weeks_to_close,
)

SCREEN = Currency(1, "Screen time", "min", payout_weekday=4, can_be_lost=True, default_max=120)
MONEY = Currency(2, "Allowance", "NOK", payout_weekday=5, can_be_lost=False, cap_mode=CapMode.POT)

MON = date(2026, 10, 5)
TUE = date(2026, 10, 6)
SUN = date(2026, 10, 11)

DISHES = Chore(
    1,
    "Dishes",
    ChoreType.EXPECTED,
    kid_ids=frozenset({10, 11}),
    weekdays=frozenset({0, 1, 2, 3, 4}),
    slot=Slot.AFTERNOON,
    values={1: 30, 2: 10},
)
BED = Chore(2, "Make bed", ChoreType.EXPECTED, frozenset({10}), frozenset(), Slot.MORNING, {1: 10})
WINDOWS = Chore(
    3, "Windows", ChoreType.BONUS, frozenset({10}), frozenset({5}), Slot.ANYTIME, {2: 50}
)


def inst(chore=DISHES, kid=10, day=MON, status=Status.PENDING):
    return replace(snapshot(chore, kid, day), status=status)


# --- weeks --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("day", "monday"),
    [
        (MON, MON),
        (SUN, MON),
        (date(2026, 12, 31), date(2026, 12, 28)),  # year boundary
        (date(2027, 1, 3), date(2026, 12, 28)),
        (date(2026, 10, 25), date(2026, 10, 19)),  # DST change day (Oslo)
        (date(2026, 3, 29), date(2026, 3, 23)),
    ],
)
def test_week_start(day, monday):
    assert week_start(day) == monday


def test_week_days():
    days = week_days(MON)
    assert days[0] == MON and days[-1] == SUN and len(days) == 7


def test_days_to_finalize_normal_and_catch_up():
    """AC-6.3: each missed day processed in order, exactly once."""
    assert days_to_finalize(None, TUE) == []
    assert days_to_finalize(MON, TUE) == []
    assert days_to_finalize(date(2026, 10, 4), TUE) == [MON]
    gap = days_to_finalize(date(2026, 10, 2), TUE)  # off Fri..Mon
    assert gap == [date(2026, 10, 3), date(2026, 10, 4), MON]
    assert days_to_finalize(TUE, TUE) == []


def test_days_to_finalize_year_boundary():
    assert days_to_finalize(date(2026, 12, 30), date(2027, 1, 2)) == [
        date(2026, 12, 31),
        date(2027, 1, 1),
    ]


def test_weeks_to_close():
    """AC-9.2 / D1: weeks before the current one are closed."""
    prev = date(2026, 9, 28)
    assert weeks_to_close([prev, MON], TUE) == [prev]
    assert weeks_to_close([MON], SUN) == []
    assert weeks_to_close([prev, date(2026, 9, 21), prev], MON) == [date(2026, 9, 21), prev]


# --- scheduling ---------------------------------------------------------------


def test_is_scheduled():
    """AC-5.1."""
    assert is_scheduled(DISHES, 10, MON)
    assert not is_scheduled(DISHES, 10, SUN)  # weekday not set
    assert not is_scheduled(DISHES, 99, MON)  # not assigned
    assert not is_scheduled(replace(DISHES, active=False), 10, MON)
    assert is_scheduled(BED, 10, SUN)  # empty weekdays = every day


def test_instances_for_day_snapshots():
    out = instances_for_day([DISHES, BED, WINDOWS], [10, 11], MON)
    assert {(i.chore_id, i.kid_id) for i in out} == {(1, 10), (1, 11), (2, 10)}
    assert all(i.status is Status.PENDING and i.day == MON for i in out)


def test_snapshot_is_independent_of_later_edits():
    """AC-5.6."""
    values = {1: 30}
    chore = replace(DISHES, values=values)
    i = snapshot(chore, 10, MON)
    values[1] = 999
    assert i.values == {1: 30}


def test_group_by_slot_order_and_bonus_excluded():
    """AC-8.1."""
    items = [inst(DISHES), inst(BED), inst(WINDOWS, day=date(2026, 10, 10))]
    groups = group_by_slot(items)
    assert list(groups) == [Slot.MORNING, Slot.AFTERNOON, Slot.ANYTIME]
    assert [i.name for i in groups[Slot.MORNING]] == ["Make bed"]
    assert [i.name for i in groups[Slot.AFTERNOON]] == ["Dishes"]
    assert groups[Slot.ANYTIME] == []


# --- transitions --------------------------------------------------------------


def test_finalize():
    """AC-5.3, AC-5.4."""
    assert finalize(inst()).status is Status.MISSED
    assert finalize(inst(status=Status.DONE)).status is Status.DONE
    assert finalize(inst(WINDOWS)).status is Status.PENDING


def test_kid_done_and_undo_today():
    """AC-6.1, AC-6.2."""
    done = transition(inst(), Status.DONE, Actor.KID, today=MON)
    assert done.status is Status.DONE
    assert transition(done, Status.PENDING, Actor.KID, today=MON).status is Status.PENDING


@pytest.mark.parametrize(
    ("status", "target", "today", "code"),
    [
        (Status.DONE, Status.PENDING, TUE, "not_today"),  # undo past day
        (Status.PENDING, Status.DONE, TUE, "not_today"),
        (Status.MISSED, Status.DONE, MON, "not_allowed"),
        (Status.PENDING, Status.EXCUSED, MON, "not_allowed"),
        (Status.PENDING, Status.DONE, date(2026, 10, 4), "future_day"),
    ],
)
def test_kid_refusals(status, target, today, code):
    with pytest.raises(RuleError) as err:
        transition(inst(status=status), target, Actor.KID, today=today)
    assert err.value.code == code


def test_parent_can_edit_past_days_in_open_week():
    """D8, AC-7.4, AC-7.5."""
    missed = inst(status=Status.MISSED)
    assert transition(missed, Status.DONE, Actor.PARENT, today=TUE).status is Status.DONE
    assert transition(missed, Status.EXCUSED, Actor.PARENT, today=TUE).status is Status.EXCUSED
    done = inst(status=Status.DONE)
    assert transition(done, Status.REJECTED, Actor.PARENT, today=TUE).status is Status.REJECTED
    excused = inst(status=Status.EXCUSED)
    assert transition(excused, Status.MISSED, Actor.PARENT, today=TUE).status is Status.MISSED
    today_done = inst(day=TUE, status=Status.DONE)
    assert transition(today_done, Status.PENDING, Actor.PARENT, today=TUE).status is Status.PENDING


@pytest.mark.parametrize(
    ("instance", "target", "today", "code"),
    [
        (inst(status=Status.PENDING), Status.REJECTED, TUE, "not_done"),
        (inst(status=Status.MISSED), Status.PENDING, TUE, "not_today"),
        (inst(day=TUE), Status.MISSED, TUE, "not_allowed"),  # can't miss before midnight
        (inst(WINDOWS, day=date(2026, 10, 10)), Status.MISSED, SUN, "not_allowed"),
        (inst(day=date(2026, 9, 30)), Status.DONE, TUE, "week_closed"),
        (inst(day=date(2026, 10, 7)), Status.DONE, TUE, "future_day"),
    ],
)
def test_parent_refusals(instance, target, today, code):
    with pytest.raises(RuleError) as err:
        transition(instance, target, Actor.PARENT, today=today)
    assert err.value.code == code


def test_parent_explicit_open_week():
    old = inst(day=date(2026, 9, 30), status=Status.MISSED)
    out = transition(old, Status.EXCUSED, Actor.PARENT, today=TUE, open_week=date(2026, 9, 28))
    assert out.status is Status.EXCUSED


# --- balances -----------------------------------------------------------------


def test_balance_earn():
    """AC-3.1, AC-5.2."""
    assert compute_balance(SCREEN, [], 0, 120).total == 0
    b = compute_balance(SCREEN, [inst(status=Status.DONE)], 0, 120)
    assert (b.earned, b.lost, b.total) == (30, 0, 30)


def test_balance_loss_floors_at_zero():
    """AC-3.2."""
    b = compute_balance(
        SCREEN, [inst(status=Status.MISSED), inst(BED, status=Status.MISSED)], 0, 120
    )
    assert b.lost == 40 and b.total == 0
    items = [inst(status=Status.DONE), inst(BED, status=Status.MISSED)]
    assert compute_balance(SCREEN, items, 0, 120).total == 20


def test_balance_cannot_be_lost():
    """AC-3.3."""
    items = [inst(status=Status.DONE), inst(day=TUE, status=Status.MISSED)]
    b = compute_balance(MONEY, items, 0, None)
    assert (b.lost, b.total) == (0, 10)


def test_rejected_counts_as_missed_excused_is_neutral():
    """AC-7.4, AC-7.5."""
    assert compute_balance(SCREEN, [inst(status=Status.REJECTED)], 0, 120).lost == 30
    b = compute_balance(SCREEN, [inst(status=Status.EXCUSED)], 0, 120)
    assert (b.earned, b.lost, b.total) == (0, 0, 0)


def test_rejected_bonus_never_costs():
    b = compute_balance(
        SCREEN, [inst(replace(WINDOWS, values={1: 20}), status=Status.REJECTED)], 0, None
    )
    assert b.lost == 0


def test_balance_fixed_cap_then_loss():
    """AC-4.1: cap earnings first, then subtract losses."""
    done = [inst(day=MON.replace(day=5 + i), status=Status.DONE) for i in range(5)]  # 150
    b = compute_balance(SCREEN, done, 0, 120)
    assert (b.earned, b.total) == (150, 120)
    b = compute_balance(SCREEN, [*done, inst(BED, status=Status.MISSED)], 0, 120)
    assert b.total == 110


def test_balance_adjustments_clamped():
    """AC-7.6 / D5: adjustments apply after the cap; total stays within 0..cap."""
    done = [inst(status=Status.DONE)]
    assert compute_balance(SCREEN, done, 15, 120).total == 45
    assert compute_balance(SCREEN, done, -100, 120).total == 0
    assert compute_balance(SCREEN, done, 500, 120).total == 120
    assert compute_balance(MONEY, done, 500, None).total == 510


def test_resolve_cap():
    """AC-4.1, AC-4.2, AC-4.3."""
    assert resolve_cap(SCREEN, None, pot=999) == 120
    assert resolve_cap(SCREEN, 60, pot=999) == 60
    assert resolve_cap(replace(SCREEN, default_max=None), None, pot=999) is None
    assert resolve_cap(MONEY, 60, pot=80) == 80


def test_week_pot_uses_snapshots_then_schedule():
    """AC-4.2: past days from snapshots, future days from the current schedule."""
    # today = Tue. Mon, Tue snapshots (old value 5); Wed-Fri dishes at 10; Sat windows 50.
    old = [inst(replace(DISHES, values={2: 5}), day=d) for d in (MON, TUE)]
    other_kid = inst(kid=11)
    pot = week_pot([*old, other_kid], [DISHES, WINDOWS], 10, MON, TUE, currency_id=2)
    assert pot == 5 + 5 + 3 * 10 + 50


# --- payout -------------------------------------------------------------------


def test_payout_warnings():
    """AC-5.5: warn if a currency is earned after its payout day."""
    assert payout_warnings(DISHES, [SCREEN, MONEY]) == []  # Mon-Fri
    weekend = replace(DISHES, weekdays=frozenset({6}))
    assert payout_warnings(weekend, [SCREEN, MONEY]) == [1, 2]
    saturday = replace(DISHES, weekdays=frozenset({5}))
    assert payout_warnings(saturday, [SCREEN, MONEY]) == [1]  # Sat is payout day for money
    assert payout_warnings(BED, [SCREEN, MONEY]) == [1]  # every day; pays screen only
    assert payout_warnings(replace(saturday, values={1: 0}), [SCREEN]) == []


def test_is_payout_day():
    assert is_payout_day(SCREEN, date(2026, 10, 9))
    assert not is_payout_day(SCREEN, MON)
    assert not is_payout_day(replace(SCREEN, active=False), date(2026, 10, 9))


def test_rule_error_code():
    assert str(RuleError("x")) == "x" and RuleError("x").code == "x"
