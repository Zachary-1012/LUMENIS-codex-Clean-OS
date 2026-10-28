import base64
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE_FLAG = "--internal-beta-workspace-context-acceptance"
PROFILE_HOST = "127.0.0.1"
PROFILE_PORT = "51236"


def _isolated_env(tmp_path, *, outside_db=False):
    data_dir = tmp_path / "fresh-runtime-data"
    db_path = (tmp_path / "outside.sqlite") if outside_db else (data_dir / "acceptance.sqlite")
    env = os.environ.copy()
    env["ZBC_DATA_DIR"] = str(data_dir)
    env["ZBC_DB_PATH"] = str(db_path)
    env["ZBC_WSGI"] = ""
    env["ZBC_GUARDIAN_ENABLED"] = "1"
    env["ZBC_PREFLIGHT_ENFORCE"] = "1"
    env["TAIKOO_AUTH_USER"] = "inherited-auth-user-sentinel"
    env["TAIKOO_AUTH_PASSWORD"] = "inherited-auth-password-sentinel"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Scoped Evidence writes require the production HMAC contract.  The
    # workspace profile is disposable, so provide a deterministic test-only
    # key ring instead of inheriting a developer/production credential.
    env["LUMENIS_EVIDENCE_HMAC_KEY_RING"] = json.dumps(
        {"workspace-acceptance-test": "disposable-workspace-acceptance-key"}
    )
    env["LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID"] = "workspace-acceptance-test"
    env.pop("LUMENIS_TEST_SEED_DB", None)
    env.pop("LUMENIS_WORKSPACE_BUILD_DIR", None)
    env.pop("LUMENIS_FLUTTER_WEB_BUILD_DIR", None)
    return env, data_dir, db_path


def _run_python(code, tmp_path, *, args, outside_db=False, existing_data=False):
    env, data_dir, db_path = _isolated_env(tmp_path, outside_db=outside_db)
    if existing_data:
        data_dir.mkdir()
    prefix = (
        "import sys\n"
        f"sys.argv = ['app.py', *{args!r}]\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", prefix + textwrap.dedent(code)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=120,
    )
    return result, data_dir, db_path


@pytest.mark.parametrize("target", [
    "app.tool",
    "app.tool.test_build_windows.WindowsPortableBundleTests.test_example",
])
def test_unittest_app_tool_target_rejected_before_product_imports(target, monkeypatch):
    source_path = REPO_ROOT / "app.py"
    source = source_path.read_text(encoding="utf-8-sig")
    guard_call = "_reject_unittest_app_tool_package_collision(__name__, sys.argv[1:])"
    guard_position = source.index(guard_call)
    prefix_end = source.index("_CORE_SERVER_KIND = 'not_started'")
    prefix = source[:prefix_end]

    for later_import in ("def _load_dotenv", "import database as db", "from flask import Flask"):
        assert guard_position < source.index(later_import)

    monkeypatch.setattr(sys, "argv", ["python", target])
    with pytest.raises(ImportError, match="python app/tool/test_build_windows.py"):
        exec(compile(prefix, str(source_path), "exec"), {
            "__name__": "app",
            "__file__": str(source_path),
        })

    # Ordinary Core imports used by product tests keep passing this early gate.
    monkeypatch.setattr(sys, "argv", ["pytest", "tests/test_api_smoke.py"])
    exec(compile(prefix, str(source_path), "exec"), {
        "__name__": "app",
        "__file__": str(source_path),
    })


