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
import os
import shutil
import sqlite3
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from lumenis.shared.database import get_repository, main_db_path


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
_ASSET_EXTENSIONS = _IMAGE_EXTENSIONS | _VIDEO_EXTENSIONS
_MAX_ASSETS = 8
_MAX_ASSET_BYTES = 500 * 1024 * 1024
_MAX_BRIEF_LENGTH = 2000
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
    if not raw or "://" in lowered or lowered.startswith(("data:", "javascript:")):
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
    item["approval_required"] = bool(item.get("approval_required"))
    return item


def artifact_file_path(artifact_id: str) -> Optional[Path]:
    """Resolve an artifact file only after DB metadata and root confinement."""
    item = get_artifact(artifact_id)
    if not item:
        return None
    root = artifact_root()
    candidate = (root / str(item["relative_path"])).resolve()
    if not _is_relative_to(candidate, root) or not candidate.is_file():
        return None
    return candidate


__all__ = [
    "LocalArtifactError",
    "artifact_root",
    "artifact_file_path",
    "ensure_artifact_table",
    "get_artifact",
    "render_local_video_artifact",
    "validate_local_asset",
]
