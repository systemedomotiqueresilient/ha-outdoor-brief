"""0.4 : pêche à pied, Open-Meteo (facultatif) et surcote."""

from __future__ import annotations

from datetime import date, datetime
import json
from zoneinfo import ZoneInfo

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.outdoor_brief.const import (
    CONF_PORT_DEVICE,
    CONF_PROFILE,
    CONF_SPRING_THRESHOLD,
    DOMAIN,
)
from custom_components.outdoor_brief.alerts import summary_message
from custom_components.outdoor_brief.fishing import fishing_summary, fishing_windows
from custom_components.outdoor_brief.marine import (
    FORECAST_URL,
    MARINE_URL,
    pressure_from_state,
    surge,
)
from custom_components.outdoor_brief.render import render_summaries, sea_line, texts
from custom_components.outdoor_brief.tides import parse_coefficients, parse_tides

from .conftest import NOW, FakeMarees, load

TZ = ZoneInfo("Europe/Paris")
# Point générique au large de la Bretagne (pas une adresse)
SEA = {"latitude": 47.0, "longitude": -3.0}

MARINE = {
    "current": {
        "time": "2026-11-21T18:45",
        "wave_height": 1.42,
        "wave_period": 8.3,
        "wave_direction": 268.0,
        "swell_wave_height": 1.18,
        "swell_wave_period": 11.2,
        "swell_wave_direction": 275.0,
        "sea_surface_temperature": 13.4,
    }
}
FORECAST = {"current": {"time": "2026-11-21T18:45", "pressure_msl": 1005.2}}


