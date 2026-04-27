"""C4 integration tests: PostSandboxInteractionError dispatch.

These tests verify the new dispatch branch in `get_verifier_or_raise`:
when the current execution context still carries a `_current_sandbox_id`
ContextVar value but that sandbox has already exited, the call raises
`PostSandboxInteractionError` (distinct from `SandboxNotActiveError` and
from `GuardedCallError`).

Tests use the public dispatch entry point directly to avoid coupling to
any specific plugin's interceptor.
"""

from __future__ import annotations

import asyncio

import pytest

from tripwire._context import (
    _guard_active,
    _guard_patches_installed,
    get_verifier_or_raise,
)
from tripwire._errors import (
    PostSandboxInteractionError,
    SandboxNotActiveError,
)
from tripwire._verifier import StrictVerifier

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _suppress_direct_warning() -> None:
    StrictVerifier._suppress_direct_warning = True
    try:
        yield
    finally:
        StrictVerifier._suppress_direct_warning = False


@pytest.fixture(autouse=True)
def _disable_guard() -> None:
    """These tests verify the post-sandbox dispatch branch in isolation
    from guard mode. Disable guard so a fall-through hits Branch 5
    (SandboxNotActiveError) rather than Branch 3 (GuardedCallError)."""
    g_token = _guard_active.set(False)
    p_token = _guard_patches_installed.set(False)
    try:
        yield
    finally:
        _guard_patches_installed.reset(p_token)
        _guard_active.reset(g_token)


# ---------------------------------------------------------------------------
# C4-T4: asyncio task that survives sandbox exit raises PostSandboxInteractionError
# ---------------------------------------------------------------------------


def test_async_task_after_exit_raises_post_sandbox() -> None:
    """A task scheduled inside `with v.sandbox():` whose body fires an
    intercepted dispatch AFTER the sandbox has exited raises
    `PostSandboxInteractionError` (NOT `SandboxNotActiveError`,
    NOT `GuardedCallError`)."""

    async def main() -> BaseException | None:
        v = StrictVerifier()
        captured: list[BaseException] = []
        ready = asyncio.Event()
        gate = asyncio.Event()

        async def late_caller() -> None:
            ready.set()
            await gate.wait()
            try:
                get_verifier_or_raise(source_id="test:late_call")
            except BaseException as exc:  # noqa: BLE001
                captured.append(exc)

        async with v.sandbox():
            task = asyncio.create_task(late_caller())
            # Wait until the task is parked at gate.wait() so we know
            # ContextVar capture happened with the sandbox active.
            await ready.wait()

        # Sandbox is now exited. Release the task; its dispatch call
        # MUST raise PostSandboxInteractionError.
        gate.set()
        await task

        return captured[0] if captured else None

    err = asyncio.run(main())
    assert isinstance(err, PostSandboxInteractionError), (
        f"Expected PostSandboxInteractionError, got {type(err).__name__}: {err!r}"
    )
    assert err.source_id == "test:late_call"
    assert isinstance(err.sandbox_id, int)


# ---------------------------------------------------------------------------
# C4-T5: dispatch outside of any sandbox still raises the leaked-interaction error
# ---------------------------------------------------------------------------


def test_call_without_any_sandbox_raises_leaked() -> None:
    """A direct dispatch outside any sandbox (no ContextVar value carried)
    raises `SandboxNotActiveError`, NOT `PostSandboxInteractionError`.
    This guards against the new branch firing when no sandbox was ever
    entered in the current context."""
    with pytest.raises(SandboxNotActiveError) as exc_info:
        get_verifier_or_raise(source_id="test:never_sandboxed")
    assert exc_info.value.source_id == "test:never_sandboxed"


# ---------------------------------------------------------------------------
# C4-T6: PostSandboxInteractionError message includes sandbox_id and pedagogy
# ---------------------------------------------------------------------------


def test_post_sandbox_message_includes_sandbox_id() -> None:
    """The error message must include the offending sandbox_id and a hint
    about awaiting/cancelling tasks before sandbox exit."""

    async def main() -> BaseException:
        v = StrictVerifier()
        captured: list[BaseException] = []
        ready = asyncio.Event()
        gate = asyncio.Event()

        async def late_caller() -> None:
            ready.set()
            await gate.wait()
            try:
                get_verifier_or_raise(source_id="test:late_msg")
            except BaseException as exc:  # noqa: BLE001
                captured.append(exc)

        async with v.sandbox():
            task = asyncio.create_task(late_caller())
            await ready.wait()

        gate.set()
        await task
        return captured[0]

    err = asyncio.run(main())
    assert isinstance(err, PostSandboxInteractionError)
    msg = str(err)
    assert f"sandbox #{err.sandbox_id}" in msg
    assert "test:late_msg" in msg
    # Pedagogical content: must hint at awaiting/cancelling tasks before
    # sandbox exit, and at wrapping intentional late calls in their own
    # `with tripwire:` block.
    assert "Await or cancel all pending tasks before exiting the sandbox." in msg
    assert "asyncio.gather" in msg
    assert "with tripwire:" in msg


