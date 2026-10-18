"""Bounded full-frame reference measurements, with explicitly sampled review sheets.

Every accepted frame is decoded in presentation order and bound to FFprobe PTS.
Small analysis pixels and deterministic change peaks do not imply visual semantic
understanding, confirmed shots, human review or permission to reuse source assets.
The caller retains source-use/Artifact/version permissions.
"""
from __future__ import annotations

from bisect import bisect_right
import csv
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile
from typing import Any, Callable

from . import rendering
from .video_editing import MEDIA_INPUT_DEMUXERS, MediaAsset, VideoEditingError, _ffprobe_path, fingerprint_local_media


MAX_DURATION_SECONDS = 120.0
MAX_FRAMES = 7200
ANALYSIS_WIDTH, ANALYSIS_HEIGHT = 160, 90
CONTACT_INTERVAL_SECONDS = .5
CONTACT_CELLS_PER_PAGE = 24
MAX_CONTACT_PAGES = 10
MAX_PEAK_CANDIDATES = 128
PIXEL_CHANGE_THRESHOLD = .08
EDGE_THRESHOLD = .12
PEAK_MEAN_THRESHOLD = .08
PEAK_AREA_THRESHOLD = .10


def _check(callback) -> None:
    if callback:
        callback()


def _verify_source(asset: MediaAsset, check_cancel) -> None:
    from shared_artifacts import validate_local_asset
    _check(check_cancel)
    path = validate_local_asset(asset.path)
    if str(path) != asset.path or fingerprint_local_media(str(path)).to_dict() != asset.to_dict():
        raise VideoEditingError("REFERENCE_SOURCE_CHANGED")
    _check(check_cancel)


def _probe_json(command: list[str], path: Path, *, check_cancel, maximum: int = 8 * 1024 * 1024) -> dict:
    def check():
        _check(check_cancel)
        if path.exists() and path.stat().st_size > maximum:
            raise VideoEditingError("REFERENCE_PROBE_LIMIT_EXCEEDED")
    rendering._run(command + ["-of", "json", "-o", str(path)], cwd=path.parent,
                   timeout=120, check_continue=check)
    check()
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            raise ValueError("invalid metadata")
        return result
    except (OSError, ValueError, TypeError) as exc:
        raise VideoEditingError("REFERENCE_PROBE_INVALID") from exc


def _video_metadata(asset: MediaAsset, *, ffprobe: str, work: Path, check_cancel) -> tuple[dict, int, int]:
    result = _probe_json([
        ffprobe, "-v", "error", "-protocol_whitelist", "file", "-format_whitelist", MEDIA_INPUT_DEMUXERS,
        "-select_streams", "v", "-show_entries",
        "stream=index,width,height,time_base,sample_aspect_ratio:stream_disposition=attached_pic:stream_side_data=rotation",
        asset.path,
    ], work / "streams.json", check_cancel=check_cancel, maximum=65536)
    streams = result.get("streams")
    if not isinstance(streams, list) or len(streams) != 1:
        raise VideoEditingError("REFERENCE_SINGLE_VIDEO_STREAM_REQUIRED")
    stream = streams[0]
    try:
        width, height = int(stream["width"]), int(stream["height"])
        timebase = Fraction(stream["time_base"])
        sar_raw = stream.get("sample_aspect_ratio", "1:1")
        sar = Fraction(sar_raw.replace(":", "/")) if sar_raw not in {"N/A", "0:1"} else Fraction(1)
        if (not 1 <= width <= 8192 or not 1 <= height <= 8192 or width * height > 33554432
                or not 0 < timebase <= 1 or not 1 / 100 <= sar <= 100
                or stream.get("disposition", {}).get("attached_pic", 0)):
            raise ValueError("unsupported frame geometry")
        for side in stream.get("side_data_list", []):
            if float(side.get("rotation", 0)) % 360:
                raise VideoEditingError("REFERENCE_ROTATED_VIDEO_REQUIRES_NORMALIZATION")
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        if isinstance(exc, VideoEditingError):
            raise
        raise VideoEditingError("REFERENCE_VIDEO_METADATA_INVALID") from exc
    display_width = width * float(sar)
    scale = min(1.0, ANALYSIS_WIDTH / display_width, ANALYSIS_HEIGHT / height)
    analysis_width, analysis_height = max(1, round(display_width * scale)), max(1, round(height * scale))
    return {"stream_index": int(stream["index"]), "encoded_width": width, "encoded_height": height,
            "sample_aspect_ratio": str(sar), "time_base": str(timebase),
            "rotation_degrees": 0, "spatial_scale": scale}, analysis_width, analysis_height


