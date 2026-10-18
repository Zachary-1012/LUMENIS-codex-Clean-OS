"""Real deterministic media capabilities; synthetic inputs are not audience acceptance."""
import json
import math
import struct
import wave
from pathlib import Path
import pytest
import shared_artifacts as artifacts
from lumenis.shared.content_creation.video_editing import Timeline, fingerprint_local_media, VideoEditingError
from lumenis.shared.content_creation import rendering
from tests.test_content_project_storage import media_store, approve, import_source, ACTOR, SCOPE


def source_wave(path):
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(48000)
        audio.writeframes(b''.join(struct.pack('<h', int(3000 * math.sin(2*math.pi*440*n/48000))) for n in range(4*48000)))


def test_real_waveform_and_explicit_linear_master_preserve_source_and_reopen(media_store, tmp_path):
    source_wave(media_store['source']); original=media_store['source'].read_bytes()
    approve(media_store); source=import_source(media_store); source_id=source['artifact']['artifact_id']
    with artifacts.resolve_content_source_assets([source_id],actor=ACTOR,**SCOPE) as sources:
        asset=sources[0]['asset']
        view=rendering.extract_waveform(asset,bins=16)
        assert view['state']=='measured' and view['decoded_samples']==32000 and len(view['bins'])==16
        assert all(x['max']>0.05 and x['min']<-.05 and x['rms']>0 for x in view['bins'])
        timeline=Timeline.from_assets([asset]).add_audio_track('voice',audio_role='voiceover')
        timeline=timeline.add_clip(asset.asset_id,track_id='voice',source_out=4)
        options={'loudness_target_lufs':-16}
        plain=artifacts.content_project_export_resource(timeline,actor=ACTOR,source_artifact_refs=[source_id],output_kind='audio',**SCOPE)
        mastered=artifacts.content_project_export_resource(timeline,actor=ACTOR,source_artifact_refs=[source_id],output_kind='audio',render_options=options,**SCOPE)
        assert plain!=mastered
        result=artifacts.stage_timeline_artifact(timeline,actor=ACTOR,source_execution_id='real-master',output_kind='audio',source_artifact_refs=[source_id],render_options=options,**SCOPE)
        assert result['render']['audio_processing']['loudness_normalized'] is True
        assert result['render']['audio_processing']['mastering']['passes']==2
        loudness=result['render']['measurement']['loudness']
        assert abs(loudness['integrated_lufs']+16)<=1 and loudness['true_peak_dbtp']<=-1
        reopened=artifacts.read_content_project(result['artifact']['artifact_id'],actor=ACTOR,**SCOPE)
        assert reopened['project']['render_options']==options
    assert media_store['source'].read_bytes()==original


@pytest.mark.parametrize('options',[{'loudness_target_lufs':True},{'loudness_target_lufs':-99},{'loudness_target_lufs':float('nan')},{'other':1},[]])
def test_master_options_fail_closed(options):
    with pytest.raises(VideoEditingError):rendering.validate_render_options(options)


def test_waveform_changed_source_and_invalid_stream_denied(media_store):
    asset=fingerprint_local_media(str(media_store['source']))
    with pytest.raises(VideoEditingError,match='WAVEFORM_AUDIO_STREAM_INVALID'):
        rendering.extract_waveform(asset,audio_stream_index=1)
    source_wave(media_store['source'])
    with pytest.raises(VideoEditingError,match='SOURCE_MEDIA_CHANGED'):
        rendering.extract_waveform(asset)


def test_square_preset(tmp_path):
    assert rendering.FRAME_SIZES['1:1']==(1080,1080)


def test_standalone_subtitles_match_burned_frame_timing(media_store):
    asset=fingerprint_local_media(str(media_store['source']))
    timeline=Timeline.from_assets([asset]).add_audio_track('voice',audio_role='voiceover')
    timeline=timeline.add_clip(asset.asset_id,track_id='voice',source_out=.5).add_caption(.01,.49,'中文 & <literal>')
    documents=rendering.subtitle_documents(timeline)
    assert '00:00:00,033 --> 00:00:00,500' in documents['captions.srt']
    assert documents['captions.vtt'].startswith('WEBVTT') and '中文 &amp; &lt;literal&gt;' in documents['captions.vtt']


