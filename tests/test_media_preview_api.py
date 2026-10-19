"""Read-only media previews use the real exact Shared route and local identity guards."""
import hashlib,json
import pytest
from tests.test_content_project_storage import media_store,rows
from tests.test_local_content_source_routes import local_client,SHARED_HEADERS
from podcast.intelligence.editorial_planning import GATES


def test_real_shared_speech_preview_has_measured_identity_no_persistence(local_client):
    client,store,_=local_client
    response=client.post('/api/experience/content-sources/tts/preview',headers=SHARED_HEADERS,json={'text':'This is a synthetic engineering test.','voice':'slt','language':'en-US'})
    assert response.status_code==200,response.get_json()
    assert response.data[:4]==b'RIFF' and response.headers['X-Lumenis-Synthetic']=='true'
    assert response.headers['X-Lumenis-TTS-Engine']=='ffmpeg_libflite'
    assert response.headers['X-Lumenis-TTS-Voice']=='slt' and response.headers['X-Lumenis-TTS-Language']=='en-US'
    assert response.headers['X-Lumenis-Source-SHA256']==hashlib.sha256(response.data).hexdigest()
    assert rows(store)==[]


@pytest.mark.parametrize('body',[{'text':'你好'},{'text':'Hello','actor_id':9},{'text':'Hello','voice':'unknown'},{'text':'Hello','language':'ko'}])
def test_speech_preview_rejects_unsupported_or_identity_injection(local_client,body):
    client,store,_=local_client
    response=client.post('/api/experience/content-sources/tts/preview',headers=SHARED_HEADERS,json=body)
    assert response.status_code==(400 if 'actor_id' in body else 503),response.get_json()
    assert response.get_json()['code'] in {'CONTENT_TTS_INPUT_INVALID','TTS_LANGUAGE_UNAVAILABLE','TTS_VOICE_UNAVAILABLE'}
    assert rows(store)==[]


@pytest.mark.parametrize('path',['/api/experience/content-sources/tts/preview','/api/experience/podcast/editorial/preview'])
def test_preview_cross_origin_denied(local_client,path):
    client,store,_=local_client
    response=client.post(path,headers={**SHARED_HEADERS,'Origin':'https://evil.invalid'},json={'text':'hello'})
    assert response.status_code==403,response.get_json()
    assert rows(store)==[]


def test_editorial_shared_explicit_gates_bound_to_server_context(local_client):
    client,store,_=local_client
    body={'topic':'播客制作','guests':[{'guest_id':'own','name':'测试资料','domains':['播客制作'],'prior_programmes':[],'viewpoints':[],'source_refs':['user:own']}],'selected_guest_id':'own','gates':{gate:{'decision':'pass','note':'用户测试确认'} for gate in GATES}}
    response=client.post('/api/experience/podcast/editorial/preview',headers=SHARED_HEADERS,json=body)
    assert response.status_code==200,response.get_json()
    result=response.get_json();assert result['state']=='editable_draft' and not result['external_fetch']
    payload=result['saved_work_draft']['payload'];assert payload['manual_review_context']['principal_ref']=='workspace:local'
    assert hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()==result['saved_work_payload_hash']
    body['gates'][GATES[0]]['decision']='unknown'
    response=client.post('/api/experience/podcast/editorial/preview',headers=SHARED_HEADERS,json=body)
    assert response.get_json()['state']=='manual_gate_blocked'
    assert rows(store)==[]


@pytest.mark.parametrize('language,text,voice',[('zh-CN','这是明确标记的合成测试。','cmn'),('ko','이 음성은 합성 테스트입니다.','ko')])
def test_explicit_formant_preview_uses_requested_engine(local_client,language,text,voice):
    import os
    if not os.environ.get('LUMENIS_ESPEAK_BINARY'):pytest.skip('explicit isolated eSpeak runtime not configured')
    client,store,_=local_client
    response=client.post('/api/experience/content-sources/tts/preview',headers=SHARED_HEADERS,json={'engine':'espeak_ng','language':language,'text':text})
    assert response.status_code==200,response.get_json()
    assert response.headers['X-Lumenis-TTS-Engine']=='espeak_ng' and response.headers['X-Lumenis-TTS-Voice']==voice
    assert response.headers['X-Lumenis-TTS-Language']==language and response.data[:4]==b'RIFF'
    assert rows(store)==[]
