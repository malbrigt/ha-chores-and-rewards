"""JSON shapes for the domain objects: one function per type, used everywhere.

The WebSocket API, the audit log payloads (D46) and the replay test all use these, so
the shapes can't drift apart. Pure: no Home Assistant imports. Maps keyed by id use
string keys (JSON).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .logic import Balance, Chore, Currency, Instance, Kid


def kid_json(kid: Kid, max_: dict[int, int] | None = None) -> dict[str, Any]:
    out = asdict(kid)
    if max_ is not None:
        out["max"] = {str(k): v for k, v in max_.items()}
    return out


def currency_json(c: Currency) -> dict[str, Any]:
    return {**asdict(c), "cap_mode": c.cap_mode.value}


def chore_json(c: Chore) -> dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "icon": c.icon,
        "description": c.description,
        "chore_type": c.type.value,  # "type" is taken by the WebSocket envelope (D27)
        "slot": c.slot.value,
        "weekdays": sorted(c.weekdays),
        "kid_ids": sorted(c.kid_ids),
        "values": {str(k): v for k, v in c.values.items()},
        "active": c.active,
        "sort": c.sort,
        "once_a_day": c.once_a_day,
    }


def instance_json(i: Instance) -> dict[str, Any]:
    """Everything needed to recreate an instance row (also the audit snapshot, D46)."""
    return {
        "id": i.id,
        "kid_id": i.kid_id,
        "chore_id": i.chore_id,
        "day": i.day.isoformat(),
        "type": i.type.value,
        "slot": i.slot.value,
        "name": i.name,
        "icon": i.icon,
        "values": {str(k): v for k, v in i.values.items()},
        "status": i.status.value,
        "currency_id": i.currency_id,
        "once_a_day": i.once_a_day,
    }


def balance_json(b: Balance) -> dict[str, Any]:
    return asdict(b)


def balances_json(balances: dict[int, Balance]) -> dict[str, Any]:
    return {str(cid): balance_json(b) for cid, b in balances.items()}
