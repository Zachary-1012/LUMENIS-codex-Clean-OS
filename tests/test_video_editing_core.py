from __future__ import annotations

from dataclasses import replace
import json
from copy import deepcopy
import math
from pathlib import Path
import subprocess
import wave

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


def _write_short_stereo_wave(path: Path) -> None:
    with wave.open(str(path), "wb") as target:
        target.setnchannels(2)
        target.setsampwidth(2)
        target.setframerate(48_000)
        target.writeframes(bytes(4 * 4_800))


def test_actual_ffprobe_wav_stream_metadata_preserves_missing_start_pts_as_null(tmp_path):
    ffprobe = video_editing._ffprobe_path()
    if not ffprobe or not Path(ffprobe).is_file():
        pytest.skip("actual media metadata contract requires FFprobe")
    source = tmp_path / "short-stereo.wav"
    _write_short_stereo_wave(source)
    result = subprocess.run(
        [ffprobe, "-v", "error", "-protocol_whitelist", "file", "-format_whitelist", "wav",
         "-show_entries", "stream=index,codec_type,sample_rate,channels,time_base,start_pts,duration_ts",
         "-of", "json", "-i", str(source)],
        capture_output=True, text=True, timeout=15, check=True, shell=False,
    )
    reported = json.loads(result.stdout)["streams"][0]

    asset = fingerprint_local_media(str(source))
    assert len(asset.stream_metadata) == 1
    stream = asset.stream_metadata[0]
    assert stream.kind == "audio" and stream.type_relative_ordinal == 0
    assert stream.global_index == reported.get("index")
    assert stream.sample_rate == 48_000 and stream.channels == 2
    assert stream.time_base == reported.get("time_base")
    raw_duration_ts = reported.get("duration_ts")
    assert stream.duration_ts == (int(raw_duration_ts) if raw_duration_ts is not None else None)
    # FFprobe may omit an undefined field. Omission stays null; it is never
    # synthesized into a zero timestamp.
    raw_start_pts = reported.get("start_pts")
    expected_start_pts = int(raw_start_pts) if raw_start_pts is not None else None
    assert stream.start_pts == expected_start_pts
    if raw_start_pts is None:
        assert asset.to_dict()["stream_metadata"][0]["start_pts"] is None


@pytest.mark.parametrize(("field", "value"), [
    ("index", True), ("sample_rate", 48_000.0), ("channels", "stereo"),
    ("time_base", "0/0"), ("start_pts", 1.5), ("duration_ts", -1),
])
def test_probe_rejects_present_malformed_stream_metadata(tmp_path, monkeypatch, field, value):
    source = tmp_path / "malformed-stream.wav"
    source.write_bytes(b"probe payload is isolated by the test")
    stream = {
        "index": 0, "codec_type": "audio", "duration": "1.0",
        "sample_rate": "48000", "channels": 2, "time_base": "1/48000",
        "start_pts": "0", "duration_ts": "48000",
    }
    stream[field] = value
    payload = json.dumps({"streams": [stream], "format": {"duration": "1.0"}})
    monkeypatch.setattr(video_editing, "_ffprobe_path", lambda: "ffprobe-test")
    monkeypatch.setattr(
        video_editing.subprocess, "run",
        lambda *args, **kwargs: type("Probe", (), {"stdout": payload})(),
    )
    with pytest.raises(VideoEditingError, match="MEDIA_STREAM_METADATA_INVALID"):
        fingerprint_local_media(str(source))


def test_probe_retains_negative_start_pts_without_zero_or_seconds_conversion(tmp_path, monkeypatch):
    source = tmp_path / "negative-start.wav"
    source.write_bytes(b"probe payload is isolated by the test")
    payload = json.dumps({"streams": [{
        "index": 0, "codec_type": "audio", "duration": "1.0",
        "sample_rate": "48000", "channels": 2, "time_base": "1/48000",
        "start_pts": "-240", "duration_ts": "48000",
    }]})
    monkeypatch.setattr(video_editing, "_ffprobe_path", lambda: "ffprobe-test")
    monkeypatch.setattr(
        video_editing.subprocess, "run",
        lambda *args, **kwargs: type("Probe", (), {"stdout": payload})(),
    )
    asset = fingerprint_local_media(str(source))
    assert asset.stream_metadata[0].start_pts == -240
    assert asset.stream_metadata[0].time_base == "1/48000"


