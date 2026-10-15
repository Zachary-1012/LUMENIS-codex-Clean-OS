"""Isolated regressions for the #17 KOS, Gateway status, and Shared SavedWork repairs."""
from __future__ import annotations

import ast
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType

import pytest
from flask import Flask, jsonify, request
from werkzeug.datastructures import Headers

from lumenis.shared.database import DatabaseRepository
from lumenis.system.security import permission

SHARED_SCOPE = {"scope_kind": "shared_workspace", "version": 1}


@pytest.fixture
def shared_workspace(tmp_path, monkeypatch):
    db_path = tmp_path / "isolated-shared-work.sqlite3"
    artifact_dir = tmp_path / "artifacts"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(artifact_dir))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"isolated-test": "isolated-test-evidence-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "isolated-test")
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.delenv("LUMENIS_BOOTSTRAP_OWNER_USERNAME", raising=False)
    monkeypatch.delenv("LUMENIS_BOOTSTRAP_OWNER_PASSWORD", raising=False)
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)

    import account.models as account_models
    import canonical_data
    import shared_artifacts
    import subject_registry
    from lumenis.importer import documents
    from lumenis.shared.evidence import store
    from lumenis.shared.reporting import saved_work

    repository = DatabaseRepository(str(db_path))
    for module in (account_models, shared_artifacts, store, documents, saved_work):
        monkeypatch.setattr(module, "get_repository", lambda repo=repository: repo)
    if hasattr(subject_registry, "get_repository"):
        monkeypatch.setattr(subject_registry, "get_repository", lambda: repository)

    shared_artifacts.ensure_artifact_table()
    store.init_evidence_store(str(db_path))
    with repository.transaction() as con:
        store.ensure_evidence_schema(con)
    canonical_data.ensure_canonical_table(str(db_path))
    account_models.init_account_db()

    gate = permission.PermissionGate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    monkeypatch.setattr(permission, "get_permission_gate", lambda: gate)
    workspace = {
        "root": tmp_path,
        "artifact_dir": artifact_dir,
        "repo": repository,
        "gate": gate,
        "app": Flask("issue17-isolated-shared-work"),
        "documents": documents,
        "saved_work": saved_work,
        "actor_counter": 0,
    }

    # Run the exact current app.py pre-handler guard in this isolated Flask app.
    # Importing app.py would initialize unrelated production services and DBs.
    tree = ast.parse(Path("app.py").read_text(encoding="utf-8-sig"))
    guard = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "_permission_gate_write_check")
    guard.decorator_list = []
    namespace = {
        "request": request, "jsonify": jsonify,
        "_PG_WRITE_METHODS": {"POST", "PUT", "PATCH", "DELETE"},
        "_PG_BYPASS_PATHS": set(), "_pg": gate,
        "_pg_resolve_operation_type": lambda *_args: permission.OperationType.DB_WRITE,
    }
    exec(compile(ast.Module(body=[guard], type_ignores=[]), "app.py", "exec"), namespace)  # noqa: S102 -- execute the extracted guard in an isolated Flask test app.
    workspace["app"].before_request(namespace["_permission_gate_write_check"])
    return workspace


def _account(workspace, *, grants=("read", "write"), product="SHARED"):
    workspace["actor_counter"] += 1
    username = f"issue17-user-{workspace['actor_counter']}"
    with workspace["repo"].transaction() as con:
        cursor = con.execute(
            "INSERT INTO v4_users (username,password_hash,role,display_name,status) "
            "VALUES (?,?,?,?,?)",
            (username, "isolated-test-hash", "user", username, "active"),
        )
        actor = {"id": int(cursor.lastrowid)}
        for action in grants:
            con.execute(
                "INSERT INTO v4_member_authorizations "
                "(user_id,product_id,module,action,data_scope,time_range,granted_by) "
                "VALUES (?,?,?,?,?,?,?)",
                (actor["id"], product, "reports", action, None, None, None),
            )
    return actor


def _grant(workspace, actor, *, product, module, action, data_scope=None):
    with workspace["repo"].transaction() as con:
        con.execute(
            "INSERT INTO v4_member_authorizations "
            "(user_id,product_id,module,action,data_scope,time_range,granted_by) "
            "VALUES (?,?,?,?,?,?,?)",
            (actor["id"], product, module, action,
             None if data_scope is None else json.dumps(data_scope), None, None),
        )


