"""Synthetic, no-network regression of actor selection and exact external consent."""
import io
import json
from datetime import datetime, timedelta

import pytest
from flask import Flask, request
from lumenis.system.ai_gateway import core, user_api_adapter as adapter
from lumenis.system.security import permission

CONFIG = {'provider': 'user_api', 'base_url': adapter.GROQ_BASE_URL,
          'api_key': 'synthetic-test-secret', 'model': 'synthetic-model'}


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    import ai_api
    import settings_module
    from lumenis.ai_hub import service
    from lumenis.auth import service as auth
    gate = permission.PermissionGate()
    monkeypatch.setattr(permission, '_TESTING_BYPASS_ENABLED', False)
    monkeypatch.delenv('PERMISSION_GATE_TESTING', raising=False)
    monkeypatch.setattr(permission, 'get_permission_gate', lambda: gate)
    # Test identity comes only from this fixture, never from product headers.
    actor = {'id': 17}
    monkeypatch.setattr(auth, 'get_current_user', lambda **kw: dict(actor) if actor else None)
    monkeypatch.setattr(permission, '_actor_has_scope_action', lambda *a, **k: True)
    monkeypatch.setattr(permission, '_load_actor_scope_role', lambda *a, **k: 'owner')
    monkeypatch.setattr(service, 'record_learning', lambda *a, **k: None)
    monkeypatch.setattr(service.freg, 'search_function_metadata', lambda *a, **k: [])
    monkeypatch.setattr(settings_module, 'CONFIG_FILE', str(tmp_path / 'settings.json'))
    monkeypatch.setattr(adapter, '_open', lambda *a, **k: pytest.fail('external network attempted'))
    app = Flask(__name__)
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    app.register_blueprint(settings_module.settings_bp)
    app.register_blueprint(ai_api.bp)
    return app, app.test_client(), gate, actor


def select(client, **overrides):
    response = client.post('/api/settings/ai', json={**CONFIG, **overrides})
    assert response.status_code == 200, response.json
    assert CONFIG['api_key'] not in json.dumps(response.json)
    return response.json


def preview(client, text='my question', **extra):
    response = client.post('/api/ai/chat', json={'message': text, **extra})
    assert response.status_code == 409, response.json
    assert response.json['status'] == 'APPROVAL_REQUIRED'
    p = response.json['approval_request']
    assert p['destination'] == adapter.GROQ_CHAT_URL
    return {'confirmed': True, 'confirmation_id': p['confirmation_id'], 'resource': p['resource']}, p


def transport(monkeypatch):
    calls = []
    def opened(req, timeout):
        calls.append(req)
        return io.BytesIO(b'{"choices":[{"message":{"content":"synthetic response"}}],"usage":{"total_tokens":8}}')
    monkeypatch.setattr(adapter, '_open', opened)
    return calls


def test_process_env_never_selects_product_user(runtime, monkeypatch):
    from lumenis.ai_hub import service
    app, client, gate, actor = runtime
    monkeypatch.setenv('AI_PROVIDER', 'user_api')
    monkeypatch.setenv('USER_MODEL_API_KEY', 'synthetic-env-secret')
    monkeypatch.setenv('USER_MODEL_API_MODEL', 'synthetic-model')
    monkeypatch.setenv('USER_MODEL_API_BASE_URL', adapter.GROQ_BASE_URL)
    monkeypatch.setattr(service, '_run_owned', lambda *a: {'ok': False, 'status': 'UNAVAILABLE'})
    with app.test_request_context('/'):
        assert adapter.is_selected() is False
        assert adapter.config() == {}
        assert service.chat('hello')['provider'] == 'owned'
    assert client.get('/api/settings/ai').json['ai']['provider'] == 'owned'


