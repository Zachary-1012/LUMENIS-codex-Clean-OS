"""Durable V4 caller integration with owned Atom fixtures, not live-source acceptance."""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from flask import Flask
from tests.test_collector_transaction_truth import collector_case, SOURCE_URL, _pipeline_counts


@pytest.fixture
def durable_case(collector_case, tmp_path, monkeypatch):
    case = collector_case
    from lumenis.auth.models import V4_TABLES_SQL
    from lumenis.auth import service as auth
    from lumenis.adapters import collector_service as service
    from lumenis.system.collector.guard import task_queue
    from lumenis.blueprint import create_v4_blueprint
    with sqlite3.connect(case['db_path']) as conn:
        conn.executescript(V4_TABLES_SQL)
        for user_id in (101, 102):
            conn.execute("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES(?,?,?,'owner','active')",
                         (user_id, 'owned-test-' + str(user_id), 'unusable-test-password'))
            conn.execute("INSERT INTO v4_sessions(user_id,token,expires_at) VALUES(?,?,'2099-01-01 00:00:00')",
                         (user_id, 'owned-session-' + str(user_id)))
    monkeypatch.setattr(auth, '_initialized', True)
    queue_path = tmp_path / 'queue' / 'task_queue.db'
    monkeypatch.setattr(task_queue, 'DEFAULT_PATH', str(queue_path))
    submitted = []
    monkeypatch.setattr(service._job_pool, 'submit', lambda fn, *args: submitted.append((fn, args)))
    app = Flask(__name__)
    app.config['LUMENIS_OPEN_WORKSPACE'] = False
    app.register_blueprint(create_v4_blueprint())
    case.update(client=app.test_client(), service=service, submitted=submitted,
                queue_path=queue_path, headers={**case['focus_headers'], 'Authorization': 'Bearer owned-session-101'})
    return case


def submit(case):
    case['reset_rate_limit']()
    return case['client'].post('/v4/adapters/collect', headers=case['headers'], json={
        'keyword': SOURCE_URL, 'platforms': ['web_atom'], 'max_results': 1, 'confirm_read_only': True})


def approved_task(case):
    response = submit(case)
    assert response.status_code == 403, response.get_json()
    assert response.get_json()['status'] == 'APPROVAL_REQUIRED'
    assert not case['fetches'] and not case['submitted']
    case['gate'].grant_approval('data_import', resource=response.get_json()['approval_resource'],
                                granted_by='explicit isolated fixture integration')
    response = submit(case)
    assert response.status_code == 200, response.get_json()
    return response.get_json()['task_id']


def assert_committed_once(case):
    assert _pipeline_counts(case['db_path']) == {
        'notes': 1, 'canonical_data': 1, 'app_evidence_records': 2,
        'platform_contents': 1, 'metric_snapshots': 1}
    with sqlite3.connect(case['db_path']) as conn:
        assert conn.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTOR_TASK_COMMIT'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id!='COLLECTOR_TASK_COMMIT'").fetchone()[0] == 1


def test_v4_real_permission_transaction_persists_and_reopens_without_reexecution(durable_case):
    case = durable_case
    task_id = approved_task(case)
    pending = case['service'].get_task(task_id)
    assert pending['queue_status'] == 'pending' and pending['success'] is False
    case['service']._job(task_id)
    completed = case['service'].get_task(task_id)
    assert completed['success'] is True, completed
    assert completed['per_platform']['web_atom']['evidence_recorded'] is True
    assert_committed_once(case)
    assert len(case['fetches']) == 1
    # A genuinely new Python process reopens the operational store, no memory cache.
    env = {**os.environ, 'ZBC_DATA_DIR': str(case['queue_path'].parent),
           'ZBC_DB_PATH': str(case['db_path'])}
    code = "from lumenis.adapters.collector_service import get_task; import json; print(json.dumps(get_task(" + repr(task_id) + ")))"
    reopened = subprocess.check_output([sys.executable, '-c', code], env=env, text=True)
    assert json.loads(reopened.splitlines()[-1]) == completed
    response = case['client'].post('/v4/adapters/task/' + task_id + '/resume',
                                  headers=case['headers'], json={'confirm_read_only': True})
    assert response.status_code == 200 and response.get_json()['task'] == completed
    case['service']._job(task_id)
    assert len(case['fetches']) == 1
    assert len(case['submitted']) == 1
    foreign = {**case['headers'], 'Authorization': 'Bearer owned-session-102'}
    assert case['client'].get('/v4/adapters/task/' + task_id, headers=foreign).status_code == 404
    assert case['client'].post('/v4/adapters/task/' + task_id + '/resume',
        headers=foreign, json={'confirm_read_only': True}).status_code == 404


