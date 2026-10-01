"""Checkpoint contract tests against an isolated, reopened TaskEngine database."""
import json
from types import SimpleNamespace

import pytest

from agent_runtime.durable_adapter import DurableExecutionAdapter
from agent_runtime.loop import AgentConfig, AgentLoop
from agent_runtime.planner import Plan, PlanStep
from ai_task_engine import TaskEngine


class ControlledPermission:
    def check(self, **kwargs):
        return SimpleNamespace(allowed=True)


class StaticPlanner:
    def __init__(self, plan):
        self.plan_value = plan

    def plan(self, *args, **kwargs):
        return self.plan_value


@pytest.fixture
def durable(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "checkpoint.sqlite3"))
    gate = ControlledPermission()
    engine = TaskEngine()
    return engine, gate, DurableExecutionAdapter(task_engine=engine, permission_gate=gate)


def _run(plan, adapter, monkeypatch, context):
    loop = AgentLoop(
        config=AgentConfig(max_steps=4, max_time_seconds=30, max_cost=1.0,
                           enable_evaluation=False),
        planner=StaticPlanner(plan),
        durable_adapter=adapter,
        tool_executor=lambda step, ctx: {
            "success": True, "output": "completed output", "estimated_cost": 0.125,
        },
    )
    # This batch verifies checkpoint persistence, not the production permission chain.
    monkeypatch.setattr(loop, "_check_security", lambda step, ctx: {"allowed": True})
    return loop.run(plan.goal, context=context, agent_id="agent-checkpoint-test")


def test_completed_plan_and_cumulative_budget_survive_engine_reopen(durable, monkeypatch):
    _engine, gate, adapter = durable
    step = PlanStep(step_id="step-stable-1", index=0, action="read report", tool="reader")
    plan = Plan(plan_id="plan-stable", goal="read report", steps=[step],
                token_usage={"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150},
                raw_response="raw planner response is omitted")

    result = _run(plan, adapter, monkeypatch, {
        "actor_id": "actor-1", "domain_id": "cth", "scope": "weekly-report",
        "private_note": "must not enter the checkpoint",
    })

    reopened = DurableExecutionAdapter(task_engine=TaskEngine(), permission_gate=gate).recover(result.task_id)
    assert reopened["source"] == "db"
    assert reopened["task"]["context"] == {
        "actor_id": "actor-1", "domain_id": "cth", "scope": "weekly-report",
    }
    checkpoint = reopened["last_checkpoint"]
    snapshot = checkpoint["plan_snapshot"]
    assert snapshot["plan_id"] == "plan-stable"
    assert "raw_response" not in snapshot
    assert snapshot["token_usage"] == {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}
    assert snapshot["steps"][0]["step_id"] == "step-stable-1"
    assert snapshot["steps"][0]["status"] == "completed"
    assert snapshot["steps"][0]["result"]["output"] == "completed output"
    assert checkpoint["context"] == {
        "actor_id": "actor-1", "domain_id": "cth", "scope": "weekly-report",
    }

    assert checkpoint["metadata"]["steps_started"] == 1
    assert checkpoint["metadata"]["replans"] == 0
    assert checkpoint["metadata"]["elapsed_seconds"] >= 0
    assert checkpoint["metadata"]["estimated_cost"] == pytest.approx(0.12515)
    assert checkpoint["metadata"]["limits"] == {
        "max_steps": 4, "max_time_seconds": 30, "max_cost": 1.0,
        "max_retries": 3, "max_replans": 2, "step_timeout_seconds": 60.0,
    }
    assert checkpoint["metadata"]["resumable"] is True


def test_secret_plan_material_is_omitted_and_checkpoint_marked_non_resumable(
    durable, monkeypatch,
):
    engine, gate, adapter = durable
    plan = Plan(
        plan_id="plan-sensitive", goal="read report",
        steps=[PlanStep(
            step_id="step-sensitive", index=0, action="read report", tool="reader",
            params={"api_key": "private-api-key-value", "approval_token": "approval-secret",
                    "session_cookie": "session-secret",
                    "note": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz"},
        )],
    )
    result = _run(plan, adapter, monkeypatch, {"actor_id": "actor-1", "domain_id": "cth", "scope": "report"})

    reopened = DurableExecutionAdapter(task_engine=TaskEngine(), permission_gate=gate).recover(result.task_id)
    checkpoint = reopened["last_checkpoint"]
    assert checkpoint["metadata"]["resumable"] is False
    assert checkpoint["metadata"]["non_resumable_reason"] == "sensitive checkpoint material omitted"
    params = checkpoint["plan_snapshot"]["steps"][0]["params"]
    assert "api_key" not in params and "approval_token" not in params and "session_cookie" not in params
    assert params["note"] == "Authorization: [REDACTED]"

    persisted = json.dumps(engine.get_steps(result.task_id), sort_keys=True)
    for secret in ("private-api-key-value", "approval-secret", "session-secret", "abcdefghijklmnopqrstuvwxyz"):
        assert secret not in persisted


def test_credential_in_goal_is_sanitized_only_in_persistence(durable, monkeypatch):
    engine, gate, adapter = durable
    credential = "Bearer abcdefghijklmnopqrstuvwxyz"
    goal = f"read report using {credential}"
    plan = Plan(plan_id="plan-goal-secret", goal=goal,
                steps=[PlanStep(step_id="step-goal-secret", index=0,
                                action="read report", tool="reader")])

    result = _run(plan, adapter, monkeypatch, {"actor_id": "actor-1", "domain_id": "cth", "scope": "report"})

    persisted_goal = "read report using [REDACTED]"
    assert engine.get_task(result.task_id)["user_input"] == persisted_goal
    assert adapter._memory_tasks[result.task_id]["goal"] == persisted_goal
    assert result.goal == goal and result.plan["goal"] == goal

    reopened = DurableExecutionAdapter(task_engine=TaskEngine(), permission_gate=gate).recover(result.task_id)
    checkpoint = reopened["last_checkpoint"]
    assert checkpoint["plan_snapshot"]["goal"] == persisted_goal
    assert checkpoint["metadata"]["resumable"] is False
    persisted = json.dumps({"task": engine.get_task(result.task_id),
                            "steps": engine.get_steps(result.task_id)}, sort_keys=True)
    assert "abcdefghijklmnopqrstuvwxyz" not in persisted
