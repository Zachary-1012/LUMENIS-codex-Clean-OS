"""Public response-to-Source custody on disposable owners; acquisition is a fixture."""
import base64
import hashlib
import json
import sqlite3

import pytest

from tests.test_collector_transaction_truth import (
    admit_registered_subject_for_isolated_collector,
    collector_case as collector_case,
    URL,
    REGISTERED_NAME,
)


@pytest.fixture(autouse=True)
def _admit_registered_subject_for_public_original(request):
    case = request.getfixturevalue("collector_case")
    admit_registered_subject_for_isolated_collector(case)


def test_media_only_public_source_empty_text_original_and_processing_prepare(collector_case,monkeypatch,tmp_path):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.importer.documents import _source_bytes
    from lumenis.shared.reporting.media_brief import prepare_collected_media
    import shared_artifacts
    case=collector_case
    monkeypatch.setenv('ZBC_ARTIFACT_DIR',str(tmp_path/'artifacts'))
    shared_artifacts.ensure_artifact_table()
    source='https://public.example.test/player'
    original=('<html><head><title>'+REGISTERED_NAME+'</title></head><body>'
        '<video src="https://cdn.example.test/native.mpd"></video></body></html>').encode()
    adapter=PublicHttpAdapter(fetcher=lambda url:PublicResponse(source,original,'text/html',200,source))
    monkeypatch.setattr(case['surface'],'_get_runtime_adapter',lambda *args:adapter)
    monkeypatch.setitem(case['surface']._last_action,'public_http',0.0)
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    body={'operator':'human','confirm_read_only':True,'platform':'public_http','keyword':source,'max_results':1}
    def post(action,**extra):
        return case['client'].post(URL,headers=case['focus_headers'],json={**body,'action':action,**extra})
    prepared=post('prepare').get_json()
    assert post('confirm',confirmed_resource=prepared['approval_resource']).get_json()['approved']
    result=post('run').get_json()
    assert result['ok'],result
    item=result['items'][0]
    assert item['body_character_count']==0 and item['body_preview'] is None
    assert item['body_state']=='EMPTY' and item['original_body_available'] is False
    assert item['media'][0]['url']=='https://cdn.example.test/native.mpd'
    refs=result['public_original_refs'];assert refs['status']=='SAVED',refs
    with sqlite3.connect(case['db_path']) as con:
        con.row_factory=sqlite3.Row
        source_id=int(refs['source_evidence_ref'].split(':')[1])
        row=dict(con.execute('SELECT * FROM app_evidence_records WHERE id=?',(source_id,)).fetchone())
        document,_=_source_bytes(con,{**row,'provenance':json.loads(row['collection_metadata'])})
        value=json.loads(document)
        assert value['body']=='' and value['body_state']=='EMPTY'
        assert base64.b64decode(value['source_response']['body_base64'])==original
        assert con.execute('SELECT content FROM notes WHERE note_id=?',(item['source_id'],)).fetchone()[0]==''
    with case['client'].application.test_request_context('/',headers=case['focus_headers'],
            environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
        actor=case['permission'].resolve_local_workspace_principal(module='collector',action='read')
        prepared=prepare_collected_media(item['source_id'],actor=actor,scope=case['scope'],
            source_evidence_ref=item['evidence_ref'])
        assert prepared['media'][0]['acquisition']['representation']=='STREAM_MANIFEST'
        assert not prepared['network_attempted']


def test_manual_public_response_has_reopenable_exact_original(collector_case, monkeypatch, tmp_path):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter
    from lumenis.importer.documents import _source_bytes
    from lumenis.shared.evidence.store import classify_evidence_integrity
    import shared_artifacts
    case = collector_case
    monkeypatch.setenv('ZBC_ARTIFACT_DIR', str(tmp_path / 'artifacts'))
    shared_artifacts.ensure_artifact_table()
    original = ('<!doctype html><html><head><title>Original source</title></head><body><main><h1>'
        + REGISTERED_NAME + '</h1><p>Native public source statement for current scope.</p>'
        '<img src="/native-image.png"><audio src="/native-audio.wav"></audio></main></body></html>').encode()
    source_url = 'https://public.example.test/official-source'
    response = PublicResponse(url=source_url, requested_url=source_url, content=original,
                              content_type='text/html', status_code=200)
    adapter = PublicHttpAdapter(fetcher=lambda url: response)
    monkeypatch.setattr(PublicHttpAdapter, "_document_limiter",
                        AdaptiveRateLimiter(base_interval=0, min_interval=0, jitter=False))
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda *args: adapter)
    monkeypatch.setitem(case['surface']._last_action, 'public_http', 0.0)
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    body = {'operator': 'human', 'confirm_read_only': True, 'platform': 'public_http',
            'keyword': source_url, 'max_results': 1}
    def post(action, **extra):
        return case['client'].post(URL, headers=case['focus_headers'], json={**body, 'action': action, **extra})
    prepared = post('prepare').get_json()
    assert post('confirm', confirmed_resource=prepared['approval_resource']).get_json()['approved']
    result = post('run').get_json()
    assert result['ok'] and result['canonical_synced'] == 1
    assert {item['kind'] for item in result['items'][0]['media']} == {'image','audio'}
    assert all(item['original_bytes_state'] == 'NOT_ACQUIRED' for item in result['items'][0]['media'])
    refs = result['public_original_refs']
    assert refs['status'] == 'SAVED', refs
    source_id = int(refs['source_evidence_ref'].split(':')[1])
    with sqlite3.connect(case['db_path']) as con:
        con.row_factory = sqlite3.Row
        evidence = dict(con.execute('SELECT * FROM app_evidence_records WHERE id=?', (source_id,)).fetchone())
        assert classify_evidence_integrity(evidence)['assurance'] == 'writer-authenticated'
        raw, artifact = _source_bytes(con, {**evidence, 'provenance': json.loads(evidence['collection_metadata'])})
        assert artifact['artifact_id'] == refs['source_artifact_ref']
        document = json.loads(raw)
        assert base64.b64decode(document['source_response']['body_base64']) == original
        assert document['source_response']['sha256'] == hashlib.sha256(original).hexdigest()
        from lumenis.system.collector.adapters.secondary_collection import validate_public_source_original
        assert validate_public_source_original(raw, artifact['sha256']) == document
        for layer in ('native_record', 'source_raw'):
            for field in ('media_list', 'media_hints', 'media_observation'):
                media_tampered = json.loads(raw)
                record = media_tampered['native_record']
                target = record if layer == 'native_record' else record['source_raw']
                if field == 'media_observation':
                    target[field]['bytes_acquired'] = True
                else:
                    target[field][0]['url'] = 'https://invented.example.test/not-in-DOM.png'
                changed_media = json.dumps(media_tampered).encode()
                with pytest.raises(ValueError, match='PUBLIC_SOURCE_MEDIA_BINDING_CHANGED'):
                    validate_public_source_original(changed_media, hashlib.sha256(changed_media).hexdigest())
        document['body'] += ' unobserved change'
        changed = json.dumps(document).encode()
        with pytest.raises(ValueError, match='PUBLIC_SOURCE_BODY_BINDING_CHANGED'):
            validate_public_source_original(changed, hashlib.sha256(changed).hexdigest())
    # A fresh connection must read the same immutable bytes without a fetch.
    with sqlite3.connect(case['db_path']) as con:
        con.row_factory = sqlite3.Row
        cold_raw, _ = _source_bytes(con, {**evidence, 'provenance': json.loads(evidence['collection_metadata'])})
        assert cold_raw == raw


