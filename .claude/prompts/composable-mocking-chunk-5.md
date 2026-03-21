# Composable Mocking - Chunk 5/6: Domain Plugin Migration (Batches 3-4)

## What This Chunk Does

Migrate the remaining ~13 domain plugins: multi-patch stateless plugins (like Boto3Plugin with its complex patching) and all 11 StateMachinePlugin subclasses. These require more careful handling.

Previous chunks completed: Chunk 1 (shared patching primitives)
Note: Does NOT require Chunks 2 or 3. Can run in parallel with them.

## How to Execute

### Step 1: Read the implementation plan

Use the Read tool:
```
Read /Users/elijahrutschman/.local/spellbook/docs/Users-elijahrutschman-Development-bigfoot/plans/2026-03-20-composable-mocking-impl.md
```

Find Tasks 3.3 and 3.4. These are your tasks.

### Step 2: Read the design document

Use the Read tool:
```
Read /Users/elijahrutschman/.local/spellbook/docs/Users-elijahrutschman-Development-bigfoot/plans/2026-03-20-composable-mocking-design.md
```

### Step 3: For Task 3.3 (multi-patch BasePlugin subclasses)

These plugins have multiple patch points or complex patching. For EACH plugin:

1. Use the Read tool to read the plugin source and test file
2. Apply migration: use `_install_patches()`/`_restore_patches()` hooks, add `raised` to details
3. Use the Edit tool to make changes
4. Run plugin tests:
   ```bash
   cd /Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking && uv run python -m pytest tests/unit/test_<plugin>.py -x -q
   ```
5. Commit using Bash tool

### Step 4: For Task 3.4 (StateMachinePlugin subclasses)

CRITICAL: StateMachinePlugin subclasses have lifecycle state machines (connect/disconnect, open/close). Their activate/deactivate manages state machine initialization, not just patching. Be careful:

1. Read `src/bigfoot/plugins/_state_machine_plugin.py` FIRST to understand the base
2. For EACH StateMachinePlugin subclass:
   - Read the plugin source and test file
   - These plugins may need to KEEP their custom activate/deactivate if it manages state beyond patching
   - Add `raised` to interaction details
   - Integrate with shared patching where possible without breaking state machine logic
3. Run tests after each plugin
4. Commit each separately

### Step 5: Run full suite

```bash
cd /Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking && uv run python -m pytest tests/ -q --tb=short
```

## Pre-conditions

- Chunk 1 COMPLETE: BasePlugin has shared patching primitives
- All tests passing

## Exit Criteria

- All plugins in Tasks 3.3 and 3.4 migrated
- All 11 StateMachinePlugin subclasses: preserve lifecycle state machines, integrate shared patching where safe, store raised in details
- All existing plugin tests pass after migration
- Full test suite passes
- All changes committed

## Dependency Graph

```
Chunk 1 (patching) ──> This chunk (5) ──> Chunk 6 (finishing)
                  ──> Chunk 4 (batches 1-2, runs in parallel)
```
