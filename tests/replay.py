"""Rebuild the integration's state from the audit log alone (D46).

`replay(entries)` folds audit rows (oldest first) into a plain-dict state; `snapshot(repo)`
reads the same shape from the database. test_replay asserts they are equal, so any write
that is not audited (or audited without enough data) fails the test.
"""

import json
from typing import Any

from custom_components.chores_and_rewards.db import (
    DEFAULT_SETTINGS,
    Repo,
    instance_snapshot,
    mask_to_weekdays,
)

# Audited events that change no stored state (usage only).
NO_STATE = {"db_created", "pin_unlock", "pin_wrong_pin", "pin_locked_out", "pin_lock", "pin_reset"}
STATUS_EVENTS = {"check", "uncheck", "set_status", "auto_missed"}


def _chore(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": c["name"],
        "icon": c["icon"],
        "description": c["description"],
        "type": c["chore_type"],
        "slot": c["slot"],
        "weekdays": sorted(c["weekdays"]),
        "kid_ids": sorted(c["kid_ids"]),
        "values": {str(k): v for k, v in c["values"].items()},
        "active": bool(c["active"]),
        "sort": c["sort"],
    }


def _currency(c: dict[str, Any]) -> dict[str, Any]:
    keys = ("name", "unit", "icon", "payout_weekday", "cap_mode", "default_max", "sort")
    return {
        **{k: c[k] for k in keys},
        "can_be_lost": bool(c["can_be_lost"]),
        "active": bool(c["active"]),
    }


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
    unknown = set()
    for e in sorted(entries, key=lambda e: e["id"]):
        action, eid = e["action"], e["entity_id"]
        after = json.loads(e["after"]) if e["after"] else None
        if action == "kid_save":
            st["kids"][eid] = {
                "name": after["name"],
                "sort": after["sort"],
                "active": after["active"],
                "deleted": False,
            }
            st["kid_max"] = {k: v for k, v in st["kid_max"].items() if k[0] != eid}
            st["kid_max"].update({(eid, int(c)): m for c, m in after["max"].items()})
        elif action in ("kid_delete", "currency_delete", "chore_delete"):
            table = {"kid": "kids", "currency": "currencies", "chore": "chores"}[e["entity"]]
            st[table][eid]["deleted"] = True
        elif action == "currency_save":
            st["currencies"][eid] = {**_currency(after), "deleted": False}
        elif action == "chore_save":
            st["chores"][eid] = {**_chore(after), "deleted": False}
        elif action == "settings_save":
            st["settings"] = after
        elif action in ("week_open", "reopen_week"):
            st["weeks"][e["day"]] = "open"
        elif action == "close_week":
            st["weeks"][e["day"]] = "closed"
        elif action in ("instance_create", "instance_update"):
            st["instances"][eid] = {k: v for k, v in after.items() if k != "id"}
        elif action == "instance_delete":
            del st["instances"][eid]
        elif action in STATUS_EVENTS:
            st["instances"][eid]["status"] = after["status"]
        elif action == "adjust":
            st["adjustments"][eid] = {
                "week": after["week"],
                "kid_id": e["kid_id"],
                "currency_id": after["currency_id"],
                "amount": after["amount"],
                "note": e["note"],
            }
        elif action == "payout":
            st["payouts"][(after["week"], e["kid_id"], after["currency_id"])] = after["amount"]
        elif action == "payout_undo":
            del st["payouts"][(after["week"], e["kid_id"], after["currency_id"])]
        elif action == "rollover":
            st["last_finalized"] = after["last_finalized"]
        elif action not in NO_STATE:
            unknown.add(action)
    assert not unknown, f"replay doesn't know these audit actions: {unknown}"
    return st


def snapshot(repo: Repo) -> dict[str, Any]:
    """The same shape as replay(), read straight from the tables."""
    q = lambda sql: [dict(r) for r in repo.conn.execute(sql)]  # noqa: E731
    kids_of: dict[int, list[int]] = {}
    for r in q("SELECT chore_id, kid_id FROM chore_kids"):
        kids_of.setdefault(r["chore_id"], []).append(r["kid_id"])
    values_of: dict[int, dict[str, int]] = {}
    for r in q("SELECT chore_id, currency_id, value FROM chore_values"):
        values_of.setdefault(r["chore_id"], {})[str(r["currency_id"])] = r["value"]
    last = repo.last_finalized()
    return {
        "kids": {
            r["id"]: {
                "name": r["name"],
                "sort": r["sort"],
                "active": bool(r["active"]),
                "deleted": r["deleted_at"] is not None,
            }
            for r in q("SELECT * FROM kids")
        },
        "kid_max": {
            (r["kid_id"], r["currency_id"]): r["weekly_max"]
            for r in q("SELECT * FROM kid_currency_max")
        },
        "currencies": {
            r["id"]: {**_currency(r), "deleted": r["deleted_at"] is not None}
            for r in q("SELECT * FROM currencies")
        },
        "chores": {
            r["id"]: {
                **_chore(
                    {
                        **r,
                        "chore_type": r["type"],
                        "weekdays": mask_to_weekdays(r["weekdays"]),
                        "kid_ids": kids_of.get(r["id"], []),
                        "values": values_of.get(r["id"], {}),
                    }
                ),
                "deleted": r["deleted_at"] is not None,
            }
            for r in q("SELECT * FROM chores")
        },
        "settings": repo.get_settings(),
        "weeks": {r["start"]: r["status"] for r in q("SELECT * FROM weeks")},
        "instances": {
            i.id: {k: v for k, v in instance_snapshot(i).items() if k != "id"}
            for i in repo.list_instances()
        },
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
