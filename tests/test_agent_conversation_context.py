"""Real isolated owner/scope state; synthetic planning never invokes a model."""
import json
import sqlite3

import pytest

from agent_capability.formation import FormationError
from agent_runtime import task_binding
from agent_runtime.planner import Planner, PlanStep
from tests import test_ai_conversation_owner as fixtures
from tests.test_agent_runtime_http_binding import submit

agent_client = fixtures.agent_client
skill_client = fixtures.skill_client


@pytest.fixture
def linked(agent_client):
    api, app, path = agent_client
    from lumenis.ai_hub.routes import ai_bp
    from lumenis.shared.database import migrations
    assert migrations.migrate()
    with sqlite3.connect(path) as con:
        con.executemany("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'SHARED','conversation',?)",
                        [('read',), ('write',)])
    app.register_blueprint(ai_bp, url_prefix='/v4')
    own = {'Authorization': 'Bearer fixture-session-one'}
    task_id = submit(api)
    row = fixtures.create(api, own)
    base = '/v4/ai/conversations/' + row['conversation_id']
    attached = api.post(base + '/tasks', headers=own, json={'task_id': task_id,
        'idempotency_key': 'task-link', 'expected_revision': row['revision']})
    assert attached.status_code == 200, attached.get_json()
    value = {'goal': 'Current professional goal', 'constraints': ['Never publish', 'Budget is 80'],
             'draft': 'Current human writing preserved in full', 'decisions': ['Reject sending'], 'excluded_turn_ids': []}
    saved = api.put(base + '/context', headers=own, json={'value': value, 'idempotency_key': 'human-state',
        'expected_revision': attached.get_json()['revision']})
    assert saved.status_code == 200, saved.get_json()
    return {'api': api, 'app': app, 'path': path, 'task_id': task_id, 'headers': own,
            'base': base, 'value': value, 'revision': saved.get_json()['revision']}


def _state(ws):
    from ai_task_engine import get_task_engine
    task = get_task_engine().get_task(ws['task_id'])
    context = task_binding.authorized_context(task, {'id': 1})
    snapshot = task_binding._conversation_snapshot(task, context)
    return task, context, snapshot


def _change(ws, key='new-state'):
    response = ws['app'].test_client().put(ws['base'] + '/context', headers=ws['headers'], json={
        'value': {**ws['value'], 'draft': 'Newer human revision'}, 'idempotency_key': key,
        'expected_revision': ws['revision']})
    assert response.status_code == 200, response.get_json()
    ws['revision'] = response.get_json()['revision']


def _journal_fixture_measure(request):
    """Protocol fixture only: no actual tokenizer, model, weights or inference."""
    from lumenis.system.ai_gateway import owned_service
    return {'ok': True, 'fits': True, 'prompt_tokens': 100,
        'context_window_tokens': 8192, 'output_token_limit': 2000, 'output_tokens_reserved': request.max_output_tokens,
        'request_sha256': owned_service.owned_service_request_digest(request), 'runtime_sha256': 'a' * 64,
        'tokenizer_identity': 'a' * 64, 'formatter_sha256': 'b' * 64,
        'count_method': 'loaded_runtime_tokenizer', 'generation_performed': False, 'binding_sha256': 'c' * 64}


def _journal_fixture_result(request):
    """Synthetic plan/result receipt for actual Task persistence/recovery tests."""
    from lumenis.system.ai_gateway import owned_service
    return {'ok': True, 'status': 'COMPLETED', 'provider': 'owned', 'operation': 'agent_plan',
        'request_id': request.request_id, 'request_digest': owned_service.owned_service_request_digest(request),
        'run_id': 'synthetic-journal-run', 'model_id': 'synthetic-isolated-model', 'model_revision': 'test', 'recipe': 'test',
        'source_use_policy_sha256': request.source_use_policy_sha256,
        'source_binding_sha256': request.source_binding_sha256,
        'input_revision_sha256': request.input_revision_sha256, 'source_evidence_refs': list(request.source_evidence_refs),
        'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120, 'real_input_bound': True,
        'analysis': {'steps': [{'action': 'Read actual local metadata', 'tool': 'zbc.skill_registry_snapshot',
            'params': {}, 'expected_output': 'metadata', 'risk_level': 'low'}]}}


