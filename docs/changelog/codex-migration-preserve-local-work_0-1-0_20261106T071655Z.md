# Reject invalid task containers before dictionary access

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T07:16:55.307015+00:00
- **Type**: Fix
- **Coverage**: Native focused checks passed; coverage percentage not measured.

## Description

Integrate the preserved type guard in `validate_task_schema`: non-dictionary input
returns a structured validation failure before accessing `.keys()`.

## Rationale

Malformed input previously raised `AttributeError` instead of a validation result.
This maintenance change preserves valid dictionary behavior and error context.

## Details

Retain the preserved expanded validation tests and correct two draft diagnostic
expectations to the existing task-container and task-ID contracts. Add regression
cases for strings, lists, integers, null and a dictionary-like object whose keys
method must never run. Native focused core/validation checks passed: 47 tests and
22 subtests. The exact staged source tree is tested separately in disposable scratch.

## Files

- `src/taskautomation/validation_utils.py`: reject invalid containers before key access.
- `tests/test_validation_utils.py`: preserved expanded validation checks and precise diagnostics.
- `tests/test_schema_input_guard.py`: malformed-container regression and valid-input context.

## Next Steps

Keep unrelated preserved feature drafts separate until their API mismatches are
resolved and tested. No task updater was applied to actual project tasks, and no
publication or deployment is part of this local integration.

## Mistakes Discovered

Two draft tests expected metadata/ID diagnostics for a top-level task container or
`task_id`. Their corrected assertions now verify the actual intended input boundary.

## Lessons Learned

Validate a container's type before reading its keys; retain a structured error and
verify that dictionary-like objects cannot bypass that boundary.
