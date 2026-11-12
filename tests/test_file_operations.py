#!/usr/bin/env python3
"""
Tests for file_operations module.

This module tests safe file I/O operations with backup/recovery mechanisms,
validation, and safety checks for YAML-based task management files.

Test Coverage:
- File backup and restore operations
- YAML file loading and saving with validation
- Safe file read/write operations
- System safety and prerequisite validation
- File integrity checks
- Error handling and edge cases
- Integration workflows
"""

import os
import pathlib
import tempfile
from unittest.mock import Mock, patch

import pytest
import yaml

from src.taskautomation.file_operations import (
    BACKUP_DIR,
    ROOT,
    TASKS_FILE,
    _check_disk_space,
    _check_git_availability,
    _check_python_version,
    _check_required_directories,
    backup_tasks_file,
    check_file_integrity,
    load_tasks_file,
    load_yaml_file,
    read_file_safely,
    restore_tasks_file,
    save_tasks_file,
    save_yaml_file,
    validate_system_prerequisites,
    verify_operation_safety,
    write_file_safely,
)
from src.taskautomation.task_types import ExitCode, ValidationResult


class TestConstants:
    """Test module constants and path resolution."""

    def test_root_path_resolution(self):
        """Test that ROOT is resolved correctly."""
        assert isinstance(ROOT, pathlib.Path)
        assert ROOT.is_absolute()

    def test_tasks_file_path(self):
        """Test TASKS_FILE path construction."""
        assert isinstance(TASKS_FILE, pathlib.Path)
        assert TASKS_FILE == ROOT / "docs" / "tasks.yaml"

    def test_backup_dir_path(self):
        """Test BACKUP_DIR path construction."""
        assert isinstance(BACKUP_DIR, pathlib.Path)
        assert BACKUP_DIR == ROOT / ".task_backups"


