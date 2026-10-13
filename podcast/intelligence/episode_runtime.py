"""Deterministic episode-runtime primitives.

Keeps playback/runtime facts separate from AI interpretation. Consumers can
attach transcript, story and evidence adapters without changing this contract.
"""
from __future__ import annotations

import json
import hashlib
import math
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from lumenis.shared.content_creation.video_editing import (
    MAX_EDIT_TIME_SEC,
    MediaAsset,
    Timeline,
)


class SegmentKind(str, Enum):
    OPENING = "opening"
    STORY = "story"
    CONFLICT = "conflict"
    QUESTION = "question"
    INSIGHT = "insight"
    EMOTION = "emotion"
    QUOTE = "quote"
    TRANSITION = "transition"
    ENDING = "ending"


@dataclass(frozen=True)
class RuntimeSegment:
    segment_id: str
    start_ms: int
    end_ms: int
    kind: SegmentKind
    speaker_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("segment time range is invalid")

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


def validate_segments(segments: list[RuntimeSegment]) -> None:
    """Reject overlapping segments only when they are exact same-layer nodes.

    Different semantic layers may intentionally overlap (e.g. EMOTION inside
    STORY), so callers should provide one semantic layer per validation pass.
    """
    ordered = sorted(segments, key=lambda s: (s.start_ms, s.end_ms))
    for previous, current in zip(ordered, ordered[1:]):
        if current.start_ms < previous.end_ms:
            raise ValueError(
                f"overlapping runtime segments: {previous.segment_id} / {current.segment_id}"
            )


def _required_text(value: Any, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field_name} must be non-empty text")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field_name} must contain valid Unicode") from exc
    return value


