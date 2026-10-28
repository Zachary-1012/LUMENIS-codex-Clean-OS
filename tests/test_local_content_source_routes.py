"""Real isolated import/confirmation/read API without any account records."""
import ast
import hashlib
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import zipfile
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from flask import Flask, jsonify, request

from lumenis.system import security
from lumenis.system.security import permission as p
from tests.test_content_project_storage import media_store, rows  # noqa: F401 -- registers the shared pytest fixture.

HEADERS = {"X-Domain-Id": "BMP", "X-Product-Id": "ZBMP", "X-Lumenis-Action": "WRITE"}
SHARED_SCOPE = {"scope_kind": "shared_workspace", "version": 1}
SHARED_HEADERS = {
    "X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE),
    "X-Lumenis-Action": "WRITE",
}


@pytest.fixture
def local_client(media_store, monkeypatch):
    import experience_runtime
    import lumenis.auth.service
    from lumenis.shared.database import migrations

    media_store["gate"].revoke_permission(p.PermissionLevel.COMMIT)
    monkeypatch.setattr(security, "get_permission_gate", lambda: media_store["gate"])
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({"media-test": "public-isolated-test-key"}))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "media-test")
    with media_store["repository"].connect() as connection:
        connection.execute("DROP TABLE v4_users")
        migrations.migration_16_to_17(connection)
    monkeypatch.setattr(lumenis.auth.service, "get_current_user", lambda: None)
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    app.register_blueprint(experience_runtime.experience_bp)
    # Execute the exact global guard, without unrelated import-time app startups.
    tree = ast.parse(Path("app.py").read_text(encoding="utf-8-sig"))
    resolver = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "_pg_resolve_operation_type")
    guard = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "_permission_gate_write_check")
    guard.decorator_list = []
    namespace = dict(request=request, jsonify=jsonify, _PG_WRITE_METHODS={"POST", "PUT", "PATCH", "DELETE"},
                     _PG_BYPASS_PATHS=set(), _pg=media_store["gate"],
                     re=re, OperationType=p.OperationType)
    exec(compile(ast.Module(body=[resolver], type_ignores=[]), "app.py", "exec"), namespace)
    exec(compile(ast.Module(body=[guard], type_ignores=[]), "app.py", "exec"), namespace)
    app.before_request(namespace["_permission_gate_write_check"])
    app.add_url_rule("/api/experience/content-sources/wrong", "wrong_handler", lambda: {"wrong": True}, methods=["POST"])
    fence = security.get_effect_fence()
    fence.clear_for_testing()
    yield app.test_client(), media_store, app
    fence.clear_for_testing()


def upload(client, store, *, headers=None, data=None):
    return client.post("/api/experience/content-sources?filename=voice.wav",
                       headers=HEADERS if headers is None else headers,
                       data=store["source"].read_bytes() if data is None else data,
                       content_type="application/octet-stream")


def pending(client, store):
    response = upload(client, store)
    assert response.status_code == 403, response.get_json()
    body = response.get_json()
    assert body["requires_approval"] is True
    assert body["confirmation"]["body_sha256"] == hashlib.sha256(store["source"].read_bytes()).hexdigest()
    assert "approval_token" not in json.dumps(body)
    assert rows(store) == []
    assert not list(store["root"].iterdir())
    return body["confirmation"]["confirmation_id"]


def confirm(client, confirmation_id, *, confirmed=True, headers=None):
    return client.post(f"/api/experience/content-source-confirmations/{confirmation_id}",
                       json={"confirmed": confirmed}, headers=HEADERS if headers is None else headers)


def test_real_open_workspace_import_reopen_without_accounts(local_client):
    client, store, _app = local_client
    confirmation = pending(client, store)
    assert confirm(client, confirmation).status_code == 200
    result = upload(client, store)
    assert result.status_code == 201, result.get_json()
    body = result.get_json()
    assert body["evidence_recorded"] is True
    assert body["publish_status"] == "not_performed"
    artifact_id = body["result"]["artifact"]["artifact_id"]
    reopened = client.get(f"/api/experience/content-sources/{artifact_id}", headers=HEADERS)
    assert reopened.status_code == 200, reopened.get_json()
    assert reopened.get_json()["result"]["asset"] == body["result"]["asset"]
    assert len(rows(store)) == 1
    assert not store["gate"].has_permission(p.PermissionLevel.COMMIT)
    # Approval is consumed. Another upload must ask again, not duplicate silently.
    assert upload(client, store).status_code == 403
    assert len(rows(store)) == 1


def test_original_media_preview_is_version_bound_and_read_only(local_client):
    client, store, app = local_client
    confirmation = pending(client, store)
    assert confirm(client, confirmation).status_code == 200
    imported = upload(client, store).get_json()["result"]
    artifact_id = imported["artifact"]["artifact_id"]
    digest = imported["asset"]["sha256"]
    route = f"/api/experience/content-sources/{artifact_id}"
    before = rows(store)
    preview = client.get(f"{route}?format=media&sha256={digest}", headers=HEADERS)
    assert preview.status_code == 200, preview.get_json()
    assert preview.data == store["source"].read_bytes()
    assert preview.content_type == "audio/wav"
    assert preview.headers["Cache-Control"] == "private, no-store"
    assert preview.headers["X-Content-Type-Options"] == "nosniff"
    assert "inline" in preview.headers["Content-Disposition"]
    for query in ("format=media", f"format=media&sha256={'0' * 64}",
                  f"format=media&sha256={digest}&sha256={digest}",
                  f"format=media&format=json&sha256={digest}"):
        response = client.get(f"{route}?{query}", headers=HEADERS)
        assert response.status_code == 400
        assert response.is_json
    wrong_scope = {**HEADERS, "X-Domain-Id": "CTH", "X-Product-Id": "CTH"}
    assert client.get(f"{route}?format=media&sha256={digest}", headers=wrong_scope).status_code == 403
    assert client.get(f"{route}?format=media&sha256={digest}",
                      headers={**HEADERS, "Origin": "https://external.invalid"}).status_code == 401
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    assert client.get(f"{route}?format=media&sha256={digest}", headers=HEADERS).status_code == 401
    assert rows(store) == before


