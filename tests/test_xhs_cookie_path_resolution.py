"""Regression tests for the production-local credential/data path contract."""

from pathlib import Path

import xhs_cookie_bridge as bridge
import system_health_api as health


def test_explicit_data_dir_has_priority(tmp_path):
    data_dir = tmp_path / "protected-data"
    db_path = tmp_path / "other" / "monitor.db"

    resolved = bridge._resolve_runtime_data_dir(
        root=str(tmp_path / "repo"),
        environ={"ZBC_DATA_DIR": str(data_dir), "ZBC_DB_PATH": str(db_path)},
    )

    assert Path(resolved) == data_dir.resolve()


def test_db_parent_is_reused_when_data_dir_is_not_set(tmp_path):
    data_dir = tmp_path / "protected-data"
    db_path = data_dir / "monitor.db"

    resolved = bridge._resolve_runtime_data_dir(
        root=str(tmp_path / "repo"),
        environ={"ZBC_DB_PATH": str(db_path)},
    )

    assert Path(resolved) == data_dir.resolve()


def test_sqlite_url_uses_its_filesystem_parent(tmp_path):
    data_dir = tmp_path / "protected-data"
    db_path = data_dir / "monitor.db"

    resolved = bridge._resolve_runtime_data_dir(
        root=str(tmp_path / "repo"),
        environ={"ZBC_DB_PATH": f"sqlite:///{db_path.as_posix()}"},
    )

    assert Path(resolved) == data_dir.resolve()


def test_repo_data_is_only_the_fallback(tmp_path):
    repo = tmp_path / "repo"

    resolved = bridge._resolve_runtime_data_dir(root=str(repo), environ={})

    assert Path(resolved) == (repo / "data").resolve()


def test_health_summary_reuses_database_parent_for_runtime_data(tmp_path, monkeypatch):
    data_dir = tmp_path / "protected-data"
    db_path = data_dir / "monitor.db"
    monkeypatch.delenv("ZBC_DATA_DIR", raising=False)
    monkeypatch.setattr(health, "get_db_path", lambda: str(db_path))

    assert Path(health.get_data_dir()) == data_dir.resolve()
