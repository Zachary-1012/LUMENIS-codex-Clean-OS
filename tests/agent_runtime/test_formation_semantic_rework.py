"""Reproduce the two M source-review counterexamples before the repair."""
import hashlib
import json

import pytest

from agent_runtime.loop import AgentLoop
from agent_runtime.planner import PlanStep
from lumenis.shared.evaluation.trajectory import OutcomeAssertion, TrajectoryEvaluator
from agent_capability.formation import BoundToolExecutor, FormationError


def test_literal_slice_handlers_have_typed_identity_and_changed_bounds_never_match():
    from agent_capability.formation import implementation_identity, _code_value
    handlers = []
    for bound in (160, 161):
        namespace = {'__name__': 'literal_slice_identity_fixture'}
        exec(compile('def trim(value):\n    return value[:' + str(bound) + ']\n',
                     '<literal-slice-identity>', 'exec'), namespace)
        handlers.append(namespace['trim'])
    assert len(handlers[0]('x' * 200)) == 160
    assert implementation_identity(handlers[0]) != implementation_identity(handlers[1])
    assert implementation_identity(handlers[0]) == implementation_identity(handlers[0])
    with pytest.raises(FormationError, match='TOOL_IMPLEMENTATION_IDENTITY_UNAVAILABLE'):
        _code_value(slice(object(), 3, None))


def generated_requirement():
    return {"schema": "canonical-committed-artifact:v1", "domain_id": "bmp",
            "scope": {"global_scope": True, "subject_id": None, "brand_focus_id": None},
            "output_type": "podcast_episode", "parent_version_id": "episode-v1",
            "requirements": {"language": "zh-CN", "source_evidence_refs": ["evidence://original"]}}


def test_new_output_contract_can_freeze_intent_before_output_bytes_exist(tmp_path):
    result_path = tmp_path / "new-episode.json"
    assert not result_path.exists()
    requirement = OutcomeAssertion("episode", "artifact", "task-output://episode",
                                   expected_value=generated_requirement())
    evaluator = TrajectoryEvaluator(outcome_contract_func=lambda task: [requirement],
                                   outcome_resolver=lambda row, task: {"state": "NOT_AVAILABLE"})
    assert evaluator.form_outcome_contract("task-new")
    assert not result_path.exists()


def test_incompatible_planned_write_cannot_replace_trusted_export_permission():
    step = PlanStep(tool="actual_export", params={"action_type": "WRITE"})
    step.formation = {"effect": "EXPORT"}
    # Either reject the disagreement or keep DATA_EXPORT obligations.
    try:
        action = AgentLoop._security_action(step)
    except Exception as exc:
        assert str(exc) == "TOOL_EFFECT_DECLARATION_CONFLICT"
    else:
        assert action.value == "EXPORT"


class UnitCommittedArtifactOwner:
    """Disk-backed unit owner seam; not production Artifact/Task acceptance.

    The independent reader reloads a stored committed receipt and output bytes;
    handler-returned success/receipt fields cannot enter either read path.
    """
    def __init__(self, folder):
        self.folder = folder
        self.output = folder / "new-episode.json"
        self.receipt = folder / "committed-receipt.json"
        self.requirement = OutcomeAssertion("episode", "artifact", "task-output://episode",
                                            expected_value=generated_requirement())
        self.task_id = None
        self.contract = None
        self.read_count = 0

    def requirements(self, task_id):
        self.task_id = task_id
        return [self.requirement]

    def commit(self, task_id, contract):
        assert not self.output.exists()
        payload = {**self.requirement.expected_value["requirements"], "script": "A new saved episode result"}
        self.output.write_text(json.dumps(payload), encoding="utf-8")
        body = self.output.read_bytes()
        spec = self.requirement.expected_value
        receipt = {"schema": "canonical-committed-output-receipt:v1", "state": "COMMITTED",
                   "task_id": task_id, "assertion_id": self.requirement.assertion_id,
                   "contract_sha256": contract, "domain_id": spec["domain_id"], "scope": spec["scope"],
                   "output_type": spec["output_type"], "parent_version_id": spec["parent_version_id"],
                   "artifact_ref": "artifact://episode-created", "version_id": "episode-v2",
                   "sha256": hashlib.sha256(body).hexdigest(), "byte_length": len(body),
                   "constraint_observations": {key: payload[key] for key in spec["requirements"]}}
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")

    def read_commit(self, row, task_id, contract):
        if not self.receipt.exists():
            return {"state": "NOT_AVAILABLE"}
        return json.loads(self.receipt.read_bytes())

    def reopen(self, row, task_id, *, committed_receipt):
        self.read_count += 1
        body = self.output.read_bytes()
        return {"state": "AVAILABLE", "reference": row.reference, "kind": row.kind,
                **{key: committed_receipt[key] for key in
                   ("artifact_ref", "version_id", "task_id", "domain_id", "scope", "parent_version_id")},
                "sha256": hashlib.sha256(body).hexdigest(), "byte_length": len(body)}

    def evaluator(self):
        return TrajectoryEvaluator(outcome_contract_func=self.requirements,
            outcome_resolver=self.reopen, committed_artifact_resolver=self.read_commit)


