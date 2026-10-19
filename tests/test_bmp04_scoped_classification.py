import importlib.util
from pathlib import Path
import pytest
from tests import test_experience_runtime as fixture
isolated_client=fixture.isolated_client
PATH='/api/experience/propagation/classify'

@pytest.fixture
def setup(isolated_client,monkeypatch):
    import database
    from subject_registry import add_subject
    from lumenis.system.security import permission
    monkeypatch.setattr(permission, '_TESTING_BYPASS_ENABLED', False)
    cli,db=isolated_client
    brand,_=add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Synthetic','name_zh':'合成'})
    # Real source producer binds the fixture note to the registry's exact BrandFocus.
    scope=fixture._admit_existing_note(db,monkeypatch,'n1',bmp=True)
    # Fixture helper's fixed focus must use the actual registered focus throughout.
    from canonical_data import CanonicalRecord,persist_canonical
    from lumenis.shared.evidence import store
    scope={**scope,'brand_focus_id':brand['brand_focus_id']}
    with database.get_db() as con:
        eid=store.record_evidence(connection=con,source='public_http',project='LUMENIS',product='ZBMP',domain_id='zbmp',brand_focus_id=scope['brand_focus_id'],feature_id='TEST',test_name='source',result='PASS',status='verified',inputs={'source_ids':['n1']},outputs={'synthetic':True})
        con.execute("UPDATE notes SET brand_focus_id=?,scope_evidence_ref=? WHERE note_id='n1'",(scope['brand_focus_id'],str(eid)))
        con.execute("DELETE FROM canonical_data WHERE source_id='n1'")
        persist_canonical(con,CanonicalRecord(canonical_id='bmp-test-n1',product_id='ZBMP',domain_id='zbmp',brand_focus_id=scope['brand_focus_id'],scope_status='VERIFIED',scope_evidence_ref=str(eid),source_id='n1',external_id='n1',source_type='note',source_table='notes',source_platform='x',title='Synthetic',raw_ref='{"table":"notes","note_id":"n1"}'))
    gate=permission.PermissionGate();gate.grant_permission(permission.PermissionLevel.COMMIT);gate.grant_permission(permission.PermissionLevel.HUMAN_APPROVAL)
    monkeypatch.setattr(permission,'get_permission_gate',lambda:gate)
    h={'X-Domain-Id':'BMP','X-Lumenis-Context-Mode':'FOCUS','X-Subject-ID':brand['subject_id']}
    ids=[]
    for i in range(3):
        ids.append(database.upsert_event({'event_key':database._event_scope_token(scope)+'.test-'+str(i),'title':'Synthetic specific launch event '+str(i),'status':'active','risk_level':'high'},scope=scope,mentions=[{'source_type':'note','source_id':'n1'}]))
    return cli,db,h,ids,eid

def write(cli,h,eid,category,rid):
    b={'source_event_id':eid,'category':category,'request_id':rid}
    r=cli.post(PATH,headers=h,json=b);assert r.status_code==200,r.get_json()
    b.update(confirm=True,confirmed_resource=r.get_json()['resource'])
    r=cli.post(PATH,headers=h,json=b);assert r.status_code==200,r.get_json()
    return r

def test_three_real_classifications(setup):
    cli,db,h,ids,eid=setup
    for i,cat in enumerate(('brand_event','product_event','industry_event')):write(cli,h,ids[i],cat,'classify-test-'+str(i))
    r=cli.get('/api/experience/screen/BMP-04',headers=h);assert r.status_code==200,r.get_json()
    data=r.get_json()['truth'];assert [x['observed_events'] for x in data['dashboards']]==[1,1,1]
    assert data['unclassified_event_count']==0
    assert all(x['source_refs'] and x['claim_type']=='human_business_classification' for x in data['dashboards'])

def test_unclassified_and_revoked_not_zero(setup):
    cli,db,h,ids,eid=setup
    data=cli.get('/api/experience/screen/BMP-04',headers=h).get_json()['truth']
    assert data['unclassified_event_count']==3
    assert all(x['total_events'] is None for x in data['dashboards'])
    write(cli,h,ids[0],'brand_event','classify-revoke-1')
    import database
    with database.get_db() as con:con.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?",(eid,))
    data=cli.get('/api/experience/screen/BMP-04',headers=h).get_json()['truth']
    assert data['classification_rejected']==1
    assert all(x['total_events'] is None for x in data['dashboards'])

