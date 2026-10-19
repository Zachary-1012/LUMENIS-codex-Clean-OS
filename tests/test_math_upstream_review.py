"""Actual scheduler/queue/Evidence/reviewer chain, isolated generated upstream."""
import hashlib
import json
import time
import pytest
from tests.test_math_revocation import workspace, original_workspace, review
from lumenis.system.collector.runtime.scheduler import upstream_math_review as u
from lumenis.system.collector.runtime.scheduler.collector_job import Scheduler
from lumenis.system.collector.guard.task_queue import TaskQueue
from lumenis.system.collector.guard.queue_worker import QueueWorker
from lumenis.system.security import OperationType
from lumenis.shared.evaluation.openai_math_papers import provenance as p

COMMIT = 'a' * 40
TREE = 'b' * 40
CONTENT = b'Generated changed fragment, not real official evidence.\n'
BLOB = hashlib.sha1(b'blob ' + str(len(CONTENT)).encode() + b'\0' + CONTENT).hexdigest()
PATH = p.REGISTRY['102']['path']


def fetch(url):
    if url == u.HEAD_URL:
        obj = {'sha': COMMIT, 'commit': {'tree': {'sha': TREE}}}
    elif '/git/trees/' in url:
        obj = {'sha': TREE, 'truncated': False, 'tree': [
            {'path': path, 'type': 'blob', 'sha': BLOB if path in (PATH, 'history.md') else spec['blob']}
            for path, spec in u.sources().items()]}
    else:
        return CONTENT
    return json.dumps(obj).encode()


@pytest.fixture
def setup(workspace, monkeypatch):
    w = workspace
    monkeypatch.setattr(u, 'get_permission_gate', lambda: w['gate'])
    monkeypatch.setattr(u, 'get_repository', lambda: w['repo'])
    config = u.configuration(schedule_id='official-math', cadence_seconds=3600, enabled=True, actor=w['actor'], scope=w['scope'])
    for op in (OperationType.CONFIG_MODIFY, OperationType.COLLECTOR_START, OperationType.EXTERNAL_NETWORK):
        w['gate'].grant_approval(op.value, resource=config['resource'], granted_by='isolated-owner')
    u.configure(schedule_id='official-math', cadence_seconds=3600, enabled=True, actor=w['actor'], scope=w['scope'])
    queue = TaskQueue(str(w['root'] / 'queue.sqlite3'))
    scheduler = Scheduler(str(w['root'] / 'scheduler.json'))
    yield w, queue, scheduler, config
    queue.close()


def run(setup, fetcher=fetch):
    w, queue, scheduler, _ = setup
    ids = scheduler.tick_upstream_review(queue, actor=w['actor'], scope=w['scope'])
    worker = QueueWorker(queue, u.processor(queue, actor_provider=lambda: (w['actor'], w['scope']), fetch=fetcher))
    return ids, worker.process_once()


def test_scheduler_observation_review_owner_guard_end_to_end(setup):
    w, q, s, _ = setup
    ids, result = run(setup)
    assert result == (ids[0], True)
    assert s.tick_upstream_review(q, actor=w['actor'], scope=w['scope']) == ids
    handoff = u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])
    assert handoff['current_status'] == 'REVIEW_REQUIRED'
    assert p.assert_review('102')['status'] == 'REVIEWED_PINNED'
    eid = handoff['observations'][0]['evidence_id']
    args = dict(evidence_id=eid, path=PATH, actor=w['actor'], scope=w['scope'])
    prepared = u.prepare_changed_review(**args)
    with pytest.raises(PermissionError, match='EXACT_APPROVAL'):
        u.apply_changed_review(**args)
    w['gate'].grant_approval(OperationType.CONFIG_MODIFY.value, resource=prepared['resource'], granted_by='isolated-reviewer')
    u.apply_changed_review(**args)
    assert p.review_snapshot('102')['status'] == 'REVIEW_REQUIRED'
    assert p.assert_review('103')['status'] == 'REVIEWED_PINNED'
    assert p.UPSTREAM_COMMIT == 'fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb'


def test_unknown_fetch_backoff_keeps_last_success(setup):
    w, q, s, _ = setup
    run(setup)
    def offline(url):
        raise RuntimeError('network unavailable')
    ids = s.tick_upstream_review(q, actor=w['actor'], scope=w['scope'], now=time.time()+3600)
    result = QueueWorker(q, u.processor(q, actor_provider=lambda: (w['actor'], w['scope']), fetch=offline)).process_once()
    assert result == (ids[0], False)
    task = q.get(ids[0])
    assert task['status'] == 'pending' and task['attempts'] == 1 and task['scheduled_at'] > time.time()
    handoff = u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])
    assert handoff['current_status'] == 'FETCH_UNAVAILABLE' and handoff['last_verified_acquisition_at']
    assert p.assert_review('102')['status'] == 'REVIEWED_PINNED'


