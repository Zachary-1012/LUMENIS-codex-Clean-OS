# -*- coding: utf-8 -*-
"""LUMENIS canonical runtime identity snapshot.

The snapshot is generated once per process and reused by health/attestation
consumers.  It performs read-only Git and SQLite schema inspection, never
returns an absolute database path, and never hashes live database contents on
request paths.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


ROOT_DIR = Path(__file__).resolve().parent
IDENTITY_SCHEMA = "lumenis.runtime-identity.v1"
SERVICE_NAMESPACE = "lumenis"
SERVICE_NAME = "production-core"
_CACHE: Dict[str, Any] | None = None
_CACHE_LOCK = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT_DIR), *args],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _service_version() -> str:
    try:
        return (ROOT_DIR / "VERSION").read_text(encoding="utf-8-sig").strip() or "unknown"
    except OSError:
        return "unknown"


def _database_identity(db_path: str) -> Dict[str, Any]:
    """Return non-secret DB identity and schema fingerprints without writes."""
    resolved = Path(db_path).resolve()
    normalized = os.path.normcase(str(resolved))
    result: Dict[str, Any] = {
        "identity_digest": _sha256_text(normalized),
        "exists": resolved.is_file(),
        "schema_digest": None,
        "schema_version": None,
        "user_version": None,
    }
    if not result["exists"]:
        return result

    try:
        uri = resolved.as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=3) as conn:
            schema_version = int(conn.execute("PRAGMA schema_version").fetchone()[0])
            user_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
            rows = conn.execute(
                "SELECT type, name, tbl_name, COALESCE(sql, '') "
                "FROM sqlite_master ORDER BY type, name, tbl_name"
            ).fetchall()
        schema_payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
        result.update(
            {
                "schema_digest": _sha256_text(schema_payload),
                "schema_version": schema_version,
                "user_version": user_version,
            }
        )
    except (OSError, sqlite3.Error) as exc:
        result["schema_error"] = type(exc).__name__
    return result


def _load_release_manifest() -> Dict[str, Any]:
    declared_path = os.getenv("LUMENIS_RELEASE_MANIFEST", "").strip()
    manifest_path = Path(declared_path) if declared_path else ROOT_DIR / "config" / "release_manifest.json"
    if not manifest_path.is_file():
        return {"present": False, "verified": False, "reason": "manifest_missing"}
    try:
        raw = manifest_path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("manifest root must be an object")
        required = {
            "schema_version",
            "release_id",
            "core_commit",
            "source_tree_digest",
            "product_mode",
        }
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError("manifest required fields missing")
        return {
            "present": True,
            "verified": False,
            "digest": hashlib.sha256(raw).hexdigest(),
            "payload": payload,
        }
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "present": True,
            "verified": False,
            "reason": f"manifest_invalid:{type(exc).__name__}",
        }


def _configured_workers() -> list[str]:
    workers = ["web"]
    if "--no-scheduler" not in sys.argv:
        workers.append("scheduler-requested")
    declared = os.getenv("LUMENIS_WORKER_SET", "")
    for item in declared.split(","):
        item = item.strip().lower()
        if item and item not in workers:
            workers.append(item)
    return workers


def build_runtime_identity(*, db_path: str | None = None) -> Dict[str, Any]:
    core_commit = _git("rev-parse", "HEAD")
    tree_digest = _git("rev-parse", "HEAD^{tree}")
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    source_dirty = bool(_git("status", "--porcelain", "--untracked-files=no"))
    version = _service_version()

    manifest = _load_release_manifest()
    manifest_payload = manifest.pop("payload", {})
    manifest_matches = bool(
        manifest.get("present")
        and manifest_payload.get("schema_version") == "lumenis.release-manifest.v1"
        and manifest_payload.get("core_commit") == core_commit
        and manifest_payload.get("source_tree_digest") == tree_digest
    )
    manifest["verified"] = manifest_matches
    if manifest.get("present") and not manifest_matches and "reason" not in manifest:
        manifest["reason"] = "source_mismatch"

    declared_release = (
        manifest_payload.get("release_id")
        or os.getenv("LUMENIS_RELEASE_ID")
        or os.getenv("ZBC_RELEASE_ID")
    )
    if manifest_matches:
        release_state = "MANIFEST_VERIFIED"
    elif declared_release:
        release_state = "DECLARED_UNVERIFIED"
    else:
        release_state = "UNRELEASED"
    release_id = str(declared_release or f"unreleased-{(core_commit or 'unknown')[:12]}")

    product_mode = (
        manifest_payload.get("product_mode")
        or os.getenv("LUMENIS_PRODUCT_MODE")
        or os.getenv("ZBC_PRODUCT_ID")
        or "UNSPECIFIED"
    )
    profile_id = (
        manifest_payload.get("profile_id")
        or os.getenv("LUMENIS_PROFILE_ID")
        or os.getenv("ZBC_ACTIVE_BRAND")
        or ""
    )
    if db_path is None:
        try:
            from database import DB_PATH

            db_path = DB_PATH
        except Exception:
            db_path = os.getenv("ZBC_DB_PATH") or str(ROOT_DIR / "data" / "monitor.db")

    started_at = _utc_now()
    instance_seed = f"{socket.gethostname()}|{os.getpid()}|{started_at}"
    return {
        "identity_schema": IDENTITY_SCHEMA,
        "service_namespace": SERVICE_NAMESPACE,
        "service_name": SERVICE_NAME,
        "service_version": version,
        "instance_id": _sha256_text(instance_seed)[:20],
        "started_at": started_at,
        "runtime_state": "STARTED",
        "release_id": release_id,
        "release_state": release_state,
        "core_commit": core_commit or None,
        "source_tree_digest": tree_digest or None,
        "source_branch": branch or None,
        "source_dirty": source_dirty,
        "product_mode": str(product_mode),
        "profile_digest": _sha256_text(str(profile_id)) if profile_id else None,
        "database": _database_identity(str(db_path)),
        "configured_workers": _configured_workers(),
        "release_manifest": manifest,
    }


def get_runtime_identity(*, public: bool = False, force: bool = False) -> Dict[str, Any]:
    global _CACHE
    with _CACHE_LOCK:
        if _CACHE is None or force:
            _CACHE = build_runtime_identity()
        identity = dict(_CACHE)
        identity["database"] = dict(_CACHE["database"])
        identity["release_manifest"] = dict(_CACHE["release_manifest"])
        identity["configured_workers"] = list(_CACHE["configured_workers"])

    if not public:
        return identity
    return {
        "identity_schema": identity["identity_schema"],
        "service_name": identity["service_name"],
        "service_version": identity["service_version"],
        "instance_id": identity["instance_id"],
        "started_at": identity["started_at"],
        "runtime_state": identity["runtime_state"],
        "release_id": identity["release_id"],
        "release_state": identity["release_state"],
        "core_commit": (identity["core_commit"] or "")[:12] or None,
        "source_tree_digest": (identity["source_tree_digest"] or "")[:12] or None,
        "product_mode": identity["product_mode"],
    }


def reset_runtime_identity_cache() -> None:
    """Test/process-reload helper; production requests must not call this."""
    global _CACHE
    with _CACHE_LOCK:
        _CACHE = None
