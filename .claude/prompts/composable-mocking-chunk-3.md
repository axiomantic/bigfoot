# Composable Mocking - Chunk 3/6: MockPlugin Rearchitecture

## What This Chunk Does

The core rearchitecture. Replace MockPlugin's standalone proxy pattern with import-site patching. Implement:
- `resolve_target()` for colon-separated path resolution
- `_BaseMock`, `ImportSiteMock`, `ObjectMock` with context manager protocol
- `_MockDispatchProxy` for intercepting attribute access on patched objects
- SandboxContext mock activation/deactivation
- `_MockFactory`/`_SpyFactory` as callable objects with `.object()` methods
- Spy mode recording all calls
- Migration of all existing MockPlugin tests to new API

This is the largest chunk (7 tasks).

Previous chunks completed: Chunk 1 (shared patching), Chunk 2 (enforce flag)

## How to Execute

### Step 1: Read the implementation plan

Use the Read tool:
```
Read /Users/elijahrutschman/.local/spellbook/docs/Users-elijahrutschman-Development-bigfoot/plans/2026-03-20-composable-mocking-impl.md
```

Find Tasks 2.1 through 2.7. These are your tasks. Execute them IN ORDER.

### Step 2: Read the design document

Use the Read tool:
```
Read /Users/elijahrutschman/.local/spellbook/docs/Users-elijahrutschman-Development-bigfoot/plans/2026-03-20-composable-mocking-design.md
```

### Step 3: Read the current source files

Use the Read tool to read ALL of these BEFORE starting:
- `src/bigfoot/_mock_plugin.py` (you will heavily modify this)
- `src/bigfoot/__init__.py` (you will modify mock/spy API)
- `src/bigfoot/_verifier.py` (you will modify SandboxContext)
- `src/bigfoot/_patching.py` (created by Chunk 1, you will use it)
- `src/bigfoot/_timeline.py` (modified by Chunk 2, has enforce flag)
- `tests/unit/test_mock_plugin.py` (you will migrate these tests)
- `tests/dogfood/test_dogfood.py` (you will update these tests)

### Step 4: For each task (2.1 through 2.7), invoke TDD

For EACH task, invoke the test-driven-development skill using the Skill tool:
```
Skill: test-driven-development
```

Follow RED-GREEN-COMMIT for each task. Run targeted tests after each:
```bash
cd /Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking && uv run python -m pytest tests/unit/test_mock_plugin.py -x -q
```

Commit after each task.

### Step 5: After all 7 tasks, run full suite

```bash
cd /Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking && uv run python -m pytest tests/ -q --tb=short
```

## Pre-conditions

- Chunk 1 COMPLETE: `_patching.py` exists, BasePlugin has shared patching primitives
- Chunk 2 COMPLETE: Interaction has `enforce` field, verify_all() filters by it
- All tests passing

## Exit Criteria

- `resolve_target("mod:attr")` resolves module:attr, mod:Class, mod:Class.method
- `_BaseMock` base with `_activate(enforce)`, `_deactivate()`, `__enter__`/`__exit__`/`__aenter__`/`__aexit__`
- `ImportSiteMock` resolves colon-separated paths at activation
- `ObjectMock` patches target.attr at activation
- `_MockDispatchProxy` intercepts `__getattr__` on patched objects, returns `MethodProxy`
- `SandboxContext._enter()` activates all registered mocks with enforce=True
- `SandboxContext._exit()` deactivates all mocks (restores originals)
- `with mock:` activates with enforce=False, deactivates on exit
- `bigfoot.mock` is a `_MockFactory` instance with `__call__` and `.object()` methods
- `bigfoot.spy` is a `_SpyFactory` instance with `__call__` and `.object()` methods
- Spy mode records ALL method calls with returned/raised in details
- All existing MockPlugin tests migrated to use `mock.object()` or `mock("mod:attr")`
- All dogfood tests updated
- All tests pass
- All changes committed

## Dependency Graph

```
Chunk 1 (patching) ──┐
                     ├──> This chunk (3) ──> Chunk 6 (finishing)
Chunk 2 (enforce) ───┘
```
