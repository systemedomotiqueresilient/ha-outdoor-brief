"""Config flow, options flow, capteurs, erreurs de source, module commun et versions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import custom_components.outdoor_brief as ob
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.outdoor_brief import admin_phone
from custom_components.outdoor_brief.admin_phone import (
    ATTR_NOTIFY_SERVICE,
    CONF_ADMIN_NOTIFY_TARGET,
)
from custom_components.outdoor_brief.const import (
    CARD_FILE,
    CONF_PORT_DEVICE,
    CONF_PROFILE,
    CONF_SPRING_THRESHOLD,
    DOMAIN,
    FRONTEND_URL,
    SCHEMA_VERSION,
    VERSION,
)
from custom_components.outdoor_brief.coordinator import OutdoorBriefCoordinator

from .conftest import NOW, FakeMarees

MOBILE = "notify.mobile_app_pixel_9"


def _entity(hass: HomeAssistant, entry, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{key}")
    assert entity_id
    return entity_id


# --- Config flow --------------------------------------------------------------


async def test_full_flow(hass: HomeAssistant, marees: FakeMarees, freezer) -> None:
    freezer.move_to(NOW)
    hass.services.async_register("notify", "mobile_app_pixel_9", lambda call: None)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROFILE: "coastal"}
    )
    assert result["step_id"] == "port"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PORT_DEVICE: marees.device.id}
    )
    assert result["step_id"] == "settings"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SPRING_THRESHOLD: 100, CONF_ADMIN_NOTIFY_TARGET: "nimporte"}
    )
    assert result["errors"] == {CONF_ADMIN_NOTIFY_TARGET: "invalid_target"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SPRING_THRESHOLD: 95.0, CONF_ADMIN_NOTIFY_TARGET: MOBILE}
    )
    assert result["step_id"] == "notifications"
    notif = {
        "notify_frequency": "daily",
        "notify_time": "07:00:00",
        "image_theme": "light",
        "watch_mode": "notice",
    }
    result = await hass.config_entries.flow.async_configure(result["flow_id"], notif)
    assert result["errors"] == {"watch_notify_target": "watch_target_required"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**notif, "watch_notify_target": "montre"}
    )
    assert result["errors"] == {"watch_notify_target": "invalid_target"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**notif, "watch_notify_target": "notify.mobile_app_galaxy_watch"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Port-Louis (Locmalo)"
    assert result["data"] == {
        CONF_PROFILE: "coastal",
        CONF_PORT_DEVICE: marees.device.id,
        CONF_ADMIN_NOTIFY_TARGET: MOBILE,
    }
    assert result["options"] == {
        CONF_SPRING_THRESHOLD: 95,
        **notif,
        "watch_notify_target": "notify.mobile_app_galaxy_watch",
        "notify_grouping": "own",
        "tap_url": None,
        "message_style": "short",
        "extra_notify_targets": [],
    }
    await hass.async_block_till_done()
    # Le port est toujours passé à l'action : sans lui, Marées France répond pour un autre port
    assert {data["device_id"] for _, data in marees.calls} == {marees.device.id}

    # Même port une seconde fois : refusé
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROFILE: "coastal"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PORT_DEVICE: marees.device.id}
    )
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"


async def test_flow_without_marees_france(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROFILE: "coastal"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "marees_france_missing"


async def test_options_flow(hass: HomeAssistant, entry) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "settings"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SPRING_THRESHOLD: 120, CONF_ADMIN_NOTIFY_TARGET: "x"}
    )
    assert result["errors"] == {CONF_ADMIN_NOTIFY_TARGET: "invalid_target"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SPRING_THRESHOLD: 95, CONF_ADMIN_NOTIFY_TARGET: MOBILE}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {CONF_SPRING_THRESHOLD: 95}
    assert entry.data[CONF_ADMIN_NOTIFY_TARGET] == MOBILE
    state = hass.states.get(_entity(hass, entry, "next_spring_tide"))
    assert state.state == "2026-11-25"  # le seuil 95 est appliqué après rechargement

    # Écran Notifications : les autres options sont conservées
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "notifications"}
    )
    assert result["step_id"] == "notifications"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "notify_frequency": "remarkable",
            "notify_time": "06:30:00",
            "image_theme": "dark",
            "watch_mode": "off",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options[CONF_SPRING_THRESHOLD] == 95
    assert entry.options["notify_frequency"] == "remarkable"
    assert entry.options["watch_notify_target"] is None


# --- Capteurs -------------------------------------------------------------------


async def test_sensors(hass: HomeAssistant, entry) -> None:
    summary = hass.states.get(_entity(hass, entry, "daily_summary"))
    assert summary.state == "2026-11-21"
    attrs = summary.attributes
    assert attrs["schema_version"] == SCHEMA_VERSION
    assert attrs["port"] == "Port-Louis (Locmalo)"
    assert attrs["tide_twelfth"] == 6
    assert attrs["coefficients"] == [57, 64]
    assert [(t["type"], t["time"][11:16], t["height"]) for t in attrs["tides"]] == [
        ("high", "01:42", 4.37),
        ("low", "07:47", 1.82),
        ("high", "14:02", 4.6),
        ("low", "20:10", 1.57),
    ]
    assert attrs["next_tide"]["type"] == "low"
    assert attrs["next_spring_tide"] == {"date": "2027-01-23", "coefficient": 104}
    assert attrs["month_max"] == {"date": "2026-11-25", "coefficient": 97}

    assert float(hass.states.get(_entity(hass, entry, "tidal_range")).state) == 3.03
    twelfth = hass.states.get(_entity(hass, entry, "tide_twelfth"))
    assert twelfth.state == "6"
    assert twelfth.attributes["trend"] == "falling"
    assert twelfth.attributes["range_share"] == "1/12"
    assert twelfth.attributes["duration_minutes"] == 368

    spring = hass.states.get(_entity(hass, entry, "next_spring_tide"))
    assert spring.state == "2027-01-23"
    assert spring.attributes["coefficient"] == 104
    assert spring.attributes["upcoming"][0] == {"date": "2027-01-23", "coefficient": 104}


async def test_recompute_without_refetch(hass: HomeAssistant, entry, marees, freezer) -> None:
    calls = len(marees.calls)
    freezer.move_to("2026-11-21T19:20:00+00:00")  # 20:20 à Paris : la marée montante a commencé
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    twelfth = hass.states.get(_entity(hass, entry, "tide_twelfth"))
    assert twelfth.state == "1" and twelfth.attributes["trend"] == "rising"
    assert float(hass.states.get(_entity(hass, entry, "tidal_range")).state) == 3.07
    assert len(marees.calls) == calls  # aucune relecture de Marées France


async def test_own_phone_seen_as_sibling(hass: HomeAssistant, marees, freezer) -> None:
    """admin_phone 1.2.0 : le téléphone d'Outdoor Brief est proposé aux intégrations sœurs."""
    freezer.move_to(NOW)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROFILE: "coastal", CONF_PORT_DEVICE: marees.device.id,
              CONF_ADMIN_NOTIFY_TARGET: MOBILE},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert "outdoor_brief" in admin_phone.SIBLING_PLATFORMS
    assert admin_phone.find_admin_targets(hass) == [MOBILE]


