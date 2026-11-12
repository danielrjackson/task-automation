#!/usr/bin/env python3
"""
Test suite for task_parser module.

This module tests YAML task parsing functionality including file parsing,
content parsing, task operations, and search capabilities.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from src.taskautomation.task_parser import (
    add_task_to_list,
    archive_task,
    find_tasks_by_criteria,
    get_task_summary,
    parse_yaml_content,
    parse_yaml_file,
    save_yaml_file,
    update_task_status,
    validate_yaml_structure,
)
from src.taskautomation.task_schema import (
    Priority,
    TaskList,
    TaskStatus,
    ValidationError,
)
from src.taskautomation.task_types import (
    ExitCode,
    OperationResult,
    TaskOperationResult,
)


class TestParseYamlFile:
    """Test parse_yaml_file function."""

    def test_parse_yaml_file_success(self):
        """Test successful YAML file parsing."""
        yaml_content = """
        medium:
          - id: 1
            title: "Test Task"
            status: "pending"
            priority: "Medium"
            description: "A test task"
        metadata:
          version: "1.0"
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            result = parse_yaml_file(temp_path)

            assert isinstance(result, TaskList)
            assert len(result.medium) == 1
            assert result.medium[0].title == "Test Task"
            assert result.medium[0].id == 1
            assert result.metadata.get("version") == "1.0"
        finally:
            Path(temp_path).unlink()

    def test_parse_yaml_file_empty_file(self):
        """Test parsing empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            result = parse_yaml_file(temp_path)

            assert isinstance(result, TaskList)
            assert len(result.get_all_tasks()) == 0
        finally:
            Path(temp_path).unlink()

    def test_parse_yaml_file_not_found(self):
        """Test parsing non-existent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            parse_yaml_file("/nonexistent/path/to/file.yaml")

        assert "Task file not found" in str(exc_info.value)

    def test_parse_yaml_file_invalid_yaml(self):
        """Test parsing file with invalid YAML syntax."""
        invalid_yaml = """
        tasks:
          - title: "Test Task"
            invalid: [unclosed list
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name

        try:
            with pytest.raises(ValidationError) as exc_info:
                parse_yaml_file(temp_path)

            assert "YAML parsing failed" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()

    @patch("pathlib.Path.open")
    def test_parse_yaml_file_io_error(self, mock_open_func):
        """Test handling of I/O errors during file parsing."""
        mock_open_func.side_effect = OSError("Permission denied")

        # Create a real file path to pass existence check
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name

        try:
            with pytest.raises(ValidationError) as exc_info:
                parse_yaml_file(temp_path)

            assert "File I/O error" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()

    def test_parse_yaml_file_validation_error(self):
        """Test parsing file with invalid task structure."""
        invalid_task_yaml = """
        medium:
          - id: "invalid_id"  # Should be integer
            title: "Test Task"
            status: "pending"
            priority: "Medium"
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_task_yaml)
            temp_path = f.name

        try:
            with pytest.raises(ValidationError):
                parse_yaml_file(temp_path)
        finally:
            Path(temp_path).unlink()


