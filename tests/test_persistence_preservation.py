"""Failed persistence must preserve existing task bytes and the selected backup source."""

from pathlib import Path

import pytest

from taskautomation import file_operations, task_parser
from taskautomation.task_schema import TaskList


def save(kind, tasks, path, **kwargs):
    """Exercise both public save APIs without touching project task files."""
    if kind == "parser":
        return task_parser.save_yaml_file(tasks, path, **kwargs)
    return file_operations.save_tasks_file(tasks, path, validate=False, **kwargs)


@pytest.mark.parametrize("kind", ["parser", "operations"])
def test_unsupported_yaml_object_does_not_replace_existing_tasks(tmp_path, kind):
    """A Python-only YAML tag cannot become a successful, unreloadable save."""
    path = tmp_path / "tasks.yaml"
    original = b"# original synthetic tasks\r\nmedium: []\r\n"
    path.write_bytes(original)
    tasks = TaskList({"metadata": {"unsupported": object()}})
    result = save(kind, tasks, path, backup=False)
    assert result.success is False
    assert path.read_bytes() == original


@pytest.mark.parametrize("kind", ["parser", "operations"])
def test_model_serialization_failure_does_not_truncate_existing_tasks(tmp_path, kind, monkeypatch):
    """Complete model conversion before opening an existing destination for writing."""
    path = tmp_path / "tasks.yaml"
    original = b"# original synthetic tasks\nmedium: []\n"
    path.write_bytes(original)
    tasks = TaskList()

    def fail():
        raise RuntimeError("synthetic conversion failure")

    monkeypatch.setattr(tasks, "to_dict", fail)
    result = save(kind, tasks, path, backup=False)
    assert result.success is False
    assert path.read_bytes() == original


@pytest.mark.parametrize("kind", ["parser", "operations"])
def test_saved_supported_data_can_be_read_by_the_declared_safe_loader(tmp_path, kind):
    """Normal typed data, Unicode and metadata remain roundtrippable."""
    path = tmp_path / "tasks.yaml"
    tasks = TaskList({"metadata": {"project_name": "Synthetic café"},
                      "medium": [{"id": 1, "title": "Synthetic task"}]})
    result = save(kind, tasks, path, backup=False)
    assert result.success is True
    restored = task_parser.parse_yaml_file(path)
    assert restored.to_dict() == tasks.to_dict()


@pytest.mark.parametrize("default_exists", [False, True])
def test_custom_save_uses_selected_backup_source(tmp_path, default_exists, monkeypatch):
    """An unrelated or missing default task file cannot select backup contents."""
    default = tmp_path / "default.yaml"
    if default_exists:
        default.write_bytes(b"# unrelated synthetic default\n")
    path = tmp_path / "custom.yaml"
    original = b"# selected synthetic tasks\nmedium: []\n"
    path.write_bytes(original)
    monkeypatch.setattr(file_operations, "TASKS_FILE", default)
    monkeypatch.setattr(file_operations, "BACKUP_DIR", tmp_path / "backups")
    result = file_operations.save_tasks_file(TaskList(), path, validate=False)
    assert result.success is True
    backup = result.data["backup_path"]
    assert Path(backup).read_bytes() == original
    if default_exists:
        assert default.read_bytes() == b"# unrelated synthetic default\n"
    else:
        assert not default.exists()


def test_unsupported_dry_run_remains_side_effect_free(tmp_path):
    """A preview must not endorse data the safe loader cannot reload."""
    path = tmp_path / "missing" / "tasks.yaml"
    result = file_operations.save_tasks_file(
        TaskList({"metadata": {"unsupported": object()}}), path, validate=False, dry_run=True)
    assert result.success is False
    assert not path.parent.exists()


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_parser_backup_retains_original_bytes(tmp_path, newline):
    """A backup must not normalize historical line endings."""
    path = tmp_path / "tasks.yaml"
    original = newline.join([b"# synthetic original", b"medium: []", b""])
    path.write_bytes(original)
    result = task_parser.save_yaml_file(TaskList(), path, backup=True)
    assert result.success is True
    assert path.with_suffix(".yaml.backup").read_bytes() == original
