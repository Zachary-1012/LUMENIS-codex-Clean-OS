from __future__ import annotations

import importlib
import os
from pathlib import Path


def test_auth_recovery_respects_zbc_db_path(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "isolated.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(target))
    import auth_recovery_center
    auth_recovery_center.AuthRecoveryCenter._instance = None
    module = importlib.reload(auth_recovery_center)
    assert Path(module.AuthRecoveryCenter.DB_PATH) == target.resolve()


def test_schedule_planner_respects_zbc_db_path(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "isolated.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(target))
    import platform_adapters.scheduling as scheduling
    scheduling._PLANNER = None
    planner = scheduling.get_planner()
    assert Path(planner.store.db_path) == target.resolve()
    assert Path(planner.state_file).parent == target.parent.resolve()
