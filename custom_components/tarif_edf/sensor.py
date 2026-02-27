"""Sensor platform for the Tarif EDF integration."""

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONTRACT_TYPE_BASE,
    CONTRACT_TYPE_HPHC,
    CONTRACT_TYPE_TEMPO,
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

    contract_type = coordinator.data["contract_type"]
    contract_power = coordinator.data["contract_power"]

    sensors = [
        TarifEdfSensor(
            coordinator,
            "contract_power",
            f"Puissance souscrite {contract_type} {contract_power}kVA",
            unit_of_measurement="kVA",
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    ]

    if contract_type == CONTRACT_TYPE_BASE:
        sensors.extend(
            [
                TarifEdfSensor(
                    coordinator,
                    "base_variable_ttc",
                    "Tarif Base TTC",
                    "EUR/kWh",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                TarifEdfSensor(
                    coordinator,
                    "base_abonnement_ttc",
                    "Tarif Abonnement Base TTC",
                    "EUR/mois",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
            ]
        )

    elif contract_type == CONTRACT_TYPE_HPHC:
        sensors.extend(
            [
                TarifEdfSensor(
                    coordinator,
                    "hphc_variable_hc_ttc",
                    "Tarif Heures creuses TTC",
                    "EUR/kWh",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                TarifEdfSensor(
                    coordinator,
                    "hphc_variable_hp_ttc",
                    "Tarif Heures pleines TTC",
                    "EUR/kWh",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                TarifEdfSensor(
                    coordinator,
                    "hphc_abonnement_ttc",
                    "Tarif Abonnement HPHC TTC",
                    "EUR/mois",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
            ]
        )

    elif contract_type == CONTRACT_TYPE_TEMPO:
        sensors.extend(
            [
                # Current and daily color sensors (no state_class for text values)
                TarifEdfSensor(
                    coordinator,
                    "tempo_couleur",
                    "Tarif Tempo Couleur",
                    state_class=None,
                ),
                TarifEdfSensor(
                    coordinator,
                    "tempo_couleur_hier",
                    "Tarif Tempo Couleur Hier",
                    state_class=None,
                ),
                TarifEdfSensor(
                    coordinator,
                    "tempo_couleur_aujourdhui",
                    "Tarif Tempo Couleur Aujourd'hui",
                    state_class=None,
                ),
                TarifEdfSensor(
                    coordinator,
                    "tempo_couleur_demain",
                    "Tarif Tempo Couleur Demain",
                    state_class=None,
                ),
                # Current rates
                TarifEdfSensor(
                    coordinator,
                    "tempo_variable_hc_ttc",
                    "Tarif Tempo Heures creuses TTC",
                    "EUR/kWh",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                TarifEdfSensor(
                    coordinator,
                    "tempo_variable_hp_ttc",
                    "Tarif Tempo Heures pleines TTC",
                    "EUR/kWh",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                # Blue day rates
                TarifEdfSensor(
                    coordinator,
                    "tempo_variable_hc_bleu_ttc",
                    "Tarif Bleu Tempo Heures creuses TTC",
                    "EUR/kWh",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                TarifEdfSensor(
                    coordinator,
                    "tempo_variable_hp_bleu_ttc",
                    "Tarif Bleu Tempo Heures pleines TTC",
                    "EUR/kWh",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                # White day rates
                TarifEdfSensor(
                    coordinator,
                    "tempo_variable_hc_blanc_ttc",
                    "Tarif Blanc Tempo Heures creuses TTC",
                    "EUR/kWh",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                TarifEdfSensor(
                    coordinator,
                    "tempo_variable_hp_blanc_ttc",
                    "Tarif Blanc Tempo Heures pleines TTC",
                    "EUR/kWh",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                # Red day rates
                TarifEdfSensor(
                    coordinator,
                    "tempo_variable_hc_rouge_ttc",
                    "Tarif Rouge Tempo Heures creuses TTC",
                    "EUR/kWh",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                TarifEdfSensor(
                    coordinator,
                    "tempo_variable_hp_rouge_ttc",
                    "Tarif Rouge Tempo Heures pleines TTC",
                    "EUR/kWh",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                # Subscription
                TarifEdfSensor(
                    coordinator,
                    "tempo_abonnement_ttc",
                    "Tarif Abonnement Tempo TTC",
                    "EUR/mois",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
            ]
        )

    # Current tariff sensor
    if coordinator.data.get("tarif_actuel_ttc") is not None:
        sensors.append(
            TarifEdfSensor(
                coordinator,
                "tarif_actuel_ttc",
                f"Tarif actuel {contract_type} {contract_power}kVA TTC",
                "EUR/kWh",
                state_class=SensorStateClass.MEASUREMENT,
            )
        )

    async_add_entities(sensors, False)


class TarifEdfSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tarif EDF sensor."""

    def __init__(
        self,
        coordinator: TarifEdfDataUpdateCoordinator,
        coordinator_key: str,
        name: str,
        unit_of_measurement: str | None = None,
        state_class: SensorStateClass | None = None,
        entity_category: EntityCategory | None = None,
    ) -> None:
        """Initialize the Tarif EDF sensor."""
        super().__init__(coordinator)
        contract_type = self.coordinator.data["contract_type"]
        contract_power = self.coordinator.data["contract_power"]
        contract_name = f"{contract_type.upper()} {contract_power}kVA"

        self._coordinator_key = coordinator_key

        # Use coordinator_key for unique_id to ensure uniqueness
        self._attr_unique_id = (
            f"tarif_edf_{contract_type}_{contract_power}_{coordinator_key}"
        )
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            name=f"Tarif EDF - {contract_name}",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"tarif_edf_{contract_type}_{contract_power}")},
            manufacturer="Tarif EDF",
            model=contract_name,
        )

        if unit_of_measurement is not None:
            self._attr_native_unit_of_measurement = unit_of_measurement

        if state_class is not None:
            self._attr_state_class = state_class

        if entity_category is not None:
            self._attr_entity_category = entity_category

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self.coordinator.data.get(self._coordinator_key)
        if value is None:
            return None
        return value

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            "updated_at": self.coordinator.last_update_success_time,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get(self._coordinator_key) is not None
        )
