"""Config flow for Huerizon integration."""

from __future__ import annotations

from typing import Any, Dict
from homeassistant.data_entry_flow import FlowResult

from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_SOURCE_CAMERA,
    CONF_TARGET_LIGHTS,
    CONF_HUE_SCALE,
    CONF_PERCENT_SCALE,
    SCALE_AUTO,
    SCALE_0_360,
    SCALE_0_255,
    SCALE_0_1,
    PERCENT_0_100,
    CONF_STATE_H_ENTITY,
    CONF_STATE_S_ENTITY,
    CONF_STATE_B_ENTITY,
    DEFAULT_OPTIONS,
    CONF_ONLY_AT_NIGHT,
    CONF_ACTIVE_START,
    CONF_ACTIVE_END,
    CONF_ACTIVE_DAYS,
    CONF_MIN_DELTA,
    CONF_RATE_LIMIT_SEC,
    CONF_INPUT_FORMAT,
    FORMAT_XY,
    FORMAT_RGB,
    FORMAT_TEMP,
    CONF_X_ENTITY,
    CONF_Y_ENTITY,
    CONF_R_ENTITY,
    CONF_G_ENTITY,
    CONF_B_ENTITY,
    CONF_MIREDS_ENTITY,
    CONF_KELVIN_ENTITY,
    CONF_BRIGHTNESS_ENTITY,
    CONF_NORMALIZE,
    CONF_STRIP_SYMBOLS,
    CONF_COERCE_NUMBERS,
    CONF_CLAMP,
    CONF_BRIGHTNESS_IS_PERCENT,
    CONF_APPLY_MODE,
    APPLY_PREFER_XY,
    INPUT_FORMAT_OPTIONS,
    APPLY_MODE_OPTIONS,
)

SCALE_OPTIONS_HUE = [
    {"value": SCALE_AUTO, "label": "Auto detect"},
    {"value": SCALE_0_360, "label": "0-360"},
    {"value": SCALE_0_255, "label": "0-255"},
    {"value": SCALE_0_1, "label": "0-1"},
]

SCALE_OPTIONS_PERCENT = [
    {"value": SCALE_AUTO, "label": "Auto detect"},
    {"value": PERCENT_0_100, "label": "0-100"},
    {"value": SCALE_0_255, "label": "0-255"},
    {"value": SCALE_0_1, "label": "0-1"},
]

DOW_OPTIONS = [
    {"value": "0", "label": "Mon"},
    {"value": "1", "label": "Tue"},
    {"value": "2", "label": "Wed"},
    {"value": "3", "label": "Thu"},
    {"value": "4", "label": "Fri"},
    {"value": "5", "label": "Sat"},
    {"value": "6", "label": "Sun"},
]


class HuerizonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Initial config flow for Huerizon."""

    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step.

        We don't require settings at install time; users will choose the
        source mode, camera, and lights from the Options flow.
        """
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Huerizon Sky Sync", data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return HuerizonOptionsFlowHandler(config_entry)


class HuerizonOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to pick camera/lights and configure HSB source parsing."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry
        base = dict(DEFAULT_OPTIONS)
        base.update(entry.options or {})
        self._opts: Dict[str, Any] = base
        self._working: Dict[str, Any] = {}

        for _k in (CONF_ACTIVE_START, CONF_ACTIVE_END):
            if self._opts.get(_k) == "":
                self._opts[_k] = None
        if isinstance(self._opts.get(CONF_ACTIVE_DAYS), list):
            self._opts[CONF_ACTIVE_DAYS] = [str(v) for v in self._opts[CONF_ACTIVE_DAYS]]
        if self._opts.get(CONF_SOURCE_CAMERA) == "":
            self._opts[CONF_SOURCE_CAMERA] = None

        norm = dict(self._opts.get(CONF_NORMALIZE, {}))
        norm.setdefault(CONF_STRIP_SYMBOLS, True)
        norm.setdefault(CONF_COERCE_NUMBERS, True)
        norm.setdefault(CONF_CLAMP, True)
        norm.setdefault(CONF_BRIGHTNESS_IS_PERCENT, False)
        self._opts[CONF_NORMALIZE] = norm
        self._opts.setdefault(CONF_APPLY_MODE, APPLY_PREFER_XY)
        self._opts.setdefault(CONF_INPUT_FORMAT, FORMAT_XY)

    def _finalize(self) -> Dict[str, Any]:
        """Merge working options and coerce types for storage."""
        merged: Dict[str, Any] = {**self._opts, **self._working}

        if CONF_ACTIVE_DAYS in merged and isinstance(merged[CONF_ACTIVE_DAYS], list):
            merged[CONF_ACTIVE_DAYS] = [
                int(v) for v in merged[CONF_ACTIVE_DAYS]
                if isinstance(v, (str, int)) and str(v).isdigit()
            ]

        for _k in (CONF_ACTIVE_START, CONF_ACTIVE_END):
            if merged.get(_k) in ("", None):
                merged[_k] = None

        if merged.get(CONF_SOURCE_CAMERA) in ("", None):
            merged[CONF_SOURCE_CAMERA] = None

        norm = dict(merged.get(CONF_NORMALIZE, {}))
        for k in (CONF_STRIP_SYMBOLS, CONF_COERCE_NUMBERS, CONF_CLAMP, CONF_BRIGHTNESS_IS_PERCENT):
            if k in merged:
                norm[k] = bool(merged.pop(k))
            else:
                norm.setdefault(k, True if k in (CONF_STRIP_SYMBOLS, CONF_COERCE_NUMBERS, CONF_CLAMP) else False)
        merged[CONF_NORMALIZE] = norm

        return merged

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """First page: choose camera, target lights, input format, scales, schedule, and normalization."""
        if user_input is not None:
            if CONF_SOURCE_CAMERA in user_input and not user_input[CONF_SOURCE_CAMERA]:
                user_input.pop(CONF_SOURCE_CAMERA, None)

            self._working.update(user_input)

            fmt = user_input.get(CONF_INPUT_FORMAT, FORMAT_XY)
            if fmt == FORMAT_XY:
                return await self.async_step_format_xy()
            if fmt == FORMAT_RGB:
                return await self.async_step_format_rgb()
            if fmt == FORMAT_TEMP:
                return await self.async_step_format_temp()
            return await self.async_step_format_hs()

        opts = self._opts
        norm = opts.get(CONF_NORMALIZE, {})

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SOURCE_CAMERA,
                    default=(opts.get(CONF_SOURCE_CAMERA) if opts.get(CONF_SOURCE_CAMERA) is not None else vol.UNDEFINED),
                ): vol.Any(
                    selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["camera"])
                    ),
                    None,
                ),
                vol.Required(
                    CONF_TARGET_LIGHTS,
                    default=opts.get(CONF_TARGET_LIGHTS, []),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["light"], multiple=True)
                ),
                vol.Required(
                    CONF_INPUT_FORMAT,
                    default=opts.get(CONF_INPUT_FORMAT, FORMAT_XY),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=INPUT_FORMAT_OPTIONS, mode="dropdown")
                ),
                vol.Optional(
                    CONF_HUE_SCALE,
                    default=opts.get(CONF_HUE_SCALE, SCALE_AUTO),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=SCALE_OPTIONS_HUE, mode="dropdown")
                ),
                vol.Optional(
                    CONF_PERCENT_SCALE,
                    default=opts.get(CONF_PERCENT_SCALE, SCALE_AUTO),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=SCALE_OPTIONS_PERCENT, mode="dropdown")
                ),
                vol.Optional(
                    CONF_APPLY_MODE,
                    default=opts.get(CONF_APPLY_MODE, APPLY_PREFER_XY),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=APPLY_MODE_OPTIONS, mode="dropdown")
                ),
                vol.Optional(
                    CONF_ONLY_AT_NIGHT,
                    default=opts.get(CONF_ONLY_AT_NIGHT, DEFAULT_OPTIONS.get(CONF_ONLY_AT_NIGHT, False)),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_ACTIVE_START,
                    default=(opts.get(CONF_ACTIVE_START) if opts.get(CONF_ACTIVE_START) is not None else vol.UNDEFINED),
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_ACTIVE_END,
                    default=(opts.get(CONF_ACTIVE_END) if opts.get(CONF_ACTIVE_END) is not None else vol.UNDEFINED),
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_ACTIVE_DAYS,
                    default=[str(v) for v in opts.get(CONF_ACTIVE_DAYS, DEFAULT_OPTIONS.get(CONF_ACTIVE_DAYS, []))],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=DOW_OPTIONS, multiple=True, mode="list"),
                ),
                vol.Optional(
                    CONF_MIN_DELTA,
                    default=opts.get(CONF_MIN_DELTA, DEFAULT_OPTIONS.get(CONF_MIN_DELTA, 0.0)),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=360, step=0.1, mode="box")
                ),
                vol.Optional(
                    CONF_RATE_LIMIT_SEC,
                    default=opts.get(CONF_RATE_LIMIT_SEC, DEFAULT_OPTIONS.get(CONF_RATE_LIMIT_SEC, 0)),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=3600, step=1, mode="box")
                ),
                vol.Optional(
                    CONF_STRIP_SYMBOLS,
                    default=norm.get(CONF_STRIP_SYMBOLS, True),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_COERCE_NUMBERS,
                    default=norm.get(CONF_COERCE_NUMBERS, True),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_CLAMP,
                    default=norm.get(CONF_CLAMP, True),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_BRIGHTNESS_IS_PERCENT,
                    default=norm.get(CONF_BRIGHTNESS_IS_PERCENT, False),
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)


    async def async_step_format_xy(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Pick entities for xy input format."""
        if user_input is not None:
            self._working.update(user_input)
            return self.async_create_entry(title="", data=self._finalize())

        schema = vol.Schema(
            {
                vol.Required(CONF_X_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
                vol.Required(CONF_Y_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
                vol.Optional(CONF_BRIGHTNESS_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
            }
        )
        return self.async_show_form(step_id="format_xy", data_schema=schema)

    async def async_step_format_hs(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Pick entities for hs input format."""
        if user_input is not None:
            self._working.update(user_input)
            return self.async_create_entry(title="", data=self._finalize())

        schema = vol.Schema(
            {
                vol.Required(CONF_STATE_H_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
                vol.Required(CONF_STATE_S_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
                vol.Optional(CONF_STATE_B_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
            }
        )
        return self.async_show_form(step_id="format_hs", data_schema=schema)

    async def async_step_format_rgb(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Pick entities for rgb input format."""
        if user_input is not None:
            self._working.update(user_input)
            return self.async_create_entry(title="", data=self._finalize())

        schema = vol.Schema(
            {
                vol.Required(CONF_R_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
                vol.Required(CONF_G_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
                vol.Required(CONF_B_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
                vol.Optional(CONF_BRIGHTNESS_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
            }
        )
        return self.async_show_form(step_id="format_rgb", data_schema=schema)

    async def async_step_format_temp(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Pick entities for color temperature input format."""
        schema = vol.Schema(
            {
                vol.Optional(CONF_MIREDS_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
                vol.Optional(CONF_KELVIN_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
                vol.Optional(CONF_BRIGHTNESS_ENTITY, default=vol.UNDEFINED): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number"])
                ),
            }
        )
        if user_input is not None:
            if not user_input.get(CONF_MIREDS_ENTITY) and not user_input.get(CONF_KELVIN_ENTITY):
                return self.async_show_form(
                    step_id="format_temp",
                    data_schema=schema,
                    errors={"base": "require_one_temp_source"},
                )
            self._working.update(user_input)
            return self.async_create_entry(title="", data=self._finalize())
        return self.async_show_form(step_id="format_temp", data_schema=schema)
