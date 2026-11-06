# Keep task completion booleans distinct from integer identities

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T08:09:16.585060+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

Subtask completion previously coerced strings such as false to True, and generic integer validation accepted Python booleans as task IDs. Reject ambiguous non-boolean completion values and boolean identities while preserving actual booleans, the omitted completion default and ordinary integer range behavior.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

New synthetic regression checks reproduced nine failures before the fix. They verify that malformed completion cannot silently mark work done and that bool/int inheritance cannot create an ambiguous task identity.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/task_schema.py`
- `tests/test_schema_scalar_types.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
