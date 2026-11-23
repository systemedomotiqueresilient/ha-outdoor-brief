"""Notifications d'Outdoor Brief : résumé quotidien et grande marée à J-2.

- Téléphone : la cible « téléphone admin » de la convention SDR (entry.data), avec l'image
  du résumé en pièce jointe quand la cible est un service notify.mobile_app_*.
- Montre (facultative) : soit la notification complète, sans image, envoyée même sans
  téléphone ; soit un court avis, envoyé seulement si le téléphone a bien reçu la sienne.
- Les événements sont émis dans tous les cas, même si les notifications sont coupées.
- Anti-doublon persistant : un même envoi ne part qu'une fois, même après un redémarrage.
"""

from __future__ import annotations

from datetime import date, datetime, time
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .admin_phone import CONF_ADMIN_NOTIFY_TARGET, async_notify_admin, normalize_target
from .const import (
    CONF_NOTIFY_FREQUENCY,
    CONF_NOTIFY_TIME,
    CONF_SPRING_THRESHOLD,
    CONF_WATCH_MODE,
    CONF_WATCH_TARGET,
    DEFAULT_NOTIFY_TIME,
    DEFAULT_SPRING_THRESHOLD,
    DOMAIN,
    EVENT_DAILY_SUMMARY,
    EVENT_SPRING_TIDE,
    FALLBACK_FREQUENCY,
    FREQ_DAILY,
    FREQ_NEVER,
    FREQ_REMARKABLE,
    SPRING_TIDE_NOTICE_DAYS,
    WATCH_FULL,
    WATCH_NOTICE,
    WATCH_OFF,
)
from .coordinator import OutdoorBriefCoordinator
from .render import fmt_day, fmt_time, halves, texts
from .summary import build_summary

_LOGGER = logging.getLogger(__name__)

MESSAGES = {
    "fr": {
        "summary_title": "🌊 {port}",
        "spring_title": "🌕 Grande marée dans {n} jours",
        "spring_message": "{port} : {day}, coef {coef}{times}",
        "spring_times": " · PM {times}",
        "notice_summary": "Résumé {port} envoyé sur le téléphone",
        "notice_spring": "Grande marée {day} (coef {coef}) : détails sur le téléphone",
        "coef": "coef",
        "high": "PM",
        "low": "BM",
    },
    "en": {
        "summary_title": "🌊 {port}",
        "spring_title": "🌕 Spring tide in {n} days",
        "spring_message": "{port}: {day}, coef {coef}{times}",
        "spring_times": " · HW {times}",
        "notice_summary": "{port} brief sent to the phone",
        "notice_spring": "Spring tide {day} (coef {coef}): details on the phone",
        "coef": "coef",
        "high": "HW",
        "low": "LW",
    },
}


def _messages(language: str | None) -> dict[str, str]:
    return MESSAGES["fr" if str(language or "").lower().startswith("fr") else "en"]


def summary_message(summary: dict[str, Any], language: str | None) -> str:
    """Texte court, lisible seul (montre, notifications groupées) : « PM 03:07 · 15:30 · … »."""
    msg = _messages(language)
    table = halves(summary)
    parts = []
    for kind in ("high", "low"):
        times = [fmt_time(t["time"]) for t in table[kind] if t]
        if times:
            parts.append(f"{msg[kind]} {' · '.join(times)}")
    if coefs := summary.get("coefficients"):
        parts.append(f"{msg['coef']} {'-'.join(str(c) for c in coefs)}")
    return " | ".join(parts) or "—"


def is_remarkable(summary: dict[str, Any], today: date) -> bool:
    """Jour remarquable (0.3) : coefficient du jour au seuil, ou grande marée sous 2 jours."""
    threshold = summary.get("spring_tide_threshold", DEFAULT_SPRING_THRESHOLD)
    if max(summary.get("coefficients") or [0]) >= threshold:
        return True
    spring = summary.get("next_spring_tide")
    if spring:
        delta = (date.fromisoformat(spring["date"]) - today).days
        return 0 <= delta <= SPRING_TIDE_NOTICE_DAYS
    return False