def test_linked_actor_workspace_human_state_and_request_hashes_are_real_sources(linked):
    ws = linked
    with ws['app'].test_request_context('/', headers=ws['headers']):
        task, context, snapshot = _state(ws)
        assert snapshot['conversations'][0]['human_state'] == ws['value']
        assert snapshot['actor_ref'] == 'actor:1' and not snapshot['permission_grant']
        payload = {**context, 'conversation_context_pack': snapshot, 'committed_step_receipts': []}
        request = task_binding._gateway_request(ws['task_id'], 'bounded task planning', json.dumps(snapshot), payload)
        assert request.source_binding_sha256 != task_binding._digest(task['context'])
        assert request.input_revision_sha256 != task_binding._digest(task['user_input'])
        assert request.source_evidence_refs == ('user-task:' + ws['task_id'],)
        forged = json.loads(json.dumps(payload))
        forged['conversation_context_pack']['conversations'][0]['human_state']['draft'] = 'forged content with copied hash'
        with pytest.raises(PermissionError, match='CONVERSATION_CONTEXT_INVALID'):
            task_binding._gateway_request(ws['task_id'], 'bounded task planning', 'forged', forged)
        with pytest.raises(PermissionError, match='ACTOR_MISMATCH'):
            task_binding.authorized_context(task, {'id': 2})
    _change(ws)
    with ws['app'].test_request_context('/', headers=ws['headers']):
        with pytest.raises(FormationError, match='CONVERSATION_CONTEXT_CHANGED'):
            task_binding._assert_conversation_snapshot(ws['task_id'], snapshot['sha256'])
        fresh = _state(ws)[2]
        assert fresh['sha256'] != snapshot['sha256']


def test_conversation_revocation_blocks_dependent_plans_and_result_reads(linked):
    ws = linked
    with ws['app'].test_request_context('/', headers=ws['headers']):
        task, context, snapshot = _state(ws)
    with sqlite3.connect(ws['path']) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='SHARED' AND module='conversation' AND action='read'")
    with ws['app'].test_request_context('/', headers=ws['headers']):
        with pytest.raises(PermissionError, match='CONVERSATION_CONTEXT_ACCESS_DENIED'):
            task_binding._assert_conversation_snapshot(ws['task_id'], snapshot['sha256'])
        with pytest.raises(PermissionError, match='CONVERSATION_CONTEXT_ACCESS_DENIED'):
            task_binding.authorize_task_result_read(task, context['actor'])
    assert ws['api'].get('/api/ai/tasks/' + ws['task_id'], headers=ws['headers']).status_code == 403


def test_late_plan_is_not_adopted_and_stale_formed_call_never_dispatches(linked, monkeypatch):
    ws = linked
    with ws['app'].test_request_context('/', headers=ws['headers']):
        task, context, snapshot = _state(ws)
        context['conversation_context_pack'] = snapshot
        guard = lambda: task_binding._assert_conversation_snapshot(ws['task_id'], snapshot['sha256'])
        router = task_binding._tool_router(task, snapshot['sha256'])
        step = PlanStep(tool='zbc.skill_registry_snapshot', action='read metadata', expected_output='metadata')
        formed = router.form_step(step, context)
        dispatched = []
        monkeypatch.setattr(task_binding, '_invoke_local_tool', lambda *a, **k: dispatched.append(True))
        def synthetic_response(*args, **kwargs):
            _change(ws)
            return json.dumps({'steps': [{'action': 'read metadata', 'tool': 'zbc.skill_registry_snapshot',
                'params': {}, 'expected_output': 'metadata', 'risk_level': 'low'}]}), 'synthetic-test'
        plan = Planner(ai_chat_func=synthetic_response, context_validator=guard).plan('original task', context=context)
        assert not plan.steps and plan.fallback_reason == 'AGENT_CONVERSATION_CONTEXT_CHANGED'
        with pytest.raises(FormationError):
            formed.invoke(step, context)
        assert dispatched == []


