#!/usr/bin/env python3
"""
Test suite for task_types module.

This module tests the core data structures, enums, named tuples,
and utility functions used throughout the task automation system.
"""

from unittest.mock import Mock

import pytest

from src.taskautomation.task_schema import (
    Priority,
    Subtask,
    Task,
    TaskList,
    TaskStatus,
)
from src.taskautomation.task_types import (
    ExitCode,
    OperationResult,
    SubtaskDict,
    TaskDict,
    TaskId,
    TaskListDict,
    TaskOperationResult,
    ValidationResult,
    create_structured_error,
    create_task_operation_error,
    create_validation_result,
    get_task_list_summary,
    get_task_summary,
    subtask_to_dict,
    task_list_to_dict,
    task_to_dict,
)


class TestExitCode:
    """Test ExitCode enum values and behavior."""

    def test_exit_code_values(self):
        """Test that all exit codes have expected integer values."""
        assert ExitCode.SUCCESS == 0
        assert ExitCode.NO_WORK == 1
        assert ExitCode.VALIDATION_ERROR == 2
        assert ExitCode.SYSTEM_ERROR == 3
        assert ExitCode.USER_ABORT == 4

    def test_exit_code_is_int_enum(self):
        """Test that ExitCode inherits from IntEnum."""
        assert isinstance(ExitCode.SUCCESS, int)
        assert ExitCode.SUCCESS + 1 == 1

    def test_exit_code_iteration(self):
        """Test that we can iterate over all exit codes."""
        codes = list(ExitCode)
        assert len(codes) == 5
        assert ExitCode.SUCCESS in codes
        assert ExitCode.USER_ABORT in codes


class TestValidationResult:
    """Test ValidationResult named tuple."""

    def test_validation_result_creation(self):
        """Test creating ValidationResult with all fields."""
        result = ValidationResult(
            is_valid=True,
            errors=["error1", "error2"],
            warnings=["warning1"],
            context={"key": "value"},
        )

        assert result.is_valid is True
        assert result.errors == ["error1", "error2"]
        assert result.warnings == ["warning1"]
        assert result.context == {"key": "value"}

    def test_validation_result_immutable(self):
        """Test that ValidationResult is immutable."""
        result = ValidationResult(True, [], [], {})

        with pytest.raises(AttributeError):
            result.is_valid = False

    def test_validation_result_field_access(self):
        """Test accessing fields by name and index."""
        result = ValidationResult(False, ["error"], ["warning"], {"test": True})

        # Access by name
        assert result.is_valid is False
        assert result.errors == ["error"]

        # Access by index
        assert result[0] is False
        assert result[1] == ["error"]


class TestOperationResult:
    """Test OperationResult named tuple."""

    def test_operation_result_creation(self):
        """Test creating OperationResult with all fields."""
        result = OperationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            message="Operation completed",
            data={"result": "success"},
            errors=[],
            warnings=["minor issue"],
        )

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert result.message == "Operation completed"
        assert result.data == {"result": "success"}
        assert result.errors == []
        assert result.warnings == ["minor issue"]

    def test_operation_result_with_error(self):
        """Test creating OperationResult for error case."""
        result = OperationResult(
            success=False,
            exit_code=ExitCode.VALIDATION_ERROR,
            message="Validation failed",
            data={},
            errors=["Invalid data"],
            warnings=[],
        )

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert result.errors == ["Invalid data"]


class TestTaskOperationResult:
    """Test TaskOperationResult named tuple."""

    def test_task_operation_result_creation(self):
        """Test creating TaskOperationResult with all fields."""
        mock_task_list = Mock(spec=TaskList)
        mock_task = Mock(spec=Task)

        result = TaskOperationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            message="Task operation completed",
            task_list=mock_task_list,
            modified_tasks=[mock_task],
            errors=[],
            warnings=[],
        )

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert result.message == "Task operation completed"
        assert result.task_list == mock_task_list
        assert result.modified_tasks == [mock_task]
        assert result.errors == []
        assert result.warnings == []

    def test_task_operation_result_none_task_list(self):
        """Test TaskOperationResult with None task_list."""
        result = TaskOperationResult(
            success=False,
            exit_code=ExitCode.SYSTEM_ERROR,
            message="Failed to load tasks",
            task_list=None,
            modified_tasks=[],
            errors=["File not found"],
            warnings=[],
        )

        assert result.task_list is None
        assert result.errors == ["File not found"]


