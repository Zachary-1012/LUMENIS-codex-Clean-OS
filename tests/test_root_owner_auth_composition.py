"""Root auth plus the existing scoped owner routes, without app.py startup."""
from __future__ import annotations

import ast
import base64
import copy
import hashlib
import importlib
import json
import re
import secrets
import sys
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from flask import Blueprint, Flask, jsonify, request

flask_request = request


_REPO_ROOT = Path(__file__).resolve().parents[1]
_ACTOR = {"id": 731, "role": "member"}


def _source_tree(relative_path: str):
    path = _REPO_ROOT / relative_path
    return path, ast.parse(path.read_text(encoding="utf-8"))


def _compile_functions(path: Path, tree: ast.Module, names: set[str], namespace: dict):
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            cloned = copy.deepcopy(node)
            cloned.decorator_list = []
            selected.append(cloned)
    assert {node.name for node in selected} == names
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def _route_spec(tree: ast.Module, function_name: str, owner_name: str):
    function = next(
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
    )
    for decorator in function.decorator_list:
        call = decorator if isinstance(decorator, ast.Call) else None
        target = call.func if call is not None else decorator
        if not isinstance(target, ast.Attribute) or not isinstance(target.value, ast.Name):
            continue
        if target.value.id != owner_name or target.attr not in {
            "route", "get", "post", "put", "delete", "patch", "head", "options",
        }:
            continue
        if call is None or not call.args:
            continue
        rule = ast.literal_eval(call.args[0])
        if target.attr == "route":
            methods_kw = next((kw.value for kw in call.keywords if kw.arg == "methods"), None)
            methods = set(ast.literal_eval(methods_kw)) if methods_kw is not None else {"GET"}
        else:
            methods = {target.attr.upper()}
        return rule, methods
    raise AssertionError(f"No {owner_name} route decorator for {function_name}")


def _register_ast_routes(blueprint: Blueprint, tree: ast.Module, namespace: dict,
                         function_names: tuple[str, ...], owner_name: str):
    registered = {}
    for name in function_names:
        rule, methods = _route_spec(tree, name, owner_name)
        blueprint.add_url_rule(rule, endpoint=name, view_func=namespace[name], methods=methods)
        registered[name] = (rule, methods)
    return registered


def _rule_contract(app: Flask, endpoint: str):
    matches = [rule for rule in app.url_map.iter_rules() if rule.endpoint == endpoint]
    assert len(matches) == 1
    rule = matches[0]
    return rule.rule, set(rule.methods) - {"HEAD", "OPTIONS"}


def _build_root_hooks(app: Flask):
    path, tree = _source_tree("app.py")
    namespace = {
        "request": flask_request,
        "jsonify": jsonify,
        "secrets": secrets,
        "re": re,
        "AUTH_USER": "root-auth-test-user",
        "AUTH_PASSWORD": "root-auth-test-password",
        "_auth_enabled": lambda: True,
    }
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_CTH_READONLY_GET_PREFIXES"
            for target in node.targets
        ):
            namespace["_CTH_READONLY_GET_PREFIXES"] = ast.literal_eval(node.value)
            break
    else:
        raise AssertionError("app.py no longer defines the CTH read-only GET set")
    _compile_functions(path, tree, {
        "_is_cth_readonly_get", "_owner_authorized_root_request", "_basic_auth",
    }, namespace)
    app.before_request(namespace["_basic_auth"])
    return namespace


