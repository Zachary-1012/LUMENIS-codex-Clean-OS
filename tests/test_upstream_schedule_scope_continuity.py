"""Signed scheduler ownership and acquisition-version regressions, offline only."""
import json

import pytest
from tests.test_saved_document_workflow import workspace as original_workspace
from tests.test_math_revocation import workspace
from tests.test_math_upstream_review import setup, fetch, run, PATH
from lumenis.system.collector.runtime.scheduler import upstream_math_review as u
from lumenis.system.collector.guard.queue_worker import QueueWorker
from lumenis.system.security import OperationType
from lumenis.shared.evidence.store import record_evidence


def approved(w, *, scope=None, actor=None, cadence=7200):
    args = dict(schedule_id='official-math', cadence_seconds=cadence, enabled=True,
                actor=actor or w['actor'], scope=scope or w['scope'])
    config = u.configuration(**args)
    for op in (OperationType.CONFIG_MODIFY, OperationType.COLLECTOR_START, OperationType.EXTERNAL_NETWORK):
        w['gate'].grant_approval(op.value, resource=config['resource'], granted_by='isolated-owner')
    return args, config


def test_same_name_schedule_cannot_move_across_scope(setup):
    w, q, scheduler, original = setup
    run(setup)
    other_scope = {**w['scope'], 'domain_id': 'zbmp'}
    args, config = approved(w, scope=other_scope)
    with pytest.raises(PermissionError, match='OWNER_MISMATCH'):
        u.configure(**args)
    with pytest.raises(PermissionError, match='BINDING_CHANGED'):
        u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=other_scope)
    assert u.tick(q, actor=w['actor'], scope=other_scope) == []
    assert len(u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])['observations']) == 1


def test_same_name_schedule_cannot_move_across_actor(setup):
    w, q, _, _ = setup
    from account.models import init_account_db
    init_account_db()
    with w['repo'].transaction() as con:
        con.execute("INSERT INTO v4_users(id,username,password_hash,role,status) VALUES(87,'fixture-owner','not-a-password','owner','active')")
    args, _ = approved(w, actor={'id': 87})
    with pytest.raises(PermissionError, match='OWNER_MISMATCH'):
        u.configure(**args)
    with pytest.raises(PermissionError, match='BINDING_CHANGED'):
        u.read_handoff(schedule_id='official-math', actor={'id': 87}, scope=w['scope'])


def test_same_owner_configuration_upgrade_keeps_original_observation_provenance(setup):
    w, q, scheduler, _ = setup
    run(setup)
    old = u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])['observations'][0]
    args, _ = approved(w)
    new = u.configure(**args)
    reopened = u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])['observations']
    assert reopened[0]['configuration_evidence_id'] == old['configuration_evidence_id']
    assert reopened[0]['configuration_evidence_id'] != new['configuration_evidence_id']
    prepared = u.prepare_changed_review(evidence_id=old['evidence_id'], path=PATH, actor=w['actor'], scope=w['scope'])
    assert prepared['observation_evidence_id'] == old['evidence_id']
    jobs = u.tick(q, actor=w['actor'], scope=w['scope'])
    assert q.get(jobs[0])['payload']['configuration_evidence_id'] == new['configuration_evidence_id']
    assert QueueWorker(q, u.processor(q, actor_provider=lambda: (w['actor'], w['scope']), fetch=fetch)).process_once() == (jobs[0], True)
    assert len(u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])['observations']) == 2


def test_historical_foreign_configuration_cannot_shadow_first_owner(setup):
    w, q, scheduler, _ = setup
    run(setup)
    other_scope = {**w['scope'], 'domain_id': 'zbmp'}
    args, historical = approved(w, scope=other_scope)
    with w['repo'].transaction() as con:
        record_evidence(connection=con, source=u.CONFIG_SOURCE, product='Shared', feature_id='G165',
                        outputs=historical, raw_content=json.dumps(historical), status='verified', result='PASS')
    assert u.tick(q, actor=w['actor'], scope=other_scope) == []
    with pytest.raises(PermissionError):
        u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=other_scope)
    assert len(u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])['observations']) == 1
    own, _ = approved(w, cadence=10800)
    recovered = u.configure(**own)
    with w['repo'].connection(read_only=True) as con:
        assert u._current(con, 'official-math')[0] == recovered['configuration_evidence_id']


@pytest.mark.parametrize('mutation', ['foreign_config', 'unknown_config', 'custody'])
def test_signed_observation_requires_exact_source_configuration_and_scope(setup, mutation):
    w, q, scheduler, _ = setup
    run(setup)
    original = u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])['observations'][0]
    observation = {k: v for k, v in original.items() if k != 'evidence_id'}
    if mutation == 'unknown_config':
        observation['configuration_evidence_id'] = 999999
    elif mutation == 'foreign_config':
        args, foreign = approved(w, scope={**w['scope'], 'domain_id': 'zbmp'})
        with w['repo'].transaction() as con:
            observation['configuration_evidence_id'] = record_evidence(connection=con, source=u.CONFIG_SOURCE,
                product='Shared', outputs=foreign, raw_content=json.dumps(foreign), status='verified', result='PASS')
    with w['repo'].transaction() as con:
        evidence_id = record_evidence(connection=con, source=u.OBS_SOURCE,
            product='ZBMP' if mutation == 'custody' else 'CTH', outputs=observation,
            inputs={'configuration_evidence_id': observation['configuration_evidence_id']},
            raw_content=json.dumps(observation), domain_id='zbmp' if mutation == 'custody' else 'cth',
            global_scope=True, status='pending', result='GAP')
    if mutation == 'foreign_config':
        handoff = u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])
        assert [o['evidence_id'] for o in handoff['observations']] == [original['evidence_id']]
    else:
        with pytest.raises(PermissionError, match='UPSTREAM_OBSERVATION_'):
            u.read_handoff(schedule_id='official-math', actor=w['actor'], scope=w['scope'])
    with pytest.raises(PermissionError, match='UPSTREAM_OBSERVATION_'):
        u.prepare_changed_review(evidence_id=evidence_id, path=PATH, actor=w['actor'], scope=w['scope'])


def test_configuration_change_during_acquisition_cannot_commit_old_version(setup):
    w, q, scheduler, _ = setup
    changed = False
    def update(url):
        nonlocal changed
        result = fetch(url)
        if not changed:
            changed = True
            args, _ = approved(w)
            u.configure(**args)
        return result
    ids, outcome = run(setup, update)
    assert outcome == (ids[0], False)
    with w['repo'].connection(read_only=True) as con:
        assert u._rows(con, u.OBS_SOURCE) == []
