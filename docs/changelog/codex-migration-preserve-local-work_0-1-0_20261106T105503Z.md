# Confirm fresh backup durability before task saves and restores

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T10:55:03.997732+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

Backups now stage complete bytes under a fresh pending name, flush the file, publish without replacing an existing backup and flush directory metadata before returning. Newly created backup directories and their parent entries are flushed too. Same-second timestamps and repeated parser saves retain earlier backups. Save and restore stop before altering current task bytes when backup persistence fails; recovery material is retained with an explicit unconfirmed-state error.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

Thirteen new cases cover name collisions, both saver refusal paths, real Windows directory flush failure, read-only source metadata, and owned synthetic process death after file or namespace persistence. Twenty-four focused backup and existing serialization cases pass. The restore refusal regression previously overwrote current data. One original draft expects warning-only unsafe restore continuation and is retained unchanged as an explicit contract conflict. This provides confirmed backup publication, not power-loss atomic replacement of the task file; concurrent source writers and storage ignoring flush requests remain outside the guarantee.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/backup_persistence.py`
- `src/taskautomation/file_operations.py`
- `src/taskautomation/task_parser.py`
- `tests/test_backup_persistence.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
