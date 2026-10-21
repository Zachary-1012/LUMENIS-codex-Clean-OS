"""Canonical SQLite connection primitive for LUMENIS Shared Capability."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

from .paths import main_db_path


def connect_sqlite(
    db_path: Optional[str] = None,
    *,
    timeout: float = 30.0,
    row_factory: bool = True,
    check_same_thread: bool = True,
    isolation_level: Optional[str] = "DEFERRED",
    wal: bool = True,
    foreign_keys: bool = True,
    busy_timeout_ms: int = 30000,
    read_only: bool = False,
    immutable: bool = False,
) -> sqlite3.Connection:
    """Open SQLite through the canonical database authority.

    Explicit db_path is reserved for disposable tests, controlled migration
    tooling, or an explicitly architecture-registered SYSTEM operational store.
    Ordinary business callers omit it and resolve main_db_path() at call time.
    immutable is reserved for independently read-back, fully closed snapshots
    that will not change during this connection. It requires read_only and an
    explicit non-canonical path, never the live business database or WAL files.
    """
    path = os.path.abspath(db_path or main_db_path())
    if immutable:
        if not read_only or db_path is None:
            raise ValueError("immutable requires an explicit read-only snapshot")
        requested = Path(path)
        if any(component.is_symlink() for component in [requested, *requested.parents]):
            raise ValueError("immutable snapshot must not traverse symbolic links")
        if requested.exists() and requested.stat().st_nlink != 1:
            raise ValueError("immutable snapshot must not have hard-link aliases")
        canonical = Path(main_db_path()).resolve()
        snapshot = Path(path).resolve()
        if snapshot == canonical or (snapshot.exists() and canonical.exists()
                                     and os.path.samefile(snapshot, canonical)):
            raise ValueError("immutable cannot open the live canonical database")
        if any(os.path.lexists(str(snapshot) + suffix) for suffix in ("-wal", "-shm", "-journal")):
            raise ValueError("immutable snapshot must have no live SQLite sidecars")
    if read_only:
        target = f"file:{path.replace(os.sep, '/')}?mode=ro"
        if immutable:
            target = Path(path).as_uri() + "?mode=ro&immutable=1"
        conn = sqlite3.connect(
            target,
            uri=True,
            timeout=timeout,
            check_same_thread=check_same_thread,
            isolation_level=isolation_level,
        )
    else:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(
            path,
            timeout=timeout,
            check_same_thread=check_same_thread,
            isolation_level=isolation_level,
        )
    if row_factory:
        conn.row_factory = sqlite3.Row
    if busy_timeout_ms > 0:
        conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
    if wal and not read_only:
        conn.execute("PRAGMA journal_mode=WAL")
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys=ON")
    return conn