@pytest.fixture
def auth_composition(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "saved-work.sqlite3"))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"root-owner-composition-test": "synthetic-test-only-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "root-owner-composition-test")

    from lumenis.shared.database import DatabaseRepository
    from lumenis.system.security import permission
    import canonical_data
    import shared_artifacts
    from lumenis.shared.evidence import store
    from lumenis.shared.reporting import saved_work

    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)
    repository = DatabaseRepository(str(tmp_path / "saved-work.sqlite3"))
    for module in (store, shared_artifacts, saved_work):
        monkeypatch.setattr(module, "get_repository", lambda: repository)
    shared_artifacts.ensure_artifact_table()
    store.init_evidence_store(str(tmp_path / "saved-work.sqlite3"))
    with repository.transaction() as connection:
        store.ensure_evidence_schema(connection)
    canonical_data.ensure_canonical_table(str(tmp_path / "saved-work.sqlite3"))

    gate = permission.PermissionGate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    monkeypatch.setattr(permission, "get_permission_gate", lambda: gate)

    scope_grants = set()
    permission_calls = []

    def scope_key(domain_id, module, action, subject_id=None, brand_focus_id=None, global_scope=False):
        domain = str(domain_id).strip().lower()
        if domain == "bmp":
            domain = "zbmp"
        return domain, module, action, subject_id, brand_focus_id, global_scope

    def check_actor_scope(actor, *, domain_id, module, action, subject_id=None,
                          brand_focus_id=None, global_scope=False, **_kwargs):
        actor_id = actor.get("id") if isinstance(actor, dict) else None
        key = scope_key(domain_id, module, action, subject_id, brand_focus_id, global_scope)
        allowed = type(actor_id) is int and actor_id == _ACTOR["id"] and key in scope_grants
        permission_calls.append((actor_id, key, allowed))
        return SimpleNamespace(
            allowed=allowed,
            verification_state="verified",
            actor_id=actor_id,
            domain_id=key[0],
            principal_ref=None,
            audit_id="audit-root-owner-composition-test",
        )

    monkeypatch.setattr(permission, "check_actor_scope_permission", check_actor_scope)

    actor_state = {"current": _ACTOR.copy()}
    auth_service = importlib.import_module("lumenis.auth.service")
    real_get_current_user = auth_service.get_current_user
    monkeypatch.setattr(auth_service, "get_current_user", lambda **_kwargs: actor_state["current"])

    dual_domain_calls = []

    def dual_domain_read(actor_id, product_id, *, module, action):
        domain = "zbmp" if product_id == "ZBMP" else str(product_id).lower()
        call = (actor_id, domain, module, action)
        dual_domain_calls.append(call)
        return any(
            key[0] == domain and key[1] == module and key[2] == action
            and key[3] is None and key[4] is None and key[5] is True
            for key in scope_grants
        )

    authorization = importlib.import_module("account.authorization")
    monkeypatch.setattr(authorization, "check_dual_domain_permission", dual_domain_read)

    subject_registry = importlib.import_module("subject_registry")
    subjects = {
        "SUBJECT-A": {"subject_id": "SUBJECT-A", "domain_id": "CTH", "subject_type": "company",
                       "brand_focus_id": None, "name_zh": "测试主体", "name_en": "Test Subject"},
        "SUBJECT-B": {"subject_id": "SUBJECT-B", "domain_id": "CTH", "subject_type": "company",
                       "brand_focus_id": None, "name_zh": "另一个主体", "name_en": "Other Subject"},
    }
    monkeypatch.setattr(
        subject_registry, "get_subject_by_id",
        lambda domain, subject_id: subjects.get(subject_id) if str(domain).upper() == "CTH" else None,
    )
    picker_reads = []

    def list_subjects_for_test(domain=None):
        picker_reads.append(domain)
        return [
            subject for subject in subjects.values()
            if domain is None or subject["domain_id"].upper() == str(domain).upper()
        ]

    monkeypatch.setattr(subject_registry, "list_subjects", list_subjects_for_test)

    app = Flask("root-owner-auth-composition-test")
    app.config.update(TESTING=True, LUMENIS_OPEN_WORKSPACE=False)
    root_hooks = _build_root_hooks(app)

    experience_path, experience_tree = _source_tree("experience_runtime.py")
    experience_namespace = {"request": request, "jsonify": jsonify, "re": re}
    _compile_functions(experience_path, experience_tree, {
        "_content_project_scope", "_source_brief_context", "_shared_work_actor_scope",
        "_shared_work_response", "save_shared_work", "read_shared_work", "runtime_subjects",
        "register_experience_runtime",
    }, experience_namespace)
    experience_bp = Blueprint("experience_runtime", "experience_runtime")
    experience_namespace["experience_bp"] = experience_bp
    experience_routes = _register_ast_routes(
        experience_bp, experience_tree, experience_namespace,
        ("save_shared_work", "read_shared_work", "runtime_subjects"), "experience_bp",
    )
    experience_namespace["register_experience_runtime"](app)

    subject_path, subject_tree = _source_tree("subject_registry.py")
    subject_namespace = dict(vars(subject_registry))
    subject_namespace.update(request=request, jsonify=jsonify)
    _compile_functions(subject_path, subject_tree, {"get_subjects"}, subject_namespace)
    subject_bp = Blueprint("subject_registry", "subject_registry")
    subject_namespace["subject_registry_bp"] = subject_bp
    subject_routes = _register_ast_routes(
        subject_bp, subject_tree, subject_namespace, ("get_subjects",), "subject_registry_bp",
    )
    app.register_blueprint(subject_bp)

    api_path, api_tree = _source_tree("lumenis_app_api.py")
    api_namespace = {"request": request, "jsonify": jsonify, "json": json}
    _compile_functions(api_path, api_tree, {
        "_internal_pitch_body", "_context_error", "_context_selection_from_scope",
        "_context_envelope", "api_settings_context",
    }, api_namespace)
    lumenis_app_api_stub = ModuleType("lumenis_app_api")
    lumenis_app_api_stub._internal_pitch_body = api_namespace["_internal_pitch_body"]
    monkeypatch.setitem(sys.modules, "lumenis_app_api", lumenis_app_api_stub)

    domain_bp = Blueprint("domain_api", "lumenis_app_api")
    domain_routes = _register_ast_routes(
        domain_bp, api_tree, api_namespace, ("api_settings_context",), "domain_api_bp",
    )
    app.register_blueprint(domain_bp)

    assert _rule_contract(app, "domain_api.api_settings_context") == (
        "/api/settings/context", {"GET", "PUT", "DELETE"},
    )
    assert _rule_contract(app, "experience_runtime.save_shared_work") == (
        "/api/experience/saved-work", {"POST"},
    )
    assert _rule_contract(app, "experience_runtime.read_shared_work") == (
        "/api/experience/saved-work/<artifact_id>", {"GET"},
    )
    assert _rule_contract(app, "experience_runtime.runtime_subjects") == (
        "/api/experience/subjects", {"GET"},
    )
    assert _rule_contract(app, "subject_registry.get_subjects") == (
        "/api/settings/subjects", {"GET"},
    )

    grants = {
        "cth_reports_write": scope_key("cth", "reports", "write", global_scope=True),
        "cth_reports_read": scope_key("cth", "reports", "read", global_scope=True),
        "bmp_reports_read": scope_key("zbmp", "reports", "read", global_scope=True),
        "subject_a_read": scope_key("CTH", "subject_registry", "read", subject_id="SUBJECT-A"),
        "cth_subject_registry_global_read": scope_key(
            "CTH", "subject_registry", "read", global_scope=True,
        ),
    }
    scope_grants.update({grants["cth_reports_write"], grants["cth_reports_read"], grants["bmp_reports_read"]})

    return {
        "app": app,
        "client": app.test_client(),
        "actor_state": actor_state,
        "real_get_current_user": real_get_current_user,
        "scope_grants": scope_grants,
        "scope_key": scope_key,
        "grants": grants,
        "permission_calls": permission_calls,
        "dual_domain_calls": dual_domain_calls,
        "picker_reads": picker_reads,
        "repository": repository,
        "saved_work": saved_work,
        "root_hooks": root_hooks,
        "experience_routes": experience_routes,
        "subject_routes": subject_routes,
        "domain_routes": domain_routes,
    }


