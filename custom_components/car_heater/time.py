"""Time entity for the 'car ready by' time."""

from __future__ import annotations

from datetime import time as dt_time

from homeassistant.components.time import TimeEntity
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
    """Set up the ready-time entity."""
    coordinator: CarHeaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CarHeaterReadyTime(coordinator)])


class CarHeaterReadyTime(CarHeaterEntity, TimeEntity):
    """The time of day the car must be ready to go."""

    _attr_icon = "mdi:clock-time-eight"

    def __init__(self, coordinator: CarHeaterCoordinator) -> None:
        super().__init__(coordinator, "time", "ready_time", "Ready time")

    @property
    def native_value(self) -> dt_time | None:
        return self.coordinator.ready_time

    async def async_set_value(self, value: dt_time) -> None:
        await self.coordinator.async_set_ready_time(value)
