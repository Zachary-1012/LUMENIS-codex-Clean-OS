"""Isolated signed-source HTTP regressions, not live business acceptance."""
import json
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_bmp09_request_binding import accounts


@pytest.fixture
def kos(workspace):
    import kos_routes
    from subject_registry import add_subject
    ws = workspace
    ws['app'].register_blueprint(kos_routes.kos_bp)
    a = add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'KOS A','name_zh':'创作者甲'})[0]
    b = add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'KOS B','name_zh':'创作者乙'})[0]
    one, two = accounts(ws)
    ws['repo'].execute("UPDATE v4_users SET role='user'")
    for user, brand in ((1,a),(2,b)):
        for module in ('reports','brand_market_overview','subject_registry'):
            ws['repo'].execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(?,'ZBMP',?,'read',?)",(user,module,json.dumps({'brand_focus_ids':[brand['brand_focus_id']]})))
    headers = {**one,'X-Domain-Id':'BMP','X-Lumenis-Context-Mode':'FOCUS','X-Subject-ID':a['subject_id']}
    return ws['app'].test_client(), ws, a, b, headers, two


def source(ws, brand, key, author, *, likes=10, comments=0, published='2026-09-01T00:00:00Z', platform='xiaohongshu'):
    from lumenis.shared.evidence import store
    from canonical_data import CanonicalRecord, persist_canonical
    eid = store.record_evidence(source='public_http',project='LUMENIS',product='ZBMP',feature_id='SYNTHETIC_KOS_PARITY',test_name='signed-source',result='PASS',status='verified',inputs={'source_ids':[key]},outputs={'synthetic_fixture':True},domain_id='zbmp',brand_focus_id=brand['brand_focus_id'])
    with ws['repo'].transaction() as con:
        persist_canonical(con,CanonicalRecord(canonical_id='can-'+key,product_id='ZBMP',domain_id='zbmp',brand_focus_id=brand['brand_focus_id'],source_id=key,source_type='note',source_table='notes',source_platform=platform,title=key,author_id=author,author_name=author,publish_datetime=published,engagement_likes=likes,engagement_comments=comments,engagement_collects=0,engagement_shares=0,scope_status='VERIFIED',scope_evidence_ref=str(eid)))
    return eid


def body(kos, path):
    client,ws,a,b,h,two = kos
    response = client.get('/api/kos/'+path,headers=h)
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_sort_filter_and_unknown_are_real_operations(kos):
    _,ws,a,b,_,_ = kos
    source(ws,a,'low','low',likes=10)
    source(ws,a,'high','high',likes=600)
    source(ws,a,'unknown','unknown',likes=None,published='')
    source(ws,b,'private','private',likes=900)
    rows=body(kos,'list?sort_by=total_engagement')['profiles']
    assert [r['author_id'] for r in rows] == ['high','low','unknown']
    assert rows[-1]['total_engagement'] is None
    assert [r['author_id'] for r in body(kos,'list?potential=1')['profiles']] == ['high']
    assert len(body(kos,'list?lifecycle=discovered')['profiles']) == 3
    assert len(body(kos,'list?tier=UNKNOWN')['profiles']) == 3
    assert 'private' not in json.dumps(rows)
    overview=body(kos,'overview')['data']
    assert overview['by_lifecycle']['discovered'] == 3
    assert overview['potential_unknown_count'] == 1
    assert overview['potential'] is None


def test_koc_numeric_contract_missing_invalid_and_scope(kos):
    client,ws,a,b,h,two=kos
    result=body(kos,'koc-tier?interactions_24h=100&interactions_7d=500')['data']
    assert result['tier']=='gold' and result['interactions_24h']==100
    assert result['input_basis']=='user_declared' and result['external_effect']=='not_performed'
    for query in ('interactions_24h=1','interactions_24h=-1&interactions_7d=1','interactions_24h=1.5&interactions_7d=2','interactions_24h=1&interactions_24h=2&interactions_7d=3'):
        assert client.get('/api/kos/koc-tier?'+query,headers=h).status_code==400
    assert client.get('/api/kos/koc-tier?interactions_24h=1&interactions_7d=2',headers={**h,**two}).status_code==403


