import pytest

from custom_components.huerizon.helpers import (
    normalize_hue,
    normalize_percent,
)
from custom_components.huerizon.const import (
    SCALE_0_360,
    SCALE_0_255,
    SCALE_0_1,
    PERCENT_0_100,
)


def _val(x):
    """Support both old and new helpers return types.
    Some versions return just a float; newer ones may return (value, reason).
    This extracts the numeric value in either case."""
    if isinstance(x, tuple):
        return x[0]
    return x


def test_normalize_hue_360():
    assert _val(normalize_hue(360, SCALE_0_360)) == 360
    assert _val(normalize_hue(90, SCALE_0_360)) == 90


def test_normalize_hue_255():
    # 255 maps to 360; 128 ~= 181
    assert _val(normalize_hue(255, SCALE_0_255)) == 360
    assert _val(normalize_hue(128, SCALE_0_255)) == pytest.approx(181, abs=1)


def test_normalize_hue_01():
    assert _val(normalize_hue(1.0, SCALE_0_1)) == 360
    assert _val(normalize_hue(0.5, SCALE_0_1)) == 180


def test_normalize_percent_100():
    assert _val(normalize_percent(100, PERCENT_0_100)) == 100
    assert _val(normalize_percent(50, PERCENT_0_100)) == 50


def test_normalize_percent_255():
    assert _val(normalize_percent(255, SCALE_0_255)) == 100
    assert _val(normalize_percent(128, SCALE_0_255)) == pytest.approx(50, abs=1)


def test_normalize_percent_01():
    assert _val(normalize_percent(1.0, SCALE_0_1)) == 100
    assert _val(normalize_percent(0.25, SCALE_0_1)) == 25