def test_tampered_verified_stream_metadata_is_rejected_on_timeline_reopen(tmp_path):
    ffprobe = video_editing._ffprobe_path()
    if not ffprobe or not Path(ffprobe).is_file():
        pytest.skip("actual media metadata contract requires FFprobe")
    source = tmp_path / "tamper-check.wav"
    _write_short_stereo_wave(source)
    asset = fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,)).add_audio_track("voice", audio_role="voiceover")
    timeline = timeline.add_clip(
        asset.asset_id, source_in=0.01, source_out=0.08, track_id="voice",
        timeline_start=0.2, audio_stream_index=0,
    )
    tampered = deepcopy(timeline.to_dict())
    stored_stream = tampered["assets"][0]["stream_metadata"][0]
    stored_stream["duration_ts"] = (stored_stream["duration_ts"] or 0) + 1
    with pytest.raises(VideoEditingError, match="TIMELINE_REOPEN_ASSET_MISMATCH"):
        Timeline.from_dict(tampered, assets=(asset,))


@pytest.mark.parametrize("field,value", [
    ("type_relative_ordinal", False), ("global_index", False),
    ("duration_ts", 4800.0), ("sample_rate", 48000.0), ("channels", 2.0),
])
def test_timeline_reopen_rejects_wrong_metadata_types_even_when_numerically_equal(tmp_path, field, value):
    source = tmp_path / "metadata-types.wav"
    _write_short_stereo_wave(source)
    asset = fingerprint_local_media(str(source))
    document = Timeline.from_assets((asset,)).to_dict()
    document["assets"][0]["stream_metadata"][0][field] = value
    with pytest.raises(VideoEditingError, match="MEDIA_STREAM_METADATA_INVALID"):
        Timeline.from_dict(document, assets=(asset,))


def test_legacy_timeline_reopens_with_fresh_metadata_then_keeps_audio_edit_semantics(tmp_path):
    ffprobe = video_editing._ffprobe_path()
    if not ffprobe or not Path(ffprobe).is_file():
        pytest.skip("actual media metadata contract requires FFprobe")
    source = tmp_path / "legacy-reopen.wav"
    _write_short_stereo_wave(source)
    asset = fingerprint_local_media(str(source))
    original = Timeline.from_assets((asset,)).add_audio_track("voice", audio_role="voiceover")
    original = original.add_clip(
        asset.asset_id, source_in=0.02, source_out=0.08, track_id="voice",
        timeline_start=0.25, audio_stream_index=0,
    )
    saved_legacy = deepcopy(original.to_dict())
    saved_legacy["assets"][0].pop("stream_metadata")
    assert "stream_metadata" not in saved_legacy["assets"][0]

    reopened = Timeline.from_dict(saved_legacy, assets=(asset,))
    reopened_clip = reopened.tracks[1].clips[0]
    assert (reopened_clip.source_in, reopened_clip.source_out, reopened_clip.timeline_start) == (
        0.02, 0.08, 0.25,
    )
    assert reopened_clip.audio_stream_index == 0
    assert reopened.to_dict()["assets"][0]["stream_metadata"] == asset.to_dict()["stream_metadata"]
    # The old document is not rewritten in place; the next current serialization
    # reflects metadata freshly admitted from the verified media bytes.
    assert "stream_metadata" not in saved_legacy["assets"][0]

    moved = reopened.move_audio_clip(reopened_clip.clip_id, timeline_start=0.4)
    moved_clip = moved.tracks[1].clips[0]
    assert (moved_clip.source_in, moved_clip.source_out, moved_clip.timeline_start) == (
        0.02, 0.08, 0.4,
    )
    assert moved_clip.audio_stream_index == 0
    recovered = Timeline.from_dict(moved.to_dict(), assets=(asset,))
    assert recovered.tracks[1].clips[0] == moved_clip


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


