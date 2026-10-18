"""Source-record admission races over disposable SQLite, not platform execution."""
import json
import pytest

from tests.test_saved_document_workflow import workspace
from tests.test_kos_input_compatibility import kos_compat, post


def draft(kos_compat, *, author='race-author', key='source-atomic-draft'):
    response = post(kos_compat, 'cooperation', {'author_id': author, 'quote': 10,
        'budget': None, 'request_id': key}, approve=True)
    assert response.status_code == 200, response.get_json()
    return response.get_json()['operation']


def scope():
    return {'domain_id': 'zbmp', 'subject_id': None, 'brand_focus_id': 'COMPAT-B1', 'global_scope': False}


def pending_confirmation(kos_compat, source):
    body = {'operation_record_id': source['record_id'], 'request_id': 'atomic-source-confirm'}
    pending = post(kos_compat, 'cooperation/confirm', body)
    assert pending.status_code == 403 and pending.get_json()['requires_approval']
    _, ws, _ = kos_compat
    token = ws['gate'].grant_approval('db_write', resource=pending.get_json()['resource'], granted_by='isolated-test')
    return body, token


def assert_no_executions(ws):
    with ws['repo'].connection(read_only=True) as con:
        table = con.execute("SELECT 1 FROM sqlite_master WHERE name='kos_executions'").fetchone()
        assert table is None or con.execute('SELECT COUNT(*) FROM kos_executions').fetchone()[0] == 0


def test_source_revised_after_route_resolution_is_rejected_atomically(kos_compat, monkeypatch):
    import kos_execution
    import kos_ops
    source = draft(kos_compat)
    body, _ = pending_confirmation(kos_compat, source)
    _, ws, _ = kos_compat
    original = kos_execution.create_scoped_execution
    observed = []
    def revise_before_create(**kwargs):
        # This commits through the real owner after the route read, before BEGIN.
        revision = dict(actor=kwargs['actor'], scope=kwargs['scope'], author_id='race-author',
            operation='cooperation', payload={'quote': 20, 'budget': None},
            request_id='source-race-new-version', expected_version=1)
        resource = kos_ops.scoped_operation_resource(**revision)
        ws['gate'].grant_approval('db_write', resource=resource, granted_by='isolated-test')
        observed.append(kos_ops.write_scoped_operation(**revision)['operation'])
        return original(**kwargs)
    monkeypatch.setattr(kos_execution, 'create_scoped_execution', revise_before_create)
    response = post(kos_compat, 'cooperation/confirm', body)
    assert len(observed) == 1 and observed[0]['version'] == 2
    assert response.status_code == 400, response.get_json()
    assert response.get_json()['code'] == 'KOS_PLAN_VERSION_SUPERSEDED'
    assert_no_executions(ws)


def test_source_validation_uses_execution_write_transaction_and_preserves_source(kos_compat, monkeypatch):
    import sqlite3
    import kos_ops
    import kos_execution
    source = draft(kos_compat)
    body, _ = pending_confirmation(kos_compat, source)
    _, ws, _ = kos_compat
    with ws['repo'].connection(read_only=True) as con:
        original_note = con.execute('SELECT note FROM kos_operations WHERE id=?', (source['record_id'],)).fetchone()[0]
    original_resolve = kos_ops.resolve_scoped_operation_record
    original_conn = kos_execution._conn
    connections, checks = [], []
    def capture_connection():
        con = original_conn()
        connections.append(con)
        return con
    def validate_under_lock(**kwargs):
        con = kwargs.get('connection')
        if con is not None:
            assert connections and con is connections[-1] and con.in_transaction
            competitor = ws['repo'].connect(timeout=0)
            try:
                competitor.execute('PRAGMA busy_timeout=0')
                with pytest.raises(sqlite3.OperationalError, match='locked'):
                    competitor.execute('BEGIN IMMEDIATE')
            finally:
                competitor.close()
            checks.append(True)
        return original_resolve(**kwargs)
    monkeypatch.setattr(kos_execution, '_conn', capture_connection)
    monkeypatch.setattr(kos_ops, 'resolve_scoped_operation_record', validate_under_lock)
    response = post(kos_compat, 'cooperation/confirm', body)
    assert response.status_code == 200, response.get_json()
    assert checks == [True]
    execution = response.get_json()['execution']
    assert execution['status'] == 'AI_GENERATED' and execution['approved_at'] is None
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute('SELECT note FROM kos_operations WHERE id=?', (source['record_id'],)).fetchone()[0] == original_note
        assert con.execute('SELECT COUNT(*) FROM kos_operations').fetchone()[0] == 1


