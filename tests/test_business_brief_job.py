"""Exact authorized Canonical body -> signed draft -> artifact/reopen boundaries."""
import json
import sqlite3

import pytest

from tests.test_source_brief_job_routes import client, GLOBAL, URL
from tests.test_source_brief_job import job_db
from tests.business_brief_fixture import (
    attach_legacy_brief_to_job, prepare_synthetic_content_sources,
)
from lumenis.shared.reporting import business_brief as analysis


def test_excerpt_selection_retains_short_source_context_and_merges_tiny_tail():
    short = "An attributed social post; this is not an internal disclosure. " * 5
    assert analysis._excerpts({"text": short}) == [short]
    long = "A" * 800 + "person-name."
    excerpts = analysis._excerpts({"text": long})
    assert ''.join(excerpts) == long
    assert len(excerpts) == 2 and all(100 <= len(item) <= 500 for item in excerpts)


def _answer(payload):
    source = json.loads(payload)["sources"][0]
    value = {"source_observations": [{"source_id": source["source_id"], "excerpt_index": 0}],
            "interpretations": [{"text": "This source alone cannot establish consumer demand.", "source_ids": [source["source_id"]]}],
            "proposed_actions": [{"action": "Check the proposed content with the team.", "reason": "Only one source is available.",
                                  "check": "Ask for actual customer feedback before promotion.", "source_ids": [source["source_id"]]}],
            "unknowns": ["Sales and customer sentiment are unknown."]}
    if analysis._VERSION in analysis._PILOT_VERSIONS:
        value["proposed_actions"][0]["pilot"] = {
            "audience": "Propose inviting five consenting participants.",
            "procedure": "Show two draft concepts in alternating order during one interview round.",
            "measure": "Record each person's unaided interpretation, preference and reason.",
            "continue_if": "Explore the concept further only if its intended meaning is understood.",
            "stop_if": "Revise if misunderstood; draw no conclusion if feedback is insufficient.",
        }
    return value


def _mock_model(monkeypatch, client, transform=lambda value: value):
    from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest
    from tests.test_business_brief_typed_owned import _owned_result

    prepared = prepare_synthetic_content_sources(client, monkeypatch)
    class SourceCalls(list):
        pass
    calls = SourceCalls()
    calls.source_ids = prepared["source_ids"]
    def run_owned(request):
        assert type(request) is OwnedServiceRequest
        assert request.operation == "business_brief"
        assert request.max_output_tokens == 4096
        payload = json.loads(request.user_payload)
        calls.append(payload)
        result = transform(_answer(request.user_payload))
        if "revision" in payload:
            result = {"changes": [{"section": "unknowns", "reason": "Address the saved review."}],
                      "analysis": result}
        return _owned_result(request, actor=prepared["actor"], analysis=result)

    monkeypatch.setattr(analysis.gateway, "run_owned_request", run_owned)
    return calls


def test_real_route_derivative_and_reopen_are_scoped_immutable_not_business_success(client, monkeypatch):
    api, app, path, entry, _ = client
    calls = _mock_model(monkeypatch, client)
    focus = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    result = api.post(URL + "/generate", headers=focus, json={
        "business_question": "What should this venue do next, and what information is missing?",
    })
    assert result.status_code == 200, result.get_json()
    job = result.get_json()["result"]
    draft = job["business_analysis"]
    assert draft["state"] == "draft", draft
    assert draft["review_status"] == "HUMAN_PENDING"
    assert draft["outcome_state"] == "NOT_OBSERVED" and draft["action_state"] == "NOT_EXECUTED"
    assert set(draft["analysis"]["proposed_actions"][0]["pilot"]) == set(analysis._PILOT_FIELDS)
    assert "待确认的小规模试验（尚未执行）" in draft["markdown"]
    assert len(calls) == 1 and calls[0]["sources"][0]["excerpts"][0].startswith("Private source body")
    assert draft["sample"]["coverage"] == "PARTIAL"
    assert job["source_brief"]["records"][0].get("text") is None
    assert "NOT_OBSERVED" not in job["source_brief"]["markdown"]
    reopened = app.test_client().get(URL + "/jobs/" + job["job_id"], headers=focus)
    assert reopened.get_json()["result"] == job and len(calls) == 1
    assert api.get(URL + "/jobs/" + job["job_id"], headers=GLOBAL).status_code == 403
    # A stored signature failure must block replay, even if its report hash stays valid.
    evidence_id = int(draft["evidence_ref"].split(":")[1])
    with sqlite3.connect(path) as con:
        con.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?", (evidence_id,))
    assert api.get(URL + "/jobs/" + job["job_id"], headers=focus).status_code != 200


