"""C5-T4, C5-T5, C5-T9: walk_to_user_frame() unit tests.

Verifies the frame-walking algorithm:
- Walks past tripwire-internal frames (any frame whose ``__name__`` starts
  with ``"tripwire."``).
- Walks past frames whose ``__name__`` is exactly ``"tripwire"`` (the
  top-level proxy case in ``src/tripwire/__init__.py``).
- Returns None when no user frame exists.
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import patch

from tripwire._frames import walk_to_user_frame


def _call_via_synthetic_module(module_name: str) -> tuple[str, int, str] | None:
    """Invoke walk_to_user_frame() from inside a synthetic module so its frame
    is skipped by the predicate, returning the next frame up (this caller).

    Saves and restores any pre-existing entry in ``sys.modules[module_name]``
    so that registering a synthetic ``"tripwire"`` (or other live name) does
    not corrupt the live module cache for subsequent tests.
    """
    mod = types.ModuleType(module_name)
    code = (
        "def inner():\n"
        "    from tripwire._frames import walk_to_user_frame\n"
        "    return walk_to_user_frame()\n"
    )
    exec(code, mod.__dict__)
    saved = sys.modules.get(module_name)
    sys.modules[module_name] = mod
    try:
        return mod.inner()  # type: ignore[no-any-return]
    finally:
        if saved is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = saved


def test_walks_past_tripwire_frames() -> None:
    """C5-T4: from inside a synthetic ``tripwire.foo`` frame, returns a user
    frame (the test module helper), not the synthetic tripwire frame.

    The walker must skip the synthetic ``tripwire.synthetic_internal`` frame
    and return the next non-tripwire frame, which is ``_call_via_synthetic_module``
    in this test module.
    """
    result = _call_via_synthetic_module("tripwire.synthetic_internal")
    assert result is not None
    filename, lineno, funcname = result
    assert filename == __file__
    assert funcname == "_call_via_synthetic_module"


def test_skips_top_level_tripwire_proxy_frame() -> None:
    """C5-T9: synthetic frame whose ``__name__`` is exactly ``"tripwire"``
    (a proxy in ``src/tripwire/__init__.py``) MUST be skipped. Verifies the
    skip predicate is ``module_name == "tripwire" or module_name.startswith("tripwire.")``,
    not just ``startswith("tripwire.")`` which would leak the top-level frame.

    If the predicate were missing the equality clause, the synthetic
    ``"tripwire"`` frame would be returned as the user frame instead of the
    test module helper.
    """
    result = _call_via_synthetic_module("tripwire")
    assert result is not None
    filename, lineno, funcname = result
    assert filename == __file__
    assert funcname == "_call_via_synthetic_module"


def test_returns_none_when_no_user_frame() -> None:
    """C5-T5: when no user frame exists in the stack (every frame is a
    tripwire-internal frame), the walker returns None and the message would
    render ``<unknown call site>``.

    Simulated by constructing a synthetic chain of fake frame objects whose
    ``f_globals["__name__"]`` is always ``"tripwire.synthetic_internal"``,
    then patching ``sys._getframe`` to return the head of the chain. The
    walker's loop terminates when it reaches a frame whose ``f_back`` is
    ``None`` without finding any user frame.
    """

    class _FakeCode:
        co_filename = "/tripwire/synthetic.py"
        co_name = "synthetic_func"

    class _FakeFrame:
        def __init__(self, back: Any) -> None:
            self.f_back = back
            self.f_globals = {"__name__": "tripwire.synthetic_internal"}
            self.f_lineno = 1
            self.f_code = _FakeCode()

    # Build a 3-frame chain entirely inside tripwire-internal namespace,
    # terminated by None.
    f3 = _FakeFrame(back=None)
    f2 = _FakeFrame(back=f3)
    f1 = _FakeFrame(back=f2)

    with patch.object(sys, "_getframe", lambda depth=0: f1):
        result = walk_to_user_frame()

    assert result is None
