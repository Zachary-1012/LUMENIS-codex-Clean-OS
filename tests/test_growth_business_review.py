"""Synthetic SQLite regression evidence, not live business acceptance."""
import copy
import sqlite3
import pytest
from tests.test_business_decision_workflow import work, step, choose, workspace
from tests.test_source_brief_job import job_db


def outcome(service, inputs):
    selected = choose(service, inputs, service.prepare(**inputs))
    return step(service, inputs, selected, 'outcome', {
        'source_job_id': inputs['source_job_id'], 'source_id': inputs['options'][0]['source_ids'][0],
        'quote': 'zero participants', 'limits': 'Source statement, no independently observed business effect.'}, 'growth-outcome-01')


def feedback(source_id="decision-source"):
    return {'assessment': 'inconclusive', 'observations': 'No independently observed uplift.',
            'limitations': ['Synthetic source; no live business validation.'],
            'next_step': 'revise', 'source_ids': [source_id]}


def count(db):
    with sqlite3.connect(db) as con:
        return con.execute("SELECT count(*) FROM app_evidence_records WHERE feature_id='CTH_BMP_DECISION_WORK'").fetchone()[0]


def test_review_exact_revision_persist_replay_revise_no_fact_promotion(work):
    service, inputs, db = work
    current = outcome(service, inputs)
    reviewed = step(service, inputs, current, 'review', feedback(inputs['options'][0]['source_ids'][0]), 'growth-review-01')
    assert reviewed['operator_review']['reviewer'] == inputs['actor_ref']
    assert reviewed['operator_review']['reviewed_revision'] == current['revision']
    assert reviewed['operator_review']['metric_value'] is None
    assert reviewed['evaluation']['business_usefulness'] == 'UNKNOWN'
    assert reviewed['business_outcome'] == 'NOT_OBSERVED'
    assert reviewed['action_state'] == 'NOT_EXECUTED'
    assert step(service, inputs, current, 'review', feedback(inputs['options'][0]['source_ids'][0]), 'growth-review-01') == reviewed
    reopened = service.reopen(current['work_id'], actor_ref=inputs['actor_ref'], scope=inputs['scope'], authorize=inputs['authorize'])
    assert reopened == reviewed
    revised = step(service, inputs, reviewed, 'review', {**feedback(inputs['options'][0]['source_ids'][0]), 'assessment': 'not_useful'}, 'growth-review-02')
    assert revised['operator_review']['reviewed_revision'] == reviewed['revision']
    historical = service.reopen(current['work_id'], actor_ref=inputs['actor_ref'], scope=inputs['scope'], authorize=inputs['authorize'], revision=reviewed['revision'])
    assert historical['operator_review'] == reviewed['operator_review']
    assert historical['is_current_revision'] is False


@pytest.mark.parametrize('change', [ {'source_ids': ['foreign-source']}, {'source_ids': []},
    {'limitations': []}, {'assessment': []}, {'next_step': {}}, {'assessment': 'FACT'}, {'next_step': 'execute'}, {'reviewer': 'other-user'}])
def test_invalid_review_never_persists(work, change):
    service, inputs, db = work
    current = outcome(service, inputs)
    before = count(db)
    with pytest.raises((ValueError, PermissionError)):
        step(service, inputs, current, 'review', {**feedback(inputs['options'][0]['source_ids'][0]), **change}, 'growth-invalid-01')
    assert count(db) == before


def test_review_requires_outcome_and_current_revision(work):
    service, inputs, db = work
    prepared = service.prepare(**inputs)
    with pytest.raises(RuntimeError, match='OUTCOME_REVIEW_REQUIRED'):
        step(service, inputs, prepared, 'review', feedback(inputs['options'][0]['source_ids'][0]), 'growth-early-01')
    selected = choose(service, inputs, prepared)
    assert selected['selected_by'] == inputs['actor_ref']
    with pytest.raises(RuntimeError, match='REVISION_CONFLICT'):
        step(service, inputs, prepared, 'review', feedback(inputs['options'][0]['source_ids'][0]), 'growth-stale-01')


