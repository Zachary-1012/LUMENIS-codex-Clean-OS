"""No-GPU remote training preflight contracts."""

from pathlib import Path

from flask import Flask
import pytest

import experience_runtime as runtime
from lumenis.system.ai_gateway import owned_training_ssh as ssh
from lumenis.system.security import permission as permission
from tests.test_owned_training_phase_http_v2 import _actual_app_guards


_PINS = {
    "lumenis/system/ai_gateway/owned_training.py": "a" * 64,
    "lumenis/system/ai_gateway/owned_training_runtime.py": "b" * 64,
}


def _endpoint(tmp_path: Path) -> ssh.SSHTrainingEndpoint:
    executable = tmp_path / "ssh.exe"
    identity = tmp_path / "training-id"
    known_hosts = tmp_path / "known_hosts"
    for path in (executable, identity, known_hosts):
        path.write_bytes(b"fixture")
    return ssh.SSHTrainingEndpoint(
        ssh_executable=executable.resolve(),
        host="training.example.test",
        port=22,
        user="trainer",
        identity_file=identity.resolve(),
        known_hosts=known_hosts.resolve(),
        remote_python="/usr/bin/python3",
        source_root="/srv/lumenis",
        source_pins=dict(_PINS),
    )


def test_remote_preflight_verifies_only_the_source_pin_contract(tmp_path, monkeypatch):
    transport = ssh.AuthenticatedSSHTrainingTransport(_endpoint(tmp_path))
    observed = {}

    def query(code, body, timeout):
        observed.update(code=code, body=body, timeout=timeout)
        return {
            "state": "REMOTE_TRAINING_PREFLIGHT_OK",
            "source_pins": dict(_PINS),
        }

    monkeypatch.setattr(transport, "_query", query)

    assert transport.preflight_source() == {
        "state": "REMOTE_TRAINING_PREFLIGHT_SOURCE_PINS_VERIFIED",
        "source_pins_verified": True,
    }
    assert observed["body"] == {
        "source_root": "/srv/lumenis",
        "source_pins": _PINS,
    }
    assert observed["timeout"] == 20
    assert "REMOTE_TRAINING_PREFLIGHT_OK" in observed["code"]
    assert transport._channel is None
    assert transport._peer is None


def test_remote_preflight_rejects_a_malformed_or_changed_observation(tmp_path, monkeypatch):
    transport = ssh.AuthenticatedSSHTrainingTransport(_endpoint(tmp_path))
    monkeypatch.setattr(
        transport,
        "_query",
        lambda *_args, **_kwargs: {"state": "REMOTE_TRAINING_PREFLIGHT_OK", "source_pins": {}},
    )

    with pytest.raises(ssh.RemoteTrainingError, match="REMOTE_TRAINING_PREFLIGHT_INVALID"):
        transport.preflight_source()
    assert transport._channel is None
    assert transport._peer is None


def _install_route_fixtures(monkeypatch, *, remote_result, fresh_error=None):
    endpoint = object()
    calls = {"fresh": 0, "transport": 0, "preflight": 0}

    def fresh():
        calls["fresh"] += 1
        if fresh_error is not None:
            raise fresh_error

    monkeypatch.setattr(runtime, "_owned_training_phase_body", lambda: {"fixture": True})
    monkeypatch.setattr(
        runtime,
        "_owned_training_phase_material",
        lambda body: (None, None, None, "cth", None, None, None, fresh),
    )
    monkeypatch.setattr(
        runtime,
        "_owned_training_parent_profile",
        lambda body, domain: (
            Path("C:/lumenis"),
            {
                "worker_source_pins": dict(_PINS),
                "private_endpoint_configuration_reference": "private-reference",
            },
            {},
        ),
    )
    monkeypatch.setattr(
        runtime,
        "_owned_training_parent_endpoint",
        lambda pins, reference: endpoint,
    )

    class FakeTransport:
        def __init__(self, supplied_endpoint):
            assert supplied_endpoint is endpoint
            calls["transport"] += 1

        def preflight_source(self):
            calls["preflight"] += 1
            return remote_result

    monkeypatch.setattr(ssh, "AuthenticatedSSHTrainingTransport", FakeTransport)
    return calls


def test_execution_preflight_never_starts_training_or_a_model(monkeypatch):
    calls = _install_route_fixtures(
        monkeypatch,
        remote_result={
            "state": "REMOTE_TRAINING_PREFLIGHT_SOURCE_PINS_VERIFIED",
            "source_pins_verified": True,
        },
    )
    app = Flask(__name__)

    with app.test_request_context("/", method="POST"):
        response = runtime.preflight_owned_training_execution()

    assert response.status_code == 200
    assert response.get_json() == {
        "ok": True,
        "state": "REMOTE_TRAINING_PREFLIGHT_BOUND",
        "configuration_revision": "owned-parent-remote-preflight-1",
        "endpoint_present": True,
        "exact_source_pins": True,
        "remote_source_pins_verified": True,
        "training_started": False,
        "model_loaded": False,
        "optimizer_steps": 0,
    }
    assert calls == {"fresh": 2, "transport": 1, "preflight": 1}


def test_app_permission_guard_routes_preflight_to_the_existing_sealed_owner(monkeypatch):
    calls = _install_route_fixtures(
        monkeypatch,
        remote_result={
            "state": "REMOTE_TRAINING_PREFLIGHT_SOURCE_PINS_VERIFIED",
            "source_pins_verified": True,
        },
    )
    gate = permission.PermissionGate(enabled_permissions={permission.PermissionLevel.COMMIT})
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    app.register_blueprint(runtime.experience_bp)
    _actual_app_guards(app, gate)

    response = app.test_client().post(
        "/api/experience/owned-training/execution-preflight",
        json={"training_request": {}, "scope_descriptors": {}},
        headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )

    assert response.status_code == 200
    assert response.get_json()["state"] == "REMOTE_TRAINING_PREFLIGHT_BOUND"
    assert calls == {"fresh": 2, "transport": 1, "preflight": 1}


def test_execution_preflight_fails_closed_before_remote_access_without_exact_approval(monkeypatch):
    calls = _install_route_fixtures(
        monkeypatch,
        remote_result={
            "state": "REMOTE_TRAINING_PREFLIGHT_SOURCE_PINS_VERIFIED",
            "source_pins_verified": True,
        },
        fresh_error=PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REQUIRED"),
    )
    app = Flask(__name__)

    with app.test_request_context("/", method="POST"):
        response, status = runtime.preflight_owned_training_execution()

    assert status == 403
    assert response.get_json() == {
        "ok": False,
        "code": "OWNED_TRAINING_PHASE_APPROVAL_REQUIRED",
        "training_started": False,
    }
    assert calls == {"fresh": 1, "transport": 0, "preflight": 0}


def test_execution_preflight_rejects_a_remote_result_without_training(monkeypatch):
    calls = _install_route_fixtures(
        monkeypatch,
        remote_result={"state": "wrong", "source_pins_verified": False},
    )
    app = Flask(__name__)

    with app.test_request_context("/", method="POST"):
        response, status = runtime.preflight_owned_training_execution()

    assert status == 409
    assert response.get_json() == {
        "ok": False,
        "code": "REMOTE_TRAINING_PREFLIGHT_INVALID",
        "training_started": False,
    }
    assert calls == {"fresh": 1, "transport": 1, "preflight": 1}
