"""Permission boundary checks; account reads are fixtures, never user acceptance."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from lumenis.system.security import permission as p


@pytest.fixture
def boundary(monkeypatch, tmp_path):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    previous = p._TESTING_BYPASS_ENABLED
    p.set_testing_bypass(False)
    state = {"active": True, "module_calls": [], "db_calls": 0}
    def action(actor_id, product, module, action):
        state["module_calls"].append((actor_id, product, module, action))
        return state["active"]
    monkeypatch.setattr(p, "_actor_has_scope_action", action)
    monkeypatch.setattr(p, "_load_actor_scope_role", lambda actor_id: "user")
    monkeypatch.setattr(p, "_registered_resource_scope_exists", lambda *a, **k: True)
    monkeypatch.setattr(p, "_load_actor_scope_grants", lambda actor_id: [
        {"product_id": product, "module": "content", "action": "write",
         "data_scope": json.dumps({"global": True})}
        for product in ("CTH", "ZBMP")
    ])
    def no_db(*args, **kwargs):
        state["db_calls"] += 1
        raise AssertionError("permission precursor must not open a database")
    monkeypatch.setattr(sqlite3, "connect", no_db)
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "must-not-exist.db"))
    gate = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})
    upload = p.ContentSourceImport(
        actor_id=1, domain_id="bmp", subject_id=None, brand_focus_id="brand-a",
        global_scope=False, filename="source.mp4", size_bytes=3,
        body_sha256=hashlib.sha256(b"abc").hexdigest(),
    )
    yield gate, upload, state
    assert state["db_calls"] == 0
    assert not list(tmp_path.iterdir())
    p.set_testing_bypass(previous)


def scope(gate, upload, *, action="write"):
    return p.check_actor_scope_permission(
        {"id": upload.actor_id}, domain_id=upload.domain_id, action=action,
        module="content", subject_id=upload.subject_id,
        brand_focus_id=upload.brand_focus_id, global_scope=upload.global_scope,
        gate=gate,
    )


def resource(gate, upload):
    return p.content_source_import_resource(scope(gate, upload), upload, gate=gate)


def check(gate, upload, actor_id=None):
    return p.check_content_source_import_permission(
        {"id": upload.actor_id if actor_id is None else actor_id}, upload, gate=gate
    )


def approve(gate, upload, **kwargs):
    return gate.grant_approval("db_write", resource=resource(gate, upload), **kwargs)


def test_unapproved_denied_approved_exact_receipt_cancel_denied(boundary):
    gate, upload, state = boundary
    denied = check(gate, upload)
    assert not denied.allowed and denied.requires_approval
    token = approve(gate, upload)
    allowed = check(gate, upload)
    assert allowed.allowed and allowed.approval_token == token
    assert allowed.resource == denied.resource
    assert allowed.operation_type == "db_write"
    assert allowed.risk_level == "high" and allowed.permission_required == "commit"
    assert allowed.caller == "actor:1" and allowed.brand_focus_id == "brand-a"
    assert allowed.scope_audit_id and allowed.audit_id != allowed.scope_audit_id
    assert allowed.operation_id is None and not allowed.idempotent_hit
    assert all(call[2:] == ("content", "write") for call in state["module_calls"])
    assert gate.revoke_approval(token)
    assert not check(gate, upload).allowed


@pytest.mark.parametrize("change", [
    {"actor_id": 2}, {"brand_focus_id": "brand-b"}, {"filename": "renamed.mp4"},
    {"size_bytes": 4}, {"body_sha256": hashlib.sha256(b"abd").hexdigest()},
    {"global_scope": True, "brand_focus_id": None},
    {"domain_id": "cth", "subject_id": "subject-a", "brand_focus_id": None},
])
def test_exact_approval_not_reused_across_actor_scope_or_file(boundary, change):
    gate, upload, _ = boundary
    approve(gate, upload)
    changed = replace(upload, **change)
    assert resource(gate, changed) != resource(gate, upload)
    assert not check(gate, changed).allowed
    assert check(gate, upload).allowed


def test_global_approval_not_reused_for_focus(boundary):
    gate, upload, _ = boundary
    global_upload = replace(upload, global_scope=True, brand_focus_id=None)
    approve(gate, global_upload)
    assert check(gate, global_upload).allowed
    assert not check(gate, upload).allowed


@pytest.mark.parametrize("operation,target", [
    ("*", None), ("*", "exact"), ("db_write", None),
    ("db_write", "*"), ("data_import", "exact"), ("data_export", "exact"),
])
def test_wildcard_and_other_operation_approvals_do_not_authorize(boundary, operation, target):
    gate, upload, _ = boundary
    gate.grant_approval(operation, resource=resource(gate, upload) if target == "exact" else target)
    assert not check(gate, upload).allowed


def test_expiry_and_account_revocation_are_rechecked(boundary):
    gate, upload, state = boundary
    token = approve(gate, upload)
    assert check(gate, upload).allowed
    gate._approvals[token].expires_at = datetime.now() - timedelta(seconds=1)
    assert not check(gate, upload).allowed
    approve(gate, upload)
    state["active"] = False
    assert not check(gate, upload).allowed


def test_actor_descriptor_mismatch_and_no_commit_permission_deny(boundary):
    gate, upload, _ = boundary
    approve(gate, upload)
    assert not check(gate, upload, actor_id=2).allowed
    gate.revoke_permission(p.PermissionLevel.COMMIT)
    assert not check(gate, upload).allowed


@pytest.mark.parametrize("kind", ["flag", "environment"])
def test_testing_bypass_cannot_authorize_source_import(boundary, monkeypatch, kind):
    gate, upload, _ = boundary
    approve(gate, upload)
    if kind == "flag":
        p.set_testing_bypass(True)
    else:
        monkeypatch.setenv("PERMISSION_GATE_TESTING", "1")
    result = check(gate, upload)
    assert not result.allowed
    assert result.reason == "CONTENT_SOURCE_TESTING_BYPASS_FORBIDDEN"


@pytest.mark.parametrize("mutation", [
    {"allowed": False}, {"verification_state": "unavailable"},
    {"scope_action": "read"}, {"scope_audit_id": "forged"},
    {"audit_id": "forged", "scope_audit_id": "forged"},
    {"caller": "actor:2"}, {"resource": "bmp:brand-b"},
    {"operation_type": "resource_scope_read"},
])
def test_forged_or_denied_scope_receipt_rejected(boundary, mutation):
    gate, upload, _ = boundary
    receipt = replace(scope(gate, upload), **mutation)
    with pytest.raises(ValueError):
        p.content_source_import_resource(receipt, upload, gate=gate)


def test_another_gate_and_audit_with_changed_scope_cannot_be_borrowed(boundary):
    gate, upload, _ = boundary
    receipt = scope(gate, upload)
    with pytest.raises(ValueError):
        p.content_source_import_resource(receipt, upload, gate=p.PermissionGate())
    changed = replace(upload, brand_focus_id="brand-b")
    forged = replace(receipt, brand_focus_id="brand-b", resource="bmp:brand-b")
    with pytest.raises(ValueError):
        p.content_source_import_resource(forged, changed, gate=gate)


@pytest.mark.parametrize("change", [
    {"actor_id": True}, {"size_bytes": True}, {"size_bytes": 0},
    {"size_bytes": 128 * 1024 * 1024 + 1}, {"body_sha256": "a" * 63},
    {"body_sha256": "A" * 64}, {"filename": "../source.mp4"},
    {"filename": "C:\\source.mp4"}, {"filename": "source.mp4:stream"},
    {"filename": " source.mp4"}, {"filename": "source.mp4."},
    {"filename": "source\n.mp4"}, {"filename": "a" * 256},
    {"global_scope": True}, {"subject_id": "other-domain"},
])
def test_invalid_upload_descriptors_never_authorize(boundary, change):
    gate, upload, _ = boundary
    approve(gate, upload)
    assert not check(gate, replace(upload, **change)).allowed


def test_client_dictionary_cannot_supply_rights_or_permission(boundary):
    gate, upload, _ = boundary
    client = {**asdict(upload), "rights": "cleared", "approval_token": "claimed"}
    with pytest.raises(ValueError):
        p.check_content_source_import_permission({"id": 1}, client, gate=gate)
    with pytest.raises(ValueError):
        p.content_source_import_resource(scope(gate, upload), client, gate=gate)


def test_base_serializer_and_unknown_rights_remain_unchanged(boundary):
    gate, upload, _ = boundary
    approve(gate, upload)
    result = check(gate, upload)
    assert set(result.to_dict()) == set(p.PermissionResult.__dataclass_fields__)
    assert result.to_scope_dict()["brand_focus_id"] == "brand-a"
    assert not any("right" in key or "publish" in key for key in result.to_scope_dict())
    assert not gate.is_approved("data_export", result.resource)
    assert not gate.is_approved("ad_execute", result.resource)


def test_check_has_no_file_or_network_effects(boundary, monkeypatch):
    import builtins
    import socket

    gate, upload, _ = boundary
    approve(gate, upload)
    def forbidden(*args, **kwargs):
        raise AssertionError("permission check attempted an external effect")
    with monkeypatch.context() as effects:
        effects.setattr(builtins, "open", forbidden)
        effects.setattr(Path, "open", forbidden)
        effects.setattr(socket, "socket", forbidden)
        assert check(gate, upload).allowed
        gate.revoke_all_approvals()
        assert not check(gate, upload).allowed


def import_scope(upload):
    return {
        "domain_id": upload.domain_id,
        "subject_id": upload.subject_id,
        "brand_focus_id": upload.brand_focus_id,
        "global_scope": upload.global_scope,
    }


def prepare(gate, upload):
    return p.prepare_content_source_import_confirmation(
        {"id": upload.actor_id}, upload, gate=gate,
    )


def confirm(gate, upload, confirmation_id, **changes):
    arguments = {**import_scope(upload), "confirmed": True, **changes}
    return p.confirm_content_source_import(
        {"id": upload.actor_id}, confirmation_id, gate=gate, **arguments,
    )


def test_confirmation_grants_only_the_exact_import_without_enabling_commit(boundary):
    gate, upload, _ = boundary
    gate.revoke_permission(p.PermissionLevel.COMMIT)
    pending = prepare(gate, upload)
    assert pending["allowed"] and pending["code"] == "CONTENT_SOURCE_CONFIRMATION_PENDING"
    assert pending["resource"] == resource(gate, upload)
    assert pending["filename"] == upload.filename
    assert pending["size_bytes"] == upload.size_bytes
    assert pending["body_sha256"] == upload.body_sha256
    assert "approval_token" not in pending and not gate._approvals
    assert not check(gate, upload).allowed

    result = confirm(gate, upload, pending["confirmation_id"])
    assert result.allowed and result.approval_token is None
    assert result.code == "CONTENT_SOURCE_IMPORT_ALLOWED"
    assert result.audit_id and result.scope_audit_id
    assert not gate.has_permission(p.PermissionLevel.COMMIT)
    receipt = check(gate, upload)
    assert receipt.allowed and receipt.approval_token

    # A confirmed import is not a general DB-write or cross-actor approval,
    # even for a caller which already has COMMIT permission.
    gate.grant_permission(p.PermissionLevel.COMMIT)
    for caller in ("actor:1", "actor:2"):
        assert not gate.check(
            p.OperationType.DB_WRITE, resource=receipt.resource, caller=caller,
            domain_id=upload.domain_id, exact_approval_required=True,
        ).allowed
    assert not gate.check(
        p.OperationType.DB_WRITE, resource=receipt.resource, caller="actor:2",
        domain_id=upload.domain_id, exact_approval_required=True,
        content_import_grant=receipt.approval_token,
    ).allowed
    assert check(gate, upload).allowed


@pytest.mark.parametrize("changes", [
    {"domain_id": "cth"}, {"subject_id": "subject-other"},
    {"brand_focus_id": "brand-other"}, {"global_scope": True},
    {"global_scope": 1},
])
def test_confirmation_cannot_change_the_prepared_scope(boundary, changes):
    gate, upload, _ = boundary
    pending = prepare(gate, upload)
    denied = confirm(gate, upload, pending["confirmation_id"], **changes)
    assert not denied.allowed and denied.code == "CONTENT_SOURCE_SCOPE_MISMATCH"
    assert not gate._approvals
    assert confirm(gate, upload, pending["confirmation_id"]).allowed


@pytest.mark.parametrize("change", [
    {"actor_id": 2}, {"filename": "different.mp4"}, {"size_bytes": 4},
    {"body_sha256": hashlib.sha256(b"abd").hexdigest()},
    {"brand_focus_id": "brand-b"},
])
def test_confirmed_grant_does_not_authorize_a_different_upload(boundary, change):
    gate, upload, _ = boundary
    pending = prepare(gate, upload)
    assert confirm(gate, upload, pending["confirmation_id"]).allowed
    assert not check(gate, replace(upload, **change)).allowed
    assert check(gate, upload).allowed


@pytest.mark.parametrize("confirmed", [False, None, 1, "true"])
def test_confirmation_requires_literal_user_confirmation(boundary, confirmed):
    gate, upload, _ = boundary
    pending = prepare(gate, upload)
    result = confirm(gate, upload, pending["confirmation_id"], confirmed=confirmed)
    assert not result.allowed and result.code == "CONTENT_SOURCE_CONFIRMATION_DECLINED"
    assert not gate._approvals


def test_confirmation_nonce_cannot_be_borrowed_replayed_or_reused_after_revocation(boundary):
    gate, upload, _ = boundary
    pending = prepare(gate, upload)
    nonce = pending["confirmation_id"]
    wrong_actor = confirm(gate, replace(upload, actor_id=2), nonce)
    assert not wrong_actor.allowed and wrong_actor.code == "CONTENT_SOURCE_ACTOR_MISMATCH"
    assert not confirm(p.PermissionGate(), upload, nonce).allowed
    assert not confirm(gate, upload, "invented-confirmation").allowed
    assert confirm(gate, upload, nonce).allowed
    token = check(gate, upload).approval_token
    assert not confirm(gate, upload, nonce).allowed
    # The owning import handler consumes the authorization using this existing
    # revocation API. This unit test does not claim that handler is integrated.
    assert gate.revoke_approval(token)
    assert not check(gate, upload).allowed
    assert not confirm(gate, upload, nonce).allowed


@pytest.mark.parametrize("state", ["pending", "confirmed"])
def test_cancellation_is_bound_to_actor_scope_and_revokes_only_its_grant(boundary, state):
    gate, upload, _ = boundary
    pending = prepare(gate, upload)
    nonce = pending["confirmation_id"]
    other_upload = replace(upload, filename="other.mp4")
    other = prepare(gate, other_upload)
    assert confirm(gate, other_upload, other["confirmation_id"]).allowed
    if state == "confirmed":
        assert confirm(gate, upload, nonce).allowed
    assert not p.cancel_content_source_import_confirmation(
        {"id": 2}, nonce, import_scope(upload), gate=gate,
    )
    assert not p.cancel_content_source_import_confirmation(
        {"id": 1}, nonce, import_scope(replace(upload, brand_focus_id="other")), gate=gate,
    )
    assert p.cancel_content_source_import_confirmation(
        {"id": 1}, nonce, import_scope(upload), gate=gate,
    )
    assert not check(gate, upload).allowed
    assert not confirm(gate, upload, nonce).allowed
    assert check(gate, other_upload).allowed
    assert not p.cancel_content_source_import_confirmation(
        {"id": 1}, nonce, import_scope(upload), gate=gate,
    )


@pytest.mark.parametrize("stage", ["confirmation", "grant", "approval"])
def test_expired_confirmation_or_authority_cannot_authorize_import(boundary, stage):
    gate, upload, _ = boundary
    pending = prepare(gate, upload)
    nonce = pending["confirmation_id"]
    expired = datetime.now() - timedelta(seconds=1)
    if stage == "confirmation":
        gate._content_import_confirmations[nonce].expires_at = expired
        assert not confirm(gate, upload, nonce).allowed
        assert nonce not in gate._content_import_confirmations
    else:
        assert confirm(gate, upload, nonce).allowed
        token = check(gate, upload).approval_token
        if stage == "grant":
            gate._content_import_grants[token].expires_at = expired
        else:
            gate._approvals[token].expires_at = expired
    assert not check(gate, upload).allowed


@pytest.mark.parametrize("stage", ["prepare", "confirm", "use"])
def test_current_account_scope_is_required_at_every_confirmation_stage(boundary, stage):
    gate, upload, state = boundary
    if stage == "prepare":
        state["active"] = False
        assert not prepare(gate, upload)["allowed"]
        assert not gate._content_import_confirmations
        return
    pending = prepare(gate, upload)
    if stage == "use":
        assert confirm(gate, upload, pending["confirmation_id"]).allowed
    state["active"] = False
    assert not confirm(gate, upload, pending["confirmation_id"]).allowed
    assert not check(gate, upload).allowed


@pytest.mark.parametrize("kind", ["flag", "environment"])
def test_testing_bypass_never_creates_or_confirms_import_authority(boundary, monkeypatch, kind):
    gate, upload, _ = boundary
    pending = prepare(gate, upload)
    if kind == "flag":
        p.set_testing_bypass(True)
    else:
        monkeypatch.setenv("PERMISSION_GATE_TESTING", "1")
    assert not prepare(gate, upload)["allowed"]
    assert not confirm(gate, upload, pending["confirmation_id"]).allowed
    assert not gate._approvals


def test_confirmation_capacity_is_bounded_and_expiry_recovers_capacity(boundary, monkeypatch):
    gate, upload, _ = boundary
    monkeypatch.setattr(p, "_CONTENT_SOURCE_CONFIRMATION_CAPACITY", 1)
    pending = prepare(gate, upload)
    full = prepare(gate, upload)
    assert not full["allowed"] and full["code"] == "CONTENT_SOURCE_CONFIRMATION_CAPACITY"
    assert len(gate._content_import_confirmations) == 1
    gate._content_import_confirmations[pending["confirmation_id"]].expires_at = (
        datetime.now() - timedelta(seconds=1)
    )
    recovered = prepare(gate, upload)
    assert recovered["allowed"]
    assert recovered["confirmation_id"] != pending["confirmation_id"]
    assert len(gate._content_import_confirmations) == 1


def test_pruning_expired_import_grant_cannot_promote_it_to_general_write_approval(boundary):
    gate, upload, _ = boundary
    pending = prepare(gate, upload)
    assert confirm(gate, upload, pending["confirmation_id"]).allowed
    receipt = check(gate, upload)
    token = receipt.approval_token
    assert gate._approval_token_is_valid(token, "db_write", receipt.resource)
    gate._content_import_grants[token].expires_at = datetime.now() - timedelta(seconds=1)

    gate._prune_content_source_import_state()

    other_caller = gate.check(
        p.OperationType.DB_WRITE, resource=receipt.resource, caller="actor:2",
        domain_id=upload.domain_id, exact_approval_required=True,
    )
    assert not other_caller.allowed
    assert not gate._approval_token_is_valid(token, "db_write", receipt.resource)
    assert not check(gate, upload).allowed
