"""LUMENIS P0-C database environment and copy-verification primitives.

This module never mutates a source database.  Any migration/repair workflow must
first create a SQLite-consistent copy and operate on that destination only.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List, Optional


class DatabaseEnvironment(str, Enum):
    PRODUCTION = "production"
    TEST = "test"
    EXPERIMENT = "experiment"


@dataclass(frozen=True)
class DatabaseIdentity:
    path: str
    exists: bool
    size: int = 0
    mtime_ns: int = 0
    sha256: str = ""
    integrity: str = "missing"
    foreign_key_violations: int = 0
    table_count: int = 0

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def environment_directories(repo_root: os.PathLike[str] | str) -> Dict[str, Path]:
    base = Path(repo_root).resolve() / "data"
    return {
        DatabaseEnvironment.PRODUCTION.value: base / "production",
        DatabaseEnvironment.TEST.value: base / "test",
        DatabaseEnvironment.EXPERIMENT.value: base / "experiment",
    }


def resolve_database_path(
    repo_root: os.PathLike[str] | str,
    *,
    environment: Optional[str] = None,
    explicit_path: Optional[str] = None,
) -> Path:
    """Resolve a DB without silently crossing production/test/experiment zones.

    The historical production default remains ``data/monitor.db`` for runtime
    compatibility.  Explicit test/experiment modes always use separate physical
    directories.  Tests normally override this with an OS-temp ZBC_DB_PATH.
    """
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    selected = (environment or os.environ.get("LUMENIS_DATA_ENVIRONMENT") or
                DatabaseEnvironment.PRODUCTION.value).strip().lower()
    if selected not in {item.value for item in DatabaseEnvironment}:
        raise ValueError(f"unknown database environment: {selected}")
    root = Path(repo_root).resolve()
    if selected == DatabaseEnvironment.PRODUCTION.value:
        return root / "data" / "monitor.db"
    return environment_directories(root)[selected] / "monitor.db"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def database_identity(path_value: os.PathLike[str] | str) -> DatabaseIdentity:
    path = Path(path_value).expanduser().resolve()
    if not path.exists():
        return DatabaseIdentity(path=str(path), exists=False)
    stat = path.stat()
    integrity = "unreadable"
    fk_count = 0
    table_count = 0
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        fk_count = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        table_count = int(connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0])
    finally:
        connection.close()
    return DatabaseIdentity(
        path=str(path), exists=True, size=stat.st_size, mtime_ns=stat.st_mtime_ns,
        sha256=_sha256(path), integrity=integrity,
        foreign_key_violations=fk_count, table_count=table_count,
    )


def backup_to_isolated_copy(
    source_value: os.PathLike[str] | str,
    destination_value: os.PathLike[str] | str,
) -> Path:
    source = Path(source_value).expanduser().resolve()
    destination = Path(destination_value).expanduser().resolve()
    if source == destination:
        raise ValueError("source and destination database must differ")
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    source_connection = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()
    return destination


def foreign_key_rows(path_value: os.PathLike[str] | str) -> List[Dict[str, object]]:
    path = Path(path_value).expanduser().resolve()
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        rows = connection.execute("PRAGMA foreign_key_check").fetchall()
        return [
            {"table": row[0], "rowid": row[1], "parent": row[2], "fkid": row[3]}
            for row in rows
        ]
    finally:
        connection.close()


def foreign_key_details(path_value: os.PathLike[str] | str) -> List[Dict[str, object]]:
    """Return row-level FK roots without modifying the database."""
    path = Path(path_value).expanduser().resolve()
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    details: List[Dict[str, object]] = []
    try:
        for violation in connection.execute("PRAGMA foreign_key_check").fetchall():
            table, rowid, parent, fkid = violation
            fk_rows = connection.execute(
                f'PRAGMA foreign_key_list("{str(table).replace(chr(34), chr(34) * 2)}")'
            ).fetchall()
            fk = next((row for row in fk_rows if int(row[0]) == int(fkid)), None)
            child_column = fk[3] if fk else None
            parent_column = fk[4] if fk else None
            child_value = None
            if child_column and rowid is not None:
                quoted_table = str(table).replace('"', '""')
                quoted_column = str(child_column).replace('"', '""')
                child = connection.execute(
                    f'SELECT "{quoted_column}" FROM "{quoted_table}" WHERE rowid=?',
                    (rowid,),
                ).fetchone()
                child_value = child[0] if child else None
            details.append({
                "table": table,
                "rowid": rowid,
                "parent": parent,
                "fkid": fkid,
                "child_column": child_column,
                "child_value": child_value,
                "parent_column": parent_column,
                "root_cause": "missing_parent_reference",
            })
    finally:
        connection.close()
    return details