def test_idempotent_and_stale_preview(setup):
    cli,db,h,ids,eid=setup
    body={'source_event_id':ids[0],'category':'brand_event','request_id':'same-request-0001'}
    p=cli.post(PATH,headers=h,json=body).get_json()
    confirmed={**body,'confirm':True,'confirmed_resource':p['resource']}
    one=cli.post(PATH,headers=h,json=confirmed);assert one.status_code==200,one.get_json()
    two=cli.post(PATH,headers=h,json=confirmed);assert two.status_code==200,two.get_json()
    assert one.get_json()==two.get_json()
    stale={**body,'request_id':'other-request-001','category':'product_event'}
    old=cli.post(PATH,headers=h,json=stale).get_json()
    write(cli,h,ids[0],'industry_event','changed-request-001')
    assert cli.post(PATH,headers=h,json={**stale,'confirm':True,'confirmed_resource':old['resource']}).status_code==403

def test_real_app_guards_on_exact_route(setup):
    # Execute the exact production guard bodies against the same HTTP app;
    # avoid app import's unrelated scheduler/startup effects in this offline test.
    import ast,os,secrets
    from flask import request,jsonify,Response
    cli,db,h,ids,eid=setup
    source=(Path(__file__).resolve().parents[1]/'app.py').read_text()
    parsed=ast.parse(source)
    names={'_basic_auth','_permission_gate_write_check','_owner_authorized_root_request','_auth_enabled','_is_cth_readonly_get'}
    nodes=[]
    for node in parsed.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list=[];nodes.append(node)
    ns={'request':request,'jsonify':jsonify,'Response':Response,'os':os,'secrets':secrets,
        'AUTH_USER':'configured','AUTH_PASSWORD':'synthetic-basic-secret',
        '_CTH_READONLY_GET_PREFIXES':(), '_PG_WRITE_METHODS':{'POST','PUT','PATCH','DELETE'},'app':cli.application}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-app-guards','exec'),ns)
    cli.application.before_request_funcs.setdefault(None,[]).extend([ns['_basic_auth'],ns['_permission_gate_write_check']])
    write(cli,h,ids[0],'brand_event','guarded-classify-001')
    assert cli.post(PATH+'-unrelated',headers=h,json={}).status_code==401
    assert cli.get(PATH,headers=h).status_code==401

def test_foreign_origin_denied(setup):
    cli,db,h,ids,eid=setup
    assert cli.post(PATH,headers={**h,'Origin':'https://foreign.invalid'},json={'source_event_id':ids[0],'category':'brand_event','request_id':'foreign-origin-001'}).status_code==403

def test_actor_scope_and_legacy_isolation(setup,monkeypatch):
    import account.models
    import lumenis.auth.models as auth_models
    import lumenis.shared.database as shared_database
    from tests.test_bmp09_request_binding import accounts
    from subject_registry import add_subject
    cli,db,h,ids,eid=setup
    repo=shared_database.DatabaseRepository(db)
    monkeypatch.setattr(auth_models,'get_repository',lambda:repo)
    one,two=accounts({'repo':repo,'app':cli.application})
    h={**h,**one}
    write(cli,h,ids[0],'brand_event','actor-one-classify')
    r=cli.get('/api/experience/screen/BMP-04',headers=h);assert r.status_code==200,r.get_json()
    assert r.get_json()['truth']['dashboards'][0]['observed_events']==1
    r=cli.get('/api/experience/screen/BMP-04',headers={**h,**two,'X-Actor-ID':'1'})
    assert r.status_code==200,r.get_json()
    assert all(d['observed_events']==0 for d in r.get_json()['truth']['dashboards'])
    b,_=add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Other','name_zh':'其他'})
    r=cli.get('/api/experience/screen/BMP-04',headers={**h,'X-Subject-ID':b['subject_id']})
    assert r.status_code==200 and all(d['observed_events']==0 for d in r.get_json()['truth']['dashboards'])
    with repo.transaction() as con:
        con.execute("INSERT INTO brand_propagation_events(event_id,title,category) VALUES('legacy-secret','must-not-leak','product_event')")
    r=cli.get('/api/experience/screen/BMP-04',headers=h)
    assert 'must-not-leak' not in r.get_data(as_text=True)
    repo.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    assert cli.post(PATH,headers=h,json={'source_event_id':ids[1],'category':'brand_event','request_id':'after-revoke-user'}).status_code>=400
    assert cli.get('/api/experience/screen/BMP-04',headers=h).status_code>=400

