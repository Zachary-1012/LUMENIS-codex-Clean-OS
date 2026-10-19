import uuid
from tests.test_independent_growth_real_app import real_app, headers, private_source, BASE
from tests.test_saved_document_workflow import workspace
URL = BASE + '/learning'

def test_research_source_new_version_revokes_cached_learning_but_preserves_history(real_app):
    ws=real_app; api=ws['api']; h=headers(201)
    source=private_source(ws)
    r=api.post(BASE+'/generate',headers=h,json={'source_ids':[source]})
    assert r.status_code==200,r.get_json()
    job=r.get_json()['result']['job_id']
    r=api.post(BASE+'/jobs/'+job+'/reviews',headers=h,json={'submission_id':str(uuid.uuid4()),'decision':'request_changes','notes':'Synthetic review; unknown outcome.'})
    assert r.status_code==200,r.get_json()
    review=r.get_json()['review']['review_id']
    r=api.post(URL+'/candidates',headers=h,json={'job_id':job,'review_id':review,'submission_id':str(uuid.uuid4())})
    assert r.status_code==200,r.get_json()
    candidate=r.get_json()['result']['id']
    def counts():
        with ws['repo'].connection(read_only=True,wal=False) as con:
            return {t:con.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('app_evidence_records','daily_reports','ai_task','evaluation_records','lumenis_shared_artifacts','canonical_data')}
    item=api.get('/api/experience/saved-work/'+source,headers=h).get_json()['result']
    response=api.post('/api/experience/saved-work/'+source+'/revise',headers=h,json={
        'request_id':'independent-new-version-'+str(uuid.uuid4()),'expected_sha256':item['artifact']['sha256'],
        'reason':'Synthetic source notes correction','edits':[{'pointer':'/markdown',
        'expected':item['document']['markdown'],'value':item['document']['markdown']+'\nCorrected source notes.'}]})
    assert response.status_code==200,response.get_json()
    newer=response.get_json()['result']['artifact']['artifact_id']
    before=counts()
    assert api.get('/api/experience/saved-work/'+source,headers=h).status_code==200
    response=api.get(URL+'/candidates/'+candidate,headers=h)
    assert response.status_code!=200,response.get_json()
    assert counts()==before
    fresh=api.post(BASE+'/generate',headers=h,json={'source_ids':[newer]})
    assert fresh.status_code==200,fresh.get_json()
    assert fresh.get_json()['result']['source_brief']['records'][0]['source_id']==newer
