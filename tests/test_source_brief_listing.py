"""Real reporting owner, signed sources, stored principals and exact evaluations."""
import json
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_bmp09_request_binding import accounts
from tests.test_source_brief_job import _source
from lumenis.shared.reporting import source_brief_job as jobs
from lumenis.shared.database.business_schema import apply_business_schema
from lumenis.shared.evaluation.recorder import init_db

@pytest.fixture
def listing(workspace):
    ws=workspace
    accounts(ws)
    from subject_registry import add_subject
    entry,_=add_subject({'domain_id':'CTH','subject_type':'company','name_en':'Listing subject','name_zh':'列表主体'})
    with ws['repo'].transaction() as con:
        apply_business_schema(con)
        _source(con,subject=entry['subject_id'])
    init_db()
    return ws

def make(ws, key='job-list-00000001', actor_id=1):
    with ws['repo'].connection() as con:
        return jobs.create_source_brief_job(con,product_id='CTH',global_scope=True,
            entity_label='All registered subjects',subject_id=None,brand_focus_id=None,
            actor_id=f'actor:{actor_id}',permission_audit_ref='permission-audit:list-test',
            trace_id='trace-list-test',job_id=key,image_actor={'id':actor_id,'role':'owner'})

def read(ws, limit=30, actor_id=1):
    return jobs.list_source_brief_jobs(actor={'id':actor_id,'role':'owner'},scope=ws['scope'],limit=limit)

def test_exact_artifact_evaluations_and_actor_filtered_before_limit(listing):
    ws=listing;made=make(ws)
    for i in range(3):make(ws,'job-other-'+str(i),2)
    result=read(ws,1)
    assert result['returned_count']==1 and result['scanned_count']==1 and result['read_complete']
    row=result['items'][0]
    assert row['artifact_hash']==made['artifact_outcome']['artifact_hash']
    assert row['evaluation_state']=='recorded' and len(row['evaluations'])==3
    assert any(e['status']=='unknown' for e in row['evaluations'])
    make(ws,'job-list-00000002')
    limited=read(ws,1)
    assert limited['has_more'] and not limited['read_complete'] and limited['state']=='PARTIAL'
    assert limited['scanned_count']==limited['returned_count']==1

def test_artifact_tamper_and_source_rejection_are_not_clean_empty(listing):
    ws=listing;make(ws)
    with ws['repo'].connection(read_only=True) as c:
        original=c.execute('SELECT summary FROM daily_reports').fetchone()[0]
    ws['repo'].execute("UPDATE daily_reports SET summary='tampered'")
    result=read(ws)
    assert result['items']==[] and result['rejected_count']==1 and not result['read_complete']
    ws['repo'].execute('UPDATE daily_reports SET summary=?',(original,))
    assert read(ws)['returned_count']==1
    ws['repo'].execute("UPDATE app_evidence_records SET outputs_json='{}'")
    result=read(ws)
    assert result['items']==[] and result['state']=='PARTIAL' and result['rejected_count']==1

def test_wrong_actor_hash_and_scope_evaluations_never_attach(listing):
    ws=listing;make(ws)
    with ws['repo'].connection(read_only=True) as c:
        records=c.execute('SELECT evaluation_id,metadata FROM evaluation_records').fetchall()
    for index,row in enumerate(records):
        meta=json.loads(row['metadata'])
        if index==0:meta['actor_id']='actor:2'
        elif index==1:meta['artifact_hash']='stale-hash'
        else:meta['scope']={**meta['scope'],'entity_label':'wrong-scope'}
        ws['repo'].execute('UPDATE evaluation_records SET metadata=? WHERE evaluation_id=?',(json.dumps(meta),row['evaluation_id']))
    row=read(ws)['items'][0]
    assert row['evaluation_state']=='partial' and row['evaluations']==[]

def test_empty_missing_storage_and_revocation_distinct(listing):
    ws=listing
    result=read(ws)
    assert result['state']=='EMPTY' and result['read_complete']
    ws['repo'].execute('DROP TABLE daily_reports')
    result=read(ws)
    assert result['state']=='UNAVAILABLE' and not result['read_complete'] and result['has_more'] is None
    ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    with pytest.raises(ValueError,match='WORK_PERMISSION_DENIED'):read(ws)

@pytest.mark.parametrize('limit',[0,101,True,'1'])
def test_invalid_limit_failclosed(listing,limit):
    with pytest.raises(ValueError,match='LIST_LIMIT_INVALID'):read(listing,limit)


def test_missing_evaluation_storage_is_unavailable(listing):
    ws=listing;make(ws)
    ws['repo'].execute('DROP TABLE evaluation_records')
    result=read(ws)
    assert result['state']=='UNAVAILABLE' and not result['read_complete']
    assert result['reason']=='SOURCE_BRIEF_EVALUATION_STORAGE_NOT_INITIALIZED'


@pytest.mark.parametrize('domain',['shared','unknown','finance','CTH',''])
def test_unsupported_domain_rejected_before_discovery(listing,domain):
    with pytest.raises(ValueError,match='WORK_SCOPE_INVALID'):
        jobs.list_source_brief_jobs(actor={'id':1,'role':'owner'},scope={**listing['scope'],'domain_id':domain})
