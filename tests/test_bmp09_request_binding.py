"""BMP-09 carries its exact screen selection into the existing reports owner."""
import json
import pytest
from tests.test_saved_document_workflow import workspace

PATH = '/api/experience/screen/BMP-09'
GLOBAL = {'domain_id':'zbmp','subject_id':None,'brand_focus_id':None,'global_scope':True}

@pytest.fixture
def client(workspace):
    import experience_runtime
    workspace['app'].register_blueprint(experience_runtime.experience_bp)
    return workspace['app'].test_client(), workspace

def save(ws, *, actor=None, scope=None, key='global'):
    return ws['work'].save_work(actor=actor or ws['actor'], scope=scope or GLOBAL, title='Private '+key,
        kind='research',markdown='Original synthetic research',payload={},citations=[],request_id='bmp09-'+key)

def ids(r):
    assert r.status_code == 200, r.get_json()
    return [x['id'] for x in r.get_json()['saved_artifacts']]

def accounts(ws):
    import account.models
    with ws['repo'].transaction() as con:
        con.executescript(account.models.BASE_TABLES_SQL)
        con.executescript(account.models.SKILLS_TABLES_SQL)
        con.executescript(account.models.AUTHORIZATION_TABLES_SQL)
        con.executemany("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES (?,?,?,'owner','active')",[(1,'one','not-a-login'),(2,'two','not-a-login')])
        con.executemany("INSERT INTO v4_sessions(user_id,token,expires_at) VALUES (?,?,?)",[(1,'bmp-one','2099-01-01 00:00:00'),(2,'bmp-two','2099-01-01 00:00:00')])
    ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    return {'Authorization':'Bearer bmp-one'}, {'Authorization':'Bearer bmp-two'}

def test_bmp09_no_domain_header_global_reads_own_reports(client):
    http, ws = client
    made = save(ws)
    assert ids(http.get(PATH)) == [made['artifact']['artifact_id']]
    assert ids(http.get(PATH,headers={'X-Domain-Id':'BMP'})) == [made['artifact']['artifact_id']]
    assert http.get(PATH,headers={'X-Domain-Id':'CTH'}).status_code == 400
    assert http.post(PATH).status_code == 405

def test_bmp09_focus_never_broadens_to_other_brand_or_global(client):
    http, ws = client
    from subject_registry import add_subject
    first,_ = add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Brand A','name_zh':'品牌甲'})
    second,_ = add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Brand B','name_zh':'品牌乙'})
    scope = {**GLOBAL,'brand_focus_id':first['brand_focus_id'],'global_scope':False}
    made = save(ws,scope=scope,key='focus')
    headers = {'X-Domain-Id':'BMP','X-Lumenis-Context-Mode':'FOCUS','X-Subject-ID':first['subject_id']}
    assert ids(http.get(PATH,headers=headers)) == [made['artifact']['artifact_id']]
    assert ids(http.get(PATH,headers={**headers,'X-Subject-ID':second['subject_id']})) == []
    assert ids(http.get(PATH)) == []
    assert http.get(PATH,headers={**headers,'X-Brand-Focus-ID':second['brand_focus_id']}).status_code == 400
    assert http.get(PATH,headers={'X-Brand-Focus-ID':first['brand_focus_id']}).status_code == 400
    ws['repo'].execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE subject_id=?",(first['subject_id'],))
    assert http.get(PATH,headers=headers).status_code >= 400

def test_bmp09_current_actor_isolation_revoke_recover(client):
    http, ws = client
    one,two = accounts(ws)
    made = save(ws,actor={'id':1,'role':'owner'},key='account-one')
    assert ids(http.get(PATH,headers=one)) == [made['artifact']['artifact_id']]
    assert ids(http.get(PATH,headers=two)) == []
    assert ids(http.get(PATH,headers={**two,'X-Actor-ID':'1'})) == []
    assert http.get(PATH).status_code == 401
    assert http.get(PATH,headers={'Authorization':'Bearer bad'}).status_code == 401
    ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    assert http.get(PATH,headers=one).status_code >= 400
    assert ids(http.get(PATH,headers=two)) == []
    ws['repo'].execute("UPDATE v4_users SET status='active' WHERE id=1")
    assert ids(http.get(PATH,headers=one)) == [made['artifact']['artifact_id']]

