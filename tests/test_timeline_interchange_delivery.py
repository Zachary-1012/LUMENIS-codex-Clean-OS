"""Real local-media regression; no network/model or rights assertions."""
import json
import shutil
import subprocess
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import pytest
from lumenis.shared.content_creation.video_editing import (Timeline, TimelineClip, TimelineTrack,
    AudioMix, TimedOverlay, Transition, VideoEditingError, fingerprint_local_media)
from lumenis.shared.content_creation.timeline_interchange import (build_interchange_files,
    preflight_interchange, import_interchange)
from lumenis.shared.content_creation.cover_candidates import build_cover_files

@pytest.fixture(scope='module')
def asset(tmp_path_factory):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('real FFmpeg/FFprobe required')
    p = tmp_path_factory.mktemp('exchange')/'sample.mp4'
    subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-f','lavfi','-i',
        'testsrc2=size=160x90:rate=30000/1001','-f','lavfi','-i','sine=frequency=440:sample_rate=48000',
        '-t','4.004','-c:v','libx264','-threads','1','-c:a','aac',str(p)],check=True,timeout=30)
    return fingerprint_local_media(str(p))

@pytest.fixture
def timeline(asset):
    f = Fraction(1001,30000)
    return Timeline(assets=(asset,), tracks=(TimelineTrack('video','video',(
        TimelineClip('a',asset.asset_id,float(3*f),float(33*f),0),
        TimelineClip('b',asset.asset_id,float(40*f),float(70*f),float(45*f)),)),),format_ratio='16:9')


def options(asset):
    return {'frame_rate':'30000/1001','media_refs':{asset.asset_id:'source.mp4'}}

@pytest.mark.parametrize('fmt',['otio','fcpxml'])
def test_ntsc_roundtrip(timeline,asset,fmt):
    data = build_interchange_files(timeline,formats=[fmt],**options(asset))
    assert data['report']['preflight'][0]['status']=='PASS'
    result = import_interchange(data['files']['timeline.'+fmt],format=fmt,assets=(asset,),media_refs=options(asset)['media_refs'])
    for old,new in zip(timeline.tracks[0].clips,result.tracks[0].clips):
        assert old.to_dict()==new.to_dict()
    assert result.format_ratio=='16:9'


def test_official_otio_parser(timeline,asset):
    otio = pytest.importorskip('opentimelineio')
    data=build_interchange_files(timeline,formats=['otio'],**options(asset))
    doc=otio.adapters.read_from_string(data['files']['timeline.otio'].decode(),adapter_name='otio_json')
    assert doc.tracks[0][0].source_range.start_time.value==3
    assert doc.tracks[0][1].duration().value==15
    assert doc.tracks[0][2].source_range.duration.value==30
    assert doc.tracks[0][2].media_reference.target_url=='source.mp4'


def test_multi_track_otio(timeline,asset):
    audio=TimelineTrack('music','bgm',(TimelineClip('m',asset.asset_id,0,1.001,1.001,track_id='music',audio_role='bgm',audio_stream_index=0),))
    t=replace(timeline,tracks=timeline.tracks+(audio,))
    result=build_interchange_files(t,formats=['otio'],**options(asset))
    read=import_interchange(result['files']['timeline.otio'],format='otio',assets=(asset,),media_refs=options(asset)['media_refs'])
    assert read.to_dict()==t.to_dict()
    fcp=build_interchange_files(t,formats=['fcpxml'],**options(asset))
    read_fcp=import_interchange(fcp['files']['timeline.fcpxml'],format='fcpxml',assets=(asset,),media_refs=options(asset)['media_refs'])
    assert read_fcp.to_dict()==t.to_dict()

@pytest.mark.parametrize('edit',[{'frame_rate':None},{'media_refs':{}},{'media_refs':{'bogus':'../secret'}},{'frame_rate':'nan'}])
def test_unknown_or_mixed_block(timeline,asset,edit):
    kwargs=options(asset);kwargs.update(edit)
    assert preflight_interchange(timeline,format='otio',**kwargs)['status'] in ('UNKNOWN','BLOCKED')
    with pytest.raises(VideoEditingError): build_interchange_files(timeline,**kwargs)


