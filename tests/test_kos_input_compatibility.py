"""Isolated HTTP/SQLite regressions; synthetic fixtures, no platform execution."""
import json
import pytest

from tests.test_saved_document_workflow import workspace


@pytest.fixture
def kos_compat(workspace):
    import kos_routes
    import subject_registry
    ws = workspace
    ws['app'].register_blueprint(kos_routes.kos_bp)
    with ws['repo'].transaction() as con:
        subject_registry.ensure_schema(con)
        for number in (1, 2):
            con.execute('''INSERT INTO lumenis_subject_registry
                (subject_id, brand_focus_id, domain_id, subject_type, name_en,
                 name_zh, name_en_norm, name_zh_norm, created_at, updated_at, status)
                VALUES (?, ?, 'BMP', 'brand', ?, ?, ?, ?, 'now', 'now', 'active')''',
                (f'COMPAT-S{number}', f'COMPAT-B{number}', f'Brand{number}',
                 f'品牌{number}', f'brand{number}', f'品牌{number}'))
    headers = {'Host': 'localhost', 'X-Domain-Id': 'BMP',
               'X-Lumenis-Context-Mode': 'FOCUS', 'X-Brand-Focus-ID': 'COMPAT-B1'}
    return ws['app'].test_client(), ws, headers


def post(kos_compat, path, body, *, headers=None, approve=False):
    client, ws, default_headers = kos_compat
    response = client.post('/api/kos/' + path, json=body, headers=headers or default_headers)
    if approve:
        result = response.get_json()
        assert response.status_code == 403 and result.get('requires_approval'), result
        ws['gate'].grant_approval('db_write', resource=result['resource'], granted_by='isolated-test-user')
        response = client.post('/api/kos/' + path, json=body, headers=headers or default_headers)
    return response


def test_manual_legacy_kos_id_maps_to_author_without_zero(kos_compat):
    result = post(kos_compat, 'manual', {'kos_id': 'same-author', 'sales_amount': None,
        'wecom_add': 0, 'request_id': 'compat-manual-001'}, approve=True)
    assert result.status_code == 200, result.get_json()
    operation = result.get_json()['operation']
    assert operation['author_id'] == 'same-author'
    assert operation['payload'] == {'sales_amount': None, 'wecom_add': 0}
    assert operation['external_effect'] == 'not_performed'
    conflict = post(kos_compat, 'manual', {'kos_id': 'one', 'author_id': 'two', 'wecom_add': 1})
    assert conflict.status_code == 400 and conflict.get_json()['code'] == 'KOS_AUTHOR_ID_CONFLICT'


def test_cooperation_top_level_quote_budget_preserves_exact_approval(kos_compat):
    body = {'author_id': 'same-author', 'quote': 10, 'budget': None, 'request_id': 'compat-confirm-001'}
    response = post(kos_compat, 'cooperation/confirm', body, approve=True)
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    execution = result['execution']
    assert execution['status'] == 'AI_GENERATED' and execution['approved_at'] is None
    assert json.loads(execution['payload'])['request']['payload'] == {'quote': 10, 'budget': None}
    changed = post(kos_compat, 'cooperation/confirm', {**body, 'quote': 11})
    assert changed.status_code == 403 and changed.get_json()['requires_approval']
    bad = post(kos_compat, 'cooperation/confirm', {**body, 'payload': {'quote': 12}})
    assert bad.status_code == 400 and bad.get_json()['code'] == 'KOS_EXECUTION_PAYLOAD_CONFLICT'
    forged = post(kos_compat, 'cooperation/confirm', {**body, 'confirmed_by': 'owner'})
    assert forged.status_code == 400