def test_changed_classification_rejected(setup):
    cli,db,h,ids,eid=setup
    write(cli,h,ids[0],'product_event','classify-metadata-1')
    import database
    with database.get_db() as con:con.execute("UPDATE brand_propagation_events SET category='industry_event'")
    d=cli.get('/api/experience/screen/BMP-04',headers=h).get_json()['truth']
    assert d['classification_rejected']==1 and d['classification_state']=='PARTIAL'
    assert all(x['observed_events']==0 and x['total_events'] is None for x in d['dashboards'])

def test_scoped_page_ignores_unrelated_rows(setup):
    import database,json
    cli,db,h,ids,eid=setup
    write(cli,h,ids[0],'brand_event','scope-page-0001')
    before=cli.get('/api/experience/screen/BMP-04',headers=h).get_json()['truth']
    gh={'X-Domain-Id':'BMP','X-Lumenis-Context-Mode':'GLOBAL_ALL'}
    global_before=cli.get('/api/experience/screen/BMP-04',headers=gh).get_json()['truth']
    with database.get_db() as con:
        proof=json.loads(con.execute('SELECT metadata FROM brand_propagation_events').fetchone()[0])
        other_actor=json.loads(json.dumps(proof)); other_actor['context']['actor_id']=999999
        other_brand=json.loads(json.dumps(proof)); other_brand['context']['brand_focus_id']='foreign-focus'
        records=[]
        for i in range(1001):
            for kind,metadata in [('legacy','{broken'),('actor',json.dumps(other_actor)),('brand',json.dumps(other_brand))]:
                records.append((f'AAA-{kind}-{i:04}',metadata))
        con.executemany("INSERT INTO brand_propagation_events(event_id,title,category,metadata) VALUES(?,'unrelated','brand_event',?)",records)
    after=cli.get('/api/experience/screen/BMP-04',headers=h).get_json()['truth']
    assert after==before
    assert cli.get('/api/experience/screen/BMP-04',headers=gh).get_json()['truth']==global_before
    assert after['dashboards'][0]['observed_events']==1

def test_copied_metadata_is_rejected_without_double_count(setup):
    import database
    cli,db,h,ids,eid=setup
    write(cli,h,ids[0],'brand_event','copy-proof-0001')
    with database.get_db() as con:
        con.execute("INSERT INTO brand_propagation_events(event_id,title,category,metadata) SELECT 'copied-id',title,category,metadata FROM brand_propagation_events LIMIT 1")
    after=cli.get('/api/experience/screen/BMP-04',headers=h).get_json()['truth']
    assert after['dashboards'][0]['observed_events']==1
    assert after['classification_rejected']==1
    assert all(x['total_events'] is None for x in after['dashboards'])


def test_authorized_page_truncation_remains_partial(setup):
    import database
    cli,db,h,ids,eid=setup
    write(cli,h,ids[0],'brand_event','bounded-page-0001')
    with database.get_db() as con:
        metadata=con.execute('SELECT metadata FROM brand_propagation_events').fetchone()[0]
        con.executemany("INSERT INTO brand_propagation_events(event_id,title,category,metadata) VALUES(?,'tampered copy','brand_event',?)", [(f'ZZZ-{i:04}',metadata) for i in range(1001)])
    truth=cli.get('/api/experience/screen/BMP-04',headers=h).get_json()['truth']
    assert truth['dashboards'][0]['observed_events']==1
    assert truth['classification_rejected']==999
    assert all(x['total_events'] is None for x in truth['dashboards'])
