"""A replan must retain the job and completed work, not manufacture completion."""
from copy import deepcopy

import pytest

from agent_runtime.durable_adapter import DurableExecutionAdapter
from tests.agent_runtime.formation_support import unit_identity
from agent_capability.formation import BoundToolExecutor, FormationError
from agent_runtime.loop import AgentConfig, AgentLoop
from agent_runtime.planner import Plan, PlanStep
from agent_runtime.replanner import ReplanDecision, Replanner


class StaticPlanner:
    def __init__(self, plan):
        self.value = plan

    def plan(self, *args, **kwargs):
        return self.value


def _plan():
    return Plan(goal="read the source and produce a report", steps=[
        PlanStep(step_id="read-source", index=0, action="read source", tool="reader",
                 expected_output="source material"),
        PlanStep(step_id="write-report", index=1, action="produce report", tool="reporter",
                 expected_output="report", risk_level="high"),
    ])


def _loop(plan, executor, monkeypatch, replanner=None, report_effect="WRITE"):
    # These are explicit server-side UNIT tool declarations. The simulated
    # report writer must not be mislabeled ANALYZE, or rely on numeric ranking.
    bindings = {name: BoundToolExecutor(executor, origin="lumenis-unit-tests",
                    resource_uri=f"tool://unit-replan/{name}", identity_provider=unit_identity,
                    action_type=effect)
                for name, effect in {"reader": "READ", "reporter": report_effect}.items()}

    class FixtureBindings:
        def form_step(self, step, context, *, expected=None):
            selected = bindings.get(step.tool)
            if selected is None:
                raise FormationError("TOOL_IMPLEMENTATION_NOT_BOUND")
            return selected.form_step(step, context, expected=expected)

    loop = AgentLoop(
        config=AgentConfig(max_steps=10, max_retries=1, max_replans=1,
                           enable_evaluation=False),
        planner=StaticPlanner(plan), replanner=replanner,
        durable_adapter=DurableExecutionAdapter(enabled=False), tool_binding=FixtureBindings(),
    )
    # These are loop contract tests; no production permission or effect is bypassed.
    monkeypatch.setattr(loop, "_check_security", lambda step, context: {"allowed": True})
    return loop


def test_parameter_repair_cannot_retry_uncertain_write_and_retains_completed_source(monkeypatch):
    plan = _plan()
    calls = []

    def execute(step, context):
        calls.append(step.tool)
        if step.tool == "reporter" and calls.count("reporter") == 1:
            return {"success": False, "error": "invalid param: format"}
        return {"success": True, "output": "actual " + step.expected_output}

    result = _loop(plan, execute, monkeypatch).run(plan.goal)

    assert result.status == "reconciliation_required"
    assert "Consequential tool outcome" in result.error, (result.error, result.metrics)
    assert calls == ["reader", "reporter"]
    assert [step["step_id"] for step in result.plan["steps"]] == ["read-source", "write-report"]
    assert result.result is None
    assert result.plan["steps"][0]["result"]["output"] == "actual source material"


class ReplacingReplanner(Replanner):
    def __init__(self, mutation):
        super().__init__(max_replans=1)
        self.mutation = mutation

    def replan(self, goal, current_plan, decision, observation=None, context=None):
        self._replan_count += 1
        candidate = deepcopy(current_plan)
        self.mutation(candidate)
        return candidate