def _frame_timestamps(asset: MediaAsset, *, ffprobe: str, work: Path, count: int,
                      metadata: dict, check_cancel) -> list[dict[str, Any]]:
    result = _probe_json([
        ffprobe, "-v", "error", "-err_detect", "explode", "-protocol_whitelist", "file",
        "-format_whitelist", MEDIA_INPUT_DEMUXERS, "-select_streams", "v:0", "-show_frames",
        "-show_entries", "frame=pts,pts_time,duration_time,pkt_duration_time,width,height", asset.path,
    ], work / "frames.json", check_cancel=check_cancel)
    frames = result.get("frames")
    if not isinstance(frames, list) or len(frames) != count:
        raise VideoEditingError("REFERENCE_FRAME_COUNT_MISMATCH")
    timestamps = []
    timebase = Fraction(metadata["time_base"])
    callback_error = None
    def check():
        nonlocal callback_error
        try:
            _check(check_cancel)
        except BaseException as exc:
            callback_error = exc
            raise
    try:
        for index, frame in enumerate(frames):
            check()
            pts = int(frame["pts"])
            seconds = float(frame["pts_time"])
            exact_seconds = float(pts * timebase)
            duration_raw = frame.get("duration_time", frame.get("pkt_duration_time"))
            duration = None if duration_raw in (None, "N/A", "0", "0.000000") else float(duration_raw)
            if (not math.isfinite(seconds) or abs(seconds) > 1_000_000_000
                    or abs(seconds - exact_seconds) > .000002
                    or timestamps and pts <= timestamps[-1]["pts"]
                    or (int(frame["width"]), int(frame["height"])) != (metadata["encoded_width"], metadata["encoded_height"])
                    or duration is not None and (not math.isfinite(duration) or duration <= 0)):
                raise ValueError("unstable or unsupported frame timestamps")
            timestamps.append({"frame_index": index, "pts": pts, "pts_sec": exact_seconds,
                               "frame_duration_sec": duration})
        origin = timestamps[0]["pts_sec"]
        end = timestamps[-1]["pts_sec"] + (timestamps[-1]["frame_duration_sec"] or 0)
        if end - origin > MAX_DURATION_SECONDS + .000002:
            raise VideoEditingError("REFERENCE_DURATION_LIMIT_EXCEEDED")
        for frame in timestamps:
            frame["elapsed_sec"] = frame["pts_sec"] - origin
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        if exc is callback_error or isinstance(exc, VideoEditingError):
            raise
        raise VideoEditingError("REFERENCE_FRAME_PTS_INVALID") from exc
    return timestamps


def _measure_frames(raw: Path, *, width: int, height: int, timestamps: list[dict], check_cancel) -> list[dict]:
    import numpy as np
    rows = []
    previous = None
    frame_bytes = width * height * 3
    with raw.open("rb") as source:
        for timestamp in timestamps:
            _check(check_cancel)
            pixels = source.read(frame_bytes)
            if len(pixels) != frame_bytes:
                raise VideoEditingError("REFERENCE_DECODE_TRUNCATED")
            rgb = np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 3).astype(np.float32)
            # Explicit linear combination of decoded RGB code values. This is
            # an image-change measure, not physical luminance or colour science.
            gray = (rgb[:, :, 0] * .2126 + rgb[:, :, 1] * .7152 + rgb[:, :, 2] * .0722) / 255
            edges_x, edges_y = np.abs(np.diff(gray, axis=1)), np.abs(np.diff(gray, axis=0))
            edge_count = edges_x.size + edges_y.size
            edge_density = (int(np.count_nonzero(edges_x > EDGE_THRESHOLD)) +
                            int(np.count_nonzero(edges_y > EDGE_THRESHOLD))) / edge_count if edge_count else 0.0
            difference = None if previous is None else np.abs(gray - previous)
            rows.append({**timestamp, "mean_luminance": round(float(gray.mean()), 8),
                         "mean_adjacent_difference": None if difference is None else round(float(difference.mean()), 8),
                         "changed_area_fraction": None if difference is None else round(float((difference > PIXEL_CHANGE_THRESHOLD).mean()), 8),
                         "edge_density": round(edge_density, 8)})
            previous = gray
        if source.read(1):
            raise VideoEditingError("REFERENCE_FRAME_COUNT_MISMATCH")
    return rows


