"""Existing local Skill/Agent consumers; disposable identities, no model/network."""
import json
import sqlite3

import pytest

from tests.test_skill_http_durable_identity import skill_client
from tests.test_agent_runtime_http_binding import agent_client, submit
from tests.test_registered_skill_background import background, submit as submit_skill
from agent_runtime import task_binding
from agent_runtime.planner import PlanStep
from agent_capability.formation import FormationError


OWN = {'Authorization': 'Bearer fixture-session-one'}


def _state(api, app, identifier):
    from ai_task_engine import get_task_engine
    task = get_task_engine().get_task(identifier)
    context = task_binding.authorized_context(task, {'id': 1})
    return task, context, task_binding._tool_router(task)


def test_formed_agent_call_binds_actual_handler_and_blocks_runtime_replacement(agent_client, monkeypatch):
    api, app, path = agent_client
    identifier = submit(api)
    from lumenis.shared.agents.skills import execution
    with app.test_request_context('/', headers=OWN):
        task, context, router = _state(api, app, identifier)
        step = PlanStep(tool='zbc.skill_registry_snapshot', action='read metadata', expected_output='metadata')
        formed = router.form_step(step, context)
        calls = []
        def changed(ctx, meta):
            calls.append(ctx.execution_id)
            return {'total': 999}
        monkeypatch.setattr(execution, '_execute_builtin_local', changed)
        with pytest.raises(FormationError, match='TOOL_FORMATION_CHANGED'):
            formed.invoke(step, context)
        assert calls == []


def test_registered_json_schema_is_applied_before_formation_and_cannot_expand_source_scope(agent_client):
    api, app, path = agent_client
    from lumenis.shared.agents.skills.execution import registered_background_contract
    from agent_capability.router import ToolDefinition
    info = {'skill_id': 'shared.social_card', 'input_schema_json': json.dumps({
        'type': 'object', 'properties': {'title': {'type': 'string', 'minLength': 3},
            'width': {'type': 'integer'}}, 'required': ['title']}), 'output_schema_json': '{}'}
    contract = registered_background_contract(info)
    tool = ToolDefinition('shared.social_card', 'card', 'local card', input_schema=contract['input_schema'])
    assert tool.validate_params({'title': 'Original', 'width': 1080})[0]
    for body in ({'title': 'a'}, {'title': 'Original', 'width': True},
                 {'title': 'Original', 'source_id': 'foreign'}, {'title': 'Original', '_execution_control': {}}):
        assert tool.validate_params(body)[0] is False
    info['input_schema_json'] = json.dumps({'type': 'object', '$ref': 'https://foreign.invalid/schema'})
    with pytest.raises(ValueError, match='external MCP schema references are forbidden'):
        registered_background_contract(info)


def test_actual_agent_output_schema_failure_is_persistent_and_not_reported_as_completed(agent_client):
    api, app, path = agent_client
    with sqlite3.connect(path) as con:
        con.execute('UPDATE skills_registry SET output_schema_json=? WHERE skill_id=?',
            (json.dumps({'type': 'object', 'properties': {'total': {'type': 'string'}}, 'required': ['total']}),
             'zbc.skill_registry_snapshot'))
    identifier = submit(api)
    response = api.post('/api/ai/tasks/' + identifier + '/run', headers=OWN)
    assert response.status_code == 200, response.get_json()
    task = response.get_json()['task']
    assert task['status'] == 'failed' and task['result'] is None
    fresh = app.test_client().get('/api/ai/tasks/' + identifier, headers=OWN)
    assert fresh.status_code == 200, fresh.get_json()
    assert fresh.get_json()['task']['status'] == 'failed'
    with sqlite3.connect(path) as con:
        row = con.execute('SELECT status,output_json FROM skill_executions').fetchone()
        assert row[0] == 'failed'
        assert json.loads(row[1]).get('result') is None


