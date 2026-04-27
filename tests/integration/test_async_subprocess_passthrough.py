"""C2-T5, C2-T6: async_subprocess passthrough returns the real
asyncio.subprocess.Process when guard ALLOW lets the call through.

The runtime always returned a real Process; the prior `cast(_AsyncFakeProcess,
...)` annotation lied about it. These tests pin the post-fix runtime story
so a future refactor cannot regress it.
"""

from __future__ import annotations

import asyncio
import shutil

import pytest

pytestmark = pytest.mark.integration

# Portable path to /bin/true (Linux) vs /usr/bin/true (macOS).
_TRUE_PATH = shutil.which("true") or "/usr/bin/true"


@pytest.mark.allow("subprocess")
async def test_async_subprocess_passthrough_returns_real_process() -> None:
    """C2-T5: With guard ALLOW for subprocess, asyncio.create_subprocess_exec
    outside any sandbox returns a real asyncio.subprocess.Process whose
    wait() resolves to the child exit code (0 for /bin/true).

    ESCAPE: test_async_subprocess_passthrough_returns_real_process
      CLAIM: When the firewall ALLOWs subprocess and no sandbox is active,
             our patched create_subprocess_exec falls into the
             GuardPassThrough branch and awaits the original
             asyncio.create_subprocess_exec, returning the real Process.
      PATH:  patched _fake_create_subprocess_exec catches GuardPassThrough,
             awaits _ORIGINAL_CREATE_SUBPROCESS_EXEC, returns its result.
      CHECK: isinstance(result, asyncio.subprocess.Process); wait() returns 0.
      MUTATION: If someone re-wraps the original return value in a
                _AsyncFakeProcess (the bug the cast() was hiding), the
                isinstance check would fail. If the await is removed and a
                _AsyncFakeProcess is returned directly, same failure.
      ESCAPE: A return-type annotation mismatch (only mypy catches that)
              would not change runtime behavior; the runtime test could
              still pass while the static types lied. The annotation is
              checked separately by mypy --strict.
    """
    proc = await asyncio.create_subprocess_exec(_TRUE_PATH)
    assert isinstance(proc, asyncio.subprocess.Process), type(proc)
    rc = await proc.wait()
    assert rc == 0


@pytest.mark.allow("subprocess")
async def test_async_subprocess_shell_passthrough_returns_real_process() -> None:
    """C2-T6: Same as T5 but for asyncio.create_subprocess_shell.

    ESCAPE: test_async_subprocess_shell_passthrough_returns_real_process
      CLAIM: Mirrors T5 for the shell variant.
      PATH:  patched _fake_create_subprocess_shell -> GuardPassThrough ->
             await _ORIGINAL_CREATE_SUBPROCESS_SHELL -> real Process.
      CHECK: isinstance + wait() == 0.
      MUTATION: Same as T5; the shell branch is a near-copy of exec and the
                fix applies to both.
      ESCAPE: A divergence between exec and shell branches (e.g., shell still
              wraps in _AsyncFakeProcess) would silently regress one but not
              the other; both tests are needed.
    """
    proc = await asyncio.create_subprocess_shell(_TRUE_PATH)
    assert isinstance(proc, asyncio.subprocess.Process), type(proc)
    rc = await proc.wait()
    assert rc == 0
