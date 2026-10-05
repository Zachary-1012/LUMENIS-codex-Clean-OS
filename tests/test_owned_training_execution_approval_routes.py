"""Execution-intent boundary over real owners in disposable databases only."""
import copy
import pytest
from tests.test_owned_training_phase_http_v2 import phase_http, strict_permission_mode, BASE_HEADERS, TASK_URL, _db_snapshot
from lumenis.system.security import permission as p

URL = '/api/experience/owned-training/execution-approvals'

def body(case, confirm=False, resource=None):
    return {**copy.deepcopy(case['body']), 'confirm': confirm, 'confirmed_resource': resource}

def request(case, value, **extra):
    return case['client'].post(URL, json=value, headers=BASE_HEADERS,
                               environ_overrides={'REMOTE_ADDR': '127.0.0.1', **extra})

def test_preview_is_not_approval_and_confirm_enables_only_exact_phase_task(phase_http):
    case = phase_http
    case['gate'].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    before = _db_snapshot(case['db'])
    preview = request(case, body(case))
    assert preview.status_code == 200, preview.get_json()
    value = preview.get_json()
    assert value['approval_issued'] is False and value['training_started'] is False
    assert _db_snapshot(case['db']) == before
    confirmed = request(case, body(case, True, value['resource']))
    assert confirmed.status_code == 200, confirmed.get_json()
    result = confirmed.get_json()
    assert result['approval_issued'] is True and result['training_started'] is False
    assert 'approval_token' not in result
    assert _db_snapshot(case['db']) == before
    task = case['client'].post(TASK_URL, json=case['body'], headers=BASE_HEADERS,
                               environ_overrides={'REMOTE_ADDR': '127.0.0.1'})
    assert task.status_code == 200, task.get_json()
    assert task.get_json()['state'] == 'PHASE_TASK_PREPARED'
    assert task.get_json()['public_challenge_context']['next_sequence'] == 1
    assert task.get_json()['public_challenge_context']['last_phase'] is None

@pytest.mark.parametrize('change', ['extra_actor', 'changed_resource', 'not_boolean', 'wrong_descriptor'])
def test_invalid_or_forged_intent_cannot_create_grant_or_task(phase_http, change):
    case = phase_http
    case['gate'].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    before = _db_snapshot(case['db'])
    value = body(case, True, 'owned_training:v1:' + '0' * 64)
    if change == 'extra_actor':
        value['actor_id'] = 1
    elif change == 'not_boolean':
        value['confirm'] = 1
    elif change == 'wrong_descriptor':
        value['scope_descriptors']['GLOBAL / ALL']['domain_id'] = 'bmp'
    response = request(case, value)
    assert response.status_code in {400, 403}, response.get_json()
    assert _db_snapshot(case['db']) == before
    assert not any(not approval.revoked for approval in case['gate']._approvals.values())

def test_non_loopback_without_authentication_cannot_issue_execution_intent(phase_http):
    case = phase_http
    case['gate'].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    before = _db_snapshot(case['db'])
    response = request(case, body(case), REMOTE_ADDR='203.0.113.44')
    assert response.status_code in {401, 403}, response.get_json()
    assert _db_snapshot(case['db']) == before

def test_confirmation_is_rejected_when_final_server_identity_changes(phase_http, monkeypatch):
    import experience_runtime as runtime
    case = phase_http
    case['gate'].grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    preview = request(case, body(case)).get_json()
    original = runtime._owned_training_phase_material
    counter = {'calls': 0}
    def change_identity(value):
        result = original(value)
        counter['calls'] += 1
        if counter['calls'] == 3:
            binding = dict(result[4])
            binding['resource'] = 'changed'
            result = (*result[:4], binding, *result[5:])
        return result
    monkeypatch.setattr(runtime, '_owned_training_phase_material', change_identity)
    before = _db_snapshot(case['db'])
    response = request(case, body(case, True, preview['resource']))
    assert response.status_code == 403, response.get_json()
    assert _db_snapshot(case['db']) == before
    assert all(approval.revoked for approval in case['gate']._approvals.values())
