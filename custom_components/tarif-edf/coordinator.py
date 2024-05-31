"""Data update coordinator for the Tarif EDF integration."""
from __future__ import annotations

from datetime import timedelta, datetime
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

def time_in_between(now, start, end):
    if start <= end:
        return start <= now < end
    else:
        return start <= now or now < end

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
            update_interval=timedelta(minutes=1),
        )
        self.config_entry = entry

    async def _async_update_data(self) -> dict[Platform, dict[str, Any]]:
        """Get the latest data from Tarif EDF and updates the state."""
        data = self.config_entry.data
        previous_data = None if self.data is None else self.data.copy()

        if previous_data is None:
            self.data = {
                "contract_power": data['contract_power'],
                "contract_type": data['contract_type'],
                "last_refresh_at": None,
                "tarif_actuel_ttc": None
            }

        fresh_data_limit = datetime.now() - timedelta(days=self.config_entry.options.get("refresh_interval", DEFAULT_REFRESH_INTERVAL))

        tarif_needs_update = self.data['last_refresh_at'] is None or self.data['last_refresh_at'] < fresh_data_limit

        self.logger.info('EDF tarif_needs_update '+('yes' if tarif_needs_update else 'no'))

        if tarif_needs_update:
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
                        self.data['last_refresh_at'] = datetime.now()

                        break
                response.close
            elif data['contract_type'] == CONTRACT_TYPE_TEMPO:
                response = await self.hass.async_add_executor_job(get_remote_file, TEMPO_COLOR_API_URL)
                tempo_color_data = response.json()

                if tempo_color_data['codeJour'] in [1, 2, 3]:
                    self.data['tempo_couleur'] = TEMPO_PRICES_DETAILS[tempo_color_data['codeJour']]['couleur']
                    self.data['tempo_variable_hp_ttc'] = TEMPO_PRICES_DETAILS[tempo_color_data['codeJour']]['hp']
                    self.data['tempo_variable_hc_ttc'] = TEMPO_PRICES_DETAILS[tempo_color_data['codeJour']]['hc']
                    self.data['last_refresh_at'] = datetime.now()

        off_peak_hours_ranges = self.config_entry.options.get("off_peak_hours_ranges")

        if data['contract_type'] == CONTRACT_TYPE_BASE:
            self.data['tarif_actuel_ttc'] = self.data['base_variable_ttc']
        elif data['contract_type'] in [CONTRACT_TYPE_HPHC, CONTRACT_TYPE_TEMPO] and off_peak_hours_ranges is not None:
            ranges = off_peak_hours_ranges.split(',')
            for range in ranges:
                if not re.match(r'([0-1]?[0-9]|2[0-3]):[0-5][0-9]-([0-1]?[0-9]|2[0-3]):[0-5][0-9]', range):
                    continue

                hours = range.split('-')
                start_at = datetime.strptime(hours[0], '%H:%M').time()
                end_at = datetime.strptime(hours[1], '%H:%M').time()

                contract_type_key = 'hphc' if data['contract_type'] == CONTRACT_TYPE_HPHC else 'tempo'
                tarif_actuel = self.data[contract_type_key+'_variable_hp_ttc']
                if time_in_between(datetime.now().time(), start_at, end_at):
                    tarif_actuel = self.data[contract_type_key+'_variable_hc_ttc']

                self.data['tarif_actuel_ttc'] = tarif_actuel

        self.logger.info('EDF Tarif')
        self.logger.info(self.data)

        return self.data