def test_paid_result_can_resolve_plan_without_author_and_reject_conflict(kos_compat):
    plan = post(kos_compat, 'paid/plan', {'author_id': 'same-author', 'budget': 30,
        'request_id': 'compat-paid-plan-001'}, approve=True)
    assert plan.status_code == 200, plan.get_json()
    plan_id = plan.get_json()['operation']['plan_id']
    response = post(kos_compat, 'paid/result', {'plan_id': plan_id, 'spend': None, 'clicks': 0,
        'request_id': 'compat-paid-result-001'}, approve=True)
    assert response.status_code == 200, response.get_json()
    operation = response.get_json()['operation']
    assert operation['author_id'] == 'same-author'
    assert operation['payload']['spend'] is None and operation['payload']['clicks'] == 0
    assert operation['plan_binding']['source_sha256'] == plan.get_json()['operation']['sha256']
    assert operation['factual_verification'] == 'NOT_ESTABLISHED'
    conflict = post(kos_compat, 'paid/result', {'plan_id': plan_id, 'author_id': 'other', 'spend': 1})
    assert conflict.status_code == 400 and conflict.get_json()['code'] == 'KOS_PLAN_AUTHOR_MISMATCH'
    foreign = post(kos_compat, 'paid/result', {'plan_id': plan_id, 'spend': 1},
        headers={**kos_compat[2], 'X-Brand-Focus-ID': 'COMPAT-B2'})
    assert foreign.status_code == 403
    legacy = post(kos_compat, 'paid/result', {'plan_id': 'PAID-historical-unscoped', 'spend': 1})
    assert legacy.status_code == 400 and legacy.get_json()['code'] == 'KOS_LEGACY_PLAN_REQUIRES_SCOPED_RECREATION'


@pytest.mark.parametrize('body,code', [
    ({'author_id': 'a', 'kos_id': 'b', 'wecom_add': 1}, 'KOS_AUTHOR_ID_CONFLICT'),
    ({'kos_id': None, 'wecom_add': 1}, 'AUTHOR_ID_REQUIRED'),
    ({'kos_id': ' ', 'wecom_add': 1}, 'AUTHOR_ID_REQUIRED'),
    ({'kos_id': True, 'wecom_add': 1}, 'AUTHOR_ID_REQUIRED'),
    ({'kos_id': 'a', 'wecom_add': False}, 'KOS_OPERATION_NUMBER_INVALID'),
    ({'kos_id': 'a', 'wecom_add': -1}, 'KOS_OPERATION_NUMBER_INVALID'),
    ({'kos_id': 'a', 'wecom_add': 1, 'confirmed_by': 'owner'}, 'KOS_OPERATION_FIELDS_INVALID'),
])
def test_manual_invalid_aliases_and_payload_are_rejected(kos_compat, body, code):
    response = post(kos_compat, 'manual', body)
    assert response.status_code == 400 and response.get_json()['code'] == code
    _, ws, _ = kos_compat
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute("SELECT 1 FROM sqlite_master WHERE name='kos_operations'").fetchone() is None


@pytest.mark.parametrize('body,code', [
    ({'author_id': 'a', 'target_author_id': 'b'}, 'KOS_AUTHOR_ID_CONFLICT'),
    ({'author_id': 'a', 'quote': -1}, 'KOS_OPERATION_NUMBER_INVALID'),
    ({'author_id': 'a', 'quote': True}, 'KOS_OPERATION_NUMBER_INVALID'),
    ({'author_id': 'a', 'quote': 1, 'payload': {'quote': True}}, 'KOS_OPERATION_NUMBER_INVALID'),
    ({'author_id': 'a', 'budget': float('inf')}, 'KOS_OPERATION_NUMBER_INVALID'),
    ({'author_id': 'a', 'payload': []}, 'KOS_EXECUTION_PAYLOAD_INVALID'),
    ({'author_id': 'a', 'action_type': 'paid_media'}, 'KOS_PLAN_ACTION_MISMATCH'),
])
def test_cooperation_conflicts_and_invalid_numbers(kos_compat, body, code):
    response = post(kos_compat, 'cooperation/confirm', body)
    assert response.status_code == 400 and response.get_json()['code'] == code


def test_manual_alias_replay_and_scope_approval_are_identical(kos_compat):
    body = {'kos_id': 'same-author', 'inquiry': None, 'request_id': 'manual-alias-replay'}
    first = post(kos_compat, 'manual', body, approve=True).get_json()
    canonical = {key: value for key, value in body.items() if key != 'kos_id'}
    canonical['author_id'] = 'same-author'
    response = post(kos_compat, 'manual', canonical)
    assert response.status_code == 200 and response.get_json()['replayed']
    assert response.get_json()['operation'] == first['operation']
    different = post(kos_compat, 'manual', body,
        headers={**kos_compat[2], 'X-Brand-Focus-ID': 'COMPAT-B2'})
    assert different.status_code == 403 and different.get_json()['requires_approval']
    assert different.get_json()['resource'] != first['operation']['resource']
    missing_scope = post(kos_compat, 'manual', body, headers={'Host': 'localhost'})
    assert missing_scope.status_code == 400


