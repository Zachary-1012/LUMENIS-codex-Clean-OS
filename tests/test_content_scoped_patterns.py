"""Real isolated importer -> scoped research -> pattern -> saved work contracts."""
import json
import pytest
from tests.test_saved_document_workflow import workspace, _source
from lumenis.system.security import permission as p

HEADERS = {"X-Domain-Id": "CTH", "X-Product-Id": "CTH"}

@pytest.fixture
def client(workspace, monkeypatch):
    import content_generation as c
    from lumenis.shared.learning import operations
    monkeypatch.setattr(c, "get_repository", lambda: workspace["repo"])
    monkeypatch.setattr(operations, "_operation_learning", operations.OperationLearning(workspace["root"] / "learning"))
    c.init_db()
    app = workspace["app"]
    app.register_blueprint(c.content_bp)
    return app.test_client(), workspace


def candidate(ref):
    return {"asset_type": "narrative", "title": "Action leads explanation", "source_evidence_refs": [ref],
        "extracted_principle": "Present the action before explaining the intent.",
        "reusable_pattern": {"sequence": ["action", "intent"]}, "evidence_requirements": ["verify claims"],
        "originality_boundary": "Do not copy wording or identity", "legal_or_compliance_boundary": "Research only",
        "counterexamples": ["Safety instructions may need explanation first"],
        "platform_scope": ["podcast"], "format_scope": ["outline"], "audience_scope": ["general"],
        "objective_scope": ["explain"]}


def create(client):
    http, ws = client
    _, _, source = _source(ws)
    response = http.post("/api/content/patterns", json=candidate(source["evidence_id"]), headers=HEADERS)
    assert response.status_code == 201, response.get_json()
    return source, response.get_json()


def apply_body(created):
    return {"candidate_hash": created["candidate_hash"], "confirmed": True, "request_id": "pattern-apply-001",
            "brief": {"title": "How a story starts", "text": "My original outline", "platform": "podcast",
                      "format": "outline", "audience": "general", "objective": "explain"}}


def test_scoped_pattern_full_roundtrip_and_retire(client):
    http, ws = client
    source, created = create(client)
    pattern_id = created["candidate"]["id"]
    search = http.get(f"/api/content/research/search?q=Original&evidence_id={source['evidence_id']}", headers=HEADERS)
    assert search.status_code == 200, search.get_json()
    assert len(search.get_json()["db_results"]) == 1
    found = http.get("/api/content/patterns?platform=podcast", headers=HEADERS)
    assert len(found.get_json()["candidates"]) == 1, found.get_json()
    response = http.post(f"/api/content/patterns/{pattern_id}/apply", json=apply_body(created), headers=HEADERS)
    assert response.status_code == 201, response.get_json()
    result = response.get_json()["result"]
    artifact = result["artifact"]["artifact_id"]
    reopened = ws["work"].reopen_work(artifact, actor=ws["actor"], scope=ws["scope"])
    assert reopened["document"]["payload"]["application_trace"]["pattern_id"] == pattern_id
    assert reopened["document"]["payload"]["brief"]["text"] == "My original outline"
    replay = http.post(f"/api/content/patterns/{pattern_id}/apply", json=apply_body(created), headers=HEADERS)
    assert replay.status_code == 201, replay.get_json()
    assert replay.get_json()["result"]["replayed"]
    retired = http.post(f"/api/content/patterns/{pattern_id}/retire", json={"candidate_hash": created["candidate_hash"], "confirmed": True}, headers=HEADERS)
    assert retired.status_code == 200, retired.get_json()
    assert http.get("/api/content/patterns", headers=HEADERS).get_json()["candidates"] == []
    assert http.post(f"/api/content/patterns/{pattern_id}/apply", json=apply_body(created), headers=HEADERS).status_code == 409
    assert ws["work"].reopen_work(artifact, actor=ws["actor"], scope=ws["scope"])["document"] == reopened["document"]


def test_scope_unknown_sources_and_forged_context_denied(client):
    http, ws = client
    source, created = create(client)
    eid = created["evidence_id"]
    assert http.get(f"/api/content/evidence/{eid}", headers=HEADERS).status_code == 200
    other = {"X-Domain-Id": "BMP", "X-Product-Id": "ZBMP"}
    assert http.get(f"/api/content/evidence/{eid}", headers=other).status_code == 404
    assert http.get("/api/content/evidence", headers=other).get_json()["data"]["items"] == []
    assert http.get("/api/content/patterns", headers=other).get_json()["candidates"] == []
    resources = http.get("/api/content/resources", headers=HEADERS).get_json()
    assert {(row["evidence_id"], row["source_id"]) for row in resources["data"]} == {
        (source["evidence_id"], source["source_id"])}
    assert resources["verification_complete"] is True
    assert http.get("/api/content/resources", headers=other).get_json()["data"] == []
    forged = candidate(source["evidence_id"]); forged["_content_context"] = {}
    assert http.post("/api/content/patterns", headers=HEADERS, json=forged).status_code >= 400
    bad = apply_body(created); bad["confirmed"] = False
    assert http.post(f"/api/content/patterns/{created['candidate']['id']}/apply", headers=HEADERS, json=bad).status_code >= 400
    with ws["repo"].transaction() as con:
        con.execute("UPDATE app_evidence_records SET content_hash='tampered' WHERE id=?", (source["evidence_id"],))
    assert http.get("/api/content/patterns", headers=HEADERS).get_json()["candidates"] == []
    assert http.get(f"/api/content/evidence/{eid}", headers=HEADERS).status_code == 404
    resources = http.get("/api/content/resources", headers=HEADERS).get_json()
    assert resources["data"] == [] and resources["verification_complete"] is False


