"""Isolated Effect Fence contract for manual Skill metadata admission."""
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
import re
import sqlite3
import uuid

from flask import Flask
import pytest

from lumenis.shared.agents.skills import lifecycle as lc
from lumenis.shared.evidence import store
from lumenis.shared.database import repository as db_repository
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
    request_headers = {"Host": "localhost"}
    if headers:
        request_headers.update(headers)
    with app.test_request_context(
        "/", headers=request_headers,
        environ_overrides={"REMOTE_ADDR": remote_addr},
    ):
        yield


@pytest.fixture
def registry(tmp_path, monkeypatch):
    from account.models import SKILLS_TABLES_SQL, _SKILL_RUNTIME_COLUMNS

    path = tmp_path / "skill-metadata-fence.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"skill-fence-test": "ephemeral-test-only-signing-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "skill-fence-test")
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
                VALUES (1,'valid-owner-session','2999-01-01 00:00:00');
        """)
    from lumenis.shared.agents.skills.execution import ensure_skill_executions_table

    ensure_skill_executions_table()
    return path


@pytest.fixture
def gate(monkeypatch):
    value = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})
    monkeypatch.setattr(p, "_default_gate", value)
    return value


def _candidate():
    return lc.prepare_skill_metadata_change(
        "owned.read", "uninstall", operation_id=str(uuid.uuid4()),
    )


def _grant(candidate, gate, app):
    with _request(app):
        principal = p.resolve_local_workspace_principal(module="skills", action="write")
        resource = p.skill_metadata_approval_resource(
            candidate, principal=principal, domain_id="cth", global_scope=True,
        )
        token = gate.grant_approval(
            p.OperationType.CONFIG_MODIFY.value, resource=resource, granted_by="test-human",
        )
    return principal, resource, token


def _connection(path):
    connection = db_repository.get_repository().connect(wal=False)
    connection.execute("BEGIN IMMEDIATE")
    assert connection.in_transaction
    assert connection.execute("PRAGMA database_list").fetchone()[2] == str(path)
    return connection


def _check(candidate, connection, gate, app, principal, **kwargs):
    with _request(app):
        return ef.get_effect_fence().check_skill_metadata_change(
            candidate, connection=connection, gate=gate, principal=principal,
            domain_id="cth", global_scope=True, **kwargs,
        )


def _apply_metadata(connection, candidate):
    after = json.loads(candidate._after_json)
    assignments = ",".join(f"{name}=?" for name in lc._METADATA_FIELDS)
    connection.execute(
        f"UPDATE skills_registry SET {assignments},last_error=NULL,last_health_at=NULL,"
        "updated_at=datetime('now','localtime') WHERE skill_id=?",
        (*[after[name] for name in lc._METADATA_FIELDS], candidate.skill_id),
    )


def test_before_write_and_commit_verify_only_the_exact_disabled_metadata(registry, gate, app):
    candidate = _candidate()
    principal, resource, _token = _grant(candidate, gate, app)
    connection = _connection(registry)
    try:
        decision = _check(candidate, connection, gate, app, principal)
        assert type(decision) is ef.SkillMetadataFenceDecision
        assert decision.allowed is True and decision.state == "admitted"
        assert decision.resource == resource
        assert decision.operation_id == candidate.operation_id
        assert decision.candidate_sha256 == candidate.candidate_sha256
        assert decision.caller == "workspace:local"
        assert decision.principal_kind == "local_workspace"
        assert decision.principal_ref == "workspace:local"
        assert all(re.fullmatch(r"aud_[0-9a-f]{16}", value) for value in (
            decision.permission_audit_id, decision.scope_audit_id, decision.fence_audit_id,
        ))
        assert re.fullmatch(r"[0-9a-f]{64}", decision.approval_token_sha256)

        _apply_metadata(connection, candidate)
        commit = _check(candidate, connection, gate, app, principal, phase="before_commit")
        assert commit.allowed is True and commit.state == "commit_verified"
        assert commit.candidate_sha256 == candidate.candidate_sha256
        row = lc._registry_row(connection, candidate.skill_id)
        assert lc._snapshot(row) == json.loads(candidate._after_json)
        assert json.loads(row["permissions_granted_json"]) == []
        assert row["install_state"] == "not_installed"
        assert row["install_path"] is None and row["active_version"] is None
        assert row["config_json"] == '{"keep":"configuration"}'
    finally:
        connection.rollback()
        connection.close()


def test_revoked_approval_between_write_and_commit_fails_closed(registry, gate, app):
    candidate = _candidate()
    principal, _resource, token = _grant(candidate, gate, app)
    connection = _connection(registry)
    try:
        assert _check(candidate, connection, gate, app, principal).allowed is True
        _apply_metadata(connection, candidate)
        assert gate.revoke_approval(token) is True
        decision = _check(candidate, connection, gate, app, principal, phase="before_commit")
        assert decision.allowed is False
        assert decision.state == "denied"
        assert decision.code == "SKILL_METADATA_MANUAL_APPROVAL_REQUIRED"
        assert lc._snapshot(lc._registry_row(connection, candidate.skill_id)) == json.loads(candidate._after_json)
        # The caller still owns the transaction and can roll it back.
    finally:
        connection.rollback()
        connection.close()
    with db_repository.get_repository().connection(read_only=True, wal=False) as reopened:
        assert lc._snapshot(lc._registry_row(reopened, candidate.skill_id)) == json.loads(candidate._before_json)


def _record_real_history(connection, candidate, first, commit):
    material = lc._candidate_material(candidate)
    inputs = {key: value for key, value in material.items()
              if key not in {"before_metadata", "after_metadata"}}
    inputs.update(
        candidate_sha256=candidate.candidate_sha256,
        identity={name: getattr(first, name) for name in ("actor_id", "caller", "principal_kind", "principal_ref")},
        scope={name: getattr(first, name) for name in ("domain_id", "subject_id", "brand_focus_id", "global_scope")},
        resource=first.resource,
        permission_audit_id=first.permission_audit_id,
        scope_audit_id=first.scope_audit_id,
        fence_audit_id=first.fence_audit_id,
        approval_token_sha256=first.approval_token_sha256,
        commit_verification={name: getattr(commit, name) for name in (
            "permission_audit_id", "scope_audit_id", "fence_audit_id", "approval_token_sha256",
        )},
    )
    record_id = store.record_evidence(
        connection=connection, source=lc.HISTORY_SOURCE, product="SYSTEM", subject_scope="SYSTEM",
        feature_id=lc.HISTORY_FEATURE, asset_id=candidate.skill_id,
        test_name=candidate.operation_id, version=lc.SCHEMA_VERSION + ":" + candidate.candidate_sha256,
        capture_mode="manual_metadata_admission", result="PASS", status="derived", inputs=inputs,
        outputs={"before_metadata": json.loads(candidate._before_json),
                 "after_metadata": json.loads(candidate._after_json),
                 "config_sha256": candidate.config_sha256},
    )
    return f"app_evidence_records:{record_id}"


def test_signed_history_replay_is_readback_only_and_allows_a_fresh_exact_approval(registry, gate, app):
    candidate = _candidate()
    principal, resource, old_token = _grant(candidate, gate, app)
    connection = _connection(registry)
    try:
        first = _check(candidate, connection, gate, app, principal)
        _apply_metadata(connection, candidate)
        commit = _check(candidate, connection, gate, app, principal, phase="before_commit")
        reference = _record_real_history(connection, candidate, first, commit)
        lc._history_row(connection, reference, candidate.skill_id)
        connection.commit()
    finally:
        connection.close()

    assert gate.revoke_approval(old_token) is True
    new_token = gate.grant_approval(
        p.OperationType.CONFIG_MODIFY.value, resource=resource, granted_by="test-human-after-restart",
    )
    replay = _connection(registry)
    try:
        changes_before = replay.total_changes
        decision = _check(candidate, replay, gate, app, principal,
                          phase="replay", replay_evidence_ref=reference)
        assert decision.allowed is True and decision.state == "already_applied"
        assert decision.idempotent_hit is True
        assert decision.approval_token_sha256 == hashlib.sha256(new_token.encode()).hexdigest()
        assert replay.total_changes == changes_before
        assert lc._snapshot(lc._registry_row(replay, candidate.skill_id)) == json.loads(candidate._after_json)
    finally:
        replay.rollback()
        replay.close()


def test_foreign_connection_stale_registry_and_forged_candidate_are_denied(registry, gate, app, tmp_path):
    candidate = _candidate()
    principal, _resource, _token = _grant(candidate, gate, app)
    foreign_path = tmp_path / "foreign.sqlite3"
    with sqlite3.connect(foreign_path) as foreign:
        foreign.execute("CREATE TABLE marker(value TEXT)")
    foreign = sqlite3.connect(foreign_path)
    foreign.execute("BEGIN IMMEDIATE")
    try:
        decision = _check(candidate, foreign, gate, app, principal)
        assert decision.allowed is False and decision.state == "denied"
    finally:
        foreign.rollback()
        foreign.close()

    stale = _connection(registry)
    try:
        stale.execute("UPDATE skills_registry SET name='changed elsewhere' WHERE skill_id=?", (candidate.skill_id,))
        decision = _check(candidate, stale, gate, app, principal)
        assert decision.allowed is False
    finally:
        stale.rollback()
        stale.close()

    forged = replace(candidate, _after_json=candidate._after_json.replace('"disabled"', '"enabled"'))
    check = _connection(registry)
    try:
        denied = _check(forged, check, gate, app, principal)
        assert denied.allowed is False and denied.state == "denied"
    finally:
        check.rollback()
        check.close()


@pytest.mark.parametrize("field,value", [
    ("config_json", '{"changed":"configuration"}'),
    ("last_error", "row changed outside the metadata candidate"),
])
def test_config_and_nonmetadata_full_row_changes_are_denied(registry, gate, app, field, value):
    candidate = _candidate()
    principal, _resource, _token = _grant(candidate, gate, app)
    connection = _connection(registry)
    try:
        connection.execute(f"UPDATE skills_registry SET {field}=? WHERE skill_id=?", (value, candidate.skill_id))
        decision = _check(candidate, connection, gate, app, principal)
        assert decision.allowed is False
        assert decision.state == "denied"
    finally:
        connection.rollback()
        connection.close()


def test_signed_history_replay_rejects_identity_and_scope_collisions(registry, gate, app, monkeypatch):
    from lumenis.auth import service

    monkeypatch.setattr(service, "ensure_initialized", lambda: None)
    candidate = _candidate()
    principal, _resource, _old_token = _grant(candidate, gate, app)
    connection = _connection(registry)
    try:
        first = _check(candidate, connection, gate, app, principal)
        _apply_metadata(connection, candidate)
        commit = _check(candidate, connection, gate, app, principal, phase="before_commit")
        reference = _record_real_history(connection, candidate, first, commit)
        connection.commit()
    finally:
        connection.close()

    # The same candidate and resulting metadata do not let a different domain reuse the signed admission.
    with _request(app):
        bmp_resource = p.skill_metadata_approval_resource(
            candidate, principal=principal, domain_id="bmp", global_scope=True,
        )
        gate.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource=bmp_resource)
        scoped = db_repository.get_repository().connect(wal=False)
        scoped.execute("BEGIN IMMEDIATE")
        try:
            mismatch = ef.get_effect_fence().check_skill_metadata_change(
                candidate, connection=scoped, gate=gate, principal=principal,
                domain_id="bmp", global_scope=True, phase="replay",
                replay_evidence_ref=reference,
            )
            assert mismatch.allowed is False
            assert mismatch.code == "SKILL_METADATA_REPLAY_CONTEXT_MISMATCH"
        finally:
            scoped.rollback()
            scoped.close()

    # A valid account session with a fresh exact resource still cannot replay the workspace-signed identity.
    with _request(app, headers={"Authorization": "Bearer valid-owner-session"}):
        account_resource = p.skill_metadata_approval_resource(
            candidate, actor_id=1, domain_id="cth", global_scope=True,
        )
        gate.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource=account_resource)
        account = db_repository.get_repository().connect(wal=False)
        account.execute("BEGIN IMMEDIATE")
        try:
            mismatch = ef.get_effect_fence().check_skill_metadata_change(
                candidate, connection=account, gate=gate, actor_id=1,
                domain_id="cth", global_scope=True, phase="replay",
                replay_evidence_ref=reference,
            )
            assert mismatch.allowed is False
            assert mismatch.code == "SKILL_METADATA_REPLAY_CONTEXT_MISMATCH"
        finally:
            account.rollback()
            account.close()


def test_signed_history_tampering_blocks_replay(registry, gate, app):
    candidate = _candidate()
    principal, _resource, _old_token = _grant(candidate, gate, app)
    connection = _connection(registry)
    try:
        first = _check(candidate, connection, gate, app, principal)
        _apply_metadata(connection, candidate)
        commit = _check(candidate, connection, gate, app, principal, phase="before_commit")
        reference = _record_real_history(connection, candidate, first, commit)
        connection.commit()
    finally:
        connection.close()

    with db_repository.get_repository().transaction() as tamper:
        tamper.execute(
            "UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?",
            (int(reference.split(":")[1]),),
        )
    replay = _connection(registry)
    try:
        decision = _check(candidate, replay, gate, app, principal,
                          phase="replay", replay_evidence_ref=reference)
        assert decision.allowed is False
        assert decision.code == "SKILL_HISTORY_SIGNATURE_INVALID"
    finally:
        replay.rollback()
        replay.close()


def test_generic_effect_fence_production_truth_denial_is_unchanged():
    from lumenis.system.security.action_firewall import AgentAction

    decision = ef.get_effect_fence().check(
        action=AgentAction.COMMIT, target="production_db",
        payload={"staging": True}, operation_id="generic-denial-regression",
    )
    assert decision.allowed is False
    assert decision.reservation_status == "rejected"
