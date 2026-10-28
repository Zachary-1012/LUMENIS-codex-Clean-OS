"""Actual HTTP/SQLite/existing leased QueueWorker, without external models."""
import json
import sqlite3

import pytest

from tests.test_skill_http_durable_identity import skill_client


@pytest.fixture
def background(skill_client, tmp_path, monkeypatch):
    from lumenis.shared.agents.skills import execution
    from lumenis.system.collector.guard import task_queue
    monkeypatch.setattr(task_queue, 'DEFAULT_PATH', tmp_path / 'existing-queue.sqlite')
    # Tests choose exactly when the real leased worker wakes, except real_thread.
    monkeypatch.setattr(execution, 'start_registered_skill_job', lambda _id: None)
    return skill_client


def submit(api):
    response = api.post('/api/ai/tasks', headers={'Authorization': 'Bearer fixture-session-one'}, json={
        'skill_id': 'zbc.skill_registry_snapshot', 'task': 'Read registered capabilities',
        'product': 'CTH', 'action_type': 'READ', 'background': True, 'user_id': 2})
    assert response.status_code == 202, response.get_json()
    return response.get_json()['execution_id']


def test_queued_http_reopens_runs_and_notifies_without_second_execution(background, monkeypatch):
    api, app, path = background
    identifier = submit(api)
    own = {'Authorization': 'Bearer fixture-session-one'}
    assert app.test_client().get('/api/ai/tasks/' + identifier, headers=own).get_json()['task']['status'] == 'pending'
    response = app.test_client().post('/api/ai/tasks/' + identifier + '/run', headers=own)
    assert response.status_code == 200, response.get_json()
    assert response.get_json()['task']['status'] == 'completed', response.get_json()
    assert response.get_json()['notification']['external_delivery'] is False
    from lumenis.shared.agents.skills import execution
    monkeypatch.setattr(execution, 'execute_skill', lambda *a, **kw: pytest.fail('terminal replay'))
    assert api.post('/api/ai/tasks/' + identifier + '/run', headers=own).get_json()['task']['status'] == 'completed'
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM skill_executions WHERE execution_id=?', (identifier,)).fetchone()[0] == 1
    from lumenis.system.collector.guard.task_queue import TaskQueue
    queue = TaskQueue()
    try:
        assert queue.stats()['done'] == 1
    finally:
        queue.close()


def test_cancel_wins_and_cross_actor_cannot_mutate(background):
    api, app, path = background
    identifier = submit(api)
    own = {'Authorization': 'Bearer fixture-session-one'}
    other = {'Authorization': 'Bearer fixture-session-two'}
    for action in ('run','cancel'):
        assert api.post(f'/api/ai/tasks/{identifier}/{action}', headers=other).status_code == 404
    assert api.post(f'/api/ai/tasks/{identifier}/cancel', headers=own).get_json()['task']['status'] == 'cancelled'
    assert api.post(f'/api/ai/tasks/{identifier}/run', headers=own).get_json()['task']['status'] == 'cancelled'
    from lumenis.shared.agents.skills.execution import SkillExecutionContext, ExecutionStatus, write_trace
    late = SkillExecutionContext(execution_id=identifier, skill_id='zbc.skill_registry_snapshot', status=ExecutionStatus.COMPLETED)
    assert write_trace(late) is False
    assert api.get(f'/api/ai/tasks/{identifier}', headers=own).get_json()['task']['status'] == 'cancelled'


@pytest.mark.parametrize('change', ['revoke', 'version', 'inactive'])
def test_worker_rechecks_current_authority_and_version(background, change):
    api, app, path = background
    identifier = submit(api)
    with sqlite3.connect(path) as con:
        if change == 'revoke':
            con.execute('DELETE FROM v4_member_authorizations WHERE user_id=1')
        elif change == 'version':
            con.execute("UPDATE skills_registry SET version='2.0' WHERE skill_id='zbc.skill_registry_snapshot'")
        else:
            con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    from lumenis.shared.agents.skills.execution import run_registered_skill_job
    row = run_registered_skill_job(identifier)
    assert row['status'] == 'rejected', row
    assert row['output_json'] is None
    if change != 'version':
        assert api.get(f'/api/ai/tasks/{identifier}', headers={'Authorization': 'Bearer fixture-session-one'}).status_code == 404


def test_real_thread_worker_executes_after_http_submit(skill_client, tmp_path, monkeypatch):
    api, app, path = skill_client
    from lumenis.system.collector.guard import task_queue
    from lumenis.shared.agents.skills import execution
    monkeypatch.setattr(task_queue, 'DEFAULT_PATH', tmp_path / 'existing-queue.sqlite')
    threads = []
    start = execution.start_registered_skill_job
    def capture(identifier):
        thread = start(identifier)
        threads.append(thread)
        return thread
    monkeypatch.setattr(execution, 'start_registered_skill_job', capture)
    identifier = submit(api)
    threads[0].join(timeout=10)
    assert not threads[0].is_alive()
    result = app.test_client().get(f'/api/ai/tasks/{identifier}', headers={'Authorization': 'Bearer fixture-session-one'})
    assert result.get_json()['task']['status'] == 'completed', result.get_json()


def test_external_or_unbound_background_handler_is_not_enqueued(background):
    api, app, path = background
    response = api.post('/api/ai/tasks', headers={'Authorization': 'Bearer fixture-session-one'}, json={
        'skill_id': 'zbc.skill_registry_snapshot', 'product': 'CTH', 'action_type': 'READ',
        'background': True, 'input': {'api_key': 'not-a-secret-fixture'}})
    assert response.status_code == 409
    assert response.get_json()['code'] == 'BACKGROUND_HANDLER_NOT_ALLOWED'


