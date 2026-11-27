"""Résumé du jour (contrat public) : commun au capteur, à l'image et aux notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .const import SCHEMA_VERSION
from .coordinator import BriefData
from .tides import month_max, spring_tides, surrounding, tidal_range, tides_of_day, twelfth


def build_summary(
    data: BriefData,
    now: datetime,
    threshold: int,
    port: str,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attributs du « Résumé du jour » : ajouts possibles, retraits en version majeure."""
    today = now.date()
    previous, next_tide = surrounding(data.tides, now)
    upcoming = spring_tides(data.coefficients, today, threshold)
    best = month_max(data.coefficients, today)
    return {
        "schema_version": SCHEMA_VERSION,
        "port": port,
        "date": today.isoformat(),
        "tides": [tide.as_dict() for tide in tides_of_day(data.tides, today)],
        "coefficients": data.coefficients.get(today, []),
        "tidal_range": tidal_range(previous, next_tide),
        "tide_twelfth": twelfth(previous, next_tide, now),
        "next_tide": next_tide.as_dict() if next_tide else None,
        "next_spring_tide": (
            {"date": upcoming[0][0].isoformat(), "coefficient": upcoming[0][1]}
            if upcoming
            else None
        ),
        "month_max": {"date": best[0].isoformat(), "coefficient": best[1]} if best else None,
        "spring_tide_threshold": threshold,
        "source": "SHOM via Marées France",
        # 0.4 : pêche à pied, mer (Open-Meteo, facultatif) et surcote estimée
        "fishing": None,
        "marine": None,
        "surge": None,
        **(extras or {}),
    }
