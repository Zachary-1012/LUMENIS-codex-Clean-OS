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


@pytest.mark.parametrize("column,value", [("summary", "replaced source brief"),
                                          ("artifact_hash", "f" * 64)])
def test_case_reopen_reverifies_original_source_report(case_client, column, value):
    api, _, db, focus, body, _ = case_client
    case = api.post(URL, headers=focus, json=body).get_json()["result"]
    with sqlite3.connect(db) as con:
        con.execute(f"UPDATE daily_reports SET {column}=? WHERE report_id=?", (value, body["source_job_id"]))
    response = api.get(URL + "/" + case["case_id"], headers=focus)
    assert response.status_code == 503
    assert response.get_json()["code"] in {"SOURCE_BRIEF_ARTIFACT_HASH_MISMATCH", "CTH_CASE_SOURCE_JOB_CHANGED"}
    assert _counts(db) == (1, 1)


def test_case_reopen_fails_honestly_when_source_report_disappears(case_client):
    api, _, db, focus, body, _ = case_client
    case = api.post(URL, headers=focus, json=body).get_json()["result"]
    with sqlite3.connect(db) as con:
        con.execute("DELETE FROM daily_reports WHERE report_id=?", (body["source_job_id"],))
    response = api.get(URL + "/" + case["case_id"], headers=focus)
    assert response.status_code == 503
    assert response.get_json()["code"] == "CTH_CASE_SOURCE_JOB_INVALID"
    assert _counts(db) == (1, 1)


def test_case_reopen_requires_selected_refs_to_match_source_report(case_client, monkeypatch):
    import cth_cases

    api, _, db, focus, body, _ = case_client
    case = api.post(URL, headers=focus, json=body).get_json()["result"]
    verify_report = cth_cases._verify_report

    def mismatched_source_ref(*args, **kwargs):
        verified = verify_report(*args, **kwargs)
        verified["source_brief"]["records"][0]["scope_evidence_ref"] = "replaced-source-evidence"
        return verified

    monkeypatch.setattr(cth_cases, "_verify_report", mismatched_source_ref)
    response = api.get(URL + "/" + case["case_id"], headers=focus)
    assert response.status_code == 503
    assert response.get_json()["code"] == "CTH_CASE_SOURCE_BINDING_INVALID"
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


def test_case_list_reopens_real_source_bound_cases_without_writes(case_client):
    api, app, db, focus, body, _ = case_client
    assert api.get(URL, headers=focus).get_json()["result"]["cases"] == []
    created = api.post(URL, headers=focus, json=body).get_json()["result"]
    counts = _counts(db)
    listed = app.test_client().get(URL, headers=focus)
    assert listed.status_code == 200, listed.get_json()
    page = listed.get_json()["result"]
    assert page == {"version": "cth-case-list:v1", "scope": created["scope"],
                    "cases": [created], "next_cursor": None}
    assert api.get(URL + "/" + page["cases"][0]["case_id"], headers=focus).get_json()["result"] == created
    assert _counts(db) == counts


