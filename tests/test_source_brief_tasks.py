"""Real Permission and report artifact integration, in a disposable database."""
import sqlite3
import os
import subprocess
import sys
import threading
import time

import pytest

from tests.test_source_brief_job import job_db
from tests.test_source_brief_job_routes import client, GLOBAL, URL
from lumenis.shared.reporting import source_brief_tasks as tasks
from ai_task_engine import init_task_engine_db


@pytest.fixture(autouse=True)
def task_schema(client):
    init_task_engine_db()
    from ai_api import bp
    client[1].register_blueprint(bp)
    yield
    for thread in list(tasks._workers.values()):
        thread.join(10)
        assert not thread.is_alive(), "Report worker leaked from the test"


def _poll(api, task_id, headers=GLOBAL):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = api.get(URL + '/tasks/' + task_id, headers=headers)
        assert response.status_code == 200, response.get_json()
        task = response.get_json()['task']
        if task['state'] != 'running':
            return task
        time.sleep(.02)
    pytest.fail('Worker failed to complete')


def test_nonblocking_start_duplicate_resume_and_scoped_artifact(client, monkeypatch):
    api, app, path, entry, _gate = client
    focus = {**GLOBAL, 'X-Lumenis-Context-Mode': 'FOCUS', 'X-Subject-ID': entry['subject_id']}
    entered, release = threading.Event(), threading.Event()
    real = tasks.create_source_brief_job
    calls = []
    def delayed(*args, **kwargs):
        calls.append(kwargs['job_id'])
        entered.set()
        assert release.wait(5)
        return real(*args, **kwargs)
    monkeypatch.setattr(tasks, 'create_source_brief_job', delayed)
    started = api.post(URL + '/start', json={}, headers=focus)
    try:
        assert started.status_code == 202, started.get_json()
        task = started.get_json()['task']
        assert task['state'] == 'running' and task['result'] is None
        assert entered.wait(2)
        assert api.get(URL + '/tasks/' + task['task_id'], headers=GLOBAL).status_code == 403
        assert api.post(URL + '/tasks/' + task['task_id'] + '/resume', json={}, headers=GLOBAL).status_code == 403
        assert api.post(URL + '/tasks/' + task['task_id'] + '/resume', json={}, headers=focus).status_code == 202
    finally:
        release.set()
    finished = _poll(api, task['task_id'], focus)
    assert finished['state'] == 'succeeded', finished
    assert finished['result']['artifact_outcome']['source_count'] == 1
    assert finished['result']['review_status'] == 'HUMAN_PENDING'
    again = api.post(URL + '/tasks/' + task['task_id'] + '/resume', json={}, headers=focus)
    assert again.get_json()['task']['result'] == finished['result'] and len(calls) == 1
    for suffix in ['', '/steps', '/evidence']:
        assert api.get('/api/ai/tasks/' + task['task_id'] + suffix).status_code == 403
    for suffix in ['/run', '/approve', '/cancel']:
        assert api.post('/api/ai/tasks/' + task['task_id'] + suffix, json={}).status_code == 403
    assert api.get('/api/ai/trace?task_id=' + task['task_id']).status_code == 403
    assert task['task_id'] not in api.get('/api/ai/tasks').get_data(as_text=True)
    assert task['task_id'] not in api.get('/api/ai/trace').get_data(as_text=True)
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT count(*) FROM daily_reports').fetchone()[0] == 1
        assert con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0] == 3


def test_dispatch_failure_is_persisted_and_resume_reopens_same_artifact(client, monkeypatch):
    api, _app, path, _entry, _gate = client
    real = tasks.create_source_brief_job
    def fail_after_artifact(*args, **kwargs):
        real(*args, **kwargs)
        raise OSError('test failure after report save')
    monkeypatch.setattr(tasks, 'create_source_brief_job', fail_after_artifact)
    task = api.post(URL + '/start', json={}, headers=GLOBAL).get_json()['task']
    failed = _poll(api, task['task_id'])
    assert failed['state'] == 'failed' and failed['can_resume'] is True
    monkeypatch.setattr(tasks, 'create_source_brief_job', real)
    assert api.post(URL + '/tasks/' + task['task_id'] + '/resume', json={}, headers=GLOBAL).status_code == 202
    finished = _poll(api, task['task_id'])
    assert finished['state'] == 'succeeded' and finished['job_id'] == task['job_id']
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT count(*) FROM daily_reports').fetchone()[0] == 1
        assert con.execute('SELECT count(*) FROM evaluation_records').fetchone()[0] == 3


def test_revoked_workspace_prevents_final_artifact_commit_and_fresh_resume(client, monkeypatch):
    api, app, path, _entry, _gate = client
    real = tasks.create_source_brief_job
    entered, release = threading.Event(), threading.Event()
    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return real(*args, **kwargs)
    monkeypatch.setattr(tasks, 'create_source_brief_job', delayed)
    task = api.post(URL + '/start', json={}, headers=GLOBAL).get_json()['task']
    try:
        assert entered.wait(2)
        app.config['LUMENIS_OPEN_WORKSPACE'] = False
    finally:
        release.set()
    for thread in list(tasks._workers.values()):
        thread.join(5)
    assert api.post(URL + '/tasks/' + task['task_id'] + '/resume', json={}, headers=GLOBAL).status_code in {401, 403}
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT count(*) FROM daily_reports').fetchone()[0] == 0
        assert con.execute('SELECT status FROM ai_task WHERE task_id=?', (task['task_id'],)).fetchone()[0] == 'failed'


def test_dead_process_is_reported_interrupted_and_fresh_request_resumes(client, monkeypatch):
    api, _app, path, _entry, _gate = client
    # Admit a real scoped request, then crash its claimed disposable worker.
    with monkeypatch.context() as scoped:
        scoped.setattr(tasks, 'dispatch', lambda *args, **kwargs: None)
        initial = api.post(URL + '/start', json={}, headers=GLOBAL).get_json()['task']
    assert initial['state'] == 'pending'
    child = subprocess.run(
        [sys.executable, '-c', 'import os,sys; from ai_task_engine import TaskEngine; '
         'assert TaskEngine(auto_init_db=False).claim_report_task(sys.argv[1]); os._exit(23)',
         initial['task_id']], env=dict(os.environ, ZBC_DB_PATH=str(path)),
        capture_output=True, timeout=20,
    )
    assert child.returncode == 23, child.stderr.decode(errors='replace')
    interrupted = _poll(api, initial['task_id'])
    assert interrupted['state'] == 'interrupted' and interrupted['can_resume'] is True
    assert api.post(URL + '/tasks/' + initial['task_id'] + '/resume', headers=GLOBAL, json={}).status_code == 202
    finished = _poll(api, initial['task_id'])
    assert finished['state'] == 'succeeded' and finished['job_id'] == initial['job_id']


@pytest.mark.parametrize('body', [{'actor_ref': 'actor:1'}, {'resume_job_id': 'forged'}, {'limit': True}, {'business_question': ''}])
def test_client_cannot_inject_task_authority(client, body):
    api, _app, path, _entry, _gate = client
    assert api.post(URL + '/start', json=body, headers=GLOBAL).status_code == 400
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT count(*) FROM ai_task').fetchone()[0] == 0
