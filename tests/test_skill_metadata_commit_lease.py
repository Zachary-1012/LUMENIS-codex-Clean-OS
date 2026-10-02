"""Concurrency and rollback tests for the exact Skill metadata commit lease."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
import json
import sqlite3
import threading
import uuid

from flask import Flask
import pytest

from lumenis.auth import service as auth_service
from lumenis.shared.agents.skills import lifecycle as lc
from lumenis.shared.database import repository as db_repository
from lumenis.shared.evidence import store
from lumenis.system.security import effect_fence as ef
from lumenis.system.security import permission as p


@pytest.fixture(autouse=True)
def strict_permission_mode(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    previous = p._TESTING_BYPASS_ENABLED
    p.set_testing_bypass(False)
    yield
    p.set_testing_bypass(previous)


@pytest.fixture
def app():
    value = Flask(__name__)
    value.config["LUMENIS_OPEN_WORKSPACE"] = True
    return value


@contextmanager
def _request(app, *, headers=None, remote_addr="127.0.0.1"):
    values = {"Host": "localhost"}
    if headers:
        values.update(headers)
    with app.test_request_context(
        "/", headers=values,
        environ_overrides={"REMOTE_ADDR": remote_addr},
    ):
        yield


@pytest.fixture
def registry(tmp_path, monkeypatch):
    from account.models import SKILLS_TABLES_SQL, _SKILL_RUNTIME_COLUMNS

    path = tmp_path / "skill-metadata-lease.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"skill-lease-test": "ephemeral-test-only-signing-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "skill-lease-test")
    monkeypatch.setattr(db_repository, "_default_repository", db_repository.DatabaseRepository())
    package = tmp_path / "owned-skill"
    package.mkdir()
    (package / "main.py").write_text("raise RuntimeError('must not execute')\n", encoding="utf-8")
    with sqlite3.connect(path) as connection:
        connection.executescript(SKILLS_TABLES_SQL)
        for name, kind in _SKILL_RUNTIME_COLUMNS:
            connection.execute(f"ALTER TABLE skills_registry ADD COLUMN {name} {kind}")
        connection.execute(
            """INSERT INTO skills_registry (
                skill_id,name,product,domain,status,version,config_json,source,source_type,runtime,
                entrypoint,permissions_granted_json,trust_level,health_state,install_state,
                lifecycle_state,install_path,active_version
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("owned.read", "Owned reader", "SYSTEM", "global", "enabled", "1.0.0",
             '{"keep":"configuration"}', str(package), "local", "python", "main:run",
             '["filesystem.read"]', "verified", "healthy", "installed", "available",
             str(package), "1.0.0"),
        )
        store.ensure_evidence_schema(connection)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(app_evidence_records)")}
        for name, kind, default in store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if name not in columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                connection.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {name} {kind}{suffix}")
        connection.executescript("""
            CREATE TABLE v4_users (
                id INTEGER PRIMARY KEY, username TEXT NOT NULL, password_hash TEXT NOT NULL,
                role TEXT NOT NULL, display_name TEXT, status TEXT NOT NULL
            );
            CREATE TABLE v4_sessions (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, token TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            INSERT INTO v4_users (id,username,password_hash,role,display_name,status)
                VALUES (1,'owner','unused','owner','Test Owner','active');
            INSERT INTO v4_sessions (user_id,token,expires_at)
                VALUES (1,'expired-readonly-session','2000-01-01 00:00:00');
        """)
    return path, package


@pytest.fixture
def gate(monkeypatch):
    value = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})
    monkeypatch.setattr(p, "_default_gate", value)
    return value


def _candidate():
    return lc.prepare_skill_metadata_change(
        "owned.read", "uninstall", operation_id=str(uuid.uuid4()),
    )


def _approved_context(candidate, gate, app):
    with _request(app):
        principal = p.resolve_local_workspace_principal(module="skills", action="write")
        resource = p.skill_metadata_approval_resource(
            candidate, principal=principal, domain_id="cth", global_scope=True,
        )
        token = gate.grant_approval(
            p.OperationType.CONFIG_MODIFY.value, resource=resource, granted_by="test-human",
        )
    assert type(principal) is p.LocalWorkspacePrincipal
    return principal, resource, token


def _check(candidate, connection, gate, app, principal, *, phase, reference=None):
    with _request(app):
        return ef.get_effect_fence().check_skill_metadata_change(
            candidate, connection=connection, gate=gate, principal=principal,
            domain_id="cth", global_scope=True, phase=phase,
            replay_evidence_ref=reference,
        )