def test_waveform_http_uses_real_samples_and_rejects_invalid_options(media_store):
    from flask import Flask
    import experience_runtime
    app=Flask(__name__);app.config['LUMENIS_OPEN_WORKSPACE']=True
    app.register_blueprint(experience_runtime.experience_bp)
    api=app.test_client(); headers={'X-Domain-Id':'BMP','X-Product-Id':'ZBMP'}
    def post(options):
        return api.post('/api/experience/shared-skills/shared.content_project/inspect',headers=headers,json={'action_type':'READ','input':{'asset_paths':[str(media_store['source'])],'waveform':options}})
    response=post({'bins':8})
    assert response.status_code==200,response.get_json()
    measured=response.get_json()['waveforms'][0]
    assert measured['decoded_samples']==4000 and len(measured['bins'])==8
    assert post({'bins':False}).status_code==400
    assert post({'audio_stream_index':2}).status_code==400
    assert post({'start_sec':'invalid'}).status_code==400


def test_offline_podcast_package_contains_real_encodings_plan_and_nonpublishable_rss(media_store):
    import zipfile
    import xml.etree.ElementTree as ET
    from podcast.intelligence.episode_runtime import PodcastPlan,PodcastSegment
    source_wave(media_store['source']);approve(media_store);source=import_source(media_store);sid=source['artifact']['artifact_id']
    with artifacts.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as sources:
        asset=sources[0]['asset'];plan=PodcastPlan('自有测试','纯音工程验证','zh',(PodcastSegment(segment_id='s1',media_asset_id=asset.asset_id,source_in=0,source_out=4,original_text='无口语',corrected_text='无口语',speaker='测试',chapter_title='验证'),))
        options={'audio_formats':['mp3','m4a'],'podcast_plan':plan.to_dict()}
        result=artifacts.stage_timeline_artifact(plan.build_timeline((asset,)),actor=ACTOR,**SCOPE,source_execution_id='podcast-real-delivery',output_kind='audio',source_artifact_refs=[sid],render_options={'loudness_target_lufs':-16},delivery_options=options)
    aid=result['artifact']['artifact_id'];opened=artifacts.read_content_project(aid,actor=ACTOR,**SCOPE)
    assert opened['project']['delivery_options']==options
    reports=result['render']['delivery_reports']
    assert reports['mp3']['decode_all_frames']=='passed' and reports['m4a']['decode_all_frames']=='passed'
    assert reports['publication']['publishable'] is False and reports['publication']['missing_url_fields']
    with zipfile.ZipFile(media_store['root']/f'{aid}.zip') as archive:
        assert {'episode.mp3','episode.m4a','show-notes.txt','feed.xml','chapters.json','podcast-plan.json'}<=set(archive.namelist())
        assert ET.fromstring(archive.read('feed.xml')).find('channel/item/enclosure').get('url')=='episode.mp3'
        assert json.loads(archive.read('chapters.json'))['version']=='1.2.0'


@pytest.mark.parametrize('options',[{'audio_formats':['ogg']},{'audio_formats':['mp3','mp3']},{'publication_urls':{}},{'interchange':{'command':'oops'}},{'cover':{'path':'/tmp/secret'}}])
def test_delivery_options_reject_unbounded_fields(options):
    with pytest.raises(ValueError):artifacts._validate_content_delivery_options(options)


def test_real_silence_candidates_keep_margins_and_never_apply(media_store):
    path=media_store['source'];source_wave(path)
    with wave.open(str(path),'rb') as f:params=f.getparams();data=f.readframes(f.getnframes())
    with wave.open(str(path),'wb') as f:
        f.setparams(params);f.writeframes(data[:48000*2]+bytes(48000*2)+data[48000*4:])
    original=path.read_bytes();asset=fingerprint_local_media(str(path))
    report=rendering.propose_silence_edits(asset,min_silence_sec=.5,margin_sec=.15)
    assert report['requires_user_review'] and not report['automatic_application'] and not report['word_alignment_verified']
    candidate=report['candidates'][0]
    assert abs(candidate['suggested_remove_start_sec']-1.15)<.01 and abs(candidate['suggested_remove_end_sec']-1.85)<.01
    assert path.read_bytes()==original


