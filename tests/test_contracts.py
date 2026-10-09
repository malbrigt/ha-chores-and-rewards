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
    ChoreType,
    Instance,
    RuleError,
    Slot,
    Status,
    transition,
)

ROOT = Path(__file__).parent.parent
FIXTURE = json.loads((ROOT / "tests/fixtures/parent_actions.json").read_text())
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
    error_codes = {"invalid_token", "wrong_pin", "locked_out", "not_found", "not_loaded"}
    documented -= error_codes | {"invalid_format"} | set(DEFAULT_SETTINGS)  # other tables
    registered = _registered_types()
    assert len(registered) >= 20
    assert documented == registered
