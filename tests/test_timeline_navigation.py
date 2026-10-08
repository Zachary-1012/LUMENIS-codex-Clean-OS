import copy
import json
import math
import wave

import pytest
from lumenis.shared.content_creation.video_editing import Timeline, VideoEditingError, fingerprint_local_media


@pytest.fixture
def asset(tmp_path):
    path=tmp_path/"navigation.wav"
    with wave.open(str(path),"wb") as sound:
        sound.setnchannels(1);sound.setsampwidth(2);sound.setframerate(8000)
        sound.writeframes(b"\x00\x00"*80000)
    return fingerprint_local_media(str(path.resolve()))


@pytest.fixture
def timeline(asset):
    value=Timeline.from_assets((asset,)).add_audio_track("voice",audio_role="voiceover")
    value=value.add_clip(asset.asset_id,source_in=1,source_out=4,track_id="voice",audio_role="voiceover",timeline_start=0)
    return value.add_clip(asset.asset_id,source_in=4,source_out=7,track_id="voice",audio_role="voiceover",timeline_start=3)


def test_half_open_window_preserves_two_source_offsets(timeline):
    before=timeline.to_dict()
    result=timeline.describe_window(start_sec=1,span_sec=3,playhead_sec=3)
    clips=result["tracks"][1]["clips"]
    assert result["duration_sec"]==6
    assert clips[0]["visible_timeline_range_sec"]==[1,3]
    assert clips[0]["visible_source_range_sec"]==[2,4]
    assert clips[0]["start_fraction"]==0 and clips[0]["width_fraction"]==pytest.approx(2/3)
    assert clips[1]["visible_timeline_range_sec"]==[3,4]
    assert clips[1]["visible_source_range_sec"]==[4,5]
    assert len(result["playhead"]["active_clips"])==1
    assert result["playhead"]["active_clips"][0]["clip_id"]==clips[1]["clip"]["clip_id"]
    assert result["playhead"]["active_clips"][0]["source_position_sec"]==4
    assert timeline.to_dict()==before


def test_pan_and_zoom_do_not_edit_or_move_playhead(timeline):
    before=timeline.to_dict()
    view=timeline.describe_window(start_sec=1,span_sec=3,playhead_sec=2)
    right=timeline.navigate_window(view["state"],action="pan",value=100)
    assert right["window"]["start_sec"]==3 and right["playhead"]["time_sec"]==2
    assert right["playhead"]["inside_window"] is False
    left=timeline.navigate_window(right["state"],action="pan",value=-100)
    assert left["window"]["start_sec"]==0
    zoom=timeline.navigate_window(view["state"],action="zoom",value=2,anchor_sec=2)
    assert zoom["window"]["start_sec"]==pytest.approx(1.5)
    assert zoom["window"]["span_sec"]==1.5
    assert zoom["playhead"]["window_fraction"]==pytest.approx(1/3)
    fit=timeline.navigate_window(view["state"],action="zoom",value=.01)
    assert fit["window"]["start_sec"]==0 and fit["window"]["span_sec"]==6
    assert timeline.to_dict()==before


def test_seek_end_does_not_fabricate_active_source(timeline):
    state=timeline.describe_window(span_sec=3)["state"]
    end=timeline.navigate_window(state,action="seek",value=6)
    assert end["playhead"]["at_timeline_end"] is True
    assert end["playhead"]["active_clips"]==[]
    assert end["playhead"]["timeline_fraction"]==1


def test_overlapping_tracks_return_all_active_clips(timeline,asset):
    value=timeline.add_audio_track("music",audio_role="bgm")
    value=value.add_clip(asset.asset_id,source_in=2,source_out=5,track_id="music",audio_role="bgm",timeline_start=1)
    view=value.describe_window(start_sec=1,span_sec=2,playhead_sec=2)
    assert {x["track_id"] for x in view["playhead"]["active_clips"]}=={"voice","music"}
    assert {x["source_position_sec"] for x in view["playhead"]["active_clips"]}=={3}
    assert all(x["stream_index_kind"]=="audio_type_relative_ordinal" for x in view["playhead"]["active_clips"])
    assert view["waveform"] is None


def test_overlay_window_is_half_open_and_keeps_full_text(timeline):
    value=timeline.add_caption(0,1,"already ended").add_caption(1,4,"keep this entire source sentence")
    view=value.describe_window(start_sec=1,span_sec=2)
    assert len(view["overlays"])==1
    assert view["overlays"][0]["overlay"]["text"]=="keep this entire source sentence"
    assert view["overlays"][0]["visible_range_sec"]==[1,3]


def test_empty_timeline_has_view_but_no_duration_fraction(asset):
    value=Timeline.from_assets((asset,))
    result=value.describe_window(start_sec=10,span_sec=20)
    assert result["duration_sec"]==0 and result["window"]["start_sec"]==0
    assert result["playhead"]["timeline_fraction"] is None
    assert result["playhead"]["active_clips"]==[] and result["tracks"][0]["clips"]==[]


def test_state_round_trip_is_bound_to_exact_timeline(timeline):
    result=timeline.describe_window(start_sec=1,span_sec=2,playhead_sec=2)
    saved=json.loads(json.dumps(result["state"]))
    assert timeline.navigate_window(saved,action="pan",value=0)==result
    clip=timeline.tracks[1].clips[0]
    changed=timeline.trim(clip.clip_id,source_in=1,source_out=3)
    with pytest.raises(VideoEditingError,match="TIMELINE_VIEW_SOURCE_CHANGED"):
        changed.navigate_window(saved,action="seek",value=1)


@pytest.mark.parametrize("change",[
    {"timeline_version":True},{"timeline_digest":"different"},
    {"window_start_sec":True},{"window_span_sec":0},{"playhead_sec":math.nan},{"extra":1},
])
def test_tampered_or_invalid_view_state_rejected(timeline,change):
    state=copy.deepcopy(timeline.describe_window()["state"])
    state.update(change)
    with pytest.raises(VideoEditingError):
        timeline.navigate_window(state,action="pan",value=1)


@pytest.mark.parametrize("kwargs",[
    {"start_sec":-1},{"start_sec":math.inf},{"span_sec":0},{"span_sec":True},
    {"span_sec":math.nan},{"playhead_sec":-1},{"playhead_sec":7},{"playhead_sec":True},
])
def test_invalid_view_coordinates_rejected(timeline,kwargs):
    with pytest.raises(VideoEditingError):
        timeline.describe_window(**kwargs)


@pytest.mark.parametrize("action,value,anchor",[
    ("unknown",1,None),("zoom",0,None),("zoom",False,None),("zoom",2,7),
    ("seek",7,None),("seek",1,1),("pan",math.inf,None),("pan",1,1),
])
def test_invalid_navigation_actions_rejected(timeline,action,value,anchor):
    state=timeline.describe_window()["state"]
    with pytest.raises(VideoEditingError):
        timeline.navigate_window(state,action=action,value=value,anchor_sec=anchor)


def test_output_does_not_expose_local_media_path(timeline):
    view=timeline.describe_window(playhead_sec=2)
    serialized=json.dumps(view)
    assert timeline.assets[0].path not in serialized
    assert "source_pts_mapping" in view and view["waveform_state"]=="NOT_COMPUTED"
