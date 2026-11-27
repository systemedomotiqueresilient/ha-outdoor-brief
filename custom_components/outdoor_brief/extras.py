"""Blocs ajoutés au résumé du jour en 0.4 : pêche à pied, mer (Open-Meteo) et surcote."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_event_date

from .const import (
    CONF_FISHING_DAYLIGHT,
    CONF_FISHING_THRESHOLD,
    CONF_PRESSURE_ENTITY,
    DEFAULT_FISHING_DAYLIGHT,
    DEFAULT_FISHING_THRESHOLD,
)
from .fishing import FishingWindow, fishing_summary, fishing_windows
from .marine import SOURCE, pressure_from_state, surge

if TYPE_CHECKING:
    from .coordinator import OutdoorBriefCoordinator


def sun_times(hass: HomeAssistant):
    """Lever et coucher du soleil au lieu de Home Assistant (astral, fourni par HA)."""

    def _sun(day: date) -> tuple[datetime | None, datetime | None]:
        return (
            get_astral_event_date(hass, "sunrise", day),
            get_astral_event_date(hass, "sunset", day),
        )

    return _sun


def fishing_threshold(entry: ConfigEntry) -> int:
    return int(entry.options.get(CONF_FISHING_THRESHOLD, DEFAULT_FISHING_THRESHOLD))


def daylight_only(entry: ConfigEntry) -> bool:
    return bool(entry.options.get(CONF_FISHING_DAYLIGHT, DEFAULT_FISHING_DAYLIGHT))


def windows(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: OutdoorBriefCoordinator, now: datetime
) -> list[FishingWindow]:
    data = coordinator.data
    return fishing_windows(
        data.tides, data.coefficients, now, fishing_threshold(entry), sun_times(hass)
    )


def pressure(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: OutdoorBriefCoordinator
) -> tuple[float | None, str | None]:
    """(pression en hPa, source) : le capteur local d'abord, sinon Open-Meteo."""
    entity_id = entry.options.get(CONF_PRESSURE_ENTITY)
    if entity_id:
        return pressure_from_state(hass, entity_id), entity_id
    marine = coordinator.marine
    if marine is not None and marine.last_update_success and marine.data is not None:
        return marine.data.pressure, SOURCE
    return None, None


def has_pressure_source(entry: ConfigEntry, coordinator: OutdoorBriefCoordinator) -> bool:
    return bool(entry.options.get(CONF_PRESSURE_ENTITY)) or coordinator.marine is not None


def summary_extras(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: OutdoorBriefCoordinator, now: datetime
) -> dict[str, Any]:
    """Ajouts au contrat public (schema_version inchangé : ajouts seulement)."""
    marine = coordinator.marine
    marine_data = (
        marine.data.as_dict()
        if marine is not None and marine.last_update_success and marine.data is not None
        else None
    )
    value, source = pressure(hass, entry, coordinator)
    return {
        "fishing": fishing_summary(
            windows(hass, entry, coordinator, now),
            now.date(),
            fishing_threshold(entry),
            daylight_only(entry),
        ),
        "marine": marine_data,
        "surge": surge(value, source) if has_pressure_source(entry, coordinator) else None,
    }
