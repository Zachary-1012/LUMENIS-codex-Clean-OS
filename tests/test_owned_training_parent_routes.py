"""The legacy execution configuration route reports withdrawal only."""
from pathlib import Path

import pytest

import experience_runtime as runtime
from tests.test_owned_training_phase_http_v2 import (
    BASE_HEADERS, phase_http, strict_permission_mode,
)

pytestmark = pytest.mark.usefixtures("strict_permission_mode")


def test_execution_configuration_reports_withdrawal_without_reading_private_config(
        phase_http, tmp_path, monkeypatch):
    case = phase_http
    spec_path = tmp_path / "must-not-read-parent-config.json"
    endpoint_path = tmp_path / "must-not-probe-ssh-endpoint.json"
    monkeypatch.setenv("LUMENIS_TRAINING_PARENT_SPEC_PATH", str(spec_path))
    monkeypatch.setenv("LUMENIS_TRAINING_SSH_ENDPOINT_PATH", str(endpoint_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "must-not-probe-appdata"))
    touched = []

    def guard_path_method(original, method_name):
        def guarded(path, *args, **kwargs):
            if path in {spec_path, endpoint_path}:
                touched.append(method_name + ":" + str(path))
                raise AssertionError("withdrawn configuration endpoint probed private training config")
            return original(path, *args, **kwargs)
        return guarded

    with monkeypatch.context() as effects:
        for method_name in ("is_file", "is_symlink", "stat", "read_bytes"):
            original = getattr(Path, method_name)
            effects.setattr(Path, method_name, guard_path_method(original, method_name))
        effects.setattr(runtime, "_owned_training_phase_body",
                        lambda *_args, **_kwargs: pytest.fail("request body must not be parsed"))
        effects.setattr(runtime, "_owned_training_phase_material",
                        lambda *_args, **_kwargs: pytest.fail("Permission material must not be read"))
        response = case["client"].post(
            "/api/experience/owned-training/execution-configuration",
            data=b"{invalid", headers={**BASE_HEADERS, "Content-Type": "application/json"},
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
        )

    assert response.status_code == 200
    assert response.get_json() == {
        "ok": True,
        "state": "GPU_TRAINING_WITHDRAWN_BY_PO",
        "code": "GPU_TRAINING_WITHDRAWN_BY_PO",
        "training_started": False,
        "execution_available": False,
        "ai_status_url": "/api/ai/status",
    }
    assert touched == []
