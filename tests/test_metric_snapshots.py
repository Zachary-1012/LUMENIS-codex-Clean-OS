# -*- coding: utf-8 -*-
"""metric_snapshots 指标快照时序测试（UNIFIED-BASELINE §9/§11/§15）。

验证：笔记互动量被覆盖前留痕、仅变化才写、话题指标时序、趋势查询、开关、旁路不阻断采集。
全部使用 tmp_path 临时库，绝不触碰生产 data/monitor.db。
"""
import importlib
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture()
def dbmod(tmp_path, monkeypatch):
    db_path = str(tmp_path / "snapshot_test.db")
    monkeypatch.setenv("ZBC_DB_PATH", db_path)
    monkeypatch.setenv("ZBC_METRIC_SNAPSHOT", "1")
    import database
    importlib.reload(database)  # 让 DB_PATH 重新从环境变量取临时库
    database.DB_PATH = db_path
    database.init_db()
    yield database


def _note(nid, likes=0, comments=0, collects=0, shares=0, **kw):
    d = {"note_id": nid, "title": "t", "content": "c", "likes": likes,
         "comments": comments, "collects": collects, "shares": shares}
    d.update(kw)
    return d


def test_table_created(dbmod):
    with dbmod.get_db() as conn:
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='metric_snapshots'")]
    assert names == ["metric_snapshots"]


def test_new_note_no_snapshot_update_change_writes(dbmod):
    # 首次插入：不产生快照（没有"被覆盖的历史"）
    dbmod.insert_note(_note("n1", likes=1, comments=2))
    assert dbmod.get_metric_trend("note", "n1") == []
    # 第一次更新（指标变化）：写 1 条基线快照
    dbmod.insert_note(_note("n1", likes=5, comments=2))
    t1 = dbmod.get_metric_trend("note", "n1")
    assert len(t1) == 1 and t1[0]["likes"] == 5
    # 指标无变化：不重复刷表
    dbmod.insert_note(_note("n1", likes=5, comments=2))
    assert len(dbmod.get_metric_trend("note", "n1")) == 1
    # 再次变化：新增一条，趋势升序
    dbmod.insert_note(_note("n1", likes=9, comments=8))
    t3 = dbmod.get_metric_trend("note", "n1")
    assert [x["likes"] for x in t3] == [5, 9]
    # notes 单行仍是最新值（零减配：最新值语义不变）
    with dbmod.get_db() as conn:
        row = conn.execute("SELECT likes,comments FROM notes WHERE note_id='n1'").fetchone()
    assert (row["likes"], row["comments"]) == (9, 8)


def test_topic_snapshot_change_only_and_trend(dbmod):
    assert dbmod.record_topic_snapshot("话题A", browse_count=100, discussion_count=3, note_count=2)
    assert not dbmod.record_topic_snapshot("话题A", browse_count=100, discussion_count=3, note_count=2)  # 无变化跳过
    assert dbmod.record_topic_snapshot("话题A", browse_count=160, discussion_count=5, note_count=4)      # 变化写
    trend = dbmod.get_metric_trend("topic", "话题A")
    assert [x["browse_count"] for x in trend] == [100, 160]
    assert [x["discussion_count"] for x in trend] == [3, 5]


def test_switch_off_no_write(dbmod, monkeypatch):
    monkeypatch.setenv("ZBC_METRIC_SNAPSHOT", "0")
    dbmod.insert_note(_note("n2", likes=1))
    dbmod.insert_note(_note("n2", likes=99))
    assert dbmod.get_metric_trend("note", "n2") == []
    assert not dbmod.record_topic_snapshot("t", browse_count=1)


def test_force_write_even_unchanged(dbmod):
    dbmod.insert_note(_note("n3", likes=1))
    dbmod.insert_note(_note("n3", likes=2))   # 首次更新建立基线快照
    assert len(dbmod.get_metric_trend("note", "n3")) == 1
    dbmod.insert_note(_note("n3", likes=2))   # 无变化不写
    assert len(dbmod.get_metric_trend("note", "n3")) == 1
    with dbmod.get_db() as conn:
        assert dbmod.record_note_metric_snapshot(
            conn, "n3", {"likes": 2, "comments": 0, "collects": 0, "shares": 0}, force=True)
    assert len(dbmod.get_metric_trend("note", "n3")) == 2


def test_snapshot_failure_does_not_block_upsert(dbmod, monkeypatch):
    # 模拟快照函数抛错，insert_note 仍应正常完成更新（旁路不阻断）
    def boom(*a, **k):
        raise RuntimeError("snapshot broken")
    monkeypatch.setattr(dbmod, "record_note_metric_snapshot", boom)
    dbmod.insert_note(_note("n4", likes=1))
    dbmod.insert_note(_note("n4", likes=42))  # 内部快照抛错被吞，更新照常
    with dbmod.get_db() as conn:
        row = conn.execute("SELECT likes FROM notes WHERE note_id='n4'").fetchone()
    assert row["likes"] == 42
