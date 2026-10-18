"""Bounded synthetic-source FFmpeg integration, not real-user/P11 narrative E2E."""
from __future__ import annotations

from array import array
from dataclasses import replace
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import wave

from PIL import Image
import pytest

from lumenis.shared.content_creation import audio_visuals as av
from lumenis.shared.content_creation import rendering
from lumenis.shared.content_creation.video_editing import VideoEditingError, fingerprint_local_media


@pytest.fixture
def source(tmp_path, monkeypatch):
    """A known stereo source whose requested middle excerpt has a unique tone."""
    from shared_artifacts import _ffmpeg_path
    if not _ffmpeg_path() or not av._ffprobe_path() or not rendering.CAPTION_FONT.is_file():
        pytest.skip("requires the existing FFmpeg/FFprobe/CJK-font toolchain")
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(tmp_path))
    path = tmp_path / "source ' [%{n}] ;.wav"
    samples = array("h")
    for index in range(3 * av.SAMPLE_RATE):
        frequency = 880 if av.SAMPLE_RATE <= index < 2 * av.SAMPLE_RATE else 220
        sample = round(12000 * math.sin(2 * math.pi * frequency * index / av.SAMPLE_RATE))
        samples.extend((sample, -sample))
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setparams((2, 2, av.SAMPLE_RATE, 0, "NONE", "not compressed"))
        output.writeframes(samples.tobytes())
    return fingerprint_local_media(str(path))


def _build(source, **kwargs):
    values = {"start_sec": 1.0, "end_sec": 1.5,
              "title": "声音片段", "quote": "真实声音，清楚表达。"}
    values.update(kwargs)
    return av.build_audio_visual_files(source, **values)


@pytest.mark.parametrize("ratio,dimensions", [("9:16", (720, 1280)), ("16:9", (1280, 720)),
                                             ("1:1", (1080, 1080)), ("4:5", (864, 1080)),
                                             ("3:4", (810, 1080))])
def test_real_cards_and_complete_audio_video_decode(source, tmp_path, ratio, dimensions):
    from shared_artifacts import _ffmpeg_path
    before = Path(source.path).read_bytes()
    result = _build(source, format_ratio=ratio)
    assert set(result) == {"files", "report"}
    assert set(result["files"]) == {"audio-visual.png", "quote-card.png", "audio-visual.mp4", "audio-visual.json"}
    report = result["report"]
    assert report == json.loads(result["files"]["audio-visual.json"])
    assert report["source_sha256"] == hashlib.sha256(before).hexdigest()
    assert report["source_start_sec"] == 1 and report["source_end_sec"] == 1.5
    assert report["asr_performed"] is report["ai_generated"] is report["published"] is False
    assert report["copy_check"] == "USER_SUPPLIED_LITERAL_NOT_VERIFIED_AGAINST_AUDIO"
    assert report["semantic_story_selection"] == "not_performed"
    assert report["font"]["all_requested_glyphs_verified"] is True
    assert report["waveform"]["decoded_samples_per_channel"] == 24000
    assert max(peak["max"] for peak in report["waveform"]["bins"]) > .3
    assert min(peak["min"] for peak in report["waveform"]["bins"]) < -.3
    assert source.path not in json.dumps(report)
    for filename, data in result["files"].items():
        assert Path(filename).name == filename
        if filename == "audio-visual.json":
            continue
        metadata = report["outputs"][filename]
        assert metadata["sha256"] == hashlib.sha256(data).hexdigest()
        assert metadata["size_bytes"] == len(data)
        assert (metadata["width"], metadata["height"]) == dimensions
        assert metadata["source_sha256"] == source.sha256
        if filename.endswith(".png"):
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                assert image.size == dimensions and image.format == "PNG"
            for region in metadata["layout"].values():
                if "safe_box" in region:
                    x1, y1, x2, y2 = region["bounds"]
                    a, b, c, d = region["safe_box"]
                    assert a <= x1 <= x2 <= c and b <= y1 <= y2 <= d
    clip = report["outputs"]["audio-visual.mp4"]
    assert clip["video_frames"] == 15
    assert clip["decode_all_frames"] == "passed" and clip["strict_decode"] is True
    assert clip["audio_codec"] == "aac" and clip["video_codec"] == "h264"
    # An independent real decoder verifies selected audio, not only metadata.
    path = tmp_path / "result.mp4"
    path.write_bytes(result["files"]["audio-visual.mp4"])
    decoded = subprocess.run([
        _ffmpeg_path(), "-v", "error", "-xerror", "-nostdin", "-i", str(path),
        "-map", "0:a:0", "-af", "pan=mono|c0=c0", "-ar", "48000",
        "-c:a", "pcm_s16le", "-f", "s16le", "pipe:1",
    ], capture_output=True, check=True, timeout=30, shell=False).stdout
    samples = array("h")
    samples.frombytes(decoded)
    if sys.byteorder != "little":
        samples.byteswap()
    def amplitude(frequency):
        return abs(sum(value * complex(math.cos(2 * math.pi * frequency * i / 48000),
                                       math.sin(2 * math.pi * frequency * i / 48000))
                       for i, value in enumerate(samples[:20000])))
    assert amplitude(880) > 30 * amplitude(220)
    assert Path(source.path).read_bytes() == before


