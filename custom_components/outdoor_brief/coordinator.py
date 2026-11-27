"""Lecture des données de Marées France, par ses actions à réponse (aucun appel Internet ici)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .const import (
    CONF_PORT_DEVICE,
    DOMAIN,
    MAREES_DOMAIN,
    REFRESH_INTERVAL,
    SERVICE_COEFFICIENTS,
    SERVICE_TIDES,
)
from .tides import Tide, parse_coefficients, parse_tides

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class BriefData:
    """Dernière lecture réussie de Marées France pour le port choisi."""

    tides: list[Tide] = field(default_factory=list)
    coefficients: dict[date, list[int]] = field(default_factory=dict)
    fetched_at: datetime | None = None


class OutdoorBriefCoordinator(DataUpdateCoordinator[BriefData]):
    """Relit les marées (8 jours) et les coefficients (1 an) toutes les heures."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=REFRESH_INTERVAL,
        )
        self.device_id: str = entry.data[CONF_PORT_DEVICE]
        self.notifier: Any = None  # alerts.Notifier, posé par async_setup_entry
        self.marine: Any = None  # marine.MarineCoordinator, seulement si Open-Meteo est activé

    async def _call(self, service: str) -> Any:
        if not self.hass.services.has_service(MAREES_DOMAIN, service):
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="marees_france_unavailable",
            )
        try:
            return await self.hass.services.async_call(
                MAREES_DOMAIN,
                service,
                {"device_id": self.device_id},  # sans lui, l'action répond pour un autre port
                blocking=True,
                return_response=True,
            )
        except (HomeAssistantError, vol.Invalid) as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="marees_france_error",
                translation_placeholders={"service": service, "error": str(err)},
            ) from err

    async def _async_update_data(self) -> BriefData:
        tz = dt_util.get_default_time_zone()
        tides = parse_tides(await self._call(SERVICE_TIDES), tz)
        coefficients = parse_coefficients(await self._call(SERVICE_COEFFICIENTS))
        if not tides:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="no_tide_data")
        return BriefData(tides=tides, coefficients=coefficients, fetched_at=dt_util.utcnow())
