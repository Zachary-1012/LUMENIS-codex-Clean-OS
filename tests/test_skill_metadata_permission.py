"""Permission identity, scope and exact human approval tests for Skill metadata."""
from contextlib import contextmanager
from datetime import datetime, timedelta
import json
import sqlite3
import uuid

from flask import Flask
import pytest

from lumenis.shared.agents.skills import lifecycle as lc
from lumenis.shared.evidence import store
from lumenis.shared.database import repository as db_repository
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

    path = tmp_path / "skill-metadata-permission.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"skill-permission-test": "ephemeral-test-only-signing-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "skill-permission-test")
    monkeypatch.setattr(db_repository, "_default_repository", db_repository.DatabaseRepository())
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
             '{"keep":"configuration"}', "/tmp/test-owned-skill", "local", "python",
             "main:run", '["filesystem.read"]', "verified", "healthy", "installed",
             "available", "/tmp/test-owned-skill", "1.0.0"),
        )
        store.ensure_evidence_schema(connection)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(app_evidence_records)")}
        for name, kind, default in store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if name not in columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                connection.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {name} {kind}{suffix}")
        connection.execute("""CREATE TABLE v4_users (
            id INTEGER PRIMARY KEY, username TEXT NOT NULL, password_hash TEXT NOT NULL,
            role TEXT NOT NULL, display_name TEXT, status TEXT NOT NULL
        )""")
        connection.execute("""CREATE TABLE v4_sessions (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, token TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )""")
        connection.execute("""CREATE TABLE v4_member_authorizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            product_id TEXT NOT NULL, module TEXT NOT NULL, action TEXT NOT NULL,
            data_scope TEXT, time_range TEXT, granted_by INTEGER, created_at TEXT,
            updated_at TEXT, UNIQUE(user_id, product_id, module, action)
        )""")
        connection.execute("""INSERT INTO v4_users
            (id,username,password_hash,role,display_name,status) VALUES
            (1,'owner','unused','owner','Test Owner','active'),
            (2,'member','unused','user','Test Member','active')""")
        connection.execute(
            "INSERT INTO v4_sessions (user_id,token,expires_at) VALUES (1,?,?)",
            ("valid-owner-session", "2999-01-01 00:00:00"),
        )
        connection.execute(
            "INSERT INTO v4_sessions (user_id,token,expires_at) VALUES (2,?,?)",
            ("valid-member-session", "2999-01-01 00:00:00"),
        )
        connection.execute(
            """INSERT INTO v4_member_authorizations
                (user_id,product_id,module,action,data_scope,time_range)
                VALUES (2,'CTH','skills','write','{"global":true}',NULL)"""
        )
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


def _workspace_principal(app):
    with _request(app):
        principal = p.resolve_local_workspace_principal(module="skills", action="write")
    assert type(principal) is p.LocalWorkspacePrincipal
    return principal


def _workspace_resource(candidate, principal, app, *, domain="cth", global_scope=True):
    with _request(app):
        return p.skill_metadata_approval_resource(
            candidate, principal=principal, domain_id=domain, global_scope=global_scope,
        )


def _workspace_check(candidate, gate, principal, app, *, domain="cth", global_scope=True):
    with _request(app):
        return p.check_skill_metadata_change_permission(
            candidate, gate=gate, principal=principal, domain_id=domain,
            global_scope=global_scope,
        )


def test_open_workspace_permission_requires_exact_scope_and_manual_approval(registry, gate, app):
    candidate = _candidate()
    principal = _workspace_principal(app)
    resource = _workspace_resource(candidate, principal, app)
    token = gate.grant_approval(
        p.OperationType.CONFIG_MODIFY.value, resource=resource, granted_by="test-human",
    )
    decision = _workspace_check(candidate, gate, principal, app)
    assert type(decision) is p.SkillMetadataPermissionDecision
    assert decision.allowed is True
    assert decision.resource == resource
    assert decision.operation_id == candidate.operation_id
    assert decision.candidate_sha256 == candidate.candidate_sha256
    assert decision.actor_id is None and decision.caller == "workspace:local"
    assert decision.principal_kind == "local_workspace"
    assert decision.principal_ref == "workspace:local"
    assert decision.global_scope is True and decision.domain_id == "cth"
    assert decision.permission_audit_id.startswith("aud_")
    assert decision.scope_audit_id.startswith("aud_")
    assert len(decision.approval_token_sha256) == 64
    assert gate.get_valid_approval_token(
        p.OperationType.CONFIG_MODIFY.value, resource, exact=True,
    ) == token


