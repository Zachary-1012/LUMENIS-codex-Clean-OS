"""Production HTTP -> existing queue -> AgentLoop with actual canonical Permission."""
import json
import sqlite3

import pytest
from tests.test_skill_http_durable_identity import skill_client


@pytest.fixture
def agent_client(skill_client, monkeypatch, tmp_path):
    api, app, path = skill_client
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_KEY_RING', json.dumps({'agent-test': 'public-isolated-agent-fixture-key'}))
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID', 'agent-test')
    from lumenis.system.collector.guard import task_queue
    from agent_runtime import task_binding
    monkeypatch.setattr(task_queue, 'DEFAULT_PATH', tmp_path / 'agent-queue.sqlite')
    monkeypatch.setattr(task_binding, 'start_agent_task', lambda _: None)
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','agent_runtime','read',?)", (json.dumps({'global': True}),))
        con.execute("UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1 AND product_id='CTH' AND module='zbc.skill_registry_snapshot' AND action='read'", (json.dumps({'global': True}),))
    return skill_client


def submit(api, *, model=False):
    data = {'execution_mode': 'agent', 'input': 'Read local registered metadata',
            'domain_id': 'cth', 'scope': {'global_scope': True, 'subject_id': None, 'brand_focus_id': None},
            'actor_id': 2, 'created_by': 'admin'}
    if not model:
        data['steps'] = [{'skill_id': 'zbc.skill_registry_snapshot', 'input': {}}]
    response = api.post('/api/ai/tasks', json=data, headers={'Authorization': 'Bearer fixture-session-one'})
    assert response.status_code == 202, response.get_json()
    return response.get_json()['task']['task_id']


def test_agent_focus_selection_is_server_resolved_to_registered_bmp_scope(agent_client):
    api, app, path = agent_client
    import subject_registry
    with sqlite3.connect(path) as con:
        subject_registry.ensure_schema(con)
        con.execute("""INSERT INTO lumenis_subject_registry
            (subject_id,brand_focus_id,domain_id,subject_type,name_en,name_zh,
             name_en_norm,name_zh_norm,industry,keywords_json,status,created_at,updated_at)
            VALUES ('SUBJECT-BMP-1','BRAND-FOCUS-1','BMP','brand','Fixture Brand','Fixture Brand',
                    'fixture brand','fixture brand','retail','[]','configured','2026-10-27','2026-10-27')""")
        scope = json.dumps({'brand_focus_ids': ['BRAND-FOCUS-1']})
        con.executemany("""INSERT INTO v4_member_authorizations
            (user_id,product_id,module,action,data_scope) VALUES (1,'ZBMP',?,'read',?)""",
            [('subject_registry', scope), ('agent_runtime', scope)])
    own = {'Authorization': 'Bearer fixture-session-one',
           'X-Lumenis-Context-Mode': 'FOCUS', 'X-Domain-Id': 'BMP',
           'X-Subject-ID': 'SUBJECT-BMP-1'}
    request_id = 'ef' * 16
    body = {'execution_mode': 'agent', 'input': 'Analyze the selected brand',
            'request_id': request_id,
            'selection': {'mode': 'FOCUS', 'domain_id': 'BMP', 'subject_id': 'SUBJECT-BMP-1'}}
    response = api.post('/api/ai/tasks', headers=own, json=body)
    assert response.status_code == 202, response.get_json()
    task_id = response.get_json()['task']['task_id']
    from ai_task_engine import get_task_engine
    with app.test_request_context('/api/ai/tasks', headers=own):
        stored = get_task_engine().get_task(task_id)
        assert stored['context']['domain_id'] == 'zbmp'
        assert stored['context']['scope'] == {
            'global_scope': False, 'subject_id': None, 'brand_focus_id': 'BRAND-FOCUS-1'}
    lookup = api.get('/api/ai/tasks?request_id=' + request_id, headers=own)
    assert lookup.status_code == 200, lookup.get_json()
    assert lookup.get_json()['found'] is True
    assert lookup.get_json()['request_scope'] == {
        'domain_id': 'zbmp', 'scope': {
            'global_scope': False, 'subject_id': None, 'brand_focus_id': 'BRAND-FOCUS-1'}}
    invalid = api.post('/api/ai/tasks', headers=own, json={**body, 'domain_id': 'shared',
        'scope': {'scope_kind': 'shared_workspace', 'version': 1}})
    assert invalid.status_code == 400 and invalid.get_json()['code'] == 'AGENT_SELECTION_INVALID'
    missing = api.post('/api/ai/tasks', headers=own, json={**body, 'selection': {
        'mode': 'FOCUS', 'domain_id': 'BMP', 'subject_id': 'MISSING'}})
    assert missing.status_code == 404, missing.get_json()


