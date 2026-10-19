"""Read-only, measured edit candidates; every application uses canonical EDL confirmation."""
import hashlib,json
from pathlib import Path
from .video_editing import VideoEditingError


def silence_edl_candidate(timeline,proposal):
    timeline.validate()
    tracks=[track for track in timeline.tracks if track.clips]
    if len(tracks)!=1 or len(tracks[0].clips)!=1 or timeline.overlays or timeline.transitions:
        raise VideoEditingError('SILENCE_EDL_REQUIRES_SINGLE_UNADORNED_CLIP')
    clip=tracks[0].clips[0];asset=next(asset for asset in timeline.assets if asset.asset_id==clip.media_asset_id)
    # WAV has sample-zero origin. Other containers require verified A/V timestamp
    # mapping; do not assume stream elapsed time equals container source time.
    if asset.has_video or Path(asset.path).suffix.lower()!='.wav' or clip.timeline_start!=0:
        raise VideoEditingError('SILENCE_EDL_REQUIRES_ZERO_ORIGIN_WAV')
    if proposal.get('source_sha256')!=asset.sha256 or proposal.get('audio_stream_index')!=(clip.audio_stream_index or 0):
        raise VideoEditingError('SILENCE_EDL_SOURCE_MISMATCH')
    intervals=[]
    for item in proposal.get('candidates',[]):
        a=max(clip.source_in,item['suggested_remove_start_sec']);b=min(clip.source_out,item['suggested_remove_end_sec'])
        if b-a>=1/30 and a-clip.source_in>=1/30 and clip.source_out-b>=1/30:intervals.append((a,b))
    intervals.sort()
    if len(intervals)>40 or any(intervals[i][0]<intervals[i-1][1]+1/30 for i in range(1,len(intervals))):
        raise VideoEditingError('SILENCE_EDL_CANDIDATE_LIMIT_OR_OVERLAP')
    decisions=[];current=clip.clip_id
    def add(ref,operation,a=None,b=None,metadata=None):
        decisions.append({'source_clip_ref':ref,'in_sec':a,'out_sec':b,'operation':operation,
            'reason':'FFmpeg测得静音，保留边距；语义与词界需人工复核','confidence':0,
            'narrative_beat':'用户确认停顿是否可删除','metadata':metadata or {}})
    for a,b in intervals:
        add(current,'split',a);current+='-b'
        add(current,'split',b);add(current+'-a','delete',metadata={'ripple':True});current+='-b'
    identity=hashlib.sha256(json.dumps({'timeline':timeline.to_dict(),'intervals':intervals},sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
    return {'state':'candidate' if decisions else 'no_candidate',
            'edl':{'candidate_id':'EDL-silence-'+identity,'decisions':decisions} if decisions else None,
            'removed_source_intervals':intervals,'requires_user_review':True,'automatic_application':False,
            'word_alignment_verified':False,'semantic_confidence_assessed':False,
            'source_sha256':asset.sha256,'scope':'one_audio_WAV_clip_no_overlays_or_transitions'}
