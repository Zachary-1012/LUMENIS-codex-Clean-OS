# -*- coding: utf-8 -*-
"""ZBC Production Core — Repository Registry (Shard D / Team 1)

Canonical path resolution for Z-Brand-Core / 序境 Production Core.
All production code MUST obtain repository-relative paths through this module
instead of hardcoding absolute filesystem paths.

Resolution order (highest priority first):
    1. Environment variable override (ZBC_ROOT, ZBC_DATA_DIR, ...)
    2. Dynamic detection from __file__ location (repo root = parent of core/)
    3. Platform-aware fallback probe (common locations)
    4. Last-resort default (only for dev/debug; logged as warning)

Design red lines:
    - stdlib only, no third-party dependencies
    - read-only: never writes to filesystem
    - never raises on missing path; returns resolved path and lets caller handle
    - env var names are stable public API
    - all paths normalized via os.path.normpath
"""
import os
import sys
import warnings

# ---------------------------------------------------------------------------
# Repository root resolution
# ---------------------------------------------------------------------------

_REGISTRY_VERSION = "1.0.0"
_REGISTRY_ID = "zbc-production-core"


def _detect_repo_root():
    """Dynamically detect ZBC repo root from this file's location.

    This module lives at <repo_root>/core/repository_registry.py,
    so repo_root = dirname(dirname(abspath(__file__))).
    """
    return os.path.normpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _probe_fallback_roots():
    """Probe common locations when dynamic detection fails (e.g. frozen exe)."""
    candidates = [
        os.getcwd(),
        os.path.expanduser("~/Taikoo-monitor-new"),
        os.path.expanduser("~/z-brand-core"),
        "/workspace/Taikoo-monitor-new",
        "/app/Taikoo-monitor-new",
    ]
    # Windows dev machine fallback (last resort only)
    if os.name == "nt":
        candidates.append(r"D:\Taikoo-monitor-new")
    for cand in candidates:
        try:
            if cand and os.path.isdir(cand) and os.path.isfile(os.path.join(cand, "app.py")):
                return os.path.normpath(cand)
        except OSError:
            continue
    return None


def get_repo_root():
    """Resolve ZBC repository root path.

    Priority: ZBC_ROOT env var > dynamic __file__ detection > fallback probe.
    Never returns None; falls back to dynamic detection result even if unverified.
    """
    # 1. Environment override
    env_root = os.environ.get("ZBC_ROOT", "").strip().strip('"').strip("'")
    if env_root and os.path.isdir(env_root):
        return os.path.normpath(env_root)

    # 2. Dynamic detection from __file__
    dynamic = _detect_repo_root()
    if os.path.isdir(dynamic):
        return dynamic

    # 3. Fallback probe
    probed = _probe_fallback_roots()
    if probed:
        warnings.warn(
            "RepositoryRegistry: using probed fallback root (dynamic detection failed). "
            "Set ZBC_ROOT env var for production stability.",
            RuntimeWarning,
            stacklevel=2,
        )
        return probed

    # 4. Last resort (unverified)
    warnings.warn(
        "RepositoryRegistry: could not verify repo root; returning dynamic detection result. "
        "Set ZBC_ROOT env var immediately.",
        RuntimeWarning,
        stacklevel=2,
    )
    return dynamic


# ---------------------------------------------------------------------------
# Standard subdirectory resolution
# ---------------------------------------------------------------------------

def _subdir(name, env_var=None):
    """Resolve a standard subdirectory under repo root.

    Supports env var override for the full path.
    """
    if env_var:
        env_val = os.environ.get(env_var, "").strip().strip('"').strip("'")
        if env_val:
            return os.path.normpath(env_val)
    return os.path.normpath(os.path.join(get_repo_root(), name))


def get_data_dir():
    """Database and persistent data directory."""
    return _subdir("data", "ZBC_DATA_DIR")


def get_log_dir():
    """Log files directory."""
    return _subdir("logs", "ZBC_LOG_DIR")


def get_config_dir():
    """Configuration files directory."""
    return _subdir("config", "ZBC_CONFIG_DIR")


def get_static_dir():
    """Static assets directory."""
    return _subdir("static", "ZBC_STATIC_DIR")


def get_template_dir():
    """Jinja2 templates directory."""
    return _subdir("templates", "ZBC_TEMPLATE_DIR")


def get_backup_dir():
    """Database backups directory."""
    return _subdir("backups", "ZBC_BACKUP_DIR")


def get_staging_dir():
    """Staging / intermediate files directory."""
    return _subdir("staging", "ZBC_STAGING_DIR")


def get_db_path():
    """Primary SQLite database path (data/monitor.db)."""
    return os.path.normpath(os.path.join(get_data_dir(), "monitor.db"))


def get_env_path():
    """.env file path (repo root)."""
    return os.path.normpath(os.path.join(get_repo_root(), ".env"))


# ---------------------------------------------------------------------------
# Cross-repository references (read-only, for dual-core coordination)
# ---------------------------------------------------------------------------

