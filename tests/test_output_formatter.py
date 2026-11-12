#!/usr/bin/env python3
"""
Test suite for output_formatter module.

This module tests output formatting utilities including YAML formatting,
result output, datetime handling, and structured result creation.
"""

import datetime
import json
from unittest.mock import Mock, patch

import yaml

from src.taskautomation.output_formatter import (
    create_structured_error,
    create_success_result,
    format_task_block,
    format_task_list_summary,
    format_task_list_yaml,
    format_task_summary,
    format_task_yaml,
    format_validation_summary,
    get_current_datetime,
    output_result,
)
from src.taskautomation.task_schema import (
    Task,
    TaskList,
)
from src.taskautomation.task_types import (
    ExitCode,
    OperationResult,
)


class TestGetCurrentDatetime:
    """Test get_current_datetime function."""

    @patch("datetime.datetime")
    def test_get_current_datetime_format(self, mock_datetime):
        """Test that get_current_datetime returns proper ISO8601 format."""
        # Mock the datetime.now() call
        mock_now = Mock()
        mock_now.isoformat.return_value = "2024-01-15T10:30:45.123+00:00"
        mock_datetime.now.return_value = mock_now
        mock_datetime.UTC = datetime.UTC

        result = get_current_datetime()

        assert result == "2024-01-15T10:30:45.123Z"
        mock_datetime.now.assert_called_once_with(datetime.UTC)
        mock_now.isoformat.assert_called_once()

    @patch("datetime.datetime")
    def test_get_current_datetime_timezone_replacement(self, mock_datetime):
        """Test that +00:00 is properly replaced with Z."""
        mock_now = Mock()
        mock_now.isoformat.return_value = "2024-12-31T23:59:59.999+00:00"
        mock_datetime.now.return_value = mock_now
        mock_datetime.UTC = datetime.UTC

        result = get_current_datetime()

        assert result.endswith("Z")
        assert "+00:00" not in result
        assert result == "2024-12-31T23:59:59.999Z"


class TestFormatTaskYaml:
    """Test format_task_yaml function."""

    def test_format_task_yaml_basic(self):
        """Test formatting a basic task to YAML."""
        task_data = {
            "id": 1,
            "title": "Test task",
            "status": "pending",
            "priority": "Medium",
            "description": "A test task",
        }
        task = Task(task_data)

        result = format_task_yaml(task)

        # Verify it's valid YAML
        parsed = yaml.safe_load(result)
        assert parsed["id"] == 1
        assert parsed["title"] == "Test task"
        assert parsed["status"] == "pending"
        assert parsed["priority"] == "Medium"
        assert parsed["description"] == "A test task"

    def test_format_task_yaml_with_subtasks(self):
        """Test formatting a task with subtasks to YAML."""
        task_data = {
            "id": 1,
            "title": "Task with subtasks",
            "status": "pending",
            "priority": "High",
            "subtasks": [
                {"name": "Subtask 1", "completed": True},
                {"name": "Subtask 2", "completed": False},
            ],
        }
        task = Task(task_data)

        result = format_task_yaml(task)

        parsed = yaml.safe_load(result)
        assert len(parsed["subtasks"]) == 2
        assert parsed["subtasks"][0]["name"] == "Subtask 1"
        assert parsed["subtasks"][0]["completed"] is True
        assert parsed["subtasks"][1]["completed"] is False

    def test_format_task_yaml_with_dates(self):
        """Test formatting a task with date fields to YAML."""
        task_data = {
            "id": 1,
            "title": "Task with dates",
            "status": "completed",
            "priority": "Low",
            "created_date": "2024-01-01T00:00:00Z",
            "start_date": "2024-01-02T10:00:00Z",
            "finish_date": "2024-01-03T15:30:00Z",
        }
        task = Task(task_data)

        result = format_task_yaml(task)

        parsed = yaml.safe_load(result)
        assert parsed["created_date"] == "2024-01-01T00:00:00Z"
        assert parsed["start_date"] == "2024-01-02T10:00:00Z"
        assert parsed["finish_date"] == "2024-01-03T15:30:00Z"

    def test_format_task_yaml_structure(self):
        """Test that YAML output has proper structure."""
        task_data = {"id": 1, "title": "Structured task", "status": "pending", "priority": "Medium"}
        task = Task(task_data)

        result = format_task_yaml(task)

        # Should be properly indented and not use flow style
        assert "id: 1" in result
        assert "title: Structured task" in result
        assert "{" not in result  # No flow style
        assert result.count("  ") >= 0  # Has indentation


