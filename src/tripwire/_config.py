"""Config loading for tripwire: reads [tool.tripwire] from pyproject.toml."""

from __future__ import annotations

import difflib
import functools
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from tripwire._compat import tomllib


@functools.lru_cache(maxsize=8)
def _load_tripwire_config_cached(search: Path) -> dict[str, Any]:
    """Cached implementation of ``load_tripwire_config``.

    Cached because this function is called multiple times per test (once
    by the session-scoped guard fixture, once per ``StrictVerifier``
    instantiation). ``pyproject.toml`` is expected to be stable during a
    test run, so re-reading and re-parsing it on every call is wasted
    work.

    ``maxsize=8`` rather than ``1`` because different search roots must
    each cache independently — tests may invoke from different cwds or
    pass explicit start paths, and we do not want a path with a
    different ancestor chain to evict another entry.

    NOTE: ``search`` is the already-resolved root (never ``None``), so
    the cache key reflects the actual filesystem location rather than a
    sentinel that captures only the FIRST cwd a process called from.
    """
    from tripwire._errors import ConfigMigrationError  # noqa: PLC0415

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


def load_tripwire_config(start: Path | None = None) -> dict[str, Any]:
    """Walk up from start (default: Path.cwd()) to find pyproject.toml.

    Returns the [tool.tripwire] table as a dict, or {} if:
    - no pyproject.toml found in start or any ancestor directory
    - pyproject.toml found but has no [tool.tripwire] section

    Raises tomllib.TOMLDecodeError if pyproject.toml is malformed.
    This is intentional: a malformed pyproject.toml is a user error that
    must not silently produce empty config.

    Results are cached per-resolved-search-path (``start`` if provided,
    else ``Path.cwd()`` at call time). The cache survives across calls
    in the same process; tests that REWRITE an already-observed
    ``pyproject.toml`` mid-session must call
    ``load_tripwire_config.cache_clear()`` in their teardown to bust the
    cache. Tests that simply ``chdir`` between cases get fresh entries
    because the resolved cwd is the cache key.
    """
    search = start if start is not None else Path.cwd()
    return _load_tripwire_config_cached(search)


# Expose the cache controls on the public function so callers can write
# ``load_tripwire_config.cache_clear()`` without poking at the private
# helper. ``cache_info`` is included for symmetry / debug.
load_tripwire_config.cache_clear = _load_tripwire_config_cached.cache_clear  # type: ignore[attr-defined]
load_tripwire_config.cache_info = _load_tripwire_config_cached.cache_info  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Guard-level config (C3 - per-protocol guard levels)
# ---------------------------------------------------------------------------

_VALID_LEVELS: Final[frozenset[str]] = frozenset({"warn", "error", "off"})
_LEVEL_ALIASES: Final[Mapping[str, str]] = {"strict": "error"}


# ---------------------------------------------------------------------------
# Strict schema validation (C7)
# ---------------------------------------------------------------------------

# Scalar / table keys that may appear directly under [tool.tripwire] and are
# not plugin sub-tables. Plugin sub-table names are added dynamically from
# the registry by ``_allowed_top_level_keys``.
_TOP_LEVEL_NON_PLUGIN_KEYS: Final[frozenset[str]] = frozenset(
    {"guard", "firewall", "enabled_plugins", "disabled_plugins"}
)


def _allowed_top_level_keys() -> frozenset[str]:
    """Return the closed schema of allowed [tool.tripwire] top-level keys.

    Built from the union of fixed non-plugin keys and the registered plugin
    names (each plugin may have a [tool.tripwire.<name>] sub-table). The
    registry is the single source of truth — never hardcode the plugin list.
    """
    from tripwire._registry import VALID_PLUGIN_NAMES  # noqa: PLC0415

    return _TOP_LEVEL_NON_PLUGIN_KEYS | VALID_PLUGIN_NAMES


def _format_suggestion(unknown: str, candidates: frozenset[str]) -> str:
    """Format a 'did you mean' hint via difflib.get_close_matches.

    Returns an empty string when difflib finds no close matches. Uses
    difflib's default cutoff (0.6).
    """
    matches = difflib.get_close_matches(unknown, sorted(candidates), n=3)
    if not matches:
        return ""
    if len(matches) == 1:
        return f" (did you mean: {matches[0]}?)"
    return f" (did you mean: {', '.join(matches)}?)"


# Legacy keys removed in 0.20.0 that need a tailored migration message
# instead of the generic "unknown key" + difflib suggestion. Handled by
# downstream code (e.g., pytest_plugin.py for ``guard_allow``); skipped
# here so the specific message wins.
_LEGACY_MIGRATED_KEYS: Final[frozenset[str]] = frozenset({"guard_allow"})


def validate_top_level_schema(config: Mapping[str, Any]) -> None:
    """Validate the top-level [tool.tripwire] table against the closed schema.

    Raises :class:`TripwireConfigError` for any unknown key. The allowed-key
    set is the union of the fixed non-plugin keys (``guard``, ``firewall``,
    ``enabled_plugins``, ``disabled_plugins``) and every plugin name from
    ``PLUGIN_REGISTRY``. Unknown keys produce ``difflib.get_close_matches``
    typo suggestions when a close candidate exists.

    This validator does NOT validate the contents of each sub-table — that
    is each plugin's ``load_config`` responsibility. It only enforces that
    the top-level keys themselves are recognised. Legacy keys with their
    own migration message (see ``_LEGACY_MIGRATED_KEYS``) are skipped so
    downstream code can emit the tailored message.
    """
    from tripwire._errors import TripwireConfigError  # noqa: PLC0415

    allowed = _allowed_top_level_keys()
    for key in config:
        if key in allowed or key in _LEGACY_MIGRATED_KEYS:
            continue
        suggestion = _format_suggestion(key, allowed)
        raise TripwireConfigError(
            f"Unknown key {key!r} in [tool.tripwire]{suggestion or '.'}"
        )


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
        from tripwire._registry import VALID_PLUGIN_NAMES  # noqa: PLC0415

        overrides: dict[str, str] = {}
        for key, value in raw.items():
            if key == "default":
                continue
            # C7: every override key must match a registered plugin name.
            if key not in VALID_PLUGIN_NAMES:
                suggestion = _format_suggestion(key, VALID_PLUGIN_NAMES)
                raise TripwireConfigError(
                    f"Unknown protocol {key!r} in [tool.tripwire.guard]"
                    f"{suggestion or '.'}"
                )
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