@pytest.mark.parametrize("question,material", [
    ("Compare cushioning traction weight and durability", "Cushioning traction weight durability measured in this test."),
    ("比较缓震抓地耐久重量", "缓震、抓地、耐久、重量的实测结果在此。"),
])
def test_real_job_selects_task_material_beyond_article_prefix(client, monkeypatch, question, material):
    api, _, path, entry, _ = client
    body = "Navigation and unrelated introduction. " * 100 + material + " Method and limits. " * 50
    with sqlite3.connect(path) as con:
        con.execute("UPDATE canonical_data SET content=? WHERE source_id='brief-job-source'", (body,))
    calls = _mock_model(monkeypatch, client)
    focus = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    response = api.post(URL + "/generate", headers=focus, json={
        "source_ids": [calls.source_ids["brief-job-source"]], "business_question": question,
    })
    assert response.status_code == 200, response.get_json()
    job = response.get_json()["result"]
    source_text = "".join(calls[0]["sources"][0]["excerpts"])
    assert material in source_text and source_text in body and len(source_text) <= 1200
    assert job["business_analysis"]["sample"]["has_truncated_bodies"] is True
    assert api.get(URL + "/jobs/" + job["job_id"], headers=focus).get_json()["result"] == job


def test_no_lexical_match_does_not_claim_semantic_relevance():
    from lumenis.shared.reporting.operational_brief import _analysis_window
    body = "Original source text. " * 100
    text, selection = _analysis_window(body, "无关的问题")
    assert text == body[:1200]
    assert selection["matched_query_terms"] == 0
    assert selection["semantic_relevance"] == "NOT_EVALUATED"


@pytest.mark.parametrize("missing_body", [False, True])
def test_explicit_materials_bind_model_input_or_fail_without_partial_analysis(client, monkeypatch, missing_body):
    from tests.test_source_brief_job import _source
    api, _, path, entry, _ = client
    with sqlite3.connect(path) as con:
        _source(con, "selected-older", subject=entry["subject_id"])
        _source(con, "unselected", subject=entry["subject_id"])
        con.execute("UPDATE canonical_data SET captured_at='2020-01-01' WHERE source_id='selected-older'")
        if missing_body:
            con.execute("UPDATE canonical_data SET content='' WHERE source_id='selected-older'")
    calls = _mock_model(monkeypatch, client)
    selected = [calls.source_ids[name] for name in ("selected-older", "brief-job-source")]
    focus = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    response = api.post(URL + "/generate", headers=focus, json={
        "source_ids": selected, "limit": 2, "business_question": "Propose a content research direction.",
    })
    assert response.status_code == 200, response.get_json()
    job = response.get_json()["result"]
    assert job["requested_source_ids"] == selected
    assert job["artifact_outcome"]["source_count"] == 2
    if missing_body:
        assert calls == []
        assert job["business_analysis"]["reason"] == "SOURCE_BRIEF_SELECTED_BODY_UNAVAILABLE"
    else:
        assert [source["source_id"] for source in calls[0]["sources"]] == selected
        assert job["business_analysis"]["state"] == "draft"
        assert job["business_analysis"]["sample"]["omitted_source_count"] == 0