def test_v4_crashed_attempt_recovery_keeps_checkpoint_and_fences_old_worker(durable_case):
    case = durable_case
    task_id = approved_task(case)
    queue = case['service']._queue()
    identity = int(task_id[3:])
    crashed = queue.dequeue(worker_id='crashed', lease_owner='crashed', task_id=identity)
    receipt = {key: crashed[key] for key in ('run_id', 'worker_id', 'lease_owner')}
    assert queue.save_progress(identity, {'per_platform': {}}, **receipt)
    with queue._conn:
        queue._conn.execute('UPDATE tasks SET last_heartbeat_at=0 WHERE id=?', (identity,))
    queue.close()
    response = case['client'].post('/v4/adapters/task/' + task_id + '/resume',
        headers=case['headers'], json={'confirm_read_only': True})
    assert response.status_code == 200, response.get_json()
    queue = case['service']._queue()
    assert not queue.ack(identity, **receipt)
    assert not queue.save_progress(identity, {'forged': True}, **receipt)
    with queue._conn:
        queue._conn.execute('UPDATE tasks SET scheduled_at=0 WHERE id=?', (identity,))
    queue.close()
    case['service']._job(task_id)
    assert case['service'].get_task(task_id)['success'] is True
    assert len(case['fetches']) == 1


def test_v4_revoked_approval_stays_failed_without_network_or_business_writes(durable_case):
    case = durable_case
    task_id = approved_task(case)
    # Disable this real persisted account after submission. Worker must recheck it.
    with sqlite3.connect(case['db_path']) as conn:
        conn.execute("UPDATE v4_users SET status='disabled' WHERE id=101")
    case['service']._job(task_id)
    task = case['service'].get_task(task_id)
    assert task['success'] is False and task['resume_required'] is True
    assert task['per_platform']['web_atom']['state'] == 'SCOPE_UNAUTHORIZED'
    assert not case['fetches']
    assert all(n == 0 for n in _pipeline_counts(case['db_path']).values())


def test_v4_normalized_request_approval_matches_execution(durable_case):
    case = durable_case
    headers = case['headers']
    body = {'keyword': '  ' + SOURCE_URL + '  ', 'platforms': ['web_atom'],
            'max_results': '1', 'confirm_read_only': True}
    response = case['client'].post('/v4/adapters/collect', headers=headers, json=body)
    assert response.status_code == 403
    case['gate'].grant_approval('data_import', resource=response.get_json()['approval_resource'],
                               granted_by='explicit isolated normalized request')
    response = case['client'].post('/v4/adapters/collect', headers=headers, json=body)
    assert response.status_code == 200, response.get_json()
    task_id = response.get_json()['task_id']
    case['service']._job(task_id)
    assert case['service'].get_task(task_id)['success'] is True
    assert case['fetches'] == [SOURCE_URL]


def test_reclaimed_worker_cannot_commit_collected_business_truth(durable_case, monkeypatch):
    case = durable_case
    task_id = approved_task(case)
    identity = int(task_id[3:])
    adapter = case['surface']._get_runtime_adapter('web_atom')
    original_fetch = adapter.fetcher
    def fetch_then_reclaim(url):
        result = original_fetch(url)
        other = case['service']._queue()
        with other._conn:
            other._conn.execute('UPDATE tasks SET last_heartbeat_at=0 WHERE id=?', (identity,))
        assert other.reap_stale(1, task_id=identity) == [identity]
        other.close()
        return result
    monkeypatch.setattr(adapter, 'fetcher', fetch_then_reclaim)
    case['service']._job(task_id)
    assert len(case['fetches']) == 1
    assert all(n == 0 for n in _pipeline_counts(case['db_path']).values())
    assert case['service'].get_task(task_id)['success'] is False


