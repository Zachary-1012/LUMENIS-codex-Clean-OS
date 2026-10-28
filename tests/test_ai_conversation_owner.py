"""Conversation owner: real scope/SQLite/HTTP; fake responses are explicitly synthetic."""
import json
import sqlite3
import pytest
from tests.test_agent_runtime_http_binding import agent_client, _submit_local
from tests.test_skill_http_durable_identity import skill_client


@pytest.fixture
def conversation_client(agent_client, monkeypatch):
    from lumenis.shared.database import migrations
    from lumenis.system.security import permission
    assert not permission.is_testing_bypass_enabled()
    assert migrations.migrate()
    import app as core
    monkeypatch.setattr(core, 'AUTH_USER', 'synthetic-basic')
    monkeypatch.setattr(core, 'AUTH_PASSWORD', 'synthetic-basic-password')
    monkeypatch.setitem(core.app.config, 'LUMENIS_OPEN_WORKSPACE', True)
    path = agent_client[2]
    with sqlite3.connect(path) as con:
        con.executemany("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'SHARED','conversation',?)", [('read',),('write',)])
    return core.app.test_client(), core.app, path


def create(api, headers=None):
    response = api.post('/v4/ai/conversations', json={'title': 'Local conversation'}, headers=headers)
    assert response.status_code == 200, response.get_json()
    return response.get_json()['conversation']


def append(api, row, text='ordinary user input', key='message-1', headers=None):
    response = api.post('/v4/ai/conversations/' + row['conversation_id'] + '/turns',
        json={'text': text, 'idempotency_key': key, 'expected_revision': row['revision']}, headers=headers)
    assert response.status_code == 200, response.get_json()
    result = response.get_json(); row['revision'] = result['revision']
    return result['turn']


def test_full_app_conversation_storage_identity_pagination_and_restart(conversation_client):
    api, app, path = conversation_client
    row = create(api); root = '/v4/ai/conversations/' + row['conversation_id']
    text = '完整用户内容🙂' * 20000
    first = append(api, row, text=text)
    append(api, row, 'second', 'message-2'); append(api, row, 'third', 'message-3')
    page = api.get(root + '?limit=2').get_json()['conversation']
    assert page['turns'][0]['content']['text'] == text
    assert page['has_more'] and page['next_sequence'] == 2
    assert app.test_client().get(root + '?after_sequence=2').get_json()['conversation']['turns'][0]['content']['text'] == 'third'
    duplicate = api.post(root + '/turns', json={'text':text, 'idempotency_key':'message-1','expected_revision':1})
    assert duplicate.get_json()['idempotent_hit'] is True
    conflict = api.post(root + '/turns', json={'text':'changed','idempotency_key':'message-1','expected_revision':1})
    assert conflict.status_code == 409
    assert api.get(root, headers={'Origin':'https://external.example'}).status_code in (401,403)
    assert api.get(root, headers={'Authorization':'Bearer fixture-session-one'}).status_code in (401,403)
    own = {'Authorization':'Bearer fixture-session-one'}
    account = create(api, own)
    assert api.get('/v4/ai/conversations/' + account['conversation_id']).status_code in (401,403)
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE product_id='SHARED'")
    assert api.get('/v4/ai/conversations/' + account['conversation_id'], headers=own).status_code in (401,403)


def test_conversation_task_refs_require_both_owners_and_never_export_derived_history(conversation_client):
    api, app, path = conversation_client
    row = create(api); root = '/v4/ai/conversations/' + row['conversation_id']
    task_id = _submit_local(api)
    linked = api.post(root + '/tasks', json={'task_id': task_id,'idempotency_key':'task-1','expected_revision':row['revision']})
    assert linked.status_code == 200, linked.get_json()
    row['revision'] = linked.get_json()['revision']
    detail = api.get('/api/ai/tasks/' + task_id).get_json()
    assert detail['conversation_refs'][0]['conversation_id'] == row['conversation_id']
    user = append(api, row, 'Interpret the task')
    response = api.post(root + '/turns/' + user['turn_id'] + '/respond', json={
        'idempotency_key':'reply-1','expected_revision':row['revision']})
    assert response.status_code == 403
    assert response.get_json()['code'] == 'CONVERSATION_HISTORY_TYPED_SOURCE_USE_REQUIRED'
    fake = api.post(root + '/turns', json={'text':'x','idempotency_key':'fake','expected_revision':row['revision'],'origin_kind':'model_output'})
    assert fake.status_code == 400


def test_task_projection_offers_only_current_preparable_shared_visual_without_saving(conversation_client):
    from tests.test_agent_runtime_http_binding import _shared_task
    from lumenis.system.security import permission
    api, app, path = conversation_client
    own = {'Authorization': 'Bearer fixture-session-one'}
    with sqlite3.connect(path) as con:
        con.execute("INSERT OR REPLACE INTO skills_registry(skill_id,name,product,domain,status,version) "
                    "VALUES('shared.social_card','Local original card','SHARED',NULL,'enabled','1.0')")
        con.executemany("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'SHARED',?,?)",
                        [('content','read'), ('reports','read'), ('reports','write')])
    row = create(api, own); root = '/v4/ai/conversations/' + row['conversation_id']
    made = _shared_task(api, headers=own)
    assert made.status_code == 202, made.get_json()
    task_id = made.get_json()['task']['task_id']
    attached = api.post(root + '/tasks', headers=own, json={'task_id': task_id,
        'idempotency_key': 'visual-task-link', 'expected_revision': row['revision']})
    assert attached.status_code == 200, attached.get_json()
    assert 'deliverable' not in attached.get_json()['turn']['content']
    assert api.post('/api/ai/tasks/' + task_id + '/run', headers=own).status_code == 200
    approvals_before = len(permission.get_permission_gate().list_approvals())
    projected = api.get(root, headers=own).get_json()['conversation']['turns'][0]['content']
    assert projected['deliverable'] == {'kind': 'visual', 'step_index': 0}
    prepared = api.post('/api/ai/tasks/' + task_id + '/deliverable', headers=own,
                        json={'mode': 'prepare', 'step_index': 0})
    assert prepared.status_code == 200, prepared.get_json()
    assert prepared.get_json()['state'] == 'READY_TO_SAVE' and prepared.get_json()['saved'] is False
    assert api.post('/api/ai/tasks/' + task_id + '/deliverable',
        headers={'Authorization': 'Bearer fixture-session-two'},
        json={'mode': 'prepare', 'step_index': 0}).status_code in (401, 403)
    assert len(permission.get_permission_gate().list_approvals()) == approvals_before
    with sqlite3.connect(path) as con:
        present = con.execute("SELECT 1 FROM sqlite_master WHERE name='lumenis_shared_artifacts'").fetchone()
        assert not present or con.execute('SELECT COUNT(*) FROM lumenis_shared_artifacts').fetchone()[0] == 0
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='SHARED' AND module='reports' AND action='write'")
    projected = app.test_client().get(root, headers=own).get_json()['conversation']['turns'][0]['content']
    assert projected['status'] == 'succeeded' and 'deliverable' not in projected
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='SHARED' AND module='content'")
    assert app.test_client().get(root, headers=own).get_json()['conversation']['turns'][0]['content'] == {'state': 'source_access_unavailable'}


