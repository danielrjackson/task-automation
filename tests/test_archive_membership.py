"""Archive membership must survive retries and search without duplication."""

import pytest

from taskautomation.task_parser import archive_task, find_tasks_by_criteria
from taskautomation.task_schema import Priority, Task, TaskList


def sample_tasks():
    """Create one active and one archived synthetic task."""
    return TaskList({
        "high": [{"id": 1, "title": "Synthetic active", "priority": "High"}],
        "archive": [{"id": 2, "title": "Synthetic archived", "priority": "Low",
                     "status": "completed", "finish_date": "2026-01-01T00:00:00Z"}],
    })


@pytest.mark.parametrize("include_archived, expected", [(False, [1]), (True, [1, 2])])
def test_search_respects_archive_membership(include_archived, expected):
    """Return each selected task once and respect archive exclusion."""
    tasks = sample_tasks()
    result = find_tasks_by_criteria(tasks, include_archived=include_archived)
    assert [task.id for task in result] == expected


def test_repeated_archive_cannot_duplicate_or_retimestamp_task():
    """A repeated archive request leaves persisted task state unchanged."""
    tasks = sample_tasks()
    original = tasks.get_task_by_id(2)
    finish = original.finish_date
    before = tasks.to_dict()
    assert tasks.archive_task(2) is False
    assert tasks.to_dict() == before
    assert tasks.archive == [original]
    assert original.finish_date == finish


@pytest.mark.parametrize("priority", list(Priority))
def test_only_active_tasks_can_transition_to_archive(priority):
    """Each active priority supports one transition and refuses a repeat."""
    task = Task({"id": 7, "title": "Synthetic transition", "priority": priority})
    tasks = TaskList()
    tasks.add_task(task)
    assert tasks.archive_task(7) is True
    assert tasks.get_active_tasks() == []
    assert tasks.archive == [task]
    finish = task.finish_date
    repeated = archive_task(tasks, 7)
    assert repeated.success is False
    assert tasks.archive == [task]
    assert task.finish_date == finish
