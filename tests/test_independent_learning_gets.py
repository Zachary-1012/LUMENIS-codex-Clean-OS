import uuid
from tests.test_independent_growth_real_app import real_app, headers, private_source, BASE
from tests.test_saved_document_workflow import workspace
URL = BASE + '/learning'

def test_real_session_learning_gets_never_write_and_foreign_cannot_list(real_app):
    ws=real_app; api=ws['api']; h=headers(201)
    source=private_source(ws)
    r=api.post(BASE+'/generate',headers=h,json={'source_ids':[source]})
    assert r.status_code==200,r.get_json()
    job=r.get_json()['result']['job_id']
    r=api.post(BASE+'/jobs/'+job+'/reviews',headers=h,json={'submission_id':str(uuid.uuid4()),'decision':'request_changes','notes':'Synthetic review; unknown outcome.'})
    assert r.status_code==200,r.get_json()
    review=r.get_json()['review']['review_id']
    r=api.post(URL+'/candidates',headers=h,json={'job_id':job,'review_id':review,'submission_id':str(uuid.uuid4())})
    assert r.status_code==200,r.get_json()
    candidate=r.get_json()['result']['id']
    def counts():
        with ws['repo'].connection(read_only=True,wal=False) as con:
            return {t:con.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('app_evidence_records','daily_reports','ai_task','evaluation_records','lumenis_shared_artifacts','canonical_data')}
    before=counts()
    for suffix in ('/candidates','/candidates/'+candidate,'/outbox'):
        assert api.get(URL+suffix,headers=h).status_code==200
        response=api.get(URL+suffix,headers=headers(202))
        if suffix=='/candidates/'+candidate:
            assert response.status_code!=200
        else:
            assert candidate not in response.get_data(as_text=True)
        assert counts()==before
    with ws['repo'].transaction() as con:
        con.execute("UPDATE v4_users SET status='inactive' WHERE id=201")
    for suffix in ('/candidates','/candidates/'+candidate,'/outbox'):
        assert api.get(URL+suffix,headers=h).status_code!=200
        assert counts()==before
