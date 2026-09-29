"""Real FFmpeg render checks on tiny generated media; not user-media E2E."""
from __future__ import annotations

import array
import hashlib
import math
from pathlib import Path
import subprocess
import sys

import pytest

from lumenis.shared.content_creation import rendering, video_editing
from lumenis.shared.content_creation.video_editing import AudioMix, Timeline, VideoEditingError
from lumenis.shared.content_creation.rendering import render_timeline


SAMPLE_RATE = 48000


def _run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, capture_output=True, check=True, timeout=15, shell=False)


@pytest.fixture
def generated_media(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from shared_artifacts import _ffmpeg_path

    ffmpeg = _ffmpeg_path()
    ffprobe = video_editing._ffprobe_path()
    if not ffmpeg or not ffprobe or not Path(ffmpeg).is_file() or not Path(ffprobe).is_file():
        pytest.skip("real renderer checks require available FFmpeg and FFprobe tools")
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(tmp_path))
    source = tmp_path / "tiny-multitrack.mkv"
    _run([
        ffmpeg, "-v", "error", "-nostdin", "-n", "-filter_threads", "1",
        "-filter_complex_threads", "1", "-f", "lavfi", "-i",
        "color=c=black:s=64x64:r=30:d=1.2", "-f", "lavfi", "-i",
        "sine=frequency=440:sample_rate=48000:duration=0.9", "-itsoffset", "0.2",
        "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000:duration=0.7",
        "-map", "0:v:0", "-map", "1:a:0", "-map", "2:a:0", "-t", "1.2",
        "-c:v", "libx264", "-preset", "ultrafast", "-threads:v", "1",
        "-c:a", "pcm_s16le", "-threads:a", "1", str(source),
    ])
    return video_editing.fingerprint_local_media(str(source)), source, str(ffmpeg)


