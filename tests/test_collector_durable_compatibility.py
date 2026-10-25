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


@pytest.mark.parametrize('interruption', ['none', 'cancel_before_resume', 'progress_crash'])
def test_native_partial_source_commit_and_same_task_resume_keep_original_receipts(request, monkeypatch, tmp_path, interruption):
    """Real isolated persistence with admitted fixture bytes; no platform/session is called."""
    import socket

    from lumenis.system.collector import acquisition_plan
    from lumenis.system.collector.adapters.base import (
        CollectionResult,
        CollectionStatus,
    )
    from lumenis.system.collector.guard import checkpoint, task_queue
    from tests.test_collector_transaction_truth import REGISTERED_NAME

    case = request.getfixturevalue('collector_case')
    entry = case['surface']
    monkeypatch.setattr(task_queue, 'DEFAULT_PATH', str(tmp_path / 'native-tasks.db'))
    monkeypatch.setattr(checkpoint, 'get_data_dir', lambda: str(tmp_path / 'native-progress'))
    def no_network(*args, **kwargs):
        pytest.fail('isolated continuation attempted live acquisition')
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    monkeypatch.setattr(socket.socket, 'connect_ex', no_network)
    monkeypatch.setattr(socket, 'create_connection', no_network)
    monkeypatch.setattr(entry, '_adapter_health', lambda *a, **k: {'status': 'SUCCESS', 'can_attempt': True})
    calls = []
    class AllowedInputAdapter:
        def search(self, keyword, **kwargs):
            calls.append(kwargs['acquisition_fingerprint'])
            index = len(calls)
            partial = index == 1
            descriptor = {'task_binding': calls[-1], 'keyword': keyword, 'source_host': 'www.rednote.com',
                'raw_path': str(tmp_path / 'synthetic-native-checkpoint.json'), 'raw_sha256': 'a' * 64,
                'identity_fingerprint': 'b' * 64, 'run_id': 'allowed-input-' + str(index),
                'complete': not partial, 'terminal_error': False, 'continuation_required': partial,
                'pending_note_ids': ['d' * 24] if partial else [], 'pagination_exhausted': False}
            assert checkpoint.Checkpoint('xhs').save_operational_resume(keyword, calls[-1], descriptor)
            note_id = ('c' if partial else 'd') * 24
            return CollectionResult(status=CollectionStatus.SUCCESS, platform='xiaohongshu', raw_count=1,
                items=[{'note_id': note_id, 'title': REGISTERED_NAME + ' fixture page ' + str(index),
                    'content': keyword + ' permitted synthetic native detail',
                    'url': 'https://www.rednote.com/explore/' + note_id,
                    'publish_datetime': '2026-10-01T08:00:00Z', 'liked_count': 0,
                    'comment_count': None, 'collected_count': 1, 'source_platform': 'xhs'}],
                metadata={'provider': 'isolated_allowed_input', 'source_platform': 'xhs',
                    'source': 'www.rednote.com', 'continuation_persisted': True,
                    'checkpoint_identity_verified': True, 'continuation': {
                        'keyword': keyword, 'source_host': 'www.rednote.com', 'identity_verified': True,
                        'continuation_required': partial, 'checkpoint_run_id': descriptor['run_id']}})
    adapter = AllowedInputAdapter()
    monkeypatch.setattr(entry, '_get_runtime_adapter', lambda *a: adapter)
    reqs = [{'domain_id': 'CTH', 'scope_key': case['scope']['subject_id'], 'aliases': [REGISTERED_NAME],
             'purpose': 'Review permitted fixture input', 'dimension': 'market_activity',
             'platforms': ['xiaohongshu'], 'topic_terms': ['fixture']}]
    with case['client'].application.test_request_context('/', headers=case['focus_headers'],
            environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        actor = case['permission'].resolve_local_workspace_principal(module='collector', action='write')
        plan = acquisition_plan.build_acquisition_plan(business_requests=reqs)
        assert len(plan.queries) == 1
        for query in plan.queries:
            _scope, denial = entry._manual_collection_guard(actor, case['scope'], 'xiaohongshu', query.keyword, 1)
            assert denial['status'] == 'APPROVAL_REQUIRED'
            case['gate'].grant_approval('data_import', resource=denial['approval_resource'], granted_by='isolated allowed input')
        def execute(**extra):
            monkeypatch.setitem(entry._last_action, 'xiaohongshu', 0.0)
            return entry.collect_business_queries(reqs, actor=actor, scopes={'cth': case['scope']},
                max_results=1, request_id='native-isolated-001', **extra)
        if interruption == 'progress_crash':
            save_progress = task_queue.TaskQueue.save_progress
            lost = []
            def crash_after_source_commit(self, task_id, progress, **receipt):
                if progress.get('native_rounds') and not lost:
                    lost.append(True)
                    raise RuntimeError('isolated interruption after durable source commit')
                return save_progress(self, task_id, progress, **receipt)
            monkeypatch.setattr(task_queue.TaskQueue, 'save_progress', crash_after_source_commit)
            with pytest.raises(RuntimeError, match='interruption after durable source commit'):
                execute()
            assert len(calls) == 1
            queue = task_queue.TaskQueue()
            with queue._conn:
                queue._conn.execute('UPDATE tasks SET scheduled_at=0')
            queue.close()
        first = execute()
        assert first['native_continuation_required'] is True, first
        assert not first['ok'] and first['continuation_required']
        first_ref = first['runs'][0]['result']['task_commit_evidence_ref']
        with sqlite3.connect(case['db_path']) as con:
            assert con.execute('SELECT count(*) FROM canonical_data').fetchone()[0] == 1
        assert execute()['cached'] and len(calls) == 1
        if interruption == 'cancel_before_resume':
            # This owner test injects the existing server cancel control; there
            # is no claim that a new UI cancellation endpoint has been added.
            queue = task_queue.TaskQueue()
            task = queue.get(first['checkpoint']['task_id'])
            task['payload']['cancel_requested'] = True
            with queue._conn:
                queue._conn.execute('UPDATE tasks SET payload=? WHERE id=?',
                    (json.dumps(task['payload']), task['id']))
            cancelled = execute(checkpoint=first['checkpoint'])
            assert cancelled['status'] == 'CANCELLED' and not cancelled['network_attempted']
            assert len(calls) == 1
            task['payload']['cancel_requested'] = False
            with queue._conn:
                queue._conn.execute('UPDATE tasks SET payload=? WHERE id=?',
                    (json.dumps(task['payload']), task['id']))
            queue.close()
        second = execute(checkpoint=first['checkpoint'])
        assert second['ok'] and second['checkpoint']['task_id'] == first['checkpoint']['task_id'], second
        assert len(calls) == 2
        assert second['runs'][0]['result']['task_commit_evidence_ref'] != first_ref
        old = execute(checkpoint=first['checkpoint'])
        assert old['cached'] and not old['refresh_performed'] and len(calls) == 2
        with sqlite3.connect(case['db_path']) as con:
            assert con.execute('SELECT count(*) FROM canonical_data').fetchone()[0] == 2
            assert con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='COLLECTOR_TASK_COMMIT'").fetchone()[0] == 2


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
    from tests.test_collector_transaction_truth import _feed
    case = durable_case
    task_id = approved_task(case)
    manifest = case['db_path'].parent / 'commit-worker.json'
    manifest.write_text(json.dumps({
        'root': str(case['db_path'].parent), 'db_path': str(case['db_path']),
        'queue_path': str(case['queue_path']), 'task_id': task_id,
        'source_url': SOURCE_URL, 'atom': _feed(1234).decode('utf-8'),
    }), encoding='utf-8')
    # Explicit fixture setup replaces inherited fork/monkeypatch state. Keep
    # platform/model/session/signing configuration out of both new interpreters.
    env = {key: value for key, value in os.environ.items() if key.upper() in {
        'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PATH', 'PATHEXT', 'COMSPEC',
        'LANG', 'LC_ALL', 'PYTHONHOME', 'VIRTUAL_ENV',
    }}
    env.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
    worker = Path(__file__).with_name('collector_commit_worker.py')
    def run_worker(mode):
        return subprocess.run([sys.executable, '-X', 'utf8', str(worker), str(manifest), mode],
            env=env, text=True, encoding='utf-8', capture_output=True, timeout=35,
            cwd=str(Path(__file__).resolve().parents[1]))
    crashed = run_worker('crash')
    assert crashed.returncode == 86, crashed.stdout + crashed.stderr
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
    recovered = run_worker('recover')
    assert recovered.returncode == 0, recovered.stdout + recovered.stderr
    assert json.loads(recovered.stdout.splitlines()[-1])['success'] is True
    assert_committed_once(case)
    assert case['service'].get_task(task_id)['success'] is True


@pytest.mark.parametrize('source_token', [False, True])
def test_independent_detail_uses_same_permission_transaction_and_replays_exact_commit(collector_case, monkeypatch, source_token):
    from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
    from tests.test_collector_transaction_truth import REGISTERED_NAME
    case = collector_case
    entry = case['surface']
    note_id = 'e' * 24
    url = 'https://www.rednote.com/explore/' + note_id
    requested = url + '?xsec_token=isolated-locator-never-evidence' if source_token else note_id
    expected_backend_url = url + '?xsec_token=isolated-locator-never-evidence' if source_token else url
    calls = []
    class ExactDetailAdapter:
        def detail(self, target, **kwargs):
            calls.append((target, kwargs['acquisition_fingerprint']))
            assert target == expected_backend_url
            return CollectionResult(CollectionStatus.SUCCESS, 'xhs', raw_count=1,
                items=[{'note_id': note_id, 'title': REGISTERED_NAME + ' permitted detail fixture',
                        'content': 'Original permitted source content for ' + REGISTERED_NAME,
                        'url': url, 'source_platform': 'xhs', 'liked_count': 0,
                        'comment_count': None, 'collected_count': 1,
                        'publish_datetime': '2026-10-01T08:00:00Z',
                        'detail_fetched': True, 'detail_identity_verified': True}],
                metadata={'provider': 'isolated_detail_fixture', 'source': 'www.rednote.com',
                          'source_platform': 'xhs', 'acquisition_capability': 'detail'})
    monkeypatch.setattr(entry, '_get_runtime_adapter', lambda *a: ExactDetailAdapter())
    monkeypatch.setattr(entry, '_adapter_health', lambda *a, **k: {'status': 'SUCCESS', 'can_attempt': True})
    with case['client'].application.test_request_context('/', headers=case['focus_headers'],
            environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        actor = case['permission'].resolve_local_workspace_principal(module='collector', action='write')
        args = {'actor': actor, 'scope': case['scope'], 'operation_key': 'isolated-independent-detail-01'}
        denied = entry.collect_detail('xhs', requested, **args)
        assert denied['status'] == 'APPROVAL_REQUIRED' and not calls
        case['gate'].grant_approval('data_import', resource=denied['approval_resource'],
                                    granted_by='isolated exact detail permission')
        monkeypatch.setitem(entry._last_action, 'xiaohongshu', 0.0)
        committed = entry.collect_detail('xhs', requested, **args)
        assert committed['ok'], committed
        assert committed['evidence_recorded']
        replayed = entry.collect_detail('xhs', url, **args)
        assert replayed['commit_reconciled'] and len(calls) == 1
        assert 'isolated-locator-never-evidence' not in json.dumps(replayed)
        with sqlite3.connect(case['db_path']) as con:
            for (material,) in con.execute("SELECT inputs_json||outputs_json FROM app_evidence_records"):
                assert 'isolated-locator-never-evidence' not in material
        assert _pipeline_counts(case['db_path']) == {
            'notes': 1, 'canonical_data': 1, 'app_evidence_records': 2,
            'platform_contents': 1, 'metric_snapshots': 1}


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
