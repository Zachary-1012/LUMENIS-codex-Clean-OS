"""Real TaskEngine persistence behind an explicit disposable permission fixture."""
import json
from types import SimpleNamespace

import pytest

from agent_runtime.durable_adapter import DurableExecutionAdapter
from ai_task_engine import TaskEngine


class ControlledPermission:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def check(self, **kwargs):
        return SimpleNamespace(allowed=self.allowed)


@pytest.fixture
def durable(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "durable.sqlite3"))
    engine = TaskEngine()
    gate = ControlledPermission()
    return engine, gate, DurableExecutionAdapter(task_engine=engine, permission_gate=gate)


def test_fresh_adapter_reopens_task_plan_context_and_cancel(durable):
    engine, gate, adapter = durable
    task = adapter.create_task("resume scoped report", agent_id="agent-report", context={"scope": "exact"})
    assert isinstance(task, str) and task.startswith("task_")
    first = adapter.checkpoint(task, 0, "executing", plan_snapshot={"steps": ["read", "analyze"]},
                               context={"result_ref": "report-ref"}, agent_id="agent-report")
    fresh = DurableExecutionAdapter(task_engine=TaskEngine(), permission_gate=gate)
    reopened = fresh.recover(task)
    assert reopened["source"] == "db" and reopened["checkpoint_count"] == 1
    assert reopened["last_checkpoint"] == first.to_dict()
    assert reopened["task"]["context"] == {"scope": "exact"}
    assert reopened["task"]["agent_id"] == "agent-report"
    assert fresh.get_checkpoints(task)[0] == first
    fresh.complete_step(task, 0, result={"observation": "long text " * 100})
    assert len(fresh.recover(task)["last_checkpoint"]["metadata"]["result"]["observation"]) > 500
    assert fresh.get_task(task)["status"] == "pending"  # A finished step is not a finished task.
    assert fresh.cancel(task)
    assert adapter.get_task(task)["status"] == "cancelled"  # Do not trust an old memory snapshot.
    assert fresh.list_tasks(status="cancelled")[0]["task_id"] == task


def test_fresh_adapter_reopens_gateway_inference_receipt_metrics_and_provenance(durable):
    _engine, gate, adapter = durable
    task = adapter.create_task("resume owned analysis", agent_id="agent-analysis")
    receipt = {
        "provider": "owned",
        "model_id": "lumenis-owned-model",
        "model_revision": "revision-7",
        "run_id": "run-7",
        "request_digest": "a" * 64,
        "source_binding_sha256": "b" * 64,
        "admission_audit_hashes": {"permission": "c" * 64},
        "source_evidence_refs": ["evidence-1", "evidence-2"],
        "prompt_tokens": 31,
        "completion_tokens": 17,
        "total_tokens": 48,
        "context_window_tokens": 4096,
        "output_token_limit": 64,
    }
    adapter.checkpoint(
        task,
        0,
        "executing",
        plan_snapshot={
            "plan_id": "plan-owned-7",
            "steps": [{"step_id": "step-0", "description": "analyze"}],
            "inference_receipt": receipt,
        },
        agent_id="agent-analysis",
    )

    fresh = DurableExecutionAdapter(task_engine=TaskEngine(), permission_gate=gate)
    reopened = fresh.recover(task)
    checkpoint = reopened["last_checkpoint"]

    assert reopened["source"] == "db"
    assert checkpoint["metadata"]["resumable"] is True
    assert checkpoint["plan_snapshot"]["inference_receipt"] == receipt


def test_permission_denial_is_not_memory_success(durable):
    engine, gate, adapter = durable
    gate.allowed = False
    with pytest.raises(PermissionError):
        adapter.create_task("must not exist")
    assert engine.list_tasks() == [] and adapter._memory_tasks == {}
    gate.allowed = True
    task = adapter.create_task("permitted before revocation")
    gate.allowed = False
    with pytest.raises(PermissionError):
        adapter.checkpoint(task, 0, "executing")
    with pytest.raises(PermissionError):
        adapter.cancel(task)
    assert engine.get_steps(task) == [] and engine.get_task(task)["status"] == "pending"


def test_enabled_database_failure_never_uses_cached_checkpoint(durable, monkeypatch):
    engine, _gate, adapter = durable
    task = adapter.create_task("one task")
    adapter.checkpoint(task, 0, "executing")
    def failed(*args, **kwargs):
        raise OSError("isolated disk unavailable")
    monkeypatch.setattr(engine, "_db_add_step", failed)
    with pytest.raises(RuntimeError, match="could not persist"):
        adapter.checkpoint(task, 1, "executing")
    assert len(adapter._memory_checkpoints[task]) == 1
    monkeypatch.setattr(engine, "get_steps", failed)
    with pytest.raises(RuntimeError, match="could not recover"):
        adapter.recover(task)


def test_enabled_engine_unavailable_is_explicit(monkeypatch):
    adapter = DurableExecutionAdapter(permission_gate=ControlledPermission())
    monkeypatch.setattr(adapter, "_get_task_engine", lambda: None)
    with pytest.raises(RuntimeError, match="unavailable"):
        adapter.create_task("no false durable ID")
    assert adapter._memory_tasks == {}


@pytest.mark.parametrize("bad_detail", ["old unstructured checkpoint", "[]", '{"version":9}',
                                      json.dumps({"format":"lumenis.agent_runtime.checkpoint", "version":1,
                                                  "checkpoint":{"task_id":"wrong", "step_index":0}})])
def test_malformed_or_mismatched_checkpoint_cannot_be_resumed(durable, bad_detail):
    engine, gate, adapter = durable
    task = adapter.create_task("one task")
    engine._db_add_step(task, phase="agent_step_0", detail=bad_detail)
    fresh = DurableExecutionAdapter(task_engine=engine, permission_gate=gate)
    with pytest.raises(RuntimeError, match="Persisted agent checkpoint"):
        fresh.recover(task)


def test_corrupt_context_is_not_silently_changed_to_empty(durable):
    engine, _gate, adapter = durable
    task = adapter.create_task("one task")
    engine._db_update_task(task, context_json="invalid json")
    with pytest.raises(RuntimeError, match="context is malformed"):
        adapter.get_task(task)