class TestCreateStructuredError:
    """Test create_structured_error function."""

    def test_create_structured_error_basic(self):
        """Test creating basic structured error."""
        result = create_structured_error("Test error", ExitCode.VALIDATION_ERROR)

        assert isinstance(result, OperationResult)
        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert result.message == "Test error"
        assert result.data == {}
        assert result.errors == []
        assert result.warnings == []

    def test_create_structured_error_with_details(self):
        """Test creating structured error with errors and context."""
        errors = ["Error 1", "Error 2"]
        context = {"file": "test.yaml", "line": 42}

        result = create_structured_error(
            "Validation failed", ExitCode.VALIDATION_ERROR, errors=errors, context=context
        )

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert result.message == "Validation failed"
        assert result.data == context
        assert result.errors == errors
        assert result.warnings == []

    def test_create_structured_error_none_values(self):
        """Test creating structured error with None values."""
        result = create_structured_error(
            "Test error", ExitCode.SYSTEM_ERROR, errors=None, context=None
        )

        assert result.data == {}
        assert result.errors == []


class TestCreateTaskOperationError:
    """Test create_task_operation_error function."""

    def test_create_task_operation_error_basic(self):
        """Test creating basic task operation error."""
        result = create_task_operation_error("Task operation failed", ExitCode.SYSTEM_ERROR)

        assert isinstance(result, TaskOperationResult)
        assert result.success is False
        assert result.exit_code == ExitCode.SYSTEM_ERROR
        assert result.message == "Task operation failed"
        assert result.task_list is None
        assert result.modified_tasks == []
        assert result.errors == []
        assert result.warnings == []

    def test_create_task_operation_error_with_details(self):
        """Test creating task operation error with errors and task list."""
        mock_task_list = Mock(spec=TaskList)
        errors = ["Error 1", "Error 2"]

        result = create_task_operation_error(
            "Operation failed", ExitCode.VALIDATION_ERROR, errors=errors, task_list=mock_task_list
        )

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert result.message == "Operation failed"
        assert result.task_list == mock_task_list
        assert result.modified_tasks == []
        assert result.errors == errors
        assert result.warnings == []


class TestCreateValidationResult:
    """Test create_validation_result function."""

    def test_create_validation_result_valid(self):
        """Test creating validation result for valid case."""
        result = create_validation_result(True)

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.context == {}

    def test_create_validation_result_invalid(self):
        """Test creating validation result for invalid case."""
        errors = ["Error 1", "Error 2"]
        warnings = ["Warning 1"]
        context = {"file": "test.yaml"}

        result = create_validation_result(False, errors=errors, warnings=warnings, context=context)

        assert result.is_valid is False
        assert result.errors == errors
        assert result.warnings == warnings
        assert result.context == context

    def test_create_validation_result_none_values(self):
        """Test creating validation result with None values."""
        result = create_validation_result(True, errors=None, warnings=None, context=None)

        assert result.errors == []
        assert result.warnings == []
        assert result.context == {}


class TestConversionFunctions:
    """Test task/subtask/task_list conversion functions."""

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        # Create a mock task with to_dict method
        mock_task = Mock(spec=Task)
        expected_dict = {"id": 1, "title": "Test Task", "status": "pending", "priority": "Medium"}
        mock_task.to_dict.return_value = expected_dict

        result = task_to_dict(mock_task)

        assert result == expected_dict
        mock_task.to_dict.assert_called_once()

    def test_subtask_to_dict(self):
        """Test converting subtask to dictionary."""
        # Create a mock subtask with to_dict method
        mock_subtask = Mock(spec=Subtask)
        expected_dict = {"name": "Test Subtask", "completed": False}
        mock_subtask.to_dict.return_value = expected_dict

        result = subtask_to_dict(mock_subtask)

        assert result == expected_dict
        mock_subtask.to_dict.assert_called_once()

    def test_task_list_to_dict(self):
        """Test converting task list to dictionary."""
        # Create a mock task list with to_dict method
        mock_task_list = Mock(spec=TaskList)
        expected_dict = {"Critical": [], "High": [], "Medium": [], "Low": [], "archive": []}
        mock_task_list.to_dict.return_value = expected_dict

        result = task_list_to_dict(mock_task_list)

        assert result == expected_dict
        mock_task_list.to_dict.assert_called_once()