async def test_admin_phone_sensor(hass: HomeAssistant, entry) -> None:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_admin_notify_target"
    )
    assert registry.async_get(entity_id).entity_category is EntityCategory.DIAGNOSTIC
    state = hass.states.get(entity_id)
    assert state.state == "unknown" and state.attributes[ATTR_NOTIFY_SERVICE] is None


# --- Erreurs de source ------------------------------------------------------------


async def test_marees_france_missing_at_setup(hass: HomeAssistant, freezer) -> None:
    freezer.move_to(NOW)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_PROFILE: "coastal", CONF_PORT_DEVICE: "abc", CONF_ADMIN_NOTIFY_TARGET: None},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_empty_or_failing_source(hass: HomeAssistant, marees: FakeMarees, freezer) -> None:
    freezer.move_to(NOW)
    marees.tides = {}
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PROFILE: "coastal",
            CONF_PORT_DEVICE: marees.device.id,
            CONF_ADMIN_NOTIFY_TARGET: None,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY  # aucune marée renvoyée

    async def boom(call: ServiceCall) -> dict:
        raise HomeAssistantError("port inconnu")

    hass.services.async_register(
        "marees_france", "get_tides_data", boom, supports_response=SupportsResponse.ONLY
    )
    with pytest.raises(UpdateFailed):
        await OutdoorBriefCoordinator(hass, entry)._call("get_tides_data")


async def test_unload(hass: HomeAssistant, entry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


# --- Module commun et versions ------------------------------------------------------


def test_module_copy_and_versions() -> None:
    root = Path(__file__).parents[1]
    module = root / "custom_components" / DOMAIN / "admin_phone.py"
    assert admin_phone.MODULE_VERSION == "1.2.0"
    assert hashlib.sha256(module.read_bytes()).hexdigest() == (
        "1d720150ff1c709547018236afcb1c555e630c504be0c34b20fe0b79ed80545b"
    )
    manifest = json.loads((root / "custom_components" / DOMAIN / "manifest.json").read_text())
    assert manifest["version"] == VERSION == (root / "VERSION").read_text().strip()
    js = (root / "custom_components" / DOMAIN / "frontend" / CARD_FILE).read_text()
    assert f'const CARD_VERSION = "{VERSION}";' in js


# --- Carte Lovelace ------------------------------------------------------------------


async def test_card_registered(hass: HomeAssistant) -> None:
    hass.config.components.add("frontend")
    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    with patch.object(ob, "add_extra_js_url") as extra:
        assert await ob.async_setup(hass, {})
    config = hass.http.async_register_static_paths.call_args.args[0][0]
    assert config.url_path == FRONTEND_URL
    assert (Path(config.path) / CARD_FILE).is_file()
    extra.assert_called_once_with(hass, f"{FRONTEND_URL}/{CARD_FILE}?v={VERSION}")


async def test_card_skipped_without_frontend(hass: HomeAssistant) -> None:
    with patch.object(ob, "add_extra_js_url") as extra:
        assert await ob.async_setup(hass, {})
    extra.assert_not_called()


def test_card_never_injects_data_as_html() -> None:
    js = (Path(__file__).parents[1] / "custom_components" / DOMAIN / "frontend" / CARD_FILE)
    text = js.read_text(encoding="utf-8")
    # innerHTML ne reçoit que le gabarit fixe ; les données passent par textContent
    assert re.findall(r"innerHTML\s*=\s*([A-Z_]+)", text) == ["TEMPLATE"]
    assert 'customElements.define("outdoor-brief-card"' in text
    # L'éditeur ne propose que les résumés du jour (0.2.2)
    assert "include_entities: summaryEntities(this._hass)" in text


def test_translations_match() -> None:
    folder = Path(__file__).parents[1] / "custom_components" / DOMAIN
    strings = json.loads((folder / "strings.json").read_text(encoding="utf-8"))
    for lang in ("en", "fr"):
        other = json.loads((folder / "translations" / f"{lang}.json").read_text(encoding="utf-8"))

        def keys(node, prefix=""):
            if isinstance(node, dict):
                return {k for key, value in node.items() for k in keys(value, f"{prefix}.{key}")}
            return {prefix}

        assert keys(other) == keys(strings), lang
