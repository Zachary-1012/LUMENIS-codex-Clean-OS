"""Composer delegates to the durable Agent owner using real server identity."""
import json
import sqlite3
from tests.test_agent_runtime_http_binding import agent_client
from tests.test_skill_http_durable_identity import skill_client


def test_composer_creates_owned_task_then_unconfigured_planner_fails_honestly(agent_client):
    api, app, path = agent_client
    import experience_runtime as runtime
    app.register_blueprint(runtime.experience_bp)
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','content','read',?)", (json.dumps({'global':True}),))
    headers={'Authorization':'Bearer fixture-session-one','X-Domain-ID':'CTH','X-Lumenis-Context-Mode':'GLOBAL_ALL'}
    response=api.post('/api/experience/ai/intent',headers=headers,json={'task':'Read authorized local information','action_type':'ANALYZE'})
    assert response.status_code==202,response.get_json()
    result=response.get_json()
    assert result['execution_kind']=='AGENT_TASK' and result['evidence_recorded'] is False
    task_id=result['task_id']
    read=api.get('/api/ai/tasks/'+task_id,headers=headers)
    assert read.status_code==200,read.get_json()
    assert read.get_json()['task']['context']['actor_id']==1
    run=api.post('/api/ai/tasks/'+task_id+'/run',headers=headers)
    assert run.status_code==200,run.get_json()
    assert run.get_json()['task']['status']=='failed'
    assert api.get('/api/ai/tasks/'+task_id,headers={'Authorization':'Bearer fixture-session-two'}).status_code==403
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE module='agent_runtime'")
    response=api.post('/api/experience/ai/intent',headers=headers,json={'task':'Read again'})
    assert response.status_code==403,response.get_json()
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM ai_task').fetchone()[0]==1


def test_composer_accepts_real_sealed_workspace_and_rejects_spoofing(agent_client):
    api, app, path = agent_client
    import experience_runtime as runtime
    app.register_blueprint(runtime.experience_bp)
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    headers={'X-Domain-ID':'CTH','X-Lumenis-Context-Mode':'GLOBAL_ALL'}
    body={'task':'Read currently authorized local capabilities'}
    response=api.post('/api/experience/ai/intent',headers=headers,json=body)
    assert response.status_code==202,response.get_json()
    identifier=response.get_json()['task_id']
    task=api.get('/api/ai/tasks/'+identifier).get_json()['task']
    assert task['context']['actor_id'] is None and task['context']['agent_runtime']['principal_ref']=='workspace:local'
    assert api.get('/api/ai/tasks/'+identifier,headers={'Authorization':'Bearer fixture-session-one'}).status_code==403
    for additions in ({'Origin':'https://foreign.example'},{'X-Actor-ID':'1'}):
        denied=api.post('/api/experience/ai/intent',headers={**headers,**additions},json=body)
        assert denied.status_code in {200,403} and not denied.get_json()['ok']
    app.config['LUMENIS_OPEN_WORKSPACE']=False
    assert api.get('/api/ai/tasks/'+identifier).status_code==403
