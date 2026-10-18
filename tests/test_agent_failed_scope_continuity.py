"""Failed child outputs are not result authority; isolated real HTTP/SQLite only."""
import json
import sqlite3
import threading

import pytest
from tests.test_skill_http_durable_identity import skill_client
from tests.test_agent_runtime_http_binding import agent_client
from tests.test_skill_scope_receipts import scoped_skill
from tests.test_agent_skill_scope_continuity import bound_agent, submit, run, SKILL, OWN, SCOPE

SENTINEL = 'ISOLATED_UNRECEIPTED_CHILD_OUTPUT_20261018'


def deny_child(path):
    with sqlite3.connect(path) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE user_id=1 AND module=?", (SKILL,))


def assert_unreadable(api, task_id):
    for suffix in ('', '/steps', '/evidence'):
        response = api.get('/api/ai/tasks/' + task_id + suffix, headers=OWN)
        assert response.status_code == 403, (suffix, response.get_json())
        assert SENTINEL not in json.dumps(response.get_json())
    assert api.get('/api/ai/trace?task_id=' + task_id, headers=OWN).status_code == 403
    assert not any(row.get('task_id', row.get('id')) == task_id for row in api.get('/api/ai/tasks', headers=OWN).get_json()['tasks'])
    assert not any(row['task_id'] == task_id for row in api.get('/api/ai/trace', headers=OWN).get_json()['traces'])


def test_concurrent_child_withdrawal_never_checkpoints_unreceipted_output(bound_agent, monkeypatch):
    from lumenis.shared.agents.skills import execution
    from ai_task_engine import get_task_engine
    api, app, path = bound_agent
    finished, withdrawn = threading.Event(), threading.Event()
    real = execution.execute_skill
    errors = []
    def withdraw():
        try:
            assert finished.wait(10)
            deny_child(path)
        except BaseException as exc:
            errors.append(exc)
        finally:
            withdrawn.set()
    def handler(*args, **kwargs):
        result = real(*args, **kwargs)
        result['protected_output'] = SENTINEL
        finished.set()
        assert withdrawn.wait(10)
        return result
    monkeypatch.setattr(execution, 'execute_skill', handler)
    worker = threading.Thread(target=withdraw)
    worker.start()
    task_id = submit(api)
    try:
        response = api.post('/api/ai/tasks/' + task_id + '/run', headers=OWN)
    finally:
        worker.join(10)
    assert not worker.is_alive() and not errors
    assert response.status_code == 403
    assert execution.query_executions(skill_id=SKILL, strict=True) == []
    engine = get_task_engine()
    task = engine.get_task(task_id)
    assert task['status'] == 'failed' and task['result'] is None
    assert SENTINEL not in json.dumps(engine.get_steps(task_id))
    assert_unreadable(api, task_id)
    monkeypatch.setattr(execution, 'execute_skill', lambda *a, **k: pytest.fail('cancel started new child'))
    from agent_runtime import task_binding
    monkeypatch.setattr(task_binding, '_gateway_request', lambda *a, **k: pytest.fail('cancel called model'))
    with sqlite3.connect(path) as con:
        con.execute("UPDATE ai_task SET status='running' WHERE task_id=?", (task_id,))
    other = {'Authorization': 'Bearer fixture-session-two'}
    assert api.post('/api/ai/tasks/' + task_id + '/cancel', headers=other).status_code == 403
    cancelled = api.post('/api/ai/tasks/' + task_id + '/cancel', headers=OWN)
    assert cancelled.status_code == 200
    assert cancelled.get_json()['task'] == {'task_id': task_id, 'status': 'cancelled'}
    assert_unreadable(api, task_id)