def test_bmp09_screen_read_grant_does_not_grant_reports(client):
    http, ws = client
    one,_ = accounts(ws)
    ws['repo'].execute("UPDATE v4_users SET role='user' WHERE id=1")
    ws['repo'].execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'ZBMP','brand_market_overview','read',?)",(json.dumps({'global':True}),))
    response = http.get(PATH,headers=one)
    assert response.status_code == 403
    assert 'sections' not in response.get_json()
    ws['repo'].execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'ZBMP','reports','read',?)",(json.dumps({'global':True}),))
    assert ids(http.get(PATH,headers=one)) == []
    ws['repo'].execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND module='reports'")
    assert http.get(PATH,headers=one).status_code >= 400

def test_bmp09_binding_change_during_read_is_denied(client,monkeypatch):
    http, ws = client
    made=save(ws)
    import experience_runtime as r
    original=r._bmp01_read_scope
    calls=[]
    def changed():
        binding,error=original();calls.append(1)
        if len(calls)>2:binding={**binding,'brand_focus_id':'different'}
        return binding,error
    monkeypatch.setattr(r,'_bmp01_read_scope',changed)
    response=http.get(PATH)
    assert response.status_code>=400
    assert made['artifact']['artifact_id'] not in json.dumps(response.get_json())

def test_bmp09_actor_change_during_read_is_denied(client,monkeypatch):
    http, ws = client
    one,_=accounts(ws)
    made=save(ws,actor={'id':1,'role':'owner'})
    import experience_runtime as r
    original=r._bmp_saved_work_actor_scope
    calls=[]
    def changed(binding):
        actor,scope=original(binding);calls.append(1)
        return (actor if len(calls)==1 else {'id':2,'role':'owner'}),scope
    monkeypatch.setattr(r,'_bmp_saved_work_actor_scope',changed)
    response=http.get(PATH,headers=one)
    assert response.status_code>=400
    assert made['artifact']['artifact_id'] not in json.dumps(response.get_json())

def test_bmp09_report_permission_withdrawn_during_read(client,monkeypatch):
    http,ws=client
    one,_=accounts(ws)
    made=save(ws,actor={'id':1,'role':'owner'})
    from lumenis.shared.reporting import saved_work
    original=saved_work.search_work
    def revoked(**kwargs):
        result=original(**kwargs)
        ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
        return result
    monkeypatch.setattr(saved_work,'search_work',revoked)
    response=http.get(PATH,headers=one)
    assert response.status_code>=400
    assert made['artifact']['artifact_id'] not in json.dumps(response.get_json())

def test_bmp09_helper_rejects_wrong_route_and_shared_scope(client):
    http,ws=client
    import experience_runtime as r
    with ws['app'].test_request_context('/api/experience/screen/BMP-01'):
        with pytest.raises(PermissionError,match='BMP_REPORT_ROUTE_UNAUTHORIZED'): r._bmp_saved_work_actor_scope({})
    response=http.get(PATH,headers={'X-Lumenis-Workspace-Scope':json.dumps({'scope_kind':'shared_workspace','version':1})})
    assert response.status_code>=400

