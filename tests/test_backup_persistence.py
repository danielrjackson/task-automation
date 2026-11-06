"""Fresh backup names and real persistence failures must protect original tasks."""

import datetime
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from taskautomation import backup_persistence as persistence
from taskautomation import file_operations, task_parser
from taskautomation.task_schema import TaskList


@pytest.mark.parametrize("metadata", [False, True])
def test_backup_publication_preserves_existing_backup(tmp_path, metadata):
    """Publish a complete new copy without overwriting an existing chosen name."""
    source, preferred = tmp_path / "tasks", tmp_path / "backup"
    source.write_bytes(b"synthetic current\r\n")
    preferred.write_bytes(b"synthetic historical\n")
    published = persistence.copy_backup(source, preferred, preserve_metadata=metadata)
    assert published != preferred
    assert published.read_bytes() == source.read_bytes()
    assert preferred.read_bytes() == b"synthetic historical\n"
    assert not list(tmp_path.glob("*.pending"))


def test_same_second_backups_cannot_overwrite_history(tmp_path, monkeypatch):
    """Timestamp collisions retain both selected versions."""
    source = tmp_path / "tasks.yaml"
    monkeypatch.setattr(file_operations, "TASKS_FILE", source)
    monkeypatch.setattr(file_operations, "BACKUP_DIR", tmp_path / "backups")
    fixed = datetime.datetime(2026, 11, 6, 12)
    monkeypatch.setattr(file_operations, "datetime",
                        SimpleNamespace(datetime=SimpleNamespace(now=lambda: fixed)))
    source.write_bytes(b"first synthetic version")
    first = file_operations.backup_tasks_file()
    source.write_bytes(b"second synthetic version")
    second = file_operations.backup_tasks_file()
    assert first != second
    assert first.read_bytes() == b"first synthetic version"
    assert second.read_bytes() == b"second synthetic version"


def test_repeated_parser_saves_retain_previous_backup_and_report_new_path(tmp_path):
    """The parser cannot silently clobber its previous `.backup` file."""
    path = tmp_path / "tasks.yaml"
    path.write_bytes(b"first synthetic version")
    first = task_parser.save_yaml_file(TaskList(), path)
    assert first.success
    path.write_bytes(b"second synthetic version")
    second = task_parser.save_yaml_file(TaskList(), path)
    assert second.success
    first_path, second_path = Path(first.data["backup_path"]), Path(second.data["backup_path"])
    assert first_path != second_path
    assert first_path.read_bytes() == b"first synthetic version"
    assert second_path.read_bytes() == b"second synthetic version"


@pytest.mark.parametrize("kind", ["parser", "operations"])
@pytest.mark.parametrize("phase", ["file", "directory"])
def test_failed_backup_persistence_prevents_task_mutation(tmp_path, monkeypatch, kind, phase):
    """A backup barrier failure must stop the save before opening its source."""
    source = tmp_path / "tasks.yaml"
    original = b"# original synthetic bytes\r\n"
    source.write_bytes(original)
    monkeypatch.setattr(file_operations, "TASKS_FILE", source)
    monkeypatch.setattr(file_operations, "BACKUP_DIR", tmp_path)
    if phase == "file":
        def fail_sync(descriptor):
            raise OSError("synthetic file persistence failure")
        monkeypatch.setattr(persistence, "_sync_file", fail_sync)
    else:
        actual = persistence._sync_directory
        calls = []

        def fail_directory(path):
            calls.append(path)
            if len(calls) == 2:
                raise OSError("synthetic namespace persistence failure")
            actual(path)
        monkeypatch.setattr(persistence, "_sync_directory", fail_directory)
    result = (task_parser.save_yaml_file(TaskList(), source) if kind == "parser" else
              file_operations.save_tasks_file(TaskList(), source, validate=False))
    assert result.success is False
    assert source.read_bytes() == original
    assert "persistence unconfirmed" in " ".join(result.errors)