def test_conversation_response_reservation_context_accounting_and_no_auto_retry(conversation_client, monkeypatch):
    from lumenis.ai_hub import service
    api, app, path = conversation_client
    row = create(api); root = '/v4/ai/conversations/' + row['conversation_id']
    for i in range(8):
        append(api, row, 'long content ' * 100, 'm-' + str(i))
    user = append(api, row, 'current full question', 'current')
    calls = []
    def synthetic(question, history=None, **kwargs):
        calls.append((question, history))
        return {'ok':True,'reply':'Synthetic test response','provider':'synthetic-fixture','model':'not-real'}
    monkeypatch.setattr(service, 'chat', synthetic)
    endpoint = root + '/turns/' + user['turn_id'] + '/respond'
    request = {'idempotency_key':'answer-1','expected_revision':row['revision']}
    replied = api.post(endpoint, json=request)
    assert replied.status_code == 200, replied.get_json()
    result = replied.get_json(); row['revision'] = result['revision']
    accounting = result['turn']['content']['context_accounting']
    assert accounting['history_turns_total'] == 8 and accounting['history_turns_included'] == 8
    assert accounting['history_turns_omitted'] == 0 and accounting['history_characters_omitted'] == 0
    assert accounting['context_policy'] == 'versioned_complete_source_free_context_pack_v1'
    assert accounting['token_budget_verified'] is False
    assert len(calls[0][1]) == 8 and calls[0][1][0]['content'] == 'long content ' * 100
    assert len(calls) == 1 and calls[0][0] == 'current full question'
    assert api.post(endpoint, json=request).get_json()['idempotent_hit'] is True
    assert len(calls) == 1
    assert api.post(endpoint, json={'idempotency_key':'answer-2','expected_revision':row['revision']}).status_code == 400
    def crash(*args, **kwargs):
        calls.append('reserved-before-crash'); raise SystemExit(23)
    monkeypatch.setattr(service, 'chat', crash)
    request2 = {'idempotency_key':'answer-2','expected_revision':row['revision'],'retry_confirmed':True}
    with pytest.raises(SystemExit):
        api.post(endpoint, json=request2)
    replay = app.test_client().post(endpoint, json=request2).get_json()
    assert replay['turn']['state'] == 'reserved' and replay['turn']['recovery'] == 'RESULT_UNKNOWN_NO_AUTOMATIC_RETRY'
    assert len(calls) == 2
    interrupted = api.post(root + '/turns/' + replay['turn']['turn_id'] + '/respond', json={
        'operation':'interrupt','confirmed':True,'expected_revision':replay['revision']})
    assert interrupted.status_code == 200 and interrupted.get_json()['external_call_stopped'] is False


def test_conversation_sensitive_input_and_failed_storage_leave_no_fake_turn(conversation_client):
    api, app, path = conversation_client
    row = create(api); root = '/v4/ai/conversations/' + row['conversation_id']
    rejected = api.post(root + '/turns', json={'text':'api_key=sk-fixturecredentialonly','idempotency_key':'secret','expected_revision':1})
    assert rejected.status_code == 400 and 'sk-' not in rejected.get_data(as_text=True)
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM ai_conversation_turns').fetchone()[0] == 0
        con.execute("CREATE TRIGGER reject_turn BEFORE INSERT ON ai_conversation_turns BEGIN SELECT RAISE(ABORT,'storage fault'); END")
    failed = api.post(root + '/turns', json={'text':'safe','idempotency_key':'safe','expected_revision':1})
    assert failed.status_code == 503
    assert api.get(root).get_json()['conversation']['revision'] == 1


