"""Config flow for Huerizon integration."""

from __future__ import annotations

from typing import Any, Dict

from homeassistant import config_entries # type: ignore
import voluptuous as vol # type: ignore
from homeassistant.helpers import selector # type: ignore

from .const import (
    DOMAIN,
    # Basic
    CONF_SOURCE_CAMERA,
    CONF_TARGET_LIGHTS,
    # Flexible source options
    CONF_SOURCE_MODE,
    SOURCE_MODE_JSON,
    SOURCE_MODE_TRIPLET,
    CONF_HUE_SCALE,
    CONF_PERCENT_SCALE,
    SCALE_AUTO,
    SCALE_0_360,
    SCALE_0_255,
    SCALE_0_1,
    PERCENT_0_100,
    # JSON source specifics
    CONF_JSON_SENSOR,
    CONF_JSON_HKEY,
    CONF_JSON_SKEY,
    CONF_JSON_BKEY,
    # Triplet source specifics
    CONF_STATE_H_ENTITY,
    CONF_STATE_S_ENTITY,
    CONF_STATE_B_ENTITY,
    # Defaults
    DEFAULT_OPTIONS,
    CONF_ONLY_AT_NIGHT,
    CONF_ACTIVE_START,
    CONF_ACTIVE_END,
    CONF_ACTIVE_DAYS,
    CONF_MIN_DELTA,
    CONF_RATE_LIMIT_SEC,
)

# NOTE: Labels shown here are fallback UI strings.
# Proper, localized labels should be provided via translations (translations/en.json).
SCALE_OPTIONS_HUE = [
    {"value": SCALE_AUTO, "label": "Auto detect"},
    {"value": SCALE_0_360, "label": "0-360"},
    {"value": SCALE_0_255, "label": "0-255"},
    {"value": SCALE_0_1, "label": "0-1"},
]

SCALE_OPTIONS_PERCENT = [
    {"value": SCALE_AUTO, "label": "Auto detect"},
    {"value": PERCENT_0_100, "label": "0-100%"},
    {"value": SCALE_0_255, "label": "0-255"},
    {"value": SCALE_0_1, "label": "0-1"},
]

DOW_OPTIONS = [
    {"value": 0, "label": "Mon"},
    {"value": 1, "label": "Tue"},
    {"value": 2, "label": "Wed"},
    {"value": 3, "label": "Thu"},
    {"value": 4, "label": "Fri"},
    {"value": 5, "label": "Sat"},
    {"value": 6, "label": "Sun"},
]


class HuerizonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Initial config flow for Huerizon."""

    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None):
        """Handle the initial step.

        We don't require settings at install time; users will choose the
        source mode, camera, and lights from the Options flow.
        """
        if user_input is not None:
            return self.async_create_entry(title="Huerizon Sky Sync", data={})

        # Empty form – just click Submit to create the entry
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return HuerizonOptionsFlowHandler(config_entry)


class HuerizonOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to pick camera/lights and configure HSB source parsing."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry
        # Start with saved options, overlaid on DEFAULT_OPTIONS for safety
        base = dict(DEFAULT_OPTIONS)
        base.update(entry.options or {})
        self._opts: Dict[str, Any] = base
        self._working: Dict[str, Any] = {}

    async def async_step_init(self, user_input: Dict[str, Any] | None = None):
        """First page: choose camera, target lights, source mode, and scales."""
        if user_input is not None:
            # Stash and route based on mode
            self._working.update(user_input)
            mode = user_input.get(CONF_SOURCE_MODE, SOURCE_MODE_JSON)
            if mode == SOURCE_MODE_JSON:
                return await self.async_step_source_json()
            return await self.async_step_source_states()

        opts = self._opts
        mode_default = opts.get(CONF_SOURCE_MODE, SOURCE_MODE_JSON)

        schema = vol.Schema(
            {
                # Camera to preview and for future features (optional)
                vol.Optional(
                    CONF_SOURCE_CAMERA,
                    default=opts.get(CONF_SOURCE_CAMERA, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["camera"])
                ),
                # One or more lights to drive
                vol.Required(
                    CONF_TARGET_LIGHTS,
                    default=opts.get(CONF_TARGET_LIGHTS, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["light"], multiple=True)
                ),
                # Where H/S/B comes from
                vol.Required(
                    CONF_SOURCE_MODE,
                    default=mode_default,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": SOURCE_MODE_JSON, "label": "Single JSON sensor"},
                            {
                                "value": SOURCE_MODE_TRIPLET,
                                "label": "Three separate sensors",
                            },
                        ],
                        mode="dropdown",
                    )
                ),
                # How to interpret hue values
                vol.Optional(
                    CONF_HUE_SCALE,
                    default=opts.get(CONF_HUE_SCALE, SCALE_AUTO),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SCALE_OPTIONS_HUE, mode="dropdown"
                    )
                ),
                # How to interpret saturation/brightness values
                vol.Optional(
                    CONF_PERCENT_SCALE,
                    default=opts.get(CONF_PERCENT_SCALE, SCALE_AUTO),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SCALE_OPTIONS_PERCENT, mode="dropdown"
                    )
                ),
                # Scheduling / triggers
                vol.Optional(
                    CONF_ONLY_AT_NIGHT,
                    default=opts.get(
                        CONF_ONLY_AT_NIGHT,
                        DEFAULT_OPTIONS.get(CONF_ONLY_AT_NIGHT, False),
                    ),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_ACTIVE_START,
                    default=opts.get(
                        CONF_ACTIVE_START, DEFAULT_OPTIONS.get(CONF_ACTIVE_START, "")
                    ),
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_ACTIVE_END,
                    default=opts.get(
                        CONF_ACTIVE_END, DEFAULT_OPTIONS.get(CONF_ACTIVE_END, "")
                    ),
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_ACTIVE_DAYS,
                    default=opts.get(
                        CONF_ACTIVE_DAYS, DEFAULT_OPTIONS.get(CONF_ACTIVE_DAYS, [])
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=DOW_OPTIONS, multiple=True, mode="list"
                    ),
                ),
                vol.Optional(
                    CONF_MIN_DELTA,
                    default=opts.get(
                        CONF_MIN_DELTA, DEFAULT_OPTIONS.get(CONF_MIN_DELTA, 0.0)
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=360, step=0.1, mode="box")
                ),
                vol.Optional(
                    CONF_RATE_LIMIT_SEC,
                    default=opts.get(
                        CONF_RATE_LIMIT_SEC, DEFAULT_OPTIONS.get(CONF_RATE_LIMIT_SEC, 0)
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=3600, step=1, mode="box")
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_source_json(self, user_input: Dict[str, Any] | None = None):
        """Configure single-sensor JSON source."""
        if user_input is not None:
            self._working.update(user_input)
            # Persist everything
            merged = {**self._opts, **self._working}
            return self.async_create_entry(title="", data=merged)

        opts = self._opts

        schema = vol.Schema(
            {
                # Sensor entity whose state is JSON like {"hue": 123, "saturation": 45, "brightness": 67}
                vol.Required(
                    CONF_JSON_SENSOR,
                    default=opts.get(CONF_JSON_SENSOR, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                # Key names inside the JSON
                vol.Optional(
                    CONF_JSON_HKEY,
                    default=opts.get(CONF_JSON_HKEY, "hue"),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_JSON_SKEY,
                    default=opts.get(CONF_JSON_SKEY, "saturation"),
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_JSON_BKEY,
                    default=opts.get(CONF_JSON_BKEY, "brightness"),
                ): selector.TextSelector(),
            }
        )

        return self.async_show_form(step_id="source_json", data_schema=schema)

    async def async_step_source_states(self, user_input: Dict[str, Any] | None = None):
        """Configure three separate sensor entities for H/S/B."""
        if user_input is not None:
            self._working.update(user_input)
            merged = {**self._opts, **self._working}
            return self.async_create_entry(title="", data=merged)

        opts = self._opts

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_STATE_H_ENTITY,
                    default=opts.get(CONF_STATE_H_ENTITY, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
                vol.Required(
                    CONF_STATE_S_ENTITY,
                    default=opts.get(CONF_STATE_S_ENTITY, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
                vol.Required(
                    CONF_STATE_B_ENTITY,
                    default=opts.get(CONF_STATE_B_ENTITY, ""),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
            }
        )

        return self.async_show_form(step_id="source_states", data_schema=schema)