def test_human_edit_after_committed_tool_is_not_adopted_or_reexecuted(linked, monkeypatch):
    ws = linked
    with ws['app'].test_request_context('/', headers=ws['headers']):
        _task, _context, snapshot = _state(ws)
        calls = []
        def committed(*args, **kwargs):
            calls.append('one original commit')
            _change(ws)
            return {'success': True, 'skill_execution_id': 'original-committed-receipt'}
        monkeypatch.setattr(task_binding, '_invoke_local_tool', committed)
        handler = task_binding._bound_local_handler(ws['task_id'], 'zbc.skill_registry_snapshot',
            account=True, conversation_sha256=snapshot['sha256'])
        with pytest.raises(FormationError, match='CONVERSATION_CONTEXT_CHANGED'):
            handler()
        with pytest.raises(FormationError, match='CONVERSATION_CONTEXT_CHANGED'):
            handler()
        assert calls == ['one original commit']


def test_actual_registered_task_records_committed_receipts_without_replaying(linked):
    ws = linked
    result = ws['api'].post('/api/ai/tasks/' + ws['task_id'] + '/run', headers=ws['headers'])
    assert result.status_code == 200, result.get_json()
    assert result.get_json()['task']['status'] == 'succeeded', result.get_json()
    with ws['app'].test_request_context('/', headers=ws['headers']):
        task, context, _snapshot = _state(ws)
        receipts = task_binding._committed_step_receipts(task, context)
        assert len(receipts) == 1 and receipts[0]['state'] == 'COMMITTED_ALREADY_EXECUTED'
        assert receipts[0]['replay_allowed'] is False
    with sqlite3.connect(ws['path']) as con:
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 1
    repeated = ws['api'].post('/api/ai/tasks/' + ws['task_id'] + '/run', headers=ws['headers'])
    assert repeated.get_json()['task']['status'] == 'succeeded'
    with sqlite3.connect(ws['path']) as con:
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 1


def test_required_human_pack_survives_real_gateway_budget_consumer_optional_eviction(linked, monkeypatch):
    from lumenis.system.ai_gateway import core, owned_service
    ws = linked
    calls = []
    def measured(request):
        return {'ok': True, 'fits': 'optional-large-memory' not in request.user_payload,
                'prompt_tokens': 100, 'binding_sha256': 'd' * 64, 'count_method': 'synthetic_fixture_only'}
    def synthetic_gateway(request, **kwargs):
        calls.append(request)
        return {'ok': True, 'status': 'COMPLETED', 'provider': 'owned', 'operation': 'agent_plan',
            'request_id': request.request_id, 'request_digest': owned_service.owned_service_request_digest(request),
            'run_id': 'synthetic-run', 'model_id': 'synthetic-test-runtime', 'model_revision': 'test', 'recipe': 'test',
            'source_use_policy_sha256': request.source_use_policy_sha256,
            'source_binding_sha256': request.source_binding_sha256,
            'input_revision_sha256': request.input_revision_sha256, 'source_evidence_refs': list(request.source_evidence_refs),
            'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120, 'real_input_bound': True,
            'analysis': {'steps': [{'action': 'Read metadata', 'tool': 'zbc.skill_registry_snapshot',
                'params': {}, 'expected_output': 'metadata', 'risk_level': 'low'}]}}
    monkeypatch.setattr(owned_service, 'measure_owned_request', measured)
    monkeypatch.setattr(owned_service, 'owned_service_status', lambda _: {'binding_sha256': 'd' * 64})
    monkeypatch.setattr(core, 'run_owned_request', synthetic_gateway)
    with ws['app'].test_request_context('/', headers=ws['headers']):
        task, context, snapshot = _state(ws)
        context.update(conversation_context_pack=snapshot, committed_step_receipts=[],
                       derived_memory=['optional-large-memory'])
        planner = Planner(gateway_request_factory=lambda system, user, ctx:
            task_binding._gateway_request(ws['task_id'], system, user, ctx),
            context_validator=lambda: task_binding._assert_conversation_snapshot(ws['task_id'], snapshot['sha256']))
        plan = planner.plan(task['user_input'], context=context)
    assert plan.steps and len(calls) == 1
    assert ws['value']['draft'] in calls[0].user_payload and 'Never publish' in calls[0].user_payload
    assert 'optional-large-memory' not in calls[0].user_payload
    assert plan.context_budget['required_context_sha256'] == snapshot['sha256']
    assert plan.context_budget['omitted_sections'][0]['section'] == 'derived_memory'
    assert context['derived_memory'] == ['optional-large-memory']