def _global_cth_headers():
    return {
        "X-Domain-Id": "CTH",
        "X-Product-Id": "CTH",
        "X-Lumenis-Context-Mode": "GLOBAL_ALL",
    }


def _saved_work_body():
    return {
        "title": "Auth boundary composition draft",
        "markdown": "A synthetic actor scoped this saved result.",
        "kind": "research",
        "payload": {"finding": "scope remains attached to the saved result"},
        "citations": [],
        "request_id": "auth-compose-0001",
    }


def test_owner_account_session_is_explicit_and_revocation_is_fresh(auth_composition, monkeypatch):
    """A Core Basic header is not an account; use the existing V4 session owner."""
    from lumenis.auth import models, service
    from lumenis.shared import database

    repository = auth_composition["repository"]
    monkeypatch.setattr(database, "get_repository", lambda: repository)
    real_get_current_user = auth_composition["real_get_current_user"]
    # Keep the real account lookup and isolate only its repository; never run
    # the credential/bootstrap initializer or touch a production database.
    monkeypatch.setattr(
        service, "get_current_user",
        lambda **_kwargs: real_get_current_user(read_only=True),
    )
    token = "synthetic-root-owner-session"
    expiry = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    with repository.transaction() as connection:
        connection.executescript(models.V4_TABLES_SQL)
        connection.execute(
            "INSERT INTO v4_users(id,username,password_hash,role,display_name,status) "
            "VALUES(?,?,?,?,?,?)",
            (_ACTOR["id"], "isolated-owner", "unused-session-read-fixture", "user", "Test", "active"),
        )
        connection.execute(
            "INSERT INTO v4_sessions(user_id,token,expires_at) VALUES(?,?,?)",
            (_ACTOR["id"], token, expiry),
        )

    auth_composition["scope_grants"].add(
        auth_composition["grants"]["cth_subject_registry_global_read"],
    )
    app = auth_composition["app"]
    assert app.config["LUMENIS_OPEN_WORKSPACE"] is False
    client = app.test_client(use_cookies=False)
    route = "/api/settings/subjects?domain_id=CTH"

    # Neither the current credential-free client nor the old reusable Basic
    # credential supplies the account identity required by this scoped owner.
    basic = base64.b64encode(b"root-auth-test-user:root-auth-test-password").decode()
    for headers in ({}, {"Authorization": f"Basic {basic}"}):
        denied = client.get(route, headers=headers)
        assert denied.status_code == 401
        assert denied.get_json()["code"] == "AUTH_REQUIRED"
    assert auth_composition["picker_reads"] == []

    headers = {"Authorization": f"Bearer {token}"}
    allowed = client.get(route, headers=headers)
    assert allowed.status_code == 200
    assert {row["subject_id"] for row in allowed.get_json()["subjects"]} == {
        "SUBJECT-A", "SUBJECT-B",
    }
    assert auth_composition["dual_domain_calls"][-1][0] == _ACTOR["id"]

    with repository.transaction() as connection:
        connection.execute("DELETE FROM v4_sessions WHERE token=?", (token,))
    revoked = client.get(route, headers=headers)
    assert revoked.status_code == 401
    assert revoked.get_json()["code"] == "AUTH_REQUIRED"
    assert auth_composition["picker_reads"] == ["CTH"]


