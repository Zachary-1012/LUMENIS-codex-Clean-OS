"""Display-name changes must preserve signed business history, not widen scope."""
import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from tests.test_business_work_owner_routes import owners, client, job_db, prepare_business, BUSINESS
from tests.test_business_result_continuity import business, workspace, save, adopt, selection
from tests.test_cth_case_routes import case_client, report_client, URL as CASES


def rename_registry(db, *, subject_id=None, brand_focus_id=None):
    with sqlite3.connect(db) as connection:
        column, value = ("subject_id", subject_id) if subject_id else ("brand_focus_id", brand_focus_id)
        changed = connection.execute(
            f"UPDATE lumenis_subject_registry SET name_zh=?,name_en=? WHERE {column}=?",
            ("更名后的隔离主体", "Renamed isolated entity", value),
        )
        assert changed.rowcount == 1


def test_business_route_reopens_signed_history_after_registry_rename(owners):
    ws = owners
    original = prepare_business(ws)
    rename_registry(ws["db"], subject_id=ws["scope"]["subject_id"], brand_focus_id=ws["scope"]["brand_focus_id"])
    response = ws["api"].get(BUSINESS + "/" + original["work_id"], headers=ws["headers"])
    assert response.status_code == 200, response.get_json()
    reopened = response.get_json()["result"]
    for field in ("work_id", "revision", "scope", "source_brief", "source_report", "timeline"):
        assert reopened[field] == original[field]


