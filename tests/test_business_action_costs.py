"""Real isolated business/Source/SavedWork owners; no live financial effects."""
import copy
import hashlib

import pytest

from tests.test_business_domain_workbench import prepared, domain_plan
from tests.test_business_result_continuity import business, add_material, save, selection
from tests.test_saved_document_workflow import workspace
from tests.test_business_execution_observations import advance, observation_payload


def selected(ws):
    result = prepared(ws, submission='prepare-action-cost-plan')
    return advance(ws, result, 'choose', selection(result['options'][0]['option_id'], '100'), 'choose-action-cost-plan')


def cost(identity, kind, amount, *, action=None, related=None, supersedes=None, currency='CNY', occurred=None):
    result = {'entry_id': identity, 'kind': kind, 'amount': amount, 'currency': currency, 'related_entry_id': related}
    if action is not None:
        result['plan_action_id'] = action
    if supersedes:
        result.update(supersedes_entry_id=supersedes, correction_reason='Corrected transcription from the permitted receipt.')
    if occurred:
        result['occurred_at'] = occurred
    return result


def observe(ws, current, costs, identity):
    quote = 'Operator reported source amounts and corrections; no independent financial verification.'
    report, _ = add_material(ws, 'cost-' + hashlib.sha256(identity.encode()).hexdigest()[:12], quote)
    payload = observation_payload(report, quote)
    payload.update(metrics=[], costs=costs)
    return advance(ws, current, 'observation', payload, identity)


def test_action_unknown_cost_correction_refund_save_and_cold_reopen(business):
    from api_dual_domain import BusinessDecisionWorkflow
    ws = business
    current = selected(ws)
    initial = [cost('bill-unknown', 'ACTUAL', None, action='verify-input'),
               cost('bill-known', 'ACTUAL', '20', action='verify-input', occurred='2026-10-10T10:00:00+08:00'),
               cost('bill-refund', 'REFUND', '5', related='bill-known', occurred='2026-10-11T10:00:00+08:00')]
    current = observe(ws, current, initial, 'observe-action-unknown-cost')
    original = copy.deepcopy(current['observation'])
    totals = original['cost_totals']['CNY']
    assert totals['ACTUAL'] is None and totals['net_actual'] is None
    assert totals['known_subtotals']['ACTUAL'] == '20' and totals['unknown_amount_counts']['ACTUAL'] == 1
    assert original['resource_result']['remaining_budget_amount'] is None
    assert current['domain_execution']['actions'][0]['cost_review']['estimate_comparison'] == 'UNKNOWN'
    assert current['domain_execution']['reported_performed'] == 0
    ws['current'] = current
    first_revision = current['revision']
    first = save(ws, request_id='save-unknown-action-costs',
                 citations=[item['citation'] for item in current['citation_candidates']['items']])['saved_work']
    correction = cost('bill-corrected', 'ACTUAL', '30', supersedes='bill-unknown')
    current = observe(ws, current, [correction], 'correct-action-cost-total')
    assert current['observation']['cost_totals']['CNY']['ACTUAL'] == '50'
    assert current['observation']['cost_totals']['CNY']['net_actual'] == '45'
    review = current['observation']['action_cost_review']
    assert review['superseded_entry_ids'] == ['bill-unknown']
    assert review['actions'][0]['remaining_against_declared_estimate'] == '55.50'
    assert current['observation']['cost_ledger'][:3] == original['cost_ledger']
    current = observe(ws, current, [cost('refund-corrected', 'REFUND', '2', related='bill-known', supersedes='bill-refund')],
                      'correct-action-refund-total')
    assert current['observation']['cost_totals']['CNY']['net_actual'] == '48'
    current = observe(ws, current, [cost('late-refund', 'REFUND', '3', related='bill-unknown')], 'record-late-action-refund')
    assert current['observation']['cost_totals']['CNY']['net_actual'] == '45'
    check = next(item for item in current['observation']['action_cost_review']['refund_checks'] if item['entry_id'] == 'late-refund')
    assert check['original_actual_entry_id'] == 'bill-unknown' and check['current_actual_entry_id'] == 'bill-corrected'
    assert current['observation']['cost_ledger'][-1]['planned_action'] == original['cost_ledger'][0]['planned_action']
    assert current['observation']['action_cost_review']['profit'] is None
    assert current['observation']['action_cost_review']['causal_roi'] is None
    assert '原记录保留' in current['usable_result']['markdown']
    ws['current'] = current
    second = save(ws, request_id='save-corrected-action-costs', parent=first['artifact']['artifact_id'],
        digest=first['document']['draft_digest'], citations=[item['citation'] for item in current['citation_candidates']['items']])['saved_work']
    assert second['document']['version'] == 2
    cold = BusinessDecisionWorkflow(action_actor=ws['actor'])
    reopened = cold.reopen(current['work_id'], actor_ref=ws['actor_ref'], scope=ws['domain_scope'], authorize=ws['authorize'])
    assert reopened['observation'] == current['observation']
    assert reopened['domain_execution'] == current['domain_execution']
    historical = cold.reopen(current['work_id'], actor_ref=ws['actor_ref'], scope=ws['domain_scope'],
        authorize=ws['authorize'], revision=first_revision)
    assert historical['observation'] == original
    assert ws['work'].reopen_work(first['artifact']['artifact_id'], actor=ws['actor'], scope=ws['scope'])['document'] == first['document']