def test_linked_task_keeps_complete_100_turn_input_and_reopens_coverage(linked):
    ws = linked
    first = None
    for index in range(100):
        text = ('Hard constraint: never publish; budget 80; deadline 2026-10-30; ' if index < 30 else
                'Professional revision preserving original writing; ') + str(index)
        response = ws['api'].post(ws['base'] + '/turns', headers=ws['headers'], json={
            'text': text, 'idempotency_key': 'long-turn-' + str(index), 'expected_revision': ws['revision']})
        assert response.status_code == 200, response.get_json()
        result = response.get_json()
        ws['revision'] = result['revision']
        first = first or result['turn']['turn_id']
    with ws['app'].test_request_context('/', headers=ws['headers']):
        _task, _context, snapshot = _state(ws)
        pack = snapshot['conversations'][0]
        assert len(pack['history']) == 101
        assert all('Hard constraint: never publish' in turn['content'] for turn in pack['history'][:30])
        assert pack['context_accounting']['history_turns_total'] == 100
        assert pack['omitted_reference_turns'][0]['reason'] == 'source_use_not_granted'
        assert pack['permission_grant'] is False
    endpoint = '/api/ai/tasks/' + ws['task_id'] + '/context'
    reopened = ws['app'].test_client().get(endpoint, headers=ws['headers'])
    assert reopened.status_code == 200, reopened.get_json()
    dto = reopened.get_json()
    assert dto['context_snapshot_sha256'] == snapshot['sha256']
    assert 'history' not in dto['conversations'][0]
    assert dto['conversations'][0]['context_accounting']['coverage'][0]['turn_id'] == first
    assert dto['model_execution'] == 'NOT_RUN' and dto['external_source_content'] == 'NOT_READ'
    assert ws['api'].get(endpoint + '?actor_id=2', headers=ws['headers']).status_code == 400
    assert ws['api'].get(endpoint, headers={'Authorization': 'Bearer fixture-session-two'}).status_code == 403


def test_new_user_turn_and_cancellation_fence_old_plans(linked):
    ws = linked
    with ws['app'].test_request_context('/', headers=ws['headers']):
        _task, _context, snapshot = _state(ws)
    response = ws['api'].post(ws['base'] + '/turns', headers=ws['headers'], json={
        'text': 'Correction: no spending, keep the original draft', 'idempotency_key': 'new-user-turn',
        'expected_revision': ws['revision']})
    assert response.status_code == 200
    with ws['app'].test_request_context('/', headers=ws['headers']):
        with pytest.raises(FormationError, match='CONVERSATION_CONTEXT_CHANGED'):
            task_binding._assert_conversation_snapshot(ws['task_id'], snapshot['sha256'])
        fresh = _state(ws)[2]
    assert ws['api'].post('/api/ai/tasks/' + ws['task_id'] + '/cancel', headers=ws['headers']).status_code == 200
    with ws['app'].test_request_context('/', headers=ws['headers']):
        with pytest.raises(FormationError, match='USER_CANCELLED'):
            task_binding._assert_conversation_snapshot(ws['task_id'], fresh['sha256'])


