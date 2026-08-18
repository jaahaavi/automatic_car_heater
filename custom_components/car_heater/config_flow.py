"""Config and options flow for the Automatic Car Heater Timer."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

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
    DOMAIN,
)

_TEMP_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
)
_SWITCH_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain=["switch", "input_boolean"])
)


def _temp_number() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=-40, max=40, step=0.5, unit_of_measurement="°C",
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _time_number() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1, max=600, step=1, unit_of_measurement="min",
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _params_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Schema for the four optional parameters plus the off-delay."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_MIN_TEMP, default=defaults.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)
            ): _temp_number(),
            vol.Optional(
                CONF_MAX_TEMP, default=defaults.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)
            ): _temp_number(),
            vol.Optional(
                CONF_MIN_TIME, default=defaults.get(CONF_MIN_TIME, DEFAULT_MIN_TIME)
            ): _time_number(),
            vol.Optional(
                CONF_MAX_TIME, default=defaults.get(CONF_MAX_TIME, DEFAULT_MAX_TIME)
            ): _time_number(),
            vol.Optional(
                CONF_OFF_DELAY, default=defaults.get(CONF_OFF_DELAY, DEFAULT_OFF_DELAY)
            ): _time_number(),
        }
    )


class CarHeaterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First (and only) setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_TEMPERATURE_SENSOR: user_input[CONF_TEMPERATURE_SENSOR],
                CONF_HEATER_SWITCH: user_input[CONF_HEATER_SWITCH],
                CONF_MIN_TEMP: user_input[CONF_MIN_TEMP],
                CONF_MAX_TEMP: user_input[CONF_MAX_TEMP],
                CONF_MIN_TIME: user_input[CONF_MIN_TIME],
                CONF_MAX_TIME: user_input[CONF_MAX_TIME],
                CONF_OFF_DELAY: user_input[CONF_OFF_DELAY],
            }
            return self.async_create_entry(title=user_input[CONF_NAME], data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Car heater"): selector.TextSelector(),
                vol.Required(CONF_TEMPERATURE_SENSOR): _TEMP_SELECTOR,
                vol.Required(CONF_HEATER_SWITCH): _SWITCH_SELECTOR,
            }
        ).extend(_params_schema({}).schema)

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return CarHeaterOptionsFlow()


class CarHeaterOptionsFlow(OptionsFlow):
    """Edit the heating parameters after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Prefer previously-set options, fall back to the original setup data.
        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_params_schema(defaults)
        )
