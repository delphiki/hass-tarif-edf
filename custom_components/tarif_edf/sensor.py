from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.components.sensor import (
    SensorEntity,
)

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)


from .coordinator import TarifEdfDataUpdateCoordinator

from .const import (
    DOMAIN,
    CONTRACT_TYPE_BASE,
    CONTRACT_TYPE_HPHC,
    CONTRACT_TYPE_TEMPO,
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TarifEdfDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]["coordinator"]

    sensors = [
        TarifEdfSensor(coordinator, 'contract_power', f"Puissance souscrite {coordinator.data['contract_type']} {coordinator.data['contract_power']}kVA", 'kVA'),
    ]

    if coordinator.data['contract_type'] == CONTRACT_TYPE_BASE:
        sensors.extend([
            TarifEdfSensor(coordinator, 'base_fixe_ttc', 'Tarif Base Fixe TTC', 'EUR/mois'),
            TarifEdfSensor(coordinator, 'base_fixe_ht', 'Tarif Base Fixe HT', 'EUR/mois'),
            TarifEdfSensor(coordinator, 'base_variable_ttc', 'Tarif Base Variable TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'base_variable_ht', 'Tarif Base Variable HT', 'EUR/kWh'),
        ])
    elif coordinator.data['contract_type'] == CONTRACT_TYPE_HPHC:
        sensors.extend([
            TarifEdfSensor(coordinator, 'hphc_fixe_ttc', 'Tarif HPHC Fixe TTC', 'EUR/mois'),
            TarifEdfSensor(coordinator, 'hphc_fixe_ht', 'Tarif HPHC Fixe HT', 'EUR/mois'),
            TarifEdfSensor(coordinator, 'hphc_variable_hc_ttc', 'Tarif HPHC Heures Creuses TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'hphc_variable_hc_ht', 'Tarif HPHC Heures Creuses HT', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'hphc_variable_hp_ttc', 'Tarif HPHC Heures Pleines TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'hphc_variable_hp_ht', 'Tarif HPHC Heures Pleines HT', 'EUR/kWh'),
        ])
    elif coordinator.data['contract_type'] == CONTRACT_TYPE_TEMPO:
        sensors.extend([
            TarifEdfSensor(coordinator, 'tempo_fixe_ttc', 'Tarif Tempo Fixe TTC', 'EUR/mois'),
            TarifEdfSensor(coordinator, 'tempo_fixe_ht', 'Tarif Tempo Fixe HT', 'EUR/mois'),
            TarifEdfSensor(coordinator, 'tempo_variable_hc_bleu_ttc', 'Tarif Bleu Tempo Heures Creuses TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hc_bleu_ht', 'Tarif Bleu Tempo Heures Creuses HT', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hp_bleu_ttc', 'Tarif Bleu Tempo Heures Pleines TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hp_bleu_ht', 'Tarif Bleu Tempo Heures Pleines HT', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hc_blanc_ttc', 'Tarif Blanc Tempo Heures Creuses TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hc_blanc_ht', 'Tarif Blanc Tempo Heures Creuses HT', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hp_blanc_ttc', 'Tarif Blanc Tempo Heures Pleines TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hp_blanc_ht', 'Tarif Blanc Tempo Heures Pleines HT', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hc_rouge_ttc', 'Tarif Rouge Tempo Heures Creuses TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hc_rouge_ht', 'Tarif Rouge Tempo Heures Creuses HT', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hp_rouge_ttc', 'Tarif Rouge Tempo Heures Pleines TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hp_rouge_ht', 'Tarif Rouge Tempo Heures Pleines HT', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_couleur', 'Tarif Tempo Couleur'),
            TarifEdfSensor(coordinator, 'tempo_couleur_hier', 'Tarif Tempo Couleur Hier'),
            TarifEdfSensor(coordinator, 'tempo_couleur_aujourdhui', "Tarif Tempo Couleur Aujourd'hui"),
            TarifEdfSensor(coordinator, 'tempo_couleur_demain', 'Tarif Tempo Couleur Demain'),
        ])

    if coordinator.data['tarif_actuel_ttc'] is not None:
        sensors.append(
            TarifEdfSensor(coordinator, 'tarif_actuel_ttc', f"Tarif actuel {coordinator.data['contract_type']} {coordinator.data['contract_power']}kVA TTC", 'EUR/kWh')
        )

    if coordinator.data['tarif_actuel_ht'] is not None:
        sensors.append(
            TarifEdfSensor(coordinator, 'tarif_actuel_ht', f"Tarif actuel {coordinator.data['contract_type']} {coordinator.data['contract_power']}kVA HT", 'EUR/kWh')
        )

    async_add_entities(sensors, False)

class TarifEdfSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tarif EDF sensor."""

    def __init__(self, coordinator, coordinator_key: str, name: str, unit_of_measurement: str = None, icon: str = None) -> None:
        """Initialize the Tarif EDF sensor."""
        super().__init__(coordinator)
        contract_name = str.upper(self.coordinator.data['contract_type']) + " " + self.coordinator.data['contract_power'] + "kVA"

        self._coordinator_key = coordinator_key
        self._name = name
        self._attr_unique_id = f"tarif_edf_{self._name}"
        self._attr_name = name
        self._attr_icon = "mdi:currency-eur" if unit_of_measurement and "EUR" in unit_of_measurement else icon
        self._attr_entity_registry_enabled_default = not coordinator_key.endswith('_ht')
        self._attr_device_info = DeviceInfo(
            name=f"Tarif EDF - {contract_name}",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={
                (DOMAIN, f"Tarif EDF - {contract_name}")
            },
            manufacturer="Tarif EDF",
            model=contract_name,
        )
        if (unit_of_measurement is not None):
            self._attr_unit_of_measurement = unit_of_measurement

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data[self._coordinator_key] is None:
            return 'unavailable'
        else:
            return self.coordinator.data[self._coordinator_key]

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            'updated_at': self.coordinator.last_update_success_time,
            'unit_of_measurement': self._attr_unit_of_measurement,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data[self._coordinator_key] is not None
