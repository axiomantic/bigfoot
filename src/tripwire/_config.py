"""Config loading for tripwire: reads [tool.tripwire] from pyproject.toml."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from tripwire._compat import tomllib


def load_tripwire_config(start: Path | None = None) -> dict[str, Any]:
    """Walk up from start (default: Path.cwd()) to find pyproject.toml.

    Returns the [tool.tripwire] table as a dict, or {} if:
    - no pyproject.toml found in start or any ancestor directory
    - pyproject.toml found but has no [tool.tripwire] section

    Raises tomllib.TOMLDecodeError if pyproject.toml is malformed.
    This is intentional: a malformed pyproject.toml is a user error that
    must not silently produce empty config.
    """
    from tripwire._errors import ConfigMigrationError  # noqa: PLC0415

    search = start or Path.cwd()
    for directory in (search, *search.parents):
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            with candidate.open("rb") as f:
                data = tomllib.load(f)
            if "bigfoot" in data.get("tool", {}):
                raise ConfigMigrationError(
                    "bigfoot was renamed to tripwire in 0.20.0; "
                    "rename the table to [tool.tripwire]"
                )
            result: dict[str, Any] = data.get("tool", {}).get("tripwire", {})
            return result
    return {}


# ---------------------------------------------------------------------------
# Guard-level config (C3 - per-protocol guard levels)
# ---------------------------------------------------------------------------

_VALID_LEVELS: Final[frozenset[str]] = frozenset({"warn", "error", "off"})
_LEVEL_ALIASES: Final[Mapping[str, str]] = {"strict": "error"}


@dataclass(frozen=True, slots=True)
class GuardLevels:
    """Resolved guard levels: a default plus per-plugin overrides.

    `default` applies when no override is registered for a given plugin.
    `overrides` maps plugin name (e.g., ``"subprocess"``, ``"dns"``) to
    a per-plugin level. Values in both fields are normalized to one of
    ``"warn"``, ``"error"``, or ``"off"``.
    """

    default: str
    overrides: Mapping[str, str] = field(default_factory=dict)


def _normalize_level(raw: str) -> str:
    """Normalize a guard-level string: lowercase, then apply aliases.

    Preserves the prior parser's ``.lower()`` behavior and the
    ``"strict"`` -> ``"error"`` alias so existing configs keep working.
    """
    lowered = raw.lower()
    return _LEVEL_ALIASES.get(lowered, lowered)


def _resolve_guard_levels(config: Mapping[str, Any]) -> GuardLevels:
    """Parse the ``guard`` config value into a ``GuardLevels`` object.

    Accepts:
    - missing key (defaults to ``"error"`` per the 0.20.0 default flip)
    - scalar string: ``guard = "warn"``
    - scalar bool: ``guard = false`` (normalized to ``"off"``)
    - nested table: ``[tool.tripwire.guard]`` with ``default`` and
      per-plugin keys

    Raises ``TripwireConfigError`` for invalid values.
    """
    from tripwire._errors import TripwireConfigError  # noqa: PLC0415

    raw = config.get("guard", "error")

    # Bool MUST be checked before int/str because bool is a subclass of
    # int. The design pseudocode pins bool first.
    if isinstance(raw, bool):
        if raw is False:
            return GuardLevels(default="off", overrides={})
        raise TripwireConfigError(
            '[tool.tripwire] guard = true is not a valid value. '
            'Use "warn", "error", "off", or false.'
        )

    if isinstance(raw, str):
        normalized = _normalize_level(raw)
        if normalized not in _VALID_LEVELS:
            raise TripwireConfigError(
                f"Invalid value {raw!r} for [tool.tripwire] guard. "
                f"Expected one of: {sorted(_VALID_LEVELS)}."
            )
        return GuardLevels(default=normalized, overrides={})

    if isinstance(raw, dict):
        default_raw = raw.get("default", "error")
        default: Any
        if isinstance(default_raw, bool):
            default = "off" if default_raw is False else default_raw
        elif isinstance(default_raw, str):
            default = _normalize_level(default_raw)
        else:
            default = default_raw
        if default not in _VALID_LEVELS:
            raise TripwireConfigError(
                f"Invalid value {default_raw!r} for [tool.tripwire.guard] default. "
                f"Expected one of: {sorted(_VALID_LEVELS)}."
            )
        overrides: dict[str, str] = {}
        for key, value in raw.items():
            if key == "default":
                continue
            normalized_value: Any
            if isinstance(value, bool):
                normalized_value = "off" if value is False else value
            elif isinstance(value, str):
                normalized_value = _normalize_level(value)
            else:
                normalized_value = value
            if normalized_value not in _VALID_LEVELS:
                raise TripwireConfigError(
                    f"Invalid value {value!r} for [tool.tripwire.guard] {key}. "
                    f"Expected one of: {sorted(_VALID_LEVELS)}."
                )
            overrides[key] = normalized_value
        return GuardLevels(default=default, overrides=overrides)

    raise TripwireConfigError(
        f"[tool.tripwire] guard must be a string, bool, or a table, "
        f"got {type(raw).__name__}: {raw!r}"
    )
