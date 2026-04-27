"""Prototype validation script for the frame-walking approach (PRE-C5 GATE).

This script validates that `walk_to_user_frame()` correctly identifies the
USER call site (the line in this script that issued the call) when invoked
from inside a wrapper around 5 representative call sites:

    1. subprocess.run            (C-extension stdlib)
    2. socket.socket().connect   (C-extension stdlib)
    3. httpx.get                 (pure-Python wrapper; skip if not installed)
    4. aiohttp request           (asyncio internals; skip if not installed)
    5. psycopg2.connect          (C-extension binding; skip if not installed)

For each call site, the wrapper installs itself by monkey-patching the target
function. From inside the wrapper, `walk_to_user_frame()` is invoked and the
captured (filename, lineno) is recorded. PASS = the captured frame is THIS
script's filename and the line number is the line where the call originated.
FAIL = the captured frame is tripwire-internal, a stdlib internal frame, an
asyncio frame, or any other unrelated framework frame.

The walk_to_user_frame() implementation here is INLINE (not imported from
src/tripwire/) so that this script can be run before any production code
exists. It uses the algorithm specified in the design doc Section 7
lines 846-870: skip frames where module_name == "tripwire" or starts with
"tripwire.", return the first non-tripwire frame.

To simulate that this prototype's WRAPPER lives in tripwire-internal code,
we inject the wrapper into a synthetic module named "tripwire._proto_wrapper"
so that walk_to_user_frame's skip predicate has something to skip past.
Without this, the wrapper would be in __main__ (the script itself) and the
walk would trivially return the wrapper frame.
"""

from __future__ import annotations

import asyncio
import socket
import subprocess
import sys
import types
from types import FrameType


# ---------------------------------------------------------------------------
# Inline walk_to_user_frame() per design Section 7 lines 846-870.
# ---------------------------------------------------------------------------
def walk_to_user_frame() -> tuple[str, int, str] | None:
    frame: FrameType | None = sys._getframe(1)  # skip this function itself
    while frame is not None:
        module_name = frame.f_globals.get("__name__", "")
        if module_name != "tripwire" and not module_name.startswith("tripwire."):
            return (frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name)
        frame = frame.f_back
    return None


# ---------------------------------------------------------------------------
# Synthetic "tripwire._proto_wrapper" module: wrappers live here so that
# walk_to_user_frame() has tripwire-namespaced frames to skip past, mimicking
# the real plugin/proxy layout.
# ---------------------------------------------------------------------------
_wrapper_module = types.ModuleType("tripwire._proto_wrapper")
_wrapper_module.__name__ = "tripwire._proto_wrapper"
sys.modules["tripwire._proto_wrapper"] = _wrapper_module
# Also register a parent "tripwire" module so introspection is consistent.
if "tripwire" not in sys.modules:
    _tripwire_pkg = types.ModuleType("tripwire")
    _tripwire_pkg.__name__ = "tripwire"
    sys.modules["tripwire"] = _tripwire_pkg


def _make_wrapper(label: str, original_callable: object) -> object:
    """Construct a wrapper whose code object lives in tripwire._proto_wrapper."""
    src = (
        "def _wrapper(*args, **kwargs):\n"
        "    captured = walk_to_user_frame()\n"
        "    _captures[label] = captured\n"
        "    try:\n"
        "        return original_callable(*args, **kwargs)\n"
        "    except Exception as exc:\n"
        "        _exceptions[label] = exc\n"
        "        return None\n"
    )
    code = compile(src, "<tripwire._proto_wrapper>", "exec")
    namespace: dict = {
        "__name__": "tripwire._proto_wrapper",
        "walk_to_user_frame": walk_to_user_frame,
        "original_callable": original_callable,
        "_captures": _captures,
        "_exceptions": _exceptions,
        "label": label,
    }
    exec(code, namespace)
    wrapper = namespace["_wrapper"]
    # Force the function's globals to claim the tripwire module name so the
    # skip predicate fires on it.
    wrapper.__module__ = "tripwire._proto_wrapper"
    return wrapper


_captures: dict[str, tuple[str, int, str] | None] = {}
_exceptions: dict[str, BaseException] = {}


# ---------------------------------------------------------------------------
# Async wrapper variant: same pattern but `async def` for aiohttp.
# ---------------------------------------------------------------------------
def _make_async_wrapper(label: str, original_coro_callable: object) -> object:
    src = (
        "async def _wrapper(*args, **kwargs):\n"
        "    captured = walk_to_user_frame()\n"
        "    _captures[label] = captured\n"
        "    try:\n"
        "        return await original_coro_callable(*args, **kwargs)\n"
        "    except Exception as exc:\n"
        "        _exceptions[label] = exc\n"
        "        return None\n"
    )
    code = compile(src, "<tripwire._proto_wrapper>", "exec")
    namespace: dict = {
        "__name__": "tripwire._proto_wrapper",
        "walk_to_user_frame": walk_to_user_frame,
        "original_coro_callable": original_coro_callable,
        "_captures": _captures,
        "_exceptions": _exceptions,
        "label": label,
    }
    exec(code, namespace)
    wrapper = namespace["_wrapper"]
    wrapper.__module__ = "tripwire._proto_wrapper"
    return wrapper


