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
)
import voluptuous as vol

from .admin_phone import (
    CONF_ADMIN_NOTIFY_TARGET,
    is_valid_target,
    normalize_target,
    suggest_admin_target,
)
from .const import (
    CONF_PORT_DEVICE,
    CONF_PROFILE,
    CONF_SPRING_THRESHOLD,
    DEFAULT_SPRING_THRESHOLD,
    DOMAIN,
    MAREES_DOMAIN,
    MAX_SPRING_THRESHOLD,
    MIN_SPRING_THRESHOLD,
    PROFILE_COASTAL,
    PROFILES_AVAILABLE,
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
    values[CONF_SPRING_THRESHOLD] = int(
        values.get(CONF_SPRING_THRESHOLD, DEFAULT_SPRING_THRESHOLD)
    )
    return values, normalize_target(raw), errors


class OutdoorBriefConfigFlow(ConfigFlow, domain=DOMAIN):
    """Une entrée par port Marées France."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

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
                return self.async_create_entry(
                    title=self.context["title_placeholders"]["port"],
                    data={**self._data, CONF_ADMIN_NOTIFY_TARGET: target},
                    options=options,
                )
        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(self.hass, {}, None),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return OutdoorBriefOptionsFlow()


class OutdoorBriefOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self.config_entry
        target = normalize_target(entry.data.get(CONF_ADMIN_NOTIFY_TARGET))
        errors: dict[str, str] = {}
        if user_input is not None:
            options, target, errors = _split(user_input)
            if not errors:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_ADMIN_NOTIFY_TARGET: target}
                )
                return self.async_create_entry(data=options)
        return self.async_show_form(
            step_id="init",
            data_schema=_settings_schema(self.hass, dict(entry.options), target),
            errors=errors,
        )
