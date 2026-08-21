"""Switches: schedule enable/disable and the 2-hour manual heating."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CarHeaterCoordinator
from .entity import CarHeaterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the control switches."""
    coordinator: CarHeaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            CarHeaterScheduleSwitch(coordinator),
            CarHeaterManualSwitch(coordinator),
        ]
    )


class CarHeaterScheduleSwitch(CarHeaterEntity, SwitchEntity):
    """Enable/disable the whole heating schedule (e.g. for a holiday)."""

    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: CarHeaterCoordinator) -> None:
        super().__init__(coordinator, "switch", "schedule", "Schedule")

    @property
    def is_on(self) -> bool:
        return self.coordinator.schedule_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_schedule_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_schedule_enabled(False)


class CarHeaterManualSwitch(CarHeaterEntity, SwitchEntity):
    """Manual override: turn on to heat now for 2 hours, then auto-off."""

    _attr_icon = "mdi:car-turbocharger"

    def __init__(self, coordinator: CarHeaterCoordinator) -> None:
        super().__init__(coordinator, "switch", "manual", "Manual heating")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("manual_active")

    @property
    def extra_state_attributes(self) -> dict:
        manual_until = self.coordinator.manual_until
        return {"manual_until": manual_until.isoformat() if manual_until else None}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_manual(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_manual(False)
