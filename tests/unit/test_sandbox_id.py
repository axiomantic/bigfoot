"""C4 unit tests: sandbox_id allocation, active-set tracking, and the
private `_sandbox_id` attribute on Interaction.

These tests guard the certainty contract: `_sandbox_id` is a PRIVATE
dataclass field on Interaction (declared with `field(default=None,
init=False, repr=False)`) and MUST NOT appear inside `interaction.details`.
"""

from __future__ import annotations

import dataclasses
import warnings

import pytest

from tripwire._timeline import Interaction
from tripwire._verifier import SandboxContext, StrictVerifier


@pytest.fixture(autouse=True)
def _suppress_direct_instantiation_warning() -> None:
    """Tests in this module construct StrictVerifier directly. Suppress the
    pytest-fixture-wanted warning the verifier emits in that case."""
    StrictVerifier._suppress_direct_warning = True
    try:
        yield
    finally:
        StrictVerifier._suppress_direct_warning = False


# ---------------------------------------------------------------------------
# C4-T1: counter is monotonic and unique per sandbox
# ---------------------------------------------------------------------------


def test_monotonic_unique_per_sandbox() -> None:
    """Two consecutive `with v.sandbox():` blocks have distinct, strictly
    increasing `sandbox_id` values."""
    from tripwire._verifier import _current_sandbox_id

    v = StrictVerifier()

    ctx_a = v.sandbox()
    with ctx_a:
        id_a = _current_sandbox_id.get()
    ctx_b = v.sandbox()
    with ctx_b:
        id_b = _current_sandbox_id.get()

    assert isinstance(id_a, int)
    assert isinstance(id_b, int)
    assert id_a < id_b
    assert ctx_a.sandbox_id == id_a
    assert ctx_b.sandbox_id == id_b


# ---------------------------------------------------------------------------
# C4-T2: certainty contract — _sandbox_id never appears in interaction.details
# ---------------------------------------------------------------------------


def test_sandbox_id_not_in_details() -> None:
    """Inside a sandbox, an interaction recorded by a plugin has
    `_sandbox_id` set to a non-None int but `interaction.details` keys do
    NOT contain `_sandbox_id` or `sandbox_id`. The Interaction dataclass
    field for `_sandbox_id` is declared with `init=False, repr=False`,
    matching the existing private-attribute convention shared by
    `_asserted` and `enforce`. This preserves the certainty contract per
    CLAUDE.md.
    """
    from tripwire._base_plugin import BasePlugin

    # 1. Verify the dataclass field declaration directly.
    fields_by_name = {f.name: f for f in dataclasses.fields(Interaction)}
    assert "_sandbox_id" in fields_by_name
    sid_field = fields_by_name["_sandbox_id"]
    assert sid_field.init is False
    assert sid_field.repr is False
    assert sid_field.default is None

    # 2. Construct an Interaction WITHOUT passing _sandbox_id. The dataclass
    # must accept this (init=False keeps the constructor signature clean
    # and backwards-compatible).
    class _NullPlugin(BasePlugin):
        passthrough_safe = True

        def matches(self, interaction, expected):  # type: ignore[no-untyped-def]
            return True

        def format_interaction(self, interaction):  # type: ignore[no-untyped-def]
            return "[Null]"

        def format_mock_hint(self, interaction):  # type: ignore[no-untyped-def]
            return ""

        def format_unmocked_hint(self, source_id, args, kwargs):  # type: ignore[no-untyped-def]
            return ""

        def format_assert_hint(self, interaction):  # type: ignore[no-untyped-def]
            return ""

        def get_unused_mocks(self):  # type: ignore[no-untyped-def]
            return []

        def format_unused_mock_hint(self, mock_config):  # type: ignore[no-untyped-def]
            return ""

    v = StrictVerifier()
    plugin = _NullPlugin(v)

    # Build an interaction with a real-world details dict.
    interaction = Interaction(
        source_id="test:thing",
        sequence=0,
        details={"foo": "bar", "n": 1},
        plugin=plugin,
    )

    # Drive plugin.record() inside an active sandbox so the stamp logic runs.
    # _NullPlugin intentionally does not override install_patches; suppress
    # the no-op warning from BasePlugin.activate so the test output stays
    # clean.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with v.sandbox():
            plugin.record(interaction)
            sid_observed = interaction._sandbox_id

    # The stamp must be a non-None int (we were inside a sandbox).
    assert isinstance(sid_observed, int)

    # The certainty contract: details must NOT contain _sandbox_id or
    # sandbox_id under any spelling.
    assert "_sandbox_id" not in interaction.details
    assert "sandbox_id" not in interaction.details

    # And the original details payload is untouched.
    assert interaction.details == {"foo": "bar", "n": 1}


# ---------------------------------------------------------------------------
# C4-T3: active-set tracking (LIFO add/remove for nested sandboxes)
# ---------------------------------------------------------------------------


def test_active_set_tracking() -> None:
    """SandboxContext._enter() adds the sandbox_id to
    `SandboxContext._active_sandbox_ids`; `_exit()` removes it. Nested
    sandboxes have both ids present, then both are removed in LIFO order."""
    v = StrictVerifier()

    # Snapshot the set so the test isolates from any leakage from earlier
    # tests in the same process.
    baseline = set(SandboxContext._active_sandbox_ids)

    outer_ctx = v.sandbox()
    with outer_ctx:
        outer_id = outer_ctx.sandbox_id
        assert outer_id is not None
        assert outer_id in SandboxContext._active_sandbox_ids
        assert SandboxContext._active_sandbox_ids - baseline == {outer_id}

        inner_ctx = v.sandbox()
        with inner_ctx:
            inner_id = inner_ctx.sandbox_id
            assert inner_id is not None
            assert inner_id != outer_id
            assert SandboxContext._active_sandbox_ids - baseline == {
                outer_id,
                inner_id,
            }

        # Inner exited; only outer remains.
        assert SandboxContext._active_sandbox_ids - baseline == {outer_id}

    # Outer exited; nothing extra remains.
    assert set(SandboxContext._active_sandbox_ids) == baseline
