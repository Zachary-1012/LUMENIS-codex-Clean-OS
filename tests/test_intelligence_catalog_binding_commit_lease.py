"""Exact catalog-binding approval lifetime and withdrawal serialization."""
from datetime import datetime, timedelta
import hashlib
import json
import sqlite3
import threading

import pytest

from lumenis.system.security import permission as p


CALLER = json.dumps({'actor_id': 1, 'domain_id': 'cth', 'subject_id': 'subject-a',
                     'brand_focus_id': None, 'global_scope': False}, sort_keys=True, separators=(',', ':'))
RESOURCE = 'intelligence-asset-bind:v1:' + hashlib.sha256(b'exact synthetic actor/source/catalog snapshot').hexdigest()


@pytest.fixture
def gate(monkeypatch):
    monkeypatch.delenv('PERMISSION_GATE_TESTING', raising=False)
    monkeypatch.setattr(p, '_TESTING_BYPASS_ENABLED', False)
    value = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT, p.PermissionLevel.HUMAN_APPROVAL})
    monkeypatch.setattr(p, '_default_gate', value)
    return value


def _token(gate, **changes):
    args = {'operation': p.OperationType.DATA_IMPORT.value, 'resource': RESOURCE, 'granted_by': CALLER}
    args.update(changes)
    return gate.grant_approval(**args)


def _lease(gate, token, **changes):
    args = {'resource': RESOURCE, 'caller': CALLER}
    args.update(changes)
    return gate.intelligence_catalog_binding_commit_lease(token, **args)


@pytest.mark.parametrize('changes', [
    {'operation': '*'}, {'operation': p.OperationType.CONFIG_MODIFY.value},
    {'operation': p.OperationType.REPORT_REVIEW.value}, {'resource': None},
    {'resource': RESOURCE + '0'}, {'resource': 'content-review:v1:' + 'a' * 64},
    {'granted_by': 'actor:2'},
])
def test_cannot_borrow_wildcard_other_purpose_scope_or_actor_approval(gate, changes):
    token = _token(gate, **changes)
    with pytest.raises(PermissionError):
        with _lease(gate, token):
            pytest.fail('must not enter commit section')


@pytest.mark.parametrize('changes', [
    {'resource': 'content-review:v1:' + 'a' * 64}, {'resource': RESOURCE + 'x'},
    {'resource': 'intelligence-asset-bind:v1:' + 'A' * 64}, {'resource': None},
    {'caller': ''}, {'caller': None}, {'caller': 'x' * 4097},
])
def test_malformed_binding_is_rejected(gate, changes):
    with pytest.raises(PermissionError):
        with _lease(gate, _token(gate), **changes):
            pytest.fail('must not enter commit section')


@pytest.mark.parametrize('invalid', ['missing', 'revoked', 'expired', 'no_audit', 'commit', 'human', 'permissive', 'bypass', 'foreign_gate'])
def test_lease_requires_current_exact_audited_unexpired_authority(gate, monkeypatch, invalid):
    token = _token(gate)
    if invalid == 'missing': token = 'missing'
    elif invalid == 'revoked': gate.revoke_approval(token)
    elif invalid == 'expired': gate._approvals[token].expires_at = datetime.now() - timedelta(seconds=1)
    elif invalid == 'no_audit': gate._approvals[token].issuance_audit_id = None
    elif invalid == 'commit': gate.revoke_permission(p.PermissionLevel.COMMIT)
    elif invalid == 'human': gate.revoke_permission(p.PermissionLevel.HUMAN_APPROVAL)
    elif invalid == 'permissive': gate.fail_closed = False
    elif invalid == 'bypass': monkeypatch.setattr(p, '_TESTING_BYPASS_ENABLED', True)
    elif invalid == 'foreign_gate': monkeypatch.setattr(p, '_default_gate', p.PermissionGate())
    with pytest.raises(PermissionError):
        with _lease(gate, token):
            pytest.fail('must not enter commit section')


def test_expiry_during_final_material_validation_rolls_back_sqlite(gate, tmp_path):
    path = tmp_path / 'catalog.sqlite'
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE binding (value TEXT)')
    token = _token(gate)
    with pytest.raises(PermissionError, match='APPROVAL_REVOKED'):
        with sqlite3.connect(path) as connection:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute("INSERT INTO binding VALUES ('synthetic signed material')")
            with _lease(gate, token) as require_current:
                gate._approvals[token].expires_at = datetime.now() - timedelta(seconds=1)
                require_current()
                connection.commit()
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT COUNT(*) FROM binding').fetchone()[0] == 0


@pytest.mark.parametrize('kind', ['token', 'commit', 'human'])
def test_withdrawal_waits_for_sqlite_commit_then_stale_token_cannot_commit(gate, tmp_path, kind):
    path = tmp_path / 'catalog.sqlite'
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE binding (value TEXT)')
    token = _token(gate)
    entered, release, withdrawing, returned = (threading.Event() for _ in range(4))
    outcomes = []
    errors = []
    def writer():
        try:
            with sqlite3.connect(path) as connection:
                connection.execute('BEGIN IMMEDIATE')
                connection.execute("INSERT INTO binding VALUES ('synthetic signed material')")
                with _lease(gate, token) as require_current:
                    entered.set()
                    assert release.wait(3)
                    require_current()
                    connection.commit()
                    outcomes.append('committed')
        except BaseException as exc:
            errors.append(exc)
    def withdraw():
        try:
            assert entered.wait(3)
            withdrawing.set()
            if kind == 'token': gate.revoke_approval(token)
            else: gate.revoke_permission(p.PermissionLevel.COMMIT if kind == 'commit' else p.PermissionLevel.HUMAN_APPROVAL)
            outcomes.append('withdrawn')
            returned.set()
        except BaseException as exc:
            errors.append(exc)
    threads = [threading.Thread(target=writer), threading.Thread(target=withdraw)]
    for thread in threads: thread.start()
    try:
        assert entered.wait(3) and withdrawing.wait(3)
        assert not returned.wait(.05)
    finally:
        release.set()
        for thread in threads: thread.join(4)
    assert not errors and not any(thread.is_alive() for thread in threads)
    assert outcomes == ['committed', 'withdrawn']
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT COUNT(*) FROM binding').fetchone()[0] == 1
    with pytest.raises(PermissionError):
        with _lease(gate, token):
            pytest.fail('withdrawn authority cannot be reused')


def test_yielded_check_expires_with_lease_and_exception_releases_lock(gate):
    token = _token(gate)
    with pytest.raises(ValueError):
        with _lease(gate, token) as require_current:
            require_current()
            raise ValueError('synthetic rollback')
    with pytest.raises(PermissionError, match='PERMISSION_REVOKED'):
        require_current()
    assert gate.revoke_approval(token) is True
