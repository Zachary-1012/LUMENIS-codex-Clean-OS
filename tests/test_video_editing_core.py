from __future__ import annotations

from dataclasses import replace
import json
import math

import pytest

from lumenis.shared.content_creation import video_editing
from lumenis.shared.content_creation.video_editing import (
    AudioMix,
    EditDecision,
    MediaAsset,
    Timeline,
    TimelineClip,
    TimelineTrack,
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
    command = calls[0][0]
    assert command[command.index("-protocol_whitelist") + 1] == "file"
    assert command[command.index("-i") + 1] == str(source.resolve())
    assert command.index("-protocol_whitelist") < command.index("-i")
    assert command[command.index("-format_whitelist") + 1] == video_editing.MEDIA_INPUT_DEMUXERS
    assert command.index("-format_whitelist") < command.index("-i")
    assert {"concat", "hls", "dash"}.isdisjoint(video_editing.MEDIA_INPUT_DEMUXERS.split(","))


@pytest.mark.parametrize("network_path", ["//server/share/source.mp4", r"\\server\share\source.mp4"])
def test_fingerprint_rejects_unc_paths_before_probe(network_path, monkeypatch):
    monkeypatch.setattr(
        video_editing, "_probe_media_info",
        lambda _path: pytest.fail("network path reached FFprobe"),
    )
    with pytest.raises(VideoEditingError, match="LOCAL_MEDIA_ONLY"):
        fingerprint_local_media(network_path)


def test_audio_only_timeline_supports_trim_split_position_and_gain(tmp_path, monkeypatch):
    source = tmp_path / "music.wav"
    source.write_bytes(b"audio-only timeline source")
    monkeypatch.setattr(
        video_editing, "_probe_media_info",
        lambda path: video_editing._MediaProbe(
            20.0, str(path).endswith(".mp4"), 1
        ),
    )
    asset = fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,)).add_audio_track("music", audio_role="bgm")
    timeline = timeline.add_clip(
        asset.asset_id, source_in=0.0, source_out=12.0, track_id="music", timeline_start=3.0,
    )
    original = timeline.tracks[1].clips[0]
    timeline = timeline.trim(original.clip_id, source_in=1.0, source_out=9.0)
    timeline = timeline.set_audio_mix(
        original.clip_id, AudioMix(volume=0.35, fade_in_sec=2.0, fade_out_sec=3.0)
    )
    timeline = timeline.split(original.clip_id, at_sec=5.0)
    first, last = timeline.tracks[1].clips
    assert len(timeline.tracks[0].clips) == 0
    assert (first.source_in, first.source_out, first.timeline_start) == (1.0, 5.0, 3.0)
    assert (last.source_in, last.source_out, last.timeline_start) == (5.0, 9.0, 7.0)
    assert first.audio_mix.fade_in_sec == 2.0
    assert first.audio_mix.fade_out_sec == 0.0
    assert last.audio_mix.fade_in_sec == 0.0
    assert last.audio_mix.fade_out_sec == 3.0
    assert first.audio_mix.volume == last.audio_mix.volume == 0.35

    moved = timeline.move_audio_clip(last.clip_id, timeline_start=11.0)
    moved_last = moved.tracks[1].clips[1]
    assert moved_last.timeline_start == 11.0
    assert (moved_last.source_in, moved_last.source_out) == (5.0, 9.0)
    assert moved.to_export_request()["status"] == "blocked"
    assert moved.undo().tracks == timeline.tracks

    document = json.loads(json.dumps(moved.to_dict(), allow_nan=False))
    tracks = tuple(
        TimelineTrack(
            track_id=track["track_id"], kind=track["kind"],
            clips=tuple(
                TimelineClip(**{
                    **clip, "audio_mix": AudioMix(**clip["audio_mix"]),
                    "evidence_refs": tuple(clip["evidence_refs"]),
                }) for clip in track["clips"]
            ),
        ) for track in document["tracks"]
    )
    reconstructed = Timeline(
        assets=(fingerprint_local_media(str(source)),), tracks=tracks,
        version=document["version"], format_ratio=document["format_ratio"],
    )
    assert reconstructed.to_dict() == document

    video_source = tmp_path / "video.mp4"
    video_source.write_bytes(b"video clip source")
    video_asset = fingerprint_local_media(str(video_source))
    video_timeline = Timeline.from_assets((video_asset,)).add_clip(video_asset.asset_id)
    with pytest.raises(VideoEditingError, match="MOVE_AUDIO_CLIP_AUDIO_TRACK_ONLY"):
        video_timeline.move_audio_clip(video_timeline.tracks[0].clips[0].clip_id, timeline_start=1.0)


def test_uploaded_audio_is_a_fingerprinted_asset_and_can_be_positioned_on_manual_track(tmp_path, monkeypatch):
    source = tmp_path / "music.wav"
    source.write_bytes(b"user-selected local music bytes")

    class ProbeResult:
        stdout = '{"streams":[{"codec_type":"audio","duration":"18.5"}],"format":{"duration":"18.5"}}'

    monkeypatch.setattr(video_editing, "_ffprobe_path", lambda: "ffprobe-test")
    monkeypatch.setattr(video_editing.subprocess, "run", lambda *args, **kwargs: ProbeResult())
    asset = fingerprint_local_media(str(source))

    assert asset.media_kind == "audio"
    assert asset.has_video is False
    assert asset.audio_stream_count == 1
    assert asset.rights_status == "unknown"
    assert str(source) not in str(asset.to_dict())

    timeline = Timeline.from_assets((asset,)).add_audio_track("music", audio_role="bgm")
    timeline = timeline.add_clip(
        asset.asset_id,
        source_in=2.0,
        source_out=12.0,
        track_id="music",
        timeline_start=4.5,
    )
    clip = timeline.tracks[1].clips[0]
    assert clip.timeline_start == 4.5
    assert clip.audio_role == "bgm"
    assert clip.audio_stream_index == 0
    assert timeline.to_export_request()["status"] == "blocked"
    with pytest.raises(VideoEditingError, match="VIDEO_TRACK_REQUIRES_VIDEO_ASSET"):
        Timeline.from_assets((asset,)).add_clip(asset.asset_id)


