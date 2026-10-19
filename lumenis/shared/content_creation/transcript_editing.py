"""Explicit word selections become immutable EDL candidates, never automatic edits."""
import hashlib,json,math,re,unicodedata
from pathlib import Path
from .video_editing import VideoEditingError


def _word_edit_context(timeline, transcript):
    timeline.validate()
    tracks=[track for track in timeline.tracks if track.clips]
    if len(tracks)!=1 or len(tracks[0].clips)!=1 or timeline.overlays or timeline.transitions:
        raise VideoEditingError('WORD_EDIT_REQUIRES_SINGLE_UNADORNED_CLIP')
    clip=tracks[0].clips[0];asset=next(a for a in timeline.assets if a.asset_id==clip.media_asset_id)
    if asset.has_video or Path(asset.path).suffix.lower()!='.wav' or clip.timeline_start!=0:
        raise VideoEditingError('WORD_EDIT_REQUIRES_ZERO_ORIGIN_WAV')
    if transcript.get('original_source_sha256')!=asset.sha256 or transcript.get('selected_audio_stream_index')!=(clip.audio_stream_index or 0):
        raise VideoEditingError('WORD_EDIT_SOURCE_MISMATCH')
    return clip,asset


def _index_words(transcript, duration):
    indexed={};previous=0
    for segment in transcript.get('transcript',{}).get('segments',[]):
        for index,word in enumerate(segment.get('words',[])):
            start,end=word.get('start'),word.get('end')
            if any(type(x) not in (int,float) or not math.isfinite(x) for x in (start,end)) or not previous<=start<end<=duration:
                raise VideoEditingError('WORD_EDIT_TIMESTAMPS_INVALID')
            identity=f"{segment['id']}:{index}"
            if identity in indexed:raise VideoEditingError('WORD_EDIT_TIMESTAMPS_INVALID')
            indexed[identity]=(start,end,word.get('word',''));previous=end
    return indexed


