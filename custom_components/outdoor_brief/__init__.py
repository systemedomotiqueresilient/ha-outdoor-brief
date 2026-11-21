"""Outdoor Brief : le résumé du jour pour ce qui se passe dehors (marées, puis météo et lune)."""

from __future__ import annotations

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, RECOMPUTE_INTERVAL
from .coordinator import OutdoorBriefCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type OutdoorBriefConfigEntry = ConfigEntry[OutdoorBriefCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: OutdoorBriefConfigEntry) -> bool:
    coordinator = OutdoorBriefCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # Le marnage et le douzième dépendent de l'heure : on les recalcule sans relire la source.
    @callback
    def _recompute(_now: datetime) -> None:
        coordinator.async_update_listeners()

    entry.async_on_unload(async_track_time_interval(hass, _recompute, RECOMPUTE_INTERVAL))
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OutdoorBriefConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """1.1 = première version : rien à migrer, une version plus récente est refusée."""
    return entry.version <= 1
