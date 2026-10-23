"""Read-only media inspection through real local scope and ffprobe boundaries."""
import hashlib

import pytest
from flask import Flask

from tests.test_content_project_storage import media_store, rows


@pytest.fixture
def inspection_client(media_store, monkeypatch):
    import experience_runtime
    import lumenis.auth.service
    from lumenis.system.security.permission import PermissionLevel

    monkeypatch.setattr(lumenis.auth.service, "get_current_user", lambda: None)
    media_store["gate"].revoke_permission(PermissionLevel.COMMIT)
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    app.register_blueprint(experience_runtime.experience_bp)
    return app.test_client(), media_store, app


def inspect(client, store, *, headers=None, payload=None, **kwargs):
    return client.post(
        "/api/experience/shared-skills/shared.content_project/inspect",
        headers=headers or {"X-Domain-Id": "BMP", "X-Product-Id": "ZBMP"},
        json={"action_type": "READ", "input": payload or {
            "asset_paths": [str(store["source"])],
        }},
        **kwargs,
    )


@pytest.mark.parametrize("domain,product", [("CTH", "CTH"), ("BMP", "ZBMP")])
def test_local_open_media_inspection_without_account_or_artifact_write(
    inspection_client, monkeypatch, domain, product,
):
    import lumenis.auth.service

    def account_wall_is_forbidden():
        raise AssertionError("open local workspace must not depend on a product account")

    monkeypatch.setattr(lumenis.auth.service, "get_current_user", account_wall_is_forbidden)
    client, store, _app = inspection_client
    original = store["source"].read_bytes()
    response = inspect(client, store, headers={"X-Domain-Id": domain, "X-Product-Id": product})
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["assets"][0]["media_kind"] == "audio"
    assert body["assets"][0]["sha256"] == hashlib.sha256(original).hexdigest()
    assert body["rights_state"] == "unknown"
    assert body["external_fetch"] is False
    assert body["source_artifact_refs"] == []
    assert store["source"].read_bytes() == original
    assert rows(store) == []
    assert not store["root"].exists()


def test_missing_file_can_be_restored_and_retried_without_partial_artifact(inspection_client):
    client, store, _app = inspection_client
    source = store["source"]
    parked = source.with_name("parked.wav")
    source.rename(parked)
    assert inspect(client, store).status_code == 404
    assert rows(store) == []
    parked.rename(source)
    assert inspect(client, store).status_code == 200
    assert rows(store) == []


def test_registered_brand_focus_is_resolved_before_reading(inspection_client, monkeypatch):
    import subject_registry

    client, store, _app = inspection_client
    entry = {
        "subject_id": "SUBJ-BRAND", "brand_focus_id": "BRAND-X",
        "subject_type": "brand", "domain_id": "BMP",
        "status": "active",
    }
    monkeypatch.setattr(subject_registry, "get_subject_by_id", lambda *_: entry)
    monkeypatch.setattr(subject_registry, "list_subjects", lambda *_: [entry])
    headers = {
        "X-Domain-Id": "BMP", "X-Lumenis-Context-Mode": "FOCUS",
        "X-Subject-ID": "SUBJ-BRAND", "X-Brand-Focus-ID": "BRAND-X",
    }
    assert inspect(client, store, headers=headers).status_code == 200
    monkeypatch.setattr(subject_registry, "list_subjects", lambda *_: [])
    assert inspect(client, store, headers=headers).status_code == 403
    assert rows(store) == []


@pytest.mark.parametrize("extra", [
    {"Origin": "https://external.invalid"},
    {"Authorization": "Bearer invalid"},
    {"X-Forwarded-For": "127.0.0.1"},
    {"Host": "external.invalid"},
])
def test_ineligible_transport_never_probes_media(inspection_client, monkeypatch, extra):
    import lumenis.shared.content_creation.video_editing as editing

    monkeypatch.setattr(editing, "fingerprint_local_media", lambda *_: pytest.fail("denied media was probed"))
    client, store, _app = inspection_client
    response = inspect(client, store, headers={"X-Domain-Id": "BMP", **extra})
    assert response.status_code == 401
    assert rows(store) == []


def test_workspace_closed_or_remote_fails_without_probe(inspection_client):
    client, store, app = inspection_client
    assert inspect(client, store, environ_overrides={"REMOTE_ADDR": "192.0.2.4"}).status_code == 401
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    assert inspect(client, store).status_code == 401
    assert rows(store) == []


@pytest.mark.parametrize("extra", [
    {"X-Product-Id": "CTH"},
    {"X-Lumenis-Context-Mode": "GLOBAL_ALL", "X-Subject-ID": "SUBJ-X"},
    {"X-Lumenis-Context-Mode": "FOCUS"},
    {"X-Domain-Id": "SYSTEM"},
])
def test_mismatched_scope_is_not_implicitly_global(inspection_client, extra):
    client, store, _app = inspection_client
    response = inspect(client, store, headers={"X-Domain-Id": "BMP", **extra})
    assert response.status_code in {400, 403}
    assert rows(store) == []


