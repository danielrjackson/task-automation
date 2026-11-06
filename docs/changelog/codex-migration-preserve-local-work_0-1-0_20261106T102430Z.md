# Preserve unambiguous display-case priority sections

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T10:24:30.340345+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

Preserved task data and feature tests use the existing priority labels Critical, High, Medium and Low as flat section names. The maintained model silently ignored those sections, losing their tasks. Accept each known display-case label as an input alias for its canonical lowercase section while keeping output canonical. Refuse duplicate case aliases and invalid list/task shapes instead of dropping data.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

All fifteen regression cases fail before the fix. They cover the four known priority labels, conflicting canonical/display aliases, malformed sections and entries, unchanged input dictionaries and actual YAML files. Twenty-nine focused compatibility, wrapper rejection and archive checks pass. No unknown container, arbitrary case conversion, priority inference or automatic rewrite of original files was added.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/task_schema.py`
- `tests/test_priority_section_compatibility.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
