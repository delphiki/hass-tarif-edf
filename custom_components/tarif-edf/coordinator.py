"""Data update coordinator for the Tarif EDF integration."""
from __future__ import annotations

from datetime import timedelta
import re
from typing import Any

import logging

import requests
import csv

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import TimestampDataUpdateCoordinator

from .const import (
    DEFAULT_REFRESH_INTERVAL,
    CONTRACT_TYPE_BASE,
    CONTRACT_TYPE_HPHC,
    CONTRACT_TYPE_TEMPO,
    TARIF_BASE_URL,
    TARIF_HPHC_URL,
    TEMPO_COLOR_API_URL,
    TEMPO_PRICES_DETAILS,
)

_LOGGER = logging.getLogger(__name__)

def get_remote_file(url: str):
    response = requests.get(url, stream = True)
    return response

class TarifEdfDataUpdateCoordinator(TimestampDataUpdateCoordinator):
    """Data update coordinator for the Tarif EDF integration."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=entry.title,
            update_interval=timedelta(days=entry.options.get("refresh_interval", DEFAULT_REFRESH_INTERVAL)),
        )
        self.config_entry = entry

    async def _async_update_data(self) -> dict[Platform, dict[str, Any]]:
        """Get the latest data from Tarif EDF and updates the state."""
        data = self.config_entry.data
        self.data = {
            "contract_power": data['contract_power'],
            "contract_type": data['contract_type'],
        }

        if data['contract_type'] in [CONTRACT_TYPE_BASE, CONTRACT_TYPE_HPHC]:
            if data['contract_type'] == CONTRACT_TYPE_BASE:
                url = TARIF_BASE_URL
            elif data['contract_type'] == CONTRACT_TYPE_HPHC:
                url = TARIF_HPHC_URL

            response = await self.hass.async_add_executor_job(get_remote_file, url)
            parsed_content = csv.reader(response.content.decode('utf-8').splitlines(), delimiter=';')
            rows = list(parsed_content)

            for row in rows:
                if row[1] == '' and row[2] == data['contract_power']:
                    if data['contract_type'] == CONTRACT_TYPE_BASE:
                        self.data['base_fixe_ttc'] = float(row[4].replace(",", "." ))
                        self.data['base_variable_ttc'] = float(row[6].replace(",", "." ))
                    elif data['contract_type'] == CONTRACT_TYPE_HPHC:
                        self.data['hphc_fixe_ttc'] = float(row[4].replace(",", "." ))
                        self.data['hphc_variable_hc_ttc'] = float(row[6].replace(",", "." ))
                        self.data['hphc_variable_hp_ttc'] = float(row[8].replace(",", "." ))

                    break
            response.close
        elif data['contract_type'] == CONTRACT_TYPE_TEMPO:
            response = await self.hass.async_add_executor_job(get_remote_file, TEMPO_COLOR_API_URL)
            tempo_color_data = response.json()

            if tempo_color_data['codeJour'] in [1, 2, 3]:
                self.data['tempo_couleur'] = TEMPO_PRICES_DETAILS[tempo_color_data['codeJour']]['couleur']
                self.data['tempo_variable_hp_ttc'] = TEMPO_PRICES_DETAILS[tempo_color_data['codeJour']]['hp']
                self.data['tempo_variable_hc_ttc'] = TEMPO_PRICES_DETAILS[tempo_color_data['codeJour']]['hc']

        self.logger.info(self.data)

        return self.data
