"""Lecture des réponses de Marées France et calculs de marée.

Ce module ne dépend pas de Home Assistant : il reçoit les réponses brutes des
actions marees_france.get_tides_data et marees_france.get_coefficients_data,
et un fuseau horaire.

Format observé (Marées France, novembre 2026) :
- marées : {"2026-11-21": [["tide.high", "14:02", "4.60", "64"],
                           ["tide.low", "20:10", "1.57", "---"], ...], ...}
  heure locale HH:MM sans fuseau, nombres en texte, "---" = absent,
  "tide.none" avec "--:--" pour compléter un jour à 3 marées ;
- coefficients : {"2026-11-21": ["57", "64"], ...}, un ou deux par jour.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, tzinfo
from typing import Any

HIGH = "high"
LOW = "low"

# Part du marnage parcourue pendant chaque douzième (règle des douzièmes)
TWELFTHS = (1, 2, 3, 3, 2, 1)


@dataclass(frozen=True, slots=True)
class Tide:
    """Une pleine mer ou une basse mer."""

    kind: str  # HIGH ou LOW
    time: datetime  # avec fuseau
    height: float | None  # mètres
    coefficient: int | None  # seulement sur les pleines mers

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.kind,
            "time": self.time.isoformat(),
            "height": self.height,
            "coefficient": self.coefficient,
        }


def _number(value: Any, cast: type) -> Any:
    """'4.60' → 4.6 ; '---', '', None ou illisible → None."""
    if value is None:
        return None
    try:
        return cast(float(str(value).strip().replace(",", ".")))
    except ValueError:
        return None


def _date(key: Any) -> date | None:
    try:
        return date.fromisoformat(str(key))
    except ValueError:
        return None


def unwrap(raw: Any) -> Mapping[str, Any]:
    """Renvoie le dictionnaire {date: …}, même s'il est emballé dans une clé de plus."""
    for _ in range(3):
        if not isinstance(raw, Mapping) or not raw:
            return {}
        if all(_date(key) for key in raw):
            return raw
        if len(raw) != 1:
            return {}
        raw = next(iter(raw.values()))
    return {}


def parse_tides(raw: Any, tz: tzinfo) -> list[Tide]:
    """Liste triée des marées, toutes dates confondues."""
    tides: list[Tide] = []
    for key, entries in unwrap(raw).items():
        day = _date(key)
        if day is None or not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, list | tuple) or len(entry) < 3:
                continue
            kind = str(entry[0]).removeprefix("tide.")
            if kind not in (HIGH, LOW):
                continue  # tide.none : jour à 3 marées
            try:
                clock = time.fromisoformat(str(entry[1]))
            except ValueError:
                continue
            coefficient = _number(entry[3], int) if len(entry) > 3 else None
            tides.append(
                Tide(
                    kind=kind,
                    time=datetime.combine(day, clock, tzinfo=tz),
                    height=_number(entry[2], float),
                    coefficient=coefficient if kind == HIGH else None,
                )
            )
    return sorted(tides, key=lambda tide: tide.time)


def parse_coefficients(raw: Any) -> dict[date, list[int]]:
    """{date: [coefficients du jour]} ; les jours sans coefficient lisible sont ignorés."""
    result: dict[date, list[int]] = {}
    for key, values in unwrap(raw).items():
        day = _date(key)
        if day is None:
            continue
        items = values if isinstance(values, list | tuple) else [values]
        coefficients = [c for c in (_number(v, int) for v in items) if c is not None]
        if coefficients:
            result[day] = coefficients
    return dict(sorted(result.items()))


def surrounding(tides: list[Tide], now: datetime) -> tuple[Tide | None, Tide | None]:
    """(dernière marée passée, prochaine marée) autour de `now`."""
    previous = next_tide = None
    for tide in tides:
        if tide.time <= now:
            previous = tide
        else:
            next_tide = tide
            break
    return previous, next_tide


def tidal_range(previous: Tide | None, next_tide: Tide | None) -> float | None:
    """Marnage de la demi-marée en cours, en mètres."""
    if previous is None or next_tide is None:
        return None
    if previous.height is None or next_tide.height is None:
        return None
    return round(abs(next_tide.height - previous.height), 2)


def twelfth(previous: Tide | None, next_tide: Tide | None, now: datetime) -> int | None:
    """Douzième en cours (1 à 6) sur la demi-marée entre deux extrêmes."""
    if previous is None or next_tide is None:
        return None
    duration = (next_tide.time - previous.time).total_seconds()
    if duration <= 0:
        return None
    elapsed = (now - previous.time).total_seconds()
    return max(1, min(6, int(elapsed / duration * 6) + 1))


def tides_of_day(tides: list[Tide], day: date) -> list[Tide]:
    return [tide for tide in tides if tide.time.date() == day]


def spring_tides(
    coefficients: dict[date, list[int]], today: date, threshold: int
) -> list[tuple[date, int]]:
    """Jours, à partir d'aujourd'hui, dont le plus fort coefficient atteint le seuil."""
    return [
        (day, max(values))
        for day, values in coefficients.items()
        if day >= today and max(values) >= threshold
    ]


def month_max(coefficients: dict[date, list[int]], today: date) -> tuple[date, int] | None:
    """Plus fort coefficient d'aujourd'hui à la fin du mois (premier jour en cas d'égalité)."""
    best: tuple[date, int] | None = None
    for day, values in coefficients.items():
        if day < today or (day.year, day.month) != (today.year, today.month):
            continue
        if best is None or max(values) > best[1]:
            best = (day, max(values))
    return best