class TestParseYamlContent:
    """Test parse_yaml_content function."""

    def test_parse_yaml_content_success(self):
        """Test successful YAML content parsing."""
        yaml_content = """
        high:
          - id: 1
            title: "High Priority Task"
            status: "pending"
            priority: "High"
            description: "Important task"
            subtasks:
              - name: "Subtask 1"
                completed: true
              - name: "Subtask 2"
                completed: false
        """

        result = parse_yaml_content(yaml_content)

        assert isinstance(result, TaskList)
        assert len(result.high) == 1
        assert result.high[0].title == "High Priority Task"
        assert len(result.high[0].subtasks) == 2
        assert result.high[0].subtasks[0].completed is True

    def test_parse_yaml_content_empty(self):
        """Test parsing empty YAML content."""
        result = parse_yaml_content("")

        assert isinstance(result, TaskList)
        assert len(result.get_all_tasks()) == 0

    def test_parse_yaml_content_none(self):
        """Test parsing None content."""
        result = parse_yaml_content("null")

        assert isinstance(result, TaskList)
        assert len(result.get_all_tasks()) == 0

    def test_parse_yaml_content_invalid_syntax(self):
        """Test parsing content with invalid YAML syntax."""
        invalid_content = """
        tasks:
          - title: "Test"
            data: {unclosed: dict
        """

        with pytest.raises(ValidationError) as exc_info:
            parse_yaml_content(invalid_content)

        assert "YAML parsing failed" in str(exc_info.value)

    def test_parse_yaml_content_multiple_priorities(self):
        """Test parsing content with multiple priorities."""
        content = """
        critical:
          - id: 1
            title: "Critical Task"
            status: "pending"
            priority: "Critical"
        high:
          - id: 2
            title: "High Task"
            status: "in_progress"
            priority: "High"
        medium:
          - id: 3
            title: "Medium Task"
            status: "completed"
            priority: "Medium"
        low: []
        archive:
          - id: 4
            title: "Archived Task"
            status: "completed"
            priority: "Low"
        """

        result = parse_yaml_content(content)

        assert len(result.critical) == 1
        assert len(result.high) == 1
        assert len(result.medium) == 1
        assert len(result.low) == 0
        assert len(result.archive) == 1
        assert result.critical[0].title == "Critical Task"
        assert result.high[0].status == TaskStatus.IN_PROGRESS