def test_live_long_collection_renews_lease_before_reaper(durable_case, monkeypatch):
    import time
    from types import SimpleNamespace
    from lumenis.system.collector.guard import task_queue
    case = durable_case
    clock = {'now': time.time()}
    monkeypatch.setattr(task_queue, 'time', SimpleNamespace(time=lambda: clock['now']))
    task_id = approved_task(case)
    adapter = case['surface']._get_runtime_adapter('web_atom')
    original_fetch = adapter.fetcher
    def delayed_owned_transport(url):
        # Simulate >120s logical acquisition while exercising the actual 15s
        # renewal thread. No network, no patched heartbeat or lease result.
        clock['now'] += 200
        time.sleep(16)
        other = case['service']._queue()
        assert other.reap_stale(120, task_id=int(task_id[3:])) == []
        other.close()
        return original_fetch(url)
    monkeypatch.setattr(adapter, 'fetcher', delayed_owned_transport)
    case['service']._job(task_id)
    assert case['service'].get_task(task_id)['success'] is True

@pytest.mark.parametrize('confirmation', [1, 1.0, 'true'])
def test_resume_requires_literal_boolean(durable_case, confirmation):
    case = durable_case
    task_id = approved_task(case)
    response = case['client'].post('/v4/adapters/task/' + task_id + '/resume',
        headers=case['headers'], json={'confirm_read_only': confirmation})
    assert response.status_code == 400
    assert not case['fetches']


def test_process_death_after_business_commit_recovers_signed_receipt_without_fetch(durable_case, monkeypatch):
    """Actual child exits at queue checkpoint; new process reconciles committed SQL."""
    import multiprocessing
    from lumenis.system.collector.guard.task_queue import TaskQueue
    case = durable_case
    task_id = approved_task(case)
    def crash_after_commit():
        TaskQueue.save_progress = lambda *args, **kwargs: os._exit(86)
        case['service']._job(task_id)
    process = multiprocessing.get_context('fork').Process(target=crash_after_commit)
    process.start(); process.join(20)
    assert process.exitcode == 86
    assert_committed_once(case)
    queue = case['service']._queue()
    row = queue.get(int(task_id[3:]))
    assert row['status'] == 'running' and not row['payload'].get('progress')
    with queue._conn:
        queue._conn.execute('UPDATE tasks SET last_heartbeat_at=0 WHERE id=?', (row['id'],))
    queue.reap_stale(120, task_id=row['id'])
    with queue._conn:
        queue._conn.execute('UPDATE tasks SET scheduled_at=0 WHERE id=?', (row['id'],))
    queue.close()
    script = """
import json
from lumenis.adapters import collector_service as service
from lumenis.system.collector.adapters import secondary_collection as entry
from lumenis.system.collector.guard import task_queue
from lumenis.system import security
from lumenis.system.security import permission
task_queue.DEFAULT_PATH = QUEUE_PATH
gate = permission.PermissionGate()
gate.grant_permission(permission.PermissionLevel.COMMIT)
permission.get_permission_gate = security.get_permission_gate = lambda: gate
queue = service._queue(); row = queue.get(int(TASK_ID[3:])); queue.close()
payload = row['payload']
_, denial = entry._manual_collection_guard({'id': payload['actor_id']}, payload['scope'],
    'web_atom', payload['keyword'], payload['max_results'])
if denial is not None:
    assert denial['status'] == 'APPROVAL_REQUIRED', denial
    gate.grant_approval('data_import', resource=denial['approval_resource'],
                       granted_by='explicit isolated restart verification')
entry._get_runtime_adapter = lambda *args: (_ for _ in ()).throw(AssertionError('receipt recovery fetched source'))
service._job(TASK_ID)
completed = service.get_task(TASK_ID)
assert completed['success'] is True, completed
assert completed['per_platform']['web_atom']['commit_reconciled'] is True
print(json.dumps(completed))
"""
    script = 'QUEUE_PATH=' + repr(str(case['queue_path'])) + '\nTASK_ID=' + repr(task_id) + '\n' + script
    env = {**os.environ, 'ZBC_DB_PATH': str(case['db_path']),
           'ZBC_DATA_DIR': str(case['queue_path'].parent)}
    recovered = subprocess.check_output([sys.executable, '-c', script], env=env, text=True)
    assert json.loads(recovered.splitlines()[-1])['success'] is True
    assert_committed_once(case)
    assert case['service'].get_task(task_id)['success'] is True