def test_timeline_sanitized_document_roundtrips_against_fresh_assets(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fingerprinted source for timeline reopen")
    monkeypatch.setattr(
        video_editing, "_probe_media_info",
        lambda _path: video_editing._MediaProbe(12.0, True, 1),
    )
    asset = fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,), format_ratio="16:9")
    timeline = timeline.add_clip(asset.asset_id, source_out=5.0)
    first_clip_id = timeline.tracks[0].clips[0].clip_id
    timeline = timeline.add_clip(asset.asset_id, source_in=5.0, source_out=10.0)
    second_clip_id = timeline.tracks[0].clips[1].clip_id
    timeline = timeline.add_transition(
        first_clip_id, second_clip_id, transition_type="dissolve", duration_sec=0.5,
        reason="soft scene change",
    )
    timeline = timeline.add_audio_track("music", audio_role="bgm")
    timeline = timeline.add_clip(
        asset.asset_id, source_in=1.0, source_out=4.0, track_id="music", timeline_start=2.5,
    )
    timeline = timeline.set_audio_mix(
        timeline.tracks[1].clips[0].clip_id,
        AudioMix(volume=0.4, fade_in_sec=0.5, fade_out_sec=0.75),
    )
    timeline = timeline.add_caption(0.5, 1.5, "A reviewed caption")

    document = timeline.to_dict()
    assert str(source.resolve()) not in repr(document)
    reopened = Timeline.from_dict(document, assets=(asset,))
    assert reopened.to_dict() == document
    assert [track.track_id for track in reopened.tracks] == ["video", "music"]
    assert [clip.clip_id for clip in reopened.tracks[0].clips] == [first_clip_id, second_clip_id]
    assert reopened.transitions == timeline.transitions
    assert reopened.overlays == timeline.overlays
    assert reopened.version == timeline.version


def test_timeline_deserializer_rejects_missing_tampered_and_forged_asset_data(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"freshly fingerprinted media")
    monkeypatch.setattr(
        video_editing, "_probe_media_info",
        lambda _path: video_editing._MediaProbe(8.0, True, 1),
    )
    asset = fingerprint_local_media(str(source))
    document = Timeline.from_assets((asset,)).add_clip(asset.asset_id).to_dict()

    with pytest.raises(VideoEditingError, match="TIMELINE_REOPEN_ASSET_MISSING"):
        Timeline.from_dict(document, assets=())

    for field, value in (
        ("sha256", "0" * 64),
        ("duration_sec", 7.0),
        ("audio_stream_count", 2),
        ("has_video", False),
        ("media_kind", "audio"),
    ):
        altered = deepcopy(document)
        altered["assets"][0][field] = value
        with pytest.raises(VideoEditingError, match="TIMELINE_REOPEN_ASSET_MISMATCH"):
            Timeline.from_dict(altered, assets=(asset,))

    for field, value in (("evidence_refs", ["forged-evidence"]), ("rights_status", "cleared")):
        altered = deepcopy(document)
        altered["assets"][0][field] = value
        with pytest.raises(VideoEditingError, match="TIMELINE_REOPEN_ASSET_MISMATCH"):
            Timeline.from_dict(altered, assets=(asset,))

    with pytest.raises(VideoEditingError, match="TIMELINE_DOCUMENT_FIELDS_INVALID"):
        Timeline.from_dict({**document, "source_path": str(source)}, assets=(asset,))
    path_injected = deepcopy(document)
    path_injected["assets"][0]["path"] = str(source)
    with pytest.raises(VideoEditingError, match="TIMELINE_DOCUMENT_FIELDS_INVALID"):
        Timeline.from_dict(path_injected, assets=(asset,))

    evidence_injected = deepcopy(document)
    evidence_injected["tracks"][0]["clips"][0]["evidence_refs"] = ["forged-evidence"]
    with pytest.raises(VideoEditingError, match="CANONICAL_EVIDENCE_BINDING_UNAVAILABLE"):
        Timeline.from_dict(evidence_injected, assets=(asset,))


