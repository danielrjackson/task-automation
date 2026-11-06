# Render canonical timestamps, active counts and safe YAML

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T11:00:47.024774+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

Human task summaries used raw datetime display instead of the existing canonical UTC/offset serializer, and active row lists counted archived completions in their header and status totals. Reuse the established timestamp policy and explicit active-task view. YAML formatters now use the same safe representation subset as the declared loaders and persistence APIs.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

Eight display regression cases fail before the correction, and an additional unsupported-Python-object case reproduces unsafe, unreloadable YAML output. Ten focused cases pass afterward, covering UTC, fractional offsets, legacy naive dates, grouped/flat active and archive-only views, exact model preservation and safe YAML roundtrips. Required task fields and canonical stored key casing are retained; incompatible original draft expectations are not used to relax them.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/output_formatter.py`
- `tests/test_summary_display_contract.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