class TestSaveYamlFile:
    """Test save_yaml_file function."""

    def test_save_yaml_file_success(self):
        """Test successful YAML file saving."""
        # Create a task list
        data = {
            "Medium": [{"id": 1, "title": "Test Task", "status": "pending", "priority": "Medium"}],
            "metadata": {"version": "1.0"},
        }
        task_list = TaskList(data)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_tasks.yaml"

            result = save_yaml_file(task_list, file_path, backup=False)

            assert result.success is True
            assert result.exit_code == ExitCode.SUCCESS
            assert "Successfully saved task list" in result.message
            assert file_path.exists()

            # Verify content
            with file_path.open("r") as f:
                saved_data = yaml.safe_load(f)

            assert saved_data["Medium"][0]["title"] == "Test Task"
            assert saved_data["metadata"]["version"] == "1.0"

    def test_save_yaml_file_with_backup(self):
        """Test saving YAML file with backup creation."""
        # Create initial file
        initial_data = {
            "Medium": [
                {"id": 1, "title": "Original Task", "status": "pending", "priority": "Medium"}
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_tasks.yaml"

            # Create initial file
            with file_path.open("w") as f:
                yaml.dump(initial_data, f)

            # Save new content with backup
            new_data = {
                "Medium": [
                    {"id": 2, "title": "Updated Task", "status": "pending", "priority": "Medium"}
                ]
            }
            new_task_list = TaskList(new_data)

            result = save_yaml_file(new_task_list, file_path, backup=True)

            assert result.success is True

            # Check backup file exists
            backup_path = file_path.with_suffix(".yaml.backup")
            assert backup_path.exists()

            # Verify backup contains original data
            with backup_path.open("r") as f:
                backup_data = yaml.safe_load(f)
            assert backup_data["Medium"][0]["title"] == "Original Task"

            # Verify main file has new data
            with file_path.open("r") as f:
                current_data = yaml.safe_load(f)
            assert current_data["Medium"][0]["title"] == "Updated Task"

    def test_save_yaml_file_directory_creation(self):
        """Test that parent directories are created."""
        data = {
            "Medium": [{"id": 1, "title": "Test Task", "status": "pending", "priority": "Medium"}]
        }
        task_list = TaskList(data)

        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "nested" / "dir" / "tasks.yaml"

            result = save_yaml_file(task_list, nested_path, backup=False)

            assert result.success is True
            assert nested_path.exists()
            assert nested_path.parent.exists()

    @patch("pathlib.Path.open")
    def test_save_yaml_file_io_error(self, mock_open_func):
        """Test handling of I/O errors during file saving."""
        mock_open_func.side_effect = OSError("Permission denied")

        data = {"Medium": []}
        task_list = TaskList(data)

        result = save_yaml_file(task_list, "test.yaml", backup=False)

        assert result.success is False
        assert result.exit_code == ExitCode.SYSTEM_ERROR
        assert "Failed to save YAML file" in result.message
        assert "Permission denied" in result.errors[0]

    def test_save_yaml_file_task_count_data(self):
        """Test that result data includes task count."""
        data = {
            "Critical": [{"id": 1, "title": "Task 1", "status": "pending", "priority": "Critical"}],
            "High": [
                {"id": 2, "title": "Task 2", "status": "pending", "priority": "High"},
                {"id": 3, "title": "Task 3", "status": "pending", "priority": "High"},
            ],
        }
        task_list = TaskList(data)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "tasks.yaml"

            result = save_yaml_file(task_list, file_path)

            assert result.success is True
            assert result.data["task_count"] == 3
            assert str(file_path) in result.data["file_path"]


class TestAddTaskToList:
    """Test add_task_to_list function."""

    def test_add_task_basic(self):
        """Test adding a basic task to task list."""
        task_list = TaskList({})

        result = add_task_to_list(
            task_list=task_list,
            title="New Task",
            priority=Priority.HIGH,
            description="Test description",
        )

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert "Successfully added task: New Task" in result.message
        assert len(result.modified_tasks) == 1

        added_task = result.modified_tasks[0]
        assert added_task.title == "New Task"
        assert added_task.priority == Priority.HIGH
        assert added_task.status == TaskStatus.PENDING
        assert added_task.description == "Test description"

        # Check task was added to correct priority list
        assert len(task_list.high) == 1
        assert task_list.high[0] == added_task

    def test_add_task_with_all_fields(self):
        """Test adding task with all optional fields."""
        task_list = TaskList({})

        subtasks_data = [
            {"name": "Subtask 1", "completed": False},
            {"name": "Subtask 2", "completed": True},
        ]

        result = add_task_to_list(
            task_list=task_list,
            title="Comprehensive Task",
            priority=Priority.CRITICAL,
            description="Detailed description",
            assignee="John Doe",
            estimated_time="2 hours",
            prerequisites=["Task A", "Task B"],
            subtasks=subtasks_data,
        )

        assert result.success is True
        added_task = result.modified_tasks[0]

        assert added_task.title == "Comprehensive Task"
        assert added_task.priority == Priority.CRITICAL
        assert added_task.assignee == "John Doe"
        assert added_task.estimated_time == "2 hours"
        assert added_task.prerequisites == ["Task A", "Task B"]
        assert len(added_task.subtasks) == 2
        assert added_task.subtasks[0].name == "Subtask 1"
        assert added_task.subtasks[1].completed is True

        # Check added to critical priority list
        assert len(task_list.critical) == 1

    def test_add_task_id_generation(self):
        """Test that task IDs are generated correctly."""
        # Create task list with existing tasks
        data = {
            "Medium": [
                {"id": 1, "title": "Existing Task 1", "status": "pending", "priority": "Medium"},
                {"id": 3, "title": "Existing Task 3", "status": "pending", "priority": "Medium"},
            ],
            "High": [
                {"id": 2, "title": "Existing Task 2", "status": "pending", "priority": "High"}
            ],
        }
        task_list = TaskList(data)

        result = add_task_to_list(task_list, "New Task", Priority.LOW)

        assert result.success is True
        added_task = result.modified_tasks[0]
        assert added_task.id == 4  # Should be next available ID

    def test_add_task_default_values(self):
        """Test adding task with default values."""
        task_list = TaskList({})

        result = add_task_to_list(task_list, "Minimal Task")

        assert result.success is True
        added_task = result.modified_tasks[0]

        assert added_task.title == "Minimal Task"
        assert added_task.priority == Priority.MEDIUM  # Default
        assert added_task.status == TaskStatus.PENDING
        assert added_task.description is None
        assert added_task.assignee is None
        assert added_task.estimated_time is None
        assert added_task.prerequisites == []
        assert added_task.subtasks == []

        # Should be added to medium priority list
        assert len(task_list.medium) == 1

    @patch("src.taskautomation.task_parser.Task")
    def test_add_task_validation_error(self, mock_task_class):
        """Test handling of validation errors during task creation."""
        mock_task_class.side_effect = ValidationError("Invalid task data")

        task_list = TaskList({})

        result = add_task_to_list(task_list, "Invalid Task")

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert "Failed to add task due to validation error" in result.message
        assert "Invalid task data" in result.errors[0]
        assert result.task_list == task_list


class TestUpdateTaskStatus:
    """Test update_task_status function."""

    def test_update_task_status_success(self):
        """Test successful task status update."""
        data = {
            "Medium": [{"id": 1, "title": "Test Task", "status": "pending", "priority": "Medium"}]
        }
        task_list = TaskList(data)

        result = update_task_status(task_list, 1, TaskStatus.IN_PROGRESS)

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert "Updated task 1 status from pending to in_progress" in result.message
        assert len(result.modified_tasks) == 1

        # Verify task status was updated
        updated_task = result.modified_tasks[0]
        assert updated_task.status == TaskStatus.IN_PROGRESS
        assert task_list.medium[0].status == TaskStatus.IN_PROGRESS

    def test_update_task_status_task_not_found(self):
        """Test updating status of non-existent task."""
        task_list = TaskList({})

        result = update_task_status(task_list, 999, TaskStatus.COMPLETED)

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert "Task with ID 999 not found" in result.message
        assert "No task found with ID: 999" in result.errors[0]
        assert result.task_list == task_list

    def test_update_task_status_all_statuses(self):
        """Test updating to all different status values."""
        data = {
            "High": [
                {"id": 1, "title": "Task 1", "status": "pending", "priority": "High"},
                {"id": 2, "title": "Task 2", "status": "pending", "priority": "High"},
                {"id": 3, "title": "Task 3", "status": "pending", "priority": "High"},
                {"id": 4, "title": "Task 4", "status": "pending", "priority": "High"},
            ]
        }
        task_list = TaskList(data)

        # Test each status transition
        statuses_to_test = [
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
            TaskStatus.BLOCKED,
            TaskStatus.PENDING,  # Back to pending
        ]

        for i, new_status in enumerate(statuses_to_test, 1):
            result = update_task_status(task_list, i, new_status)

            assert result.success is True
            assert task_list.high[i - 1].status == new_status

    @patch("src.taskautomation.task_parser.create_task_operation_error")
    def test_update_task_status_unexpected_error(self, mock_error_func):
        """Test handling of unexpected errors during status update."""
        # Create a mock task list that raises an exception
        mock_task_list = Mock()
        mock_task_list.get_task_by_id.side_effect = Exception("Unexpected error")

        mock_error_result = TaskOperationResult(
            success=False,
            exit_code=ExitCode.SYSTEM_ERROR,
            message="Error",
            task_list=mock_task_list,
            modified_tasks=[],
            errors=["Unexpected error"],
            warnings=[],
        )
        mock_error_func.return_value = mock_error_result

        result = update_task_status(mock_task_list, 1, TaskStatus.COMPLETED)

        assert result.success is False
        mock_error_func.assert_called_once()


class TestArchiveTask:
    """Test archive_task function."""

    def test_archive_task_success(self):
        """Test successful task archiving."""
        data = {
            "Medium": [
                {"id": 1, "title": "Task to Archive", "status": "completed", "priority": "Medium"}
            ]
        }
        task_list = TaskList(data)

        result = archive_task(task_list, 1)

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert "Successfully archived task: Task to Archive" in result.message
        assert len(result.modified_tasks) == 1

        # Verify task was moved to archive
        assert len(task_list.medium) == 0  # Task removed from active list
        assert len(task_list.archive) == 1  # Task added to archive
        assert task_list.archive[0].title == "Task to Archive"

    def test_archive_task_not_found(self):
        """Test archiving non-existent task."""
        task_list = TaskList({})

        result = archive_task(task_list, 999)

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert "Task with ID 999 not found" in result.message
        assert "No task found with ID: 999" in result.errors[0]

    def test_archive_task_from_different_priorities(self):
        """Test archiving tasks from different priority levels."""
        data = {
            "Critical": [
                {"id": 1, "title": "Critical Task", "status": "completed", "priority": "Critical"}
            ],
            "High": [{"id": 2, "title": "High Task", "status": "completed", "priority": "High"}],
            "Low": [{"id": 3, "title": "Low Task", "status": "completed", "priority": "Low"}],
        }
        task_list = TaskList(data)

        # Archive tasks from each priority level
        results = []
        for task_id in [1, 2, 3]:
            result = archive_task(task_list, task_id)
            results.append(result)
            assert result.success is True

        # Verify all tasks were archived
        assert len(task_list.critical) == 0
        assert len(task_list.high) == 0
        assert len(task_list.low) == 0
        assert len(task_list.archive) == 3

    @patch("src.taskautomation.task_parser.create_task_operation_error")
    def test_archive_task_archive_failure(self, mock_error_func):
        """Test handling when archive operation fails."""
        # Create a mock task list where archive_task returns False
        mock_task_list = Mock()
        mock_task = Mock()
        mock_task.title = "Test Task"
        mock_task_list.get_task_by_id.return_value = mock_task
        mock_task_list.archive_task.return_value = False  # Simulate failure

        mock_error_result = TaskOperationResult(
            success=False,
            exit_code=ExitCode.VALIDATION_ERROR,
            message="Archive failed",
            task_list=mock_task_list,
            modified_tasks=[],
            errors=["Cannot archive task"],
            warnings=[],
        )
        mock_error_func.return_value = mock_error_result

        result = archive_task(mock_task_list, 1)

        assert result.success is False
        mock_error_func.assert_called_once()


class TestFindTasksByCriteria:
    """Test find_tasks_by_criteria function."""

    def setup_method(self):
        """Set up test data."""
        data = {
            "Critical": [
                {
                    "id": 1,
                    "title": "Critical Task",
                    "status": "pending",
                    "priority": "Critical",
                    "assignee": "Alice",
                    "subtasks": [{"name": "Sub1", "completed": False}],
                }
            ],
            "High": [
                {
                    "id": 2,
                    "title": "High Task",
                    "status": "in_progress",
                    "priority": "High",
                    "assignee": "Bob",
                    "subtasks": [],
                },
                {
                    "id": 3,
                    "title": "Another High Task",
                    "status": "completed",
                    "priority": "High",
                    "assignee": "Alice",
                },
            ],
            "Medium": [
                {
                    "id": 4,
                    "title": "Medium Task",
                    "status": "blocked",
                    "priority": "Medium",
                    "assignee": "Charlie",
                }
            ],
            "archive": [
                {
                    "id": 5,
                    "title": "Archived Task",
                    "status": "completed",
                    "priority": "Low",
                    "assignee": "Alice",
                }
            ],
        }
        self.task_list = TaskList(data)

    def test_find_tasks_no_criteria(self):
        """Test finding tasks with no filter criteria."""
        results = find_tasks_by_criteria(self.task_list)

        assert len(results) == 4  # All active tasks (not archived)
        task_ids = [task.id for task in results]
        assert 1 in task_ids
        assert 2 in task_ids
        assert 3 in task_ids
        assert 4 in task_ids
        assert 5 not in task_ids  # Archived task excluded

    def test_find_tasks_by_priority(self):
        """Test finding tasks by priority."""
        high_tasks = find_tasks_by_criteria(self.task_list, priority=Priority.HIGH)

        assert len(high_tasks) == 2
        assert all(task.priority == Priority.HIGH for task in high_tasks)
        assert high_tasks[0].id in [2, 3]
        assert high_tasks[1].id in [2, 3]

    def test_find_tasks_by_status(self):
        """Test finding tasks by status."""
        pending_tasks = find_tasks_by_criteria(self.task_list, status=TaskStatus.PENDING)

        assert len(pending_tasks) == 1
        assert pending_tasks[0].id == 1
        assert pending_tasks[0].status == TaskStatus.PENDING

    def test_find_tasks_by_assignee(self):
        """Test finding tasks by assignee."""
        alice_tasks = find_tasks_by_criteria(self.task_list, assignee="Alice")

        assert len(alice_tasks) == 2
        assert all(task.assignee == "Alice" for task in alice_tasks)
        task_ids = [task.id for task in alice_tasks]
        assert 1 in task_ids
        assert 3 in task_ids

    def test_find_tasks_by_subtasks_presence(self):
        """Test finding tasks by presence of subtasks."""
        # Tasks with subtasks
        with_subtasks = find_tasks_by_criteria(self.task_list, has_subtasks=True)
        assert len(with_subtasks) == 1
        assert with_subtasks[0].id == 1

        # Tasks without subtasks
        without_subtasks = find_tasks_by_criteria(self.task_list, has_subtasks=False)
        assert len(without_subtasks) == 3
        task_ids = [task.id for task in without_subtasks]
        assert 2 in task_ids
        assert 3 in task_ids
        assert 4 in task_ids

    def test_find_tasks_include_archived(self):
        """Test finding tasks including archived ones."""
        results = find_tasks_by_criteria(self.task_list, include_archived=True)

        assert len(results) == 5  # All tasks including archived
        task_ids = [task.id for task in results]
        assert 5 in task_ids  # Archived task included

    def test_find_tasks_multiple_criteria(self):
        """Test finding tasks with multiple filter criteria."""
        results = find_tasks_by_criteria(
            self.task_list, priority=Priority.HIGH, assignee="Alice", status=TaskStatus.COMPLETED
        )

        assert len(results) == 1
        assert results[0].id == 3
        assert results[0].priority == Priority.HIGH
        assert results[0].assignee == "Alice"
        assert results[0].status == TaskStatus.COMPLETED

    def test_find_tasks_no_matches(self):
        """Test finding tasks with criteria that match nothing."""
        results = find_tasks_by_criteria(self.task_list, assignee="NonexistentUser")

        assert len(results) == 0

    def test_find_tasks_archived_by_assignee(self):
        """Test finding archived tasks by assignee."""
        results = find_tasks_by_criteria(self.task_list, assignee="Alice", include_archived=True)

        assert len(results) == 3  # 2 active + 1 archived
        archived_task = next((task for task in results if task.id == 5), None)
        assert archived_task is not None
        assert archived_task.assignee == "Alice"


class TestGetTaskSummary:
    """Test get_task_summary function."""

    def test_get_task_summary_comprehensive(self):
        """Test comprehensive task summary generation."""
        data = {
            "Critical": [
                {"id": 1, "title": "Critical 1", "status": "pending", "priority": "Critical"},
                {"id": 2, "title": "Critical 2", "status": "completed", "priority": "Critical"},
            ],
            "High": [{"id": 3, "title": "High 1", "status": "in_progress", "priority": "High"}],
            "Medium": [
                {"id": 4, "title": "Medium 1", "status": "blocked", "priority": "Medium"},
                {"id": 5, "title": "Medium 2", "status": "pending", "priority": "Medium"},
            ],
            "Low": [],
            "archive": [
                {"id": 6, "title": "Archived 1", "status": "completed", "priority": "Low"},
                {"id": 7, "title": "Archived 2", "status": "completed", "priority": "Medium"},
            ],
        }
        task_list = TaskList(data)

        summary = get_task_summary(task_list)

        # Check basic counts
        assert summary["total_tasks"] == 5  # Active tasks only
        assert summary["archived_tasks"] == 2

        # Check completion rate (1 completed out of 5 active = 20%)
        assert summary["completion_rate"] == 20.0

        # Check priority breakdown
        assert summary["priority_breakdown"]["Critical"] == 2
        assert summary["priority_breakdown"]["High"] == 1
        assert summary["priority_breakdown"]["Medium"] == 2
        assert summary["priority_breakdown"]["Low"] == 0

        # Check status breakdown
        assert summary["status_breakdown"]["pending"] == 2
        assert summary["status_breakdown"]["in_progress"] == 1
        assert summary["status_breakdown"]["completed"] == 1
        assert summary["status_breakdown"]["blocked"] == 1

        # Check specific status counts
        assert summary["pending_tasks"] == 2
        assert summary["in_progress_tasks"] == 1
        assert summary["blocked_tasks"] == 1

    def test_get_task_summary_empty_list(self):
        """Test summary of empty task list."""
        task_list = TaskList({})

        summary = get_task_summary(task_list)

        assert summary["total_tasks"] == 0
        assert summary["archived_tasks"] == 0
        assert summary["completion_rate"] == 0

        # All priority counts should be 0
        for priority in Priority:
            assert summary["priority_breakdown"][priority.value] == 0

        # All status counts should be 0
        for status in TaskStatus:
            assert summary["status_breakdown"][status.value] == 0

    def test_get_task_summary_all_completed(self):
        """Test summary with all tasks completed."""
        data = {
            "High": [
                {"id": 1, "title": "Task 1", "status": "completed", "priority": "High"},
                {"id": 2, "title": "Task 2", "status": "completed", "priority": "High"},
            ]
        }
        task_list = TaskList(data)

        summary = get_task_summary(task_list)

        assert summary["total_tasks"] == 2
        assert summary["completion_rate"] == 100.0
        assert summary["status_breakdown"]["completed"] == 2
        assert summary["pending_tasks"] == 0
        assert summary["in_progress_tasks"] == 0
        assert summary["blocked_tasks"] == 0

    def test_get_task_summary_rounding(self):
        """Test that completion rate is properly rounded."""
        data = {
            "Medium": [
                {"id": 1, "title": "Task 1", "status": "completed", "priority": "Medium"},
                {"id": 2, "title": "Task 2", "status": "pending", "priority": "Medium"},
                {"id": 3, "title": "Task 3", "status": "pending", "priority": "Medium"},
            ]
        }
        task_list = TaskList(data)

        summary = get_task_summary(task_list)

        # 1 completed out of 3 = 33.333...% -> should round to 33.33%
        assert summary["completion_rate"] == 33.33


class TestValidateYamlStructure:
    """Test validate_yaml_structure function."""

    def test_validate_yaml_structure_valid(self):
        """Test validation of valid YAML structure."""
        valid_content = """
        critical:
          - id: 1
            title: "Critical Task"
            status: "pending"
            priority: "Critical"
        medium:
          - id: 2
            title: "Medium Task"
            status: "completed"
            priority: "Medium"
        metadata:
          version: "1.0"
        """

        result = validate_yaml_structure(valid_content)

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert "YAML structure is valid" in result.message
        assert result.data["structure"] == "valid"
        assert result.data["task_count"] == 2
        assert result.data["archive_count"] == 0

    def test_validate_yaml_structure_empty(self):
        """Test validation of empty YAML content."""
        result = validate_yaml_structure("")

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert "Empty YAML content is valid" in result.message
        assert result.data["structure"] == "empty"
        assert len(result.warnings) == 1
        assert "Content is empty" in result.warnings[0]

    def test_validate_yaml_structure_null(self):
        """Test validation of null YAML content."""
        result = validate_yaml_structure("null")

        assert result.success is True
        assert result.data["structure"] == "empty"
        assert result.warnings == ["Content is empty"]

    def test_validate_yaml_structure_invalid_syntax(self):
        """Test validation of invalid YAML syntax."""
        invalid_content = """
        tasks:
          - title: "Test"
            invalid: [unclosed
        """

        result = validate_yaml_structure(invalid_content)

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert "YAML syntax error" in result.message
        assert len(result.errors) == 1
        assert "YAML parsing failed" in result.errors[0]

    def test_validate_yaml_structure_invalid_schema(self):
        """Test validation of invalid task schema."""
        invalid_schema_content = """
        medium:
          - id: "invalid_id"  # Should be integer
            title: "Test Task"
            status: "pending"
            priority: "Medium"
        """

        result = validate_yaml_structure(invalid_schema_content)

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert "YAML structure validation failed" in result.message
        assert len(result.errors) == 1

    def test_validate_yaml_structure_with_archive(self):
        """Test validation that includes archive count."""
        content_with_archive = """
        high:
          - id: 1
            title: "Active Task"
            status: "pending"
            priority: "High"
        archive:
          - id: 2
            title: "Archived Task"
            status: "completed"
            priority: "Medium"
          - id: 3
            title: "Another Archived"
            status: "completed"
            priority: "Low"
        """

        result = validate_yaml_structure(content_with_archive)

        assert result.success is True
        assert result.data["task_count"] == 1  # Active tasks only
        assert result.data["archive_count"] == 2

    @patch("src.taskautomation.task_parser.create_structured_error")
    def test_validate_yaml_structure_unexpected_error(self, mock_error_func):
        """Test handling of unexpected errors during validation."""
        mock_error_result = OperationResult(
            success=False,
            exit_code=ExitCode.SYSTEM_ERROR,
            message="Unexpected error",
            data={},
            errors=["Unexpected validation error"],
            warnings=[],
        )
        mock_error_func.return_value = mock_error_result

        # Patch TaskList to raise unexpected exception
        with patch("src.taskautomation.task_parser.TaskList") as mock_task_list:
            mock_task_list.side_effect = Exception("Unexpected error")

            result = validate_yaml_structure("valid: yaml")

            assert result.success is False
            mock_error_func.assert_called_once()


class TestIntegration:
    """Integration tests combining multiple parser functions."""

    def test_full_yaml_workflow(self):
        """Test complete workflow from parsing to saving."""
        # Create initial YAML content
        initial_content = """
        high:
          - id: 1
            title: "Initial Task"
            status: "pending"
            priority: "High"
            description: "First task"
        metadata:
          version: "1.0"
          author: "Test User"
        """

        # Parse content
        task_list = parse_yaml_content(initial_content)
        assert len(task_list.high) == 1
        assert task_list.high[0].title == "Initial Task"

        # Add a new task
        add_result = add_task_to_list(
            task_list,
            title="Added Task",
            priority=Priority.MEDIUM,
            description="Dynamically added task",
        )
        assert add_result.success is True
        assert len(task_list.medium) == 1

        # Update task status
        update_result = update_task_status(task_list, 1, TaskStatus.IN_PROGRESS)
        assert update_result.success is True
        assert task_list.high[0].status == TaskStatus.IN_PROGRESS

        # Save to file
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "workflow_test.yaml"
            save_result = save_yaml_file(task_list, file_path)
            assert save_result.success is True
            assert file_path.exists()

            # Re-parse saved file
            reloaded_task_list = parse_yaml_file(file_path)
            assert len(reloaded_task_list.high) == 1
            assert len(reloaded_task_list.medium) == 1
            assert reloaded_task_list.high[0].status == TaskStatus.IN_PROGRESS
            assert reloaded_task_list.medium[0].title == "Added Task"

    def test_search_and_archive_workflow(self):
        """Test workflow involving search and archiving."""
        data = {
            "Critical": [
                {"id": 1, "title": "Critical Done", "status": "completed", "priority": "Critical"},
            ],
            "High": [
                {"id": 2, "title": "High Done", "status": "completed", "priority": "High"},
                {"id": 3, "title": "High Pending", "status": "pending", "priority": "High"},
            ],
            "Medium": [
                {"id": 4, "title": "Medium Done", "status": "completed", "priority": "Medium"},
            ],
        }
        task_list = TaskList(data)

        # Find all completed tasks
        completed_tasks = find_tasks_by_criteria(task_list, status=TaskStatus.COMPLETED)
        assert len(completed_tasks) == 3

        # Archive all completed tasks
        for task in completed_tasks:
            archive_result = archive_task(task_list, task.id)
            assert archive_result.success is True

        # Verify results
        assert len(task_list.get_all_tasks()) == 1  # Only pending task left
        assert len(task_list.archive) == 3  # All completed tasks archived

        # Get summary
        summary = get_task_summary(task_list)
        assert summary["total_tasks"] == 1
        assert summary["archived_tasks"] == 3
        assert summary["completion_rate"] == 0  # No completed active tasks

    def test_validation_and_error_handling_workflow(self):
        """Test workflow with validation and error scenarios."""
        # Test invalid YAML
        invalid_yaml = "invalid: [unclosed"
        validation_result = validate_yaml_structure(invalid_yaml)
        assert validation_result.success is False

        # Test valid YAML with invalid task structure
        invalid_task_yaml = """
        medium:
          - id: "not_a_number"
            title: "Invalid Task"
            status: "pending"
            priority: "Medium"
        """
        validation_result = validate_yaml_structure(invalid_task_yaml)
        assert validation_result.success is False

        # Test operations on empty task list
        empty_task_list = TaskList({})

        # Try to update non-existent task
        update_result = update_task_status(empty_task_list, 999, TaskStatus.COMPLETED)
        assert update_result.success is False

        # Try to archive non-existent task
        archive_result = archive_task(empty_task_list, 999)
        assert archive_result.success is False

        # Search should return empty list
        search_results = find_tasks_by_criteria(empty_task_list)
        assert len(search_results) == 0

        # Summary should show zeros
        summary = get_task_summary(empty_task_list)
        assert summary["total_tasks"] == 0
        assert summary["completion_rate"] == 0
