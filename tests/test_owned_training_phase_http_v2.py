"""HTTP boundary tests for sealed owned-training phase metadata (no trainer)."""
from __future__ import annotations

import ast
from contextlib import contextmanager
from datetime import datetime, timedelta
import hashlib
import json
import multiprocessing
import os
import re
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


@pytest.fixture
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


pytestmark = pytest.mark.usefixtures("strict_permission_mode")


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
        "request": request, "jsonify": jsonify, "re": re,
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
def phase_http(tmp_path, monkeypatch, strict_permission_mode):
    seed_value = os.environ.get("LUMENIS_TEST_SEED_DB") or os.environ.get("ZBC_DB_PATH")
    assert seed_value, "phase HTTP tests require the already-isolated pytest seed"
    seed = Path(seed_value).resolve()
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


def _seed_legacy_history(case, grant):
    """Seed a historical receipt in the existing isolated Task database only."""
    from lumenis.system.security import training_receipts as receipt_owner

    with case["app"].test_request_context(
            "/", headers=_headers_for(grant["identity"]),
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        typed, context, args, domain, binding, fingerprints, gate, fresh = runtime._owned_training_phase_material(
            case["body"])
        public_key = receipt_owner.get_training_receipt_public_key()
        engine = ai_task_engine.get_task_engine()
        with runtime._owned_training_phase_transaction() as (connection, commit):
            _, reference = runtime._owned_training_phase_reference(
                typed, context, args, domain, gate, fresh)
            state = engine.create_training_receipt_task(
                binding=binding, fingerprints=fingerprints, connection=connection,
                approval_reference=reference, pinned_public_key=public_key)
            runtime._commit_owned_training_phase(
                connection, typed, context, args, domain, gate, fresh, reference,
                task_id=state["task_id"], mutation="create", state=state, commit=commit)

        task_id = state["task_id"]
        with runtime._owned_training_phase_transaction() as (connection, commit):
            _, reference = runtime._owned_training_phase_reference(
                typed, context, args, domain, gate, fresh)
            challenge = engine.prepare_training_phase_challenge(
                task_id, binding, reference, public_key, "initial", connection)
            state = engine.get_training_receipt_task(
                task_id, expected_binding=binding, connection=connection)
            runtime._commit_owned_training_phase(
                connection, typed, context, args, domain, gate, fresh, reference,
                task_id=task_id, mutation="challenge", state=state, commit=commit)

        signed = receipt_owner.sign_training_phase_decision(challenge, "allow")
        receipt_owner.verify_training_phase_decision(
            signed, expected_challenge=challenge, pinned_public_key=public_key)
        encoded = json.dumps(signed, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
        with runtime._owned_training_phase_transaction() as (connection, commit):
            _, reference = runtime._owned_training_phase_reference(
                typed, context, args, domain, gate, fresh)
            state = engine.consume_training_phase_challenge(
                task_id, expected_binding=binding, challenge=challenge,
                receipt_sha256=hashlib.sha256(encoded).hexdigest(), decision="allow",
                connection=connection, receipt=signed, expected_approval_reference=reference)
            runtime._commit_owned_training_phase(
                connection, typed, context, args, domain, gate, fresh, reference,
                task_id=task_id, mutation="receipt", state=state, commit=commit)
    return task_id, binding, challenge, signed


def test_withdrawn_task_and_phase_routes_are_410_without_database_or_worker_effects(
        phase_http, monkeypatch):
    case = phase_http
    before = _db_snapshot(case["db"])
    attempted = []

    def fail(name):
        def forbidden(*_args, **_kwargs):
            attempted.append(name)
            raise AssertionError(f"withdrawn route attempted {name}")
        return forbidden

    task_id = "trainrelay_00000000-0000-4000-8000-000000000001"
    with monkeypatch.context() as effects:
        effects.setattr(ai_task_engine, "get_task_engine", fail("task-engine"))
        effects.setattr(repository, "get_repository", fail("database"))
        effects.setattr(sqlite3, "connect", fail("sqlite"))
        effects.setattr(runtime, "_owned_training_phase_body", fail("phase-body"))
        effects.setattr(runtime, "_owned_training_phase_material", fail("permission-material"))
        for path, body in (
            (TASK_URL, {}),
            (CHALLENGE_URL.format(task_id=task_id), {}),
            (DECISION_URL.format(task_id=task_id), {}),
            (RESUME_URL.format(task_id=task_id), {}),
        ):
            response = _post(case["client"], path, body)
            assert response.status_code == 410, (path, response.get_json())
            assert response.get_json()["code"] == "GPU_TRAINING_WITHDRAWN_BY_PO"
    assert attempted == []
    assert _db_snapshot(case["db"]) == before


def test_historical_receipt_remains_read_only_and_non_authorizing(phase_http):
    case = phase_http
    grant = case["grant"]()
    task_id, _binding, challenge, signed = _seed_legacy_history(case, grant)
    before = _db_snapshot(case["db"])

    response = _read(case, grant, task_id, challenge["nonce"])
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    assert result["receipt"] == signed and result["challenge"] == challenge
    assert result["historical"] is True
    assert result["authorization_usable"] is False
    assert result["model_execution_claimed"] is False
    assert _db_snapshot(case["db"]) == before


def test_interrupt_stops_inflight_owner_and_preserves_historical_receipt(phase_http):
    case = phase_http
    grant = case["grant"]()
    task_id, binding, challenge, signed = _seed_legacy_history(case, grant)
    calls = []

    class RetainedWorker:
        def stop_and_reap(self):
            calls.append("stop-and-reap")
            return {"state": "STOPPED_AND_REAPED", "task_id": task_id}

    assert task_id not in runtime._OWNED_TRAINING_PARENT_FENCES
    runtime._OWNED_TRAINING_PARENT_FENCES[task_id] = {
        "binding": binding, "worker": RetainedWorker(),
    }
    try:
        response = _post(case["client"], INTERRUPT_URL.format(task_id=task_id),
                         case["body"], grant["identity"])
        assert response.status_code == 200, response.get_json()
        result = response.get_json()
        assert result["state"] == "PHASE_TASK_INTERRUPTED"
        assert result["task"]["status"] == "unknown"
        assert result["trainer_process_stopped"] is True
        assert result["trainer_stop_receipt"]["state"] == "STOPPED_AND_REAPED"
        assert result["model_execution_claimed"] is False
        assert calls == ["stop-and-reap"]
    finally:
        runtime._OWNED_TRAINING_PARENT_FENCES.pop(task_id, None)

    before_resume = _db_snapshot(case["db"])
    resumed = _post(case["client"], RESUME_URL.format(task_id=task_id),
                    case["body"], grant["identity"])
    assert resumed.status_code == 410
    assert resumed.get_json()["code"] == "GPU_TRAINING_WITHDRAWN_BY_PO"
    assert _db_snapshot(case["db"]) == before_resume

    history = _read(case, grant, task_id, challenge["nonce"])
    assert history.status_code == 200
    assert history.get_json()["receipt"] == signed
    assert history.get_json()["historical"] is True
    assert history.get_json()["authorization_usable"] is False
    assert history.get_json()["task"]["status"] == "unknown"
