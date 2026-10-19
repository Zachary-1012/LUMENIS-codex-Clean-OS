"""Real current Source/SavedWork/manual counterevidence, no model or false fact."""
import uuid
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_shared_work_owner_routes import route_workspace
from tests.test_growth_research_shared import research,upload,BASE,SHARED


def report(ws):
    sources=[upload(ws,'The pilot source reports ten participants.'),upload(ws,'An independent source reports the participant count is unresolved.')]
    response=ws['api'].post(BASE+'/generate',headers=SHARED,json={'source_ids':sources,'business_question':'What supports the participant claim?'})
    assert response.status_code==200,response.get_json()
    return response.get_json()['result'],sources


def review(ws,job,hypothesis,refs,revision=None,disposition='challenge',request_id=None):
    return ws['api'].post(BASE+'/jobs/'+job+'/hypotheses/review',headers=SHARED,json={
        'hypothesis_id':hypothesis,'disposition':disposition,'rationale':'Counter-source leaves the reported measure unresolved.',
        'evidence_refs':refs,'request_id':request_id or 'review-'+uuid.uuid4().hex,'expected_revision':revision})


def test_manual_counterevidence_effective_view_history_cas_replay(research):
    original,sources=report(research);job=original['job_id'];h=original['business_analysis']['hypotheses'][0]
    counter=[r['evidence_id'] for r in original['source_brief']['records'] if r['evidence_id'] not in h['evidence_refs']]
    saved=research['api'].post(BASE+'/jobs/'+job+'/save',headers=SHARED,json={'request_id':'before-review-save','title':'Before review'})
    assert saved.status_code==200
    saved_id=saved.get_json()['result']['artifact']['artifact_id']
    request_id='manual-counter-review-1'
    response=review(research,job,h['hypothesis_id'],counter,request_id=request_id)
    assert response.status_code==200,response.get_json()
    first=response.get_json()['result'];assert first['analysis']['debate_transcript']
    assert h['hypothesis_id'] not in {x['hypothesis_id'] for x in first['analysis']['effective_hypotheses']}
    assert review(research,job,h['hypothesis_id'],counter,request_id=request_id).get_json()['result']['replayed']
    assert review(research,job,h['hypothesis_id'],counter,disposition='reject').status_code==409
    rejected=review(research,job,h['hypothesis_id'],counter,revision=first['expected_revision'],disposition='reject')
    assert rejected.status_code==200,rejected.get_json()
    rejected=rejected.get_json()['result']
    current=research['api'].get(BASE+'/jobs/'+job,headers=SHARED).get_json()['result']
    assert current['hypothesis_review_state']=='requires_reassessment'
    assert h['hypothesis_id'] not in {x['hypothesis_id'] for x in current['business_analysis']['hypotheses']}
    assert current['historical_research_analysis']['hypotheses']
    assert research['api'].get('/api/experience/saved-work/'+saved_id,headers=SHARED).status_code!=200
    # Fresh downstream admission cannot keep using rejected support.
    from lumenis.shared.reporting.source_brief_job import resolve_report_sources
    with pytest.raises(PermissionError,match='REASSESSMENT'):
        resolve_report_sources(job,actor=research['actor'],actor_id='workspace:local',expected_scope={'scope_kind':'shared_workspace','version':1})
    reinstated=review(research,job,h['hypothesis_id'],counter,revision=rejected['expected_revision'],disposition='reinstate')
    assert reinstated.status_code==200,reinstated.get_json()
    state=reinstated.get_json()['result']
    chosen=next(x for x in state['analysis']['hypotheses'] if x['hypothesis_id']==h['hypothesis_id'])
    assert chosen['status']=='reinstated' and chosen['confidence'] is None
    # Historical review remains inspectable, but current state points at the new immutable version.
    assert research['api'].get('/api/experience/saved-work/'+first['reference']['artifact_id'],headers=SHARED).status_code==200


@pytest.mark.parametrize('kind',['fake_ref','fake_hypothesis','empty_ref'])
def test_unbound_counterevidence_rejected_without_artifacts(research,kind):
    original,_=report(research);h=original['business_analysis']['hypotheses'][0]
    refs=[original['source_brief']['records'][1]['evidence_id']]
    if kind=='fake_ref':refs=['app_evidence_records:999999']
    if kind=='empty_ref':refs=[]
    hid='hypothesis_not_real' if kind=='fake_hypothesis' else h['hypothesis_id']
    with research['repo'].connection(read_only=True,wal=False) as con:before=con.execute('SELECT count(*) FROM lumenis_shared_artifacts').fetchone()[0]
    response=review(research,original['job_id'],hid,refs)
    assert response.status_code==400,response.get_json()
    with research['repo'].connection(read_only=True,wal=False) as con:assert con.execute('SELECT count(*) FROM lumenis_shared_artifacts').fetchone()[0]==before


