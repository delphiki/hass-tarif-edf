"""Binary sensor platform for the Tarif EDF integration."""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.components.binary_sensor import BinarySensorEntity

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import TarifEdfDataUpdateCoordinator

from .const import (
    DOMAIN,
    CONTRACT_TYPE_HPHC,
    CONTRACT_TYPE_TEMPO,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tarif EDF binary sensors from a config entry."""
    coordinator: TarifEdfDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]["coordinator"]

    contract_type = coordinator.data["contract_type"]

    sensors = []

    # Off-peak binary sensor (for HPHC and Tempo contracts)
    if contract_type in [CONTRACT_TYPE_HPHC, CONTRACT_TYPE_TEMPO]:
        sensors.append(TarifEdfOffPeakBinarySensor(coordinator))

    async_add_entities(sensors, False)


class TarifEdfOffPeakBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor indicating if currently in off-peak hours."""

    _attr_device_class = None

    def __init__(self, coordinator: TarifEdfDataUpdateCoordinator) -> None:
        """Initialize the off-peak binary sensor."""
        super().__init__(coordinator)
        contract_type = self.coordinator.data["contract_type"]
        contract_power = self.coordinator.data["contract_power"]
        contract_name = f"{contract_type.upper()} {contract_power}kVA"

        self._attr_unique_id = f"tarif_edf_{contract_type}_{contract_power}_is_off_peak"
        self._attr_name = f"Heures creuses {contract_type.upper()} {contract_power}kVA"
        self._attr_device_info = DeviceInfo(
            name=f"Tarif EDF - {contract_name}",
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f"tarif_edf_{contract_type}_{contract_power}")},
            manufacturer="Tarif EDF",
            model=contract_name,
        )

    @property
    def is_on(self) -> bool:
        """Return True if currently in off-peak hours."""
        return self.coordinator.data.get("is_off_peak", False)

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            "updated_at": self.coordinator.last_update_success_time,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
