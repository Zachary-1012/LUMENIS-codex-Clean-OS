"""Retained transport contract plus the withdrawn HTTP preflight endpoint."""
import builtins
import sqlite3
import subprocess
import threading
from pathlib import Path

import pytest

import ai_task_engine
import experience_runtime as runtime
from lumenis.shared.database import repository
from lumenis.system.ai_gateway import owned_training_ssh as ssh
from tests.test_owned_training_phase_http_v2 import (
    BASE_HEADERS, _db_snapshot, phase_http, strict_permission_mode,
)

pytestmark = pytest.mark.usefixtures("strict_permission_mode")

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
        return {"state": "REMOTE_TRAINING_PREFLIGHT_OK", "source_pins": dict(_PINS)}

    monkeypatch.setattr(transport, "_query", query)
    assert transport.preflight_source() == {
        "state": "REMOTE_TRAINING_PREFLIGHT_SOURCE_PINS_VERIFIED",
        "source_pins_verified": True,
    }
    assert observed["body"] == {"source_root": "/srv/lumenis", "source_pins": _PINS}
    assert observed["timeout"] == 20
    assert "REMOTE_TRAINING_PREFLIGHT_OK" in observed["code"]
    assert transport._channel is None and transport._peer is None


def test_remote_preflight_rejects_a_malformed_or_changed_observation(tmp_path, monkeypatch):
    transport = ssh.AuthenticatedSSHTrainingTransport(_endpoint(tmp_path))
    monkeypatch.setattr(
        transport, "_query",
        lambda *_args, **_kwargs: {"state": "REMOTE_TRAINING_PREFLIGHT_OK", "source_pins": {}},
    )
    with pytest.raises(ssh.RemoteTrainingError, match="REMOTE_TRAINING_PREFLIGHT_INVALID"):
        transport.preflight_source()
    assert transport._channel is None and transport._peer is None


def test_http_preflight_is_withdrawn_before_database_ssh_or_worker_access(phase_http, monkeypatch):
    case = phase_http
    before = _db_snapshot(case["db"])
    attempted = []

    def forbidden(name):
        def fail(*_args, **_kwargs):
            attempted.append(name)
            raise AssertionError(f"withdrawn preflight attempted {name}")
        return fail

    blocked_imports = {
        "ai_task_engine", "lumenis.system.ai_gateway.owned_training_runtime",
        "lumenis.system.ai_gateway.owned_training_ssh", "subprocess",
    }
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name in blocked_imports:
            attempted.append("import:" + name)
            raise AssertionError(f"withdrawn preflight imported {name}")
        return original_import(name, *args, **kwargs)

    with monkeypatch.context() as effects:
        effects.setattr(builtins, "__import__", guarded_import)
        effects.setattr(runtime, "_owned_training_phase_body", forbidden("phase-body"))
        effects.setattr(runtime, "_owned_training_phase_material", forbidden("permission-material"))
        effects.setattr(runtime, "_owned_training_parent_profile", forbidden("parent-profile"), raising=False)
        effects.setattr(runtime, "_owned_training_parent_endpoint", forbidden("parent-endpoint"), raising=False)
        effects.setattr(ai_task_engine, "get_task_engine", forbidden("task-engine"))
        effects.setattr(repository, "get_repository", forbidden("database"))
        effects.setattr(sqlite3, "connect", forbidden("sqlite"))
        effects.setattr(ssh, "AuthenticatedSSHTrainingTransport", forbidden("ssh-transport"))
        effects.setattr(subprocess, "Popen", forbidden("worker-process"))
        effects.setattr(threading.Thread, "start", forbidden("worker-thread"))
        response = case["client"].post(
            "/api/experience/owned-training/execution-preflight", json={}, headers=BASE_HEADERS,
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
        )

    assert response.status_code == 410
    assert response.get_json() == {
        "ok": False,
        "state": "GPU_TRAINING_WITHDRAWN_BY_PO",
        "code": "GPU_TRAINING_WITHDRAWN_BY_PO",
        "training_started": False,
        "execution_available": False,
        "ai_status_url": "/api/ai/status",
    }
    assert attempted == []
    assert _db_snapshot(case["db"]) == before
