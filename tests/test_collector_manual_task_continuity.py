"""Manual durable task operations; declared source fixtures and isolated queue only."""
import json
import sqlite3
import time

import pytest

from tests.test_collector_transaction_truth import collector_case as collector_case, URL, REQUEST, GLOBAL_MODE
from tests.test_collector_comment_pages import comments_case as comments_case
from tests.test_collected_media_consumer import media_case as media_case
from tests.test_collector_request_confirmation import selected_provider_case as selected_provider_case


@pytest.fixture
def queue_owner(tmp_path, monkeypatch):
    from lumenis.system.collector.guard import task_queue
    path = tmp_path / 'manual-queue.sqlite3'
    monkeypatch.setattr(task_queue, 'DEFAULT_PATH', str(path))
    return task_queue, path


def request(case, action, *, source=None, **extra):
    body = {'operator': 'human_ui', 'confirm_read_only': True, 'action': action, **extra}
    if source is not None:
        body = {**source, **body}
    return case['client'].post(URL, json=body, headers=case['focus_headers'])


def authorize(case, source):
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    prepared = request(case, 'prepare', source=source).get_json()
    assert isinstance(prepared, dict) and prepared.get('approval_resource'), prepared
    confirmed = request(case, 'confirm', source=source,
        confirmed_resource=prepared['approval_resource']).get_json()
    assert confirmed.get('approved') is True, confirmed


def deny_current_collector_scope(monkeypatch, actions):
    import experience_runtime
    original = experience_runtime._content_project_scope
    def denied(action, **kwargs):
        if (kwargs.get('module') == 'collector' and kwargs.get('permission_required', True)
                and action in actions):
            from shared_artifacts import LocalArtifactError
            raise LocalArtifactError('CONTENT_SCOPE_DENIED')
        return original(action, **kwargs)
    monkeypatch.setattr(experience_runtime, '_content_project_scope', denied)


def test_manual_start_cancel_resume_and_cold_read_preserve_one_source(collector_case, queue_owner):
    case = collector_case
    authorize(case, REQUEST)
    task = request(case, 'start', source=REQUEST, request_id='actual-request-fixture-01').get_json()
    assert task['status'] == 'PENDING' and not case['fetches']
    task_id = task['task_id']
    assert request(case, 'start', source=REQUEST, request_id='actual-request-fixture-01').get_json()['task_id'] == task_id
    assert request(case, 'cancel', task_id=task_id).get_json()['status'] == 'CANCELLED'
    assert request(case, 'step', task_id=task_id).get_json()['status'] == 'CANCELLED'
    assert not case['fetches']
    assert request(case, 'resume', task_id=task_id).get_json()['status'] == 'PENDING'
    result = request(case, 'step', task_id=task_id).get_json()
    assert result['status'] == 'COMPLETED' and result['result']['canonical_synced'] == 1
    assert len(case['fetches']) == 1
    for action in ['status', 'step', 'cancel', 'resume']:
        cold = request(case, action, task_id=task_id).get_json()
        assert cold['status'] == 'COMPLETED' and not cold['network_attempted']
    assert len(case['fetches']) == 1
    other = case['client'].post(URL, json={'operator': 'human_ui', 'confirm_read_only': True,
        'action': 'status', 'task_id': task_id}, headers=GLOBAL_MODE)
    assert other.status_code == 403 and other.get_json()['code'] == 'COLLECTION_TASK_CONTEXT_CHANGED'


def test_public_http_task_cancel_during_document_limit_wait_stops_before_fetch(
        collector_case, queue_owner, monkeypatch):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter

    case = collector_case
    case['surface']._last_action['public_http'] = 0.0
    case['focus_headers'] = GLOBAL_MODE
    source = {**REQUEST, 'platform': 'public_http',
              'keyword': 'https://public.example.test/cancel-before-fetch'}
    fetched = []
    response = PublicResponse(source['keyword'], b'<main>Authorized source</main>',
                              'text/html', 200, source['keyword'])
    adapter = PublicHttpAdapter(fetcher=lambda url: fetched.append(url) or response)
    limiter = AdaptiveRateLimiter(base_interval=0, min_interval=0, jitter=False)
    monkeypatch.setattr(PublicHttpAdapter, '_document_limiter', limiter)
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda *_args: adapter)
    authorize(case, source)
    task_id = request(case, 'start', source=source,
                      request_id='public-http-cancel-before-fetch').get_json()['task_id']

    wait_slot = limiter.wait_slot
    def cancel_after_document_slot(*args, **kwargs):
        result = wait_slot(*args, **kwargs)
        cancelled = request(case, 'cancel', task_id=task_id).get_json()
        assert cancelled['status'] == 'CANCELLED'
        return result
    monkeypatch.setattr(limiter, 'wait_slot', cancel_after_document_slot)

    stopped = request(case, 'step', task_id=task_id).get_json()
    assert stopped['status'] == 'CANCELLED', stopped
    assert not fetched


def test_public_http_detail_cancel_during_document_limit_wait_stops_before_fetch(
        collector_case, queue_owner, monkeypatch):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter

    case = collector_case
    case['surface']._last_action['public_http'] = 0.0
    case['focus_headers'] = GLOBAL_MODE
    source_url = 'https://public.example.test/detail-cancel-before-fetch'
    source = {'platform': 'public_http', 'capability': 'detail',
              'content_id': source_url}
    fetched = []
    response = PublicResponse(source_url, b'<main>Authorized source</main>',
                              'text/html', 200, source_url)
    adapter = PublicHttpAdapter(fetcher=lambda url: fetched.append(url) or response)
    limiter = AdaptiveRateLimiter(base_interval=0, min_interval=0, jitter=False)
    monkeypatch.setattr(PublicHttpAdapter, '_document_limiter', limiter)
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda *_args: adapter)
    authorize(case, source)
    task_id = request(case, 'start', source=source,
                      request_id='public-http-detail-cancel-before-fetch').get_json()['task_id']

    wait_slot = limiter.wait_slot
    def cancel_after_document_slot(*args, **kwargs):
        result = wait_slot(*args, **kwargs)
        cancelled = request(case, 'cancel', task_id=task_id).get_json()
        assert cancelled['status'] == 'CANCELLED'
        return result
    monkeypatch.setattr(limiter, 'wait_slot', cancel_after_document_slot)

    stopped = request(case, 'step', task_id=task_id).get_json()
    assert stopped['status'] == 'CANCELLED', stopped
    assert stopped['network_attempted'] is False
    assert not fetched