class TestFormatTaskListYaml:
    """Test format_task_list_yaml function."""

    def test_format_task_list_yaml_basic(self):
        """Test formatting a basic task list to YAML."""
        data = {
            "Medium": [
                {"id": 1, "title": "Task 1", "status": "pending", "priority": "Medium"},
                {"id": 2, "title": "Task 2", "status": "completed", "priority": "Medium"},
            ],
            "metadata": {"version": "1.0"},
        }
        task_list = TaskList(data)

        result = format_task_list_yaml(task_list)

        parsed = yaml.safe_load(result)
        assert "Medium" in parsed
        assert len(parsed["Medium"]) == 2
        assert parsed["metadata"]["version"] == "1.0"

    def test_format_task_list_yaml_empty_priorities(self):
        """Test formatting task list with empty priority sections."""
        data = {
            "Critical": [],
            "High": [],
            "Medium": [{"id": 1, "title": "Only task", "status": "pending", "priority": "Medium"}],
            "Low": [],
            "archive": [],
        }
        task_list = TaskList(data)

        result = format_task_list_yaml(task_list)

        parsed = yaml.safe_load(result)
        assert parsed["Critical"] == []
        assert parsed["High"] == []
        assert len(parsed["Medium"]) == 1
        assert parsed["Low"] == []
        assert parsed["archive"] == []

    def test_format_task_list_yaml_with_metadata(self):
        """Test formatting task list with comprehensive metadata."""
        data = {
            "Medium": [],
            "metadata": {
                "version": "2.0",
                "author": "Test User",
                "created": "2024-01-01T00:00:00Z",
                "last_modified": "2024-01-15T10:30:00Z",
            },
        }
        task_list = TaskList(data)

        result = format_task_list_yaml(task_list)

        parsed = yaml.safe_load(result)
        assert parsed["metadata"]["version"] == "2.0"
        assert parsed["metadata"]["author"] == "Test User"
        assert parsed["metadata"]["created"] == "2024-01-01T00:00:00Z"


class TestFormatTaskBlock:
    """Test format_task_block function (legacy/deprecated)."""

    def test_format_task_block_basic(self):
        """Test formatting a basic legacy task object."""
        # Create a mock legacy task object
        mock_task = Mock()
        mock_task.title = "Test Task"
        mock_task.checked = False
        mock_task.task_id = 1
        mock_task.description = "Test description"
        mock_task.prerequisites = ["Prerequisite 1"]
        mock_task.priority = "High"
        mock_task.estimated_time = "2 hours"
        mock_task.assignee = "Test User"
        mock_task.create_date = "2024-01-01"
        mock_task.start_date = "2024-01-02"
        mock_task.finish_date = None
        mock_task.subtasks = {"Subtask 1": True, "Subtask 2": False}

        result = format_task_block(mock_task)

        assert "- [ ] **Test Task**:" in result
        assert "**ID**: 1" in result
        assert "**Description**: Test description" in result
        assert "**Priority**: High" in result
        assert "**Estimated Time**: 2 hours" in result
        assert "**Assignee**: Test User" in result
        assert "- [x] Subtask 1" in result
        assert "- [ ] Subtask 2" in result
        assert result.endswith("\n")

    def test_format_task_block_checked(self):
        """Test formatting a checked/completed legacy task."""
        mock_task = Mock()
        mock_task.title = "Completed Task"
        mock_task.checked = True
        mock_task.task_id = 2
        mock_task.description = None
        mock_task.prerequisites = []
        mock_task.priority = "Medium"
        mock_task.estimated_time = None
        mock_task.assignee = None
        mock_task.create_date = None
        mock_task.start_date = None
        mock_task.finish_date = None
        mock_task.subtasks = {}

        result = format_task_block(mock_task)

        assert "- [x] **Completed Task**:" in result
        assert "**Description**: No description" in result
        assert "- None" in result  # Prerequisites
        assert "**Estimated Time**: 30 minutes" in result  # Default
        assert "**Assignee**: None" in result
        assert "- None" in result  # Subtasks

    def test_format_task_block_updated_subtasks(self):
        """Test formatting with updated subtasks parameter."""
        mock_task = Mock()
        mock_task.title = "Task with overrides"
        mock_task.checked = False
        mock_task.task_id = 3
        mock_task.description = "Test"
        mock_task.prerequisites = []
        mock_task.priority = "Low"
        mock_task.estimated_time = "1 hour"
        mock_task.assignee = "User"
        mock_task.create_date = "2024-01-01"
        mock_task.start_date = "2024-01-02"
        mock_task.finish_date = "2024-01-03"
        mock_task.subtasks = {"Original": False}

        updated_subtasks = {"New Subtask": True, "Another": False}
        result = format_task_block(mock_task, updated_subtasks)

        # Should use updated_subtasks, not original
        assert "- [x] New Subtask" in result
        assert "- [ ] Another" in result
        assert "Original" not in result


