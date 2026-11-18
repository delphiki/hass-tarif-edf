"""Data update coordinator for the Tarif EDF integration."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo
import csv
import logging
import re

import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_CONTRACT_POWER,
    CONF_CONTRACT_TYPE,
    CONF_OFF_PEAK_HOURS_RANGES,
    CONF_REFRESH_INTERVAL,
    CONTRACT_TYPE_BASE,
    CONTRACT_TYPE_HPHC,
    CONTRACT_TYPE_TEMPO,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    HTTP_TIMEOUT,
    TARIF_BASE_URL,
    TARIF_HPHC_URL,
    TARIF_TEMPO_URL,
    TEMPO_COLOR_API_URL,
    TEMPO_COLORS_MAPPING,
    TEMPO_DAY_START_AT,
    TEMPO_OFFPEAK_HOURS,
    TEMPO_TIMEZONE,
    TEMPO_TOMRROW_AVAILABLE_AT,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

_TEMPO_TZ = ZoneInfo(TEMPO_TIMEZONE)

_HOURS_RANGE_RE = re.compile(
    r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]-([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
)


def get_remote_file(url: str) -> requests.Response:
    """Fetch a remote file with a proper User-Agent and timeout."""
    return requests.get(
        url,
        stream=True,
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )


def str_to_time(value: str) -> time:
    return datetime.strptime(value, "%H:%M").time()


def time_in_between(now: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= now < end
    return start <= now or now < end


def get_tempo_color_from_code(code: int) -> str:
    return TEMPO_COLORS_MAPPING.get(code, TEMPO_COLORS_MAPPING[0])


def _now() -> datetime:
    """Current datetime in the Tempo timezone (Europe/Paris)."""
    return datetime.now(_TEMPO_TZ)


class TarifEdfDataUpdateCoordinator(TimestampDataUpdateCoordinator):
    """Data update coordinator for the Tarif EDF integration."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=entry.title,
            update_interval=timedelta(minutes=DEFAULT_UPDATE_INTERVAL_MINUTES),
        )

        self.config_entry = entry
        self.tempo_prices: list[dict[str, Any]] = []
        self._today: date = _now().date()

    # ------------------------------------------------------------------ #
    #  Tempo API                                                          #
    # ------------------------------------------------------------------ #

    async def get_tempo_day(self, day: date) -> dict[str, Any]:
        """Return the Tempo colour payload for *day*, using the local cache."""
        date_str = day.strftime("%Y-%m-%d")
        now = _now().time()
        check_limit = str_to_time(TEMPO_TOMRROW_AVAILABLE_AT)

        for price in self.tempo_prices:
            code_jour = price.get("codeJour")
            if price.get("dateJour") != date_str:
                continue
            # Confirmed colours (1-3) are always valid; "indéterminé" (0) only before the cutoff
            if code_jour in (1, 2, 3) or (code_jour == 0 and now < check_limit):
                return price

        url = f"{TEMPO_COLOR_API_URL}/{date_str}"
        response: requests.Response | None = None
        try:
            response = await self.hass.async_add_executor_job(get_remote_file, url)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as err:
            raise UpdateFailed(f"Error fetching Tempo day {date_str}: {err}") from err
        except (ValueError, KeyError) as err:
            raise UpdateFailed(f"Invalid Tempo response for {date_str}: {err}") from err
        finally:
            if response is not None:
                response.close()

        self.tempo_prices.append(payload)
        return payload

    # ------------------------------------------------------------------ #
    #  Tariff CSV                                                         #
    # ------------------------------------------------------------------ #

    def _parse_tarif_csv(
        self, content: str, contract_type: str, contract_power: str
    ) -> dict[str, float]:
        """Parse the data.gouv.fr CSV and return tariff fields for *contract_power*."""
        reader = csv.reader(content.splitlines(), delimiter=";")
        rows = list(reader)

        for row in rows:
            # Skip header / malformed rows
            if len(row) < 5 or row[1] != "" or row[2] != contract_power:
                continue

            def _f(index: int) -> float:
                return float(row[index].replace(",", "."))

            if contract_type == CONTRACT_TYPE_BASE:
                return {
                    "base_fixe_ttc": _f(4),
                    "base_variable_ttc": _f(6),
                }
            if contract_type == CONTRACT_TYPE_HPHC:
                return {
                    "hphc_fixe_ttc": _f(4),
                    "hphc_variable_hc_ttc": _f(6),
                    "hphc_variable_hp_ttc": _f(8),
                }
            if contract_type == CONTRACT_TYPE_TEMPO:
                if len(row) < 17:
                    _LOGGER.warning("Tempo CSV row too short, skipping: %s", row)
                    continue
                return {
                    "tempo_fixe_ttc": _f(4),
                    "tempo_variable_hc_bleu_ttc": _f(6),
                    "tempo_variable_hp_bleu_ttc": _f(8),
                    "tempo_variable_hc_blanc_ttc": _f(10),
                    "tempo_variable_hp_blanc_ttc": _f(12),
                    "tempo_variable_hc_rouge_ttc": _f(14),
                    "tempo_variable_hp_rouge_ttc": _f(16),
                }

        raise UpdateFailed(
            f"No tariff row found for power={contract_power} type={contract_type}"
        )

    async def _async_fetch_tarifs(self) -> dict[str, float]:
        """Download and parse the tariff CSV for the configured contract."""
        data = self.config_entry.data
        contract_type = data[CONF_CONTRACT_TYPE]
        contract_power = data[CONF_CONTRACT_POWER]

        url = {
            CONTRACT_TYPE_BASE: TARIF_BASE_URL,
            CONTRACT_TYPE_HPHC: TARIF_HPHC_URL,
            CONTRACT_TYPE_TEMPO: TARIF_TEMPO_URL,
        }[contract_type]

        response: requests.Response | None = None
        try:
            response = await self.hass.async_add_executor_job(get_remote_file, url)
            response.raise_for_status()
            return self._parse_tarif_csv(
                response.content.decode("utf-8"), contract_type, contract_power
            )
        except requests.RequestException as err:
            raise UpdateFailed(f"Error fetching tariff CSV: {err}") from err
        finally:
            if response is not None:
                response.close()

    # ------------------------------------------------------------------ #
    #  Tempo colours                                                      #
    # ------------------------------------------------------------------ #

    async def _async_update_tempo(self) -> None:
        """Update Tempo colour sensors and current HP/HC tarif."""
        today = _now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        tempo_yesterday = await self.get_tempo_day(yesterday)
        tempo_today = await self.get_tempo_day(today)
        tempo_tomorrow = await self.get_tempo_day(tomorrow)

        yesterday_color = get_tempo_color_from_code(tempo_yesterday["codeJour"])
        today_color = get_tempo_color_from_code(tempo_today["codeJour"])
        tomorrow_color = get_tempo_color_from_code(tempo_tomorrow["codeJour"])

        if self._today != today:
            # Day rollover: shift "aujourd'hui" → "hier"
            self._today = today
            self.data["tempo_couleur_hier"] = (
                self.data.get("tempo_couleur_aujourdhui")
                if yesterday_color == "indéterminé"
                else yesterday_color
            )
            self.data["tempo_couleur_aujourdhui"] = (
                self.data.get("tempo_couleur_demain")
                if today_color == "indéterminé"
                else today_color
            )
        else:
            if yesterday_color != "indéterminé":
                self.data["tempo_couleur_hier"] = yesterday_color
            if today_color != "indéterminé":
                self.data["tempo_couleur_aujourdhui"] = today_color

        self.data["tempo_couleur_demain"] = tomorrow_color

        # Determine which day's colour applies right now
        current_code = tempo_yesterday["codeJour"]
        if _now().time() >= str_to_time(TEMPO_DAY_START_AT):
            _LOGGER.debug("Using today's tempo prices")
            current_code = tempo_today["codeJour"]
        else:
            _LOGGER.debug("Using yesterday's tempo prices")

        if current_code in (1, 2, 3):
            color = get_tempo_color_from_code(current_code)
            self.data["tempo_couleur"] = color
            self.data["tempo_variable_hp_ttc"] = self.data[
                f"tempo_variable_hp_{color}_ttc"
            ]
            self.data["tempo_variable_hc_ttc"] = self.data[
                f"tempo_variable_hc_{color}_ttc"
            ]

    # ------------------------------------------------------------------ #
    #  Current tariff                                                     #
    # ------------------------------------------------------------------ #

    def _compute_tarif_actuel(self) -> None:
        """Compute the currently applicable tariff based on contract type and off-peak ranges."""
        data = self.config_entry.data
        contract_type = data[CONF_CONTRACT_TYPE]

        if contract_type == CONTRACT_TYPE_BASE:
            self.data["tarif_actuel_ttc"] = self.data["base_variable_ttc"]
            return

        if contract_type not in (CONTRACT_TYPE_HPHC, CONTRACT_TYPE_TEMPO):
            return

        default_offpeak = (
            TEMPO_OFFPEAK_HOURS if contract_type == CONTRACT_TYPE_TEMPO else None
        )
        ranges_str = self.config_entry.options.get(
            CONF_OFF_PEAK_HOURS_RANGES, default_offpeak
        )
        if ranges_str is None:
            return

        prefix = "hphc" if contract_type == CONTRACT_TYPE_HPHC else "tempo"
        tarif = self.data[f"{prefix}_variable_hp_ttc"]
        now = _now().time()

        for rng in ranges_str.split(","):
            rng = rng.strip()
            if not _HOURS_RANGE_RE.fullmatch(rng):
                _LOGGER.debug("Ignoring invalid off-peak range: %s", rng)
                continue
            start_str, end_str = rng.split("-")
            if time_in_between(now, str_to_time(start_str), str_to_time(end_str)):
                tarif = self.data[f"{prefix}_variable_hc_ttc"]
                break

        self.data["tarif_actuel_ttc"] = tarif

    # ------------------------------------------------------------------ #
    #  Main update                                                        #
    # ------------------------------------------------------------------ #

    async def _async_update_data(self) -> dict[str, Any]:
        """Get the latest data from Tarif EDF and update the state."""
        data = self.config_entry.data

        if self.data is None:
            self.data = {
                "contract_power": data[CONF_CONTRACT_POWER],
                "contract_type": data[CONF_CONTRACT_TYPE],
                "last_refresh_at": None,
                "tarif_actuel_ttc": None,
            }

        # Refresh tariff CSV only when the cache is stale
        refresh_days = self.config_entry.options.get(
            CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
        )
        fresh_limit = _now() - timedelta(days=refresh_days)
        last_refresh = self.data.get("last_refresh_at")

        if last_refresh is None or last_refresh < fresh_limit:
            _LOGGER.debug("Tariff CSV cache stale, re-fetching")
            self.data.update(await self._async_fetch_tarifs())
            self.data["last_refresh_at"] = _now()

        if data[CONF_CONTRACT_TYPE] == CONTRACT_TYPE_TEMPO:
            await self._async_update_tempo()

        self._compute_tarif_actuel()

        _LOGGER.debug("EDF data: %s", self.data)
        return self.data
