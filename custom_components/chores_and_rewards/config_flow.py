"""Config flow: one-click setup that asks for the parent PIN; reconfigure changes it."""

from __future__ import annotations

from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .audit import AuditAction
from .const import CONF_PIN, CONF_PIN_CONFIRM, CONF_PIN_HASH, DOMAIN, NAME
from .logic import hash_pin, is_valid_pin

_PIN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
PIN_SCHEMA = vol.Schema(
    {vol.Required(CONF_PIN): _PIN_SELECTOR, vol.Required(CONF_PIN_CONFIRM): _PIN_SELECTOR}
)


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    """Return form errors for a PIN + confirmation pair."""
    if not is_valid_pin(user_input[CONF_PIN]):
        return {CONF_PIN: "invalid_pin"}
    if user_input[CONF_PIN] != user_input[CONF_PIN_CONFIRM]:
        return {CONF_PIN_CONFIRM: "pin_mismatch"}
    return {}


async def _hash(hass: HomeAssistant, pin: str) -> str:
    """Hash off the event loop; scrypt is deliberately slow."""
    return await hass.async_add_executor_job(hash_pin, pin)


class ChoresConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup, and reconfigure for an HA admin to reset the parent PIN."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                pin_hash = await _hash(self.hass, user_input[CONF_PIN])
                return self.async_create_entry(title=NAME, data={CONF_PIN_HASH: pin_hash})
        return self.async_show_form(step_id="user", data_schema=PIN_SCHEMA, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """New PIN. The reload that follows ends all parent sessions and lockouts (D40)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                entry = self._get_reconfigure_entry()
                pin_hash = await _hash(self.hass, user_input[CONF_PIN])
                store = getattr(entry, "runtime_data", None)
                if store is not None:
                    await store.async_audit(AuditAction.PIN_RESET, None, note="reconfigure")
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PIN_HASH: pin_hash}
                )
        return self.async_show_form(step_id="reconfigure", data_schema=PIN_SCHEMA, errors=errors)
