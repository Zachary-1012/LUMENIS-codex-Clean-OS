"""Typed professional plans over real isolated owners, not live business effects."""
import copy
import json

import pytest

from tests.test_business_result_continuity import business, add_material, save, selection
from tests.test_saved_document_workflow import workspace
from tests.test_business_execution_observations import advance, manual_payload, observation_payload


def domain_plan(source_id, *, bmp=False):
    measure = {'name': 'participants', 'definition': 'Operator-reported participants at one desk.',
               'unit': 'people', 'baseline_value': '90', 'target_value': '100',
               'window': {'start': '2026-10-10T00:00:00+08:00', 'end': '2026-10-12T00:00:00+08:00'}}
    def action(identity, parents, amount):
        return {'action_id': identity, 'target': 'Declared store service desk',
                'responsible': 'Declared store operator', 'deliverable': 'Review and record ' + identity,
                'source_ids': [source_id], 'depends_on': parents,
                'due_at': '2026-10-10T12:00:00+08:00',
                'cost_estimate': {'amount': amount, 'currency': 'CNY'},
                'success_measure': measure if parents else None}
    return {'workflow': 'campaign' if bmp else 'feedback_resolution',
            'objective': 'Resolve the declared issue and review the reported result.',
            'actions': [action('verify-input', [], '100.50'), action('follow-up', ['verify-input'], '20.25')]}


def prepared(ws, *, plan=None, submission='prepare-domain-plan'):
    source_id = ws['current']['source_brief']['records'][0]['source_id']
    plan = domain_plan(source_id, bmp=ws['scope']['domain_id'] == 'zbmp') if plan is None else plan
    return ws['service'].prepare(actor_ref=ws['actor_ref'], scope=ws['domain_scope'], authorize=ws['authorize'],
        submission_id=submission, source_job_id=ws['current']['source_report']['job_id'],
        kind=ws['current']['kind'], question='Review the permitted operating and campaign source statements.',
        planning_constraints={'domain_plan': plan})


def test_typed_plan_dependency_execution_target_save_and_cold_reopen(business):
    from api_dual_domain import BusinessDecisionWorkflow
    ws = business
    current = prepared(ws)
    workbench = current['domain_analysis']['question_result']['business_report']['domain_workbench']
    assert workbench['cost_assessment']['CNY']['complete_estimate'] == '120.75'
    assert workbench['cost_assessment']['CNY']['actual_spend'] is None
    assert current['domain_execution']['actions'][0]['state'] == 'DECISION_REQUIRED'
    current = advance(ws, current, 'choose', selection(current['options'][0]['option_id'], '100'), 'choose-domain-plan')
    ws['current'] = current
    first = save(ws, request_id='save-domain-plan-v1')['saved_work']
    first_revision = current['revision']
    receipt, _ = add_material(ws, 'domain-plan-receipt', 'Operator reported the two tasks and 120 participants.')
    payload = {**manual_payload(receipt, 'Operator reported the two tasks and 120 participants.'),
               'option_id': current['decision']['option_id'], 'plan_action_id': 'follow-up'}
    with pytest.raises(RuntimeError, match='DEPENDENCIES_NOT_RECORDED'):
        advance(ws, current, 'manual_action', payload, 'reject-unrecorded-dependency')
    first_payload = {**payload, 'plan_action_id': 'verify-input'}
    current = advance(ws, current, 'manual_action', first_payload, 'record-domain-first')
    payload['performed_at'] = '2026-10-10T09:00:00+08:00'
    with pytest.raises(ValueError, match='DEPENDENCY_TIME_INVALID'):
        advance(ws, current, 'manual_action', payload, 'reject-backdated-followup')
    payload['performed_at'] = '2026-10-10T11:00:00+08:00'
    current = advance(ws, current, 'manual_action', payload, 'record-domain-followup')
    assert current['domain_execution']['reported_performed'] == 2
    assert current['action_state'] == 'MANUALLY_REPORTED'
    assert current['execution_records'][1]['planned_action']['dependency_receipts'] == [
        current['execution_records'][0]['operation_digest']]
    observation = observation_payload(receipt, 'Operator reported the two tasks and 120 participants.')
    observation['metrics'][0]['value'] = '120'
    current = advance(ws, current, 'observation', observation, 'observe-domain-target')
    review = current['observation']['domain_target_review']['actions'][1]
    assert review['target_gap'] == '20' and review['reported_change_from_declared_baseline'] == '30'
    assert review['state'] == 'REPORTED_TARGET_COMPARISON' and review['causation'] == 'NOT_ESTABLISHED'
    assert current['business_outcome'] == 'SOURCE_REPORTED_NOT_ATTRIBUTED'
    ws['current'] = current
    second = save(ws, request_id='save-domain-plan-v2', parent=first['artifact']['artifact_id'],
        digest=first['document']['draft_digest'], citations=[i['citation'] for i in current['citation_candidates']['items']])['saved_work']
    assert second['document']['version'] == 2
    cold = BusinessDecisionWorkflow(action_actor=ws['actor'])
    reopened = cold.reopen(current['work_id'], actor_ref=ws['actor_ref'], scope=ws['domain_scope'], authorize=ws['authorize'])
    assert reopened['domain_execution'] == current['domain_execution']
    old = cold.reopen(current['work_id'], actor_ref=ws['actor_ref'], scope=ws['domain_scope'],
                      authorize=ws['authorize'], revision=first_revision)
    assert old['domain_execution']['reported_performed'] == 0
    assert ws['work'].reopen_work(first['artifact']['artifact_id'], actor=ws['actor'], scope=ws['scope'])['document'] == first['document']


