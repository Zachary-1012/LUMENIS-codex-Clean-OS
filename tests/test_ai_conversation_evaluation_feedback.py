"""Conversation-to-Evaluation feedback binding on one isolated SQLite owner."""
import json

import pytest

import ai_call_logger as acl
from lumenis.ai_hub import conversations
from lumenis.shared.database.repository import DatabaseRepository
from lumenis.shared.evaluation import ai as evaluation
from lumenis.system.ai_gateway.owned_service import owned_service_request_digest


@pytest.fixture
def conversation_store(tmp_path, monkeypatch):
    repository = DatabaseRepository(str(tmp_path / 'conversation-evaluation.db'))
    actor_ref = 'actor:synthetic-conversation-owner'
    workspace = 'a' * 64
    monkeypatch.setattr(conversations, '_connect', lambda: repository.connect())
    monkeypatch.setattr(conversations, '_identity',
        lambda actor, action, connection: (actor_ref, workspace))
    monkeypatch.setattr(evaluation, 'get_repository', lambda: repository)
    monkeypatch.setattr(acl, 'get_repository', lambda: repository)
    connection = repository.connect()
    try:
        connection.execute('BEGIN IMMEDIATE')
        conversations.ensure_schema(connection)
        connection.commit()
    finally:
        connection.close()
    assert acl.init_db()
    return repository, actor_ref, workspace


def _request(conversation_id, response_turn_id, user_turn_id, actor_ref, workspace):
    material = {
        'conversation_id': conversation_id,
        'response_turn_id': response_turn_id,
        'user_turn_id': user_turn_id,
        'actor_ref': actor_ref,
        'workspace_binding': workspace,
        'scope': dict(conversations._SCOPE),
        'question': 'Private synthetic question not retained in Evaluation',
        'history': [],
        'context_accounting': {'context_pack_sha256': 'b' * 64},
        'source_use_mode': 'source_free',
    }
    return conversations._conversation_request(material)


def test_excluded_completed_turn_records_private_safe_feedback_and_reopens(
        conversation_store):
    repository, actor_ref, workspace = conversation_store
    actor = {'synthetic': True}
    conversation = conversations.create_conversation(actor, title='Evaluation link test')
    user = conversations.append_user_turn(actor, conversation['conversation_id'],
        text='A synthetic question', idempotency_key='user-1', expected_revision=1)

    with conversations._write(conversation['conversation_id'], actor) as (connection, row):
        conversations._advance(connection, row, 2)
        model_turn = conversations._insert_turn(connection, row,
            key='synthetic-model-output', digest='c' * 64, role='assistant',
            origin='model_output', content={
                'text': 'Private synthetic model answer', 'in_reply_to': user['turn']['turn_id'],
                'source_policy': 'source_free_conversation',
                'owned_provenance': {'model_revision': 'synthetic-rev-1'},
            }, state='completed')

    request = _request(conversation['conversation_id'], model_turn['turn_id'],
                       user['turn']['turn_id'], actor_ref, workspace)
    result = {
        'ok': True, 'status': 'COMPLETED', 'code': 'OWNED_INFERENCE_COMPLETED',
        'attempt_id': 'attempt_' + '1' * 32, 'run_id': 'synthetic-run-1',
        'request_digest': owned_service_request_digest(request),
        'operation': request.operation, 'domain_id': request.domain_id,
        'scope': request.scope, 'input_revision_sha256': request.input_revision_sha256,
        'source_binding_sha256': request.source_binding_sha256,
        'real_input_bound': True, 'model_id': 'synthetic-owned-cpu',
        'model_revision': 'synthetic-rev-1', 'runtime_sha256': 'd' * 64,
        'executor_sha256': 'e' * 64, 'text': 'Private synthetic model answer',
        'prompt_tokens': 3, 'completion_tokens': 4, 'total_tokens': 7,
    }
    evaluation_ref = evaluation.record_owned_gateway_execution(request, result, latency_ms=12)
    assert evaluation_ref
    with conversations._write(conversation['conversation_id'], actor) as (connection, _):
        raw = connection.execute('SELECT content_json FROM ai_conversation_turns WHERE turn_id=?',
                                 (model_turn['turn_id'],)).fetchone()[0]
        content = json.loads(raw)
        content['_evaluation_call_ref'] = evaluation_ref
        connection.execute('UPDATE ai_conversation_turns SET content_json=? WHERE turn_id=?',
                           (json.dumps(content, ensure_ascii=False), model_turn['turn_id']))

    reopened = conversations.read_conversation(actor, conversation['conversation_id'])
    public_output = next(turn for turn in reopened['turns'] if turn['turn_id'] == model_turn['turn_id'])
    assert '_evaluation_call_ref' not in public_output['content']

    state = {'goal': 'continue', 'constraints': [], 'draft': '', 'decisions': [],
             'excluded_turn_ids': [model_turn['turn_id']]}
    saved = conversations.update_context(actor, conversation['conversation_id'], value=state,
        idempotency_key='forget-model-output', expected_revision=3)
    assert saved['evaluation_feedback']['state'] == 'RECORDED'
    assert saved['evaluation_feedback']['recorded'] == 1

    reopened_context = conversations.read_context(actor, conversation['conversation_id'])
    assert reopened_context['context']['content']['value']['excluded_turn_ids'] == [model_turn['turn_id']]
    assert reopened_context['evaluation_feedback']['state'] == 'RECORDED'
    assert reopened_context['evaluation_feedback']['items'] == [
        {'turn_id': model_turn['turn_id'], 'state': 'RECORDED'}]
    assert '_evaluation_call_ref' not in reopened_context['context']['content']

    replay = conversations.update_context(actor, conversation['conversation_id'], value=state,
        idempotency_key='forget-model-output', expected_revision=3)
    assert replay['idempotent_hit'] is True
    assert replay['evaluation_feedback']['state'] == 'ALREADY_RECORDED'

    connection = repository.connect()
    try:
        call = connection.execute('SELECT final_decision,input_text,output,system_result FROM ai_call_logs').fetchone()
        assert call['final_decision'] == 'USER_EXCLUDED_FROM_FUTURE_CONTEXT'
        assert call['input_text'] == '' and call['output'] == ''
        assert 'Private synthetic question not retained in Evaluation' not in call['system_result']
        assert 'Private synthetic model answer' not in call['system_result']
    finally:
        connection.close()