class TestBackupTasksFile:
    """Test backup_tasks_file function."""

    def test_backup_success(self):
        """Test successful backup creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temp tasks file
            tasks_file = pathlib.Path(temp_dir) / "tasks.yaml"
            tasks_file.write_text("test: data\n")

            # Mock the module constants
            with (
                patch("src.taskautomation.file_operations.TASKS_FILE", tasks_file),
                patch(
                    "src.taskautomation.file_operations.BACKUP_DIR",
                    pathlib.Path(temp_dir) / "backups",
                ),
            ):
                backup_path = backup_tasks_file()

                assert backup_path.exists()
                assert backup_path.parent == pathlib.Path(temp_dir) / "backups"
                assert backup_path.name.startswith("tasks_")
                assert backup_path.name.endswith(".yaml")
                assert backup_path.read_text() == "test: data\n"

    def test_backup_with_suffix(self):
        """Test backup creation with custom suffix."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temp tasks file
            tasks_file = pathlib.Path(temp_dir) / "tasks.yaml"
            tasks_file.write_text("test: data\n")

            # Mock the module constants
            with (
                patch("src.taskautomation.file_operations.TASKS_FILE", tasks_file),
                patch(
                    "src.taskautomation.file_operations.BACKUP_DIR",
                    pathlib.Path(temp_dir) / "backups",
                ),
            ):
                backup_path = backup_tasks_file("pre_test")

                assert backup_path.exists()
                assert "_pre_test" in backup_path.name
                assert backup_path.name.endswith(".yaml")

    def test_backup_file_not_found(self):
        """Test backup when tasks file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = pathlib.Path(temp_dir) / "nonexistent.yaml"

            with patch("src.taskautomation.file_operations.TASKS_FILE", nonexistent_file):
                with pytest.raises(FileNotFoundError, match="Tasks file not found"):
                    backup_tasks_file()

    def test_backup_creates_directory(self):
        """Test that backup directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temp tasks file
            tasks_file = pathlib.Path(temp_dir) / "tasks.yaml"
            tasks_file.write_text("test: data\n")
            backup_dir = pathlib.Path(temp_dir) / "new_backups"

            # Ensure backup directory doesn't exist
            assert not backup_dir.exists()

            with (
                patch("src.taskautomation.file_operations.TASKS_FILE", tasks_file),
                patch("src.taskautomation.file_operations.BACKUP_DIR", backup_dir),
            ):
                backup_path = backup_tasks_file()

                assert backup_dir.exists()
                assert backup_path.exists()

    @patch("shutil.copy2")
    def test_backup_copy_error(self, mock_copy):
        """Test backup when copy operation fails."""
        mock_copy.side_effect = OSError("Copy failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_file = pathlib.Path(temp_dir) / "tasks.yaml"
            tasks_file.write_text("test: data\n")

            with (
                patch("src.taskautomation.file_operations.TASKS_FILE", tasks_file),
                patch(
                    "src.taskautomation.file_operations.BACKUP_DIR",
                    pathlib.Path(temp_dir) / "backups",
                ),
            ):
                with pytest.raises(OSError, match="Copy failed"):
                    backup_tasks_file()


class TestRestoreTasksFile:
    """Test restore_tasks_file function."""

    def test_restore_success(self):
        """Test successful file restoration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create backup file
            backup_file = pathlib.Path(temp_dir) / "backup.yaml"
            backup_file.write_text("restored: data\n")

            # Create current tasks file
            tasks_file = pathlib.Path(temp_dir) / "tasks.yaml"
            tasks_file.write_text("current: data\n")

            with (
                patch("src.taskautomation.file_operations.TASKS_FILE", tasks_file),
                patch(
                    "src.taskautomation.file_operations.BACKUP_DIR",
                    pathlib.Path(temp_dir) / "backups",
                ),
            ):
                result = restore_tasks_file(backup_file)

                assert result.success
                assert result.exit_code == ExitCode.SUCCESS
                assert "restored successfully" in result.message
                assert tasks_file.read_text() == "restored: data\n"
                assert str(backup_file) in result.data["backup_path"]

    def test_restore_backup_not_found(self):
        """Test restore when backup file doesn't exist."""
        nonexistent_backup = pathlib.Path("/nonexistent/backup.yaml")

        result = restore_tasks_file(nonexistent_backup)

        assert not result.success
        assert result.exit_code == ExitCode.SYSTEM_ERROR
        assert "Backup file not found" in result.message
        assert "Backup file not found" in result.errors[0]

    def test_restore_without_current_file(self):
        """Test restore when current tasks file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create backup file
            backup_file = pathlib.Path(temp_dir) / "backup.yaml"
            backup_file.write_text("restored: data\n")

            # Current tasks file doesn't exist
            tasks_file = pathlib.Path(temp_dir) / "tasks.yaml"

            with patch("src.taskautomation.file_operations.TASKS_FILE", tasks_file):
                result = restore_tasks_file(backup_file)

                assert result.success
                assert result.exit_code == ExitCode.SUCCESS
                assert tasks_file.read_text() == "restored: data\n"

    @patch("src.taskautomation.file_operations.backup_tasks_file")
    def test_restore_backup_current_fails(self, mock_backup):
        """Test restore when backing up current file fails."""
        mock_backup.side_effect = Exception("Backup failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create backup file
            backup_file = pathlib.Path(temp_dir) / "backup.yaml"
            backup_file.write_text("restored: data\n")

            # Create current tasks file
            tasks_file = pathlib.Path(temp_dir) / "tasks.yaml"
            tasks_file.write_text("current: data\n")

            with patch("src.taskautomation.file_operations.TASKS_FILE", tasks_file):
                result = restore_tasks_file(backup_file)

                assert result.success  # Still succeeds, just warns
                assert "Could not backup current file" in result.warnings[0]
                assert tasks_file.read_text() == "restored: data\n"

    @patch("shutil.copy2")
    def test_restore_copy_error(self, mock_copy):
        """Test restore when copy operation fails."""
        mock_copy.side_effect = OSError("Copy failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_file = pathlib.Path(temp_dir) / "backup.yaml"
            backup_file.write_text("restored: data\n")

            result = restore_tasks_file(backup_file)

            assert not result.success
            assert result.exit_code == ExitCode.SYSTEM_ERROR
            assert "File restore failed" in result.message
            assert "Restore error: Copy failed" in result.errors[0]


class TestLoadTasksFile:
    """Test load_tasks_file function."""

    def test_load_success_with_validation(self):
        """Test successful file loading with validation."""
        yaml_content = """
tasks:
  critical: []
  high: []
  medium: []
  low: []
archived_tasks: []
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            # Mock validation and parsing
            mock_validation = ValidationResult(is_valid=True, errors=[], warnings=[], context={})
            mock_task_list = Mock()

            with (
                patch(
                    "src.taskautomation.file_operations.validate_yaml_content",
                    return_value=mock_validation,
                ),
                patch(
                    "src.taskautomation.file_operations.parse_yaml_tasks",
                    return_value=mock_task_list,
                ),
            ):
                task_list, raw_data = load_tasks_file(temp_path, validate=True)

                assert task_list == mock_task_list
                assert isinstance(raw_data, dict)
                assert "tasks" in raw_data
        finally:
            temp_path.unlink()

    def test_load_success_without_validation(self):
        """Test successful file loading without validation."""
        yaml_content = """
tasks:
  critical: []
  high: []
  medium: []
  low: []
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            mock_task_list = Mock()

            with patch(
                "src.taskautomation.file_operations.parse_yaml_tasks", return_value=mock_task_list
            ):
                task_list, raw_data = load_tasks_file(temp_path, validate=False)

                assert task_list == mock_task_list
                assert isinstance(raw_data, dict)
        finally:
            temp_path.unlink()

    def test_load_uses_default_path(self):
        """Test loading uses TASKS_FILE as default."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("tasks: {}\n")
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            mock_task_list = Mock()

            with (
                patch("src.taskautomation.file_operations.TASKS_FILE", temp_path),
                patch(
                    "src.taskautomation.file_operations.parse_yaml_tasks",
                    return_value=mock_task_list,
                ),
            ):
                task_list, raw_data = load_tasks_file(validate=False)

                assert task_list == mock_task_list
        finally:
            temp_path.unlink()

    def test_load_file_not_found(self):
        """Test loading when file doesn't exist."""
        nonexistent_file = pathlib.Path("/nonexistent/file.yaml")

        with pytest.raises(FileNotFoundError, match="Tasks file not found"):
            load_tasks_file(nonexistent_file)

    def test_load_yaml_error(self):
        """Test loading with invalid YAML."""
        invalid_yaml = "invalid: yaml: content: ["

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_yaml)
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            with pytest.raises(yaml.YAMLError, match="Failed to parse YAML file"):
                load_tasks_file(temp_path)
        finally:
            temp_path.unlink()

    def test_load_validation_failure(self):
        """Test loading with validation failure."""
        yaml_content = "invalid: structure\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            mock_validation = ValidationResult(
                is_valid=False, errors=["Invalid structure", "Missing required fields"], warnings=[]
            )

            with patch(
                "src.taskautomation.file_operations.validate_yaml_content",
                return_value=mock_validation,
            ):
                with pytest.raises(ValueError, match="Tasks file validation failed"):
                    load_tasks_file(temp_path, validate=True)
        finally:
            temp_path.unlink()

    def test_load_empty_file(self):
        """Test loading empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            mock_task_list = Mock()

            with patch(
                "src.taskautomation.file_operations.parse_yaml_tasks", return_value=mock_task_list
            ):
                task_list, raw_data = load_tasks_file(temp_path, validate=False)

                assert task_list == mock_task_list
                assert raw_data == {}
        finally:
            temp_path.unlink()


class TestReadFileSafely:
    """Test read_file_safely function."""

    def test_read_success(self):
        """Test successful file reading."""
        content = "This is test content\nWith multiple lines\n"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            result = read_file_safely(temp_path)

            assert result.success
            assert result.exit_code == ExitCode.SUCCESS
            assert result.data["content"] == content
            assert result.data["size"] == len(content)
            assert result.data["lines"] == 3  # Including empty line at end
            assert result.data["encoding"] == "utf-8"
        finally:
            temp_path.unlink()

    def test_read_with_custom_encoding(self):
        """Test reading with custom encoding."""
        content = "Test content"

        with tempfile.NamedTemporaryFile(mode="w", encoding="latin-1", delete=False) as f:
            f.write(content)
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            result = read_file_safely(temp_path, encoding="latin-1")

            assert result.success
            assert result.data["content"] == content
            assert result.data["encoding"] == "latin-1"
        finally:
            temp_path.unlink()

    def test_read_file_not_found(self):
        """Test reading when file doesn't exist."""
        nonexistent_file = pathlib.Path("/nonexistent/file.txt")

        result = read_file_safely(nonexistent_file)

        assert not result.success
        assert result.exit_code == ExitCode.SYSTEM_ERROR
        assert "File not found" in result.message
        assert f"File not found: {nonexistent_file}" in result.errors[0]

    def test_read_not_a_file(self):
        """Test reading when path is not a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = pathlib.Path(temp_dir)

            result = read_file_safely(dir_path)

            assert not result.success
            assert result.exit_code == ExitCode.SYSTEM_ERROR
            assert "Path is not a file" in result.message
            assert f"Path is not a file: {dir_path}" in result.errors[0]

    @patch("pathlib.Path.read_text")
    def test_read_encoding_error(self, mock_read_text):
        """Test reading with encoding error."""
        mock_read_text.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = pathlib.Path(f.name)

        try:
            result = read_file_safely(temp_path)

            assert not result.success
            assert result.exit_code == ExitCode.SYSTEM_ERROR
            assert "File read failed" in result.message
            assert "Read error:" in result.errors[0]
        finally:
            temp_path.unlink()


class TestSaveTasksFile:
    """Test save_tasks_file function."""

    def test_save_success(self):
        """Test successful file saving with validation."""
        mock_task_list = Mock()
        mock_task_list.to_dict.return_value = {"tasks": {"Critical": []}}
        mock_validation = ValidationResult(is_valid=True, errors=[], warnings=[], context={})

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test_tasks.yaml"

            with patch(
                "src.taskautomation.file_operations.validate_task_list",
                return_value=mock_validation,
            ):
                result = save_tasks_file(mock_task_list, file_path)

                assert result.success
                assert result.exit_code == ExitCode.SUCCESS
                assert "saved successfully" in result.message
                assert file_path.exists()

                # Verify YAML content
                with open(file_path) as f:
                    saved_data = yaml.safe_load(f)
                assert saved_data == {"tasks": {"Critical": []}}

    def test_save_with_backup(self):
        """Test saving with backup creation."""
        mock_task_list = Mock()
        mock_task_list.to_dict.return_value = {"tasks": {"Critical": []}}
        mock_validation = ValidationResult(is_valid=True, errors=[], warnings=[], context={})

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test_tasks.yaml"

            # Create existing file
            file_path.write_text("old: content\n")

            with (
                patch(
                    "src.taskautomation.file_operations.validate_task_list",
                    return_value=mock_validation,
                ),
                patch("src.taskautomation.file_operations.backup_tasks_file") as mock_backup,
            ):
                mock_backup.return_value = pathlib.Path(temp_dir) / "backup.yaml"

                result = save_tasks_file(mock_task_list, file_path, backup=True)

                assert result.success
                mock_backup.assert_called_once_with("pre_save")
                assert "backup_path" in result.data

    def test_save_without_backup(self):
        """Test saving without backup."""
        mock_task_list = Mock()
        mock_task_list.to_dict.return_value = {"tasks": {"Critical": []}}
        mock_validation = ValidationResult(is_valid=True, errors=[], warnings=[], context={})

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test_tasks.yaml"

            with patch(
                "src.taskautomation.file_operations.validate_task_list",
                return_value=mock_validation,
            ):
                result = save_tasks_file(mock_task_list, file_path, backup=False)

                assert result.success
                assert "backup_path" not in result.data

    def test_save_dry_run(self):
        """Test dry run mode."""
        mock_task_list = Mock()
        mock_task_list.to_dict.return_value = {"tasks": {"Critical": []}}
        mock_validation = ValidationResult(is_valid=True, errors=[], warnings=[], context={})

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test_tasks.yaml"

            with patch(
                "src.taskautomation.file_operations.validate_task_list",
                return_value=mock_validation,
            ):
                result = save_tasks_file(mock_task_list, file_path, dry_run=True)

                assert result.success
                assert "Dry run - file would be saved" in result.message
                assert not file_path.exists()
                assert "yaml_preview" in result.data

    def test_save_validation_failure(self):
        """Test saving with validation failure."""
        mock_task_list = Mock()
        mock_task_list.to_dict.return_value = {"invalid": "structure"}
        mock_validation = ValidationResult(
            is_valid=False, errors=["Invalid structure"], warnings=["Minor issue"]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test_tasks.yaml"

            with patch(
                "src.taskautomation.file_operations.validate_task_list",
                return_value=mock_validation,
            ):
                result = save_tasks_file(mock_task_list, file_path)

                assert not result.success
                assert result.exit_code == ExitCode.VALIDATION_ERROR
                assert "TaskList validation failed" in result.message
                assert "Invalid structure" in result.errors
                assert "Minor issue" in result.warnings

    def test_save_without_validation(self):
        """Test saving without validation."""
        mock_task_list = Mock()
        mock_task_list.to_dict.return_value = {"tasks": {"Critical": []}}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test_tasks.yaml"

            result = save_tasks_file(mock_task_list, file_path, validate=False)

            assert result.success
            assert file_path.exists()

    def test_save_uses_default_path(self):
        """Test saving uses TASKS_FILE as default."""
        mock_task_list = Mock()
        mock_task_list.to_dict.return_value = {"tasks": {"Critical": []}}

        with tempfile.TemporaryDirectory() as temp_dir:
            default_path = pathlib.Path(temp_dir) / "default_tasks.yaml"

            with patch("src.taskautomation.file_operations.TASKS_FILE", default_path):
                result = save_tasks_file(mock_task_list, validate=False)

                assert result.success
                assert default_path.exists()

    @patch("builtins.open")
    def test_save_write_error(self, mock_open_func):
        """Test saving with write error."""
        mock_open_func.side_effect = OSError("Write failed")
        mock_task_list = Mock()
        mock_task_list.to_dict.return_value = {"tasks": {"Critical": []}}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test_tasks.yaml"

            result = save_tasks_file(mock_task_list, file_path, validate=False)

            assert not result.success
            assert result.exit_code == ExitCode.SYSTEM_ERROR
            assert "File save failed" in result.message
            assert "Save error: Write failed" in result.errors[0]


class TestWriteFileSafely:
    """Test write_file_safely function."""

    def test_write_success(self):
        """Test successful file writing."""
        content = "This is test content"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.txt"

            result = write_file_safely(file_path, content)

            assert result.success
            assert result.exit_code == ExitCode.SUCCESS
            assert "File written successfully" in result.message
            assert file_path.read_text() == content
            assert result.data["content_size"] == len(content)

    def test_write_with_backup(self):
        """Test writing with backup creation."""
        old_content = "Old content"
        new_content = "New content"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.txt"
            file_path.write_text(old_content)

            result = write_file_safely(file_path, new_content, backup=True)

            assert result.success
            assert file_path.read_text() == new_content
            assert "backup_path" in result.data

            # Verify backup exists and has old content
            backup_path = pathlib.Path(result.data["backup_path"])
            assert backup_path.exists()
            assert backup_path.read_text() == old_content

    def test_write_create_directories(self):
        """Test writing with directory creation."""
        content = "Test content"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "new" / "nested" / "test.txt"

            result = write_file_safely(file_path, content, create_dirs=True)

            assert result.success
            assert file_path.exists()
            assert file_path.read_text() == content

    def test_write_no_create_directories(self):
        """Test writing without directory creation."""
        content = "Test content"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "new" / "test.txt"

            result = write_file_safely(file_path, content, create_dirs=False)

            assert not result.success
            assert result.exit_code == ExitCode.SYSTEM_ERROR
            assert "Write error:" in result.errors[0]

    def test_write_custom_encoding(self):
        """Test writing with custom encoding."""
        content = "Test content with special chars: ñ á é í"

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.txt"

            result = write_file_safely(file_path, content, encoding="latin-1")

            assert result.success
            assert result.data["encoding"] == "latin-1"
            assert file_path.read_text(encoding="latin-1") == content

    @patch("pathlib.Path.write_text")
    def test_write_encoding_error(self, mock_write_text):
        """Test writing with encoding error."""
        mock_write_text.side_effect = UnicodeEncodeError("utf-8", "", 0, 1, "invalid character")

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.txt"

            result = write_file_safely(file_path, "content")

            assert not result.success
            assert result.exit_code == ExitCode.SYSTEM_ERROR
            assert "Write error:" in result.errors[0]


class TestSaveYamlFile:
    """Test save_yaml_file function."""

    def test_save_yaml_success(self):
        """Test successful YAML file saving."""
        data = {"test": "data", "nested": {"key": "value"}}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.yaml"

            result = save_yaml_file(file_path, data)

            assert result.success
            assert result.exit_code == ExitCode.SUCCESS
            assert "YAML file written successfully" in result.message
            assert file_path.exists()

            # Verify YAML content
            with open(file_path) as f:
                loaded_data = yaml.safe_load(f)
            assert loaded_data == data

    def test_save_yaml_with_backup(self):
        """Test YAML saving with backup."""
        old_data = {"old": "data"}
        new_data = {"new": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.yaml"

            # Create existing file
            with open(file_path, "w") as f:
                yaml.dump(old_data, f)

            result = save_yaml_file(file_path, new_data, backup=True)

            assert result.success
            assert "backup_path" in result.data

            # Verify new content
            with open(file_path) as f:
                loaded_data = yaml.safe_load(f)
            assert loaded_data == new_data

            # Verify backup
            backup_path = pathlib.Path(result.data["backup_path"])
            assert backup_path.exists()
            with open(backup_path) as f:
                backup_data = yaml.safe_load(f)
            assert backup_data == old_data

    def test_save_yaml_create_directories(self):
        """Test YAML saving with directory creation."""
        data = {"test": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "new" / "test.yaml"

            result = save_yaml_file(file_path, data, create_dirs=True)

            assert result.success
            assert file_path.exists()

    def test_save_yaml_data_keys_tracking(self):
        """Test data keys are tracked in result."""
        data = {"key1": "value1", "key2": "value2"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.yaml"

            result = save_yaml_file(file_path, data)

            assert result.success
            assert set(result.data["data_keys"]) == {"key1", "key2"}

    def test_save_yaml_non_dict_data(self):
        """Test saving non-dict data."""
        data = ["item1", "item2", "item3"]

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.yaml"

            result = save_yaml_file(file_path, data)

            assert result.success
            assert result.data["data_keys"] == "non-dict"

    @patch("builtins.open")
    def test_save_yaml_write_error(self, mock_open_func):
        """Test YAML saving with write error."""
        mock_open_func.side_effect = OSError("Write failed")
        data = {"test": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.yaml"

            result = save_yaml_file(file_path, data)

            assert not result.success
            assert result.exit_code == ExitCode.SYSTEM_ERROR
            assert "YAML file write failed" in result.message
            assert "YAML write error: Write failed" in result.errors[0]


class TestLoadYamlFile:
    """Test load_yaml_file function."""

    def test_load_yaml_success(self):
        """Test successful YAML file loading."""
        data = {"test": "data", "nested": {"key": "value"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            result = load_yaml_file(temp_path)

            assert result.success
            assert result.exit_code == ExitCode.SUCCESS
            assert "YAML file loaded successfully" in result.message
            assert result.data["yaml_data"] == data
            assert set(result.data["data_keys"]) == {"test", "nested"}
        finally:
            temp_path.unlink()

    def test_load_yaml_empty_file(self):
        """Test loading empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            result = load_yaml_file(temp_path)

            assert result.success
            assert result.data["yaml_data"] == {}
            assert result.data["data_keys"] == []
        finally:
            temp_path.unlink()

    def test_load_yaml_file_not_found(self):
        """Test loading when YAML file doesn't exist."""
        nonexistent_file = pathlib.Path("/nonexistent/file.yaml")

        result = load_yaml_file(nonexistent_file)

        assert not result.success
        assert result.exit_code == ExitCode.SYSTEM_ERROR
        assert "YAML file not found" in result.message
        assert f"YAML file not found: {nonexistent_file}" in result.errors[0]

    def test_load_yaml_not_a_file(self):
        """Test loading when path is not a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = pathlib.Path(temp_dir)

            result = load_yaml_file(dir_path)

            assert not result.success
            assert result.exit_code == ExitCode.SYSTEM_ERROR
            assert "Path is not a file" in result.message

    def test_load_yaml_parsing_error(self):
        """Test loading with YAML parsing error."""
        invalid_yaml = "invalid: yaml: content: ["

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_yaml)
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            result = load_yaml_file(temp_path)

            assert not result.success
            assert result.exit_code == ExitCode.VALIDATION_ERROR
            assert "YAML parsing failed" in result.message
            assert "YAML parsing error:" in result.errors[0]
        finally:
            temp_path.unlink()

    def test_load_yaml_non_dict_data(self):
        """Test loading YAML file with non-dict data."""
        data = ["item1", "item2", "item3"]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            result = load_yaml_file(temp_path)

            assert result.success
            assert result.data["yaml_data"] == data
            assert result.data["data_keys"] == "non-dict"
        finally:
            temp_path.unlink()


class TestVerifyOperationSafety:
    """Test verify_operation_safety function."""

    def test_verify_safety_success(self):
        """Test successful safety verification."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.txt"
            file_path.write_text("content")

            result = verify_operation_safety("test operation", [file_path])

            assert result.is_valid
            assert result.context["operation"] == "test operation"
            assert str(file_path) in result.context["target_files"]

    def test_verify_safety_non_file_target(self):
        """Test safety verification with non-file target."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = pathlib.Path(temp_dir)

            result = verify_operation_safety("test operation", [dir_path])

            assert not result.is_valid
            assert f"Target is not a file: {dir_path}" in result.errors

    def test_verify_safety_no_write_permission(self):
        """Test safety verification with no write permission."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = pathlib.Path(f.name)

        try:
            # Make file read-only
            temp_path.chmod(0o444)

            result = verify_operation_safety("test operation", [temp_path])

            if os.name != "nt":  # Skip on Windows as permissions work differently
                assert not result.is_valid
                assert f"No write permission: {temp_path}" in result.errors
        finally:
            temp_path.chmod(0o666)  # Restore permissions for cleanup
            temp_path.unlink()

    def test_verify_safety_nonexistent_file(self):
        """Test safety verification with nonexistent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = pathlib.Path(temp_dir) / "nonexistent.txt"

            result = verify_operation_safety("test operation", [nonexistent_file])

            assert result.is_valid  # Should be valid as parent directory is writable

    def test_verify_safety_nonexistent_parent(self):
        """Test safety verification with nonexistent parent directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_file = pathlib.Path(temp_dir) / "new" / "nonexistent.txt"

            result = verify_operation_safety("test operation", [nonexistent_file])

            assert result.is_valid
            assert any("Parent directory will be created" in w for w in result.warnings)

    @patch("subprocess.run")
    def test_verify_safety_git_uncommitted_changes(self, mock_run):
        """Test safety verification with uncommitted git changes."""
        mock_run.return_value = Mock(returncode=0, stdout="M modified_file.txt\n")

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.txt"
            file_path.write_text("content")

            result = verify_operation_safety("test operation", [file_path])

            assert result.is_valid
            assert any("uncommitted changes" in w for w in result.warnings)

    @patch("subprocess.run")
    def test_verify_safety_git_not_available(self, mock_run):
        """Test safety verification when git is not available."""
        mock_run.side_effect = Exception("Git not found")

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.txt"
            file_path.write_text("content")

            result = verify_operation_safety("test operation", [file_path])

            assert result.is_valid  # Should still be valid


