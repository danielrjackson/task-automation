"""Preserved display-case priority sections must not silently lose their tasks."""

import pytest
import yaml

from taskautomation.task_parser import parse_yaml_file
from taskautomation.task_schema import Priority, TaskList, ValidationError


@pytest.mark.parametrize("priority", list(Priority))
def test_display_priority_sections_preserve_tasks_and_canonical_output(priority):
    """Accept the existing priority label as an unambiguous input alias."""
    entry = {"id": 1, "title": "Synthetic preserved task", "priority": priority.value}
    data = {priority.value: [entry]}
    tasks = TaskList(data)
    assert [task.id for task in tasks.get_tasks_by_priority(priority)] == [1]
    output = tasks.to_dict()
    assert output[priority.value.lower()][0]["title"] == entry["title"]
    assert priority.value not in output
    assert data == {priority.value: [entry]}


@pytest.mark.parametrize("priority", list(Priority))
def test_duplicate_case_aliases_require_resolution_instead_of_dropping_data(priority):
    """Do not choose between conflicting canonical and display-case sections."""
    data = {priority.value.lower(): [], priority.value: [{"id": 1, "title": "Retained"}]}
    with pytest.raises(ValidationError, match="Ambiguous priority sections"):
        TaskList(data)
    assert data[priority.value][0]["title"] == "Retained"


@pytest.mark.parametrize("value", [None, "not a list", {"id": 1}])
def test_invalid_aliased_section_is_a_validation_failure(value):
    """An invalid section cannot turn into a successful empty model."""
    with pytest.raises(ValidationError, match="must be a list"):
        TaskList({"High": value})


@pytest.mark.parametrize("value", [None, "not a task", 1])
def test_invalid_task_entry_is_a_validation_failure(value):
    """Give malformed list entries the model's documented exception type."""
    with pytest.raises(ValidationError, match=r"task.*dictionary"):
        TaskList({"High": [value]})


def test_parser_accepts_display_sections_without_modifying_input_file(tmp_path):
    """Compatibility parsing preserves actual task data and original bytes."""
    path = tmp_path / "preserved.yaml"
    original = yaml.safe_dump({"High": [{"id": 9, "title": "Synthetic preserved task",
                                        "priority": "High"}]}).encode()
    path.write_bytes(original)
    tasks = parse_yaml_file(path)
    assert [task.id for task in tasks.high] == [9]
    assert path.read_bytes() == original
