# tests/test_setupoptions.py
import pytest
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.huerizon.const import DOMAIN, DEFAULT_OPTIONS


@pytest.mark.asyncio
async def test_setup_entry_seeds_default_options(hass: HomeAssistant) -> None:
    """Ensure missing options are filled from DEFAULT_OPTIONS and overrides are preserved."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={"rate_limit_sec": 1.0},  # override one key
        title="With override",
    )
    entry.add_to_hass(hass)

    ok = await hass.config_entries.async_setup(entry.entry_id)
    assert ok is True

    opts = hass.data[DOMAIN][entry.entry_id]["options"]
    for key in (
        "only_at_night",
        "active_start_time",
        "active_end_time",
        "active_days",
        "min_color_delta",
        "rate_limit_sec",
    ):
        assert key in opts

    assert opts["rate_limit_sec"] == 1.0
    for k, v in DEFAULT_OPTIONS.items():
        assert k in opts


@pytest.mark.asyncio
async def test_apply_sky_service_turns_on_light(hass: HomeAssistant) -> None:
    """apply_sky should call light.turn_on with hs_color + brightness_pct."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={}, title="Service Test")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)

    assert hass.services.has_service(DOMAIN, "apply_sky")

    calls = async_mock_service(hass, "light", "turn_on")

    await hass.services.async_call(
        DOMAIN,
        "apply_sky",
        {"hue": 15, "saturation": 45, "brightness_pct": 60},
        target={"entity_id": "light.office"},
        blocking=True,
    )

    assert len(calls) == 1
    payload = calls[0].data
    entity_ids = (
        payload["entity_id"]
        if isinstance(payload["entity_id"], list)
        else [payload["entity_id"]]
    )
    assert "light.office" in entity_ids
    assert payload["hs_color"] == [15.0, 45.0]
    assert payload["brightness_pct"] == 60.0


@pytest.mark.asyncio
async def test_options_update_triggers_reload(hass: HomeAssistant) -> None:
    """Changing options should trigger async_reload."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={}, title="Reload Test")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)

    with patch.object(
        hass.config_entries, "async_reload", wraps=hass.config_entries.async_reload
    ) as reload_spy:
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, "only_at_night": True}
        )
        await hass.async_block_till_done()
        reload_spy.assert_called_with(entry.entry_id)