def edl_parent(store):
    approve(store); source=import_source(store); sid=source['artifact']['artifact_id']
    with artifacts.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as sources:
        asset=sources[0]['asset']; timeline=Timeline.from_assets([asset]).add_audio_track('voice',audio_role='voiceover')
        timeline=timeline.add_clip(asset.asset_id,track_id='voice',source_out=.5)
        result=artifacts.stage_timeline_artifact(timeline,actor=ACTOR,**SCOPE,source_execution_id='edl-parent',output_kind='audio',source_artifact_refs=[sid])
    edl={'candidate_id':'EDL-user-edit','decisions':[{'source_clip_ref':timeline.tracks[1].clips[0].clip_id,'in_sec':.1,'out_sec':.4,'operation':'trim','reason':'自有输入明确修剪','confidence':1,'narrative_beat':'保留中段'}]}
    return result['artifact']['artifact_id'],edl


def test_edl_real_confirmation_new_version_and_idempotent_replay(media_store):
    aid,edl=edl_parent(media_store)
    original=artifacts.read_content_project(aid,actor=ACTOR,**SCOPE)
    prepared=artifacts.prepare_content_edl_application(aid,edl,actor=ACTOR,scope=SCOPE,request_id='edl-test-0001')
    assert prepared['state']=='confirmation_required'
    kwargs=dict(actor=ACTOR,scope=SCOPE,request_id='edl-test-0001',expected_resource=prepared['resource'])
    with pytest.raises(ValueError,match='CONFIRMATION_REQUIRED'):
        artifacts.apply_content_edl_application(aid,edl,**kwargs)
    with pytest.raises(ValueError,match='BASE_CHANGED'):
        artifacts.apply_content_edl_application(aid,edl,**{**kwargs,'expected_resource':'bad'},confirmed=True)
    applied=artifacts.apply_content_edl_application(aid,edl,**kwargs,confirmed=True)
    child=artifacts.read_content_project(applied['artifact_id'],actor=ACTOR,**SCOPE)
    assert child['project']['timeline']==prepared['preview_timeline']
    assert child['project']['parent_artifact_id']==aid
    assert artifacts.read_content_project(aid,actor=ACTOR,**SCOPE)==original
    again=artifacts.apply_content_edl_application(aid,edl,**kwargs,confirmed=True)
    assert again['artifact_id']==applied['artifact_id'] and again['idempotent_replay']
    with pytest.raises(ValueError):
        artifacts.apply_content_edl_application(aid,edl,**{**kwargs,'actor':{'id':2,'role':'admin'}},confirmed=True)


def test_edl_exact_approval_revoked_during_real_render_keeps_parent(media_store,monkeypatch):
    aid,edl=edl_parent(media_store)
    prepared=artifacts.prepare_content_edl_application(aid,edl,actor=ACTOR,scope=SCOPE,request_id='edl-test-revoke')
    original=rendering.render_timeline
    def revoke(*args,**kwargs):
        token=media_store['gate'].get_valid_approval_token('data_export',prepared['resource'],exact=True)
        assert token;media_store['gate'].revoke_approval(token)
        return original(*args,**kwargs)
    monkeypatch.setattr(rendering,'render_timeline',revoke)
    with pytest.raises(ValueError,match='EXACT_APPROVAL_REQUIRED'):
        artifacts.apply_content_edl_application(aid,edl,actor=ACTOR,scope=SCOPE,request_id='edl-test-revoke',expected_resource=prepared['resource'],confirmed=True)
    assert artifacts.read_content_project(aid,actor=ACTOR,**SCOPE)
    assert not artifacts._artifact_record(artifacts._content_edl_artifact_id(prepared['operation_id']),read_only=True)


