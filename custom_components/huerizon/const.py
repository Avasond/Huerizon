"""
Constants for the Huerizon integration.
"""

from __future__ import annotations
import logging

LOGGER = logging.getLogger(__name__)

DOMAIN = "huerizon"
VERSION = "1.0.0"

TOPIC_IMAGE_ORIGINAL = f"{DOMAIN}/image/original"
TOPIC_IMAGE_FILTERED = f"{DOMAIN}/image/filtered"

CAMERA_ORIGINAL_NAME = "Huerizon Sky Image"
CAMERA_FILTERED_NAME = "Huerizon Sky Filtered"
FRIENDLY_NAME = "Huerizon Sky Monitor"

ICON_CAMERA = "mdi:camera"

CONF_SOURCE_CAMERA = "source_camera"
CONF_TARGET_LIGHTS = "target_lights"

CONF_STATE_H_ENTITY = "state_h_entity"
CONF_STATE_S_ENTITY = "state_s_entity"
CONF_STATE_B_ENTITY = "state_b_entity"

CONF_HUE_SCALE = "hue_scale"
CONF_PERCENT_SCALE = "percent_scale"

SCALE_AUTO = "auto"
SCALE_0_360 = "0_360"
SCALE_0_1 = "0_1"
SCALE_0_255 = "0_255"
PERCENT_0_100 = "0_100"

CONF_ONLY_AT_NIGHT = "only_at_night"
CONF_ACTIVE_START = "active_start"
CONF_ACTIVE_END = "active_end"
CONF_ACTIVE_DAYS = "active_days"
CONF_MIN_DELTA = "min_delta"
CONF_RATE_LIMIT_SEC = "rate_limit_sec"

CONF_INPUT_FORMAT = "input_format"
FORMAT_XY = "xy"
FORMAT_HS = "hs"
FORMAT_RGB = "rgb"
FORMAT_TEMP = "color_temp"

CONF_X_ENTITY = "x_entity"
CONF_Y_ENTITY = "y_entity"

CONF_R_ENTITY = "r_entity"
CONF_G_ENTITY = "g_entity"
CONF_B_ENTITY = "b_entity"

CONF_MIREDS_ENTITY = "mireds_entity"
CONF_KELVIN_ENTITY = "kelvin_entity"

CONF_BRIGHTNESS_ENTITY = "brightness_entity"

CONF_NORMALIZE = "normalize"
CONF_STRIP_SYMBOLS = "strip_symbols"
CONF_COERCE_NUMBERS = "coerce_numbers"
CONF_CLAMP = "clamp"
CONF_BRIGHTNESS_IS_PERCENT = "brightness_is_percent"

CONF_APPLY_MODE = "apply_mode"
APPLY_PREFER_XY = "prefer_xy"
APPLY_PREFER_HS = "prefer_hs"
APPLY_PREFER_TEMP = "prefer_temp"

DEFAULT_OPTIONS = {
    CONF_STATE_H_ENTITY: "",
    CONF_STATE_S_ENTITY: "",
    CONF_STATE_B_ENTITY: "",
    CONF_HUE_SCALE: SCALE_AUTO,
    CONF_PERCENT_SCALE: SCALE_AUTO,
    CONF_ONLY_AT_NIGHT: False,
    CONF_ACTIVE_START: "",
    CONF_ACTIVE_END: "",
    CONF_ACTIVE_DAYS: [],
    CONF_MIN_DELTA: 0.0,
    CONF_RATE_LIMIT_SEC: 0,
    CONF_SOURCE_CAMERA: None,
    CONF_TARGET_LIGHTS: [],
    CONF_INPUT_FORMAT: FORMAT_XY,
    CONF_NORMALIZE: {
        CONF_STRIP_SYMBOLS: True,
        CONF_COERCE_NUMBERS: True,
        CONF_CLAMP: True,
        CONF_BRIGHTNESS_IS_PERCENT: False,
    },
    CONF_APPLY_MODE: APPLY_PREFER_XY,
    CONF_X_ENTITY: "",
    CONF_Y_ENTITY: "",
    CONF_R_ENTITY: "",
    CONF_G_ENTITY: "",
    CONF_B_ENTITY: "",
    CONF_MIREDS_ENTITY: "",
    CONF_KELVIN_ENTITY: "",
    CONF_BRIGHTNESS_ENTITY: "",
}

INPUT_FORMAT_OPTIONS = [
    {"label": "XY Color", "value": FORMAT_XY},
    {"label": "HS Color", "value": FORMAT_HS},
    {"label": "RGB Color", "value": FORMAT_RGB},
    {"label": "Color Temperature", "value": FORMAT_TEMP},
]

APPLY_MODE_OPTIONS = [
    {"label": "Prefer XY (accurate for Hue lights)", "value": APPLY_PREFER_XY},
    {"label": "Prefer HS (for RGBW lights)", "value": APPLY_PREFER_HS},
    {"label": "Prefer Temperature (for tunable whites)", "value": APPLY_PREFER_TEMP},
]

__all__ = [
    "LOGGER",
    "DOMAIN",
    "VERSION",
    "TOPIC_IMAGE_ORIGINAL",
    "TOPIC_IMAGE_FILTERED",
    "CAMERA_ORIGINAL_NAME",
    "CAMERA_FILTERED_NAME",
    "FRIENDLY_NAME",
    "ICON_CAMERA",
    "CONF_SOURCE_CAMERA",
    "CONF_TARGET_LIGHTS",
    "CONF_STATE_H_ENTITY",
    "CONF_STATE_S_ENTITY",
    "CONF_STATE_B_ENTITY",
    "CONF_HUE_SCALE",
    "CONF_PERCENT_SCALE",
    "SCALE_AUTO",
    "SCALE_0_360",
    "SCALE_0_1",
    "SCALE_0_255",
    "PERCENT_0_100",
    "CONF_ONLY_AT_NIGHT",
    "CONF_ACTIVE_START",
    "CONF_ACTIVE_END",
    "CONF_ACTIVE_DAYS",
    "CONF_MIN_DELTA",
    "CONF_RATE_LIMIT_SEC",
    "CONF_INPUT_FORMAT",
    "FORMAT_XY",
    "FORMAT_HS",
    "FORMAT_RGB",
    "FORMAT_TEMP",
    "CONF_X_ENTITY",
    "CONF_Y_ENTITY",
    "CONF_R_ENTITY",
    "CONF_G_ENTITY",
    "CONF_B_ENTITY",
    "CONF_MIREDS_ENTITY",
    "CONF_KELVIN_ENTITY",
    "CONF_BRIGHTNESS_ENTITY",
    "CONF_NORMALIZE",
    "CONF_STRIP_SYMBOLS",
    "CONF_COERCE_NUMBERS",
    "CONF_CLAMP",
    "CONF_BRIGHTNESS_IS_PERCENT",
    "CONF_APPLY_MODE",
    "APPLY_PREFER_XY",
    "APPLY_PREFER_HS",
    "APPLY_PREFER_TEMP",
    "DEFAULT_OPTIONS",
    "INPUT_FORMAT_OPTIONS",
    "APPLY_MODE_OPTIONS",
]
