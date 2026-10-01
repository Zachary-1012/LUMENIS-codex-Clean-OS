"""Report disposition through the actual request principal and operation gate."""
import sqlite3
import uuid

import pytest

from tests.test_source_brief_job_routes import client, job_db, GLOBAL, URL
from lumenis.system.security import permission as p


def _report(client):
    api, _app, _db, entry, _gate = client
    focus = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    response = api.post(URL + "/generate", headers=focus, json={})
    assert response.status_code == 200, response.get_json()
    report = response.get_json()["result"]
    return report, focus, URL + "/jobs/" + report["job_id"] + "/reviews"


def _payload():
    return {"submission_id": str(uuid.uuid4()), "decision": "request_changes",
            "notes": "Need a sourced baseline before using the proposal."}


def _counts(db):
    with sqlite3.connect(db) as con:
        return (con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='REPORT_OPERATOR_REVIEW'").fetchone()[0],
                con.execute("SELECT COUNT(*) FROM evaluation_records WHERE metric_name='operator_report_disposition'").fetchone()[0])


def test_review_reopen_retry_and_conflict_leave_original_report_unchanged(client):
    api, app, db, _entry, _gate = client
    original, focus, path = _report(client)
    payload = _payload()
    response = api.post(path, headers=focus, json=payload)
    assert response.status_code == 200, response.get_json()
    review = response.get_json()["review"]
    assert response.get_json()["publish_status"] == "not_performed"
    assert review["decision"] == payload["decision"] and review["notes"] == payload["notes"]
    assert review["business_outcome"] == "NOT_OBSERVED"
    assert review["evidence_ref"] and review["evaluation_id"]
    assert api.post(path, headers=focus, json=payload).get_json()["review"] == review
    assert api.post(path, headers=focus, json={**payload, "decision": "reject"}).status_code == 400
    reopened = app.test_client().get(path.removesuffix("/reviews"), headers=focus).get_json()["result"]
    assert reopened["operator_review"]["latest"] == review
    assert reopened["review_status"] == "HUMAN_PENDING"
    assert reopened["artifact_outcome"] == original["artifact_outcome"]
    assert reopened["source_brief"] == original["source_brief"]
    assert _counts(db) == (1, 1)
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT status FROM app_evidence_records WHERE feature_id='REPORT_OPERATOR_REVIEW'").fetchone()[0] == "derived"
        row = con.execute("SELECT evidence_ref,status FROM evaluation_records WHERE evaluation_id=?", (review["evaluation_id"],)).fetchone()
        assert row == (f"daily_reports:{original['job_id']}:{original['artifact_outcome']['artifact_hash']}", "unknown")


def test_interrupted_review_has_honest_pending_state_and_recovers_through_route(client, monkeypatch):
    from lumenis.shared.reporting import operator_review as reviews
    api, app, db, _entry, _gate = client
    original, focus, path = _report(client)
    payload = _payload()
    actual = reviews.record_evaluation
    monkeypatch.setattr(reviews, "record_evaluation", lambda **kwargs: (_ for _ in ()).throw(OSError("interrupted")))
    assert api.post(path, headers=focus, json=payload).status_code == 503
    assert _counts(db) == (1, 0)
    reopened = app.test_client().get(path.removesuffix("/reviews"), headers=focus)
    assert reopened.status_code == 200, reopened.get_json()
    projection = reopened.get_json()["result"]
    assert projection["operator_review"]["state"] != "recorded"
    assert projection["operator_review"]["latest"]["decision"] == "request_changes"
    assert projection["artifact_outcome"] == original["artifact_outcome"]
    monkeypatch.setattr(reviews, "record_evaluation", actual)
    repaired = api.post(path, headers=focus, json=payload)
    assert repaired.status_code == 200, repaired.get_json()
    assert _counts(db) == (1, 1)
    assert app.test_client().get(path.removesuffix("/reviews"), headers=focus).get_json()["result"]["operator_review"]["state"] == "recorded"


@pytest.mark.parametrize("extra", [{"Origin": "https://foreign.invalid"}, {"X-Actor-ID": "owner"},
                                   {"X-Forwarded-For": "127.0.0.1"}])
def test_review_rejects_forged_principal_without_side_effect(client, extra):
    api, _app, db, _entry, _gate = client
    _original, focus, path = _report(client)
    assert api.post(path, headers={**focus, **extra}, json=_payload()).status_code in {401, 403}
    assert _counts(db) == (0, 0)


def test_exact_scope_and_revocation_apply_to_first_write_and_retry(client):
    api, _app, db, _entry, gate = client
    _original, focus, path = _report(client)
    payload = _payload()
    assert api.post(path, headers=GLOBAL, json=payload).status_code == 403
    assert _counts(db) == (0, 0)
    assert api.post(path, headers=focus, json=payload).status_code == 200
    gate.revoke_permission(p.PermissionLevel.VERIFY)
    assert api.post(path, headers=focus, json=payload).status_code == 403
    assert api.post(path, headers=focus, json=_payload()).status_code == 403
    assert _counts(db) == (1, 1)
    # A different high-risk database write did not gain an automatic allow.
    assert not gate.check(p.OperationType.DB_WRITE, resource="arbitrary", caller="test").allowed


@pytest.mark.parametrize("mutate", [
    lambda value: {**value, "actor_id": "owner"},
    lambda value: {**value, "business_outcome": "PASS"},
    lambda value: {**value, "decision": "publish"},
    lambda value: {**value, "submission_id": "not-an-id"},
    lambda value: {**value, "notes": ""},
])
def test_review_does_not_accept_client_trust_or_invalid_payload(client, mutate):
    api, _app, db, _entry, _gate = client
    _original, focus, path = _report(client)
    assert api.post(path, headers=focus, json=mutate(_payload())).status_code == 400
    assert _counts(db) == (0, 0)


def test_review_operation_is_scoped_to_the_exact_route(client):
    _api, app, _db, _entry, _gate = client
    resolver = app.before_request_funcs[None][0].__globals__["_pg_resolve_operation_type"]
    assert resolver(URL + "/jobs/job-1/reviews", "POST") == p.OperationType.REPORT_REVIEW
    for path in (URL + "/jobs/job-1/reviews/extra", "/api/data/reviews", "/api/other/reviews"):
        assert resolver(path, "POST") != p.OperationType.REPORT_REVIEW