class TestValidateSystemPrerequisites:
    """Test validate_system_prerequisites function."""

    def test_validate_prerequisites_success(self):
        """Test successful prerequisite validation."""
        with (
            patch("src.taskautomation.file_operations._check_python_version") as mock_python,
            patch("src.taskautomation.file_operations._check_required_directories") as mock_dirs,
            patch("src.taskautomation.file_operations._check_git_availability") as mock_git,
            patch("src.taskautomation.file_operations._check_disk_space") as mock_disk,
        ):
            # Configure mocks to not add any errors
            mock_python.return_value = None
            mock_dirs.return_value = None
            mock_git.return_value = True
            mock_disk.return_value = None

            result = validate_system_prerequisites()

            assert result.is_valid
            assert len(result.errors) == 0

    def test_validate_prerequisites_with_errors(self):
        """Test prerequisite validation with errors."""

        def add_python_error(errors, context):
            errors.append("Python version too old")

        def add_dir_error(errors):
            errors.append("Missing required directory")

        with (
            patch(
                "src.taskautomation.file_operations._check_python_version",
                side_effect=add_python_error,
            ),
            patch(
                "src.taskautomation.file_operations._check_required_directories",
                side_effect=add_dir_error,
            ),
            patch("src.taskautomation.file_operations._check_git_availability") as mock_git,
            patch("src.taskautomation.file_operations._check_disk_space") as mock_disk,
        ):
            mock_git.return_value = False
            mock_disk.return_value = None

            result = validate_system_prerequisites()

            assert not result.is_valid
            assert "Python version too old" in result.errors
            assert "Missing required directory" in result.errors


