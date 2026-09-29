from contextlib import contextmanager
from datetime import datetime, timedelta
import hashlib

import pytest
from flask import Flask

from lumenis.system.security import permission as p


@pytest.fixture
def workspace(monkeypatch):
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    active_focuses = {"brand-a", "brand-b"}
    monkeypatch.setattr(
        p,
        "_registered_resource_scope_exists",
        lambda domain, *, subject_id, brand_focus_id: (
            domain == "bmp" and brand_focus_id in active_focuses and subject_id is None
        ),
    )
    gate = p.PermissionGate(enabled_permissions={p.PermissionLevel.READ})
    return app, gate, active_focuses


@pytest.fixture(autouse=True)
def strict_permission_mode(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    previous = p._TESTING_BYPASS_ENABLED
    p.set_testing_bypass(False)
    yield
    p.set_testing_bypass(previous)


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


def _upload(*, filename="source.mp4", brand_focus_id="brand-a"):
    body = filename.encode("utf-8")
    return p.ContentSourceImport(
        actor_id=None,
        domain_id="bmp",
        subject_id=None,
        brand_focus_id=brand_focus_id,
        global_scope=False,
        filename=filename,
        size_bytes=len(body),
        body_sha256=hashlib.sha256(body).hexdigest(),
        principal_kind="local_workspace",
        principal_ref="workspace:local",
    )


def _principal(app):
    with _request(app):
        return p.resolve_local_workspace_principal(module="content", action="write")


def _prepare(app, gate, upload, *, principal=None, actor=None):
    with _request(app):
        current = principal or p.resolve_local_workspace_principal(
            module="content", action="write",
        )
        return p.prepare_content_source_import_confirmation(
            actor, upload, principal=current, gate=gate,
        )


def _confirm(app, gate, upload, confirmation_id, *, principal=None, actor=None, **changes):
    with _request(app):
        current = principal or p.resolve_local_workspace_principal(
            module="content", action="write",
        )
        return p.confirm_content_source_import(
            actor,
            confirmation_id,
            domain_id=changes.pop("domain_id", upload.domain_id),
            subject_id=changes.pop("subject_id", upload.subject_id),
            brand_focus_id=changes.pop("brand_focus_id", upload.brand_focus_id),
            global_scope=changes.pop("global_scope", upload.global_scope),
            confirmed=changes.pop("confirmed", True),
            principal=current,
            gate=gate,
            **changes,
        )


def _check(app, gate, upload, *, principal=None, actor=None):
    with _request(app):
        current = principal or p.resolve_local_workspace_principal(
            module="content", action="write",
        )
        return p.check_content_source_import_permission(
            actor, upload, principal=current, gate=gate,
        )


def _current_scope(upload):
    return {
        "domain_id": upload.domain_id,
        "subject_id": upload.subject_id,
        "brand_focus_id": upload.brand_focus_id,
        "global_scope": upload.global_scope,
    }


def test_local_confirmation_is_exact_and_does_not_create_general_db_write(workspace):
    app, gate, _ = workspace
    upload = _upload()
    principal = _principal(app)
    assert type(principal) is p.LocalWorkspacePrincipal
    assert not gate.has_permission(p.PermissionLevel.COMMIT)

    pending = _prepare(app, gate, upload, principal=principal)
    assert pending["allowed"]
    assert pending["resource"].startswith("content-source-import:v1:")
    assert not gate._approvals

    confirmed = _confirm(app, gate, upload, pending["confirmation_id"], principal=principal)
    assert confirmed.allowed and confirmed.approval_token is None
    assert confirmed.actor_id is None
    assert confirmed.caller == "workspace:local"
    assert confirmed.principal_kind == "local_workspace"
    assert confirmed.principal_ref == "workspace:local"
    assert not gate.has_permission(p.PermissionLevel.COMMIT)

    receipt = _check(app, gate, upload, principal=principal)
    assert receipt.allowed and receipt.approval_token
    assert receipt.actor_id is None and receipt.caller == "workspace:local"
    assert receipt.principal_kind == "local_workspace"
    assert receipt.resource == pending["resource"]

    gate.grant_permission(p.PermissionLevel.COMMIT)
    with _request(app):
        generic_write = gate.check(
            p.OperationType.DB_WRITE,
            resource=receipt.resource,
            caller="workspace:local",
            domain_id=upload.domain_id,
            exact_approval_required=True,
        )
        wrong_caller = gate.check(
            p.OperationType.DB_WRITE,
            resource=receipt.resource,
            caller="actor:1",
            domain_id=upload.domain_id,
            exact_approval_required=True,
            content_import_grant=receipt.approval_token,
        )
    assert not generic_write.allowed
    assert not wrong_caller.allowed
    assert _check(app, gate, upload, principal=principal).allowed

    assert gate.revoke_approval(receipt.approval_token)
    assert not _check(app, gate, upload, principal=principal).allowed


def test_old_account_import_resource_hash_is_unchanged(monkeypatch):
    monkeypatch.setattr(p, "_actor_has_scope_action", lambda *args: True)
    monkeypatch.setattr(p, "_load_actor_scope_role", lambda *args: "admin")
    monkeypatch.setattr(p, "_registered_resource_scope_exists", lambda *a, **k: True)
    gate = p.PermissionGate()
    upload = p.ContentSourceImport(
        actor_id=1,
        domain_id="bmp",
        subject_id=None,
        brand_focus_id="brand-a",
        global_scope=False,
        filename="source.mp4",
        size_bytes=3,
        body_sha256=hashlib.sha256(b"abc").hexdigest(),
    )
    scope = p.check_actor_scope_permission(
        {"id": 1}, domain_id="bmp", action="write", module="content",
        brand_focus_id="brand-a", gate=gate,
    )
    assert upload.principal_kind is None and upload.principal_ref is None
    assert p.content_source_import_resource(scope, upload, gate=gate) == (
        "content-source-import:v1:75dd3fdb4d04fffa2115a89d0d936bd1fb2b4175a2a5c8d542a728ca05498698"
    )


def test_actor_and_principal_together_or_json_principal_are_rejected(workspace):
    app, gate, _ = workspace
    upload = _upload()
    principal = _principal(app)
    mixed = _prepare(app, gate, upload, principal=principal, actor={"id": 1})
    fake = {
        "principal_kind": "local_workspace",
        "principal_ref": "workspace:local",
        "actor_id": None,
    }
    with _request(app):
        missing_principal = p.prepare_content_source_import_confirmation(
            None, upload, gate=gate,
        )
        fake_result = p.prepare_content_source_import_confirmation(
            None, upload, principal=fake, gate=gate,
        )
    assert not mixed["allowed"]
    assert not missing_principal["allowed"]
    assert not fake_result["allowed"]
    assert not gate._content_import_confirmations


def test_cross_scope_and_account_cannot_confirm_workspace_nonce(workspace):
    app, gate, _ = workspace
    upload = _upload()
    principal = _principal(app)
    pending = _prepare(app, gate, upload, principal=principal)
    nonce = pending["confirmation_id"]

    changed_scope = _confirm(
        app, gate, upload, nonce, principal=principal, brand_focus_id="brand-b",
    )
    account = _confirm(app, gate, upload, nonce, actor={"id": 1})
    assert not changed_scope.allowed and changed_scope.code == "CONTENT_SOURCE_SCOPE_MISMATCH"
    assert not account.allowed
    assert _confirm(app, gate, upload, nonce, principal=principal).allowed


def test_cancel_revokes_only_the_selected_workspace_import(workspace):
    app, gate, _ = workspace
    first, second = _upload(), _upload(filename="second.mp4", brand_focus_id="brand-b")
    principal = _principal(app)
    first_pending = _prepare(app, gate, first, principal=principal)
    second_pending = _prepare(app, gate, second, principal=principal)
    assert _confirm(app, gate, first, first_pending["confirmation_id"], principal=principal).allowed
    assert _confirm(app, gate, second, second_pending["confirmation_id"], principal=principal).allowed
    first_receipt = _check(app, gate, first, principal=principal)
    second_receipt = _check(app, gate, second, principal=principal)

    with _request(app):
        cancelled = p.cancel_content_source_import_confirmation(
            None, first_pending["confirmation_id"], _current_scope(first),
            principal=principal, gate=gate,
        )
    assert cancelled
    assert not gate._approval_token_is_valid(
        first_receipt.approval_token, p.OperationType.DB_WRITE.value, first_receipt.resource,
    )
    assert not _check(app, gate, first, principal=principal).allowed
    assert _check(app, gate, second, principal=principal).allowed


def test_workspace_close_invalidates_pending_and_confirmed_authority(workspace):
    app, gate, _ = workspace
    upload = _upload()
    principal = _principal(app)
    pending = _prepare(app, gate, upload, principal=principal)

    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    closed_confirmation = _confirm(
        app, gate, upload, pending["confirmation_id"], principal=principal,
    )
    assert not closed_confirmation.allowed
    assert gate._content_import_confirmations[pending["confirmation_id"]].state == "cancelled"

    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    replay = _confirm(app, gate, upload, pending["confirmation_id"], principal=principal)
    assert not replay.allowed

    next_pending = _prepare(app, gate, upload, principal=principal)
    assert _confirm(app, gate, upload, next_pending["confirmation_id"], principal=principal).allowed
    receipt = _check(app, gate, upload, principal=principal)
    token = receipt.approval_token
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    closed_check = _check(app, gate, upload, principal=principal)
    assert not closed_check.allowed
    assert token not in gate._content_import_grants
    assert not gate._approval_token_is_valid(
        token, p.OperationType.DB_WRITE.value, receipt.resource,
    )

    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    assert not _check(app, gate, upload, principal=principal).allowed


def test_expired_workspace_confirmation_cannot_be_replayed(workspace):
    app, gate, _ = workspace
    upload = _upload()
    principal = _principal(app)
    pending = _prepare(app, gate, upload, principal=principal)
    gate._content_import_confirmations[pending["confirmation_id"]].expires_at = (
        datetime.now() - timedelta(seconds=1)
    )
    expired = _confirm(app, gate, upload, pending["confirmation_id"], principal=principal)
    assert not expired.allowed
    assert pending["confirmation_id"] not in gate._content_import_confirmations


def test_invalidating_one_workspace_grant_does_not_mutate_live_iteration(workspace):
    app, gate, active_focuses = workspace
    first = _upload(brand_focus_id="brand-a")
    second = _upload(filename="second.mp4", brand_focus_id="brand-b")
    principal = _principal(app)
    first_pending = _prepare(app, gate, first, principal=principal)
    second_pending = _prepare(app, gate, second, principal=principal)
    assert _confirm(app, gate, first, first_pending["confirmation_id"], principal=principal).allowed
    assert _confirm(app, gate, second, second_pending["confirmation_id"], principal=principal).allowed
    first_receipt = _check(app, gate, first, principal=principal)
    second_receipt = _check(app, gate, second, principal=principal)
    first_token, second_token = first_receipt.approval_token, second_receipt.approval_token

    active_focuses.remove("brand-a")
    with _request(app):
        found = gate._find_content_import_grant(first_receipt.resource, "workspace:local")
    assert found is None
    assert first_token not in gate._content_import_grants
    assert second_token in gate._content_import_grants
    assert gate._approval_token_is_valid(
        second_token, p.OperationType.DB_WRITE.value, second_receipt.resource,
    )
