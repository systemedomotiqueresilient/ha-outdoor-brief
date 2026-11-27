"""Fixtures : une fausse intégration Marées France (appareil + actions à réponse)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import device_registry as dr

from custom_components.outdoor_brief.admin_phone import CONF_ADMIN_NOTIFY_TARGET
from custom_components.outdoor_brief.const import (
    CONF_PORT_DEVICE,
    CONF_PROFILE,
    CONF_SPRING_THRESHOLD,
    DOMAIN,
    MAREES_DOMAIN,
)

FIXTURES = Path(__file__).parent / "fixtures"
# Relevé réel (Port-Louis, Locmalo) : samedi 21 novembre 2026, 19:52 heure de Paris
NOW = "2026-11-21T18:52:00+00:00"


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
async def paris(hass: HomeAssistant) -> None:
    await hass.config.async_set_time_zone("Europe/Paris")
    # Point générique au large de la Bretagne (lever et coucher du soleil réalistes)
    hass.config.latitude, hass.config.longitude = 47.0, -3.0


class FakeMarees:
    """Actions get_tides_data / get_coefficients_data de Marées France."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.tides: Any = load("tides.json")
        self.coefficients: Any = load("coefficients.json")
        self.entry = MockConfigEntry(domain=MAREES_DOMAIN, title="Marées France")
        self.entry.add_to_hass(hass)
        self.device = dr.async_get(hass).async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers={(MAREES_DOMAIN, "PORT_LOUIS")},
            name="Port-Louis (Locmalo)",
        )
        for service, attr in (("get_tides_data", "tides"), ("get_coefficients_data", "coefficients")):
            hass.services.async_register(
                MAREES_DOMAIN,
                service,
                self._handler(service, attr),
                supports_response=SupportsResponse.ONLY,
            )

    def _handler(self, service: str, attr: str):
        async def handle(call: ServiceCall) -> dict:
            self.calls.append((service, dict(call.data)))
            return getattr(self, attr)

        return handle


@pytest.fixture
def marees(hass: HomeAssistant) -> FakeMarees:
    return FakeMarees(hass)


@pytest.fixture
async def entry(hass: HomeAssistant, marees: FakeMarees, freezer) -> MockConfigEntry:
    freezer.move_to(NOW)
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        title="Port-Louis (Locmalo)",
        unique_id=marees.device.id,
        data={
            CONF_PROFILE: "coastal",
            CONF_PORT_DEVICE: marees.device.id,
            CONF_ADMIN_NOTIFY_TARGET: None,
        },
        options={CONF_SPRING_THRESHOLD: 100},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
