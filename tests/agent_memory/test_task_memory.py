# -*- coding: utf-8 -*-
"""Task Memory 单元测试 — 真实操作临时DB，不 mock。"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_memory.task import TaskMemory


class TestTaskMemory:
    def test_get_task(self, seeded_db):
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        task = tm.get_task("task_001")
        assert task is not None
        assert task["task_id"] == "task_001"
        assert task["intent"] == "analysis"
        assert task["status"] == "completed"

    def test_get_task_not_found(self, seeded_db):
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        assert tm.get_task("nonexistent") is None

    def test_get_task_steps(self, seeded_db):
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        steps = tm.get_task_steps("task_001")
        assert len(steps) >= 1
        assert steps[0]["step_id"] == "step_001"

    def test_get_task_evidence(self, seeded_db):
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        evidence = tm.get_task_evidence("task_001")
        assert len(evidence) >= 1
        assert evidence[0]["evidence_id"] == "ev_001"
        assert evidence[0]["authenticity_score"] == 0.9

    def test_query_tasks_by_intent(self, seeded_db):
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        tasks = tm.query_tasks(intent="analysis")
        assert len(tasks) >= 1
        assert all("analysis" in t["intent"] for t in tasks)

    def test_query_tasks_by_status(self, seeded_db):
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        completed = tm.query_tasks(status="completed")
        assert len(completed) >= 1
        assert all(t["status"] == "completed" for t in completed)
        failed = tm.query_tasks(status="failed")
        assert len(failed) >= 1

    def test_get_task_summary(self, seeded_db):
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        summary = tm.get_task_summary("task_001")
        assert summary is not None
        assert "task" in summary
        assert "steps" in summary
        assert "evidence" in summary
        assert summary["task"]["task_id"] == "task_001"

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
        tm = TaskMemory(db_path=seeded_db, enabled=True)
        s = tm.stats()
        assert s["layer"] == "task"
        assert s["ai_task_total"] >= 2
