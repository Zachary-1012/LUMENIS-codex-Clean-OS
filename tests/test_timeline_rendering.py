"""Bounded renderer contracts; synthetic timing checks are not user E2E."""
import array
from dataclasses import replace
import json
from pathlib import Path
import struct
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

    def run(command, *, cwd, timeout=60, check_continue=None):
        if check_continue:
            check_continue()
        if "-filter_complex_script" in command:
            graph = Path(command[command.index("-filter_complex_script") + 1]).read_text(encoding="utf-8")
        elif "-filter_complex" in command:
            graph = command[command.index("-filter_complex") + 1]
        else:
            graph = ""
        calls.append((command, graph))
        if command[-2:] == ["null", "-"]:
            return ""
        target = Path(command[-1])
        if not target.is_absolute():
            target = cwd / target
        target.write_bytes(b"fixture output, not playable media")
        return ""

    monkeypatch.setattr(rendering, "_run", run)
    monkeypatch.setattr(rendering, "_probe_output", lambda *a, **k: {"duration": k["duration"], "has_audio": k["has_audio"]})
    monkeypatch.setattr(rendering, "_measure_loudness", lambda *a, **k: {"state": "measured", "true_peak_dbtp": -2})
    return calls


def test_long_video_encoder_has_programme_budget_and_keeps_cancel_callback(media, render_calls, tmp_path, monkeypatch):
    fixture_run = rendering._run
    final_calls = []
    def record_run(command, **kwargs):
        if Path(command[-1]).name == "media.mp4":
            final_calls.append(kwargs)
        return fixture_run(command, **kwargs)
    monkeypatch.setattr(rendering, "_run", record_run)
    timeline = Timeline.from_assets((media,), "16:9")
    for _ in range(6):
        timeline = timeline.add_clip(media.asset_id, source_in=0, source_out=12, audio_role="muted")
    checks = []
    def check_continue():
        checks.append(True)
    rendering.render_timeline(timeline, tmp_path / "long-video.mp4", check_continue=check_continue)
    assert len(final_calls) == 1 and checks
    assert timeline.duration_sec <= final_calls[0]["timeout"] <= timeline.duration_sec * 8
    assert final_calls[0]["check_continue"] is check_continue


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
    assert result["measurement"] == {"duration": 2, "has_audio": True, "loudness": {"state": "measured", "true_peak_dbtp": -2}}
    assert result["rights_state"] == "unknown" and result["publish_status"] == "not_performed"


def test_muted_clip_creates_no_audio_stream(media, render_calls, tmp_path):
    timeline = Timeline.from_assets([media]).add_clip(media.asset_id, source_out=1, audio_role="muted")
    result = rendering.render_timeline(timeline, tmp_path / "muted.mp4")
    assert "-an" in render_calls[-1][0]
    assert "[a]" not in render_calls[-1][1]
    assert result["measurement"]["has_audio"] is False
    assert result["audio_processing"]["true_peak_verified"] is False
    assert result["audio_processing"]["true_peak_status"] == "not_applicable"


@pytest.mark.parametrize("output_kind", ["video", "audio"])
def test_encoded_peak_correction_uses_lossless_mix_once_and_rechecks_final_file(
    media, render_calls, tmp_path, monkeypatch, output_kind,
):
    timeline = Timeline.from_assets([media])
    track = "video"
    if output_kind == "audio":
        timeline = timeline.add_audio_track("voice", audio_role="voiceover")
        track = "voice"
    timeline = timeline.add_clip(media.asset_id, track_id=track, source_out=1, audio_stream_index=0)
    measurements = []
    def measure(path, *args, **kwargs):
        measurements.append(path)
        return {"state": "measured", "true_peak_dbtp": 2.04 if len(measurements) == 1 else -1.48}
    monkeypatch.setattr(rendering, "_measure_loudness", measure)
    suffix = ".mp4" if output_kind == "video" else ".wav"
    result = rendering.render_timeline(timeline, tmp_path / ("safe" + suffix), output_kind=output_kind)
    assert len(measurements) == 2 and measurements[0] != measurements[1]
    correction = render_calls[-1][0]
    inputs = [Path(correction[index + 1]).name for index, value in enumerate(correction) if value == "-i"]
    assert inputs == (["media.mp4", "audio.wav"] if output_kind == "video" else ["audio.wav"])
    assert "volume=-3.540000dB" in correction[correction.index("-af") + 1]
    assert "loudnorm" not in correction[correction.index("-af") + 1]
    if output_kind == "video":
        assert correction[correction.index("-c:v") + 1] == "copy"
    assert "-n" in correction and "-y" not in correction
    assert result["measurement"]["loudness"]["true_peak_dbtp"] == -1.48
    processing = result["audio_processing"]
    assert processing["true_peak_verified"] is True
    assert processing["initial_true_peak_dbtp"] == 2.04
    assert processing["peak_correction_db"] == pytest.approx(-3.54)
    assert processing["peak_correction_passes"] == 1
    assert processing["final_true_peak_limit_dbtp"] == -1
    assert processing["loudness_normalized"] is False


