"""Canonical LUMENIS repository/path registry authority.

This module owns repository-root and standard-directory resolution for the
production product.  Historical root/core registry modules are import surfaces
only and contain no independent resolution logic.

Database-file selection remains owned by lumenis.shared.database.paths so
ZBC_DB_PATH is the single production DB override.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from .paths import main_db_path

_REPOSITORY_REGISTRY_VERSION = "2.0.0"
_REPOSITORY_REGISTRY_ID = "lumenis-production"
_registry: Optional["RepositoryRegistry"] = None


class RepositoryRegistry:
    """Single repository and standard-directory registry."""

    _DIR_SPEC: Dict[str, Dict[str, str]] = {
        "core": {"env": "ZBC_CORE_DIR", "default": "."},
        "data": {"env": "ZBC_DATA_DIR", "default": "data"},
        "runtime": {"env": "ZBC_RUNTIME_DIR", "default": "browser_runtime"},
        "backup": {"env": "ZBC_BACKUP_DIR", "default": "backups"},
        "export": {"env": "ZBC_EXPORT_DIR", "default": "report_export"},
        "temp": {"env": "ZBC_TEMP_DIR", "default": "staging"},
        "ai_runtime": {"env": "ZBC_AI_RUNTIME_DIR", "default": "data/runtime/ai"},
        "collector": {"env": "ZBC_COLLECTOR_DIR", "default": "collector_v2"},
        "log": {"env": "ZBC_LOG_DIR", "default": "logs"},
        "config": {"env": "ZBC_CONFIG_DIR", "default": "config"},
        "static": {"env": "ZBC_STATIC_DIR", "default": "static"},
        "template": {"env": "ZBC_TEMPLATE_DIR", "default": "templates"},
    }

    def __init__(self, repo_root: Optional[str] = None):
        if repo_root is not None:
            root = repo_root
        else:
            root = (
                os.environ.get("ZBC_REPO_ROOT")
                or os.environ.get("ZBC_ROOT")
                or str(Path(__file__).resolve().parents[3])
            )
        self._repo_root = Path(root).resolve()
        self._dirs: Dict[str, Path] = {}
        self._ensured: set[str] = set()

        for key, spec in self._DIR_SPEC.items():
            raw = os.environ.get(spec["env"])
            path = Path(raw) if raw else self._repo_root / spec["default"]
            if not path.is_absolute():
                path = self._repo_root / path
            self._dirs[key] = path.resolve()

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    @property
    def core_dir(self) -> Path:
        return self._dirs["core"]

    @property
    def data_dir(self) -> Path:
        return self._dirs["data"]

    @property
    def runtime_dir(self) -> Path:
        return self._dirs["runtime"]

    @property
    def backup_dir(self) -> Path:
        return self._dirs["backup"]

    @property
    def export_dir(self) -> Path:
        return self._dirs["export"]

    @property
    def temp_dir(self) -> Path:
        return self._dirs["temp"]

    @property
    def staging_dir(self) -> Path:
        return self._dirs["temp"]

    @property
    def ai_runtime_dir(self) -> Path:
        return self._dirs["ai_runtime"]

    @property
    def collector_dir(self) -> Path:
        return self._dirs["collector"]

    @property
    def log_dir(self) -> Path:
        return self._dirs["log"]

    @property
    def config_dir(self) -> Path:
        return self._dirs["config"]

    @property
    def static_dir(self) -> Path:
        return self._dirs["static"]

    @property
    def template_dir(self) -> Path:
        return self._dirs["template"]

    def resolve(self, relative_path: str, ensure_dir: bool = False) -> str:
        path = Path(relative_path)
        if not path.is_absolute():
            path = self._repo_root / path
        path = path.resolve()
        if ensure_dir:
            parent = path.parent
            if str(parent) not in self._ensured:
                parent.mkdir(parents=True, exist_ok=True)
                self._ensured.add(str(parent))
        return str(path)

    def resolve_path(self, relative_path: str, ensure_dir: bool = False) -> Path:
        return Path(self.resolve(relative_path, ensure_dir=ensure_dir))

    def ensure_dir(self, dir_key: str) -> Path:
        if dir_key not in self._dirs:
            raise KeyError(f"unknown directory key: {dir_key}")
        path = self._dirs[dir_key]
        if str(path) not in self._ensured:
            path.mkdir(parents=True, exist_ok=True)
            self._ensured.add(str(path))
        return path

    def all_dirs(self) -> Dict[str, Path]:
        return dict(self._dirs)

    def to_dict(self) -> Dict[str, str]:
        return {
            "repo_root": str(self._repo_root),
            **{key: str(value) for key, value in self._dirs.items()},
        }


def get_registry(force_reload: bool = False) -> RepositoryRegistry:
    global _registry
    if _registry is None or force_reload:
        _registry = RepositoryRegistry()
    return _registry


def resolve_path(relative_path: str, ensure_dir: bool = False) -> str:
    return get_registry().resolve(relative_path, ensure_dir=ensure_dir)


def get_repo_root() -> str:
    return str(get_registry().repo_root)


def get_data_dir() -> str:
    return str(get_registry().data_dir)


def get_log_dir() -> str:
    return str(get_registry().log_dir)


def get_config_dir() -> str:
    return str(get_registry().config_dir)


def get_static_dir() -> str:
    return str(get_registry().static_dir)


def get_template_dir() -> str:
    return str(get_registry().template_dir)


def get_backup_dir() -> str:
    return str(get_registry().backup_dir)


def get_staging_dir() -> str:
    return str(get_registry().staging_dir)


def get_db_path() -> str:
    return main_db_path()


def get_env_path() -> str:
    return resolve_path(".env")


def _optional_external_root(env_name: str) -> Optional[str]:
    """Return an explicitly configured external repository root.

    No sibling-directory probing is performed. Cross-repository runtime
    coupling must use a versioned contract/artifact/API rather than filesystem
    discovery.
    """
    value = os.environ.get(env_name, "").strip().strip('"').strip("'")
    if not value:
        return None
    path = Path(value).expanduser().resolve()
    return str(path) if path.is_dir() else None


def get_osai_root() -> Optional[str]:
    return _optional_external_root("OSAI_ROOT")


def get_ggi_root() -> Optional[str]:
    return _optional_external_root("GGI_ROOT")


def get_python_executable() -> str:
    configured = os.environ.get("ZBC_PYTHON", "").strip().strip('"').strip("'")
    if configured and Path(configured).is_file():
        return str(Path(configured).resolve())
    root = get_registry().repo_root
    candidate = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if candidate.is_file():
        return str(candidate.resolve())
    return sys.executable


def get_git_info() -> dict:
    root = get_repo_root()
    info = {"branch": "unknown", "sha": "unknown", "remote": "unknown", "clean": None}
    try:
        def _git(args):
            result = subprocess.run(
                ["git", *args],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        info["branch"] = _git(["branch", "--show-current"]) or "unknown"
        info["sha"] = _git(["rev-parse", "HEAD"]) or "unknown"
        info["remote"] = _git(["config", "--get", "remote.origin.url"]) or "unknown"
        info["clean"] = _git(["status", "--short"]) == ""
    except Exception:
        pass
    return info


def registry_snapshot() -> dict:
    return {
        "registry_id": _REPOSITORY_REGISTRY_ID,
        "registry_version": _REPOSITORY_REGISTRY_VERSION,
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
            "ZBC_REPO_ROOT": bool(os.environ.get("ZBC_REPO_ROOT")),
            "ZBC_ROOT": bool(os.environ.get("ZBC_ROOT")),
            "ZBC_DATA_DIR": bool(os.environ.get("ZBC_DATA_DIR")),
            "OSAI_ROOT": bool(os.environ.get("OSAI_ROOT")),
            "GGI_ROOT": bool(os.environ.get("GGI_ROOT")),
        },
    }


def ensure_standard_dirs() -> None:
    registry = get_registry()
    for key in ("data", "log", "config", "backup", "temp"):
        try:
            registry.ensure_dir(key)
        except OSError:
            pass


BASE_DIR = str(Path(__file__).resolve().parents[3])

__all__ = [
    "BASE_DIR",
    "RepositoryRegistry",
    "ensure_standard_dirs",
    "get_backup_dir",
    "get_config_dir",
    "get_data_dir",
    "get_db_path",
    "get_env_path",
    "get_ggi_root",
    "get_git_info",
    "get_log_dir",
    "get_osai_root",
    "get_python_executable",
    "get_registry",
    "get_repo_root",
    "get_staging_dir",
    "get_static_dir",
    "get_template_dir",
    "registry_snapshot",
    "resolve_path",
]
