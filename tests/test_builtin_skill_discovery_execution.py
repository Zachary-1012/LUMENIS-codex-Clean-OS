"""Builtin projection/selection/execution using original account and Skill owners."""
import sqlite3

from tests.test_skill_http_durable_identity import skill_client
from tests.test_agent_runtime_http_binding import agent_client, submit


def test_existing_local_handlers_are_discoverable_disabled_without_overwriting_existing_skill(skill_client):
    api, app, path = skill_client
    from account.skills import list_skills
    from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS
    rows = {row['skill_id']: row for row in list_skills()}
    assert _BACKGROUND_INPUTS.keys() <= rows.keys()
    assert rows['zbc.skill_registry_snapshot']['product'] == 'CTH'
    assert rows['zbc.skill_registry_snapshot']['status'] == 'enabled'
    assert rows['zbc.skill_registry_snapshot']['version'] == '1.0'
    for skill_id in _BACKGROUND_INPUTS.keys() - {'zbc.skill_registry_snapshot'}:
        assert rows[skill_id]['status'] == 'disabled'
        assert rows[skill_id]['runtime'] == 'builtin' and rows[skill_id]['source'] == 'builtin'


def test_owner_can_select_existing_local_shared_handler_without_business_prerequisite(skill_client, monkeypatch):
    api, app, path = skill_client
    from account.api import account_bp
    app.register_blueprint(account_bp)
    with sqlite3.connect(path) as con:
        con.execute("UPDATE v4_users SET role='owner' WHERE id=1")
    import lumenis_skill_adapter
    monkeypatch.setattr(lumenis_skill_adapter, 'get_skill_adapter', lambda: (_ for _ in ()).throw(AssertionError('external runtime reached')))
    own = {'Authorization': 'Bearer fixture-session-one'}
    discovered = api.get('/api/system/account/skills', headers=own)
    assert discovered.status_code == 200
    enabled = api.post('/api/system/account/skills/shared.social_card/enable', headers=own)
    assert enabled.status_code == 200, enabled.get_json()
    response = api.post('/api/ai/tasks', headers=own, json={
        'skill_id': 'shared.social_card', 'task': 'Original local card', 'input': {'title': 'Own writing'}, 'action_type': 'READ'})
    assert response.status_code == 200 and response.get_json()['success'], response.get_json()
    identifier = response.get_json()['execution_id']
    reopened = app.test_client().get('/api/ai/tasks/' + identifier, headers=own)
    assert reopened.status_code == 200 and reopened.get_json()['task']['status'] == 'completed', reopened.get_json()


def test_domain_agent_uses_original_system_metadata_owner_with_current_cross_domain_contract(agent_client):
    api, app, path = agent_client
    # Match a normally discovered builtin. Earlier fixtures used a CTH-owned
    # copy and therefore did not exercise the actual SYSTEM caller boundary.
    with sqlite3.connect(path) as con:
        con.execute("UPDATE skills_registry SET product='SYSTEM',domain='system',source='builtin',runtime='builtin' "
                    "WHERE skill_id='zbc.skill_registry_snapshot'")
    identifier = submit(api)
    own = {'Authorization': 'Bearer fixture-session-one'}
    response = api.post('/api/ai/tasks/' + identifier + '/run', headers=own)
    assert response.status_code == 200 and response.get_json()['task']['status'] == 'succeeded', response.get_json()
    assert app.test_client().get('/api/ai/tasks/' + identifier, headers=own).get_json()['task']['status'] == 'succeeded'


def test_cancelled_parent_retains_readable_committed_child_without_execution_replay(agent_client, monkeypatch):
    api, app, path = agent_client
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    identifier = submit(api)
    own = {'Authorization': 'Bearer fixture-session-one'}
    original = DurableExecutionAdapter.complete_step
    stopped = []
    def completed(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if not stopped:
            stopped.append(True)
            response = api.post('/api/ai/tasks/' + identifier + '/cancel', headers=own)
            assert response.status_code == 200, response.get_json()
        return result
    monkeypatch.setattr(DurableExecutionAdapter, 'complete_step', completed)
    response = api.post('/api/ai/tasks/' + identifier + '/run', headers=own)
    assert response.status_code == 200 and response.get_json()['task']['status'] == 'cancelled', response.get_json()
    reopened = app.test_client().get('/api/ai/tasks/' + identifier, headers=own)
    assert reopened.status_code == 200 and reopened.get_json()['task']['status'] == 'cancelled', reopened.get_json()
    with sqlite3.connect(path) as con:
        before = con.execute("SELECT COUNT(*) FROM skill_executions WHERE status='completed'").fetchone()[0]
    replay = api.post('/api/ai/tasks/' + identifier + '/run', headers=own)
    assert replay.status_code == 200 and replay.get_json()['task']['status'] == 'cancelled', replay.get_json()
    with sqlite3.connect(path) as con:
        assert before == 1 and con.execute("SELECT COUNT(*) FROM skill_executions WHERE status='completed'").fetchone()[0] == before
