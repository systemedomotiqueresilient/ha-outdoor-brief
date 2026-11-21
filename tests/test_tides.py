"""Lecture des réponses Marées France et calculs, sur le relevé réel du 21/11/2026."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from custom_components.outdoor_brief.tides import (
    HIGH,
    LOW,
    month_max,
    parse_coefficients,
    parse_tides,
    spring_tides,
    surrounding,
    tidal_range,
    tides_of_day,
    twelfth,
    unwrap,
)

from .conftest import load

PARIS = ZoneInfo("Europe/Paris")
NOW = datetime(2026, 11, 21, 19, 52, tzinfo=PARIS)


def test_parse_tides_formats() -> None:
    tides = parse_tides(load("tides.json"), PARIS)
    # 8 jours, 4 marées par jour sauf le 27 (tide.none ignorée)
    assert len(tides) == 31
    day = tides_of_day(tides, date(2026, 11, 21))
    assert [(t.kind, t.time.strftime("%H:%M"), t.height, t.coefficient) for t in day] == [
        (HIGH, "01:42", 4.37, 57),
        (LOW, "07:47", 1.82, None),  # "---" → None
        (HIGH, "14:02", 4.60, 64),
        (LOW, "20:10", 1.57, None),
    ]
    assert day[2].time.utcoffset().total_seconds() == 3600  # heure locale, pas UTC
    assert len(tides_of_day(tides, date(2026, 11, 27))) == 3


def test_parse_is_tolerant() -> None:
    raw = {"2026-11-21": [["tide.high", "14:02", "4,60", "64"], ["tide.low", "xx", "1", "-"],
                          ["tide.flood", "10:00", "1", "1"], "bad", ["tide.low"]],
           "pas une date": []}
    assert unwrap(raw) == {}  # clé non datée : réponse non reconnue
    tides = parse_tides({"port": {"2026-11-21": raw["2026-11-21"]}}, PARIS)  # emballée
    assert [(t.kind, t.height) for t in tides] == [(HIGH, 4.6)]
    assert parse_tides(None, PARIS) == [] and parse_tides([], PARIS) == []
    assert parse_coefficients({"2026-11-21": "64", "2026-11-22": ["---"]}) == {
        date(2026, 11, 21): [64]
    }


def test_range_and_twelfth() -> None:
    tides = parse_tides(load("tides.json"), PARIS)
    previous, next_tide = surrounding(tides, NOW)
    assert (previous.kind, previous.time.strftime("%H:%M")) == (HIGH, "14:02")
    assert (next_tide.kind, next_tide.time.strftime("%H:%M")) == (LOW, "20:10")
    assert tidal_range(previous, next_tide) == 3.03
    assert twelfth(previous, next_tide, NOW) == 6  # 5 h 50 sur 6 h 08
    assert twelfth(previous, next_tide, datetime(2026, 11, 21, 14, 2, tzinfo=PARIS)) == 1
    assert twelfth(previous, next_tide, datetime(2026, 11, 21, 17, 10, tzinfo=PARIS)) == 4
    # Hors des données disponibles
    before = surrounding(tides, datetime(2026, 11, 1, tzinfo=PARIS))
    assert before[0] is None and tidal_range(*before) is None and twelfth(*before, NOW) is None


def test_spring_tides_and_month_max() -> None:
    coefficients = parse_coefficients(load("coefficients.json"))
    today = date(2026, 11, 21)
    # Même résultat que l'entité de Marées France : 23 janvier 2027, coefficient 104
    assert spring_tides(coefficients, today, 100)[0] == (date(2027, 1, 23), 104)
    # Seuil abaissé : les 96-97 de la fin novembre comptent
    assert spring_tides(coefficients, today, 95)[0] == (date(2026, 11, 25), 97)
    assert month_max(coefficients, today) == (date(2026, 11, 25), 97)
    # Décembre culmine à 99 : aucune grande marée au seuil 100
    december = month_max(coefficients, date(2026, 12, 1))
    assert december == (date(2026, 12, 25), 99)
    assert month_max({}, today) is None