@pytest.mark.parametrize(
    ('platform', 'module_name', 'adapter_name', 'source_url'),
    [
        ('public_http', 'public_http', 'PublicHttpAdapter',
         'https://public.example.test/registered-venue-page'),
        ('web_atom', 'web_atom', 'AtomAdapter',
         'https://public.example.test/registered-venue.atom'),
        ('sitemap', 'sitemap', 'SitemapAdapter',
         'https://public.example.test/registered-venue.xml'),
    ],
)
def test_manual_public_source_cancel_before_public_transport(
        collector_case, queue_owner, monkeypatch,
        platform, module_name, adapter_name, source_url):
    import importlib

    from lumenis.system.collector.adapters.public_source import PublicResponse

    case = collector_case
    case['focus_headers'] = GLOBAL_MODE
    source = {**REQUEST, 'platform': platform, 'keyword': source_url}

    adapter_module = importlib.import_module(
        f'lumenis.system.collector.adapters.{module_name}')
    network_requests = []
    response = PublicResponse(
        url=source_url,
        content=b'<feed xmlns="http://www.w3.org/2005/Atom"/>'
        if platform == 'web_atom'
        else b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>',
        content_type='application/xml',
        status_code=200,
    )

    if platform == 'public_http':
        from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
        from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter

        case['surface']._last_action['public_http'] = 0.0
        monkeypatch.setattr(
            PublicHttpAdapter, '_document_limiter',
            AdaptiveRateLimiter(base_interval=0, min_interval=0, jitter=False),
        )

    def public_transport(url, *, check_continue=None, before_fetch=None):
        if check_continue is not None:
            check_continue()
        cancelled = request(case, 'cancel', task_id=task_id).get_json()
        assert cancelled['status'] == 'CANCELLED'
        if before_fetch is not None:
            before_fetch()
        network_requests.append(url)
        return response

    monkeypatch.setattr(adapter_module, 'fetch_public_url', public_transport)
    adapter = getattr(adapter_module, adapter_name)()
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda *_args: adapter)
    authorize(case, source)
    task_id = request(case, 'start', source=source,
                      request_id=f'{platform}-cancel-before-fetch').get_json()['task_id']

    stopped = request(case, 'step', task_id=task_id).get_json()
    assert stopped['status'] == 'CANCELLED', stopped
    assert stopped['network_attempted'] is False
    assert not network_requests


def test_public_http_task_cancel_while_waiting_for_document_slot_is_prompt(
        collector_case, queue_owner, monkeypatch):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter

    case = collector_case
    case['surface']._last_action['public_http'] = 0.0
    source = {**REQUEST, 'platform': 'public_http',
              'keyword': 'https://public.example.test/cancel-during-limiter-wait'}
    fetched = []
    response = PublicResponse(source['keyword'], b'<main>Authorized source</main>',
                              'text/html', 200, source['keyword'])
    adapter = PublicHttpAdapter(fetcher=lambda url: fetched.append(url) or response)
    limiter = AdaptiveRateLimiter(base_interval=0, min_interval=0, jitter=False)
    monkeypatch.setattr(PublicHttpAdapter, '_document_limiter', limiter)
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda *_args: adapter)
    authorize(case, source)
    task_id = request(case, 'start', source=source,
                      request_id='public-http-cancel-during-limiter-wait').get_json()['task_id']

    def cancel_inside_wait(*, sleep, cancelled):
        assert not cancelled()
        cancelled_task = request(case, 'cancel', task_id=task_id).get_json()
        assert cancelled_task['status'] == 'CANCELLED'
        sleep(1.0)

    monkeypatch.setattr(limiter, 'wait_slot', cancel_inside_wait)
    stopped = request(case, 'step', task_id=task_id).get_json()

    assert stopped['status'] == 'CANCELLED', stopped
    assert stopped['network_attempted'] is False
    assert not fetched


def test_public_http_durable_success_reads_saved_source_without_refetch(
        collector_case, queue_owner, monkeypatch, tmp_path):
    from urllib.parse import urlencode

    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter
    import shared_artifacts

    case = collector_case
    monkeypatch.setenv('ZBC_ARTIFACT_DIR', str(tmp_path / 'artifacts'))
    shared_artifacts.ensure_artifact_table()
    source_url = 'https://public.example.test/durable-source'
    original = ("<html><head><title>Public venue update</title></head><body><main><article>"
                "<h1>Registered Harbor Venue Holdings update</h1>"
                "<p>Observed source body preserved for the requested task.</p>"
                "</article></main></body></html>").encode()
    fetched = []
    response = PublicResponse(source_url, original, 'text/html', 200, source_url)
    adapter = PublicHttpAdapter(fetcher=lambda url: fetched.append(url) or response)
    monkeypatch.setattr(PublicHttpAdapter, '_document_limiter',
                        AdaptiveRateLimiter(base_interval=0, min_interval=0, jitter=False))
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda *_args: adapter)
    monkeypatch.setitem(case['surface']._last_action, 'public_http', 0.0)
    source = {**REQUEST, 'platform': 'public_http', 'keyword': source_url}
    authorize(case, source)

    task_id = request(case, 'start', source=source,
                      request_id='public-http-durable-readback').get_json()['task_id']
    completed = request(case, 'step', task_id=task_id).get_json()
    assert completed['status'] == 'COMPLETED'
    assert completed['result']['canonical_synced'] == 1
    assert completed['result']['public_original_refs']['status'] == 'SAVED'
    assert len(fetched) == 1

    item = completed['result']['saved_sources']['items'][0]
    evidence_ref = 'app_evidence_records:' + completed['result']['evidence_ref']
    detail = case['client'].get(
        '/api/experience/cth/platform-collection/results?' + urlencode({
            'evidence_ref': evidence_ref, 'source_id': item['source_id'],
        }), headers=case['focus_headers'])
    assert detail.status_code == 200
    assert 'Observed source body preserved for the requested task.' in detail.get_json()['items'][0]['body']

    cold = request(case, 'status', task_id=task_id).get_json()
    assert cold['status'] == 'COMPLETED' and cold['network_attempted'] is False
    assert len(fetched) == 1


