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


# New test: options flow roundtrip with JSON mode, no 400

@pytest.mark.asyncio
async def test_options_flow_roundtrip_no_400(hass: HomeAssistant) -> None:
    """Options flow should progress without raising and end with create_entry (no 400).

    This simulates the UI sequence:
      1) open options -> init form
      2) submit minimal valid data for JSON mode -> next step
      3) submit JSON sensor details -> create_entry
    """
    # Ensure the integration is set up so options flow is available
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={}, title="Options Flow")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)

    # Step 1: start the options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Import constants to provide valid values
    from custom_components.huerizon.const import (
        CONF_SOURCE_CAMERA,
        CONF_TARGET_LIGHTS,
        CONF_SOURCE_MODE,
        SOURCE_MODE_JSON,
        CONF_HUE_SCALE,
        CONF_PERCENT_SCALE,
        SCALE_AUTO,
        CONF_ONLY_AT_NIGHT,
        CONF_ACTIVE_START,
        CONF_ACTIVE_END,
        CONF_ACTIVE_DAYS,
        CONF_MIN_DELTA,
        CONF_RATE_LIMIT_SEC,
        CONF_JSON_SENSOR,
        CONF_JSON_HKEY,
        CONF_JSON_SKEY,
        CONF_JSON_BKEY,
    )

    # Step 2: submit the init form with minimal-but-valid values
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SOURCE_CAMERA: None,
            CONF_TARGET_LIGHTS: ["light.office"],  # list required
            CONF_SOURCE_MODE: SOURCE_MODE_JSON,     # choose JSON path
            CONF_HUE_SCALE: SCALE_AUTO,
            CONF_PERCENT_SCALE: SCALE_AUTO,
            CONF_ONLY_AT_NIGHT: False,
            CONF_ACTIVE_START: "00:00:00",
            CONF_ACTIVE_END: "23:59:59",
            CONF_ACTIVE_DAYS: [],
            CONF_MIN_DELTA: 0.0,
            CONF_RATE_LIMIT_SEC: 0,
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "source_json"

    # Step 3: submit the JSON sensor keys
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_JSON_SENSOR: "sensor.sky_color",
            CONF_JSON_HKEY: "hue",
            CONF_JSON_SKEY: "saturation",
            CONF_JSON_BKEY: "brightness",
        },
    )

    assert result["type"] == "create_entry"
    # A create_entry result means the flow completed successfully with no backend 400s
