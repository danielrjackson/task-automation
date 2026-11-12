#!/usr/bin/env python3
"""
Comprehensive tests for git_helpers module.

This test suite covers Git integration utilities including command execution,
repository information gathering, and status checking with extensive mocking
of subprocess calls.

Test Coverage:
- run_git_command: Git command execution with success/failure scenarios
- get_git_info: Comprehensive repository information gathering
- get_current_branch: Branch name retrieval with fallbacks
- check_git_repository: Repository detection and validation
- check_git_availability: Git availability and version checking
- get_repository_status: Combined status information gathering
- ROOT constant: Path resolution testing
- Error handling: Exception scenarios and subprocess failures
- Integration: Combined workflow testing
"""

import pathlib
import subprocess
from unittest.mock import Mock, patch

from src.taskautomation.git_helpers import (
    ROOT,
    check_git_availability,
    check_git_repository,
    get_current_branch,
    get_git_info,
    get_repository_status,
    run_git_command,
)


class TestModuleConstants:
    """Test module-level constants and imports."""

    def test_root_constant(self):
        """Test ROOT constant is correctly calculated."""
        # ROOT should be the repository root (3 levels up from git_helpers.py)
        assert isinstance(ROOT, pathlib.Path)
        assert ROOT.is_absolute()

        # Should be 3 levels up from the git_helpers.py file
        git_helpers_path = (
            pathlib.Path(__file__).resolve().parent.parent
            / "src"
            / "taskautomation"
            / "git_helpers.py"
        )
        expected_root = git_helpers_path.parent.parent.parent
        assert ROOT == expected_root

    def test_imports(self):
        """Test that all necessary imports are available."""
        # Test that key modules are imported
        assert pathlib is not None
        assert subprocess is not None

        # Test that all functions are importable
        assert callable(run_git_command)
        assert callable(get_git_info)
        assert callable(get_current_branch)
        assert callable(check_git_repository)
        assert callable(check_git_availability)
        assert callable(get_repository_status)


class TestRunGitCommand:
    """Test run_git_command function with various scenarios."""

    @patch("src.taskautomation.git_helpers.subprocess.run")
    def test_successful_command(self, mock_run):
        """Test successful git command execution."""
        # Setup mock
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "  test output  \n"
        mock_result.stderr = "  \n"
        mock_run.return_value = mock_result

        # Test
        success, stdout, stderr = run_git_command(["status", "--porcelain"])

        # Verify
        assert success is True
        assert stdout == "test output"  # Should be stripped
        assert stderr == ""  # Should be stripped

        # Verify subprocess call
        mock_run.assert_called_once_with(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=False, cwd=ROOT
        )

    @patch("src.taskautomation.git_helpers.subprocess.run")
    def test_failed_command(self, mock_run):
        """Test failed git command execution."""
        # Setup mock
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "fatal: not a git repository"
        mock_run.return_value = mock_result

        # Test
        success, stdout, stderr = run_git_command(["status"])

        # Verify
        assert success is False
        assert stdout == ""
        assert stderr == "fatal: not a git repository"

    @patch("src.taskautomation.git_helpers.subprocess.run")
    def test_command_with_exception(self, mock_run):
        """Test git command execution with subprocess exception."""
        # Setup mock to raise exception
        mock_run.side_effect = FileNotFoundError("git command not found")

        # Test
        success, stdout, stderr = run_git_command(["--version"])

        # Verify
        assert success is False
        assert stdout == ""
        assert stderr == "git command not found"

    @patch("src.taskautomation.git_helpers.subprocess.run")
    def test_command_with_different_exception(self, mock_run):
        """Test git command execution with different exception type."""
        # Setup mock to raise exception
        mock_run.side_effect = PermissionError("Permission denied")

        # Test
        success, stdout, stderr = run_git_command(["config", "--list"])

        # Verify
        assert success is False
        assert stdout == ""
        assert stderr == "Permission denied"

    @patch("src.taskautomation.git_helpers.subprocess.run")
    def test_empty_command_list(self, mock_run):
        """Test run_git_command with empty command list."""
        # Setup mock
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "git version 2.34.1"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Test
        success, stdout, stderr = run_git_command([])

        # Verify
        assert success is True
        assert stdout == "git version 2.34.1"

        # Verify subprocess call with just git
        mock_run.assert_called_once_with(
            ["git"], capture_output=True, text=True, check=False, cwd=ROOT
        )

    @patch("src.taskautomation.git_helpers.subprocess.run")
    def test_command_with_whitespace_output(self, mock_run):
        """Test command execution with whitespace in output."""
        # Setup mock
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "\n\n  main  \n\n"
        mock_result.stderr = "\t\t\n"
        mock_run.return_value = mock_result

        # Test
        success, stdout, stderr = run_git_command(["branch", "--show-current"])

        # Verify output is properly stripped
        assert success is True
        assert stdout == "main"
        assert stderr == ""