def test_edl_commit_before_consume_retry_returns_same_version(media_store,monkeypatch):
    aid,edl=edl_parent(media_store)
    prepared=artifacts.prepare_content_edl_application(aid,edl,actor=ACTOR,scope=SCOPE,request_id='edl-crash-after-commit')
    kwargs=dict(actor=ACTOR,scope=SCOPE,request_id='edl-crash-after-commit',expected_resource=prepared['resource'],confirmed=True)
    original=media_store['gate'].revoke_approval
    def interrupted(token):raise RuntimeError('simulated process stop after commit')
    monkeypatch.setattr(media_store['gate'],'revoke_approval',interrupted)
    with pytest.raises(RuntimeError,match='after commit'):
        artifacts.apply_content_edl_application(aid,edl,**kwargs)
    saved_id=artifacts._content_edl_artifact_id(prepared['operation_id'])
    assert artifacts.read_content_project(saved_id,actor=ACTOR,**SCOPE)
    monkeypatch.setattr(media_store['gate'],'revoke_approval',original)
    receipt=artifacts.apply_content_edl_application(aid,edl,**kwargs)
    assert receipt['artifact_id']==saved_id and receipt['state']=='already_applied'
    assert not media_store['gate'].get_valid_approval_token('data_export',prepared['resource'],exact=True)
    other=json.loads(json.dumps(edl));other['decisions'][0]['in_sec']=.2
    changed=artifacts.prepare_content_edl_application(aid,other,actor=ACTOR,scope=SCOPE,request_id=kwargs['request_id'])
    with pytest.raises(ValueError,match='REQUEST_ID_CONFLICT'):
        artifacts.apply_content_edl_application(aid,other,**{**kwargs,'expected_resource':changed['resource']})


def test_edl_http_same_origin_and_server_actor_only(media_store,monkeypatch):
    from flask import Flask
    import experience_runtime
    aid,edl=edl_parent(media_store)
    app=Flask(__name__);app.register_blueprint(experience_runtime.experience_bp)
    monkeypatch.setattr(experience_runtime,'_content_project_scope',lambda action:(ACTOR,SCOPE))
    api=app.test_client();base=f'/api/experience/content-projects/{aid}/edl/'
    body={'edl':edl,'request_id':'http-edl-00001'}
    assert api.post(base+'prepare',json=body,headers={'Origin':'https://attacker.invalid'}).status_code!=200
    assert api.post(base+'prepare',json={**body,'actor':{'id':2}}).status_code!=200
    response=api.post(base+'prepare',json=body)
    assert response.status_code==200,response.get_json()
    prepared=response.get_json();payload={**body,'expected_resource':prepared['resource'],'confirmed':True}
    response=api.post(base+'apply',json=payload)
    assert response.status_code==200,response.get_json()
    assert response.get_json()['state']=='applied'


def test_edl_parent_hash_and_live_account_revocation_fail_closed(media_store):
    aid,edl=edl_parent(media_store)
    prepared=artifacts.prepare_content_edl_application(aid,edl,actor=ACTOR,scope=SCOPE,request_id='edl-parent-integrity')
    kwargs=dict(actor=ACTOR,scope=SCOPE,request_id='edl-parent-integrity',expected_resource=prepared['resource'],confirmed=True)
    path=media_store['root']/f'{aid}.zip';data=path.read_bytes()
    path.write_bytes(data+b'changed-after-preview')
    try:
        with pytest.raises(ValueError):artifacts.apply_content_edl_application(aid,edl,**kwargs)
    finally:path.write_bytes(data)
    with media_store['repository'].connect() as connection:
        connection.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    with pytest.raises(ValueError):artifacts.apply_content_edl_application(aid,edl,**kwargs)
    assert not artifacts._artifact_record(artifacts._content_edl_artifact_id(prepared['operation_id']),read_only=True)
    assert not media_store['gate'].get_valid_approval_token('data_export',prepared['resource'],exact=True)