def test_new_result_is_independently_committed_then_reopened_and_hash_bound(tmp_path):
    owner = UnitCommittedArtifactOwner(tmp_path)
    evaluator = owner.evaluator()
    bound = evaluator.form_outcome_contract("task-new")
    assert not owner.output.exists()
    assert evaluator.verify_outcome("task-new", bound)["state"] == "NOT_VERIFIED"
    owner.commit("task-new", bound)
    result = evaluator.verify_outcome("task-new", bound)
    assert result["state"] == "VERIFIED"
    assert owner.read_count == 1
    retained = result["committed_output_bindings"]
    reopened = owner.evaluator().verify_outcome("task-new", bound,
        expected_output_receipts=retained, require_bound_receipts=True)
    assert reopened["state"] == "VERIFIED"
    owner.output.write_bytes(b"tampered after committed generation")
    assert evaluator.verify_outcome("task-new", bound,
        expected_output_receipts=retained, require_bound_receipts=True)["state"] == "FAILED"


@pytest.mark.parametrize("field,value", [
    ("task_id", "foreign-task"), ("scope", {"global_scope": False, "brand_focus_id": "foreign"}),
    ("domain_id", "cth"), ("parent_version_id", "wrong-parent"),
    ("constraint_observations", {"language": "en"}), ("byte_length", True),
    ("contract_sha256", "0" * 64),
])
def test_foreign_or_malformed_committed_result_cannot_fill_frozen_intent(tmp_path, field, value):
    owner = UnitCommittedArtifactOwner(tmp_path)
    evaluator = owner.evaluator()
    bound = evaluator.form_outcome_contract("task-new")
    owner.commit("task-new", bound)
    receipt = json.loads(owner.receipt.read_bytes())
    receipt[field] = value
    owner.receipt.write_text(json.dumps(receipt), encoding="utf-8")
    result = evaluator.verify_outcome("task-new", bound)
    assert result["state"] == "FAILED"
    assert result["committed_output_bindings"] == {}
    assert owner.read_count == 0


def test_changed_requirement_or_latest_commit_cannot_rebind_a_completed_job(tmp_path):
    owner = UnitCommittedArtifactOwner(tmp_path)
    evaluator = owner.evaluator()
    bound = evaluator.form_outcome_contract("task-new")
    owner.commit("task-new", bound)
    bindings = evaluator.verify_outcome("task-new", bound)["committed_output_bindings"]
    receipt = json.loads(owner.receipt.read_bytes())
    receipt["version_id"] = "episode-v3"
    owner.receipt.write_text(json.dumps(receipt), encoding="utf-8")
    failed = evaluator.verify_outcome("task-new", bound,
        expected_output_receipts=bindings, require_bound_receipts=True)
    assert failed["state"] == "FAILED"
    assert failed["checks"][0]["reason"] == "OUTCOME_COMMIT_BINDING_CHANGED"
    assert evaluator.verify_outcome("task-new", bound, require_bound_receipts=True)["state"] == "FAILED"
    owner.requirement.expected_value["requirements"]["language"] = "ko"
    assert evaluator.verify_outcome("task-new", bound)["reason"] == "OUTCOME_CONTRACT_CHANGED"


def test_model_success_or_its_receipt_does_not_issue_a_canonical_commit(tmp_path):
    from tests.agent_runtime.test_formation_dispatch import Gate, StaticPlanner, plan, state
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    owner = UnitCommittedArtifactOwner(tmp_path)
    p = plan()
    loop = AgentLoop(planner=StaticPlanner(p), evaluator=owner.evaluator(),
        tool_binding=BoundToolExecutor(lambda step, context: {"success": True,
            "receipt": {"state": "COMMITTED", "sha256": "f" * 64}},
            origin="unit-owner", resource_uri="skill://unit/create", identity_provider=state),
        permission_gate=Gate(), durable_adapter=DurableExecutionAdapter(enabled=False))
    result = loop.run("create an episode")
    assert result.status == "blocked"
    assert not owner.receipt.exists()
    assert p.outcome_receipt_bindings == {}


def test_export_conflict_stops_actual_handler_before_db_write_only_admission():
    from tests.agent_runtime.test_formation_dispatch import Gate, StaticPlanner, plan, state
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    calls = []
    p = plan()
    p.steps[0].params["action_type"] = "WRITE"
    gate = Gate()
    executor = BoundToolExecutor(lambda step, context: calls.append("export") or {"success": True},
        origin="unit-owner", resource_uri="skill://unit/export", identity_provider=state, action_type="EXPORT")
    loop = AgentLoop(planner=StaticPlanner(p), tool_binding=executor, permission_gate=gate,
                     durable_adapter=DurableExecutionAdapter(enabled=False))
    result = loop.run("export data")
    assert result.status == "reconciliation_required"
    assert result.error == "TOOL_EFFECT_DECLARATION_CONFLICT"
    assert gate.calls == 0  # DB_WRITE admission cannot substitute for DATA_EXPORT.
    assert calls == []


