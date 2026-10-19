"""Authorized media adaptation to the sole SYSTEM offline speech Gateway.

No model discovery/download, provider fallback, server-path input from clients,
Canonical promotion or transcript persistence occurs here. Optional Artifact
files and API callers retain the existing source/export/version authorization.
"""
import dataclasses,hashlib,json,math,os,re,tempfile,wave
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
        # Scan the actual selected audio frames. The packet cap, JSON byte cap,
        # process timeout and cancellation callback bound malformed/long inputs.
        # A discontinuity needs piecewise renderer semantics, not a guessed offset.
        frames_path = root / 'frames.json'
        _run([probe, '-v', 'error', '-protocol_whitelist', 'file', '-format_whitelist', MEDIA_INPUT_DEMUXERS,
              '-select_streams', f'a:{audio_stream_index}', '-read_intervals', '%+#100001',
              '-show_frames', '-count_packets',
              '-show_entries', 'frame=best_effort_timestamp,nb_samples:stream=nb_read_packets',
              '-of', 'json', '-o', str(frames_path), str(asset.path)], cwd=root, timeout=60,
             check_continue=check_cancel)
        if not frames_path.is_file() or frames_path.stat().st_size > 16 * 1024 * 1024:
            raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_SCAN_LIMIT')
        try:
            scanned = json.loads(frames_path.read_text(encoding='utf-8'))
            frames = scanned['frames']; counts = scanned['streams']
            if (len(counts) != 1 or not 0 < int(counts[0]['nb_read_packets']) < 100001
                    or not isinstance(frames, list) or not 0 < len(frames) <= 100000):
                raise ValueError('bounded complete audio scan required')
            tick = Fraction(selected['time_base'])
            if not 0 < tick <= Fraction(1, 100):
                raise ValueError('audio timestamp resolution unverified')
            tolerance = 2 * tick + Fraction(2, rate)
            previous_end = None; first_pts = None; decoded_samples = 0
            for frame in frames:
                if check_cancel:
                    check_cancel()
                pts = int(frame['best_effort_timestamp']) * tick
                samples = frame['nb_samples']
                if type(samples) is not int or not 0 < samples <= rate * 10:
                    raise ValueError('audio frame size invalid')
                if previous_end is not None and abs(pts - previous_end) > tolerance:
                    raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_DISCONTINUITY_UNSUPPORTED')
                if first_pts is None:
                    first_pts = pts
                if abs(pts - (first_pts + Fraction(decoded_samples, rate))) > tolerance:
                    raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_DISCONTINUITY_UNSUPPORTED')
                decoded_samples += samples
                previous_end = pts + Fraction(samples, rate)
            continuity = {'state': 'decoded_audio_pts_continuity_verified', 'audio_frames': len(frames),
                          'audio_packets': int(counts[0]['nb_read_packets']),
                          'first_decoded_pts_seconds': float(first_pts),
                          'last_decoded_end_seconds': float(previous_end),
                          'timestamp_rounding_tolerance_seconds': float(tolerance),
                          'method': 'bounded_ffprobe_decoded_frame_pts_and_sample_counts'}
        except VideoEditingError:
            raise
        except (ValueError, TypeError, KeyError, IndexError, ZeroDivisionError) as exc:
            raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_UNVERIFIED') from exc
    return {'schema': 'source-audio-clock:v1', 'basis': 'ffmpeg_input_presentation_relative_seconds',
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


def build_transcription_files(asset,*,audio_stream_index=None,language_hint=None,check_cancel=None):
    from shared_artifacts import validate_local_asset,_ffmpeg_path
    from .rendering import _run
    from lumenis.system.ai_gateway import owned_speech
    if language_hint is not None and (not isinstance(language_hint,str) or language_hint not in CONTENT_LANGUAGE_CODES):raise VideoEditingError('CONTENT_ASR_LANGUAGE_INVALID')
    runtime=configured_speech_runtime();asset.validate();path=validate_local_asset(asset.path)
    if not asset.audio_stream_count or asset.duration_sec>600:raise VideoEditingError('CONTENT_ASR_AUDIO_UNSUPPORTED')
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
        from .video_editing import MEDIA_INPUT_DEMUXERS
        _run([ffmpeg,'-v','error','-nostdin','-n','-protocol_whitelist','file','-format_whitelist',MEDIA_INPUT_DEMUXERS,
              '-i',str(path),'-map',f'0:a:{audio_stream_index}','-vn','-sn','-dn','-map_metadata','-1',
              '-af',_transcription_normalization_filter(asset.duration_sec),
              '-ar','16000','-ac','1','-c:a','pcm_s16le',str(normalized)],cwd=work,timeout=180,check_continue=check_cancel)
        try:
            with wave.open(str(normalized), 'rb') as audio:
                frames = audio.getnframes()
                if (audio.getframerate() != _TRANSCRIPTION_SAMPLE_RATE or audio.getnchannels() != 1
                        or audio.getsampwidth() != 2 or frames != round(asset.duration_sec * _TRANSCRIPTION_SAMPLE_RATE)):
                    raise ValueError('normalized audio clock mismatch')
        except (OSError, ValueError, wave.Error) as exc:
            raise VideoEditingError('CONTENT_ASR_NORMALIZATION_UNVERIFIED') from exc
        normalized_hash = hashlib.sha256(normalized.read_bytes()).hexdigest()
        normalization = {'schema': 'source-audio-normalization:v1', 'sha256': normalized_hash,
                         'sample_rate': _TRANSCRIPTION_SAMPLE_RATE, 'frame_count': frames,
                         'duration_seconds': frames / _TRANSCRIPTION_SAMPLE_RATE,
                         'source_clock': source_clock,
                         'filter': _transcription_normalization_filter(asset.duration_sec),
                         'mapping': 'identity_after_pts_aligned_padding_and_negative_time_trim',
                         'timestamp_quantization_seconds': 1 / _TRANSCRIPTION_SAMPLE_RATE}
        def cancelled():check();return False
        try:
            result=owned_speech.transcribe_audio(str(normalized),expected_audio_sha256=normalized_hash,runtime=runtime,source_ref=asset.asset_id,is_cancelled=cancelled,language_hint=language_hint)
        except owned_speech.SpeechBlocked as exc:
            code=str(exc)
            raise VideoEditingError(code if re.fullmatch('[A-Z_0-9]{1,100}',code) else 'CONTENT_ASR_FAILED') from exc
    verify()
    if _source_transcription_clock(asset, audio_stream_index, check_cancel=check_cancel) != source_clock:
        raise VideoEditingError('CONTENT_ASR_SOURCE_CLOCK_CHANGED')
    if result.get('source_sha256', normalized_hash) != normalized_hash:
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
    """Derive selected-source subtitles using the renderer's unit-rate audio clock.

    This is not mixed-output recognition or human-verified alignment. Originals
    remain untouched. Unsupported timing semantics fail rather than guess.
    """
    from .video_editing import TimelineClip
    from .rendering import SAMPLE_RATE, _number
    from lumenis.system.ai_gateway.owned_speech import validate_transcript
    def check():
        if check_cancel: check_cancel()
    def fail(code):
        raise VideoEditingError('CONTENT_ASR_TIMELINE_'+code)
    def encoded(value):
        return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
    check();timeline.validate()
    if not isinstance(rendered_sha256,str) or not re.fullmatch('[a-f0-9]{64}',rendered_sha256):fail('OUTPUT_HASH_INVALID')
    report=source_item['report'];original=source_item['files']['transcription.json']
    if json.loads(original)!=report:fail('SOURCE_REPORT_MISMATCH')
    asset=next((a for a in timeline.assets if a.asset_id==report.get('source_asset_id')),None)
    if asset is None or asset.sha256!=report.get('original_source_sha256'):fail('SOURCE_MISMATCH')
    if fingerprint_local_media(asset.path).sha256!=asset.sha256:fail('SOURCE_CHANGED')
    transcript=report['transcript'];validate_transcript(transcript,duration_seconds=asset.duration_sec)
    selected_stream=report.get('selected_audio_stream_index')
    if type(selected_stream) is not int or not 0<=selected_stream<asset.audio_stream_count:fail('STREAM_INVALID')
    normalization = report.get('audio_normalization')
    if normalization is None:
        # Historical WAV reports used a sample-zero source. Old arbitrary
        # container reports never proved this identity and must be regenerated.
        if Path(asset.path).suffix.lower() != '.wav':
            fail('SOURCE_CLOCK_UNVERIFIED')
    else:
        if (not isinstance(normalization, dict)
                or normalization.get('schema') != 'source-audio-normalization:v1'
                or normalization.get('source_clock') != _source_transcription_clock(asset, selected_stream, check_cancel=check_cancel)
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
    clips=[]
    for track in timeline.tracks:
        for clip in track.clips:
            check()
            if type(clip) is not TimelineClip or set(vars(clip))!={f.name for f in dataclasses.fields(TimelineClip)}:fail('RATE_UNSUPPORTED')
            if clip.media_asset_id!=asset.asset_id or clip.audio_role=='muted' or clip.audio_mix.volume==0:continue
            stream=clip.audio_stream_index
            if stream is None and asset.audio_stream_count==1:stream=0
            if stream!=selected_stream:continue
            start=round(clip.timeline_start*SAMPLE_RATE)/SAMPLE_RATE
            end=start+round(clip.duration_sec*SAMPLE_RATE)/SAMPLE_RATE
            clips.append((start,end,clip))
    clips.sort(key=lambda entry:(entry[0],entry[2].clip_id))
    if any(right[0]<left[1] for left,right in zip(clips,clips[1:])):fail('OVERLAP_REQUIRES_REVIEW')
    words=[];warnings=[]
    for start,end,clip in clips:
        source_in=float(_number(clip.source_in));source_out=float(_number(clip.source_out))
        for segment in transcript['segments']:
            for index,word in enumerate(segment['words']):
                check();a=word['start'];b=word['end'];word_id=f"{segment['id']}:{index}"
                if b<=source_in or a>=source_out:continue
                if a<source_in or b>source_out or b<=a:
                    warnings.append({'reason':'cut_or_zero_length_word_omitted','clip_id':clip.clip_id,'source_word_id':word_id});continue
                out_a=start+a-source_in;out_b=start+b-source_in
                if out_b>end or round(out_b*1000)<=round(out_a*1000):
                    warnings.append({'reason':'outside_rendered_or_submillisecond_word_omitted','clip_id':clip.clip_id,'source_word_id':word_id});continue
                words.append({'source_word_id':word_id,'clip_id':clip.clip_id,'text':word['word'],
                              'source_start':a,'source_end':b,'start':out_a,'end':out_b})
    # A cue per retained word keeps source identity and prevents grouping across cuts.
    vtt='WEBVTT\n\n';srt=''
    for index,word in enumerate(words,1):
        text=word['text'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        vtt+=f"{index}\n{_stamp(word['start'],'.')} --> {_stamp(word['end'],'.')}\n{text}\n\n"
        srt+=f"{index}\n{_stamp(word['start'],',')} --> {_stamp(word['end'],',')}\n{text}\n\n"
    derived={'schema':'timeline-transcription:v1','state':'available' if words else 'no_retained_words',
             'time_basis':'rendered_output_seconds','mapping':'unit_rate_source_words_sample_quantized_clip_delay',
             'source_asset_id':asset.asset_id,'source_sha256':asset.sha256,'selected_audio_stream_index':selected_stream,
             'source_transcription_sha256':hashlib.sha256(original).hexdigest(),
             'source_audio_normalization':normalization,
             'source_clock_definition':'container_presentation_relative_not_absolute_stream_pts',
             'timeline_sha256':hashlib.sha256(encoded(timeline.to_dict())).hexdigest(),'timeline_version':timeline.version,
             'rendered_sha256':rendered_sha256,'coverage':'selected_source_and_audio_stream_only',
             'complete_mix_transcription':False,'review_state':'UNREVIEWED','human_alignment':'NOT_VERIFIED',
             'requires_user_review':True,'words':words,'warnings':warnings}
    files={'transcript-timeline.json':encoded(derived)}
    if words:files.update({'transcript-timeline.srt':srt.encode(),'transcript-timeline.vtt':vtt.encode()})
    check()
    return {'files':files,'report':derived}
