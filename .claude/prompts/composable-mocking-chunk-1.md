# Composable Mocking - Chunk 1/6: Shared Patching Primitives

## What This Chunk Does

Build the shared patching infrastructure in BasePlugin that all plugins (MockPlugin + 27 domain plugins) will use. Creates `_patching.py` with PatchSet/PatchTarget, updates BasePlugin with `__init_subclass__`, default ref-counted activate/deactivate, and hook methods.

Previous chunks completed: none (this is the first chunk)

## How to Execute

### Step 1: Read the implementation plan

Use the Read tool to read the full implementation plan:
```
Read /Users/elijahrutschman/.local/spellbook/docs/Users-elijahrutschman-Development-bigfoot/plans/2026-03-20-composable-mocking-impl.md
```

Find Tasks 0.1, 0.2, and 0.3. These are your tasks.

### Step 2: Read the design document

Use the Read tool to read the design document for architectural context:
```
Read /Users/elijahrutschman/.local/spellbook/docs/Users-elijahrutschman-Development-bigfoot/plans/2026-03-20-composable-mocking-design.md
```

### Step 3: Execute each task using TDD

For each task (0.1, 0.2, 0.3), invoke the test-driven-development skill using the Skill tool:
```
Skill: test-driven-development
```

Then follow its complete workflow (RED-GREEN-COMMIT) for that task.

Before writing any code, read the existing source files using the Read tool:
- `src/bigfoot/_base_plugin.py` (you will modify this)
- `src/bigfoot/_timeline.py` (for Interaction dataclass reference)

Working directory for ALL commands: `/Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking`

Run tests after each task:
```bash
cd /Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking && uv run python -m pytest tests/ -x -q
```

Commit after each task using the Bash tool.

### Step 4: Verify backward compatibility

After all 3 tasks, specifically run tests for StateMachinePlugin subclasses:
```bash
cd /Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking && uv run python -m pytest tests/unit/test_ssh_plugin.py tests/unit/test_pika_plugin.py tests/unit/test_smtp_plugin.py tests/unit/test_database_plugin.py -x -q
```

## Pre-conditions

- Branch `elijahr/error-mocking` with error mocking work committed
- 1565 tests passing baseline

## Exit Criteria

- `src/bigfoot/_patching.py` exists with PatchSet and PatchTarget classes (with _ABSENT sentinel for None handling)
- BasePlugin has `__init_subclass__` providing per-class `_install_lock` and `_install_count`
- BasePlugin has default `activate()`/`deactivate()` with ref counting calling `_check_conflicts()` then `_install_patches()`/`_restore_patches()`
- `_install_patches()`, `_restore_patches()`, `_check_conflicts()` are default no-ops (NOT abstract)
- All 11 StateMachinePlugin subclasses still work
- All existing 1565 tests pass
- All changes committed

## Dependency Graph

```
This chunk (1) ──┬──> Chunk 3 (MockPlugin rearchitecture) -- needs both 1 and 2
                 ├──> Chunk 4 (plugin migration batch 1-2) -- needs only 1
                 └──> Chunk 5 (plugin migration batch 3-4) -- needs only 1

Chunk 2 (enforce flag) runs in PARALLEL with this chunk
```