def test_exact_approval_then_single_use_transport(runtime, monkeypatch):
    app, client, gate, actor = runtime
    select(client)
    confirmation, p = preview(client)
    calls = transport(monkeypatch)
    result = client.post('/api/ai/chat', json={'message': 'my question', 'external_approval': confirmation})
    assert result.status_code == 200, result.json
    assert result.json['provider'] == 'user_api'
    assert json.loads(calls[0].data) == p['request']
    assert result.json['usage'] == {'total_tokens': 8}
    retry = client.post('/api/ai/chat', json={'message': 'my question', 'external_approval': confirmation})
    assert retry.json['code'] == 'USER_API_CONFIRMATION_INVALID'
    assert len(calls) == 1


def test_selection_and_approval_cannot_cross_user(runtime, monkeypatch):
    app, client, gate, actor = runtime
    select(client)
    confirmation, _ = preview(client)
    actor['id'] = 18
    assert client.get('/api/settings/ai').json['ai']['provider'] == 'owned'
    select(client, api_key='synthetic-user-18-secret')
    calls = transport(monkeypatch)
    denied = client.post('/api/ai/chat', json={'message': 'my question', 'external_approval': confirmation})
    assert denied.json['code'] == 'USER_API_CONFIRMATION_INVALID'
    assert calls == []
    actor['id'] = 17
    assert client.post('/api/ai/chat', json={'message': 'my question', 'external_approval': confirmation}).status_code == 200
    assert calls[0].headers['Authorization'] == 'Bearer synthetic-test-secret'


@pytest.mark.parametrize('mutation', ['message', 'history', 'model', 'key', 'selection'])
def test_exact_binding_changes_invalidate_confirmation(runtime, monkeypatch, mutation):
    app, client, gate, actor = runtime
    select(client)
    confirmation, _ = preview(client)
    data = {'message': 'my question', 'external_approval': confirmation}
    if mutation == 'message': data['message'] += ' changed'
    if mutation == 'history': data['history'] = [{'role': 'user', 'content': 'changed history'}]
    if mutation == 'model': select(client, model='new-model')
    if mutation == 'key': select(client, api_key='synthetic-key-rotated')
    if mutation == 'selection':
        assert client.post('/api/settings/ai', json={'provider': 'owned'}).status_code == 200
        select(client)
    calls = transport(monkeypatch)
    result = client.post('/api/ai/chat', json=data)
    assert result.json['code'] == 'USER_API_CONFIRMATION_INVALID'
    assert not calls


def test_destination_and_confirmation_fields_cannot_be_forged(runtime):
    app, client, gate, actor = runtime
    invalid = client.post('/api/settings/ai', json={**CONFIG, 'base_url': 'https://other.invalid/v1'})
    assert invalid.status_code == 400 and invalid.json['code'] == 'USER_API_DESTINATION_NOT_ALLOWED'
    select(client)
    confirmation, _ = preview(client)
    confirmation['destination'] = 'https://other.invalid'
    assert client.post('/api/ai/chat', json={'message': 'my question', 'external_approval': confirmation}).json['code'] == 'USER_API_CONFIRMATION_INVALID'


def test_broad_gate_approval_does_not_replace_request_confirmation(runtime):
    app, client, gate, actor = runtime
    select(client)
    gate.grant_approval('*', resource=None)
    assert client.post('/api/ai/chat', json={'message': 'my question', 'external_approval': {'confirmed': True}}).json['code'] == 'USER_API_CONFIRMATION_INVALID'
    confirmation, p = preview(client)
    with app.test_request_context('/'):
        d = permission.check_shared_workspace_effect({'id':17}, {'scope_kind':'shared_workspace','version':1},
            permission.OperationType.AI_CALL, p['resource'], module='conversation',action='write')
        assert d.allowed is False and d.requires_approval is True
        assert d.risk_level == 'high'


def test_withdrawal_and_cold_gate_restart_never_restore_external_route(runtime, monkeypatch):
    app, client, gate, actor = runtime
    select(client)
    confirmation, _ = preview(client)
    gate.revoke_permission(permission.PermissionLevel.ANALYZE)
    assert client.post('/api/settings/ai', json={'provider':'owned'}).status_code == 200
    gate.grant_permission(permission.PermissionLevel.ANALYZE)
    result = client.post('/api/ai/chat', json={'message':'my question','external_approval':confirmation})
    assert result.json['code'] == 'USER_API_NOT_SELECTED'
    select(client)
    monkeypatch.setattr(permission, 'get_permission_gate', lambda: permission.PermissionGate())
    with app.test_request_context('/'):
        assert adapter.is_selected() is False