class TestSummaryFunctions:
    """Test task summary functions."""

    def test_get_task_summary(self):
        """Test getting task summary string."""
        # Create a mock task
        mock_task = Mock(spec=Task)
        mock_task.id = 42
        mock_task.title = "Complete project"
        mock_task.status = Mock()
        mock_task.status.value = "in_progress"
        mock_task.priority = Mock()
        mock_task.priority.value = "High"

        result = get_task_summary(mock_task)

        expected = "42: Complete project [in_progress] (high)"
        assert result == expected

    def test_get_task_list_summary(self):
        """Test getting task list summary statistics."""
        # Create mock tasks with different statuses and priorities
        mock_task1 = Mock(spec=Task)
        mock_task1.status = TaskStatus.PENDING
        mock_task1.priority = Priority.HIGH

        mock_task2 = Mock(spec=Task)
        mock_task2.status = TaskStatus.COMPLETED
        mock_task2.priority = Priority.MEDIUM

        mock_task3 = Mock(spec=Task)
        mock_task3.status = TaskStatus.IN_PROGRESS
        mock_task3.priority = Priority.HIGH

        # Create mock task list
        mock_task_list = Mock(spec=TaskList)
        mock_task_list.get_all_tasks.return_value = [mock_task1, mock_task2, mock_task3]
        mock_task_list.archive = [Mock(), Mock()]  # 2 archived tasks

        result = get_task_list_summary(mock_task_list)

        assert result["total_tasks"] == 3
        assert result["archived_tasks"] == 2

        # Check status counts
        status_counts = result["status_counts"]
        assert status_counts["pending"] == 1
        assert status_counts["completed"] == 1
        assert status_counts["in_progress"] == 1
        assert status_counts["blocked"] == 0
        assert status_counts["cancelled"] == 0

        # Check priority counts
        priority_counts = result["priority_counts"]
        assert priority_counts["High"] == 2
        assert priority_counts["Medium"] == 1
        assert priority_counts["Low"] == 0
        assert priority_counts["Critical"] == 0

    def test_get_task_list_summary_empty(self):
        """Test getting summary for empty task list."""
        mock_task_list = Mock(spec=TaskList)
        mock_task_list.get_all_tasks.return_value = []
        mock_task_list.archive = []

        result = get_task_list_summary(mock_task_list)

        assert result["total_tasks"] == 0
        assert result["archived_tasks"] == 0

        # All counts should be zero
        for status in TaskStatus:
            assert result["status_counts"][status.value] == 0

        for priority in Priority:
            assert result["priority_counts"][priority.value] == 0


class TestTypeAliases:
    """Test that type aliases are properly defined."""

    def test_type_aliases_exist(self):
        """Test that all type aliases are defined."""
        # These should not raise AttributeErrors
        assert TaskId is not None
        assert TaskDict is not None
        assert SubtaskDict is not None
        assert TaskListDict is not None

    def test_task_id_is_int_alias(self):
        """Test that TaskId is an alias for int."""
        # This is mainly for documentation/type checking
        # but we can verify the alias exists
        test_id: TaskId = 42
        assert isinstance(test_id, int)

    def test_dict_aliases_are_dict_types(self):
        """Test that dict aliases work with dict types."""
        test_task_dict: TaskDict = {"id": 1, "title": "test"}
        test_subtask_dict: SubtaskDict = {"name": "subtask", "completed": True}
        test_task_list_dict: TaskListDict = {"Critical": [], "High": []}

        assert isinstance(test_task_dict, dict)
        assert isinstance(test_subtask_dict, dict)
        assert isinstance(test_task_list_dict, dict)


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_error_creation_and_access(self):
        """Test creating errors and accessing their fields."""
        # Create a structured error
        error_result = create_structured_error(
            "Integration test error",
            ExitCode.VALIDATION_ERROR,
            errors=["Field missing", "Invalid format"],
            context={"test": "integration"},
        )

        # Verify we can access all fields
        assert not error_result.success
        assert error_result.exit_code == ExitCode.VALIDATION_ERROR
        assert len(error_result.errors) == 2
        assert "test" in error_result.data

    def test_validation_result_with_context(self):
        """Test validation result with exit code context."""
        result = create_validation_result(
            False, errors=["Validation failed"], context={"exit_code": ExitCode.VALIDATION_ERROR}
        )

        assert not result.is_valid
        assert result.context["exit_code"] == ExitCode.VALIDATION_ERROR

    def test_all_exit_codes_in_results(self):
        """Test that all exit codes can be used in results."""
        for exit_code in ExitCode:
            result = create_structured_error("Test", exit_code)
            assert result.exit_code == exit_code
            assert isinstance(result.exit_code, ExitCode)
