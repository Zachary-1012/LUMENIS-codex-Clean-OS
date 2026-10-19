"""Real isolated session/SQLite/Permission roundtrips; no model or network calls."""
import json
import sqlite3

import pytest
from tests.test_skill_http_durable_identity import skill_client
from tests.test_skill_scope_receipts import scoped_skill
from tests.test_agent_runtime_http_binding import agent_client

OWN = {'Authorization': 'Bearer fixture-session-one'}
OTHER = {'Authorization': 'Bearer fixture-session-two'}
SKILL = 'zbc.skill_registry_snapshot'
BASE = '/lumenis/api/'
SCOPE = {'subject_id': 'SCOPE-A', 'global_scope': False}

@pytest.fixture
def legacy(scoped_skill, monkeypatch, tmp_path):
    api, app, path = scoped_skill
    from lumenis_app_api import lumenis_bp
    app.register_blueprint(lumenis_bp)
    import lumenis_skill_adapter
    monkeypatch.setattr(lumenis_skill_adapter.CrossCoreSkillAdapter, '_run_osai',
                        lambda *a, **k: pytest.fail('external invocation forbidden'))
    monkeypatch.setenv('LUMENIS_RUNTIME_DIR', str(tmp_path / 'runtime'))
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','evidence','read',?)", (json.dumps({'global': True}),))
    return api, app, path


def invoke(api, headers=OWN, **extra):
    return api.post(BASE+'skills/invoke', headers=headers, json={
        'skill_id': SKILL, 'task': 'Read local registered capabilities', 'product': 'CTH',
        'scope': SCOPE, 'action_type': 'READ', **extra})


def evidence_headers(auth=OWN):
    return {**auth, 'X-Lumenis-Context-Mode': 'FOCUS', 'X-Domain-Id': 'CTH', 'X-Subject-ID': 'SCOPE-A'}


def test_authorized_execution_history_and_evidence_cold_read(legacy):
    api, app, path = legacy
    response = invoke(api, user_id=2, user_role='owner')
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body['success'] and body['status'] == 'COMPLETED'
    identifier = body['execution_id']
    fresh = app.test_client()
    history = fresh.get(BASE+'skills/invocations', headers=OWN)
    assert history.status_code == 200, history.get_json()
    assert [r['execution_id'] for r in history.json['records']] == [identifier]
    assert history.headers['Cache-Control'] == 'no-store'
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT user_id FROM skill_executions').fetchone()[0] == 1
    evidence = fresh.get(BASE+'intelligence/evidence', headers=evidence_headers())
    assert evidence.status_code == 200, evidence.get_json()
    assert evidence.json['count'] >= 1


@pytest.mark.parametrize('headers', [{}, {'Authorization':'Basic dXNlcjpwYXNz'}, {'X-Actor-ID':'1'}, {'Authorization':'Bearer wrong'}])
def test_anonymous_and_spoofed_identity_never_executes_or_reads(legacy, headers):
    api, _, path = legacy
    assert invoke(api, headers=headers).status_code == 403
    assert api.get(BASE+'skills/invocations', headers=headers).status_code == 403
    assert api.get(BASE+'intelligence/evidence', headers=evidence_headers(headers)).status_code in (401,403)
    with sqlite3.connect(path) as con:
        table = con.execute("SELECT 1 FROM sqlite_master WHERE name='skill_executions'").fetchone()
        assert not table or con.execute('SELECT count(*) FROM skill_executions').fetchone()[0] == 0


@pytest.mark.parametrize('change', ['actor', 'scope', 'source', 'inactive', 'signature'])
def test_other_actor_and_revocation_hide_history_and_evidence(legacy, change):
    api, app, path = legacy
    assert invoke(api).status_code == 200
    headers = OWN
    with sqlite3.connect(path) as con:
        if change == 'actor': headers = OTHER
        elif change == 'scope': con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE user_id=1")
        elif change == 'source': con.execute("UPDATE lumenis_subject_registry SET status='disabled' WHERE subject_id='SCOPE-A'")
        elif change == 'inactive': con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
        else: con.execute("UPDATE app_evidence_records SET integrity_digest='invalid'")
    history = app.test_client().get(BASE+'skills/invocations', headers=headers)
    assert history.status_code == 403 or history.json['records'] == []
    evidence = app.test_client().get(BASE+'intelligence/evidence', headers=evidence_headers(headers))
    assert evidence.status_code in (401,403,404) or evidence.json['chains'] == []


