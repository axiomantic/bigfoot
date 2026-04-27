"""C6 integration tests: @pytest.mark.guard per-test override.

Verifies that the `guard` marker overrides the project's resolved guard
levels for the marked test only. Uses pytester subprocesses to isolate
project config from each scenario; tripwire's `pytest_unconfigure`
unconditionally tears down global context propagation, so an in-process
pytester would corrupt the parent session.
"""

from __future__ import annotations

import textwrap

import pytest

pytest_plugins = ["pytester"]


@pytest.mark.allow("subprocess")
def test_marker_string_form(pytester: pytest.Pytester) -> None:
    """C6-T1: `@pytest.mark.guard("error")` raises on unmocked call when project default is "warn".

    ESCAPE: test_marker_string_form
      CLAIM: The string form override escalates the test from project
             default "warn" to "error", raising GuardedCallError.
      PATH:  pytest_runtest_call -> iter_markers("guard") -> string arg
             -> GuardLevels(default="error", overrides={}) -> _guard_levels.set(...)
             -> subprocess.run intercepted -> get_verifier_or_raise -> raise.
      CHECK: Inner test passes because pytest.raises(GuardedCallError) matches.
      MUTATION: If the marker is ignored (no override applied), the project
                default "warn" would emit only a warning and the call would
                not raise; pytest.raises would fail and outcomes would be
                failed=1 instead of passed=1.
      ESCAPE: If the marker is read but the levels token is never set, the
              ContextVar default applies; with project default "warn", the
              call would warn rather than raise.
    """
    pytester.makepyprojecttoml(
        textwrap.dedent(
            """
            [project]
            name = "client"
            version = "0.0.0"

            [tool.tripwire]
            guard = "warn"
            """
        )
    )
    pytester.makepyfile(
        test_string_form=textwrap.dedent(
            """
            import subprocess

            import pytest

            from tripwire import GuardedCallError


            @pytest.mark.guard("error")
            def test_strict():
                with pytest.raises(GuardedCallError):
                    subprocess.run(["true"])
            """
        )
    )
    result = pytester.runpytest_subprocess("-q")
    result.assert_outcomes(passed=1)


@pytest.mark.allow("subprocess")
def test_marker_warn_form(pytester: pytest.Pytester) -> None:
    """C6-T2: `@pytest.mark.guard("warn")` warns instead of raising when project default is "error".

    Under guard="warn" the dispatch enters the warn branch instead of
    the error branch. For an unsafe plugin (subprocess) this surfaces
    as `UnsafePassthroughError` (the warn-branch gate for unsafe
    plugins), not `GuardedCallError` (the error-branch behavior). The
    branch flip is the observable signal.

    ESCAPE: test_marker_warn_form
      CLAIM: The string form override demotes dispatch from the error
             branch to the warn branch; observable as
             UnsafePassthroughError instead of GuardedCallError.
      PATH:  pytest_runtest_call -> iter_markers("guard") -> string arg
             -> GuardLevels(default="warn", overrides={}) -> _guard_levels.set(...)
             -> subprocess.run intercepted -> warn-branch unsafe gate.
      CHECK: Inner test asserts UnsafePassthroughError is raised (NOT
             GuardedCallError); the type difference is what proves the
             branch flipped.
      MUTATION: If the marker is ignored, project default "error" would
                raise GuardedCallError and pytest.raises(UnsafePassthroughError)
                would fail with the wrong exception type.
      ESCAPE: A bug that always raises UnsafePassthroughError regardless
              of level would pass this test in isolation but fail T1
              (which expects GuardedCallError under guard="error").
    """
    pytester.makepyprojecttoml(
        textwrap.dedent(
            """
            [project]
            name = "client"
            version = "0.0.0"

            [tool.tripwire]
            guard = "error"
            """
        )
    )
    pytester.makepyfile(
        test_warn_form=textwrap.dedent(
            """
            import subprocess

            import pytest

            from tripwire._errors import UnsafePassthroughError


            @pytest.mark.guard("warn")
            def test_lenient():
                with pytest.raises(UnsafePassthroughError):
                    subprocess.run(["true"])
            """
        )
    )
    result = pytester.runpytest_subprocess("-q")
    result.assert_outcomes(passed=1)