def _save_args(actor, *, request_id="issue17-save-0001", **changes):
    result = {
        "title": "Independent workspace note",
        "markdown": "A user-authored draft that has no CTH or BMP source prerequisite.",
        "kind": "research",
        "payload": {"origin": "direct_user_brief"},
        "citations": [],
        "request_id": request_id,
        "actor": actor,
        "scope": SHARED_SCOPE,
    }
    result.update(changes)
    return result


def _artifact_state(workspace):
    with workspace["repo"].connection(read_only=True, wal=False) as con:
        rows = con.execute(
            "SELECT artifact_id,kind,product_id,domain_id,source_execution_id,sha256 "
            "FROM lumenis_shared_artifacts ORDER BY artifact_id"
        ).fetchall()
    files = tuple(sorted(path.name for path in workspace["artifact_dir"].iterdir())) \
        if workspace["artifact_dir"].exists() else ()
    return tuple(tuple(row) for row in rows), files


@pytest.mark.parametrize("selected_user_api", [False, True])
def test_gateway_status_reports_selected_service_and_separates_deterministic_module(
    monkeypatch, selected_user_api,
):
    import api_dual_domain
    from lumenis.system.ai_gateway import core, user_api_adapter

    class Connection:
        def execute(self, _sql):
            return self

        def fetchone(self):
            return {"c": 0}

        def close(self):
            return None

    class Guardian:
        @staticmethod
        def health_check():
            return {"overall": "healthy", "workers": {"total": 0, "running": 0}}

    class Collector:
        @staticmethod
        def get_status():
            return {"is_running": False, "state": "idle"}

    monkeypatch.setattr(api_dual_domain, "_get_conn", Connection)
    monkeypatch.setitem(__import__("sys").modules, "runtime_guardian",
                        type("GuardianModule", (), {"get_guardian": staticmethod(lambda _name: Guardian())}))
    monkeypatch.setitem(__import__("sys").modules, "collector_automation",
                        type("CollectorModule", (), {"get_collector_automation": staticmethod(lambda: Collector())}))
    owned_observation = {
        "provider": "owned", "available": False, "service_binding": "NOT_BOUND",
        "state": "UNAVAILABLE", "reason": "OWNED_SERVICE_SCOPED_STATUS",
        "model_id": None, "fallback_allowed": False,
    }
    user_api_observation = {
        "provider": "user_api", "configured": True, "available": False,
        "service_binding": "CONFIGURED", "state": "CONFIGURED_NOT_VERIFIED",
        "reason": "INFERENCE_NOT_VERIFIED", "model_id": "selected-user-model",
        "fallback_allowed": False,
    }
    monkeypatch.setattr(core, "owned_service_observation", lambda: owned_observation)
    monkeypatch.setattr(user_api_adapter, "is_selected", lambda: selected_user_api)
    monkeypatch.setattr(user_api_adapter, "status", lambda: user_api_observation)
    monkeypatch.setitem(__import__("sys").modules, "ai_analyzer", ModuleType("ai_analyzer"))

    app = Flask("issue17-system-status")
    app.register_blueprint(api_dual_domain.system_bp)
    response = app.test_client().get("/api/system/status", headers={"X-Domain-Id": "system"})

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["ai"]["status"] == "unavailable"
    assert data["ai"]["available"] is False
    expected = user_api_observation if selected_user_api else owned_observation
    assert data["ai"]["provider"] == expected["provider"]
    assert data["ai"]["service_binding"] == expected["service_binding"]
    if selected_user_api:
        assert data["ai"]["configured"] is True
        assert data["ai"]["state"] == "CONFIGURED_NOT_VERIFIED"
    assert data["deterministic_analysis"] == {
        "status": "available", "module": "ai_analyzer",
    }


