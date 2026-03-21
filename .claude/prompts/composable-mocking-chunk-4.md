# Composable Mocking - Chunk 4/6: Domain Plugin Migration (Batches 1-2)

## What This Chunk Does

Migrate the first ~14 domain plugins to use shared patching base from BasePlugin and store `raised` in interaction.details. These are simpler stateless plugins that extend BasePlugin directly.

Previous chunks completed: Chunk 1 (shared patching primitives)
Note: Does NOT require Chunks 2 or 3. Can run in parallel with them.

## How to Execute

### Step 1: Read the implementation plan

Use the Read tool:
```
Read /Users/elijahrutschman/.local/spellbook/docs/Users-elijahrutschman-Development-bigfoot/plans/2026-03-20-composable-mocking-impl.md
```

Find Tasks 3.1 and 3.2. These are your tasks.

### Step 2: Read the design document migration section

Use the Read tool:
```
Read /Users/elijahrutschman/.local/spellbook/docs/Users-elijahrutschman-Development-bigfoot/plans/2026-03-20-composable-mocking-design.md
```

Look for the "Domain Plugin Migration" section for the template pattern.

### Step 3: For each plugin in the batch

For EACH plugin listed in Tasks 3.1 and 3.2:

1. Use the Read tool to read the plugin source file (e.g., `src/bigfoot/plugins/redis_plugin.py`)
2. Use the Read tool to read its test file (e.g., `tests/unit/test_redis_plugin.py`)
3. Apply the migration template from the impl plan:
   - Replace custom `activate()`/`deactivate()` with BasePlugin's default (if applicable)
   - Use `_install_patches()`/`_restore_patches()` hooks
   - Add `raised` to interaction details when `config.raises` is set
   - Update `_check_conflicts()` if the plugin has conflict detection
4. Use the Edit tool to make changes
5. Run that plugin's tests:
   ```bash
   cd /Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking && uv run python -m pytest tests/unit/test_<plugin>.py -x -q
   ```
6. Commit each plugin migration separately using the Bash tool

Do NOT invoke the develop or TDD skill for each individual plugin -- this is mechanical migration work. Just read, edit, test, commit for each plugin.

### Step 4: After all plugins in batch, run full suite

```bash
cd /Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking && uv run python -m pytest tests/ -q --tb=short
```

## Pre-conditions

- Chunk 1 COMPLETE: BasePlugin has shared patching primitives (_install_patches, _restore_patches, _check_conflicts, default activate/deactivate)
- All tests passing

## Exit Criteria

- All plugins in Tasks 3.1 and 3.2 migrated to use BasePlugin's patching hooks
- All migrated plugins store `raised` in interaction.details when config.raises is set
- Each plugin's existing tests pass after migration
- Full test suite passes
- Each plugin migration committed separately (one commit per plugin or per small batch)

## Dependency Graph

```
Chunk 1 (patching) ──> This chunk (4) ──> Chunk 6 (finishing)
                  ──> Chunk 5 (batches 3-4, runs in parallel)
```
