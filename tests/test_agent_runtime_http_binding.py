"""Production HTTP -> existing queue -> AgentLoop with actual canonical Permission."""
import json
import sqlite3

import pytest
from tests.test_skill_http_durable_identity import skill_client


@pytest.fixture
def agent_client(skill_client, monkeypatch, tmp_path):
    api, app, path = skill_client
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_KEY_RING', json.dumps({'agent-test': 'public-isolated-agent-fixture-key'}))
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID', 'agent-test')
    from lumenis.system.collector.guard import task_queue
    from agent_runtime import task_binding
    monkeypatch.setattr(task_queue, 'DEFAULT_PATH', tmp_path / 'agent-queue.sqlite')
    monkeypatch.setattr(task_binding, 'start_agent_task', lambda _: None)
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','agent_runtime','read',?)", (json.dumps({'global': True}),))
        con.execute("UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1 AND product_id='CTH' AND module='zbc.skill_registry_snapshot' AND action='read'", (json.dumps({'global': True}),))
    return skill_client


def submit(api, *, model=False):
    data = {'execution_mode': 'agent', 'input': 'Read local registered metadata',
            'domain_id': 'cth', 'scope': {'global_scope': True, 'subject_id': None, 'brand_focus_id': None},
            'actor_id': 2, 'created_by': 'admin'}
    if not model:
        data['steps'] = [{'skill_id': 'zbc.skill_registry_snapshot', 'input': {}}]
    response = api.post('/api/ai/tasks', json=data, headers={'Authorization': 'Bearer fixture-session-one'})
    assert response.status_code == 202, response.get_json()
    return response.get_json()['task']['task_id']


def test_http_agent_loop_actual_permission_result_reopens(agent_client):
    api, app, path = agent_client
    task_id = submit(api)
    own = {'Authorization': 'Bearer fixture-session-one'}
    result = api.post(f'/api/ai/tasks/{task_id}/run', headers=own)
    assert result.status_code == 200, result.get_json()
    row = result.get_json()['task']
    assert row['status'] == 'succeeded', row
    assert row['context']['actor_id'] == 1
    reopened = app.test_client().get(f'/api/ai/tasks/{task_id}', headers=own).get_json()
    assert reopened['task']['result'] == row['result']
    assert reopened['notification']['external_delivery'] is False
    assert api.get(f'/api/ai/tasks/{task_id}/steps', headers=own).get_json()['count'] >= 2
    assert api.post(f'/api/ai/tasks/{task_id}/run', headers=own).get_json()['task']['status'] == 'succeeded'
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM ai_task').fetchone()[0] == 1
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 1


def test_agent_model_planning_is_bound_but_unavailable_without_service(agent_client):
    api, app, path = agent_client
    task_id = submit(api, model=True)
    response = api.post(f'/api/ai/tasks/{task_id}/run', headers={'Authorization': 'Bearer fixture-session-one'})
    assert response.status_code == 200, response.get_json()
    row = response.get_json()['task']
    assert row['status'] == 'failed', row
    assert 'BOUND' in row['error'] or 'UNAVAILABLE' in row['error'], row['error']
    assert row.get('result') is None


def test_agent_cancel_cross_actor_and_scope_revocation(agent_client):
    api, app, path = agent_client
    task_id = submit(api)
    other = {'Authorization': 'Bearer fixture-session-two'}
    assert api.post(f'/api/ai/tasks/{task_id}/run', headers=other).status_code == 403
    own = {'Authorization': 'Bearer fixture-session-one'}
    assert api.post(f'/api/ai/tasks/{task_id}/cancel', headers=own).status_code == 200
    assert api.post(f'/api/ai/tasks/{task_id}/run', headers=own).get_json()['task']['status'] == 'cancelled'
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE module='agent_runtime'")
    assert api.get(f'/api/ai/tasks/{task_id}', headers=own).status_code == 403
    assert api.get('/api/ai/tasks', headers=own).get_json()['tasks'] == []


def test_local_principal_actual_queue_result_and_identity_boundaries(agent_client):
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    data = {'execution_mode': 'agent', 'input': 'Read local tools', 'domain_id': 'cth',
            'scope': {'global_scope': True, 'subject_id': None, 'brand_focus_id': None},
            'steps': [{'skill_id': 'zbc.skill_registry_snapshot', 'input': {}}]}
    rejected = api.post('/api/ai/tasks', json=data, headers={'Origin': 'https://external.example'})
    assert rejected.status_code == 403
    rejected = api.post('/api/ai/tasks', json=data, headers={'X-Actor-ID': '1'})
    assert rejected.status_code == 403
    created = api.post('/api/ai/tasks', json={**data, 'actor_id': 1, 'principal_ref': 'actor:1'})
    assert created.status_code == 202, created.get_json()
    task_id = created.get_json()['task']['task_id']
    assert created.get_json()['task']['context']['actor_id'] is None
    assert api.get(f'/api/ai/tasks/{task_id}', headers={'Authorization': 'Bearer fixture-session-one'}).status_code == 403
    account_task = submit(api)
    assert api.get(f'/api/ai/tasks/{account_task}').status_code == 403
    result = api.post(f'/api/ai/tasks/{task_id}/run')
    assert result.status_code == 200, result.get_json()
    assert result.get_json()['task']['status'] == 'succeeded', result.get_json()
    from ai_task_engine import reset_task_engine
    reset_task_engine()
    assert app.test_client().get(f'/api/ai/tasks/{task_id}').get_json()['task']['status'] == 'succeeded'
    assert api.post(f'/api/ai/tasks/{task_id}/run').get_json()['task']['status'] == 'succeeded'
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT user_id FROM skill_executions').fetchall() == [(None,)]
    app.config['LUMENIS_OPEN_WORKSPACE'] = False
    assert api.get(f'/api/ai/tasks/{task_id}').status_code == 403