def test_public_http_manual_request_rechecks_permission_after_document_limiter(collector_case, monkeypatch):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter

    case = collector_case
    case["surface"]._last_action["public_http"] = 0.0
    fetched = []
    adapter = PublicHttpAdapter(fetcher=lambda url: fetched.append(url))
    monkeypatch.setattr(PublicHttpAdapter, "_document_limiter",
                        AdaptiveRateLimiter(base_interval=0, min_interval=0, jitter=False))
    monkeypatch.setattr(case["surface"], "_get_runtime_adapter", lambda *_args: adapter)
    original_guard = case["surface"]._manual_collection_guard
    guard_calls = {"count": 0}

    def revoke_at_fetch_wait(*args, **kwargs):
        guard_calls["count"] += 1
        if guard_calls["count"] == 3:
            return None, {"ok": False, "status": "APPROVAL_REQUIRED",
                          "platform": "public_http", "read_only": True, "external_write": False}
        return original_guard(*args, **kwargs)

    monkeypatch.setattr(case["surface"], "_manual_collection_guard", revoke_at_fetch_wait)
    case["gate"].grant_permission(case["permission"].PermissionLevel.HUMAN_APPROVAL)
    source_url = "https://public.example.test/permission-recheck"
    body = {"operator": "human", "confirm_read_only": True, "platform": "public_http",
            "keyword": source_url, "max_results": 1}

    prepared = case["client"].post(URL, headers=case["focus_headers"],
        json={**body, "action": "prepare"}).get_json()
    confirmed = case["client"].post(URL, headers=case["focus_headers"],
        json={**body, "action": "confirm", "confirmed_resource": prepared["approval_resource"]})
    assert confirmed.get_json()["approved"] is True

    denied = case["client"].post(URL, headers=case["focus_headers"],
        json={**body, "action": "run"})
    assert denied.status_code == 403, denied.get_json()
    assert denied.get_json()["code"] == "COLLECTION_SOURCE_PERMISSION_REVOKED"
    assert guard_calls["count"] == 3
    assert fetched == []
