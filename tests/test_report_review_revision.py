"""Stored signed feedback -> real report task/owners with isolated model input."""
import json
import sqlite3
import uuid

import pytest

from tests.test_source_brief_job import job_db
from tests.test_source_brief_job_routes import client, GLOBAL, URL
from tests.test_source_brief_tasks import task_schema, _poll
from tests.test_business_brief_job import _mock_model, _answer
from lumenis.shared.reporting import source_brief_tasks as tasks, business_brief as analysis
from lumenis.system.security.permission import PermissionLevel


def _parent(client, monkeypatch, decision="request_changes"):
    api, _, _, entry, _ = client
    calls = _mock_model(monkeypatch)
    headers = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    parent = api.post(URL + "/generate", headers=headers, json={
        "business_question": "Propose a measurable content experiment using these sources.",
        "source_ids": ["brief-job-source"],
    }).get_json()["result"]
    response = api.post(URL + "/jobs/" + parent["job_id"] + "/reviews", headers=headers, json={
        "submission_id": str(uuid.uuid4()), "decision": decision,
        "notes": "Do not claim consumer consensus; define what to do when the baseline is unknown.",
    })
    assert response.status_code == 200, response.get_json()
    review = response.get_json()["review"]
    return headers, parent, review, calls


def test_revision_uses_saved_feedback_and_preserves_original_through_reopen_resume(client, monkeypatch):
    api, _, db, _, _ = client
    headers, parent, review, calls = _parent(client, monkeypatch)
    def revised_model(system, user, **kwargs):
        calls.append(json.loads(user))
        answer = _answer(user)
        answer["unknowns"] = ["Baseline is unknown; gather initial observations before comparing change."]
        return json.dumps(answer), "ollama", {"model": "test-local"}
    monkeypatch.setattr(analysis.ai_core, "local_structured_chat", revised_model)
    reference = {"parent_job_id": parent["job_id"], "review_id": review["review_id"]}
    response = api.post(URL + "/start", headers=headers, json={"revision": reference})
    assert response.status_code == 202, response.get_json()
    task = _poll(api, response.get_json()["task"]["task_id"], headers)
    assert task["state"] == "succeeded", task
    revised = task["result"]
    assert revised["job_id"] != parent["job_id"]
    assert revised["revision"]["review_evidence_ref"] == review["evidence_ref"]
    assert revised["revision"]["parent_artifact_hash"] == parent["artifact_outcome"]["artifact_hash"]
    assert revised["business_analysis"]["revision"] == revised["revision"]
    assert calls[-1]["revision"]["feedback"] == review["notes"]
    assert calls[-1]["revision"]["previous_analysis"] == parent["business_analysis"]["analysis"]
    assert calls[-1]["question"] == parent["business_question"]
    assert revised["requested_source_ids"] == parent["requested_source_ids"]
    assert revised["operator_review"]["state"] == "not_recorded"
    assert revised["review_status"] == "HUMAN_PENDING"
    reopened = api.get(URL + "/jobs/" + revised["job_id"], headers=headers).get_json()["result"]
    assert reopened == revised
    resumed = api.post(URL + "/tasks/" + task["task_id"] + "/resume", headers=headers, json={})
    assert resumed.get_json()["task"]["result"] == revised and len(calls) == 2
    original = api.get(URL + "/jobs/" + parent["job_id"], headers=headers).get_json()["result"]
    assert original["artifact_outcome"] == parent["artifact_outcome"]
    assert original["business_analysis"] == parent["business_analysis"]
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT count(*) FROM daily_reports").fetchone()[0] == 2
        con.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?", (int(review["evidence_ref"].split(":")[1]),))
    # Signed feedback remains part of reopen lineage, not just a copied note.
    assert api.get(URL + "/jobs/" + revised["job_id"], headers=headers).status_code == 503


def test_unchanged_revision_is_unavailable_with_retained_failure_not_new_draft(client, monkeypatch):
    api, _, db, _, _ = client
    headers, parent, review, calls = _parent(client, monkeypatch)
    response = api.post(URL + "/start", headers=headers, json={"revision": {
        "parent_job_id": parent["job_id"], "review_id": review["review_id"]}})
    task = _poll(api, response.get_json()["task"]["task_id"], headers)
    result = task["result"]
    rejected = result["business_analysis"]
    assert rejected["state"] == "unavailable"
    assert rejected["reason"] == "BUSINESS_BRIEF_REVISION_UNCHANGED"
    assert rejected["review_status"] == "HUMAN_PENDING" and "analysis" not in rejected
    with sqlite3.connect(db) as con:
        evidence = con.execute("SELECT feature_id,result,outputs_json FROM app_evidence_records WHERE id=?",
            (int(rejected["rejected_candidate_evidence_ref"].split(":")[1]),)).fetchone()
        assert evidence[:2] == ("REPORT_BUSINESS_ANALYSIS_REJECTED", "FAIL")
        assert json.loads(evidence[2])["reason"] == "BUSINESS_BRIEF_REVISION_UNCHANGED"
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS'").fetchone()[0] == 1
    reopened = api.get(URL + "/jobs/" + result["job_id"], headers=headers).get_json()["result"]
    assert reopened == result
    assert api.post(URL + "/tasks/" + task["task_id"] + "/resume", headers=headers, json={}).get_json()["task"]["result"] == result
    assert len(calls) == 2  # No automatic regeneration to hide unchanged output.
    original = api.get(URL + "/jobs/" + parent["job_id"], headers=headers).get_json()["result"]
    assert original["artifact_outcome"] == parent["artifact_outcome"]


@pytest.mark.parametrize("invalid", ["foreign_scope", "fake_review", "tamper", "override", "non_revision_decision"])
def test_revision_rejects_untrusted_inputs_before_task_or_model(client, monkeypatch, invalid):
    api, _, db, _, _ = client
    headers, parent, review, calls = _parent(client, monkeypatch,
        decision="use_for_next_step" if invalid == "non_revision_decision" else "request_changes")
    reference = {"parent_job_id": parent["job_id"], "review_id": review["review_id"]}
    body = {"revision": reference}
    if invalid == "foreign_scope": headers = GLOBAL
    if invalid == "fake_review": reference["review_id"] = "0" * 64
    if invalid == "override": body["business_question"] = "Replace the approved task."
    if invalid == "tamper":
        with sqlite3.connect(db) as con:
            con.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?", (int(review["evidence_ref"].split(":")[1]),))
    response = api.post(URL + "/start", headers=headers, json=body)
    assert response.status_code in {400, 403, 503}, response.get_json()
    assert len(calls) == 1
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT count(*) FROM ai_task").fetchone()[0] == 0
        assert con.execute("SELECT count(*) FROM daily_reports").fetchone()[0] == 1


def test_revision_rechecks_permission_before_derivative_evidence(client, monkeypatch):
    api, _, db, _, gate = client
    headers, parent, review, _ = _parent(client, monkeypatch)
    def revoke_during_model(system, user, **kwargs):
        gate.revoke_permission(PermissionLevel.ANALYZE)
        return json.dumps(_answer(user)), "ollama", {"model": "test-local"}
    monkeypatch.setattr(analysis.ai_core, "local_structured_chat", revoke_during_model)
    response = api.post(URL + "/start", headers=headers, json={
        "revision": {"parent_job_id": parent["job_id"], "review_id": review["review_id"]}})
    assert response.status_code == 202, response.get_json()
    assert _poll(api, response.get_json()["task"]["task_id"], headers)["state"] == "failed"
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT count(*) FROM daily_reports").fetchone()[0] == 1
        assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='REPORT_BUSINESS_ANALYSIS'").fetchone()[0] == 1
