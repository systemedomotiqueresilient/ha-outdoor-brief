"""Notifications d'Outdoor Brief : résumé quotidien et grande marée à J-2.

- Téléphone : la cible « téléphone admin » de la convention SDR (entry.data), avec l'image
  du résumé en pièce jointe quand la cible est un service notify.mobile_app_*.
- Montre (facultative) : soit la notification complète, sans image, envoyée même sans
  téléphone ; soit un court avis, envoyé seulement si le téléphone a bien reçu la sienne.
- Les événements sont émis dans tous les cas, même si les notifications sont coupées.
- Anti-doublon persistant : un même envoi ne part qu'une fois, même après un redémarrage.
- Regroupement (0.3.1) : les ports « regroupés » partagent une seule notification, envoyée
  par le premier d'entre eux (le port principal) selon ses propres réglages.
- Une cible « entité notify » de l'app Companion est remplacée, pour l'envoi, par le service
  notify.mobile_app_* du même appareil : seul le service transmet image, tag et lien.
"""

from __future__ import annotations

from datetime import date, datetime, time
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util, slugify

from .admin_phone import CONF_ADMIN_NOTIFY_TARGET, async_notify_admin, normalize_target
from .const import (
    CONF_EXTRA_TARGETS,
    CONF_GROUPING,
    CONF_MESSAGE_STYLE,
    CONF_NOTIFY_FREQUENCY,
    CONF_NOTIFY_TIME,
    CONF_SPRING_THRESHOLD,
    CONF_TAP_URL,
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
    GROUPING_GROUPED,
    PANEL_URL_PATH,
    SPRING_TIDE_NOTICE_DAYS,
    STYLE_SHORT,
    WATCH_FULL,
    WATCH_NOTICE,
    WATCH_OFF,
)
from .coordinator import OutdoorBriefCoordinator
from .extras import summary_extras
from .render import fmt_day, fmt_time, halves, texts
from .summary import build_summary

_LOGGER = logging.getLogger(__name__)

