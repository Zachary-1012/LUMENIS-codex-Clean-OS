"""Explicit word selections become immutable EDL candidates, never automatic edits."""
import hashlib,json,math,re,unicodedata
from copy import deepcopy
from .video_editing import VideoEditingError


def validate_manual_transcript(report, *, duration):
    """Human timing is an explicit annotation, never invented ASR confidence."""
    transcript = report.get('transcript')
    if (type(transcript) is not dict or set(transcript) != {'language','text','segments'}
            or type(transcript['segments']) is not list or not 1 <= len(transcript['segments']) <= 4096):
        raise VideoEditingError('MANUAL_TRANSCRIPT_INVALID')
    ids=set();previous_by_speaker={};words=0
    for segment in transcript['segments']:
        if (type(segment) is not dict or set(segment) != {'id','start','end','text','speaker_id','words'}
                or type(segment['id']) is not int or segment['id'] < 0 or segment['id'] in ids
                or type(segment['speaker_id']) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',segment['speaker_id'])
                or type(segment['text']) is not str or not segment['text'].strip() or len(segment['text']) > 64000
                or any(unicodedata.category(c).startswith('C') and c not in '\n\t' for c in segment['text'])
                or type(segment['words']) is not list):
            raise VideoEditingError('MANUAL_TRANSCRIPT_SEGMENT_INVALID')
        start,end=segment['start'],segment['end'];speaker=segment['speaker_id']
        if (any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,end))
                or not previous_by_speaker.get(speaker,0) <= start < end <= duration):
            raise VideoEditingError('MANUAL_TRANSCRIPT_TIMING_INVALID')
        last=start
        for word in segment['words']:
            if (type(word) is not dict or set(word) != {'word','start','end'} or type(word['word']) is not str
                    or not word['word'].strip() or len(word['word']) > 1000
                    or any(type(word[k]) not in (int,float) or not math.isfinite(word[k]) for k in ('start','end'))
                    or not last <= word['start'] < word['end'] <= end):
                raise VideoEditingError('MANUAL_TRANSCRIPT_WORD_INVALID')
            last=word['end'];words+=1
        previous_by_speaker[speaker]=end;ids.add(segment['id'])
    if words > 100000 or transcript['text'] != '\n'.join(segment['text'] for segment in transcript['segments']):
        raise VideoEditingError('MANUAL_TRANSCRIPT_INVALID')
    return transcript


def transcript_annotation_files(report, *, member, reviewed=False):
    from .speech_transcription import _stamp
    if not isinstance(member,str) or not re.fullmatch(r'transcription(?:-reviewed)?-MEDIA-[a-f0-9]{16}\.json',member):
        raise VideoEditingError('TRANSCRIPT_MEMBER_INVALID')
    segments=report['text_review']['segments'] if reviewed else report['transcript']['segments']
    vtt='WEBVTT\n\n';srt=''
    for index,segment in enumerate(segments,1):
        text=segment['text'].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        vtt+=f"{index}\n{_stamp(segment['start'],'.')} --> {_stamp(segment['end'],'.')}\n{text}\n\n"
        srt+=f"{index}\n{_stamp(segment['start'],',')} --> {_stamp(segment['end'],',')}\n{text}\n\n"
    stem=member.removesuffix('.json')
    return {member:json.dumps(report,ensure_ascii=False,sort_keys=True,allow_nan=False).encode(),
            stem+'.vtt':vtt.encode(),stem+'.srt':srt.encode()}