def test_public_http_failure_reason_is_saved_and_read_without_refetch(
        collector_case, queue_owner, monkeypatch):
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicSourceError
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter

    case = collector_case
    source_url = 'https://public.example.test/temporary-dns-failure'
    source = {**REQUEST, 'platform': 'public_http', 'keyword': source_url}
    fetch_calls = []

    def fail_without_network(url):
        fetch_calls.append(url)
        raise PublicSourceError(
            'private resolver diagnostic must not leave the adapter',
            network_attempted=False,
            reason_code='PUBLIC_SOURCE_DNS_UNRESOLVED',
        )

    adapter = PublicHttpAdapter(fetcher=fail_without_network)
    monkeypatch.setattr(PublicHttpAdapter, '_document_limiter',
                        AdaptiveRateLimiter(base_interval=0, min_interval=0, jitter=False))
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda _platform: adapter)
    monkeypatch.setattr(case['surface'], '_adapter_health', lambda _platform, **_kwargs: {
        'status': 'SUCCESS', 'ready': True, 'can_attempt': True,
        'message': 'ok', 'metadata': {},
    })
    monkeypatch.setitem(case['surface']._last_action, 'public_http', 0.0)
    authorize(case, source)

    task_id = request(case, 'start', source=source,
                      request_id='public-http-dns-failure-readback-01').get_json()['task_id']
    pending = request(case, 'step', task_id=task_id).get_json()
    assert pending['result']['status'] == 'PROVIDER_UNAVAILABLE'
    assert pending['result']['reason_code'] == 'PUBLIC_SOURCE_DNS_UNRESOLVED'
    assert pending['result']['error_kind'] == 'PUBLIC_SOURCE_DNS_UNRESOLVED'
    assert pending['result']['recovery_action'] == 'CHECK_NETWORK_AND_RETRY'
    assert pending['result']['network_attempted'] is False
    assert pending['result']['raw_count'] is None
    assert pending['last_attempt']['reason_code'] == 'PUBLIC_SOURCE_DNS_UNRESOLVED'
    assert pending['result_pages'][0]['error_kind'] == 'PUBLIC_SOURCE_DNS_UNRESOLVED'
    assert 'private resolver diagnostic' not in json.dumps(pending, ensure_ascii=False)
    assert len(fetch_calls) == 1

    assert pending['result']['evidence_ref']
    with sqlite3.connect(case['db_path']) as connection:
        evidence = connection.execute(
            'SELECT collection_metadata FROM app_evidence_records WHERE id=?',
            (int(pending['result']['evidence_ref']),),
        ).fetchone()
    assert evidence is not None
    evidence_metadata = json.loads(evidence[0])
    assert evidence_metadata['reason_code'] == 'PUBLIC_SOURCE_DNS_UNRESOLVED'
    assert evidence_metadata['error_kind'] == 'PUBLIC_SOURCE_DNS_UNRESOLVED'
    assert evidence_metadata['recovery_action'] == 'CHECK_NETWORK_AND_RETRY'

    cold = request(case, 'status', task_id=task_id).get_json()
    assert cold['result']['reason_code'] == 'PUBLIC_SOURCE_DNS_UNRESOLVED'
    assert cold['result']['recovery_action'] == 'CHECK_NETWORK_AND_RETRY'
    assert cold['last_attempt']['error_kind'] == 'PUBLIC_SOURCE_DNS_UNRESOLVED'
    assert cold['result_pages'][0]['reason_code'] == 'PUBLIC_SOURCE_DNS_UNRESOLVED'
    assert cold['result']['saved_sources']['reason_code'] == 'PUBLIC_SOURCE_DNS_UNRESOLVED'
    assert cold['result']['saved_sources']['recovery_action'] == 'CHECK_NETWORK_AND_RETRY'
    assert cold['network_attempted'] is False
    assert len(fetch_calls) == 1


def test_revoked_scope_allows_owner_cancel_and_safe_status_only(collector_case, queue_owner, monkeypatch):
    case = collector_case
    authorize(case, REQUEST)
    started = request(case, 'start', source=REQUEST, request_id='revoked-cancel-pending-01').get_json()
    task_id = started['task_id']
    assert started['status'] == 'PENDING' and not case['fetches']
    deny_current_collector_scope(monkeypatch, {'read', 'write'})

    cancelled = request(case, 'cancel', task_id=task_id)
    assert cancelled.status_code == 200
    cancel_receipt = cancelled.get_json()
    assert cancel_receipt['status'] == 'CANCELLED'
    assert cancel_receipt['cancel_applied'] is True
    assert cancel_receipt['result_available'] is False
    assert not {'result', 'request', 'result_pages', 'saved_sources'} & set(cancel_receipt)

    status_response = case['client'].get(
        f'/api/experience/cth/platform-collection/tasks/{task_id}', headers=case['focus_headers'])
    assert status_response.status_code == 200
    safe_status = status_response.get_json()
    assert safe_status['status'] == 'CANCELLED' and safe_status['cancel_requested'] is True
    assert safe_status['result_available'] is False
    assert not {'result', 'request', 'result_pages', 'saved_sources'} & set(safe_status)

    wrong_scope = case['client'].post(URL, json={'operator': 'human_ui', 'confirm_read_only': True,
        'action': 'cancel', 'task_id': task_id}, headers=GLOBAL_MODE)
    assert wrong_scope.status_code == 403
    blocked_step = request(case, 'step', task_id=task_id)
    assert blocked_step.status_code == 403 and not case['fetches']