# ---------------------------------------------------------------------------
# C4-T7: nested sandbox — task spawned inside inner survives both exits;
# carries OUTER sandbox_id after inner exits but is detected as post-sandbox
# only after BOTH have exited. Per design Section 5: a task spawned inside
# the inner sandbox captures the inner id at creation time; after both
# exits the dispatch reports the inner id as the offending sandbox_id.
# ---------------------------------------------------------------------------


def test_nested_sandbox_task_survives_inner_exit() -> None:
    """Nested-sandbox handling. Outer enters, inner enters and spawns
    `asyncio.create_task(...)` whose body sleeps past the INNER exit but
    fires its dispatch only AFTER the OUTER also exits.

    The task captures `_current_sandbox_id` at create_task time (the
    INNER id). When it fires after both exits, dispatch sees that
    captured inner id is no longer in `SandboxContext._active_sandbox_ids`
    and raises `PostSandboxInteractionError` carrying the INNER id.

    This verifies the ContextVar token-save/reset pattern in
    _enter()/_exit(): if the inner _exit() failed to reset the ContextVar
    via the saved token, the outer sandbox id would not be restored
    correctly inside the outer scope, breaking nested correctness for any
    other code reading `_current_sandbox_id` between the inner exit and
    the outer exit.
    """
    from tripwire._verifier import _current_sandbox_id

    async def main() -> tuple[BaseException, int, int, int | None]:
        v = StrictVerifier()
        captured: list[BaseException] = []
        ready = asyncio.Event()
        gate = asyncio.Event()
        inner_id_holder: list[int] = []
        outer_id_holder: list[int] = []
        outer_after_inner_holder: list[int | None] = []

        async def late_caller() -> None:
            ready.set()
            await gate.wait()
            try:
                get_verifier_or_raise(source_id="test:nested_late")
            except BaseException as exc:  # noqa: BLE001
                captured.append(exc)

        outer_ctx = v.sandbox()
        async with outer_ctx:
            assert outer_ctx.sandbox_id is not None
            outer_id_holder.append(outer_ctx.sandbox_id)
            inner_ctx = v.sandbox()
            async with inner_ctx:
                assert inner_ctx.sandbox_id is not None
                inner_id_holder.append(inner_ctx.sandbox_id)
                task = asyncio.create_task(late_caller())
                await ready.wait()
            # Inner exited. The ContextVar token-reset must restore the
            # OUTER sandbox_id here (not None, not the inner id).
            outer_after_inner_holder.append(_current_sandbox_id.get())

        # Both sandboxes have exited. Release the task.
        gate.set()
        await task
        return (
            captured[0],
            inner_id_holder[0],
            outer_id_holder[0],
            outer_after_inner_holder[0],
        )

    err, inner_id, outer_id, outer_after_inner = asyncio.run(main())

    # Token-reset correctness: between inner exit and outer exit, the
    # ContextVar must hold the outer sandbox_id.
    assert outer_after_inner == outer_id

    # The task captured the INNER id at create_task time. After both
    # exits the dispatch reports it as the offending sandbox.
    assert isinstance(err, PostSandboxInteractionError)
    assert err.source_id == "test:nested_late"
    assert err.sandbox_id == inner_id
    assert err.sandbox_id != outer_id


# ---------------------------------------------------------------------------
# Sanity: GuardPassThrough is NOT raised for post-sandbox path (the new
# branch must run BEFORE Branch 4 / patches-installed fallthrough).
# ---------------------------------------------------------------------------


def test_post_sandbox_branch_runs_above_guard_branches() -> None:
    """If guard patches are installed (Branch 4) but the current context
    carries a since-exited sandbox_id, the post-sandbox branch must fire
    first and raise PostSandboxInteractionError, NOT raise GuardPassThrough."""

    async def main() -> BaseException | None:
        v = StrictVerifier()
        captured: list[BaseException] = []
        ready = asyncio.Event()
        gate = asyncio.Event()

        async def late_caller() -> None:
            # Patches "installed" only inside the task scope to mimic guard mode.
            patches_token = _guard_patches_installed.set(True)
            try:
                ready.set()
                await gate.wait()
                try:
                    get_verifier_or_raise(source_id="test:late_above_guard")
                except BaseException as exc:  # noqa: BLE001
                    captured.append(exc)
            finally:
                _guard_patches_installed.reset(patches_token)

        async with v.sandbox():
            task = asyncio.create_task(late_caller())
            await ready.wait()

        gate.set()
        await task
        return captured[0] if captured else None

    err = asyncio.run(main())
    assert isinstance(err, PostSandboxInteractionError), (
        f"Expected PostSandboxInteractionError, got {type(err).__name__}: {err!r}"
    )
