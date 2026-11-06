"""Every task parser must reject unsupported containers before losing their tasks."""

import pytest
import yaml

from taskautomation.task_parser import (
    parse_yaml_content,
    parse_yaml_file,
    validate_yaml_structure,
)
from taskautomation.task_schema import TaskList, ValidationError


@pytest.mark.parametrize("key", ["tasks", "archived_tasks"])
def test_all_parser_entrypoints_refuse_unsupported_task_containers(tmp_path, key):
    """A wrapper must not become a successful empty import through another API."""
    data = {key: [{"id": 1, "title": "Synthetic retained task"}]}
    content = yaml.safe_dump(data)
    path = tmp_path / "unsupported.yaml"
    path.write_text(content, encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(ValidationError, match="Unsupported task container"):
        TaskList(data)
    with pytest.raises(ValidationError, match="Unsupported task container"):
        parse_yaml_content(content)
    with pytest.raises(ValidationError, match="Unsupported task container"):
        parse_yaml_file(path)
    result = validate_yaml_structure(content)
    assert result.success is False
    assert path.read_bytes() == before


@pytest.mark.parametrize("data", [[], False, 0, "text"])
def test_invalid_root_has_documented_validation_error(data):
    """A typed input failure must not escape as AttributeError."""
    with pytest.raises(ValidationError, match="root must be a dictionary"):
        TaskList(data)
    with pytest.raises(ValidationError, match="root must be a dictionary"):
        parse_yaml_content(yaml.safe_dump(data))


def test_valid_flat_sections_and_empty_documents_remain_supported(tmp_path):
    """The existing flat schema and explicit empty default retain their data."""
    data = {"medium": [{"id": 1, "title": "Synthetic active"}],
            "archive": [{"id": 2, "title": "Synthetic archived", "status": "completed"}]}
    content = yaml.safe_dump(data)
    path = tmp_path / "valid.yaml"
    path.write_text(content, encoding="utf-8")
    assert [task.id for task in parse_yaml_content(content).get_all_tasks()] == [1, 2]
    assert [task.id for task in parse_yaml_file(path).get_all_tasks()] == [1, 2]
    assert validate_yaml_structure(content).success is True
    assert parse_yaml_content("").get_all_tasks() == []