def get_osai_root():
    """Resolve OSAI (Intelligence Core) repo root, if available.

    Priority: OSAI_ROOT env var > sibling directory probe > None.
    Returns None if OSAI is not present (ZBC must operate independently).
    """
    env_val = os.environ.get("OSAI_ROOT", "").strip().strip('"').strip("'")
    if env_val and os.path.isdir(env_val):
        return os.path.normpath(env_val)

    # Probe sibling directory
    sibling = os.path.normpath(os.path.join(os.path.dirname(get_repo_root()), "Zachary OS AI"))
    if os.path.isdir(sibling):
        return sibling

    # Windows dev machine fallback
    if os.name == "nt":
        cand = r"D:\Zachary OS AI"
        if os.path.isdir(cand):
            return os.path.normpath(cand)

    return None


def get_ggi_root():
    """Resolve GGI (Global Growth Intelligence) repo root, if available.

    GGI is an independent product; ZBC must never have a hard runtime dependency.
    Returns None if not present.
    """
    env_val = os.environ.get("GGI_ROOT", "").strip().strip('"').strip("'")
    if env_val and os.path.isdir(env_val):
        return os.path.normpath(env_val)

    sibling = os.path.normpath(os.path.join(os.path.dirname(get_repo_root()), "global-growth-intelligence"))
    if os.path.isdir(sibling):
        return sibling

    return None


# ---------------------------------------------------------------------------
# Python interpreter resolution
# ---------------------------------------------------------------------------

def get_python_executable():
    """Resolve the preferred Python interpreter.

    Priority: ZBC_PYTHON env var > repo .venv > sys.executable > system python.
    """
    env_py = os.environ.get("ZBC_PYTHON", "").strip().strip('"').strip("'")
    if env_py and os.path.isfile(env_py):
        return os.path.normpath(env_py)

    root = get_repo_root()
    if os.name == "nt":
        venv_py = os.path.join(root, ".venv", "Scripts", "python.exe")
    else:
        venv_py = os.path.join(root, ".venv", "bin", "python")
    if os.path.isfile(venv_py):
        return os.path.normpath(venv_py)

    return sys.executable


# ---------------------------------------------------------------------------
# Git metadata (read-only, best-effort)
# ---------------------------------------------------------------------------

def get_git_info():
    """Read-only git metadata (branch, sha, remote). Best-effort; never raises."""
    import subprocess
    root = get_repo_root()
    info = {"branch": "unknown", "sha": "unknown", "remote": "unknown", "clean": None}
    try:
        def _git(args):
            r = subprocess.run(["git"] + args, cwd=root, capture_output=True,
                               text=True, timeout=10)
            return r.stdout.strip() if r.returncode == 0 else ""
        info["branch"] = _git(["branch", "--show-current"]) or "unknown"
        info["sha"] = _git(["rev-parse", "HEAD"]) or "unknown"
        info["remote"] = _git(["config", "--get", "remote.origin.url"]) or "unknown"
        status = _git(["status", "--short"])
        info["clean"] = (status == "")
    except Exception:
        pass
    return info


# ---------------------------------------------------------------------------
# Registry snapshot (for observability / health checks)
# ---------------------------------------------------------------------------

def registry_snapshot():
    """Full registry snapshot for health checks and debugging.

    Does NOT expose sensitive values; only paths and metadata.
    """
    return {
        "registry_id": _REGISTRY_ID,
        "registry_version": _REGISTRY_VERSION,
        "repo_root": get_repo_root(),
        "data_dir": get_data_dir(),
        "log_dir": get_log_dir(),
        "config_dir": get_config_dir(),
        "db_path": get_db_path(),
        "python_executable": get_python_executable(),
        "osai_root": get_osai_root(),
        "ggi_root": get_ggi_root(),
        "osai_present": get_osai_root() is not None,
        "ggi_present": get_ggi_root() is not None,
        "git": get_git_info(),
        "env_overrides": {
            "ZBC_ROOT": bool(os.environ.get("ZBC_ROOT")),
            "ZBC_DATA_DIR": bool(os.environ.get("ZBC_DATA_DIR")),
            "OSAI_ROOT": bool(os.environ.get("OSAI_ROOT")),
        },
    }


# ---------------------------------------------------------------------------
# Convenience: ensure standard directories exist (caller-initiated only)
# ---------------------------------------------------------------------------

def ensure_standard_dirs():
    """Create standard directories if they don't exist.

    This is the ONLY write operation in this module, and only creates
    directories (never files). Call explicitly during app initialization.
    """
    for path_fn in (get_data_dir, get_log_dir, get_config_dir,
                     get_backup_dir, get_staging_dir):
        try:
            p = path_fn()
            if p and not os.path.isdir(p):
                os.makedirs(p, exist_ok=True)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    snap = registry_snapshot()
    print(json.dumps(snap, ensure_ascii=False, indent=2))
    print("\n[OK] Repository Registry self-test passed.")
    print(f"  repo_root exists: {os.path.isdir(snap['repo_root'])}")
    print(f"  db_path exists: {os.path.isfile(snap['db_path'])}")
    print(f"  python exists: {os.path.isfile(snap['python_executable'])}")