def test_root_delegation_composes_with_saved_work_scope_save_reopen_and_revocation(auth_composition):
    client = auth_composition["client"]
    repository = auth_composition["repository"]
    saved_work = auth_composition["saved_work"]
    actor_state = auth_composition["actor_state"]
    scope_grants = auth_composition["scope_grants"]
    grants = auth_composition["grants"]

    actor_state["current"] = None
    denied = client.post("/api/experience/saved-work", json=_saved_work_body(), headers=_global_cth_headers())
    assert denied.status_code == 401
    assert denied.get_json()["code"] == "AUTH_REQUIRED"
    assert repository.query_one(f"SELECT COUNT(*) FROM {saved_work._TABLE}")[0] == 0

    actor_state["current"] = _ACTOR.copy()
    saved = client.post("/api/experience/saved-work", json=_saved_work_body(), headers=_global_cth_headers())
    assert saved.status_code == 200
    saved_body = saved.get_json()
    artifact_id = saved_body["result"]["artifact"]["artifact_id"]
    assert saved_body["result"]["receipt"]["scope"]["domain_id"] == "cth"
    assert saved_body["result"]["document"]["context"]["domain_id"] == "cth"
    assert saved_body["publish_status"] == "not_performed"

    reopened = client.get(f"/api/experience/saved-work/{artifact_id}", headers=_global_cth_headers())
    assert reopened.status_code == 200
    assert reopened.get_json()["result"]["document"]["markdown"] == _saved_work_body()["markdown"]

    wrong_scope = client.get(f"/api/experience/saved-work/{artifact_id}", headers={
        "X-Domain-Id": "BMP",
        "X-Product-Id": "BMP",
        "X-Lumenis-Context-Mode": "GLOBAL_ALL",
    })
    assert wrong_scope.status_code == 400
    assert wrong_scope.get_json()["code"] == "WORK_CONTEXT_MISMATCH"
    assert "result" not in wrong_scope.get_json()

    scope_grants.remove(grants["cth_reports_read"])
    revoked = client.get(f"/api/experience/saved-work/{artifact_id}", headers=_global_cth_headers())
    assert revoked.status_code == 403
    assert "result" not in revoked.get_json()
    assert any(call[1] == grants["cth_reports_write"] and call[2] for call in auth_composition["permission_calls"])
    assert any(call[1] == grants["cth_reports_read"] and not call[2] for call in auth_composition["permission_calls"])


