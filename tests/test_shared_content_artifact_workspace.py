"""Isolated regressions for actor-owned Shared content artifacts.

These tests exercise the canonical account and Permission owners with a
disposable repository. They do not claim application or user acceptance.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import wave

import pytest

import shared_artifacts as artifacts
from lumenis.shared.content_creation.video_editing import Timeline
from lumenis.shared.database import DatabaseRepository
from lumenis.system.security import permission as p


SHARED_SCOPE = {"scope_kind": "shared_workspace", "version": 1}
BMP_GLOBAL_SCOPE = {"domain_id": "bmp", "global_scope": True}


@pytest.fixture
def content_workspace(tmp_path, monkeypatch):
    db_path = tmp_path / "shared-content.sqlite3"
    artifact_dir = tmp_path / "artifacts"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(artifact_dir))
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(tmp_path))
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)

    import account.models as account_models

    repository = DatabaseRepository(str(db_path))
    monkeypatch.setattr(account_models, "get_repository", lambda: repository)
    monkeypatch.setattr(artifacts, "get_repository", lambda: repository)
    account_models.init_account_db()
    artifacts.ensure_artifact_table()

    gate = p.PermissionGate()
    gate.grant_permission(p.PermissionLevel.COMMIT)
    monkeypatch.setattr(p, "get_permission_gate", lambda: gate)

    actors = {}
    with repository.transaction() as connection:
        for username, grants in (
            ("shared-content-owner", True),
            ("shared-content-peer", True),
            ("shared-content-ungranted", False),
        ):
            cursor = connection.execute(
                "INSERT INTO v4_users "
                "(username,password_hash,role,display_name,status) VALUES (?,?,?,?,?)",
                (username, "isolated-test-only-password-hash", "user", username, "active"),
            )
            actor_id = int(cursor.lastrowid)
            actors[username] = {"id": actor_id, "role": "owner"}
            if grants:
                rows = [
                    ("SHARED", "content", "read", None),
                    ("SHARED", "content", "write", None),
                    ("ZBMP", "content", "read", json.dumps({"global": True})),
                    ("ZBMP", "content", "write", json.dumps({"global": True})),
                ]
                connection.executemany(
                    "INSERT INTO v4_member_authorizations "
                    "(user_id,product_id,module,action,data_scope,time_range) "
                    "VALUES (?,?,?,?,?,NULL)",
                    [(actor_id, *row) for row in rows],
                )

    source = tmp_path / "voice.wav"
    with wave.open(str(source), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(48000)
        samples = (
            int(7000 * math.sin(2 * math.pi * 440 * index / 48000))
            for index in range(24000)
        )
        audio.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))

    yield {
        "root": tmp_path,
        "artifact_dir": artifact_dir,
        "db_path": db_path,
        "repository": repository,
        "gate": gate,
        "source": source,
        "owner": actors["shared-content-owner"],
        "peer": actors["shared-content-peer"],
        "ungranted": actors["shared-content-ungranted"],
    }


def _artifact_rows(workspace):
    with workspace["repository"].connect(read_only=True, wal=False) as connection:
        return connection.execute(
            "SELECT artifact_id,kind,product_id,domain_id,sha256 "
            "FROM lumenis_shared_artifacts ORDER BY artifact_id"
        ).fetchall()


def _import_scope4_source(workspace):
    actor = workspace["owner"]
    source = workspace["source"]
    upload = p.ContentSourceImport(
        actor_id=actor["id"], domain_id="bmp", subject_id=None,
        brand_focus_id=None, global_scope=True, filename=source.name,
        size_bytes=source.stat().st_size,
        body_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    scope = p.check_actor_scope_permission(
        actor, action="write", module="content", gate=workspace["gate"],
        **BMP_GLOBAL_SCOPE,
    )
    assert scope.allowed and scope.verification_state == "verified", scope
    resource = p.content_source_import_resource(scope, upload, gate=workspace["gate"])
    approval = workspace["gate"].grant_approval(
        "db_write", resource=resource, granted_by="isolated-source-owner-test",
    )
    result = artifacts.stage_content_source_artifact(
        source, filename=source.name, actor=actor,
        source_execution_id="isolated-scope4-import", **BMP_GLOBAL_SCOPE,
    )
    assert workspace["gate"]._approvals[approval].revoked
    assert result["rights_state"] == "unknown"
    return result


def _stage_shared_audio(workspace, source_id, *, previous=None, revised=False):
    with artifacts.resolve_content_source_assets(
        [source_id], actor=workspace["owner"], **BMP_GLOBAL_SCOPE,
    ) as sources:
        asset = sources[0]["asset"]
        if revised:
            assert previous is not None
            timeline = Timeline.from_dict(
                previous["project"]["timeline"], assets=[asset],
            ).add_audio_track("music", audio_role="bgm")
        else:
            timeline = Timeline.from_assets([asset]).add_audio_track(
                "voice", audio_role="voiceover",
            )
            timeline = timeline.add_clip(
                asset.asset_id, track_id="voice", audio_role="voiceover", source_out=0.4,
            )
        return artifacts.stage_timeline_artifact(
            timeline,
            actor=workspace["owner"],
            workspace_scope=dict(SHARED_SCOPE),
            source_execution_id=("isolated-shared-revision" if revised
                                 else "isolated-shared-export"),
            output_kind="audio",
            source_artifact_refs=[source_id],
            previous_artifact_id=(
                previous["artifact"]["artifact_id"] if previous is not None else None
            ),
        )


def test_shared_workspace_selector_is_exact_and_ignores_claimed_account_role(content_workspace):
    owner = content_workspace["owner"]
    ungranted = content_workspace["ungranted"]

    with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
        artifacts.list_content_projects(actor=owner)
    with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
        artifacts.list_content_projects(actor=ungranted, workspace_scope=dict(SHARED_SCOPE))

    invalid = [
        {"scope_kind": "shared_workspace", "version": True},
        {"scope_kind": "shared_workspace", "version": 1, "actor_id": owner["id"]},
        {"scope_kind": "shared_workspace", "version": 1, "domain_id": "cth"},
    ]
    for selector in invalid:
        with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
            artifacts.list_content_projects(actor=owner, workspace_scope=selector)

    conflicts = [
        {"domain_id": "bmp"},
        {"subject_id": "SUBJECT-1"},
        {"brand_focus_id": "BRAND-1"},
        {"global_scope": True},
    ]
    for conflict in conflicts:
        with pytest.raises(artifacts.LocalArtifactError, match="ACTOR_SCOPE_PERMISSION_DENIED"):
            artifacts.list_content_projects(
                actor=owner, workspace_scope=dict(SHARED_SCOPE), **conflict,
            )

    empty = artifacts.list_content_projects(
        actor=owner, workspace_scope=dict(SHARED_SCOPE),
    )
    assert empty == {"status": "empty", "projects": [], "next_cursor": None}


def test_shared_project_reopens_revises_exports_and_keeps_source_scope(content_workspace):
    imported = _import_scope4_source(content_workspace)
    source_id = imported["artifact"]["artifact_id"]
    # The original BMP path still returns only its own metadata under Scope4.
    assert artifacts.read_content_source_artifact(
        source_id, actor=content_workspace["owner"], **BMP_GLOBAL_SCOPE,
    ) == imported

    first = _stage_shared_audio(content_workspace, source_id)
    project_id = first["artifact"]["artifact_id"]
    assert first["artifact"]["product_id"] == "SHARED"
    assert first["artifact"]["domain_id"] == "content"
    assert first["project"]["context"] == {
        **SHARED_SCOPE, "actor_id": content_workspace["owner"]["id"],
    }
    assert first["project"]["source_artifact_refs"] == [source_id]
    assert first["project"]["rights"] == {"state": "unknown", "label": "rights unknown"}
    assert first["rights_state"] == "unknown"
    assert first["publish_status"] == "not_performed"

    reopened = artifacts.read_content_project(
        project_id, actor=content_workspace["owner"], workspace_scope=dict(SHARED_SCOPE),
    )
    assert reopened == {"project": first["project"], "render": first["render"]}
    media = artifacts.authorized_project_media(
        project_id, actor=content_workspace["owner"], workspace_scope=dict(SHARED_SCOPE),
    )
    assert media["data"].startswith(b"RIFF")
    assert hashlib.sha256(media["data"]).hexdigest() == first["render"]["media_sha256"]

    second = _stage_shared_audio(
        content_workspace, source_id, previous=first, revised=True,
    )
    assert second["project"]["parent_artifact_id"] == project_id
    assert second["artifact"]["artifact_id"] != project_id
    assert artifacts.read_content_project(
        project_id, actor=content_workspace["owner"], workspace_scope=dict(SHARED_SCOPE),
    ) == reopened

    own_list = artifacts.list_content_projects(
        actor=content_workspace["owner"], workspace_scope=dict(SHARED_SCOPE), limit=1,
    )
    assert own_list["status"] == "ok" and len(own_list["projects"]) == 1
    assert own_list["next_cursor"]
    peer_list = artifacts.list_content_projects(
        actor=content_workspace["peer"], workspace_scope=dict(SHARED_SCOPE),
    )
    assert peer_list == {"status": "empty", "projects": [], "next_cursor": None}
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_PROJECT_CONTEXT_MISMATCH"):
        artifacts.read_content_project(
            project_id, actor=content_workspace["peer"], workspace_scope=dict(SHARED_SCOPE),
        )
    with pytest.raises(artifacts.LocalArtifactError, match="CONTENT_PROJECT_CURSOR_INVALID"):
        artifacts.list_content_projects(
            actor=content_workspace["peer"], workspace_scope=dict(SHARED_SCOPE),
            limit=1, cursor=own_list["next_cursor"],
        )

    # Shared access does not replace the original BMP Source read permission.
    with content_workspace["repository"].transaction() as connection:
        connection.execute(
            "DELETE FROM v4_member_authorizations "
            "WHERE user_id=? AND product_id='ZBMP' AND module='content' AND action='read'",
            (content_workspace["owner"]["id"],),
        )
    with pytest.raises(
        artifacts.LocalArtifactError, match="CONTENT_SOURCE_REFERENCE_UNAVAILABLE",
    ):
        artifacts.read_content_project(
            project_id, actor=content_workspace["owner"], workspace_scope=dict(SHARED_SCOPE),
        )


def test_shared_source_import_fails_before_path_probe_hash_or_write(
    content_workspace, monkeypatch,
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Shared upload must stop before touching source files or writing")

    for name in (
        "_safe_content_source_filename", "validate_local_asset", "_hash_file",
        "_fingerprint_content_source", "_register_artifact", "artifact_root",
    ):
        monkeypatch.setattr(artifacts, name, forbidden)

    with pytest.raises(
        artifacts.LocalArtifactError, match="CONTENT_SOURCE_APPROVAL_UNAVAILABLE",
    ):
        artifacts.stage_content_source_artifact(
            object(), filename="voice.wav", actor=content_workspace["owner"],
            workspace_scope=dict(SHARED_SCOPE), source_execution_id="blocked-shared-import",
        )
    assert not content_workspace["artifact_dir"].exists()
    assert _artifact_rows(content_workspace) == []

