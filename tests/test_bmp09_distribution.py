"""Actual disposable report/Evaluation/HTTP workflow, not business acceptance."""
import json
import pytest
from tests.test_saved_document_workflow import workspace as base_workspace
from lumenis.shared.reporting import source_brief_job as jobs
from lumenis.shared.evaluation.recorder import init_db, record_evaluation
from lumenis.shared.database.business_schema import apply_business_schema
from tests.test_bmp09_request_binding import accounts, save, PATH, GLOBAL

@pytest.fixture
def workspace(base_workspace, monkeypatch):
    ws=base_workspace
    import lumenis.shared.database as db
    import account.models
    import lumenis.auth.models
    from lumenis.shared.reporting import operator_review
    # Imported owner references must bind to this fixture, not a prior deleted DB.
    for module in (db, jobs, operator_review, account.models, lumenis.auth.models):
        monkeypatch.setattr(module,'get_repository',lambda:ws['repo'])
    import experience_runtime
    ws['app'].register_blueprint(experience_runtime.experience_bp)
    ws['one'],ws['two']=accounts(ws)
    with ws['repo'].transaction() as con: apply_business_schema(con)
    init_db()
    ws['http']=ws['app'].test_client()
    return ws

def make(ws,key='distribution-job-0001',actor=1):
    with ws['repo'].connection() as con:
        return jobs.create_source_brief_job(con,product_id='ZBMP',global_scope=True,
            entity_label='All brands',actor_id=f'actor:{actor}',image_actor={'id':actor,'role':'owner'},
            permission_audit_ref='permission-audit:isolated-distribution',trace_id='trace-distribution',job_id=key)

def view(ws,headers=None):
    r=ws['http'].get(PATH,headers=headers or ws['one'])
    assert r.status_code==200,r.get_json()
    body=r.get_json()
    first=[s for s in body['sections'] if s['type']=='table'][0]
    assert first['resource_type']=='report_evaluation_distribution'
    assert [r['status'] for r in first['rows']]==['pass','warn','fail','unknown']
    return body,body['truth']['evaluation_distribution']

def test_actual_empty_zero_and_saved_work_not_evaluation(workspace):
    ws=workspace
    _,dist=view(ws)
    assert dist['counts']==dict.fromkeys(('pass','warn','fail','unknown'),0)
    made=save(ws,actor={'id':1,'role':'owner'})
    body,dist=view(ws)
    assert body['saved_artifacts'][0]['id']==made['artifact']['artifact_id']
    assert dist['counts']==dict.fromkeys(('pass','warn','fail','unknown'),0)
    assert dist['saved_work_evaluation']=='NOT_ESTABLISHED'

def test_real_four_status_records_and_actor_scope(workspace):
    ws=workspace; made=make(ws)
    with ws['repo'].connection(read_only=True) as con:
        row=dict(con.execute('SELECT * FROM evaluation_records LIMIT 1').fetchone())
    meta=json.loads(row['metadata'])
    for state,value in [('warn',.85),('fail',.1)]:
        record_evaluation(dimension='report',metric_name='fixture_'+state,metric_value=value,
            pass_threshold=1.,warn_threshold=.8,source='isolated-test',
            evidence_ref=row['evidence_ref'],metadata=meta)
    before=records(ws)
    body,dist=view(ws)
    assert dist['counts']=={'pass':1,'warn':1,'fail':1,'unknown':2}
    assert dist['business_effect']=='NOT_ESTABLISHED'
    assert records(ws)==before
    assert body['source_brief_artifacts'][0]['artifact_hash']==made['artifact_outcome']['artifact_hash']
    _,other=view(ws,ws['two'])
    assert other['counts']==dict.fromkeys(('pass','warn','fail','unknown'),0)
    # Wrong scope cannot inherit global evaluation records.
    from subject_registry import add_subject
    entry,_=add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Scoped','name_zh':'限定'})
    _,focus=view(ws,{**ws['one'],'X-Domain-Id':'BMP','X-Lumenis-Context-Mode':'FOCUS','X-Subject-ID':entry['subject_id']})
    assert focus['counts']==dict.fromkeys(('pass','warn','fail','unknown'),0)