@pytest.mark.parametrize('extra', [{'scope':None}, {'scope':{}}, {'scope':{'subject_id':'SCOPE-B'}}, {'product':'SYSTEM'}, {'action_type':'PUSH'}])
def test_missing_or_substituted_scope_and_write_cannot_execute(legacy, extra):
    api, _, path = legacy
    with sqlite3.connect(path) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1", (json.dumps({'subject_ids':['SCOPE-A']}),))
    response = invoke(api, **extra)
    assert response.status_code in (400,403), response.get_json()
    assert not response.json.get('success')


def test_unowned_legacy_files_retained_and_never_read(legacy, tmp_path, monkeypatch):
    api, _, _ = legacy
    runtime = tmp_path/'runtime'; runtime.mkdir(exist_ok=True)
    history = runtime/'skill_invocations.jsonl'; history.write_text('{"task":"other-actor-secret"}\n')
    osai = tmp_path/'osai'; chains = osai/'evidence'/'chains'; chains.mkdir(parents=True)
    original = chains/'private.json'; original.write_text('{"result":"other-actor-secret"}')
    monkeypatch.setenv('OSAI_ROOT', str(osai))
    for route, headers in [('skills/invocations', OWN), ('intelligence/evidence', evidence_headers())]:
        response = api.get(BASE+route, headers=headers)
        assert response.status_code == 200, response.get_json()
        assert 'other-actor-secret' not in response.text and 'private.json' not in response.text
        assert response.json['legacy_history_state'] == 'UNBOUND_NOT_ADMITTED'
    assert history.exists() and original.exists()


@pytest.fixture
def legacy_agent(agent_client, monkeypatch):
    api, app, path = agent_client
    from lumenis_app_api import lumenis_bp
    app.register_blueprint(lumenis_bp)
    import lumenis_skill_adapter
    monkeypatch.setattr(lumenis_skill_adapter.CrossCoreSkillAdapter, '_run_osai',
                        lambda *a, **k: pytest.fail('external invocation forbidden'))
    return api, app, path


def test_sealed_local_task_binding_executes_and_reopens(legacy_agent, monkeypatch):
    api, app, path = legacy_agent
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    body = {'execution_mode':'agent', 'input':'Read local metadata', 'domain_id':'cth',
            'scope':{'global_scope':True, 'subject_id':None, 'brand_focus_id':None},
            'steps':[{'skill_id':SKILL,'input':{}}]}
    created = api.post('/api/ai/tasks', json=body)
    assert created.status_code == 202, created.get_json()
    task_id = created.json['task']['task_id']
    response = api.post(BASE+'skills/invoke', json={'task_id':task_id,'skill_id':SKILL})
    assert response.status_code == 200, response.get_json()
    assert response.json['success']
    reopened = api.get(BASE+'skills/invocations?task_id='+task_id)
    assert reopened.status_code == 200 and len(reopened.json['records']) == 1
    assert api.post(BASE+'skills/invoke', headers=OWN, json={'task_id':task_id,'skill_id':SKILL}).status_code == 403
    assert api.get(BASE+'skills/invocations?task_id='+task_id, headers=OWN).status_code == 403
    app.config['LUMENIS_OPEN_WORKSPACE'] = False
    assert api.get(BASE+'skills/invocations?task_id='+task_id).status_code == 403


def test_system_metadata_skill_remains_usable_with_real_module_grant(legacy, monkeypatch):
    api, _, path = legacy
    with sqlite3.connect(path) as con:
        con.execute("UPDATE skills_registry SET product='SYSTEM',domain='system' WHERE skill_id=?", (SKILL,))
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'SYSTEM',?,'read')", (SKILL,))
    response = invoke(api, product='SYSTEM', scope=None)
    assert response.status_code == 200, response.get_json()
    history = api.get(BASE+'skills/invocations', headers=OWN)
    assert len(history.json['records']) == 1
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE product_id='SYSTEM'")
    assert api.get(BASE+'skills/invocations', headers=OWN).json['records'] == []
    assert invoke(api, product='SYSTEM', scope=None).status_code == 403


def test_account_bound_task_rejects_other_actor_and_scope_substitution(legacy_agent):
    api, app, path = legacy_agent
    from tests.test_agent_runtime_http_binding import submit
    task_id = submit(api)
    payload = {'task_id':task_id, 'skill_id':SKILL}
    assert api.post(BASE+'skills/invoke', headers=OTHER, json=payload).status_code == 403
    assert api.post(BASE+'skills/invoke', headers=OWN, json={**payload,'scope':SCOPE}).status_code == 403
    response = api.post(BASE+'skills/invoke', headers=OWN, json=payload)
    assert response.status_code == 200, response.get_json()
    assert len(api.get(BASE+'skills/invocations?task_id='+task_id,headers=OWN).json['records']) == 1
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE module='agent_runtime'")
    assert api.post(BASE+'skills/invoke', headers=OWN, json=payload).status_code == 403
    assert api.get(BASE+'skills/invocations?task_id='+task_id,headers=OWN).status_code == 403


