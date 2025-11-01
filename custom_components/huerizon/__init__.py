import logging
from typing import Any, Tuple
from collections.abc import Mapping
from datetime import datetime, timedelta

from homeassistant.const import Platform, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, Event, callback
from homeassistant.helpers import service as ha_service
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.sun import get_astral_event_date
from homeassistant.util import dt as dt_util

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


def _merge_and_normalize_options(options: Mapping[str, Any]) -> Tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
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

    def _none_if_empty(val: Any) -> Any:
        if val is None:
            return None
        if isinstance(val, str) and val.strip() == "":
            return None
        return val

    runtime = {
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

    merged["normalize"] = dict(norm)

    return merged, runtime, dict(norm)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    merged, runtime, norm = _merge_and_normalize_options(dict(entry.options))

    data = hass.data.setdefault(DOMAIN, {})
    entry_bucket = data.setdefault(entry.entry_id, {})
    entry_bucket["options"] = merged
    entry_bucket["runtime"] = runtime
    entry_bucket["normalize"] = norm

    try:
        entry.runtime_data = {"runtime": runtime, "normalize": norm}
    except Exception:
        pass

    if merged != entry.options:
        hass.config_entries.async_update_entry(entry, options=merged)

    # Restart coordinator with new settings
    coordinator = entry_bucket.get("coordinator")
    if coordinator:
        await coordinator.async_stop()

    target_lights = merged.get("target_lights", [])
    if target_lights and runtime.get("entities"):
        new_coordinator = HuerizonCoordinator(hass, entry.entry_id, runtime, target_lights)
        entry_bucket["coordinator"] = new_coordinator
        await new_coordinator.async_start()
    else:
        entry_bucket.pop("coordinator", None)

    _LOGGER.debug("Huerizon options updated")


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
        ct_mireds = call.data.get("color_temp")
        ct_kelvin = call.data.get("color_temp_kelvin")
        transition = call.data.get("transition")

        entity_ids = await ha_service.async_extract_entity_ids(call)
        if not entity_ids and ATTR_ENTITY_ID in call.data:
            ids = call.data[ATTR_ENTITY_ID]
            entity_ids = {ids} if isinstance(ids, str) else set(ids)
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

        # Color temperature handling block (reversed priority, new logic)
        if ct_kelvin is not None:
            try:
                service_data["color_temp_kelvin"] = int(float(ct_kelvin))
            except Exception:
                _LOGGER.debug("Invalid color_temp_kelvin payload: %s", ct_kelvin)
        elif ct_mireds is not None:
            try:
                mireds_val = float(ct_mireds)
                if mireds_val > 0:
                    service_data["color_temp_kelvin"] = max(1, int(1000000 / mireds_val))
            except Exception:
                _LOGGER.debug("Invalid color_temp payload: %s", ct_mireds)

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

        if transition is not None:
            try:
                service_data["transition"] = float(transition)
            except Exception:
                _LOGGER.debug("Invalid transition payload: %s", transition)

        if source:
            _LOGGER.debug(
                "apply_sky called from source=%s payload=%s",
                source,
                {k: v for k, v in service_data.items() if k != "entity_id"},
            )

        await hass.services.async_call("light", "turn_on", service_data, blocking=False)

    hass.services.async_register(DOMAIN, SERVICE_APPLY_SKY, _handle_apply_sky)


class HuerizonCoordinator:
    """Coordinator to track entity state changes and trigger light updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        runtime: dict[str, Any],
        target_lights: list[str],
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.runtime = runtime
        self.target_lights = target_lights
        self._unsub_track = None
        self._last_update_time = None

    def _should_update(self) -> bool:
        """Check if update is allowed based on schedule and rate limit."""
        schedule = self.runtime.get("schedule", {})

        # Check rate limit
        rate_limit = schedule.get("rate_limit_sec", 0)
        if rate_limit > 0 and self._last_update_time:
            now = dt_util.utcnow()
            if (now - self._last_update_time).total_seconds() < rate_limit:
                return False

        # Check only_at_night
        if schedule.get("only_at_night", False):
            try:
                next_sunrise = get_astral_event_date(self.hass, "sunrise", dt_util.now())
                next_sunset = get_astral_event_date(self.hass, "sunset", dt_util.now())
                now = dt_util.now()

                if next_sunrise and next_sunset:
                    # If sunrise is before sunset, it means we're currently in daytime
                    if next_sunrise < next_sunset:
                        return False
            except Exception as e:
                _LOGGER.debug("Could not determine day/night status: %s", e)

        # Check active time range
        active_start = schedule.get("active_start")
        active_end = schedule.get("active_end")
        if active_start or active_end:
            now = dt_util.now()
            current_time = now.time()

            if active_start and active_end:
                from datetime import time as dt_time
                if isinstance(active_start, str):
                    h, m, s = active_start.split(":")
                    start_time = dt_time(int(h), int(m), int(s))
                else:
                    start_time = active_start

                if isinstance(active_end, str):
                    h, m, s = active_end.split(":")
                    end_time = dt_time(int(h), int(m), int(s))
                else:
                    end_time = active_end

                if start_time <= end_time:
                    if not (start_time <= current_time <= end_time):
                        return False
                else:  # Crosses midnight
                    if not (current_time >= start_time or current_time <= end_time):
                        return False

        # Check active days
        active_days = schedule.get("active_days", [])
        if active_days:
            now = dt_util.now()
            current_day = now.weekday()
            if current_day not in active_days:
                return False

        return True

    def _get_entity_value(self, entity_id: str) -> float | None:
        """Get numeric value from entity state."""
        if not entity_id:
            return None

        state = self.hass.states.get(entity_id)
        if not state:
            return None

        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    @callback
    def _handle_state_change(self, event: Event) -> None:
        """Handle state change of monitored entities."""
        if not self._should_update():
            _LOGGER.debug("Update skipped due to schedule/rate limit")
            return

        entities = self.runtime.get("entities", {})
        input_format = self.runtime.get("input_format", "xy")

        service_data: dict[str, Any] = {}

        # Collect values based on input format
        if input_format == "xy":
            x = self._get_entity_value(entities.get("x"))
            y = self._get_entity_value(entities.get("y"))
            if x is not None and y is not None:
                service_data["xy_color"] = [x, y]

        elif input_format == "hs":
            h = self._get_entity_value(entities.get("h"))
            s = self._get_entity_value(entities.get("s"))
            if h is not None and s is not None:
                service_data["hs_color"] = [h, s]

        elif input_format == "rgb":
            r = self._get_entity_value(entities.get("r"))
            g = self._get_entity_value(entities.get("g"))
            b = self._get_entity_value(entities.get("b"))
            if r is not None and g is not None and b is not None:
                service_data["rgb_color"] = [int(r), int(g), int(b)]

        elif input_format == "color_temp":
            mireds = self._get_entity_value(entities.get("mireds"))
            kelvin = self._get_entity_value(entities.get("kelvin"))
            if kelvin is not None:
                service_data["color_temp_kelvin"] = int(kelvin)
            elif mireds is not None and mireds > 0:
                service_data["color_temp_kelvin"] = max(1, int(1000000 / mireds))

        # Add brightness if configured
        brightness = self._get_entity_value(entities.get("brightness"))
        if brightness is not None:
            service_data["brightness"] = int(brightness)

        # Only call service if we have color data
        if not service_data or (len(service_data) == 1 and "brightness" in service_data):
            _LOGGER.debug("No valid color data to send")
            return

        # Add target lights (do not add source)
        service_data["entity_id"] = self.target_lights

        _LOGGER.debug("Calling light.turn_on with data: %s", service_data)

        # Call the service directly with properly formatted data
        # Use async_create_task since we're in a callback (can't use await)
        self.hass.async_create_task(
            self.hass.services.async_call("light", "turn_on", service_data, blocking=False)
        )

        self._last_update_time = dt_util.utcnow()

    async def async_start(self) -> None:
        """Start tracking entity state changes."""
        entities = self.runtime.get("entities", {})
        entity_ids = [
            eid for eid in entities.values()
            if eid and isinstance(eid, str) and eid.strip()
        ]

        if not entity_ids:
            _LOGGER.warning("No entities configured to monitor")
            return

        _LOGGER.debug("Tracking entities: %s", entity_ids)

        self._unsub_track = async_track_state_change_event(
            self.hass, entity_ids, self._handle_state_change
        )

    async def async_stop(self) -> None:
        """Stop tracking entity state changes."""
        if self._unsub_track:
            self._unsub_track()
            self._unsub_track = None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Setting up Huerizon integration: %s", entry.entry_id)

    merged, runtime, norm = _merge_and_normalize_options(dict(entry.options))

    if merged != entry.options:
        hass.config_entries.async_update_entry(entry, options=merged)

    domain_bucket: dict[str, dict[str, Any]] = hass.data.setdefault(DOMAIN, {})
    entry_bucket: dict[str, Any] = domain_bucket.setdefault(entry.entry_id, {})
    entry_bucket["config"] = dict(entry.data)
    entry_bucket["options"] = dict(merged)
    entry_bucket["runtime"] = dict(runtime)
    entry_bucket["normalize"] = dict(norm)

    try:
        entry.runtime_data = {"runtime": dict(runtime), "normalize": dict(norm)}
    except Exception:
        pass

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await _async_register_services(hass)

    # Set up the coordinator to monitor entities and trigger updates
    target_lights = merged.get("target_lights", [])
    if target_lights and runtime.get("entities"):
        coordinator = HuerizonCoordinator(hass, entry.entry_id, runtime, target_lights)
        entry_bucket["coordinator"] = coordinator
        await coordinator.async_start()
        entry.async_on_unload(coordinator.async_stop)
    else:
        _LOGGER.warning("No target lights or entities configured, automation disabled")

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