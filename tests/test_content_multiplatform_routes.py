"""Real isolated local principal, focused scope, DB, source import and review.

No Global fallback, account scope mock or Permission bypass. Inputs are explicit
engineering fixtures and do not establish customer or language acceptance.
"""
import copy
import json
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_content_multiplatform import spec
from lumenis.system.security import permission as p


@pytest.fixture
def client(workspace, monkeypatch):
    import content_generation as c
    from subject_registry import add_subject
    ws = workspace
    first, _ = add_subject({"domain_id": "CTH", "subject_type": "company", "name_en": "Creation A", "name_zh": "Creation A"})
    other, _ = add_subject({"domain_id": "CTH", "subject_type": "company", "name_en": "Creation B", "name_zh": "Creation B"})
    ws["scope"] = {"domain_id": "cth", "subject_id": first["subject_id"], "brand_focus_id": None, "global_scope": False}
    ws["headers"] = {"X-Domain-Id": "CTH", "X-Product-Id": "CTH", "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": first["subject_id"]}
    ws["other"] = {**ws["headers"], "X-Subject-ID": other["subject_id"]}
    monkeypatch.setattr(c, "get_repository", lambda: ws["repo"])
    def no_ai(*args, **kwargs):
        pytest.fail("Deterministic creation called AI")
    monkeypatch.setattr(c, "_call_ai", no_ai)
    c.init_db()
    ws["app"].register_blueprint(c.content_bp)
    yield ws["app"].test_client(), ws


def create(client, request_id="multiplatform-create-1", value=None):
    http, ws = client
    response = http.post("/api/content/multiplatform/drafts", headers=ws["headers"], json={"request_id": request_id, "spec": value or spec()})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["result"]


def source_spec(client):
    _, ws = client
    value = spec()
    content = "\n".join([v["title"] for v in value["variants"]] + [f["texts"]["en"] for f in value["facts"]])
    path = ws["root"] / "launch-facts.txt"; path.write_text(content)
    provenance = {"source_url": "https://example.org/explicit-engineering-fixture", "published_at": None,
        "captured_at": "2026-10-17T14:00:00Z", "rights": "public-reference-only", "title": "Generated launch fixture"}
    args = {"actor": ws["actor"], "scope": ws["scope"], "provenance": provenance}
    resource = ws["documents"].document_import_resource(str(path), **args)
    ws["gate"].grant_approval(p.OperationType.DATA_IMPORT.value, resource=resource, granted_by="isolated-test")
    imported = ws["documents"].import_document(str(path), **args)
    for f in value["facts"]:
        text = f["texts"]["en"]; start = content.index(text)
        f["citation"] = {"evidence_id": imported["evidence_id"], "start": start, "end": start + len(text), "quote": text}
    return value, imported, content


def test_no_ai_save_independent_reopen_idempotency_and_focus(client):
    http, ws = client
    saved = create(client); aid = saved["artifact"]["artifact_id"]
    assert saved["document"]["context"]["global_scope"] is False
    assert saved["document"]["context"]["subject_id"] == ws["scope"]["subject_id"]
    read = http.get("/api/content/multiplatform/drafts/" + aid, headers=ws["headers"])
    assert read.status_code == 200 and read.get_json()["result"]["document"] == saved["document"], read.get_json()
    assert create(client)["replayed"]
    independent = ws["work"].reopen_work(aid, actor=ws["actor"], scope=ws["scope"])
    assert independent["document"] == saved["document"]
    assert http.get("/api/content/multiplatform/drafts/" + aid, headers=ws["other"]).status_code >= 400
    assert http.get("/api/content/multiplatform/drafts/" + aid, headers={"X-Domain-Id": "CTH", "X-Product-Id": "CTH"}).status_code >= 400
    assert http.get("/api/content/types").get_json()