class Notifier:
    """Planifie et envoie les notifications d'une entrée (un port)."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, coordinator: OutdoorBriefCoordinator
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self._store: Store[dict[str, str]] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self._sent: dict[str, str] = {}
        self._unsub: CALLBACK_TYPE | None = None

    # --- Réglages ---------------------------------------------------------------------

    @property
    def frequency(self) -> str:
        return self.entry.options.get(CONF_NOTIFY_FREQUENCY, FALLBACK_FREQUENCY)

    @property
    def phone(self) -> str | None:
        return normalize_target(self.entry.data.get(CONF_ADMIN_NOTIFY_TARGET))

    @property
    def watch(self) -> str | None:
        if self.entry.options.get(CONF_WATCH_MODE, WATCH_OFF) == WATCH_OFF:
            return None
        return normalize_target(self.entry.options.get(CONF_WATCH_TARGET))

    @property
    def watch_mode(self) -> str:
        return self.entry.options.get(CONF_WATCH_MODE, WATCH_OFF)

    def send_time(self) -> time:
        try:
            return time.fromisoformat(self.entry.options.get(CONF_NOTIFY_TIME, DEFAULT_NOTIFY_TIME))
        except ValueError:
            return time.fromisoformat(DEFAULT_NOTIFY_TIME)

    # --- Cycle de vie ------------------------------------------------------------------

    async def async_start(self) -> None:
        self._sent = await self._store.async_load() or {}
        at = self.send_time()
        self._unsub = async_track_time_change(
            self.hass, self._async_at_time, hour=at.hour, minute=at.minute, second=at.second
        )

    def stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    async def _async_at_time(self, now: datetime) -> None:
        await self.async_run(dt_util.as_local(now))

    # --- Logique -----------------------------------------------------------------------

    def summary(self, now: datetime) -> dict[str, Any]:
        threshold = int(self.entry.options.get(CONF_SPRING_THRESHOLD, DEFAULT_SPRING_THRESHOLD))
        return build_summary(self.coordinator.data, now, threshold, self.entry.title)

    async def async_run(self, now: datetime, force: bool = False) -> dict[str, bool]:
        """Passage quotidien : événements toujours, envois selon la fréquence.

        `force` (action send_summary) envoie le résumé sans tenir compte de la fréquence
        ni de l'anti-doublon, pour tester.
        """
        today = now.date()
        summary = self.summary(now)
        base = {"entry_id": self.entry.entry_id, "port": self.entry.title}
        self.hass.bus.async_fire(EVENT_DAILY_SUMMARY, {**base, **summary})

        result = {"summary": False, "spring_tide": False}
        send_summary = force or (
            self.frequency == FREQ_DAILY
            or (self.frequency == FREQ_REMARKABLE and is_remarkable(summary, today))
        )
        if send_summary and (force or self._sent.get("summary") != today.isoformat()):
            result["summary"] = await self._async_send_summary(summary)
            self._sent["summary"] = today.isoformat()

        spring = summary.get("next_spring_tide")
        if spring:
            day = date.fromisoformat(spring["date"])
            if (day - today).days == SPRING_TIDE_NOTICE_DAYS:
                self.hass.bus.async_fire(
                    EVENT_SPRING_TIDE,
                    {**base, **spring, "days_before": SPRING_TIDE_NOTICE_DAYS},
                )
                if self.frequency != FREQ_NEVER and self._sent.get("spring_tide") != spring["date"]:
                    result["spring_tide"] = await self._async_send_spring(spring, day)
                    self._sent["spring_tide"] = spring["date"]

        await self._store.async_save(self._sent)
        return result

    # --- Envois -------------------------------------------------------------------------

    def _image_url(self) -> str | None:
        entity_id = er.async_get(self.hass).async_get_entity_id(
            "image", DOMAIN, f"{self.entry.entry_id}_summary_image"
        )
        return f"/api/image_proxy/{entity_id}" if entity_id else None

    async def _async_deliver(
        self, kind: str, title: str, message: str, notice: str, image: bool
    ) -> bool:
        """Téléphone puis montre. Renvoie True si au moins un envoi a abouti."""
        tag = f"{DOMAIN}_{self.entry.entry_id}_{kind}"
        phone_ok = False
        if self.phone:
            data: dict[str, Any] = {"tag": tag, "group": DOMAIN}
            if image and (url := self._image_url()):
                data["image"] = url
            phone_ok = await async_notify_admin(self.hass, self.phone, title, message, data)
        watch_ok = False
        if self.watch:
            if self.watch_mode == WATCH_FULL:
                watch_ok = await async_notify_admin(
                    self.hass, self.watch, title, message, {"tag": tag}
                )
            elif self.watch_mode == WATCH_NOTICE and phone_ok:
                watch_ok = await async_notify_admin(
                    self.hass, self.watch, "Outdoor Brief", notice, {"tag": tag}
                )
        if not (self.phone or self.watch):
            _LOGGER.debug("Aucune cible de notification pour %s", self.entry.title)
        return phone_ok or watch_ok

    async def _async_send_summary(self, summary: dict[str, Any]) -> bool:
        language = self.hass.config.language
        msg = _messages(language)
        return await self._async_deliver(
            "summary",
            msg["summary_title"].format(port=self.entry.title),
            summary_message(summary, language),
            msg["notice_summary"].format(port=self.entry.title),
            image=True,
        )

    async def _async_send_spring(self, spring: dict[str, Any], day: date) -> bool:
        language = self.hass.config.language
        msg = _messages(language)
        lang = texts(language)
        highs = [
            fmt_time(t.time.isoformat())
            for t in self.coordinator.data.tides
            if t.kind == "high" and t.time.date() == day
        ]
        times = msg["spring_times"].format(times=" · ".join(highs)) if highs else ""
        label = fmt_day(day, lang)
        return await self._async_deliver(
            "spring_tide",
            msg["spring_title"].format(n=SPRING_TIDE_NOTICE_DAYS),
            msg["spring_message"].format(
                port=self.entry.title, day=label, coef=spring["coefficient"], times=times
            ),
            msg["notice_spring"].format(day=label, coef=spring["coefficient"]),
            image=False,
        )
