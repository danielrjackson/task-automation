# Preserve archive membership across search and repeated requests

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T09:11:17.242075+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

Task searches included archived tasks even when explicitly excluded and duplicated them when included. Repeated archival selected an already archived task, appended it again and replaced its finish timestamp. Search the declared active or all-task view exactly once, and permit archive transitions only from active lists.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

Seven corrected synthetic regression cases fail before the implementation fix and pass afterward. They cover both archive search modes, unchanged archived state on repeat, each active priority, and the parser operation result. Fixture priority values use the existing case-sensitive enum without relaxing the schema.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/task_schema.py`
- `src/taskautomation/task_parser.py`
- `tests/test_archive_membership.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
