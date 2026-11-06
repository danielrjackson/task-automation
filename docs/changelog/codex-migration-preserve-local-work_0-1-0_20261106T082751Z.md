# Load task files through the declared model and validator contracts

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T08:27:51.641229+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

The file loader passed a dictionary to a string validator, accessed a nonexistent result field, and imported a nonexistent parser function. Construct the declared TaskList directly and apply its semantic validator. Reject non-mapping roots and unsupported nested/legacy wrappers instead of silently emptying their data; preserve the original dictionary and leave source files unchanged.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

Eleven new synthetic regression checks failed before the fix. They cover valid and empty documents, false-like scalar/list roots, unsupported containers with either validation setting, and explicit semantic-validation opt-out for a typed model.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/file_operations.py`
- `tests/test_task_file_loading.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
