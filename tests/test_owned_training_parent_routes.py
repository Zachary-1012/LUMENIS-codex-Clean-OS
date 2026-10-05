"""Normal parent denies unadmitted/mixed tasks before any remote side effect."""
import copy
import json
from pathlib import Path
import pytest
import experience_runtime as runtime
from lumenis.system.ai_gateway.owned_training_runtime import training_worker_source_pins
from tests.test_owned_training_phase_http_v2 import phase_http, strict_permission_mode, BASE_HEADERS, TASK_URL, _db_snapshot


def execute(case, task_id, body=None):
    return case['client'].post(TASK_URL + '/' + task_id + '/execute',
        json=case['body'] if body is None else body, headers=BASE_HEADERS,
        environ_overrides={'REMOTE_ADDR': '127.0.0.1'})


def test_parent_without_current_intent_cannot_touch_private_configuration(phase_http, monkeypatch):
    case = phase_http
    before = _db_snapshot(case['db'])
    def forbidden(*args):
        pytest.fail('Private runtime access before actual current approval')
    monkeypatch.setattr(runtime, '_owned_training_parent_profile', forbidden)
    response = execute(case, 'trainrelay_00000000-0000-4000-8000-000000000001')
    assert response.status_code == 403
    assert _db_snapshot(case['db']) == before


def test_prepared_task_cannot_mix_a_different_runtime_version(phase_http, tmp_path, monkeypatch):
    case = phase_http
    case['grant']()
    task = case['client'].post(TASK_URL, json=case['body'], headers=BASE_HEADERS,
                              environ_overrides={'REMOTE_ADDR': '127.0.0.1'}).get_json()
    before = _db_snapshot(case['db'])
    spec = tmp_path / 'runtime.json'
    spec.write_text(json.dumps({'worker_source_pins': {}, 'profiles': [
        {'domain_id': 'cth', 'request_body': case['body']}]}))
    monkeypatch.setenv('LUMENIS_TRAINING_PARENT_SPEC_PATH', str(spec))
    response = execute(case, task['task_id'])
    assert response.status_code == 409
    assert 'TRAINING_PARENT_INPUT_VERSION_CHANGED' in str(response.get_json())
    assert _db_snapshot(case['db']) == before
    assert not runtime._OWNED_TRAINING_PARENT_FENCES


def test_current_task_missing_actual_ssh_endpoint_is_unavailable_not_executed(phase_http, tmp_path, monkeypatch):
    case = phase_http
    case['grant']()
    task = case['client'].post(TASK_URL, json=case['body'], headers=BASE_HEADERS,
                              environ_overrides={'REMOTE_ADDR': '127.0.0.1'}).get_json()
    before = _db_snapshot(case['db'])
    root = Path(runtime.__file__).resolve().parent
    spec = tmp_path / 'runtime.json'
    spec.write_text(json.dumps({'worker_source_pins': training_worker_source_pins(root),
        'profiles': [{'domain_id': 'cth', 'request_body': case['body'],
            'controller_source_root': str(root), 'local_invocation': {
                'manifest_path': str(root / 'config/ai-owned-foundation.json'),
                'resume_request': None, 'stop_after_checkpoint_step': 2}}]}))
    monkeypatch.setenv('LUMENIS_TRAINING_PARENT_SPEC_PATH', str(spec))
    monkeypatch.delenv('LUMENIS_TRAINING_SSH_ENDPOINT_PATH', raising=False)
    # Isolate the fallback lookup from this workstation's real private runtime
    # file; this test proves the unavailable path, not the configured path.
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'missing-local-appdata'))
    response = execute(case, task['task_id'])
    assert response.status_code == 409
    assert 'TRAINING_SSH_ENDPOINT_NOT_CONFIGURED' in str(response.get_json())
    assert _db_snapshot(case['db']) == before
    assert not runtime._OWNED_TRAINING_PARENT_FENCES


def test_client_supplied_endpoint_or_actor_is_not_parent_authority(phase_http):
    case = phase_http
    for field in ('endpoint', 'actor_id'):
        value = copy.deepcopy(case['body'])
        value[field] = 1
        response = execute(case, 'trainrelay_00000000-0000-4000-8000-000000000001', value)
        assert response.status_code == 400
