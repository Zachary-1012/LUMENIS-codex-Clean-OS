"""PR83 boundary regressions using real generated media; probe faults are isolated."""
import json
import subprocess
from xml.etree import ElementTree as ET
import pytest
from tests.test_timeline_interchange_delivery import asset, timeline, options
from lumenis.shared.content_creation import timeline_interchange as exchange
from lumenis.shared.content_creation.video_editing import VideoEditingError

@pytest.mark.parametrize('field,value', [('avg_frame_rate','0/0'), ('r_frame_rate','0/0'),
    ('time_base','1/0'), ('time_base',None), ('avg_frame_rate',None)])
def test_bad_probe_rate_returns_unknown(timeline, asset, monkeypatch, field, value):
    real_run = subprocess.run
    def bad_probe(args, **kwargs):
        result = real_run(args, **kwargs)
        if 'stream=avg_frame_rate,r_frame_rate,time_base,width,height' in args:
            data = json.loads(result.stdout)
            data['streams'][0][field] = value
            result.stdout = json.dumps(data)
        return result
    monkeypatch.setattr(exchange.subprocess, 'run', bad_probe)
    report = exchange.preflight_interchange(timeline, format='otio', **options(asset))
    assert report['status'] == 'UNKNOWN'
    assert 'SOURCE_TIMEBASE_UNKNOWN' in {i['code'] for i in report['issues']}

@pytest.mark.parametrize('fmt', ['otio','fcpxml'])
def test_supplied_rate_reaches_export_when_probe_rate_unknown(timeline, asset, monkeypatch, fmt):
    real_run = subprocess.run
    def unknown_rate(args, **kwargs):
        result = real_run(args, **kwargs)
        if 'stream=avg_frame_rate,r_frame_rate,time_base,width,height' in args:
            data = json.loads(result.stdout)
            data['streams'][0]['avg_frame_rate'] = '0/0'
            result.stdout = json.dumps(data)
        return result
    monkeypatch.setattr(exchange.subprocess, 'run', unknown_rate)
    result = exchange.build_interchange_files(timeline, formats=[fmt], source_frame_rates={asset.asset_id:'30000/1001'}, **options(asset))
    report = result['report']['preflight'][0]
    assert report['source_frame_rates'][asset.asset_id] == '30000/1001'
    restored = exchange.import_interchange(result['files']['timeline.'+fmt], format=fmt, assets=(asset,), media_refs=options(asset)['media_refs'])
    assert restored.to_dict() == timeline.to_dict()

@pytest.mark.parametrize('width,height', [('1280','0'),('1280','-90'),('0','720'),('-1280','-720')])
def test_bad_fcpxml_dimensions_reject_cleanly(timeline, asset, width, height):
    result = exchange.build_interchange_files(timeline, formats=['fcpxml'], **options(asset))
    root = ET.fromstring(result['files']['timeline.fcpxml'])
    root.find('./resources/format').set('height', height)
    root.find('./resources/format').set('width', width)
    with pytest.raises(VideoEditingError, match='^INTERCHANGE_DOCUMENT_UNSUPPORTED_OR_INVALID$'):
        exchange.import_interchange(ET.tostring(root), format='fcpxml', assets=(asset,), media_refs=options(asset)['media_refs'])

@pytest.mark.parametrize('fmt', ['otio','fcpxml'])
def test_caller_cannot_override_measured_clock(timeline, asset, fmt):
    result = exchange.build_interchange_files(timeline, formats=[fmt], source_frame_rates={asset.asset_id:'25'}, **options(asset))
    report = result['report']['preflight'][0]
    assert report['source_frame_rates'][asset.asset_id] == '30000/1001'
    assert report['source_rate_origins'][asset.asset_id] == 'FFPROBE_STREAM_METADATA'
    restored = exchange.import_interchange(result['files']['timeline.'+fmt], format=fmt, assets=(asset,), media_refs=options(asset)['media_refs'])
    assert restored.to_dict() == timeline.to_dict()

@pytest.mark.parametrize('value', ['0/0','0','-1','nan','inf','241','1/0',True,30,30.0,None,{},[]])
def test_invalid_fallback_never_unblocks(timeline, asset, monkeypatch, value):
    monkeypatch.setattr(exchange, '_ffprobe_path', lambda: None)
    report = exchange.preflight_interchange(timeline, format='otio', source_frame_rates={asset.asset_id:value}, **options(asset))
    assert report['status'] == 'UNKNOWN'
    assert report['source_frame_rates'] == {}
    with pytest.raises(VideoEditingError, match='INTERCHANGE_PREFLIGHT_BLOCKED_OR_UNKNOWN'):
        exchange.build_interchange_files(timeline, formats=['otio'], source_frame_rates={asset.asset_id:value}, **options(asset))


def test_fallback_without_probe_rates_preserves_otio_clock(timeline, asset, monkeypatch):
    monkeypatch.setattr(exchange, '_ffprobe_path', lambda: None)
    result = exchange.build_interchange_files(timeline, formats=['otio'], frame_rate='25',
        source_frame_rates={asset.asset_id:'30000/1001'}, media_refs=options(asset)['media_refs'])
    report = result['report']['preflight'][0]
    assert report['source_rate_origins'] == {asset.asset_id:'CALLER_DECLARED'}
    assert report['source_rate_verification'] == 'CALLER_DECLARED_FALLBACK_NOT_FULL_FILE_CFR_ASSERTION'
    obj = json.loads(result['files']['timeline.otio'])
    assert obj['tracks']['children'][0]['children'][0]['source_range']['start_time']['rate'] == float(30000/1001)
    restored = exchange.import_interchange(result['files']['timeline.otio'], format='otio', assets=(asset,), media_refs=options(asset)['media_refs'])
    assert restored.to_dict() == timeline.to_dict()