@pytest.mark.parametrize('skill_id,payload', [
    ('zbc.agent_boundary_audit', {}),
    ('shared.social_card', {'title': 'Original local card'}),
    ('shared.video_shotcraft', {'brief': 'Original local story'}),
    ('shared.huashu', {'brief': 'Original local workflow'}),
])
def test_all_admitted_local_handlers_complete_without_provider(background, monkeypatch, skill_id, payload):
    api, app, path = background
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO skills_registry(skill_id,name,product,domain,status,version) VALUES(?,?,'CTH','cth','enabled','1.0')", (skill_id, skill_id))
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'CTH',?,'read')", (skill_id,))
    import lumenis_skill_adapter
    monkeypatch.setattr(lumenis_skill_adapter, 'get_skill_adapter', lambda: pytest.fail('provider adapter reached'))
    own = {'Authorization': 'Bearer fixture-session-one'}
    response = api.post('/api/ai/tasks', headers=own, json={'skill_id': skill_id, 'product': 'CTH',
        'action_type': 'READ', 'background': True, 'input': payload})
    assert response.status_code == 202, response.get_json()
    identifier = response.get_json()['execution_id']
    result = api.post(f'/api/ai/tasks/{identifier}/run', headers=own).get_json()
    assert result['task']['status'] == 'completed', result
    assert json.loads(result['task']['output_json'])['source'] == 'custom_handler'


def test_terminal_receipt_reconciles_lost_queue_ack_without_reexecution(background, monkeypatch):
    api, app, path = background
    identifier = submit(api)
    from lumenis.system.collector.guard.task_queue import TaskQueue
    original = TaskQueue.ack
    monkeypatch.setattr(TaskQueue, 'ack', lambda *a, **kw: False)
    from lumenis.shared.agents.skills.execution import run_registered_skill_job
    assert run_registered_skill_job(identifier)['status'] == 'completed'
    monkeypatch.setattr(TaskQueue, 'ack', original)
    from account import skills
    monkeypatch.setattr(skills, 'execute_skill_api', lambda *a, **kw: pytest.fail('reexecuted committed result'))
    assert run_registered_skill_job(identifier)['status'] == 'completed'
    queue = TaskQueue()
    try:
        assert queue.stats()['done'] == 1
    finally:
        queue.close()


def test_two_workers_claim_one_skill_and_do_not_consume_collector(background, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from lumenis.system.collector.guard.task_queue import TaskQueue
    from lumenis.shared.agents.skills import execution
    api, app, path = background
    count = []
    original = execution._execute_builtin_local
    def counted(ctx, meta):
        count.append(ctx.execution_id)
        return original(ctx, meta)
    monkeypatch.setattr(execution, '_execute_builtin_local', counted)
    # The server admits the actual callable before submission. Changing it
    # afterwards is a different execution version and is deliberately rejected.
    identifier = submit(api)
    queue = TaskQueue()
    collector = queue.enqueue('collect', {'keyword': 'must remain queued'})
    queue.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execution.run_registered_skill_job, [identifier, identifier]))
    assert count == [identifier]
    assert any(row['status'] == 'completed' for row in results)
    queue = TaskQueue()
    try:
        assert queue.get(collector)['status'] == 'pending'
    finally:
        queue.close()


def test_process_exit_after_claim_then_existing_lease_recovery(background, monkeypatch):
    import os
    import subprocess
    import sys
    from lumenis.system.collector.guard import task_queue
    from lumenis.shared.agents.skills.execution import run_registered_skill_job, query_executions
    api, app, path = background
    identifier = submit(api)
    row = query_executions(execution_id=identifier, limit=1)[0]
    queue = task_queue.TaskQueue()
    binding = json.loads(row['permission_json'])['background_binding']
    handler_identity = json.loads(row['permission_json'])['background_handler_identity_sha256']
    queue_id = queue.enqueue_once('registered_skill', {'execution_id': identifier,
        'actor_id': 1, 'product': 'CTH', 'binding': binding,
        'handler_identity_sha256': handler_identity}, identifier)
    queue.close()
    code = ('import os,sys; from lumenis.system.collector.guard.task_queue import TaskQueue; '
            'q=TaskQueue(sys.argv[1]); assert q.dequeue(worker_id="crashed",task_id=int(sys.argv[2])); os._exit(23)')
    child = subprocess.run([sys.executable, '-c', code, str(task_queue.DEFAULT_PATH), str(queue_id)],
                           env=dict(os.environ), capture_output=True, timeout=15)
    assert child.returncode == 23, child.stderr.decode()
    # Advance the stale-lease clock deterministically; actual subprocess committed
    # the claim and died without ack. Do not bypass the production reaper or CAS.
    with sqlite3.connect(task_queue.DEFAULT_PATH) as con:
        con.execute('UPDATE tasks SET last_heartbeat_at=0 WHERE id=?', (queue_id,))
    first = run_registered_skill_job(identifier)
    assert first['status'] == 'pending'
    with sqlite3.connect(task_queue.DEFAULT_PATH) as con:
        con.execute('UPDATE tasks SET scheduled_at=0 WHERE id=?', (queue_id,))
    final = run_registered_skill_job(identifier)
    assert final['status'] == 'completed', final
    queue = task_queue.TaskQueue()
    try:
        assert queue.get(queue_id)['status'] == 'done'
        assert queue.get(queue_id)['recovery_reason']
    finally:
        queue.close()