def test_tampered_commit_receipt_does_not_refetch(durable_case):
    case = durable_case
    task_id = approved_task(case)
    case['service']._job(task_id)
    queue = case['service']._queue()
    task = queue.get(int(task_id[3:])); queue.close()
    with sqlite3.connect(case['db_path']) as conn:
        conn.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE feature_id='COLLECTOR_TASK_COMMIT'")
    result = case['surface'].collect_search('web_atom', SOURCE_URL, max_results=1,
        actor={'id': 101}, scope=case['scope'],
        operation_key=task['payload']['operation_id'] + ':web_atom')
    assert result['status'] == 'COLLECTION_COMMIT_UNVERIFIED'
    assert result['network_attempted'] is False
    assert len(case['fetches']) == 1

@pytest.mark.parametrize('failure', ['NETWORK_ERROR', 'NEED_VERIFY'])
def test_uncommitted_failure_does_not_poison_operation_receipt(durable_case, monkeypatch, failure):
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    case = durable_case
    task_id = approved_task(case)
    actual = case['surface']._get_runtime_adapter('web_atom')
    attempts = []
    class TransientTransport:
        def health_check(self, **kwargs):
            return CollectionResult(CollectionStatus.SUCCESS, 'web_atom')
        def search(self, *args, **kwargs):
            attempts.append(1)
            if len(attempts) == 1:
                case['reset_rate_limit']()
                return CollectionResult(failure, 'web_atom', raw_count=0)
            return actual.search(*args, **kwargs)
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda _: TransientTransport())
    case['service']._job(task_id)
    if failure == 'NEED_VERIFY':
        assert case['service'].get_task(task_id)['success'] is False
        with sqlite3.connect(case['db_path']) as conn:
            assert conn.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTOR_TASK_COMMIT'").fetchone()[0] == 0
        queue = case['service']._queue()
        with queue._conn:
            queue._conn.execute('UPDATE tasks SET scheduled_at=0 WHERE id=?', (int(task_id[3:]),))
        queue.close()
        case['reset_rate_limit']()
        case['service']._job(task_id)
    assert case['service'].get_task(task_id)['success'] is True
    assert len(attempts) == 2 and len(case['fetches']) == 1
    with sqlite3.connect(case['db_path']) as conn:
        assert conn.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTOR_TASK_COMMIT'").fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM canonical_data').fetchone()[0] == 1


def test_receipt_recovery_rechecks_source_evidence_and_actor(durable_case):
    case = durable_case
    task_id = approved_task(case)
    case['service']._job(task_id)
    queue = case['service']._queue(); task = queue.get(int(task_id[3:])); queue.close()
    kwargs = dict(max_results=1, actor={'id': 101}, scope=case['scope'],
                  operation_key=task['payload']['operation_id'] + ':web_atom')
    with sqlite3.connect(case['db_path']) as conn:
        conn.execute("UPDATE v4_users SET status='disabled' WHERE id=101")
    denied = case['surface'].collect_search('web_atom', SOURCE_URL, **kwargs)
    assert denied['ok'] is False and denied.get('commit_reconciled') is not True
    with sqlite3.connect(case['db_path']) as conn:
        conn.execute("UPDATE v4_users SET status='active' WHERE id=101")
        conn.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE feature_id!='COLLECTOR_TASK_COMMIT'")
    denied = case['surface'].collect_search('web_atom', SOURCE_URL, **kwargs)
    assert denied['status'] == 'COLLECTION_COMMIT_UNVERIFIED'
    assert len(case['fetches']) == 1


