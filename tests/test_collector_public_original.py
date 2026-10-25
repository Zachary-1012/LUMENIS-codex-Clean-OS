"""Public response-to-Source custody on disposable owners; acquisition is a fixture."""
import base64
import hashlib
import json
import sqlite3

import pytest

from tests.test_collector_transaction_truth import collector_case, URL, REGISTERED_NAME


def test_manual_public_response_has_reopenable_exact_original(collector_case, monkeypatch, tmp_path):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.importer.documents import _source_bytes
    from lumenis.shared.evidence.store import classify_evidence_integrity
    import shared_artifacts
    case = collector_case
    monkeypatch.setenv('ZBC_ARTIFACT_DIR', str(tmp_path / 'artifacts'))
    shared_artifacts.ensure_artifact_table()
    original = ('<!doctype html><html><head><title>Original source</title></head><body><main><h1>'
        + REGISTERED_NAME + '</h1><p>Native public source statement for current scope.</p></main></body></html>').encode()
    source_url = 'https://public.example.test/official-source'
    response = PublicResponse(url=source_url, requested_url=source_url, content=original,
                              content_type='text/html', status_code=200)
    adapter = PublicHttpAdapter(fetcher=lambda url: response)
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
        document['body'] += ' unobserved change'
        changed = json.dumps(document).encode()
        with pytest.raises(ValueError, match='PUBLIC_SOURCE_BODY_BINDING_CHANGED'):
            validate_public_source_original(changed, hashlib.sha256(changed).hexdigest())
    # A fresh connection must read the same immutable bytes without a fetch.
    with sqlite3.connect(case['db_path']) as con:
        con.row_factory = sqlite3.Row
        cold_raw, _ = _source_bytes(con, {**evidence, 'provenance': json.loads(evidence['collection_metadata'])})
        assert cold_raw == raw