def _peaks_and_shots(rows: list[dict]) -> tuple[list[dict], list[dict], int]:
    scores = [(row["mean_adjacent_difference"] or 0) * (.5 + .5 * (row["changed_area_fraction"] or 0)) for row in rows]
    peaks = [index for index in range(1, len(rows))
             if rows[index]["mean_adjacent_difference"] >= PEAK_MEAN_THRESHOLD
             and rows[index]["changed_area_fraction"] >= PEAK_AREA_THRESHOLD
             and scores[index] >= scores[index - 1]
             and (index + 1 == len(rows) or scores[index] >= scores[index + 1])]
    observed = len(peaks)
    chosen = sorted(sorted(peaks, key=lambda index: (-scores[index], index))[:MAX_PEAK_CANDIDATES])
    candidates = [{"frame_index": index, "pts": rows[index]["pts"], "pts_sec": rows[index]["pts_sec"],
                   "elapsed_sec": rows[index]["elapsed_sec"], "change_score": round(scores[index], 8),
                   "mean_adjacent_difference": rows[index]["mean_adjacent_difference"],
                   "changed_area_fraction": rows[index]["changed_area_fraction"],
                   "status": "human_review_required_not_confirmed_cut"} for index in chosen]
    boundaries = [0] + chosen + [len(rows)]
    shots = []
    for number, (first, following) in enumerate(zip(boundaries, boundaries[1:]), 1):
        end = rows[following]["pts_sec"] if following < len(rows) else rows[-1]["pts_sec"] + (rows[-1]["frame_duration_sec"] or 0)
        shots.append({"candidate_id": f"shot-{number:03d}", "first_frame_index": first,
                      "last_frame_index": following - 1, "frame_count": following - first,
                      "start_pts_sec": rows[first]["pts_sec"], "end_pts_sec": end,
                      "end_boundary": "next_candidate_frame_pts" if following < len(rows) else (
                          "last_frame_pts_plus_duration" if rows[-1]["frame_duration_sec"] else "last_frame_pts_duration_unknown"),
                      "status": "human_review_required_not_confirmed_shot"})
    return candidates, shots, observed


