# -*- coding: utf-8 -*-
"""
Unit tests for agent_runtime.durable_adapter
覆盖：任务创建、检查点、取消、恢复、重试、证据保存
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_runtime.durable_adapter import DurableExecutionAdapter, Checkpoint


class TestDurableAdapterInit:
    def test_default_enabled(self):
        adapter = DurableExecutionAdapter(enabled=False)
        assert adapter._enabled is False

    def test_memory_only_mode(self):
        adapter = DurableExecutionAdapter(enabled=False)
        assert adapter._memory_checkpoints == {}
        assert adapter._memory_tasks == {}


class TestTaskCreation:
    def test_create_task(self):
        adapter = DurableExecutionAdapter(enabled=False)
        task_id = adapter.create_task("test goal", agent_id="agent_1", context={"k": "v"})
        assert task_id
        assert task_id.startswith("agent_")
        task = adapter.get_task(task_id)
        assert task["goal"] == "test goal"
        assert task["agent_id"] == "agent_1"
        assert task["status"] == "created"

    def test_create_task_unique_ids(self):
        adapter = DurableExecutionAdapter(enabled=False)
        id1 = adapter.create_task("goal1")
        id2 = adapter.create_task("goal2")
        assert id1 != id2


class TestCheckpoint:
    def test_save_checkpoint(self):
        adapter = DurableExecutionAdapter(enabled=False)
        task_id = adapter.create_task("test")
        cp = adapter.checkpoint(
            task_id=task_id, step_index=0, state="executing",
            step_detail="doing something", step_status="running",
        )
        assert cp.checkpoint_id
        assert cp.task_id == task_id
        assert cp.step_index == 0
        assert cp.state == "executing"

    def test_multiple_checkpoints(self):
        adapter = DurableExecutionAdapter(enabled=False)
        task_id = adapter.create_task("test")
        adapter.checkpoint(task_id, 0, "executing")
        adapter.checkpoint(task_id, 1, "executing")
        adapter.checkpoint(task_id, 2, "completed")
        checkpoints = adapter.get_checkpoints(task_id)
        assert len(checkpoints) == 3
        assert checkpoints[-1].state == "completed"

    def test_complete_step(self):
        adapter = DurableExecutionAdapter(enabled=False)
        task_id = adapter.create_task("test")
        adapter.complete_step(task_id, 0, result={"output": "ok"}, error=None)
        checkpoints = adapter.get_checkpoints(task_id)
        assert len(checkpoints) >= 1
        assert checkpoints[-1].state == "completed"

    def test_fail_step(self):
        adapter = DurableExecutionAdapter(enabled=False)
        task_id = adapter.create_task("test")
        adapter.complete_step(task_id, 0, result=None, error="something failed")
        checkpoints = adapter.get_checkpoints(task_id)
        assert checkpoints[-1].state == "failed"


class TestCancel:
    def test_cancel_task(self):
        adapter = DurableExecutionAdapter(enabled=False)
        task_id = adapter.create_task("test")
        result = adapter.cancel(task_id, reason="user cancelled")
        assert result is True
        task = adapter.get_task(task_id)
        assert task["status"] == "cancelled"
        assert task["cancel_reason"] == "user cancelled"

    def test_cancel_nonexistent_task(self):
        adapter = DurableExecutionAdapter(enabled=False)
        result = adapter.cancel("nonexistent")
        assert result is True  # 内存取消总是成功


class TestRecover:
    def test_recover_from_memory(self):
        adapter = DurableExecutionAdapter(enabled=False)
        task_id = adapter.create_task("test")
        adapter.checkpoint(task_id, 0, "executing")
        adapter.checkpoint(task_id, 1, "completed")
        recovered = adapter.recover(task_id)
        assert recovered is not None
        assert recovered["source"] == "memory"
        assert recovered["checkpoint_count"] == 2
        assert recovered["last_checkpoint"]["state"] == "completed"

    def test_recover_nonexistent(self):
        adapter = DurableExecutionAdapter(enabled=False)
        result = adapter.recover("nonexistent")
        assert result is None


class TestRetry:
    def test_retry_step(self):
        adapter = DurableExecutionAdapter(enabled=False)
        task_id = adapter.create_task("test")
        r1 = adapter.retry_step(task_id, 0, max_retries=3)
        assert r1["retry_count"] == 1
        assert r1["can_retry"] is True

        r2 = adapter.retry_step(task_id, 0, max_retries=3)
        assert r2["retry_count"] == 2

        r3 = adapter.retry_step(task_id, 0, max_retries=3)
        assert r3["retry_count"] == 3
        assert r3["can_retry"] is False

    def test_retry_different_steps_independent(self):
        adapter = DurableExecutionAdapter(enabled=False)
        task_id = adapter.create_task("test")
        adapter.retry_step(task_id, 0)
        adapter.retry_step(task_id, 0)
        r = adapter.retry_step(task_id, 1)  # 不同步骤独立计数
        assert r["retry_count"] == 1


class TestListTasks:
    def test_list_all_tasks(self):
        adapter = DurableExecutionAdapter(enabled=False)
        adapter.create_task("goal1")
        adapter.create_task("goal2")
        tasks = adapter.list_tasks()
        assert len(tasks) == 2

    def test_list_by_status(self):
        adapter = DurableExecutionAdapter(enabled=False)
        t1 = adapter.create_task("goal1")
        t2 = adapter.create_task("goal2")
        adapter.cancel(t2)
        created = adapter.list_tasks(status="created")
        assert len(created) == 1
        assert created[0]["task_id"] == t1


class TestEvidence:
    def test_save_evidence_disabled(self):
        """Durable 禁用时 save_evidence 返回 None。"""
        adapter = DurableExecutionAdapter(enabled=False)
        result = adapter.save_evidence("task_1", "test_type", "content")
        assert result is None


class TestReset:
    def test_reset_clears_memory(self):
        adapter = DurableExecutionAdapter(enabled=False)
        adapter.create_task("test")
        adapter.reset()
        assert adapter.list_tasks() == []
        assert adapter._memory_checkpoints == {}


class TestCheckpointDataclass:
    def test_checkpoint_to_dict(self):
        cp = Checkpoint(agent_id="a1", task_id="t1", step_index=0, state="running")
        d = cp.to_dict()
        assert d["agent_id"] == "a1"
        assert d["task_id"] == "t1"
        assert d["step_index"] == 0
        assert d["state"] == "running"
        assert "checkpoint_id" in d
        assert "created_at" in d