def test_expired_permission_and_live_revocation_prevent_transport(runtime):
    app, client, gate, actor = runtime
    select(client)
    confirmation, _ = preview(client)
    gate._user_api_confirmations[confirmation['confirmation_id']]['expires'] = datetime.now() - timedelta(seconds=1)
    assert client.post('/api/ai/chat', json={'message':'my question','external_approval':confirmation}).json['code'] == 'USER_API_CONFIRMATION_INVALID'
    confirmation, _ = preview(client)
    gate.revoke_permission(permission.PermissionLevel.ANALYZE)
    assert client.post('/api/ai/chat', json={'message':'my question','external_approval':confirmation}).json['code'] == 'USER_API_PERMISSION_DENIED'


def test_settings_never_persist_or_return_secret(runtime, tmp_path):
    import settings_module
    app, client, gate, actor = runtime
    result = client.post('/api/settings/config', json={'ai': CONFIG, 'report': {'daily_enabled': False}})
    assert result.status_code == 200, result.json
    persisted = open(settings_module.CONFIG_FILE).read()
    assert CONFIG['api_key'] not in persisted and '"ai":' not in persisted
    assert CONFIG['api_key'] not in json.dumps(client.get('/api/settings/config').json)
    assert CONFIG['api_key'] not in repr(gate.get_audit_log())


def test_no_user_identity_and_cross_origin_settings_fail_closed(runtime):
    app, client, gate, actor = runtime
    assert client.post('/api/settings/ai', json=CONFIG, headers={'Origin':'https://evil.invalid'}).status_code == 403
    actor.clear()
    app.config['LUMENIS_OPEN_WORKSPACE'] = False
    assert client.post('/api/settings/ai', json=CONFIG).status_code == 403


def test_owned_analysis_risk_and_unrelated_settings_preserved(runtime):
    app, client, gate, actor = runtime
    d = gate.check(permission.OperationType.AI_CALL, resource='owned-analysis', domain_id='system')
    assert d.allowed and not d.requires_approval and d.risk_level == 'low'
    result = client.post('/api/settings/config', json={'report': {'daily_enabled': False}})
    assert result.status_code == 200
    assert client.get('/api/settings/config').json['config']['report']['daily_enabled'] is False


def test_network_failure_consumes_confirmation_without_automatic_retry(runtime, monkeypatch):
    app, client, gate, actor = runtime
    select(client)
    confirmation, _ = preview(client)
    calls = []
    def fail(*args, **kwargs):
        calls.append(True)
        raise OSError('synthetic network failure')
    monkeypatch.setattr(adapter, '_open', fail)
    body = {'message': 'my question', 'external_approval': confirmation}
    assert client.post('/api/ai/chat', json=body).json['code'] == 'USER_API_UNAVAILABLE'
    assert client.post('/api/ai/chat', json=body).json['code'] == 'USER_API_CONFIRMATION_INVALID'
    assert calls == [True]


def test_concurrent_same_confirmation_sends_at_most_once(runtime, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    app, client, gate, actor = runtime
    select(client)
    confirmation, _ = preview(client)
    calls = transport(monkeypatch)
    def submit():
        return app.test_client().post('/api/ai/chat', json={
            'message': 'my question', 'external_approval': confirmation}).json
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(), range(2)))
    assert sum(result['ok'] for result in results) == 1
    assert len(calls) == 1


def test_approval_withdrawn_between_confirmation_and_send(runtime, monkeypatch):
    app, client, gate, actor = runtime
    select(client)
    confirmation, _ = preview(client)
    original = gate.confirm_user_api_request
    def withdraw(*args):
        token = original(*args)
        gate.revoke_approval(token)
        return token
    monkeypatch.setattr(gate, 'confirm_user_api_request', withdraw)
    result = client.post('/api/ai/chat', json={'message': 'my question', 'external_approval': confirmation})
    assert result.json['code'] == 'USER_API_PERMISSION_DENIED'


