"""Contracts between backend, frontend and docs, so they can't silently drift."""

import json
import re
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest

from custom_components.chores_and_rewards import websocket_api
from custom_components.chores_and_rewards.const import DOMAIN
from custom_components.chores_and_rewards.db import DEFAULT_SETTINGS
from custom_components.chores_and_rewards.logic import (
    Actor,
    Balance,
    ChoreType,
    Currency,
    Instance,
    RuleError,
    Slot,
    Status,
    earn_options,
    transition,
    undo_status,
)

ROOT = Path(__file__).parent.parent
FIXTURE = json.loads((ROOT / "tests/fixtures/parent_actions.json").read_text())
KID_FIXTURE = json.loads((ROOT / "tests/fixtures/kid_actions.json").read_text())
EARN_FIXTURE = json.loads((ROOT / "tests/fixtures/earn_options.json").read_text())
TODAY = date(2026, 10, 9)  # Friday, so "yesterday" is in the same week


@pytest.mark.parametrize(
    "case", FIXTURE["cases"], ids=lambda c: f"{c['type']}-{c['status']}-{c['day']}"
)
def test_parent_actions_match_transition(case):
    """panel.js parentActions is tested against the same fixture (tests/js)."""
    inst = Instance(
        kid_id=1,
        chore_id=1,
        day=TODAY + timedelta(days=case["day"]),
        type=ChoreType(case["type"]),
        slot=Slot.AFTERNOON,
        name="x",
        values={},
        status=Status(case["status"]),
        id=1,
    )
    allowed = []
    for target in FIXTURE["order"]:
        if target == case["status"]:
            continue
        try:
            transition(replace(inst), Status(target), Actor.PARENT, TODAY)
        except RuleError:
            continue
        allowed.append(target)
    assert allowed == case["actions"]


def _allowed(inst: Instance, target: Status) -> bool:
    try:
        transition(inst, target, Actor.KID, TODAY)
    except RuleError:
        return False
    return True


@pytest.mark.parametrize(
    "case", KID_FIXTURE["cases"], ids=lambda c: f"{c['type']}-{c['status']}-{c['day']}"
)
def test_kid_tap_matches_transition(case):
    """panel.js kidTap is tested against the same fixture (tests/js)."""
    inst = Instance(
        kid_id=1,
        chore_id=1,
        day=TODAY + timedelta(days=case["day"]),
        type=ChoreType(case["type"]),
        slot=Slot.AFTERNOON,
        name="x",
        values={},
        status=Status(case["status"]),
        id=1,
    )
    if inst.status is Status.DONE:
        tap = "untick" if _allowed(inst, undo_status(inst, TODAY)) else None
    else:
        tap = "tick" if _allowed(inst, Status.DONE) else None
    assert tap == case["tap"]


@pytest.mark.parametrize("case", EARN_FIXTURE["cases"])
def test_earn_options_match_fixture(case):
    """AC-6.6. panel.js earnOptions is tested against the same fixture (tests/js)."""
    currencies = [
        Currency(c["id"], "x", "u", payout_weekday=4, can_be_lost=c["can_be_lost"])
        for c in EARN_FIXTURE["currencies"]
    ]
    balances = {
        int(cid): Balance(earned=0, lost=lost, refilled=ref, adjustments=0, cap=None, total=0)
        for cid, (lost, ref) in case["balances"].items()
    }
    inst = Instance(
        kid_id=1,
        chore_id=1,
        day=TODAY,
        type=ChoreType.BONUS,
        slot=Slot.ANYTIME,
        name="x",
        values={int(k): v for k, v in case["values"].items()},
    )
    assert earn_options(inst, currencies, balances) == case["options"]


def _registered_types() -> set[str]:
    types = set()
    for name in dir(websocket_api):
        func = getattr(websocket_api, name)
        command = getattr(func, "_ws_command", None)
        if isinstance(command, str) and command.startswith(f"{DOMAIN}/"):
            types.add(command.removeprefix(f"{DOMAIN}/"))
    return types


def test_ws_doc_lists_every_command():
    """docs/ws-api.md must document exactly the commands the code registers."""
    doc = (ROOT / "docs/ws-api.md").read_text()
    documented = set(re.findall(r"^\| `([a-z_/]+)` \|", doc, flags=re.M))
    error_codes = {
        "invalid_token",
        "wrong_pin",
        "locked_out",
        "not_found",
        "duplicate_name",
        "not_loaded",
    }
    documented -= error_codes | {"invalid_format"} | set(DEFAULT_SETTINGS)  # other tables
    registered = _registered_types()
    assert len(registered) >= 20
    assert documented == registered


def test_panel_labels_every_audit_action():
    """Every AuditAction has an nb label in the panel's log (D46)."""
    from custom_components.chores_and_rewards.audit import AuditAction

    panel = (ROOT / "custom_components/chores_and_rewards/frontend/panel.js").read_text()
    missing = [a.value for a in AuditAction if f"a_{a.value}:" not in panel]
    assert missing == []


def test_ws_doc_lists_every_audit_action():
    from custom_components.chores_and_rewards.audit import AuditAction

    doc = (ROOT / "docs/ws-api.md").read_text().split("## Audit actions")[1]
    assert set(re.findall(r"`([a-z_]+)`", doc)) == {a.value for a in AuditAction}
