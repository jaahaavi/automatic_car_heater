"""Server-side control logic for the Automatic Car Heater Timer."""

from __future__ import annotations

import logging
from datetime import datetime, time as dt_time, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util, slugify

from .const import (
    CONF_HEATER_SWITCH,
    CONF_MAX_TEMP,
    CONF_MAX_TIME,
    CONF_MIN_TEMP,
    CONF_MIN_TIME,
    CONF_NAME,
    CONF_OFF_DELAY,
    CONF_TEMPERATURE_SENSOR,
    DEFAULT_MAX_TEMP,
    DEFAULT_MAX_TIME,
    DEFAULT_MIN_TEMP,
    DEFAULT_MIN_TIME,
    DEFAULT_OFF_DELAY,
    DEFAULT_READY_TIME,
    DEFAULT_WEEKDAYS,
    DOMAIN,
    MANUAL_OVERRIDE_MINUTES,
    STORAGE_VERSION,
    UPDATE_INTERVAL_SECONDS,
    WEEKDAYS,
)

_LOGGER = logging.getLogger(__name__)


def _parse_time(value: str) -> dt_time:
    """Parse a 'HH:MM:SS' (or 'HH:MM') string into a time."""
    parts = [int(p) for p in value.split(":")]
    while len(parts) < 3:
        parts.append(0)
    return dt_time(parts[0], parts[1], parts[2])


