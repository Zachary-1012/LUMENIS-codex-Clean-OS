"""Collector admission and import approval remain separate, using the real Gate."""
import sqlite3

import pytest
from flask import Flask

from lumenis.system import security
from lumenis.system.security import permission as p
from lumenis.system.collector.adapters import secondary_collection as surface
from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus


@pytest.fixture
def local_request(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.setattr(p, "_registered_resource_scope_exists", lambda *a, **kw: True)
    gate = p.PermissionGate()
    gate.grant_permission(p.PermissionLevel.COMMIT)
    monkeypatch.setattr(security, "get_permission_gate", lambda: gate)
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with app.test_request_context("/", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        principal = p.resolve_local_workspace_principal(module="collector", action="write")
        assert type(principal) is p.LocalWorkspacePrincipal
        yield app, principal, gate


SCOPE = {"domain_id": "cth", "global_scope": False, "subject_id": "SUBJ-A", "brand_focus_id": None}


def _scope_fence_schema(conn):
    fields = "domain_id TEXT,subject_id TEXT,brand_focus_id TEXT,source_platform TEXT,scope_status TEXT,scope_evidence_ref TEXT,product_id TEXT DEFAULT 'CTH'"
    conn.execute("CREATE TABLE notes(note_id TEXT," + fields + ")")
    conn.execute("CREATE TABLE canonical_data(source_id TEXT," + fields + ")")


def _approve(principal, gate, scope=SCOPE, keyword="Mall", max_results=1):
    _, denied = surface._manual_collection_guard(principal, scope, "weibo", keyword, max_results)
    assert denied["status"] == "APPROVAL_REQUIRED"
    return gate.grant_approval(
        p.OperationType.DATA_IMPORT.value, resource=denied["approval_resource"],
        granted_by="explicit isolated test",
    )


def test_no_actor_denies_before_adapter_or_persistence(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("unauthenticated request reached an effect")
    monkeypatch.setattr(surface, "_adapter_health", forbidden)
    monkeypatch.setattr(surface, "_write_run_log", forbidden)
    monkeypatch.setattr(surface, "_write_evidence", forbidden)
    result = surface.collect_search("weibo", "Mall", scope=SCOPE)
    assert result["status"] == "AUTH_REQUIRED"


@pytest.mark.parametrize("scope", [None, {}, {**SCOPE, "global_scope": "false"},
                                  {**SCOPE, "global_scope": True},
                                  {**SCOPE, "brand_focus_id": "BRAND-A"}])
def test_scope_form_cannot_be_inferred(local_request, scope):
    _, principal, _ = local_request
    _, denied = surface._manual_collection_guard(principal, scope, "weibo", "Mall", 1)
    assert denied["status"] == "SCOPE_UNAUTHORIZED"


def test_admission_does_not_grant_approval(local_request):
    _, principal, gate = local_request
    _, denied = surface._manual_collection_guard(principal, SCOPE, "weibo", "Mall", 1)
    assert denied["status"] == "APPROVAL_REQUIRED"
    assert gate.list_approvals() == []
    _approve(principal, gate)
    admitted, denied = surface._manual_collection_guard(principal, SCOPE, "weibo", "Mall", 1)
    assert denied is None and admitted == SCOPE


@pytest.mark.parametrize("scope,keyword,limit", [
    (SCOPE, "Other query", 1), (SCOPE, "Mall", 2),
    ({**SCOPE, "subject_id": "SUBJ-B"}, "Mall", 1),
    ({"domain_id": "cth", "global_scope": True, "subject_id": None, "brand_focus_id": None}, "Mall", 1),
])
def test_exact_approval_does_not_expand_to_another_request(local_request, scope, keyword, limit):
    _, principal, gate = local_request
    _approve(principal, gate)
    _, denied = surface._manual_collection_guard(principal, scope, "weibo", keyword, limit)
    assert denied["status"] == "APPROVAL_REQUIRED"


def test_workspace_revocation_rechecks_before_capture(local_request, monkeypatch):
    app, principal, gate = local_request
    _approve(principal, gate)
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    monkeypatch.setattr(surface, "_adapter_health", lambda *a, **kw: pytest.fail("capture after revocation"))
    result = surface.collect_search("weibo", "Mall", actor=principal, scope=SCOPE, max_results=1)
    assert result["status"] == "SCOPE_UNAUTHORIZED"


def test_import_approval_revoked_during_capture_prevents_all_persistence(local_request, monkeypatch):
    _, principal, gate = local_request
    token = _approve(principal, gate)
    class Adapter:
        def search(self, *a, **kw):
            gate.revoke_approval(token)
            return CollectionResult(status=CollectionStatus.SUCCESS, platform="weibo", items=[{
                "platform_content_id": "123", "title": "Mall", "content": "Mall source",
                "author_id": "456", "raw": {"mid": "123"},
            }])
    monkeypatch.setattr(surface, "_adapter_health", lambda *a, **kw: {"ready": True, "status": "READY"})
    monkeypatch.setattr(surface, "_get_runtime_adapter", lambda *a: Adapter())
    monkeypatch.setitem(surface._last_action, "weibo", 0.0)
    def forbidden(*a, **kw):
        raise AssertionError("persistence after revocation")
    monkeypatch.setattr(surface, "_write_run_log", forbidden)
    monkeypatch.setattr(surface, "_write_prelaunch_evidence", forbidden)
    monkeypatch.setattr("lumenis.system.collector.adapters.multi_platform_import.import_multi_platform_records", forbidden)
    result = surface.collect_search("weibo", "Mall", actor=principal, scope=SCOPE, max_results=1)
    assert result["status"] == "APPROVAL_REQUIRED"


def test_credential_filter_preserves_native_author_identity():
    raw = [{"author_id": "user-1", "url_token": "zhihu-user", "user_id": "user-1",
            "access_token": "private", "raw": {"cookie": "private", "pubdate": 123}}]
    assert surface._credential_free_observations(raw) == [
        {"author_id": "user-1", "url_token": "zhihu-user", "user_id": "user-1", "raw": {"pubdate": 123}},
    ]
    assert raw[0]["access_token"] == "private"


@pytest.mark.parametrize("platform,status,reference,expected", [
    ("weibo", "UNASSIGNED", None, False),
    ("weibo", "VERIFIED", "123", True),
    ("weibo", "VERIFIED", None, True),
    ("douyin", "UNASSIGNED", None, True),
])
def test_global_preflight_protects_assigned_or_cross_platform_sources(
    tmp_path, monkeypatch, platform, status, reference, expected,
):
    path = tmp_path / "source-fence.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    with sqlite3.connect(path) as conn:
        _scope_fence_schema(conn)
        conn.execute("INSERT INTO notes(note_id,domain_id,subject_id,brand_focus_id,source_platform,scope_status,scope_evidence_ref) VALUES('123','cth',NULL,NULL,?,?,?)", (platform, status, reference))
    global_scope = {"domain_id": "cth", "global_scope": True, "subject_id": None, "brand_focus_id": None}
    assert surface._prelaunch_scope_conflict(
        [{"content_id": "123", "platform": "weibo"}], global_scope,
    ) is expected


def test_scope_preflight_preserves_registered_platform_alias(tmp_path, monkeypatch):
    path = tmp_path / "alias-fence.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    with sqlite3.connect(path) as conn:
        _scope_fence_schema(conn)
        conn.execute("INSERT INTO notes VALUES('123','cth','SUBJ-A',NULL,'xhs','VERIFIED','9','CTH')")
        conn.execute("INSERT INTO canonical_data VALUES('123','cth','SUBJ-A',NULL,'xiaohongshu','VERIFIED','9','CTH')")
    assert surface._prelaunch_scope_conflict(
        [{"content_id": "123", "source_platform": "xiaohongshu"}], SCOPE,
    ) is False


def test_evidence_url_filter_removes_credentials_and_preserves_public_identity():
    raw = {"url": "https://private:secret@example.test/item?author_id=1&xsec_token=private&token=private#private"}
    assert surface._credential_free_observations(raw) == {"url": "https://example.test/item?author_id=1"}
    assert "private" in raw["url"]