def _entity(hass: HomeAssistant, entry, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{key}")


async def _setup(hass: HomeAssistant, marees: FakeMarees, freezer, **options) -> MockConfigEntry:
    freezer.move_to(NOW)
    hass.config.latitude, hass.config.longitude = SEA["latitude"], SEA["longitude"]
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        title="Port-Louis (Locmalo)",
        unique_id=marees.device.id,
        data={CONF_PROFILE: "coastal", CONF_PORT_DEVICE: marees.device.id},
        options={CONF_SPRING_THRESHOLD: 100, **options},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


# --- Pêche à pied ----------------------------------------------------------------------


def test_fishing_windows_on_real_data() -> None:
    tides = parse_tides(load("tides.json"), TZ)
    coefficients = parse_coefficients(load("coefficients.json"))
    now = datetime(2026, 11, 21, 19, 52, tzinfo=TZ)
    found = fishing_windows(tides, coefficients, now, 70)
    # Créneau en cours (BM 20:10, coef 70) : de 2 h avant à 1 h après la basse mer
    first = found[0]
    assert first.low.time == datetime(2026, 11, 21, 20, 10, tzinfo=TZ)
    assert (first.start.hour, first.start.minute) == (18, 10)
    assert (first.end.hour, first.end.minute) == (21, 10)
    assert first.coefficient == 70
    assert [w.coefficient for w in found[:4]] == [70, 76, 81, 86]
    # Seuil plus haut : moins de créneaux, coefficients toujours au seuil
    strong = fishing_windows(tides, coefficients, now, 95)
    assert strong and all(w.coefficient >= 95 for w in strong)
    # Jour / nuit selon le soleil fourni
    sun = lambda day: (  # noqa: E731
        datetime.combine(day, datetime.min.time(), TZ).replace(hour=8),
        datetime.combine(day, datetime.min.time(), TZ).replace(hour=17, minute=30),
    )
    found = fishing_windows(tides, coefficients, now, 70, sun)
    assert found[0].daylight is False  # BM 20:10
    block = fishing_summary(found, date(2026, 11, 21), 70, daylight_only=True)
    assert block["today"] == []  # le seul créneau du jour est de nuit
    assert block["next"]["low_tide"].startswith("2026-11-22T08:32")
    assert fishing_summary(found, date(2026, 11, 21), 70, False)["today"][0]["coefficient"] == 70


async def test_fishing_sensor_and_summary(hass: HomeAssistant, marees, freezer) -> None:
    entry = await _setup(hass, marees, freezer, fishing_daylight_only=False)
    state = hass.states.get(_entity(hass, entry, "next_fishing_window"))
    assert state.state == "2026-11-21T17:10:00+00:00"  # 18:10 à Paris
    assert state.attributes["coefficient"] == 70
    assert state.attributes["threshold"] == 70
    assert len(state.attributes["upcoming"]) == 5
    summary = hass.states.get(_entity(hass, entry, "daily_summary")).attributes
    assert summary["fishing"]["today"][0]["low_tide"].startswith("2026-11-21T20:10")
    # Sans Open-Meteo ni capteur de pression : pas de mer, pas de surcote, pas d'entité
    assert summary["marine"] is None and summary["surge"] is None
    assert _entity(hass, entry, "storm_surge") is None
    assert _entity(hass, entry, "wave_height") is None


async def test_daylight_only_by_default(hass: HomeAssistant, marees, freezer) -> None:
    entry = await _setup(hass, marees, freezer)
    state = hass.states.get(_entity(hass, entry, "next_fishing_window"))
    assert state.attributes["daylight"] is True
    assert state.attributes["low_tide"] > "2026-11-22"


# --- Surcote ---------------------------------------------------------------------------


def test_surge_and_pressure_units(hass: HomeAssistant) -> None:
    assert surge(1005.2, "x")["height_cm"] == 8
    assert surge(1023.25, "x")["height_cm"] == -10  # décote
    assert surge(None, "x") is None
    hass.states.async_set("sensor.p", "29.68", {"unit_of_measurement": "inHg"})
    assert pressure_from_state(hass, "sensor.p") == 1005.1
    hass.states.async_set("weather.home", "rainy", {"pressure": 1009, "pressure_unit": "hPa"})
    assert pressure_from_state(hass, "weather.home") == 1009
    hass.states.async_set("sensor.bad", "unknown", {"unit_of_measurement": "hPa"})
    assert pressure_from_state(hass, "sensor.bad") is None
    assert pressure_from_state(hass, "sensor.absent") is None


async def test_surge_from_local_sensor(hass: HomeAssistant, marees, freezer) -> None:
    hass.states.async_set("sensor.pression", "1003", {"unit_of_measurement": "hPa"})
    entry = await _setup(hass, marees, freezer, pressure_entity="sensor.pression")
    surge_id = _entity(hass, entry, "storm_surge")
    assert hass.states.get(surge_id).state == "10"
    assert hass.states.get(surge_id).attributes["source"] == "sensor.pression"
    # Le capteur change : la surcote suit sans attendre le recalcul des 5 minutes
    hass.states.async_set("sensor.pression", "1020", {"unit_of_measurement": "hPa"})
    await hass.async_block_till_done()
    assert hass.states.get(surge_id).state == "-7"
    summary = hass.states.get(_entity(hass, entry, "daily_summary")).attributes
    assert summary["surge"]["height_cm"] == -7
    # Capteur indisponible : seule la surcote devient indisponible
    hass.states.async_set("sensor.pression", "unavailable")
    await hass.async_block_till_done()
    assert hass.states.get(surge_id).state == "unavailable"
    assert hass.states.get(_entity(hass, entry, "tidal_range")).state != "unavailable"


# --- Open-Meteo --------------------------------------------------------------------------


async def test_marine_disabled_makes_no_request(
    hass: HomeAssistant, marees, freezer, aioclient_mock
) -> None:
    await _setup(hass, marees, freezer)
    assert aioclient_mock.call_count == 0


async def test_marine_enabled(hass: HomeAssistant, marees, freezer, aioclient_mock) -> None:
    aioclient_mock.get(MARINE_URL, json=MARINE)
    aioclient_mock.get(FORECAST_URL, json=FORECAST)
    entry = await _setup(hass, marees, freezer, marine_enabled=True, marine_location=SEA)
    assert hass.states.get(_entity(hass, entry, "wave_height")).state == "1.42"
    assert hass.states.get(_entity(hass, entry, "swell_period")).state == "11.2"
    assert hass.states.get(_entity(hass, entry, "sea_temperature")).state == "13.4"
    # Surcote avec la pression d'Open-Meteo, faute de capteur local
    surge_state = hass.states.get(_entity(hass, entry, "storm_surge"))
    assert surge_state.state == "8"
    assert surge_state.attributes["source"] == "Open-Meteo"
    summary = hass.states.get(_entity(hass, entry, "daily_summary")).attributes
    assert summary["marine"]["swell_height"] == 1.18
    assert summary["marine"]["source"] == "Open-Meteo"
    # Le point demandé est celui choisi, en mer
    url = str(aioclient_mock.mock_calls[0][1])
    assert "latitude=47.0" in url and "cell_selection=sea" in url


async def test_marine_failure_keeps_tides(
    hass: HomeAssistant, marees, freezer, aioclient_mock
) -> None:
    aioclient_mock.get(MARINE_URL, status=500, json={"error": True, "reason": "boom"})
    entry = await _setup(hass, marees, freezer, marine_enabled=True, marine_location=SEA)
    assert entry.state is config_entries.ConfigEntryState.LOADED
    assert hass.states.get(_entity(hass, entry, "wave_height")).state == "unavailable"
    assert hass.states.get(_entity(hass, entry, "storm_surge")).state == "unavailable"
    assert hass.states.get(_entity(hass, entry, "tidal_range")).state == "3.03"
    summary = hass.states.get(_entity(hass, entry, "daily_summary")).attributes
    assert summary["marine"] is None and summary["surge"] is None


async def test_marine_options_step(hass: HomeAssistant, marees, freezer, aioclient_mock) -> None:
    entry = await _setup(hass, marees, freezer)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "marine"}
    )
    assert result["step_id"] == "marine"
    # Point dans les terres : pas de données de vagues
    aioclient_mock.get(MARINE_URL, json={"current": {"time": "x", "wave_height": None}})
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"marine_enabled": True, "marine_location": SEA}
    )
    assert result["errors"] == {"base": "marine_no_data"}
    aioclient_mock.clear_requests()
    aioclient_mock.get(MARINE_URL, exc=TimeoutError)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"marine_enabled": True, "marine_location": SEA}
    )
    assert result["errors"] == {"base": "marine_unreachable"}
    aioclient_mock.clear_requests()
    aioclient_mock.get(MARINE_URL, json=MARINE)
    aioclient_mock.get(FORECAST_URL, json=FORECAST)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"marine_enabled": True, "marine_location": SEA}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["marine_enabled"] is True
    assert entry.options[CONF_SPRING_THRESHOLD] == 100  # le reste est conservé
    assert hass.states.get(_entity(hass, entry, "wave_height")).state == "1.42"


