"""WebSocket API for the panel. Contract: docs/ws-api.md.

Every command requires an HA admin user. Parent commands also need a PIN session token.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, timedelta
from functools import wraps
from typing import Any

import probatio as vol
from homeassistant.components import websocket_api
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv

from .const import CONF_PIN_HASH, DOMAIN, EVENT_UPDATED
from .db import Repo
from .logic import (
    Actor,
    Balance,
    CapMode,
    Chore,
    ChoreType,
    Currency,
    Instance,
    Kid,
    RuleError,
    Slot,
    Status,
    is_payout_day,
    payout_warnings,
    transition,
    verify_pin,
    week_days,
    week_start,
)
from .store import (
    ChoresStore,
    board,
    ensure_today,
    kid_balances,
    refresh_today_for_chore,
    refresh_today_for_kid,
    week_grid,
)

P = f"{DOMAIN}/"
TOKEN = {vol.Required("token"): str}

type Handler = Callable[
    [HomeAssistant, websocket_api.ActiveConnection, dict[str, Any], ChoresStore],
    Awaitable[Any],
]


class NotFound(Exception):
    """Unknown or deleted id."""


def async_register(hass: HomeAssistant) -> None:
    """Register all commands. Called once from async_setup."""
    for handler in (
        ws_subscribe,
        ws_get_state,
        ws_get_week,
        ws_set_done,
        ws_pin_unlock,
        ws_pin_status,
        ws_pin_lock,
        ws_admin_list,
        ws_kid_save,
        ws_kid_delete,
        ws_currency_save,
        ws_currency_delete,
        ws_chore_save,
        ws_chore_delete,
        ws_settings_save,
        ws_parent_set_status,
        ws_parent_adjust,
        ws_parent_payouts,
        ws_parent_payout,
        ws_parent_close_week,
        ws_parent_reopen_week,
        ws_parent_audit,
    ):
        websocket_api.async_register_command(hass, handler)


# --- plumbing -----------------------------------------------------------------


def _store(hass: HomeAssistant) -> ChoresStore | None:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    return entries[0].runtime_data if entries else None


def handler(*, parent: bool) -> Callable[[Handler], Any]:
    """Wrap a command: find the store, check the PIN session, map errors to codes."""

    def decorator(func: Handler) -> Any:
        @wraps(func)
        async def wrapper(
            hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
        ) -> None:
            store = _store(hass)
            if store is None:
                connection.send_error(msg["id"], "not_loaded", "Integration not loaded")
                return
            if parent and not store.sessions.touch(msg.get("token")):
                connection.send_error(msg["id"], "invalid_token", "PIN required")
                return
            try:
                result = await func(hass, connection, msg, store)
            except RuleError as err:
                connection.send_error(msg["id"], err.code, err.code)
            except NotFound:
                connection.send_error(msg["id"], "not_found", "Not found")
            else:
                connection.send_result(msg["id"], result)

        return wrapper

    return decorator


def command(schema: dict[Any, Any], *, parent: bool = True) -> Callable[[Handler], Any]:
    """Admin-only async command; parent=True also requires a PIN session token."""
    full = {**schema, **TOKEN} if parent else schema

    def decorator(func: Handler) -> Any:
        wrapped = websocket_api.async_response(handler(parent=parent)(func))
        return websocket_api.websocket_command(full)(websocket_api.require_admin(wrapped))

    return decorator


def _user(connection: websocket_api.ActiveConnection) -> str | None:
    return connection.user.id if connection.user else None


def _require[T](value: T | None) -> T:
    if value is None:
        raise NotFound
    return value


# --- serialization ------------------------------------------------------------


def kid_dict(kid: Kid, max_: dict[int, int] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"id": kid.id, "name": kid.name, "sort": kid.sort, "active": kid.active}
    if max_ is not None:
        out["max"] = {str(k): v for k, v in max_.items()}
    return out


def currency_dict(c: Currency) -> dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "unit": c.unit,
        "icon": c.icon,
        "payout_weekday": c.payout_weekday,
        "can_be_lost": c.can_be_lost,
        "cap_mode": c.cap_mode.value,
        "default_max": c.default_max,
        "active": c.active,
        "sort": c.sort,
    }


def chore_dict(c: Chore) -> dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "icon": c.icon,
        "description": c.description,
        "chore_type": c.type.value,
        "slot": c.slot.value,
        "weekdays": sorted(c.weekdays),
        "kid_ids": sorted(c.kid_ids),
        "values": {str(k): v for k, v in c.values.items()},
        "active": c.active,
        "sort": c.sort,
    }


def instance_dict(i: Instance) -> dict[str, Any]:
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
        "status_at": i.status_at,
    }


def balance_dict(b: Balance) -> dict[str, Any]:
    return {
        "earned": b.earned,
        "lost": b.lost,
        "adjustments": b.adjustments,
        "cap": b.cap,
        "total": b.total,
    }


def balances_dict(balances: dict[int, Balance]) -> dict[str, Any]:
    return {str(cid): balance_dict(b) for cid, b in balances.items()}


# --- Kid and read API (step 6) -------------------------------------------------


@websocket_api.websocket_command({vol.Required("type"): P + "subscribe"})
@websocket_api.require_admin
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Push {event: "updated"} after any change; the panel then re-reads (AC-6.1)."""

    @callback
    def forward(_event: Event) -> None:
        connection.send_message(websocket_api.event_message(msg["id"], {"event": "updated"}))

    # Stored subscriptions are removed by HA on unsubscribe or disconnect.
    connection.subscriptions[msg["id"]] = hass.bus.async_listen(EVENT_UPDATED, forward)
    connection.send_result(msg["id"])