from agent_runtime.task_binding import start_agent_task as _real_start_agent_task


def _submit_local(api):
    response = api.post('/api/ai/tasks', json={'execution_mode': 'agent', 'input': 'Read local tools',
        'domain_id': 'cth', 'scope': {'global_scope': True, 'subject_id': None, 'brand_focus_id': None},
        'steps': [{'skill_id': 'zbc.skill_registry_snapshot', 'input': {}}]})
    assert response.status_code == 202, response.get_json()
    return response.get_json()['task']['task_id']


def test_local_background_thread_keeps_live_server_request_identity(agent_client):
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    task_id = _submit_local(api)
    with app.test_request_context('/api/ai/tasks', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        thread = _real_start_agent_task(task_id)
    thread.join(timeout=10)
    assert not thread.is_alive()
    result = api.get(f'/api/ai/tasks/{task_id}').get_json()['task']
    assert result['status'] == 'succeeded', result


def test_local_process_crash_after_tool_checkpoint_resumes_without_duplicate_effect(agent_client):
    import os
    import subprocess
    import sys
    from lumenis.system.collector.guard import task_queue
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    task_id = _submit_local(api)
    code = '''import os,sys
from flask import Flask
from lumenis.system.security import permission
permission._TESTING_BYPASS_ENABLED=False
from lumenis.system.collector.guard import task_queue
task_queue.DEFAULT_PATH=sys.argv[2]
from agent_runtime.durable_adapter import DurableExecutionAdapter
DurableExecutionAdapter.finalize_task=lambda *args,**kwargs: os._exit(23)
from ai_api import bp
app=Flask(__name__); app.config['LUMENIS_OPEN_WORKSPACE']=True; app.register_blueprint(bp)
r=app.test_client().post('/api/ai/tasks/'+sys.argv[1]+'/run')
print(r.status_code,r.get_json(),flush=True)
'''
    env = dict(os.environ)
    env.pop('PERMISSION_GATE_TESTING', None)
    child = subprocess.run([sys.executable, '-c', code, task_id, str(task_queue.DEFAULT_PATH)],
        env=env, text=True, capture_output=True, timeout=30)
    assert child.returncode == 23, child.stdout + child.stderr
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT status FROM ai_task WHERE task_id=?', (task_id,)).fetchone()[0] == 'running'
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 1
    with sqlite3.connect(task_queue.DEFAULT_PATH) as con:
        con.execute('UPDATE tasks SET last_heartbeat_at=0')
    result = app.test_client().post(f'/api/ai/tasks/{task_id}/run')
    assert result.status_code == 200, result.get_json()
    with sqlite3.connect(task_queue.DEFAULT_PATH) as con:
        con.execute('UPDATE tasks SET scheduled_at=0')
    result = app.test_client().post(f'/api/ai/tasks/{task_id}/run')
    assert result.get_json()['task']['status'] == 'succeeded', result.get_json()
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 1


def test_local_workspace_copy_and_formed_identity_substitution_are_denied(agent_client, monkeypatch, tmp_path):
    import shutil
    from agent_capability.formation import context_identity, FormationError
    from agent_runtime.task_binding import authorized_context
    from ai_task_engine import get_task_engine, reset_task_engine
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    task_id = _submit_local(api)
    with app.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        context = authorized_context(get_task_engine().get_task(task_id))
        identity = context_identity(context)
        assert identity
        with pytest.raises(FormationError):
            context_identity({**context, 'actor': {'principal_kind': 'local_workspace', 'principal_ref': 'workspace:local'}})
        altered = {**context, 'agent_runtime': {**context['agent_runtime'], 'workspace_binding': 'other-workspace'}}
        with pytest.raises(FormationError):
            context_identity(altered)
        app.config['LUMENIS_OPEN_WORKSPACE'] = False
        with pytest.raises(FormationError):
            context_identity(context)
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    other_db = tmp_path / 'different-workspace.sqlite'
    with sqlite3.connect(path) as source, sqlite3.connect(other_db) as destination:
        source.backup(destination)
    monkeypatch.setenv('ZBC_DB_PATH', str(other_db))
    reset_task_engine()
    assert app.test_client().get(f'/api/ai/tasks/{task_id}').status_code == 403
