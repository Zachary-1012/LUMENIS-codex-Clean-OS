"""Render verified local timelines under the existing Shared media owner.

Artifact registration, source authorization and export permission remain caller
responsibilities. Unsupported timeline features fail instead of disappearing.
"""
from __future__ import annotations

import hashlib
from bisect import bisect_left
import json
import math
import os
import re
import shutil
import subprocess
import struct
import tempfile
import time
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .video_editing import (
    MAX_EDIT_TIME_SEC,
    MEDIA_INPUT_DEMUXERS,
    Timeline,
    TimelineClip,
    VideoEditingError,
    _ffprobe_path,
    fingerprint_local_media,
)


SAMPLE_RATE = 48000
FRAME_RATE = 30
MAX_RENDER_CLIPS = 128
MIX_SAMPLE_PEAK_LIMIT = 0.891251  # -1 dBFS sample peak; not a true-peak/LUFS guarantee.
FINAL_TRUE_PEAK_LIMIT_DBTP = -1.0
PEAK_CORRECTION_HEADROOM_DB = .5  # Codec response can change with gain; remeasure, never assume.
FRAME_SIZES = {"9:16": (720, 1280), "16:9": (1280, 720), "3:4": (810, 1080), "4:5": (864, 1080)}
CAPTION_FONT = Path("C:/Windows/Fonts/msyh.ttc")  # Host resource only; never bundled/exported.