def test_loss_inventory_and_acceptance(timeline,asset):
    clips=tuple(replace(c,audio_role='muted',audio_mix=AudioMix(volume=.5,fade_in_sec=.1,ducking=True)) for c in timeline.tracks[0].clips)
    t=replace(timeline,tracks=(TimelineTrack('video','video',clips),),overlays=(TimedOverlay('o','caption',0,1,'Caption'),),
              transitions=(Transition('a','b','dissolve',.1,'intent'),))
    report=preflight_interchange(t,format='otio',**options(asset))
    codes={i['code'] for i in report['issues']}
    assert {'VOLUME_LOSS','FADE_LOSS','DUCKING_LOSS','MUTED_LOSS','OVERLAY_CAPTION_LOSS','DISSOLVE_OR_TRANSITION_LOSS'} <= codes
    with pytest.raises(VideoEditingError,match='EXPLICIT_ACCEPTANCE'): build_interchange_files(t,**options(asset))
    result=build_interchange_files(t,allow_loss=True,**options(asset))
    assert result['report']['preflight'][0]['status']=='LOSS'
    assert timeline.overlays==()  # no mutations


def test_overlap_and_off_frame(timeline,asset):
    a,b=timeline.tracks[0].clips
    for change in ({'timeline_start':0},):
        t=replace(timeline,tracks=(TimelineTrack('video','video',(a,replace(b,**change))),))
        assert preflight_interchange(t,format='otio',**options(asset))['status']=='BLOCKED'


def test_path_and_xml_rejection(timeline,asset):
    result=build_interchange_files(timeline,**options(asset))
    raw=json.loads(result['files']['timeline.otio'])
    raw['tracks']['children'][0]['children'][0]['media_references']['DEFAULT_MEDIA']['target_url']='https://evil.test/video'
    with pytest.raises(VideoEditingError): import_interchange(json.dumps(raw).encode(),format='otio',assets=(asset,),media_refs=options(asset)['media_refs'])
    with pytest.raises(VideoEditingError): import_interchange(b'<!DOCTYPE x [<!ENTITY x SYSTEM "file:///etc/passwd">]><fcpxml/>',format='fcpxml',assets=(asset,),media_refs=options(asset)['media_refs'])


def test_covers_and_cancel(asset):
    from PIL import Image
    import io
    args=dict(audience='Creator',industry='Video',visual_hook='Story',body_text='Creator Video Story')
    result=build_cover_files(asset,**args)
    assert len(result['files'])==4
    assert result['report']['copy_check']=='EXACT_SUBSTRING_ONLY_HUMAN_REVIEW_REQUIRED'
    for name,data in result['files'].items():
        if name.endswith('.png'):
            assert Image.open(io.BytesIO(data)).size==(1280,720)
    with pytest.raises(VideoEditingError,match='NOT_IN_BODY'): build_cover_files(asset,**dict(args,body_text='unrelated'))
    def cancelled(): raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError,match='cancelled'): build_cover_files(asset,check_cancel=cancelled,**args)

@pytest.mark.parametrize('fmt',['otio','fcpxml'])
def test_real_mixed_rate_and_subframe_roundtrip(timeline,asset,tmp_path,fmt):
    p=tmp_path/'other.mp4'
    subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-f','lavfi','-i',
        'testsrc2=size=160x90:rate=25','-t','2','-c:v','libx264','-threads','1',str(p)],check=True,timeout=30)
    other=fingerprint_local_media(str(p))
    # A rational NTSC cut followed by a different source clock and an exact
    # non-frame-aligned edit. Never force these into rounded project frames.
    a=timeline.tracks[0].clips[0]
    b=TimelineClip('mixed',other.asset_id,.0123,.8123,1.17)
    t=replace(timeline,assets=(asset,other),tracks=(TimelineTrack('video','video',(a,b)),))
    opts={'frame_rate':'30','media_refs':{asset.asset_id:'one.mp4',other.asset_id:'two.mp4'}}
    r=build_interchange_files(t,formats=[fmt],**opts)
    assert r['report']['preflight'][0]['status']=='PASS'
    read=import_interchange(r['files']['timeline.'+fmt],format=fmt,assets=t.assets,media_refs=opts['media_refs'])
    for old,new in zip(t.tracks[0].clips,read.tracks[0].clips):
        assert old.clip_id==new.clip_id
        for key in ('source_in','source_out','timeline_start'):
            assert getattr(new,key)==pytest.approx(getattr(old,key),abs=1e-12)