class TestCheckPythonVersion:
    """Test _check_python_version function."""

    def test_check_python_version_success(self):
        """Test Python version check with valid version."""
        errors = []
        context = {}

        with patch("sys.version_info", (3, 9, 0)):
            _check_python_version(errors, context)

            assert len(errors) == 0
            assert context["python_version"] == "3.9.0"

    def test_check_python_version_old(self):
        """Test Python version check with old version."""
        errors = []
        context = {}

        with patch("sys.version_info", (3, 7, 0)):
            _check_python_version(errors, context)

            assert len(errors) == 1
            assert "Python 3.8+ required" in errors[0]
            assert context["python_version"] == "3.7.0"


class TestCheckRequiredDirectories:
    """Test _check_required_directories function."""

    def test_check_required_directories_success(self):
        """Test required directories check with existing directories."""
        errors = []

        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            docs_dir = root / "docs"
            scripts_dir = root / "scripts" / "dev"

            docs_dir.mkdir()
            scripts_dir.mkdir(parents=True)

            with patch("src.taskautomation.file_operations.ROOT", root):
                _check_required_directories(errors)

                assert len(errors) == 0

    def test_check_required_directories_missing(self):
        """Test required directories check with missing directories."""
        errors = []

        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)

            with patch("src.taskautomation.file_operations.ROOT", root):
                _check_required_directories(errors)

                assert len(errors) == 2
                assert any("docs" in error for error in errors)
                assert any("scripts/dev" in error for error in errors)


