"""Minimal, provider-free video editing core for Shared Content & Creation.

This module probes explicitly selected local media and edits a versioned
timeline description. It does not download platform videos, call AI, render,
publish, or claim Evidence, rights, or approval that a canonical owner has not
verified. The existing Artifact renderer is not yet a timeline renderer.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
from urllib.parse import urlsplit


class VideoEditingError(ValueError):
    """Raised for invalid local media or timeline operations."""


ALLOWED_FORMAT_RATIOS = ("9:16", "4:5", "3:4", "16:9")
ALLOWED_OPERATIONS = frozenset({"trim", "split", "reorder", "delete", "transition", "hold"})
MAX_EDIT_TIME_SEC = 24 * 60 * 60
MAX_TRANSITION_DURATION_SEC = 30.0
MAX_SERIALIZED_INTEGER = 1_000_000_000
# File-only protocols still allow playlist demuxers to open other local files.
# User sources are self-contained media; generated concat lists belong only to
# the renderer's private working directory, never to this input boundary.
MEDIA_INPUT_DEMUXERS = "mov,matroska,avi,wav,mp3,flac,ogg,aac,aiff"
_MEDIA_ASSET_FACTORY_TOKEN = object()


@dataclass(frozen=True)
class _MediaProbe:
    duration_sec: float
    has_video: bool
    audio_stream_count: int


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _bounded_number(
    value: Any,
    *,
    error_code: str,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
) -> float:
    """Accept only finite, bounded JSON numeric values (never bool or coercions)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VideoEditingError(error_code)
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise VideoEditingError(error_code) from exc
    if not math.isfinite(number):
        raise VideoEditingError(error_code)
    if minimum is not None and number < minimum:
        raise VideoEditingError(error_code)
    if maximum is not None and number > maximum:
        raise VideoEditingError(error_code)
    return number


def _json_safe_copy(value: Any) -> Any:
    """Validate and copy nested EDL metadata before it crosses serialization."""
    if value is None or type(value) in (str, bool):
        return value
    if type(value) is int:
        if abs(value) > MAX_SERIALIZED_INTEGER:
            raise VideoEditingError("EDL_METADATA_NUMBER_OUT_OF_RANGE")
        return value
    if type(value) is float:
        return _bounded_number(
            value,
            error_code="EDL_METADATA_NUMBER_INVALID",
            minimum=-MAX_EDIT_TIME_SEC,
            maximum=MAX_EDIT_TIME_SEC,
        )
    if isinstance(value, Mapping):
        copied: Dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise VideoEditingError("EDL_METADATA_KEY_INVALID")
            copied[key] = _json_safe_copy(nested)
        return copied
    if isinstance(value, (list, tuple)):
        return [_json_safe_copy(nested) for nested in value]
    raise VideoEditingError("EDL_METADATA_NOT_JSON_SAFE")


@dataclass(frozen=True)
class MediaAsset:
    asset_id: str
    filename: str
    sha256: str
    duration_sec: float
    path: str
    evidence_refs: Tuple[str, ...] = field(default_factory=tuple)
    rights_status: str = "unknown"
    has_video: bool = True
    audio_stream_count: int = 0
    _factory_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.validate()
        object.__setattr__(self, "duration_sec", float(self.duration_sec))

    def validate(self) -> None:
        if self._factory_token is not _MEDIA_ASSET_FACTORY_TOKEN:
            raise VideoEditingError("MEDIA_ASSET_MUST_BE_FINGERPRINTED_FROM_LOCAL_FILE")
        _bounded_number(
            self.duration_sec,
            error_code="MEDIA_ASSET_REQUIRES_FINGERPRINT_AND_DURATION",
            minimum=0.000001,
            maximum=MAX_EDIT_TIME_SEC,
        )
        if not self.asset_id or not self.sha256:
            raise VideoEditingError("MEDIA_ASSET_REQUIRES_FINGERPRINT_AND_DURATION")
        if (
            len(self.sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.sha256.lower())
            or self.asset_id != f"MEDIA-{self.sha256[:16]}"
        ):
            raise VideoEditingError("MEDIA_ASSET_FINGERPRINT_INVALID")
        if (
            type(self.has_video) is not bool
            or type(self.audio_stream_count) is not int
            or self.audio_stream_count < 0
            or self.audio_stream_count > 256
            or (not self.has_video and self.audio_stream_count == 0)
        ):
            raise VideoEditingError("MEDIA_ASSET_STREAM_INVENTORY_INVALID")
        if self.evidence_refs:
            raise VideoEditingError("CANONICAL_EVIDENCE_BINDING_UNAVAILABLE")
        if self.rights_status != "unknown":
            raise VideoEditingError("RIGHTS_STATUS_REQUIRES_CANONICAL_REVIEW")

    @property
    def media_kind(self) -> str:
        if self.has_video:
            return "video_audio" if self.audio_stream_count else "video"
        return "audio"

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        # Never expose an absolute local path through the source-backed UI contract.
        return {
            "asset_id": self.asset_id,
            "filename": self.filename,
            "sha256": self.sha256,
            "duration_sec": self.duration_sec,
            "media_kind": self.media_kind,
            "has_video": self.has_video,
            "audio_stream_count": self.audio_stream_count,
            "evidence_refs": list(self.evidence_refs),
            "rights_status": self.rights_status,
        }


def fingerprint_local_media(
    path: str,
    *,
    duration_sec: Optional[float] = None,
    evidence_refs: Iterable[str] = (),
    rights_status: Optional[str] = None,
) -> MediaAsset:
    """Fingerprint local bytes and probe duration; caller-supplied claims fail closed.

    Evidence and rights stay unasserted until their canonical owners can bind
    them to these exact bytes. Legacy metadata parameters remain temporarily
    accepted only to return explicit errors instead of silently trusting them.
    """
    if duration_sec is not None:
        raise VideoEditingError("CALLER_SUPPLIED_MEDIA_DURATION_NOT_TRUSTED")
    if tuple(evidence_refs):
        raise VideoEditingError("CANONICAL_EVIDENCE_BINDING_UNAVAILABLE")
    if rights_status not in (None, "", "unknown"):
        raise VideoEditingError("RIGHTS_STATUS_REQUIRES_CANONICAL_REVIEW")

    raw = str(path or "").strip()
    if raw.startswith(("//", "\\\\")):
        raise VideoEditingError("LOCAL_MEDIA_ONLY")
    parsed = urlsplit(raw)
    windows_drive = len(raw) >= 3 and raw[1] == ":" and raw[2] in {"\\", "/"}
    if not raw or (parsed.scheme and not windows_drive) or parsed.netloc:
        raise VideoEditingError("LOCAL_MEDIA_ONLY")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise VideoEditingError("LOCAL_MEDIA_MUST_BE_ABSOLUTE")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise VideoEditingError("LOCAL_MEDIA_NOT_FOUND") from exc
    if not resolved.is_file():
        raise VideoEditingError("LOCAL_MEDIA_NOT_FILE")

    try:
        before = resolved.stat()
    except OSError as exc:
        raise VideoEditingError("LOCAL_MEDIA_NOT_READABLE") from exc
    digest = hashlib.sha256()
    try:
        with resolved.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise VideoEditingError("LOCAL_MEDIA_NOT_READABLE") from exc
    probe = _probe_media_info(resolved)
    duration = probe.duration_sec
    try:
        after = resolved.stat()
    except OSError as exc:
        raise VideoEditingError("LOCAL_MEDIA_CHANGED_DURING_FINGERPRINT") from exc
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise VideoEditingError("LOCAL_MEDIA_CHANGED_DURING_FINGERPRINT")

    media_hash = digest.hexdigest()
    return MediaAsset(
        asset_id=f"MEDIA-{media_hash[:16]}",
        filename=resolved.name,
        sha256=media_hash,
        duration_sec=duration,
        path=str(resolved),
        evidence_refs=(),
        rights_status="unknown",
        has_video=probe.has_video,
        audio_stream_count=probe.audio_stream_count,
        _factory_token=_MEDIA_ASSET_FACTORY_TOKEN,
    )


