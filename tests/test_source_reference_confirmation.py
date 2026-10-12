"""Permission boundary regressions for explicit approved-source-reference confirmation."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from lumenis.importer import documents
from lumenis.shared.reporting import saved_work
from lumenis.system.security import permission as p

_SCOPE = {
    "domain_id": "cth",
    "subject_id": "subject-confirmation",
    "brand_focus_id": None,
    "global_scope": False,
}
_REQUEST = {
    "source_id": "approved-source-1",
    "canonical_id": "canonical-source-1",
    "expected_body_sha256": hashlib.sha256(b"approved source body").hexdigest(),
    "request_id": "source-reference-request-1",
}


@pytest.fixture(scope="module", autouse=True)
def _strict_permission_mode():
    previous = p._TESTING_BYPASS_ENABLED
    p.set_testing_bypass(False)
    yield
    p.set_testing_bypass(previous)


def _descriptor_sha256(descriptor):
    raw = json.dumps(
        descriptor, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _current_prepared(actor, scope, request, state):
    context = {
        **scope,
        "domain_id": "zbmp" if scope["domain_id"] in {"bmp", "zbmp"} else "cth",
        "actor_id": actor["id"],
    }
    descriptor = {
        "schema": "lumenis.approved-source-reference-request/v2",
        **request,
        "context": context,
        "source_url": state["source_url"],
        "scope_evidence_ref": "app_evidence_records:101",
        "source_content_locator": "app_evidence_records:102",
        "body_sha256": state["body_sha256"],
        "parsed_text": state["body"],
        "body_length": len(state["body"]),
        "offset_unit": "unicode-codepoint",
        "title": state["title"],
        "source_platform": "PUBLIC_WEB",
        "published_at": "UNKNOWN",
        "captured_at": "2026-10-11T00:00:00Z",
        "rights_state": "approved_internal_research",
        "snapshot_kind": "verified_source",
        "receipt_id": "source-use-receipt-1",
        "receipt_descriptor_sha256": state["receipt_sha256"],
        "source_use": {
            "purpose": "internal_research",
            "operation": "derive_reference",
            "commercial_state": "UNKNOWN",
            "publication_state": "NOT_APPROVED",
            "training_state": "NOT_APPROVED",
        },
    }
    descriptor_sha256 = _descriptor_sha256(descriptor)
    return {
        "ok": True,
        "prepared": True,
        **descriptor,
        "descriptor_sha256": descriptor_sha256,
        "resource": (
            "approved-internal-source-reference:v2:" + descriptor_sha256
        ),
    }


@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    p.set_testing_bypass(False)
    actor = {"id": 7}
    scope = dict(_SCOPE)
    state = {
        "body": "approved source body",
        "body_sha256": _REQUEST["expected_body_sha256"],
        "receipt_sha256": "b" * 64,
        "source_url": "https://sources.example.test/item/1",
        "title": "Approved source",
        "authorization_allowed": True,
        "prepare_calls": [],
        "transaction_calls": [],
        "authorize_calls": [],
    }
    gate = p.PermissionGate(
        enabled_permissions={p.PermissionLevel.COMMIT},
    )

    def authorize(current_actor, current_scope, *, action, connection=None):
        state["authorize_calls"].append((dict(current_scope), action, connection))
        if not state["authorization_allowed"]:
            raise ValueError("WORK_PERMISSION_DENIED")
        if not isinstance(current_actor, dict) or type(current_actor.get("id")) is not int:
            raise ValueError("WORK_PERMISSION_DENIED")
        domain_id = current_scope["domain_id"]
        context = {
            **current_scope,
            "domain_id": "zbmp" if domain_id in {"bmp", "zbmp"} else "cth",
            "actor_id": current_actor["id"],
        }
        return context

    def prepare(*, source_id, canonical_id, expected_body_sha256,
                request_id, actor, scope):
        state["prepare_calls"].append((actor["id"], dict(scope)))
        request = {
            "source_id": source_id,
            "canonical_id": canonical_id,
            "expected_body_sha256": expected_body_sha256,
            "request_id": request_id,
        }
        return _current_prepared(actor, scope, request, state)

    def prepare_in_transaction(connection, *, source_id, canonical_id,
                               expected_body_sha256, request_id, actor, scope,
                               action, source_use_operation):
        state["transaction_calls"].append(
            (connection, action, source_use_operation)
        )
        assert action == "write"
        assert source_use_operation == "derive_reference"
        authorize(actor, scope, action=action, connection=connection)
        request = {
            "source_id": source_id,
            "canonical_id": canonical_id,
            "expected_body_sha256": expected_body_sha256,
            "request_id": request_id,
        }
        return _current_prepared(actor, scope, request, state), {}, {}, {}, state["body"]

    monkeypatch.setattr(saved_work, "authorize", authorize)
    monkeypatch.setattr(documents, "prepare_approved_source_reference", prepare)
    monkeypatch.setattr(
        documents, "_prepare_approved_source_reference", prepare_in_transaction,
    )
    yield gate, actor, scope, state
    p.set_testing_bypass(False)


def _prepare(boundary):
    gate, actor, scope, _state = boundary
    return p.prepare_approved_source_reference_confirmation(
        actor=actor, scope=scope, request=_REQUEST, gate=gate,
    )


def _confirm(boundary, confirmation_id, *, confirmed=True, actor=None, scope=None):
    gate, default_actor, default_scope, _state = boundary
    return p.confirm_approved_source_reference_confirmation(
        actor=default_actor if actor is None else actor,
        scope=default_scope if scope is None else scope,
        confirmation_id=confirmation_id, confirmed=confirmed, gate=gate,
    )


def _check(boundary, prepared=None, *, actor=None, scope=None, connection=None):
    gate, default_actor, default_scope, state = boundary
    source = prepared or _current_prepared(
        default_actor, default_scope, _REQUEST, state,
    )
    return p.check_approved_source_reference_import(
        actor=default_actor if actor is None else actor,
        scope=default_scope if scope is None else scope,
        prepared=source, connection=connection, gate=gate,
    )


def test_confirmation_requires_explicit_action_and_keeps_private_state_inside_gate(boundary):
    gate, _actor, _scope, state = boundary
    pending = _prepare(boundary)
    assert pending["allowed"] is True
    assert pending["code"] == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_PENDING"
    assert pending["title"] == state["title"]
    assert pending["source_url"] == state["source_url"]
    assert pending["body_sha256"] == _REQUEST["expected_body_sha256"]
    assert set(pending["scope"]) == {
        "domain_id", "subject_id", "brand_focus_id", "global_scope",
    }
    assert "parsed_text" not in pending and "approval_token" not in pending
    assert not gate._approvals

    confirmation = gate._approved_source_reference_confirmations[
        pending["confirmation_id"]
    ]
    assert confirmation.request == _REQUEST
    assert "parsed_text" not in confirmation.__dict__
    assert "source_url" not in confirmation.__dict__
    assert not _check(boundary).allowed
    assert not gate._approved_source_reference_grants

    confirmed = _confirm(boundary, pending["confirmation_id"])
    assert confirmed["allowed"] is True
    assert confirmed["state"] == "ready_for_retry"
    assert confirmed["code"] == "APPROVED_SOURCE_REFERENCE_READY_FOR_RETRY"
    assert "approval_token" not in confirmed
    assert gate.has_permission(p.PermissionLevel.COMMIT)
    assert len(gate._approved_source_reference_grants) == 1

    # The response can be retried only after fresh owner checks; it never exposes
    # the Gate's approval token through PermissionResult or the generic token API.
    repeated = _confirm(boundary, pending["confirmation_id"])
    assert repeated["allowed"] is True
    assert repeated["state"] == "ready_for_retry"
    assert len(gate._approved_source_reference_grants) == 1
    assert gate.get_valid_approval_token(
        p.OperationType.DATA_IMPORT.value, pending["resource"], exact=True,
    ) is None
    assert not gate.check(
        p.OperationType.DATA_IMPORT, resource=pending["resource"],
        caller="actor:7", domain_id="cth", exact_approval_required=True,
    ).allowed
    assert _check(boundary).allowed
    assert _check(boundary).approval_token is None
    assert len(state["prepare_calls"]) >= 4


def test_declining_confirmation_cancels_only_that_nonce(boundary):
    gate, _actor, _scope, _state = boundary
    pending = _prepare(boundary)
    result = _confirm(boundary, pending["confirmation_id"], confirmed=False)
    assert result["allowed"] is False
    assert result["code"] == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_CANCELLED"
    assert pending["confirmation_id"] not in gate._approved_source_reference_confirmations
    assert not gate._approved_source_reference_grants
    assert not gate._approvals
    assert not _check(boundary).allowed


def test_commit_permission_is_never_bypassed_by_confirmation(boundary):
    gate, _actor, _scope, _state = boundary
    gate.revoke_permission(p.PermissionLevel.COMMIT)
    pending = _prepare(boundary)
    result = _confirm(boundary, pending["confirmation_id"])
    assert result["allowed"] is False
    assert result["code"] == "APPROVED_SOURCE_REFERENCE_COMMIT_PERMISSION_REQUIRED"
    assert not gate._approved_source_reference_grants
    assert not gate._approvals
    assert not _check(boundary).allowed


def test_expired_nonce_cannot_be_confirmed(boundary):
    gate, _actor, _scope, _state = boundary
    pending = _prepare(boundary)
    confirmation = gate._approved_source_reference_confirmations[
        pending["confirmation_id"]
    ]
    confirmation.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    result = _confirm(boundary, pending["confirmation_id"])
    assert result["allowed"] is False
    assert result["code"] == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_UNKNOWN"
    assert not gate._approved_source_reference_grants
    assert not gate._approvals


def test_current_scope_authorization_is_rechecked_before_confirmation(boundary):
    gate, _actor, _scope, state = boundary
    pending = _prepare(boundary)
    state["authorization_allowed"] = False
    result = _confirm(boundary, pending["confirmation_id"])
    assert result["allowed"] is False
    assert result["code"] == "WORK_PERMISSION_DENIED"
    assert not gate._approved_source_reference_grants
    assert not gate._approvals


@pytest.mark.parametrize("change", ["expiry", "revocation"])
def test_expired_or_revoked_grant_fails_the_next_effect_check(boundary, change):
    gate, _actor, _scope, _state = boundary
    pending = _prepare(boundary)
    assert _confirm(boundary, pending["confirmation_id"])["allowed"] is True
    token, grant = next(iter(gate._approved_source_reference_grants.items()))
    if change == "expiry":
        grant.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    else:
        assert gate.revoke_approval(token)
    assert not _check(boundary).allowed
    assert not gate._approved_source_reference_grants


@pytest.mark.parametrize("change", ["actor", "scope"])
def test_confirmation_cannot_be_reused_by_another_actor_or_focus(boundary, change):
    gate, actor, scope, _state = boundary
    pending = _prepare(boundary)
    if change == "actor":
        denied = _confirm(
            boundary, pending["confirmation_id"], actor={"id": 8},
        )
    else:
        changed_scope = {**scope, "subject_id": "subject-other"}
        denied = _confirm(
            boundary, pending["confirmation_id"], scope=changed_scope,
        )
    assert denied["allowed"] is False
    assert not gate._approved_source_reference_grants
    assert _confirm(boundary, pending["confirmation_id"], actor=actor)["allowed"]


@pytest.mark.parametrize("change", ["body", "receipt"])
def test_changed_body_or_source_use_receipt_invalidates_pending_confirmation(boundary, change):
    gate, _actor, _scope, state = boundary
    pending = _prepare(boundary)
    if change == "body":
        state["body"] = "changed source body"
        state["body_sha256"] = hashlib.sha256(state["body"].encode()).hexdigest()
    else:
        state["receipt_sha256"] = "c" * 64
    result = _confirm(boundary, pending["confirmation_id"])
    assert result["allowed"] is False
    assert not gate._approved_source_reference_grants
    assert not _check(boundary).allowed


@pytest.mark.parametrize("field", ["body_sha256", "receipt_descriptor_sha256"])
def test_caller_prepared_descriptor_must_equal_fresh_importer_result(boundary, field):
    _gate, _actor, _scope, state = boundary
    pending = _prepare(boundary)
    assert _confirm(boundary, pending["confirmation_id"])["allowed"] is True
    prepared = _current_prepared(_actor, _scope, _REQUEST, state)
    prepared[field] = "d" * 64
    decision = _check(boundary, prepared)
    assert not decision.allowed
    assert decision.approval_token is None


def test_generic_approval_cannot_authorize_source_reference_resource(boundary):
    gate, _actor, _scope, state = boundary
    prepared = _current_prepared(_actor, _scope, _REQUEST, state)
    gate.grant_approval(
        p.OperationType.DATA_IMPORT.value, duration_minutes=1,
        resource=prepared["resource"], granted_by="actor:7",
    )
    assert not gate.check(
        p.OperationType.DATA_IMPORT, resource=prepared["resource"],
        caller="actor:7", domain_id="cth", exact_approval_required=True,
    ).allowed
    assert not _check(boundary, prepared).allowed


def test_testing_bypass_cannot_prepare_confirm_or_check_source_reference(boundary):
    gate, _actor, _scope, state = boundary
    prepared = _current_prepared(_actor, _scope, _REQUEST, state)
    p.set_testing_bypass(True)
    pending = _prepare(boundary)
    assert pending["allowed"] is False
    assert pending["code"] == "APPROVED_SOURCE_REFERENCE_TESTING_BYPASS_FORBIDDEN"
    confirmed = _confirm(boundary, "unknown-confirmation")
    assert confirmed["allowed"] is False
    assert confirmed["code"] == "APPROVED_SOURCE_REFERENCE_TESTING_BYPASS_FORBIDDEN"
    assert not _check(boundary, prepared).allowed
    direct = gate.check(
        p.OperationType.DATA_IMPORT, resource=prepared["resource"],
        caller="actor:7", domain_id="cth", exact_approval_required=True,
    )
    assert not direct.allowed
    assert direct.reason == "APPROVED_SOURCE_REFERENCE_TESTING_BYPASS_FORBIDDEN"
    assert not gate._approved_source_reference_grants


def test_transactional_check_uses_current_write_derivation_contract(boundary):
    _gate, actor, scope, state = boundary
    pending = _prepare(boundary)
    assert _confirm(boundary, pending["confirmation_id"])["allowed"] is True
    prepared = _current_prepared(actor, scope, _REQUEST, state)
    connection = object()
    decision = _check(boundary, prepared, connection=connection)
    assert decision.allowed
    assert state["transaction_calls"] == [(connection, "write", "derive_reference")]
    assert state["authorize_calls"][-1] == (scope, "write", connection)
    assert decision.approval_token is None


def test_source_reference_confirmation_is_mandatory_without_high_risk_approval(boundary, monkeypatch):
    gate, _actor, _scope, _state = boundary
    monkeypatch.setattr(gate, "require_human_approval", lambda _risk: False)
    pending = _prepare(boundary)

    before_confirmation = gate.check(
        p.OperationType.DATA_IMPORT, resource=pending["resource"],
        caller="actor:7", domain_id="cth",
    )
    assert before_confirmation.allowed is False
    assert before_confirmation.reason == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_REQUIRED"

    confirmed = _confirm(boundary, pending["confirmation_id"])
    assert confirmed["allowed"] is True
    assert confirmed["state"] == "ready_for_retry"
    assert _check(boundary).allowed


def test_source_reference_uses_commit_floor_with_custom_verify_auto_allow_spec(
    boundary, monkeypatch,
):
    gate, _actor, _scope, _state = boundary
    monkeypatch.setattr(gate, "require_human_approval", lambda _risk: False)
    gate.register_operation(
        p.OperationType.DATA_IMPORT,
        p.OperationSpec(
            p.PermissionLevel.VERIFY, p.RiskLevel.LOW,
            "custom test spec", auto_allow=True,
        ),
    )
    pending = _prepare(boundary)
    before_confirmation = gate.check(
        p.OperationType.DATA_IMPORT, resource=pending["resource"],
        caller="actor:7", domain_id="cth",
    )
    assert before_confirmation.allowed is False
    assert before_confirmation.reason == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_REQUIRED"
    confirmed = _confirm(boundary, pending["confirmation_id"])

    assert confirmed["allowed"] is True
    assert _check(boundary).allowed
    token, _grant = next(iter(gate._approved_source_reference_grants.items()))
    decision = gate.check(
        p.OperationType.DATA_IMPORT, resource=pending["resource"],
        caller="actor:7", domain_id="cth", source_reference_grant=token,
    )
    assert decision.allowed is True
    assert decision.permission_required == p.PermissionLevel.COMMIT.value
    assert decision.risk_level == p.RiskLevel.HIGH.value


def test_revoking_commit_after_confirmation_denies_source_reference_import(boundary):
    gate, _actor, _scope, _state = boundary
    pending = _prepare(boundary)
    assert _confirm(boundary, pending["confirmation_id"])["allowed"] is True
    gate.revoke_permission(p.PermissionLevel.COMMIT)

    decision = _check(boundary)
    assert decision.allowed is False
    assert decision.permission_required == p.PermissionLevel.COMMIT.value
    assert p.PermissionLevel.COMMIT.value in decision.reason


def test_prior_allowed_operation_id_cannot_replay_source_reference_import(boundary):
    gate, _actor, _scope, _state = boundary
    pending = _prepare(boundary)
    operation_id = "source-reference-replay"
    gate._idempotency_cache[operation_id] = p.PermissionResult(
        allowed=True, reason="stale unrelated allow",
        operation_type=p.OperationType.DATA_IMPORT.value,
        resource=pending["resource"], risk_level=p.RiskLevel.HIGH.value,
        permission_required=p.PermissionLevel.COMMIT.value,
        caller="actor:7", operation_id=operation_id, idempotent_hit=True,
    )

    denied = gate.check(
        p.OperationType.DATA_IMPORT, resource=pending["resource"],
        caller="actor:7", domain_id="cth", operation_id=operation_id,
    )
    assert denied.allowed is False
    assert denied.reason == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_REQUIRED"
    assert denied.operation_id is None
    assert denied.idempotent_hit is False

    assert _confirm(boundary, pending["confirmation_id"])["allowed"] is True
    token, _grant = next(iter(gate._approved_source_reference_grants.items()))
    allowed = gate.check(
        p.OperationType.DATA_IMPORT, resource=pending["resource"],
        caller="actor:7", domain_id="cth", operation_id=operation_id,
        source_reference_grant=token,
    )
    assert allowed.allowed is True
    assert allowed.idempotent_hit is False
    assert allowed.operation_id is None


def test_foreign_caller_cannot_borrow_source_reference_grant(boundary):
    gate, _actor, _scope, _state = boundary
    pending = _prepare(boundary)
    assert _confirm(boundary, pending["confirmation_id"])["allowed"] is True
    token, _grant = next(iter(gate._approved_source_reference_grants.items()))

    decision = gate.check(
        p.OperationType.DATA_IMPORT, resource=pending["resource"],
        caller="actor:8", domain_id="cth", source_reference_grant=token,
    )
    assert decision.allowed is False
    assert decision.reason == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_REQUIRED"


def test_private_source_reference_token_cannot_be_borrowed_as_generic_grant(boundary):
    gate, _actor, _scope, _state = boundary
    pending = _prepare(boundary)
    assert _confirm(boundary, pending["confirmation_id"])["allowed"] is True
    token, _grant = next(iter(gate._approved_source_reference_grants.items()))

    decision = gate.check(
        p.OperationType.DATA_IMPORT, resource=pending["resource"],
        caller="actor:7", domain_id="cth", content_import_grant=token,
    )
    assert decision.allowed is False
    assert decision.reason == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_REQUIRED"
    assert gate.get_valid_approval_token(
        p.OperationType.DATA_IMPORT.value, pending["resource"], exact=True,
    ) is None
