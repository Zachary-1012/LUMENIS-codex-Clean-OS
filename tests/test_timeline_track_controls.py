"""Track intent survives reopen and changes actual local rendering."""
import subprocess
import array
import math

import pytest

from lumenis.shared.content_creation import video_editing as editing, rendering
from shared_artifacts import _ffmpeg_path


@pytest.fixture
def media(tmp_path,monkeypatch):
    ffmpeg = _ffmpeg_path()
    if not ffmpeg or not editing._ffprobe_path():
        pytest.skip('Existing encoders are required for affected media rendering')
    monkeypatch.setenv('LUMENIS_LOCAL_ASSET_DIR',str(tmp_path))
    monkeypatch.setitem(rendering.FRAME_SIZES,'16:9',(160,90))
    assets = []
    for color,hertz in [('red',220),('blue',660)]:
        path = tmp_path/(color+'.mp4')
        subprocess.run([ffmpeg,'-v','error','-nostdin','-n','-f','lavfi','-i',f'color=c={color}:s=160x90:r=30:d=2',
            '-f','lavfi','-i',f'sine=frequency={hertz}:sample_rate=48000:duration=2','-c:v','libx264','-threads:v','1',
            '-pix_fmt','yuv420p','-c:a','aac','-shortest',str(path)],check=True,capture_output=True,timeout=20)
        assets.append(editing.fingerprint_local_media(str(path)))
    return assets


def timeline(assets):
    result = editing.Timeline.from_assets(assets,'16:9').add_clip(assets[0].asset_id,source_out=2)
    return result.add_video_track('upper').add_clip(assets[1].asset_id,track_id='upper',source_out=2,timeline_start=0)


def test_locked_track_rejects_edit_and_word_cut_atomically_and_reopens(media):
    original = timeline(media)
    locked = original.set_track_controls('video',locked=True)
    clip = locked.tracks[0].clips[0]
    with pytest.raises(editing.VideoEditingError,match='TIMELINE_TRACK_LOCKED'):
        locked.trim(clip.clip_id,source_in=0,source_out=1)
    with pytest.raises(editing.VideoEditingError,match='TIMELINE_TRACK_LOCKED'):
        locked.apply_edit_batch([{'op':'track_controls','track_id':'upper','muted':True},
            {'op':'delete','clip_id':clip.clip_id}],expected_version=locked.version)
    assert not locked.tracks[1].muted
    reopened = editing.Timeline.from_dict(locked.to_dict(),assets=media)
    assert reopened.tracks[0].locked
    with pytest.raises(editing.VideoEditingError,match='TIMELINE_TRACK_LOCKED'):
        reopened.split(clip.clip_id,at_sec=1)
    unlocked = reopened.set_track_controls('video',locked=False)
    assert len(unlocked.split(clip.clip_id,at_sec=1).tracks[0].clips) == 2
    assert locked.undo().to_dict()['tracks'] == original.to_dict()['tracks']


def test_hidden_video_and_solo_audio_affect_pixels_and_real_mix(media,tmp_path):
    value = timeline(media).set_track_controls('upper',hidden=True,muted=True).set_track_controls('video',solo=True)
    reopened = editing.Timeline.from_dict(value.to_dict(),assets=media)
    path = tmp_path/'controlled.mp4'
    result = rendering.render_timeline(reopened,path)
    pixels = subprocess.run([_ffmpeg_path(),'-v','error','-i',str(path),'-vf','scale=1:1','-frames:v','1',
        '-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True,check=True,timeout=15).stdout
    assert pixels[0] > 220 and pixels[2] < 20
    assert result['track_processing']['hidden_video_tracks'] == ['upper']
    assert result['measurement']['audio_streams'] == 1
    assert [track.track_id for track in reopened.audible_tracks()] == ['video']
    raw = subprocess.run([_ffmpeg_path(),'-v','error','-i',str(path),'-map','0:a:0','-ac','1',
        '-ar','48000','-f','s16le','pipe:1'],capture_output=True,check=True,timeout=15).stdout
    samples = array.array('h',raw)[12000:72000:8]
    def energy(hertz):
        return abs(sum(value*complex(math.cos(2*math.pi*hertz*i/6000),
                                     math.sin(2*math.pi*hertz*i/6000)) for i,value in enumerate(samples)))
    assert energy(220) > 30*energy(660)


def test_all_video_hidden_renders_black_without_discarding_project(media,tmp_path):
    value = timeline(media).set_track_controls('video',hidden=True).set_track_controls('upper',hidden=True)
    result = rendering.render_timeline(value,tmp_path/'black.mp4')
    assert result['measurement']['video_frames'] == 60
    pixels = subprocess.run([_ffmpeg_path(),'-v','error','-i',str(tmp_path/'black.mp4'),'-vf','scale=1:1',
        '-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True,check=True,timeout=15).stdout
    assert max(pixels) < 10
    assert len(value.tracks[0].clips) == len(value.tracks[1].clips) == 1


def test_rate_window_seek_maps_to_original_source_clock(media):
    value = editing.Timeline.from_assets(media,'16:9').add_clip(media[0].asset_id,source_out=2)
    clip = value.tracks[0].clips[0]
    value = value.set_playback_rate(clip.clip_id,playback_rate=2)
    window = value.describe_window(start_sec=0,span_sec=1,playhead_sec=.5)
    assert window['tracks'][0]['clips'][0]['visible_source_range_sec'] == [0,2]
    assert window['playhead']['active_clips'][0]['source_position_sec'] == 1


def test_all_audio_muted_exports_intentional_silence_and_retains_source(media,tmp_path):
    value = editing.Timeline.from_assets(media,'16:9').add_audio_track('speech',audio_role='voiceover')
    value = value.add_clip(media[0].asset_id,track_id='speech',source_out=2,audio_stream_index=0)
    value = value.set_track_controls('speech',muted=True)
    result = rendering.render_timeline(value,tmp_path/'muted.wav',output_kind='audio')
    assert result['measurement']['audio_streams'] == 1
    raw = subprocess.run([_ffmpeg_path(),'-v','error','-i',str(tmp_path/'muted.wav'),'-f','s16le','pipe:1'],
                         capture_output=True,check=True,timeout=10).stdout
    assert raw and not any(raw)
    assert value.tracks[1].clips[0].media_asset_id == media[0].asset_id


def test_batched_music_audition_does_not_require_muted_sidechain(media,tmp_path,monkeypatch):
    monkeypatch.setattr(rendering,'RENDER_INPUT_BATCH_SIZE',2)
    value = editing.Timeline.from_assets(media,'16:9').add_audio_track('speech',audio_role='voiceover')
    value = value.add_clip(media[0].asset_id,track_id='speech',source_out=2,audio_stream_index=0)
    value = value.add_audio_track('music',audio_role='bgm')
    for _ in range(3):
        value = value.add_clip(media[1].asset_id,track_id='music',source_out=2,timeline_start=0,audio_stream_index=0)
        value = value.set_audio_mix(value.tracks[-1].clips[-1].clip_id,editing.AudioMix(ducking=True,volume=.1))
    value = value.set_track_controls('music',solo=True)
    result = rendering.render_timeline(value,tmp_path/'music.wav',output_kind='audio')
    assert result['measurement']['audio_streams'] == 1
    assert result['measurement']['actual_duration_sec'] == pytest.approx(2,abs=.001)
