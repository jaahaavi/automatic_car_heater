"""Binary sensor exposing the car heater status (and all display data)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up the status binary sensor."""
    coordinator: CarHeaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CarHeaterHeatingSensor(coordinator)])


class CarHeaterHeatingSensor(CarHeaterEntity, BinarySensorEntity):
    """True while the heater is (or should be) running."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: CarHeaterCoordinator) -> None:
        super().__init__(coordinator, "binary_sensor", "heating", "Heating")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("desired_on")

    @property
    def icon(self) -> str:
        return "mdi:car-defrost-front" if self.is_on else "mdi:car"

    @property
    def extra_state_attributes(self) -> dict:
        """Everything the Lovelace card needs, in one place."""
        data = self.coordinator.data or {}
        params = self.coordinator.params
        next_ready = data.get("next_ready")
        next_start = data.get("next_start")
        manual_until = data.get("manual_until")
        return {
            "integration": DOMAIN,
            "prefix": self.coordinator.prefix,
            "device_name": self.coordinator.entry.data.get("name"),
            "outside_temperature": data.get("outside_temperature"),
            "heating_duration": data.get("duration"),
            "scheduled_active": data.get("scheduled_active"),
            "manual_active": data.get("manual_active"),
            "manual_until": manual_until.isoformat() if manual_until else None,
            "next_ready": next_ready.isoformat() if next_ready else None,
            "next_start": next_start.isoformat() if next_start else None,
            "schedule_enabled": self.coordinator.schedule_enabled,
            "weekdays": self.coordinator.weekdays,
            "ready_time": self.coordinator.ready_time.strftime("%H:%M"),
            "min_temp": params["min_temp"],
            "max_temp": params["max_temp"],
            "min_time": params["min_time"],
            "max_time": params["max_time"],
            "off_delay": params["off_delay"],
        }