def test_http_agent_loop_actual_permission_result_reopens(agent_client):
    api, app, path = agent_client
    task_id = submit(api)
    own = {'Authorization': 'Bearer fixture-session-one'}
    result = api.post(f'/api/ai/tasks/{task_id}/run', headers=own)
    assert result.status_code == 200, result.get_json()
    row = result.get_json()['task']
    assert row['status'] == 'succeeded', row
    assert 'context' not in row and 'result' not in row and 'error' not in row
    assert row['workspace_view']['status'] == 'succeeded'
    assert row['workspace_view']['input'] == 'Read local registered metadata'
    assert isinstance(row['workspace_view']['steps'], list)
    assert all(set(step) == {'label', 'status'} for step in row['workspace_view']['steps'])
    reopened = app.test_client().get(f'/api/ai/tasks/{task_id}', headers=own).get_json()
    assert reopened['task']['workspace_view'] == row['workspace_view']
    assert 'context' not in reopened['task'] and 'result' not in reopened['task']
    assert reopened['notification']['external_delivery'] is False
    steps = api.get(f'/api/ai/tasks/{task_id}/steps', headers=own).get_json()
    assert steps['count'] >= 1 and all(set(step) == {'label', 'status'} for step in steps['steps'])
    listing = api.get('/api/ai/tasks', headers=own).get_json()['tasks']
    listed = next(item for item in listing if item['task_id'] == task_id)
    assert 'context' not in listed and 'result' not in listed and 'error' not in listed
    with sqlite3.connect(path) as con:
        con.execute("""INSERT INTO ai_task_evidence
            (evidence_id,task_id,evidence_type,content,source,authenticity_score,created_at)
            VALUES (?,?,?,?,?,?,?)""",
            ('ev-sensitive', task_id, 'task', 'private prompt Authorization=Bearer abcdefghijklmnop',
             r'C:\\private\\source.txt', 0.9, '2026-10-27'))
    evidence = api.get(f'/api/ai/tasks/{task_id}/evidence', headers=own).get_json()
    assert evidence['count'] >= 1
    encoded_evidence = json.dumps(evidence, ensure_ascii=False)
    assert 'content' not in encoded_evidence and 'private prompt' not in encoded_evidence
    assert 'C:\\private' not in encoded_evidence and 'abcdefgh' not in encoded_evidence
    assert api.post(f'/api/ai/tasks/{task_id}/run', headers=own).get_json()['task']['workspace_view']['status'] == 'succeeded'
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM ai_task').fetchone()[0] == 1
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 1


def test_agent_model_planning_is_bound_but_unavailable_without_service(agent_client):
    api, app, path = agent_client
    task_id = submit(api, model=True)
    response = api.post(f'/api/ai/tasks/{task_id}/run', headers={'Authorization': 'Bearer fixture-session-one'})
    assert response.status_code == 200, response.get_json()
    row = response.get_json()['task']
    assert row['status'] == 'failed', row
    assert row['workspace_view']['error_code'] in {
        'PLANNER_GATEWAY_UNAVAILABLE', 'PLANNER_GATEWAY_RESULT_INVALID',
        'OWNED_SERVICE_EXECUTOR_NOT_BOUND', 'TASK_FAILED'}
    assert 'error' not in row and 'result' not in row and 'context' not in row


def _shared_task(api, *, headers=None, scope=None, steps=True, request_id=None,
                 goal='Create an original event card from my own wording'):
    data = {'execution_mode': 'agent', 'input': goal,
            'domain_id': 'shared', 'scope': scope or {'scope_kind': 'shared_workspace', 'version': 1}}
    if request_id is not None:
        data['request_id'] = request_id
    if steps:
        data['steps'] = [{'skill_id': 'shared.social_card', 'input': {
            'title': '寰意独立创作 · 원문', 'subtitle': 'Use my writing; no source lookup or publishing',
            'width': 800, 'height': 600}}]
    return api.post('/api/ai/tasks', json=data, headers=headers)


@pytest.fixture
def shared_agent_client(agent_client):
    api, app, path = agent_client
    with sqlite3.connect(path) as con:
        con.execute("INSERT OR REPLACE INTO skills_registry(skill_id,name,product,domain,status,version) "
                    "VALUES('shared.social_card','Local original card','SHARED',NULL,'enabled','1.0')")
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'SHARED','content','read')")
    return api, app, path


