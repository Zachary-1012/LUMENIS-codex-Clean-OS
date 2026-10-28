"""Isolated account Agent -> Skill scope continuity; generated identities only."""
import json
import os
import sqlite3
import subprocess
import sys

import pytest
from tests.test_skill_http_durable_identity import skill_client
from tests.test_agent_runtime_http_binding import agent_client
from tests.test_skill_scope_receipts import scoped_skill

SKILL = 'zbc.skill_registry_snapshot'
OWN = {'Authorization': 'Bearer fixture-session-one'}
SCOPE = {'subject_id': 'SCOPE-A', 'brand_focus_id': None, 'global_scope': False}


@pytest.fixture
def bound_agent(agent_client, scoped_skill):
    return agent_client


def submit(api, scope=None):
    response = api.post('/api/ai/tasks', headers=OWN, json={
        'execution_mode': 'agent', 'input': 'Read scoped registry metadata', 'domain_id': 'cth',
        'scope': scope or SCOPE, 'actor_id': 2,
        'steps': [{'skill_id': SKILL, 'input': {}}]})
    assert response.status_code == 202, response.get_json()
    return response.get_json()['task']['task_id']


def run(bound_agent):
    api, app, path = bound_agent
    task_id = submit(api)
    response = api.post(f'/api/ai/tasks/{task_id}/run', headers=OWN)
    assert response.status_code == 200, response.get_json()
    assert response.get_json()['task']['status'] == 'succeeded', response.get_json()
    from lumenis.shared.agents.skills.execution import query_executions
    from agent_runtime.task_binding import _digest
    identifier = 'skillscope_agentstep_' + _digest({'task': task_id, 'skill': SKILL, 'inputs': {}})[:32]
    row = query_executions(execution_id=identifier, strict=True)[0]
    return task_id, row


def assert_restricted_task_projection(task, task_id, expected_status):
    assert set(task) == {
        'task_id', 'task_kind', 'user_input', 'status', 'created_at', 'updated_at',
        'request_id', 'workspace_view',
    }
    assert task['task_id'] == task_id and task['task_kind'] == 'TASK_ENGINE'
    assert task['user_input'] == 'Read scoped registry metadata'
    assert task['status'] == expected_status and task['request_id'] is None
    view = task['workspace_view']
    assert set(view) == {
        'title', 'input', 'status', 'created_at', 'updated_at', 'can_cancel', 'can_resume',
        'output_text', 'work_refs', 'steps', 'error_code', 'result_access_state', 'request_id',
    }
    assert view == {
        'title': 'Read scoped registry metadata',
        'input': 'Read scoped registry metadata',
        'status': expected_status,
        'created_at': task['created_at'],
        'updated_at': task['updated_at'],
        'can_cancel': expected_status in {'pending', 'ready', 'running'},
        'can_resume': False,
        'output_text': None,
        'work_refs': [],
        'steps': [],
        'error_code': None,
        'result_access_state': 'RESTRICTED',
        'request_id': None,
    }
    assert not {'context', 'result', 'error', 'evidence', 'skill_executions'} & set(task)
    assert SKILL not in json.dumps(task, ensure_ascii=False)
    return task


def assert_restricted_task_status(response, task_id, expected_status):
    assert response.status_code == 200, response.get_json()
    envelope = response.get_json()
    assert envelope['ok'] is True
    return assert_restricted_task_projection(envelope['task'], task_id, expected_status)


def test_account_agent_returns_signed_exact_scope_and_task(bound_agent):
    task_id, row = run(bound_agent)
    from lumenis.shared.agents.skills.execution import verified_execution_scope
    scope = verified_execution_scope(row, {'id': 1})
    assert row['user_id'] == 1 and row['execution_id'].startswith('skillscope_agentstep_')
    assert scope and all(scope[k] == v for k, v in SCOPE.items())
    assert verified_execution_scope(row, {'id': 2}) is None
    proof = json.loads(row['evidence_json'])['scope_receipt']
    with sqlite3.connect(bound_agent[2]) as con:
        material = json.loads(con.execute('SELECT inputs_json FROM app_evidence_records WHERE id=?',
                                         (proof['evidence_id'],)).fetchone()[0])['scope_receipt']
    assert material['agent_task']['task_id'] == task_id
    assert len(material['agent_task']['binding_sha256']) == 64
    # The signed Agent child remains inside its Skill owner. Read the actual
    # authorized task through the parent API, and keep direct child IDs private.
    child = bound_agent[0].get('/api/ai/tasks/' + row['execution_id'], headers=OWN)
    assert child.status_code == 404
    parent = bound_agent[0].get('/api/ai/tasks/' + task_id, headers=OWN)
    assert parent.status_code == 200, parent.get_json()
    parent_task = parent.get_json()['task']
    assert parent_task['task_id'] == task_id and parent_task['status'] == 'succeeded'
    assert not {'context', 'result', 'error'} & set(parent_task)
    assert parent_task['workspace_view']['status'] == 'succeeded'
    assert any(step['status'] == 'completed' for step in parent_task['workspace_view']['steps'])
    from ai_task_engine import get_task_engine
    stored = get_task_engine().get_task(task_id)
    child_link = stored['result']['final_step_results'][0]['result']['skill_execution_id']
    assert child_link == row['execution_id']
    timeline = bound_agent[0].get('/api/ai/tasks/' + task_id + '/steps', headers=OWN)
    assert timeline.status_code == 200, timeline.get_json()
    steps = timeline.get_json()['steps']
    assert timeline.get_json()['count'] == len(steps) and steps
    assert all(set(step) == {'label', 'status'} for step in steps)
    assert any(step['status'] == 'completed' for step in steps)


