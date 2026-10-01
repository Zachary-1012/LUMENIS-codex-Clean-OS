"""Isolated contracts for Source Brief tasks stored by the existing TaskEngine."""
from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

import ai_task_engine as task_engine_module
from ai_task_engine import TaskEngine
from database import get_db


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "managed-report-tasks.db"))
    monkeypatch.setattr(task_engine_module, "_LIFECYCLE_AVAILABLE", False)
    return TaskEngine(auto_init_db=True)


def _context(**overrides):
    context = {
        "actor_ref": "workspace:local",
        "scope": {
            "product_id": "CTH",
            "global_scope": False,
            "entity_label": "Test Subject",
            "subject_id": "subject-test-1",
            "brand_focus_id": None,
        },
        "job_id": "brief-0123456789abcdef0123456789abcdef",
        "limit": 10,
        "image_source_ref": None,
        "business_question": None,
        "permission_audit_ref": "aud_0123456789abcdef",
    }
    context.update(overrides)
    return context


def test_create_report_task_snapshots_exact_context_and_rejects_malformed_json(engine):
    context = _context()
    task = engine.create_report_task(context)
    task_id = task["task_id"]

    assert task_id.startswith("rbrief_")
    assert task["created_by"] == "shared.reporting.source_brief"
    assert task["status"] == "pending"
    assert task["user_input"] == "Source Brief"
    assert task["context"] == context
    assert task["parameters"] == {}

    context["scope"]["entity_label"] = "mutated after create"
    task["context"]["scope"]["entity_label"] = "mutated after read"
    assert engine.get_report_task(task_id)["context"]["scope"]["entity_label"] == "Test Subject"

    with pytest.raises(ValueError):
        engine.create_report_task(_context(limit=101))

    with get_db() as conn:
        conn.execute(
            "UPDATE ai_task SET parameters_json=? WHERE task_id=?",
            ('{"worker_pid":NaN}', task_id),
        )
    with pytest.raises(ValueError, match="malformed JSON"):
        engine.get_report_task(task_id)

    with get_db() as conn:
        conn.execute(
            "UPDATE ai_task SET parameters_json='{}' WHERE task_id=?",
            (task_id,),
        )
        conn.execute(
            "UPDATE ai_task SET context_json=? WHERE task_id=?",
            ('{"actor_ref":', task_id),
        )
    with pytest.raises(ValueError, match="malformed JSON"):
        engine.get_report_task(task_id)


def test_generic_task_methods_cannot_read_or_control_managed_reports(engine):
    generic = engine.create_task(
        "forged context",
        context={"task_id": "rbrief_00000000-0000-0000-0000-000000000000"},
        created_by="shared.reporting.source_brief",
    )
    managed = engine.create_report_task(_context())
    generic_id = generic["task_id"]
    managed_id = managed["task_id"]

    assert generic_id.startswith("task_")
    assert not generic_id.startswith("rbrief_")

    with get_db() as conn:
        conn.execute("UPDATE ai_task SET created_at='2000-01-01' WHERE task_id=?", (generic_id,))
        conn.execute("UPDATE ai_task SET created_at='9999-01-01', status='dlq' WHERE task_id=?", (managed_id,))
        conn.execute(
            "UPDATE ai_task_trace SET started_at='2000-01-01' WHERE task_id=?",
            (generic_id,),
        )
        conn.execute(
            """INSERT INTO ai_task_trace
               (trace_id, task_id, span, detail, status, started_at, finished_at, metadata_json)
               VALUES (?, ?, 'managed-test', '', 'ok', '9999-01-01', '9999-01-01', '{}')""",
            ("trace_managed_visibility", managed_id),
        )

    assert [row["task_id"] for row in engine.list_tasks(limit=1)] == [generic_id]
    assert engine.get_dlq() == []
    assert [row["task_id"] for row in engine.get_trace(limit=1)] == [generic_id]

    for call in (
        lambda: engine.get_task(managed_id),
        lambda: engine.get_steps(managed_id),
        lambda: engine.get_evidence(managed_id),
        lambda: engine.get_trace(managed_id),
        lambda: engine.parse_task(managed_id),
        lambda: engine.select_agent_and_skill(managed_id),
        lambda: engine.check_permission(managed_id),
        lambda: engine.execute_task(managed_id),
        lambda: engine.approve_task(managed_id),
        lambda: engine.cancel_task(managed_id),
        lambda: engine.run_task(managed_id),
    ):
        with pytest.raises(PermissionError):
            call()


def test_claim_is_single_cas_and_restart_requires_explicit_interruption(engine):
    task = engine.create_report_task(_context())
    task_id = task["task_id"]
    barrier = threading.Barrier(3)

    def claim():
        barrier.wait(timeout=5)
        return engine.claim_report_task(task_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(claim) for _ in range(2)]
        barrier.wait(timeout=5)
        outcomes = [future.result(timeout=10) for future in futures]

    assert sorted(outcomes) == [False, True]
    running = engine.get_report_task(task_id)
    old_parameters_json = running["parameters_json"]
    worker = json.loads(old_parameters_json)
    assert set(worker) == {"worker_pid", "worker_started_at"}
    assert worker["worker_pid"] > 0
    assert worker["worker_started_at"] > 0
    assert engine.claim_report_task(task_id) is False

    stale_parameters_json = json.dumps(
        {
            "worker_pid": worker["worker_pid"] + 1,
            "worker_started_at": worker["worker_started_at"],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    assert engine.mark_interrupted_report_task(task_id, stale_parameters_json) is False
    assert engine.get_report_task(task_id)["status"] == "running"
    assert engine.mark_interrupted_report_task(task_id, old_parameters_json) is True
    interrupted = engine.get_report_task(task_id)
    assert interrupted["status"] == "interrupted"
    assert engine.mark_interrupted_report_task(task_id, old_parameters_json) is False

    assert engine.claim_report_task(task_id) is True
    reclaimed = engine.get_report_task(task_id)
    assert reclaimed["status"] == "running"
    active_parameters_json = reclaimed["parameters_json"]
    active_worker = reclaimed["parameters"]
    stale_worker_json = json.dumps(
        {
            "worker_pid": active_worker["worker_pid"] + 1,
            "worker_started_at": active_worker["worker_started_at"],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    with get_db() as conn:
        conn.execute(
            "UPDATE ai_task SET parameters_json=? WHERE task_id=?",
            (stale_worker_json, task_id),
        )
    assert engine.finish_report_task(task_id, result={"artifact_hash": "stale"}) is False
    with get_db() as conn:
        conn.execute(
            "UPDATE ai_task SET parameters_json=? WHERE task_id=?",
            (active_parameters_json, task_id),
        )
    assert engine.finish_report_task(task_id, result={"artifact_hash": "abc123"}) is True
    assert engine.get_report_task(task_id)["status"] == "succeeded"
    assert engine.finish_report_task(task_id, error="late failure") is False
