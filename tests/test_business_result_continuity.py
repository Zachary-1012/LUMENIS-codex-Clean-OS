"""C3 domain/Shared persistence checks; fixtures are not live user acceptance."""
import copy
import json

import pytest

from tests.test_saved_document_workflow import workspace
from api_dual_domain import BusinessDecisionWorkflow


@pytest.fixture(params=["CTH", "BMP"])
def business(workspace, request, monkeypatch):
    import api_dual_domain
    import subject_registry
    from lumenis.shared.database.business_schema import apply_business_schema
    from lumenis.shared.evaluation.recorder import init_db
    from lumenis.shared.reporting import source_brief_job as jobs
    monkeypatch.setattr(api_dual_domain, "get_repository", lambda: workspace["repo"])
    monkeypatch.setattr(jobs, "get_repository", lambda: workspace["repo"])
    entity, _ = subject_registry.add_subject({"domain_id": request.param,
        "subject_type": "company" if request.param == "CTH" else "brand",
        "name_en": "Isolated business source", "name_zh": "隔离业务来源"})
    scope = {"domain_id": "cth" if request.param == "CTH" else "zbmp",
             "global_scope": False, "subject_id": entity["subject_id"] if request.param == "CTH" else None,
             "brand_focus_id": entity["brand_focus_id"] if request.param == "BMP" else None}
    with workspace["repo"].transaction() as con:
        apply_business_schema(con)
    init_db()
    result = {**workspace, "scope": scope, "jobs": jobs}
    report, citation = add_material(result, "first", "Original issuer disclosure. No consumer effect measured.")
    domain_scope = report["source_brief"]["scope"]
    actor_ref = workspace["actor"].principal_ref
    def authorize(operation):
        return {"actor_id": actor_ref, "scope": domain_scope, "operation": operation,
                "permission_audit_ref": "isolated-scope-audit", "operation_audit_ref": "isolated-operation-audit"}
    options = make_options(report["source_brief"]["records"][0]["source_id"])
    service = BusinessDecisionWorkflow(action_actor=workspace["actor"])
    prepared = service.prepare(actor_ref=actor_ref, scope=domain_scope, submission_id="prepare-business-test",
        source_job_id=report["job_id"], kind="venue_operations" if request.param == "CTH" else "brand_market",
        question="Which source-bounded internal review should be prepared?", options=options, authorize=authorize)
    selected = service.advance(prepared["work_id"], actor_ref=actor_ref, scope=domain_scope, authorize=authorize,
        expected_revision=prepared["revision"], submission_id="choose-business-test", operation="choose",
        payload=selection("A", "100"))
    return {**result, "service": service, "actor_ref": actor_ref, "domain_scope": domain_scope,
            "authorize": authorize, "current": selected, "citation": citation, "options": options}


def add_material(ws, name, body):
    from lumenis.system.security import permission
    path = ws["root"] / (name + ".txt")
    path.write_text(body, encoding="utf-8")
    provenance = {"source_url": "https://example.org/business/" + name,
                  "published_at": None, "captured_at": "2026-10-08T00:00:00Z",
                  "rights": "public-reference-only", "title": "Isolated original " + name}
    args = {"actor": ws["actor"], "scope": ws["scope"], "provenance": provenance}
    resource = ws["documents"].document_import_resource(str(path), **args)
    ws["gate"].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=resource, granted_by="isolated-test")
    source = ws["documents"].import_document(str(path), **args)
    with ws["repo"].transaction() as con:
        report = ws["jobs"].create_source_brief_job(con, product_id="CTH" if ws["scope"]["domain_id"] == "cth" else "ZBMP",
            subject_id=ws["scope"]["subject_id"], brand_focus_id=ws["scope"]["brand_focus_id"],
            global_scope=False, entity_label="Isolated business source", source_ids=[source["source_id"]],
            actor_id=ws["actor"].principal_ref, permission_audit_ref="isolated-source-audit",
            trace_id="isolated-trace-" + name, job_id="isolated-job-" + name)
    citation = ws["documents"].locate_quote(source["evidence_id"], actor=ws["actor"], scope=ws["scope"],
                                           start=0, end=min(25, len(body)))["citation"]
    return report, citation


