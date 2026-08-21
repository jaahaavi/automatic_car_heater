"""Timestamp sensors: next ready time and next heating start time."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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
    """Set up the timestamp sensors."""
    coordinator: CarHeaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            CarHeaterTimestampSensor(
                coordinator, "next_ready", "Next ready", "mdi:car-clock"
            ),
            CarHeaterTimestampSensor(
                coordinator, "next_start", "Next start", "mdi:clock-start"
            ),
        ]
    )


class CarHeaterTimestampSensor(CarHeaterEntity, SensorEntity):
    """A datetime value taken from the coordinator data."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: CarHeaterCoordinator,
        key: str,
        name_suffix: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, "sensor", key, name_suffix)
        self._key = key
        self._attr_icon = icon

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.data.get(self._key)