class TestGetGitInfo:
    """Test get_git_info function with various repository states."""

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_complete_git_info(self, mock_run_git):
        """Test get_git_info with all information available."""

        # Setup mock responses for different git commands
        def mock_git_command(cmd):
            if cmd == ["rev-parse", "--abbrev-ref", "HEAD"]:
                return True, "main", ""
            elif cmd == ["rev-parse", "HEAD"]:
                return True, "1234567890abcdef1234567890abcdef12345678", ""
            elif cmd == ["config", "user.name"]:
                return True, "John Doe", ""
            elif cmd == ["config", "user.email"]:
                return True, "john@example.com", ""
            elif cmd == ["status", "--porcelain"]:
                return True, "", ""  # Clean repository
            else:
                return False, "", "Unknown command"

        mock_run_git.side_effect = mock_git_command

        # Test
        info = get_git_info()

        # Verify
        assert info["branch"] == "main"
        assert info["commit"] == "12345678"  # Short hash
        assert info["user_name"] == "John Doe"
        assert info["user_email"] == "john@example.com"
        assert info["is_clean"] is True
        assert info["has_uncommitted"] is False

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_git_info_with_uncommitted_changes(self, mock_run_git):
        """Test get_git_info with uncommitted changes."""

        # Setup mock responses
        def mock_git_command(cmd):
            if cmd == ["rev-parse", "--abbrev-ref", "HEAD"]:
                return True, "feature-branch", ""
            elif cmd == ["rev-parse", "HEAD"]:
                return True, "abcdef1234567890abcdef1234567890abcdef12", ""
            elif cmd == ["config", "user.name"]:
                return True, "Jane Smith", ""
            elif cmd == ["config", "user.email"]:
                return True, "jane@example.com", ""
            elif cmd == ["status", "--porcelain"]:
                return True, " M file1.py\n?? file2.py", ""  # Modified and untracked files
            else:
                return False, "", "Unknown command"

        mock_run_git.side_effect = mock_git_command

        # Test
        info = get_git_info()

        # Verify
        assert info["branch"] == "feature-branch"
        assert info["commit"] == "abcdef12"
        assert info["user_name"] == "Jane Smith"
        assert info["user_email"] == "jane@example.com"
        assert info["is_clean"] is False
        assert info["has_uncommitted"] is True

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_git_info_with_failures(self, mock_run_git):
        """Test get_git_info when git commands fail."""
        # Setup mock to always fail
        mock_run_git.return_value = (False, "", "fatal: not a git repository")

        # Test
        info = get_git_info()

        # Verify defaults are returned
        assert info["branch"] == "unknown"
        assert info["commit"] == "unknown"
        assert info["user_name"] == "unknown"
        assert info["user_email"] == "unknown"
        assert info["is_clean"] is False
        assert info["has_uncommitted"] is False

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_git_info_partial_failures(self, mock_run_git):
        """Test get_git_info with some commands succeeding and others failing."""

        # Setup mock responses with mixed success/failure
        def mock_git_command(cmd):
            if cmd == ["rev-parse", "--abbrev-ref", "HEAD"]:
                return True, "develop", ""
            elif cmd == ["rev-parse", "HEAD"]:
                return False, "", "fatal: ambiguous argument 'HEAD'"
            elif cmd == ["config", "user.name"]:
                return True, "Test User", ""
            elif cmd == ["config", "user.email"]:
                return False, "", "fatal: unable to read config"
            elif cmd == ["status", "--porcelain"]:
                return True, "A  new_file.py", ""  # Staged file
            else:
                return False, "", "Unknown command"

        mock_run_git.side_effect = mock_git_command

        # Test
        info = get_git_info()

        # Verify mixed results
        assert info["branch"] == "develop"
        assert info["commit"] == "unknown"  # Failed
        assert info["user_name"] == "Test User"
        assert info["user_email"] == "unknown"  # Failed
        assert info["is_clean"] is False
        assert info["has_uncommitted"] is True

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_git_info_short_commit_hash(self, mock_run_git):
        """Test that commit hash is properly shortened."""

        # Setup mock with very short commit hash
        def mock_git_command(cmd):
            if cmd == ["rev-parse", "HEAD"]:
                return True, "abc123", ""  # Hash shorter than 8 chars
            else:
                return False, "", ""

        mock_run_git.side_effect = mock_git_command

        # Test
        info = get_git_info()

        # Verify short hash is preserved
        assert info["commit"] == "abc123"


