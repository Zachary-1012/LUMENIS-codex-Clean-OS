import subprocess
from dataclasses import replace
import pytest
from lumenis.shared.content_creation.video_editing import Timeline,TimelineClip,TimelineTrack,VideoEditingError,fingerprint_local_media
from lumenis.shared.content_creation.timeline_interchange import build_interchange_files,preflight_interchange

@pytest.fixture
def timeline(tmp_path,monkeypatch):
    monkeypatch.setenv('LUMENIS_LOCAL_ASSET_DIR',str(tmp_path))
    p=tmp_path/'owned.mp4'
    subprocess.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','testsrc2=s=160x90:r=30:d=3','-c:v','libx264','-threads','1',str(p)],check=True)
    a=fingerprint_local_media(str(p))
    return Timeline(assets=(a,),tracks=(TimelineTrack('video','video',(TimelineClip('a',a.asset_id,.1,1.1,0),TimelineClip('b',a.asset_id,1.2,2.2,1.5))),),format_ratio='16:9')

def opts(t):return dict(frame_rate='30',media_refs={t.assets[0].asset_id:'source.mp4'},formats=['cmx3600'])

def test_real_cmx_full_pts_and_edl(timeline):
    with pytest.raises(VideoEditingError,match='LOSS_REQUIRES'):build_interchange_files(timeline,**opts(timeline))
    result=build_interchange_files(timeline,allow_loss=True,**opts(timeline))
    text=result['files']['timeline.edl'].decode()
    assert '00:00:00:03 00:00:01:03 00:00:00:00 00:00:01:00' in text
    assert '00:00:01:06 00:00:02:06 00:00:01:15 00:00:02:15' in text
    assert result['report']['preflight'][0]['source_rate_verification']=='FULL_SOURCE_PTS_CFR_ZERO_ORIGIN'
    assert result['report']['preflight'][0]['external_import_frame_rate_required'] is True

@pytest.mark.parametrize('fps',['30000/1001','25',None])
def test_unknown_or_mismatch_blocks(timeline,fps):
    o=opts(timeline);o['frame_rate']=fps
    with pytest.raises(VideoEditingError,match='BLOCKED_OR_UNKNOWN'):build_interchange_files(timeline,allow_loss=True,**o)

def test_subframe_and_multitrack_block(timeline):
    t=replace(timeline,tracks=(replace(timeline.tracks[0],clips=(replace(timeline.tracks[0].clips[0],source_in=.11),)),))
    with pytest.raises(VideoEditingError,match='BLOCKED_OR_UNKNOWN'):build_interchange_files(t,allow_loss=True,**opts(t))
    t=replace(timeline,tracks=timeline.tracks+(replace(timeline.tracks[0],track_id='second',clips=(replace(timeline.tracks[0].clips[0],clip_id='second',track_id='second'),)),))
    with pytest.raises(VideoEditingError,match='BLOCKED_OR_UNKNOWN'):build_interchange_files(t,allow_loss=True,**opts(t))

def test_cancel(timeline):
    def cancel():raise RuntimeError('cancel')
    with pytest.raises(RuntimeError,match='cancel'):build_interchange_files(timeline,allow_loss=True,check_cancel=cancel,**opts(timeline))

def test_embedded_nonzero_timecode_blocks(timeline,tmp_path):
    p=tmp_path/'timecoded.mp4'
    subprocess.run(['ffmpeg','-v','error','-n','-i',timeline.assets[0].path,'-c','copy','-timecode','01:00:00:00',str(p)],check=True)
    a=fingerprint_local_media(str(p));t=replace(timeline,assets=(a,),tracks=(replace(timeline.tracks[0],clips=tuple(replace(c,media_asset_id=a.asset_id) for c in timeline.tracks[0].clips)),))
    report=preflight_interchange(t,format='cmx3600',frame_rate='30',media_refs={a.asset_id:'source.mp4'})
    assert report['status']=='BLOCKED'
    assert any(x['code']=='CMX_NONZERO_OR_DROP_SOURCE_TIMECODE_UNSUPPORTED' for x in report['issues'])