def test_multitrack_source_requires_explicit_audio_stream_selection(tmp_path, monkeypatch):
    source = tmp_path / "multitrack.mp4"
    source.write_bytes(b"user-selected local multitrack media bytes")

    class ProbeResult:
        stdout = (
            '{"streams":['
            '{"codec_type":"video","duration":"10"},'
            '{"codec_type":"audio","duration":"10"},'
            '{"codec_type":"audio","duration":"10"}],'
            '"format":{"duration":"10"}}'
        )

    monkeypatch.setattr(video_editing, "_ffprobe_path", lambda: "ffprobe-test")
    monkeypatch.setattr(video_editing.subprocess, "run", lambda *args, **kwargs: ProbeResult())
    asset = fingerprint_local_media(str(source))
    assert asset.media_kind == "video_audio"
    assert asset.audio_stream_count == 2

    timeline = Timeline.from_assets((asset,))
    with pytest.raises(VideoEditingError, match="MULTIPLE_SOURCE_AUDIO_TRACKS_REQUIRE_EXPLICIT_SELECTION"):
        timeline.add_clip(asset.asset_id)

    timeline = timeline.add_clip(asset.asset_id, audio_role="muted")
    timeline = timeline.add_audio_track("voice", audio_role="voiceover")
    with pytest.raises(VideoEditingError, match="MULTIPLE_SOURCE_AUDIO_TRACKS_REQUIRE_EXPLICIT_SELECTION"):
        timeline.add_clip(asset.asset_id, track_id="voice", timeline_start=2.0)
    timeline = timeline.add_clip(
        asset.asset_id,
        track_id="voice",
        timeline_start=2.0,
        audio_stream_index=1,
    )
    voice_clip = timeline.tracks[1].clips[0]
    assert voice_clip.audio_stream_index == 1
    assert voice_clip.audio_role == "voiceover"


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
    monkeypatch.setattr(
        video_editing, "_probe_media_info",
        lambda _path: video_editing._MediaProbe(10.0, True, 1),
    )
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
    monkeypatch.setattr(
        video_editing, "_probe_media_info",
        lambda _path: video_editing._MediaProbe(10.0, True, 1),
    )
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
    monkeypatch.setattr(
        video_editing, "_probe_media_info",
        lambda _path: video_editing._MediaProbe(10.0, True, 1),
    )
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
    with pytest.raises(VideoEditingError, match="INVALID_AUDIO_MIX"):
        AudioMix(fade_in_sec=0.8, fade_out_sec=0.8).validate(duration_sec=1.0)
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


@pytest.mark.parametrize("bad_index", [-1, True, 2, "0"])
def test_audio_stream_selection_rejects_invalid_indices(tmp_path, monkeypatch, bad_index):
    source = tmp_path / "multitrack.mp4"
    source.write_bytes(b"scoped media stream selection")
    monkeypatch.setattr(video_editing, "_probe_media_info", lambda path: video_editing._MediaProbe(10, True, 2))
    asset = fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,)).add_audio_track("voice", audio_role="voiceover")
    with pytest.raises(VideoEditingError, match="AUDIO_STREAM_INDEX_OUT_OF_RANGE"):
        timeline.add_clip(asset.asset_id, track_id="voice", audio_stream_index=bad_index)


def test_muted_video_cannot_restore_selected_audio_stream(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"muted source")
    monkeypatch.setattr(video_editing, "_probe_media_info", lambda path: video_editing._MediaProbe(10, True, 1))
    asset = fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,)).add_clip(asset.asset_id, audio_role="muted")
    track = timeline.tracks[0]
    selected = replace(track.clips[0], audio_stream_index=0)
    with pytest.raises(VideoEditingError, match="MUTED_VIDEO_CLIP_CANNOT_SELECT_AUDIO"):
        replace(timeline, tracks=(replace(track, clips=(selected,)),))


@pytest.mark.parametrize("payload", ['{}', '{"streams":{}}', '{"streams":[]}', '{"streams":[{"codec_type":"subtitle"}]}'])
def test_probe_without_audio_or_video_inventory_is_not_a_media_asset(tmp_path, monkeypatch, payload):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"invalid media inventory")
    monkeypatch.setattr(video_editing, "_ffprobe_path", lambda: "ffprobe-test")
    monkeypatch.setattr(video_editing.subprocess, "run", lambda *args, **kwargs: type("Probe", (), {"stdout": payload})())
    with pytest.raises(VideoEditingError, match="MEDIA_DURATION_PROBE_FAILED|LOCAL_MEDIA_HAS_NO_AUDIO_OR_VIDEO_STREAM"):
        fingerprint_local_media(str(source))


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