# --- Affichage -----------------------------------------------------------------------------


def test_sea_line_and_image() -> None:
    summary = json.loads(json.dumps(_summary()))
    fr, en = texts("fr"), texts("en")
    assert sea_line(summary, fr) == (
        "Mer : vagues 1,4 m · houle O 1,2 m 11 s · eau 13,4 °C · surcote estimée +8 cm"
    )
    assert sea_line(summary, en).startswith("Sea: waves 1.4 m · swell W 1.2 m 11 s")
    summary["surge"]["height_cm"] = -6
    assert sea_line(summary, fr).endswith("décote estimée -6 cm")
    assert sea_line({"marine": None, "surge": None}, fr) is None
    assert summary_message(summary, "fr").endswith("| pêche 08:32-11:32")
    png = render_summaries([summary, summary], "fr", "dark")
    assert png.startswith(b"\x89PNG")


def _summary() -> dict:
    return {
        "schema_version": 1,
        "port": "Port-Louis",
        "date": "2026-11-21",
        "tides": [],
        "coefficients": [57, 64],
        "next_tide": None,
        "next_spring_tide": None,
        "month_max": None,
        "spring_tide_threshold": 100,
        "fishing": {
            "threshold": 70,
            "daylight_only": True,
            "today": [
                {
                    "start": "2026-11-21T08:32:00+01:00",
                    "end": "2026-11-21T11:32:00+01:00",
                    "low_tide": "2026-11-21T10:32:00+01:00",
                    "height": 1.2,
                    "coefficient": 76,
                    "daylight": True,
                }
            ],
            "next": None,
        },
        "marine": {
            "wave_height": 1.42,
            "wave_period": 8.3,
            "wave_direction": 268.0,
            "swell_height": 1.18,
            "swell_period": 11.2,
            "swell_direction": 275.0,
            "sea_temperature": 13.4,
            "pressure": 1005.2,
            "source": "Open-Meteo",
        },
        "surge": {"height_cm": 8, "pressure_hpa": 1005.2, "source": "Open-Meteo"},
    }