def test_human_context_reopens_corrects_and_invalidates_late_result(conversation_client, monkeypatch):
    from lumenis.ai_hub import conversations, service
    api, app, path = conversation_client
    row = create(api)
    first = append(api, row, 'old budget is 100; original human writing', 'old-input')
    value = {'goal': 'finish original manuscript', 'constraints': ['budget is 80', 'no publication'],
             'draft': 'human draft kept in full', 'decisions': ['reject sending'],
             'excluded_turn_ids': [first['turn_id']]}
    with app.test_request_context('/', headers={'Host': 'localhost'}, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        actor = conversations.current_actor('write')
        saved = conversations.update_context(actor, row['conversation_id'], value=value,
                    idempotency_key='context-one', expected_revision=row['revision'])
        row['revision'] = saved['revision']
        assert conversations.read_context(actor, row['conversation_id'])['context']['content']['value'] == value
        assert conversations.update_context(actor, row['conversation_id'], value=value,
                    idempotency_key='context-one', expected_revision=1)['idempotent_hit']
        with pytest.raises(ValueError, match='EXCLUSION_TURN_REQUIRED'):
            conversations.update_context(actor, row['conversation_id'], value={**value, 'excluded_turn_ids': ['foreign']},
                    idempotency_key='foreign', expected_revision=row['revision'])
    user = append(api, row, 'continue with the current writing', 'continue')
    seen = []
    def synthetic(question, history, **kwargs):
        seen.extend(history)
        # A fresh manual correction during generation must invalidate its late
        # result, and must never overwrite the new human state.
        current = conversations.read_context(actor, row['conversation_id'])
        conversations.update_context(actor, row['conversation_id'], value={**value, 'draft': 'newer human edit'},
            idempotency_key='context-newer', expected_revision=current['revision'])
        return {'ok': True, 'reply': 'obsolete synthetic result', 'provider': 'synthetic-fixture'}
    monkeypatch.setattr(service, 'chat', synthetic)
    response = api.post('/v4/ai/conversations/' + row['conversation_id'] + '/turns/' + user['turn_id'] + '/respond',
        json={'idempotency_key': 'late-response', 'expected_revision': row['revision']})
    assert response.status_code == 200, response.get_json()
    turn = response.get_json()['turn']
    assert turn['state'] == 'interrupted'
    assert turn['content']['code'] == 'CONVERSATION_CONTEXT_CHANGED_NO_RESULT_ADOPTED'
    assert 'text' not in turn['content']
    assert len(seen) == 1 and 'human draft kept in full' in seen[0]['content']
    with app.test_request_context('/', headers={'Host': 'localhost'}, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        assert conversations.read_context(actor, row['conversation_id'])['context']['content']['value']['draft'] == 'newer human edit'
    with sqlite3.connect(path) as con:
        assert json.loads(con.execute('SELECT content_json FROM ai_conversation_turns WHERE turn_id=?',
            (first['turn_id'],)).fetchone()[0])['text'] == 'old budget is 100; original human writing'


def test_human_context_can_forget_completed_assistant_output_and_dependent_replies(tmp_path, monkeypatch):
    from lumenis.ai_hub import conversations, service
    from lumenis.system.ai_gateway import user_api_adapter

    database_path = tmp_path / 'conversation-forget.sqlite3'
    workspace_binding = 'a' * 64

    def connect_isolated():
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        return connection

    monkeypatch.setattr(conversations, '_connect', connect_isolated)
    monkeypatch.setattr(conversations, '_identity',
        lambda actor, action, connection: ('actor:7', workspace_binding))
    monkeypatch.setattr(user_api_adapter, 'is_selected', lambda: False)

    with connect_isolated() as connection:
        connection.execute('BEGIN')
        conversations.ensure_schema(connection)
        connection.commit()

    actor = {'fixture_actor': 7}
    conversation = conversations.create_conversation(actor, title='Forget one answer')
    first_question = conversations.append_user_turn(actor, conversation['conversation_id'],
        text='Question one', idempotency_key='question-one', expected_revision=conversation['revision'])
    revision = first_question['revision']
    generated = []
    answers = {
        'Question one': 'Assistant answer one',
        'Question two': 'Assistant answer two derived from answer one',
        'Question three': 'Assistant answer after forgetting',
        'Question four': 'Assistant answer after a later context revision',
    }

    def synthetic_chat(question, **kwargs):
        generated.append({'question': question, 'history': kwargs['history']})
        return {'ok': True, 'status': 'COMPLETED', 'reply': answers[question],
                'provider': 'isolated-synthetic-test'}

    monkeypatch.setattr(service, 'chat', synthetic_chat)
    first_response = conversations.respond(actor, conversation['conversation_id'],
        first_question['turn']['turn_id'], idempotency_key='response-one', expected_revision=revision)
    assert first_response['turn']['state'] == 'completed'
    revision = first_response['revision']

    second_question = conversations.append_user_turn(actor, conversation['conversation_id'],
        text='Question two', idempotency_key='question-two', expected_revision=revision)
    second_response = conversations.respond(actor, conversation['conversation_id'],
        second_question['turn']['turn_id'], idempotency_key='response-two',
        expected_revision=second_question['revision'])
    assert second_response['turn']['state'] == 'completed'
    first_response_id = first_response['turn']['turn_id']
    assert any(item['turn_id'] == first_response_id and item['included'] is True
               for item in second_response['turn']['content']['context_accounting']['coverage'])

    correction = {'goal': 'Continue from the current human draft', 'constraints': ['do not publish'],
        'draft': 'Human revision retained', 'decisions': ['forget the old assistant answer'],
        'excluded_turn_ids': [first_response_id]}
    saved = conversations.update_context(actor, conversation['conversation_id'], value=correction,
        idempotency_key='forget-answer-one', expected_revision=second_response['revision'])
    reopened = conversations.read_conversation(actor, conversation['conversation_id'], limit=100)
    assert reopened['turns'][-1]['content']['value'] == correction
    assert any(turn['turn_id'] == first_response_id
               and turn['content']['text'] == answers['Question one'] for turn in reopened['turns'])

    third_question = conversations.append_user_turn(actor, conversation['conversation_id'],
        text='Question three', idempotency_key='question-three', expected_revision=saved['revision'])
    third_response = conversations.respond(actor, conversation['conversation_id'],
        third_question['turn']['turn_id'], idempotency_key='response-three',
        expected_revision=third_question['revision'])
    assert third_response['turn']['state'] == 'completed'
    final_history = generated[-1]['history']
    serialized_history = json.dumps(final_history, ensure_ascii=False)
    assert answers['Question one'] not in serialized_history
    assert answers['Question two'] not in serialized_history
    coverage = third_response['turn']['content']['context_accounting']['coverage']
    reasons = {item['turn_id']: item['reason'] for item in coverage}
    assert reasons[first_response_id] == 'explicit_human_correction_or_forget'
    second_response_id = second_response['turn']['turn_id']
    assert reasons[second_response_id] == 'derived_from_excluded_input'

    final_reopen = conversations.read_conversation(actor, conversation['conversation_id'], limit=100)
    assert any(turn['turn_id'] == first_response_id
               and turn['content']['text'] == answers['Question one'] for turn in final_reopen['turns'])
    assert any(turn['turn_id'] == second_response_id
               and turn['content']['text'] == answers['Question two'] for turn in final_reopen['turns'])

    # Editing another part of the context with an empty client exclusion list
    # must not silently bring the previously forgotten answer back into prompts.
    later_context = conversations.update_context(actor, conversation['conversation_id'],
        value={**correction, 'draft': 'A later human revision', 'excluded_turn_ids': []},
        idempotency_key='later-context-edit', expected_revision=third_response['revision'])
    persisted_context = conversations.read_context(actor, conversation['conversation_id'])
    assert persisted_context['context']['content']['value']['draft'] == 'A later human revision'
    assert persisted_context['context']['content']['value']['excluded_turn_ids'] == [first_response_id]
    with connect_isolated() as connection:
        task_context = conversations.task_working_context(connection, conversation['conversation_id'], actor)
    task_prompt = json.dumps(task_context['history'], ensure_ascii=False)
    assert answers['Question one'] not in task_prompt
    assert answers['Question two'] not in task_prompt
    task_coverage = {item['turn_id']: item for item in task_context['context_accounting']['coverage']}
    assert task_coverage[first_response_id]['reason'] == 'explicit_human_correction_or_forget'
    fourth_question = conversations.append_user_turn(actor, conversation['conversation_id'],
        text='Question four', idempotency_key='question-four', expected_revision=later_context['revision'])
    fourth_response = conversations.respond(actor, conversation['conversation_id'],
        fourth_question['turn']['turn_id'], idempotency_key='response-four',
        expected_revision=fourth_question['revision'])
    final_prompt = json.dumps(generated[-1]['history'], ensure_ascii=False)
    assert answers['Question one'] not in final_prompt
    assert answers['Question two'] not in final_prompt
    assert answers['Question three'] in final_prompt

    with connect_isolated() as connection:
        sequence = connection.execute(
            'SELECT COALESCE(MAX(sequence),0)+1 FROM ai_conversation_turns WHERE conversation_id=?',
            (conversation['conversation_id'],),
        ).fetchone()[0]
        now = conversations._now()
        connection.executemany('''INSERT INTO ai_conversation_turns
            (turn_id,conversation_id,idempotency_key,request_sha256,sequence,role,origin_kind,
             content_json,task_id,state,revision,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,1,?,?)''', [
            ('turn_reserved_output', conversation['conversation_id'], 'reserved-output', 'b' * 64,
             sequence, 'assistant', 'model_output', '{"in_reply_to":"none"}', None,
             'reserved', now, now),
            ('turn_task_projection', conversation['conversation_id'], 'task-projection', 'c' * 64,
             sequence + 1, 'assistant', 'task_projection', '{"source_policy":"TASK_OWNER_RECHECK_ON_READ"}',
             'task-fixture', 'recorded', now, now),
        ])

    for key, turn_id in (
        ('forget-reserved-output', 'turn_reserved_output'),
        ('forget-task-projection', 'turn_task_projection'),
    ):
        with pytest.raises(ValueError, match='CONVERSATION_CONTEXT_EXCLUSION_TURN_REQUIRED'):
            conversations.update_context(actor, conversation['conversation_id'],
                value={**correction, 'excluded_turn_ids': [turn_id]},
                idempotency_key=key, expected_revision=fourth_response['revision'])
    with connect_isolated() as connection:
        current_revision = connection.execute(
            'SELECT revision FROM ai_conversations WHERE conversation_id=?',
            (conversation['conversation_id'],),
        ).fetchone()[0]
    assert current_revision == fourth_response['revision']


def test_context_http_owner_permission_reopen_conflict_and_no_inference(conversation_client, monkeypatch):
    from lumenis.ai_hub import service
    api, app, path = conversation_client
    monkeypatch.setattr(service, 'chat', lambda *args, **kwargs: pytest.fail('human context editing invoked a model'))
    own = {'Authorization': 'Bearer fixture-session-one'}
    row = create(api, own)
    first = append(api, row, 'dated budget: 100; old human paragraph', 'original', own)
    url = '/v4/ai/conversations/' + row['conversation_id'] + '/context'
    assert api.get(url, headers=own).get_json()['context'] is None
    value = {'goal': 'complete the existing manuscript', 'constraints': ['budget is 80', 'do not send'],
             'draft': 'complete current human draft', 'decisions': ['review before export'],
             'excluded_turn_ids': [first['turn_id']]}
    body = {'value': value, 'idempotency_key': 'save-context', 'expected_revision': row['revision']}
    saved = api.put(url, json=body, headers=own)
    assert saved.status_code == 200, saved.get_json()
    result = saved.get_json()
    assert api.put(url, json=body, headers=own).get_json()['idempotent_hit']
    reopened = app.test_client().get(url, headers=own).get_json()
    assert reopened['context']['content']['value'] == value and reopened['revision'] == result['revision']
    assert reopened['effect_permission'] == reopened['training_admission'] == 'NOT_GRANTED'
    conflict = api.put(url, json={**body, 'idempotency_key': 'stale'}, headers=own)
    assert conflict.status_code == 409 and conflict.get_json()['code'] == 'CONVERSATION_REVISION_CONFLICT'
    assert api.put(url, json={**body, 'actor_id': 2}, headers=own).status_code == 400
    assert api.get(url, headers={'Authorization': 'Bearer fixture-session-two'}).status_code == 403
    assert api.put(url, json=body, headers={'Authorization': 'Bearer fixture-session-two'}).status_code == 403
    assert api.get(url).status_code == 403
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='SHARED' AND action='write'")
    assert api.get(url, headers=own).status_code == 200
    denied = api.put(url, json={**body, 'expected_revision': result['revision'], 'idempotency_key': 'denied'}, headers=own)
    assert denied.status_code == 403
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM ai_conversation_turns WHERE origin_kind='system_status'").fetchone()[0] == 1
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='SHARED'")
    assert app.test_client().get(url, headers=own).status_code == 403


def test_conversation_concurrent_append_and_workspace_copy_are_isolated(conversation_client, monkeypatch, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from ai_task_engine import reset_task_engine
    api, app, path = conversation_client
    row = create(api); root = '/v4/ai/conversations/' + row['conversation_id']
    body = {'text':'one durable turn','idempotency_key':'same','expected_revision':1}
    def post(data):
        response = app.test_client().post(root + '/turns', json=data)
        return response.status_code, response.get_json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(post, [body, body]))
    assert [status for status, _ in outcomes] == [200,200]
    assert sorted(out['idempotent_hit'] for _,out in outcomes) == [False,True]
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(post, [{**body,'idempotency_key':key,'expected_revision':2} for key in ('a','b')]))
    assert sorted(status for status,_ in outcomes) == [200,409]
    assert len(api.get(root).get_json()['conversation']['turns']) == 2
    copied = tmp_path / 'another-workspace.sqlite'
    with sqlite3.connect(path) as source, sqlite3.connect(copied) as target:
        source.backup(target)
    with monkeypatch.context() as patch:
        patch.setenv('ZBC_DB_PATH', str(copied)); reset_task_engine()
        assert app.test_client().get(root).status_code in (401,403)
        assert app.test_client().get('/v4/ai/conversations').get_json()['conversations'] == []
    reset_task_engine()
    assert app.test_client().get(root).status_code == 200
    monkeypatch.setitem(app.config, 'LUMENIS_OPEN_WORKSPACE', False)
    assert app.test_client().get(root).status_code in (401,403)


def test_real_tcp_full_app_no_model_conversation_persists_unavailable(conversation_client, monkeypatch):
    import urllib.request
    from threading import Thread
    from werkzeug.serving import make_server
    from lumenis.system.security import permission
    api, app, path = conversation_client
    assert not permission.is_testing_bypass_enabled()
    monkeypatch.setenv('AI_PROVIDER', 'owned')
    server = make_server('127.0.0.1', 0, app)
    thread = Thread(target=server.serve_forever); thread.start()
    def call(path, body=None):
        request = urllib.request.Request(f'http://127.0.0.1:{server.server_port}' + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request, timeout=10) as response:
            assert response.status == 200
            return json.load(response)
    try:
        row = call('/v4/ai/conversations', {'title':'No model needed for storage'})['conversation']
        root = '/v4/ai/conversations/' + row['conversation_id']
        user = call(root + '/turns', {'text':'Keep my user-authored conversation', 'idempotency_key':'one','expected_revision':1})
        url = root + '/turns/' + user['turn']['turn_id'] + '/respond'
        replied = call(url, {'idempotency_key':'reply','expected_revision':user['revision']})
        assert replied['turn']['state'] == 'unavailable', replied
        assert 'text' not in replied['turn']['content']
        fresh = call(root)['conversation']
        assert fresh['turns'][0]['content']['text'] == 'Keep my user-authored conversation'
        assert fresh['turns'][1]['state'] == 'unavailable'
        screen = call('/api/experience/screen/AI-03')
        assert any(item['conversation_id'] == row['conversation_id'] for item in screen['data']['conversations'])
        selected = call('/api/experience/screen/AI-03?conversation_id=' + row['conversation_id'])
        assert selected['data']['selected_conversation']['turns'][0]['content']['text'] == 'Keep my user-authored conversation'
    finally:
        server.shutdown(); thread.join(5); server.server_close()
        assert not thread.is_alive()


def test_new_process_reads_same_workspace_and_interruption_rejects_late_response(conversation_client, monkeypatch):
    import os
    import subprocess
    import sys
    from threading import Event, Thread
    from lumenis.ai_hub import service
    api, app, path = conversation_client
    row = create(api); root = '/v4/ai/conversations/' + row['conversation_id']
    user = append(api, row, 'Survive process restart')
    code = '''import json,sys
from flask import Flask
from lumenis.ai_hub.conversations import current_actor,read_conversation
app=Flask(__name__);app.config['LUMENIS_OPEN_WORKSPACE']=True
with app.test_request_context('/',environ_base={'REMOTE_ADDR':'127.0.0.1'}):
 print(json.dumps(read_conversation(current_actor(),sys.argv[1]),ensure_ascii=False))
'''
    environment = dict(os.environ); environment.pop('PERMISSION_GATE_TESTING',None)
    reopened = subprocess.run([sys.executable,'-c',code,row['conversation_id']], env=environment,
        text=True,capture_output=True,timeout=20)
    assert reopened.returncode == 0, reopened.stderr
    assert json.loads(reopened.stdout.strip().splitlines()[-1])['turns'][0]['content']['text'] == 'Survive process restart'
    entered, release = Event(), Event()
    def slow_response(*args, **kwargs):
        entered.set(); assert release.wait(5)
        return {'ok':True,'reply':'late synthetic output','provider':'synthetic'}
    monkeypatch.setattr(service,'chat',slow_response)
    responses = []
    endpoint = root + '/turns/' + user['turn_id'] + '/respond'
    worker = Thread(target=lambda: responses.append(app.test_client().post(endpoint,json={
        'idempotency_key':'reserved','expected_revision':row['revision']})))
    worker.start(); assert entered.wait(5)
    snapshot = api.get(root).get_json()['conversation']
    pending = snapshot['turns'][-1]
    interrupted = api.post(root + '/turns/' + pending['turn_id'] + '/respond',json={
        'operation':'interrupt','confirmed':True,'expected_revision':snapshot['revision']})
    assert interrupted.status_code == 200, interrupted.get_json()
    release.set(); worker.join(5)
    assert not worker.is_alive() and responses[0].status_code == 409
    final = api.get(root).get_json()['conversation']['turns'][-1]
    assert final['state'] == 'interrupted' and 'text' not in final['content']


def test_schema_rejects_complete_columns_without_owner_constraints(tmp_path):
    from lumenis.ai_hub.conversations import SCHEMA, ensure_schema
    import re
    for missing in ('unique','foreign_key','primary_key'):
        path = tmp_path / (missing + '.sqlite')
        con = sqlite3.connect(path)
        con.execute('BEGIN IMMEDIATE')
        statements = list(SCHEMA)
        if missing == 'unique':
            statements[1] = statements[1].replace('UNIQUE(conversation_id,idempotency_key),','')
        elif missing == 'foreign_key':
            statements[1] = statements[1].replace(' REFERENCES ai_conversations(conversation_id)','')
        else:
            statements[0] = statements[0].replace('conversation_id TEXT PRIMARY KEY','conversation_id TEXT')
        for statement in statements:
            con.execute(statement)
        with pytest.raises(RuntimeError, match='INCOMPATIBLE'):
            ensure_schema(con)
        con.rollback(); con.close()


def test_conversation_archive_write_revoke_and_explicit_size_limits(conversation_client, monkeypatch):
    from lumenis.ai_hub import conversations as owner
    api, app, path = conversation_client
    own = {'Authorization':'Bearer fixture-session-one'}
    row = create(api, own); root = '/v4/ai/conversations/' + row['conversation_id']
    append(api, row, headers=own)
    archived = api.patch(root, json={'state':'archived','expected_revision':row['revision']}, headers=own)
    assert archived.status_code == 200, archived.get_json()
    archived_revision = archived.get_json()['conversation']['revision']
    denied = api.post(root + '/turns', json={'text':'blocked','idempotency_key':'archived','expected_revision':archived_revision}, headers=own)
    assert denied.status_code == 409
    reopened = api.patch(root, json={'state':'active','expected_revision':archived_revision}, headers=own)
    assert reopened.status_code == 200
    row['revision'] = reopened.get_json()['conversation']['revision']
    append(api, row, 'after reopen', 'reopen', own)
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='SHARED' AND module='conversation' AND action='write'")
    assert api.get(root, headers=own).status_code == 200
    assert api.post(root + '/turns', json={'text':'withdrawn','idempotency_key':'withdrawn','expected_revision':row['revision']}, headers=own).status_code == 403
    # Small synthetic caps exercise explicit failure and rollback, not production capacities.
    local = create(api); local_root = '/v4/ai/conversations/' + local['conversation_id']
    monkeypatch.setattr(owner, 'TURN_MAX_BYTES', 512)
    oversized = api.post(local_root + '/turns', json={'text':'x'*600,'idempotency_key':'large','expected_revision':1})
    assert oversized.status_code == 400 and oversized.get_json()['code'] == 'CONVERSATION_TURN_TOO_LARGE'
    monkeypatch.setattr(owner, 'CONVERSATION_MAX_BYTES', 20)
    aggregate = api.post(local_root + '/turns', json={'text':'x'*100,'idempotency_key':'aggregate','expected_revision':1})
    assert aggregate.status_code == 400, aggregate.get_json()
    saved = api.get(local_root).get_json()['conversation']
    assert saved['revision'] == 1 and saved['turns'] == []


def test_scoped_skill_conversation_link_rechecks_original_scope(conversation_client, skill_client, monkeypatch):
    from types import SimpleNamespace
    import lumenis_skill_adapter
    api, app, path = conversation_client
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_KEY_RING', json.dumps({'scope-test':'public-local-fixture-key'}))
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID', 'scope-test')
    monkeypatch.setattr(lumenis_skill_adapter, 'get_skill_adapter', lambda: SimpleNamespace(available=False))
    with sqlite3.connect(path) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1 AND product_id='CTH'", (json.dumps({'global':True}),))
    own = {'Authorization':'Bearer fixture-session-one'}
    executed = skill_client[0].post('/api/ai/tasks', headers=own, json={
        'skill_id':'zbc.skill_registry_snapshot','task':'Read local capabilities',
        'product':'CTH','action_type':'READ','scope':{'global_scope':True}})
    assert executed.status_code == 200, executed.get_json()
    identifier = executed.get_json()['execution_id']
    row = create(api, own); root = '/v4/ai/conversations/' + row['conversation_id']
    linked = api.post(root + '/tasks', headers=own, json={
        'task_id':identifier,'idempotency_key':'skill-link','expected_revision':1})
    assert linked.status_code == 200, linked.get_json()
    detail = api.get(root, headers=own).get_json()['conversation']
    assert detail['turns'][0]['content']['task_kind'] == 'SKILL_EXECUTION'
    with sqlite3.connect(path) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1 AND product_id='CTH'", (json.dumps({'subject_ids':['different']}),))
    hidden = api.get(root, headers=own).get_json()['conversation']['turns'][0]
    assert hidden['content'].get('task_id') is None
    assert 'source_access_unavailable' in json.dumps(hidden)


def test_workspace_draft_restart_scope_conflict_and_account_isolation(conversation_client):
    api, app, path = conversation_client
    route = '/v4/ai/workspace-draft'
    own = {'Authorization': 'Bearer fixture-session-one'}
    scope = {'scope_key': 'GLOBAL_ALL::'}
    def read(headers=own, key='GLOBAL_ALL::'):
        return api.get(route, headers=headers, query_string={'scope_key': key})
    assert read().get_json()['draft']['revision'] == 0
    body = {**scope, 'text': 'Draft to resume after closing the window.', 'expected_revision': 0}
    saved = api.put(route, headers=own, json=body)
    assert saved.status_code == 200, saved.get_json()
    assert saved.get_json()['draft']['revision'] == 1
    assert api.put(route, headers=own, json=body).get_json()['draft']['revision'] == 1
    assert app.test_client().get(route, headers=own, query_string=scope).get_json()['draft']['text'] == body['text']
    changed = {**body, 'text': 'Revised draft', 'expected_revision': 1}
    assert api.put(route, headers=own, json=changed).get_json()['draft']['revision'] == 2
    assert api.put(route, headers=own, json={**body, 'text': 'Stale overwrite'}).status_code == 409
    assert read().get_json()['draft']['text'] == 'Revised draft'
    assert read(key='FOCUS:CTH:isolated-subject').get_json()['draft']['text'] == ''
    with sqlite3.connect(path) as con:
        con.executemany("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(2,'SHARED','conversation',?)", [('read',),('write',)])
    other = {'Authorization': 'Bearer fixture-session-two'}
    assert read(other).get_json()['draft']['revision'] == 0
    assert api.put(route, headers=own, json={**changed, 'actor_ref': 'actor:2'}).status_code == 400
    assert api.put(route, headers=own, json={**changed, 'text': None}).status_code == 400
    assert api.put(route, headers=own, json={**changed, 'expected_revision': True}).status_code == 400
    assert read(key='../another').status_code == 400
    assert api.put(route, headers=own, json={**changed, 'text': '', 'expected_revision': 2}).get_json()['draft']['revision'] == 3
    assert read().get_json()['draft']['text'] == ''
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE module='conversation' AND user_id=1")
    assert read().status_code == 403


@pytest.fixture
def conversation_sources(conversation_client, monkeypatch, tmp_path):
    import socket

    import shared_artifacts
    from lumenis.ai_hub import conversations
    from lumenis.importer import documents
    from lumenis.shared.evidence import store
    from lumenis.shared.reporting import saved_work
    from lumenis.system.security import permission

    api, app, path = conversation_client
    monkeypatch.setenv('ZBC_ARTIFACT_DIR', str(tmp_path / 'source-artifacts'))
    def denied(*args, **kwargs):
        raise AssertionError('CONVERSATION_SOURCE_NETWORK_FORBIDDEN')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket.socket, 'connect_ex', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    shared_artifacts.ensure_artifact_table()
    store.init_evidence_store(str(path))
    with sqlite3.connect(path) as con:
        con.executemany("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'SHARED','reports',?)",
                        [('read',), ('write',)])
    permission.get_permission_gate().grant_permission(permission.PermissionLevel.COMMIT)
    own = {'Authorization': 'Bearer fixture-session-one'}
    scope = {'scope_kind': 'shared_workspace', 'version': 1}
    with app.test_request_context('/', headers=own):
        actor = conversations.current_actor('write')
    def save(text, title='Original orchard material', filename='source.txt'):
        source = tmp_path / filename
        source.write_text(text, encoding='utf-8')
        return documents.save_private_document(source, actor=actor, scope=scope,
            request_id='source-' + filename.replace('.', '-'), title=title)
    row = create(api, own)
    yield {'api': api, 'app': app, 'db': path, 'actor': actor, 'scope': scope,
           'headers': own, 'save': save, 'root': '/v4/ai/conversations/' + row['conversation_id'],
           'row': row, 'work': saved_work}


def _search_sources(ws, query='orchard', **options):
    response = ws['api'].get(ws['root'] + '/context', headers=ws['headers'],
                            query_string={'query': query, **options})
    assert response.status_code == 200, response.get_json()
    return response.get_json()['search']


def _source_context_body(revision, references, key='adopt-original'):
    return {'value': {'goal': 'finish writing', 'constraints': ['do not publish'],
                     'draft': 'manual writing survives source withdrawal', 'decisions': ['review first'],
                     'excluded_turn_ids': []}, 'source_references': references,
            'idempotency_key': key, 'expected_revision': revision}


def test_conversation_source_search_preview_adopt_reopen_and_source_free_model_boundary(conversation_sources, monkeypatch):
    from lumenis.ai_hub import service
    ws = conversation_sources
    text = 'orchard original evidence statement 🙂 ' * 100
    made = ws['save'](text)
    result = _search_sources(ws)
    assert result['verification_complete'] is True
    assert result['retrieval']['mode'] == 'BM25_ONLY'
    assert result['retrieval']['neural_retrieval_performed'] is False
    source = result['records'][0]
    assert source['character_count'] == len(text) and len(source['text']) == 1200
    assert source['text_basis'] == 'retained_original_parsed_text'
    reference = {**source['reference'], 'start': 0, 'end': len(text)}
    assert reference['type'] == 'private_document'
    assert reference['artifact_id'] == made['artifact']['artifact_id']
    preview = ws['api'].get(ws['root'] + '/context', headers=ws['headers'],
                           query_string={'source_reference': json.dumps(reference)}).get_json()['source_preview']
    assert preview['text'] == text and preview['model_source_use'] == 'NOT_GRANTED'
    body = _source_context_body(ws['row']['revision'], [reference])
    saved = ws['api'].put(ws['root'] + '/context', headers=ws['headers'], json=body)
    assert saved.status_code == 200, saved.get_json()
    assert ws['api'].put(ws['root'] + '/context', headers=ws['headers'], json=body).get_json()['idempotent_hit']
    reopened = ws['app'].test_client().get(ws['root'] + '/context', headers=ws['headers']).get_json()
    assert reopened['source_references'][0]['text'] == text
    assert reopened['context']['content']['value'] == body['value']
    assert reopened['context']['content']['source_references'] == [reference]
    with sqlite3.connect(ws['db']) as con:
        assert con.execute('SELECT COUNT(*) FROM ai_task').fetchone()[0] == 0
        stored = con.execute("SELECT content_json FROM ai_conversation_turns WHERE origin_kind='system_status'").fetchone()[0]
        assert text not in stored and 'orchard original evidence statement' not in stored
    ws['row']['revision'] = saved.get_json()['revision']
    user = append(ws['api'], ws['row'], 'continue manual writing', headers=ws['headers'])
    captured = []
    def synthetic(question, history, **kwargs):
        captured.extend(history)
        return {'ok': True, 'reply': 'synthetic boundary response', 'provider': 'synthetic-fixture'}
    monkeypatch.setattr(service, 'chat', synthetic)
    replied = ws['api'].post(ws['root'] + '/turns/' + user['turn_id'] + '/respond', headers=ws['headers'],
        json={'expected_revision': ws['row']['revision'], 'idempotency_key': 'manual-source-free'})
    assert replied.status_code == 200, replied.get_json()
    assert 'manual writing survives source withdrawal' in json.dumps(captured)
    assert 'orchard original evidence statement' not in json.dumps(captured)
    assert reference['artifact_id'] not in json.dumps(captured)


def test_conversation_source_reference_withdrawal_preserves_manual_context_and_explicit_removal(conversation_sources):
    ws = conversation_sources
    ws['save']('orchard original source available for an explicit human selection')
    reference = _search_sources(ws)['records'][0]['reference']
    body = _source_context_body(1, [reference])
    saved = ws['api'].put(ws['root'] + '/context', headers=ws['headers'], json=body)
    assert saved.status_code == 200, saved.get_json()
    revision = saved.get_json()['revision']
    with sqlite3.connect(ws['db']) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND module='reports'")
    reopened = ws['api'].get(ws['root'] + '/context', headers=ws['headers'])
    assert reopened.status_code == 200, reopened.get_json()
    projection = reopened.get_json()
    assert projection['context']['content']['value'] == body['value']
    assert projection['source_references'] == [{'reference': reference, 'state': 'source_access_unavailable',
        'model_source_use': 'NOT_GRANTED', 'training_admission': 'NOT_GRANTED'}]
    assert ws['api'].get(ws['root'] + '/context', headers=ws['headers'], query_string={'query': 'orchard'}).status_code == 403
    # A manual-only edit neither adopts the source again nor needs source access.
    manual = {**body, 'expected_revision': revision, 'idempotency_key': 'manual-withdrawn'}
    manual.pop('source_references')
    kept = ws['api'].put(ws['root'] + '/context', headers=ws['headers'], json=manual)
    assert kept.status_code == 200, kept.get_json()
    assert kept.get_json()['turn']['content']['source_references'] == [reference]
    removed = ws['api'].put(ws['root'] + '/context', headers=ws['headers'],
        json=_source_context_body(kept.get_json()['revision'], [], 'remove-withdrawn'))
    assert removed.status_code == 200, removed.get_json()
    assert ws['api'].get(ws['root'] + '/context', headers=ws['headers']).get_json()['source_references'] == []


@pytest.mark.parametrize('mutation', ['delete', 'replace'])
def test_conversation_source_post_rank_original_file_change_is_rejected(conversation_sources, monkeypatch, mutation):
    import shared_artifacts
    from agent_memory import retrieval

    ws = conversation_sources
    made = ws['save']('orchard original same-size source before ranking')
    binding = made['document']['attachments'][0]
    source = shared_artifacts.artifact_file_path(binding['artifact_id'])
    assert source is not None
    original = retrieval.lexical_search
    def ranked(*args, **kwargs):
        result = original(*args, **kwargs)
        if mutation == 'delete':
            source.unlink()
        else:
            source.write_bytes(b'X' * source.stat().st_size)
        return result
    monkeypatch.setattr(retrieval, 'lexical_search', ranked)
    response = ws['api'].get(ws['root'] + '/context', headers=ws['headers'], query_string={'query': 'orchard'})
    assert response.status_code == 409, response.get_json()
    assert response.get_json()['code'] == 'MEMORY_REFERENCE_CHANGED'
    assert 'records' not in response.get_json()


def test_conversation_source_pagination_scope_cas_and_reference_validation(conversation_sources):
    ws = conversation_sources
    ws['save']('orchard one', filename='one.txt')
    ws['save']('orchard two', filename='two.txt')
    result = _search_sources(ws, limit=1)
    assert result['has_more'] and result['next_offset'] == 1
    second = _search_sources(ws, limit=1, offset=1, snapshot=result['retrieval']['source_snapshot_sha256'])
    assert second['records'][0]['reference'] != result['records'][0]['reference']
    reference = result['records'][0]['reference']
    url = ws['root'] + '/context'
    for query in ({'query': 'orchard', 'offset': 1}, {'query': 'orchard', 'snapshot': '0' * 64}):
        assert ws['api'].get(url, headers=ws['headers'], query_string=query).status_code == 409
    for query in ({'query': 'orchard', 'actor_id': '2'}, {'limit': 1}, {'source_reference': 'null'},
                  {'source_reference': json.dumps({**reference, 'end': 64001})}):
        assert ws['api'].get(url, headers=ws['headers'], query_string=query).status_code == 400
    for refs in (None, [reference, reference], [{**reference, 'type': []}]):
        response = ws['api'].put(url, headers=ws['headers'], json=_source_context_body(1, refs))
        assert response.status_code == 400, response.get_json()
    altered = {**reference, 'sha256': '0' * 64}
    assert ws['api'].put(url, headers=ws['headers'], json=_source_context_body(1, [altered])).status_code == 409
    saved = ws['api'].put(url, headers=ws['headers'], json=_source_context_body(1, [reference]))
    assert saved.status_code == 200, saved.get_json()
    assert ws['api'].put(url, headers=ws['headers'], json=_source_context_body(1, [], 'stale-remove')).status_code == 409
    assert ws['api'].get(url, headers={'Authorization': 'Bearer fixture-session-two'},
        query_string={'query': 'orchard'}).status_code == 403
    ws['save']('orchard third', filename='three.txt')
    stale = ws['api'].get(url, headers=ws['headers'], query_string={'query': 'orchard', 'offset': 1,
        'snapshot': result['retrieval']['source_snapshot_sha256']})
    assert stale.status_code == 409 and stale.get_json()['code'] == 'MEMORY_SEARCH_SNAPSHOT_CHANGED'


def test_conversation_source_signed_original_scope_and_source_use_rechecked(conversation_sources, tmp_path, monkeypatch):
    import intelligence_library_api
    from lumenis.importer import documents
    from lumenis.system.security import permission
    ws = conversation_sources
    with sqlite3.connect(ws['db']) as con:
        con.executemany("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) "
                        "VALUES(1,'CTH','reports',?,?)", [('read', '{"global":true}'), ('write', '{"global":true}')])
    source = tmp_path / 'signed-orchard.txt'
    text = 'orchard signed source retained with its actual rights and domain.'
    source.write_text(text, encoding='utf-8')
    arguments = {'actor': ws['actor'],
        'scope': {'domain_id': 'cth', 'subject_id': None, 'brand_focus_id': None, 'global_scope': True},
        'provenance': {'title': 'Signed orchard material', 'source_url': 'https://example.org/isolated-orchard',
                       'rights': 'public-reference-only', 'captured_at': '2026-10-25T00:00:00Z', 'published_at': None}}
    resource = documents.document_import_resource(str(source), **arguments)
    permission.get_permission_gate().grant_approval('data_import', resource=resource, granted_by='isolated-test')
    documents.import_document(str(source), **arguments)
    result = _search_sources(ws)
    reference = result['records'][0]['reference']
    assert reference['type'] == 'evidence' and result['records'][0]['text'] == text
    body = _source_context_body(1, [reference])
    saved = ws['api'].put(ws['root'] + '/context', headers=ws['headers'], json=body)
    assert saved.status_code == 200, saved.get_json()
    reader = intelligence_library_api.verified_research_source
    def read_then_revoke(connection, *args, **kwargs):
        result = reader(connection, *args, **kwargs)
        # A source's domain permission may change independently of the still
        # readable Shared conversation. Never send the already-read body.
        connection.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='CTH'")
        return result
    with monkeypatch.context() as patch:
        patch.setattr(intelligence_library_api, 'verified_research_source', read_then_revoke)
        unselected = create(ws['api'], ws['headers'])
        response = ws['api'].get('/v4/ai/conversations/' + unselected['conversation_id'] + '/context', headers=ws['headers'],
                                query_string={'source_reference': json.dumps(reference)})
        assert response.status_code == 409 and 'source_preview' not in response.get_json()
    with sqlite3.connect(ws['db']) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1 AND product_id='CTH'",
                    ('{"subject_ids":["other-subject"]}',))
    reopened = ws['api'].get(ws['root'] + '/context', headers=ws['headers']).get_json()
    assert reopened['source_references'][0]['state'] == 'source_access_unavailable'
    assert 'text' not in reopened['source_references'][0]
    assert _search_sources(ws)['records'] == []