@pytest.mark.parametrize("peak,state", [(-1, "measured"), (-45, "below_integrated_gate"), (None, "silent")])
def test_safe_encoded_audio_is_not_boosted_or_reencoded(media, render_calls, tmp_path, monkeypatch, peak, state):
    timeline = Timeline.from_assets([media]).add_clip(media.asset_id, source_out=1, audio_stream_index=0)
    measurements = []
    def measure(path, *args, **kwargs):
        measurements.append(path)
        return {"state": state, "true_peak_dbtp": peak}
    monkeypatch.setattr(rendering, "_measure_loudness", measure)
    result = rendering.render_timeline(timeline, tmp_path / "unchanged.mp4")
    assert len(measurements) == 1 and len(render_calls) == 3
    assert result["audio_processing"]["peak_correction_passes"] == 0
    assert result["audio_processing"]["peak_correction_db"] == 0
    assert result["audio_processing"]["true_peak_verified"] is True
    assert result["measurement"]["loudness"]["true_peak_dbtp"] == peak


@pytest.mark.parametrize("failure", ["still_over", "measurement", "cancelled"])
def test_failed_peak_correction_never_retries_or_replaces_previous_output(
    media, render_calls, tmp_path, monkeypatch, failure,
):
    timeline = Timeline.from_assets([media]).add_clip(media.asset_id, source_out=1, audio_stream_index=0)
    previous = tmp_path / "previous.mp4"
    previous.write_bytes(b"previous verified output")
    measurements = []
    def measure(path, *args, **kwargs):
        measurements.append(path)
        if len(measurements) == 2 and failure == "measurement":
            raise VideoEditingError("AUDIO_LOUDNESS_MEASUREMENT_FAILED")
        return {"state": "measured", "true_peak_dbtp": 2.04}
    monkeypatch.setattr(rendering, "_measure_loudness", measure)
    original_run = rendering._run
    def run(command, *, check_continue=None, **kwargs):
        if check_continue:
            check_continue()
        return original_run(command, **kwargs)
    monkeypatch.setattr(rendering, "_run", run)
    def check_continue():
        if failure == "cancelled" and measurements:
            raise VideoEditingError("MEDIA_RENDER_CANCELLED")
    with pytest.raises(VideoEditingError, match={
        "still_over": "AUDIO_TRUE_PEAK_VERIFICATION_FAILED",
        "measurement": "AUDIO_LOUDNESS_MEASUREMENT_FAILED",
        "cancelled": "MEDIA_RENDER_CANCELLED",
    }[failure]):
        rendering.render_timeline(timeline, tmp_path / "new.mp4", check_continue=check_continue)
    assert len(measurements) <= 2 and len(render_calls) <= 4
    assert previous.read_bytes() == b"previous verified output"
    assert not (tmp_path / "new.mp4").exists()
    assert not list(tmp_path.glob("timeline-render-*"))


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
    with pytest.raises(VideoEditingError, match="OVERLAYS_REQUIRE_VIDEO_OUTPUT"):
        rendering.render_timeline(timeline.add_caption(0, .5, "caption"), tmp_path / "unsupported.wav", output_kind="audio")
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


def test_registered_artifact_workspace_outside_os_temp(media, render_calls, tmp_path, monkeypatch):
    root = tmp_path / "artifacts"
    workspace = root / "content-project-owned"
    workspace.mkdir(parents=True)
    os_temp = tmp_path / "os-temp"
    os_temp.mkdir()
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(root))
    monkeypatch.setattr(rendering.tempfile, "gettempdir", lambda: str(os_temp))
    timeline = Timeline.from_assets([media]).add_clip(media.asset_id, source_out=1, audio_role="muted")
    output = workspace / "media.mp4"
    result = rendering.render_timeline(timeline, output, artifact_workspace=workspace)
    assert result["state"] == "rendered_verified" and output.is_file()
    assert not list(workspace.glob("timeline-render-*"))


@pytest.mark.parametrize("case", ["no_binding", "root", "foreign", "sibling", "nested", "existing", "wrong_suffix"])
def test_artifact_workspace_does_not_grant_arbitrary_output(media, render_calls, tmp_path, monkeypatch, case):
    root = tmp_path / "artifacts"
    workspace = root / "content-project-owned"
    workspace.mkdir(parents=True)
    os_temp = tmp_path / "os-temp"
    os_temp.mkdir()
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(root))
    monkeypatch.setattr(rendering.tempfile, "gettempdir", lambda: str(os_temp))
    output = workspace / "media.mp4"
    bound = workspace
    if case == "no_binding":
        bound = None
    elif case == "root":
        bound = root
        output = root / "media.mp4"
    elif case == "foreign":
        bound = tmp_path / "content-project-foreign"
        bound.mkdir()
        output = bound / "media.mp4"
    elif case == "sibling":
        sibling = root / "content-project-other"
        sibling.mkdir()
        output = sibling / "media.mp4"
    elif case == "nested":
        nested = workspace / "nested"
        nested.mkdir()
        output = nested / "media.mp4"
    elif case == "existing":
        output.write_bytes(b"preserve previous output")
    else:
        output = workspace / "media.wav"
    timeline = Timeline.from_assets([media]).add_clip(media.asset_id, source_out=1, audio_role="muted")
    with pytest.raises(VideoEditingError, match="NEW_PRIVATE_TEMP_OUTPUT_REQUIRED"):
        rendering.render_timeline(timeline, output, artifact_workspace=bound)
    assert render_calls == []
    if case == "existing":
        assert output.read_bytes() == b"preserve previous output"