def test_real_source_citations_unknown_rights_and_changed_source_denied(client):
    http, ws = client
    value, imported, _ = source_spec(client)
    saved = create(client, value=value)
    package = saved["document"]["payload"]["multiplatform"]
    assert package["source_bindings"][0]["rights"] == "public-reference-only"
    assert len(saved["document"]["citations"]) == 3
    assert all(c["verification"] == "NOT_VERIFIED" for c in saved["document"]["payload"]["claims"])
    bad = copy.deepcopy(value); bad["facts"][0]["citation"]["quote"] = "Not in source"
    response = http.post("/api/content/multiplatform/drafts", headers=ws["headers"], json={"request_id": "bad-source-01", "spec": bad})
    assert response.status_code >= 400
    with ws["repo"].transaction() as con:
        con.execute("UPDATE app_evidence_records SET content_hash='changed' WHERE id=?", (imported["evidence_id"],))
    assert http.get("/api/content/multiplatform/drafts/" + saved["artifact"]["artifact_id"], headers=ws["headers"]).status_code >= 400


def test_edit_restore_new_versions_and_no_old_review_reuse(client):
    http, ws = client
    first = create(client); v = first["document"]["payload"]["multiplatform"]["variants"][0]
    body = {"request_id": "multiplatform-edit-1", "expected_sha256": first["artifact"]["sha256"], "reason": "Correct fixture timing",
            "edits": [{"variant_id": v["id"], "expected_body_sha256": v["body_sha256"], "body": "Corrected timing remains to be reviewed."}]}
    path = "/api/content/multiplatform/drafts/" + first["artifact"]["artifact_id"] + "/revisions"
    response = http.post(path, headers=ws["headers"], json=body)
    assert response.status_code == 201, response.get_json()
    second = response.get_json()["result"]
    assert second["document"]["version"] == 2
    assert second["document"]["payload"]["content_review"]["decision"] == "NOT_VERIFIED"
    assert http.post(path, headers=ws["headers"], json=body).get_json()["result"]["replayed"]
    restore = {"request_id": "multiplatform-restore-1", "expected_sha256": second["artifact"]["sha256"], "reason": "Restore original wording for review", "restore_artifact_id": first["artifact"]["artifact_id"]}
    result = http.post("/api/content/multiplatform/drafts/" + second["artifact"]["artifact_id"] + "/revisions", headers=ws["headers"], json=restore)
    assert result.status_code == 201, result.get_json()
    third = result.get_json()["result"]
    assert third["document"]["version"] == 3 and third["document"]["markdown"] == first["document"]["markdown"]
    assert third["document"]["payload"]["multiplatform_revision"]["review_status"] == "RESET_FOR_NEW_VERSION"
    conflict = {**body, "request_id": "multiplatform-conflict-1"}
    assert http.post(path, headers=ws["headers"], json=conflict).status_code == 409


def test_transaction_failure_rolls_back_artifact_and_receipt(client, monkeypatch):
    import content_generation as c
    http, ws = client
    def fail(*args, **kwargs): raise ValueError("INJECTED_COMMIT_FAILURE")
    with ws["repo"].connection() as con:
        before = con.execute("SELECT count(*) FROM lumenis_shared_artifacts").fetchone()[0]
    monkeypatch.setattr(c, "_record_content_work", fail)
    response = http.post("/api/content/multiplatform/drafts", headers=ws["headers"], json={"request_id": "atomic-create-01", "spec": spec()})
    assert response.status_code >= 400
    with ws["repo"].connection() as con:
        assert con.execute("SELECT count(*) FROM lumenis_shared_artifacts").fetchone()[0] == before
        assert con.execute("SELECT count(*) FROM content_generation_evidence").fetchone()[0] == 0


def test_shared_scope_without_global_and_no_source_still_draft(client):
    http, ws = client
    headers = {"X-Lumenis-Workspace-Scope": json.dumps({"scope_kind": "shared_workspace", "version": 1})}
    result = http.post("/api/content/multiplatform/drafts", headers=headers, json={"request_id": "shared-create-01", "spec": spec()})
    assert result.status_code == 201, result.get_json()
    saved = result.get_json()["result"]
    assert saved["document"]["context"]["scope_kind"] == "shared_workspace"
    assert "global_scope" not in saved["document"]["context"]
    assert http.get("/api/content/multiplatform/drafts/" + saved["artifact"]["artifact_id"], headers=ws["headers"]).status_code >= 400