def build_manual_transcript_files(asset, *, audio_stream_index, language, segments, check_cancel=None):
    from .speech_transcription import _source_transcription_clock
    from lumenis.system.ai_gateway.owned_speech import CONTENT_LANGUAGE_CODES
    if (type(audio_stream_index) is not int or not 0 <= audio_stream_index < asset.audio_stream_count
            or type(language) is not str or language not in CONTENT_LANGUAGE_CODES):
        raise VideoEditingError('MANUAL_TRANSCRIPT_SOURCE_INVALID')
    transcript={'language':language,'text':'\n'.join(s.get('text','') for s in segments) if type(segments) is list and all(type(s) is dict and type(s.get('text')) is str for s in segments) else '',
                'segments':deepcopy(segments)}
    report={'schema':'human-source-transcript:v1','owner':'Shared Content Creation',
        'source_annotation':'human_authored_transcript_not_independently_verified',
        'source_asset_id':asset.asset_id,'original_source_sha256':asset.sha256,
        'selected_audio_stream_index':audio_stream_index,'transcript_time_basis':'original_source_seconds',
        'transcript':transcript,'owned_model_execution':'NOT_RUN','speaker_diarization':'human_labels_not_identity_proof',
        'timestamp_method':'human_supplied_source_seconds','word_alignment':'HUMAN_SUPPLIED_NOT_MEASURED',
        'original_audio_modified':False,'subtitle_timeline_modified':False,'redub_performed':False}
    validate_manual_transcript(report,duration=asset.duration_sec)
    report['source_audio_clock']=_source_transcription_clock(asset,audio_stream_index,check_cancel=check_cancel)
    return {'report':report,'files':transcript_annotation_files(report,member='transcription-'+asset.asset_id+'.json')}