class TestCheckGitAvailability:
    """Test _check_git_availability function."""

    @patch("subprocess.run")
    def test_check_git_available_and_repo(self, mock_run):
        """Test git availability check with git available and in repo."""
        warnings = []
        context = {}

        # Mock git --version success and git rev-parse success
        mock_run.side_effect = [
            Mock(returncode=0),  # git --version
            Mock(returncode=0),  # git rev-parse
        ]

        result = _check_git_availability(warnings, context)

        assert result is True
        assert context["git_available"] is True
        assert context["is_git_repo"] is True
        assert len(warnings) == 0

    @patch("subprocess.run")
    def test_check_git_not_available(self, mock_run):
        """Test git availability check with git not available."""
        warnings = []
        context = {}

        mock_run.side_effect = Exception("Git not found")

        result = _check_git_availability(warnings, context)

        assert result is False
        assert context["git_available"] is False
        assert any("Git not available" in w for w in warnings)

    @patch("subprocess.run")
    def test_check_git_available_not_repo(self, mock_run):
        """Test git availability check with git available but not in repo."""
        warnings = []
        context = {}

        # Mock git --version success but git rev-parse failure
        mock_run.side_effect = [
            Mock(returncode=0),  # git --version
            Mock(returncode=1),  # git rev-parse
        ]

        result = _check_git_availability(warnings, context)

        assert result is True
        assert context["git_available"] is True
        assert context["is_git_repo"] is False
        assert any("Not in a git repository" in w for w in warnings)


