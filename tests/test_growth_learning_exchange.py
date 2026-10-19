"""Actual synthetic importer/report/review/Evidence/Permission integration.

No provider, external receiver, production DB or network is used.
"""
import json
import uuid

import pytest

from tests.test_saved_document_workflow import workspace, _source
from lumenis.shared.learning import contribution as learning
from lumenis.shared.reporting import source_brief_job as jobs, operator_review
from lumenis.shared.reporting.media_brief import _actor_ref
from lumenis.shared.database.business_schema import apply_business_schema
from lumenis.shared.evaluation import recorder
from lumenis.system.security import permission


@pytest.fixture
def journey(workspace):
    workspace['gate'].grant_permission(permission.PermissionLevel.HUMAN_APPROVAL)
    with workspace['repo'].transaction() as con:
        apply_business_schema(con)
    recorder.init_db()
    import subject_registry
    entry, _ = subject_registry.add_subject({'domain_id': 'CTH', 'subject_type': 'company', 'name_en': 'Synthetic learning subject', 'name_zh': '合成测试主体'})
    workspace = {**workspace, 'scope': {**workspace['scope'], 'subject_id': entry['subject_id'], 'global_scope': False}}
    _, _, source = _source(workspace)
    actor_id = _actor_ref(workspace['actor'])
    with workspace['repo'].connection(read_only=True, wal=False) as con:
        report = jobs.create_source_brief_job(con, product_id='CTH', global_scope=False,
            entity_label=entry['name_zh'], subject_id=entry['subject_id'], actor_id=actor_id,
            permission_audit_ref='test:scope-read', trace_id='test:growth-learning',
            job_id='job-learning-' + uuid.uuid4().hex, source_ids=[source['source_id']], image_actor=workspace['actor'])
    scope = report['source_brief']['scope']
    authorize = lambda: {'actor_id': actor_id, 'scope': scope,
                         'permission_audit_ref': 'test:permission', 'operation_audit_ref': 'test:operation'}
    review = operator_review.write_operator_review(report['job_id'], actor_id=actor_id,
        expected_scope=scope, submission_id=str(uuid.uuid4()), decision='request_changes',
        notes='The source supports its own wording; outcome remains unknown.', authorize=authorize)
    common = dict(actor=workspace['actor'], actor_id=actor_id, expected_scope=scope)
    candidate = learning.create_candidate(job_id=report['job_id'], review_id=review['review_id'],
        submission_id=str(uuid.uuid4()), authorize=authorize, **common)
    return {**workspace, 'source': source, 'report': report, 'review': review,
            'common': common, 'authorize': authorize, 'candidate': candidate}


def transition(j, obj, action, *, approved=True, submission_id=None, **overrides):
    if approved:
        j['gate'].grant_approval(permission.OperationType.CONFIG_MODIFY.value,
            resource=learning.approval_resource(obj['id'], action, obj['revision']), granted_by=j['common']['actor_id'])
    args = dict(**j['common'], action=action, expected_revision=obj['revision'],
                submission_id=submission_id or str(uuid.uuid4()), authorize=j['authorize'])
    args.update(overrides)
    if obj['kind'] == 'candidate':
        return learning.transition_candidate(obj['id'], notes='Independent review of source-limited result.', **args)
    return learning.transition_outbox(obj['id'], **args)


def validated(j):
    return transition(j, transition(j, j['candidate'], 'review'), 'validate')


def enqueue(j, candidate=None):
    candidate = candidate or validated(j)
    return learning.enqueue_candidate(candidate['id'], expected_revision=candidate['revision'],
        submission_id=str(uuid.uuid4()), authorize=j['authorize'], **j['common'])


