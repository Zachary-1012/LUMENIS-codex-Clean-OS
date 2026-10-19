"""Real SQLite/Permission/source custody and task lifecycle, no model/network."""
import io
import json
import sqlite3
import time
import uuid
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_shared_work_owner_routes import route_workspace
from lumenis.shared.reporting import source_brief_tasks as tasks

BASE = '/api/experience/reports/source-brief'
SHARED = {'X-Lumenis-Workspace-Scope': '{"scope_kind":"shared_workspace","version":1}'}

@pytest.fixture
def research(route_workspace, monkeypatch):
    ws = route_workspace
    from lumenis.shared.database.business_schema import apply_business_schema
    from lumenis.shared.evaluation.recorder import init_db
    from ai_task_engine import init_task_engine_db
    from lumenis.shared.reporting import source_brief_job
    import lumenis.auth.service
    monkeypatch.setattr(source_brief_job, 'get_repository', lambda: ws['repo'])
    monkeypatch.setattr(lumenis.auth.service, 'get_current_user', lambda **kw: None)
    with ws['repo'].transaction() as con:
        apply_business_schema(con)
    init_db(); init_task_engine_db()
    yield ws
    for worker in list(tasks._workers.values()):
        worker.join(10)
        assert not worker.is_alive()


def upload(ws, text='Source statement: revenue 10 in 2020. 未验证事实。', request_id=None):
    response = ws['api'].post('/api/experience/materials/documents', headers=SHARED,
        data={'file': (io.BytesIO(text.encode()), 'source.txt'), 'request_id': request_id or 'upload-' + uuid.uuid4().hex},
        content_type='multipart/form-data')
    assert response.status_code == 200, response.get_json()
    return response.get_json()['result']['artifact']['artifact_id']


def start(ws, source=None, **extra):
    response = ws['api'].post(BASE+'/start', headers=SHARED,
        json={**({'source_ids':[source]} if source else {}), **extra})
    assert response.status_code == 202, response.get_json()
    return response.get_json()['task']


def poll(ws, task):
    for _ in range(250):
        response = ws['api'].get(BASE+'/tasks/'+task['task_id'],headers=SHARED)
        assert response.status_code == 200, response.get_json()
        task=response.get_json()['task']
        if task['state'] not in {'pending','running'}:
            return task
        time.sleep(.02)
    pytest.fail('research worker timeout')


def test_private_source_research_reopen_save_no_ai(research):
    source=upload(research)
    task=poll(research,start(research,source,business_question='What does this source state?',
        research={'dimension':'business','regions':['china','europe'],'languages':['zh','en','ko']}))
    assert task['state']=='succeeded',task
    report=task['result']
    assert report['job_state']=='completed'
    assert report['source_brief']['scope']=={'scope_kind':'shared_workspace','version':1}
    record=report['source_brief']['records'][0]
    assert record['canonical_id'] is None and record['rights']=='UNKNOWN'
    assert record['source_id']==source and not record['fact_verified']
    assert report['business_analysis']['ranked_findings']
    response=research['api'].get(BASE+'/jobs/'+report['job_id'],headers=SHARED)
    assert response.status_code==200 and response.get_json()['result']==report
    saved=research['api'].post(BASE+'/jobs/'+report['job_id']+'/save',headers=SHARED,
        json={'request_id':'save-research-001','title':'Research result'})
    assert saved.status_code==200,saved.get_json()
    with research['repo'].connection() as con:
        assert con.execute('SELECT COUNT(*) FROM canonical_data').fetchone()[0]==0
        counts=[con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('daily_reports','ai_task','evaluation_records')]
    research['api'].get(BASE+'/jobs/'+report['job_id'],headers=SHARED)
    with research['repo'].connection() as con:
        assert counts==[con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('daily_reports','ai_task','evaluation_records')]


def test_no_source_is_not_completed_research(research):
    task=poll(research,start(research))
    assert task['state']=='succeeded',task
    assert task['result']['job_state']=='needs_sources'
    assert task['result']['business_analysis']['ranked_findings']==[]


def test_pending_edit_cas_cancel_restore_and_filtered_pagination(research):
    ids=[]
    for i in range(5):
        task=start(research,defer=True,research={'dimension':'business' if i%2 else 'technology'})
        ids.append(task['task_id'])
    page=research['api'].get(BASE+'/tasks',headers=SHARED,query_string={'dimension':'technology','limit':1}).get_json()['result']
    seen=[page['items'][0]['task_id']]
    while page['has_more']:
        page=research['api'].get(BASE+'/tasks',headers=SHARED,query_string={'dimension':'technology','limit':1,'cursor':page['next_cursor']}).get_json()['result']
        seen += [item['task_id'] for item in page['items']]
    assert len(seen)==len(set(seen))==3 and page['total']==3
    old=task['expected_revision']
    edited=research['api'].patch(BASE+'/tasks/'+task['task_id'],headers=SHARED,
        json={'expected_revision':old,'changes':{'business_question':'Updated research goal'}})
    assert edited.status_code==200,edited.get_json()
    stale=research['api'].post(BASE+'/tasks/'+task['task_id']+'/cancel',headers=SHARED,json={'expected_revision':old})
    assert stale.status_code==409
    task=edited.get_json()['task']
    cancelled=research['api'].post(BASE+'/tasks/'+task['task_id']+'/cancel',headers=SHARED,json={'expected_revision':task['expected_revision']})
    assert cancelled.status_code==200,cancelled.get_json()
    task=cancelled.get_json()['task'];assert task['state']=='cancelled'
    restored=research['api'].post(BASE+'/tasks/'+task['task_id']+'/restore',headers=SHARED,json={'expected_revision':task['expected_revision']})
    assert restored.status_code==200 and restored.get_json()['task']['state']=='pending'


