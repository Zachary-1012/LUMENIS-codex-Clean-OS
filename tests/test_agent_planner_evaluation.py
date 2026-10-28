"""Planner-to-Evaluation handoff at the typed Gateway boundary.

This is an isolated caller contract test. Its Gateway result is synthetic and
does not establish model execution or product acceptance.
"""
import json

import pytest


def _request():
    from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest

    return OwnedServiceRequest(
        operation='agent_plan', request_id='agent-plan:task-eval-contract',
        job_id='task-eval-contract', actor_ref='actor:synthetic-agent-user',
        domain_id='shared', scope='shared_workspace:v1',
        source_use_policy_version='agent-source-use:v1',
        source_use_policy_sha256='a' * 64, source_binding_sha256='b' * 64,
        source_evidence_refs=('user-task:task-eval-contract',),
        input_revision_sha256='c' * 64, system_prompt='bounded planner contract',
        user_payload='synthetic task text', response_schema_json='{}',
        max_output_tokens=128,
    )


@pytest.mark.parametrize('status,code,attempt_id,expected_fallback,tamper', [
    ('COMPLETED', 'OWNED_INFERENCE_COMPLETED', 'attempt_' + '1' * 32, False, None),
    ('COMPLETED', 'OWNED_INFERENCE_COMPLETED', None, True, None),
    ('COMPLETED', 'OWNED_INFERENCE_COMPLETED', 'attempt_' + '4' * 32, True, 'scope'),
    ('COMPLETED', 'OWNED_INFERENCE_COMPLETED', 'attempt_' + '5' * 32, True, 'request_digest'),
    ('ERROR', 'OWNED_RUNTIME_EXECUTION_FAILED', 'attempt_' + '2' * 32, True, None),
    ('CANCELLED', 'OWNED_SERVICE_CANCELLED', None, True, None),
    ('BLOCKED', 'CONTEXT_REQUIRED_INPUT_EXCEEDS_MODEL_BUDGET', None, True, None),
])
def test_agent_planner_hands_all_structured_gateway_outcomes_to_evaluation_owner(
        monkeypatch, status, code, attempt_id, expected_fallback, tamper):
    from agent_runtime.planner import Planner
    from lumenis.shared.evaluation import ai as evaluation
    from lumenis.system.ai_gateway import core, owned_service

    source_request = _request()
    calls = []
    monkeypatch.setattr(owned_service, 'measure_owned_request', lambda request: {
        'ok': True, 'fits': True, 'binding_sha256': 'd' * 64,
        'prompt_tokens': 11, 'count_method': 'synthetic_contract_test',
    })
    monkeypatch.setattr(owned_service, 'owned_service_status', lambda _domain: {
        'binding_sha256': 'd' * 64,
    })

    def gateway(request, **_kwargs):
        result = {'ok': status == 'COMPLETED', 'status': status, 'code': code,
                  'provider': 'owned', 'operation': request.operation,
                  'domain_id': request.domain_id, 'scope': request.scope,
                  'request_id': request.request_id,
                  'request_digest': owned_service.owned_service_request_digest(request)}
        if attempt_id:
            result['attempt_id'] = attempt_id
        if status == 'COMPLETED':
            result.update({
                'run_id': 'synthetic-run', 'model_id': 'synthetic-owned-cpu',
                'model_revision': 'synthetic-revision', 'recipe': 'test-only',
                'runtime_sha256': 'a' * 64, 'executor_sha256': 'b' * 64,
                'source_use_policy_version': request.source_use_policy_version,
                'source_use_policy_sha256': request.source_use_policy_sha256,
                'source_binding_sha256': request.source_binding_sha256,
                'input_revision_sha256': request.input_revision_sha256,
                'source_evidence_refs': list(request.source_evidence_refs),
                'prompt_tokens': 11, 'completion_tokens': 4, 'total_tokens': 15,
                'real_input_bound': True,
                'analysis': {'steps': [{
                    'action': 'Read authorized task input',
                    'tool': 'zbc.skill_registry_snapshot', 'params': {},
                    'expected_output': 'metadata', 'risk_level': 'low',
                }]},
            })
        if tamper == 'scope':
            result['scope'] = 'different-tenant-or-scope'
        elif tamper == 'request_digest':
            result['request_digest'] = 'f' * 64
        return result

    monkeypatch.setattr(core, 'run_owned_request', gateway)
    monkeypatch.setattr(evaluation, 'record_owned_gateway_execution',
                        lambda request, result, *, latency_ms: calls.append(
                            (request, result, latency_ms)))
    planner = Planner(gateway_request_factory=lambda *_args: source_request)
    plan = planner.plan('synthetic task', context={}, max_steps=1)

    assert len(calls) == 1
    recorded_request, recorded_result, latency_ms = calls[0]
    assert recorded_request.operation == 'agent_plan'
    assert recorded_request.job_id == 'task-eval-contract'
    assert recorded_result['status'] == status and recorded_result['code'] == code
    assert type(latency_ms) is int and latency_ms >= 0
    assert plan.is_fallback is expected_fallback
    if status == 'COMPLETED' and not expected_fallback:
        assert plan.steps and json.loads(plan.raw_response)['steps'][0]['tool'] == 'zbc.skill_registry_snapshot'


