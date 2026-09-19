"""Canonical LUMENIS production database path authority.

Production has one SQLite truth. ZBC_DB_PATH is the single supported runtime
override for tests, staging and deployment. Shared capabilities and SYSTEM
services must not select parallel production database files.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = str((REPO_ROOT / "data" / "monitor.db").resolve())


def main_db_path() -> str:
    """Return the one canonical production database path at call time."""
    value = os.environ.get("ZBC_DB_PATH")
    if value is not None and str(value).strip():
        return os.path.abspath(str(value).strip())
    return DEFAULT_DB_PATH


def production_db_path() -> str:
    """Semantic alias for the Production Truth database."""
    return main_db_path()
