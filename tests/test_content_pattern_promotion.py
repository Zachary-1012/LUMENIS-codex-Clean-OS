"""Isolated engineering acceptance, never real learning lift or production approval.

Positive qualification is a server-authority test double. No HTTP field can
provide it; real independent task qualification remains explicitly unverified.
"""
import json
import pytest
from tests.test_content_scoped_patterns import client, create, HEADERS
from tests.test_saved_document_workflow import workspace, _save
from lumenis.system.security import permission as p


def evaluated(client):
    http, ws = client
    source, created = create(client)
    baseline = _save(ws, request_id="pattern-baseline-1", markdown="Fiction. A paper boat. It returns home.")
    candidate = _save(ws, request_id="pattern-candidate-1", markdown="Fiction. It returns home. A paper boat.")
    body = {"candidate_hash": created["candidate_hash"],
            "baseline_artifact_id": baseline["artifact"]["artifact_id"],
            "candidate_artifact_id": candidate["artifact"]["artifact_id"],
            "criteria": {"required_phrases": ["A paper boat.", "It returns home."], "max_characters": 200}}
    pid = created["candidate"]["id"]
    response = http.post(f"/api/content/patterns/{pid}/evaluations", json=body, headers=HEADERS)
    assert response.status_code == 201, response.get_json()
    return pid, created, body, response.get_json()


def transition(created, eid, *, request_id="pattern-promote-0001", action="promote", target=None):
    return {"candidate_hash": created["candidate_hash"], "action": action, "selected_evaluation_id": eid,
            "target_decision_id": target, "request_id": request_id, "confirmed": False}


def eligible_fixture(monkeypatch):
    import content_generation as c
    monkeypatch.setattr(c, "_pattern_promotion_qualification", lambda evaluation: {
        "eligible": True, "reasons": [], "qualification": "ISOLATED_SERVER_AUTHORITY_TEST_DOUBLE"})


def prepare(client, pid, body):
    http, ws = client
    response = http.post(f"/api/content/patterns/{pid}/transitions", json=body, headers=HEADERS)
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def confirm(client, pid, body, preview):
    return client[0].post(f"/api/content/patterns/{pid}/transitions", headers=HEADERS,
        json={**body, "confirmed": True, **{k: preview[k] for k in
              ("confirmation_id", "activation_resource", "write_resource")}})


def test_real_artifact_measurement_persist_reopen_recompute_and_not_eligible(client):
    http, ws = client
    pid, created, body, result = evaluated(client)
    measured = result["measurement"]
    assert measured["gain"] == 0 and measured["state"] == "NOT_ELIGIBLE"
    assert measured["outputs"]["candidate"]["numerator"] == 2
    assert measured["outputs"]["candidate"]["denominator"] == 2
    read = http.get(f"/api/content/patterns/{pid}/evaluations/{result['evaluation_id']}", headers=HEADERS)
    assert read.status_code == 200 and read.get_json()["measurement"] == measured
    retry = http.post(f"/api/content/patterns/{pid}/evaluations", json=body, headers=HEADERS)
    assert retry.status_code == 201 and retry.get_json()["evaluation_id"] == result["evaluation_id"]
    denied = prepare(client, pid, transition(created, result["evaluation_id"]))
    assert denied["state"] == "NOT_ELIGIBLE" and denied["activation_performed"] is False
    with ws["repo"].connection() as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='CONTENT_PATTERN_APPROVAL'").fetchone()[0] == 0


@pytest.mark.parametrize("key", ["promotion_eligible", "self_reported_pass", "status", "reviewer", "independent"])
def test_client_qualification_fields_rejected(client, key):
    pid, created, body, result = evaluated(client)
    response = client[0].post(f"/api/content/patterns/{pid}/evaluations", json={**body, key: True}, headers=HEADERS)
    assert response.status_code == 400


def test_mutated_evaluation_record_rejected(client):
    pid, created, body, result = evaluated(client)
    with client[1]["repo"].transaction() as con:
        con.execute("UPDATE evaluation_records SET metric_value=99 WHERE evaluation_id=?",
                    (result["evaluation_records"][0]["evaluation_id"],))
    read = client[0].get(f"/api/content/patterns/{pid}/evaluations/{result['evaluation_id']}", headers=HEADERS)
    assert read.status_code == 403, read.get_json()


