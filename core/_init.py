"""Compatibility surface for historical core path helpers.

Canonical repository/path authority lives in lumenis.shared.database.repository.
"""
from lumenis.shared.database.registry import (
    ensure_standard_dirs,
    get_backup_dir,
    get_config_dir,
    get_data_dir,
    get_db_path,
    get_env_path,
    get_ggi_root,
    get_git_info,
    get_log_dir,
    get_osai_root,
    get_python_executable,
    get_repo_root,
    get_staging_dir,
    get_static_dir,
    get_template_dir,
    registry_snapshot,
)

__all__ = [
    "get_repo_root", "get_data_dir", "get_log_dir", "get_config_dir",
    "get_static_dir", "get_template_dir", "get_backup_dir", "get_staging_dir",
    "get_db_path", "get_env_path", "get_osai_root", "get_ggi_root",
    "get_python_executable", "get_git_info", "registry_snapshot",
    "ensure_standard_dirs",
]
