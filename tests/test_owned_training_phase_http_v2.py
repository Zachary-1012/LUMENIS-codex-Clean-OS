"""HTTP boundary tests for sealed owned-training phase metadata (no trainer)."""
from __future__ import annotations

import ast
from contextlib import contextmanager
from datetime import datetime, timedelta
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import sqlite3
import threading
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from flask import Flask, jsonify, request
import pytest

import ai_task_engine
import experience_runtime as runtime
from lumenis.shared.database import repository
from lumenis.system.ai_gateway.owned_training import TrainingApprovalRequest
from lumenis.system.security import permission as p
from lumenis.system.security import training_receipts as receipts


TASK_URL = "/api/experience/owned-training/phase-tasks"
CHALLENGE_URL = TASK_URL + "/{task_id}/challenges"
DECISION_URL = TASK_URL + "/{task_id}/challenge-decisions"
INTERRUPT_URL = TASK_URL + "/{task_id}/interrupt"
RESUME_URL = TASK_URL + "/{task_id}/resume"
RECEIPT_URL = TASK_URL + "/{task_id}/receipts/{nonce}"
BASE_HEADERS = {
    "Host": "localhost", "X-Domain-Id": "CTH", "X-Product-Id": "CTH",
    "X-Lumenis-Context-Mode": "GLOBAL_ALL",
}
TASK_OWNER = "owned_training_phase_receipts:v1"


@pytest.fixture(autouse=True)
def strict_permission_mode(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)
    thread_ids = {id(thread) for thread in threading.enumerate()}
    child_pids = {child.pid for child in multiprocessing.active_children()}
    yield
    assert not [thread for thread in threading.enumerate()
                if id(thread) not in thread_ids and thread.is_alive()]
    assert not [child for child in multiprocessing.active_children()
                if child.pid not in child_pids and child.is_alive()]


def _training_request():
    return {
        "model_id": "openai/gpt-oss-20b",
        "model_revision": "6cee5e81ee83917806bbde320786a8fb61efebee",
        "train_sha256": "1" * 64,
        "heldout_sha256": "2" * 64,
        "scopes": ["GLOBAL / ALL"],
        "recipe": "openai-h100-bf16",
        "manifest_sha256": "3" * 64,
        "domain_id": "cth",
    }


def _descriptors():
    return {"GLOBAL / ALL": {
        "domain_id": "cth", "product_id": "CTH", "global_scope": True,
        "subject_id": None, "brand_focus_id": None,
    }}


def _request_object(body):
    return TrainingApprovalRequest(
        model_id=body["model_id"], model_revision=body["model_revision"],
        train_sha256=body["train_sha256"], heldout_sha256=body["heldout_sha256"],
        domain_id=body["domain_id"], scopes=tuple(body["scopes"]),
        recipe=body["recipe"], manifest_sha256=body["manifest_sha256"],
    )


def _actual_app_guards(app, gate):
    """Compile the exact current resolver and before_request guard from app.py."""
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename="app.py")
    names = {"_pg_resolve_operation_type", "_permission_gate_write_check"}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in functions} == names
    namespace = {
        "request": request, "jsonify": jsonify,
        "OperationType": p.OperationType,
        "_PG_WRITE_METHODS": {"POST", "PUT", "DELETE", "PATCH"},
        "_PG_BYPASS_PATHS": frozenset(), "_pg": gate,
    }
    resolver_node, guard_node = functions
    resolver_node.decorator_list = []
    guard_node.decorator_list = []
    exec(compile(ast.Module(body=[resolver_node], type_ignores=[]), "app.py", "exec"), namespace)
    exec(compile(ast.Module(body=[guard_node], type_ignores=[]), "app.py", "exec"), namespace)
    app.before_request(namespace["_permission_gate_write_check"])
    return namespace["_pg_resolve_operation_type"]


