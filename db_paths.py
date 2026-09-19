"""Transitional import surface for the retired root DB-path owner.

Canonical owner: lumenis.shared.database.paths.
This file contains no path-selection logic and will be deleted after remaining
callers are migrated.
"""
from lumenis.shared.database.paths import DEFAULT_DB_PATH, main_db_path

def evidence_db_path() -> str:
    return main_db_path()

def guardian_db_path() -> str:
    return main_db_path()

def token_db_path() -> str:
    return main_db_path()

__all__ = ["DEFAULT_DB_PATH", "main_db_path", "evidence_db_path", "guardian_db_path", "token_db_path"]