@pytest.mark.parametrize("bad", ["made_up_excerpt", "foreign_source", "missing_excerpt_index"])
def test_model_cannot_invent_quote_or_cite_other_scope(client, monkeypatch, bad):
    def corrupt(value):
        if bad == "made_up_excerpt":
            value["source_observations"][0]["excerpt"] = "Sales increased 999 percent."
        elif bad == "missing_excerpt_index":
            value["source_observations"][0]["excerpt_index"] = 6
        else:
            value["proposed_actions"][0]["source_ids"] = ["OTHER-BRAND"]
        return value
    api, _, path, _, _ = client
    _mock_model(monkeypatch, client, corrupt)
    result = api.post(URL + "/generate", headers=GLOBAL, json={"business_question": "Recommend an operating action."})
    job = result.get_json()["result"]
    assert job["business_analysis"]["state"] == "unavailable"
    assert job["business_analysis"]["real_input_bound"] is False
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS'").fetchone()[0] == 0
        rejected = con.execute("SELECT result,outputs_json FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS_REJECTED'").fetchone()
        assert rejected[0] == 'FAIL' and 'rejected_model_output' in json.loads(rejected[1])


@pytest.mark.parametrize("failure_code,reason", [
    ("OWNED_SERVICE_TIMEOUT", "BUSINESS_BRIEF_OWNED_SERVICE_TIMEOUT"),
    (None, "BUSINESS_BRIEF_OWNED_SERVICE_FAILED"),
])
def test_unavailable_owned_service_is_reopenable_without_fake_analysis_or_retry(
    client, monkeypatch, failure_code, reason,
):
    api, _, path, _, _ = client
    prepare_synthetic_content_sources(client, monkeypatch)
    calls = []
    def unavailable(request):
        calls.append(request)
        result = {"ok": False, "status": "UNAVAILABLE"}
        if failure_code is not None:
            result["code"] = failure_code
        return result
    monkeypatch.setattr(analysis.gateway, "run_owned_request", unavailable)
    response = api.post(URL + "/generate", headers=GLOBAL, json={"business_question": "Which action is supported?"})
    assert response.status_code == 200
    job = response.get_json()["result"]
    assert job["business_analysis"]["state"] == "unavailable"
    assert job["business_analysis"]["reason"] == reason
    assert "analysis" not in job["business_analysis"] and len(calls) == 1
    reopened = api.get(URL + "/jobs/" + job["job_id"], headers=GLOBAL)
    assert reopened.status_code == 200 and reopened.get_json()["result"] == job
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS'").fetchone()[0] == 0


def test_empty_body_never_substitutes_title_and_no_model_call(client, monkeypatch):
    api, _, path, _, _ = client
    calls = _mock_model(monkeypatch, client)
    with sqlite3.connect(path) as con:
        con.execute("UPDATE canonical_data SET content=''")
    result = api.post(URL + "/generate", headers=GLOBAL, json={"business_question": "What can we conclude?"})
    draft = result.get_json()["result"]["business_analysis"]
    assert draft["reason"] == "BUSINESS_BRIEF_SOURCE_BODY_UNAVAILABLE" and calls == []


def test_model_error_preserves_source_report_and_does_not_claim_analysis(client, monkeypatch):
    api, _, path, _, _ = client
    prepare_synthetic_content_sources(client, monkeypatch)
    calls = []
    def failed(*args, **kwargs):
        calls.append(args[0])
        raise TimeoutError("model unavailable")
    monkeypatch.setattr(analysis.gateway, "run_owned_request", failed)
    job = api.post(URL + "/generate", headers=GLOBAL, json={"business_question": "What should the team do?"}).get_json()["result"]
    assert job["business_analysis"]["state"] == "error"
    assert len(calls) == 1
    assert api.get(URL + "/jobs/" + job["job_id"], headers=GLOBAL).get_json()["result"] == job
    assert job["artifact_outcome"]["source_count"] == 1


@pytest.mark.parametrize("question", [None, "", "a", 123, "x" * 1501])
def test_invalid_question_never_writes_report(client, question):
    api, _, path, _, _ = client
    assert api.post(URL + "/generate", headers=GLOBAL, json={"business_question": question}).status_code == 400
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 0


