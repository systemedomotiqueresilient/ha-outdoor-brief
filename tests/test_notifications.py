"""Notifications : résumé quotidien, jours remarquables, grande marée J-2, montre, image."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from PIL import Image
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.outdoor_brief.admin_phone import CONF_ADMIN_NOTIFY_TARGET
from custom_components.outdoor_brief.alerts import is_remarkable, summary_message
from custom_components.outdoor_brief.const import (
    CONF_PORT_DEVICE,
    CONF_PROFILE,
    CONF_SPRING_THRESHOLD,
    DOMAIN,
    EVENT_DAILY_SUMMARY,
    EVENT_SPRING_TIDE,
)
from custom_components.outdoor_brief.render import render_png

from .conftest import FakeMarees

PHONE = "notify.mobile_app_iphone"
WATCH = "notify.mobile_app_galaxy_watch"
PARIS_0700_21 = "2026-11-21T06:00:01+00:00"  # 07:00 à Paris le 21/11
PARIS_0700_23 = "2026-11-23T06:00:01+00:00"  # J-2 de la grande marée du 25/11 (seuil 95)


@pytest.fixture
def sent(hass: HomeAssistant) -> dict[str, list[dict]]:
    calls: dict[str, list[dict]] = {"phone": [], "watch": []}
    for name, key in (("mobile_app_iphone", "phone"), ("mobile_app_galaxy_watch", "watch")):
        hass.services.async_register(
            "notify", name, lambda call, k=key: calls[k].append(dict(call.data))
        )
    return calls


async def _setup(hass, marees, freezer, now, **options) -> MockConfigEntry:
    freezer.move_to(now)
    phone = options.pop("phone", PHONE)
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        title="Port-Louis (Locmalo)",
        unique_id=marees.device.id,
        data={CONF_PROFILE: "coastal", CONF_PORT_DEVICE: marees.device.id,
              CONF_ADMIN_NOTIFY_TARGET: phone},
        options={CONF_SPRING_THRESHOLD: 100, "notify_time": "07:00:00", **options},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


async def _tick(hass, freezer, when: str) -> None:
    """Avance l'horloge à `when` et déclenche les minuteries échues (dont celle de 07:00)."""
    freezer.move_to(when)
    async_fire_time_changed(hass, dt_util.utcnow(), fire_all=True)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_daily_summary_phone_with_image(hass, marees, freezer, sent) -> None:
    events = []
    hass.bus.async_listen(EVENT_DAILY_SUMMARY, events.append)
    entry = await _setup(hass, marees, freezer, "2026-11-21T05:00:00+00:00",
                         notify_frequency="daily")
    await _tick(hass, freezer, PARIS_0700_21)
    assert len(sent["phone"]) == 1
    call = sent["phone"][0]
    assert call["title"] == "🌊 Port-Louis (Locmalo)"
    assert call["message"] == "HW 01:42 · 14:02 | LW 07:47 · 20:10 | coef 57-64"
    image_id = er.async_get(hass).async_get_entity_id(
        "image", DOMAIN, f"{entry.entry_id}_summary_image"
    )
    assert call["data"]["image"] == f"/api/image_proxy/{image_id}"
    assert sent["watch"] == []
    assert events and events[0].data["coefficients"] == [57, 64]

    # Même jour : jamais deux fois, même après un rechargement (anti-doublon persistant)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    async_fire_time_changed(hass, dt_util.utcnow(), fire_all=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(sent["phone"]) == 1


async def test_never_sends_nothing_but_fires_events(hass, marees, freezer, sent) -> None:
    events = []
    hass.bus.async_listen(EVENT_DAILY_SUMMARY, events.append)
    await _setup(hass, marees, freezer, "2026-11-21T05:00:00+00:00", notify_frequency="never")
    await _tick(hass, freezer, PARIS_0700_21)
    assert sent["phone"] == [] and len(events) == 1


async def test_entry_from_0_2_sends_nothing(hass, marees, freezer, sent) -> None:
    """Option absente (entrée créée en 0.2) : rien n'est envoyé tant qu'on n'a pas choisi."""
    await _setup(hass, marees, freezer, "2026-11-21T05:00:00+00:00")
    await _tick(hass, freezer, PARIS_0700_21)
    assert sent["phone"] == []


async def test_remarkable_and_spring_tide(hass, marees, freezer, sent) -> None:
    springs = []
    hass.bus.async_listen(EVENT_SPRING_TIDE, springs.append)
    # Seuil 95 : grande marée le 25/11 (coef 97) ; le 23/11 est donc J-2
    await _setup(hass, marees, freezer, "2026-11-23T05:00:00+00:00",
                 notify_frequency="remarkable", **{CONF_SPRING_THRESHOLD: 95})
    await _tick(hass, freezer, PARIS_0700_23)
    titles = [c["title"] for c in sent["phone"]]
    assert titles == ["🌊 Port-Louis (Locmalo)", "🌕 Spring tide in 2 days"]
    assert sent["phone"][1]["message"] == "Port-Louis (Locmalo): Wed Nov 25, coef 97 · HW 04:34 · 17:00"
    assert "image" not in sent["phone"][1]["data"]
    assert springs[0].data["date"] == "2026-11-25" and springs[0].data["days_before"] == 2


