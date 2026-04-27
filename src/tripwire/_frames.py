"""Frame-walking utility for pedagogical error messages (Proposal 5 / C5).

Captures the user call site (file, lineno, function name) by walking the
Python call stack from this function's caller upward, skipping frames whose
``__module__`` is exactly ``"tripwire"`` or starts with ``"tripwire."``. The
former clause catches proxy functions defined directly in
``src/tripwire/__init__.py`` (whose ``__name__`` is exactly ``"tripwire"``);
the latter catches all submodules. Both clauses are required: dropping the
first would leak top-level proxy frames as the reported user call site.

Returns ``None`` when no user frame is found (e.g., called from a thread
spawned without any user frame in the stack). Callers must render this case
as ``"<unknown call site>"`` per Section 7 of the design doc.
"""

from __future__ import annotations

import sys
from types import FrameType


def walk_to_user_frame() -> tuple[str, int, str] | None:
    """Walk the call stack from this function's caller upward, skipping
    frames whose ``__module__`` is ``"tripwire"`` or starts with
    ``"tripwire."``, and return ``(filename, lineno, function_name)`` of the
    first user frame found.

    The skip predicate is
    ``module_name == "tripwire" or module_name.startswith("tripwire.")``,
    not just ``module_name.startswith("tripwire.")``: the former catches
    proxy functions defined directly in ``src/tripwire/__init__.py`` (whose
    ``__name__`` is exactly ``"tripwire"``); the latter alone would leak
    them. C5-T9 locks this in.

    Returns ``None`` if no user frame is found (e.g., called from a thread
    spawned without any user frame in the stack).
    """
    frame: FrameType | None = sys._getframe(1)  # skip this function itself
    while frame is not None:
        module_name = frame.f_globals.get("__name__", "")
        if module_name != "tripwire" and not module_name.startswith("tripwire."):
            return (frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name)
        frame = frame.f_back
    return None
