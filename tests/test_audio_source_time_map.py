from dataclasses import replace
import json

import pytest

from lumenis.shared.content_creation import video_editing as video
from tests.test_clip_source_revision import make_asset, without_version


@pytest.fixture
def episode(make_asset):
    old = make_asset("original.wav", duration=30)
    timeline = video.Timeline.from_assets((old,)).add_audio_track("voice", audio_role="voiceover")
    for index in range(3):
        timeline = timeline.add_clip(old.asset_id, source_in=index*3, source_out=(index+1)*3,
                                      track_id="voice", timeline_start=index*3)
    return timeline


def test_full_utterance_revision_shifts_later_clip_and_caption_and_undo(episode, make_asset):
    value = episode.add_caption(6, 8, "Keep this complete later sentence")
    target = value.tracks[1].clips[1]
    new = make_asset("complete-corrected.wav")
    revised = value.replace_audio_source(target.clip_id, asset=new, source_in=0, source_out=5,
                                         ripple_track_ids=("voice",))
    assert revised.duration_sec == 11
    assert revised.version == value.version+1
    assert revised.tracks[1].clips[0] == value.tracks[1].clips[0]
    assert revised.tracks[1].clips[1].clip_id == target.clip_id
    assert revised.tracks[1].clips[1].source_out == 5
    later = revised.tracks[1].clips[2]
    assert later.timeline_start == 8
    assert (later.source_in, later.source_out) == (6, 9)
    assert later.clip_id == value.tracks[1].clips[2].clip_id
    assert revised.overlays[0].start_sec == 8 and revised.overlays[0].end_sec == 10
    assert revised.overlays[0].text == value.overlays[0].text
    assert without_version(revised.undo()) == without_version(value)
    assert video.Timeline.from_dict(json.loads(json.dumps(revised.to_dict())), assets=revised.assets).to_dict() == revised.to_dict()


def test_selected_other_track_shifts_but_unselected_track_stays_anchored(episode, make_asset):
    asset = episode.assets[0]
    value = episode.add_audio_track("sfx", audio_role="sfx").add_audio_track("music", audio_role="bgm")
    value = value.add_clip(asset.asset_id, source_out=1, track_id="sfx", timeline_start=7)
    value = value.add_clip(asset.asset_id, source_out=2, track_id="music", timeline_start=7)
    changed = value.replace_audio_source(value.tracks[1].clips[1].clip_id, asset=make_asset("new.wav"),
        source_in=0, source_out=5, ripple_track_ids=("voice", "sfx"))
    assert changed.tracks[2].clips[0].timeline_start == 9
    assert changed.tracks[3].clips == value.tracks[3].clips


def test_intersecting_dependent_clip_requires_real_replan(episode, make_asset):
    value = episode.add_audio_track("music", audio_role="bgm")
    value = value.add_clip(episode.assets[0].asset_id, source_out=9, track_id="music")
    before = value.to_dict()
    with pytest.raises(video.VideoEditingError, match="INTERSECTING_CLIP_REQUIRES_REPLAN"):
        value.replace_audio_source(value.tracks[1].clips[1].clip_id, asset=make_asset("new.wav"),
            source_in=0, source_out=5, ripple_track_ids=("voice", "music"))
    assert value.to_dict() == before


def test_overlay_inside_changed_utterance_needs_explicit_authored_range(episode, make_asset):
    value = episode.add_caption(3, 6, "Changed utterance text")
    target = value.tracks[1].clips[1]
    new = make_asset("new.wav")
    with pytest.raises(video.VideoEditingError, match="INTERSECTING_OVERLAY_REQUIRES_RANGE"):
        value.replace_audio_source(target.clip_id, asset=new, source_in=0, source_out=5,
                                   ripple_track_ids=("voice",))
    changed = value.replace_audio_source(target.clip_id, asset=new, source_in=0, source_out=5,
        ripple_track_ids=("voice",), overlay_ranges={value.overlays[0].overlay_id: (3, 8)})
    assert changed.overlays[0].start_sec == 3 and changed.overlays[0].end_sec == 8
    assert changed.overlays[0].text == value.overlays[0].text


@pytest.mark.parametrize("scope", ["voice", (), ("missing",), ("voice", "voice"), (True,)])
def test_invalid_ripple_scope_keeps_old_work(episode, make_asset, scope):
    before = episode.to_dict()
    with pytest.raises(video.VideoEditingError, match="RIPPLE_SCOPE_INVALID"):
        episode.replace_audio_source(episode.tracks[1].clips[1].clip_id, asset=make_asset("new.wav"),
            source_in=0, source_out=5, ripple_track_ids=scope)
    assert episode.to_dict() == before


def test_video_clip_cannot_be_retimed_by_audio_replacement(make_asset):
    picture = make_asset("picture.mp4", has_video=True)
    value = video.Timeline.from_assets((picture,)).add_clip(picture.asset_id, source_out=3)
    with pytest.raises(video.VideoEditingError, match="REQUIRES_AUDIO_CLIP"):
        value.replace_audio_source(value.tracks[0].clips[0].clip_id, asset=picture,
                                   source_in=0, source_out=5, ripple_track_ids=("video",))


def test_actual_adjacent_decimal_endpoints_do_not_create_false_overlap(make_asset):
    source = make_asset("actual-clock.wav", duration=80)
    value = video.Timeline.from_assets((source,)).add_audio_track("voice", audio_role="voiceover")
    value = value.add_clip(source.asset_id, source_in=1.975, source_out=20.575, track_id="voice", timeline_start=1.975)
    value = value.add_clip(source.asset_id, source_in=20.575, source_out=43.9, track_id="voice", timeline_start=20.575)
    value = value.add_clip(source.asset_id, source_in=43.9, source_out=60, track_id="voice", timeline_start=43.9)
    before = value.tracks[1].clips[0]
    assert before.timeline_start + before.duration_sec > 20.575
    target = value.tracks[1].clips[1]
    new = make_asset("complete-new-source.wav", duration=25.65)
    changed = value.replace_audio_source(target.clip_id, asset=new, source_in=0, source_out=25.65,
                                         ripple_track_ids=("voice",))
    assert changed.tracks[1].clips[0] == before
    assert changed.tracks[1].clips[2].timeline_start == 46.225
    assert without_version(changed.undo()) == without_version(value)
