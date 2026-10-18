"""Local, deterministic cover variants for the existing media Artifact owner.

Temporal sample candidates are not semantic keyframe detection. User-authored
copy is bound to supplied body text by exact matching, not AI fact checking.
The caller retains export permission, project/version and publication controls.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import tempfile
import unicodedata
from pathlib import Path

from .video_editing import MediaAsset, VideoEditingError, fingerprint_local_media, MEDIA_INPUT_DEMUXERS


def build_cover_files(asset: MediaAsset, *, audience: str, industry: str, visual_hook: str,
                      body_text: str, count: int = 3, check_cancel=None):
    from PIL import Image, ImageDraw, ImageFont, ImageStat, ImageFilter
    from shared_artifacts import _ffmpeg_path
    from .rendering import CAPTION_FONT, _verify_caption_glyphs, _run
    asset.validate()
    if not asset.has_video:
        raise VideoEditingError('COVER_REQUIRES_VIDEO')
    if type(count) is not int or not 1 <= count <= 6:
        raise VideoEditingError('COVER_COUNT_INVALID')
    if not isinstance(body_text, str) or not 1 <= len(body_text) <= 100000:
        raise VideoEditingError('COVER_BODY_REQUIRED')
    copy = {'audience': audience, 'industry': industry, 'visual_hook': visual_hook}
    for text in copy.values():
        if (not isinstance(text, str) or not text.strip() or len(text) > 36
                or any(unicodedata.category(c).startswith('C') for c in text)):
            raise VideoEditingError('COVER_COPY_INVALID')
        if text not in body_text:
            raise VideoEditingError('COVER_COPY_NOT_IN_BODY')
    if check_cancel:
        check_cancel()
    if fingerprint_local_media(asset.path).sha256 != asset.sha256:
        raise VideoEditingError('COVER_MEDIA_CHANGED')
    ffmpeg = _ffmpeg_path()
    if not ffmpeg or not CAPTION_FONT.is_file():
        raise VideoEditingError('COVER_TOOLCHAIN_UNAVAILABLE')
    _verify_caption_glyphs(''.join(copy.values()))
    files = {}; candidates = []
    with tempfile.TemporaryDirectory(prefix='lumenis-cover-') as temp:
        work = Path(temp)
        # Real content-change candidates, not encoder I-frame labels and not
        # semantic importance. Limit the analysis window explicitly; supplement
        # with whole-source temporal samples when fewer cuts are observed.
        scan_duration = min(asset.duration_sec, 120.0)
        scene_log = _run([ffmpeg, '-v', 'info', '-nostdin', '-threads', '1',
            '-protocol_whitelist', 'file', '-format_whitelist', MEDIA_INPUT_DEMUXERS,
            '-i', asset.path, '-t', str(scan_duration), '-an', '-vf',
            "scale=160:90,select='gt(scene,0.25)',showinfo", '-vsync', 'vfr',
            '-frames:v', '24', '-f', 'null', '-'], cwd=work, timeout=60, check_continue=check_cancel)
        scene_times = sorted({float(x) for x in re.findall(r'pts_time:([0-9.eE+-]+)', scene_log)
                              if 0 <= float(x) < scan_duration})
        covered_end = scene_times[-1] if len(scene_times) >= 24 else scan_duration
        candidates_at = [(t, 'scene_change_threshold_0.25') for t in scene_times]
        candidates_at += [(asset.duration_sec * (i+1)/(count+1), 'uniform_temporal_fallback') for i in range(count)]
        selected = []
        for at, method in candidates_at:
            if all(abs(at-old[0]) >= min(.2, asset.duration_sec/(2*count+2)) for old in selected):
                selected.append((at,method))
            if len(selected) == count: break
        for index, (at, method) in enumerate(selected):
            if check_cancel:
                check_cancel()
            output = work / f'frame-{index}.png'
            _run([ffmpeg, '-v', 'error', '-nostdin', '-n', '-threads', '1',
                  '-protocol_whitelist', 'file', '-format_whitelist', MEDIA_INPUT_DEMUXERS,
                  '-ss', str(at), '-i', asset.path, '-map', '0:v:0', '-an', '-frames:v', '1',
                  '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2',
                  '-threads', '1', str(output)], cwd=work, timeout=60, check_continue=check_cancel)
            with Image.open(output) as source:
                source.load(); canvas = source.convert('RGB')
            gray = canvas.convert('L')
            statistics = {'mean_luma': round(ImageStat.Stat(gray).mean[0], 3),
                          'edge_mean': round(ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0], 3)}
            draw = ImageDraw.Draw(canvas)
            # Fixed safe layout; dynamic font size is bounded and every line is
            # measured before drawing so long CJK copy never clips silently.
            panel_top = 408 if index % 2 == 0 else 40
            draw.rounded_rectangle((40, panel_top, 1240, panel_top+270), radius=20, fill=(15, 23, 38))
            for row, text in enumerate(copy.values()):
                size = 54 if row == 2 else 44
                while size >= 18:
                    font = ImageFont.truetype(str(CAPTION_FONT), size)
                    box = draw.textbbox((0, 0), text, font=font)
                    if box[2]-box[0] <= 1120:
                        break
                    size -= 1
                if size < 18:
                    raise VideoEditingError('COVER_COPY_LAYOUT_OVERFLOW')
                draw.text((80, panel_top+20+row*78), text, font=font,
                          fill=(255, 214, 92) if row == 2 else (255, 255, 255))
            result = io.BytesIO(); canvas.save(result, format='PNG'); data = result.getvalue()
            filename = f'cover-{index+1:02d}.png'; files[filename] = data
            candidates.append({'filename': filename, 'sha256': hashlib.sha256(data).hexdigest(),
                               'requested_time_sec': round(at, 6), 'width': 1280, 'height': 720,
                               'sampling': method + '_accurate_seek_first_decoded_frame',
                               'measurements': statistics, 'ai_generated': False})
    if check_cancel:
        check_cancel()
    if fingerprint_local_media(asset.path).sha256 != asset.sha256:
        raise VideoEditingError('COVER_MEDIA_CHANGED')
    report = {'schema': 'lumenis.cover-candidates/v1', 'source_asset_id': asset.asset_id,
              'source_sha256': asset.sha256, 'body_sha256': hashlib.sha256(body_text.encode()).hexdigest(),
              'copy': copy, 'copy_check': 'EXACT_SUBSTRING_ONLY_HUMAN_REVIEW_REQUIRED',
              'selection': 'SCENE_CHANGE_AND_TEMPORAL_CANDIDATES_NOT_SEMANTIC_RANKING',
              'scene_analysis': {'threshold': .25, 'covered_start_sec': 0, 'covered_end_sec': covered_end,
                                 'whole_source_analyzed': covered_end >= asset.duration_sec,
                                 'candidate_limit': 24, 'observed_scene_times': scene_times},
              'candidates': candidates, 'published': False}
    files['cover.json'] = json.dumps(report, ensure_ascii=False, indent=2).encode()
    return {'files': files, 'report': report}
