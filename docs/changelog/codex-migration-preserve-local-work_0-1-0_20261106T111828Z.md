# Fail closed on unsupported or unknown Python runtime versions

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T11:18:28.318944+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

Both environment validators now enforce the package requirement >=3.13,<4.0 through one shared version check. Missing or malformed version metadata is a blocking validation error rather than a warning that admits the environment. Version display supports the actual tuple contract as well as sys.version_info. No packages are installed and no project task files are opened.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

Eleven of twelve synthetic boundary and malformed-evidence cases failed before the fix. All twelve pass afterward, including the actual native interpreter. Original draft assumptions accepting Python 3.9 or naming a Python 3.8 minimum are preserved unchanged as incompatible expectations. Installed dependencies are imported with actual interpreter metadata before simulation, so their own version-dependent initialization is not corrupted by mocks.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/runtime_version.py`
- `src/taskautomation/file_operations.py`
- `src/taskautomation/task_validator.py`
- `tests/test_runtime_version_contract.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