# ---------------------------------------------------------------------------
# Exercise call sites. Each call site records the line number on which the
# call is issued so we can compare against the captured frame.
# ---------------------------------------------------------------------------
THIS_FILE = __file__


def exercise_subprocess_run() -> int:
    """Returns the line number on which the patched subprocess.run is called."""
    original = subprocess.run
    subprocess.run = _make_wrapper("subprocess.run", original)
    try:
        # The next non-blank line is the user call site.
        call_line = sys._getframe().f_lineno + 1
        subprocess.run(["/bin/true"])
    finally:
        subprocess.run = original
    return call_line


def exercise_socket_connect() -> int:
    """Returns the line number on which the patched socket.connect is called.

    socket.socket instances do not allow attribute assignment, so we patch
    socket.socket.connect at the class level. The wrapper accepts `self` as
    the first positional arg and forwards it to the original unbound method.
    """
    original = socket.socket.connect
    socket.socket.connect = _make_wrapper("socket.connect", original)
    s = socket.socket()
    try:
        try:
            call_line = sys._getframe().f_lineno + 1
            s.connect(("127.0.0.1", 9999))
        except ConnectionRefusedError:
            pass
        except OSError:
            pass
    finally:
        socket.socket.connect = original
        try:
            s.close()
        except Exception:
            pass
    return call_line


def exercise_httpx_get() -> int | None:
    try:
        import httpx
    except ImportError:
        return None
    original = httpx.get
    httpx.get = _make_wrapper("httpx.get", original)
    try:
        try:
            call_line = sys._getframe().f_lineno + 1
            httpx.get("https://127.0.0.1:1/")  # will fail fast, that's fine
        except Exception:
            pass
    finally:
        httpx.get = original
    return call_line


def exercise_aiohttp_get() -> int | None:
    try:
        import aiohttp
    except ImportError:
        return None

    # We patch ClientSession._request which is the funnel for all HTTP verbs.
    original = aiohttp.ClientSession._request
    aiohttp.ClientSession._request = _make_async_wrapper(
        "aiohttp.request", original
    )

    async def _runner() -> int:
        async with aiohttp.ClientSession() as session:
            try:
                call_line = sys._getframe().f_lineno + 1
                await session.get("http://127.0.0.1:1/")
            except Exception:
                pass
            return call_line

    try:
        return asyncio.run(_runner())
    finally:
        aiohttp.ClientSession._request = original


def exercise_psycopg2_connect() -> int | None:
    try:
        import psycopg2
    except ImportError:
        return None
    original = psycopg2.connect
    psycopg2.connect = _make_wrapper("psycopg2.connect", original)
    try:
        try:
            call_line = sys._getframe().f_lineno + 1
            psycopg2.connect("host=127.0.0.1 port=1 dbname=nope user=nope connect_timeout=1")
        except psycopg2.OperationalError:
            pass
        except Exception:
            pass
    finally:
        psycopg2.connect = original
    return call_line


# ---------------------------------------------------------------------------
# Main: run every site, compare captured frame to expected (file, line).
# ---------------------------------------------------------------------------
def main() -> int:
    sites: list[tuple[str, int | None]] = []

    sites.append(("subprocess.run", exercise_subprocess_run()))
    sites.append(("socket.connect", exercise_socket_connect()))
    sites.append(("httpx.get", exercise_httpx_get()))
    sites.append(("aiohttp.request", exercise_aiohttp_get()))
    sites.append(("psycopg2.connect", exercise_psycopg2_connect()))

    print("=" * 72)
    print("Prototype Frame-Walk Validation Report")
    print("=" * 72)
    print(f"Script file: {THIS_FILE}")
    print()

    overall_pass = True
    for label, expected_line in sites:
        if expected_line is None:
            print(f"[SKIP] {label}: dependency not installed")
            continue

        captured = _captures.get(label)
        if captured is None:
            print(f"[FAIL] {label}: walk_to_user_frame() returned None")
            overall_pass = False
            continue

        cap_file, cap_line, cap_func = captured
        same_file = cap_file == THIS_FILE
        same_line = cap_line == expected_line
        status = "PASS" if (same_file and same_line) else "FAIL"
        if status == "FAIL":
            overall_pass = False

        print(f"[{status}] {label}")
        print(f"        expected: {THIS_FILE}:{expected_line}")
        print(f"        captured: {cap_file}:{cap_line} (in {cap_func})")
        if label in _exceptions:
            exc = _exceptions[label]
            print(f"        (call raised: {type(exc).__name__})")

    print()
    print("=" * 72)
    print(f"OVERALL: {'PASS' if overall_pass else 'FAIL'}")
    print("=" * 72)
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