def test_restart_after_commit_before_ack_idempotent(setup):
    w, q, s, _ = setup
    task_id = s.tick_upstream_review(q, actor=w['actor'], scope=w['scope'])[0]
    task = q.dequeue(worker_id='old', lease_owner='old')
    assert u.processor(q, actor_provider=lambda: (w['actor'], w['scope']), fetch=fetch)(task)
    q.close()
    recovered = TaskQueue(q.path)
    try:
        assert recovered.reap_stale(0) == [task_id]
        with recovered._conn:
            recovered._conn.execute('UPDATE tasks SET scheduled_at=0 WHERE id=?', (task_id,))
        def no_refetch(url):
            pytest.fail('committed observation must recover without another fetch')
        assert QueueWorker(recovered, u.processor(recovered, actor_provider=lambda: (w['actor'], w['scope']), fetch=no_refetch)).process_once() == (task_id, True)
        assert not recovered.ack(task_id, run_id=task['run_id'], worker_id='old', lease_owner='old')
        assert len(u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])['observations']) == 1
    finally:
        recovered.close()


def test_revoke_before_worker_no_network(setup, monkeypatch):
    w, q, s, _ = setup
    task_id = s.tick_upstream_review(q, actor=w['actor'], scope=w['scope'])[0]
    monkeypatch.setattr(w['gate'], 'get_valid_approval_token', lambda *a, **k: None)
    def forbidden(url):
        pytest.fail('revoked grant must prevent network')
    assert QueueWorker(q, u.processor(q, actor_provider=lambda: (w['actor'], w['scope']), fetch=forbidden)).process_once() == (task_id, False)


def test_revoked_paper_never_cleared_by_collection(setup):
    w, _, _, _ = setup
    review(w)
    assert run(setup)[1][1]
    assert p.review_snapshot('102')['status'] == 'REVOKED'


def test_validation_and_no_default_schedule(workspace):
    w = workspace
    q = TaskQueue(str(w['root'] / 'emptyqueue.sqlite3'))
    try:
        assert Scheduler(str(w['root']/'empty.json')).tick_upstream_review(q, actor=w['actor'], scope=w['scope']) == []
    finally:
        q.close()
    for cadence in (True, 1, 604801):
        with pytest.raises(ValueError):
            u.configuration(schedule_id='x', cadence_seconds=cadence, enabled=True, actor=w['actor'], scope=w['scope'])
    def truncated(url):
        if '/git/trees/' in url:
            return json.dumps({'sha': TREE, 'truncated': True, 'tree': []}).encode()
        return fetch(url)
    with pytest.raises(ValueError, match='TREE_INCOMPLETE'):
        u.collect_observation(truncated)


def test_revocation_during_fetch_prevents_commit(setup, monkeypatch):
    w, q, s, _ = setup
    def changing(url):
        result = fetch(url)
        if 'raw.githubusercontent' in url:
            monkeypatch.setattr(w['gate'], 'get_valid_approval_token', lambda *a, **k: None)
        return result
    assert run(setup, changing)[1][1] is False
    with w['repo'].connection(read_only=True) as con:
        assert u._rows(con, u.OBS_SOURCE) == []


@pytest.mark.parametrize('domain,expected', [('cth', 'CTH'), ('bmp', 'ZBMP'), ('zbmp', 'ZBMP')])
def test_verified_business_domain_controls_observation_custody(workspace, monkeypatch, domain, expected):
    """A Shared feature label never overrides the current authorized business scope."""
    w = workspace
    scope = {**w['scope'], 'domain_id': domain}
    monkeypatch.setattr(u, 'get_permission_gate', lambda: w['gate'])
    monkeypatch.setattr(u, 'get_repository', lambda: w['repo'])
    config = u.configuration(schedule_id='custody', cadence_seconds=3600, enabled=True,
                             actor=w['actor'], scope=scope)
    for op in (OperationType.CONFIG_MODIFY, OperationType.COLLECTOR_START, OperationType.EXTERNAL_NETWORK):
        w['gate'].grant_approval(op.value, resource=config['resource'], granted_by='isolated-owner')
    u.configure(schedule_id='custody', cadence_seconds=3600, enabled=True, actor=w['actor'], scope=scope)
    queue = TaskQueue(str(w['root'] / 'custody.sqlite3'))
    try:
        task_id = u.tick(queue, actor=w['actor'], scope=scope)[0]
        assert QueueWorker(queue, u.processor(queue, actor_provider=lambda: (w['actor'], scope), fetch=fetch)).process_once() == (task_id, True)
        with w['repo'].connection(read_only=True) as con:
            rows = con.execute('SELECT * FROM app_evidence_records WHERE source=?', (u.OBS_SOURCE,)).fetchall()
            assert len(rows) == 1
            row = dict(rows[0])
            assert row['product'] == expected
            assert row['domain_id'] == ('cth' if domain == 'cth' else 'zbmp')
            stored_scope = json.loads(row['inputs_json'])['_lumenis_scope']
            assert stored_scope == {'domain_id': row['domain_id'], 'product_id': expected, 'global': True}
            assert u.verify_evidence_record_integrity(row)
    finally:
        queue.close()


