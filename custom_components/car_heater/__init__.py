"""The Automatic Car Heater Timer integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CARD_FILENAME,
    CARD_URL_PATH,
    DOMAIN,
    FRONTEND_REGISTERED,
    VERSION,
)
from .coordinator import CarHeaterCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
    Platform.TEXT,
]


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve and register the Lovelace card once, so no manual resource is needed."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(FRONTEND_REGISTERED):
        return

    card_path = Path(__file__).parent / "frontend" / CARD_FILENAME
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_PATH, str(card_path), False)]
    )
    add_extra_js_url(hass, f"{CARD_URL_PATH}?v={VERSION}")
    domain_data[FRONTEND_REGISTERED] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Automatic Car Heater Timer from a config entry."""
    await _async_register_frontend(hass)

    coordinator = CarHeaterCoordinator(hass, entry)
    await coordinator.async_load()
    coordinator.async_setup_listeners()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Runs the first evaluation (and applies the switch if needed).
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload when the options (parameters) change.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: CarHeaterCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok
