"""The Tarif EDF integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from datetime import timedelta

from .coordinator import TarifEdfDataUpdateCoordinator

from .const import (
    DOMAIN,
    PLATFORMS,
    DEFAULT_REFRESH_INTERVAL
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tarif EDF from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = TarifEdfDataUpdateCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    hass.data[DOMAIN][entry.entry_id]['coordinator'].update_interval = timedelta(days=entry.options.get("refresh_interval", DEFAULT_REFRESH_INTERVAL))

    return True