def test_literal_copy_is_not_filter_markup_and_output_is_reproducible(source):
    quote = "原样 %{n} : ' ; [0:v] drawtext=hello \\ <b>文字</b>"
    first = _build(source, quote=quote, end_sec=1.25)
    second = _build(source, quote=quote, end_sec=1.25)
    assert first["report"]["copy"]["quote"] == quote
    assert first["files"] == second["files"]


@pytest.mark.parametrize("changes,code", [
    ({"start_sec": True}, "RANGE_INVALID"), ({"end_sec": "2"}, "RANGE_INVALID"),
    ({"end_sec": 10 ** 1000}, "RANGE_INVALID"),
    ({"start_sec": -1}, "RANGE_INVALID"), ({"end_sec": float("nan")}, "RANGE_INVALID"),
    ({"end_sec": float("inf")}, "RANGE_INVALID"), ({"end_sec": 4}, "RANGE_INVALID"),
    ({"end_sec": 1.01}, "RANGE_INVALID"), ({"end_sec": 1}, "RANGE_INVALID"),
    ({"title": " "}, "COPY_INVALID"), ({"quote": "\x00bad"}, "COPY_INVALID"),
    ({"quote": "hidden\u202etext"}, "COPY_INVALID"), ({"quote": "\ud800"}, "COPY_INVALID"),
    ({"quote": "字" * 401}, "COPY_INVALID"), ({"title": "A" * 81}, "COPY_INVALID"),
    ({"format_ratio": "../../file"}, "FORMAT_RATIO_INVALID"),
    ({"format_ratio": []}, "FORMAT_RATIO_INVALID"),
])
def test_invalid_inputs_fail_before_render(source, monkeypatch, changes, code):
    monkeypatch.setattr(rendering, "_run", lambda *a, **k: pytest.fail("invalid input reached FFmpeg"))
    with pytest.raises(VideoEditingError, match=code):
        _build(source, **changes)


def test_forged_metadata_and_changed_source_are_rejected(source):
    with pytest.raises(VideoEditingError, match="SOURCE_CHANGED"):
        _build(replace(source, duration_sec=2.5))
    with Path(source.path).open("ab") as output:
        output.write(b"changed")
    with pytest.raises(VideoEditingError, match="SOURCE_CHANGED"):
        _build(source)


def test_multiple_audio_streams_need_explicit_supported_selection(source, tmp_path):
    from shared_artifacts import _ffmpeg_path
    path = tmp_path / "multiple.mkv"
    subprocess.run([_ffmpeg_path(), "-v", "error", "-nostdin", "-n", "-i", source.path,
                    "-map", "0:a:0", "-map", "0:a:0", "-c:a", "copy", str(path)],
                   capture_output=True, check=True, timeout=30, shell=False)
    with pytest.raises(VideoEditingError, match="SINGLE_AUDIO_STREAM_REQUIRED"):
        _build(fingerprint_local_media(str(path)))


def test_no_audio_stream_rejected(source):
    with pytest.raises(VideoEditingError, match="AUDIO_REQUIRED"):
        _build(replace(source, has_video=True, audio_stream_count=0))


