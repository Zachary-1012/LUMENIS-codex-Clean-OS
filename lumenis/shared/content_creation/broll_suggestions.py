"""Explainable local-asset keyword candidates and explicit ripple-insert previews.

The caller resolves current source access. Descriptions are user annotations, not
visual understanding or copyright grants. No network and no persistence.
"""
import hashlib,json,math,re,unicodedata
from collections import Counter
from .video_editing import VideoEditingError,fingerprint_local_media


def _text(value,limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or any(unicodedata.category(c).startswith('C') and c not in '\n\t' for c in value):
        raise VideoEditingError('BROLL_TEXT_INVALID')
    return value


def _terms(value):
    words=re.findall(r'[a-z0-9]+',value.lower())
    for run in re.findall(r'[\u3400-\u9fff]+',value):
        words.extend(run[i:i+2] for i in range(len(run)-1))
        if len(run)==1:words.append(run)
    return Counter(words)


def suggest_broll(assets,*,transcript,descriptions,limit=10,check_cancel=None):
    from shared_artifacts import validate_local_asset
    transcript=_text(transcript,20000)
    if type(limit) is not int or not 1<=limit<=20:raise VideoEditingError('BROLL_LIMIT_INVALID')
    if not 1<=len(assets)<=64 or not isinstance(descriptions,dict):raise VideoEditingError('BROLL_ASSETS_INVALID')
    ids={asset.asset_id for asset in assets}
    if len(ids)!=len(assets) or set(descriptions)-ids:raise VideoEditingError('BROLL_SOURCE_SCOPE_MISMATCH')
    query=_terms(transcript);ranked=[]
    for asset in assets:
        if check_cancel:check_cancel()
        asset.validate();path=validate_local_asset(asset.path)
        if fingerprint_local_media(str(path)).sha256!=asset.sha256:raise VideoEditingError('SOURCE_MEDIA_CHANGED')
        description=_text(descriptions.get(asset.asset_id,asset.filename),2000)
        if not asset.has_video:continue
        terms=_terms(description);shared=sorted(set(query)&set(terms))
        score=sum(query[w]*terms[w] for w in shared)/max(1,math.sqrt(sum(v*v for v in query.values())*sum(v*v for v in terms.values())))
        if shared:ranked.append({'asset_id':asset.asset_id,'source_sha256':asset.sha256,'description':description,
            'similarity':round(score,8),'matching_terms':shared,'duration_sec':asset.duration_sec,
            'rights_state':'unknown_not_a_license','annotation_origin':'user_supplied_not_visually_verified'})
    ranked.sort(key=lambda row:(-row['similarity'],row['asset_id']))
    return {'method':'character_bigram_word_cosine_v1','semantic_understanding':False,'external_fetch':False,
            'automatic_insertion':False,'review_required':True,'candidates':ranked[:limit],
            'input_hash':hashlib.sha256(json.dumps({'transcript':transcript,'descriptions':descriptions,'sources':[(a.asset_id,a.sha256) for a in assets]},ensure_ascii=False,sort_keys=True).encode()).hexdigest()}


def prepare_broll_insertion(timeline,*,selected_asset_id,at_sec,source_in,source_out):
    """Return a new unsaved Timeline, preserving its parent; export still needs approval."""
    timeline.validate()
    for value in (at_sec,source_in,source_out):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise VideoEditingError('BROLL_RANGE_INVALID')
    tracks=[track for track in timeline.tracks if track.kind=='video']
    if len(tracks)!=1 or any(track.clips for track in timeline.tracks if track.kind!='video') or timeline.overlays or timeline.transitions:
        raise VideoEditingError('BROLL_INSERT_REQUIRES_UNADORNED_SINGLE_VIDEO_TRACK')
    track=tracks[0];duration=max((c.timeline_start+c.duration_sec for c in track.clips),default=0)
    if not 0<=at_sec<=duration:raise VideoEditingError('BROLL_INSERT_POSITION_INVALID')
    selected=next((a for a in timeline.assets if a.asset_id==selected_asset_id),None)
    if selected is None or not selected.has_video:raise VideoEditingError('BROLL_SOURCE_SCOPE_MISMATCH')
    if not 0<=source_in<source_out<=selected.duration_sec or source_out-source_in<1/30:raise VideoEditingError('BROLL_RANGE_INVALID')
    candidate=timeline;index=len(track.clips)
    for i,clip in enumerate(track.clips):
        if abs(at_sec-clip.timeline_start)<1e-6:index=i;break
        if clip.timeline_start<at_sec<clip.timeline_start+clip.duration_sec:
            if min(at_sec-clip.timeline_start,clip.timeline_start+clip.duration_sec-at_sec)<1/30:raise VideoEditingError('BROLL_INSERT_TOO_CLOSE_TO_BOUNDARY')
            candidate=candidate.split(clip.clip_id,at_sec=clip.source_in+at_sec-clip.timeline_start);index=i+1;break
    candidate=candidate.add_clip(selected_asset_id,track_id=track.track_id,source_in=source_in,source_out=source_out,audio_role='muted',purpose='User-selected B-roll ripple insertion')
    new_clip=next(t for t in candidate.tracks if t.track_id==track.track_id).clips[-1]
    candidate=candidate.reorder(new_clip.clip_id,new_index=index)
    return {'state':'unsaved_insertion_preview','operation':'muted_video_ripple_insert','requires_explicit_export_confirmation':True,
            'parent_version':timeline.version,'timeline':candidate.to_dict(),'inserted_clip_id':new_clip.clip_id,
            'duration_added_sec':source_out-source_in,'rights_state':'unknown_not_a_license',
            'note':'Original clips and their original audio move together; this inserts duration rather than covering existing narration.'}
