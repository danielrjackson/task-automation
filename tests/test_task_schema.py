#!/usr/bin/env python3
"""
Test suite for task_schema module.

This module tests the schema definitions, validation functions,
data classes, and enums used for YAML-based task storage.
"""

from datetime import datetime

import pytest

from src.taskautomation.task_schema import (
    Priority,
    Subtask,
    Task,
    TaskList,
    TaskStatus,
    ValidationError,
    get_schema_example,
    validate_datetime,
    validate_integer,
    validate_list,
    validate_string,
)


class TestPriorityEnum:
    """Test Priority enum values and behavior."""

    def test_priority_values(self):
        """Test that all priority values are correct."""
        assert Priority.CRITICAL.value == "Critical"
        assert Priority.HIGH.value == "High"
        assert Priority.MEDIUM.value == "Medium"
        assert Priority.LOW.value == "Low"

    def test_priority_ordering(self):
        """Test priority enum ordering (if implemented)."""
        priorities = list(Priority)
        assert len(priorities) == 4
        assert Priority.CRITICAL in priorities
        assert Priority.LOW in priorities

    def test_priority_string_representation(self):
        """Test string representation of priorities."""
        assert str(Priority.CRITICAL) == "Critical"
        assert Priority.HIGH.value == "High"


class TestTaskStatusEnum:
    """Test TaskStatus enum values and behavior."""

    def test_task_status_values(self):
        """Test that all task status values are correct."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_count(self):
        """Test that we have all expected task statuses."""
        statuses = list(TaskStatus)
        assert len(statuses) == 5

        expected_values = {"pending", "in_progress", "completed", "blocked", "cancelled"}
        actual_values = {status.value for status in statuses}
        assert actual_values == expected_values


class TestValidationError:
    """Test ValidationError exception class."""

    def test_validation_error_creation(self):
        """Test creating ValidationError with message."""
        error = ValidationError("Test validation error")
        assert str(error) == "Test validation error"
        assert isinstance(error, Exception)

    def test_validation_error_inheritance(self):
        """Test that ValidationError inherits from Exception."""
        error = ValidationError("Test error")
        assert isinstance(error, Exception)

        # Should be catchable as Exception
        try:
            raise error
        except Exception as e:
            assert str(e) == "Test error"


class TestValidationFunctions:
    """Test validation utility functions."""

    def test_validate_string_valid(self):
        """Test validate_string with valid inputs."""
        # Valid strings
        assert validate_string("test", "field") == "test"
        assert validate_string("", "field") == ""
        assert validate_string("multi word string", "field") == "multi word string"

    def test_validate_string_invalid(self):
        """Test validate_string with invalid inputs."""
        with pytest.raises(ValidationError, match="Field 'field' must be a string"):
            validate_string(123, "field")

        with pytest.raises(ValidationError, match="Field 'field' must be a string"):
            validate_string(None, "field")

        with pytest.raises(ValidationError, match="Field 'field' must be a string"):
            validate_string([], "field")

    def test_validate_integer_valid(self):
        """Test validate_integer with valid inputs."""
        assert validate_integer(42, "field") == 42
        assert validate_integer(0, "field") == 0
        assert validate_integer(-5, "field") == -5

    def test_validate_integer_invalid(self):
        """Test validate_integer with invalid inputs."""
        with pytest.raises(ValidationError, match="Field 'field' must be an integer"):
            validate_integer("not_int", "field")

        with pytest.raises(ValidationError, match="Field 'field' must be an integer"):
            validate_integer(3.14, "field")

        with pytest.raises(ValidationError, match="Field 'field' must be an integer"):
            validate_integer(None, "field")

    def test_validate_datetime_valid(self):
        """Test validate_datetime with valid inputs."""
        # Valid ISO format strings
        result1 = validate_datetime("2023-12-25T10:30:00", "field")
        assert isinstance(result1, datetime)
        assert result1.year == 2023
        assert result1.month == 12
        assert result1.day == 25

        # With timezone
        result2 = validate_datetime("2023-12-25T10:30:00Z", "field")
        assert isinstance(result2, datetime)

        # Already datetime object
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result3 = validate_datetime(dt, "field")
        assert result3 == dt

    def test_validate_datetime_invalid(self):
        """Test validate_datetime with invalid inputs."""
        with pytest.raises(ValidationError, match="Field 'field' must be a valid ISO 8601 datetime string"):
            validate_datetime("invalid-date", "field")

        with pytest.raises(ValidationError, match="Field 'field' must be a valid ISO 8601 datetime string"):
            validate_datetime("2023-13-45", "field")

        with pytest.raises(ValidationError, match="Field 'field' must be a valid ISO 8601 datetime string"):
            validate_datetime(123, "field")

    def test_validate_datetime_none(self):
        """Test validate_datetime with None input."""
        result = validate_datetime(None, "field")
        assert result is None

    def test_validate_list_valid(self):
        """Test validate_list with valid inputs."""
        assert validate_list([], "field") == []
        assert validate_list([1, 2, 3], "field") == [1, 2, 3]
        assert validate_list(["a", "b"], "field") == ["a", "b"]

    def test_validate_list_invalid(self):
        """Test validate_list with invalid inputs."""
        with pytest.raises(ValidationError, match="Field 'field' must be a list"):
            validate_list("not_list", "field")

        with pytest.raises(ValidationError, match="Field 'field' must be a list"):
            validate_list(123, "field")

        with pytest.raises(ValidationError, match="Field 'field' must be a list"):
            validate_list({"key": "value"}, "field")

    def test_validate_list_none(self):
        """Test validate_list with None input."""
        result = validate_list(None, "field")
        assert result == []


class TestSubtask:
    """Test Subtask data class."""

    def test_subtask_creation_basic(self):
        """Test creating basic subtask."""
        subtask = Subtask({"name": "Test subtask", "completed": False})

        assert subtask.name == "Test subtask"
        assert subtask.completed is False

    def test_subtask_creation_completed(self):
        """Test creating completed subtask."""
        subtask = Subtask({"name": "Done subtask", "completed": True})

        assert subtask.name == "Done subtask"
        assert subtask.completed is True

    def test_subtask_missing_name(self):
        """Test subtask creation with missing name."""
        with pytest.raises(ValidationError, match="name.*required"):
            Subtask({})

    def test_subtask_invalid_name_type(self):
        """Test subtask creation with invalid name type."""
        with pytest.raises(ValidationError, match="Field 'name' must be a string"):
            Subtask({"name": 123, "completed": False})

    def test_subtask_invalid_completed_type(self):
        """Test subtask creation with invalid completed type."""
        with pytest.raises(ValidationError, match="Field 'completed' must be a boolean"):
            Subtask({"name": "Test", "completed": "not_bool"})

    def test_subtask_default_completed(self):
        """Test subtask with default completed value."""
        subtask = Subtask({"name": "Test subtask"})
        assert subtask.completed is False

    def test_subtask_to_dict(self):
        """Test converting subtask to dictionary."""
        subtask = Subtask({"name": "Test subtask", "completed": True})
        result = subtask.to_dict()

        expected = {"name": "Test subtask", "completed": True}
        assert result == expected

    def test_subtask_empty_name(self):
        """Test subtask with empty name string."""
        subtask = Subtask({"name": "", "completed": False})
        assert subtask.name == ""


class TestTask:
    """Test Task data class."""

    def test_task_creation_minimal(self):
        """Test creating task with minimal required fields."""
        task_data = {"id": 1, "title": "Test task", "status": "pending", "priority": "Medium"}
        task = Task(task_data)

        assert task.id == 1
        assert task.title == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == Priority.MEDIUM
        assert task.description == ""
        assert task.subtasks == []
        assert task.prerequisites == []

    def test_task_creation_full(self):
        """Test creating task with all fields."""
        task_data = {
            "id": 42,
            "title": "Complex task",
            "status": "in_progress",
            "priority": "High",
            "description": "A detailed description",
            "start_date": "2023-01-01T09:00:00",
            "finish_date": "2023-01-15T17:00:00",
            "estimated_time": "2 weeks",
            "subtasks": [
                {"name": "Subtask 1", "completed": True},
                {"name": "Subtask 2", "completed": False},
            ],
            "prerequisites": ["Previous task", "Setup task"],
        }
        task = Task(task_data)

        assert task.id == 42
        assert task.title == "Complex task"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.priority == Priority.HIGH
        assert task.description == "A detailed description"
        assert isinstance(task.start_date, datetime)
        assert isinstance(task.finish_date, datetime)
        assert task.estimated_time == "2 weeks"
        assert len(task.subtasks) == 2
        assert task.subtasks[0].name == "Subtask 1"
        assert task.subtasks[0].completed is True
        assert task.prerequisites == ["Previous task", "Setup task"]

    def test_task_missing_required_fields(self):
        """Test task creation with missing required fields."""
        # Missing id
        with pytest.raises(ValidationError, match="id.*required"):
            Task({"title": "Test", "status": "pending", "priority": "Medium"})

        # Missing title
        with pytest.raises(ValidationError, match="title.*required"):
            Task({"id": 1, "status": "pending", "priority": "Medium"})

        # Missing status
        with pytest.raises(ValidationError, match="status.*required"):
            Task({"id": 1, "title": "Test", "priority": "Medium"})

        # Missing priority
        with pytest.raises(ValidationError, match="priority.*required"):
            Task({"id": 1, "title": "Test", "status": "pending"})

    def test_task_invalid_status(self):
        """Test task creation with invalid status."""
        task_data = {
            "id": 1,
            "title": "Test task",
            "status": "invalid_status",
            "priority": "Medium",
        }
        with pytest.raises(ValidationError, match="Invalid status"):
            Task(task_data)

    def test_task_invalid_priority(self):
        """Test task creation with invalid priority."""
        task_data = {
            "id": 1,
            "title": "Test task",
            "status": "pending",
            "priority": "invalid_priority",
        }
        with pytest.raises(ValidationError, match="Invalid priority"):
            Task(task_data)

    def test_task_invalid_id_type(self):
        """Test task creation with invalid id type."""
        task_data = {
            "id": "not_int",
            "title": "Test task",
            "status": "pending",
            "priority": "Medium",
        }
        with pytest.raises(ValidationError, match="Field 'id' must be an integer"):
            Task(task_data)

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        task_data = {
            "id": 1,
            "title": "Test task",
            "status": "pending",
            "priority": "Medium",
            "description": "Test description",
            "subtasks": [{"name": "Sub1", "completed": True}],
            "prerequisites": ["Prereq1"],
        }
        task = Task(task_data)
        result = task.to_dict()

        assert result["id"] == 1
        assert result["title"] == "Test task"
        assert result["status"] == "pending"
        assert result["priority"] == "Medium"
        assert result["description"] == "Test description"
        assert len(result["subtasks"]) == 1
        assert result["subtasks"][0]["name"] == "Sub1"
        assert result["prerequisites"] == ["Prereq1"]

    def test_task_subtasks_validation(self):
        """Test task creation with invalid subtasks."""
        task_data = {
            "id": 1,
            "title": "Test task",
            "status": "pending",
            "priority": "Medium",
            "subtasks": "not_list",
        }
        with pytest.raises(ValidationError, match="Field 'subtasks' must be a list"):
            Task(task_data)


class TestTaskList:
    """Test TaskList data class."""

    def test_task_list_creation_empty(self):
        """Test creating empty task list."""
        task_list = TaskList({})

        assert task_list.critical == []
        assert task_list.high == []
        assert task_list.medium == []
        assert task_list.low == []
        assert task_list.archive == []
        assert task_list.metadata == {}

    def test_task_list_creation_with_tasks(self):
        """Test creating task list with tasks."""
        data = {
            "Critical": [
                {"id": 1, "title": "Critical task", "status": "pending", "priority": "Critical"}
            ],
            "High": [{"id": 2, "title": "High task", "status": "in_progress", "priority": "High"}],
            "Medium": [],
            "Low": [{"id": 3, "title": "Low task", "status": "completed", "priority": "Low"}],
            "archive": [
                {"id": 4, "title": "Archived task", "status": "completed", "priority": "Medium"}
            ],
        }
        task_list = TaskList(data)

        assert len(task_list.critical) == 1
        assert len(task_list.high) == 1
        assert len(task_list.medium) == 0
        assert len(task_list.low) == 1
        assert len(task_list.archive) == 1

        assert task_list.critical[0].title == "Critical task"
        assert task_list.high[0].status == TaskStatus.IN_PROGRESS
        assert task_list.low[0].priority == Priority.LOW

    def test_task_list_with_metadata(self):
        """Test creating task list with metadata."""
        data = {"metadata": {"version": "1.0", "created": "2023-01-01", "author": "Test User"}}
        task_list = TaskList(data)

        assert task_list.metadata["version"] == "1.0"
        assert task_list.metadata["created"] == "2023-01-01"
        assert task_list.metadata["author"] == "Test User"

    def test_task_list_invalid_task_data(self):
        """Test task list creation with invalid task data."""
        data = {
            "Critical": [
                {"id": "not_int", "title": "Bad task", "status": "pending", "priority": "Critical"}
            ]
        }
        with pytest.raises(ValidationError):
            TaskList(data)

    def test_task_list_get_all_tasks(self):
        """Test getting all tasks from task list."""
        data = {
            "Critical": [
                {"id": 1, "title": "Critical", "status": "pending", "priority": "Critical"}
            ],
            "High": [{"id": 2, "title": "High", "status": "pending", "priority": "High"}],
            "Medium": [{"id": 3, "title": "Medium", "status": "pending", "priority": "Medium"}],
            "Low": [{"id": 4, "title": "Low", "status": "pending", "priority": "Low"}],
        }
        task_list = TaskList(data)
        all_tasks = task_list.get_all_tasks()

        assert len(all_tasks) == 4
        task_ids = {task.id for task in all_tasks}
        assert task_ids == {1, 2, 3, 4}

    def test_task_list_to_dict(self):
        """Test converting task list to dictionary."""
        data = {
            "Critical": [
                {"id": 1, "title": "Critical", "status": "pending", "priority": "Critical"}
            ],
            "metadata": {"version": "1.0"},
        }
        task_list = TaskList(data)
        result = task_list.to_dict()

        assert "critical" in result
        assert "high" in result
        assert "medium" in result
        assert "low" in result
        assert "archive" in result
        assert "metadata" in result

        assert len(result["critical"]) == 1
        assert result["critical"][0]["title"] == "Critical"
        assert result["metadata"]["version"] == "1.0"

    def test_task_list_invalid_priority_section(self):
        """Test task list with invalid task in priority section."""
        data = {
            "High": [
                # Task with wrong priority for this section
                {"id": 1, "title": "Task", "status": "pending", "priority": "Low"}
            ]
        }
        with pytest.raises(ValidationError, match="priority mismatch"):
            TaskList(data)


class TestGetSchemaExample:
    """Test get_schema_example function."""

    def test_get_schema_example_structure(self):
        """Test that schema example has correct structure."""
        example = get_schema_example()

        assert isinstance(example, dict)
        assert "Critical" in example
        assert "High" in example
        assert "Medium" in example
        assert "Low" in example
        assert "archive" in example
        assert "metadata" in example

    def test_get_schema_example_tasks(self):
        """Test that schema example contains valid task examples."""
        example = get_schema_example()

        # Check that we have example tasks in different priorities
        assert isinstance(example["High"], list)
        assert len(example["High"]) > 0

        # Verify first task has required fields
        first_task = example["High"][0]
        assert "id" in first_task
        assert "title" in first_task
        assert "status" in first_task
        assert "priority" in first_task

        # Verify task can be created from example
        task = Task(first_task)
        assert task.id is not None
        assert task.title is not None

    def test_get_schema_example_metadata(self):
        """Test that schema example has proper metadata."""
        example = get_schema_example()

        metadata = example["metadata"]
        assert isinstance(metadata, dict)
        assert "version" in metadata
        assert "description" in metadata

    def test_get_schema_example_creates_valid_task_list(self):
        """Test that schema example can create valid TaskList."""
        example = get_schema_example()

        # Should not raise exception
        task_list = TaskList(example)
        assert isinstance(task_list, TaskList)

        # Should have some tasks
        all_tasks = task_list.get_all_tasks()
        assert len(all_tasks) > 0


class TestIntegration:
    """Integration tests combining multiple schema components."""

    def test_full_task_lifecycle(self):
        """Test creating, modifying, and converting full task structure."""
        # Create a complex task with subtasks
        task_data = {
            "id": 100,
            "title": "Integration test task",
            "status": "pending",
            "priority": "High",
            "description": "Full integration test",
            "subtasks": [
                {"name": "Setup", "completed": True},
                {"name": "Implementation", "completed": False},
                {"name": "Testing", "completed": False},
            ],
            "prerequisites": ["Environment setup"],
        }

        # Create task
        task = Task(task_data)
        assert task.id == 100
        assert len(task.subtasks) == 3

        # Convert back to dict
        task_dict = task.to_dict()
        assert task_dict["id"] == 100
        assert len(task_dict["subtasks"]) == 3

        # Create new task from dict (round-trip test)
        task2 = Task(task_dict)
        assert task2.title == task.title
        assert len(task2.subtasks) == len(task.subtasks)

    def test_task_list_with_all_priorities(self):
        """Test task list with tasks in all priority levels."""
        data = {
            "Critical": [
                {"id": 1, "title": "Critical 1", "status": "pending", "priority": "Critical"}
            ],
            "High": [
                {"id": 2, "title": "High 1", "status": "in_progress", "priority": "High"},
                {"id": 3, "title": "High 2", "status": "completed", "priority": "High"},
            ],
            "Medium": [{"id": 4, "title": "Medium 1", "status": "blocked", "priority": "Medium"}],
            "Low": [{"id": 5, "title": "Low 1", "status": "cancelled", "priority": "Low"}],
            "archive": [
                {"id": 6, "title": "Archived", "status": "completed", "priority": "Medium"}
            ],
        }

        task_list = TaskList(data)

        # Verify all tasks are accessible
        all_tasks = task_list.get_all_tasks()
        assert len(all_tasks) == 5  # archive not included in get_all_tasks

        # Verify different statuses
        statuses = {task.status for task in all_tasks}
        expected_statuses = {
            TaskStatus.PENDING,
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
            TaskStatus.BLOCKED,
            TaskStatus.CANCELLED,
        }
        assert statuses == expected_statuses

        # Verify conversion back to dict
        result_dict = task_list.to_dict()
        assert len(result_dict["critical"]) == 1
        assert len(result_dict["high"]) == 2
        assert len(result_dict["archive"]) == 1

    def test_validation_error_propagation(self):
        """Test that validation errors propagate correctly through nested structures."""
        # Invalid subtask should fail task creation
        task_data = {
            "id": 1,
            "title": "Test task",
            "status": "pending",
            "priority": "Medium",
            "subtasks": [
                {"name": "Valid subtask", "completed": True},
                {"name": 123, "completed": False},  # Invalid name type
            ],
        }

        with pytest.raises(ValidationError, match="Field 'name' must be a string"):
            Task(task_data)

        # Invalid task should fail task list creation
        list_data = {
            "Medium": [task_data]  # Contains invalid task
        }

        with pytest.raises(ValidationError):
            TaskList(list_data)