@command({vol.Required("type"): P + "get_state", vol.Optional("day"): cv.date}, parent=False)
async def ws_get_state(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    await store.async_ensure_current()
    today = store.today()
    day = msg.get("day", today)

    def read(repo: Repo) -> dict[str, Any]:
        return {
            "today": today.isoformat(),
            "day": day.isoformat(),
            "week": week_start(day).isoformat(),
            "week_status": repo.week_status(week_start(day)),
            "is_preview": day > today,
            "kids": [kid_dict(k) for k in repo.list_kids()],
            "currencies": [currency_dict(c) for c in repo.list_currencies()],
            "settings": repo.get_settings(),
            "board": {
                str(kid_id): {
                    "chores": [instance_dict(i) for i in data.chores],
                    "bonus": [instance_dict(i) for i in data.bonus],
                    "balances": balances_dict(data.balances),
                }
                for kid_id, data in board(repo, day, today).items()
            },
        }

    return await store.async_read(read)


@command(
    {
        vol.Required("type"): P + "get_week",
        vol.Required("kid_id"): int,
        vol.Optional("week"): cv.date,
    },
    parent=False,
)
async def ws_get_week(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    today = store.today()
    week = week_start(msg.get("week", today))

    def read(repo: Repo) -> dict[str, Any]:
        _require(repo.get_kid(msg["kid_id"]))
        rows = week_grid(repo, msg["kid_id"], week)
        return {
            "week": week.isoformat(),
            "week_status": repo.week_status(week),
            "days": [d.isoformat() for d in week_days(week)],
            "rows": [
                {
                    "chore_id": r["chore_id"],
                    "name": r["name"],
                    "type": r["type"].value,
                    "slot": r["slot"].value,
                    "cells": {d.isoformat(): st.value for d, st in r["cells"].items()},
                    "ids": {d.isoformat(): i for d, i in r["ids"].items()},
                }
                for r in rows
            ],
            "balances": balances_dict(kid_balances(repo, msg["kid_id"], week, today)),
        }

    return await store.async_read(read)


@command(
    {
        vol.Required("type"): P + "set_done",
        vol.Required("instance_id"): int,
        vol.Required("done"): bool,
    },
    parent=False,
)
async def ws_set_done(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    """Kid tap: done or undo, today only, no approval (AC-6.1, AC-6.2)."""
    await store.async_ensure_current()
    today = store.today()
    target = Status.DONE if msg["done"] else Status.PENDING

    def write(repo: Repo) -> Instance:
        inst = _require(repo.get_instance(msg["instance_id"]))
        if repo.week_status(week_start(inst.day)) != "open":
            raise RuleError("week_closed")
        new = transition(inst, target, Actor.KID, today)
        assert new.id is not None
        repo.set_status(new.id, new.status, by="kid")
        return _require(repo.get_instance(new.id))

    return {"instance": instance_dict(await store.async_write(write))}


# --- PIN ----------------------------------------------------------------------


@command({vol.Required("type"): P + "pin/unlock", vol.Required("pin"): str}, parent=False)
async def ws_pin_unlock(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    """AC-7.1, AC-7.2."""
    store.sessions.check_allowed()
    entry = hass.config_entries.async_loaded_entries(DOMAIN)[0]
    ok = await hass.async_add_executor_job(verify_pin, msg["pin"], entry.data[CONF_PIN_HASH])
    token = store.sessions.unlock(ok)  # raises wrong_pin / locked_out
    return {"token": token, "expires_in": store.sessions.expires_in(token)}


@command({vol.Required("type"): P + "pin/status", vol.Required("token"): str}, parent=False)
async def ws_pin_status(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    valid = store.sessions.touch(msg["token"])
    return {"valid": valid, "expires_in": store.sessions.expires_in(msg["token"])}


@command({vol.Required("type"): P + "pin/lock", vol.Required("token"): str}, parent=False)
async def ws_pin_lock(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    store.sessions.lock(msg["token"])
    return {}


# --- admin: list --------------------------------------------------------------


@command({vol.Required("type"): P + "admin/list"})
async def ws_admin_list(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    def read(repo: Repo) -> dict[str, Any]:
        return {
            "kids": [kid_dict(k, repo.kid_max(k.id)) for k in repo.list_kids(True)],
            "currencies": [currency_dict(c) for c in repo.list_currencies(True)],
            "chores": [chore_dict(c) for c in repo.list_chores(True)],
            "settings": repo.get_settings(),
        }

    return await store.async_read(read)


# --- admin: kids --------------------------------------------------------------

_NON_NEG = vol.All(int, vol.Range(min=0))
_MAX_MAP = {vol.Coerce(int): vol.Any(None, _NON_NEG)}
_NAME = vol.All(str, vol.Strip, vol.Length(min=1, max=50))


@command(
    {
        vol.Required("type"): P + "admin/kid/save",
        vol.Optional("kid_id"): int,
        vol.Required("name"): _NAME,
        vol.Optional("sort", default=0): int,
        vol.Optional("active", default=True): bool,
        vol.Optional("max", default={}): _MAX_MAP,
    }
)
async def ws_kid_save(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    user, today = _user(connection), store.today()

    def write(repo: Repo) -> int:
        fields = {"name": msg["name"], "sort": msg["sort"], "active": msg["active"]}
        if "kid_id" in msg:
            before = _require(repo.get_kid(msg["kid_id"]))
            kid_id = before.id
            repo.update_kid(kid_id, **fields)
            before_dict: dict[str, Any] | None = kid_dict(before, repo.kid_max(kid_id))
        else:
            kid_id = repo.add_kid(**fields)
            before_dict = None
        for currency_id, weekly_max in msg["max"].items():
            repo.set_kid_max(kid_id, currency_id, weekly_max)
        after = kid_dict(_require(repo.get_kid(kid_id)), repo.kid_max(kid_id))
        repo.audit(
            "kid_save",
            user_id=user,
            entity="kid",
            entity_id=kid_id,
            before=before_dict,
            after=after,
        )
        refresh_today_for_kid(repo, kid_id, today)
        return kid_id

    return {"id": await store.async_write(write)}


@command({vol.Required("type"): P + "admin/kid/delete", vol.Required("kid_id"): int})
async def ws_kid_delete(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    user, today = _user(connection), store.today()

    def write(repo: Repo) -> None:
        kid = _require(repo.get_kid(msg["kid_id"]))
        repo.delete_kid(kid.id)
        repo.audit("kid_delete", user_id=user, entity="kid", entity_id=kid.id, before=kid_dict(kid))
        refresh_today_for_kid(repo, kid.id, today)

    await store.async_write(write)
    return {}


# --- admin: currencies --------------------------------------------------------


@command(
    {
        vol.Required("type"): P + "admin/currency/save",
        vol.Optional("currency_id"): int,
        vol.Required("name"): _NAME,
        vol.Required("unit"): vol.All(str, vol.Strip, vol.Length(min=1, max=10)),
        vol.Optional("icon", default=""): str,
        vol.Required("payout_weekday"): vol.All(int, vol.Range(min=0, max=6)),
        vol.Required("can_be_lost"): bool,
        vol.Required("cap_mode"): vol.In([m.value for m in CapMode]),
        vol.Optional("default_max", default=None): vol.Any(None, _NON_NEG),
        vol.Optional("active", default=True): bool,
        vol.Optional("sort", default=0): int,
    }
)
async def ws_currency_save(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    user = _user(connection)
    keys = ("name", "unit", "icon", "payout_weekday", "can_be_lost", "cap_mode")
    fields = {k: msg[k] for k in (*keys, "default_max", "active", "sort")}

    def write(repo: Repo) -> int:
        if "currency_id" in msg:
            before = _find_currency(repo, msg["currency_id"])
            repo.update_currency(before.id, **fields)
            currency_id, before_dict = before.id, currency_dict(before)
        else:
            currency = Currency(id=0, **{**fields, "cap_mode": CapMode(fields["cap_mode"])})
            currency_id, before_dict = repo.add_currency(currency), None
        after = currency_dict(_find_currency(repo, currency_id))
        repo.audit(
            "currency_save",
            user_id=user,
            entity="currency",
            entity_id=currency_id,
            before=before_dict,
            after=after,
        )
        return currency_id

    return {"id": await store.async_write(write)}


@command({vol.Required("type"): P + "admin/currency/delete", vol.Required("currency_id"): int})
async def ws_currency_delete(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    user = _user(connection)

    def write(repo: Repo) -> None:
        currency = _find_currency(repo, msg["currency_id"])
        repo.delete_currency(currency.id)
        repo.audit(
            "currency_delete",
            user_id=user,
            entity="currency",
            entity_id=currency.id,
            before=currency_dict(currency),
        )

    await store.async_write(write)
    return {}


def _find_currency(repo: Repo, currency_id: int) -> Currency:
    return _require(next((c for c in repo.list_currencies(True) if c.id == currency_id), None))


# --- admin: chores ------------------------------------------------------------


@command(
    {
        vol.Required("type"): P + "admin/chore/save",
        vol.Optional("chore_id"): int,
        vol.Required("name"): vol.All(str, vol.Strip, vol.Length(min=1, max=80)),
        vol.Optional("icon", default=""): str,
        vol.Optional("description", default=""): vol.All(str, vol.Length(max=500)),
        vol.Required("chore_type"): vol.In([t.value for t in ChoreType]),
        vol.Required("slot"): vol.In([s.value for s in Slot]),
        vol.Required("weekdays"): [vol.All(int, vol.Range(min=0, max=6))],
        vol.Required("kid_ids"): [int],
        vol.Required("values"): {vol.Coerce(int): _NON_NEG},
        vol.Optional("active", default=True): bool,
        vol.Optional("sort", default=0): int,
    }
)
async def ws_chore_save(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    """AC-5.5: returns payout warnings but always saves."""
    user, today = _user(connection), store.today()
    chore = Chore(
        id=msg.get("chore_id", 0),
        name=msg["name"],
        type=ChoreType(msg["chore_type"]),
        kid_ids=frozenset(msg["kid_ids"]),
        weekdays=frozenset(msg["weekdays"]),
        slot=Slot(msg["slot"]),
        values={k: v for k, v in msg["values"].items() if v},
        icon=msg["icon"],
        description=msg["description"],
        active=msg["active"],
        sort=msg["sort"],
    )

    def write(repo: Repo) -> tuple[int, list[int]]:
        known_kids = {k.id for k in repo.list_kids(True)}
        known_currencies = {c.id for c in repo.list_currencies(True)}
        if not chore.kid_ids <= known_kids or not set(chore.values) <= known_currencies:
            raise NotFound
        if "chore_id" in msg:
            before = _require(repo.get_chore(msg["chore_id"]))
            repo.update_chore(chore)
            chore_id, before_dict = before.id, chore_dict(before)
        else:
            chore_id, before_dict = repo.add_chore(chore), None
        saved = _require(repo.get_chore(chore_id))
        repo.audit(
            "chore_save",
            user_id=user,
            entity="chore",
            entity_id=chore_id,
            before=before_dict,
            after=chore_dict(saved),
        )
        refresh_today_for_chore(repo, chore_id, today)
        return chore_id, payout_warnings(saved, repo.list_currencies())

    chore_id, warnings = await store.async_write(write)
    return {"id": chore_id, "warnings": warnings}


@command({vol.Required("type"): P + "admin/chore/delete", vol.Required("chore_id"): int})
async def ws_chore_delete(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    user, today = _user(connection), store.today()

    def write(repo: Repo) -> None:
        chore = _require(repo.get_chore(msg["chore_id"]))
        repo.delete_chore(chore.id)
        repo.audit(
            "chore_delete",
            user_id=user,
            entity="chore",
            entity_id=chore.id,
            before=chore_dict(chore),
        )
        refresh_today_for_chore(repo, chore.id, today)

    await store.async_write(write)
    return {}


# --- admin: settings ----------------------------------------------------------

_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Optional("clean_hands_enabled"): bool,
        vol.Optional("clean_hands_text"): vol.All(str, vol.Length(max=100)),
        vol.Optional("idle_seconds"): vol.All(int, vol.Range(min=10)),
        vol.Optional("wake_seconds"): vol.All(int, vol.Range(min=10)),
        vol.Optional("pin_timeout_seconds"): vol.All(int, vol.Range(min=30)),
    }
)


@command(
    {vol.Required("type"): P + "admin/settings/save", vol.Required("settings"): _SETTINGS_SCHEMA}
)
async def ws_settings_save(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    user = _user(connection)

    def write(repo: Repo) -> dict[str, Any]:
        before = repo.get_settings()
        for key, value in msg["settings"].items():
            repo.set_setting(key, value)
        after = repo.get_settings()
        repo.audit("settings_save", user_id=user, entity="settings", before=before, after=after)
        return after

    settings = await store.async_write(write)
    store.sessions.timeout = settings["pin_timeout_seconds"]
    return {"settings": settings}


# --- Parent actions (step 7) ----------------------------------------------------


def _open_week(repo: Repo, week: date) -> None:
    if repo.week_status(week) != "open":
        raise RuleError("week_closed")


@command(
    {
        vol.Required("type"): P + "parent/set_status",
        vol.Required("instance_id"): int,
        vol.Required("status"): vol.In([s.value for s in Status]),
    }
)
async def ws_parent_set_status(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    """Reject, mark done/excused/missed, or reset today (AC-7.4, AC-7.5, D19)."""
    await store.async_ensure_current()
    user, today = _user(connection), store.today()

    def write(repo: Repo) -> Instance:
        inst = _require(repo.get_instance(msg["instance_id"]))
        _open_week(repo, week_start(inst.day))
        new = transition(inst, Status(msg["status"]), Actor.PARENT, today)
        assert new.id is not None
        repo.set_status(new.id, new.status, by=user)
        repo.audit(
            "set_status",
            user_id=user,
            entity="instance",
            entity_id=new.id,
            before={"status": inst.status.value},
            after={"status": new.status.value},
        )
        return _require(repo.get_instance(new.id))

    return {"instance": instance_dict(await store.async_write(write))}


@command(
    {
        vol.Required("type"): P + "parent/adjust",
        vol.Required("kid_id"): int,
        vol.Required("currency_id"): int,
        vol.Required("amount"): vol.All(int, vol.NotIn([0])),
        vol.Required("note"): vol.All(str, vol.Strip, vol.Length(min=1, max=200)),
    }
)
async def ws_parent_adjust(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    """Adjust this week's balance with a required note (AC-7.6)."""
    user, week = _user(connection), week_start(store.today())

    def write(repo: Repo) -> int:
        _require(repo.get_kid(msg["kid_id"]))
        _find_currency(repo, msg["currency_id"])
        _open_week(repo, week)
        adj_id = repo.add_adjustment(
            week, msg["kid_id"], msg["currency_id"], msg["amount"], msg["note"], by=user
        )
        repo.audit(
            "adjust",
            user_id=user,
            entity="kid",
            entity_id=msg["kid_id"],
            after={"currency_id": msg["currency_id"], "amount": msg["amount"]},
            note=msg["note"],
        )
        return adj_id

    return {"id": await store.async_write(write)}


@command({vol.Required("type"): P + "parent/payouts", vol.Optional("week"): cv.date})
async def ws_parent_payouts(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    """Amount per kid and currency for a week, with paid state (AC-9.1, D11)."""
    today = store.today()
    week = week_start(msg.get("week", today))

    def read(repo: Repo) -> dict[str, Any]:
        paid = {(p["kid_id"], p["currency_id"]): p for p in repo.list_payouts(week)}
        currencies = repo.list_currencies()
        items = []
        for kid in repo.list_kids():
            balances = kid_balances(repo, kid.id, week, today)
            for c in currencies:
                record = paid.get((kid.id, c.id))
                due = balances[c.id].total
                items.append(
                    {
                        "kid_id": kid.id,
                        "currency_id": c.id,
                        "amount_due": due,
                        "paid": {"amount": record["amount"], "done_at": record["done_at"]}
                        if record
                        else None,
                        # Earned after the tick; the parent settles it by hand (§5, D11).
                        "after_payout": max(0, due - record["amount"]) if record else 0,
                        "payout_day": (week + timedelta(days=c.payout_weekday)).isoformat(),
                        "is_payout_day": is_payout_day(c, today) and week == week_start(today),
                    }
                )
        return {
            "week": week.isoformat(),
            "week_status": repo.week_status(week),
            "items": items,
            "adjustments": repo.list_adjustments(week),
        }

    return await store.async_read(read)


@command(
    {
        vol.Required("type"): P + "parent/payout",
        vol.Required("kid_id"): int,
        vol.Required("currency_id"): int,
        vol.Required("paid"): bool,
        vol.Optional("week"): cv.date,
    }
)
async def ws_parent_payout(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    """Tick (or untick) "paid"/"entered". Allowed for closed weeks too: late payouts happen."""
    user, today = _user(connection), store.today()
    week = week_start(msg.get("week", today))
    kid_id, currency_id = msg["kid_id"], msg["currency_id"]

    def write(repo: Repo) -> dict[str, Any]:
        _require(repo.get_kid(kid_id))
        _find_currency(repo, currency_id)
        if msg["paid"]:
            amount = kid_balances(repo, kid_id, week, today)[currency_id].total
            repo.record_payout(week, kid_id, currency_id, amount, by=user)
        else:
            amount = None
            repo.undo_payout(week, kid_id, currency_id)
        repo.audit(
            "payout" if msg["paid"] else "payout_undo",
            user_id=user,
            entity="kid",
            entity_id=kid_id,
            after={"week": week.isoformat(), "currency_id": currency_id, "amount": amount},
        )
        return {"amount": amount}

    return await store.async_write(write)


@command({vol.Required("type"): P + "parent/close_week"})
async def ws_parent_close_week(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    """Close the current week early (D1). It freezes: no taps, no midnight losses (D31)."""
    user, week = _user(connection), week_start(store.today())

    def write(repo: Repo) -> None:
        _open_week(repo, week)
        repo.close_week(week, by=user)
        repo.audit("close_week", user_id=user, entity="week", entity_id=week, note="manual")

    await store.async_write(write)
    return {}


@command({vol.Required("type"): P + "parent/reopen_week"})
async def ws_parent_reopen_week(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    """Undo an early close of the current week (warn, don't block: mistakes happen)."""
    user, today = _user(connection), store.today()
    week = week_start(today)

    def write(repo: Repo) -> None:
        if repo.week_status(week) != "closed":
            raise RuleError("not_allowed")
        repo.reopen_week(week)
        repo.audit("reopen_week", user_id=user, entity="week", entity_id=week)
        ensure_today(repo, today)

    await store.async_write(write)
    return {}


@command(
    {
        vol.Required("type"): P + "parent/audit",
        vol.Optional("limit", default=100): vol.All(int, vol.Range(min=1, max=1000)),
    }
)
async def ws_parent_audit(hass, connection, msg, store: ChoresStore) -> dict[str, Any]:
    return {"entries": await store.async_read(lambda repo: repo.list_audit(msg["limit"]))}