def test_local_producer_never_falls_through_to_external_adapter(legacy, monkeypatch):
    api, _, path = legacy
    from types import SimpleNamespace
    import lumenis_skill_adapter
    calls = []
    def provider(**kwargs):
        calls.append(kwargs)
        return {'connected':True, 'osai':{'status':'SUCCESS','result':{'summary':'fixture provider response'}}}
    monkeypatch.setattr(lumenis_skill_adapter,'get_skill_adapter',lambda:SimpleNamespace(available=True,invoke_skill=provider))
    assert invoke(api, headers=OTHER).status_code == 403
    assert calls == []
    response = invoke(api)
    assert response.status_code == 200, response.get_json()
    assert calls == []
    with sqlite3.connect(path) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE user_id=1")
    assert invoke(api).status_code == 403
    assert calls == []


def test_invalid_query_and_payload_are_bounded(legacy):
    api, _, _ = legacy
    for payload in ([], 'bad', {'skill_id':SKILL,'input':[]}):
        assert api.post(BASE+'skills/invoke', headers=OWN,json=payload).status_code == 400
    assert api.get(BASE+'skills/invocations?limit=bad',headers=OWN).status_code == 400
    assert api.get(BASE+'intelligence/evidence?limit=0',headers=evidence_headers()).status_code == 400


from tests.test_saved_document_workflow import workspace, _source


def test_original_document_owner_blocks_same_scope_other_actor_and_revoked_rights(workspace):
    from account.models import BASE_TABLES_SQL
    from lumenis_app_api import lumenis_bp
    from lumenis.shared.evidence import store
    ws = workspace
    ws['app'].register_blueprint(lumenis_bp)
    ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    with ws['repo'].transaction() as con:
        con.executescript(BASE_TABLES_SQL)
        con.executemany("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES(?,?,?,'owner','active')",
            [(1,'one','not-a-login'),(2,'two','not-a-login')])
        con.executemany("INSERT INTO v4_sessions(user_id,token,expires_at) VALUES(?,?,'2099-01-01 00:00:00')",[(1,'doc-one'),(2,'doc-two')])
    _, _, source = _source({**ws,'actor':{'id':1,'role':'owner'}})
    api = ws['app'].test_client()
    headers = {'Authorization':'Bearer doc-one','X-Lumenis-Context-Mode':'GLOBAL_ALL','X-Domain-Id':'CTH'}
    response = api.get(BASE+'intelligence/evidence',headers=headers)
    assert response.status_code == 200, response.get_json()
    assert [r['id'] for r in response.json['chains']] == [source['evidence_id']]
    assert 'Original source line' in response.text
    other = api.get(BASE+'intelligence/evidence',headers={**headers,'Authorization':'Bearer doc-two'})
    assert other.status_code == 200 and other.json['chains'] == []
    with ws['repo'].transaction() as con:
        metadata = json.loads(con.execute('SELECT collection_metadata FROM app_evidence_records WHERE id=?',(source['evidence_id'],)).fetchone()[0])
        metadata['provenance']['rights'] = 'revoked'
        con.execute('UPDATE app_evidence_records SET collection_metadata=? WHERE id=?',(json.dumps(metadata),source['evidence_id']))
        store._sign_evidence_record(con,source['evidence_id'])
    revoked = api.get(BASE+'intelligence/evidence',headers=headers)
    assert revoked.status_code == 200 and revoked.json['chains'] == []


def test_same_scope_foreign_execution_and_unbound_signed_producer_do_not_leak(legacy):
    api, _, path = legacy
    assert invoke(api).status_code == 200
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(2,'CTH','evidence','read',?)",(json.dumps({'global':True}),))
    response = api.get(BASE+'intelligence/evidence',headers=evidence_headers(OTHER))
    assert response.status_code == 200 and response.json['chains'] == []
    from lumenis.shared.evidence import store
    store.record_evidence(source='unbound-private-producer',product='CTH',domain_id='cth',subject_id='SCOPE-A',
        inputs={'private':'MUST_NOT_DISCLOSE'},outputs={'result':'MUST_NOT_DISCLOSE'})
    response = api.get(BASE+'intelligence/evidence',headers=evidence_headers())
    assert 'MUST_NOT_DISCLOSE' not in response.text


