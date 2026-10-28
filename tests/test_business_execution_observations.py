"""Isolated business records and Shared save; synthetic inputs are not live execution."""
import copy

import pytest

from tests.test_business_result_continuity import add_material, save
from tests.test_business_result_continuity import business as _business
from tests.test_saved_document_workflow import workspace as _workspace

business = _business
workspace = _workspace


def advance(ws, current, operation, payload, submission_id):
    return ws["service"].advance(current["work_id"], actor_ref=ws["actor_ref"],
        scope=ws["domain_scope"], authorize=ws["authorize"], expected_revision=current["revision"],
        operation=operation, payload=payload, submission_id=submission_id)


def source_payload(report, quote):
    return {"source_job_id": report["job_id"],
            "source_id": report["source_brief"]["records"][0]["source_id"], "quote": quote}


def manual_payload(report, quote):
    return {**source_payload(report, quote), "option_id": "A", "performer": "Declared store operator",
            "performed_at": "2026-10-10T10:00:00+08:00", "exact_target": "Declared store service desk",
            "limits": "Operator statement only. No independent verification or external tool execution."}


def observation_payload(report, quote):
    return {**source_payload(report, quote), "observed_at": "2026-10-12T12:00:00+08:00",
            "window": {"start": "2026-10-10T00:00:00+08:00", "end": "2026-10-12T00:00:00+08:00"},
            "metrics": [{"name": "participants", "definition": "Operator-reported participants at one desk.",
                         "value": "0", "unit": "people", "numerator": "0", "denominator": "0"},
                        {"name": "sales", "definition": "No sales evidence was supplied.",
                         "value": None, "unit": "CNY", "numerator": None, "denominator": None}],
            "costs": [{"entry_id": "estimate-1", "kind": "ESTIMATE", "amount": "100", "currency": "CNY", "related_entry_id": None},
                      {"entry_id": "commitment-1", "kind": "COMMITTED", "amount": "50", "currency": "CNY", "related_entry_id": None},
                      {"entry_id": "spend-1", "kind": "ACTUAL", "amount": "20", "currency": "CNY", "related_entry_id": None},
                      {"entry_id": "refund-1", "kind": "REFUND", "amount": "5", "currency": "CNY", "related_entry_id": "spend-1"}],
            "limits": "Transcribed operator observation; no causal or cross-market attribution."}


def count(ws):
    return ws["repo"].query_one("SELECT count(*) FROM app_evidence_records WHERE feature_id=?", (ws["service"].FEATURE,))[0]