def test_positive_software_transition_requires_exact_human_then_idempotent(client, monkeypatch):
    http, ws = client
    pid, created, _, result = evaluated(client)
    eligible_fixture(monkeypatch)
    body = transition(created, result["evaluation_id"])
    denied = http.post(f"/api/content/patterns/{pid}/transitions", json=body, headers=HEADERS)
    assert denied.status_code == 403
    ws["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    preview = prepare(client, pid, body)
    assert preview["state"] == "APPROVAL_REQUIRED"
    forged = dict(preview, write_resource="content-pattern-write:v1:" + "0" * 64)
    assert confirm(client, pid, body, forged).status_code == 403
    done = confirm(client, pid, body, preview)
    assert done.status_code == 200, done.get_json()
    assert done.get_json()["state"] == "COMMITTED"
    again = confirm(client, pid, body, preview)
    assert again.status_code == 200 and again.get_json()["replayed"]
    state = http.get(f"/api/content/patterns/{pid}/state", headers=HEADERS)
    assert state.status_code == 200 and state.get_json()["effective"]
    with ws["repo"].connection() as con:
        rows = con.execute("SELECT outputs_json FROM app_evidence_records WHERE feature_id='CONTENT_PATTERN_APPROVAL' ORDER BY id").fetchall()
    assert [json.loads(r[0])["state"] for r in rows] == ["PREPARED", "CONFIRMED", "CONSUMED"]


def test_revocation_and_other_worker_gate_readback(client, monkeypatch):
    http, ws = client
    pid, created, _, result = evaluated(client)
    eligible_fixture(monkeypatch)
    ws["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    body = transition(created, result["evaluation_id"])
    preview = prepare(client, pid, body)
    # A new Gate has no in-memory approvals/nonces. Durable scoped state is authoritative.
    other = p.PermissionGate()
    other.grant_permission(p.PermissionLevel.COMMIT)
    other.grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    monkeypatch.setattr(p, "get_permission_gate", lambda: other)
    revoked = http.post(f"/api/content/patterns/approvals/{preview['confirmation_id']}/revoke",
                        json={"confirmed": True}, headers=HEADERS)
    assert revoked.status_code == 200 and revoked.get_json()["state"] == "REVOKED"
    assert confirm(client, pid, body, preview).status_code == 403
    assert http.get(f"/api/content/patterns/{pid}/state", headers=HEADERS).get_json()["effective"] is False


def test_failure_between_decision_and_consume_rolls_back(client, monkeypatch):
    pid, created, _, result = evaluated(client)
    eligible_fixture(monkeypatch)
    client[1]["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    body = transition(created, result["evaluation_id"])
    preview = prepare(client, pid, body)
    def fail(*args, **kwargs):
        raise RuntimeError("INJECTED_BEFORE_CONSUME")
    monkeypatch.setattr(p, "consume_pattern_transition", fail)
    failed = confirm(client, pid, body, preview)
    assert failed.status_code >= 400
    with client[1]["repo"].connection() as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='CONTENT_PATTERN_TRANSITION'").fetchone()[0] == 0
        rows = con.execute("SELECT outputs_json FROM app_evidence_records WHERE feature_id='CONTENT_PATTERN_APPROVAL' ORDER BY id").fetchall()
    assert [json.loads(r[0])["state"] for r in rows] == ["PREPARED"]


def test_disable_and_rollback_preserve_decisions(client, monkeypatch):
    pid, created, _, result = evaluated(client)
    eligible_fixture(monkeypatch)
    client[1]["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    body = transition(created, result["evaluation_id"])
    promoted = confirm(client, pid, body, prepare(client, pid, body))
    assert promoted.status_code == 200, promoted.get_json()
    first = promoted.get_json()["decision"]["decision_id"]
    disabled = transition(created, None, action="disable", request_id="pattern-disable-0001")
    off = confirm(client, pid, disabled, prepare(client, pid, disabled))
    assert off.status_code == 200, off.get_json()
    assert client[0].get(f"/api/content/patterns/{pid}/state", headers=HEADERS).get_json()["effective"] is False
    back = transition(created, result["evaluation_id"], action="rollback", target=first, request_id="pattern-rollback-0001")
    done = confirm(client, pid, back, prepare(client, pid, back))
    assert done.status_code == 200, done.get_json()
    with client[1]["repo"].connection() as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='CONTENT_PATTERN_TRANSITION'").fetchone()[0] == 3


def test_cross_scope_reads_and_approval_replay_rejected(client, monkeypatch):
    pid, created, _, result = evaluated(client)
    eligible_fixture(monkeypatch)
    client[1]["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    body = transition(created, result["evaluation_id"])
    preview = prepare(client, pid, body)
    other = {"X-Domain-Id": "BMP", "X-Product-Id": "ZBMP"}
    read = client[0].get(f"/api/content/patterns/{pid}/evaluations/{result['evaluation_id']}", headers=other)
    assert read.status_code >= 400
    revoke = client[0].post(f"/api/content/patterns/approvals/{preview['confirmation_id']}/revoke",
                           json={"confirmed": True}, headers=other)
    assert revoke.status_code == 403
    assert confirm(client, pid, body, preview).status_code == 200


def test_learning_projection_sh05_and_retirement_are_truthful(client):
    http, ws = client
    import experience_runtime
    ws["app"].register_blueprint(experience_runtime.experience_bp)
    pid, created, _, result = evaluated(client)
    view = http.get("/api/experience/screen/SH-05", headers=HEADERS)
    assert view.status_code == 200, view.get_json()
    assert view.get_json()["truth"] == {"learning_count": 1, "effective_count": 0, "business_lift_verified": False}
    assert "NOT_ELIGIBLE" in json.dumps(view.get_json())
    assert http.get("/api/content/patterns/learning", headers=HEADERS).get_json()["items"][0]["evaluations"][0]["measurement"]["gain"] == 0
    assert http.post(f"/api/content/patterns/{pid}/retire", json={"candidate_hash": created["candidate_hash"], "confirmed": True}, headers=HEADERS).status_code == 200
    retired = http.get("/api/content/patterns/learning", headers=HEADERS)
    assert retired.status_code == 200, retired.get_json()
    assert retired.get_json()["items"][0]["state"] == "RETIRED"


def test_permission_withdrawal_before_commit_rolls_back(client, monkeypatch):
    pid, created, _, result = evaluated(client)
    eligible_fixture(monkeypatch)
    client[1]["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    body = transition(created, result["evaluation_id"])
    preview = prepare(client, pid, body)
    original = p.consume_pattern_transition
    def consume_then_withdraw(*args, **kwargs):
        result = original(*args, **kwargs)
        client[1]["gate"].revoke_permission(p.PermissionLevel.HUMAN_APPROVAL)
        return result
    monkeypatch.setattr(p, "consume_pattern_transition", consume_then_withdraw)
    assert confirm(client, pid, body, preview).status_code == 403
    with client[1]["repo"].connection() as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='CONTENT_PATTERN_TRANSITION'").fetchone()[0] == 0


def _process_pattern_request(app, path, body, barrier, queue):
    try:
        barrier.wait(timeout=15)
        response = app.test_client().post(path, json=body, headers=HEADERS)
        queue.put((response.status_code, response.get_json()))
    except BaseException as exc:
        queue.put(("error", repr(exc)))


def test_separate_process_confirmation_and_revocation_are_serialized(client, monkeypatch):
    import multiprocessing
    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("This process test requires fork; no claim of other platforms passing.")
    pid, created, _, result = evaluated(client)
    eligible_fixture(monkeypatch)
    client[1]["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    body = transition(created, result["evaluation_id"])
    preview = prepare(client, pid, body)
    confirmed = {**body, "confirmed": True, **{key: preview[key] for key in
                  ("confirmation_id", "activation_resource", "write_resource")}}
    ctx = multiprocessing.get_context("fork")
    barrier, queue = ctx.Barrier(2), ctx.Queue()
    calls = [(f"/api/content/patterns/{pid}/transitions", confirmed),
             (f"/api/content/patterns/approvals/{preview['confirmation_id']}/revoke", {"confirmed": True})]
    workers = [ctx.Process(target=_process_pattern_request, args=(client[1]["app"], path, payload, barrier, queue))
               for path, payload in calls]
    for child in workers:
        child.start()
    try:
        outputs = [queue.get(timeout=30) for _ in workers]
        for child in workers:
            child.join(timeout=10)
            assert child.exitcode == 0
        assert all(code != "error" for code, _ in outputs), outputs
        with client[1]["repo"].connection() as con:
            rows = con.execute("SELECT outputs_json FROM app_evidence_records WHERE feature_id='CONTENT_PATTERN_APPROVAL' ORDER BY id").fetchall()
            count = con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='CONTENT_PATTERN_TRANSITION'").fetchone()[0]
        states = [json.loads(row[0])["state"] for row in rows]
        assert (states, count) == (["PREPARED", "REVOKED"], 0), outputs
        if count == 1:
            assert any(value.get("state") == "ALREADY_EXECUTED" for _, value in outputs), outputs
        else:
            assert any(code == 403 for code, _ in outputs), outputs
    finally:
        for child in workers:
            if child.is_alive():
                child.terminate()
            child.join(timeout=5)
        queue.close()


@pytest.mark.parametrize("error,status", [(PermissionError("private /workspace/key.sql"), 403),
                                          (RuntimeError("SELECT private FROM /private/database"), 503)])
def test_sh05_errors_never_leak_or_become_empty_success(client, monkeypatch, error, status):
    import content_generation as c
    import experience_runtime
    client[1]["app"].register_blueprint(experience_runtime.experience_bp)
    def fail():
        raise error
    monkeypatch.setattr(c, "read_pattern_learning_projection", fail)
    result = client[0].get("/api/experience/screen/SH-05", headers=HEADERS)
    assert result.status_code == status
    assert result.get_json()["ok"] is False and result.get_json()["bound"] is False
    assert "private" not in result.get_data(as_text=True) and "trace" not in result.get_data(as_text=True)


def test_evaluation_unexpected_error_is_sanitized(client, monkeypatch):
    import content_generation as c
    def fail(*args, **kwargs):
        raise RuntimeError("SELECT secret FROM /private/production.sqlite")
    monkeypatch.setattr(c, "_pattern_current", fail)
    response = client[0].get("/api/content/patterns/CLA-private/state", headers=HEADERS)
    assert response.status_code == 503
    assert response.get_json() == {"ok": False, "code": "PATTERN_SERVICE_UNAVAILABLE"}


def _ordered_process_pattern_request(app, path, body, wait_event, done_event, queue):
    try:
        if wait_event is not None:
            assert wait_event.wait(20)
        response = app.test_client().post(path, json=body, headers=HEADERS)
        queue.put((response.status_code, response.get_json()))
    except BaseException as exc:
        queue.put(("error", repr(exc)))
    finally:
        done_event.set()


@pytest.mark.parametrize("first_action", ["confirm", "revoke"])
def test_real_process_both_commit_orders(client, monkeypatch, first_action):
    import multiprocessing
    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("Fork process runner is unavailable on this platform.")
    pid, created, _, result = evaluated(client)
    eligible_fixture(monkeypatch)
    client[1]["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    body = transition(created, result["evaluation_id"])
    preview = prepare(client, pid, body)
    confirm_body = {**body, "confirmed": True, **{key: preview[key] for key in
                    ("confirmation_id", "activation_resource", "write_resource")}}
    calls = {"confirm": (f"/api/content/patterns/{pid}/transitions", confirm_body),
             "revoke": (f"/api/content/patterns/approvals/{preview['confirmation_id']}/revoke", {"confirmed": True})}
    order = [first_action, "revoke" if first_action == "confirm" else "confirm"]
    ctx = multiprocessing.get_context("fork")
    ready, finished, queue = ctx.Event(), ctx.Event(), ctx.Queue()
    revoke_path, revoke_body = calls["revoke"]
    worker = ctx.Process(target=_ordered_process_pattern_request,
        args=(client[1]["app"], revoke_path, revoke_body,
              ready if first_action == "confirm" else None, finished, queue))
    workers = [worker]
    worker.start()
    try:
        if first_action == "revoke":
            assert finished.wait(timeout=20)
        response = client[0].post(*[calls["confirm"][0]], json=calls["confirm"][1], headers=HEADERS)
        ready.set()
        outputs = [(response.status_code, response.get_json()), queue.get(timeout=30)]
        worker.join(10)
        assert worker.exitcode == 0
        assert all(code != "error" for code, _ in outputs), outputs
        with client[1]["repo"].connection() as con:
            rows = con.execute("SELECT outputs_json FROM app_evidence_records WHERE feature_id='CONTENT_PATTERN_APPROVAL' ORDER BY id").fetchall()
            count = con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='CONTENT_PATTERN_TRANSITION'").fetchone()[0]
        states = [json.loads(row[0])["state"] for row in rows]
        if first_action == "confirm":
            assert states == ["PREPARED", "CONFIRMED", "CONSUMED"] and count == 1, outputs
            assert any(value.get("state") == "ALREADY_EXECUTED" for _, value in outputs), outputs
        else:
            assert states == ["PREPARED", "REVOKED"] and count == 0, outputs
            assert any(code == 403 for code, _ in outputs), outputs
    finally:
        for child in workers:
            if child.is_alive():
                child.terminate()
            child.join(5)
        queue.close()


def test_tampered_disable_context_cannot_resurrect_promotion(client, monkeypatch):
    pid, created, _, result = evaluated(client)
    eligible_fixture(monkeypatch)
    client[1]["gate"].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    body = transition(created, result["evaluation_id"])
    assert confirm(client, pid, body, prepare(client, pid, body)).status_code == 200
    off = transition(created, None, action="disable", request_id="pattern-disable-tamper")
    assert confirm(client, pid, off, prepare(client, pid, off)).status_code == 200
    with client[1]["repo"].transaction() as con:
        con.execute("UPDATE app_evidence_records SET inputs_json=? WHERE id=(SELECT MAX(id) FROM app_evidence_records WHERE feature_id='CONTENT_PATTERN_TRANSITION')",
                    (json.dumps({"context": {"domain_id": "another"}}),))
    read = client[0].get(f"/api/content/patterns/{pid}/state", headers=HEADERS)
    assert read.status_code >= 400
    assert read.get_json().get("effective") is not True


def test_shared_sh05_exact_read_and_corrupt_signature(client):
    from tests.test_content_scoped_patterns import candidate
    from tests.test_saved_document_workflow import _source
    import experience_runtime
    http, ws = client
    ws["app"].register_blueprint(experience_runtime.experience_bp)
    headers = {"X-Lumenis-Workspace-Scope": json.dumps({"scope_kind": "shared_workspace", "version": 1})}
    _, _, source = _source(ws)
    created = http.post("/api/content/patterns", json=candidate(source["evidence_id"]), headers=headers)
    assert created.status_code == 201, created.get_json()
    response = http.get("/api/experience/screen/SH-05", headers=headers)
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["truth"]["learning_count"] == 1
    # SH-01 is now an exact authorized read consumer; neighboring screens remain denied.
    with ws["app"].test_request_context("/api/experience/screen/SH-01", headers=headers):
        assert experience_runtime._shared_content_project_route_allowed()
    with ws["app"].test_request_context("/api/experience/screen/SH-02", headers=headers):
        assert not experience_runtime._shared_content_project_route_allowed()
    assert http.post("/api/experience/screen/SH-05", headers=headers).status_code == 405
    with ws["repo"].transaction() as con:
        con.execute("UPDATE app_evidence_records SET integrity_digest='corrupt' WHERE feature_id='CONTENT_SCOPED_OUTCOME'")
    failed = http.get("/api/experience/screen/SH-05", headers=headers)
    assert failed.status_code == 503, failed.get_json()
    assert failed.get_json()["code"] == "LEARNING_DATA_UNAVAILABLE"


def test_shared_sh05_account_authority_revocation_and_forged_actor(client):
    import account.models
    import experience_runtime
    http, ws = client
    ws["app"].register_blueprint(experience_runtime.experience_bp)
    ws["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    with ws["repo"].transaction() as con:
        con.executescript(account.models.BASE_TABLES_SQL)
        con.executemany("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES (?,?,?,?,?)",
                        [(1,"learning-owner","not-a-login","owner","active"),
                         (2,"learning-reader","not-a-login","viewer","active")])
        con.executemany("INSERT INTO v4_sessions(user_id,token,expires_at) VALUES (?,?,?)",
                        [(1,"learning-owner-session","2099-01-01 00:00:00"),
                         (2,"learning-reader-session","2099-01-01 00:00:00")])
    scope = {"scope_kind": "shared_workspace", "version": 1}
    headers = {"X-Lumenis-Workspace-Scope": json.dumps(scope)}
    path = "/api/experience/screen/SH-05"
    assert http.get(path, headers=headers).status_code == 403
    owner = {**headers, "Authorization": "Bearer learning-owner-session"}
    assert http.get(path, headers=owner).status_code == 200
    reader = {**headers, "Authorization": "Bearer learning-reader-session"}
    assert http.get(path, headers=reader).status_code == 403
    forged = {**owner, "X-Lumenis-Workspace-Scope": json.dumps({**scope, "actor_id": 2})}
    assert http.get(path, headers=forged).status_code == 403
    with ws["repo"].transaction() as con:
        con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    assert http.get(path, headers=owner).status_code == 403