def test_no_ai_complete_candidate_admission_withdraw_restore(journey):
    j = journey
    raw = learning.get_candidate(j['candidate']['id'], **j['common'])
    assert raw['admission'] == 'RAW'
    assert raw['origin']['business_outcome'] == 'NOT_OBSERVED'
    assert raw['origin']['source_bindings'][0]['rights'] == 'public-reference-only'
    assert not raw['training_eligible'] and not raw['commercial_use_eligible']
    with pytest.raises(ValueError, match='TRANSITION_INVALID'):
        transition(j, raw, 'adopt')
    reviewed = transition(j, raw, 'review')
    validated_record = transition(j, reviewed, 'validate')
    adopted = transition(j, validated_record, 'adopt')
    assert adopted['admission'] == 'ADOPTED' and not adopted['production_truth_write']
    withdrawn = transition(j, adopted, 'withdraw')
    restored = transition(j, withdrawn, 'restore')
    assert restored['admission'] == 'REVIEWED'
    assert restored == learning.get_candidate(raw['id'], **j['common'])


def test_approval_cas_replay_and_duplicate_candidate(journey):
    j = journey
    with pytest.raises(ValueError, match='WORK_EFFECT_PERMISSION_DENIED'):
        transition(j, j['candidate'], 'review', approved=False)
    sid = str(uuid.uuid4())
    reviewed = transition(j, j['candidate'], 'review', submission_id=sid)
    assert transition(j, j['candidate'], 'review', submission_id=sid) == reviewed
    with pytest.raises(RuntimeError, match='REVISION_CONFLICT'):
        transition(j, j['candidate'], 'review')
    again = learning.create_candidate(job_id=j['report']['job_id'], review_id=j['review']['review_id'],
        submission_id=str(uuid.uuid4()), authorize=j['authorize'], **j['common'])
    assert again == reviewed


def test_local_outbox_runtime_contract_minimization_and_no_global_read(journey):
    j = journey
    out = enqueue(j)
    contract = learning.current_contract()
    assert out['payload']['contract_version'] == contract['contract_version'] == '1.1.0'
    assert out['payload']['cross_product_contract_fingerprint'] == contract['protocol_fingerprint_sha256']
    assert out['payload']['license'] == 'UNKNOWN'
    assert not out['payload']['external_delivery_authorized']
    text = json.dumps(out['payload'])
    assert 'Original source line' not in text and 'swireproperties' not in text
    staged = transition(j, out, 'stage')
    assert staged['transport'] == 'EXPORTED' and not staged['delivery_proven']
    assert learning.list_outbox(**j['common'])['records'] == [staged]
    wrong = {**j['common'], 'actor_id': 'actor:999'}
    with pytest.raises(PermissionError):
        learning.get_outbox(out['id'], **wrong)
    with pytest.raises(PermissionError):
        learning.list_outbox(**wrong)
    with pytest.raises((PermissionError, ValueError)):
        learning.get_outbox(out['id'], **{**j['common'], 'expected_scope': {**j['common']['expected_scope'], 'entity_label': 'Other'}})


def test_three_failures_dead_letter_reviewed_requeue(journey):
    j = journey
    out = enqueue(j)
    for i in range(3):
        out = transition(j, out, 'fail')
        assert out['attempts'] == i + 1
    assert out['transport'] == 'DEAD_LETTER'
    with pytest.raises(ValueError, match='TRANSITION_INVALID'):
        transition(j, out, 'stage')
    with pytest.raises(ValueError, match='WORK_EFFECT_PERMISSION_DENIED'):
        transition(j, out, 'requeue', approved=False)
    retried = transition(j, out, 'requeue')
    assert retried['transport'] == 'PENDING' and retried['retry_cycle'] == 1 and retried['attempts'] == 0


def test_spoofed_receipt_and_changed_source_are_rejected(journey):
    j = journey
    out = transition(j, enqueue(j), 'stage')
    with pytest.raises(PermissionError, match='RECEIVER_NOT_BOUND'):
        transition(j, out, 'receipt', receipt_evidence_ref=j['review']['evidence_ref'])
    with pytest.raises(PermissionError, match='RECEIVER_NOT_BOUND'):
        transition(j, out, 'receipt', receipt_evidence_ref='app_evidence_records:999999')
    with j['repo'].transaction() as con:
        con.execute("UPDATE app_evidence_records SET content_hash=? WHERE id=?", ('f' * 64, j['source']['evidence_id']))
    with pytest.raises((ValueError, PermissionError, RuntimeError)):
        learning.get_outbox(out['id'], **j['common'])


