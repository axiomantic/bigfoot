"""Test run_linter using bigfoot popen."""

import bigfoot

from .app import run_linter


def test_linter_clean():
    (bigfoot.popen
        .new_session()
        .expect("spawn",       returns=None)
        .expect("communicate", returns=(b"All checks passed.\n", b"", 0)))

    with bigfoot:
        rc, output = run_linter("src/")

    assert rc == 0
    assert output == "All checks passed.\n"

    bigfoot.popen.assert_spawn(command=["ruff", "check", "src/"], stdin=None)
    bigfoot.popen.assert_communicate(input=None)
