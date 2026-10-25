"""Persistent signing configuration for an explicitly selected local workspace."""
from __future__ import annotations

import ctypes
import json
import os
import secrets
import sqlite3
import stat
import tempfile
from pathlib import Path

from lumenis.shared.database import DatabaseRepository


class WorkspaceSigningError(ValueError):
    pass


def _dpapi(value: bytes, *, decrypt: bool) -> bytes:
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
    source, result = Blob(len(value), buffer), Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        call = crypt.CryptUnprotectData
        call.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                         ctypes.POINTER(Blob)]
        description = None
    else:
        call = crypt.CryptProtectData
        call.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                         ctypes.POINTER(Blob)]
        description = "OEVIRA workspace Evidence signing"
    call.restype = wintypes.BOOL
    if not call(ctypes.byref(source), description, None, None, None, 1,
                ctypes.byref(result)):
        raise WorkspaceSigningError("WORKSPACE_SIGNING_KEY_PROTECTION_FAILED")
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel.LocalFree(result.data)


def _private_directory(directory: Path) -> None:
    if os.name != "nt":
        directory.chmod(0o700)
        return
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                       ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                         ctypes.c_void_p, wintypes.DWORD,
                                         ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p,
                                             ctypes.POINTER(wintypes.LPWSTR)]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.DWORD)]
    advapi.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    token, needed = wintypes.HANDLE(), wintypes.DWORD()
    sid_text, descriptor = wintypes.LPWSTR(), ctypes.c_void_p()
    try:
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
            raise OSError("token unavailable")
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(needed))
        if not needed.value:
            raise OSError("token identity unavailable")
        buffer = ctypes.create_string_buffer(needed.value)
        if not advapi.GetTokenInformation(token, 1, buffer, needed, ctypes.byref(needed)):
            raise OSError("token identity unavailable")
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(sid_text)):
            raise OSError("token identity unavailable")
        sddl = f"D:P(A;OICI;FA;;;{sid_text.value})(A;OICI;FA;;;SY)"
        if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(descriptor), None
        ) or not advapi.SetFileSecurityW(str(directory), 0x80000004, descriptor):
            raise OSError("private directory unavailable")
    except OSError:
        raise WorkspaceSigningError("WORKSPACE_SIGNING_DIRECTORY_PROTECTION_FAILED") from None
    finally:
        if token:
            kernel.CloseHandle(token)
        if sid_text:
            kernel.LocalFree(sid_text)
        if descriptor:
            kernel.LocalFree(descriptor)


def _assert_regular_path(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise WorkspaceSigningError("WORKSPACE_SIGNING_PATH_REDIRECTED")
    if path.exists() and path.is_file() and path.stat().st_nlink != 1:
        raise WorkspaceSigningError("WORKSPACE_SIGNING_PATH_ALIASED")


def _signed_key_ids(database: Path) -> set[str]:
    if not database.exists():
        if any(Path(str(database) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
            raise WorkspaceSigningError("WORKSPACE_SIGNING_DATABASE_RECOVERY_REQUIRED")
        return set()
    try:
        with DatabaseRepository(str(database)).connection(read_only=True) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(app_evidence_records)")}
            if not {"integrity_digest", "integrity_key_id"} <= columns:
                if columns & {"integrity_digest", "integrity_key_id", "integrity_version"}:
                    raise WorkspaceSigningError("WORKSPACE_SIGNING_SCHEMA_RECOVERY_REQUIRED")
                return set()
            rows = connection.execute(
                "SELECT DISTINCT integrity_key_id FROM app_evidence_records "
                "WHERE COALESCE(integrity_digest, '') <> '' "
                "OR COALESCE(integrity_key_id, '') <> ''"
            )
            return {str(row[0] or "") for row in rows}
    except WorkspaceSigningError:
        raise
    except (OSError, sqlite3.Error):
        raise WorkspaceSigningError("WORKSPACE_SIGNING_DATABASE_UNREADABLE") from None


def activate_workspace_signing(data_root: str, database_path: str, environ=None) -> Path:
    env = os.environ if environ is None else environ
    root, database = Path(data_root).absolute(), Path(database_path).absolute()
    _assert_regular_path(root)
    _assert_regular_path(database)
    root, database = root.resolve(), database.resolve()
    if root == database or not database.is_relative_to(root):
        raise WorkspaceSigningError("WORKSPACE_SIGNING_DATABASE_OUTSIDE_ROOT")
    directory = root / "security"
    file = directory / ("evidence-signing.dpapi" if os.name == "nt" else "evidence-signing.json")
    _assert_regular_path(file)
    signed_ids = _signed_key_ids(database)
    relative_db = database.relative_to(root).as_posix()
    if not file.exists():
        if signed_ids:
            raise WorkspaceSigningError("WORKSPACE_SIGNING_KEY_RECOVERY_REQUIRED")
        if env.get("LUMENIS_EVIDENCE_HMAC_KEY_RING") or env.get("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID"):
            raise WorkspaceSigningError("WORKSPACE_SIGNING_KEY_IMPORT_REQUIRED")
        directory.mkdir(parents=True, exist_ok=True)
        _private_directory(directory)
        key_id = "workspace-" + secrets.token_hex(16)
        payload = {"version": 1, "database": relative_db, "active_id": key_id,
                   "keys": {key_id: secrets.token_urlsafe(48)}}
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        protected = _dpapi(raw, decrypt=False) if os.name == "nt" else raw
        fd, temporary = tempfile.mkstemp(prefix=".evidence-signing-", dir=directory)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(protected)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            try:
                os.link(temporary, file)
            except FileExistsError:
                pass
        finally:
            Path(temporary).unlink(missing_ok=True)
    _assert_regular_path(file)
    if not file.is_file() or file.stat().st_size > 65536:
        raise WorkspaceSigningError("WORKSPACE_SIGNING_KEY_INVALID")
    if os.name != "nt" and stat.S_IMODE(file.stat().st_mode) & 0o077:
        raise WorkspaceSigningError("WORKSPACE_SIGNING_KEY_PERMISSIONS_INVALID")
    try:
        raw = file.read_bytes()
        decoded = _dpapi(raw, decrypt=True) if os.name == "nt" else raw
        payload = json.loads(decoded)
        keys, active = payload["keys"], payload["active_id"]
        if (payload["version"] != 1 or payload["database"] != relative_db
                or not isinstance(keys, dict) or not isinstance(active, str)
                or active not in keys or not keys
                or not all(isinstance(k, str) and k and isinstance(v, str)
                           and len(v) >= 32 for k, v in keys.items())):
            raise ValueError("invalid signing configuration")
    except (OSError, ValueError, TypeError, KeyError):
        raise WorkspaceSigningError("WORKSPACE_SIGNING_KEY_UNREADABLE") from None
    if not signed_ids <= set(keys):
        raise WorkspaceSigningError("WORKSPACE_SIGNING_KEY_RECOVERY_REQUIRED")
    env["LUMENIS_EVIDENCE_HMAC_KEY_RING"] = json.dumps(keys, sort_keys=True)
    env["LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID"] = active
    return file