@pytest.mark.parametrize('local', [False, True])
def test_independent_shared_agent_actual_result_reopens_without_business_scope_or_model(shared_agent_client, local):
    api, app, path = shared_agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    own = None if local else {'Authorization': 'Bearer fixture-session-one'}
    created = _shared_task(api, headers=own)
    assert created.status_code == 202, created.get_json()
    task = created.get_json()['task']; task_id = task['task_id']
    assert 'context' not in task and 'result' not in task
    assert task['workspace_view']['input'] == 'Create an original event card from my own wording'
    assert task['workspace_view']['status'] in {'pending', 'running'}
    run = api.post('/api/ai/tasks/' + task_id + '/run', headers=own)
    if run.status_code != 200:
        from ai_task_engine import get_task_engine
        from agent_runtime.task_binding import authorize_task_result_read
        with app.test_request_context('/', headers=own, environ_base={'REMOTE_ADDR': '127.0.0.1'}):
            failed = get_task_engine().get_task(task_id)
            print('Shared Task failure:', failed['status'], failed.get('error'),
                  [(step.get('step_name'), step.get('error')) for step in get_task_engine().get_steps(task_id)])
            from agent_runtime.durable_adapter import DurableExecutionAdapter
            for checkpoint in DurableExecutionAdapter._db_checkpoints(get_task_engine().get_steps(task_id)):
                print('Shared checkpoint:', checkpoint.metadata,
                      [(step.get('status'), step.get('error')) for step in checkpoint.plan_snapshot.get('steps', [])])
            authorize_task_result_read(get_task_engine().get_task(task_id))
    assert run.status_code == 200, run.get_json()
    result = run.get_json()['task']
    assert result['status'] == 'succeeded', result
    from ai_task_engine import get_task_engine
    with app.test_request_context('/', headers=own, environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        raw_agent_task = get_task_engine().get_task(task_id)
        assert raw_agent_task['status'] == 'succeeded'
    assert '寰意独立创作' in result['workspace_view']['output_text']
    assert '<svg' not in result['workspace_view']['output_text']
    assert result['workspace_view']['work_refs'] == []
    assert 'context' not in result and 'result' not in result and 'error' not in result
    from ai_task_engine import reset_task_engine
    reset_task_engine()
    reopened = app.test_client().get('/api/ai/tasks/' + task_id, headers=own)
    assert reopened.status_code == 200, reopened.get_json()
    assert reopened.get_json()['task']['workspace_view'] == result['workspace_view']
    replayed = api.post('/api/ai/tasks/' + task_id + '/run', headers=own)
    assert replayed.status_code == 200 and replayed.get_json()['task']['workspace_view'] == result['workspace_view']
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 1
        saved = con.execute('SELECT product,domain,user_id FROM skill_executions').fetchone()
        assert saved == ('SHARED', None, None if local else 1)
    assert api.get('/api/ai/tasks/' + task_id, headers={'Authorization': 'Bearer fixture-session-two'}).status_code == 403


def test_shared_agent_exact_scope_revocation_and_model_plan_never_borrow_cth(shared_agent_client):
    api, app, path = shared_agent_client
    own = {'Authorization': 'Bearer fixture-session-one'}
    bad = _shared_task(api, headers=own, scope={'global_scope': True, 'subject_id': None, 'brand_focus_id': None})
    assert bad.status_code == 400
    created = _shared_task(api, headers=own, steps=False)
    assert created.status_code == 202, created.get_json()
    task_id = created.get_json()['task']['task_id']
    from ai_task_engine import get_task_engine
    from agent_runtime.task_binding import authorized_context, _planner_context, _gateway_request
    with app.test_request_context('/', headers=own):
        task = get_task_engine().get_task(task_id)
        context = _planner_context(task, authorized_context(task))
        request = _gateway_request(task_id, 'bounded planning', 'user input only', context)
        assert request.domain_id == 'shared' and request.scope == 'shared_workspace:v1'
        assert request.actor_ref == 'actor:1'
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='SHARED'")
    assert api.get('/api/ai/tasks/' + task_id, headers=own).status_code == 403
    assert api.post('/api/ai/tasks/' + task_id + '/run', headers=own).status_code == 403
    assert _shared_task(api, headers=own).status_code == 403
    with sqlite3.connect(path) as con:
        present = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='skill_executions'").fetchone()
        assert not present or con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 0


def test_shared_agent_output_commits_editable_artifact_revises_and_reopens_independently(shared_agent_client, tmp_path, monkeypatch):
    import copy
    from lumenis.shared.reporting import saved_work
    from lumenis.system.security import permission
    from lumenis.shared.content_creation.audio_visuals import visual_document_markdown
    import shared_artifacts
    api, app, path = shared_agent_client
    monkeypatch.setenv('ZBC_ARTIFACT_DIR', str(tmp_path / 'actual-artifacts'))
    shared_artifacts.ensure_artifact_table()
    with sqlite3.connect(path) as con:
        con.executemany("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'SHARED','reports',?)",
                        [('read',), ('write',)])
    own = {'Authorization': 'Bearer fixture-session-one'}
    created = _shared_task(api, headers=own)
    assert created.status_code == 202, created.get_json()
    task_id = created.get_json()['task']['task_id']
    assert api.post('/api/ai/tasks/' + task_id + '/run', headers=own).status_code == 200
    actor, scope = {'id': 1}, {'scope_kind': 'shared_workspace', 'version': 1}
    gate = permission.get_permission_gate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    route = '/api/ai/tasks/' + task_id + '/deliverable'
    prepared_response = api.post(route, headers=own, json={'mode': 'prepare'})
    assert prepared_response.status_code == 200, prepared_response.get_json()
    prepared = prepared_response.get_json()
    save_body = {'mode': 'save', 'expected_resource': prepared['resource']}
    assert api.post(route, headers=own, json=save_body).status_code == 403
    assert api.post(route, headers=own, json={**save_body, 'expected_resource': 'forged'}).status_code == 403
    assert api.post(route, headers={'Authorization': 'Bearer fixture-session-two'}, json={'mode': 'prepare'}).status_code == 403
    with app.test_request_context('/', headers=own):
        assert prepared['saved'] is False and prepared['draft']['payload']['visual_document']['layers'][2]['text'] == '寰意独立创作 · 원문'
    confirm_body = {**save_body, 'confirm': True, 'confirmed_resource': prepared['resource']}
    denied = api.post(route, headers=own, json=confirm_body)
    assert denied.status_code == 403 and denied.get_json()['code'] == 'WORK_MANUAL_AUTHORITY_REQUIRED'
    gate.grant_permission(permission.PermissionLevel.HUMAN_APPROVAL)
    assert api.post(route, headers={**own, 'Origin': 'https://outside.example'}, json=confirm_body).status_code == 403
    assert api.post(route, headers=own, json={**confirm_body, 'confirmed_resource': 'forged'}).status_code == 403
    save_body = confirm_body
    saved_response = api.post(route, headers=own, json=save_body)
    assert saved_response.status_code == 200, saved_response.get_json()
    first = saved_response.get_json()
    assert first['saved'] is True and first['state'] == 'SAVED'
    assert first['document']['task_id'] == task_id
    from agent_runtime.task_binding import _digest
    request_id = 'agent-copy-' + _digest(first['document']['payload']['task_reference'])[:40]
    saved_context = saved_work.authorize_saved_work(actor, scope, action='read')
    expected_work_id = 'WORK-' + saved_work._digest({'context': saved_context, 'request_id': request_id})[:24]
    assert expected_work_id == first['document']['work_id']
    reopened_task = api.get('/api/ai/tasks/' + task_id, headers=own)
    assert reopened_task.status_code == 200, reopened_task.get_json()
    work_refs = reopened_task.get_json()['task']['workspace_view']['work_refs']
    assert work_refs == [{'kind': first['document']['kind'], 'artifact_id': first['artifact']['artifact_id'],
                          'title': first['document']['title']}]
    assert work_refs[0]['kind'] == 'report'
    duplicate = app.test_client().post(route, headers=own, json=save_body)
    assert duplicate.status_code == 200, duplicate.get_json()
    with app.test_request_context('/', headers=own):
        first_id = first['artifact']['artifact_id']
        assert first['document']['version'] == 1
        assert duplicate.get_json()['artifact']['artifact_id'] == first_id
        payload = copy.deepcopy(first['document']['payload'])
        payload['visual_document']['layers'][2]['text'] = 'Revised by the author · 두 번째 버전'
        args = {'title': 'Revised independent visual', 'markdown': visual_document_markdown(payload['visual_document']),
            'kind': 'report', 'payload': payload, 'citations': [], 'request_id': 'author-visual-revision-0002',
            'work_id': first['document']['work_id'], 'previous_artifact_id': first_id,
            'expected_draft_digest': first['document']['draft_digest'], 'actor': actor, 'scope': scope}
        resource = saved_work.work_write_resource(**args)
        gate.grant_approval('data_export', resource=resource, granted_by='actor:1')
        second = saved_work.save_work(**args)
        second_id = second['artifact']['artifact_id']
    with app.test_request_context('/', headers=own):
        old = saved_work.reopen_work(first_id, actor=actor, scope=scope)
        new = saved_work.reopen_work(second_id, actor=actor, scope=scope)
        assert old['document']['payload']['visual_document']['layers'][2]['text'] == '寰意独立创作 · 원문'
        assert new['document']['payload']['visual_document']['layers'][2]['text'] == 'Revised by the author · 두 번째 버전'
        assert new['document']['version'] == 2 and first_id != second_id
    latest_refs = api.get('/api/ai/tasks/' + task_id, headers=own).get_json()['task']['workspace_view']['work_refs']
    assert latest_refs == [{'kind': new['document']['kind'], 'artifact_id': second_id,
                            'title': new['document']['title']}]
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='SHARED' AND module='reports'")
    assert app.test_client().post(route, headers=own, json={'mode': 'prepare'}).status_code == 403


def test_shared_agent_source_use_permission_binds_exact_current_request_without_loading_model(shared_agent_client):
    from dataclasses import replace
    from ai_task_engine import get_task_engine
    from agent_runtime import task_binding
    from agent_runtime.planner import Planner, _PLANNER_SYSTEM_PROMPT
    from lumenis.system.security import permission
    api, app, path = shared_agent_client
    own = {'Authorization': 'Bearer fixture-session-one'}
    created = _shared_task(api, headers=own, steps=False)
    assert created.status_code == 202, created.get_json()
    task_id = created.get_json()['task']['task_id']
    with app.test_request_context('/', headers=own):
        task = get_task_engine().get_task(task_id)
        current = task_binding.authorized_context(task, {'id': 1})
        context = task_binding._planner_context(task, current)
        prompt = Planner()._build_user_prompt(task['user_input'], context, 8)
        request = task_binding._gateway_request(task_id, _PLANNER_SYSTEM_PROMPT, prompt, context)
        request = replace(request, response_schema_json=json.dumps(Planner._response_schema(8),
            ensure_ascii=False, sort_keys=True, allow_nan=False))
        resource = task_binding.shared_agent_ai_resource(request, 8)
        scope = {'scope_kind': 'shared_workspace', 'version': 1}
        assert task_binding.validate_shared_agent_ai_resource(resource, actor={'id': 1}, scope=scope)
        assert not task_binding.validate_shared_agent_ai_resource(resource, actor={'id': 2}, scope=scope)
        assert not task_binding.validate_shared_agent_ai_resource(resource[:-1] + ('a' if resource[-1] != 'a' else 'b'), actor={'id': 1}, scope=scope)
        assert not task_binding.validate_shared_agent_ai_resource(resource, actor={'id': 1}, scope={**scope, 'version': 2})
        gate = permission.get_permission_gate()
        gate.grant_permission(permission.PermissionLevel.HUMAN_APPROVAL)
        gate.grant_approval('ai_call', resource=resource, granted_by='actor:1')
        decision = task_binding.validate_agent_source_use(request, actor={'id': 1})
        assert decision.allowed and decision.domain_id == 'shared' and decision.scope == 'shared_workspace:v1'
        assert decision.scope_audit_id and decision.source_audit_id
        with pytest.raises(PermissionError):
            task_binding.validate_agent_source_use(replace(request, user_payload=prompt + 'forged'), actor={'id': 1})
        get_task_engine().cancel_task(task_id)
        assert not task_binding.validate_shared_agent_ai_resource(resource, actor={'id': 1}, scope=scope)
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE product_id='SHARED' AND module='content'")
    with app.test_request_context('/', headers=own):
        assert not task_binding.validate_shared_agent_ai_resource(resource, actor={'id': 1}, scope=scope)


def test_shared_agent_deliverable_revoked_exact_approval_rolls_back_artifact(shared_agent_client, tmp_path, monkeypatch):
    from lumenis.shared.reporting import saved_work
    from lumenis.system.security import permission
    import shared_artifacts
    api, app, path = shared_agent_client
    monkeypatch.setenv('ZBC_ARTIFACT_DIR', str(tmp_path / 'revoked-artifacts'))
    shared_artifacts.ensure_artifact_table()
    with sqlite3.connect(path) as con:
        con.executemany("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'SHARED','reports',?)",
                        [('read',), ('write',)])
    own = {'Authorization': 'Bearer fixture-session-one'}
    task_id = _shared_task(api, headers=own).get_json()['task']['task_id']
    assert api.post('/api/ai/tasks/' + task_id + '/run', headers=own).status_code == 200
    route = '/api/ai/tasks/' + task_id + '/deliverable'
    prepared = api.post(route, headers=own, json={'mode': 'prepare'}).get_json()
    gate = permission.get_permission_gate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    approval = gate.grant_approval('data_export', resource=prepared['resource'], granted_by='actor:1')
    original = saved_work.save_work
    def revoke_before_write(**kwargs):
        assert gate.revoke_approval(approval)
        return original(**kwargs)
    monkeypatch.setattr(saved_work, 'save_work', revoke_before_write)
    response = api.post(route, headers=own, json={'mode': 'save', 'expected_resource': prepared['resource']})
    assert response.status_code == 403, response.get_json()
    assert response.get_json()['code'] == 'AGENT_DELIVERABLE_APPROVAL_CHANGED'
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM lumenis_shared_artifacts').fetchone()[0] == 0
    assert not list((tmp_path / 'revoked-artifacts').rglob('*.json'))


def test_shared_task_derived_memory_http_revisions_forget_and_permission_remain_local(shared_agent_client):
    from lumenis.shared.database import migrations
    api, app, path = shared_agent_client
    assert migrations.migrate()
    own = {'Authorization': 'Bearer fixture-session-one'}
    created = _shared_task(api, headers=own)
    assert created.status_code == 202, created.get_json()
    url = '/api/ai/tasks/' + created.get_json()['task']['task_id'] + '/memory'
    body = {'key': 'writing', 'value': {'text': 'Complete user writing · 원문'}, 'expected_revision': 0}
    assert api.post(url, headers=own, json=body).status_code == 403
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'SHARED','content','write')")
    saved = api.post(url, headers=own, json=body)
    assert saved.status_code == 200, saved.get_json()
    assert saved.get_json()['record']['metadata']['memory_revision'] == 1
    reopened = app.test_client().get(url + '?key=writing', headers=own)
    assert reopened.get_json()['records'][0]['value'] == body['value']
    assert api.post(url, headers=own, json={**body, 'value': {'text': 'explicit correction'}}).status_code == 409
    assert api.delete(url, headers=own, json={'key': 'writing', 'expected_revision': 1}).status_code == 200
    assert app.test_client().get(url + '?key=writing', headers=own).get_json()['records'] == []
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE product_id='SHARED' AND module='content'")
    assert api.get(url, headers=own).status_code == 403


