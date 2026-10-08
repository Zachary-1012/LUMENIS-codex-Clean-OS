from dataclasses import replace
import json
import math

import pytest

from lumenis.shared.content_creation import video_editing as video
from podcast.intelligence.episode_runtime import PodcastPlan, PodcastSegment


@pytest.fixture
def make_asset(tmp_path, monkeypatch):
    probes = {}
    monkeypatch.setattr(video, "_probe_media_info", lambda path: probes[path.name])
    def make(name, *, duration=12, has_video=False, streams=1):
        path = tmp_path / name
        path.write_bytes((name + ":isolated-source-test").encode())
        probes[name] = video._MediaProbe(duration, has_video, streams)
        return video.fingerprint_local_media(str(path.resolve()))
    return make


@pytest.fixture
def full_video(make_asset):
    picture = make_asset("picture.mp4", has_video=True, streams=0)
    voice = make_asset("voice.wav")
    value = video.Timeline.from_assets((picture, voice))
    value = value.add_clip(picture.asset_id, source_in=1.123456789, source_out=3.876543219,
                           purpose="retain a complete graphic action", audio_role="muted")
    first = value.tracks[0].clips[0]
    value = value.add_clip(picture.asset_id, source_in=2, source_out=5, audio_role="muted")
    second = value.tracks[0].clips[1]
    value = value.add_transition(first.clip_id, second.clip_id, duration_sec=.3,
                                 reason="continuous graphic position")
    value = value.add_audio_track("narration", audio_role="voiceover")
    value = value.add_clip(voice.asset_id, source_in=.2, source_out=5.2, track_id="narration",
                           timeline_start=.5, audio_role="voiceover")
    value = value.add_caption(.5, 2.4, "retain the whole conditional sentence")
    value = value.set_audio_mix(first.clip_id, video.AudioMix(volume=.375, fade_in_sec=.12, fade_out_sec=.34))
    return value


def without_version(value):
    document = value.to_dict()
    document.pop("version")
    return document


def test_fractional_video_replacement_keeps_whole_edit_and_undo(full_video, make_asset):
    source = make_asset("new-picture.mp4", has_video=True, streams=2)
    old = full_video.tracks[0].clips[0]
    before = full_video.to_dict()
    changed = full_video.replace_clip_source(old.clip_id, asset=source, source_in=1.987654321)
    new = changed.tracks[0].clips[0]
    assert new.source_in == 1.987654321
    assert new.source_out == 1.987654321 + (old.source_out - old.source_in)
    assert new.clip_id == old.clip_id and new.track_id == old.track_id
    assert new.timeline_start == old.timeline_start and new.purpose == old.purpose
    assert new.audio_mix == old.audio_mix and new.audio_role == "muted"
    assert new.audio_stream_index is None
    assert changed.tracks[0].clips[1:] == full_video.tracks[0].clips[1:]
    assert changed.tracks[1:] == full_video.tracks[1:]
    assert changed.overlays == full_video.overlays and changed.transitions == full_video.transitions
    assert changed.version == full_video.version + 1
    assert len(changed.assets) == len(full_video.assets) + 1
    assert without_version(changed.undo()) == without_version(full_video)
    assert full_video.to_dict() == before
    reopened = video.Timeline.from_dict(json.loads(json.dumps(changed.to_dict())), assets=changed.assets)
    assert reopened.to_dict() == changed.to_dict()
    with pytest.raises(video.VideoEditingError, match="TIMELINE_VIEW_SOURCE_CHANGED"):
        changed.navigate_window(full_video.describe_window()["state"], action="seek", value=1)


def test_short_replacement_rejected_without_partial_asset_or_history(full_video, make_asset):
    source = make_asset("short.mp4", duration=2, has_video=True, streams=0)
    before = full_video.to_dict()
    with pytest.raises(video.VideoEditingError, match="REPLACEMENT_RANGE_OUTSIDE_MEDIA_ASSET"):
        full_video.replace_clip_source(full_video.tracks[0].clips[0].clip_id, asset=source, source_in=0)
    assert full_video.to_dict() == before