def test_refresh_recomputes_and_independent_read_recovers(kos):
    client,ws,a,b,h,two=kos
    source(ws,a,'before','author',likes=5)
    first=client.post('/api/kos/refresh',json={},headers=h).get_json()
    assert first['recomputed'] is True and first['persisted'] is False
    assert first['profiles'][0]['total_engagement']==5
    source(ws,a,'after','author',likes=9,published='2026-09-04T00:00:00Z')
    second=client.post('/api/kos/refresh',json={},headers=h).get_json()
    assert second['profiles'][0]['total_engagement']==14
    assert second['profiles'][0]['lifecycle_stage']=='growing'
    with ws['app'].test_client() as independent:
        assert independent.get('/api/kos/list',headers=h).get_json()['profiles']==second['profiles']
    ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    assert client.post('/api/kos/refresh',json={},headers=h).status_code>=400
    ws['repo'].execute("UPDATE v4_users SET status='active' WHERE id=1")
    assert body(kos,'list')['profiles']==second['profiles']
    assert client.post('/api/kos/refresh',json={'brand_focus_id':b['brand_focus_id']},headers=h).status_code==400


def test_profile_after_first_hundred_sources_is_not_lost(kos):
    _,ws,a,b,_,_=kos
    for index in range(105):
        source(ws,a,f'number-{index:03}',f'author-{index:03}',likes=index)
    result=body(kos,'list?sort_by=total_engagement&limit=200')
    assert result['total']==105 and result['source_count']==105
    assert result['truncated'] is False
    assert len(body(kos,'detail?author_id=author-000')['data']['source_refs'])==1


def test_invalid_sort_and_platform_filter(kos):
    client,ws,a,_,h,_=kos
    source(ws,a,'red','same',platform='xiaohongshu')
    source(ws,a,'web','same',platform='web_rss')
    assert len(body(kos,'list?platform=xiaohongshu')['profiles'])==1
    assert client.get('/api/kos/list?sort_by=secret',headers=h).status_code==400


def test_classification_retains_unknown_and_legacy_weighted_threshold(kos):
    _,ws,a,_,_,_=kos
    source(ws,a,'time1','no-time',likes=1000,published='')
    source(ws,a,'time2','no-time',likes=1000,published='2026-09-02T00:00:00Z')
    source(ws,a,'metric1','no-metric',likes=None,published='2026-01-01T00:00:00Z')
    source(ws,a,'metric2','no-metric',likes=600,published='2026-09-02T00:00:00Z')
    source(ws,a,'platform','no-rule',likes=1000,platform='web_rss')
    rows={row['author_id']:row for row in body(kos,'list')['profiles']}
    assert rows['no-time']['active_days'] is None
    assert rows['no-time']['lifecycle_stage'] is None
    assert rows['no-metric']['is_potential'] is None
    assert rows['no-metric']['lifecycle_stage'] is None
    assert rows['no-rule']['weighted_avg_engagement'] is None
    assert rows['no-rule']['classification_reasons']['is_potential']=='PLATFORM_WEIGHTS_UNAVAILABLE'
    assert all(row['kos_tier'] is None and row['kos_score'] is None for row in rows.values())
    assert len(body(kos,'list?lifecycle=UNKNOWN')['profiles'])==2
    assert len(body(kos,'list?potential=unknown')['profiles'])==2


def test_signature_rejection_prevents_false_complete_classification(kos):
    _,ws,a,_,_,_=kos
    source(ws,a,'valid','known',likes=600)
    eid=source(ws,a,'invalid','other',likes=900)
    ws['repo'].execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?",(eid,))
    result=body(kos,'list')
    assert result['rejected_count']==1
    row=result['profiles'][0]
    assert row['lifecycle_stage'] is None and row['is_potential'] is None
    assert row['classification_reasons']['lifecycle_stage']=='SOURCE_READ_INCOMPLETE'


