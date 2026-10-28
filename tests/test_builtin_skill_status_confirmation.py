"""Original full-app Skill opt-in over isolated accounts/database, no model."""
from contextlib import contextmanager
from datetime import datetime, timedelta
import sqlite3
import uuid

import pytest

from tests.test_ai_conversation_owner import conversation_client
from tests.test_agent_runtime_http_binding import agent_client
from tests.test_skill_http_durable_identity import skill_client


@pytest.fixture
def builtin_client(conversation_client):
    from lumenis.system.security import permission
    api, app, path = conversation_client
    # Match main app startup policy on each disposable Gate; approval tokens
    # themselves are issued only by the real explicit-confirmation HTTP route.
    gate = permission.get_permission_gate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    gate.grant_permission(permission.PermissionLevel.HUMAN_APPROVAL)
    with sqlite3.connect(path) as con:
        con.execute("UPDATE v4_users SET role='owner' WHERE id=1")
        con.execute("INSERT OR REPLACE INTO skills_registry(skill_id,name,product,domain,status,version,source,runtime,source_type) "
            "VALUES('shared.social_card','Original local card','SHARED','content','disabled','1.0','builtin','builtin','builtin')")
    return api, app, path


def prepare(api, headers=None, *, operation_id=None, action='enable'):
    operation_id = operation_id or str(uuid.uuid4())
    response = api.post('/api/system/account/skills/shared.social_card/' + action, headers=headers,
                        json={'mode': 'prepare', 'operation_id': operation_id})
    assert response.status_code == 200, response.get_json()
    result = response.get_json()['result']
    return {'mode': 'confirm', 'operation_id': operation_id, 'expected_binding': result['expected_binding'],
            'confirm': True, 'confirmed_resource': result['resource']}


def status(path):
    with sqlite3.connect(path) as con:
        return con.execute("SELECT status FROM skills_registry WHERE skill_id='shared.social_card'").fetchone()[0]


@pytest.mark.parametrize('account', [False, True])
def test_explicit_opt_in_readback_replay_and_old_confirm_never_reenables(builtin_client, account):
    from lumenis.system.security import permission
    api, app, path = builtin_client
    headers = {'Authorization': 'Bearer fixture-session-one'} if account else None
    gate = permission.get_permission_gate()
    approvals = len(gate.list_approvals())
    request = prepare(api, headers)
    assert len(gate.list_approvals()) == approvals and status(path) == 'disabled'
    url = '/api/system/account/skills/shared.social_card/enable'
    enabled = api.post(url, headers=headers, json=request)
    assert enabled.status_code == 200, enabled.get_json()
    assert enabled.get_json()['result']['effect_performed'] is True and status(path) == 'enabled'
    repeated = app.test_client().post(url, headers=headers, json=request)
    assert repeated.status_code == 200, repeated.get_json()
    assert repeated.get_json()['result']['idempotent_hit'] is True
    off = prepare(api, headers, action='disable')
    assert api.post('/api/system/account/skills/shared.social_card/disable', headers=headers, json=off).status_code == 200
    replay = app.test_client().post(url, headers=headers, json=request)
    assert replay.status_code == 200, replay.get_json()
    assert replay.get_json()['result']['current_status'] == 'disabled' and status(path) == 'disabled'
    assert replay.get_json()['result']['effect_performed'] is False
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM v4_audit_logs WHERE action='builtin_skill_status_confirm'").fetchone()[0] == 2


@pytest.mark.parametrize('kind', ['cross_origin', 'identity_header', 'member', 'wrong_resource', 'false_confirm', 'changed_binding'])
def test_original_identity_current_registry_and_exact_confirmation_boundaries(builtin_client, kind):
    from lumenis.system.security import permission
    api, app, path = builtin_client
    request = prepare(api)
    headers = None
    if kind == 'cross_origin':
        headers = {'Origin': 'https://outside.example'}
    elif kind == 'identity_header':
        headers = {'X-Actor-ID': '1'}
    elif kind == 'member':
        headers = {'Authorization': 'Bearer fixture-session-two'}
    elif kind == 'wrong_resource':
        request['confirmed_resource'] = 'builtin-skill-status:v1:' + '0' * 64
    elif kind == 'false_confirm':
        request['confirm'] = False
    elif kind == 'changed_binding':
        with sqlite3.connect(path) as con:
            con.execute("UPDATE skills_registry SET version='2' WHERE skill_id='shared.social_card'")
    approvals = len(permission.get_permission_gate().list_approvals())
    response = api.post('/api/system/account/skills/shared.social_card/enable', headers=headers, json=request)
    assert response.status_code in (400, 401, 403, 409), response.get_json()
    assert status(path) == 'disabled'
    assert len(permission.get_permission_gate().list_approvals()) == approvals


@pytest.mark.parametrize('withdrawal', ['revoke', 'expire', 'authority'])
def test_withdrawal_before_commit_rolls_back_status_and_operation(builtin_client, monkeypatch, withdrawal):
    from lumenis.system.security import permission
    api, app, path = builtin_client
    request = prepare(api)
    gate = permission.get_permission_gate()
    original = gate.builtin_skill_status_commit_lease
    @contextmanager
    def withdraw(token, *, resource, caller):
        if withdrawal == 'revoke':
            gate.revoke_approval(token)
        elif withdrawal == 'expire':
            gate._approvals[token].expires_at = datetime.now() - timedelta(seconds=1)
        else:
            gate.revoke_permission(permission.PermissionLevel.COMMIT)
        with original(token, resource=resource, caller=caller):
            yield
    monkeypatch.setattr(gate, 'builtin_skill_status_commit_lease', withdraw)
    denied = api.post('/api/system/account/skills/shared.social_card/enable', json=request)
    assert denied.status_code == 403, denied.get_json()
    assert status(path) == 'disabled'
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM v4_audit_logs WHERE action='builtin_skill_status_confirm'").fetchone()[0] == 0


def test_opt_in_never_enables_an_unselected_builtin_or_package(builtin_client):
    api, app, path = builtin_client
    for skill_id in ['ai_analyzer', 'unregistered.plugin']:
        response = api.post('/api/system/account/skills/' + skill_id + '/enable',
                           json={'mode': 'prepare', 'operation_id': str(uuid.uuid4())})
        assert response.status_code in (400, 401, 403, 404)
    assert status(path) == 'disabled'
