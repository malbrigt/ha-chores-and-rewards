"""WebSocket API for the panel. Contract: docs/ws-api.md.

Any logged-in HA user may call these (D14): the setup decides whether the kitchen tablet
runs as an admin or a normal user. Parent and admin commands need a PIN session token.

Handlers are thin (D47): validate input, call one use case in actions.py (writes) or a
read model in store.py (reads), and serialize with serialize.py.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Awaitable, Callable
from functools import partial, wraps
from typing import Any, Protocol

import probatio as vol
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util

from . import actions
from .actions import Ctx, NotFound, require
from .audit import AuditAction
from .const import DOMAIN, SIGNAL_UPDATED
from .db import Repo
from .logic import (
    CapMode,
    Chore,
    ChoreType,
    Currency,
    Instance,
    Kid,
    RuleError,
    Slot,
    Status,
    is_late,
    verify_pin,
    week_days,
    week_start,
)
from .serialize import balances_json, chore_json, currency_json, instance_json, kid_json
from .store import ChoresStore
from .views import board, kid_balances, payout_items, week_grid

P = f"{DOMAIN}/"
TOKEN = {vol.Required("token"): str}

type Msg = dict[str, Any]


class Handler(Protocol):
    def __call__(
        self, hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
    ) -> Awaitable[Any]: ...


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


def _error_code(err: Exception) -> str:
    if isinstance(err, RuleError):
        return err.code
    if isinstance(err, sqlite3.IntegrityError):
        # UNIQUE: an active kid/chore/currency already has that name. Anything else
        # (FOREIGN KEY): a reference to a missing kid/currency/chore.
        unique = err.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE"
        return "duplicate_name" if unique else "not_found"
    return "not_found"  # NotFound


def command(schema: dict[Any, Any], *, parent: bool = True) -> Callable[[Handler], Any]:
    """An async command for any HA user; parent=True requires a PIN session token.

    Finds the store, checks the PIN session, and maps rule/lookup errors to codes.
    """
    full = {**schema, **TOKEN} if parent else schema

    def decorator(func: Handler) -> Any:
        @wraps(func)
        async def wrapper(hass: HomeAssistant, connection: ActiveConnection, msg: Msg) -> None:
            store = _store(hass)
            if store is None:
                connection.send_error(msg["id"], "not_loaded", "Integration not loaded")
                return
            if parent and not store.sessions.touch(msg.get("token")):
                connection.send_error(msg["id"], "invalid_token", "PIN required")
                return
            try:
                result = await func(hass, connection, msg, store)
            except (RuleError, NotFound, sqlite3.IntegrityError) as err:
                code = _error_code(err)
                connection.send_error(msg["id"], code, code)
            else:
                connection.send_result(msg["id"], result)

        return websocket_api.websocket_command(full)(websocket_api.async_response(wrapper))

    return decorator


def _ctx(connection: ActiveConnection, store: ChoresStore) -> Ctx:
    return Ctx(by=connection.user.id if connection.user else None, today=store.today())


def _ticked_late(i: Instance) -> bool:
    """Done, and ticked on a later (local) day than the chore's own day (D43)."""
    if i.status is not Status.DONE or not i.status_at:
        return False
    changed = dt_util.parse_datetime(i.status_at)
    return changed is not None and is_late(i.day, dt_util.as_local(changed).date())


def instance_out(i: Instance) -> dict[str, Any]:
    """The audit snapshot plus what the panel needs to show it."""
    return {**instance_json(i), "status_at": i.status_at, "late": _ticked_late(i)}


# --- Kid and read API ---------------------------------------------------------------


@websocket_api.websocket_command({vol.Required("type"): P + "subscribe"})
@callback
def ws_subscribe(hass: HomeAssistant, connection: ActiveConnection, msg: Msg) -> None:
    """Push {event: "updated"} after any change; the panel then re-reads (AC-6.1)."""
    if _store(hass) is None:
        connection.send_error(msg["id"], "not_loaded", "Integration not loaded")
        return

    @callback
    def forward() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], {"event": "updated"}))

    # Stored subscriptions are removed by HA on unsubscribe or disconnect.
    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_UPDATED, forward)
    connection.send_result(msg["id"])