def test_edl_process_death_before_registry_preserves_orphan_and_recovers(media_store):
    import multiprocessing,os
    if 'fork' not in multiprocessing.get_all_start_methods():pytest.skip('POSIX real-process crash test')
    aid,edl=edl_parent(media_store)
    prepared=artifacts.prepare_content_edl_application(aid,edl,actor=ACTOR,scope=SCOPE,request_id='edl-pre-register-crash')
    kwargs=dict(actor=ACTOR,scope=SCOPE,request_id='edl-pre-register-crash',expected_resource=prepared['resource'],confirmed=True)
    def child():
        original=artifacts._register_artifact
        def die(**fields):
            if fields['kind']=='content_project':os._exit(73)
            return original(**fields)
        artifacts._register_artifact=die
        artifacts.apply_content_edl_application(aid,edl,**kwargs)
    process=multiprocessing.get_context('fork').Process(target=child);process.start();process.join(20)
    if process.is_alive():process.kill();process.join();pytest.fail('crash probe timed out')
    assert process.exitcode==73
    generated=artifacts._content_edl_artifact_id(prepared['operation_id'])
    orphan=media_store['root']/f'{generated}.zip';unknown=orphan.read_bytes()
    assert not artifacts._artifact_record(generated,read_only=True)
    result=artifacts.apply_content_edl_application(aid,edl,**kwargs)
    retained=result['recovery']['retained_orphan']
    assert retained and (media_store['root']/retained).read_bytes()==unknown
    assert result['artifact_id']==generated
    assert artifacts.read_content_project(generated,actor=ACTOR,**SCOPE)


def test_edl_two_process_same_request_creates_one_artifact(media_store):
    import multiprocessing
    if 'fork' not in multiprocessing.get_all_start_methods():pytest.skip('POSIX real-process concurrency test')
    aid,edl=edl_parent(media_store)
    prepared=artifacts.prepare_content_edl_application(aid,edl,actor=ACTOR,scope=SCOPE,request_id='edl-two-processes')
    kwargs=dict(actor=ACTOR,scope=SCOPE,request_id='edl-two-processes',expected_resource=prepared['resource'],confirmed=True)
    ctx=multiprocessing.get_context('fork');start=ctx.Event();queue=ctx.Queue()
    def child():
        start.wait(10)
        try:
            result=artifacts.apply_content_edl_application(aid,edl,**kwargs);queue.put(('ok',result['artifact_id']))
        except ValueError as exc:queue.put(('error',str(exc)))
    processes=[ctx.Process(target=child) for _ in range(2)]
    for process in processes:process.start()
    start.set()
    for process in processes:
        process.join(20)
        if process.is_alive():process.kill();process.join();pytest.fail('concurrency probe timed out')
        assert process.exitcode==0
    results=[queue.get(timeout=3) for _ in processes]
    generated=artifacts._content_edl_artifact_id(prepared['operation_id'])
    assert ('ok',generated) in results
    assert all(item in [('ok',generated),('error','CONTENT_EDL_OPERATION_IN_PROGRESS')] for item in results)
    assert not list(media_store['root'].glob(generated+'.orphan-*'))
    replay=artifacts.apply_content_edl_application(aid,edl,**kwargs)
    assert replay['artifact_id']==generated and replay['idempotent_replay']


def test_styled_chinese_caption_real_render_ass_and_saved_version(media_store,tmp_path):
    import subprocess,zipfile
    from lumenis.shared.content_creation.video_editing import CaptionStyle
    source=tmp_path/'owned-video.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=s=320x180:r=30:d=1','-c:v','libx264','-pix_fmt','yuv420p',str(source)],check=True,capture_output=True)
    media_store['source']=source;approve(media_store);sid=import_source(media_store)['artifact']['artifact_id']
    style=CaptionStyle(font_size=42,color='#FFFF00',max_chars_per_line=14,max_lines=2,position='bottom')
    with artifacts.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as sources:
        asset=sources[0]['asset'];timeline=Timeline.from_assets([asset],format_ratio='16:9').add_clip(asset.asset_id,source_out=1)
        text='这是自有中文素材字幕样式验证保留原文并且真实导出'
        timeline=timeline.add_caption(0,.9,text,style=style)
        assert Timeline.from_dict(timeline.to_dict(),assets=[asset]).to_dict()==timeline.to_dict()
        result=artifacts.stage_timeline_artifact(timeline,actor=ACTOR,**SCOPE,source_execution_id='styled-caption',output_kind='video',source_artifact_refs=[sid],delivery_options={'include_ass_subtitles':True})
    aid=result['artifact']['artifact_id'];opened=artifacts.read_content_project(aid,actor=ACTOR,**SCOPE)
    assert opened['project']['timeline']['overlays'][0]['style']==style.to_dict()
    layout=result['render']['overlay_processing']['measured_layouts'][0]
    assert all(len(line)<=14 for line in layout['display_text'].split('\n'))
    assert layout['text_width_px']+16<=1280-2*layout['horizontal_margin_px']
    with zipfile.ZipFile(media_store['root']/f'{aid}.zip') as archive:
        ass=archive.read('captions.ass');(tmp_path/'captions.ass').write_bytes(ass)
        assert b'[V4+ Styles]' in ass and b'\\N' in ass
        assert layout['display_text'] in archive.read('captions.srt').decode()
    # The actual libass parser/render path accepts the emitted file.
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=s=1280x720:d=1','-vf','ass=captions.ass','-frames:v','1','-f','null','-'],cwd=tmp_path,check=True,capture_output=True)


