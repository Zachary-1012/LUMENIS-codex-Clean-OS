"""Actual Shared custody -> explicitly authorized domain import -> business HTTP."""
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_shared_work_owner_routes import route_workspace
from tests.test_growth_research_shared import research, upload, start, poll, BASE
from tests.test_business_result_continuity import make_options

@pytest.mark.parametrize('domain', ['CTH', 'BMP'])
def test_shared_source_adoption_and_parent_revocation(research, domain):
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
    with ws['repo'].transaction() as con:
        con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(source,))
    assert ws['api'].get(url,headers=headers).status_code!=200

    with pytest.raises((PermissionError,ValueError,RuntimeError,LookupError)):
        documents.adopt_shared_research_source(**args,mode='import')
