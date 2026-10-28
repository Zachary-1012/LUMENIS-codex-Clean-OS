"""Explicit word selections become immutable EDL candidates, never automatic edits."""
import hashlib,json,math,re,unicodedata
from copy import deepcopy
from .video_editing import VideoEditingError


def validate_manual_transcript(report, *, duration):
    """Human timing is an explicit annotation, never invented ASR confidence."""
    from lumenis.system.ai_gateway.owned_speech import CONTENT_LANGUAGE_CODES
    transcript = report.get('transcript')
    if (type(transcript) is not dict or set(transcript) != {'language','text','segments'}
            or type(transcript['language']) is not str or transcript['language'] not in CONTENT_LANGUAGE_CODES
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
    source_asset_id = transcript.get('source_asset_id')
    if source_asset_id is not None:
        asset = next((item for item in timeline.assets
                      if item.asset_id == source_asset_id
                      and item.sha256 == transcript.get('original_source_sha256')), None)
    else:
        # Legacy annotations without an asset id are usable only when their
        # content hash identifies exactly one asset in this project. Equal
        # bytes do not establish the same source/artifact/permission identity.
        matches = [item for item in timeline.assets
                   if item.sha256 == transcript.get('original_source_sha256')]
        asset = matches[0] if len(matches) == 1 else None
    if asset is None:
        raise VideoEditingError('WORD_EDIT_SOURCE_MISMATCH')
    stream = transcript.get('selected_audio_stream_index')
    if type(stream) is not int or not 0 <= stream < asset.audio_stream_count:
        raise VideoEditingError('WORD_EDIT_SOURCE_MISMATCH')
    matching = [clip for track in timeline.tracks for clip in track.clips
                if clip.media_asset_id == asset.asset_id and clip.audio_role != 'muted'
                and (clip.audio_stream_index if clip.audio_stream_index is not None else 0) == stream]
    if clip_ids is not None:
        if (type(clip_ids) is not list or not clip_ids
                or any(type(value) is not str for value in clip_ids)
                or len(set(clip_ids)) != len(clip_ids)
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
                                    source_selections=None,
                                    actor, scope, source_artifact_refs):
    if source_selections is not None:
        if (word_ids is not None or filler_terms is not None or expected_transcript_sha256 is not None
                or clip_ids is not None or transcript_asset_id is not None):
            raise VideoEditingError('WORD_EDIT_SOURCE_SELECTIONS_MIXED')
        return project_multi_source_word_deletion_candidate(project_id,source_selections=source_selections,
            synchronize=synchronize,actor=actor,scope=scope,source_artifact_refs=source_artifact_refs)
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
    if expected_transcript_sha256 is not None:
        if (not isinstance(expected_transcript_sha256,str) or not re.fullmatch(r'[0-9a-f]{64}',expected_transcript_sha256)
                or expected_transcript_sha256!=entry['sha256']):
            raise VideoEditingError('WORD_EDIT_TRANSCRIPT_STALE')
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


def project_multi_source_word_deletion_candidate(project_id, *, source_selections, synchronize=True,
                                                 actor, scope, source_artifact_refs):
    """Prepare one CAS-bound word-cut transaction across source transcripts.

    Each source selection binds a transcript member/hash independently because
    word ids are local to a transcript. The cuts are compiled together against
    the unchanged parent Timeline and applied once; no intermediate preview is
    treated as a saved revision.
    """
    import zipfile
    import shared_artifacts as owner
    from fractions import Fraction
    from .video_editing import Timeline

    if (not isinstance(project_id,str) or not project_id or type(synchronize) is not bool
            or type(source_selections) is not list or not 1 <= len(source_selections) <= 256):
        raise VideoEditingError('WORD_EDIT_SOURCE_SELECTIONS_INVALID')
    seen_assets={};seen_selections=set();total_words=0;normalized=[]
    for selection in source_selections:
        if (type(selection) is not dict
                or set(selection)-{'transcript_asset_id','expected_transcript_sha256','word_ids','clip_ids'}
                or not {'transcript_asset_id','expected_transcript_sha256','word_ids','clip_ids'} <= set(selection)):
            raise VideoEditingError('WORD_EDIT_SOURCE_SELECTION_INVALID')
        asset_id=selection['transcript_asset_id'];digest=selection['expected_transcript_sha256']
        word_ids=selection['word_ids'];occurrences=selection['clip_ids']
        if (type(asset_id) is not str or not re.fullmatch(r'MEDIA-[a-f0-9]{16}',asset_id)
                or type(digest) is not str or not re.fullmatch(r'[0-9a-f]{64}',digest)
                or type(word_ids) is not list or not word_ids or len(word_ids)>100000
                or any(type(value) is not str for value in word_ids) or len(set(word_ids))!=len(word_ids)
                or type(occurrences) is not list or not occurrences
                or any(type(value) is not str for value in occurrences)
                or len(set(occurrences))!=len(occurrences)):
            raise VideoEditingError('WORD_EDIT_SOURCE_SELECTION_INVALID')
        if asset_id in seen_assets and seen_assets[asset_id] != digest:
            raise VideoEditingError('WORD_EDIT_TRANSCRIPT_STALE')
        if occurrences is not None and len(word_ids) > 1 and len(occurrences) > 1:
            raise VideoEditingError('WORD_EDIT_SOURCE_SELECTION_AMBIGUOUS')
        selection_identity=(asset_id,digest,tuple(sorted(word_ids)),tuple(sorted(occurrences)))
        if selection_identity in seen_selections:
            raise VideoEditingError('WORD_EDIT_SOURCE_SELECTION_DUPLICATE')
        seen_selections.add(selection_identity);seen_assets[asset_id]=digest;total_words+=len(word_ids)
        if total_words>100000:raise VideoEditingError('WORD_EDIT_SELECTION_INVALID')
        normalized.append({'transcript_asset_id':asset_id,'expected_transcript_sha256':digest,
            'word_ids':list(word_ids),'clip_ids':list(occurrences)})

    project,_,record,path=owner._verified_content_project(project_id,actor=actor,**scope)
    refs=project.get('source_artifact_refs',[])
    if not refs or set(refs)!=set(source_artifact_refs):raise VideoEditingError('WORD_EDIT_SOURCE_SCOPE_MISMATCH')
    try:
        with zipfile.ZipFile(path) as package:
            source_reports=[]
            manifest=project.get('delivery_manifest',{})
            for selection in normalized:
                asset_id=selection['transcript_asset_id']
                member='transcription-'+asset_id+'.json'
                entry=manifest.get(member)
                if not entry:raise VideoEditingError('WORD_EDIT_VERIFIED_TRANSCRIPT_REQUIRED')
                raw=package.read(member)
                actual_hash=hashlib.sha256(raw).hexdigest()
                if actual_hash!=entry.get('sha256'):
                    raise VideoEditingError('WORD_EDIT_TRANSCRIPT_HASH_MISMATCH')
                if actual_hash!=selection['expected_transcript_sha256']:
                    raise VideoEditingError('WORD_EDIT_TRANSCRIPT_STALE')
                report=json.loads(raw)
                if type(report) is not dict or report.get('source_asset_id')!=asset_id:
                    raise VideoEditingError('WORD_EDIT_TRANSCRIPT_PROVENANCE_INVALID')
                source_reports.append((selection,member,raw,report))
    except (zipfile.BadZipFile,KeyError,json.JSONDecodeError) as exc:
        raise VideoEditingError('WORD_EDIT_PROJECT_PACKAGE_INVALID') from exc

    with owner.resolve_content_source_assets(refs,actor=actor,**scope) as sources:
        timeline=Timeline.from_dict(project['timeline'],assets=[item['asset'] for item in sources])
        assets={asset.asset_id:asset for asset in timeline.assets}
        compiled=[];bindings=[];combined_cuts=[];source_candidates=[];removed_intervals=[]
        seen_cuts=set();seen_occurrences=set()
        for selection,member,raw,report in source_reports:
            asset=assets.get(selection['transcript_asset_id'])
            if (asset is None or report.get('original_source_sha256')!=asset.sha256
                    or type(report.get('selected_audio_stream_index')) is not int
                    or not 0<=report['selected_audio_stream_index']<asset.audio_stream_count):
                raise VideoEditingError('WORD_EDIT_SOURCE_MISMATCH')
            annotation=report.get('source_annotation')
            manual=(report.get('owner')=='Shared Content Creation'
                    and annotation=='human_authored_transcript_not_independently_verified')
            asr=(report.get('owner')=='SYSTEM AI Gateway'
                 and annotation=='model_estimated_unreviewed_derivative')
            if not (manual or asr):raise VideoEditingError('WORD_EDIT_TRANSCRIPT_PROVENANCE_INVALID')
            if manual:
                validate_manual_transcript(report,duration=asset.duration_sec)
            else:
                from lumenis.system.ai_gateway.owned_speech import validate_transcript
                validate_transcript(report.get('transcript'),duration_seconds=asset.duration_sec)
            candidate=word_deletion_candidate(timeline,report,word_ids=selection['word_ids'],
                transcript_artifact_id=project_id,transcript_sha256=selection['expected_transcript_sha256'],
                clip_ids=selection['clip_ids'],synchronize=synchronize)
            source_candidates.append(candidate)
            cuts=candidate['edl']['decisions'][0]['metadata']['cuts']
            binding={'transcript_asset_id':asset.asset_id,'source_asset_id':asset.asset_id,
                'source_sha256':asset.sha256,'selected_audio_stream_index':report['selected_audio_stream_index'],
                'transcript_member':member,'transcript_sha256':selection['expected_transcript_sha256'],
                'source_annotation':annotation,'word_ids':selection['word_ids'],
                'clip_ids':selection['clip_ids']}
            bindings.append(binding)
            for cut in cuts:
                cut_key=(cut['clip_id'],cut['source_in'],cut['source_out'])
                if cut_key in seen_cuts:
                    continue
                seen_cuts.add(cut_key);combined_cuts.append(cut)
                removed_intervals.append({'source_asset_id':asset.asset_id,'source_sha256':asset.sha256,
                    'transcript_member':member,'transcript_sha256':selection['expected_transcript_sha256'],
                    'clip_id':cut['clip_id'],'source_in':cut['source_in'],'source_out':cut['source_out']})
            words_by_id={word['id']:word for word in candidate['selected_words']}
            for mapping in candidate['word_mappings']:
                word_id=mapping['word_id'];clip_id=mapping['clip_id']
                occurrence=(asset.asset_id,word_id,clip_id)
                if occurrence in seen_occurrences:
                    raise VideoEditingError('WORD_EDIT_SOURCE_SELECTION_DUPLICATE')
                seen_occurrences.add(occurrence)
                word=words_by_id.get(word_id)
                if word is None:
                    raise VideoEditingError('WORD_EDIT_SOURCE_SELECTION_INVALID')
                compiled.append({**word,'clip_id':clip_id,'track_id':mapping['track_id'],
                    'qualified_id':asset.asset_id+':'+word_id+':'+clip_id,
                    'transcript_asset_id':asset.asset_id,'source_asset_id':asset.asset_id,
                    'source_sha256':asset.sha256,'transcript_member':member,
                    'transcript_sha256':selection['expected_transcript_sha256'],
                    'selected_audio_stream_index':report['selected_audio_stream_index'],
                    'source_annotation':annotation})
        if not combined_cuts:raise VideoEditingError('WORD_EDIT_SELECTION_INVALID')
        # One operation applies all selected source intervals to the same base
        # revision. Per-source candidates above are immutable calculations only.
        preview=timeline.cut_source_intervals(combined_cuts,synchronize=synchronize)
        identity_payload={'project_id':project_id,'parent_sha256':record['sha256'],
            'timeline':timeline.to_dict(),'source_selections':normalized,'synchronize':synchronize}
        identity=hashlib.sha256(json.dumps(identity_payload,ensure_ascii=False,allow_nan=False,
            sort_keys=True,separators=(',',':')).encode()).hexdigest()[:20]
        mappings=[]
        for candidate,binding in zip(source_candidates,bindings):
            for mapping in candidate['word_mappings']:
                mappings.append({**mapping,**binding,
                    'qualified_id':binding['source_asset_id']+':'+mapping['word_id']+':'+mapping['clip_id']})

    _,_,current,_=owner._verified_content_project(project_id,actor=actor,**scope)
    if current['sha256']!=record['sha256']:raise VideoEditingError('WORD_EDIT_PROJECT_CHANGED')
    selected_clip_ids={cut['clip_id'] for cut in combined_cuts}
    affected_intervals=[(Fraction(item['timeline_start_exact']['numerator'],item['timeline_start_exact']['denominator']),
                         Fraction(item['timeline_end_exact']['numerator'],item['timeline_end_exact']['denominator']))
                        for item in mappings]
    affected_clips=[];affected_captions=[]
    for track in timeline.tracks:
        for clip in track.clips:
            begin=Fraction(str(clip.timeline_start))
            end=begin+(Fraction(str(clip.source_out))-Fraction(str(clip.source_in)))/Fraction(str(clip.playback_rate))
            if (synchronize or clip.clip_id in selected_clip_ids) and any(begin<right and end>left for left,right in affected_intervals):
                affected_clips.append(clip.clip_id)
    if synchronize:
        for overlay in timeline.overlays:
            begin=Fraction(str(overlay.start_sec));end=Fraction(str(overlay.end_sec))
            if any(begin<right and end>left for left,right in affected_intervals):affected_captions.append(overlay.overlay_id)
    cuts_identity=[{'clip_id':item['clip_id'],'source_in':item['source_in'],'source_out':item['source_out']}
                   for item in combined_cuts]
    decision={'source_clip_ref':combined_cuts[0]['clip_id'],'in_sec':None,'out_sec':None,
        'operation':'word_cut','reason':'用户明确选择多个来源中的已计时词和片段；词界仍需试听审核',
        'confidence':0,'narrative_beat':'跨素材词级剪辑预览',
        'metadata':{'cuts':cuts_identity,'synchronize':synchronize,
                    'source_bindings':bindings}}
    single=len({item['source_asset_id'] for item in bindings})==1
    return {'state':'candidate','edit_kind':'cut_original',
        'edl':{'candidate_id':'EDL-words-'+identity,'decisions':[decision]},
        'removed_source_intervals':removed_intervals,
        'selected_words':compiled,'word_mappings':mappings,'transcript_bindings':bindings,
        'source_selections':normalized,'affected_clip_ids':affected_clips,
        'affected_caption_ids':affected_captions,'preview_timeline':preview.to_dict(),
        'synchronize':synchronize,'source_sha256':bindings[0]['source_sha256'] if single else None,
        'source_sha256s':[item['source_sha256'] for item in bindings],
        'transcript_artifact_id':project_id,
        'transcript_sha256':bindings[0]['transcript_sha256'] if single else None,
        'transcript_sha256s':[item['transcript_sha256'] for item in bindings],
        'timestamp_origin':bindings[0]['source_annotation'] if single else 'MULTI_SOURCE_ANNOTATIONS',
        'boundary_rounding_seconds':0,'human_alignment_accuracy':'NOT_VERIFIED',
        'requires_user_review':True,'automatic_application':False,
        'original_media_modified':False,'transcript_text_modified':False,'redub_performed':False,
        'parent_artifact_id':project_id,'parent_sha256':record['sha256'],
        'parent_timeline_version':timeline.version}


def project_transcripts_read(project_id, *, actor, scope, source_artifact_refs,
                            offset=0, limit=500):
    """Read the version-bound word projection used to prepare source selections.

    This is a read path over the existing immutable content-project package. It
    reauthorizes the project and every source, and returns source-local word ids
    alongside the source/clip bindings needed by the existing edit owner.
    """
    import zipfile
    import shared_artifacts as owner
    from .video_editing import Timeline

    if (type(offset) is not int or not 0 <= offset <= 10000000
            or type(limit) is not int or not 1 <= limit <= 2000
            or type(source_artifact_refs) is not list or not source_artifact_refs
            or any(type(value) is not str for value in source_artifact_refs)
            or len(set(source_artifact_refs)) != len(source_artifact_refs)):
        raise VideoEditingError('PROJECT_TRANSCRIPTION_READ_OPTIONS_INVALID')
    project, render, record, path = owner._verified_content_project(project_id, actor=actor, **scope)
    refs = project.get('source_artifact_refs', [])
    if not refs or set(refs) != set(source_artifact_refs):
        raise VideoEditingError('WORD_EDIT_SOURCE_SCOPE_MISMATCH')
    manifest = project.get('delivery_manifest')
    if type(manifest) is not dict:
        raise VideoEditingError('WORD_EDIT_PROJECT_PACKAGE_INVALID')
    try:
        with owner.resolve_content_source_assets(refs, actor=actor, **scope) as resolved:
            timeline = Timeline.from_dict(project['timeline'], assets=[item['asset'] for item in resolved])
            sources_by_asset = {item['asset'].asset_id: item for item in resolved}
            clips_by_id = {clip.clip_id: clip for track in timeline.tracks for clip in track.clips}
            member = 'transcript-timeline.json'
            entry = manifest.get(member)
            if entry is None:
                report = None
                raw = None
            else:
                with zipfile.ZipFile(path) as package:
                    info = package.getinfo(member)
                    if (type(entry) is not dict or type(entry.get('sha256')) is not str
                            or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256'])
                            or type(entry.get('size_bytes')) is not int or entry['size_bytes'] != info.file_size):
                        raise VideoEditingError('WORD_EDIT_PROJECT_PACKAGE_INVALID')
                    raw = package.read(member)
                if hashlib.sha256(raw).hexdigest() != entry['sha256']:
                    raise VideoEditingError('WORD_EDIT_TRANSCRIPT_HASH_MISMATCH')
                report = json.loads(raw)
                if (type(report) is not dict or report.get('schema') != 'timeline-transcription:v2'
                        or report.get('timeline_version') != timeline.version
                        or report.get('timeline_sha256') != hashlib.sha256(json.dumps(
                            timeline.to_dict(), ensure_ascii=False, allow_nan=False, sort_keys=True,
                            separators=(',', ':')).encode()).hexdigest()
                        or report.get('rendered_sha256') != (None if render.get('state') == 'not_rendered'
                            else render.get('media_sha256'))
                        or report.get('render_binding') != ('PROJECT_DRAFT_NOT_RENDERED'
                            if render.get('state') == 'not_rendered' else 'CURRENT_RENDER')):
                    raise VideoEditingError('CONTENT_TRANSCRIPT_PROJECT_BINDING_CHANGED')

            if report is None:
                result = {'state': 'not_available', 'reason': 'PROJECT_TRANSCRIPT_NOT_SAVED',
                    'project_artifact_id': project_id, 'project_sha256': record['sha256'],
                    'timeline_version': timeline.version, 'sources': [
                        {'source_artifact_ref': item['artifact_ref'], 'source_asset_id': item['asset'].asset_id,
                         'source_sha256': item['asset'].sha256, 'state': 'NOT_AVAILABLE',
                         'reason': 'SOURCE_TRANSCRIPT_NOT_SAVED'} for item in resolved],
                    'words': [], 'cues': [], 'word_count': 0, 'cue_count': 0,
                    'offset': offset, 'limit': limit, 'word_has_more': False, 'cue_has_more': False,
                    'has_more': False, 'next_offset': None}
            else:
                source_bindings = {}
                for source in report.get('sources', []):
                    source_asset_id = source.get('source_asset_id')
                    resolved_source = sources_by_asset.get(source_asset_id)
                    if (resolved_source is None or source.get('source_sha256') != resolved_source['asset'].sha256
                            or source.get('source_artifact_ref') != resolved_source['artifact_ref']):
                        raise VideoEditingError('CONTENT_TRANSCRIPT_SOURCE_MISMATCH')
                    original_member = 'transcription-' + source_asset_id + '.json'
                    original_entry = manifest.get(original_member)
                    original_digest = source.get('original_transcription_sha256')
                    if source.get('state') == 'AVAILABLE':
                        if (type(original_entry) is not dict or type(original_digest) is not str
                                or original_entry.get('sha256') != original_digest
                                or not re.fullmatch(r'[0-9a-f]{64}', original_digest)):
                            raise VideoEditingError('CONTENT_TRANSCRIPT_SOURCE_MISMATCH')
                    source_bindings[source_asset_id] = {
                        'transcript_asset_id': source_asset_id,
                        'expected_transcript_sha256': original_digest,
                        'transcript_member': original_member,
                        'transcript_revision_member': source.get('member'),
                        'source_artifact_ref': resolved_source['artifact_ref'],
                        'source_sha256': resolved_source['asset'].sha256,
                        'selected_audio_stream_index': source.get('selected_audio_stream_index'),
                        'source_annotation': source.get('source_annotation'),
                        'state': source.get('state'), 'reason': source.get('reason'),
                    }
                all_words = report.get('words')
                all_cues = report.get('cues')
                if type(all_words) is not list or type(all_cues) is not list:
                    raise VideoEditingError('CONTENT_TRANSCRIPT_PROJECT_BINDING_CHANGED')
                total = len(all_words)
                page = []
                for item in all_words[offset:offset + limit]:
                    asset_id = item.get('source_asset_id')
                    binding = source_bindings.get(asset_id)
                    word_id = item.get('source_word_id')
                    clip_id = item.get('clip_id')
                    clip = clips_by_id.get(clip_id) if type(clip_id) is str else None
                    if (binding is None or binding.get('state') != 'AVAILABLE'
                            or type(word_id) is not str or not word_id
                            or clip is None or clip.media_asset_id != asset_id):
                        raise VideoEditingError('CONTENT_TRANSCRIPT_PROJECT_BINDING_CHANGED')
                    page.append({**item, **binding, 'word_id': word_id,
                        'qualified_id': asset_id + ':' + word_id + ':' + clip_id,
                        'word_selection_basis': 'ORIGINAL_SOURCE_WORD_TIMES'})
                cues = all_cues[offset:offset + limit]
                word_has_more = offset + len(page) < total
                cue_has_more = offset + len(cues) < len(all_cues)
                result = {'state': report.get('state'), 'project_artifact_id': project_id,
                    'project_sha256': record['sha256'], 'timeline_version': timeline.version,
                    'timeline_sha256': report['timeline_sha256'], 'rendered_sha256': report['rendered_sha256'],
                    'time_basis': report.get('time_basis'), 'source_selection': report.get('source_selection'),
                    'complete_mix_transcription': report.get('complete_mix_transcription'),
                    'review_state': report.get('review_state'), 'human_alignment': report.get('human_alignment'),
                    'new_model_execution': report.get('new_model_execution'),
                    'sources': list(source_bindings.values()), 'words': page, 'cues': cues,
                    'word_count': total, 'cue_count': len(all_cues), 'offset': offset, 'limit': limit,
                    'word_has_more': word_has_more, 'cue_has_more': cue_has_more,
                    'has_more': word_has_more or cue_has_more,
                    'next_offset': offset + limit if word_has_more or cue_has_more else None}
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        raise VideoEditingError('WORD_EDIT_PROJECT_PACKAGE_INVALID') from exc

    _, _, current, _ = owner._verified_content_project(project_id, actor=actor, **scope)
    if current['sha256'] != record['sha256']:
        raise VideoEditingError('WORD_EDIT_PROJECT_CHANGED')
    return result
