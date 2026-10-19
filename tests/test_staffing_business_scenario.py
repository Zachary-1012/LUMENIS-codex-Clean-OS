"""Bounded business adaptation; no external hiring or allocation is performed."""
import copy
import pytest
from tests.test_saved_document_workflow import workspace
from lumenis.shared.evaluation.openai_math_papers.business_scenarios import (
    staffing_task_input, staffing_capability, GOAL,
)
from lumenis.shared.evaluation.openai_math_papers.dispatch import execute
from lumenis.shared.evaluation.openai_math_papers.core import Budget, ResourceBound


def example():
    return {'goal': GOAL, 'source_brief_job_id': 'source-job', 'request_id': 'a' * 32,
            'creators': [{'id': 'c1', 'label': 'Creator One'}, {'id': 'c2', 'label': 'Creator Two'}],
            'roles': [{'id': 'r1', 'label': 'Writing'}, {'id': 'r2', 'label': 'Editing'}],
            'eligible_pairs': [{'creator_id': c, 'role_id': r} for c in ['c1', 'c2'] for r in ['r1', 'r2']]}


def test_explicit_eligibility_maps_to_complete_uniform_scenario(workspace, monkeypatch):
    monkeypatch.setattr("lumenis.shared.database.get_repository", lambda: workspace["repo"])
    request = staffing_task_input(example())
    problem = request['context']['openai_math_problem']
    assert problem['parameters']['theta'] == [0] * 4
    assert 'DECLARED_MATHEMATICAL_SCENARIO' == request['context']['openai_math_declaration']['origin']
    result = execute(problem)['result']
    assert result['matching_count'] == 2
    assert len(result['distribution']) == 2
    assert 'not a behavioral probability' in request['context']['openai_math_declaration']['variable_map']['uniform_scenario']


def test_missing_eligibility_yields_infeasible_not_invented_edges(workspace, monkeypatch):
    monkeypatch.setattr("lumenis.shared.database.get_repository", lambda: workspace["repo"])
    body = example()
    body['eligible_pairs'] = []
    result = execute(staffing_task_input(body)['context']['openai_math_problem'])['result']
    assert result['state'] == 'INFEASIBLE'
    assert result['distribution'] == []


def test_budget_exhaustion_does_not_return_partial_uniform_support(workspace, monkeypatch):
    monkeypatch.setattr("lumenis.shared.database.get_repository", lambda: workspace["repo"])
    problem = staffing_task_input(example())['context']['openai_math_problem']
    with pytest.raises(ResourceBound, match='ENUMERATION_BUDGET_EXCEEDED'):
        execute(problem, budget=Budget(max_items=1))
    assert staffing_capability()['execution_limits']['complete_matchings'] == 10000
    assert 'does not guarantee completion' in staffing_capability()['budget_semantics']


@pytest.mark.parametrize('mutation', ['paper', 'theta', 'actor', 'duplicate', 'unequal', 'foreign', 'goal'])
def test_untrusted_parameters_and_mismatched_graph_reject(mutation):
    body = copy.deepcopy(example())
    if mutation in {'paper', 'theta', 'actor'}:
        body[mutation] = 'client-defined'
    elif mutation == 'duplicate':
        body['eligible_pairs'][1] = body['eligible_pairs'][0]
    elif mutation == 'unequal':
        body['roles'].pop()
    elif mutation == 'foreign':
        body['eligible_pairs'][0]['creator_id'] = 'unknown'
    else:
        body['goal'] = 'predict_real_hiring_success'
    with pytest.raises(ValueError):
        staffing_task_input(body)
