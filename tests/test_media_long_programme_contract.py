"""Long-duration control contracts plus tiny native media; no long-film acceptance."""
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from lumenis.shared.content_creation import rendering, video_editing
from lumenis.shared.content_creation.video_editing import VideoEditingError


def _video_probe(duration):
    return {'streams': [{'codec_type': 'video', 'codec_name': 'h264',
        'nb_read_frames': str(round(duration * 30)), 'start_time': '0'}],
        'format': {'duration': str(duration), 'format_name': 'mov,mp4,m4a,3gp,3g2,mj2'}}


class _ProbeProcess:
    def __init__(self, payload, pending=0):
        self.payload, self.pending = payload, pending
        self.returncode, self.killed, self.communications, self.exited = 0, False, 0, False
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.exited = True
        return False
    def communicate(self, timeout=None):
        self.communications += 1
        if timeout is not None and self.pending:
            self.pending -= 1
            raise subprocess.TimeoutExpired('synthetic-probe', timeout)
        return json.dumps(self.payload), ''
    def kill(self):
        self.killed = True


def test_programme_probe_can_progress_past_old_thirty_second_limit(tmp_path, monkeypatch):
    duration = 7200
    process = _ProbeProcess(_video_probe(duration), pending=1)
    clock = iter(range(0, 1000, 35))
    monkeypatch.setattr(rendering.time, 'monotonic', lambda: next(clock))
    monkeypatch.setattr(rendering.subprocess, 'Popen', lambda *a, **k: process)
    checks = []
    result = rendering._probe_output(tmp_path / 'programme.mp4', 'synthetic-probe', output_kind='video',
        duration=duration, has_audio=False, check_continue=lambda: checks.append(True))
    assert result['video_frames'] == 216000
    assert process.communications == 2 and not process.killed and process.exited
    assert len(checks) >= 4


@pytest.mark.parametrize('error', [PermissionError('PERMISSION_REVOKED'), VideoEditingError('MEDIA_RENDER_CANCELLED')])
def test_probe_revocation_or_cancellation_reaps_child_and_preserves_original_exception(tmp_path, monkeypatch, error):
    process = _ProbeProcess(_video_probe(7200), pending=1)
    monkeypatch.setattr(rendering.subprocess, 'Popen', lambda *a, **k: process)
    checks = []
    def check():
        checks.append(True)
        if len(checks) == 3:
            raise error
    with pytest.raises(type(error)) as raised:
        rendering._probe_output(tmp_path / 'programme.mp4', 'synthetic-probe', output_kind='video',
            duration=7200, has_audio=False, check_continue=check)
    assert raised.value is error
    assert process.killed and process.exited and process.communications == 2


def test_probe_timeout_is_finite_and_reaps_encoder(tmp_path, monkeypatch):
    process = _ProbeProcess(_video_probe(1), pending=10)
    clock = iter((0, 31))
    monkeypatch.setattr(rendering.time, 'monotonic', lambda: next(clock))
    monkeypatch.setattr(rendering.subprocess, 'Popen', lambda *a, **k: process)
    with pytest.raises(VideoEditingError, match='RENDER_OUTPUT_VERIFICATION_FAILED'):
        rendering._probe_output(tmp_path / 'programme.mp4', 'synthetic-probe', output_kind='video',
            duration=1, has_audio=False)
    assert process.killed and process.exited


@pytest.mark.parametrize('duration', [True, 0, -1, float('nan'), float('inf'), 86401])
def test_programme_budget_never_accepts_invalid_or_unbounded_duration(duration):
    with pytest.raises(VideoEditingError, match='DURATION_OUT_OF_RANGE'):
        rendering._programme_timeout(duration)


def _loudness(peak=-2):
    return {'state': 'measured', 'integrated_lufs': -16, 'true_peak_dbtp': peak}


