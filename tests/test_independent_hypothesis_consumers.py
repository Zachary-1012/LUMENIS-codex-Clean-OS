import io,uuid
from tests.test_independent_growth_real_app import real_app,headers,BASE,counts
from tests.test_saved_document_workflow import workspace

def test_real_session_counterevidence_blocks_stale_learning_even_after_reinstatement(real_app):
    ws=real_app;api=ws['api'];h=headers(201);sources=[]
    for text in (b'Synthetic source says ten participants.',b'Synthetic counter source says the count is unresolved.'):
        r=api.post('/api/experience/materials/documents',headers=h,data={'file':(io.BytesIO(text),'source.txt'),'request_id':'source-'+uuid.uuid4().hex},content_type='multipart/form-data')
        assert r.status_code==200,r.get_json();sources.append(r.get_json()['result']['artifact']['artifact_id'])
    r=api.post(BASE+'/generate',headers=h,json={'source_ids':sources,'business_question':'What supports the participant claim?'})
    assert r.status_code==200,r.get_json();report=r.get_json()['result'];job=report['job_id']
    hyp=report['business_analysis']['hypotheses'][0]
    refs=[r['evidence_id'] for r in report['source_brief']['records'] if r['evidence_id'] not in hyp['evidence_refs']]
    r=api.post(BASE+'/jobs/'+job+'/reviews',headers=h,json={'submission_id':str(uuid.uuid4()),'decision':'request_changes','notes':'Unknown external outcome.'})
    assert r.status_code==200,r.get_json();review=r.get_json()['review']['review_id']
    body={'job_id':job,'review_id':review,'submission_id':str(uuid.uuid4())}
    r=api.post(BASE+'/learning/candidates',headers=h,json=body)
    assert r.status_code==200,r.get_json();candidate=r.get_json()['result']['id']
    cmd={'hypothesis_id':hyp['hypothesis_id'],'disposition':'challenge','rationale':'Counter-source leaves count unresolved.','evidence_refs':refs,'request_id':'review-'+uuid.uuid4().hex,'expected_revision':None}
    url=BASE+'/jobs/'+job+'/hypotheses/review';before=counts(ws)
    assert api.post(url,headers=headers(202),json=cmd).status_code!=200
    assert api.post(url,headers=h,json={**cmd,'evidence_refs':['app_evidence_records:999999']}).status_code!=200
    assert counts(ws)==before
    r=api.post(url,headers=h,json=cmd);assert r.status_code==200,r.get_json();challenged=r.get_json()['result']
    current=api.get(BASE+'/jobs/'+job,headers=h).get_json()['result']
    assert hyp['hypothesis_id'] not in {x['hypothesis_id'] for x in current['business_analysis']['hypotheses']}
    assert not set(hyp['finding_ids']) & {x['finding_id'] for x in current['business_analysis']['ranked_findings']}
    assert api.get(BASE+'/learning/candidates/'+candidate,headers=h).status_code!=200
    before=counts(ws)
    assert api.post(url,headers=h,json={**cmd,'request_id':'stale-'+uuid.uuid4().hex,'disposition':'reject'}).status_code!=200
    assert counts(ws)==before
    r=api.post(url,headers=h,json={**cmd,'request_id':'reinstate-'+uuid.uuid4().hex,'disposition':'reinstate','expected_revision':challenged['expected_revision']})
    assert r.status_code==200,r.get_json()
    # A new review generation cannot revive a previously authorized learning dependency.
    r=api.get(BASE+'/learning/candidates/'+candidate,headers=h)
    assert r.status_code!=200,r.get_json()
    # Re-adoption needs a new independent disposition/evaluation, not a renamed request.
    re_evaluated=api.post(BASE+'/jobs/'+job+'/reviews',headers=h,json={'submission_id':str(uuid.uuid4()),'decision':'request_changes','notes':'Reassessed current hypothesis review; outcome remains unknown.'})
    assert re_evaluated.status_code==200,re_evaluated.get_json()
    new_review=re_evaluated.get_json()['review']['review_id']
    assert new_review!=review
    fresh=api.post(BASE+'/learning/candidates',headers=h,json={**body,'review_id':new_review,'submission_id':str(uuid.uuid4())})
    assert fresh.status_code==200,fresh.get_json()
    assert fresh.get_json()['result']['id']!=candidate
    with ws['repo'].transaction() as con:con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(sources[1],))
    assert api.get(BASE+'/jobs/'+job+'/hypotheses',headers=h).status_code!=200
    assert api.post(url,headers=h,json=cmd).status_code!=200
    assert api.get(BASE+'/learning/candidates/'+fresh.get_json()['result']['id'],headers=h).status_code!=200