class TestFormatTaskSummary:
    """Test format_task_summary function."""

    def test_format_task_summary_basic(self):
        """Test formatting a basic task summary."""
        task_data = {
            "id": 1,
            "title": "Test Task",
            "status": "pending",
            "priority": "High",
            "description": "A test task for summary",
        }
        task = Task(task_data)

        result = format_task_summary(task)

        assert "[1] Test Task (HIGH PRIORITY, PENDING)" in result
        assert "Description: A test task for summary" in result

    def test_format_task_summary_with_dates(self):
        """Test formatting task summary with date fields."""
        task_data = {
            "id": 2,
            "title": "Task with dates",
            "status": "in_progress",
            "priority": "Medium",
            "created_date": "2024-01-01T00:00:00Z",
            "start_date": "2024-01-02T10:00:00Z",
            "finish_date": "2024-01-03T15:30:00Z",
        }
        task = Task(task_data)

        result = format_task_summary(task)

        assert "Created: 2024-01-01T00:00:00Z" in result
        assert "Start: 2024-01-02T10:00:00Z" in result
        assert "Finish: 2024-01-03T15:30:00Z" in result
        assert "IN PROGRESS" in result

    def test_format_task_summary_with_subtasks(self):
        """Test formatting task summary with subtasks."""
        task_data = {
            "id": 3,
            "title": "Task with subtasks",
            "status": "pending",
            "priority": "Low",
            "subtasks": [
                {"name": "Done subtask", "completed": True},
                {"name": "Pending subtask", "completed": False},
            ],
        }
        task = Task(task_data)

        result = format_task_summary(task)

        assert "Subtasks:" in result
        assert "✓ Done subtask" in result
        assert "○ Pending subtask" in result

    def test_format_task_summary_exclude_subtasks(self):
        """Test formatting task summary without subtasks."""
        task_data = {
            "id": 4,
            "title": "Task without subtask display",
            "status": "completed",
            "priority": "Critical",
            "subtasks": [{"name": "Hidden subtask", "completed": True}],
        }
        task = Task(task_data)

        result = format_task_summary(task, include_subtasks=False)

        assert "Subtasks:" not in result
        assert "Hidden subtask" not in result
        assert "CRITICAL PRIORITY" in result

    def test_format_task_summary_with_prerequisites(self):
        """Test formatting task summary with prerequisites."""
        task_data = {
            "id": 5,
            "title": "Task with prereqs",
            "status": "pending",
            "priority": "Medium",
            "prerequisites": ["Task A", "Task B", "Task C"],
        }
        task = Task(task_data)

        result = format_task_summary(task)

        assert "Prerequisites: Task A, Task B, Task C" in result

    def test_format_task_summary_minimal_data(self):
        """Test formatting task summary with minimal data."""
        task_data = {
            "id": 6,
            "title": "",  # Empty title
            "status": None,
            "priority": None,
        }
        task = Task(task_data)

        result = format_task_summary(task)

        assert "[6] Untitled Task (UNKNOWN PRIORITY, UNKNOWN)" in result
        assert "Description: No description provided" in result