def test_agent_cancel_cross_actor_and_scope_revocation(agent_client):
    api, app, path = agent_client
    task_id = submit(api)
    other = {'Authorization': 'Bearer fixture-session-two'}
    assert api.post(f'/api/ai/tasks/{task_id}/run', headers=other).status_code == 403
    assert api.post(f'/api/ai/tasks/{task_id}/cancel', headers=other).status_code == 403
    from ai_task_engine import get_task_engine
    with app.test_request_context('/', headers={'Authorization': 'Bearer fixture-session-one'}):
        assert get_task_engine().get_task(task_id)['status'] == 'pending'
    own = {'Authorization': 'Bearer fixture-session-one'}
    assert api.post(f'/api/ai/tasks/{task_id}/cancel', headers=own).status_code == 200
    cancelled = api.post(f'/api/ai/tasks/{task_id}/run', headers=own).get_json()['task']
    assert cancelled['status'] == 'cancelled' and cancelled['workspace_view']['can_cancel'] is False
    assert 'context' not in cancelled and 'result' not in cancelled
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE module='agent_runtime'")
    assert api.post(f'/api/ai/tasks/{task_id}/cancel', headers=own).status_code == 403
    assert api.get(f'/api/ai/tasks/{task_id}', headers=own).status_code == 403
    assert api.get('/api/ai/tasks', headers=own).get_json()['tasks'] == []


