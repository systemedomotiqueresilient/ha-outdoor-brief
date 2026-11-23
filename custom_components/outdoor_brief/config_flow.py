"""Config flow (profil, port, réglages) et options flow d'Outdoor Brief."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import (
    DeviceSelector,
    DeviceSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TimeSelector,
)
import voluptuous as vol

from .admin_phone import (
    CONF_ADMIN_NOTIFY_TARGET,
    is_valid_target,
    list_mobile_notify_entities,
    list_mobile_notify_services,
    normalize_target,
    suggest_admin_target,
)
from .const import (
    CONF_GROUPING,
    CONF_IMAGE_THEME,
    CONF_NOTIFY_FREQUENCY,
    CONF_NOTIFY_TIME,
    CONF_PORT_DEVICE,
    CONF_PROFILE,
    CONF_SPRING_THRESHOLD,
    CONF_TAP_URL,
    CONF_WATCH_MODE,
    CONF_WATCH_TARGET,
    DEFAULT_IMAGE_THEME,
    DEFAULT_NEW_FREQUENCY,
    DEFAULT_NOTIFY_TIME,
    DEFAULT_SPRING_THRESHOLD,
    DOMAIN,
    FALLBACK_FREQUENCY,
    FREQUENCIES,
    GROUPING_OWN,
    GROUPINGS,
    MAREES_DOMAIN,
    MAX_SPRING_THRESHOLD,
    MIN_SPRING_THRESHOLD,
    PROFILE_COASTAL,
    PROFILES_AVAILABLE,
    THEMES,
    WATCH_MODES,
    WATCH_OFF,
)


def _settings_schema(
    hass: HomeAssistant, options: dict[str, Any], target: str | None
) -> vol.Schema:
    suggested, choices = suggest_admin_target(hass, target)
    return vol.Schema(
        {
            vol.Required(
                CONF_SPRING_THRESHOLD,
                default=options.get(CONF_SPRING_THRESHOLD, DEFAULT_SPRING_THRESHOLD),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_SPRING_THRESHOLD,
                    max=MAX_SPRING_THRESHOLD,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_ADMIN_NOTIFY_TARGET, description={"suggested_value": suggested}
            ): SelectSelector(
                SelectSelectorConfig(
                    options=choices, custom_value=True, mode=SelectSelectorMode.DROPDOWN
                )
            ),
        }
    )


def _split(user_input: dict[str, Any]) -> tuple[dict[str, Any], str | None, dict[str, str]]:
    """(options, téléphone admin pour entry.data, erreurs)."""
    values = dict(user_input)
    raw = values.pop(CONF_ADMIN_NOTIFY_TARGET, None)
    errors: dict[str, str] = {}
    if raw and str(raw).strip() and not is_valid_target(raw):
        errors[CONF_ADMIN_NOTIFY_TARGET] = "invalid_target"
    values[CONF_SPRING_THRESHOLD] = int(values.get(CONF_SPRING_THRESHOLD, DEFAULT_SPRING_THRESHOLD))
    return values, normalize_target(raw), errors


def _notifications_schema(
    hass: HomeAssistant, options: dict[str, Any], default_frequency: str
) -> vol.Schema:
    watch_choices = list_mobile_notify_services(hass) + list_mobile_notify_entities(hass)
    current_watch = options.get(CONF_WATCH_TARGET)
    if current_watch and current_watch not in watch_choices:
        watch_choices.insert(0, current_watch)

    def choice(key: str, values: tuple[str, ...]) -> SelectSelector:
        return SelectSelector(
            SelectSelectorConfig(
                options=list(values), translation_key=key, mode=SelectSelectorMode.LIST
            )
        )

    return vol.Schema(
        {
            vol.Required(
                CONF_NOTIFY_FREQUENCY,
                default=options.get(CONF_NOTIFY_FREQUENCY, default_frequency),
            ): choice(CONF_NOTIFY_FREQUENCY, FREQUENCIES),
            vol.Required(
                CONF_NOTIFY_TIME, default=options.get(CONF_NOTIFY_TIME, DEFAULT_NOTIFY_TIME)
            ): TimeSelector(),
            vol.Required(CONF_GROUPING, default=options.get(CONF_GROUPING, GROUPING_OWN)): choice(
                CONF_GROUPING, GROUPINGS
            ),
            vol.Required(
                CONF_IMAGE_THEME, default=options.get(CONF_IMAGE_THEME, DEFAULT_IMAGE_THEME)
            ): choice(CONF_IMAGE_THEME, THEMES),
            vol.Optional(
                CONF_TAP_URL, description={"suggested_value": options.get(CONF_TAP_URL)}
            ): TextSelector(),
            vol.Required(CONF_WATCH_MODE, default=options.get(CONF_WATCH_MODE, WATCH_OFF)): choice(
                CONF_WATCH_MODE, WATCH_MODES
            ),
            vol.Optional(
                CONF_WATCH_TARGET, description={"suggested_value": current_watch}
            ): SelectSelector(
                SelectSelectorConfig(
                    options=watch_choices, custom_value=True, mode=SelectSelectorMode.DROPDOWN
                )
            ),
        }
    )


def _check_notifications(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    values = dict(user_input)
    errors: dict[str, str] = {}
    watch = normalize_target(values.get(CONF_WATCH_TARGET))
    raw = values.get(CONF_WATCH_TARGET)
    if raw and str(raw).strip() and watch is None:
        errors[CONF_WATCH_TARGET] = "invalid_target"
    elif values.get(CONF_WATCH_MODE, WATCH_OFF) != WATCH_OFF and watch is None:
        errors[CONF_WATCH_TARGET] = "watch_target_required"
    values[CONF_WATCH_TARGET] = watch
    tap = str(values.get(CONF_TAP_URL) or "").strip()
    if tap and not tap.startswith(("/", "http://", "https://", "homeassistant://")):
        errors[CONF_TAP_URL] = "invalid_tap_url"
    values[CONF_TAP_URL] = tap or None
    return values, errors


class OutdoorBriefConfigFlow(ConfigFlow, domain=DOMAIN):
    """Une entrée par port Marées France."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._options: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Écran 1 : profil. En 0.1.0, seul le littoral existe."""
        if user_input is not None:
            self._data[CONF_PROFILE] = user_input[CONF_PROFILE]
            return await self.async_step_port()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROFILE, default=PROFILE_COASTAL): SelectSelector(
                        SelectSelectorConfig(
                            options=list(PROFILES_AVAILABLE),
                            translation_key=CONF_PROFILE,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_port(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Écran 2 : le port, c'est-à-dire un appareil Marées France."""
        if not self.hass.config_entries.async_entries(MAREES_DOMAIN):
            return self.async_abort(reason="marees_france_missing")
        if user_input is not None:
            device_id = user_input[CONF_PORT_DEVICE]
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()
            device = dr.async_get(self.hass).async_get(device_id)
            self._data[CONF_PORT_DEVICE] = device_id
            self.context["title_placeholders"] = {
                "port": (device.name_by_user or device.name) if device else device_id
            }
            return await self.async_step_settings()
        return self.async_show_form(
            step_id="port",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PORT_DEVICE): DeviceSelector(
                        DeviceSelectorConfig(integration=MAREES_DOMAIN)
                    )
                }
            ),
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Écran 3 : seuil des grandes marées et téléphone de l'administrateur."""
        errors: dict[str, str] = {}
        if user_input is not None:
            options, target, errors = _split(user_input)
            if not errors:
                self._data[CONF_ADMIN_NOTIFY_TARGET] = target
                self._options = options
                return await self.async_step_notifications()
        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(self.hass, {}, None),
            errors=errors,
        )

    async def async_step_notifications(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Écran 4 : notifications du téléphone et de la montre."""
        errors: dict[str, str] = {}
        if user_input is not None:
            values, errors = _check_notifications(user_input)
            if not errors:
                return self.async_create_entry(
                    title=self.context["title_placeholders"]["port"],
                    data=self._data,
                    options={**self._options, **values},
                )
        return self.async_show_form(
            step_id="notifications",
            data_schema=self.add_suggested_values_to_schema(
                _notifications_schema(self.hass, {}, DEFAULT_NEW_FREQUENCY), user_input or {}
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return OutdoorBriefOptionsFlow()


class OutdoorBriefOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="init", menu_options=["settings", "notifications"])

    async def async_step_notifications(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        options = dict(self.config_entry.options)
        errors: dict[str, str] = {}
        if user_input is not None:
            values, errors = _check_notifications(user_input)
            if not errors:
                return self.async_create_entry(data={**options, **values})
        return self.async_show_form(
            step_id="notifications",
            data_schema=_notifications_schema(self.hass, options, FALLBACK_FREQUENCY),
            errors=errors,
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self.config_entry
        target = normalize_target(entry.data.get(CONF_ADMIN_NOTIFY_TARGET))
        errors: dict[str, str] = {}
        if user_input is not None:
            options, target, errors = _split(user_input)
            if not errors:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_ADMIN_NOTIFY_TARGET: target}
                )
                return self.async_create_entry(data={**entry.options, **options})
        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(self.hass, dict(entry.options), target),
            errors=errors,
        )