def test_bmp_scope_alias_uses_canonical_receipt_and_exact_approval(registry, gate, app):
    candidate = _candidate()
    principal = _workspace_principal(app)
    resource = _workspace_resource(candidate, principal, app, domain="bmp")
    gate.grant_approval(
        p.OperationType.CONFIG_MODIFY.value, resource=resource, granted_by="test-human",
    )

    decision = _workspace_check(candidate, gate, principal, app, domain="bmp")

    assert decision.allowed is True
    assert decision.code == "SKILL_METADATA_APPROVED"
    assert decision.resource == resource
    assert decision.domain_id == "bmp"


def test_cth_skill_metadata_approval_cannot_authorize_bmp_scope(registry, gate, app):
    candidate = _candidate()
    principal = _workspace_principal(app)
    cth_resource = _workspace_resource(candidate, principal, app, domain="cth")
    bmp_resource = _workspace_resource(candidate, principal, app, domain="bmp")
    assert cth_resource != bmp_resource
    gate.grant_approval(
        p.OperationType.CONFIG_MODIFY.value, resource=cth_resource, granted_by="test-human",
    )

    decision = _workspace_check(candidate, gate, principal, app, domain="bmp")

    assert decision.allowed is False
    assert decision.code == "SKILL_METADATA_MANUAL_APPROVAL_REQUIRED"


@pytest.mark.parametrize("headers,remote_addr,open_workspace", [
    ({}, "127.0.0.1", False),
    ({}, "192.0.2.7", True),
    ({"Forwarded": "for=127.0.0.1"}, "127.0.0.1", True),
    ({"X-Forwarded-For": "127.0.0.1"}, "127.0.0.1", True),
    ({"Authorization": "Bearer claimed"}, "127.0.0.1", True),
    ({"Cookie": "cth_poms_v4_session=claimed"}, "127.0.0.1", True),
    *[({header: "17"}, "127.0.0.1", True)
      for header in sorted(p._LOCAL_WORKSPACE_IDENTITY_HEADERS)],
])
def test_workspace_permission_rechecks_open_loopback_transport_and_rejects_claims(
    registry, gate, app, headers, remote_addr, open_workspace,
):
    candidate = _candidate()
    principal = _workspace_principal(app)
    resource = _workspace_resource(candidate, principal, app)
    gate.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource=resource)
    app.config["LUMENIS_OPEN_WORKSPACE"] = open_workspace
    with _request(app, headers=headers, remote_addr=remote_addr):
        decision = p.check_skill_metadata_change_permission(
            candidate, gate=gate, principal=principal, domain_id="cth", global_scope=True,
        )
    assert decision.allowed is False


def test_forged_mixed_and_absent_workspace_identities_are_denied(registry, gate, app):
    candidate = _candidate()
    with pytest.raises(TypeError):
        p.LocalWorkspacePrincipal(_issuer=object())
    for forged in (
        {"principal_kind": "local_workspace", "principal_ref": "workspace:local", "actor_id": None},
        None,
    ):
        decision = p.check_skill_metadata_change_permission(
            candidate, gate=gate, principal=forged, domain_id="cth", global_scope=True,
        )
        assert decision.allowed is False
    principal = _workspace_principal(app)
    with pytest.raises(ValueError):
        p.skill_metadata_approval_resource(
            candidate, actor_id=1, principal=principal, domain_id="cth", global_scope=True,
        )
    with pytest.raises(ValueError):
        p.skill_metadata_approval_resource(
            candidate, domain_id="cth", global_scope=True,
        )
    with _request(app):
        assert p.check_local_workspace_scope_permission(
            principal, domain_id="cth", action="write", module="skills",
            global_scope=True, gate=gate,
        ).allowed is True
        # Scope admission alone still has no metadata approval token.
        assert p.check_skill_metadata_change_permission(
            candidate, gate=gate, principal=principal, domain_id="cth", global_scope=True,
        ).allowed is False


@pytest.mark.parametrize("approval_kind", ["wildcard", "wrong_resource", "revoked", "expired", "missing"])
def test_metadata_requires_a_live_exact_resource_approval(registry, gate, app, approval_kind):
    candidate = _candidate()
    principal = _workspace_principal(app)
    resource = _workspace_resource(candidate, principal, app)
    if approval_kind == "wildcard":
        token = gate.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource="*")
    elif approval_kind == "wrong_resource":
        token = gate.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource=resource + ":other")
    elif approval_kind in {"revoked", "expired"}:
        token = gate.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource=resource)
        if approval_kind == "revoked":
            gate.revoke_approval(token)
        else:
            gate._approvals[token].expires_at = datetime.now() - timedelta(seconds=1)
    decision = _workspace_check(candidate, gate, principal, app)
    assert decision.allowed is False


