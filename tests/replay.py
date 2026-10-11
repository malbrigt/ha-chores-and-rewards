"""Rebuild the integration's state from the audit log alone (D46).

`replay(entries)` folds audit rows (oldest first) into a plain-dict state; `snapshot(repo)`
reads the same shape from the database through the same serializers the audit payloads
use. test_replay asserts they are equal, so any write that is not audited (or audited
without enough data) fails the test.
"""

import json
from typing import Any

from custom_components.chores_and_rewards.audit import STATUS_ACTIONS, USAGE_ONLY, AuditAction
from custom_components.chores_and_rewards.db import DEFAULT_SETTINGS, Repo, _currency, _kid
from custom_components.chores_and_rewards.serialize import (
    chore_json,
    currency_json,
    instance_json,
    kid_json,
)

A = AuditAction


def _without_id(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if k not in ("id", "max")}


def replay(entries: list[dict[str, Any]]) -> dict[str, Any]:
    st: dict[str, Any] = {
        "kids": {},
        "kid_max": {},
        "currencies": {},
        "chores": {},
        "settings": dict(DEFAULT_SETTINGS),
        "weeks": {},
        "instances": {},
        "adjustments": {},
        "payouts": {},
        "last_finalized": None,
    }
    deleted_table = {"kid": "kids", "currency": "currencies", "chore": "chores"}
    for e in sorted(entries, key=lambda e: e["id"]):
        action, eid = AuditAction(e["action"]), e["entity_id"]
        after = json.loads(e["after"]) if e["after"] else None
        if action is A.KID_SAVE:
            st["kids"][eid] = {**_without_id(after), "deleted": False}
            st["kid_max"] = {k: v for k, v in st["kid_max"].items() if k[0] != eid}
            st["kid_max"].update({(eid, int(c)): m for c, m in after["max"].items()})
        elif action in (A.KID_DELETE, A.CURRENCY_DELETE, A.CHORE_DELETE):
            st[deleted_table[e["entity"]]][eid]["deleted"] = True
        elif action is A.CURRENCY_SAVE:
            st["currencies"][eid] = {**_without_id(after), "deleted": False}
        elif action is A.CHORE_SAVE:
            st["chores"][eid] = {**_without_id(after), "deleted": False}
        elif action is A.SETTINGS_SAVE:
            st["settings"] = after
        elif action in (A.WEEK_OPEN, A.REOPEN_WEEK):
            st["weeks"][e["day"]] = "open"
        elif action is A.CLOSE_WEEK:
            st["weeks"][e["day"]] = "closed"
        elif action in (A.INSTANCE_CREATE, A.INSTANCE_UPDATE):
            st["instances"][eid] = _without_id(after)
        elif action is A.INSTANCE_DELETE:
            del st["instances"][eid]
        elif action in STATUS_ACTIONS:
            st["instances"][eid]["status"] = after["status"]
            st["instances"][eid]["currency_id"] = after.get("currency_id")  # D49
        elif action is A.ADJUST:
            st["adjustments"][eid] = {
                "week": after["week"],
                "kid_id": e["kid_id"],
                "currency_id": after["currency_id"],
                "amount": after["amount"],
                "note": e["note"],
            }
        elif action is A.PAYOUT:
            st["payouts"][(after["week"], e["kid_id"], after["currency_id"])] = after["amount"]
        elif action is A.PAYOUT_UNDO:
            del st["payouts"][(after["week"], e["kid_id"], after["currency_id"])]
        elif action is A.ROLLOVER:
            st["last_finalized"] = after["last_finalized"]
        else:
            assert action in USAGE_ONLY, f"replay doesn't handle {action}"
    return st


def snapshot(repo: Repo) -> dict[str, Any]:
    """The same shape as replay(), read straight from the tables (deleted rows too)."""
    q = lambda sql: repo.conn.execute(sql).fetchall()  # noqa: E731
    chore_rows = q("SELECT * FROM chores")
    chores = {c.id: c for c in repo._chores(chore_rows)}
    last = repo.last_finalized()
    return {
        "kids": {
            r["id"]: {**_without_id(kid_json(_kid(r))), "deleted": r["deleted_at"] is not None}
            for r in q("SELECT * FROM kids")
        },
        "kid_max": repo.all_kid_max(),
        "currencies": {
            r["id"]: {
                **_without_id(currency_json(_currency(r))),
                "deleted": r["deleted_at"] is not None,
            }
            for r in q("SELECT * FROM currencies")
        },
        "chores": {
            r["id"]: {
                **_without_id(chore_json(chores[r["id"]])),
                "deleted": r["deleted_at"] is not None,
            }
            for r in chore_rows
        },
        "settings": repo.get_settings(),
        "weeks": {r["start"]: r["status"] for r in q("SELECT * FROM weeks")},
        "instances": {i.id: _without_id(instance_json(i)) for i in repo.list_instances()},
        "adjustments": {
            r["id"]: {k: r[k] for k in ("week", "kid_id", "currency_id", "amount", "note")}
            for r in q("SELECT * FROM adjustments")
        },
        "payouts": {
            (r["week"], r["kid_id"], r["currency_id"]): r["amount"]
            for r in q("SELECT * FROM payouts")
        },
        "last_finalized": last.isoformat() if last else None,
    }