@pytest.mark.parametrize('lra', [0, 4])
def test_denoise_and_both_master_branches_keep_programme_budget_callback_and_rf64(tmp_path, monkeypatch, lra):
    duration, commands, measurements = 7200, [], []
    def check():
        pass
    def measure(path, ffmpeg, **kwargs):
        measurements.append(kwargs)
        return _loudness()
    def run(command, **kwargs):
        commands.append((command, kwargs))
        return json.dumps({'input_i': '-23', 'input_tp': '-10', 'input_lra': str(lra),
                          'input_thresh': '-33', 'target_offset': '0', 'normalization_type': 'linear'})
    monkeypatch.setattr(rendering, '_measure_loudness', measure)
    monkeypatch.setattr(rendering, '_run', run)
    output, mastering, denoising = rendering._process_audio(tmp_path / 'mix.wav', 'synthetic-ffmpeg',
        {'noise_reduction_db': 6, 'noise_floor_db': -50, 'loudness_target_lufs': -16},
        duration=duration, check_continue=check)
    assert output.name == 'mastered.wav' and mastering and denoising
    assert all(item['duration'] == duration and item['check_continue'] is check for item in measurements)
    assert all(60 < options['timeout'] <= duration * 8 and options['check_continue'] is check for _, options in commands)
    wav_outputs = [command for command, _ in commands if str(command[-1]).endswith('.wav')]
    assert len(wav_outputs) == 2
    assert all(command[command.index('-rf64') + 1] == 'auto' for command in wav_outputs)


def test_measurement_uses_programme_budget_without_changing_input_loudness_semantics(tmp_path, monkeypatch):
    calls = []
    def check():
        pass
    def run(command, **kwargs):
        calls.append(kwargs)
        return json.dumps({'input_i': '-18', 'input_tp': '-3', 'input_lra': '4', 'output_i': '-24'})
    monkeypatch.setattr(rendering, '_run', run)
    result = rendering._measure_loudness(tmp_path / 'mix.wav', 'synthetic-ffmpeg', duration=7200, check_continue=check)
    assert result['integrated_lufs'] == -18 and result['target_lufs'] is None
    assert 60 < calls[0]['timeout'] <= 7200 * 8 and calls[0]['check_continue'] is check


@pytest.mark.parametrize('kind', ['audio', 'video'])
def test_peak_correction_keeps_budget_and_uses_rf64_only_for_wav(tmp_path, monkeypatch, kind):
    measured, commands = [], []
    def check():
        pass
    def measure(path, ffmpeg, **kwargs):
        measured.append(kwargs)
        return _loudness(2 if len(measured) == 1 else -2)
    def run(command, **kwargs):
        commands.append((command, kwargs))
    monkeypatch.setattr(rendering, '_measure_loudness', measure)
    monkeypatch.setattr(rendering, '_run', run)
    suffix = '.wav' if kind == 'audio' else '.mp4'
    _, _, report = rendering._verify_final_audio_peak(tmp_path / ('programme' + suffix), tmp_path / 'mix.wav',
        ffmpeg='synthetic-ffmpeg', output_kind=kind, duration=7200, check_continue=check)
    assert report['peak_correction_passes'] == 1 and report['true_peak_verified']
    assert all(item['duration'] == 7200 and item['check_continue'] is check for item in measured)
    assert 60 < commands[0][1]['timeout'] <= 7200 * 8
    assert commands[0][1]['check_continue'] is check
    assert ('-rf64' in commands[0][0]) == (kind == 'audio')