@pytest.mark.parametrize('changed', [
    {'domain_id': 'bmp'}, {'domain_id': 'shared'}, {'domain_id': 'content'},
    {'product': 'Shared'}, {'subject_id': 'forged-subject', 'global_scope': False},
    {'brand_focus_id': 'forged-brand', 'global_scope': False},
])
def test_changed_or_forged_scope_cannot_fetch_or_write(setup, changed):
    w, queue, scheduler, _ = setup
    task_id = scheduler.tick_upstream_review(queue, actor=w['actor'], scope=w['scope'])[0]
    altered = {**w['scope'], **changed}
    def forbidden(url):
        pytest.fail('invalid or cross-domain principal must fail before fetching')
    assert QueueWorker(queue, u.processor(queue, actor_provider=lambda: (w['actor'], altered), fetch=forbidden)).process_once() == (task_id, False)
    with w['repo'].connection(read_only=True) as con:
        assert u._rows(con, u.OBS_SOURCE) == []


@pytest.mark.parametrize('domain', ['Shared', 'shared', 'content'])
def test_shared_scope_configuration_is_rejected_without_side_effect(workspace, monkeypatch, domain):
    w = workspace
    monkeypatch.setattr(u, 'get_repository', lambda: w['repo'])
    with pytest.raises((ValueError, PermissionError)):
        u.configuration(schedule_id='forged-shared', cadence_seconds=3600, enabled=True,
                        actor=w['actor'], scope={**w['scope'], 'domain_id': domain})
    with w['repo'].connection(read_only=True) as con:
        assert u._rows(con, u.CONFIG_SOURCE) == []
        assert u._rows(con, u.OBS_SOURCE) == []


def test_payload_product_cannot_override_server_custody(setup):
    w, queue, scheduler, _ = setup
    task_id = scheduler.tick_upstream_review(queue, actor=w['actor'], scope=w['scope'])[0]
    task = queue.dequeue(worker_id='product-test', lease_owner='product-test')
    task['payload']['product'] = 'Shared'
    task['payload']['domain_id'] = 'zbmp'
    assert u.processor(queue, actor_provider=lambda: (w['actor'], w['scope']), fetch=fetch)(task)
    with w['repo'].connection(read_only=True) as con:
        row = dict(con.execute('SELECT * FROM app_evidence_records WHERE source=?', (u.OBS_SOURCE,)).fetchone())
        assert row['product'] == 'CTH' and row['domain_id'] == 'cth'


def test_cold_process_reads_committed_observation_before_queue_ack(setup):
    """Read the committed bytes in another interpreter, then resume with a new lease."""
    import os
    import subprocess
    import sys
    w, queue, scheduler, _ = setup
    task_id = scheduler.tick_upstream_review(queue, actor=w['actor'], scope=w['scope'])[0]
    task = queue.dequeue(worker_id='cold-old', lease_owner='cold-old')
    assert u.processor(queue, actor_provider=lambda: (w['actor'], w['scope']), fetch=fetch)(task)
    queue.close()
    probe = subprocess.run([sys.executable, '-B', '-c',
        "import sqlite3,sys,json; c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True); "
        "r=c.execute('SELECT product,domain_id,outputs_json FROM app_evidence_records WHERE source=?',(sys.argv[2],)).fetchall(); "
        "assert len(r)==1; assert r[0][:2]==('CTH','cth'); assert json.loads(r[0][2])['acquisition_status']=='OBSERVED'; print('COLD_READ_PASS')",
        str(w['root'] / 'isolated.sqlite3'), u.OBS_SOURCE], capture_output=True, text=True,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    assert probe.returncode == 0, probe.stderr
    assert probe.stdout.strip() == 'COLD_READ_PASS'
    recovered = TaskQueue(queue.path)
    try:
        assert recovered.reap_stale(0) == [task_id]
        with recovered._conn:
            recovered._conn.execute('UPDATE tasks SET scheduled_at=0 WHERE id=?', (task_id,))
        def no_refetch(url):
            pytest.fail('cold committed observation must not fetch again')
        assert QueueWorker(recovered, u.processor(recovered, actor_provider=lambda: (w['actor'], w['scope']), fetch=no_refetch)).process_once() == (task_id, True)
        assert not recovered.ack(task_id, run_id=task['run_id'], worker_id='cold-old', lease_owner='cold-old')
        assert len(u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])['observations']) == 1
    finally:
        recovered.close()