def test_hub_route_uses_same_exact_confirmation(runtime, monkeypatch):
    from lumenis.ai_hub.routes import ai_bp
    app, client, gate, actor = runtime
    app.register_blueprint(ai_bp, url_prefix='/v4')
    select(client)
    before = client.post('/v4/ai/chat', json={'message': 'hub question'})
    assert before.status_code == 409, before.json
    consent = before.json['approval_request']
    calls = transport(monkeypatch)
    result = client.post('/v4/ai/chat', json={'message': 'hub question', 'external_approval': {
        'confirmed': True, 'confirmation_id': consent['confirmation_id'], 'resource': consent['resource'],
    }})
    assert result.status_code == 200 and result.json['success'] is True
    assert len(calls) == 1


@pytest.mark.parametrize('value', [[], None, True, 1, {}, 'unknown'])
def test_malformed_provider_setting_is_client_error(runtime, value):
    app, client, gate, actor = runtime
    assert client.post('/api/settings/ai', json={'provider': value}).status_code == 400


from tests.test_skill_http_durable_identity import skill_client


def test_real_session_sqlite_two_users_and_revocation(skill_client, monkeypatch):
    import sqlite3
    from lumenis.ai_hub import service
    from lumenis.ai_hub.routes import ai_bp
    api, app, path = skill_client
    app.register_blueprint(ai_bp, url_prefix='/v4')
    monkeypatch.setattr(service, 'record_learning', lambda *a, **k: None)
    monkeypatch.setattr(service.freg, 'search_function_metadata', lambda *a, **k: [])
    one = {'Authorization': 'Bearer fixture-session-one'}
    two = {'Authorization': 'Bearer fixture-session-two'}
    with sqlite3.connect(path) as con:
        con.executemany("INSERT INTO v4_member_authorizations(user_id,product_id,module,action) VALUES(?,'SHARED','conversation','write')", [(1,), (2,)])
    calls = transport(monkeypatch)
    selected = api.post('/v4/ai/settings', json=CONFIG, headers=one)
    assert selected.status_code == 200, selected.json
    assert api.get('/v4/ai/settings', headers=two).json['ai']['provider'] == 'owned'
    before = api.post('/v4/ai/chat', json={'message': 'private user-one text'}, headers=one)
    assert before.status_code == 409 and calls == [], before.json
    preview = before.json['approval_request']
    body = {'message': 'private user-one text', 'external_approval': {
        'confirmed': True, 'confirmation_id': preview['confirmation_id'], 'resource': preview['resource'],
    }}
    assert api.post('/v4/ai/chat', json=body, headers=two).json['code'] == 'USER_API_NOT_SELECTED'
    assert api.post('/v4/ai/chat', json=body, headers=one).status_code == 200
    assert len(calls) == 1
    before = api.post('/v4/ai/chat', json={'message': 'revoked query'}, headers=one)
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1 AND product_id='SHARED'")
    preview = before.json['approval_request']
    denied = api.post('/v4/ai/chat', json={'message': 'revoked query', 'external_approval': {
        'confirmed': True, 'confirmation_id': preview['confirmation_id'], 'resource': preview['resource'],
    }}, headers=one)
    assert denied.json['code'] == 'USER_API_PERMISSION_DENIED'
    assert len(calls) == 1
    assert api.post('/v4/ai/settings', json={'provider':'owned'}, headers=one).status_code == 200


def test_final_audit_records_effect_without_raw_conversation_or_credentials(runtime, monkeypatch):
    app, client, gate, actor = runtime
    select(client)
    confirmation, _ = preview(client, 'private-content-sentinel')
    transport(monkeypatch)
    result = client.post('/api/ai/chat', json={'message': 'private-content-sentinel', 'external_approval': confirmation})
    assert result.status_code == 200
    event = gate.get_audit_log()[-1]
    assert event['result'] == 'completed' and event['caller'] == 'actor:17'
    assert event['resource'] == confirmation['resource']
    audit = repr(gate.get_audit_log())
    assert 'private-content-sentinel' not in audit and CONFIG['api_key'] not in audit