def test_missing_dimensions_remain_unknown_for_fcpxml(timeline, asset, monkeypatch):
    monkeypatch.setattr(exchange, '_ffprobe_path', lambda: None)
    report = exchange.preflight_interchange(timeline, format='fcpxml', source_frame_rates={asset.asset_id:'30000/1001'}, **options(asset))
    assert 'SOURCE_DIMENSIONS_UNKNOWN' in {i['code'] for i in report['issues']}
    with pytest.raises(VideoEditingError, match='INTERCHANGE_PREFLIGHT_BLOCKED_OR_UNKNOWN'):
        exchange.build_interchange_files(timeline, formats=['fcpxml'], source_frame_rates={asset.asset_id:'30000/1001'}, **options(asset))


def test_conflicting_measured_rates_cannot_use_fallback(timeline, asset, monkeypatch):
    real_run = subprocess.run
    def conflicting(args, **kwargs):
        result = real_run(args, **kwargs)
        if 'stream=avg_frame_rate,r_frame_rate,time_base,width,height' in args:
            data = json.loads(result.stdout)
            data['streams'][0]['r_frame_rate'] = '25'
            result.stdout = json.dumps(data)
        return result
    monkeypatch.setattr(exchange.subprocess, 'run', conflicting)
    report = exchange.preflight_interchange(timeline, format='otio', source_frame_rates={asset.asset_id:'30000/1001'}, **options(asset))
    assert report['status'] == 'UNKNOWN'
    assert report['source_frame_rates'] == {}


def test_fallback_cannot_export_missing_source(timeline, asset, monkeypatch):
    monkeypatch.setattr(exchange, '_ffprobe_path', lambda: None)
    from dataclasses import replace
    missing = replace(asset, path=asset.path+'.missing')
    broken = replace(timeline, assets=(missing,))
    with pytest.raises(VideoEditingError):
        exchange.build_interchange_files(broken, formats=['otio'], source_frame_rates={asset.asset_id:'30000/1001'}, **options(asset))


def test_cmx_fallback_does_not_bypass_full_pts(timeline, asset, monkeypatch):
    from pathlib import Path
    monkeypatch.setenv('LUMENIS_LOCAL_ASSET_DIR', str(Path(asset.path).parent))
    monkeypatch.setattr(exchange, '_ffprobe_path', lambda: None)
    report = exchange.preflight_interchange(timeline, format='cmx3600', frame_rate='30',
        source_frame_rates={asset.asset_id:'30'}, media_refs=options(asset)['media_refs'])
    assert report['status'] in ('BLOCKED','UNKNOWN')
    assert 'CMX_FULL_CFR_ZERO_ORIGIN_REQUIRED' in {i['code'] for i in report['issues']}
    with pytest.raises(VideoEditingError, match='INTERCHANGE_PREFLIGHT_BLOCKED_OR_UNKNOWN'):
        exchange.build_interchange_files(timeline, formats=['cmx3600'], allow_loss=True, frame_rate='30',
            source_frame_rates={asset.asset_id:'30'}, media_refs=options(asset)['media_refs'])


@pytest.mark.parametrize('declared', ['30','25'])
def test_cmx_fallback_valid_full_pts_still_exports(tmp_path, monkeypatch, declared):
    monkeypatch.setenv('LUMENIS_LOCAL_ASSET_DIR', str(tmp_path))
    from lumenis.shared.content_creation.video_editing import fingerprint_local_media, Timeline, TimelineTrack, TimelineClip
    path = tmp_path/'cfr30.mp4'
    subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-f','lavfi','-i',
        'testsrc2=size=160x90:rate=30','-t','2','-c:v','libx264','-threads','1',str(path)], check=True, timeout=30)
    real_asset = fingerprint_local_media(str(path))
    real_timeline = Timeline(assets=(real_asset,), tracks=(TimelineTrack('video','video',(
        TimelineClip('cut',real_asset.asset_id,.1,1.1,0),)),),format_ratio='16:9')
    monkeypatch.setattr(exchange, '_ffprobe_path', lambda: None)
    if declared != '30':
        report = exchange.preflight_interchange(real_timeline, format='cmx3600', frame_rate='30',
            source_frame_rates={real_asset.asset_id:declared}, media_refs={real_asset.asset_id:'source.mp4'})
        assert report['status'] == 'UNKNOWN'
        assert 'CMX_SOURCE_RATE_CONFLICT' in {i['code'] for i in report['issues']}
        return
    result = exchange.build_interchange_files(real_timeline, formats=['cmx3600'], allow_loss=True,
        frame_rate='30', source_frame_rates={real_asset.asset_id:'30'}, media_refs={real_asset.asset_id:'source.mp4'})
    assert result['report']['preflight'][0]['source_rate_verification'] == 'FULL_SOURCE_PTS_CFR_ZERO_ORIGIN'
    assert '00:00:00:03 00:00:01:03 00:00:00:00 00:00:01:00' in result['files']['timeline.edl'].decode()