@pytest.mark.parametrize('changed', ['skill_scope', 'missing_skill_scope', 'agent_scope', 'inactive_actor'])
def test_revoked_account_agent_never_runs_tool(bound_agent, monkeypatch, changed):
    api, app, path = bound_agent
    task_id = submit(api)
    with sqlite3.connect(path) as con:
        if changed == 'inactive_actor':
            con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
        else:
            module = SKILL if changed in ('skill_scope', 'missing_skill_scope') else 'agent_runtime'
            con.execute('UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1 AND module=?',
                        (json.dumps({} if changed == 'missing_skill_scope' else {'subject_ids': ['SCOPE-B']}), module))
    from lumenis.shared.agents.skills import execution
    monkeypatch.setattr(execution, 'execute_skill', lambda *a, **kw: pytest.fail('revoked scope reached handler'))
    from agent_runtime.task_binding import _invoke_local_tool
    if changed in ('skill_scope', 'missing_skill_scope'):
        assert _invoke_local_tool(task_id, SKILL)['success'] is False
    else:
        with pytest.raises(PermissionError):
            _invoke_local_tool(task_id, SKILL)


@pytest.mark.parametrize('change', ['actor', 'scope', 'task', 'product', 'execution_id', 'unknown_task'])
def test_account_task_binding_rejects_substitution(bound_agent, change):
    from account.skills import execute_skill_api
    from agent_runtime.task_binding import _digest
    task_id = submit(bound_agent[0])
    args = {'task': 'Read scoped registry metadata', 'input_payload': {}, 'action_type': 'READ',
            'user_id': 1, 'product': 'CTH', '_agent_task_id': task_id, 'scope': SCOPE,
            '_execution_id': 'skillscope_agentstep_' + _digest({'task': task_id, 'skill': SKILL, 'inputs': {}})[:32]}
    if change == 'actor': args['user_id'] = 2
    if change == 'scope': args['scope'] = {**SCOPE, 'subject_id': 'SCOPE-B'}
    if change == 'task': args['task'] = 'Different task'
    if change == 'product': args['product'] = 'BMP'
    if change == 'execution_id': args['_execution_id'] = 'arbitrary-client-id'
    if change == 'unknown_task': args['_agent_task_id'] = 'task_missing'
    assert execute_skill_api(SKILL, **args)['success'] is False


@pytest.mark.parametrize('change', ['scope', 'task', 'receipt', 'skill_grant', 'actor'])
def test_completed_replay_revalidates_task_and_receipt(bound_agent, change):
    task_id, row = run(bound_agent)
    from ai_task_engine import get_task_engine
    from lumenis.shared.agents.skills.execution import verified_execution_scope, query_executions
    from agent_runtime.task_binding import _invoke_local_tool
    with sqlite3.connect(bound_agent[2]) as con:
        if change in ('scope', 'task'):
            task = get_task_engine().get_task(task_id)
            if change == 'scope':
                task['context']['scope']['subject_id'] = 'SCOPE-B'
                con.execute('UPDATE ai_task SET context_json=? WHERE task_id=?', (json.dumps(task['context']), task_id))
            else:
                con.execute("UPDATE ai_task SET user_input='different task' WHERE task_id=?", (task_id,))
        elif change == 'receipt':
            con.execute("UPDATE skill_executions SET evidence_json='{}' WHERE execution_id=?", (row['execution_id'],))
        elif change == 'actor':
            con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
        else:
            con.execute('UPDATE v4_member_authorizations SET data_scope=? WHERE module=?',
                        (json.dumps({'subject_ids': ['SCOPE-B']}), SKILL))
    live = query_executions(execution_id=row['execution_id'], strict=True)[0]
    assert verified_execution_scope(live, {'id': 1}) is None
    with pytest.raises(PermissionError):
        _invoke_local_tool(task_id, SKILL)
    assert bound_agent[0].get('/api/ai/tasks/' + row['execution_id'], headers=OWN).status_code in (401, 404)