def _decode_pcm(ffmpeg: str, path: Path) -> array.array:
    result = _run([
        ffmpeg, "-v", "error", "-nostdin", "-threads", "1", "-protocol_whitelist", "file",
        "-format_whitelist", "wav", "-i", str(path), "-map", "0:a:0", "-ac", "1",
        "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", "-threads:a", "1", "-f", "s16le", "pipe:1",
    ])
    samples = array.array("h")
    samples.frombytes(result.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


def _tone_amplitude(samples: array.array, start_sec: float, end_sec: float, frequency: float) -> float:
    start = round(start_sec * SAMPLE_RATE)
    end = round(end_sec * SAMPLE_RATE)
    count = end - start
    real = 0.0
    imaginary = 0.0
    for offset, sample in enumerate(samples[start:end]):
        phase = 2 * math.pi * frequency * offset / SAMPLE_RATE
        real += sample * math.cos(phase)
        imaginary -= sample * math.sin(phase)
    return 2 * math.hypot(real, imaginary) / count


def test_multiple_video_clips_render_with_real_ffmpeg(generated_media, tmp_path: Path):
    asset, source, _ = generated_media
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    timeline = Timeline.from_assets((asset,))
    timeline = timeline.add_clip(asset.asset_id, source_out=0.5, audio_role="muted")
    timeline = timeline.add_clip(asset.asset_id, source_in=0.5, source_out=1.0, audio_role="muted")

    output = tmp_path / "two-clips.mp4"
    result = render_timeline(timeline, output)

    final_source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    print(f"multi_video={result['measurement']} source_sha256={source_hash} source_unchanged={source_hash == final_source_hash}")
    assert result["state"] == "rendered_verified"
    assert result["output_kind"] == "video"
    assert result["measurement"]["video_streams"] == 1
    assert result["measurement"]["video_frames"] == 30
    assert result["measurement"]["audio_streams"] == 0
    assert source_hash == final_source_hash
    assert output.is_file() and output.stat().st_size > 0


@pytest.mark.parametrize("music_tracks", [1, 2])
def test_ducking_lowers_only_music_during_voice_and_recovers_afterward(
    generated_media, tmp_path, music_tracks,
):
    asset, _, ffmpeg = generated_media
    timeline = Timeline.from_assets((asset,)).add_audio_track("speech", audio_role="voiceover")
    timeline = timeline.add_clip(asset.asset_id, track_id="speech", source_out=.2,
                                 timeline_start=.35, audio_stream_index=0)
    for index in range(music_tracks):
        track = f"music{index}"
        timeline = timeline.add_audio_track(track, audio_role="bgm")
        timeline = timeline.add_clip(asset.asset_id, track_id=track, source_out=.9, audio_stream_index=1)
        timeline = timeline.set_audio_mix(timeline.tracks[-1].clips[0].clip_id, AudioMix(volume=.4))

    original_output = tmp_path / "original-mix.wav"
    render_timeline(timeline, original_output, output_kind="audio")
    original = _decode_pcm(ffmpeg, original_output)
    for track in timeline.tracks:
        if track.kind == "bgm":
            timeline = timeline.set_audio_mix(track.clips[0].clip_id, AudioMix(volume=.4, ducking=True))
    ducked_output = tmp_path / "ducked-mix.wav"
    result = render_timeline(timeline, ducked_output, output_kind="audio")
    ducked = _decode_pcm(ffmpeg, ducked_output)

    assert len(ducked) == len(original) == round(.9 * SAMPLE_RATE)
    assert max(abs(sample) for sample in ducked[:round(.19 * SAMPLE_RATE)]) < 10
    for start, end in ((.25, .3), (.84, .89)):
        assert _tone_amplitude(ducked, start, end, 880) == pytest.approx(
            _tone_amplitude(original, start, end, 880), rel=.12
        )
    assert _tone_amplitude(ducked, .43, .5, 880) < .55 * _tone_amplitude(original, .43, .5, 880)
    assert _tone_amplitude(ducked, .43, .5, 440) == pytest.approx(
        _tone_amplitude(original, .43, .5, 440), rel=.04
    )
    assert result["audio_processing"]["ducked_music_clips"] == music_tracks
    assert result["audio_processing"]["loudness_normalized"] is False


def test_overlapping_tracks_have_headroom_without_clipping_or_added_delay(generated_media, tmp_path):
    asset, _, ffmpeg = generated_media
    timeline = Timeline.from_assets((asset,))
    for index in range(8):
        track = f"voice{index}"
        timeline = timeline.add_audio_track(track, audio_role="voiceover")
        timeline = timeline.add_clip(asset.asset_id, track_id=track, source_out=.9, audio_stream_index=0)
        timeline = timeline.set_audio_mix(timeline.tracks[-1].clips[0].clip_id, AudioMix(volume=2))
    output = tmp_path / "limited.wav"
    result = render_timeline(timeline, output, output_kind="audio")
    samples = _decode_pcm(ffmpeg, output)
    assert len(samples) == round(.9 * SAMPLE_RATE)
    assert .8 < max(abs(sample) for sample in samples) / 32768 <= .8913
    assert next(index for index, sample in enumerate(samples) if abs(sample) > 100) < 5
    assert result["audio_processing"]["limiter_latency_compensated"] is True
    assert result["audio_processing"]["true_peak_verified"] is True
    loudness = result["measurement"]["loudness"]
    assert loudness["state"] == "measured"
    assert math.isfinite(loudness["integrated_lufs"])
    assert -1.2 < loudness["true_peak_dbtp"] < -.8


def test_muted_audio_stays_silent_and_has_no_invented_loudness(generated_media, tmp_path):
    asset, _, _ = generated_media
    timeline = Timeline.from_assets((asset,)).add_audio_track("voice", audio_role="voiceover")
    timeline = timeline.add_clip(asset.asset_id, track_id="voice", source_out=.9, audio_stream_index=0)
    timeline = timeline.set_audio_mix(timeline.tracks[-1].clips[0].clip_id, AudioMix(volume=0))
    result = render_timeline(timeline, tmp_path / "silence.wav", output_kind="audio")
    loudness = result["measurement"]["loudness"]
    assert loudness["state"] == "silent"
    assert loudness["integrated_lufs"] is None
    assert loudness["true_peak_dbtp"] is None
    assert result["audio_processing"]["true_peak_status"] == "silent"
    assert result["audio_processing"]["peak_correction_passes"] == 0


def test_actual_aac_peak_correction_preserves_frames_and_audio_placement(generated_media, tmp_path, monkeypatch):
    asset, source, ffmpeg = generated_media
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    timeline = Timeline.from_assets([asset]).add_clip(asset.asset_id, source_out=.9, audio_role="muted")
    for index in range(8):
        track = f"voice{index}"
        timeline = timeline.add_audio_track(track, audio_role="voiceover")
        timeline = timeline.add_clip(asset.asset_id, track_id=track, source_out=.9, audio_stream_index=1)
        timeline = timeline.set_audio_mix(timeline.tracks[-1].clips[0].clip_id, AudioMix(volume=2))
    calls = []
    original_run = rendering._run
    def observe(command, **kwargs):
        calls.append(command)
        return original_run(command, **kwargs)
    monkeypatch.setattr(rendering, "_run", observe)
    output = tmp_path / "aac-final-peak.mp4"
    result = render_timeline(timeline, output)
    processing = result["audio_processing"]
    print(f"aac_peak_processing={processing} final={result['measurement']}")
    assert processing["initial_true_peak_dbtp"] > -1
    assert processing["peak_correction_passes"] == 1
    assert processing["peak_correction_db"] < 0
    assert processing["true_peak_verified"] is True
    assert result["measurement"]["loudness"]["true_peak_dbtp"] <= -1
    assert result["measurement"]["video_frames"] == 27
    assert result["measurement"]["actual_duration_sec"] == pytest.approx(.9, abs=2 / 30)
    assert result["measurement"]["stream_start_seconds"] == [0, 0]
    correction = [command for command in calls if Path(command[-1]).name == "peak-safe.mp4"]
    assert len(correction) == 1
    assert correction[0][correction[0].index("-c:v") + 1] == "copy"
    pcm = _run([ffmpeg, "-v", "error", "-nostdin", "-i", str(output), "-map", "0:a:0",
                "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", "-f", "s16le", "pipe:1"])
    samples = array.array("h", pcm.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    assert max(abs(value) for value in samples[:round(.15 * SAMPLE_RATE)]) < 100
    assert max(abs(value) for value in samples[round(.25 * SAMPLE_RATE):round(.8 * SAMPLE_RATE)]) > 1000
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_ducking_without_explicit_voiceover_is_rejected(generated_media, tmp_path):
    asset, _, _ = generated_media
    timeline = Timeline.from_assets((asset,)).add_audio_track("music", audio_role="bgm")
    timeline = timeline.add_clip(asset.asset_id, track_id="music", source_out=.9, audio_stream_index=1)
    timeline = timeline.set_audio_mix(timeline.tracks[-1].clips[0].clip_id, AudioMix(ducking=True))
    output = tmp_path / "no-voice.wav"
    with pytest.raises(VideoEditingError, match="AUDIO_DUCKING_REQUIRES_VOICEOVER"):
        render_timeline(timeline, output, output_kind="audio")
    assert not output.exists()


def test_audio_only_podcast_mixes_independent_tracks_and_preserves_offsets_and_fades(
    generated_media, tmp_path: Path,
):
    asset, source, ffmpeg = generated_media
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    timeline = Timeline.from_assets((asset,)).add_audio_track("speech", audio_role="voiceover")
    timeline = timeline.add_audio_track("music", audio_role="bgm")
    timeline = timeline.add_clip(asset.asset_id, track_id="speech", source_out=0.9, audio_stream_index=0)
    timeline = timeline.add_clip(asset.asset_id, track_id="music", source_out=0.8,
                                 timeline_start=0.1, audio_stream_index=1)
    speech_clip = timeline.tracks[1].clips[0]
    timeline = timeline.set_audio_mix(
        speech_clip.clip_id, AudioMix(volume=0.5, fade_in_sec=0.1, fade_out_sec=0.2)
    )
    music_clip = timeline.tracks[2].clips[0]
    timeline = timeline.set_audio_mix(music_clip.clip_id, AudioMix(volume=0.25))

    output = tmp_path / "podcast.wav"
    result = render_timeline(timeline, output, output_kind="audio")
    samples = _decode_pcm(ffmpeg, output)
    early_music = _tone_amplitude(samples, 0.15, 0.25, 880)
    audible_music = _tone_amplitude(samples, 0.35, 0.45, 880)
    voice_mid = _tone_amplitude(samples, 0.45, 0.55, 440)
    music_mid = _tone_amplitude(samples, 0.45, 0.55, 880)
    voice_fade = _tone_amplitude(samples, 0.82, 0.88, 440)
    voice_steady = _tone_amplitude(samples, 0.6, 0.66, 440)
    late_music = _tone_amplitude(samples, 0.82, 0.88, 880)
    final_source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    print(f"audio_only={result['measurement']} pcm_samples={len(samples)} source_sha256={source_hash} "
          f"source_unchanged={source_hash == final_source_hash} music_offset_early_late={early_music:.2f}/{audible_music:.2f} "
          f"gain_ratio_voice_music={voice_mid / music_mid:.3f} voice_fade_ratio={voice_fade / voice_steady:.3f} "
          f"late_music={late_music:.2f}")

    assert result["output_kind"] == "audio"
    assert result["measurement"]["video_streams"] == 0
    assert result["measurement"]["video_frames"] == 0
    assert result["measurement"]["audio_streams"] == 1
    assert result["measurement"]["requested_duration_sec"] == pytest.approx(0.9)
    assert len(samples) == round(0.9 * SAMPLE_RATE)
    # The delayed music source starts at 0.2 s, then its clip is placed at 0.1 s.
    assert early_music < 20
    assert audible_music > 500
    # Independent gains remain visible in the overlap; the voice track is twice the music gain.
    assert 1.6 < voice_mid / music_mid < 2.4
    # The voice fades out while the independently positioned music continues.
    assert voice_fade < voice_steady * 0.5
    assert late_music > 500
    assert source_hash == final_source_hash
    assert output.is_file() and output.stat().st_size > 0
