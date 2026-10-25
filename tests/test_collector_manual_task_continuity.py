"""Manual durable task operations; declared source fixtures and isolated queue only."""
import json
import sqlite3
import time

import pytest

from tests.test_collector_transaction_truth import collector_case, URL, REQUEST, GLOBAL_MODE
from tests.test_collector_comment_pages import comments_case


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
    assert request(case, 'confirm', source=source,
        confirmed_resource=prepared['approval_resource']).get_json()['approved']


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
    request(case, 'cancel', task_id=task_id)
    assert request(case, 'status', task_id=task_id).get_json()['result']['page_ref'] == first['result']['page_ref']
    request(case, 'resume', task_id=task_id)
    monkeypatch.setitem(case['entry']._last_action, 'xiaohongshu', 0.0)
    second = request(case, 'step', task_id=task_id).get_json()
    assert second['status'] == 'COMPLETED' and not second['continuation_required']
    assert len(case['calls']) == 2 and case['calls'][1]['cursor'] == {'page': 2}
    with sqlite3.connect(queue_owner[1]) as connection:
        payload = connection.execute('SELECT payload FROM tasks WHERE id=?', (task_id,)).fetchone()[0]
        assert 'First source statement' not in payload and 'Second page source statement' not in payload
        assert 'comments' not in (json.loads(payload).get('progress', {}).get('result') or {})
