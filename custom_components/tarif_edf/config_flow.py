"""Config flow for Tarif EDF integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import (
    DOMAIN,
    DEFAULT_REFRESH_INTERVAL,
    CONTRACT_TYPE_BASE,
    CONTRACT_TYPE_HPHC,
    CONTRACT_TYPE_TEMPO,
    TEMPO_OFFPEAK_HOURS,
)

_LOGGER = logging.getLogger(__name__)

# Power levels vary by contract type
POWER_LEVELS_BASE = ["3", "6", "9", "12", "15"]
POWER_LEVELS_HPHC_TEMPO = ["6", "9", "12", "15", "18", "30", "36"]

POWER_LEVELS_BY_CONTRACT = {
    CONTRACT_TYPE_BASE: POWER_LEVELS_BASE,
    CONTRACT_TYPE_HPHC: POWER_LEVELS_HPHC_TEMPO,
    CONTRACT_TYPE_TEMPO: POWER_LEVELS_HPHC_TEMPO,
}

STEP_CONTRACT_TYPE = vol.Schema(
    {
        vol.Required("contract_type"): vol.In(
            {
                CONTRACT_TYPE_BASE: "Base",
                CONTRACT_TYPE_HPHC: "Heures pleines / Heures creuses",
                CONTRACT_TYPE_TEMPO: "Tempo",
            }
        )
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tarif EDF."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._contract_type: str | None = None
        self._contract_power: str | None = None

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step triggered by the user."""
        _LOGGER.debug("Setup process initiated by user.")
        return await self.async_step_contract()

    async def async_step_contract(self, user_input: dict | None = None) -> FlowResult:
        """Handle the first step: contract type selection."""
        if user_input is None:
            return self.async_show_form(
                step_id="contract", data_schema=STEP_CONTRACT_TYPE
            )

        self._contract_type = user_input["contract_type"]
        return await self.async_step_power()

    async def async_step_power(self, user_input: dict | None = None) -> FlowResult:
        """Handle the second step: power level selection."""
        if user_input is None:
            power_levels = POWER_LEVELS_BY_CONTRACT.get(
                self._contract_type, POWER_LEVELS_HPHC_TEMPO
            )
            default_power = "6" if "6" in power_levels else power_levels[0]

            schema = vol.Schema(
                {
                    vol.Required(
                        "contract_power", default=default_power
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=power_levels,
                            mode="dropdown",
                        )
                    ),
                }
            )
            return self.async_show_form(step_id="power", data_schema=schema)

        self._contract_power = user_input["contract_power"]

        # For HPHC, ask for off-peak hours
        if self._contract_type == CONTRACT_TYPE_HPHC:
            return await self.async_step_offpeak_hours()

        # For BASE and TEMPO, create entry directly
        return self._create_entry()

    async def async_step_offpeak_hours(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the off-peak hours step for HPHC contracts."""
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required("off_peak_hours_ranges"): str,
                }
            )
            return self.async_show_form(step_id="offpeak_hours", data_schema=schema)

        # Store off-peak hours in options
        return self._create_entry(
            options={"off_peak_hours_ranges": user_input["off_peak_hours_ranges"]}
        )

    def _create_entry(self, options: dict | None = None) -> FlowResult:
        """Create the config entry."""
        contract_type = self._contract_type
        contract_power = self._contract_power
        title = f"Option {contract_type.upper()}, {contract_power}kVA"

        return self.async_create_entry(
            title=title,
            data={
                "contract_type": contract_type,
                "contract_power": contract_power,
            },
            options=options or {},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry.entry_id)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry_id: str) -> None:
        """Initialize options flow."""
        self.config_entry_id = config_entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        config_entry = self.hass.config_entries.async_get_entry(self.config_entry_id)

        default_offpeak_hours = None
        if config_entry.data["contract_type"] == CONTRACT_TYPE_TEMPO:
            default_offpeak_hours = TEMPO_OFFPEAK_HOURS

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "refresh_interval",
                        default=config_entry.options.get(
                            "refresh_interval", DEFAULT_REFRESH_INTERVAL
                        ),
                    ): int,
                    vol.Optional(
                        "off_peak_hours_ranges",
                        default=config_entry.options.get(
                            "off_peak_hours_ranges", default_offpeak_hours
                        ),
                    ): str,
                }
            ),
        )
