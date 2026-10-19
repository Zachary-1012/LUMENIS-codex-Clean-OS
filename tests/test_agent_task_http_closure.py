"""Existing source-bound HTTP task chain, strict local principal and no models."""
import pytest

from tests.test_source_brief_job import job_db
from tests.test_source_brief_job_routes import client, GLOBAL, URL


@pytest.mark.parametrize("question", ["分析来源数据统计", "查询数据数量", "生成报告"])
def test_source_statistics_http_submit_execute_reopen(client, question):
    api, app, path, entry, gate = client
    from ai_api import bp
    from ai_task_engine import init_task_engine_db
    init_task_engine_db()
    app.register_blueprint(bp)
    report = api.post(URL + '/generate', json={}, headers=GLOBAL)
    assert report.status_code == 200, report.get_json()
    job_id = report.get_json()['result']['job_id']
    created = api.post('/api/ai/tasks', headers=GLOBAL, json={
        'input': question, 'context': {
            'analysis_operation': 'source_statistics', 'source_brief_job_id': job_id,
        },
    })
    assert created.status_code == 200, created.get_json()
    task_id = created.get_json()['task']['task_id']
    executed = api.post('/api/ai/tasks/' + task_id + '/run', headers=GLOBAL, json={})
    assert executed.status_code == 200, executed.get_json()
    task = executed.get_json()['task']
    assert task['status'] == 'succeeded', (task.get('error'), task.get('result'))
    reopened = app.test_client().get('/api/ai/tasks/' + task_id, headers=GLOBAL)
    assert reopened.status_code == 200, reopened.get_json()
    assert reopened.get_json()['task']['result'] == task['result']


def test_source_task_notification_restart_cancel_scope_and_revocation(client):
    api, app, path, entry, gate = client
    import ai_task_engine
    from ai_api import bp
    ai_task_engine.init_task_engine_db()
    app.register_blueprint(bp)
    report = api.post(URL + '/generate', json={}, headers=GLOBAL).get_json()['result']
    body = {'input': '分析来源数据统计', 'context': {
        'analysis_operation': 'source_statistics', 'source_brief_job_id': report['job_id']}}
    task_id = api.post('/api/ai/tasks', headers=GLOBAL, json=body).get_json()['task']['task_id']
    api.post('/api/ai/tasks/' + task_id + '/run', headers=GLOBAL, json={})
    first = api.get('/api/ai/tasks/' + task_id, headers=GLOBAL).get_json()
    assert first['notification']['terminal'] is True
    assert first['notification']['return_ref'] == '/api/ai/tasks/' + task_id
    ai_task_engine.reset_task_engine()
    again = app.test_client().get('/api/ai/tasks/' + task_id, headers=GLOBAL).get_json()
    assert again['notification'] == first['notification']
    assert again['task']['result'] == first['task']['result']
    for suffix in ['/steps', '/evidence']:
        assert api.get('/api/ai/tasks/' + task_id + suffix, headers=GLOBAL).status_code == 200
    page = api.get('/api/ai/tasks', headers=GLOBAL).get_json()
    assert any(row['task_id'] == task_id for row in page['tasks'])
    assert first['notification'] in page['notifications']
    focus = {**GLOBAL, 'X-Lumenis-Context-Mode': 'FOCUS', 'X-Subject-ID': entry['subject_id']}
    assert api.get('/api/ai/tasks/' + task_id, headers=focus).status_code == 403
    assert api.get('/api/ai/tasks', headers=focus).get_json()['tasks'] == []
    pending = api.post('/api/ai/tasks', headers=GLOBAL, json=body).get_json()['task']['task_id']
    cancelled = api.post('/api/ai/tasks/' + pending + '/cancel', headers=GLOBAL, json={})
    assert cancelled.status_code == 200 and cancelled.get_json()['task']['status'] == 'cancelled'
    assert api.post('/api/ai/tasks/' + pending + '/run', headers=GLOBAL, json={}).get_json()['task']['status'] == 'cancelled'
    app.config['LUMENIS_OPEN_WORKSPACE'] = False
    assert api.get('/api/ai/tasks/' + task_id, headers=GLOBAL).status_code == 403
    assert api.get('/api/ai/tasks', headers=GLOBAL).get_json()['tasks'] == []
    assert api.get('/api/ai/tasks/' + pending + '/steps', headers=GLOBAL).status_code == 403


def test_forged_user_cannot_submit_or_read_skill(client, monkeypatch):
    api, app, path, entry, gate = client
    from ai_api import bp
    from ai_task_engine import init_task_engine_db
    init_task_engine_db()
    app.register_blueprint(bp)
    import lumenis.auth.service
    monkeypatch.setattr(lumenis.auth.service, 'get_current_user', lambda **kwargs: None)
    denied = api.post('/api/ai/tasks', json={
        'skill_id': 'zbc.skill_registry_snapshot', 'user_id': 1, 'product': 'SYSTEM'}, headers=GLOBAL)
    assert denied.status_code == 403