def test_cancel_restore_preserves_interruption_and_has_no_external_effect(work):
    service, inputs, db = work
    selected = choose(service, inputs, service.prepare(**inputs))
    interrupted = step(service, inputs, selected, 'interrupt', {'reason': 'Connection interrupted.'}, 'growth-interrupt-01')
    cancelled = step(service, inputs, interrupted, 'cancel', {'reason': 'Stop this record.'}, 'growth-cancel-01')
    restored = step(service, inputs, cancelled, 'restore', {'reason': 'Resume record review.'}, 'growth-restore-01')
    assert restored['state'] == 'INTERRUPTED'
    assert restored['previous_state'] == 'DECIDED'
    assert restored['recovery']['external_effect'] == 'NOT_PERFORMED'
    assert step(service, inputs, cancelled, 'restore', {'reason': 'Resume record review.'}, 'growth-restore-01') == restored
    resumed = step(service, inputs, restored, 'resume', {}, 'growth-resume-01')
    assert resumed['state'] == 'DECIDED' and resumed['action_state'] == 'NOT_EXECUTED'
    assert service.reopen(cancelled['work_id'], actor_ref=inputs['actor_ref'], scope=inputs['scope'], authorize=inputs['authorize'], revision=cancelled['revision'])['state'] == 'CANCELLED'


def test_review_revocation_and_outcome_tamper_rollback(work):
    service, inputs, db = work
    current = outcome(service, inputs)
    before = count(db)
    def denied(operation):
        raise PermissionError('revoked')
    with pytest.raises(PermissionError):
        step(service, {**inputs, 'authorize': denied}, current, 'review', feedback(inputs['options'][0]['source_ids'][0]), 'growth-denied-01')
    with sqlite3.connect(db) as con:
        con.execute("UPDATE canonical_data SET content='Changed source bytes' WHERE source_id=?", (inputs['options'][0]['source_ids'][0],))
    with pytest.raises((RuntimeError, PermissionError, ValueError)):
        step(service, inputs, current, 'review', feedback(inputs['options'][0]['source_ids'][0]), 'growth-tampered-01')
    assert count(db) == before


@pytest.mark.parametrize('operation', ['review', 'restore'])
def test_foreign_actor_and_scope_fail_closed(work, operation):
    service, inputs, db = work
    current = outcome(service, inputs) if operation == 'review' else service.prepare(**inputs)
    if operation == 'restore':
        current = step(service, inputs, current, 'cancel', {'reason': 'Stop.'}, 'growth-stop-01')
    payload = feedback(inputs['options'][0]['source_ids'][0]) if operation == 'review' else {'reason': 'Restore.'}
    before = count(db)
    foreign = {**inputs, 'actor_ref': 'workspace:foreign'}
    foreign['authorize'] = lambda op: {'actor_id': foreign['actor_ref'], 'scope': inputs['scope'], 'operation': op,
                                      'permission_audit_ref': 'audit:foreign', 'operation_audit_ref': 'audit:foreign'}
    with pytest.raises(PermissionError):
        step(service, foreign, current, operation, payload, 'growth-foreign-01')
    assert count(db) == before

from tests.test_source_brief_job_routes import client as report_client, GLOBAL, URL


