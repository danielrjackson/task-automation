# Preserve task bytes when serialization fails and back up the selected source

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T10:10:04.604610+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

Both save APIs now finish safe YAML serialization before opening the destination or creating its backup. This prevents model conversion and unsupported Python-object serialization from truncating existing tasks or producing tags the safe loader cannot reload. Custom-path saves select that file as the backup source, and parser backups copy original bytes rather than normalizing line endings.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

Eleven regression cases reproduce seven failures before the fix and pass afterward. They cover both save APIs, conversion and representation failures, supported Unicode/model roundtrips, custom paths with missing or unrelated defaults, side-effect-free rejected previews, and LF/CRLF backup identity. The earlier load and missing-file checks also pass. This change does not claim power-loss-atomic writes, concurrency control or collision-free historical backup retention; the unsupported atomicity claim in the module overview was corrected.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/task_parser.py`
- `src/taskautomation/file_operations.py`
- `tests/test_persistence_preservation.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