@pytest.mark.parametrize("field", ["unknowns", "interpretations", "proposed_actions"])
def test_model_schema_diagnostic_is_rejected_not_silently_removed(client, monkeypatch, field):
    def diagnostic(value):
        if field == "unknowns":
            value[field][0] = "source_ids_all_not_used"
        elif field == "interpretations":
            value[field][0]["text"] = "source_observations_missing"
        else:
            value[field][0]["check"] = "Validate excerpt_index first."
        return value
    api, _, path, _, _ = client
    _mock_model(monkeypatch, client, diagnostic)
    job = api.post(URL + "/generate", headers=GLOBAL, json={
        "business_question": "Propose a content research direction and validation method.",
    }).get_json()["result"]
    assert job["business_analysis"]["state"] == "unavailable"
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS'").fetchone()[0] == 0
        rejected = con.execute("SELECT outputs_json FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS_REJECTED'").fetchone()
        assert rejected and "rejected_model_output" in json.loads(rejected[0])


@pytest.mark.parametrize("version", ["report-business-brief/1", "report-business-brief/2", "report-business-brief/3", "report-business-brief/4", "report-business-brief/5", "report-business-brief/6"])
def test_previous_signed_artifact_remains_reopenable_after_upgrade(client, monkeypatch, version):
    api, _, _, _, _ = client
    from lumenis.shared.reporting.operational_brief import _analysis_window

    prepared = prepare_synthetic_content_sources(client, monkeypatch)
    monkeypatch.setattr(
        analysis.gateway, "run_owned_request",
        lambda *_args, **_kwargs: pytest.fail("historical replay must not call the Gateway"),
    )
    job = api.post(URL + "/generate", headers=GLOBAL, json={}).get_json()["result"]
    question = "Propose an operating research direction."
    payload = {"sources": [{"source_id": job["source_brief"]["records"][0]["source_id"]}]}
    historical_analysis = _answer(json.dumps(payload))
    if version not in analysis._PILOT_VERSIONS:
        for action in historical_analysis["proposed_actions"]:
            action.pop("pilot", None)
    sources = []
    for record in job["source_brief"]["records"]:
        source = prepared["sources"][record["source_id"]]
        text, selection = _analysis_window(source["text"], question)
        sources.append({**source, "text": text, "text_selection": selection,
                        "truncated": len(text) < len(source["text"])})
    historical_analysis = analysis._validate(
        analysis._resolve_excerpts(historical_analysis, sources), sources, version=version,
    )
    historical = attach_legacy_brief_to_job(
        client, prepared, job, version=version, question=question,
        stored_analysis=historical_analysis,
    )
    reopened = api.get(URL + "/jobs/" + job["job_id"], headers=GLOBAL)
    assert reopened.status_code == 200, reopened.get_json()
    result = reopened.get_json()["result"]
    assert result["business_analysis"] == historical
    assert result["business_analysis"]["state"] == "draft"
    assert result["business_analysis"]["provider"] == "ollama"
    assert result["business_question"] == question


@pytest.mark.parametrize("bad", ["missing", "partial", "extra", "empty", "too_long", "wrong_type", "diagnostic"])
def test_malformed_pilot_is_rejected_without_repairing_model_output(client, monkeypatch, bad):
    def corrupt(value):
        action = value["proposed_actions"][0]
        if bad == "missing":
            del action["pilot"]
        elif bad == "partial":
            del action["pilot"]["stop_if"]
        elif bad == "extra":
            action["pilot"]["success"] = True
        elif bad == "empty":
            action["pilot"]["measure"] = " "
        elif bad == "too_long":
            action["pilot"]["measure"] = "x" * 801
        elif bad == "wrong_type":
            action["pilot"] = []
        else:
            action["pilot"]["measure"] = "source_ids_unknown"
        return value
    api, _, path, _, _ = client
    _mock_model(monkeypatch, client, corrupt)
    job = api.post(URL + "/generate", headers=GLOBAL, json={"business_question": "Plan a small content experiment."}).get_json()["result"]
    assert job["business_analysis"]["state"] == "unavailable"
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS'").fetchone()[0] == 0
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS_REJECTED'").fetchone()[0] == 1


def test_diagnostic_filter_does_not_modify_original_source_quote():
    value = _answer(json.dumps({"sources": [{"source_id": "source-1"}]}))
    value["source_observations"] = [{"source_id": "source-1", "excerpt": "The manual calls this field source_ids."}]
    analysis._validate_generated_prose(value)
    assert value["source_observations"][0]["excerpt"] == "The manual calls this field source_ids."