@pytest.fixture
def caption_font(tmp_path, monkeypatch):
    font = tmp_path / "installed-font.ttc"
    font.write_bytes(b"unit fixture only")
    monkeypatch.setattr(rendering, "CAPTION_FONT", font)
    monkeypatch.setattr(rendering, "os", type("Host", (), {"name": "nt"}))
    monkeypatch.setattr(rendering, "_verify_caption_glyphs", lambda _: None)


def overlay_filters(timeline, tmp_path, **kwargs):
    return rendering._overlay_filters(timeline, duration=1, width=1280, height=720,
                                      ffmpeg="unit-ffmpeg", work=tmp_path, **kwargs)


def test_caption_literal_files_preserve_newlines_and_never_enter_graph(
    media, render_calls, caption_font, tmp_path,
):
    literal = "中文 English\n\n%{pts}:;[]'\\\nmovie=http://invalid.test/"
    timeline = Timeline.from_assets((media,)).add_caption(.201, .799, literal)
    graph = overlay_filters(timeline, tmp_path)
    assert (tmp_path / "caption-000.txt").read_text(encoding="utf-8") == literal
    assert len(graph) == 1 and "expansion=none:reload=0" in graph[0]
    assert "gte(n,7)*lt(n,24)" in graph[0]
    for user_text in ("中文", "%{pts}", "invalid.test", "movie="):
        assert user_text not in graph[0]
    assert "textfile=caption-000.txt" in graph[0]
    assert list(tmp_path.glob("*.mp4")) == [Path(media.path)]


def test_wrapping_preserves_spaces_blank_lines_and_combining_marks(media, render_calls, caption_font, tmp_path):
    literal = "界" * 27 + "e\u0301 " + "English\n\n尾 "
    timeline = Timeline.from_assets((media,)).add_caption(0, 1, literal)
    timeline = replace(timeline, overlays=(replace(timeline.overlays[0], text=literal),))
    overlay_filters(timeline, tmp_path)
    wrapped = (tmp_path / "caption-000.txt").read_text(encoding="utf-8")
    assert wrapped == "界" * 27 + "e\u0301\n English\n\n尾 "
    assert wrapped.replace("\n", "") == literal.replace("\n", "")


@pytest.mark.parametrize("text,start,end,error", [
    ("caption", .001, .002, "OVERLAY_SHORTER_THAN_OUTPUT_FRAME"),
    ("caption", 0, 1.01, "OVERLAY_EXTENDS_BEYOND_VIDEO"),
    ("a\x00b", 0, 1, "OVERLAY_TEXT_NOT_SUPPORTED"),
    ("a\tb", 0, 1, "OVERLAY_TEXT_NOT_SUPPORTED"),
    ("a\ud800", 0, 1, "OVERLAY_TEXT_NOT_SUPPORTED"),
    ("x" * 1025, 0, 1, "OVERLAY_TEXT_NOT_SUPPORTED"),
    ("x" * 113, 0, 1, "OVERLAY_LAYOUT_EXCEEDS_FOUR_LINES"),
    ("a\n\n\n\nb", 0, 1, "OVERLAY_LAYOUT_EXCEEDS_FOUR_LINES"),
])
def test_invalid_overlay_is_explicit_and_runs_no_process(media, render_calls, tmp_path, text, start, end, error):
    timeline = Timeline.from_assets((media,)).add_caption(start, end, text)
    with pytest.raises(VideoEditingError, match=error):
        overlay_filters(timeline, tmp_path)
    assert render_calls == [] and not list(tmp_path.glob("caption-*.txt"))


def test_overlap_count_and_nonstring_are_not_silently_rendered(media, render_calls, tmp_path):
    base = Timeline.from_assets((media,)).add_caption(0, .7, "first")
    overlap = base.add_caption(.6, 1, "second")
    for timeline, error in (
        (overlap, "OVERLAY_SAME_KIND_OVERLAP_NOT_SUPPORTED"),
        (replace(base, overlays=base.overlays * 65), "OVERLAY_COUNT_EXCEEDED"),
        (replace(base, overlays=(replace(base.overlays[0], text=123),)), "OVERLAY_TEXT_NOT_SUPPORTED"),
    ):
        with pytest.raises(VideoEditingError, match=error):
            overlay_filters(timeline, tmp_path)
    assert render_calls == []