class TestGetCurrentBranch:
    """Test get_current_branch function."""

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_successful_branch_retrieval(self, mock_run_git):
        """Test successful branch name retrieval."""
        mock_run_git.return_value = (True, "main", "")

        result = get_current_branch()

        assert result == "main"
        mock_run_git.assert_called_once_with(["rev-parse", "--abbrev-ref", "HEAD"])

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_failed_branch_retrieval(self, mock_run_git):
        """Test failed branch name retrieval returns fallback."""
        mock_run_git.return_value = (False, "", "fatal: not a git repository")

        result = get_current_branch()

        assert result == "unknown-branch"
        mock_run_git.assert_called_once_with(["rev-parse", "--abbrev-ref", "HEAD"])

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_branch_with_whitespace(self, mock_run_git):
        """Test branch name with whitespace is properly handled."""
        mock_run_git.return_value = (True, "  feature/test-branch  ", "")

        result = get_current_branch()

        # run_git_command should strip whitespace, so we get the clean branch name
        assert result == "feature/test-branch"

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_detached_head_state(self, mock_run_git):
        """Test behavior in detached HEAD state."""
        mock_run_git.return_value = (True, "HEAD", "")

        result = get_current_branch()

        assert result == "HEAD"


class TestCheckGitRepository:
    """Test check_git_repository function."""

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_valid_git_repository(self, mock_run_git):
        """Test checking valid git repository."""
        mock_run_git.return_value = (True, ".git", "")

        is_repo, message = check_git_repository()

        assert is_repo is True
        assert message == "Git repository detected"
        mock_run_git.assert_called_once_with(["rev-parse", "--git-dir"])

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_not_git_repository(self, mock_run_git):
        """Test checking directory that is not a git repository."""
        mock_run_git.return_value = (False, "", "fatal: not a git repository")

        is_repo, message = check_git_repository()

        assert is_repo is False
        assert message == "Not in a git repository: fatal: not a git repository"
        mock_run_git.assert_called_once_with(["rev-parse", "--git-dir"])

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_git_repository_with_worktree(self, mock_run_git):
        """Test checking git repository with worktree."""
        mock_run_git.return_value = (True, "/path/to/.git/worktrees/branch", "")

        is_repo, message = check_git_repository()

        assert is_repo is True
        assert message == "Git repository detected"

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_git_repository_permission_error(self, mock_run_git):
        """Test git repository check with permission error."""
        mock_run_git.return_value = (False, "", "fatal: unable to access '.git': Permission denied")

        is_repo, message = check_git_repository()

        assert is_repo is False
        assert "Permission denied" in message


class TestCheckGitAvailability:
    """Test check_git_availability function."""

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_git_available(self, mock_run_git):
        """Test git availability check when git is available."""
        mock_run_git.return_value = (True, "git version 2.34.1", "")

        available, version_info = check_git_availability()

        assert available is True
        assert version_info == "git version 2.34.1"
        mock_run_git.assert_called_once_with(["--version"])

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_git_not_available(self, mock_run_git):
        """Test git availability check when git is not available."""
        mock_run_git.return_value = (False, "", "git: command not found")

        available, version_info = check_git_availability()

        assert available is False
        assert version_info == "Git not available: git: command not found"
        mock_run_git.assert_called_once_with(["--version"])

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_git_version_different_format(self, mock_run_git):
        """Test git availability with different version format."""
        mock_run_git.return_value = (True, "git version 2.40.0.windows.1", "")

        available, version_info = check_git_availability()

        assert available is True
        assert version_info == "git version 2.40.0.windows.1"

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_git_old_version(self, mock_run_git):
        """Test git availability with older version."""
        mock_run_git.return_value = (True, "git version 1.8.5", "")

        available, version_info = check_git_availability()

        assert available is True
        assert version_info == "git version 1.8.5"


