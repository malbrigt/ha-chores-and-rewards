"""WebSocket API for the panel. Contract: docs/ws-api.md.

Every command requires an HA admin user. Parent commands also need a PIN session token.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

import probatio as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .const import CONF_PIN_HASH, DOMAIN
from .db import Repo
from .logic import (
    CapMode,
    Chore,
    ChoreType,
    Currency,
    Kid,
    RuleError,
    Slot,
    payout_warnings,
    verify_pin,
)
from .store import ChoresStore, refresh_today_for_chore, refresh_today_for_kid

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