def word_deletion_candidate(timeline, transcript, *, word_ids, transcript_artifact_id, transcript_sha256):
    clip,asset=_word_edit_context(timeline,transcript)
    if not isinstance(word_ids,list) or not 1<=len(word_ids)<=100 or any(not isinstance(x,str) for x in word_ids) or len(set(word_ids))!=len(word_ids):
        raise VideoEditingError('WORD_EDIT_SELECTION_INVALID')
    indexed=_index_words(transcript,asset.duration_sec)
    if not indexed or any(key not in indexed for key in word_ids):raise VideoEditingError('WORD_EDIT_WORD_ID_UNKNOWN')
    intervals=[]
    for start,end,_ in sorted(indexed[key] for key in word_ids):
        if not clip.source_in<=start<end<=clip.source_out:raise VideoEditingError('WORD_EDIT_OUTSIDE_CLIP')
        if intervals and abs(start-intervals[-1][1])<1e-8:intervals[-1]=(intervals[-1][0],end)
        else:intervals.append((start,end))
    decisions=[];current=clip.clip_id;cursor=clip.source_in
    def add(ref,operation,start=None,end=None):
        decisions.append({'source_clip_ref':ref,'in_sec':start,'out_sec':end,'operation':operation,
            'reason':'用户明确选择原转写词ID；模型词界需人工听审','confidence':0,'narrative_beat':'词级删选预览',
            'metadata':{'ripple':True} if operation=='delete' else {}})
    # Timeline split resolution is currently 1/30 sec. Reject shorter surviving
    # or deleted spans rather than silently deleting adjacent words or rounding.
    minimum=1/30
    for start,end in intervals:
        if end-start<minimum:raise VideoEditingError('WORD_EDIT_INTERVAL_TOO_SHORT')
        if start>cursor:
            if start-cursor<minimum:raise VideoEditingError('WORD_EDIT_REMAINDER_TOO_SHORT')
            add(current,'split',start);current+='-b'
        if end<clip.source_out:
            if clip.source_out-end<minimum:raise VideoEditingError('WORD_EDIT_REMAINDER_TOO_SHORT')
            add(current,'split',end);add(current+'-a','delete');current+='-b'
        else:add(current,'delete')
        cursor=end
    if len(decisions)>128:raise VideoEditingError('WORD_EDIT_DECISION_LIMIT')
    if sum(b-a for a,b in intervals)>=clip.duration_sec-1e-8:raise VideoEditingError('WORD_EDIT_WOULD_REMOVE_ALL_AUDIO')
    binding={'timeline':timeline.to_dict(),'transcript_artifact_id':transcript_artifact_id,'transcript_sha256':transcript_sha256,'word_ids':word_ids}
    identity=hashlib.sha256(json.dumps(binding,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
    return {'state':'candidate','edl':{'candidate_id':'EDL-words-'+identity,'decisions':decisions},'removed_source_intervals':intervals,
            'selected_words':[{'id':key,'text':indexed[key][2],'start':indexed[key][0],'end':indexed[key][1]} for key in word_ids],
            'source_sha256':asset.sha256,'transcript_artifact_id':transcript_artifact_id,'transcript_sha256':transcript_sha256,
            'timestamp_origin':'model_estimated_unreviewed_derivative','boundary_rounding_seconds':0,
            'human_alignment_accuracy':'NOT_VERIFIED','requires_user_review':True,'automatic_application':False}


def _literal_token(value):
    if not isinstance(value,str) or len(value)>256 or any(ord(c)<32 for c in value):
        raise VideoEditingError('WORD_EDIT_FILLER_TERM_INVALID')
    value=unicodedata.normalize('NFKC',value).casefold().strip()
    while value and unicodedata.category(value[0]).startswith('P'):value=value[1:]
    while value and unicodedata.category(value[-1]).startswith('P'):value=value[:-1]
    return value


def filler_word_deletion_candidate(timeline,transcript,*,filler_terms,transcript_artifact_id,transcript_sha256):
    clip,asset=_word_edit_context(timeline,transcript)
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
        start,end,text=indexed[key]
        if clip.source_in<=start<end<=clip.source_out and _literal_token(text) in normalized:
            matches.append(key)
            contexts.append({'word_id':key,'source_start':start,'source_end':end,
                'context':[{'id':k,'text':indexed[k][2],'start':indexed[k][0],'end':indexed[k][1]} for k in ordered[max(0,pos-2):pos+3]]})
    if len(matches)>100:raise VideoEditingError('WORD_EDIT_FILLER_MATCH_LIMIT')
    if not matches:
        result={'state':'no_matches','edl':None,'selected_words':[],'automatic_application':False,
                'transcript_artifact_id':transcript_artifact_id,'transcript_sha256':transcript_sha256,'source_sha256':asset.sha256}
    else:
        result=word_deletion_candidate(timeline,transcript,word_ids=matches,transcript_artifact_id=transcript_artifact_id,transcript_sha256=transcript_sha256)
    return {**result,'filler_terms':filler_terms,'normalized_terms':normalized,'candidate_contexts':contexts,
            'selection_method':'explicit_user_terms_literal_original_asr_token_match',
            'matching_recipe':{'unicode_normalization':'NFKC','unicode_version':unicodedata.unidata_version,'case':'casefold',
                'boundary':'strip_outer_whitespace_and_unicode_punctuation','tokenization':'original_ASR_word_units_no_retokenization_or_substring_matching'},
            'semantic_filler_classification':False,'requires_user_review':True}


def project_word_deletion_candidate(project_id, *, word_ids=None, filler_terms=None, expected_transcript_sha256=None, actor, scope, source_artifact_refs):
    import zipfile
    import shared_artifacts as owner
    from .video_editing import Timeline
    project,_,record,path=owner._verified_content_project(project_id,actor=actor,**scope)
    refs=project.get('source_artifact_refs',[])
    if not refs or set(refs)!=set(source_artifact_refs):raise VideoEditingError('WORD_EDIT_SOURCE_SCOPE_MISMATCH')
    entry=project.get('delivery_manifest',{}).get('transcription.json')
    if not entry:raise VideoEditingError('WORD_EDIT_VERIFIED_TRANSCRIPT_REQUIRED')
    if filler_terms is not None:
        if word_ids is not None or not isinstance(expected_transcript_sha256,str) or not re.fullmatch(r'[0-9a-f]{64}',expected_transcript_sha256):
            raise VideoEditingError('WORD_EDIT_FILLER_BINDING_REQUIRED')
        if expected_transcript_sha256!=entry['sha256']:raise VideoEditingError('WORD_EDIT_TRANSCRIPT_STALE')
    with zipfile.ZipFile(path) as package:data=package.read('transcription.json')
    if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise VideoEditingError('WORD_EDIT_TRANSCRIPT_HASH_MISMATCH')
    transcript=json.loads(data)
    if transcript.get('owner')!='SYSTEM AI Gateway' or transcript.get('source_annotation')!='model_estimated_unreviewed_derivative':
        raise VideoEditingError('WORD_EDIT_TRANSCRIPT_PROVENANCE_INVALID')
    with owner.resolve_content_source_assets(refs,actor=actor,**scope) as sources:
        timeline=Timeline.from_dict(project['timeline'],assets=[item['asset'] for item in sources])
        if filler_terms is not None:
            candidate=filler_word_deletion_candidate(timeline,transcript,filler_terms=filler_terms,transcript_artifact_id=project_id,transcript_sha256=entry['sha256'])
        else:
            candidate=word_deletion_candidate(timeline,transcript,word_ids=word_ids,transcript_artifact_id=project_id,transcript_sha256=entry['sha256'])
    _,_,current,_=owner._verified_content_project(project_id,actor=actor,**scope)
    if current['sha256']!=record['sha256']:raise VideoEditingError('WORD_EDIT_PROJECT_CHANGED')
    return {**candidate,'parent_artifact_id':project_id,'parent_sha256':record['sha256'],'parent_timeline_version':timeline.version}