def test_revoked_scope_status_of_completed_task_never_reads_saved_results(collector_case, queue_owner, monkeypatch):
    case = collector_case
    authorize(case, REQUEST)
    started = request(case, 'start', source=REQUEST, request_id='revoked-status-terminal-01').get_json()
    task_id = started['task_id']
    completed = request(case, 'step', task_id=task_id).get_json()
    assert completed['status'] == 'COMPLETED' and case['fetches']

    def forbidden_result_read(*args, **kwargs):
        raise AssertionError('revoked task status must not read saved source content')
    monkeypatch.setattr(case['surface'], 'read_collected_items', forbidden_result_read)
    deny_current_collector_scope(monkeypatch, {'read', 'write'})

    response = case['client'].get(
        f'/api/experience/cth/platform-collection/tasks/{task_id}', headers=case['focus_headers'])
    assert response.status_code == 200
    safe_status = response.get_json()
    assert safe_status['status'] == 'TERMINAL'
    assert safe_status['result_available'] is False
    assert not {'result', 'request', 'result_pages', 'saved_sources'} & set(safe_status)

    cancelled = request(case, 'cancel', task_id=task_id)
    assert cancelled.status_code == 200 and cancelled.get_json()['status'] == 'TERMINAL'
    assert cancelled.get_json()['result_available'] is False
    assert not {'result', 'request', 'result_pages', 'saved_sources'} & set(cancelled.get_json())


def test_manual_publication_window_survives_confirmation_start_resume_and_result_readback(
        collector_case, queue_owner):
    case = collector_case
    source = {**REQUEST, 'publication_since': '2026-10-01', 'publication_until': '2026-10-01'}
    authorize(case, source)
    started = request(case, 'start', source=source, request_id='publication-window-durable-01').get_json()
    assert started['status'] == 'PENDING' and not case['fetches']
    task_id = started['task_id']
    assert started['request']['publication_since'] == source['publication_since']
    assert started['request']['publication_until'] == source['publication_until']

    assert request(case, 'cancel', task_id=task_id).get_json()['status'] == 'CANCELLED'
    assert request(case, 'step', task_id=task_id).get_json()['status'] == 'CANCELLED'
    resumed = request(case, 'resume', task_id=task_id).get_json()
    assert resumed['status'] == 'PENDING'
    assert resumed['request']['publication_since'] == source['publication_since']
    assert resumed['request']['publication_until'] == source['publication_until']

    changed = request(case, 'step', task_id=task_id, publication_until='2026-09-30')
    assert changed.status_code == 400 and not case['fetches']
    result = request(case, 'step', task_id=task_id).get_json()
    assert result['status'] == 'COMPLETED'
    assert result['request']['publication_since'] == source['publication_since']
    assert result['request']['publication_until'] == source['publication_until']
    assert result['result']['publication_window']['state'] == 'APPLIED'
    assert result['result']['publication_window']['reviews'][0]['within_publication_window'] is True
    assert len(case['fetches']) == 1

    cold = request(case, 'status', task_id=task_id).get_json()
    assert cold['result']['publication_window'] == result['result']['publication_window']
    assert not cold['network_attempted'] and len(case['fetches']) == 1
    with sqlite3.connect(queue_owner[1]) as connection:
        saved = json.loads(connection.execute(
            'SELECT payload FROM tasks WHERE id=?', (task_id,)).fetchone()[0])
    assert saved['binding']['request']['publication_since'] == source['publication_since']
    assert saved['binding']['request']['publication_until'] == source['publication_until']