@pytest.mark.parametrize('operation', ['review', 'restore'])
def test_new_operations_use_real_permission_and_origin_fence(report_client, operation):
    import json
    from api_dual_domain import authorize_business_work_request
    from lumenis.system.security import permission as p
    from shared_artifacts import LocalArtifactError
    api, app, db, entry, gate = report_client
    headers = {**GLOBAL, 'X-Lumenis-Context-Mode': 'FOCUS', 'X-Subject-ID': entry['subject_id']}
    report = api.post(URL + '/generate', headers=headers, json={}).get_json()['result']
    with sqlite3.connect(db) as con:
        actor = json.loads(con.execute('SELECT source_snapshot FROM daily_reports WHERE report_id=?', (report['job_id'],)).fetchone()[0])['actor_id']
    scope = report['source_brief']['scope']
    with app.test_request_context('/', headers=headers, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        assert authorize_business_work_request(operation, actor_ref=actor, scope=scope)['operation_audit_ref']
        gate.revoke_permission(p.PermissionLevel.VERIFY)
        with pytest.raises(PermissionError):
            authorize_business_work_request(operation, actor_ref=actor, scope=scope)
    with app.test_request_context('/', headers={**headers, 'Origin': 'https://foreign.invalid'}, environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        with pytest.raises((PermissionError, LocalArtifactError)):
            authorize_business_work_request(operation, actor_ref=actor, scope=scope)


def test_review_evaluation_failure_replay_recovers_exact_signed_feedback(work, monkeypatch):
    from lumenis.shared.evaluation import recorder
    service, inputs, db = work
    current = outcome(service, inputs)
    original = recorder.record_evaluation
    def interrupted(**kwargs):
        raise RuntimeError('evaluation interrupted')
    monkeypatch.setattr(recorder, 'record_evaluation', interrupted)
    with pytest.raises(RuntimeError, match='evaluation interrupted'):
        step(service, inputs, current, 'review', feedback(inputs['options'][0]['source_ids'][0]), 'growth-recovery-01')
    after = count(db)
    pending = service.reopen(current['work_id'], actor_ref=inputs['actor_ref'], scope=inputs['scope'], authorize=inputs['authorize'])
    assert pending['evaluation']['state'] == 'PENDING_RECOVERY'
    assert pending['operator_review']['outcome_revision'] == current['revision']
    monkeypatch.setattr(recorder, 'record_evaluation', original)
    repaired = step(service, inputs, current, 'review', feedback(inputs['options'][0]['source_ids'][0]), 'growth-recovery-01')
    assert repaired['revision'] == pending['revision'] and count(db) == after
    assert repaired['evaluation']['state'] == 'RECORDED'

from tests.test_business_work_owner_routes import owners, prepare_business, advance, BUSINESS, PITCH
from tests.test_source_brief_job_routes import client
from tests.test_internal_pitch_workflow import manuscript_arguments


def test_growth_http_actual_artifact_feedback_restore_and_revocation(owners):
    from lumenis.system.security import permission
    ws = owners
    selected = advance(ws, prepare_business(ws), 'choose', {
        'option_id': 'B', 'reason': 'Review the bounded deliverable.', 'owner': 'Operator label',
        'review_at': '2026-10-20T12:00:00+00:00'}, 'growth-http-choose')
    cancelled = advance(ws, selected, 'cancel', {'reason': 'Pause this record.'}, 'growth-http-cancel')
    restored = advance(ws, cancelled, 'restore', {'reason': 'Continue record review.'}, 'growth-http-restore')
    assert restored['state'] == 'DECIDED'
    assert restored['action_state'] == 'NOT_EXECUTED'
    values = manuscript_arguments({'actor': None, 'scope': ws['scope']})
    values.pop('actor')
    pending = ws['api'].post(PITCH, headers=ws['headers'], json=values)
    assert pending.status_code == 202, pending.get_json()
    task_id = pending.get_json()['result']['task_id']
    produced = ws['api'].post(PITCH + '/' + task_id + '/run', headers=ws['headers'], json={'scope': ws['scope']})
    assert produced.status_code == 200, produced.get_json()
    executed = advance(ws, restored, 'action', {'option_id': 'B', 'task_id': task_id}, 'growth-http-action')
    assert executed['action']['receipt']['sha256'] == produced.get_json()['result']['action_receipt']['sha256']
    unknown = advance(ws, executed, 'outcome_unknown', {'limits': 'Actual internal artifact only; no campaign result.'}, 'growth-http-unknown')
    payload = {**feedback(), 'source_ids': [ws['source_id']]}
    reviewed = advance(ws, unknown, 'review', payload, 'growth-http-review')
    assert reviewed['operator_review']['outcome_revision'] == unknown['revision']
    assert reviewed['operator_review']['reviewer'] == reviewed['selected_by']
    assert reviewed['business_outcome'] == 'UNKNOWN'
    assert reviewed['evaluation']['state'] == 'RECORDED'
    assert advance(ws, unknown, 'review', payload, 'growth-http-review') == reviewed
    reopened = ws['api'].get(BUSINESS + '/' + reviewed['work_id'], headers=ws['headers'])
    assert reopened.status_code == 200 and reopened.get_json()['result'] == reviewed
    body = {'submission_id': 'growth-http-denied', 'expected_revision': reviewed['revision'], 'payload': payload}
    stale = ws['api'].post(BUSINESS + '/' + reviewed['work_id'] + '/review', headers=ws['headers'],
        json={**body, 'expected_revision': selected['revision']})
    assert stale.status_code == 409, stale.get_json()
    before = count(ws['db'])
    ws['gate'].revoke_permission(permission.PermissionLevel.VERIFY)
    denied = ws['api'].post(BUSINESS + '/' + reviewed['work_id'] + '/review', headers=ws['headers'], json=body)
    assert denied.status_code == 403, denied.get_json()
    assert count(ws['db']) == before