@pytest.mark.parametrize('fault', ['cycle', 'unknown_dependency', 'foreign_source', 'wrong_domain', 'bad_currency'])
def test_plan_rejects_invalid_dependencies_source_or_domain_without_write(business, fault):
    ws = business
    source_id = ws['current']['source_brief']['records'][0]['source_id']
    plan = domain_plan(source_id, bmp=ws['scope']['domain_id'] == 'zbmp')
    if fault == 'cycle':
        plan['actions'][0]['depends_on'] = ['follow-up']
    elif fault == 'unknown_dependency':
        plan['actions'][0]['depends_on'] = ['missing-action']
    elif fault == 'foreign_source':
        plan['actions'][0]['source_ids'] = ['another-scope-source']
    elif fault == 'wrong_domain':
        plan['workflow'] = 'venue_operations' if ws['scope']['domain_id'] == 'zbmp' else 'campaign'
    else:
        plan['actions'][0]['cost_estimate']['currency'] = 'not-a-currency'
    before = ws['repo'].query_one('SELECT count(*) FROM app_evidence_records')[0]
    with pytest.raises((ValueError, PermissionError)):
        prepared(ws, plan=plan, submission='reject-plan-' + fault)
    assert ws['repo'].query_one('SELECT count(*) FROM app_evidence_records')[0] == before


@pytest.mark.parametrize('changed', ['definition', 'unit', 'window', 'unknown'])
def test_target_comparison_preserves_incompatible_or_missing_input(business, changed):
    ws = business
    current = prepared(ws)
    current = advance(ws, current, 'choose', selection(current['options'][0]['option_id'], '100'), 'choose-target-gap')
    report, _ = add_material(ws, 'target-gap-source', 'Operator reported a result with limited comparability.')
    observation = observation_payload(report, 'Operator reported a result with limited comparability.')
    if changed in {'definition', 'unit'}:
        observation['metrics'][0][changed] = 'Different ' + changed
    elif changed == 'window':
        observation['window']['start'] = '2026-10-11T00:00:00+08:00'
    else:
        observation['metrics'][0]['value'] = None
    current = advance(ws, current, 'observation', observation, 'observe-target-gap')
    review = current['observation']['domain_target_review']['actions'][1]
    assert review['state'] != 'REPORTED_TARGET_COMPARISON' and review['target_gap'] is None