@pytest.mark.parametrize("mutation,error", [
    (lambda p: setattr(p, "steps", p.steps[:1]), "REPLAN_REQUIRED_STEP_LOST"),
    (lambda p: setattr(p, "steps", []), "REPLAN_EMPTY_PLAN"),
    (lambda p: setattr(p, "goal", "read only"), "REPLAN_GOAL_CHANGED"),
    (lambda p: setattr(p.steps[1], "status", "completed"), "REPLAN_UNEXECUTED_STEP_COMPLETED"),
    (lambda p: setattr(p.steps[1], "risk_level", "low"), "REPLAN_RISK_DOWNGRADE"),
    (lambda p: setattr(p.steps[0], "result", {"success": True, "output": "invented"}),
     "REPLAN_COMPLETED_STEP_CHANGED"),
    (lambda p: setattr(p.steps[1], "expected_output", "a cheaper partial result"),
     "REPLAN_REQUIRED_OUTCOME_CHANGED"),
])
def test_replan_cannot_erase_or_claim_a_required_outcome(monkeypatch, mutation, error):
    plan = _plan()

    def execute(step, context):
        return ({"success": True, "output": "actual source material"}
                if step.tool == "reader" else {"success": False, "error": "invalid param"})

    result = _loop(plan, execute, monkeypatch, ReplacingReplanner(mutation)).run(plan.goal)

    assert result.status == "reconciliation_required"
    assert "Consequential tool outcome" in result.error, (result.error, result.metrics)
    assert result.result is None
    assert len(result.plan["steps"]) == 2
    assert result.plan["steps"][0]["result"]["output"] == "actual source material"
    assert result.plan["steps"][1]["status"] == "failed"
    # Preserve every original negative replan assertion. The safer Loop now
    # stops the uncertain write before requesting any automatic successor.
    candidate = deepcopy(plan)
    mutation(candidate)
    with pytest.raises(ValueError, match=error):
        AgentLoop._validate_replan(plan, candidate, ReplanDecision(
            strategy="adjust_params", reason="fixture candidate", original_step_index=1))


def test_skipped_required_step_is_not_a_completed_job(monkeypatch):
    plan = _plan()
    for step in plan.steps:
        step.status = "skipped"
    calls = []
    result = _loop(plan, lambda s, c: calls.append(s), monkeypatch).run(plan.goal)

    assert calls == []
    assert result.status == "failed"
    assert result.result is None


def test_switch_tool_only_changes_failed_step_and_preserves_risk_and_history():
    plan = _plan()
    plan.steps[0].tool = "db_query"
    plan.steps[0].status = "completed"
    plan.steps[0].result = {"success": True, "output": "actual source material"}
    plan.steps[1].tool = "ai_analysis"
    plan.steps[1].status = "failed"
    before = deepcopy(plan.to_dict())

    replacement = Replanner().replan(plan.goal, plan, ReplanDecision(
        strategy="switch_tool", reason="tool unavailable", original_step_index=1,
    ))

    assert plan.to_dict() == before
    assert replacement.steps[0].to_dict() == before["steps"][0]
    assert replacement.steps[1].step_id == "write-report"
    assert replacement.steps[1].tool == "rule_based_analysis"
    assert replacement.steps[1].risk_level == "high"
    assert replacement.steps[1].status == "pending"


def test_split_recovery_preserves_original_job_and_completed_source(monkeypatch):
    plan = _plan()
    plan.steps[1].risk_level = "low"  # Analytical work, not a write or external effect.
    calls = []

    def execute(step, context):
        calls.append(step.tool)
        if step.tool == "reporter" and calls.count("reporter") == 1:
            return {"success": False, "error": "timeout"}
        return {"success": True, "output": "actual " + step.expected_output}

    result = _loop(plan, execute, monkeypatch, report_effect="ANALYZE").run(plan.goal)

    assert result.status == "reconciliation_required", result.error
    assert result.error == "REPLAN_FORMED_CALL_CHANGED"
    assert result.plan["goal"] == plan.goal
    assert calls == ["reader", "reporter"]
    original = next(step for step in result.plan["steps"] if step["step_id"] == "write-report")
    assert original["expected_output"] == "report" and original["risk_level"] == "low"
    assert result.result is None
    assert result.plan["steps"][0]["result"]["output"] == "actual source material"


def test_split_cannot_repeat_a_write_as_prepare_and_execute(monkeypatch):
    plan = _plan()
    calls = []

    def execute(step, context):
        calls.append(step.tool)
        if step.tool == "reporter":
            return {"success": False, "error": "timeout after uncertain write outcome"}
        return {"success": True, "output": "actual source material"}

    result = _loop(plan, execute, monkeypatch).run(plan.goal)

    assert result.status == "reconciliation_required"
    assert "Consequential tool outcome" in result.error
    assert calls == ["reader", "reporter"]
    assert result.plan["steps"][1]["risk_level"] == "high"
    with pytest.raises(ValueError, match="REPLAN_SIDE_EFFECT_SPLIT_REQUIRES_TOOL_CONTRACT"):
        AgentLoop._validate_replan(plan, deepcopy(plan), ReplanDecision(
            strategy="split_step", reason="fixture candidate", original_step_index=1))
