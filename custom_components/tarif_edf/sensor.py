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
    TEMPO_FORECAST_DAYS,
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
            TarifEdfSensor(coordinator, 'base_variable_ttc', 'Tarif Base TTC', 'EUR/kWh'),
        ])
    elif coordinator.data['contract_type'] == CONTRACT_TYPE_HPHC:
        sensors.extend([
            TarifEdfSensor(coordinator, 'hphc_variable_hc_ttc', 'Tarif Heures creuses TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'hphc_variable_hp_ttc', 'Tarif Heures pleines TTC', 'EUR/kWh'),
        ])
    elif coordinator.data['contract_type'] == CONTRACT_TYPE_TEMPO:
        sensors.extend([
            TarifEdfSensor(coordinator, 'tempo_couleur', 'Tarif Tempo Couleur'),
            TarifEdfSensor(coordinator, 'tempo_couleur_hier', 'Tarif Tempo Couleur Hier'),
            TarifEdfSensor(coordinator, 'tempo_couleur_aujourdhui', "Tarif Tempo Couleur Aujourd'hui"),
            TarifEdfSensor(coordinator, 'tempo_couleur_demain', 'Tarif Tempo Couleur Demain'),
            TarifEdfSensor(coordinator, 'tempo_variable_hc_ttc', 'Tarif Tempo Heures creuses TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hp_ttc', 'Tarif Tempo Heures pleines TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hc_bleu_ttc', 'Tarif Bleu Tempo Heures creuses TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hp_bleu_ttc', 'Tarif Bleu Tempo Heures pleines TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hc_rouge_ttc', 'Tarif Rouge Tempo Heures creuses TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hp_rouge_ttc', 'Tarif Rouge Tempo Heures pleines TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hc_blanc_ttc', 'Tarif Blanc Tempo Heures creuses TTC', 'EUR/kWh'),
            TarifEdfSensor(coordinator, 'tempo_variable_hp_blanc_ttc', 'Tarif Blanc Tempo Heures pleines TTC', 'EUR/kWh'),
        ])
        # Capteurs de prévisions Tempo (J+1 à J+9)
        for day in range(1, TEMPO_FORECAST_DAYS + 1):
            sensors.append(
                TarifEdfForecastSensor(
                    coordinator,
                    f'tempo_prevision_j{day}_couleur',
                    f'Tempo Prévision J+{day}',
                    day
                )
            )

    # Capteur d'abonnement annuel TTC (inclut la majoration auto-producteur
    # avec injection si l'option est activée)
    fixe_key = {
        CONTRACT_TYPE_BASE: 'base_fixe_ttc',
        CONTRACT_TYPE_HPHC: 'hphc_fixe_ttc',
        CONTRACT_TYPE_TEMPO: 'tempo_fixe_ttc',
    }.get(coordinator.data['contract_type'])
    if fixe_key is not None and coordinator.data.get(fixe_key) is not None:
        sensors.append(
            TarifEdfSensor(coordinator, fixe_key, f"Abonnement {coordinator.data['contract_type']} {coordinator.data['contract_power']}kVA TTC", 'EUR/an')
        )

    # Abonnement en €/h (mois courant) : à intégrer pour obtenir le coût total
    if coordinator.data.get('abonnement_horaire_ttc') is not None:
        sensors.append(
            TarifEdfSensor(coordinator, 'abonnement_horaire_ttc', f"Abonnement horaire {coordinator.data['contract_type']} {coordinator.data['contract_power']}kVA TTC", 'EUR/h')
        )

    if coordinator.data['tarif_actuel_ttc'] is not None:
        sensors.append(
            TarifEdfSensor(coordinator, 'tarif_actuel_ttc', f"Tarif actuel {coordinator.data['contract_type']} {coordinator.data['contract_power']}kVA TTC", 'EUR/kWh')
        )

    async_add_entities(sensors, False)

class TarifEdfSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tarif EDF sensor."""

    def __init__(self, coordinator, coordinator_key: str, name: str, unit_of_measurement: str = None) -> None:
        """Initialize the Tarif EDF sensor."""
        super().__init__(coordinator)
        contract_name = str.upper(self.coordinator.data['contract_type']) + " " + self.coordinator.data['contract_power'] + "kVA"

        self._coordinator_key = coordinator_key
        self._name = name
        self._attr_unique_id = f"tarif_edf_{self._name}"
        self._attr_name = name
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


class TarifEdfForecastSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Tempo forecast sensor with probability."""

    def __init__(self, coordinator, coordinator_key: str, name: str, day_number: int) -> None:
        """Initialize the Tempo forecast sensor."""
        super().__init__(coordinator)
        contract_name = str.upper(self.coordinator.data['contract_type']) + " " + self.coordinator.data['contract_power'] + "kVA"

        self._coordinator_key = coordinator_key
        self._day_number = day_number
        self._name = name
        self._attr_unique_id = f"tarif_edf_{self._name}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            name=f"Tarif EDF - {contract_name}",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={
                (DOMAIN, f"Tarif EDF - {contract_name}")
            },
            manufacturer="Tarif EDF",
            model=contract_name,
        )

    @property
    def native_value(self):
        """Return the predicted color for this day."""
        if self._coordinator_key not in self.coordinator.data or self.coordinator.data[self._coordinator_key] is None:
            return 'indéterminé'
        return self.coordinator.data[self._coordinator_key]

    @property
    def extra_state_attributes(self):
        """Return the state attributes including probability and date."""
        prob_key = f'tempo_prevision_j{self._day_number}_probabilite'
        date_key = f'tempo_prevision_j{self._day_number}_date'

        probability = self.coordinator.data.get(prob_key, 0)
        forecast_date = self.coordinator.data.get(date_key, '')

        return {
            'updated_at': self.coordinator.last_update_success_time,
            'probabilite': probability,
            'probabilite_pourcent': f"{probability}%",
            'date': forecast_date,
            'jour': f"J+{self._day_number}",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self._coordinator_key in self.coordinator.data
