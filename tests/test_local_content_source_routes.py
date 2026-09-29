"""Real isolated import/confirmation/read API without any account records."""
import ast
import hashlib
import json
import io
import zipfile
from pathlib import Path

import pytest
from flask import Flask, jsonify, request

from tests.test_content_project_storage import media_store, rows
from lumenis.system import security
from lumenis.system.security import permission as p


HEADERS = {"X-Domain-Id": "BMP", "X-Product-Id": "ZBMP", "X-Lumenis-Action": "WRITE"}


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
    guard = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "_permission_gate_write_check")
    guard.decorator_list = []
    namespace = dict(request=request, jsonify=jsonify, _PG_WRITE_METHODS={"POST", "PUT", "PATCH", "DELETE"},
                     _PG_BYPASS_PATHS=set(), _pg=media_store["gate"],
                     _pg_resolve_operation_type=lambda *_: p.OperationType.DB_WRITE)
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
    import experience_runtime

    client, store, _app = local_client
    monkeypatch.setattr(experience_runtime, "_CONTENT_SOURCE_IMPORT_MAX_BYTES", 16)
    response = upload(client, store)
    assert response.status_code == 413
    assert rows(store) == []


def imported_audio_project(client, store):
    from lumenis.shared.content_creation.video_editing import Timeline, fingerprint_local_media

    confirmation = pending(client, store)
    assert confirm(client, confirmation).status_code == 200
    imported = upload(client, store).get_json()["result"]
    asset = fingerprint_local_media(store["source"])
    assert imported["asset"]["asset_id"] == asset.asset_id
    timeline = Timeline.from_assets([asset]).add_audio_track("voice", audio_role="voiceover")
    timeline = timeline.add_clip(asset.asset_id, track_id="voice", source_out=.4)
    return {
        "asset_refs": [imported["artifact"]["artifact_id"]], "timeline": timeline.to_dict(),
        "output_kind": "audio", "demo_acknowledged": True,
    }


def export_project(client, payload):
    return client.post("/api/experience/content-projects/export", headers=HEADERS,
                       json={"action_type": "EXPORT", "input": payload})


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
    # Revision must persist separately and preserve the earlier editable package.
    from lumenis.shared.content_creation.video_editing import Timeline, fingerprint_local_media
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
