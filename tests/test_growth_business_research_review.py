"""Fresh manual research review versions bind real HTTP business approvals."""
import sqlite3
from tests.test_source_brief_job import job_db
from tests.test_source_brief_job_routes import client, URL
from tests.test_business_work_owner_routes import owners, prepare_business, advance, BUSINESS, PITCH


def test_reject_reinstate_requires_explicit_new_business_approval(owners):
    ws=owners
    prepared=prepare_business(ws)
    decision={'option_id':'A','reason':'Inspect bounded source statements.', 'owner':'Synthetic operator',
              'review_at':'2026-10-18T14:00:00Z'}
    chosen=advance(ws,prepared,'choose',decision,'research-choose-original')
    from tests.test_growth_business_review import manuscript_arguments
    values=manuscript_arguments({'actor':None,'scope':ws['scope']})
    values.pop('actor')
    pending=ws['api'].post(PITCH,headers=ws['headers'],json=values)
    assert pending.status_code==202,pending.get_json()
    task_id=pending.get_json()['result']['task_id']
    produced=ws['api'].post(PITCH+'/'+task_id+'/run',headers=ws['headers'],json={'scope':ws['scope']})
    assert produced.status_code==200,produced.get_json()
    job=chosen['source_report']['job_id']
    route=URL+'/jobs/'+job+'/hypotheses'
    response=ws['api'].get(route,headers=ws['headers'])
    assert response.status_code==200,response.get_json()
    current=response.get_json()['result']
    h=current['analysis']['hypotheses'][0]
    def review(disposition):
        nonlocal current
        response=ws['api'].post(route+'/review',headers=ws['headers'],json={
            'request_id':'business-research-'+disposition+'-'+str(current['expected_revision'] or 'initial')[:12],'expected_revision':current['expected_revision'],
            'hypothesis_id':h['hypothesis_id'],'disposition':disposition,
            'rationale':'Source statement is insufficient without independent measurement.',
            'evidence_refs':h['evidence_refs']})
        assert response.status_code==200,response.get_json()
        current=response.get_json()['result']
    def refused():
        with sqlite3.connect(ws['db']) as con:
            before=con.execute("SELECT count(*) FROM app_evidence_records WHERE source='cth_bmp_business'").fetchone()[0]
        response=ws['api'].post(BUSINESS+'/'+chosen['work_id']+'/choose',headers=ws['headers'],json={
            'submission_id':'research-choose-original','expected_revision':prepared['revision'],'payload':decision})
        assert response.status_code!=200,response.get_json()
        with sqlite3.connect(ws['db']) as con:
            assert con.execute("SELECT count(*) FROM app_evidence_records WHERE source='cth_bmp_business'").fetchone()[0]==before
        return response.get_json()['code']
    review('challenge')
    assert refused()=='SOURCE_BRIEF_RESEARCH_REASSESSMENT_REQUIRED'
    review('reject')
    assert refused()=='SOURCE_BRIEF_RESEARCH_REASSESSMENT_REQUIRED'
    review('reinstate')
    assert refused()=='BUSINESS_WORK_RESEARCH_REVIEW_CHANGED'
    stale_action=ws['api'].post(BUSINESS+'/'+chosen['work_id']+'/action',headers=ws['headers'],json={
        'submission_id':'research-stale-action','expected_revision':chosen['revision'],
        'payload':{'option_id':'A','task_id':task_id}})
    assert stale_action.status_code!=200
    assert stale_action.get_json()['code']=='BUSINESS_WORK_RESEARCH_REVIEW_CHANGED'
    # Reinstatement does not restore prior approval. An explicit new adoption
    # acknowledges exactly the new manual-review version, even with same options.
    adopted=advance(ws,chosen,'adopt',{'source_job_id':job,'reason':'Reviewed the reinstated pending hypothesis.',
        'question':'Which reversible action should be reviewed?', 'options':[{k:v for k,v in option.items() if k not in {'claim_type','causation'}} for option in chosen['options']],
        'decision':decision},'research-adopt-reviewed')
    assert adopted['state']=='DECIDED'
    assert adopted['adoption']['research_review_changed'] is True
    executed=advance(ws,adopted,'action',{'option_id':'A','task_id':task_id},'research-fresh-action')
    assert executed['action']['receipt']['sha256']==produced.get_json()['result']['action_receipt']['sha256']
    assert ws['api'].get(BUSINESS+'/'+chosen['work_id'],headers=ws['headers']).status_code==200
    review('challenge')
    assert ws['api'].get(BUSINESS+'/'+chosen['work_id'],headers=ws['headers']).status_code!=200