def _finite_time(value: Any, field_name: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{field_name} must be a finite number")
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number") from exc
    if not math.isfinite(number) or not 0 <= number <= MAX_EDIT_TIME_SEC:
        raise ValueError(f"{field_name} is outside the supported time range")
    return number


def _json_object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {value}")


def _timecode(seconds: float) -> str:
    milliseconds = math.floor(seconds * 1000 + 0.5)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{millis:03d}"


@dataclass(frozen=True)
class PodcastSegment:
    """One reviewed transcript slice mapped to a source-media range.

    Evidence references are opaque IDs only. This class does not validate or
    promote Evidence, and retains original and corrected text independently.
    """

    segment_id: str
    media_asset_id: str
    source_in: float
    source_out: float
    original_text: str
    corrected_text: str
    speaker: str
    chapter_title: str
    evidence_refs: tuple[str, ...] = ()
    audio_stream_index: int | None = None

    def __post_init__(self) -> None:
        for field_name in ("segment_id", "media_asset_id", "speaker", "chapter_title", "original_text", "corrected_text"):
            _required_text(getattr(self, field_name), field_name)
        source_in = _finite_time(self.source_in, "source_in")
        source_out = _finite_time(self.source_out, "source_out")
        if source_out <= source_in:
            raise ValueError("source_out must be greater than source_in")
        object.__setattr__(self, "source_in", source_in)
        object.__setattr__(self, "source_out", source_out)
        if type(self.evidence_refs) is not tuple:
            raise ValueError("evidence_refs must be a tuple of reference IDs")
        for reference in self.evidence_refs:
            _required_text(reference, "evidence_refs item")
        if self.audio_stream_index is not None and (
            type(self.audio_stream_index) is not int or self.audio_stream_index < 0
        ):
            raise ValueError("audio_stream_index must be a non-negative exact integer")

    @property
    def duration(self) -> float:
        return self.source_out - self.source_in

    def to_dict(self) -> dict[str, Any]:
        result = {
            "segment_id": self.segment_id,
            "media_asset_id": self.media_asset_id,
            "source_in": self.source_in,
            "source_out": self.source_out,
            "original_text": self.original_text,
            "corrected_text": self.corrected_text,
            "speaker": self.speaker,
            "chapter_title": self.chapter_title,
            "evidence_refs": list(self.evidence_refs),
        }
        if self.audio_stream_index is not None:
            result["audio_stream_index"] = self.audio_stream_index
        return result

    @classmethod
    def from_dict(cls, payload: Any) -> "PodcastSegment":
        fields = {
            "segment_id", "media_asset_id", "source_in", "source_out",
            "original_text", "corrected_text", "speaker", "chapter_title", "evidence_refs",
        }
        if type(payload) is not dict or set(payload) not in (fields, fields | {"audio_stream_index"}):
            raise ValueError("Podcast segment fields are invalid")
        refs = payload["evidence_refs"]
        if type(refs) is not list:
            raise ValueError("evidence_refs must be a JSON array")
        return cls(
            segment_id=payload["segment_id"],
            media_asset_id=payload["media_asset_id"],
            source_in=payload["source_in"],
            source_out=payload["source_out"],
            original_text=payload["original_text"],
            corrected_text=payload["corrected_text"],
            speaker=payload["speaker"],
            chapter_title=payload["chapter_title"],
            evidence_refs=tuple(refs),
            audio_stream_index=payload.get("audio_stream_index"),
        )


@dataclass(frozen=True)
class PodcastPlan:
    """Validated, ordered Podcast edit intent backed by the Shared Timeline."""

    title: str
    description: str
    language: str
    segments: tuple[PodcastSegment, ...]
    revision: int = 1

    def __post_init__(self) -> None:
        for field_name in ("title", "description", "language"):
            _required_text(getattr(self, field_name), field_name)
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("revision must be a positive exact integer")
        if type(self.segments) is not tuple or not self.segments:
            raise ValueError("segments must be a non-empty tuple")
        if len(self.segments) > 512:
            raise ValueError("Podcast plans are limited to 512 segments")
        if any(not isinstance(segment, PodcastSegment) for segment in self.segments):
            raise ValueError("segments must contain PodcastSegment values")
        segment_ids = [segment.segment_id for segment in self.segments]
        if len(set(segment_ids)) != len(segment_ids):
            raise ValueError("segment_id values must be unique")
        try:
            total_duration = math.fsum(segment.duration for segment in self.segments)
        except (OverflowError, ValueError) as exc:
            raise ValueError("plan duration is invalid") from exc
        if not math.isfinite(total_duration) or total_duration > MAX_EDIT_TIME_SEC:
            raise ValueError("plan duration exceeds the supported timeline range")
        text_size = len(self.title) + len(self.description) + len(self.language)
        for segment in self.segments:
            text_size += sum(len(value) for value in (
                segment.segment_id, segment.media_asset_id, segment.original_text,
                segment.corrected_text, segment.speaker, segment.chapter_title,
            ))
            text_size += sum(len(reference) for reference in segment.evidence_refs)
        if text_size > 200_000:
            raise ValueError("Podcast plan text exceeds 200000 characters")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 2 if any(segment.audio_stream_index is not None for segment in self.segments) else 1,
            "title": self.title,
            "description": self.description,
            "language": self.language,
            "revision": self.revision,
            "segments": [segment.to_dict() for segment in self.segments],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, allow_nan=False)

    def content_digest(self) -> str:
        """Return a deterministic digest of this plan's serialized content."""
        canonical = json.dumps(
            self.to_dict(), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def _check_edit_base(self, expected_revision: int, expected_digest: str) -> None:
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError("expected_revision must be a positive exact integer")
        if type(expected_digest) is not str or not expected_digest:
            raise ValueError("expected_digest must be non-empty text")
        if expected_revision != self.revision or expected_digest != self.content_digest():
            raise ValueError("stale podcast plan revision or digest")

    def with_transcript_corrections(
        self,
        corrections: dict[str, str],
        *,
        expected_revision: int,
        expected_digest: str,
    ) -> "PodcastPlan":
        """Return a corrected-text revision without changing source transcript facts."""
        self._check_edit_base(expected_revision, expected_digest)
        if type(corrections) is not dict:
            raise ValueError("corrections must be a dict")
        by_id = {segment.segment_id: segment for segment in self.segments}
        for segment_id, text in corrections.items():
            if type(segment_id) is not str or segment_id not in by_id:
                raise ValueError("corrections contain an unknown segment ID")
            _required_text(text, "correction text")
        updated = tuple(
            replace(segment, corrected_text=corrections[segment.segment_id])
            if segment.segment_id in corrections and corrections[segment.segment_id] != segment.corrected_text
            else segment
            for segment in self.segments
        )
        if updated == self.segments:
            return self
        return replace(self, segments=updated, revision=self.revision + 1)

    def reordered_segments(
        self,
        segment_ids: tuple[str, ...],
        *,
        expected_revision: int,
        expected_digest: str,
    ) -> "PodcastPlan":
        """Return a new plan ordering while preserving every original segment."""
        self._check_edit_base(expected_revision, expected_digest)
        if type(segment_ids) is not tuple:
            raise ValueError("segment_ids must be a tuple")
        if any(type(segment_id) is not str for segment_id in segment_ids):
            raise ValueError("segment_ids must contain text IDs")
        current = {segment.segment_id: segment for segment in self.segments}
        if len(segment_ids) != len(self.segments):
            raise ValueError("segment_ids must include every segment exactly once")
        if len(set(segment_ids)) != len(segment_ids):
            raise ValueError("segment_ids must not contain duplicates")
        if set(segment_ids) != set(current):
            raise ValueError("segment_ids contain unknown or missing IDs")
        ordered = tuple(current[segment_id] for segment_id in segment_ids)
        if ordered == self.segments:
            return self
        return replace(self, segments=ordered, revision=self.revision + 1)

    @classmethod
    def from_dict(cls, payload: Any) -> "PodcastPlan":
        fields = {"version", "title", "description", "language", "revision", "segments"}
        if type(payload) is not dict or set(payload) != fields:
            raise ValueError("Podcast plan fields are invalid")
        if type(payload["version"]) is not int or payload["version"] not in {1, 2}:
            raise ValueError("Podcast plan version is unsupported")
        if type(payload["segments"]) is not list:
            raise ValueError("segments must be a JSON array")
        if not 1 <= len(payload["segments"]) <= 512:
            raise ValueError("Podcast plans require one to 512 segments")
        if payload["version"] == 1 and any(
            isinstance(item, dict) and "audio_stream_index" in item for item in payload["segments"]
        ):
            raise ValueError("Explicit audio stream selection requires Podcast plan version 2")
        return cls(
            title=payload["title"],
            description=payload["description"],
            language=payload["language"],
            revision=payload["revision"],
            segments=tuple(PodcastSegment.from_dict(item) for item in payload["segments"]),
        )

    @classmethod
    def from_json(cls, document: str) -> "PodcastPlan":
        if type(document) is not str:
            raise ValueError("Podcast plan JSON must be text")
        # Bound parser work before the structured text/segment limits apply.
        if len(document) > 1_600_000:
            raise ValueError("Podcast plan JSON exceeds the input limit")
        try:
            payload = json.loads(
                document,
                object_pairs_hook=_json_object_without_duplicate_keys,
                parse_constant=_reject_json_constant,
            )
        except (json.JSONDecodeError, TypeError, RecursionError) as exc:
            raise ValueError("Podcast plan JSON is invalid") from exc
        return cls.from_dict(payload)

    def with_segment_source(
        self, segment_id: str, *, asset: MediaAsset, source_in: float, source_out: float,
        new_source_text: str, new_source_speaker: str, audio_stream_index: int | None = None,
        expected_revision: int, expected_digest: str,
    ) -> "PodcastPlan":
        """Adopt an explicit new utterance and range without truncating its words.

        New-source text and speaker are supplied authoring intent, not ASR or
        identity proof. The prior plan retains the old source and corrections.
        Chapters and both transcript views use the revised ordered durations.
        The caller retains the permitted old and new media for rebuild/rollback.
        """
        self._check_edit_base(expected_revision, expected_digest)
        target = next((item for item in self.segments if item.segment_id == segment_id), None)
        if target is None:
            raise ValueError("source replacement contains an unknown segment ID")
        if not isinstance(asset, MediaAsset):
            raise ValueError("source replacement requires fingerprinted media")
        asset.validate()
        start = _finite_time(source_in, "source_in")
        end = _finite_time(source_out, "source_out")
        if start >= end or end > asset.duration_sec:
            raise ValueError("source replacement range is outside media")
        if asset.audio_stream_count < 1:
            raise ValueError("source replacement media has no audio stream")
        if audio_stream_index is None:
            if asset.audio_stream_count > 1:
                raise ValueError("source replacement requires an explicit audio stream")
            audio_stream_index = 0
        if type(audio_stream_index) is not int or not 0 <= audio_stream_index < asset.audio_stream_count:
            raise ValueError("source replacement audio stream is out of range")
        text = _required_text(new_source_text, "new_source_text")
        speaker = _required_text(new_source_speaker, "new_source_speaker")
        replacement = replace(target, media_asset_id=asset.asset_id, source_in=start, source_out=end,
                              original_text=text, corrected_text=text, speaker=speaker,
                              evidence_refs=asset.evidence_refs, audio_stream_index=audio_stream_index)
        if replacement == target:
            return self
        return replace(self, revision=self.revision + 1,
                       segments=tuple(replacement if item.segment_id == segment_id else item for item in self.segments))

    def _output_segments(self) -> tuple[tuple[PodcastSegment, float, float], ...]:
        result = []
        cursor = 0.0
        for segment in self.segments:
            # Match Shared TimelineClip's six-decimal duration and boundaries.
            end = round(cursor + round(segment.duration, 6), 6)
            result.append((segment, cursor, end))
            cursor = end
        return tuple(result)

    def voice_track_labels(self) -> dict[str, str]:
        """Derive human labels for turn-based tracks; these are not separated stems."""
        speakers = dict.fromkeys(segment.speaker for segment in self.segments)
        return {f"podcast_voice_{index}": speaker for index, speaker in enumerate(speakers, 1)}

    def build_timeline(self, assets: tuple[MediaAsset, ...], *, separate_speakers: bool = False) -> Timeline:
        if type(separate_speakers) is not bool:
            raise ValueError("separate_speakers must be a boolean")
        if type(assets) is not tuple or not assets:
            raise ValueError("assets must be a non-empty tuple of fingerprinted media")
        assets_by_id: dict[str, MediaAsset] = {}
        for asset in assets:
            if not isinstance(asset, MediaAsset):
                raise ValueError("assets must contain fingerprinted MediaAsset values")
            asset.validate()
            if asset.asset_id in assets_by_id:
                raise ValueError("media asset IDs must be unique")
            assets_by_id[asset.asset_id] = asset
        for segment in self.segments:
            asset = assets_by_id.get(segment.media_asset_id)
            if asset is None:
                raise ValueError(f"media asset is missing for segment {segment.segment_id}")
            if asset.audio_stream_count == 0:
                raise ValueError(f"media asset has no audio stream for segment {segment.segment_id}")
            if asset.audio_stream_count > 1 and segment.audio_stream_index is None:
                raise ValueError(
                    f"media asset has multiple audio streams for segment {segment.segment_id}; explicit selection is required"
                )
            if segment.audio_stream_index is not None and segment.audio_stream_index >= asset.audio_stream_count:
                raise ValueError(f"audio stream selection is out of range for segment {segment.segment_id}")

        labels = self.voice_track_labels() if separate_speakers else {"podcast_voice": "Combined speaker turns"}
        speaker_tracks = {speaker: track_id for track_id, speaker in labels.items()}
        timeline = Timeline.from_assets(assets)
        for track_id in labels:
            timeline = timeline.add_audio_track(track_id, audio_role="voiceover")
        for segment, timeline_start, _ in self._output_segments():
            timeline = timeline.add_clip(
                segment.media_asset_id,
                source_in=segment.source_in,
                source_out=segment.source_out,
                track_id=speaker_tracks[segment.speaker] if separate_speakers else "podcast_voice",
                purpose=f"podcast-segment:{segment.segment_id}",
                audio_role="voiceover",
                timeline_start=timeline_start,
                audio_stream_index=segment.audio_stream_index if segment.audio_stream_index is not None else 0,
            )
        return timeline

    def chapter_document(self) -> dict[str, Any]:
        chapters: list[dict[str, Any]] = []
        for segment, start, end in self._output_segments():
            if chapters and chapters[-1]["title"] == segment.chapter_title and chapters[-1]["endTime"] == start:
                chapters[-1]["endTime"] = end
            else:
                chapters.append({
                    "startTime": start,
                    "title": segment.chapter_title,
                    "endTime": end,
                })
        return {"version": "1.2.0", "chapters": chapters}

    def script_text(self) -> str:
        lines = [self.title, self.description, ""]
        for segment, start, _ in self._output_segments():
            lines.append(f"[{_timecode(start)}] {segment.speaker} {segment.corrected_text}")
        return "\n".join(lines)

    def original_script_text(self) -> str:
        lines = [self.title, self.description, ""]
        for segment, start, _ in self._output_segments():
            lines.append(f"[{_timecode(start)}] {segment.speaker} {segment.original_text}")
        return "\n".join(lines)

    def _transcript_vtt(self, text_field: str) -> str:
        cues = ["WEBVTT", ""]
        for index, (segment, start, end) in enumerate(self._output_segments(), start=1):
            start_code, end_code = _timecode(start), _timecode(end)
            if start_code == end_code:
                raise ValueError("Podcast transcript cue is shorter than millisecond precision")
            # Escape markup while preserving the Unicode text as visible cue content.
            speaker = " ".join(segment.speaker.split())
            speaker = speaker.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            body = getattr(segment, text_field)
            body = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if "\x00" in speaker or "\x00" in body:
                raise ValueError("Podcast transcript contains a null character")
            # WebVTT uses physical line breaks, not HTML br elements. Keep
            # authored blank lines inside the cue using a visible-space entity.
            body = "\n".join(line if line.strip() else "&nbsp;" for line in
                             body.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
            cues.extend((
                str(index),
                f"{start_code} --> {end_code}",
                f"{speaker}: {body}",
                "",
            ))
        return "\n".join(cues)

    def transcript_vtt(self) -> str:
        return self._transcript_vtt("corrected_text")

    def original_transcript_vtt(self) -> str:
        return self._transcript_vtt("original_text")

    def editable_documents(self) -> dict[str, str]:
        """Build content members for the existing Artifact wrapper; persist nothing."""
        corrections = {
            "version": 1,
            "segments": [
                {
                    "segment_id": segment.segment_id,
                    "original_text": segment.original_text,
                    "corrected_text": segment.corrected_text,
                    "changed": segment.original_text != segment.corrected_text,
                    "media_asset_id": segment.media_asset_id,
                    "source_in": segment.source_in,
                    "source_out": segment.source_out,
                    "speaker": segment.speaker,
                    "chapter_title": segment.chapter_title,
                    "evidence_refs": list(segment.evidence_refs),
                }
                for segment in self.segments
            ],
        }
        metadata = {
            "original_text_semantics": (
                "Preserved plan source text; it does not automatically establish verified ASR."
            ),
            "transcript_edits_change_audio": False,
            "transcript_to_existing_audio_alignment": (
                "Not asserted by this plan; correcting a transcript to match an existing recording requires actual alignment review."
            ),
            "intended_spoken_content_and_audio_identity": (
                "Not asserted by this plan; a new intended wording or order requires matching recorded or generated media and an actual render before claiming a match."
            ),
            "human_listening_acceptance": "not_asserted_by_plan",
            "persistence_semantics": (
                "This builder only serializes content members and performs no persistence."
            ),
            "artifact_evidence_permission_binding": (
                "Not asserted by the plan; bind actual media identity, provenance, permission, review and artifact references through the existing external owners."
            ),
            "revision": self.revision,
            "content_digest": self.content_digest(),
        }
        return {
            "podcast-plan.json": json.dumps(self.to_dict(), ensure_ascii=False, indent=2, allow_nan=False),
            "script.txt": self.script_text(),
            "transcript-original.vtt": self.original_transcript_vtt(),
            "transcript-corrected.vtt": self.transcript_vtt(),
            "chapters.json": json.dumps(self.chapter_document(), ensure_ascii=False, indent=2, allow_nan=False),
            "corrections.json": json.dumps(corrections, ensure_ascii=False, indent=2, allow_nan=False),
            "metadata.json": json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False),
        }


__all__ = [
    "PodcastPlan",
    "PodcastSegment",
    "RuntimeSegment",
    "SegmentKind",
    "validate_segments",
]
