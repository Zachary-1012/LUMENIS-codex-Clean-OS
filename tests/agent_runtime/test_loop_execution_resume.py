"""Resume execution through reopened TaskEngine and canonical authorization owners."""
import json
import sqlite3

import pytest

from agent_runtime.durable_adapter import DurableExecutionAdapter
from agent_runtime.loop import AgentConfig, AgentLoop
from agent_runtime.planner import Plan, PlanStep
from ai_task_engine import TaskEngine
from tests.agent_runtime.formation_support import trusted_test_executor


class PersistencePermission:
    """Allow only the isolated TaskEngine fixture writes in these tests."""

    def check(self, **_kwargs):
        from types import SimpleNamespace
        return SimpleNamespace(allowed=True)


class NoPlanner:
    def plan(self, *_args, **_kwargs):
        raise AssertionError("resume must restore its plan without replanning")


@pytest.fixture(autouse=True)
def _strict_permission_gate(monkeypatch):
    import lumenis.system.security.permission as permission_module

    monkeypatch.setattr(permission_module, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)


@pytest.fixture
def resume_env(tmp_path, monkeypatch):
    path = tmp_path / "agent-resume.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    import subject_registry

    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE v4_users (
                id INTEGER PRIMARY KEY, role TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE v4_member_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL, product_id TEXT NOT NULL,
                module TEXT NOT NULL, action TEXT NOT NULL, data_scope TEXT,
                time_range TEXT, granted_by INTEGER, created_at TEXT, updated_at TEXT,
                UNIQUE(user_id, product_id, module, action)
            );
            INSERT INTO v4_users (id, role, status) VALUES
                (1, 'user', 'active'), (2, 'user', 'active');
            """
        )
        subject_registry.ensure_schema(conn)
        conn.execute(
            """INSERT INTO lumenis_subject_registry (
                subject_id, brand_focus_id, domain_id, subject_type,
                name_en, name_zh, name_en_norm, name_zh_norm, industry,
                keywords_json, status, created_at, updated_at
            ) VALUES (?, NULL, 'CTH', 'company', 'North Center', '北区中心',
                      'north center', '北区中心', 'retail', '[]', 'configured',
                      '2026-09-24', '2026-09-24')""",
            ("SUBJ-CTH-A",),
        )
        conn.execute(
            """INSERT INTO lumenis_subject_registry (
                subject_id, brand_focus_id, domain_id, subject_type,
                name_en, name_zh, name_en_norm, name_zh_norm, industry,
                keywords_json, status, created_at, updated_at
            ) VALUES (?, NULL, 'CTH', 'company', 'South Center', '南区中心',
                      'south center', '南区中心', 'retail', '[]', 'configured',
                      '2026-09-24', '2026-09-24')""",
            ("SUBJ-CTH-B",),
        )

    from lumenis.system.security import PermissionGate

    gate = PermissionGate()
    engine = TaskEngine()
    adapter = DurableExecutionAdapter(task_engine=engine, permission_gate=PersistencePermission())
    return {"path": path, "gate": gate, "engine": engine, "adapter": adapter}


def _grant(path, *, user_id=1, subject_id="SUBJ-CTH-A", action="read"):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO v4_member_authorizations
               (user_id, product_id, module, action, data_scope)
               VALUES (?, 'CTH', 'evidence', ?, ?)""",
            (user_id, action, json.dumps({"subject_ids": [subject_id]})),
        )


def _context(actor_id=1, subject_id="SUBJ-CTH-A"):
    return {
        "actor": {"id": actor_id, "role": "user"},
        "actor_id": actor_id,
        "domain_id": "cth",
        "scope": {
            "global_scope": False,
            "subject_id": subject_id,
            "brand_focus_id": None,
        },
        "module": "evidence",
    }


def _plan(*, interrupted=None, second_action="read report"):
    first = PlanStep(
        step_id="step-resume-1", index=0, action="read prior report", tool="reader",
        status="completed", result={"output": "Q4 forecast: $4.2M", "estimated_cost": 0.125},
    )
    second = PlanStep(
        step_id="step-resume-2", index=1, action=second_action, tool="reader",
        status=interrupted or "pending",
        risk_level="high" if interrupted and second_action.startswith("write") else "low",
        params={"action_type": "WRITE"} if interrupted and second_action.startswith("write") else {},
    )
    return Plan(
        plan_id="plan-resume-stable", goal="read confidential forecast", steps=[first, second],
        token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    )


