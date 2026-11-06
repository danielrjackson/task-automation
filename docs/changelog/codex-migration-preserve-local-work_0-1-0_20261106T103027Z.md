# Keep archived completion separate from active task progress

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T10:30:27.823358+00:00
- **Type**: Fix
- **Coverage**: Synthetic regression and exact staged-source validation recorded in the migration receipts.

## Description

The task parser labeled its total as active work but counted get_all_tasks, which includes archived tasks. Archived completions inflated active totals, status/priority counts and completion rates. Use the explicit active-task view while retaining the separate archive count, without changing the model or stored data.

## Rationale

Restore the existing persistence/input contract without accepting incompatible
feature-draft assumptions or running the updater on actual project tasks.

## Details

Three of four new regression cases fail before the fix. They cover pending work with completed archives, mixed active status, archive-only and all-active-completed lists. Twenty-six focused summary, archive and input-compatibility cases pass. The original preserved comprehensive-summary feature case is also reassessed in disposable scratch; original draft files are not edited.

The complete staged source is qualified in disposable native scratch. Unrelated
feature tests, templates and other working changes are excluded from this commit.

## Files

- `src/taskautomation/task_parser.py`
- `tests/test_active_task_summary.py`

## Next Steps

Keep unrelated preserved feature drafts separate until their contracts are resolved.
No package publication, deployment or actual task-file migration is included.

## Mistakes Discovered

The regression is in maintained implementation behavior, rather than a reason to
relax the new test expectations or silently reinterpret persisted input.

## Lessons Learned

Test persistence roundtrips and observable exception contracts, not just successful
object construction or individual formatter calls.
