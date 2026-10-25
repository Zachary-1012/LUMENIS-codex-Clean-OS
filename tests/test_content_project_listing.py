import hashlib
import sqlite3
import zipfile

import pytest
from flask import Flask

import shared_artifacts as artifacts
from lumenis.shared.database import DatabaseRepository
from lumenis.system.security import permission as p


@pytest.fixture
def store(tmp_path, monkeypatch):
    db_path = tmp_path / "projects.sqlite3"
    root = tmp_path / "artifacts"
    repository = DatabaseRepository(str(db_path))
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(root))
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)
    monkeypatch.setattr(artifacts, "get_repository", lambda: repository)
    monkeypatch.setattr(
        p, "_registered_resource_scope_exists",
        lambda domain, *, subject_id, brand_focus_id: (
            domain in {"bmp", "zbmp"} and subject_id is None
            and brand_focus_id in {"brand-a", "brand-b"}
        ),
    )
    monkeypatch.setattr(p, "_actor_has_scope_action", lambda actor_id, *_: actor_id in {1, 2})
    monkeypatch.setattr(p, "_load_actor_scope_role", lambda actor_id: "admin" if actor_id in {1, 2} else None)
    gate = p.PermissionGate()
    monkeypatch.setattr(p, "get_permission_gate", lambda: gate)
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with app.test_request_context(
        "/", headers={"Host": "localhost"}, environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        principal = p.resolve_local_workspace_principal(module="content", action="write")
    return {"app": app, "db_path": db_path, "repository": repository,
            "root": root, "principal": principal}


def _scope(*, brand_focus_id=None):
    return {
        "domain_id": "bmp", "subject_id": None, "brand_focus_id": brand_focus_id,
        "global_scope": brand_focus_id is None,
    }


def _write_project(store, actor, *, scope, artifact_id, created_at="2026-01-01 00:00:00", padding=""):
    actor_id, normalized = artifacts._authorize_content_project(
        actor, **scope, action="read",
    )
    media = b"isolated-media-bytes"
    project = {
        "schema_version": 1, "timeline": {}, "source_artifact_refs": [],
        "context": artifacts._content_artifact_context(actor, actor_id, normalized),
        "parent_artifact_id": None,
        "rights": {"state": "unknown", "demo_acknowledged": True,
                   "label": "demo-only / rights unknown"},
        "output_kind": "audio",
    }
    if padding:
        project["test_padding"] = padding
    render = {
        "output_kind": "audio", "state": "rendered_verified", "measurement": {},
        "media_sha256": hashlib.sha256(media).hexdigest(), "size_bytes": len(media),
    }
    store["root"].mkdir(parents=True, exist_ok=True)
    package = store["root"] / f"{artifact_id}.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("project.json", artifacts._json_bytes(project))
        archive.writestr("render.json", artifacts._json_bytes(render))
        archive.writestr("media.wav", media)
    record = artifacts._register_artifact(
        artifact_id=artifact_id, kind="content_project",
        product_id="CTH" if normalized["domain_id"] == "cth" else "ZBMP",
        domain_id=normalized["domain_id"], source_execution_id="isolated-list-test",
        evidence_id="", note_id="", path=package, media_type="application/zip",
    )
    with store["repository"].connect() as connection:
        connection.execute(
            "UPDATE lumenis_shared_artifacts SET created_at=? WHERE artifact_id=?",
            (created_at, artifact_id),
        )
    record["created_at"] = created_at
    return record, package


def _list(store, actor, scope, *, limit=20, cursor=None):
    return artifacts.list_content_projects(actor=actor, **scope, limit=limit, cursor=cursor)


def _local_request(store):
    return store["app"].test_request_context(
        "/", headers={"Host": "localhost"}, environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )


def test_local_projects_are_filtered_by_exact_focus_and_reopen_after_new_connection(store, monkeypatch):
    with _local_request(store):
        first, _ = _write_project(
            store, store["principal"], scope=_scope(brand_focus_id="brand-a"),
            artifact_id="ART-0000000000000001",
        )
        second, _ = _write_project(
            store, store["principal"], scope=_scope(brand_focus_id="brand-b"),
            artifact_id="ART-0000000000000002",
        )
    reopened = DatabaseRepository(str(store["db_path"]))
    monkeypatch.setattr(artifacts, "get_repository", lambda: reopened)
    with _local_request(store):
        a = _list(store, store["principal"], _scope(brand_focus_id="brand-a"))
        b = _list(store, store["principal"], _scope(brand_focus_id="brand-b"))
    assert a["status"] == b["status"] == "ok"
    assert [item["artifact_id"] for item in a["projects"]] == [first["artifact_id"]]
    assert [item["artifact_id"] for item in b["projects"]] == [second["artifact_id"]]
    assert set(a["projects"][0]) == {
        "artifact_id", "output_kind", "created_at", "updated_at", "status",
        "title", "project_revision", "render_state",
    }
    assert second["artifact_id"] not in repr(a)


def test_account_projects_are_filtered_by_actor_without_owner_metadata(store):
    first_actor, second_actor = {"id": 1, "role": "admin"}, {"id": 2, "role": "admin"}
    scope = _scope()
    first, _ = _write_project(
        store, first_actor, scope=scope, artifact_id="ART-0000000000000011",
    )
    second, _ = _write_project(
        store, second_actor, scope=scope, artifact_id="ART-0000000000000012",
    )
    a, b = _list(store, first_actor, scope), _list(store, second_actor, scope)
    assert [item["artifact_id"] for item in a["projects"]] == [first["artifact_id"]]
    assert [item["artifact_id"] for item in b["projects"]] == [second["artifact_id"]]
    assert second["artifact_id"] not in repr(a) and first["artifact_id"] not in repr(b)
    assert "actor_id" not in repr(a) and "relative_path" not in repr(a)


def test_keyset_pages_are_stable_and_cursor_is_scope_bound(store):
    scope = _scope(brand_focus_id="brand-a")
    actor = store["principal"]
    ids = [f"ART-{number:016x}" for number in (31, 32, 33)]
    with _local_request(store):
        for artifact_id in ids:
            _write_project(store, actor, scope=scope, artifact_id=artifact_id)
        first = _list(store, actor, scope, limit=1)
        assert first["next_cursor"]
        with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_PROJECT_CURSOR_INVALID"):
            _list(store, actor, _scope(brand_focus_id="brand-b"), limit=1, cursor=first["next_cursor"])
        second = _list(store, actor, scope, limit=1, cursor=first["next_cursor"])
        third = _list(store, actor, scope, limit=1, cursor=second["next_cursor"])
    actual = [first["projects"][0]["artifact_id"], second["projects"][0]["artifact_id"],
              third["projects"][0]["artifact_id"]]
    assert actual == ids
    assert third["next_cursor"] is None


@pytest.mark.parametrize("damage", ["tampered", "missing"])
def test_damaged_package_is_incomplete_without_unverified_identifier(store, damage):
    scope, actor = _scope(brand_focus_id="brand-a"), store["principal"]
    with _local_request(store):
        record, package = _write_project(
            store, actor, scope=scope, artifact_id="ART-0000000000000041",
        )
        if damage == "missing":
            package.unlink()
        else:
            package.write_bytes(package.read_bytes() + b"tampered")
        result = _list(store, actor, scope)
    assert result["status"] == "integrity_incomplete"
    assert result["projects"] == []
    assert record["artifact_id"] not in repr(result)


def test_closed_workspace_denies_project_listing(store):
    store["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    with _local_request(store), pytest.raises(
        artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED",
    ):
        _list(store, store["principal"], _scope(brand_focus_id="brand-a"))


def test_empty_registry_read_does_not_create_artifact_schema(store):
    sqlite3.connect(store["db_path"]).close()
    with _local_request(store):
        result = _list(store, store["principal"], _scope(brand_focus_id="brand-a"))
    with sqlite3.connect(store["db_path"]) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        ).fetchall()
    assert result == {"status": "empty", "projects": [], "next_cursor": None}
    assert not any(row[0] == "lumenis_shared_artifacts" for row in tables)


