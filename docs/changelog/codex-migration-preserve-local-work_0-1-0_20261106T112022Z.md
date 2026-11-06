# Report compatibility diagnostics using accepted priority aliases

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T11:20:22.975776+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

Schema compatibility warnings now recognize precisely the canonical and display-case priority aliases already accepted by TaskList. Present sections are no longer reported missing; missing-section names use the human priority labels. Invalid metadata remains a blocking error and identifies its field. Model validation continues rejecting ambiguous aliases, invalid section values and unsupported containers.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

Five of seven new synthetic cases failed before the fix. They verify canonical, display and mixed aliases, exact missing-section membership, isolated missing-version diagnostics, unchanged input data, ambiguous/invalid rejection and field-specific metadata errors. Stored key casing and all task admission requirements are unchanged.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/task_validator.py`
- `tests/test_compatibility_diagnostics.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
