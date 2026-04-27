"""C2-T3, C2-T4: warn-mode behavior under the passthrough_safe gate.

When guard='warn' and a call would pass through, an UNSAFE plugin
(passthrough_safe=False) raises UnsafePassthroughError; a SAFE plugin
(passthrough_safe=True) emits the existing GuardedCallWarning and raises
GuardPassThrough so the original call proceeds.

These tests exercise the dispatch path inside get_verifier_or_raise
directly because the high-level subprocess integration goes through the
pytest plugin's session-scoped fixtures, which we do not want to
re-stage here.
"""

from __future__ import annotations

import warnings

import pytest

from tripwire._context import (
    GuardPassThrough,
    _guard_active,
    _guard_level,
    get_verifier_or_raise,
)
from tripwire._errors import GuardedCallWarning, UnsafePassthroughError
from tripwire._firewall_request import (
    NetworkFirewallRequest,
    SubprocessFirewallRequest,
)

pytestmark = pytest.mark.integration


def test_warn_with_unsafe_plugin_raises() -> None:
    """C2-T3: guard=warn + DENY + passthrough_safe=False plugin
    raises UnsafePassthroughError (NOT a warning + passthrough).

    ESCAPE: test_warn_with_unsafe_plugin_raises
      CLAIM: Under guard='warn', an unmocked subprocess.run call (the
             SubprocessPlugin is passthrough_safe=False) outside any
             sandbox and outside any allow() rule raises
             UnsafePassthroughError, never GuardPassThrough.
      PATH:  get_verifier_or_raise -> Branch 3b-warn-unsafe -> raise.
      CHECK: pytest.raises(UnsafePassthroughError) catches; the message
             names the plugin.
      MUTATION: If Branch 3b-warn-unsafe is missing, the call falls to the
                existing warn path and raises GuardPassThrough (not the
                unsafe error) - the pytest.raises would fail. If
                passthrough_safe is mistakenly True on SubprocessPlugin,
                the gate skips and the test fails the same way.
      ESCAPE: A bug that raises UnsafePassthroughError for the WRONG plugin
              name would still pass pytest.raises but fail the message
              check.
    """
    req = SubprocessFirewallRequest(command="true", binary="true")
    level_token = _guard_level.set("warn")
    guard_token = _guard_active.set(True)
    try:
        with pytest.raises(UnsafePassthroughError) as exc_info:
            get_verifier_or_raise("subprocess:run", firewall_request=req)
    finally:
        _guard_active.reset(guard_token)
        _guard_level.reset(level_token)

    err = exc_info.value
    assert err.plugin_name == "subprocess"
    assert err.source_id == "subprocess:run"
    assert "doesn't support outside-sandbox passthrough" in err.args[0]


def test_warn_with_safe_plugin_passthroughs() -> None:
    """C2-T4: guard=warn + DENY + passthrough_safe=True plugin
    emits GuardedCallWarning and raises GuardPassThrough (existing
    behavior preserved for safe plugins).

    Uses the 'crypto' plugin source_id - CryptoPlugin is
    passthrough_safe=True (it has no real I/O and its interceptors raise
    SandboxNotActiveError outside sandboxes, which is a safe failure
    mode rather than a real-world side effect).

    ESCAPE: test_warn_with_safe_plugin_passthroughs
      CLAIM: Under guard='warn', a safe-passthrough plugin still warns +
             passes through; the new gate must NOT over-restrict it.
      PATH:  get_verifier_or_raise -> Branch 3b-warn-unsafe (skipped because
             plugin.passthrough_safe is True) -> Branch 3b-warn-safe -> warn
             + raise GuardPassThrough.
      CHECK: pytest.raises(GuardPassThrough) catches AND a single
             GuardedCallWarning was emitted.
      MUTATION: If the gate over-fires on safe plugins, this test would see
                UnsafePassthroughError instead of GuardPassThrough.
      ESCAPE: A bug that no-ops the warn path entirely (no warning) would
                pass GuardPassThrough but fail the warning-count assert.
    """
    req = NetworkFirewallRequest(protocol="crypto", host="local", port=0)
    level_token = _guard_level.set("warn")
    guard_token = _guard_active.set(True)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with pytest.raises(GuardPassThrough):
                get_verifier_or_raise("crypto:sign", firewall_request=req)
            warning_msgs = [w for w in caught if issubclass(w.category, GuardedCallWarning)]
            assert len(warning_msgs) == 1
            assert "'crypto:sign'" in str(warning_msgs[0].message)
    finally:
        _guard_active.reset(guard_token)
        _guard_level.reset(level_token)