def test_legacy_task_without_operation_identity_is_unknown_not_reexecuted(durable_case):
    case = durable_case
    task_id = approved_task(case)
    queue = case['service']._queue()
    task = queue.get(int(task_id[3:]))
    payload = task['payload']; payload.pop('operation_id')
    with queue._conn:
        queue._conn.execute('UPDATE tasks SET payload=? WHERE id=?', (json.dumps(payload), task['id']))
    queue.close()
    case['service']._job(task_id)
    result = case['service'].get_task(task_id)
    assert result['per_platform']['web_atom']['state'] == 'LEGACY_COLLECTION_COMMIT_UNKNOWN'
    assert result['new_collection_required'] is True and result['resume_required'] is False
    assert not case['fetches']
    before = len(case['submitted'])
    resumed = case['client'].post('/v4/adapters/task/' + task_id + '/resume',
        headers=case['headers'], json={'confirm_read_only': True})
    assert resumed.status_code == 200
    assert len(case['submitted']) == before


@pytest.mark.parametrize("transient_connection_error", [False, True])
def test_keyless_keyword_search_uses_existing_rss_parser_and_canonical_chain(durable_case, monkeypatch, transient_connection_error):
    """Owned RSS bytes test keyword discovery, not a user-supplied feed URL."""
    from tests.test_collector_transaction_truth import REGISTERED_NAME
    from lumenis.system.collector.adapters.web_rss import WebRSSAdapter
    from lumenis.system.collector.adapters import public_source
    case = durable_case
    requests = []
    class Response:
        status_code = 200
        content = ('<rss><channel><item><title>' + REGISTERED_NAME + ' service update</title>'
            '<link>https://public.example.test/owned-news-1</link>'
            '<source>Owned synthetic publisher</source>'
            '<pubDate>Thu, 01 Oct 2026 08:00:00 GMT</pubDate>'
            '</item></channel></rss>').encode()
    def owned_transport(url, **kwargs):
        requests.append(url)
        assert url.startswith('https://news.google.com/rss/search?q=')
        if transient_connection_error and len(requests) == 1:
            monkeypatch.setitem(case['surface']._last_action, 'web_rss', 0.0)
            raise ConnectionError('owned transient fixture')
        return public_source.PublicResponse(url=url, content=Response.content,
            content_type="application/rss+xml", status_code=200)
    monkeypatch.setattr(public_source, 'fetch_public_url', owned_transport)
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda _: WebRSSAdapter())
    import time
    monkeypatch.setitem(case['surface']._last_action, 'web_rss',
                        time.monotonic() if transient_connection_error else 0.0)
    keyword = REGISTERED_NAME + ' service'
    body = {'keyword': keyword, 'platforms': ['web_rss'], 'max_results': 1, 'confirm_read_only': True}
    response = case['client'].post('/v4/adapters/collect', headers=case['headers'], json=body)
    assert response.status_code == 403 and response.get_json()['status'] == 'APPROVAL_REQUIRED'
    case['gate'].grant_approval('data_import', resource=response.get_json()['approval_resource'],
                               granted_by='explicit owned discovery fixture')
    response = case['client'].post('/v4/adapters/collect', headers=case['headers'], json=body)
    assert response.status_code == 200
    task_id = response.get_json()['task_id']
    case['service']._job(task_id)
    result = case['service'].get_task(task_id)
    assert result['success'] is True, (result, requests)
    assert len(requests) == (2 if transient_connection_error else 1)
    assert result['attempts'] == (1 if transient_connection_error else 0)
    counts = _pipeline_counts(case['db_path'])
    assert counts == {'notes': 1, 'canonical_data': 1, 'app_evidence_records': 3 if transient_connection_error else 2,
                      'platform_contents': 1, 'metric_snapshots': 1}
    with sqlite3.connect(case['db_path']) as conn:
        title, content, url = conn.execute('SELECT title,content,url FROM canonical_data').fetchone()
        assert REGISTERED_NAME in title and url == 'https://public.example.test/owned-news-1'
        # A discovery card is never fabricated into a full-text article.
        assert content in ('', None)


