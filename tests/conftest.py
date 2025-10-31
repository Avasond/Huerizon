import sys
import types
import pytest
from unittest.mock import patch

pytest_plugins = ["pytest_homeassistant_custom_component"]

@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    yield enable_custom_integrations

@pytest.fixture(autouse=True)
def _stub_turbojpeg():
    mod = types.ModuleType("turbojpeg")
    class _DummyJPEG:
        pass
    mod.TurboJPEG = _DummyJPEG
    sys.modules["turbojpeg"] = mod
    try:
        yield
    finally:
        sys.modules.pop("turbojpeg", None)

@pytest.fixture(autouse=True)
def _limit_platforms():
    with patch("custom_components.huerizon.__init__.PLATFORMS", []):
        yield
