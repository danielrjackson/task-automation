# Preserve valid task timestamps across persistence

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T08:01:19.263055+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

Timezone-aware task dates were serialized with both an offset and Z, producing strings that the task parser could not reload. Preserve explicit non-UTC offsets, emit a single Z for UTC, and retain the legacy Z policy for naive dates and null optional dates.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

New regression checks reproduced five failures before the fix and pass afterward. They cover UTC, fractional seconds, positive and negative offsets, default creation dates, optional null values and legacy naive timestamps.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/task_schema.py`
- `tests/test_datetime_roundtrip.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