def test_plan_change_retains_exact_unchanged_action_costs_and_original_refund_allocation(business):
    ws = business
    current = selected(ws)
    current = observe(ws, current, [cost('first-action-bill', 'ACTUAL', '20', action='verify-input'),
                                  cost('second-action-bill', 'ACTUAL', '10', action='follow-up')], 'cost-before-action-change')
    original_link = current['observation']['cost_ledger'][0]['planned_action']
    source_id = current['source_brief']['records'][0]['source_id']
    plan = domain_plan(source_id, bmp=ws['scope']['domain_id'] == 'zbmp')
    plan['actions'][1]['cost_estimate']['amount'] = '25'
    adopted = advance(ws, current, 'adopt', {'source_job_id': current['source_report']['job_id'],
        'question': 'Review this explicitly revised action estimate.', 'options': ws['options'],
        'decision': selection('B', '200'), 'reason': 'Only the follow-up action estimate changed.',
        'planning_constraints': {'domain_plan': plan}}, 'adopt-action-cost-change')
    assert adopted['domain_execution']['cost_review_state'] == 'PRIOR_PLAN_ONLY'
    assert adopted['observation']['cost_ledger'] == current['observation']['cost_ledger']
    revised = observe(ws, adopted, [cost('late-first-refund', 'REFUND', '5', related='first-action-bill')],
                      'refund-original-action-after-plan-change')
    review = revised['observation']['action_cost_review']
    assert revised['observation']['cost_ledger'][-1]['planned_action'] == original_link
    assert review['actions'][0]['reported_costs']['CNY']['net_actual'] == '15'
    assert set(review['actions'][0]['retained_prior_plan_entry_ids']) == {'first-action-bill', 'late-first-refund'}
    assert review['prior_plan_entry_ids'] == ['second-action-bill']
    assert review['actions'][1]['reported_costs'] == {}