def make_options(source_id):
    return [{"option_id": key, "proposal": "Internal review " + key, "rationale": "Review source statements only.",
             "source_ids": [source_id], "assumptions": ["Internal review resources require confirmation."],
             "unknowns": ["Actual demand and outcomes have not been measured."], "check": "Record exact source limits."}
            for key in ("A", "B")]


def selection(option, budget):
    return {"option_id": option, "reason": "Use the bounded review plan.", "owner": "Isolated reviewer",
            "review_at": "2026-10-09T12:00:00+08:00",
            "resource_constraints": {"budget_amount": budget, "estimated_cost_amount": "50", "currency": "CNY",
                                     "as_of": "2026-10-08T08:00:00+08:00", "limits": ["Estimate only; no purchasing."]}}


def save(ws, *, request_id="save-business-01", citations=None, parent=None, digest=None):
    from lumenis.system.security import permission
    args = {"actor_ref": ws["actor_ref"], "scope": ws["domain_scope"], "authorize": ws["authorize"],
            "expected_revision": ws["current"]["revision"], "request_id": request_id,
            "citations": [ws["citation"]] if citations is None else citations,
            "previous_artifact_id": parent, "expected_draft_digest": digest}
    review = ws["service"].save_result_request(ws["current"]["work_id"], **args)
    ws["gate"].grant_approval(permission.OperationType.DATA_EXPORT.value, resource=review["resource"], granted_by="isolated-test")
    return ws["service"].save_result(ws["current"]["work_id"], **args)


