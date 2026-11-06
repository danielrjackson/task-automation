# Run native pytest with intact arguments and the selected Python

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T17:45:28.160157+00:00
- **Type**: Fix
- **Task**: [SYN-97](https://linear.app/synaptic-lens-research/issue/SYN-97/migrate-development-to-native-windows)

## Description

The preserved test runner joined pytest arguments into a shell command and selected
pytest from PATH. Windows paths with spaces and shell metacharacters were changed
before pytest received them, and a different environment could be selected. The
runner now invokes its current Python with `-m pytest` using literal arguments,
consumes its documented forwarding separator, and runs from its configured project
root. The optional formatter also receives an argument list.

## Validation

Five new native cases failed before the fix. The working-directory extension also
failed before its correction. All 21 new and existing runner cases pass afterward.
The CLI integration case uses a byte-identical disposable source copy, a test path
with spaces and a separate launch directory. No real task list is updated.

Read-only comparison of the previously reviewed 213 utility sources found only the
intended runner source changed from the previous lineage receipt. Unrelated feature
drafts, templates, WSL originals and protected data remain untouched. Exact staged
source qualification is recorded separately in the migration receipt; no package
installation, publication, dashboard deployment or research launch is included.

## Compatibility

The module's internal `run` and `build_pytest_command` helpers now use argument
lists instead of shell strings. Their maintained callers are updated. Shell syntax
is passed literally; this runner no longer supports shell command composition.