def test_readonly_source_metadata_is_preserved_without_changing_original(tmp_path):
    """Only disposable fixture attributes are set and restored in this test."""
    source = tmp_path / "readonly"
    source.write_bytes(b"synthetic readonly contents")
    source.chmod(0o444)
    try:
        published = persistence.copy_backup(source, tmp_path / "backup", preserve_metadata=True)
        assert published.read_bytes() == source.read_bytes()
        assert not source.stat().st_mode & 0o200
        assert not published.stat().st_mode & 0o200
    finally:
        for path in tmp_path.iterdir():
            if path.is_file():
                path.chmod(0o600)


def test_restore_refuses_without_confirmed_backup(tmp_path, monkeypatch):
    """Recovery must protect the current version before replacing its bytes."""
    current, recovery = tmp_path / "tasks.yaml", tmp_path / "recovery.yaml"
    current.write_bytes(b"synthetic current version")
    recovery.write_bytes(b"synthetic requested recovery")
    monkeypatch.setattr(file_operations, "TASKS_FILE", current)
    monkeypatch.setattr(file_operations, "BACKUP_DIR", tmp_path / "backups")

    def fail(descriptor):
        raise OSError("synthetic backup flush failure")

    monkeypatch.setattr(persistence, "_sync_file", fail)
    result = file_operations.restore_tasks_file(recovery)
    assert result.success is False
    assert current.read_bytes() == b"synthetic current version"
    assert recovery.read_bytes() == b"synthetic requested recovery"


@pytest.mark.skipif(os.name != "nt", reason="Real Windows directory flush error contract")
def test_real_windows_directory_flush_error_is_not_a_success_fallback(tmp_path, monkeypatch):
    """Keep real open/query/close operations; inject only failed FlushFileBuffers."""
    import ctypes

    api = persistence._windows_directory_api()

    def fail(handle):
        ctypes.set_last_error(5)
        return 0

    wrapped = SimpleNamespace(CreateFileW=api.CreateFileW,
        GetFileInformationByHandleEx=api.GetFileInformationByHandleEx,
        FlushFileBuffers=fail, CloseHandle=api.CloseHandle)
    monkeypatch.setattr(persistence, "_windows_directory_api", lambda: wrapped)
    with pytest.raises(OSError) as error:
        persistence._sync_directory(tmp_path)
    assert error.value.winerror == 5


@pytest.mark.parametrize("barrier", ["file", "directory"])
def test_owned_process_death_retains_source_and_recovery_material(tmp_path, barrier):
    """Kill only a synthetic process after actual data or namespace persistence."""
    source, preferred = tmp_path / "tasks", tmp_path / "backup"
    original = b"synthetic original recovery bytes\r\n"
    source.write_bytes(original)
    code = """import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('persistence',sys.argv[1])
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
barrier=sys.argv[4]
if barrier=='file':
 original=p._sync_file
 def wait(fd):
  original(fd);print('persisted',flush=True);sys.stdin.buffer.read(1)
 p._sync_file=wait
else:
 original=p._sync_directory
 count=0
 def wait(path):
  global count
  original(path);count+=1
  if count==2:print('persisted',flush=True);sys.stdin.buffer.read(1)
 p._sync_directory=wait
p.copy_backup(Path(sys.argv[2]),Path(sys.argv[3]),preserve_metadata=False)
"""
    child = subprocess.Popen([sys._base_executable, "-I", "-S", "-B", "-c", code,
        persistence.__file__, str(source), str(preferred), barrier], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        assert child.stdout.readline().strip() == b"persisted"
        child.kill()
        child.wait(timeout=5)
        assert source.read_bytes() == original
        if barrier == "file":
            pending = list(tmp_path.glob("*.pending"))
            assert len(pending) == 1
            assert pending[0].read_bytes() == original
            assert not preferred.exists()
        else:
            assert preferred.read_bytes() == original
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
        child.stdin.close()
        child.stdout.close()
        child.stderr.close()
