"""
Durably publish fresh backups without replacing previous backup files.

This does not make the task-file update atomic. A failed operation retains its
new staging/recovery material and never authorizes the caller to alter source.
Concurrent source modification and hardware ignoring flush requests are outside
this guarantee. No privilege, original-file attribute or ACL is changed.
"""

import os
import shutil
import tempfile
import uuid
from pathlib import Path


class BackupPersistenceError(OSError):

    """Backup publication or durability failed; retain the indicated material."""


def _sync_file(descriptor: int) -> None:
    os.fsync(descriptor)


def _windows_directory_api():
    import ctypes
    from ctypes import wintypes

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    api.CreateFileW.restype = wintypes.HANDLE
    api.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                ctypes.c_void_p, wintypes.DWORD]
    api.GetFileInformationByHandleEx.restype = wintypes.BOOL
    api.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    api.FlushFileBuffers.restype = wintypes.BOOL
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    return api


def _sync_directory(path: Path) -> None:
    """Persist namespace metadata; unsupported access/storage is an error."""
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return
    import ctypes
    from ctypes import wintypes

    class Tag(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("tag", wintypes.DWORD)]

    api = _windows_directory_api()
    handle = api.CreateFileW(str(path.absolute()), 0x40000000, 7, None, 3, 0x02200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = Tag()
        if not api.GetFileInformationByHandleEx(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not info.attributes & 0x10 or info.attributes & 0x400:
            raise OSError("Backup directory must be a non-reparse directory")
        if not api.FlushFileBuffers(handle):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        api.CloseHandle(handle)


def _ensure_directory(path: Path) -> None:
    missing = []
    current = path
    while not current.exists():
        if current.parent == current:
            raise OSError("Backup directory has no existing filesystem ancestor")
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(exist_ok=True)
        _sync_directory(directory)
        _sync_directory(directory.parent)
    _sync_directory(path)


def copy_backup(source: Path, preferred: Path, *, preserve_metadata: bool) -> Path:
    """
    Return only after a complete fresh backup and its name are flushed.

    The preferred name is never overwritten. Collisions select another name;
    partial files stay visibly marked `.pending`. Errors may leave a complete
    published backup whose durability is unconfirmed, so no automatic retry or
    deletion is attempted. Callers must not modify the source on failure.
    """
    # Check directory support before staging source bytes. The final flush is
    # still required after publication; this preflight is not a commit barrier.
    _ensure_directory(preferred.parent)
    descriptor, name = tempfile.mkstemp(prefix=f".{preferred.name}.", suffix=".pending",
                                       dir=preferred.parent)
    pending = Path(name)
    published = None
    try:
        try:
            if preserve_metadata:
                shutil.copy2(source, pending)
            else:
                shutil.copyfile(source, pending)
            _sync_file(descriptor)
        finally:
            os.close(descriptor)
        for attempt in range(16):
            candidate = (preferred if attempt == 0 else
                         preferred.with_name(f"{preferred.stem}-{uuid.uuid4().hex}{preferred.suffix}"))
            try:
                if os.name == "nt":
                    # Windows rename fails if candidate exists; os.replace is forbidden here.
                    os.rename(pending, candidate)
                else:
                    os.link(pending, candidate)
                    published = candidate
                    pending.unlink()
                published = candidate
                break
            except FileExistsError:
                continue
        if published is None:
            raise OSError("Could not reserve a fresh backup publication name")
        _sync_directory(preferred.parent)
        return published
    except Exception as error:
        raise BackupPersistenceError(
            f"Backup persistence unconfirmed; source must remain unchanged; "
            f"staging={pending}; published={published}: {error}"
        ) from error