def test_transition_media_handles_remain_blocking(full_video, make_asset):
    source = make_asset("no-incoming-handle.mp4", has_video=True, streams=0)
    before = full_video.to_dict()
    with pytest.raises(video.VideoEditingError, match="TRANSITION_MEDIA_HANDLES_UNAVAILABLE"):
        full_video.replace_clip_source(full_video.tracks[0].clips[1].clip_id, asset=source, source_in=0)
    assert full_video.to_dict() == before


@pytest.mark.parametrize("start", [True, -1, math.nan, math.inf])
def test_invalid_replacement_range_rejected(full_video, make_asset, start):
    source = make_asset("range.mp4", has_video=True, streams=0)
    with pytest.raises(video.VideoEditingError):
        full_video.replace_clip_source(full_video.tracks[0].clips[0].clip_id, asset=source, source_in=start)


def test_intentional_mute_never_adopts_source_audio(full_video, make_asset):
    source = make_asset("multiaudio.mp4", has_video=True, streams=2)
    with pytest.raises(video.VideoEditingError, match="MUTED_VIDEO_CLIP_CANNOT_SELECT_AUDIO"):
        full_video.replace_clip_source(full_video.tracks[0].clips[0].clip_id, asset=source,
                                       source_in=1, audio_stream_index=0)


def test_original_video_sound_cannot_disappear(make_asset):
    old = make_asset("av-old.mp4", has_video=True)
    new = make_asset("silent-new.mp4", has_video=True, streams=0)
    value = video.Timeline.from_assets((old,)).add_clip(old.asset_id, source_out=4)
    with pytest.raises(video.VideoEditingError, match="REPLACEMENT_WOULD_REMOVE_SOURCE_AUDIO"):
        value.replace_clip_source(value.tracks[0].clips[0].clip_id, asset=new, source_in=1)


def test_audio_replacement_uses_fresh_explicit_stream_and_preserves_mix(make_asset):
    old = make_asset("old.wav")
    new = make_asset("new.mka", streams=2)
    value = video.Timeline.from_assets((old,)).add_audio_track("music", audio_role="bgm")
    value = value.add_clip(old.asset_id, source_in=1.25, source_out=4.75, track_id="music", timeline_start=4)
    target = value.tracks[1].clips[0]
    value = value.set_audio_mix(target.clip_id, video.AudioMix(volume=.41, fade_in_sec=.5, fade_out_sec=.6))
    with pytest.raises(video.VideoEditingError, match="MULTIPLE_SOURCE_AUDIO_TRACKS_REQUIRE_EXPLICIT_SELECTION"):
        value.replace_clip_source(target.clip_id, asset=new, source_in=2)
    changed = value.replace_clip_source(target.clip_id, asset=new, source_in=2, audio_stream_index=1)
    result = changed.tracks[1].clips[0]
    assert result.timeline_start == 4 and result.source_out == 5.5
    assert result.audio_stream_index == 1 and result.audio_role == "bgm"
    assert result.audio_mix == value.tracks[1].clips[0].audio_mix
    assert without_version(changed.undo()) == without_version(value)


@pytest.mark.parametrize("stream", [True, -1, 2, "0"])
def test_forged_stream_choice_rejected(make_asset, stream):
    old = make_asset("old.wav")
    new = make_asset("new.mka", streams=2)
    value = video.Timeline.from_assets((old,)).add_audio_track("voice", audio_role="voiceover")
    value = value.add_clip(old.asset_id, source_out=3, track_id="voice")
    with pytest.raises(video.VideoEditingError, match="AUDIO_STREAM_INDEX_OUT_OF_RANGE"):
        value.replace_clip_source(value.tracks[1].clips[0].clip_id, asset=new, source_in=1,
                                   audio_stream_index=stream)


