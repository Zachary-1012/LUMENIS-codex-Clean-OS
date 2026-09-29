"""Real isolated media/registry round trips; these are not App/user acceptance."""
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import struct
import subprocess
import wave

import pytest

import shared_artifacts as artifacts
from lumenis.shared.content_creation.video_editing import Timeline, fingerprint_local_media
from lumenis.shared.database import DatabaseRepository
from lumenis.system.security import permission as p


@pytest.fixture
def media_store(tmp_path, monkeypatch):
    database = tmp_path / "media-store.sqlite3"
    root = tmp_path / "artifacts"
    monkeypatch.setenv("ZBC_DB_PATH", str(database))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(root))
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(tmp_path))
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)
    repository = DatabaseRepository(str(database))
    import account.models
    monkeypatch.setattr(account.models, "get_repository", lambda: repository)
    monkeypatch.setattr(artifacts, "get_repository", lambda: repository)
    with repository.connect() as connection:
        connection.execute("CREATE TABLE v4_users (id INTEGER PRIMARY KEY, role TEXT, status TEXT)")
        connection.executemany("INSERT INTO v4_users VALUES (?, 'admin', 'active')", [(1,), (2,)])
    gate = p.PermissionGate()
    gate.grant_permission(p.PermissionLevel.COMMIT)
    monkeypatch.setattr(p, "get_permission_gate", lambda: gate)
    source = tmp_path / "voice.wav"
    with wave.open(str(source), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(48000)
        samples = (int(7000 * math.sin(2 * math.pi * 440 * n / 48000)) for n in range(24000))
        audio.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    return {"source": source, "root": root, "gate": gate, "repository": repository}


SCOPE = {"domain_id": "bmp", "global_scope": True}
ACTOR = {"id": 1, "role": "admin"}


@pytest.mark.parametrize("path", [
    r"\\fileserver.invalid\share\clip.mp4",
    "//fileserver.invalid/share/clip.mp4",
])
def test_network_share_path_is_rejected_without_touching_filesystem(monkeypatch, path):
    def forbidden_resolve(*args, **kwargs):
        raise AssertionError("remote share must be rejected before filesystem access")

    monkeypatch.setattr(Path, "resolve", forbidden_resolve)
    with pytest.raises(artifacts.LocalArtifactError, match="LOCAL_ASSET_REQUIRED"):
        artifacts.validate_local_asset(path)


def approve(store):
    source = store["source"]
    upload = p.ContentSourceImport(
        actor_id=1, domain_id="bmp", subject_id=None, brand_focus_id=None,
        global_scope=True, filename=source.name, size_bytes=source.stat().st_size,
        body_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    scope = p.check_actor_scope_permission(ACTOR, action="write", module="content", gate=store["gate"], **SCOPE)
    assert scope.allowed
    resource = p.content_source_import_resource(scope, upload, gate=store["gate"])
    return store["gate"].grant_approval("db_write", resource=resource, granted_by="isolated-test-only")


def import_source(store):
    return artifacts.stage_content_source_artifact(
        store["source"], filename=store["source"].name, actor=ACTOR,
        source_execution_id="isolated-import", **SCOPE,
    )


def rows(store):
    with store["repository"].connect() as connection:
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE name='lumenis_shared_artifacts'").fetchone():
            return []
        return connection.execute("SELECT artifact_id,sha256 FROM lumenis_shared_artifacts").fetchall()


def test_unapproved_upload_creates_no_artifact_or_registry(media_store):
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_APPROVAL_REQUIRED"):
        import_source(media_store)
    assert rows(media_store) == []
    assert not media_store["root"].exists()


def test_real_source_round_trip_consumes_exact_approval_and_hides_legacy_download(media_store):
    token = approve(media_store)
    result = import_source(media_store)
    artifact_id = result["artifact"]["artifact_id"]
    assert result["asset"]["media_kind"] == "audio"
    assert result["rights_state"] == "unknown"
    assert media_store["gate"]._approvals[token].revoked
    assert len(rows(media_store)) == 1
    assert artifacts.get_artifact(artifact_id) is None
    assert artifacts.artifact_file_path(artifact_id) is None
    reopened = artifacts.read_content_source_artifact(artifact_id, actor=ACTOR, **SCOPE)
    assert reopened == result
    with artifacts.resolve_content_source_assets([artifact_id], actor=ACTOR, **SCOPE) as sources:
        resolved = sources[0]["path"]
        assert resolved.read_bytes() == media_store["source"].read_bytes()
        assert sources[0]["asset"].to_dict() == result["asset"]
    assert not resolved.exists()
    assert str(media_store["source"]) not in json.dumps(result)
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_APPROVAL_REQUIRED"):
        import_source(media_store)
    assert len(rows(media_store)) == 1


def test_changed_source_bytes_are_denied_before_decoding_or_packaging(media_store, monkeypatch):
    token = approve(media_store)
    original = media_store["source"].read_bytes()
    expected_sha256 = hashlib.sha256(original).hexdigest()
    media_store["source"].write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    import lumenis.shared.content_creation.video_editing as editing

    def forbidden_probe(*args, **kwargs):
        raise AssertionError("changed upload must be rejected before decoding")

    monkeypatch.setattr(editing, "fingerprint_local_media", forbidden_probe)
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_CHANGED_DURING_IMPORT"):
        artifacts.stage_content_source_artifact(
            media_store["source"], filename=media_store["source"].name,
            actor=ACTOR, **SCOPE, source_execution_id="isolated-changed-source",
            expected_sha256=expected_sha256,
        )
    assert rows(media_store) == []
    assert not media_store["root"].exists()
    assert not media_store["gate"]._approvals[token].revoked


def test_failed_registration_cleans_only_new_package_and_allows_explicit_retry(media_store, monkeypatch):
    token = approve(media_store)

    def unavailable(**kwargs):
        raise sqlite3.OperationalError("isolated registration failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(artifacts, "_register_artifact", unavailable)
        with pytest.raises(sqlite3.OperationalError, match="isolated registration failure"):
            import_source(media_store)
    assert rows(media_store) == []
    assert list(media_store["root"].iterdir()) == []
    assert not media_store["gate"]._approvals[token].revoked
    result = import_source(media_store)
    assert media_store["gate"]._approvals[token].revoked
    assert len(rows(media_store)) == 1
    assert artifacts.read_content_source_artifact(
        result["artifact"]["artifact_id"], actor=ACTOR, **SCOPE,
    ) == result


def test_source_id_collision_preserves_registered_package_and_does_not_consume_new_approval(media_store, monkeypatch):
    approve(media_store)
    first = import_source(media_store)
    artifact_id = first["artifact"]["artifact_id"]
    package = media_store["root"] / f"{artifact_id}.zip"
    original = package.read_bytes()
    token = approve(media_store)
    monkeypatch.setattr(artifacts, "_new_artifact_id", lambda: artifact_id)
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_ID_COLLISION"):
        import_source(media_store)
    assert package.read_bytes() == original
    assert len(rows(media_store)) == 1
    assert not media_store["gate"]._approvals[token].revoked


@pytest.mark.parametrize("scope_request", [
    {"actor": {"id": 2}, **SCOPE},
    {"actor": ACTOR, "domain_id": "cth", "global_scope": True},
])
def test_other_actor_and_domain_cannot_reopen_source(media_store, scope_request):
    approve(media_store)
    result = import_source(media_store)
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_CONTEXT_MISMATCH"):
        artifacts.read_content_source_artifact(result["artifact"]["artifact_id"], **scope_request)


def test_revoke_during_packaging_removes_unregistered_package(media_store, monkeypatch):
    token = approve(media_store)
    checker = p.check_content_source_import_permission
    count = 0
    def cancel_before_registration(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 2:
            media_store["gate"].revoke_approval(token)
        return checker(*args, **kwargs)
    monkeypatch.setattr(p, "check_content_source_import_permission", cancel_before_registration)
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_APPROVAL_REQUIRED"):
        import_source(media_store)
    assert count == 2 and rows(media_store) == []
    assert list(media_store["root"].iterdir()) == []


def test_tampered_package_and_inactive_account_are_denied_with_recovery(media_store):
    approve(media_store)
    result = import_source(media_store)
    artifact_id = result["artifact"]["artifact_id"]
    package = media_store["root"] / f"{artifact_id}.zip"
    original = package.read_bytes()
    package.write_bytes(original + b"tampered")
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_INTEGRITY_FAILED"):
        artifacts.read_content_source_artifact(artifact_id, actor=ACTOR, **SCOPE)
    package.write_bytes(original)
    with media_store["repository"].connect() as connection:
        connection.execute("UPDATE v4_users SET status='inactive' WHERE id=1")
    with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
        artifacts.read_content_source_artifact(artifact_id, actor=ACTOR, **SCOPE)
    with media_store["repository"].connect() as connection:
        connection.execute("UPDATE v4_users SET status='active' WHERE id=1")
    assert artifacts.read_content_source_artifact(artifact_id, actor=ACTOR, **SCOPE) == result


def test_audio_project_real_render_reopen_revision_and_download(media_store):
    approve(media_store)
    source = import_source(media_store)
    source_id = source["artifact"]["artifact_id"]
    with artifacts.resolve_content_source_assets([source_id], actor=ACTOR, **SCOPE) as sources:
        asset = sources[0]["asset"]
        timeline = Timeline.from_assets([asset]).add_audio_track("voice", audio_role="voiceover")
        timeline = timeline.add_clip(asset.asset_id, track_id="voice", audio_role="voiceover", source_out=0.4)
        result = artifacts.stage_timeline_artifact(
            timeline, actor=ACTOR, **SCOPE, source_execution_id="isolated-export",
            demo_acknowledged=True, output_kind="audio", source_artifact_refs=[source_id],
        )
    project_id = result["artifact"]["artifact_id"]
    reopened = artifacts.read_content_project(project_id, actor=ACTOR, **SCOPE)
    assert artifacts.get_artifact(project_id) is None
    assert artifacts.artifact_file_path(project_id) is None
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_PROJECT_CONTEXT_MISMATCH"):
        artifacts.authorized_project_media(project_id, actor={"id": 2}, **SCOPE)
    package = media_store["root"] / f"{project_id}.zip"
    original_package = package.read_bytes()
    package.write_bytes(original_package + b"tampered")
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_PROJECT_INTEGRITY_FAILED"):
        artifacts.read_content_project(project_id, actor=ACTOR, **SCOPE)
    package.write_bytes(original_package)
    assert artifacts.read_content_project(project_id, actor=ACTOR, **SCOPE) == reopened
    assert reopened["project"]["source_artifact_refs"] == [source_id]
    media = artifacts.authorized_project_media(project_id, actor=ACTOR, **SCOPE)
    assert media["data"].startswith(b"RIFF")
    assert hashlib.sha256(media["data"]).hexdigest() == result["render"]["media_sha256"]
    assert media["media_type"] == "audio/wav"
    assert result["rights_state"] == "unknown" and result["publish_status"] == "not_performed"
    with artifacts.resolve_content_source_assets([source_id], actor=ACTOR, **SCOPE) as sources:
        restored = Timeline.from_dict(reopened["project"]["timeline"], assets=[item["asset"] for item in sources])
        revised = restored.add_audio_track("music", audio_role="bgm")
        second = artifacts.stage_timeline_artifact(
            revised, actor=ACTOR, **SCOPE, source_execution_id="isolated-revision",
            demo_acknowledged=True, output_kind="audio", source_artifact_refs=[source_id],
            previous_artifact_id=project_id,
        )
    assert second["project"]["parent_artifact_id"] == project_id
    assert second["artifact"]["artifact_id"] != project_id
    assert artifacts.read_content_project(project_id, actor=ACTOR, **SCOPE) == reopened
    assert len(rows(media_store)) == 3


def test_access_revoked_during_encoding_stops_process_and_preserves_reopenable_version(media_store, monkeypatch):
    approve(media_store)
    source = import_source(media_store)
    source_id = source["artifact"]["artifact_id"]
    with artifacts.resolve_content_source_assets([source_id], actor=ACTOR, **SCOPE) as sources:
        asset = sources[0]["asset"]
        timeline = Timeline.from_assets([asset]).add_audio_track("voice", audio_role="voiceover")
        timeline = timeline.add_clip(asset.asset_id, track_id="voice", source_out=.4)
        arguments = dict(actor=ACTOR, **SCOPE, source_execution_id="isolated-revocation",
                         demo_acknowledged=True, output_kind="audio", source_artifact_refs=[source_id])
        previous = artifacts.stage_timeline_artifact(timeline, **arguments)
        previous_id = previous["artifact"]["artifact_id"]
        previous_bytes = artifacts.authorized_project_media(previous_id, actor=ACTOR, **SCOPE)["data"]
        revision = timeline.add_audio_track("music", audio_role="bgm")
        processes = []
        popen = subprocess.Popen
        def revoke_on_encoder_launch(command, **kwargs):
            process = popen(command, **kwargs)
            if Path(command[0]).stem.lower() == "ffmpeg":
                processes.append(process)
                with media_store["repository"].connect() as connection:
                    connection.execute("UPDATE v4_users SET status='inactive' WHERE id=1")
            return process
        with monkeypatch.context() as scoped:
            scoped.setattr(subprocess, "Popen", revoke_on_encoder_launch)
            with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
                artifacts.stage_timeline_artifact(revision, previous_artifact_id=previous_id, **arguments)
        assert len(processes) == 1 and processes[0].poll() is not None
        assert len(rows(media_store)) == 2
        assert len(list(media_store["root"].glob("*.zip"))) == 2
        with media_store["repository"].connect() as connection:
            connection.execute("UPDATE v4_users SET status='active' WHERE id=1")
        assert artifacts.authorized_project_media(previous_id, actor=ACTOR, **SCOPE)["data"] == previous_bytes
        recovered = artifacts.stage_timeline_artifact(revision, previous_artifact_id=previous_id, **arguments)
        assert recovered["project"]["parent_artifact_id"] == previous_id
        assert len(rows(media_store)) == 3
