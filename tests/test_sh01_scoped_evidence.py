"""SH-01 uses the existing Content owner, signed evidence and current principal."""
import json
import pytest
from tests.test_saved_document_workflow import workspace, _source
from tests.test_content_scoped_patterns import client as content_client, create, candidate, HEADERS

PATH = '/api/experience/screen/SH-01'

@pytest.fixture
def client(content_client):
    import experience_runtime
    http, ws = content_client
    ws['app'].register_blueprint(experience_runtime.experience_bp)
    return http, ws

def rows(response):
    assert response.status_code == 200, response.get_json()
    return next(s['rows'] for s in response.get_json()['sections'] if s['type'] == 'table')

def test_sh01_same_scope_reads_signed_evidence_other_scope_hidden(client):
    http, ws = client
    source, made = create(client)
    assert [r['evidence_id'] for r in rows(http.get(PATH, headers=HEADERS))] == [made['evidence_id']]
    other = {'X-Domain-Id': 'BMP', 'X-Product-Id': 'ZBMP'}
    assert rows(http.get(PATH, headers=other)) == []
    with ws['repo'].transaction() as con:
        con.execute("UPDATE app_evidence_records SET content_hash='tampered' WHERE id=?", (source['evidence_id'],))
    assert rows(http.get(PATH, headers=HEADERS)) == []

def test_sh01_shared_independent_scope(client):
    http, ws = client
    _, _, source = _source(ws)
    headers = {'X-Lumenis-Workspace-Scope': json.dumps({'scope_kind':'shared_workspace','version':1})}
    made = http.post('/api/content/patterns', json=candidate(source['evidence_id']), headers=headers)
    assert made.status_code == 201, made.get_json()
    assert [r['evidence_id'] for r in rows(http.get(PATH, headers=headers))] == [made.get_json()['evidence_id']]
    assert rows(http.get(PATH, headers=HEADERS)) == []

def test_sh01_current_account_isolation_revocation_and_recovery(client):
    http, ws = client
    import account.models
    with ws['repo'].transaction() as con:
        con.executescript(account.models.BASE_TABLES_SQL)
        con.executemany("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES (?,?,?,'owner','active')", [(1,'one','not-a-login'),(2,'two','not-a-login')])
        con.executemany("INSERT INTO v4_sessions(user_id,token,expires_at) VALUES (?,?,?)",[(1,'screen-one','2099-01-01 00:00:00'),(2,'screen-two','2099-01-01 00:00:00')])
    ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    one = {**HEADERS, 'Authorization':'Bearer screen-one'}
    two = {**HEADERS, 'Authorization':'Bearer screen-two'}
    _, _, source = _source({**ws,'actor':{'id':1,'role':'owner'}})
    made = http.post('/api/content/patterns', json=candidate(source['evidence_id']), headers=one)
    assert made.status_code == 201, made.get_json()
    eid = made.get_json()['evidence_id']
    assert [r['evidence_id'] for r in rows(http.get(PATH, headers=one))] == [eid]
    assert rows(http.get(PATH, headers=two)) == []
    assert rows(http.get(PATH, headers={**two, 'X-Actor-ID':'1','X-User-ID':'1'})) == []
    assert http.post(PATH, headers=one).status_code == 405
    assert http.get(PATH, headers=HEADERS).status_code == 403
    assert http.get(PATH, headers={**HEADERS,'Authorization':'Bearer invalid'}).status_code == 403
    with ws['repo'].transaction() as con: con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    response = http.get(PATH, headers=one)
    assert response.status_code == 403
    assert 'trace' not in response.get_json()
    assert rows(http.get(PATH, headers=two)) == []
    with ws['repo'].transaction() as con: con.execute("UPDATE v4_users SET status='active' WHERE id=1")
    assert [r['evidence_id'] for r in rows(http.get(PATH, headers=one))] == [eid]

def test_sh01_revalidates_principal_after_read(client, monkeypatch):
    http, ws = client
    _, made = create(client)
    import content_generation as c
    original = c.authorize_content_root_request
    calls = []
    def change(**kwargs):
        context = original(**kwargs)
        calls.append(context)
        return context if len(calls) == 1 else {**context, 'actor_id':999}
    monkeypatch.setattr(c, 'authorize_content_root_request', change)
    response = http.get(PATH, headers=HEADERS)
    assert response.status_code == 403
    assert response.get_json()['bound'] is False
    assert made['evidence_id'] not in json.dumps(response.get_json())

def test_sh01_revalidates_denial_after_read(client, monkeypatch):
    http, ws = client
    create(client)
    import content_generation as c
    original = c.list_evidence
    def revoked(*args, **kwargs):
        result = original(*args, **kwargs)
        def deny(**kwargs): raise PermissionError('CONTENT_SCOPE_REVOKED')
        monkeypatch.setattr(c, 'authorize_content_root_request', deny)
        return result
    monkeypatch.setattr(c, 'list_evidence', revoked)
    assert http.get(PATH, headers=HEADERS).status_code == 403

@pytest.mark.parametrize('path', ['/api/experience/screen/SH-02','/api/experience/screen/SH-010'])
def test_sh01_does_not_delegate_other_routes(client, path):
    _, ws = client
    import content_generation as c
    with ws['app'].test_request_context(path, headers=HEADERS):
        with pytest.raises(PermissionError, match='CONTENT_ROUTE_UNAUTHORIZED'):
            c.authorize_content_root_request(strict=True)