@pytest.mark.parametrize("failure", ["font", "platform", "filter", "cancel"])
def test_overlay_unavailable_or_cancel_preserves_previous_and_cleans_work(
    media, render_calls, caption_font, tmp_path, monkeypatch, failure,
):
    timeline = Timeline.from_assets((media,)).add_clip(media.asset_id, source_out=1, audio_role="muted")
    timeline = timeline.add_caption(.2, .8, "字幕")
    previous = tmp_path / "previous.mp4"
    previous.write_bytes(b"keep verified film")
    sentinel = VideoEditingError("MEDIA_RENDER_FAILED")
    if failure == "font":
        monkeypatch.setattr(rendering, "CAPTION_FONT", tmp_path / "not-installed.ttc")
    elif failure == "platform":
        monkeypatch.setattr(rendering, "os", type("Host", (), {"name": "posix"}))
    def run(*args, **kwargs):
        if failure == "cancel":
            kwargs["check_continue"]()
        raise VideoEditingError("MEDIA_RENDER_FAILED")
    monkeypatch.setattr(rendering, "_run", run)
    checks = 0
    def check():
        nonlocal checks
        checks += 1
        if failure == "cancel" and checks == 3:
            raise sentinel
    with pytest.raises(VideoEditingError) as result:
        rendering.render_timeline(timeline, tmp_path / "new.mp4", check_continue=check)
    if failure == "cancel":
        assert result.value is sentinel
    else:
        assert str(result.value) == ("CAPTION_FONT_UNAVAILABLE" if failure == "font"
                                     else "CAPTION_RENDER_UNAVAILABLE")
    assert previous.read_bytes() == b"keep verified film"
    assert not (tmp_path / "new.mp4").exists()
    assert not list(tmp_path.glob("timeline-render-*"))


def test_caption_and_text_follow_concat_without_changing_muted_audio(media, render_calls, caption_font, tmp_path):
    timeline = Timeline.from_assets((media,), format_ratio="16:9").add_clip(media.asset_id, source_out=.5, audio_role="muted")
    timeline = timeline.add_clip(media.asset_id, source_out=.5, audio_role="muted")
    timeline = timeline.add_caption(.2, .8, "字幕").add_text_overlay(.2, .8, "Title")
    result = rendering.render_timeline(timeline, tmp_path / "caption.mp4")
    graph = render_calls[-1][1]
    assert "concat=n=2:v=1:a=0,drawtext=" in graph
    assert graph.count("drawtext=") == 2 and graph.count("gte(n,6)*lt(n,24)") == 2
    assert "y=h-text_h-30" in graph and "y=30" in graph
    assert "-an" in render_calls[-1][0] and not result["measurement"]["has_audio"]
    assert result["overlay_processing"]["count"] == 2
    assert result["overlay_processing"]["profile"] == "literal-cjk-installed-font-v2"
    assert len(result["overlay_processing"]["font_sha256"]) == 64
    assert result["renderer"] == "lumenis-timeline-4"


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


@pytest.mark.parametrize("phase", ["before", "during", "after"])
@pytest.mark.parametrize("error_kind", ["permission", "os", "subprocess"])
def test_callback_error_identity_survives_process_boundary(tmp_path, monkeypatch, phase, error_kind):
    error = {"permission": PermissionError("access revoked"), "os": OSError("callback failure"),
             "subprocess": subprocess.TimeoutExpired("callback", 1)}[error_kind]
    processes = []
    original_popen = subprocess.Popen
    def launch(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(rendering.subprocess, "Popen", launch)
    checks = 0
    def check_continue():
        nonlocal checks
        checks += 1
        if checks == (1 if phase == "before" else 3):
            raise error
    script = "import time; time.sleep(5)" if phase == "during" else "pass"
    with pytest.raises(type(error)) as caught:
        rendering._run([sys.executable, "-c", script], cwd=tmp_path, check_continue=check_continue)
    assert caught.value is error
    assert len(processes) == (0 if phase == "before" else 1)
    assert all(process.poll() is not None for process in processes)
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


def _font_with_cmap(subtable, *, collection=False):
    """Minimal synthetic font directory, not a distributable typeface."""
    prefix = struct.pack(">4sIII", b"ttcf", 0x10000, 1, 16) if collection else b""
    cmap = struct.pack(">HHHHI", 0, 1, 3, 10 if subtable[:2] == b"\x00\x0c" else 1, 12) + subtable
    header = struct.pack(">IHHHH", 0x10000, 1, 0, 0, 0)
    directory = struct.pack(">4sIII", b"cmap", 0, len(prefix) + 28, len(cmap))
    return prefix + header + directory + cmap


@pytest.mark.parametrize("collection", [False, True])
@pytest.mark.parametrize("indirect", [False, True])
def test_caption_font_cmap4_respects_delta_range_and_missing_glyph(tmp_path, monkeypatch, collection, indirect):
    # Two segments: A..B and the required sentinel. In the indirect branch B is missing.
    subtable = struct.pack(">7H", 4, 36 if indirect else 32, 0, 4, 4, 1, 0)
    subtable += struct.pack(">2HH2H2h2H", 66, 65535, 0, 65, 65535,
                            1 if indirect else -64, 1, 4 if indirect else 0, 0)
    if indirect:
        subtable += struct.pack(">2H", 5, 0)
    font = tmp_path / "synthetic.ttf"
    font.write_bytes(_font_with_cmap(subtable, collection=collection))
    monkeypatch.setattr(rendering, "CAPTION_FONT", font)
    rendering._verify_caption_glyphs("A\n")
    if indirect:
        with pytest.raises(VideoEditingError, match="OVERLAY_GLYPH_UNAVAILABLE"):
            rendering._verify_caption_glyphs("B")
    else:
        rendering._verify_caption_glyphs("AB")
    with pytest.raises(VideoEditingError, match="OVERLAY_GLYPH_UNAVAILABLE"):
        rendering._verify_caption_glyphs("C")


def test_caption_font_cmap12_and_malformed_directory_fail_closed(tmp_path, monkeypatch):
    subtable = struct.pack(">HHIII", 12, 0, 40, 0, 2)
    subtable += struct.pack(">6I", 65, 65, 0, 0x1F600, 0x1F600, 7)
    font = tmp_path / "synthetic.ttc"
    font.write_bytes(_font_with_cmap(subtable, collection=True))
    monkeypatch.setattr(rendering, "CAPTION_FONT", font)
    rendering._verify_caption_glyphs("\U0001f600")
    with pytest.raises(VideoEditingError, match="OVERLAY_GLYPH_UNAVAILABLE"):
        rendering._verify_caption_glyphs("A")
    for broken in (b"", b"ttcf", font.read_bytes()[:-2]):
        font.write_bytes(broken)
        with pytest.raises(VideoEditingError, match="CAPTION_FONT_UNAVAILABLE"):
            rendering._verify_caption_glyphs("A")


@pytest.fixture
def installed_caption_runtime(timestamped_audio_source, monkeypatch):
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(timestamped_audio_source[1].parent))
    if not rendering.CAPTION_FONT.is_file():
        pytest.skip("caption profile requires an installed verified CJK font")
    return timestamped_audio_source