@pytest.mark.parametrize('status', ['failed', 'cancelled', 'timeout', 'running'])
@pytest.mark.parametrize('location', ['plan', 'metadata'])
def test_historical_noncompleted_payload_requires_child_proof(bound_agent, status, location):
    api, app, path = bound_agent
    task_id, row = run(bound_agent)
    with sqlite3.connect(path) as con:
        steps = con.execute('SELECT rowid,detail FROM ai_task_step WHERE task_id=?', (task_id,)).fetchall()
        # A legacy failed/interrupted parent may have no final result, but child
        # data in either copy of a checkpoint. Status cannot erase this boundary.
        for rowid, detail in steps:
            envelope = json.loads(detail)
            cp = envelope['checkpoint']
            cp['state'] = status
            cp['metadata'].pop('result', None)
            cp['metadata'].pop('error', None)
            for step in cp['plan_snapshot'].get('steps', []):
                step.update(status=status, result=None, error=None)
            if cp['plan_snapshot'].get('steps'):
                child = {'success': False, 'result': {'protected_output': SENTINEL},
                         'error': 'failed', 'skill_execution_id': row['execution_id']}
                if location == 'plan':
                    cp['plan_snapshot']['steps'][0]['result'] = child
                else:
                    cp['metadata']['result'] = child
            con.execute('UPDATE ai_task_step SET detail=? WHERE rowid=?', (json.dumps(envelope), rowid))
        con.execute('UPDATE ai_task SET status=?,result_json=NULL WHERE task_id=?', (status, task_id))
    assert_unreadable(api, task_id)


def test_authorized_data_free_failure_remains_readable(bound_agent, monkeypatch):
    from lumenis.shared.agents.skills import execution
    from ai_task_engine import get_task_engine
    api, app, path = bound_agent
    monkeypatch.setattr(execution, 'execute_skill', lambda *a, **k: {
        'success': False, 'result': {'protected_partial': SENTINEL}, 'error': SENTINEL,
        'traceback': SENTINEL, 'source': 'custom_handler'})
    task_id = submit(api)
    response = api.post('/api/ai/tasks/' + task_id + '/run', headers=OWN)
    assert response.status_code == 200 and response.get_json()['task']['status'] == 'failed'
    assert SENTINEL not in json.dumps(response.get_json())
    assert SENTINEL not in json.dumps(get_task_engine().get_steps(task_id))
    steps = api.get('/api/ai/tasks/' + task_id + '/steps', headers=OWN)
    assert steps.status_code == 200 and SENTINEL not in json.dumps(steps.get_json())
    deny_child(path)
    assert_unreadable(api, task_id)


@pytest.mark.parametrize('outcome', ['handler_failure', 'signature_failure'])
def test_scoped_account_api_never_returns_failed_handler_data(bound_agent, monkeypatch, outcome):
    from account.skills import execute_skill_api
    from lumenis.shared.agents.skills import execution
    real = execution.execute_skill
    def handler(*args, **kwargs):
        result = real(*args, **kwargs)
        result['protected_output'] = SENTINEL
        if outcome == 'handler_failure':
            result.update(success=False, error=SENTINEL)
        return result
    monkeypatch.setattr(execution, 'execute_skill', handler)
    if outcome == 'signature_failure':
        monkeypatch.setattr(execution, '_record_execution_scope_receipt',
                            lambda *a, **k: (_ for _ in ()).throw(ValueError(SENTINEL)))
    response = execute_skill_api(SKILL, task='Read scoped metadata', input_payload={},
                                action_type='READ', user_id=1, product='CTH', scope=SCOPE)
    assert response['success'] is False and response['result'] is None
    assert response['evidence'] is None and response['evaluation'] is None
    assert SENTINEL not in json.dumps(response)
    assert bound_agent[0].get('/api/ai/tasks/' + response['execution_id'], headers=OWN).status_code == 404