@pytest.mark.parametrize("kind", ["global", "environment"])
def test_testing_bypass_never_approves_skill_metadata(registry, gate, app, monkeypatch, kind):
    candidate = _candidate()
    principal = _workspace_principal(app)
    resource = _workspace_resource(candidate, principal, app)
    gate.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource=resource)
    if kind == "global":
        p.set_testing_bypass(True)
    else:
        monkeypatch.setenv("PERMISSION_GATE_TESTING", "1")
    decision = _workspace_check(candidate, gate, principal, app)
    assert decision.allowed is False
    assert decision.code == "SKILL_METADATA_MANUAL_APPROVAL_REQUIRED"


def test_account_identity_comes_from_live_session_and_admin_role(registry, gate, app, monkeypatch):
    from lumenis.auth import service

    monkeypatch.setattr(service, "ensure_initialized", lambda: None)
    candidate = _candidate()
    with _request(app, headers={"Authorization": "Bearer valid-owner-session"}):
        resource = p.skill_metadata_approval_resource(
            candidate, actor_id=1, domain_id="cth", global_scope=True,
        )
        gate.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource=resource)
        decision = p.check_skill_metadata_change_permission(
            candidate, gate=gate, actor_id=1, domain_id="cth", global_scope=True,
        )
        assert decision.allowed is True
        assert decision.caller == "actor:1" and decision.actor_id == 1
        mismatched = p.check_skill_metadata_change_permission(
            candidate, gate=gate, actor_id=2, domain_id="cth", global_scope=True,
        )
        assert mismatched.allowed is False
        assert mismatched.code == "SKILL_METADATA_PERMISSION_UNVERIFIED"

    with _request(app):
        no_session = p.check_skill_metadata_change_permission(
            candidate, gate=gate, actor_id=1, domain_id="cth", global_scope=True,
        )
        assert no_session.allowed is False


def test_account_member_scope_does_not_satisfy_metadata_admin_role(registry, gate, app, monkeypatch):
    from lumenis.auth import service

    monkeypatch.setattr(service, "ensure_initialized", lambda: None)
    candidate = _candidate()
    with _request(app, headers={"Authorization": "Bearer valid-member-session"}):
        resource = p.skill_metadata_approval_resource(
            candidate, actor_id=2, domain_id="cth", global_scope=True,
        )
        gate.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource=resource)
        decision = p.check_skill_metadata_change_permission(
            candidate, gate=gate, actor_id=2, domain_id="cth", global_scope=True,
        )
    assert decision.allowed is False
    assert decision.code == "SKILL_METADATA_ADMIN_REQUIRED"


def test_injected_gate_and_stale_uuid_cache_cannot_replace_canonical_exact_approval(registry, gate, app):
    candidate = _candidate()
    principal = _workspace_principal(app)
    resource = _workspace_resource(candidate, principal, app)
    token = gate.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource=resource)
    injected = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})
    injected.grant_approval(p.OperationType.CONFIG_MODIFY.value, resource=resource)
    with _request(app):
        denied = p.check_skill_metadata_change_permission(
            candidate, gate=injected, principal=principal, domain_id="cth", global_scope=True,
        )
    assert denied.allowed is False
    assert denied.code == "SKILL_METADATA_CANONICAL_PERMISSION_REQUIRED"

    with _request(app):
        cached = gate.check(
            p.OperationType.CONFIG_MODIFY, resource=resource, caller="workspace:local",
            domain_id="cth", exact_approval_required=True, operation_id=candidate.operation_id,
        )
        assert cached.allowed is True
    assert gate.revoke_approval(token) is True
    with _request(app):
        after_revoke = p.check_skill_metadata_change_permission(
            candidate, gate=gate, principal=principal, domain_id="cth", global_scope=True,
        )
    assert after_revoke.allowed is False


@pytest.mark.parametrize("domain,subject,brand,global_scope", [
    ("outside", None, None, True),
    ("cth", "SUBJ-CLAIM", "BRAND-CLAIM", False),
    ("cth", None, None, False),
    ("bmp", "SUBJ-CLAIM", None, False),
    ("bmp", None, "BRAND-CLAIM", True),
    ("cth", None, None, 1),
])
def test_invalid_domain_scope_forms_are_rejected(registry, gate, app, domain, subject, brand, global_scope):
    candidate = _candidate()
    principal = _workspace_principal(app)
    with _request(app):
        decision = p.check_skill_metadata_change_permission(
            candidate, gate=gate, principal=principal, domain_id=domain,
            subject_id=subject, brand_focus_id=brand, global_scope=global_scope,
        )
    assert decision.allowed is False