def _apply_metadata(connection, candidate):
    after = json.loads(candidate._after_json)
    assignments = ",".join(f"{name}=?" for name in lc._METADATA_FIELDS)
    connection.execute(
        f"UPDATE skills_registry SET {assignments},last_error=NULL,last_health_at=NULL,"
        "updated_at=datetime('now','localtime') WHERE skill_id=?",
        (*[after[name] for name in lc._METADATA_FIELDS], candidate.skill_id),
    )


def _record_signed_history(connection, candidate, admitted, commit_verified):
    material = lc._candidate_material(candidate)
    inputs = {key: value for key, value in material.items()
              if key not in {"before_metadata", "after_metadata"}}
    inputs.update(
        candidate_sha256=candidate.candidate_sha256,
        identity={name: getattr(admitted, name) for name in
                  ("actor_id", "caller", "principal_kind", "principal_ref")},
        scope={name: getattr(admitted, name) for name in
               ("domain_id", "subject_id", "brand_focus_id", "global_scope")},
        resource=admitted.resource,
        permission_audit_id=admitted.permission_audit_id,
        scope_audit_id=admitted.scope_audit_id,
        fence_audit_id=admitted.fence_audit_id,
        approval_token_sha256=admitted.approval_token_sha256,
        commit_verification={name: getattr(commit_verified, name) for name in
                             ("permission_audit_id", "scope_audit_id", "fence_audit_id", "approval_token_sha256")},
    )
    record_id = store.record_evidence(
        connection=connection, source=lc.HISTORY_SOURCE, product="SYSTEM", subject_scope="SYSTEM",
        feature_id=lc.HISTORY_FEATURE, asset_id=candidate.skill_id,
        test_name=candidate.operation_id,
        version=lc.SCHEMA_VERSION + ":" + candidate.candidate_sha256,
        capture_mode="manual_metadata_admission", result="PASS", status="derived", inputs=inputs,
        outputs={"before_metadata": material["before_metadata"],
                 "after_metadata": material["after_metadata"],
                 "config_sha256": candidate.config_sha256},
    )
    return f"app_evidence_records:{record_id}"


def _prepare_pending_commit(candidate, gate, app, principal):
    """Return a real canonical writer transaction and its final Fence receipt."""
    connection = db_repository.get_repository().connect(wal=False)
    try:
        connection.execute("BEGIN IMMEDIATE")
        admitted = _check(candidate, connection, gate, app, principal, phase="before_write")
        assert admitted.allowed is True and admitted.state == "admitted"
        _apply_metadata(connection, candidate)
        first_commit_check = _check(candidate, connection, gate, app, principal, phase="before_commit")
        assert first_commit_check.allowed is True and first_commit_check.state == "commit_verified"
        reference = _record_signed_history(connection, candidate, admitted, first_commit_check)
        lc._history_row(connection, reference, candidate.skill_id)
        final_check = _check(candidate, connection, gate, app, principal, phase="before_commit")
        assert final_check.allowed is True and final_check.state == "commit_verified"
        return connection, final_check, reference
    except BaseException:
        connection.rollback()
        connection.close()
        raise


def _lease(gate, candidate, connection, decision, app, principal, *, timeout_seconds=2.0):
    return gate.skill_metadata_commit_lease(
        candidate, connection=connection, decision=decision, principal=principal,
        domain_id="cth", global_scope=True, timeout_seconds=timeout_seconds,
    )


def _assert_rolled_back(path, candidate):
    with db_repository.get_repository().connection(read_only=True, wal=False) as connection:
        row = lc._registry_row(connection, candidate.skill_id)
        assert lc._snapshot(row) == json.loads(candidate._before_json)
        assert row["config_json"] == '{"keep":"configuration"}'
        assert connection.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE source=? AND feature_id=? AND test_name=?",
            (lc.HISTORY_SOURCE, lc.HISTORY_FEATURE, candidate.operation_id),
        ).fetchone()[0] == 0


def test_revoke_before_lease_denies_and_rolls_back_metadata_and_signed_history(registry, gate, app):
    path, _package = registry
    candidate = _candidate()
    principal, _resource, token = _approved_context(candidate, gate, app)
    connection, final_check, _reference = _prepare_pending_commit(candidate, gate, app, principal)
    try:
        assert gate.revoke_approval(token) is True
        with pytest.raises(PermissionError, match="SKILL_METADATA_COMMIT_LEASE_APPROVAL_REQUIRED"):
            with _request(app):
                with _lease(gate, candidate, connection, final_check, app, principal):
                    connection.commit()
    finally:
        connection.rollback()
        connection.close()
    _assert_rolled_back(path, candidate)


