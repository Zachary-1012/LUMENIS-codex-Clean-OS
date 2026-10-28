"""Actual conversation/Gateway/Permission consumers; inference is synthetic only."""
from dataclasses import replace
import json

import pytest

from tests.test_ai_conversation_owner import conversation_client, create, append
from tests.test_agent_runtime_http_binding import agent_client
from tests.test_skill_http_durable_identity import skill_client
from tests.test_owned_service import _binding, _admission_request
from agent_capability.formation import implementation_identity
from lumenis.ai_hub import conversations, service
from lumenis.system.ai_gateway import owned_service


@pytest.fixture
def owned_conversation(conversation_client, monkeypatch):
    api, app, path = conversation_client
    owned_service._SLOTS.clear()
    from lumenis.system.ai_gateway import user_api_adapter
    monkeypatch.setattr(user_api_adapter, 'is_selected', lambda: False)
    with app.test_request_context('/', headers={'Host': 'localhost'}, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        actor = conversations.current_actor('write')
        con = conversations._connect()
        try:
            actor_ref, _ = conversations._identity(actor, 'write', con)
        finally:
            con.close()
    policy = conversations.conversation_source_use_policy()
    admission = replace(_admission_request(domain='shared', source_hash=implementation_identity(conversations.validate_conversation_source_use)),
        scopes=('shared_workspace:v1',), source_use_sha256=policy['sha256'], source_use_version=policy['version'],
        allowed_operations=(policy['operation'],), context_window_tokens=32768, output_token_limit=2048)
    binding, runtime = _binding(monkeypatch, admission, caller=actor_ref,
                                source_validator=conversations.validate_conversation_source_use)
    observed = owned_service.bind_owned_service(binding)
    assert observed['ok'], observed
    yield api, app, path, actor, runtime
    owned_service._SLOTS.clear()


def test_actual_owned_conversation_preserves_complete_context_provenance_and_reopen(owned_conversation, monkeypatch):
    api, app, path, actor, runtime = owned_conversation
    monkeypatch.setattr(service, 'retrieve', lambda *a, **kw: pytest.fail('conversation read business sources'))
    monkeypatch.setattr(service, '_run_owned', lambda *a, **kw: pytest.fail('typed response used legacy unbound path'))
    row = create(api)
    for i in range(40):
        append(api, row, ('Original authored constraints ' + str(i) + ' ') * 40, 'history-' + str(i))
    question = append(api, row, 'Use my complete original writing', 'current')
    root = '/v4/ai/conversations/' + row['conversation_id']
    endpoint = root + '/turns/' + question['turn_id'] + '/respond'
    seen = []
    def inspect_current_input():
        current = conversations.read_conversation(actor, row['conversation_id'], limit=100)
        request = conversations.build_conversation_owned_request(actor, row['conversation_id'], current['turns'][-1]['turn_id'])
        seen.append(json.loads(request.user_payload)['material'])
    runtime.on_generate = inspect_current_input
    response = api.post(endpoint, json={'idempotency_key': 'reply', 'expected_revision': row['revision']})
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    turn = body['turn']
    assert turn['state'] == 'completed', body
    assert turn['content']['text'] == 'A grounded answer.'
    proof = turn['content']['owned_provenance']
    assert proof['operation'] == 'conversation_response' and proof['domain_id'] == 'shared'
    assert proof['scope'] == 'shared_workspace:v1' and proof['quality_state'] == 'NOT_EVALUATED'
    assert proof['product_acceptance'] is False and len(proof['request_digest']) == 64
    assert turn['content']['context_accounting']['history_turns_included'] == 40
    assert turn['content']['context_accounting']['token_budget_verified'] is True
    assert len(seen) == 1 and len(seen[0]['history']) == 40
    assert seen[0]['history'][0]['content'] == 'Original authored constraints 0 ' * 40
    assert sum(len(item['content']) for item in seen[0]['history']) > 32000
    with app.test_request_context('/', headers={'Host': 'localhost'}, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        current = conversations.read_conversation(actor, row['conversation_id'], limit=100)
        assert current['turns'][-1]['content'] == turn['content']
    replay = api.post(endpoint, json={'idempotency_key': 'reply', 'expected_revision': 1})
    assert replay.status_code == 200 and replay.get_json()['idempotent_hit'] is True
    assert runtime.generated == 1


def test_actual_owned_response_cancellation_does_not_stop_another_conversation(owned_conversation):
    api, app, path, actor, runtime = owned_conversation
    row = create(api); user = append(api, row)
    root = '/v4/ai/conversations/' + row['conversation_id']
    endpoint = root + '/turns/' + user['turn_id'] + '/respond'
    def stop():
        current = api.get(root).get_json()['conversation']
        pending = current['turns'][-1]
        stopped = app.test_client().post(root + '/turns/' + pending['turn_id'] + '/respond', json={
            'operation': 'interrupt', 'confirmed': True, 'expected_revision': current['revision']})
        assert stopped.status_code == 200, stopped.get_json()
        assert stopped.get_json()['external_call_stopped'] is False
    runtime.on_generate = stop
    interrupted = api.post(endpoint, json={'idempotency_key': 'reply', 'expected_revision': row['revision']})
    assert interrupted.status_code == 409, interrupted.get_json()
    current = api.get(root).get_json()['conversation']
    assert current['turns'][-1]['state'] == 'interrupted'
    assert 'text' not in current['turns'][-1]['content']
    runtime.on_generate = None
    other = create(api); other_user = append(api, other, 'Independent original question')
    completed = api.post('/v4/ai/conversations/' + other['conversation_id'] + '/turns/' + other_user['turn_id'] + '/respond',
        json={'idempotency_key': 'reply', 'expected_revision': other['revision']})
    assert completed.status_code == 200 and completed.get_json()['turn']['state'] == 'completed', completed.get_json()
    resumed = api.post(endpoint, json={'idempotency_key': 'explicit-new-attempt', 'retry_confirmed': True,
                                      'expected_revision': current['revision']})
    assert resumed.status_code == 200 and resumed.get_json()['turn']['state'] == 'completed', resumed.get_json()
    assert api.get(root).get_json()['conversation']['turns'][-2]['state'] == 'interrupted'


def test_pending_source_validator_rejects_injection_and_current_human_context_change(owned_conversation, monkeypatch):
    api, app, path, actor, runtime = owned_conversation
    row = create(api); user = append(api, row)
    root = '/v4/ai/conversations/' + row['conversation_id']
    with monkeypatch.context() as patch:
        patch.setattr(service, 'chat', lambda *a, **kw: (_ for _ in ()).throw(SystemExit(23)))
        with pytest.raises(SystemExit):
            api.post(root + '/turns/' + user['turn_id'] + '/respond', json={'idempotency_key': 'pending', 'expected_revision': row['revision']})
    current = api.get(root).get_json()['conversation']; pending = current['turns'][-1]
    with app.test_request_context('/', headers={'Host': 'localhost'}, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        request = conversations.build_conversation_owned_request(actor, row['conversation_id'], pending['turn_id'])
        decision = conversations.validate_conversation_source_use(request, actor=actor)
        assert decision.allowed and decision.domain_id == 'shared'
        body = json.loads(request.user_payload); body['material']['sources'] = [{'body': 'unauthorized task source'}]
        for changed in (replace(request, user_payload=json.dumps(body)), replace(request, actor_ref='actor:2'),
                        replace(request, domain_id='cth'), replace(request, max_output_tokens=1)):
            with pytest.raises(PermissionError, match='CONVERSATION_INPUT_OR_POLICY_CHANGED'):
                conversations.validate_conversation_source_use(changed, actor=actor)
        value = {'goal': 'Use revised writing', 'constraints': ['do not publish'], 'draft': 'Updated human text',
                 'decisions': [], 'excluded_turn_ids': []}
        conversations.update_context(actor, row['conversation_id'], value=value, idempotency_key='changed',
                                     expected_revision=current['revision'])
        with pytest.raises(PermissionError, match='CONVERSATION_CONTEXT_CHANGED'):
            conversations.validate_conversation_source_use(request, actor=actor)
    assert runtime.generated == 0


def test_actual_late_response_keeps_manual_revision_and_explicit_recovery(owned_conversation):
    api, app, path, actor, runtime = owned_conversation
    row = create(api); user = append(api, row, 'Continue my original manuscript')
    root = '/v4/ai/conversations/' + row['conversation_id']
    endpoint = root + '/turns/' + user['turn_id'] + '/respond'
    value = {'goal': 'Finish revised manuscript', 'draft': 'Retain this human edit completely',
             'constraints': ['do not publish'], 'decisions': ['use revised text'], 'excluded_turn_ids': []}
    def edit():
        current = conversations.read_context(actor, row['conversation_id'])
        conversations.update_context(actor, row['conversation_id'], value=value, idempotency_key='human-edit',
                                     expected_revision=current['revision'])
    runtime.on_generate = edit
    response = api.post(endpoint, json={'idempotency_key': 'old-response', 'expected_revision': row['revision']})
    assert response.status_code == 200, response.get_json()
    turn = response.get_json()['turn']
    assert turn['state'] == 'interrupted'
    assert turn['content']['code'] == 'CONVERSATION_CONTEXT_CHANGED_NO_RESULT_ADOPTED'
    assert 'text' not in turn['content'] and 'owned_provenance' not in turn['content']
    runtime.on_generate = None
    current = api.get(root + '/context').get_json()
    assert current['context']['content']['value'] == value
    resumed = api.post(endpoint, json={'idempotency_key': 'explicit-current-input', 'retry_confirmed': True,
                                      'expected_revision': response.get_json()['revision']})
    assert resumed.status_code == 200 and resumed.get_json()['turn']['state'] == 'completed', resumed.get_json()
    assert next(item for item in api.get(root).get_json()['conversation']['turns']
                if item['turn_id'] == turn['turn_id'])['state'] == 'interrupted'


def test_unbound_model_keeps_user_input_and_honest_unavailable_result(owned_conversation):
    api, app, path, actor, runtime = owned_conversation
    owned_service._SLOTS.clear()
    row = create(api); user = append(api, row, 'Original question kept without inference')
    root = '/v4/ai/conversations/' + row['conversation_id']
    response = api.post(root + '/turns/' + user['turn_id'] + '/respond',
        json={'idempotency_key': 'unavailable', 'expected_revision': row['revision']})
    assert response.status_code == 200, response.get_json()
    turn = response.get_json()['turn']
    assert turn['state'] == 'unavailable' and 'text' not in turn['content']
    assert turn['content']['code'] == 'OWNED_SERVICE_EXECUTOR_NOT_BOUND'
    assert runtime.generated == 0
    reopened = api.get(root).get_json()['conversation']['turns']
    assert reopened[0]['content']['text'] == 'Original question kept without inference'
    assert reopened[-1]['state'] == 'unavailable'


def test_hub_status_reads_actual_shared_binding_and_does_not_confuse_creation_admission(owned_conversation, monkeypatch):
    api, app, path, actor, runtime = owned_conversation
    with app.test_request_context('/', headers={'Host': 'localhost'}, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        observed = service.status()
        assert observed['enabled'] and observed['conversation_available'] and observed['service_available']
        assert observed['domain_id'] == 'shared' and observed['generation_probe_performed'] is False
        assert observed['model_id'] == 'lumenis/owned-base'
        monkeypatch.setattr(service.intelligence, 'owned_inference_status', lambda domain: {
            'available': True, 'service_binding': 'BOUND', 'allowed_operations': ['professional_creation'],
            'source_use_policy_version': 'content-creation-source-use/v1', 'source_use_policy_sha256': 'a' * 64})
        other = service.status()
        assert other['service_available'] and not other['enabled'] and not other['conversation_available']
        assert other['reason'] == 'OWNED_CONVERSATION_POLICY_NOT_ADMITTED'
    assert runtime.generated == 0