import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_shared_work_owner_routes import route_workspace
from tests.test_growth_research_shared import research, upload, start, poll, BASE
from tests.test_business_result_continuity import make_options

@pytest.mark.parametrize('domain', ['CTH', 'BMP'])
def test_shared_parent_reject_reinstate_does_not_restore_domain_approval(research, domain):
    import lumenis_app_api
    import subject_registry
    from lumenis.importer import documents
    ws=research
    ws['app'].register_blueprint(lumenis_app_api.domain_api_bp)
    source=upload(ws)
    shared=poll(ws,start(ws,source))['result']
    entity,_=subject_registry.add_subject({'domain_id':domain,'subject_type':'company' if domain=='CTH' else 'brand',
        'name_en':'Synthetic adopted business','name_zh':'合成采用业务'})
    scope={'domain_id':'cth' if domain=='CTH' else 'zbmp','global_scope':False,
        'subject_id':entity['subject_id'] if domain=='CTH' else None,
        'brand_focus_id':entity['brand_focus_id'] if domain=='BMP' else None}
    headers={'X-Domain-Id':domain,'X-Product-Id':domain,'X-Lumenis-Context-Mode':'FOCUS',
        ('X-Subject-ID' if domain=='CTH' else 'X-Brand-Focus-ID'):scope['subject_id'] or scope['brand_focus_id']}
    declaration={'source_url':None,'published_at':None,'captured_at':'2026-10-18T00:00:00Z',
        'rights':'owner-approved','rights_statement':'Self-authored synthetic test; explicit business research use.',
        'title':'Explicit synthetic adoption','intended_use':'research_reference'}
    args=dict(job_id=shared['job_id'],source_id=source,actor=ws['actor'],target_scope=scope,provenance=declaration)
    with pytest.raises(ValueError,match='EXPLICIT_RIGHTS'):
        documents.adopt_shared_research_source(**{**args,'provenance':{**declaration,'rights':'UNKNOWN'}})
    prepared=documents.adopt_shared_research_source(**args)
    with pytest.raises((PermissionError,ValueError,RuntimeError)):
        documents.adopt_shared_research_source(**args,mode='import')
    ws['gate'].grant_approval('data_import',resource=prepared['resource'],granted_by='synthetic-test-owner')
    adopted=documents.adopt_shared_research_source(**args,mode='import')
    assert adopted['research_origin']['source_id']==source
    replay=documents.adopt_shared_research_source(**args,mode='import')
    assert replay['replayed'] and replay['source_id']==adopted['source_id']
    report=ws['api'].post(BASE+'/generate',headers=headers,json={'source_ids':[adopted['source_id']]})
    assert report.status_code==200,report.get_json()
    report=report.get_json()['result']
    result=ws['api'].post('/api/experience/business-works',headers=headers,json={
        'submission_id':'adoption-business-01','source_job_id':report['job_id'],
        'kind':'venue_operations' if domain=='CTH' else 'brand_market','question':'Compare two bounded internal reviews.',
        'options':make_options(adopted['source_id'])})
    assert result.status_code==200,result.get_json()
    work=result.get_json()['result']
    url='/api/experience/business-works/'+work['work_id']
    assert ws['api'].get(url,headers=headers).status_code==200
    from tests.test_growth_research_shared import SHARED
    review_route=BASE+'/jobs/'+shared['job_id']+'/hypotheses'
    state=ws['api'].get(review_route,headers=SHARED).get_json()['result']
    hypothesis=state['analysis']['hypotheses'][0]
    for disposition in ['reject','reinstate']:
        response=ws['api'].post(review_route+'/review',headers=SHARED,json={
            'request_id':'parent-review-'+disposition,'expected_revision':state['expected_revision'],
            'hypothesis_id':hypothesis['hypothesis_id'],'disposition':disposition,
            'rationale':'Reassess the adopted source interpretation.', 'evidence_refs':hypothesis['evidence_refs']})
        assert response.status_code==200,response.get_json()
        state=response.get_json()['result']
        assert ws['api'].get(url,headers=headers).status_code!=200
    assert ws['api'].get(url,headers=headers).status_code!=200

    with pytest.raises((PermissionError,ValueError,RuntimeError,LookupError)):
        documents.adopt_shared_research_source(**args,mode='import')