@pytest.mark.parametrize('format', ['mp3', 'm4a'])
def test_delivery_encode_probe_decode_and_measurement_all_receive_programme_control(tmp_path, monkeypatch, format):
    calls, probes, measurements = [], [], []
    def check():
        pass
    def run(command, **kwargs):
        calls.append(kwargs)
        if command[-1] != '-':
            Path(command[-1]).write_bytes(b'synthetic-contract-only')
        return ''
    def probe(command, **kwargs):
        probes.append(kwargs)
        return {'streams': [{'codec_type': 'audio', 'codec_name': 'mp3' if format == 'mp3' else 'aac',
            'sample_rate': '48000', 'channels': 2}], 'format': {'duration': '7200'}}
    def measure(path, ffmpeg, **kwargs):
        measurements.append(kwargs)
        return _loudness()
    monkeypatch.setattr(rendering, '_run', run)
    monkeypatch.setattr(rendering, '_probe_json', probe)
    monkeypatch.setattr(rendering, '_measure_loudness', measure)
    monkeypatch.setattr(rendering, '_ffprobe_path', lambda: 'synthetic-probe')
    import shared_artifacts
    monkeypatch.setattr(shared_artifacts, '_ffmpeg_path', lambda: 'synthetic-ffmpeg')
    result = rendering.encode_audio_delivery(tmp_path / 'mix.wav', duration=7200, format=format,
        target_lufs=-16, check_continue=check)
    assert result['report']['decode_all_frames'] == 'passed'
    assert len(calls) == 2 and all(60 < item['timeout'] <= 7200 * 8 and item['check_continue'] is check for item in calls)
    assert probes[0]['duration'] == measurements[0]['duration'] == 7200
    assert probes[0]['check_continue'] is measurements[0]['check_continue'] is check


@pytest.mark.parametrize('reported_duration', ['nan', 'inf'])
def test_delivery_rejects_nonfinite_output_duration_before_claiming_verification(tmp_path, monkeypatch,
                                                                                reported_duration):
    calls = []
    monkeypatch.setattr(rendering, '_run', lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr(rendering, '_ffprobe_path', lambda: 'synthetic-probe')
    monkeypatch.setattr(rendering, '_probe_json', lambda *args, **kwargs: {
        'streams': [{'codec_type': 'audio', 'codec_name': 'mp3', 'sample_rate': '48000', 'channels': 2}],
        'format': {'duration': reported_duration}})
    import shared_artifacts
    monkeypatch.setattr(shared_artifacts, '_ffmpeg_path', lambda: 'synthetic-ffmpeg')
    with pytest.raises(VideoEditingError, match='AUDIO_DELIVERY_VERIFICATION_FAILED'):
        rendering.encode_audio_delivery(tmp_path / 'mix.wav', duration=7200, format='mp3')
    assert len(calls) == 1


def test_native_postprocessing_and_delivery_use_installed_tools_and_preserve_original(tmp_path, monkeypatch):
    from shared_artifacts import _ffmpeg_path
    ffmpeg, ffprobe = _ffmpeg_path(), video_editing._ffprobe_path()
    if not ffmpeg or not ffprobe:
        pytest.skip('installed FFmpeg/FFprobe required')
    source = tmp_path / 'source.wav'
    subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i',
        'sine=frequency=440:sample_rate=48000:duration=1', '-af', 'volume=16',
        '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s24le', str(source)], check=True, capture_output=True, timeout=15)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    commands = []
    real_run = rendering._run
    def record(command, **kwargs):
        commands.append(command)
        return real_run(command, **kwargs)
    monkeypatch.setattr(rendering, '_run', record)
    safe, _, report = rendering._verify_final_audio_peak(source, source, ffmpeg=ffmpeg,
        output_kind='audio', duration=1)
    assert report['peak_correction_passes'] == 1 and report['true_peak_verified']
    denoised, _ = rendering._denoise_audio(safe, ffmpeg=ffmpeg, reduction=6, noise_floor=-50, duration=1)
    mastered, _ = rendering._master_audio(denoised, ffmpeg=ffmpeg, target=-16, duration=1)
    verified = rendering._probe_output(mastered, ffprobe, output_kind='audio', duration=1, has_audio=True)
    assert verified['actual_duration_sec'] == pytest.approx(1, abs=2 / 48000)
    delivery = rendering.encode_audio_delivery(mastered, duration=1, format='mp3', target_lufs=-16)
    assert delivery['report']['decode_all_frames'] == 'passed'
    wav_outputs = [command for command in commands if str(command[-1]).endswith('.wav')]
    assert len(wav_outputs) == 3
    assert all(command[command.index('-rf64') + 1] == 'auto' for command in wav_outputs)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