def test_case_list_cursor_pagination_with_tied_times_is_stable(case_client, monkeypatch):
    import cth_cases
    from datetime import datetime, timezone
    class FixedClock:
        @staticmethod
        def now(_timezone):
            return datetime(2026, 10, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(cth_cases, "datetime", FixedClock)
    api, _, db, focus, body, _ = case_client
    ids = [api.post(URL, headers=focus, json={**body, "submission_id": f"page-request-{i:02}"})
           .get_json()["result"]["case_id"] for i in range(3)]
    seen = []
    cursor = None
    for index in range(3):
        query = {"limit": 1, **({"before": cursor} if cursor else {})}
        response = api.get(URL, headers=focus, query_string=query)
        assert response.status_code == 200, response.get_json()
        page = response.get_json()["result"]
        seen.extend(case["case_id"] for case in page["cases"])
        cursor = page["next_cursor"]
        assert (cursor is None) == (index == 2)
    assert seen == sorted(ids, reverse=True)
    assert api.get(URL, headers=focus, query_string={"before": seen[-1]}).get_json()["result"]["cases"] == []
    assert _counts(db) == (3, 3)


def test_case_list_never_discloses_other_actor_subject_or_global(case_client):
    import subject_registry
    from cth_cases import list_cth_cases
    api, _, db, focus, body, _ = case_client
    created = api.post(URL, headers=focus, json=body).get_json()["result"]
    other, _ = subject_registry.add_subject({"domain_id": "CTH", "subject_type": "company",
                                           "name_en": "Another venue", "name_zh": "另一个商业主体"})
    assert api.get(URL, headers={**focus, "X-Subject-ID": other["subject_id"]}).get_json()["result"]["cases"] == []
    global_headers = {"X-Domain-Id": "CTH", "X-Product-Id": "CTH", "X-Lumenis-Context-Mode": "GLOBAL_ALL"}
    assert api.get(URL, headers=global_headers).status_code == 403
    assert list_cth_cases(actor_ref="workspace:other", expected_scope=created["scope"])["cases"] == []
    with pytest.raises(LookupError, match="CTH_CASE_CURSOR_NOT_FOUND"):
        list_cth_cases(actor_ref="workspace:other", expected_scope=created["scope"], before=created["case_id"])
    unknown = "CASE-" + "0" * 32
    for cursor in (created["case_id"], unknown):
        response = api.get(URL, headers={**focus, "X-Subject-ID": other["subject_id"]}, query_string={"before": cursor})
        assert response.status_code == 404
        assert response.get_json()["code"] == "CTH_CASE_CURSOR_NOT_FOUND"
    assert _counts(db) == (1, 1)


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "limit=true", "limit=01", "limit=", "limit=-1",
                                  "limit=1&limit=2", "before=", "before=bad", "actor_ref=workspace:other"])
def test_invalid_case_list_query_has_no_effect(case_client, query):
    api, _, db, focus, body, _ = case_client
    api.post(URL, headers=focus, json=body)
    assert api.get(URL + "?" + query, headers=focus).status_code == 400
    assert _counts(db) == (1, 1)


@pytest.mark.parametrize("extra", [{"Origin": "https://foreign.invalid"}, {"X-Actor-ID": "23"},
                                  {"X-Forwarded-For": "127.0.0.1"}])
def test_case_list_respects_server_principal_boundary(case_client, extra):
    api, _, db, focus, body, _ = case_client
    api.post(URL, headers=focus, json=body)
    assert api.get(URL, headers={**focus, **extra}).status_code in {401, 403}
    assert _counts(db) == (1, 1)


@pytest.mark.parametrize("target", ["case", "creation", "source"])
def test_case_list_fails_honestly_on_broken_lineage(case_client, target):
    api, _, db, focus, body, _ = case_client
    case = api.post(URL, headers=focus, json=body).get_json()["result"]
    with sqlite3.connect(db) as con:
        if target == "case":
            con.execute(f"UPDATE {TABLE} SET title='Changed title' WHERE case_id=?", (case["case_id"],))
        else:
            evidence_id = (case["creation_evidence_ref"].split(":")[1] if target == "creation"
                           else case["source_refs"][0]["scope_evidence_ref"])
            con.execute("UPDATE app_evidence_records SET inputs_json='{}' WHERE id=?", (evidence_id,))
    assert api.get(URL, headers=focus).status_code == (403 if target == "source" else 503)
    assert api.get(URL, headers=focus, query_string={"before": case["case_id"]}).status_code == (403 if target == "source" else 503)
    assert _counts(db) == (1, 1)


def test_archived_subject_has_no_case_list_access(case_client):
    from cth_cases import list_cth_cases
    api, _, db, focus, body, _ = case_client
    case = api.post(URL, headers=focus, json=body).get_json()["result"]
    with sqlite3.connect(db) as con:
        actor_ref = con.execute(f"SELECT actor_ref FROM {TABLE}").fetchone()[0]
        con.execute("UPDATE lumenis_subject_registry SET status='archived' WHERE subject_id=?", (focus["X-Subject-ID"],))
    assert api.get(URL, headers=focus).status_code == 404
    with pytest.raises(PermissionError, match="CTH_CASE_SUBJECT_NOT_ACTIVE"):
        list_cth_cases(actor_ref=actor_ref, expected_scope=case["scope"])