def test_manual_unknown_publication_time_is_terminal_review_with_saved_original(collector_case, queue_owner,
                                                                                monkeypatch):
    from urllib.parse import urlencode

    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.adapters.web_atom import AtomAdapter
    from tests.test_collector_transaction_truth import _feed

    case = collector_case
    body = _feed(1234).replace(b'<published>2026-10-01T08:00:00Z</published>', b'')
    fetched_urls = []
    def fetch(url):
        fetched_urls.append(url)
        return PublicResponse(url=url, content=body, content_type='application/atom+xml', status_code=200)
    adapter = AtomAdapter(fetcher=fetch)
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda _platform: adapter)
    source = {**REQUEST, 'publication_since': '2026-10-01', 'publication_until': '2026-10-02'}
    authorize(case, source)

    started = request(case, 'start', source=source, request_id='unknown-publication-review-01').get_json()
    assert started['status'] == 'PENDING' and not case['fetches']
    task_id = started['task_id']
    result = request(case, 'step', task_id=task_id).get_json()
    assert result['status'] == 'REVIEW_REQUIRED'
    assert result['queue_status'] == 'done'
    assert result['result']['status'] == 'PARTIAL_COMMITTED'
    assert result['result']['source_status'] == 'PUBLICATION_TIME_REVIEW_REQUIRED'
    assert result['result']['new_collection_required'] is True
    assert result['result']['retry_safe'] is False
    assert result['result']['publication_window']['state'] == 'REVIEW_REQUIRED'
    assert result['result']['publication_window']['publication_since'] == source['publication_since']
    assert result['result']['publication_window']['publication_until'] == source['publication_until']
    assert result['result']['publication_window']['within_window_count'] == 0
    assert result['result']['publication_window']['review_required_count'] == 1

    saved = result['result'].get('saved_sources')
    assert saved is not None, result
    assert saved['items'] == []
    assert saved['review_candidates_state'] == 'COMPLETE'
    assert saved['unassigned_review_candidate_count'] == 1
    candidate = saved['review_candidates'][0]
    assert candidate['review_kind'] == 'PUBLICATION_TIME'
    assert candidate['candidate_id'] == candidate['platform_content_id']
    assert candidate['review_status'] == 'REVIEW_REQUIRED_NATIVE_PUBLICATION_TIME_UNKNOWN'
    assert candidate['publication_time_state'] == 'UNKNOWN'
    assert candidate['native_publication_normalized'] is None
    assert candidate['within_publication_window'] is None
    assert candidate['publication_since'] == source['publication_since']
    assert candidate['publication_until'] == source['publication_until']
    assert candidate['source_scope']['subject_id'] == case['scope']['subject_id']
    assert candidate['canonical_admission'] == 'NOT_ADMITTED'
    assert 'Public source material' in candidate['body_preview']
    assert len(fetched_urls) == 1

    evidence_ref = 'app_evidence_records:' + result['result']['evidence_ref']
    read_url = '/api/experience/cth/platform-collection/results?' + urlencode({
        'evidence_ref': evidence_ref,
        'source_id': candidate['candidate_id'],
    })
    reopened = case['client'].get(read_url, headers=case['focus_headers'])
    assert reopened.status_code == 200
    reopened_body = reopened.get_json()
    assert reopened_body['items'] == []
    assert reopened_body['review_candidates_state'] == 'SELECTED'
    assert reopened_body['unassigned_review_candidate_count'] == 1
    assert reopened_body['requested_publication_window']['publication_since'] == source['publication_since']
    assert reopened_body['requested_publication_window']['publication_until'] == source['publication_until']
    assert reopened_body['scope'] == candidate['source_scope']
    assert len(reopened_body['review_candidates']) == 1
    assert reopened_body['review_candidates'][0]['candidate_id'] == candidate['candidate_id']
    assert reopened_body['review_candidates'][0]['platform_content_id'] == candidate['candidate_id']
    assert reopened_body['review_candidates'][0]['body'] == 'Public source material for Registered Harbor Venue Holdings.'
    assert reopened_body['review_candidates'][0]['source_observation_ref'].startswith(
        evidence_ref + ':inputs.source_observation_records[')

    cold = request(case, 'status', task_id=task_id).get_json()
    assert cold['status'] == 'REVIEW_REQUIRED'
    assert cold['result']['publication_window'] == result['result']['publication_window']
    assert len(fetched_urls) == 1
    with sqlite3.connect(queue_owner[1]) as connection:
        row = connection.execute('SELECT status,last_error,payload FROM tasks WHERE id=?', (task_id,)).fetchone()
    saved_payload = json.loads(row[2])
    assert row[0] == 'done' and row[1] == ''
    assert saved_payload['binding']['request']['publication_since'] == source['publication_since']
    assert saved_payload['binding']['request']['publication_until'] == source['publication_until']
    assert saved_payload['progress']['result']['source_status'] == 'PUBLICATION_TIME_REVIEW_REQUIRED'


def test_provider_over_return_is_rejected_before_source_and_canonical_admission(
        collector_case, queue_owner, monkeypatch):
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus

    case = collector_case
    authorize(case, REQUEST)
    returned = []

    class OverreturningAtom:
        def search(self, keyword, **options):
            returned.append((keyword, options))
            return CollectionResult(CollectionStatus.SUCCESS, 'web_atom', items=[
                {'platform_content_id': 'over-limit-1', 'source_platform': 'web_atom',
                 'title': 'First out-of-contract item', 'content': 'must not be stored',
                 'url': 'https://public.example.test/items/over-limit-1',
                 'publish_datetime': '2026-10-01T08:00:00Z'},
                {'platform_content_id': 'over-limit-2', 'source_platform': 'web_atom',
                 'title': 'Second out-of-contract item', 'content': 'must not be stored either',
                 'url': 'https://public.example.test/items/over-limit-2',
                 'publish_datetime': '2026-10-01T09:00:00Z'},
            ], raw_count=2, metadata={'source': keyword, 'provider': 'isolated-atom-fixture',
                'pagination': {'request_cursor': None, 'next_cursor': 'would-skip-items',
                    'exhausted': False, 'page_complete': True}})

    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda _platform: OverreturningAtom())
    monkeypatch.setattr(case['surface'], '_adapter_health',
        lambda *_args, **_kwargs: {'status': 'SUCCESS', 'can_attempt': True})
    task_id = request(case, 'start', source=REQUEST,
                      request_id='provider-over-return-search-01').get_json()['task_id']
    failed = request(case, 'step', task_id=task_id).get_json()

    assert len(returned) == 1
    assert failed['status'] == 'FAILED'
    assert failed['result']['status'] == 'COLLECT_ERROR'
    assert failed['result']['error_type'] == 'PROVIDER_RESULT_LIMIT_EXCEEDED'
    assert failed['result']['requested_result_limit'] == 1
    assert failed['result']['provider_returned_count'] == 2
    assert failed['result']['saved_sources']['items'] == []
    assert failed['result']['saved_sources']['error_type'] == 'PROVIDER_RESULT_LIMIT_EXCEEDED'
    assert failed['result']['saved_sources']['requested_result_limit'] == 1
    assert failed['result']['saved_sources']['provider_returned_count'] == 2
    assert not failed['continuation_required']
    with sqlite3.connect(case['db_path']) as connection:
        assert connection.execute('SELECT COUNT(*) FROM notes').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM canonical_data').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM platform_contents').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM metric_snapshots').fetchone()[0] == 0
    with sqlite3.connect(queue_owner[1]) as connection:
        payload = json.loads(connection.execute('SELECT payload FROM tasks WHERE id=?', (task_id,)).fetchone()[0])
    assert 'must not be stored' not in json.dumps(payload)
    assert 'would-skip-items' not in json.dumps(payload)


