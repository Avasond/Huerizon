import logging
from typing import Any
from collections.abc import Mapping

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import service as ha_service
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, DEFAULT_OPTIONS as _DEFAULTS

_LOGGER = logging.getLogger(__name__)

_DEFAULTS_FALLBACK: dict[str, Any] = {
    "input_format": "xy",
    "x_entity": "",
    "y_entity": "",
    "r_entity": "",
    "g_entity": "",
    "b_entity": "",
    "mireds_entity": "",
    "kelvin_entity": "",
    "brightness_entity": "",
    "state_h_entity": "",
    "state_s_entity": "",
    "state_b_entity": "",

    "normalize": {
        "strip_symbols": True,
        "coerce_numbers": True,
        "clamp": True,
        "brightness_is_percent": False,
    },

    "apply_mode": "prefer_xy",

    "only_at_night": False,
    "active_start": None,
    "active_end": None,
    "active_days": [],
    "min_delta": 0.0,
    "rate_limit_sec": 0.0,
}

try:
    DEFAULT_OPTIONS: dict[str, Any] = {**_DEFAULTS_FALLBACK, **dict(_DEFAULTS)}
except Exception:
    DEFAULT_OPTIONS = dict(_DEFAULTS_FALLBACK)

PLATFORMS: tuple[Platform, ...] = (Platform.CAMERA,)

SERVICE_APPLY_SKY: str = "apply_sky"


def _coerce_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "on"}:
            return True
        if v in {"false", "0", "no", "off"}:
            return False
    return default


def _merge_and_normalize_options(options: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {**DEFAULT_OPTIONS, **dict(options or {})}

    for k in ("min_delta", "rate_limit_sec"):
        try:
            merged[k] = float(merged.get(k))
        except Exception:
            merged[k] = DEFAULT_OPTIONS[k]

    merged["only_at_night"] = _coerce_bool(
        merged.get("only_at_night"), DEFAULT_OPTIONS["only_at_night"]
    )

    norm_src = dict(merged.get("normalize", {}))
    norm = {
        "strip_symbols": _coerce_bool(norm_src.get("strip_symbols"), True),
        "coerce_numbers": _coerce_bool(norm_src.get("coerce_numbers"), True),
        "clamp": _coerce_bool(norm_src.get("clamp"), True),
        "brightness_is_percent": _coerce_bool(
            norm_src.get("brightness_is_percent"), False
        ),
    }
    merged["normalize"] = dict(norm)
    merged["_runtime_normalize"] = dict(norm)

    def _none_if_empty(val: Any) -> Any:
        if val is None:
            return None
        if isinstance(val, str) and val.strip() == "":
            return None
        return val

    merged["_runtime"] = {
        "input_format": (merged.get("input_format") or "xy").lower(),
        "entities": {
            "x": merged.get("x_entity", ""),
            "y": merged.get("y_entity", ""),
            "h": (merged.get("h_entity") or merged.get("state_h_entity", "")),
            "s": (merged.get("s_entity") or merged.get("state_s_entity", "")),
            "r": merged.get("r_entity", ""),
            "g": merged.get("g_entity", ""),
            "b": merged.get("b_entity", ""),
            "mireds": merged.get("mireds_entity", ""),
            "kelvin": merged.get("kelvin_entity", ""),
            "brightness": (merged.get("brightness_entity") or merged.get("state_b_entity", "")),
        },
        "apply_mode": (merged.get("apply_mode") or "prefer_xy").lower(),
        "schedule": {
            "only_at_night": bool(merged.get("only_at_night", False)),
            "active_start": _none_if_empty(merged.get("active_start", None)),
            "active_end": _none_if_empty(merged.get("active_end", None)),
            "active_days": list(merged.get("active_days", [])),
            "min_delta": float(merged.get("min_delta", DEFAULT_OPTIONS.get("min_delta", 0.0))),
            "rate_limit_sec": float(merged.get("rate_limit_sec", DEFAULT_OPTIONS.get("rate_limit_sec", 0.0))),
        },
    }

    return merged


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    merged = _merge_and_normalize_options(dict(entry.options))

    data = hass.data.setdefault(DOMAIN, {})
    entry_bucket = data.setdefault(entry.entry_id, {})
    entry_bucket["options"] = merged
    entry_bucket["runtime"] = merged.get("_runtime", {})
    entry_bucket["normalize"] = merged.get("_runtime_normalize", {})

    _LOGGER.debug("Huerizon options updated: %s", merged)

    hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))


