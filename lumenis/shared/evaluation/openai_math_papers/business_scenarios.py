"""Business inputs for existing bounded mathematical tasks; no new solver/store."""
import re

from .core import Budget, MathInputError
from .matching_113 import Graph
from .product_outcome import freeze_problem

GOAL = 'assess_complete_staffing_options'


def staffing_capability():
    budget = Budget()
    return {
        'goal': GOAL, 'method': 'matching.gibbs', 'family': '113',
        'applicability': 'Equal numbers of creators and roles; one creator per role and one role per creator; explicitly declared eligible pairs.',
        'max_each_side': 12, 'max_graph_vertices': 24,
        'execution_limits': {'seconds': budget.seconds, 'steps': budget.max_steps,
                             'complete_matchings': budget.max_items, 'rational_bits': budget.max_bits},
        'budget_semantics': 'Dimension admission does not guarantee completion; full enumeration and all marginals must finish within the original budget. No truncated support is returned as a uniform distribution.',
        'inputs_origin': 'USER_DECLARED_SCENARIO; source brief is retained context, not proof of eligibility.',
        'output_semantics': 'Complete feasible configurations and numerical uniform-scenario edge marginals; not hiring likelihood, optimal-cost scheduling, or general-graph FPRAS.',
        'ai_required': False,
    }


def _entities(value, kind):
    if not isinstance(value, list) or not 1 <= len(value) <= 12:
        raise MathInputError('STAFFING_EQUAL_BOUNDED_SETS_REQUIRED')
    output = []
    seen = set()
    for item in value:
        if (not isinstance(item, dict) or set(item) != {'id', 'label'}
                or not isinstance(item['id'], str)
                or re.fullmatch(r'[A-Za-z0-9_-]{1,60}', item['id']) is None
                or item['id'] in seen or not isinstance(item['label'], str)
                or not 1 <= len(item['label'].strip()) <= 200
                or any(ord(char) < 32 for char in item['label'])):
            raise MathInputError('STAFFING_ENTITY_INVALID')
        seen.add(item['id'])
        output.append({'id': item['id'], 'label': item['label'].strip(), 'kind': kind})
    return output


def staffing_task_input(body):
    if not isinstance(body, dict) or set(body) - {
        'goal', 'source_brief_job_id', 'request_id', 'creators', 'roles',
        'eligible_pairs', 'parent_artifact_id',
    }:
        raise MathInputError('STAFFING_REQUEST_INVALID')
    if body.get('goal') != GOAL:
        raise MathInputError('STAFFING_GOAL_UNSUPPORTED')
    if not isinstance(body.get('source_brief_job_id'), str) or not body['source_brief_job_id']:
        raise MathInputError('STAFFING_SOURCE_BRIEF_REQUIRED')
    if not isinstance(body.get('request_id'), str) or re.fullmatch(r'[0-9a-f]{32}', body['request_id']) is None:
        raise MathInputError('MATHEMATICAL_REQUEST_ID_REQUIRED')
    creators, roles = _entities(body.get('creators'), 'creator'), _entities(body.get('roles'), 'role')
    if len(creators) != len(roles):
        raise MathInputError('STAFFING_EQUAL_BOUNDED_SETS_REQUIRED')
    creator_index = {row['id']: index for index, row in enumerate(creators)}
    role_index = {row['id']: len(creators) + index for index, row in enumerate(roles)}
    pairs = body.get('eligible_pairs')
    if not isinstance(pairs, list) or len(pairs) > len(creators) * len(roles):
        raise MathInputError('STAFFING_ELIGIBILITY_INVALID')
    edges = []
    for pair in pairs:
        if (not isinstance(pair, dict) or set(pair) != {'creator_id', 'role_id'}
                or not isinstance(pair['creator_id'], str) or not isinstance(pair['role_id'], str)
                or pair['creator_id'] not in creator_index or pair['role_id'] not in role_index):
            raise MathInputError('STAFFING_ELIGIBILITY_INVALID')
        edge = [creator_index[pair['creator_id']], role_index[pair['role_id']]]
        if edge in edges:
            raise MathInputError('STAFFING_DUPLICATE_ELIGIBILITY')
        edges.append(edge)
    graph = {'vertices': len(creators) + len(roles), 'edges': sorted(edges)}
    Graph.read(graph)
    problem = {'operation': 'matching.gibbs', 'parameters': {
        'graph': graph, 'theta': [0] * len(edges), 'covariance': False}}
    variable_map = {str(index): row['kind'] + ': ' + row['id'] + ' / ' + row['label']
                    for index, row in enumerate(creators + roles)}
    variable_map['eligible_edges'] = 'Explicit user-declared eligibility only; no source-derived identity or suitability claim.'
    variable_map['uniform_scenario'] = 'All eligible complete assignments weighted equally; not a behavioral probability or optimal-cost recommendation.'
    declaration = {'origin': 'DECLARED_MATHEMATICAL_SCENARIO',
                   'purpose': 'Assess complete creator-to-role staffing options under explicitly declared one-to-one eligibility constraints.',
                   'variable_map': variable_map}
    problem, declaration, _ = freeze_problem(problem, declaration)
    context = {'analysis_operation': 'openai_math', 'source_brief_job_id': body['source_brief_job_id'],
               'openai_math_request_id': body['request_id'], 'openai_math_problem': problem,
               'openai_math_declaration': declaration}
    if body.get('parent_artifact_id') is not None:
        context['openai_math_parent_artifact_id'] = body['parent_artifact_id']
    return {'input': declaration['purpose'], 'context': context}
