"""Real isolated media/registry round trips; these are not App/user acceptance."""
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import struct
import subprocess
import wave
import zipfile

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


def test_account_source_manifest_is_not_implicitly_transferred_to_local_workspace(media_store):
    from flask import Flask

    approve(media_store)
    source = import_source(media_store)
    artifact_id = source["artifact"]["artifact_id"]
    package = media_store["root"] / f"{artifact_id}.zip"
    original = package.read_bytes()
    with zipfile.ZipFile(package) as archive:
        metadata = json.loads(archive.read("source.json"))
    assert metadata["context"] == {
        "actor_id": 1, "domain_id": "zbmp", "subject_id": None,
        "brand_focus_id": None, "global_scope": True,
    }
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with app.test_request_context(
        "/", headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        principal = p.resolve_local_workspace_principal(module="content", action="read")
        assert type(principal) is p.LocalWorkspacePrincipal
        with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_CONTEXT_MISMATCH"):
            artifacts.read_content_source_artifact(artifact_id, actor=principal, **SCOPE)
        with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_CONTEXT_MISMATCH"):
            with artifacts.resolve_content_source_assets([artifact_id], actor=principal, **SCOPE):
                raise AssertionError("account source was implicitly reassigned to workspace")
    assert package.read_bytes() == original
    assert artifacts.read_content_source_artifact(artifact_id, actor=ACTOR, **SCOPE) == source


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


@pytest.mark.parametrize("legacy_demo", [None, False, True])
def test_audio_project_real_render_reopen_revision_and_download(media_store, legacy_demo):
    approve(media_store)
    source = import_source(media_store)
    source_id = source["artifact"]["artifact_id"]
    with artifacts.resolve_content_source_assets([source_id], actor=ACTOR, **SCOPE) as sources:
        asset = sources[0]["asset"]
        timeline = Timeline.from_assets([asset]).add_audio_track("voice", audio_role="voiceover")
        timeline = timeline.add_clip(asset.asset_id, track_id="voice", audio_role="voiceover", source_out=0.4)
        result = artifacts.stage_timeline_artifact(
            timeline, actor=ACTOR, **SCOPE, source_execution_id="isolated-export",
            output_kind="audio", source_artifact_refs=[source_id],
            **({} if legacy_demo is None else {"demo_acknowledged": legacy_demo}),
        )
    project_id = result["artifact"]["artifact_id"]
    reopened = artifacts.read_content_project(project_id, actor=ACTOR, **SCOPE)
    assert reopened["project"]["context"] == {
        "actor_id": 1, "domain_id": "zbmp", "subject_id": None,
        "brand_focus_id": None, "global_scope": True,
    }
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
    assert reopened["project"]["rights"] == {"state": "unknown", "label": "rights unknown"}
    assert "demo_acknowledged" not in result
    with artifacts.resolve_content_source_assets([source_id], actor=ACTOR, **SCOPE) as sources:
        restored = Timeline.from_dict(reopened["project"]["timeline"], assets=[item["asset"] for item in sources])
        revised = restored.add_audio_track("music", audio_role="bgm")
        second = artifacts.stage_timeline_artifact(
            revised, actor=ACTOR, **SCOPE, source_execution_id="isolated-revision",
            output_kind="audio", source_artifact_refs=[source_id],
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


@pytest.fixture
def local_store(tmp_path, monkeypatch):
    """Actual local Flask transport and a server-issued principal, no account row."""
    from flask import Flask

    database = tmp_path / "local-workspace.sqlite3"
    root = tmp_path / "artifacts"
    monkeypatch.setenv("ZBC_DB_PATH", str(database))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(root))
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(tmp_path))
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)
    repository = DatabaseRepository(str(database))
    monkeypatch.setattr(artifacts, "get_repository", lambda: repository)
    gate = p.PermissionGate()
    monkeypatch.setattr(p, "get_permission_gate", lambda: gate)

    def account_lookup_forbidden(*args, **kwargs):
        raise AssertionError("workspace operation must not borrow an account actor")

    monkeypatch.setattr(p, "_actor_has_scope_action", account_lookup_forbidden)
    source = tmp_path / "local-voice.wav"
    with wave.open(str(source), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(48000)
        samples = (int(7000 * math.sin(2 * math.pi * 440 * n / 48000)) for n in range(24000))
        audio.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with app.test_request_context(
        "/", headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        principal = p.resolve_local_workspace_principal(module="content", action="write")
        assert type(principal) is p.LocalWorkspacePrincipal
        yield {
            "source": source, "root": root, "gate": gate, "repository": repository,
            "app": app, "principal": principal,
        }


def local_scope(store, **changes):
    arguments = {
        "actor": store["principal"], "domain_id": "bmp", "subject_id": None,
        "brand_focus_id": None, "global_scope": True, "action": "read",
    }
    return artifacts._authorize_content_project(**{**arguments, **changes})


def test_local_ownership_is_explicit_and_never_an_account_actor(local_store):
    actor_id, scope = local_scope(local_store)
    assert actor_id is None
    assert artifacts._content_artifact_context(local_store["principal"], actor_id, scope) == {
        "actor_id": None, "domain_id": "zbmp", "subject_id": None,
        "brand_focus_id": None, "global_scope": True,
        "principal_kind": "local_workspace", "principal_ref": "workspace:local",
    }
    assert not local_store["gate"].has_permission(p.PermissionLevel.COMMIT)
    assert not local_store["gate"]._approvals


@pytest.mark.parametrize("actor", [
    None, {"id": None}, {"id": 0},
    {"actor_id": None, "principal_kind": "local_workspace", "principal_ref": "workspace:local"},
])
def test_local_actor_cannot_be_supplied_as_json_or_an_empty_account(local_store, actor):
    with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
        local_scope(local_store, actor=actor)


def test_local_ownership_rechecks_the_workspace_flag_without_discarding_principal(local_store):
    assert local_scope(local_store)[0] is None
    local_store["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
        local_scope(local_store)
    local_store["app"].config["LUMENIS_OPEN_WORKSPACE"] = True
    assert local_scope(local_store)[0] is None


@pytest.mark.parametrize("headers,remote_addr", [
    ({"Host": "remote.invalid"}, "127.0.0.1"),
    ({"Host": "localhost"}, "192.0.2.7"),
    ({"Host": "localhost", "X-Forwarded-For": "127.0.0.1"}, "127.0.0.1"),
    ({"Host": "localhost", "X-Actor-ID": "1"}, "127.0.0.1"),
    ({"Host": "localhost", "Authorization": "Bearer ignored"}, "127.0.0.1"),
    ({"Host": "localhost", "Cookie": "cth_poms_v4_session=present"}, "127.0.0.1"),
])
def test_saved_local_principal_does_not_authorize_another_transport(local_store, headers, remote_addr):
    with local_store["app"].test_request_context(
        "/", headers=headers, environ_overrides={"REMOTE_ADDR": remote_addr},
    ):
        with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
            local_scope(local_store)


@pytest.mark.parametrize("changes", [
    {"domain_id": "other"}, {"global_scope": 1},
    {"global_scope": True, "brand_focus_id": "brand-a"},
    {"subject_id": "subject-a", "brand_focus_id": "brand-a"},
])
def test_local_principal_cannot_widen_invalid_resource_selection(local_store, changes):
    with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
        local_scope(local_store, **changes)


def prepare_local_import(store):
    source = store["source"]
    principal = store["principal"]
    upload = p.ContentSourceImport(
        actor_id=None, domain_id="bmp", subject_id=None, brand_focus_id=None,
        global_scope=True, filename=source.name, size_bytes=source.stat().st_size,
        body_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        principal_kind=principal.principal_kind, principal_ref=principal.principal_ref,
    )
    pending = p.prepare_content_source_import_confirmation(
        None, upload, principal=principal, gate=store["gate"],
    )
    assert pending["allowed"], pending
    return pending, upload


def confirm_local_import(store, pending):
    decision = p.confirm_content_source_import(
        None, pending["confirmation_id"], principal=store["principal"],
        confirmed=True, gate=store["gate"], **SCOPE,
    )
    assert decision.allowed, decision
    assert decision.approval_token is None


def import_local_source(store):
    return artifacts.stage_content_source_artifact(
        store["source"], filename=store["source"].name, actor=store["principal"],
        source_execution_id="isolated-local-workspace-import", **SCOPE,
    )


def test_local_source_requires_real_confirmation_and_consumes_it_without_account_or_commit(local_store):
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_APPROVAL_REQUIRED"):
        import_local_source(local_store)
    assert rows(local_store) == [] and not local_store["root"].exists()
    pending, upload = prepare_local_import(local_store)
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_APPROVAL_REQUIRED"):
        import_local_source(local_store)
    confirm_local_import(local_store, pending)
    receipt = p.check_content_source_import_permission(
        None, upload, principal=local_store["principal"], gate=local_store["gate"],
    )
    assert receipt.allowed
    result = import_local_source(local_store)
    assert local_store["gate"]._approvals[receipt.approval_token].revoked
    assert not local_store["gate"].has_permission(p.PermissionLevel.COMMIT)
    artifact_id = result["artifact"]["artifact_id"]
    with zipfile.ZipFile(local_store["root"] / f"{artifact_id}.zip") as archive:
        metadata = json.loads(archive.read("source.json"))
    assert metadata["context"] == {
        "actor_id": None, "domain_id": "zbmp", "subject_id": None,
        "brand_focus_id": None, "global_scope": True,
        "principal_kind": "local_workspace", "principal_ref": "workspace:local",
    }
    assert artifacts.read_content_source_artifact(
        artifact_id, actor=local_store["principal"], **SCOPE,
    ) == result
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_CONTEXT_MISMATCH"):
        artifacts.read_content_source_artifact(
            artifact_id, actor=local_store["principal"], domain_id="cth", global_scope=True,
        )
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_APPROVAL_REQUIRED"):
        import_local_source(local_store)
    with local_store["repository"].connect() as connection:
        assert not connection.execute("SELECT 1 FROM sqlite_master WHERE name='v4_users'").fetchone()
    assert len(rows(local_store)) == 1


@pytest.mark.parametrize("confirmed", [False, True])
def test_local_import_cancel_creates_no_artifact_and_retry_needs_a_new_confirmation(local_store, confirmed):
    pending, _ = prepare_local_import(local_store)
    if confirmed:
        confirm_local_import(local_store, pending)
    assert p.cancel_content_source_import_confirmation(
        None, pending["confirmation_id"], SCOPE,
        principal=local_store["principal"], gate=local_store["gate"],
    )
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_SOURCE_APPROVAL_REQUIRED"):
        import_local_source(local_store)
    assert rows(local_store) == [] and not local_store["root"].exists()
    retry, _ = prepare_local_import(local_store)
    assert retry["confirmation_id"] != pending["confirmation_id"]
    confirm_local_import(local_store, retry)
    assert import_local_source(local_store)["asset"]["media_kind"] == "audio"


def test_local_source_rechecks_flag_after_read_and_reopens_after_reenable(local_store, monkeypatch):
    pending, _ = prepare_local_import(local_store)
    confirm_local_import(local_store, pending)
    result = import_local_source(local_store)
    artifact_id = result["artifact"]["artifact_id"]
    original_hash = artifacts._hash_file

    def close_after_hash(path):
        digest = original_hash(path)
        local_store["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
        return digest

    with monkeypatch.context() as scoped:
        scoped.setattr(artifacts, "_hash_file", close_after_hash)
        with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
            artifacts.read_content_source_artifact(artifact_id, actor=local_store["principal"], **SCOPE)
    local_store["app"].config["LUMENIS_OPEN_WORKSPACE"] = True
    assert artifacts.read_content_source_artifact(artifact_id, actor=local_store["principal"], **SCOPE) == result


def test_local_render_reopen_revision_revalidates_export_and_transport(local_store, monkeypatch):
    pending, _ = prepare_local_import(local_store)
    confirm_local_import(local_store, pending)
    source = import_local_source(local_store)
    source_id = source["artifact"]["artifact_id"]
    actor = local_store["principal"]
    with artifacts.resolve_content_source_assets([source_id], actor=actor, **SCOPE) as sources:
        timeline = Timeline.from_assets([sources[0]["asset"]]).add_audio_track("voice", audio_role="voiceover")
        timeline = timeline.add_clip(sources[0]["asset"].asset_id, track_id="voice", source_out=.4)
        arguments = dict(
            actor=actor, **SCOPE, source_execution_id="isolated-local-export",
            demo_acknowledged=True, output_kind="audio", source_artifact_refs=[source_id],
        )
        gate = local_store["gate"]
        gate.revoke_permission(p.PermissionLevel.VERIFY)
        with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_EXPORT_PERMISSION_DENIED"):
            artifacts.stage_timeline_artifact(timeline, **arguments)
        assert len(rows(local_store)) == 1
        gate.grant_permission(p.PermissionLevel.VERIFY)
        first = artifacts.stage_timeline_artifact(timeline, **arguments)
        project_id = first["artifact"]["artifact_id"]
        reopened = artifacts.read_content_project(project_id, actor=actor, **SCOPE)
        context = reopened["project"]["context"]
        assert context["actor_id"] is None
        assert context["principal_kind"] == "local_workspace"
        assert context["principal_ref"] == "workspace:local"
        previous_bytes = artifacts.authorized_project_media(project_id, actor=actor, **SCOPE)["data"]
        restored = Timeline.from_dict(reopened["project"]["timeline"], assets=[item["asset"] for item in sources])
        revised = restored.add_audio_track("music", audio_role="bgm")
        processes = []
        popen = subprocess.Popen

        def close_on_encoder_launch(command, **kwargs):
            process = popen(command, **kwargs)
            if Path(command[0]).stem.lower() == "ffmpeg":
                processes.append(process)
                local_store["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
            return process

        with monkeypatch.context() as scoped:
            scoped.setattr(subprocess, "Popen", close_on_encoder_launch)
            with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
                artifacts.stage_timeline_artifact(revised, previous_artifact_id=project_id, **arguments)
        assert len(processes) == 1 and processes[0].poll() is not None
        assert len(rows(local_store)) == 2
        with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
            artifacts.read_content_project(project_id, actor=actor, **SCOPE)
        with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
            artifacts.authorized_project_media(project_id, actor=actor, **SCOPE)
        local_store["app"].config["LUMENIS_OPEN_WORKSPACE"] = True
        assert artifacts.authorized_project_media(project_id, actor=actor, **SCOPE)["data"] == previous_bytes
        second = artifacts.stage_timeline_artifact(revised, previous_artifact_id=project_id, **arguments)
        assert second["project"]["parent_artifact_id"] == project_id
        assert artifacts.read_content_project(project_id, actor=actor, **SCOPE) == reopened
        export_audits = gate.get_audit_log(operation_type="data_export")
        assert export_audits and all(entry["caller"] == "workspace:local" for entry in export_audits)
        assert len(rows(local_store)) == 3