def test_agent_task_request_idempotency_and_exact_read_only_recovery(shared_agent_client, monkeypatch):
    api, _app, _path = shared_agent_client
    own = {'Authorization': 'Bearer fixture-session-one'}
    request_id = 'ab' * 16
    from agent_runtime import task_binding
    dispatches = []
    monkeypatch.setattr(task_binding, 'start_agent_task', lambda task_id: dispatches.append(task_id))

    first = _shared_task(api, headers=own, request_id=request_id)
    assert first.status_code == 202, first.get_json()
    first_body = first.get_json()
    task_id = first_body['task']['task_id']
    assert first_body['request_id'] == request_id
    assert first_body['task']['request_id'] == request_id
    assert first_body['reused'] is False
    assert first_body['request_scope'] == {
        'domain_id': 'shared', 'scope': {'scope_kind': 'shared_workspace', 'version': 1}}
    assert first_body['task']['workspace_view']['status'] == 'pending'
    assert first_body['task']['workspace_view']['can_resume'] is True
    assert dispatches == [task_id]

    replay = _shared_task(api, headers=own, request_id=request_id)
    assert replay.status_code == 200, replay.get_json()
    assert replay.get_json()['reused'] is True
    assert replay.get_json()['task']['task_id'] == task_id
    assert replay.get_json()['task']['request_id'] == request_id
    assert dispatches == [task_id]

    recovered = api.get('/api/ai/tasks?request_id=' + request_id, headers=own)
    assert recovered.status_code == 200, recovered.get_json()
    assert recovered.get_json()['found'] is True
    assert recovered.get_json()['request_id'] == request_id
    assert recovered.get_json()['task']['task_id'] == task_id
    assert recovered.get_json()['task']['request_id'] == request_id
    assert recovered.get_json()['request_scope'] == first_body['request_scope']
    missing = api.get('/api/ai/tasks?request_id=' + ('cd' * 16), headers=own)
    assert missing.status_code == 200 and missing.get_json() == {
        'ok': True, 'request_id': 'cd' * 16, 'found': False}

    changed = _shared_task(api, headers=own, request_id=request_id,
                           goal='Create a different event card')
    assert changed.status_code == 409
    assert changed.get_json() == {
        'ok': False, 'code': 'AGENT_TASK_REQUEST_ID_CONFLICT'}
    assert dispatches == [task_id]