def test_shared_saved_work_is_independent_and_preserves_version_conflicts(shared_workspace):
    work = shared_workspace["saved_work"]
    actor = _account(shared_workspace)
    args = _save_args(actor)

    first = work.save_work(**args)
    assert first["replayed"] is False
    assert first["document"]["context"] == {
        "scope_kind": "shared_workspace", "version": 1, "actor_id": actor["id"],
    }
    assert first["return_ref"]["scope"] == SHARED_SCOPE
    assert (first["artifact"]["product_id"], first["artifact"]["domain_id"]) == ("SHARED", "content")

    reopened = work.reopen_work(first["artifact"]["artifact_id"], actor=actor, scope=SHARED_SCOPE)
    assert reopened["document"] == first["document"]
    found = work.search_work(actor=actor, scope=SHARED_SCOPE, query="user-authored")
    assert [item["artifact"]["artifact_id"] for item in found["items"]] == [first["artifact"]["artifact_id"]]

    revision = work.revise_work(
        first["artifact"]["artifact_id"], actor=actor, scope=SHARED_SCOPE,
        request_id="issue17-revision-0002", expected_sha256=first["artifact"]["sha256"],
        reason="Correct the user-authored wording.", edits=[{
            "pointer": "/markdown",
            "expected": first["document"]["markdown"],
            "value": "A revised user-authored draft with no CTH or BMP source prerequisite.",
        }],
    )
    assert revision["document"]["version"] == 2
    assert revision["document"]["parent_artifact_id"] == first["artifact"]["artifact_id"]
    assert revision["return_ref"]["scope"] == SHARED_SCOPE

    before_stale_write = _artifact_state(shared_workspace)
    with pytest.raises(ValueError, match="WORK_REVISION_CONFLICT"):
        work.save_work(**_save_args(
            actor, request_id="issue17-stale-parent-0003", work_id=first["document"]["work_id"],
            markdown="A stale writer cannot replace a current revision.",
        ))
    assert _artifact_state(shared_workspace) == before_stale_write


def test_shared_saved_work_serializes_concurrent_initial_versions(shared_workspace):
    work = shared_workspace["saved_work"]
    actor = _account(shared_workspace)
    work_id = "WORK-" + "c" * 24
    start = threading.Barrier(2)

    def write(request_id, markdown):
        start.wait(timeout=5)
        try:
            result = work.save_work(**_save_args(
                actor, request_id=request_id, work_id=work_id, markdown=markdown,
            ))
            return ("saved", result)
        except ValueError as exc:
            return (str(exc), None)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(write, "issue17-concurrent-a", "Concurrent draft A."),
            pool.submit(write, "issue17-concurrent-b", "Concurrent draft B."),
        ]
        results = [future.result(timeout=20) for future in futures]

    assert sorted(result[0] for result in results) == ["WORK_REVISION_CONFLICT", "saved"]
    saved = next(result[1] for result in results if result[0] == "saved")
    assert saved["document"]["version"] == 1
    assert len(work.search_work(actor=actor, scope=SHARED_SCOPE)["items"]) == 1


def test_shared_permission_does_not_fallback_to_cth_and_rechecks_revocation(shared_workspace):
    work = shared_workspace["saved_work"]
    cth_only_actor = _account(shared_workspace, product="CTH")
    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        work.save_work(**_save_args(cth_only_actor, request_id="issue17-cth-only-0001"))
    assert _artifact_state(shared_workspace) == ((), ())

    scoped_shared_actor = _account(shared_workspace, grants=())
    _grant(shared_workspace, scoped_shared_actor, product="SHARED", module="reports",
           action="write", data_scope={"global": True})
    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        work.save_work(**_save_args(scoped_shared_actor, request_id="issue17-scoped-shared-0001"))
    assert _artifact_state(shared_workspace) == ((), ())

    denied_effect = permission.check_shared_workspace_effect(
        scoped_shared_actor, SHARED_SCOPE, permission.OperationType.DATA_IMPORT,
        "document-import:v1:" + "a" * 64, module="reports", action="write",
        gate=shared_workspace["gate"],
    )
    assert denied_effect.allowed is False
    borrowed_gate = permission.PermissionGate()
    borrowed_gate.grant_permission(permission.PermissionLevel.COMMIT)
    borrowed_effect = permission.check_shared_workspace_effect(
        _account(shared_workspace), SHARED_SCOPE, permission.OperationType.DATA_EXPORT,
        "saved-work:v1:" + "b" * 64, module="reports", action="read", gate=borrowed_gate,
    )
    assert borrowed_effect.allowed is False

    actor = _account(shared_workspace)
    first = work.save_work(**_save_args(actor, request_id="issue17-revocation-0001"))
    with shared_workspace["repo"].transaction() as con:
        con.execute(
            "DELETE FROM v4_member_authorizations WHERE user_id=? AND product_id='SHARED' AND action='write'",
            (actor["id"],),
        )
    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        work.revise_work(
            first["artifact"]["artifact_id"], actor=actor, scope=SHARED_SCOPE,
            request_id="issue17-revoked-revision", expected_sha256=first["artifact"]["sha256"],
            reason="Attempt after revocation.", edits=[{
                "pointer": "/markdown", "expected": first["document"]["markdown"],
                "value": "This change must be denied after write revocation.",
            }],
        )
    assert work.reopen_work(first["artifact"]["artifact_id"], actor=actor, scope=SHARED_SCOPE)["document"] == first["document"]

    with shared_workspace["repo"].transaction() as con:
        con.execute(
            "DELETE FROM v4_member_authorizations WHERE user_id=? AND product_id='SHARED' AND action='read'",
            (actor["id"],),
        )
    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        work.reopen_work(first["artifact"]["artifact_id"], actor=actor, scope=SHARED_SCOPE)


