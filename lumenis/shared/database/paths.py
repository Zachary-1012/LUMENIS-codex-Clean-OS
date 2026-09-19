"""Canonical LUMENIS production database path authority.

Production has one SQLite business-truth database. ZBC_DB_PATH is the single
supported runtime override for that truth store in tests, staging and deployment.
An explicitly architecture-registered SYSTEM operational store (such as durable
task-queue state) may use its own owner-declared path, but cannot store Canonical
Data, Evidence or business outcomes and must use the shared connection owner.
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
