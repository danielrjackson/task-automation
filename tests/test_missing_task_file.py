"""Distinguish absent task files from invalid YAML and other I/O failures."""

from pathlib import Path

import pytest

from taskautomation.task_parser import parse_yaml_file
from taskautomation.task_schema import ValidationError


def test_missing_task_file_retains_documented_exception(tmp_path):
    """Callers can handle a missing source without treating it as corrupt data."""
    path = tmp_path / "absent.yaml"
    with pytest.raises(FileNotFoundError, match="Task file not found"):
        parse_yaml_file(path)
    assert not path.exists()


def test_missing_file_race_is_not_relabelled_as_schema_failure(tmp_path, monkeypatch):
    """A file disappearing between existence check and open stays a missing file."""
    path = tmp_path / "disappeared.yaml"
    original = Path.exists
    monkeypatch.setattr(Path, "exists", lambda self: True if self == path else original(self))
    with pytest.raises(FileNotFoundError):
        parse_yaml_file(path)


def test_invalid_yaml_keeps_validation_error(tmp_path):
    """Malformed bytes must remain a parse/validation failure."""
    path = tmp_path / "invalid.yaml"
    path.write_text("medium: [", encoding="utf-8")
    with pytest.raises(ValidationError, match="YAML parsing failed"):
        parse_yaml_file(path)


def test_other_io_error_keeps_validation_context(tmp_path, monkeypatch):
    """The missing-file exception change must not hide denied reads."""
    path = tmp_path / "denied.yaml"
    path.write_text("{}", encoding="utf-8")
    original = Path.open

    def denied(self, *args, **kwargs):
        if self == path:
            raise PermissionError("synthetic read denied")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    with pytest.raises(ValidationError, match="File I/O error"):
        parse_yaml_file(path)
