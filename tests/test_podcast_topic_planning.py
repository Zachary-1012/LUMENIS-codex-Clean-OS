import pytest
from podcast.intelligence.topic_planning import build_topic_preview
from tests.test_content_project_storage import media_store,rows
from tests.test_local_content_source_routes import local_client,SHARED_HEADERS

def card(**kw):return {'topic_id':'one','title':'自有选题','planned_date':'2026-10-17',**kw}
def test_day_week_month_missing_and_zero():
 r=build_topic_preview(as_of='2026-10-17',cards=[card(),card(topic_id='two',planned_date='2026-10-18'),card(topic_id='three',planned_date='2026-10-30')])
 p=r['saved_work_draft']['payload'];assert p['vault_projections']=={'day':['one'],'week':['one','two'],'month':['one','two','three']}
 assert p['topic_cards'][0]['score'] is None and p['topic_cards'][0]['heat']['value'] is None
 fields=p['topic_cards'][0]['signals'];r=build_topic_preview(as_of='2026-10-17',cards=[card(signals=dict.fromkeys(fields,0))]);assert r['saved_work_draft']['payload']['topic_cards'][0]['score']==0
 assert p['calendar_reference']['state']=='reference_only_not_live_verified'
def test_unknown_calendar_year_and_source_binding():
 r=build_topic_preview(as_of='2027-10-17',cards=[card()]);assert r['saved_work_draft']['payload']['calendar_reference']['state']=='year_not_covered'
 with pytest.raises(ValueError,match='SOURCE_BINDING'):build_topic_preview(as_of='2026-10-17',cards=[card(source_artifact_ids=['ART-unknown'])])
@pytest.mark.parametrize('change',[{'signals':{'demand':True}},{'planned_date':'2026-02-30'},{'signals':{'demand':float('nan')}},{'title':''},{'topic_id':[]},{'source_artifact_ids':'x'}])
def test_bad_card(change):
 with pytest.raises(ValueError):build_topic_preview(as_of='2026-10-17',cards=[card(**change)])
def test_actual_shared_guard_no_source_draft(local_client):
 client,store,_=local_client
 r=client.post('/api/experience/podcast/topics/preview',headers=SHARED_HEADERS,json={'as_of':'2026-10-17','cards':[card()]})
 assert r.status_code==200,r.get_json()
 assert r.json['saved_work_draft']['payload']['topic_cards'][0]['source_state']=='original_user_draft_no_external_source'
 assert rows(store)==[]
@pytest.mark.parametrize('extra',[{'actor_id':99},{'source_bindings':{}},{'citations':[]}])
def test_cannot_inject_identity_or_source_proof(local_client,extra):
 client,_,_=local_client;r=client.post('/api/experience/podcast/topics/preview',headers=SHARED_HEADERS,json={'as_of':'2026-10-17','cards':[card()],**extra})
 assert r.status_code==400,r.get_json()
def test_cross_origin_and_missing_source(local_client):
 client,_,_=local_client;body={'as_of':'2026-10-17','cards':[card()]}
 assert client.post('/api/experience/podcast/topics/preview',headers={**SHARED_HEADERS,'Origin':'https://evil.invalid'},json=body).status_code==403
 body['cards'][0]['source_artifact_ids']=['ART-'+'0'*16]
 assert client.post('/api/experience/podcast/topics/preview',headers=SHARED_HEADERS,json=body).status_code!=200

def test_source_owner_denial_is_not_downgraded_to_original_draft(local_client,monkeypatch):
    from lumenis.shared.reporting import saved_work
    def denied(*args,**kwargs):raise PermissionError('WORK_PERMISSION_DENIED')
    monkeypatch.setattr(saved_work,'read_committed_work',denied)
    client,_,_=local_client
    r=client.post('/api/experience/podcast/topics/preview',headers=SHARED_HEADERS,json={'as_of':'2026-10-17','cards':[card(source_artifact_ids=['ART-'+'a'*16])]})
    assert r.status_code==403,r.get_json()
    assert 'saved_work_draft' not in r.get_json()
