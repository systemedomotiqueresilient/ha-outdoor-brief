"""Créneaux de pêche à pied (0.4) : calcul pur, sans Home Assistant.

Un créneau entoure une basse mer dont le coefficient atteint le seuil choisi : il commence
2 heures avant la basse mer et se termine 1 heure après, le moment où la mer remonte vite
(repère courant des guides de pêche à pied). Ce sont des repères horaires, pas un conseil
de sécurité : la mer, la météo et le terrain décident sur place.

Marées France ne donne le coefficient que sur les pleines mers : une basse mer prend le
plus fort coefficient des pleines mers qui l'entourent, ou à défaut celui du jour.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from .tides import HIGH, LOW, Tide

BEFORE = timedelta(hours=2)
AFTER = timedelta(hours=1)
HORIZON_DAYS = 7

# (lever, coucher) du soleil pour un jour, ou None si le soleil ne se lève/couche pas
SunFn = Callable[[date], tuple[datetime | None, datetime | None]]


@dataclass(frozen=True, slots=True)
class FishingWindow:
    start: datetime
    end: datetime
    low: Tide
    coefficient: int | None
    daylight: bool | None  # basse mer entre le lever et le coucher du soleil

    def as_dict(self) -> dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "low_tide": self.low.time.isoformat(),
            "height": self.low.height,
            "coefficient": self.coefficient,
            "daylight": self.daylight,
        }


def low_tide_coefficient(
    tides: list[Tide], index: int, coefficients: dict[date, list[int]]
) -> int | None:
    """Plus fort coefficient des pleines mers voisines de la basse mer tides[index]."""
    around = [
        tides[i].coefficient
        for i in (index - 1, index + 1)
        if 0 <= i < len(tides) and tides[i].kind == HIGH and tides[i].coefficient is not None
    ]
    if around:
        return max(around)
    day = coefficients.get(tides[index].time.date())
    return max(day) if day else None


def _daylight(low: Tide, sun: SunFn | None) -> bool | None:
    if sun is None:
        return None
    rise, set_ = sun(low.time.date())
    if rise is None or set_ is None:
        return None
    return rise <= low.time <= set_


def fishing_windows(
    tides: list[Tide],
    coefficients: dict[date, list[int]],
    now: datetime,
    threshold: int,
    sun: SunFn | None = None,
    days: int = HORIZON_DAYS,
) -> list[FishingWindow]:
    """Créneaux pas encore terminés, sur `days` jours, coefficient ≥ seuil, dans l'ordre."""
    limit = now + timedelta(days=days)
    windows = []
    for index, tide in enumerate(tides):
        if tide.kind != LOW or tide.time + AFTER <= now or tide.time > limit:
            continue
        coefficient = low_tide_coefficient(tides, index, coefficients)
        if coefficient is None or coefficient < threshold:
            continue
        windows.append(
            FishingWindow(
                start=tide.time - BEFORE,
                end=tide.time + AFTER,
                low=tide,
                coefficient=coefficient,
                daylight=_daylight(tide, sun),
            )
        )
    return windows


def fishing_summary(
    windows: list[FishingWindow], today: date, threshold: int, daylight_only: bool
) -> dict[str, Any]:
    """Bloc « fishing » du résumé du jour : créneaux d'aujourd'hui et prochain créneau."""
    usable = [w for w in windows if not daylight_only or w.daylight is not False]
    return {
        "threshold": threshold,
        "daylight_only": daylight_only,
        "today": [w.as_dict() for w in usable if w.low.time.date() == today],
        "next": usable[0].as_dict() if usable else None,
    }
