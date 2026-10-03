"""Domain decision/recovery integration; synthetic inputs are not user acceptance."""
import copy
import json
import sqlite3

import pytest

from tests.test_source_brief_job import job_db
from canonical_data import CanonicalRecord, persist_canonical
from lumenis.shared.evidence import store
from lumenis.shared.reporting.source_brief_job import create_source_brief_job
from api_dual_domain import BusinessDecisionWorkflow
from tests.test_source_brief_job_routes import client as report_client, GLOBAL, URL
from tests.test_cth_case_routes import case_client


@pytest.fixture(params=["CTH", "ZBMP"])
def work(job_db, request, monkeypatch):
    from lumenis.shared.reporting.business_brief import ai_core
    monkeypatch.setattr(ai_core, "local_structured_chat", lambda *a, **k: pytest.fail("retired provider invoked"))
    product = request.param
    domain = "cth" if product == "CTH" else "zbmp"
    args = {"product_id": product, "global_scope": False, "entity_label": "Isolated focus",
            "subject_id": "VENUE-A" if product == "CTH" else None,
            "brand_focus_id": "BRAND-A" if product == "ZBMP" else None}
    with sqlite3.connect(job_db) as con:
        con.row_factory = sqlite3.Row
        ref = store.record_evidence(connection=con, source="isolated_test", project="LUMENIS",
                                    product=product, domain_id=domain, subject_id=args["subject_id"],
                                    brand_focus_id=args["brand_focus_id"], global_scope=False,
                                    feature_id="TEST_SOURCE", result="PASS", status="verified",
                                    inputs={"source_ids": ["decision-source"],
                                            "source_role": "OFFICIAL_BRAND_SELF_DESCRIPTION" if product == "ZBMP" else "VENUE_OPERATOR_DISCLOSURE"},
                                    outputs={"test": True})
        persist_canonical(con, CanonicalRecord(
            canonical_id="decision-source-canonical", source_id="decision-source", product_id=product,
            domain_id=domain, subject_id=args["subject_id"], brand_focus_id=args["brand_focus_id"],
            scope_status="VERIFIED", scope_evidence_ref=str(ref), source_type="web_mention",
            source_platform="web", title="Attributed test statement", content="The source reports zero participants.",
            url="https://example.org/isolated-test", captured_at="2026-10-02T00:00:00Z"))
        con.commit()
        report = create_source_brief_job(con, **args, actor_id="workspace:local", permission_audit_ref="audit:test",
                                        trace_id="trace-test-decision", job_id="job-decision-test")
    scope = report["source_brief"]["scope"]
    def authorize(operation):
        return {"actor_id": "workspace:local", "scope": scope, "operation": operation,
                "permission_audit_ref": "audit:isolated-test", "operation_audit_ref": "effect:isolated-test"}
    options = [{"option_id": name, "proposal": "Proposed reversible research activity " + name,
                "rationale": "One source does not establish consumer demand.", "source_ids": ["decision-source"],
                "assumptions": ["Participants might consent; not confirmed."],
                "unknowns": ["Commercial material rights and actual demand are unknown."],
                "check": "Record consenting participants' unaided reasons; stop if inputs are insufficient."}
               for name in ["A", "B"]]
    service = BusinessDecisionWorkflow()
    inputs = {"actor_ref": "workspace:local", "scope": scope, "submission_id": "prepare-request-01",
              "source_job_id": report["job_id"], "kind": "venue_operations" if product == "CTH" else "brand_market",
              "question": "Which bounded option should the operator investigate next?",
              "options": options, "authorize": authorize}
    return service, inputs, job_db


def step(service, inputs, current, operation, payload, submission_id):
    return service.advance(current["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"],
                           authorize=inputs["authorize"], expected_revision=current["revision"],
                           submission_id=submission_id, operation=operation, payload=payload)


def choose(service, inputs, current):
    return step(service, inputs, current, "choose", {"option_id": "B", "reason": "Explore the smaller reversible option.",
                "owner": "Consenting operator", "review_at": "2026-10-05T12:00:00+08:00"}, "choose-request-01")


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
    payload = {"source_job_id": inputs["source_job_id"], "source_id": "decision-source",
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
    payload = {"source_job_id": inputs["source_job_id"], "source_id": "decision-source",
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
    payload = {"source_job_id": inputs["source_job_id"], "source_id": "decision-source",
               "quote": "The source reports zero participants.", "limits": "Not a campaign measurement."}
    real = recorder.record_evaluation
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
    payload = {"source_job_id": inputs["source_job_id"], "source_id": "decision-source",
               "quote": "The source reports zero participants.", "limits": "Not a causal attribution."}
    result = step(service, inputs, selected, "outcome", payload, "outcome-source-01")
    with sqlite3.connect(db) as con:
        con.execute("UPDATE canonical_data SET content='Changed source body'")
    with pytest.raises(RuntimeError, match="OUTCOME_SOURCE_CHANGED"):
        service.reopen(result["work_id"], actor_ref=inputs["actor_ref"], scope=inputs["scope"], authorize=inputs["authorize"])


def test_existing_cth_case_continues_into_decision_without_replacing_case(case_client):
    from api_dual_domain import authorize_business_work_request
    api, app, db, headers, body, _ = case_client
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
                    "engagement_collects=0, engagement_shares=0 WHERE source_id='decision-source'")
    reopened = service.reopen(current["work_id"], actor_ref=inputs["actor_ref"],
                              scope=inputs["scope"], authorize=inputs["authorize"])
    metric = reopened["material_review"]["sources"][0]["engagement"]
    assert metric["value"] == 0 and metric["state"] == "COMPLETE_INPUT"
    with sqlite3.connect(db) as con:
        con.execute("UPDATE canonical_data SET engagement_shares=NULL WHERE source_id='decision-source'")
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
                    "engagement_collects=0, engagement_shares=0 WHERE source_id='decision-source'")
    reopened = service.reopen(current["work_id"], actor_ref=inputs["actor_ref"],
                              scope=inputs["scope"], authorize=inputs["authorize"])
    assert "来源互动字段合计：0" in reopened["usable_result"]["markdown"]
    assert "不代表客流、需求、销量或投放回报" in reopened["usable_result"]["markdown"]


def test_readable_result_withholds_credential_or_unapproved_query_urls(work):
    service, inputs, db = work
    with sqlite3.connect(db) as con:
        con.execute("UPDATE canonical_data SET url=? WHERE source_id='decision-source'",
                    ("https://example.org/source?token=TEST_ONLY_CANARY",))
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


def test_focus_lens_global_aggregate_gap_is_explicit(related_work):
    service, current, args, _ = related_work
    descriptor = copy.deepcopy(args["related_reports"][0])
    descriptor["original_scope"]["global"] = True
    with pytest.raises(RuntimeError, match="GLOBAL_REPORT_SOURCE_SCOPE_OWNER_REQUIRED"):
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
