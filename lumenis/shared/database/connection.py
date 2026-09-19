"""Canonical SQLite connection primitive for LUMENIS Shared Capability."""
from __future__ import annotations

import os
import sqlite3
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
) -> sqlite3.Connection:
    """Open SQLite through the canonical database authority.

    Explicit db_path is reserved for disposable tests and controlled migration
    tooling. Omitting it always resolves main_db_path() at call time.
    """
    path = os.path.abspath(db_path or main_db_path())
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
    if wal:
        conn.execute("PRAGMA journal_mode=WAL")
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys=ON")
    return conn
