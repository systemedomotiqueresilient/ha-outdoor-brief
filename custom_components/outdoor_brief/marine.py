"""Mer (0.4) : houle Open-Meteo (facultative) et indicateur de surcote.

- Open-Meteo n'est interrogé que si l'utilisateur l'a activé sur son écran dédié :
  désactivé, aucune requête n'est faite et aucune entité de houle n'existe.
- La surcote est une estimation de l'effet de baromètre inverse : environ 1 cm d'eau en
  plus par hectopascal sous 1013,25 hPa (et une décote au-dessus). Le vent, la houle et la
  forme de la côte ne sont pas pris en compte. La pression vient d'abord d'un capteur
  local choisi par l'utilisateur, sinon d'Open-Meteo quand il est activé.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import timedelta
import logging
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, UnitOfPressure
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.unit_conversion import PressureConverter

from .const import CONF_MARINE_LOCATION, DOMAIN

_LOGGER = logging.getLogger(__name__)

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_INTERVAL = timedelta(hours=1)
TIMEOUT = 20

MARINE_VARIABLES = {
    "wave_height": "wave_height",
    "wave_period": "wave_period",
    "wave_direction": "wave_direction",
    "swell_wave_height": "swell_height",
    "swell_wave_period": "swell_period",
    "swell_wave_direction": "swell_direction",
    "sea_surface_temperature": "sea_temperature",
}

REFERENCE_PRESSURE = 1013.25  # hPa
SURGE_CM_PER_HPA = 1.0
SOURCE = "Open-Meteo"


@dataclass(slots=True)
class MarineData:
    """Conditions actuelles au point choisi (valeurs None si le modèle n'en donne pas)."""

    time: str | None = None
    wave_height: float | None = None
    wave_period: float | None = None
    wave_direction: float | None = None
    swell_height: float | None = None
    swell_period: float | None = None
    swell_direction: float | None = None
    sea_temperature: float | None = None
    pressure: float | None = None  # hPa, niveau de la mer

    def as_dict(self) -> dict[str, Any]:
        return {**asdict(self), "source": SOURCE}


class MarineError(Exception):
    """Erreur traduite : `key` est une clé d'erreur du config flow et des exceptions."""

    def __init__(self, key: str, detail: str = "") -> None:
        super().__init__(detail or key)
        self.key = key
        self.detail = detail


def _float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


async def _get(session: aiohttp.ClientSession, url: str, params: dict[str, Any]) -> dict:
    try:
        async with asyncio.timeout(TIMEOUT):
            response = await session.get(url, params=params)
            payload = await response.json(content_type=None)
    except (TimeoutError, aiohttp.ClientError, ValueError) as err:
        raise MarineError("marine_unreachable", str(err)) from err
    if response.status != 200 or not isinstance(payload, dict):
        reason = payload.get("reason") if isinstance(payload, dict) else None
        raise MarineError("marine_unreachable", str(reason or f"HTTP {response.status}"))
    return payload


async def async_fetch_marine(hass: HomeAssistant, latitude: float, longitude: float) -> MarineData:
    """Deux requêtes : houle et température de l'eau, puis pression au niveau de la mer."""
    session = async_get_clientsession(hass)
    where = {"latitude": round(latitude, 4), "longitude": round(longitude, 4)}
    marine = await _get(
        session,
        MARINE_URL,
        {**where, "current": ",".join(MARINE_VARIABLES), "cell_selection": "sea"},
    )
    current = marine.get("current") or {}
    data = MarineData(time=current.get("time"))
    for api_name, field in MARINE_VARIABLES.items():
        setattr(data, field, _float(current.get(api_name)))
    if data.wave_height is None and data.swell_height is None:
        # Point dans les terres ou hors des modèles de vagues
        raise MarineError("marine_no_data")
    forecast = await _get(session, FORECAST_URL, {**where, "current": "pressure_msl"})
    data.pressure = _float((forecast.get("current") or {}).get("pressure_msl"))
    return data


class MarineCoordinator(DataUpdateCoordinator[MarineData]):
    """Relit Open-Meteo toutes les heures, seulement si l'utilisateur l'a activé."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_marine",
            update_interval=MARINE_INTERVAL,
        )
        location = entry.options.get(CONF_MARINE_LOCATION) or {}
        self.latitude = float(location.get("latitude", hass.config.latitude))
        self.longitude = float(location.get("longitude", hass.config.longitude))

    async def _async_update_data(self) -> MarineData:
        try:
            return await async_fetch_marine(self.hass, self.latitude, self.longitude)
        except MarineError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key=err.key,
                translation_placeholders={"error": err.detail},
            ) from err


def pressure_from_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Pression en hPa lue sur un capteur (unité quelconque) ou une entité météo."""
    if not entity_id or (state := hass.states.get(entity_id)) is None:
        return None
    if entity_id.startswith("weather."):
        value = _float(state.attributes.get("pressure"))
        unit = state.attributes.get("pressure_unit") or UnitOfPressure.HPA
    else:
        value = _float(state.state)
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) or UnitOfPressure.HPA
    if value is None:
        return None
    try:
        return round(PressureConverter.convert(value, unit, UnitOfPressure.HPA), 1)
    except Exception:  # noqa: BLE001 - unité inconnue : on ne devine pas
        return None


def surge(pressure: float | None, source: str | None) -> dict[str, Any] | None:
    """Surcote (positive) ou décote (négative) estimée par l'effet de baromètre inverse."""
    if pressure is None:
        return None
    return {
        "height_cm": round((REFERENCE_PRESSURE - pressure) * SURGE_CM_PER_HPA),
        "pressure_hpa": round(pressure, 1),
        "reference_hpa": REFERENCE_PRESSURE,
        "source": source,
    }