def test_expired_task_stops_without_fetch_and_preserves_failure_truth(durable_case):
    case = durable_case
    task_id = approved_task(case)
    queue = case['service']._queue(); task = queue.get(int(task_id[3:]))
    payload = task['payload']; payload['deadline_at'] = 1
    with queue._conn:
        queue._conn.execute('UPDATE tasks SET payload=? WHERE id=?', (json.dumps(payload), task['id']))
    queue.close()
    case['service']._job(task_id)
    result = case['service'].get_task(task_id)
    assert result['queue_status'] == 'failed' and result['success'] is False
    assert result['per_platform']['web_atom']['state'] == 'TASK_DEADLINE_EXCEEDED'
    assert not case['fetches']


def test_revoke_during_local_throttle_blocks_next_network_attempt(durable_case, monkeypatch):
    import time
    from lumenis.system.collector.guard.task_queue import TaskQueue
    case = durable_case
    task_id = approved_task(case)
    monkeypatch.setitem(case['surface']._last_action, 'web_atom', time.monotonic())
    real_defer = TaskQueue.defer
    def revoke_then_defer(self, *args, **kwargs):
        with sqlite3.connect(case['db_path']) as conn:
            conn.execute("UPDATE v4_users SET status='disabled' WHERE id=101")
        return real_defer(self, *args, **kwargs)
    monkeypatch.setattr(TaskQueue, 'defer', revoke_then_defer)
    case['service']._job(task_id)
    result = case['service'].get_task(task_id)
    assert result['success'] is False
    assert result['per_platform']['web_atom']['state'] == 'SCOPE_UNAUTHORIZED'
    assert not case['fetches']


def test_note_metric_replay_missing_null_zero_and_distinct_source(durable_case):
    import database as db
    case = durable_case
    def snapshots():
        with sqlite3.connect(case['db_path']) as conn:
            return conn.execute("SELECT entity_key,likes,comments,collects,shares FROM metric_snapshots WHERE entity_type='note' ORDER BY id").fetchall()
    payload = {'note_id': 'owned-metric-1', 'source_platform': 'x', 'title': 'Owned metrics', 'likes': 7, 'comments': 2}
    db.insert_note(payload)
    db.insert_note(payload)
    assert snapshots() == []
    db.insert_note({'note_id': payload['note_id'], 'source_platform': 'x', 'title': 'No metric fields'})
    assert snapshots() == []
    db.insert_note({**payload, 'likes': 0})
    assert snapshots() == [('owned-metric-1', 0, 2, None, None)]
    db.insert_note({**payload, 'likes': 0})
    assert len(snapshots()) == 1
    db.insert_note({**payload, 'likes': None})
    assert snapshots()[-1] == ('owned-metric-1', None, 2, None, None)
    assert snapshots()[0] == ('owned-metric-1', 0, 2, None, None)
    db.insert_note({**payload, 'note_id': 'owned-metric-2'})
    db.insert_note({**payload, 'note_id': 'owned-metric-2', 'likes': 0})
    assert snapshots()[-1][0] == 'owned-metric-2'


def test_expiration_during_acquisition_fences_source_commit(durable_case, monkeypatch):
    import time
    case = durable_case
    task_id = approved_task(case)
    adapter = case['surface']._get_runtime_adapter('web_atom')
    original_fetch = adapter.fetcher
    queue = case['service']._queue(); task = queue.get(int(task_id[3:]))
    payload = task['payload']; payload['deadline_at'] = time.time() + 0.2
    with queue._conn:
        queue._conn.execute('UPDATE tasks SET payload=? WHERE id=?', (json.dumps(payload), task['id']))
    queue.close()
    def slow_owned_fetch(url):
        result = original_fetch(url)
        time.sleep(0.3)
        return result
    monkeypatch.setattr(adapter, 'fetcher', slow_owned_fetch)
    case['service']._job(task_id)
    result = case['service'].get_task(task_id)
    assert result['queue_status'] == 'failed' and result['success'] is False
    assert result['per_platform']['web_atom']['state'] == 'TASK_DEADLINE_EXCEEDED'
    assert len(case['fetches']) == 1
    assert all(value == 0 for value in _pipeline_counts(case['db_path']).values())


