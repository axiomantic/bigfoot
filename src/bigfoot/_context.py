"""Module-level ContextVars for bigfoot.

Import this module first to avoid circular imports. It has no dependencies
on other bigfoot modules at import time (only deferred imports in functions).
"""

from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bigfoot._verifier import StrictVerifier

# ---------------------------------------------------------------------------
# Module-level ContextVars
# ---------------------------------------------------------------------------

_active_verifier: contextvars.ContextVar[StrictVerifier | None] = contextvars.ContextVar(
    "bigfoot_active_verifier", default=None
)

_any_order_depth: contextvars.ContextVar[int] = contextvars.ContextVar(
    "bigfoot_any_order_depth", default=0
)

_current_test_verifier: contextvars.ContextVar[StrictVerifier | None] = contextvars.ContextVar(
    "bigfoot_current_test_verifier", default=None
)

_guard_active: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "bigfoot_guard_active", default=False
)

_guard_allowlist: contextvars.ContextVar[frozenset[str]] = contextvars.ContextVar(
    "bigfoot_guard_allowlist", default=frozenset()
)


class _GuardPassThrough(BaseException):
    """Internal sentinel: interceptor should call the original function.

    Inherits from BaseException (not Exception) so generic except clauses
    in user code do not accidentally swallow it. Only interceptors should
    catch this.
    """


# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------


def get_active_verifier() -> StrictVerifier | None:
    """Return the currently active verifier, or None if no sandbox is active."""
    return _active_verifier.get()


def _get_verifier_or_raise(source_id: str) -> StrictVerifier:
    """Return the active verifier, or handle guard mode, or raise SandboxNotActiveError.

    Called by interceptors when they fire. Decision tree:
    1. _active_verifier set: return verifier (sandbox mode, existing behavior)
    2. _guard_active True: check allowlist, raise _GuardPassThrough if allowed,
       raise GuardedCallError if not
    3. Neither: raise SandboxNotActiveError (existing behavior)
    """
    verifier = _active_verifier.get()
    if verifier is not None:
        return verifier
    # No sandbox active
    if _guard_active.get():
        _check_guard_allowlist(source_id)
        # Allowed: caller must invoke original function
        raise _GuardPassThrough()
    from bigfoot._errors import SandboxNotActiveError  # noqa: PLC0415

    raise SandboxNotActiveError(source_id=source_id)


def _check_guard_allowlist(source_id: str) -> None:
    """Check if the plugin identified by source_id is in the guard allowlist.

    Extracts the plugin name as the prefix before the first colon.
    Raises GuardedCallError if the plugin is not allowed.
    """
    from bigfoot._errors import GuardedCallError  # noqa: PLC0415

    plugin_name = source_id.split(":")[0]
    allowlist = _guard_allowlist.get()
    if plugin_name not in allowlist:
        raise GuardedCallError(source_id=source_id, plugin_name=plugin_name)


def _get_test_verifier_or_raise() -> StrictVerifier:
    """Return the current test verifier, or raise NoActiveVerifierError.

    Called by module-level API functions (mock, sandbox, assert_interaction, etc.)
    when no test verifier is active.
    """
    from bigfoot._errors import NoActiveVerifierError

    verifier = _current_test_verifier.get()
    if verifier is None:
        raise NoActiveVerifierError()
    return verifier


def is_in_any_order() -> bool:
    """Return True if the current context is inside an in_any_order() block."""
    return _any_order_depth.get() > 0