@pytest.mark.parametrize('style',[{'font_size':True},{'font_size':200},{'color':'red:movie=evil'},{'safe_margin_ratio':0},{'background_opacity':float('nan')},{'max_chars_per_line':15},{'position':'center'}, {'fontfile':'/untrusted.ttf'}])
def test_caption_style_rejects_unsafe_or_unbounded_fields(style):
    from lumenis.shared.content_creation.video_editing import CaptionStyle
    with pytest.raises(ValueError):CaptionStyle.from_dict(style)


def test_explicit_frame_crop_preserves_selected_subject_region_and_version(media_store,tmp_path):
    import subprocess
    from lumenis.shared.content_creation.video_editing import FrameCrop
    source=tmp_path/'two-regions.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=blue:s=320x180:r=30:d=0.5','-vf','drawbox=x=0:y=0:w=160:h=180:color=red:t=fill','-c:v','libx264','-pix_fmt','yuv420p',str(source)],check=True,capture_output=True)
    media_store['source']=source;original=source.read_bytes();approve(media_store);sid=import_source(media_store)['artifact']['artifact_id']
    with artifacts.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as sources:
        asset=sources[0]['asset'];timeline=Timeline.from_assets([asset],format_ratio='9:16').add_clip(asset.asset_id,source_out=.5)
        clip=timeline.tracks[0].clips[0];crop=FrameCrop(0,0,.5,1)
        cropped=timeline.set_frame_crop(clip.clip_id,crop)
        assert cropped.undo().tracks==timeline.tracks
        result=artifacts.stage_timeline_artifact(cropped,actor=ACTOR,**SCOPE,source_execution_id='explicit-crop',output_kind='video',source_artifact_refs=[sid])
    aid=result['artifact']['artifact_id'];opened=artifacts.read_content_project(aid,actor=ACTOR,**SCOPE)
    assert opened['project']['timeline']['tracks'][0]['clips'][0]['frame_crop']==crop.to_dict()
    data=artifacts.authorized_project_media(aid,actor=ACTOR,**SCOPE)['data'];out=tmp_path/'cropped.mp4';out.write_bytes(data)
    pixel=subprocess.run(['ffmpeg','-v','error','-ss','0.2','-i',str(out),'-vf','crop=2:2:iw/2:ih/2','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'],check=True,capture_output=True).stdout
    assert len(pixel)==12 and pixel[0]>200 and pixel[1]<50 and pixel[2]<50
    assert source.read_bytes()==original
    assert result['render']['frame_processing']['automatic_subject_detection'] is False


@pytest.mark.parametrize('values',[(0,0,0,1),(-.1,0,.5,.5),(.8,0,.3,1),(0,0,float('nan'),1),(True,0,.5,1)])
def test_frame_crop_invalid_values_fail_closed(values):
    from lumenis.shared.content_creation.video_editing import FrameCrop
    with pytest.raises(ValueError):FrameCrop(*values)


