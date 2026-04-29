"""C6 unit tests: @pytest.mark.guard marker registration.

Verifies that the `guard` marker is registered alongside the existing
`allow` and `deny` markers, so `pytest --markers` lists it.
"""

from __future__ import annotations

import textwrap

import pytest

pytest_plugins = ["pytester"]


@pytest.mark.allow("subprocess")
def test_marker_registered_in_configure(pytester: pytest.Pytester) -> None:
    """C6-T6: `pytest --markers` output contains `guard(...)`.

    The tripwire pytest plugin must register an unprefixed `guard` marker
    in `pytest_configure` via `addinivalue_line`. Run an inner pytest in
    a subprocess so tripwire's `pytest_unconfigure` does not tear down the
    parent session's global context propagation.

    ESCAPE: test_marker_registered_in_configure
      CLAIM: The `guard` marker is registered with the documented help text.
      PATH:  pytest_configure -> config.addinivalue_line("markers", "guard(...)")
             -> pytest collects markers -> `pytest --markers` lists it.
      CHECK: stdout contains the literal `@pytest.mark.guard(level_or_dict)`
             header AND the documented help text describing accepted shapes.
      MUTATION: If the addinivalue_line call is removed, the marker would
                not appear in `--markers` output and `assert "guard("` would
                fail. If the help string is mutated (wrong protocol shape
                description), the substring check on accepted args would fail.
      ESCAPE: A bug that registers the marker under a different name (e.g.,
              `tripwire_guard`) would fail the unprefixed-name assertion.
    """
    pytester.makepyprojecttoml('[project]\nname = "client"\nversion = "0.0.0"\n')
    pytester.makepyfile(
        test_noop=textwrap.dedent(
            """
            def test_noop():
                pass
            """
        )
    )
    result = pytester.runpytest_subprocess("--markers")
    stdout = "\n".join(result.outlines)
    assert "@pytest.mark.guard(level_or_dict)" in stdout
    assert "override guard level for this test" in stdout
    assert '"error", "warn", "off"' in stdout
