# Reject unsupported task containers through every parser entrypoint

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T09:18:36.150655+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

The file-operations loader rejected unsupported nested task wrappers, but direct TaskList construction and the YAML parser still accepted them as empty data. Enforce the existing flat-container contract at the shared model boundary, and give non-mapping roots the documented ValidationError instead of AttributeError.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

Six regression cases fail before the fix. All seven new cases pass afterward, covering all public parser entrypoints, both unsupported wrapper names, false-like and scalar roots, unchanged source files, valid flat active/archive sections and empty documents. The earlier file loader tests also continue to pass.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/task_schema.py`
- `tests/test_parser_container_preservation.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