def test_counter_source_deletion_invalidates_review_report_and_replay(research):
    original,sources=report(research);h=original['business_analysis']['hypotheses'][0]
    refs=[original['source_brief']['records'][1]['evidence_id']]
    response=review(research,original['job_id'],h['hypothesis_id'],refs,request_id='counter-deletion-review')
    assert response.status_code==200,response.get_json()
    artifact=response.get_json()['result']['reference']['artifact_id']
    with research['repo'].transaction() as con:con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(sources[1],))
    assert research['api'].get(BASE+'/jobs/'+original['job_id']+'/hypotheses',headers=SHARED).status_code!=200
    assert research['api'].get('/api/experience/saved-work/'+artifact,headers=SHARED).status_code!=200
    assert review(research,original['job_id'],h['hypothesis_id'],refs,request_id='counter-deletion-review').status_code!=200


def test_inline_reviews_cannot_bypass_manual_owner(research):
    original,sources=report(research)
    body={'source_ids':sources,'research':{'hypothesis_reviews':[]}}
    assert research['api'].post(BASE+'/generate',headers=SHARED,json=body).status_code==400
    assert research['api'].post(BASE+'/start',headers=SHARED,json={**body,'defer':True}).status_code==400


def test_generic_saved_work_cannot_erase_review_history(research):
    original,_=report(research);h=original['business_analysis']['hypotheses'][0]
    response=review(research,original['job_id'],h['hypothesis_id'],h['evidence_refs'])
    assert response.status_code==200,response.get_json()
    ref=response.get_json()['result']['reference']
    response=research['api'].post('/api/experience/saved-work/'+ref['artifact_id']+'/revise',headers=SHARED,json={
        'request_id':'illegal-review-edit','expected_sha256':ref['sha256'],'reason':'Erase manual review',
        'edits':[{'pointer':'/markdown','expected':'not the saved text','value':'erase'}]})
    assert response.status_code!=200
    item=research['api'].get('/api/experience/saved-work/'+ref['artifact_id'],headers=SHARED).get_json()['result']
    response=research['api'].post('/api/experience/saved-work/'+ref['artifact_id']+'/revise',headers=SHARED,json={
        'request_id':'illegal-valid-edit','expected_sha256':ref['sha256'],'reason':'Change review owner through generic API',
        'edits':[{'pointer':'/markdown','expected':item['document']['markdown'],'value':'Changed manual review'}]})
    assert response.status_code!=200,response.get_json()
    current=research['api'].get(BASE+'/jobs/'+original['job_id']+'/hypotheses',headers=SHARED).get_json()['result']
    assert current['reference']==ref


from tests.test_independent_growth_real_app import real_app,headers,private_source


def test_real_session_counterevidence_actor_revocation_and_read_only(real_app):
    ws=real_app;sources=[private_source(ws),private_source(ws)]
    response=ws['api'].post(BASE+'/generate',headers=headers(201),json={'source_ids':sources,'business_question':'Check conflicting source statements'})
    assert response.status_code==200,response.get_json()
    report=response.get_json()['result'];job=report['job_id'];h=report['business_analysis']['hypotheses'][0]
    body={'hypothesis_id':h['hypothesis_id'],'disposition':'reject','rationale':'The second source does not establish this proposition.',
          'evidence_refs':[report['source_brief']['records'][1]['evidence_id']],
          'request_id':'real-session-counter-review','expected_revision':None}
    url=BASE+'/jobs/'+job+'/hypotheses/review'
    assert ws['api'].post(url,headers=headers(202),json=body).status_code in (403,404)
    assert ws['api'].post(url,headers=SHARED,json=body).status_code in (401,403)
    response=ws['api'].post(url,headers=headers(201),json=body)
    assert response.status_code==200,response.get_json()
    with ws['repo'].connection(read_only=True,wal=False) as con:
        before=[con.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('daily_reports','evaluation_records','lumenis_shared_artifacts')]
    assert ws['app'].test_client().get(BASE+'/jobs/'+job+'/hypotheses',headers=headers(201)).status_code==200
    with ws['repo'].connection(read_only=True,wal=False) as con:
        assert [con.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('daily_reports','evaluation_records','lumenis_shared_artifacts')]==before
    with ws['repo'].transaction() as con:con.execute("UPDATE v4_users SET status='inactive' WHERE id=201")
    assert ws['api'].get(BASE+'/jobs/'+job+'/hypotheses',headers=headers(201)).status_code in (401,403)