def test_original_media_preview_rejects_changed_source_package(local_client):
    client, store, _ = local_client
    confirmation = pending(client, store)
    assert confirm(client, confirmation).status_code == 200
    imported = upload(client, store).get_json()["result"]
    artifact_id = imported["artifact"]["artifact_id"]
    digest = imported["asset"]["sha256"]
    import shared_artifacts
    record = shared_artifacts._artifact_record(artifact_id)
    path = store["root"] / record["relative_path"]
    route = f"/api/experience/content-sources/{artifact_id}?format=media&sha256={digest}"
    assert client.head(route, headers=HEADERS).status_code == 200
    original_stat = path.stat()
    changed = bytearray(path.read_bytes())
    changed[-1] ^= 1
    path.write_bytes(changed)
    os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    response = client.get(f"/api/experience/content-sources/{artifact_id}?format=media&sha256={digest}",
                          headers=HEADERS)
    assert response.status_code == 400
    assert response.get_json()["code"] == "CONTENT_SOURCE_INTEGRITY_FAILED"


def test_media_ranges_head_and_query_context_preserve_source(local_client):
    client, store, app = local_client
    confirmation = pending(client, store)
    assert confirm(client, confirmation).status_code == 200
    result = upload(client, store).get_json()["result"]
    digest = result["asset"]["sha256"]
    route = f'/api/experience/content-sources/{result["artifact"]["artifact_id"]}'
    query = {"format": "media", "sha256": digest, "context": json.dumps({
        "X-Domain-Id": "BMP", "X-Product-Id": "ZBMP",
    })}
    raw = store["source"].read_bytes()
    before = rows(store)
    head = client.head(route, query_string=query)
    assert head.status_code == 200
    assert head.data == b""
    assert head.content_length == len(raw)
    assert head.headers["Accept-Ranges"] == "bytes"
    assert head.headers["ETag"] == f'"{digest}"'
    for requested, start, stop in [("bytes=8-15", 8, 16), ("bytes=-12", len(raw) - 12, len(raw)),
                                    ("bytes=20-", 20, len(raw))]:
        response = client.get(route, query_string=query, headers={"Range": requested})
        assert response.status_code == 206
        assert response.data == raw[start:stop]
        assert response.content_length == stop - start
        assert response.headers["Content-Range"] == f"bytes {start}-{stop - 1}/{len(raw)}"
    for requested in (f"bytes={len(raw)}-", "bytes=4-2", "bytes=0-1,4-5", "items=0-1"):
        response = client.get(route, query_string=query, headers={"Range": requested})
        assert response.status_code == 416
        assert response.headers["Content-Range"] == f"bytes */{len(raw)}"
        assert response.data == b""
    stale_range = client.get(route, query_string=query, headers={"Range": "bytes=4-9", "If-Range": '"old"'})
    assert stale_range.status_code == 200 and stale_range.data == raw
    assert client.head(route, query_string={**query, "context": json.dumps({
        "X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE),
    })}).status_code == 200
    assert client.get(route, query_string=query, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.get(route, query_string=query, headers={"X-Domain-Id": "CTH"}).status_code == 400
    for context in ('{"actor_id":1}', '{"X-Domain-Id":"BMP","X-Domain-Id":"CTH"}', '[]'):
        assert client.get(route, query_string={**query, "context": context}).status_code == 400
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    assert client.get(route, query_string=query, headers={"Range": "bytes=0-9"}).status_code == 401
    assert rows(store) == before


def test_range_stream_rechecks_permission_and_closes_on_disconnect(local_client):
    client, store, app = local_client
    with wave.open(str(store["source"]), "wb") as audio:
        audio.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\0\0" * 600000)
    confirmation = pending(client, store)
    assert confirm(client, confirmation).status_code == 200
    result = upload(client, store).get_json()["result"]
    route = f'/api/experience/content-sources/{result["artifact"]["artifact_id"]}'
    query = {"format": "media", "sha256": result["asset"]["sha256"]}
    response = client.get(route, query_string=query, headers=HEADERS, buffered=False)
    assert response.status_code == 200, response.get_json()
    stream = iter(response.response)
    assert len(next(stream)) < store["source"].stat().st_size
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    with pytest.raises(ValueError, match="AUTH_REQUIRED"):
        next(stream)
    response.close()
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    resumed = client.get(route, query_string=query, headers={**HEADERS, "Range": "bytes=-32"})
    assert resumed.status_code == 206
    assert resumed.data == store["source"].read_bytes()[-32:]
    interrupted = client.get(route, query_string=query, headers=HEADERS, buffered=False)
    interrupted.close()
    assert client.head(route, query_string=query, headers=HEADERS).status_code == 200


def test_cancel_cannot_be_replayed_and_can_start_fresh(local_client):
    client, store, _app = local_client
    confirmation = pending(client, store)
    assert confirm(client, confirmation, confirmed=False).status_code == 200
    assert confirm(client, confirmation).status_code == 403
    fresh = pending(client, store)
    assert fresh != confirmation
    assert confirm(client, fresh).status_code == 200
    assert upload(client, store).status_code == 201


def test_changed_bytes_cannot_borrow_confirmation(local_client):
    client, store, _app = local_client
    confirmation = pending(client, store)
    assert confirm(client, confirmation).status_code == 200
    changed = bytearray(store["source"].read_bytes())
    changed[-1] ^= 1
    assert upload(client, store, data=bytes(changed)).status_code == 403
    assert rows(store) == []
    assert upload(client, store).status_code == 201


def test_domain_change_or_workspace_closure_cannot_confirm(local_client):
    client, store, app = local_client
    confirmation = pending(client, store)
    assert confirm(client, confirmation, headers={**HEADERS, "X-Domain-Id": "CTH", "X-Product-Id": "CTH"}).status_code == 403
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    assert confirm(client, confirmation).status_code == 401
    assert rows(store) == []


@pytest.mark.parametrize("extra", [
    {"Origin": "https://external.invalid"}, {"Origin": "null"},
    {"Sec-Fetch-Site": "cross-site"}, {"X-Forwarded-For": "127.0.0.1"},
])
def test_ineligible_request_has_no_confirmation_or_file(local_client, extra):
    client, store, _app = local_client
    response = upload(client, store, headers={**HEADERS, **extra})
    assert response.status_code in {401, 403}
    assert "confirmation" not in response.get_json()
    assert rows(store) == []
    assert not store["root"].exists()


def test_only_registered_handler_may_use_handler_owned_permission(local_client):
    client, store, _app = local_client
    assert client.post("/api/experience/content-sources/wrong").status_code == 403
    assert rows(store) == []


def test_observed_size_limit_cleans_up_without_import(local_client, monkeypatch):
    import shared_artifacts

    client, store, _app = local_client
    monkeypatch.setattr(shared_artifacts, "content_media_resource_budget", lambda: {
        "available_bytes": 65536 + 32, "storage_capacity_bytes": 65536 + 32,
        "chunk_bytes": 16, "buffer_bytes": 16, "disk_reserve_bytes": 0, "concurrent_jobs": 2})
    response = upload(client, store)
    assert response.status_code == 507
    assert rows(store) == []


def imported_audio_project(client, store):
    from lumenis.shared.content_creation.video_editing import (
        Timeline,
        fingerprint_local_media,
    )

    confirmation = pending(client, store)
    assert confirm(client, confirmation).status_code == 200
    imported = upload(client, store).get_json()["result"]
    asset = fingerprint_local_media(store["source"])
    assert imported["asset"]["asset_id"] == asset.asset_id
    timeline = Timeline.from_assets([asset]).add_audio_track("voice", audio_role="voiceover")
    timeline = timeline.add_clip(asset.asset_id, track_id="voice", source_out=.4)
    return {
        "asset_refs": [imported["artifact"]["artifact_id"]], "timeline": timeline.to_dict(),
        "output_kind": "audio",
    }


def imported_shared_audio_project(client, store):
    from lumenis.shared.content_creation.video_editing import Timeline, fingerprint_local_media

    confirmation = shared_upload(client, store).get_json()["confirmation"]
    assert confirm(client, confirmation["confirmation_id"], headers=SHARED_HEADERS).status_code == 200
    imported = shared_upload(client, store).get_json()["result"]
    asset = fingerprint_local_media(store["source"])
    assert imported["asset"]["asset_id"] == asset.asset_id
    timeline = Timeline.from_assets([asset]).add_audio_track("voice", audio_role="voiceover")
    timeline = timeline.add_clip(asset.asset_id, track_id="voice", source_out=.4)
    return {"asset_refs": [imported["artifact"]["artifact_id"]],
            "timeline": timeline.to_dict(), "output_kind": "audio"}


def export_project(client, payload):
    return client.post("/api/experience/content-projects/export", headers=HEADERS,
                       json={"action_type": "EXPORT", "input": payload})


def export_shared_project(client, payload):
    return client.post(
        "/api/experience/content-projects/export", headers=SHARED_HEADERS,
        json={"action_type": "EXPORT", "input": payload},
    )


def shared_upload(client, store, *, data=None, headers=None):
    return client.post(
        "/api/experience/content-sources?filename=voice.wav",
        headers=SHARED_HEADERS if headers is None else headers,
        data=store["source"].read_bytes() if data is None else data,
        content_type="application/octet-stream",
    )


def install_exact_bytes_fingerprint_stub(monkeypatch, store):
    """Isolate Permission/commit tests from the unavailable system FFprobe binary."""
    import shared_artifacts
    from lumenis.shared.content_creation.video_editing import (
        _MEDIA_ASSET_FACTORY_TOKEN,
        MediaAsset,
    )

    digest = hashlib.sha256(store["source"].read_bytes()).hexdigest()

    def fingerprint(path):
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
        return MediaAsset(
            asset_id=f"MEDIA-{digest[:16]}", filename=Path(path).name,
            sha256=digest, duration_sec=0.5, path=str(path), has_video=False,
            audio_stream_count=1, _factory_token=_MEDIA_ASSET_FACTORY_TOKEN,
        )

    monkeypatch.setattr(shared_artifacts, "_fingerprint_content_source", fingerprint)


def test_shared_content_project_real_api_save_reopen_revise_and_export(local_client):
    client, store, app = local_client
    pending_response = shared_upload(client, store)
    assert pending_response.status_code == 403, pending_response.get_json()
    pending = pending_response.get_json().get("confirmation")
    assert pending is not None, pending_response.get_json()
    assert pending["resource"].startswith("content-source-import:shared-workspace:v1:")
    assert "approval_token" not in json.dumps(pending_response.get_json())
    assert rows(store) == []

    confirmed = client.post(
        f"/api/experience/content-source-confirmations/{pending['confirmation_id']}",
        json={"confirmed": True}, headers=SHARED_HEADERS,
    )
    assert confirmed.status_code == 200, confirmed.get_json()
    imported = shared_upload(client, store)
    assert imported.status_code == 201, imported.get_json()
    imported_data = imported.get_json()["result"]
    source_id = imported_data["artifact"]["artifact_id"]
    assert (imported_data["artifact"]["product_id"],
            imported_data["artifact"]["domain_id"]) == ("SHARED", "content")
    assert imported_data["asset"]["rights_status"] == "unknown"
    assert imported.get_json()["evidence_recorded"] is True

    from lumenis.shared.evidence import EvidenceStore
    from lumenis.system.security.permission import resolve_local_workspace_principal

    evidence_store = EvidenceStore()
    import_evidence = [
        evidence for evidence in evidence_store.list_evidence(
            source_type="skill_execution", domain_id="content", product_id="SHARED",
        ) if evidence.source_id == imported.get_json()["execution_id"]
    ]
    assert len(import_evidence) == 1
    assert import_evidence[0].subject_scope == "shared_workspace:workspace:local"
    assert import_evidence[0].collection_metadata["shared_workspace_execution"] == {
        "kind": "skill_execution_trace", "canonical_fact": False,
        "scope": SHARED_SCOPE,
        "actor": {"principal_kind": "local_workspace", "principal_ref": "workspace:local"},
    }
    with app.test_request_context(
        "/", environ_base={"REMOTE_ADDR": "127.0.0.1"},
        headers={"Host": "localhost"},
    ):
        local_principal = resolve_local_workspace_principal(module="content", action="read")
        readback = evidence_store.get_shared_skill_execution_evidence(
            import_evidence[0].evidence_id, actor=local_principal,
            shared_workspace_scope=SHARED_SCOPE,
        )
    assert readback is not None
    with pytest.raises(PermissionError, match="SHARED_SKILL_EVIDENCE_PERMISSION_DENIED"):
        evidence_store.get_shared_skill_execution_evidence(
            import_evidence[0].evidence_id, actor={"id": 77},
            shared_workspace_scope=SHARED_SCOPE,
        )

    source_detail = client.get(
        f"/api/experience/content-sources/{source_id}",
        headers={"X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE)},
    )
    assert source_detail.status_code == 200, source_detail.get_json()
    assert source_detail.get_json()["result"]["asset"] == imported_data["asset"]

    from lumenis.shared.content_creation.video_editing import (
        Timeline,
        fingerprint_local_media,
    )

    asset = fingerprint_local_media(store["source"])
    timeline = Timeline.from_assets([asset]).add_audio_track("voice", audio_role="voiceover")
    timeline = timeline.add_clip(asset.asset_id, track_id="voice", source_out=.4)
    payload = {
        "asset_refs": [source_id], "timeline": timeline.to_dict(), "output_kind": "audio",
    }
    first = export_shared_project(client, payload)
    assert first.status_code == 200, first.get_json()
    first_result = first.get_json()["result"]
    project_id = first_result["artifact"]["artifact_id"]
    assert (first_result["artifact"]["product_id"],
            first_result["artifact"]["domain_id"]) == ("SHARED", "content")
    assert first.get_json()["evidence_recorded"] is True
    export_evidence = [
        evidence for evidence in evidence_store.list_evidence(
            source_type="skill_execution", domain_id="content", product_id="SHARED",
        ) if evidence.source_id == first.get_json()["execution_id"]
    ]
    assert len(export_evidence) == 1
    assert export_evidence[0].subject_scope == "shared_workspace:workspace:local"

    detail_url = f"/api/experience/content-projects/{project_id}"
    first_detail = client.get(detail_url, headers={
        "X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE),
    })
    assert first_detail.status_code == 200, first_detail.get_json()
    project = first_detail.get_json()["project"]["project"]
    assert project["source_artifact_refs"] == [source_id]
    assert project["rights"]["state"] == "unknown"
    assert project["context"]["shared_workspace_scope"] == SHARED_SCOPE

    listed = client.get("/api/experience/content-projects", headers={
        "X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE),
    })
    assert listed.status_code == 200, listed.get_json()
    assert [item["artifact_id"] for item in listed.get_json()["projects"]] == [project_id]
    package_url = first_detail.get_json()["package_url"]
    media_url = first_detail.get_json()["preview_url"]
    first_package = client.get(package_url, headers={
        "X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE),
    })
    assert first_package.status_code == 200 and zipfile.is_zipfile(io.BytesIO(first_package.data))
    media = client.get(media_url, headers={
        "X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE),
    })
    assert media.status_code == 200 and media.data[:4] == b"RIFF"

    revised_timeline = timeline.add_audio_track("music", audio_role="bgm")
    revised = export_shared_project(client, {
        **payload, "timeline": revised_timeline.to_dict(), "previous_artifact_id": project_id,
    })
    assert revised.status_code == 200, revised.get_json()
    revised_id = revised.get_json()["result"]["artifact"]["artifact_id"]
    reopened = client.get(f"/api/experience/content-projects/{revised_id}", headers={
        "X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE),
    })
    assert reopened.status_code == 200, reopened.get_json()
    assert reopened.get_json()["project"]["project"]["parent_artifact_id"] == project_id
    assert reopened.get_json()["project"]["project"]["timeline"]["version"] > project["timeline"]["version"]
    assert client.get(package_url, headers={
        "X-Lumenis-Workspace-Scope": json.dumps(SHARED_SCOPE),
    }).data == first_package.data


def test_shared_content_export_task_real_route_result_reopens_same_editable_project(
    local_client, monkeypatch, tmp_path,
):
    client, store, _app = local_client
    from lumenis.system.collector.guard import task_queue

    monkeypatch.setattr(task_queue, "DEFAULT_PATH", str(tmp_path / "content-export-queue.sqlite3"))
    payload = imported_shared_audio_project(client, store)
    request_id = "e" * 32
    submitted = client.post(
        "/api/experience/content-projects/export/tasks", headers=SHARED_HEADERS,
        json={"action_type": "EXPORT", "request_id": request_id,
              "task": "导出可继续编辑的采访音频工程", "input": payload},
    )
    assert submitted.status_code == 202, submitted.get_json()
    task = submitted.get_json()["task"]
    assert task["task_kind"] == "content_project_export"
    assert task["status"] in {"pending", "running", "completed"}
    assert "asset_paths" not in json.dumps(submitted.get_json())
    assert "approval_token" not in json.dumps(submitted.get_json())

    for _ in range(500):
        response = client.get(
            f"/api/experience/content-projects/export/tasks/{task['task_id']}",
            headers=SHARED_HEADERS,
        )
        assert response.status_code == 200, response.get_json()
        task = response.get_json()["task"]
        if (task["status"] in {"failed", "cancelled", "interrupted"}
                or task["status"] == "completed" and isinstance(task.get("result"), dict)
                and type(task["result"].get("evidence_recorded")) is bool):
            break
        import time
        time.sleep(0.02)
    assert task["status"] == "completed", task
    result = task["result"]
    assert result["status"] == "rendered_staged"
    assert result["evidence_recorded"] is True
    artifact_id = result["artifact"]["artifact_id"]
    assert result["artifact"]["source_execution_id"] == str(task["task_id"])
    assert result["project"]["source_artifact_refs"] == payload["asset_refs"]
    assert result["project"]["timeline"] == payload["timeline"]
    assert result["package_url"] == f"/api/experience/content-projects/{artifact_id}/package"
    package = client.get(result["package_url"], headers=SHARED_HEADERS)
    assert package.status_code == 200 and zipfile.is_zipfile(io.BytesIO(package.data))
    reopened = client.get(f"/api/experience/content-projects/{artifact_id}", headers=SHARED_HEADERS)
    assert reopened.status_code == 200, reopened.get_json()
    assert reopened.get_json()["project"]["project"] == result["project"]
    assert reopened.get_json()["project"]["render"] == result["render"]


def test_shared_content_export_rejects_cross_kind_parent_before_enqueue(
    local_client, monkeypatch, tmp_path,
):
    client, store, _app = local_client
    from lumenis.system.collector.guard import task_queue

    queue_path = tmp_path / "content-export-type-change.sqlite3"
    monkeypatch.setattr(task_queue, "DEFAULT_PATH", str(queue_path))
    payload = imported_shared_audio_project(client, store)
    parent = export_shared_project(client, {
        **payload, "output_kind": "video", "render_media": False,
        "title": "视频工程草稿",
    })
    assert parent.status_code == 200, parent.get_json()
    parent_id = parent.get_json()["result"]["artifact"]["artifact_id"]
    artifacts_before = rows(store)
    assert len(artifacts_before) == 2

    synchronous = export_shared_project(client, {
        **payload, "output_kind": "audio", "previous_artifact_id": parent_id,
        "title": "音频新工程",
    })
    assert synchronous.status_code == 400, synchronous.get_json()
    assert synchronous.get_json()["code"] == "CONTENT_PROJECT_TYPE_CHANGE_REQUIRES_NEW_PROJECT"
    assert rows(store) == artifacts_before

    rejected = client.post(
        "/api/experience/content-projects/export/tasks", headers=SHARED_HEADERS,
        json={"action_type": "EXPORT", "request_id": "a" * 32,
              "task": "从视频工程另建音频工程", "input": {
                  **payload, "output_kind": "audio", "previous_artifact_id": parent_id,
                  "title": "音频新工程",
                  "delivery_options": {"audio_formats": ["mp3"]},
              }},
    )
    assert rejected.status_code == 400, rejected.get_json()
    assert rejected.get_json()["code"] == "CONTENT_PROJECT_TYPE_CHANGE_REQUIRES_NEW_PROJECT"
    assert rows(store) == artifacts_before
    assert not queue_path.exists()


def test_shared_content_export_task_reopens_cross_kind_project_lineage(local_client, monkeypatch, tmp_path):
    client, store, _app = local_client
    from lumenis.system.collector.guard import task_queue

    queue_path = tmp_path / "cross-kind-project-lineage.sqlite3"
    monkeypatch.setattr(task_queue, "DEFAULT_PATH", str(queue_path))
    payload = imported_shared_audio_project(client, store)
    source_video = export_shared_project(client, {
        **payload, "output_kind": "video", "render_media": False,
        "title": "原视频工程来源",
    })
    assert source_video.status_code == 200, source_video.get_json()
    source_video_id = source_video.get_json()["result"]["artifact"]["artifact_id"]

    derived_input = {
        **payload,
        "output_kind": "audio",
        "previous_artifact_id": None,
        "source_project_artifact_refs": [source_video_id],
        "render_media": False,
        "title": "独立音频工程",
    }
    submitted = client.post(
        "/api/experience/content-projects/export/tasks", headers=SHARED_HEADERS,
        json={"action_type": "EXPORT", "request_id": "9" * 32,
              "task": "从视频工程另建可继续编辑的音频工程", "input": derived_input},
    )
    assert submitted.status_code == 202, submitted.get_json()
    task_id = submitted.get_json()["task"]["task_id"]
    for _ in range(500):
        response = client.get(
            f"/api/experience/content-projects/export/tasks/{task_id}", headers=SHARED_HEADERS,
        )
        assert response.status_code == 200, response.get_json()
        task = response.get_json()["task"]
        if task["status"] in {"failed", "cancelled", "interrupted"} or (
                task["status"] == "completed" and isinstance(task.get("result"), dict)
                and type(task["result"].get("evidence_recorded")) is bool):
            break
        import time
        time.sleep(.02)
    assert task["status"] == "completed", task
    result = task["result"]
    audio_id = result["artifact"]["artifact_id"]
    assert result["project"]["output_kind"] == "audio"
    assert result["project"]["parent_artifact_id"] is None
    assert result["project"]["source_project_artifact_refs"] == [source_video_id]
    reopened = client.get(f"/api/experience/content-projects/{audio_id}", headers=SHARED_HEADERS)
    assert reopened.status_code == 200, reopened.get_json()
    assert reopened.get_json()["project"]["project"]["source_project_artifact_refs"] == [source_video_id]
    assert reopened.get_json()["project"]["project"] == result["project"]
    listed = client.get("/api/experience/content-projects", headers=SHARED_HEADERS)
    assert listed.status_code == 200, listed.get_json()
    summary = next(item for item in listed.get_json()["projects"] if item["artifact_id"] == audio_id)
    assert summary["source_project_artifact_refs"] == [source_video_id]

    before = [tuple(row) for row in rows(store)]
    invalid = export_shared_project(client, {
        **derived_input, "source_project_artifact_refs": ["ART-0000000000000000"],
        "title": "不得写入的无效来源",
    })
    assert invalid.status_code == 404, invalid.get_json()
    assert invalid.get_json()["code"] == "CONTENT_PROJECT_NOT_FOUND"
    assert [tuple(row) for row in rows(store)] == before


def test_shared_content_export_task_reports_safe_stage_error(local_client, monkeypatch, tmp_path):
    client, store, _app = local_client
    from lumenis.system.collector.guard import task_queue
    import shared_artifacts

    monkeypatch.setattr(task_queue, "DEFAULT_PATH", str(tmp_path / "content-export-safe-error.sqlite3"))
    payload = imported_shared_audio_project(client, store)
    artifacts_before = rows(store)

    def failed_stage(*_args, **_kwargs):
        raise shared_artifacts.LocalArtifactError("CONTENT_RENDER_UNAVAILABLE")

    monkeypatch.setattr(shared_artifacts, "stage_timeline_artifact", failed_stage)
    submitted = client.post(
        "/api/experience/content-projects/export/tasks", headers=SHARED_HEADERS,
        json={"action_type": "EXPORT", "request_id": "b" * 32,
              "task": "验证媒体处理失败可读回", "input": payload},
    )
    assert submitted.status_code == 202, submitted.get_json()
    task_id = submitted.get_json()["task"]["task_id"]
    for _ in range(200):
        readback = client.get(
            f"/api/experience/content-projects/export/tasks/{task_id}",
            headers=SHARED_HEADERS,
        )
        assert readback.status_code == 200, readback.get_json()
        task = readback.get_json()["task"]
        if task["status"] in {"failed", "cancelled", "interrupted"}:
            break
        import time
        time.sleep(0.01)
    assert task["status"] == "failed", task
    assert task["error_code"] == "CONTENT_RENDER_UNAVAILABLE"
    assert task["result"] is None
    assert str(store["root"]) not in json.dumps(readback.get_json())
    assert rows(store) == artifacts_before


def test_shared_content_export_task_pending_cancel_and_request_id_conflict(
    local_client, monkeypatch, tmp_path,
):
    client, store, _app = local_client
    import experience_runtime
    from lumenis.system.collector.guard import task_queue

    monkeypatch.setattr(task_queue, "DEFAULT_PATH", str(tmp_path / "content-export-cancel.sqlite3"))
    monkeypatch.setattr(experience_runtime, "_start_content_project_export_worker",
                        lambda *_args, **_kwargs: None)
    payload = imported_shared_audio_project(client, store)
    request_id = "c" * 32
    body = {"action_type": "EXPORT", "request_id": request_id, "input": payload}
    submitted = client.post("/api/experience/content-projects/export/tasks",
                            headers=SHARED_HEADERS, json=body)
    assert submitted.status_code == 202, submitted.get_json()
    task = submitted.get_json()["task"]
    assert task["status"] == "pending" and task["can_cancel"] is True
    newer = client.post("/api/experience/content-projects/export/tasks",
        headers=SHARED_HEADERS,
        json={**body, "request_id": "d" * 32},
    )
    assert newer.status_code == 202, newer.get_json()
    # A newer task under another binding must not occupy this actor's page or
    # hide its older task behind a global queue cursor.
    foreign_queue = task_queue.TaskQueue()
    foreign_queue.enqueue_once(
        "shared_content_project_export",
        {"request_id": "f" * 32, "request_digest": "a" * 64,
         "binding": {"actor_ref": "actor:unrelated", "scope_sha256": "b" * 64}},
        "c" * 64,
    )
    foreign_queue.close()
    listed = client.get("/api/experience/content-projects/export/tasks?limit=1",
                        headers=SHARED_HEADERS)
    assert listed.status_code == 200, listed.get_json()
    first_page = listed.get_json()
    assert [item["task_id"] for item in first_page["tasks"]] == [newer.get_json()["task"]["task_id"]]
    assert first_page["next_cursor"] is not None
    second_page = client.get(
        "/api/experience/content-projects/export/tasks?limit=1&cursor=" + first_page["next_cursor"],
        headers=SHARED_HEADERS,
    )
    assert second_page.status_code == 200, second_page.get_json()
    assert [item["task_id"] for item in second_page.get_json()["tasks"]] == [task["task_id"]]
    conflict = client.post("/api/experience/content-projects/export/tasks",
        headers=SHARED_HEADERS,
        json={**body, "input": {**payload, "title": "different immutable request"}})
    assert conflict.status_code == 409, conflict.get_json()
    assert conflict.get_json()["code"] == "CONTENT_EXPORT_REQUEST_ID_CONFLICT"
    cancelled = client.post(
        f"/api/experience/content-projects/export/tasks/{task['task_id']}/cancel",
        headers=SHARED_HEADERS, json={},
    )
    assert cancelled.status_code == 200, cancelled.get_json()
    assert cancelled.get_json()["task"]["status"] == "cancelled"
    assert cancelled.get_json()["task"]["result"] is None


def test_shared_content_export_task_running_cancel_finishes_after_skill_returns(
    local_client, monkeypatch, tmp_path,
):
    client, store, _app = local_client
    import threading
    import types
    from lumenis.shared.agents.skills import execution
    from lumenis.system.collector.guard import task_queue

    monkeypatch.setattr(task_queue, "DEFAULT_PATH", str(tmp_path / "content-export-running-cancel.sqlite3"))
    payload = imported_shared_audio_project(client, store)
    entered = threading.Event()
    release = threading.Event()

    def skill_returns_after_cancel(**_kwargs):
        entered.set()
        if not release.wait(10):
            raise AssertionError("test did not release the skill result")
        return types.SimpleNamespace(
            status=types.SimpleNamespace(value="failed"),
            error="CONTENT_EXPORT_CANCELLED", evidence_record=None,
        )

    monkeypatch.setattr(execution, "run_execution_chain", skill_returns_after_cancel)
    request_id = "e" * 32
    submitted = client.post(
        "/api/experience/content-projects/export/tasks", headers=SHARED_HEADERS,
        json={"action_type": "EXPORT", "request_id": request_id,
              "task": "取消中的真实录屏工程导出", "input": payload},
    )
    assert submitted.status_code == 202, submitted.get_json()
    task_id = submitted.get_json()["task"]["task_id"]
    assert entered.wait(5), "worker never entered the existing skill execution path"
    try:
        cancelled = client.post(
            f"/api/experience/content-projects/export/tasks/{task_id}/cancel",
            headers=SHARED_HEADERS, json={},
        )
        assert cancelled.status_code == 200, cancelled.get_json()
        assert cancelled.get_json()["task"]["status"] == "canceling"
    finally:
        release.set()

    for _ in range(200):
        readback = client.get(
            f"/api/experience/content-projects/export/tasks/{task_id}",
            headers=SHARED_HEADERS,
        )
        assert readback.status_code == 200, readback.get_json()
        if readback.get_json()["task"]["status"] == "cancelled":
            break
        import time
        time.sleep(0.01)
    task = readback.get_json()["task"]
    assert task["status"] == "cancelled", task
    assert task["result"] is None


def test_shared_project_rejects_domain_source_without_exact_cross_scope_use(local_client):
    client, store, _app = local_client
    private_domain_project = imported_audio_project(client, store)
    assert len(rows(store)) == 1

    response = export_shared_project(client, private_domain_project)
    assert response.status_code == 403, response.get_json()
    assert response.get_json()["code"] == "CONTENT_SOURCE_USE_PERMISSION_REQUIRED"
    assert len(rows(store)) == 1


def test_shared_content_confirmation_cancel_and_boundary_rejection(local_client):
    client, store, app = local_client
    pending = shared_upload(client, store).get_json()["confirmation"]
    cancelled = client.post(
        f"/api/experience/content-source-confirmations/{pending['confirmation_id']}",
        json={"confirmed": False}, headers=SHARED_HEADERS,
    )
    assert cancelled.status_code == 200 and cancelled.get_json()["status"] == "cancelled"
    stale = client.post(
        f"/api/experience/content-source-confirmations/{pending['confirmation_id']}",
        json={"confirmed": True}, headers=SHARED_HEADERS,
    )
    assert stale.status_code == 403
    fresh = shared_upload(client, store).get_json()["confirmation"]
    assert fresh["confirmation_id"] != pending["confirmation_id"]

    mixed = shared_upload(client, store, headers={
        **SHARED_HEADERS, "X-Domain-Id": "CTH", "X-Product-Id": "CTH",
    })
    assert mixed.status_code == 400, mixed.get_json()
    assert mixed.get_json()["code"] == "SHARED_WORKSPACE_SCOPE_MIXED_CONTEXT"
    forged = shared_upload(client, store, headers={
        "X-Lumenis-Workspace-Scope": json.dumps({**SHARED_SCOPE, "actor_id": 77}),
        "X-Lumenis-Action": "WRITE",
    })
    assert forged.status_code == 400, forged.get_json()
    assert forged.get_json()["code"] == "SHARED_WORKSPACE_SCOPE_INVALID"
    impersonated = shared_upload(client, store, headers={
        **SHARED_HEADERS, "X-User-Id": "77",
    })
    assert impersonated.status_code in {401, 403}, impersonated.get_json()
    assert "confirmation" not in impersonated.get_json()
    assert rows(store) == []
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    closed = shared_upload(client, store)
    assert closed.status_code in {401, 403}, closed.get_json()
    assert closed.get_json()["code"] == "AUTH_REQUIRED"
    assert rows(store) == []


def test_shared_source_import_recovers_exact_artifact_after_evidence_failure(local_client, monkeypatch):
    client, store, _app = local_client
    from lumenis.shared.agents.skills import execution

    original_record = execution.record_execution_evidence
    attempts = 0

    def fail_once(context):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return {"ok": False, "error": "isolated evidence write failure"}
        return original_record(context)

    monkeypatch.setattr(execution, "record_execution_evidence", fail_once)
    first_pending = shared_upload(client, store).get_json()["confirmation"]
    assert client.post(
        f"/api/experience/content-source-confirmations/{first_pending['confirmation_id']}",
        json={"confirmed": True}, headers=SHARED_HEADERS,
    ).status_code == 200
    failed = shared_upload(client, store)
    assert failed.status_code == 503 and failed.get_json()["code"] == "EVIDENCE_RECORD_FAILED"
    assert len(rows(store)) == 1
    failed_execution_id = failed.get_json()["execution_id"]
    with store["repository"].connect() as connection:
        failure = connection.execute(
            "SELECT status,error FROM skill_executions WHERE execution_id=?",
            (failed_execution_id,),
        ).fetchone()
    assert failure["status"] == "failed" and failure["error"] == "EVIDENCE_RECORD_FAILED"

    retry_pending = shared_upload(client, store).get_json()["confirmation"]
    assert client.post(
        f"/api/experience/content-source-confirmations/{retry_pending['confirmation_id']}",
        json={"confirmed": True}, headers=SHARED_HEADERS,
    ).status_code == 200
    recovered = shared_upload(client, store)
    assert recovered.status_code == 201, recovered.get_json()
    assert recovered.get_json()["evidence_recorded"] is True
    assert len(rows(store)) == 1
    with store["repository"].connect() as connection:
        preserved_failure = connection.execute(
            "SELECT status,error FROM skill_executions WHERE execution_id=?",
            (failed_execution_id,),
        ).fetchone()
    assert preserved_failure["status"] == "failed"
    assert preserved_failure["error"] == "EVIDENCE_RECORD_FAILED"


def test_shared_import_confirmation_is_atomically_consumed_for_concurrent_posts(
    local_client, monkeypatch,
):
    client, store, app = local_client
    install_exact_bytes_fingerprint_stub(monkeypatch, store)
    confirmation = shared_upload(client, store).get_json()["confirmation"]
    assert client.post(
        f"/api/experience/content-source-confirmations/{confirmation['confirmation_id']}",
        json={"confirmed": True}, headers=SHARED_HEADERS,
    ).status_code == 200

    gate_permission = p.check_content_source_import_permission
    arrival = threading.Barrier(2)
    calls = threading.local()

    def synchronize_final_permission_check(*args, **kwargs):
        result = gate_permission(*args, **kwargs)
        count = getattr(calls, "count", 0) + 1
        calls.count = count
        if count == 3 and result.allowed:
            arrival.wait(timeout=10)
        return result

    monkeypatch.setattr(p, "check_content_source_import_permission", synchronize_final_permission_check)
    monkeypatch.setattr(security, "check_content_source_import_permission", synchronize_final_permission_check)

    def import_from_independent_client():
        with app.test_client() as concurrent_client:
            response = shared_upload(concurrent_client, store)
            return response.status_code, response.get_json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: import_from_independent_client(), range(2)))

    assert sum(status == 201 for status, _body in results) == 1, results
    assert sum(status in {403, 503} for status, _body in results) == 1, results
    artifact_ids = [
        body["result"]["artifact"]["artifact_id"]
        for status, body in results if status == 201
    ]
    assert len(artifact_ids) == 1
    assert len(rows(store)) == 1


