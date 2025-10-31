from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.huerizon.const import DOMAIN, DEFAULT_OPTIONS


async def test_setup_entry(hass: HomeAssistant) -> None:
    """Integration config_entry should set up cleanly with default options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},  # we store almost everything in options
        options=DEFAULT_OPTIONS,  # safe defaults from const.py
        title="Mock Title",
    )
    entry.add_to_hass(hass)

    ok = await hass.config_entries.async_setup(entry.entry_id)
    assert ok is True

    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.LOADED
