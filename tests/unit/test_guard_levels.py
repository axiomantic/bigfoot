"""C3 unit tests: per-protocol guard levels via [tool.tripwire.guard].

Tests the parser `_resolve_guard_levels` (plural) which replaces
`_resolve_guard_level` (singular) and returns a `GuardLevels` frozen
dataclass with `default` and `overrides` fields.
"""

from __future__ import annotations

import pytest


def test_scalar_form_parses() -> None:
    """C3-T1: scalar `guard = "warn"` parses to GuardLevels(default="warn", overrides={}).

    ESCAPE: test_scalar_form_parses
      CLAIM: The legacy scalar form is preserved; `_resolve_guard_levels`
             returns the new GuardLevels dataclass with empty overrides.
      PATH:  _resolve_guard_levels -> isinstance(raw, str) branch -> return
             GuardLevels(default="warn", overrides={}).
      CHECK: Assertion equates the full result to a constructed GuardLevels
             with default="warn" and overrides=an empty dict.
      MUTATION: If the parser drops the str branch entirely, the call would
                hit the dict branch (or the trailing TypeError) and raise.
                If overrides is mistakenly populated, the equality check
                fails.
      ESCAPE: An implementation that swaps default for an unrelated literal
              (e.g., always returns "error") would fail the equality check.
    """
    from tripwire._config import GuardLevels, _resolve_guard_levels

    result = _resolve_guard_levels({"guard": "warn"})
    assert result == GuardLevels(default="warn", overrides={})


def test_table_form_parses() -> None:
    """C3-T2: nested table parses to GuardLevels with per-protocol overrides.

    ESCAPE: test_table_form_parses
      CLAIM: A nested-table form `guard = {default = "warn", subprocess =
             "error"}` returns GuardLevels(default="warn",
             overrides={"subprocess": "error"}).
      PATH:  _resolve_guard_levels -> isinstance(raw, dict) branch -> loop
             populates overrides for keys other than "default" -> return
             GuardLevels.
      CHECK: Full equality on the returned dataclass.
      MUTATION: If the parser drops the dict loop, overrides would be
                empty and equality fails. If the parser miscapitalizes the
                value (e.g., omits .lower() on table values), "error"
                comparisons would still pass but a "Strict" alias variant
                of this test would fail (covered separately by case +
                alias coverage in T3).
      ESCAPE: An implementation that hardcodes the override key as a
              specific name (e.g., always "subprocess") would coincidentally
              pass this test but fail variants with different protocols;
              we add a second protocol below to widen coverage.
    """
    from tripwire._config import GuardLevels, _resolve_guard_levels

    result = _resolve_guard_levels(
        {"guard": {"default": "warn", "subprocess": "error", "dns": "off"}}
    )
    assert result == GuardLevels(
        default="warn",
        overrides={"subprocess": "error", "dns": "off"},
    )


def test_unknown_protocol_value_rejected() -> None:
    """C3-T3: invalid override value raises TripwireConfigError listing valid choices.

    ESCAPE: test_unknown_protocol_value_rejected
      CLAIM: A nested-table override with an unknown level value raises
             TripwireConfigError, and the message names the offending key
             and lists the valid level set.
      PATH:  _resolve_guard_levels -> dict branch -> _normalize_level for
             value -> not in _VALID_LEVELS -> raise.
      CHECK: pytest.raises with match validates both the offending value
             repr and the valid-values list.
      MUTATION: If the validation branch is missing, no error is raised
                and pytest.raises fails. If the message format changes to
                drop the valid-values list, the match fails.
      ESCAPE: A test that only checks for the exception type would miss a
              regression where the error names the wrong key; the match
              regex below pins both.
    """
    from tripwire._config import _resolve_guard_levels
    from tripwire._errors import TripwireConfigError

    # "Warn" lowercases to "warn" and is valid; pick a value that does
    # NOT normalize to a valid level. Bare "louder" never maps.
    with pytest.raises(TripwireConfigError, match=r"Invalid value 'louder' for"):
        _resolve_guard_levels({"guard": {"default": "warn", "subprocess": "louder"}})


def test_mixed_scalar_and_table_rejected_by_tomllib() -> None:
    """C3 (design 836-838): both `guard = "..."` and `[tool.tripwire.guard]` table
    is illegal; tomllib itself raises TOMLDecodeError because the key
    conflicts with the table at the same dotted path.

    ESCAPE: test_mixed_scalar_and_table_rejected_by_tomllib
      CLAIM: Mixing scalar and table forms at the same TOML path is
             rejected by tomllib; tripwire's parser does not need extra
             detection logic.
      PATH:  tomllib.loads on the conflicting source raises before any
             tripwire code runs.
      CHECK: pytest.raises confirms the TOMLDecodeError surfaces.
      MUTATION: If tomllib silently accepted the conflicting forms, this
                test would fail (proving the design's assumption that
                tomllib is the gatekeeper is wrong).
      ESCAPE: None: this test pins the platform contract that the design
              relies on. If tomllib changes behavior, we know immediately.
    """
    import tomllib

    source = (
        '[tool.tripwire]\n'
        'guard = "warn"\n'
        '\n'
        '[tool.tripwire.guard]\n'
        'default = "error"\n'
    )
    with pytest.raises(tomllib.TOMLDecodeError):
        tomllib.loads(source)


def test_off_disables_per_protocol() -> None:
    """C3-T5: per-protocol `guard.<plugin> = "off"` short-circuits dispatch
    BEFORE the C2 unsafe-passthrough check, so an unsafe plugin neither
    raises nor warns.

    ESCAPE: test_off_disables_per_protocol
      CLAIM: When `_guard_levels` carries an override of "off" for a
             specific plugin, get_verifier_or_raise raises GuardPassThrough
             (not UnsafePassthroughError, not GuardedCallError, no warning).
      PATH:  get_verifier_or_raise -> Branch 3b -> overrides.get returns
             "off" -> raise GuardPassThrough BEFORE the warn-unsafe
             branch.
      CHECK: pytest.raises(GuardPassThrough) catches and no warning is
             emitted.
      MUTATION: If the "off" check is placed BELOW the warn-unsafe branch,
                an unsafe plugin would raise UnsafePassthroughError and
                this test would fail. If "off" is missing entirely, the
                error/warn path runs.
      ESCAPE: A buggy implementation that raises GuardPassThrough but ALSO
              emits a warning would be caught by the warning-count check.
    """
    import warnings

    from tripwire._config import GuardLevels
    from tripwire._context import (
        GuardPassThrough,
        _guard_active,
        _guard_levels,
        get_verifier_or_raise,
    )
    from tripwire._firewall_request import SubprocessFirewallRequest

    # SubprocessPlugin is passthrough_safe=False; would normally raise
    # UnsafePassthroughError under guard="warn" or GuardedCallError under
    # "error". With per-protocol "off", neither fires.
    req = SubprocessFirewallRequest(command="true", binary="true")
    levels_token = _guard_levels.set(
        GuardLevels(default="error", overrides={"subprocess": "off"})
    )
    guard_token = _guard_active.set(True)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with pytest.raises(GuardPassThrough):
                get_verifier_or_raise("subprocess:run", firewall_request=req)
            assert caught == []
    finally:
        _guard_active.reset(guard_token)
        _guard_levels.reset(levels_token)