@pytest.mark.parametrize('mutation', ['runtime','source','version','unsigned_legacy','signature'])
def test_local_producer_receipt_rechecks_registry_and_proof(legacy, mutation):
    api, _, path = legacy
    assert invoke(api).status_code == 200
    with sqlite3.connect(path) as con:
        if mutation == 'unsigned_legacy':
            con.execute("DELETE FROM app_evidence_records WHERE source='skill_execution_local_producer'")
        elif mutation == 'signature':
            con.execute("UPDATE app_evidence_records SET integrity_digest='bad' WHERE source='skill_execution_local_producer'")
        else:
            value = {'runtime':'mcp','source':'external','version':'changed'}[mutation]
            con.execute('UPDATE skills_registry SET '+mutation+'=? WHERE skill_id=?',(value,SKILL))
    assert api.get(BASE+'skills/invocations',headers=OWN).json['records'] == []
    if mutation in ('runtime','source'):
        denied = invoke(api)
        assert denied.status_code == 403 and denied.json['code'] == 'SOURCE_READER_UNBOUND'


def test_source_references_and_unbound_skill_denied_before_handler(legacy):
    api, _, path = legacy
    response = invoke(api,input={'evidence_id':123})
    assert response.status_code == 403 and response.json['code'] == 'SOURCE_READER_UNBOUND'
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO skills_registry(skill_id,name,product,domain,status,version) VALUES('unbound','Unbound','CTH','cth','enabled','1')")
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','unbound','read',?)",(json.dumps({'global':True}),))
    response = invoke(api,skill_id='unbound')
    assert response.status_code == 403 and response.json['code'] == 'SOURCE_READER_UNBOUND'


def test_original_account_adapter_behavior_remains_default(legacy, monkeypatch):
    from types import SimpleNamespace
    import lumenis_skill_adapter
    api, _, _ = legacy
    calls = []
    def provider(**kwargs):
        calls.append(kwargs)
        return {'connected':True,'osai':{'status':'SUCCESS','result':{'summary':'controlled provider fixture'}}}
    monkeypatch.setattr(lumenis_skill_adapter,'get_skill_adapter',lambda:SimpleNamespace(available=True,invoke_skill=provider))
    response = api.post('/api/ai/tasks',headers=OWN,json={
        'skill_id':SKILL,'task':'Existing original owner','product':'CTH','scope':SCOPE,'action_type':'READ'})
    assert response.status_code == 200, response.get_json()
    assert response.json['success'] and len(calls) == 1
    # A scope receipt alone must not admit that opaque adapter output to the
    # stricter compatibility history's source-free producer lane.
    assert api.get(BASE+'skills/invocations',headers=OWN).json['records'] == []


def test_old_local_task_cache_without_producer_is_not_relabelled(legacy_agent):
    api, app, _ = legacy_agent
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    data = {'execution_mode':'agent','input':'Read local tools','domain_id':'cth',
        'scope':{'global_scope':True,'subject_id':None,'brand_focus_id':None},
        'steps':[{'skill_id':SKILL,'input':{}}]}
    created = api.post('/api/ai/tasks',json=data)
    task_id = created.json['task']['task_id']
    assert api.post('/api/ai/tasks/'+task_id+'/run').json['task']['status'] == 'succeeded'
    response = api.post(BASE+'skills/invoke',json={'task_id':task_id,'skill_id':SKILL})
    assert response.status_code == 409 and response.json['code'] == 'SOURCE_READER_UNBOUND'
    assert response.json['result'] is None


def test_evidence_pages_after_original_producer_authorization(legacy):
    api, _, _ = legacy
    assert invoke(api).status_code == 200
    from lumenis.shared.evidence import store
    for index in range(105):
        store.record_evidence(source='unbound',product='CTH',domain_id='cth',subject_id='SCOPE-A',
            inputs={'private':str(index)},outputs={'private':'not-visible'})
    response = api.get(BASE+'intelligence/evidence?limit=1',headers=evidence_headers())
    assert response.status_code == 200, response.get_json()
    assert response.json['count'] == 1 and response.json['chains'][0]['execution_id']
    second = api.get(BASE+'intelligence/evidence?limit=1&offset=1',headers=evidence_headers())
    assert second.json['chains'] == []


