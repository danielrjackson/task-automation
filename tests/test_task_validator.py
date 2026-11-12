#!/usr/bin/env python3
"""
Test suite for task_validator module.

This module tests YAML-based task validation functionality including
file validation, task object validation, and environment validation.
"""

from unittest.mock import Mock, PropertyMock, patch

import yaml

from src.taskautomation.task_schema import (
    Task,
    TaskList,
    TaskStatus,
)
from src.taskautomation.task_types import (
    ExitCode,
    ValidationResult,
)
from src.taskautomation.task_validator import (
    _check_duplicate_task_ids,
    _check_prerequisites_exist,
    _has_circular_dependency,
    _is_valid_time_estimate,
    create_validation_summary,
    validate_automation_environment,
    validate_schema_compatibility,
    validate_task_list,
    validate_task_object,
    validate_yaml_content,
    validate_yaml_file,
)


class TestValidateTaskObject:
    """Test validate_task_object function."""

    def test_validate_task_object_valid(self):
        """Test validating a valid task object."""
        task_data = {
            "id": 1,
            "title": "Valid task",
            "status": "pending",
            "priority": "Medium",
            "description": "A valid task for testing",
        }
        task = Task(task_data)

        result = validate_task_object(task)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.context["exit_code"] == ExitCode.SUCCESS

    def test_validate_task_object_date_consistency_error(self):
        """Test task with start date after finish date."""
        task_data = {
            "id": 1,
            "title": "Invalid dates task",
            "status": "pending",
            "priority": "Medium",
            "start_date": "2023-12-31T23:59:59",
            "finish_date": "2023-01-01T00:00:00",
        }
        task = Task(task_data)

        result = validate_task_object(task)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Start date cannot be after finish date" in result.errors[0]
        assert result.context["exit_code"] == ExitCode.VALIDATION_ERROR

    def test_validate_task_object_completed_with_uncompleted_subtasks(self):
        """Test completed task with uncompleted subtasks (warning)."""
        task_data = {
            "id": 1,
            "title": "Completed task",
            "status": "completed",
            "priority": "Medium",
            "subtasks": [
                {"name": "Done subtask", "completed": True},
                {"name": "Pending subtask", "completed": False},
            ],
        }
        task = Task(task_data)

        result = validate_task_object(task)

        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) == 1
        assert "uncompleted subtasks" in result.warnings[0]
        assert "Pending subtask" in result.warnings[0]

    def test_validate_task_object_in_progress_no_start_date(self):
        """Test in progress task without start date (warning)."""
        task_data = {
            "id": 1,
            "title": "In progress task",
            "status": "in_progress",
            "priority": "Medium",
        }
        task = Task(task_data)

        result = validate_task_object(task)

        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) == 1
        assert "in progress but has no start date" in result.warnings[0]

    def test_validate_task_object_completed_no_finish_date(self):
        """Test completed task without finish date (warning)."""
        task_data = {
            "id": 1,
            "title": "Completed task",
            "status": "completed",
            "priority": "Medium",
        }
        task = Task(task_data)

        result = validate_task_object(task)

        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) == 1
        assert "completed but has no finish date" in result.warnings[0]

    def test_validate_task_object_invalid_time_estimate(self):
        """Test task with invalid time estimate format."""
        task_data = {
            "id": 1,
            "title": "Task with bad time",
            "status": "pending",
            "priority": "Medium",
            "estimated_time": "sometime next week maybe",
        }
        task = Task(task_data)

        result = validate_task_object(task)

        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) == 1
        assert "Estimated time should be in format" in result.warnings[0]

    def test_validate_task_object_exception_handling(self):
        """Test exception handling in task validation."""
        # Create a mock task that raises an exception
        mock_task = Mock(spec=Task)
        mock_task.id = 1
        mock_task.start_date = None
        mock_task.finish_date = None
        mock_task.status = TaskStatus.PENDING
        mock_task.subtasks = []
        mock_task.estimated_time = None

        # Make accessing start_date raise an exception
        type(mock_task).start_date = PropertyMock(side_effect=Exception("Test error"))

        result = validate_task_object(mock_task)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Unexpected error validating task" in result.errors[0]


