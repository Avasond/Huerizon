import pytest

# Use the pytest-homeassistant-custom-component plugin
pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom_components/ for all tests automatically."""
    yield
