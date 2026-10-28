"""Authorized media adaptation to the sole SYSTEM offline speech Gateway.

No model discovery/download, provider fallback, server-path input from clients,
Canonical promotion or transcript persistence occurs here. Optional Artifact
files and API callers retain the existing source/export/version authorization.
"""
import dataclasses,hashlib,json,math,os,re,shutil,tempfile,time,wave
from pathlib import Path
from fractions import Fraction
from lumenis.system.ai_gateway.owned_speech import CONTENT_LANGUAGE_CODES, model_weight_sha256
from .video_editing import VideoEditingError,fingerprint_local_media

CONFIG_ENV='LUMENIS_SPEECH_RUNTIME_CONFIG'


def configured_speech_runtime():
    from lumenis.system.ai_gateway.owned_speech import SpeechRuntime
    value=os.environ.get(CONFIG_ENV)
    if not value:raise VideoEditingError('CONTENT_ASR_RUNTIME_UNAVAILABLE')
    path=Path(value)
    if not path.is_absolute() or path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=16384:
        raise VideoEditingError('CONTENT_ASR_CONFIGURATION_INVALID')
    try:
        def pairs(items):
            result={}
            for key,value in items:
                if key in result:raise ValueError('duplicate')
                result[key]=value
            return result
        raw=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=pairs)
        if not isinstance(raw,dict) or set(raw) not in ({field.name for field in dataclasses.fields(SpeechRuntime)}, {field.name for field in dataclasses.fields(SpeechRuntime)}-{'model_id'}):raise ValueError('fields')
        for key,value in raw.items():
            if not isinstance(value,str) or not value:raise ValueError('value')
            if key.endswith('_sha256') and not re.fullmatch(r'[a-f0-9]{64}',value):raise ValueError('hash')
            if key.endswith('_path') and not Path(value).is_absolute():raise ValueError('path')
        model_weight_sha256(raw.get('model_id','openai/whisper-base'))
        return SpeechRuntime(**raw)
    except (ValueError,TypeError,OSError,UnicodeError,RuntimeError) as exc:raise VideoEditingError('CONTENT_ASR_CONFIGURATION_INVALID') from exc


def speech_runtime_status():
    from lumenis.system.ai_gateway.owned_speech import MODEL_ID,MODEL_REVISION,WEIGHT_SHA256
    model_id=MODEL_ID;weight_sha=WEIGHT_SHA256
    try:
        runtime=configured_speech_runtime();model_id=runtime.model_id;weight_sha=model_weight_sha256(model_id)
        missing=[key for key,value in dataclasses.asdict(runtime).items() if key.endswith('_path') and (not Path(value).is_file() or Path(value).is_symlink())]
        state='missing_local_files' if missing else 'configured_not_yet_inference_verified'
    except VideoEditingError as exc:state=str(exc);missing=[]
    return {'state':state,'missing_fields':missing,'model_id':model_id,'model_revision':MODEL_REVISION if model_id==MODEL_ID else weight_sha,
            'weight_sha256':weight_sha,'accepted_language_hints':sorted(CONTENT_LANGUAGE_CODES),'configuration_environment':CONFIG_ENV,'automatic_download':False,
            'inference_verified':False,'model_language_support_is_not_quality_acceptance':True,
            'owner':'SYSTEM AI Gateway owned_speech','human_listening_acceptance':False}


def _stamp(seconds,separator):
    ticks=max(0,round(seconds*1000));hours,ticks=divmod(ticks,3600000);minutes,ticks=divmod(ticks,60000);secs,ms=divmod(ticks,1000)
    return f'{hours:02}:{minutes:02}:{secs:02}{separator}{ms:03}'


_TRANSCRIPTION_SAMPLE_RATE = 16000
_TRANSCRIPTION_CHUNK_CORE_SECONDS = 590
_TRANSCRIPTION_CHUNK_OVERLAP_SECONDS = 2
_TRANSCRIPTION_MAX_CHUNKS = 256
_SOURCE_CLOCK_MAX_PACKETS = 5_000_000
_SOURCE_CLOCK_MAX_FRAMES = 5_000_000
_SOURCE_CLOCK_MAX_BYTES = 256 * 1024 * 1024
_SOURCE_CLOCK_MAX_DURATION_SECONDS = 24 * 60 * 60


