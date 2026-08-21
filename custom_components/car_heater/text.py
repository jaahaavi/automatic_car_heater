"""Text entity storing the selected weekdays as a CSV string."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, WEEKDAYS
from .coordinator import CarHeaterCoordinator
from .entity import CarHeaterEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the weekdays text entity."""
    coordinator: CarHeaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CarHeaterWeekdaysText(coordinator)])


class CarHeaterWeekdaysText(CarHeaterEntity, TextEntity):
    """Selected weekdays as a CSV string, e.g. 'mon,tue,wed,thu,fri'.

    The Lovelace card presents this as weekday chips; the raw string is only
    the storage format.
    """

    _attr_icon = "mdi:calendar-week"
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 64
    # Comma separated list of the seven allowed abbreviations (or empty).
    _attr_pattern = r"^$|^(mon|tue|wed|thu|fri|sat|sun)(,(mon|tue|wed|thu|fri|sat|sun))*$"

    def __init__(self, coordinator: CarHeaterCoordinator) -> None:
        super().__init__(coordinator, "text", "weekdays", "Weekdays")

    @property
    def native_value(self) -> str:
        return ",".join(self.coordinator.weekdays)

    async def async_set_value(self, value: str) -> None:
        tokens = [t.strip().lower() for t in value.split(",") if t.strip()]
        weekdays = [d for d in WEEKDAYS if d in tokens]
        await self.coordinator.async_set_weekdays(weekdays)