def test_audit_failure_after_send_is_honest_and_not_retried(runtime, monkeypatch):
    app, client, gate, actor = runtime
    select(client)
    confirmation, _ = preview(client)
    original = gate._write_audit
    def write(**kwargs):
        if kwargs.get('result') == 'completed':
            raise OSError('synthetic audit unavailable')
        return original(**kwargs)
    monkeypatch.setattr(gate, '_write_audit', write)
    calls = transport(monkeypatch)
    body = {'message': 'my question', 'external_approval': confirmation}
    assert client.post('/api/ai/chat', json=body).json['code'] == 'USER_API_AUDIT_UNAVAILABLE_AFTER_SEND'
    assert client.post('/api/ai/chat', json=body).json['code'] == 'USER_API_CONFIRMATION_INVALID'
    assert len(calls) == 1


def test_credentials_require_https_outside_loopback(runtime):
    app, client, gate, actor = runtime
    denied = client.post('/api/settings/ai', json=CONFIG, base_url='http://product.example',
                         environ_overrides={'REMOTE_ADDR': '192.0.2.10'})
    assert denied.status_code == 403
    allowed = client.post('/api/settings/ai', json=CONFIG, base_url='https://product.example',
                          environ_overrides={'REMOTE_ADDR': '192.0.2.10'})
    assert allowed.status_code == 200


def test_early_analyze_refusal_has_canonical_minimal_audit(runtime):
    app, client, gate, actor = runtime
    select(client)
    gate.revoke_permission(permission.PermissionLevel.ANALYZE)
    with app.test_request_context('/'):
        result = adapter.chat('private-prompt', 'secret-user-text', external_user_input=True)
    assert result[1] == 'user_api_permission_denied'
    event = gate.get_audit_log()[-1]
    assert event['reason'] == 'USER_API_ANALYZE_PERMISSION_REQUIRED'
    assert event['result'] == 'denied' and event['caller'] == 'actor:17'
    assert event['resource'] == 'user-api-conversation:denied'
    assert event['audit_id'] and event['operation_id'].startswith('user_api_denial_')
    assert 'private-prompt' not in repr(event) and 'secret-user-text' not in repr(event)


def test_noncanonical_gate_refusal_audits_current_request_not_supplied_actor(runtime):
    app, client, gate, actor = runtime
    other = permission.PermissionGate()
    with app.test_request_context('/'):
        with pytest.raises(PermissionError) as caught:
            other.authorize_user_api_action({'id': 999, 'secret': 'not-a-real-identity'})
    assert caught.value.audit_id
    assert other.get_audit_log() == []
    event = gate.get_audit_log()[-1]
    assert event['reason'] == 'USER_API_CANONICAL_GATE_REQUIRED'
    assert event['caller'] == 'actor:17'
    assert '999' not in repr(event) and 'not-a-real-identity' not in repr(event)


def test_absent_request_identity_is_explicitly_unverified_in_denial_audit(runtime):
    app, client, gate, actor = runtime
    assert adapter.chat('private-s', 'private-u', external_user_input=True)[1] == 'user_api_permission_context_required'
    event = gate.get_audit_log()[-1]
    assert event['caller'] == 'unverified' and event['audit_id']
    assert event['reason'] == 'USER_API_PERMISSION_CONTEXT_REQUIRED'


def test_settings_identity_denial_returns_canonical_correlation_id(runtime):
    app, client, gate, actor = runtime
    actor.clear()
    app.config['LUMENIS_OPEN_WORKSPACE'] = False
    response = client.get('/api/settings/ai')
    assert response.status_code == 403
    event = gate.get_audit_log()[-1]
    assert event['audit_id'] == response.json['audit_id']
    assert event['caller'] == 'unverified' and event['result'] == 'denied'