def test_durable_agent_receipt_requires_attempt_for_new_results_but_reads_legacy_receipts():
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    from lumenis.system.ai_gateway import owned_service

    request = _request()
    result = {
        'ok': True, 'status': 'COMPLETED', 'provider': 'owned', 'operation': 'agent_plan',
        'code': 'OWNED_INFERENCE_COMPLETED', 'domain_id': request.domain_id, 'scope': request.scope,
        'request_id': request.request_id,
        'request_digest': owned_service.owned_service_request_digest(request),
        'run_id': 'synthetic-run', 'model_id': 'synthetic-owned-cpu',
        'model_revision': 'synthetic-revision', 'recipe': 'test-only',
        'runtime_sha256': 'a' * 64, 'executor_sha256': 'b' * 64,
        'source_use_policy_version': request.source_use_policy_version,
        'source_use_policy_sha256': request.source_use_policy_sha256,
        'source_binding_sha256': request.source_binding_sha256,
        'input_revision_sha256': request.input_revision_sha256,
        'source_evidence_refs': list(request.source_evidence_refs),
        'prompt_tokens': 11, 'completion_tokens': 4, 'total_tokens': 15,
        'real_input_bound': True,
        'analysis': {'steps': [{'action': 'Read source metadata', 'tool': 'zbc.skill_registry_snapshot',
                               'params': {}, 'expected_output': 'metadata', 'risk_level': 'low'}]},
    }
    budget = {
        'ok': True, 'fits': True, 'prompt_tokens': 11, 'context_window_tokens': 512,
        'output_token_limit': 128, 'output_tokens_reserved': 128,
        'request_sha256': result['request_digest'], 'runtime_sha256': 'a' * 64,
        'tokenizer_identity': 'a' * 64, 'formatter_sha256': 'b' * 64,
        'count_method': 'loaded_runtime_tokenizer', 'generation_performed': False,
        'binding_sha256': 'c' * 64,
    }

    with pytest.raises(RuntimeError, match='^AGENT_MODEL_RECEIPT_INVALID$'):
        DurableExecutionAdapter._checked_model_response(request, result, budget)

    legacy_fields = {
        'ok', 'provider', 'status', 'operation', 'request_id', 'request_digest', 'run_id',
        'model_id', 'model_revision', 'recipe', 'source_use_policy_sha256',
        'source_binding_sha256', 'input_revision_sha256', 'source_evidence_refs',
        'prompt_tokens', 'completion_tokens', 'total_tokens', 'real_input_bound', 'analysis',
    }
    legacy_result, _ = DurableExecutionAdapter._checked_model_response(
        request, {key: value for key, value in result.items() if key in legacy_fields}, budget,
        allow_legacy_attempt_receipt=True,
    )
    assert 'attempt_id' not in legacy_result

    result['attempt_id'] = 'attempt_' + '3' * 32
    current_result, _ = DurableExecutionAdapter._checked_model_response(request, result, budget)
    assert current_result['attempt_id'] == result['attempt_id']