def test_agent_source_validator_binds_exact_live_user_context_and_rejects_injected_sources(linked):
    from dataclasses import replace
    from agent_runtime.planner import _PLANNER_SYSTEM_PROMPT
    ws = linked
    with ws['app'].test_request_context('/', headers=ws['headers']):
        task, current, _snapshot = _state(ws)
        context = task_binding._planner_context(task, current)
        user = Planner()._build_user_prompt(task['user_input'], context, 8)
        request = task_binding._gateway_request(ws['task_id'], _PLANNER_SYSTEM_PROMPT, user, context)
        request = replace(request, response_schema_json=json.dumps(
            Planner._response_schema(8), ensure_ascii=False, sort_keys=True, allow_nan=False))
        decision = task_binding.validate_agent_source_use(request, actor={'id': 1})
        assert decision.allowed and decision.code == 'AGENT_SOURCE_USE_VERIFIED'
        assert decision.scope_audit_id and decision.source_audit_id
        # A valid actor/task scope cannot authorize stored material bodies.
        injected = {**context, 'derived_memory': [{'text': 'unadmitted stored source'}]}
        forged = replace(request, user_payload=Planner()._build_user_prompt(task['user_input'], injected, 8))
        with pytest.raises(PermissionError, match='MODEL_SOURCE_USE_REQUIRED'):
            task_binding.validate_agent_source_use(forged, actor={'id': 1})
        with pytest.raises(PermissionError, match='MODEL_INPUT_BINDING_INVALID'):
            task_binding.validate_agent_source_use(replace(request, system_prompt='invented system instruction'), actor={'id': 1})
        with pytest.raises(PermissionError, match='ACTOR_MISMATCH'):
            task_binding.validate_agent_source_use(request, actor={'id': 2})
    _change(ws, 'validator-new-human-state')
    with ws['app'].test_request_context('/', headers=ws['headers']):
        with pytest.raises(PermissionError, match='MODEL_SOURCE_USE_REQUIRED'):
            task_binding.validate_agent_source_use(request, actor={'id': 1})


def test_agent_source_validator_rechecks_human_correction_during_permission(linked, monkeypatch):
    from dataclasses import replace
    from agent_runtime.planner import _PLANNER_SYSTEM_PROMPT
    from lumenis.system.security import permission
    ws = linked
    with ws['app'].test_request_context('/', headers=ws['headers']):
        task, current, _snapshot = _state(ws)
        context = task_binding._planner_context(task, current)
        user = Planner()._build_user_prompt(task['user_input'], context, 8)
        request = task_binding._gateway_request(ws['task_id'], _PLANNER_SYSTEM_PROMPT, user, context)
        request = replace(request, response_schema_json=json.dumps(
            Planner._response_schema(8), ensure_ascii=False, sort_keys=True, allow_nan=False))
        gate = permission.get_permission_gate()
        check = gate.check
        def concurrent_correction(operation, *args, **kwargs):
            result = check(operation, *args, **kwargs)
            if operation == permission.OperationType.AI_CALL:
                _change(ws, 'permission-race-correction')
            return result
        monkeypatch.setattr(gate, 'check', concurrent_correction)
        with pytest.raises(PermissionError, match='MODEL_SOURCE_CHANGED'):
            task_binding.validate_agent_source_use(request, actor={'id': 1})


@pytest.mark.parametrize('stop_reason', ['cancel', 'deadline'])
def test_existing_task_model_consumer_cooperatively_stops_before_late_adoption(linked, monkeypatch, stop_reason):
    """Actual Task/queue/Planner path, synthetic Gateway response; no model run."""
    from lumenis.system.ai_gateway import core, owned_service
    from agent_runtime.loop import AgentLoop
    from lumenis.shared.agents.skills.execution import ensure_skill_executions_table
    ws = linked
    ensure_skill_executions_table()
    identifier = submit(ws['api'], model=True)
    attached = ws['api'].post(ws['base'] + '/tasks', headers=ws['headers'], json={
        'task_id': identifier, 'idempotency_key': 'model-task-link', 'expected_revision': ws['revision']})
    assert attached.status_code == 200, attached.get_json()
    observed = []
    class ObservableLoop(AgentLoop):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            observed.append(self)
    monkeypatch.setattr(task_binding, 'AgentLoop', ObservableLoop)
    monkeypatch.setattr(owned_service, 'measure_owned_request', lambda request: {
        'ok': True, 'fits': True, 'binding_sha256': 'e' * 64, 'prompt_tokens': 100,
        'count_method': 'synthetic_unit_counter_not_model_measurement'})
    monkeypatch.setattr(owned_service, 'owned_service_status', lambda domain: {'binding_sha256': 'e' * 64})
    calls = []
    def synthetic_inference(request, **control):
        calls.append(request)
        assert control['is_cancelled']() is False
        if stop_reason == 'cancel':
            stopped = ws['api'].post('/api/ai/tasks/' + identifier + '/cancel', headers=ws['headers'])
            assert stopped.status_code == 200, stopped.get_json()
        else:
            # Advance this loop's elapsed budget only, without a sleep or
            # changing the machine clock, other tasks or model settings.
            observed[-1]._start_time -= 61
        assert control['is_cancelled']() is True
        return {'ok': False, 'status': 'CANCELLED', 'code': 'OWNED_SERVICE_CANCELLED'}
    monkeypatch.setattr(core, 'run_owned_request', synthetic_inference)
    result = ws['api'].post('/api/ai/tasks/' + identifier + '/run', headers=ws['headers'])
    assert result.status_code == 200, result.get_json()
    task = result.get_json()['task']
    assert task['status'] == ('cancelled' if stop_reason == 'cancel' else 'failed'), task
    if stop_reason == 'deadline':
        assert 'AGENT_TASK_DEADLINE_EXCEEDED' in task['error']
    assert len(calls) == 1 and task['result'] is None
    with sqlite3.connect(ws['path']) as con:
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 0


