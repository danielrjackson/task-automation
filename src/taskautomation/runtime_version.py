"""Shared runtime requirement matching the declared Python package range."""

import sys


def check_runtime_version() -> tuple[str, str | None]:
    """Return the interpreter version and any blocking requirement error."""
    try:
        parts = tuple(sys.version_info[:3])
        if len(parts) != 3 or any(type(part) is not int or part < 0 for part in parts):
            raise ValueError("expected three nonnegative integer version components")
    except (TypeError, ValueError, AttributeError) as error:
        return "unknown", f"Could not check Python version: {error}"
    display = ".".join(map(str, parts))
    if not (3, 13) <= parts[:2] < (4, 0):
        return display, f"Python >=3.13,<4.0 required, found {display}"
    return display, None