@pytest.mark.parametrize("derived", [False, True])
def test_same_source_revision_keeps_prior_observations_and_late_refund_parent(business, derived):
    from tests.test_business_result_continuity import adopt, selection
    from tests.test_business_single_derived_revision import (
        chosen,
        revise,
        revision_payload,
    )

    ws = business
    selected = chosen(ws)[1] if derived else ws["current"]
    report, _ = add_material(ws, "pre-revision-cost", "Prior expense and observation, independently reported.")
    observed = advance(ws, selected, "observation",
        observation_payload(report, "Prior expense and observation, independently reported."), "cost-before-revision")
    original = copy.deepcopy(observed["observation"])
    ws["current"] = observed
    first = save(ws, request_id="save-before-cost-revision",
                 citations=[item["citation"] for item in observed["citation_candidates"]["items"]])["saved_work"]
    if derived:
        payload = revision_payload(observed)
        payload["decision"]["resource_constraints"]["budget_amount"] = "200"
        adopted = revise(ws, observed, payload, "adopt-retaining-cost")
    else:
        adopted = adopt(ws, {"job_id": observed["source_report"]["job_id"]}, ws["options"], selection("B", "200"))
    carried = adopted["observation"]
    assert adopted["state"] == "DECIDED" and adopted["outcome_state"] == "PRIOR_OBSERVATION_ONLY"
    assert adopted["action_state"] == "NOT_EXECUTED" and adopted["business_outcome"] == "NOT_OBSERVED"
    assert adopted["evaluation"]["state"] == "NOT_EVALUATED" and "execution_records" not in adopted
    for key in ("source_claim", "metrics", "metric_observations", "cost_ledger", "cost_totals", "window", "observed_at"):
        assert carried[key] == original[key]
    assert carried["adoption_lineage"]["prior_revision"] == observed["revision"]
    assert carried["resource_result"]["remaining_budget_amount"] == "185"
    assert "不是修订方案的新效果" in adopted["usable_result"]["markdown"]
    old = ws["service"].reopen(observed["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
        authorize=ws["authorize"], revision=observed["revision"])
    assert old["observation"] == original
    adopted = advance(ws, adopted, "choose", selection(adopted["decision"]["option_id"], "300"), "rechoose-with-prior-cost")
    assert adopted["observation"]["cost_ledger"] == original["cost_ledger"]
    assert adopted["observation"]["resource_result"]["remaining_budget_amount"] == "285"
    refund = observation_payload(report, "Prior expense and observation, independently reported.")
    refund["metrics"] = []
    refund["costs"] = [{"entry_id": "refund-after-revision", "kind": "REFUND", "amount": "5", "currency": "CNY",
                        "related_entry_id": "spend-1"}]
    after = advance(ws, adopted, "observation", refund, "refund-after-plan-change")
    assert after["observation"]["cost_totals"]["CNY"]["net_actual"] == "10"
    assert after["observation"]["metrics"] == original["metrics"]
    assert after["observation"]["cost_ledger"][:4] == original["cost_ledger"]
    ws["current"] = after
    second = save(ws, request_id="save-refund-after-revision", parent=first["artifact"]["artifact_id"],
        digest=first["document"]["draft_digest"], citations=[item["citation"] for item in after["citation_candidates"]["items"]])
    assert second["saved_work"]["document"]["work_id"] == first["document"]["work_id"]
    assert second["saved_work"]["document"]["version"] == 2


@pytest.mark.parametrize("replace_source", [False, True])
def test_revision_revalidates_retained_observations_without_binding_new_sources(business, monkeypatch, replace_source):
    from tests.test_business_result_continuity import adopt, make_options, selection

    ws = business
    report, _ = add_material(ws, "withdrawn-prior-cost", "Prior cost source whose access can be withdrawn.")
    observed = advance(ws, ws["current"], "observation",
        observation_payload(report, "Prior cost source whose access can be withdrawn."), "cost-before-withdrawal")
    ws["current"] = observed
    replacement, _ = add_material(ws, "replacement-plan-source", "Independent replacement planning source.")
    original_report = ws["service"]._report
    def read_report(connection, job_id, *args, **kwargs):
        if job_id == report["job_id"]:
            raise PermissionError("PRIOR_OBSERVATION_WITHDRAWN")
        return original_report(connection, job_id, *args, **kwargs)
    monkeypatch.setattr(ws["service"], "_report", read_report)
    before = count(ws)
    if replace_source:
        changed = adopt(ws, replacement, make_options(replacement["source_brief"]["records"][0]["source_id"]), selection("B", "200"))
        assert "observation" not in changed
        assert changed["outcome_state"] == changed["business_outcome"] == "NOT_OBSERVED"
        assert count(ws) == before + 1
    else:
        with pytest.raises(PermissionError, match="PRIOR_OBSERVATION_WITHDRAWN"):
            adopt(ws, {"job_id": observed["source_report"]["job_id"]}, ws["options"], selection("B", "200"))
        assert count(ws) == before


def test_manual_execution_observation_save_reopen_and_historical_recovery(business):
    ws = business
    report, _ = add_material(ws, "execution", "Operator states the desk opened. No independent verification.")
    payload = manual_payload(report, "Operator states the desk opened.")
    selected = ws["current"]
    recorded = advance(ws, selected, "manual_action", payload, "manual-execution-01")
    assert recorded["action_state"] == "MANUALLY_REPORTED" and recorded.get("action") is None
    receipt = recorded["execution_records"][0]
    assert receipt["execution_state"] == "REPORTED_PERFORMED"
    assert receipt["external_effect"] == "NOT_PERFORMED_BY_LUMENIS"
    assert receipt["independent_verification"] == "NOT_VERIFIED"
    assert advance(ws, selected, "manual_action", payload, "manual-execution-01") == recorded
    report2, _ = add_material(ws, "observation", "Operator reports 0 participants; spent 20 CNY and received 5 CNY refund.")
    observation = observation_payload(report2, "Operator reports 0 participants; spent 20 CNY and received 5 CNY refund.")
    current = advance(ws, recorded, "observation", observation, "observation-execution-01")
    assert current["business_outcome"] == "SOURCE_REPORTED_NOT_ATTRIBUTED"
    assert current["evaluation"]["state"] == "RECORDED"
    assert current["evaluation"]["business_usefulness"] == "UNKNOWN"
    observed = current["observation"]
    assert observed["metrics"][0]["value"] == "0"
    assert observed["metrics"][0]["ratio"] is None
    assert observed["metrics"][0]["ratio_state"] == "ZERO_DENOMINATOR"
    assert observed["metrics"][1]["value"] is None
    assert observed["cost_totals"]["CNY"] == {"ESTIMATE": "100", "COMMITTED": "50", "ACTUAL": "20", "REFUND": "5", "net_actual": "15"}
    assert observed["causation"] == "NOT_ESTABLISHED" and observed["attribution"] == "NOT_ESTABLISHED"
    candidates = current["citation_candidates"]
    assert candidates["source_count"] == 3 and len(candidates["items"]) == 3
    assert candidates["export_authorization"] == "NOT_GRANTED"
    ws["current"] = current
    exported = save(ws, citations=[item["citation"] for item in candidates["items"]])
    stored = exported["saved_work"]["document"]["payload"]["business_work"]
    assert stored["execution_records"] == current["execution_records"]
    assert stored["observation"] == observed and len(stored["source_bindings"]) == 3
    assert "尚未独立核实" in exported["saved_work"]["document"]["markdown"]
    reopened = ws["service"].reopen(current["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
                                    authorize=ws["authorize"])
    assert reopened["observation"] == current["observation"]
    assert reopened["saved_results"]["latest"]["artifact_id"] == exported["saved_work"]["artifact"]["artifact_id"]
    assert reopened["saved_results"]["latest"]["draft_digest"] == exported["saved_work"]["document"]["draft_digest"]
    assert observed["resource_result"]["remaining_budget_amount"] == "85"
    assert observed["resource_result"]["state"] == "WITHIN_OPERATOR_BUDGET"
    original = ws["service"].reopen(current["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
                                    authorize=ws["authorize"], revision=selected["revision"])
    assert "execution_records" not in original and "observation" not in original
    listed = ws["service"].list_recent(actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"])
    assert listed["items"][0]["work_id"] == current["work_id"]
    assert listed["items"][0]["availability"] == "AVAILABLE"
    # A fresh read supplies the exact Shared parent for the next user save.
    followup = copy.deepcopy(observation)
    followup["observed_at"] = "2026-10-13T12:00:00+08:00"
    followup["costs"] = []
    ws["current"] = advance(ws, current, "observation", followup, "followup-observation-01")
    latest = ws["current"]["saved_results"]["latest"]
    revised = save(ws, request_id="save-followup-observation", parent=latest["artifact_id"], digest=latest["draft_digest"],
                   citations=[item["citation"] for item in ws["current"]["citation_candidates"]["items"]])
    reopened = ws["service"].reopen(current["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"])
    assert [item["version"] for item in reopened["saved_results"]["items"]] == [1, 2]
    assert reopened["saved_results"]["latest"]["artifact_id"] == revised["saved_work"]["artifact"]["artifact_id"]


@pytest.mark.parametrize("fault", ["wrong_option", "missing_quote", "naive_time", "foreign_source", "blank_target"])
def test_invalid_manual_receipt_never_records_execution(business, fault):
    ws = business
    report, _ = add_material(ws, "manual-invalid", "Operator declaration.")
    payload = manual_payload(report, "Operator declaration.")
    if fault == "wrong_option":
        payload["option_id"] = "B"
    elif fault == "missing_quote":
        payload["quote"] = "Not present in the source."
    elif fault == "naive_time":
        payload["performed_at"] = "2026-10-10T10:00:00"
    elif fault == "foreign_source":
        payload["source_id"] = "unadmitted-source"
    else:
        payload["exact_target"] = ""
    before = count(ws)
    with pytest.raises((ValueError, PermissionError, RuntimeError)):
        advance(ws, ws["current"], "manual_action", payload, "invalid-manual-01")
    assert count(ws) == before


@pytest.mark.parametrize("fault", ["float", "negative_cost", "reversed_window", "future_window", "naive_window", "ratio_missing", "duplicate_metric", "refund_currency", "refund_excess", "duplicate_refund"])
def test_observation_invalid_window_metric_and_costs_roll_back(business, fault):
    ws = business
    report, _ = add_material(ws, "observation-invalid", "Synthetic observation for validation only.")
    payload = observation_payload(report, "Synthetic observation for validation only.")
    if fault == "float":
        payload["metrics"][0]["value"] = 0.0
    elif fault == "negative_cost":
        payload["costs"][2]["amount"] = "-1"
    elif fault == "reversed_window":
        payload["window"]["end"] = payload["window"]["start"]
    elif fault == "future_window":
        payload["observed_at"] = payload["window"]["start"]
    elif fault == "naive_window":
        payload["window"]["start"] = "2026-10-10T00:00:00"
    elif fault == "ratio_missing":
        payload["metrics"][0]["denominator"] = None
    elif fault == "duplicate_metric":
        payload["metrics"].append(copy.deepcopy(payload["metrics"][0]))
    elif fault == "refund_currency":
        payload["costs"][-1]["currency"] = "USD"
    elif fault == "refund_excess":
        payload["costs"][-1]["amount"] = "21"
    elif fault == "duplicate_refund":
        payload["costs"].append(copy.deepcopy(payload["costs"][-1]))
    before = count(ws)
    with pytest.raises(ValueError):
        advance(ws, ws["current"], "observation", payload, "invalid-observation-01")
    assert count(ws) == before


def test_late_refund_and_lost_evaluation_ack_do_not_repeat_actual_costs(business, monkeypatch):
    from lumenis.shared.evaluation import recorder
    ws = business
    report, _ = add_material(ws, "late-refund", "Synthetic operator costs; delayed refund declared later.")
    payload = observation_payload(report, "Synthetic operator costs; delayed refund declared later.")
    first = advance(ws, ws["current"], "observation", payload, "initial-cost-observation")
    late = copy.deepcopy(payload)
    late["observed_at"] = "2026-10-13T12:00:00+08:00"
    late["costs"] = [{"entry_id": "refund-2", "kind": "REFUND", "amount": "5", "currency": "CNY", "related_entry_id": "spend-1"}]
    original = recorder.record_evaluation
    monkeypatch.setattr(recorder, "record_evaluation", lambda **kw: (_ for _ in ()).throw(OSError("lost evaluation ack")))
    with pytest.raises(OSError, match="lost evaluation ack"):
        advance(ws, first, "observation", late, "late-cost-observation")
    after_commit = count(ws)
    monkeypatch.setattr(recorder, "record_evaluation", original)
    recovered = advance(ws, first, "observation", late, "late-cost-observation")
    assert recovered["observation"]["cost_totals"]["CNY"]["net_actual"] == "10"
    assert recovered["evaluation"]["state"] == "RECORDED" and count(ws) == after_commit
    duplicate = advance(ws, recovered, "observation", late, "same-refund-readback")
    assert len(duplicate["observation"]["cost_ledger"]) == 5
    conflict = copy.deepcopy(late)
    conflict["costs"][0]["amount"] = "6"
    before = count(ws)
    with pytest.raises(ValueError, match="COST_ID_CONFLICT"):
        advance(ws, duplicate, "observation", conflict, "refund-conflict-01")
    assert count(ws) == before
    old = ws["service"].reopen(first["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"],
                               authorize=ws["authorize"], revision=first["revision"])
    assert old["observation"]["cost_totals"]["CNY"]["net_actual"] == "15"


def test_recent_index_does_not_expose_withdrawn_content_or_other_actor(business, monkeypatch):
    ws = business
    service = ws["service"]
    original = service.reopen
    monkeypatch.setattr(service, "reopen", lambda *a, **k: (_ for _ in ()).throw(PermissionError("private title")))
    listed = service.list_recent(actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"])
    assert listed["state"] == "PARTIAL"
    assert listed["items"] == [{"work_id": ws["current"]["work_id"], "availability": "UNAVAILABLE",
                                "reason": "CURRENT_SOURCE_OR_PERMISSION_UNAVAILABLE"}]
    monkeypatch.setattr(service, "reopen", original)
    def other_authorize(operation):
        return {"actor_id": "other-workspace", "scope": ws["domain_scope"], "operation": operation,
                "permission_audit_ref": "other-scope", "operation_audit_ref": "other-audit"}
    assert service.list_recent(actor_ref="other-workspace", scope=ws["domain_scope"], authorize=other_authorize)["items"] == []
    with pytest.raises(ValueError, match="LIST_LIMIT"):
        service.list_recent(actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"], limit=31)


def test_budget_and_reported_comparison_keep_units_unknowns_and_exact_money():
    from api_dual_domain import BusinessDecisionWorkflow
    service = BusinessDecisionWorkflow()
    decision = {"resource_constraints": {"budget_amount": "100", "currency": "CNY", "as_of": "2026-10-01T00:00:00Z", "estimated_cost_amount": "50"}}
    prior = {"source_claim": {"source_id": "baseline"},
             "window": {"start": "2026-10-10T00:00:00Z", "end": "2026-10-11T00:00:00Z"},
             "metrics": [{"name": "visitors", "definition": "Declared entrance counts", "unit": "people", "value": "0"}]}
    observation = {"window": {"start": "2026-10-11T00:00:00Z", "end": "2026-10-12T00:00:00Z"},
                   "metrics": [{"name": "visitors", "definition": "Declared entrance counts", "unit": "people", "value": "20"}],
                   "cost_totals": {"CNY": {"ACTUAL": "120", "REFUND": "5", "net_actual": "115"}}}
    result = service._observation_result(observation, decision, prior, "app_evidence_records:1")
    assert result["resource_result"]["remaining_budget_amount"] == "-15"
    assert result["resource_result"]["state"] == "OVER_OPERATOR_BUDGET"
    compared = result["comparison"]["items"][0]
    assert compared["difference"] == "20" and compared["relative_change"] is None
    assert compared["reason"] == "ZERO_BASELINE_RELATIVE_CHANGE_UNKNOWN"
    assert result["comparison"]["causation"] == "NOT_ESTABLISHED"
    changed = copy.deepcopy(observation)
    changed["metrics"][0]["unit"] = "visits per hour"
    assert service._observation_result(changed, decision, prior, "old")["comparison"]["items"][0]["difference"] is None
    changed = copy.deepcopy(observation)
    changed["cost_totals"]["USD"] = {"ACTUAL": "1", "REFUND": None, "net_actual": "1"}
    partial = service._observation_result(changed, decision, None, None)["resource_result"]
    assert partial["state"] == "PARTIAL_CURRENCY_CONVERSION_REQUIRED"
    assert partial["unconverted_cost_currencies"] == ["USD"]
    unknown = service._observation_result({**observation, "cost_totals": {}}, decision, None, None)["resource_result"]
    assert unknown["reported_net_actual_amount"] is None and unknown["remaining_budget_amount"] is None
    assert str(service._money_sum(["99999999999999999999999999999999999999", "1"])) == "100000000000000000000000000000000000000"


def test_refund_batch_order_does_not_change_cost_identity(business):
    ws = business
    report, _ = add_material(ws, "refund-before-spend", "Synthetic spend and refund statements.")
    payload = observation_payload(report, "Synthetic spend and refund statements.")
    payload["costs"].reverse()
    current = advance(ws, ws["current"], "observation", payload, "unordered-cost-observation")
    assert current["observation"]["cost_totals"]["CNY"]["net_actual"] == "15"


def test_available_source_choices_use_owner_pagination_and_exact_original_offsets(business, monkeypatch):
    ws = business
    second, _ = add_material(ws, "choice-second", "Second admitted execution material.")
    third, _ = add_material(ws, "choice-third", "Third admitted observation material.")
    service = ws["service"]
    args = {"actor_ref": ws["actor_ref"], "scope": ws["domain_scope"], "authorize": ws["authorize"], "limit": 1}
    first_page = service.available_sources(**args)
    assert first_page["has_more"] and first_page["next_cursor"]
    assert first_page["items"][0]["job_id"] == third["job_id"]
    candidate = first_page["items"][0]["citation_candidates"]["items"][0]
    citation = candidate["citation"]
    assert citation["quote"] == "Third admitted observation material."
    assert citation["start"] == 0 and citation["end"] == len(citation["quote"])
    second_page = service.available_sources(**args, cursor=first_page["next_cursor"])
    assert second_page["items"][0]["job_id"] == second["job_id"]
    assert first_page["items"][0]["job_id"] != second_page["items"][0]["job_id"]
    original = service._report
    def withdrawn(connection, job_id, actor_ref, scope, **kwargs):
        if job_id == third["job_id"]:
            raise PermissionError("withdrawn private statement")
        return original(connection, job_id, actor_ref, scope, **kwargs)
    monkeypatch.setattr(service, "_report", withdrawn)
    unavailable = service.available_sources(**args)
    assert unavailable["state"] == "PARTIAL" and unavailable["read_complete"] is False
    assert unavailable["items"] == [{"job_id": third["job_id"], "availability": "UNAVAILABLE",
                                      "reason": "CURRENT_SOURCE_USE_UNAVAILABLE"}]


def test_cost_increment_preserves_metric_identity_source_window_and_saved_history(business, monkeypatch):
    ws = business
    metric_report, _ = add_material(ws, "metric-original", "Operator reports zero desk participants in the original window.")
    first_payload = observation_payload(metric_report, "Operator reports zero desk participants in the original window.")
    first_payload["costs"] = []
    first = advance(ws, ws["current"], "observation", first_payload, "metric-original-observation")
    cost_report, _ = add_material(ws, "cost-later", "Operator declares a later payment of 9 CNY.")
    later = observation_payload(cost_report, "Operator declares a later payment of 9 CNY.")
    later["window"] = {"start": "2026-10-13T00:00:00+08:00", "end": "2026-10-14T00:00:00+08:00"}
    later["observed_at"] = "2026-10-14T12:00:00+08:00"
    later["metrics"] = []
    later["costs"] = [{"entry_id": "actual-increment", "kind": "ACTUAL", "amount": "9", "currency": "CNY", "related_entry_id": None}]
    current = advance(ws, first, "observation", later, "cost-increment-observation")
    observation = current["observation"]
    assert observation["metrics"] == first["observation"]["metrics"]
    assert observation["metric_updates"] == []
    assert observation["metric_observations"] == first["observation"]["metric_observations"]
    metric = observation["metrics"][0]
    assert metric["source_claim"]["source_job_id"] == metric_report["job_id"]
    assert metric["window"] == first_payload["window"] and metric["observed_at"] == first_payload["observed_at"]
    assert observation["source_claim"]["source_job_id"] == cost_report["job_id"]
    assert observation["cost_ledger"][0]["source_claim"]["source_job_id"] == cost_report["job_id"]
    assert observation["comparison"]["state"] == "NO_NEW_METRIC_OBSERVATION"
    assert observation["comparison"]["items"] == []
    ws["current"] = current
    saved = save(ws, citations=[item["citation"] for item in current["citation_candidates"]["items"]])
    stored = saved["saved_work"]["document"]["payload"]["business_work"]["observation"]
    assert stored["metrics"][0]["source_claim"] == metric["source_claim"]
    assert stored["cost_ledger"][0]["source_claim"] != metric["source_claim"]
    assert len(saved["saved_work"]["document"]["payload"]["business_work"]["source_bindings"]) == 3
    manual = advance(ws, current, "manual_action", manual_payload(cost_report, later["quote"]), "next-manual-execution")
    assert manual["outcome_state"] == "PRIOR_OBSERVATION_ONLY"
    assert manual["observation"]["cost_ledger"] == observation["cost_ledger"]
    assert manual["observation"]["metrics"] == observation["metrics"]
    reader = ws["service"]._report
    def withdrawn(connection, job_id, actor_ref, scope, **kwargs):
        if job_id == metric_report["job_id"]:
            raise PermissionError("original metric source withdrawn")
        return reader(connection, job_id, actor_ref, scope, **kwargs)
    monkeypatch.setattr(ws["service"], "_report", withdrawn)
    with pytest.raises(PermissionError, match="metric source withdrawn"):
        ws["service"].reopen(current["work_id"], actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"])