def test_provider_over_return_fails_saved_comment_page_without_refetch(comments_case, queue_owner, monkeypatch):
    case = comments_case
    source = {'operator': 'human_ui', 'confirm_read_only': True, 'capability': 'comments',
              'source_id': case['source_id'], 'max_results': 1, 'include_replies': False}
    authorize(case, source)
    task_id = request(case, 'start', source=source,
                      request_id='provider-over-return-comments-01').get_json()['task_id']
    monkeypatch.setitem(case['entry']._last_action, 'xiaohongshu', 0.0)

    failed = request(case, 'step', task_id=task_id).get_json()
    assert failed['status'] == 'FAILED'
    assert failed['result']['error_type'] == 'PROVIDER_RESULT_LIMIT_EXCEEDED'
    assert failed['result']['requested_result_limit'] == 1
    assert failed['result']['provider_returned_count'] == 2
    assert failed['result']['saved_page']['status'] == 'COLLECT_ERROR'
    assert failed['result']['saved_page']['observed_count'] == 2
    assert failed['result']['saved_page']['comments'] == []
    assert failed['result']['page_ref']
    assert failed['continuation_required'] is False
    assert len(case['calls']) == 1
    cold = request(case, 'status', task_id=task_id).get_json()
    assert cold['status'] == 'FAILED' and not cold['network_attempted']
    assert len(case['calls']) == 1
    with sqlite3.connect(case['db_path']) as connection:
        assert connection.execute('SELECT COUNT(*) FROM note_comments').fetchone()[0] == 0
    with sqlite3.connect(queue_owner[1]) as connection:
        payload = json.loads(connection.execute('SELECT payload FROM tasks WHERE id=?', (task_id,)).fetchone()[0])
    assert 'First source statement' not in json.dumps(payload)
    assert 'Already returned reply' not in json.dumps(payload)


def test_saved_provider_transport_stays_fixed_after_server_default_changes(selected_provider_case,queue_owner,monkeypatch):
    from config import get_config
    case=selected_provider_case
    configured=get_config()
    current=configured.get
    values={'LUMENIS_YOUTUBE_PROVIDER_MODE':'public','LUMENIS_YOUTUBE_PUBLIC_TRANSPORT':'http'}
    def get(key,default=None):
        return values[key] if key in values else current(key,default)
    monkeypatch.setattr(configured,'get',get)
    source={'operator':'human','confirm_read_only':True,'platform':'youtube','keyword':'permitted fixture','max_results':1}
    authorize(case,source)
    started=request(case,'start',source=source,request_id='selection-stable-product-task').get_json()
    assert started['request']['provider_mode']=='public' and started['request']['public_transport']=='http'
    values['LUMENIS_YOUTUBE_PUBLIC_TRANSPORT']='browser'
    task_id=started['task_id']
    rejected=request(case,'step',task_id=task_id,public_transport='browser')
    assert rejected.status_code==400 and not case['selection_calls']
    monkeypatch.setitem(case['surface']._last_action,'youtube',0.0)
    finished=request(case,'step',task_id=task_id).get_json()
    assert finished['status']=='COMPLETED',finished
    assert finished['request']['public_transport']=='http'
    assert all(options.get('public_transport')=='http' for _,options in case['selection_calls'])
    with sqlite3.connect(queue_owner[1]) as connection:
        saved=json.loads(connection.execute('SELECT payload FROM tasks WHERE id=?',(task_id,)).fetchone()[0])
    assert saved['binding']['request']['public_transport']=='http'


def test_committed_source_recovers_after_operational_checkpoint_failure_without_refetch(
        collector_case, queue_owner, monkeypatch):
    case = collector_case
    module, _ = queue_owner
    authorize(case, REQUEST)
    task_id = request(case, 'start', source=REQUEST, request_id='checkpoint-failure-fixture').get_json()['task_id']
    original = module.TaskQueue.save_progress
    def fail_once(self, *args, **kwargs):
        monkeypatch.setattr(module.TaskQueue, 'save_progress', original)
        raise RuntimeError('SIMULATED_QUEUE_FAILURE_AFTER_SOURCE_COMMIT')
    monkeypatch.setattr(module.TaskQueue, 'save_progress', fail_once)
    failed = request(case, 'step', task_id=task_id)
    assert failed.status_code == 503 and len(case['fetches']) == 1
    time.sleep(2.05)
    recovered = request(case, 'step', task_id=task_id).get_json()
    assert recovered['status'] == 'COMPLETED'
    assert recovered['result']['commit_reconciled'] and not recovered['network_attempted']
    assert len(case['fetches']) == 1
    with sqlite3.connect(case['db_path']) as connection:
        assert connection.execute('SELECT COUNT(*) FROM canonical_data').fetchone()[0] == 1


