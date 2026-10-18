"""Bounded editorial exchange for the existing Timeline owner.

No application compatibility is inferred from a file round trip. Effects that
this adapter cannot represent are reported before export; unknown relinks/time
bases always block. Media bytes, rights and Artifact persistence stay with the
calling owner. OTIO JSON is emitted without a runtime dependency on OTIO.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from fractions import Fraction
from pathlib import PurePosixPath
from typing import Mapping
from xml.etree import ElementTree as ET

from .video_editing import (Timeline, TimelineClip, TimelineTrack, AudioMix, VideoEditingError,
                            fingerprint_local_media, _ffprobe_path, MEDIA_INPUT_DEMUXERS)

_FORMATS = ('otio', 'fcpxml', 'cmx3600')
_MAX_CLIPS = 128


def _rate(value):
    if not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]{0,5}(?:/[1-9][0-9]{0,5})?', value):
        raise VideoEditingError('INTERCHANGE_TIMEBASE_UNKNOWN')
    result = Fraction(value)
    if not 1 <= result <= 240:
        raise VideoEditingError('INTERCHANGE_TIMEBASE_UNKNOWN')
    return result


def _ref(value):
    # Package-local basenames only: never cause an importer to open a URL/path.
    return (isinstance(value, str) and bool(value) and len(value) <= 180
            and value not in ('.', '..') and PurePosixPath(value).name == value
            and not any(c in value for c in '/\\:%?#')
            and not any(ord(c) < 32 for c in value))


def _sec(value, rate):
    """Recover rational frame endpoints while preserving genuine subframe edits."""
    exact = Fraction(str(value))
    frames = exact * rate
    nearest = round(frames)
    if abs(frames - nearest) <= Fraction(1, 100000):
        return Fraction(nearest, 1) / rate
    return exact.limit_denominator(1_000_000_000)


def _clips(timeline):
    return [c for t in timeline.tracks for c in t.clips]


def _probe_rates(timeline, *, dimensions=None):
    rates = {}
    probe = _ffprobe_path()
    if not probe:
        return rates
    for asset in timeline.assets:
        if not asset.has_video:
            continue
        try:
            result = subprocess.run([probe, '-v', 'error', '-protocol_whitelist', 'file',
                '-format_whitelist', MEDIA_INPUT_DEMUXERS, '-select_streams', 'v:0',
                '-show_entries', 'stream=avg_frame_rate,r_frame_rate,time_base,width,height', '-of', 'json',
                '-i', asset.path], capture_output=True, text=True, check=True, timeout=15)
            stream = json.loads(result.stdout)['streams'][0]
            avg, real = _rate(stream['avg_frame_rate']), _rate(stream['r_frame_rate'])
            if avg == real and Fraction(stream['time_base']) > 0:
                rates[asset.asset_id] = str(avg)
                if dimensions is not None:
                    dimensions[asset.asset_id] = (int(stream['width']), int(stream['height']))
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError):
            continue
    return rates


def preflight_interchange(timeline: Timeline, *, format: str, frame_rate=None,
                          source_frame_rates=None, media_refs=None, check_cancel=None):
    """Read-only deterministic loss assessment, not permission or rights approval."""
    timeline.validate()
    if len(timeline.assets) > 128 or len(timeline.tracks) > 32:
        raise VideoEditingError('INTERCHANGE_RESOURCE_LIMIT')
    issues = []
    def issue(code, severity, clips=()):
        issues.append({'code': code, 'severity': severity, 'clip_ids': sorted(clips)})
    if format not in _FORMATS:
        issue('FORMAT_NOT_SUPPORTED', 'BLOCKED')
    try:
        rate = _rate(frame_rate)
    except VideoEditingError:
        rate = None
        issue('PROJECT_TIMEBASE_UNKNOWN', 'UNKNOWN')
    dimensions = {}
    source_frame_rates = _probe_rates(timeline, dimensions=dimensions)
    media_refs = media_refs if isinstance(media_refs, Mapping) else {}
    clips = _clips(timeline)
    if not clips or len(clips) > _MAX_CLIPS:
        issue('CLIP_COUNT_OUT_OF_BOUNDS', 'BLOCKED')
    used = {c.media_asset_id for c in clips}
    for asset in timeline.assets:
        if asset.asset_id not in used:
            continue
        affected = [c.clip_id for c in clips if c.media_asset_id == asset.asset_id]
        if not _ref(media_refs.get(asset.asset_id)):
            issue('MEDIA_RELINK_UNKNOWN', 'UNKNOWN', affected)
        try:
            source_rate = _rate(source_frame_rates.get(asset.asset_id)) if asset.has_video else rate
        except VideoEditingError:
            source_rate = None
            issue('SOURCE_TIMEBASE_UNKNOWN', 'UNKNOWN', affected)
        # Source time bases are declarations from a verified probe owner, not
        # guessed from the desired output frame rate.
        if format == 'otio' and asset.asset_id in dimensions:
            width, height = dimensions[asset.asset_id]
            if height and Fraction(width,height) != Fraction(timeline.format_ratio.replace(':','/')):
                issue('OUTPUT_FRAME_CONFORM_NOT_PORTABLE', 'LOSS', affected)
        if asset.audio_stream_count > 1:
            issue('SOURCE_AUDIO_STREAM_SELECTION_LOSS', 'LOSS', affected)
    if format == 'cmx3600':
        from .stream_probe import probe_source_streams
        if rate not in (Fraction(24), Fraction(25), Fraction(30), Fraction(50), Fraction(60)):
            issue('CMX_INTEGER_NON_DROP_TIMEBASE_REQUIRED', 'BLOCKED')
        active_tracks = [t for t in timeline.tracks if t.clips]
        if len(active_tracks) != 1 or active_tracks[0].kind != 'video':
            issue('CMX_SINGLE_VIDEO_TRACK_REQUIRED', 'BLOCKED')
        for asset in timeline.assets:
            if asset.asset_id not in used: continue
            affected = [c.clip_id for c in clips if c.media_asset_id == asset.asset_id]
            ref = media_refs.get(asset.asset_id)
            if not isinstance(ref,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,180}',ref):
                issue('CMX_ASCII_RELINK_REQUIRED','BLOCKED',affected)
            if not asset.has_video:
                issue('CMX_VIDEO_SOURCE_REQUIRED','BLOCKED',affected);continue
            inspected = probe_source_streams(asset,analyze_timing=True,check_cancel=check_cancel)
            timing = inspected['frame_timing']
            timecodes = [item.get('tags',{}).get('timecode') for item in inspected['streams']+[inspected['format']]]
            if any(value not in (None,'00:00:00:00') for value in timecodes):
                issue('CMX_NONZERO_OR_DROP_SOURCE_TIMECODE_UNSUPPORTED','BLOCKED',affected)
            measured = None
            if timing.get('cfr_verified') and timing.get('minimum_delta_ticks'):
                measured = 1/(Fraction(timing['time_base'])*timing['minimum_delta_ticks'])
            if measured != rate or abs(timing.get('first_timestamp_seconds',1)) > 1e-7:
                issue('CMX_FULL_CFR_ZERO_ORIGIN_REQUIRED','UNKNOWN',affected)
            audible = [c.clip_id for c in clips if c.media_asset_id==asset.asset_id and c.audio_role!='muted']
            if asset.audio_stream_count and audible:
                issue('CMX_VIDEO_ONLY_SOURCE_AUDIO_OMITTED','LOSS',audible)
        issue('CMX_OUTPUT_GEOMETRY_NOT_ENCODED','LOSS',[c.clip_id for c in clips])
    refs = [media_refs.get(a) for a in used if _ref(media_refs.get(a))]
    if len(set(refs)) != len(refs):
        issue('MEDIA_RELINK_COLLISION', 'BLOCKED')
    for track in timeline.tracks:
        identifiers = [track.track_id] + [c.clip_id for c in track.clips]
        if any(not isinstance(v,str) or len(v)>256 or any(ord(ch)<32 for ch in v) for v in identifiers):
            issue('EDITORIAL_IDENTIFIER_INVALID', 'BLOCKED')
        if any(not isinstance(c.purpose,str) or len(c.purpose)>4096 or any(ord(ch)<32 and ch not in '\n\t' for ch in c.purpose) for c in track.clips):
            issue('EDITORIAL_NOTE_INVALID', 'BLOCKED')
        end = Fraction(0)
        for clip in sorted(track.clips, key=lambda c: (c.timeline_start, c.clip_id)):
            if clip.frame_crop is not None:
                issue("EXPLICIT_FRAME_CROP_NOT_PORTABLE", "LOSS", [clip.clip_id])
            mix = clip.audio_mix
            for code, active in (('VOLUME_LOSS', format == 'otio' and mix.volume != 1), ('FADE_LOSS', bool(mix.fade_in_sec or mix.fade_out_sec)),
                                 ('DUCKING_LOSS', mix.ducking), ('MUTED_LOSS', format == 'otio' and clip.audio_role == 'muted')):
                if active:
                    issue(code, 'LOSS', [clip.clip_id])
            if rate:
                try:
                    start = _sec(clip.timeline_start, rate)
                    source_in = _sec(clip.source_in, rate)
                    source_out = _sec(clip.source_out, rate)
                    if format == 'cmx3600' and any((v*rate).denominator != 1 for v in (start,source_in,source_out)):
                        issue('CMX_OFF_FRAME_EDIT_UNSUPPORTED','BLOCKED',[clip.clip_id])
                    if source_out <= source_in:
                        issue('ZERO_FRAME_DURATION', 'BLOCKED', [clip.clip_id])
                    if start < end:
                        issue('TRACK_OVERLAP_UNSUPPORTED', 'BLOCKED', [clip.clip_id])
                    end = start + source_out - source_in
                except VideoEditingError:
                    issue('OFF_FRAME_EDIT_UNSUPPORTED', 'BLOCKED', [clip.clip_id])
    for trans in timeline.transitions:
        if trans.transition_type != 'cut':
            issue('DISSOLVE_OR_TRANSITION_LOSS', 'LOSS', [trans.from_clip, trans.to_clip])
    if timeline.overlays:
        issue('OVERLAY_CAPTION_LOSS', 'LOSS', [c.clip_id for c in clips])
    status = next((s for s in ('BLOCKED', 'UNKNOWN', 'LOSS') if any(i['severity'] == s for i in issues)), 'PASS')
    return {'schema': 'lumenis.interchange-preflight/v1', 'format': format, 'status': status,
            'issues': issues, 'frame_rate': str(rate) if rate else None,
            'source_frame_rates': {key:source_frame_rates[key] for key in sorted(used) if key in source_frame_rates},
            'timeline_version': timeline.version,
            'timeline_sha256': hashlib.sha256(json.dumps(timeline.to_dict(), sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            'compatibility': 'BOUNDED_FORMAT_ONLY_APPLICATION_IMPORT_NOT_VERIFIED',
            'source_rate_verification': ('FULL_SOURCE_PTS_CFR_ZERO_ORIGIN' if format=='cmx3600' and status not in ('BLOCKED','UNKNOWN') else 'FFPROBE_STREAM_METADATA_NOT_FULL_FILE_CFR_ASSERTION'),
            'external_import_frame_rate_required': format == 'cmx3600',
            'preserved': ['source_ranges', 'timeline_offsets', 'media_references', 'gaps', 'track_order']}


def _rt(seconds, rate):
    return {'OTIO_SCHEMA': 'RationalTime.1', 'value': float(seconds * rate), 'rate': float(rate)}


def _range(start, duration, rate):
    return {'OTIO_SCHEMA': 'TimeRange.1', 'start_time': _rt(start, rate), 'duration': _rt(duration, rate)}


def _otio(timeline, rate, media_refs):
    assets = {a.asset_id: a for a in timeline.assets}
    source_rates = _probe_rates(timeline)
    tracks = []
    for track in timeline.tracks:
        children = []
        end = Fraction(0)
        for clip in sorted(track.clips, key=lambda c: (c.timeline_start, c.clip_id)):
            source_rate = Fraction(source_rates.get(clip.media_asset_id, str(rate)))
            start = _sec(clip.timeline_start, rate)
            si, so = (_sec(v, source_rate) for v in (clip.source_in, clip.source_out))
            if start > end:
                children.append({'OTIO_SCHEMA': 'Gap.1', 'name': '', 'metadata': {}, 'effects': [], 'markers': [],
                                 'enabled': True, 'source_range': _range(Fraction(0), start - end, rate)})
            asset = assets[clip.media_asset_id]
            children.append({'OTIO_SCHEMA': 'Clip.2', 'name': clip.clip_id, 'metadata': {'lumenis_purpose': clip.purpose}, 'effects': [], 'markers': [], 'enabled': True,
                             'source_range': _range(si, so - si, source_rate),
                             'media_references': {'DEFAULT_MEDIA': {'OTIO_SCHEMA': 'ExternalReference.1', 'name': asset.asset_id,
                                 'metadata': {'lumenis_sha256': asset.sha256}, 'available_range': None,
                                 'target_url': media_refs[asset.asset_id], 'available_image_bounds': None}},
                             'active_media_reference_key': 'DEFAULT_MEDIA'})
            end = start + so - si
        tracks.append({'OTIO_SCHEMA': 'Track.1', 'name': track.track_id,
                       'metadata': {'lumenis_track_kind': track.kind}, 'source_range': None,
                       'effects': [], 'markers': [], 'enabled': True,
                       'kind': 'Video' if track.kind == 'video' else 'Audio', 'children': children})
    obj = {'OTIO_SCHEMA': 'Timeline.1', 'name': 'LUMENIS',
           'metadata': {'lumenis_frame_rate': str(rate), 'lumenis_format_ratio': timeline.format_ratio},
           'global_start_time': _rt(Fraction(0), rate),
           'tracks': {'OTIO_SCHEMA': 'Stack.1', 'name': 'tracks', 'metadata': {}, 'source_range': None,
                      'effects': [], 'markers': [], 'enabled': True, 'children': tracks}}
    return json.dumps(obj, ensure_ascii=False, indent=2).encode('utf-8')


def _time(value):
    return f'{value.numerator}/{value.denominator}s'


def _fcpxml(timeline, rate, media_refs):
    from .rendering import FRAME_SIZES
    root = ET.Element('fcpxml', version='1.10')
    resources = ET.SubElement(root, 'resources')
    width, height = FRAME_SIZES[timeline.format_ratio]
    ET.SubElement(resources, 'format', id='r0', name='LUMENIS', frameDuration=_time(1/rate), width=str(width), height=str(height))
    refs = {}; source_rates = _probe_rates(timeline)
    used = {c.media_asset_id for c in _clips(timeline)}
    for i, asset in enumerate(timeline.assets, 1):
        if asset.asset_id not in used: continue
        rid = f'r{i}'; refs[asset.asset_id] = rid
        attrs = dict(id=rid, name=asset.asset_id, start='0s', duration=_time(Fraction(str(asset.duration_sec))),
                     hasVideo='1' if asset.has_video else '0', hasAudio='1' if asset.audio_stream_count else '0')
        if asset.has_video:
            info = subprocess.run([_ffprobe_path(), '-v', 'error', '-protocol_whitelist', 'file',
                '-format_whitelist', MEDIA_INPUT_DEMUXERS, '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height', '-of', 'json', '-i', asset.path],
                capture_output=True, text=True, check=True, timeout=15)
            dims = json.loads(info.stdout)['streams'][0]
            source_format = f'f{i}'
            ET.SubElement(resources, 'format', id=source_format, frameDuration=_time(1/Fraction(source_rates[asset.asset_id])),
                          width=str(int(dims['width'])), height=str(int(dims['height'])))
            attrs['format'] = source_format
        node = ET.SubElement(resources, 'asset', **attrs)
        ET.SubElement(node, 'media-rep', kind='original-media', src=media_refs[asset.asset_id])
    event = ET.SubElement(root, 'event', name='LUMENIS')
    project = ET.SubElement(event, 'project', name='LUMENIS')
    duration = max(_sec(c.timeline_start, rate) + _sec(c.source_out, Fraction(source_rates.get(c.media_asset_id,str(rate))))
                   - _sec(c.source_in, Fraction(source_rates.get(c.media_asset_id,str(rate)))) for c in _clips(timeline))
    sequence = ET.SubElement(project, 'sequence', format='r0', duration=_time(duration), tcStart='0s', tcFormat='NDF')
    spine = ET.SubElement(sequence, 'spine')
    anchor = ET.SubElement(spine, 'gap', name='LUMENIS track anchor', offset='0s', start='0s', duration=_time(duration))
    track_map = []; video_lane = 0; audio_lane = 0
    for track in timeline.tracks:
        if track.kind == 'video': video_lane += 1; lane = video_lane
        else: audio_lane -= 1; lane = audio_lane
        track_map.append({'lane': lane, 'track_id': track.track_id, 'kind': track.kind})
        for clip in sorted(track.clips, key=lambda c:(c.timeline_start,c.clip_id)):
            source_rate = Fraction(source_rates.get(clip.media_asset_id,str(rate)))
            start = _sec(clip.timeline_start, rate)
            si, so = (_sec(v, source_rate) for v in (clip.source_in,clip.source_out))
            node = ET.SubElement(anchor, 'asset-clip', name=clip.clip_id, ref=refs[clip.media_asset_id],
                lane=str(lane), offset=_time(start), start=_time(si), duration=_time(so-si),
                srcEnable=('video' if clip.audio_role == 'muted' else 'all') if track.kind == 'video' else 'audio',
                audioRole=clip.audio_role)
            if clip.purpose:
                ET.SubElement(node,'note').text = clip.purpose
            if clip.audio_mix.volume != 1:
                amount = '-inf' if clip.audio_mix.volume == 0 else format(20*math.log10(clip.audio_mix.volume),'.15g')
                ET.SubElement(node,'adjust-volume',amount=amount+'dB')
    metadata = ET.SubElement(sequence,'metadata')
    ET.SubElement(metadata,'md',key='com.lumenis.track-identities',value=json.dumps(track_map,ensure_ascii=False))
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def _cmx3600(timeline, rate, media_refs):
    """CMX 3600 video cuts; import rate is explicit in the bound report."""
    def tc(seconds):
        frames = _sec(seconds,rate)*rate
        if frames.denominator != 1 or not 0 <= frames < 86400*rate:
            raise VideoEditingError('CMX_TIMECODE_OUT_OF_BOUNDS')
        seconds,frame = divmod(int(frames),int(rate))
        minutes,second = divmod(seconds,60);hour,minute=divmod(minutes,60)
        return f'{hour:02}:{minute:02}:{second:02}:{frame:02}'
    reels={a.asset_id:hashlib.sha256(a.asset_id.encode()).hexdigest()[:8].upper() for a in timeline.assets}
    if len(set(reels.values()))!=len(reels):raise VideoEditingError('CMX_REEL_COLLISION')
    lines=['TITLE: LUMENIS','FCM: NON-DROP FRAME','']
    for number,clip in enumerate(sorted(_clips(timeline),key=lambda c:c.timeline_start),1):
        end=_sec(clip.timeline_start,rate)+_sec(clip.source_out,rate)-_sec(clip.source_in,rate)
        lines += [f'{number:03}  {reels[clip.media_asset_id]} V     C        {tc(clip.source_in)} {tc(clip.source_out)} {tc(clip.timeline_start)} {tc(end)}',
                  '* FROM CLIP NAME: '+media_refs[clip.media_asset_id],
                  '* FROM FILE: '+media_refs[clip.media_asset_id],'']
    return ('\n'.join(lines)+'\n').encode('ascii')


def build_interchange_files(timeline: Timeline, *, formats=('otio', 'fcpxml'), frame_rate=None,
                            source_frame_rates=None, media_refs=None, allow_loss=False, check_cancel=None):
    if type(allow_loss) is not bool or not isinstance(formats, (list, tuple)) or not formats or len(formats) > 3 or any(not isinstance(f, str) for f in formats) or len(set(formats)) != len(formats):
        raise VideoEditingError('INTERCHANGE_OPTIONS_INVALID')
    if check_cancel:
        check_cancel()
    reports = [preflight_interchange(timeline, format=f, frame_rate=frame_rate,
                                    source_frame_rates=source_frame_rates, media_refs=media_refs, check_cancel=check_cancel) for f in formats]
    if any(r['status'] in ('BLOCKED', 'UNKNOWN') for r in reports):
        raise VideoEditingError('INTERCHANGE_PREFLIGHT_BLOCKED_OR_UNKNOWN')
    if not allow_loss and any(r['status'] == 'LOSS' for r in reports):
        raise VideoEditingError('INTERCHANGE_LOSS_REQUIRES_EXPLICIT_ACCEPTANCE')
    # Verify bytes again, not merely a saved MediaAsset label. Do not infer rights.
    for asset in timeline.assets:
        if check_cancel:
            check_cancel()
        current = fingerprint_local_media(asset.path)
        if current.sha256 != asset.sha256:
            raise VideoEditingError('INTERCHANGE_MEDIA_CHANGED')
    rate = _rate(frame_rate)
    exporters = {'otio':_otio,'fcpxml':_fcpxml,'cmx3600':_cmx3600}
    files = {('timeline.edl' if f=='cmx3600' else f'timeline.{f}'): exporters[f](timeline,rate,media_refs) for f in formats}
    report = {'schema': 'lumenis.interchange-package/v1', 'preflight': reports,
              'loss_accepted': allow_loss, 'source_sha256': {a.asset_id: a.sha256 for a in timeline.assets},
              'file_sha256': {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}}
    if check_cancel:
        check_cancel()
    files['interchange.json'] = json.dumps(report, ensure_ascii=False, indent=2).encode()
    return {'files': files, 'report': report}


def import_interchange(data: bytes, *, format: str, assets, media_refs: Mapping[str, str]) -> Timeline:
    """Read this adapter's strict editorial subset against explicit local assets.

    This is not a general professional-project importer. Unsupported objects,
    effects, external URLs and missing relinks fail; document media paths are
    never opened. Permission checks belong to the existing Artifact caller.
    """
    if not isinstance(data, bytes) or len(data) > 4_000_000:
        raise VideoEditingError('INTERCHANGE_DOCUMENT_INVALID')
    assets = tuple(assets)
    by_id = {a.asset_id: a for a in assets}
    by_ref = {media_refs.get(a.asset_id): a for a in assets if _ref(media_refs.get(a.asset_id))}
    if len(by_ref) != len(assets):
        raise VideoEditingError('INTERCHANGE_RELINK_REQUIRED')
    for asset in assets:
        if fingerprint_local_media(asset.path).sha256 != asset.sha256:
            raise VideoEditingError('INTERCHANGE_MEDIA_CHANGED')
    try:
        if format == 'otio':
            obj = json.loads(data)
            if obj['OTIO_SCHEMA'] != 'Timeline.1' or obj['tracks']['OTIO_SCHEMA'] != 'Stack.1':
                raise ValueError()
            rate = _rate(obj['metadata']['lumenis_frame_rate'])
            ratio = obj['metadata']['lumenis_format_ratio']
            if obj['tracks'].get('effects') or obj['tracks'].get('markers') or obj['tracks'].get('source_range'):
                raise ValueError()
            tracks = []
            def seconds(time):
                clock_rate = time['rate']
                if time['OTIO_SCHEMA'] != 'RationalTime.1' or type(clock_rate) not in (int,float) or not math.isfinite(clock_rate) or not 1 <= clock_rate <= 240:
                    raise ValueError()
                value = time['value']
                if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 240*86400:
                    raise ValueError()
                return (Fraction(str(value))/Fraction(str(clock_rate))).limit_denominator(1_000_000_000)
            for node in obj['tracks']['children']:
                if node['OTIO_SCHEMA'] != 'Track.1' or node.get('effects') or node.get('markers') or node.get('source_range') or node.get('enabled') is False:
                    raise ValueError()
                kind = node['metadata']['lumenis_track_kind']; tid = node['name']
                if node['kind'] != ('Video' if kind == 'video' else 'Audio'):
                    raise ValueError()
                cursor = Fraction(0); clips = []
                for child in node['children']:
                    if child.get('effects') or child.get('markers') or child.get('enabled') is False:
                        raise ValueError()
                    duration = seconds(child['source_range']['duration'])
                    if child['OTIO_SCHEMA'] == 'Gap.1':
                        cursor += duration; continue
                    if child['OTIO_SCHEMA'] != 'Clip.2':
                        raise ValueError()
                    ref = child['media_references'][child['active_media_reference_key']]
                    if ref['OTIO_SCHEMA'] != 'ExternalReference.1' or ref['target_url'] not in by_ref:
                        raise ValueError()
                    asset = by_ref[ref['target_url']]
                    if ref['name'] != asset.asset_id or ref['metadata']['lumenis_sha256'] != asset.sha256:
                        raise ValueError()
                    si = seconds(child['source_range']['start_time'])
                    clips.append(TimelineClip(child['name'], asset.asset_id, float(si), float(si+duration), float(cursor),
                                              track_id=tid, purpose=child.get('metadata',{}).get('lumenis_purpose',''), audio_role='original' if kind == 'video' else kind,
                                              audio_stream_index=None if kind == 'video' else 0))
                    cursor += duration
                tracks.append(TimelineTrack(tid, kind, tuple(clips)))
            if sum(len(t.clips) for t in tracks) > _MAX_CLIPS:
                raise ValueError()
            return Timeline(assets=assets, tracks=tuple(tracks), format_ratio=ratio)
        if format != 'fcpxml' or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
            raise ValueError()
        root = ET.fromstring(data)
        if root.tag != 'fcpxml' or root.get('version') != '1.10':
            raise ValueError()
        allowed = {'fcpxml', 'resources', 'format', 'asset', 'media-rep', 'event', 'project', 'sequence', 'spine', 'gap', 'asset-clip', 'metadata', 'md', 'adjust-volume', 'note'}
        if any(e.tag not in allowed for e in root.iter()):
            raise ValueError()
        def sec(value):
            if not re.fullmatch(r'[0-9]{1,16}(?:/[1-9][0-9]{0,9})?s', value):
                raise ValueError()
            return Fraction(value[:-1])
        resource_map = {}
        for item in root.findall('./resources/asset'):
            rep = item.find('media-rep')
            if rep is None or rep.get('src') not in by_ref or item.get('name') not in by_id:
                raise ValueError()
            asset = by_ref[rep.get('src')]
            if asset.asset_id != item.get('name'):
                raise ValueError()
            if item.get('id') in resource_map:
                raise ValueError()
            resource_map[item.get('id')] = asset
        formats = {i.get('id'): i for i in root.findall('./resources/format')}
        projects = root.findall('./event/project')
        if len(projects) != 1:
            raise ValueError()
        project = projects[0]; sequence = project.find('sequence'); spine = sequence.find('spine')
        fmt = formats[sequence.get('format')]
        ratio = str(Fraction(int(fmt.get('width')), int(fmt.get('height')))).replace('/', ':')
        if ratio == '1': ratio = '1:1'
        anchor = spine.find('gap')
        identities = sequence.find("./metadata/md[@key='com.lumenis.track-identities']")
        if anchor is None or len(spine) != 1 or identities is None:
            raise ValueError()
        track_map = json.loads(identities.get('value'))
        if not isinstance(track_map,list) or not 1 <= len(track_map) <= 32:
            raise ValueError()
        by_lane = {str(t['lane']):t for t in track_map}
        if len(by_lane) != len(track_map) or '0' in by_lane:
            raise ValueError()
        grouped = {lane:[] for lane in by_lane}
        for node in anchor:
            if node.tag != 'asset-clip' or node.get('lane') not in by_lane or node.get('enabled') not in (None, '1'):
                raise ValueError()
            if any(child.tag not in ('adjust-volume','note') for child in node) or len(node.findall('adjust-volume'))>1 or len(node.findall('note'))>1:
                raise ValueError()
            track = by_lane[node.get('lane')]
            asset = resource_map[node.get('ref')]
            si, duration, start = (sec(node.get(key)) for key in ('start', 'duration', 'offset'))
            volume = 1.0
            gain = node.find('adjust-volume')
            if gain is not None:
                amount = gain.get('amount')
                if not amount.endswith('dB') or len(gain): raise ValueError()
                db = float(amount[:-2])
                volume = 0.0 if db == -math.inf else round(10**(db/20), 14)
            kind = track['kind']
            muted = kind == 'video' and node.get('srcEnable') == 'video'
            role = ('muted' if muted else 'original') if kind == 'video' else kind
            if node.get('srcEnable') != ('video' if muted else 'all') and kind == 'video': raise ValueError()
            if kind != 'video' and node.get('srcEnable') != 'audio': raise ValueError()
            grouped[node.get('lane')].append(TimelineClip(node.get('name'), asset.asset_id,
                float(si), float(si+duration), float(start), track_id=track['track_id'],purpose=node.findtext('note',''),audio_role=role,
                audio_mix=AudioMix(volume=volume),audio_stream_index=None if kind=='video' else 0))
        if sum(len(c) for c in grouped.values()) > _MAX_CLIPS: raise ValueError()
        tracks = tuple(TimelineTrack(t['track_id'],t['kind'],tuple(grouped[str(t['lane'])])) for t in track_map)
        return Timeline(assets=assets,tracks=tracks,format_ratio=ratio)

    except (KeyError, TypeError, ValueError, AttributeError, OverflowError, RecursionError, ET.ParseError) as exc:
        raise VideoEditingError('INTERCHANGE_DOCUMENT_UNSUPPORTED_OR_INVALID') from exc
