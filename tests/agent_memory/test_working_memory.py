# -*- coding: utf-8 -*-
"""Working Memory 单元测试 — 真实操作临时DB，不 mock。"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_memory.working import WorkingMemory


class TestWorkingMemory:
    def test_store_and_retrieve(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        rec = wm.store("key1", {"data": "value1"}, metadata={"type": "test"})
        assert rec is not None
        assert rec.key == "key1"
        assert rec.value["data"] == "value1"

        retrieved = wm.retrieve("key1")
        assert retrieved is not None
        assert retrieved.value["data"] == "value1"

    def test_disabled_by_default(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=False)
        rec = wm.store("key1", {"data": "value1"})
        assert rec is None
        assert wm.retrieve("key1") is None

    def test_begin_and_end_task(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task_test", "测试目标", {"extra": "context"})
        assert wm._current_task_id == "task_test"
        ctx = wm.get_context()
        assert ctx["goal"] == "测试目标"
        assert ctx["extra"] == "context"

        summary = wm.end_task(result={"ok": True})
        assert summary["task_id"] == "task_test"
        assert summary["result"]["ok"] is True
        assert wm._current_task_id is None

    def test_add_step(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task_steps", "步骤测试")
        step1 = wm.add_step("parse", input_data={"q": "test"}, output_data={"ok": True})
        step2 = wm.add_step("execute", input_data={"action": "run"}, status="completed")
        assert step1["seq"] == 1
        assert step2["seq"] == 2
        assert len(wm.get_recent_steps()) == 2
        assert wm.get_context()["step_count"] == 2

    def test_add_step_persists_to_db(self, temp_db):
        import sqlite3
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task_persist", "持久化测试")
        wm.add_step("test_action", persist=True)
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM ai_task_step WHERE task_id=?", ("task_persist",)
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["phase"] == "test_action"

    def test_recent_steps_limit(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=True, max_steps=5)
        wm.begin_task("task_limit", "限制测试")
        for i in range(10):
            wm.add_step(f"step_{i}", persist=False)
        assert len(wm.get_recent_steps()) == 5
        assert wm.get_recent_steps()[0]["action"] == "step_5"

    def test_ttl_expiry(self, temp_db):
        import time
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.store("ttl_key", {"data": "temp"}, ttl_seconds=0.01)
        time.sleep(0.02)
        assert wm.retrieve("ttl_key") is None

    def test_query_by_keyword(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.store("k1", {"topic": "舆情分析", "detail": "测试数据"})
        wm.store("k2", {"topic": "品牌营销", "detail": "其他数据"})
        results = wm.query({"keyword": "舆情"}, limit=10)
        assert len(results) == 1
        assert results[0].key == "k1"

    def test_forget(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.store("forget_me", {"data": "x"})
        assert wm.retrieve("forget_me") is not None
        assert wm.forget("forget_me") is True
        assert wm.retrieve("forget_me") is None

    def test_archive_to_episodic(self, temp_db):
        from agent_memory.episodic import EpisodicMemory
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        em = EpisodicMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task_archive", "归档测试")
        wm.add_step("step1", persist=False)
        archive_id = wm.archive_to_episodic(em)
        assert archive_id is not None
        retrieved = em.retrieve(f"case:task_archive")
        assert retrieved is not None
        assert retrieved.value["task_id"] == "task_archive"
        assert retrieved.value["step_count"] == 1

    def test_stats(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task_stats", "统计测试")
        s = wm.stats()
        assert s["layer"] == "working"
        assert s["enabled"] is True
        assert s["current_task_id"] == "task_stats"
