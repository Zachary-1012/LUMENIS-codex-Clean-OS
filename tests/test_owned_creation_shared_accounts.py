"""Real isolated account/scope checks; inference result remains a fixture."""
import json

import pytest

import content_generation as creation
from lumenis.shared.content_creation import internal_pitch as pitch
from lumenis.shared.evidence import store
from tests import test_internal_pitch_shared_av as shared_helpers
from tests.test_owned_creation_workflow import arguments, fake_gateway, run

shared = shared_helpers.shared


@pytest.fixture
def ready(shared, monkeypatch):
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_KEY_RING', json.dumps({'creation-test':'isolated-source-signing-key'}))
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID', 'creation-test')
    monkeypatch.setattr(creation, 'get_repository', lambda:shared['repo'])
    store.init_evidence_store(str(shared['root']/'shared-av.sqlite3'))
    with shared['repo'].transaction() as con:
        store.ensure_evidence_schema(con)
    return shared


def test_independent_shared_reports_grant_can_create_without_business_domain(ready, monkeypatch):
    ws = ready
    assert not ws['repo'].query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='lumenis_subject_registry'")
    calls = fake_gateway(ws, monkeypatch)
    saved = run(ws, pitch.prepare_internal_pitch(**arguments(ws)))
    assert calls[0].domain_id == 'shared' and calls[0].scope == 'shared_workspace:v1'
    assert saved['creation_evidence']['integrity_digest']
    assert pitch.read_internal_pitch(saved['task_id'], actor=ws['actor'], scope=ws['scope'])['action_receipt'] == saved['action_receipt']


def test_revoked_shared_write_prevents_inference(ready, monkeypatch):
    ws = ready
    calls = fake_gateway(ws, monkeypatch)
    task = pitch.prepare_internal_pitch(**arguments(ws))
    if ws['mode'] == 'account':
        with ws['repo'].transaction() as con:
            con.execute("DELETE FROM v4_member_authorizations WHERE user_id=? AND module='reports' AND action='write'", (ws['actor']['id'],))
    else:
        ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    with pytest.raises(ValueError, match='WORK_PERMISSION_DENIED'):
        run(ws, task)
    assert not calls