def test_missing_or_wrong_binding_unknown_not_pass(workspace):
    ws=workspace;make(ws)
    with ws['repo'].connection(read_only=True) as con:
        records=con.execute('SELECT evaluation_id,metadata FROM evaluation_records').fetchall()
    for row in records:
        meta=json.loads(row['metadata']);meta['artifact_hash']='stale-version'
        ws['repo'].execute('UPDATE evaluation_records SET metadata=? WHERE evaluation_id=?',(json.dumps(meta),row['evaluation_id']))
    _,dist=view(ws)
    assert dist['counts']=={'pass':0,'warn':0,'fail':0,'unknown':3}
    assert dist['missing_evaluation_count']==3

def test_missing_storage_not_empty_and_permission_revoke(workspace):
    ws=workspace;make(ws)
    ws['repo'].execute('DROP TABLE evaluation_records')
    _,dist=view(ws)
    assert all(v is None for v in dist['counts'].values())
    assert not dist['read_complete']
    ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    assert ws['http'].get(PATH,headers=ws['one']).status_code>=400

def test_tampered_artifact_is_incomplete_not_clean_zero(workspace):
    ws=workspace;make(ws)
    ws['repo'].execute("UPDATE daily_reports SET summary='altered'")
    body,dist=view(ws)
    assert not dist['read_complete']
    assert body['truth']['source_brief_reports']['rejected_count']==1
    assert body['source_brief_artifacts']==[]


def records(ws):
    with ws['repo'].connection(read_only=True) as con:
        return [tuple(row) for row in con.execute('SELECT * FROM evaluation_records ORDER BY id')]

def signed_source(ws):
    from lumenis.shared.evidence import store
    from canonical_data import CanonicalRecord, persist_canonical
    from subject_registry import add_subject
    entry,_=add_subject({'domain_id':'BMP','subject_type':'brand','name_en':'Evidence Brand','name_zh':'证据品牌'})
    with ws['repo'].transaction() as con:
        evidence=store.record_evidence(connection=con,source='public_http',project='LUMENIS',product='ZBMP',
            feature_id='DISTRIBUTION_TEST',test_name='signed_source',result='PASS',status='verified',
            inputs={'source_ids':['distribution-source']},outputs={'source_read':True},domain_id='zbmp',brand_focus_id=entry['brand_focus_id'])
        persist_canonical(con,CanonicalRecord(canonical_id='distribution-canonical',product_id='ZBMP',domain_id='zbmp',
            brand_focus_id=entry['brand_focus_id'],scope_status='VERIFIED',scope_evidence_ref=str(evidence),
            source_id='distribution-source',external_id='distribution-source',source_type='web_mention',source_platform='web',
            title='Synthetic permitted source',url='https://example.invalid/fixture',content='Synthetic data',captured_at='2026-10-18T00:00:00Z'))
    return evidence

def test_signed_source_withdrawal_and_midread_recheck(workspace,monkeypatch):
    ws=workspace;evidence=signed_source(ws);make(ws)
    _,dist=view(ws)
    assert dist['counts']=={'pass':2,'warn':0,'fail':0,'unknown':1}
    original=jobs.get_artifact_evaluations
    def withdraw(**kwargs):
        result=original(**kwargs)
        ws['repo'].execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?",(evidence,))
        return result
    monkeypatch.setattr(jobs,'get_artifact_evaluations',withdraw)
    body,dist=view(ws)
    assert body['source_brief_artifacts']==[]
    assert not dist['read_complete']
    assert dist['counts']['pass']==0

def test_page_counts_are_bounded_and_never_global_total(workspace):
    ws=workspace;make(ws);make(ws,'distribution-job-0002')
    page=jobs.list_source_brief_jobs(actor={'id':1,'role':'owner'},scope=GLOBAL,limit=1)
    assert page['has_more'] and not page['read_complete'] and page['next_cursor']
    assert len(page['items'])==1
    assert sum(page['items'][0]['evaluation_counts'].values())==3
    body,dist=view(ws)
    assert dist['population']=='returned_source_brief_page'
    assert sum(dist['counts'].values())==6
    assert dist['unit']=='artifact_bound_check'