def test_measured_silence_candidate_confirmed_audio_ripple_real_new_version(media_store):
    from lumenis.shared.content_creation.editorial_candidates import silence_edl_candidate
    with wave.open(str(media_store['source']),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(48000)
        audio.writeframes(b''.join(struct.pack('<h',0 if 48000<=n<96000 else int(3000*math.sin(2*math.pi*440*n/48000))) for n in range(144000)))
    approve(media_store);sid=import_source(media_store)['artifact']['artifact_id']
    with artifacts.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as sources:
        asset=sources[0]['asset'];timeline=Timeline.from_assets([asset]).add_audio_track('voice',audio_role='voiceover').add_clip(asset.asset_id,track_id='voice',source_out=3)
        parent=artifacts.stage_timeline_artifact(timeline,actor=ACTOR,**SCOPE,source_execution_id='silence-parent',output_kind='audio',source_artifact_refs=[sid])
        measured=rendering.propose_silence_edits(asset,min_silence_sec=.5,margin_sec=.15)
        candidate=silence_edl_candidate(timeline,measured)
    assert candidate['word_alignment_verified'] is False and len(candidate['edl']['decisions'])==3
    aid=parent['artifact']['artifact_id'];request='silence-reviewed-001'
    prepared=artifacts.prepare_content_edl_application(aid,candidate['edl'],actor=ACTOR,scope=SCOPE,request_id=request)
    result=artifacts.apply_content_edl_application(aid,candidate['edl'],actor=ACTOR,scope=SCOPE,request_id=request,expected_resource=prepared['resource'],confirmed=True)
    reopened=artifacts.read_content_project(result['artifact_id'],actor=ACTOR,**SCOPE)
    clips=reopened['project']['timeline']['tracks'][1]['clips']
    assert len(clips)==2 and clips[1]['timeline_start']==pytest.approx(1.15,abs=.001)
    assert result['result']['render']['measurement']['actual_duration_sec']==pytest.approx(2.3,abs=.05)
    assert artifacts.read_content_project(aid,actor=ACTOR,**SCOPE)['project']['timeline']==timeline.to_dict()


def test_real_audio_visual_delivery_from_rendered_output_and_reopen(media_store):
    import zipfile
    approve(media_store);sid=import_source(media_store)['artifact']['artifact_id']
    options={'audio_visual':{'start_sec':0,'end_sec':.5,'quote':'自有纯音测试不是真人讲话','title':'离线切片验证','format_ratio':'1:1'}}
    with artifacts.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as sources:
        asset=sources[0]['asset'];timeline=Timeline.from_assets([asset]).add_audio_track('voice',audio_role='voiceover').add_clip(asset.asset_id,track_id='voice',source_out=.5)
        result=artifacts.stage_timeline_artifact(timeline,actor=ACTOR,**SCOPE,source_execution_id='audio-visual-owner',output_kind='audio',source_artifact_refs=[sid],delivery_options=options)
    report=result['render']['delivery_reports']['audio_visual']
    assert report['source_sha256']==result['render']['media_sha256'] and report['source_kind']=='rendered_output'
    aid=result['artifact']['artifact_id'];opened=artifacts.read_content_project(aid,actor=ACTOR,**SCOPE)
    with zipfile.ZipFile(media_store['root']/f'{aid}.zip') as archive:
        assert {'audio-visual.png','quote-card.png','audio-visual.mp4','audio-visual.json'} <= set(archive.namelist())
    assert opened['project']['delivery_options']==options


def test_actual_source_frame_timing_and_metadata_persist_in_artifact(media_store,tmp_path):
    import subprocess
    from lumenis.shared.content_creation.stream_probe import probe_source_streams
    source=tmp_path/'timed.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=s=320x180:r=30:d=1','-c:v','libx264','-pix_fmt','yuv420p',str(source)],check=True,capture_output=True)
    media_store['source']=source;approve(media_store);sid=import_source(media_store)['artifact']['artifact_id']
    with artifacts.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as sources:
        asset=sources[0]['asset'];report=probe_source_streams(asset,analyze_timing=True)
        assert report['frame_timing']['cfr_verified'] and report['frame_timing']['frames_observed']==30
        assert report['streams'][0]['width']==320 and report['streams'][0]['time_base']
        timeline=Timeline.from_assets([asset],format_ratio='16:9').add_clip(asset.asset_id,source_out=1)
        result=artifacts.stage_timeline_artifact(timeline,actor=ACTOR,**SCOPE,source_execution_id='source-probe',output_kind='video',source_artifact_refs=[sid],delivery_options={'include_source_probe':True})
    opened=artifacts.read_content_project(result['artifact']['artifact_id'],actor=ACTOR,**SCOPE)
    assert 'source-probe.json' in opened['project']['delivery_manifest']
    assert result['render']['delivery_reports']['source_probe']['sources'][0]==report


