import io
import uuid
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_growth_research_shared import BASE, SHARED

@pytest.fixture
def real_app(workspace, monkeypatch):
    ws=workspace
    import app as module
    from lumenis.auth.models import V4_TABLES_SQL
    from lumenis.shared.database.business_schema import apply_business_schema
    from lumenis.shared.evaluation.recorder import init_db
    from ai_task_engine import init_task_engine_db
    with ws['repo'].transaction() as con:
        apply_business_schema(con)
        con.executescript(V4_TABLES_SQL)
        for n in (201,202):
            con.execute("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES(?,?,?,'owner','active')",(n,'review-'+str(n),'not-a-password'))
            con.execute("INSERT INTO v4_sessions(user_id,token,expires_at) VALUES(?,?,'2099-01-01 00:00:00')",(n,'synthetic-session-'+str(n)))
    init_db();init_task_engine_db()
    monkeypatch.setattr(module,'_pg',ws['gate'])
    monkeypatch.setitem(module.app.config,'LUMENIS_OPEN_WORKSPACE',False)
    monkeypatch.setitem(module.app.config,'TESTING',True)
    return {**ws,'app':module.app,'api':module.app.test_client()}


def headers(n):
    return {**SHARED,'Authorization':'Bearer synthetic-session-'+str(n)}


def counts(ws):
    with ws['repo'].connection(read_only=True,wal=False) as con:
        return {t:con.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('daily_reports','ai_task','evaluation_records','lumenis_shared_artifacts')}


def test_real_app_session_isolation_revocation_read_no_business_writes(real_app):
    ws=real_app
    before=counts(ws)
    assert ws['api'].get(BASE+'/taxonomy',headers=SHARED).status_code in (401,403)
    assert counts(ws)==before
    response=ws['api'].get(BASE+'/taxonomy',headers=headers(201))
    assert response.status_code==200,response.get_json()
    assert counts(ws)==before
    up=ws['api'].post('/api/experience/materials/documents',headers=headers(201),data={'file':(io.BytesIO(b'Synthetic source says ten visitors.'),'source.txt'),'request_id':'independent-source-upload'},content_type='multipart/form-data')
    assert up.status_code==200,up.get_json()
    source=up.get_json()['result']['artifact']['artifact_id']
    response=ws['api'].post(BASE+'/generate',headers=headers(201),json={'source_ids':[source],'business_question':'What did this source say?'})
    assert response.status_code==200,response.get_json()
    result=response.get_json()['result']; job=result['job_id']
    before=counts(ws)
    own=ws['api'].get(BASE+'/jobs/'+job,headers=headers(201))
    assert own.status_code==200,own.get_json()
    assert counts(ws)==before
    foreign=ws['api'].get(BASE+'/jobs/'+job,headers=headers(202))
    assert foreign.status_code in (401,403,404),foreign.get_json()
    assert counts(ws)==before
    with ws['repo'].transaction() as con:
        con.execute("UPDATE v4_users SET status='inactive' WHERE id=201")
    inactive=ws['api'].get(BASE+'/jobs/'+job,headers=headers(201))
    assert inactive.status_code in (401,403),inactive.get_json()
    assert counts(ws)==before


def private_source(ws):
    response=ws['api'].post('/api/experience/materials/documents',headers=headers(201),data={'file':(io.BytesIO(b'Private synthetic material.'),'private.txt'),'request_id':'source-'+uuid.uuid4().hex},content_type='multipart/form-data')
    assert response.status_code==200,response.get_json()
    return response.get_json()['result']['artifact']['artifact_id']


def test_foreign_source_generate_and_forged_actor_have_no_effect(real_app):
    ws=real_app
    source=private_source(ws)
    before=counts(ws)
    for h,body in [(headers(202),{'source_ids':[source]}),({**headers(202),'X-Actor-ID':'201'},{'source_ids':[source]}),(headers(202),{'source_ids':[source],'actor_id':201})]:
        result=ws['api'].post(BASE+'/generate',headers=h,json=body)
        assert result.status_code in (400,401,403,404,409,503),result.get_json()
        assert counts(ws)==before


@pytest.mark.parametrize('change', ['session','permissions','source'])
def test_fresh_get_revocation_preserves_business_tables(real_app,change):
    ws=real_app
    source=private_source(ws)
    response=ws['api'].post(BASE+'/generate',headers=headers(201),json={'source_ids':[source]})
    assert response.status_code==200,response.get_json()
    job=response.get_json()['result']['job_id']
    with ws['repo'].transaction() as con:
        if change=='session': con.execute('DELETE FROM v4_sessions WHERE user_id=201')
        elif change=='permissions': con.execute("UPDATE v4_users SET role='user' WHERE id=201")
        else: con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(source,))
    before=counts(ws)
    denied=ws['api'].get(BASE+'/jobs/'+job,headers=headers(201))
    assert denied.status_code!=200,denied.get_json()
    assert counts(ws)==before


def test_real_app_task_cancel_foreign_denied_no_job_created(real_app):
    ws=real_app
    source=private_source(ws)
    created=ws['api'].post(BASE+'/start',headers=headers(201),json={'source_ids':[source],'defer':True})
    assert created.status_code==202,created.get_json()
    task=created.get_json()['task']
    before=counts(ws)
    foreign=ws['api'].post(BASE+'/tasks/'+task['task_id']+'/cancel',headers=headers(202),json={'expected_revision':task['expected_revision']})
    assert foreign.status_code in (401,403,404),foreign.get_json()
    assert counts(ws)==before
    cancelled=ws['api'].post(BASE+'/tasks/'+task['task_id']+'/cancel',headers=headers(201),json={'expected_revision':task['expected_revision']})
    assert cancelled.status_code==200,cancelled.get_json()
    assert cancelled.get_json()['task']['state']=='cancelled'
    assert counts(ws)==before
    readback=ws['api'].get(BASE+'/tasks/'+task['task_id'],headers=headers(201))
    assert readback.status_code==200 and readback.get_json()['task']['state']=='cancelled'
    assert counts(ws)==before


def test_cancel_before_report_commit_prevents_all_derivative_writes(real_app,monkeypatch):
    import threading
    from lumenis.shared.reporting import source_brief_job as jobs, source_brief_tasks as tasks
    ws=real_app
    source=private_source(ws)
    reached,release=threading.Event(),threading.Event()
    original=jobs._persist_report
    def paused(report, **kwargs):
        reached.set()
        assert release.wait(5),'test release timeout'
        return original(report, **kwargs)
    monkeypatch.setattr(jobs,'_persist_report',paused)
    response=ws['api'].post(BASE+'/start',headers=headers(201),json={'source_ids':[source]})
    assert response.status_code==202,response.get_json()
    task=response.get_json()['task']
    try:
        assert reached.wait(5),'worker did not reach evaluation boundary'
        latest=ws['api'].get(BASE+'/tasks/'+task['task_id'],headers=headers(201))
        assert latest.status_code==200,latest.get_json()
        cancelled=ws['api'].post(BASE+'/tasks/'+task['task_id']+'/cancel',headers=headers(201),json={'expected_revision':latest.get_json()['task']['expected_revision']})
        assert cancelled.status_code==200,cancelled.get_json()
        assert cancelled.get_json()['task']['state']=='cancelled'
        before=counts(ws)
    finally:
        release.set()
        for worker in list(tasks._workers.values()):
            worker.join(5)
            assert not worker.is_alive()
    assert counts(ws)==before,'Cancelled task appended business records after cancellation committed'
