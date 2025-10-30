import pytest
from homeassistant.data_entry_flow import FlowResultType
from custom_components.huerizon.const import DOMAIN

pytestmark = pytest.mark.asyncio


async def test_user_flow_creates_entry(hass):
    """Config flow should show the user step, then create an entry on submit."""
    # Start the user-initiated config flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Submit with empty data (integration stores options later via OptionsFlow)
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Huerizon Sky Sync"
    assert result2["data"] == {}

    # Ensure Home Assistant finishes any pending tasks from the flow
    await hass.async_block_till_done()
