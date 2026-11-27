"""Capteurs d'Outdoor Brief (v0.1 : profil littoral)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    EntityCategory,
    UnitOfLength,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .admin_phone import (
    ADMIN_TARGET_SUFFIX,
    ATTR_NOTIFY_SERVICE,
    CONF_ADMIN_NOTIFY_TARGET,
    normalize_target,
)
from .alerts import report_info
from .const import (
    CONF_SPRING_THRESHOLD,
    DEFAULT_SPRING_THRESHOLD,
    DOMAIN,
    UPCOMING_SPRING_TIDES,
    VERSION,
)
from .coordinator import BriefData, OutdoorBriefCoordinator
from .extras import daylight_only, fishing_threshold, has_pressure_source, pressure, windows
from .marine import MarineCoordinator, MarineData, surge
from .summary import build_summary
from .tides import HIGH, TWELFTHS, spring_tides, surrounding, tidal_range, twelfth


@dataclass(frozen=True, slots=True)
class Context:
    """Ce qu'un capteur sait au moment de calculer son état."""

    data: BriefData
    now: datetime
    today: date
    threshold: int
    port: str


@dataclass(frozen=True, kw_only=True)
class BriefSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Context], Any]
    attrs_fn: Callable[[Context], dict[str, Any]] = lambda ctx: {}


def _range(ctx: Context) -> float | None:
    return tidal_range(*surrounding(ctx.data.tides, ctx.now))


def _twelfth(ctx: Context) -> int | None:
    previous, next_tide = surrounding(ctx.data.tides, ctx.now)
    return twelfth(previous, next_tide, ctx.now)


def _twelfth_attrs(ctx: Context) -> dict[str, Any]:
    previous, next_tide = surrounding(ctx.data.tides, ctx.now)
    current = twelfth(previous, next_tide, ctx.now)
    if previous is None or next_tide is None or current is None:
        return {}
    return {
        "trend": "rising" if next_tide.kind == HIGH else "falling",
        "range_share": f"{TWELFTHS[current - 1]}/12",
        "started_at": previous.time.isoformat(),
        "ends_at": next_tide.time.isoformat(),
        "duration_minutes": round((next_tide.time - previous.time).total_seconds() / 60),
    }


def _spring(ctx: Context) -> list[tuple[date, int]]:
    return spring_tides(ctx.data.coefficients, ctx.today, ctx.threshold)


def _next_spring_attrs(ctx: Context) -> dict[str, Any]:
    upcoming = _spring(ctx)
    return {
        "coefficient": upcoming[0][1] if upcoming else None,
        "threshold": ctx.threshold,
        "upcoming": [
            {"date": day.isoformat(), "coefficient": coef}
            for day, coef in upcoming[:UPCOMING_SPRING_TIDES]
        ],
    }


def _summary_attrs(ctx: Context) -> dict[str, Any]:
    """Contrat public (schema_version) : lu par la carte, l'image et les tiers."""
    return build_summary(ctx.data, ctx.now, ctx.threshold, ctx.port)


SENSORS: tuple[BriefSensorDescription, ...] = (
    BriefSensorDescription(
        key="daily_summary",
        translation_key="daily_summary",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda ctx: ctx.today,
        attrs_fn=_summary_attrs,
    ),
    BriefSensorDescription(
        key="tidal_range",
        translation_key="tidal_range",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_range,
    ),
    BriefSensorDescription(
        key="tide_twelfth",
        translation_key="tide_twelfth",
        value_fn=_twelfth,
        attrs_fn=_twelfth_attrs,
    ),
    BriefSensorDescription(
        key="next_spring_tide",
        translation_key="next_spring_tide",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda ctx: upcoming[0][0] if (upcoming := _spring(ctx)) else None,
        attrs_fn=_next_spring_attrs,
    ),
)


def device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Outdoor Brief {entry.title}",
        manufacturer="SDR",
        model="Outdoor Brief",
        entry_type=DeviceEntryType.SERVICE,
        sw_version=VERSION,
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: OutdoorBriefCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        BriefSensor(coordinator, entry, description) for description in SENSORS
    ]
    entities += [FishingSensor(coordinator, entry), AdminPhoneSensor(entry)]
    # Entités créées seulement pour les données choisies (0.4)
    if has_pressure_source(entry, coordinator):
        entities.append(SurgeSensor(coordinator, entry))
    if coordinator.marine is not None:
        entities += [
            MarineSensor(coordinator.marine, entry, description) for description in MARINE_SENSORS
        ]
    async_add_entities(entities)


