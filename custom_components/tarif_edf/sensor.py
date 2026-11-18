"""Sensor platform for the Tarif EDF integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CONTRACT_POWER,
    CONF_CONTRACT_TYPE,
    CONTRACT_TYPE_BASE,
    CONTRACT_TYPE_HPHC,
    CONTRACT_TYPE_TEMPO,
    DOMAIN,
    TEMPO_COLORS_MAPPING,
)
from .coordinator import TarifEdfDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tarif EDF sensors from a config entry."""
    coordinator: TarifEdfDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]["coordinator"]

    contract_type = coordinator.data[CONF_CONTRACT_TYPE]
    contract_power = coordinator.data[CONF_CONTRACT_POWER]

    sensors: list[SensorEntity] = [
        TarifEdfSensor(
            coordinator,
            config_entry.entry_id,
            "contract_power",
            f"Puissance souscrite {contract_type} {contract_power}kVA",
            unit="kVA",
            icon="mdi:flash",
        ),
    ]

    if contract_type == CONTRACT_TYPE_BASE:
        sensors.append(
            TarifEdfSensor(
                coordinator,
                config_entry.entry_id,
                "base_variable_ttc",
                "Tarif Base TTC",
                unit="EUR/kWh",
            )
        )
    elif contract_type == CONTRACT_TYPE_HPHC:
        sensors.extend(
            [
                TarifEdfSensor(
                    coordinator,
                    config_entry.entry_id,
                    "hphc_variable_hc_ttc",
                    "Tarif Heures creuses TTC",
                    unit="EUR/kWh",
                ),
                TarifEdfSensor(
                    coordinator,
                    config_entry.entry_id,
                    "hphc_variable_hp_ttc",
                    "Tarif Heures pleines TTC",
                    unit="EUR/kWh",
                ),
            ]
        )
    elif contract_type == CONTRACT_TYPE_TEMPO:
        sensors.extend(
            [
                CouleurEdfSensor(
                    coordinator, config_entry.entry_id, "tempo_couleur", "Couleur actuelle"
                ),
                CouleurEdfSensor(
                    coordinator, config_entry.entry_id, "tempo_couleur_hier", "Couleur Hier"
                ),
                CouleurEdfSensor(
                    coordinator,
                    config_entry.entry_id,
                    "tempo_couleur_aujourdhui",
                    "Couleur Aujourd'hui",
                ),
                CouleurEdfSensor(
                    coordinator, config_entry.entry_id, "tempo_couleur_demain", "Couleur Demain"
                ),
                TarifEdfSensor(
                    coordinator,
                    config_entry.entry_id,
                    "tempo_variable_hc_ttc",
                    "Tarif Tempo Heures creuses TTC",
                    unit="EUR/kWh",
                ),
                TarifEdfSensor(
                    coordinator,
                    config_entry.entry_id,
                    "tempo_variable_hp_ttc",
                    "Tarif Tempo Heures pleines TTC",
                    unit="EUR/kWh",
                ),
                TarifEdfSensor(
                    coordinator,
                    config_entry.entry_id,
                    "tempo_variable_hc_bleu_ttc",
                    "Tarif Bleu Tempo Heures creuses TTC",
                    unit="EUR/kWh",
                ),
                TarifEdfSensor(
                    coordinator,
                    config_entry.entry_id,
                    "tempo_variable_hp_bleu_ttc",
                    "Tarif Bleu Tempo Heures pleines TTC",
                    unit="EUR/kWh",
                ),
                TarifEdfSensor(
                    coordinator,
                    config_entry.entry_id,
                    "tempo_variable_hc_blanc_ttc",
                    "Tarif Blanc Tempo Heures creuses TTC",
                    unit="EUR/kWh",
                ),
                TarifEdfSensor(
                    coordinator,
                    config_entry.entry_id,
                    "tempo_variable_hp_blanc_ttc",
                    "Tarif Blanc Tempo Heures pleines TTC",
                    unit="EUR/kWh",
                ),
                TarifEdfSensor(
                    coordinator,
                    config_entry.entry_id,
                    "tempo_variable_hc_rouge_ttc",
                    "Tarif Rouge Tempo Heures creuses TTC",
                    unit="EUR/kWh",
                ),
                TarifEdfSensor(
                    coordinator,
                    config_entry.entry_id,
                    "tempo_variable_hp_rouge_ttc",
                    "Tarif Rouge Tempo Heures pleines TTC",
                    unit="EUR/kWh",
                ),
            ]
        )

    if coordinator.data.get("tarif_actuel_ttc") is not None:
        sensors.append(
            TarifEdfSensor(
                coordinator,
                config_entry.entry_id,
                "tarif_actuel_ttc",
                f"Tarif actuel {contract_type} {contract_power}kVA TTC",
                unit="EUR/kWh",
            )
        )

    async_add_entities(sensors, True)


class TarifEdfSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tarif EDF tariff sensor."""

    def __init__(
        self,
        coordinator: TarifEdfDataUpdateCoordinator,
        entry_id: str,
        coordinator_key: str,
        name: str,
        unit: str | None = None,
        icon: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        contract_name = (
            f"{str.upper(coordinator.data[CONF_CONTRACT_TYPE])} "
            f"{coordinator.data[CONF_CONTRACT_POWER]}kVA"
        )

        self._coordinator_key = coordinator_key
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{coordinator_key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            name=f"Tarif EDF - {contract_name}",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"{entry_id}_{contract_name}")},
            manufacturer="Tarif EDF",
            model=contract_name,
        )

        if unit is not None:
            self._attr_unit_of_measurement = unit
            self._attr_icon = icon or "mdi:currency-eur"

        # Monetary sensors (EUR/kWh) are usable in the Energy dashboard cost section.
        # HA only accepts state_class TOTAL or TOTAL_INCREASING with device_class MONETARY.
        # TOTAL fits a tariff that can go up and down (unlike TOTAL_INCREASING which
        # would wrongly treat it as a cumulative meter and require last_reset).
        if unit is not None and "/" in unit:
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self.coordinator.data.get(self._coordinator_key)
        return "unavailable" if value is None else value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get(self._coordinator_key) is not None
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        return {"updated_at": self.coordinator.last_update_success_time}


class CouleurEdfSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tempo colour sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(TEMPO_COLORS_MAPPING.values())

    def __init__(
        self,
        coordinator: TarifEdfDataUpdateCoordinator,
        entry_id: str,
        coordinator_key: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        contract_name = (
            f"{str.upper(coordinator.data[CONF_CONTRACT_TYPE])} "
            f"{coordinator.data[CONF_CONTRACT_POWER]}kVA"
        )

        self._coordinator_key = coordinator_key
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{coordinator_key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            name=f"Tarif EDF - {contract_name}",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"{entry_id}_{contract_name}")},
            manufacturer="Tarif EDF",
            model=contract_name,
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self.coordinator.data.get(self._coordinator_key)
        return "unavailable" if value is None else value

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get(self._coordinator_key) is not None
        )

    @property
    def icon(self) -> str:
        """Return the icon based on the current colour state."""
        color = self.coordinator.data.get(self._coordinator_key)
        return {
            "bleu": "mdi:check-circle",
            "blanc": "mdi:circle-slice-8",
            "rouge": "mdi:alert-circle",
        }.get(color, "mdi:help-circle")

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        return {"updated_at": self.coordinator.last_update_success_time}
