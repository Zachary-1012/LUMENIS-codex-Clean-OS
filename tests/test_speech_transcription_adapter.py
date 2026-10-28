"""Gateway adaptation contracts; decoder fixtures are NOT actual ASR evidence."""
import dataclasses,hashlib,json,wave
from pathlib import Path
import pytest
from tests.test_content_project_storage import media_store as media_store
from lumenis.shared.content_creation import speech_transcription as adapter
from lumenis.shared.content_creation.video_editing import VideoEditingError,fingerprint_local_media
from lumenis.system.ai_gateway import owned_speech


def test_missing_configuration_is_unavailable_not_ready(monkeypatch):
    monkeypatch.delenv(adapter.CONFIG_ENV,raising=False)
    assert adapter.speech_runtime_status()['state']=='CONTENT_ASR_RUNTIME_UNAVAILABLE'
    assert adapter.speech_runtime_status()['inference_verified'] is False
    with pytest.raises(VideoEditingError,match='UNAVAILABLE'):adapter.configured_speech_runtime()


@pytest.mark.parametrize('raw',[None,{},[],{'python_path':'relative'}, {'python_path':False}])
def test_invalid_operator_config_fails_closed(tmp_path,monkeypatch,raw):
    path=tmp_path/'speech.json';path.write_text(json.dumps(raw));monkeypatch.setenv(adapter.CONFIG_ENV,str(path))
    with pytest.raises(VideoEditingError,match='CONFIGURATION_INVALID'):adapter.configured_speech_runtime()


@pytest.fixture
def decoder_contract(media_store,monkeypatch):
    runtime=owned_speech.SpeechRuntime('/missing/python','a'*64,'/missing/manifest','b'*64,'/missing/weight','/missing/ffmpeg','c'*64)
    monkeypatch.setattr(adapter,'configured_speech_runtime',lambda:runtime)
    calls=[]
    def decode(path,**kw):
        data=Path(path).read_bytes();assert hashlib.sha256(data).hexdigest()==kw['expected_audio_sha256']
        with wave.open(path) as wav:
            frames,rate=wav.getnframes(),wav.getframerate()
            assert rate==16000 and wav.getnchannels()==1
        kw['is_cancelled']();calls.append(kw)
        raw={'text':' 测试','language':'zh','segments':[{'id':0,'start':0,'end':.2,'text':' 测试','avg_logprob':-.1,'compression_ratio':1,'no_speech_prob':.01,'words':[{'word':'测试','start':0,'end':.2,'probability':.9}]}]}
        return {'schema':'owned-speech-derivative:v1','owner':'SYSTEM AI Gateway',
            **owned_speech.validate_transcript(raw,duration_seconds=frames/rate),
            'source_sha256':kw['expected_audio_sha256'],'source_ref':kw['source_ref'],
            'source_ref_authenticated_by_adapter':False,'duration_seconds':frames/rate,
            'model_id':runtime.model_id,'model_revision':owned_speech.MODEL_REVISION,
            'weight_sha256':owned_speech.model_weight_sha256(runtime.model_id),
            'runtime_manifest_sha256':runtime.manifest_sha256,'adapter_sha256':'d'*64,
            'ffmpeg_sha256':runtime.ffmpeg_sha256,'fallback_allowed':False,'offline':True,
            'declared_language':kw['language_hint'],'rights_state':'UNKNOWN',
            'product_acceptance':False,'warnings':[]}
    monkeypatch.setattr(owned_speech,'transcribe_audio',decode)
    return calls


def test_fixture_decoder_adapter_uses_real_normalization_and_retains_review(media_store,decoder_contract):
    asset=fingerprint_local_media(str(media_store['source']));original=media_store['source'].read_bytes()
    item=adapter.build_transcription_files(asset)
    assert decoder_contract and item['report']['original_source_sha256']==asset.sha256
    assert item['report']['review_state']=='UNREVIEWED' and item['report']['speaker_diarization']=='not_performed'
    assert set(item['files'])=={'transcription.json','transcript-asr.srt','transcript-asr.vtt','transcript-words.json'}
    assert '测试' in item['files']['transcript-asr.srt'].decode() and media_store['source'].read_bytes()==original


def test_callback_denial_prevents_decoder(media_store,decoder_contract):
    asset=fingerprint_local_media(str(media_store['source']))
    def deny():raise PermissionError('scope revoked')
    with pytest.raises(PermissionError):adapter.build_transcription_files(asset,check_cancel=deny)
    assert decoder_contract==[]