def test_encoded_video_source_uses_requested_real_audio(source, tmp_path):
    from shared_artifacts import _ffmpeg_path
    path = tmp_path / "source.mp4"
    subprocess.run([
        _ffmpeg_path(), "-v", "error", "-nostdin", "-n", "-filter_threads", "1",
        "-f", "lavfi", "-i", "color=c=black:s=64x64:r=30:d=3", "-i", source.path,
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-threads:v", "1",
        "-c:a", "aac", "-threads:a", "1", str(path),
    ], capture_output=True, check=True, timeout=30, shell=False)
    asset = fingerprint_local_media(str(path))
    result = _build(asset)
    assert result["report"]["source_sha256"] == asset.sha256
    assert result["report"]["outputs"]["audio-visual.mp4"]["decode_all_frames"] == "passed"


def test_missing_audio_at_requested_tail_is_not_filled_silently(source, tmp_path):
    from shared_artifacts import _ffmpeg_path
    path = tmp_path / "short-audio.mkv"
    subprocess.run([
        _ffmpeg_path(), "-v", "error", "-nostdin", "-n", "-filter_threads", "1",
        "-f", "lavfi", "-i", "color=c=black:s=64x64:r=30:d=4", "-i", source.path,
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-threads:v", "1",
        "-c:a", "pcm_s16le", "-threads:a", "1", str(path),
    ], capture_output=True, check=True, timeout=30, shell=False)
    with pytest.raises(VideoEditingError, match="AUDIO_COVERAGE_INVALID"):
        _build(fingerprint_local_media(str(path)), start_sec=2.5, end_sec=3.5)


def test_missing_glyph_fails_closed(source):
    with pytest.raises(VideoEditingError, match="GLYPH_UNAVAILABLE"):
        _build(source, quote="未支持\U00013000")


@pytest.mark.parametrize("end_sec", [1.2, 1.21337, 1.966667])
def test_non_frame_aligned_excerpt_keeps_measured_duration(source, end_sec):
    result = _build(source, end_sec=end_sec)
    report = result["report"]
    assert report["source_end_sec"] == end_sec
    assert abs(report["outputs"]["audio-visual.mp4"]["audio_duration_sec"] - (end_sec - 1)) < .001


def test_cancellation_preserves_callback_and_cleans_private_work(source, monkeypatch):
    roots = []
    original_temp = av.tempfile.TemporaryDirectory
    def private_directory(*args, **kwargs):
        temporary = original_temp(*args, **kwargs)
        roots.append(Path(temporary.name))
        return temporary
    monkeypatch.setattr(av.tempfile, "TemporaryDirectory", private_directory)
    calls = 0
    cancel = TimeoutError("owner cancelled")
    def check():
        nonlocal calls
        calls += 1
        if calls == 12:
            raise cancel
    with pytest.raises(TimeoutError) as caught:
        _build(source, check_cancel=check)
    assert caught.value is cancel and roots
    assert all(not path.exists() for path in roots)


def test_mutation_after_render_never_returns_artifacts(source, monkeypatch):
    original = av._verify_video
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        with Path(source.path).open("ab") as output:
            output.write(b"changed during render")
        return result
    monkeypatch.setattr(av, "_verify_video", mutate)
    with pytest.raises(VideoEditingError, match="SOURCE_CHANGED"):
        _build(source)


def test_private_work_is_removed_after_encoder_failure(source, monkeypatch):
    original = rendering._run
    root = None
    def fail_video(command, **kwargs):
        nonlocal root
        root = kwargs["cwd"]
        if "libx264" in command:
            raise VideoEditingError("MEDIA_RENDER_FAILED")
        return original(command, **kwargs)
    monkeypatch.setattr(rendering, "_run", fail_video)
    with pytest.raises(VideoEditingError, match="MEDIA_RENDER_FAILED"):
        _build(source)
    assert root is not None and not root.exists()


def test_copy_overflow_never_truncates(source):
    with pytest.raises(VideoEditingError, match="COPY_LAYOUT_OVERFLOW"):
        _build(source, title="\n".join("字" for _ in range(40)))


def test_automatic_cjk_wrap_keeps_punctuation_and_all_copy():
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(Image.new("RGB", (720, 1280)))
    font = ImageFont.truetype(str(rendering.CAPTION_FONT), 44)
    copy = "仅验证片段编码、波形和时间码；不代表语音转写或故事闭环。"
    wrapped = av._wrap_copy(draw, copy, font, 624)
    assert wrapped.replace("\n", "") == copy
    assert all(not line.startswith(tuple("，。；：！？、")) for line in wrapped.splitlines())
