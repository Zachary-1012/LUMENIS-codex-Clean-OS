"""Canonical LUMENIS database repository layer.

All ordinary production SQLite access should flow through this layer.  Domain
modules keep their business SQL, but connection selection, transactions and
commit/rollback semantics are centralized here.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence

from .connection import connect_sqlite


class DatabaseRepository:
    """Repository over the canonical business database or a registered system store.

    The default path is the only Production Truth database. An explicit path is
    reserved for isolated tests, controlled migrations, and architecture-registered
    SYSTEM operational stores; it must never create a second business-truth owner.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def connect(self, **kwargs):
        return connect_sqlite(self.db_path, **kwargs)

    @contextmanager
    def transaction(self, **kwargs) -> Iterator[Any]:
        conn = self.connect(**kwargs)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def connection(self, **kwargs) -> Iterator[Any]:
        conn = self.connect(**kwargs)
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        with self.transaction() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount

    def executemany(self, sql: str, params: Iterable[Sequence[Any]]) -> int:
        with self.transaction() as conn:
            cursor = conn.executemany(sql, params)
            return cursor.rowcount

    def executescript(self, sql: str) -> None:
        with self.transaction() as conn:
            conn.executescript(sql)

    def query_one(self, sql: str, params: Sequence[Any] = ()):
        with self.connection() as conn:
            return conn.execute(sql, params).fetchone()

    def query_all(self, sql: str, params: Sequence[Any] = ()):
        with self.connection() as conn:
            return conn.execute(sql, params).fetchall()

    def table_exists(self, table_name: str) -> bool:
        row = self.query_one(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return row is not None


_default_repository: Optional[DatabaseRepository] = None


def get_repository(force_reload: bool = False) -> DatabaseRepository:
    global _default_repository
    if _default_repository is None or force_reload:
        _default_repository = DatabaseRepository()
    return _default_repository


__all__ = ["DatabaseRepository", "get_repository"]