def test_prepare_lost_ack_retry_after_rename_keeps_work_identity(owners):
    ws = owners
    original = prepare_business(ws)
    rename_registry(ws["db"], subject_id=ws["scope"]["subject_id"], brand_focus_id=ws["scope"]["brand_focus_id"])
    response = ws["api"].post(BUSINESS, headers=ws["headers"], json={
        "submission_id": "prepare-owner-route-01", "source_job_id": original["source_report"]["job_id"],
        "kind": original["kind"], "question": original["question"],
        "options": [{key: value for key, value in option.items() if key not in {"claim_type", "causation"}}
                    for option in original["options"]],
    })
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["result"]["work_id"] == original["work_id"]
    assert response.get_json()["result"]["revision"] == original["revision"]
    conflicting = {"submission_id": "prepare-owner-route-01",
                   "source_job_id": original["source_report"]["job_id"], "kind": original["kind"],
                   "question": "A different request cannot replace this work.", "options": []}
    refused = ws["api"].post(BUSINESS, headers=ws["headers"], json=conflicting)
    # An existing idempotency key with changed intent is the API's explicit
    # 409 conflict contract; a new malformed request still receives 400.
    assert refused.status_code == 409, refused.get_json()
    assert refused.get_json()["code"] == "BUSINESS_WORK_SUBMISSION_CONFLICT"
    invalid = ws["api"].post(BUSINESS, headers=ws["headers"], json={
        **conflicting, "submission_id": "new-malformed-prepare"})
    assert invalid.status_code == 400, invalid.get_json()
    assert invalid.get_json()["code"] == "BUSINESS_WORK_COMPARABLE_OPTIONS_REQUIRED"
    with sqlite3.connect(ws["db"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='CTH_BMP_DECISION_WORK'").fetchone()[0] == 1


def test_saved_result_and_evaluation_replay_keep_original_versions_after_rename(business):
    ws = business
    args = dict(actor_ref=ws["actor_ref"], scope=ws["domain_scope"], authorize=ws["authorize"])
    before = ws["current"]
    payload = {"source_job_id": before["source_report"]["job_id"],
               "source_id": ws["options"][0]["source_ids"][0], "quote": ws["citation"]["quote"],
               "limits": "Attributed statement; actual business effect is not measured."}
    ws["current"] = ws["service"].advance(before["work_id"], **args,
        submission_id="rename-outcome-01", operation="outcome",
        expected_revision=before["revision"], payload=payload)
    original = copy.deepcopy(ws["current"])
    saved = save(ws)
    rename_registry(ws["root"] / "isolated.sqlite3", subject_id=ws["scope"]["subject_id"], brand_focus_id=ws["scope"]["brand_focus_id"])
    ws["domain_scope"]["entity_label"] = "Renamed isolated entity"
    reopened = ws["service"].reopen(original["work_id"], **args)
    assert reopened["scope"] == original["scope"]
    assert reopened["evaluation"] == original["evaluation"]
    replay = save(ws)
    assert replay["saved_work"]["replayed"]
    assert replay["creation_upstream"] == saved["creation_upstream"]
    outcome_replay = ws["service"].advance(before["work_id"], **args,
        submission_id="rename-outcome-01", operation="outcome",
        expected_revision=before["revision"], payload=payload)
    assert outcome_replay["evaluation"] == original["evaluation"]
    assert outcome_replay["revision"] == original["revision"]
    with ws["repo"].connection(read_only=True, wal=False) as connection:
        report = ws["service"]._report(connection, original["source_report"]["job_id"], ws["actor_ref"], ws["domain_scope"])
    ws["current"] = adopt(ws, report["snapshot"], ws["options"], selection("B", "200"), request_id="rename-adopt-01")
    revised = save(ws, request_id="rename-save-version-02", parent=saved["saved_work"]["artifact"]["artifact_id"],
                   digest=saved["saved_work"]["document"]["draft_digest"])
    assert revised["saved_work"]["document"]["version"] == 2
    assert revised["saved_work"]["document"]["work_id"] == saved["saved_work"]["document"]["work_id"]
    assert revised["saved_work"]["document"]["payload"]["brief"]["scope"]["entity_label"] == "Renamed isolated entity"
    original_doc = ws["work"].reopen_work(saved["saved_work"]["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"])
    assert original_doc["document"] == saved["saved_work"]["document"]


def test_concurrent_prepare_across_display_labels_records_one_request(business):
    ws = business
    barrier = Barrier(2)
    def prepare(label):
        scope = {**ws["domain_scope"], "entity_label": label}
        def authorize(operation):
            return {"actor_id": ws["actor_ref"], "scope": scope, "operation": operation,
                    "permission_audit_ref": "isolated-concurrent-scope", "operation_audit_ref": "isolated-concurrent-operation"}
        barrier.wait(timeout=10)
        with ws["app"].test_request_context("/", headers={"Host": "localhost"},
                environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
            return ws["service"].prepare(actor_ref=ws["actor_ref"], scope=scope, authorize=authorize,
                submission_id="concurrent-rename-prepare", source_job_id=ws["current"]["source_report"]["job_id"],
                kind=ws["current"]["kind"], question=ws["current"]["question"], options=ws["options"])
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(prepare, label) for label in ("Original isolated label", "Renamed isolated label")]
        first, second = [future.result(timeout=30) for future in futures]
    assert first["work_id"] == second["work_id"]
    assert first["revision"] == second["revision"]
    assert first["scope"] == second["scope"]
    assert ws["repo"].query_one("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='CTH_BMP_DECISION_WORK' AND test_name='concurrent-rename-prepare'")[0] == 1


def test_rename_does_not_grant_other_entity_or_archived_entity_access(owners):
    import subject_registry
    ws = owners
    original = prepare_business(ws)
    rename_registry(ws["db"], subject_id=ws["scope"]["subject_id"], brand_focus_id=ws["scope"]["brand_focus_id"])
    cth = ws["scope"]["domain_id"] == "cth"
    other, _ = subject_registry.add_subject({"domain_id": "CTH" if cth else "BMP",
        "subject_type": "company" if cth else "brand", "name_zh": "另一个隔离主体", "name_en": "Another isolated entity"})
    rename_registry(ws["db"], subject_id=other["subject_id"] if cth else None,
                    brand_focus_id=other["brand_focus_id"] if not cth else None)
    header = "X-Subject-ID" if cth else "X-Brand-Focus-ID"
    refused = ws["api"].get(BUSINESS + "/" + original["work_id"], headers={**ws["headers"], header: other["subject_id"] if cth else other["brand_focus_id"]})
    assert refused.status_code == 403, refused.get_json()
    assert "result" not in refused.get_json()
    with sqlite3.connect(ws["db"]) as connection:
        column = "subject_id" if cth else "brand_focus_id"
        connection.execute(f"UPDATE lumenis_subject_registry SET status='archived' WHERE {column}=?", (ws["scope"][column],))
    refused = ws["api"].get(BUSINESS + "/" + original["work_id"], headers=ws["headers"])
    assert refused.status_code == (400 if cth else 403), refused.get_json()
    assert "result" not in refused.get_json()
    if cth:
        assert refused.get_json()["code"] == "CONTENT_SCOPE_NOT_FOUND"


def test_tampered_prepare_cannot_be_skipped_by_renamed_retry(owners):
    ws = owners
    original = prepare_business(ws)
    rename_registry(ws["db"], subject_id=ws["scope"]["subject_id"], brand_focus_id=ws["scope"]["brand_focus_id"])
    with sqlite3.connect(ws["db"]) as connection:
        row = connection.execute("SELECT id,inputs_json FROM app_evidence_records WHERE feature_id='CTH_BMP_DECISION_WORK'").fetchone()
        inputs = json.loads(row[1])
        inputs["actor_ref"] = "forged-other-actor"
        connection.execute("UPDATE app_evidence_records SET inputs_json=? WHERE id=?", (json.dumps(inputs), row[0]))
    response = ws["api"].post(BUSINESS, headers=ws["headers"], json={
        "submission_id": "prepare-owner-route-01", "source_job_id": original["source_report"]["job_id"],
        "kind": original["kind"], "question": original["question"],
        "options": [{key: value for key, value in option.items() if key not in {"claim_type", "causation"}}
                    for option in original["options"]],
    })
    assert response.status_code == 503, response.get_json()
    assert response.get_json()["code"] == "BUSINESS_WORK_SIGNATURE_INVALID"
    with sqlite3.connect(ws["db"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='CTH_BMP_DECISION_WORK'").fetchone()[0] == 1


def test_case_reopen_list_and_lost_ack_retry_preserve_original_snapshot(case_client):
    api, _, db, focus, body, _ = case_client
    first = api.post(CASES, headers=focus, json=body)
    assert first.status_code == 200, first.get_json()
    original = first.get_json()["result"]
    rename_registry(db, subject_id=focus["X-Subject-ID"])
    reopened = api.get(CASES + "/" + original["case_id"], headers=focus)
    assert reopened.status_code == 200, reopened.get_json()
    assert reopened.get_json()["result"] == original
    listed = api.get(CASES, headers=focus)
    assert listed.status_code == 200, listed.get_json()
    assert listed.get_json()["result"]["cases"] == [original]
    replay = api.post(CASES, headers=focus, json=body)
    assert replay.status_code == 200, replay.get_json()
    assert replay.get_json()["result"] == original


def test_new_case_after_rename_can_use_unchanged_signed_source(case_client):
    api, _, db, focus, body, _ = case_client
    rename_registry(db, subject_id=focus["X-Subject-ID"])
    response = api.post(CASES, headers=focus, json=body)
    assert response.status_code == 200, response.get_json()
    case = response.get_json()["result"]
    assert case["scope"]["entity_label"] == "更名后的隔离主体"
    assert case["source_job_id"] == body["source_job_id"]
    reopened = api.get(CASES + "/" + case["case_id"], headers=focus)
    assert reopened.status_code == 200, reopened.get_json()
