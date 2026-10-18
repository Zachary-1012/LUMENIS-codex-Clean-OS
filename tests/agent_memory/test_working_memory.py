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
        import json
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
        assert row is None  # Unbound memory cannot write TaskEngine execution truth.

    def test_recent_steps_limit(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=True, max_steps=5)
        wm.begin_task("task_limit", "限制测试")
        for i in range(10):
            wm.add_step(f"step_{i}", persist=False)
        assert len(wm.get_recent_steps()) == 5
        assert wm.get_recent_steps()[0]["action"] == "step_5"
        assert [step["seq"] for step in wm.get_recent_steps()] == [6, 7, 8, 9, 10]
        assert wm.get_context()["step_count"] == 10
        assert wm.get_context()["steps_in_memory"] == 5
        assert wm.end_task()["step_count"] == 10

    def test_context_cannot_replace_task_binding_or_step_count(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("actual-task", "actual-goal", {"task_id": "other-task", "goal": "other-goal", "step_count": 99})
        assert wm.get_context()["task_id"] == "actual-task"
        assert wm.get_context()["goal"] == "actual-goal"
        assert wm.get_context()["step_count"] == 0

    def test_missing_step_table_reports_unavailable_without_overwriting_business_status(self, temp_db):
        import sqlite3
        with sqlite3.connect(temp_db) as connection:
            connection.execute("DROP TABLE ai_task_step")
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task-failure", "Preserve actual business result")
        result = wm.add_step("actual-tool", output_data={"observed": "source output"})
        assert result["status"] == "completed"
        assert result["output"] == {"observed": "source output"}
        assert result["persistence"]["state"] == "UNAVAILABLE"
        assert result["persistence"]["code"] == "WORKING_MEMORY_PERSISTENCE_FAILED"
        assert wm.end_task()["persistence"]["failed_steps"] == 1

    def test_long_step_is_valid_json_reopened_by_a_fresh_connection(self, temp_db):
        import json
        import sqlite3
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task-long", "Read source content")
        content = "A long actual source result. " * 240
        result = wm.add_step("read", output_data={"content": content})
        assert result["persistence"]["state"] == "UNAVAILABLE"
        assert result["output"]["content"] == content
        with sqlite3.connect(temp_db) as connection:
            assert connection.execute("SELECT detail FROM ai_task_step WHERE step_id=?", (result["step_id"],)).fetchone() is None

    def test_credentials_are_excluded_from_context_step_and_persisted_observation(self, temp_db):
        import json
        import sqlite3
        credential = "sk-test-working-memory-secret"
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task-safe", "Read source", {"api_key": credential, "source": "public"})
        result = wm.add_step("read", input_data={"authorization": credential},
                             output_data={"content": "Bearer private-credential-material", "observed": True})
        assert result["memory_sanitized"] is True
        assert "api_key" not in wm.get_context()
        assert "authorization" not in result["input"]
        with sqlite3.connect(temp_db) as connection:
            assert connection.execute("SELECT detail FROM ai_task_step WHERE step_id=?", (result["step_id"],)).fetchone() is None
        detail = json.dumps(result)
        assert credential not in detail and "private-credential-material" not in detail
        assert result["output"]["observed"] is True

    def test_oversize_step_fails_durability_explicitly_and_does_not_write_truncated_json(self, temp_db):
        import sqlite3
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task-large", "Preserve business output")
        result = wm.add_step("read", output_data={"content": "x" * (129 * 1024)})
        assert result["persistence"]["code"] == "WORKING_MEMORY_PERSISTENCE_FAILED"
        assert result["status"] == "completed" and len(result["output"]["content"]) == 129 * 1024
        with sqlite3.connect(temp_db) as connection:
            assert connection.execute("SELECT COUNT(*) FROM ai_task_step WHERE task_id='task-large'").fetchone()[0] == 0

    def test_returned_step_cannot_mutate_retained_work(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task-copy", "Retain output")
        result = wm.add_step("read", output_data={"items": ["observed"]}, persist=False)
        result["output"]["items"].append("caller mutation")
        assert wm.get_recent_steps()[0]["output"]["items"] == ["observed"]
        snapshot = wm.get_recent_steps()
        snapshot[0]["output"]["items"].clear()
        assert wm.get_recent_steps()[0]["output"]["items"] == ["observed"]

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

    def test_finished_result_is_redacted_and_cannot_alias_callers_output(self, temp_db):
        import json
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task-finished", "Retain business result")
        actual_result = {"items": ["actual result"], "approval_token": "private-final-token",
                         "note": "Bearer private-final-credential"}
        summary = wm.end_task(actual_result)
        assert summary["result"]["items"] == ["actual result"]
        assert summary["memory_sanitized"] is True
        assert "private-final" not in json.dumps(summary)
        actual_result["items"].append("later caller mutation")
        assert summary["result"]["items"] == ["actual result"]

    def test_archived_observation_cannot_mutate_active_working_steps(self, temp_db):
        from agent_memory.episodic import EpisodicMemory
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        em = EpisodicMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task-archive-copy", "Retain source observation")
        wm.add_step("read", output_data={"items": ["observed"]}, persist=False)
        assert wm.archive_to_episodic(em) is not None
        archived = em.retrieve("case:task-archive-copy")
        archived.value["steps"][0]["output"]["items"].append("archive consumer mutation")
        assert wm.get_recent_steps()[0]["output"]["items"] == ["observed"]

    def test_stats(self, temp_db):
        wm = WorkingMemory(db_path=temp_db, enabled=True)
        wm.begin_task("task_stats", "统计测试")
        s = wm.stats()
        assert s["layer"] == "working"
        assert s["enabled"] is True
        assert s["current_task_id"] == "task_stats"