def test_timeline_deserializer_rejects_unknown_fields_and_invalid_times(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source for malformed document")
    monkeypatch.setattr(
        video_editing, "_probe_media_info",
        lambda _path: video_editing._MediaProbe(8.0, True, 1),
    )
    asset = fingerprint_local_media(str(source))
    document = Timeline.from_assets((asset,)).add_clip(asset.asset_id).to_dict()

    unknown = deepcopy(document)
    unknown["tracks"][0]["clips"][0]["extra"] = "unexpected"
    with pytest.raises(VideoEditingError, match="TIMELINE_DOCUMENT_FIELDS_INVALID"):
        Timeline.from_dict(unknown, assets=(asset,))

    malformed_time = deepcopy(document)
    malformed_time["tracks"][0]["clips"][0]["source_in"] = math.nan
    with pytest.raises(VideoEditingError, match="INVALID_CLIP_RANGE"):
        Timeline.from_dict(malformed_time, assets=(asset,))


@pytest.mark.parametrize("mutation", ["missing", "bytes", "duration", "inventory", "path"])
def test_reopen_revalidates_actual_file_even_when_supplied_asset_is_stale(tmp_path, monkeypatch, mutation):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"original media")
    monkeypatch.setattr(video_editing, "_probe_media_info", lambda path: video_editing._MediaProbe(8, True, 1))
    asset = fingerprint_local_media(str(source))
    document = Timeline.from_assets((asset,)).add_clip(asset.asset_id).to_dict()
    if mutation == "missing":
        source.unlink()
    elif mutation == "bytes":
        source.write_bytes(b"replaced media")
    elif mutation == "duration":
        asset = replace(asset, duration_sec=9)
    elif mutation == "inventory":
        asset = replace(asset, audio_stream_count=2)
    else:
        replacement = tmp_path / "other.mp4"
        replacement.write_bytes(b"different media")
        asset = replace(asset, path=str(replacement))
    with pytest.raises(VideoEditingError, match="TIMELINE_REOPEN_ASSET_UNAVAILABLE|TIMELINE_REOPEN_ASSET_MISMATCH"):
        Timeline.from_dict(document, assets=(asset,))


@pytest.mark.parametrize("field,value", [
    ("version", True), ("approval_required", False), ("tracks", {}),
    ("assets", None), ("overlays", "bad"), ("transitions", 0),
])
def test_reopen_rejects_malformed_document_shapes(tmp_path, monkeypatch, field, value):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"actual local media")
    monkeypatch.setattr(video_editing, "_probe_media_info", lambda path: video_editing._MediaProbe(8, True, 1))
    asset = fingerprint_local_media(str(source))
    document = Timeline.from_assets((asset,)).add_clip(asset.asset_id).to_dict()
    document[field] = value
    with pytest.raises(VideoEditingError):
        Timeline.from_dict(document, assets=(asset,))