MESSAGES = {
    "fr": {
        "summary_title": "🌊 {port}",
        "group_title": "🌊 Marées du jour",
        "short": "Coef {coefs} · prochaine {kind} {time}",
        "short_group": "Coef {coefs} · {n} ports, détails dans l'image",
        "notice_group": "Marées du jour envoyées sur le téléphone",
        "spring_title": "🌕 Grande marée dans {n} jours",
        "spring_message": "{port} : {day}, coef {coef}{times}",
        "spring_times": " · PM {times}",
        "notice_summary": "Résumé {port} envoyé sur le téléphone",
        "notice_spring": "Grande marée {day} (coef {coef}) : détails sur le téléphone",
        "coef": "coef",
        "fishing": "pêche",
        "high": "PM",
        "low": "BM",
    },
    "en": {
        "summary_title": "🌊 {port}",
        "group_title": "🌊 Today's tides",
        "short": "Coef {coefs} · next {kind} {time}",
        "short_group": "Coef {coefs} · {n} ports, details in the image",
        "notice_group": "Today's tides sent to the phone",
        "spring_title": "🌕 Spring tide in {n} days",
        "spring_message": "{port}: {day}, coef {coef}{times}",
        "spring_times": " · HW {times}",
        "notice_summary": "{port} brief sent to the phone",
        "notice_spring": "Spring tide {day} (coef {coef}): details on the phone",
        "coef": "coef",
        "fishing": "fishing",
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
    if today := (summary.get("fishing") or {}).get("today"):  # 0.4
        spans = [f"{fmt_time(w['start'])}-{fmt_time(w['end'])}" for w in today]
        parts.append(f"{msg['fishing']} {' · '.join(spans)}")
    return " | ".join(parts) or "—"


def rich_target(hass: HomeAssistant, target: str | None) -> str | None:
    """Service notify.mobile_app_* à utiliser à la place d'une entité notify de l'app.

    notify.send_message (entité) ne transmet ni image, ni tag, ni lien. Si la cible est
    l'entité notify d'un appareil Companion, on retrouve le service du même appareil.
    Sinon, la cible est rendue telle quelle.
    """
    if not target or hass.states.get(target) is None:
        return target
    entry = er.async_get(hass).async_get(target)
    if entry is None or entry.platform != "mobile_app" or not entry.device_id:
        return target
    device = dr.async_get(hass).async_get(entry.device_id)
    if device is None:
        return target
    for name in (device.name, device.name_by_user):
        if name and hass.services.has_service("notify", f"mobile_app_{slugify(name)}"):
            return f"notify.mobile_app_{slugify(name)}"
    return target


def group_members(hass: HomeAssistant) -> list[ConfigEntry]:
    """Entrées chargées en mode regroupé, de la plus ancienne à la plus récente."""
    return [
        entry
        for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        if entry.options.get(CONF_GROUPING) == GROUPING_GROUPED
        and getattr(entry.runtime_data, "notifier", None) is not None
    ]


def short_message(summaries: list[dict[str, Any]], language: str | None) -> str:
    """Texte court, quand l'image jointe porte le détail."""
    msg = _messages(language)
    first = summaries[0]
    coefs = "-".join(str(c) for c in first.get("coefficients") or []) or "—"
    if len(summaries) > 1:
        return msg["short_group"].format(coefs=coefs, n=len(summaries))
    nxt = first.get("next_tide")
    if not nxt:
        return f"{msg['coef'].capitalize()} {coefs}"
    return msg["short"].format(coefs=coefs, kind=msg[nxt["type"]], time=fmt_time(nxt["time"]))


def is_rich(hass: HomeAssistant, target: str | None) -> bool:
    """Cible capable de recevoir image, tag et lien : un service notify.mobile_app_*."""
    return bool(
        target
        and target.startswith("notify.mobile_app_")
        and hass.services.has_service("notify", target.removeprefix("notify."))
    )


def report_info(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Place du port dans le rapport : lu par le tableau de bord pour reproduire la notification."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    rank = next((i for i, e in enumerate(entries) if e.entry_id == entry.entry_id), len(entries))
    return {
        "entry_id": entry.entry_id,
        "rank": rank,
        "grouped": entry.options.get(CONF_GROUPING) == GROUPING_GROUPED,
    }


def group_message(summaries: list[dict[str, Any]], language: str | None) -> str:
    """Une ligne par port : « Lorient : PM 03:05 · 15:30 | BM … | coef 81-86 »."""
    return "\n".join(
        f"{summary.get('port')} : {summary_message(summary, language)}" for summary in summaries
    )


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

    # --- Regroupement ------------------------------------------------------------------

    def group(self) -> list[ConfigEntry]:
        """Membres du groupe si ce port est regroupé avec au moins un autre, sinon []."""
        if self.entry.options.get(CONF_GROUPING) != GROUPING_GROUPED:
            return []
        members = group_members(self.hass)
        return members if len(members) > 1 else []

    def is_secondary(self) -> bool:
        """Port regroupé qui n'envoie rien lui-même (le principal envoie pour lui)."""
        members = self.group()
        return bool(members) and members[0].entry_id != self.entry.entry_id

    def summaries(self, now: datetime) -> list[dict[str, Any]]:
        """Résumés à montrer : tout le groupe pour le port principal, sinon le sien."""
        members = self.group()
        if members and members[0].entry_id == self.entry.entry_id:
            return [member.runtime_data.notifier.summary(now) for member in members]
        return [self.summary(now)]

    # --- Logique -----------------------------------------------------------------------

    def summary(self, now: datetime) -> dict[str, Any]:
        threshold = int(self.entry.options.get(CONF_SPRING_THRESHOLD, DEFAULT_SPRING_THRESHOLD))
        return build_summary(
            self.coordinator.data,
            now,
            threshold,
            self.entry.title,
            summary_extras(self.hass, self.entry, self.coordinator, now),
        )

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

        # Grande marée à J-2 : l'événement part toujours, pour chaque port
        spring = summary.get("next_spring_tide")
        spring_soon = None
        if spring:
            day = date.fromisoformat(spring["date"])
            if (day - today).days == SPRING_TIDE_NOTICE_DAYS:
                spring_soon = (spring, day)
                self.hass.bus.async_fire(
                    EVENT_SPRING_TIDE,
                    {**base, **spring, "days_before": SPRING_TIDE_NOTICE_DAYS},
                )

        if self.is_secondary() and not force:
            return result  # le port principal du groupe envoie pour ce port

        summaries = self.summaries(now)
        remarkable = any(is_remarkable(item, today) for item in summaries)
        send_summary = force or (
            self.frequency == FREQ_DAILY or (self.frequency == FREQ_REMARKABLE and remarkable)
        )
        if send_summary and (force or self._sent.get("summary") != today.isoformat()):
            result["summary"] = await self._async_send_summary(summaries)
            self._sent["summary"] = today.isoformat()

        if self.frequency != FREQ_NEVER:
            springs = (
                self._group_springs(now)
                if len(summaries) > 1
                else ([(self.entry.title, *spring_soon)] if spring_soon else [])
            )
            if springs and self._sent.get("spring_tide") != springs[0][1]["date"]:
                result["spring_tide"] = await self._async_send_spring(springs)
                self._sent["spring_tide"] = springs[0][1]["date"]

        await self._store.async_save(self._sent)
        return result

    # --- Envois -------------------------------------------------------------------------

    def _image_url(self) -> str | None:
        entity_id = er.async_get(self.hass).async_get_entity_id(
            "image", DOMAIN, f"{self.entry.entry_id}_summary_image"
        )
        return f"/api/image_proxy/{entity_id}" if entity_id else None

    def _group_springs(self, now: datetime) -> list[tuple[str, dict[str, Any], date]]:
        """(port, grande marée, jour) des membres du groupe dont la grande marée est à J-2."""
        found = []
        for member in self.group():
            spring = member.runtime_data.notifier.summary(now).get("next_spring_tide")
            if spring:
                day = date.fromisoformat(spring["date"])
                if (day - now.date()).days == SPRING_TIDE_NOTICE_DAYS:
                    found.append((member.title, spring, day))
        return found

    def _tap_data(self) -> dict[str, Any]:
        """Lien ouvert au toucher : « url » pour iOS, « clickAction » pour Android.

        Sans réglage, le tableau de bord Outdoor Brief : le rapport regroupé, ou ce port seul.
        """
        url = str(self.entry.options.get(CONF_TAP_URL) or "").strip()
        if not url:
            url = f"/{PANEL_URL_PATH}"
            if not self.group():
                url += f"?entry={self.entry.entry_id}"
        return {"url": url, "clickAction": url}

    @property
    def extra_targets(self) -> list[str]:
        values = self.entry.options.get(CONF_EXTRA_TARGETS) or []
        return [t for t in (normalize_target(v) for v in values) if t]

    async def _async_send_to(
        self,
        target: str,
        title: str,
        message: str,
        short: str | None,
        image: bool,
        tag: str,
    ) -> bool:
        """Un envoi. Service mobile_app : image, tag, lien et texte court si l'image part.
        Autre canal (Telegram, ntfy, e-mail…) : titre et texte détaillé seulement."""
        target = rich_target(self.hass, target)
        if not is_rich(self.hass, target):
            return await async_notify_admin(self.hass, target, title, message)
        data: dict[str, Any] = {"tag": tag, "group": DOMAIN, **self._tap_data()}
        url = self._image_url() if image else None
        if url:
            data["image"] = url
            if short and self.entry.options.get(CONF_MESSAGE_STYLE, STYLE_SHORT) == STYLE_SHORT:
                message = short
        return await async_notify_admin(self.hass, target, title, message, data)

    async def _async_deliver(
        self,
        kind: str,
        title: str,
        message: str,
        notice: str,
        image: bool,
        short: str | None = None,
    ) -> bool:
        """Téléphone admin, destinataires supplémentaires, puis montre.

        Renvoie True si au moins un envoi a abouti.
        """
        tag = f"{DOMAIN}_{self.entry.entry_id}_{kind}"
        phone_ok = False
        if self.phone:
            phone_ok = await self._async_send_to(self.phone, title, message, short, image, tag)
        extra_ok = False
        for target in self.extra_targets:
            if target != self.phone:
                extra_ok |= await self._async_send_to(target, title, message, short, image, tag)
        watch_ok = False
        if self.watch:
            if self.watch_mode == WATCH_FULL:
                watch_ok = await self._async_send_to(self.watch, title, message, None, False, tag)
            elif self.watch_mode == WATCH_NOTICE and phone_ok:
                watch_ok = await async_notify_admin(
                    self.hass,
                    rich_target(self.hass, self.watch),
                    "Outdoor Brief",
                    notice,
                    {"tag": tag},
                )
        if not (self.phone or self.watch or self.extra_targets):
            _LOGGER.debug("Aucune cible de notification pour %s", self.entry.title)
        return phone_ok or extra_ok or watch_ok

    async def _async_send_summary(self, summaries: list[dict[str, Any]]) -> bool:
        language = self.hass.config.language
        msg = _messages(language)
        if len(summaries) > 1:
            return await self._async_deliver(
                "summary",
                msg["group_title"],
                group_message(summaries, language),
                msg["notice_group"],
                image=True,
                short=short_message(summaries, language),
            )
        return await self._async_deliver(
            "summary",
            msg["summary_title"].format(port=self.entry.title),
            summary_message(summaries[0], language),
            msg["notice_summary"].format(port=self.entry.title),
            image=True,
            short=short_message(summaries, language),
        )

    async def _async_send_spring(self, springs: list[tuple[str, dict[str, Any], date]]) -> bool:
        language = self.hass.config.language
        msg = _messages(language)
        lang = texts(language)
        lines = []
        for port, spring, day in springs:
            member = next((m for m in self.group() if m.title == port), self.entry)
            highs = [
                fmt_time(t.time.isoformat())
                for t in member.runtime_data.data.tides
                if t.kind == "high" and t.time.date() == day
            ]
            times = msg["spring_times"].format(times=" · ".join(highs)) if highs else ""
            lines.append(
                msg["spring_message"].format(
                    port=port, day=fmt_day(day, lang), coef=spring["coefficient"], times=times
                )
            )
        _, first, day = springs[0]
        label = fmt_day(day, lang)
        return await self._async_deliver(
            "spring_tide",
            msg["spring_title"].format(n=SPRING_TIDE_NOTICE_DAYS),
            "\n".join(lines),
            msg["notice_spring"].format(day=label, coef=first["coefficient"]),
            image=False,
        )