def test_source_tampered_after_route_resolution_creates_no_execution(kos_compat, monkeypatch):
    import kos_execution
    source = draft(kos_compat)
    body, _ = pending_confirmation(kos_compat, source)
    _, ws, _ = kos_compat
    original = kos_execution.create_scoped_execution
    def tamper_before_create(**kwargs):
        with ws['repo'].transaction() as con:
            con.execute("UPDATE kos_operations SET note=replace(note, '\"quote\":10', '\"quote\":11') WHERE id=?",
                        (source['record_id'],))
        return original(**kwargs)
    monkeypatch.setattr(kos_execution, 'create_scoped_execution', tamper_before_create)
    response = post(kos_compat, 'cooperation/confirm', body)
    assert response.status_code == 400 and response.get_json()['code'] == 'KOS_OPERATION_INTEGRITY_FAILED'
    assert_no_executions(ws)


@pytest.mark.parametrize('mutation,code', [
    ('hash', 'KOS_PLAN_SOURCE_HASH_MISMATCH'),
    ('version', 'KOS_PLAN_SOURCE_VERSION_MISMATCH'),
    ('version_bool', 'KOS_PLAN_BINDING_INVALID'),
    ('content', 'KOS_EXECUTION_PAYLOAD_CONFLICT'),
    ('content_bool', 'KOS_EXECUTION_PAYLOAD_CONFLICT'),
    ('author', 'KOS_PLAN_AUTHOR_MISMATCH'),
    ('action', 'KOS_PLAN_ACTION_MISMATCH'),
    ('incomplete', 'KOS_PLAN_BINDING_INVALID'),
    ('extra', 'KOS_PLAN_BINDING_INVALID'),
    ('missing_record', 'KOS_PLAN_NOT_FOUND_IN_SCOPE'),
])
def test_owner_rejects_mismatched_binding_even_with_exact_creation_approval(kos_compat, mutation, code):
    import kos_execution
    import kos_ops
    source = draft(kos_compat)
    _, ws, _ = kos_compat
    payload = {'private_plan': source['payload'], 'source_record_id': source['record_id'],
               'source_sha256': source['sha256']}
    args = dict(actor=ws['actor'], scope=scope(), action_type='cooperation_confirm',
                target_author_id='race-author', payload=payload, request_id='source-owner-validation',
                expected_source_version=source['version'])
    if mutation == 'hash':
        payload['source_sha256'] = '0' * 64
    elif mutation == 'version':
        args['expected_source_version'] = 2
    elif mutation == 'version_bool':
        args['expected_source_version'] = True
    elif mutation == 'content':
        payload['private_plan'] = {'quote': 11, 'budget': None}
    elif mutation == 'content_bool':
        payload['private_plan'] = {'quote': 10, 'budget': False}
    elif mutation == 'author':
        args['target_author_id'] = 'other-author'
    elif mutation == 'action':
        args['action_type'] = 'paid_media'
    elif mutation == 'incomplete':
        payload.pop('source_sha256')
    elif mutation == 'extra':
        payload['unbound_override'] = 'not-approved-by-source'
    elif mutation == 'missing_record':
        payload['source_record_id'] = 1000000
    with pytest.raises(kos_ops.ScopedOperationApprovalRequired) as needed:
        kos_execution.create_scoped_execution(**args)
    ws['gate'].grant_approval('db_write', resource=needed.value.resource, granted_by='isolated-test')
    with pytest.raises((ValueError, PermissionError), match=code):
        kos_execution.create_scoped_execution(**args)
    assert_no_executions(ws)


def test_source_bound_creation_rolls_back_when_approval_revoked_inside_transaction(kos_compat, monkeypatch):
    import kos_ops
    source = draft(kos_compat)
    body, token = pending_confirmation(kos_compat, source)
    _, ws, _ = kos_compat
    original = kos_ops.resolve_scoped_operation_record
    revoked = []
    def revoke_after_validation(**kwargs):
        result = original(**kwargs)
        if kwargs.get('connection') is not None:
            assert kwargs['connection'].in_transaction
            ws['gate'].revoke_approval(token)
            revoked.append(True)
        return result
    monkeypatch.setattr(kos_ops, 'resolve_scoped_operation_record', revoke_after_validation)
    response = post(kos_compat, 'cooperation/confirm', body)
    assert revoked == [True]
    assert response.status_code == 403 and response.get_json()['requires_approval']
    assert_no_executions(ws)