class TestValidateTaskList:
    """Test validate_task_list function."""

    def test_validate_task_list_valid(self):
        """Test validating a valid task list."""
        data = {
            "Medium": [
                {"id": 1, "title": "Task 1", "status": "pending", "priority": "Medium"},
                {"id": 2, "title": "Task 2", "status": "completed", "priority": "Medium"},
            ]
        }
        task_list = TaskList(data)

        result = validate_task_list(task_list)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.context["exit_code"] == ExitCode.SUCCESS

    def test_validate_task_list_duplicate_ids(self):
        """Test task list with duplicate task IDs."""
        data = {
            "Medium": [
                {"id": 1, "title": "Task 1", "status": "pending", "priority": "Medium"},
                {"id": 1, "title": "Task 2", "status": "completed", "priority": "Medium"},
            ]
        }
        task_list = TaskList(data)

        result = validate_task_list(task_list)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Duplicate task ID 1" in result.errors[0]

    def test_validate_task_list_missing_prerequisites(self):
        """Test task list with missing prerequisites."""
        data = {
            "Medium": [
                {
                    "id": 1,
                    "title": "Dependent task",
                    "status": "pending",
                    "priority": "Medium",
                    "prerequisites": ["Nonexistent task"],
                }
            ]
        }
        task_list = TaskList(data)

        result = validate_task_list(task_list)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "unknown prerequisite" in result.errors[0]
        assert "Nonexistent task" in result.errors[0]

    def test_validate_task_list_circular_dependencies(self):
        """Test task list with circular dependencies."""
        data = {
            "Medium": [
                {
                    "id": 1,
                    "title": "Task A",
                    "status": "pending",
                    "priority": "Medium",
                    "prerequisites": ["Task B"],
                },
                {
                    "id": 2,
                    "title": "Task B",
                    "status": "pending",
                    "priority": "Medium",
                    "prerequisites": ["Task A"],
                },
            ]
        }
        task_list = TaskList(data)

        result = validate_task_list(task_list)

        assert result.is_valid is False
        assert len(result.errors) >= 1
        assert any("Circular dependency" in error for error in result.errors)

    def test_validate_task_list_completion_consistency_warning(self):
        """Test task list with completion consistency issues."""
        data = {
            "Medium": [
                {"id": 1, "title": "Prerequisite", "status": "pending", "priority": "Medium"},
                {
                    "id": 2,
                    "title": "Completed task",
                    "status": "completed",
                    "priority": "Medium",
                    "prerequisites": ["Prerequisite"],
                },
            ]
        }
        task_list = TaskList(data)

        result = validate_task_list(task_list)

        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) >= 1
        assert any("incomplete prerequisites" in warning for warning in result.warnings)

    def test_validate_task_list_exception_handling(self):
        """Test exception handling in task list validation."""
        # Create a mock task list that raises an exception
        mock_task_list = Mock(spec=TaskList)
        mock_task_list.get_all_tasks.side_effect = Exception("Test error")

        result = validate_task_list(mock_task_list)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Unexpected error validating task list" in result.errors[0]