def test_legacy_unbound_outcome_hidden_and_generated_failure_honest(client):
    http, ws = client
    import content_generation as c
    eid = c.record_evidence("ad_copy", {}, "private", "private", "private", {}, "none", "none", "low", 0, 0, "failed")
    assert http.get(f"/api/content/evidence/{eid}", headers=HEADERS).status_code == 404
    assert c.search_research_library("secret") == []
    assert c.search_research_filesystem("secret") == []


def test_shared_independent_pattern_consumer(client):
    http, ws = client
    _, _, source = _source(ws)
    headers = {"X-Lumenis-Workspace-Scope": json.dumps({"scope_kind": "shared_workspace", "version": 1})}
    response = http.post("/api/content/patterns", json=candidate(source["evidence_id"]), headers=headers)
    assert response.status_code == 201, response.get_json()
    created = response.get_json()
    assert created["candidate"]["access_context"]["shared_workspace_scope"]["scope_kind"] == "shared_workspace"
    applied = http.post(f"/api/content/patterns/{created['candidate']['id']}/apply", json=apply_body(created), headers=headers)
    assert applied.status_code == 201, applied.get_json()
    assert applied.get_json()["result"]["document"]["context"]["scope_kind"] == "shared_workspace"
    assert http.get("/api/content/patterns", headers=HEADERS).get_json()["candidates"] == []