class TestCheckDiskSpace:
    """Test _check_disk_space function."""

    @patch("shutil.disk_usage")
    def test_check_disk_space_sufficient(self, mock_disk_usage):
        """Test disk space check with sufficient space."""
        warnings = []
        context = {}

        # Mock 1GB free space
        mock_disk_usage.return_value = Mock(free=1024 * 1024 * 1024)

        _check_disk_space(warnings, context)

        assert len(warnings) == 0
        assert context["free_space_mb"] == 1024

    @patch("shutil.disk_usage")
    def test_check_disk_space_low(self, mock_disk_usage):
        """Test disk space check with low space."""
        warnings = []
        context = {}

        # Mock 50MB free space
        mock_disk_usage.return_value = Mock(free=50 * 1024 * 1024)

        _check_disk_space(warnings, context)

        assert len(warnings) == 1
        assert "Low disk space: 50MB" in warnings[0]
        assert context["free_space_mb"] == 50

    @patch("shutil.disk_usage")
    def test_check_disk_space_error(self, mock_disk_usage):
        """Test disk space check with error."""
        warnings = []
        context = {}

        mock_disk_usage.side_effect = OSError("Disk error")

        _check_disk_space(warnings, context)

        assert len(warnings) == 1
        assert "Could not check disk space" in warnings[0]


