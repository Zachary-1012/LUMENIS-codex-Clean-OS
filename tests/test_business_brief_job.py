"""Exact authorized Canonical body -> signed draft -> artifact/reopen boundaries."""
import json
import sqlite3

import pytest

from tests.test_source_brief_job_routes import client, GLOBAL, URL
from tests.test_source_brief_job import job_db
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
    return {"source_observations": [{"source_id": source["source_id"], "excerpt_index": 0}],
            "interpretations": [{"text": "This source alone cannot establish consumer demand.", "source_ids": [source["source_id"]]}],
            "proposed_actions": [{"action": "Check the proposed content with the team.", "reason": "Only one source is available.",
                                  "check": "Ask for actual customer feedback before promotion.", "source_ids": [source["source_id"]]}],
            "unknowns": ["Sales and customer sentiment are unknown."]}


def _mock_model(monkeypatch, transform=lambda value: value):
    calls = []
    def model(system, user, **kwargs):
        calls.append(json.loads(user))
        return json.dumps(transform(_answer(user))), "ollama", {"model": "test-local"}
    monkeypatch.setattr(analysis.ai_core, "local_structured_chat", model)
    return calls


def test_real_route_derivative_and_reopen_are_scoped_immutable_not_business_success(client, monkeypatch):
    api, app, path, entry, _ = client
    calls = _mock_model(monkeypatch)
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
    _mock_model(monkeypatch, corrupt)
    api, _, path, _, _ = client
    result = api.post(URL + "/generate", headers=GLOBAL, json={"business_question": "Recommend an operating action."})
    job = result.get_json()["result"]
    assert job["business_analysis"]["state"] == "unavailable"
    assert job["business_analysis"]["real_input_bound"] is False
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS'").fetchone()[0] == 0
        rejected = con.execute("SELECT result,outputs_json FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS_REJECTED'").fetchone()
        assert rejected[0] == 'FAIL' and 'rejected_model_output' in json.loads(rejected[1])


def test_empty_body_never_substitutes_title_and_no_model_call(client, monkeypatch):
    api, _, path, _, _ = client
    calls = _mock_model(monkeypatch)
    with sqlite3.connect(path) as con:
        con.execute("UPDATE canonical_data SET content=''")
    result = api.post(URL + "/generate", headers=GLOBAL, json={"business_question": "What can we conclude?"})
    draft = result.get_json()["result"]["business_analysis"]
    assert draft["reason"] == "BUSINESS_BRIEF_SOURCE_BODY_UNAVAILABLE" and calls == []


def test_model_error_preserves_source_report_and_does_not_claim_analysis(client, monkeypatch):
    api, _, path, _, _ = client
    def failed(*args, **kwargs):
        raise TimeoutError("model unavailable")
    monkeypatch.setattr(analysis.ai_core, "local_structured_chat", failed)
    job = api.post(URL + "/generate", headers=GLOBAL, json={"business_question": "What should the team do?"}).get_json()["result"]
    assert job["business_analysis"]["state"] == "error"
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
    _mock_model(monkeypatch, diagnostic)
    api, _, path, _, _ = client
    job = api.post(URL + "/generate", headers=GLOBAL, json={
        "business_question": "Propose a content research direction and validation method.",
    }).get_json()["result"]
    assert job["business_analysis"]["state"] == "unavailable"
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS'").fetchone()[0] == 0
        rejected = con.execute("SELECT outputs_json FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS_REJECTED'").fetchone()
        assert rejected and "rejected_model_output" in json.loads(rejected[0])


def test_v3_signed_artifact_remains_reopenable_after_v4_upgrade(client, monkeypatch):
    api, _, _, _, _ = client
    calls = _mock_model(monkeypatch)
    with monkeypatch.context() as previous:
        previous.setattr(analysis, "_VERSION", "report-business-brief/3")
        job = api.post(URL + "/generate", headers=GLOBAL, json={
            "business_question": "Propose an operating research direction.",
        }).get_json()["result"]
    assert job["business_analysis"]["state"] == "draft"
    reopened = api.get(URL + "/jobs/" + job["job_id"], headers=GLOBAL)
    assert reopened.status_code == 200 and reopened.get_json()["result"] == job
    assert len(calls) == 1


def test_diagnostic_filter_does_not_modify_original_source_quote():
    value = _answer(json.dumps({"sources": [{"source_id": "source-1"}]}))
    value["source_observations"] = [{"source_id": "source-1", "excerpt": "The manual calls this field source_ids."}]
    analysis._validate_generated_prose(value)
    assert value["source_observations"][0]["excerpt"] == "The manual calls this field source_ids."