class TestValidateYamlFile:
    """Test validate_yaml_file function."""

    @patch("pathlib.Path.exists")
    def test_validate_yaml_file_not_exists(self, mock_exists):
        """Test validation of non-existent file."""
        mock_exists.return_value = False

        result = validate_yaml_file("nonexistent.yaml")

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Task file not found" in result.errors[0]
        assert result.context["exit_code"] == ExitCode.SYSTEM_ERROR

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open")
    def test_validate_yaml_file_permission_error(self, mock_open, mock_exists):
        """Test validation with permission error."""
        mock_exists.return_value = True
        mock_open.side_effect = PermissionError("Permission denied")

        result = validate_yaml_file("restricted.yaml")

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Permission denied reading file" in result.errors[0]
        assert result.context["exit_code"] == ExitCode.SYSTEM_ERROR

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open")
    def test_validate_yaml_file_encoding_error(self, mock_open, mock_exists):
        """Test validation with encoding error."""
        mock_exists.return_value = True
        mock_open.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid byte")

        result = validate_yaml_file("bad_encoding.yaml")

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "File encoding error" in result.errors[0]
        assert result.context["exit_code"] == ExitCode.SYSTEM_ERROR

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open")
    def test_validate_yaml_file_empty(self, mock_open, mock_exists):
        """Test validation of empty file."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "   \n\t  "

        result = validate_yaml_file("empty.yaml")

        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "Task file is empty" in result.warnings[0]
        assert result.context["exit_code"] == ExitCode.SUCCESS

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open")
    @patch("yaml.safe_load")
    def test_validate_yaml_file_yaml_error(self, mock_yaml_load, mock_open, mock_exists):
        """Test validation with YAML syntax error."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "invalid: yaml: content:"
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML syntax")

        result = validate_yaml_file("invalid.yaml")

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "YAML syntax error" in result.errors[0]
        assert result.context["exit_code"] == ExitCode.VALIDATION_ERROR

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open")
    @patch("yaml.safe_load")
    def test_validate_yaml_file_valid(self, mock_yaml_load, mock_open, mock_exists):
        """Test validation of valid YAML file."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = "medium: []"
        mock_yaml_load.return_value = {"Medium": []}

        result = validate_yaml_file("valid.yaml")

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.context["exit_code"] == ExitCode.SUCCESS


class TestValidateYamlContent:
    """Test validate_yaml_content function."""

    def test_validate_yaml_content_empty(self):
        """Test validation of empty YAML content."""
        result = validate_yaml_content("")

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert result.message == "Empty YAML content is valid"
        assert result.data["structure"] == "empty"
        assert len(result.warnings) == 1
        assert "Content is empty" in result.warnings[0]

    def test_validate_yaml_content_valid(self):
        """Test validation of valid YAML content."""
        content = """
        medium:
          - id: 1
            title: "Test task"
            status: "pending"
            priority: "Medium"
        """

        result = validate_yaml_content(content)

        assert result.success is True
        assert result.exit_code == ExitCode.SUCCESS
        assert result.data["structure"] == "valid"
        assert result.data["task_count"] == 1

    @patch("yaml.safe_load")
    def test_validate_yaml_content_yaml_error(self, mock_yaml_load):
        """Test validation with YAML parsing error."""
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid syntax")

        result = validate_yaml_content("invalid: yaml: content:")

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert result.message == "YAML syntax error"
        assert len(result.errors) == 1
        assert "YAML parsing failed" in result.errors[0]

    def test_validate_yaml_content_schema_error(self):
        """Test validation with schema validation error."""
        # Invalid task data that should fail schema validation
        content = """
        medium:
          - id: "not_an_integer"
            title: "Test task"
            status: "pending"
            priority: "Medium"
        """

        result = validate_yaml_content(content)

        assert result.success is False
        assert result.exit_code == ExitCode.VALIDATION_ERROR
        assert result.message == "Schema validation failed"


class TestValidateAutomationEnvironment:
    """Test validate_automation_environment function."""

    @patch("os.path.exists")
    def test_validate_automation_environment_missing_dirs(self, mock_exists):
        """Test validation with missing required directories."""

        def exists_side_effect(path):
            return path not in ["scripts/dev", "docs"]

        mock_exists.side_effect = exists_side_effect

        result = validate_automation_environment()

        assert result.is_valid is False
        assert len(result.errors) >= 2
        assert any("Required directory missing: scripts/dev" in error for error in result.errors)
        assert any("Required directory missing: docs" in error for error in result.errors)

    @patch("os.path.exists")
    def test_validate_automation_environment_missing_files(self, mock_exists):
        """Test validation with missing required files."""

        def exists_side_effect(path):
            # Directories exist, but files don't
            if path in ["scripts/dev", "docs", ".git"]:
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        result = validate_automation_environment()

        assert result.is_valid is False
        assert len(result.errors) >= 3  # 3 required files
        assert any("Required file missing" in error for error in result.errors)

    @patch("os.path.exists")
    @patch("sys.version_info", (3, 7))  # Mock old Python version
    def test_validate_automation_environment_old_python(self, mock_exists):
        """Test validation with old Python version."""
        mock_exists.return_value = True  # All files exist

        result = validate_automation_environment()

        assert result.is_valid is False
        assert len(result.errors) >= 1
        assert any("Python 3.8+ required" in error for error in result.errors)

    @patch("os.path.exists")
    @patch("builtins.__import__")
    def test_validate_automation_environment_missing_packages(self, mock_import, mock_exists):
        """Test validation with missing required packages."""
        mock_exists.return_value = True  # All files exist

        def import_side_effect(name):
            if name in ["yaml", "pydantic"]:
                raise ImportError(f"No module named '{name}'")
            return Mock()

        mock_import.side_effect = import_side_effect

        result = validate_automation_environment()

        assert result.is_valid is False
        assert len(result.errors) >= 2
        assert any("Required package missing: PyYAML" in error for error in result.errors)
        assert any("Required package missing: pydantic" in error for error in result.errors)

    @patch("os.path.exists")
    def test_validate_automation_environment_no_git(self, mock_exists):
        """Test validation without git repository."""

        def exists_side_effect(path):
            return path != ".git"  # Everything exists except .git

        mock_exists.side_effect = exists_side_effect

        result = validate_automation_environment()

        assert result.is_valid is True  # Git is not required, just a warning
        assert len(result.warnings) >= 1
        assert any("Not in a git repository" in warning for warning in result.warnings)


class TestCreateValidationSummary:
    """Test create_validation_summary function."""

    def test_create_validation_summary_mixed_results(self):
        """Test creating summary with mixed validation results."""
        results = [
            ValidationResult(True, [], ["warning1"], {}),
            ValidationResult(False, ["error1", "error2"], [], {}),
            ValidationResult(True, [], [], {}),
            ValidationResult(False, ["error3"], ["warning2"], {}),
        ]

        summary = create_validation_summary(results)

        assert summary["total_validations"] == 4
        assert summary["successful_validations"] == 2
        assert summary["failed_validations"] == 2
        assert summary["total_errors"] == 3
        assert summary["total_warnings"] == 2
        assert summary["overall_success"] is False
        assert "error1" in summary["errors"]
        assert "warning1" in summary["warnings"]

    def test_create_validation_summary_all_success(self):
        """Test creating summary with all successful results."""
        results = [
            ValidationResult(True, [], [], {}),
            ValidationResult(True, [], ["minor warning"], {}),
        ]

        summary = create_validation_summary(results)

        assert summary["total_validations"] == 2
        assert summary["successful_validations"] == 2
        assert summary["failed_validations"] == 0
        assert summary["total_errors"] == 0
        assert summary["total_warnings"] == 1
        assert summary["overall_success"] is True

    def test_create_validation_summary_empty_list(self):
        """Test creating summary with empty results list."""
        summary = create_validation_summary([])

        assert summary["total_validations"] == 0
        assert summary["successful_validations"] == 0
        assert summary["failed_validations"] == 0
        assert summary["total_errors"] == 0
        assert summary["total_warnings"] == 0
        assert summary["overall_success"] is True  # No errors means success


class TestValidateSchemaCompatibility:
    """Test validate_schema_compatibility function."""

    def test_validate_schema_compatibility_valid(self):
        """Test schema compatibility with valid structure."""
        data = {
            "Critical": [],
            "High": [],
            "Medium": [],
            "Low": [],
            "archive": [],
            "metadata": {"version": "1.0"},
        }

        result = validate_schema_compatibility(data)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_schema_compatibility_missing_sections(self):
        """Test schema compatibility with missing priority sections."""
        data = {
            "High": [],
            "Medium": [],
            # Missing critical, low, archive
        }

        result = validate_schema_compatibility(data)

        assert result.is_valid is True  # Missing sections are warnings
        assert len(result.warnings) == 1
        assert "Missing priority sections" in result.warnings[0]
        assert "Critical" in result.warnings[0]
        assert "Low" in result.warnings[0]

    def test_validate_schema_compatibility_invalid_metadata(self):
        """Test schema compatibility with invalid metadata."""
        data = {
            "Critical": [],
            "High": [],
            "Medium": [],
            "Low": [],
            "archive": [],
            "metadata": "not_a_dict",
        }

        result = validate_schema_compatibility(data)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Field 'metadata' must be a dictionary" in result.errors[0]

    def test_validate_schema_compatibility_no_version(self):
        """Test schema compatibility with missing version in metadata."""
        data = {
            "Critical": [],
            "High": [],
            "Medium": [],
            "Low": [],
            "archive": [],
            "metadata": {"author": "test"},
        }

        result = validate_schema_compatibility(data)

        assert result.is_valid is True  # Missing version is warning
        assert len(result.warnings) == 1
        assert "No version information" in result.warnings[0]


class TestHelperFunctions:
    """Test private helper functions."""

    def test_check_duplicate_task_ids(self):
        """Test _check_duplicate_task_ids function."""
        task1 = Mock(spec=Task)
        task1.id = 1
        task1.title = "Task 1"

        task2 = Mock(spec=Task)
        task2.id = 1
        task2.title = "Task 2"

        errors = []
        _check_duplicate_task_ids([task1, task2], errors)

        assert len(errors) == 1
        assert "Duplicate task ID 1" in errors[0]
        assert "Task 1" in errors[0]
        assert "Task 2" in errors[0]

    def test_check_prerequisites_exist(self):
        """Test _check_prerequisites_exist function."""
        task1 = Mock(spec=Task)
        task1.title = "Task 1"
        task1.prerequisites = ["Nonexistent task"]

        task2 = Mock(spec=Task)
        task2.title = "Task 2"
        task2.prerequisites = []

        errors = []
        _check_prerequisites_exist([task1, task2], errors)

        assert len(errors) == 1
        assert "unknown prerequisite" in errors[0]
        assert "Nonexistent task" in errors[0]

    def test_has_circular_dependency(self):
        """Test _has_circular_dependency function."""
        task_a = Mock(spec=Task)
        task_a.prerequisites = ["Task B"]

        task_b = Mock(spec=Task)
        task_b.prerequisites = ["Task A"]

        all_tasks = {"Task A": task_a, "Task B": task_b}

        # Test circular dependency detection
        assert _has_circular_dependency("Task A", task_a, all_tasks, set()) is True
        assert _has_circular_dependency("Task B", task_b, all_tasks, set()) is True

    def test_has_circular_dependency_no_cycle(self):
        """Test _has_circular_dependency with no cycle."""
        task_a = Mock(spec=Task)
        task_a.prerequisites = ["Task B"]

        task_b = Mock(spec=Task)
        task_b.prerequisites = []

        all_tasks = {"Task A": task_a, "Task B": task_b}

        assert _has_circular_dependency("Task A", task_a, all_tasks, set()) is False

    def test_is_valid_time_estimate(self):
        """Test _is_valid_time_estimate function."""
        # Valid formats
        assert _is_valid_time_estimate("30 minutes") is True
        assert _is_valid_time_estimate("2 hours") is True
        assert _is_valid_time_estimate("1 day") is True
        assert _is_valid_time_estimate("3 weeks") is True
        assert _is_valid_time_estimate("2h") is True
        assert _is_valid_time_estimate("30m") is True
        assert _is_valid_time_estimate("2:30") is True

        # Invalid formats
        assert _is_valid_time_estimate("sometime") is False
        assert _is_valid_time_estimate("a long time") is False
        assert _is_valid_time_estimate("123") is False
        assert _is_valid_time_estimate("") is False


class TestIntegration:
    """Integration tests combining multiple validation components."""

    def test_full_validation_workflow(self):
        """Test complete validation workflow from YAML to task list."""
        yaml_content = """
        high:
          - id: 1
            title: "Important task"
            status: "pending"
            priority: "High"
            estimated_time: "2 hours"
            subtasks:
              - name: "Subtask 1"
                completed: true
              - name: "Subtask 2"
                completed: false
        medium:
          - id: 2
            title: "Medium task"
            status: "completed"
            priority: "Medium"
            prerequisites: ["Important task"]
        """

        # Validate YAML content
        content_result = validate_yaml_content(yaml_content)
        assert content_result.success is True

        # Parse and validate task list
        data = yaml.safe_load(yaml_content)
        task_list = TaskList(data)
        list_result = validate_task_list(task_list)

        assert list_result.is_valid is True
        assert len(list_result.warnings) == 1  # Completed task should have finish date

    def test_validation_error_propagation(self):
        """Test that validation errors propagate correctly through the system."""
        # Create invalid YAML content
        yaml_content = """
        medium:
          - id: 1
            title: "Task 1"
            status: "pending"
            priority: "Medium"
          - id: 1  # Duplicate ID
            title: "Task 2"
            status: "pending"
            priority: "Medium"
        """

        # Should succeed at YAML level but fail at task list validation
        content_result = validate_yaml_content(yaml_content)
        assert content_result.success is False
        assert "Duplicate task ID" in str(content_result.errors)

    def test_comprehensive_environment_validation(self):
        """Test comprehensive environment validation scenario."""
        with (
            patch("os.path.exists") as mock_exists,
            patch("sys.version_info", (3, 9)),
            patch("builtins.__import__") as mock_import,
        ):
            # Mock successful environment
            mock_exists.return_value = True
            mock_import.return_value = Mock()

            result = validate_automation_environment()

            assert result.is_valid is True
            # Should have some warnings (like Python version info)
            assert len(result.warnings) >= 1