def review(client, saved, imported, source_text, *, risk="pass", draft_digest=None):
    import content_generation as c
    http, ws = client
    ws["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    claims = []
    for claim in saved["document"]["payload"]["claims"]:
        text = claim["text"]
        start = source_text.index(text)
        claims.append({"claim_id": claim["claim_id"], "decision": "supported_by_human_review",
            "reason": "Explicit engineering reviewer checked source span; not customer approval",
            "locators": [{"evidence_id": imported["evidence_id"], "start": start, "end": start + len(text), "quote": text}]})
    body = {"confirmed": False, "all_factual_claims_enumerated": True,
        "draft_digest": draft_digest or saved["document"]["draft_digest"], "claims": claims,
        "dimensions": {key: {"status": risk if key == "risk" else "pass", "reason": "Explicit engineering reviewer decision"} for key in c.CONTENT_REVIEW_DIMENSIONS}}
    path = "/api/content/drafts/" + saved["artifact"]["artifact_id"] + "/reviews"
    prepared = http.post(path, headers=ws["headers"], json=body)
    assert prepared.status_code == 200, prepared.get_json()
    body.update(confirmed=True, confirmed_resource=prepared.get_json()["resource"], confirmation_id=prepared.get_json()["confirmation_id"])
    result = http.post(path, headers=ws["headers"], json=body)
    assert result.status_code == 201, result.get_json()
    return result.get_json(), path


def test_real_claim_review_withdrawal_and_revision_requires_new_review(client):
    http, ws = client
    value, imported, text = source_spec(client)
    first = create(client, value=value)
    approved, path = review(client, first, imported, text)
    assert approved["review"]["decision"] == "READY"
    status = http.get(path + "/" + approved["review_evidence_id"], headers=ws["headers"])
    assert status.status_code == 200 and len(status.get_json()["eligible_claim_ids"]) == 16
    withdrawal, _ = review(client, first, imported, text, risk="fail")
    assert withdrawal["review"]["decision"] == "BLOCKED"
    assert http.get(path + "/" + approved["review_evidence_id"], headers=ws["headers"]).status_code == 403
    v = first["document"]["payload"]["multiplatform"]["variants"][0]
    update = {"request_id": "reviewed-edit-0001", "expected_sha256": first["artifact"]["sha256"], "reason": "Edit after withdrawal",
        "edits": [{"variant_id": v["id"], "expected_body_sha256": v["body_sha256"], "body": "The date is not confirmed."}]}
    second = http.post("/api/content/multiplatform/drafts/" + first["artifact"]["artifact_id"] + "/revisions", headers=ws["headers"], json=update)
    assert second.status_code == 201, second.get_json()
    saved = second.get_json()["result"]
    wrong_review = "/api/content/drafts/" + saved["artifact"]["artifact_id"] + "/reviews/" + approved["review_evidence_id"]
    assert http.get(wrong_review, headers=ws["headers"]).status_code >= 400
    assert saved["document"]["payload"]["content_review"]["decision"] == "NOT_VERIFIED"


def test_unavailable_language_cannot_be_reviewed_as_complete_bundle(client):
    value, imported, text = source_spec(client)
    value["variants"][3]["locale"] = "ko"
    saved = create(client, value=value)
    reviewed, _ = review(client, saved, imported, text)
    assert reviewed["review"]["decision"] == "NEEDS_REVISION"


def test_commit_failure_after_owner_receipt_leaves_no_draft(client, monkeypatch):
    import content_generation as c
    http, ws = client
    original = c._record_content_work
    def fail_after(*args, **kwargs):
        original(*args, **kwargs)
        raise ValueError("INJECTED_AFTER_SIGNED_RECEIPT")
    monkeypatch.setattr(c, "_record_content_work", fail_after)
    result = http.post("/api/content/multiplatform/drafts", headers=ws["headers"], json={"request_id": "after-receipt-01", "spec": spec()})
    assert result.status_code >= 400
    with ws["repo"].connection() as con:
        assert con.execute("SELECT count(*) FROM content_generation_evidence").fetchone()[0] == 0
        assert con.execute("SELECT count(*) FROM lumenis_shared_artifacts").fetchone()[0] == 0


def test_owner_receipt_required_for_copied_metadata(client):
    http, ws = client
    first = create(client)
    forged = ws["work"].save_work(title=first["document"]["title"], markdown=first["document"]["markdown"], kind="research",
        payload=first["document"]["payload"], citations=[], request_id="copied-multi-0001", actor=ws["actor"], scope=ws["scope"])
    path = "/api/content/multiplatform/drafts/" + forged["artifact"]["artifact_id"]
    assert http.get(path, headers=ws["headers"]).status_code == 403
    doc = first["document"]
    generic = {"title": "Generic copy", "text": "Cannot silently drop variant provenance", "claims": [], "request_id": "generic-parent-01",
        "parent": {"artifact_id": first["artifact"]["artifact_id"], "sha256": first["artifact"]["sha256"], "draft_digest": doc["draft_digest"], "adopt_unverified_parent": False}}
    assert http.post("/api/content/drafts", headers=ws["headers"], json=generic).status_code >= 400


def test_permission_denial_reserved_context_and_inactive_focus(client):
    http, ws = client
    bad = {"request_id": "reserved-create-01", "spec": spec(), "_content_context": {"admin": True}}
    assert http.post("/api/content/multiplatform/drafts", headers=ws["headers"], json=bad).status_code >= 400
    saved = create(client)
    ws["repo"].execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE subject_id=?", (ws["scope"]["subject_id"],))
    assert http.get("/api/content/multiplatform/drafts/" + saved["artifact"]["artifact_id"], headers=ws["headers"]).status_code >= 400


def test_account_isolation_uses_real_sessions_in_shared_scope(client):
    import account.models
    http, ws = client
    with ws["repo"].transaction() as con:
        con.executescript(account.models.BASE_TABLES_SQL)
        con.executemany("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES (?,?,?,'owner','active')", [(1, 'creator-one', 'not-a-login'), (2, 'creator-two', 'not-a-login')])
        con.executemany("INSERT INTO v4_sessions(user_id,token,expires_at) VALUES (?,?,?)", [(1, 'creation-one-token', '2099-01-01 00:00:00'), (2, 'creation-two-token', '2099-01-01 00:00:00')])
    ws["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    shared = {"X-Lumenis-Workspace-Scope": json.dumps({"scope_kind": "shared_workspace", "version": 1})}
    one = {**shared, "Authorization": "Bearer creation-one-token"}
    two = {**shared, "Authorization": "Bearer creation-two-token"}
    result = http.post("/api/content/multiplatform/drafts", headers=one, json={"request_id": "account-create-01", "spec": spec()})
    assert result.status_code == 201, result.get_json()
    saved = result.get_json()["result"]
    assert saved["document"]["context"]["actor_id"] == 1
    path = "/api/content/multiplatform/drafts/" + saved["artifact"]["artifact_id"]
    assert http.get(path, headers=two).status_code >= 400
    assert http.get(path, headers=one).status_code == 200
    ws["repo"].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    assert http.get(path, headers=one).status_code >= 400


def test_fact_sheet_revision_updates_all_variants_and_retains_diff(client):
    http, ws = client
    first = create(client)
    updated = spec()
    updated["facts"][0]["texts"]["en"] = "The demonstration opening date is now 21 October, pending review."
    response = http.post("/api/content/multiplatform/drafts/" + first["artifact"]["artifact_id"] + "/revisions", headers=ws["headers"],
        json={"request_id": "fact-update-001", "expected_sha256": first["artifact"]["sha256"], "reason": "Update shared fact sheet", "spec": updated})
    assert response.status_code == 201, response.get_json()
    saved = response.get_json()["result"]
    assert all(updated["facts"][0]["texts"]["en"] in v["body"] for v in saved["document"]["payload"]["multiplatform"]["variants"])
    assert saved["document"]["payload"]["multiplatform_revision"]["fact_sheet_changed"]
    assert saved["document"]["payload"]["content_review"]["decision"] == "NOT_VERIFIED"