def _ffprobe_path() -> Optional[str]:
    """Find ffprobe from the environment or beside the existing FFmpeg owner."""
    configured = str(os.environ.get("LUMENIS_FFPROBE_PATH") or "").strip()
    candidates: List[Path] = [Path(configured).expanduser()] if configured else []
    found = shutil.which("ffprobe")
    if found:
        candidates.append(Path(found))
    try:
        # Reuse the established toolchain locator without invoking its renderer.
        import shared_artifacts

        ffmpeg = shared_artifacts._ffmpeg_path()
        if ffmpeg:
            candidates.append(Path(ffmpeg).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe"))
    except Exception:
        pass
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            if resolved.is_file():
                return str(resolved)
        except OSError:
            continue
    return None


def _probe_media_info(path: Path) -> _MediaProbe:
    """Read real local audio/video streams and duration using the existing FFprobe."""
    ffprobe = _ffprobe_path()
    if not ffprobe:
        raise VideoEditingError("MEDIA_DURATION_PROBE_UNAVAILABLE")
    try:
        completed = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-protocol_whitelist", "file",
                "-format_whitelist", MEDIA_INPUT_DEMUXERS,
                "-show_entries", "stream=codec_type,duration:format=duration",
                "-of", "json",
                "-i", str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
            shell=False,
        )
        payload = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VideoEditingError("MEDIA_DURATION_PROBE_FAILED") from exc
    streams = payload.get("streams") if isinstance(payload, dict) else None
    if not isinstance(streams, list):
        raise VideoEditingError("MEDIA_DURATION_PROBE_FAILED")
    video_streams = [
        stream for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "video"
    ]
    audio_streams = [
        stream for stream in streams
        if isinstance(stream, dict) and stream.get("codec_type") == "audio"
    ]
    if not video_streams and not audio_streams:
        raise VideoEditingError("LOCAL_MEDIA_HAS_NO_AUDIO_OR_VIDEO_STREAM")
    duration_stream = video_streams[0] if video_streams else audio_streams[0]
    raw_duration = duration_stream.get("duration")
    if raw_duration in (None, "", "N/A"):
        format_info = payload.get("format")
        raw_duration = format_info.get("duration") if isinstance(format_info, dict) else None
    try:
        duration = float(raw_duration)
    except (TypeError, ValueError) as exc:
        raise VideoEditingError("MEDIA_DURATION_PROBE_FAILED") from exc
    if not math.isfinite(duration) or duration <= 0 or duration > MAX_EDIT_TIME_SEC:
        raise VideoEditingError("MEDIA_DURATION_PROBE_FAILED")
    return _MediaProbe(
        duration_sec=duration,
        has_video=bool(video_streams),
        audio_stream_count=len(audio_streams),
    )


def _probe_media_duration(path: Path) -> float:
    """Compatibility helper exposing the real duration only."""
    return _probe_media_info(path).duration_sec


@dataclass(frozen=True)
class AudioMix:
    volume: float = 1.0
    fade_in_sec: float = 0.0
    fade_out_sec: float = 0.0
    ducking: bool = False

    def __post_init__(self) -> None:
        self.validate()

    def validate(self, *, duration_sec: Optional[float] = None) -> None:
        _bounded_number(self.volume, error_code="INVALID_AUDIO_MIX", minimum=0, maximum=2)
        fade_in = _bounded_number(
            self.fade_in_sec,
            error_code="INVALID_AUDIO_MIX",
            minimum=0,
            maximum=MAX_EDIT_TIME_SEC,
        )
        fade_out = _bounded_number(
            self.fade_out_sec,
            error_code="INVALID_AUDIO_MIX",
            minimum=0,
            maximum=MAX_EDIT_TIME_SEC,
        )
        if type(self.ducking) is not bool:
            raise VideoEditingError("INVALID_AUDIO_MIX")
        if duration_sec is not None:
            duration = _bounded_number(
                duration_sec,
                error_code="INVALID_AUDIO_MIX",
                minimum=0.000001,
                maximum=MAX_EDIT_TIME_SEC,
            )
            if fade_in > duration or fade_out > duration:
                raise VideoEditingError("INVALID_AUDIO_MIX")
            if fade_in + fade_out > duration:
                raise VideoEditingError("INVALID_AUDIO_MIX")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "volume": self.volume,
            "fade_in_sec": self.fade_in_sec,
            "fade_out_sec": self.fade_out_sec,
            "ducking": self.ducking,
        }


