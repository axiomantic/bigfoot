# src/bigfoot/pytest_plugin.py
"""pytest fixture registration for bigfoot."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from bigfoot._config import load_bigfoot_config
from bigfoot._context import _current_test_verifier
from bigfoot._verifier import StrictVerifier


def pytest_configure(config: pytest.Config) -> None:
    """Register bigfoot pytest markers."""
    config.addinivalue_line(
        "markers",
        'allow(*plugin_names): allow specific plugins to make real calls (guard mode)',
    )


@pytest.fixture(autouse=True)
def _bigfoot_auto_verifier() -> Generator[StrictVerifier, None, None]:
    """Auto-use fixture: creates a StrictVerifier for each test, invisible to test authors.

    verify_all() is called at teardown automatically. The sandbox is NOT automatically
    activated -- the test (or module-level bigfoot.sandbox()) controls sandbox lifetime.
    """
    verifier = StrictVerifier()
    token = _current_test_verifier.set(verifier)
    yield verifier
    _current_test_verifier.reset(token)
    verifier.verify_all()


@pytest.fixture
def bigfoot_verifier(_bigfoot_auto_verifier: StrictVerifier) -> StrictVerifier:
    """Explicit fixture for tests that need direct access to the verifier.

    Usage:
        def test_something(bigfoot_verifier):
            http = HttpPlugin(bigfoot_verifier)
            http.mock_response("GET", "https://api.example.com/data", json={})
            with bigfoot_verifier.sandbox():
                response = httpx.get("https://api.example.com/data")
                bigfoot_verifier.assert_interaction(http.request, method="GET")
    """
    return _bigfoot_auto_verifier


@pytest.fixture(autouse=True, scope="session")
def _bigfoot_guard_patches() -> Generator[None, None, None]:
    """Install I/O plugin patches at session start for guard mode.

    Only installs patches for plugins that:
    - Have their dependencies available
    - Have supports_guard = True
    - Are default_enabled (not opt-in plugins like file_io, native)

    Uses the existing reference-counting activate/deactivate mechanism.
    At session teardown, all activated plugins are deactivated.
    """
    config = load_bigfoot_config()
    if not config.get("guard", True):
        yield
        return

    from bigfoot._base_plugin import BasePlugin
    from bigfoot._registry import PLUGIN_REGISTRY, _is_available, get_plugin_class

    activated: list[BasePlugin] = []

    for entry in PLUGIN_REGISTRY:
        if not entry.default_enabled:
            continue
        if not _is_available(entry):
            continue
        try:
            plugin_cls = get_plugin_class(entry)
            if not getattr(plugin_cls, "supports_guard", True):
                continue
            # Create minimal plugin instance just for activate/deactivate.
            # __new__ skips __init__; activate() uses ClassVars for patch
            # installation via reference counting, so no verifier is needed.
            plugin = plugin_cls.__new__(plugin_cls)
            plugin.activate()
            activated.append(plugin)
        except Exception:
            pass  # Skip plugins that fail to activate

    yield

    for plugin in reversed(activated):
        try:
            plugin.deactivate()
        except Exception:
            pass