def test_root_delegation_composes_with_context_picker_exact_scope_and_rechecks(auth_composition):
    client = auth_composition["client"]
    grants = auth_composition["grants"]
    scope_grants = auth_composition["scope_grants"]
    request_body = {"mode": "FOCUS", "domain_id": "CTH", "subject_id": "SUBJECT-A"}

    scope_grants.add(grants["subject_a_read"])
    allowed = client.put("/api/settings/context", json=request_body)
    assert allowed.status_code == 200
    body = allowed.get_json()
    assert body["selection_only"] is True
    assert body["context"]["domain_id"] == "CTH"
    assert body["context"]["subject_id"] == "SUBJECT-A"

    wrong_subject = client.put("/api/settings/context", json={**request_body, "subject_id": "SUBJECT-B"})
    assert wrong_subject.status_code == 403
    assert wrong_subject.get_json()["code"] == "SUBJECT_SCOPE_DENIED"

    scope_grants.remove(grants["subject_a_read"])
    revoked = client.put("/api/settings/context", json=request_body)
    assert revoked.status_code == 403
    assert revoked.get_json()["code"] == "SUBJECT_SCOPE_DENIED"
    assert any(
        call[1] == grants["subject_a_read"] and call[2]
        for call in auth_composition["permission_calls"]
    )
    assert any(
        call[1] == grants["subject_a_read"] and not call[2]
        for call in auth_composition["permission_calls"]
    )


def test_subject_registry_owner_requires_actor_and_exact_domain_read(auth_composition):
    client = auth_composition["client"]
    actor_state = auth_composition["actor_state"]
    scope_grants = auth_composition["scope_grants"]
    grants = auth_composition["grants"]
    picker_reads = auth_composition["picker_reads"]
    dual_domain_calls = auth_composition["dual_domain_calls"]

    actor_state["current"] = None
    no_actor = client.get("/api/settings/subjects?domain_id=CTH")
    assert no_actor.status_code == 401
    assert no_actor.get_json()["code"] == "AUTH_REQUIRED"
    assert dual_domain_calls == []
    assert picker_reads == []

    actor_state["current"] = _ACTOR.copy()
    no_scope = client.get("/api/settings/subjects?domain_id=CTH")
    assert no_scope.status_code == 403
    assert no_scope.get_json()["code"] == "SUBJECT_SCOPE_DENIED"
    assert picker_reads == []

    scope_grants.add(grants["cth_subject_registry_global_read"])
    authorized = client.get("/api/settings/subjects?domain_id=CTH")
    assert authorized.status_code == 200
    body = authorized.get_json()
    assert [domain["id"] for domain in body["domains"]] == ["CTH"]
    assert {subject["subject_id"] for subject in body["subjects"]} == {"SUBJECT-A", "SUBJECT-B"}
    assert picker_reads == ["CTH"]

    wrong_domain = client.get("/api/settings/subjects?domain_id=BMP")
    assert wrong_domain.status_code == 403
    assert wrong_domain.get_json()["code"] == "SUBJECT_SCOPE_DENIED"
    assert picker_reads == ["CTH"]

    scope_grants.remove(grants["cth_subject_registry_global_read"])
    revoked = client.get("/api/settings/subjects?domain_id=CTH")
    assert revoked.status_code == 403
    assert revoked.get_json()["code"] == "SUBJECT_SCOPE_DENIED"
    assert picker_reads == ["CTH"]
    assert dual_domain_calls == [
        (_ACTOR["id"], "cth", "subject_registry", "read"),
        (_ACTOR["id"], "cth", "subject_registry", "read"),
        (_ACTOR["id"], "zbmp", "subject_registry", "read"),
        (_ACTOR["id"], "cth", "subject_registry", "read"),
    ]