def test_comments_native_pages_continue_after_cancel_without_queue_body_copy(comments_case, queue_owner, monkeypatch):
    case = comments_case
    source = {'operator': 'human_ui', 'confirm_read_only': True, 'capability': 'comments',
              'source_id': case['source_id'], 'max_results': 20, 'include_replies': False}
    authorize(case, source)
    task_id = request(case, 'start', source=source, request_id='native-pages-fixture').get_json()['task_id']
    monkeypatch.setitem(case['entry']._last_action, 'xiaohongshu', 0.0)
    first = request(case, 'step', task_id=task_id).get_json()
    assert first['status'] == 'PENDING' and first['continuation_required']
    assert first['result']['saved_page']['comments'][1]['parent_comment_id'] == 'root-native'
    assert first['result']['reply_coverage_state'] == 'NOT_REQUESTED'
    assert first['result']['saved_page']['requested_reply_scope'] == 'TOP_LEVEL_ONLY'
    request(case, 'cancel', task_id=task_id)
    assert request(case, 'status', task_id=task_id).get_json()['result']['page_ref'] == first['result']['page_ref']
    request(case, 'resume', task_id=task_id)
    monkeypatch.setitem(case['entry']._last_action, 'xiaohongshu', 0.0)
    second = request(case, 'step', task_id=task_id).get_json()
    assert second['status'] == 'COMPLETED' and not second['continuation_required']
    assert len(case['calls']) == 2 and case['calls'][1]['cursor'] == {'page': 2}
    assert [page['page_ref'] for page in second['result_pages']] == [
        first['result']['page_ref'], second['result']['page_ref']]
    older = case['client'].get(URL.replace('/search', '/tasks/') + str(task_id),
        headers=case['focus_headers'], query_string={'before_page': 2}).get_json()
    assert [page['page_ref'] for page in older['result_pages']] == [first['result']['page_ref']]
    with sqlite3.connect(queue_owner[1]) as connection:
        payload = connection.execute('SELECT payload FROM tasks WHERE id=?', (task_id,)).fetchone()[0]
        assert 'First source statement' not in payload and 'Second page source statement' not in payload
        assert 'comments' not in (json.loads(payload).get('progress', {}).get('result') or {})


def test_history_filters_owner_and_scope_before_pagination_without_fetch(collector_case, queue_owner):
    case = collector_case
    authorize(case, REQUEST)
    ids = [request(case, 'start', source=REQUEST, request_id=f'history-request-{n}').get_json()['task_id']
           for n in range(3)]
    module, _ = queue_owner
    queue = module.TaskQueue()
    original = queue.get(ids[0])['payload']['binding']
    queue.enqueue_once('collector_manual_request', {'binding': {**original,
        'identity': {'principal_ref': 'a-different-workspace'}}, 'progress': {}}, 'different-owner')
    queue.close()
    endpoint = URL.replace('/search', '/tasks')
    first = case['client'].get(endpoint, headers=case['focus_headers'], query_string={'limit': 2}).get_json()
    assert [row['task_id'] for row in first['tasks']] == ids[:0:-1]
    second = case['client'].get(endpoint, headers=case['focus_headers'],
        query_string={'limit': 2, 'before': first['next_cursor']}).get_json()
    assert [row['task_id'] for row in second['tasks']] == ids[:1] and second['next_cursor'] is None
    assert case['client'].get(endpoint, headers=GLOBAL_MODE).get_json()['tasks'] == []
    assert case['client'].get(endpoint, headers=case['focus_headers'], query_string={'limit': 0}).status_code == 400
    assert not case['fetches']


def test_manual_resume_preserves_cooldown_and_recovers_exhausted_attempt(collector_case, queue_owner):
    case = collector_case
    module, _ = queue_owner
    authorize(case, REQUEST)
    task_id = request(case, 'start', source=REQUEST, request_id='bounded-retry-cooldown').get_json()['task_id']
    queue = module.TaskQueue()
    claimed = queue.dequeue(worker_id='bounded-retry', lease_owner='bounded-retry', task_id=task_id)
    receipt = {key: claimed[key] for key in ('run_id', 'worker_id', 'lease_owner')}
    queue.yield_pending(task_id, **receipt, delay=120)
    request(case, 'cancel', task_id=task_id)
    resumed = request(case, 'resume', task_id=task_id).get_json()
    assert resumed['retry_after_seconds'] > 100
    assert request(case, 'step', task_id=task_id).get_json()['status'] == 'PENDING'
    assert not case['fetches']
    with queue._conn:
        queue._conn.execute("UPDATE tasks SET scheduled_at=0 WHERE id=?", (task_id,))
    claimed = queue.dequeue(worker_id='retry-exhausted', lease_owner='retry-exhausted', task_id=task_id)
    receipt = {key: claimed[key] for key in ('run_id', 'worker_id', 'lease_owner')}
    queue.fail(task_id, 'SOURCE_TRANSPORT_FAILED', retryable=False, **receipt)
    assert request(case, 'status', task_id=task_id).get_json()['status'] == 'FAILED'
    assert request(case, 'resume', task_id=task_id).get_json()['status'] == 'PENDING'
    assert not queue.ack(task_id, **receipt)
    queue.close()
    result = request(case, 'step', task_id=task_id).get_json()
    assert result['status'] == 'COMPLETED' and len(case['fetches']) == 1


def test_saved_body_and_native_metrics_survive_new_capture(collector_case, queue_owner):
    case = collector_case
    authorize(case, REQUEST)
    first_id = request(case, 'start', source=REQUEST, request_id='version-first-capture').get_json()['task_id']
    first = request(case, 'step', task_id=first_id).get_json()
    source = first['result']['saved_sources']['items'][0]
    endpoint = URL.replace('/search', '/results')
    args = {'evidence_ref': source['evidence_ref'], 'source_id': source['source_id']}
    original = case['client'].get(endpoint, headers=case['focus_headers'], query_string=args).get_json()['items'][0]
    assert original['body'] and original['source_version_state'] == 'CURRENT_SOURCE_VERSION'
    case['views']['value'] = 3456
    case['reset_rate_limit']()
    second_id = request(case, 'start', source=REQUEST, request_id='version-second-capture').get_json()['task_id']
    second = request(case, 'step', task_id=second_id).get_json()
    assert second['result']['saved_sources']['items'][0]['metrics']['views'] == 3456
    reopened = case['client'].get(endpoint, headers=case['focus_headers'], query_string=args).get_json()['items'][0]
    assert reopened['body'] == original['body'] and reopened['metrics']['views'] == 1234
    assert reopened['source_version_state'] == 'RECORDED_SOURCE_VERSION'
    assert case['client'].get(endpoint, headers=case['focus_headers'],
        query_string={**args, 'source_id': 'not-in-this-capture'}).status_code == 400
    assert len(case['fetches']) == 2