class BriefSensor(CoordinatorEntity[OutdoorBriefCoordinator], SensorEntity):
    """Capteur calculé à partir des données de Marées France et de l'heure courante."""

    _attr_has_entity_name = True
    entity_description: BriefSensorDescription

    def __init__(
        self,
        coordinator: OutdoorBriefCoordinator,
        entry: ConfigEntry,
        description: BriefSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = device_info(entry)

    def _snapshot(self) -> Context:
        now = dt_util.now()
        return Context(
            data=self.coordinator.data,
            now=now,
            today=now.date(),
            threshold=int(self._entry.options.get(CONF_SPRING_THRESHOLD, DEFAULT_SPRING_THRESHOLD)),
            port=self._entry.title,
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._snapshot())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self.entity_description.key != "daily_summary":
            return self.entity_description.attrs_fn(self._snapshot())
        notifier = self.coordinator.notifier
        attrs = (
            notifier.summary(dt_util.now())  # avec les blocs de la 0.4
            if notifier is not None
            else self.entity_description.attrs_fn(self._snapshot())
        )
        attrs["report"] = report_info(self.hass, self._entry)  # 0.3.5 : ajout
        return attrs


class AdminPhoneSensor(SensorEntity):
    """Cible de notification de l'administrateur, lue dans entry.data (convention SDR)."""

    _attr_has_entity_name = True
    _attr_translation_key = "admin_phone"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}{ADMIN_TARGET_SUFFIX}"
        self._attr_device_info = device_info(entry)

    @property
    def _target(self) -> str | None:
        return normalize_target(self._entry.data.get(CONF_ADMIN_NOTIFY_TARGET))

    @property
    def native_value(self) -> str | None:
        return self._target

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {ATTR_NOTIFY_SERVICE: self._target}


class FishingSensor(CoordinatorEntity[OutdoorBriefCoordinator], SensorEntity):
    """Début du prochain créneau de pêche à pied (0.4), avec les suivants en attributs."""

    _attr_has_entity_name = True
    _attr_translation_key = "next_fishing_window"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: OutdoorBriefCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_next_fishing_window"
        self._attr_device_info = device_info(entry)

    def _windows(self) -> list[Any]:
        found = windows(self.hass, self._entry, self.coordinator, dt_util.now())
        if daylight_only(self._entry):
            found = [w for w in found if w.daylight is not False]
        return found

    @property
    def native_value(self) -> datetime | None:
        found = self._windows()
        return found[0].start if found else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        found = self._windows()
        first = found[0].as_dict() if found else {}
        return {
            "end": first.get("end"),
            "low_tide": first.get("low_tide"),
            "height": first.get("height"),
            "coefficient": first.get("coefficient"),
            "daylight": first.get("daylight"),
            "threshold": fishing_threshold(self._entry),
            "daylight_only": daylight_only(self._entry),
            "upcoming": [w.as_dict() for w in found[:UPCOMING_SPRING_TIDES]],
        }


class SurgeSensor(CoordinatorEntity[OutdoorBriefCoordinator], SensorEntity):
    """Surcote (+) ou décote (−) estimée par l'effet de baromètre inverse (0.4)."""

    _attr_has_entity_name = True
    _attr_translation_key = "storm_surge"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: OutdoorBriefCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_storm_surge"
        self._attr_device_info = device_info(entry)

    def _surge(self) -> dict[str, Any] | None:
        return surge(*pressure(self.hass, self._entry, self.coordinator))

    @property
    def available(self) -> bool:
        return self._surge() is not None

    @property
    def native_value(self) -> int | None:
        value = self._surge()
        return value["height_cm"] if value else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        value = self._surge() or {}
        return {key: val for key, val in value.items() if key != "height_cm"}


@dataclass(frozen=True, kw_only=True)
class MarineSensorDescription(SensorEntityDescription):
    field: str


MARINE_SENSORS: tuple[MarineSensorDescription, ...] = (
    MarineSensorDescription(
        key="wave_height",
        translation_key="wave_height",
        field="wave_height",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    MarineSensorDescription(
        key="wave_period",
        translation_key="wave_period",
        field="wave_period",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    MarineSensorDescription(
        key="wave_direction",
        translation_key="wave_direction",
        field="wave_direction",
        native_unit_of_measurement=DEGREE,
        suggested_display_precision=0,
    ),
    MarineSensorDescription(
        key="swell_height",
        translation_key="swell_height",
        field="swell_height",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    MarineSensorDescription(
        key="swell_period",
        translation_key="swell_period",
        field="swell_period",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    MarineSensorDescription(
        key="swell_direction",
        translation_key="swell_direction",
        field="swell_direction",
        native_unit_of_measurement=DEGREE,
        suggested_display_precision=0,
    ),
    MarineSensorDescription(
        key="sea_temperature",
        translation_key="sea_temperature",
        field="sea_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
)


class MarineSensor(CoordinatorEntity[MarineCoordinator], SensorEntity):
    """Conditions de mer Open-Meteo au point choisi (créées seulement si activé)."""

    _attr_has_entity_name = True
    _attr_attribution = "Open-Meteo.com (CC BY 4.0)"
    entity_description: MarineSensorDescription

    def __init__(
        self,
        coordinator: MarineCoordinator,
        entry: ConfigEntry,
        description: MarineSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = device_info(entry)

    @property
    def native_value(self) -> float | None:
        data: MarineData | None = self.coordinator.data
        return getattr(data, self.entity_description.field) if data else None