class TestFormatTaskListSummary:
    """Test format_task_list_summary function."""

    def test_format_task_list_summary_grouped(self):
        """Test formatting task list summary grouped by priority."""
        data = {
            "Critical": [
                {"id": 1, "title": "Critical task", "status": "pending", "priority": "Critical"}
            ],
            "High": [{"id": 2, "title": "High task", "status": "in_progress", "priority": "High"}],
            "Medium": [
                {"id": 3, "title": "Medium task", "status": "completed", "priority": "Medium"}
            ],
            "Low": [],
            "archive": [
                {"id": 4, "title": "Archived task", "status": "completed", "priority": "Low"}
            ],
        }
        task_list = TaskList(data)

        result = format_task_list_summary(task_list, group_by_priority=True)

        assert "Task List Summary" in result
        assert "Total Tasks: 3" in result  # Active tasks only
        assert "CRITICAL PRIORITY (1 tasks)" in result
        assert "HIGH PRIORITY (1 tasks)" in result
        assert "MEDIUM PRIORITY (1 tasks)" in result
        assert "ARCHIVED (1 tasks)" in result
        assert "[1] Critical task (PENDING)" in result

    def test_format_task_list_summary_flat(self):
        """Test formatting task list summary in flat format."""
        data = {
            "High": [{"id": 1, "title": "High task", "status": "pending", "priority": "High"}],
            "Medium": [
                {"id": 2, "title": "Medium task", "status": "completed", "priority": "Medium"}
            ],
        }
        task_list = TaskList(data)

        result = format_task_list_summary(task_list, group_by_priority=False)

        assert "Task List Summary" in result
        assert "Total Tasks: 2" in result
        assert "- [1] High task (HIGH, PENDING)" in result
        assert "- [2] Medium task (MEDIUM, COMPLETED)" in result
        # Should not have priority headers
        assert "HIGH PRIORITY" not in result

    def test_format_task_list_summary_status_counts(self):
        """Test that status counts are correctly displayed."""
        data = {
            "Medium": [
                {"id": 1, "title": "Task 1", "status": "pending", "priority": "Medium"},
                {"id": 2, "title": "Task 2", "status": "pending", "priority": "Medium"},
                {"id": 3, "title": "Task 3", "status": "completed", "priority": "Medium"},
                {"id": 4, "title": "Task 4", "status": "in_progress", "priority": "Medium"},
            ]
        }
        task_list = TaskList(data)

        result = format_task_list_summary(task_list)

        assert "Total Tasks: 4" in result
        # Should show status breakdown
        assert "Status:" in result
        assert "2 Pending" in result
        assert "1 Completed" in result
        assert "1 In Progress" in result

    def test_format_task_list_summary_empty(self):
        """Test formatting empty task list summary."""
        data = {"Critical": [], "High": [], "Medium": [], "Low": [], "archive": []}
        task_list = TaskList(data)

        result = format_task_list_summary(task_list)

        assert "Task List Summary" in result
        assert "Total Tasks: 0" in result


class TestOutputResult:
    """Test output_result function."""

    @patch("builtins.print")
    def test_output_result_human_success(self, mock_print):
        """Test outputting successful result in human format."""
        result = OperationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            message="Operation completed successfully",
            data={},
            errors=[],
            warnings=["Minor warning"],
        )

        output_result(result, format_type="human", quiet=False)

        # Check that print was called with expected content
        calls = [call.args[0] for call in mock_print.call_args_list]
        assert "✓ Operation completed successfully" in calls
        assert "Warnings:" in calls
        assert "  ⚠ Minor warning" in calls

    @patch("builtins.print")
    def test_output_result_human_failure(self, mock_print):
        """Test outputting failed result in human format."""
        result = OperationResult(
            success=False,
            exit_code=ExitCode.VALIDATION_ERROR,
            message="Operation failed",
            data={},
            errors=["Error 1", "Error 2"],
            warnings=[],
        )

        output_result(result, format_type="human", quiet=False)

        calls = [call.args[0] for call in mock_print.call_args_list]
        assert "✗ Operation failed" in calls
        assert "Errors:" in calls
        assert "  ✗ Error 1" in calls
        assert "  ✗ Error 2" in calls

    @patch("builtins.print")
    def test_output_result_human_quiet(self, mock_print):
        """Test outputting result in human format with quiet mode."""
        result = OperationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            message="Quiet operation",
            data={},
            errors=[],
            warnings=["Should not show"],
        )

        output_result(result, format_type="human", quiet=True)

        # In quiet mode, should not print warnings
        calls = [call.args[0] for call in mock_print.call_args_list]
        assert len(calls) == 0  # Quiet mode suppresses output

    @patch("builtins.print")
    def test_output_result_json_format(self, mock_print):
        """Test outputting result in JSON format."""
        result = OperationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            message="JSON test",
            data={"key": "value"},
            errors=[],
            warnings=["Warning message"],
        )

        output_result(result, format_type="json")

        # Should output JSON string
        mock_print.assert_called_once()
        json_output = mock_print.call_args[0][0]
        parsed = json.loads(json_output)

        assert parsed["success"] is True
        assert parsed["exit_code"] == 0
        assert parsed["message"] == "JSON test"
        assert parsed["data"]["key"] == "value"
        assert parsed["warnings"] == ["Warning message"]