def test_operator_configuration_status_never_claims_inference(tmp_path,monkeypatch):
    runtime=owned_speech.SpeechRuntime(str(tmp_path/'missing-python'),'a'*64,str(tmp_path/'missing-manifest'),
        'b'*64,str(tmp_path/'missing-weight'),str(tmp_path/'missing-ffmpeg'),'c'*64)
    path=tmp_path/'config.json';path.write_text(json.dumps(dataclasses.asdict(runtime)));monkeypatch.setenv(adapter.CONFIG_ENV,str(path))
    state=adapter.speech_runtime_status();assert state['state']=='missing_local_files' and len(state['missing_fields'])==4
    assert not state['inference_verified'] and not state['automatic_download']


@pytest.mark.parametrize('hint',[None,*sorted(owned_speech.CONTENT_LANGUAGE_CODES)])
def test_declared_language_is_explicitly_forwarded(media_store,decoder_contract,hint):
    asset=fingerprint_local_media(str(media_store['source']))
    adapter.build_transcription_files(asset,language_hint=hint)
    assert decoder_contract[-1]['language_hint']==hint

@pytest.mark.parametrize('hint',[True,[],{},'auto','zh-CN','../../ko'])
def test_invalid_language_fails_before_runtime(media_store,hint):
    asset=fingerprint_local_media(str(media_store['source']))
    with pytest.raises(VideoEditingError,match='LANGUAGE_INVALID'):
        adapter.build_transcription_files(asset,language_hint=hint)


def test_no_recognized_speech_never_fabricates_subtitle_files(media_store,decoder_contract,monkeypatch):
    runtime=owned_speech.SpeechRuntime('/missing/python','a'*64,'/missing/manifest','b'*64,
        '/missing/weight','/missing/ffmpeg','c'*64)
    def empty(path,**kwargs):
        with wave.open(path) as wav:duration=wav.getnframes()/wav.getframerate()
        return {'schema':'owned-speech-derivative:v1','owner':'SYSTEM AI Gateway',
            **owned_speech.validate_transcript({'text':'','language':'ko','segments':[]},duration_seconds=duration),
            'source_sha256':kwargs['expected_audio_sha256'],'source_ref':kwargs['source_ref'],
            'source_ref_authenticated_by_adapter':False,'duration_seconds':duration,
            'model_id':runtime.model_id,'model_revision':owned_speech.MODEL_REVISION,
            'weight_sha256':owned_speech.model_weight_sha256(runtime.model_id),
            'runtime_manifest_sha256':runtime.manifest_sha256,'adapter_sha256':'d'*64,
            'ffmpeg_sha256':runtime.ffmpeg_sha256,'fallback_allowed':False,'offline':True,
            'declared_language':kwargs['language_hint'],'rights_state':'UNKNOWN',
            'product_acceptance':False,'warnings':[]}
    monkeypatch.setattr(owned_speech,'transcribe_audio',empty)
    asset=fingerprint_local_media(str(media_store['source']))
    result=adapter.build_transcription_files(asset,language_hint='ko')
    assert result['report']['review_state']=='NO_RECOGNIZED_SPEECH'
    assert result['report']['subtitle_export']=={'state':'no_recognized_speech','files':[]}
    assert set(result['files'])=={'transcription.json','transcript-words.json'}


def test_empty_recognition_delivery_has_specific_failure(media_store,decoder_contract,monkeypatch):
    import shared_artifacts as owner
    from lumenis.shared.content_creation.video_editing import Timeline
    asset=fingerprint_local_media(str(media_store['source']))
    timeline=Timeline.from_assets([asset])
    monkeypatch.setattr(adapter,'build_transcription_files',lambda *a,**k:{'files':{},'report':{'review_state':'NO_RECOGNIZED_SPEECH'}})
    with pytest.raises(owner.LocalArtifactError,match='CONTENT_ASR_NO_RECOGNIZED_SPEECH'):
        owner._build_content_delivery(timeline,media_store['source'],output_kind='audio',options={'transcription':{'asset_id':asset.asset_id,'language_hint':'ko'}},render_options={},check_continue=lambda:None)


def mapped_fixture(media_store, decoder_contract, *, ranges=((0,.3,0),)):
    from lumenis.shared.content_creation.video_editing import Timeline
    asset=fingerprint_local_media(str(media_store['source']))
    timeline=Timeline.from_assets([asset]).add_audio_track('voice',audio_role='voiceover')
    for a,b,start in ranges:
        timeline=timeline.add_clip(asset.asset_id,track_id='voice',audio_role='voiceover',source_in=a,source_out=b,timeline_start=start)
    item=adapter.build_transcription_files(asset)
    return timeline,item