def test_cancel_control_reaches_actual_skill_and_does_not_cancel_another_task(agent_client, monkeypatch):
    api, app, path = agent_client
    from lumenis.shared.agents.skills import execution
    from agent_runtime.loop import StepExecutionControl
    first, second = submit(api), submit(api)
    original = execution._execute_builtin_local
    observed = []
    def controlled(ctx, meta):
        assert type(ctx.execution_control) is StepExecutionControl
        identity = ctx.request_context['agent_task_id']
        observed.append(identity)
        if identity == first:
            stopped = app.test_client().post('/api/ai/tasks/' + first + '/cancel', headers=OWN)
            assert stopped.status_code == 200
            assert ctx.execution_control.is_cancelled() is True
            ctx.execution_control.check()
            pytest.fail('cancelled task reached a result')
        return original(ctx, meta)
    monkeypatch.setattr(execution, '_execute_builtin_local', controlled)
    cancelled = api.post('/api/ai/tasks/' + first + '/run', headers=OWN)
    assert cancelled.status_code == 200, cancelled.get_json()
    assert cancelled.get_json()['task']['status'] == 'cancelled'
    completed = api.post('/api/ai/tasks/' + second + '/run', headers=OWN)
    assert completed.status_code == 200, completed.get_json()
    assert completed.get_json()['task']['status'] == 'succeeded', completed.get_json()
    assert observed == [first, second]
    assert app.test_client().get('/api/ai/tasks/' + first, headers=OWN).get_json()['task']['status'] == 'cancelled'
    assert app.test_client().get('/api/ai/tasks/' + second, headers=OWN).get_json()['task']['result'] == completed.get_json()['task']['result']
    with sqlite3.connect(path) as con:
        # Opaque server control is never model input, trace, corpus or JSON.
        assert con.execute("SELECT COUNT(*) FROM skill_executions WHERE input_json LIKE '%execution_control%'").fetchone()[0] == 0


def test_queued_skill_pins_implementation_before_worker_and_preserves_terminal_readback(background, monkeypatch):
    api, app, path = background
    from lumenis.shared.agents.skills import execution
    identifier = submit_skill(api)
    calls = []
    def replacement(ctx, meta):
        calls.append(ctx.execution_id)
        return {'total': 99}
    monkeypatch.setattr(execution, '_execute_builtin_local', replacement)
    response = api.post('/api/ai/tasks/' + identifier + '/run', headers=OWN)
    assert response.status_code == 200, response.get_json()
    result = response.get_json()['task']
    assert result['status'] == 'rejected' and result['error'] == 'BACKGROUND_BINDING_CHANGED'
    assert result['output_json'] is None and calls == []
    assert app.test_client().get('/api/ai/tasks/' + identifier, headers=OWN).get_json()['task'] == result


def test_queued_skill_cancel_control_is_separate_for_each_existing_job(background, monkeypatch):
    api, app, path = background
    from lumenis.shared.agents.skills import execution
    from agent_runtime.loop import StepExecutionControl
    original = execution._execute_builtin_local
    identifiers, observed = [], []
    def controlled(ctx, meta):
        assert type(ctx.execution_control) is StepExecutionControl
        observed.append(ctx.execution_id)
        if ctx.execution_id == identifiers[0]:
            assert app.test_client().post('/api/ai/tasks/' + ctx.execution_id + '/cancel', headers=OWN).status_code == 200
            assert ctx.execution_control.is_cancelled()
            ctx.execution_control.check()
            pytest.fail('cancelled Skill reached output')
        return original(ctx, meta)
    monkeypatch.setattr(execution, '_execute_builtin_local', controlled)
    identifiers.extend([submit_skill(api), submit_skill(api)])
    cancelled = api.post('/api/ai/tasks/' + identifiers[0] + '/run', headers=OWN).get_json()['task']
    completed = api.post('/api/ai/tasks/' + identifiers[1] + '/run', headers=OWN).get_json()['task']
    assert cancelled['status'] == 'cancelled' and cancelled['output_json'] is None
    assert completed['status'] == 'completed'
    assert observed == identifiers
    assert app.test_client().get('/api/ai/tasks/' + identifiers[0], headers=OWN).get_json()['task']['status'] == 'cancelled'
    assert app.test_client().get('/api/ai/tasks/' + identifiers[1], headers=OWN).get_json()['task']['output_json'] == completed['output_json']


@pytest.mark.parametrize('invalid_output', [False, True])
def test_immediate_builtin_uses_same_contract_without_external_adapter(skill_client, monkeypatch, invalid_output):
    api, app, path = skill_client
    import lumenis_skill_adapter
    monkeypatch.setattr(lumenis_skill_adapter, 'get_skill_adapter', lambda: pytest.fail('builtin selected an external adapter'))
    if invalid_output:
        with sqlite3.connect(path) as con:
            con.execute('UPDATE skills_registry SET output_schema_json=? WHERE skill_id=?',
                (json.dumps({'type': 'object', 'properties': {'total': {'type': 'string'}}, 'required': ['total']}),
                 'zbc.skill_registry_snapshot'))
    response = api.post('/api/ai/tasks', headers=OWN, json={
        'skill_id': 'zbc.skill_registry_snapshot', 'task': 'Read current local metadata',
        'product': 'CTH', 'action_type': 'READ'})
    assert response.status_code == (409 if invalid_output else 200), response.get_json()
    body = response.get_json()
    assert body['success'] is not invalid_output
    row = app.test_client().get('/api/ai/tasks/' + body['execution_id'], headers=OWN).get_json()['task']
    assert row['status'] == ('failed' if invalid_output else 'completed')
    if invalid_output:
        assert json.loads(row['output_json']).get('result') is None
