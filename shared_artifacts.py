"""LUMENIS Shared Capability staged-artifact boundary.

This module closes the safe local portion of ``video-shotcraft``:

* only explicitly supplied local assets are accepted;
* no URL, cookie, platform media endpoint, or external fetch is allowed;
* ffmpeg is invoked without a shell and only against validated local paths;
* output is stored below the canonical runtime data directory, never in the
  source tree by default;
* the returned artifact is staged and always remains approval-required.

It deliberately does not publish, upload, or make an external browser action.
Those effects remain behind the existing human approval and Browser Runtime
boundaries.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import uuid
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional
from urllib.parse import urlsplit

from lumenis.shared.database import get_repository, main_db_path
from lumenis.system.security.permission import LocalWorkspacePrincipal


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".aiff"}
_ASSET_EXTENSIONS = _IMAGE_EXTENSIONS | _VIDEO_EXTENSIONS | _AUDIO_EXTENSIONS
_MAX_ASSETS = 8
_MAX_ASSET_BYTES = 500 * 1024 * 1024
_MAX_BRIEF_LENGTH = 2000
_MAX_PROJECT_JSON_BYTES = 8 * 1024 * 1024
_MAX_CONTENT_PROJECT_MEDIA_BYTES = _MAX_ASSET_BYTES
_MAX_CONTENT_PROJECT_BYTES = _MAX_CONTENT_PROJECT_MEDIA_BYTES + (2 * _MAX_PROJECT_JSON_BYTES) + 65536
_MAX_CONTENT_SOURCE_BYTES = 128 * 1024 * 1024
_MAX_CONTENT_SOURCE_TOTAL_BYTES = _MAX_ASSET_BYTES
_MAX_CONTENT_SOURCE_METADATA_BYTES = 64 * 1024
_MAX_CONTENT_SOURCE_DURATION_SEC = 24 * 60 * 60
_CONTENT_SOURCE_ARTIFACT_ID = re.compile(r"ART-(?:[0-9a-f]{16}|[0-9a-f]{32})\Z")
_ARTIFACT_TABLE = "lumenis_shared_artifacts"
_CONTENT_PROJECT_LIST_SCAN_LIMIT = 100
_CONTENT_PROJECT_LIST_CURSOR_LIMIT = 256
_CONTENT_PROJECT_LIST_CURSOR_LOCK = threading.Lock()
_CONTENT_PROJECT_LIST_CURSORS: Dict[str, tuple[str, str, str]] = {}


class LocalArtifactError(ValueError):
    """A caller-supplied local artifact request is invalid."""


def artifact_root() -> Path:
    """Return the canonical protected artifact directory.

    ``ZBC_ARTIFACT_DIR`` is an explicit deployment override.  Otherwise the
    artifact directory sits beside the configured runtime database, which is
    the protected data location in the current LUMENIS deployment.
    """
    configured = str(os.environ.get("ZBC_ARTIFACT_DIR") or "").strip()
    root = Path(configured) if configured else Path(main_db_path()).resolve().parent / "artifacts"
    return root.expanduser().resolve()


def _db_connect() -> sqlite3.Connection:
    conn = get_repository().connect(timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_artifact_table() -> None:
    """Create the staged-artifact registry idempotently in the canonical DB."""
    conn = _db_connect()
    try:
        conn.execute(
            f"""CREATE TABLE IF NOT EXISTS {_ARTIFACT_TABLE} (
                artifact_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                product_id TEXT NOT NULL,
                domain_id TEXT NOT NULL,
                source_execution_id TEXT,
                evidence_id TEXT,
                note_id TEXT,
                filename TEXT NOT NULL,
                media_type TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                sha256 TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'staged',
                approval_required INTEGER NOT NULL DEFAULT 1,
                approval_status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{_ARTIFACT_TABLE}_created "
            f"ON {_ARTIFACT_TABLE}(created_at)"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{_ARTIFACT_TABLE}_execution "
            f"ON {_ARTIFACT_TABLE}(source_execution_id)"
        )
        conn.commit()
    finally:
        conn.close()


def _repo_root() -> Path:
    try:
        from repository_registry import get_registry

        return Path(get_registry().repo_root).resolve()
    except Exception:
        return Path(__file__).resolve().parent


