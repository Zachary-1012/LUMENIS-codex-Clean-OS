from __future__ import annotations

from dataclasses import replace
import math

import pytest

from lumenis.shared.content_creation import video_editing
from lumenis.shared.content_creation.video_editing import (
    AudioMix,
    EditDecision,
    MediaAsset,
    Timeline,
    TimelineClip,
    TimedOverlay,
    Transition,
    VideoEditingError,
    apply_edl_suggestion,
    fingerprint_local_media,
    propose_edl,
)


def test_fingerprint_uses_ffprobe_and_keeps_unverified_claims_empty(tmp_path, monkeypatch):
    source = tmp_path / "selected.mp4"
    source.write_bytes(b"explicit local media bytes")
    calls = []

    class ProbeResult:
        stdout = '{"streams":[{"codec_type":"video","duration":"4.25"}],"format":{"duration":"4.25"}}'

    monkeypatch.setattr(video_editing, "_ffprobe_path", lambda: "ffprobe-test")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return ProbeResult()

    monkeypatch.setattr(video_editing.subprocess, "run", fake_run)
    asset = fingerprint_local_media(str(source))

    assert asset.duration_sec == 4.25
    assert asset.evidence_refs == ()
    assert asset.rights_status == "unknown"
    assert str(source) not in str(asset.to_dict())
    assert calls[0][0][0] == "ffprobe-test"
    assert calls[0][1]["shell"] is False


def test_untrusted_duration_evidence_and_rights_claims_are_rejected(tmp_path, monkeypatch):
    source = tmp_path / "selected.mp4"
    source.write_bytes(b"explicit local media bytes")
    monkeypatch.setattr(video_editing, "_ffprobe_path", lambda: None)

    with pytest.raises(VideoEditingError, match="CALLER_SUPPLIED_MEDIA_DURATION_NOT_TRUSTED"):
        fingerprint_local_media(str(source), duration_sec=4.25)
    with pytest.raises(VideoEditingError, match="CANONICAL_EVIDENCE_BINDING_UNAVAILABLE"):
        fingerprint_local_media(str(source), evidence_refs=("invented-evidence",))
    with pytest.raises(VideoEditingError, match="RIGHTS_STATUS_REQUIRES_CANONICAL_REVIEW"):
        fingerprint_local_media(str(source), rights_status="verified")
    with pytest.raises(VideoEditingError, match="MEDIA_DURATION_PROBE_UNAVAILABLE"):
        fingerprint_local_media(str(source))
    with pytest.raises(VideoEditingError, match="MEDIA_ASSET_MUST_BE_FINGERPRINTED"):
        MediaAsset("MEDIA-fake", "selected.mp4", "f" * 64, 4.25, str(source))


def test_timeline_edits_remain_local_and_render_handoff_is_blocked(tmp_path, monkeypatch):
    source = tmp_path / "selected.mp4"
    source.write_bytes(b"explicit local media bytes")
    monkeypatch.setattr(video_editing, "_probe_media_duration", lambda _path: 10.0)
    asset = fingerprint_local_media(str(source))

    timeline = Timeline.from_assets((asset,)).add_clip(asset.asset_id, source_out=8.0)
    clip = timeline.tracks[0].clips[0]
    edited = timeline.trim(clip.clip_id, source_in=1.0, source_out=5.0)
    assert edited.tracks[0].clips[0].duration_sec == 4.0

    request = edited.to_export_request()
    assert request["status"] == "blocked"
    assert request["artifact_owner"] == "shared_artifacts.render_local_video_artifact"
    assert request["artifact_integration"] == "unavailable_for_edited_timeline"
    assert "TIMELINE_RENDER_ADAPTER_UNAVAILABLE" in request["blockers"]
    assert "CANONICAL_PERMISSION_APPROVAL_NOT_CONNECTED" in request["blockers"]


def test_edl_self_review_and_forged_approval_never_apply(tmp_path, monkeypatch):
    source = tmp_path / "selected.mp4"
    source.write_bytes(b"explicit local media bytes")
    monkeypatch.setattr(video_editing, "_probe_media_duration", lambda _path: 10.0)
    asset = fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,)).add_clip(asset.asset_id, source_out=8.0)
    clip = timeline.tracks[0].clips[0]
    edl = propose_edl(
        (),
        (EditDecision(clip.clip_id, 1.0, 5.0, "trim", "remove setup", 0.9, "hook"),),
    )

    with pytest.raises(VideoEditingError, match="CANONICAL_EDL_APPROVAL_NOT_CONNECTED"):
        edl.review(reviewer="self-asserted", approved=True, reviewed_at="2026-09-26T00:00:00Z")
    assert edl.to_dict()["status"] == "candidate"
    assert edl.to_dict()["reviewed_by"] is None
    forged = replace(edl, status="approved", reviewed_by="self-asserted", reviewed_at="2026-09-26T00:00:00Z")
    with pytest.raises(VideoEditingError, match="EDL_APPROVAL_STATE_NOT_TRUSTED"):
        forged.to_dict()
    forged = replace(edl)
    object.__setattr__(forged, "status", "approved")
    object.__setattr__(forged, "reviewed_by", "self-asserted")
    with pytest.raises(VideoEditingError, match="EDL_APPROVAL_STATE_NOT_TRUSTED"):
        forged.to_dict()
    with pytest.raises(VideoEditingError, match="CANONICAL_EDL_PERMISSION_APPROVAL_NOT_CONNECTED"):
        apply_edl_suggestion(timeline, forged)
    with pytest.raises(VideoEditingError, match="CANONICAL_EDL_PERMISSION_APPROVAL_NOT_CONNECTED"):
        apply_edl_suggestion(timeline, edl)
    with pytest.raises(VideoEditingError, match="CANONICAL_EVIDENCE_BINDING_UNAVAILABLE"):
        propose_edl(
            ("invented-evidence",),
            (EditDecision(clip.clip_id, 1.0, 5.0, "trim", "remove setup", 0.9, "hook"),),
        )


