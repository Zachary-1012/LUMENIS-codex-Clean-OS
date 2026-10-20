"""Isolated regressions for truthful Runtime and security diagnostics.

These tests compile only the target Flask handlers from source. Importing
``app.py`` would run application database migrations and startup setup, so this
file deliberately does not import the application entrypoint.
"""

from __future__ import annotations

import ast
import base64
import json
import secrets
import subprocess
import sys
import types
import urllib.parse
from datetime import datetime
from pathlib import Path

import pytest
from flask import Flask, jsonify, request

_ROOT = Path(__file__).resolve().parents[1]
_APP_SOURCE = _ROOT / "app.py"
_AGG_SOURCE = _ROOT / "lumenis_agg_api.py"


def _load_function(source_path: Path, function_name: str, **extra_globals):
    """Compile one function without importing its module or running decorators."""
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    function_node = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    function_node.decorator_list = []
    module = ast.Module(body=[function_node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {
        "datetime": datetime,
        "json": json,
        "jsonify": jsonify,
        "request": request,
        "Path": Path,
        **extra_globals,
    }
    exec(compile(module, str(source_path), "exec"), namespace)  # noqa: S102 - importing app.py runs DB startup
    return namespace[function_name], namespace


def _client_for(source_path: Path, function_name: str, route: str, **extra_globals):
    flask_app = Flask(f"isolated_{function_name}")
    function, _ = _load_function(
        source_path, function_name, app=flask_app, **extra_globals
    )
    flask_app.add_url_rule(route, view_func=function)
    return flask_app.test_client(), flask_app


@pytest.mark.parametrize(
    ("function_name", "route"),
    [
        ("api_viz_overview_stats", "/api/viz/overview.stats"),
        ("api_viz_risk_active", "/api/viz/risk.active"),
        ("api_viz_overview_trend", "/api/viz/overview.trend"),
    ],
)
def test_visualization_database_errors_keep_500_and_use_flask_logger(
    function_name: str, route: str, caplog: pytest.LogCaptureFixture
) -> None:
    def unavailable_db():
        raise RuntimeError("isolated database unavailable")

    client, flask_app = _client_for(
        _APP_SOURCE, function_name, route, get_db=unavailable_db
    )

    with caplog.at_level("WARNING", logger=flask_app.logger.name):
        response = client.get(route)

    assert response.status_code == 500
    assert response.get_json()["success"] is False
    assert any("error" in record.getMessage() for record in caplog.records)


def test_malformed_system_config_uses_flask_logger_and_keeps_defaults(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    config_path = tmp_path / "system_config.json"
    config_path.write_text("{malformed", encoding="utf-8")
    flask_app = Flask("isolated_config")
    load_config, _ = _load_function(
        _APP_SOURCE,
        "_load_config",
        app=flask_app,
        CONFIG_FILE=config_path,
    )

    with caplog.at_level("WARNING", logger=flask_app.logger.name):
        result = load_config()

    assert result == {
        "company_domain": "",
        "company_name": None,
        "push_emails": [],
        "cdp_url": None,
        "auto_interval": 90,
        "daily_push_hour": 9,
    }
    assert any("Failed to load system config" in record.getMessage() for record in caplog.records)


def test_security_scan_without_quick_callable_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scanner = types.ModuleType("security_scanner")
    monkeypatch.setitem(sys.modules, "security_scanner", scanner)
    client, _ = _client_for(
        _APP_SOURCE, "api_security_scan", "/api/security/scan"
    )

    response = client.get("/api/security/scan")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["status"] == "UNAVAILABLE"
    assert payload["code"] == "QUICK_SECURITY_SCAN_UNAVAILABLE"
    assert "data" not in payload
    assert "users" not in payload
    assert "roles" not in payload
    assert "audit_today" not in payload


def test_security_scan_preserves_existing_quick_scan_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scanner = types.ModuleType("security_scanner")
    scanner.quick_scan = lambda: {"status": "complete", "findings": 2}
    monkeypatch.setitem(sys.modules, "security_scanner", scanner)
    client, _ = _client_for(
        _APP_SOURCE, "api_security_scan", "/api/security/scan"
    )

    response = client.get("/api/security/scan")

    assert response.status_code == 200
    assert response.get_json() == {
        "ok": True,
        "data": {"status": "complete", "findings": 2},
        "source": "security_scanner",
    }


def test_security_scan_exception_is_an_error_without_synthetic_counts(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    scanner = types.ModuleType("security_scanner")

    def fail_scan(*, quick_mode: bool):
        assert quick_mode is True
        raise RuntimeError("isolated scanner failure")

    scanner.run_scan = fail_scan
    monkeypatch.setitem(sys.modules, "security_scanner", scanner)
    client, flask_app = _client_for(
        _APP_SOURCE, "api_security_scan", "/api/security/scan"
    )

    with caplog.at_level("ERROR", logger=flask_app.logger.name):
        response = client.get("/api/security/scan")

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["status"] == "ERROR"
    assert payload["code"] == "QUICK_SECURITY_SCAN_FAILED"
    assert not {"users", "roles", "audit_today", "domain_isolation"} & payload.keys()
    assert any("security scan failed" in record.getMessage() for record in caplog.records)


class _FakeDLQ:
    def stats(self):
        return {"total": 2, "pending": 2}


class _FakeGuardian:
    def __init__(self, workers: list[dict], health: dict):
        self._workers = workers
        self._health = health
        self.dlq = _FakeDLQ()

    def list_lifecycle_workers(self):
        return self._workers

    def health_check(self):
        return self._health


def _runtime_client(
    monkeypatch: pytest.MonkeyPatch,
    guardian: _FakeGuardian,
    *,
    default_guardian: _FakeGuardian | None = None,
    requested_names: list[str] | None = None,
):
    runtime_guardian = types.ModuleType("runtime_guardian")
    guardians = {"app_main": guardian}
    if default_guardian is not None:
        guardians["default"] = default_guardian

    def get_guardian(name: str):
        if requested_names is not None:
            requested_names.append(name)
        return guardians[name]

    runtime_guardian.get_guardian = get_guardian
    monkeypatch.setitem(sys.modules, "runtime_guardian", runtime_guardian)
    return _client_for(
        _AGG_SOURCE,
        "system_runtime",
        "/api/system/runtime",
        platform=types.SimpleNamespace(
            python_version=lambda: "test-python",
            system=lambda: "test-os",
            machine=lambda: "test-machine",
        ),
        _ZBC_ROOT=_ROOT,
        _osai_root=lambda: None,
        _db_path=lambda: None,
        _db_readonly=lambda: None,
    )[0]


def test_system_runtime_uses_worker_observations_across_all_domains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guardian = _FakeGuardian(
        workers=[
            {
                "worker_id": "cth-1",
                "worker_name": "collector",
                "domain_id": "cth",
                "status": "running",
                "lease_owner": "worker-a",
                "last_heartbeat_at": "2026-10-16 10:00:00",
                "last_checkpoint_at": "2026-10-16 10:00:01",
                "failure_count": 3,
                "retry_count": 4,
                "recovery_reason": "internal-only detail",
                "created_at": "2026-10-15 10:00:00",
            },
            {
                "worker_id": "system-1",
                "domain_id": "system",
                "status": "paused",
                "lease_owner": "",
                "last_heartbeat_at": "",
                "last_checkpoint_at": "",
            },
            {
                "worker_id": "zbmp-1",
                "domain_id": "zbmp",
                "status": "dead",
                "lease_owner": "",
                "last_heartbeat_at": "",
                "last_checkpoint_at": "",
            },
        ],
        health={"overall": "degraded", "reaper_running": False},
    )
    client = _runtime_client(monkeypatch, guardian)

    response = client.get("/api/system/runtime")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["state"] == "READY"
    assert payload["guardian_health"] == "degraded"
    assert payload["guardian_status"] == {
        "lease_manager": "OBSERVED",
        "heartbeat_monitor": "OBSERVED",
        "reaper": "STOPPED",
        "checkpoint": "OBSERVED",
    }
    assert payload["runtime_by_domain"]["cth"]["running"] == 1
    assert payload["runtime_by_domain"]["cth"]["failed"] == 0
    cth_worker = payload["runtime_by_domain"]["cth"]["workers"][0]
    assert set(cth_worker) == {
        "worker_id", "worker_name", "status", "last_heartbeat_at"
    }
    assert cth_worker["worker_id"] == "cth-1"
    assert cth_worker["worker_name"] == "collector"
    assert cth_worker["status"] == "running"
    assert cth_worker["last_heartbeat_at"] == "2026-10-16 10:00:00"
    assert payload["runtime_by_domain"]["system"]["running"] == 0
    assert payload["runtime_by_domain"]["system"]["paused"] == 1
    assert payload["runtime_by_domain"]["zbmp"]["failed"] == 1
    assert all(
        payload["runtime_by_domain"][domain_id]["dlq_count"] is None
        for domain_id in ("cth", "zbmp", "system")
    )
    assert payload["dlq"] == {"total": 2, "pending": 2}
    assert payload["guardian"]["reaper"]["last_run"] is None


def test_system_runtime_reads_app_main_guardian_not_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_main_guardian = _FakeGuardian(
        workers=[
            {
                "worker_id": "app-main-worker",
                "domain_id": "system",
                "status": "running",
            }
        ],
        health={"overall": "app-main-health", "reaper_running": True},
    )
    default_guardian = _FakeGuardian(
        workers=[
            {
                "worker_id": "default-only-worker",
                "domain_id": "system",
                "status": "failed",
            }
        ],
        health={"overall": "default-health", "reaper_running": False},
    )
    requested_names: list[str] = []
    client = _runtime_client(
        monkeypatch,
        app_main_guardian,
        default_guardian=default_guardian,
        requested_names=requested_names,
    )

    response = client.get("/api/system/runtime")

    assert response.status_code == 200
    assert requested_names == ["app_main"]
    payload = response.get_json()
    assert payload["guardian_health"] == "app-main-health"
    assert payload["guardian_status"]["reaper"] == "ACTIVE"
    workers = payload["runtime_by_domain"]["system"]["workers"]
    assert [worker["worker_id"] for worker in workers] == ["app-main-worker"]
    assert all(
        "default-only-worker" != worker["worker_id"] for worker in workers
    )


def test_system_runtime_keeps_unobserved_component_states_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guardian = _FakeGuardian(workers=[], health={"overall": "healthy"})
    client = _runtime_client(monkeypatch, guardian)

    response = client.get("/api/system/runtime")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["runtime_by_domain"]["cth"]["total_workers"] == 0
    assert payload["guardian_status"] == {
        "lease_manager": "UNKNOWN",
        "heartbeat_monitor": "UNKNOWN",
        "reaper": "UNKNOWN",
        "checkpoint": "UNKNOWN",
    }
    assert payload["guardian"]["heartbeat"]["status"] == "UNKNOWN"
    assert payload["guardian"]["checkpoint"]["status"] == "UNKNOWN"
    assert payload["guardian"]["reaper"]["last_run"] is None


def test_system_runtime_reports_unavailable_owner_without_zero_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnavailableGuardian(_FakeGuardian):
        def list_lifecycle_workers(self):
            raise RuntimeError("isolated guardian failure")

    client = _runtime_client(
        monkeypatch, UnavailableGuardian(workers=[], health={},)
    )

    response = client.get("/api/system/runtime")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["state"] == "UNAVAILABLE"
    assert payload["guardian_health"] == "UNKNOWN"
    for domain in payload["runtime_by_domain"].values():
        assert domain["total_workers"] is None
        assert domain["running"] is None
        assert domain["failed"] is None
        assert domain["paused"] is None
        assert domain["workers"] is None
        assert domain["dlq_count"] is None


def test_app_system_runtime_compatibility_handler_delegates_to_agg_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = {"ok": True, "state": "READY", "runtime_by_domain": {}}
    agg_api = types.ModuleType("lumenis_agg_api")
    agg_api.system_runtime = lambda: jsonify(expected)
    monkeypatch.setitem(sys.modules, "lumenis_agg_api", agg_api)
    client, _ = _client_for(
        _APP_SOURCE, "api_system_runtime", "/api/system/runtime"
    )

    response = client.get("/api/system/runtime")

    assert response.status_code == 200
    assert response.get_json() == expected


def _auth_client():
    flask_app = Flask("isolated_runtime_basic_auth")
    basic_auth, _ = _load_function(
        _APP_SOURCE,
        "_basic_auth",
        app=flask_app,
        _owner_authorized_root_request=lambda: False,
        _is_cth_readonly_get=lambda path, method: False,
        _auth_enabled=lambda: True,
        secrets=secrets,
        AUTH_USER="isolated-runtime-user",
        AUTH_PASSWORD="isolated-runtime-password",
    )
    flask_app.before_request(basic_auth)

    @flask_app.get("/api/system/runtime")
    def runtime_route():
        return jsonify({"ok": True, "source": "isolated-runtime-handler"})

    @flask_app.get("/api/system/status")
    def public_status_route():
        return jsonify({"ok": True, "source": "existing-public-status"})

    return flask_app.test_client()


def test_system_runtime_requires_basic_auth_and_keeps_other_public_route() -> None:
    client = _auth_client()

    denied = client.get("/api/system/runtime")

    assert denied.status_code == 401
    assert denied.get_json()["auth_required"] is True

    credential = base64.b64encode(
        b"isolated-runtime-user:isolated-runtime-password"
    ).decode("ascii")
    allowed = client.get(
        "/api/system/runtime",
        headers={"Authorization": f"Basic {credential}"},
    )
    assert allowed.status_code == 200
    assert allowed.get_json() == {
        "ok": True,
        "source": "isolated-runtime-handler",
    }

    existing_public_route = client.get("/api/system/status")
    assert existing_public_route.status_code == 200
    assert existing_public_route.get_json() == {
        "ok": True,
        "source": "existing-public-status",
    }


def _new_local_git_repo(repo_path: Path) -> None:
    """Create a committed local fixture without contacting any remote."""
    subprocess.run(["git", "init", "--quiet"], cwd=repo_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Isolated Test",
            "-c",
            "user.email=isolated-test@example.invalid",
            "commit",
            "--no-gpg-sign",
            "--quiet",
            "--allow-empty",
            "-m",
            "fixture",
        ],
        cwd=repo_path,
        check=True,
    )


def _git_info(subprocess_module=subprocess):
    function, _ = _load_function(
        _AGG_SOURCE,
        "_git_info",
        subprocess=subprocess_module,
        urllib=urllib,
    )
    return function


def test_git_info_distinguishes_real_clean_output_from_git_failure(tmp_path: Path) -> None:
    repo_path = tmp_path / "clean-repository"
    repo_path.mkdir()
    _new_local_git_repo(repo_path)

    clean_result = _git_info()(repo_path)

    assert clean_result["available"] is True
    assert clean_result["status"] == "READY"
    assert clean_result["clean"] is True
    assert clean_result["dirty_files"] == 0
    assert clean_result["head_sha"] != "UNKNOWN"
    assert clean_result["branch"] != "UNKNOWN"

    class FailingStatusSubprocess:
        @staticmethod
        def run(args, **kwargs):
            if args == ["git", "status", "--porcelain"]:
                return subprocess.CompletedProcess(
                    args, 128, stdout="", stderr="isolated-git-error-marker"
                )
            return subprocess.run(args, **kwargs)

    failed_result = _git_info(FailingStatusSubprocess)(repo_path)

    assert failed_result["available"] is False
    assert failed_result["status"] == "ERROR"
    assert failed_result["clean"] is None
    assert failed_result["dirty_files"] is None
    assert failed_result["failed_commands"] == ["worktree_status"]
    assert "isolated-git-error-marker" not in json.dumps(failed_result)


def test_git_info_preserves_observed_worktree_when_head_is_unavailable(tmp_path: Path) -> None:
    repo_path = tmp_path / "unborn-repository"
    repo_path.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo_path, check=True)
    (repo_path / "untracked.txt").write_text("synthetic", encoding="utf-8")

    result = _git_info()(repo_path)

    assert result["available"] is False
    assert result["status"] == "ERROR"
    assert result["head_sha"] == "UNKNOWN"
    assert result["clean"] is False
    assert result["dirty_files"] == 1
    assert "head_sha" in result["failed_commands"]


def test_git_info_redacts_credentials_from_remote_url(tmp_path: Path) -> None:
    repo_path = tmp_path / "remote-fixture"
    repo_path.mkdir()
    _new_local_git_repo(repo_path)
    subprocess.run(
        [
            "git",
            "remote",
            "add",
            "origin",
            "https://fixture-user:fixture-password@github.com/example/repo.git"
            "?access_token=query-secret&key=key-secret&signature=signature-secret"
            "&code=code-secret&ref=main#fragment-secret",
        ],
        cwd=repo_path,
        check=True,
    )

    result = _git_info()(repo_path)

    assert result["available"] is True
    assert result["clean"] is True
    assert result["remote"] == "https://github.com/example/repo.git"
    assert not any(
        secret in result["remote"]
        for secret in (
            "fixture-user",
            "fixture-password",
            "query-secret",
            "key-secret",
            "signature-secret",
            "code-secret",
            "fragment-secret",
        )
    )


def test_git_info_sanitizes_nested_remote_helper_address_and_fails_closed(
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "remote-helper-fixture"
    repo_path.mkdir()
    _new_local_git_repo(repo_path)
    subprocess.run(
        [
            "git", "remote", "add", "origin",
            "foo::https://fixture-user:fixture-password@github.com/example/repo.git"
            "?token=query-secret&key=key-secret#fragment-secret",
        ],
        cwd=repo_path,
        check=True,
    )

    result = _git_info()(repo_path)

    assert result["available"] is True
    assert result["remote"] == "foo::https://github.com/example/repo.git"
    assert not any(
        secret in json.dumps(result)
        for secret in (
            "fixture-user", "fixture-password", "query-secret", "key-secret",
            "fragment-secret",
        )
    )

    subprocess.run(
        ["git", "remote", "set-url", "origin", "custom::opaque-helper-secret"],
        cwd=repo_path,
        check=True,
    )
    opaque_result = _git_info()(repo_path)

    assert opaque_result["available"] is False
    assert opaque_result["status"] == "ERROR"
    assert opaque_result["remote"] == "UNKNOWN"
    assert "opaque-helper-secret" not in json.dumps(opaque_result)


def test_git_info_preserves_local_remote_path_with_at_sign(tmp_path: Path) -> None:
    repo_path = tmp_path / "local-path-remote-fixture"
    repo_path.mkdir()
    _new_local_git_repo(repo_path)
    local_remote = "/srv/git/team@archive/repo.git"
    subprocess.run(
        ["git", "remote", "add", "origin", local_remote], cwd=repo_path, check=True
    )

    result = _git_info()(repo_path)

    assert result["remote"] == local_remote
    assert result["available"] is True


def test_git_info_remote_sanitization_failure_is_incomplete(tmp_path: Path) -> None:
    repo_path = tmp_path / "invalid-remote-fixture"
    repo_path.mkdir()
    _new_local_git_repo(repo_path)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://[invalid"],
        cwd=repo_path,
        check=True,
    )

    result = _git_info()(repo_path)

    assert result["available"] is False
    assert result["status"] == "ERROR"
    assert result["remote"] == "UNKNOWN"
    assert result["failed_commands"] == ["remote_sanitize"]
    assert result["clean"] is True
    assert result["dirty_files"] == 0


def test_git_fixture_commit_ignores_inherited_gpg_sign_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    global_config = tmp_path / "gitconfig"
    global_config.write_text("[commit]\n\tgpgsign = true\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    repo_path = tmp_path / "signing-fixture"
    repo_path.mkdir()

    _new_local_git_repo(repo_path)

    assert subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"], cwd=repo_path,
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def test_git_info_redacts_scp_style_remote_username(tmp_path: Path) -> None:
    repo_path = tmp_path / "scp-remote-fixture"
    repo_path.mkdir()
    _new_local_git_repo(repo_path)
    subprocess.run(
        ["git", "remote", "add", "origin", "fixture-secret@github.com:org/repo.git"],
        cwd=repo_path,
        check=True,
    )

    result = _git_info()(repo_path)

    assert result["remote"] == "github.com:org/repo.git"
    assert "fixture-secret" not in result["remote"]


def _remote_result(tmp_path: Path, name: str, url: str) -> dict:
    repo_path = tmp_path / name
    repo_path.mkdir()
    _new_local_git_repo(repo_path)
    subprocess.run(["git", "remote", "add", "origin", url], cwd=repo_path, check=True)
    return _git_info()(repo_path)


def test_git_info_fails_closed_for_opaque_scheme_remote_with_credentials(tmp_path: Path) -> None:
    result = _remote_result(tmp_path, "opaque", "https:fixture-user:fixture-secret@host/repo")
    assert result["available"] is False
    assert result["remote"] == "UNKNOWN"
    assert "fixture-secret" not in json.dumps(result)


def test_git_info_sanitizes_network_path_remotes(tmp_path: Path) -> None:
    result = _remote_result(tmp_path, "netpath", "//fixture-user:fixture-secret@host/repo")
    assert result["remote"] == "//host/repo"
    assert "fixture-secret" not in json.dumps(result)
    helper = _remote_result(tmp_path, "netpath-helper", "foo:://fixture-user:fixture-secret@host/repo")
    assert "fixture-secret" not in json.dumps(helper)


def test_git_info_accepts_dotted_and_plus_helper_transports(tmp_path: Path) -> None:
    result = _remote_result(tmp_path, "dotted", "foo.bar+x::https://u:fixture-secret@host/repo")
    assert result["available"] is True
    assert result["remote"] == "foo.bar+x::https://host/repo"