def test_mapping_repeats_and_reorders_preserve_original_and_lineage(media_store,decoder_contract):
    timeline,item=mapped_fixture(media_store,decoder_contract,ranges=((0,.3,.4),(0,.3,0)))
    original=dict(item['files'])
    result=adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='a'*64)
    report=result['report'];words=report['words']
    assert item['files']==original
    assert [w['start'] for w in words]==[0,.4]
    assert [w['source_word_id'] for w in words]==['0:0','0:0']
    assert len({w['clip_id'] for w in words})==2
    assert report['rendered_sha256']=='a'*64 and not report['complete_mix_transcription']
    assert report['source_transcription_sha256']==hashlib.sha256(original['transcription.json']).hexdigest()
    assert item['report']['transcript_time_basis']=='original_source_seconds'


def test_cut_word_is_omitted_not_proportionally_rescaled(media_store,decoder_contract):
    timeline,item=mapped_fixture(media_store,decoder_contract,ranges=((.1,.3,0),))
    result=adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='a'*64)
    assert result['report']['state']=='no_retained_words'
    assert result['report']['warnings'][0]['reason']=='cut_or_zero_length_word_omitted'
    assert set(result['files'])=={'transcript-timeline.json'}


def test_mapping_retains_overlapping_selected_audio_for_listening_review(media_store,decoder_contract):
    timeline,item=mapped_fixture(media_store,decoder_contract,ranges=((0,.3,0),))
    asset=timeline.assets[0]
    timeline=timeline.add_audio_track('voice2',audio_role='voiceover').add_clip(asset.asset_id,track_id='voice2',audio_role='voiceover',source_out=.3)
    mapped=adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='a'*64)['report']
    assert len(mapped['words'])==2 and len(mapped['cues'])==2 and mapped['overlapping_cues']
    assert len({word['track_id'] for word in mapped['words']})==2
    assert any(warning['reason']=='overlapping_source_cues_retained_requires_listening_review' for warning in mapped['warnings'])


def test_mapping_unknown_rate_and_cancel_fail_without_result(media_store,decoder_contract):
    timeline,item=mapped_fixture(media_store,decoder_contract)
    clip=next(c for t in timeline.tracks for c in t.clips)
    object.__setattr__(clip,'playback_rate',2)
    mapped=adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='a'*64)['report']
    assert mapped['words'][0]['end']==pytest.approx(.1)
    object.__setattr__(clip,'unknown_time_warp',{})
    with pytest.raises(VideoEditingError,match='RATE_UNSUPPORTED'):
        adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='a'*64)
    def cancel():raise PermissionError('cancelled')
    with pytest.raises(PermissionError,match='cancelled'):
        adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='a'*64,check_cancel=cancel)


def test_mapping_rejects_report_or_output_hash_mismatch(media_store,decoder_contract):
    timeline,item=mapped_fixture(media_store,decoder_contract)
    with pytest.raises(VideoEditingError,match='OUTPUT_HASH_INVALID'):
        adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='wrong')
    item['report']['source_asset_id']='wrong'
    with pytest.raises(VideoEditingError,match='SOURCE_REPORT_MISMATCH'):
        adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='a'*64)


@pytest.mark.parametrize('model_id',[None,'openai/whisper-base','openai/whisper-small'])
def test_operator_config_legacy_and_explicit_model(tmp_path,monkeypatch,model_id):
    raw=dict(python_path=str(tmp_path/'p'),python_sha256='a'*64,manifest_path=str(tmp_path/'m'),
        manifest_sha256='b'*64,weight_path=str(tmp_path/'w'),ffmpeg_path=str(tmp_path/'f'),ffmpeg_sha256='c'*64)
    if model_id:raw['model_id']=model_id
    p=tmp_path/'config.json';p.write_text(json.dumps(raw));monkeypatch.setenv(adapter.CONFIG_ENV,str(p))
    assert adapter.configured_speech_runtime().model_id==(model_id or owned_speech.MODEL_ID)


