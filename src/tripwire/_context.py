"""Module-level ContextVars for tripwire.

Import this module first to avoid circular imports. It has no dependencies
on other tripwire modules at import time (only deferred imports in functions).
"""

from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING

from tripwire._config import GuardLevels

if TYPE_CHECKING:
    from tripwire._firewall_request import FirewallRequest
    from tripwire._verifier import StrictVerifier

# ---------------------------------------------------------------------------
# Module-level ContextVars
# ---------------------------------------------------------------------------

_active_verifier: contextvars.ContextVar[StrictVerifier | None] = contextvars.ContextVar(
    "tripwire_active_verifier", default=None
)

_any_order_depth: contextvars.ContextVar[int] = contextvars.ContextVar(
    "tripwire_any_order_depth", default=0
)

_current_test_verifier: contextvars.ContextVar[StrictVerifier | None] = contextvars.ContextVar(
    "tripwire_current_test_verifier", default=None
)

_guard_active: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "tripwire_guard_active", default=False
)

_guard_levels: contextvars.ContextVar[GuardLevels] = contextvars.ContextVar(
    "tripwire_guard_levels", default=GuardLevels(default="warn", overrides={})
)

_guard_patches_installed: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "tripwire_guard_patches_installed", default=False
)


class GuardPassThrough(BaseException):
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


def get_verifier_or_raise(
    source_id: str,
    firewall_request: FirewallRequest | None = None,
) -> StrictVerifier:
    """Return the active verifier, or handle guard mode, or raise.

    Decision tree:

    1. Sandbox active: return verifier.
    2. Guard active + firewall_request:
       a. ALLOW: raise GuardPassThrough.
       b. DENY + level "warn":
          - plugin.passthrough_safe is False: raise UnsafePassthroughError
            (real I/O would otherwise leak past 'warn').
          - otherwise: emit GuardedCallWarning and raise GuardPassThrough.
       c. DENY + level "error": raise GuardedCallError.
    3. Guard active + no firewall_request: raise GuardedCallError (fail-closed).
    4. Guard not active but patches installed: raise GuardPassThrough.
    5. Otherwise: raise SandboxNotActiveError.
    """
    plugin_name = source_id.split(":")[0]

    # === Branch 1: sandbox active ===
    verifier = _active_verifier.get()
    if verifier is not None:
        return verifier

    # Resolve the plugin class once. ``plugin_cls is None`` means the
    # source_id does not belong to a registered plugin (e.g., a test
    # exercising get_verifier_or_raise with an arbitrary name). Unknown
    # plugins skip every guard branch and fall through to
    # SandboxNotActiveError so they preserve the pre-C2 contract.
    from tripwire._registry import (  # noqa: PLC0415
        lookup_plugin_class_by_name,
    )
    plugin_cls = lookup_plugin_class_by_name(plugin_name)
    plugin_is_unsafe_passthrough = (
        plugin_cls is not None and plugin_cls.passthrough_safe is False
    )

    # === Branch 3: guard active ===
    if plugin_cls is not None and _guard_active.get():
        if firewall_request is not None:
            from tripwire._firewall import Disposition, get_firewall_stack  # noqa: PLC0415

            disposition = get_firewall_stack().evaluate(firewall_request)

            # === Branch 3a: ALLOW ===
            if disposition is Disposition.ALLOW:
                raise GuardPassThrough()

            # === Branch 3b: DENY ===
            # Per-protocol or default guard level (C3).
            guard_levels = _guard_levels.get()
            level = guard_levels.overrides.get(plugin_name, guard_levels.default)

            # === Branch 3b-off (C3) ===
            # Per-protocol "off" disables the firewall entirely for this
            # plugin: no warn, no error, no UnsafePassthroughError.
            # MUST run BEFORE the warn-unsafe check.
            if level == "off":
                raise GuardPassThrough()

            if level == "warn":
                # === Branch 3b-warn-unsafe ===
                # If the plugin's passthrough is NOT safe, raise rather
                # than warn-and-pass-through, so real I/O does not leak.
                if plugin_is_unsafe_passthrough:
                    from tripwire._errors import UnsafePassthroughError  # noqa: PLC0415

                    raise UnsafePassthroughError(
                        source_id=source_id,
                        plugin_name=plugin_name,
                    )

                # === Branch 3b-warn-safe ===
                import warnings  # noqa: PLC0415

                from tripwire._errors import GuardedCallWarning  # noqa: PLC0415

                warnings.warn(
                    f"{source_id!r} blocked by firewall. "
                    f"See GuardedCallError docs for fix options.",
                    GuardedCallWarning,
                    stacklevel=4,
                )
                raise GuardPassThrough()

            # === Branch 3b-error ===
            from tripwire._errors import GuardedCallError  # noqa: PLC0415

            raise GuardedCallError(
                source_id=source_id,
                plugin_name=plugin_name,
                firewall_request=firewall_request,
            )

        # === Branch 3c: guard active, no firewall_request ===
        # Fail-closed only for plugins whose passthrough is unsafe (real
        # I/O). Unknown plugins and passthrough_safe=True plugins fall
        # through to SandboxNotActiveError so their interceptor-level
        # error paths can run as before.
        if plugin_is_unsafe_passthrough:
            from tripwire._errors import GuardedCallError  # noqa: PLC0415

            raise GuardedCallError(
                source_id=source_id,
                plugin_name=plugin_name,
                firewall_request=None,
            )

    # === Branch 4: guard not active but patches installed ===
    # Only fires for known plugins; unknown source_ids fall through to
    # SandboxNotActiveError below.
    if plugin_cls is not None and _guard_patches_installed.get():
        raise GuardPassThrough()

    # === Branch 5: nothing active ===
    from tripwire._errors import SandboxNotActiveError  # noqa: PLC0415
    raise SandboxNotActiveError(source_id=source_id)



def _get_test_verifier_or_raise() -> StrictVerifier:
    """Return the current test verifier, or raise NoActiveVerifierError.

    Called by module-level API functions (mock, sandbox, assert_interaction, etc.)
    when no test verifier is active.
    """
    from tripwire._errors import NoActiveVerifierError

    verifier = _current_test_verifier.get()
    if verifier is None:
        raise NoActiveVerifierError()
    return verifier


def is_in_any_order() -> bool:
    """Return True if the current context is inside an in_any_order() block."""
    return _any_order_depth.get() > 0
