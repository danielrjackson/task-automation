"""Exercise native runner argument boundaries with disposable test files."""

import json
import pathlib
import subprocess
import sys

import pytest

from taskautomation import run_tests


def test_run_preserves_literal_arguments_without_shell_expansion(monkeypatch):
    """Shell syntax and environment references must reach the child unchanged."""
    monkeypatch.setenv("MIGRATION_LITERAL_VALUE", "expanded")
    arguments = ["two words", "x&echo", "%MIGRATION_LITERAL_VALUE%", "$HOME", "literal;token"]
    status, output = run_tests.run([
        sys.executable, "-c", "import json,sys; print(json.dumps(sys.argv[1:]))", *arguments,
    ])
    assert status == 0
    assert json.loads(output) == arguments


@pytest.mark.parametrize("coverage", ["none", "html", "terminal"])
def test_pytest_command_uses_current_interpreter_and_intact_arguments(coverage):
    """The runner must not depend on a PATH-selected pytest executable."""
    arguments = ["-k", "first or second", "tests with spaces/test_example.py"]
    command = run_tests.build_pytest_command(coverage, arguments)
    assert command[:4] == [sys.executable, "-m", "pytest", "-v"]
    assert command[-len(arguments):] == arguments
    assert ("--cov=taskautomation" in command) == (coverage != "none")


def test_runner_cli_accepts_separator_and_test_path_with_spaces(tmp_path):
    """Run actual pytest without touching any project task list."""
    test_file = tmp_path / "tests with spaces" / "test_portable_example.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "from pathlib import Path\ndef test_portable_example():\n"
        f"    assert Path.cwd() == Path({str(tmp_path)!r})\n", encoding="utf-8",
    )
    script = tmp_path / "src" / "taskautomation" / "run_tests.py"
    script.parent.mkdir(parents=True)
    script.write_bytes(pathlib.Path(run_tests.__file__).read_bytes())
    launch_directory = tmp_path / "launch elsewhere"
    launch_directory.mkdir()
    result = subprocess.run(
        [sys.executable, str(script), "--coverage", "none", "--quiet", "--", str(test_file)],
        cwd=launch_directory, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "docs" / "TASKS.md").exists()
