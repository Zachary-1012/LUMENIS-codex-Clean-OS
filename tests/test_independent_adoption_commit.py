"""Actual Shared custody -> explicitly authorized domain import -> business HTTP."""
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_shared_work_owner_routes import route_workspace
from tests.test_growth_research_shared import research, upload, start, poll, BASE
from tests.test_business_result_continuity import make_options

@pytest.mark.parametrize('domain', ['CTH', 'BMP'])
def test_parent_removed_between_approval_parse_and_commit(research, domain, monkeypatch):
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
    with ws['repo'].connection() as con:
        before = [con.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('canonical_data','app_evidence_records','lumenis_shared_artifacts')]
    original = documents._parse_approved
    def parse_then_revoke(prepared):
        result = original(prepared)
        with ws['repo'].transaction() as con:
            con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(source,))
        return result
    monkeypatch.setattr(documents,'_parse_approved',parse_then_revoke)
    with pytest.raises((PermissionError,ValueError,RuntimeError,LookupError)):
        documents.adopt_shared_research_source(**args,mode='import')
    with ws['repo'].connection() as con:
        after = [con.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('canonical_data','app_evidence_records','lumenis_shared_artifacts')]
    assert after == [before[0],before[1],before[2]-1]
