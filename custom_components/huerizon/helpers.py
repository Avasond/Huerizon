"""Helper utilities for normalizing/reading HSB data for Huerizon.

This module is intentionally pure (no Home Assistant imports) so it can be
unit-tested without HA. It focuses on:
- Coercing raw inputs (strings, numbers, None) into floats
- Normalizing hue/saturation/brightness to canonical units:
    hue: 0–360 degrees
    saturation: 0–100 percent
    brightness: 0–100 percent
- Extracting HSB from either:
    * A JSON payload with keys {"hue","saturation","brightness"}
    * Three separate sensor states (one each for hue/saturation/brightness)

Supported input “scales”:
    Hue:       "auto" | "deg" | "0_360" | "0_255" | "0_1"
    Percent:   "auto" | "0_100" | "0_255" | "0_1"

Where:
- "deg" and "0_360" are synonymous (already in degrees)
- "0_255" maps x in [0..255] to percent or degrees
- "0_1"   maps x in [0..1]   to percent or degrees
- "auto"  tries to infer based on magnitude and/or symbols (° or %)

All public functions return (value, notes) where `notes` is a short string with
any auto-inference decisions that were applied (can be surfaced in logs).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import json
import math
import re

__all__ = [
    "normalize_hue",
    "normalize_percent",
    "extract_hsb_from_json",
    "extract_hsb_from_states",
    "hsb_to_rgb",
]

DEGREE_RE = re.compile(r"[°\s]+$")
PERCENT_RE = re.compile(r"[%\s]+$")


def _norm_key(scale: str) -> str:
    """Normalize scale tokens by lowercasing and unifying separators."""
    return scale.replace("-", "_").strip().lower()


# ---------------------- generic coercion ----------------------


def _coerce_float(value: Any) -> Optional[float]:
    """Best-effort conversion to float. Returns None if not coercible."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Avoid bool (bool is subclass of int)
        if isinstance(value, bool):
            return float(1 if value else 0)
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Strip known suffixes then try again
        s = DEGREE_RE.sub("", s)
        s = PERCENT_RE.sub("", s)
        try:
            return float(s)
        except ValueError:
            return None
    # Fallback: try stringifying
    try:
        return float(str(value))
    except Exception:
        return None


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---------------------- normalization ----------------------


def normalize_hue(raw: Any, scale: str = "auto") -> Tuple[Optional[float], str]:
    """Normalize hue to degrees [0, 360].

    scale: "auto" | "deg" | "0_360"/"0-360" | "0_255"/"0-255" | "0_1"/"0-1"
    Returns (hue_deg, notes)
    """
    notes = []
    # Pre-hint from symbols
    prehint_deg = False
    if isinstance(raw, str) and "°" in raw:
        prehint_deg = True

    val = _coerce_float(raw)
    if val is None:
        return None, "hue: not a number"

    # Auto detection
    if scale == "auto":
        if prehint_deg:
            scale_eff = "deg"
            notes.append("auto→deg(symbol)")
        elif 0.0 <= val <= 1.0:
            scale_eff = "0_1"
            notes.append("auto→0_1")
        elif 1.0 < val <= 360.0:
            scale_eff = "deg"
            notes.append("auto→deg(range)")
        elif 0.0 <= val <= 255.0:
            scale_eff = "0_255"
            notes.append("auto→0_255(range)")
        else:
            # Out-of-range; default to degrees and clamp
            scale_eff = "deg"
            notes.append("auto→deg(default)")
    else:
        scale_eff = _norm_key(scale)

    if scale_eff in ("deg", "0_360"):
        hue = _clamp(val, 0.0, 360.0)
    elif scale_eff == "0_1":
        hue = _clamp(val, 0.0, 1.0) * 360.0
    elif scale_eff == "0_255":
        hue = _clamp(val, 0.0, 255.0) / 255.0 * 360.0
    else:
        # Unknown scale; treat as degrees
        hue = _clamp(val, 0.0, 360.0)
        notes.append(f"unknown_scale({scale_eff})→deg")

    # Clamp to [0, 360] (do not wrap 360->0)
    hue = _clamp(hue, 0.0, 360.0)
    return hue, ";".join(notes)


