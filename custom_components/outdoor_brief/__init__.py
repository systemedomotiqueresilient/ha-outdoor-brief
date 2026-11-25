"""Outdoor Brief : le résumé du jour pour ce qui se passe dehors (marées, puis météo et lune)."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .alerts import Notifier
from .const import (
    CARD_FILE,
    DOMAIN,
    FRONTEND_URL,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_URL_PATH,
    RECOMPUTE_INTERVAL,
    SERVICE_SEND_SUMMARY,
    VERSION,
)
from .coordinator import OutdoorBriefCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.IMAGE, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type OutdoorBriefConfigEntry = ConfigEntry[OutdoorBriefCoordinator]


SEND_SCHEMA = vol.Schema({vol.Optional("config_entry_id"): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Action de test des notifications, puis carte Lovelace livrée avec l'intégration."""

    async def _send_summary(call: ServiceCall) -> ServiceResponse:
        wanted = call.data.get("config_entry_id")
        entries = [
            e
            for e in hass.config_entries.async_loaded_entries(DOMAIN)
            if wanted in (None, e.entry_id)
        ]
        if not entries:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="entry_not_loaded"
            )
        results = {}
        for entry in entries:
            notifier: Notifier = entry.runtime_data.notifier
            # Sans port précisé, un port regroupé secondaire est déjà inclus dans la
            # notification du port principal : on ne l'envoie pas une seconde fois.
            if wanted is None and notifier.is_secondary():
                continue
            outcome = await notifier.async_run(dt_util.now(), force=True)
            results[entry.title] = outcome["summary"]
        return {"sent": results}

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_SUMMARY,
        _send_summary,
        schema=SEND_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    if "frontend" not in hass.config.components or hass.http is None:
        _LOGGER.debug("Interface web absente : carte Outdoor Brief non enregistrée")
        return True
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_URL, str(Path(__file__).parent / "frontend"), False)]
    )
    # ?v= change à chaque version : le navigateur recharge la carte après une mise à jour.
    module = f"{FRONTEND_URL}/{CARD_FILE}?v={VERSION}"
    add_extra_js_url(hass, module)
    # Tableau de bord dédié : le rapport du jour en temps réel, cible du toucher sur la
    # notification. Ouvert à tous les utilisateurs (lecture seule).
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title="Outdoor Brief",
        sidebar_icon=PANEL_ICON,
        module_url=module,
        require_admin=False,
        config={"version": VERSION},
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: OutdoorBriefConfigEntry) -> bool:
    coordinator = OutdoorBriefCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    coordinator.notifier = Notifier(hass, entry, coordinator)

    # Le marnage et le douzième dépendent de l'heure : on les recalcule sans relire la source.
    @callback
    def _recompute(_now: datetime) -> None:
        coordinator.async_update_listeners()

    entry.async_on_unload(async_track_time_interval(hass, _recompute, RECOMPUTE_INTERVAL))
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await coordinator.notifier.async_start()
    entry.async_on_unload(coordinator.notifier.stop)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OutdoorBriefConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """1.1 = première version : rien à migrer, une version plus récente est refusée."""
    return entry.version <= 1