def test_revoked_permission_and_mid_transaction_failure_roll_back(journey):
    j = journey
    raw = j['candidate']
    def revoked():
        raise PermissionError('REVOKED')
    with pytest.raises(PermissionError, match='REVOKED'):
        transition(j, raw, 'review', authorize=revoked)
    assert learning.get_candidate(raw['id'], **j['common'])['revision'] == 1
    count = 0
    def revoke_at_commit():
        nonlocal count
        count += 1
        if count == 2:
            raise PermissionError('REVOKED_AT_COMMIT')
        return j['authorize']()
    with pytest.raises(PermissionError, match='REVOKED_AT_COMMIT'):
        transition(j, raw, 'review', authorize=revoke_at_commit)
    assert learning.get_candidate(raw['id'], **j['common'])['revision'] == 1


def test_no_sources_no_candidate(workspace):
    with workspace['repo'].transaction() as con:
        apply_business_schema(con)
    recorder.init_db()
    with workspace['repo'].connection(read_only=True, wal=False) as con:
        report = jobs.create_source_brief_job(con, product_id='CTH', global_scope=True,
            entity_label='Empty synthetic research', actor_id=_actor_ref(workspace['actor']),
            permission_audit_ref='test:permission', trace_id='test:empty', job_id='job-empty-synthetic')
    scope = report['source_brief']['scope']
    auth = lambda: dict(actor_id=_actor_ref(workspace['actor']), scope=scope,
                        permission_audit_ref='test:permission', operation_audit_ref='test:operation')
    with pytest.raises(ValueError, match='REAL_SOURCES_REQUIRED'):
        learning.create_candidate(job_id=report['job_id'], actor=workspace['actor'], actor_id=_actor_ref(workspace['actor']),
            expected_scope=scope, review_id='0' * 64, submission_id=str(uuid.uuid4()), authorize=auth)


def test_actual_local_receiver_separates_admission_and_replays(journey):
    j = journey
    candidate = validated(j)
    out = learning.enqueue_candidate(candidate['id'], expected_revision=candidate['revision'],
        submission_id=str(uuid.uuid4()), authorize=j['authorize'], receiver=learning.LOCAL_REPO, **j['common'])
    out = transition(j, out, 'stage')
    sid = str(uuid.uuid4())
    args = dict(**j['common'], expected_revision=out['revision'], submission_id=sid, authorize=j['authorize'])
    with pytest.raises(ValueError, match='WORK_EFFECT_PERMISSION_DENIED'):
        learning.receive_local_contribution(out['id'], **args)
    j['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,
        resource=learning.approval_resource(out['id'], 'receive_local', out['revision']), granted_by=j['common']['actor_id'])
    ack = learning.receive_local_contribution(out['id'], **args)
    assert ack['transport'] == 'ACKNOWLEDGED' and not ack['remote_delivery_proven']
    assert ack['receipt']['staged_evidence_ref'] == out['evidence_ref']
    assert learning.receive_local_contribution(out['id'], **args) == ack
    assert learning.get_candidate(candidate['id'], **j['common'])['admission'] == 'VALIDATED'
    with pytest.raises(ValueError, match='SUBMISSION_CONFLICT'):
        learning.receive_local_contribution(out['id'], accepted=False, **args)


def test_withdrawn_candidate_blocks_stale_staging(journey):
    j = journey
    candidate = validated(j)
    out = enqueue(j, candidate)
    transition(j, candidate, 'withdraw')
    with pytest.raises(PermissionError, match='REVIEW_CHANGED'):
        transition(j, out, 'stage')