def _source_transcription_clock(asset, audio_stream_index, *, check_cancel=None):
    """Observe container/stream origins, without confusing absolute PTS with source seconds.

    FFmpeg's default input timestamp adjustment (also used by the renderer)
    makes source seconds relative to the container presentation origin. Missing
    ffprobe start_time stays None: the extraction filter uses actual decoded PTS,
    not a guessed metadata offset. Video frame-rate declarations are irrelevant
    to this audio clock; no CFR or video-frame alignment claim is made.
    """
    from .rendering import _run
    from .video_editing import _ffprobe_path, MEDIA_INPUT_DEMUXERS
    probe = _ffprobe_path()
    if not probe:
        raise VideoEditingError('MEDIA_RENDER_TOOLS_UNAVAILABLE')
    with tempfile.TemporaryDirectory(prefix='lumenis-transcription-clock-') as temporary:
        root = Path(temporary); output = root / 'clock.json'
        _run([probe, '-v', 'error', '-protocol_whitelist', 'file', '-format_whitelist', MEDIA_INPUT_DEMUXERS,
              '-show_entries', 'format=start_time,duration,format_name:stream=index,codec_type,start_time,time_base,sample_rate',
              '-of', 'json', '-o', str(output), str(asset.path)], cwd=root, timeout=30,
             check_continue=check_cancel)
        if not output.is_file() or output.stat().st_size > 1024 * 1024:
            raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_UNVERIFIED')
        try:
            raw = json.loads(output.read_text(encoding='utf-8'))
            streams = raw['streams']
            if not isinstance(streams, list) or len(streams) > 256:
                raise ValueError('stream inventory')
            audio = [stream for stream in streams if stream.get('codec_type') == 'audio']
            if len(audio) != asset.audio_stream_count:
                raise ValueError('stream inventory changed')
            selected = audio[audio_stream_index]; container = raw.get('format', {})
            def observed(value):
                if value in (None, 'N/A'):
                    return None
                number = float(value)
                if not math.isfinite(number):
                    raise ValueError('nonfinite origin')
                return number
            origin = observed(container.get('start_time'))
            stream_start = observed(selected.get('start_time'))
            rate = int(selected['sample_rate'])
            if not 1 <= rate <= 768000 or type(selected['index']) is not int:
                raise ValueError('sample rate or stream index')
        except (ValueError, TypeError, KeyError, IndexError, UnicodeError) as exc:
            raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_UNVERIFIED') from exc
        # Stream decoded frame timestamps and sample counts. JSON materialized
        # every frame before it could be bounded and the former 100,000-frame
        # ceiling rejected ordinary long-form audio. Compact output is parsed
        # line by line; the packet limit proves the scan reached end-of-stream.
        frames_path = root / 'frames.compact'
        _run([probe, '-v', 'error', '-protocol_whitelist', 'file', '-format_whitelist', MEDIA_INPUT_DEMUXERS,
              '-select_streams', f'a:{audio_stream_index}',
              '-read_intervals', f'%+#{_SOURCE_CLOCK_MAX_PACKETS + 1}',
              '-show_frames', '-count_packets',
              '-show_entries', 'frame=best_effort_timestamp,nb_samples:stream=nb_read_packets',
              '-of', 'compact=p=0:nk=0', '-o', str(frames_path), str(asset.path)], cwd=root,
             timeout=min(3600, max(60, 120 + asset.duration_sec * .08)),
             check_continue=check_cancel)
        if not frames_path.is_file() or frames_path.stat().st_size > _SOURCE_CLOCK_MAX_BYTES:
            raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_SCAN_LIMIT')
        try:
            packet_count = None
            frame_count = 0
            tick = Fraction(selected['time_base'])
            if not 0 < tick <= Fraction(1, 100):
                raise ValueError('audio timestamp resolution unverified')
            tolerance = 2 * tick + Fraction(2, rate)
            previous_end = None; first_pts = None; cumulative_duration = Fraction(0)
            with frames_path.open('r', encoding='utf-8', newline='') as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    fields = {}
                    for field in line.rstrip('\r\n').split('|'):
                        key, separator, value = field.partition('=')
                        if not separator or key in fields:
                            raise ValueError('compact ffprobe record malformed')
                        fields[key] = value
                    if set(fields) == {'nb_read_packets'}:
                        if packet_count is not None:
                            raise ValueError('duplicate packet count')
                        packet_count = int(fields['nb_read_packets'])
                        continue
                    if set(fields) != {'best_effort_timestamp', 'nb_samples'}:
                        raise ValueError('decoded audio frame fields missing')
                    frame_count += 1
                    if frame_count > _SOURCE_CLOCK_MAX_FRAMES:
                        raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_SCAN_LIMIT')
                    if frame_count % 256 == 1 and check_cancel:
                        check_cancel()
                    pts = int(fields['best_effort_timestamp']) * tick
                    samples = int(fields['nb_samples'])
                    if not 0 < samples <= rate * 10:
                        raise ValueError('decoded audio frame size invalid')
                    if previous_end is not None and abs(pts - previous_end) > tolerance:
                        raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_DISCONTINUITY_UNSUPPORTED')
                    if first_pts is None:
                        first_pts = pts
                    if abs(pts - (first_pts + Fraction(cumulative_duration, rate))) > tolerance:
                        raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_DISCONTINUITY_UNSUPPORTED')
                    cumulative_duration += samples
                    previous_end = pts + Fraction(samples, rate)
            if (packet_count is None or not 0 < packet_count < _SOURCE_CLOCK_MAX_PACKETS
                    or not 0 < frame_count <= _SOURCE_CLOCK_MAX_FRAMES):
                raise ValueError('complete bounded decoded audio scan required')
            continuity = {'state': 'decoded_audio_pts_continuity_verified',
                          'audio_frames': frame_count, 'audio_packets': packet_count,
                          'first_decoded_pts_seconds': float(first_pts),
                          'last_decoded_end_seconds': float(previous_end),
                          'timestamp_rounding_tolerance_seconds': float(tolerance),
                          'method': 'streamed_bounded_ffprobe_decoded_frame_pts_and_sample_counts'}
        except VideoEditingError:
            raise
        except (ValueError, TypeError, KeyError, IndexError, ZeroDivisionError) as exc:
            raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_UNVERIFIED') from exc
    return {'schema': 'source-audio-clock:v2', 'basis': 'ffmpeg_input_presentation_relative_seconds',
            'source_sha256': asset.sha256, 'selected_audio_stream_index': audio_stream_index,
            'container_start_time_seconds': origin, 'stream_start_time_seconds': stream_start,
            'declared_relative_stream_start_seconds': (stream_start - origin
                                                      if origin is not None and stream_start is not None else None),
            'stream_index': selected['index'], 'stream_time_base': selected.get('time_base'),
            'source_sample_rate': rate, 'source_duration_seconds': asset.duration_sec,
            'missing_origin_policy': 'use_decoded_pts_same_as_renderer_not_metadata_zero_guess',
            'video_frame_alignment': 'not_claimed', 'continuity': continuity}


def _transcription_normalization_filter(duration):
    """Same source clock as rendering._audio_filter, before model-specific mono encoding."""
    from .rendering import _number
    frames = round(duration * _TRANSCRIPTION_SAMPLE_RATE)
    return (f'atrim=start=0:end={_number(duration)},asetpts=PTS,'
            f'aresample={_TRANSCRIPTION_SAMPLE_RATE}:first_pts=0,'
            f'apad=whole_len={frames},atrim=end_sample={frames},asetpts=N/SR/TB')


def _sha256_file(path, *, check_cancel=None):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        while block := handle.read(1024 * 1024):
            if check_cancel:
                check_cancel()
            digest.update(block)
    return digest.hexdigest()


def _source_clock_matches(stored, current):
    """Revalidate old frame-scan reports without invalidating their history."""
    if stored == current:
        return True
    if not isinstance(stored, dict) or not isinstance(current, dict):
        return False
    legacy = stored.get('continuity')
    if (stored.get('schema') != 'source-audio-clock:v1'
            or current.get('schema') != 'source-audio-clock:v2'
            or not isinstance(legacy, dict)
            or legacy.get('state') != 'decoded_audio_pts_continuity_verified'
            or legacy.get('method') != 'bounded_ffprobe_decoded_frame_pts_and_sample_counts'):
        return False
    identity_fields = ('basis', 'source_sha256', 'selected_audio_stream_index',
                       'container_start_time_seconds', 'stream_start_time_seconds',
                       'declared_relative_stream_start_seconds', 'stream_index',
                       'stream_time_base', 'source_sample_rate', 'source_duration_seconds',
                       'missing_origin_policy', 'video_frame_alignment')
    return all(stored.get(key) == current.get(key) for key in identity_fields)


