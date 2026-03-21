# Composable Mocking - Chunk 2/6: Interaction Enforce Flag

## What This Chunk Does

Add `enforce: bool = True` field to the Interaction dataclass. Update `verify_all()` to filter to enforce=True interactions only. This enables mocks activated individually (outside sandbox) to record without requiring assertion.

Previous chunks completed: none (runs in parallel with Chunk 1)

## How to Execute

### Step 1: Read the implementation plan

Use the Read tool:
```
Read /Users/elijahrutschman/.local/spellbook/docs/Users-elijahrutschman-Development-bigfoot/plans/2026-03-20-composable-mocking-impl.md
```

Find Task 1.1. This is your only task.

### Step 2: Read the relevant source files

Use the Read tool to read these files BEFORE making any changes:
- `src/bigfoot/_timeline.py` (Interaction dataclass, Timeline class)
- `src/bigfoot/_verifier.py` (verify_all, all_unasserted usage)

### Step 3: Execute Task 1.1 using TDD

Invoke the test-driven-development skill using the Skill tool:
```
Skill: test-driven-development
```

Follow its complete workflow (RED-GREEN-COMMIT).

Key changes:
1. Add `enforce: bool = True` to Interaction dataclass in `_timeline.py`
2. Update `Timeline.all_unasserted()` to accept optional `enforce_only: bool = True` parameter
3. Update `StrictVerifier.verify_all()` to only check enforce=True interactions
4. Write tests proving enforce=False interactions are ignored by verify_all()

Working directory: `/Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking`

Run tests:
```bash
cd /Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking && uv run python -m pytest tests/ -x -q
```

Commit when done.

## Pre-conditions

- Branch `elijahr/error-mocking` with error mocking work committed
- 1565 tests passing baseline

## Exit Criteria

- `Interaction` dataclass has `enforce: bool = True` field
- `verify_all()` filters to enforce=True interactions only
- All existing tests pass (all current interactions default to enforce=True, zero behavior change)
- New tests verify: interaction with enforce=False is NOT reported by verify_all()
- New tests verify: interaction with enforce=True IS reported by verify_all() (current behavior preserved)
- Changes committed

## Dependency Graph

```
This chunk (2) ──> Chunk 3 (MockPlugin rearchitecture) -- needs both 1 and 2
Chunk 1 (patching) runs in PARALLEL with this chunk
```
