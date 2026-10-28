"""Domain decision/recovery integration; synthetic inputs are not user acceptance."""
import copy
import json
import sqlite3

import pytest

from tests.test_saved_document_workflow import workspace
from tests.test_source_brief_job import job_db
from canonical_data import CanonicalRecord, persist_canonical
from lumenis.shared.evidence import store
from lumenis.shared.reporting.source_brief_job import create_source_brief_job
from api_dual_domain import BusinessDecisionWorkflow
from tests.test_source_brief_job_routes import client as report_client, GLOBAL, URL
from tests.test_cth_case_routes import case_client

# Pytest discovers these imported owner fixtures by module name.
__all__ = ["workspace", "job_db", "report_client", "case_client"]


@pytest.fixture(params=["CTH", "ZBMP"])
def work(workspace, request, monkeypatch):
    from lumenis.shared.reporting.business_brief import ai_core
    from lumenis.shared.database.business_schema import apply_business_schema
    from lumenis.shared.evaluation.recorder import init_db
    from lumenis.system.security import permission
    import subject_registry
    monkeypatch.setattr(ai_core, "local_structured_chat", lambda *a, **k: pytest.fail("retired provider invoked"))
    product = request.param
    domain = "cth" if product == "CTH" else "zbmp"
    entity, _ = subject_registry.add_subject({"domain_id": "CTH" if product == "CTH" else "BMP",
        "subject_type": "company" if product == "CTH" else "brand",
        "name_en": "Isolated focus", "name_zh": "隔离业务来源"})
    media_scope = {"domain_id": domain, "global_scope": False,
                  "subject_id": entity["subject_id"] if product == "CTH" else None,
                  "brand_focus_id": entity["brand_focus_id"] if product == "ZBMP" else None}
    args = {"product_id": product, "global_scope": False, "entity_label": "Isolated focus",
            "subject_id": media_scope["subject_id"], "brand_focus_id": media_scope["brand_focus_id"]}
    db = workspace["root"] / "isolated.sqlite3"
    with workspace["repo"].transaction() as con:
        apply_business_schema(con)
    init_db()
    path = workspace["root"] / "decision-source.txt"
    path.write_text("The source reports zero participants.", encoding="utf-8")
    provenance = {"source_url": "https://example.org/isolated-test", "published_at": None,
                  "captured_at": "2026-10-02T00:00:00Z", "rights": "public-reference-only",
                  "title": "Attributed test statement"}
    import_args = {"actor": workspace["actor"], "scope": media_scope, "provenance": provenance}
    resource = workspace["documents"].document_import_resource(str(path), **import_args)
    workspace["gate"].grant_approval(permission.OperationType.DATA_IMPORT.value,
        resource=resource, granted_by="isolated-test")
    imported = workspace["documents"].import_document(str(path), **import_args)
    source_id = imported["source_id"]
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row
        # Preserve capture-role test annotation independently of the real
        # Importer receipt and retained source bytes used by SourceUse.
        ref = store.record_evidence(connection=con, source="isolated_test", project="LUMENIS",
            product=product, domain_id=domain, subject_id=args["subject_id"], brand_focus_id=args["brand_focus_id"],
            global_scope=False, feature_id="TEST_SOURCE", result="PASS", status="verified",
            inputs={"source_ids": [source_id], "source_role": "OFFICIAL_BRAND_SELF_DESCRIPTION" if product == "ZBMP" else "VENUE_OPERATOR_DISCLOSURE"},
            outputs={"test": True})
        con.execute("UPDATE canonical_data SET scope_evidence_ref=?,raw_ref=? WHERE source_id=?",
            (str(ref), json.dumps({"content_evidence_ref": "app_evidence_records:" + str(imported["evidence_id"])}), source_id))
        con.commit()
        report = create_source_brief_job(con, **args, actor_id=workspace["actor"].principal_ref,
            permission_audit_ref="audit:test", trace_id="trace-test-decision", job_id="job-decision-test")
    scope = report["source_brief"]["scope"]
    def authorize(operation):
        return {"actor_id": workspace["actor"].principal_ref, "scope": scope, "operation": operation,
                "permission_audit_ref": "audit:isolated-test", "operation_audit_ref": "effect:isolated-test"}
    options = [{"option_id": name, "proposal": "Proposed reversible research activity " + name,
                "rationale": "One source does not establish consumer demand.", "source_ids": [source_id],
                "assumptions": ["Participants might consent; not confirmed."],
                "unknowns": ["Commercial material rights and actual demand are unknown."],
                "check": "Record consenting participants' unaided reasons; stop if inputs are insufficient."}
               for name in ["A", "B"]]
    service = BusinessDecisionWorkflow(source_actor=workspace["actor"])
    inputs = {"actor_ref": workspace["actor"].principal_ref, "scope": scope, "submission_id": "prepare-request-01",
              "source_job_id": report["job_id"], "kind": "venue_operations" if product == "CTH" else "brand_market",
              "question": "Which bounded option should the operator investigate next?",
              "options": options, "authorize": authorize}
    return service, inputs, db


def step(service, inputs, current, operation, payload, submission_id):
    return service.advance(current["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"],
                           authorize=inputs["authorize"], expected_revision=current["revision"],
                           submission_id=submission_id, operation=operation, payload=payload)


def choose(service, inputs, current):
    return step(service, inputs, current, "choose", {"option_id": "B", "reason": "Explore the smaller reversible option.",
                "owner": "Consenting operator", "review_at": "2026-10-05T12:00:00+08:00"}, "choose-request-01")


