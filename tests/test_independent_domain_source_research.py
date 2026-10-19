from tests.test_saved_document_workflow import workspace, _source
from lumenis.shared.reporting import source_brief_job as jobs
from lumenis.shared.reporting.media_brief import _actor_ref
from lumenis.shared.database.business_schema import apply_business_schema
from lumenis.shared.evaluation.recorder import init_db
from agent_research.source_bound import analyze_source_records


def test_authorized_domain_original_can_produce_source_findings(workspace):
    ws=workspace
    with ws['repo'].transaction() as con:
        apply_business_schema(con)
    init_db()
    import subject_registry
    entry,_=subject_registry.add_subject({'domain_id':'CTH','subject_type':'company','name_en':'Synthetic research subject','name_zh':'合成研究主体'})
    ws={**ws,'scope':{**ws['scope'],'subject_id':entry['subject_id'],'global_scope':False}}
    _,_,source=_source(ws)
    actor_id=_actor_ref(ws['actor'])
    with ws['repo'].connection(read_only=True,wal=False) as con:
        report=jobs.create_source_brief_job(con,product_id='CTH',global_scope=False,subject_id=entry['subject_id'],entity_label='Synthetic global research',actor_id=actor_id,permission_audit_ref='independent:test',trace_id='independent-domain-test',job_id='brief-independent-domain',source_ids=[source['source_id']],image_actor=ws['actor'])
    resolved=jobs.resolve_report_sources(report['job_id'],actor=ws['actor'],actor_id=actor_id,expected_scope=report['source_brief']['scope'])
    result=analyze_source_records('Original source line',resolved['records'],actor_id=actor_id,scope=resolved['scope'],dimension='business')
    assert result['ranked_findings'], result['rejected_records']
    assert not result['ranked_findings'][0]['fact_verified']
