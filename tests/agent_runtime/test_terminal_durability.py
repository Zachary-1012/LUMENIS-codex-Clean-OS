"""Real SQLite atomic outcomes; authorization is an explicit isolated fixture."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from ai_task_engine import TaskEngine
from agent_runtime.durable_adapter import DurableExecutionAdapter


class Permission:
    def check(self, **kwargs):
        return SimpleNamespace(allowed=True)


@pytest.fixture
def durable(tmp_path, monkeypatch):
    path = tmp_path / "terminal.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    adapter = DurableExecutionAdapter(task_engine=TaskEngine(), permission_gate=Permission())
    task = adapter.create_task("deterministic local result")
    return path, adapter, task


def finalize(adapter, task, state="completed", result=None, error=None):
    return adapter.finalize_task(task, state, result=result, error=error, step_index=1,
        plan_snapshot={"plan_id": "stable", "steps": [{"status": state}]})


@pytest.mark.parametrize("state,status,result,error", [
    ("completed", "succeeded", {"count": 0}, None),
    ("failed", "failed", None, "input invalid"),
    ("cancelled", "cancelled", None, "user cancelled"),
])
def test_terminal_records_reopen_together(durable, state, status, result, error):
    path, adapter, task = durable
    cp = finalize(adapter, task, state, result, error)
    reopened = DurableExecutionAdapter(task_engine=TaskEngine(), permission_gate=Permission())
    saved = reopened.recover(task)
    assert saved["task"]["status"] == status
    assert saved["task"].get("result") == result
    assert saved["task"]["error"] == error
    assert saved["last_checkpoint"] == cp.to_dict()


def test_sqlite_update_failure_rolls_back_terminal_checkpoint(durable):
    path, adapter, task = durable
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TRIGGER fail_terminal BEFORE UPDATE ON ai_task BEGIN SELECT RAISE(ABORT,'disk fault'); END")
    with pytest.raises(RuntimeError, match="could not persist"):
        finalize(adapter, task, result={"count": 3})
    assert adapter.get_task(task)["status"] == "pending"
    assert adapter.get_checkpoints(task) == []
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TRIGGER fail_terminal")
    finalize(adapter, task, result={"count": 3})
    assert adapter.get_task(task)["status"] == "succeeded"


def test_concurrent_repeat_finalization_is_one_commit(durable):
    path, adapter, task = durable
    def write(_):
        other = DurableExecutionAdapter(task_engine=TaskEngine(), permission_gate=Permission())
        return finalize(other, task, result={"count": 3}).checkpoint_id
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(write, range(2)))
    assert ids[0] == ids[1]
    assert len(adapter.get_checkpoints(task)) == 1
    with pytest.raises(RuntimeError):
        finalize(adapter, task, result={"count": 4})
    assert adapter.get_task(task)["result"] == {"count": 3}


def test_prior_cancel_cannot_be_overwritten_by_late_success(durable):
    path, adapter, task = durable
    adapter.cancel(task, "stop now")
    with pytest.raises(RuntimeError):
        finalize(adapter, task, result={"count": 3})
    assert adapter.get_task(task)["status"] == "cancelled"
    finalize(adapter, task, state="cancelled")
    assert adapter.get_task(task)["error"] == "stop now"
    assert adapter.recover(task)["last_checkpoint"]["state"] == "cancelled"


def test_failed_task_resumes_through_running_checkpoint_without_new_task(durable):
    path, adapter, task = durable
    finalize(adapter, task, state="failed", error="retryable read failure")
    adapter.checkpoint(task, 0, "executing", plan_snapshot={"plan_id": "stable", "steps": []})
    assert adapter.get_task(task)["status"] == "running"
    assert adapter.get_task(task)["finished_at"] is None
    finalize(adapter, task, result={"count": 3})
    assert adapter.get_task(task)["status"] == "succeeded"
    assert len(adapter.list_tasks()) == 1


def test_completed_task_cannot_reopen_an_execution_checkpoint(durable):
    path, adapter, task = durable
    finalize(adapter, task, result={"count": 3})
    with pytest.raises(RuntimeError):
        adapter.checkpoint(task, 0, "executing")
    assert adapter.get_task(task)["status"] == "succeeded"
