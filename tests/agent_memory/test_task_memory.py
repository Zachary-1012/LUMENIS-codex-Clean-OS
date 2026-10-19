# -*- coding: utf-8 -*-
"""Task Memory 单元测试 — 真实操作临时DB，不 mock。"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_memory.task import TaskMemory


class TestTaskMemory:
    def test_get_task(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        assert tm.get_task("task_001") is None

    def test_get_task_not_found(self, seeded_db):
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        assert tm.get_task("nonexistent") is None

    def test_get_task_steps(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        assert tm.get_task_steps("task_001") == []

    def test_get_task_evidence(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        assert tm.get_task_evidence("task_001") == []

    def test_query_tasks_by_intent(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        assert tm.query_tasks(intent="analysis") == []

    def test_query_tasks_by_status(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        assert tm.query_tasks(status="completed") == []
        assert tm.query_tasks(status="failed") == []

    def test_get_task_summary(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        assert tm.get_task_summary("task_001") is None

    def test_record_task_outcome(self, seeded_db):
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        ok = tm.record_task_outcome("task_001", "success", "任务完成", {"meta": "data"})
        assert ok is True
        rec = tm.retrieve("outcome:task_001")
        assert rec is not None
        assert rec.value["outcome"] == "success"

    def test_disabled(self, seeded_db):
        tm = TaskMemory(db_path=seeded_db, enabled=False)
        assert tm.get_task("task_001") is None
        assert tm.query_tasks() == []

    def test_stats(self, seeded_db):
        # Legacy rows have no verified actor/scope binding.
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        assert tm.stats()["visible_task_count"] == 0