async def test_watch_notice_only_after_phone(hass, marees, freezer, sent) -> None:
    await _setup(hass, marees, freezer, "2026-11-21T05:00:00+00:00", notify_frequency="daily",
                 watch_mode="notice", watch_notify_target=WATCH)
    await _tick(hass, freezer, PARIS_0700_21)
    assert len(sent["phone"]) == 1
    assert sent["watch"] == [
        {"title": "Outdoor Brief", "message": "Port-Louis (Locmalo) brief sent to the phone",
         "data": {"tag": sent["phone"][0]["data"]["tag"]}}
    ]


async def test_watch_notice_skipped_without_phone(hass, marees, freezer, sent) -> None:
    await _setup(hass, marees, freezer, "2026-11-21T05:00:00+00:00", notify_frequency="daily",
                 watch_mode="notice", watch_notify_target=WATCH, phone=None)
    await _tick(hass, freezer, PARIS_0700_21)
    assert sent["phone"] == [] and sent["watch"] == []


async def test_watch_full_works_without_phone(hass, marees, freezer, sent) -> None:
    await _setup(hass, marees, freezer, "2026-11-21T05:00:00+00:00", notify_frequency="daily",
                 watch_mode="full", watch_notify_target=WATCH, phone=None)
    await _tick(hass, freezer, PARIS_0700_21)
    assert sent["phone"] == []
    assert sent["watch"][0]["message"] == "HW 01:42 · 14:02 | LW 07:47 · 20:10 | coef 57-64"
    assert "image" not in sent["watch"][0]["data"]


async def test_send_summary_action(hass, marees, freezer, sent) -> None:
    entry = await _setup(hass, marees, freezer, "2026-11-21T10:00:00+00:00",
                         notify_frequency="never")
    response = await hass.services.async_call(
        DOMAIN, "send_summary", {"config_entry_id": entry.entry_id},
        blocking=True, return_response=True,
    )
    assert response == {"sent": {"Port-Louis (Locmalo)": True}}
    assert len(sent["phone"]) == 1
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "send_summary", {"config_entry_id": "inconnu"}, blocking=True
        )


async def test_image_entity_serves_png(hass, marees, freezer, hass_client) -> None:
    entry = await _setup(hass, marees, freezer, "2026-11-21T18:52:00+00:00")
    image_id = er.async_get(hass).async_get_entity_id(
        "image", DOMAIN, f"{entry.entry_id}_summary_image"
    )
    client = await hass_client()
    # Même adresse que celle des notifications ; l'app Companion s'authentifie, ici le jeton
    resp = await client.get(hass.states.get(image_id).attributes["entity_picture"])
    assert resp.status == 200 and resp.content_type == "image/png"
    png = Image.open(BytesIO(await resp.read()))
    assert png.width == 1080


def test_render_themes_and_languages() -> None:
    summary = {
        "port": "Port-Louis (Locmalo)", "date": "2026-11-21", "tides": [],
        "coefficients": [], "next_tide": None, "next_spring_tide": None, "month_max": None,
        "spring_tide_threshold": 100,
    }
    for language, theme in (("fr", "light"), ("en", "dark"), (None, "inconnu")):
        assert render_png(summary, language, theme).startswith(b"\x89PNG")


def test_message_helpers() -> None:
    summary = {"tides": [], "coefficients": [], "spring_tide_threshold": 100,
               "next_spring_tide": {"date": "2026-11-30", "coefficient": 101}}
    assert summary_message(summary, "fr") == "—"
    assert not is_remarkable(summary, datetime(2026, 11, 21).date())
    assert is_remarkable(summary, datetime(2026, 11, 28).date())
    assert is_remarkable({**summary, "coefficients": [100]}, datetime(2026, 11, 21).date())
    assert not is_remarkable({"coefficients": [50]}, datetime(2026, 11, 21).date())


# --- 0.3.1 : cible entité, lien au toucher, regroupement ---------------------------------


