"""Scoped media-derived podcast metrics; annotations never establish external facts."""
from datetime import datetime,timezone
import hashlib,json,math,subprocess,time,uuid
from threading import Thread
from lumenis.shared.content_creation.video_editing import VideoEditingError,MediaAsset,MEDIA_INPUT_DEMUXERS,MAX_EDIT_TIME_SEC
from lumenis.shared.content_creation.audio_visuals import _source_unchanged,_check

PIPELINE_VERSION='lumenis.podcast-analysis/v2'
NODE_TYPES={'story','conflict','reveal','emotion_peak','insight_peak','quote','problem'}
ANALYSIS_SAMPLE_RATE=16000


def _decode_full_audio_sample_count(asset, *, ffmpeg, check_cancel=None):
    """Decode the complete source to a bounded PCM pipe without a large temp WAV."""
    max_bytes=math.ceil((asset.duration_sec+.1)*ANALYSIS_SAMPLE_RATE*2)
    command=[ffmpeg,'-v','error','-xerror','-nostdin','-threads','1','-protocol_whitelist','file',
        '-format_whitelist',MEDIA_INPUT_DEMUXERS,'-i',asset.path,'-map','0:a:0','-ar',str(ANALYSIS_SAMPLE_RATE),
        '-ac','1','-c:a','pcm_s16le','-f','s16le','pipe:1']
    try:
        process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL,shell=False)
    except OSError as exc:
        raise VideoEditingError('PODCAST_ANALYSIS_DECODE_UNAVAILABLE') from exc
    state={'byte_count':0,'error':None}

    def terminate():
        try:
            if process.poll() is None:
                process.kill()
        except OSError:
            pass

    def consume():
        try:
            while True:
                block=process.stdout.read(1024*1024)
                if not block:break
                state['byte_count']+=len(block)
                if state['byte_count']>max_bytes:
                    state['error']='PODCAST_ANALYSIS_DECODED_SIZE_LIMIT'
                    terminate()
                    break
        except OSError:
            state['error']=state['error'] or 'PODCAST_ANALYSIS_FULL_DECODE_FAILED'
            terminate()

    reader=Thread(target=consume,name='podcast-analysis-pcm-reader',daemon=True)
    reader.start()
    deadline=time.monotonic()+max(120,asset.duration_sec*2)
    cancelled=None;timed_out=False
    while process.poll() is None:
        try:
            _check(check_cancel)
        except BaseException as exc:
            cancelled=exc
            terminate()
            break
        if state['error']:
            terminate()
            break
        if time.monotonic()>=deadline:
            timed_out=True
            terminate()
            break
        time.sleep(.1)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        terminate()
        process.wait()
    reader.join(timeout=10)
    if reader.is_alive():
        if process.stdout:
            process.stdout.close()
        reader.join(timeout=2)
    if process.stdout:
        process.stdout.close()
    if cancelled is not None:
        raise cancelled
    if timed_out:
        raise VideoEditingError('PODCAST_ANALYSIS_DECODE_TIMEOUT')
    if reader.is_alive() or state['error']:
        raise VideoEditingError(state['error'] or 'PODCAST_ANALYSIS_FULL_DECODE_FAILED')
    if process.returncode != 0 or state['byte_count'] <= 0 or state['byte_count'] % 2:
        raise VideoEditingError('PODCAST_ANALYSIS_FULL_DECODE_FAILED')
    return state['byte_count']//2

def build_episode_analysis_files(asset,*,timeline_version,expected_timeline_version,nodes=None,check_cancel=None):
    from shared_artifacts import validate_local_asset,_ffmpeg_path
    started=datetime.now(timezone.utc).isoformat();clock=time.monotonic();run_id='podcast-run-'+uuid.uuid4().hex
    _check(check_cancel)
    if (not isinstance(asset,MediaAsset) or asset.audio_stream_count!=1
            or not 0<asset.duration_sec<=MAX_EDIT_TIME_SEC):
        raise VideoEditingError('PODCAST_ANALYSIS_SINGLE_AUDIO_REQUIRED')
    if type(timeline_version) is not int or timeline_version!=expected_timeline_version:
        raise VideoEditingError('PODCAST_ANALYSIS_TIMELINE_VERSION_MISMATCH')
    if nodes is not None and (not isinstance(nodes,list) or len(nodes)>1000):
        raise VideoEditingError('PODCAST_ANALYSIS_NODES_INVALID')
    validate_local_asset(asset.path);_source_unchanged(asset,check_cancel)
    ffmpeg=_ffmpeg_path()
    if not ffmpeg:
        raise VideoEditingError('MEDIA_RENDER_TOOLS_UNAVAILABLE')
    decoded_sample_count=_decode_full_audio_sample_count(asset,ffmpeg=ffmpeg,check_cancel=check_cancel)
    duration=decoded_sample_count/ANALYSIS_SAMPLE_RATE
    if not 0<duration<=MAX_EDIT_TIME_SEC or abs(duration-asset.duration_sec)>.05:
        raise VideoEditingError('PODCAST_ANALYSIS_FULL_DECODE_MISMATCH')
    _source_unchanged(asset,check_cancel)
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
        node_count=None if nodes is None else sum(1 for n in nodes if kind is None or n['node_type']==kind)
        metrics[name]={'value':None if node_count is None else node_count/(duration/60),'unit':'nodes_per_minute',
                       'count':node_count,'state':'missing' if node_count is None else 'derived_from_user_annotation',
                       'definition':'all annotated story nodes' if kind is None else 'annotated '+kind+' nodes'}
    for name in ('question_quality_score','interview_yield','interview_to_ip_conversion','content_asset_reuse_rate','runtime_retention_curve','platform_translation_delta'):
        metrics[name]={'value':None,'state':'missing','reason':'no_verified_observation_or_assessment_supplied'}
    inputs={'source_sha256':asset.sha256,'timeline_version':timeline_version,'nodes':nodes}
    report={'schema':PIPELINE_VERSION,'run':{'run_id':run_id,'pipeline_version':PIPELINE_VERSION,
        'model_name':None,'model_version':None,'prompt_version':None,'input_hash':hashlib.sha256(json.dumps(inputs,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest(),
        'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),'duration_ms':round((time.monotonic()-clock)*1000,3),
        'status':'completed','evidence_ids':[],'error_class':None,'inference_performed':False},
        **inputs,'decoded_duration_seconds':duration,'decoded_sample_count':decoded_sample_count,
        'decode_method':'ffmpeg_normalized_pcm_stream','decode_sample_rate':ANALYSIS_SAMPLE_RATE,
        'annotation_origin':'USER_ANNOTATION','metrics':metrics,
        'authoritative':False,'learning_promoted':False,'published':False,'platform':None}
    _check(check_cancel)
    return {'files':{'podcast-analysis.json':json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False).encode()},'report':report}