def test_actual_account_session_isolation_and_revocation(client):
    http, ws = client
    import account.models
    with ws["repo"].transaction() as con:
        con.executescript(account.models.BASE_TABLES_SQL)
        con.executemany("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES (?,?,?,'owner','active')", [(1,'one','not-a-login'), (2,'two','not-a-login')])
        con.executemany("INSERT INTO v4_sessions(user_id,token,expires_at) VALUES (?,?,?)", [(1,'content-fixture-one','2099-01-01 00:00:00'), (2,'content-fixture-two','2099-01-01 00:00:00')])
    ws["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    one = {**HEADERS, "Authorization": "Bearer content-fixture-one"}
    two = {**HEADERS, "Authorization": "Bearer content-fixture-two"}
    draft = {"title": "Original draft", "text": "An original story", "claims": [], "request_id": "account-draft-01"}
    result = http.post("/api/content/drafts", json=draft, headers=one)
    assert result.status_code == 201, result.get_json()
    assert result.get_json()["result"]["document"]["context"]["actor_id"] == 1
    import content_generation as c
    ws["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    saved_one = result.get_json()["result"]
    saved_two = http.post("/api/content/drafts", json=draft, headers=two).get_json()["result"]
    path_one = f"/api/content/drafts/{saved_one['artifact']['artifact_id']}/reviews"
    path_two = f"/api/content/drafts/{saved_two['artifact']['artifact_id']}/reviews"
    review = {"confirmed":False, "all_factual_claims_enumerated":True,
              "draft_digest":saved_one["document"]["draft_digest"], "claims":[],
              "dimensions":{key:{"status":"pass","reason":"Account owner explicit review"} for key in c.CONTENT_REVIEW_DIMENSIONS}}
    preview = http.post(path_one, headers=one, json=review)
    assert preview.status_code == 200, preview.get_json()
    prepared = preview.get_json()
    review.update(confirmed=True, confirmed_resource=prepared["resource"], confirmation_id=prepared["confirmation_id"])
    stolen = {**review, "draft_digest":saved_two["document"]["draft_digest"]}
    assert http.post(path_two, headers=two, json=stolen).status_code == 403
    assert http.post(path_one, headers=two, json=review).status_code >= 400
    exact = http.post(path_one, headers=one, json=review)
    assert exact.status_code == 201, exact.get_json()
    assert http.post(path_one, headers=one, json=review).status_code == 403
    _, _, account_source = _source({**ws, "actor": {"id": 1, "role": "owner"}})
    account_pattern = http.post("/api/content/patterns", json=candidate(account_source["evidence_id"]), headers=one)
    assert account_pattern.status_code == 201, account_pattern.get_json()
    account_eid = account_pattern.get_json()["evidence_id"]
    assert http.get(f"/api/content/evidence/{account_eid}", headers=two).status_code == 404
    assert http.get("/api/content/patterns", headers=two).get_json()["candidates"] == []
    assert http.post(f"/api/content/patterns/{account_pattern.get_json()['candidate']['id']}/apply",
                     json=apply_body(account_pattern.get_json()), headers=one).status_code == 201
    assert http.post("/api/content/drafts", json=draft, headers={**HEADERS,"Authorization":"Bearer invalid"}).status_code >= 400
    with ws["repo"].transaction() as con:
        con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    assert http.post("/api/content/drafts", json=draft, headers=one).status_code >= 400
    assert http.post("/api/content/drafts", json=draft, headers=two).status_code == 201


def test_nine_dimension_claim_review_current_receipt_and_withdrawal(client):
    http, ws = client
    import content_generation as c
    from podcast.intelligence.research_pipeline import ResearchClaim, EvidenceStatus, evidence_gate
    # Self-asserted confidence or labels cannot admit facts; drafts remain allowed.
    assert evidence_gate([ResearchClaim("claim-1", "Original source line", ("123",), EvidenceStatus.HUMAN_VERIFIED, 1)]) == []
    _, _, source = _source(ws)
    text = "Original source line"
    draft = http.post("/api/content/drafts", headers=HEADERS, json={"title":"Review draft", "text":text,
        "request_id":"claim-review-draft-1", "claims":[{"claim_id":"claim-1","text":text,"start":0,"end":len(text)}]})
    assert draft.status_code == 201, draft.get_json()
    saved = draft.get_json()["result"]
    artifact = saved["artifact"]["artifact_id"]
    body = {"confirmed":True, "all_factual_claims_enumerated":True, "draft_digest":saved["document"]["draft_digest"],
        "dimensions":{key:{"status":"pass","reason":"Explicit fixture human assessment"} for key in c.CONTENT_REVIEW_DIMENSIONS},
        "claims":[{"claim_id":"claim-1","decision":"supported_by_human_review","reason":"Reviewer checked the exact original span",
                   "locators":[{"evidence_id":source["evidence_id"],"start":0,"end":len(text),"quote":text}]}]}
    path = f"/api/content/drafts/{artifact}/reviews"
    assert http.post(path, headers=HEADERS, json=body).status_code == 403
    ws["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    bad = json.loads(json.dumps(body)); bad["claims"][0]["locators"][0]["quote"] = "invented"
    assert http.post(path, headers=HEADERS, json=bad).status_code >= 400
    assert http.post(path, headers=HEADERS, json=body).status_code == 403
    def approve_exact(decisions):
        preview = http.post(path, headers=HEADERS, json={**decisions, "confirmed": False})
        assert preview.status_code == 200, preview.get_json()
        prepared = preview.get_json()
        assert prepared["binding"]["review"]["claims"]
        decisions["confirmed_resource"] = prepared["resource"]
        decisions["confirmation_id"] = prepared["confirmation_id"]
    approve_exact(body)
    changed = json.loads(json.dumps(body)); changed["dimensions"]["risk"]["reason"] = "Changed after approval"
    assert http.post(path, headers=HEADERS, json=changed).status_code == 403
    response = http.post(path, headers=HEADERS, json=body)
    assert response.status_code == 201, response.get_json()
    reviewed = response.get_json()
    assert reviewed["review"]["decision"] == "READY"
    assert not reviewed["review"]["automatic_semantic_truth_verification"]
    status = http.get(path+"/"+reviewed["review_evidence_id"], headers=HEADERS)
    assert status.status_code == 200, status.get_json()
    assert status.get_json()["eligible_claim_ids"] == ["claim-1"]
    body["dimensions"]["risk"] = {"status":"fail", "reason":"Human withdraws earlier readiness"}
    assert http.post(path, headers=HEADERS, json=body).status_code == 403
    approve_exact(body)
    withdrawal = http.post(path, headers=HEADERS, json=body)
    assert withdrawal.status_code == 201, withdrawal.get_json()
    assert withdrawal.get_json()["review"]["decision"] == "BLOCKED"
    assert http.get(path+"/"+reviewed["review_evidence_id"], headers=HEADERS).status_code == 403
    assert http.get(path+"/"+withdrawal.get_json()["review_evidence_id"], headers=HEADERS).get_json()["eligible_claim_ids"] == []
    with ws["repo"].transaction() as con:
        con.execute("UPDATE app_evidence_records SET content_hash='changed' WHERE id=?", (source["evidence_id"],))
    assert http.get(path+"/"+withdrawal.get_json()["review_evidence_id"], headers=HEADERS).status_code == 403


def test_focus_original_scope_revocation_and_pattern_backup_cannot_revive(client):
    http, ws = client
    from subject_registry import add_subject
    from lumenis.shared.learning import operations
    first, _ = add_subject({"domain_id":"CTH","subject_type":"company","name_en":"Focus A","name_zh":"Focus A"})
    second, _ = add_subject({"domain_id":"CTH","subject_type":"company","name_en":"Focus B","name_zh":"Focus B"})
    focused = {**ws["scope"],"subject_id":first["subject_id"],"global_scope":False}
    _, _, source = _source({**ws,"scope":focused})
    headers = {**HEADERS,"X-Lumenis-Context-Mode":"FOCUS","X-Subject-ID":first["subject_id"]}
    response = http.post("/api/content/patterns",headers=headers,json=candidate(source["evidence_id"]))
    assert response.status_code==201,response.get_json()
    created=response.get_json(); pid=created["candidate"]["id"]
    other={**headers,"X-Subject-ID":second["subject_id"]}
    assert http.get("/api/content/patterns",headers=other).get_json()["candidates"]==[]
    assert http.get("/api/content/patterns",headers=HEADERS).get_json()["candidates"]==[]
    persistence=operations.get_operation_learning().persistence
    old=persistence.load_collection("patterns")
    assert http.post(f"/api/content/patterns/{pid}/retire",headers=headers,json={"candidate_hash":created["candidate_hash"],"confirmed":True}).status_code==200
    persistence.save_collection("patterns",old)
    assert http.get("/api/content/patterns",headers=headers).get_json()["candidates"]==[]
    assert http.post(f"/api/content/patterns/{pid}/apply",headers=headers,json=apply_body(created)).status_code==409
    ws["repo"].execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE subject_id=?",(first["subject_id"],))
    assert http.get("/api/content/patterns",headers=headers).status_code>=400


def test_post_signature_revocation_rolls_back_outcome_and_receipt(client,monkeypatch):
    http,ws=client
    _,_,source=_source(ws)
    from lumenis.shared.evidence import store
    original=store.record_evidence
    def revoke(**kwargs):
        result=original(**kwargs)
        if kwargs.get("feature_id")=="CONTENT_SCOPED_OUTCOME":
            ws["gate"].revoke_permission(p.PermissionLevel.VERIFY)
        return result
    monkeypatch.setattr(store,"record_evidence",revoke)
    response=http.post("/api/content/patterns",headers=HEADERS,json=candidate(source["evidence_id"]))
    assert response.status_code>=400,response.get_json()
    with ws["repo"].connection(read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM content_generation_evidence").fetchone()[0]==0
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='CONTENT_SCOPED_OUTCOME'").fetchone()[0]==0


def test_shared_effect_rejects_wrong_endpoint_hash_and_context(client):
    _,ws=client
    import content_generation as c
    from flask import g
    headers={"X-Lumenis-Workspace-Scope":json.dumps({"scope_kind":"shared_workspace","version":1})}
    with ws["app"].test_request_context('/api/content/drafts',method='POST',json={"text":"fixture"},headers=headers,environ_overrides={"REMOTE_ADDR":"127.0.0.1"}):
        c.authorize_content_root_request(strict=True)
        resource=c.content_derived_resource()
        assert c.validate_content_derived_resource(resource,actor=g.content_actor,scope=g.content_scope['shared_workspace_scope'])
        assert not c.validate_content_derived_resource('content-derived:v1:'+'0'*64)
        denied=p.check_shared_workspace_effect(g.content_actor,g.content_scope['shared_workspace_scope'],p.OperationType.DATA_EXPORT,
            'content-derived:v1:'+'0'*64,module='content',action='write')
        assert not denied.allowed
        g.content_context={**g.content_context,"actor_id":999}
        assert not c.validate_content_derived_resource(resource)
    with ws["app"].test_request_context('/api/content/not-an-owner',method='POST',json={"text":"fixture"},headers=headers,environ_overrides={"REMOTE_ADDR":"127.0.0.1"}):
        assert not c.validate_content_derived_resource(resource)


@pytest.mark.parametrize("operation", ["create", "retire"])
@pytest.mark.parametrize("failure", ["before_write", "after_write", "readback"])
def test_pattern_failure_rolls_back_both_owners(client, monkeypatch, operation, failure):
    http, ws = client
    import content_generation as c
    from lumenis.shared.learning import operations
    source, created = create(client)
    persistence = operations.get_operation_learning().persistence
    original_save, original_load = persistence.save_collection, persistence.load_collection
    before = json.loads(json.dumps(original_load("patterns")))
    with ws["repo"].connection(read_only=True, wal=False) as con:
        evidence_count = con.execute("SELECT count(*) FROM content_generation_evidence").fetchone()[0]
        receipt_count = con.execute("SELECT count(*) FROM app_evidence_records").fetchone()[0]
    state = {"fired": False, "readback": False}
    def failing_save(name, data, immediate=True):
        if name != "patterns" or state["fired"]:
            return original_save(name, data, immediate=immediate)
        state["fired"] = True
        if failure == "before_write":
            raise RuntimeError("injected before write")
        result = original_save(name, data, immediate=immediate)
        if failure == "after_write":
            raise RuntimeError("injected after write")
        state["readback"] = True
        return result
    def failing_load(name):
        if name == "patterns" and state["readback"]:
            state["readback"] = False
            raise RuntimeError("injected readback failure")
        return original_load(name)
    monkeypatch.setattr(persistence, "save_collection", failing_save)
    monkeypatch.setattr(persistence, "load_collection", failing_load)
    if operation == "create":
        response = http.post("/api/content/patterns", headers=HEADERS, json={**candidate(source["evidence_id"]), "request_id":"failure-new-creation"})
    else:
        response = http.post(f"/api/content/patterns/{created['candidate']['id']}/retire", headers=HEADERS,
                             json={"confirmed": True, "candidate_hash": created["candidate_hash"]})
    assert response.status_code >= 400, response.get_json()
    assert original_load("patterns") == before
    with ws["repo"].connection(read_only=True, wal=False) as con:
        assert con.execute("SELECT count(*) FROM content_generation_evidence").fetchone()[0] == evidence_count
        assert con.execute("SELECT count(*) FROM app_evidence_records").fetchone()[0] == receipt_count
    assert len(http.get("/api/content/patterns", headers=HEADERS).get_json()["candidates"]) == 1


def test_explicit_signed_recovery_and_committed_retirement_denial(client):
    http, ws = client
    from lumenis.shared.learning import operations
    source, created = create(client)
    pid = created['candidate']['id']
    persistence = operations.get_operation_learning().persistence
    original = persistence.load_collection('patterns')
    interrupted = json.loads(json.dumps(original))
    interrupted[pid]['lifecycle_state'] = 'retired'
    interrupted[pid]['version'] += '.retired'
    interrupted[pid]['previous_version_hash'] = created['candidate_hash']
    persistence.save_collection('patterns', interrupted)
    ws['gate'].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    path = f'/api/content/patterns/{pid}/recovery'
    preview = http.post(path, headers=HEADERS, json={'confirmed':False})
    assert preview.status_code == 200, preview.get_json()
    prepared = preview.get_json()
    assert prepared['binding']['replacement'] == original[pid]
    body = {'confirmed':True, 'confirmation_id':prepared['confirmation_id'], 'confirmed_resource':prepared['resource']}
    assert http.post(path, headers={"X-Domain-Id":"BMP","X-Product-Id":"ZBMP"}, json=body).status_code >= 400
    changed = json.loads(json.dumps(interrupted)); changed[pid]['title'] = 'changed after preview'
    persistence.save_collection('patterns', changed)
    assert http.post(path, headers=HEADERS, json=body).status_code == 403
    prepared = http.post(path, headers=HEADERS, json={'confirmed':False}).get_json()
    body.update(confirmation_id=prepared['confirmation_id'], confirmed_resource=prepared['resource'])
    response = http.post(path, headers=HEADERS, json=body)
    assert response.status_code == 200, response.get_json()
    assert persistence.load_collection('patterns') == original
    assert http.post(path, headers=HEADERS, json=body).status_code >= 400
    assert http.post(f'/api/content/patterns/{pid}/apply', headers=HEADERS, json=apply_body(created)).status_code == 201
    assert http.post(f'/api/content/patterns/{pid}/retire', headers=HEADERS,
                     json={'confirmed':True,'candidate_hash':created['candidate_hash']}).status_code == 200
    persistence.save_collection('patterns', original)
    blocked = http.post(path, headers=HEADERS, json={'confirmed':False})
    assert blocked.status_code >= 400 and blocked.get_json()['code'] == 'PATTERN_COMMITTED_RETIREMENT_CANNOT_RECOVER'


def test_uncommitted_create_diagnose_discard_and_same_request_retry(client):
    http, ws = client
    source, created = create(client)
    pid = created['candidate']['id']
    with ws['repo'].transaction() as con:
        con.execute("DELETE FROM app_evidence_records WHERE asset_id=? AND feature_id='CONTENT_SCOPED_OUTCOME'", (created['evidence_id'],))
        con.execute('DELETE FROM content_generation_evidence WHERE evidence_id=?', (created['evidence_id'],))
    original_request = candidate(source['evidence_id'])
    diagnosis = http.post('/api/content/patterns', headers=HEADERS, json=original_request)
    assert diagnosis.status_code == 409 and diagnosis.get_json()['pattern_id'] == pid
    ws['gate'].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    path = diagnosis.get_json()['recovery_url']
    preview = http.post(path, headers=HEADERS, json={'confirmed':False})
    assert preview.status_code == 200, preview.get_json()
    prepared = preview.get_json()
    assert prepared['binding']['action'] == 'discard_uncommitted_create'
    response = http.post(path, headers=HEADERS, json={'confirmed':True,
        'confirmation_id':prepared['confirmation_id'], 'confirmed_resource':prepared['resource']})
    assert response.status_code == 200, response.get_json()
    retried = http.post('/api/content/patterns', headers=HEADERS, json=original_request)
    assert retried.status_code == 201 and retried.get_json()['candidate']['id'] == pid
    replayed = http.post('/api/content/patterns', headers=HEADERS, json=original_request)
    assert replayed.status_code == 201 and replayed.get_json()['replayed']


def continuation_body(parent, *, request_id="content-continuation-001", text="An original scene.\n\nOriginal source line"):
    claim = "Original source line"
    start = text.index(claim) if claim in text else -1
    return {"title": "Original authored story", "text": text, "request_id": request_id,
        "claims": [] if start < 0 else [{"claim_id": "claim-1", "text": claim, "start": start, "end": start+len(claim)}],
        "parent": {"artifact_id": parent["artifact"]["artifact_id"], "sha256": parent["artifact"]["sha256"],
            "draft_digest": parent["document"]["draft_digest"], "adopt_unverified_parent": False}}


def applied_work(client):
    http, ws = client
    source, created = create(client)
    response = http.post(f"/api/content/patterns/{created['candidate']['id']}/apply", json=apply_body(created), headers=HEADERS)
    assert response.status_code == 201, response.get_json()
    return source, created, response.get_json()["result"]


def test_continuation_retired_parent_review_reset_and_replay(client):
    http, ws = client
    source, created, parent = applied_work(client)
    assert http.post(f"/api/content/patterns/{created['candidate']['id']}/retire", headers=HEADERS,
        json={"candidate_hash":created["candidate_hash"],"confirmed":True}).status_code == 200
    body = continuation_body(parent)
    response = http.post("/api/content/drafts", headers=HEADERS, json=body)
    assert response.status_code == 201, response.get_json()
    child = response.get_json()["result"]
    doc = child["document"]
    assert doc["work_id"] == parent["document"]["work_id"] and doc["version"] == 2
    assert doc["parent_sha256"] == parent["artifact"]["sha256"]
    assert doc["citations"] == parent["document"]["citations"]
    assert doc["payload"]["content_origin"]["application_trace"] == parent["document"]["payload"]["application_trace"]
    assert doc["payload"]["content_continuation"]["parent_owner_receipt_id"]
    assert doc["payload"]["content_review"]["decision"] == "NOT_VERIFIED"
    assert all(x["status"] == "not_verified" for x in doc["payload"]["content_review"]["dimensions"].values())
    assert doc["payload"]["claims"][0]["verification"] == "NOT_VERIFIED"
    replay = http.post("/api/content/drafts", headers=HEADERS, json=body)
    assert replay.status_code == 201 and replay.get_json()["result"]["replayed"]
    stale = {**body, "request_id":"content-stale-parent-001"}
    assert http.post("/api/content/drafts", headers=HEADERS, json=stale).status_code >= 400
    conflict = {**body, "text":"Changed", "claims":[]}
    assert http.post("/api/content/drafts", headers=HEADERS, json=conflict).status_code >= 400
    assert ws["work"].reopen_work(parent["artifact"]["artifact_id"], actor=ws["actor"], scope=ws["scope"])["document"] == parent["document"]
    second = http.post("/api/content/drafts", headers=HEADERS,
        json=continuation_body(child, request_id="content-continuation-002", text="Another original story."))
    assert second.status_code == 201, second.get_json()
    assert second.get_json()["result"]["document"]["version"] == 3
    assert second.get_json()["result"]["document"]["payload"]["content_origin"] == doc["payload"]["content_origin"]


def test_continuation_forged_trace_requires_current_explicit_adoption(client):
    http, ws = client
    _, _, original = applied_work(client)
    forged = ws["work"].save_work(title="Copied metadata", markdown=original["document"]["markdown"],
        kind="research", payload=original["document"]["payload"], citations=original["document"]["citations"],
        request_id="copied-parent-0001", actor=ws["actor"], scope=ws["scope"])
    body = continuation_body(forged)
    denied = http.post("/api/content/drafts", headers=HEADERS, json=body)
    assert denied.status_code == 403 and denied.get_json()["code"] == "CONTENT_PARENT_EXPLICIT_ADOPTION_REQUIRED"
    body["parent"]["adopt_unverified_parent"] = True
    adopted = http.post("/api/content/drafts", headers=HEADERS, json=body)
    assert adopted.status_code == 201, adopted.get_json()
    payload = adopted.get_json()["result"]["document"]["payload"]
    assert "content_origin" not in payload
    assert payload["content_continuation"]["parent_owner_receipt_id"] is None
    assert payload["content_continuation"]["adoption"] == "EXPLICIT_CURRENT_ADOPTION"
    assert payload["unverified_parent_context"]["past_owner_execution"] == "NOT_VERIFIED"
    assert payload["unverified_parent_context"]["historical_payload"] == original["document"]["payload"]
    injected = {**continuation_body(original), "application_trace": original["document"]["payload"]["application_trace"]}
    assert http.post("/api/content/drafts", headers=HEADERS, json=injected).status_code >= 400


def test_continuation_source_scope_hash_and_receipt_denials(client):
    http, ws = client
    source, _, parent = applied_work(client)
    body = continuation_body(parent)
    assert http.post("/api/content/drafts", headers={"X-Domain-Id":"BMP","X-Product-Id":"ZBMP"}, json=body).status_code >= 400
    wrong = json.loads(json.dumps(body)); wrong["parent"]["sha256"] = "0"*64
    assert http.post("/api/content/drafts", headers=HEADERS, json=wrong).status_code >= 400
    with ws["repo"].transaction() as con:
        con.execute("UPDATE app_evidence_records SET content_hash='tampered' WHERE id=?", (source["evidence_id"],))
    assert http.post("/api/content/drafts", headers=HEADERS, json=body).status_code >= 400


@pytest.mark.parametrize("failure", ["receipt", "after_receipt", "readback"])
def test_continuation_atomic_failure_retry(client, monkeypatch, failure):
    http, ws = client
    import content_generation as c
    _, _, parent = applied_work(client)
    body = continuation_body(parent)
    with ws["repo"].connection(read_only=True, wal=False) as con:
        before = [con.execute("SELECT count(*) FROM "+table).fetchone()[0] for table in
            ["content_generation_evidence", "app_evidence_records", "lumenis_shared_artifacts"]]
    original = c._record_content_work
    def fail(kind, *args, **kwargs):
        if kind == "content_draft":
            if failure == "after_receipt": original(kind, *args, **kwargs)
            raise RuntimeError("Injected content continuation failure")
        return original(kind, *args, **kwargs)
    if failure != "readback":
        monkeypatch.setattr(c, "_record_content_work", fail)
    else:
        reopen = ws["work"].reopen_work
        def fail_reopen(aid, *args, **kwargs):
            if aid != parent["artifact"]["artifact_id"]: raise RuntimeError("Injected postcommit readback failure")
            return reopen(aid, *args, **kwargs)
        monkeypatch.setattr(ws["work"], "reopen_work", fail_reopen)
    response = http.post("/api/content/drafts", headers=HEADERS, json=body)
    assert response.status_code >= 400
    with ws["repo"].connection(read_only=True, wal=False) as con:
        after = [con.execute("SELECT count(*) FROM "+table).fetchone()[0] for table in
            ["content_generation_evidence", "app_evidence_records", "lumenis_shared_artifacts"]]
    if failure != "readback": assert after == before
    else: assert after[0] == before[0]+1 and after[1] == before[1]+1 and after[2] == before[2]+1
    monkeypatch.setattr(c, "_record_content_work", original)
    if failure == "readback": monkeypatch.setattr(ws["work"], "reopen_work", reopen)
    retried = http.post("/api/content/drafts", headers=HEADERS, json=body)
    assert retried.status_code == 201, retried.get_json()
    assert retried.get_json()["result"]["replayed"] == (failure == "readback")


def test_continuation_real_account_parent_isolation_and_revocation(client):
    http, ws = client
    import account.models
    with ws["repo"].transaction() as con:
        con.executescript(account.models.BASE_TABLES_SQL)
        con.executemany("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES (?,?,?,'owner','active')", [(1,'one','not-a-login'),(2,'two','not-a-login')])
        con.executemany("INSERT INTO v4_sessions(user_id,token,expires_at) VALUES (?,?,?)", [(1,'continuation-one','2099-01-01 00:00:00'),(2,'continuation-two','2099-01-01 00:00:00')])
    ws["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    one = {**HEADERS,"Authorization":"Bearer continuation-one"}
    two = {**HEADERS,"Authorization":"Bearer continuation-two"}
    response = http.post('/api/content/drafts',headers=one,json={'title':'One draft','text':'Original source line','claims':[], 'request_id':'owner-one-parent-001'})
    assert response.status_code == 201, response.get_json()
    parent=response.get_json()['result']; body=continuation_body(parent)
    denied=http.post('/api/content/drafts',headers=two,json=body)
    assert denied.status_code>=400
    assert 'Original source line' not in json.dumps(denied.get_json())
    accepted=http.post('/api/content/drafts',headers=one,json=body)
    assert accepted.status_code==201,accepted.get_json()
    with ws['repo'].transaction() as con: con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    assert http.post('/api/content/drafts',headers=one,json=continuation_body(accepted.get_json()['result'],request_id='disabled-child-001')).status_code>=400


def test_continuation_receipt_tamper_cannot_be_legacy_adopted(client):
    http, ws = client
    _,_,parent=applied_work(client)
    with ws['repo'].transaction() as con:
        con.execute("UPDATE content_generation_evidence SET output_json='{}' WHERE content_type='pattern_application'")
    body=continuation_body(parent);body['parent']['adopt_unverified_parent']=True
    response=http.post('/api/content/drafts',headers=HEADERS,json=body)
    assert response.status_code==403 and response.get_json()['code']=='CONTENT_PARENT_RECEIPT_INVALID'


def _withdraw_source_use(ws, evidence_id):
    from lumenis.shared.evidence import store
    with ws['repo'].transaction() as con:
        row=dict(con.execute('SELECT * FROM app_evidence_records WHERE id=?',(evidence_id,)).fetchone())
        metadata=json.loads(row['collection_metadata']);metadata['provenance']['intended_use']='forbidden'
        con.execute('UPDATE app_evidence_records SET collection_metadata=? WHERE id=?',(json.dumps(metadata),evidence_id))
        store._sign_evidence_record(con,evidence_id)
        assert store.verify_evidence_record_integrity(dict(con.execute('SELECT * FROM app_evidence_records WHERE id=?',(evidence_id,)).fetchone()))


@pytest.mark.parametrize('stage', ['preview', 'confirm', 'status'])
@pytest.mark.parametrize('claim_covers_first_only', [False, True])
def test_continuation_review_checks_all_inherited_source_uses(client, stage, claim_covers_first_only):
    http,ws=client
    import content_generation as c
    _,_,one=_source(ws)
    _,_,two=_source(ws, filename='another-reference.txt', source_url='https://example.org/another')
    data=candidate(one['evidence_id']);data['source_evidence_refs']=[one['evidence_id'],two['evidence_id']]
    r=http.post('/api/content/patterns',headers=HEADERS,json=data)
    assert r.status_code==201,r.get_json()
    created=r.get_json()
    r=http.post(f"/api/content/patterns/{created['candidate']['id']}/apply",headers=HEADERS,json=apply_body(created))
    assert r.status_code==201,r.get_json()
    body=continuation_body(r.get_json()['result'],text='Original source line' if claim_covers_first_only else 'An imagined quiet scene.')
    r=http.post('/api/content/drafts',headers=HEADERS,json=body)
    assert r.status_code==201,r.get_json()
    child=r.get_json()['result'];path=f"/api/content/drafts/{child['artifact']['artifact_id']}/reviews"
    ws['gate'].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    review={'confirmed':False,'all_factual_claims_enumerated':True,'draft_digest':child['document']['draft_digest'],
        'dimensions':{key:{'status':'pass','reason':'Explicit engineering reviewer assessment'} for key in c.CONTENT_REVIEW_DIMENSIONS},
        'claims':[] if not claim_covers_first_only else [{'claim_id':'claim-1','decision':'supported_by_human_review',
            'reason':'Exact first source span checked','locators':[{'evidence_id':one['evidence_id'], 'start':0,'end':20,'quote':'Original source line'}]}]}
    if stage=='preview':
        _withdraw_source_use(ws,two['evidence_id'])
        denied=http.post(path,headers=HEADERS,json=review)
    else:
        preview=http.post(path,headers=HEADERS,json=review)
        assert preview.status_code==200,preview.get_json()
        material=preview.get_json()
        assert {s['evidence_id'] for s in material['binding']['source_bindings']}=={one['evidence_id'],two['evidence_id']}
        assert material['binding']['review']['draft_source_evidence_ids']==[one['evidence_id'],two['evidence_id']]
        # Inherited references never automatically become claim evidence.
        claims=material['binding']['review']['claims']
        assert claims==[] if not claim_covers_first_only else claims[0]['evidence_ids']==[str(one['evidence_id'])]
        review.update(confirmed=True,confirmation_id=material['confirmation_id'],confirmed_resource=material['resource'])
        if stage=='confirm':
            _withdraw_source_use(ws,two['evidence_id'])
            denied=http.post(path,headers=HEADERS,json=review)
        else:
            confirmed=http.post(path,headers=HEADERS,json=review)
            assert confirmed.status_code==201,confirmed.get_json()
            review_id=confirmed.get_json()['review_evidence_id']
            assert http.get(path+'/'+review_id,headers=HEADERS).status_code==200
            _withdraw_source_use(ws,two['evidence_id'])
            denied=http.get(path+'/'+review_id,headers=HEADERS)
    assert denied.status_code>=400,denied.get_json()
    assert body['text'] not in json.dumps(denied.get_json())
