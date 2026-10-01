"""Real Case routes, signed sources and atomic persistence on disposable DBs."""
import sqlite3

import pytest

from tests.test_source_brief_job_routes import client as report_client, job_db
from lumenis.shared.database.cth_cases import ensure_cth_case_schema, TABLE
from lumenis.system.security import permission as p

URL = "/api/experience/cth/cases"


@pytest.fixture
def case_client(report_client):
    api, app, db, entry, gate = report_client
    with sqlite3.connect(db) as con:
        ensure_cth_case_schema(con)
    focus = {"X-Domain-Id": "CTH", "X-Product-Id": "CTH",
             "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    response = api.post("/api/experience/reports/source-brief/generate", headers=focus, json={})
    assert response.status_code == 200
    body = {"submission_id": "case-request-01", "title": "Review this commercial venue",
            "question": "Which source-backed observations need further investigation?",
            "source_job_id": response.get_json()["result"]["job_id"], "source_ids": ["brief-job-source"]}
    return api, app, db, focus, body, gate


def _counts(db):
    with sqlite3.connect(db) as con:
        return (con.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0],
                con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='CTH_CASE_CREATED'").fetchone()[0])


def test_case_create_reopen_retry_preserves_sources_without_claiming_outcome(case_client):
    api, app, db, focus, body, _ = case_client
    first = api.post(URL, headers=focus, json=body)
    assert first.status_code == 200, first.get_json()
    result = first.get_json()["result"]
    assert result["case_id"].startswith("CASE-") and result["state"] == "OPEN"
    assert result["analysis_state"] == "NOT_REQUESTED" and result["business_outcome"] == "NOT_OBSERVED"
    assert result["source_refs"][0]["source_id"] == "brief-job-source"
    assert result["timeline"][0]["stage"] == "CASE"
    assert api.post(URL, headers=focus, json=body).get_json()["result"] == result
    assert app.test_client().get(URL + "/" + result["case_id"], headers=focus).get_json()["result"] == result
    assert _counts(db) == (1, 1)
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM canonical_data").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 1
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("extra", [{"Origin": "https://foreign.invalid"}, {"X-Actor-ID": "23"},
                                  {"X-Forwarded-For": "127.0.0.1"}])
def test_foreign_transport_never_creates_case(case_client, extra):
    api, _, db, focus, body, _ = case_client
    assert api.post(URL, headers={**focus, **extra}, json=body).status_code in {401, 403}
    assert _counts(db) == (0, 0)


@pytest.mark.parametrize("change", [{"source_ids": None}, {"source_ids": []},
                                   {"source_ids": ["brief-job-source", "brief-job-source"]},
                                   {"actor_ref": "workspace:other"}, {"state": "CLOSED"},
                                   {"title": ""}, {"submission_id": "bad"}])
def test_invalid_or_forged_intent_has_no_case_effect(case_client, change):
    api, _, db, focus, body, _ = case_client
    assert api.post(URL, headers=focus, json={**body, **change}).status_code == 400
    assert _counts(db) == (0, 0)


def test_case_write_fence_denial_keeps_report_and_sources(case_client):
    api, _, db, focus, body, gate = case_client
    gate.revoke_permission(p.PermissionLevel.VERIFY)
    assert api.post(URL, headers=focus, json=body).status_code == 403
    assert _counts(db) == (0, 0)
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM canonical_data").fetchone()[0] == 1


def test_global_and_other_subject_cannot_create_or_reopen_focused_case(case_client):
    import subject_registry
    api, _, db, focus, body, _ = case_client
    global_headers = {"X-Domain-Id": "CTH", "X-Product-Id": "CTH", "X-Lumenis-Context-Mode": "GLOBAL_ALL"}
    assert api.post(URL, headers=global_headers, json=body).status_code == 403
    created = api.post(URL, headers=focus, json=body).get_json()["result"]
    other, _ = subject_registry.add_subject({"domain_id": "CTH", "subject_type": "company",
                                           "name_en": "Other venue", "name_zh": "其他商业主体"})
    foreign = {**focus, "X-Subject-ID": other["subject_id"]}
    assert api.post(URL, headers=foreign, json={**body, "submission_id": "other-request"}).status_code == 403
    assert api.get(URL + "/" + created["case_id"], headers=foreign).status_code == 403
    assert api.get(URL + "/" + created["case_id"], headers=global_headers).status_code == 403
    assert _counts(db) == (1, 1)


def test_source_tampering_is_rejected_before_case_write(case_client):
    api, _, db, focus, body, _ = case_client
    with sqlite3.connect(db) as con:
        con.execute("UPDATE app_evidence_records SET inputs_json='{}' WHERE id=(SELECT scope_evidence_ref FROM canonical_data LIMIT 1)")
    assert api.post(URL, headers=focus, json=body).status_code == 403
    assert _counts(db) == (0, 0)


@pytest.mark.parametrize("field,value", [("title", "Tampered title"), ("created_at", "2099-01-01"),
                                       ("question", "Changed question"), ("source_refs_json", "[]")])
def test_case_tampering_is_not_displayed_as_a_verified_case(case_client, field, value):
    api, _, db, focus, body, _ = case_client
    case_id = api.post(URL, headers=focus, json=body).get_json()["result"]["case_id"]
    with sqlite3.connect(db) as con:
        con.execute(f"UPDATE {TABLE} SET {field}=? WHERE case_id=?", (value, case_id))
    assert api.get(URL + "/" + case_id, headers=focus).status_code == 503
    assert _counts(db) == (1, 1)


def test_failed_case_insert_rolls_back_signed_evidence_and_retry_recovers(case_client):
    api, _, db, focus, body, _ = case_client
    with sqlite3.connect(db) as con:
        con.execute(f"CREATE TRIGGER reject_case BEFORE INSERT ON {TABLE} BEGIN SELECT RAISE(ABORT,'isolated failure'); END")
    assert api.post(URL, headers=focus, json=body).status_code == 503
    assert _counts(db) == (0, 0)
    with sqlite3.connect(db) as con:
        con.execute("DROP TRIGGER reject_case")
    assert api.post(URL, headers=focus, json=body).status_code == 200
    assert _counts(db) == (1, 1)


def test_same_submission_conflict_preserves_original_case(case_client):
    api, _, db, focus, body, _ = case_client
    result = api.post(URL, headers=focus, json=body).get_json()["result"]
    changed = api.post(URL, headers=focus, json={**body, "question": "A different question must not overwrite the original."})
    assert changed.status_code == 400
    assert api.get(URL + "/" + result["case_id"], headers=focus).get_json()["result"] == result
    assert _counts(db) == (1, 1)


def test_another_actor_cannot_read_a_case(case_client):
    from cth_cases import get_cth_case
    api, _, _, focus, body, _ = case_client
    result = api.post(URL, headers=focus, json=body).get_json()["result"]
    with pytest.raises(PermissionError):
        get_cth_case(result["case_id"], actor_ref="workspace:other", expected_scope=result["scope"])


def test_archived_subject_revokes_case_read_and_write(case_client):
    from cth_cases import get_cth_case
    api, _, db, focus, body, _ = case_client
    result = api.post(URL, headers=focus, json=body).get_json()["result"]
    with sqlite3.connect(db) as con:
        actor_ref = con.execute(f"SELECT actor_ref FROM {TABLE}").fetchone()[0]
        con.execute("UPDATE lumenis_subject_registry SET status='archived' WHERE subject_id=?",
                    (focus["X-Subject-ID"],))
    # The existing context owner hides archived registry entries as not found.
    assert api.get(URL + "/" + result["case_id"], headers=focus).status_code == 404
    assert api.post(URL, headers=focus, json=body).status_code == 404
    with pytest.raises(PermissionError):
        get_cth_case(result["case_id"], actor_ref=actor_ref, expected_scope=result["scope"])
    assert _counts(db) == (1, 1)


def test_creation_trace_tampering_prevents_reopen(case_client):
    api, _, db, focus, body, _ = case_client
    result = api.post(URL, headers=focus, json=body).get_json()["result"]
    with sqlite3.connect(db) as con:
        con.execute("UPDATE app_evidence_records SET inputs_json='{}' WHERE id="
                    f"(SELECT creation_evidence_ref FROM {TABLE})")
    assert api.get(URL + "/" + result["case_id"], headers=focus).status_code == 503
    assert _counts(db) == (1, 1)


def test_brand_focus_cannot_invoke_cth_case_write(case_client):
    import subject_registry
    api, _, db, _, body, _ = case_client
    brand, _ = subject_registry.add_subject({"domain_id": "ZBMP", "subject_type": "brand",
                                            "name_en": "Sample Brand", "name_zh": "示例品牌"})
    headers = {"X-Domain-Id": "ZBMP", "X-Product-Id": "ZBMP",
               "X-Lumenis-Context-Mode": "FOCUS", "X-Brand-Focus-ID": brand["brand_focus_id"]}
    assert api.post(URL, headers=headers, json=body).status_code == 403
    assert _counts(db) == (0, 0)


def test_revocation_after_admission_before_transaction_write_has_no_effect(case_client, monkeypatch):
    import cth_cases
    from contextlib import contextmanager
    api, _, db, focus, body, gate = case_client
    repo = cth_cases.get_repository()
    original = repo.transaction

    @contextmanager
    def revoked_transaction(**kwargs):
        with original(**kwargs) as connection:
            gate.revoke_permission(p.PermissionLevel.VERIFY)
            yield connection

    monkeypatch.setattr(repo, "transaction", revoked_transaction)
    assert api.post(URL, headers=focus, json=body).status_code == 403
    assert _counts(db) == (0, 0)