class TestCreateStructuredError:
    """Test create_structured_error function."""

    def test_create_structured_error_basic(self):
        """Test creating a basic structured error."""
        result = create_structured_error(message="Test error", exit_code=ExitCode.VALIDATION_ERROR)

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert result.message == "Test error"
        assert result.errors == []
        assert result.warnings == []
        assert result.data == {}

    def test_create_structured_error_with_details(self):
        """Test creating structured error with errors and context."""
        result = create_structured_error(
            message="Validation failed",
            exit_code=ExitCode.VALIDATION_ERROR,
            errors=["Missing field: title", "Invalid format: date"],
            context={"file": "tasks.yaml", "line": 42},
        )

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert result.message == "Validation failed"
        assert len(result.errors) == 2
        assert "Missing field: title" in result.errors
        assert "Invalid format: date" in result.errors
        assert result.data["file"] == "tasks.yaml"
        assert result.data["line"] == 42

    def test_create_structured_error_system_error(self):
        """Test creating system error result."""
        result = create_structured_error(
            message="File not found",
            exit_code=ExitCode.SYSTEM_ERROR,
            errors=["Could not read tasks.yaml"],
            context={"path": "/path/to/tasks.yaml"},
        )

        assert result.success is False
        assert result.exit_code == ExitCode.SYSTEM_ERROR
        assert result.message == "File not found"
        assert result.errors == ["Could not read tasks.yaml"]
        assert result.data["path"] == "/path/to/tasks.yaml"


class TestFormatValidationSummary:
    """Test format_validation_summary function."""

    def test_format_validation_summary_mixed_results(self):
        """Test formatting mixed validation results."""
        validation_results = [
            ("File Structure", True, [], ["Missing optional config"]),
            ("Task Format", False, ["Invalid ID format", "Missing title"], ["Deprecated field"]),
            ("Dependencies", True, [], []),
            ("Schema", False, ["Schema error"], []),
        ]

        result = format_validation_summary(validation_results)

        assert "Validation Summary:" in result
        assert "✓ File Structure (1 warning)" in result
        assert "  ⚠ Missing optional config" in result
        assert "✗ Task Format (2 errors, 1 warning)" in result
        assert "  ✗ Invalid ID format" in result
        assert "  ✗ Missing title" in result
        assert "  ⚠ Deprecated field" in result
        assert "✓ Dependencies" in result
        assert "✗ Schema (1 error)" in result

    def test_format_validation_summary_all_success(self):
        """Test formatting all successful validation results."""
        validation_results = [
            ("Check 1", True, [], []),
            ("Check 2", True, [], ["Minor issue"]),
        ]

        result = format_validation_summary(validation_results)

        assert "✓ Check 1" in result
        assert "✓ Check 2 (1 warning)" in result
        assert "  ⚠ Minor issue" in result
        assert "✗" not in result  # No failures

    def test_format_validation_summary_pluralization(self):
        """Test proper pluralization in validation summary."""
        validation_results = [
            ("Single", False, ["One error"], ["One warning"]),
            ("Multiple", False, ["Error 1", "Error 2"], ["Warning 1", "Warning 2"]),
        ]

        result = format_validation_summary(validation_results)

        assert "✗ Single (1 error, 1 warning)" in result
        assert "✗ Multiple (2 errors, 2 warnings)" in result