@pytest.mark.allow("subprocess")
def test_marker_off_form(pytester: pytest.Pytester) -> None:
    """C6-T3: `@pytest.mark.guard("off")` disables guard for the test.

    ESCAPE: test_marker_off_form
      CLAIM: The "off" form disables guard entirely for the marked test;
             the unmocked call neither raises nor warns.
      PATH:  pytest_runtest_call -> iter_markers("guard") -> "off"
             -> GuardLevels(default="off", overrides={}) -> dispatch
             returns GuardPassThrough -> intercept passes through.
      CHECK: Inner test asserts no GuardedCallWarning was emitted and
             the call did not raise.
      MUTATION: If the marker is ignored, project default "error" would
                raise and the inner test would fail.
      ESCAPE: A bug where "off" still warns but does not raise would be
              caught by the warning-empty assertion.
    """
    pytester.makepyprojecttoml(
        textwrap.dedent(
            """
            [project]
            name = "client"
            version = "0.0.0"

            [tool.tripwire]
            guard = "error"
            """
        )
    )
    pytester.makepyfile(
        test_off_form=textwrap.dedent(
            """
            import subprocess
            import warnings

            import pytest

            from tripwire import GuardedCallError, GuardedCallWarning


            @pytest.mark.guard("off")
            def test_no_guard():
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    try:
                        subprocess.run(["true"])
                    except GuardedCallError:
                        raise AssertionError("guard('off') must not raise")
                guard_warnings = [
                    w for w in caught if issubclass(w.category, GuardedCallWarning)
                ]
                assert guard_warnings == []
            """
        )
    )
    result = pytester.runpytest_subprocess("-q")
    result.assert_outcomes(passed=1)


@pytest.mark.allow("subprocess")
def test_marker_dict_form(pytester: pytest.Pytester) -> None:
    """C6-T4: `@pytest.mark.guard({"default": "warn", "subprocess": "error"})` overrides per-protocol.

    Project default is "warn"; the marker dict escalates the
    `subprocess` protocol specifically to "error". This proves both the
    dict shape is parsed via `_resolve_guard_levels({"guard": arg})`
    AND the per-protocol override is honored at the per-test level.
    Without the override, the call would fall to the warn branch and
    raise UnsafePassthroughError instead of GuardedCallError.

    ESCAPE: test_marker_dict_form
      CLAIM: The dict form is parsed via `_resolve_guard_levels` and the
             per-protocol override escalates subprocess to "error" while
             the rest of the test stays at default "warn".
      PATH:  pytest_runtest_call -> iter_markers("guard") -> dict arg
             -> _resolve_guard_levels({"guard": {...}}) -> GuardLevels with
             overrides={"subprocess": "error"} -> dispatch reads
             override -> error branch -> GuardedCallError.
      CHECK: Inner test asserts GuardedCallError is raised (the
             error-branch behavior); UnsafePassthroughError would not
             match (that's the warn-branch behavior).
      MUTATION: If the dict form is treated as a string, the call to
                `_resolve_guard_levels` would raise TripwireConfigError
                and the test would fail with that exception. If
                overrides dict is dropped, subprocess inherits default
                "warn" and the call raises UnsafePassthroughError, not
                GuardedCallError.
      ESCAPE: A bug that always escalates regardless of marker arg
              would still pass this test but fail T2 (warn-form must
              NOT raise GuardedCallError).
    """
    pytester.makepyprojecttoml(
        textwrap.dedent(
            """
            [project]
            name = "client"
            version = "0.0.0"

            [tool.tripwire]
            guard = "warn"
            """
        )
    )
    pytester.makepyfile(
        test_dict_form=textwrap.dedent(
            """
            import subprocess

            import pytest

            from tripwire import GuardedCallError


            @pytest.mark.guard({"default": "warn", "subprocess": "error"})
            def test_per_protocol():
                with pytest.raises(GuardedCallError):
                    subprocess.run(["true"])
            """
        )
    )
    result = pytester.runpytest_subprocess("-q")
    result.assert_outcomes(passed=1)


@pytest.mark.allow("subprocess")
def test_marker_resets_after_test(pytester: pytest.Pytester) -> None:
    """C6-T5: After a `guard("off")` test, the next test sees the project default.

    ESCAPE: test_marker_resets_after_test
      CLAIM: The marker override is scoped to the marked test's lifetime;
             the next test in the same session sees the project default.
      PATH:  pytest_runtest_call sets levels_token, yield, reset on the
             "off" test -> next test enters the hookwrapper fresh ->
             re-resolves project levels -> default "error" applies.
      CHECK: Inner test_first (off) does not raise; test_second (no marker)
             raises GuardedCallError under project default "error".
      MUTATION: If the reset is omitted, the "off" override would persist
                via the ContextVar default and test_second would not raise.
      ESCAPE: A bug that sets the override on a module-level variable
              instead of via ContextVar would leak across tests.
    """
    pytester.makepyprojecttoml(
        textwrap.dedent(
            """
            [project]
            name = "client"
            version = "0.0.0"

            [tool.tripwire]
            guard = "error"
            """
        )
    )
    pytester.makepyfile(
        test_reset=textwrap.dedent(
            """
            import subprocess

            import pytest

            from tripwire import GuardedCallError


            @pytest.mark.guard("off")
            def test_first():
                # off override -> no raise.
                subprocess.run(["true"])


            def test_second():
                # No marker -> project default "error" -> must raise.
                with pytest.raises(GuardedCallError):
                    subprocess.run(["true"])
            """
        )
    )
    result = pytester.runpytest_subprocess("-q")
    result.assert_outcomes(passed=2)