@command({vol.Required("type"): P + "get_state", vol.Optional("day"): cv.date}, parent=False)
async def ws_get_state(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    await store.async_ensure_current()
    today = store.today()
    day = msg.get("day", today)
    week = week_start(day)

    def read(repo: Repo) -> dict[str, Any]:
        return {
            "today": today.isoformat(),
            "day": day.isoformat(),
            "week": week.isoformat(),
            "week_status": repo.week_status(week),
            "is_preview": day > today,
            "kids": [kid_json(k) for k in repo.list_kids()],
            "currencies": [currency_json(c) for c in repo.list_currencies()],
            "settings": repo.get_settings(),
            "board": {
                str(kid_id): {
                    "chores": [instance_out(i) for i in data.chores],
                    "bonus": [
                        {**instance_out(i), "taken_by": data.taken.get(i.id or 0)}
                        for i in data.bonus
                    ],
                    "balances": balances_json(data.balances),
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
async def ws_get_week(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    today = store.today()
    week = week_start(msg.get("week", today))
    kid_id = msg["kid_id"]

    def read(repo: Repo) -> dict[str, Any]:
        require(repo.get_kid(kid_id))
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
                    "cells": {d.isoformat(): i.status.value for d, i in r["days"].items()},
                    "ids": {d.isoformat(): i.id for d, i in r["days"].items()},
                    "late": {d.isoformat(): _ticked_late(i) for d, i in r["days"].items()},
                    "values": {
                        d.isoformat(): {str(c): v for c, v in i.values.items()}
                        for d, i in r["days"].items()
                    },
                }
                for r in week_grid(repo, kid_id, week)
            ],
            "balances": balances_json(kid_balances(repo, kid_id, week, today)),
        }

    return await store.async_read(read)


@command(
    {
        vol.Required("type"): P + "set_done",
        vol.Required("instance_id"): int,
        vol.Required("done"): bool,
        vol.Optional("currency_id"): int,  # extra chores: what to earn (D49)
    },
    parent=False,
)
async def ws_set_done(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    await store.async_ensure_current()
    run = partial(
        actions.set_done,
        ctx=_ctx(connection, store),
        instance_id=msg["instance_id"],
        done=msg["done"],
        currency_id=msg.get("currency_id"),
    )
    return {"instance": instance_out(await store.async_write(run))}


# --- PIN ----------------------------------------------------------------------


@command({vol.Required("type"): P + "pin/unlock", vol.Required("pin"): str}, parent=False)
async def ws_pin_unlock(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    """AC-7.1, AC-7.2. Every attempt is audited as PIN usage."""
    by = _ctx(connection, store).by
    try:
        store.sessions.check_allowed()
        ok = await hass.async_add_executor_job(verify_pin, msg["pin"], store.pin_hash)
        token = store.sessions.unlock(ok)  # raises wrong_pin / locked_out
    except RuleError as err:
        locked = err.code == "locked_out"
        await store.async_audit(AuditAction.PIN_LOCKED_OUT if locked else AuditAction.PIN_WRONG, by)
        raise
    await store.async_audit(AuditAction.PIN_UNLOCK, by)
    return {"token": token, "expires_in": store.sessions.expires_in(token)}


@command({vol.Required("type"): P + "pin/status", vol.Required("token"): str}, parent=False)
async def ws_pin_status(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    valid = store.sessions.touch(msg["token"])
    return {"valid": valid, "expires_in": store.sessions.expires_in(msg["token"])}


@command({vol.Required("type"): P + "pin/lock", vol.Required("token"): str}, parent=False)
async def ws_pin_lock(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    store.sessions.lock(msg["token"])
    await store.async_audit(AuditAction.PIN_LOCK, _ctx(connection, store).by)
    return {}


# --- Admin ---------------------------------------------------------------------

_NON_NEG = vol.All(int, vol.Range(min=0))
_NAME = vol.All(str, vol.Strip, vol.Length(min=1, max=50))


@command({vol.Required("type"): P + "admin/list"})
async def ws_admin_list(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    def read(repo: Repo) -> dict[str, Any]:
        maxes = repo.all_kid_max()
        return {
            "kids": [
                kid_json(k, {c: m for (kid, c), m in maxes.items() if kid == k.id})
                for k in repo.list_kids(True)
            ],
            "currencies": [currency_json(c) for c in repo.list_currencies(True)],
            "chores": [chore_json(c) for c in repo.list_chores(True)],
            "settings": repo.get_settings(),
        }

    return await store.async_read(read)


@command(
    {
        vol.Required("type"): P + "admin/kid/save",
        vol.Optional("kid_id", default=0): int,
        vol.Required("name"): _NAME,
        vol.Optional("sort", default=0): int,
        vol.Optional("active", default=True): bool,
        vol.Optional("max", default={}): {vol.Coerce(int): vol.Any(None, _NON_NEG)},
    }
)
async def ws_kid_save(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    kid = Kid(id=msg["kid_id"], name=msg["name"], sort=msg["sort"], active=msg["active"])
    run = partial(actions.save_kid, ctx=_ctx(connection, store), kid=kid, maxes=msg["max"])
    return {"id": await store.async_write(run)}


@command({vol.Required("type"): P + "admin/kid/delete", vol.Required("kid_id"): int})
async def ws_kid_delete(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    await store.async_write(
        partial(actions.delete_kid, ctx=_ctx(connection, store), kid_id=msg["kid_id"])
    )
    return {}


@command(
    {
        vol.Required("type"): P + "admin/currency/save",
        vol.Optional("currency_id", default=0): int,
        vol.Required("name"): _NAME,
        vol.Required("unit"): vol.All(str, vol.Strip, vol.Length(min=1, max=10)),
        vol.Optional("icon", default=""): str,
        vol.Required("payout_weekday"): vol.All(int, vol.Range(min=0, max=6)),
        vol.Required("can_be_lost"): bool,
        vol.Required("cap_mode"): vol.In([m.value for m in CapMode]),
        vol.Optional("default_max", default=None): vol.Any(None, _NON_NEG),
        # Minor unit of every amount in this currency; fixed after create (D50).
        vol.Optional("decimals", default=0): vol.In([0, 1, 2]),
        vol.Optional("active", default=True): bool,
        vol.Optional("sort", default=0): int,
    }
)
async def ws_currency_save(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    currency = Currency(
        id=msg["currency_id"],
        name=msg["name"],
        unit=msg["unit"],
        icon=msg["icon"],
        payout_weekday=msg["payout_weekday"],
        can_be_lost=msg["can_be_lost"],
        cap_mode=CapMode(msg["cap_mode"]),
        default_max=msg["default_max"],
        decimals=msg["decimals"],
        active=msg["active"],
        sort=msg["sort"],
    )
    run = partial(actions.save_currency, ctx=_ctx(connection, store), currency=currency)
    return {"id": await store.async_write(run)}


@command({vol.Required("type"): P + "admin/currency/delete", vol.Required("currency_id"): int})
async def ws_currency_delete(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    await store.async_write(
        partial(
            actions.delete_currency, ctx=_ctx(connection, store), currency_id=msg["currency_id"]
        )
    )
    return {}


@command(
    {
        vol.Required("type"): P + "admin/chore/save",
        vol.Optional("chore_id", default=0): int,
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
        vol.Optional("once_a_day", default=False): bool,
    }
)
async def ws_chore_save(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    """AC-5.5: returns payout warnings but always saves."""
    chore = Chore(
        id=msg["chore_id"],
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
        once_a_day=msg["once_a_day"],
    )
    run = partial(actions.save_chore, ctx=_ctx(connection, store), chore=chore)
    chore_id, warnings = await store.async_write(run)
    return {"id": chore_id, "warnings": warnings}


@command({vol.Required("type"): P + "admin/chore/delete", vol.Required("chore_id"): int})
async def ws_chore_delete(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    await store.async_write(
        partial(actions.delete_chore, ctx=_ctx(connection, store), chore_id=msg["chore_id"])
    )
    return {}


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
async def ws_settings_save(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    run = partial(actions.save_settings, ctx=_ctx(connection, store), changes=msg["settings"])
    settings = await store.async_write(run)
    store.apply_settings(settings)
    return {"settings": settings}


# --- Parent actions ------------------------------------------------------------------


@command(
    {
        vol.Required("type"): P + "parent/set_status",
        vol.Required("instance_id"): int,
        vol.Required("status"): vol.In([s.value for s in Status]),
        vol.Optional("currency_id"): int,  # extra chores marked done: what to earn (D49)
    }
)
async def ws_parent_set_status(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    await store.async_ensure_current()
    run = partial(
        actions.set_status,
        ctx=_ctx(connection, store),
        instance_id=msg["instance_id"],
        status=Status(msg["status"]),
        currency_id=msg.get("currency_id"),
    )
    return {"instance": instance_out(await store.async_write(run))}


@command(
    {
        vol.Required("type"): P + "parent/adjust",
        vol.Required("kid_id"): int,
        vol.Required("currency_id"): int,
        vol.Required("amount"): vol.All(int, vol.NotIn([0])),
        vol.Required("note"): vol.All(str, vol.Strip, vol.Length(min=1, max=200)),
    }
)
async def ws_parent_adjust(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    run = partial(
        actions.adjust,
        ctx=_ctx(connection, store),
        kid_id=msg["kid_id"],
        currency_id=msg["currency_id"],
        amount=msg["amount"],
        note=msg["note"],
    )
    return {"id": await store.async_write(run)}


@command({vol.Required("type"): P + "parent/payouts", vol.Optional("week"): cv.date})
async def ws_parent_payouts(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    today = store.today()
    week = week_start(msg.get("week", today))

    def read(repo: Repo) -> dict[str, Any]:
        return {
            "week": week.isoformat(),
            "week_status": repo.week_status(week),
            "items": [
                {
                    "kid_id": i.kid_id,
                    "currency_id": i.currency_id,
                    "amount_due": i.amount_due,
                    "paid": {"amount": i.paid_amount, "done_at": i.paid_at}
                    if i.paid_amount is not None
                    else None,
                    "after_payout": i.after_payout,
                    "payout_day": i.payout_day.isoformat(),
                    "is_payout_day": i.is_payout_day,
                }
                for i in payout_items(repo, week, today)
            ],
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
async def ws_parent_payout(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    """Tick (or untick) "paid"/"entered". Allowed for closed weeks too: late payouts happen."""
    ctx = _ctx(connection, store)
    run = partial(
        actions.payout,
        ctx=ctx,
        week=week_start(msg.get("week", ctx.today)),
        kid_id=msg["kid_id"],
        currency_id=msg["currency_id"],
        paid=msg["paid"],
    )
    return {"amount": await store.async_write(run)}


@command({vol.Required("type"): P + "parent/close_week"})
async def ws_parent_close_week(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    await store.async_write(partial(actions.close_week, ctx=_ctx(connection, store)))
    return {}


@command({vol.Required("type"): P + "parent/reopen_week"})
async def ws_parent_reopen_week(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    await store.async_write(partial(actions.reopen_week, ctx=_ctx(connection, store)))
    return {}


@command(
    {
        vol.Required("type"): P + "parent/audit",
        vol.Optional("limit", default=100): vol.All(int, vol.Range(min=1, max=1000)),
        vol.Optional("actions"): [str],
        vol.Optional("kid_id"): int,
        vol.Optional("week"): cv.date,
        vol.Optional("late_only", default=False): bool,
    }
)
async def ws_parent_audit(
    hass: HomeAssistant, connection: ActiveConnection, msg: Msg, store: ChoresStore
) -> dict[str, Any]:
    """Audit log, newest first, optionally filtered (D44). `week`: any date in that week."""
    week = week_start(msg["week"]) if "week" in msg else None

    def read(repo: Repo) -> list[dict[str, Any]]:
        return repo.list_audit(
            msg["limit"],
            actions=msg.get("actions"),
            kid_id=msg.get("kid_id"),
            week=week,
            late_only=msg["late_only"],
        )

    return {"entries": await store.async_read(read)}