def adopt(ws, report, options, decision, *, request_id="adopt-business-01"):
    return ws["service"].advance(ws["current"]["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=ws["current"]["revision"], submission_id=request_id,
        operation="adopt", payload={"source_job_id": report["job_id"], "question": ws["current"]["question"],
                                   "options": options, "decision": decision, "reason": "Explicitly adopt corrected inputs."})


def test_domain_save_replay_creation_inheritance_and_budget_revision(business):
    from lumenis.shared.content_creation.contracts import resolve_creation_upstream
    ws = business
    saved = save(ws)
    first = saved["saved_work"]
    replay = save(ws)
    assert replay["saved_work"]["replayed"]
    assert replay["creation_upstream"] == saved["creation_upstream"]
    upstream = resolve_creation_upstream(saved["creation_upstream"], actor=ws["actor"], scope=ws["scope"])
    assert upstream["document"]["citations"][0]["quote"] == ws["citation"]["quote"]
    assert upstream["document"]["payload"]["brief"]["goal"] == ws["current"]["question"]
    assert upstream["document"]["payload"]["brief"]["resource_constraints"]["budget_amount"] == "100"
    with ws["repo"].connection(read_only=True, wal=False) as con:
        report = ws["service"]._report(con, ws["current"]["source_report"]["job_id"], ws["actor_ref"], ws["domain_scope"])
    options = copy.deepcopy(ws["options"])
    options[1]["proposal"] = "Expanded internal review with two independently checked drafts."
    original_work = ws["current"]
    ws["current"] = adopt(ws, report["snapshot"], options, selection("B", "300"))
    assert ws["current"]["adoption"]["unchanged_option_ids"] == ["A"]
    assert ws["current"]["adoption"]["changed_option_ids"] == ["B"]
    old_request = {**ws, "current": original_work}
    delayed_replay = save(old_request)
    assert delayed_replay["saved_work"]["replayed"]
    assert delayed_replay["creation_upstream"] == saved["creation_upstream"]
    assert delayed_replay["state"] == "SAVED_PREVIOUS_REVISION"
    assert delayed_replay["current_revision"] == ws["current"]["revision"]
    with pytest.raises(RuntimeError, match="BUSINESS_WORK_REVISION_CONFLICT"):
        save(old_request, request_id="uncommitted-stale-save", parent=first["artifact"]["artifact_id"],
             digest=first["document"]["draft_digest"])
    assert ws["repo"].query_one("SELECT count(*) FROM lumenis_shared_artifacts WHERE kind='saved_document'")[0] == 1
    second = save(ws, request_id="save-business-02", parent=first["artifact"]["artifact_id"], digest=first["document"]["draft_digest"])
    assert second["saved_work"]["document"]["version"] == 2
    assert second["saved_work"]["document"]["parent_sha256"] == first["artifact"]["sha256"]
    assert ws["work"].reopen_work(first["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"])["document"] == first["document"]
    assert json.loads(ws["work"].export_work(second["saved_work"]["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"])["content"])["version"] == 2


def test_derived_analysis_reopen_reports_canonical_snapshot_changes_without_rewriting_it(business):
    ws = business
    source_id = ws["current"]["options"][0]["source_ids"][0]
    fields = ("canonical_id", "source_id", "source_platform", "subject_id", "brand_focus_id",
              "publish_datetime", "captured_at", "sentiment", "risk_level",
              "engagement_likes", "engagement_comments", "engagement_collects", "engagement_shares")
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        original = ws["service"]._canonical_source(connection, source_id, ws["domain_scope"])
        snapshot = {key: original.get(key) for key in fields}
        analysis = {"version": ws["service"].CURRENT_ANALYSIS_VERSION,
                    "question_result": {"business_report": {"canonical_inputs": [snapshot]}}}
        assert ws["service"]._analysis_input_status(connection, analysis, ws["domain_scope"]) is None

    with ws["repo"].transaction() as connection:
        connection.execute("UPDATE canonical_data SET engagement_likes=? WHERE source_id=? AND product_id=? AND domain_id=?",
                           ((original.get("engagement_likes") or 0) + 1, source_id,
                            ws["domain_scope"]["product_id"], ws["domain_scope"]["domain_id"]))
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        status = ws["service"]._analysis_input_status(connection, analysis, ws["domain_scope"])

    assert status == {"state": "CURRENT_INPUTS_CHANGED", "affected_source_ids": [source_id],
                      "snapshot_immutable": True, "adoption_required": True}
    assert snapshot["engagement_likes"] == original.get("engagement_likes")


def test_source_withdrawal_adopts_new_input_without_rewriting_old_artifact(business):
    ws = business
    first = save(ws)["saved_work"]
    report, citation = add_material(ws, "replacement", "Replacement attributed source. Outcomes remain unmeasured.")
    with ws["repo"].transaction() as con:
        con.execute("DELETE FROM canonical_data WHERE source_id=?", (ws["options"][0]["source_ids"][0],))
    with pytest.raises(PermissionError, match="BUSINESS_WORK_SOURCE_SCOPE_INVALID"):
        ws["service"].reopen(ws["current"]["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"])
    ws["current"] = adopt(ws, report, make_options(report["source_brief"]["records"][0]["source_id"]), selection("A", "100"))
    ws["citation"] = citation
    corrected = save(ws, request_id="save-after-withdrawal", parent=first["artifact"]["artifact_id"], digest=first["document"]["draft_digest"])
    assert corrected["saved_work"]["document"]["version"] == 2
    assert corrected["saved_work"]["document"]["parent_artifact_id"] == first["artifact"]["artifact_id"]
    assert corrected["saved_work"]["document"]["citations"][0]["evidence_id"] == citation["evidence_id"]


def test_withdrawn_quote_rights_block_old_use_and_allow_explicit_replacement(business):
    from lumenis.shared.content_creation.contracts import resolve_creation_upstream
    from lumenis.shared.evidence import store
    ws = business
    first = save(ws)
    evidence_id = ws["citation"]["evidence_id"]
    # Simulate a canonical writer-authenticated rights withdrawal in this
    # disposable DB; corrupt signatures would exercise a different boundary.
    with ws["repo"].transaction() as con:
        metadata = json.loads(con.execute("SELECT collection_metadata FROM app_evidence_records WHERE id=?",
                                          (evidence_id,)).fetchone()[0])
        metadata["provenance"]["rights"] = "withdrawn"
        con.execute("UPDATE app_evidence_records SET collection_metadata=? WHERE id=?",
                    (json.dumps(metadata), evidence_id))
        store._sign_evidence_record(con, evidence_id)
    artifact = first["saved_work"]["artifact"]
    for read in (ws["work"].reopen_work, ws["work"].export_work):
        with pytest.raises(ValueError, match="WORK_SOURCE_RIGHTS_UNVERIFIED"):
            read(artifact["artifact_id"], actor=ws["actor"], scope=ws["scope"])
    with pytest.raises(ValueError, match="WORK_SOURCE_RIGHTS_UNVERIFIED"):
        resolve_creation_upstream(first["creation_upstream"], actor=ws["actor"], scope=ws["scope"])
    with pytest.raises(ValueError, match="WORK_SOURCE_RIGHTS_UNVERIFIED"):
        save(ws)
    report, citation = add_material(ws, "rights-replacement", "A separately permitted replacement source.")
    ws["current"] = adopt(ws, report, make_options(report["source_brief"]["records"][0]["source_id"]), selection("B", "100"))
    ws["citation"] = citation
    replacement = save(ws, request_id="save-permitted-replacement", parent=artifact["artifact_id"],
                       digest=first["saved_work"]["document"]["draft_digest"])
    assert replacement["saved_work"]["document"]["parent_sha256"] == artifact["sha256"]
    assert replacement["saved_work"]["document"]["citations"] == [{**citation, "source_scope": ws["scope"]}]
    with pytest.raises(ValueError, match="WORK_SOURCE_RIGHTS_UNVERIFIED"):
        ws["work"].reopen_work(artifact["artifact_id"], actor=ws["actor"], scope=ws["scope"])


def test_actual_creation_action_outcome_and_adoption_preserve_fixed_versions(business, monkeypatch):
    import ai_task_engine
    from lumenis.shared.content_creation import internal_pitch as pitch
    from tests.test_internal_pitch_workflow import arguments
    ws = business
    for module in (ai_task_engine, pitch):
        monkeypatch.setattr(module, "get_repository", lambda: ws["repo"])
    with ws["repo"].connection() as con:
        con.executescript(ai_task_engine._TASK_ENGINE_SCHEMA)
    pitch.engine.cache_clear()
    try:
        first = save(ws)
        args = arguments(ws, "business-source-pitch-01")
        args.pop("shot_plan")
        args.update(profile="source-bound/v3", upstream_ref=first["creation_upstream"])
        pending = pitch.prepare_internal_pitch(**args)
        made = pitch.run_internal_pitch(pending["task_id"], actor=ws["actor"], scope=ws["scope"])
        receipt = made["action_receipt"]
        service = BusinessDecisionWorkflow(internal_action_reader=pitch.read_internal_pitch, action_actor=ws["actor"])
        ws["service"] = service
        action = service.advance(ws["current"]["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
            authorize=ws["authorize"], expected_revision=ws["current"]["revision"], submission_id="actual-business-action",
            operation="action", payload={"option_id": "A", "task_id": pending["task_id"]})
        outcome = service.advance(action["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
            authorize=ws["authorize"], expected_revision=action["revision"], submission_id="actual-business-outcome",
            operation="outcome", payload={"source_job_id": action["source_report"]["job_id"],
                "source_id": ws["options"][0]["source_ids"][0], "quote": ws["citation"]["quote"],
                "limits": "This attributed disclosure is not an observed consumer or campaign effect."})
        assert outcome["action"]["receipt"] == receipt
        assert outcome["evaluation"]["state"] == "RECORDED"
        assert outcome["outcome_state"] == "SOURCE_REPORTED"
        assert outcome["business_outcome"] == "NOT_OBSERVED"
        ws["current"] = outcome
        second = save(ws, request_id="save-business-outcome", parent=first["saved_work"]["artifact"]["artifact_id"],
                      digest=first["saved_work"]["document"]["draft_digest"])
        with ws["repo"].connection(read_only=True, wal=False) as con:
            report = service._report(con, outcome["source_report"]["job_id"], ws["actor_ref"], ws["domain_scope"])
        revised = adopt(ws, report["snapshot"], ws["options"], selection("B", "300"))
        assert revised["action_state"] == "NOT_EXECUTED" and revised["outcome_state"] == "NOT_OBSERVED"
        assert revised["evaluation"]["state"] == "NOT_EVALUATED"
        assert revised["adoption"]["previous_action_ref"] == receipt["artifact_id"]
        assert revised["adoption"]["previous_outcome_revision"] == outcome["revision"]
        historical = service.reopen(outcome["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
                                    authorize=ws["authorize"], revision=outcome["revision"])
        assert historical["action"]["receipt"] == receipt and historical["evaluation"] == outcome["evaluation"]
        assert historical["is_current_revision"] is False
        ws["current"] = revised
        third = save(ws, request_id="save-business-adopted", parent=second["saved_work"]["artifact"]["artifact_id"],
                     digest=second["saved_work"]["document"]["draft_digest"])
        assert third["saved_work"]["document"]["version"] == 3
        original_creation = pitch.read_internal_pitch(pending["task_id"], actor=ws["actor"], scope=ws["scope"])
        original_input = original_creation["work"]["document"]["payload"]["upstream_binding"]["document"]
        assert original_input["payload"]["brief"]["resource_constraints"]["budget_amount"] == "100"
        assert original_input["citations"] == first["saved_work"]["document"]["citations"]
        assert original_creation["action_receipt"] == receipt
        assert ws["repo"].query_one("SELECT count(*) FROM ai_task")[0] == 1
    finally:
        pitch.engine.cache_clear()


def test_wrong_task_quote_missing_quote_and_stale_revision_do_not_save(business):
    ws = business
    with pytest.raises(ValueError, match="BUSINESS_WORK_SAVE_CITATIONS_REQUIRED"):
        save(ws, citations=[])
    _report, citation = add_material(ws, "unselected", "Unselected source must not authorize this task.")
    with pytest.raises(PermissionError, match="BUSINESS_WORK_SAVE_CITATION_NOT_IN_TASK"):
        save(ws, citations=[citation])
    with pytest.raises(RuntimeError, match="BUSINESS_WORK_REVISION_CONFLICT"):
        ws["service"].save_result_request(ws["current"]["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
            authorize=ws["authorize"], expected_revision="app_evidence_records:0", request_id="stale-business-save",
            citations=[ws["citation"]])
    assert ws["repo"].query_one("SELECT count(*) FROM lumenis_shared_artifacts WHERE kind='saved_document'")[0] == 0


def test_adoption_replay_conflict_and_interruption_preserve_history(business):
    ws = business
    report, _citation = add_material(ws, "new-input", "New source for an explicit revised research plan.")
    options = make_options(report["source_brief"]["records"][0]["source_id"])
    old = ws["current"]
    result = adopt(ws, report, options, selection("B", "200"))
    assert adopt(ws, report, options, selection("B", "200"))["revision"] == result["revision"]
    with pytest.raises(ValueError, match="BUSINESS_WORK_SUBMISSION_CONFLICT"):
        adopt(ws, report, options, selection("A", "200"))
    assert result["timeline"][:len(old["timeline"])] == old["timeline"]
    interrupted = ws["service"].advance(result["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=result["revision"], submission_id="interrupt-after-adopt",
        operation="interrupt", payload={"reason": "Interrupted operator editing."})
    with pytest.raises(RuntimeError, match="BUSINESS_WORK_RESUME_REQUIRED"):
        ws["service"].advance(result["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
            authorize=ws["authorize"], expected_revision=interrupted["revision"], submission_id="adopt-while-interrupted",
            operation="adopt", payload={"source_job_id": report["job_id"], "question": result["question"],
                                       "options": options, "decision": selection("A", "200"), "reason": "Changed selection."})
    resumed = ws["service"].advance(result["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], expected_revision=interrupted["revision"], submission_id="resume-after-adopt",
        operation="resume", payload={})
    assert resumed["state"] == "DECIDED" and resumed["adoption"] == result["adoption"]


def test_evaluation_recovery_does_not_change_committed_save_request(business, monkeypatch):
    from lumenis.shared.evaluation import recorder
    ws = business
    decision = ws["current"]
    payload = {"source_job_id": decision["source_report"]["job_id"],
               "source_id": ws["options"][0]["source_ids"][0], "quote": ws["citation"]["quote"],
               "limits": "Attributed source, with no observed business effect."}
    args = {"actor_ref": ws["actor_ref"], "scope": ws["domain_scope"], "authorize": ws["authorize"],
            "expected_revision": decision["revision"], "submission_id": "evaluation-recovery-outcome",
            "operation": "outcome", "payload": payload}
    record = recorder.record_evaluation
    def interrupted_evaluation(*_args, **_kwargs):
        raise RuntimeError("isolated evaluation side-write interruption")
    monkeypatch.setattr(recorder, "record_evaluation", interrupted_evaluation)
    with pytest.raises(RuntimeError, match="evaluation side-write interruption"):
        ws["service"].advance(decision["work_id"], **args)
    ws["current"] = ws["service"].reopen(decision["work_id"], actor_ref=ws["actor_ref"],
                                        scope=ws["domain_scope"], authorize=ws["authorize"])
    assert ws["current"]["evaluation"]["state"] == "PENDING_RECOVERY"
    first = save(ws, request_id="save-before-evaluation-recovery")
    original = first["saved_work"]["document"]
    assert first["current_evaluation"]["state"] == "PENDING_RECOVERY"
    monkeypatch.setattr(recorder, "record_evaluation", record)
    recovered = ws["service"].advance(decision["work_id"], **args)
    assert recovered["revision"] == ws["current"]["revision"]
    assert recovered["evaluation"]["state"] == "RECORDED"
    ws["current"] = recovered
    replay = save(ws, request_id="save-before-evaluation-recovery")
    assert replay["saved_work"]["replayed"]
    assert replay["saved_work"]["document"] == original
    assert replay["creation_upstream"] == first["creation_upstream"]
    assert replay["current_evaluation"]["state"] == "RECORDED"
    assert original["payload"]["business_work"]["evaluation"] == {
        "evaluation_id": recovered["evaluation"]["evaluation_id"], "evidence_ref": recovered["revision"]}
    assert ws["repo"].query_one("SELECT count(*) FROM lumenis_shared_artifacts WHERE kind='saved_document'")[0] == 1


def test_business_work_http_save_adopt_reopen_and_revision_conflict(business, monkeypatch):
    """Exercise the existing HTTP composition against disposable source and Shared stores."""
    import lumenis_app_api
    from lumenis.shared.reporting import saved_work
    from lumenis.system.security import permission

    ws = business
    app = ws["app"]
    app.register_blueprint(lumenis_app_api.domain_api_bp)
    binding = lambda _operation: (ws["service"], ws["actor_ref"], ws["domain_scope"], ws["authorize"])
    monkeypatch.setattr(lumenis_app_api, "_business_work_binding", binding)
    api = app.test_client()
    base = "/api/experience/business-works/" + ws["current"]["work_id"]
    original = ws["current"]
    first_body = {"request_id": "route-save-v1", "expected_revision": original["revision"],
                  "citations": [ws["citation"]]}

    malformed = api.post(base + "/save-request", json={**first_body, "actor": {"id": 7}})
    assert malformed.status_code == 400
    assert ws["repo"].query_one("SELECT count(*) FROM lumenis_shared_artifacts WHERE kind='saved_document'")[0] == 0

    request_response = api.post(base + "/save-request", json=first_body)
    assert request_response.status_code == 200, request_response.get_json()
    request_result = request_response.get_json()["result"]
    assert request_result["state"] == "AWAITING_SHARED_SAVE_PERMISSION"
    assert request_result["publish_status"] == "not_performed"
    assert ws["repo"].query_one("SELECT count(*) FROM lumenis_shared_artifacts WHERE kind='saved_document'")[0] == 0

    # The Shared effect check receives the exact resource returned for this immutable request.
    checks = []
    gate_check = ws["gate"].check
    def capture_check(operation_type, *args, **kwargs):
        if operation_type is permission.OperationType.DATA_EXPORT:
            checks.append(kwargs.get("resource"))
        return gate_check(operation_type, *args, **kwargs)
    monkeypatch.setattr(ws["gate"], "check", capture_check)
    ws["gate"].grant_approval(permission.OperationType.DATA_EXPORT.value,
                              resource=request_result["resource"], granted_by="isolated-test")
    first_response = api.post(base + "/save", json=first_body)
    assert first_response.status_code == 200, first_response.get_json()
    assert checks and set(checks) == {request_result["resource"]}
    first = first_response.get_json()["result"]["saved_work"]
    assert first["document"]["version"] == 1
    assert first["document"]["citations"][0]["evidence_id"] == ws["citation"]["evidence_id"]
    assert first["document"]["payload"]["business_work"]["source_bindings"][0]["evidence_id"] == ws["citation"]["evidence_id"]

    # A second resource request bound to revision 1 cannot be used after adoption creates revision 2.
    stale_body = {"request_id": "route-stale-save", "expected_revision": original["revision"],
                  "citations": [ws["citation"]], "previous_artifact_id": first["artifact"]["artifact_id"],
                  "expected_draft_digest": first["document"]["draft_digest"]}
    stale_request = api.post(base + "/save-request", json=stale_body)
    assert stale_request.status_code == 200, stale_request.get_json()

    replacement_report, replacement_citation = add_material(
        ws, "route-replacement", "Replacement issuer statement. No consumer outcome measured.")
    replacement_source = replacement_report["source_brief"]["records"][0]["source_id"]
    replacement_options = make_options(replacement_source)
    adopt_body = {"submission_id": "route-adopt-v2", "expected_revision": original["revision"],
                  "payload": {"source_job_id": replacement_report["job_id"],
                              "question": original["question"], "options": replacement_options,
                              "decision": selection("B", "200"), "reason": "Adopt the reviewed replacement source."}}
    adopted_response = api.post(base + "/adopt", json=adopt_body)
    assert adopted_response.status_code == 200, adopted_response.get_json()
    adopted = adopted_response.get_json()["result"]
    assert adopted["adoption"]["source_changed"] is True
    assert adopted["revision"] != original["revision"]

    # Server-resolved actor/scope drift is denied before any save side effect.
    wrong_scope = {**ws["domain_scope"], "domain_id": "zbmp" if ws["domain_scope"]["domain_id"] == "cth" else "cth"}
    monkeypatch.setattr(lumenis_app_api, "_business_work_binding",
                        lambda _operation: (ws["service"], ws["actor_ref"], wrong_scope, ws["authorize"]))
    wrong_scope_response = api.get(base)
    assert wrong_scope_response.status_code == 403
    assert wrong_scope_response.get_json()["code"] == "BUSINESS_WORK_AUTHORIZATION_MISMATCH"
    monkeypatch.setattr(lumenis_app_api, "_business_work_binding", binding)

    ws["gate"].grant_approval(permission.OperationType.DATA_EXPORT.value,
                              resource=stale_request.get_json()["result"]["resource"], granted_by="isolated-test")
    stale_save = api.post(base + "/save", json=stale_body)
    assert stale_save.status_code == 409, stale_save.get_json()
    assert stale_save.get_json()["code"] == "BUSINESS_WORK_REVISION_CONFLICT"
    assert ws["repo"].query_one("SELECT count(*) FROM lumenis_shared_artifacts WHERE kind='saved_document'")[0] == 1

    historical = api.get(base, query_string={"revision": original["revision"]})
    assert historical.status_code == 200, historical.get_json()
    assert historical.get_json()["result"]["is_current_revision"] is False
    assert historical.get_json()["result"]["revision"] == original["revision"]

    second_body = {"request_id": "route-save-v2", "expected_revision": adopted["revision"],
                   "citations": [replacement_citation], "previous_artifact_id": first["artifact"]["artifact_id"],
                   "expected_draft_digest": first["document"]["draft_digest"]}
    second_request = api.post(base + "/save-request", json=second_body)
    assert second_request.status_code == 200, second_request.get_json()
    ws["gate"].grant_approval(permission.OperationType.DATA_EXPORT.value,
                              resource=second_request.get_json()["result"]["resource"], granted_by="isolated-test")
    second_response = api.post(base + "/save", json=second_body)
    assert second_response.status_code == 200, second_response.get_json()
    second = second_response.get_json()["result"]["saved_work"]
    assert second["document"]["version"] == 2
    assert second["document"]["parent_artifact_id"] == first["artifact"]["artifact_id"]
    assert second["document"]["citations"][0]["evidence_id"] == replacement_citation["evidence_id"]
    replay = api.post(base + "/save", json=second_body)
    assert replay.status_code == 200, replay.get_json()
    assert replay.get_json()["result"]["saved_work"]["replayed"] is True

    latest = api.get(base)
    assert latest.status_code == 200 and latest.get_json()["result"]["revision"] == adopted["revision"]
    reopened_second = saved_work.reopen_work(second["artifact"]["artifact_id"],
                                             actor=ws["actor"], scope=ws["scope"])
    reopened_first = saved_work.reopen_work(first["artifact"]["artifact_id"],
                                            actor=ws["actor"], scope=ws["scope"])
    assert reopened_first["document"]["version"] == 1
    assert reopened_second["document"]["version"] == 2
    assert reopened_second["document"]["citations"][0]["evidence_id"] == replacement_citation["evidence_id"]