def test_agent_task_result_revocation_keeps_safe_status_and_cancel(agent_client):
    api, _app, path = agent_client
    own = {'Authorization': 'Bearer fixture-session-one'}
    task_id = submit(api)
    completed = api.post(f'/api/ai/tasks/{task_id}/run', headers=own)
    assert completed.status_code == 200, completed.get_json()

    # Keep the parent Task scope permission and revoke only the child Skill
    # result permission; exercise cancellation through the isolated fixture DB.
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='CTH' "
                    "AND module='zbc.skill_registry_snapshot' AND action='read'")
        con.execute("UPDATE ai_task SET status='running' WHERE task_id=?", (task_id,))

    readback = api.get(f'/api/ai/tasks/{task_id}', headers=own)
    assert readback.status_code == 200, readback.get_json()
    task = readback.get_json()['task']
    view = task['workspace_view']
    assert view['status'] == 'running'
    assert view['result_access_state'] == 'RESTRICTED'
    assert view['can_cancel'] is True and view['can_resume'] is False
    assert view['output_text'] is None and view['work_refs'] == [] and view['steps'] == []
    assert 'result' not in task and 'context' not in task and 'error' not in task

    cancelled = api.post(f'/api/ai/tasks/{task_id}/cancel', headers=own)
    assert cancelled.status_code == 200, cancelled.get_json()
    cancelled_task = cancelled.get_json()['task']
    assert cancelled_task['status'] == 'cancelled'
    assert cancelled_task['workspace_view']['result_access_state'] == 'RESTRICTED'
    assert cancelled_task['workspace_view']['output_text'] is None
    assert cancelled_task['workspace_view']['work_refs'] == []
    assert cancelled_task['workspace_view']['steps'] == []
    assert 'result' not in cancelled_task and 'context' not in cancelled_task


