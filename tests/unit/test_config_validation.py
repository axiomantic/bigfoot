"""C7: Strict TOML schema validation with typo suggestions.

Tests that unknown top-level keys, unknown plugin sub-tables, and unknown
per-protocol guard keys are rejected with TripwireConfigError. Suggestions
are produced via difflib.get_close_matches.

Note: the legacy-table migration error is C1's responsibility (covered by
the rename smoke/migration tests), not C7.
"""

from __future__ import annotations

import pytest

from tripwire._config import (
    _resolve_guard_levels,
    validate_top_level_schema,
)
from tripwire._errors import TripwireConfigError

# ---------------------------------------------------------------------------
# C7-T1: unknown top-level key rejected
# ---------------------------------------------------------------------------


def test_unknown_top_level_key_rejected() -> None:
    """[tool.tripwire] foobar = 1 raises TripwireConfigError mentioning the key."""
    config = {"foobar": 1}
    with pytest.raises(TripwireConfigError) as exc_info:
        validate_top_level_schema(config)
    assert "foobar" in str(exc_info.value)


# ---------------------------------------------------------------------------
# C7-T2: typo suggestion via difflib
# ---------------------------------------------------------------------------


def test_typo_suggestion() -> None:
    """[tool.tripwire] gaurd = "warn" raises with 'did you mean: guard' hint."""
    config = {"gaurd": "warn"}
    with pytest.raises(TripwireConfigError) as exc_info:
        validate_top_level_schema(config)
    message = str(exc_info.value)
    assert "gaurd" in message
    assert "did you mean: guard" in message


# ---------------------------------------------------------------------------
# C7-T3: invalid guard value rejected; .lower() preserved
# ---------------------------------------------------------------------------


def test_invalid_guard_value_rejected() -> None:
    """guard = "Warn" lowercases to "warn" and is accepted; bogus values raise."""
    # Capital W normalized via .lower() and accepted (preserves existing behavior).
    levels = _resolve_guard_levels({"guard": "Warn"})
    assert levels.default == "warn"
    assert dict(levels.overrides) == {}

    # A genuinely invalid value (after lowering) still raises with the
    # allowed-values list.
    with pytest.raises(TripwireConfigError) as exc_info:
        _resolve_guard_levels({"guard": "loud"})
    message = str(exc_info.value)
    assert "loud" in message
    assert "warn" in message
    assert "error" in message
    assert "off" in message


def test_strict_alias_accepted() -> None:
    """guard = "strict" is accepted as an alias for "error" (preserves existing behavior)."""
    levels = _resolve_guard_levels({"guard": "strict"})
    assert levels.default == "error"
    assert dict(levels.overrides) == {}

    # Also case-insensitive: "Strict" -> lower -> "strict" -> alias -> "error".
    levels_capital = _resolve_guard_levels({"guard": "Strict"})
    assert levels_capital.default == "error"
    assert dict(levels_capital.overrides) == {}


# ---------------------------------------------------------------------------
# C7-T5: unknown plugin sub-table rejected
# ---------------------------------------------------------------------------


def test_unknown_plugin_subtable_rejected() -> None:
    """[tool.tripwire.notarealplugin] x = 1 raises with the offending name."""
    config = {"notarealplugin": {"x": 1}}
    with pytest.raises(TripwireConfigError) as exc_info:
        validate_top_level_schema(config)
    assert "notarealplugin" in str(exc_info.value)


# ---------------------------------------------------------------------------
# C7-T6: unknown per-protocol guard key rejected with typo suggestion
# ---------------------------------------------------------------------------


def test_unknown_per_protocol_guard_key_rejected() -> None:
    """[tool.tripwire.guard] subprocesss = "error" raises with difflib suggestion."""
    config = {"guard": {"default": "error", "subprocesss": "error"}}
    with pytest.raises(TripwireConfigError) as exc_info:
        _resolve_guard_levels(config)
    message = str(exc_info.value)
    assert "subprocesss" in message
    assert "did you mean: subprocess" in message
