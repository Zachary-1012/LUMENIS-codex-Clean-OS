"""Compatibility endpoints for the withdrawn GPU training route."""
import builtins
import sqlite3
import subprocess
import threading

import pytest

import ai_task_engine
import experience_runtime as runtime
from lumenis.shared.database import repository
from tests.test_owned_training_phase_http_v2 import (
    BASE_HEADERS, _db_snapshot, phase_http, strict_permission_mode,
)

pytestmark = pytest.mark.usefixtures("strict_permission_mode")


def test_withdrawn_execution_routes_return_410_without_effects(phase_http, monkeypatch):
    case = phase_http
    before = _db_snapshot(case["db"])
    forbidden_calls = []

    def forbidden(name):
        def fail(*_args, **_kwargs):
            forbidden_calls.append(name)
            raise AssertionError(f"withdrawn endpoint attempted {name}")
        return fail

    blocked_imports = {
        "ai_task_engine", "lumenis.system.ai_gateway.owned_training_runtime",
        "lumenis.system.ai_gateway.owned_training_ssh", "requests", "shared_artifacts",
    }
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name in blocked_imports:
            forbidden_calls.append("import:" + name)
            raise AssertionError(f"withdrawn endpoint imported {name}")
        return original_import(name, *args, **kwargs)

    task_id = "trainrelay_00000000-0000-4000-8000-000000000001"
    paths = [
        ("/api/experience/owned-training/execution-approvals", {}),
        ("/api/experience/owned-training/phase-tasks", {}),
        ("/api/experience/owned-training/execution-preflight", {}),
        (f"/api/experience/owned-training/phase-tasks/{task_id}/execute", {}),
        (f"/api/experience/owned-training/phase-tasks/{task_id}/challenges", {}),
        (f"/api/experience/owned-training/phase-tasks/{task_id}/challenge-decisions", {}),
        (f"/api/experience/owned-training/phase-tasks/{task_id}/resume", {}),
    ]
    with monkeypatch.context() as effects:
        effects.setattr(builtins, "__import__", guarded_import)
        effects.setattr(ai_task_engine, "get_task_engine", forbidden("task-engine"))
        effects.setattr(repository, "get_repository", forbidden("database"))
        effects.setattr(sqlite3, "connect", forbidden("sqlite"))
        effects.setattr(subprocess, "Popen", forbidden("worker-process"))
        effects.setattr(threading.Thread, "start", forbidden("worker-thread"))
        effects.setattr(runtime, "_owned_training_phase_body", forbidden("phase-body"))
        effects.setattr(runtime, "_owned_training_phase_material", forbidden("permission-material"))
        for path, body in paths:
            response = case["client"].post(
                path, json=body, headers=BASE_HEADERS,
                environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
            )
            assert response.status_code == 410, (path, response.get_json())
            assert response.get_json() == {
                "ok": False,
                "state": "GPU_TRAINING_WITHDRAWN_BY_PO",
                "code": "GPU_TRAINING_WITHDRAWN_BY_PO",
                "training_started": False,
                "execution_available": False,
                "ai_status_url": "/api/ai/status",
            }

    assert forbidden_calls == []
    assert _db_snapshot(case["db"]) == before
