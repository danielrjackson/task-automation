"""Archived completion must not inflate current work progress."""

import pytest

from taskautomation.task_parser import get_task_summary
from taskautomation.task_schema import TaskList


@pytest.mark.parametrize("statuses, archived, rate", [
    (["pending"], 2, 0.0),
    (["pending", "completed"], 3, 50.0),
    ([], 2, 0.0),
    (["completed"], 0, 100.0),
])
def test_summary_counts_active_progress_and_archive_separately(statuses, archived, rate):
    """Retain archive counts without treating archived work as active completion."""
    data = {
        "medium": [{"id": index + 1, "title": "Synthetic active", "status": status}
                   for index, status in enumerate(statuses)],
        "archive": [{"id": index + 100, "title": "Synthetic archived",
                     "status": "completed", "priority": "Low"} for index in range(archived)],
    }
    tasks = TaskList(data)
    before = tasks.to_dict()
    summary = get_task_summary(tasks)
    assert summary["total_tasks"] == len(statuses)
    assert summary["archived_tasks"] == archived
    assert summary["completion_rate"] == rate
    assert summary["status_breakdown"]["completed"] == statuses.count("completed")
    assert summary["priority_breakdown"]["Low"] == 0
    assert tasks.to_dict() == before