def test_source_bound_v1_replay_retains_existing_human_approval(kos_compat):
    source = draft(kos_compat)
    body, _ = pending_confirmation(kos_compat, source)
    response = post(kos_compat, 'cooperation/confirm', body)
    assert response.status_code == 200, response.get_json()
    first = response.get_json()['execution']
    request = json.loads(first['payload'])['request']
    # The existing v1 request shape and approval hash remain compatible.
    assert set(request['payload']) == {'private_plan', 'source_record_id', 'source_sha256'}
    path = 'execution/' + first['execution_id'] + '/transition'
    for state in ('PENDING_HUMAN_REVIEW', 'HUMAN_APPROVED'):
        response = post(kos_compat, path, {'status': state}, approve=True)
        assert response.status_code == 200, response.get_json()
    approved = response.get_json()['execution']
    replay = post(kos_compat, 'cooperation/confirm', body)
    assert replay.status_code == 200 and replay.get_json()['replayed']
    assert replay.get_json()['execution']['status'] == 'HUMAN_APPROVED'
    assert replay.get_json()['execution']['approved_at'] == approved['approved_at']
    assert json.loads(replay.get_json()['execution']['payload'])['request'] == request


def test_legacy_v1_source_wrapper_without_explicit_version_still_validates(kos_compat):
    import kos_execution
    import kos_ops
    source = draft(kos_compat)
    _, ws, _ = kos_compat
    args = dict(actor=ws['actor'], scope=scope(), action_type='cooperation_confirm', target_author_id='race-author',
        payload={'private_plan': source['payload'], 'source_record_id': source['record_id'], 'source_sha256': source['sha256']},
        request_id='legacy-versioned-source-wrapper')
    with pytest.raises(kos_ops.ScopedOperationApprovalRequired) as needed:
        kos_execution.create_scoped_execution(**args)
    ws['gate'].grant_approval('db_write', resource=needed.value.resource, granted_by='isolated-test')
    result = kos_execution.create_scoped_execution(**args)
    assert result['ok'] and result['execution']['status'] == 'AI_GENERATED'


def test_source_removal_after_route_resolution_creates_no_execution(kos_compat, monkeypatch):
    import kos_execution
    source = draft(kos_compat)
    body, _ = pending_confirmation(kos_compat, source)
    _, ws, _ = kos_compat
    original = kos_execution.create_scoped_execution
    def remove_before_create(**kwargs):
        # Only this disposable fixture is deleted; no production DB is used.
        with ws['repo'].transaction() as con:
            con.execute('DELETE FROM kos_operations WHERE id=?', (source['record_id'],))
        return original(**kwargs)
    monkeypatch.setattr(kos_execution, 'create_scoped_execution', remove_before_create)
    response = post(kos_compat, 'cooperation/confirm', body)
    assert response.status_code == 403 and response.get_json()['code'] == 'KOS_PLAN_NOT_FOUND_IN_SCOPE'
    assert_no_executions(ws)


def test_source_owner_rejects_other_brand_even_with_creation_approval(kos_compat):
    import kos_execution
    import kos_ops
    source = draft(kos_compat)
    _, ws, _ = kos_compat
    args = dict(actor=ws['actor'], scope={**scope(), 'brand_focus_id': 'COMPAT-B2'},
        action_type='cooperation_confirm', target_author_id='race-author',
        payload={'private_plan': source['payload'], 'source_record_id': source['record_id'],
                 'source_sha256': source['sha256']},
        request_id='source-cross-brand-owner', expected_source_version=1)
    with pytest.raises(kos_ops.ScopedOperationApprovalRequired) as needed:
        kos_execution.create_scoped_execution(**args)
    ws['gate'].grant_approval('db_write', resource=needed.value.resource, granted_by='isolated-test')
    with pytest.raises(PermissionError, match='KOS_PLAN_NOT_FOUND_IN_SCOPE'):
        kos_execution.create_scoped_execution(**args)
    assert_no_executions(ws)
