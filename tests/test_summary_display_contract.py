"""Rendered task summaries must preserve timestamp meaning and active-work counts."""

import pytest
import yaml

from taskautomation.output_formatter import (
    format_task_list_summary,
    format_task_list_yaml,
    format_task_summary,
)
from taskautomation.task_schema import Task, TaskList


@pytest.mark.parametrize("timestamp, expected", [
    ("2026-01-01T12:30:00Z", "2026-01-01T12:30:00Z"),
    ("2026-01-01T12:30:00.125+05:30", "2026-01-01T12:30:00.125000+05:30"),
    ("2026-01-01T12:30:00-07:00", "2026-01-01T12:30:00-07:00"),
    ("2026-01-01T12:30:00", "2026-01-01T12:30:00Z"),
])
def test_summary_dates_follow_the_existing_canonical_timestamp_policy(timestamp, expected):
    """Display the same UTC/offset meaning as persisted typed task dates."""
    task = Task({"id": 1, "title": "Synthetic date task", "created_date": timestamp,
                 "start_date": timestamp, "finish_date": timestamp})
    before = task.to_dict()
    output = format_task_summary(task)
    for label in ("Created", "Start", "Finish"):
        assert f"{label}: {expected}" in output
    assert task.to_dict() == before


@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize("active", [False, True])
def test_rendered_count_and_status_match_active_rows(grouped, active):
    """Archived completions must not inflate counts for active rows."""
    tasks = TaskList({
        "high": [{"id": 1, "title": "Synthetic active", "priority": "High"}] if active else [],
        "archive": [{"id": 2, "title": "Synthetic archive", "status": "completed"}],
    })
    output = format_task_list_summary(tasks, group_by_priority=grouped)
    assert f"Total Tasks: {int(active)}" in output
    assert "Completed" not in output
    assert "Synthetic archive" not in output
    if grouped:
        assert "ARCHIVED (1 tasks)" in output


def test_yaml_output_can_be_reloaded_by_the_safe_task_parser():
    """Supported metadata and tasks remain typed-data roundtrippable."""
    tasks = TaskList({"metadata": {"project_name": "Synthetic café"},
                      "High": [{"id": 1, "title": "Synthetic task", "priority": "High"}]})
    content = format_task_list_yaml(tasks)
    assert TaskList(yaml.safe_load(content)).to_dict() == tasks.to_dict()


def test_yaml_output_refuses_python_only_object_tags():
    """Do not produce YAML that the declared safe loader cannot reload."""
    tasks = TaskList({"metadata": {"unsupported": object()}})
    with pytest.raises(yaml.YAMLError):
        format_task_list_yaml(tasks)