def _persist_checkpoint(env, plan, *, state="completed", index=0, steps_started=1,
                        elapsed=0.25, cost=0.12515, replans=0, resumable=True,
                        limits=None, form_pending=True):
    if form_pending:
        owner = _resume_executor([])
        for pending in plan.steps:
            if pending.status not in {"completed", "skipped"}:
                pending.formation = owner.form_step(pending, _context()).binding
    binding = {key: value for key, value in _context().items()
               if key in {"actor_id", "domain_id", "scope"}}
    task_id = env["adapter"].create_task(plan.goal, "agent-resume-test", binding)
    env["adapter"].checkpoint(
        task_id, index, state=state, plan_snapshot=plan.to_dict(), context=binding,
        agent_id="agent-resume-test", step_status="completed" if state == "completed" else "running",
        metadata={
            "resumable": resumable, "elapsed_seconds": elapsed,
            "estimated_cost": cost, "steps_started": steps_started, "replans": replans,
            "limits": limits or {
                "max_steps": 4, "max_time_seconds": 30.0, "max_cost": 1.0,
                "max_retries": 3, "max_replans": 2, "step_timeout_seconds": 60.0,
            },
        },
    )
    return task_id


def _resume_executor(tool_calls):
    return trusted_test_executor(lambda step, _context: (
        tool_calls.append(step.step_id) or {
            "success": True, "output": "fresh result", "estimated_cost": 0.2,
        }))


def _loop(env, *, tool_calls, config=None):
    return AgentLoop(
        config=config or AgentConfig(max_steps=4, max_time_seconds=30, max_cost=1.0,
                                     enable_evaluation=False),
        planner=NoPlanner(),
        durable_adapter=DurableExecutionAdapter(
            task_engine=TaskEngine(), permission_gate=PersistencePermission()),
        tool_binding=_resume_executor(tool_calls),
        permission_gate=env["gate"],
    )


def _loop_without_executor(env):
    return AgentLoop(
        config=AgentConfig(max_steps=4, max_time_seconds=30, max_cost=1.0,
                           enable_evaluation=False),
        planner=NoPlanner(),
        durable_adapter=DurableExecutionAdapter(
            task_engine=TaskEngine(), permission_gate=PersistencePermission()),
        permission_gate=env["gate"],
    )


def test_resume_after_engine_reopen_continues_same_task_and_skips_completed_plan_step(
    resume_env,
):
    _grant(resume_env["path"])
    task_id = _persist_checkpoint(resume_env, _plan(), replans=1)
    calls = []

    result = _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())

    assert result.status == "completed"
    assert result.task_id == task_id
    assert result.plan["plan_id"] == "plan-resume-stable"
    assert [step["step_id"] for step in result.plan["steps"]] == [
        "step-resume-1", "step-resume-2",
    ]
    assert calls == ["step-resume-2"]
    reopened = DurableExecutionAdapter(
        task_engine=TaskEngine(), permission_gate=PersistencePermission()).recover(task_id)
    assert reopened["source"] == "db"
    assert reopened["last_checkpoint"]["state"] == "completed"
    assert reopened["last_checkpoint"]["step_index"] == 2
    assert reopened["last_checkpoint"]["metadata"]["steps_started"] == 2
    assert reopened["last_checkpoint"]["metadata"]["estimated_cost"] == pytest.approx(0.32515)
    assert result.metrics["step_timeout_enforcement"] == "not_enforced_by_synchronous_executor"
    assert result.metrics["steps"] == 2 and result.metrics["replans"] == 1
    assert result.metrics["cost"] == pytest.approx(0.32515)
    assert result.duration_ms >= 250
    with sqlite3.connect(resume_env["path"]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ai_task").fetchone()[0] == 1


def test_legacy_pending_checkpoint_cannot_be_filled_from_new_executor(resume_env):
    _grant(resume_env["path"])
    task_id = _persist_checkpoint(resume_env, _plan(), form_pending=False)
    calls = []
    result = _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())
    assert result.status == "reconciliation_required"
    assert result.error == "TOOL_FORMATION_MISSING"
    assert calls == []
    recovered = resume_env["adapter"].recover(task_id)
    assert recovered["last_checkpoint"]["metadata"]["steps_started"] == 1