def test_mapping_delivery_real_package_revision_and_cold_reopen(media_store,decoder_contract,tmp_path):
    import os,subprocess,sys,zipfile
    import shared_artifacts as owner
    from tests.test_content_project_storage import approve,import_source,ACTOR,SCOPE
    from lumenis.shared.content_creation.video_editing import Timeline
    approve(media_store);source=import_source(media_store);source_id=source['artifact']['artifact_id']
    ids=[]
    with owner.resolve_content_source_assets([source_id],actor=ACTOR,**SCOPE) as sources:
        asset=sources[0]['asset'];timeline=Timeline.from_assets([asset]).add_audio_track('voice',audio_role='voiceover')
        timeline=timeline.add_clip(asset.asset_id,track_id='voice',audio_role='voiceover',source_out=.4)
        args=dict(actor=ACTOR,**SCOPE,source_execution_id='mapping-fixture-real-package',output_kind='audio',source_artifact_refs=[source_id],delivery_options={'transcription':{'asset_id':asset.asset_id,'language_hint':'zh'}})
        first=owner.stage_timeline_artifact(timeline,**args);ids.append(first['artifact']['artifact_id'])
        recognition_calls_after_first=len(decoder_contract)
        assert recognition_calls_after_first==1
        clip=next(c for t in timeline.tracks for c in t.clips)
        second=owner.stage_timeline_artifact(timeline.trim(clip.clip_id,source_in=.1,source_out=.4),previous_artifact_id=ids[0],**args);ids.append(second['artifact']['artifact_id'])
        assert len(decoder_contract)==recognition_calls_after_first
    for i,project_id in enumerate(ids):
        owner.read_content_project(project_id,actor=ACTOR,**SCOPE)
        with zipfile.ZipFile(media_store['root']/f'{project_id}.zip') as z:
            names=z.namelist();name=next(n for n in names if n.endswith('transcript-timeline.json'))
            mapped=json.loads(z.read(name));assert mapped['schema']=='timeline-transcription:v2'
            assert mapped['state']==('available' if i==0 else 'no_retained_cues')
            assert any(n.endswith('transcript-asr.srt') for n in names)
    code='import shared_artifacts as a; import json; print(json.dumps([a.read_content_project(i,actor={"id":1,"role":"admin"},domain_id="bmp",global_scope=True)["project"]["output_kind"] for i in '+repr(ids)+']))'
    result=subprocess.run([sys.executable,'-c',code],env=os.environ.copy(),cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)==["audio","audio"]


@pytest.mark.parametrize('text',['中文','English','한국어','日本語','français','Deutsch','español','português','русский','العربية','हिन्दी','Indonesia'])
def test_mapping_preserves_unicode_word_text(media_store,decoder_contract,text):
    timeline,item=mapped_fixture(media_store,decoder_contract)
    item['report']['transcript']['text']=text
    segment=item['report']['transcript']['segments'][0];segment['text']=text;segment['words'][0]['word']=text
    item['files']['transcription.json']=json.dumps(item['report'],ensure_ascii=False).encode()
    result=adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='a'*64)
    assert result['report']['words'][0]['text']==text
    assert text in result['files']['transcript-timeline.srt'].decode()


def test_mapping_fractional_delay_uses_audio_sample_grid(media_store,decoder_contract):
    timeline,item=mapped_fixture(media_store,decoder_contract,ranges=((0,.3,.000013),))
    result=adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='a'*64)
    assert result['report']['words'][0]['start']==round(.000013*48000)/48000


def test_mapping_zero_volume_is_not_transcribed(media_store,decoder_contract):
    from lumenis.shared.content_creation.video_editing import AudioMix
    timeline,item=mapped_fixture(media_store,decoder_contract)
    track=next(t for t in timeline.tracks if t.clips);clip=track.clips[0]
    silent=dataclasses.replace(clip,audio_mix=AudioMix(volume=0))
    timeline=dataclasses.replace(timeline,tracks=tuple(dataclasses.replace(t,clips=(silent,)) if t.track_id==track.track_id else t for t in timeline.tracks))
    result=adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='a'*64)
    assert result['report']['state']=='no_retained_words'


def test_mapping_cancellation_mid_words_returns_no_partial_result(media_store,decoder_contract):
    timeline,item=mapped_fixture(media_store,decoder_contract)
    calls=[]
    def cancel():
        calls.append(1)
        if len(calls)==3:raise PermissionError('cancel mid mapping')
    original=dict(item['files'])
    with pytest.raises(PermissionError,match='cancel mid mapping'):
        adapter.build_timeline_transcription_files(timeline,item,rendered_sha256='a'*64,check_cancel=cancel)
    assert item['files']==original


@pytest.mark.parametrize('code',sorted(owned_speech.CONTENT_LANGUAGE_CODES))
def test_delivery_accepts_same_twelve_languages(code):
    from shared_artifacts import _validate_content_delivery_options
    options={'transcription':{'asset_id':'MEDIA-ab12','language_hint':code}}
    assert _validate_content_delivery_options(options)['transcription']['language_hint']==code