def _transcribe_normalized_audio(normalized, *, frame_count, normalized_sha256, runtime,
                                 source_ref, language_hint, check_cancel):
    """Run the existing SYSTEM decoder on overlapping, bounded PCM windows."""
    from lumenis.system.ai_gateway import owned_speech

    rate = _TRANSCRIPTION_SAMPLE_RATE
    total_frames = frame_count
    core_frames = _TRANSCRIPTION_CHUNK_CORE_SECONDS * rate
    overlap_frames = _TRANSCRIPTION_CHUNK_OVERLAP_SECONDS * rate
    chunk_count = (total_frames + core_frames - 1) // core_frames
    if not 0 < chunk_count <= _TRANSCRIPTION_MAX_CHUNKS:
        raise VideoEditingError('CONTENT_ASR_AUDIO_UNSUPPORTED')

    def check():
        if check_cancel:
            check_cancel()

    windows = []
    units = []
    chunk_warnings = []
    language_codes = []
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='lumenis-asr-chunks-') as temporary:
        root = Path(temporary)
        with wave.open(str(normalized), 'rb') as source:
            for chunk_index in range(chunk_count):
                check()
                core_start = chunk_index * core_frames
                core_end = min(total_frames, core_start + core_frames)
                window_start = max(0, core_start - overlap_frames)
                window_end = min(total_frames, core_end + overlap_frames)
                window_frames = window_end - window_start
                chunk_path = root / f'chunk-{chunk_index:04d}.wav'
                source.setpos(window_start)
                with wave.open(str(chunk_path), 'wb') as chunk:
                    chunk.setnchannels(1)
                    chunk.setsampwidth(2)
                    chunk.setframerate(rate)
                    remaining = window_frames
                    while remaining:
                        check()
                        frames = source.readframes(min(remaining, rate * 30))
                        if not frames:
                            raise VideoEditingError('CONTENT_ASR_NORMALIZATION_UNVERIFIED')
                        chunk.writeframesraw(frames)
                        remaining -= len(frames) // 2
                    chunk.writeframes(b'')
                chunk_sha256 = _sha256_file(chunk_path)
                try:
                    decoded = owned_speech.transcribe_audio(
                        str(chunk_path), expected_audio_sha256=chunk_sha256,
                        runtime=runtime, source_ref=source_ref, is_cancelled=check,
                        timeout_seconds=1800, language_hint=language_hint)
                except owned_speech.SpeechBlocked as exc:
                    code = str(exc)
                    raise VideoEditingError(
                        code if re.fullmatch('[A-Z_0-9]{1,100}', code)
                        else 'CONTENT_ASR_FAILED') from exc
                check()
                if (not isinstance(decoded, dict)
                        or decoded.get('source_sha256') != chunk_sha256
                        or decoded.get('duration_seconds') != window_frames / rate
                        or decoded.get('owner') != 'SYSTEM AI Gateway'
                        or decoded.get('schema') != 'owned-speech-derivative:v1'
                        or decoded.get('source_ref') != source_ref
                        or decoded.get('source_ref_authenticated_by_adapter') is not False
                        or decoded.get('model_id') != runtime.model_id
                        or decoded.get('weight_sha256') != owned_speech.model_weight_sha256(runtime.model_id)
                        or decoded.get('runtime_manifest_sha256') != runtime.manifest_sha256
                        or decoded.get('ffmpeg_sha256') != runtime.ffmpeg_sha256
                        or not isinstance(decoded.get('model_revision'), str)
                        or not re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', decoded['model_revision'])
                        or not all(isinstance(decoded.get(key), str)
                                   and re.fullmatch(r'[a-f0-9]{64}', decoded[key])
                                   for key in ('weight_sha256', 'runtime_manifest_sha256',
                                               'adapter_sha256', 'ffmpeg_sha256'))
                        or decoded.get('fallback_allowed') is not False
                        or decoded.get('offline') is not True
                        or decoded.get('declared_language') != language_hint
                        or decoded.get('rights_state') != 'UNKNOWN'
                        or decoded.get('product_acceptance') is not False
                        or not isinstance(decoded.get('warnings'), list)):
                    raise VideoEditingError('CONTENT_ASR_CHUNK_RESULT_UNVERIFIED')
                transcript = decoded.get('transcript')
                try:
                    validated = owned_speech.validate_transcript(
                        transcript, duration_seconds=window_frames / rate)
                except owned_speech.SpeechBlocked as exc:
                    raise VideoEditingError('CONTENT_ASR_CHUNK_RESULT_UNVERIFIED') from exc
                if validated['transcript'] != transcript:
                    raise VideoEditingError('CONTENT_ASR_CHUNK_RESULT_UNVERIFIED')
                language = transcript['language']
                if language not in language_codes:
                    language_codes.append(language)
                core_start_seconds = core_start / rate
                core_end_seconds = core_end / rate
                window_start_seconds = window_start / rate
                window_end_seconds = window_end / rate
                windows.append({
                    'index': chunk_index,
                    'core_start_sample': core_start,
                    'core_end_sample': core_end,
                    'window_start_sample': window_start,
                    'window_end_sample': window_end,
                    'window_audio_sha256': chunk_sha256,
                    'decoder_model_id': decoded.get('model_id'),
                    'decoder_model_revision': decoded.get('model_revision'),
                    'decoder_weight_sha256': decoded.get('weight_sha256'),
                    'runtime_manifest_sha256': decoded.get('runtime_manifest_sha256'),
                    'decoder_adapter_sha256': decoded.get('adapter_sha256'),
                    'ffmpeg_sha256': decoded.get('ffmpeg_sha256'),
                    'language': language,
                    'decoder_warning_count': len(decoded.get('warnings', [])),
                })
                warning_counts = {}
                for warning in decoded.get('warnings', []):
                    if isinstance(warning, dict) and isinstance(warning.get('reason'), str):
                        reason = warning['reason']
                        warning_counts[reason] = warning_counts.get(reason, 0) + 1
                chunk_warnings.append({'chunk_index': chunk_index, 'counts_by_reason': warning_counts})

                selected_from_segment = {}
                for segment_index, segment in enumerate(transcript['segments']):
                    segment_start = window_start_seconds + segment['start']
                    segment_end = window_start_seconds + segment['end']
                    words = segment['words']
                    if not words:
                        midpoint = (segment_start + segment_end) / 2
                        in_core = core_start_seconds <= midpoint < core_end_seconds
                        if chunk_index == chunk_count - 1 and midpoint == core_end_seconds:
                            in_core = True
                        if in_core:
                            if (segment_start < window_start_seconds - 1 / rate
                                    or segment_end > window_end_seconds + 1 / rate):
                                raise VideoEditingError('CONTENT_ASR_CHUNK_BOUNDARY_UNSUPPORTED')
                            units.append({
                                'start': segment_start, 'end': segment_end,
                                'text': segment['text'], 'words': [],
                                'avg_logprob': segment['avg_logprob'],
                                'compression_ratio': segment['compression_ratio'],
                                'no_speech_prob': segment['no_speech_prob'],
                                'chunk_index': chunk_index, 'segment_index': segment_index,
                                'segment_only': True,
                            })
                        continue

                    segment_text = segment['text']
                    spans = []
                    cursor = 0
                    aligned = True
                    for word in words:
                        begin = segment_text.find(word['word'], cursor)
                        if begin < 0:
                            aligned = False
                            spans = []
                            break
                        finish = begin + len(word['word'])
                        spans.append((begin, finish))
                        cursor = finish
                    for word_index, word in enumerate(words):
                        absolute_start = window_start_seconds + word['start']
                        absolute_end = window_start_seconds + word['end']
                        midpoint = (absolute_start + absolute_end) / 2
                        if not core_start_seconds <= midpoint < core_end_seconds:
                            if chunk_index != chunk_count - 1 or midpoint != core_end_seconds:
                                continue
                        if (absolute_start < window_start_seconds - 1 / rate
                                or absolute_end > window_end_seconds + 1 / rate):
                            raise VideoEditingError('CONTENT_ASR_CHUNK_BOUNDARY_UNSUPPORTED')
                        selected_from_segment.setdefault(segment_index, []).append({
                            'start': absolute_start, 'end': absolute_end,
                            'text': word['word'], 'probability': word['probability'],
                            'chunk_index': chunk_index, 'segment_index': segment_index,
                            'word_index': word_index, 'segment_word_count': len(words),
                            'segment_text': segment_text, 'segment_text_aligned': aligned,
                            'segment_text_spans': spans,
                            'avg_logprob': segment['avg_logprob'],
                            'compression_ratio': segment['compression_ratio'],
                            'no_speech_prob': segment['no_speech_prob'],
                        })
                for entries in selected_from_segment.values():
                    units.extend(entries)

    # The same spoken word may be returned by both overlapping windows with
    # slightly different estimates. Merge only same-token candidates with
    # materially overlapping intervals; repeated words at distinct times stay.
    word_units = [unit for unit in units if not unit.get('segment_only')]
    segment_units = [unit for unit in units if unit.get('segment_only')]

    def token_key(value):
        return ''.join(character.casefold() for character in value if character.isalnum())

    def is_same_occurrence(left, right):
        if left['chunk_index'] == right['chunk_index'] or token_key(left['text']) != token_key(right['text']):
            return False
        if not token_key(left['text']):
            return False
        overlap = max(0.0, min(left['end'], right['end']) - max(left['start'], right['start']))
        shorter = min(left['end'] - left['start'], right['end'] - right['start'])
        if shorter <= 1 / rate:
            return abs((left['start'] + left['end']) / 2 - (right['start'] + right['end']) / 2) <= .12
        return overlap / shorter >= .6

    word_units.sort(key=lambda item: (item['start'], item['end'], item['chunk_index'], item['word_index']))
    unique_words = []
    duplicate_word_count = 0
    for candidate in word_units:
        duplicate_index = next((index for index, existing in enumerate(unique_words[-4:])
                                if is_same_occurrence(existing, candidate)), None)
        if duplicate_index is None:
            unique_words.append(candidate)
            continue
        absolute_index = len(unique_words) - min(4, len(unique_words)) + duplicate_index
        existing = unique_words[absolute_index]
        duplicate_word_count += 1
        if (candidate['probability'] > existing['probability']
                or (candidate['probability'] == existing['probability']
                    and candidate['chunk_index'] < existing['chunk_index'])):
            unique_words[absolute_index] = candidate

    segment_units.sort(key=lambda item: (item['start'], item['end'], item['chunk_index']))
    unique_segments = []
    duplicate_segment_count = 0
    for candidate in segment_units:
        duplicate = next((index for index, existing in enumerate(unique_segments[-4:])
                          if (existing['chunk_index'] != candidate['chunk_index']
                              and existing['text'].strip().casefold() == candidate['text'].strip().casefold()
                              and is_same_occurrence({**existing, 'text': existing['text']}, candidate))), None)
        if duplicate is None:
            unique_segments.append(candidate)
        else:
            absolute_index = len(unique_segments) - min(4, len(unique_segments)) + duplicate
            duplicate_segment_count += 1
            existing = unique_segments[absolute_index]
            if (candidate['no_speech_prob'] < existing['no_speech_prob']
                    or (candidate['no_speech_prob'] == existing['no_speech_prob']
                        and candidate['chunk_index'] < existing['chunk_index'])):
                unique_segments[absolute_index] = candidate

    by_segment = {}
    for candidate in unique_words:
        by_segment.setdefault((candidate['chunk_index'], candidate['segment_index']), []).append(candidate)
    units = []
    for key, entries in by_segment.items():
        entries.sort(key=lambda item: item['word_index'])
        first = entries[0]
        complete = (len(entries) == first['segment_word_count']
                    and [item['word_index'] for item in entries] == list(range(first['segment_word_count'])))
        if complete:
            text = first['segment_text']
        else:
            pieces = []
            for item in entries:
                if not item['segment_text_aligned']:
                    raise VideoEditingError('CONTENT_ASR_CHUNK_TEXT_ALIGNMENT_UNSUPPORTED')
                start, end = item['segment_text_spans'][item['word_index']]
                if item['word_index'] == 0:
                    start = 0
                if item['word_index'] == item['segment_word_count'] - 1:
                    end = len(item['segment_text'])
                pieces.append(item['segment_text'][start:end])
            text = ''.join(pieces)
        if not text:
            raise VideoEditingError('CONTENT_ASR_CHUNK_TEXT_ALIGNMENT_UNSUPPORTED')
        units.append({
            'start': min(item['start'] for item in entries),
            'end': max(item['end'] for item in entries),
            'text': text,
            'words': [{'word': item['text'], 'start': item['start'], 'end': item['end'],
                       'probability': item['probability']} for item in entries],
            'avg_logprob': min(item['avg_logprob'] for item in entries),
            'compression_ratio': max(item['compression_ratio'] for item in entries),
            'no_speech_prob': max(item['no_speech_prob'] for item in entries),
            'chunk_index': first['chunk_index'], 'segment_index': first['segment_index'],
            'segment_only': False,
        })
    units.extend(unique_segments)
    units.sort(key=lambda item: (item['start'], item['end'], item['chunk_index'], item['segment_index']))
    if len(units) > 1_000_000:
        raise VideoEditingError('CONTENT_ASR_TRANSCRIPT_SIZE_UNSUPPORTED')

    # Whisper's 4,096 segment limit applies to each inference window. Coalesce
    # those immutable word estimates into 30-second source blocks for a single
    # long-form transcript while retaining each word time and uncertainty.
    buckets = {}
    for unit in units:
        midpoint = (unit['start'] + unit['end']) / 2
        bucket = int(midpoint // 30)
        buckets.setdefault(bucket, []).append(unit)
    segments = []
    for bucket in sorted(buckets):
        group = buckets[bucket]
        group.sort(key=lambda item: (item['start'], item['end'], item['chunk_index'], item['segment_index']))
        segment = {
            'id': len(segments),
            'start': group[0]['start'],
            'end': max(item['end'] for item in group),
            'text': ''.join(item['text'] for item in group),
            'avg_logprob': min(item['avg_logprob'] for item in group),
            'compression_ratio': max(item['compression_ratio'] for item in group),
            'no_speech_prob': max(item['no_speech_prob'] for item in group),
            'words': [word for item in group for word in item['words']],
        }
        if not segment['text']:
            continue
        segments.append(segment)
    if len(segments) > 4096:
        raise VideoEditingError('CONTENT_ASR_TRANSCRIPT_SIZE_UNSUPPORTED')
    language = language_codes[0] if len(language_codes) == 1 else 'mul' if language_codes else 'und'
    transcript = {'text': ''.join(segment['text'] for segment in segments),
                  'language': language, 'segments': segments}
    try:
        validated = owned_speech.validate_transcript(
            transcript, duration_seconds=total_frames / rate)
    except owned_speech.SpeechBlocked as exc:
        raise VideoEditingError('CONTENT_ASR_CHUNK_ASSEMBLY_UNVERIFIED') from exc

    # All inference windows must retain the same admitted runtime and model pins.
    pin_keys = ('decoder_model_id', 'decoder_model_revision', 'decoder_weight_sha256',
                'runtime_manifest_sha256', 'decoder_adapter_sha256', 'ffmpeg_sha256')
    if any(any(window.get(key) != windows[0].get(key) for key in pin_keys) for window in windows[1:]):
        raise VideoEditingError('CONTENT_ASR_CHUNK_RUNTIME_CHANGED')
    first = windows[0]
    result = {
        'schema': 'owned-speech-derivative:v1', 'owner': 'SYSTEM AI Gateway',
        **validated, 'source_ref': source_ref, 'source_ref_authenticated_by_adapter': False,
        'source_sha256': normalized_sha256, 'duration_seconds': total_frames / rate,
        'model_id': first['decoder_model_id'], 'model_revision': first['decoder_model_revision'],
        'weight_sha256': first['decoder_weight_sha256'],
        'evaluation_candidate': first['decoder_model_id'] != owned_speech.MODEL_ID,
        'runtime_manifest_sha256': first['runtime_manifest_sha256'],
        'adapter_sha256': first['decoder_adapter_sha256'], 'ffmpeg_sha256': first['ffmpeg_sha256'],
        'elapsed_seconds': time.monotonic() - started, 'offline': True, 'fallback_allowed': False,
        'script_or_target_supplied': False, 'declared_language': language_hint,
        'language_selection': 'user_declared' if language_hint else 'automatic',
        'rights_state': 'UNKNOWN', 'human_listening_acceptance': False,
        'promotion_status': 'NOT_PROMOTED', 'product_acceptance': False,
        'chunking': {
            'schema': 'source-asr-chunking:v1', 'state': 'complete_source_windows_processed',
            'method': 'overlapped_pcm_windows_midpoint_owned_word_merge',
            'source_sample_rate': rate, 'source_frame_count': total_frames,
            'chunk_core_seconds': _TRANSCRIPTION_CHUNK_CORE_SECONDS,
            'overlap_seconds_each_side': _TRANSCRIPTION_CHUNK_OVERLAP_SECONDS,
            'boundary_assignment': 'word_midpoint_to_one_nonoverlapping_source_core',
            'duplicate_resolution': 'same_token_material_interval_overlap_keep_higher_decoder_probability',
            'duplicate_words_removed': duplicate_word_count,
            'duplicate_segments_removed': duplicate_segment_count,
            'segment_aggregation': '30_second_source_blocks_conservative_decoder_metrics_word_times_retained',
            'recognized_chunk_languages': language_codes,
            'source_warning_counts': chunk_warnings,
            'normalized_source_sha256': normalized_sha256,
            'windows': windows,
        },
    }
    return result


def build_transcription_files(asset,*,audio_stream_index=None,language_hint=None,check_cancel=None):
    from shared_artifacts import validate_local_asset,_ffmpeg_path
    from .rendering import _run
    from lumenis.system.ai_gateway import owned_speech
    if language_hint is not None and (not isinstance(language_hint,str) or language_hint not in CONTENT_LANGUAGE_CODES):raise VideoEditingError('CONTENT_ASR_LANGUAGE_INVALID')
    runtime=configured_speech_runtime();asset.validate();path=validate_local_asset(asset.path)
    if not asset.audio_stream_count or asset.duration_sec>_SOURCE_CLOCK_MAX_DURATION_SECONDS:raise VideoEditingError('CONTENT_ASR_AUDIO_UNSUPPORTED')
    if audio_stream_index is None:
        if asset.audio_stream_count!=1:raise VideoEditingError('AUDIO_STREAM_SELECTION_REQUIRED')
        audio_stream_index=0
    if type(audio_stream_index) is not int or not 0<=audio_stream_index<asset.audio_stream_count:raise VideoEditingError('AUDIO_STREAM_INDEX_OUT_OF_RANGE')
    def check():
        if check_cancel:check_cancel()
    def verify():
        check()
        if fingerprint_local_media(str(path)).sha256!=asset.sha256:raise VideoEditingError('SOURCE_MEDIA_CHANGED')
    verify();ffmpeg=_ffmpeg_path()
    if not ffmpeg:raise VideoEditingError('MEDIA_RENDER_TOOLS_UNAVAILABLE')
    source_clock = _source_transcription_clock(asset, audio_stream_index, check_cancel=check_cancel)
    with tempfile.TemporaryDirectory(prefix='lumenis-source-transcription-') as temporary:
        work=Path(temporary);normalized=work/'source.wav'
        expected_bytes = round(asset.duration_sec * _TRANSCRIPTION_SAMPLE_RATE) * 2 + 128
        if shutil.disk_usage(work).free < expected_bytes + 64 * 1024 * 1024:
            raise VideoEditingError('CONTENT_ASR_TEMP_STORAGE_UNAVAILABLE')
        from .video_editing import MEDIA_INPUT_DEMUXERS
        _run([ffmpeg,'-v','error','-nostdin','-n','-protocol_whitelist','file','-format_whitelist',MEDIA_INPUT_DEMUXERS,
              '-i',str(path),'-map',f'0:a:{audio_stream_index}','-vn','-sn','-dn','-map_metadata','-1',
              '-af',_transcription_normalization_filter(asset.duration_sec),
              '-ar','16000','-ac','1','-c:a','pcm_s16le',str(normalized)],cwd=work,
             timeout=min(7200,max(180,120+asset.duration_sec*.25)),check_continue=check_cancel)
        try:
            with wave.open(str(normalized), 'rb') as audio:
                frames = audio.getnframes()
                if (audio.getframerate() != _TRANSCRIPTION_SAMPLE_RATE or audio.getnchannels() != 1
                        or audio.getsampwidth() != 2 or frames != round(asset.duration_sec * _TRANSCRIPTION_SAMPLE_RATE)):
                    raise ValueError('normalized audio clock mismatch')
        except (OSError, ValueError, wave.Error) as exc:
            raise VideoEditingError('CONTENT_ASR_NORMALIZATION_UNVERIFIED') from exc
        normalized_hash = _sha256_file(normalized,check_cancel=check_cancel)
        normalization = {'schema': 'source-audio-normalization:v1', 'sha256': normalized_hash,
                         'sample_rate': _TRANSCRIPTION_SAMPLE_RATE, 'frame_count': frames,
                         'duration_seconds': frames / _TRANSCRIPTION_SAMPLE_RATE,
                         'source_clock': source_clock,
                         'filter': _transcription_normalization_filter(asset.duration_sec),
                         'mapping': 'identity_after_pts_aligned_padding_and_negative_time_trim',
                         'timestamp_quantization_seconds': 1 / _TRANSCRIPTION_SAMPLE_RATE}
        result=_transcribe_normalized_audio(normalized,frame_count=frames,normalized_sha256=normalized_hash,
            runtime=runtime,source_ref=asset.asset_id,language_hint=language_hint,check_cancel=check_cancel)
    verify()
    if _source_transcription_clock(asset, audio_stream_index, check_cancel=check_cancel) != source_clock:
        raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_CHANGED')
    if result.get('source_sha256') != normalized_hash:
        raise VideoEditingError('CONTENT_ASR_NORMALIZATION_UNVERIFIED')
    transcript=result['transcript'];segments=transcript['segments']
    owned_speech.validate_transcript(transcript, duration_seconds=frames / _TRANSCRIPTION_SAMPLE_RATE)
    report={**result,'original_source_sha256':asset.sha256,'source_asset_id':asset.asset_id,'selected_audio_stream_index':audio_stream_index,
            'transcript_time_basis':'original_source_seconds','subtitle_alignment_scope':'original_source_not_edited_timeline',
            'source_clock_definition':'container_presentation_relative_not_absolute_stream_pts',
            'audio_normalization':normalization,
            'source_annotation':'model_estimated_unreviewed_derivative','original_audio_modified':False,
            'model_ownership':'third_party_pretrained','model_provider':'OpenAI Whisper','model_license':'MIT',
            'runtime_dependencies':{'torch':'third_party_cpu_runtime','ffmpeg':'third_party_deterministic_media_tool'},
            'product_integration_owner':'SYSTEM AI Gateway; model ownership is not claimed',
            'speaker_diarization':'not_performed','source_permission_checked_by_caller':True}
    vtt='WEBVTT\n\n';srt=''
    for i,segment in enumerate(segments,1):
        # Subtitle markup from a recognizer is literal text, not styling or HTML.
        text=segment['text'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        vtt+=f"{i}\n{_stamp(segment['start'],'.')} --> {_stamp(segment['end'],'.')}\n{text}\n\n"
        srt+=f"{i}\n{_stamp(segment['start'],',')} --> {_stamp(segment['end'],',')}\n{text}\n\n"
    words={'source_sha256':asset.sha256,'timestamp_method':result['timestamp_method'],'review_state':result['review_state'],
           'segments':[{key:segment[key] for key in ('id','start','end','text','words')} for segment in segments]}
    recognized=bool(segments) and result['review_state']!='NO_RECOGNIZED_SPEECH'
    report['subtitle_export']={'state':'available' if recognized else 'no_recognized_speech',
                               'files':['transcript-asr.vtt','transcript-asr.srt'] if recognized else []}
    files={'transcription.json':json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2).encode(),
           'transcript-words.json':json.dumps(words,ensure_ascii=False,allow_nan=False,indent=2).encode()}
    if recognized:files.update({'transcript-asr.vtt':vtt.encode(),'transcript-asr.srt':srt.encode()})
    return {'files':files,'report':report}


def build_timeline_transcription_files(timeline, source_item, *, rendered_sha256, check_cancel=None):
    """Derive selected-source subtitles using the renderer's audio clock.

    This is not mixed-output recognition or human-verified alignment. Originals
    remain untouched. Unsupported timing semantics fail rather than guess.
    """
    from .video_editing import TimelineClip
    from .rendering import SAMPLE_RATE, _number
    from .transcript_editing import validate_manual_transcript
    from fractions import Fraction
    from lumenis.system.ai_gateway.owned_speech import validate_transcript
    def check():
        if check_cancel: check_cancel()
    def fail(code):
        raise VideoEditingError('CONTENT_ASR_TIMELINE_'+code)
    def encoded(value):
        return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
    check();timeline.validate()
    if rendered_sha256 is not None and (not isinstance(rendered_sha256,str) or not re.fullmatch('[a-f0-9]{64}',rendered_sha256)):fail('OUTPUT_HASH_INVALID')
    report=source_item['report'];original=source_item['files']['transcription.json']
    if json.loads(original)!=report:fail('SOURCE_REPORT_MISMATCH')
    asset=next((a for a in timeline.assets if a.asset_id==report.get('source_asset_id')),None)
    if asset is None or asset.sha256!=report.get('original_source_sha256'):fail('SOURCE_MISMATCH')
    if fingerprint_local_media(asset.path).sha256!=asset.sha256:fail('SOURCE_CHANGED')
    transcript=report['transcript']
    manual=(report.get('owner')=='Shared Content Creation'
            and report.get('source_annotation')=='human_authored_transcript_not_independently_verified')
    if manual:
        validate_manual_transcript(report,duration=asset.duration_sec)
    else:
        validate_transcript(transcript,duration_seconds=asset.duration_sec)
    selected_stream=report.get('selected_audio_stream_index')
    if type(selected_stream) is not int or not 0<=selected_stream<asset.audio_stream_count:fail('STREAM_INVALID')
    normalization = report.get('audio_normalization')
    current_clock = _source_transcription_clock(asset, selected_stream, check_cancel=check_cancel)
    if manual:
        if not _source_clock_matches(report.get('source_audio_clock'), current_clock):
            fail('SOURCE_CLOCK_MISMATCH')
    elif normalization is None:
        # Historical WAV reports used a sample-zero source. Old arbitrary
        # container reports never proved this identity and must be regenerated.
        if Path(asset.path).suffix.lower() != '.wav':
            fail('SOURCE_CLOCK_UNVERIFIED')
    else:
        if (not isinstance(normalization, dict)
                or normalization.get('schema') != 'source-audio-normalization:v1'
                or not _source_clock_matches(normalization.get('source_clock'), current_clock)
                or normalization.get('filter') != _transcription_normalization_filter(asset.duration_sec)
                or normalization.get('mapping') != 'identity_after_pts_aligned_padding_and_negative_time_trim'
                or normalization.get('sample_rate') != _TRANSCRIPTION_SAMPLE_RATE
                or normalization.get('frame_count') != round(asset.duration_sec * _TRANSCRIPTION_SAMPLE_RATE)
                or normalization.get('duration_seconds') != round(asset.duration_sec * _TRANSCRIPTION_SAMPLE_RATE) / _TRANSCRIPTION_SAMPLE_RATE
                or not isinstance(normalization.get('sha256'), str)
                or not re.fullmatch('[a-f0-9]{64}', normalization['sha256'])
                or report.get('source_sha256', normalization['sha256']) != normalization['sha256']):
            fail('SOURCE_CLOCK_MISMATCH')
    if report.get('transcript_time_basis') != 'original_source_seconds':fail('SOURCE_CLOCK_UNVERIFIED')
    reviewed=report.get('text_review',{}).get('segments')
    if reviewed is not None:
        if (type(reviewed) is not list or len(reviewed)!=len(transcript['segments'])
                or any(type(current) is not dict or current.get('id')!=original.get('id')
                       or type(current.get('text')) is not str or not current['text'].strip()
                       or {key:value for key,value in current.items() if key not in {'text','speaker_id'}}
                          !={key:value for key,value in original.items() if key not in {'text','speaker_id'}}
                       for original,current in zip(transcript['segments'],reviewed))):
            fail('TEXT_REVIEW_MISMATCH')
    reviewed_by_id={segment['id']:segment for segment in reviewed or []}
    clips=[]
    for track in timeline.audible_tracks():
        for clip in track.clips:
            check()
            if type(clip) is not TimelineClip or set(vars(clip))!={f.name for f in dataclasses.fields(TimelineClip)}:fail('RATE_UNSUPPORTED')
            if clip.media_asset_id!=asset.asset_id or clip.audio_role=='muted' or clip.audio_mix.volume==0:continue
            stream=clip.audio_stream_index
            if stream is None and asset.audio_stream_count==1:stream=0
            if stream!=selected_stream:continue
            start=round(clip.timeline_start*SAMPLE_RATE)/SAMPLE_RATE
            end=start+round(clip.duration_sec*SAMPLE_RATE)/SAMPLE_RATE
            clips.append((start,end,clip,track.track_id))
    clips.sort(key=lambda entry:(entry[0],entry[2].clip_id))
    words=[];cues=[];warnings=[]
    for start,end,clip,track_id in clips:
        source_in=float(_number(clip.source_in));source_out=float(_number(clip.source_out))
        rate=Fraction(str(clip.playback_rate));origin=Fraction(round(clip.timeline_start*SAMPLE_RATE),SAMPLE_RATE)
        def mapped(point):
            return origin+(Fraction(str(point))-Fraction(str(source_in)))/rate
        def timed(start_time,end_time):
            return {'start':float(start_time),'end':float(end_time),
                'start_exact':{'numerator':start_time.numerator,'denominator':start_time.denominator},
                'end_exact':{'numerator':end_time.numerator,'denominator':end_time.denominator}}
        for segment in transcript['segments']:
            edited=reviewed_by_id.get(segment['id'],segment)
            full_segment=(source_in<=segment['start']<segment['end']<=source_out
                and all(source_in<=word['start']<=word['end']<=source_out for word in segment['words']))
            retained=[]
            for index,word in enumerate(segment['words']):
                check();a=word['start'];b=word['end'];word_id=f"{segment['id']}:{index}"
                if b<=source_in or a>=source_out:continue
                if a<source_in or b>source_out or b<=a:
                    warnings.append({'reason':'cut_or_zero_length_word_omitted','clip_id':clip.clip_id,'source_word_id':word_id});continue
                out_a=mapped(a);out_b=mapped(b)
                if float(out_b)>end or round(float(out_b)*1000)<=round(float(out_a)*1000):
                    warnings.append({'reason':'outside_rendered_or_submillisecond_word_omitted','clip_id':clip.clip_id,'source_word_id':word_id});continue
                value={'source_word_id':word_id,'source_segment_id':segment['id'],'clip_id':clip.clip_id,
                    'track_id':track_id,'text':word['word'],'source_start':a,'source_end':b,
                    'speaker_id':segment.get('speaker_id',segment.get('speaker')),
                    'language':transcript['language'],'text_state':'ORIGINAL_TIMED_WORD_NOT_REALIGNED',**timed(out_a,out_b)}
                retained.append(value);words.append(value)
            if full_segment:
                out_a,out_b=mapped(segment['start']),mapped(segment['end'])
                if float(out_b)<=end and round(float(out_b)*1000)>round(float(out_a)*1000):
                    cues.append({'clip_id':clip.clip_id,'track_id':track_id,'source_segment_id':segment['id'],
                        'source_start':segment['start'],'source_end':segment['end'],
                        'speaker_id':edited.get('speaker_id',edited.get('speaker')),'text':edited['text'],
                        'text_state':'HUMAN_REVIEWED_SEGMENT_ORIGINAL_INTERVAL' if edited is not segment else 'ORIGINAL_SEGMENT',
                        **timed(out_a,out_b)})
                    continue
            cues.extend({**word,'text_state':'ORIGINAL_WORD_AFTER_CUT_REVIEW_REQUIRED'} for word in retained)
            if retained and edited['text']!=segment['text']:
                warnings.append({'reason':'corrected_segment_crosses_cut_requires_text_realignment',
                    'clip_id':clip.clip_id,'source_segment_id':segment['id'],'reviewed_text':edited['text'],
                    'original_word_times_unchanged':True})
            if (not full_segment and not segment['words']
                    and segment['start']<source_out and segment['end']>source_in):
                warnings.append({'reason':'partial_segment_has_no_word_timing_requires_manual_alignment',
                    'clip_id':clip.clip_id,'source_segment_id':segment['id']})
    cues.sort(key=lambda item:(item['start'],item['end'],item['clip_id'],item['source_segment_id']))
    overlaps=any(right['start']<left['end'] for left,right in zip(cues,cues[1:]))
    if overlaps:warnings.append({'reason':'overlapping_source_cues_retained_requires_listening_review'})
    vtt='WEBVTT\n\n';srt=''
    for index,cue in enumerate(cues,1):
        text=cue['text'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        vtt+=f"{index}\n{_stamp(cue['start'],'.')} --> {_stamp(cue['end'],'.')}\n{text}\n\n"
        srt+=f"{index}\n{_stamp(cue['start'],',')} --> {_stamp(cue['end'],',')}\n{text}\n\n"
    derived={'schema':'timeline-transcription:v1','state':'available' if cues else 'no_retained_words',
             'time_basis':'rendered_output_seconds','mapping':'source_words_playback_rate_sample_quantized_clip_delay',
             'source_asset_id':asset.asset_id,'source_sha256':asset.sha256,'selected_audio_stream_index':selected_stream,
             'source_transcription_sha256':hashlib.sha256(original).hexdigest(),
             'source_audio_normalization':normalization,'source_audio_clock':report.get('source_audio_clock'),
             'source_clock_definition':'container_presentation_relative_not_absolute_stream_pts',
             'timeline_sha256':hashlib.sha256(encoded(timeline.to_dict())).hexdigest(),'timeline_version':timeline.version,
             'rendered_sha256':rendered_sha256,'coverage':'selected_source_and_audio_stream_only',
             'complete_mix_transcription':False,'review_state':'UNREVIEWED','human_alignment':'NOT_VERIFIED',
             'requires_user_review':True,'words':words,'cues':cues,'overlapping_cues':overlaps,'warnings':warnings,
             'source_annotation':report.get('source_annotation'),'owned_model_execution':'NOT_RUN' if manual else 'SOURCE_REPORT_ONLY_NO_NEW_INFERENCE',
             'render_binding':'CURRENT_RENDER' if rendered_sha256 is not None else 'PROJECT_DRAFT_NOT_RENDERED'}
    files={'transcript-timeline.json':encoded(derived)}
    if cues:files.update({'transcript-timeline.srt':srt.encode(),'transcript-timeline.vtt':vtt.encode()})
    check()
    return {'files':files,'report':derived}


def build_project_transcription_files(timeline, source_files, *, rendered_sha256=None,
                                      source_artifact_refs=None, check_cancel=None):
    """Project saved source annotations onto this exact editable revision.

    This does not recognize the final mix. Human annotations take precedence
    over an ASR alternative for the same source/stream; both originals survive.
    """
    def check():
        if check_cancel:check_cancel()
    check();timeline.validate()
    assets={asset.asset_id:asset for asset in timeline.assets}
    candidates={};unavailable=[]
    for member,raw in source_files.items():
        check()
        if member!='transcription.json' and not re.fullmatch(r'transcription-MEDIA-[a-f0-9]{16}\.json',member):
            continue
        report=json.loads(raw)
        if not isinstance(report,dict):raise VideoEditingError('CONTENT_ASR_TIMELINE_SOURCE_REPORT_MISMATCH')
        asset=assets.get(report.get('source_asset_id'))
        if asset is None:
            if member=='transcription.json' and report.get('source_asset_id') is None:
                unavailable.append({'member':member,'sha256':hashlib.sha256(raw).hexdigest(),
                    'state':'UNAVAILABLE','reason':'HISTORICAL_SOURCE_IDENTITY_UNVERIFIED'})
                continue
            raise VideoEditingError('CONTENT_ASR_TIMELINE_SOURCE_MISMATCH')
        if (asset.sha256!=report.get('original_source_sha256')
                or member!='transcription.json' and member!='transcription-'+asset.asset_id+'.json'):
            raise VideoEditingError('CONTENT_ASR_TIMELINE_SOURCE_MISMATCH')
        stream=report.get('selected_audio_stream_index')
        if type(stream) is not int or not 0<=stream<asset.audio_stream_count:
            raise VideoEditingError('CONTENT_ASR_TIMELINE_STREAM_INVALID')
        manual=report.get('source_annotation')=='human_authored_transcript_not_independently_verified'
        if not manual and report.get('source_annotation')!='model_estimated_unreviewed_derivative':
            raise VideoEditingError('WORD_EDIT_TRANSCRIPT_PROVENANCE_INVALID')
        key=(asset.asset_id,stream)
        previous=candidates.get(key)
        if previous is None or manual:
            candidates[key]=(member,raw,report,manual)
    if not candidates and not unavailable:
        return {'files':{},'report':None}
    words=[];cues=[];warnings=[];sources=[]
    for (asset_id,stream),(member,original,report,manual) in sorted(candidates.items()):
        check();raw=original
        reviewed_member='transcription-reviewed-'+asset_id+'.json'
        if reviewed_member in source_files:
            reviewed=json.loads(source_files[reviewed_member])
            if (not isinstance(reviewed,dict) or reviewed.get('source_asset_id')!=asset_id
                    or reviewed.get('original_source_sha256')!=assets[asset_id].sha256):
                raise VideoEditingError('CONTENT_ASR_TIMELINE_TEXT_REVIEW_MISMATCH')
            if reviewed.get('selected_audio_stream_index')==stream:
                if ({key:value for key,value in reviewed.items() if key!='text_review'}
                        !={key:value for key,value in report.items() if key!='text_review'}):
                    raise VideoEditingError('CONTENT_ASR_TIMELINE_TEXT_REVIEW_MISMATCH')
                report=reviewed;raw=source_files[reviewed_member];member=reviewed_member
        source={'source_asset_id':asset_id,'source_sha256':assets[asset_id].sha256,
            'selected_audio_stream_index':stream,'member':member,
            'source_transcription_sha256':hashlib.sha256(raw).hexdigest(),
            'original_transcription_sha256':hashlib.sha256(original).hexdigest(),
            'source_artifact_ref':(source_artifact_refs or {}).get(asset_id),
            'source_annotation':report.get('source_annotation'),'state':'AVAILABLE',
            'new_model_execution':'NOT_RUN'}
        try:
            mapped=build_timeline_transcription_files(timeline,{'report':report,'files':{'transcription.json':raw}},
                rendered_sha256=rendered_sha256,check_cancel=check_cancel)['report']
        except VideoEditingError as exc:
            if str(exc)!='CONTENT_ASR_TIMELINE_SOURCE_CLOCK_UNVERIFIED':raise
            source.update(state='UNAVAILABLE',reason=str(exc))
            sources.append(source);continue
        sources.append(source)
        binding={key:source[key] for key in ('source_asset_id','source_sha256','selected_audio_stream_index',
            'source_artifact_ref','member','source_transcription_sha256')}
        for key,target in (('words',words),('cues',cues),('warnings',warnings)):
            for value in mapped.get(key,[]):
                target.append({**value,**binding})
        check()
    words.sort(key=lambda item:(item['start'],item['end'],item['source_asset_id'],item['clip_id'],item['source_word_id']))
    cues.sort(key=lambda item:(item['start'],item['end'],item['source_asset_id'],item['clip_id'],item['source_segment_id']))
    overlaps=any(right['start']<left['end'] for left,right in zip(cues,cues[1:]))
    if overlaps:warnings.append({'reason':'overlapping_sources_preserved_no_speaker_identity_inference'})
    covered={(item['source_asset_id'],item['selected_audio_stream_index']) for item in sources if item['state']=='AVAILABLE'}
    missing=[]
    for track in timeline.audible_tracks():
        for clip in track.clips:
            asset=assets[clip.media_asset_id]
            if clip.audio_role=='muted' or clip.audio_mix.volume==0 or not asset.audio_stream_count:continue
            stream=clip.audio_stream_index if clip.audio_stream_index is not None else 0
            if (asset.asset_id,stream) not in covered:
                missing.append({'source_asset_id':asset.asset_id,'clip_id':clip.clip_id,'track_id':track.track_id,
                    'selected_audio_stream_index':stream,'reason':'SOURCE_TRANSCRIPT_NOT_AVAILABLE'})
    encoded=lambda value:json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
    result={'schema':'timeline-transcription:v2','state':'available' if cues else 'no_retained_cues',
        'time_basis':'rendered_output_seconds' if rendered_sha256 is not None else 'project_timeline_seconds_not_rendered',
        'timeline_sha256':hashlib.sha256(encoded(timeline.to_dict())).hexdigest(),'timeline_version':timeline.version,
        'rendered_sha256':rendered_sha256,'render_binding':'CURRENT_RENDER' if rendered_sha256 is not None else 'PROJECT_DRAFT_NOT_RENDERED',
        'sources':sources,'unavailable_source_reports':unavailable,'untranscribed_audible_clips':missing,
        'words':words,'cues':cues,'warnings':warnings,'overlapping_cues':overlaps,
        'source_selection':'HUMAN_ANNOTATION_THEN_ASR_PER_SOURCE_STREAM_ORIGINALS_PRESERVED',
        'coverage':'SOURCE_ANNOTATIONS_PROJECTED_NOT_MIX_RECOGNITION','complete_mix_transcription':False,
        'review_state':'UNREVIEWED','human_alignment':'NOT_VERIFIED','new_model_execution':'NOT_RUN',
        'original_audio_modified':False,'timeline_subtitles_modified':False,'redub_performed':False}
    files={'transcript-timeline.json':encoded(result)}
    if cues:
        vtt='WEBVTT\n\n';srt=''
        for index,cue in enumerate(cues,1):
            check();text=cue['text'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            vtt+=f"{index}\n{_stamp(cue['start'],'.')} --> {_stamp(cue['end'],'.')}\n{text}\n\n"
            srt+=f"{index}\n{_stamp(cue['start'],',')} --> {_stamp(cue['end'],',')}\n{text}\n\n"
        files.update({'transcript-timeline.srt':srt.encode(),'transcript-timeline.vtt':vtt.encode()})
    check()
    return {'files':files,'report':result}


def project_transcription_summary(report, raw):
    """Keep the full word graph in its hashed member, not duplicated metadata."""
    return {key:report[key] for key in ('schema','state','time_basis','timeline_sha256','timeline_version',
        'rendered_sha256','render_binding','coverage','complete_mix_transcription','new_model_execution')} | {
        'member':'transcript-timeline.json','sha256':hashlib.sha256(raw).hexdigest(),
        'word_count':len(report['words']),'cue_count':len(report['cues']),'source_count':len(report['sources']),
        'warning_count':len(report['warnings']),'untranscribed_audible_clip_count':len(report['untranscribed_audible_clips'])}


def validate_project_transcription_files(project, render, source_assets, files):
    """Reopen/export checks for source annotations and current v2 sidecars.

    Old projects without this derived schema retain their existing read path.
    A checksum is necessary but cannot make a sidecar from another revision fit.
    """
    from .transcript_editing import validate_manual_transcript
    import math
    by_asset={item['asset']['asset_id']:item for item in source_assets}
    for member,raw in files.items():
        if not re.fullmatch(r'transcription(?:-reviewed)?-MEDIA-[a-f0-9]{16}\.json',member):continue
        report=json.loads(raw);asset=by_asset.get(report.get('source_asset_id'),{}).get('asset')
        if (asset is None or report.get('original_source_sha256')!=asset['sha256']
                or member not in {'transcription-'+asset['asset_id']+'.json','transcription-reviewed-'+asset['asset_id']+'.json'}
                or type(report.get('selected_audio_stream_index')) is not int
                or not 0<=report['selected_audio_stream_index']<asset['audio_stream_count']):
            raise VideoEditingError('CONTENT_TRANSCRIPT_SOURCE_MISMATCH')
        if report.get('source_annotation')=='human_authored_transcript_not_independently_verified':
            if report.get('owner')!='Shared Content Creation':raise VideoEditingError('WORD_EDIT_TRANSCRIPT_PROVENANCE_INVALID')
            validate_manual_transcript(report,duration=asset['duration_sec'])
    raw=files.get('transcript-timeline.json')
    if raw is None:return
    report=json.loads(raw)
    if report.get('schema')!='timeline-transcription:v2':return
    encoded=json.dumps(project['timeline'],ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
    media_hash=None if render.get('state')=='not_rendered' else render.get('media_sha256')
    if (report.get('timeline_sha256')!=hashlib.sha256(encoded).hexdigest()
            or report.get('timeline_version')!=project['timeline'].get('version')
            or report.get('rendered_sha256')!=media_hash
            or report.get('render_binding')!=('CURRENT_RENDER' if media_hash is not None else 'PROJECT_DRAFT_NOT_RENDERED')
            or render.get('delivery_reports',{}).get('timeline_transcription')!=project_transcription_summary(report,raw)):
        raise VideoEditingError('CONTENT_TRANSCRIPT_PROJECT_BINDING_CHANGED')
    sources={}
    for source in report['sources']:
        asset=by_asset.get(source.get('source_asset_id'),{}).get('asset')
        original=files.get(source.get('member'))
        expected_ref=by_asset.get(source.get('source_asset_id'),{}).get('artifact_ref')
        if (asset is None or source.get('source_sha256')!=asset['sha256'] or original is None
                or source.get('source_artifact_ref')!=expected_ref
                or source.get('source_transcription_sha256')!=hashlib.sha256(original).hexdigest()
                or type(source.get('selected_audio_stream_index')) is not int
                or not 0<=source['selected_audio_stream_index']<asset['audio_stream_count']):
            raise VideoEditingError('CONTENT_TRANSCRIPT_SOURCE_MISMATCH')
        sources[(asset['asset_id'],source['selected_audio_stream_index'])]=source
    for value in report['words']+report['cues']:
        source=sources.get((value.get('source_asset_id'),value.get('selected_audio_stream_index')))
        if (source is None or any(value.get(key)!=source[key] for key in
                ('source_sha256','source_artifact_ref','member','source_transcription_sha256'))
                or any(type(value.get(key)) not in (int,float) or not math.isfinite(value[key]) for key in ('start','end'))
                or not 0<=value['start']<value['end']):
            raise VideoEditingError('CONTENT_TRANSCRIPT_PROJECT_BINDING_CHANGED')
    expected={}
    if report['cues']:
        vtt='WEBVTT\n\n';srt=''
        for index,cue in enumerate(report['cues'],1):
            text=cue['text'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            vtt+=f"{index}\n{_stamp(cue['start'],'.')} --> {_stamp(cue['end'],'.')}\n{text}\n\n"
            srt+=f"{index}\n{_stamp(cue['start'],',')} --> {_stamp(cue['end'],',')}\n{text}\n\n"
        expected={'transcript-timeline.vtt':vtt.encode(),'transcript-timeline.srt':srt.encode()}
    if any(files.get(name)!=expected.get(name) for name in ('transcript-timeline.vtt','transcript-timeline.srt')):
        raise VideoEditingError('CONTENT_TRANSCRIPT_SUBTITLE_BINDING_CHANGED')