class TestCheckFileIntegrity:
    """Test check_file_integrity function."""

    def test_check_integrity_success(self):
        """Test successful file integrity check."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            result = check_file_integrity(temp_path)

            assert result.is_valid
            assert len(result.errors) == 0
            assert result.context["file_path"] == str(temp_path)
            assert "size" in result.context
            assert "modified" in result.context
            assert "permissions" in result.context
        finally:
            temp_path.unlink()

    def test_check_integrity_file_not_exists(self):
        """Test integrity check when file doesn't exist."""
        nonexistent_file = pathlib.Path("/nonexistent/file.txt")

        result = check_file_integrity(nonexistent_file)

        assert not result.is_valid
        assert f"File does not exist: {nonexistent_file}" in result.errors

    def test_check_integrity_not_a_file(self):
        """Test integrity check when path is not a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = pathlib.Path(temp_dir)

            result = check_file_integrity(dir_path)

            assert not result.is_valid
            assert f"Path is not a file: {dir_path}" in result.errors

    def test_check_integrity_empty_file(self):
        """Test integrity check with empty file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.flush()  # Create empty file
            temp_path = pathlib.Path(f.name)

        try:
            result = check_file_integrity(temp_path)

            assert result.is_valid
            assert any("File is empty" in w for w in result.warnings)
            assert result.context["size"] == 0
        finally:
            temp_path.unlink()

    @patch("os.access")
    def test_check_integrity_no_read_permission(self, mock_access):
        """Test integrity check with no read permission."""

        def mock_access_func(path, mode):
            if mode == os.R_OK:
                return False
            return True

        mock_access.side_effect = mock_access_func

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("content")
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            result = check_file_integrity(temp_path)

            assert not result.is_valid
            assert f"File is not readable: {temp_path}" in result.errors
        finally:
            temp_path.unlink()

    @patch("os.access")
    def test_check_integrity_no_write_permission(self, mock_access):
        """Test integrity check with no write permission."""

        def mock_access_func(path, mode):
            if mode == os.W_OK:
                return False
            return True

        mock_access.side_effect = mock_access_func

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("content")
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            result = check_file_integrity(temp_path)

            assert result.is_valid  # Still valid, just warns
            assert any(f"File is not writable: {temp_path}" in w for w in result.warnings)
        finally:
            temp_path.unlink()

    @patch("pathlib.Path.stat")
    def test_check_integrity_stat_error(self, mock_stat):
        """Test integrity check with stat error."""
        mock_stat.side_effect = OSError("Stat failed")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("content")
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            result = check_file_integrity(temp_path)

            assert not result.is_valid
            assert "Error checking file integrity: Stat failed" in result.errors
        finally:
            temp_path.unlink()


class TestIntegrationWorkflows:
    """Test integration workflows combining multiple functions."""

    def test_backup_save_restore_workflow(self):
        """Test complete backup, save, and restore workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create initial tasks file
            tasks_file = pathlib.Path(temp_dir) / "tasks.yaml"
            original_content = "original: data\n"
            tasks_file.write_text(original_content)

            backup_dir = pathlib.Path(temp_dir) / "backups"

            with (
                patch("src.taskautomation.file_operations.TASKS_FILE", tasks_file),
                patch("src.taskautomation.file_operations.BACKUP_DIR", backup_dir),
            ):
                # Create backup
                backup_path = backup_tasks_file("workflow_test")
                assert backup_path.exists()
                assert backup_path.read_text() == original_content

                # Modify original file
                modified_content = "modified: data\n"
                tasks_file.write_text(modified_content)

                # Restore from backup
                result = restore_tasks_file(backup_path)
                assert result.success
                assert tasks_file.read_text() == original_content

    def test_load_modify_save_workflow(self):
        """Test loading, modifying, and saving workflow."""
        yaml_content = """
tasks:
  critical: []
  high: []
  medium: []
  low: []