class TestGetRepositoryStatus:
    """Test get_repository_status function with various scenarios."""

    @patch("src.taskautomation.git_helpers.check_git_availability")
    @patch("src.taskautomation.git_helpers.check_git_repository")
    @patch("src.taskautomation.git_helpers.get_git_info")
    def test_complete_repository_status(self, mock_get_git_info, mock_check_repo, mock_check_avail):
        """Test complete repository status when everything is available."""
        # Setup mocks
        mock_check_avail.return_value = (True, "git version 2.34.1")
        mock_check_repo.return_value = (True, "Git repository detected")
        mock_get_git_info.return_value = {
            "branch": "main",
            "commit": "12345678",
            "user_name": "Test User",
            "user_email": "test@example.com",
            "is_clean": True,
            "has_uncommitted": False,
        }

        # Test
        status = get_repository_status()

        # Verify
        assert status["git_available"] is True
        assert status["is_git_repo"] is True
        assert status["git_version"] == "git version 2.34.1"
        assert status["repository_info"]["branch"] == "main"
        assert status["repository_info"]["commit"] == "12345678"

        # Verify all functions were called
        mock_check_avail.assert_called_once()
        mock_check_repo.assert_called_once()
        mock_get_git_info.assert_called_once()

    @patch("src.taskautomation.git_helpers.check_git_availability")
    @patch("src.taskautomation.git_helpers.check_git_repository")
    @patch("src.taskautomation.git_helpers.get_git_info")
    def test_git_not_available(self, mock_get_git_info, mock_check_repo, mock_check_avail):
        """Test repository status when git is not available."""
        # Setup mocks
        mock_check_avail.return_value = (False, "Git not available: git: command not found")

        # Test
        status = get_repository_status()

        # Verify
        assert status["git_available"] is False
        assert status["is_git_repo"] is False
        assert status["git_version"] == "Git not available: git: command not found"
        assert status["repository_info"] == {}

        # Verify git info was not called when git is unavailable
        mock_check_avail.assert_called_once()
        mock_check_repo.assert_not_called()
        mock_get_git_info.assert_not_called()

    @patch("src.taskautomation.git_helpers.check_git_availability")
    @patch("src.taskautomation.git_helpers.check_git_repository")
    @patch("src.taskautomation.git_helpers.get_git_info")
    def test_not_git_repository(self, mock_get_git_info, mock_check_repo, mock_check_avail):
        """Test repository status when not in a git repository."""
        # Setup mocks
        mock_check_avail.return_value = (True, "git version 2.34.1")
        mock_check_repo.return_value = (
            False,
            "Not in a git repository: fatal: not a git repository",
        )

        # Test
        status = get_repository_status()

        # Verify
        assert status["git_available"] is True
        assert status["is_git_repo"] is False
        assert status["git_version"] == "git version 2.34.1"
        assert status["repository_info"] == {}

        # Verify repository check was called but git info was not
        mock_check_avail.assert_called_once()
        mock_check_repo.assert_called_once()
        mock_get_git_info.assert_not_called()

    @patch("src.taskautomation.git_helpers.check_git_availability")
    @patch("src.taskautomation.git_helpers.check_git_repository")
    @patch("src.taskautomation.git_helpers.get_git_info")
    def test_dirty_repository_status(self, mock_get_git_info, mock_check_repo, mock_check_avail):
        """Test repository status with uncommitted changes."""
        # Setup mocks
        mock_check_avail.return_value = (True, "git version 2.34.1")
        mock_check_repo.return_value = (True, "Git repository detected")
        mock_get_git_info.return_value = {
            "branch": "feature-branch",
            "commit": "abcdef12",
            "user_name": "Developer",
            "user_email": "dev@company.com",
            "is_clean": False,
            "has_uncommitted": True,
        }

        # Test
        status = get_repository_status()

        # Verify
        assert status["git_available"] is True
        assert status["is_git_repo"] is True
        assert status["repository_info"]["is_clean"] is False
        assert status["repository_info"]["has_uncommitted"] is True
        assert status["repository_info"]["branch"] == "feature-branch"


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple functions."""

    @patch("src.taskautomation.git_helpers.subprocess.run")
    def test_complete_workflow_with_mocked_subprocess(self, mock_run):
        """Test complete workflow with subprocess mocking."""

        # Setup subprocess mock to return different results for different commands
        def mock_subprocess_run(cmd, **kwargs):
            result = Mock()
            result.returncode = 0

            if cmd == ["git", "--version"]:
                result.stdout = "git version 2.34.1"
                result.stderr = ""
            elif cmd == ["git", "rev-parse", "--git-dir"]:
                result.stdout = ".git"
                result.stderr = ""
            elif cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
                result.stdout = "main"
                result.stderr = ""
            elif cmd == ["git", "rev-parse", "HEAD"]:
                result.stdout = "1234567890abcdef1234567890abcdef12345678"
                result.stderr = ""
            elif cmd == ["git", "config", "user.name"]:
                result.stdout = "Integration Test"
                result.stderr = ""
            elif cmd == ["git", "config", "user.email"]:
                result.stdout = "test@integration.com"
                result.stderr = ""
            elif cmd == ["git", "status", "--porcelain"]:
                result.stdout = ""  # Clean repository
                result.stderr = ""
            else:
                result.returncode = 1
                result.stdout = ""
                result.stderr = "unknown command"

            return result

        mock_run.side_effect = mock_subprocess_run

        # Test complete workflow
        # 1. Check git availability
        available, version = check_git_availability()
        assert available is True
        assert version == "git version 2.34.1"

        # 2. Check repository
        is_repo, message = check_git_repository()
        assert is_repo is True
        assert message == "Git repository detected"

        # 3. Get current branch
        branch = get_current_branch()
        assert branch == "main"

        # 4. Get git info
        info = get_git_info()
        assert info["branch"] == "main"
        assert info["commit"] == "12345678"
        assert info["user_name"] == "Integration Test"
        assert info["user_email"] == "test@integration.com"
        assert info["is_clean"] is True
        assert info["has_uncommitted"] is False

        # 5. Get complete status
        status = get_repository_status()
        assert status["git_available"] is True
        assert status["is_git_repo"] is True
        assert status["repository_info"]["branch"] == "main"

    @patch("src.taskautomation.git_helpers.subprocess.run")
    def test_error_propagation_through_workflow(self, mock_run):
        """Test error propagation through complete workflow."""
        # Setup subprocess mock to simulate git not available
        mock_run.side_effect = FileNotFoundError("git command not found")

        # Test that all functions handle the error gracefully
        available, version = check_git_availability()
        assert available is False
        assert "git command not found" in version

        is_repo, message = check_git_repository()
        assert is_repo is False
        assert "git command not found" in message

        branch = get_current_branch()
        assert branch == "unknown-branch"

        info = get_git_info()
        assert info["branch"] == "unknown"
        assert info["commit"] == "unknown"

        status = get_repository_status()
        assert status["git_available"] is False
        assert status["is_git_repo"] is False
        assert status["repository_info"] == {}

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_mixed_success_failure_scenario(self, mock_run_git):
        """Test scenario with mixed success and failure responses."""
        call_count = 0

        def mock_git_command(cmd):
            nonlocal call_count
            call_count += 1

            # Simulate intermittent failures
            if call_count % 2 == 0:  # Even calls fail
                return False, "", "intermittent failure"
            else:  # Odd calls succeed
                if cmd == ["--version"]:
                    return True, "git version 2.34.1", ""
                elif cmd == ["rev-parse", "--git-dir"]:
                    return True, ".git", ""
                elif cmd == ["rev-parse", "--abbrev-ref", "HEAD"]:
                    return True, "develop", ""
                else:
                    return True, "success", ""

        mock_run_git.side_effect = mock_git_command

        # Test functions with mixed results
        available, version = check_git_availability()  # Call 1 - success
        assert available is True

        is_repo, message = check_git_repository()  # Call 2 - failure
        assert is_repo is False

        branch = get_current_branch()  # Call 3 - success
        assert branch == "develop"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_empty_git_responses(self, mock_run_git):
        """Test handling of empty git command responses."""
        mock_run_git.return_value = (True, "", "")

        # Test functions with empty responses
        branch = get_current_branch()
        assert branch == ""  # Empty but successful response

        info = get_git_info()
        assert info["branch"] == ""
        assert info["commit"] == ""  # Empty commit hash
        assert info["is_clean"] is True  # Empty status means clean

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_very_long_git_responses(self, mock_run_git):
        """Test handling of very long git command responses."""
        long_output = "x" * 10000  # Very long output
        mock_run_git.return_value = (True, long_output, "")

        branch = get_current_branch()
        assert branch == long_output

        # Test commit hash truncation with long hash
        def mock_git_command(cmd):
            if cmd == ["rev-parse", "HEAD"]:
                return True, long_output, ""
            else:
                return False, "", ""

        mock_run_git.side_effect = mock_git_command
        info = get_git_info()
        assert info["commit"] == long_output[:8]  # Still truncated to 8 chars

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_special_characters_in_git_output(self, mock_run_git):
        """Test handling of special characters in git output."""
        special_branch = "feature/test-#123-@special"
        special_email = "user+test@domain.co.uk"

        def mock_git_command(cmd):
            if cmd == ["rev-parse", "--abbrev-ref", "HEAD"]:
                return True, special_branch, ""
            elif cmd == ["config", "user.email"]:
                return True, special_email, ""
            else:
                return False, "", ""

        mock_run_git.side_effect = mock_git_command

        branch = get_current_branch()
        assert branch == special_branch

        info = get_git_info()
        assert info["branch"] == special_branch
        assert info["user_email"] == special_email

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_unicode_in_git_output(self, mock_run_git):
        """Test handling of Unicode characters in git output."""
        unicode_name = "João Döe"
        unicode_branch = "feature/测试-branch"

        def mock_git_command(cmd):
            if cmd == ["config", "user.name"]:
                return True, unicode_name, ""
            elif cmd == ["rev-parse", "--abbrev-ref", "HEAD"]:
                return True, unicode_branch, ""
            else:
                return False, "", ""

        mock_run_git.side_effect = mock_git_command

        info = get_git_info()
        assert info["user_name"] == unicode_name
        assert info["branch"] == unicode_branch


class TestErrorHandling:
    """Test comprehensive error handling scenarios."""

    @patch("src.taskautomation.git_helpers.subprocess.run")
    def test_subprocess_timeout_simulation(self, mock_run):
        """Test handling of subprocess timeout-like behavior."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)

        success, stdout, stderr = run_git_command(["status"])

        assert success is False
        assert stdout == ""
        assert "TimeoutExpired" in stderr

    @patch("src.taskautomation.git_helpers.subprocess.run")
    def test_subprocess_memory_error(self, mock_run):
        """Test handling of MemoryError during subprocess."""
        mock_run.side_effect = MemoryError("Out of memory")

        success, stdout, stderr = run_git_command(["log", "--all"])

        assert success is False
        assert stdout == ""
        assert "Out of memory" in stderr

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_get_git_info_with_all_commands_failing(self, mock_run_git):
        """Test get_git_info when every git command fails."""
        mock_run_git.return_value = (False, "", "All commands fail")

        info = get_git_info()

        # Should return all default values
        expected_defaults = {
            "branch": "unknown",
            "commit": "unknown",
            "user_name": "unknown",
            "user_email": "unknown",
            "is_clean": False,
            "has_uncommitted": False,
        }

        assert info == expected_defaults

    @patch("src.taskautomation.git_helpers.run_git_command")
    def test_repository_status_chain_failures(self, mock_run_git):
        """Test get_repository_status with cascading failures."""
        # First call (git --version) succeeds, rest fail
        call_count = 0

        def mock_failing_chain(cmd):
            nonlocal call_count
            call_count += 1
            if call_count == 1 and cmd == ["--version"]:
                return True, "git version 2.34.1", ""
            else:
                return False, "", f"Command {call_count} failed"

        mock_run_git.side_effect = mock_failing_chain

        status = get_repository_status()

        assert status["git_available"] is True
        assert status["is_git_repo"] is False
        assert status["repository_info"] == {}
