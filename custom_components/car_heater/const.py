"""Constants for the Automatic Car Heater Timer integration."""

from __future__ import annotations

DOMAIN = "car_heater"
VERSION = "1.2.1"

# Frontend (Lovelace card) auto-registration
CARD_URL_PATH = "/car_heater_frontend/car-heater-card.js"
CARD_FILENAME = "car-heater-card.js"
STATIC_PATH_REGISTERED = "static_path_registered"
RESOURCE_REGISTERED = "resource_registered"

# Config keys (config flow / options)
CONF_NAME = "name"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_HEATER_SWITCH = "heater_switch"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_MIN_TIME = "min_time"
CONF_MAX_TIME = "max_time"
CONF_OFF_DELAY = "off_delay"

# Defaults (per the specification)
DEFAULT_MIN_TEMP = 5.0        # °C at (or above) which the minimum heating time is used
DEFAULT_MAX_TEMP = -20.0      # °C at (or below) which the maximum heating time is used
DEFAULT_MIN_TIME = 30         # minutes of heating at min_temp
DEFAULT_MAX_TIME = 120        # minutes of heating at max_temp
DEFAULT_OFF_DELAY = 15        # minutes to keep heating after the ready time
MANUAL_OVERRIDE_MINUTES = 120  # 2 hour manual heating

# Weekday order matching Python's datetime.weekday() (Mon=0 ... Sun=6)
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DEFAULT_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]
DEFAULT_READY_TIME = "07:30:00"

# Runtime persistence
STORAGE_VERSION = 1
UPDATE_INTERVAL_SECONDS = 30