def _allowed_asset_roots() -> List[Path]:
    roots = [
        _repo_root(),
        Path(main_db_path()).resolve().parent,
        artifact_root(),
    ]
    configured = str(os.environ.get("LUMENIS_LOCAL_ASSET_DIR") or "").strip()
    if configured:
        roots.append(Path(configured).expanduser().resolve())
    unique: List[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_local_asset(value: Any) -> Path:
    """Resolve one explicit local asset without permitting remote input."""
    raw = str(value or "").strip()
    lowered = raw.lower()
    if not raw or raw.startswith(("\\\\", "//")) or "://" in lowered or lowered.startswith(("data:", "javascript:")):
        raise LocalArtifactError("LOCAL_ASSET_REQUIRED")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise LocalArtifactError("LOCAL_ASSET_MUST_BE_ABSOLUTE")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise LocalArtifactError("LOCAL_ASSET_NOT_FOUND") from exc
    if not resolved.is_file():
        raise LocalArtifactError("LOCAL_ASSET_NOT_FILE")
    if resolved.suffix.lower() not in _ASSET_EXTENSIONS:
        raise LocalArtifactError("LOCAL_ASSET_TYPE_NOT_ALLOWED")
    if resolved.stat().st_size > _MAX_ASSET_BYTES:
        raise LocalArtifactError("LOCAL_ASSET_TOO_LARGE")
    if not any(_is_relative_to(resolved, root) for root in _allowed_asset_roots()):
        raise LocalArtifactError("LOCAL_ASSET_OUTSIDE_ALLOWED_ROOT")
    return resolved


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ffmpeg_path() -> Optional[str]:
    configured = str(os.environ.get("LUMENIS_FFMPEG_PATH") or os.environ.get("FFMPEG_PATH") or "").strip()
    candidates: List[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    found = shutil.which("ffmpeg")
    if found:
        candidates.append(Path(found))
    # The current toolchain archive is adjacent to the canonical D: workspace;
    # resolve it from the repository instead of using the retired D:\lum-toolchain path.
    candidates.append(_repo_root().parent / "_TOOLCHAIN_ARCHIVE_20260912" / "ffmpeg" / "bin" / "ffmpeg.exe")
    candidates.append(_repo_root() / "tools" / "ffmpeg.exe")
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
            if resolved.is_file():
                return str(resolved)
        except OSError:
            continue
    return None


def _run_ffmpeg(command: List[str], timeout: int = 180) -> None:
    """Run a local ffmpeg command without shell expansion or network access."""
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    if completed.returncode != 0:
        raise LocalArtifactError("FFMPEG_RENDER_FAILED")


def _video_filter() -> str:
    return (
        "scale=1280:720:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
    )


def _concat_quote(path: Path) -> str:
    # concat demuxer syntax; paths have already passed local-root validation.
    return path.as_posix().replace("'", "'\\''")


def _new_artifact_id() -> str:
    return "ART-" + uuid.uuid4().hex[:16]


def _shared_content_source_artifact_id(approval_token: str) -> str:
    """Derive one stable registry key from the exact server approval nonce."""
    if type(approval_token) is not str or not approval_token:
        raise LocalArtifactError("CONTENT_SOURCE_APPROVAL_UNVERIFIED")
    digest = hashlib.sha256(
        b"lumenis:shared-content-source-artifact:v1:" + approval_token.encode("utf-8")
    ).hexdigest()
    return "ART-" + digest[:32]


def _register_artifact(
    *,
    artifact_id: str,
    kind: str,
    product_id: str,
    domain_id: str,
    source_execution_id: str,
    evidence_id: str,
    note_id: str,
    path: Path,
    media_type: str,
) -> Dict[str, Any]:
    root = artifact_root()
    try:
        relative_path = path.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise LocalArtifactError("ARTIFACT_OUTSIDE_CANONICAL_ROOT") from exc
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record = {
        "artifact_id": artifact_id,
        "kind": kind,
        "product_id": product_id,
        "domain_id": domain_id,
        "source_execution_id": source_execution_id,
        "evidence_id": evidence_id,
        "note_id": note_id,
        "filename": path.name,
        "media_type": media_type,
        "relative_path": relative_path,
        "size_bytes": path.stat().st_size,
        "sha256": _hash_file(path),
        "status": "staged",
        "approval_required": True,
        "approval_status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    ensure_artifact_table()
    conn = _db_connect()
    try:
        conn.execute(
            f"""INSERT INTO {_ARTIFACT_TABLE}
               (artifact_id,kind,product_id,domain_id,source_execution_id,evidence_id,note_id,
                filename,media_type,relative_path,size_bytes,sha256,status,approval_required,
                approval_status,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            tuple(record[key] for key in (
                "artifact_id", "kind", "product_id", "domain_id", "source_execution_id",
                "evidence_id", "note_id", "filename", "media_type", "relative_path",
                "size_bytes", "sha256", "status", "approval_required", "approval_status",
                "created_at", "updated_at",
            )),
        )
        conn.commit()
    finally:
        conn.close()
    return record


def _content_project_scope(
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    global_scope: bool = False,
    shared_workspace_scope: Mapping[str, Any] | None = None,
) -> tuple[int | None, dict[str, Any]]:
    actor_id = actor.get("id") if isinstance(actor, Mapping) else None
    if type(actor) is not LocalWorkspacePrincipal and (
        type(actor_id) is not int or actor_id <= 0
    ):
        raise LocalArtifactError("ACTOR_SCOPE_PERMISSION_DENIED")
    if shared_workspace_scope is not None:
        if (domain_id is not None or subject_id is not None or brand_focus_id is not None
                or type(global_scope) is not bool or global_scope is not False):
            raise LocalArtifactError("CONTENT_SCOPE_MIXED_CONTEXT")
        try:
            from lumenis.system.security.permission import (
                validate_shared_workspace_scope,
            )

            normalized = validate_shared_workspace_scope(shared_workspace_scope)
        except (TypeError, ValueError) as exc:
            raise LocalArtifactError("SHARED_WORKSPACE_SCOPE_INVALID") from exc
        return actor_id, {"shared_workspace_scope": normalized}
    if not isinstance(domain_id, str) or not domain_id.strip():
        raise LocalArtifactError("ACTOR_SCOPE_PERMISSION_DENIED")
    if type(global_scope) is not bool:
        raise LocalArtifactError("ACTOR_SCOPE_PERMISSION_DENIED")

    normalized_domain = domain_id.strip().lower()
    if normalized_domain in {"bmp", "zbmp"}:
        normalized_domain = "zbmp"
    scope = {
        "domain_id": normalized_domain,
        "subject_id": subject_id,
        "brand_focus_id": brand_focus_id,
        "global_scope": global_scope,
    }
    return actor_id, scope


def _authorize_content_project(
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    *,
    domain_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    global_scope: bool = False,
    action: str,
    shared_workspace_scope: Mapping[str, Any] | None = None,
) -> tuple[int | None, dict[str, Any]]:
    actor_id, scope = _content_project_scope(
        actor=actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope,
    )
    if "shared_workspace_scope" in scope:
        from lumenis.system.security.permission import authorize_shared_workspace

        try:
            authorize_shared_workspace(
                actor, scope["shared_workspace_scope"],
                module="content", action=action,
            )
        except Exception as exc:
            raise LocalArtifactError("ACTOR_SCOPE_PERMISSION_DENIED") from exc
        return actor_id, scope
    from lumenis.system.security.permission import (
        check_actor_scope_permission, check_local_workspace_scope_permission,
    )

    scope_checker = (
        check_local_workspace_scope_permission
        if type(actor) is LocalWorkspacePrincipal else check_actor_scope_permission
    )
    decision = scope_checker(
        actor,
        action=action,
        module="content",
        **scope,
    )
    if decision.allowed is not True or decision.verification_state != "verified":
        raise LocalArtifactError("ACTOR_SCOPE_PERMISSION_DENIED")
    return actor_id, scope


def _content_project_storage_identity(scope: Mapping[str, Any]) -> tuple[str, str]:
    if "shared_workspace_scope" in scope:
        return "SHARED", "content"
    domain_id = scope.get("domain_id")
    if domain_id == "cth":
        return "CTH", "cth"
    if domain_id == "zbmp":
        return "ZBMP", "zbmp"
    raise LocalArtifactError("ACTOR_SCOPE_PERMISSION_DENIED")


def _content_artifact_context(
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    actor_id: Optional[int], scope: Mapping[str, Any],
) -> Dict[str, Any]:
    """Serialize ownership after authorization; keep account manifests unchanged."""
    context = {"actor_id": actor_id, **scope}
    if type(actor) is LocalWorkspacePrincipal:
        context.update(
            principal_kind=actor.principal_kind, principal_ref=actor.principal_ref,
        )
    return context


def _content_project_export_resource_for_context(
    context: Mapping[str, Any], timeline_data: Mapping[str, Any],
    source_refs: list[str], output_kind: str, previous_artifact_id: str | None,
    render_options: dict | None = None, delivery_options: dict | None = None,
    title: str | None = None, render_media: bool = True,
) -> str:
    return "content-project-export:v1:" + hashlib.sha256(_json_bytes({
        "context": dict(context), "timeline": dict(timeline_data),
        "source_refs": list(source_refs), "output_kind": output_kind,
        "parent_artifact_id": previous_artifact_id,
        **({"render_options": render_options} if render_options else {}),
        **({"delivery_options": delivery_options} if delivery_options else {}),
        **({"title": title} if title is not None else {}),
        **({"render_media": False} if not render_media else {}),
    })).hexdigest()


def content_project_export_resource(
    timeline: Any, *, actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    source_artifact_refs: list[str] | None, output_kind: str,
    previous_artifact_id: str | None = None, render_options: dict | None = None, delivery_options: dict | None = None,
    domain_id: str | None = None, subject_id: str | None = None,
    brand_focus_id: str | None = None, global_scope: bool = False,
    shared_workspace_scope: Mapping[str, Any] | None = None,
    title: str | None = None, render_media: bool = True,
) -> str:
    """Bind the existing export Permission request to the exact project inputs."""
    from lumenis.shared.content_creation.rendering import validate_render_options
    render_options = validate_render_options(render_options)
    delivery_options = _validate_content_delivery_options(delivery_options)
    _validate_content_project_save(title, render_media, delivery_options)
    actor_id, scope = _authorize_content_project(
        actor, domain_id=domain_id, subject_id=subject_id,
        brand_focus_id=brand_focus_id, global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope, action="write",
    )
    try:
        timeline_data = timeline.to_dict()
    except Exception as exc:
        raise LocalArtifactError("CONTENT_TIMELINE_INVALID") from exc
    if not isinstance(timeline_data, dict) or _contains_local_path_field(timeline_data):
        raise LocalArtifactError("CONTENT_TIMELINE_INVALID")
    refs, _, _ = _validate_content_source_refs(
        [] if source_artifact_refs is None else source_artifact_refs,
        actor=actor, domain_id=domain_id, subject_id=subject_id,
        brand_focus_id=brand_focus_id, global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope,
    )
    return _content_project_export_resource_for_context(
        _content_artifact_context(actor, actor_id, scope), timeline_data,
        refs, output_kind, previous_artifact_id, render_options, delivery_options,
        title, render_media,
    )


def _validate_content_project_save(title, render_media, delivery_options=None):
    if type(render_media) is not bool:
        raise LocalArtifactError("INVALID_CONTENT_INPUT")
    if title is not None and (
        not isinstance(title, str) or not title.strip() or title != title.strip()
        or len(title) > 200 or any(ord(char) < 32 for char in title)
    ):
        raise LocalArtifactError("CONTENT_PROJECT_TITLE_INVALID")
    if not render_media and title is None:
        raise LocalArtifactError("CONTENT_PROJECT_TITLE_INVALID")


def _artifact_record(artifact_id: str, *, read_only: bool = False) -> Optional[Dict[str, Any]]:
    if not artifact_id or len(str(artifact_id)) > 80:
        return None
    if read_only:
        conn = get_repository().connect(timeout=10, read_only=True, wal=False)
        conn.row_factory = sqlite3.Row
    else:
        ensure_artifact_table()
        conn = _db_connect()
    try:
        row = conn.execute(
            f"SELECT * FROM {_ARTIFACT_TABLE} WHERE artifact_id=?", (str(artifact_id),)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def _contains_local_path_field(value: Any) -> bool:
    path_fields = {"path", "local_path", "source_path", "absolute_path", "asset_path"}
    if isinstance(value, Mapping):
        return any(
            str(key).casefold() in path_fields or _contains_local_path_field(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_local_path_field(item) for item in value)
    return False


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LocalArtifactError("CONTENT_PROJECT_METADATA_INVALID") from exc
    if len(encoded) > _MAX_PROJECT_JSON_BYTES:
        raise LocalArtifactError("CONTENT_PROJECT_METADATA_TOO_LARGE")
    return encoded


def _verified_content_project(
    artifact_id: str,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    global_scope: bool = False,
    shared_workspace_scope: Mapping[str, Any] | None = None,
    read_only_registry: bool = False,
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Path]:
    actor_id, scope = _authorize_content_project(
        actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope,
        action="read",
    )
    record = _artifact_record(artifact_id, read_only=read_only_registry)
    if not record or record.get("kind") != "content_project":
        raise LocalArtifactError("CONTENT_PROJECT_NOT_FOUND")

    expected_product, expected_domain = _content_project_storage_identity(scope)
    if record.get("domain_id") != expected_domain or record.get("product_id") != expected_product:
        raise LocalArtifactError("CONTENT_PROJECT_CONTEXT_MISMATCH")
    root = artifact_root()
    candidate = (root / str(record.get("relative_path") or "")).resolve()
    if not _is_relative_to(candidate, root) or not candidate.is_file():
        raise LocalArtifactError("CONTENT_PROJECT_NOT_FOUND")
    size = candidate.stat().st_size
    if size <= 0 or size > _MAX_CONTENT_PROJECT_BYTES or size != record.get("size_bytes"):
        raise LocalArtifactError("CONTENT_PROJECT_INTEGRITY_FAILED")
    if _hash_file(candidate) != record.get("sha256"):
        raise LocalArtifactError("CONTENT_PROJECT_INTEGRITY_FAILED")

    expected_context = _content_artifact_context(actor, actor_id, scope)
    try:
        with zipfile.ZipFile(candidate, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            basic_names = {"project.json", "render.json", "media.mp4", "media.wav", "captions.srt", "captions.vtt"}
            if (not 2 <= len(names) <= 85 or len(set(names)) != len(names)
                    or any(name not in basic_names and not _content_delivery_filename(name) for name in names)
                    or (("captions.srt" in names) != ("captions.vtt" in names))):
                raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID")
            project_infos = [info for info in infos if info.filename == "project.json"]
            render_infos = [info for info in infos if info.filename == "render.json"]
            media_infos = [info for info in infos if info.filename in {"media.mp4", "media.wav"}]
            if len(project_infos) != 1 or len(render_infos) != 1 or len(media_infos) > 1:
                raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID")
            for info in infos:
                limit = (
                    _MAX_CONTENT_PROJECT_MEDIA_BYTES
                    if info.filename in {"media.mp4", "media.wav"} or _content_delivery_filename(info.filename)
                    else _MAX_PROJECT_JSON_BYTES
                )
                if (
                    info.file_size > limit
                    or info.compress_type != zipfile.ZIP_STORED
                    or info.flag_bits & 0x1
                ):
                    raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID")
            project_data = json.loads(archive.read(project_infos[0]).decode("utf-8"))
            render_data = json.loads(archive.read(render_infos[0]).decode("utf-8"))
            manifest = project_data.get("delivery_manifest", {}) if isinstance(project_data, dict) else None
            extra_names = set(names) - basic_names
            if not isinstance(manifest, dict) or set(manifest) != extra_names:
                raise LocalArtifactError("CONTENT_DELIVERY_MANIFEST_INVALID")
            for name, info in manifest.items():
                raw = archive.read(name)
                if info != {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}:
                    raise LocalArtifactError("CONTENT_DELIVERY_INTEGRITY_FAILED")
    except LocalArtifactError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID") from exc

    source_artifact_refs = project_data.get("source_artifact_refs", []) if isinstance(project_data, dict) else None
    if (
        not isinstance(project_data, dict)
        or type(project_data.get("schema_version")) is not int
        or project_data.get("schema_version") not in {1, 2}
        or project_data.get("context") != expected_context
        or project_data.get("output_kind") not in {"video", "audio"}
        or project_data.get("rights") not in ({"state": "unknown", "label": "rights unknown"}, {
            "state": "unknown",
            "demo_acknowledged": True,
            "label": "demo-only / rights unknown",
        })
        or not isinstance(project_data.get("timeline"), dict)
        or _contains_local_path_field(project_data.get("timeline"))
        or not isinstance(source_artifact_refs, list)
        or len(source_artifact_refs) > 64
        or any(not isinstance(ref, str) or not _CONTENT_SOURCE_ARTIFACT_ID.fullmatch(ref)
               for ref in source_artifact_refs)
        or len(set(source_artifact_refs)) != len(source_artifact_refs)
        or not isinstance(render_data, dict)
        or render_data.get("output_kind") != project_data.get("output_kind")
        or _contains_local_path_field(render_data)
    ):
        raise LocalArtifactError("CONTENT_PROJECT_CONTEXT_MISMATCH")
    draft = render_data.get("state") == "not_rendered"
    if project_data["schema_version"] == 2:
        _validate_content_project_save(project_data.get("title"), not draft)
        if (project_data.get("title") is None or type(project_data.get("project_revision")) is not int
                or project_data["project_revision"] < 1):
            raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID")
    if draft:
        if (project_data["schema_version"] != 2 or not source_artifact_refs or media_infos
                or set(names) - {"project.json", "render.json", "credits.json", "credits.txt"}
                or render_data != {"state": "not_rendered", "output_kind": project_data["output_kind"],
                                   "timeline_version": project_data["timeline"].get("version")}):
            raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID")
    elif (render_data.get("state") != "rendered_verified" or len(media_infos) != 1
          or not isinstance(render_data.get("measurement"), dict)):
        raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID")
    _, verified_sources, _ = _validate_content_source_refs(
        source_artifact_refs, actor=actor,
        domain_id=scope.get("domain_id"),
        subject_id=scope.get("subject_id"),
        brand_focus_id=scope.get("brand_focus_id"),
        global_scope=scope.get("global_scope", False),
        shared_workspace_scope=scope.get("shared_workspace_scope"),
    )
    expected_credits = _content_license_credits(verified_sources, project_data["timeline"], project_data.get("render_options"))
    if project_data.get("media_credits") != expected_credits:
        raise LocalArtifactError("CONTENT_MEDIA_CREDITS_MISMATCH")
    expected_credit_files = _content_license_credit_files(expected_credits) if expected_credits is not None else {}
    with zipfile.ZipFile(candidate, "r") as archive:
        if ({name for name in names if name in {"credits.json", "credits.txt"}} != set(expected_credit_files)
                or any(archive.read(name) != data for name, data in expected_credit_files.items())):
            raise LocalArtifactError("CONTENT_MEDIA_CREDITS_MISMATCH")
    project_data["source_artifact_refs"] = list(source_artifact_refs)
    expected_media = "media.mp4" if project_data["output_kind"] == "video" else "media.wav"
    claimed_media_hash = render_data.get("media_sha256")
    claimed_media_size = render_data.get("size_bytes")
    if not draft and (
        media_infos[0].filename != expected_media
        or media_infos[0].file_size <= 0
        or media_infos[0].file_size > _MAX_CONTENT_PROJECT_MEDIA_BYTES
        or type(claimed_media_size) is not int
        or claimed_media_size != media_infos[0].file_size
        or not isinstance(claimed_media_hash, str)
        or len(claimed_media_hash) != 64
        or any(character not in "0123456789abcdef" for character in claimed_media_hash)
    ):
        raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID")
    parent_id = project_data.get("parent_artifact_id")
    if parent_id is not None and (
        not isinstance(parent_id, str) or not parent_id.startswith("ART-")
    ):
        raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID")
    _authorize_content_project(actor, action="read", **scope)
    return project_data, render_data, {**record, "media_member": None if draft else expected_media}, candidate


_MEDIA_LICENSE_MAX_BYTES = 16 * 1024
_MEDIA_LICENSE_URLS = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
}


def parse_media_license_header(raw: str | None) -> dict | None:
    """Parse inert, bounded user declarations. Never fetch a URL or grant rights."""
    if raw is None:
        return None
    try:
        if not isinstance(raw, str) or len(raw.encode("utf-8", errors="strict")) > _MEDIA_LICENSE_MAX_BYTES:
            raise ValueError()
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError()
                result[key] = value
            return result
        value = json.loads(raw, object_pairs_hook=unique_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if value is None:
            raise ValueError()
        return validate_media_license(value)
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise LocalArtifactError("CONTENT_MEDIA_LICENSE_INVALID") from exc


def validate_media_license(value: Any, *, asset_sha256: str | None = None) -> dict | None:
    """Asset license declaration only; code/model/voice consent is a separate owner.

    This records what was supplied, not an independently verified legal conclusion.
    Unknown general rights and all Permission gates are intentionally unchanged.
    """
    if value is None:
        return None
    keys = {"schema_version", "object_kind", "license_id", "license_url", "source_url",
            "source_version", "asset_sha256", "creator", "title", "notice", "changes",
            "evidence_text", "evidence_sha256"}
    try:
        if (type(value) is not dict or set(value) != keys
                or type(value["schema_version"]) is not int or value["schema_version"] != 1
                or value["object_kind"] != "media_asset"):
            raise ValueError()
        for key in keys - {"schema_version"}:
            text = value[key]
            if (not isinstance(text, str)
                    or (key != "evidence_text" and text != text.strip())
                    or (not text.strip() and key not in {"notice", "changes"})
                    or any(ord(char) < 32 and char not in ("\n\r\t" if key == "evidence_text" else "\n") for char in text)
                    or any(ord(char) == 127 for char in text)):
                raise ValueError()
        if (value["license_id"] not in _MEDIA_LICENSE_URLS
                or value["license_url"] != _MEDIA_LICENSE_URLS[value["license_id"]]
                or not re.fullmatch(r"[0-9a-f]{64}", value["asset_sha256"])
                or not re.fullmatch(r"[0-9a-f]{64}", value["evidence_sha256"])
                or (asset_sha256 is not None and value["asset_sha256"] != asset_sha256)
                or hashlib.sha256(value["evidence_text"].encode("utf-8")).hexdigest() != value["evidence_sha256"]):
            raise ValueError()
        for key in ("source_url", "license_url"):
            url = value[key]
            parsed = urlsplit(url)
            # Locator only: reject embedded credentials, query tokens and fragments.
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                    or parsed.password or parsed.query or parsed.fragment
                    or any(char.isspace() for char in url) or "\\" in url
                    or "%" in parsed.netloc or parsed.port not in (None, 443)):
                raise ValueError()
        if len(_json_bytes(value)) > _MEDIA_LICENSE_MAX_BYTES:
            raise ValueError()
    except (ValueError, TypeError, UnicodeError, KeyError, RecursionError) as exc:
        raise LocalArtifactError("CONTENT_MEDIA_LICENSE_INVALID") from exc
    return dict(value)


def _media_license_digest(value: dict | None) -> str | None:
    return hashlib.sha256(_json_bytes(value)).hexdigest() if value is not None else None


def _media_license_public(metadata: Mapping[str, Any]) -> dict:
    if metadata.get("schema_version") != 2:
        return {}
    return {"media_license": metadata["media_license"],
            "media_license_sha256": metadata["media_license_sha256"],
            "license_verification_state": "declared_not_independently_verified"}


def _content_license_credits(entries: list, timeline: dict, render_options: dict | None = None) -> dict | None:
    if not any(entry["metadata"].get("schema_version") == 2 for entry in entries):
        return None
    sources = []
    for entry in entries:
        metadata, record = entry["metadata"], entry["record"]
        asset = metadata["asset"]
        uses = []
        for track in timeline.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("media_asset_id") == asset["asset_id"]:
                    uses.append({"track_id": track["track_id"], "track_kind": track["kind"], "clip": clip})
        sources.append({"artifact_id": record["artifact_id"], "artifact_sha256": record["sha256"],
                        "asset_id": asset["asset_id"], "asset_sha256": asset["sha256"],
                        "media_license": metadata.get("media_license"),
                        "media_license_sha256": metadata.get("media_license_sha256"),
                        "license_verification_state": ("declared_not_independently_verified"
                                                       if metadata.get("media_license") else "unknown"),
                        "actual_timeline_uses": uses})
    return {"schema_version": 1, "rights_state": "unknown",
            "notice": "License declarations are not independently verified; code/model licenses and personal voice consent are not granted.",
            "timeline_version": timeline["version"],
            "actual_render_options": render_options or {},
            "actual_transitions": timeline.get("transitions", []),
            "actual_overlays": timeline.get("overlays", []),
            "timeline_sha256": hashlib.sha256(_json_bytes(timeline)).hexdigest(), "sources": sources}


def _content_license_credit_files(credits: dict) -> dict[str, bytes]:
    lines = ["Media credits", credits["notice"],
             "Timeline version: " + str(credits["timeline_version"]),
             "Render options: " + json.dumps(credits["actual_render_options"], ensure_ascii=False, sort_keys=True),
             "Transitions: " + json.dumps(credits["actual_transitions"], ensure_ascii=False, sort_keys=True),
             "Overlays: " + json.dumps(credits["actual_overlays"], ensure_ascii=False, sort_keys=True)]
    for item in credits["sources"]:
        lines.extend(["", "Asset: " + item["asset_id"], "Source artifact: " + item["artifact_id"],
                      "Asset SHA256: " + item["asset_sha256"],
                      "License verification: " + item["license_verification_state"]])
        declaration = item["media_license"]
        if declaration:
            for key in ("title", "creator", "source_url", "source_version", "license_id", "license_url", "notice", "changes"):
                lines.append(key + ": " + declaration[key])
        lines.append("Actual edit operations (source in/out, placement and effects): " +
                     json.dumps(item["actual_timeline_uses"], ensure_ascii=False, sort_keys=True))
    return {"credits.json": _json_bytes(credits), "credits.txt": ("\n".join(lines) + "\n").encode("utf-8")}


def _safe_content_source_filename(filename: Any) -> str:
    if not isinstance(filename, str) or not filename or len(filename) > 255:
        raise LocalArtifactError("CONTENT_SOURCE_FILENAME_INVALID")
    if (
        filename in {".", ".."}
        or filename.startswith(".")
        or filename[-1] in {".", " "}
        or any(ord(character) < 32 or ord(character) == 127 for character in filename)
        or any(character in filename for character in '<>:"/\\|?*')
        or Path(filename).name != filename
    ):
        raise LocalArtifactError("CONTENT_SOURCE_FILENAME_INVALID")
    extension = Path(filename).suffix.lower()
    if extension not in _ASSET_EXTENSIONS:
        raise LocalArtifactError("LOCAL_ASSET_TYPE_NOT_ALLOWED")
    stem = filename.split(".", 1)[0].rstrip(" .").upper()
    if stem in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"(?:COM|LPT)[1-9]", stem):
        raise LocalArtifactError("CONTENT_SOURCE_FILENAME_INVALID")
    return filename


def _source_asset_metadata_is_valid(asset: Any, media_filename: str) -> bool:
    if isinstance(asset, dict) and asset.get("media_kind") == "image":
        try:
            return asset == _ImageSourceAsset(
                media_filename, asset["sha256"], asset["width"], asset["height"],
            ).to_dict()
        except (KeyError, ValueError, TypeError):
            return False
    expected_fields = {
        "asset_id", "filename", "sha256", "duration_sec", "media_kind", "has_video",
        "audio_stream_count", "evidence_refs", "rights_status",
    }
    if not isinstance(asset, dict) or set(asset) != expected_fields:
        return False
    digest = asset.get("sha256")
    try:
        duration = float(asset.get("duration_sec"))
    except (TypeError, ValueError, OverflowError):
        return False
    return (
        asset.get("filename") == media_filename
        and isinstance(digest, str)
        and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
        and asset.get("asset_id") == f"MEDIA-{digest[:16]}"
        and type(asset.get("duration_sec")) in {int, float}
        and duration > 0
        and duration <= _MAX_CONTENT_SOURCE_DURATION_SEC
        and duration < float("inf")
        and asset.get("media_kind") in {"video_audio", "video", "audio"}
        and type(asset.get("has_video")) is bool
        and type(asset.get("audio_stream_count")) is int
        and 0 <= asset["audio_stream_count"] <= 256
        and (
            (asset["media_kind"] == "video_audio" and asset["has_video"] and asset["audio_stream_count"] > 0)
            or (asset["media_kind"] == "video" and asset["has_video"] and asset["audio_stream_count"] == 0)
            or (asset["media_kind"] == "audio" and not asset["has_video"] and asset["audio_stream_count"] > 0)
        )
        and asset.get("evidence_refs") == []
        and asset.get("rights_status") == "unknown"
    )


@dataclass(frozen=True)
class _ImageSourceAsset:
    filename: str
    sha256: str
    width: int
    height: int
    rights_status = "unknown"
    evidence_refs = ()

    def to_dict(self):
        if (Path(self.filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}
                or not re.fullmatch(r"[0-9a-f]{64}", str(self.sha256))
                or type(self.width) is not int or type(self.height) is not int
                or min(self.width, self.height) < 1 or self.width * self.height > 40_000_000):
            raise LocalArtifactError("CONTENT_IMAGE_METADATA_INVALID")
        return {"asset_id": "MEDIA-" + self.sha256[:16], "filename": self.filename,
                "sha256": self.sha256, "duration_sec": None, "media_kind": "image",
                "has_video": False, "audio_stream_count": 0, "width": self.width,
                "height": self.height, "evidence_refs": [], "rights_status": "unknown"}


def _fingerprint_content_source(path):
    """Static images have no duration; never invent a video duration for them."""
    from lumenis.shared.content_creation.video_editing import fingerprint_local_media, _ffprobe_path

    if path.suffix.lower() not in _IMAGE_EXTENSIONS:
        return fingerprint_local_media(str(path))
    ffprobe = _ffprobe_path()
    if not ffprobe:
        raise LocalArtifactError("CONTENT_IMAGE_PROBE_UNAVAILABLE")
    before = path.stat()
    digest = _hash_file(path)
    try:
        output = subprocess.run(
            [ffprobe, "-v", "error", "-protocol_whitelist", "file",
             "-format_whitelist", "image2,jpeg_pipe,png_pipe,webp_pipe",
             "-show_entries", "stream=codec_name,width,height", "-of", "json", "-i", str(path)],
            check=True, capture_output=True, text=True, timeout=15, shell=False,
        )
        streams = json.loads(output.stdout).get("streams", [])
        expected = {".jpg": "mjpeg", ".jpeg": "mjpeg", ".png": "png", ".webp": "webp"}
        if len(streams) != 1 or streams[0].get("codec_name") != expected.get(path.suffix.lower()):
            raise ValueError("unsupported image stream")
        result = _ImageSourceAsset(path.name, digest, streams[0]["width"], streams[0]["height"])
        result.to_dict()
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        raise LocalArtifactError("CONTENT_IMAGE_PROBE_FAILED") from exc
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise LocalArtifactError("CONTENT_SOURCE_CHANGED_DURING_IMPORT")
    return result


def _verified_content_source(
    artifact_id: str,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    global_scope: bool = False,
    shared_workspace_scope: Mapping[str, Any] | None = None,
    action: str = "read",
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Path]:
    actor_id, scope = _authorize_content_project(
        actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope,
        action=action,
    )
    if not isinstance(artifact_id, str) or not _CONTENT_SOURCE_ARTIFACT_ID.fullmatch(artifact_id):
        raise LocalArtifactError("CONTENT_SOURCE_NOT_FOUND")
    record = _artifact_record(artifact_id)
    if not record or record.get("kind") != "content_source":
        raise LocalArtifactError("CONTENT_SOURCE_NOT_FOUND")
    shared_request = "shared_workspace_scope" in scope
    source_domain = record.get("domain_id")
    source_product = record.get("product_id")
    if shared_request:
        if (source_domain, source_product) not in {
            ("content", "SHARED"), ("cth", "CTH"), ("zbmp", "ZBMP"),
        }:
            raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    elif (source_domain, source_product) != _content_project_storage_identity(scope)[::-1]:
        # Storage columns are (product_id, domain_id); reverse the helper tuple.
        raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    root = artifact_root()
    candidate = (root / str(record.get("relative_path") or "")).resolve()
    if not _is_relative_to(candidate, root) or not candidate.is_file():
        raise LocalArtifactError("CONTENT_SOURCE_NOT_FOUND")
    size = candidate.stat().st_size
    max_package_size = _MAX_CONTENT_SOURCE_BYTES + _MAX_CONTENT_SOURCE_METADATA_BYTES + 4096
    if size <= 0 or size > max_package_size or size != record.get("size_bytes"):
        raise LocalArtifactError("CONTENT_SOURCE_INTEGRITY_FAILED")
    if _hash_file(candidate) != record.get("sha256"):
        raise LocalArtifactError("CONTENT_SOURCE_INTEGRITY_FAILED")

    expected_context = _content_artifact_context(actor, actor_id, scope)
    try:
        with zipfile.ZipFile(candidate, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(infos) != 2 or len(set(names)) != 2 or "source.json" not in names:
                raise LocalArtifactError("CONTENT_SOURCE_ARCHIVE_INVALID")
            metadata_info = archive.getinfo("source.json")
            media_infos = [info for info in infos if info.filename != "source.json"]
            if len(media_infos) != 1:
                raise LocalArtifactError("CONTENT_SOURCE_ARCHIVE_INVALID")
            media_info = media_infos[0]
            media_filename = _safe_content_source_filename(media_info.filename)
            if (
                metadata_info.file_size > _MAX_CONTENT_SOURCE_METADATA_BYTES
                or metadata_info.compress_type != zipfile.ZIP_STORED
                or media_info.file_size <= 0
                or media_info.file_size > _MAX_CONTENT_SOURCE_BYTES
                or media_info.compress_type != zipfile.ZIP_STORED
                or metadata_info.flag_bits & 0x1
                or media_info.flag_bits & 0x1
            ):
                raise LocalArtifactError("CONTENT_SOURCE_ARCHIVE_INVALID")
            metadata = json.loads(archive.read(metadata_info).decode("utf-8"))
    except LocalArtifactError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocalArtifactError("CONTENT_SOURCE_ARCHIVE_INVALID") from exc

    source_context = metadata.get("context") if isinstance(metadata, dict) else None
    if shared_request and isinstance(source_context, dict) and "domain_id" in source_context:
        expected_context = _content_source_original_context(
            source_context, actor=actor, shared_actor_id=actor_id,
            record_domain=source_domain, record_product=source_product, action=action,
        )
    if (
        not isinstance(metadata, dict)
        or type(metadata.get("schema_version")) is not int
        or metadata.get("schema_version") not in {1, 2}
        or set(metadata) != ({"schema_version", "context", "asset", "media_filename", "rights_state"}
                            | ({"media_license", "media_license_sha256"} if metadata.get("schema_version") == 2 else set()))
        or source_context != expected_context
        or metadata.get("media_filename") != media_filename
        or metadata.get("rights_state") != "unknown"
        or not _source_asset_metadata_is_valid(metadata.get("asset"), media_filename)
        or media_info.file_size <= 0
    ):
        raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    if metadata["schema_version"] == 2:
        declaration = validate_media_license(metadata["media_license"], asset_sha256=metadata["asset"]["sha256"])
        if declaration is None or _media_license_digest(declaration) != metadata["media_license_sha256"]:
            raise LocalArtifactError("CONTENT_MEDIA_LICENSE_INTEGRITY_FAILED")
    digest = hashlib.sha256()
    with zipfile.ZipFile(candidate, "r") as archive, archive.open(media_filename) as media:
        for chunk in iter(lambda: media.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != metadata["asset"]["sha256"]:
        raise LocalArtifactError("CONTENT_SOURCE_INTEGRITY_FAILED")
    if record.get("media_type") != "application/zip":
        raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    _authorize_content_project(actor, action=action, **scope)
    return metadata, {**record, "media_member": media_filename, "media_size_bytes": media_info.file_size}, expected_context, candidate


def _content_source_original_context(
    context: Mapping[str, Any], *, actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    shared_actor_id: int | None, record_domain: Any, record_product: Any,
    action: str,
) -> dict[str, Any]:
    """Reauthorize a CTH/BMP source in its immutable original business scope."""
    base_keys = {"actor_id", "domain_id", "subject_id", "brand_focus_id", "global_scope"}
    local_keys = base_keys | {"principal_kind", "principal_ref"}
    if type(context) is not dict or frozenset(context) not in {frozenset(base_keys), frozenset(local_keys)}:
        raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    domain_id = context.get("domain_id")
    if domain_id not in {"cth", "zbmp"}:
        raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    expected_product, expected_domain = _content_project_storage_identity({"domain_id": domain_id})
    if (record_product, record_domain) != (expected_product, expected_domain):
        raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    source_actor_id = context.get("actor_id")
    if shared_actor_id is not None:
        if (type(source_actor_id) is not int or source_actor_id != shared_actor_id
                or "principal_kind" in context or "principal_ref" in context):
            raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    else:
        if (type(actor) is not LocalWorkspacePrincipal or source_actor_id is not None
                or context.get("principal_kind") != actor.principal_kind
                or context.get("principal_ref") != actor.principal_ref):
            raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    try:
        _actor_id, original_scope = _authorize_content_project(
            actor,
            domain_id=domain_id,
            subject_id=context.get("subject_id"),
            brand_focus_id=context.get("brand_focus_id"),
            global_scope=context.get("global_scope"),
            action=action,
        )
    except LocalArtifactError:
        raise
    except Exception as exc:
        raise LocalArtifactError("CONTENT_SOURCE_SCOPE_DENIED") from exc
    if _content_artifact_context(actor, _actor_id, original_scope) != dict(context):
        raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    return dict(context)


def _recover_shared_source_after_evidence_failure(
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    shared_workspace_scope: Mapping[str, Any],
    filename: str,
    size_bytes: int,
    body_sha256: str,
    license_metadata_sha256: str | None = None,
) -> dict[str, Any] | None:
    """Reuse an exact committed source from a failed Skill Evidence finalization.

    The prior execution trace is the recovery receipt. A candidate is returned
    only when its stored input matches this upload exactly and the current
    caller can still reauthorize and read the source through the Content owner.
    This keeps retries from creating a second Artifact after a transient
    Evidence write failure, while leaving the original failed trace intact.
    """
    actor_id, scope = _authorize_content_project(
        actor, shared_workspace_scope=shared_workspace_scope, action="write",
    )
    if "shared_workspace_scope" not in scope:
        return None
    expected_input = {
        "actor_id": actor_id,
        "scope": scope,
        "filename": filename,
        "size_bytes": size_bytes,
        "body_sha256": body_sha256,
        "effect_mode": "staging",
        **({"license_metadata_sha256": license_metadata_sha256} if license_metadata_sha256 else {}),
    }
    try:
        ensure_artifact_table()
        connection = _db_connect()
        try:
            rows = connection.execute(
                f"""SELECT a.artifact_id, a.source_execution_id, e.execution_id,
                           e.input_json, e.output_json, e.user_id
                    FROM {_ARTIFACT_TABLE} AS a
                    JOIN skill_executions AS e
                      ON e.execution_id = a.source_execution_id
                    WHERE a.kind='content_source'
                      AND a.product_id='SHARED' AND a.domain_id='content'
                      AND e.skill_id='shared.content_project'
                      AND e.status='failed' AND e.error='EVIDENCE_RECORD_FAILED'
                      AND e.user_id IS ?
                    ORDER BY e.rowid DESC LIMIT 128""",
                (actor_id,),
            ).fetchall()
        finally:
            connection.close()
    except Exception:  # noqa: BLE001 -- unreadable recovery records never grant reuse.
        # Recovery is an optimization for an already-proven exact request; a
        # missing trace table or unreadable receipt must never authorize reuse.
        return None

    for row in rows:
        try:
            if json.loads(row["input_json"] or "null") != expected_input:
                continue
            output = json.loads(row["output_json"] or "null")
            result = output.get("result") if isinstance(output, dict) else None
            artifact = result.get("artifact") if isinstance(result, dict) else None
            if not isinstance(artifact, dict) or artifact.get("artifact_id") != row["artifact_id"]:
                continue
            if row["source_execution_id"] != row["execution_id"]:
                continue
            metadata, record, _context, _package_path = _verified_content_source(
                row["artifact_id"], actor=actor,
                shared_workspace_scope=shared_workspace_scope, action="write",
            )
            asset = metadata.get("asset")
            if (
                not isinstance(asset, dict)
                or asset.get("sha256") != body_sha256
                or metadata.get("media_filename") != filename
                or metadata.get("media_license_sha256") != license_metadata_sha256
                or record.get("media_size_bytes") != size_bytes
                or record.get("source_execution_id") != row["source_execution_id"]
            ):
                continue
            public_record = {
                key: record[key]
                for key in (
                    "artifact_id", "kind", "product_id", "domain_id", "source_execution_id",
                    "filename", "media_type", "size_bytes", "sha256", "status",
                    "approval_required", "approval_status", "created_at", "updated_at",
                )
            }
            return {"artifact": public_record, "asset": asset, "rights_state": "unknown", **_media_license_public(metadata)}
        except Exception:  # noqa: BLE001, S112 -- skip one malformed recovery candidate.
            continue
    return None


def _validate_content_source_refs(
    artifact_refs: Any,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    global_scope: bool = False,
    shared_workspace_scope: Mapping[str, Any] | None = None,
) -> tuple[list[str], list[dict[str, Any]], int]:
    if (
        not isinstance(artifact_refs, list)
        or len(artifact_refs) > 64
        or any(not isinstance(ref, str) or not _CONTENT_SOURCE_ARTIFACT_ID.fullmatch(ref) for ref in artifact_refs)
    ):
        raise LocalArtifactError("CONTENT_SOURCE_REFS_INVALID")
    if len(set(artifact_refs)) != len(artifact_refs):
        raise LocalArtifactError("CONTENT_SOURCE_REF_DUPLICATE")
    entries: List[Dict[str, Any]] = []
    asset_ids: set[str] = set()
    total_size = 0
    for artifact_id in artifact_refs:
        metadata, record, source_context, package_path = _verified_content_source(
            artifact_id,
            actor=actor,
            domain_id=domain_id,
            subject_id=subject_id,
            brand_focus_id=brand_focus_id,
            global_scope=global_scope,
            shared_workspace_scope=shared_workspace_scope,
        )
        if (
            shared_workspace_scope is not None
            and isinstance(source_context, dict)
            and source_context.get("domain_id") in {"cth", "zbmp"}
        ):
            # A CTH/BMP upload confirmation is scoped to that domain's private
            # draft. Existing content:read and DATA_EXPORT checks do not grant
            # its separate use in an independent Shared workspace; require the
            # exact source-use approval before accepting this reference.
            raise LocalArtifactError("CONTENT_SOURCE_USE_PERMISSION_REQUIRED")
        asset_id = metadata["asset"]["asset_id"]
        if asset_id in asset_ids:
            raise LocalArtifactError("CONTENT_SOURCE_ASSET_DUPLICATE")
        asset_ids.add(asset_id)
        total_size += int(record["media_size_bytes"])
        if total_size > _MAX_CONTENT_SOURCE_TOTAL_BYTES:
            raise LocalArtifactError("CONTENT_SOURCE_TOTAL_TOO_LARGE")
        entries.append({"metadata": metadata, "record": record, "package_path": package_path,
                        "source_context": source_context})
    return list(artifact_refs), entries, total_size


def stage_content_source_artifact(
    asset_path: Any,
    *,
    filename: str,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    global_scope: bool = False,
    shared_workspace_scope: Mapping[str, Any] | None = None,
    source_execution_id: str,
    expected_sha256: Optional[str] = None,
    media_license: dict | None = None,
) -> Dict[str, Any]:
    """Package one probed upload as an immutable, scope-bound canonical Artifact."""
    actor_id, scope = _authorize_content_project(
        actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope,
        action="write",
    )
    safe_filename = _safe_content_source_filename(filename)
    path = validate_local_asset(asset_path)
    source_stat = path.stat()
    if path.name != safe_filename or source_stat.st_size <= 0 or source_stat.st_size > _MAX_CONTENT_SOURCE_BYTES:
        raise LocalArtifactError("CONTENT_SOURCE_SIZE_INVALID")
    if not isinstance(source_execution_id, str) or not source_execution_id.strip():
        raise LocalArtifactError("SOURCE_EXECUTION_ID_REQUIRED")
    # Bind the approval to the observed bytes before probing/decoding media.
    # An unapproved request must not depend on FFprobe/FFmpeg availability and
    # must not spend decoder work before the Permission owner has allowed it.
    observed_sha256 = _hash_file(path)
    media_license = validate_media_license(media_license, asset_sha256=observed_sha256)
    license_digest = _media_license_digest(media_license)
    if expected_sha256 is not None and observed_sha256 != expected_sha256:
        raise LocalArtifactError("CONTENT_SOURCE_CHANGED_DURING_IMPORT")
    from lumenis.system.security.permission import (
        ContentSourceImport, check_content_source_import_permission, get_permission_gate,
    )

    gate = get_permission_gate()
    principal = actor if type(actor) is LocalWorkspacePrincipal else None
    permission_actor = None if principal is not None else actor
    shared_scope = scope.get("shared_workspace_scope")
    upload = ContentSourceImport(
        actor_id=actor_id,
        domain_id=(None if shared_scope is not None else
                   "bmp" if scope["domain_id"] == "zbmp" else "cth"),
        subject_id=None if shared_scope is not None else subject_id,
        brand_focus_id=None if shared_scope is not None else brand_focus_id,
        global_scope=False if shared_scope is not None else global_scope,
        filename=safe_filename, size_bytes=source_stat.st_size, body_sha256=observed_sha256,
        principal_kind=principal.principal_kind if principal is not None else None,
        principal_ref=principal.principal_ref if principal is not None else None,
        scope_kind=shared_scope.get("scope_kind") if shared_scope is not None else None,
        scope_version=shared_scope.get("version") if shared_scope is not None else None,
        license_metadata_sha256=license_digest,
    )
    permission = check_content_source_import_permission(
        permission_actor, upload, principal=principal, gate=gate,
    )
    if not permission.allowed:
        raise LocalArtifactError("CONTENT_SOURCE_APPROVAL_REQUIRED")
    if not (
        permission.approval_token and permission.resource and permission.caller
    ):
        raise LocalArtifactError("CONTENT_SOURCE_APPROVAL_UNVERIFIED")
    if shared_scope is not None:
        recovered = _recover_shared_source_after_evidence_failure(
            actor=actor, shared_workspace_scope=shared_scope,
            filename=safe_filename, size_bytes=source_stat.st_size,
            body_sha256=observed_sha256, license_metadata_sha256=license_digest,
        )
        if recovered is not None:
            with gate._content_import_artifact_commit(
                permission.approval_token, permission.resource, permission.caller,
            ) as can_commit:
                if not can_commit:
                    raise LocalArtifactError("CONTENT_SOURCE_APPROVAL_REQUIRED")
            return recovered
    asset = _fingerprint_content_source(path)
    if asset.sha256 != observed_sha256:
        raise LocalArtifactError("CONTENT_SOURCE_CHANGED_DURING_IMPORT")
    if asset.filename != safe_filename or asset.rights_status != "unknown" or asset.evidence_refs:
        raise LocalArtifactError("CONTENT_SOURCE_METADATA_INVALID")
    expected_context = _content_artifact_context(actor, actor_id, scope)
    source_metadata = {
        "schema_version": 1,
        "context": expected_context,
        "asset": asset.to_dict(),
        "media_filename": safe_filename,
        "rights_state": "unknown",
    }
    if media_license is not None:
        source_metadata.update(schema_version=2, media_license=media_license, media_license_sha256=license_digest)
    metadata_bytes = _json_bytes(source_metadata)
    if len(metadata_bytes) > _MAX_CONTENT_SOURCE_METADATA_BYTES:
        raise LocalArtifactError("CONTENT_SOURCE_METADATA_TOO_LARGE")

    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    if shared_scope is not None:
        artifact_id = _shared_content_source_artifact_id(permission.approval_token)
        package_path = root / f"{artifact_id}.{uuid.uuid4().hex}.zip"
    else:
        artifact_id = _new_artifact_id()
        package_path = root / f"{artifact_id}.zip"
    package_created = False
    registered = False
    try:
        try:
            package_handle = package_path.open("xb")
        except FileExistsError as exc:
            raise LocalArtifactError("CONTENT_SOURCE_ID_COLLISION") from exc
        package_created = True
        with package_handle, zipfile.ZipFile(
            package_handle, mode="w", compression=zipfile.ZIP_STORED,
        ) as archive:
            archive.writestr("source.json", metadata_bytes)
            archive.write(path, safe_filename)
        archived_digest = hashlib.sha256()
        archived_size = 0
        with zipfile.ZipFile(package_path, "r") as archive, archive.open(
            safe_filename, "r",
        ) as media:
            while True:
                chunk = media.read(1024 * 1024)
                if not chunk:
                    break
                archived_size += len(chunk)
                archived_digest.update(chunk)
        after_stat = path.stat()
        if (
            archived_size != source_stat.st_size
            or (after_stat.st_size, after_stat.st_mtime_ns) != (source_stat.st_size, source_stat.st_mtime_ns)
            or archived_digest.hexdigest() != asset.sha256
        ):
            raise LocalArtifactError("CONTENT_SOURCE_CHANGED_DURING_IMPORT")
        # Decoding/packaging can take time. Recheck before registering a result.
        permission = check_content_source_import_permission(
            permission_actor, upload, principal=principal, gate=gate,
        )
        if not permission.allowed:
            raise LocalArtifactError("CONTENT_SOURCE_APPROVAL_REQUIRED")
        product_id, artifact_domain = _content_project_storage_identity(scope)
        def register_artifact():
            nonlocal registered
            try:
                registered_record = _register_artifact(
                    artifact_id=artifact_id,
                    kind="content_source",
                    product_id=product_id,
                    domain_id=artifact_domain,
                    source_execution_id=source_execution_id.strip(),
                    evidence_id="",
                    note_id="",
                    path=package_path,
                    media_type="application/zip",
                )
            except sqlite3.IntegrityError as exc:
                if shared_scope is None:
                    raise
                try:
                    existing_metadata, existing_record, _context, _existing_path = (
                        _verified_content_source(
                            artifact_id, actor=actor,
                            shared_workspace_scope=shared_scope, action="write",
                        )
                    )
                except Exception as verification_error:
                    raise LocalArtifactError(
                        "CONTENT_SOURCE_IDEMPOTENCY_CONFLICT"
                    ) from verification_error
                if (
                    existing_metadata.get("context") != expected_context
                    or existing_metadata.get("asset") != asset.to_dict()
                    or existing_metadata.get("media_filename") != safe_filename
                    or existing_metadata.get("rights_state") != "unknown"
                    or existing_metadata.get("media_license_sha256") != license_digest
                    or existing_record.get("media_size_bytes") != source_stat.st_size
                ):
                    raise LocalArtifactError(
                        "CONTENT_SOURCE_IDEMPOTENCY_CONFLICT"
                    ) from exc
                return existing_record
            registered = True
            return registered_record

        if shared_scope is not None:
            with gate._content_import_artifact_commit(
                permission.approval_token, permission.resource, permission.caller,
            ) as can_commit:
                if not can_commit:
                    raise LocalArtifactError("CONTENT_SOURCE_APPROVAL_REQUIRED")
                record = register_artifact()
        else:
            record = register_artifact()
            gate.revoke_approval(permission.approval_token)
    finally:
        if package_created and not registered:
            try:
                package_path.unlink(missing_ok=True)
            except OSError:
                pass

    public_record = {
        key: record[key]
        for key in (
            "artifact_id", "kind", "product_id", "domain_id", "source_execution_id",
            "filename", "media_type", "size_bytes", "sha256", "status",
            "approval_required", "approval_status", "created_at", "updated_at",
        )
    }
    return {"artifact": public_record, "asset": asset.to_dict(), "rights_state": "unknown", **_media_license_public(source_metadata)}


def read_content_source_artifact(
    artifact_id: str,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    global_scope: bool = False,
    shared_workspace_scope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return authorized source metadata only; the original media is never served here."""
    metadata, record, _, _ = _verified_content_source(
        artifact_id,
        actor=actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope,
    )
    public_record = {
        key: record[key]
        for key in (
            "artifact_id", "kind", "product_id", "domain_id", "source_execution_id",
            "filename", "media_type", "size_bytes", "sha256", "status",
            "approval_required", "approval_status", "created_at", "updated_at",
        )
    }
    return {"artifact": public_record, "asset": metadata["asset"], "rights_state": "unknown", **_media_license_public(metadata)}


@contextmanager
def resolve_content_source_assets(
    artifact_refs: Any,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    global_scope: bool = False,
    shared_workspace_scope: Mapping[str, Any] | None = None,
) -> Iterator[list[dict[str, Any]]]:
    """Reauthorize and stream verified source entries to temporary local files."""
    if not isinstance(artifact_refs, list) or not 1 <= len(artifact_refs) <= 64:
        raise LocalArtifactError("CONTENT_SOURCE_REFS_INVALID")
    refs, entries, _ = _validate_content_source_refs(
        artifact_refs,
        actor=actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope,
    )

    resolved: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="content-source-open-", dir=str(artifact_root())) as work_dir:
        root = Path(work_dir)
        for index, entry in enumerate(entries):
            metadata = entry["metadata"]
            member = entry["record"]["media_member"]
            destination_dir = root / f"{index:02d}"
            destination_dir.mkdir()
            destination = destination_dir / member
            digest = hashlib.sha256()
            copied = 0
            try:
                with zipfile.ZipFile(entry["package_path"], "r") as archive:
                    with archive.open(member, "r") as source, destination.open("xb") as target:
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            copied += len(chunk)
                            if copied > _MAX_CONTENT_SOURCE_BYTES:
                                raise LocalArtifactError("CONTENT_SOURCE_SIZE_INVALID")
                            digest.update(chunk)
                            target.write(chunk)
                if copied != entry["record"]["media_size_bytes"] or digest.hexdigest() != metadata["asset"]["sha256"]:
                    raise LocalArtifactError("CONTENT_SOURCE_INTEGRITY_FAILED")
                fresh_asset = _fingerprint_content_source(destination)
                if fresh_asset.to_dict() != metadata["asset"]:
                    raise LocalArtifactError("CONTENT_SOURCE_FINGERPRINT_MISMATCH")
            except LocalArtifactError:
                raise
            except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
                raise LocalArtifactError("CONTENT_SOURCE_ARCHIVE_INVALID") from exc
            resolved.append({"artifact_ref": refs[index], "path": destination, "asset": fresh_asset})
        _authorize_content_project(
            actor, domain_id=domain_id, subject_id=subject_id,
            brand_focus_id=brand_focus_id, global_scope=global_scope,
            shared_workspace_scope=shared_workspace_scope, action="read",
        )
        for entry in entries:
            source_context = entry.get("source_context")
            if isinstance(source_context, dict) and "domain_id" in source_context:
                _content_source_original_context(
                    source_context, actor=actor,
                    shared_actor_id=actor.get("id") if isinstance(actor, Mapping) else None,
                    record_domain=entry["record"].get("domain_id"),
                    record_product=entry["record"].get("product_id"), action="read",
                )
        yield resolved


def stage_timeline_artifact(
    timeline: Any,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    global_scope: bool = False,
    shared_workspace_scope: Mapping[str, Any] | None = None,
    source_execution_id: str,
    demo_acknowledged: Optional[bool] = None,
    output_kind: str = "video",
    previous_artifact_id: Optional[str] = None,
    source_artifact_refs: Optional[List[str]] = None,
    render_options: dict | None = None,
    delivery_options: dict | None = None,
    operation_binding: dict | None = None,
    title: str | None = None,
    render_media: bool = True,
) -> Dict[str, Any]:
    """Render a permission-scoped project without an additional demo checkbox.

    The optional legacy demo argument is accepted for older clients, but never
    authorizes rendering. Source read/write scope and DATA_EXPORT admission are
    checked independently; unknown rights remain unknown in the stored result.
    """
    from lumenis.shared.content_creation.rendering import validate_render_options
    render_options = validate_render_options(render_options)
    delivery_options = _validate_content_delivery_options(delivery_options)
    _validate_content_project_save(title, render_media, delivery_options)
    if operation_binding and (title is not None or not render_media):
        raise LocalArtifactError("CONTENT_EDL_OPERATION_BINDING_INVALID")
    actor_id, scope = _authorize_content_project(
        actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope,
        action="write",
    )
    if operation_binding is not None and (not isinstance(operation_binding, dict)
            or set(operation_binding) != {"operation_id", "resource"}
            or re.fullmatch(r"content-edl:[0-9a-f]{64}", str(operation_binding.get("operation_id", ""))) is None
            or re.fullmatch(r"content-project-export:v1:[0-9a-f]{64}", str(operation_binding.get("resource", ""))) is None):
        raise LocalArtifactError("CONTENT_EDL_OPERATION_BINDING_INVALID")
    if not isinstance(source_execution_id, str) or not source_execution_id.strip():
        raise LocalArtifactError("SOURCE_EXECUTION_ID_REQUIRED")
    if demo_acknowledged is not None and type(demo_acknowledged) is not bool:
        raise LocalArtifactError("INVALID_CONTENT_INPUT")
    if output_kind not in {"video", "audio"}:
        raise LocalArtifactError("OUTPUT_KIND_NOT_SUPPORTED")

    from lumenis.shared.content_creation.video_editing import Timeline

    if not isinstance(timeline, Timeline):
        raise LocalArtifactError("CONTENT_TIMELINE_INVALID")
    try:
        timeline.validate()
        timeline_data = timeline.to_dict()
    except Exception as exc:
        raise LocalArtifactError("CONTENT_TIMELINE_INVALID") from exc
    if not isinstance(timeline_data, dict) or _contains_local_path_field(timeline_data):
        raise LocalArtifactError("CONTENT_TIMELINE_INVALID")
    if any(getattr(asset, "rights_status", "unknown") != "unknown" for asset in timeline.assets):
        raise LocalArtifactError("CONTENT_RIGHTS_STATE_UNAVAILABLE")

    source_refs, source_entries, _ = _validate_content_source_refs(
        [] if source_artifact_refs is None else source_artifact_refs,
        actor=actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope,
    )
    if not render_media and not source_refs:
        raise LocalArtifactError("CONTENT_ORIGINAL_FILES_REQUIRED")
    if source_refs:
        source_assets = [entry["metadata"]["asset"] for entry in source_entries]
        if [asset.to_dict() for asset in timeline.assets] != source_assets:
            raise LocalArtifactError("CONTENT_SOURCE_TIMELINE_MISMATCH")

    expected_context = _content_artifact_context(actor, actor_id, scope)
    parent_project: Optional[Dict[str, Any]] = None
    if previous_artifact_id is not None:
        parent_project, parent_render, _, _ = _verified_content_project(
            previous_artifact_id,
            actor=actor,
            domain_id=domain_id,
            subject_id=subject_id,
            brand_focus_id=brand_focus_id,
            global_scope=global_scope,
            shared_workspace_scope=shared_workspace_scope,
        )
        if (
            parent_project.get("context") != expected_context
            or parent_project.get("output_kind") != output_kind
        ):
            raise LocalArtifactError("CONTENT_PROJECT_PARENT_SCOPE_MISMATCH")
        parent_timeline = parent_project.get("timeline")
        parent_version = parent_timeline.get("version") if isinstance(parent_timeline, dict) else None
        current_version = getattr(timeline, "version", None)
        metadata_revision = (
            timeline_data == parent_timeline
            and (title is not None and title != parent_project.get("title")
                 or render_options != parent_project.get("render_options", {})
                 or delivery_options != parent_project.get("delivery_options", {})
                 or render_media and parent_render.get("state") == "not_rendered")
        )
        if (
            type(parent_version) is not int
            or type(current_version) is not int
            or current_version < parent_version
            or current_version == parent_version and not metadata_revision
        ):
            raise LocalArtifactError("CONTENT_PROJECT_PARENT_REVISION_REQUIRED")

    stored_title = title if title is not None else (parent_project or {}).get("title")

    from lumenis.system.security.permission import OperationType, get_permission_gate, is_testing_bypass_enabled

    if is_testing_bypass_enabled():
        raise LocalArtifactError("CONTENT_EXPORT_PERMISSION_UNVERIFIED")
    export_resource = _content_project_export_resource_for_context(
        expected_context, timeline_data, source_refs, output_kind, previous_artifact_id, render_options, delivery_options,
        title, render_media,
    )
    gate = get_permission_gate()
    caller = expected_context["principal_ref"] if actor_id is None else f"actor:{actor_id}"
    if "shared_workspace_scope" in scope:
        from lumenis.system.security.permission import check_shared_workspace_effect

        export_permission = check_shared_workspace_effect(
            actor, scope["shared_workspace_scope"], OperationType.DATA_EXPORT,
            export_resource, module="content", action="write", gate=gate,
        )
    else:
        export_permission = gate.check(
            OperationType.DATA_EXPORT, resource=export_resource,
            caller=caller, domain_id="bmp" if scope["domain_id"] == "zbmp" else "cth",
        )
    if not export_permission.allowed:
        raise LocalArtifactError("CONTENT_EXPORT_PERMISSION_DENIED")

    def check_export_permission() -> None:
        # Use the canonical owner throughout encoding, not a copied authorization.
        _authorize_content_project(actor, action="write", **scope)
        for entry in source_entries:
            source_context = entry.get("source_context")
            if isinstance(source_context, dict) and "domain_id" in source_context:
                _content_source_original_context(
                    source_context, actor=actor, shared_actor_id=actor_id,
                    record_domain=entry["record"].get("domain_id"),
                    record_product=entry["record"].get("product_id"), action="read",
                )
        if "shared_workspace_scope" in scope:
            current = check_shared_workspace_effect(
                actor, scope["shared_workspace_scope"], OperationType.DATA_EXPORT,
                export_resource, module="content", action="write", gate=gate,
            )
        else:
            current = gate.check(
                OperationType.DATA_EXPORT, resource=export_resource,
                caller=caller, domain_id="bmp" if scope["domain_id"] == "zbmp" else "cth",
            )
        if not current.allowed or is_testing_bypass_enabled():
            raise LocalArtifactError("CONTENT_EXPORT_PERMISSION_DENIED")
        if operation_binding and not gate.get_valid_approval_token(
                OperationType.DATA_EXPORT.value, operation_binding["resource"], exact=True):
            raise LocalArtifactError("CONTENT_EDL_EXACT_APPROVAL_REQUIRED")

    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    artifact_id = _content_edl_artifact_id(operation_binding["operation_id"]) if operation_binding else _new_artifact_id()
    media_suffix = ".mp4" if output_kind == "video" else ".wav"
    media_name = f"media{media_suffix}"
    package_path = root / f"{artifact_id}.zip"
    product_id, artifact_domain = _content_project_storage_identity(scope)
    render_result: Optional[Mapping[str, Any]] = None
    package_created = False
    try:
        with tempfile.TemporaryDirectory(prefix="content-project-", dir=str(root)) as work_dir:
            rendered_path = Path(work_dir) / media_name
            from lumenis.shared.content_creation.rendering import render_timeline, subtitle_documents

            if render_media:
                measured = render_timeline(timeline, rendered_path, output_kind=output_kind,
                                           check_continue=check_export_permission,
                                           **({"render_options": render_options} if render_options else {}))
                if (
                    not isinstance(measured, Mapping)
                    or measured.get("state") != "rendered_verified"
                    or measured.get("output_kind") != output_kind
                    or not rendered_path.is_file()
                ):
                    raise LocalArtifactError("CONTENT_RENDER_UNVERIFIED")
                media_size = rendered_path.stat().st_size
                media_hash = _hash_file(rendered_path)
                if (
                    media_size <= 0
                    or media_size > _MAX_CONTENT_PROJECT_MEDIA_BYTES
                    or measured.get("size_bytes") != media_size
                    or measured.get("media_sha256") != media_hash
                ):
                    raise LocalArtifactError("CONTENT_RENDER_INTEGRITY_FAILED")
                render_result = dict(measured)
                try:
                    subtitle_output = subtitle_documents(timeline)
                    render_result["subtitle_export"] = {"state": "exported" if subtitle_output else "not_applicable",
                                                        "files": list(subtitle_output)}
                except ValueError as exc:
                    if str(exc) != "SUBTITLE_TEXT_NOT_SUPPORTED":
                        raise
                    subtitle_output = {}
                    render_result["subtitle_export"] = {"state": "unsupported", "reason": str(exc), "files": []}
                delivery_files, delivery_reports = _build_content_delivery(
                    timeline, rendered_path, output_kind=output_kind, options=delivery_options,
                    render_options=render_options, check_continue=check_export_permission)
            else:
                render_result = {"state": "not_rendered", "output_kind": output_kind,
                                 "timeline_version": timeline.version}
                subtitle_output, delivery_files, delivery_reports = {}, {}, {}
            credits = _content_license_credits(source_entries, timeline_data, render_options)
            if credits is not None:
                delivery_files.update(_content_license_credit_files(credits))
            if len(delivery_files) > 80 or sum(map(len, delivery_files.values())) > 128 * 1024 * 1024:
                raise LocalArtifactError("CONTENT_DELIVERY_TOO_LARGE")
            delivery_manifest = {name: {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
                                 for name, data in delivery_files.items()}
            if delivery_reports:
                render_result["delivery_reports"] = delivery_reports
            project = {
                "schema_version": 2 if stored_title is not None else 1,
                **({"title": stored_title, "project_revision": (parent_project or {}).get("project_revision", 0) + 1}
                   if stored_title is not None else {}),
                **({"operation_binding": operation_binding} if operation_binding else {}),
                **({"delivery_options": delivery_options, "delivery_manifest": delivery_manifest} if delivery_manifest or delivery_options else {}),
                **({"media_credits": credits} if credits is not None else {}),
                **({"render_options": render_options} if render_options else {}),
                "timeline": timeline_data,
                "source_artifact_refs": source_refs,
                "context": expected_context,
                "parent_artifact_id": previous_artifact_id,
                "rights": {
                    "state": "unknown",
                    "label": "rights unknown",
                },
                "output_kind": output_kind,
            }
            project_bytes = _json_bytes(project)
            render_bytes = _json_bytes(render_result)
            if len(project_bytes) > _MAX_PROJECT_JSON_BYTES or len(render_bytes) > _MAX_PROJECT_JSON_BYTES:
                raise LocalArtifactError("CONTENT_PROJECT_PACKAGE_TOO_LARGE")
            try:
                package_handle = package_path.open("xb")
            except FileExistsError as exc:
                raise LocalArtifactError("CONTENT_PROJECT_ID_COLLISION") from exc
            package_created = True
            with package_handle:
                with zipfile.ZipFile(
                    package_handle, mode="w", compression=zipfile.ZIP_STORED
                ) as archive:
                    archive.writestr("project.json", project_bytes)
                    archive.writestr("render.json", render_bytes)
                    if render_media:
                        archive.write(rendered_path, media_name)
                    for name, data in delivery_files.items():
                        archive.writestr(name, data)
                    for name, text in subtitle_output.items():
                        archive.writestr(name, text.encode("utf-8"))
        package_size = package_path.stat().st_size
        if package_size > _MAX_CONTENT_PROJECT_BYTES:
            raise LocalArtifactError("CONTENT_PROJECT_PACKAGE_TOO_LARGE")
        check_export_permission()
        record = _register_artifact(
            artifact_id=artifact_id,
            kind="content_project",
            product_id=product_id,
            domain_id=artifact_domain,
            source_execution_id=source_execution_id.strip(),
            evidence_id="",
            note_id="",
            path=package_path,
            media_type="application/zip",
        )
    except Exception:
        if package_created:
            try:
                package_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise

    public_record = {
        key: record[key]
        for key in (
            "artifact_id", "kind", "product_id", "domain_id", "source_execution_id",
            "filename", "media_type", "size_bytes", "sha256", "status",
            "approval_required", "approval_status", "created_at", "updated_at",
        )
    }
    return {
        "status": "rendered_staged" if render_media else "project_saved",
        "artifact": public_record,
        "project": project,
        "render": dict(render_result or {}),
        "rights_state": "unknown",
        "approval_required": True,
        "publish_status": "not_performed",
    }


def read_content_project(
    artifact_id: str,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    global_scope: bool = False,
    shared_workspace_scope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return verified project and render metadata without source filesystem paths."""
    project, render, _, _ = _verified_content_project(
        artifact_id,
        actor=actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope,
    )
    return {"project": project, "render": render}


def _content_project_list_cursor(identity: str, boundary: Mapping[str, Any]) -> str:
    created_at = boundary.get("created_at")
    artifact_id = boundary.get("artifact_id")
    if not isinstance(created_at, str) or not isinstance(artifact_id, str):
        raise LocalArtifactError("CONTENT_PROJECT_LIST_UNAVAILABLE")
    token = secrets.token_urlsafe(32)
    with _CONTENT_PROJECT_LIST_CURSOR_LOCK:
        if len(_CONTENT_PROJECT_LIST_CURSORS) >= _CONTENT_PROJECT_LIST_CURSOR_LIMIT:
            _CONTENT_PROJECT_LIST_CURSORS.clear()
        _CONTENT_PROJECT_LIST_CURSORS[token] = (identity, created_at, artifact_id)
    return token


def _content_project_list_boundary(cursor: Optional[str], identity: str) -> Optional[tuple[str, str]]:
    if cursor is None:
        return None
    if not isinstance(cursor, str) or not re.fullmatch(r"[A-Za-z0-9_-]{40,48}", cursor):
        raise LocalArtifactError("CONTENT_PROJECT_CURSOR_INVALID")
    with _CONTENT_PROJECT_LIST_CURSOR_LOCK:
        state = _CONTENT_PROJECT_LIST_CURSORS.get(cursor)
        if state is None or state[0] != identity:
            raise LocalArtifactError("CONTENT_PROJECT_CURSOR_INVALID")
    return state[1], state[2]


def _content_project_candidates(scope: Mapping[str, Any], boundary: Optional[tuple[str, str]], limit: int):
    conn = get_repository().connect(timeout=10, read_only=True, wal=False)
    conn.row_factory = sqlite3.Row
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (_ARTIFACT_TABLE,),
        ).fetchone()
        if not exists:
            return [], False, False
        where = ""
        params = [_content_project_storage_identity(scope)[1]]
        if boundary:
            where = " AND (created_at>? OR (created_at=? AND artifact_id>?))"
            params.extend((boundary[0], boundary[0], boundary[1]))
        params.append(limit + 1)
        rows = conn.execute(
            f"SELECT artifact_id,created_at,size_bytes FROM {_ARTIFACT_TABLE} "
            "WHERE kind='content_project' AND domain_id=?" + where +
            " ORDER BY created_at,artifact_id LIMIT ?", params,
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows[:limit]], len(rows) > limit, True


def _content_project_list_result(status: str, projects: List[Dict[str, Any]], identity=None, boundary=None):
    return {"status": status, "projects": projects,
            "next_cursor": _content_project_list_cursor(identity, boundary) if identity and boundary else None}


def list_content_projects(*, actor: Mapping[str, Any] | LocalWorkspacePrincipal,
                          domain_id: str | None = None, subject_id: str | None = None,
                          brand_focus_id: str | None = None, global_scope: bool = False,
                          shared_workspace_scope: Mapping[str, Any] | None = None,
                          limit: int = 20, cursor: str | None = None) -> dict[str, Any]:
    """List verified project summaries; cursors are opaque process-local keyset handles."""
    actor_id, scope = _authorize_content_project(
        actor, domain_id=domain_id, subject_id=subject_id,
        brand_focus_id=brand_focus_id, global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope, action="read",
    )
    if type(limit) is not int or not 1 <= limit <= 20:
        raise LocalArtifactError("CONTENT_PROJECT_LIST_LIMIT_INVALID")
    identity = hashlib.sha256(_json_bytes(_content_artifact_context(actor, actor_id, scope))).hexdigest()
    boundary = _content_project_list_boundary(cursor, identity)
    try:
        candidates, has_more, table_exists = _content_project_candidates(
            scope, boundary, _CONTENT_PROJECT_LIST_SCAN_LIMIT,
        )
    except sqlite3.Error as exc:
        raise LocalArtifactError("CONTENT_PROJECT_LIST_UNAVAILABLE") from exc
    if not table_exists:
        return _content_project_list_result("empty", [])

    projects: List[Dict[str, Any]] = []
    page_boundary: Optional[Mapping[str, Any]] = None
    verified_bytes = 0
    last_scanned: Optional[Mapping[str, Any]] = None
    for candidate in candidates:
        artifact_id = candidate.get("artifact_id")
        size_bytes = candidate.get("size_bytes")
        if type(size_bytes) is not int or not 0 < size_bytes <= _MAX_CONTENT_PROJECT_BYTES:
            return _content_project_list_result("integrity_incomplete", projects, identity, candidate)
        if verified_bytes and verified_bytes + size_bytes > _MAX_CONTENT_PROJECT_BYTES:
            return _content_project_list_result("scan_incomplete", projects, identity, last_scanned)
        verified_bytes += size_bytes
        last_scanned = candidate
        if not isinstance(artifact_id, str) or not _CONTENT_SOURCE_ARTIFACT_ID.fullmatch(artifact_id):
            return _content_project_list_result("integrity_incomplete", projects, identity, candidate)
        try:
            project, render, record, _ = _verified_content_project(
                artifact_id,
                actor=actor,
                domain_id=domain_id,
                subject_id=subject_id,
                brand_focus_id=brand_focus_id,
                global_scope=global_scope,
                shared_workspace_scope=shared_workspace_scope,
                read_only_registry=True,
            )
        except LocalArtifactError as exc:
            code = str(exc)
            if code == "CONTENT_PROJECT_CONTEXT_MISMATCH":
                continue
            if code in {
                "CONTENT_PROJECT_NOT_FOUND", "CONTENT_PROJECT_INTEGRITY_FAILED",
                "CONTENT_PROJECT_ARCHIVE_INVALID", "CONTENT_PROJECT_INTEGRITY_UNVERIFIED",
            }:
                return _content_project_list_result("integrity_incomplete", projects, identity, candidate)
            raise
        except OSError:
            return _content_project_list_result("integrity_incomplete", projects, identity, candidate)
        except sqlite3.Error as exc:
            raise LocalArtifactError("CONTENT_PROJECT_LIST_UNAVAILABLE") from exc
        projects.append({
            "artifact_id": artifact_id,
            "output_kind": project["output_kind"],
            "title": project.get("title"),
            "project_revision": project.get("project_revision"),
            "render_state": render["state"],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
            "status": record["status"],
        })
        if len(projects) > limit:
            return _content_project_list_result("ok", projects[:limit], identity, page_boundary)
        page_boundary = candidate

    if has_more and candidates:
        return _content_project_list_result("scan_incomplete", projects, identity, last_scanned)
    return _content_project_list_result("ok" if projects else "empty", projects)


def authorized_project_media(
    artifact_id: str,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str | None = None,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    global_scope: bool = False,
    shared_workspace_scope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return authorized package media bytes and safe display metadata."""
    project, render, record, package_path = _verified_content_project(
        artifact_id,
        actor=actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope,
    )
    if render["state"] != "rendered_verified":
        raise LocalArtifactError("CONTENT_PROJECT_NOT_RENDERED")
    try:
        with zipfile.ZipFile(package_path, "r") as archive:
            info = archive.getinfo(record["media_member"])
            data = archive.read(info)
    except (OSError, zipfile.BadZipFile, KeyError, RuntimeError) as exc:
        raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID") from exc
    extension = ".mp4" if project["output_kind"] == "video" else ".wav"
    if len(data) != render.get("size_bytes") or hashlib.sha256(data).hexdigest() != render.get("media_sha256"):
        raise LocalArtifactError("CONTENT_PROJECT_INTEGRITY_FAILED")
    _authorize_content_project(
        actor, domain_id=domain_id, subject_id=subject_id,
        brand_focus_id=brand_focus_id, global_scope=global_scope,
        shared_workspace_scope=shared_workspace_scope, action="read",
    )
    return {
        "artifact_id": artifact_id,
        "filename": f"{artifact_id}{extension}",
        "media_type": "video/mp4" if extension == ".mp4" else "audio/wav",
        "output_kind": project["output_kind"],
        "data": data,
    }


def render_local_video_artifact(
    asset_paths: Iterable[Any],
    *,
    brief: str = "",
    product_id: Optional[str] = None,
    domain_id: Optional[str] = None,
    source_execution_id: str = "",
    evidence_id: str = "",
    note_id: str = "",
) -> Dict[str, Any]:
    """Render explicit local assets into a staged MP4 artifact.

    The function never invents media when assets are absent.  It returns a
    metadata-only staged artifact record only after ffmpeg has produced a real
    file from the validated inputs.
    """
    from domain_isolation import resolve_domain_identity

    try:
        domain_id, product_id = resolve_domain_identity(
            domain_id=domain_id, product_id=product_id,
        )
    except ValueError as exc:
        raise LocalArtifactError(str(exc)) from exc
    if not domain_id or not product_id:
        raise LocalArtifactError("ARTIFACT_DOMAIN_IDENTITY_REQUIRED")
    values = list(asset_paths or [])
    if not values:
        raise LocalArtifactError("LOCAL_ASSETS_REQUIRED")
    if len(values) > _MAX_ASSETS:
        raise LocalArtifactError("TOO_MANY_LOCAL_ASSETS")
    assets = [validate_local_asset(value) for value in values]
    ffmpeg = _ffmpeg_path()
    if not ffmpeg:
        raise LocalArtifactError("FFMPEG_UNAVAILABLE")
    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    artifact_id = _new_artifact_id()
    output = root / f"{artifact_id}.mp4"
    brief = str(brief or "").strip()[:_MAX_BRIEF_LENGTH]
    try:
        with tempfile.TemporaryDirectory(prefix="video-render-", dir=str(root)) as work_dir:
            work = Path(work_dir)
            clips: List[Path] = []
            for index, asset in enumerate(assets, start=1):
                clip = work / f"clip-{index:02d}.mp4"
                command = [ffmpeg, "-y"]
                if asset.suffix.lower() in _IMAGE_EXTENSIONS:
                    command += ["-loop", "1", "-i", str(asset), "-t", "4"]
                else:
                    command += ["-i", str(asset), "-t", "6"]
                command += [
                    "-vf", _video_filter(), "-r", "30", "-an",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip),
                ]
                _run_ffmpeg(command)
                clips.append(clip)
            concat_file = work / "concat.txt"
            concat_file.write_text(
                "\n".join(f"file '{_concat_quote(clip)}'" for clip in clips) + "\n",
                encoding="utf-8",
            )
            _run_ffmpeg([
                ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(output),
            ])
        if not output.is_file() or output.stat().st_size <= 0:
            raise LocalArtifactError("FFMPEG_EMPTY_OUTPUT")
        artifact = _register_artifact(
            artifact_id=artifact_id,
            kind="video_shotcraft_render",
            product_id=product_id,
            domain_id=domain_id,
            source_execution_id=source_execution_id,
            evidence_id=str(evidence_id or "")[:128],
            note_id=str(note_id or "")[:128],
            path=output,
            media_type="video/mp4",
        )
    except Exception:
        try:
            output.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return {
        "status": "rendered_staged",
        "artifact": artifact,
        "brief": brief,
        "source_scope": "explicit_local_assets_only",
        "asset_count": len(assets),
        "source_assets": [
            {"name": asset.name, "extension": asset.suffix.lower(), "sha256": _hash_file(asset)}
            for asset in assets
        ],
        "external_media_fetch": False,
        "approval_required": True,
        "publish_status": "not_performed",
    }


def get_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    """Return sanitized artifact metadata, without an absolute path."""
    if not artifact_id or len(str(artifact_id)) > 80:
        return None
    ensure_artifact_table()
    conn = _db_connect()
    try:
        row = conn.execute(
            f"SELECT * FROM {_ARTIFACT_TABLE} WHERE artifact_id=?", (str(artifact_id),)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    item = dict(row)
    if item.get("kind") in {"content_source", "content_project", "training_checkpoint"}:
        # Scoped media must use the actor-authorized source/project readers.
        return None
    item["approval_required"] = bool(item.get("approval_required"))
    return item


def artifact_file_path(artifact_id: str) -> Optional[Path]:
    """Resolve only a root-confined file matching its registered size and hash."""
    item = get_artifact(artifact_id)
    if not item:
        return None
    root = artifact_root()
    candidate = (root / str(item["relative_path"])).resolve()
    if not _is_relative_to(candidate, root) or not candidate.is_file():
        return None
    expected_hash = item.get("sha256")
    expected_size = item.get("size_bytes")
    if (
        not isinstance(expected_hash, str) or len(expected_hash) != 64
        or any(character not in "0123456789abcdef" for character in expected_hash.lower())
        or type(expected_size) is not int or expected_size <= 0
    ):
        raise LocalArtifactError("ARTIFACT_INTEGRITY_UNVERIFIED")
    try:
        before = candidate.stat()
        if before.st_size != expected_size:
            raise LocalArtifactError("ARTIFACT_INTEGRITY_FAILED")
        actual_hash = _hash_file(candidate)
        after = candidate.stat()
    except OSError as exc:
        raise LocalArtifactError("ARTIFACT_READ_UNAVAILABLE") from exc
    if (
        actual_hash != expected_hash.lower()
        or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
    ):
        raise LocalArtifactError("ARTIFACT_INTEGRITY_FAILED")
    return candidate


def _checkpoint_json(value):
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID") from exc
    if len(raw) > 1024 * 1024:
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    return raw


def _checkpoint_regular(path, *, directory=False):
    import stat
    try:
        info = path.lstat()
    except OSError as exc:
        raise LocalArtifactError("CHECKPOINT_STORAGE_UNAVAILABLE") from exc
    if (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or (not directory and info.st_nlink != 1)):
        raise LocalArtifactError("CHECKPOINT_STORAGE_SUBSTITUTED")
    return info


def _checkpoint_relative(value):
    from pathlib import PurePosixPath
    if (type(value) is not str or not value or len(value) > 512
            or "\\" in value or ":" in value or "\0" in value):
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(x in {".", ".."} for x in path.parts):
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    # Prevent Windows alternate names and reserved-device aliasing on every host.
    for part in path.parts:
        if (part.endswith((".", " ")) or any(ord(c) < 32 for c in part)
                or part.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL",
                    *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}):
            raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    return path


def _checkpoint_files(root, files, max_bytes, *, allow_manifest=False):
    if (type(max_bytes) is not int or max_bytes <= 0 or type(files) is not list
            or not 0 < len(files) <= 4096):
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    declared, total = {}, 0
    for item in files:
        if type(item) is not dict or set(item) != {"path", "role", "size_bytes", "sha256"}:
            raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
        rel = _checkpoint_relative(item["path"])
        if (str(rel) == "checkpoint.manifest.json" or str(rel).casefold() in declared
                or type(item["size_bytes"]) is not int or item["size_bytes"] < 0
                or item["role"] not in {"adapter_or_model", "model_config", "tokenizer", "optimizer",
                    "scheduler", "rng_cpu", "rng_cuda", "trainer_state", "data_position", "scaler",
                    "callback_state", "auxiliary"}
                or type(item["sha256"]) is not str or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is None):
            raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
        declared[str(rel).casefold()] = item
        total += item["size_bytes"]
    if total > max_bytes or [x["path"] for x in files] != sorted(x["path"] for x in files):
        raise LocalArtifactError("CHECKPOINT_STORAGE_LIMIT_EXCEEDED")
    actual = []
    _checkpoint_regular(root, directory=True)
    for parent in root.parents:
        _checkpoint_regular(parent, directory=True)
    for current, dirs, names in os.walk(root, followlinks=False):
        for name in dirs:
            _checkpoint_regular(Path(current) / name, directory=True)
        for name in names:
            path = Path(current) / name
            _checkpoint_regular(path)
            rel = path.relative_to(root).as_posix()
            if rel != "checkpoint.manifest.json" or not allow_manifest:
                actual.append(rel)
    if sorted(actual) != [x["path"] for x in files]:
        raise LocalArtifactError("CHECKPOINT_INVENTORY_MISMATCH")
    for item in files:
        path = root / item["path"]
        before = _checkpoint_regular(path)
        actual_hash = _hash_file(path)
        after = _checkpoint_regular(path)
        if (actual_hash != item["sha256"] or before.st_size != item["size_bytes"]
                or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
                   (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise LocalArtifactError("CHECKPOINT_INTEGRITY_FAILED")
    return total


def _checkpoint_authorize(authorize):
    if not callable(authorize):
        raise PermissionError("CHECKPOINT_PERMISSION_REQUIRED")
    # This private storage adapter is invoked only by the bound Task/Permission
    # composition. None is a successful fresh check; booleans are not grants.
    if authorize() is not None:
        raise PermissionError("CHECKPOINT_PERMISSION_REQUIRED")


def _checkpoint_install(source, target):
    """Flush actual bytes, then install a new immutable name without replacement."""
    if target.exists():
        raise LocalArtifactError("CHECKPOINT_OPERATION_CONFLICT")
    if os.name == "nt":
        import ctypes
        move = ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW
        move.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
        move.restype = ctypes.c_int
        # MOVEFILE_WRITE_THROUGH, with no REPLACE_EXISTING or cross-volume copy.
        if not move(str(source), str(target), 0x8):
            raise LocalArtifactError("CHECKPOINT_DURABILITY_UNAVAILABLE")
    else:
        for directory in sorted([source, *[p for p in source.rglob("*") if p.is_dir()]],
                                key=lambda p: len(p.parts), reverse=True):
            fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        os.rename(source, target)
        for directory in {target.parent, source.parent}:
            fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)


def stage_training_checkpoint_artifact(*, source_root, inventory, binding, max_bytes,
                                      authorize, artifact_ref=None):
    """Install closed/excluded worker bytes; no DB write or recovery grant.

    The bound training process owner must retain effective writer exclusion
    across this call. Fresh authorizer validates that exact Task/worker/recipe.
    ``source_root`` is an owner-created directory below the canonical Artifact
    root. Artifact IDs and an unacknowledged stage are retained by the same Task
    operation; filesystem existence alone never creates a committed checkpoint.
    """
    _checkpoint_authorize(authorize)
    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    source_root = Path(source_root)
    if not source_root.is_absolute() or source_root == root:
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    try:
        source_root.relative_to(root)
    except ValueError as exc:
        raise LocalArtifactError("CHECKPOINT_STORAGE_OUTSIDE_OWNER_ROOT") from exc
    inventory = json.loads(_checkpoint_json(inventory))
    binding = json.loads(_checkpoint_json(binding))
    if (type(inventory) is not dict or type(inventory.get("schema_version")) is not int
            or inventory.get("schema_version") != 1
            or set(inventory) != {"schema_version", "operation_id", "completed_step", "checkpoint_relative_path",
                "policy_sha256", "fingerprints", "framework_versions", "trainer_config_sha256",
                "data_order_sha256", "data_position", "files"}
            or type(binding) is not dict or set(binding) != {
                "task_id", "domain_id", "task_digest", "operation_id", "attempt_id", "worker_epoch",
                "actor_identity", "scope_descriptors", "artifact_version", "parent_ref"}
            or binding["domain_id"] not in {"cth", "bmp"}
            or type(binding["artifact_version"]) is not int or binding["artifact_version"] < 1):
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    if (inventory["operation_id"] != binding["operation_id"]
            or type(inventory["completed_step"]) is not int or inventory["completed_step"] < 0
            or type(binding["worker_epoch"]) is not int or binding["worker_epoch"] < 1
            or type(binding["task_id"]) is not str or not binding["task_id"]
            or type(binding["actor_identity"]) is not dict
            or set(binding["actor_identity"]) != {"actor_id", "caller", "principal_kind", "principal_ref"}
            or type(binding["scope_descriptors"]) is not dict or not binding["scope_descriptors"]
            or (binding["parent_ref"] is not None and
                (type(binding["parent_ref"]) is not str or _CONTENT_SOURCE_ARTIFACT_ID.fullmatch(binding["parent_ref"]) is None))):
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    for value in (binding["operation_id"], binding["attempt_id"]):
        if type(value) is not str or str(uuid.UUID(value)) != value or uuid.UUID(value).version != 4:
            raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    for value in (binding["task_digest"], inventory["policy_sha256"],
                  inventory["trainer_config_sha256"], inventory["data_order_sha256"]):
        if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    _checkpoint_relative(inventory["checkpoint_relative_path"])
    artifact_ref = artifact_ref or _new_artifact_id()
    if type(artifact_ref) is not str or _CONTENT_SOURCE_ARTIFACT_ID.fullmatch(artifact_ref) is None:
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    total = _checkpoint_files(source_root, inventory.get("files"), max_bytes)
    manifest = _checkpoint_json({"schema": "lumenis.training-checkpoint-artifact/v1",
        "artifact_ref": artifact_ref, "inventory": inventory, "binding": binding,
        "max_bytes": max_bytes})
    relative = f"training_checkpoints/{artifact_ref}/checkpoint.manifest.json"
    destination = root / "training_checkpoints" / artifact_ref
    destination.parent.mkdir(exist_ok=True)
    if destination.exists():
        if (destination / "checkpoint.manifest.json").read_bytes() != manifest:
            raise LocalArtifactError("CHECKPOINT_OPERATION_CONFLICT")
        _checkpoint_files(destination, inventory["files"], max_bytes, allow_manifest=True)
    else:
        stage = Path(tempfile.mkdtemp(prefix=".checkpoint-stage-", dir=root))
        # Failed stages are diagnostic orphans. They are never registered or
        # recursively removed by a generic cleanup/recovery path.
        for item in inventory["files"]:
            target = stage / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            with (source_root / item["path"]).open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
                dst.flush()
                os.fsync(dst.fileno())
        _checkpoint_files(stage, inventory["files"], max_bytes)
        with (stage / "checkpoint.manifest.json").open("xb") as dst:
            dst.write(manifest)
            dst.flush()
            os.fsync(dst.fileno())
        _checkpoint_authorize(authorize)
        _checkpoint_install(stage, destination)
    _checkpoint_authorize(authorize)
    return {"artifact_ref": artifact_ref, "sha256": hashlib.sha256(manifest).hexdigest(),
        "size_bytes": len(manifest) + total, "relative_path": relative,
        "storage_identity": "artifact:" + artifact_ref, "binding": binding}


def _checkpoint_reopen_record(staged):
    if type(staged) is not dict or set(staged) != {
            "artifact_ref", "sha256", "size_bytes", "relative_path", "storage_identity", "binding"}:
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    ref = staged["artifact_ref"]
    if type(ref) is not str or _CONTENT_SOURCE_ARTIFACT_ID.fullmatch(ref) is None:
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    expected_path = f"training_checkpoints/{ref}/checkpoint.manifest.json"
    if staged["relative_path"] != expected_path or staged["storage_identity"] != "artifact:" + ref:
        raise LocalArtifactError("CHECKPOINT_STORAGE_SUBSTITUTED")
    path = artifact_root() / expected_path
    for parent in path.parents:
        _checkpoint_regular(parent, directory=True)
    _checkpoint_regular(path)
    if path.stat().st_size > 1024 * 1024:
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    raw = path.read_bytes()
    try:
        manifest = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise LocalArtifactError("CHECKPOINT_INTEGRITY_FAILED") from exc
    if (_checkpoint_json(manifest) != raw or type(manifest) is not dict or set(manifest) != {
            "schema", "artifact_ref", "inventory", "binding", "max_bytes"}
            or manifest["schema"] != "lumenis.training-checkpoint-artifact/v1"
            or manifest["artifact_ref"] != ref or manifest["binding"] != staged["binding"]
            or hashlib.sha256(raw).hexdigest() != staged["sha256"]):
        raise LocalArtifactError("CHECKPOINT_INTEGRITY_FAILED")
    total = _checkpoint_files(path.parent, manifest["inventory"]["files"], manifest["max_bytes"], allow_manifest=True)
    if len(raw) + total != staged["size_bytes"]:
        raise LocalArtifactError("CHECKPOINT_INTEGRITY_FAILED")
    return manifest, path.parent


def register_training_checkpoint_artifact(*, connection, staged, authorize):
    """Register with the caller's Task transaction; never open/commit/create DB."""
    from ai_task_engine import TaskEngine
    TaskEngine._require_training_receipt_connection(connection)
    _checkpoint_authorize(authorize)
    _checkpoint_reopen_record(staged)
    binding = staged["binding"]
    if binding["parent_ref"] is not None:
        parent = connection.execute(f"SELECT * FROM {_ARTIFACT_TABLE} WHERE artifact_id=?",
                                    (binding["parent_ref"],)).fetchone()
        if (not parent or parent["kind"] != "training_checkpoint" or parent["status"] != "committed"
                or parent["source_execution_id"] != binding["task_id"]):
            raise LocalArtifactError("CHECKPOINT_PARENT_MISMATCH")
        parent_raw = read_training_checkpoint_artifact(connection=connection,
            artifact_ref=binding["parent_ref"], expected_sha256=parent["sha256"], authorize=authorize)
        parent_binding = parent_raw["manifest"]["binding"]
        if (parent_binding["artifact_version"] + 1 != binding["artifact_version"]
                or any(parent_binding[k] != binding[k] for k in
                       ("actor_identity", "scope_descriptors", "domain_id", "task_digest"))):
            raise LocalArtifactError("CHECKPOINT_PARENT_MISMATCH")
    elif binding["artifact_version"] != 1:
        raise LocalArtifactError("CHECKPOINT_PARENT_MISMATCH")
    record = {"artifact_id": staged["artifact_ref"], "kind": "training_checkpoint",
        "product_id": "CTH" if binding["domain_id"] == "cth" else "ZBMP",
        "domain_id": "cth" if binding["domain_id"] == "cth" else "zbmp",
        "source_execution_id": binding["task_id"], "evidence_id": None, "note_id": None,
        "filename": "checkpoint.manifest.json", "media_type": "application/vnd.lumenis.training-checkpoint+json",
        "relative_path": staged["relative_path"], "size_bytes": staged["size_bytes"],
        "sha256": staged["sha256"], "status": "committed", "approval_required": True,
        "approval_status": "approved"}
    existing = connection.execute(f"SELECT * FROM {_ARTIFACT_TABLE} WHERE artifact_id=?",
                                  (staged["artifact_ref"],)).fetchone()
    if existing:
        if any(dict(existing)[k] != v for k, v in record.items()):
            raise LocalArtifactError("CHECKPOINT_OPERATION_CONFLICT")
        _checkpoint_authorize(authorize)
        return {**dict(existing), "artifact_ref": staged["artifact_ref"], "storage_identity": staged["storage_identity"]}
    now = datetime.utcnow().isoformat(timespec="microseconds") + "Z"
    record.update(created_at=now, updated_at=now)
    keys = list(record)
    connection.execute(f"INSERT INTO {_ARTIFACT_TABLE} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",
                       tuple(record[k] for k in keys))
    _checkpoint_authorize(authorize)
    return {**record, "artifact_ref": staged["artifact_ref"], "storage_identity": staged["storage_identity"]}


def read_training_checkpoint_artifact(*, connection, artifact_ref, expected_sha256, authorize):
    """Verify a registered immutable checkpoint; returned Path stays private."""
    _checkpoint_authorize(authorize)
    if type(connection) is not sqlite3.Connection:
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    dbs = connection.execute("PRAGMA database_list").fetchall()
    selected = next((r[2] for r in dbs if r[1] == "main"), None)
    if not selected or Path(selected).resolve() != Path(main_db_path()).resolve():
        raise LocalArtifactError("CHECKPOINT_STORAGE_OUTSIDE_OWNER_ROOT")
    row = connection.execute(f"SELECT * FROM {_ARTIFACT_TABLE} WHERE artifact_id=?", (artifact_ref,)).fetchone()
    if not row or row["kind"] != "training_checkpoint" or row["status"] != "committed":
        raise LocalArtifactError("CHECKPOINT_NOT_COMMITTED")
    item = dict(row)
    if item["sha256"] != expected_sha256:
        raise LocalArtifactError("CHECKPOINT_INTEGRITY_FAILED")
    path = artifact_root() / f"training_checkpoints/{artifact_ref}/checkpoint.manifest.json"
    for parent in path.parents:
        _checkpoint_regular(parent, directory=True)
    _checkpoint_regular(path)
    if path.stat().st_size > 1024 * 1024:
        raise LocalArtifactError("CHECKPOINT_REQUEST_INVALID")
    manifest = json.loads(path.read_bytes())
    staged = {"artifact_ref": artifact_ref, "sha256": expected_sha256,
        "size_bytes": item["size_bytes"], "relative_path": item["relative_path"],
        "storage_identity": "artifact:" + artifact_ref, "binding": manifest["binding"]}
    verified, load_root = _checkpoint_reopen_record(staged)
    _checkpoint_authorize(authorize)
    return {"record": item, "manifest": verified, "load_root": load_root,
            "artifact_ref": artifact_ref, "sha256": expected_sha256,
            "storage_identity": staged["storage_identity"]}


__all__ = [
    "LocalArtifactError",
    "artifact_root",
    "artifact_file_path",
    "authorized_project_media",
    "ensure_artifact_table",
    "get_artifact",
    "list_content_projects",
    "read_content_source_artifact",
    "read_content_project",
    "resolve_content_source_assets",
    "render_local_video_artifact",
    "stage_content_source_artifact",
    "stage_timeline_artifact",
    "validate_local_asset",
]


def _validate_content_delivery_options(value=None):
    """Bound optional offline deliverables to the same project authorization."""
    if value is None:
        return {}
    if not isinstance(value, dict) or set(value) - {"audio_formats", "podcast_plan", "publication_urls", "interchange", "cover", "include_ass_subtitles", "audio_visual", "include_source_probe", "reference_analysis", "transcription", "podcast_cover", "podcast_analysis"}:
        raise LocalArtifactError("CONTENT_DELIVERY_OPTIONS_INVALID")
    if len(_json_bytes(value)) > _MAX_PROJECT_JSON_BYTES:
        raise LocalArtifactError("CONTENT_DELIVERY_OPTIONS_TOO_LARGE")
    value = json.loads(_json_bytes(value))
    if "include_ass_subtitles" in value and type(value["include_ass_subtitles"]) is not bool:
        raise LocalArtifactError("CONTENT_SUBTITLE_OPTIONS_INVALID")
    if "include_source_probe" in value and type(value["include_source_probe"]) is not bool:
        raise LocalArtifactError("SOURCE_PROBE_OPTIONS_INVALID")
    formats = value.get("audio_formats", [])
    if not isinstance(formats, list) or len(formats) > 2 or any(not isinstance(x,str) or x not in {"mp3", "m4a"} for x in formats) or len(formats) != len(set(formats)):
        raise LocalArtifactError("CONTENT_DELIVERY_FORMAT_INVALID")
    if "podcast_plan" in value:
        from podcast.intelligence.episode_runtime import PodcastPlan
        PodcastPlan.from_dict(value["podcast_plan"])
        if not formats:
            raise LocalArtifactError("PODCAST_DELIVERY_REQUIRES_AUDIO_FORMAT")
    elif "publication_urls" in value:
        raise LocalArtifactError("PODCAST_DELIVERY_PLAN_REQUIRED")
    exchange = value.get("interchange")
    if "interchange" in value and (not isinstance(exchange, dict) or set(exchange) - {"formats", "frame_rate", "allow_loss"}):
        raise LocalArtifactError("CONTENT_INTERCHANGE_OPTIONS_INVALID")
    cover = value.get("cover")
    if "cover" in value and (not isinstance(cover, dict) or set(cover) - {"audience", "industry", "visual_hook", "body_text", "count"}):
        raise LocalArtifactError("CONTENT_COVER_OPTIONS_INVALID")
    analysis=value.get("podcast_analysis")
    if "podcast_analysis" in value and (not isinstance(analysis,dict) or "timeline_version" not in analysis or set(analysis)-{"timeline_version","nodes"}):
        raise LocalArtifactError("PODCAST_ANALYSIS_OPTIONS_INVALID")
    podcast_cover=value.get("podcast_cover")
    if "podcast_cover" in value and (not isinstance(podcast_cover,dict) or not {"title","subtitle"}<=set(podcast_cover) or set(podcast_cover)-{"title","subtitle","footer"}):
        raise LocalArtifactError("PODCAST_COVER_OPTIONS_INVALID")
    from lumenis.system.ai_gateway.owned_speech import CONTENT_LANGUAGE_CODES
    transcription=value.get("transcription")
    if "transcription" in value and (not isinstance(transcription,dict) or "asset_id" not in transcription
            or set(transcription)-{"asset_id","audio_stream_index","language_hint"} or not isinstance(transcription["asset_id"],str)
            or not re.fullmatch(r"MEDIA-[a-fA-F0-9]+",transcription["asset_id"])):
        raise LocalArtifactError("CONTENT_TRANSCRIPTION_OPTIONS_INVALID")
    if isinstance(transcription,dict) and transcription.get("language_hint") is not None and (not isinstance(transcription["language_hint"],str) or transcription["language_hint"] not in CONTENT_LANGUAGE_CODES):
        raise LocalArtifactError("CONTENT_ASR_LANGUAGE_INVALID")
    reference=value.get("reference_analysis")
    if "reference_analysis" in value and (not isinstance(reference,dict) or set(reference)!={"asset_id"}
            or not isinstance(reference["asset_id"],str) or not re.fullmatch(r"MEDIA-[a-fA-F0-9]+",reference["asset_id"])):
        raise LocalArtifactError("REFERENCE_ANALYSIS_OPTIONS_INVALID")
    visual=value.get("audio_visual")
    if "audio_visual" in value and (not isinstance(visual,dict) or set(visual)-{"start_sec","end_sec","quote","title","format_ratio"}
            or not {"start_sec","end_sec","quote","title"} <= set(visual)):
        raise LocalArtifactError("CONTENT_AUDIO_VISUAL_OPTIONS_INVALID")
    return value


def _content_delivery_filename(name):
    fixed = {"credits.json", "credits.txt", "episode.mp3", "episode.m4a", "podcast-plan.json", "script.txt", "transcript-original.vtt",
             "transcript-corrected.vtt", "chapters.json", "corrections.json", "metadata.json", "show-notes.txt", "feed.xml",
             "timeline.otio", "timeline.fcpxml", "timeline.edl", "interchange.json", "cover.json", "captions.ass", "subtitles.json", "audio-visual.png", "quote-card.png", "audio-visual.mp4", "audio-visual.json", "source-probe.json", "analysis.json", "frame-metrics.csv", "shot-candidates.csv", "transcription.json", "transcript-asr.vtt", "transcript-asr.srt", "transcript-words.json", "transcript-timeline.json", "transcript-timeline.srt", "transcript-timeline.vtt", "podcast-cover.png", "podcast-cover.json", "podcast-analysis.json"}
    return isinstance(name, str) and (name in fixed or re.fullmatch(r"contact-sheet-(?:0[1-9]|10)\.png", name) is not None or re.fullmatch(r"cover-0[1-9]\.png", name) is not None
        or re.fullmatch(r"source-MEDIA-[a-fA-F0-9]+\.(?:mp4|mov|webm|mkv|avi|wav|mp3|m4a|flac|ogg|aac|aiff)", name) is not None)


def _build_content_delivery(timeline, rendered_path, *, output_kind, options, render_options, check_continue):
    from lumenis.shared.content_creation.rendering import encode_audio_delivery
    files, reports = {}, {}
    if "transcription" in options:
        from lumenis.shared.content_creation.speech_transcription import build_transcription_files, build_timeline_transcription_files
        selected=next((asset for asset in timeline.assets if asset.asset_id==options["transcription"]["asset_id"]),None)
        if selected is None:raise LocalArtifactError("CONTENT_TRANSCRIPTION_SOURCE_SCOPE_MISMATCH")
        item=build_transcription_files(selected,check_cancel=check_continue,**{key:value for key,value in options["transcription"].items() if key!="asset_id"})
        if item["report"].get("review_state")=="NO_RECOGNIZED_SPEECH":raise LocalArtifactError("CONTENT_ASR_NO_RECOGNIZED_SPEECH")
        files.update(item["files"]);reports["transcription"]=item["report"]
        edited=build_timeline_transcription_files(timeline,item,rendered_sha256=hashlib.sha256(Path(rendered_path).read_bytes()).hexdigest(),check_cancel=check_continue)
        files.update(edited["files"]);reports["timeline_transcription"]=edited["report"]
    if "podcast_analysis" in options:
        from podcast.intelligence.episode_analysis import build_episode_analysis_files
        from lumenis.shared.content_creation.video_editing import fingerprint_local_media
        item=build_episode_analysis_files(fingerprint_local_media(str(rendered_path)),expected_timeline_version=timeline.version,check_cancel=check_continue,**options["podcast_analysis"])
        files.update(item["files"]);reports["podcast_analysis"]=item["report"]
    if "podcast_cover" in options:
        from lumenis.shared.content_creation.podcast_cover import build_podcast_cover_files
        from lumenis.shared.content_creation.video_editing import fingerprint_local_media
        item=build_podcast_cover_files(fingerprint_local_media(str(rendered_path)),check_cancel=check_continue,**options["podcast_cover"])
        files.update(item["files"]);reports["podcast_cover"]=item["report"]
    if "reference_analysis" in options:
        from lumenis.shared.content_creation.reference_analysis import build_reference_analysis_files
        selected=next((asset for asset in timeline.assets if asset.asset_id==options["reference_analysis"]["asset_id"]),None)
        if selected is None:raise LocalArtifactError("REFERENCE_ANALYSIS_SOURCE_SCOPE_MISMATCH")
        item=build_reference_analysis_files(selected,check_cancel=check_continue)
        files.update(item["files"])
        reports["reference_analysis"]=item["report"]
    if options.get("include_source_probe"):
        from lumenis.shared.content_creation.stream_probe import probe_source_streams
        source_probe=[probe_source_streams(asset,analyze_timing=True,check_cancel=check_continue) for asset in timeline.assets]
        files["source-probe.json"]=_json_bytes({"sources":source_probe})
        reports["source_probe"]={"sources":source_probe}
    if options.get("include_ass_subtitles"):
        from lumenis.shared.content_creation.subtitle_export import build_ass_files
        item = build_ass_files(timeline)
        files.update(item["files"]); reports["subtitles"] = item["report"]
    formats = options.get("audio_formats", [])
    if formats and output_kind != "audio":
        raise LocalArtifactError("PODCAST_DELIVERY_REQUIRES_AUDIO_PROJECT")
    for format in formats:
        item = encode_audio_delivery(rendered_path, format=format, duration=timeline.duration_sec,
                                     target_lufs=render_options.get("loudness_target_lufs"), check_continue=check_continue)
        files.update(item["files"]); reports[format] = item["report"]
    if "podcast_plan" in options:
        from podcast.intelligence.episode_runtime import PodcastPlan, build_offline_publication_documents
        plan = PodcastPlan.from_dict(options["podcast_plan"])
        voice_tracks = {t.track_id for t in timeline.tracks if t.kind == "voiceover" and t.clips}
        separate = voice_tracks != {"podcast_voice"}
        expected = plan.build_timeline(tuple(timeline.assets), separate_speakers=separate)
        def spans(value):
            return sorted((t.track_id, c.purpose, c.media_asset_id, c.source_in, c.source_out,
                           c.timeline_start, c.audio_stream_index)
                          for t in value.tracks if t.kind == "voiceover" for c in t.clips)
        if (spans(expected) != spans(timeline)
                or any(t.clips and t.kind not in {"voiceover", "bgm", "sfx"} for t in timeline.tracks)):
            raise LocalArtifactError("PODCAST_PLAN_TIMELINE_MISMATCH")
        name = "episode." + formats[0]
        item = build_offline_publication_documents(plan,audio_filename=name,audio_size=len(files[name]),
                                                   urls=options.get("publication_urls"))
        files.update(item["files"]); reports["publication"] = item["report"]
    if "interchange" in options:
        from lumenis.shared.content_creation.timeline_interchange import build_interchange_files
        refs = {}
        for asset in timeline.assets:
            check_continue()
            path = validate_local_asset(asset.path)
            if _hash_file(path) != asset.sha256:
                raise LocalArtifactError("CONTENT_SOURCE_INTEGRITY_FAILED")
            name = "source-" + asset.asset_id + path.suffix.lower()
            if sum(map(len,files.values())) + path.stat().st_size > 128 * 1024 * 1024:
                raise LocalArtifactError("CONTENT_DELIVERY_TOO_LARGE")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != asset.sha256:
                raise LocalArtifactError("CONTENT_SOURCE_INTEGRITY_FAILED")
            files[name] = data; refs[asset.asset_id] = name
        item = build_interchange_files(timeline,media_refs=refs,check_cancel=check_continue,**options["interchange"])
        files.update(item["files"]); reports["interchange"] = item["report"]
    if "audio_visual" in options:
        from lumenis.shared.content_creation.audio_visuals import build_audio_visual_files
        from lumenis.shared.content_creation.video_editing import fingerprint_local_media
        asset=fingerprint_local_media(str(rendered_path))
        item=build_audio_visual_files(asset,check_cancel=check_continue,**options["audio_visual"])
        item["report"]["source_kind"]="rendered_output"
        item["files"]["audio-visual.json"]=_json_bytes(item["report"])
        files.update(item["files"]);reports["audio_visual"]=item["report"]
    if "cover" in options:
        from lumenis.shared.content_creation.cover_candidates import build_cover_files
        if output_kind != "video":
            raise LocalArtifactError("CONTENT_COVER_REQUIRES_RENDERED_VIDEO")
        from lumenis.shared.content_creation.video_editing import fingerprint_local_media
        asset = fingerprint_local_media(str(rendered_path))
        item = build_cover_files(asset,check_cancel=check_continue,**options["cover"])
        item["report"]["source_kind"] = "rendered_output"
        item["files"]["cover.json"] = _json_bytes(item["report"])
        files.update(item["files"]); reports["cover"] = item["report"]
    if len(files) > 80 or sum(map(len, files.values())) > 128 * 1024 * 1024:
        raise LocalArtifactError("CONTENT_DELIVERY_TOO_LARGE")
    if any(not _content_delivery_filename(name) or not isinstance(data, bytes) or not data for name,data in files.items()):
        raise LocalArtifactError("CONTENT_DELIVERY_FILE_INVALID")
    check_continue()
    return files, reports


_CONTENT_EDL_LOCK = threading.RLock()


def _parse_content_edl(value):
    from lumenis.shared.content_creation.video_editing import EditDecision, EditDecisionList
    if not isinstance(value, dict) or set(value) != {"candidate_id", "decisions"} or not isinstance(value["decisions"], list) or not 1 <= len(value["decisions"]) <= 128:
        raise LocalArtifactError("CONTENT_EDL_INPUT_INVALID")
    _json_bytes(value)  # Same bounded, finite JSON contract as saved project metadata.
    try:
        decisions = []
        for raw in value["decisions"]:
            if not isinstance(raw, dict):raise ValueError("decision")
            item=dict(raw)
            for key in ("affected_audio", "affected_text"):
                if key in item:
                    if not isinstance(item[key], list):raise ValueError("list")
                    item[key]=tuple(item[key])
            decisions.append(EditDecision(**item))
        return EditDecisionList(value["candidate_id"], (), tuple(decisions))
    except (ValueError, TypeError, KeyError) as exc:
        raise LocalArtifactError("CONTENT_EDL_INPUT_INVALID") from exc


def _content_edl_artifact_id(operation_id):
    return "ART-" + hashlib.sha256(operation_id.encode()).hexdigest()[:16]


def _content_edl_binding(project_id, edl, *, actor, scope, request_id):
    if not isinstance(request_id,str) or re.fullmatch(r"[A-Za-z0-9_-]{8,128}",request_id) is None:
        raise LocalArtifactError("CONTENT_EDL_REQUEST_ID_INVALID")
    actor_id,current_scope=_authorize_content_project(actor,action="write",**scope)
    context=_content_artifact_context(actor,actor_id,current_scope)
    project,render,record,path=_verified_content_project(project_id,actor=actor,**scope)
    if not project.get("source_artifact_refs"):
        raise LocalArtifactError("CONTENT_EDL_SAVED_SOURCES_REQUIRED")
    from lumenis.shared.content_creation.video_editing import Timeline, _apply_edl_operations
    with resolve_content_source_assets(project["source_artifact_refs"],actor=actor,**scope) as sources:
        original=Timeline.from_dict(project["timeline"],assets=[item["asset"] for item in sources])
        preview=_apply_edl_operations(original,edl).to_dict()
    binding={"operation_type":"content_edl_derived_export_v1","context":context,
             "parent_artifact_id":project_id,"parent_sha256":record["sha256"],
             "timeline":project["timeline"],"edl":edl.to_dict(),"preview":preview,
             "render_options":project.get("render_options",{}),"request_id":request_id}
    resource="content-project-export:v1:"+hashlib.sha256(_json_bytes(binding)).hexdigest()
    operation_id="content-edl:"+hashlib.sha256(_json_bytes({"context":context,"request_id":request_id})).hexdigest()
    return project,record,context,resource,operation_id


def _check_content_edl_effect(actor,scope,context,resource):
    from lumenis.system.security.permission import OperationType,get_permission_gate,check_shared_workspace_effect,is_testing_bypass_enabled
    if is_testing_bypass_enabled():raise LocalArtifactError("CONTENT_EDL_APPROVAL_UNVERIFIED")
    _authorize_content_project(actor,action="write",**scope)
    gate=get_permission_gate()
    if "shared_workspace_scope" in scope:
        result=check_shared_workspace_effect(actor,scope["shared_workspace_scope"],OperationType.DATA_EXPORT,resource,module="content",action="write",gate=gate)
    else:
        result=gate.check(OperationType.DATA_EXPORT,resource=resource,caller=context["principal_ref"] if context.get("actor_id") is None else f"actor:{context['actor_id']}",domain_id="bmp" if context["domain_id"]=="zbmp" else "cth")
    if not result.allowed:raise LocalArtifactError("CONTENT_EDL_EFFECT_DENIED")
    return gate


def prepare_content_edl_application(project_id, edl_input, *, actor, scope, request_id):
    from lumenis.shared.content_creation.video_editing import Timeline,_apply_edl_operations
    edl=_parse_content_edl(edl_input)
    project,record,context,resource,operation_id=_content_edl_binding(project_id,edl,actor=actor,scope=scope,request_id=request_id)
    _check_content_edl_effect(actor,scope,context,resource)
    with resolve_content_source_assets(project["source_artifact_refs"],actor=actor,**scope) as sources:
        timeline=Timeline.from_dict(project["timeline"],assets=[item["asset"] for item in sources])
        preview=_apply_edl_operations(timeline,edl)
    return {"state":"confirmation_required","parent_artifact_id":project_id,"parent_sha256":record["sha256"],
            "resource":resource,"operation_id":operation_id,"request_id":request_id,"preview_timeline":preview.to_dict(),
            "requires_confirmation":True,"delivery_policy":"rendered_media_and_subtitles_only; rebuild_optional_delivery_package_explicitly",
            "publish_status":"not_performed"}


def _authorize_content_edl_application(timeline,edl,*,actor,scope,project_id,request_id,expected_resource):
    from lumenis.system.security.permission import OperationType
    project,record,context,resource,operation_id=_content_edl_binding(project_id,edl,actor=actor,scope=scope,request_id=request_id)
    if timeline.to_dict()!=project["timeline"] or expected_resource!=resource:
        raise LocalArtifactError("CONTENT_EDL_BASE_CHANGED")
    gate=_check_content_edl_effect(actor,scope,context,resource)
    token=gate.get_valid_approval_token(OperationType.DATA_EXPORT.value,resource,exact=True)
    if not token:raise LocalArtifactError("CONTENT_EDL_EXACT_APPROVAL_REQUIRED")
    return gate,token


@contextmanager
def _content_edl_process_lock(artifact_id):
    """Serialize the deterministic ID across workers; never leave a live writer's ZIP behind."""
    root=artifact_root()/".content-edl-locks"
    root.mkdir(parents=True,exist_ok=True)
    with (root/(artifact_id+".lock")).open("a+b") as handle:
        if os.name == "posix":
            import fcntl
            try:fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as exc:raise LocalArtifactError("CONTENT_EDL_OPERATION_IN_PROGRESS") from exc
            try:yield
            finally:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
        elif os.name == "nt":
            import msvcrt
            handle.seek(0);handle.write(b"0");handle.flush();handle.seek(0)
            try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            except OSError as exc:raise LocalArtifactError("CONTENT_EDL_OPERATION_IN_PROGRESS") from exc
            try:yield
            finally:
                handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
        else:
            raise LocalArtifactError("CONTENT_EDL_PROCESS_LOCK_UNAVAILABLE")


def apply_content_edl_application(project_id,edl_input,*,actor,scope,request_id,expected_resource,confirmed=False):
    from lumenis.system.security.permission import OperationType
    from lumenis.shared.content_creation.video_editing import Timeline,apply_edl_suggestion
    if confirmed is not True:raise LocalArtifactError("CONTENT_EDL_CONFIRMATION_REQUIRED")
    edl=_parse_content_edl(edl_input)
    with _CONTENT_EDL_LOCK:
        project,record,context,resource,operation_id=_content_edl_binding(project_id,edl,actor=actor,scope=scope,request_id=request_id)
        if resource!=expected_resource:raise LocalArtifactError("CONTENT_EDL_BASE_CHANGED")
        gate=_check_content_edl_effect(actor,scope,context,resource)
        artifact_id=_content_edl_artifact_id(operation_id)
        with _content_edl_process_lock(artifact_id):
            existing=_artifact_record(artifact_id,read_only=True)
            if existing:
                cached=read_content_project(artifact_id,actor=actor,**scope)
                if cached["project"].get("operation_binding")!={"operation_id":operation_id,"resource":resource}:
                    raise LocalArtifactError("CONTENT_EDL_REQUEST_ID_CONFLICT")
                pending=gate.get_valid_approval_token(OperationType.DATA_EXPORT.value,resource,exact=True)
                if pending:gate.revoke_approval(pending)
                return {"state":"already_applied","artifact_id":artifact_id,"result":cached,"idempotent_replay":True}
            # A dead process may have written a partial/complete ZIP before DB commit.
            # Under the per-ID OS lock, retain those bytes verbatim as an orphan;
            # they are never accepted as a valid Artifact or silently deleted.
            orphan=artifact_root()/(artifact_id+".zip")
            recovered_orphan=None
            if orphan.exists() or orphan.is_symlink():
                if orphan.is_symlink() or not orphan.is_file():
                    raise LocalArtifactError("CONTENT_EDL_ORPHAN_REQUIRES_REVIEW")
                retained=artifact_root()/(artifact_id+".orphan-"+uuid.uuid4().hex+".zip")
                # link() is exclusive even on POSIX: never overwrite any retained
                # bytes. A crash before unlink merely leaves two safe names.
                os.link(orphan,retained,follow_symlinks=False)
                orphan.unlink()
                recovered_orphan=retained.name
            # The canonical service computes identity; no caller/reviewer string is accepted.
            caller=context["principal_ref"] if context.get("actor_id") is None else f"actor:{context['actor_id']}"
            token=gate.grant_approval(OperationType.DATA_EXPORT.value,resource=resource,duration_minutes=5,granted_by=caller)
            try:
                with resolve_content_source_assets(project["source_artifact_refs"],actor=actor,**scope) as sources:
                    timeline=Timeline.from_dict(project["timeline"],assets=[item["asset"] for item in sources])
                    changed=apply_edl_suggestion(timeline,edl,actor=actor,scope=scope,project_id=project_id,request_id=request_id,expected_resource=resource)
                    _authorize_content_edl_application(timeline,edl,actor=actor,scope=scope,project_id=project_id,request_id=request_id,expected_resource=resource)
                    result=stage_timeline_artifact(changed,actor=actor,**scope,source_execution_id=operation_id,
                        output_kind=project["output_kind"],previous_artifact_id=project_id,source_artifact_refs=project["source_artifact_refs"],
                        render_options=project.get("render_options"),
                        operation_binding={"operation_id":operation_id,"resource":resource})
            except Exception:
                gate.revoke_approval(token)
                raise
            # Committed deterministic ID is read back before consuming approval. A
            # crash here reopens that same version on retry, never creates another.
            read_content_project(artifact_id,actor=actor,**scope)
            gate.revoke_approval(token)
            return {"state":"applied","artifact_id":artifact_id,"result":result,"idempotent_replay":False,
                    "recovery":{"retained_orphan":recovered_orphan,"unknown_bytes_preserved":bool(recovered_orphan)}}