def test_remote_asset_and_unavailable_local_asset_have_honest_errors(inspection_client):
    client, store, _app = inspection_client
    response = inspect(client, store, payload={"asset_paths": ["https://external.invalid/video.mp4"]})
    assert response.status_code == 400
    assert response.get_json()["code"] == "LOCAL_ASSET_REQUIRED"
    missing = store["source"].with_name("not-present.wav")
    response = inspect(client, store, payload={"asset_paths": [str(missing)]})
    assert response.status_code == 404
    assert str(missing) not in response.get_data(as_text=True)
    assert rows(store) == []


def test_cross_domain_focus_cannot_be_relabelled(inspection_client, monkeypatch):
    import subject_registry

    client, store, _app = inspection_client
    monkeypatch.setattr(subject_registry, "get_subject_by_id", lambda *_: {
        "subject_id": "SUBJ-COMMERCIAL", "subject_type": "company", "domain_id": "CTH",
    })
    response = inspect(client, store, headers={
        "X-Domain-Id": "BMP", "X-Lumenis-Context-Mode": "FOCUS",
        "X-Subject-ID": "SUBJ-COMMERCIAL",
    })
    assert response.status_code == 403
    assert rows(store) == []


def _audio_comparison_request(store, **changes):
    from lumenis.shared.content_creation.video_editing import (
        Timeline,
        fingerprint_local_media,
    )
    asset = fingerprint_local_media(str(store["source"]))
    timeline = Timeline.from_assets([asset]).add_audio_track("voice", audio_role="voiceover")
    timeline = timeline.add_clip(asset.asset_id, track_id="voice", audio_stream_index=0)
    options = {"start_sec": 0, "end_sec": .5, "render_options": {"loudness_target_lufs": -23}}
    options.update(changes)
    return {"asset_paths": [str(store["source"])], "timeline": timeline.to_dict(), "audio_comparison": options}


def test_audio_comparison_decodes_real_same_range_without_saving(inspection_client):
    import base64
    import io
    import wave
    client, store, _ = inspection_client
    original = store["source"].read_bytes()
    response = inspect(client, store, payload=_audio_comparison_request(store))
    assert response.status_code == 200, response.get_json()
    result = response.get_json()["audio_comparison"]
    assert response.headers["Cache-Control"] == "no-store"
    assert result["persisted"] is False and result["export_performed"] is False
    assert result["approval_required"] is True
    assert abs(result["programme_measurements"]["processed"]["integrated_lufs"] + 23) < 1
    assert result["samples"]["original"]["sha256"] != result["samples"]["processed"]["sha256"]
    for sample in result["samples"].values():
        data = base64.b64decode(sample["wav_base64"], validate=True)
        assert len(data) == sample["size_bytes"] and hashlib.sha256(data).hexdigest() == sample["sha256"]
        with wave.open(io.BytesIO(data)) as audio:
            assert audio.getnframes() == 24000 and audio.getframerate() == 48000
            assert audio.getnchannels() == 2 and audio.getsampwidth() == 2
    assert store["source"].read_bytes() == original
    assert rows(store) == [] and not store["root"].exists()


@pytest.mark.parametrize("change", [
    {"start_sec": -1}, {"end_sec": 61}, {"end_sec": 0},
    {"start_sec": True}, {"render_options": {"noise_reduction_db": 30}},
])
def test_invalid_audio_preview_never_decodes_or_saves(inspection_client, monkeypatch, change):
    from lumenis.shared.content_creation import rendering
    client, store, _ = inspection_client
    payload = _audio_comparison_request(store, **change)
    monkeypatch.setattr(rendering, "_run", lambda *a, **k: pytest.fail("invalid preview decoded audio"))
    assert inspect(client, store, payload=payload).status_code == 400
    assert rows(store) == [] and not store["root"].exists()


def test_audio_comparison_permission_change_stops_processing(inspection_client, monkeypatch):
    import experience_runtime
    from shared_artifacts import LocalArtifactError
    client, store, _ = inspection_client
    payload = _audio_comparison_request(store)
    original_scope = experience_runtime._content_project_scope
    count = 0
    def changing_scope(action):
        nonlocal count
        count += 1
        if count >= 3:
            raise LocalArtifactError("CONTENT_PROJECT_CONTEXT_MISMATCH")
        return original_scope(action)
    monkeypatch.setattr(experience_runtime, "_content_project_scope", changing_scope)
    assert inspect(client, store, payload=payload).status_code != 200
    assert count >= 3 and rows(store) == [] and not store["root"].exists()