def test_registered_skilljob_owner_can_cancel_and_read_status_after_result_revocation(agent_client, monkeypatch):
    api, _app, path = agent_client
    own = {'Authorization': 'Bearer fixture-session-one'}
    from lumenis.shared.agents.skills import execution
    monkeypatch.setattr(execution, 'start_registered_skill_job', lambda _execution_id: None)
    submitted = api.post('/api/ai/tasks', headers=own, json={
        'skill_id': 'zbc.skill_registry_snapshot',
        'task': 'Read local registered metadata', 'input': {},
        'action_type': 'READ', 'product': 'CTH', 'background': True,
    })
    assert submitted.status_code == 202, submitted.get_json()
    task_id = submitted.get_json()['execution_id']
    assert task_id.startswith('skilljob_')

    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='CTH' "
                    "AND module='zbc.skill_registry_snapshot' AND action='read'")
    cancelled = api.post(f'/api/ai/tasks/{task_id}/cancel', headers=own)
    assert cancelled.status_code == 200, cancelled.get_json()
    task = cancelled.get_json()['task']
    assert task['task_id'] == task_id and task['status'] == 'cancelled'
    assert task['workspace_view']['result_access_state'] == 'RESTRICTED'
    assert task['workspace_view']['output_text'] is None
    assert task['workspace_view']['error_code'] is None
    assert 'result' not in task and 'output_json' not in task

    reopened = api.get(f'/api/ai/tasks/{task_id}', headers=own)
    assert reopened.status_code == 200, reopened.get_json()
    assert reopened.get_json()['task']['status'] == 'cancelled'
    assert reopened.get_json()['task']['workspace_view']['result_access_state'] == 'RESTRICTED'
    assert reopened.get_json()['task']['workspace_view']['output_text'] is None


def test_local_principal_actual_queue_result_and_identity_boundaries(agent_client):
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    data = {'execution_mode': 'agent', 'input': 'Read local tools', 'domain_id': 'cth',
            'scope': {'global_scope': True, 'subject_id': None, 'brand_focus_id': None},
            'steps': [{'skill_id': 'zbc.skill_registry_snapshot', 'input': {}}]}
    rejected = api.post('/api/ai/tasks', json=data, headers={'Origin': 'https://external.example'})
    assert rejected.status_code == 403
    rejected = api.post('/api/ai/tasks', json=data, headers={'X-Actor-ID': '1'})
    assert rejected.status_code == 403
    created = api.post('/api/ai/tasks', json={**data, 'actor_id': 1, 'principal_ref': 'actor:1'})
    assert created.status_code == 202, created.get_json()
    task_id = created.get_json()['task']['task_id']
    assert 'context' not in created.get_json()['task']
    assert api.get(f'/api/ai/tasks/{task_id}', headers={'Authorization': 'Bearer fixture-session-one'}).status_code == 403
    account_task = submit(api)
    assert api.get(f'/api/ai/tasks/{account_task}').status_code == 403
    result = api.post(f'/api/ai/tasks/{task_id}/run')
    assert result.status_code == 200, result.get_json()
    assert result.get_json()['task']['status'] == 'succeeded', result.get_json()
    from ai_task_engine import reset_task_engine
    reset_task_engine()
    reopened = app.test_client().get(f'/api/ai/tasks/{task_id}').get_json()['task']
    assert reopened['status'] == 'succeeded' and 'context' not in reopened
    assert api.post(f'/api/ai/tasks/{task_id}/run').get_json()['task']['status'] == 'succeeded'
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT user_id FROM skill_executions').fetchall() == [(None,)]
    app.config['LUMENIS_OPEN_WORKSPACE'] = False
    assert api.get(f'/api/ai/tasks/{task_id}').status_code == 403


from agent_runtime.task_binding import start_agent_task as _real_start_agent_task


def _submit_local(api):
    response = api.post('/api/ai/tasks', json={'execution_mode': 'agent', 'input': 'Read local tools',
        'domain_id': 'cth', 'scope': {'global_scope': True, 'subject_id': None, 'brand_focus_id': None},
        'steps': [{'skill_id': 'zbc.skill_registry_snapshot', 'input': {}}]})
    assert response.status_code == 202, response.get_json()
    return response.get_json()['task']['task_id']