@pytest.mark.parametrize('crash_at', ['unknown_inference_result', 'committed_model_receipt', 'changed_human_context'])
def test_model_attempt_cold_recovery_never_replays_inference(linked, monkeypatch, crash_at):
    """Synthetic inference, actual durable Task/queue/result/Skill recovery."""
    from ai_task_engine import reset_task_engine
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    from lumenis.system.ai_gateway import core, owned_service
    from lumenis.system.collector.guard import task_queue
    from lumenis.shared.agents.skills.execution import ensure_skill_executions_table
    ws = linked
    ensure_skill_executions_table()
    identifier = submit(ws['api'], model=True)
    calls = []
    def synthetic_inference(request, **kwargs):
        calls.append(request)
        if crash_at == 'unknown_inference_result':
            raise SystemExit(90)
        return _journal_fixture_result(request)
    monkeypatch.setattr(owned_service, 'measure_owned_request', _journal_fixture_measure)
    monkeypatch.setattr(owned_service, 'owned_service_status', lambda domain: {'binding_sha256': 'c' * 64})
    monkeypatch.setattr(core, 'run_owned_request', synthetic_inference)
    record = DurableExecutionAdapter.record_model_response
    def commit_then_die(self, *args):
        record(self, *args)
        raise SystemExit(91)
    with monkeypatch.context() as crash:
        if crash_at != 'unknown_inference_result':
            crash.setattr(DurableExecutionAdapter, 'record_model_response', commit_then_die)
        with pytest.raises(SystemExit):
            ws['api'].post('/api/ai/tasks/' + identifier + '/run', headers=ws['headers'])
    assert len(calls) == 1
    with sqlite3.connect(ws['path']) as con:
        journal = con.execute("SELECT status,detail FROM ai_task_step WHERE task_id=? AND phase='agent_model_request'",
                              (identifier,)).fetchall()
        assert len(journal) == 1
        assert journal[0][0] == ('running' if crash_at == 'unknown_inference_result' else 'completed')
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 0
    # Reopen canonical owners, then legitimately reclaim only this expired
    # isolated attempt. No completed request/effect is dispatched again.
    reset_task_engine()
    if crash_at == 'changed_human_context':
        linked_now = ws['api'].post(ws['base'] + '/tasks', headers=ws['headers'], json={
            'task_id': identifier, 'idempotency_key': 'changed-model-human-context', 'expected_revision': ws['revision']})
        assert linked_now.status_code == 200, linked_now.get_json()
    with sqlite3.connect(task_queue.DEFAULT_PATH) as con:
        con.execute('UPDATE tasks SET last_heartbeat_at=0')
    queue = task_queue.TaskQueue()
    try:
        queue.reap_stale(90)
    finally:
        queue.close()
    with sqlite3.connect(task_queue.DEFAULT_PATH) as con:
        con.execute('UPDATE tasks SET scheduled_at=0')
    def no_replay(*args, **kwargs):
        pytest.fail('Cold recovery repeated model measurement or inference')
    monkeypatch.setattr(core, 'run_owned_request', no_replay)
    monkeypatch.setattr(owned_service, 'measure_owned_request', no_replay)
    response = ws['app'].test_client().post('/api/ai/tasks/' + identifier + '/run', headers=ws['headers'])
    assert response.status_code == 200, response.get_json()
    task = response.get_json()['task']
    assert task['status'] == ('succeeded' if crash_at == 'committed_model_receipt' else 'failed'), task
    if crash_at == 'unknown_inference_result':
        assert task['error'] == 'AGENT_MODEL_RESULT_UNKNOWN_NO_REPLAY'
    elif crash_at == 'changed_human_context':
        assert task['error'] == 'AGENT_MODEL_INPUT_CHANGED_NO_REPLAY'
    else:
        reopened = ws['app'].test_client().get('/api/ai/tasks/' + identifier, headers=ws['headers'])
        assert reopened.status_code == 200 and reopened.get_json()['task']['result'] == task['result']
    with sqlite3.connect(ws['path']) as con:
        assert con.execute("SELECT COUNT(*) FROM ai_task_step WHERE task_id=? AND phase='agent_model_request'",
                           (identifier,)).fetchone()[0] == 1
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == (crash_at == 'committed_model_receipt')