def test_fcpxml_gain_mute_preserved(timeline,asset):
    clips=tuple(replace(c,audio_role='muted',audio_mix=AudioMix(volume=.5)) for c in timeline.tracks[0].clips)
    t=replace(timeline,tracks=(TimelineTrack('video','video',clips),))
    r=build_interchange_files(t,formats=['fcpxml'],**options(asset))
    assert r['report']['preflight'][0]['status']=='PASS'
    read=import_interchange(r['files']['timeline.fcpxml'],format='fcpxml',assets=t.assets,media_refs=options(asset)['media_refs'])
    assert all(c.audio_role=='muted' and c.audio_mix.volume==pytest.approx(.5,abs=1e-12) for c in read.tracks[0].clips)


def test_actual_scene_change_candidates(tmp_path):
    p=tmp_path/'cuts.mp4'
    subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-f','lavfi','-i','color=c=red:s=160x90:r=30:d=1',
        '-f','lavfi','-i','color=c=blue:s=160x90:r=30:d=1','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]',
        '-map','[v]','-c:v','libx264','-threads','1',str(p)],check=True,timeout=30)
    a=fingerprint_local_media(str(p))
    r=build_cover_files(a,audience='Creator',industry='Video',visual_hook='Story',body_text='Creator Video Story')
    assert any(abs(t-1)<.04 for t in r['report']['scene_analysis']['observed_scene_times'])
    assert r['report']['scene_analysis']['whole_source_analyzed'] is True
    assert r['report']['candidates'][0]['sampling'].startswith('scene_change')
    assert len(r['report']['candidates'])==3

@pytest.mark.parametrize('fmt',['otio','fcpxml'])
def test_audio_only_tracks_and_notes(asset,tmp_path,fmt):
    p=tmp_path/'audio.wav'
    subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-i',asset.path,'-vn','-c:a','pcm_s16le',str(p)],check=True,timeout=30)
    audio=fingerprint_local_media(str(p))
    clip=TimelineClip('spoken',audio.asset_id,.0123,.8123,.1,track_id='voice',audio_role='voiceover',audio_stream_index=0,purpose='Opening context')
    t=Timeline(assets=(audio,),tracks=(TimelineTrack('video','video'),TimelineTrack('voice','voiceover',(clip,))))
    opts={'formats':[fmt],'frame_rate':'30','media_refs':{audio.asset_id:'audio.wav'}}
    r=build_interchange_files(t,**opts)
    read=import_interchange(r['files']['timeline.'+fmt],format=fmt,assets=t.assets,media_refs=opts['media_refs'])
    assert read.tracks[1].clips[0].purpose=='Opening context'
    assert read.tracks[1].clips[0].audio_role=='voiceover'
    assert read.tracks[1].clips[0].source_in==pytest.approx(.0123,abs=1e-12)


def test_aspect_conform_is_not_falsely_portable(timeline,asset):
    t=replace(timeline,format_ratio='9:16')
    report=preflight_interchange(t,format='otio',**options(asset))
    assert 'OUTPUT_FRAME_CONFORM_NOT_PORTABLE' in {i['code'] for i in report['issues']}
    assert preflight_interchange(t,format='fcpxml',**options(asset))['status']=='PASS'


def test_full_gain_boundary_roundtrip(timeline,asset):
    t=replace(timeline,tracks=(TimelineTrack('video','video',tuple(replace(c,audio_mix=AudioMix(volume=2)) for c in timeline.tracks[0].clips)),))
    r=build_interchange_files(t,formats=['fcpxml'],**options(asset))
    read=import_interchange(r['files']['timeline.fcpxml'],format='fcpxml',assets=t.assets,media_refs=options(asset)['media_refs'])
    assert all(c.audio_mix.volume==2 for c in read.tracks[0].clips)


@pytest.mark.parametrize('fmt',['otio','fcpxml'])
def test_explicit_region_crop_requires_loss_acceptance(timeline,asset,fmt):
    from lumenis.shared.content_creation.video_editing import FrameCrop
    edited=timeline.set_frame_crop('a',FrameCrop(x=.25,y=0,width=.5,height=1))
    report=preflight_interchange(edited,format=fmt,**options(asset))
    assert any(issue['code']=='EXPLICIT_FRAME_CROP_NOT_PORTABLE' and issue['severity']=='LOSS' for issue in report['issues'])
    with pytest.raises(VideoEditingError,match='LOSS'):
        build_interchange_files(edited,formats=[fmt],**options(asset))
    delivered=build_interchange_files(edited,formats=[fmt],allow_loss=True,**options(asset))
    assert delivered['report']['loss_accepted']
