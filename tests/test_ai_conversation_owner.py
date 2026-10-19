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
    assert accounting['history_turns_total'] == 8 and accounting['history_turns_included'] == 6
    assert accounting['history_turns_omitted'] == 2 and accounting['history_characters_omitted'] > 0
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