def test_cooperation_replay_does_not_overwrite_human_approval(kos_compat):
    body = {'kos_id': 'same-author', 'quote': 0, 'request_id': 'cooperation-replay'}
    execution = post(kos_compat, 'cooperation/confirm', body, approve=True).get_json()['execution']
    path = 'execution/' + execution['execution_id'] + '/transition'
    for state in ('PENDING_HUMAN_REVIEW', 'HUMAN_APPROVED'):
        response = post(kos_compat, path, {'status': state}, approve=True)
        assert response.status_code == 200, response.get_json()
    approved = response.get_json()['execution']
    replay = post(kos_compat, 'cooperation/confirm', body).get_json()
    assert replay['replayed'] and replay['execution']['status'] == 'HUMAN_APPROVED'
    assert replay['execution']['approved_at'] == approved['approved_at']
    denied = post(kos_compat, 'cooperation/execute', {'execution_id': execution['execution_id']})
    assert denied.status_code == 409 and denied.get_json()['code'] == 'KOS_CHANNEL_NOT_CONFIGURED'
    assert denied.get_json()['execution']['status'] == 'HUMAN_APPROVED'


def test_cooperation_record_derives_exact_author_and_cannot_override(kos_compat):
    draft = post(kos_compat, 'cooperation', {'author_id': 'same-author', 'quote': 10,
        'budget': None, 'request_id': 'cooperation-record'}, approve=True).get_json()['operation']
    body = {'operation_record_id': draft['record_id'], 'request_id': 'cooperation-record-confirm'}
    response = post(kos_compat, 'cooperation/confirm', body, approve=True)
    assert response.status_code == 200, response.get_json()
    execution = response.get_json()['execution']
    request = json.loads(execution['payload'])['request']
    assert request['target_author_id'] == 'same-author'
    assert request['payload']['private_plan'] == draft['payload']
    alias_replay = post(kos_compat, 'cooperation/confirm', {**body, 'quote': 10})
    assert alias_replay.status_code == 200 and alias_replay.get_json()['replayed']
    conflict = post(kos_compat, 'cooperation/confirm', {**body, 'author_id': 'other'})
    assert conflict.status_code == 400 and conflict.get_json()['code'] == 'KOS_PLAN_AUTHOR_MISMATCH'
    override = post(kos_compat, 'cooperation/confirm', {**body, 'quote': 20})
    assert override.status_code == 400 and override.get_json()['code'] == 'KOS_EXECUTION_PAYLOAD_CONFLICT'
    foreign = post(kos_compat, 'cooperation/confirm', body,
        headers={**kos_compat[2], 'X-Brand-Focus-ID': 'COMPAT-B2'})
    assert foreign.status_code == 403 and foreign.get_json()['code'] == 'KOS_PLAN_NOT_FOUND_IN_SCOPE'


def test_paid_result_resolves_scoped_execution_and_rejects_wrong_action(kos_compat):
    body = {'target_author_id': 'same-author', 'action_type': 'paid_media',
            'payload': {'budget': 25}, 'request_id': 'paid-scoped-execution'}
    plan = post(kos_compat, 'execution', body, approve=True).get_json()['execution']
    response = post(kos_compat, 'paid/result', {'plan_id': plan['execution_id'], 'spend': 0,
        'request_id': 'paid-execution-result'}, approve=True)
    assert response.status_code == 200, response.get_json()
    operation = response.get_json()['operation']
    assert operation['author_id'] == 'same-author'
    assert operation['plan_binding']['source_execution_id'] == plan['execution_id']
    assert operation['external_effect'] == 'not_performed'
    assert 'roi' not in operation['payload']
    wrong = post(kos_compat, 'execution', {**body, 'action_type': 'reward_issue',
        'request_id': 'wrong-action-execution'}, approve=True).get_json()['execution']
    response = post(kos_compat, 'paid/result', {'plan_id': wrong['execution_id'], 'spend': 1})
    assert response.status_code == 400 and response.get_json()['code'] == 'KOS_PLAN_ACTION_OR_TARGET_MISMATCH'
    foreign = post(kos_compat, 'paid/result', {'plan_id': plan['execution_id'], 'spend': 1},
        headers={**kos_compat[2], 'X-Brand-Focus-ID': 'COMPAT-B2'})
    assert foreign.status_code == 403


