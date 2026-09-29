"""Bounded renderer contracts; synthetic timing checks are not user E2E."""
import array
import json
from pathlib import Path
import subprocess
import sys

import pytest

from lumenis.shared.content_creation import rendering, video_editing
from lumenis.shared.content_creation.video_editing import AudioMix, Timeline, VideoEditingError


@pytest.fixture
def media(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(tmp_path))
    monkeypatch.setattr(video_editing, "_probe_media_info", lambda _: video_editing._MediaProbe(12, True, 2))
    source = tmp_path / "speech.mp4"
    source.write_bytes(b"fixture bytes, not playable media")
    return video_editing.fingerprint_local_media(str(source))


@pytest.fixture
def render_calls(monkeypatch, tmp_path):
    import shared_artifacts

    calls = []
    suffix = ".exe" if sys.platform == "win32" else ""
    probe = tmp_path / f"ffprobe{suffix}"
    ffmpeg = tmp_path / f"ffmpeg{suffix}"
    ffmpeg.write_bytes(b"fixture only, never executed")
    monkeypatch.setattr(shared_artifacts, "_ffmpeg_path", lambda: str(ffmpeg))
    monkeypatch.setattr(rendering, "_ffprobe_path", lambda: str(probe))

    def run(command, *, cwd, timeout=60):
        if "-filter_complex_script" in command:
            graph = Path(command[command.index("-filter_complex_script") + 1]).read_text(encoding="utf-8")
        elif "-filter_complex" in command:
            graph = command[command.index("-filter_complex") + 1]
        else:
            graph = ""
        calls.append((command, graph))
        target = Path(command[-1])
        if not target.is_absolute():
            target = cwd / target
        target.write_bytes(b"fixture output, not playable media")
        return ""

    monkeypatch.setattr(rendering, "_run", run)
    monkeypatch.setattr(rendering, "_probe_output", lambda *a, **k: {"duration": k["duration"], "has_audio": k["has_audio"]})
    monkeypatch.setattr(rendering, "_measure_loudness", lambda *a, **k: {"state": "test_stub"})
    return calls


def test_trim_selected_audio_gain_fades_and_fixed_decoder_arguments(media, render_calls, tmp_path):
    timeline = Timeline.from_assets([media]).add_clip(media.asset_id, source_in=2, source_out=4, audio_stream_index=1)
    timeline = timeline.set_audio_mix(timeline.tracks[0].clips[0].clip_id, AudioMix(volume=.5, fade_in_sec=.1, fade_out_sec=.2))
    result = rendering.render_timeline(timeline, tmp_path / "film.mp4")
    command, graph = render_calls[0]
    assert "[0:a:1]" in graph and "atrim=start=2.000000:end=4.000000" in graph
    assert "asetpts=PTS-2.000000/TB,aresample=48000:first_pts=0" in graph
    assert "volume=0.500000" in graph and "afade=t=out:st=1.800000:d=0.200000" in graph
    assert "setpts=PTS-2.000000/TB" in graph
    assert command[command.index("-protocol_whitelist") + 1] == "file"
    assert command[command.index("-format_whitelist") + 1] == video_editing.MEDIA_INPUT_DEMUXERS
    assert command.index("-protocol_whitelist") < command.index("-i")
    assert "-n" in command and "-y" not in command and "concat" not in command
    assert result["measurement"] == {"duration": 2, "has_audio": True, "loudness": {"state": "test_stub"}}
    assert result["rights_state"] == "unknown" and result["publish_status"] == "not_performed"


def test_muted_clip_creates_no_audio_stream(media, render_calls, tmp_path):
    timeline = Timeline.from_assets([media]).add_clip(media.asset_id, source_out=1, audio_role="muted")
    result = rendering.render_timeline(timeline, tmp_path / "muted.mp4")
    assert "-an" in render_calls[-1][0]
    assert "[a]" not in render_calls[-1][1]
    assert result["measurement"]["has_audio"] is False


