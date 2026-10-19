import io,uuid
from tests.test_independent_growth_real_app import real_app,headers,BASE,counts
from tests.test_saved_document_workflow import workspace

def test_counterevidence_commit_rechecks_original_source_inside_writer_transaction(real_app,monkeypatch):
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
    from lumenis.shared.reporting import saved_work
    real_save=saved_work.save_work
    def save_with_source_removed(**kwargs):
        original=kwargs.get('before_commit')
        if kwargs.get('payload',{}).get('research_hypothesis_review') is not None:
            def before_commit(con,record,document):
                con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(sources[1],))
                return original(con,record,document)
            kwargs['before_commit']=before_commit
        return real_save(**kwargs)
    monkeypatch.setattr(saved_work,'save_work',save_with_source_removed)
    response=api.post(url,headers=h,json=cmd)
    assert response.status_code!=200,response.get_json()
    assert counts(ws)==before
    assert api.get(BASE+'/jobs/'+job,headers=h).status_code==200
