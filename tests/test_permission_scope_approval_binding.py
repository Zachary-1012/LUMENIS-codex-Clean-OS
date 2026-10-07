"""Regression for the unique scoped approval candidate, not user E2E."""
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from lumenis.system.security import permission as p


@pytest.fixture
def receipts(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    previous = p._TESTING_BYPASS_ENABLED
    p.set_testing_bypass(False)
    monkeypatch.setattr(p, "_actor_has_scope_action", lambda *args: True)
    monkeypatch.setattr(p, "_load_actor_scope_role", lambda *args: "admin")
    monkeypatch.setattr(p, "_registered_resource_scope_exists", lambda *a, **k: True)
    gate = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})
    scope = p.check_actor_scope_permission(
        {"id": 1}, domain_id="bmp", action="write", module="content",
        brand_focus_id="brand-a", gate=gate,
    )
    token = gate.grant_approval("db_write", resource=scope.resource)
    approval = gate.check(
        p.OperationType.DB_WRITE, resource=scope.resource, caller=scope.caller,
        domain_id=scope.domain_id, exact_approval_required=True,
    )
    assert scope.allowed and approval.allowed
    yield gate, scope, approval, token
    p.set_testing_bypass(previous)


def test_exact_live_receipts_bind_without_changing_legacy_json(receipts):
    gate, scope, approval, token = receipts
    bound = p.bind_scope_permission_approval(scope, approval, gate=gate)
    assert type(bound) is p.ActorScopePermissionResult
    assert bound.allowed and bound.approval_token == token
    assert bound.scope_audit_id == scope.audit_id
    assert set(bound.to_dict()) == set(p.PermissionResult.__dataclass_fields__)
    assert bound.to_scope_dict()["actor_id"] == 1
    assert bound.to_scope_dict()["brand_focus_id"] == "brand-a"
    assert gate.get_audit_log(operation_type="resource_scope_approval")[-1]["result"] == "allowed"


def test_bmp_alias_uses_canonical_domain_for_real_receipt_binding(receipts):
    gate, scope, approval, _ = receipts  # receipt input is domain_id="bmp"

    assert scope.domain_id == "zbmp"
    assert approval.domain_id == scope.domain_id
    bound = p.bind_scope_permission_approval(scope, approval, gate=gate)
    assert bound.allowed
    assert bound.domain_id == "zbmp"


@pytest.mark.parametrize("change", [
    {"actor_id": 2}, {"brand_focus_id": "brand-b"}, {"subject_id": "other"},
    {"global_scope": True}, {"global_scope": 1}, {"domain_id": "cth"},
    {"scope_action": "read"}, {"audit_id": "invented", "scope_audit_id": "invented"},
    {"verification_state": "unavailable"}, {"allowed": False},
    {"caller": "actor:2"}, {"resource": "bmp:brand-b"},
])
def test_modified_scope_receipt_denied(receipts, change):
    gate, scope, approval, _ = receipts
    result = p.bind_scope_permission_approval(replace(scope, **change), approval, gate=gate)
    assert not result.allowed and result.approval_token is None


@pytest.mark.parametrize("change", [
    {"operation_type": "file_write"}, {"resource": "bmp:brand-b"},
    {"caller": "actor:2"}, {"domain_id": "cth"}, {"audit_id": "invented"},
    {"approval_token": "invented"}, {"requires_approval": False}, {"allowed": False},
])
def test_modified_approval_receipt_denied(receipts, change):
    gate, scope, approval, _ = receipts
    result = p.bind_scope_permission_approval(scope, replace(approval, **change), gate=gate)
    assert not result.allowed and result.approval_token is None


@pytest.mark.parametrize("mode", ["revoked", "expired", "wildcard_operation", "wildcard_resource"])
def test_live_token_state_not_old_check_result_controls_binding(receipts, mode):
    gate, scope, approval, token = receipts
    if mode == "revoked":
        gate.revoke_approval(token)
    elif mode == "expired":
        gate._approvals[token].expires_at = datetime.now() - timedelta(seconds=1)
    elif mode == "wildcard_operation":
        gate._approvals[token].operation = "*"
    else:
        gate._approvals[token].resource = None
    result = p.bind_scope_permission_approval(scope, approval, gate=gate)
    assert not result.allowed


def test_another_gate_cannot_bind_receipts(receipts):
    _, scope, approval, _ = receipts
    assert not p.bind_scope_permission_approval(scope, approval, gate=p.PermissionGate()).allowed


@pytest.mark.parametrize("audit_result", [None, "", 17])
def test_missing_binding_audit_fails_closed(receipts, monkeypatch, audit_result):
    gate, scope, approval, _ = receipts
    monkeypatch.setattr(gate, "_write_audit", lambda **kwargs: audit_result)
    result = p.bind_scope_permission_approval(scope, approval, gate=gate)
    assert not result.allowed and result.verification_state == "unavailable"


def test_bypass_is_not_scoped_approval(receipts):
    gate, scope, approval, _ = receipts
    p.set_testing_bypass(True)
    assert not p.bind_scope_permission_approval(scope, approval, gate=gate).allowed


@pytest.mark.parametrize("value", [None, {}, p.PermissionResult(True, "not a scope receipt")])
def test_untyped_scope_is_denied_without_crashing(receipts, value):
    gate, _, approval, _ = receipts
    assert not p.bind_scope_permission_approval(value, approval, gate=gate).allowed


def test_audit_read_failure_is_unavailable(receipts, monkeypatch):
    gate, scope, approval, _ = receipts
    def fail(**kwargs):
        raise RuntimeError("audit offline")
    monkeypatch.setattr(gate, "get_audit_log", fail)
    result = p.bind_scope_permission_approval(scope, approval, gate=gate)
    assert not result.allowed and result.verification_state == "unavailable"