def _audio_packets(ffprobe, path):
    result = subprocess.run(
        [ffprobe, "-v", "error", "-protocol_whitelist", "file", "-format_whitelist", "mov",
         "-select_streams", "a:0", "-show_packets", "-show_data_hash", "sha256",
         "-show_entries", "packet=pts,dts,duration,size,data_hash", "-of", "json", str(path)],
        capture_output=True, check=True, timeout=15, shell=False,
    )
    return json.loads(result.stdout)["packets"]


def test_actual_caption_filter_is_literal_and_frame_bounded(installed_caption_runtime, tmp_path, monkeypatch):
    ffmpeg, source = installed_caption_runtime
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(source.parent))
    asset = video_editing.fingerprint_local_media(str(source))
    literal = "中文 English\n%{pts}:;[]'\\\nmovie=http://invalid.test/"
    timeline = Timeline.from_assets((asset,), "16:9").add_caption(.201, .799, literal)
    filters = rendering._overlay_filters(timeline, duration=1, width=320, height=180,
                                         ffmpeg=ffmpeg, work=tmp_path)
    assert (tmp_path / "caption-000.txt").read_text(encoding="utf-8") == literal
    command = [ffmpeg, "-v", "error", "-nostdin", "-filter_threads", "1", "-f", "lavfi",
               "-i", "color=c=black:s=320x180:r=30:d=1"]
    output = ["-pix_fmt", "gray", "-f", "rawvideo", "pipe:1"]
    baseline = subprocess.run(command + output, cwd=tmp_path, capture_output=True, check=True, timeout=15).stdout
    captioned = subprocess.run(command + ["-vf", ",".join(filters)] + output,
                               cwd=tmp_path, capture_output=True, check=True, timeout=15).stdout
    frame_size = 320 * 180
    assert len(baseline) == len(captioned) == frame_size * 30
    for frame in range(30):
        selection = slice(frame * frame_size, (frame + 1) * frame_size)
        assert (baseline[selection] != captioned[selection]) is (7 <= frame < 24)


def test_actual_caption_export_reopen_keeps_audio_and_duration(installed_caption_runtime, tmp_path, monkeypatch):
    ffmpeg, source = installed_caption_runtime
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(source.parent))
    asset = video_editing.fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,), "16:9")
    timeline = timeline.add_clip(asset.asset_id, source_out=.5, audio_stream_index=1)
    timeline = timeline.add_clip(asset.asset_id, source_in=.5, source_out=1, audio_stream_index=1)
    baseline = tmp_path / "baseline.mp4"
    before = rendering.render_timeline(timeline, baseline)
    timeline = timeline.add_caption(.2, .8, "中文 English").add_text_overlay(.2, .8, "%{pts}:;[]'\\")
    reopened = Timeline.from_dict(json.loads(json.dumps(timeline.to_dict())), assets=(asset,))
    assert reopened.to_dict() == timeline.to_dict()
    captioned = tmp_path / "captioned.mp4"
    after = rendering.render_timeline(reopened, captioned)
    assert before["measurement"] == after["measurement"]
    assert after["measurement"]["video_frames"] == 30
    assert after["audio_processing"]["true_peak_verified"] is True
    assert after["rights_state"] == "unknown" and after["publish_status"] == "not_performed"
    packets = _audio_packets(video_editing._ffprobe_path(), baseline)
    assert packets and packets == _audio_packets(video_editing._ffprobe_path(), captioned)
    assert not list(tmp_path.glob("timeline-render-*"))
    muted = Timeline.from_assets((asset,), "16:9").add_clip(asset.asset_id, source_out=.5, audio_role="muted")
    result = rendering.render_timeline(muted.add_caption(0, .5, "静音"), tmp_path / "muted.mp4")
    assert result["measurement"]["audio_streams"] == 0
    assert result["measurement"]["video_frames"] == 15


