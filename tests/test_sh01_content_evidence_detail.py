"""Real owner HTTP roundtrip and negative access regressions; no external calls."""
import json
import ast
import secrets
from pathlib import Path
from flask import request, jsonify
import pytest
from tests.test_saved_document_workflow import workspace as owner_workspace, _source
from tests.test_content_scoped_patterns import client as content_client, create, candidate, HEADERS


def install_actual_root_guard(app):
    module = ast.parse((Path(__file__).resolve().parents[1] / 'app.py').read_text())
    names = {'_owner_authorized_root_request', '_is_cth_readonly_get', '_auth_enabled', '_basic_auth'}
    nodes = []
    for item in module.body:
        if isinstance(item, ast.FunctionDef) and item.name in names:
            item.decorator_list = []; nodes.append(item)
        elif isinstance(item, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_CTH_READONLY_GET_PREFIXES' for t in item.targets):
            nodes.append(item)
    assert {n.name for n in nodes if isinstance(n, ast.FunctionDef)} == names
    env = dict(request=request, jsonify=jsonify, secrets=secrets,
               AUTH_USER='synthetic', AUTH_PASSWORD='fixture-only')
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<actual-root-auth>', 'exec'), env)
    app.before_request_funcs.setdefault(None, []).insert(0, env['_basic_auth'])

@pytest.fixture
def workspace(owner_workspace, monkeypatch):
    import account.models
    import lumenis.auth.models as auth_models
    import lumenis.shared.database as shared_database
    monkeypatch.setattr(account.models, 'get_repository', lambda: owner_workspace['repo'])
    monkeypatch.setattr(shared_database, 'get_repository', lambda: owner_workspace['repo'])
    monkeypatch.setattr(auth_models, "get_repository", lambda: owner_workspace["repo"])
    return owner_workspace

@pytest.fixture
def client(content_client):
    import experience_runtime
    http, ws = content_client
    ws['app'].register_blueprint(experience_runtime.experience_bp)
    install_actual_root_guard(ws['app'])
    return http, ws

def path(eid): return '/api/experience/content/evidence/'+eid

def test_real_creator_detail_readonly_and_source_revocation(client):
    http, ws = client
    source, made = create(client)
    with ws['repo'].connection() as con: before = '\n'.join(con.iterdump())
    response = http.get(path(made['evidence_id']), headers=HEADERS)
    assert response.status_code == 200, response.get_json()
    payload=response.get_json(); assert payload['evidence']['evidence_id']==made['evidence_id']
    assert payload['evidence']['output'] == made['candidate']
    assert not {'input_json','prompt','_content_context'} & set(payload['evidence'])
    with ws['repo'].connection() as con: assert '\n'.join(con.iterdump())==before
    assert http.get(path(made['evidence_id']),headers={'X-Domain-Id':'BMP','X-Product-Id':'ZBMP'}).status_code==404
    with ws['repo'].transaction() as con:
        con.execute("UPDATE app_evidence_records SET content_hash='withdrawn' WHERE id=?",(source['evidence_id'],))
    denied=http.get(path(made['evidence_id']),headers=HEADERS)
    assert denied.status_code==404 and 'evidence' not in denied.get_json()

def test_account_identity_revoke_recover(client):
    http, ws=client
    from tests.test_bmp09_request_binding import accounts
    one,two=accounts(ws);one={**HEADERS,**one};two={**HEADERS,**two}
    _,_,source=_source({**ws,'actor':{'id':1,'role':'owner'}})
    made=http.post('/api/content/patterns',headers=one,json=candidate(source['evidence_id']))
    assert made.status_code==201,made.get_json()
    url=path(made.get_json()['evidence_id'])
    assert http.get(url,headers=one).status_code==200
    assert http.get(url,headers=two).status_code==404
    assert http.get(url,headers={**two,'X-Actor-ID':'1'}).status_code==404
    assert http.get(url,headers={**HEADERS,'Authorization':'Bearer invalid'}).status_code==401
    ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    assert http.get(url,headers=one).status_code==401
    ws['repo'].execute("UPDATE v4_users SET status='active' WHERE id=1")
    assert http.get(url,headers=one).status_code==200

def test_shared_workspace_exact_route_boundary(client):
    http,ws=client
    _,_,source=_source(ws)
    headers={'X-Lumenis-Workspace-Scope':json.dumps({'scope_kind':'shared_workspace','version':1})}
    made=http.post('/api/content/patterns',json=candidate(source['evidence_id']),headers=headers)
    assert made.status_code==201,made.get_json()
    url=path(made.get_json()['evidence_id'])
    assert http.get(url,headers=headers).status_code==200
    assert http.get(url,headers=HEADERS).status_code==404
    assert http.post(url,headers=headers).status_code in (401, 405)
    assert http.get(path('invalid'),headers=headers).status_code==400
    import content_generation as c
    for wrong in [url+'/extra','/api/experience/content/evidences/'+made.get_json()['evidence_id']]:
        with ws['app'].test_request_context(wrong,headers=headers):
            with pytest.raises(PermissionError,match='CONTENT_ROUTE_UNAUTHORIZED'):
                c.authorize_content_root_request(strict=True)

def test_source_withdrawn_between_real_reads_denied(client,monkeypatch):
    http,ws=client;source,made=create(client)
    import content_generation as c
    original=c.get_evidence;calls=[]
    def read(*args,**kwargs):
        result=original(*args,**kwargs);calls.append(1)
        if len(calls)==1:
            ws['repo'].execute("UPDATE app_evidence_records SET content_hash='withdrawn' WHERE id=?",(source['evidence_id'],))
        return result
    monkeypatch.setattr(c,'get_evidence',read)
    result=http.get(path(made['evidence_id']),headers=HEADERS)
    assert result.status_code==403 and 'evidence' not in result.get_json()
    assert len(calls)==2

def test_principal_revoked_between_real_reads_denied(client,monkeypatch):
    http,ws=client
    from tests.test_bmp09_request_binding import accounts
    one,_=accounts(ws);one={**HEADERS,**one}
    _,_,source=_source({**ws,'actor':{'id':1,'role':'owner'}})
    made=http.post('/api/content/patterns',headers=one,json=candidate(source['evidence_id']))
    assert made.status_code==201,made.get_json()
    import content_generation as c
    original=c.get_evidence
    def read(*args,**kwargs):
        result=original(*args,**kwargs)
        ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
        return result
    monkeypatch.setattr(c,'get_evidence',read)
    response=http.get(path(made.get_json()['evidence_id']),headers=one)
    assert response.status_code==403 and 'evidence' not in response.get_json()


def test_root_guard_does_not_open_unregistered_or_closed_workspace(client):
    http, ws = client
    _, made = create(client)
    assert http.get('/unregistered-private-route', headers=HEADERS).status_code == 401
    ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    denied = http.get(path(made['evidence_id']), headers=HEADERS)
    assert denied.status_code in (401, 403)
    assert 'evidence' not in denied.get_json()