def test_local_background_thread_keeps_live_server_request_identity(agent_client):
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    task_id = _submit_local(api)
    with app.test_request_context('/api/ai/tasks', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        thread = _real_start_agent_task(task_id)
    thread.join(timeout=10)
    assert not thread.is_alive()
    result = api.get(f'/api/ai/tasks/{task_id}').get_json()['task']
    assert result['status'] == 'succeeded', result


def test_local_process_crash_after_tool_checkpoint_resumes_without_duplicate_effect(agent_client):
    import os
    import subprocess
    import sys
    from lumenis.system.collector.guard import task_queue
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    task_id = _submit_local(api)
    code = '''import os,sys
from flask import Flask
from lumenis.system.security import permission
permission._TESTING_BYPASS_ENABLED=False
from lumenis.system.collector.guard import task_queue
task_queue.DEFAULT_PATH=sys.argv[2]
from agent_runtime.durable_adapter import DurableExecutionAdapter
DurableExecutionAdapter.finalize_task=lambda *args,**kwargs: os._exit(23)
from ai_api import bp
app=Flask(__name__); app.config['LUMENIS_OPEN_WORKSPACE']=True; app.register_blueprint(bp)
r=app.test_client().post('/api/ai/tasks/'+sys.argv[1]+'/run')
print(r.status_code,r.get_json(),flush=True)
'''
    env = dict(os.environ)
    env.pop('PERMISSION_GATE_TESTING', None)
    child = subprocess.run([sys.executable, '-c', code, task_id, str(task_queue.DEFAULT_PATH)],
        env=env, text=True, capture_output=True, timeout=30)
    assert child.returncode == 23, child.stdout + child.stderr
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT status FROM ai_task WHERE task_id=?', (task_id,)).fetchone()[0] == 'running'
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 1
    with sqlite3.connect(task_queue.DEFAULT_PATH) as con:
        con.execute('UPDATE tasks SET last_heartbeat_at=0')
    recovered_view = api.get(f'/api/ai/tasks/{task_id}').get_json()['task']['workspace_view']
    assert recovered_view['can_resume'] is True, recovered_view
    result = app.test_client().post(f'/api/ai/tasks/{task_id}/run')
    assert result.status_code == 200, result.get_json()
    with sqlite3.connect(task_queue.DEFAULT_PATH) as con:
        con.execute('UPDATE tasks SET scheduled_at=0')
    result = app.test_client().post(f'/api/ai/tasks/{task_id}/run')
    assert result.get_json()['task']['status'] == 'succeeded', result.get_json()
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM skill_executions').fetchone()[0] == 1


def test_local_workspace_copy_and_formed_identity_substitution_are_denied(agent_client, monkeypatch, tmp_path):
    import shutil
    from agent_capability.formation import context_identity, FormationError
    from agent_runtime.task_binding import authorized_context
    from ai_task_engine import get_task_engine, reset_task_engine
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    task_id = _submit_local(api)
    with app.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        context = authorized_context(get_task_engine().get_task(task_id))
        identity = context_identity(context)
        assert identity
        with pytest.raises(FormationError):
            context_identity({**context, 'actor': {'principal_kind': 'local_workspace', 'principal_ref': 'workspace:local'}})
        altered = {**context, 'agent_runtime': {**context['agent_runtime'], 'workspace_binding': 'other-workspace'}}
        with pytest.raises(FormationError):
            context_identity(altered)
        app.config['LUMENIS_OPEN_WORKSPACE'] = False
        with pytest.raises(FormationError):
            context_identity(context)
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    other_db = tmp_path / 'different-workspace.sqlite'
    with sqlite3.connect(path) as source, sqlite3.connect(other_db) as destination:
        source.backup(destination)
    monkeypatch.setenv('ZBC_DB_PATH', str(other_db))
    reset_task_engine()
    assert app.test_client().get(f'/api/ai/tasks/{task_id}').status_code == 403


def test_workspace_projection_redacts_single_slash_windows_paths():
    from agent_runtime.task_binding import _workspace_text
    projected = _workspace_text(r"Saved at C:\Users\28049\Documents\private.txt")
    assert projected is not None
    assert r"C:\Users\28049" not in projected
    assert '[path hidden]' in projected


def test_source_statistics_workspace_projection_preserves_null_and_verified_result():
    from ai_api import _task_workspace_record
    job_id = 'rbrief_1234567890abcdef'
    result = {
        'analysis_operation': 'source_statistics', 'base_analysis_status': 'completed',
        'source_brief_job_id': job_id, 'artifact_outcome': {'artifact_hash': 'a' * 64},
        'base_analysis': {
            'input_count': 0, 'unique_source_count': 0, 'duplicate_projection_count': 0,
            'platform_counts': {}, 'source_type_counts': {},
            'publication_time_known_count': 0, 'publication_time_unknown_count': 0,
            'publication_time_known_ratio': None, 'coverage': 'UNKNOWN',
        },
    }
    record = {'task_id': 'task_statistics_12345678', 'user_input': '分析来源数据统计',
        'status': 'succeeded', 'created_at': '2026-10-27T00:00:00Z',
        'updated_at': '2026-10-27T00:00:01Z', 'context': {
            'analysis_operation': 'source_statistics', 'source_brief_job_id': job_id,
        }, 'result': result}
    projected = _task_workspace_record(record)
    assert projected['result'] == result
    assert projected['workspace_view']['output_text'] is not None
    assert '唯一来源 0 个' in projected['workspace_view']['output_text']
    assert '已知比例 —' in projected['workspace_view']['output_text']
    assert '覆盖度：未知' in projected['workspace_view']['output_text']
    unavailable = {**result, 'base_analysis_status': 'unavailable', 'error': 'ANALYSIS_SOURCE_UNAVAILABLE'}
    failed_projection = _task_workspace_record({**record, 'result': unavailable})
    assert failed_projection['workspace_view']['output_text'] is None
    assert failed_projection['workspace_view']['error_code'] == 'ANALYSIS_SOURCE_UNAVAILABLE'