@pytest.mark.parametrize('mutation,reason', [
    ({'base_url': 'https://private-user:private-password@other.invalid/private-path?key=private-query'}, 'USER_API_DESTINATION_NOT_ALLOWED'),
    ({'api_key': ''}, 'USER_API_KEY_REQUIRED'),
    ({'model': ''}, 'USER_API_MODEL_REQUIRED'),
    ({'unexpected': 'private-unknown-field'}, 'USER_API_SETTINGS_INVALID'),
])
def test_invalid_configuration_denial_never_audits_secret_url_or_secret_hash(runtime, mutation, reason):
    import hashlib
    app, client, gate, actor = runtime
    response = client.post('/api/settings/ai', json={**CONFIG, **mutation})
    assert response.status_code == 400
    event = gate.get_audit_log()[-1]
    assert event['reason'] == reason and event['audit_id'] == response.json['audit_id']
    text = repr(gate.get_audit_log())
    for value in ['private-user', 'private-password', 'private-path', 'private-query', 'private-unknown-field', CONFIG['api_key']]:
        assert value not in text and hashlib.sha256(value.encode()).hexdigest() not in text


@pytest.mark.parametrize('mode', ['raise', 'missing_id'])
def test_unwritable_denial_audit_fails_closed_without_transport(runtime, monkeypatch, mode):
    app, client, gate, actor = runtime
    select(client)
    calls = transport(monkeypatch)
    gate.revoke_permission(permission.PermissionLevel.ANALYZE)
    def broken(**kwargs):
        if mode == 'raise':
            raise OSError('private-log-path-error')
        return None
    monkeypatch.setattr(gate, '_write_audit', broken)
    with app.test_request_context('/'):
        result = adapter.chat('secret-prompt', 'private-text', external_user_input=True)
    assert result == (None, 'user_api_audit_unavailable', None)
    assert calls == [] and 'private-log-path-error' not in repr(result)
    settings = client.post('/api/settings/ai', json=CONFIG)
    assert settings.status_code == 503 and settings.json['code'] == 'USER_API_AUDIT_UNAVAILABLE'


def test_actual_persistent_audit_failure_blocks_external_transport(runtime, monkeypatch, tmp_path):
    app, client, gate, actor = runtime
    select(client)
    confirmation, _ = preview(client)
    calls = transport(monkeypatch)
    gate.audit_log_path = str(tmp_path)  # Existing directory cannot be a log file.
    response = client.post('/api/ai/chat', json={'message': 'my question', 'external_approval': confirmation})
    assert response.json['code'] == 'USER_API_AUDIT_UNAVAILABLE'
    assert calls == []
    gate.audit_log_path = None
    replay = client.post('/api/ai/chat', json={'message': 'my question', 'external_approval': confirmation})
    assert replay.json['code'] == 'USER_API_CONFIRMATION_INVALID' and calls == []


def test_confirmation_denial_has_no_untrusted_body_metadata(runtime):
    app, client, gate, actor = runtime
    select(client)
    response = client.post('/api/ai/chat', json={'message': 'private-body', 'external_approval': {
        'confirmed': True, 'confirmation_id': 'private-forged-token', 'resource': 'private-forged-resource'}})
    assert response.json['code'] == 'USER_API_CONFIRMATION_INVALID'
    event = gate.get_audit_log()[-1]
    assert event['reason'] == 'USER_API_CONFIRMATION_INVALID' and event['audit_id']
    for value in ('private-body', 'private-forged-token', 'private-forged-resource'):
        assert value not in repr(event)


def test_missing_selection_and_explicit_admission_each_have_fixed_denial_audit(runtime):
    app, client, gate, actor = runtime
    with app.test_request_context('/'):
        assert adapter.chat('s', 'u', external_user_input=True)[1] == 'provider_disabled'
        assert gate.get_audit_log()[-1]['reason'] == 'USER_API_NOT_SELECTED'
        assert adapter.chat('s', 'u')[1] == 'provider_disabled'
        assert gate.get_audit_log()[-1]['reason'] == 'USER_API_EXTERNAL_INPUT_REQUIRED'


