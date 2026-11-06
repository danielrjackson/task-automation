"""File loading must preserve typed tasks and reject unsupported input shapes."""

import pytest
import yaml

from taskautomation.file_operations import load_tasks_file


def test_valid_task_file_loads_model_and_original_dictionary(tmp_path):
    """The public loader must use the actual model and semantic-validator APIs."""
    path = tmp_path / "tasks.yaml"
    data = {"metadata": {"version": "1.0"}, "medium": [
        {"id": 1, "title": "Synthetic task", "priority": "Medium", "status": "pending"},
    ]}
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    before = path.read_bytes()
    tasks, original = load_tasks_file(path)
    assert original == data
    assert len(tasks.medium) == 1
    assert tasks.medium[0].id == 1
    assert tasks.medium[0].title == "Synthetic task"
    assert path.read_bytes() == before


def test_empty_task_file_remains_an_explicit_empty_model(tmp_path):
    """Only an empty YAML document receives the existing empty-model default."""
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    tasks, original = load_tasks_file(path)
    assert original == {}
    assert tasks.get_all_tasks() == []


@pytest.mark.parametrize("content", ["[]", "false", "0", "'text'"])
def test_nonmapping_document_is_not_silently_emptied(tmp_path, content):
    """False-like scalar/list data must not turn into a successful empty import."""
    path = tmp_path / "invalid-root.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="root must be a dictionary"):
        load_tasks_file(path)
    assert path.read_text(encoding="utf-8") == content


@pytest.mark.parametrize("key", ["tasks", "archived_tasks"])
@pytest.mark.parametrize("validate", [True, False])
def test_unsupported_wrapper_is_retained_for_review(tmp_path, key, validate):
    """Do not silently discard legacy/nested sections the model does not support."""
    path = tmp_path / "unsupported.yaml"
    content = yaml.safe_dump({key: [{"id": 1, "title": "Synthetic task"}]})
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported task container"):
        load_tasks_file(path, validate=validate)
    assert path.read_text(encoding="utf-8") == content


def test_semantic_validation_can_be_explicitly_disabled(tmp_path):
    """The flag skips semantic checks rather than changing the parsed model."""
    path = tmp_path / "duplicates.yaml"
    data = {"medium": [{"id": 1, "title": "First"}, {"id": 1, "title": "Second"}]}
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match="validation failed"):
        load_tasks_file(path)
    tasks, original = load_tasks_file(path, validate=False)
    assert len(tasks.medium) == 2
    assert original == data