@pytest.mark.parametrize(
    ("args", "outside_db", "expected"),
    [
        ([PROFILE_FLAG, "--host", "0.0.0.0", "--port", PROFILE_PORT], False, "requires --host 127.0.0.1"),
        ([PROFILE_FLAG, "--host", PROFILE_HOST, "--port", "8200"], False, "reserved"),
        ([PROFILE_FLAG, "--host=127.0.0.1", "--port", PROFILE_PORT], False, "separate explicit arguments"),
        ([PROFILE_FLAG, "--host", PROFILE_HOST, "--port", PROFILE_PORT, "--debug"], False, "unsupported flag"),
        ([PROFILE_FLAG, "--host", PROFILE_HOST], False, "explicit --host and --port"),
        ([PROFILE_FLAG, "--host", PROFILE_HOST, "--port", PROFILE_PORT], True, "under ZBC_DATA_DIR"),
        ([PROFILE_FLAG, PROFILE_FLAG, "--host", PROFILE_HOST, "--port", PROFILE_PORT], False, "exactly once"),
        ([PROFILE_FLAG + "=true", "--host", PROFILE_HOST, "--port", PROFILE_PORT], False, "standalone flag"),
        ([PROFILE_FLAG, "--host", PROFILE_HOST, "--port", PROFILE_PORT], False, "new, unused"),
        ([PROFILE_FLAG, "--internal-beta-acceptance", "--host", PROFILE_HOST, "--port", PROFILE_PORT], False, "cannot be combined"),
    ],
)
def test_workspace_profile_rejects_unsafe_host_port_path_and_flags_before_app_import(
    tmp_path, args, outside_db, expected
):
    result, data_dir, _ = _run_python(
        """
        try:
            import app
        except SystemExit as exc:
            print("PROFILE_REJECTED", exc)
            assert "flask" not in sys.modules
        else:
            raise SystemExit("PROFILE_UNEXPECTEDLY_IMPORTED")
        """,
        tmp_path,
        args=args,
        outside_db=outside_db,
        existing_data=(expected == "new, unused"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PROFILE_REJECTED" in result.stdout
    assert expected in result.stdout
    assert "PROFILE_UNEXPECTEDLY_IMPORTED" not in result.stdout
    if expected == "new, unused":
        assert data_dir.is_dir()
        assert list(data_dir.iterdir()) == []
    else:
        assert not data_dir.exists()


def test_workspace_context_evidence_allowlist_and_startup_fences(tmp_path):
    result, data_dir, db_path = _run_python(
        r"""
        import base64
        import importlib
        import os
        import sys
        import types
        from pathlib import Path
        from types import SimpleNamespace

        import app as core

        assert core.INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE is True
        assert core.INTERNAL_BETA_ACCEPTANCE is False
        assert core.INTERNAL_BETA_SAFE_STARTUP is True
        assert os.environ["XHS_COOKIE_HEADER"] == ""
        assert os.environ["XHS_COOKIES_JSON"] == ""
        assert os.environ["XHS_CDP_URL"] == ""
        assert os.environ["XHS_PRODUCTION"] == "0"
        assert os.environ["ZB_WSGI"] == ""
        assert os.environ["ZBC_PREFLIGHT_ENFORCE"] == "0"
        assert os.environ["ZBC_GUARDIAN_ENABLED"] == "0"
        assert os.environ["TAIKOO_AUTH_USER"].startswith("lumenis-acceptance-")
        assert os.environ["TAIKOO_AUTH_USER"] != "inherited-auth-user-sentinel"
        assert os.environ["TAIKOO_AUTH_PASSWORD"] != "inherited-auth-password-sentinel"
        assert "LUMENIS_WORKSPACE_BUILD_DIR" not in os.environ
        assert "LUMENIS_FLUTTER_WEB_BUILD_DIR" not in os.environ

        hooks = [hook.__name__ for hook in core.app.before_request_funcs.get(None, [])]
        assert hooks.index("_internal_beta_health_only_request_fence") == 0
        assert hooks.index("_internal_beta_workspace_context_request_fence") == 1
        assert hooks.index("_basic_auth") > hooks.index("_internal_beta_workspace_context_request_fence")
        assert hooks.index("_permission_gate_write_check") > hooks.index("_internal_beta_workspace_context_request_fence")

        calls = []
        def forbidden(name):
            def fail(*_args, **_kwargs):
                calls.append(name)
                raise AssertionError(name + " must stay suppressed")
            return fail

        original_thread = core.threading.Thread
        try:
            class ForbiddenThread:
                def __init__(self, *_args, **_kwargs):
                    calls.append("thread")
                    raise AssertionError("thread startup must stay suppressed")
            core.threading.Thread = ForbiddenThread
            core._ensure_node_on_path = forbidden("node")
            core.scheduler_loop = forbidden("scheduler")
            core.xhs_p0_orchestrator.start_resident = forbidden("xhs_resident")
            core.memory_optimizer.get_memory_optimizer = forbidden("memory_monitor")
            core.stability_monitor.get_stability_monitor = forbidden("stability_monitor")
            core.runtime_preflight.run_preflight = forbidden("preflight")
            ai_channel = importlib.import_module("lumenis.system.ai_gateway.channel")
            ai_channel.start_health_monitor = forbidden("ai_heartbeat")
            cdp_stub = types.ModuleType("cdp_helper")
            cdp_stub.get_cdp_status = forbidden("cdp_probe")
            sys.modules["cdp_helper"] = cdp_stub
            auto_recovery_stub = types.ModuleType("auto_recovery")
            auto_recovery_stub.recovery_engine = SimpleNamespace(
                start_background_monitor=forbidden("auto_recovery"),
                _p17_started=False,
            )
            sys.modules["auto_recovery"] = auto_recovery_stub
            system_guardian_stub = types.ModuleType("system_guardian")
            system_guardian_stub.health_check = forbidden("system_guardian")
            sys.modules["system_guardian"] = system_guardian_stub
            runtime_guardian_stub = types.ModuleType("runtime_guardian")
            runtime_guardian_stub.get_guardian = forbidden("runtime_guardian")
            sys.modules["runtime_guardian"] = runtime_guardian_stub
            args = SimpleNamespace(
                no_scheduler=False,
                internal_beta_acceptance=False,
                internal_beta_workspace_context_acceptance=False,
            )
            assert core._prepare_node_runtime(True) is False
            assert core._start_app_automations(args) is False
            assert core._start_optional_runtime_services(False) is False
            assert calls == []
        finally:
            core.threading.Thread = original_thread

        # Exercise the canonical Workspace host against a disposable test artifact.
        web_root = Path(os.environ["ZBC_DATA_DIR"]) / "workspace-fixture"
        web_root.mkdir(parents=True)
        (web_root / "index.html").write_text("<!doctype html><title>Workspace fixture</title>", encoding="utf-8")
        (web_root / "main.dart.js").write_text("/* disposable workspace asset */", encoding="utf-8")
        workspace_view = core.app.view_functions["lumenis_workspace_host.root"]
        workspace_host = workspace_view.__self__
        workspace_host.build_dir = web_root

        client = core.app.test_client()
        auth_config = client.get("/api/auth/config")
        assert auth_config.status_code == 200
        auth_payload = auth_config.get_json()
        assert auth_payload == {"ok": True, "auth_enabled": True}
        assert auth_config.headers["Cache-Control"] == "no-store"
        # Only the disposable in-process profile supplies synthetic test
        # credentials; the anonymous metadata endpoint never exposes them.
        auth_user, auth_password = core.AUTH_USER, core.AUTH_PASSWORD
        assert auth_user.startswith("lumenis-acceptance-")
        assert auth_user != "inherited-auth-user-sentinel"
        assert auth_password != "inherited-auth-password-sentinel"
        test_header = base64.b64encode(f"{auth_user}:{auth_password}".encode()).decode("ascii")
        workspace_headers = {"Authorization": "Basic " + test_header}
        response = client.get("/workspace", headers=workspace_headers)
        assert response.status_code == 200, response.get_data(as_text=True)
        assert "Workspace fixture" in response.get_data(as_text=True)
        asset = client.get("/main.dart.js", headers=workspace_headers)
        assert asset.status_code == 200
        assert "disposable workspace asset" in asset.get_data(as_text=True)

        from lumenis.auth import service as auth_service
        import subject_registry
        permission = importlib.import_module("lumenis.system.security.permission")
        from lumenis.shared.evidence.store import record_evidence

        actor = {"id": 71, "role": "owner"}
        auth_service.get_current_user = lambda: None
        scope_headers = {
            "X-Lumenis-Context-Mode": "FOCUS",
            "X-Domain-Id": "CTH",
            "X-Subject-ID": "SUBJ-CTH-A",
        }
        rejected_auth = client.get("/api/settings/context", headers=scope_headers)
        assert rejected_auth.status_code == 401
        assert rejected_auth.get_json()["code"] == "AUTH_REQUIRED"

        auth_service.get_current_user = lambda: actor
        subject_registry.get_subject_by_id = lambda domain, subject_id: {
            "subject_type": "company" if str(domain).upper() == "CTH" else "brand",
            "brand_focus_id": "FOCUS-BRAND-A" if str(domain).upper() != "CTH" else None,
        }
        permission_calls = []
        def allow_exact_scope(actor_arg, **scope):
            permission_calls.append((actor_arg, scope))
            return SimpleNamespace(verification_state="verified", allowed=True, reason="test grant")
        permission.check_actor_scope_permission = allow_exact_scope

        authorized_headers = {
            **scope_headers,
            "Authorization": "Basic " + test_header,
        }
        context = client.get("/api/settings/context", headers=authorized_headers)
        assert context.status_code == 200, context.get_data(as_text=True)
        assert context.get_json()["context"]["subject_id"] == "SUBJ-CTH-A"
        assert permission_calls[-1][1] == {
            "domain_id": "CTH",
            "action": "read",
            "module": "subject_registry",
            "subject_id": "SUBJ-CTH-A",
            "brand_focus_id": None,
        }

        evidence_id = record_evidence(
            source="isolated-runtime-acceptance",
            project="LUMENIS",
            product="CTH",
            feature_id="RUNTIME_CONTEXT_ACCEPTANCE",
            env="test",
            level="L4",
            test_name="scoped evidence route",
            result="PASS",
            inputs={"purpose": "temporary route acceptance"},
            actual="disposable scoped evidence record",
            domain_id="cth",
            subject_id="SUBJ-CTH-A",
        )
        evidence = client.get("/api/evidence/list", headers=authorized_headers)
        assert evidence.status_code == 200, evidence.get_data(as_text=True)
        evidence_payload = evidence.get_json()
        assert evidence_payload["count"] == 1
        assert evidence_payload["records"][0]["id"] == evidence_id
        assert evidence_payload["scope"]["evidence_scope"] == "EXACT_SUBJECT_OR_BRAND_FOCUS_EVIDENCE"
        assert permission_calls[-1][1] == {
            "domain_id": "CTH",
            "action": "read",
            "module": "evidence",
            "subject_id": "SUBJ-CTH-A",
            "brand_focus_id": None,
            "global_scope": False,
        }
        stats = client.get("/api/evidence/stats", headers=authorized_headers)
        assert stats.status_code == 200
        detail = client.get(f"/api/evidence/{evidence_id}", headers=authorized_headers)
        assert detail.status_code == 200
        assert detail.get_json()["record"]["id"] == evidence_id

        def deny_exact_scope(actor_arg, **scope):
            permission_calls.append((actor_arg, scope))
            return SimpleNamespace(verification_state="verified", allowed=False, reason="denied")
        permission.check_actor_scope_permission = deny_exact_scope
        denied_evidence = client.get("/api/evidence/list", headers=authorized_headers)
        assert denied_evidence.status_code == 403
        assert denied_evidence.get_json()["code"] == "EVIDENCE_SCOPE_DENIED"

        # A permitted actor in a different exact scope cannot discover the seeded record.
        permission.check_actor_scope_permission = allow_exact_scope
        other_scope_headers = {
            **authorized_headers,
            "X-Subject-ID": "SUBJ-CTH-B",
        }
        hidden_detail = client.get(f"/api/evidence/{evidence_id}", headers=other_scope_headers)
        assert hidden_detail.status_code == 404
        assert hidden_detail.get_json()["code"] == "EVIDENCE_NOT_FOUND"

        prohibited = [
            client.get("/api/xhs/p0/status"),
            client.post("/api/xhs/p0/collection", json={}),
            client.post("/api/experience/ai/intent", json={"task": "read"}),
            client.post("/api/evidence/replay-failed", json={}),
            client.post("/api/evidence/replay-failed/approval", json={}),
            client.get("/api/app_evidence/list"),
            client.get("/api/experience/content/evidence/CGE-test"),
            client.get("/api/experience/subjects"),
            client.get("/api/content/evidence"),
            client.post("/api/content/generate", json={}),
            client.post("/api/collect"),
            client.get("/api/not-reviewed"),
            client.put("/api/settings/context", json={}),
            client.delete("/api/settings/context"),
        ]
        assert all(response.status_code == 403 for response in prohibited), [
            (response.status_code, response.get_json(silent=True)) for response in prohibited
        ]
        assert all(
            response.get_json()["code"] == "INTERNAL_BETA_WORKSPACE_CONTEXT_ONLY"
            for response in prohibited
        )

        print("WORKSPACE_CONTEXT_EVIDENCE_PROFILE_PASS")
        """,
        tmp_path,
        args=[PROFILE_FLAG, "--host", PROFILE_HOST, "--port", PROFILE_PORT],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WORKSPACE_CONTEXT_EVIDENCE_PROFILE_PASS" in result.stdout
    assert data_dir.exists()
    assert db_path.exists()
    assert data_dir in db_path.parents


def test_existing_health_only_profile_still_allows_only_health(tmp_path):
    result, data_dir, db_path = _run_python(
        """
        from types import SimpleNamespace
        import app as core

        assert core.INTERNAL_BETA_ACCEPTANCE is True
        assert core.INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE is False
        client = core.app.test_client()
        health = client.get("/healthz")
        assert health.status_code != 403, health.get_data(as_text=True)
        assert health.get_json(silent=True) is None or health.get_json().get("code") != "INTERNAL_BETA_HEALTH_ONLY"
        for response in (
            client.get("/workspace"),
            client.get("/api/settings/context"),
            client.get("/api/evidence/list"),
            client.get("/api/xhs/p0/status"),
        ):
            assert response.status_code == 403
            assert response.get_json()["code"] == "INTERNAL_BETA_HEALTH_ONLY"

        args = SimpleNamespace(
            no_scheduler=False,
            internal_beta_acceptance=False,
            internal_beta_workspace_context_acceptance=False,
        )
        assert core._start_app_automations(args) is False
        print("HEALTH_ONLY_REGRESSION_PASS")
        """,
        tmp_path,
        args=["--internal-beta-acceptance", "--host", PROFILE_HOST],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "HEALTH_ONLY_REGRESSION_PASS" in result.stdout
    assert data_dir.exists()
    assert db_path.exists()
    assert data_dir in db_path.parents
