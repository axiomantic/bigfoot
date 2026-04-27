"""C9: tripwire.allow / tripwire.deny / tripwire.restrict raise outside sandbox.

When called with no active sandbox (no `with tripwire:` and no marker /
fixture path that sets `_active_verifier`), these context managers used to
silently push a frame onto `_firewall_stack` and pop it on exit, which made
the rule a no-op. Now they raise a `TripwireError` whose message points the
user at `[tool.tripwire.firewall]` for module-scoped rules.

The check fires INSIDE the generator body BEFORE `_firewall_stack.set(...)`,
so the error is raised on `__enter__`. The check uses
`_active_verifier.get() is not None` ONLY (not `_guard_active.get()`), which
preserves the documented behavior of allowing `tripwire.allow(...)` inside
guard mode (the marker / fixture path that sets `_active_verifier` keeps
working).

The same check applies to `deny` for symmetry: its rule frame is equally
meaningless without an active sandbox or guard context.
"""

from __future__ import annotations

import pytest

import tripwire
from tripwire._errors import TripwireError
from tripwire._firewall import _firewall_stack
from tripwire._guard import restrict as _restrict


def test_allow_outside_sandbox_raises() -> None:
    """C9-T1: `tripwire.allow("dns")` outside any sandbox raises
    TripwireError whose message references `[tool.tripwire.firewall]`.
    """
    with pytest.raises(TripwireError) as exc_info:
        with tripwire.allow("dns"):
            pass

    expected_message = (
        "tripwire.allow(...) was called outside any active sandbox. "
        "For module-scoped firewall rules, use [tool.tripwire.firewall] in pyproject.toml."
    )
    assert str(exc_info.value) == expected_message


def test_restrict_outside_sandbox_raises() -> None:
    """C9-T2: `tripwire.restrict(...)` outside any sandbox raises
    TripwireError whose message references `[tool.tripwire.firewall]`.
    """
    with pytest.raises(TripwireError) as exc_info:
        with _restrict("dns"):
            pass

    expected_message = (
        "tripwire.restrict(...) was called outside any active sandbox. "
        "For module-scoped firewall rules, use [tool.tripwire.firewall] in pyproject.toml."
    )
    assert str(exc_info.value) == expected_message


def test_deny_outside_sandbox_raises() -> None:
    """C9 (symmetry): `tripwire.deny(...)` outside any sandbox raises
    TripwireError whose message references `[tool.tripwire.firewall]`.

    Although the I-3 finding only enumerates `allow` and `restrict`, the
    same check applies to `deny` for consistency. Its rule frame is
    equally meaningless without an active sandbox or guard context.
    """
    with pytest.raises(TripwireError) as exc_info:
        with tripwire.deny("dns"):
            pass

    expected_message = (
        "tripwire.deny(...) was called outside any active sandbox. "
        "For module-scoped firewall rules, use [tool.tripwire.firewall] in pyproject.toml."
    )
    assert str(exc_info.value) == expected_message


def test_allow_inside_sandbox_works() -> None:
    """C9-T3: Sanity check: `with tripwire: tripwire.allow("dns")` does
    not raise. The sandbox sets `_active_verifier`, so the C9 check
    passes and the existing allow body runs normally.
    """
    entered_body = False
    with tripwire.sandbox():
        with tripwire.allow("dns"):
            entered_body = True
    assert entered_body is True


def test_allow_raises_on_enter_not_exit() -> None:
    """C9-T4: `with tripwire.allow("dns"): pass` raises TripwireError on
    __enter__, not on __exit__. The `pass` body never executes.

    If the C9 check were accidentally moved AFTER `_firewall_stack.set(...)`
    (or the body raised instead of __enter__), this test would catch it.
    """
    body_executed = False

    with pytest.raises(TripwireError):
        with tripwire.allow("dns"):
            body_executed = True

    assert body_executed is False


def test_allow_failed_enter_leaves_firewall_stack_unchanged() -> None:
    """C9-T4 companion: after a failed `__enter__`, `_firewall_stack.get()`
    is unchanged. Confirms the check fires BEFORE `_firewall_stack.set(...)`,
    so no stale frame is left on the stack when the error raises.
    """
    stack_before = _firewall_stack.get()
    with pytest.raises(TripwireError):
        with tripwire.allow("dns"):
            pass
    stack_after = _firewall_stack.get()
    assert stack_after is stack_before
