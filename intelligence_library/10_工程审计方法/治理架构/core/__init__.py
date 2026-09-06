# -*- coding: utf-8 -*-
"""ZBC Production Core — core package.

Canonical infrastructure modules for Z-Brand-Core / 序境 Production Core.
All production code should import from here rather than hardcoding paths
or duplicating infrastructure logic.
"""
from .repository_registry import (
    get_repo_root,
    get_data_dir,
    get_log_dir,
    get_config_dir,
    get_static_dir,
    get_template_dir,
    get_backup_dir,
    get_staging_dir,
    get_db_path,
    get_env_path,
    get_osai_root,
    get_ggi_root,
    get_python_executable,
    get_git_info,
    registry_snapshot,
    ensure_standard_dirs,
)

__all__ = [
    "get_repo_root",
    "get_data_dir",
    "get_log_dir",
    "get_config_dir",
    "get_static_dir",
    "get_template_dir",
    "get_backup_dir",
    "get_staging_dir",
    "get_db_path",
    "get_env_path",
    "get_osai_root",
    "get_ggi_root",
    "get_python_executable",
    "get_git_info",
    "registry_snapshot",
    "ensure_standard_dirs",
]
