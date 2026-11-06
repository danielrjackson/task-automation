"""Runtime checks enforce the package requirement and fail closed."""

import importlib
import sys
from unittest.mock import patch

import pytest

from taskautomation.file_operations import _check_python_version
from taskautomation.task_validator import validate_automation_environment


@pytest.fixture(autouse=True)
def load_dependencies_before_version_simulation():
    """Import actual installed dependencies with actual interpreter metadata."""
    importlib.import_module("pydantic")


@pytest.mark.parametrize("version,accepted", [
    ((3, 7, 0), False), ((3, 9, 0), False), ((3, 12, 9), False),
    ((3, 13, 0), True), ((3, 14, 1), True), ((4, 0, 0), False),
])
def test_both_checks_enforce_declared_python_range(version, accepted):
    """Both public environment paths agree with requires-python ~=3.13."""
    errors, context = [], {}
    with patch.object(sys, "version_info", version), patch("os.path.exists", return_value=True):
        _check_python_version(errors, context)
        result = validate_automation_environment()
    assert (not errors) is accepted
    assert result.is_valid is accepted
    assert context["python_version"] == ".".join(map(str, version))
    if not accepted:
        assert any("3.13" in error for error in result.errors)


@pytest.mark.parametrize("version", [None, (), (3,), ("3", 13, 0), (True, 13, 0)])
def test_unreadable_version_does_not_admit_environment(version):
    """Missing or malformed version evidence must produce an error, not a warning."""
    errors, context = [], {}
    with patch.object(sys, "version_info", version), patch("os.path.exists", return_value=True):
        _check_python_version(errors, context)
        result = validate_automation_environment()
    assert errors
    assert result.is_valid is False
    assert any("Python version" in error for error in result.errors)


def test_native_runtime_matches_package_requirement():
    """The actual native interpreter passes the same check without mocks."""
    errors, context = [], {}
    _check_python_version(errors, context)
    assert errors == []
    assert context["python_version"] == ".".join(map(str, sys.version_info[:3]))