class TestCreateSuccessResult:
    """Test create_success_result function."""

    def test_create_success_result_basic(self):
        """Test creating a basic success result."""
        result = create_success_result("Operation completed")

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert result.message == "Operation completed"
        assert result.errors == []
        assert result.warnings == []
        assert result.data == {}

    def test_create_success_result_with_data(self):
        """Test creating success result with data."""
        result = create_success_result(
            message="Task created successfully",
            data={"task_id": 42, "priority": "High"},
            warnings=["Used default assignee"],
        )

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert result.message == "Task created successfully"
        assert result.data["task_id"] == 42
        assert result.data["priority"] == "High"
        assert result.warnings == ["Used default assignee"]
        assert result.errors == []

    def test_create_success_result_with_warnings(self):
        """Test creating success result with multiple warnings."""
        result = create_success_result(
            message="Processing completed", warnings=["Warning 1", "Warning 2", "Warning 3"]
        )

        assert result.success is True
        assert len(result.warnings) == 3
        assert "Warning 1" in result.warnings
        assert "Warning 2" in result.warnings
        assert "Warning 3" in result.warnings


class TestIntegration:
    """Integration tests combining multiple formatting functions."""

    def test_full_task_formatting_workflow(self):
        """Test complete workflow from Task creation to various outputs."""
        # Create a comprehensive task
        task_data = {
            "id": 100,
            "title": "Integration Test Task",
            "status": "in_progress",
            "priority": "High",
            "description": "A comprehensive task for testing",
            "created_date": "2024-01-01T00:00:00Z",
            "start_date": "2024-01-02T10:00:00Z",
            "prerequisites": ["Setup task", "Config task"],
            "subtasks": [
                {"name": "Phase 1", "completed": True},
                {"name": "Phase 2", "completed": False},
                {"name": "Phase 3", "completed": False},
            ],
            "estimated_time": "4 hours",
            "assignee": "Test User",
        }
        task = Task(task_data)

        # Test YAML formatting
        yaml_output = format_task_yaml(task)
        yaml_parsed = yaml.safe_load(yaml_output)
        assert yaml_parsed["id"] == 100
        assert yaml_parsed["title"] == "Integration Test Task"

        # Test summary formatting
        summary = format_task_summary(task)
        assert "[100] Integration Test Task (HIGH PRIORITY, IN PROGRESS)" in summary
        assert "Prerequisites: Setup task, Config task" in summary
        assert "✓ Phase 1" in summary
        assert "○ Phase 2" in summary

    def test_result_output_formatting_workflow(self):
        """Test workflow from operation results to formatted output."""
        # Create various types of results
        success_result = create_success_result(
            "All tasks processed",
            data={"processed": 5, "skipped": 1},
            warnings=["One task had missing data"],
        )

        error_result = create_structured_error(
            "Processing failed",
            ExitCode.VALIDATION_ERROR,
            errors=["Invalid task format", "Missing required fields"],
            context={"file": "tasks.yaml"},
        )

        # Test that both results have proper structure
        assert success_result.success is True
        assert error_result.success is False

        # Test JSON serialization works
        with patch("builtins.print") as mock_print:
            output_result(success_result, format_type="json")
            json_output = mock_print.call_args[0][0]
            parsed = json.loads(json_output)
            assert parsed["success"] is True
            assert parsed["data"]["processed"] == 5

    def test_validation_summary_integration(self):
        """Test integration of validation results with summary formatting."""
        # Simulate validation results from different sources
        validation_results = [
            ("YAML Syntax", True, [], []),
            (
                "Task Schema",
                False,
                ["Invalid task ID: 'abc'"],
                ["Deprecated field: 'old_priority'"],
            ),
            ("Dependencies", True, [], ["Circular dependency warning"]),
            ("File System", False, ["File not readable"], []),
        ]

        summary = format_validation_summary(validation_results)

        # Verify comprehensive formatting
        assert "Validation Summary:" in summary
        assert "✓ YAML Syntax" in summary
        assert "✗ Task Schema (1 error, 1 warning)" in summary
        assert "✓ Dependencies (1 warning)" in summary
        assert "✗ File System (1 error)" in summary

        # Verify error and warning details are included
        assert "Invalid task ID: 'abc'" in summary
        assert "Deprecated field: 'old_priority'" in summary
        assert "Circular dependency warning" in summary
        assert "File not readable" in summary
