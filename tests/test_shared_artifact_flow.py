"""Focused tests for the local video artifact and publish-approval boundary."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture()
def artifact_client(tmp_path, monkeypatch):
    db_file = tmp_path / "artifact-runtime.db"
    artifact_dir = tmp_path / "artifacts"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_file))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(artifact_dir))
    monkeypatch.setenv("ZBC_TEST_OFFLINE", "1")

    import shared_artifacts

    importlib.reload(shared_artifacts)
    shared_artifacts.ensure_artifact_table()

    import evidence_chain

    evidence_chain.init_db(str(db_file))

    import skill_execution_chain

    skill_execution_chain.ensure_skill_executions_table()

    from flask import Flask
    import experience_runtime

    app = Flask(__name__)
    app.register_blueprint(experience_runtime.experience_bp)
    return app.test_client(), tmp_path, shared_artifacts


def test_local_asset_validation_rejects_remote_urls(artifact_client):
    _, _, artifacts = artifact_client
    with pytest.raises(artifacts.LocalArtifactError, match="LOCAL_ASSET_REQUIRED"):
        artifacts.validate_local_asset("https://example.invalid/video.mp4")


def test_render_route_stages_real_artifact_and_exposes_no_absolute_path(artifact_client, monkeypatch):
    client, tmp_path, artifacts = artifact_client
    asset = tmp_path / "source.png"
    asset.write_bytes(b"local-test-asset")

    monkeypatch.setattr(artifacts, "_ffmpeg_path", lambda: "ffmpeg-test")

    def fake_ffmpeg(command, timeout=180):
        # The production function passes every output path as the final arg.
        Path(command[-1]).write_bytes(b"rendered-local-video")

    monkeypatch.setattr(artifacts, "_run_ffmpeg", fake_ffmpeg)
    response = client.post(
        "/api/experience/shared-skills/shared.video_shotcraft/render",
        json={
            "action_type": "EXPORT",
            "domain": "BMP",
            "task": "为品牌 Brief 生成视频成片草稿",
            "input": {"asset_paths": [str(asset)]},
        },
    )
    payload = response.get_json()
    assert response.status_code == 200, payload
    assert payload["ok"] is True
    assert payload["status"] == "rendered_staged"
    assert payload["approval_required"] is True
    assert payload["publish_status"] == "not_performed"
    assert payload["external_fetch"] is False
    assert payload["artifact"]["domain_id"] == "zbmp"
    assert ":\\" not in json.dumps(payload, ensure_ascii=False)

    artifact_id = payload["artifact"]["artifact_id"]
    detail = client.get(f"/api/experience/artifacts/{artifact_id}")
    assert detail.status_code == 200
    assert detail.get_json()["artifact"]["relative_path"] == f"{artifact_id}.mp4"
    stream = client.get(f"/api/experience/artifacts/{artifact_id}/file")
    assert stream.status_code == 200
    assert stream.data == b"rendered-local-video"


def test_render_route_rejects_remote_media_and_missing_assets(artifact_client):
    client, _, _ = artifact_client
    remote = client.post(
        "/api/experience/shared-skills/shared.video_shotcraft/render",
        json={
            "action_type": "EXPORT",
            "domain": "CTH",
            "input": {"asset_paths": ["https://example.invalid/a.mp4"]},
        },
    )
    assert remote.status_code == 400
    assert remote.get_json()["code"] == "LOCAL_ASSET_REQUIRED"

    missing = client.post(
        "/api/experience/shared-skills/shared.video_shotcraft/render",
        json={"action_type": "EXPORT", "domain": "CTH", "input": {}},
    )
    assert missing.status_code == 400
    assert missing.get_json()["code"] == "LOCAL_ASSETS_REQUIRED"


def test_publish_request_is_traceable_and_never_external(artifact_client, monkeypatch):
    client, tmp_path, artifacts = artifact_client
    artifact_file = artifacts.artifact_root() / "ART-test.mp4"
    artifact_file.parent.mkdir(parents=True, exist_ok=True)
    artifact_file.write_bytes(b"staged")
    artifact = artifacts._register_artifact(
        artifact_id="ART-test",
        kind="video_shotcraft_render",
        product_id="LUMENIS",
        domain_id="cth",
        source_execution_id="exec-test",
        evidence_id="",
        note_id="",
        path=artifact_file,
        media_type="video/mp4",
    )

    response = client.post(
        "/api/experience/ai/publish-requests",
        json={"artifact_id": artifact["artifact_id"], "platform": "rednote_hk", "domain": "cth"},
    )
    payload = response.get_json()
    assert response.status_code == 200, payload
    assert payload["status"] == "awaiting_approval"
    assert payload["approval_required"] is True
    assert payload["external_action"] == "not_executed"
    assert payload["next_step"] == "human_manual_publish"
    assert payload["human_controls_publish"] is True
    assert payload["product_will_not_publish"] is True
    assert payload["account_policy"] == "XHS_RETINAUT"
    assert payload["task"]["status"] == "awaiting_approval"

    rejected = client.post(
        "/api/experience/ai/publish-requests",
        json={"artifact_id": artifact["artifact_id"], "platform": "douyin", "domain": "cth"},
    )
    assert rejected.status_code == 409
    assert rejected.get_json()["code"] == "PLATFORM_NOT_ENABLED"