def test_cooldown_keeps_saved_page_and_native_continuation(comments_case, queue_owner, monkeypatch):
    case = comments_case
    source = {'capability': 'comments', 'source_id': case['source_id'], 'max_results': 20,
              'include_replies': False}
    authorize(case, source)
    task_id = request(case, 'start', source=source, request_id='cooldown-native-pages').get_json()['task_id']
    monkeypatch.setitem(case['entry']._last_action, 'xiaohongshu', 0.0)
    first = request(case, 'step', task_id=task_id).get_json()
    real_collect = case['entry'].collect_comments
    monkeypatch.setattr(case['entry'], 'collect_comments', lambda *a, **k: {
        'ok': False, 'status': 'RATE_LIMITED', 'retry_after_seconds': 120, 'network_attempted': False})
    blocked = request(case, 'step', task_id=task_id).get_json()
    assert blocked['status'] == 'WAITING_USER' and blocked['retry_after_seconds'] > 110
    assert blocked['last_attempt']['status'] == 'RATE_LIMITED'
    assert blocked['result']['page_ref'] == first['result']['page_ref']
    queue = queue_owner[0].TaskQueue()
    row = queue.get(task_id)
    assert row['payload']['progress']['continuation']
    queue.close()
    monkeypatch.setattr(case['entry'], 'collect_comments', real_collect)
    still_waiting = request(case, 'step', task_id=task_id).get_json()
    assert still_waiting['result']['page_ref'] == first['result']['page_ref'] and len(case['calls']) == 1


def test_media_task_real_artifact_range_reopen_and_cancel_without_refetch(media_case, queue_owner):
    case = media_case
    source = {'capability': 'media', 'source_id': case['source_id'],
              'source_evidence_ref': case['media_arguments']['source_evidence_ref']}
    authorize(case, source)
    start = request(case, 'start', source=source, request_id='media-durable-product-request').get_json()
    task_id = start['task_id']
    assert request(case, 'cancel', task_id=task_id).get_json()['status'] == 'CANCELLED'
    assert request(case, 'step', task_id=task_id).get_json()['status'] == 'CANCELLED'
    assert not case['media_calls']
    assert request(case, 'resume', task_id=task_id).get_json()['status'] == 'PENDING'
    task = request(case, 'step', task_id=task_id).get_json()
    assert task['status'] == 'COMPLETED', task
    assert task['result']['auto_continue'] is False
    assert task['result']['pending_positions'] == []
    assert task['result']['failed_positions'] == []
    assert task['result']['intervention_required'] is False
    media = task['result']['saved_media'][0]
    assert media['original']['size_bytes'] == len(case['media_raw'])
    assert len(case['media_calls']) == 1
    reopened = request(case, 'status', task_id=task_id).get_json()
    assert reopened['result']['saved_media'][0]['manifest_sha256'] == media['manifest_sha256']
    endpoint = URL.replace('/search', f'/tasks/{task_id}/media/{media["evidence_ref"].split(":")[1]}')
    query = {'sha256': media['original']['sha256']}
    response = case['client'].get(endpoint, headers={**case['focus_headers'], 'Range': 'bytes=5-14'}, query_string=query)
    assert response.status_code == 206 and response.data == case['media_raw'][5:15]
    assert response.headers['Content-Range'] == f'bytes 5-14/{len(case["media_raw"])}'
    assert case['client'].head(endpoint, headers=case['focus_headers'], query_string=query).status_code == 200
    assert case['client'].get(endpoint, headers=GLOBAL_MODE, query_string=query).status_code == 403
    assert case['client'].get(endpoint, headers=case['focus_headers'], query_string={'sha256': '0'*64}).status_code == 400
    assert len(case['media_calls']) == 1


def test_media_approval_revoked_after_original_save_waits_and_resumes_without_download(
        media_case, queue_owner, monkeypatch):
    case = media_case
    owner = case['media_owner']
    source = {'capability': 'media', 'source_id': case['source_id'],
              'source_evidence_ref': case['media_arguments']['source_evidence_ref']}
    authorize(case, source)
    task_id = request(case, 'start', source=source,
        request_id='media-permission-expiry-recovery').get_json()['task_id']
    inspect = owner._inspect_collected_media

    def revoke_after_original(*args, **kwargs):
        for token, approval in list(case['gate']._approvals.items()):
            if approval.resource.startswith('collector-media-use:v1:'):
                case['gate'].revoke_approval(token)
        monkeypatch.setattr(owner, '_inspect_collected_media', inspect)
        return inspect(*args, **kwargs)

    monkeypatch.setattr(owner, '_inspect_collected_media', revoke_after_original)
    waiting = request(case, 'step', task_id=task_id).get_json()
    assert waiting['status'] == 'WAITING_USER', waiting
    assert waiting['last_attempt']['status'] == 'APPROVAL_REQUIRED'
    assert waiting['next_action'] == 'confirm' and not waiting['auto_continue']
    assert len(case['media_calls']) == 1
    assert request(case, 'status', task_id=task_id).get_json()['status'] == 'WAITING_USER'
    denied = request(case, 'step', task_id=task_id).get_json()
    assert denied['status'] == 'WAITING_USER' and len(case['media_calls']) == 1
    authorize(case, source)
    recovered = request(case, 'step', task_id=task_id).get_json()
    assert recovered['status'] == 'COMPLETED', recovered
    assert recovered['result']['saved_media'][0]['original']['size_bytes'] == len(case['media_raw'])
    assert len(case['media_calls']) == 1
