import io,uuid
from tests.test_independent_growth_real_app import real_app,headers,BASE,counts
from tests.test_saved_document_workflow import workspace
from tests.test_growth_learning_routes import post
from lumenis.shared.learning import contribution as owner
from lumenis.system.security import permission as p

def test_review_version_invalidates_staged_outbox_and_allows_new_chain(real_app):
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
    ws['gate'].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    pair=({**ws,'common':{'actor_id':'actor:201'}},api,h)
    obj=r.get_json()['result']
    for action in ('review','validate'):
        changed=post(pair,obj,action);assert changed.status_code==200,changed.get_json()
        obj=changed.get_json()['result']
    queued=api.post(BASE+'/learning/candidates/'+candidate+'/enqueue',headers=h,json=dict(expected_revision=obj['revision'],submission_id=str(uuid.uuid4()),receiver=owner.LOCAL_REPO))
    assert queued.status_code==200,queued.get_json()
    staged=post(pair,queued.get_json()['result'],'stage')
    assert staged.status_code==200,staged.get_json()
    staged=staged.get_json()['result']
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
    assert post(pair,staged,'receive_local').status_code!=200
    assert api.get(BASE+'/learning/outbox/'+staged['id'],headers=h).status_code!=200
    rereview=api.post(BASE+'/jobs/'+job+'/reviews',headers=h,json={'submission_id':str(uuid.uuid4()),'decision':'request_changes','notes':'Reassessed after counterevidence reinstatement; impact remains unknown.'})
    assert rereview.status_code==200,rereview.get_json()
    fresh=api.post(BASE+'/learning/candidates',headers=h,json={**body,'review_id':rereview.get_json()['review']['review_id'],'submission_id':str(uuid.uuid4())})
    assert fresh.status_code==200,fresh.get_json()
    assert fresh.get_json()['result']['id']!=candidate
    obj=fresh.get_json()['result']
    current=api.get(BASE+'/jobs/'+job,headers=h).get_json()['result']
    assert obj['origin']['hypothesis_review']==current['hypothesis_review']
    for action in ('review','validate'):
        changed=post(pair,obj,action);assert changed.status_code==200,changed.get_json()
        obj=changed.get_json()['result']
    queued=api.post(BASE+'/learning/candidates/'+obj['id']+'/enqueue',headers=h,json=dict(expected_revision=obj['revision'],submission_id=str(uuid.uuid4()),receiver=owner.LOCAL_REPO))
    assert queued.status_code==200,queued.get_json()
    out=queued.get_json()['result']
    for action in ('stage','receive_local'):
        changed=post(pair,out,action);assert changed.status_code==200,changed.get_json()
        out=changed.get_json()['result']
    assert out['transport']=='ACKNOWLEDGED' and not out['remote_delivery_proven']
    with ws['repo'].transaction() as con:con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(sources[1],))
    assert api.get(BASE+'/jobs/'+job+'/hypotheses',headers=h).status_code!=200
    assert api.post(url,headers=h,json=cmd).status_code!=200
    assert api.get(BASE+'/learning/candidates/'+fresh.get_json()['result']['id'],headers=h).status_code!=200