def test_revocation_during_agent_tool_cannot_sign_result(bound_agent, monkeypatch):
    from lumenis.shared.agents.skills import execution
    real = execution.execute_skill
    def revoke(*args, **kwargs):
        result = real(*args, **kwargs)
        with sqlite3.connect(bound_agent[2]) as con:
            con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE user_id=1")
        return result
    monkeypatch.setattr(execution, 'execute_skill', revoke)
    task_id = submit(bound_agent[0])
    response = bound_agent[0].post('/api/ai/tasks/' + task_id + '/run', headers=OWN)
    assert response.status_code == 403 and 'task' not in response.get_json()
    from ai_task_engine import get_task_engine
    assert get_task_engine().get_task(task_id)['status'] != 'succeeded'
    assert not execution.query_executions(skill_id=SKILL, strict=True)


def test_signed_agent_skill_scope_survives_cold_reopen(bound_agent):
    task_id, row = run(bound_agent)
    code = '''import sys
from lumenis.system.security import permission
permission._TESTING_BYPASS_ENABLED=False
from lumenis.shared.agents.skills.execution import query_executions, verified_execution_scope
from agent_runtime.task_binding import _invoke_local_tool
row=query_executions(execution_id=sys.argv[1], strict=True)[0]
assert verified_execution_scope(row, {'id':1})['subject_id']=='SCOPE-A'
assert _invoke_local_tool(sys.argv[2], 'zbc.skill_registry_snapshot')['success']
print('COLD_ACCOUNT_AGENT_SCOPE_PASS')
'''
    env = dict(os.environ); env.pop('PERMISSION_GATE_TESTING', None)
    done = subprocess.run([sys.executable, '-B', '-c', code, row['execution_id'], task_id],
                          env=env, capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stdout + done.stderr
    assert 'COLD_ACCOUNT_AGENT_SCOPE_PASS' in done.stdout


def test_agent_scope_is_rechecked_immediately_before_handler(bound_agent, monkeypatch):
    from lumenis.shared.agents.skills import execution
    from agent_runtime.task_binding import _invoke_local_tool
    task_id = submit(bound_agent[0])
    real = execution.action_firewall
    def withdraw(ctx, *args, **kwargs):
        result = real(ctx, *args, **kwargs)
        with sqlite3.connect(bound_agent[2]) as con:
            con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE module=?", (SKILL,))
        return result
    monkeypatch.setattr(execution, 'action_firewall', withdraw)
    monkeypatch.setattr(execution, 'execute_skill', lambda *a, **kw: pytest.fail('withdrawn scope reached handler'))
    assert _invoke_local_tool(task_id, SKILL)['success'] is False


def test_historical_account_agentstep_without_scope_receipt_is_not_readable(bound_agent):
    from lumenis.shared.agents.skills.execution import ensure_skill_executions_table
    ensure_skill_executions_table()
    identifier = 'agentstep_' + '1' * 32
    with sqlite3.connect(bound_agent[2]) as con:
        con.execute("""INSERT INTO skill_executions(execution_id,skill_id,user_id,domain,product,
            task,action_type,input_json,output_json,status,evidence_json)
            VALUES(?, ?, 1, 'cth', 'CTH', 'Historical Agent result', 'READ', '{}',
                   '{"success":true}', 'completed', '{}')""", (identifier, SKILL))
    assert bound_agent[0].get('/api/ai/tasks/' + identifier, headers=OWN).status_code == 404


def test_parent_agent_result_rechecks_child_skill_permission(bound_agent):
    task_id, row = run(bound_agent)
    api, app, path = bound_agent
    from agent_runtime.task_binding import authorize_task_result_read
    from ai_task_engine import get_task_engine
    assert authorize_task_result_read(get_task_engine().get_task(task_id), {'id': 1})
    before = api.get('/api/ai/tasks/' + task_id, headers=OWN)
    assert before.status_code == 200
    with sqlite3.connect(path) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE module=?", (SKILL,))
    status = api.get('/api/ai/tasks/' + task_id, headers=OWN)
    assert_restricted_task_status(status, task_id, 'succeeded')
    for method, suffix in [('get', '/steps'), ('get', '/evidence'), ('post', '/run')]:
        assert getattr(api, method)('/api/ai/tasks/' + task_id + suffix, headers=OWN).status_code == 403
    listing = api.get('/api/ai/tasks', headers=OWN)
    assert listing.status_code == 200, listing.get_json()
    listed = listing.get_json()['tasks']
    assert len(listed) == 1
    assert_restricted_task_projection(listed[0], task_id, 'succeeded')


@pytest.mark.parametrize('change', ['output', 'missing_step', 'receipt', 'other_task'])
def test_parent_agent_result_cannot_substitute_child_evidence(bound_agent, change):
    task_id, row = run(bound_agent)
    from ai_task_engine import get_task_engine
    result = get_task_engine().get_task(task_id)['result']
    with sqlite3.connect(bound_agent[2]) as con:
        if change == 'receipt':
            con.execute("UPDATE skill_executions SET evidence_json='{}' WHERE execution_id=?", (row['execution_id'],))
        elif change == 'missing_step':
            result['final_step_results'] = []
        elif change == 'output':
            result['final_step_results'][0]['result']['result']['result'] = {'foreign': 'unverified content'}
        else:
            other_id, other_row = run(bound_agent)
            result['final_step_results'][0]['result']['skill_execution_id'] = other_row['execution_id']
        if change != 'receipt':
            con.execute('UPDATE ai_task SET result_json=? WHERE task_id=?', (json.dumps(result), task_id))
    status = bound_agent[0].get('/api/ai/tasks/' + task_id, headers=OWN)
    assert_restricted_task_status(status, task_id, 'succeeded')
    for suffix in ('/steps', '/evidence'):
        assert bound_agent[0].get('/api/ai/tasks/' + task_id + suffix, headers=OWN).status_code == 403
    assert bound_agent[0].post('/api/ai/tasks/' + task_id + '/run', headers=OWN).status_code == 403


@pytest.mark.parametrize('status', ['failed', 'cancelled', 'running'])
def test_partial_parent_checkpoint_rechecks_completed_skill(bound_agent, status):
    task_id, row = run(bound_agent)
    with sqlite3.connect(bound_agent[2]) as con:
        con.execute('UPDATE ai_task SET status=?,result_json=NULL WHERE task_id=?', (status, task_id))
        con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE module=?", (SKILL,))
    status_response = bound_agent[0].get('/api/ai/tasks/' + task_id, headers=OWN)
    assert_restricted_task_status(status_response, task_id, status)
    for suffix in ('/steps', '/evidence'):
        assert bound_agent[0].get('/api/ai/tasks/' + task_id + suffix, headers=OWN).status_code == 403


def test_parent_agent_trace_views_recheck_child_skill_permission(bound_agent):
    task_id, row = run(bound_agent)
    api, app, path = bound_agent
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO ai_task_trace(trace_id,task_id,span,detail,status) VALUES(?,?,'fixture','isolated output','ok')", ('trace_fixture_' + task_id, task_id))
    assert api.get('/api/ai/trace?task_id=' + task_id, headers=OWN).get_json()['count'] >= 1
    assert any(item['task_id'] == task_id for item in api.get('/api/ai/trace', headers=OWN).get_json()['traces'])
    with sqlite3.connect(path) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE module=?", (SKILL,))
    assert api.get('/api/ai/trace?task_id=' + task_id, headers=OWN).status_code == 403
    assert not any(item['task_id'] == task_id for item in api.get('/api/ai/trace', headers=OWN).get_json()['traces'])


def test_revoked_child_does_not_remove_original_task_stop_authority(bound_agent, monkeypatch):
    task_id, row = run(bound_agent)
    api, app, path = bound_agent
    with sqlite3.connect(path) as con:
        con.execute("UPDATE ai_task SET status='running',result_json=NULL WHERE task_id=?", (task_id,))
        con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE module=?", (SKILL,))
    from lumenis.shared.agents.skills import execution
    from agent_runtime import task_binding
    monkeypatch.setattr(execution, 'execute_skill', lambda *a, **kw: pytest.fail('cancel must not start a Skill'))
    monkeypatch.setattr(task_binding, '_gateway_request', lambda *a, **kw: pytest.fail('cancel must not call a model'))
    before = execution.query_executions(skill_id=SKILL, strict=True)
    other = {'Authorization': 'Bearer fixture-session-two'}
    assert api.post('/api/ai/tasks/' + task_id + '/cancel', headers=other).status_code == 403
    assert api.get('/api/ai/tasks/' + task_id, headers=other).status_code == 403
    stopped = api.post('/api/ai/tasks/' + task_id + '/cancel', headers=OWN)
    stopped_task = assert_restricted_task_status(stopped, task_id, 'cancelled')
    assert execution.query_executions(skill_id=SKILL, strict=True) == before
    status = api.get('/api/ai/tasks/' + task_id, headers=OWN)
    status_task = assert_restricted_task_status(status, task_id, 'cancelled')
    assert status_task['workspace_view'] == stopped_task['workspace_view']
    assert api.get('/api/ai/tasks/' + task_id + '/steps', headers=OWN).status_code == 403
    assert api.get('/api/ai/tasks/' + task_id + '/evidence', headers=OWN).status_code == 403
