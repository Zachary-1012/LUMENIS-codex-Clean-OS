"""Verified single-clip local rendering under the existing Shared media owner.

Artifact registration, source authorization and export permission remain caller
responsibilities. Unsupported timeline features fail instead of disappearing.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .video_editing import (
    MEDIA_INPUT_DEMUXERS, Timeline, TimelineClip, VideoEditingError,
    _ffprobe_path, fingerprint_local_media,
)

SAMPLE_RATE = 48000
FRAME_RATE = 30
FRAME_SIZES = {"9:16": (720, 1280), "16:9": (1280, 720), "3:4": (810, 1080), "4:5": (864, 1080)}


def _run(command: list[str], *, cwd: Path, timeout: int = 60) -> str:
    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, check=False, shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise VideoEditingError("MEDIA_RENDER_PROCESS_FAILED") from exc
    if result.returncode != 0:
        # Decoder messages can contain private source paths. Keep them out of API errors.
        raise VideoEditingError("MEDIA_RENDER_FAILED")
    return result.stderr


def _number(value: float) -> str:
    return f"{value:.6f}"


def _audio_filter(clip: TimelineClip) -> str:
    duration = clip.duration_sec
    mix = clip.audio_mix
    filters = [
        f"atrim=start={_number(clip.source_in)}:end={_number(clip.source_out)}",
        # Anchor to the cut boundary, not the first decoded sound: a source
        # stream can legitimately begin later than its video. Keep that silence.
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


def _probe_output(path: Path, ffprobe: str, *, duration: float, has_audio: bool) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-protocol_whitelist", "file", "-format_whitelist", "mov",
             "-count_frames", "-show_entries",
             "stream=codec_type,start_time,nb_read_frames,sample_rate,channels:format=duration",
             "-of", "json", "-i", str(path)],
            capture_output=True, text=True, timeout=30, check=True, shell=False,
        )
        probe = json.loads(result.stdout)
        streams = probe["streams"]
        audio = [s for s in streams if s.get("codec_type") == "audio"]
        video = [s for s in streams if s.get("codec_type") == "video"]
        actual = float(probe["format"]["duration"])
        starts = [float(s.get("start_time", 0)) for s in audio + video]
        frames = int(video[0]["nb_read_frames"])
        if (len(video) != 1 or len(audio) != int(has_audio) or frames < 1
                or not math.isfinite(actual) or abs(actual - duration) > 2 / FRAME_RATE
                or any(not math.isfinite(t) or abs(t) > 2 / FRAME_RATE for t in starts)
                or (audio and (int(audio[0]["sample_rate"]) != SAMPLE_RATE or audio[0]["channels"] != 2))):
            raise ValueError("output differs from timeline")
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise VideoEditingError("RENDER_OUTPUT_VERIFICATION_FAILED") from exc
    return {"requested_duration_sec": duration, "actual_duration_sec": actual,
            "audio_streams": len(audio), "video_streams": len(video),
            "video_frames": frames, "stream_start_seconds": starts}


def render_timeline(timeline: Timeline, output: Path, *, output_kind: str = "video") -> dict[str, Any]:
    """Render one video clip to a new private-Temp MP4; never authorize export."""
    timeline.validate()
    clips = [(track, clip) for track in timeline.tracks for clip in track.clips]
    if output_kind != "video" or len(clips) != 1 or clips[0][0].kind != "video":
        raise VideoEditingError("SINGLE_VIDEO_CLIP_RENDER_REQUIRED")
    _, clip = clips[0]
    if timeline.transitions or timeline.overlays or clip.audio_mix.ducking or clip.timeline_start != 0:
        raise VideoEditingError("TIMELINE_FEATURE_RENDER_NOT_SUPPORTED")
    if timeline.format_ratio not in FRAME_SIZES:
        raise VideoEditingError("FORMAT_RATIO_NOT_SUPPORTED")
    if round(clip.duration_sec * FRAME_RATE) < 1:
        raise VideoEditingError("VIDEO_CLIP_SHORTER_THAN_OUTPUT_FRAME")
    output = Path(output)
    try:
        parent = output.parent.resolve(strict=True)
        temp = Path(tempfile.gettempdir()).resolve()
        if (not output.is_absolute() or output.suffix.lower() != ".mp4"
                or output.exists() or output.is_symlink() or parent == temp
                or parent != output.parent.absolute() or not parent.is_relative_to(temp)):
            raise ValueError("not a new private temporary output")
    except (OSError, ValueError) as exc:
        raise VideoEditingError("NEW_PRIVATE_TEMP_OUTPUT_REQUIRED") from exc
    ffprobe = _ffprobe_path()
    ffmpeg = Path(ffprobe).with_name("ffmpeg.exe" if os.name == "nt" else "ffmpeg") if ffprobe else None
    if ffmpeg is None or not ffmpeg.is_file():
        raise VideoEditingError("MEDIA_RENDER_TOOLS_UNAVAILABLE")
    asset = next(a for a in timeline.assets if a.asset_id == clip.media_asset_id)
    if fingerprint_local_media(asset.path).to_dict() != asset.to_dict():
        raise VideoEditingError("SOURCE_MEDIA_CHANGED")
    has_audio = clip.audio_role != "muted" and asset.audio_stream_count > 0
    width, height = FRAME_SIZES[timeline.format_ratio]
    graph = (
        f"[0:v:0]trim=start={_number(clip.source_in)}:end={_number(clip.source_out)},"
        f"setpts=PTS-{_number(clip.source_in)}/TB,fps={FRAME_RATE}:start_time=0,"
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v]"
    )
    command = [str(ffmpeg), "-v", "error", "-nostdin", "-n", "-filter_complex_threads", "1",
               "-threads", "1", "-protocol_whitelist", "file", "-format_whitelist",
               MEDIA_INPUT_DEMUXERS, "-i", asset.path]
    if has_audio:
        stream = clip.audio_stream_index if clip.audio_stream_index is not None else 0
        graph += f";[0:a:{stream}]" + _audio_filter(clip) + "[a]"
    with tempfile.TemporaryDirectory(prefix="timeline-render-", dir=parent) as temporary:
        work = Path(temporary)
        rendered = work / "media.mp4"
        command += ["-filter_complex", graph, "-map", "[v]"]
        command += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", str(SAMPLE_RATE)] if has_audio else ["-an"]
        command += ["-c:v", "libx264", "-preset", "veryfast", "-threads:v", "1", "-pix_fmt", "yuv420p",
                    "-t", _number(clip.duration_sec), "-map_metadata", "-1",
                    "-metadata", "comment=Demo - source rights not verified", "-movflags", "+faststart", str(rendered)]
        _run(command, cwd=work)
        measured = _probe_output(rendered, ffprobe, duration=clip.duration_sec, has_audio=has_audio)
        if fingerprint_local_media(asset.path).to_dict() != asset.to_dict():
            raise VideoEditingError("SOURCE_MEDIA_CHANGED")
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
    return {"state": "rendered_verified", "output_kind": "video", "timeline_version": timeline.version,
            "media_sha256": digest.hexdigest(), "size_bytes": output.stat().st_size,
            "measurement": measured, "renderer": "lumenis-single-clip-1",
            "rights_state": "unknown", "publish_status": "not_performed"}
