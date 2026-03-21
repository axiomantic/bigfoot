# Composable Mocking - Chunk 6/6: Docs, Version Bump, Finishing

## What This Chunk Does

Final chunk: update public API exports, bump version to 0.14.0, write documentation with migration guide, run full test suite, and create PR.

Previous chunks completed: ALL chunks 1-5

## How to Execute

### Step 1: Read the implementation plan

Use the Read tool:
```
Read /Users/elijahrutschman/.local/spellbook/docs/Users-elijahrutschman-Development-bigfoot/plans/2026-03-20-composable-mocking-impl.md
```

Find Tasks 5.1, 5.2, and 5.3.

### Step 2: Execute Task 5.1 -- API exports

Use the Read tool to read `src/bigfoot/__init__.py` and `src/bigfoot/plugins/__init__.py`.
Use the Edit tool to update `__all__` exports if they exist.
Verify new public API is importable:
```bash
cd /Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking && uv run python -c "from bigfoot import mock, spy; print(type(mock), type(spy)); print(hasattr(mock, 'object'), hasattr(spy, 'object'))"
```
Commit.

### Step 3: Execute Task 5.2 -- Version bump

Use the Read tool to read `pyproject.toml`.
Use the Edit tool to bump version to 0.14.0.
Commit.

### Step 4: Execute Task 5.3 -- Documentation

Update README.md with:
- New mock/spy API examples (colon-separated paths, .object())
- Context manager usage (with mock:, with sandbox:)
- Spy observability (returned/raised in details)
- Error mocking (mock_error on HTTP plugin)
- Migration guide for breaking changes (old mock("Name") -> new mock("mod:attr"))

Use the Read tool to read current README.md first, then Edit tool to update.
Commit.

### Step 5: Run full test suite

```bash
cd /Users/elijahrutschman/Development/bigfoot/.worktrees/error-mocking && uv run python -m pytest tests/ -q --tb=short
```

ALL tests must pass.

### Step 6: Finish the branch

Invoke the finishing-a-development-branch skill using the Skill tool:
```
Skill: finishing-a-development-branch
```

Context: Feature branch elijahr/error-mocking, all tests passing, ready for PR.

## Pre-conditions

- ALL chunks 1-5 complete
- All 27 plugins migrated
- MockPlugin rearchitected with import-site patching
- All tests passing

## Exit Criteria

- Public API exports correct
- Version is 0.14.0
- README/docs updated with new API, examples, migration guide
- Full test suite passes
- PR created or branch merged (per user choice)
