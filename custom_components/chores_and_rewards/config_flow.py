"""Config flow: one-click setup that only asks for the parent PIN."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

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
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                pin_hash = await _hash(self.hass, user_input[CONF_PIN])
                return self.async_create_entry(title=NAME, data={CONF_PIN_HASH: pin_hash})
        return self.async_show_form(step_id="user", data_schema=PIN_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return ChoresOptionsFlow()


class ChoresOptionsFlow(OptionsFlow):
    """Options: an HA admin can reset the parent PIN."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                pin_hash = await _hash(self.hass, user_input[CONF_PIN])
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data={**self.config_entry.data, CONF_PIN_HASH: pin_hash}
                )
                return self.async_create_entry(data=dict(self.config_entry.options))
        return self.async_show_form(step_id="init", data_schema=PIN_SCHEMA, errors=errors)