def test_resume_requires_injected_executor_but_completed_readback_still_works(resume_env):
    _grant(resume_env["path"])
    pending_task = _persist_checkpoint(resume_env, _plan())
    completed_plan = _plan()
    completed_plan.steps[1].status = "completed"
    completed_plan.steps[1].result = {"output": "final report"}
    completed_task = _persist_checkpoint(
        resume_env, completed_plan, index=2, steps_started=2, cost=0.32515,
    )
    loop = _loop_without_executor(resume_env)
    pending_rows = len(TaskEngine().get_steps(pending_task))

    blocked = loop.resume(pending_task, context=_context())

    assert blocked.status == "blocked"
    assert "TOOL_EXECUTOR_NOT_BOUND" in blocked.error
    assert blocked.goal == "" and blocked.plan is None and blocked.result is None
    assert len(TaskEngine().get_steps(pending_task)) == pending_rows

    completed_rows = len(TaskEngine().get_steps(completed_task))
    already_done = loop.resume(completed_task, context=_context())
    assert already_done.status == "already_completed"
    assert already_done.result["completed_steps"] == 2
    assert already_done.result["final_step_results"][0]["result"]["output"] == "Q4 forecast: $4.2M"
    assert already_done.result["final_step_results"][1]["result"]["output"] == "final report"
    assert len(TaskEngine().get_steps(completed_task)) == completed_rows


@pytest.mark.parametrize(
    "fresh, revoke_grant, expected_layer",
    [
        (_context(actor_id=2), False, "binding"),
        (_context(subject_id="SUBJ-CTH-B"), False, "binding"),
        (_context(), True, "actor_scope"),
    ],
)
def test_resume_requires_current_actor_and_exact_scope_grant(
    resume_env, fresh, revoke_grant, expected_layer,
):
    _grant(resume_env["path"])
    task_id = _persist_checkpoint(resume_env, _plan())
    if revoke_grant:
        with sqlite3.connect(resume_env["path"]) as conn:
            conn.execute("DELETE FROM v4_member_authorizations WHERE user_id=1")
    calls = []

    result = _loop(resume_env, tool_calls=calls).resume(task_id, context=fresh)

    assert result.status == "blocked"
    assert calls == []
    assert result.goal == "" and result.plan is None and result.result is None
    assert "$4.2M" not in repr(result.to_dict())
    if expected_layer == "actor_scope":
        assert "actor scope denied" in result.error


def test_resume_does_not_reuse_cached_permission_allow_after_revocation(resume_env):
    from lumenis.system.security import OperationType, PermissionLevel, RiskLevel

    _grant(resume_env["path"])
    task_id = _persist_checkpoint(resume_env, _plan())
    gate = resume_env["gate"]
    primed = gate.check(
        OperationType.SKILL_EXECUTE, resource="skill:reader", risk_level=RiskLevel.LOW,
        caller="agent_runtime:agent-resume-test", operation_id="step-resume-2",
        domain_id="cth",
    )
    assert primed.allowed
    gate.revoke_permission(PermissionLevel.TEST)
    calls = []

    result = _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())

    assert result.status == "blocked"
    assert "permission denied" in result.error
    assert calls == []
    assert result.goal == "" and result.plan is None and result.result is None
    assert "$4.2M" not in repr(result.to_dict())
    assert gate._idempotency_cache["step-resume-2"].allowed is True


def test_resume_enforces_cumulative_budget_before_execution(resume_env):
    _grant(resume_env["path"])
    plan = _plan()
    task_id = _persist_checkpoint(resume_env, plan, steps_started=4)
    calls = []

    result = _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())

    assert result.status == "max_steps"
    assert calls == []


