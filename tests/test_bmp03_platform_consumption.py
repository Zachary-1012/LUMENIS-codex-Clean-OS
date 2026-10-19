"""Real signed Canonical/Permission reads; no collector or remote requests."""
import json
import pytest
from tests.test_bmp09_request_binding import client, accounts
from tests.test_saved_document_workflow import workspace
PATH='/api/experience/screen/BMP-03'

def source(ws, focus, key):
    from lumenis.shared.evidence import store
    from canonical_data import CanonicalRecord,persist_canonical
    evidence=store.record_evidence(source='public_http',project='LUMENIS',product='ZBMP',feature_id='SYNTHETIC_BMP03_TEST',test_name='signed-source',result='PASS',status='verified',inputs={'source_ids':[key]},outputs={'synthetic_fixture':True},domain_id='zbmp',brand_focus_id=focus)
    with ws['repo'].transaction() as c:
        persist_canonical(c,CanonicalRecord(canonical_id='can-'+key,product_id='ZBMP',domain_id='zbmp',brand_focus_id=focus,source_id=key,source_type='web_mention',source_table='web_mentions',source_platform='web_rss',title=key,scope_status='VERIFIED',scope_evidence_ref=str(evidence)))
    return evidence

def section(response):
    assert response.status_code==200,response.get_json()
    return next(s for s in response.get_json()['sections'] if s['type']=='platforms')

@pytest.fixture
def scoped(client):
    http,ws=client
    from subject_registry import add_subject
    a=add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Platform A','name_zh':'平台甲'})[0]
    b=add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Platform B','name_zh':'平台乙'})[0]
    one,two=accounts(ws)
    ws['repo'].execute("UPDATE v4_users SET role='user'")
    for user,brand in [(1,a),(2,b)]:
        for module in ['subject_registry','brand_market_overview']:
            ws['repo'].execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(?,'ZBMP',?,'read',?)",(user,module,json.dumps({'brand_focus_ids':[brand['brand_focus_id']]})))
    h={**one,'X-Domain-Id':'BMP','X-Lumenis-Context-Mode':'FOCUS','X-Subject-ID':a['subject_id']}
    eid=source(ws,a['brand_focus_id'],'source-a');source(ws,b['brand_focus_id'],'private-b')
    return http,ws,a,b,h,two,eid

def test_bmp03_signed_platform_consumption_reopen_and_permission_revoke(scoped):
    http,ws,a,b,h,two,eid=scoped
    for _ in range(2):
        s=section(http.get(PATH,headers=h))
        assert s['consumer']=='BMP' and s['collection_owner']=='CTH'
        assert s['source_count']==1 and s['count_complete']
        assert s['items'][0]['source_references'][0]['scope_evidence']['id']==eid
        assert s['can_trigger'] is False and s['endpoint']=='' and s['source_endpoint']==''
        assert s['collection_runtime']=={'state':'UNKNOWN','reason':'COLLECTOR_RUN_SCOPE_NOT_VERIFIED'}
        assert 'private-b' not in json.dumps(s)
    assert http.get(PATH,headers={**h,**two,'X-Actor-ID':'1'}).status_code==403
    assert http.get(PATH,headers={**h,'X-Subject-ID':b['subject_id']}).status_code==403
    assert http.get(PATH,headers={'Authorization':h['Authorization']}).status_code==403
    assert http.get(PATH).status_code==401
    assert http.post(PATH,headers=h).status_code==405
    ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    assert http.get(PATH,headers=h).status_code>=400
    ws['repo'].execute("UPDATE v4_users SET status='active' WHERE id=1")
    assert section(http.get(PATH,headers=h))['source_count']==1
    ws['repo'].execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND module='brand_market_overview'")
    assert http.get(PATH,headers=h).status_code==403

def test_bmp03_signed_source_tamper_never_looks_like_empty(scoped):
    http,ws,a,b,h,two,eid=scoped
    ws['repo'].execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?",(eid,))
    s=section(http.get(PATH,headers=h))
    assert s['source_count']==0 and s['state']=='partial'
    assert s['count_complete'] is False and s['rejected_count']==1
    assert s['items']==[]

def test_bmp03_does_not_read_unscoped_collector_history(scoped,monkeypatch):
    http,ws,a,b,h,two,eid=scoped
    from lumenis.system.collector.adapters import secondary_collection
    def forbidden():raise AssertionError('UNSCOPED_COLLECTION_HISTORY_FORBIDDEN')
    monkeypatch.setattr(secondary_collection,'get_collection_surface',forbidden)
    assert section(http.get(PATH,headers=h))['source_count']==1

def test_bmp03_global_requires_real_global_authority(scoped):
    http,ws,a,b,h,two,eid=scoped
    assert http.get(PATH,headers={'Authorization':h['Authorization']}).status_code==403
    ws['repo'].execute("UPDATE v4_users SET role='owner' WHERE id=1")
    s=section(http.get(PATH,headers={'Authorization':h['Authorization']}))
    assert s['source_count']==2
    assert section(http.get(PATH,headers=h))['source_count']==1

def test_bmp03_midread_actor_switch_is_closed(scoped,monkeypatch):
    http,ws,a,b,h,two,eid=scoped
    import kos_engine
    original=kos_engine._read_scoped_canonical_material
    def switch(binding):
        data=original(binding)
        ws['repo'].execute("UPDATE v4_sessions SET user_id=2 WHERE token='bmp-one'")
        return data
    monkeypatch.setattr(kos_engine,'_read_scoped_canonical_material',switch)
    response=http.get(PATH,headers=h)
    assert response.status_code>=400
    assert 'source-a' not in json.dumps(response.get_json())

def test_bmp03_scope_exception_response_is_sanitized(scoped,monkeypatch):
    http,ws,a,b,h,two,eid=scoped
    import lumenis.auth.service
    def broken(**kwargs): raise RuntimeError('SECRET /private/database.sqlite3 token=forbidden')
    monkeypatch.setattr(lumenis.auth.service,'get_current_user',broken)
    response=http.get(PATH,headers=h)
    assert response.status_code==503
    assert response.get_json()['code']=='SCOPED_DATA_UNAVAILABLE'
    assert 'SECRET' not in response.get_data(as_text=True)
    assert 'private' not in response.get_data(as_text=True)
    assert 'trace' not in response.get_json()