def normalize_percent(raw: Any, scale: str = "auto") -> Tuple[Optional[float], str]:
    """Normalize percent-like values to [0, 100].

    scale: "auto" | "0_100"/"0-100" | "0_255"/"0-255" | "0_1"/"0-1"
    Returns (percent, notes)
    """
    notes = []
    # Pre-hint
    if isinstance(raw, str) and "%" in raw:
        scale_eff = "0_100" if scale == "auto" else _norm_key(scale)
        if scale == "auto":
            notes.append("auto→0_100(symbol)")
    else:
        val = _coerce_float(raw)
        if val is None:
            return None, "percent: not a number"

        if scale == "auto":
            if 0.0 <= val <= 1.0:
                scale_eff = "0_1"
                notes.append("auto→0_1")
            elif 0.0 <= val <= 100.0:
                scale_eff = "0_100"
                notes.append("auto→0_100(range)")
            elif 0.0 <= val <= 255.0:
                scale_eff = "0_255"
                notes.append("auto→0_255(range)")
            else:
                scale_eff = "0_100"
                notes.append("auto→0_100(default)")
        else:
            scale_eff = _norm_key(scale)

    # We need val again (may have been coerced above inside branch)
    val2 = _coerce_float(raw)
    if val2 is None:
        return None, "percent: not a number"

    if scale_eff == "0_100":
        pct = _clamp(val2, 0.0, 100.0)
    elif scale_eff == "0_1":
        pct = _clamp(val2, 0.0, 1.0) * 100.0
    elif scale_eff == "0_255":
        pct = _clamp(val2, 0.0, 255.0) / 255.0 * 100.0
    else:
        pct = _clamp(val2, 0.0, 100.0)
        notes.append(f"unknown_scale({scale_eff})→0_100")

    return pct, ";".join(notes)


# ---------------------- extraction helpers ----------------------


def extract_hsb_from_json(
    payload: str,
    hue_scale: str = "auto",
    sat_scale: str = "auto",
    bri_scale: str = "auto",
) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    """Given a JSON payload, extract hue/saturation/brightness and normalize.

    Returns (hue_deg, sat_pct, bri_pct, notes)
    """
    notes = []
    try:
        obj = json.loads(payload)
    except Exception as e:
        return None, None, None, f"json_error({e})"

    h_raw = obj.get("hue")
    s_raw = obj.get("saturation")
    b_raw = obj.get("brightness")

    h, n1 = normalize_hue(h_raw, hue_scale)
    s, n2 = normalize_percent(s_raw, sat_scale)
    b, n3 = normalize_percent(b_raw, bri_scale)

    for n in (n1, n2, n3):
        if n:
            notes.append(n)

    return h, s, b, ";".join(filter(None, notes))


def extract_hsb_from_states(
    hue_state: Any,
    sat_state: Any,
    bri_state: Any,
    hue_scale: str = "auto",
    sat_scale: str = "auto",
    bri_scale: str = "auto",
) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    """Given three raw state values (often HA state strings), normalize HSB.

    Returns (hue_deg, sat_pct, bri_pct, notes)
    """
    h, n1 = normalize_hue(hue_state, hue_scale)
    s, n2 = normalize_percent(sat_state, sat_scale)
    b, n3 = normalize_percent(bri_state, bri_scale)

    notes = ";".join(filter(None, (n1, n2, n3)))
    return h, s, b, notes


# ---------------------- conversion helpers ----------------------


def hsb_to_rgb(h_deg: float, s_pct: float, b_pct: float) -> Tuple[int, int, int]:
    """Convert HSB (Hue[0..360], Sat[0..100], Bri[0..100]) to RGB 0..255.

    Returns (r, g, b) ints in [0,255]. Values are clamped before conversion.
    """
    h = (h_deg % 360.0) / 360.0
    s = _clamp(s_pct, 0.0, 100.0) / 100.0
    v = _clamp(b_pct, 0.0, 100.0) / 100.0

    if s == 0.0:
        x = int(round(v * 255))
        return x, x, x

    i = int(math.floor(h * 6.0))
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)

    i_mod = i % 6
    if i_mod == 0:
        r, g, b = v, t, p
    elif i_mod == 1:
        r, g, b = q, v, p
    elif i_mod == 2:
        r, g, b = p, v, t
    elif i_mod == 3:
        r, g, b = p, q, v
    elif i_mod == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q

    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