async def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_APPLY_SKY):
        return

    async def _handle_apply_sky(call: ServiceCall) -> None:
        xy = call.data.get("xy_color")
        hs = call.data.get("hs_color")
        rgb = call.data.get("rgb_color")
        bri = call.data.get("brightness")
        source = call.data.get("source")

        hue = call.data.get("hue")
        sat = call.data.get("saturation")
        bri_pct = call.data.get("brightness_pct")

        entity_ids: set[str] = await ha_service.async_extract_entity_ids(hass, call)
        if not entity_ids:
            _LOGGER.warning("huerizon.apply_sky called without target lights")
            return

        service_data: dict[str, Any] = {"entity_id": list(entity_ids)}

        if isinstance(xy, (list, tuple)) and len(xy) == 2:
            try:
                service_data["xy_color"] = [float(xy[0]), float(xy[1])]
            except Exception:
                _LOGGER.debug("Invalid xy_color payload: %s", xy)
        elif isinstance(hs, (list, tuple)) and len(hs) == 2:
            try:
                service_data["hs_color"] = [float(hs[0]), float(hs[1])]
            except Exception:
                _LOGGER.debug("Invalid hs_color payload: %s", hs)
        elif isinstance(rgb, (list, tuple)) and len(rgb) == 3:
            try:
                service_data["rgb_color"] = [int(rgb[0]), int(rgb[1]), int(rgb[2])]
            except Exception:
                _LOGGER.debug("Invalid rgb_color payload: %s", rgb)
        elif hue is not None and sat is not None:
            try:
                service_data["hs_color"] = [float(hue), float(sat)]
            except Exception:
                _LOGGER.debug("Invalid legacy hue/saturation payload: %s, %s", hue, sat)

        if bri is not None:
            try:
                bri_val = int(float(bri))
                if bri_val < 0:
                    bri_val = 0
                if bri_val > 255:
                    bri_val = 255
                service_data["brightness"] = bri_val
            except Exception:
                _LOGGER.debug("Invalid brightness payload: %s", bri)
        elif bri_pct is not None:
            try:
                service_data["brightness_pct"] = float(bri_pct)
            except Exception:
                _LOGGER.debug("Invalid brightness_pct payload: %s", bri_pct)

        if source:
            _LOGGER.debug(
                "apply_sky called from source=%s payload=%s",
                source,
                {k: v for k, v in service_data.items() if k != "entity_id"},
            )

        await hass.services.async_call("light", "turn_on", service_data, blocking=False)

    hass.services.async_register(DOMAIN, SERVICE_APPLY_SKY, _handle_apply_sky)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setting up Huerizon integration: %s", entry.entry_id)

    merged = _merge_and_normalize_options(dict(entry.options))
    if merged != entry.options:
        _LOGGER.debug("Applying default/normalized options for Huerizon: %s", merged)
        hass.config_entries.async_update_entry(entry, options=merged)

    domain_bucket: dict[str, dict[str, Any]] = hass.data.setdefault(DOMAIN, {})
    entry_bucket: dict[str, Any] = domain_bucket.setdefault(entry.entry_id, {})
    entry_bucket["config"] = dict(entry.data)
    entry_bucket["options"] = dict(merged)
    entry_bucket["runtime"] = dict(merged.get("_runtime", {}))
    entry_bucket["normalize"] = dict(merged.get("_runtime_normalize", {}))

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await _async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Unloading Huerizon integration: %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_bucket = hass.data.get(DOMAIN, {})
        if isinstance(domain_bucket, dict):
            domain_bucket.pop(entry.entry_id, None)
    return unload_ok