class CarHeaterCoordinator(DataUpdateCoordinator):
    """Runs the heater schedule and drives the physical switch."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.slug = slugify(entry.data[CONF_NAME])
        self.prefix = f"{DOMAIN}_{self.slug}"

        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self._unsub_state = None
        self._we_turned_on = False

        # Runtime (user adjustable) state — defaults, overwritten by async_load().
        self.schedule_enabled: bool = True
        self.weekdays: list[str] = list(DEFAULT_WEEKDAYS)
        self.ready_time: dt_time = _parse_time(DEFAULT_READY_TIME)
        self.manual_until: datetime | None = None

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _cfg(self, key: str, default):
        """Read a parameter, preferring options over the original data."""
        return self.entry.options.get(key, self.entry.data.get(key, default))

    @property
    def params(self) -> dict:
        """Return the resolved heating parameters."""
        return {
            "min_temp": float(self._cfg(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)),
            "max_temp": float(self._cfg(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)),
            "min_time": int(self._cfg(CONF_MIN_TIME, DEFAULT_MIN_TIME)),
            "max_time": int(self._cfg(CONF_MAX_TIME, DEFAULT_MAX_TIME)),
            "off_delay": int(self._cfg(CONF_OFF_DELAY, DEFAULT_OFF_DELAY)),
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Group all entities under a single device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.entry.data[CONF_NAME],
            manufacturer="Automatic Car Heater Timer",
            model="Car heater timer",
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    async def async_load(self) -> None:
        """Load runtime state from disk."""
        data = await self._store.async_load()
        if not data:
            return
        self.schedule_enabled = bool(data.get("schedule_enabled", True))
        self.weekdays = list(data.get("weekdays", DEFAULT_WEEKDAYS))
        if rt := data.get("ready_time"):
            try:
                self.ready_time = _parse_time(rt)
            except (ValueError, IndexError):
                _LOGGER.warning("Could not parse stored ready_time %s", rt)
        if mu := data.get("manual_until"):
            parsed = dt_util.parse_datetime(mu)
            if parsed:
                self.manual_until = parsed

    async def _async_save(self) -> None:
        """Persist runtime state to disk."""
        await self._store.async_save(
            {
                "schedule_enabled": self.schedule_enabled,
                "weekdays": self.weekdays,
                "ready_time": self.ready_time.strftime("%H:%M:%S"),
                "manual_until": self.manual_until.isoformat()
                if self.manual_until
                else None,
            }
        )

    # ------------------------------------------------------------------
    # Listeners / lifecycle
    # ------------------------------------------------------------------
    @callback
    def async_setup_listeners(self) -> None:
        """Refresh promptly when the temperature or switch changes."""
        entities = [
            self.entry.data[CONF_TEMPERATURE_SENSOR],
            self.entry.data[CONF_HEATER_SWITCH],
        ]
        self._unsub_state = async_track_state_change_event(
            self.hass, entities, self._handle_source_event
        )

    @callback
    def _handle_source_event(self, event: Event) -> None:
        self.hass.async_create_task(self.async_request_refresh())

    async def async_shutdown(self) -> None:
        """Clean up on unload."""
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None
        await super().async_shutdown()

    # ------------------------------------------------------------------
    # Setters used by the control entities
    # ------------------------------------------------------------------
    async def async_set_schedule_enabled(self, enabled: bool) -> None:
        self.schedule_enabled = enabled
        await self._async_save()
        await self.async_request_refresh()

    async def async_set_weekdays(self, weekdays: list[str]) -> None:
        self.weekdays = [d for d in WEEKDAYS if d in weekdays]
        await self._async_save()
        await self.async_request_refresh()

    async def async_set_ready_time(self, value: dt_time) -> None:
        self.ready_time = value
        await self._async_save()
        await self.async_request_refresh()

    async def async_set_manual(self, enabled: bool) -> None:
        if enabled:
            self.manual_until = dt_util.now() + timedelta(minutes=MANUAL_OVERRIDE_MINUTES)
        else:
            self.manual_until = None
        await self._async_save()
        await self.async_request_refresh()

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------
    def _outside_temperature(self) -> float | None:
        """Return the current outside temperature, or None if unavailable."""
        state = self.hass.states.get(self.entry.data[CONF_TEMPERATURE_SENSOR])
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE, ""):
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    def _duration_minutes(self, temp: float | None) -> int:
        """Heating time in minutes for a given outside temperature.

        - At or above min_temp -> min_time.
        - At or below max_temp -> max_time (stays capped below max_temp).
        - In between -> linear interpolation.
        - Unknown temperature -> max_time (fail safe / warm).
        """
        p = self.params
        if temp is None:
            return p["max_time"]
        if temp >= p["min_temp"]:
            return p["min_time"]
        if temp <= p["max_temp"]:
            return p["max_time"]
        span = p["min_temp"] - p["max_temp"]  # e.g. 5 - (-20) = 25
        if span <= 0:
            return p["max_time"]
        frac = (p["min_temp"] - temp) / span
        return int(round(p["min_time"] + (p["max_time"] - p["min_time"]) * frac))

    def _next_ready(self, now: datetime) -> datetime | None:
        """Next datetime the car must be ready, honouring the off-delay window."""
        if not self.schedule_enabled or not self.weekdays:
            return None
        off = timedelta(minutes=self.params["off_delay"])
        for offset in range(0, 8):
            day = (now + timedelta(days=offset)).date()
            if WEEKDAYS[day.weekday()] not in self.weekdays:
                continue
            candidate = datetime.combine(day, self.ready_time, tzinfo=now.tzinfo)
            # Only pick a candidate whose full heating window has not yet ended.
            if now <= candidate + off:
                return candidate
        return None

    def _evaluate(self, now: datetime) -> dict:
        """Compute the desired state without side effects."""
        p = self.params
        temp = self._outside_temperature()
        duration = self._duration_minutes(temp)
        next_ready = self._next_ready(now)
        next_start = (
            next_ready - timedelta(minutes=duration) if next_ready else None
        )
        off = timedelta(minutes=p["off_delay"])

        scheduled_active = bool(
            next_ready and next_start <= now <= next_ready + off
        )
        manual_active = bool(self.manual_until and now < self.manual_until)
        desired_on = scheduled_active or manual_active

        return {
            "desired_on": desired_on,
            "scheduled_active": scheduled_active,
            "manual_active": manual_active,
            "manual_until": self.manual_until,
            "outside_temperature": temp,
            "duration": duration,
            "next_ready": next_ready,
            "next_start": next_start,
        }

    async def _async_apply_switch(self, desired_on: bool) -> None:
        """Drive the physical switch to match the desired state."""
        switch_entity = self.entry.data[CONF_HEATER_SWITCH]
        state = self.hass.states.get(switch_entity)
        is_on = state is not None and state.state == "on"

        if desired_on and not is_on:
            await self.hass.services.async_call(
                "homeassistant", "turn_on", {"entity_id": switch_entity}, blocking=False
            )
            self._we_turned_on = True
        elif not desired_on and is_on and self._we_turned_on:
            await self.hass.services.async_call(
                "homeassistant", "turn_off", {"entity_id": switch_entity}, blocking=False
            )
            self._we_turned_on = False
        elif not desired_on:
            # Nothing to command; drop our ownership flag.
            self._we_turned_on = False

    async def _async_update_data(self) -> dict:
        """Periodic evaluation: expire manual boost, compute state, drive switch."""
        now = dt_util.now()

        if self.manual_until and now >= self.manual_until:
            self.manual_until = None
            await self._async_save()

        data = self._evaluate(now)
        await self._async_apply_switch(data["desired_on"])
        return data