@pytest.mark.parametrize("text", ["\U0001d11e", "\U0001f600"])
def test_installed_font_missing_glyph_never_publishes_output(installed_caption_runtime, tmp_path, monkeypatch, text):
    _, source = installed_caption_runtime
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(source.parent))
    asset = video_editing.fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,)).add_clip(asset.asset_id, source_out=1, audio_stream_index=0)
    output = tmp_path / "unsupported.mp4"
    with pytest.raises(VideoEditingError, match="OVERLAY_GLYPH_UNAVAILABLE"):
        rendering.render_timeline(timeline.add_caption(0, 1, text), output)
    assert not output.exists() and not list(tmp_path.glob("timeline-render-*"))


def test_dissolve_uses_centred_handles_and_preserves_cuts_caption_and_audio(media, render_calls, caption_font, tmp_path):
    timeline = Timeline.from_assets((media,), "16:9")
    for _ in range(3):
        timeline = timeline.add_clip(media.asset_id, source_in=2, source_out=4, audio_stream_index=0)
    first, second, third = timeline.tracks[0].clips
    timeline = timeline.add_transition(first.clip_id, second.clip_id, duration_sec=.31, reason="visual continuity")
    timeline = timeline.add_transition(second.clip_id, third.clip_id, transition_type="cut", duration_sec=0, reason="")
    result = rendering.render_timeline(timeline.add_caption(2, 3, "Same timing"), tmp_path / "dissolve.mp4")
    video = [command for command, _ in render_calls if "-frames:v" in command and command[-1].endswith(".mp4")]
    assert [command[command.index("-frames:v") + 1] for command in video] == ["65", "64", "60"]
    assert [command[command.index("-ss") + 1] for command in video] == ["2.000000", "1.866667", "2.000000"]
    graph = next(graph for _, graph in render_calls if "xfade=" in graph)
    assert "xfade=transition=fade:duration=0.300000:offset=1.866667" in graph
    assert "concat=n=2:v=1:a=0,settb=1/30,setpts=PTS-STARTPTS,fps=30" in graph and "trim=end_frame=180" in graph
    assert "gte(n,60)*lt(n,90)" in graph
    audio_graph = next(graph for _, graph in render_calls if "atrim=" in graph)
    assert audio_graph.count("atrim=start=2.000000:end=4.000000") == 3
    assert "acrossfade" not in audio_graph
    applied = result["transition_processing"]["applied"]
    assert len(applied) == 1 and applied[0]["start_frame"] == 56 and applied[0]["end_frame"] == 65
    assert applied[0]["requested_duration_sec"] == .31 and applied[0]["duration_frames"] == 9
    assert result["transition_processing"]["visual_only"] is True


@pytest.mark.parametrize("failure,error", [
    ("handles", "TRANSITION_MEDIA_HANDLES_UNAVAILABLE"),
    ("subframe", "TRANSITION_SHORTER_THAN_OUTPUT_FRAME"),
    ("duplicate", "TRANSITION_BOUNDARY_CONFLICT"),
    ("reverse", "TRANSITION_REQUIRES_ADJACENT_VIDEO_CLIPS"),
    ("unknown", "TRANSITION_RENDER_NOT_SUPPORTED"),
])
def test_transition_preflight_failure_starts_no_encoder_and_preserves_old_output(media, render_calls, tmp_path, failure, error):
    timeline = Timeline.from_assets((media,)).add_clip(media.asset_id, source_in=2, source_out=4, audio_role="muted")
    timeline = timeline.add_clip(media.asset_id, source_in=0 if failure == "handles" else 5, source_out=2 if failure == "handles" else 7, audio_role="muted")
    first, second = timeline.tracks[0].clips
    timeline = timeline.add_transition(first.clip_id, second.clip_id,
        transition_type="wipe" if failure == "unknown" else "dissolve",
        duration_sec=.01 if failure == "subframe" else .3, reason="reviewed edit")
    if failure == "duplicate":
        timeline = timeline.add_transition(first.clip_id, second.clip_id, transition_type="cut", duration_sec=0, reason="")
    elif failure == "reverse":
        transition = timeline.transitions[0]
        timeline = replace(timeline, transitions=(replace(transition, from_clip=second.clip_id, to_clip=first.clip_id),))
    previous = tmp_path / "previous.mp4"
    previous.write_bytes(b"previous output")
    with pytest.raises(VideoEditingError, match=error):
        rendering.render_timeline(timeline, tmp_path / "new.mp4")
    assert not render_calls and not (tmp_path / "new.mp4").exists()
    assert previous.read_bytes() == b"previous output" and not list(tmp_path.glob("timeline-render-*"))


