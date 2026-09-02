# -*- coding: utf-8 -*-
"""P0-A 生产安全基线脚本自检测试：验证安全门各段可运行、备份可恢复、收集解析正确。"""
import importlib.util
import os
import sqlite3

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "production_baseline_check.py")


@pytest.fixture(scope="module")
def baseline():
    spec = importlib.util.spec_from_file_location("production_baseline_check", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_git_segment_pass(baseline):
    report = {}
    ok = baseline.check_git(report)
    assert ok is True
    assert report["git"]["checks"]["head"]["ok"]
    assert report["git"]["rollback_candidate"]  # 存在可回退点


def test_runtime_segment_pass(baseline):
    report = {}
    ok = baseline.check_runtime(report)
    assert ok is True
    assert report["runtime"]["checks"]["core_blueprints"]["ok"]
    assert report["runtime"]["checks"]["route_count"]["value"] > 300


def _make_minimal_db(path):
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")  # 对齐生产库 WAL 安全门
    for t in ("notes", "events", "daily_reports", "web_mentions", "metric_snapshots"):
        con.execute(f"CREATE TABLE {t} (id INTEGER PRIMARY KEY)")
    con.commit()
    con.close()


def test_data_segment_with_temp_db(baseline, tmp_path, monkeypatch):
    """最小库隔离验证：integrity/核心表/一致性备份可恢复，绝不触碰生产库。"""
    tmp_db = str(tmp_path / "t.db")
    _make_minimal_db(tmp_db)
    import database
    monkeypatch.setattr(database, "DB_PATH", tmp_db)
    monkeypatch.setattr(baseline, "BACKUP_DIR", str(tmp_path / "bk"))
    report = {}
    ok = baseline.check_data(report, do_backup=True)
    assert ok is True
    assert report["data"]["checks"]["integrity"]["value"] == "ok"
    assert os.path.exists(report["data"]["backup_path"])
    assert os.path.getsize(report["data"]["backup_path"]) > 0
    # 备份可恢复：从备份读回核心表
    bc = sqlite3.connect(report["data"]["backup_path"])
    try:
        assert bc.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0
    finally:
        bc.close()


def test_collect_count_regex():
    import re
    sample = ["tests/test_a.py: 16", "tests/test_b.py: 8", "some noise line"]
    n = 0
    for ln in sample:
        m = re.search(r":\s*(\d+)\s*$", ln.strip())
        if m:
            n += int(m.group(1))
    assert n == 24