def test_shared_import_commit_failure_releases_approval_for_retry(local_client, monkeypatch):
    client, store, _app = local_client
    install_exact_bytes_fingerprint_stub(monkeypatch, store)
    confirmation = shared_upload(client, store).get_json()["confirmation"]
    assert client.post(
        f"/api/experience/content-source-confirmations/{confirmation['confirmation_id']}",
        json={"confirmed": True}, headers=SHARED_HEADERS,
    ).status_code == 200

    import shared_artifacts

    register = shared_artifacts._register_artifact
    attempts = 0

    def fail_before_artifact_commit(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise sqlite3.OperationalError("isolated commit interruption")
        return register(**kwargs)

    monkeypatch.setattr(shared_artifacts, "_register_artifact", fail_before_artifact_commit)
    failed = shared_upload(client, store)
    assert failed.status_code == 503, failed.get_json()
    assert rows(store) == []

    retried = shared_upload(client, store)
    assert retried.status_code == 201, retried.get_json()
    assert retried.get_json()["evidence_recorded"] is True
    assert len(rows(store)) == 1


def test_shared_import_cross_process_artifact_key_conflict_returns_existing(
    local_client, monkeypatch,
):
    client, store, _app = local_client
    install_exact_bytes_fingerprint_stub(monkeypatch, store)
    pending_response = shared_upload(client, store)
    confirmation = pending_response.get_json()["confirmation"]
    assert client.post(
        f"/api/experience/content-source-confirmations/{confirmation['confirmation_id']}",
        json={"confirmed": True}, headers=SHARED_HEADERS,
    ).status_code == 200

    import shared_artifacts
    register = shared_artifacts._register_artifact

    approval_token = next(
        token for token, grant in store["gate"]._content_import_grants.items()
        if grant.confirmation_id == confirmation["confirmation_id"]
    )
    expected_artifact_id = shared_artifacts._shared_content_source_artifact_id(approval_token)
    assert len(expected_artifact_id) == 36
    committed_by_sibling = False
    observed_conflicts = []

    def register_from_sibling_process(**kwargs):
        nonlocal committed_by_sibling
        assert not committed_by_sibling
        child_code = (
            "import json, shutil, sys, uuid; from pathlib import Path; "
            "import shared_artifacts; from lumenis.shared.database import main_db_path; "
            "payload=json.load(sys.stdin); "
            "original=Path(payload['path']); "
            "sibling=original.with_name('sibling-'+uuid.uuid4().hex+'.zip'); "
            "shutil.copy2(original, sibling); payload['path']=sibling; "
            "shared_artifacts._register_artifact(**payload); print(main_db_path())"
        )
        child = subprocess.run(
            [sys.executable, "-X", "utf8", "-c", child_code],
            input=json.dumps({**kwargs, "path": str(kwargs["path"])}),
            text=True, encoding="utf-8", capture_output=True, cwd=os.getcwd(), check=False, timeout=30,
        )
        assert child.returncode == 0, child.stderr
        assert Path(child.stdout.strip()).resolve() == Path(
            store["repository"].db_path
        ).resolve()
        assert len(rows(store)) == 1
        committed_by_sibling = True
        # Make this process attempt the same commit so SQLite, rather than the
        # test, proves the cross-process primary-key conflict.
        try:
            return register(**kwargs)
        except sqlite3.IntegrityError as exc:
            observed_conflicts.append(exc)
            raise

    monkeypatch.setattr(shared_artifacts, "_register_artifact", register_from_sibling_process)
    response = shared_upload(client, store)
    assert len(observed_conflicts) == 1
    assert observed_conflicts[0].sqlite_errorname == "SQLITE_CONSTRAINT_PRIMARYKEY"
    assert response.status_code == 201, response.get_json()
    assert response.get_json()["result"]["artifact"]["artifact_id"] == expected_artifact_id
    assert response.get_json()["evidence_recorded"] is True
    assert len(rows(store)) == 1

    detail = client.get(
        f"/api/experience/content-sources/{expected_artifact_id}", headers=SHARED_HEADERS,
    )
    assert detail.status_code == 200, detail.get_json()
    assert detail.get_json()["result"]["asset"]["sha256"] == hashlib.sha256(
        store["source"].read_bytes()
    ).hexdigest()


def test_real_import_export_revision_and_reopen_api(local_client):
    client, store, app = local_client
    payload = imported_audio_project(client, store)
    first = export_project(client, payload)
    assert first.status_code == 200, first.get_json()
    body = first.get_json()
    assert body["evidence_recorded"] is True
    project_id = body["result"]["artifact"]["artifact_id"]
    detail_url = f"/api/experience/content-projects/{project_id}"
    first_detail = client.get(detail_url, headers=HEADERS)
    assert first_detail.status_code == 200, first_detail.get_json()
    package_url = first_detail.get_json()["package_url"]
    media_url = first_detail.get_json()["preview_url"]
    first_package = client.get(package_url, headers=HEADERS).data
    assert zipfile.is_zipfile(io.BytesIO(first_package))
    media = client.get(media_url, headers=HEADERS)
    assert media.status_code == 200 and media.data[:4] == b"RIFF"
    assert len(rows(store)) == 2
    unchanged = export_project(client, {**payload, "previous_artifact_id": project_id})
    assert unchanged.status_code == 400, unchanged.get_json()
    assert unchanged.get_json()["code"] == "CONTENT_PROJECT_PARENT_REVISION_REQUIRED"
    assert len(rows(store)) == 2
    # Revision must persist separately and preserve the earlier editable package.
    from lumenis.shared.content_creation.video_editing import (
        Timeline,
        fingerprint_local_media,
    )
    revised = Timeline.from_dict(payload["timeline"], assets=[fingerprint_local_media(store["source"])]).add_audio_track("music", audio_role="bgm")
    second = export_project(client, {**payload, "timeline": revised.to_dict(), "previous_artifact_id": project_id})
    assert second.status_code == 200, second.get_json()
    assert second.get_json()["result"]["artifact"]["artifact_id"] != project_id
    assert client.get(package_url, headers=HEADERS).data == first_package
    # Separate client reopens the same stored result without an account or transient upload.
    reopened = app.test_client().get(detail_url, headers=HEADERS)
    assert reopened.status_code == 200 and reopened.get_json() == first_detail.get_json()
    for url in (detail_url, package_url, media_url):
        denied = client.get(url, headers={**HEADERS, "X-Domain-Id": "CTH", "X-Product-Id": "CTH"})
        assert denied.status_code == 403, denied.get_json()
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    assert client.get(detail_url, headers=HEADERS).status_code == 401
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    assert client.get(package_url, headers=HEADERS).data == first_package
    assert len(rows(store)) == 3
    assert not store["gate"].has_permission(p.PermissionLevel.COMMIT)


def test_render_failure_preserves_source_and_explicit_retry(local_client, monkeypatch):
    import shared_artifacts

    client, store, _app = local_client
    payload = imported_audio_project(client, store)
    before = rows(store)
    with monkeypatch.context() as scoped:
        def unavailable(*args, **kwargs):
            raise shared_artifacts.LocalArtifactError("CONTENT_RENDER_UNAVAILABLE")
        scoped.setattr(shared_artifacts, "stage_timeline_artifact", unavailable)
        failed = export_project(client, payload)
    assert failed.status_code == 503, failed.get_json()
    assert rows(store) == before
    recovered = export_project(client, payload)
    assert recovered.status_code == 200, recovered.get_json()
    assert len(rows(store)) == 2