@pytest.mark.parametrize("boundaries", [(0,), (1,), (0, 1)])
def test_real_dissolve_blends_frames_without_shortening_mixed_cut_sequence(tmp_path, monkeypatch, boundaries):
    from shared_artifacts import _ffmpeg_path
    ffmpeg = _ffmpeg_path()
    probe = video_editing._ffprobe_path()
    if not ffmpeg or not probe:
        pytest.skip("transition frame contract requires FFmpeg and FFprobe")
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(tmp_path))
    assets = []
    for color in ("red", "blue", "green"):
        source = tmp_path / (color + ".mp4")
        subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-n", "-f", "lavfi", "-i",
                        f"color=c={color}:s=32x32:r=30:d=3", "-c:v", "libx264", "-threads:v", "1",
                        "-pix_fmt", "yuv420p", str(source)], capture_output=True, check=True, timeout=15)
        assets.append(video_editing.fingerprint_local_media(str(source)))
    timeline = Timeline.from_assets(assets, "16:9")
    for asset in assets:
        timeline = timeline.add_clip(asset.asset_id, source_in=1, source_out=2, audio_role="muted")
    clips = timeline.tracks[0].clips
    for index in boundaries:
        timeline = timeline.add_transition(clips[index].clip_id, clips[index + 1].clip_id,
                                           duration_sec=.4, reason="synthetic frame contract")
    output = tmp_path / "blend.mp4"
    result = rendering.render_timeline(timeline, output)
    assert result["measurement"]["video_frames"] == 90
    assert result["measurement"]["audio_streams"] == 0
    frames = subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-i", str(output), "-vf",
                            "select='eq(n,10)+eq(n,30)+eq(n,50)+eq(n,60)+eq(n,70)',crop=16:16:(iw-16)/2:(ih-16)/2,scale=1:1", "-fps_mode", "vfr",
                            "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"], capture_output=True, check=True, timeout=15).stdout
    assert len(frames) == 15
    red, first_cut, blue, second_cut, green = [tuple(frames[index:index + 3]) for index in range(0, 15, 3)]
    assert red[0] > 200 and red[2] < 20 and blue[2] > 200 and blue[0] < 20
    if 0 in boundaries:
        assert 70 < first_cut[0] < 180 and 70 < first_cut[2] < 180 and first_cut[1] < 20
    else:
        assert first_cut[2] > 200 and first_cut[0] < 20
    if 1 in boundaries:
        assert 30 < second_cut[1] < 90 and 70 < second_cut[2] < 180 and second_cut[0] < 20
    else:
        assert second_cut[1] > 90 and second_cut[0] < 20 and second_cut[2] < 20
    assert green[1] > 90 and green[0] < 20 and green[2] < 20
    reopened = Timeline.from_dict(timeline.to_dict(), assets=[video_editing.fingerprint_local_media(asset.path) for asset in assets])
    assert reopened.transitions == timeline.transitions
    assert not list(tmp_path.glob("timeline-render-*"))


@pytest.fixture
def wide_caption_measurement(render_calls, monkeypatch):
    fixture_run = rendering._run
    def run(command, **kwargs):
        report = fixture_run(command, **kwargs)
        if "-vf" in command and "print(text_w)" in command[command.index("-vf") + 1]:
            return "[Eval @ 001] 835.000000\n[Eval @ 001] 190.000000\n[Eval @ 001] 835.000000\n"
        return report
    monkeypatch.setattr(rendering, "_run", run)


def test_wide_caption_explicit_profile_preserves_full_literal_and_four_line_guard(
    media, render_calls, caption_font, wide_caption_measurement, tmp_path,
):
    literal = "Three recorded answers would be returned to their speakers before the final edit. A complete transcript would keep another way into the work."
    timeline = Timeline.from_assets((media,), "16:9").add_caption(0, 1, literal, layout_profile="literal-wide-720p-v2")
    readback = []
    filters = rendering._overlay_filters(timeline, duration=1, width=1280, height=720,
                                         ffmpeg="unit-ffmpeg", work=tmp_path, layout_readback=readback)
    wrapped = (tmp_path / "caption-000.txt").read_text(encoding="utf-8")
    assert wrapped.replace("\n", "") == literal
    assert len(wrapped.split("\n")) == 4 and "fontsize=35" in filters[0] and "line_spacing=8" in filters[0]
    assert all(line.endswith(" ") for line in wrapped.split("\n")[:-1])
    assert readback[0]["text_width_px"] == 835 and readback[0]["text_height_px"] == 190
    assert "returned" not in filters[0] and "expansion=none:reload=0" in filters[0]
    legacy = Timeline.from_assets((media,)).add_caption(0, 1, literal)
    with pytest.raises(VideoEditingError, match="OVERLAY_LAYOUT_EXCEEDS_FOUR_LINES"):
        overlay_filters(legacy, tmp_path)
    over_limit = Timeline.from_assets((media,), "16:9").add_caption(0, 1, "a" * 193,
        layout_profile="literal-wide-720p-v2")
    with pytest.raises(VideoEditingError, match="OVERLAY_LAYOUT_EXCEEDS_FOUR_LINES"):
        overlay_filters(over_limit, tmp_path)


@pytest.mark.parametrize("dimensions", [(720, 1280), (320, 180), (810, 1080)])
def test_wide_caption_rejects_other_frame_sizes_before_any_process(media, render_calls, tmp_path, dimensions):
    timeline = Timeline.from_assets((media,), "16:9").add_caption(0, 1, "text", layout_profile="literal-wide-720p-v2")
    with pytest.raises(VideoEditingError, match="CAPTION_LAYOUT_REQUIRES_1280_720"):
        rendering._overlay_filters(timeline, duration=1, width=dimensions[0], height=dimensions[1],
                                   ffmpeg="unit-ffmpeg", work=tmp_path)
    assert not render_calls and not list(tmp_path.glob("caption-*.txt"))