def test_revocation_deleted_source_and_anonymous_fail_closed(research):
    source=upload(research)
    task=poll(research,start(research,source))
    assert task['state']=='succeeded',task
    research['app'].config['LUMENIS_OPEN_WORKSPACE']=False
    denied=research['api'].get(BASE+'/jobs/'+task['job_id'],headers=SHARED)
    assert denied.status_code in {401,403}
    research['app'].config['LUMENIS_OPEN_WORKSPACE']=True
    with research['repo'].transaction() as con:
        con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(source,))
    response=research['api'].get(BASE+'/jobs/'+task['job_id'],headers=SHARED)
    assert response.status_code!=200


def test_review_revise_and_reference_catalog(research):
    source=upload(research)
    task=poll(research,start(research,source,business_question='Review the selected source'))
    reviewed=research['api'].post(BASE+'/jobs/'+task['job_id']+'/reviews',headers=SHARED,
        json={'submission_id':str(uuid.uuid4()),'decision':'request_changes','notes':'Explain the limitations.'})
    assert reviewed.status_code==200,reviewed.get_json()
    review=reviewed.get_json()['review']
    revised=poll(research,start(research,revision={'parent_job_id':task['job_id'],'review_id':review['review_id']}))
    assert revised['state']=='succeeded',revised
    assert revised['result']['revision']['parent_job_id']==task['job_id']
    catalog=research['api'].get(BASE+'/references',headers=SHARED).get_json()['result']
    assert catalog['total']==36
    taxonomy=research['api'].get(BASE+'/taxonomy',headers=SHARED).get_json()['result']
    assert len(taxonomy['dimensions'])==9


def test_task_duplicate_request_and_changed_payload_conflict(research):
    source = upload(research)
    request_id = str(uuid.uuid4())
    first = start(research, source, defer=True, request_id=request_id)
    second = start(research, source, defer=True, request_id=request_id)
    assert first['task_id'] == second['task_id']
    response = research['api'].post(BASE+'/start', headers=SHARED,
        json={'source_ids':[source], 'defer':True, 'request_id':request_id,
              'research':{'dimension':'business'}})
    assert response.status_code in (400,409), response.get_json()
    with research['repo'].connection(read_only=True,wal=False) as con:
        assert con.execute('SELECT count(*) FROM ai_task').fetchone()[0] == 1


def test_task_concurrent_duplicate_and_compare_swap(research):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    request_id = str(uuid.uuid4())
    barrier = Barrier(2)
    app = research['api'].application
    def create():
        barrier.wait()
        with app.test_client() as api:
            response = api.post(BASE+'/start', headers=SHARED,
                json={'defer':True, 'request_id':request_id})
            return response.status_code, response.get_json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert [r[0] for r in results] == [202,202], results
    task = results[0][1]['task']
    assert task['task_id'] == results[1][1]['task']['task_id']
    barrier = Barrier(2)
    def edit(dimension):
        barrier.wait()
        with app.test_client() as api:
            response = api.patch(BASE+'/tasks/'+task['task_id'], headers=SHARED,
                json={'expected_revision':task['expected_revision'], 'changes':{'research':{'dimension':dimension}}})
            return response.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(edit, ['business','technology']))
    assert sorted(statuses) == [200,409]


def test_private_source_new_version_invalidates_old_report(research):
    source = upload(research)
    task = poll(research, start(research, source))
    assert task['state'] == 'succeeded'
    item = research['api'].get('/api/experience/saved-work/'+source,headers=SHARED).get_json()['result']
    document = item['document']
    response = research['api'].post('/api/experience/saved-work/'+source+'/revise',headers=SHARED,
        json={'request_id':'source-revision-'+uuid.uuid4().hex, 'expected_sha256':item['artifact']['sha256'],
              'reason':'Revise source analysis notes',
              'edits':[{'pointer':'/markdown','expected':document['markdown'],
                        'value':document['markdown']+'\nRevised notes.'}]})
    assert response.status_code == 200, response.get_json()
    newer = response.get_json()['result']['artifact']['artifact_id']
    response = research['api'].get(BASE+'/jobs/'+task['result']['job_id'],headers=SHARED)
    assert response.status_code in (400,403,409), response.get_json()
    fresh = poll(research, start(research, newer))
    assert fresh['state'] == 'succeeded', fresh
    # Immutable historical custody remains viewable; current adoption is stricter.
    old = research['api'].get('/api/experience/saved-work/'+source, headers=SHARED)
    assert old.status_code == 200 and old.get_json()['result']['artifact']['artifact_id'] == source
    new_item = research['api'].get('/api/experience/saved-work/'+newer, headers=SHARED).get_json()['result']
    restored = research['api'].post('/api/experience/saved-work/'+newer+'/revise', headers=SHARED,
        json={'request_id':'source-restore-'+uuid.uuid4().hex, 'expected_sha256':new_item['artifact']['sha256'],
              'reason':'Restore historical source notes as a new version',
              'edits':[{'pointer':'/markdown','expected':new_item['document']['markdown'],'value':document['markdown']}]})
    assert restored.status_code == 200, restored.get_json()
    restored_source = restored.get_json()['result']['artifact']['artifact_id']
    assert poll(research,start(research,restored_source))['state'] == 'succeeded'



def test_completed_worker_is_not_reported_interrupted_from_stale_snapshot(research):
    source = upload(research)
    result = poll(research, start(research, source))
    assert result['state'] == 'succeeded'
    for worker in list(tasks._workers.values()):
        worker.join(10)
    stale = tasks.engine().get_report_task(result['task_id'])
    stale['status'] = 'running'
    observed = tasks.status(stale, actor=research['actor'])
    assert observed['state'] == 'succeeded'
    assert observed['result']['job_id'] == result['job_id']