def test_opt_in_fft_denoise_reduces_measured_test_noise_preserves_original(media_store):
    import random
    from lumenis.shared.content_creation.video_editing import AudioMix
    rng=random.Random(414)
    with wave.open(str(media_store['source']),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(48000)
        audio.writeframes(b''.join(struct.pack('<h',int(rng.uniform(-300,300)+(0 if n<24000 else 5000*math.sin(2*math.pi*440*n/48000)))) for n in range(96000)))
    original=media_store['source'].read_bytes();approve(media_store);sid=import_source(media_store)['artifact']['artifact_id']
    with artifacts.resolve_content_source_assets([sid],actor=ACTOR,**SCOPE) as sources:
        asset=sources[0]['asset'];timeline=Timeline.from_assets([asset]).add_audio_track('voice',audio_role='voiceover').add_clip(asset.asset_id,track_id='voice',source_out=2)
        before=rendering.extract_waveform(asset,start_sec=.1,end_sec=.4,bins=1)['bins'][0]['rms']
        result=artifacts.stage_timeline_artifact(timeline,actor=ACTOR,**SCOPE,source_execution_id='explicit-denoise',output_kind='audio',source_artifact_refs=[sid],render_options={'noise_reduction_db':12,'noise_floor_db':-35})
    report=result['render']['audio_processing']
    assert report['noise_reduction_applied'] and not report['loudness_normalized']
    aid=result['artifact']['artifact_id'];path=media_store['source'].with_name('denoised-result.wav')
    path.write_bytes(artifacts.authorized_project_media(aid,actor=ACTOR,**SCOPE)['data'])
    after=rendering.extract_waveform(fingerprint_local_media(str(path)),start_sec=.1,end_sec=.4,bins=1)['bins'][0]['rms']
    assert after<before*.6
    assert media_store['source'].read_bytes()==original
    assert artifacts.read_content_project(aid,actor=ACTOR,**SCOPE)['project']['render_options']['noise_reduction_db']==12


@pytest.mark.parametrize('options',[{'noise_floor_db':-35},{'noise_reduction_db':True},{'noise_reduction_db':99},{'noise_reduction_db':12,'noise_floor_db':float('nan')}])
def test_denoise_requires_explicit_bounded_options(options):
    with pytest.raises(ValueError):rendering.validate_render_options(options)


def test_real_variable_frame_timestamps_are_not_reported_as_cfr(media_store):
    import subprocess
    from lumenis.shared.content_creation.stream_probe import probe_source_streams
    path=media_store['source'].with_suffix('.mp4')
    subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-f','lavfi','-i','testsrc2=s=96x64:r=30:d=1',
                    '-vf',"select='not(mod(n,2))+eq(n,3)'",'-fps_mode','vfr','-c:v','libx264','-threads:v','1',str(path)],check=True,capture_output=True)
    result=probe_source_streams(fingerprint_local_media(str(path)),analyze_timing=True)
    assert result['frame_timing']['global_classification']=='variable_frame_intervals'
    assert result['frame_timing']['observed_constant_intervals'] is False
    assert result['frame_timing']['cfr_verified'] is False


@pytest.mark.parametrize('options',[{'reference_analysis':None},{'reference_analysis':{'asset_id':None}},
    {'reference_analysis':{'asset_id':'../outside'}},{'audio_formats':[{}]},
    {'interchange':None},{'cover':None},{'audio_visual':None}])
def test_optional_delivery_shape_rejected_before_render(options):
    with pytest.raises(artifacts.LocalArtifactError):artifacts._validate_content_delivery_options(options)