@pytest.mark.parametrize('route', ['skills/invocations','intelligence/evidence'])
def test_multirow_final_boundary_rechecks_earlier_producer(legacy, monkeypatch, route):
    api, _, path = legacy
    assert invoke(api,task='First').status_code == 200
    assert invoke(api,task='Second').status_code == 200
    from lumenis.shared.agents.skills import execution
    original = execution.read_source_free_execution
    calls = []
    def revoke(row, actor):
        result = original(row, actor)
        calls.append(row['execution_id'])
        if len(calls) == 2:
            with sqlite3.connect(path) as con:
                con.execute("DELETE FROM v4_member_authorizations WHERE module=?",(SKILL,))
        return result
    monkeypatch.setattr(execution,'read_source_free_execution',revoke)
    response = api.get(BASE+route,headers=evidence_headers() if route.startswith('intelligence') else OWN)
    assert response.status_code == 403, response.get_json()
    assert 'First' not in response.text and 'Second' not in response.text


@pytest.mark.parametrize('skill,inputs', [
    ('zbc.skill_registry_snapshot',{}), ('zbc.agent_boundary_audit',{}),
    ('shared.social_card',{'title':'Generated fixture','subtitle':'Local draft'}),
    ('shared.video_shotcraft',{'brief':'A short generated scene'}),
    ('shared.huashu',{'brief':'A local content workflow','audience':'fixture audience'}),
])
def test_all_five_existing_source_free_handlers_preserve_full_results(legacy, skill, inputs):
    api, _, path = legacy
    if skill != SKILL:
        with sqlite3.connect(path) as con:
            con.execute("INSERT INTO skills_registry(skill_id,name,product,domain,status,version) VALUES(?,?,'CTH','cth','enabled','1')",(skill,skill))
            con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH',?,'read',?)",(skill,json.dumps({'global':True})))
    response = invoke(api,skill_id=skill,input=inputs)
    assert response.status_code == 200 and response.json['success'], response.get_json()
    reopened = api.get(BASE+'skills/invocations?skill_id='+skill,headers=OWN)
    assert reopened.status_code == 200 and reopened.json['count'] == 1
    assert reopened.json['records'][0]['result'] == response.json['result']
    assert response.json['result']


def test_source_free_receipt_survives_cold_process(legacy):
    import os
    import subprocess
    import sys
    api, _, _ = legacy
    response = invoke(api)
    identifier = response.json['execution_id']
    code = '''import sys
from lumenis.system.security import permission
permission._TESTING_BYPASS_ENABLED=False
from lumenis.shared.agents.skills.execution import query_executions,read_source_free_execution
row=query_executions(execution_id=sys.argv[1],strict=True)[0]
assert read_source_free_execution(row,{'id':1}) is not None
assert read_source_free_execution(row,{'id':2}) is None
print('COLD_SOURCE_FREE_PRODUCER_PASS')
'''
    env = dict(os.environ); env.pop('PERMISSION_GATE_TESTING',None)
    result = subprocess.run([sys.executable,'-B','-c',code,identifier],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stdout+result.stderr
    assert 'COLD_SOURCE_FREE_PRODUCER_PASS' in result.stdout


def test_system_success_is_exact_signed_sanitized_projection(legacy):
    api, _, path = legacy
    sid = 'shared.social_card'
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO skills_registry(skill_id,name,product,domain,status,version) VALUES(?,?,'SYSTEM','system','enabled','1')",(sid,sid))
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'SYSTEM',?,'read')",(sid,))
    placeholder = 'Bearer generated-fixture-not-a-real-token-1234567890'
    response = invoke(api,skill_id=sid,product='SYSTEM',scope=None,input={'title':placeholder})
    assert response.status_code == 200, response.get_json()
    history = api.get(BASE+'skills/invocations?skill_id='+sid,headers=OWN)
    assert response.json['result'] == history.json['records'][0]['result']
    assert placeholder not in response.text and placeholder not in history.text


def test_sealed_local_success_is_exact_signed_sanitized_projection(legacy_agent):
    api, app, path = legacy_agent
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    sid = 'shared.social_card'
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO skills_registry(skill_id,name,product,domain,status,version) VALUES(?,?,'SHARED','global','enabled','1')",(sid,sid))
    placeholder = 'Generated local card'
    inputs = {'title':placeholder}
    data = {'execution_mode':'agent','input':'Prepare a local card','domain_id':'cth',
        'scope':{'global_scope':True,'subject_id':None,'brand_focus_id':None},
        'steps':[{'skill_id':sid,'input':inputs}]}
    created = api.post('/api/ai/tasks',json=data)
    assert created.status_code == 202, created.get_json()
    task_id = created.json['task']['task_id']
    response = api.post(BASE+'skills/invoke',json={'task_id':task_id,'skill_id':sid,'input':inputs})
    assert response.status_code == 200, response.get_json()
    history = api.get(BASE+'skills/invocations?task_id='+task_id)
    assert response.json['result'] == history.json['records'][0]['result']
    assert 'approval_required' not in json.dumps(response.json['result'])
