# Restore portable native editor configuration

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T07:35:20.367730+00:00
- **Type**: Improvement
- **Coverage**: JSON, root resolution, environment existence and launch-preservation checks passed.

## Description

Integrate the preserved split workspace/launch/settings configuration and select
the project-local `.venv` folder for Python environment discovery on either host.

## Rationale

The restored native environment uses `.venv/Scripts/python.exe`; a portable folder
setting avoids embedding an interpreter path for only one operating system.

## Details

The workspace still resolves to the same repository root. `launch.json` retains
every original workspace debugger configuration exactly. Existing spelling settings
are preserved. The interpreter folder exists locally. This default does not claim
to override an interpreter already selected in the editor, and editor UI acceptance
was not performed. No debugger, current file or live automation was launched.

## Files

- `.vscode/taskautomation.code-workspace`: preserve the root and split configuration.
- `.vscode/launch.json`: retain the original debugger entries.
- `.vscode/settings.json`: preserve spelling settings and use the local environment folder.

## Next Steps

Confirm the selected interpreter in the editor when its UI is available. This
editor configuration does not change the separate Codex project's WSL source path.

## Mistakes Discovered

No debugger configuration was dropped during the split.

## Lessons Learned

Check the old and new launch configurations for identity when moving editor
settings; validate root discovery separately from editor UI selection.

[Python settings reference](https://code.visualstudio.com/docs/python/settings-reference)