async def test_entity_target_uses_device_service(hass, marees, freezer, sent) -> None:
    """Téléphone admin = entité notify de l'app : l'envoi passe par son service mobile_app."""
    from homeassistant.helpers import device_registry as dr

    app = MockConfigEntry(domain="mobile_app", title="iPhone")
    app.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=app.entry_id, identifiers={("mobile_app", "iphone")}, name="iPhone"
    )
    er.async_get(hass).async_get_or_create(
        "notify", "mobile_app", "iphone_notify", device_id=device.id,
        suggested_object_id="iphone", config_entry=app,
    )
    hass.states.async_set("notify.iphone", "unknown")
    send_message = []
    hass.services.async_register("notify", "send_message", lambda call: send_message.append(1))

    await _setup(hass, marees, freezer, "2026-11-21T05:00:00+00:00", notify_frequency="daily",
                 tap_url="/lovelace/meteo", phone="notify.iphone")
    await _tick(hass, freezer, PARIS_0700_21)
    assert send_message == []  # pas de send_message : il perdrait l'image
    data = sent["phone"][0]["data"]
    assert data["image"].startswith("/api/image_proxy/image.")
    assert data["url"] == data["clickAction"] == "/lovelace/meteo"


async def _add_port(hass, marees, name: str, **options) -> MockConfigEntry:
    from homeassistant.helpers import device_registry as dr

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=marees.entry.entry_id, identifiers={("marees_france", name)}, name=name
    )
    entry = MockConfigEntry(
        domain=DOMAIN, version=1, minor_version=1, title=name, unique_id=device.id,
        data={CONF_PROFILE: "coastal", CONF_PORT_DEVICE: device.id,
              CONF_ADMIN_NOTIFY_TARGET: PHONE},
        options={CONF_SPRING_THRESHOLD: 100, "notify_time": "07:00:00", **options},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_grouped_ports_send_one_notification(hass, marees, freezer, sent, hass_client):
    first = await _setup(hass, marees, freezer, "2026-11-23T05:00:00+00:00",
                         notify_frequency="daily", notify_grouping="grouped",
                         **{CONF_SPRING_THRESHOLD: 95})
    await _add_port(hass, marees, "Port-Tudy", notify_frequency="daily",
                    notify_grouping="grouped", **{CONF_SPRING_THRESHOLD: 95})
    await _add_port(hass, marees, "Lorient", notify_frequency="daily",
                    **{CONF_SPRING_THRESHOLD: 95})  # propre à ce port
    await _tick(hass, freezer, PARIS_0700_23)

    titles = [c["title"] for c in sent["phone"]]
    assert titles.count("🌊 Today's tides") == 1  # un seul résumé pour les deux regroupés
    assert titles.count("🌊 Lorient") == 1  # le port « propre » garde le sien
    assert titles.count("🌕 Spring tide in 2 days") == 2  # groupe + Lorient
    grouped = next(c for c in sent["phone"] if c["title"] == "🌊 Today's tides")
    assert grouped["message"].splitlines() == [
        "Port-Louis (Locmalo) : HW 03:07 · 15:30 | LW 09:17 · 21:37 | coef 81-86",
        "Port-Tudy : HW 03:07 · 15:30 | LW 09:17 · 21:37 | coef 81-86",
    ]
    spring = next(
        c for c in sent["phone"]
        if c["title"] == "🌕 Spring tide in 2 days" and "Port-Tudy" in c["message"]
    )
    assert len(spring["message"].splitlines()) == 2

    # L'image du port principal empile les deux ports : plus haute que celle d'un seul port
    image_id = er.async_get(hass).async_get_entity_id(
        "image", DOMAIN, f"{first.entry_id}_summary_image"
    )
    client = await hass_client()
    resp = await client.get(hass.states.get(image_id).attributes["entity_picture"])
    png = Image.open(BytesIO(await resp.read()))
    assert png.height > 1100


def test_invalid_tap_url() -> None:
    from custom_components.outdoor_brief.config_flow import _check_notifications

    _, errors = _check_notifications({"watch_mode": "off", "tap_url": "lovelace"})
    assert errors == {"tap_url": "invalid_tap_url"}
    values, errors = _check_notifications({"watch_mode": "off", "tap_url": " /lovelace/0 "})
    assert not errors and values["tap_url"] == "/lovelace/0"


async def test_send_summary_action_with_group(hass, marees, freezer, sent) -> None:
    """Sans port précisé : une seule notification pour le groupe (0.3.2)."""
    await _setup(hass, marees, freezer, "2026-11-23T10:00:00+00:00",
                 notify_frequency="daily", notify_grouping="grouped")
    second = await _add_port(hass, marees, "Port-Tudy", notify_frequency="daily",
                             notify_grouping="grouped")
    await _add_port(hass, marees, "Lorient", notify_frequency="daily")
    response = await hass.services.async_call(
        DOMAIN, "send_summary", {}, blocking=True, return_response=True
    )
    assert response == {"sent": {"Port-Louis (Locmalo)": True, "Lorient": True}}
    assert [c["title"] for c in sent["phone"]] == ["🌊 Today's tides", "🌊 Lorient"]

    # Port secondaire précisé : son propre résumé, pour tester
    await hass.services.async_call(
        DOMAIN, "send_summary", {"config_entry_id": second.entry_id}, blocking=True
    )
    assert sent["phone"][-1]["title"] == "🌊 Port-Tudy"