@dataclass(frozen=True)
class TimelineClip:
    clip_id: str
    media_asset_id: str
    source_in: float
    source_out: float
    timeline_start: float
    track_id: str = "video"
    purpose: str = ""
    audio_role: str = "original"
    audio_mix: AudioMix = field(default_factory=AudioMix)
    evidence_refs: Tuple[str, ...] = field(default_factory=tuple)
    audio_stream_index: Optional[int] = None

    def __post_init__(self) -> None:
        self.validate()

    @property
    def duration_sec(self) -> float:
        source_in = _bounded_number(
            self.source_in, error_code="INVALID_CLIP_RANGE", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        source_out = _bounded_number(
            self.source_out, error_code="INVALID_CLIP_RANGE", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        duration = source_out - source_in
        rounded_duration = round(duration, 6)
        if rounded_duration < 0.000001 or not math.isfinite(duration):
            raise VideoEditingError("INVALID_CLIP_RANGE")
        return rounded_duration

    def validate(self) -> None:
        source_in = _bounded_number(
            self.source_in, error_code="INVALID_CLIP_RANGE", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        source_out = _bounded_number(
            self.source_out, error_code="INVALID_CLIP_RANGE", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        timeline_start = _bounded_number(
            self.timeline_start, error_code="INVALID_CLIP_RANGE", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        duration = source_out - source_in
        if (
            duration < 0.000001
            or timeline_start + duration > MAX_EDIT_TIME_SEC
            or not self.clip_id
            or not self.media_asset_id
            or not self.track_id
        ):
            raise VideoEditingError("INVALID_CLIP_RANGE")
        if self.audio_role not in {"original", "muted", "voiceover", "bgm", "sfx"}:
            raise VideoEditingError("AUDIO_TRACK_ROLE_NOT_ALLOWED")
        if self.audio_stream_index is not None and (
            type(self.audio_stream_index) is not int or self.audio_stream_index < 0
        ):
            raise VideoEditingError("AUDIO_STREAM_INDEX_OUT_OF_RANGE")
        if self.evidence_refs:
            raise VideoEditingError("CANONICAL_EVIDENCE_BINDING_UNAVAILABLE")
        if not isinstance(self.audio_mix, AudioMix):
            raise VideoEditingError("INVALID_AUDIO_MIX")
        self.audio_mix.validate(duration_sec=source_out - source_in)

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "clip_id": self.clip_id,
            "media_asset_id": self.media_asset_id,
            "source_in": self.source_in,
            "source_out": self.source_out,
            "timeline_start": self.timeline_start,
            "track_id": self.track_id,
            "purpose": self.purpose,
            "audio_role": self.audio_role,
            "audio_mix": self.audio_mix.to_dict(),
            "evidence_refs": list(self.evidence_refs),
            "audio_stream_index": self.audio_stream_index,
        }


@dataclass(frozen=True)
class TimelineTrack:
    track_id: str
    kind: str
    clips: Tuple[TimelineClip, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.track_id, str) or not self.track_id.strip():
            raise VideoEditingError("TIMELINE_TRACK_ID_REQUIRED")
        if not isinstance(self.kind, str) or self.kind not in {"video", "voiceover", "bgm", "sfx"}:
            raise VideoEditingError("TIMELINE_TRACK_KIND_NOT_ALLOWED")
        if not isinstance(self.clips, tuple):
            raise VideoEditingError("TIMELINE_TRACK_CLIPS_INVALID")
        for clip in self.clips:
            if not isinstance(clip, TimelineClip):
                raise VideoEditingError("TIMELINE_TRACK_CLIPS_INVALID")
            clip.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {"track_id": self.track_id, "kind": self.kind, "clips": [clip.to_dict() for clip in self.clips]}


@dataclass(frozen=True)
class Transition:
    from_clip: str
    to_clip: str
    transition_type: str
    duration_sec: float
    reason: str

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.from_clip or not self.to_clip or self.from_clip == self.to_clip:
            raise VideoEditingError("INVALID_TRANSITION")
        if not isinstance(self.transition_type, str) or not self.transition_type.strip():
            raise VideoEditingError("INVALID_TRANSITION")
        _bounded_number(
            self.duration_sec,
            error_code="INVALID_TRANSITION_DURATION",
            minimum=0,
            maximum=MAX_TRANSITION_DURATION_SEC,
        )
        if self.transition_type != "cut":
            if self.duration_sec <= 0:
                raise VideoEditingError("INVALID_TRANSITION_DURATION")
            if not isinstance(self.reason, str) or not self.reason.strip():
                raise VideoEditingError("TRANSITION_REASON_REQUIRED")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "from_clip": self.from_clip,
            "to_clip": self.to_clip,
            "transition_type": self.transition_type,
            "duration_sec": self.duration_sec,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TimedOverlay:
    overlay_id: str
    kind: str
    start_sec: float
    end_sec: float
    text: str

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        start = _bounded_number(
            self.start_sec, error_code="INVALID_TIMED_OVERLAY", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        end = _bounded_number(
            self.end_sec, error_code="INVALID_TIMED_OVERLAY", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        if (
            end - start < 0.000001
            or not isinstance(self.kind, str)
            or self.kind not in {"caption", "text"}
            or not str(self.text or "").strip()
        ):
            raise VideoEditingError("INVALID_TIMED_OVERLAY")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "overlay_id": self.overlay_id,
            "kind": self.kind,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "text": self.text,
        }


@dataclass(frozen=True)
class _TimelineSnapshot:
    tracks: Tuple[TimelineTrack, ...]
    transitions: Tuple[Transition, ...]
    overlays: Tuple[TimedOverlay, ...]
    format_ratio: str


@dataclass(frozen=True)
class Timeline:
    assets: Tuple[MediaAsset, ...]
    tracks: Tuple[TimelineTrack, ...] = field(default_factory=lambda: (TimelineTrack("video", "video"),))
    transitions: Tuple[Transition, ...] = field(default_factory=tuple)
    overlays: Tuple[TimedOverlay, ...] = field(default_factory=tuple)
    format_ratio: str = "9:16"
    version: int = 1
    _history: Tuple[_TimelineSnapshot, ...] = field(default_factory=tuple, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if type(self.version) is not int or not 1 <= self.version <= MAX_SERIALIZED_INTEGER:
            raise VideoEditingError("TIMELINE_VERSION_INVALID")
        if self.format_ratio not in ALLOWED_FORMAT_RATIOS:
            raise VideoEditingError("FORMAT_RATIO_NOT_SUPPORTED")
        if not isinstance(self.assets, tuple) or not self.assets:
            raise VideoEditingError("TIMELINE_REQUIRES_MEDIA_ASSET")
        if not isinstance(self.tracks, tuple) or not self.tracks:
            raise VideoEditingError("TIMELINE_TRACKS_INVALID")
        if not isinstance(self.transitions, tuple) or not isinstance(self.overlays, tuple):
            raise VideoEditingError("TIMELINE_COMPONENTS_INVALID")

        assets: Dict[str, MediaAsset] = {}
        for asset in self.assets:
            if not isinstance(asset, MediaAsset):
                raise VideoEditingError("TIMELINE_MEDIA_ASSETS_INVALID")
            asset.validate()
            if asset.asset_id in assets:
                raise VideoEditingError("TIMELINE_DUPLICATE_MEDIA_ASSET")
            assets[asset.asset_id] = asset

        track_ids = set()
        clip_ids = set()
        clips: Dict[str, TimelineClip] = {}
        for track in self.tracks:
            if not isinstance(track, TimelineTrack):
                raise VideoEditingError("TIMELINE_TRACKS_INVALID")
            track.validate()
            if track.track_id in track_ids:
                raise VideoEditingError("TIMELINE_TRACK_ALREADY_EXISTS")
            track_ids.add(track.track_id)
            for clip in track.clips:
                if clip.track_id != track.track_id or clip.media_asset_id not in assets:
                    raise VideoEditingError("TIMELINE_CLIP_SOURCE_INVALID")
                asset = assets[clip.media_asset_id]
                if clip.source_out > asset.duration_sec:
                    raise VideoEditingError("CLIP_RANGE_OUTSIDE_MEDIA_ASSET")
                if track.kind == "video" and not asset.has_video:
                    raise VideoEditingError("VIDEO_TRACK_REQUIRES_VIDEO_ASSET")
                if track.kind != "video":
                    if asset.audio_stream_count < 1:
                        raise VideoEditingError("AUDIO_TRACK_REQUIRES_AUDIO_ASSET")
                    if clip.audio_role != track.kind:
                        raise VideoEditingError("AUDIO_TRACK_ROLE_MISMATCH")
                    if clip.audio_stream_index is None:
                        raise VideoEditingError("AUDIO_STREAM_SELECTION_REQUIRED")
                elif clip.audio_role not in {"original", "muted"}:
                    raise VideoEditingError("AUDIO_TRACK_ROLE_NOT_ALLOWED")
                elif clip.audio_role == "muted" and clip.audio_stream_index is not None:
                    raise VideoEditingError("MUTED_VIDEO_CLIP_CANNOT_SELECT_AUDIO")
                if clip.audio_stream_index is not None and clip.audio_stream_index >= asset.audio_stream_count:
                    raise VideoEditingError("AUDIO_STREAM_INDEX_OUT_OF_RANGE")
                if (
                    track.kind == "video"
                    and clip.audio_role == "original"
                    and asset.audio_stream_count > 1
                    and clip.audio_stream_index is None
                ):
                    raise VideoEditingError("MULTIPLE_SOURCE_AUDIO_TRACKS_REQUIRE_EXPLICIT_SELECTION")
                if clip.clip_id in clip_ids:
                    raise VideoEditingError("TIMELINE_DUPLICATE_CLIP")
                clip_ids.add(clip.clip_id)
                clips[clip.clip_id] = clip

        for transition in self.transitions:
            if not isinstance(transition, Transition):
                raise VideoEditingError("TIMELINE_TRANSITIONS_INVALID")
            transition.validate()
            if transition.from_clip not in clips or transition.to_clip not in clips:
                raise VideoEditingError("TRANSITION_CLIP_NOT_FOUND")
            if transition.duration_sec > min(
                clips[transition.from_clip].duration_sec,
                clips[transition.to_clip].duration_sec,
            ):
                raise VideoEditingError("TRANSITION_DURATION_EXCEEDS_CLIP")

        for overlay in self.overlays:
            if not isinstance(overlay, TimedOverlay):
                raise VideoEditingError("TIMELINE_OVERLAYS_INVALID")
            overlay.validate()

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        assets: Iterable[MediaAsset],
    ) -> "Timeline":
        """Reopen a sanitized timeline against freshly fingerprinted local assets.

        The document supplies edit intent only. Asset paths, factory tokens,
        Evidence, rights claims, and other unrecognized fields are never loaded
        from stored data.
        """

        def document_object(value: Any, fields: Tuple[str, ...]) -> Dict[str, Any]:
            if type(value) is not dict or set(value) != set(fields):
                raise VideoEditingError("TIMELINE_DOCUMENT_FIELDS_INVALID")
            return value

        def document_list(value: Any) -> List[Any]:
            if type(value) is not list:
                raise VideoEditingError("TIMELINE_DOCUMENT_LIST_INVALID")
            return value

        def document_string(value: Any) -> str:
            if not isinstance(value, str):
                raise VideoEditingError("TIMELINE_DOCUMENT_VALUE_INVALID")
            return value

        root = document_object(
            payload,
            ("version", "format_ratio", "assets", "tracks", "transitions", "overlays", "approval_required"),
        )
        if type(root["version"]) is not int or root["version"] < 1:
            raise VideoEditingError("TIMELINE_VERSION_INVALID")
        if type(root["approval_required"]) is not bool or root["approval_required"] is not True:
            raise VideoEditingError("TIMELINE_DOCUMENT_VALUE_INVALID")

        fresh_assets: Dict[str, MediaAsset] = {}
        for asset in assets:
            if not isinstance(asset, MediaAsset):
                raise VideoEditingError("TIMELINE_MEDIA_ASSETS_INVALID")
            asset.validate()
            if asset.asset_id in fresh_assets:
                raise VideoEditingError("TIMELINE_DUPLICATE_MEDIA_ASSET")
            try:
                confirmed = fingerprint_local_media(asset.path)
            except VideoEditingError as exc:
                raise VideoEditingError("TIMELINE_REOPEN_ASSET_UNAVAILABLE") from exc
            if confirmed.to_dict() != asset.to_dict():
                raise VideoEditingError("TIMELINE_REOPEN_ASSET_MISMATCH")
            fresh_assets[asset.asset_id] = confirmed

        stored_assets = document_list(root["assets"])
        ordered_assets: List[MediaAsset] = []
        stored_asset_ids = set()
        asset_fields = (
            "asset_id", "filename", "sha256", "duration_sec", "media_kind",
            "has_video", "audio_stream_count", "evidence_refs", "rights_status",
        )
        for stored in stored_assets:
            item = document_object(stored, asset_fields)
            asset_id = document_string(item["asset_id"])
            if asset_id in stored_asset_ids:
                raise VideoEditingError("TIMELINE_DUPLICATE_MEDIA_ASSET")
            stored_asset_ids.add(asset_id)
            asset = fresh_assets.get(asset_id)
            if asset is None:
                raise VideoEditingError("TIMELINE_REOPEN_ASSET_MISSING")
            duration = _bounded_number(
                item["duration_sec"], error_code="TIMELINE_DOCUMENT_VALUE_INVALID",
                minimum=0.000001, maximum=MAX_EDIT_TIME_SEC,
            )
            if (
                item["filename"] != asset.filename
                or item["sha256"] != asset.sha256
                or duration != asset.duration_sec
                or item["media_kind"] != asset.media_kind
                or type(item["has_video"]) is not bool
                or item["has_video"] is not asset.has_video
                or type(item["audio_stream_count"]) is not int
                or item["audio_stream_count"] != asset.audio_stream_count
                or item["evidence_refs"] != []
                or item["rights_status"] != "unknown"
            ):
                raise VideoEditingError("TIMELINE_REOPEN_ASSET_MISMATCH")
            ordered_assets.append(asset)
        if not stored_assets or stored_asset_ids != set(fresh_assets):
            raise VideoEditingError("TIMELINE_REOPEN_ASSET_MISMATCH")

        tracks: List[TimelineTrack] = []
        track_fields = ("track_id", "kind", "clips")
        clip_fields = (
            "clip_id", "media_asset_id", "source_in", "source_out", "timeline_start",
            "track_id", "purpose", "audio_role", "audio_mix", "evidence_refs",
            "audio_stream_index",
        )
        mix_fields = ("volume", "fade_in_sec", "fade_out_sec", "ducking")
        for stored_track in document_list(root["tracks"]):
            track_data = document_object(stored_track, track_fields)
            track_id = document_string(track_data["track_id"])
            kind = document_string(track_data["kind"])
            clips: List[TimelineClip] = []
            for stored_clip in document_list(track_data["clips"]):
                clip_data = document_object(stored_clip, clip_fields)
                mix_data = document_object(clip_data["audio_mix"], mix_fields)
                if type(clip_data["evidence_refs"]) is not list or clip_data["evidence_refs"]:
                    raise VideoEditingError("CANONICAL_EVIDENCE_BINDING_UNAVAILABLE")
                if type(mix_data["ducking"]) is not bool:
                    raise VideoEditingError("TIMELINE_DOCUMENT_VALUE_INVALID")
                audio_index = clip_data["audio_stream_index"]
                if audio_index is not None and type(audio_index) is not int:
                    raise VideoEditingError("AUDIO_STREAM_INDEX_OUT_OF_RANGE")
                try:
                    mix = AudioMix(
                        volume=mix_data["volume"],
                        fade_in_sec=mix_data["fade_in_sec"],
                        fade_out_sec=mix_data["fade_out_sec"],
                        ducking=mix_data["ducking"],
                    )
                    clips.append(TimelineClip(
                        clip_id=document_string(clip_data["clip_id"]),
                        media_asset_id=document_string(clip_data["media_asset_id"]),
                        source_in=clip_data["source_in"],
                        source_out=clip_data["source_out"],
                        timeline_start=clip_data["timeline_start"],
                        track_id=document_string(clip_data["track_id"]),
                        purpose=document_string(clip_data["purpose"]),
                        audio_role=document_string(clip_data["audio_role"]),
                        audio_mix=mix,
                        evidence_refs=(),
                        audio_stream_index=audio_index,
                    ))
                except (TypeError, ValueError) as exc:
                    if isinstance(exc, VideoEditingError):
                        raise
                    raise VideoEditingError("TIMELINE_DOCUMENT_VALUE_INVALID") from exc
            tracks.append(TimelineTrack(track_id=track_id, kind=kind, clips=tuple(clips)))

        transitions: List[Transition] = []
        transition_fields = ("from_clip", "to_clip", "transition_type", "duration_sec", "reason")
        for stored_transition in document_list(root["transitions"]):
            item = document_object(stored_transition, transition_fields)
            transitions.append(Transition(
                from_clip=document_string(item["from_clip"]),
                to_clip=document_string(item["to_clip"]),
                transition_type=document_string(item["transition_type"]),
                duration_sec=item["duration_sec"],
                reason=document_string(item["reason"]),
            ))

        overlays: List[TimedOverlay] = []
        overlay_fields = ("overlay_id", "kind", "start_sec", "end_sec", "text")
        for stored_overlay in document_list(root["overlays"]):
            item = document_object(stored_overlay, overlay_fields)
            overlays.append(TimedOverlay(
                overlay_id=document_string(item["overlay_id"]),
                kind=document_string(item["kind"]),
                start_sec=item["start_sec"],
                end_sec=item["end_sec"],
                text=document_string(item["text"]),
            ))

        return cls(
            assets=tuple(ordered_assets),
            tracks=tuple(tracks),
            transitions=tuple(transitions),
            overlays=tuple(overlays),
            format_ratio=document_string(root["format_ratio"]),
            version=root["version"],
        )

    @classmethod
    def from_assets(cls, assets: Iterable[MediaAsset], format_ratio: str = "9:16") -> "Timeline":
        assets_by_id: Dict[str, MediaAsset] = {}
        for asset in assets:
            if not isinstance(asset, MediaAsset):
                raise VideoEditingError("TIMELINE_MEDIA_ASSETS_INVALID")
            asset.validate()
            existing = assets_by_id.get(asset.asset_id)
            if existing and (
                existing.sha256 != asset.sha256 or existing.duration_sec != asset.duration_sec
            ):
                raise VideoEditingError("TIMELINE_DUPLICATE_MEDIA_ASSET")
            assets_by_id.setdefault(asset.asset_id, asset)
        assets_tuple = tuple(assets_by_id.values())
        if not assets_tuple:
            raise VideoEditingError("TIMELINE_REQUIRES_MEDIA_ASSET")
        if format_ratio not in ALLOWED_FORMAT_RATIOS:
            raise VideoEditingError("FORMAT_RATIO_NOT_SUPPORTED")
        return cls(assets=assets_tuple, format_ratio=format_ratio)

    def _asset(self, asset_id: str) -> MediaAsset:
        for asset in self.assets:
            if asset.asset_id == asset_id:
                return asset
        raise VideoEditingError("MEDIA_ASSET_NOT_IN_TIMELINE")

    def _track(self, track_id: str) -> TimelineTrack:
        for track in self.tracks:
            if track.track_id == track_id:
                return track
        raise VideoEditingError("TIMELINE_TRACK_NOT_FOUND")

    def add_audio_track(self, track_id: str, *, audio_role: str) -> "Timeline":
        """Add an explicit voice-over, BGM, or SFX track to the timeline."""
        normalized_role = str(audio_role or "").strip().lower()
        if normalized_role not in {"voiceover", "bgm", "sfx"}:
            raise VideoEditingError("AUDIO_TRACK_ROLE_NOT_ALLOWED")
        if any(track.track_id == track_id for track in self.tracks):
            raise VideoEditingError("TIMELINE_TRACK_ALREADY_EXISTS")
        track = TimelineTrack(str(track_id).strip(), normalized_role)
        if not track.track_id:
            raise VideoEditingError("TIMELINE_TRACK_ID_REQUIRED")
        return self._commit(tracks=(*self.tracks, track))

    def _snapshot(self) -> _TimelineSnapshot:
        return _TimelineSnapshot(self.tracks, self.transitions, self.overlays, self.format_ratio)

    def _commit(
        self,
        *,
        tracks: Optional[Tuple[TimelineTrack, ...]] = None,
        transitions: Optional[Tuple[Transition, ...]] = None,
        overlays: Optional[Tuple[TimedOverlay, ...]] = None,
        format_ratio: Optional[str] = None,
    ) -> "Timeline":
        return replace(
            self,
            tracks=tracks if tracks is not None else self.tracks,
            transitions=transitions if transitions is not None else self.transitions,
            overlays=overlays if overlays is not None else self.overlays,
            format_ratio=format_ratio if format_ratio is not None else self.format_ratio,
            version=self.version + 1,
            _history=self._history + (self._snapshot(),),
        )

    @staticmethod
    def _reflow(track: TimelineTrack, clips: Iterable[TimelineClip]) -> TimelineTrack:
        cursor = 0.0
        result: List[TimelineClip] = []
        for clip in clips:
            updated = replace(clip, timeline_start=round(cursor, 6))
            updated.validate()
            result.append(updated)
            cursor += updated.duration_sec
            if not math.isfinite(cursor) or cursor > MAX_EDIT_TIME_SEC:
                raise VideoEditingError("TIMELINE_DURATION_OUT_OF_RANGE")
        return replace(track, clips=tuple(result))

    def add_clip(
        self,
        media_asset_id: str,
        *,
        source_in: float = 0.0,
        source_out: Optional[float] = None,
        track_id: str = "video",
        purpose: str = "",
        audio_role: str = "original",
        timeline_start: Optional[float] = None,
        audio_stream_index: Optional[int] = None,
    ) -> "Timeline":
        self.validate()
        asset = self._asset(media_asset_id)
        track = self._track(track_id)
        source_start = _bounded_number(
            source_in, error_code="CLIP_RANGE_OUTSIDE_MEDIA_ASSET", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        out = asset.duration_sec if source_out is None else _bounded_number(
            source_out,
            error_code="CLIP_RANGE_OUTSIDE_MEDIA_ASSET",
            minimum=0,
            maximum=MAX_EDIT_TIME_SEC,
        )
        if out > asset.duration_sec or out <= source_start:
            raise VideoEditingError("CLIP_RANGE_OUTSIDE_MEDIA_ASSET")
        if track.kind == "video":
            if not asset.has_video:
                raise VideoEditingError("VIDEO_TRACK_REQUIRES_VIDEO_ASSET")
            if timeline_start is not None:
                raise VideoEditingError("VIDEO_TRACK_TIMELINE_POSITION_AUTOMATIC")
            if audio_role not in {"original", "muted"}:
                raise VideoEditingError("AUDIO_TRACK_ROLE_NOT_ALLOWED")
            if audio_role == "original" and asset.audio_stream_count > 1 and audio_stream_index is None:
                raise VideoEditingError("MULTIPLE_SOURCE_AUDIO_TRACKS_REQUIRE_EXPLICIT_SELECTION")
            if audio_role == "original" and audio_stream_index is None and asset.audio_stream_count == 1:
                audio_stream_index = 0
            if audio_role == "muted" and audio_stream_index is not None:
                raise VideoEditingError("MUTED_VIDEO_CLIP_CANNOT_SELECT_AUDIO")
            timeline_position = 0.0
            clip_audio_role = audio_role
        else:
            if asset.audio_stream_count < 1:
                raise VideoEditingError("AUDIO_TRACK_REQUIRES_AUDIO_ASSET")
            if audio_role not in {"original", track.kind}:
                raise VideoEditingError("AUDIO_TRACK_ROLE_MISMATCH")
            if audio_stream_index is None:
                if asset.audio_stream_count > 1:
                    raise VideoEditingError("MULTIPLE_SOURCE_AUDIO_TRACKS_REQUIRE_EXPLICIT_SELECTION")
                audio_stream_index = 0
            if type(audio_stream_index) is not int or not 0 <= audio_stream_index < asset.audio_stream_count:
                raise VideoEditingError("AUDIO_STREAM_INDEX_OUT_OF_RANGE")
            timeline_position = 0.0 if timeline_start is None else _bounded_number(
                timeline_start,
                error_code="INVALID_CLIP_RANGE",
                minimum=0,
                maximum=MAX_EDIT_TIME_SEC,
            )
            if timeline_position + (out - source_start) > MAX_EDIT_TIME_SEC:
                raise VideoEditingError("TIMELINE_DURATION_OUT_OF_RANGE")
            clip_audio_role = track.kind
        clip = TimelineClip(
            clip_id=_id("CLIP"),
            media_asset_id=media_asset_id,
            source_in=source_start,
            source_out=out,
            timeline_start=timeline_position,
            track_id=track_id,
            purpose=purpose,
            audio_role=clip_audio_role,
            evidence_refs=asset.evidence_refs,
            audio_stream_index=audio_stream_index,
        )
        updated = (
            self._reflow(track, (*track.clips, clip))
            if track.kind == "video"
            else replace(track, clips=(*track.clips, clip))
        )
        tracks = tuple(updated if item.track_id == track_id else item for item in self.tracks)
        return self._commit(tracks=tracks)

    def _replace_clip(self, track: TimelineTrack, clip: TimelineClip) -> "Timeline":
        clips = tuple(clip if item.clip_id == clip.clip_id else item for item in track.clips)
        updated = self._reflow(track, clips) if track.kind == "video" else replace(track, clips=clips)
        tracks = tuple(updated if item.track_id == track.track_id else item for item in self.tracks)
        return self._commit(tracks=tracks)

    def _find_clip(self, clip_id: str) -> Tuple[TimelineTrack, TimelineClip]:
        for track in self.tracks:
            for clip in track.clips:
                if clip.clip_id == clip_id:
                    return track, clip
        raise VideoEditingError("TIMELINE_CLIP_NOT_FOUND")

    def trim(self, clip_id: str, *, source_in: float, source_out: float) -> "Timeline":
        self.validate()
        track, clip = self._find_clip(clip_id)
        asset = self._asset(clip.media_asset_id)
        source_start = _bounded_number(
            source_in, error_code="TRIM_RANGE_OUTSIDE_MEDIA_ASSET", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        source_end = _bounded_number(
            source_out, error_code="TRIM_RANGE_OUTSIDE_MEDIA_ASSET", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        if source_end > asset.duration_sec or source_end <= source_start:
            raise VideoEditingError("TRIM_RANGE_OUTSIDE_MEDIA_ASSET")
        return self._replace_clip(track, replace(clip, source_in=source_start, source_out=source_end))

    def split(self, clip_id: str, *, at_sec: float) -> "Timeline":
        self.validate()
        track, clip = self._find_clip(clip_id)
        at = _bounded_number(
            at_sec, error_code="SPLIT_POINT_OUTSIDE_CLIP", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        if not clip.source_in < at < clip.source_out:
            raise VideoEditingError("SPLIT_POINT_OUTSIDE_CLIP")
        first_duration = round(at - clip.source_in, 6)
        second_duration = round(clip.source_out - at, 6)
        first_mix = replace(
            clip.audio_mix,
            fade_in_sec=min(clip.audio_mix.fade_in_sec, first_duration),
            fade_out_sec=0.0,
        )
        second_mix = replace(
            clip.audio_mix,
            fade_in_sec=0.0,
            fade_out_sec=min(clip.audio_mix.fade_out_sec, second_duration),
        )
        first = replace(
            clip, clip_id=f"{clip.clip_id}-a", source_out=at, audio_mix=first_mix
        )
        second = replace(
            clip,
            clip_id=f"{clip.clip_id}-b",
            source_in=at,
            timeline_start=round(clip.timeline_start + (at - clip.source_in), 6),
            audio_mix=second_mix,
        )
        clips: List[TimelineClip] = []
        for item in track.clips:
            clips.extend((first, second) if item.clip_id == clip_id else (item,))
        updated = self._reflow(track, clips) if track.kind == "video" else replace(track, clips=tuple(clips))
        tracks = tuple(updated if item.track_id == track.track_id else item for item in self.tracks)
        transitions = tuple(
            item for item in self.transitions if item.from_clip != clip_id and item.to_clip != clip_id
        )
        return self._commit(tracks=tracks, transitions=transitions)

    def reorder(self, clip_id: str, *, new_index: int) -> "Timeline":
        self.validate()
        track, clip = self._find_clip(clip_id)
        if track.kind != "video":
            raise VideoEditingError("REORDER_VIDEO_TRACK_ONLY")
        clips = [item for item in track.clips if item.clip_id != clip_id]
        if type(new_index) is not int or not 0 <= new_index <= len(clips):
            raise VideoEditingError("REORDER_INDEX_OUT_OF_RANGE")
        clips.insert(new_index, clip)
        updated = self._reflow(track, clips)
        tracks = tuple(updated if item.track_id == track.track_id else item for item in self.tracks)
        return self._commit(tracks=tracks)

    def delete(self, clip_id: str, *, ripple: bool = True) -> "Timeline":
        self.validate()
        if type(ripple) is not bool:
            raise VideoEditingError("DELETE_RIPPLE_FLAG_INVALID")
        track, _ = self._find_clip(clip_id)
        clips = tuple(item for item in track.clips if item.clip_id != clip_id)
        updated = self._reflow(track, clips) if ripple and track.kind == "video" else replace(track, clips=clips)
        tracks = tuple(updated if item.track_id == track.track_id else item for item in self.tracks)
        transitions = tuple(item for item in self.transitions if clip_id not in {item.from_clip, item.to_clip})
        return self._commit(tracks=tracks, transitions=transitions)

    def add_transition(
        self,
        from_clip: str,
        to_clip: str,
        *,
        transition_type: str = "dissolve",
        duration_sec: float = 0.3,
        reason: str,
    ) -> "Timeline":
        self.validate()
        track, from_item = self._find_clip(from_clip)
        other, to_item = self._find_clip(to_clip)
        if track.track_id != other.track_id or track.kind != "video":
            raise VideoEditingError("TRANSITION_REQUIRES_ONE_VIDEO_TRACK")
        ids = [clip.clip_id for clip in track.clips]
        if ids.index(to_clip) != ids.index(from_clip) + 1:
            raise VideoEditingError("TRANSITION_REQUIRES_ADJACENT_CLIPS")
        if transition_type != "cut" and not reason.strip():
            raise VideoEditingError("TRANSITION_REASON_REQUIRED")
        duration = _bounded_number(
            duration_sec,
            error_code="INVALID_TRANSITION_DURATION",
            minimum=0,
            maximum=MAX_TRANSITION_DURATION_SEC,
        )
        if duration > min(from_item.duration_sec, to_item.duration_sec):
            raise VideoEditingError("TRANSITION_DURATION_EXCEEDS_CLIP")
        transition = Transition(from_clip, to_clip, transition_type, duration, reason.strip())
        return self._commit(transitions=(*self.transitions, transition))

    def set_audio_mix(self, clip_id: str, mix: AudioMix) -> "Timeline":
        self.validate()
        if not isinstance(mix, AudioMix):
            raise VideoEditingError("INVALID_AUDIO_MIX")
        track, clip = self._find_clip(clip_id)
        mix.validate(duration_sec=clip.duration_sec)
        return self._replace_clip(track, replace(clip, audio_mix=mix))

    def move_audio_clip(self, clip_id: str, *, timeline_start: float) -> "Timeline":
        """Move one manually positioned audio-track clip without changing its source range."""
        self.validate()
        track, clip = self._find_clip(clip_id)
        if track.kind == "video":
            raise VideoEditingError("MOVE_AUDIO_CLIP_AUDIO_TRACK_ONLY")
        start = _bounded_number(
            timeline_start,
            error_code="INVALID_CLIP_RANGE",
            minimum=0,
            maximum=MAX_EDIT_TIME_SEC,
        )
        if start + clip.duration_sec > MAX_EDIT_TIME_SEC:
            raise VideoEditingError("TIMELINE_DURATION_OUT_OF_RANGE")
        return self._replace_clip(track, replace(clip, timeline_start=start))

    def add_caption(self, start_sec: float, end_sec: float, text: str) -> "Timeline":
        return self._add_overlay("caption", start_sec, end_sec, text)

    def add_text_overlay(self, start_sec: float, end_sec: float, text: str) -> "Timeline":
        return self._add_overlay("text", start_sec, end_sec, text)

    def _add_overlay(self, kind: str, start_sec: float, end_sec: float, text: str) -> "Timeline":
        self.validate()
        start = _bounded_number(
            start_sec, error_code="INVALID_TIMED_OVERLAY", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        end = _bounded_number(
            end_sec, error_code="INVALID_TIMED_OVERLAY", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        if end <= start or not str(text).strip():
            raise VideoEditingError("INVALID_TIMED_OVERLAY")
        overlay = TimedOverlay(_id("OVERLAY"), kind, start, end, str(text).strip())
        return self._commit(overlays=(*self.overlays, overlay))

    def set_format(self, format_ratio: str) -> "Timeline":
        if format_ratio not in ALLOWED_FORMAT_RATIOS:
            raise VideoEditingError("FORMAT_RATIO_NOT_SUPPORTED")
        return self._commit(format_ratio=format_ratio)

    def undo(self) -> "Timeline":
        if not self._history:
            raise VideoEditingError("TIMELINE_NO_UNDO")
        snapshot = self._history[-1]
        return replace(
            self,
            tracks=snapshot.tracks,
            transitions=snapshot.transitions,
            overlays=snapshot.overlays,
            format_ratio=snapshot.format_ratio,
            version=self.version + 1,
            _history=self._history[:-1],
        )

    def to_export_request(self) -> Dict[str, Any]:
        self.validate()
        blockers = [
            "TIMELINE_RENDER_ADAPTER_UNAVAILABLE",
            "CANONICAL_EVIDENCE_BINDING_UNAVAILABLE",
            "CANONICAL_PERMISSION_APPROVAL_NOT_CONNECTED",
        ]
        return {
            "status": "blocked",
            "artifact_owner": "shared_artifacts.render_local_video_artifact",
            "artifact_integration": "unavailable_for_edited_timeline",
            "blockers": blockers,
            "approval_required": True,
            "external_fetch": False,
            "format_ratio": self.format_ratio,
            "timeline_version": self.version,
        }

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "version": self.version,
            "format_ratio": self.format_ratio,
            "assets": [asset.to_dict() for asset in self.assets],
            "tracks": [track.to_dict() for track in self.tracks],
            "transitions": [item.to_dict() for item in self.transitions],
            "overlays": [item.to_dict() for item in self.overlays],
            "approval_required": True,
        }


@dataclass(frozen=True)
class EditDecision:
    source_clip_ref: str
    in_sec: Optional[float]
    out_sec: Optional[float]
    operation: str
    reason: str
    confidence: float
    narrative_beat: str
    affected_audio: Tuple[str, ...] = field(default_factory=tuple)
    affected_text: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.operation, str) or self.operation not in ALLOWED_OPERATIONS:
            raise VideoEditingError("EDL_OPERATION_NOT_ALLOWED")
        if (
            not isinstance(self.source_clip_ref, str)
            or not self.source_clip_ref.strip()
            or not isinstance(self.reason, str)
            or not self.reason.strip()
            or not isinstance(self.narrative_beat, str)
            or not self.narrative_beat.strip()
        ):
            raise VideoEditingError("EDL_REQUIRES_SOURCE_REASON_AND_NARRATIVE_BEAT")
        _bounded_number(
            self.confidence, error_code="EDL_CONFIDENCE_MUST_BE_0_TO_1", minimum=0, maximum=1
        )
        in_sec = None if self.in_sec is None else _bounded_number(
            self.in_sec, error_code="EDL_TIME_OUT_OF_RANGE", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        out_sec = None if self.out_sec is None else _bounded_number(
            self.out_sec, error_code="EDL_TIME_OUT_OF_RANGE", minimum=0, maximum=MAX_EDIT_TIME_SEC
        )
        if out_sec is not None and in_sec is not None and out_sec <= in_sec:
            raise VideoEditingError("EDL_OUT_MUST_FOLLOW_IN")
        if self.operation == "trim" and (in_sec is None or out_sec is None):
            raise VideoEditingError("EDL_TRIM_REQUIRES_IN_AND_OUT")
        if self.operation == "split" and in_sec is None:
            raise VideoEditingError("EDL_SPLIT_REQUIRES_IN")
        if not isinstance(self.metadata, Mapping):
            raise VideoEditingError("EDL_METADATA_NOT_JSON_SAFE")
        metadata = _json_safe_copy(self.metadata)
        if self.operation == "reorder":
            new_index = metadata.get("new_index")
            if type(new_index) is not int or not 0 <= new_index <= MAX_SERIALIZED_INTEGER:
                raise VideoEditingError("EDL_REORDER_INDEX_INVALID")
        if self.operation == "delete" and "ripple" in metadata and type(metadata["ripple"]) is not bool:
            raise VideoEditingError("EDL_DELETE_RIPPLE_INVALID")
        if self.operation == "transition":
            duration = _bounded_number(
                metadata.get("duration_sec", 0.3),
                error_code="INVALID_TRANSITION_DURATION",
                minimum=0,
                maximum=MAX_TRANSITION_DURATION_SEC,
            )
            if duration <= 0 or not str(metadata.get("to_clip") or "").strip():
                raise VideoEditingError("EDL_TRANSITION_METADATA_INVALID")
        for values in (self.affected_audio, self.affected_text):
            if not isinstance(values, tuple) or any(not isinstance(value, str) for value in values):
                raise VideoEditingError("EDL_AFFECTED_FIELDS_INVALID")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "source_clip_ref": self.source_clip_ref,
            "in_sec": self.in_sec,
            "out_sec": self.out_sec,
            "operation": self.operation,
            "reason": self.reason,
            "confidence": self.confidence,
            "affected_narrative_beat": self.narrative_beat,
            "affected_audio": list(self.affected_audio),
            "affected_text": list(self.affected_text),
            "metadata": _json_safe_copy(self.metadata),
        }


@dataclass(frozen=True)
class EditDecisionList:
    candidate_id: str
    source_evidence_refs: Tuple[str, ...]
    decisions: Tuple[EditDecision, ...]
    status: str = "candidate"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise VideoEditingError("EDL_CANDIDATE_ID_REQUIRED")
        if not isinstance(self.source_evidence_refs, tuple) or not isinstance(self.decisions, tuple):
            raise VideoEditingError("EDL_CANDIDATE_SHAPE_INVALID")
        if self.source_evidence_refs:
            raise VideoEditingError("CANONICAL_EVIDENCE_BINDING_UNAVAILABLE")
        if not self.decisions:
            raise VideoEditingError("EDL_REQUIRES_DECISIONS")
        for decision in self.decisions:
            if not isinstance(decision, EditDecision):
                raise VideoEditingError("EDL_CANDIDATE_SHAPE_INVALID")
            decision.validate()

    def review(self, *, reviewer: str, approved: bool, reviewed_at: str) -> "EditDecisionList":
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise VideoEditingError("EDL_HUMAN_REVIEWER_REQUIRED")
        raise VideoEditingError("CANONICAL_EDL_APPROVAL_NOT_CONNECTED")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        if self.status != "candidate" or self.reviewed_by is not None or self.reviewed_at is not None:
            raise VideoEditingError("EDL_APPROVAL_STATE_NOT_TRUSTED")
        return {
            "candidate_id": self.candidate_id,
            "source_evidence_refs": list(self.source_evidence_refs),
            "decisions": [decision.to_dict() for decision in self.decisions],
            "status": "candidate",
            "reviewed_by": None,
            "reviewed_at": None,
            "approval_required": True,
            "canonical_evidence_binding": "unavailable",
            "ai_is_derivative": True,
        }


def propose_edl(source_evidence_refs: Iterable[str], decisions: Iterable[EditDecision]) -> EditDecisionList:
    refs = tuple(str(ref).strip() for ref in source_evidence_refs if str(ref).strip())
    if refs:
        raise VideoEditingError("CANONICAL_EVIDENCE_BINDING_UNAVAILABLE")
    candidate = EditDecisionList(_id("EDL"), (), tuple(decisions))
    candidate.validate()
    return candidate


def apply_edl_suggestion(timeline: Timeline, edl: EditDecisionList) -> Timeline:
    """Fail closed until canonical Evidence and Permission approve EDL application."""
    timeline.validate()
    edl.validate()
    raise VideoEditingError("CANONICAL_EDL_PERMISSION_APPROVAL_NOT_CONNECTED")


__all__ = [
    "ALLOWED_FORMAT_RATIOS",
    "AudioMix",
    "EditDecision",
    "EditDecisionList",
    "MediaAsset",
    "Timeline",
    "TimelineClip",
    "TimelineTrack",
    "VideoEditingError",
    "apply_edl_suggestion",
    "fingerprint_local_media",
    "propose_edl",
]
