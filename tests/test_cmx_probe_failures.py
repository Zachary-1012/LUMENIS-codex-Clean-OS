"""CMX preflight recovery preserves cancellation and source integrity boundaries."""
import subprocess
from dataclasses import replace
import pytest
from lumenis.shared.content_creation.video_editing import Timeline, TimelineClip, TimelineTrack, VideoEditingError, fingerprint_local_media
from lumenis.shared.content_creation import timeline_interchange as exchange, stream_probe

@pytest.fixture(scope='module')
def source(tmp_path_factory):
    path=tmp_path_factory.mktemp('cmx-probe-review')/'sample.mp4'
    subprocess.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','testsrc2=s=32x32:r=25:d=1','-c:v','libx264','-threads','1',str(path)],check=True,timeout=20)
    return fingerprint_local_media(str(path))

@pytest.fixture
def timeline(source, monkeypatch):
    monkeypatch.setattr(exchange, '_probe_rates', lambda *args,**kwargs: {})
    return Timeline(assets=(source,),tracks=(TimelineTrack('video','video',(TimelineClip('a',source.asset_id,0,.4,0),TimelineClip('b',source.asset_id,.4,.8,.4))),))

def options(t):
    return dict(frame_rate='25',source_frame_rates={a.asset_id:'25' for a in t.assets},media_refs={a.asset_id:f'{i}.mp4' for i,a in enumerate(t.assets)})

@pytest.mark.parametrize('code', ['MEDIA_RENDER_TOOLS_UNAVAILABLE','MEDIA_RENDER_PROCESS_FAILED','MEDIA_RENDER_FAILED','SOURCE_PROBE_RESULT_TOO_LARGE','SOURCE_PROBE_INVALID','SOURCE_TIMING_UNVERIFIABLE'])
def test_expected_probe_failure_returns_unknown_and_blocks_export(timeline,monkeypatch,code):
    def failed(*args,**kwargs): raise VideoEditingError(code)
    monkeypatch.setattr(stream_probe,'probe_source_streams',failed)
    r=exchange.preflight_interchange(timeline,format='cmx3600',**options(timeline))
    assert r['status']=='UNKNOWN'
    assert {'code':'CMX_SOURCE_TIMING_UNVERIFIABLE','severity':'UNKNOWN','clip_ids':['a','b']} in r['issues']
    assert r['source_rate_verification']!='FULL_SOURCE_PTS_CFR_ZERO_ORIGIN'
    assert any(i['code']=='CMX_OUTPUT_GEOMETRY_NOT_ENCODED' for i in r['issues'])
    with pytest.raises(VideoEditingError,match='INTERCHANGE_PREFLIGHT_BLOCKED_OR_UNKNOWN'):
        exchange.build_interchange_files(timeline,formats=['cmx3600'],allow_loss=True,**options(timeline))

@pytest.mark.parametrize('error',[VideoEditingError('SOURCE_MEDIA_CHANGED'),VideoEditingError('SOURCE_PROBE_OPTIONS_INVALID'),ValueError('unexpected parser bug')])
def test_integrity_and_unexpected_errors_propagate(timeline,monkeypatch,error):
    def failed(*args,**kwargs): raise error
    monkeypatch.setattr(stream_probe,'probe_source_streams',failed)
    with pytest.raises(type(error)) as caught: exchange.preflight_interchange(timeline,format='cmx3600',**options(timeline))
    assert caught.value is error

@pytest.mark.parametrize('error',[RuntimeError('cancel'),VideoEditingError('MEDIA_RENDER_PROCESS_FAILED'),KeyboardInterrupt()])
def test_callback_exception_is_never_reclassified(timeline,monkeypatch,error):
    def cancel(): raise error
    def inspected(*args,check_cancel=None,**kwargs): check_cancel()
    monkeypatch.setattr(stream_probe,'probe_source_streams',inspected)
    with pytest.raises(type(error)) as caught: exchange.preflight_interchange(timeline,format='cmx3600',check_cancel=cancel,**options(timeline))
    assert caught.value is error


def test_remaining_assets_and_editorial_checks_continue(timeline,source,monkeypatch):
    # Same immutable source is sufficient for a second independent clip check.
    t=replace(timeline,tracks=(replace(timeline.tracks[0],clips=(replace(timeline.tracks[0].clips[0],source_in=.01),timeline.tracks[0].clips[1])),))
    def failed(*args,**kwargs): raise VideoEditingError('SOURCE_TIMING_UNVERIFIABLE')
    monkeypatch.setattr(stream_probe,'probe_source_streams',failed)
    r=exchange.preflight_interchange(t,format='cmx3600',**options(t))
    assert r['status']=='BLOCKED'
    assert any(i['code']=='CMX_OFF_FRAME_EDIT_UNSUPPORTED' and i['clip_ids']==['a'] for i in r['issues'])

@pytest.mark.parametrize('mode',['missing_tool','malformed_timestamps'])
def test_actual_probe_failures_are_reported(timeline,source,monkeypatch,mode):
    from pathlib import Path
    from lumenis.shared.content_creation import rendering
    monkeypatch.setenv('LUMENIS_LOCAL_ASSET_DIR',str(Path(source.path).parent))
    if mode=='missing_tool':
        monkeypatch.setattr(rendering,'_ffprobe_path',lambda:None)
    else:
        def run(command,**kwargs):
            output=Path(command[command.index('-o')+1])
            output.write_text('{"frames":[]}' if '-select_streams' in command else '{"streams":[{"codec_type":"video","time_base":"1/25"}],"format":{}}')
        monkeypatch.setattr(rendering,'_run',run)
    r=exchange.preflight_interchange(timeline,format='cmx3600',**options(timeline))
    assert r['status']=='UNKNOWN'
    assert any(i['code']=='CMX_SOURCE_TIMING_UNVERIFIABLE' for i in r['issues'])


def test_later_assets_still_probed(timeline,source,monkeypatch):
    # A second valid fixture asset identity, no bytes accessed by this probe stub.
    other=replace(source,asset_id='MEDIA-'+'b'*16,sha256='b'*64)
    t=replace(timeline,assets=(source,other),tracks=(replace(timeline.tracks[0],clips=(timeline.tracks[0].clips[0],replace(timeline.tracks[0].clips[1],media_asset_id=other.asset_id))),))
    seen=[]
    def probe(asset,**kwargs):
        seen.append(asset.asset_id)
        if asset.asset_id==source.asset_id: raise VideoEditingError('SOURCE_TIMING_UNVERIFIABLE')
        return dict(streams=[dict(tags={'timecode':'01:00:00:00'})],format={},frame_timing=dict(cfr_verified=True,minimum_delta_ticks=1,time_base='1/25',first_timestamp_seconds=0))
    monkeypatch.setattr(stream_probe,'probe_source_streams',probe)
    r=exchange.preflight_interchange(t,format='cmx3600',**options(t))
    assert seen==[source.asset_id,other.asset_id]
    assert {'code':'CMX_SOURCE_TIMING_UNVERIFIABLE','severity':'UNKNOWN','clip_ids':['a']} in r['issues']
    assert {'code':'CMX_NONZERO_OR_DROP_SOURCE_TIMECODE_UNSUPPORTED','severity':'BLOCKED','clip_ids':['b']} in r['issues']