def test_shared_citations_keep_original_cth_permission_and_same_actor(shared_workspace):
    work = shared_workspace["saved_work"]
    documents = shared_workspace["documents"]
    actor = _account(shared_workspace)
    for action in ("read", "write"):
        _grant(
            shared_workspace, actor, product="CTH", module="reports", action=action,
            data_scope={"global": True},
        )

    source_scope = {
        "domain_id": "cth", "subject_id": None, "brand_focus_id": None,
        "global_scope": True,
    }
    source_path = shared_workspace["root"] / "source.txt"
    source_path.write_text("An approved source statement for exact quotation.\n", encoding="utf-8")
    provenance = {
        "source_url": None, "source_origin": {"kind": "approved-file", "ref": "issue17-source-0001"},
        "published_at": None, "captured_at": "2026-10-16T00:00:00Z",
        "rights": "owner-approved", "title": "Isolated source permission regression",
    }
    source_args = {"actor": actor, "scope": source_scope, "provenance": provenance}
    import_resource = documents.document_import_resource(str(source_path), **source_args)
    shared_workspace["gate"].grant_approval(
        permission.OperationType.DATA_IMPORT.value,
        resource=import_resource, granted_by="isolated-test",
    )
    imported = documents.import_document(str(source_path), **source_args)
    quote = documents.locate_quote(
        imported["evidence_id"], actor=actor, scope=source_scope, start=0, end=36,
    )["citation"]

    saved = work.save_work(**_save_args(
        actor, request_id="issue17-cited-shared-work-0001", citations=[quote],
    ))
    reopened = work.reopen_work(saved["artifact"]["artifact_id"], actor=actor, scope=SHARED_SCOPE)
    assert reopened["receipt"]["sources"][0]["scope"] == source_scope

    with shared_workspace["repo"].transaction() as con:
        con.execute(
            "DELETE FROM v4_member_authorizations "
            "WHERE user_id=? AND product_id='CTH' AND module='reports' AND action='read'",
            (actor["id"],),
        )
    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        work.reopen_work(saved["artifact"]["artifact_id"], actor=actor, scope=SHARED_SCOPE)
    searched = work.search_work(actor=actor, scope=SHARED_SCOPE)
    assert searched["items"] == []
    assert searched["unverified_candidates"] == 1

    other_actor = _account(shared_workspace)
    with pytest.raises(ValueError, match="WORK_CONTEXT_MISMATCH"):
        work.reopen_work(saved["artifact"]["artifact_id"], actor=other_actor, scope=SHARED_SCOPE)