def test_paid_result_rejects_tamper_and_revoked_approval(kos_compat):
    _, ws, _ = kos_compat
    plan = post(kos_compat, 'paid/plan', {'author_id': 'same-author', 'budget': 25,
        'request_id': 'paid-plan-security'}, approve=True).get_json()['operation']
    body = {'plan_id': plan['plan_id'], 'spend': 2, 'request_id': 'paid-result-security'}
    pending = post(kos_compat, 'paid/result', body).get_json()
    token = ws['gate'].grant_approval('db_write', resource=pending['resource'], granted_by='isolated-test')
    ws['gate'].revoke_approval(token)
    response = post(kos_compat, 'paid/result', body)
    assert response.status_code == 403 and response.get_json()['requires_approval']
    with ws['repo'].transaction() as con:
        con.execute("UPDATE kos_operations SET note=replace(note, '\"budget\":25', '\"budget\":26') WHERE id=?",
                    (plan['record_id'],))
    response = post(kos_compat, 'paid/result', body)
    assert response.status_code == 400 and response.get_json()['code'] == 'KOS_OPERATION_INTEGRITY_FAILED'


def test_paid_result_owner_rejects_unbound_plan_even_with_author(kos_compat):
    import kos_ops
    _, ws, _ = kos_compat
    scope = {'domain_id': 'zbmp', 'subject_id': None, 'brand_focus_id': 'COMPAT-B1', 'global_scope': False}
    args = dict(actor=ws['actor'], scope=scope, author_id='same-author', operation='paid_result',
                payload={'plan_id': 'PAID-legacy', 'spend': 10}, request_id='direct-unbound-result')
    for call in (kos_ops.scoped_operation_resource, kos_ops.write_scoped_operation):
        with pytest.raises(ValueError, match='KOS_LEGACY_PLAN_REQUIRES_SCOPED_RECREATION'):
            call(**args)


def test_superseded_private_plan_rejected_and_new_version_has_new_id(kos_compat):
    body = {'author_id': 'same-author', 'budget': 10, 'request_id': 'plan-first-version'}
    first = post(kos_compat, 'paid/plan', body, approve=True).get_json()
    second = post(kos_compat, 'paid/plan', {**body, 'budget': 20, 'request_id': 'plan-second-version',
        'expected_version': 1}, approve=True).get_json()
    assert first['plan_id'] != second['plan_id']
    response = post(kos_compat, 'paid/result', {'plan_id': first['plan_id'], 'spend': 1})
    assert response.status_code == 400 and response.get_json()['code'] == 'KOS_PLAN_VERSION_SUPERSEDED'
    response = post(kos_compat, 'paid/result', {'plan_id': second['plan_id'], 'spend': 1,
        'request_id': 'plan-second-result'}, approve=True)
    assert response.status_code == 200, response.get_json()


def test_optional_empty_author_keeps_legacy_list_behavior(kos_compat):
    client, _, headers = kos_compat
    response = client.get('/api/kos/paid/plans?author_id=', headers=headers)
    assert response.status_code == 200 and response.get_json()['items'] == []


def test_paid_plan_reference_does_not_cross_actor(kos_compat):
    from tests.test_bmp09_request_binding import accounts
    _, ws, headers = kos_compat
    one, two = accounts(ws)
    first_headers = {**headers, **one}
    second_headers = {**headers, **two, 'X-Actor-ID': '1'}
    plan = post(kos_compat, 'paid/plan', {'author_id': 'same-author', 'budget': 10,
        'request_id': 'account-one-plan'}, headers=first_headers, approve=True)
    assert plan.status_code == 200, plan.get_json()
    plan_id = plan.get_json()['plan_id']
    denied = post(kos_compat, 'paid/result', {'plan_id': plan_id, 'spend': 1}, headers=second_headers)
    assert denied.status_code == 403 and denied.get_json()['code'] == 'KOS_PLAN_NOT_FOUND_IN_SCOPE'
    allowed = post(kos_compat, 'paid/result', {'plan_id': plan_id, 'spend': 1,
        'request_id': 'account-one-result'}, headers=first_headers, approve=True)
    assert allowed.status_code == 200, allowed.get_json()
    ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    denied = post(kos_compat, 'paid/result', {'plan_id': plan_id, 'spend': 1}, headers=first_headers)
    assert denied.status_code == 403