def _run(command: list[str], *, cwd: Path, timeout: float = 60,
         check_continue: Callable[[], None] | None = None) -> str:
    if os.name == "nt" and len(subprocess.list2cmdline(command)) > 30000:
        raise VideoEditingError("RENDER_COMMAND_TOO_LARGE")
    callback_error: BaseException | None = None

    def check_status() -> None:
        nonlocal callback_error
        if check_continue:
            try:
                check_continue()
            except BaseException as exc:
                callback_error = exc
                raise

    try:
        check_status()
        deadline = time.monotonic() + timeout
        with subprocess.Popen(
            command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", shell=False,
        ) as process:
            try:
                while True:
                    check_status()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(command, timeout)
                    try:
                        _, stderr = process.communicate(timeout=min(.25, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        continue
                check_status()
            except BaseException:
                # Reap the encoder before its private working directory is removed.
                process.kill()
                process.communicate()
                raise
    except (OSError, subprocess.SubprocessError) as exc:
        # Permission/cancellation callbacks are not encoder failures, even when
        # their exception happens to inherit from a process/OS error class.
        if exc is callback_error:
            raise
        raise VideoEditingError("MEDIA_RENDER_PROCESS_FAILED") from exc
    if process.returncode != 0:
        # Decoder messages can contain private source paths. Keep them out of API errors.
        raise VideoEditingError("MEDIA_RENDER_FAILED")
    return stderr


def _number(value: float) -> str:
    return f"{value:.6f}"


def _frame_at(seconds: float) -> int:
    # Round shared boundaries once so adjacent clips cannot accumulate drift.
    return int(math.floor(round(seconds * FRAME_RATE, 6) + 0.5))


def _video_transition_plan(timeline: Timeline, clips: list[TimelineClip]) -> dict[int, dict[str, Any]]:
    """Resolve centred dissolves using real handles, without rippling other edits."""
    assets = {asset.asset_id: asset for asset in timeline.assets}
    boundaries = {(left.clip_id, right.clip_id): index
                  for index, (left, right) in enumerate(zip(clips, clips[1:]), 1)}
    seen: set[int] = set()
    plan: dict[int, dict[str, Any]] = {}
    for transition in timeline.transitions:
        if transition.transition_type not in {"cut", "dissolve"}:
            raise VideoEditingError("TRANSITION_RENDER_NOT_SUPPORTED")
        index = boundaries.get((transition.from_clip, transition.to_clip))
        if index is None:
            raise VideoEditingError("TRANSITION_REQUIRES_ADJACENT_VIDEO_CLIPS")
        if index in seen:
            raise VideoEditingError("TRANSITION_BOUNDARY_CONFLICT")
        seen.add(index)
        if transition.transition_type == "cut":
            continue
        if transition.duration_sec < 1 / FRAME_RATE:
            raise VideoEditingError("TRANSITION_SHORTER_THAN_OUTPUT_FRAME")
        frames = _frame_at(transition.duration_sec)
        before, after = frames // 2, frames - frames // 2
        left, right = clips[index - 1], clips[index]
        cut_frame = _frame_at(right.timeline_start)
        start, end = cut_frame - before, cut_frame + after
        if (start < _frame_at(left.timeline_start)
                or end > _frame_at(right.timeline_start + right.duration_sec)):
            raise VideoEditingError("TRANSITION_WINDOW_EXCEEDS_CLIP")
        left_frames = cut_frame - _frame_at(left.timeline_start)
        outgoing_end = left.source_in + (left_frames + after) / FRAME_RATE
        if (outgoing_end > assets[left.media_asset_id].duration_sec
                or right.source_in < before / FRAME_RATE):
            raise VideoEditingError("TRANSITION_MEDIA_HANDLES_UNAVAILABLE")
        plan[index] = {
            "from_clip": left.clip_id, "to_clip": right.clip_id, "type": "dissolve",
            "requested_duration_sec": transition.duration_sec, "duration_frames": frames,
            "before_cut_frames": before, "after_cut_frames": after,
            "start_frame": start, "end_frame": end,
            "outgoing_extra_source_range": [left.source_in + left_frames / FRAME_RATE, outgoing_end],
            "incoming_extra_source_range": [right.source_in - before / FRAME_RATE, right.source_in],
        }
    previous_end = -1
    for item in sorted(plan.values(), key=lambda item: item["start_frame"]):
        if item["start_frame"] < previous_end:
            raise VideoEditingError("TRANSITION_WINDOWS_OVERLAP")
        previous_end = item["end_frame"]
    return plan


def _verify_caption_glyphs(text: str) -> None:
    """Check the exact TTC face used by drawtext, without font fallback or new libraries."""
    required = {ord(char) for char in text if char != "\n"}
    supported: set[int] = set()
    try:
        data = CAPTION_FONT.read_bytes()
        face = struct.unpack_from(">I", data, 12)[0] if data[:4] == b"ttcf" else 0
        table_count = struct.unpack_from(">H", data, face + 4)[0]
        records = [face + 12 + index * 16 for index in range(table_count)]
        cmap_record = next(pos for pos in records if data[pos:pos + 4] == b"cmap")
        cmap = struct.unpack_from(">I", data, cmap_record + 8)[0]
        for index in range(struct.unpack_from(">H", data, cmap + 2)[0]):
            platform, encoding, offset = struct.unpack_from(">HHI", data, cmap + 4 + index * 8)
            if platform != 0 and (platform, encoding) not in {(3, 1), (3, 10)}:
                continue
            sub = cmap + offset
            form = struct.unpack_from(">H", data, sub)[0]
            if form == 12:
                count = struct.unpack_from(">I", data, sub + 12)[0]
                groups = [struct.unpack_from(">III", data, sub + 16 + i * 12) for i in range(count)]
                ends = [group[1] for group in groups]
                for code in required:
                    i = bisect_left(ends, code)
                    if i < count and groups[i][0] <= code and groups[i][2] + code - groups[i][0] > 0:
                        supported.add(code)
            elif form == 4:
                count = struct.unpack_from(">H", data, sub + 6)[0] // 2
                ends = struct.unpack_from(f">{count}H", data, sub + 14)
                starts = struct.unpack_from(f">{count}H", data, sub + 16 + count * 2)
                deltas = struct.unpack_from(f">{count}h", data, sub + 16 + count * 4)
                ranges_at = sub + 16 + count * 6
                ranges = struct.unpack_from(f">{count}H", data, ranges_at)
                for code in required:
                    i = bisect_left(ends, code)
                    if i >= count or code < starts[i]:
                        continue
                    glyph = (struct.unpack_from(">H", data, ranges_at + i * 2 + ranges[i] +
                                                2 * (code - starts[i]))[0] if ranges[i] else code)
                    if (not ranges[i] or glyph) and (glyph + deltas[i]) & 0xffff:
                        supported.add(code)
    except (OSError, struct.error, StopIteration, ValueError) as exc:
        raise VideoEditingError("CAPTION_FONT_UNAVAILABLE") from exc
    if required - supported:
        raise VideoEditingError("OVERLAY_GLYPH_UNAVAILABLE")


def _wide_caption_lines(text: str) -> list[str]:
    """Keep every character and prefer a space boundary within 48 base characters."""
    lines = []
    for original in text.split("\n"):
        clusters: list[str] = []
        for char in original:
            if clusters and unicodedata.category(char).startswith("M"):
                clusters[-1] += char
            else:
                clusters.append(char)
        while len(clusters) > 48:
            spaces = [index + 1 for index, cluster in enumerate(clusters[:48]) if cluster == " "]
            boundary = spaces[-1] if spaces else 48
            lines.append("".join(clusters[:boundary]))
            clusters = clusters[boundary:]
        lines.append("".join(clusters))
    return lines


def _measure_caption_box(ffmpeg: str, *, work: Path, filename: str,
                         font: str, check_continue: Callable[[], None] | None = None) -> tuple[float, float]:
    """Fail closed if the actual installed drawtext cannot report stable dimensions."""
    report = _run([ffmpeg, "-v", "info", "-nostats", "-nostdin", "-filter_threads", "1",
                   "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=30:d=0.04", "-vf",
                   f"drawtext={font}:textfile={filename}:expansion=none:reload=0:"
                   "fontsize=35:line_spacing=8:x='print(text_w)':y='print(text_h)'",
                   "-frames:v", "1", "-f", "null", "-"], cwd=work, check_continue=check_continue)
    numbers = [float(value) for value in re.findall(
        r"^\[Eval @ [^\]]+\] ([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s*$",
        report, flags=re.MULTILINE)]
    if not numbers or len(numbers) % 3 or len(numbers) > 24:
        raise VideoEditingError("CAPTION_LAYOUT_MEASUREMENT_UNAVAILABLE")
    boxes = []
    for index in range(0, len(numbers), 3):
        width, height, width_again = numbers[index:index + 3]
        if (not all(math.isfinite(value) and value > 0 for value in (width, height, width_again))
                or width != width_again):
            raise VideoEditingError("CAPTION_LAYOUT_MEASUREMENT_UNAVAILABLE")
        boxes.append((width, height))
    if any(box != boxes[0] for box in boxes):
        raise VideoEditingError("CAPTION_LAYOUT_MEASUREMENT_UNAVAILABLE")
    return boxes[0]


def _overlay_filters(timeline: Timeline, *, duration: float, width: int, height: int,
                     ffmpeg: str, work: Path,
                     check_continue: Callable[[], None] | None = None,
                     layout_readback: list[dict[str, Any]] | None = None) -> list[str]:
    if not timeline.overlays:
        return []
    if len(timeline.overlays) > 64:
        raise VideoEditingError("OVERLAY_COUNT_EXCEEDED")
    prepared = []
    previous_end: dict[str, float] = {}
    for overlay in sorted(timeline.overlays, key=lambda item: (item.start_sec, item.end_sec)):
        if check_continue:
            check_continue()
        if overlay.end_sec > duration:
            raise VideoEditingError("OVERLAY_EXTENDS_BEYOND_VIDEO")
        start = math.ceil(round(overlay.start_sec * FRAME_RATE, 6))
        end = min(math.ceil(round(overlay.end_sec * FRAME_RATE, 6)), _frame_at(duration))
        if start >= end:
            raise VideoEditingError("OVERLAY_SHORTER_THAN_OUTPUT_FRAME")
        if overlay.start_sec < previous_end.get(overlay.kind, 0):
            raise VideoEditingError("OVERLAY_SAME_KIND_OVERLAP_NOT_SUPPORTED")
        previous_end[overlay.kind] = overlay.end_sec
        if not isinstance(overlay.text, str) or len(overlay.text) > 1024:
            raise VideoEditingError("OVERLAY_TEXT_NOT_SUPPORTED")
        text = overlay.text.replace("\r\n", "\n")
        if any(unicodedata.category(char).startswith("C") and char != "\n" for char in text):
            raise VideoEditingError("OVERLAY_TEXT_NOT_SUPPORTED")
        profile = overlay.layout_profile
        if profile is not None and (profile != "literal-wide-720p-v2" or overlay.kind != "caption"):
            raise VideoEditingError("OVERLAY_LAYOUT_PROFILE_NOT_SUPPORTED")
        if profile is not None and (width, height) != (1280, 720):
            raise VideoEditingError("CAPTION_LAYOUT_REQUIRES_1280_720")
        columns_per_line = 48 if profile is not None else 28
        # Preserve every explicit line (including blank lines), space and codepoint.
        # Wrap only before a base character, never between it and its combining marks.
        lines = []
        for original_line in text.split("\n"):
            line, columns = "", 0
            for char in original_line:
                is_mark = unicodedata.category(char).startswith("M")
                if columns == columns_per_line and not is_mark:
                    lines.append(line)
                    line, columns = "", 0
                line += char
                columns += int(not is_mark)
            lines.append(line)
        if profile is not None:
            lines = _wide_caption_lines(text)
        if len(lines) > 4:
            raise VideoEditingError("OVERLAY_LAYOUT_EXCEEDS_FOUR_LINES")
        prepared.append((overlay.kind, start, end, "\n".join(lines), profile, overlay.overlay_id))
    if os.name != "nt" or not CAPTION_FONT.is_file():
        raise VideoEditingError("CAPTION_FONT_UNAVAILABLE")
    _verify_caption_glyphs("\n".join(item[3] for item in prepared))
    # Only this fixed installed font is used; no Timeline/API path enters the graph.
    font = "fontfile='C\\:/Windows/Fonts/msyh.ttc'"
    cancelled: list[BaseException] = []
    def check_probe() -> None:
        if check_continue:
            try:
                check_continue()
            except BaseException as exc:
                cancelled.append(exc)
                raise
    try:
        _run([ffmpeg, "-v", "error", "-nostdin", "-filter_threads", "1", "-f", "lavfi", "-i",
              "color=c=black:s=32x32:r=30:d=0.04", "-vf",
              f"drawtext={font}:text=中文:expansion=none", "-frames:v", "1", "-f", "null", "-"],
             cwd=work, check_continue=check_probe)
    except Exception as exc:
        if cancelled:
            raise cancelled[0]
        if isinstance(exc, VideoEditingError) and str(exc) in {"MEDIA_RENDER_FAILED", "MEDIA_RENDER_PROCESS_FAILED"}:
            raise VideoEditingError("CAPTION_RENDER_UNAVAILABLE") from exc
        raise
    size, margin = max(16, width // 36), max(16, height // 24)
    filters = []
    for index, (kind, start, end, text, profile, overlay_id) in enumerate(prepared):
        if check_continue:
            check_continue()
        filename = f"caption-{index:03d}.txt"
        with (work / filename).open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        if profile is not None:
            box_width, box_height = _measure_caption_box(ffmpeg, work=work, filename=filename,
                                                          font=font, check_continue=check_continue)
            if box_width + 16 > width - 2 * margin or box_height + 16 > height * .3:
                raise VideoEditingError("CAPTION_LAYOUT_EXCEEDS_PIXEL_BOUNDS")
            if layout_readback is not None:
                layout_readback.append({"overlay_id": overlay_id, "profile": profile,
                                        "text_width_px": box_width, "text_height_px": box_height,
                                        "box_border_px": 8, "horizontal_margin_px": margin,
                                        "maximum_box_height_ratio": .3})
        y = f"h-text_h-{margin}" if kind == "caption" else str(margin)
        filters.append(f"drawtext={font}:textfile={filename}:expansion=none:reload=0:"
                       f"fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=8:"
                       f"line_spacing={size // 4}:x=(w-text_w)/2:y={y}:"
                       f"enable='gte(n,{start})*lt(n,{end})'")
    return filters


def _audio_filter(clip: TimelineClip) -> str:
    duration = clip.duration_sec
    mix = clip.audio_mix
    filters = [
        f"atrim=start={_number(clip.source_in)}:end={_number(clip.source_out)}",
        # Keep source silence after the cut boundary; do not re-anchor first sound.
        f"asetpts=PTS-{_number(clip.source_in)}/TB", f"aresample={SAMPLE_RATE}:first_pts=0",
        "aformat=sample_fmts=fltp:channel_layouts=stereo",
        f"volume={_number(mix.volume)}",
    ]
    if mix.fade_in_sec:
        filters.append(f"afade=t=in:st=0:d={_number(mix.fade_in_sec)}")
    if mix.fade_out_sec:
        filters.append(f"afade=t=out:st={_number(duration - mix.fade_out_sec)}:d={_number(mix.fade_out_sec)}")
    filters.extend([
        f"apad=whole_len={round(duration * SAMPLE_RATE)}", f"atrim=end_sample={round(duration * SAMPLE_RATE)}",
        "asetpts=N/SR/TB",
        f"adelay={round(clip.timeline_start * SAMPLE_RATE)}S:all=1",
        "asetpts=N/SR/TB",
    ])
    return ",".join(filters)


def _verify_sources(timeline: Timeline) -> None:
    from shared_artifacts import validate_local_asset

    used = {clip.media_asset_id for track in timeline.tracks for clip in track.clips}
    assets = {asset.asset_id: asset for asset in timeline.assets}
    for asset_id in used:
        asset = assets[asset_id]
        try:
            path = validate_local_asset(asset.path)
            current = fingerprint_local_media(str(path))
        except (OSError, ValueError) as exc:
            raise VideoEditingError("SOURCE_MEDIA_NOT_READABLE") from exc
        if (current.sha256, current.duration_sec, current.has_video, current.audio_stream_count) != (
            asset.sha256, asset.duration_sec, asset.has_video, asset.audio_stream_count
        ):
            raise VideoEditingError("SOURCE_MEDIA_CHANGED")


def _render_audio(timeline: Timeline, *, duration: float, ffmpeg: str, work: Path,
                  check_continue: Callable[[], None] | None = None) -> Path | None:
    assets = {asset.asset_id: asset for asset in timeline.assets}
    command = [ffmpeg, "-v", "error", "-nostdin", "-n", "-filter_threads", "1",
               "-filter_complex_threads", "1", "-threads", "1"]
    graph: list[str] = []
    labels: list[str] = []
    voice_labels: list[str] = []
    ducked_labels: list[str] = []
    sample_count = round(duration * SAMPLE_RATE)
    input_index = 0
    for track in timeline.tracks:
        for clip in track.clips:
            asset = assets[clip.media_asset_id]
            if clip.audio_role == "muted" or asset.audio_stream_count == 0:
                continue
            stream = clip.audio_stream_index
            if stream is None:
                if asset.audio_stream_count != 1:
                    raise VideoEditingError("AUDIO_STREAM_SELECTION_REQUIRED")
                stream = 0
            command += ["-protocol_whitelist", "file", "-format_whitelist", MEDIA_INPUT_DEMUXERS,
                        "-i", asset.path]
            label = f"clip{input_index}"
            graph.append(f"[{input_index}:a:{stream}]" + _audio_filter(clip) +
                         f",apad=whole_len={sample_count},atrim=end_sample={sample_count}[{label}]")
            labels.append(label)
            if clip.audio_role == "voiceover" and clip.audio_mix.volume > 0:
                voice_labels.append(label)
            if clip.audio_mix.ducking:
                ducked_labels.append(label)
            input_index += 1

    if not labels:
        return None

    if ducked_labels:
        # Split explicit voiceover stems only. Original sound can contain music;
        # treating it as detected speech would misrepresent source separation.
        for label in voice_labels:
            graph.append(f"[{label}]asplit=2[{label}mix][{label}key]")
            labels[labels.index(label)] = f"{label}mix"
        graph.append("".join(f"[{label}key]" for label in voice_labels) +
                     f"amix=inputs={len(voice_labels)}:normalize=0:dropout_transition=0:duration=longest[voicekey]")
        graph.append(f"[voicekey]asplit={len(ducked_labels)}" +
                     "".join(f"[key{index}]" for index in range(len(ducked_labels))))
        for index, label in enumerate(ducked_labels):
            graph.append(f"[{label}][key{index}]sidechaincompress=threshold=0.025:ratio=8:"
                         f"attack=10:release=250:makeup=1:link=maximum:detection=rms[{label}ducked]")
            labels[labels.index(label)] = f"{label}ducked"

    if len(labels) == 1:
        combined = labels[0]
    else:
        combined = "mixed"
        graph.append("".join(f"[{label}]" for label in labels) +
                     f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0:duration=longest[{combined}]")
    graph.append(f"[{combined}]alimiter=limit={MIX_SAMPLE_PEAK_LIMIT}:attack=5:release=50:level=0:latency=1,"
                 f"apad=whole_len={sample_count},atrim=end_sample={sample_count},asetpts=N/SR/TB[out]")

    output = work / "audio.wav"
    _run(command + ["-filter_complex", ";".join(graph), "-map", "[out]", "-ar", str(SAMPLE_RATE),
                    "-ac", "2", "-c:a", "pcm_s24le", "-threads:a", "1", "-f", "wav", str(output)],
         cwd=work, **({"check_continue": check_continue} if check_continue else {}))
    return output


def _probe_output(path: Path, ffprobe: str, *, output_kind: str, duration: float,
                  has_audio: bool) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-protocol_whitelist", "file", "-format_whitelist", "mov,wav",
             "-count_frames", "-show_entries",
             "stream=codec_type,codec_name,start_time,nb_read_frames,sample_rate,channels:format=duration,format_name",
             "-of", "json", "-i", str(path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
            check=True, shell=False,
        )
        probe = json.loads(result.stdout)
        streams = probe["streams"]
        audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
        video = [stream for stream in streams if stream.get("codec_type") == "video"]
        actual = float(probe["format"]["duration"])
        format_name = str(probe["format"]["format_name"])
        starts = [float(stream.get("start_time", 0)) for stream in audio + video]
        frames = int(video[0]["nb_read_frames"]) if video else 0
        expected_video = int(output_kind == "video")
        expected_video_frames = _frame_at(duration) if output_kind == "video" else 0
        expected_audio = int(has_audio or output_kind == "audio")
        duration_tolerance = (2 / FRAME_RATE) if output_kind == "video" else (2 / SAMPLE_RATE)
        correct_format = (
            "mp4" in format_name.split(",") if output_kind == "video" else format_name == "wav"
        )
        audio_metadata_valid = not audio or (
            int(audio[0]["sample_rate"]) == SAMPLE_RATE
            and int(audio[0]["channels"]) == 2
            and audio[0].get("codec_name") == ("aac" if output_kind == "video" else "pcm_s24le")
        )
        if (len(video) != expected_video or len(audio) != expected_audio
                or (video and (frames != expected_video_frames or video[0].get("codec_name") != "h264"))
                or not correct_format or not audio_metadata_valid
                or not math.isfinite(actual) or abs(actual - duration) > duration_tolerance
                or any(not math.isfinite(start) or abs(start) > 2 / FRAME_RATE for start in starts)):
            raise ValueError("output differs from timeline")
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise VideoEditingError("RENDER_OUTPUT_VERIFICATION_FAILED") from exc
    return {"requested_duration_sec": duration, "actual_duration_sec": actual,
            "audio_streams": len(audio), "video_streams": len(video),
            "requested_video_frames": expected_video_frames,
            "video_frames": frames, "stream_start_seconds": starts}


def _validate_output_path(output: Path, *, output_kind: str) -> Path:
    expected_suffix = ".mp4" if output_kind == "video" else ".wav"
    try:
        temporary_root = Path(tempfile.gettempdir()).resolve(strict=True)
        parent = output.parent.resolve(strict=True)
        if (not output.is_absolute() or output.suffix.lower() != expected_suffix
                or output.exists() or output.is_symlink() or parent == temporary_root
                or parent != output.parent.absolute() or not parent.is_relative_to(temporary_root)):
            raise ValueError("not a new private temporary output")
    except (OSError, ValueError) as exc:
        raise VideoEditingError("NEW_PRIVATE_TEMP_OUTPUT_REQUIRED") from exc
    return output


def _measure_loudness(path: Path, ffmpeg: str, *,
                      check_continue: Callable[[], None] | None = None) -> dict[str, Any]:
    # Analyze the final encoded file. The transformed stream goes to null; only
    # input_* statistics describe this file, not loudnorm's hypothetical output.
    diagnostic = _run([
        ffmpeg, "-hide_banner", "-nostdin", "-nostats", "-v", "info",
        "-protocol_whitelist", "file", "-format_whitelist", "mov,wav", "-i", str(path),
        "-map", "0:a:0", "-vn", "-sn", "-dn", "-af", "loudnorm=print_format=json", "-f", "null", "-",
    ], cwd=path.parent, **({"check_continue": check_continue} if check_continue else {}))
    try:
        start = diagnostic.rfind("{")
        if start < 0:
            raise ValueError("missing measurement")
        values, _ = json.JSONDecoder().raw_decode(diagnostic[start:])
        integrated = float(values["input_i"])
        peak = float(values["input_tp"])
        loudness_range = float(values["input_lra"])
        if (any(not math.isfinite(value) and value != -math.inf for value in (integrated, peak))
                or not math.isfinite(loudness_range) or loudness_range < 0
                or (peak == -math.inf and integrated != -math.inf)):
            raise ValueError("invalid measurement")
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        raise VideoEditingError("AUDIO_LOUDNESS_MEASUREMENT_FAILED") from exc
    return {
        "state": "silent" if peak == -math.inf else "below_integrated_gate" if integrated == -math.inf else "measured",
        "integrated_lufs": integrated if math.isfinite(integrated) else None,
        "true_peak_dbtp": peak if math.isfinite(peak) else None,
        "loudness_range_lu": loudness_range,
        "method": "ffmpeg_loudnorm_input_ebu_r128",
        "target_lufs": None,
    }


def _verify_final_audio_peak(rendered: Path, audio: Path, *, ffmpeg: str,
                             output_kind: str, duration: float,
                             check_continue: Callable[[], None] | None = None
                             ) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    run_options = {"check_continue": check_continue} if check_continue else {}
    loudness = _measure_loudness(rendered, ffmpeg, **run_options)
    initial = dict(loudness)
    peak = loudness["true_peak_dbtp"]
    correction_db = 0.0
    if peak is not None and peak > FINAL_TRUE_PEAK_LIMIT_DBTP:
        # One constant attenuation of the lossless mix preserves relative gains,
        # fades and dynamics. Never cascade lossy generations or boost quiet mixes.
        correction_db = FINAL_TRUE_PEAK_LIMIT_DBTP - peak - PEAK_CORRECTION_HEADROOM_DB
        corrected = rendered.with_name("peak-safe" + rendered.suffix)
        command = [ffmpeg, "-v", "error", "-nostdin", "-n", "-filter_threads", "1", "-threads", "1"]
        if output_kind == "video":
            command += ["-protocol_whitelist", "file", "-format_whitelist", "mov", "-i", str(rendered)]
        command += ["-protocol_whitelist", "file", "-format_whitelist", "wav", "-i", str(audio)]
        if output_kind == "video":
            command += ["-map", "0:v:0", "-c:v", "copy", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k",
                        "-movflags", "+faststart"]
        else:
            command += ["-map", "0:a:0", "-c:a", "pcm_s24le"]
        samples = round(duration * SAMPLE_RATE)
        command += ["-af", f"volume={_number(correction_db)}dB,apad=whole_len={samples},"
                    f"atrim=end_sample={samples},asetpts=N/SR/TB",
                    "-ar", str(SAMPLE_RATE), "-ac", "2", "-threads:a", "1", "-t", _number(duration),
                    "-map_metadata", "-1", "-metadata", "comment=Demo - source rights not verified", str(corrected)]
        _run(command, cwd=rendered.parent, **run_options)
        rendered = corrected
        loudness = _measure_loudness(rendered, ffmpeg, **run_options)
        peak = loudness["true_peak_dbtp"]
    if (peak is None and loudness["state"] != "silent"
            or peak is not None and (not math.isfinite(peak) or peak > FINAL_TRUE_PEAK_LIMIT_DBTP)):
        raise VideoEditingError("AUDIO_TRUE_PEAK_VERIFICATION_FAILED")
    return rendered, loudness, {
        "true_peak_verified": True,
        "true_peak_status": "silent" if peak is None else "verified",
        "final_true_peak_limit_dbtp": FINAL_TRUE_PEAK_LIMIT_DBTP,
        "initial_true_peak_dbtp": initial["true_peak_dbtp"],
        "initial_loudness": initial,
        "peak_correction_db": correction_db,
        "peak_correction_passes": int(correction_db < 0),
    }


def render_timeline(timeline: Timeline, output: Path, *, output_kind: str = "video",
                    check_continue: Callable[[], None] | None = None) -> dict[str, Any]:
    """Render a bounded manual timeline to new private-Temp media; never authorize export."""
    from shared_artifacts import _ffmpeg_path

    timeline.validate()
    if check_continue:
        check_continue()
    run_options = {"check_continue": check_continue} if check_continue else {}
    if output_kind not in {"video", "audio"}:
        raise VideoEditingError("OUTPUT_KIND_NOT_SUPPORTED")
    output = _validate_output_path(Path(output), output_kind=output_kind)
    if timeline.format_ratio not in FRAME_SIZES:
        raise VideoEditingError("FORMAT_RATIO_NOT_SUPPORTED")
    if timeline.overlays and output_kind != "video":
        raise VideoEditingError("OVERLAYS_REQUIRE_VIDEO_OUTPUT")
    clips = [clip for track in timeline.tracks for clip in track.clips]
    if not clips or len(clips) > MAX_RENDER_CLIPS:
        raise VideoEditingError("RENDER_REQUIRES_ONE_TO_128_CLIPS")
    ducked_clips = [clip for clip in clips if clip.audio_mix.ducking]
    if any(clip.audio_role != "bgm" for clip in ducked_clips):
        raise VideoEditingError("AUDIO_DUCKING_REQUIRES_BACKGROUND_MUSIC")
    assets = {asset.asset_id: asset for asset in timeline.assets}
    if any(not assets[clip.media_asset_id].audio_stream_count for clip in ducked_clips):
        raise VideoEditingError("AUDIO_DUCKING_REQUIRES_AUDIO_SOURCE")
    if ducked_clips and not any(
        clip.audio_role == "voiceover" and clip.audio_mix.volume > 0
        and assets[clip.media_asset_id].audio_stream_count for clip in clips
    ):
        raise VideoEditingError("AUDIO_DUCKING_REQUIRES_VOICEOVER")
    video_tracks = [track for track in timeline.tracks if track.kind == "video" and track.clips]
    if len(video_tracks) > 1:
        raise VideoEditingError("RENDER_REQUIRES_ONE_VIDEO_TRACK")
    if output_kind == "video" and len(video_tracks) != 1:
        raise VideoEditingError("RENDER_REQUIRES_ONE_VIDEO_TRACK")
    if output_kind == "audio" and video_tracks:
        raise VideoEditingError("AUDIO_EXPORT_REQUIRES_AUDIO_ONLY_TIMELINE")

    if video_tracks:
        cursor = 0.0
        for clip in video_tracks[0].clips:
            if abs(clip.timeline_start - cursor) > 0.00001:
                raise VideoEditingError("VIDEO_CLIPS_MUST_BE_CONTIGUOUS")
            cursor += clip.duration_sec
            if not math.isfinite(cursor) or cursor > MAX_EDIT_TIME_SEC:
                raise VideoEditingError("TIMELINE_DURATION_OUT_OF_RANGE")
        duration = cursor
        if any(clip.timeline_start + clip.duration_sec > duration + 0.00001
               for track in timeline.tracks if track.kind != "video" for clip in track.clips):
            raise VideoEditingError("AUDIO_EXTENDS_BEYOND_VIDEO")
    else:
        duration = max(clip.timeline_start + clip.duration_sec for clip in clips)
        if not math.isfinite(duration) or duration <= 0 or duration > MAX_EDIT_TIME_SEC:
            raise VideoEditingError("TIMELINE_DURATION_OUT_OF_RANGE")

    transitions = _video_transition_plan(timeline, list(video_tracks[0].clips) if video_tracks else [])

    audio_clips = [clip for track in timeline.tracks for clip in track.clips
                   if clip.audio_role != "muted"
                   and next(asset for asset in timeline.assets if asset.asset_id == clip.media_asset_id).audio_stream_count]
    if output_kind == "audio" and not audio_clips:
        raise VideoEditingError("AUDIO_EXPORT_REQUIRES_AUDIO_SOURCE")

    ffmpeg = _ffmpeg_path()
    ffprobe = _ffprobe_path() if ffmpeg else None
    if not ffmpeg or not ffprobe:
        raise VideoEditingError("MEDIA_RENDER_TOOLS_UNAVAILABLE")
    _verify_sources(timeline)
    width, height = FRAME_SIZES[timeline.format_ratio]
    has_audio = bool(audio_clips)

    with tempfile.TemporaryDirectory(prefix="timeline-render-", dir=output.parent) as temporary:
        work = Path(temporary)
        caption_layouts: list[dict[str, Any]] = []
        overlays = _overlay_filters(timeline, duration=duration, width=width, height=height,
                                    ffmpeg=ffmpeg, work=work, layout_readback=caption_layouts, **run_options)
        audio = _render_audio(timeline, duration=duration, ffmpeg=ffmpeg, work=work, **run_options)
        rendered = work / ("media.mp4" if output_kind == "video" else "media.wav")
        if video_tracks:
            segments: list[Path] = []
            asset_paths = {asset.asset_id: asset.path for asset in timeline.assets}
            for index, clip in enumerate(video_tracks[0].clips):
                frame_count = _frame_at(clip.timeline_start + clip.duration_sec) - _frame_at(clip.timeline_start)
                if frame_count < 1:
                    raise VideoEditingError("VIDEO_CLIP_SHORTER_THAN_OUTPUT_FRAME")
                before = transitions.get(index, {}).get("before_cut_frames", 0)
                after = transitions.get(index + 1, {}).get("after_cut_frames", 0)
                frame_count += before + after
                segment = work / f"clip-{index:03d}.mp4"
                _run([ffmpeg, "-v", "error", "-nostdin", "-n", "-filter_threads", "1",
                      "-filter_complex_threads", "1", "-threads", "1", "-ss", _number(clip.source_in - before / FRAME_RATE),
                      "-protocol_whitelist", "file", "-format_whitelist", MEDIA_INPUT_DEMUXERS,
                      "-i", asset_paths[clip.media_asset_id], "-frames:v", str(frame_count), "-map", "0:v:0",
                      "-an", "-vf", f"setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=decrease,"
                      f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FRAME_RATE}",
                      "-c:v", "libx264", "-preset", "veryfast", "-threads:v", "1", "-pix_fmt", "yuv420p",
                      str(segment)], cwd=work, **run_options)
                segments.append(segment)

            command = [ffmpeg, "-v", "error", "-nostdin", "-n", "-filter_complex_threads", "1"]
            for segment in segments:
                command += ["-protocol_whitelist", "file", "-format_whitelist", MEDIA_INPUT_DEMUXERS,
                            "-i", str(segment)]
            if audio is not None:
                command += ["-protocol_whitelist", "file", "-format_whitelist", MEDIA_INPUT_DEMUXERS,
                            "-i", str(audio)]
            if transitions:
                graph = [f"[{index}:v:0]settb=1/{FRAME_RATE},setpts=PTS-STARTPTS[v{index}]"
                         for index in range(len(segments))]
                current = "v0"
                for index in range(1, len(segments)):
                    item = transitions.get(index)
                    merge = (f"xfade=transition=fade:duration={_number(item['duration_frames'] / FRAME_RATE)}:"
                             f"offset={_number(item['start_frame'] / FRAME_RATE)}" if item else
                             f"concat=n=2:v=1:a=0,settb=1/{FRAME_RATE},setpts=PTS-STARTPTS")
                    graph.append(f"[{current}][v{index}]{merge}[merged{index}]")
                    current = f"merged{index}"
                graph.append(f"[{current}]trim=end_frame={_frame_at(duration)},setpts=PTS-STARTPTS" +
                             ("," + ",".join(overlays) if overlays else "") + "[outv]")
            else:
                graph = [f"[{index}:v:0]setpts=PTS-STARTPTS[v{index}]" for index in range(len(segments))]
                graph.append("".join(f"[v{index}]" for index in range(len(segments))) +
                             f"concat=n={len(segments)}:v=1:a=0" +
                             ("," + ",".join(overlays) if overlays else "") + "[outv]")
            command += ["-filter_complex", ";".join(graph), "-map", "[outv]"]
            if audio is not None:
                command += ["-map", f"{len(segments)}:a:0", "-c:a", "aac", "-b:a", "192k",
                            "-ar", str(SAMPLE_RATE)]
            else:
                command += ["-an"]
            command += ["-c:v", "libx264", "-preset", "veryfast", "-threads:v", "1", "-pix_fmt", "yuv420p",
                        "-t", _number(duration), "-map_metadata", "-1",
                        "-metadata", "comment=Demo - source rights not verified", "-movflags", "+faststart",
                        str(rendered)]
            # A complete programme can take longer than the command helper's
            # short default. Keep a finite duration-based budget and the same
            # cancellation callback, rather than discarding a valid long render.
            _run(command, cwd=work, timeout=max(60.0, duration * 4.0), **run_options)
        elif audio is not None:
            shutil.copyfile(audio, rendered)
        else:
            raise VideoEditingError("AUDIO_EXPORT_REQUIRES_AUDIO_SOURCE")

        peak_processing = {"true_peak_verified": False, "true_peak_status": "not_applicable",
                           "final_true_peak_limit_dbtp": None, "initial_true_peak_dbtp": None,
                           "initial_loudness": None, "peak_correction_db": 0.0, "peak_correction_passes": 0}
        if has_audio:
            rendered, loudness, peak_processing = _verify_final_audio_peak(
                rendered, audio, ffmpeg=ffmpeg, output_kind=output_kind, duration=duration, **run_options,
            )
        measured = _probe_output(rendered, ffprobe, output_kind=output_kind,
                                 duration=duration, has_audio=has_audio)
        if has_audio:
            measured["loudness"] = loudness
        _verify_sources(timeline)
        if check_continue:
            check_continue()
        created = False
        try:
            with output.open("xb") as destination, rendered.open("rb") as source:
                created = True
                shutil.copyfileobj(source, destination)
        except Exception:
            if created:
                output.unlink(missing_ok=True)
            raise

    digest = hashlib.sha256()
    with output.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return {"state": "rendered_verified", "output_kind": output_kind, "timeline_version": timeline.version,
            "media_sha256": digest.hexdigest(), "size_bytes": output.stat().st_size,
            "measurement": measured, "renderer": "lumenis-timeline-4",
            "overlay_processing": {"count": len(timeline.overlays),
                                   "profile": ("mixed-literal-windows-v2" if caption_layouts else
                                               "literal-cjk-windows-v1" if timeline.overlays else None),
                                   **({"measured_layouts": caption_layouts} if caption_layouts else {})},
            "transition_processing": {"profile": "centred-handles-30fps-v1" if transitions else None,
                                      "visual_only": True, "applied": list(transitions.values())},
            "audio_processing": {"pre_encode_sample_peak_limit_dbfs": -1 if has_audio else None,
                                 "limiter_latency_compensated": has_audio,
                                 "ducked_music_clips": len(ducked_clips),
                                 "loudness_normalized": False, **peak_processing},
            "rights_state": "unknown", "publish_status": "not_performed"}