def test_explicit_policy_window_continuation_keeps_completed_platform_receipt(durable_case, monkeypatch):
    import time
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    from lumenis.system.collector.adapters.scheduling.policy import DEFAULT_POLICIES, PlatformSchedulePolicy
    from tests.test_collector_transaction_truth import REGISTERED_NAME
    case = durable_case
    monkeypatch.setitem(DEFAULT_POLICIES, 'public_http', PlatformSchedulePolicy('public_http', run_duration_manual=1))
    atom = case['surface']._get_runtime_adapter('web_atom')
    second_calls = []
    class OwnedHTTPTransport:
        def health_check(self, **kwargs):
            return CollectionResult(CollectionStatus.SUCCESS, 'public_http')
        def search(self, keyword, **kwargs):
            second_calls.append(keyword)
            return CollectionResult(CollectionStatus.SUCCESS, 'public_http', raw_count=1, items=[{
                'platform_content_id': 'owned-second-source', 'title': REGISTERED_NAME + ' update',
                'content': REGISTERED_NAME + ' owned fixture body',
                'url': 'https://public.example.test/owned-second-source',
                'publish_datetime': '2026-10-01T08:00:00Z', 'raw': {}}])
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda platform: atom if platform == 'web_atom' else OwnedHTTPTransport())
    body = {'keyword': SOURCE_URL, 'platforms': ['web_atom', 'public_http'],
            'max_results': 1, 'confirm_read_only': True}
    for _ in range(3):
        response = case['client'].post('/v4/adapters/collect', headers=case['headers'], json=body)
        if response.status_code == 200:
            break
        assert response.get_json()['status'] == 'APPROVAL_REQUIRED'
        case['gate'].grant_approval('data_import', resource=response.get_json()['approval_resource'],
            granted_by='explicit owned multi-platform fixture')
    assert response.status_code == 200
    task_id = response.get_json()['task_id']
    original_run = case['service']._run_one
    delayed = []
    def delay_second(platform, *args, **kwargs):
        if platform == 'public_http' and not delayed:
            delayed.append(True)
            time.sleep(1.1)
        return original_run(platform, *args, **kwargs)
    monkeypatch.setattr(case['service'], '_run_one', delay_second)
    case['service']._job(task_id)
    expired = case['service'].get_task(task_id)
    assert expired['deadline_expired'] is True and expired['resume_required'] is True
    assert expired['per_platform']['web_atom']['success'] is True
    first_ref = expired['per_platform']['web_atom']['task_commit_evidence_ref']
    assert len(case['fetches']) == 1
    monkeypatch.setitem(DEFAULT_POLICIES, 'public_http', PlatformSchedulePolicy('public_http', run_duration_manual=10))
    monkeypatch.setitem(case['surface']._last_action, 'public_http', 0.0)
    resumed = case['client'].post('/v4/adapters/task/' + task_id + '/resume',
        headers=case['headers'], json={'confirm_read_only': True})
    assert resumed.status_code == 200, resumed.get_json()
    case['service']._job(task_id)
    completed = case['service'].get_task(task_id)
    assert completed['success'] is True, completed
    assert completed['per_platform']['web_atom']['task_commit_evidence_ref'] == first_ref
    assert len(case['fetches']) == 1 and len(second_calls) == 2
    with sqlite3.connect(case['db_path']) as conn:
        assert conn.execute('SELECT COUNT(*) FROM canonical_data').fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTOR_TASK_COMMIT'").fetchone()[0] == 2