def _create_account_tables(path):
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS v4_users (
                id INTEGER PRIMARY KEY, username TEXT NOT NULL, role TEXT NOT NULL,
                status TEXT NOT NULL, display_name TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL DEFAULT '', must_change_password INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS v4_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE, ip TEXT, user_agent TEXT, expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS v4_member_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL, module TEXT NOT NULL, action TEXT NOT NULL,
                data_scope TEXT, time_range TEXT, granted_by INTEGER,
                created_at TEXT, updated_at TEXT
            );
            INSERT OR IGNORE INTO v4_users(id,username,role,status,display_name)
                VALUES (1,'phase-user-a','member','active','Test A'),
                       (2,'phase-user-b','member','active','Test B');
        """)


def _add_account_scope(path, actor_id):
    with sqlite3.connect(path) as conn:
        conn.execute("""INSERT INTO v4_member_authorizations
            (user_id,product_id,module,action,data_scope,time_range,granted_by,created_at,updated_at)
            VALUES (?,'CTH','owned_training','write',?,NULL,1,'test','test')""",
            (actor_id, json.dumps({"global": True}, separators=(",", ":"))))


def _add_session(path, actor_id):
    token = "test-session-" + uuid.uuid4().hex
    expiry = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(path) as conn:
        conn.execute("INSERT INTO v4_sessions(user_id,token,ip,user_agent,expires_at) VALUES(?,?,?,?,?)",
                     (actor_id, token, "127.0.0.1", "isolated-test", expiry))
    return token


def _db_snapshot(path):
    with sqlite3.connect(path) as conn:
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        result = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            rows = conn.execute(f"SELECT * FROM {quoted} ORDER BY rowid").fetchall()
            result[table] = tuple(tuple(row) for row in rows)
        return result


def _task_rows(path):
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        tasks = [dict(row) for row in conn.execute(
            "SELECT * FROM ai_task WHERE created_by=? ORDER BY task_id", (TASK_OWNER,)
        )]
        steps = [dict(row) for row in conn.execute(
            "SELECT s.* FROM ai_task_step s JOIN ai_task t ON t.task_id=s.task_id "
            "WHERE t.created_by=? ORDER BY s.step_id", (TASK_OWNER,)
        )]
        return tasks, steps


def _headers_for(identity):
    headers = dict(BASE_HEADERS)
    if identity and identity.startswith("Bearer "):
        headers["Authorization"] = identity
    return headers


def _post(client, path, body, identity=None):
    return client.post(path, headers=_headers_for(identity), json=body,
                       environ_overrides={"REMOTE_ADDR": "127.0.0.1"})


@pytest.fixture
def phase_http(tmp_path, monkeypatch):
    seed = Path(os.environ["LUMENIS_TEST_SEED_DB"]).resolve()
    assert seed.is_file()
    seed_before = hashlib.sha256(seed.read_bytes()).hexdigest()
    db_path = (tmp_path / "canonical-phase-http.sqlite3").resolve()
    shutil.copyfile(seed, db_path)
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("ZBC_EVIDENCE_DB_PATH", str(db_path))
    monkeypatch.setattr(repository, "_default_repository", repository.DatabaseRepository())
    ai_task_engine.reset_task_engine()
    ai_task_engine.init_task_engine_db()
    _create_account_tables(db_path)
    gate = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})
    monkeypatch.setattr(p, "_default_gate", gate)

    key_id = "http-v2-" + uuid.uuid4().hex[:12]
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    import base64
    monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", json.dumps({
        key_id: base64.b64encode(private_bytes).decode("ascii")
    }))
    monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", key_id)
    app = Flask(__name__)
    app.config.update(TESTING=True, LUMENIS_OPEN_WORKSPACE=True)
    app.register_blueprint(runtime.experience_bp)
    resolver = _actual_app_guards(app, gate)
    phase_errors = []
    original_phase_error = runtime._owned_training_phase_error

    def capture_phase_error(exc):
        phase_errors.append(f"{type(exc).__name__}:{exc}")
        return original_phase_error(exc)

    monkeypatch.setattr(runtime, "_owned_training_phase_error", capture_phase_error)
    client = app.test_client()
    request_data = _training_request()
    body = {"training_request": request_data, "scope_descriptors": _descriptors()}

    def grant(identity_kind="workspace", actor_id=1):
        if identity_kind == "account":
            _add_account_scope(db_path, actor_id)
            session_token = _add_session(db_path, actor_id)
            identity = "Bearer " + session_token
        else:
            identity = None
        with app.test_request_context("/", headers=_headers_for(identity),
                                      environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
            args = ({"actor_id": actor_id} if identity_kind == "account" else {
                "principal": p.resolve_local_workspace_principal(
                    module="owned_training", action="write")
            })
            assert identity_kind == "account" or type(args["principal"]) is p.LocalWorkspacePrincipal
            resource = p.owned_training_approval_resource(
                _request_object(request_data), domain_id="cth",
                context={"scope_descriptors": _descriptors()}, **args,
            )
        approval_token = gate.grant_approval(
            p.OperationType.MODEL_TRAIN.value, resource=resource,
            granted_by="isolated-http-v2-approval-fixture",
        )
        return {"identity": identity, "actor_id": actor_id if identity_kind == "account" else None,
                "resource": resource, "approval_token": approval_token, "kind": identity_kind}

    inventory = os.environ.get("TRAINING_HTTP_V2_DB_INVENTORY")
    if inventory:
        with open(inventory, "a", encoding="utf-8") as handle:
            handle.write(str(db_path) + "\n")
    yield {"app": app, "client": client, "gate": gate, "db": db_path,
           "seed": seed, "seed_before": seed_before, "body": body,
           "request_data": request_data, "grant": grant, "resolver": resolver,
           "initial_key_id": key_id, "initial_public_key": receipts.get_training_receipt_public_key(),
           "phase_errors": phase_errors}
    assert hashlib.sha256(seed.read_bytes()).hexdigest() == seed_before
    ai_task_engine.reset_task_engine()


def _prepare_task(case, grant):
    response = _post(case["client"], TASK_URL, case["body"], grant["identity"])
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["state"] == "PHASE_TASK_PREPARED"
    assert data["training_started"] is False and data["approval_issued"] is False
    assert data["public_challenge_context"]["admission_version"] == 2
    assert "binding" not in json.dumps(data) and "approval_token" not in json.dumps(data)
    assert grant["resource"] not in response.get_data(as_text=True)
    assert grant["approval_token"] not in response.get_data(as_text=True)
    return data["task_id"]


def _prepare_challenge(case, grant, task_id, phase="initial"):
    payload = {**case["body"], "phase": phase}
    case["last_challenge_request_payload"] = payload
    return _post(case["client"], CHALLENGE_URL.format(task_id=task_id),
                 payload, grant["identity"])


def _issue(case, grant, task_id, challenge):
    return _post(case["client"], DECISION_URL.format(task_id=task_id),
                 {**case["body"], "challenge": challenge}, grant["identity"])


def _read(case, grant, task_id, nonce):
    return case["client"].get(RECEIPT_URL.format(task_id=task_id, nonce=nonce),
                               headers=_headers_for(grant["identity"]),
                               environ_overrides={"REMOTE_ADDR": "127.0.0.1"})


def test_exact_grant_creates_one_sealed_v2_task_and_prepare_is_idempotent(phase_http):
    case = phase_http
    grant = case["grant"]()
    first = _prepare_task(case, grant)
    response = _post(case["client"], TASK_URL, case["body"], grant["identity"])
    assert response.status_code == 200 and response.get_json()["task_id"] == first
    tasks, steps = _task_rows(case["db"])
    assert len(tasks) == 1 and steps == []
    assert len(case["gate"]._approvals) == 1
    context = json.loads(tasks[0]["context_json"])
    assert context["managed_owner"] == TASK_OWNER and context["admission"]["schema_version"] == 2
    assert context["next_sequence"] == 1 and context["last_receipt_sha256"] is None


def test_missing_exact_grant_and_wrong_scope_grant_create_no_durable_task(phase_http):
    case = phase_http
    before = _db_snapshot(case["db"])
    no_grant = _post(case["client"], TASK_URL, case["body"])
    assert no_grant.status_code in {403, 400}
    assert _db_snapshot(case["db"]) == before
    wrong_resource = case["gate"].grant_approval(
        p.OperationType.MODEL_TRAIN.value, resource="owned_training:v1:" + "f" * 64,
        granted_by="wrong-scope-fixture")
    wrong = _post(case["client"], TASK_URL, case["body"])
    assert wrong.status_code in {403, 400}
    assert _db_snapshot(case["db"]) == before
    assert wrong_resource in case["gate"]._approvals


def test_server_challenge_pending_replay_and_illegal_graph_transition_have_no_duplicate_step(phase_http):
    case = phase_http
    grant = case["grant"]()
    task_id = _prepare_task(case, grant)
    first = _prepare_challenge(case, grant, task_id, "initial")
    assert first.status_code == 200, (first.get_json(), case["phase_errors"])
    challenge = first.get_json()["challenge"]
    assert challenge["phase"] == "initial" and challenge["sequence"] == 1
    assert "nonce" not in case["last_challenge_request_payload"]
    replay = _prepare_challenge(case, grant, task_id, "initial")
    assert replay.status_code == 200 and replay.get_json()["challenge"] == challenge
    before = _db_snapshot(case["db"])
    illegal = _prepare_challenge(case, grant, task_id, "before_train")
    assert illegal.status_code in {403, 409}
    assert _db_snapshot(case["db"]) == before
    tasks, steps = _task_rows(case["db"])
    assert len(tasks) == 1 and len(steps) == 1


@pytest.mark.parametrize("extra", ["actor_id", "principal", "approval_token", "binding", "authorization"])
def test_client_cannot_supply_extra_authority_fields(phase_http, extra):
    case = phase_http
    grant = case["grant"]()
    before = _db_snapshot(case["db"])
    response = _post(case["client"], TASK_URL, {**case["body"], extra: "forged"}, grant["identity"])
    assert response.status_code == 400
    assert _db_snapshot(case["db"]) == before


@pytest.mark.parametrize("bad_body", [
    b'{"training_request":{},"training_request":{},"scope_descriptors":{}}',
    b'{"training_request":{"value":NaN},"scope_descriptors":{}}',
    b" " * 65537,
], ids=["duplicate-json-key", "nan-json", "oversized-body"])
def test_duplicate_json_keys_nan_and_oversized_body_are_rejected_without_writes(phase_http, bad_body):
    case = phase_http
    grant = case["grant"]()
    before = _db_snapshot(case["db"])
    response = case["client"].post(
        TASK_URL, headers={**_headers_for(grant["identity"]), "Content-Type": "application/json"},
        data=bad_body, environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert response.status_code == 400
    assert _db_snapshot(case["db"]) == before


def test_wrong_fingerprints_and_client_nonce_cannot_consume_server_challenge(phase_http):
    case = phase_http
    grant = case["grant"]()
    task_id = _prepare_task(case, grant)
    challenge_response = _prepare_challenge(case, grant, task_id)
    challenge = challenge_response.get_json()["challenge"]
    before = _db_snapshot(case["db"])
    for field in ("request_sha256", "train_sha256", "scope_sha256"):
        wrong = {**challenge, field: "f" * 64}
        result = _issue(case, grant, task_id, wrong)
        assert result.status_code in {400, 403, 409}
        assert _db_snapshot(case["db"]) == before
    client_nonce = {**challenge, "nonce": "e" * 64}
    result = _issue(case, grant, task_id, client_nonce)
    assert result.status_code in {400, 403, 409}
    assert _db_snapshot(case["db"]) == before


def test_real_signature_persists_once_and_lost_post_response_recovers_exact_history(phase_http, monkeypatch):
    case = phase_http
    grant = case["grant"]()
    task_id = _prepare_task(case, grant)
    challenge = _prepare_challenge(case, grant, task_id).get_json()["challenge"]
    sign = receipts.sign_training_phase_decision
    sign_calls = []

    def observed_sign(*args, **kwargs):
        sign_calls.append(1)
        return sign(*args, **kwargs)

    monkeypatch.setattr(receipts, "sign_training_phase_decision", observed_sign)
    original_post = case["client"].post

    class LostResponse(RuntimeError):
        pass

    def lose_after_server_commit(*args, **kwargs):
        response = original_post(*args, **kwargs)
        assert response.status_code == 200
        raise LostResponse("client transport lost response after dispatch")

    monkeypatch.setattr(case["client"], "post", lose_after_server_commit)
    with pytest.raises(LostResponse):
        _issue(case, grant, task_id, challenge)
    monkeypatch.setattr(case["client"], "post", original_post)
    recovered_post = _issue(case, grant, task_id, challenge)
    assert recovered_post.status_code == 200
    assert recovered_post.get_json()["state"] == "PHASE_RECEIPT_ALREADY_COMMITTED"
    assert sign_calls == [1]
    receipt = recovered_post.get_json()["receipt"]
    receipts.verify_training_phase_decision(
        receipt, expected_challenge=challenge,
        pinned_public_key=case["initial_public_key"],
    )
    assert recovered_post.get_json()["model_execution_claimed"] is False
    tasks, steps = _task_rows(case["db"])
    assert len(tasks) == 1 and len(steps) == 1
    context = json.loads(tasks[0]["context_json"])
    assert context["next_sequence"] == 2 and context["admission"]["last_phase"] == "initial"
    historical = _read(case, grant, task_id, challenge["nonce"])
    assert historical.status_code == 200
    historic_json = historical.get_json()
    assert historic_json["receipt"] == receipt and historic_json["challenge"] == challenge
    assert historic_json["historical"] is True and historic_json["authorization_usable"] is False
    assert historic_json["model_execution_claimed"] is False


def test_http_guards_allow_only_exact_five_post_handler_rules(phase_http):
    case = phase_http
    resolver = case["resolver"]
    pairs = [
        ("experience_runtime.prepare_owned_training_phase_task", TASK_URL),
        ("experience_runtime.prepare_owned_training_phase_challenge",
         TASK_URL + "/<task_id>/challenges"),
        ("experience_runtime.issue_owned_training_phase_decision",
         TASK_URL + "/<task_id>/challenge-decisions"),
        ("experience_runtime.interrupt_owned_training_phase_task", TASK_URL + "/<task_id>/interrupt"),
        ("experience_runtime.resume_owned_training_phase_task", TASK_URL + "/<task_id>/resume"),
    ]
    for endpoint, rule in pairs:
        concrete = rule.replace("<task_id>", "trainrelay_00000000-0000-4000-8000-000000000001")
        assert resolver(concrete, "POST") is p.OperationType.DB_WRITE
        assert resolver(concrete + "/suffix", "POST") is p.OperationType.DB_WRITE
        exact_app = Flask("exact-hook-check-" + endpoint.rsplit(".", 1)[-1])
        _actual_app_guards(exact_app, case["gate"])
        hit = []
        exact_app.add_url_rule(rule, endpoint=endpoint,
                               view_func=lambda **_kw: (hit.append("exact"), "ok")[1],
                               methods=["POST"])
        exact_path = concrete
        exact = exact_app.test_client().post(
            exact_path, environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
        assert exact.status_code == 200 and hit == ["exact"]

    before = _db_snapshot(case["db"])
    task_url = TASK_URL
    suffix_app = Flask("suffix-hook-check")
    _actual_app_guards(suffix_app, case["gate"])
    suffix_app.add_url_rule(task_url + "/suffix", endpoint="experience_runtime.prepare_owned_training_phase_task",
                            view_func=lambda: "should-not-run", methods=["POST"])
    suffix = suffix_app.test_client().post(
        task_url + "/suffix", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert suffix.status_code == 403
    wrong_endpoint_app = Flask("endpoint-hook-check")
    _actual_app_guards(wrong_endpoint_app, case["gate"])
    wrong_endpoint_app.add_url_rule(task_url, endpoint="other.endpoint",
                                    view_func=lambda: "should-not-run", methods=["POST"])
    wrong_endpoint = wrong_endpoint_app.test_client().post(
        task_url, environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert wrong_endpoint.status_code == 403
    assert _db_snapshot(case["db"]) == before


def test_account_wrong_identity_deleted_session_and_revoked_module_scope_are_denied(phase_http):
    case = phase_http
    account_a = case["grant"]("account", actor_id=1)
    task_id = _prepare_task(case, account_a)
    account_b = case["grant"]("account", actor_id=2)
    before = _db_snapshot(case["db"])
    denied_wrong_account = _prepare_challenge(case, account_b, task_id)
    assert denied_wrong_account.status_code in {403, 409}
    assert _db_snapshot(case["db"]) == before

    with sqlite3.connect(case["db"]) as conn:
        conn.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND module='owned_training'")
    after_revoke = _db_snapshot(case["db"])
    denied_scope = _prepare_challenge(case, account_a, task_id)
    assert denied_scope.status_code in {400, 403}
    assert _db_snapshot(case["db"]) == after_revoke

    with sqlite3.connect(case["db"]) as conn:
        conn.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) "
                     "VALUES(1,'CTH','owned_training','write',?)",
                     (json.dumps({"global": True}),))
        conn.execute("DELETE FROM v4_sessions WHERE token=?", (account_a["identity"][7:],))
    after_delete = _db_snapshot(case["db"])
    denied_session = _read(case, account_a, task_id, "a" * 64)
    assert denied_session.status_code in {400, 401, 403}
    assert _db_snapshot(case["db"]) == after_delete


def test_forged_transport_and_closed_workspace_cannot_advance_task(phase_http):
    case = phase_http
    grant = case["grant"]()
    task_id = _prepare_task(case, grant)
    before = _db_snapshot(case["db"])
    url = CHALLENGE_URL.format(task_id=task_id)
    response = case["client"].post(
        url, headers=_headers_for(None), json={**case["body"], "phase": "initial"},
        environ_overrides={"REMOTE_ADDR": "192.0.2.8"},
    )
    assert response.status_code in {400, 401, 403}
    assert _db_snapshot(case["db"]) == before

    forwarded = case["client"].post(
        url, headers={**_headers_for(None), "X-Forwarded-For": "127.0.0.1"},
        json={**case["body"], "phase": "initial"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert forwarded.status_code in {400, 401, 403}
    assert _db_snapshot(case["db"]) == before

    forged = case["client"].post(
        url, headers={**_headers_for(None), "X-Actor-ID": "1"},
        json={**case["body"], "phase": "initial"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert forged.status_code in {400, 401, 403}
    assert _db_snapshot(case["db"]) == before

    case["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    closed = _prepare_challenge(case, grant, task_id)
    assert closed.status_code in {400, 401, 403}
    assert _db_snapshot(case["db"]) == before


@pytest.mark.parametrize("grant_change", ["revoke", "expire", "replace", "lost"])
def test_revoked_expired_or_replaced_training_grant_denies_next_phase_without_writes(phase_http, grant_change):
    case = phase_http
    grant = case["grant"]()
    task_id = _prepare_task(case, grant)
    before = _db_snapshot(case["db"])
    if grant_change in {"revoke", "replace"}:
        assert case["gate"].revoke_approval(grant["approval_token"])
    if grant_change == "lost":
        case["gate"]._approvals.pop(grant["approval_token"])
    if grant_change == "expire":
        case["gate"]._approvals[grant["approval_token"]].expires_at = datetime.now() - timedelta(seconds=1)
    if grant_change == "replace":
        replacement = case["gate"].grant_approval(
            p.OperationType.MODEL_TRAIN.value, resource=grant["resource"],
            granted_by="replacement-approval-fixture")
        assert replacement != grant["approval_token"]
    before_attempt = _db_snapshot(case["db"])
    denied = _prepare_challenge(case, grant, task_id)
    assert denied.status_code in {403, 409}
    assert _db_snapshot(case["db"]) == before_attempt
    assert before["ai_task"] == before_attempt["ai_task"]


def test_key_rotation_denies_new_challenge_but_preserves_historical_get_pin(phase_http, monkeypatch):
    case = phase_http
    grant = case["grant"]()
    task_id = _prepare_task(case, grant)
    challenge = _prepare_challenge(case, grant, task_id).get_json()["challenge"]
    committed = _issue(case, grant, task_id, challenge)
    assert committed.status_code == 200
    old_receipt = committed.get_json()["receipt"]
    old_pin = case["initial_public_key"]
    new_id = "rotated-" + uuid.uuid4().hex[:12]
    new_private = Ed25519PrivateKey.generate().private_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    import base64
    monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", json.dumps({
        new_id: base64.b64encode(new_private).decode("ascii")
    }))
    monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", new_id)
    before = _db_snapshot(case["db"])
    denied = _prepare_challenge(case, grant, task_id, "before_output_dir")
    assert denied.status_code in {403, 409, 503}
    assert _db_snapshot(case["db"]) == before
    historical = _read(case, grant, task_id, challenge["nonce"])
    assert historical.status_code == 200
    assert historical.get_json()["receipt"] == old_receipt
    assert historical.get_json()["pinned_public_key"] == old_pin
    assert historical.get_json()["authorization_usable"] is False


def test_interrupt_resume_preserves_history_and_requires_fresh_epoch(phase_http):
    case = phase_http
    grant = case["grant"]()
    task_id = _prepare_task(case, grant)
    first_challenge = _prepare_challenge(case, grant, task_id).get_json()["challenge"]
    committed = _issue(case, grant, task_id, first_challenge)
    assert committed.status_code == 200
    old_receipt = committed.get_json()["receipt"]
    before_context = json.loads(_task_rows(case["db"])[0][0]["context_json"])

    interrupted = _post(case["client"], INTERRUPT_URL.format(task_id=task_id),
                        case["body"], grant["identity"])
    assert interrupted.status_code == 200, interrupted.get_json()
    assert interrupted.get_json()["task"]["status"] == "unknown"
    assert interrupted.get_json()["trainer_process_stopped"] is False
    assert interrupted.get_json()["model_execution_claimed"] is False
    interrupted_context = json.loads(_task_rows(case["db"])[0][0]["context_json"])
    assert interrupted_context["next_sequence"] == 2
    assert interrupted_context["last_receipt_sha256"] == before_context["last_receipt_sha256"]

    resumed = _post(case["client"], RESUME_URL.format(task_id=task_id),
                    case["body"], grant["identity"])
    assert resumed.status_code == 200, resumed.get_json()
    assert resumed.get_json()["model_execution_claimed"] is False
    resumed_context = json.loads(_task_rows(case["db"])[0][0]["context_json"])
    assert resumed_context["run_digest"] != before_context["run_digest"]
    assert resumed_context["next_sequence"] == 2
    assert resumed_context["admission"]["last_phase"] == before_context["admission"]["last_phase"] == "initial"

    old_replay = _issue(case, grant, task_id, first_challenge)
    assert old_replay.status_code == 200
    assert old_replay.get_json()["state"] == "PHASE_RECEIPT_ALREADY_COMMITTED"
    assert old_replay.get_json()["receipt"] == old_receipt
    assert old_replay.get_json()["authorization_usable"] is False
    assert old_replay.get_json()["model_execution_claimed"] is False
    new_challenge_response = _prepare_challenge(case, grant, task_id, "before_output_dir")
    assert new_challenge_response.status_code == 200
    new_challenge = new_challenge_response.get_json()["challenge"]
    assert new_challenge["phase"] == "before_output_dir"
    assert new_challenge["sequence"] == 2 and new_challenge["run_digest"] != first_challenge["run_digest"]


def test_history_get_remains_historical_after_challenge_expiry(phase_http, monkeypatch):
    case = phase_http
    grant = case["grant"]()
    task_id = _prepare_task(case, grant)
    challenge = _prepare_challenge(case, grant, task_id).get_json()["challenge"]
    committed = _issue(case, grant, task_id, challenge)
    assert committed.status_code == 200
    receipt = committed.get_json()["receipt"]
    class ExpiredClock:
        @staticmethod
        def time():
            return challenge["expires_at"] + 1
    monkeypatch.setattr(receipts, "time", ExpiredClock)
    historical = _read(case, grant, task_id, challenge["nonce"])
    assert historical.status_code == 200
    result = historical.get_json()
    assert result["receipt"] == receipt
    assert result["historical"] is True and result["authorization_usable"] is False
    assert result["model_execution_claimed"] is False


def test_revoke_between_fence_and_real_commit_lease_rolls_back_all_staged_rows(phase_http, monkeypatch):
    case = phase_http
    grant = case["grant"]()
    task_id = _prepare_task(case, grant)
    challenge = _prepare_challenge(case, grant, task_id).get_json()["challenge"]
    before = _db_snapshot(case["db"])
    before_tasks, before_steps = _task_rows(case["db"])
    assert len(before_tasks) == 1 and len(before_steps) == 1 and before_steps[0]["status"] == "pending"
    gate = case["gate"]
    original = type(gate).owned_training_phase_commit_lease
    calls = []
    fence = __import__("lumenis.system.security.effect_fence", fromlist=["EffectFence"])
    original_fence = fence.EffectFence.authorize_training_phase_metadata

    def observe_real_fence(self, **kwargs):
        decision = original_fence(self, **kwargs)
        calls.append(("fence", decision.allowed))
        return decision

    monkeypatch.setattr(fence.EffectFence, "authorize_training_phase_metadata", observe_real_fence)

    @contextmanager
    def revoke_before_real_lease(self, *args, **kwargs):
        calls.append(("lease-enter", None))
        assert self is gate
        assert self.revoke_approval(grant["approval_token"])
        with original(self, *args, **kwargs):
            yield

    monkeypatch.setattr(type(gate), "owned_training_phase_commit_lease", revoke_before_real_lease)
    denied = _issue(case, grant, task_id, challenge)
    assert calls == [("fence", True), ("lease-enter", None)]
    assert denied.status_code == 403
    assert _db_snapshot(case["db"]) == before
    tasks, steps = _task_rows(case["db"])
    assert tasks == before_tasks and steps == before_steps


def test_effect_fence_and_real_lease_precede_one_canonical_commit(phase_http, monkeypatch):
    case = phase_http
    grant = case["grant"]()
    task_id = _prepare_task(case, grant)
    original_connection = repository.DatabaseRepository.connection
    statements = []
    events = []

    @contextmanager
    def traced_connection(self, **kwargs):
        with original_connection(self, **kwargs) as conn:
            conn.set_trace_callback(lambda sql: statements.append(sql.strip().upper()))
            yield conn

    monkeypatch.setattr(repository.DatabaseRepository, "connection", traced_connection)
    fence = __import__("lumenis.system.security.effect_fence", fromlist=["get_effect_fence"])
    original_fence = fence.EffectFence.authorize_training_phase_metadata

    def traced_fence(self, **kwargs):
        result = original_fence(self, **kwargs)
        events.append(("fence", result.allowed))
        return result

    monkeypatch.setattr(fence.EffectFence, "authorize_training_phase_metadata", traced_fence)
    gate = case["gate"]
    original_lease = type(gate).owned_training_phase_commit_lease

    @contextmanager
    def traced_lease(self, *args, **kwargs):
        events.append(("lease-enter", None))
        with original_lease(self, *args, **kwargs):
            yield
        events.append(("lease-exit", None))

    monkeypatch.setattr(type(gate), "owned_training_phase_commit_lease", traced_lease)
    result = _prepare_challenge(case, grant, task_id)
    assert result.status_code == 200, result.get_json()
    assert events == [("fence", True), ("lease-enter", None), ("lease-exit", None)]
    commits = [sql for sql in statements if sql == "COMMIT"]
    assert len(commits) == 1
    assert any(sql.startswith("BEGIN IMMEDIATE") for sql in statements)


def test_task_owner_injected_unrelated_same_connection_write_is_rolled_back(phase_http, monkeypatch):
    """Regression probe: the metadata Fence must bound all writes in its transaction."""
    case = phase_http
    grant = case["grant"]()
    with sqlite3.connect(case["db"]) as conn:
        conn.execute("CREATE TABLE unowned_effect_probe(value TEXT NOT NULL)")
    before = _db_snapshot(case["db"])
    original = ai_task_engine.TaskEngine.create_training_receipt_task

    def inject_unrelated_write(self, *args, **kwargs):
        connection = kwargs["connection"]
        connection.execute("INSERT INTO unowned_effect_probe(value) VALUES('must-rollback')")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ai_task_engine.TaskEngine, "create_training_receipt_task", inject_unrelated_write)
    response = _post(case["client"], TASK_URL, case["body"], grant["identity"])
    after = _db_snapshot(case["db"])
    assert after == before, "unrelated SQL on the canonical metadata transaction was committed"
    assert response.status_code in {400, 403, 409}
    assert any("OWNED_TRAINING_PHASE_TRANSACTION_EFFECT_DENIED" in error
               for error in case["phase_errors"])


def test_task_owner_premature_commit_is_denied_and_rolls_back(phase_http, monkeypatch):
    """The Task owner cannot commit before Fence and the live Gate lease."""
    case = phase_http
    grant = case["grant"]()
    before = _db_snapshot(case["db"])
    original = ai_task_engine.TaskEngine.create_training_receipt_task

    def attempt_premature_commit(self, *args, **kwargs):
        kwargs["connection"].commit()
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ai_task_engine.TaskEngine, "create_training_receipt_task", attempt_premature_commit)
    response = _post(case["client"], TASK_URL, case["body"], grant["identity"])
    assert response.status_code in {400, 403, 409}
    assert _db_snapshot(case["db"]) == before
    assert any("OWNED_TRAINING_PHASE_TRANSACTION_EFFECT_DENIED" in error
               for error in case["phase_errors"])


def test_unrecognized_task_owner_savepoint_is_denied_and_rolled_back(phase_http, monkeypatch):
    """The transaction permits only the sealed savepoint names used by TaskEngine."""
    case = phase_http
    grant = case["grant"]()
    before = _db_snapshot(case["db"])
    original = ai_task_engine.TaskEngine.create_training_receipt_task

    def attempt_unrecognized_savepoint(self, *args, **kwargs):
        kwargs["connection"].execute("SAVEPOINT unrecognized_task_effect")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ai_task_engine.TaskEngine, "create_training_receipt_task", attempt_unrecognized_savepoint)
    response = _post(case["client"], TASK_URL, case["body"], grant["identity"])
    assert response.status_code in {400, 403, 409}
    assert _db_snapshot(case["db"]) == before
    assert any("OWNED_TRAINING_PHASE_TRANSACTION_EFFECT_DENIED" in error
               for error in case["phase_errors"])


def test_rejected_commit_lease_has_no_committed_effect_audit_semantics(phase_http, monkeypatch):
    case = phase_http
    grant = case["grant"]()
    task_id = _prepare_task(case, grant)
    challenge = _prepare_challenge(case, grant, task_id).get_json()["challenge"]
    gate = case["gate"]
    prior_ids = {row["audit_id"] for row in gate.get_audit_log(limit=10000)}
    original = type(gate).owned_training_phase_commit_lease

    @contextmanager
    def revoke_before_real_lease(self, *args, **kwargs):
        assert self.revoke_approval(grant["approval_token"])
        with original(self, *args, **kwargs):
            yield

    monkeypatch.setattr(type(gate), "owned_training_phase_commit_lease", revoke_before_real_lease)
    denied = _issue(case, grant, task_id, challenge)
    assert denied.status_code == 403
    new_audits = [row for row in gate.get_audit_log(limit=10000) if row["audit_id"] not in prior_ids]
    committed_claims = [row for row in new_audits
                        if row.get("operation_type") == "owned_training_phase_metadata_fence"
                        and ("COMMIT_VERIFIED" in row.get("reason", "")
                             or row.get("result") in {"committed", "executed"})]
    assert committed_claims == [], "failed lease left an audit record that implies a committed effect"
    admission_audits = [row for row in new_audits
                        if row.get("operation_type") == "owned_training_phase_metadata_fence"
                        and row.get("reason") == "OWNED_TRAINING_PHASE_METADATA_ADMITTED_NOT_COMMITTED"]
    assert len(admission_audits) == 1, "Fence audit must describe admission, not a committed effect"


def test_explicit_global_training_write_does_not_open_generic_production_truth_write(phase_http):
    case = phase_http
    task_id = _prepare_task(case, case["grant"]())
    assert task_id.startswith("trainrelay_")
    fence = __import__("lumenis.system.security.effect_fence", fromlist=["get_effect_fence"])
    from lumenis.system.security.effect_fence import AgentAction
    denied = fence.get_effect_fence().check(
        action=AgentAction.WRITE, target="production_truth:unrelated", payload={"operation": "write"},
    )
    assert denied.allowed is False
