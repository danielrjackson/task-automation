#!/usr/bin/env python3
"""
Comprehensive tests for core_utils.py module.

Tests the core data structures, constants, and utility functions.
"""

import os
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from src.taskautomation.core_utils import (
    DOCS_DIR,
    PLANNING_DIR,
    ROOT_DIR,
    SRC_DIR,
    TASKS_FILE,
    ExitCode,
    OperationResult,
    Priority,
    TaskInfo,
    TaskStatus,
    ValidationResult,
    find_tasks_by_criteria,
    format_iso8601_datetime,
    get_current_datetime,
    get_git_root,
)


class TestCoreUtils(unittest.TestCase):
    """Test cases for core_utils module."""

    def test_constants_defined(self):
        """Test that all required constants are defined."""
        # Path constants
        self.assertIsInstance(ROOT_DIR, pathlib.Path)
        self.assertIsInstance(TASKS_FILE, pathlib.Path)
        self.assertIsInstance(SRC_DIR, pathlib.Path)
        self.assertIsInstance(DOCS_DIR, pathlib.Path)
        self.assertIsInstance(PLANNING_DIR, pathlib.Path)

        # Constants should be absolute paths
        self.assertTrue(ROOT_DIR.is_absolute())
        self.assertTrue(TASKS_FILE.is_absolute())
        self.assertTrue(SRC_DIR.is_absolute())
        self.assertTrue(DOCS_DIR.is_absolute())
        self.assertTrue(PLANNING_DIR.is_absolute())

    def test_exit_code_enum(self):
        """Test ExitCode enum values."""
        self.assertEqual(ExitCode.SUCCESS, 0)
        self.assertEqual(ExitCode.NO_WORK, 1)
        self.assertEqual(ExitCode.VALIDATION_ERROR, 2)
        self.assertEqual(ExitCode.SYSTEM_ERROR, 3)
        self.assertEqual(ExitCode.USER_ABORT, 4)

        # Test that all values are integers
        for code in ExitCode:
            self.assertIsInstance(code.value, int)

    def test_priority_enum(self):
        """Test Priority enum values."""
        self.assertEqual(Priority.LOW, "Low")
        self.assertEqual(Priority.MEDIUM, "Medium")
        self.assertEqual(Priority.HIGH, "High")
        self.assertEqual(Priority.CRITICAL, "Critical")

        # Test that all values are strings
        for priority in Priority:
            self.assertIsInstance(priority.value, str)

    def test_task_status_enum(self):
        """Test TaskStatus enum values."""
        self.assertEqual(TaskStatus.PENDING, "pending")
        self.assertEqual(TaskStatus.COMPLETED, "completed")

        # Test that all values are strings
        for status in TaskStatus:
            self.assertIsInstance(status.value, str)

    def test_operation_result_creation(self):
        """Test OperationResult data class creation."""
        # Test successful result
        success_result = OperationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            message="Operation completed successfully",
            data={"result": "success"},
            errors=[],
            warnings=[],
        )

        self.assertTrue(success_result.success)
        self.assertEqual(success_result.exit_code, ExitCode.SUCCESS)
        self.assertEqual(success_result.message, "Operation completed successfully")
        self.assertEqual(success_result.data["result"], "success")
        self.assertEqual(len(success_result.errors), 0)
        self.assertEqual(len(success_result.warnings), 0)

        # Test failure result
        failure_result = OperationResult(
            success=False,
            exit_code=ExitCode.VALIDATION_ERROR,
            message="Validation failed",
            data={},
            errors=["Invalid format", "Missing field"],
            warnings=["Deprecated syntax"],
        )

        self.assertFalse(failure_result.success)
        self.assertEqual(failure_result.exit_code, ExitCode.VALIDATION_ERROR)
        self.assertEqual(failure_result.message, "Validation failed")
        self.assertEqual(len(failure_result.errors), 2)
        self.assertEqual(len(failure_result.warnings), 1)
        self.assertIn("Invalid format", failure_result.errors)
        self.assertIn("Deprecated syntax", failure_result.warnings)

    def test_validation_result_creation(self):
        """Test ValidationResult data class creation."""
        # Test valid result without context
        valid_result = ValidationResult(is_valid=True, errors=[], warnings=[], context={})

        self.assertTrue(valid_result.is_valid)
        self.assertEqual(len(valid_result.errors), 0)
        self.assertEqual(len(valid_result.warnings), 0)
        self.assertEqual(len(valid_result.context), 0)

        # Test invalid result with errors
        invalid_result = ValidationResult(
            is_valid=False,
            errors=["Missing ID", "Invalid date format"],
            warnings=["Old format detected"],
            context={"field": "test_field"},
        )

        self.assertFalse(invalid_result.is_valid)
        self.assertEqual(len(invalid_result.errors), 2)
        self.assertEqual(len(invalid_result.warnings), 1)
        self.assertIn("Missing ID", invalid_result.errors)
        self.assertIn("Old format detected", invalid_result.warnings)
        self.assertEqual(invalid_result.context["field"], "test_field")

    def test_task_info_creation(self):
        """Test TaskInfo NamedTuple creation."""
        # Test pending task
        pending_task = TaskInfo(
            title="Test Task",
            checked=False,
            task_id=1,
            priority="High",
            assignee="TestUser",
            create_date="2025-01-01T12:00:00Z",
            start_date=None,
            finish_date=None,
            estimated_time="2 hours",
            description="This is a test task",
            prerequisites=["Setup environment"],
            subtasks={"Step 1": False, "Step 2": True},
            raw_block="- [ ] **Test Task**: This is a test task\n  - **ID**: 1\n  - **Priority**: High",
        )

        self.assertEqual(pending_task.task_id, 1)
        self.assertEqual(pending_task.title, "Test Task")
        self.assertEqual(pending_task.priority, "High")
        self.assertEqual(pending_task.assignee, "TestUser")
        self.assertFalse(pending_task.checked)
        self.assertEqual(pending_task.create_date, "2025-01-01T12:00:00Z")
        self.assertIsNone(pending_task.finish_date)
        self.assertEqual(pending_task.description, "This is a test task")
        self.assertEqual(len(pending_task.prerequisites), 1)
        self.assertEqual(len(pending_task.subtasks), 2)

        # Test completed task
        completed_task = TaskInfo(
            title="Completed Task",
            checked=True,
            task_id=2,
            priority="Medium",
            assignee="AnotherUser",
            create_date="2025-01-01T12:00:00Z",
            start_date="2025-01-01T12:00:00Z",
            finish_date="2025-01-02T12:00:00Z",
            estimated_time="1 hour",
            description="This task is completed",
            prerequisites=[],
            subtasks={},
            raw_block="- [x] **Completed Task**: This task is completed\n  - **ID**: 2\n  - **Priority**: Medium",
        )

        self.assertEqual(completed_task.task_id, 2)
        self.assertEqual(completed_task.title, "Completed Task")
        self.assertEqual(completed_task.priority, "Medium")
        self.assertEqual(completed_task.assignee, "AnotherUser")
        self.assertTrue(completed_task.checked)
        self.assertEqual(completed_task.finish_date, "2025-01-02T12:00:00Z")

    def test_format_iso8601_datetime(self):
        """Test format_iso8601_datetime function."""
        # Test with specific datetime
        test_datetime = datetime(2025, 1, 1, 12, 30, 45)
        formatted = format_iso8601_datetime(test_datetime)

        self.assertIsInstance(formatted, str)
        self.assertIn("2025-01-01T12:30:45", formatted)
        self.assertTrue(formatted.endswith("Z"))

        # Test with different datetime
        test_datetime2 = datetime(2024, 12, 31, 23, 59, 59)
        formatted2 = format_iso8601_datetime(test_datetime2)

        self.assertIsInstance(formatted2, str)
        self.assertIn("2024-12-31T23:59:59", formatted2)
        self.assertTrue(formatted2.endswith("Z"))

        # Test with microseconds (should be handled gracefully)
        test_datetime3 = datetime(2025, 6, 15, 8, 0, 0, 123456)
        formatted3 = format_iso8601_datetime(test_datetime3)

        self.assertIsInstance(formatted3, str)
        self.assertIn("2025-06-15T08:00:00", formatted3)

    def test_format_iso8601_datetime_none(self):
        """Test format_iso8601_datetime with None parameter."""
        # Test with None (should use current time)
        formatted = format_iso8601_datetime(None)

        self.assertIsInstance(formatted, str)
        self.assertTrue(formatted.endswith("Z"))
        # Should be in ISO format
        self.assertRegex(formatted, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_format_iso8601_datetime_utc_timezone(self):
        """Test format_iso8601_datetime with UTC timezone datetime."""
        import datetime as dt

        # Create datetime with explicit UTC timezone
        utc_datetime = dt.datetime(2025, 1, 1, 12, 0, 0, tzinfo=dt.UTC)
        formatted = format_iso8601_datetime(utc_datetime)

        self.assertIsInstance(formatted, str)
        self.assertTrue(formatted.endswith("Z"))
        self.assertIn("2025-01-01T12:00:00", formatted)

    def test_get_current_datetime(self):
        """Test get_current_datetime function."""
        current_dt = get_current_datetime()

        self.assertIsInstance(current_dt, str)
        self.assertTrue(current_dt.endswith("Z"))
        # Should be in ISO format
        self.assertRegex(current_dt, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_format_iso8601_datetime_edge_cases(self):
        """Test various edge cases for format_iso8601_datetime."""
        import datetime as dt

        # Test with different timezone formats to see if we can trigger lines 144-145
        # Note: These lines might be unreachable due to Python's datetime implementation

        # Test with timezone.utc (different from datetime.UTC)
        utc_tz = dt.UTC
        utc_datetime = dt.datetime(2025, 1, 1, 12, 0, 0, tzinfo=utc_tz)
        formatted = format_iso8601_datetime(utc_datetime)

        self.assertIsInstance(formatted, str)
        self.assertTrue(formatted.endswith("Z"))

        # Test with custom timezone offset
        custom_tz = dt.timezone(dt.timedelta(hours=5))
        custom_datetime = dt.datetime(2025, 1, 1, 12, 0, 0, tzinfo=custom_tz)
        formatted_custom = format_iso8601_datetime(custom_datetime)

        self.assertIsInstance(formatted_custom, str)
        # Custom timezone should not get Z suffix
        self.assertFalse(formatted_custom.endswith("Z"))

    def test_get_git_root(self):
        """Test get_git_root function."""
        # This function might return None if not in a git repository
        # or a Path if in a git repository
        git_root = get_git_root()

        if git_root is not None:
            self.assertIsInstance(git_root, pathlib.Path)
            self.assertTrue(git_root.exists())
            # Should contain .git directory
            self.assertTrue((git_root / ".git").exists())
        else:
            # If None, that's also valid (not in a git repo)
            self.assertIsNone(git_root)

    def test_get_git_root_with_temp_dir(self):
        """Test get_git_root function in a temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)

            # Change to temp directory and test
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_path)
                git_root = get_git_root()
                # Should return None since temp dir is not a git repo
                self.assertIsNone(git_root)
            finally:
                os.chdir(original_cwd)

    def test_data_class_equality(self):
        """Test equality comparison for data classes."""
        # Test OperationResult equality
        result1 = OperationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            message="test",
            data={},
            errors=[],
            warnings=[],
        )

        result2 = OperationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            message="test",
            data={},
            errors=[],
            warnings=[],
        )

        result3 = OperationResult(
            success=False,
            exit_code=ExitCode.VALIDATION_ERROR,
            message="test",
            data={},
            errors=[],
            warnings=[],
        )

        self.assertEqual(result1, result2)
        self.assertNotEqual(result1, result3)

        # Test TaskInfo equality
        task1 = TaskInfo(
            title="Test",
            checked=False,
            task_id=1,
            priority="High",
            assignee="User",
            create_date="2025-01-01T00:00:00Z",
            start_date=None,
            finish_date=None,
            estimated_time="1 hour",
            description="Test",
            prerequisites=[],
            subtasks={},
            raw_block="- [ ] **Test**: Test",
        )

        task2 = TaskInfo(
            title="Test",
            checked=False,
            task_id=1,
            priority="High",
            assignee="User",
            create_date="2025-01-01T00:00:00Z",
            start_date=None,
            finish_date=None,
            estimated_time="1 hour",
            description="Test",
            prerequisites=[],
            subtasks={},
            raw_block="- [ ] **Test**: Test",
        )

        task3 = TaskInfo(
            title="Test",
            checked=False,
            task_id=2,
            priority="High",
            assignee="User",
            create_date="2025-01-01T00:00:00Z",
            start_date=None,
            finish_date=None,
            estimated_time="1 hour",
            description="Test",
            prerequisites=[],
            subtasks={},
            raw_block="- [ ] **Test**: Test",
        )

        self.assertEqual(task1, task2)
        self.assertNotEqual(task1, task3)

    def test_data_class_repr(self):
        """Test string representation of data classes."""
        # Test OperationResult repr
        result = OperationResult(
            success=True,
            exit_code=ExitCode.SUCCESS,
            message="test message",
            data={"key": "value"},
            errors=[],
            warnings=[],
        )

        repr_str = repr(result)
        self.assertIn("OperationResult", repr_str)
        self.assertIn("success=True", repr_str)
        self.assertIn("test message", repr_str)

        # Test TaskInfo repr
        task = TaskInfo(
            title="Test Task",
            checked=False,
            task_id=1,
            priority="High",
            assignee="TestUser",
            create_date="2025-01-01T00:00:00Z",
            start_date=None,
            finish_date=None,
            estimated_time="2 hours",
            description="Test description",
            prerequisites=[],
            subtasks={},
            raw_block="- [ ] **Test Task**: Test description",
        )

        task_repr = repr(task)
        self.assertIn("TaskInfo", task_repr)
        self.assertIn("task_id=1", task_repr)
        self.assertIn("Test Task", task_repr)

    def test_enum_membership(self):
        """Test enum membership operations."""
        # Test ExitCode membership
        self.assertIn(ExitCode.SUCCESS, ExitCode)
        self.assertIn(ExitCode.VALIDATION_ERROR, ExitCode)

        # Test Priority membership
        self.assertIn(Priority.HIGH, Priority)
        self.assertIn(Priority.LOW, Priority)

        # Test TaskStatus membership
        self.assertIn(TaskStatus.PENDING, TaskStatus)
        self.assertIn(TaskStatus.COMPLETED, TaskStatus)

    def test_validation_result_with_context(self):
        """Test ValidationResult with context."""
        context_data = {"task_id": 1, "field": "title", "line_number": 10}

        validation_result = ValidationResult(
            is_valid=True, errors=[], warnings=["Minor formatting issue"], context=context_data
        )

        self.assertTrue(validation_result.is_valid)
        self.assertIsNotNone(validation_result.context)
        self.assertEqual(validation_result.context["task_id"], 1)
        self.assertEqual(validation_result.context["field"], "title")
        self.assertEqual(len(validation_result.warnings), 1)

    def test_find_tasks_by_criteria_no_filters(self):
        """Test find_tasks_by_criteria with no filters."""
        # Create sample tasks
        tasks = {
            "Task 1": TaskInfo(
                title="Task 1",
                checked=False,
                task_id=1,
                priority="High",
                assignee="Alice",
                create_date="2025-01-01T00:00:00Z",
                start_date=None,
                finish_date=None,
                estimated_time="2 hours",
                description="High priority task",
                prerequisites=[],
                subtasks={"Step 1": False},
                raw_block="- [ ] **Task 1**: High priority task",
            ),
            "Task 2": TaskInfo(
                title="Task 2",
                checked=True,
                task_id=2,
                priority="Medium",
                assignee="Bob",
                create_date="2025-01-01T00:00:00Z",
                start_date="2025-01-01T00:00:00Z",
                finish_date="2025-01-02T00:00:00Z",
                estimated_time="1 hour",
                description="Medium priority task",
                prerequisites=[],
                subtasks={},
                raw_block="- [x] **Task 2**: Medium priority task",
            ),
        }

        # No filters should return all tasks
        result = find_tasks_by_criteria(tasks)
        self.assertEqual(len(result), 2)
        self.assertIn("Task 1", result)
        self.assertIn("Task 2", result)

    def test_find_tasks_by_criteria_priority_filter(self):
        """Test find_tasks_by_criteria with priority filter."""
        tasks = {
            "High Task": TaskInfo(
                title="High Task",
                checked=False,
                task_id=1,
                priority="High",
                assignee="Alice",
                create_date="2025-01-01T00:00:00Z",
                start_date=None,
                finish_date=None,
                estimated_time="2 hours",
                description="High priority",
                prerequisites=[],
                subtasks={},
                raw_block="- [ ] **High Task**: High priority",
            ),
            "Medium Task": TaskInfo(
                title="Medium Task",
                checked=False,
                task_id=2,
                priority="Medium",
                assignee="Bob",
                create_date="2025-01-01T00:00:00Z",
                start_date=None,
                finish_date=None,
                estimated_time="1 hour",
                description="Medium priority",
                prerequisites=[],
                subtasks={},
                raw_block="- [ ] **Medium Task**: Medium priority",
            ),
        }

        # Filter by High priority
        result = find_tasks_by_criteria(tasks, priority="High")
        self.assertEqual(len(result), 1)
        self.assertIn("High Task", result)
        self.assertNotIn("Medium Task", result)

        # Filter by Medium priority
        result = find_tasks_by_criteria(tasks, priority="Medium")
        self.assertEqual(len(result), 1)
        self.assertIn("Medium Task", result)
        self.assertNotIn("High Task", result)

    def test_find_tasks_by_criteria_checked_filter(self):
        """Test find_tasks_by_criteria with checked filter."""
        tasks = {
            "Pending Task": TaskInfo(
                title="Pending Task",
                checked=False,
                task_id=1,
                priority="High",
                assignee="Alice",
                create_date="2025-01-01T00:00:00Z",
                start_date=None,
                finish_date=None,
                estimated_time="2 hours",
                description="Pending task",
                prerequisites=[],
                subtasks={},
                raw_block="- [ ] **Pending Task**: Pending task",
            ),
            "Completed Task": TaskInfo(
                title="Completed Task",
                checked=True,
                task_id=2,
                priority="Medium",
                assignee="Bob",
                create_date="2025-01-01T00:00:00Z",
                start_date="2025-01-01T00:00:00Z",
                finish_date="2025-01-02T00:00:00Z",
                estimated_time="1 hour",
                description="Completed task",
                prerequisites=[],
                subtasks={},
                raw_block="- [x] **Completed Task**: Completed task",
            ),
        }

        # Filter by unchecked tasks
        result = find_tasks_by_criteria(tasks, checked=False)
        self.assertEqual(len(result), 1)
        self.assertIn("Pending Task", result)

        # Filter by checked tasks
        result = find_tasks_by_criteria(tasks, checked=True)
        self.assertEqual(len(result), 1)
        self.assertIn("Completed Task", result)

    def test_find_tasks_by_criteria_assignee_filter(self):
        """Test find_tasks_by_criteria with assignee filter."""
        tasks = {
            "Alice Task": TaskInfo(
                title="Alice Task",
                checked=False,
                task_id=1,
                priority="High",
                assignee="Alice",
                create_date="2025-01-01T00:00:00Z",
                start_date=None,
                finish_date=None,
                estimated_time="2 hours",
                description="Alice's task",
                prerequisites=[],
                subtasks={},
                raw_block="- [ ] **Alice Task**: Alice's task",
            ),
            "Bob Task": TaskInfo(
                title="Bob Task",
                checked=False,
                task_id=2,
                priority="Medium",
                assignee="Bob",
                create_date="2025-01-01T00:00:00Z",
                start_date=None,
                finish_date=None,
                estimated_time="1 hour",
                description="Bob's task",
                prerequisites=[],
                subtasks={},
                raw_block="- [ ] **Bob Task**: Bob's task",
            ),
            "Unassigned Task": TaskInfo(
                title="Unassigned Task",
                checked=False,
                task_id=3,
                priority="Low",
                assignee=None,
                create_date="2025-01-01T00:00:00Z",
                start_date=None,
                finish_date=None,
                estimated_time="30 min",
                description="Unassigned task",
                prerequisites=[],
                subtasks={},
                raw_block="- [ ] **Unassigned Task**: Unassigned task",
            ),
        }

        # Filter by Alice
        result = find_tasks_by_criteria(tasks, assignee="Alice")
        self.assertEqual(len(result), 1)
        self.assertIn("Alice Task", result)

        # Filter by Bob
        result = find_tasks_by_criteria(tasks, assignee="Bob")
        self.assertEqual(len(result), 1)
        self.assertIn("Bob Task", result)

        # Filter by None (don't filter by assignee - should return all tasks)
        result = find_tasks_by_criteria(tasks, assignee=None)
        self.assertEqual(len(result), 3)  # All tasks should be returned
        self.assertIn("Alice Task", result)
        self.assertIn("Bob Task", result)
        self.assertIn("Unassigned Task", result)

    def test_find_tasks_by_criteria_subtasks_filter(self):
        """Test find_tasks_by_criteria with has_subtasks filter."""
        tasks = {
            "With Subtasks": TaskInfo(
                title="With Subtasks",
                checked=False,
                task_id=1,
                priority="High",
                assignee="Alice",
                create_date="2025-01-01T00:00:00Z",
                start_date=None,
                finish_date=None,
                estimated_time="2 hours",
                description="Task with subtasks",
                prerequisites=[],
                subtasks={"Subtask 1": False, "Subtask 2": True},
                raw_block="- [ ] **With Subtasks**: Task with subtasks",
            ),
            "Without Subtasks": TaskInfo(
                title="Without Subtasks",
                checked=False,
                task_id=2,
                priority="Medium",
                assignee="Bob",
                create_date="2025-01-01T00:00:00Z",
                start_date=None,
                finish_date=None,
                estimated_time="1 hour",
                description="Task without subtasks",
                prerequisites=[],
                subtasks={},
                raw_block="- [ ] **Without Subtasks**: Task without subtasks",
            ),
        }

        # Filter by has_subtasks=True
        result = find_tasks_by_criteria(tasks, has_subtasks=True)
        self.assertEqual(len(result), 1)
        self.assertIn("With Subtasks", result)

        # Filter by has_subtasks=False
        result = find_tasks_by_criteria(tasks, has_subtasks=False)
        self.assertEqual(len(result), 1)
        self.assertIn("Without Subtasks", result)

    def test_find_tasks_by_criteria_multiple_filters(self):
        """Test find_tasks_by_criteria with multiple filters."""
        tasks = {
            "Match All": TaskInfo(
                title="Match All",
                checked=False,
                task_id=1,
                priority="High",
                assignee="Alice",
                create_date="2025-01-01T00:00:00Z",
                start_date=None,
                finish_date=None,
                estimated_time="2 hours",
                description="Matches all criteria",
                prerequisites=[],
                subtasks={"Step 1": False},
                raw_block="- [ ] **Match All**: Matches all criteria",
            ),
            "Match Some": TaskInfo(
                title="Match Some",
                checked=False,
                task_id=2,
                priority="Medium",
                assignee="Alice",
                create_date="2025-01-01T00:00:00Z",
                start_date=None,
                finish_date=None,
                estimated_time="1 hour",
                description="Matches some criteria",
                prerequisites=[],
                subtasks={},
                raw_block="- [ ] **Match Some**: Matches some criteria",
            ),
            "Match None": TaskInfo(
                title="Match None",
                checked=True,
                task_id=3,
                priority="Low",
                assignee="Bob",
                create_date="2025-01-01T00:00:00Z",
                start_date="2025-01-01T00:00:00Z",
                finish_date="2025-01-02T00:00:00Z",
                estimated_time="30 min",
                description="Matches no criteria",
                prerequisites=[],
                subtasks={},
                raw_block="- [x] **Match None**: Matches no criteria",
            ),
        }

        # Multiple filters
        result = find_tasks_by_criteria(
            tasks, priority="High", checked=False, assignee="Alice", has_subtasks=True
        )
        self.assertEqual(len(result), 1)
        self.assertIn("Match All", result)

        # No tasks match all filters
        result = find_tasks_by_criteria(tasks, priority="Critical", checked=False, assignee="Alice")
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