@pytest.mark.parametrize("phase", ["before", "after"])
def test_changed_source_is_rejected_without_final_output(media, render_calls, tmp_path, monkeypatch, phase):
    timeline = Timeline.from_assets([media]).add_clip(media.asset_id, source_out=1, audio_role="muted")
    original = rendering._run
    if phase == "before":
        Path(media.path).write_bytes(b"different source")
    else:
        def changed(*args, **kwargs):
            original(*args, **kwargs)
            Path(media.path).write_bytes(b"different source")
        monkeypatch.setattr(rendering, "_run", changed)
    with pytest.raises(VideoEditingError, match="SOURCE_MEDIA_CHANGED"):
        rendering.render_timeline(timeline, tmp_path / "new.mp4")
    assert not (tmp_path / "new.mp4").exists()
    assert not list(tmp_path.glob("timeline-render-*"))


def test_failure_keeps_prior_output_and_cleans_work(media, render_calls, tmp_path, monkeypatch):
    previous = tmp_path / "previous.mp4"
    previous.write_bytes(b"previous result")
    timeline = Timeline.from_assets([media]).add_clip(media.asset_id, source_out=1, audio_role="muted")
    def fail(*args, **kwargs):
        raise VideoEditingError("MEDIA_RENDER_FAILED")
    monkeypatch.setattr(rendering, "_run", fail)
    with pytest.raises(VideoEditingError, match="MEDIA_RENDER_FAILED"):
        rendering.render_timeline(timeline, tmp_path / "new.mp4")
    assert previous.read_bytes() == b"previous result"
    assert not (tmp_path / "new.mp4").exists()
    assert not list(tmp_path.glob("timeline-render-*"))


def test_output_and_unsupported_features_fail_before_process(media, render_calls, tmp_path):
    timeline = Timeline.from_assets([media]).add_clip(media.asset_id, source_out=1, audio_role="muted")
    existing = tmp_path / "previous.mp4"
    existing.write_bytes(b"keep")
    for target in (existing, Path("relative.mp4"), tmp_path / "bad.wav", Path("D:/missing-render-parent/video.mp4")):
        with pytest.raises(VideoEditingError, match="NEW_PRIVATE_TEMP_OUTPUT_REQUIRED"):
            rendering.render_timeline(timeline, target)
    with pytest.raises(VideoEditingError, match="TIMELINE_OVERLAYS_NOT_SUPPORTED_BY_RENDERER"):
        rendering.render_timeline(timeline.add_caption(0, .5, "not implemented"), tmp_path / "unsupported.mp4")
    with pytest.raises(VideoEditingError, match="AUDIO_DUCKING_REQUIRES_BACKGROUND_MUSIC"):
        ducked = timeline.set_audio_mix(timeline.tracks[0].clips[0].clip_id, AudioMix(ducking=True))
        rendering.render_timeline(ducked, tmp_path / "unsupported.mp4")
    multi = timeline.add_clip(media.asset_id, source_out=1, audio_role="muted")
    rendered = rendering.render_timeline(multi, tmp_path / "multi.mp4")
    assert rendered["output_kind"] == "video"
    video_commands = [command for command, _ in render_calls if "-frames:v" in command]
    assert len(video_commands) == 2
    assert len(render_calls) == 3
    final_graph = render_calls[-1][1]
    assert "concat=n=2:v=1:a=0" in final_graph
    for command, _ in render_calls:
        for input_index, argument in enumerate(command):
            if argument == "-i":
                assert command[input_index - 4:input_index] == [
                    "-protocol_whitelist", "file", "-format_whitelist", video_editing.MEDIA_INPUT_DEMUXERS,
                ]
    assert existing.read_bytes() == b"keep"


