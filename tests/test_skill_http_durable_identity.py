"""Real HTTP/session/SQLite Skill round trip using disposable local account fixtures.

These are fixture identities, not external accounts or live model acceptance.
"""
import sqlite3

import pytest
from flask import Flask


@pytest.fixture
def skill_client(tmp_path, monkeypatch):
    path = tmp_path / 'skill-http.sqlite3'
    monkeypatch.setenv('ZBC_DB_PATH', str(path))
    from account.models import init_account_db
    from ai_task_engine import init_task_engine_db, reset_task_engine
    init_account_db()
    init_task_engine_db()
    reset_task_engine()
    with sqlite3.connect(path) as con:
        con.executemany("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES(?,?,?,'user','active')",
                        [(1,'fixture-one','not-a-password'), (2,'fixture-two','not-a-password')])
        con.executemany("INSERT INTO v4_sessions(user_id,token,expires_at) VALUES(?,?,'2099-01-01 00:00:00')",
                        [(1,'fixture-session-one'), (2,'fixture-session-two')])
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(1,'CTH','zbc.skill_registry_snapshot','read')")
        con.execute("INSERT INTO skills_registry(skill_id,name,product,domain,status,version) VALUES('zbc.skill_registry_snapshot','Registry snapshot','CTH','cth','enabled','1.0')")
    from lumenis.system.security import permission as p
    from lumenis.system import security
    monkeypatch.setattr(p, '_TESTING_BYPASS_ENABLED', False)
    monkeypatch.delenv('PERMISSION_GATE_TESTING', raising=False)
    gate = p.PermissionGate()
    monkeypatch.setattr(p, 'get_permission_gate', lambda: gate)
    monkeypatch.setattr(security, 'get_permission_gate', lambda: gate)
    from ai_api import bp
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app.test_client(), app, path


def test_skill_http_result_reopens_with_owner_identity_and_revocation(skill_client):
    api, app, path = skill_client
    own = {'Authorization': 'Bearer fixture-session-one'}
    other = {'Authorization': 'Bearer fixture-session-two'}
    response = api.post('/api/ai/tasks', headers=own, json={
        'skill_id': 'zbc.skill_registry_snapshot', 'task': 'Read registered capabilities',
        'product': 'CTH', 'action_type': 'READ', 'user_id': 2,
    })
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    assert result['success'] is True
    identifier = result['execution_id']
    assert len(identifier) == 16 and all(char in '0123456789abcdef' for char in identifier)
    reopened = app.test_client().get('/api/ai/tasks/' + identifier, headers=own)
    assert reopened.status_code == 200, reopened.get_json()
    row = reopened.get_json()['task']
    assert row['user_id'] == 1 and row['status'] == 'completed'
    assert row['task_kind'] == 'SKILL_EXECUTION'
    assert reopened.get_json()['notification']['return_ref'] == '/api/ai/tasks/' + identifier
    assert api.get('/api/ai/tasks/' + identifier, headers=other).status_code == 404
    assert api.get('/api/ai/tasks', headers=other).get_json()['tasks'] == []
    assert api.get('/api/ai/tasks', headers=own).get_json()['tasks'][0]['execution_id'] == identifier
    with sqlite3.connect(path) as con:
        con.execute('DELETE FROM v4_member_authorizations WHERE user_id=1')
    assert api.get('/api/ai/tasks/' + identifier, headers=own).status_code == 404
    assert api.get('/api/ai/tasks', headers=own).get_json()['notifications'] == []


def test_visible_pagination_scans_past_other_actors(skill_client):
    api, app, path = skill_client
    from lumenis.shared.agents.skills.execution import ensure_skill_executions_table
    ensure_skill_executions_table()
    with sqlite3.connect(path) as con:
        con.executemany("""INSERT INTO skill_executions
            (execution_id,skill_id,user_id,product,domain,status,created_at)
            VALUES(?,'zbc.skill_registry_snapshot',?,'CTH','cth','completed',?)""",
            [(f'other-{i}',2,f'2026-10-17 05:{i // 60:02}:{i % 60:02}') for i in range(105)] +
            [('own-old',1,'2026-10-17 01:00:00'), ('own-new',1,'2026-10-17 02:00:00')])
    headers = {'Authorization': 'Bearer fixture-session-one'}
    first = api.get('/api/ai/tasks?limit=1', headers=headers).get_json()
    assert [row['execution_id'] for row in first['tasks']] == ['own-new']
    assert first['has_more'] and first['next_offset'] == 1
    second = api.get('/api/ai/tasks?limit=1&offset=1', headers=headers).get_json()
    assert [row['execution_id'] for row in second['tasks']] == ['own-old']
    assert second['has_more'] is False