def test_unknown_refund_true_zero_unallocated_and_foreign_currency_remain_distinct(business):
    ws = business
    current = selected(ws)
    current = observe(ws, current, [cost('reported-spend', 'ACTUAL', '20', action='verify-input'),
        cost('refund-unknown', 'REFUND', None, related='reported-spend'),
        cost('unlinked-spend', 'ACTUAL', '3'), cost('foreign-zero', 'ACTUAL', '0', currency='USD')], 'unknown-refund-and-fx')
    totals = current['observation']['cost_totals']
    assert totals['CNY']['ACTUAL'] == '23' and totals['CNY']['REFUND'] is None
    assert totals['CNY']['net_actual'] is None and totals['CNY']['unknown_amount_counts']['REFUND'] == 1
    assert totals['USD']['ACTUAL'] == '0' and totals['USD']['net_actual'] == '0'
    review = current['observation']['action_cost_review']
    assert set(review['unallocated_entry_ids']) == {'unlinked-spend', 'foreign-zero'}
    assert review['refund_checks'][0]['state'] == 'AMOUNT_UNKNOWN_CAP_NOT_ESTABLISHED'
    changed = observe(ws, current, [cost('refund-known-zero', 'REFUND', '0', related='reported-spend',
        supersedes='refund-unknown')], 'refund-observed-zero')
    assert changed['observation']['cost_totals']['CNY']['net_actual'] == '23'
    assert changed['observation']['resource_result']['remaining_budget_amount'] == '77'
    assert changed['observation']['resource_result']['state'] == 'PARTIAL_CURRENCY_CONVERSION_REQUIRED'
    assert changed['observation']['action_cost_review']['actions'][0]['remaining_against_declared_estimate'] == '80.50'


@pytest.mark.parametrize('fault', ['over_refund', 'correct_below_refund', 'branch_correction', 'currency_correction',
    'refund_action', 'correction_action', 'unknown_action', 'event_after_observation', 'refund_before_actual', 'missing_reason'])
def test_cost_refund_and_correction_failures_leave_no_business_revision(business, fault):
    ws = business
    current = selected(ws)
    current = observe(ws, current, [cost('actual-base', 'ACTUAL', '20', action='verify-input',
        occurred='2026-10-10T10:00:00+08:00'), cost('refund-base', 'REFUND', '5', related='actual-base')], 'cost-before-negative')
    if fault == 'over_refund':
        values = [cost('bad', 'REFUND', '16', related='actual-base')]
    elif fault == 'correct_below_refund':
        values = [cost('bad', 'ACTUAL', '4', supersedes='actual-base')]
    elif fault == 'branch_correction':
        values = [cost('first-correction', 'ACTUAL', '21', supersedes='actual-base'),
                  cost('bad', 'ACTUAL', '22', supersedes='actual-base')]
    elif fault == 'currency_correction':
        values = [cost('bad', 'ACTUAL', '20', supersedes='actual-base', currency='USD')]
    elif fault == 'refund_action':
        values = [cost('bad', 'REFUND', '1', related='actual-base', action='follow-up')]
    elif fault == 'correction_action':
        values = [cost('bad', 'ACTUAL', '20', supersedes='actual-base', action='follow-up')]
    elif fault == 'unknown_action':
        values = [cost('bad', 'ACTUAL', '1', action='foreign-action')]
    elif fault == 'event_after_observation':
        values = [cost('bad', 'ACTUAL', '1', occurred='2026-10-13T00:00:00+08:00')]
    elif fault == 'refund_before_actual':
        values = [cost('bad', 'REFUND', '1', related='actual-base', occurred='2026-10-09T00:00:00+08:00')]
    else:
        values = [cost('bad', 'ACTUAL', '21', supersedes='actual-base')]
        values[0].pop('correction_reason')
    # Source intake is separate; only the subsequent business mutation must be atomic.
    quote = 'Operator expense source for rejected candidate.'
    report, _ = add_material(ws, 'cost-negative-source', quote)
    payload = observation_payload(report, quote)
    payload.update(metrics=[], costs=values)
    before = ws['repo'].query_one('SELECT count(*) FROM app_evidence_records WHERE feature_id=?', (ws['service'].FEATURE,))[0]
    with pytest.raises(ValueError):
        advance(ws, current, 'observation', payload, 'reject-cost-' + fault)
    assert ws['repo'].query_one('SELECT count(*) FROM app_evidence_records WHERE feature_id=?', (ws['service'].FEATURE,))[0] == before
