# Preserve documented missing task file errors

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T08:07:10.840000+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

A deliberately raised FileNotFoundError was caught by the generic OSError handler and mislabeled as a schema failure. Preserve the documented missing-file exception, including a disappearance between existence check and open, while retaining validation context for malformed YAML and denied reads.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

New synthetic regression checks reproduce the missing-file and disappearance failures before the fix and verify the corrected behavior alongside unchanged YAML/permission failure handling.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/task_parser.py`
- `tests/test_missing_task_file.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