def review_source_transcript(report, *, edits, expected_sha256, original_bytes):
    if (hashlib.sha256(original_bytes).hexdigest() != expected_sha256 or json.loads(original_bytes) != report
            or type(edits) is not list or not 1 <= len(edits) <= 4096):
        raise VideoEditingError('TRANSCRIPT_REVIEW_BASE_INVALID')
    base=report.get('text_review',{}).get('segments',report['transcript']['segments'])
    by_id={segment['id']:deepcopy(segment) for segment in base};seen=set()
    for edit in edits:
        if (type(edit) is not dict or not {'segment_id','expected_text','text','confirmed'} <= set(edit)
                or set(edit)-{'segment_id','expected_text','text','confirmed','speaker_id'}
                or type(edit['segment_id']) is not int or edit['segment_id'] not in by_id or edit['segment_id'] in seen
                or edit['confirmed'] is not True or edit['expected_text'] != by_id[edit['segment_id']]['text']
                or type(edit['text']) is not str or not edit['text'].strip() or len(edit['text']) > 64000
                or any(unicodedata.category(c).startswith('C') and c not in '\n\t' for c in edit['text'])):
            raise VideoEditingError('TRANSCRIPT_REVIEW_EDIT_INVALID')
        if 'speaker_id' in edit and (type(edit['speaker_id']) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',edit['speaker_id'])):
            raise VideoEditingError('TRANSCRIPT_REVIEW_SPEAKER_INVALID')
        target=by_id[edit['segment_id']];target['text']=edit['text']
        if 'speaker_id' in edit:target['speaker_id']=edit['speaker_id']
        seen.add(edit['segment_id'])
    reviewed={**deepcopy(report),'text_review':{'schema':'source-transcript-text-review/v1',
        'base_sha256':expected_sha256,'segments':[by_id[segment['id']] for segment in base],'edits':deepcopy(edits),
        'edit_kind':'correct_transcript_text','word_timestamps':'ORIGINAL_NOT_RECOMPUTED',
        'original_transcript_modified':False,'timeline_subtitles_modified':False,'audio_video_modified':False,
        'redub_performed':False,'speaker_labels':'HUMAN_DECLARATION_NOT_IDENTITY_PROOF'}}
    return reviewed


def _word_edit_context(timeline, transcript, *, clip_ids=None):
    timeline.validate()
    if not isinstance(transcript, dict):
        raise VideoEditingError('WORD_EDIT_SOURCE_MISMATCH')
    asset = next((item for item in timeline.assets
                  if item.sha256 == transcript.get('original_source_sha256')), None)
    if asset is None:
        raise VideoEditingError('WORD_EDIT_SOURCE_MISMATCH')
    stream = transcript.get('selected_audio_stream_index')
    if type(stream) is not int or not 0 <= stream < asset.audio_stream_count:
        raise VideoEditingError('WORD_EDIT_SOURCE_MISMATCH')
    matching = [clip for track in timeline.tracks for clip in track.clips
                if clip.media_asset_id == asset.asset_id and clip.audio_role != 'muted'
                and (clip.audio_stream_index if clip.audio_stream_index is not None else 0) == stream]
    if clip_ids is not None:
        if (type(clip_ids) is not list or not clip_ids or len(set(clip_ids)) != len(clip_ids)
                or any(type(value) is not str for value in clip_ids)
                or set(clip_ids) - {clip.clip_id for clip in matching}):
            raise VideoEditingError('WORD_EDIT_CLIP_SELECTION_INVALID')
        matching = [clip for clip in matching if clip.clip_id in clip_ids]
    if not matching:
        raise VideoEditingError('WORD_EDIT_SOURCE_MISMATCH')
    return matching, asset


def _index_words(transcript, duration):
    indexed = {}
    previous_by_speaker = {}
    for segment in transcript.get('transcript', {}).get('segments', []):
        speaker = segment.get('speaker_id', segment.get('speaker'))
        if speaker is not None and (not isinstance(speaker, (str, int)) or isinstance(speaker, bool)):
            raise VideoEditingError('WORD_EDIT_SPEAKER_INVALID')
        previous = previous_by_speaker.get(speaker, 0)
        for index, word in enumerate(segment.get('words', [])):
            start, end = word.get('start'), word.get('end')
            if (any(type(value) not in (int, float) or not math.isfinite(value) for value in (start, end))
                    or not previous <= start < end <= duration):
                raise VideoEditingError('WORD_EDIT_TIMESTAMPS_INVALID')
            identity = f"{segment['id']}:{index}"
            if identity in indexed:
                raise VideoEditingError('WORD_EDIT_TIMESTAMPS_INVALID')
            indexed[identity] = (start, end, word.get('word', ''), speaker)
            previous = end
        previous_by_speaker[speaker] = previous
    return indexed


def _rational(value):
    from fractions import Fraction
    value = Fraction(str(value))
    return {'numerator': value.numerator, 'denominator': value.denominator}


def word_deletion_candidate(timeline, transcript, *, word_ids, transcript_artifact_id,
                            transcript_sha256, clip_ids=None, synchronize=True):
    clips, asset = _word_edit_context(timeline, transcript, clip_ids=clip_ids)
    if (type(word_ids) is not list or not word_ids or len(word_ids) > 100000
            or any(type(value) is not str for value in word_ids)
            or len(set(word_ids)) != len(word_ids) or type(synchronize) is not bool):
        raise VideoEditingError('WORD_EDIT_SELECTION_INVALID')
    indexed = _index_words(transcript, asset.duration_sec)
    if not indexed or any(key not in indexed for key in word_ids):
        raise VideoEditingError('WORD_EDIT_WORD_ID_UNKNOWN')
    cuts, mappings, selected = [], [], []
    from fractions import Fraction
    for key in word_ids:
        start, end, text, speaker = indexed[key]
        occurrences = [clip for clip in clips if clip.source_in <= start < end <= clip.source_out]
        if not occurrences:
            raise VideoEditingError('WORD_EDIT_OUTSIDE_CLIP')
        if len(occurrences) > 1 and clip_ids is None:
            raise VideoEditingError('WORD_EDIT_CLIP_SELECTION_REQUIRED')
        selected.append({'id': key, 'text': text, 'start': start, 'end': end, 'speaker_id': speaker})
        for clip in occurrences:
            rate = Fraction(str(clip.playback_rate))
            origin = Fraction(str(clip.timeline_start))
            source_in = Fraction(str(clip.source_in))
            mapped_start = origin + (Fraction(str(start)) - source_in) / rate
            mapped_end = origin + (Fraction(str(end)) - source_in) / rate
            sample_rate = (transcript.get('audio_normalization') or {}).get('source_clock', transcript.get('source_audio_clock',{})).get('source_sample_rate')
            mappings.append({'word_id': key, 'speaker_id': speaker, 'clip_id': clip.clip_id,
                'track_id': clip.track_id, 'source_asset_id': asset.asset_id, 'source_sha256': asset.sha256,
                'audio_stream_index': transcript['selected_audio_stream_index'],
                'source_start': start, 'source_end': end,
                'source_sample_rate': sample_rate,
                'source_start_sample': round(Fraction(str(start)) * sample_rate) if type(sample_rate) is int and sample_rate > 0 else None,
                'source_end_sample': round(Fraction(str(end)) * sample_rate) if type(sample_rate) is int and sample_rate > 0 else None,
                'timeline_start': float(mapped_start), 'timeline_end': float(mapped_end),
                'timeline_start_exact': _rational(mapped_start), 'timeline_end_exact': _rational(mapped_end),
                'playback_rate': clip.playback_rate})
            cuts.append({'clip_id': clip.clip_id, 'source_in': start, 'source_out': end})
    # The batch is a single immutable Timeline transaction, not a truncated list
    # of split/delete commands. The existing metadata byte budget remains binding.
    binding = {'timeline': timeline.to_dict(), 'transcript_artifact_id': transcript_artifact_id,
               'transcript_sha256': transcript_sha256, 'word_ids': word_ids,
               'clip_ids': clip_ids, 'synchronize': synchronize}
    identity = hashlib.sha256(json.dumps(binding, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]
    decision = {'source_clip_ref': cuts[0]['clip_id'], 'in_sec': None, 'out_sec': None,
        'operation': 'word_cut', 'reason': '用户明确选择源词和片段；词界仍需试听审核',
        'confidence': 0, 'narrative_beat': '词级剪辑预览',
        'metadata': {'cuts': cuts, 'synchronize': synchronize}}
    preview = timeline.cut_source_intervals(cuts, synchronize=synchronize)
    affected_clips = [clip.clip_id for track in timeline.tracks for clip in track.clips
                      if (synchronize or clip.clip_id in {cut['clip_id'] for cut in cuts})
                      if any(item['timeline_start'] < clip.timeline_start + clip.duration_sec
                             and item['timeline_end'] > clip.timeline_start for item in mappings)]
    affected_captions = [overlay.overlay_id for overlay in timeline.overlays if synchronize
                        if any(item['timeline_start'] < overlay.end_sec and item['timeline_end'] > overlay.start_sec
                               for item in mappings)]
    return {'state': 'candidate', 'edit_kind': 'cut_original',
        'edl': {'candidate_id': 'EDL-words-' + identity, 'decisions': [decision]},
        'removed_source_intervals': sorted({(item['source_in'], item['source_out']) for item in cuts}),
        'selected_words': selected, 'word_mappings': mappings,
        'affected_clip_ids': affected_clips, 'affected_caption_ids': affected_captions,
        'preview_timeline': preview.to_dict(), 'synchronize': synchronize,
        'source_sha256': asset.sha256, 'transcript_artifact_id': transcript_artifact_id,
        'transcript_sha256': transcript_sha256, 'timestamp_origin': transcript.get('source_annotation','model_estimated_unreviewed_derivative'),
        'boundary_rounding_seconds': 0, 'human_alignment_accuracy': 'NOT_VERIFIED',
        'requires_user_review': True, 'automatic_application': False,
        'original_media_modified': False, 'transcript_text_modified': False,
        'redub_performed': False}


def _literal_token(value):
    if not isinstance(value,str) or len(value)>256 or any(ord(c)<32 for c in value):
        raise VideoEditingError('WORD_EDIT_FILLER_TERM_INVALID')
    value=unicodedata.normalize('NFKC',value).casefold().strip()
    while value and unicodedata.category(value[0]).startswith('P'):value=value[1:]
    while value and unicodedata.category(value[-1]).startswith('P'):value=value[:-1]
    return value


def filler_word_deletion_candidate(timeline,transcript,*,filler_terms,transcript_artifact_id,transcript_sha256,clip_ids=None,synchronize=True):
    clips,asset=_word_edit_context(timeline,transcript,clip_ids=clip_ids)
    indexed=_index_words(transcript,asset.duration_sec)
    if not indexed:raise VideoEditingError('WORD_EDIT_WORD_TIMES_REQUIRED')
    if not isinstance(filler_terms,list) or not 1<=len(filler_terms)<=30:
        raise VideoEditingError('WORD_EDIT_FILLER_TERMS_INVALID')
    normalized=[]
    for term in filler_terms:
        token=_literal_token(term)
        if not 1<=len(token)<=64 or any(c.isspace() for c in token) or token in normalized:
            raise VideoEditingError('WORD_EDIT_FILLER_TERM_INVALID')
        normalized.append(token)
    ordered=list(indexed);matches=[];contexts=[]
    for pos,key in enumerate(ordered):
        start,end,text,_speaker=indexed[key]
        if any(clip.source_in<=start<end<=clip.source_out for clip in clips) and _literal_token(text) in normalized:
            matches.append(key)
            contexts.append({'word_id':key,'source_start':start,'source_end':end,
                'context':[{'id':k,'text':indexed[k][2],'start':indexed[k][0],'end':indexed[k][1]} for k in ordered[max(0,pos-2):pos+3]]})
    if not matches:
        result={'state':'no_matches','edl':None,'selected_words':[],'automatic_application':False,
                'transcript_artifact_id':transcript_artifact_id,'transcript_sha256':transcript_sha256,'source_sha256':asset.sha256}
    else:
        result=word_deletion_candidate(timeline,transcript,word_ids=matches,transcript_artifact_id=transcript_artifact_id,transcript_sha256=transcript_sha256,clip_ids=clip_ids,synchronize=synchronize)
    return {**result,'filler_terms':filler_terms,'normalized_terms':normalized,'candidate_contexts':contexts,
            'selection_method':'explicit_user_terms_literal_original_asr_token_match',
            'matching_recipe':{'unicode_normalization':'NFKC','unicode_version':unicodedata.unidata_version,'case':'casefold',
                'boundary':'strip_outer_whitespace_and_unicode_punctuation','tokenization':'original_ASR_word_units_no_retokenization_or_substring_matching'},
            'semantic_filler_classification':False,'requires_user_review':True}


def project_word_deletion_candidate(project_id, *, word_ids=None, filler_terms=None, expected_transcript_sha256=None,
                                    clip_ids=None, synchronize=True, transcript_asset_id=None,
                                    actor, scope, source_artifact_refs):
    import zipfile
    import shared_artifacts as owner
    from .video_editing import Timeline
    project,_,record,path=owner._verified_content_project(project_id,actor=actor,**scope)
    refs=project.get('source_artifact_refs',[])
    if not refs or set(refs)!=set(source_artifact_refs):raise VideoEditingError('WORD_EDIT_SOURCE_SCOPE_MISMATCH')
    member = 'transcription.json' if transcript_asset_id is None else 'transcription-' + transcript_asset_id + '.json'
    if transcript_asset_id is not None and (not isinstance(transcript_asset_id,str) or not re.fullmatch(r'MEDIA-[a-f0-9]{16}',transcript_asset_id)):
        raise VideoEditingError('WORD_EDIT_SOURCE_MISMATCH')
    entry=project.get('delivery_manifest',{}).get(member)
    if not entry:raise VideoEditingError('WORD_EDIT_VERIFIED_TRANSCRIPT_REQUIRED')
    if filler_terms is not None:
        if word_ids is not None or not isinstance(expected_transcript_sha256,str) or not re.fullmatch(r'[0-9a-f]{64}',expected_transcript_sha256):
            raise VideoEditingError('WORD_EDIT_FILLER_BINDING_REQUIRED')
        if expected_transcript_sha256!=entry['sha256']:raise VideoEditingError('WORD_EDIT_TRANSCRIPT_STALE')
    with zipfile.ZipFile(path) as package:data=package.read(member)
    if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise VideoEditingError('WORD_EDIT_TRANSCRIPT_HASH_MISMATCH')
    transcript=json.loads(data)
    asr = transcript.get('owner')=='SYSTEM AI Gateway' and transcript.get('source_annotation')=='model_estimated_unreviewed_derivative'
    manual = transcript.get('owner')=='Shared Content Creation' and transcript.get('source_annotation')=='human_authored_transcript_not_independently_verified'
    if not (asr or manual):
        raise VideoEditingError('WORD_EDIT_TRANSCRIPT_PROVENANCE_INVALID')
    with owner.resolve_content_source_assets(refs,actor=actor,**scope) as sources:
        timeline=Timeline.from_dict(project['timeline'],assets=[item['asset'] for item in sources])
        if filler_terms is not None:
            candidate=filler_word_deletion_candidate(timeline,transcript,filler_terms=filler_terms,transcript_artifact_id=project_id,transcript_sha256=entry['sha256'],clip_ids=clip_ids,synchronize=synchronize)
        else:
            candidate=word_deletion_candidate(timeline,transcript,word_ids=word_ids,transcript_artifact_id=project_id,transcript_sha256=entry['sha256'],clip_ids=clip_ids,synchronize=synchronize)
    _,_,current,_=owner._verified_content_project(project_id,actor=actor,**scope)
    if current['sha256']!=record['sha256']:raise VideoEditingError('WORD_EDIT_PROJECT_CHANGED')
    return {**candidate,'parent_artifact_id':project_id,'parent_sha256':record['sha256'],'parent_timeline_version':timeline.version}