def test_concurrent_manual_reviews_use_original_saved_work_cas(research):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    original,_=report(research);h=original['business_analysis']['hypotheses'][0]
    barrier=Barrier(2);app=research['api'].application
    def submit(index):
        barrier.wait()
        with app.test_client() as api:
            response=api.post(BASE+'/jobs/'+original['job_id']+'/hypotheses/review',headers=SHARED,json={
                'hypothesis_id':h['hypothesis_id'],'disposition':'challenge','rationale':'Independent review requires rechecking.',
                'evidence_refs':h['evidence_refs'],'request_id':'concurrent-review-'+str(index),'expected_revision':None})
            return response.status_code,response.get_json()
    with ThreadPoolExecutor(max_workers=2) as pool:out=list(pool.map(submit,[1,2]))
    assert sorted(x[0] for x in out)==[200,409],out
    current=research['api'].get(BASE+'/jobs/'+original['job_id']+'/hypotheses',headers=SHARED).get_json()['result']
    assert current['reference']['version']==1


def test_derived_report_preserves_counterevidence_and_parent_review_dependency(research):
    from tests.test_growth_research_shared import start,poll
    original,_=report(research);job=original['job_id'];h=original['business_analysis']['hypotheses'][0]
    response=review(research,job,h['hypothesis_id'],h['evidence_refs'],disposition='reject')
    assert response.status_code==200,response.get_json()
    original_review=response.get_json()['result']
    disposition=research['api'].post(BASE+'/jobs/'+job+'/reviews',headers=SHARED,json={
        'submission_id':str(uuid.uuid4()),'decision':'request_changes','notes':'Preserve the counterevidence and explain it.'})
    assert disposition.status_code==200,disposition.get_json()
    derived=poll(research,start(research,revision={'parent_job_id':job,'review_id':disposition.get_json()['review']['review_id']}))
    assert derived['state']=='succeeded',derived
    child=derived['result'];assert child['hypothesis_review_state']=='requires_reassessment'
    assert h['hypothesis_id'] not in {x['hypothesis_id'] for x in child['business_analysis']['hypotheses']}
    child_state=research['api'].get(BASE+'/jobs/'+child['job_id']+'/hypotheses',headers=SHARED).get_json()['result']
    assert child_state['expected_revision'] is None and child_state['inherited_reference']['reference']==original_review['reference']
    reinstated=review(research,child['job_id'],h['hypothesis_id'],h['evidence_refs'],disposition='reinstate')
    assert reinstated.status_code==200,reinstated.get_json()
    assert reinstated.get_json()['result']['analysis']['hypotheses']
    # A later parent review cannot silently update the already-derived report.
    changed=review(research,job,h['hypothesis_id'],h['evidence_refs'],revision=original_review['expected_revision'],disposition='reinstate')
    assert changed.status_code==200,changed.get_json()
    assert research['api'].get(BASE+'/jobs/'+child['job_id'],headers=SHARED).status_code==403


def test_parent_review_changed_before_child_review_commit_is_rejected(research, monkeypatch):
    from tests.test_growth_research_shared import start,poll
    from lumenis.shared.reporting import saved_work
    original,_=report(research);job=original['job_id'];h=original['business_analysis']['hypotheses'][0]
    parent_review=review(research,job,h['hypothesis_id'],h['evidence_refs'],disposition='reject').get_json()['result']
    disposition=research['api'].post(BASE+'/jobs/'+job+'/reviews',headers=SHARED,json={
        'submission_id':str(uuid.uuid4()),'decision':'request_changes','notes':'Keep the evidence dispute.'})
    child=poll(research,start(research,revision={'parent_job_id':job,'review_id':disposition.get_json()['review']['review_id']}))['result']
    original_save=saved_work.save_work
    with research['repo'].connection(read_only=True,wal=False) as con:
        before=con.execute('SELECT count(*) FROM lumenis_shared_artifacts').fetchone()[0]
    triggered=[]
    def change_parent_then_save(**kwargs):
        body=kwargs.get('payload',{}).get('research_hypothesis_review',{})
        if body.get('job_id')==child['job_id'] and not triggered:
            triggered.append(True)
            result=review(research,job,h['hypothesis_id'],h['evidence_refs'],revision=parent_review['expected_revision'],disposition='reinstate')
            assert result.status_code==200,result.get_json()
        return original_save(**kwargs)
    monkeypatch.setattr(saved_work,'save_work',change_parent_then_save)
    result=review(research,child['job_id'],h['hypothesis_id'],h['evidence_refs'],disposition='reinstate')
    assert triggered and result.status_code==403,result.get_json()
    # Only the valid parent review committed; the denied child adds no artifact.
    with research['repo'].connection(read_only=True,wal=False) as con:
        assert con.execute('SELECT count(*) FROM lumenis_shared_artifacts').fetchone()[0]==before+1