@pytest.mark.parametrize(
    "saved, current, status, effective_key, effective_limit",
    [
        ({"steps_started": 1, "elapsed": 0.25, "cost": 0.0,
          "limits": {"max_steps": 4, "max_time_seconds": 30.0, "max_cost": 1.0,
                     "max_retries": 3, "max_replans": 2, "step_timeout_seconds": 60.0}},
         {"max_steps": 1}, "max_steps", "max_steps", 1),
        ({"steps_started": 1, "elapsed": 0.25, "cost": 0.12515,
          "limits": {"max_steps": 4, "max_time_seconds": 30.0, "max_cost": 0.1,
                     "max_retries": 3, "max_replans": 2, "step_timeout_seconds": 60.0}},
         {}, "max_cost", "max_cost", 0.1),
        ({"steps_started": 1, "elapsed": 0.25, "cost": 0.0,
          "limits": {"max_steps": 4, "max_time_seconds": 0.1, "max_cost": 1.0,
                     "max_retries": 3, "max_replans": 2, "step_timeout_seconds": 60.0}},
         {}, "max_time", "max_time_seconds", 0.1),
    ],
)
def test_resume_uses_minimum_current_and_saved_cumulative_budgets(
    resume_env, saved, current, status, effective_key, effective_limit,
):
    _grant(resume_env["path"])
    task_id = _persist_checkpoint(
        resume_env, _plan(), steps_started=saved["steps_started"],
        elapsed=saved["elapsed"], cost=saved["cost"], limits=saved["limits"],
    )
    calls = []
    config = AgentConfig(max_steps=current.get("max_steps", 4),
                         max_time_seconds=current.get("max_time_seconds", 30.0),
                         max_cost=current.get("max_cost", 1.0), enable_evaluation=False)

    result = _loop(resume_env, tool_calls=calls, config=config).resume(task_id, context=_context())

    assert result.status == status
    assert result.metrics["effective_budget_limits"][effective_key] == effective_limit
    assert calls == []


def test_interrupted_consequential_step_requires_reconciliation_before_security_or_effects(
    resume_env, monkeypatch,
):
    from lumenis.system.security import get_effect_fence

    _grant(resume_env["path"], action="write")
    plan = _plan(interrupted="running", second_action="write report")
    task_id = _persist_checkpoint(
        resume_env, plan, state="executing", index=1, steps_started=2,
    )
    calls = []
    loop = _loop(resume_env, tool_calls=calls)
    security_calls, fence_calls = [], []
    monkeypatch.setattr(loop, "_check_security", lambda *_args, **_kwargs: security_calls.append(True))
    monkeypatch.setattr(
        "lumenis.system.security.get_effect_fence",
        lambda: fence_calls.append(True) or get_effect_fence(),
    )

    result = loop.resume(task_id, context=_context())

    assert result.status == "reconciliation_required"
    assert security_calls == []
    assert fence_calls == []
    assert len(resume_env["gate"].get_audit_log()) == 0
    assert calls == []


def test_reopened_interrupted_read_step_resumes_once_with_same_task_and_step_ids(resume_env):
    _grant(resume_env["path"])
    plan = _plan(interrupted="running", second_action="read report")
    task_id = _persist_checkpoint(
        resume_env, plan, state="executing", index=1, steps_started=2,
    )
    calls = []

    resumed = _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())

    assert resumed.status == "completed"
    assert resumed.task_id == task_id
    assert [step["step_id"] for step in resumed.plan["steps"]] == [
        "step-resume-1", "step-resume-2",
    ]
    assert calls == ["step-resume-2"]
    adapter = DurableExecutionAdapter(
        task_engine=TaskEngine(), permission_gate=PersistencePermission())
    reopened = adapter.recover(task_id)
    assert reopened["last_checkpoint"]["state"] == "completed"
    assert reopened["last_checkpoint"]["metadata"]["steps_started"] == 3
    checkpoint_count = len(TaskEngine().get_steps(task_id))

    duplicate_read = _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())

    assert duplicate_read.status == "already_completed"
    assert len(TaskEngine().get_steps(task_id)) == checkpoint_count
    assert calls == ["step-resume-2"]


def test_completed_task_readback_requires_fresh_auth_and_does_not_add_checkpoint(resume_env):
    _grant(resume_env["path"])
    plan = _plan()
    task_id = _persist_checkpoint(resume_env, plan)
    calls = []
    completed = _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())
    assert completed.status == "completed"
    engine = TaskEngine()
    checkpoint_count = len(engine.get_steps(task_id))

    reopened_result = _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())

    assert reopened_result.status == "already_completed"
    assert reopened_result.result["completed_steps"] == 2
    assert len(TaskEngine().get_steps(task_id)) == checkpoint_count
    assert calls == ["step-resume-2"]