def test_paid_result_rechecks_binding_inside_write_transaction(kos_compat, monkeypatch):
    import kos_ops
    _, ws, _ = kos_compat
    plan = post(kos_compat, 'paid/plan', {'author_id': 'same-author', 'budget': 10,
        'request_id': 'race-plan-version'}, approve=True).get_json()['operation']
    scope = {'domain_id': 'zbmp', 'subject_id': None, 'brand_focus_id': 'COMPAT-B1', 'global_scope': False}
    args = dict(actor=ws['actor'], scope=scope, author_id='same-author', operation='paid_result',
                payload={'plan_id': plan['plan_id'], 'spend': 1}, request_id='race-plan-result')
    resource = kos_ops.scoped_operation_resource(**args)
    ws['gate'].grant_approval('db_write', resource=resource, granted_by='isolated-test')
    original = kos_ops._bind_paid_result
    def changed_at_commit(**kwargs):
        binding = original(**kwargs)
        if kwargs.get('connection') is not None:
            binding = {**binding, 'source_sha256': 'changed-after-approval'}
        return binding
    monkeypatch.setattr(kos_ops, '_bind_paid_result', changed_at_commit)
    with pytest.raises(ValueError, match='KOS_PLAN_BINDING_CHANGED'):
        kos_ops.write_scoped_operation(**args)
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM kos_operations WHERE action='scoped_paid_result'").fetchone()[0] == 0


def test_reference_resolution_fails_explicitly_on_history_budget(kos_compat, monkeypatch):
    import kos_ops
    first = post(kos_compat, 'paid/plan', {'author_id': 'first-author', 'budget': 10,
        'request_id': 'history-first-plan'}, approve=True).get_json()
    post(kos_compat, 'paid/plan', {'author_id': 'second-author', 'budget': 10,
        'request_id': 'history-second-plan'}, approve=True)
    monkeypatch.setattr(kos_ops, '_SCOPED_HISTORY_MAX_ROWS', 1)
    response = post(kos_compat, 'paid/result', {'plan_id': first['plan_id'], 'spend': 1})
    assert response.status_code == 503 and response.get_json()['code'] == 'KOS_OPERATION_HISTORY_RESOURCE_LIMIT'


def test_loopback_http_all_three_compatibility_paths(kos_compat):
    """Real local HTTP transport over a disposable SQLite DB; no platform calls."""
    import os
    import threading
    import urllib.error
    import urllib.request
    from pathlib import Path
    from werkzeug.serving import make_server
    _, ws, headers = kos_compat
    server = make_server('127.0.0.1', 0, ws['app'])
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    receipts = []
    def invoke(path, payload, *, approve=False):
        def attempt():
            request = urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/kos/{path}',
                data=json.dumps(payload).encode(), headers={**headers, 'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    status, value = response.status, json.load(response)
            except urllib.error.HTTPError as response:
                status, value = response.code, json.load(response)
            receipts.append({'path': path, 'status': status, 'code': value.get('code'),
                'external_effect': value.get('external_effect'), 'replayed': value.get('replayed')})
            return status, value
        status, value = attempt()
        if approve:
            assert status == 403 and value['requires_approval']
            ws['gate'].grant_approval('db_write', resource=value['resource'], granted_by='isolated-loopback-test')
            status, value = attempt()
        return status, value
    try:
        assert invoke('manual', {'kos_id': 'loopback-author', 'wecom_add': 0, 'sales_amount': None,
            'request_id': 'loopback-manual-001'}, approve=True)[0] == 200
        status, cooperation = invoke('cooperation/confirm', {'author_id': 'loopback-author',
            'quote': 12, 'budget': None, 'request_id': 'loopback-cooperation'}, approve=True)
        assert status == 200 and cooperation['execution']['status'] == 'AI_GENERATED'
        status, plan = invoke('paid/plan', {'author_id': 'loopback-author', 'budget': 12,
            'request_id': 'loopback-paid-plan'}, approve=True)
        assert status == 200
        body = {'plan_id': plan['plan_id'], 'spend': None, 'clicks': 0, 'request_id': 'loopback-paid-result'}
        status, result = invoke('paid/result', body, approve=True)
        assert status == 200 and result['operation']['author_id'] == 'loopback-author'
        assert invoke('paid/result', body)[1]['replayed']
        assert invoke('manual', {'author_id': 'one', 'kos_id': 'other', 'clicks': 0})[0] == 400
        assert invoke('paid/result', {**body, 'author_id': 'other'})[0] == 400
        assert invoke('cooperation/confirm', {'author_id': 'loopback-author', 'confirmed_by': 'forged'})[0] == 400
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()
        assert not thread.is_alive()
    if os.environ.get('LUMENIS_KOS_COMPAT_RESULTS'):
        Path(os.environ['LUMENIS_KOS_COMPAT_RESULTS'], 'loopback-http-receipts.json').write_text(json.dumps(receipts, indent=2))