def test_subject_list_picker_is_local_open_only_and_rejects_remote_or_credentialed_bypass(auth_composition):
    app = auth_composition["app"]
    # Disable the Flask test client's cookie jar so the explicit Cookie header
    # below reaches the actual local-workspace transport guard unchanged.
    client = app.test_client(use_cookies=False)
    picker_reads = auth_composition["picker_reads"]
    subject_registry = importlib.import_module("subject_registry")
    assert subject_registry.list_subjects is not None

    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    opened = client.get(
        "/api/experience/subjects", headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert opened.status_code == 200
    assert opened.get_json()["selection_only"] is True
    assert len(picker_reads) == 1

    from lumenis.config import AUTH_CONFIG
    cookie_name = AUTH_CONFIG.get("session_cookie_name")
    assert isinstance(cookie_name, str) and cookie_name
    denied_cases = [
        ("closed", False, {}, "127.0.0.1"),
        ("remote", True, {}, "203.0.113.12"),
        ("foreign-origin", True, {"Origin": "https://foreign.example"}, "127.0.0.1"),
        ("bearer", True, {"Authorization": "Bearer synthetic-session"}, "127.0.0.1"),
        ("session-cookie", True, {"Cookie": f"{cookie_name}=synthetic-cookie"}, "127.0.0.1"),
    ]
    for _case, open_workspace, headers, remote in denied_cases:
        app.config["LUMENIS_OPEN_WORKSPACE"] = open_workspace
        response = client.get(
            "/api/experience/subjects", headers={"Host": "localhost", **headers},
            environ_overrides={"REMOTE_ADDR": remote},
        )
        assert response.status_code == 401, _case
    assert len(picker_reads) == 1

    basic = base64.b64encode(b"root-auth-test-user:root-auth-test-password").decode("ascii")
    credentialed = client.get(
        "/api/experience/subjects", headers={
            "Host": "localhost", "Authorization": f"Basic {basic}",
        }, environ_overrides={"REMOTE_ADDR": "203.0.113.12"},
    )
    assert credentialed.status_code == 200
    assert len(picker_reads) == 2


def test_workspace_host_head_requires_local_open_principal_and_has_no_body(tmp_path):
    from lumenis.system.runtime.workspace_host import register_workspace_host

    build_dir = tmp_path / "workspace-build"
    build_dir.mkdir()
    index_bytes = b"<!doctype html><title>synthetic workspace</title>"
    asset_bytes = b"synthetic compiled workspace asset"
    (build_dir / "index.html").write_bytes(index_bytes)
    (build_dir / "main.dart.js").write_bytes(asset_bytes)

    app = Flask("root-auth-workspace-head-composition-test")
    app.config.update(TESTING=True, LUMENIS_OPEN_WORKSPACE=True)
    register_workspace_host(app, build_dir)
    _build_root_hooks(app)
    client = app.test_client(use_cookies=False)

    expected_routes = {
        "lumenis_workspace_host.root": ("/workspace", index_bytes),
        "lumenis_workspace_host.root_slash": ("/workspace/", index_bytes),
        "lumenis_workspace_host.resource": ("/workspace/<path:resource>", asset_bytes),
        "lumenis_workspace_host.asset": ("/<workspaceasset:resource>", asset_bytes),
    }
    registered = {
        rule.endpoint: rule for rule in app.url_map.iter_rules()
        if rule.endpoint in expected_routes
    }
    assert set(registered) == set(expected_routes)
    for endpoint, (route, _body) in expected_routes.items():
        assert registered[endpoint].rule == route
        assert {"GET", "HEAD"}.issubset(registered[endpoint].methods)

    for path, expected_body in (
        ("/workspace", index_bytes),
        ("/workspace/", index_bytes),
        ("/workspace/main.dart.js", asset_bytes),
        ("/main.dart.js", asset_bytes),
    ):
        opened = client.head(
            path, headers={"Host": "localhost"},
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
        )
        assert opened.status_code == 200, path
        assert opened.get_data() == b"", path
        assert opened.headers["Content-Length"] == str(len(expected_body)), path

    denied_cases = (
        ("closed", False, {}, "127.0.0.1"),
        ("remote", True, {}, "203.0.113.12"),
        ("foreign-origin", True, {"Origin": "https://foreign.example"}, "127.0.0.1"),
    )
    for label, open_workspace, extra_headers, remote_addr in denied_cases:
        app.config["LUMENIS_OPEN_WORKSPACE"] = open_workspace
        for path in ("/workspace", "/workspace/main.dart.js", "/main.dart.js"):
            response = client.head(
                path, headers={"Host": "localhost", **extra_headers},
                environ_overrides={"REMOTE_ADDR": remote_addr},
            )
            assert response.status_code == 401, (label, path)
            assert response.get_data() == b"", (label, path)


@pytest.fixture(params=("account", "local"))
def manual_owner_root_composition(tmp_path, monkeypatch, request):
    """Run the real admitted manual owner fixture behind AST-loaded root hooks."""
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    owner_test_path = _REPO_ROOT / "tests" / "test_manual_evidence_scope_lifecycle.py"
    owner_tree = ast.parse(owner_test_path.read_text(encoding="utf-8"))
    from lumenis.shared.database import DatabaseRepository
    from lumenis.system.security import permission

    owner_namespace = {
        "__name__": "manual_evidence_scope_lifecycle_fixture",
        "json": json,
        "DatabaseRepository": DatabaseRepository,
        "permission": permission,
        "Flask": Flask,
    }
    _compile_functions(owner_test_path, owner_tree, {"manual_workspace"}, owner_namespace)
    owner_generator = owner_namespace["manual_workspace"](tmp_path, monkeypatch, request)
    workspace = next(owner_generator)

    assert permission.is_testing_bypass_enabled() is False
    app = workspace["app"]
    root_namespace = _build_root_hooks(app)

    app_path, app_tree = _source_tree("app.py")
    pg_namespace = {
        "request": flask_request,
        "jsonify": jsonify,
        "re": re,
        "_pg": workspace["gate"],
        "OperationType": permission.OperationType,
    }
    for node in app_tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = {
            target.id for target in node.targets if isinstance(target, ast.Name)
        }
        if "_PG_WRITE_METHODS" in names:
            value = node.value
            pg_namespace["_PG_WRITE_METHODS"] = frozenset(ast.literal_eval(value.args[0]))
        elif "_PG_BYPASS_PATHS" in names:
            value = node.value
            pg_namespace["_PG_BYPASS_PATHS"] = frozenset(ast.literal_eval(value.args[0]))
    assert pg_namespace["_PG_WRITE_METHODS"] == {"POST", "PUT", "DELETE", "PATCH"}
    _compile_functions(app_path, app_tree, {
        "_pg_resolve_operation_type", "_permission_gate_write_check",
    }, pg_namespace)
    app.before_request(pg_namespace["_permission_gate_write_check"])

    workspace["root_namespace"] = root_namespace
    workspace["pg_namespace"] = pg_namespace
    workspace["client"] = app.test_client(use_cookies=False)
    try:
        yield workspace
    finally:
        owner_generator.close()


def test_manual_evidence_http_upload_exact_withdraw_restore_and_denials(manual_owner_root_composition):
    ws = manual_owner_root_composition
    app = ws["app"]
    client = ws["client"]
    repo = ws["repo"]
    manual = ws["manual"]
    gate = ws["gate"]
    scope = ws["scope"]
    actor = ws["actor"]

    expected_routes = {
        "api_evidence_upload": ("/api/app_evidence/upload", {"POST"}),
        "api_evidence_delete": ("/api/app_evidence/<int:record_id>", {"DELETE"}),
        "api_evidence_restore": ("/api/app_evidence/<int:record_id>/restore", {"POST"}),
    }
    for endpoint, expected in expected_routes.items():
        assert _rule_contract(app, endpoint) == expected

    headers = {
        **ws["auth_headers"],
        "X-Domain-Id": "CTH",
        "X-Lumenis-Context-Mode": "GLOBAL_ALL",
    }
    request_options = {"environ_overrides": {"REMOTE_ADDR": "127.0.0.1"}}
    source_bytes = b"synthetic manual evidence bytes for root-owner composition"
    uploaded = client.post(
        "/api/app_evidence/upload",
        data={
            "file": (BytesIO(source_bytes), "capture.png"),
            "source": "other",
            "capture_mode": "screenshot",
            "metric_name": "note_count",
            "metric_value": "7",
            "topic": "synthetic scoped upload",
            "notes": "isolated root composition",
        },
        headers=headers,
        content_type="multipart/form-data",
        **request_options,
    )
    assert uploaded.status_code == 200, (
        "registered manual owner upload was blocked before scoped save: "
        f"status={uploaded.status_code}, body={uploaded.get_json()}"
    )
    record = uploaded.get_json()["data"]
    record_id = record["id"]
    before = repo.query_one("SELECT * FROM app_evidence_records WHERE id=?", (record_id,))
    before_inputs = json.loads(before["inputs_json"])
    expected_hash = hashlib.sha256(source_bytes).hexdigest()
    managed_file = Path(before["evidence_path"])
    assert before["status"] == "pending"
    assert before_inputs["manual_capture"]["file_sha256"] == expected_hash
    assert managed_file.read_bytes() == source_bytes

    # No actor and a foreign scope must not alter the real owner row.
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    no_actor = client.get(
        f"/api/app_evidence/{record_id}",
        headers={"X-Domain-Id": "CTH", "X-Lumenis-Context-Mode": "GLOBAL_ALL"},
        **request_options,
    )
    assert no_actor.status_code == 401
    assert no_actor.get_json()["code"] == "AUTH_REQUIRED"
    app.config["LUMENIS_OPEN_WORKSPACE"] = True

    wrong_scope = {**headers, "X-Domain-Id": "BMP"}
    wrong_scope_response = client.get(
        f"/api/app_evidence/{record_id}", headers=wrong_scope, **request_options,
    )
    assert wrong_scope_response.status_code in {403, 404}
    still_pending = repo.query_one("SELECT status FROM app_evidence_records WHERE id=?", (record_id,))
    assert still_pending["status"] == "pending"

    reason = "Owner approved withdrawal of this exact isolated Evidence row."
    exact_resource = manual.evidence_transition_resource(
        record_id, "withdrawn", reason, actor=actor, scope=scope,
    )
    no_approval = client.delete(
        f"/api/app_evidence/{record_id}",
        json={"reason": reason}, headers=headers, **request_options,
    )
    assert no_approval.status_code == 403, (
        f"withdrawal without a DATA_DELETE approval must be denied: {no_approval.get_json()}"
    )
    assert no_approval.get_json()["code"] == "EVIDENCE_EFFECT_PERMISSION_DENIED"
    assert repo.query_one("SELECT status FROM app_evidence_records WHERE id=?", (record_id,))["status"] == "pending"

    gate.grant_approval(
        "data_delete", duration_minutes=5, resource=exact_resource,
        granted_by="isolated-root-owner-composition",
    )
    withdrawn = client.delete(
        f"/api/app_evidence/{record_id}",
        json={"reason": reason}, headers=headers, **request_options,
    )
    assert withdrawn.status_code == 200, (
        "exact owner DATA_DELETE approval was rejected by the root PermissionGate "
        f"resource binding: status={withdrawn.status_code}, body={withdrawn.get_json()}"
    )
    withdrawn_row = repo.query_one("SELECT * FROM app_evidence_records WHERE id=?", (record_id,))
    assert withdrawn_row["status"] == "withdrawn"
    assert json.loads(withdrawn_row["inputs_json"])["manual_capture"]["file_sha256"] == expected_hash
    assert managed_file.read_bytes() == source_bytes
    lifecycle_rows = repo.query_all(
        "SELECT inputs_json, outputs_json FROM app_evidence_records "
        "WHERE feature_id='APP_MANUAL_LIFECYCLE' "
        "AND json_extract(inputs_json, '$.record_id')=? ORDER BY id",
        (record_id,),
    )
    assert len(lifecycle_rows) == 1
    withdrawal_audit = json.loads(lifecycle_rows[0]["inputs_json"])
    assert withdrawal_audit["actor"] == ws["identity"]
    assert withdrawal_audit["reason"] == reason
    assert withdrawal_audit["resource"] == exact_resource

    restore_reason = "Restore the exact isolated Evidence row to pending."
    restore_resource = manual.evidence_transition_resource(
        record_id, "pending", restore_reason, actor=actor, scope=scope,
    )
    gate.grant_approval(
        "db_write", duration_minutes=5, resource=restore_resource,
        granted_by="isolated-root-owner-composition",
    )
    restored = client.post(
        f"/api/app_evidence/{record_id}/restore",
        json={"reason": restore_reason}, headers=headers, **request_options,
    )
    assert restored.status_code == 200, (
        "owner restore could not complete after exact withdrawal: "
        f"status={restored.status_code}, body={restored.get_json()}"
    )
    restored_row = repo.query_one("SELECT * FROM app_evidence_records WHERE id=?", (record_id,))
    assert restored_row["status"] == "pending"
    assert json.loads(restored_row["inputs_json"])["manual_capture"]["file_sha256"] == expected_hash
    assert managed_file.read_bytes() == source_bytes
    lifecycle_rows = repo.query_all(
        "SELECT inputs_json, outputs_json FROM app_evidence_records "
        "WHERE feature_id='APP_MANUAL_LIFECYCLE' "
        "AND json_extract(inputs_json, '$.record_id')=? ORDER BY id",
        (record_id,),
    )
    assert len(lifecycle_rows) == 2
    restore_audit = json.loads(lifecycle_rows[1]["inputs_json"])
    assert restore_audit["actor"] == ws["identity"]
    assert restore_audit["reason"] == restore_reason
    assert restore_audit["resource"] == restore_resource
