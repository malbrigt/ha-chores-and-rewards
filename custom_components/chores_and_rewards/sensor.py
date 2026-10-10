"""Balance sensors: one HA device per kid, one sensor per active currency (spec §12).

e.g. device "Ada" with sensor "Skjermtid" → sensor.ada_skjermtid. Push-updated: a
coordinator without polling refreshes (debounced) on every data change. Devices and
sensors follow kids and currencies being added, renamed, deactivated or deleted.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from . import ChoresConfigEntry
from .const import DOMAIN, NAME, SIGNAL_UPDATED
from .db import Repo
from .logic import Balance, Currency, Kid, week_start
from .store import ChoresStore, week_balances

_LOGGER = logging.getLogger(__name__)

# Coordinator-based, no polling: entity updates don't need to be limited.
PARALLEL_UPDATES = 0

type Key = tuple[int, int]  # (kid_id, currency_id)


@dataclass(frozen=True)
class BalanceRow:
    kid: Kid
    currency: Currency
    balance: Balance
    week: str


def _read(repo: Repo, today: date) -> dict[Key, BalanceRow]:
    week = week_start(today)
    kids = {k.id: k for k in repo.list_kids()}
    currencies = {c.id: c for c in repo.list_currencies()}
    balances = week_balances(repo, week, today)
    return {
        (kid_id, cur_id): BalanceRow(kids[kid_id], currencies[cur_id], balance, week.isoformat())
        for kid_id, per_currency in balances.items()
        for cur_id, balance in per_currency.items()
    }


class BalanceCoordinator(DataUpdateCoordinator[dict[Key, BalanceRow]]):
    """Holds every kid × currency balance; refreshed on change, never polled."""

    def __init__(self, hass: HomeAssistant, entry: ChoresConfigEntry, store: ChoresStore) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} balances",
            update_interval=None,
            # Bursts (a rollover, a save that also refreshes today) become one DB read.
            request_refresh_debouncer=Debouncer(hass, _LOGGER, cooldown=1.0, immediate=True),
        )
        self.store = store

    async def _async_update_data(self) -> dict[Key, BalanceRow]:
        today = self.store.today()
        return await self.store.async_read(lambda repo: _read(repo, today))


def _device_identifier(entry: ChoresConfigEntry, kid_id: int) -> tuple[str, str]:
    return (DOMAIN, f"{entry.entry_id}_kid_{kid_id}")


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
        """Add sensors for new pairs; keep device names in sync; remove what disappeared."""
        current = set(coordinator.data)
        new = current - known
        if new:
            async_add_entities(BalanceSensor(coordinator, entry, key) for key in sorted(new))
        devices = dr.async_get(hass)
        kids = {key[0]: row.kid for key, row in coordinator.data.items()}
        for kid_id, kid in kids.items():
            device = devices.async_get_device(identifiers={_device_identifier(entry, kid_id)})
            if device is not None and device.name != kid.name:
                devices.async_update_device(device.id, name=kid.name)
        gone_kids = {key[0] for key in known} - set(kids)
        for kid_id in gone_kids:  # removes the kid's device and its entities (stale devices)
            device = devices.async_get_device(identifiers={_device_identifier(entry, kid_id)})
            if device is not None:
                devices.async_update_device(device.id, remove_config_entry_id=entry.entry_id)
        entities = er.async_get(hass)
        for key in known - current:  # e.g. a currency was deactivated
            if key[0] in gone_kids:
                continue
            entity_id = entities.async_get_entity_id("sensor", DOMAIN, _unique_id(entry, key))
            if entity_id:
                entities.async_remove(entity_id)
        known.clear()
        known.update(current)

    sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(sync_entities))
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_UPDATED, coordinator.async_request_refresh)
    )


def _unique_id(entry: ChoresConfigEntry, key: Key) -> str:
    return f"{entry.entry_id}_{key[0]}_{key[1]}"


class BalanceSensor(CoordinatorEntity[BalanceCoordinator], SensorEntity):
    """This week's balance for one kid in one currency."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: BalanceCoordinator, entry: ChoresConfigEntry, key: Key) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = _unique_id(entry, key)
        kid = coordinator.data[key].kid
        self._attr_device_info = DeviceInfo(
            identifiers={_device_identifier(entry, kid.id)},
            name=kid.name,
            manufacturer=NAME,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def _row(self) -> BalanceRow | None:
        return self.coordinator.data.get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self._row is not None

    @property
    def name(self) -> str | None:
        row = self._row
        return row.currency.name if row else None

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
        # The icon is user data (set per currency), so it can't live in icons.json.
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
            "earned": b.earned,
            "lost": b.lost,
            "adjustments": b.adjustments,
            "cap": b.cap,
            "week": row.week,
        }
