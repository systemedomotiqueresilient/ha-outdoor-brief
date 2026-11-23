"""Entité image : le résumé du jour en PNG, servi localement (pièce jointe des notifications)."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_IMAGE_THEME, DEFAULT_IMAGE_THEME
from .coordinator import OutdoorBriefCoordinator
from .render import render_summaries
from .sensor import device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SummaryImage(entry.runtime_data, entry)])


class SummaryImage(CoordinatorEntity[OutdoorBriefCoordinator], ImageEntity):
    """PNG redessiné seulement quand le contenu change.

    Pour le port principal d'un groupe (0.3.1), l'image empile les résumés de tous les
    ports regroupés : c'est elle qui part avec la notification commune.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "summary_image"
    _attr_content_type = "image/png"

    def __init__(self, coordinator: OutdoorBriefCoordinator, entry: ConfigEntry) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, coordinator.hass)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_summary_image"
        self._attr_device_info = device_info(entry)
        self._summary: list[dict] | None = None
        self._png: bytes | None = None
        self._refresh(write=False)

    def summary(self) -> list[dict]:
        notifier = getattr(self.coordinator, "notifier", None)
        if notifier is None:  # pendant la mise en place de l'entrée
            return []
        return notifier.summaries(dt_util.now())

    def _refresh(self, write: bool = True) -> None:
        summary = self.summary()
        if summary != self._summary:
            self._summary = summary
            self._png = None
            self._attr_image_last_updated = dt_util.utcnow()
            if write:
                self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._refresh()

    async def async_image(self) -> bytes | None:
        if self._png is None and not self._summary:
            self._refresh(write=False)
        if self._png is None and self._summary:
            theme = self._entry.options.get(CONF_IMAGE_THEME, DEFAULT_IMAGE_THEME)
            self._png = await self.hass.async_add_executor_job(
                render_summaries, self._summary, self.hass.config.language, theme
            )
        return self._png