def test_completed_result_is_not_returned_after_scope_revocation(resume_env):
    _grant(resume_env["path"])
    task_id = _persist_checkpoint(resume_env, _plan())
    calls = []
    assert _loop(resume_env, tool_calls=calls).resume(task_id, context=_context()).status == "completed"
    with sqlite3.connect(resume_env["path"]) as conn:
        conn.execute("DELETE FROM v4_member_authorizations WHERE user_id=1")

    denied = _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())

    assert denied.status == "blocked"
    assert denied.goal == "" and denied.plan is None and denied.result is None
    assert calls == ["step-resume-2"]


def test_resume_rejects_approval_material_in_fresh_context(resume_env):
    _grant(resume_env["path"])
    task_id = _persist_checkpoint(resume_env, _plan())
    context = _context()
    context["approval_token"] = "caller-approval-secret"
    calls = []

    result = _loop(resume_env, tool_calls=calls).resume(task_id, context=context)

    assert result.status == "blocked"
    assert result.goal == "" and result.plan is None and result.result is None
    assert "caller-approval-secret" not in repr(result.to_dict())
    assert calls == []


def test_resume_rejects_missing_nonresumable_cancelled_and_corrupt_checkpoints(resume_env):
    from agent_runtime.durable_adapter import DurableExecutionAdapter

    adapter = resume_env["adapter"]
    missing = adapter.create_task("read two reports", "agent-resume-test", {
        "actor_id": 1, "domain_id": "cth", "scope": _context()["scope"],
    })
    nonresumable = _persist_checkpoint(resume_env, _plan(), resumable=False)
    cancelled = _persist_checkpoint(resume_env, _plan())
    adapter.cancel(cancelled)
    corrupt = _persist_checkpoint(resume_env, _plan())
    with sqlite3.connect(resume_env["path"]) as conn:
        row = conn.execute("""SELECT step_id, detail FROM ai_task_step
                              WHERE task_id=? ORDER BY rowid DESC LIMIT 1""", (corrupt,)).fetchone()
        envelope = json.loads(row[1])
        envelope["checkpoint"]["state"] = "surprise"
        conn.execute("UPDATE ai_task_step SET detail=? WHERE step_id=?", (json.dumps(envelope), row[0]))
    loop = _loop(resume_env, tool_calls=[])

    for task_id in (missing, nonresumable, cancelled, corrupt):
        with pytest.raises(RuntimeError):
            loop.resume(task_id, context=_context())


def test_resume_rejects_memory_only_checkpoint(resume_env):
    memory = DurableExecutionAdapter(enabled=False, permission_gate=PersistencePermission())
    task_id = memory.create_task("read confidential forecast", "agent-resume-test", {
        "actor_id": 1, "domain_id": "cth", "scope": _context()["scope"],
    })
    memory.checkpoint(
        task_id, 0, state="completed", plan_snapshot=_plan().to_dict(),
        context={"actor_id": 1, "domain_id": "cth", "scope": _context()["scope"]},
        agent_id="agent-resume-test", step_status="completed",
        metadata={
            "resumable": True, "elapsed_seconds": 0.25, "estimated_cost": 0.1,
            "steps_started": 1, "replans": 0,
            "limits": {"max_steps": 4, "max_time_seconds": 30, "max_cost": 1,
                       "max_retries": 3, "max_replans": 2, "step_timeout_seconds": 60},
        },
    )
    loop = AgentLoop(
        config=AgentConfig(enable_durable_execution=False, enable_evaluation=False),
        planner=NoPlanner(), durable_adapter=memory, permission_gate=resume_env["gate"],
    )

    with pytest.raises(RuntimeError, match="TaskEngine-backed checkpoint"):
        loop.resume(task_id, context=_context())


def test_resume_after_last_step_before_final_commit_never_repeats_tool(resume_env):
    _grant(resume_env["path"])
    plan = _plan()
    plan.steps[1].status = "completed"
    plan.steps[1].result = {"output": "persisted last result"}
    task_id = _persist_checkpoint(resume_env, plan, state="completed", index=1, steps_started=2)
    calls = []
    reopened = _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())
    assert reopened.status == "already_completed"
    assert calls == []
    assert TaskEngine().get_task(task_id)["status"] == "succeeded"
    assert TaskEngine().get_task(task_id)["result"] == reopened.result
    count = len(TaskEngine().get_steps(task_id))
    _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())
    assert len(TaskEngine().get_steps(task_id)) == count
    assert calls == []