archived_tasks: []
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            # Mock the dependencies
            mock_validation = ValidationResult(is_valid=True, errors=[], warnings=[], context={})
            mock_task_list = Mock()
            mock_task_list.to_dict.return_value = {"tasks": {"Critical": [{"id": "test"}]}}

            with (
                patch(
                    "src.taskautomation.file_operations.validate_yaml_content",
                    return_value=mock_validation,
                ),
                patch(
                    "src.taskautomation.file_operations.parse_yaml_tasks",
                    return_value=mock_task_list,
                ),
                patch(
                    "src.taskautomation.file_operations.validate_task_list",
                    return_value=mock_validation,
                ),
            ):
                # Load file
                task_list, raw_data = load_tasks_file(temp_path)
                assert task_list == mock_task_list

                # Save modified file
                result = save_tasks_file(mock_task_list, temp_path)
                assert result.success

                # Verify saved content
                with open(temp_path) as f:
                    saved_data = yaml.safe_load(f)
                assert saved_data == {"tasks": {"Critical": [{"id": "test"}]}}
        finally:
            temp_path.unlink()

    def test_safety_check_before_operations(self):
        """Test safety verification before file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = pathlib.Path(temp_dir) / "test.txt"
            file_path.write_text("content")

            # Verify operation safety
            safety_result = verify_operation_safety("test write", [file_path])
            assert safety_result.is_valid

            # Proceed with safe operation
            content = "new content"
            write_result = write_file_safely(file_path, content)
            assert write_result.success
            assert file_path.read_text() == content

    def test_prerequisite_check_integration(self):
        """Test prerequisite validation integration."""

        # Mock all prerequisite checks to pass
        def mock_python_check(errors, context):
            context["python_version"] = "3.9.0"

        def mock_dirs_check(errors):
            pass  # No errors

        def mock_git_check(warnings, context):
            context["git_available"] = True
            context["is_git_repo"] = True
            return True

        def mock_disk_check(warnings, context):
            context["free_space_mb"] = 1000

        with (
            patch(
                "src.taskautomation.file_operations._check_python_version",
                side_effect=mock_python_check,
            ),
            patch(
                "src.taskautomation.file_operations._check_required_directories",
                side_effect=mock_dirs_check,
            ),
            patch(
                "src.taskautomation.file_operations._check_git_availability",
                side_effect=mock_git_check,
            ),
            patch(
                "src.taskautomation.file_operations._check_disk_space", side_effect=mock_disk_check
            ),
        ):
            result = validate_system_prerequisites()

            assert result.is_valid
            assert result.context["python_version"] == "3.9.0"
            assert result.context["git_available"] is True
            assert result.context["free_space_mb"] == 1000

    def test_file_integrity_before_operations(self):
        """Test file integrity checks before operations."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            f.flush()
            temp_path = pathlib.Path(f.name)

        try:
            # Check integrity first
            integrity_result = check_file_integrity(temp_path)
            assert integrity_result.is_valid

            # Proceed with operation
            new_content = "updated content"
            write_result = write_file_safely(temp_path, new_content)
            assert write_result.success
            assert temp_path.read_text() == new_content
        finally:
            temp_path.unlink()

    def test_complete_workflow_chain(self):
        """Test a complete workflow chain of operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = pathlib.Path(temp_dir) / "tasks.yaml"

            # Create initial data
            initial_data = {"tasks": {"Critical": [{"id": "task1", "title": "Test task"}]}}

            # Mock dependencies
            mock_validation = ValidationResult(is_valid=True, errors=[], warnings=[], context={})
            mock_task_list = Mock()
            mock_task_list.to_dict.return_value = initial_data

            with (
                patch(
                    "src.taskautomation.file_operations.validate_yaml_content",
                    return_value=mock_validation,
                ),
                patch(
                    "src.taskautomation.file_operations.parse_yaml_tasks",
                    return_value=mock_task_list,
                ),
                patch(
                    "src.taskautomation.file_operations.validate_task_list",
                    return_value=mock_validation,
                ),
                patch("src.taskautomation.file_operations.verify_operation_safety") as mock_safety,
                patch(
                    "src.taskautomation.file_operations.validate_system_prerequisites"
                ) as mock_prereq,
                patch("src.taskautomation.file_operations.check_file_integrity") as mock_integrity,
            ):
                # Setup mocks
                mock_safety.return_value = ValidationResult(is_valid=True, errors=[], warnings=[], context={})
                mock_prereq.return_value = ValidationResult(is_valid=True, errors=[], warnings=[], context={})
                mock_integrity.return_value = ValidationResult(
                    is_valid=True, errors=[], warnings=[]
                )

                # 1. Check prerequisites
                prereq_result = validate_system_prerequisites()
                assert prereq_result.is_valid

                # 2. Check file integrity (if file exists)
                if task_file.exists():
                    integrity_result = check_file_integrity(task_file)
                    assert integrity_result.is_valid

                # 3. Verify operation safety
                safety_result = verify_operation_safety("workflow test", [task_file])
                assert safety_result.is_valid

                # 4. Create backup before operation
                backup_result = backup_tasks_file(task_file)
                # Backup might fail if file doesn't exist, which is OK

                # 5. Save new data
                save_result = save_tasks_file(mock_task_list, task_file)
                assert save_result.success

                # 6. Load and verify
                loaded_list, raw_data = load_tasks_file(task_file)
                assert loaded_list == mock_task_list

                # Verify all steps were called
                mock_safety.assert_called()
                mock_prereq.assert_called()
