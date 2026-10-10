"""Diagnostics download (Settings → Devices & services → … → Download diagnostics)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import ChoresConfigEntry
from .const import CONF_PIN_HASH
from .db import Repo

_TABLES = ("kids", "currencies", "chores", "instances", "weeks", "audit_log")


def _collect(repo: Repo) -> dict[str, Any]:
    last = repo.last_finalized()
    return {
        "schema_version": repo.schema_version(),
        "last_finalized": last.isoformat() if last else None,
        "open_weeks": [w.isoformat() for w in repo.open_weeks()],
        "counts": repo.counts(_TABLES),
        "settings": repo.get_settings(),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ChoresConfigEntry
) -> dict[str, Any]:
    data = await entry.runtime_data.async_read(_collect)
    return {
        "entry": {
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), {CONF_PIN_HASH}),
            "options": dict(entry.options),
        },
        "db": data,
    }
