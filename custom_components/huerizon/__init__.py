import logging
from typing import Any, Dict, Set

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import service as ha_service
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    # Optional: if defined in const.py, we use it to seed defaults on first setup.
    # Otherwise this local fallback keeps behavior non-breaking.
    DEFAULT_OPTIONS as _DEFAULTS,  # type: ignore[attr-defined]
)


_LOGGER = logging.getLogger(__name__)

# If const.DEFAULT_OPTIONS isn't present, provide safe local defaults AND
# ensure new keys exist even when const.DEFAULT_OPTIONS is from an older build.
_DEFAULTS_FALLBACK: Dict[str, Any] = {
    # Source selection & entity wiring
    "source_mode": "json_topic",  # or: "entity_triplet"
    "json_sensor": "",  # entity_id of the combined JSON sensor
    "state_h_entity": "",  # entity_id for hue
    "state_s_entity": "",  # entity_id for saturation
    "state_b_entity": "",  # entity_id for brightness
    # Scaling
    "hue_scale": "auto",  # auto | 0-360 | 0-1 | 0-255
    "percent_scale": "auto",  # auto | 0-100 | 0-1 | 0-255
    # Scheduling / rate limiting (new)
    "only_at_night": False,  # run only when sun is down
    "active_start_time": "00:00:00",  # HH:MM:SS
    "active_end_time": "23:59:59",  # HH:MM:SS
    "active_days": [  # Mon-Sun selection
        "mon",
        "tue",
        "wed",
        "thu",
        "fri",
        "sat",
        "sun",
    ],
    "min_color_delta": 5.0,  # minimum delta before applying new color
    "rate_limit_sec": 2.0,  # throttle rapid updates
}

# Build DEFAULT_OPTIONS so that const.DEFAULT_OPTIONS may override values, while
# still guaranteeing presence of any new keys added in this version.
try:
    DEFAULT_OPTIONS: Dict[str, Any] = {**_DEFAULTS_FALLBACK, **dict(_DEFAULTS)}  # type: ignore[name-defined]
except Exception:  # pragma: no cover - fallback path
    DEFAULT_OPTIONS = dict(_DEFAULTS_FALLBACK)

PLATFORMS = [
    Platform.SENSOR
]  # Add Platform.CAMERA if you keep a native camera platform

SERVICE_APPLY_SKY = "apply_sky"


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    data = hass.data.setdefault(DOMAIN, {})
    entry_bucket = data.setdefault(entry.entry_id, {})
    entry_bucket["options"] = dict(entry.options)
    _LOGGER.debug("Huerizon options updated: %s", entry.options)

    # Reload the entry so platform(s) pick up new options.
    hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register Huerizon services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_APPLY_SKY):
        return

    async def _handle_apply_sky(call: ServiceCall) -> None:
        """Apply sky hue/saturation/brightness to target lights."""
        hue = call.data.get("hue")
        sat = call.data.get("saturation")
        bri = call.data.get("brightness_pct")

        # Extract targets from 'target' selector (areas/devices/entities)
        entity_ids: Set[str] = await ha_service.async_extract_entity_ids(hass, call)
        if not entity_ids:
            _LOGGER.warning("huerizon.apply_sky called without target lights")
            return

        # Build light.turn_on payload. Home Assistant expects (h, s) where s is 0-100.
        service_data: Dict[str, Any] = {"entity_id": list(entity_ids)}
        if hue is not None and sat is not None:
            service_data["hs_color"] = [float(hue), float(sat)]
        if bri is not None:
            service_data["brightness_pct"] = float(bri)

        await hass.services.async_call("light", "turn_on", service_data, blocking=False)

    hass.services.async_register(DOMAIN, SERVICE_APPLY_SKY, _handle_apply_sky)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Huerizon from a config entry created via the UI."""
    _LOGGER.debug("Setting up Huerizon integration: %s", entry.entry_id)

    # Seed defaults if any option is missing.
    merged_opts = {**DEFAULT_OPTIONS, **dict(entry.options or {})}
    if merged_opts != entry.options:
        _LOGGER.debug("Applying default options for Huerizon: %s", merged_opts)
        hass.config_entries.async_update_entry(entry, options=merged_opts)

    # Persist config & options for use by platforms
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id]["config"] = dict(entry.data)
    hass.data[DOMAIN][entry.entry_id]["options"] = dict(merged_opts)

    # Listen for options changes
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Register services
    await _async_register_services(hass)

    # Forward platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle unloading of a config entry."""
    _LOGGER.debug("Unloading Huerizon integration: %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Remove our entry bucket but keep DOMAIN root in case other entries exist.
        domain_bucket = hass.data.get(DOMAIN, {})
        if isinstance(domain_bucket, dict):
            domain_bucket.pop(entry.entry_id, None)
    return unload_ok
