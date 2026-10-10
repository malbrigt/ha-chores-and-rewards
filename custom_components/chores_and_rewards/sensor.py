"""Balance sensors: one per kid × active currency, e.g. sensor.ada_skjermtid (spec §12).

Push-updated: a coordinator without polling refreshes on every data change, adds sensors
for new kids/currencies and removes sensors whose kid or currency is gone.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from . import ChoresConfigEntry
from .const import DOMAIN, SIGNAL_UPDATED
from .db import Repo
from .logic import Balance, Currency, Kid, week_start
from .store import ChoresStore, kid_balances

_LOGGER = logging.getLogger(__name__)

type Key = tuple[int, int]  # (kid_id, currency_id)


@dataclass(frozen=True)
class BalanceRow:
    kid: Kid
    currency: Currency
    balance: Balance
    week: str


def _read(repo: Repo, today: date) -> dict[Key, BalanceRow]:
    week = week_start(today)
    currencies = repo.list_currencies()
    out: dict[Key, BalanceRow] = {}
    for kid in repo.list_kids():
        balances = kid_balances(repo, kid.id, week, today)
        for currency in currencies:
            out[(kid.id, currency.id)] = BalanceRow(
                kid, currency, balances[currency.id], week.isoformat()
            )
    return out


class BalanceCoordinator(DataUpdateCoordinator[dict[Key, BalanceRow]]):
    """Holds every kid × currency balance; refreshed on change, never polled."""

    def __init__(self, hass: HomeAssistant, entry: ChoresConfigEntry, store: ChoresStore) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=f"{DOMAIN} balances", update_interval=None
        )
        self.store = store

    async def _async_update_data(self) -> dict[Key, BalanceRow]:
        today = self.store.today()
        return await self.store.async_read(lambda repo: _read(repo, today))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ChoresConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = BalanceCoordinator(hass, entry, entry.runtime_data)
    await coordinator.async_config_entry_first_refresh()
    known: set[Key] = set()

    @callback
    def sync_entities() -> None:
        """Add sensors for new kid × currency pairs, remove ones that disappeared."""
        current = set(coordinator.data)
        new = current - known
        if new:
            async_add_entities(BalanceSensor(coordinator, entry, key) for key in sorted(new))
        registry = er.async_get(hass)
        for key in known - current:
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, _unique_id(entry, key))
            if entity_id:
                registry.async_remove(entity_id)
        known.clear()
        known.update(current)

    sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(sync_entities))

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_UPDATED, coordinator.async_refresh))


def _unique_id(entry: ChoresConfigEntry, key: Key) -> str:
    return f"{entry.entry_id}_{key[0]}_{key[1]}"


class BalanceSensor(CoordinatorEntity[BalanceCoordinator], SensorEntity):
    """This week's balance for one kid in one currency."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = False

    def __init__(self, coordinator: BalanceCoordinator, entry: ChoresConfigEntry, key: Key) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = _unique_id(entry, key)
        row = coordinator.data[key]
        # Fixed at creation so the entity_id is e.g. sensor.ada_skjermtid.
        self._attr_name = f"{row.kid.name} {row.currency.name}"

    @property
    def _row(self) -> BalanceRow | None:
        return self.coordinator.data.get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self._row is not None

    @property
    def native_value(self) -> int | None:
        row = self._row
        return row.balance.total if row else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        row = self._row
        return row.currency.unit if row else None

    @property
    def icon(self) -> str | None:
        row = self._row
        return (row.currency.icon or None) if row else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        row = self._row
        if row is None:
            return None
        b = row.balance
        return {
            "kid": row.kid.name,
            "currency": row.currency.name,
            "earned": b.earned,
            "lost": b.lost,
            "adjustments": b.adjustments,
            "cap": b.cap,
            "week": row.week,
        }
