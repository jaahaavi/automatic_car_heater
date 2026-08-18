"""The Automatic Car Heater Timer integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.start import async_at_started

from .const import (
    CARD_FILENAME,
    CARD_URL_PATH,
    DOMAIN,
    RESOURCE_REGISTERED,
    STATIC_PATH_REGISTERED,
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

# Version-stamped URL so browsers refetch the card after an update.
CARD_URL_VERSIONED = f"{CARD_URL_PATH}?v={VERSION}"


# ----------------------------------------------------------------------
# Frontend card registration
# ----------------------------------------------------------------------
def _get_storage_resources(hass: HomeAssistant):
    """Return the Lovelace resource collection if in storage mode, else None."""
    try:
        from homeassistant.components.lovelace.const import DOMAIN as LOVELACE_DOMAIN
        from homeassistant.components.lovelace.resources import (
            ResourceStorageCollection,
        )
    except ImportError:  # pragma: no cover - lovelace always present in practice
        return None

    lovelace = hass.data.get(LOVELACE_DOMAIN)
    if lovelace is None:
        return None
    # Newer HA exposes a LovelaceData dataclass; older used a dict.
    resources = getattr(lovelace, "resources", None)
    if resources is None and isinstance(lovelace, dict):
        resources = lovelace.get("resources")
    if isinstance(resources, ResourceStorageCollection):
        return resources
    return None


async def _async_add_card_resource(hass: HomeAssistant) -> None:
    """Register the card as a Lovelace module resource (storage mode).

    Falls back to script injection for YAML-mode dashboards, which cannot be
    edited programmatically.
    """
    resources = _get_storage_resources(hass)
    if resources is None:
        add_extra_js_url(hass, CARD_URL_VERSIONED)
        _LOGGER.info(
            "Lovelace is in YAML mode; loaded the car heater card via script "
            "injection. You may instead add '%s' as a 'module' resource.",
            CARD_URL_PATH,
        )
        return

    try:
        if not getattr(resources, "loaded", False):
            await resources.async_load()
            resources.loaded = True

        for item in resources.async_items():
            if item.get("url", "").split("?", 1)[0] == CARD_URL_PATH:
                # Already present — bump the version query if needed.
                if item.get("url") != CARD_URL_VERSIONED:
                    await resources.async_update_item(
                        item["id"], {"url": CARD_URL_VERSIONED}
                    )
                    _LOGGER.debug("Updated car heater card resource to %s", VERSION)
                return

        await resources.async_create_item(
            {"res_type": "module", "url": CARD_URL_VERSIONED}
        )
        _LOGGER.info("Registered the car heater card as a Lovelace module resource")
    except Exception as err:  # noqa: BLE001 - defensive; fall back gracefully
        _LOGGER.warning(
            "Could not register the Lovelace resource (%s); using script "
            "injection instead",
            err,
        )
        add_extra_js_url(hass, CARD_URL_VERSIONED)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the card file and register it as a resource, once per HA instance."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    if not domain_data.get(STATIC_PATH_REGISTERED):
        card_path = Path(__file__).parent / "frontend" / CARD_FILENAME
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_PATH, str(card_path), False)]
        )
        domain_data[STATIC_PATH_REGISTERED] = True

    if domain_data.get(RESOURCE_REGISTERED):
        return
    domain_data[RESOURCE_REGISTERED] = True

    # Defer until HA has started so Lovelace resources are available (and so a
    # freshly-added entry at runtime registers promptly).
    @callback
    def _schedule(_hass: HomeAssistant) -> None:
        _hass.async_create_task(_async_add_card_resource(_hass))

    async_at_started(hass, _schedule)


# ----------------------------------------------------------------------
# Config entry lifecycle
# ----------------------------------------------------------------------
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


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up the auto-registered card resource when the last entry is removed."""
    if any(
        e.entry_id != entry.entry_id
        for e in hass.config_entries.async_entries(DOMAIN)
    ):
        return  # other instances still use the card

    resources = _get_storage_resources(hass)
    if resources is None:
        return
    try:
        if not getattr(resources, "loaded", False):
            await resources.async_load()
            resources.loaded = True
        for item in list(resources.async_items()):
            if item.get("url", "").split("?", 1)[0] == CARD_URL_PATH:
                await resources.async_delete_item(item["id"])
                _LOGGER.info("Removed the car heater card Lovelace resource")
    except Exception as err:  # noqa: BLE001 - best effort cleanup
        _LOGGER.debug("Could not remove the Lovelace resource: %s", err)
