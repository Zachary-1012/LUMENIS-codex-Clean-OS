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
import shutil
import sqlite3
import subprocess
import tempfile
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional

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
_CONTENT_SOURCE_ARTIFACT_ID = re.compile(r"ART-[0-9a-f]{16}\Z")
_ARTIFACT_TABLE = "lumenis_shared_artifacts"


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
    domain_id: str,
    subject_id: Optional[str],
    brand_focus_id: Optional[str],
    global_scope: bool,
) -> tuple[Optional[int], Dict[str, Any]]:
    actor_id = actor.get("id") if isinstance(actor, Mapping) else None
    if type(actor) is not LocalWorkspacePrincipal and (
        type(actor_id) is not int or actor_id <= 0
    ):
        raise LocalArtifactError("ACTOR_SCOPE_PERMISSION_DENIED")
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
    domain_id: str,
    subject_id: Optional[str],
    brand_focus_id: Optional[str],
    global_scope: bool,
    action: str,
) -> tuple[Optional[int], Dict[str, Any]]:
    actor_id, scope = _content_project_scope(
        actor=actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
    )
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


def _artifact_record(artifact_id: str) -> Optional[Dict[str, Any]]:
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
    domain_id: str,
    subject_id: Optional[str],
    brand_focus_id: Optional[str],
    global_scope: bool,
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Path]:
    actor_id, scope = _authorize_content_project(
        actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        action="read",
    )
    record = _artifact_record(artifact_id)
    if not record or record.get("kind") != "content_project":
        raise LocalArtifactError("CONTENT_PROJECT_NOT_FOUND")

    expected_product = "CTH" if scope["domain_id"] == "cth" else "ZBMP"
    if record.get("domain_id") != scope["domain_id"] or record.get("product_id") != expected_product:
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
            if len(names) != 3 or len(set(names)) != 3:
                raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID")
            project_infos = [info for info in infos if info.filename == "project.json"]
            render_infos = [info for info in infos if info.filename == "render.json"]
            media_infos = [info for info in infos if info.filename in {"media.mp4", "media.wav"}]
            if len(project_infos) != 1 or len(render_infos) != 1 or len(media_infos) != 1:
                raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID")
            for info in infos:
                limit = (
                    _MAX_CONTENT_PROJECT_MEDIA_BYTES
                    if info.filename in {"media.mp4", "media.wav"}
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
    except LocalArtifactError:
        raise
    except (OSError, zipfile.BadZipFile, RuntimeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocalArtifactError("CONTENT_PROJECT_ARCHIVE_INVALID") from exc

    source_artifact_refs = project_data.get("source_artifact_refs", []) if isinstance(project_data, dict) else None
    if (
        not isinstance(project_data, dict)
        or type(project_data.get("schema_version")) is not int
        or project_data.get("schema_version") != 1
        or project_data.get("context") != expected_context
        or project_data.get("output_kind") not in {"video", "audio"}
        or project_data.get("rights") != {
            "state": "unknown",
            "demo_acknowledged": True,
            "label": "demo-only / rights unknown",
        }
        or not isinstance(project_data.get("timeline"), dict)
        or _contains_local_path_field(project_data.get("timeline"))
        or not isinstance(source_artifact_refs, list)
        or len(source_artifact_refs) > 64
        or any(not isinstance(ref, str) or not _CONTENT_SOURCE_ARTIFACT_ID.fullmatch(ref)
               for ref in source_artifact_refs)
        or len(set(source_artifact_refs)) != len(source_artifact_refs)
        or not isinstance(render_data, dict)
        or render_data.get("output_kind") != project_data.get("output_kind")
        or render_data.get("state") != "rendered_verified"
        or not isinstance(render_data.get("measurement"), dict)
        or _contains_local_path_field(render_data)
    ):
        raise LocalArtifactError("CONTENT_PROJECT_CONTEXT_MISMATCH")
    project_data["source_artifact_refs"] = list(source_artifact_refs)
    expected_media = "media.mp4" if project_data["output_kind"] == "video" else "media.wav"
    claimed_media_hash = render_data.get("media_sha256")
    claimed_media_size = render_data.get("size_bytes")
    if (
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
    return project_data, render_data, {**record, "media_member": expected_media}, candidate


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


def _verified_content_source(
    artifact_id: str,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str,
    subject_id: Optional[str],
    brand_focus_id: Optional[str],
    global_scope: bool,
    action: str = "read",
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Path]:
    actor_id, scope = _authorize_content_project(
        actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        action=action,
    )
    if not isinstance(artifact_id, str) or not _CONTENT_SOURCE_ARTIFACT_ID.fullmatch(artifact_id):
        raise LocalArtifactError("CONTENT_SOURCE_NOT_FOUND")
    record = _artifact_record(artifact_id)
    if not record or record.get("kind") != "content_source":
        raise LocalArtifactError("CONTENT_SOURCE_NOT_FOUND")
    expected_product = "CTH" if scope["domain_id"] == "cth" else "ZBMP"
    if record.get("domain_id") != scope["domain_id"] or record.get("product_id") != expected_product:
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

    if (
        not isinstance(metadata, dict)
        or set(metadata) != {"schema_version", "context", "asset", "media_filename", "rights_state"}
        or type(metadata.get("schema_version")) is not int
        or metadata.get("schema_version") != 1
        or metadata.get("context") != expected_context
        or metadata.get("media_filename") != media_filename
        or metadata.get("rights_state") != "unknown"
        or not _source_asset_metadata_is_valid(metadata.get("asset"), media_filename)
        or media_info.file_size <= 0
    ):
        raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    if record.get("media_type") != "application/zip":
        raise LocalArtifactError("CONTENT_SOURCE_CONTEXT_MISMATCH")
    _authorize_content_project(actor, action=action, **scope)
    return metadata, {**record, "media_member": media_filename, "media_size_bytes": media_info.file_size}, expected_context, candidate


def _validate_content_source_refs(
    artifact_refs: Any,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str,
    subject_id: Optional[str],
    brand_focus_id: Optional[str],
    global_scope: bool,
) -> tuple[List[str], List[Dict[str, Any]], int]:
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
        metadata, record, _, package_path = _verified_content_source(
            artifact_id,
            actor=actor,
            domain_id=domain_id,
            subject_id=subject_id,
            brand_focus_id=brand_focus_id,
            global_scope=global_scope,
        )
        asset_id = metadata["asset"]["asset_id"]
        if asset_id in asset_ids:
            raise LocalArtifactError("CONTENT_SOURCE_ASSET_DUPLICATE")
        asset_ids.add(asset_id)
        total_size += int(record["media_size_bytes"])
        if total_size > _MAX_CONTENT_SOURCE_TOTAL_BYTES:
            raise LocalArtifactError("CONTENT_SOURCE_TOTAL_TOO_LARGE")
        entries.append({"metadata": metadata, "record": record, "package_path": package_path})
    return list(artifact_refs), entries, total_size


def stage_content_source_artifact(
    asset_path: Any,
    *,
    filename: str,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str,
    subject_id: Optional[str] = None,
    brand_focus_id: Optional[str] = None,
    global_scope: bool = False,
    source_execution_id: str,
    expected_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """Package one probed upload as an immutable, scope-bound canonical Artifact."""
    actor_id, scope = _authorize_content_project(
        actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
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
    if expected_sha256 is not None and observed_sha256 != expected_sha256:
        raise LocalArtifactError("CONTENT_SOURCE_CHANGED_DURING_IMPORT")
    from lumenis.system.security.permission import (
        ContentSourceImport, check_content_source_import_permission, get_permission_gate,
    )

    gate = get_permission_gate()
    principal = actor if type(actor) is LocalWorkspacePrincipal else None
    permission_actor = None if principal is not None else actor
    upload = ContentSourceImport(
        actor_id=actor_id, domain_id="bmp" if scope["domain_id"] == "zbmp" else "cth",
        subject_id=subject_id, brand_focus_id=brand_focus_id, global_scope=global_scope,
        filename=safe_filename, size_bytes=source_stat.st_size, body_sha256=observed_sha256,
        principal_kind=principal.principal_kind if principal is not None else None,
        principal_ref=principal.principal_ref if principal is not None else None,
    )
    permission = check_content_source_import_permission(
        permission_actor, upload, principal=principal, gate=gate,
    )
    if not permission.allowed:
        raise LocalArtifactError("CONTENT_SOURCE_APPROVAL_REQUIRED")
    from lumenis.shared.content_creation.video_editing import fingerprint_local_media

    asset = fingerprint_local_media(str(path))
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
    metadata_bytes = _json_bytes(source_metadata)
    if len(metadata_bytes) > _MAX_CONTENT_SOURCE_METADATA_BYTES:
        raise LocalArtifactError("CONTENT_SOURCE_METADATA_TOO_LARGE")

    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)
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
        with package_handle:
            with zipfile.ZipFile(package_handle, mode="w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("source.json", metadata_bytes)
                archive.write(path, safe_filename)
        archived_digest = hashlib.sha256()
        archived_size = 0
        with zipfile.ZipFile(package_path, "r") as archive:
            with archive.open(safe_filename, "r") as media:
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
        record = _register_artifact(
            artifact_id=artifact_id,
            kind="content_source",
            product_id="CTH" if scope["domain_id"] == "cth" else "ZBMP",
            domain_id=scope["domain_id"],
            source_execution_id=source_execution_id.strip(),
            evidence_id="",
            note_id="",
            path=package_path,
            media_type="application/zip",
        )
        registered = True
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
    return {"artifact": public_record, "asset": asset.to_dict(), "rights_state": "unknown"}


def read_content_source_artifact(
    artifact_id: str,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str,
    subject_id: Optional[str] = None,
    brand_focus_id: Optional[str] = None,
    global_scope: bool = False,
) -> Dict[str, Any]:
    """Return authorized source metadata only; the original media is never served here."""
    metadata, record, _, _ = _verified_content_source(
        artifact_id,
        actor=actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
    )
    public_record = {
        key: record[key]
        for key in (
            "artifact_id", "kind", "product_id", "domain_id", "source_execution_id",
            "filename", "media_type", "size_bytes", "sha256", "status",
            "approval_required", "approval_status", "created_at", "updated_at",
        )
    }
    return {"artifact": public_record, "asset": metadata["asset"], "rights_state": "unknown"}


@contextmanager
def resolve_content_source_assets(
    artifact_refs: Any,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str,
    subject_id: Optional[str] = None,
    brand_focus_id: Optional[str] = None,
    global_scope: bool = False,
) -> Iterator[List[Dict[str, Any]]]:
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
    )
    from lumenis.shared.content_creation.video_editing import fingerprint_local_media

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
                fresh_asset = fingerprint_local_media(str(destination))
                if fresh_asset.to_dict() != metadata["asset"]:
                    raise LocalArtifactError("CONTENT_SOURCE_FINGERPRINT_MISMATCH")
            except LocalArtifactError:
                raise
            except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
                raise LocalArtifactError("CONTENT_SOURCE_ARCHIVE_INVALID") from exc
            resolved.append({"artifact_ref": refs[index], "path": destination, "asset": fresh_asset})
        _authorize_content_project(
            actor, domain_id=domain_id, subject_id=subject_id,
            brand_focus_id=brand_focus_id, global_scope=global_scope, action="read",
        )
        yield resolved


def stage_timeline_artifact(
    timeline: Any,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str,
    subject_id: Optional[str] = None,
    brand_focus_id: Optional[str] = None,
    global_scope: bool = False,
    source_execution_id: str,
    demo_acknowledged: bool,
    output_kind: str = "video",
    previous_artifact_id: Optional[str] = None,
    source_artifact_refs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Render and register one permission-scoped, reopenable content project."""
    actor_id, scope = _authorize_content_project(
        actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
        action="write",
    )
    if not isinstance(source_execution_id, str) or not source_execution_id.strip():
        raise LocalArtifactError("SOURCE_EXECUTION_ID_REQUIRED")
    if type(demo_acknowledged) is not bool:
        raise LocalArtifactError("CONTENT_DEMO_ACKNOWLEDGEMENT_REQUIRED")
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
    if not demo_acknowledged:
        raise LocalArtifactError("CONTENT_DEMO_ACKNOWLEDGEMENT_REQUIRED")

    source_refs, source_entries, _ = _validate_content_source_refs(
        [] if source_artifact_refs is None else source_artifact_refs,
        actor=actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
    )
    if source_refs:
        source_assets = [entry["metadata"]["asset"] for entry in source_entries]
        if [asset.to_dict() for asset in timeline.assets] != source_assets:
            raise LocalArtifactError("CONTENT_SOURCE_TIMELINE_MISMATCH")

    expected_context = _content_artifact_context(actor, actor_id, scope)
    parent_project: Optional[Dict[str, Any]] = None
    if previous_artifact_id is not None:
        parent_project, _, _, _ = _verified_content_project(
            previous_artifact_id,
            actor=actor,
            domain_id=domain_id,
            subject_id=subject_id,
            brand_focus_id=brand_focus_id,
            global_scope=global_scope,
        )
        if (
            parent_project.get("context") != expected_context
            or parent_project.get("output_kind") != output_kind
        ):
            raise LocalArtifactError("CONTENT_PROJECT_PARENT_SCOPE_MISMATCH")
        parent_timeline = parent_project.get("timeline")
        parent_version = parent_timeline.get("version") if isinstance(parent_timeline, dict) else None
        current_version = getattr(timeline, "version", None)
        if (
            type(parent_version) is not int
            or type(current_version) is not int
            or current_version <= parent_version
        ):
            raise LocalArtifactError("CONTENT_PROJECT_PARENT_REVISION_REQUIRED")

    from lumenis.system.security.permission import OperationType, get_permission_gate, is_testing_bypass_enabled

    if is_testing_bypass_enabled():
        raise LocalArtifactError("CONTENT_EXPORT_PERMISSION_UNVERIFIED")
    export_resource = "content-project-export:v1:" + hashlib.sha256(_json_bytes({
        "context": expected_context, "timeline": timeline_data, "source_refs": source_refs,
        "output_kind": output_kind, "parent_artifact_id": previous_artifact_id,
        "demo_acknowledged": demo_acknowledged,
    })).hexdigest()
    gate = get_permission_gate()
    caller = expected_context["principal_ref"] if actor_id is None else f"actor:{actor_id}"
    export_permission = gate.check(
        OperationType.DATA_EXPORT, resource=export_resource,
        caller=caller, domain_id="bmp" if scope["domain_id"] == "zbmp" else "cth",
    )
    if not export_permission.allowed:
        raise LocalArtifactError("CONTENT_EXPORT_PERMISSION_DENIED")

    def check_export_permission() -> None:
        # Use the canonical owner throughout encoding, not a copied authorization.
        _authorize_content_project(actor, action="write", **scope)
        current = gate.check(
            OperationType.DATA_EXPORT, resource=export_resource,
            caller=caller, domain_id="bmp" if scope["domain_id"] == "zbmp" else "cth",
        )
        if not current.allowed or is_testing_bypass_enabled():
            raise LocalArtifactError("CONTENT_EXPORT_PERMISSION_DENIED")

    root = artifact_root()
    root.mkdir(parents=True, exist_ok=True)
    artifact_id = _new_artifact_id()
    media_suffix = ".mp4" if output_kind == "video" else ".wav"
    media_name = f"media{media_suffix}"
    package_path = root / f"{artifact_id}.zip"
    product_id = "CTH" if scope["domain_id"] == "cth" else "ZBMP"
    render_result: Optional[Mapping[str, Any]] = None
    package_created = False
    try:
        with tempfile.TemporaryDirectory(prefix="content-project-") as work_dir:
            rendered_path = Path(work_dir) / media_name
            from lumenis.shared.content_creation.rendering import render_timeline

            measured = render_timeline(timeline, rendered_path, output_kind=output_kind,
                                       check_continue=check_export_permission)
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
            project = {
                "schema_version": 1,
                "timeline": timeline_data,
                "source_artifact_refs": source_refs,
                "context": expected_context,
                "parent_artifact_id": previous_artifact_id,
                "rights": {
                    "state": "unknown",
                    "demo_acknowledged": True,
                    "label": "demo-only / rights unknown",
                },
                "output_kind": output_kind,
            }
            project_bytes = _json_bytes(project)
            render_bytes = _json_bytes(render_result)
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
                    archive.write(rendered_path, media_name)
        package_size = package_path.stat().st_size
        if package_size > _MAX_CONTENT_PROJECT_BYTES:
            raise LocalArtifactError("CONTENT_PROJECT_PACKAGE_TOO_LARGE")
        check_export_permission()
        record = _register_artifact(
            artifact_id=artifact_id,
            kind="content_project",
            product_id=product_id,
            domain_id=scope["domain_id"],
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
        "status": "rendered_staged",
        "artifact": public_record,
        "project": project,
        "render": dict(render_result or {}),
        "rights_state": "unknown",
        "demo_acknowledged": True,
        "approval_required": True,
        "publish_status": "not_performed",
    }


def read_content_project(
    artifact_id: str,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str,
    subject_id: Optional[str] = None,
    brand_focus_id: Optional[str] = None,
    global_scope: bool = False,
) -> Dict[str, Any]:
    """Return verified project and render metadata without source filesystem paths."""
    project, render, _, _ = _verified_content_project(
        artifact_id,
        actor=actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
    )
    return {"project": project, "render": render}


def authorized_project_media(
    artifact_id: str,
    *,
    actor: Mapping[str, Any] | LocalWorkspacePrincipal,
    domain_id: str,
    subject_id: Optional[str] = None,
    brand_focus_id: Optional[str] = None,
    global_scope: bool = False,
) -> Dict[str, Any]:
    """Return authorized package media bytes and safe display metadata."""
    project, render, record, package_path = _verified_content_project(
        artifact_id,
        actor=actor,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        global_scope=global_scope,
    )
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
        brand_focus_id=brand_focus_id, global_scope=global_scope, action="read",
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
    product_id: str = "LUMENIS",
    domain_id: str = "cth",
    source_execution_id: str = "",
    evidence_id: str = "",
    note_id: str = "",
) -> Dict[str, Any]:
    """Render explicit local assets into a staged MP4 artifact.

    The function never invents media when assets are absent.  It returns a
    metadata-only staged artifact record only after ffmpeg has produced a real
    file from the validated inputs.
    """
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
    if item.get("kind") in {"content_source", "content_project"}:
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


__all__ = [
    "LocalArtifactError",
    "artifact_root",
    "artifact_file_path",
    "authorized_project_media",
    "ensure_artifact_table",
    "get_artifact",
    "read_content_source_artifact",
    "read_content_project",
    "resolve_content_source_assets",
    "render_local_video_artifact",
    "stage_content_source_artifact",
    "stage_timeline_artifact",
    "validate_local_asset",
]