def test_bmp09_authenticated_focus_uses_brand_not_cth_subject_permission(client):
    http,ws=client
    one,_=accounts(ws)
    from subject_registry import add_subject
    first,_=add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Authenticated A','name_zh':'账户品牌甲'})
    other,_=add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Authenticated B','name_zh':'账户品牌乙'})
    scope={**GLOBAL,'brand_focus_id':first['brand_focus_id'],'global_scope':False}
    made=save(ws,actor={'id':1,'role':'owner'},scope=scope,key='authenticated-focus')
    headers={**one,'X-Domain-Id':'BMP','X-Lumenis-Context-Mode':'FOCUS','X-Subject-ID':first['subject_id']}
    assert ids(http.get(PATH,headers=headers))==[made['artifact']['artifact_id']]
    assert ids(http.get(PATH,headers={**headers,'X-Subject-ID':other['subject_id']}))==[]
    assert ids(http.get(PATH,headers=one))==[]
    assert http.get(PATH,headers={**headers,'X-Brand-Focus-ID':other['brand_focus_id']}).status_code==400

def test_bmp09_brand_limited_grants_cannot_read_other_focus_or_global(client):
    http,ws=client
    one,_=accounts(ws)
    from subject_registry import add_subject
    first,_=add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Granted A','name_zh':'授权品牌甲'})
    other,_=add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Granted B','name_zh':'授权品牌乙'})
    scope={**GLOBAL,'brand_focus_id':first['brand_focus_id'],'global_scope':False}
    made=save(ws,actor={'id':1,'role':'owner'},scope=scope,key='limited-focus')
    ws['repo'].execute("UPDATE v4_users SET role='user' WHERE id=1")
    header={**one,'X-Domain-Id':'BMP','X-Lumenis-Context-Mode':'FOCUS','X-Subject-ID':first['subject_id']}
    assert http.get(PATH,headers=header).status_code==403
    for module in ['subject_registry','brand_market_overview','reports']:
        ws['repo'].execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'ZBMP',?,'read',?)",(module,json.dumps({'brand_focus_ids':[first['brand_focus_id']]})))
    assert ids(http.get(PATH,headers=header))==[made['artifact']['artifact_id']]
    assert http.get(PATH,headers={**header,'X-Subject-ID':other['subject_id']}).status_code==403
    assert http.get(PATH,headers=one).status_code==403
    ws['repo'].execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND module='reports'")
    assert http.get(PATH,headers=header).status_code==403


def test_bmp09_typed_artifacts_preserve_report_owner_authorization(client):
    http,ws=client
    one,_=accounts(ws)
    made=save(ws,actor={'id':1,'role':'owner'},key='typed-owner')
    body=http.get(PATH,headers=one).get_json()
    assert body['report_artifact_contract']=='lumenis.bmp09-report-artifacts.v1'
    assert body['report_authorization']=={'module':'reports','action':'read','context':{**GLOBAL,'actor_id':1}}
    assert body['report_screen_binding']==body['global_binding']
    assert body['report_screen_binding']['module']=='brand_market_overview'
    row=body['saved_artifacts'][0]
    assert row['resource_type']=='saved_work' and row['id']==made['artifact']['artifact_id']
    assert row['sha256']==made['artifact']['sha256'] and row['version']==1
    assert row['assessment']=='NOT_ESTABLISHED_BY_STORAGE' and 'evaluations' not in row
    assert body['truth']['market_effect_state']=='NOT_ESTABLISHED'
    assert 'granted_permissions' not in body['report_authorization']


def test_bmp09_typed_payload_not_exposed_when_reports_revoked(client,monkeypatch):
    http,ws=client
    one,_=accounts(ws)
    save(ws,actor={'id':1,'role':'owner'},key='typed-revoked')
    from lumenis.shared.reporting import source_brief_job
    original=source_brief_job.list_source_brief_jobs
    def revoke(**kwargs):
        result=original(**kwargs)
        ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
        return result
    monkeypatch.setattr(source_brief_job,'list_source_brief_jobs',revoke)
    response=http.get(PATH,headers=one)
    assert response.status_code>=400
    body=response.get_json()
    assert all(key not in body for key in ['saved_artifacts','source_brief_artifacts','report_authorization','sections'])