@pytest.mark.parametrize("failure", ["timeout", "nonzero"])
def test_process_failure_is_not_success(tmp_path, monkeypatch, failure):
    processes = []
    popen = subprocess.Popen
    def launch(command, **kwargs):
        assert kwargs["shell"] is False
        process = popen(command, **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(rendering.subprocess, "Popen", launch)
    script = "import time; time.sleep(30)" if failure == "timeout" else (
        "import sys; sys.stderr.write('private file path'); sys.exit(1)"
    )
    with pytest.raises(VideoEditingError, match="MEDIA_RENDER_PROCESS_FAILED|MEDIA_RENDER_FAILED") as error:
        rendering._run([sys.executable, "-c", script], cwd=tmp_path, timeout=.1 if failure == "timeout" else 5)
    assert "private" not in str(error.value)
    assert len(processes) == 1 and processes[0].poll() is not None


def test_cancellation_reaps_process_and_allows_a_fresh_attempt(tmp_path, monkeypatch):
    processes = []
    popen = subprocess.Popen
    def launch(*args, **kwargs):
        process = popen(*args, **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(rendering.subprocess, "Popen", launch)
    checks = 0
    def check_continue():
        nonlocal checks
        checks += 1
        if checks == 3:
            raise VideoEditingError("MEDIA_RENDER_CANCELLED")
    with pytest.raises(VideoEditingError, match="MEDIA_RENDER_CANCELLED"):
        rendering._run([sys.executable, "-c", "import time; time.sleep(30)"],
                       cwd=tmp_path, check_continue=check_continue)
    assert len(processes) == 1 and processes[0].poll() is not None
    assert rendering._run([sys.executable, "-c", "pass"], cwd=tmp_path) == ""


def test_cancelled_render_cleans_new_work_and_preserves_previous(media, render_calls, tmp_path):
    previous = tmp_path / "previous.mp4"
    previous.write_bytes(b"previous verified output")
    timeline = Timeline.from_assets([media]).add_clip(media.asset_id, source_out=1, audio_role="muted")
    def check_continue():
        if render_calls:
            raise VideoEditingError("MEDIA_RENDER_CANCELLED")
    def cancellable_run(command, *, cwd, timeout=60, check_continue=None):
        render_calls.append(command)
        check_continue()
    from unittest.mock import patch
    with patch.object(rendering, "_run", cancellable_run):
        with pytest.raises(VideoEditingError, match="MEDIA_RENDER_CANCELLED"):
            rendering.render_timeline(timeline, tmp_path / "new.mp4", check_continue=check_continue)
    assert not (tmp_path / "new.mp4").exists()
    assert not list(tmp_path.glob("timeline-render-*"))
    assert previous.read_bytes() == b"previous verified output"


@pytest.mark.parametrize("integrated,peak,state", [
    ("-18.2", "-2.0", "measured"), ("-inf", "-inf", "silent"),
    ("-inf", "-45.0", "below_integrated_gate"),
])
def test_loudness_uses_encoded_input_measurements_and_preserves_unmeasurable_state(
    tmp_path, monkeypatch, integrated, peak, state,
):
    payload = {"input_i": integrated, "input_tp": peak, "input_lra": "0.0",
               "output_i": "-24.0", "output_tp": "-1.0"}
    monkeypatch.setattr(rendering, "_run", lambda *a, **k: "ffmpeg header\n" + json.dumps(payload) + "\ntrailer")
    result = rendering._measure_loudness(tmp_path / "mix.wav", "ffmpeg")
    assert result["state"] == state
    assert result["integrated_lufs"] == (None if integrated == "-inf" else float(integrated))
    assert result["true_peak_dbtp"] == (None if peak == "-inf" else float(peak))
    assert result["target_lufs"] is None
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("payload", ["", "{}", '{"input_i":"nan","input_tp":"-1","input_lra":"0"}',
                                    '{"input_i":"-20","input_tp":"-inf","input_lra":"0"}'])
def test_invalid_loudness_is_not_accepted_as_zero(tmp_path, monkeypatch, payload):
    monkeypatch.setattr(rendering, "_run", lambda *a, **k: payload)
    with pytest.raises(VideoEditingError, match="AUDIO_LOUDNESS_MEASUREMENT_FAILED"):
        rendering._measure_loudness(tmp_path / "mix.wav", "ffmpeg")


@pytest.mark.parametrize("mutation", ["duration", "frames", "frame_count", "audio"])
def test_output_probe_rejects_unverified_media(tmp_path, monkeypatch, mutation):
    probe = {"streams": [{"codec_type": "video", "codec_name": "h264", "nb_read_frames": "30", "start_time": "0"}],
             "format": {"duration": "1", "format_name": "mov,mp4,m4a,3gp,3g2,mj2"}}
    if mutation == "duration":
        probe["format"]["duration"] = "NaN"
    elif mutation == "frames":
        probe["streams"][0]["nb_read_frames"] = "0"
    elif mutation == "frame_count":
        probe["streams"][0]["nb_read_frames"] = "29"
    elif mutation == "audio":
        probe["streams"].append({"codec_type": "audio", "codec_name": "aac", "sample_rate": "44100",
                                 "channels": 2, "start_time": "0"})
    monkeypatch.setattr(rendering.subprocess, "run", lambda *a, **k: type("Probe", (), {"stdout": json.dumps(probe)})())
    with pytest.raises(VideoEditingError, match="RENDER_OUTPUT_VERIFICATION_FAILED"):
        rendering._probe_output(tmp_path / "candidate.mp4", "ffprobe", output_kind="video", duration=1,
                                has_audio=mutation == "audio")


@pytest.fixture
def timestamped_audio_source(tmp_path_factory):
    from shared_artifacts import _ffmpeg_path

    ffmpeg = _ffmpeg_path()
    ffprobe = video_editing._ffprobe_path()
    if not ffmpeg or not ffprobe or not Path(ffmpeg).is_file() or not Path(ffprobe).is_file():
        pytest.skip("synthetic timing checks require available FFmpeg and FFprobe tools")
    source = tmp_path_factory.mktemp("audio-offset") / "zero-and-delayed.mov"
    subprocess.run(
        [ffmpeg, "-v", "error", "-nostdin", "-n", "-filter_threads", "1",
         "-filter_complex_threads", "1", "-f", "lavfi", "-i",
         "color=c=black:s=16x16:r=10:d=1", "-f", "lavfi", "-i",
         "sine=frequency=1000:sample_rate=48000:duration=0.5",
         "-itsoffset", "0.2", "-f", "lavfi", "-i",
         "sine=frequency=1000:sample_rate=48000:duration=0.5",
         "-map", "0:v:0", "-map", "1:a:0", "-map", "2:a:0",
         "-c:v", "libx264", "-preset", "ultrafast", "-threads:v", "1",
         "-c:a", "pcm_s16le", "-threads:a", "1", "-t", "1", str(source)],
        capture_output=True, check=True, timeout=10, shell=False,
    )
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "stream=codec_type,start_time", "-of", "json", str(source)], capture_output=True, check=True, timeout=10, shell=False)
    streams = json.loads(result.stdout)["streams"]
    assert [(s["codec_type"], float(s["start_time"])) for s in streams] == [("video", 0), ("audio", 0), ("audio", .2)]
    return ffmpeg, source