def test_reopen_never_reads_paths_or_approval_from_untrusted_document(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"actual local media")
    monkeypatch.setattr(video_editing, "_probe_media_info", lambda path: video_editing._MediaProbe(8, True, 1))
    asset = fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,)).add_clip(asset.asset_id)
    document = timeline.to_dict()
    calls = []
    original = video_editing.fingerprint_local_media

    def observed(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(video_editing, "fingerprint_local_media", observed)
    for key in ("path", "source_ref", "artifact_id"):
        malicious = deepcopy(document)
        malicious["assets"][0][key] = "untrusted-secret-file"
        with pytest.raises(VideoEditingError, match="TIMELINE_DOCUMENT_FIELDS_INVALID"):
            Timeline.from_dict(malicious, assets=(asset,))
    assert calls == [asset.path] * 3
    with pytest.raises(VideoEditingError, match="TIMELINE_MEDIA_ASSETS_INVALID"):
        Timeline.from_dict(document, assets=document["assets"])
    with pytest.raises(VideoEditingError, match="TIMELINE_DUPLICATE_MEDIA_ASSET"):
        Timeline.from_dict(document, assets=(asset, asset))
    restored = Timeline.from_dict(document, assets=(asset,))
    assert restored.to_export_request()["status"] == "blocked"
    assert restored.to_dict()["approval_required"] is True


@pytest.fixture
def caption_edit_asset(tmp_path, monkeypatch):
    source = tmp_path / "caption-edit.mp4"
    source.write_bytes(b"technical fixture; not real movie")
    monkeypatch.setattr(video_editing, "_probe_media_info", lambda _: video_editing._MediaProbe(12, True, 1))
    return fingerprint_local_media(str(source))


def test_caption_layout_legacy_serialization_remains_exact(caption_edit_asset):
    timeline = Timeline.from_assets((caption_edit_asset,), "16:9").add_caption(0, 1, "old")
    assert set(timeline.to_dict()["overlays"][0]) == {"overlay_id", "kind", "start_sec", "end_sec", "text"}
    assert Timeline.from_dict(timeline.to_dict(), assets=(caption_edit_asset,)).to_dict() == timeline.to_dict()


def test_caption_update_remove_undo_reopen_preserve_other_edits(caption_edit_asset):
    original = Timeline.from_assets((caption_edit_asset,), "16:9").add_clip(caption_edit_asset.asset_id)
    original = original.add_caption(0, 1, "old").add_text_overlay(0, 2, "retained title")
    caption_id = original.overlays[0].overlay_id
    literal = "  All words, spaces and punctuation are retained.  "
    changed = original.update_caption(caption_id, .5, 3, literal, layout_profile="literal-wide-720p-v2")
    assert changed.version == original.version + 1
    assert changed.overlays[0].overlay_id == caption_id and changed.overlays[0].text == literal
    assert changed.tracks == original.tracks and changed.assets == original.assets
    assert changed.overlays[1] == original.overlays[1] and changed.transitions == original.transitions
    assert changed.to_dict()["overlays"][0]["layout_profile"] == "literal-wide-720p-v2"
    reopened = Timeline.from_dict(changed.to_dict(), assets=(caption_edit_asset,))
    assert reopened.to_dict() == changed.to_dict()
    restored = changed.undo()
    assert restored.overlays == original.overlays and restored.version == changed.version + 1
    removed = reopened.remove_overlay(caption_id)
    assert removed.version == reopened.version + 1 and removed.overlays == (original.overlays[1],)
    assert removed.undo().overlays == reopened.overlays
    assert original.overlays[0].text == "old" and original.overlays[0].layout_profile is None
    reset = reopened.update_caption(caption_id, 0, 1, "new default")
    assert "layout_profile" not in reset.to_dict()["overlays"][0]


@pytest.mark.parametrize("bad_profile", ["arbitrary-font", "literal-cjk-windows-v1", "", True, {}, 35])
def test_caption_profile_rejects_unregistered_values(caption_edit_asset, bad_profile):
    timeline = Timeline.from_assets((caption_edit_asset,), "16:9")
    with pytest.raises(VideoEditingError, match="OVERLAY_LAYOUT_PROFILE_NOT_SUPPORTED"):
        timeline.add_caption(0, 1, "text", layout_profile=bad_profile)
    assert not timeline.overlays and timeline.version == 1


@pytest.mark.parametrize("bad_field,value", [("layout_profile", None), ("layout_profile", "unknown"),
                                           ("fontfile", "private.ttf"), ("fontsize", 5)])
def test_caption_profile_reopen_rejects_injected_fields(caption_edit_asset, bad_field, value):
    timeline = Timeline.from_assets((caption_edit_asset,), "16:9").add_caption(0, 1, "text")
    payload = timeline.to_dict()
    payload["overlays"][0][bad_field] = value
    with pytest.raises(VideoEditingError):
        Timeline.from_dict(payload, assets=(caption_edit_asset,))


def test_caption_operations_fail_without_mutating_original(caption_edit_asset):
    original = Timeline.from_assets((caption_edit_asset,), "16:9").add_caption(0, 1, "caption")
    original = original.add_text_overlay(0, 1, "title")
    before = original.to_dict()
    for operation in (lambda: original.remove_overlay("missing"),
                      lambda: original.update_caption("missing", 0, 1, "replacement"),
                      lambda: original.update_caption(original.overlays[1].overlay_id, 0, 1, "replacement"),
                      lambda: original.update_caption(original.overlays[0].overlay_id, float("nan"), 1, "replacement"),
                      lambda: original.update_caption(original.overlays[0].overlay_id, 0, 1, 123)):
        with pytest.raises(VideoEditingError):
            operation()
        assert original.to_dict() == before
    ambiguous = replace(original, overlays=(original.overlays[0], original.overlays[0]))
    for operation in (lambda: ambiguous.remove_overlay(original.overlays[0].overlay_id),
                      lambda: ambiguous.update_caption(original.overlays[0].overlay_id, 0, 1, "replacement")):
        with pytest.raises(VideoEditingError, match="OVERLAY_ID_AMBIGUOUS"):
            operation()


def test_caption_profile_is_not_a_title_or_permission_grant(caption_edit_asset):
    with pytest.raises(VideoEditingError, match="OVERLAY_LAYOUT_PROFILE_NOT_SUPPORTED"):
        TimedOverlay("title", "text", 0, 1, "title", "literal-wide-720p-v2")
    captioned = Timeline.from_assets((caption_edit_asset,), "16:9").add_caption(
        0, 1, "literal", layout_profile="literal-wide-720p-v2")
    assert captioned.to_dict()["approval_required"] is True
    assert captioned.assets[0].rights_status == "unknown" and captioned.assets[0].evidence_refs == ()


def _real_ffprobe_voice_timeline(tmp_path):
    ffprobe = video_editing._ffprobe_path()
    if not ffprobe or not Path(ffprobe).is_file():
        pytest.skip("Timeline edit batch requires actual local FFprobe")
    source = tmp_path / "edit-batch-source.wav"
    _write_short_stereo_wave(source)
    asset = fingerprint_local_media(str(source))
    assert asset.media_kind == "audio" and asset.audio_stream_count == 1
    assert len(asset.stream_metadata) == 1 and asset.stream_metadata[0].kind == "audio"

    timeline = Timeline.from_assets((asset,)).add_audio_track(
        "voice", audio_role="voiceover"
    )
    timeline = timeline.add_clip(
        asset.asset_id,
        source_in=0.0,
        source_out=asset.duration_sec,
        track_id="voice",
        audio_role="voiceover",
        timeline_start=0.25,
    )
    clip = next(clip for track in timeline.tracks for clip in track.clips)
    return source, asset, timeline, clip


def test_timeline_apply_edit_batch_matches_owner_operations_and_reopens_with_metadata(
    tmp_path, monkeypatch,
):
    source, asset, original, clip = _real_ffprobe_voice_timeline(tmp_path)
    source_bytes = source.read_bytes()
    original_version = original.version
    mix = {"volume": 0.6, "fade_in_sec": 0.01, "fade_out_sec": 0.015, "ducking": True}
    commands = [
        {"op": "trim", "clip_id": clip.clip_id, "source_in": 0.01, "source_out": 0.09},
        {"op": "audio_mix", "clip_id": clip.clip_id, "mix": mix},
        {"op": "move_audio_clip", "clip_id": clip.clip_id, "timeline_start": 0.5},
        {"op": "add_caption", "start_sec": 0.51, "end_sec": 0.55, "text": "Batch caption"},
        {"op": "set_format", "format_ratio": "16:9"},
    ]
    # Keep generated overlay identity deterministic so the batch can be compared
    # exactly with the same existing owner operations called one by one.
    monkeypatch.setattr(video_editing, "_id", lambda prefix: f"{prefix}-batch-test")

    edited = original.apply_edit_batch(commands, expected_version=original_version)
    before_format = (
        original.trim(clip.clip_id, source_in=0.01, source_out=0.09)
        .set_audio_mix(clip.clip_id, AudioMix(**mix))
        .move_audio_clip(clip.clip_id, timeline_start=0.5)
        .add_caption(0.51, 0.55, "Batch caption")
    )
    expected = before_format.set_format("16:9")

    assert edited.to_dict() == expected.to_dict()
    assert edited.version == original_version + len(commands)
    edited_clip = edited.tracks[1].clips[0]
    assert (edited_clip.source_in, edited_clip.source_out, edited_clip.timeline_start) == (
        0.01, 0.09, 0.5,
    )
    assert edited_clip.audio_mix == AudioMix(**mix)
    assert edited.overlays[0].text == "Batch caption"
    assert edited.format_ratio == "16:9"
    export_request = edited.to_export_request()
    assert export_request["status"] == "blocked"
    assert export_request["approval_required"] is True
    assert export_request["external_fetch"] is False
    assert source.read_bytes() == source_bytes

    reopened = Timeline.from_dict(edited.to_dict(), assets=(asset,))
    assert reopened.to_dict() == edited.to_dict()
    assert reopened.assets[0].sha256 == asset.sha256
    assert reopened.assets[0].stream_metadata == asset.stream_metadata
    assert reopened.assets[0].rights_status == "unknown"
    assert reopened.assets[0].evidence_refs == ()

    # Timeline history remains per operation: this undo reverses only set_format.
    restored = edited.undo()
    assert restored.version == edited.version + 1
    assert restored.format_ratio == original.format_ratio
    assert restored.tracks == edited.tracks and restored.overlays == edited.overlays
    assert restored.assets[0].to_dict() == asset.to_dict()
    assert restored.tracks[1].clips[0].source_in == 0.01
    assert restored.tracks[1].clips[0].timeline_start == 0.5
    assert restored.tracks[1].clips[0].audio_mix == AudioMix(**mix)
    assert source.read_bytes() == source_bytes


def test_timeline_apply_edit_batch_routes_split_reorder_delete_caption_and_undo(
    tmp_path, monkeypatch,
):
    source = tmp_path / "planned-video.mp4"
    source.write_bytes(b"isolated local timeline fixture")
    monkeypatch.setattr(
        video_editing, "_probe_media_info",
        lambda _path: video_editing._MediaProbe(8.0, True, 1),
    )
    asset = fingerprint_local_media(str(source))
    original = Timeline.from_assets((asset,)).add_clip(asset.asset_id, source_out=8.0)
    original = original.add_caption(
        0.25, 1.0, "Original caption", layout_profile="literal-wide-720p-v2"
    ).add_text_overlay(0.0, 2.0, "Retained title")
    clip = original.tracks[0].clips[0]
    caption = next(item for item in original.overlays if item.kind == "caption")
    title = next(item for item in original.overlays if item.kind == "text")
    commands = [
        {"op": "split", "clip_id": clip.clip_id, "at_sec": 4.0},
        {"op": "reorder", "clip_id": f"{clip.clip_id}-b", "new_index": 0},
        {"op": "delete", "clip_id": f"{clip.clip_id}-a", "ripple": True},
        {
            "op": "update_caption", "overlay_id": caption.overlay_id,
            "start_sec": 0.5, "end_sec": 1.5, "text": "Updated caption",
        },
        {"op": "remove_overlay", "overlay_id": title.overlay_id},
        {"op": "undo"},
    ]

    edited = original.apply_edit_batch(commands, expected_version=original.version)
    expected = (
        original.split(clip.clip_id, at_sec=4.0)
        .reorder(f"{clip.clip_id}-b", new_index=0)
        .delete(f"{clip.clip_id}-a", ripple=True)
        .update_caption(
            caption.overlay_id, 0.5, 1.5, "Updated caption",
            layout_profile="literal-wide-720p-v2",
        )
        .remove_overlay(title.overlay_id)
        .undo()
    )

    assert edited.to_dict() == expected.to_dict()
    assert edited.version == original.version + len(commands)
    assert len(edited.tracks[0].clips) == 1
    assert edited.tracks[0].clips[0].clip_id == f"{clip.clip_id}-b"
    assert edited.tracks[0].clips[0].timeline_start == 0.0
    assert len(edited.overlays) == 2
    updated_caption = next(item for item in edited.overlays if item.kind == "caption")
    assert updated_caption.text == "Updated caption"
    assert updated_caption.layout_profile == "literal-wide-720p-v2"
    assert any(item.overlay_id == title.overlay_id for item in edited.overlays)
    assert edited.assets[0].rights_status == "unknown"
    assert edited.assets[0].evidence_refs == ()
    assert edited.to_export_request()["status"] == "blocked"


def test_timeline_apply_edit_batch_checks_exact_version_before_commands(tmp_path):
    source, asset, original, clip = _real_ffprobe_voice_timeline(tmp_path)
    original_digest = original._view_digest()
    source_bytes = source.read_bytes()
    commands = [
        {"op": "trim", "clip_id": clip.clip_id, "source_in": 0.01, "source_out": 0.09},
        {"op": "unsupported"},
    ]

    with pytest.raises(VideoEditingError, match="TIMELINE_VERSION_MISMATCH"):
        original.apply_edit_batch(commands, expected_version=original.version - 1)
    assert original._view_digest() == original_digest
    assert original.assets[0].sha256 == asset.sha256
    assert source.read_bytes() == source_bytes

    base = Timeline.from_assets((asset,))
    with pytest.raises(VideoEditingError, match="TIMELINE_VERSION_MISMATCH"):
        base.apply_edit_batch([], expected_version=True)
    assert base.version == 1 and base._view_digest() == Timeline.from_assets((asset,))._view_digest()


def test_timeline_apply_edit_batch_mid_batch_failure_preserves_original_hash(tmp_path):
    source, asset, original, clip = _real_ffprobe_voice_timeline(tmp_path)
    original_digest = original._view_digest()
    source_bytes = source.read_bytes()
    commands = [
        {"op": "trim", "clip_id": clip.clip_id, "source_in": 0.01, "source_out": 0.09},
        {"op": "trim", "clip_id": clip.clip_id, "source_in": 0.02, "source_out": 1.0},
    ]

    with pytest.raises(VideoEditingError, match="TRIM_RANGE_OUTSIDE_MEDIA_ASSET"):
        original.apply_edit_batch(commands, expected_version=original.version)
    assert original._view_digest() == original_digest
    assert original.assets[0].sha256 == asset.sha256
    assert source.read_bytes() == source_bytes


@pytest.mark.parametrize("failure", ["unknown_field", "unsupported_operation", "invalid_mix"])
def test_timeline_apply_edit_batch_rejects_unknown_command_fields_and_operations(
    tmp_path, failure,
):
    source, asset, original, clip = _real_ffprobe_voice_timeline(tmp_path)
    original_digest = original._view_digest()
    source_bytes = source.read_bytes()
    if failure == "unknown_field":
        command = {
            "op": "trim", "clip_id": clip.clip_id, "source_in": 0.01,
            "source_out": 0.09, "approved": True,
        }
        error = "EDIT_COMMAND_FIELDS_INVALID"
    elif failure == "unsupported_operation":
        command = {"op": "render"}
        error = "EDIT_OPERATION_NOT_SUPPORTED"
    else:
        command = {
            "op": "audio_mix", "clip_id": clip.clip_id,
            "mix": {"volume": 0.5, "unreviewed_effect": True},
        }
        error = "INVALID_AUDIO_MIX"

    with pytest.raises(VideoEditingError, match=error):
        original.apply_edit_batch([command], expected_version=original.version)
    assert original._view_digest() == original_digest
    assert original.assets[0].sha256 == asset.sha256
    assert source.read_bytes() == source_bytes


def test_timeline_apply_edit_batch_accepts_128_commands_and_rejects_129(tmp_path):
    source, asset, original, _clip = _real_ffprobe_voice_timeline(tmp_path)
    original_digest = original._view_digest()
    source_bytes = source.read_bytes()
    commands = [{"op": "set_format", "format_ratio": "16:9"}] * 128

    edited = original.apply_edit_batch(commands, expected_version=original.version)
    assert edited.version == original.version + 128
    assert edited.format_ratio == "16:9"

    with pytest.raises(VideoEditingError, match="EDIT_COMMAND_COUNT_EXCEEDED"):
        original.apply_edit_batch(commands + [{"op": "undo"}], expected_version=original.version)
    assert original._view_digest() == original_digest
    assert original.assets[0].sha256 == asset.sha256
    assert source.read_bytes() == source_bytes