@pytest.mark.parametrize("box", [(1680, 38), (1205, 190), (835, 201)])
def test_wide_caption_actual_pixel_bounds_reject_overflow(media, render_calls, caption_font, tmp_path, monkeypatch, box):
    monkeypatch.setattr(rendering, "_measure_caption_box", lambda *a, **k: box)
    timeline = Timeline.from_assets((media,), "16:9").add_caption(0, 1, "text", layout_profile="literal-wide-720p-v2")
    with pytest.raises(VideoEditingError, match="CAPTION_LAYOUT_EXCEEDS_PIXEL_BOUNDS"):
        overlay_filters(timeline, tmp_path)
    assert list(tmp_path.glob("*.mp4")) == [Path(media.path)]
    assert not list(tmp_path.glob("timeline-render-*"))


@pytest.mark.parametrize("report", ["", "[Eval @ 001] 42.000000\n", "[Eval @ 001] nan\n",
    "[Eval @ 001] ...\n", "[Eval @ 001] e\n",
    "[Eval @ 001] 835.000000\n[Eval @ 001] 190.000000\n[Eval @ 001] 836.000000\n",
    "[Eval @ 001] 835.000000\n[Eval @ 001] 190.000000\n[Eval @ 001] 835.000000\n[Eval @ 001] 835.000000\n[Eval @ 001] 191.000000\n[Eval @ 001] 835.000000\n"])
def test_wide_caption_measurement_unavailable_is_explicit(tmp_path, monkeypatch, report):
    monkeypatch.setattr(rendering, "_run", lambda *a, **k: report)
    with pytest.raises(VideoEditingError, match="CAPTION_LAYOUT_MEASUREMENT_UNAVAILABLE"):
        rendering._measure_caption_box("unit-ffmpeg", work=tmp_path, filename="caption-000.txt", font="fixed-font")


def test_wide_caption_measurement_cancellation_preserves_previous(media, render_calls, caption_font, tmp_path, monkeypatch):
    prior = tmp_path / "previous.mp4"
    prior.write_bytes(b"previous verified output")
    captioned = Timeline.from_assets((media,), "16:9").add_clip(media.asset_id, source_out=1, audio_role="muted")
    captioned = captioned.add_caption(0, 1, "complete caption", layout_profile="literal-wide-720p-v2")
    error = PermissionError("actual current access revoked")
    monkeypatch.setattr(rendering, "_measure_caption_box", lambda *a, **k: (_ for _ in ()).throw(error))
    with pytest.raises(PermissionError) as caught:
        rendering.render_timeline(captioned, tmp_path / "cancelled.mp4")
    assert caught.value is error and prior.read_bytes() == b"previous verified output"
    assert not (tmp_path / "cancelled.mp4").exists() and not list(tmp_path.glob("timeline-render-*"))


def test_actual_wide_caption_measurement_rejects_cjk_overflow(installed_caption_runtime, tmp_path):
    ffmpeg, source = installed_caption_runtime
    asset = video_editing.fingerprint_local_media(str(source))
    timeline = Timeline.from_assets((asset,), "16:9").add_caption(0, 1, "界" * 48,
        layout_profile="literal-wide-720p-v2")
    with pytest.raises(VideoEditingError, match="CAPTION_LAYOUT_EXCEEDS_PIXEL_BOUNDS"):
        rendering._overlay_filters(timeline, duration=1, width=1280, height=720,
                                   ffmpeg=ffmpeg, work=tmp_path)


def test_actual_wide_caption_export_reopen_retains_audio_and_parent(installed_caption_runtime, tmp_path, monkeypatch):
    ffmpeg, source = installed_caption_runtime
    import shared_artifacts
    monkeypatch.setattr(shared_artifacts, "_ffmpeg_path", lambda: ffmpeg)
    asset = video_editing.fingerprint_local_media(str(source))
    base = Timeline.from_assets((asset,), "16:9").add_clip(asset.asset_id, source_out=1, audio_stream_index=0)
    original = base.add_caption(0, 1, "short original")
    literal = "Some have always known this coast. Some learned the name of the river after they arrived. Some are deciding whether to stay."
    changed = original.update_caption(original.overlays[0].overlay_id, 0, 1, literal,
        layout_profile="literal-wide-720p-v2")
    reopened = Timeline.from_dict(changed.to_dict(), assets=(asset,))
    baseline = tmp_path / "base.mp4"
    rendered = tmp_path / "wide.mp4"
    rendering.render_timeline(base, baseline)
    result = rendering.render_timeline(reopened, rendered)
    assert result["measurement"]["video_frames"] == 30
    assert result["overlay_processing"]["measured_layouts"][0]["profile"] == "literal-wide-720p-v2"
    assert _audio_packets(video_editing._ffprobe_path(), baseline) == _audio_packets(video_editing._ffprobe_path(), rendered)
    assert original.overlays[0].text == "short original" and original.version + 1 == changed.version
    assert reopened.to_dict() == changed.to_dict() and not list(tmp_path.glob("timeline-render-*"))


@pytest.mark.parametrize("prefix", ["", "[Eval @ 001] "])
def test_caption_measurement_accepts_actual_ffmpeg_log_styles(tmp_path, monkeypatch, prefix):
    report = "\n".join(prefix + value for value in ["140.000000", "34.000000", "140.000000"])
    monkeypatch.setattr(rendering, "_run", lambda *a, **k: report)
    assert rendering._measure_caption_box("ffmpeg", work=tmp_path, filename="caption.txt", font="fixed") == (140, 34)