def test_denial_audit_does_not_accept_arbitrary_reason_or_forged_identity(runtime):
    app, client, gate, actor = runtime
    actor.clear()
    app.config['LUMENIS_OPEN_WORKSPACE'] = False
    with app.test_request_context('/'):
        audit_id = gate.audit_user_api_denial('USER_API_private-key-injected')
    event = gate.get_audit_log()[-1]
    assert event['audit_id'] == audit_id
    assert event['reason'] == 'USER_API_PERMISSION_UNAVAILABLE'
    assert event['caller'] == 'unverified' and 'private-key-injected' not in repr(event)


@pytest.mark.parametrize('body,expected_status', [([],400), ({'message':''},400), ({'message':'x'*4001},413)])
def test_external_chat_route_input_refusal_is_audited(runtime, body, expected_status):
    app, client, gate, actor = runtime
    select(client)
    response = client.post('/api/ai/chat', json=body)
    assert response.status_code == expected_status
    event = gate.get_audit_log()[-1]
    assert event['reason'] == 'USER_API_INVALID_REQUEST'
    assert event['audit_id'] == response.json['audit_id']


def test_stale_confirmation_after_withdrawal_has_denial_audit(runtime):
    app, client, gate, actor = runtime
    select(client)
    confirmation, _ = preview(client)
    assert client.post('/api/settings/ai', json={'provider':'owned'}).status_code == 200
    response = client.post('/api/ai/chat', json={'message':'my question', 'external_approval':confirmation})
    assert response.json['code'] == 'USER_API_NOT_SELECTED'
    assert gate.get_audit_log()[-1]['audit_id'] == response.json['audit_id']
    assert gate.get_audit_log()[-1]['reason'] == 'USER_API_NOT_SELECTED'


@pytest.mark.parametrize('error_type', [ValueError, PermissionError, RuntimeError])
def test_settings_never_echo_dynamic_identity_failure(runtime, monkeypatch, error_type):
    from lumenis.auth import service as auth
    app, client, gate, actor = runtime
    def broken(**kwargs):
        raise error_type('synthetic-secret-from-auth-read')
    monkeypatch.setattr(auth, 'get_current_user', broken)
    response = client.post('/api/settings/ai', json={'provider':'owned'})
    assert response.status_code in (403,503)
    assert 'synthetic-secret-from-auth-read' not in repr(response.json)
    event = gate.get_audit_log()[-1]
    assert event['reason'] == 'USER_API_SETTINGS_UNAVAILABLE'
    assert event['caller'] == 'unverified'
    assert 'synthetic-secret-from-auth-read' not in repr(event)
    assert response.json['audit_id'] == event['audit_id']


def test_selected_chat_denial_correlation_reaches_http_without_becoming_usage(runtime):
    app, client, gate, actor = runtime
    select(client)
    response = client.post('/api/ai/chat', json={'message':'private-input', 'external_approval':{'confirmed':True}})
    event = gate.get_audit_log()[-1]
    assert response.json['code'] == 'USER_API_CONFIRMATION_INVALID'
    assert response.json['audit_id'] == event['audit_id']
    assert response.json['usage'] is None


def test_settings_get_and_direct_chat_sanitize_dynamic_identity_failure(runtime, monkeypatch):
    from lumenis.auth import service as auth
    app, client, gate, actor = runtime
    def broken(**kwargs):
        raise ValueError('synthetic-get-identity-secret')
    monkeypatch.setattr(auth, 'get_current_user', broken)
    response = client.get('/api/settings/ai')
    assert response.status_code == 503 and response.json['code'] == 'USER_API_SETTINGS_UNAVAILABLE'
    assert 'synthetic-get-identity-secret' not in repr(response.json)
    def prefixed(**kwargs):
        raise PermissionError('USER_API_SYNTHETIC_PRIVATE_SECRET')
    monkeypatch.setattr(auth, 'get_current_user', prefixed)
    with app.test_request_context('/'):
        result = adapter.chat('s', 'u', external_user_input=True)
    assert result[1] == 'user_api_permission_unavailable'
    assert 'SYNTHETIC_PRIVATE_SECRET' not in repr(gate.get_audit_log())
    assert 'synthetic_private_secret' not in repr(result)