def test_signed_event_tampering_fails_closed(journey):
    j = journey
    with j['repo'].transaction() as con:
        con.execute("UPDATE app_evidence_records SET outputs_json=? WHERE feature_id=? AND asset_id=?",
                    ('{"admission":"ADOPTED"}', learning.FEATURE, j['candidate']['id']))
    with pytest.raises(RuntimeError, match='SIGNATURE_INVALID'):
        learning.get_candidate(j['candidate']['id'], **j['common'])


def test_existing_learning_loop_context_never_calls_ai_and_rechecks_admission(journey):
    from lumenis.shared.learning.loop import LearningLoop
    j = journey
    loop = LearningLoop(enabled=True)
    with pytest.raises(PermissionError, match='ADOPTION_REQUIRED'):
        loop.build_reviewed_research_context([j['candidate']['id']], **j['common'])
    adopted = transition(j, validated(j), 'adopt')
    context = loop.build_reviewed_research_context([adopted['id']], **j['common'])
    assert context['references'][0]['claim_type'] == 'OPERATOR_FEEDBACK'
    assert not context['instructions_authority'] and not context['external_transmission_authorized']
    transition(j, adopted, 'withdraw')
    with pytest.raises(PermissionError, match='ADOPTION_REQUIRED'):
        loop.build_reviewed_research_context([adopted['id']], **j['common'])


def test_stage_requires_exact_approval_and_deleted_source_cannot_be_reused(journey):
    j = journey
    out = enqueue(j)
    with pytest.raises(ValueError, match='WORK_EFFECT_PERMISSION_DENIED'):
        transition(j, out, 'stage', approved=False)
    with j['repo'].transaction() as con:
        con.execute('DELETE FROM canonical_data WHERE source_id=?', (j['source']['source_id'],))
    with pytest.raises((ValueError, PermissionError, RuntimeError)):
        learning.get_candidate(j['candidate']['id'], **j['common'])