@pytest.mark.parametrize("stream,source_in,source_out,position,expected_first", [
    (0, 0, 1, 0, 1), (1, 0, 1, 0, 9601), (1, .1, .8, 0, 4801),
    (1, .3, .8, 0, 1), (1, 0, 1, .25, 21601), (1, 0, .1, 0, None),
])
def test_source_audio_offset_is_preserved(timestamped_audio_source, stream, source_in, source_out, position, expected_first):
    ffmpeg, source = timestamped_audio_source
    clip = video_editing.TimelineClip("timing", "synthetic-only", source_in, source_out, position, audio_stream_index=stream)
    result = subprocess.run(
        [ffmpeg, "-v", "error", "-nostdin", "-filter_threads", "1", "-threads", "1",
         "-protocol_whitelist", "file", "-format_whitelist", video_editing.MEDIA_INPUT_DEMUXERS,
         "-i", str(source), "-map", f"0:a:{stream}", "-af", rendering._audio_filter(clip),
         "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", "-threads:a", "1", "-f", "s16le", "pipe:1"],
        capture_output=True, check=True, timeout=10, shell=False,
    )
    samples = array.array("h", result.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    first = next((i for i, value in enumerate(samples) if abs(value) > 10), None)
    assert first == expected_first
    assert len(samples) == round((source_out - source_in + position) * 48000)


def test_actual_single_clip_render_retains_delayed_audio(timestamped_audio_source, tmp_path, monkeypatch):
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(timestamped_audio_source[1].parent))
    ffmpeg, source = timestamped_audio_source
    asset = video_editing.fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,)).add_clip(asset.asset_id, source_in=.1, source_out=.8, audio_stream_index=1)
    output = tmp_path / "delayed.mp4"
    result = rendering.render_timeline(timeline, output)
    assert result["measurement"]["audio_streams"] == 1
    assert result["measurement"]["video_frames"] == 21
    pcm = subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-protocol_whitelist", "file", "-format_whitelist", "mov", "-i", str(output), "-map", "0:a:0", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", "-f", "s16le", "pipe:1"], capture_output=True, check=True, timeout=10, shell=False)
    samples = array.array("h", pcm.stdout)
    if sys.byteorder != "little":
        samples.byteswap()
    assert max(abs(value) for value in samples[:2400]) < 100
    assert max(abs(value) for value in samples[7000:14000]) > 1000