def test_conversation_saved_work_reference_version_correction_requires_explicit_new_adoption(conversation_sources):
    ws = conversation_sources
    made = ws['work'].save_work(title='Orchard current document', markdown='orchard first full manuscript',
        kind='report', payload={}, citations=[], request_id='saved-original', actor=ws['actor'], scope=ws['scope'])
    reference = _search_sources(ws)['records'][0]['reference']
    assert reference['type'] == 'saved_work'
    saved = ws['api'].put(ws['root'] + '/context', headers=ws['headers'], json=_source_context_body(1, [reference]))
    assert saved.status_code == 200, saved.get_json()
    revised = ws['work'].save_work(title='Orchard revised document', markdown='orchard corrected full manuscript',
        kind='report', payload={}, citations=[], request_id='saved-revision', actor=ws['actor'], scope=ws['scope'],
        work_id=made['document']['work_id'], previous_artifact_id=made['artifact']['artifact_id'],
        expected_draft_digest=made['document']['draft_digest'])
    reopened = ws['api'].get(ws['root'] + '/context', headers=ws['headers']).get_json()
    assert reopened['source_references'][0]['state'] == 'source_access_unavailable'
    result = _search_sources(ws)
    assert len(result['records']) == 1
    new = result['records'][0]['reference']
    assert new['version'] == 2 and new['artifact_id'] == revised['artifact']['artifact_id']
    adopted = ws['api'].put(ws['root'] + '/context', headers=ws['headers'],
        json=_source_context_body(saved.get_json()['revision'], [new], 'adopt-correction'))
    assert adopted.status_code == 200, adopted.get_json()
    assert ws['api'].get(ws['root'] + '/context', headers=ws['headers']).get_json()['source_references'][0]['text'] == 'orchard corrected full manuscript'


def test_conversation_source_late_withdrawal_rolls_back_adoption(conversation_sources, monkeypatch):
    import shared_artifacts
    from lumenis.ai_hub import conversations
    ws = conversation_sources
    made = ws['save']('orchard material withdrawn during context commit')
    reference = _search_sources(ws)['records'][0]['reference']
    source = shared_artifacts.artifact_file_path(made['document']['attachments'][0]['artifact_id'])
    insert = conversations._insert_turn
    def insert_then_withdraw(*args, **kwargs):
        result = insert(*args, **kwargs)
        source.unlink()
        return result
    monkeypatch.setattr(conversations, '_insert_turn', insert_then_withdraw)
    response = ws['api'].put(ws['root'] + '/context', headers=ws['headers'], json=_source_context_body(1, [reference]))
    assert response.status_code == 409 and response.get_json()['code'] == 'MEMORY_REFERENCE_CHANGED'
    reopened = ws['api'].get(ws['root'] + '/context', headers=ws['headers']).get_json()
    assert reopened['revision'] == 1 and reopened['context'] is None and reopened['source_references'] == []