@pytest.mark.parametrize("bad_time", [math.nan, math.inf, -math.inf])
def test_timeline_rejects_nonfinite_times_on_edit_and_serialization(tmp_path, monkeypatch, bad_time):
    source = tmp_path / "selected.mp4"
    source.write_bytes(b"explicit local media bytes")
    monkeypatch.setattr(video_editing, "_probe_media_duration", lambda _path: 10.0)
    asset = fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,))

    with pytest.raises(VideoEditingError, match="CLIP_RANGE_OUTSIDE_MEDIA_ASSET"):
        timeline.add_clip(asset.asset_id, source_in=bad_time, source_out=2.0)
    timeline = timeline.add_clip(asset.asset_id, source_out=8.0)
    clip = timeline.tracks[0].clips[0]
    with pytest.raises(VideoEditingError, match="TRIM_RANGE_OUTSIDE_MEDIA_ASSET"):
        timeline.trim(clip.clip_id, source_in=0.0, source_out=bad_time)
    with pytest.raises(VideoEditingError, match="SPLIT_POINT_OUTSIDE_CLIP"):
        timeline.split(clip.clip_id, at_sec=bad_time)
    with pytest.raises(VideoEditingError, match="INVALID_TIMED_OVERLAY"):
        timeline.add_caption(bad_time, 1.0, "caption")
    with pytest.raises(VideoEditingError, match="INVALID_CLIP_RANGE"):
        TimelineClip("clip", asset.asset_id, 0.0, 1.0, bad_time)

    malformed = replace(timeline)
    object.__setattr__(malformed, "version", bad_time)
    with pytest.raises(VideoEditingError, match="TIMELINE_VERSION_INVALID"):
        malformed.to_dict()
    with pytest.raises(VideoEditingError, match="TIMELINE_VERSION_INVALID"):
        malformed.to_export_request()


@pytest.mark.parametrize("bad_number", [math.nan, math.inf, -math.inf])
def test_all_component_numeric_fields_reject_nonfinite_values(bad_number):
    with pytest.raises(VideoEditingError, match="INVALID_AUDIO_MIX"):
        AudioMix(fade_in_sec=bad_number)
    with pytest.raises(VideoEditingError, match="INVALID_AUDIO_MIX"):
        AudioMix(fade_out_sec=bad_number)
    with pytest.raises(VideoEditingError, match="INVALID_TRANSITION_DURATION"):
        Transition("from", "to", "dissolve", bad_number, "time moved")
    with pytest.raises(VideoEditingError, match="INVALID_TIMED_OVERLAY"):
        TimedOverlay("overlay", "caption", bad_number, 1.0, "caption")
    with pytest.raises(VideoEditingError, match="EDL_CONFIDENCE_MUST_BE_0_TO_1"):
        EditDecision("clip", 0.0, 1.0, "trim", "reason", bad_number, "beat")
    with pytest.raises(VideoEditingError, match="EDL_TIME_OUT_OF_RANGE"):
        EditDecision("clip", bad_number, 1.0, "trim", "reason", 0.5, "beat")
    with pytest.raises(VideoEditingError, match="EDL_TIME_OUT_OF_RANGE"):
        EditDecision("clip", 0.0, bad_number, "trim", "reason", 0.5, "beat")


def test_edl_serialization_revalidates_mutable_nested_metadata():
    metadata = {"review_note": "candidate only"}
    decision = EditDecision("clip", None, None, "hold", "preserve", 0.5, "breathing room", metadata=metadata)
    assert decision.to_dict()["metadata"] == {"review_note": "candidate only"}
    metadata["duration_sec"] = math.nan
    with pytest.raises(VideoEditingError, match="EDL_METADATA_NUMBER_INVALID"):
        decision.to_dict()


@pytest.mark.parametrize("bad_duration", ["NaN", "Infinity", "86401"])
def test_ffprobe_duration_must_be_finite_and_within_product_bound(tmp_path, monkeypatch, bad_duration):
    source = tmp_path / "selected.mp4"
    source.write_bytes(b"explicit local media bytes")

    class ProbeResult:
        stdout = '{"streams":[{"codec_type":"video","duration":"' + bad_duration + '"}]}'

    monkeypatch.setattr(video_editing, "_ffprobe_path", lambda: "ffprobe-test")
    monkeypatch.setattr(video_editing.subprocess, "run", lambda *args, **kwargs: ProbeResult())
    with pytest.raises(VideoEditingError, match="MEDIA_DURATION_PROBE_FAILED"):
        fingerprint_local_media(str(source))