@pytest.mark.parametrize("trusted", ["EXPORT", "WRITE", "COMMIT", "PUSH", "DEPLOY"])
def test_read_label_keeps_the_exact_trusted_effect(trusted):
    step = PlanStep(params={"action_type": "READ"}, formation={"effect": trusted})
    assert AgentLoop._security_action(step).value == trusted


def test_export_uses_data_export_even_when_db_write_is_allowed():
    from lumenis.system.security import OperationType
    action = AgentLoop._security_action(PlanStep(params={"action_type": "READ"}, formation={"effect": "EXPORT"}))
    assert AgentLoop._security_operation(action) == OperationType.DATA_EXPORT
    assert AgentLoop._security_operation(action) != OperationType.DB_WRITE


def test_running_export_conflict_on_resume_reconciles_without_handler(resume_env):
    from tests.agent_runtime.test_loop_execution_resume import _grant, _plan, _persist_checkpoint, _loop, _context
    _grant(resume_env["path"], action="write")
    p = _plan(interrupted="running", second_action="export report")
    p.steps[1].params["action_type"] = "WRITE"
    p.steps[1].formation = {"effect": "EXPORT"}
    task_id = _persist_checkpoint(resume_env, p, state="executing", index=1, form_pending=False)
    calls = []
    result = _loop(resume_env, tool_calls=calls).resume(task_id, context=_context())
    assert result.status == "reconciliation_required"
    assert result.error == "TOOL_EFFECT_DECLARATION_CONFLICT"
    assert calls == []


def test_replan_cannot_replace_frozen_output_requirement_or_committed_binding():
    from agent_runtime.planner import Plan
    from agent_runtime.replanner import ReplanDecision
    from copy import deepcopy
    p = Plan(goal="create episode", steps=[PlanStep(step_id="stable", action="create episode")],
             outcome_contract_sha256="1" * 64,
             outcome_receipt_bindings={"episode": {"version_id": "episode-v2"}})
    decision = ReplanDecision(strategy="retry_step")
    changed = deepcopy(p)
    changed.outcome_contract_sha256 = "2" * 64
    with pytest.raises(FormationError, match="REPLAN_OUTCOME_CONTRACT_CHANGED"):
        AgentLoop._validate_replan(p, changed, decision)
    changed = deepcopy(p)
    changed.outcome_receipt_bindings["episode"]["version_id"] = "episode-v3"
    with pytest.raises(FormationError, match="REPLAN_OUTCOME_RECEIPT_CHANGED"):
        AgentLoop._validate_replan(p, changed, decision)


def test_new_output_binding_persists_in_existing_task_checkpoint_and_reopen(durable, monkeypatch, tmp_path):
    from tests.agent_runtime.test_loop_checkpoint_contract import StaticPlanner
    from tests.agent_runtime.formation_support import trusted_test_executor
    from agent_runtime.planner import Plan
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    from ai_task_engine import TaskEngine
    owner = UnitCommittedArtifactOwner(tmp_path)
    evaluator = owner.evaluator()
    engine, gate, adapter = durable
    p = Plan(goal="create a new episode", steps=[PlanStep(tool="create-episode", action="create episode")])

    def create(step, context):
        owner.commit(owner.task_id, evaluator.form_outcome_contract(owner.task_id))
        return {"success": True, "output": "created"}

    loop = AgentLoop(planner=StaticPlanner(p), evaluator=evaluator,
        tool_binding=trusted_test_executor(create), durable_adapter=adapter)
    monkeypatch.setattr(loop, "_check_security", lambda step, context: {"allowed": True})
    result = loop.run(p.goal, context={"domain_id": "bmp"})
    assert result.status == "completed"
    restored = DurableExecutionAdapter(task_engine=TaskEngine(), permission_gate=gate).recover(result.task_id)
    snapshot = restored["last_checkpoint"]["plan_snapshot"]
    assert snapshot["outcome_receipt_bindings"] == p.outcome_receipt_bindings
    assert snapshot["outcome_receipt_bindings"]["episode"]["version_id"] == "episode-v2"
    saved = AgentLoop._restore_checkpoint_plan(snapshot)
    reopened = evaluator.verify_outcome(result.task_id, saved.outcome_contract_sha256,
        expected_output_receipts=saved.outcome_receipt_bindings, require_bound_receipts=True)
    assert reopened["state"] == "VERIFIED"
    saved.outcome_receipt_bindings = {}
    assert evaluator.verify_outcome(result.task_id, saved.outcome_contract_sha256,
        expected_output_receipts=saved.outcome_receipt_bindings, require_bound_receipts=True)["state"] == "FAILED"


# Reuse the existing isolated TaskEngine fixture; no new store/schema owner.
from tests.agent_runtime.test_loop_checkpoint_contract import durable
from tests.agent_runtime.test_loop_execution_resume import resume_env
