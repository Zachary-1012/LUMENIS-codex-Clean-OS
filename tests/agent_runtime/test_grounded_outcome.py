"""Canonical-owner observations are separate from claimed step completion."""
from dataclasses import replace
import hashlib

import pytest

from lumenis.shared.evaluation.trajectory import OutcomeAssertion, TrajectoryEvaluator, TrajectoryMetrics


def evaluator_for(path, extra=None):
    pin = hashlib.sha256(path.read_bytes()).hexdigest()
    requirements = [OutcomeAssertion("artifact", "artifact", "artifact://unit-original", pin)]
    if extra:
        requirements.append(extra)

    def resolve(row, task):
        if row.kind == "artifact":
            return {"reference": row.reference, "kind": row.kind, "state": "AVAILABLE",
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        return {"reference": row.reference, "kind": row.kind, "state": "AVAILABLE", "value": False}

    return TrajectoryEvaluator(outcome_contract_func=lambda task: requirements,
                               outcome_resolver=resolve), requirements


def test_success_flag_alone_never_verifies_a_user_result():
    result = TrajectoryEvaluator().evaluate(TrajectoryMetrics(goal_achieved=True, total_steps=1, completed_steps=1))
    assert result.goal_completion.score == 1  # retained operational compatibility
    assert result.score_scope == "OPERATIONAL_TRAJECTORY_ONLY"
    assert result.outcome_verification["state"] == "NOT_VERIFIED"
    assert result.outcome_verification["verified_goal_achieved"] is False


def test_saved_artifact_is_reopened_and_rehashed_instead_of_trusting_its_success_flag(tmp_path):
    artifact = tmp_path / "original.txt"
    artifact.write_bytes(b"original source content")
    evaluator, _requirements = evaluator_for(artifact)
    bound = evaluator.form_outcome_contract("task")
    assert evaluator.verify_outcome("task", bound)["state"] == "VERIFIED"
    artifact.write_bytes(b"changed after task execution")
    failed = evaluator.evaluate(TrajectoryMetrics(goal_achieved=True, total_steps=1, completed_steps=1),
                                task_id="task", expected_contract_sha256=bound)
    assert failed.outcome_verification["state"] == "FAILED"
    assert failed.outcome_verification["user_verified"] is False


@pytest.mark.parametrize("kind", ["effect", "environment", "user_constraint"])
def test_actual_failed_constraints_cannot_be_overridden_by_complete_metrics(tmp_path, kind):
    artifact = tmp_path / "original.txt"
    artifact.write_bytes(b"original")
    evaluator, _ = evaluator_for(artifact, OutcomeAssertion("constraint", kind, "owner://requirement", expected_value=True))
    bound = evaluator.form_outcome_contract("task")
    result = evaluator.evaluate(TrajectoryMetrics(goal_achieved=True), task_id="task", expected_contract_sha256=bound)
    assert result.outcome_verification["state"] == "FAILED"


def test_latest_requirement_cannot_refill_or_rebind_an_old_task(tmp_path):
    artifact = tmp_path / "original.txt"
    artifact.write_bytes(b"original")
    evaluator, requirements = evaluator_for(artifact)
    original = evaluator.form_outcome_contract("task")
    requirements[0] = replace(requirements[0], reference="artifact://new-owner")
    assert evaluator.verify_outcome("task", original)["reason"] == "OUTCOME_CONTRACT_CHANGED"
    assert evaluator.verify_outcome("task")["reason"] == "OUTCOME_CONTRACT_MISSING"


def test_missing_or_false_values_are_not_zero(tmp_path):
    artifact = tmp_path / "original.txt"
    artifact.write_bytes(b"original")
    evaluator, _ = evaluator_for(artifact, OutcomeAssertion("effect", "effect", "effect://original", expected_value=0))
    bound = evaluator.form_outcome_contract("task")
    assert evaluator.verify_outcome("task", bound)["state"] == "FAILED"  # observed False != expected 0
    original = evaluator._outcome_resolver
    evaluator._outcome_resolver = lambda row, task: (original(row, task) if row.kind == "artifact" else
        {"reference": row.reference, "kind": row.kind, "state": "AVAILABLE"})
    assert evaluator.verify_outcome("task", bound)["state"] == "FAILED"


def test_actual_loop_cannot_disable_configured_outcome_verification(tmp_path):
    from tests.agent_runtime.test_formation_dispatch import Gate, StaticPlanner, plan, tool
    from agent_capability.router import CapabilityRouter
    from agent_runtime.loop import AgentLoop, AgentConfig
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    artifact = tmp_path / "original.txt"
    artifact.write_bytes(b"original")
    evaluator, _ = evaluator_for(artifact)
    router = CapabilityRouter(enabled=True)
    router.register_tool(tool(lambda: {"success": True, "output": "claimed finished"}))
    gate = Gate(lambda: artifact.write_bytes(b"changed artifact"))
    p = plan()
    loop = AgentLoop(config=AgentConfig(enable_evaluation=False), planner=StaticPlanner(p),
                     evaluator=evaluator, tool_binding=router, permission_gate=gate,
                     durable_adapter=DurableExecutionAdapter(enabled=False))
    result = loop.run(p.goal)
    assert result.status == "blocked"
    assert result.result is None
    assert result.evaluation["outcome_verification"]["state"] == "FAILED"


def test_configured_evaluator_failure_is_not_silently_a_completed_job(tmp_path):
    from tests.agent_runtime.test_formation_dispatch import Gate, StaticPlanner, plan, tool
    from agent_capability.router import CapabilityRouter
    from agent_runtime.loop import AgentLoop
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    artifact = tmp_path / "original.txt"
    artifact.write_bytes(b"original")
    evaluator, _ = evaluator_for(artifact)
    evaluator.evaluate = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("private diagnostic"))
    router = CapabilityRouter(enabled=True)
    router.register_tool(tool(lambda: {"success": True, "output": "claimed finished"}))
    p = plan()
    loop = AgentLoop(planner=StaticPlanner(p), evaluator=evaluator, tool_binding=router, permission_gate=Gate(),
                     durable_adapter=DurableExecutionAdapter(enabled=False))
    result = loop.run(p.goal)
    assert result.status == "blocked"
    assert result.error == "OUTCOME_OWNER_UNAVAILABLE"
    assert "private" not in str(result.evaluation)
