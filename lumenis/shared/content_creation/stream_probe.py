"""Real bounded ffprobe metadata and timestamp observations, without CFR guesses."""
import json
import tempfile
import math
from fractions import Fraction
from pathlib import Path
from .video_editing import fingerprint_local_media,VideoEditingError


def probe_source_streams(asset,*,analyze_timing=False,check_cancel=None):
    from .rendering import _ffprobe_path,_run,MEDIA_INPUT_DEMUXERS
    from shared_artifacts import validate_local_asset
    if type(analyze_timing) is not bool:raise VideoEditingError('SOURCE_PROBE_OPTIONS_INVALID')
    asset.validate();path=validate_local_asset(asset.path)
    def verify():
        if check_cancel:check_cancel()
        if fingerprint_local_media(str(path)).to_dict()!=asset.to_dict():raise VideoEditingError('SOURCE_MEDIA_CHANGED')
    verify();probe=_ffprobe_path()
    if not probe:raise VideoEditingError('MEDIA_RENDER_TOOLS_UNAVAILABLE')
    command=[probe,'-v','error','-protocol_whitelist','file','-format_whitelist',MEDIA_INPUT_DEMUXERS]
    def run_json(arguments,limit):
        with tempfile.TemporaryDirectory(prefix="source-probe-") as temporary:
            output=Path(temporary)/"probe.json"
            _run(command+arguments+["-of","json","-o",str(output),str(path)],cwd=Path(temporary),timeout=180,check_continue=check_cancel)
            if not output.is_file() or output.stat().st_size>limit:raise VideoEditingError("SOURCE_PROBE_RESULT_TOO_LARGE")
            return output.read_text(encoding="utf-8")
    raw=run_json(['-show_entries','stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,time_base,start_time,duration,sample_rate,channels:stream_tags=timecode:format=duration,format_name:format_tags=timecode'],1024*1024)
    try:details=json.loads(raw)
    except (TypeError,ValueError) as exc:raise VideoEditingError('SOURCE_PROBE_INVALID') from exc
    if not isinstance(details.get('streams'),list) or len(details['streams'])>128:raise VideoEditingError('SOURCE_PROBE_INVALID')
    timing={'state':'not_analyzed','cfr_verified':False,'reason':'declared_frame_rates_do_not_prove_frame_timing'}
    videos=[stream for stream in details['streams'] if stream.get('codec_type')=='video']
    if analyze_timing and videos:
        raw=run_json(['-select_streams','v:0','-read_intervals','%+180','-show_entries','frame=best_effort_timestamp'],8*1024*1024)
        try:
            frames=json.loads(raw)['frames'];ticks=[int(frame['best_effort_timestamp']) for frame in frames]
            if not 2<=len(ticks)<=108000:raise ValueError('frame count')
            timebase=Fraction(videos[0]['time_base']);deltas=[b-a for a,b in zip(ticks,ticks[1:])]
            if min(deltas)<=0 or timebase<=0:raise ValueError('timestamp order')
            declared_duration=float(videos[0].get("duration",asset.duration_sec))
            observed_duration=float((ticks[-1]-ticks[0]+deltas[-1])*timebase)
            tolerance=max(.05,2*float(max(deltas)*timebase))
            full=(asset.duration_sec<=180 and math.isfinite(declared_duration) and declared_duration>0
                  and abs(observed_duration-declared_duration)<=tolerance)
            constant=len(set(deltas))==1
            timing={'state':'measured','selected_video_stream_ordinal':0,'frames_observed':len(ticks),
                    'coverage':'full_source' if full else ('first_180_seconds_only' if asset.duration_sec>180 else 'duration_coverage_unverified'),'global_classification':
                    ('constant_frame_intervals' if constant else 'variable_frame_intervals') if full else 'unknown_partial_scan',
                    'observed_constant_intervals':constant,'cfr_verified':full and constant,
                    'declared_video_duration_sec':declared_duration,'observed_video_duration_sec':observed_duration,
                    'time_base':str(timebase),'minimum_delta_ticks':min(deltas),'maximum_delta_ticks':max(deltas),
                    'first_timestamp_seconds':float(ticks[0]*timebase),'last_timestamp_seconds':float(ticks[-1]*timebase)}
        except (ValueError,TypeError,KeyError,ZeroDivisionError) as exc:
            raise VideoEditingError('SOURCE_TIMING_UNVERIFIABLE') from exc
    verify()
    return {'source_asset_id':asset.asset_id,'source_sha256':asset.sha256,'streams':details['streams'],
            'format':details.get('format',{}),'frame_timing':timing,'method':'ffprobe_actual_streams_and_optional_frame_pts'}