def test_scan_incomplete_cursor_advances_without_claiming_empty(store):
    actor = store["principal"]
    with _local_request(store):
        for number in range(100):
            _write_project(
                store, actor, scope=_scope(brand_focus_id="brand-b"),
                artifact_id=f"ART-{number:016x}",
            )
        wanted, _ = _write_project(
            store, actor, scope=_scope(brand_focus_id="brand-a"),
            artifact_id="ART-0000000000000064",
        )
        first = _list(store, actor, _scope(brand_focus_id="brand-a"))
        second = _list(
            store, actor, _scope(brand_focus_id="brand-a"), cursor=first["next_cursor"],
        )
    assert first["status"] == "scan_incomplete" and first["projects"] == []
    assert first["next_cursor"]
    assert second["status"] == "ok"
    assert [item["artifact_id"] for item in second["projects"]] == [wanted["artifact_id"]]


def test_scan_byte_budget_advances_after_verified_project(store, monkeypatch):
    scope, actor = _scope(brand_focus_id="brand-a"), store["principal"]
    with _local_request(store):
        first, _ = _write_project(store, actor, scope=scope, artifact_id="ART-0000000000000071")
        second, _ = _write_project(store, actor, scope=scope, artifact_id="ART-0000000000000072")
        monkeypatch.setattr(
            artifacts, "_CONTENT_PROJECT_LIST_VERIFY_BYTES",
            first["size_bytes"] + second["size_bytes"] - 1,
        )
        page1 = _list(store, actor, scope, limit=2)
        page2 = _list(store, actor, scope, limit=2, cursor=page1["next_cursor"])
    assert page1["status"] == "scan_incomplete"
    assert [item["artifact_id"] for item in page1["projects"]] == [first["artifact_id"]]
    assert page1["next_cursor"]
    assert [item["artifact_id"] for item in page2["projects"]] == [second["artifact_id"]]
