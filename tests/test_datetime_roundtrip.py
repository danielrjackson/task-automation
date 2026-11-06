"""Task timestamp persistence must retain valid ISO strings and their offsets."""

from datetime import datetime

import pytest

from taskautomation.task_schema import Task


@pytest.mark.parametrize("value", [
    "2026-11-06T01:02:03Z",
    "2026-11-06T01:02:03.123456+00:00",
    "2026-11-06T01:02:03+05:30",
    "2026-11-06T01:02:03-04:00",
])
def test_timezone_aware_task_dates_roundtrip_without_loss(value):
    """Persisted dates must parse and preserve the original represented instant."""
    task = Task(dict(id=1, title="Synthetic task", created_date=value,
                     start_date=value, finish_date=value))
    serialized = task.to_dict()
    restored = Task(serialized)
    for name in ("created_date", "start_date", "finish_date"):
        assert getattr(restored, name) == getattr(task, name)
        assert "+00:00Z" not in serialized[name]
        assert datetime.fromisoformat(serialized[name]) == getattr(task, name)


def test_naive_task_dates_keep_legacy_utc_serialization():
    """Keep the existing UTC suffix policy for legacy naive timestamps."""
    value = "2026-11-06T01:02:03"
    task = Task(dict(id=1, title="Synthetic task", created_date=value, start_date=value))
    serialized = task.to_dict()
    assert serialized["created_date"] == serialized["start_date"] == value + "Z"
    assert serialized["finish_date"] is None
    assert Task(serialized).created_date.replace(tzinfo=None) == task.created_date


def test_default_created_timestamp_survives_persistence():
    """A task's generated creation date must survive its own serialized form."""
    task = Task(dict(id=1, title="Synthetic task"))
    assert Task(task.to_dict()).created_date == task.created_date