def _owner_read_contract(inputs, *, version=1, parent=None, contract_version="1"):
    """Controlled reader double with W6's observed schema, not a real Artifact.

    Real owner HTTP/Word receipts remain W6's separate frozen evidence. These
    tests exercise domain persistence/fences and never claim runtime acceptance.
    """
    from types import SimpleNamespace
    scope = BusinessDecisionWorkflow._action_scope(inputs["scope"])
    contract_paths = {
        "1": ["manuscript", "shot_plan", "truth_state"],
        "2": ["manuscript", "input_manifest", "truth_state"],
        "3": ["manuscript", "upstream_binding", "truth_state"],
        "4": ["manuscript", "truth_state"],
        "5": ["manuscript", "audiovisual_plan", "truth_state"],
    }
    contract = {"id": "lumenis.internal-pitch", "version": contract_version,
                "required_payload_paths": contract_paths[contract_version]}
    receipt = {"owner": "Shared ContentCreation/TaskEngine/SavedWork", "task_id": f"task-contract-{version}",
               "scope": scope, "action_kind": "INTERNAL_TEXT_CREATION" if version == 1 else "INTERNAL_TEXT_REVISION",
               "execution_state": "ARTIFACT_COMMITTED",
               "business_outcome": "NOT_OBSERVED", "external_effect": "NOT_PERFORMED",
               "artifact_id": f"ART-contract-{version}", "work_id": "WORK-contract", "version": version,
               "sha256": str(version) * 64, "size_bytes": 100,
               "parent_artifact_id": parent["artifact_id"] if parent else None,
               "parent_sha256": parent["sha256"] if parent else None,
               "output": {"artifact_id": f"ART-word-contract-{version}", "name": "document.docx",
                          "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                          "sha256": "a" * 64, "size_bytes": 200}}
    committed = {"schema": "lumenis.committed-saved-work/v1", "task_id": receipt["task_id"],
                 "scope": scope, "contract": contract, "work_id": receipt["work_id"], "version": version,
                 "ref": receipt["artifact_id"], "sha256": receipt["sha256"], "size_bytes": receipt["size_bytes"],
                 "parent": {"ref": receipt["parent_artifact_id"], "sha256": receipt["parent_sha256"]},
                 "constraint_observations": {"committed_bytes_match": True, "parent_chain_verified": True}}
    doc = {"task_id": receipt["task_id"], "work_id": receipt["work_id"], "version": version,
           "parent_artifact_id": receipt["parent_artifact_id"], "parent_sha256": receipt["parent_sha256"],
           "context": {**scope, "principal_ref": inputs["actor_ref"]}, "contract": contract,
           "attachments": [receipt["output"]]}
    observation = {"task_id": receipt["task_id"], "scope": scope, "state": "succeeded", "error": None,
                   "action_receipt": receipt, "work": {"receipt": committed, "document": doc,
                   "artifact": {"artifact_id": receipt["artifact_id"], "sha256": receipt["sha256"], "size_bytes": 100}}}
    actor = SimpleNamespace(principal_ref=inputs["actor_ref"])
    calls = []
    def reader(task_id, *, actor, scope):
        assert actor.principal_ref == inputs["actor_ref"]
        assert scope == BusinessDecisionWorkflow._action_scope(inputs["scope"])
        assert task_id == observation["task_id"]
        calls.append(task_id)
        return copy.deepcopy(observation)
    return observation, actor, reader, calls


def _record_action(service, inputs, current, task_id="task-contract-1", submission_id="action-contract-01"):
    return step(service, inputs, current, "action", {"option_id": "B", "task_id": task_id}, submission_id)


@pytest.mark.parametrize("contract_version", ["1", "2"])
def test_action_consumer_v2_creation_revision_unknown_recovery_and_v1_history(work, contract_version):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    with sqlite3.connect(db) as con:
        historical = con.execute("SELECT * FROM app_evidence_records WHERE feature_id=? ORDER BY id", (service.FEATURE,)).fetchall()
    first, actor, _, _ = _owner_read_contract(inputs, contract_version=contract_version)
    second, _, _, _ = _owner_read_contract(inputs, version=2, parent=first["action_receipt"], contract_version=contract_version)
    observations = {o["task_id"]: o for o in (first, second)}
    calls = []
    def reader(task_id, *, actor, scope):
        assert actor.principal_ref == inputs["actor_ref"]
        assert scope == BusinessDecisionWorkflow._action_scope(inputs["scope"])
        calls.append(task_id)
        return copy.deepcopy(observations[task_id])
    bound = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    executed = _record_action(bound, inputs, selected)
    # Lost domain ACK uses the same immutable owner receipt; no new Evidence.
    assert _record_action(bound, inputs, selected) == executed
    revised = _record_action(bound, inputs, executed, second["task_id"], "consumer-v2-revision")
    assert revised["action"]["receipt"] == second["action_receipt"]
    interrupted = step(bound, inputs, revised, "interrupt", {"reason": "Operator review interrupted."}, "consumer-v2-interrupt")
    resumed = step(bound, inputs, interrupted, "resume", {}, "consumer-v2-resume")
    assert resumed["state"] == "ACTION_RECORDED" and resumed["action"] == revised["action"]
    result = step(bound, inputs, resumed, "outcome_unknown", {"limits": "Editable internal draft committed; no campaign or consumer effects observed."}, "consumer-v2-outcome")
    assert result["action_state"] == "EXECUTED" and result["business_outcome"] == "UNKNOWN"
    assert result["evaluation"]["business_usefulness"] == "UNKNOWN"
    assert result["owned_analysis"]["state"] == "UNAVAILABLE"
    fresh = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    assert fresh.reopen(result["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"]) == result
    before = _saved_work_counts(db)
    with pytest.raises(RuntimeError, match="TERMINAL"):
        step(fresh, inputs, result, "interrupt", {"reason": "Cannot reopen terminal review as pending work."}, "consumer-v2-terminal")
    assert _saved_work_counts(db) == before
    assert result["return_context"]["global"] is True and result["scope"] == inputs["scope"]
    assert set(calls) == set(observations)
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT * FROM app_evidence_records WHERE feature_id=? ORDER BY id LIMIT 2", (service.FEATURE,)).fetchall() == historical
        metric, status, raw = con.execute("SELECT metric_value,status,metadata FROM evaluation_records WHERE evaluation_id=?", (result["evaluation"]["evaluation_id"],)).fetchone()
        assert metric is None and status == "unknown"
        assert json.loads(raw)["action"]["receipt"] == second["action_receipt"]
    # The archived exact scope and contract remain separate from active Focus.
    assert result["scope"] == inputs["scope"]
    assert first["work"]["document"]["contract"]["version"] == contract_version


def test_action_consumer_v2_cancel_reopen_retains_committed_creation(work):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    observed, actor, reader, _ = _owner_read_contract(inputs, contract_version="2")
    bound = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    executed = _record_action(bound, inputs, selected)
    cancelled = step(bound, inputs, executed, "cancel", {"reason": "Stop pending work; no owner cancellation requested."}, "consumer-v2-cancel")
    assert cancelled["state"] == "CANCELLED" and cancelled["action_state"] == "EXECUTED"
    assert cancelled["action"]["receipt"] == observed["action_receipt"]
    before = _saved_work_counts(db)
    fresh = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    assert fresh.reopen(cancelled["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"]) == cancelled
    unavailable = BusinessDecisionWorkflow().reopen(cancelled["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"])
    assert unavailable["action_state"] == "EXECUTED" and unavailable["action_read"]["state"] == "UNAVAILABLE"
    assert _saved_work_counts(db) == before


def test_action_consumer_accepts_authored_manuscript_v4_creation_revision_and_reopen(work):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    first, actor, _, _ = _owner_read_contract(inputs, contract_version="4")
    second, _, _, _ = _owner_read_contract(
        inputs, version=2, parent=first["action_receipt"], contract_version="4")
    observations = {item["task_id"]: item for item in (first, second)}

    def reader(task_id, *, actor, scope):
        assert actor.principal_ref == inputs["actor_ref"]
        assert scope == BusinessDecisionWorkflow._action_scope(inputs["scope"])
        return copy.deepcopy(observations[task_id])

    bound = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    created = _record_action(bound, inputs, selected, first["task_id"], "authored-v4-create")
    revised = _record_action(bound, inputs, created, second["task_id"], "authored-v4-revise")
    assert revised["action"]["receipt"] == second["action_receipt"]
    assert second["work"]["receipt"]["contract"] == {
        "id": "lumenis.internal-pitch", "version": "4",
        "required_payload_paths": ["manuscript", "truth_state"]}
    before = _saved_work_counts(db)
    fresh = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    assert fresh.reopen(revised["work_id"], actor_ref=inputs["actor_ref"],
                        scope=inputs["scope"], authorize=inputs["authorize"]) == revised
    assert _saved_work_counts(db) == before


@pytest.mark.parametrize("fault", ["future_version", "hybrid_paths", "v1_paths", "document_mismatch", "extra_contract_key", "missing_contract"])
def test_action_consumer_v2_rejects_unknown_or_relabelled_contract_without_write(work, fault):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    observed, actor, reader, _ = _owner_read_contract(inputs, contract_version="2")
    contract = observed["work"]["receipt"]["contract"]
    if fault == "future_version": contract["version"] = "6"
    elif fault == "hybrid_paths": contract["required_payload_paths"].append("shot_plan")
    elif fault == "v1_paths": contract["required_payload_paths"] = ["manuscript", "shot_plan", "truth_state"]
    elif fault == "extra_contract_key": contract["profile"] = "manuscript-only/v2"
    elif fault == "missing_contract": observed["work"]["receipt"].pop("contract")
    else:
        observed["work"]["document"]["contract"] = {"id": "lumenis.internal-pitch", "version": "1", "required_payload_paths": ["manuscript", "shot_plan", "truth_state"]}
    before = _saved_work_counts(db)
    bound = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    with pytest.raises(RuntimeError, match="RECEIPT_INVALID"):
        _record_action(bound, inputs, selected)
    assert _saved_work_counts(db) == before


@pytest.mark.parametrize("boundary", ["final_owner_read", "final_actor", "final_scope", "final_commit"])
def test_action_consumer_v2_fresh_final_boundaries(work, boundary, monkeypatch):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    observed, actor, reader, _ = _owner_read_contract(inputs, contract_version="2")
    rendered = False
    def guarded_reader(task_id, *, actor, scope):
        if rendered and boundary == "final_owner_read":
            raise PermissionError("v2 final owner permission revoked")
        return reader(task_id, actor=actor, scope=scope)
    bound = BusinessDecisionWorkflow(internal_action_reader=guarded_reader, action_actor=actor)
    if boundary == "final_commit":
        calls = 0
        def authorize(operation):
            nonlocal calls
            if operation == "action":
                calls += 1
                if calls == 3: raise PermissionError("v2 final domain commit revoked")
            return inputs["authorize"](operation)
        before = _saved_work_counts(db)
        with pytest.raises(PermissionError, match="v2 final domain commit revoked"):
            bound.advance(selected["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=authorize,
                          expected_revision=selected["revision"], submission_id="consumer-v2-final-commit", operation="action",
                          payload={"option_id": "B", "task_id": observed["task_id"]})
        assert _saved_work_counts(db) == before
        return
    executed = _record_action(bound, inputs, selected)
    render = bound.render_result
    def render_flag(result):
        nonlocal rendered
        out = render(result)
        rendered = True
        return out
    def authorize(operation):
        receipt = copy.deepcopy(inputs["authorize"](operation))
        if rendered:
            if boundary == "final_actor": receipt["actor_id"] = "workspace:foreign"
            elif boundary == "final_scope": receipt["scope"]["entity_label"] = "Foreign focus"
        return receipt
    monkeypatch.setattr(bound, "render_result", render_flag)
    before = _saved_work_counts(db)
    with pytest.raises(PermissionError, match="v2 final owner permission revoked|AUTHORIZATION_MISMATCH"):
        bound.reopen(executed["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=authorize)
    assert _saved_work_counts(db) == before


def test_action_contract_signed_history_unknown_evaluation_and_lost_ack(work, monkeypatch):
    from lumenis.shared.evaluation import recorder
    service, inputs, db = work
    prepared = service.prepare(**inputs)
    selected = choose(service, inputs, prepared)
    with sqlite3.connect(db) as con:
        old = con.execute("SELECT * FROM app_evidence_records WHERE feature_id=? ORDER BY id", (service.FEATURE,)).fetchall()
    observed, actor, reader, calls = _owner_read_contract(inputs)
    service = BusinessDecisionWorkflow(
        internal_action_reader=reader, action_actor=actor, source_actor=service._source_actor,
    )
    executed = _record_action(service, inputs, selected)
    assert executed["action_state"] == "EXECUTED" and executed["business_outcome"] == "NOT_OBSERVED"
    assert executed["action"]["receipt"] == observed["action_receipt"]
    assert executed["action_read"]["state"] == "FRESH_OWNER_VERIFIED"
    assert executed["owned_analysis"]["state"] == "UNAVAILABLE"
    # Simulate lost acknowledgement after Evidence committed but before the
    # recoverable Evaluation write. Replay repairs it without duplicate action.
    original = recorder.record_evaluation
    monkeypatch.setattr(recorder, "record_evaluation", lambda **kw: (_ for _ in ()).throw(OSError("lost evaluation ACK")))
    payload = {"limits": "Internal draft made; no campaign or consumer effects observed."}
    with pytest.raises(OSError, match="lost evaluation ACK"):
        step(service, inputs, executed, "outcome_unknown", payload, "unknown-contract-01")
    recovered = service.reopen(executed["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"])
    assert recovered["evaluation"]["state"] == "PENDING_RECOVERY"
    monkeypatch.setattr(recorder, "record_evaluation", original)
    result = step(service, inputs, executed, "outcome_unknown", payload, "unknown-contract-01")
    assert result["action_state"] == "EXECUTED" and result["business_outcome"] == "UNKNOWN"
    assert result["evaluation"]["state"] == "RECORDED" and result["evaluation"]["business_usefulness"] == "UNKNOWN"
    assert "未观察效果不撤销" in result["usable_result"]["markdown"]
    fresh = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    assert fresh.reopen(result["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"]) == result
    assert calls
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT * FROM app_evidence_records WHERE feature_id=? ORDER BY id LIMIT 2", (service.FEATURE,)).fetchall() == old
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id=?", (service.FEATURE,)).fetchone()[0] == 4
        evaluation = dict(zip(["metric_value", "status", "metadata"], con.execute("SELECT metric_value,status,metadata FROM evaluation_records WHERE evaluation_id=?", (result["evaluation"]["evaluation_id"],)).fetchone()))
        assert evaluation["metric_value"] is None and evaluation["status"] == "unknown"
        assert json.loads(evaluation["metadata"])["action"]["receipt"] == observed["action_receipt"]
    # Clear's return descriptor clears active Focus only; this read never edits
    # archived source/action scope or any stored version.
    before = _saved_work_counts(db)
    assert result["return_context"]["global"] is True and result["return_context"]["subject_id"] is None
    assert result["scope"] == inputs["scope"] and result["action"]["receipt"]["scope"]["global_scope"] is False
    unbound = BusinessDecisionWorkflow().reopen(result["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"])
    assert unbound["action_state"] == "EXECUTED" and unbound["action_read"]["state"] == "UNAVAILABLE"
    assert "尚未重新核验" in unbound["usable_result"]["markdown"] and _saved_work_counts(db) == before


@pytest.mark.parametrize("fault", ["actor", "scope", "task", "artifact", "parent", "output", "not_committed", "effect", "kind"])
def test_action_contract_rejects_foreign_corrupt_or_pending_owner_result(work, fault):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    observed, actor, reader, _ = _owner_read_contract(inputs)
    before = _saved_work_counts(db)
    if fault == "actor": observed["work"]["document"]["context"]["principal_ref"] = "workspace:foreign"
    elif fault == "scope": observed["scope"]["global_scope"] = True
    elif fault == "task": observed["action_receipt"]["task_id"] = "task-foreign"
    elif fault == "artifact": observed["work"]["receipt"]["sha256"] = "b" * 64
    elif fault == "parent": observed["action_receipt"]["parent_artifact_id"] = "ART-foreign"
    elif fault == "output": observed["work"]["document"]["attachments"] = []
    elif fault == "effect": observed["action_receipt"]["external_effect"] = "EXECUTED"
    elif fault == "kind": observed["action_receipt"]["action_kind"] = "INTERNAL_TEXT_REVISION"
    else: observed["state"] = "pending"
    with pytest.raises((PermissionError, RuntimeError)):
        _record_action(BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor), inputs, selected)
    assert _saved_work_counts(db) == before


def test_action_contract_unbound_and_unselected_never_record_execution(work):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    before = _saved_work_counts(db)
    with pytest.raises(RuntimeError, match="OWNER_NOT_BOUND"):
        _record_action(service, inputs, selected)
    assert _saved_work_counts(db) == before
    observed, actor, reader, _ = _owner_read_contract(inputs)
    bound = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    with pytest.raises(RuntimeError, match="SELECTED_OPTION_REQUIRED"):
        step(bound, inputs, selected, "action", {"option_id": "A", "task_id": observed["task_id"]}, "action-unselected-01")
    with pytest.raises(ValueError, match="PAYLOAD_INVALID"):
        step(bound, inputs, selected, "action", {"option_id": "B", "task_id": observed["task_id"], "action_receipt": observed["action_receipt"]}, "action-client-receipt")
    assert _saved_work_counts(db) == before


def test_action_contract_revisions_cancel_and_final_owner_revocation(work, monkeypatch):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    first, actor, _, _ = _owner_read_contract(inputs)
    second, _, _, _ = _owner_read_contract(inputs, version=2, parent=first["action_receipt"])
    observed = {x["task_id"]: x for x in (first, second)}
    revoked = False
    def reader(task_id, *, actor, scope):
        if revoked: raise PermissionError("owner revoked during render")
        assert actor.principal_ref == inputs["actor_ref"] and scope == BusinessDecisionWorkflow._action_scope(inputs["scope"])
        return copy.deepcopy(observed[task_id])
    service = BusinessDecisionWorkflow(
        internal_action_reader=reader, action_actor=actor, source_actor=service._source_actor,
    )
    executed = _record_action(service, inputs, selected)
    assert _record_action(service, inputs, selected) == executed
    revised = _record_action(service, inputs, executed, second["task_id"], "action-contract-02")
    assert revised["action"]["receipt"]["parent_artifact_id"] == first["action_receipt"]["artifact_id"]
    interrupted = step(service, inputs, revised, "interrupt", {"reason": "Review interrupted."}, "interrupt-action-01")
    resumed = step(service, inputs, interrupted, "resume", {}, "resume-action-01")
    assert resumed["state"] == "ACTION_RECORDED" and resumed["action"] == revised["action"]
    cancelled = step(service, inputs, resumed, "cancel", {"reason": "Cancel remaining business work, not committed creation."}, "cancel-action-01")
    assert cancelled["state"] == "CANCELLED" and cancelled["action_state"] == "EXECUTED"
    before = _saved_work_counts(db)
    render = service.render_result
    def render_then_revoke(work):
        nonlocal revoked
        result = render(work)
        revoked = True
        return result
    monkeypatch.setattr(service, "render_result", render_then_revoke)
    with pytest.raises(PermissionError, match="owner revoked during render"):
        service.reopen(revised["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"])
    assert _saved_work_counts(db) == before


def test_action_contract_resource_revision_zero_unknown_and_evaluation_basis(work):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    constraints = {"budget_amount": "0", "estimated_cost_amount": None, "currency": "CNY",
                   "as_of": "2026-10-03T12:00:00+08:00", "limits": ["Existing staff only; no purchase authorization."]}
    payload = {"option_id": "B", "reason": "Keep within actual zero cash budget; estimate unknown.",
               "owner": "Consenting operator", "review_at": "2026-10-05T12:00:00+08:00", "resource_constraints": constraints}
    revised = step(service, inputs, selected, "choose", payload, "resource-revision-01")
    assert revised["decision"]["resource_constraints"]["budget_amount"] == "0"
    assert revised["decision"]["resource_constraints"]["estimated_cost_amount"] is None
    assert revised["decision"]["resource_constraints"]["budget_fit"] == "UNKNOWN"
    observed, actor, reader, _ = _owner_read_contract(inputs)
    service = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    executed = _record_action(service, inputs, revised)
    result = step(service, inputs, executed, "outcome_unknown", {"limits": "No measured cost or consumer effect."}, "resource-outcome-01")
    with sqlite3.connect(db) as con:
        metadata = json.loads(con.execute("SELECT metadata FROM evaluation_records WHERE evaluation_id=?", (result["evaluation"]["evaluation_id"],)).fetchone()[0])
    assert metadata["resource_constraints"] == revised["decision"]["resource_constraints"]
    assert metadata["resource_constraints"]["actual_spend"] is None
    assert "预算上限（人工输入）：0" in result["usable_result"]["markdown"]


@pytest.mark.parametrize("boundary", ["commit", "return_actor", "return_scope", "changed_receipt"])
def test_action_contract_final_fences_and_changed_receipt(work, boundary, monkeypatch):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    observed, actor, reader, _ = _owner_read_contract(inputs)
    service = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    before = _saved_work_counts(db)
    if boundary == "commit":
        calls = 0
        def authorize(operation):
            nonlocal calls
            if operation == "action":
                calls += 1
                if calls == 3: raise PermissionError("final domain commit revoked")
            return inputs["authorize"](operation)
        with pytest.raises(PermissionError, match="final domain commit revoked"):
            service.advance(selected["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"],
                            authorize=authorize, expected_revision=selected["revision"], submission_id="action-final-denial",
                            operation="action", payload={"option_id": "B", "task_id": observed["task_id"]})
        assert _saved_work_counts(db) == before
        return
    executed = _record_action(service, inputs, selected)
    before = _saved_work_counts(db)
    if boundary == "changed_receipt":
        # A consistent but different immutable owner postimage cannot replace
        # a previously signed action, even if its scope and Task still match.
        observed["action_receipt"]["sha256"] = "b" * 64
        observed["work"]["receipt"]["sha256"] = "b" * 64
        observed["work"]["artifact"]["sha256"] = "b" * 64
        with pytest.raises(RuntimeError, match="RECEIPT_CHANGED"):
            service.reopen(executed["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"])
    else:
        rendered = False
        render = service.render_result
        def render_flag(work):
            nonlocal rendered
            result = render(work)
            rendered = True
            return result
        def authorize(operation):
            receipt = copy.deepcopy(inputs["authorize"](operation))
            if rendered:
                if boundary == "return_actor": receipt["actor_id"] = "workspace:foreign"
                else: receipt["scope"]["entity_label"] = "Different focus"
            return receipt
        monkeypatch.setattr(service, "render_result", render_flag)
        with pytest.raises(PermissionError, match="AUTHORIZATION_MISMATCH"):
            service.reopen(executed["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=authorize)
    assert _saved_work_counts(db) == before


def test_action_contract_source_claim_is_not_measured_effect_and_eval_tamper_rejected(work):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    observed, actor, reader, _ = _owner_read_contract(inputs)
    service = BusinessDecisionWorkflow(
        internal_action_reader=reader, action_actor=actor, source_actor=service._source_actor,
    )
    executed = _record_action(service, inputs, selected)
    result = step(service, inputs, executed, "outcome", {"source_job_id": inputs["source_job_id"],
                  "source_id": inputs["options"][0]["source_ids"][0], "quote": "The source reports zero participants.",
                  "limits": "Attributed statement, not a measured consequence of this creation."}, "source-after-action")
    assert result["action_state"] == "EXECUTED" and result["outcome_state"] == "SOURCE_REPORTED"
    assert result["business_outcome"] == "NOT_OBSERVED" and result["evaluation"]["business_usefulness"] == "UNKNOWN"
    with sqlite3.connect(db) as con:
        row = con.execute("SELECT metadata FROM evaluation_records WHERE evaluation_id=?", (result["evaluation"]["evaluation_id"],)).fetchone()
        metadata = json.loads(row[0]); metadata["action_state"] = "NOT_EXECUTED"
        con.execute("UPDATE evaluation_records SET metadata=? WHERE evaluation_id=?", (json.dumps(metadata), result["evaluation"]["evaluation_id"]))
    with pytest.raises(RuntimeError, match="EVALUATION_BINDING_INVALID"):
        service.reopen(result["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"])


@pytest.mark.parametrize("invalid", ["missing_currency", "missing_time", "naive_time", "float_amount", "negative", "no_limits"])
def test_action_contract_resource_basis_required_and_no_write_on_invalid(work, invalid):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    constraints = {"budget_amount": "100", "estimated_cost_amount": "101", "currency": "CNY",
                   "as_of": "2026-10-03T12:00:00+08:00", "limits": ["One operator; no procurement."]}
    if invalid == "missing_currency": constraints["currency"] = None
    elif invalid == "missing_time": constraints["as_of"] = None
    elif invalid == "naive_time": constraints["as_of"] = "2026-10-03T12:00:00"
    elif invalid == "float_amount": constraints["estimated_cost_amount"] = 101.0
    elif invalid == "negative": constraints["budget_amount"] = "-1"
    else: constraints["limits"] = []
    before = _saved_work_counts(db)
    with pytest.raises(ValueError, match="RESOURCE"):
        step(service, inputs, selected, "choose", {"option_id": "B", "reason": "Cost constrained decision.",
             "owner": "Operator", "review_at": "2026-10-05T12:00:00+08:00", "resource_constraints": constraints}, "invalid-resource-01")
    assert _saved_work_counts(db) == before


def test_action_contract_budget_scenario_changes_decision_and_over_budget_is_explicit(work):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    constrained = {"option_id": "A", "reason": "Different available staff/time requires the other plan.",
                   "owner": "Operator", "review_at": "2026-10-05T12:00:00+08:00",
                   "resource_constraints": {"budget_amount": "100", "estimated_cost_amount": "101", "currency": "CNY",
                   "as_of": "2026-10-03T12:00:00+08:00", "limits": ["Only one operator and one day available."]}}
    revised = step(service, inputs, selected, "choose", constrained, "cost-plan-revision")
    assert revised["decision"]["option_id"] == "A" and revised["decision"]["resource_constraints"]["budget_fit"] == "OVER_BUDGET"
    assert "超预算方案需调整" in revised["usable_result"]["markdown"]
    assert service.reopen(revised["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"]) == revised


@pytest.mark.parametrize("change", ["work_id", "parent_sha256"])
def test_action_contract_revision_cannot_replace_another_signed_creation(work, change):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    first, actor, _, _ = _owner_read_contract(inputs)
    second, _, _, _ = _owner_read_contract(inputs, version=2, parent=first["action_receipt"])
    if change == "work_id":
        for item in (second["action_receipt"], second["work"]["receipt"], second["work"]["document"]): item["work_id"] = "WORK-foreign"
    else:
        second["action_receipt"]["parent_sha256"] = "b" * 64
        second["work"]["document"]["parent_sha256"] = "b" * 64
        second["work"]["receipt"]["parent"]["sha256"] = "b" * 64
    observations = {x["task_id"]: x for x in (first, second)}
    def reader(task_id, *, actor, scope): return copy.deepcopy(observations[task_id])
    service = BusinessDecisionWorkflow(internal_action_reader=reader, action_actor=actor)
    executed = _record_action(service, inputs, selected)
    before = _saved_work_counts(db)
    with pytest.raises(RuntimeError, match="REVISION_INVALID"):
        _record_action(service, inputs, executed, second["task_id"], "action-foreign-parent")
    assert _saved_work_counts(db) == before


def test_action_contract_continues_legacy_source_outcome_without_rewriting_history(work):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    legacy = step(service, inputs, selected, "outcome", {"source_job_id": inputs["source_job_id"],
                  "source_id": inputs["options"][0]["source_ids"][0], "quote": "The source reports zero participants.",
                  "limits": "Source statement only, not a measured business effect."}, "legacy-source-outcome")
    with sqlite3.connect(db) as con:
        old_rows = con.execute("SELECT * FROM app_evidence_records WHERE feature_id=? ORDER BY id", (service.FEATURE,)).fetchall()
        old_eval = con.execute("SELECT * FROM evaluation_records WHERE evaluation_id=?", (legacy["evaluation"]["evaluation_id"],)).fetchone()
    observed, actor, reader, _ = _owner_read_contract(inputs)
    service = BusinessDecisionWorkflow(
        internal_action_reader=reader, action_actor=actor, source_actor=service._source_actor,
    )
    executed = _record_action(service, inputs, legacy)
    assert executed["action_state"] == "EXECUTED" and executed["business_outcome"] == "NOT_OBSERVED"
    reviewed = step(service, inputs, executed, "outcome_unknown", {"limits": "Draft creation performed; no later effect observation."}, "new-effect-review")
    assert reviewed["evaluation"]["evaluation_id"] != legacy["evaluation"]["evaluation_id"]
    assert "来源原文" in reviewed["usable_result"]["markdown"] and "业务效果：UNKNOWN" in reviewed["usable_result"]["markdown"]
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT * FROM app_evidence_records WHERE feature_id=? ORDER BY id LIMIT 3", (service.FEATURE,)).fetchall() == old_rows
        assert con.execute("SELECT * FROM evaluation_records WHERE evaluation_id=?", (legacy["evaluation"]["evaluation_id"],)).fetchone() == old_eval


def test_prepare_choose_outcome_reopen_and_unknown_evaluation(work):
    service, inputs, db = work
    original = service.prepare(**inputs)
    assert service.prepare(**inputs) == original
    assert original["state"] == "PREPARED" and len(original["options"]) == 2
    assert original["owned_analysis"] == {
        "state": "UNAVAILABLE", "reason": "OWNED_RUNTIME_NOT_BOUND"}
    assert original["return_context"]["global"] is True
    selected = choose(service, inputs, original)
    assert selected["decision"]["approval"] == "INTERNAL_SELECTION_ONLY"
    payload = {"source_job_id": inputs["source_job_id"], "source_id": inputs["options"][0]["source_ids"][0],
               "quote": "The source reports zero participants.", "limits": "Not a measured campaign outcome or causal attribution."}
    result = step(service, inputs, selected, "outcome", payload, "outcome-request-01")
    assert result["state"] == "OUTCOME_RECORDED" and result["outcome_state"] == "SOURCE_REPORTED"
    assert result["action_state"] == "NOT_EXECUTED"
    assert result["outcome"]["causation"] == "NOT_ESTABLISHED"
    assert result["evaluation"]["state"] == "RECORDED" and result["evaluation"]["business_usefulness"] == "UNKNOWN"
    assert step(service, inputs, selected, "outcome", payload, "outcome-request-01") == result
    assert BusinessDecisionWorkflow().reopen(result["work_id"], actor_ref=inputs["actor_ref"],
                                           scope=inputs["scope"], authorize=inputs["authorize"]) == result
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT count(*) FROM canonical_data").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM daily_reports").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id=?", (service.FEATURE,)).fetchone()[0] == 3
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def _saved_work_counts(db):
    with sqlite3.connect(db) as con:
        return tuple(con.execute("SELECT count(*) FROM " + table).fetchone()[0]
                     for table in ("canonical_data", "daily_reports", "app_evidence_records"))


def test_reopen_rechecks_read_after_render_revocation(work, monkeypatch):
    service, inputs, db = work
    prepared = service.prepare(**inputs)
    stored_before = _saved_work_counts(db)
    render = service.render_result
    revoked = False
    calls = []

    def render_and_revoke(result):
        nonlocal revoked
        assert result["source_brief"] and result["material_review"]["sources"]
        rendered = render(result)
        assert rendered["markdown"]
        revoked = True
        return rendered

    def authorize(operation):
        calls.append(operation)
        if revoked:
            raise PermissionError("read revoked during render")
        return inputs["authorize"](operation)

    monkeypatch.setattr(service, "render_result", render_and_revoke)
    with pytest.raises(PermissionError, match="read revoked during render"):
        service.reopen(prepared["work_id"], actor_ref=inputs["actor_ref"],
                       scope=inputs["scope"], authorize=authorize)
    assert calls == ["read", "read"]
    assert _saved_work_counts(db) == stored_before


@pytest.mark.parametrize("mismatch", ["actor", "scope"])
def test_reopen_rejects_changed_final_read_authorization(work, mismatch):
    service, inputs, db = work
    prepared = service.prepare(**inputs)
    stored_before = _saved_work_counts(db)
    calls = []

    def authorize(operation):
        calls.append(operation)
        receipt = copy.deepcopy(inputs["authorize"](operation))
        if len(calls) == 2:
            if mismatch == "actor":
                receipt["actor_id"] = "workspace:foreign"
            else:
                key = "subject_id" if inputs["scope"]["product_id"] == "CTH" else "brand_focus_id"
                receipt["scope"][key] = "FOREIGN-ENTITY"
        return receipt

    with pytest.raises(PermissionError, match="BUSINESS_WORK_AUTHORIZATION_MISMATCH"):
        service.reopen(prepared["work_id"], actor_ref=inputs["actor_ref"],
                       scope=inputs["scope"], authorize=authorize)
    assert calls == ["read", "read"]
    assert _saved_work_counts(db) == stored_before


def test_interruption_bounded_resume_cancel_preserves_report(work):
    service, inputs, db = work
    current = service.prepare(**inputs)
    for index in range(2):
        current = step(service, inputs, current, "interrupt", {"reason": "Operator stopped work."}, f"interrupt-{index}")
        current = step(service, inputs, current, "resume", {}, f"resume-request-{index}")
        assert current["state"] == "PREPARED" and current["resume_count"] == index + 1
    current = step(service, inputs, current, "interrupt", {"reason": "Operator stopped work."}, "interrupt-last")
    with pytest.raises(RuntimeError, match="RESUME_LIMIT"):
        step(service, inputs, current, "resume", {}, "resume-too-many")
    current = step(service, inputs, current, "cancel", {"reason": "No longer required."}, "cancel-request-01")
    with pytest.raises(RuntimeError, match="TERMINAL"):
        choose(service, inputs, current)
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT count(*) FROM daily_reports").fetchone()[0] == 1


@pytest.mark.parametrize("change", ["actor", "scope", "audits", "operation"])
def test_server_receipt_mismatch_never_writes(work, change):
    service, inputs, db = work
    def forged(operation):
        receipt = inputs["authorize"](operation)
        receipt.update({"actor_id": "workspace:foreign"} if change == "actor" else
                       {"scope": {**inputs["scope"], "global": True}} if change == "scope" else
                       {"permission_audit_ref": ""} if change == "audits" else {"operation": "read"})
        return receipt
    with pytest.raises((PermissionError, ValueError)):
        service.prepare(**{**inputs, "authorize": forged})
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id=?", (service.FEATURE,)).fetchone()[0] == 0


def test_stale_revision_conflicting_retry_and_foreign_reopen(work):
    service, inputs, _ = work
    prepared = service.prepare(**inputs)
    with pytest.raises(ValueError, match="SUBMISSION_CONFLICT"):
        service.prepare(**{**inputs, "question": "Changed business question."})
    choose(service, inputs, prepared)
    with pytest.raises(RuntimeError, match="REVISION_CONFLICT"):
        step(service, inputs, prepared, "cancel", {"reason": "Stale client."}, "cancel-stale-01")
    with pytest.raises(PermissionError):
        service.reopen(prepared["work_id"], actor_ref="workspace:foreign", scope=inputs["scope"], authorize=inputs["authorize"])


@pytest.mark.parametrize("change", ["single_option", "foreign_source", "no_limits", "domain", "global"])
def test_insufficient_or_mismatched_work_is_rejected(work, change):
    service, original, _ = work
    inputs = {**original, "options": copy.deepcopy(original["options"])}
    if change == "single_option": inputs["options"] = inputs["options"][:1]
    elif change == "foreign_source": inputs["options"][0]["source_ids"] = ["foreign"]
    elif change == "no_limits": inputs["options"][0]["unknowns"] = []
    elif change == "domain": inputs["kind"] = "creator_campaign" if inputs["kind"] == "venue_operations" else "consumer_risk"
    else:
        inputs["scope"] = {**inputs["scope"], "global": True}
    with pytest.raises((PermissionError, ValueError)):
        service.prepare(**inputs)


def test_source_and_transition_tampering_reject_reopen(work):
    service, inputs, db = work
    prepared = service.prepare(**inputs)
    with sqlite3.connect(db) as con:
        con.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE feature_id=?", (service.FEATURE,))
    with pytest.raises(RuntimeError, match="SIGNATURE"):
        service.reopen(prepared["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"])


def test_final_permission_denial_rolls_back(work):
    service, inputs, db = work
    count = 0
    def revoked(operation):
        nonlocal count
        count += 1
        if count > 1: raise PermissionError("revoked at persistence fence")
        return inputs["authorize"](operation)
    with pytest.raises(PermissionError, match="revoked"):
        service.prepare(**{**inputs, "authorize": revoked})
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id=?", (service.FEATURE,)).fetchone()[0] == 0


def test_outcome_must_quote_selected_source_and_follow_decision(work):
    service, inputs, _ = work
    prepared = service.prepare(**inputs)
    payload = {"source_job_id": inputs["source_job_id"], "source_id": inputs["options"][0]["source_ids"][0],
               "quote": "Invented sales growth.", "limits": "No measured impact."}
    with pytest.raises(RuntimeError, match="DECISION_REQUIRED"):
        step(service, inputs, prepared, "outcome", payload, "outcome-invalid-01")
    selected = choose(service, inputs, prepared)
    with pytest.raises(ValueError, match="QUOTE_NOT_IN_SOURCE"):
        step(service, inputs, selected, "outcome", payload, "outcome-invalid-02")


def test_real_server_receipt_rechecks_scope_transport_and_write_gate(report_client):
    from api_dual_domain import authorize_business_work_request
    from lumenis.system.security import permission as p
    from shared_artifacts import LocalArtifactError
    api, app, db, entry, gate = report_client
    headers = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    report = api.post(URL + "/generate", headers=headers, json={}).get_json()["result"]
    with sqlite3.connect(db) as con:
        actor = json.loads(con.execute("SELECT source_snapshot FROM daily_reports WHERE report_id=?", (report["job_id"],)).fetchone()[0])["actor_id"]
    scope = report["source_brief"]["scope"]
    with app.test_request_context("/", headers=headers, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        assert authorize_business_work_request("prepare", actor_ref=actor, scope=scope)["operation_audit_ref"]
        gate.revoke_permission(p.PermissionLevel.VERIFY)
        assert authorize_business_work_request("read", actor_ref=actor, scope=scope)["operation"] == "read"
        with pytest.raises(PermissionError):
            authorize_business_work_request("choose", actor_ref=actor, scope=scope)
    with app.test_request_context("/", headers={**headers, "Origin": "https://foreign.invalid"}, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        with pytest.raises((PermissionError, LocalArtifactError)):
            authorize_business_work_request("read", actor_ref=actor, scope=scope)
    with app.test_request_context("/", headers=GLOBAL, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        with pytest.raises(PermissionError):
            authorize_business_work_request("read", actor_ref=actor, scope=scope)


def test_evaluation_failure_replay_repairs_exact_outcome(work, monkeypatch):
    from lumenis.shared.evaluation import recorder
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    payload = {"source_job_id": inputs["source_job_id"], "source_id": inputs["options"][0]["source_ids"][0],
               "quote": "The source reports zero participants.", "limits": "Not a campaign measurement."}
    with monkeypatch.context() as failure:
        failure.setattr(recorder, "record_evaluation", lambda **k: (_ for _ in ()).throw(OSError("isolated injected failure")))
        with pytest.raises(OSError):
            step(service, inputs, selected, "outcome", payload, "outcome-recovery-01")
    recovered = service.reopen(selected["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"])
    assert recovered["evaluation"]["state"] == "PENDING_RECOVERY"
    result = step(service, inputs, selected, "outcome", payload, "outcome-recovery-01")
    assert result["evaluation"]["state"] == "RECORDED"
    assert len(result["timeline"]) == 3


def test_later_source_rewrite_cannot_change_recorded_result(work):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    payload = {"source_job_id": inputs["source_job_id"], "source_id": inputs["options"][0]["source_ids"][0],
               "quote": "The source reports zero participants.", "limits": "Not a causal attribution."}
    result = step(service, inputs, selected, "outcome", payload, "outcome-source-01")
    with sqlite3.connect(db) as con:
        con.execute("UPDATE canonical_data SET content='Changed source body'")
    with pytest.raises(RuntimeError, match="OUTCOME_SOURCE_CHANGED"):
        service.reopen(result["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"])


def test_existing_cth_case_continues_into_decision_without_replacing_case(case_client):
    from api_dual_domain import authorize_business_work_request
    api, app, db, headers, body, gate = case_client
    from tests.test_growth_business_fixture import prepare_owner_source
    fixture_scope = {"domain_id": "cth", "subject_id": headers["X-Subject-ID"],
                     "brand_focus_id": None, "global_scope": False}
    ws = {"api": api, "app": app, "db": db, "headers": headers, "gate": gate,
          "scope": fixture_scope, "source_id": body["source_ids"][0]}
    prepare_owner_source(ws)
    report = api.post(URL + "/generate", headers=headers, json={}).get_json()["result"]
    body = {**body, "source_ids": [ws["source_id"]], "source_job_id": report["job_id"]}
    case = api.post("/api/experience/cth/cases", headers=headers, json=body).get_json()["result"]
    with sqlite3.connect(db) as con:
        actor = con.execute("SELECT actor_ref FROM lumenis_cth_cases").fetchone()[0]
    options = [{"option_id": name, "proposal": "Operator-proposed venue investigation " + name,
                "rationale": "A source is a lead, not a confirmed operational effect.", "source_ids": body["source_ids"],
                "assumptions": ["Team capacity is not yet confirmed."], "unknowns": ["Consumer and sales metrics are not available."],
                "check": "Verify store resources and source rights before deciding whether to continue."} for name in ["A", "B"]]
    service = BusinessDecisionWorkflow()
    with app.test_request_context("/", headers=headers, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        authorize = lambda operation: authorize_business_work_request(operation, actor_ref=actor, scope=case["scope"])
        work = service.prepare_from_case(case["case_id"], actor_ref=actor, scope=case["scope"],
                    submission_id="case-business-01", kind="venue_operations", options=options, authorize=authorize)
        assert work["case_id"] == case["case_id"] and work["question"] == case["question"]
        assert work["case_evidence_ref"] == case["creation_evidence_ref"]
        assert work["source_report_hash"] == case["source_report_hash"]
        selected = service.advance(work["work_id"], actor_ref=actor, scope=case["scope"],
                    submission_id="case-decision-01", operation="choose", expected_revision=work["revision"],
                    payload={"option_id": "A", "reason": "First verify exact venue resources.",
                             "owner": "Venue operator", "review_at": "2026-10-05T09:00:00+08:00"}, authorize=authorize)
        assert selected["state"] == "DECIDED" and "Venue operator" in selected["usable_result"]["markdown"]
    assert api.get("/api/experience/cth/cases/" + case["case_id"], headers=headers).get_json()["result"] == case


def test_task_material_gaps_do_not_turn_official_identity_into_consumer_evidence(work):
    service, inputs, _ = work
    current = service.prepare(**inputs)
    review = current["material_review"]
    assert review["state"] == "INSUFFICIENT_MATERIAL"
    assert review["consumer_conclusion"] == "NOT_ESTABLISHED"
    assert review["collection_triggered"] is False
    assert review["sources"][0]["role_status"] == "CAPTURE_ANNOTATION_ONLY"
    assert review["sources"][0]["commercial_reuse"] == "UNKNOWN"
    assert review["sources"][0]["engagement"]["value"] is None
    if inputs["scope"]["product_id"] == "CTH":
        missing = next(c for c in review["checks"] if c["required_role"] == "CONSUMER_FEEDBACK")
    else:
        missing = next(c for c in review["checks"] if c["required_role"] == "MARKET_DISCLOSURE")
    assert missing["state"] == "MISSING_MATERIAL" and missing["source_ids"] == []
    assert "官网自述不代表消费者意见" in current["usable_result"]["markdown"]


def test_measured_zero_and_partial_engagement_have_distinct_meanings(work):
    service, inputs, db = work
    current = service.prepare(**inputs)
    with sqlite3.connect(db) as con:
        con.execute("UPDATE canonical_data SET engagement_likes=0, engagement_comments=0, "
                    "engagement_collects=0, engagement_shares=0 WHERE source_id=?", (inputs["options"][0]["source_ids"][0],))
    reopened = service.reopen(current["work_id"], actor_ref=inputs["actor_ref"],
                              scope=inputs["scope"], authorize=inputs["authorize"])
    metric = reopened["material_review"]["sources"][0]["engagement"]
    assert metric["value"] == 0 and metric["state"] == "COMPLETE_INPUT"
    with sqlite3.connect(db) as con:
        con.execute("UPDATE canonical_data SET engagement_shares=NULL WHERE source_id=?", (inputs["options"][0]["source_ids"][0],))
    reopened = service.reopen(current["work_id"], actor_ref=inputs["actor_ref"],
                              scope=inputs["scope"], authorize=inputs["authorize"])
    metric = reopened["material_review"]["sources"][0]["engagement"]
    assert metric["value"] is None and metric["state"] == "MISSING_INPUT"
    assert metric["components"]["likes"] == 0 and metric["components"]["shares"] is None
    assert metric["interpretation"] == "SOURCE_INTERACTIONS_ONLY_NOT_DEMAND_OR_ROI"


def test_readable_result_keeps_source_time_rights_and_missing_metrics_visible(work):
    service, inputs, db = work
    current = service.prepare(**inputs)
    markdown = current["usable_result"]["markdown"].replace("\\", "")
    assert "https://example.org/isolated-test" in markdown
    assert "捕获时间：2026-10-02T00:00:00Z" in markdown
    assert "发布时间：未知（不能以捕获时间替代）" in markdown
    assert "商业使用许可：UNKNOWN" in markdown
    assert "来源互动字段合计：未知（字段未齐）" in markdown
    with sqlite3.connect(db) as con:
        con.execute("UPDATE canonical_data SET engagement_likes=0, engagement_comments=0, "
                    "engagement_collects=0, engagement_shares=0 WHERE source_id=?", (inputs["options"][0]["source_ids"][0],))
    reopened = service.reopen(current["work_id"], actor_ref=inputs["actor_ref"],
                              scope=inputs["scope"], authorize=inputs["authorize"])
    assert "来源互动字段合计：0" in reopened["usable_result"]["markdown"]
    assert "不代表客流、需求、销量或投放回报" in reopened["usable_result"]["markdown"]


def test_readable_result_withholds_credential_or_unapproved_query_urls(work):
    service, inputs, db = work
    with sqlite3.connect(db) as con:
        con.execute("UPDATE canonical_data SET url=? WHERE source_id=?",
                    ("https://example.org/source?token=TEST_ONLY_CANARY", inputs["options"][0]["source_ids"][0]))
    result = service.prepare(**inputs)
    assert "TEST_ONLY_CANARY" not in result["usable_result"]["markdown"]
    assert "已隐去" in result["usable_result"]["markdown"]


@pytest.fixture
def related_work(work):
    service, inputs, db = work
    scope = inputs["scope"]
    product = scope["product_id"]
    subject = "VENUE-B" if product == "CTH" else None
    brand = "BRAND-B" if product == "ZBMP" else None
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row
        ref = store.record_evidence(connection=con, source="isolated_context", project="LUMENIS",
                product=product, domain_id=scope["domain_id"], subject_id=subject, brand_focus_id=brand, global_scope=False,
                feature_id="TEST_CONTEXT", status="verified", result="PASS", inputs={"source_ids": ["industry-source"]})
        persist_canonical(con, CanonicalRecord(canonical_id="industry-canonical", source_id="industry-source",
                product_id=product, domain_id=scope["domain_id"], subject_id=subject, brand_focus_id=brand, scope_status="VERIFIED", scope_evidence_ref=str(ref),
                source_type="web_mention", source_platform="web", title="Industry background", content="Different geography and period.",
                url="https://example.org/industry", captured_at="2026-10-02T00:00:00Z"))
        con.commit()
        report = create_source_brief_job(con, product_id=product, global_scope=False, subject_id=subject, brand_focus_id=brand, entity_label="Related entity B",
                actor_id=inputs["actor_ref"], permission_audit_ref="audit:global-read", trace_id="context-trace", job_id="job-context-test")
    original = report["source_brief"]["scope"]
    descriptor = {"job_id": report["job_id"], "original_scope": original, "purpose": "Compare only disclosed geographic and period boundaries."}
    def authorize_related(original_scope, operation):
        return {"actor_id": inputs["actor_ref"], "scope": original_scope, "operation": operation,
                "permission_audit_ref": "audit:context-read", "operation_audit_ref": "audit:context-read"}
    current = service.prepare(**inputs)
    args = {"actor_ref": inputs["actor_ref"], "scope": scope, "authorize": inputs["authorize"],
            "related_reports": [descriptor], "authorize_related": authorize_related}
    return service, current, args, db


def test_focus_lens_preserves_related_evidence_scope_and_writes_nothing(related_work):
    service, current, args, db = related_work
    with sqlite3.connect(db) as con:
        before = con.execute("SELECT count(*) FROM app_evidence_records").fetchone()[0]
    lens = service.focus_lens(current["work_id"], **args)
    context = lens["related_context"][0]
    assert lens["task_focus_scope"]["global"] is False
    assert context["original_scope"]["global"] is False
    assert context["original_scope"] != lens["task_focus_scope"]
    assert context["source_brief"]["scope"] == context["original_scope"]
    assert context["task_focus_scope"] == lens["task_focus_scope"]
    assert context["source_brief"]["records"][0]["source_id"] == "industry-source"
    assert lens["analysis"]["state"] == "UNAVAILABLE"
    assert lens["truth_rewritten"] is False and lens["collection_triggered"] is False
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT count(*) FROM app_evidence_records").fetchone()[0] == before
        stored_scope = con.execute("SELECT subject_id,brand_focus_id FROM canonical_data WHERE source_id='industry-source'").fetchone()
        assert stored_scope == (("VENUE-B", None) if args["scope"]["product_id"] == "CTH" else (None, "BRAND-B"))


def test_focus_lens_requires_original_scope_read_and_rechecks_revocation(related_work):
    service, current, args, _ = related_work
    count = 0
    real = args["authorize_related"]
    def revoked(original, operation):
        nonlocal count
        count += 1
        if count > 1: raise PermissionError("context read revoked")
        return real(original, operation)
    with pytest.raises(PermissionError, match="revoked"):
        service.focus_lens(current["work_id"], **{**args, "authorize_related": revoked})
    forged = lambda original, operation: {**real(original, operation), "scope": args["scope"]}
    with pytest.raises(PermissionError, match="AUTHORIZATION_MISMATCH"):
        service.focus_lens(current["work_id"], **{**args, "authorize_related": forged})


def test_focus_lens_rechecks_first_scope_after_second_related_read(related_work):
    service, current, args, db = related_work
    first = args["related_reports"][0]
    scope = args["scope"]
    product = scope["product_id"]
    second_subject = "VENUE-C" if product == "CTH" else None
    second_brand = "BRAND-C" if product == "ZBMP" else None
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row
        ref = store.record_evidence(connection=con, source="isolated_context_second", project="LUMENIS",
                product=product, domain_id=scope["domain_id"], subject_id=second_subject,
                brand_focus_id=second_brand, global_scope=False, feature_id="TEST_CONTEXT",
                status="verified", result="PASS", inputs={"source_ids": ["industry-source-second"]})
        persist_canonical(con, CanonicalRecord(canonical_id="industry-canonical-second",
                source_id="industry-source-second", product_id=product, domain_id=scope["domain_id"],
                subject_id=second_subject, brand_focus_id=second_brand, scope_status="VERIFIED",
                scope_evidence_ref=str(ref), source_type="web_mention", source_platform="web",
                title="Industry background second", content="Separate geography and period.",
                url="https://example.org/industry-second", captured_at="2026-10-02T00:00:00Z"))
        con.commit()
        report = create_source_brief_job(con, product_id=product, global_scope=False,
                subject_id=second_subject, brand_focus_id=second_brand, entity_label="Related entity C",
                actor_id=args["actor_ref"], permission_audit_ref="audit:global-read",
                trace_id="context-trace-second", job_id="job-context-second")
    second = {"job_id": report["job_id"], "original_scope": report["source_brief"]["scope"],
              "purpose": "Compare only disclosed geographic and period boundaries."}
    first_scope, second_scope = first["original_scope"], second["original_scope"]
    calls = {"first": 0, "second": 0}
    first_revoked = False
    def revoke_first_during_second_read(original, operation):
        nonlocal first_revoked
        if original == first_scope:
            calls["first"] += 1
            if first_revoked:
                raise PermissionError("first context scope revoked during second report read")
        elif original == second_scope:
            calls["second"] += 1
            if calls["second"] == 2:
                first_revoked = True
        else:
            raise AssertionError("unexpected related scope")
        return {"actor_id": args["actor_ref"], "scope": original, "operation": operation,
                "permission_audit_ref": "audit:context-read", "operation_audit_ref": "audit:context-read"}
    with sqlite3.connect(db) as con:
        before = tuple(con.execute("SELECT count(*) FROM app_evidence_records").fetchone())
    with pytest.raises(PermissionError, match="first context scope revoked"):
        service.focus_lens(current["work_id"], **{**args, "related_reports": [first, second],
                "authorize_related": revoke_first_during_second_read})
    assert first_revoked and calls["second"] >= 2
    with sqlite3.connect(db) as con:
        after = tuple(con.execute("SELECT count(*) FROM app_evidence_records").fetchone())
    assert after == before


def test_focus_lens_rejects_global_flag_with_a_retained_focus(related_work):
    service, current, args, _ = related_work
    descriptor = copy.deepcopy(args["related_reports"][0])
    descriptor["original_scope"]["global"] = True
    with pytest.raises(PermissionError, match="BUSINESS_LENS_CONTEXT_SCOPE_INVALID"):
        service.focus_lens(current["work_id"], **{**args, "related_reports": [descriptor]})


def test_related_read_adapter_uses_existing_sealed_principal_and_transport(report_client):
    from api_dual_domain import authorize_business_related_read
    from lumenis.system.security import permission as p
    api, app, db, entry, _ = report_client
    headers = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    report = api.post(URL + "/generate", headers=headers, json={}).get_json()["result"]
    scope = report["source_brief"]["scope"]
    with app.test_request_context("/", headers=headers, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        principal = p.resolve_local_workspace_principal(module="reports", action="read")
        receipt = authorize_business_related_read(principal, actor_ref=principal.principal_ref, original_scope=scope, operation="read")
        assert receipt["scope"] == scope and receipt["permission_audit_ref"]
        with pytest.raises(PermissionError):
            authorize_business_related_read({"principal_ref": principal.principal_ref}, actor_ref=principal.principal_ref,
                                            original_scope=scope, operation="read")
        with pytest.raises(PermissionError):
            authorize_business_related_read(principal, actor_ref=principal.principal_ref, original_scope=scope, operation="choose")
    with app.test_request_context("/", headers={**headers, "Origin": "https://foreign.invalid"}, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        with pytest.raises(PermissionError):
            authorize_business_related_read(principal, actor_ref=principal.principal_ref, original_scope=scope, operation="read")
