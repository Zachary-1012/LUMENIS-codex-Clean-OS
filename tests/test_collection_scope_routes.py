"""HTTP selectors bind to server Collector authority; they do not approve import."""
import pytest
from flask import Flask

from tests.test_source_brief_job import job_db
from lumenis.system.security import permission as permission

URL = "/api/experience/cth/platform-collection/search"
GLOBAL = {"X-Domain-Id": "CTH", "X-Product-Id": "CTH", "X-Lumenis-Context-Mode": "GLOBAL_ALL"}
BODY = {"operator": "human", "confirm_read_only": True, "platform": "bilibili", "keyword": "venue"}


@pytest.fixture
def route(job_db, monkeypatch):
    import experience_runtime
    import lumenis.auth.service
    import subject_registry
    from lumenis.system.collector.adapters import secondary_collection

    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.setattr(lumenis.auth.service, "get_current_user", lambda: None)
    gate = permission.PermissionGate()
    monkeypatch.setattr(permission, "get_permission_gate", lambda: gate)
    entry, _ = subject_registry.add_subject({
        "domain_id": "CTH", "subject_type": "company", "name_en": "Registered Venue", "name_zh": "已注册商业主体",
    })
    calls = []
    def collect(platform, keyword, **kwargs):
        calls.append((platform, keyword, kwargs))
        return {"ok": False, "status": "APPROVAL_REQUIRED", "read_only": True,
                "external_write": False, "approval_resource": "exact-import-resource"}
    monkeypatch.setattr(secondary_collection, "collect_search", collect)
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    app.register_blueprint(experience_runtime.experience_bp)
    return app.test_client(), app, entry, calls, gate


@pytest.mark.parametrize("body", [None, [], "human", 7,
    {**BODY, "actor": {"id": 1}}, {**BODY, "scope": {"global_scope": True}},
    {**BODY, "prelaunch_local_import": True}, {**BODY, "prelaunch_authorization": "claimed"}])
def test_client_cannot_supply_identity_or_prelaunch_admission(route, body):
    api, _, _, calls, _ = route
    result = api.post(URL, headers=GLOBAL, json=body)
    assert result.status_code == 400
    assert result.get_json()["code"] == "INVALID_COLLECTION_REQUEST"
    assert calls == []


@pytest.mark.parametrize("remote,headers,open_workspace", [
    ("192.0.2.9", {}, True), ("127.0.0.1", {"X-Forwarded-For": "127.0.0.1"}, True),
    ("127.0.0.1", {"X-Actor-ID": "23"}, True), ("127.0.0.1", {}, False),
])
def test_remote_forged_or_closed_workspace_cannot_reach_collector(route, remote, headers, open_workspace):
    api, app, _, calls, _ = route
    app.config["LUMENIS_OPEN_WORKSPACE"] = open_workspace
    result = api.post(URL, headers={**GLOBAL, **headers}, json=BODY, environ_overrides={"REMOTE_ADDR": remote})
    assert result.status_code == 401 and result.get_json()["code"] == "AUTH_REQUIRED"
    assert calls == []


def test_registered_focus_uses_sealed_server_principal_and_retains_pending_effect(route):
    api, _, entry, calls, gate = route
    focus = {**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": entry["subject_id"]}
    result = api.post(URL, headers=focus, json=BODY)
    assert result.status_code == 403 and result.get_json()["status"] == "APPROVAL_REQUIRED"
    args = calls[0][2]
    assert type(args["actor"]) is permission.LocalWorkspacePrincipal
    assert args["scope"] == {"domain_id": "cth", "subject_id": entry["subject_id"],
                             "brand_focus_id": None, "global_scope": False}
    assert args["operator"] == "human"
    assert not gate.check(permission.OperationType.DATA_IMPORT, resource="exact-import-resource", caller="workspace:local").allowed


def test_missing_focus_and_global_with_focus_cannot_reach_io(route):
    api, _, entry, calls, _ = route
    for headers in ({**GLOBAL, "X-Lumenis-Context-Mode": "FOCUS", "X-Subject-ID": "absent"},
                    {**GLOBAL, "X-Subject-ID": entry["subject_id"]}):
        assert api.post(URL, headers=headers, json=BODY).status_code in {403, 404}
    assert calls == []
