"""Constants for the Huerizon integration."""

from __future__ import annotations
import logging

LOGGER = logging.getLogger(__name__)

# Integration domain
DOMAIN = "huerizon"
VERSION = "1.0.0"

# Optional topics (used by some blueprints/scripts)
TOPIC_COLOR = f"{DOMAIN}/color"
TOPIC_BRIGHTNESS = f"{DOMAIN}/brightness"
TOPIC_IMAGE_ORIGINAL = f"{DOMAIN}/image/original"
TOPIC_IMAGE_FILTERED = f"{DOMAIN}/image/filtered"

# Friendly names/icons (may be used by sensors/camera)
SENSOR_COLOR_NAME = "Huerizon Color"
SENSOR_BRIGHTNESS_NAME = "Huerizon Brightness"
CAMERA_ORIGINAL_NAME = "Huerizon Sky Image"
CAMERA_FILTERED_NAME = "Huerizon Sky Filtered"
FRIENDLY_NAME = "Huerizon Sky Monitor"

ICON_COLOR = "mdi:palette"
ICON_BRIGHTNESS = "mdi:brightness-6"
ICON_CAMERA = "mdi:camera"

# Defaults for MQTT (if referenced)
DEFAULT_PORT = 1883
DEFAULT_USER = "mqtt_user"
DEFAULT_PASS = "mqttGate"

# -------------------------
# Options / Config Flow keys
# -------------------------
# Basic selections
CONF_SOURCE_CAMERA = "source_camera"
CONF_TARGET_LIGHTS = "target_lights"

# Source mode (HOW we read Hue/Sat/Brightness)
CONF_SOURCE_MODE = "source_mode"  # one of SOURCE_MODE_JSON | SOURCE_MODE_TRIPLET
SOURCE_MODE_JSON = "json_topic"  # single JSON state sensor/entity
SOURCE_MODE_TRIPLET = "entity_triplet"  # three separate numeric entities

# JSON mode: one entity that yields a JSON payload with H/S/B
CONF_JSON_SENSOR = (
    "json_sensor"  # entity_id of sensor exposing {hue, saturation, brightness}
)

# Triplet mode: three separate entities
CONF_STATE_H_ENTITY = "state_h_entity"  # entity_id with numeric hue
CONF_STATE_S_ENTITY = "state_s_entity"  # entity_id with numeric saturation
CONF_STATE_B_ENTITY = "state_b_entity"  # entity_id with numeric brightness

# Scaling / normalization
CONF_HUE_SCALE = "hue_scale"  # one of SCALE_* below
CONF_PERCENT_SCALE = "percent_scale"  # one of SCALE_* below for S & B

SCALE_AUTO = "auto"
SCALE_0_360 = "0-360"  # degrees

SCALE_0_1 = "0-1"  # normalized
SCALE_0_255 = "0-255"  # raw byte
PERCENT_0_100 = "0-100"  # percent

# Schedule / trigger options
CONF_ONLY_AT_NIGHT = "only_at_night"  # bool
CONF_ACTIVE_START = "active_start"  # "HH:MM" local
CONF_ACTIVE_END = "active_end"  # "HH:MM" local
CONF_ACTIVE_DAYS = "active_days"  # list[int] 0=Mon..6=Sun
CONF_MIN_DELTA = "min_delta"  # float, percent/deg threshold for updates
CONF_RATE_LIMIT_SEC = "rate_limit_sec"  # int, minimum seconds between pushes

# -------------------------
# Backward-compat aliases (if older modules referenced these)
# -------------------------
# Input mode alias
CONF_INPUT_MODE = CONF_SOURCE_MODE
# Older JSON keys
CONF_STATE_SENSOR = CONF_JSON_SENSOR
CONF_JSON_HKEY = "json_hue_key"
CONF_JSON_SKEY = "json_sat_key"
CONF_JSON_BKEY = "json_bri_key"
# Older triplet keys
CONF_HUE_SENSOR = CONF_STATE_H_ENTITY
CONF_SAT_SENSOR = CONF_STATE_S_ENTITY
CONF_BRI_SENSOR = CONF_STATE_B_ENTITY
# Older scale lists
HUE_SCALES = [SCALE_0_360, SCALE_0_255, SCALE_0_1]
PCT_SCALES = [PERCENT_0_100, SCALE_0_255, SCALE_0_1]
# Older default scale names
DEFAULT_HUE_SCALE = SCALE_0_360
DEFAULT_SAT_SCALE = PERCENT_0_100
DEFAULT_BRI_SCALE = PERCENT_0_100

# -------------------------
# Default options used by options flow (safe to import everywhere)
# -------------------------
DEFAULT_OPTIONS = {
    # Source selection
    CONF_SOURCE_MODE: SOURCE_MODE_JSON,
    # JSON mode defaults
    CONF_JSON_SENSOR: "",  # e.g. sensor.sky_state
    CONF_JSON_HKEY: "hue",
    CONF_JSON_SKEY: "saturation",
    CONF_JSON_BKEY: "brightness",
    # Triplet mode defaults
    CONF_STATE_H_ENTITY: "",
    CONF_STATE_S_ENTITY: "",
    CONF_STATE_B_ENTITY: "",
    # Scaling defaults
    CONF_HUE_SCALE: SCALE_AUTO,  # auto | 0-360 | 0-255 | 0-1
    CONF_PERCENT_SCALE: SCALE_AUTO,  # auto | 0-100 | 0-255 | 0-1
    # Schedule / trigger defaults
    CONF_ONLY_AT_NIGHT: False,
    CONF_ACTIVE_START: "",  # empty = no time window
    CONF_ACTIVE_END: "",
    CONF_ACTIVE_DAYS: [],  # empty = all days
    CONF_MIN_DELTA: 0.0,  # 0 disables thresholding
    CONF_RATE_LIMIT_SEC: 0,  # 0 disables rate limit
    # Optional UI picks made elsewhere
    CONF_SOURCE_CAMERA: "",  # camera entity_id
    CONF_TARGET_LIGHTS: [],  # list of light entity_ids
}

# -------------------------
# Platform state mappings (for sensor.py imports)
# -------------------------
SOURCE_MODE_STATES = {
    "sky": {"clear", "cloudy", "overcast", "rain", "snow", "storm"},
    "manual": set(),
}

__all__ = [
    "DOMAIN",
    "VERSION",
    "DEFAULT_OPTIONS",
    "SOURCE_MODE_STATES",
]
