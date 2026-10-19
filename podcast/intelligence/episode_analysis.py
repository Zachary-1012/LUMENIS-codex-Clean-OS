"""Scoped media-derived podcast metrics; annotations never establish external facts."""
from datetime import datetime,timezone
import hashlib,json,tempfile,time,uuid,wave
from pathlib import Path
from lumenis.shared.content_creation import rendering
from lumenis.shared.content_creation.video_editing import VideoEditingError,MediaAsset,MEDIA_INPUT_DEMUXERS
from lumenis.shared.content_creation.audio_visuals import _source_unchanged,_check

PIPELINE_VERSION='lumenis.podcast-analysis/v1'
NODE_TYPES={'story','conflict','reveal','emotion_peak','insight_peak','quote','problem'}

def build_episode_analysis_files(asset,*,timeline_version,expected_timeline_version,nodes=None,check_cancel=None):
    from shared_artifacts import validate_local_asset,_ffmpeg_path
    started=datetime.now(timezone.utc).isoformat();clock=time.monotonic();run_id='podcast-run-'+uuid.uuid4().hex
    _check(check_cancel)
    if not isinstance(asset,MediaAsset) or asset.audio_stream_count!=1 or not 0<asset.duration_sec<=600:
        raise VideoEditingError('PODCAST_ANALYSIS_SINGLE_AUDIO_MAX_600_SECONDS')
    if type(timeline_version) is not int or timeline_version!=expected_timeline_version:
        raise VideoEditingError('PODCAST_ANALYSIS_TIMELINE_VERSION_MISMATCH')
    if nodes is not None and (not isinstance(nodes,list) or len(nodes)>1000):
        raise VideoEditingError('PODCAST_ANALYSIS_NODES_INVALID')
    validate_local_asset(asset.path);_source_unchanged(asset,check_cancel)
    with tempfile.TemporaryDirectory(prefix='lumenis-podcast-metrics-') as directory:
        target=Path(directory)/'decoded.wav'
        rendering._run([_ffmpeg_path(),'-v','error','-xerror','-nostdin','-n','-protocol_whitelist','file',
            '-format_whitelist',MEDIA_INPUT_DEMUXERS,'-i',asset.path,'-map','0:a:0','-ar','16000','-ac','1','-c:a','pcm_s16le','-fs','20000000',str(target)],
            cwd=Path(directory),timeout=120,check_continue=check_cancel)
        with wave.open(str(target),'rb') as audio:
            if (audio.getnchannels(),audio.getsampwidth(),audio.getframerate())!=(1,2,16000):
                raise VideoEditingError('PODCAST_ANALYSIS_PCM_FORMAT_INVALID')
            count=0
            while True:
                _check(check_cancel);chunk=audio.readframes(16000)
                if not chunk:break
                count+=len(chunk)//2
            duration=count/audio.getframerate()
        if not 0<duration<=600 or abs(duration-asset.duration_sec)>.05:
            raise VideoEditingError('PODCAST_ANALYSIS_FULL_DECODE_MISMATCH')
    identifiers=set()
    for node in nodes or []:
        _check(check_cancel)
        if (not isinstance(node,dict) or set(node)!={'node_id','node_type','start_sec','end_sec'}
                or not isinstance(node['node_id'],str) or not 1<=len(node['node_id'])<=80
                or any(ord(c)<32 for c in node['node_id']) or node['node_id'] in identifiers
                or not isinstance(node['node_type'],str) or node['node_type'] not in NODE_TYPES
                or any(type(node[k]) not in (int,float) for k in ('start_sec','end_sec'))
                or not 0<=node['start_sec']<node['end_sec']<=duration):
            raise VideoEditingError('PODCAST_ANALYSIS_NODES_INVALID')
        identifiers.add(node['node_id'])
    _source_unchanged(asset,check_cancel)
    metrics={}
    for name,kind in [('story_node_density',None),('emotion_peak_density','emotion_peak'),('insight_density','insight_peak')]:
        count=None if nodes is None else sum(1 for n in nodes if kind is None or n['node_type']==kind)
        metrics[name]={'value':None if count is None else count/(duration/60),'unit':'nodes_per_minute',
                       'count':count,'state':'missing' if count is None else 'derived_from_user_annotation',
                       'definition':'all annotated story nodes' if kind is None else 'annotated '+kind+' nodes'}
    for name in ('question_quality_score','interview_yield','interview_to_ip_conversion','content_asset_reuse_rate','runtime_retention_curve','platform_translation_delta'):
        metrics[name]={'value':None,'state':'missing','reason':'no_verified_observation_or_assessment_supplied'}
    inputs={'source_sha256':asset.sha256,'timeline_version':timeline_version,'nodes':nodes}
    report={'schema':PIPELINE_VERSION,'run':{'run_id':run_id,'pipeline_version':PIPELINE_VERSION,
        'model_name':None,'model_version':None,'prompt_version':None,'input_hash':hashlib.sha256(json.dumps(inputs,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest(),
        'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),'duration_ms':round((time.monotonic()-clock)*1000,3),
        'status':'completed','evidence_ids':[],'error_class':None,'inference_performed':False},
        **inputs,'decoded_duration_seconds':duration,'annotation_origin':'USER_ANNOTATION','metrics':metrics,
        'authoritative':False,'learning_promoted':False,'published':False,'platform':None}
    _check(check_cancel)
    return {'files':{'podcast-analysis.json':json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False).encode()},'report':report}