def _csv_bytes(rows: list[dict]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _contact_sheets(raw: Path, *, width: int, height: int, rows: list[dict], check_cancel) -> tuple[dict, list[dict]]:
    from PIL import Image, ImageDraw, ImageFont
    elapsed = [row["elapsed_sec"] for row in rows]
    targets = [index * CONTACT_INTERVAL_SECONDS for index in range(math.floor(elapsed[-1] / CONTACT_INTERVAL_SECONDS) + 1)]
    pages = math.ceil(len(targets) / CONTACT_CELLS_PER_PAGE)
    if pages > MAX_CONTACT_PAGES:
        raise VideoEditingError("REFERENCE_CONTACT_PAGE_LIMIT_EXCEEDED")
    files, cells = {}, []
    cell_width, cell_height, margin = 320, 210, 12
    sheet_width = 4 * (cell_width + margin) + margin
    font = ImageFont.load_default()
    frame_bytes = width * height * 3
    with raw.open("rb") as source:
        for page in range(pages):
            _check(check_cancel)
            page_targets = targets[page * CONTACT_CELLS_PER_PAGE:(page + 1) * CONTACT_CELLS_PER_PAGE]
            sheet_height = math.ceil(len(page_targets) / 4) * (cell_height + margin) + 42
            image = Image.new("RGB", (sheet_width, sheet_height), (15, 23, 38))
            draw = ImageDraw.Draw(image)
            draw.text((margin, 10), f"REFERENCE CONTACT {page + 1:02d} / {pages:02d} | sampled every 0.5 s | not human-reviewed", font=font, fill="white")
            filename = f"contact-sheet-{page + 1:02d}.png"
            for slot, target in enumerate(page_targets):
                _check(check_cancel)
                index = max(0, bisect_right(elapsed, target) - 1)
                source.seek(index * frame_bytes)
                pixels = source.read(frame_bytes)
                if len(pixels) != frame_bytes:
                    raise VideoEditingError("REFERENCE_CONTACT_FRAME_MISSING")
                thumb = Image.frombytes("RGB", (width, height), pixels)
                thumb.thumbnail((cell_width, 180), resample=Image.Resampling.LANCZOS)
                left = margin + (slot % 4) * (cell_width + margin)
                top = 35 + (slot // 4) * (cell_height + margin)
                image.paste(thumb, (left + (cell_width - thumb.width) // 2, top + (180 - thumb.height) // 2))
                draw.text((left, top + 182), f"sample {target:.3f}s | frame {index}", font=font, fill="white")
                draw.text((left, top + 194), f"PTS {rows[index]['pts_sec']:.6f}s", font=font, fill="white")
                cells.append({"filename": filename, "slot": slot, "requested_elapsed_sec": target,
                              "frame_index": index, "pts": rows[index]["pts"], "pts_sec": rows[index]["pts_sec"],
                              "actual_elapsed_sec": elapsed[index], "human_reviewed": False})
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            data = buffer.getvalue()
            with Image.open(io.BytesIO(data)) as decoded:
                decoded.load()
                if decoded.format != "PNG" or decoded.size != (sheet_width, sheet_height):
                    raise VideoEditingError("REFERENCE_CONTACT_VERIFICATION_FAILED")
            files[filename] = data
    return files, cells


def build_reference_analysis_files(asset: MediaAsset, *, check_cancel: Callable[[], None] | None = None) -> dict[str, Any]:
    """Analyze an entire admitted video or reject it; never return a truncated pass."""
    from shared_artifacts import _ffmpeg_path
    _check(check_cancel)
    if not isinstance(asset, MediaAsset):
        raise VideoEditingError("REFERENCE_FINGERPRINTED_ASSET_REQUIRED")
    asset.validate()
    if not asset.has_video:
        raise VideoEditingError("REFERENCE_VIDEO_REQUIRED")
    if asset.duration_sec > MAX_DURATION_SECONDS:
        raise VideoEditingError("REFERENCE_DURATION_LIMIT_EXCEEDED")
    _verify_source(asset, check_cancel)
    ffmpeg, ffprobe = _ffmpeg_path(), _ffprobe_path()
    if not ffmpeg or not ffprobe:
        raise VideoEditingError("REFERENCE_TOOLCHAIN_UNAVAILABLE")
    with tempfile.TemporaryDirectory(prefix="lumenis-reference-") as temporary:
        work = Path(temporary)
        metadata, width, height = _video_metadata(asset, ffprobe=ffprobe, work=work, check_cancel=check_cancel)
        raw = work / "frames.rgb"
        frame_bytes = width * height * 3
        def check_decode():
            _check(check_cancel)
            if raw.exists() and raw.stat().st_size > (MAX_FRAMES + 1) * frame_bytes:
                raise VideoEditingError("REFERENCE_DECODE_LIMIT_EXCEEDED")
        rendering._run([
            ffmpeg, "-v", "error", "-xerror", "-nostdin", "-n", "-threads", "1", "-filter_threads", "1",
            "-err_detect", "explode", "-noautorotate", "-protocol_whitelist", "file", "-format_whitelist", MEDIA_INPUT_DEMUXERS,
            "-i", asset.path, "-map", "0:v:0", "-an", "-sn", "-dn", "-vf", f"scale={width}:{height}:flags=area,setsar=1",
            "-fps_mode", "passthrough", "-frames:v", str(MAX_FRAMES + 1), "-pix_fmt", "rgb24",
            "-c:v", "rawvideo", "-threads:v", "1", "-f", "rawvideo", str(raw),
        ], cwd=work, timeout=180, check_continue=check_decode)
        size = raw.stat().st_size
        if not size or size % frame_bytes:
            raise VideoEditingError("REFERENCE_DECODE_TRUNCATED")
        count = size // frame_bytes
        if count > MAX_FRAMES:
            raise VideoEditingError("REFERENCE_FRAME_LIMIT_EXCEEDED")
        timestamps = _frame_timestamps(asset, ffprobe=ffprobe, work=work, count=count,
                                       metadata=metadata, check_cancel=check_cancel)
        rows = _measure_frames(raw, width=width, height=height, timestamps=timestamps, check_cancel=check_cancel)
        peaks, shots, observed_peaks = _peaks_and_shots(rows)
        files, cells = _contact_sheets(raw, width=width, height=height, rows=rows, check_cancel=check_cancel)
        files["frame-metrics.csv"] = _csv_bytes(rows)
        files["shot-candidates.csv"] = _csv_bytes(shots)
    _verify_source(asset, check_cancel)
    report = {
        "schema": "lumenis.reference-frame-analysis/v1", "state": "analyzed_verified",
        "source_asset_id": asset.asset_id, "source_sha256": asset.sha256,
        "source_duration_sec": asset.duration_sec, "source_rights_status": asset.rights_status,
        "video": metadata, "analysis_width": width, "analysis_height": height,
        "decoded_frames": count, "ffprobe_frames": len(timestamps), "frames_analyzed": len(rows),
        "decode_all_frames": "passed", "decode_termination": "end_of_stream_before_sentinel_limit",
        "frame_pts_binding": "strict_one_to_one_presentation_order_no_fps_resampling",
        "first_pts_sec": rows[0]["pts_sec"], "last_pts_sec": rows[-1]["pts_sec"],
        "last_frame_duration_sec": rows[-1]["frame_duration_sec"],
        "measurements": {"rgb_to_gray": "(0.2126R + 0.7152G + 0.0722B) / 255 code-value measure",
                         "adjacent_difference": "mean absolute difference of all analysis pixels",
                         "changed_area": "fraction of analysis pixels with absolute difference above threshold",
                         "pixel_change_threshold": PIXEL_CHANGE_THRESHOLD,
                         "edge_density": "fraction of horizontal and vertical neighbour pairs above threshold",
                         "edge_threshold": EDGE_THRESHOLD, "spatial_resolution_reduced": metadata["spatial_scale"] < 1,
                         "temporal_sampling": "none_all_frames"},
        "peak_selection": {"method": "local_change_score_maxima_then_strongest_bounded_candidates",
                           "mean_difference_threshold": PEAK_MEAN_THRESHOLD, "changed_area_threshold": PEAK_AREA_THRESHOLD,
                           "observed_candidates": observed_peaks, "returned_candidates": len(peaks),
                           "omitted_candidates": observed_peaks - len(peaks), "limit": MAX_PEAK_CANDIDATES},
        "peak_candidates": peaks, "shot_candidates": shots,
        "contact_sheet": {"interval_sec": CONTACT_INTERVAL_SECONDS, "selection": "latest_presented_frame_at_or_before_target",
                          "sample_count": len(cells), "page_count": len({cell['filename'] for cell in cells}),
                          "maximum_pages": MAX_CONTACT_PAGES, "cells": cells,
                          "source_pixels": "same_downscaled_rgb_frames_used_for_full_frame_measurements"},
        "human_reviewed_frames": 0, "human_reviewed_contact_cells": 0,
        "ai_visual_semantics_performed": False, "confirmed_shot_boundaries": False,
        "published": False, "automatic_editing": False,
        "limits": {"maximum_duration_sec": MAX_DURATION_SECONDS, "maximum_frames": MAX_FRAMES},
        "limitations": ["Change peaks are not verified shots, interaction steps or semantic story nodes.",
                        "Contact sheets are temporal samples; no human review has been performed.",
                        "Analysis pixels are downscaled; detail-sensitive findings need source inspection.",
                        "Analysis does not grant rights to reuse source music, brands, characters or visuals."],
        "outputs": {name: {"filename": name, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
                    for name, data in files.items()},
    }
    files["analysis.json"] = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode()
    _check(check_cancel)
    return {"files": files, "report": report}
