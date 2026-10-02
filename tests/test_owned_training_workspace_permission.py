from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import json
import sqlite3

from flask import Flask
import pytest

from lumenis.system.ai_gateway.owned_training import TrainingApprovalRequest
from lumenis.system.security import permission as p


ACCOUNT_RESOURCE = (
    "owned_training:v1:"
    "21ec99a8d70e93c614fc1137dbccb4ab29e5ffc2994a6187d64ee5fe4fdea5c0"
)


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


@pytest.fixture
def scope_db(tmp_path, monkeypatch):
    path = tmp_path / "owned-training-workspace.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE v4_users (
                id INTEGER PRIMARY KEY, role TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE v4_member_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL, module TEXT NOT NULL, action TEXT NOT NULL,
                data_scope TEXT, time_range TEXT, granted_by INTEGER, created_at TEXT,
                updated_at TEXT, UNIQUE(user_id, product_id, module, action)
            );
            INSERT INTO v4_users (id, role, status) VALUES
                (1, 'user', 'active'), (2, 'user', 'active');
        """)
        import subject_registry

        subject_registry.ensure_schema(conn)
        conn.execute("""
            INSERT INTO lumenis_subject_registry (
                subject_id, brand_focus_id, domain_id, subject_type,
                name_en, name_zh, name_en_norm, name_zh_norm, industry,
                keywords_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "SUBJ-CTH-A", None, "CTH", "company", "North Center", "北区中心",
            "north center", "北区中心", "retail", "[]", "configured",
            "2026-09-24", "2026-09-24",
        ))
        conn.execute("""
            INSERT INTO lumenis_subject_registry (
                subject_id, brand_focus_id, domain_id, subject_type,
                name_en, name_zh, name_en_norm, name_zh_norm, industry,
                keywords_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "SUBJ-BMP-A", "BRAND-BMP-A", "BMP", "brand", "North Brand", "北方品牌",
            "north brand", "北方品牌", "beauty", "[]", "configured",
            "2026-09-24", "2026-09-24",
        ))
    return path


@contextmanager
def _request(app, *, headers=None, remote_addr="127.0.0.1"):
    request_headers = {"Host": "localhost"}
    if headers:
        request_headers.update(headers)
    with app.test_request_context(
        "/",
        headers=request_headers,
        environ_overrides={"REMOTE_ADDR": remote_addr},
    ):
        yield


def _request_data(**changes):
    values = {
        "model_id": "openai/gpt-oss-20b",
        "model_revision": "6cee5e81ee83917806bbde320786a8fb61efebee",
        "train_sha256": "1" * 64,
        "heldout_sha256": "2" * 64,
        "domain_id": "cth",
        "scopes": ("GLOBAL / ALL",),
        "recipe": "openai-h100-bf16",
        "manifest_sha256": "3" * 64,
    }
    values.update(changes)
    return TrainingApprovalRequest(**values)


def _context(scope="GLOBAL / ALL", *, domain="cth", global_scope=True):
    product_id = "CTH" if domain == "cth" else "ZBMP"
    return {"scope_descriptors": {scope: {
        "domain_id": domain,
        "product_id": product_id,
        "global_scope": global_scope,
        "subject_id": None if global_scope or domain == "bmp" else scope,
        "brand_focus_id": scope if domain == "bmp" and not global_scope else None,
    }}}


def _gate():
    return p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})


def _grant_account_scope(path, actor_id=1, product_id="CTH", data_scope=None):
    with sqlite3.connect(path) as conn:
        conn.execute("""
            INSERT INTO v4_member_authorizations (
                user_id, product_id, module, action, data_scope, time_range
            ) VALUES (?, ?, 'owned_training', 'write', ?, NULL)
        """, (actor_id, product_id, json.dumps(data_scope or {"global": True})))


def _authorize_account(gate, request, *, context=None, actor_id=1, domain_id="cth"):
    context = context or _context()
    resource = p.owned_training_approval_resource(
        request, actor_id=actor_id, domain_id=domain_id, context=context,
    )
    token = gate.grant_approval(
        p.OperationType.MODEL_TRAIN.value, resource=resource, granted_by="test-human",
    )
    verifier = p.make_owned_training_approval_verifier(
        gate, actor_id=actor_id, domain_id=domain_id, context=context,
    )
    return verifier, token, resource


def _authorize_workspace(app, gate, request, *, context=None, domain_id="cth"):
    context = context or _context()
    with _request(app):
        principal = p.resolve_local_workspace_principal(
            module="owned_training", action="write",
        )
        assert type(principal) is p.LocalWorkspacePrincipal
        resource = p.owned_training_approval_resource(
            request, actor_id=None, principal=principal,
            domain_id=domain_id, context=context,
        )
        token = gate.grant_approval(
            p.OperationType.MODEL_TRAIN.value,
            resource=resource,
            granted_by="test-human",
        )
        verifier = p.make_owned_training_approval_verifier(
            gate, actor_id=None, principal=principal,
            domain_id=domain_id, context=context,
        )
    return principal, verifier, token, resource


def test_identity_accepts_only_strict_account_or_sealed_live_workspace(app):
    assert p.owned_training_identity(actor_id=17) == {
        "actor_id": 17,
        "caller": "actor:17",
        "principal_kind": None,
        "principal_ref": None,
        "identity_kind": "account",
    }
    for invalid_actor in (True, False, 0, -1, 1.0):
        with pytest.raises(ValueError):
            p.owned_training_identity(actor_id=invalid_actor)
    with pytest.raises(ValueError):
        p.owned_training_identity()

    with _request(app):
        principal = p.resolve_local_workspace_principal(
            module="owned_training", action="write",
        )
        assert type(principal) is p.LocalWorkspacePrincipal
        assert p.owned_training_identity(principal=principal) == {
            "actor_id": None,
            "caller": "workspace:local",
            "principal_kind": "local_workspace",
            "principal_ref": "workspace:local",
            "identity_kind": "workspace",
        }
        with pytest.raises(ValueError):
            p.owned_training_identity(actor_id=17, principal=principal)
        with pytest.raises(ValueError):
            p.owned_training_identity(principal={
                "principal_kind": "local_workspace",
                "principal_ref": "workspace:local",
                "actor_id": None,
            })
        with pytest.raises(TypeError):
            p.LocalWorkspacePrincipal(_issuer=object())

    with pytest.raises(ValueError):
        p.owned_training_identity(principal=principal)
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    with _request(app):
        with pytest.raises(ValueError):
            p.owned_training_identity(principal=principal)


def test_legacy_account_approval_resource_bytes_are_unchanged():
    request = _request_data()
    assert p.owned_training_approval_resource(
        request, actor_id=1, domain_id="cth", context=_context(),
    ) == ACCOUNT_RESOURCE


def test_workspace_scope_admission_does_not_grant_training(scope_db, app):
    request = _request_data(scopes=("SUBJ-CTH-A",))
    context = _context("SUBJ-CTH-A", global_scope=False)
    gate = _gate()
    with _request(app):
        principal = p.resolve_local_workspace_principal(
            module="owned_training", action="write",
        )
        assert type(principal) is p.LocalWorkspacePrincipal
        identity = p.owned_training_identity(principal=principal)
        assert identity["identity_kind"] == "workspace"
        admitted = p.check_local_workspace_scope_permission(
            principal, domain_id="cth", action="write", module="owned_training",
            subject_id="SUBJ-CTH-A", global_scope=False, gate=gate,
        )
        assert admitted.allowed is True
        assert admitted.actor_id is None
        assert admitted.caller == "workspace:local"
        assert admitted.principal_kind == "local_workspace"
        assert admitted.principal_ref == "workspace:local"

        resource = p.owned_training_approval_resource(
            request, principal=principal, domain_id="cth", context=context,
        )
        verifier = p.make_owned_training_approval_verifier(
            gate, principal=principal, domain_id="cth", context=context,
        )
        effect = gate.check(
            p.OperationType.MODEL_TRAIN, resource=resource,
            caller="workspace:local", domain_id="cth", exact_approval_required=True,
        )
        assert effect.allowed is False
        assert verifier(request) is False


def test_approved_exact_workspace_training_path_binds_principal_and_resource(
    scope_db, app,
):
    request = _request_data(scopes=("SUBJ-CTH-A",))
    context = _context("SUBJ-CTH-A", global_scope=False)
    gate = _gate()
    principal, verifier, token, resource = _authorize_workspace(
        app, gate, request, context=context,
    )
    with _request(app):
        payload = p._owned_training_payload(
            request, principal=principal, domain_id="cth", context=context,
        )
        assert verifier(request) is True

    assert payload["actor_id"] is None
    assert payload["principal_kind"] == "local_workspace"
    assert payload["principal_ref"] == "workspace:local"
    canonical_payload = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    assert resource == "owned_training:v1:" + hashlib.sha256(
        canonical_payload
    ).hexdigest()
    assert resource != p.owned_training_approval_resource(
        request, actor_id=1, domain_id="cth", context=context,
    )
    audit = gate.get_audit_log(
        operation_type="model_train", result_filter="allowed",
    )[-1]
    assert audit["resource"] == resource
    assert audit["caller"] == "workspace:local"
    assert token == gate.get_valid_approval_token(
        p.OperationType.MODEL_TRAIN.value, resource, exact=True,
    )


@pytest.mark.parametrize(
    "blocked,headers,open_workspace,remote_addr",
    [
        ("closed", {}, False, "127.0.0.1"),
        ("remote", {}, True, "192.0.2.7"),
        ("forwarded", {"X-Forwarded-For": "127.0.0.1"}, True, "127.0.0.1"),
        ("forwarded-standard", {"Forwarded": "for=127.0.0.1"}, True, "127.0.0.1"),
        ("authorization", {"Authorization": "Bearer claimed"}, True, "127.0.0.1"),
        ("cookie", {"Cookie": "cth_poms_v4_session=claimed"}, True, "127.0.0.1"),
        *[
            (header, {header: "17"}, True, "127.0.0.1")
            for header in sorted(p._LOCAL_WORKSPACE_IDENTITY_HEADERS)
        ],
    ],
)
def test_workspace_identity_and_verifier_reject_closed_remote_and_claimed_transports(
    scope_db, app, blocked, headers, open_workspace, remote_addr,
):
    request = _request_data()
    gate = _gate()
    principal, verifier, _token, _resource = _authorize_workspace(app, gate, request)
    app.config["LUMENIS_OPEN_WORKSPACE"] = open_workspace
    with _request(app, headers=headers, remote_addr=remote_addr):
        with pytest.raises(ValueError):
            p.owned_training_identity(principal=principal)
        assert verifier(request) is False


@pytest.mark.parametrize(
    "change",
    [
        {"model_id": "different/model"},
        {"train_sha256": "4" * 64},
        {"scopes": ("SUBJ-CTH-A",)},
        {"domain_id": "bmp"},
    ],
)
def test_workspace_approval_rejects_changed_model_input_scope_or_domain(
    scope_db, app, change,
):
    request = _request_data()
    gate = _gate()
    _principal, verifier, _token, _resource = _authorize_workspace(app, gate, request)
    changed = replace(request, **change)
    with _request(app):
        assert verifier(changed) is False


def test_workspace_verifier_freezes_canonical_scope_context(scope_db, app):
    request = _request_data()
    context = _context()
    gate = _gate()
    _principal, verifier, _token, _resource = _authorize_workspace(
        app, gate, request, context=context,
    )
    context["scope_descriptors"]["GLOBAL / ALL"]["product_id"] = "ZBMP"
    with _request(app):
        assert verifier(request) is True


@pytest.mark.parametrize("state", ["revoked", "expired", "unregistered"])
def test_workspace_verifier_rechecks_live_approval_and_registered_scope(
    scope_db, app, state,
):
    request = _request_data(scopes=("SUBJ-CTH-A",))
    context = _context("SUBJ-CTH-A", global_scope=False)
    gate = _gate()
    _principal, verifier, token, _resource = _authorize_workspace(
        app, gate, request, context=context,
    )
    with _request(app):
        assert verifier(request) is True
    if state == "revoked":
        assert gate.revoke_approval(token) is True
    elif state == "expired":
        gate._approvals[token].expires_at = datetime.now() - timedelta(seconds=1)
    else:
        with sqlite3.connect(scope_db) as conn:
            conn.execute(
                "DELETE FROM lumenis_subject_registry WHERE subject_id=?",
                ("SUBJ-CTH-A",),
            )
    with _request(app):
        assert verifier(request) is False


@pytest.mark.parametrize("identity_kind", ["account", "workspace"])
@pytest.mark.parametrize("bypass", ["global", "environment"])
def test_testing_bypass_never_approves_training_for_either_identity(
    scope_db, app, monkeypatch, identity_kind, bypass,
):
    request = _request_data()
    gate = _gate()
    if identity_kind == "account":
        _grant_account_scope(scope_db, actor_id=1)
        verifier, _token, _resource = _authorize_account(gate, request)
    else:
        _principal, verifier, _token, _resource = _authorize_workspace(
            app, gate, request,
        )
    if bypass == "global":
        p.set_testing_bypass(True)
    else:
        monkeypatch.setenv("PERMISSION_GATE_TESTING", "1")
    if identity_kind == "account":
        assert verifier(request) is False
    else:
        with _request(app):
            assert verifier(request) is False
