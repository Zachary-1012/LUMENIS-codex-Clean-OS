"""Exercise the registered root auth functions without starting product workers.

All credentials and session actors below are disposable test values. The AST
loader retains the actual Flask decorators and request boundary from app.py.
"""
import ast
from pathlib import Path
import secrets
import sys
from types import SimpleNamespace

import pytest
from flask import Flask, jsonify, request


@pytest.fixture
def root_boundary(monkeypatch):
    source = Path(__file__).resolve().parents[1] / "app.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    names = {"_auth_enabled", "_is_cth_readonly_get", "auth_config_api", "_basic_auth",
             "_owner_authorized_root_request", "api_weibo_cookies",
             "_weibo_session_metadata_actor"}
    selected = [node for node in tree.body if (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ) or (
        isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_CTH_READONLY_GET_PREFIXES"
            for target in node.targets
        )
    )]
    app = Flask("root-auth-boundary")
    app.config["TESTING"] = True
    state = {"actor": None, "writes": 0}
    monkeypatch.setitem(sys.modules, "lumenis.auth.service", SimpleNamespace(
        get_current_user=lambda **kwargs: state["actor"],
    ))
    namespace = {"app": app, "jsonify": jsonify, "request": request,
                 "secrets": secrets, "AUTH_USER": "boundary-test-user",
                 "AUTH_PASSWORD": "boundary-test-only-password"}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"), namespace)

    @app.get("/api/platform-health")
    def health():
        return jsonify(ok=True)

    @app.route("/api/private-test-operation", methods=["GET", "POST"])
    def operation():
        if request.method == "POST":
            state["writes"] += 1
        return jsonify(ok=True)

    return app.test_client(), state, namespace


@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.parametrize("remote_addr", ["127.0.0.1", "203.0.113.10"])
def test_auth_metadata_never_returns_credentials(root_boundary, enabled, remote_addr):
    client, _, namespace = root_boundary
    if not enabled:
        namespace["AUTH_PASSWORD"] = ""
    response = client.get("/api/auth/config", environ_overrides={"REMOTE_ADDR": remote_addr})
    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "auth_enabled": enabled}
    assert response.headers["Cache-Control"] == "no-store"
    assert "boundary-test-user" not in response.get_data(as_text=True)
    assert "boundary-test-only-password" not in response.get_data(as_text=True)


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("role", ["member", "owner"])
def test_session_is_not_blanket_root_route_authorization(root_boundary, method, role):
    client, state, _ = root_boundary
    state["actor"] = {"id": 1, "role": role}
    response = client.open("/api/private-test-operation", method=method,
                           headers={"Authorization": "Bearer boundary-test-token"})
    assert response.status_code == 401
    assert state["writes"] == 0


def test_existing_session_health_read_remains_operable(root_boundary):
    client, state, _ = root_boundary
    assert client.get("/api/platform-health").status_code == 401
    state["actor"] = {"id": 1, "role": "member"}
    assert client.get("/api/platform-health",
                      headers={"Authorization": "Bearer boundary-test-token"}).status_code == 200


def test_explicit_basic_auth_retains_normal_root_operation(root_boundary):
    import base64
    client, state, _ = root_boundary
    encoded = base64.b64encode(b"boundary-test-user:boundary-test-only-password").decode("ascii")
    response = client.post("/api/private-test-operation", headers={"Authorization": "Basic " + encoded})
    assert response.status_code == 200
    assert state["writes"] == 1


def test_auth_configuration_failure_does_not_echo_sensitive_exception(root_boundary):
    class UnavailableConfiguration:
        def __bool__(self):
            raise RuntimeError("sensitive-test-configuration-detail")
    client, _, namespace = root_boundary
    namespace["AUTH_PASSWORD"] = UnavailableConfiguration()
    response = client.get("/api/auth/config")
    assert response.status_code == 503
    assert response.get_json() == {"ok": False, "code": "AUTH_CONFIG_UNAVAILABLE"}
    assert response.headers["Cache-Control"] == "no-store"
    assert "sensitive-test-configuration-detail" not in response.get_data(as_text=True)


def _session_metadata_dependencies(monkeypatch, state, *, allowed):
    closed = []
    permission_calls = []
    metadata_reads = []
    connection = SimpleNamespace(close=lambda: closed.append(True))
    def check(actor, product, *, module, action, connection):
        permission_calls.append((actor, product, module, action))
        return allowed(len(permission_calls))
    monkeypatch.setitem(sys.modules, "lumenis.system.security.permission", SimpleNamespace(
        resolve_local_workspace_principal=lambda **kwargs: None,
    ))
    monkeypatch.setitem(sys.modules, "lumenis.shared.database", SimpleNamespace(
        get_repository=lambda: SimpleNamespace(connect=lambda **kwargs: connection),
    ))
    monkeypatch.setitem(sys.modules, "account.authorization", SimpleNamespace(
        check_dual_domain_permission=check,
    ))
    def metadata():
        metadata_reads.append(True)
        return {"state": "UNVERIFIED", "cookie_count": 0, "last_login": None,
                "saved_logged_in": True}
    monkeypatch.setitem(sys.modules, "weibo_login_manager", SimpleNamespace(
        WeiboLoginManager=SimpleNamespace(read_saved_session_metadata=metadata),
    ))
    return permission_calls, metadata_reads, closed


def test_cookie_state_requires_exact_system_read_permission(root_boundary, monkeypatch):
    client, state, _ = root_boundary
    state["actor"] = {"id": 7, "role": "member"}
    calls, reads, closed = _session_metadata_dependencies(monkeypatch, state, allowed=lambda _: False)
    response = client.get("/api/weibo/cookies", headers={"Authorization": "Bearer test-only-token"})
    assert response.status_code == 403
    assert response.get_json() == {"ok": False, "code": "SESSION_PERMISSION_DENIED"}
    assert calls == [(7, "SYSTEM", "collector", "read")]
    assert reads == [] and closed == [True]


def test_authorized_cookie_state_read_preserves_zero_and_rechecks_permission(root_boundary, monkeypatch):
    client, state, _ = root_boundary
    state["actor"] = {"id": 7, "role": "member"}
    calls, reads, closed = _session_metadata_dependencies(monkeypatch, state, allowed=lambda _: True)
    response = client.get("/api/weibo/cookies", headers={"Authorization": "Bearer test-only-token"})
    assert response.status_code == 200
    assert response.get_json()["cookie_count"] == 0
    assert response.get_json()["state"] == "UNVERIFIED"
    assert "cookie_string" not in response.get_json()
    assert response.headers["Cache-Control"] == "no-store"
    assert calls == [(7, "SYSTEM", "collector", "read")] * 2
    assert reads == [True] and closed == [True, True]


def test_cookie_state_final_revocation_does_not_return_metadata(root_boundary, monkeypatch):
    client, state, _ = root_boundary
    state["actor"] = {"id": 7, "role": "member"}
    calls, reads, _ = _session_metadata_dependencies(monkeypatch, state, allowed=lambda count: count == 1)
    response = client.get("/api/weibo/cookies", headers={"Authorization": "Bearer test-only-token"})
    assert response.status_code == 403
    assert "cookie_count" not in response.get_json()
    assert len(calls) == 2 and reads == [True]


def test_unauthenticated_cookie_state_does_not_read_local_material(root_boundary, monkeypatch):
    client, state, _ = root_boundary
    calls, reads, _ = _session_metadata_dependencies(monkeypatch, state, allowed=lambda _: True)
    response = client.get("/api/weibo/cookies")
    assert response.status_code == 401
    assert calls == [] and reads == []