def test_revoke_waits_for_sqlite_commit_and_stale_receipt_cannot_write_after_return(registry, gate, app):
    path, _package = registry
    candidate = _candidate()
    principal, _resource, token = _approved_context(candidate, gate, app)
    lease_entered = threading.Event()
    allow_commit = threading.Event()
    revoke_started = threading.Event()
    revoke_returned = threading.Event()
    worker_done = threading.Event()
    order = []
    order_lock = threading.Lock()
    outcome = {}

    def add_order(label):
        with order_lock:
            order.append(label)

    def commit_worker():
        connection = None
        try:
            connection, decision, reference = _prepare_pending_commit(candidate, gate, app, principal)
            outcome.update(decision=decision, reference=reference)
            with _request(app):
                with _lease(gate, candidate, connection, decision, app, principal):
                    lease_entered.set()
                    if not allow_commit.wait(2):
                        raise TimeoutError("test commit release was not signaled")
                    connection.commit()
                    add_order("sqlite_commit_returned")
        except BaseException as exc:
            outcome["worker_error"] = exc
            lease_entered.set()
        finally:
            if connection is not None:
                connection.close()
            worker_done.set()

    def revoke_worker():
        revoke_started.set()
        outcome["revoke_result"] = gate.revoke_approval(token)
        add_order("revoke_returned")
        revoke_returned.set()

    writer = threading.Thread(target=commit_worker, name="skill-metadata-commit", daemon=True)
    writer.start()
    try:
        assert lease_entered.wait(2), "writer did not enter the real commit lease"
        assert "worker_error" not in outcome, repr(outcome.get("worker_error"))
        revoker = threading.Thread(target=revoke_worker, name="skill-metadata-revoke", daemon=True)
        revoker.start()
        assert revoke_started.wait(2)
        assert not revoke_returned.wait(0.15), "revocation returned while the lease still held the SQLite commit"
        allow_commit.set()
        assert worker_done.wait(2)
        assert revoke_returned.wait(2)
        writer.join(timeout=2)
        revoker.join(timeout=2)
        assert not writer.is_alive() and not revoker.is_alive()
        assert "worker_error" not in outcome, repr(outcome.get("worker_error"))
        assert outcome.get("revoke_result") is True
        assert order == ["sqlite_commit_returned", "revoke_returned"]

        # The old final Fence receipt cannot authorize a later write after revoke returns.
        stale = db_repository.get_repository().connect(wal=False)
        stale.execute("BEGIN IMMEDIATE")
        try:
            stale.execute("UPDATE skills_registry SET last_error=? WHERE skill_id=?",
                          ("must roll back after revocation", candidate.skill_id))
            with pytest.raises(PermissionError, match="SKILL_METADATA_COMMIT_LEASE_APPROVAL_REQUIRED"):
                with _request(app):
                    with _lease(gate, candidate, stale, outcome["decision"], app, principal):
                        stale.commit()
        finally:
            stale.rollback()
            stale.close()
        with db_repository.get_repository().connection(read_only=True, wal=False) as connection:
            row = lc._registry_row(connection, candidate.skill_id)
            assert lc._snapshot(row) == json.loads(candidate._after_json)
            assert row["last_error"] is None
            assert connection.execute(
                "SELECT COUNT(*) FROM app_evidence_records WHERE source=? AND feature_id=? AND test_name=?",
                (lc.HISTORY_SOURCE, lc.HISTORY_FEATURE, candidate.operation_id),
            ).fetchone()[0] == 1
    finally:
        allow_commit.set()
        writer.join(timeout=2)