@pytest.mark.parametrize('through_agent', [False, True])
def test_signed_sanitized_success_keeps_usable_result(bound_agent, monkeypatch, through_agent):
    from account.skills import execute_skill_api
    from lumenis.shared.agents.skills import execution
    fake_credential = 'sk-public-fixture-not-a-real-credential'
    monkeypatch.setattr(execution, 'execute_skill', lambda *a, **k: {
        'success': True, 'result': {'count': 3, 'api_key': fake_credential}, 'source': 'custom_handler'})
    if through_agent:
        task_id, row = run(bound_agent)
        response = bound_agent[0].get('/api/ai/tasks/' + task_id + '/steps', headers=OWN)
        assert response.status_code == 200
        assert fake_credential not in json.dumps(response.get_json())
    else:
        result = execute_skill_api(SKILL, task='Read scoped metadata', input_payload={},
                                   action_type='READ', user_id=1, product='CTH', scope=SCOPE)
        assert result['success'] is True, result
        assert result['result']['result'] == {'count': 3}
        assert fake_credential not in json.dumps(result)


@pytest.mark.parametrize('stage', ['handler', 'receipt', 'serialization', 'adapter'])
@pytest.mark.parametrize('revoke', [False, True])
def test_exception_details_are_isolated_before_agent_checkpoint(bound_agent, monkeypatch, stage, revoke):
    from lumenis.shared.agents.skills import execution
    from ai_task_engine import get_task_engine
    api, app, path = bound_agent
    real_execute = execution.execute_skill
    def executed(*args, **kwargs):
        result = real_execute(*args, **kwargs)
        if revoke:
            deny_child(path)
        if stage == 'handler':
            raise RuntimeError(SENTINEL)
        return result
    monkeypatch.setattr(execution, 'execute_skill', executed)
    def fault(*args, **kwargs):
        raise RuntimeError(SENTINEL)
    if stage == 'receipt':
        monkeypatch.setattr(execution, '_record_execution_scope_receipt', fault)
    elif stage == 'serialization':
        original = execution._trace_json
        def serialize(value, *args, **kwargs):
            if isinstance(value, dict) and value.get('source') == 'custom_handler':
                raise RuntimeError(SENTINEL)
            return original(value, *args, **kwargs)
        monkeypatch.setattr(execution, '_trace_json', serialize)
    elif stage == 'adapter':
        import account.skills
        original = account.skills.execute_skill_api
        def adapter(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError(SENTINEL)
        monkeypatch.setattr(account.skills, 'execute_skill_api', adapter)
    task_id = submit(api)
    response = api.post('/api/ai/tasks/' + task_id + '/run', headers=OWN)
    assert response.status_code == (403 if revoke else 200)
    assert SENTINEL not in json.dumps(response.get_json())
    assert SENTINEL not in json.dumps(get_task_engine().get_steps(task_id))
    if revoke:
        assert_unreadable(api, task_id)
    else:
        response = api.get('/api/ai/tasks/' + task_id + '/steps', headers=OWN)
        assert response.status_code == 200 and SENTINEL not in json.dumps(response.get_json())


@pytest.mark.parametrize('status', ['failed', 'cancelled', 'timeout', 'running'])
@pytest.mark.parametrize('location', ['error', 'metadata_error', 'metadata_extra'])
def test_historical_error_and_metadata_cannot_bypass_proof(bound_agent, status, location):
    api, app, path = bound_agent
    task_id, row = run(bound_agent)
    with sqlite3.connect(path) as con:
        for rowid, detail in con.execute('SELECT rowid,detail FROM ai_task_step WHERE task_id=?', (task_id,)).fetchall():
            envelope = json.loads(detail)
            cp = envelope['checkpoint']
            cp['state'] = status
            cp['metadata'].pop('result', None)
            cp['metadata'].pop('error', None)
            for step in cp['plan_snapshot'].get('steps', []):
                step.update(status=status, result=None, error=SENTINEL if location == 'error' else None)
            if location == 'metadata_error':
                cp['metadata']['error'] = SENTINEL
            elif location == 'metadata_extra':
                cp['metadata']['unexpected_output'] = SENTINEL
            con.execute('UPDATE ai_task_step SET detail=? WHERE rowid=?', (json.dumps(envelope), rowid))
        con.execute('UPDATE ai_task SET status=?,result_json=NULL WHERE task_id=?', (status, task_id))
    assert_unreadable(api, task_id)
