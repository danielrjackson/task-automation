# Preserve the validated native development environment

- **Author**: Codex migration worker
- **Branch**: codex/migration-preserve-local-work
- **Version**: 0.1.0
- **Date**: 2026-11-06T07:32:15.622002+00:00
- **Type**: Improvement
- **Coverage**: Exact staged native tests and local wheel build recorded in the migration receipt.

## Description

Integrate the preserved project metadata and universal uv lock after recreating
the developer environment under native CPython 3.13.3. The license reference now
names the existing tracked `LICENSE` file.

## Rationale

Make the restored native developer environment reproducible without changing the
system interpreter or installing tools into the research environment.

## Details

The project-local environment contains 23 compatible locked distributions.
`uv sync --locked --dry-run` resolves the preserved lock and requests no changes.
Retain the preserved type-checker and Ruff configuration, dependency versions and
build-backend minimum. Validate a wheel locally against the exact staged source
using the declared minimum Hatchling version, without publishing or deploying it.

## Files

- `pyproject.toml`: preserved developer dependencies, tooling metadata and license reference.
- `uv.lock`: preserved universal dependency resolution and distribution hashes.

## Next Steps

Keep unrelated untracked feature-test drafts separate until their API mismatches
are resolved. This environment integration does not claim those drafts pass.

## Mistakes Discovered

The original metadata named `LICENSE.md` while the tracked license is `LICENSE`.

## Lessons Learned

Check both the declared lock and built package metadata when restoring a native
developer environment; passing imports alone does not establish packaging parity.
