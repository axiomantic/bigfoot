"""C5-T6, C5-T7, C5-T8: live GuardedCallError message includes the user's
file:line for outside-sandbox calls hitting C-extension stdlib + pure-Python
wrappers. Asserts the frame walk identifies THIS test file and the line that
issued the call.

Each test uses guard='error' (the post-C1 default) and triggers the dispatch
path that constructs GuardedCallError via walk_to_user_frame().
"""

from __future__ import annotations

import sys

import pytest

from tripwire._config import GuardLevels
from tripwire._context import _guard_active, _guard_levels, get_verifier_or_raise
from tripwire._errors import GuardedCallError
from tripwire._firewall import FirewallStack, _firewall_stack
from tripwire._firewall_request import (
    NetworkFirewallRequest,
    SubprocessFirewallRequest,
)

pytestmark = pytest.mark.integration


def _enable_guard_error() -> tuple[object, object, object]:
    """Activate guard with default level 'error' for the duration of the test.

    Resets the firewall stack to empty so the project-level
    ``[tool.tripwire.firewall] allow = ["dns:*", "socket:*"]`` rules do not
    pre-allow these test calls (the empty stack returns DENY by default).

    Returns the ContextVar tokens so the caller can reset them. We avoid
    going through the pytest plugin path here because we want a direct,
    deterministic dispatch into ``get_verifier_or_raise`` regardless of
    project-level configuration.
    """
    levels = GuardLevels(default="error", overrides={})
    tok_levels = _guard_levels.set(levels)
    tok_active = _guard_active.set(True)
    tok_stack = _firewall_stack.set(FirewallStack())
    return tok_levels, tok_active, tok_stack


def _disable_guard(tokens: tuple[object, object, object]) -> None:
    tok_levels, tok_active, tok_stack = tokens
    _firewall_stack.reset(tok_stack)  # type: ignore[arg-type]
    _guard_active.reset(tok_active)  # type: ignore[arg-type]
    _guard_levels.reset(tok_levels)  # type: ignore[arg-type]


def test_message_for_subprocess_call() -> None:
    """C5-T6: an unmocked ``subprocess.run`` outside sandbox produces a
    GuardedCallError whose message identifies this test's file:line."""
    tokens = _enable_guard_error()
    try:
        with pytest.raises(GuardedCallError) as exc_info:
            expected_lineno = sys._getframe().f_lineno + 1
            get_verifier_or_raise(
                "subprocess:run",
                firewall_request=SubprocessFirewallRequest(
                    command="/bin/true",
                    binary="/bin/true",
                ),
            )
    finally:
        _disable_guard(tokens)

    msg = str(exc_info.value)
    assert f"at {__file__}:{expected_lineno}" in msg


def test_message_for_socket_connect() -> None:
    """C5-T7: an unmocked ``socket.connect`` outside sandbox produces a
    GuardedCallError whose message identifies this test's file:line."""
    tokens = _enable_guard_error()
    try:
        with pytest.raises(GuardedCallError) as exc_info:
            expected_lineno = sys._getframe().f_lineno + 1
            get_verifier_or_raise(
                "socket:connect",
                firewall_request=NetworkFirewallRequest(
                    protocol="socket",
                    host="example.com",
                    port=9999,
                ),
            )
    finally:
        _disable_guard(tokens)

    msg = str(exc_info.value)
    assert f"at {__file__}:{expected_lineno}" in msg


def test_message_for_httpx_get() -> None:
    """C5-T8: an unmocked HTTP-shaped call outside sandbox produces a
    GuardedCallError whose message identifies this test's file:line.

    Uses the live ``http`` plugin name (``http:request`` is the source_id
    HttpPlugin uses for httpx requests). Skipped if httpx is not installed
    so the plugin registration may not have run.
    """
    pytest.importorskip("httpx")

    from tripwire._firewall_request import HttpFirewallRequest

    tokens = _enable_guard_error()
    try:
        with pytest.raises(GuardedCallError) as exc_info:
            expected_lineno = sys._getframe().f_lineno + 1
            get_verifier_or_raise(
                "http:request",
                firewall_request=HttpFirewallRequest(
                    method="GET",
                    scheme="https",
                    host="example.com",
                    port=443,
                    path="/",
                ),
            )
    finally:
        _disable_guard(tokens)

    msg = str(exc_info.value)
    assert f"at {__file__}:{expected_lineno}" in msg
