"""Shared base entity for the Automatic Car Heater Timer."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME
from .coordinator import CarHeaterCoordinator


class CarHeaterEntity(CoordinatorEntity[CarHeaterCoordinator]):
    """Base class giving every entity a deterministic entity_id and device."""

    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: CarHeaterCoordinator,
        platform: str,
        key: str,
        name_suffix: str,
    ) -> None:
        """Initialise a car heater entity.

        ``platform`` is the domain the entity lives in (e.g. "sensor"). The
        entity_id is forced to ``<platform>.<prefix>_<key>`` so the Lovelace
        card can reliably derive all sibling entities from a single prefix.
        """
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_name = f"{coordinator.entry.data[CONF_NAME]} {name_suffix}"
        self._attr_device_info = coordinator.device_info
        self.entity_id = f"{platform}.{coordinator.prefix}_{key}"
