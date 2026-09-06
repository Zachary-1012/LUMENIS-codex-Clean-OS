# -*- coding: utf-8 -*-
"""P1-B TopicSnapshotManager 测试：五时间口径写入 + 变化才写（隔离临时库）。"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import database as db
from topic_snapshot import TIME_MODEL, TopicSnapshotManager  # noqa: E402


@pytest.fixture
def iso_db(tmp_path, monkeypatch):
    p = tmp_path / "iso.db"
    monkeypatch.setattr(db, "DB_PATH", str(p))
    # 建最小表结构
    con = sqlite3.connect(str(p))
    con.execute("CREATE TABLE metric_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "entity_type TEXT, entity_key TEXT, likes INT, comments INT, collects INT, shares INT,"
                "browse_count INT, discussion_count INT, note_count INT, raw_json TEXT,"
                "source TEXT, collector_version TEXT, snapshot_at TEXT)")
    con.commit()
    con.close()
    return p


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(db, "_metric_snapshot_enabled", lambda: True)


def _rows(p):
    con = sqlite3.connect(str(p))
    try:
        return con.execute("SELECT entity_key,browse_count,discussion_count,note_count,raw_json "
                           "FROM metric_snapshots WHERE entity_type='topic'").fetchall()
    finally:
        con.close()


def test_record_writes_with_time_model(iso_db, enabled):
    mgr = TopicSnapshotManager()
    ok = mgr.record("t-topic", browse=1000, discussion=50, notes=8,
                    event_date="2026-08-01", note_publish_date="2026-08-02")
    assert ok is True
    rows = _rows(iso_db)
    assert len(rows) == 1
    raw = rows[0][4]
    for k in TIME_MODEL:
        assert k in raw  # 五时间口径全部附带


def test_change_only_no_duplicate(iso_db, enabled):
    mgr = TopicSnapshotManager()
    assert mgr.record("t2", browse=1, discussion=1, notes=1) is True
    assert mgr.record("t2", browse=1, discussion=1, notes=1) is False  # 无变化不写
    assert len(_rows(iso_db)) == 1
    assert mgr.record("t2", browse=2, discussion=1, notes=1) is True  # 有变化写
    assert len(_rows(iso_db)) == 2


def test_time_model_description(iso_db):
    mgr = TopicSnapshotManager()
    d = mgr.describe_time_model()
    assert d["model"] == TIME_MODEL
    assert "发布日期 ≠ 采集日期" in d["principle"]