def test_real_loopback_http_refresh_scope_revoke_and_recover(kos):
    import threading
    import urllib.error
    import urllib.request
    from werkzeug.serving import make_server
    client,ws,a,b,h,two=kos
    source(ws,a,'http-start','http-author',likes=8)
    source(ws,b,'http-private','private',likes=999)
    server=make_server('127.0.0.1',0,ws['app'])
    thread=threading.Thread(target=server.serve_forever)
    thread.start()
    receipts=[]
    def invoke(path, *, headers=None, post=False):
        req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/kos/'+path,
            headers={**(h if headers is None else headers),'Content-Type':'application/json'},
            data=b'{}' if post else None)
        try:
            with urllib.request.urlopen(req,timeout=10) as response:
                status,data=response.status,json.load(response)
        except urllib.error.HTTPError as response:
            status,data=response.code,json.load(response)
        receipts.append({'path':path,'status':status,'post':post})
        return status,data
    try:
        status,first=invoke('refresh',post=True)
        assert status==200 and first['recomputed'] and not first['persisted']
        assert first['profiles'][0]['total_engagement']==8
        source(ws,a,'http-next','http-author',likes=5,published='2026-09-03T00:00:00Z')
        status,second=invoke('refresh',post=True)
        assert status==200 and second['profiles'][0]['total_engagement']==13
        assert invoke('list')[1]['profiles']==second['profiles']
        assert invoke('list?lifecycle=growing&sort_by=note_count')[1]['returned']==1
        assert invoke('koc-tier?interactions_24h=50&interactions_7d=100')[1]['data']['tier']=='silver'
        assert invoke('koc-tier?interactions_24h=-1&interactions_7d=100')[0]==400
        assert invoke('list',headers={**h,**two})[0]==403
        assert invoke('list',headers={**h,'X-Subject-ID':b['subject_id']})[0]==403
        ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
        assert invoke('refresh',post=True)[0]>=400
        ws['repo'].execute("UPDATE v4_users SET status='active' WHERE id=1")
        status,recovered=invoke('list')
        assert status==200 and recovered['profiles']==second['profiles']
        assert 'private' not in json.dumps(recovered)
    finally:
        server.shutdown();thread.join(timeout=10);server.server_close()
        assert not thread.is_alive()
    import os
    from pathlib import Path
    if os.environ.get('LUMENIS_VALIDATION_ROOT'):
        Path(os.environ['LUMENIS_VALIDATION_ROOT'],'results/kos-http-receipts.json').write_text(json.dumps(receipts,indent=2))


def test_actor_switch_with_same_scope_is_rejected(kos, monkeypatch):
    import kos_engine
    client,ws,a,b,h,two=kos
    source(ws,a,'actor-switch','one')
    ws['repo'].execute("UPDATE v4_users SET role='owner'")
    original=kos_engine.read_scoped_profiles
    def switch(binding):
        result=original(binding)
        ws['repo'].execute("UPDATE v4_sessions SET user_id=2 WHERE token='bmp-one'")
        return result
    monkeypatch.setattr(kos_engine,'read_scoped_profiles',switch)
    response=client.get('/api/kos/list',headers=h)
    assert response.status_code==403
    assert response.get_json()['code']=='SCOPE_IDENTITY_CHANGED'
    assert 'profiles' not in response.get_json()


def test_average_sort_retains_original_platform_weights(kos):
    _,ws,a,_,_,_=kos
    source(ws,a,'weighted','comments',likes=0,comments=8)
    source(ws,a,'raw','likes',likes=12)
    rows=body(kos,'list?sort_by=avg_engagement')['profiles']
    assert [row['author_id'] for row in rows]==['comments','likes']
    assert rows[0]['avg_engagement']==rows[0]['weighted_avg_engagement']==16
    assert rows[0]['raw_avg_engagement']==8