def test_shared_workspace_api_saves_reads_revises_and_exports(shared_workspace):
    import experience_runtime

    app = shared_workspace["app"]
    app.config.update(TESTING=True, LUMENIS_OPEN_WORKSPACE=True)
    app.register_blueprint(experience_runtime.experience_bp)
    client = app.test_client()
    headers = {"X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE)}
    body = {
        "title": "API saved draft", "markdown": "Original API draft.",
        "kind": "research", "payload": {"source": "direct_user_brief"},
        "citations": [], "request_id": "issue17-api-save-0001",
    }

    saved_response = client.post("/api/experience/saved-work", json=body, headers=headers,
                                 environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert saved_response.status_code == 200, saved_response.get_json()
    saved = saved_response.get_json()["result"]
    artifact_id = saved["artifact"]["artifact_id"]

    read_response = client.get(f"/api/experience/saved-work/{artifact_id}", headers=headers,
                               environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert read_response.status_code == 200, read_response.get_json()
    assert read_response.get_json()["result"]["document"] == saved["document"]
    search_response = client.get("/api/experience/saved-work?query=API", headers=headers,
                                 environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert search_response.status_code == 200, search_response.get_json()
    assert [item["artifact"]["artifact_id"] for item in
            search_response.get_json()["result"]["items"]] == [artifact_id]

    revision_response = client.post(
        f"/api/experience/saved-work/{artifact_id}/revise",
        json={
            "request_id": "issue17-api-revision-0002",
            "expected_sha256": saved["artifact"]["sha256"],
            "reason": "Update the user-authored draft.",
            "edits": [{"pointer": "/markdown", "expected": "Original API draft.",
                       "value": "Revised API draft."}],
        }, headers=headers, environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert revision_response.status_code == 200, revision_response.get_json()
    revised = revision_response.get_json()["result"]
    assert revised["document"]["version"] == 2
    assert revised["document"]["markdown"] == "Revised API draft."

    export_response = client.get(
        f"/api/experience/saved-work/{revised['artifact']['artifact_id']}/export?format=json",
        headers=headers, environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert export_response.status_code == 200
    assert json.loads(export_response.data)["markdown"] == "Revised API draft."


def test_shared_member_authorization_accepts_shared_without_schema_migration(shared_workspace):
    from account.authorization import (
        get_member_authorizations,
        set_member_authorizations,
    )

    actor = _account(shared_workspace, grants=())
    with shared_workspace["app"].app_context():
        result = set_member_authorizations(actor["id"], [
            {"product_id": "SHARED", "module": "reports", "action": "read"},
            {"product_id": "SHARED", "module": "reports", "action": "write"},
        ])

    assert result["success"] is True
    assert [(item["product_id"], item["module"], item["action"])
            for item in get_member_authorizations(actor["id"])] == [
                ("SHARED", "reports", "read"), ("SHARED", "reports", "write"),
            ]


def test_saved_work_route_accepts_only_exact_shared_scope_without_cth_resolution(shared_workspace, monkeypatch):
    import experience_runtime

    app = shared_workspace["app"]
    app.config.update(TESTING=True, LUMENIS_OPEN_WORKSPACE=True)
    app.register_blueprint(experience_runtime.experience_bp)
    calls = []

    def fake_save(**kwargs):
        calls.append(kwargs)
        return {"scope": kwargs["scope"], "actor": kwargs["actor"].principal_ref}

    monkeypatch.setattr(shared_workspace["saved_work"], "save_work", fake_save)
    monkeypatch.setattr(experience_runtime, "_source_brief_context",
                        lambda *_args, **_kwargs: pytest.fail("Shared scope resolved through CTH/BMP SourceBrief"))
    client = app.test_client()
    body = {
        "title": "Independent user note", "markdown": "Direct user brief.",
        "kind": "research", "payload": {}, "citations": [],
        "request_id": "issue17-route-save-0001",
    }
    response = client.post(
        "/api/experience/saved-work", json=body,
        headers={"X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE)},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert response.status_code == 200
    assert response.get_json()["result"]["scope"] == SHARED_SCOPE
    assert response.get_json()["result"]["actor"] == "workspace:local"
    assert len(calls) == 1

    before = len(calls)
    mixed = client.post(
        "/api/experience/saved-work", json=body,
        headers={"X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE), "X-Domain-Id": "cth"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert mixed.status_code == 400
    assert mixed.get_json()["code"] == "SHARED_WORKSPACE_SCOPE_MIXED_CONTEXT"
    assert len(calls) == before

    repeated = client.post(
        "/api/experience/saved-work", json=body,
        headers=Headers([
            ("X-Lumenis-Workspace-Scope", json.dumps(SHARED_SCOPE)),
            ("X-Lumenis-Workspace-Scope", json.dumps(SHARED_SCOPE)),
        ]),
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert repeated.status_code == 400
    assert repeated.get_json()["code"] == "SHARED_WORKSPACE_SCOPE_INVALID"
    assert len(calls) == before

    for field in ("actor_id", "user_id", "principal_kind", "principal_ref",
                  "workspace_id", "project_id", "domain_id", "product_id",
                  "subject_id", "brand_focus_id", "global_scope"):
        forged_scope = {**SHARED_SCOPE, field: "forged"}
        rejected = client.post(
            "/api/experience/saved-work", json=body,
            headers={"X-Lumenis-Workspace-Scope": json.dumps(forged_scope)},
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
        )
        assert rejected.status_code == 400
        assert rejected.get_json()["code"] == "SHARED_WORKSPACE_SCOPE_INVALID"
        assert len(calls) == before

    forged_identity_header = client.post(
        "/api/experience/saved-work", json=body,
        headers={"X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE), "X-User-Id": "7"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert forged_identity_header.status_code == 400
    assert forged_identity_header.get_json()["code"] == "SHARED_WORKSPACE_SCOPE_MIXED_CONTEXT"
    assert len(calls) == before
