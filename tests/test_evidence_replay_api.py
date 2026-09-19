from flask import Flask
import pytest

from lumenis.shared.evidence import api as evidence_api
from lumenis.system.security import permission as permission_module
from lumenis.system.security import (
    OperationType,
    PermissionGate,
    PermissionLevel,
    RiskLevel,
)


ACTION = "evidence.replay_failed"
RESOURCE = "evidence.replay_failed:user:17:limit:12"
OWNER = {
    "id": 17,
    "username": "owner",
    "role": "owner",
    "display_name": "主账号",
    "token": "server-session-token",
}


@pytest.fixture(autouse=True)
def disable_permission_gate_test_bypass(monkeypatch):
    # Always exercise the real COMMIT/HIGH approval contract.
    monkeypatch.setattr(permission_module, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)


class RecordingPermissionGate(PermissionGate):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.check_calls = []
        self.grant_calls = []

    def check(self, *args, **kwargs):
        self.check_calls.append(kwargs.copy())
        return super().check(*args, **kwargs)

    def grant_approval(self, *args, **kwargs):
        self.grant_calls.append((args, kwargs.copy()))
        return super().grant_approval(*args, **kwargs)


def _client(monkeypatch, user, gate, replay):
    from lumenis.auth import service as auth_service
    from lumenis import system

    monkeypatch.setattr(auth_service, "get_current_user", lambda: user)
    monkeypatch.setattr(system.security, "get_permission_gate", lambda: gate)
    monkeypatch.setattr(evidence_api.evidence_store, "replay_failed_evidence", replay)

    app = Flask(__name__)
    evidence_api.register_evidence_api(app)
    return app.test_client()


def _confirmed(limit=12, action=ACTION):
    return {"action": action, "confirm": True, "limit": limit}


def _approved_gate():
    return RecordingPermissionGate(enabled_permissions={PermissionLevel.COMMIT})


@pytest.mark.parametrize(
    ("endpoint", "user", "expected_status"),
    [
        ("/api/evidence/replay-failed/approval", None, 401),
        ("/api/evidence/replay-failed", None, 401),
        ("/api/evidence/replay-failed/approval", {"id": 8, "role": "admin"}, 403),
        ("/api/evidence/replay-failed", {"id": 8, "role": "admin"}, 403),
    ],
)
def test_both_steps_require_authenticated_owner_before_any_side_effect(
    monkeypatch, endpoint, user, expected_status
):
    gate = _approved_gate()
    replay_calls = []
    client = _client(monkeypatch, user, gate, lambda **kwargs: replay_calls.append(kwargs))

    response = client.post(endpoint, json=_confirmed())

    assert response.status_code == expected_status
    assert gate.grant_calls == []
    assert gate.check_calls == []
    assert replay_calls == []
    assert gate._approvals == {}


@pytest.mark.parametrize(
    "payload",
    [
        {"action": ACTION, "limit": 12},  # confirm omitted
        {"action": ACTION, "confirm": False, "limit": 12},
        {"action": "runtime_operation", "confirm": True, "limit": 12},
        {"action": ACTION, "confirm": True, "limit": 201},
        {"action": ACTION, "confirm": True, "limit": 12, "actor": "owner"},
        {"action": ACTION, "confirm": True, "limit": 12, "user_id": 17},
        {"action": ACTION, "confirm": True, "limit": 12, "token": "forged"},
        {"action": ACTION, "confirm": True, "limit": 12, "resource": RESOURCE},
    ],
)
def test_approval_refuses_missing_or_noncanonical_confirmation_without_grant(
    monkeypatch, payload
):
    gate = _approved_gate()
    replay_calls = []
    client = _client(monkeypatch, OWNER, gate, lambda **kwargs: replay_calls.append(kwargs))

    response = client.post("/api/evidence/replay-failed/approval", json=payload)

    assert response.status_code == 400
    assert gate.grant_calls == []
    assert gate._approvals == {}
    assert replay_calls == []


@pytest.mark.parametrize(
    "payload",
    [
        {"action": ACTION, "limit": 12},
        {"action": ACTION, "confirm": False, "limit": 12},
        {"action": "other", "confirm": True, "limit": 12},
        {"action": ACTION, "confirm": True, "limit": 12, "actor": "owner"},
        {"action": ACTION, "confirm": True, "limit": 12, "approval_token": "forged"},
        {"action": ACTION, "confirm": True, "limit": 201},
    ],
)
def test_replay_refuses_missing_or_noncanonical_confirmation_without_execution(
    monkeypatch, payload
):
    gate = _approved_gate()
    replay_calls = []
    client = _client(monkeypatch, OWNER, gate, lambda **kwargs: replay_calls.append(kwargs))

    response = client.post("/api/evidence/replay-failed", json=payload)

    assert response.status_code == 400
    assert gate.check_calls == []
    assert replay_calls == []


def test_approval_stays_fail_closed_when_commit_is_disabled(monkeypatch):
    gate = RecordingPermissionGate()
    client = _client(monkeypatch, OWNER, gate, lambda **kwargs: pytest.fail("must not replay"))

    response = client.post("/api/evidence/replay-failed/approval", json=_confirmed())

    assert response.status_code == 403
    assert gate.grant_calls == []
    assert gate._approvals == {}