def test_sqlite_commit_exception_releases_lease_and_rolls_back_full_transaction(registry, gate, app):
    path, _package = registry
    candidate = _candidate()
    principal, _resource, token = _approved_context(candidate, gate, app)
    lease_entered = threading.Event()
    fail_commit = threading.Event()
    revoke_started = threading.Event()
    revoke_returned = threading.Event()
    outcome = {}

    def failing_writer():
        connection = None
        try:
            connection, decision, _reference = _prepare_pending_commit(candidate, gate, app, principal)
            with _request(app):
                with _lease(gate, candidate, connection, decision, app, principal):
                    lease_entered.set()
                    if not fail_commit.wait(2):
                        raise TimeoutError("test commit failure was not signaled")
                    connection.close()
                    connection.commit()
        except BaseException as exc:
            outcome["error"] = exc
        finally:
            if connection is not None:
                connection.close()
            outcome["finished"] = True

    def revoker():
        revoke_started.set()
        outcome["revoked"] = gate.revoke_approval(token)
        revoke_returned.set()

    writer = threading.Thread(target=failing_writer, name="skill-metadata-failing-commit", daemon=True)
    writer.start()
    try:
        assert lease_entered.wait(2), "writer did not enter the real commit lease"
        assert "error" not in outcome
        revoke_thread = threading.Thread(target=revoker, name="skill-metadata-revoke-after-failure", daemon=True)
        revoke_thread.start()
        assert revoke_started.wait(2)
        assert not revoke_returned.wait(0.15), "revocation returned before the lease released"
        fail_commit.set()
        writer.join(timeout=2)
        revoke_thread.join(timeout=2)
        assert not writer.is_alive() and not revoke_thread.is_alive()
        assert isinstance(outcome.get("error"), sqlite3.ProgrammingError)
        assert outcome.get("revoked") is True and revoke_returned.is_set()
    finally:
        fail_commit.set()
        writer.join(timeout=2)
    _assert_rolled_back(path, candidate)


def test_lease_timeout_expired_token_and_changed_receipt_digest_all_rollback(registry, gate, app):
    path, _package = registry
    candidate = _candidate()
    principal, _resource, token = _approved_context(candidate, gate, app)
    connection, decision, _reference = _prepare_pending_commit(candidate, gate, app, principal)
    lock_held = threading.Event()
    release_lock = threading.Event()

    def hold_approval_lock():
        with gate._approval_lock:
            lock_held.set()
            release_lock.wait(2)

    blocker = threading.Thread(target=hold_approval_lock, name="skill-metadata-lock-blocker", daemon=True)
    blocker.start()
    try:
        assert lock_held.wait(2)
        with pytest.raises(PermissionError, match="SKILL_METADATA_COMMIT_LEASE_TIMEOUT"):
            with _request(app):
                with _lease(gate, candidate, connection, decision, app, principal, timeout_seconds=0.05):
                    connection.commit()
    finally:
        release_lock.set()
        blocker.join(timeout=2)
        connection.rollback()
        connection.close()
    assert not blocker.is_alive()
    _assert_rolled_back(path, candidate)

    for kind in ("expired", "changed_digest"):
        candidate = _candidate()
        principal, _resource, token = _approved_context(candidate, gate, app)
        connection, decision, _reference = _prepare_pending_commit(candidate, gate, app, principal)
        if kind == "expired":
            gate._approvals[token].expires_at = datetime.now() - timedelta(seconds=1)
            lease_decision = decision
        else:
            lease_decision = replace(decision, approval_token_sha256="f" * 64)
        try:
            with pytest.raises(PermissionError, match="SKILL_METADATA_COMMIT_LEASE_APPROVAL_REQUIRED"):
                with _request(app):
                    with _lease(gate, candidate, connection, lease_decision, app, principal):
                        connection.commit()
        finally:
            connection.rollback()
            connection.close()
        _assert_rolled_back(path, candidate)


def test_read_only_expired_session_lookup_does_not_initialize_or_delete_inside_writer_transaction(
    registry, app, monkeypatch,
):
    path, _package = registry
    calls = []
    monkeypatch.setattr(auth_service, "ensure_initialized", lambda: calls.append("initialized"))
    connection = db_repository.get_repository().connect(wal=False)
    connection.execute("BEGIN IMMEDIATE")
    try:
        with _request(app, headers={"Authorization": "Bearer expired-readonly-session"}):
            assert auth_service.get_current_user(read_only=True) is None
        assert calls == []
        assert connection.execute(
            "SELECT COUNT(*) FROM v4_sessions WHERE token=?", ("expired-readonly-session",),
        ).fetchone()[0] == 1
    finally:
        connection.rollback()
        connection.close()

    # The default auth path retains lazy initialization and expired-session cleanup.
    with _request(app, headers={"Authorization": "Bearer expired-readonly-session"}):
        assert auth_service.get_current_user() is None
    assert calls == ["initialized"]
    with db_repository.get_repository().connection(read_only=True, wal=False) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM v4_sessions WHERE token=?", ("expired-readonly-session",),
        ).fetchone()[0] == 0
