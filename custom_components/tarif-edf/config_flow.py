"""Config flow for Tarif EDF integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector

from .const import (
    DOMAIN,
    DEFAULT_REFRESH_INTERVAL,
    CONTRACT_TYPE_BASE,
    CONTRACT_TYPE_HPHC,
    CONTRACT_TYPE_TEMPO,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER = vol.Schema(
    {
        vol.Required("contract_power", default="6"): SelectSelector({
            "options": ['3', '6', '9', '12', '15'],
            "mode": "dropdown"
        }),
        vol.Required("contract_type"): vol.In({
            CONTRACT_TYPE_BASE: 'Base',
            CONTRACT_TYPE_HPHC: 'Heures pleines / Heures creuses',
            CONTRACT_TYPE_TEMPO: 'Tempo',
        })
    }
)

@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tarif EDF."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        _LOGGER.debug("Setup process initiated by user.")

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER
            )

        return self.async_create_entry(title="Option "+str.upper(user_input['contract_type']) + ", " + user_input['contract_power']+"kVA", data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional("refresh_interval", default=self.config_entry.options.get("refresh_interval", DEFAULT_REFRESH_INTERVAL)): int,
                    vol.Optional("off_peak_hours_ranges", default=self.config_entry.options.get("off_peak_hours_ranges")): str,
                }
            ),
        )
