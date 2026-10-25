"""Real FFmpeg timestamp transport with synthetic alignment tokens, NOT ASR quality."""
import copy
import hashlib
import json
import struct
import subprocess
import wave
from pathlib import Path

import pytest

from tests.test_content_project_storage import media_store  # noqa: F401
from lumenis.shared.content_creation import speech_transcription as adapter
from lumenis.shared.content_creation.video_editing import Timeline, VideoEditingError, fingerprint_local_media, _ffprobe_path
from lumenis.system.ai_gateway import owned_speech
from shared_artifacts import _ffmpeg_path


def signal_start(path, threshold=100):
    with wave.open(str(path)) as audio:
        assert audio.getsampwidth() == 2
        count, rate, channels = audio.getnframes(), audio.getframerate(), audio.getnchannels()
        samples = struct.unpack('<' + 'h' * count * channels, audio.readframes(count))
    return next((i // channels / rate for i, value in enumerate(samples) if abs(value) > threshold), None), count, rate


@pytest.fixture
def aligned_decoder(monkeypatch):
    runtime = owned_speech.SpeechRuntime('/missing/python', 'a'*64, '/missing/manifest', 'b'*64,
                                        '/missing/weights', '/missing/ffmpeg', 'c'*64)
    monkeypatch.setattr(adapter, 'configured_speech_runtime', lambda: runtime)
    captures = []
    def decode(path, **kwargs):
        kwargs['is_cancelled']()
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == kwargs['expected_audio_sha256']
        start, frames, rate = signal_start(path)
        assert start is not None and rate == 16000
        captures.append({'first_signal': start, 'frames': frames, 'rate': rate})
        a, b = start + .05, start + .15
        raw = {'text': ' synthetic-alignment-token', 'language': 'en', 'segments': [
            {'id': 0, 'start': a, 'end': b, 'text': ' synthetic-alignment-token',
             'avg_logprob': -.1, 'compression_ratio': 1., 'no_speech_prob': .01,
             'words': [{'word': 'synthetic-alignment-token', 'start': a, 'end': b, 'probability': .9}]}]}
        return {'schema': 'synthetic_alignment_fixture_NOT_ASR',
                **owned_speech.validate_transcript(raw, duration_seconds=frames/rate),
                'source_sha256': kwargs['expected_audio_sha256']}
    monkeypatch.setattr(owned_speech, 'transcribe_audio', decode)
    return captures


def container(store, *, shift=0, delay=.75, multitrack=False, vfr=False):
    root = store['source'].parent
    resampled = root / 'tone44100.wav'
    subprocess.run([_ffmpeg_path(), '-v', 'error', '-n', '-i', str(store['source']), '-ar', '44100',
                    str(resampled)], check=True, capture_output=True)
    output = root / 'timed.mkv'
    command = [_ffmpeg_path(), '-v', 'error', '-n', '-f', 'lavfi', '-i', 'color=c=black:s=32x32:r=10:d=2',
               '-itsoffset', str(delay), '-i', str(resampled)]
    if multitrack:
        command += ['-itsoffset', '1.1', '-i', str(resampled)]
    command += ['-map', '0:v', '-map', '1:a']
    if multitrack:
        command += ['-map', '2:a']
    if vfr:
        command += ['-vf', "select='not(eq(mod(n,3),1))'", '-fps_mode', 'vfr']
    command += ['-c:v', 'ffv1', '-c:a', 'pcm_s16le', '-avoid_negative_ts', 'disabled',
                '-output_ts_offset', str(shift), str(output)]
    subprocess.run(command, check=True, capture_output=True)
    return fingerprint_local_media(str(output))


@pytest.mark.parametrize('shift', [0, -.25, 2])
def test_nonzero_stream_origin_preserved_and_matches_actual_render(media_store, aligned_decoder, shift):
    from lumenis.shared.content_creation.rendering import render_timeline
    asset = container(media_store, shift=shift)
    source_bytes = Path(asset.path).read_bytes()
    item = adapter.build_transcription_files(asset)
    assert aligned_decoder[-1]['first_signal'] == pytest.approx(.75, abs=1/16000)
    clock = item['report']['audio_normalization']['source_clock']
    assert clock['container_start_time_seconds'] == shift
    assert clock['stream_start_time_seconds'] == pytest.approx(shift + .75)
    assert clock['declared_relative_stream_start_seconds'] == pytest.approx(.75)
    assert clock['source_sample_rate'] == 44100
    assert aligned_decoder[-1]['frames'] == round(asset.duration_sec * 16000)
    timeline = Timeline.from_assets([asset]).add_audio_track('voice', audio_role='voiceover')
    timeline = timeline.add_clip(asset.asset_id, track_id='voice', audio_role='voiceover',
                                 source_in=.5, source_out=1.4, timeline_start=.2)
    target = media_store['source'].parent / 'rendered.wav'
    rendered = render_timeline(timeline, target, output_kind='audio')
    converted = target.with_name('rendered16.wav')
    subprocess.run([_ffmpeg_path(), '-v', 'error', '-n', '-i', str(target), '-c:a', 'pcm_s16le', str(converted)],
                   check=True, capture_output=True)
    actual_start, _, _ = signal_start(converted)
    assert actual_start == pytest.approx(.45, abs=.002)
    mapped = adapter.build_timeline_transcription_files(timeline, item, rendered_sha256=rendered['media_sha256'])
    assert mapped['report']['words'][0]['start'] == pytest.approx(.5, abs=1/16000)
    assert mapped['report']['words'][0]['source_start'] == pytest.approx(.8, abs=1/16000)
    assert Path(asset.path).read_bytes() == source_bytes


def test_missing_container_start_wave_uses_actual_sample_clock(media_store, aligned_decoder):
    asset = fingerprint_local_media(str(media_store['source']))
    item = adapter.build_transcription_files(asset)
    clock = item['report']['audio_normalization']['source_clock']
    assert clock['container_start_time_seconds'] is None
    assert clock['stream_start_time_seconds'] is None
    assert clock['declared_relative_stream_start_seconds'] is None
    assert aligned_decoder[-1]['first_signal'] == pytest.approx(0, abs=1/16000)


def test_negative_absolute_audio_pts_is_not_blindly_clamped(media_store, aligned_decoder):
    asset = container(media_store, shift=-1)
    item = adapter.build_transcription_files(asset)
    clock = item['report']['audio_normalization']['source_clock']
    assert clock['stream_start_time_seconds'] == -.25
    assert clock['container_start_time_seconds'] == -1
    assert aligned_decoder[-1]['first_signal'] == pytest.approx(.75, abs=1/16000)


def test_selected_delayed_stream_and_vfr_video_do_not_choose_another_origin(media_store, aligned_decoder):
    asset = container(media_store, multitrack=True, vfr=True)
    observed = json.loads(subprocess.run([_ffprobe_path(), '-v', 'error', '-select_streams', 'v:0',
        '-show_frames', '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json', asset.path],
        check=True, capture_output=True, text=True).stdout)
    pts = [float(frame['best_effort_timestamp_time']) for frame in observed['frames']]
    assert len({round(right-left, 6) for left, right in zip(pts, pts[1:])}) > 1
    with pytest.raises(VideoEditingError, match='AUDIO_STREAM_SELECTION_REQUIRED'):
        adapter.build_transcription_files(asset)
    first = adapter.build_transcription_files(asset, audio_stream_index=0)
    second = adapter.build_transcription_files(asset, audio_stream_index=1)
    assert [value['first_signal'] for value in aligned_decoder] == pytest.approx([.75, 1.1], abs=1/16000)
    assert first['report']['audio_normalization']['source_clock']['stream_index'] != second['report']['audio_normalization']['source_clock']['stream_index']
    assert second['report']['audio_normalization']['source_clock']['video_frame_alignment'] == 'not_claimed'


def test_repeat_trim_overlap_and_sample_delay_mapping(media_store, aligned_decoder):
    asset = container(media_store)
    item = adapter.build_transcription_files(asset)
    timeline = Timeline.from_assets([asset]).add_audio_track('a', audio_role='voiceover')
    timeline = timeline.add_clip(asset.asset_id, track_id='a', audio_role='voiceover',
                                 source_in=.5, source_out=1, timeline_start=.000013)
    timeline = timeline.add_clip(asset.asset_id, track_id='a', audio_role='voiceover',
                                 source_in=.5, source_out=1, timeline_start=1)
    mapped = adapter.build_timeline_transcription_files(timeline, item, rendered_sha256='a'*64)
    assert [word['start'] for word in mapped['report']['words']] == pytest.approx([round(.000013*48000)/48000+.3,1.3], abs=1/16000)
    overlapping = timeline.add_audio_track('b', audio_role='voiceover').add_clip(
        asset.asset_id, track_id='b', audio_role='voiceover', source_in=.5, source_out=1)
    with pytest.raises(VideoEditingError, match='OVERLAP_REQUIRES_REVIEW'):
        adapter.build_timeline_transcription_files(overlapping, item, rendered_sha256='a'*64)
    cut = Timeline.from_assets([asset]).add_audio_track('a', audio_role='voiceover').add_clip(
        asset.asset_id, track_id='a', audio_role='voiceover', source_in=.82, source_out=1)
    assert adapter.build_timeline_transcription_files(cut, item, rendered_sha256='a'*64)['report']['state'] == 'no_retained_words'


def test_legacy_container_report_and_changed_clock_fail_closed(media_store, aligned_decoder):
    asset = container(media_store)
    original = adapter.build_transcription_files(asset)
    timeline = Timeline.from_assets([asset]).add_audio_track('a', audio_role='voiceover').add_clip(
        asset.asset_id, track_id='a', audio_role='voiceover', source_out=1.4)
    for mutate, code in [(lambda r: r.pop('audio_normalization'), 'SOURCE_CLOCK_UNVERIFIED'),
                         (lambda r: r['audio_normalization']['source_clock'].update(stream_start_time_seconds=0), 'SOURCE_CLOCK_MISMATCH')]:
        item = copy.deepcopy(original); mutate(item['report'])
        item['files']['transcription.json'] = json.dumps(item['report']).encode()
        with pytest.raises(VideoEditingError, match=code):
            adapter.build_timeline_transcription_files(timeline, item, rendered_sha256='a'*64)


@pytest.mark.parametrize('jump', [.3, -.04])
def test_actual_discontinuous_audio_pts_rejected_before_decoder(media_store, aligned_decoder, jump):
    output = media_store['source'].parent / 'discontinuous.mkv'
    subprocess.run([_ffmpeg_path(), '-v', 'error', '-n', '-i', str(media_store['source']),
                    '-af', f"asetpts=PTS+if(gte(T\\,0.4)\\,{jump}/TB\\,0)",
                    '-c:a', 'pcm_s16le', str(output)], check=True, capture_output=True)
    asset = fingerprint_local_media(str(output))
    with pytest.raises(VideoEditingError, match='SOURCE_CLOCK_DISCONTINUITY_UNSUPPORTED'):
        adapter.build_transcription_files(asset)
    assert aligned_decoder == []


def test_clock_scan_is_packet_bounded_and_cancellable(media_store, monkeypatch):
    from lumenis.shared.content_creation import rendering
    asset = fingerprint_local_media(str(media_store['source']))
    original = rendering._run
    observed = []
    def cancel():
        raise VideoEditingError('TEST_CLOCK_CANCELLED')
    def run(command, **kwargs):
        if '-show_frames' in command:
            observed.append(command)
            assert command[command.index('-read_intervals') + 1] == '%+#100001'
            assert kwargs['timeout'] == 60
            kwargs['check_continue']()
        return original(command, **{**kwargs, 'check_continue': None})
    monkeypatch.setattr(rendering, '_run', run)
    with pytest.raises(VideoEditingError, match='TEST_CLOCK_CANCELLED'):
        adapter._source_transcription_clock(asset, 0, check_cancel=cancel)
    assert len(observed) == 1


def test_incomplete_packet_scan_does_not_claim_verified_clock(media_store, monkeypatch):
    from lumenis.shared.content_creation import rendering
    asset = fingerprint_local_media(str(media_store['source']))
    original = rendering._run
    def run(command, **kwargs):
        if '-show_frames' in command:
            Path(command[command.index('-o') + 1]).write_text(json.dumps({
                'frames': [{'best_effort_timestamp': 0, 'nb_samples': 1024}],
                'streams': [{'nb_read_packets': '100001'}]}))
            return
        return original(command, **kwargs)
    monkeypatch.setattr(rendering, '_run', run)
    with pytest.raises(VideoEditingError, match='SOURCE_CLOCK_UNVERIFIED'):
        adapter._source_transcription_clock(asset, 0)


def test_sub_tolerance_frame_drift_cannot_accumulate(media_store, monkeypatch):
    from lumenis.shared.content_creation import rendering
    asset = fingerprint_local_media(str(media_store['source']))
    original = rendering._run
    def run(command, **kwargs):
        if '-show_frames' in command:
            Path(command[command.index('-o') + 1]).write_text(json.dumps({
                'frames': [{'best_effort_timestamp': i * 1025, 'nb_samples': 1024} for i in range(20)],
                'streams': [{'nb_read_packets': '20'}]}))
            return
        return original(command, **kwargs)
    monkeypatch.setattr(rendering, '_run', run)
    with pytest.raises(VideoEditingError, match='SOURCE_CLOCK_DISCONTINUITY_UNSUPPORTED'):
        adapter._source_transcription_clock(asset, 0)