def test_replacement_noop_retains_version_and_asset_set(full_video):
    target = full_video.tracks[0].clips[0]
    assert full_video.replace_clip_source(target.clip_id, asset=full_video.assets[0],
                                          source_in=target.source_in) is full_video


@pytest.fixture
def podcast(make_asset):
    source = make_asset("podcast-old.wav", duration=30)
    segments = tuple(PodcastSegment("s"+str(n), source.asset_id, n*3, (n+1)*3,
                     "source sentence "+str(n), "display correction "+str(n), "Speaker label",
                     "Chapter "+str(n)) for n in range(3))
    return PodcastPlan("Complete episode", "Retain the full ordered work", "en", segments, revision=5), source


def podcast_change(plan, asset, **extra):
    values = {"asset": asset, "source_in": 1, "source_out": 6,
              "new_source_text": "Complete revised source utterance", "new_source_speaker": "Explicit new source label",
              "expected_revision": plan.revision, "expected_digest": plan.content_digest()}
    values.update(extra)
    return plan.with_segment_source("s1", **values)


def test_longer_podcast_source_keeps_parent_and_rebuilds_all_outputs(podcast, make_asset):
    plan, old = podcast
    new = make_asset("podcast-new.wav")
    before = plan.to_dict()
    updated = podcast_change(plan, new)
    assert updated.revision == 6
    assert plan.to_dict() == before
    assert updated.segments[0] == plan.segments[0] and updated.segments[2] == plan.segments[2]
    assert updated.segments[1].duration == 5
    assert updated.segments[1].original_text == updated.segments[1].corrected_text == "Complete revised source utterance"
    assert updated.segments[1].speaker == "Explicit new source label"
    assert updated.chapter_document()["chapters"][2]["startTime"] == 8
    assert plan.chapter_document()["chapters"][2]["startTime"] == 6
    rendered = updated.build_timeline((old, new))
    assert rendered.duration_sec == 11
    assert rendered.tracks[1].clips[2].timeline_start == 8
    assert rendered.tracks[1].clips[1].source_out == 6
    members = updated.editable_documents()
    assert len(members) == 7
    assert "00:00:08.000" in members["transcript-corrected.vtt"]
    assert "00:00:08.000" in members["transcript-original.vtt"]
    assert PodcastPlan.from_json(members["podcast-plan.json"]).to_dict() == updated.to_dict()
    assert members["metadata.json"].find('"human_listening_acceptance": "not_asserted_by_plan"') >= 0


@pytest.mark.parametrize("extra", [
    {"source_in": True}, {"source_in": -1}, {"source_out": math.nan}, {"source_out": 40},
    {"new_source_text": ""}, {"new_source_speaker": ""},
    {"expected_revision": True}, {"expected_revision": 4}, {"expected_digest": "old"},
])
def test_invalid_or_stale_podcast_source_revision_preserves_parent(podcast, make_asset, extra):
    plan, _ = podcast
    new = make_asset("new.wav")
    before = plan.to_dict()
    with pytest.raises(ValueError):
        podcast_change(plan, new, **extra)
    assert plan.to_dict() == before


def test_podcast_multistream_requires_explicit_selection(podcast, make_asset):
    plan, _ = podcast
    new = make_asset("two-streams.mka", streams=2)
    with pytest.raises(ValueError, match="explicit audio stream"):
        podcast_change(plan, new)
    assert podcast_change(plan, new, audio_stream_index=1).segments[1].audio_stream_index == 1


def test_text_edit_then_source_revision_keeps_other_manual_corrections(podcast, make_asset):
    plan, _ = podcast
    plan = plan.with_transcript_corrections({"s2": "Keep my manual punctuation."},
                 expected_revision=plan.revision, expected_digest=plan.content_digest())
    updated = podcast_change(plan, make_asset("changed.wav"))
    assert updated.revision == plan.revision + 1
    assert updated.segments[2] == plan.segments[2]
    assert updated.segments[2].corrected_text == "Keep my manual punctuation."

