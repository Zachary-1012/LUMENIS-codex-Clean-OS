"""Exact collected-source permissions on isolated real owners; acquisition is synthetic."""
import json
import sqlite3
import threading

import pytest

from tests.test_collector_comment_pages import comments_case, collect
from tests.test_collector_transaction_truth import collector_case, URL, REGISTERED_NAME
from tests.test_comment_page_source_use import DECLARATION


def public_source(case, monkeypatch):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicResponse
    source_url = 'https://public.example.test/official-source'
    raw = ('<html><head><title>Original public source</title></head><body><main><h1>'
        + REGISTERED_NAME + '</h1><p>Source statements remain observations.</p></main></body></html>').encode()
    response = PublicResponse(url=source_url, requested_url=source_url, content=raw,
                              content_type='text/html', status_code=200)
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda *args: PublicHttpAdapter(fetcher=lambda url: response))
    monkeypatch.setitem(case['surface']._last_action, 'public_http', 0.0)
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    body = {'operator': 'human', 'confirm_read_only': True, 'platform': 'public_http',
            'keyword': source_url, 'max_results': 1}
    def post(action, **extra):
        value = case['client'].post(URL, headers=case['focus_headers'], json={**body, 'action': action, **extra})
        assert value.status_code == 200, value.get_json()
        return value.get_json()
    prepared = post('prepare')
    assert post('confirm', confirmed_resource=prepared['approval_resource'])['approved']
    result = post('run')
    assert result['ok'] and result['public_original_refs']['status'] == 'SAVED'
    return result['public_original_refs']


def confirm_use(case, reference, purpose, *, public):
    name = 'public-sources' if public else 'comments'
    endpoint = '/api/intelligence/library/' + name + '/' + reference.split(':')[1] + '/source-use'
    body = {'mode': 'prepare', 'purpose': purpose, 'rights_declaration': DECLARATION}
    response = case['client'].post(endpoint, headers=case['focus_headers'], json=body)
    assert response.status_code == 200, response.get_json()
    prepared = response.get_json()['result']
    assert prepared['source_use_granted'] is False
    response = case['client'].post(endpoint, headers=case['focus_headers'], json={**body, 'mode': 'confirm',
        'confirmed': True, 'confirmed_resource': prepared['resource']})
    assert response.status_code == 200, response.get_json()
    assert response.get_json()['result']['source_use_granted'] is True
    return {key: prepared[key] for key in ('scope', 'source_evidence_ref', 'source_fingerprint',
                                         'body_sha256', 'source_version', 'purpose')}


def test_public_exact_use_reopens_and_current_source_withdrawal_denies(comments_case, monkeypatch):
    import intelligence_library_api
    from lumenis.shared.database import get_repository
    case = comments_case
    case['client'].application.register_blueprint(intelligence_library_api.intelligence_library_bp)
    original = public_source(case, monkeypatch)
    ref = original['source_evidence_ref']
    con = get_repository().connect()
    try:
        evidence = dict(con.execute('SELECT * FROM app_evidence_records WHERE id=?', (int(ref.split(':')[1]),)).fetchone())
        metadata = json.loads(evidence['collection_metadata'])
        fields = dict(scope=case['scope'], source_evidence_ref=ref, source_fingerprint=metadata['source_fingerprint'],
            body_sha256=metadata['native_source_binding']['body_sha256'], source_version=evidence['version'],
            purpose='research_reference')
        gate = case['gate']
        gate.grant_approval('collector_source_read', granted_by='explicit isolated wildcard counterexample')
        assert not gate.check_collected_public_source_use(case['actor'], **fields, connection=con).allowed
        use = confirm_use(case, ref, 'research_reference', public=True)
        assert gate.check_collected_public_source_use(case['actor'], **use, connection=con).allowed
        assert not gate.check_comment_page_use(case['actor'], **use, connection=con).allowed
        assert not gate.check_collected_public_source_use(case['actor'], **{**use, 'purpose': 'quote_reference'}, connection=con).allowed
        with get_repository().connection() as writer:
            writer.execute('DELETE FROM canonical_data WHERE source_id=?', (str(evidence['asset_id']),))
            writer.commit()
        assert not gate.check_collected_public_source_use(case['actor'], **use, connection=con).allowed
        revoked = gate.revoke_collected_public_source_use(case['actor'], **use, connection=con)
        assert revoked.allowed and revoked.reason == 'PUBLIC_SOURCE_USE_REVOKED_NO_READ_GRANTED'
        assert json.loads(evidence['collection_metadata']) == metadata
    finally:
        con.close()


def test_mixed_source_batch_uses_one_commit_lock_and_revocation_wins_next_read(comments_case, monkeypatch):
    import intelligence_library_api
    from lumenis.shared.database import get_repository
    case = comments_case
    page = collect(case, monkeypatch)
    case['client'].application.register_blueprint(intelligence_library_api.intelligence_library_bp)
    original = public_source(case, monkeypatch)
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    uses = [confirm_use(case, page['page_ref'], 'research_reference', public=False),
            confirm_use(case, original['source_evidence_ref'], 'quote_reference', public=True)]
    gate = case['gate']
    con = get_repository().connect()
    entered, revoked = threading.Event(), threading.Event()
    def withdraw():
        entered.set()
        with get_repository().connection(read_only=True) as reader:
            result = gate.revoke_collected_public_source_use(case['actor'], **uses[1], connection=reader)
        assert result.allowed
        revoked.set()
    thread = threading.Thread(target=withdraw)
    try:
        con.execute('BEGIN IMMEDIATE')
        with gate.collected_source_uses_commit_lease(case['actor'], uses=uses, connection=con) as decisions:
            assert len(decisions) == 2 and all(item.allowed for item in decisions)
            assert decisions[0].resource.startswith('comment-page-use:v1:')
            assert decisions[1].resource.startswith('public-source-use:v1:')
            thread.start()
            assert entered.wait(1) and not revoked.wait(.05)
            con.commit()
        thread.join(timeout=3)
        assert revoked.is_set() and not thread.is_alive()
        con.execute('BEGIN IMMEDIATE')
        with pytest.raises(PermissionError, match='COLLECTED_SOURCE_COMMIT_USE_DENIED'):
            with gate.collected_source_uses_commit_lease(case['actor'], uses=uses, connection=con):
                pytest.fail('withdrawn public source reached commit')
        con.rollback()
    finally:
        con.close()
        if thread.is_alive():
            thread.join(timeout=3)