def test_domain_review_lanes_bind_complete_original_claims_and_distinct_work(business):
    ws = business
    is_cth = ws['scope']['domain_id'] == 'cth'
    body = ('Operating hours remain source-reported. A service complaint needs review. Event on 2026-10-10.'
            if is_cth else 'Brand positioning is source-reported. Competitor market price needs review. Consumer feedback is partial.')
    report, _ = add_material(ws, 'domain-lane-material', body)
    current = ws['service'].prepare(actor_ref=ws['actor_ref'], scope=ws['domain_scope'], authorize=ws['authorize'],
        submission_id='prepare-domain-lane', source_job_id=report['job_id'], kind=ws['current']['kind'],
        question='Review the source materials.', planning_constraints={})
    bench = current['domain_analysis']['question_result']['business_report']['domain_workbench']
    assert {lane['lane_id'] for lane in bench['review_lanes']} == (
        {'operations', 'events', 'feedback'} if is_cth else {'positioning', 'competition', 'consumer'})
    assert bench['coverage']['scanned_characters'] == len(body)
    for lane in bench['review_lanes']:
        assert lane['claims']
        for claim in lane['claims']:
            ref = claim['reference']
            assert body[ref['start']:ref['end']] == ref['statement']
            assert claim['claim_type'] == 'SOURCE_REPORTED_CANDIDATE_NOT_CONFIRMED_FACT'
    assert body.replace('.', '')[:20] in current['usable_result']['markdown']


@pytest.mark.parametrize('tamper', [None, 'computed_value', 'artifact_hash', 'foreign_source'])
def test_existing_reporting_result_is_reproduced_then_bound_to_decision_and_saved_version(business, monkeypatch, tamper):
    from lumenis.shared.reporting import business_brief
    ws = business
    monkeypatch.setattr(business_brief, 'get_repository', lambda: ws['repo'])
    dataset = json.dumps({'schema': 'lumenis.statistics-input/v1', 'analysis': 'binomial',
                          'unit': 'trial', 'data': {'successes': 37, 'trials': 100}})
    report, citation = add_material(ws, 'professional-trial-data', dataset)
    computed = business_brief.analyze_statistics_source(citation['evidence_id'], actor=ws['actor'], scope=ws['scope'])
    draft = copy.deepcopy(computed['saved_work_draft'])
    if tamper == 'computed_value':
        draft['payload']['statistics']['result']['value'] = 0.99
    saved = ws['work'].save_work(**draft, request_id='save-professional-statistics',
                                 actor=ws['actor'], scope=ws['scope'])
    reference = {'artifact_id': saved['artifact']['artifact_id'], 'expected_sha256': saved['artifact']['sha256']}
    if tamper == 'artifact_hash':
        reference['expected_sha256'] = '0' * 64
    source_report = ws['current']['source_report']['job_id'] if tamper == 'foreign_source' else report['job_id']
    before = ws['repo'].query_one('SELECT count(*) FROM app_evidence_records')[0]
    args = dict(actor_ref=ws['actor_ref'], scope=ws['domain_scope'], authorize=ws['authorize'],
        submission_id='prepare-quantitative-result', source_job_id=source_report, kind=ws['current']['kind'],
        question='Review the measured trial proportion.', planning_constraints={'analysis_artifacts': [reference]})
    if tamper is not None:
        with pytest.raises((RuntimeError, PermissionError)):
            ws['service'].prepare(**args)
        assert ws['repo'].query_one('SELECT count(*) FROM app_evidence_records')[0] == before
        return
    prepared_result = ws['service'].prepare(**args)
    selected = advance(ws, prepared_result, 'choose', selection(prepared_result['options'][0]['option_id'], '100'),
                       'choose-quantitative-result')
    linked = selected['domain_analysis']['question_result']['business_report']['quantitative_results'][0]
    assert linked['statistics']['result'] == computed['result'] and linked['version'] == 1
    assert '计算值：' in selected['usable_result']['markdown']
    ws['current'] = selected
    output = save(ws, request_id='save-quantitative-business', citations=[citation])['saved_work']
    assert output['document']['payload']['business_work']['domain_analysis']['question_result']['business_report'][
        'quantitative_results'][0] == linked
    monkeypatch.setattr(business_brief, 'analyze_statistics_source',
        lambda *a, **k: pytest.fail('reopening immutable numerical decision recalculated its result'))
    reopened = ws['service'].reopen(selected['work_id'], actor_ref=ws['actor_ref'], scope=ws['domain_scope'], authorize=ws['authorize'])
    assert reopened['domain_analysis'] == selected['domain_analysis']