def test_model_receipt_real_process_exit_recovers_without_inference_replay(linked, monkeypatch):
    """Windows-compatible real process death; model output is a named fixture."""
    import os
    import subprocess
    import sys
    from ai_task_engine import reset_task_engine
    from lumenis.system.ai_gateway import core, owned_service
    from lumenis.system.collector.guard import task_queue
    ws = linked
    identifier = submit(ws['api'], model=True)
    code = '''import os,sys,socket,pathlib,urllib.parse
def denied(*args,**kwargs): raise RuntimeError('ISOLATED_MODEL_WORKER_NETWORK_FORBIDDEN')
socket.socket.connect=socket.socket.connect_ex=socket.socket.bind=socket.socket.sendto=socket.create_connection=denied
root=pathlib.Path(sys.argv[2]).parent.resolve()
def guard(event,args):
 if event=='sqlite3.connect':
  value=str(args[0]); value=urllib.parse.unquote(value[5:].split('?',1)[0]).lstrip('/') if value.startswith('file:') else value
  if value!=':memory:' and not pathlib.Path(value).resolve().is_relative_to(root): raise RuntimeError('ISOLATED_MODEL_WORKER_DB_BOUNDARY')
sys.addaudithook(guard)
os.environ['ZBC_DB_PATH']=sys.argv[2]
from flask import Flask
from lumenis.system.security import permission
permission._TESTING_BYPASS_ENABLED=False
from lumenis.system.collector.guard import task_queue
task_queue.DEFAULT_PATH=pathlib.Path(sys.argv[3])
from lumenis.system.ai_gateway import core,owned_service
from tests.test_agent_conversation_context import _journal_fixture_measure,_journal_fixture_result
owned_service.measure_owned_request=_journal_fixture_measure
owned_service.owned_service_status=lambda domain:{'binding_sha256':'c'*64}
core.run_owned_request=lambda request,**kwargs:_journal_fixture_result(request)
from agent_runtime.durable_adapter import DurableExecutionAdapter
record=DurableExecutionAdapter.record_model_response
def commit_then_exit(self,*args):
 record(self,*args)
 os._exit(92)
DurableExecutionAdapter.record_model_response=commit_then_exit
from ai_api import bp
app=Flask(__name__);app.register_blueprint(bp)
response=app.test_client().post('/api/ai/tasks/'+sys.argv[1]+'/run',headers={'Authorization':'Bearer fixture-session-one'})
print(response.status_code,response.get_json(),flush=True)
'''
    environment = dict(os.environ)
    environment.pop('PERMISSION_GATE_TESTING', None)
    child = subprocess.run([sys.executable, '-X', 'utf8', '-c', code, identifier,
                            str(ws['path']), str(task_queue.DEFAULT_PATH)], env=environment,
                           capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert child.returncode == 92, child.stdout + child.stderr
    with sqlite3.connect(ws['path']) as con:
        stored = con.execute("SELECT status,detail FROM ai_task_step WHERE task_id=? AND phase='agent_model_request'",
                             (identifier,)).fetchall()
        assert len(stored) == 1 and stored[0][0] == 'completed'
        assert json.loads(stored[0][1])['recovery'] == 'IMMUTABLE_RESULT_NO_MODEL_REPLAY'
    reset_task_engine()
    with sqlite3.connect(task_queue.DEFAULT_PATH) as con:
        con.execute('UPDATE tasks SET last_heartbeat_at=0')
    queue = task_queue.TaskQueue()
    try:
        queue.reap_stale(90)
    finally:
        queue.close()
    with sqlite3.connect(task_queue.DEFAULT_PATH) as con:
        con.execute('UPDATE tasks SET scheduled_at=0')
    def no_replay(*args, **kwargs):
        pytest.fail('New process recovery replayed model inference or token measurement')
    monkeypatch.setattr(core, 'run_owned_request', no_replay)
    monkeypatch.setattr(owned_service, 'measure_owned_request', no_replay)
    response = ws['app'].test_client().post('/api/ai/tasks/' + identifier + '/run', headers=ws['headers'])
    assert response.status_code == 200, response.get_json()
    assert response.get_json()['task']['status'] == 'succeeded', response.get_json()
    reopened = ws['app'].test_client().get('/api/ai/tasks/' + identifier, headers=ws['headers'])
    assert reopened.status_code == 200
    assert reopened.get_json()['task']['result'] == response.get_json()['task']['result']
    with sqlite3.connect(ws['path']) as con:
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 1


def test_actual_gateway_envelope_reaches_agent_journal_and_local_skill_once(linked, monkeypatch):
    """Real Gateway/SourceUse/Task consumers; hermetic fake model binding only."""
    from dataclasses import replace
    from agent_capability.formation import implementation_identity
    from lumenis.system.ai_gateway import owned_service
    from tests import test_owned_service as fixture
    ws = linked
    identifier = submit(ws['api'], model=True)
    policy = task_binding.agent_source_use_policy()
    request = replace(fixture._admission_request(
        source_hash=implementation_identity(task_binding.validate_agent_source_use)),
        source_use_sha256=task_binding._digest(policy), source_use_version=policy['schema'],
        allowed_operations=('agent_plan',), context_window_tokens=32768, output_token_limit=2000)
    binding, runtime = fixture._binding(monkeypatch, request, caller='actor:1',
        source_validator=task_binding.validate_agent_source_use)
    from ai_task_engine import get_task_engine
    from agent_runtime.planner import _PLANNER_SYSTEM_PROMPT
    with ws['app'].test_request_context('/', headers=ws['headers']):
        original = get_task_engine().get_task(identifier)
        context = task_binding._planner_context(original, task_binding.authorized_context(original))
        user = Planner()._build_user_prompt(original['user_input'], context, 15)
        typed = task_binding._gateway_request(identifier, _PLANNER_SYSTEM_PROMPT, user, context)
        typed = replace(typed, response_schema_json=json.dumps(Planner._response_schema(15),
            ensure_ascii=False, sort_keys=True, allow_nan=False))
        assert typed.scope == 'GLOBAL / ALL'
    text = '<|start|>assistant<|channel|>final<|message|>' + json.dumps({'steps': [{
        'action': 'Read actual metadata', 'tool': 'zbc.skill_registry_snapshot', 'params': {},
        'expected_output': 'metadata', 'risk_level': 'low'}]}) + '<|return|>'
    runtime.output_override = {**fixture._runtime_output(typed, runtime, text),
                               'prompt_tokens': 17, 'total_tokens': 21}
    assert not owned_service._SLOTS
    try:
        owned_service.bind_owned_service(binding)
        response = ws['api'].post('/api/ai/tasks/' + identifier + '/run', headers=ws['headers'])
        assert response.status_code == 200, response.get_json()
        task = response.get_json()['task']
        assert task['status'] == 'succeeded', task
        assert runtime.generated == 1
        with sqlite3.connect(ws['path']) as con:
            detail = con.execute("SELECT detail FROM ai_task_step WHERE task_id=? AND phase='agent_model_request'",
                                 (identifier,)).fetchone()
            assert json.loads(detail[0])['result']['operation'] == 'agent_plan'
            assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 1
        repeated = ws['api'].post('/api/ai/tasks/' + identifier + '/run', headers=ws['headers'])
        assert repeated.get_json()['task']['result'] == task['result']
        assert runtime.generated == 1
    finally:
        owned_service._SLOTS.clear()