def test_owner_two_step_replay_uses_exact_scope_and_consumes_token(monkeypatch):
    gate = _approved_gate()
    replay_calls = []
    client = _client(
        monkeypatch,
        OWNER,
        gate,
        lambda **kwargs: replay_calls.append(kwargs) or {
            "replayed": kwargs["limit"],
            "succeeded": kwargs["limit"],
            "failed": 0,
            "remaining": 0,
        },
    )

    approval_response = client.post(
        "/api/evidence/replay-failed/approval", json=_confirmed(limit=12)
    )
    assert approval_response.status_code == 200
    assert approval_response.get_json() == {
        "ok": True,
        "action": ACTION,
        "limit": 12,
        "expires_in_seconds": 300,
    }
    assert "token" not in approval_response.get_json()
    assert gate.grant_calls == [((OperationType.RUNTIME_OPERATION.value,), {
        "duration_minutes": 5,
        "resource": RESOURCE,
        "granted_by": "evidence_replay_owner:17",
    })]
    assert gate.is_approved(OperationType.RUNTIME_OPERATION.value, RESOURCE)

    execution_response = client.post("/api/evidence/replay-failed", json=_confirmed(limit=12))
    assert execution_response.status_code == 200
    assert replay_calls == [{"limit": 12}]
    assert gate.check_calls[-1] == {
        "operation_type": OperationType.RUNTIME_OPERATION,
        "resource": RESOURCE,
        "risk_level": RiskLevel.HIGH,
        "caller": "evidence_replay:17",
        "domain_id": "system",
        "role": "system_operator",
        "exact_approval_required": True,
    }
    assert not gate.is_approved(OperationType.RUNTIME_OPERATION.value, RESOURCE)

    second_execution = client.post("/api/evidence/replay-failed", json=_confirmed(limit=12))
    assert second_execution.status_code == 403
    assert replay_calls == [{"limit": 12}]


def test_replay_rejects_mismatched_limit_and_action_without_consuming_other_scope(monkeypatch):
    gate = _approved_gate()
    replay_calls = []
    client = _client(monkeypatch, OWNER, gate, lambda **kwargs: replay_calls.append(kwargs))

    approval_response = client.post(
        "/api/evidence/replay-failed/approval", json=_confirmed(limit=12)
    )
    assert approval_response.status_code == 200

    wrong_limit = client.post("/api/evidence/replay-failed", json=_confirmed(limit=13))
    wrong_action = client.post(
        "/api/evidence/replay-failed", json=_confirmed(limit=12, action="runtime_operation")
    )

    assert wrong_limit.status_code == 403
    assert wrong_action.status_code == 400
    assert replay_calls == []
    assert len(gate.grant_calls) == 1
    assert gate.is_approved(OperationType.RUNTIME_OPERATION.value, RESOURCE)
    assert not gate.is_approved(
        OperationType.RUNTIME_OPERATION.value,
        "evidence.replay_failed:user:17:limit:13",
    )


def test_wildcard_or_broad_approval_does_not_authorize_replay(monkeypatch):
    gate = _approved_gate()
    gate.grant_approval(OperationType.RUNTIME_OPERATION.value, duration_minutes=5)
    replay_calls = []
    client = _client(monkeypatch, OWNER, gate, lambda **kwargs: replay_calls.append(kwargs))

    response = client.post("/api/evidence/replay-failed", json=_confirmed(limit=12))

    assert response.status_code == 403
    assert replay_calls == []
    assert gate.is_approved(OperationType.RUNTIME_OPERATION.value, None)


def test_failed_replay_consumes_confirmation_and_cannot_be_retried(monkeypatch):
    gate = _approved_gate()
    replay_calls = []

    def fail_replay(**kwargs):
        replay_calls.append(kwargs)
        raise RuntimeError("store unavailable")

    client = _client(monkeypatch, OWNER, gate, fail_replay)
    approval_response = client.post(
        "/api/evidence/replay-failed/approval", json=_confirmed(limit=12)
    )
    assert approval_response.status_code == 200

    failed_execution = client.post("/api/evidence/replay-failed", json=_confirmed(limit=12))
    retry_execution = client.post("/api/evidence/replay-failed", json=_confirmed(limit=12))

    assert failed_execution.status_code == 500
    assert retry_execution.status_code == 403
    assert replay_calls == [{"limit": 12}]
    assert not gate.is_approved(OperationType.RUNTIME_OPERATION.value, RESOURCE)


def test_store_error_returns_service_failure_and_consumes_confirmation(monkeypatch):
    gate = _approved_gate()
    client = _client(
        monkeypatch,
        OWNER,
        gate,
        lambda **_kwargs: {
            "replayed": 0,
            "succeeded": 0,
            "failed": 0,
            "remaining": 0,
            "error": "DLQ unavailable",
        },
    )
    approval = client.post("/api/evidence/replay-failed/approval", json=_confirmed())
    assert approval.status_code == 200

    response = client.post("/api/evidence/replay-failed", json=_confirmed())

    assert response.status_code == 503
    assert response.get_json()["ok"] is False
    assert response.get_json()["error"] == "DLQ unavailable"
    assert not gate.is_approved(OperationType.RUNTIME_OPERATION.value, RESOURCE)


def test_partial_replay_failure_returns_non_success_semantics(monkeypatch):
    gate = _approved_gate()
    client = _client(
        monkeypatch,
        OWNER,
        gate,
        lambda **_kwargs: {
            "replayed": 2,
            "succeeded": 1,
            "failed": 1,
            "remaining": 1,
        },
    )
    client.post("/api/evidence/replay-failed/approval", json=_confirmed())

    response = client.post("/api/evidence/replay-failed", json=_confirmed())

    assert response.status_code == 207
    assert response.get_json()["ok"] is False
    assert response.get_json()["failed"] == 1