def test_shared_private_source_review_local_receive(workspace):
    workspace['gate'].grant_permission(permission.PermissionLevel.HUMAN_APPROVAL)
    scope = {'scope_kind': 'shared_workspace', 'version': 1}
    with workspace['repo'].transaction() as con:
        apply_business_schema(con)
    recorder.init_db()
    path = workspace['root'] / 'private.txt'
    path.write_text('Synthetic private research: different wording can change understanding. Actual impact is unknown.')
    saved = workspace['documents'].save_private_document(str(path), actor=workspace['actor'], scope=scope,
                                                        request_id='shared-learning-original')
    source_id = saved['artifact']['artifact_id']
    actor_id = _actor_ref(workspace['actor'])
    with workspace['repo'].connection(read_only=True, wal=False) as con:
        report = jobs.create_source_brief_job(con, scope_kind='shared_workspace', version=1,
            actor_id=actor_id, image_actor=workspace['actor'], permission_audit_ref='test:shared-read',
            trace_id='test:shared-learning', job_id='job-shared-learning-original', source_ids=[source_id],
            business_question='Which statement is supported and which effect remains unknown?')
    review = jobs.write_shared_report_review(report['job_id'], actor=workspace['actor'], actor_id=actor_id,
        submission_id=str(uuid.uuid4()), decision='request_changes', notes='Keep this as an unverified source statement.')
    common = dict(actor=workspace['actor'], actor_id=actor_id, expected_scope=scope)
    authorize = lambda: dict(actor_id=actor_id, scope=scope, permission_audit_ref='test:shared', operation_audit_ref='test:review')
    candidate = learning.create_candidate(job_id=report['job_id'], review_id=review['review_id'],
        submission_id=str(uuid.uuid4()), authorize=authorize, **common)
    j = {**workspace, 'candidate': candidate, 'common': common, 'authorize': authorize}
    candidate = validated(j)
    assert candidate['origin']['source_bindings'][0]['rights'] == 'UNKNOWN'
    with pytest.raises(PermissionError, match='SHARED_EXTERNAL_DELIVERY_DENIED'):
        enqueue(j, candidate)
    out = learning.enqueue_candidate(candidate['id'], expected_revision=candidate['revision'],
        submission_id=str(uuid.uuid4()), authorize=authorize, receiver=learning.LOCAL_REPO, **common)
    staged = transition(j, out, 'stage')
    resource = learning.approval_resource(out['id'], 'receive_local', staged['revision'])
    workspace['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=resource, granted_by=j['common']['actor_id'])
    received = learning.receive_local_contribution(out['id'], expected_revision=staged['revision'],
        submission_id=str(uuid.uuid4()), authorize=authorize, **common)
    assert received['transport'] == 'ACKNOWLEDGED' and received['remote_delivery_proven'] is False
    assert not learning.get_candidate(candidate['id'], **common)['training_eligible']


def test_business_outcome_independent_review_enters_existing_learning_owner(journey):
    from api_dual_domain import BusinessDecisionWorkflow
    j = journey
    common = j['common']
    actor_ref, scope = common['actor_id'], common['expected_scope']
    auth = lambda operation: {**j['authorize'](), 'operation': operation}
    service = BusinessDecisionWorkflow(action_actor=j['actor'], source_actor=j['actor'])
    options = [{'option_id': label, 'proposal': 'Review bounded wording ' + label,
                'rationale': 'Source wording is evidence of its own statement only.',
                'source_ids': [j['source']['source_id']], 'assumptions': ['No impact is established.'],
                'unknowns': ['Audience effect.'], 'check': 'Independent operator review.'} for label in ('A', 'B')]
    work = service.prepare(actor_ref=actor_ref, scope=scope, submission_id='prepare-learning-01',
        source_job_id=j['report']['job_id'], kind='venue_operations', question='Which bounded wording merits review?',
        options=options, authorize=auth)
    def step(operation, payload):
        nonlocal work
        work = service.advance(work['work_id'], actor_ref=actor_ref, scope=scope, authorize=auth,
            expected_revision=work['revision'], submission_id='learning-' + uuid.uuid4().hex,
            operation=operation, payload=payload)
    step('choose', {'option_id': 'A', 'reason': 'Bounded exploration.', 'owner': 'Synthetic operator',
                    'review_at': '2026-10-20T12:00:00+00:00'})
    step('outcome', {'source_job_id': j['report']['job_id'], 'source_id': j['source']['source_id'],
                     'quote': 'Original source line', 'limits': 'Source statement, not an observed business effect.'})
    before = dict(job_id=j['report']['job_id'], review_id='business:' + work['work_id'] + '|' + work['revision'],
                  submission_id=str(uuid.uuid4()), authorize=j['authorize'], **common)
    with pytest.raises(RuntimeError, match='BUSINESS_LEARNING_REVIEW_REQUIRED'):
        learning.create_candidate(**before)
    feedback = {'assessment': 'inconclusive', 'observations': 'Wording persists, impact remains unknown.',
                'limitations': ['Synthetic source only.'], 'next_step': 'revise', 'source_ids': [j['source']['source_id']]}
    step('review', feedback)
    candidate = learning.create_business_candidate(work_id=work['work_id'], expected_business_revision=work['revision'],
        job_id=j['report']['job_id'], submission_id=str(uuid.uuid4()), authorize=j['authorize'], **common)
    assert candidate['origin']['business_revision'] == work['revision']
    assert candidate['origin']['evaluation_id'] == work['evaluation']['evaluation_id']
    assert candidate['origin']['outcome_state'] == 'SOURCE_REPORTED'
    assert candidate['origin']['business_outcome'] == 'NOT_OBSERVED'
    assert candidate['admission'] == 'RAW'
    step('review', {**feedback, 'assessment': 'not_useful'})
    with pytest.raises((PermissionError, RuntimeError), match='SOURCE_OR_REVIEW_CHANGED|REVISION_CONFLICT'):
        learning.get_candidate(candidate['id'], **common)


def test_contract_tamper_blocks_optional_transport_but_preserves_base_candidate(journey, tmp_path, monkeypatch):
    j = journey
    candidate = validated(j)
    contract = learning.current_contract()
    contract['contract_version'] = '1.0.0'
    path = tmp_path / 'changed-contract.json'
    path.write_text(json.dumps(contract))
    monkeypatch.setattr(learning, 'CONTRACT_PATH', path)
    with pytest.raises(RuntimeError, match='CONTRACT_UNSUPPORTED'):
        enqueue(j, candidate)
    assert learning.get_candidate(candidate['id'], **j['common'])['admission'] == 'VALIDATED'


def test_unknown_external_receiver_and_local_rejected_receipt_require_review(journey):
    j = journey
    candidate = validated(j)
    args = dict(expected_revision=candidate['revision'], submission_id=str(uuid.uuid4()),
                authorize=j['authorize'], **j['common'])
    with pytest.raises(ValueError, match='RECEIVER_INVALID'):
        learning.enqueue_candidate(candidate['id'], receiver='attacker/unknown', **args)
    out = learning.enqueue_candidate(candidate['id'], receiver=learning.LOCAL_REPO, **args)
    out = transition(j, out, 'stage')
    j['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,
        resource=learning.approval_resource(out['id'], 'receive_local', out['revision']), granted_by=j['common']['actor_id'])
    rejected = learning.receive_local_contribution(out['id'], accepted=False, expected_revision=out['revision'],
        submission_id=str(uuid.uuid4()), authorize=j['authorize'], **j['common'])
    assert rejected['transport'] == 'REJECTED'
    requeued = transition(j, rejected, 'requeue')
    assert requeued['transport'] == 'PENDING'
    assert learning.get_candidate(candidate['id'], **j['common'])['admission'] == 'VALIDATED'
    assert learning.list_candidates(**j['common'])['records'] == [candidate]


def test_effect_approval_consumed_only_on_commit_and_foreign_approver_denied(journey):
    j = journey
    raw = j['candidate']
    resource = learning.approval_resource(raw['id'], 'review', raw['revision'])
    token = j['gate'].grant_approval(permission.OperationType.CONFIG_MODIFY.value, resource=resource,
                                    granted_by='actor:999')
    with pytest.raises(PermissionError, match='APPROVAL_REVOKED'):
        transition(j, raw, 'review', approved=False)
    assert learning.get_candidate(raw['id'], **j['common'])['revision'] == raw['revision']
    j['gate'].revoke_approval(token)
    token = j['gate'].grant_approval(permission.OperationType.CONFIG_MODIFY.value, resource=resource,
                                    granted_by=j['common']['actor_id'])
    transition(j, raw, 'review', approved=False)
    assert not j['gate']._approval_token_is_valid(token, permission.OperationType.CONFIG_MODIFY.value, resource)


def test_context_unrecognized_ids_and_review_replacement_are_not_silent(journey):
    j = journey
    with pytest.raises(LookupError):
        learning.get_candidate('f' * 64, **j['common'])
    with pytest.raises(ValueError, match='CONTEXT_SELECTION_INVALID'):
        learning.build_reviewed_context([], **j['common'])
    with pytest.raises(ValueError, match='CONTEXT_SELECTION_INVALID'):
        learning.build_reviewed_context([j['candidate']['id']] * 2, **j['common'])


def test_current_server_workspace_access_revocation_blocks_reads_and_writes(journey):
    j = journey
    j['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    with pytest.raises((PermissionError, ValueError)):
        learning.get_candidate(j['candidate']['id'], **j['common'])
    with pytest.raises((PermissionError, ValueError)):
        transition(j, j['candidate'], 'review')
    j['app'].config['LUMENIS_OPEN_WORKSPACE'] = True
    assert learning.get_candidate(j['candidate']['id'], **j['common'])['admission'] == 'RAW'
