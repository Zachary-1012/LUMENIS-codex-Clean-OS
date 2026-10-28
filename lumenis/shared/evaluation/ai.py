# -*- coding: utf-8 -*-
"""
lumenis.shared.evaluation.ai — LUMENIS Shared Evaluation AI 质量评估

核心原则：AI 是辅助判断层，永远不替代核心确定性规则。
评估体系追踪 AI 与规则的一致性、已记录的人工修正、Provider 可靠性，
形成「AI 输出 → 规则对比 → 人工修正 → 规则沉淀」的闭环。

追踪指标：
- 规则一致率（rule_agreement_rate；ai_accuracy为兼容别名）：不是独立正确率
- AI 替代率（ai_replacement_rate）：最终结果采用 AI 而非规则的比例
- 人工修正数（human_correction_count）；没有复核分母时修正率保持未知
- 置信度分布（confidence_distribution）：低/中/高置信度占比
- Provider 失败率（provider_failure_rate）：按 provider 统计失败比例
- 回退率（fallback_rate）：AI 失败回退到规则的比例
- 延迟（latency）：平均/分位延迟
- Token 成本（token_cost）：总 token 用量估算

所有计算基于 ai_call_logs 表，纯只读，不修改生产数据。
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import ai_call_logger as acl
from lumenis.shared.database import get_repository

_OWNED_EXECUTION_SCHEMA = 'lumenis.owned-ai-execution/v1'
_CONTEXT_EXCLUSION_DECISION = 'USER_EXCLUDED_FROM_FUTURE_CONTEXT'
_EVALUATION_CALL_REF = re.compile(r'^ai-call:v1:([1-9][0-9]{0,15}):([0-9a-f]{64})$')
_CONVERSATION_REQUEST_ID = re.compile(r'^(turn_[0-9a-f]{32}):([0-9a-f]{64})$')


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _stable_hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def owned_gateway_output_sha256(result) -> str:
    """Return the digest used by owned-Gateway evaluation rows, without content."""
    if type(result) is not dict:
        return ''
    text = result.get('text')
    analysis = result.get('analysis')
    if type(text) is str:
        return _sha256_text(text)
    if type(analysis) is str:
        return _sha256_text(analysis)
    if type(analysis) in (dict, list):
        return _stable_hash({'analysis': analysis})
    return ''


def _safe_version(value, limit=256):
    if type(value) is not str or not value or len(value) > limit:
        return ''
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return ''
    return value


def _owned_execution_binding(request):
    """Build the actor/task/source binding shared by write and readback paths."""
    from lumenis.system.ai_gateway.owned_service import (
        OwnedServiceRequest, owned_service_request_digest, validate_owned_service_request,
    )
    if type(request) is not OwnedServiceRequest:
        return None
    try:
        validate_owned_service_request(request)
        request_digest = owned_service_request_digest(request)
    except Exception:
        return None
    target_match = _CONVERSATION_REQUEST_ID.fullmatch(request.request_id)
    is_conversation = (request.domain_id == 'shared'
        and bool(re.fullmatch(r'conv_[0-9a-f]{32}', request.job_id))
        and target_match is not None)
    turn_id = target_match.group(1) if is_conversation else ''
    binding = {
        'actor_ref_sha256': _sha256_text(request.actor_ref),
        'scope_sha256': _sha256_text(request.scope),
        'domain_id': request.domain_id,
        'task_id': request.job_id,
        'conversation_id': request.job_id if is_conversation else '',
        'turn_id': turn_id,
        'request_id_sha256': _sha256_text(request.request_id),
        'request_digest': request_digest,
        'input_revision_sha256': request.input_revision_sha256,
        'source_binding_sha256': request.source_binding_sha256,
        'source_use_policy_sha256': request.source_use_policy_sha256,
        'operation': request.operation,
    }
    return request_digest, binding, _stable_hash(binding), is_conversation, turn_id


def _owned_execution_record(request, result, *, latency_ms=None):
    """Build a content-free record for an actual typed owned-Gateway request."""
    if type(result) is not dict:
        return None
    identity = _owned_execution_binding(request)
    if identity is None:
        return None
    request_digest, binding, binding_sha256, is_conversation, turn_id = identity

    attempt_id = result.get('attempt_id')
    attempt_id = attempt_id if type(attempt_id) is str and re.fullmatch(
        r'attempt_[0-9a-f]{32}', attempt_id) else ''
    generated = bool(attempt_id)
    result_status = _safe_version(result.get('status'), 64).upper()
    code = _safe_version(result.get('code'), 96)
    result_digest = result.get('request_digest')
    exact_digest = result_digest == request_digest
    successful = (
        result.get('ok') is True and result_status == 'COMPLETED' and generated
        and result.get('real_input_bound') is True and exact_digest
        and result.get('input_revision_sha256') == request.input_revision_sha256
        and result.get('domain_id') == request.domain_id
        and result.get('scope') == request.scope
        and result.get('operation') == request.operation
        and result.get('source_binding_sha256') == request.source_binding_sha256
        and bool(_safe_version(result.get('run_id'), 512))
    )
    if successful:
        state = 'COMPLETED'
    elif result_status == 'CANCELLED' or code in {
            'OWNED_SERVICE_CANCELLED', 'OWNED_INFERENCE_CANCELLED', 'CONTEXT_CANCELLED'}:
        state = 'CANCELLED'
    elif not generated and code == 'OWNED_SERVICE_EXECUTOR_NOT_BOUND':
        state = 'NOT_BOUND'
    elif not generated and ('BUDGET' in code or code == 'CONTEXT_REQUIRED_INPUT_EXCEEDS_MODEL_BUDGET'):
        state = 'BUDGET_BLOCKED'
    elif not generated and (result_status in {'PERMISSION_DENIED', 'FORBIDDEN'}
            or 'PERMISSION' in code or 'AUTHORIZATION' in code):
        state = 'PERMISSION_DENIED'
    elif not generated and result_status in {'INVALID_INPUT', 'UNAVAILABLE'}:
        state = result_status
    elif generated:
        state = 'FAILED'
    elif result_status == 'COMPLETED':
        # A success-shaped result without the server-issued attempt and exact
        # request binding is not a model result and cannot count as success.
        state = 'UNVERIFIED_COMPLETION'
    else:
        state = 'PRECHECK_BLOCKED'

    versions = {}
    for key in ('model_id', 'model_revision', 'recipe', 'runtime_sha256', 'executor_sha256',
                'manifest_sha256', 'artifact_identity_sha256', 'candidate_identity_sha256',
                'adapter_sha256', 'adapter_config_sha256', 'evaluation_sha256',
                'quality_review_sha256'):
        safe = _safe_version(result.get(key), 128 if key in {'model_id', 'model_revision', 'recipe'} else 64)
        if safe:
            versions[key] = safe
    run_id = _safe_version(result.get('run_id'), 96)
    if run_id:
        versions['run_id'] = run_id
    if attempt_id:
        versions['attempt_id'] = attempt_id

    safe_result = {
        'schema': _OWNED_EXECUTION_SCHEMA,
        'state': state,
        'generation_performed': generated,
        'result_status': result_status or 'UNKNOWN',
        'code': code or 'UNKNOWN',
        'binding': binding,
        'binding_sha256': binding_sha256,
        'versions': versions,
    }
    encoded_result = json.dumps(safe_result, ensure_ascii=False, sort_keys=True,
                                separators=(',', ':'), allow_nan=False)
    if len(encoded_result) > 1900:
        versions = {key: value for key, value in versions.items()
                    if key in {'model_id', 'model_revision', 'runtime_sha256',
                               'executor_sha256', 'run_id', 'attempt_id'}}
        safe_result['versions'] = versions
        encoded_result = json.dumps(safe_result, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False)
    if len(encoded_result) > 2000:
        return None
    output_hash = owned_gateway_output_sha256(result) if successful else ''

    tokens = result.get('total_tokens')
    tokens = tokens if successful and type(tokens) is int and tokens >= 0 else None
    latency_ms = latency_ms if type(latency_ms) in (int, float) and latency_ms >= 0 else None
    record = {
        'provider': 'owned',
        'model': versions.get('model_id', ''),
        'prompt_version': request.source_use_policy_version,
        'input_hash': request.input_revision_sha256,
        'input_text': '',
        'output': '',
        'output_hash': output_hash,
        'task_id': request.job_id,
        'trace_id': request.request_id,
        'domain_id': request.domain_id,
        'product_id': {'shared': 'SHARED', 'cth': 'CTH', 'bmp': 'BMP'}.get(request.domain_id, ''),
        'target_type': 'ai_conversation_turn' if is_conversation else 'ai_owned_request',
        'target_id': turn_id if is_conversation else request.job_id,
        'model_version': versions.get('model_revision', ''),
        'system_result': encoded_result,
        # Keep final_decision reserved for explicit human disposition; runtime
        # state lives in the versioned system_result payload above.
        'final_decision': '',
        'failure_reason': '' if successful else (code or state),
        'success': successful,
        'token_usage': tokens,
        'latency_ms': latency_ms,
    }
    return record, binding_sha256, is_conversation


def record_owned_gateway_execution(request, result, *, latency_ms=None):
    """Record only hashes and typed execution metadata; never prompt/output text.

    A row is successful only when the server issued a generation attempt and the
    completed result matches the exact typed request, input version and bindings.
    Pre-generation outcomes remain visible with their own non-success state.
    """
    built = _owned_execution_record(request, result, latency_ms=latency_ms)
    if built is None:
        return None
    record, binding_sha256, _is_conversation = built
    call_id = acl.log_call(**record)
    if type(call_id) is not int or call_id < 1:
        return None
    return f'ai-call:v1:{call_id}:{binding_sha256}'


def verify_owned_gateway_execution_ref(evaluation_ref, request, *, expected_provenance):
    """Read back the exact successful Gateway record for a saved owned result.

    The opaque reference and attempt-id shape are not sufficient by themselves:
    this verifies the row's request, actor/scope binding, completed state, model
    identity and output digest against the typed request and saved provenance.
    """
    identity = _owned_execution_binding(request)
    match = _EVALUATION_CALL_REF.fullmatch(evaluation_ref) if type(evaluation_ref) is str else None
    if identity is None or match is None or type(expected_provenance) is not dict:
        return 'NOT_LINKED'
    _, binding, binding_sha256, is_conversation, turn_id = identity
    if match.group(2) != binding_sha256:
        return 'NOT_LINKED'
    expected = {
        'attempt_id': expected_provenance.get('attempt_id'),
        'run_id': expected_provenance.get('run_id'),
        'model_id': expected_provenance.get('model_id'),
        'model_revision': expected_provenance.get('model_revision'),
        'runtime_sha256': expected_provenance.get('runtime_sha256'),
        'executor_sha256': expected_provenance.get('executor_sha256'),
        'output_sha256': expected_provenance.get('evaluation_output_sha256'),
    }
    if (any(type(value) is not str or not value for value in expected.values())
            or not re.fullmatch(r'attempt_[0-9a-f]{32}', expected['attempt_id'])
            or any(not re.fullmatch(r'[0-9a-f]{64}', expected[key])
                   for key in ('runtime_sha256', 'executor_sha256', 'output_sha256'))):
        return 'NOT_LINKED'
    try:
        call_id = int(match.group(1))
        with get_repository().connection(read_only=True, wal=False) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute('''SELECT id,provider,model,prompt_version,input_hash,output_hash,
                    success,task_id,trace_id,domain_id,product_id,target_type,target_id,model_version,
                    system_result
                FROM ai_call_logs WHERE id=?''', (call_id,)).fetchone()
    except sqlite3.Error:
        return 'UNAVAILABLE'
    except Exception:
        return 'UNAVAILABLE'
    if row is None:
        return 'NOT_LINKED'
    try:
        payload = json.loads(row['system_result'] or '{}')
        versions = payload.get('versions')
        target_type = 'ai_conversation_turn' if is_conversation else 'ai_owned_request'
        target_id = turn_id if is_conversation else request.job_id
        product_id = {'shared': 'SHARED', 'cth': 'CTH', 'bmp': 'BMP'}.get(request.domain_id, '')
        valid = (
            payload.get('schema') == _OWNED_EXECUTION_SCHEMA
            and payload.get('state') == 'COMPLETED'
            and payload.get('generation_performed') is True
            and payload.get('result_status') == 'COMPLETED'
            and payload.get('code') == 'OWNED_INFERENCE_COMPLETED'
            and payload.get('binding') == binding
            and payload.get('binding_sha256') == binding_sha256
            and type(versions) is dict
            and all(versions.get(key) == expected[key] for key in (
                'attempt_id', 'run_id', 'model_id', 'model_revision',
                'runtime_sha256', 'executor_sha256'))
            and row['id'] == call_id and row['provider'] == 'owned' and row['success'] == 1
            and row['model'] == expected['model_id']
            and row['model_version'] == expected['model_revision']
            and row['prompt_version'] == request.source_use_policy_version
            and row['input_hash'] == request.input_revision_sha256
            and row['output_hash'] == expected['output_sha256']
            and row['task_id'] == request.job_id and row['trace_id'] == request.request_id
            and row['domain_id'] == request.domain_id and row['product_id'] == product_id
            and row['target_type'] == target_type and row['target_id'] == target_id
        )
    except (TypeError, ValueError, AttributeError):
        valid = False
    return 'VERIFIED' if valid else 'NOT_LINKED'


def _conversation_feedback_row(connection, evaluation_ref, *, actor_ref, scope,
                                conversation_id, turn_id):
    if (not isinstance(connection, sqlite3.Connection)
            or any(type(value) is not str or not value for value in
                   (actor_ref, scope, conversation_id, turn_id))):
        return None, 'NOT_LINKED'
    match = _EVALUATION_CALL_REF.fullmatch(evaluation_ref) if type(evaluation_ref) is str else None
    if not match:
        return None, 'NOT_LINKED'
    try:
        call_id = int(match.group(1))
        row = connection.execute('''SELECT id,provider,success,task_id,trace_id,domain_id,product_id,
                target_type,target_id,model_version,system_result,final_decision
            FROM ai_call_logs WHERE id=?''', (call_id,)).fetchone()
    except sqlite3.Error:
        return None, 'UNAVAILABLE'
    if row is None:
        return None, 'NOT_LINKED'
    try:
        result = json.loads(row['system_result'] or '{}')
        binding = result.get('binding')
        valid = (
            result.get('schema') == _OWNED_EXECUTION_SCHEMA
            and result.get('state') == 'COMPLETED'
            and result.get('generation_performed') is True
            and type(binding) is dict
            and _stable_hash(binding) == match.group(2) == result.get('binding_sha256')
            and binding.get('actor_ref_sha256') == _sha256_text(actor_ref)
            and binding.get('scope_sha256') == _sha256_text(scope)
            and binding.get('domain_id') == 'shared'
            and binding.get('task_id') == conversation_id
            and binding.get('conversation_id') == conversation_id
            and binding.get('turn_id') == turn_id
            and row['provider'] == 'owned' and row['success'] == 1
            and row['task_id'] == conversation_id and row['domain_id'] == 'shared'
            and row['product_id'] == 'SHARED'
            and row['target_type'] == 'ai_conversation_turn' and row['target_id'] == turn_id
        )
    except (TypeError, ValueError, AttributeError):
        valid = False
    if not valid:
        return None, 'NOT_LINKED'
    return dict(row), 'LINKED'


def inspect_conversation_turn_feedback(connection, evaluation_ref, *, actor_ref, scope,
                                       conversation_id, turn_id):
    """Read the exact saved feedback state for one actor/scope/turn-bound call."""
    row, state = _conversation_feedback_row(connection, evaluation_ref, actor_ref=actor_ref,
        scope=scope, conversation_id=conversation_id, turn_id=turn_id)
    if row is None:
        return state
    return ('RECORDED' if row['final_decision'] == _CONTEXT_EXCLUSION_DECISION
            else 'NOT_RECORDED')


def record_conversation_turn_exclusion(connection, evaluation_ref, *, actor_ref, scope,
                                       conversation_id, turn_id):
    """Atomically attach a constant human exclusion decision to a verified call.

    The conversation owner supplies its already-authorized transaction, so the
    context exclusion and this feedback marker commit or roll back together.
    Raw prompt, answer and user-authored correction text are never stored here.
    """
    row, state = _conversation_feedback_row(connection, evaluation_ref, actor_ref=actor_ref,
        scope=scope, conversation_id=conversation_id, turn_id=turn_id)
    if row is None:
        return state
    if row['final_decision'] == _CONTEXT_EXCLUSION_DECISION:
        return 'ALREADY_RECORDED'
    if row['final_decision']:
        return 'CONFLICT'
    try:
        changed = connection.execute('''UPDATE ai_call_logs SET final_decision=?
            WHERE id=? AND success=1 AND target_type='ai_conversation_turn' AND target_id=?
              AND (final_decision IS NULL OR final_decision='')''',
            (_CONTEXT_EXCLUSION_DECISION, row['id'], turn_id)).rowcount
    except sqlite3.Error:
        return 'UNAVAILABLE'
    if changed == 1:
        return 'RECORDED'
    try:
        current = connection.execute('SELECT final_decision FROM ai_call_logs WHERE id=?',
                                     (row['id'],)).fetchone()
    except sqlite3.Error:
        return 'UNAVAILABLE'
    if current and current[0] == _CONTEXT_EXCLUSION_DECISION:
        return 'ALREADY_RECORDED'
    return 'CONFLICT'

# ============================================================
# 1) 数据库连接（由 Shared Database 在调用时解析唯一运行库）
# ============================================================


def _conn():
    # Keep database selection dynamic so tests, workers and runtime overrides all
    # use the same canonical repository/path as ai_call_logger.
    conn = get_repository().connect(timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# 2) 规则 vs AI 对比记录
# ============================================================
def record_rule_vs_ai(
    provider: str,
    model: str,
    rule_result: str,
    ai_result: str,
    final_result: str,
    confidence: Optional[Union[int, float]] = None,
    prompt_version: str = '',
    input_hash: str = '',
    latency_ms: Optional[Union[int, float]] = None,
    token_usage: Optional[int] = None,
    success: bool = True,
    failure_reason: str = '',
) -> Optional[int]:
    """
    记录一次规则与 AI 的对比。这是 Evaluation 的核心数据来源。

    Args:
        rule_result: 确定性规则引擎的结果（JSON 字符串或文本）
        ai_result: AI 的输出结果
        final_result: 最终采用的结果（通常是规则优先，AI 仅辅助）
        其余字段同 ai_call_logger.log_call

    Returns:
        调用日志 id
    """
    return acl.log_call(
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        input_hash=input_hash,
        output=ai_result,
        confidence=confidence,
        rule_result=rule_result,
        final_result=final_result,
        latency_ms=latency_ms,
        token_usage=token_usage,
        failure_reason=failure_reason,
        success=success,
    )


def _results_match(rule: str, ai: str) -> bool:
    """
    判断规则结果与 AI 结果是否一致。
    优先尝试 JSON 解析后对比关键字段；否则做文本归一化对比。
    """
    if not rule and not ai:
        return True
    if not rule or not ai:
        return False

    # 尝试 JSON 对比
    try:
        rj = json.loads(rule) if isinstance(rule, str) else rule
        aj = json.loads(ai) if isinstance(ai, str) else ai
        if isinstance(rj, dict) and isinstance(aj, dict):
            # 对比核心字段：sentiment / risk_level / relevance / verification / status
            key_fields = ['sentiment', 'risk_level', 'relevance', 'verification',
                          'status', 'label', 'category']
            r_vals = {k: rj.get(k) for k in key_fields if k in rj}
            a_vals = {k: aj.get(k) for k in key_fields if k in aj}
            if r_vals and a_vals:
                return r_vals == a_vals
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # 文本归一化对比
    def _norm(s: str) -> str:
        return ''.join(str(s).split()).lower()

    return _norm(rule) == _norm(ai)


def _owned_execution_payload(row):
    try:
        value = json.loads(row.get('system_result') or '{}')
    except (TypeError, ValueError):
        return None
    if type(value) is dict and value.get('schema') == _OWNED_EXECUTION_SCHEMA:
        return value
    return None


# ============================================================
# 3) 核心评估函数：evaluate_ai_quality
# ============================================================
def evaluate_ai_quality(since: str = '', provider: str = '', limit: int = 5000) -> Dict[str, Any]:
    """Read measured quality signals; absent denominators remain unknown.

     ``ai_accuracy`` is a compatibility alias of rule_agreement_rate, NOT an
     independent accuracy benchmark. Contract v3 also separates owned Gateway
     execution, cancellation and pre-generation outcomes.
    """
    import math
    if type(limit) is not int or not 1 <= limit <= 50000:
        raise ValueError('AI_EVALUATION_LIMIT_INVALID')
    def rounded_ratio(numerator, denominator):
        return round(numerator / denominator, 4) if denominator else None
    def numbers(rows, key, maximum=None):
        result = []
        for row in rows:
            raw = row.get(key)
            if raw is None or isinstance(raw, bool):
                continue
            try:
                value = float(raw)
            except (ValueError, TypeError, OverflowError):
                continue
            if math.isfinite(value) and value >= 0 and (maximum is None or value <= maximum):
                result.append(value)
        return result
    empty = {
        'metric_contract': 'lumenis.ai-quality/v3', 'state': 'NO_SAMPLES',
        'total_calls': 0, 'success_count': 0, 'failure_count': 0,
        'cancelled_count': 0, 'cancelled_before_generation_count': 0,
        'not_executed_count': 0,
        'not_executed_states': {},
        'conversation_context_exclusion_count': 0,
        'execution_counts': {'attempted': 0, 'completed': 0, 'failed': 0,
                             'cancelled': 0, 'cancelled_before_generation': 0,
                             'not_executed': 0,
                             'not_executed_states': {}},
        'rule_agreement_rate': None, 'ai_accuracy': None,
        'ai_accuracy_semantics': 'COMPATIBILITY_ALIAS_RULE_AGREEMENT_NOT_GROUND_TRUTH',
        'independent_accuracy': None, 'independent_accuracy_state': 'NOT_MEASURED',
        'ai_replacement_rate': None, 'human_correction_count': 0,
        'human_correction_rate': None,
        'human_correction_state': 'NO_SAMPLES',
        'human_review_coverage': {'state': 'unknown', 'reviewed_calls': None, 'coverage_rate': None},
        'confidence_distribution': {'low': None, 'medium': None, 'high': None},
        'provider_failure_rate': {}, 'fallback_rate': None,
        'latency': {'avg_ms': None, 'p50_ms': None, 'p95_ms': None, 'max_ms': None},
        'token_cost': {'total_tokens': None, 'avg_tokens': None},
        'sample_counts': {'rule_comparisons': 0, 'final_comparisons': 0,
                          'confidence': 0, 'confidence_ambiguous_zero': 0,
                          'confidence_unknown': 0, 'latency': 0,
                          'latency_ambiguous_zero': 0, 'latency_unknown': 0,
                          'token_usage': 0, 'human_correction_observations': 0},
        'period': {'since': since, 'until': '', 'sampled': 0},
    }
    try:
        conn = _conn()
        try:
            sql = 'SELECT * FROM ai_call_logs WHERE 1=1'; params = []
            if since:
                sql += ' AND created_at >= ?'; params.append(since)
            if provider:
                sql += ' AND provider = ?'; params.append(provider)
            sql += ' ORDER BY id DESC LIMIT ?'; params.append(limit)
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
    except Exception as exc:
        return {**empty, 'state': 'UNAVAILABLE', 'error': type(exc).__name__,
                'reason': 'AI_EVALUATION_QUERY_FAILED', 'total_calls': None,
                'success_count': None, 'failure_count': None,
                'human_correction_count': None,
                'human_correction_state': 'UNAVAILABLE',
                'sample_counts': {key: None for key in empty['sample_counts']},
                'period': {'since': since, 'until': '', 'sampled': None}}
    if not rows:
        return empty
    tagged = {}
    for row in rows:
        execution = _owned_execution_payload(row)
        if execution is not None:
            tagged[row['id']] = execution
    legacy = [row for row in rows if row.get('id') not in tagged]
    tracked_completed = [row for row in rows if row.get('id') in tagged
        and tagged[row['id']].get('generation_performed') is True
        and tagged[row['id']].get('state') == 'COMPLETED' and row.get('success') == 1]
    tracked_cancelled = [row for row in rows if row.get('id') in tagged
        and tagged[row['id']].get('state') == 'CANCELLED']
    tracked_cancelled_before_generation = [row for row in tracked_cancelled
        if tagged[row['id']].get('generation_performed') is not True]
    tracked_failed = [row for row in rows if row.get('id') in tagged
        and tagged[row['id']].get('generation_performed') is True
        and tagged[row['id']].get('state') not in {'COMPLETED', 'CANCELLED'}]
    tracked_not_executed = [row for row in rows if row.get('id') in tagged
        and tagged[row['id']].get('generation_performed') is not True
        and tagged[row['id']].get('state') != 'CANCELLED']
    success = [row for row in legacy if row.get('success') == 1] + tracked_completed
    failure = [row for row in legacy if row.get('success') == 0] + tracked_failed
    not_executed_states = {}
    for row in tracked_not_executed:
        state = tagged[row['id']].get('state') or 'UNKNOWN'
        not_executed_states[state] = not_executed_states.get(state, 0) + 1
    execution_rows = [row for row in rows if row.get('id') not in tagged]
    execution_rows.extend(row for row in rows if row.get('id') in tagged
        and tagged[row['id']].get('generation_performed') is True
        and tagged[row['id']].get('state') != 'CANCELLED')
    comparable = [row for row in success if row.get('rule_result') and row.get('output')]
    agreement = rounded_ratio(sum(_results_match(row['rule_result'], row['output']) for row in comparable), len(comparable))
    final = [row for row in success if row.get('final_result') and row.get('output')]
    replaced = sum(_results_match(row['final_result'], row['output']) and
                   not (row.get('rule_result') and _results_match(row['rule_result'], row['output'])) for row in final)
    raw_confidences = numbers(success, 'confidence', 1)
    confidence_zero_samples = sum(value == 0 for value in raw_confidences)
    # Old logger versions defaulted absent confidence to 0. Without a versioned
    # observation marker those zeros cannot safely be treated as measured.
    confidences = [value for value in raw_confidences if value > 0]
    raw_latencies = numbers(success, 'latency_ms')
    latency_zero_samples = sum(value == 0 for value in raw_latencies)
    # Legacy schema defaults also wrote 0 for unknown latency; exclude ambiguous
    # zero rows from timing estimates while exposing their count below.
    latencies = sorted(value for value in raw_latencies if value > 0)
    tokens = numbers(success, 'token_usage')
    correction_count = sum(bool(row.get('human_correction')) for row in rows)
    context_exclusion_count = sum(
        row.get('id') in tagged and row.get('target_type') == 'ai_conversation_turn'
        and row.get('final_decision') == _CONTEXT_EXCLUSION_DECISION for row in rows)
    confidence_unknown = max(0, len(success) - len(raw_confidences))
    latency_unknown = max(0, len(success) - len(raw_latencies))
    providers = {}
    for row in execution_rows:
        name = row.get('provider') or 'unknown'
        record = providers.setdefault(name, {'total': 0, 'failures': 0, 'known': 0})
        record['total'] += 1; record['failures'] += row.get('success') == 0
        record['known'] += row.get('success') in (0, 1)
    return {
        **empty, 'state': 'OBSERVED', 'total_calls': len(rows),
        'success_count': len(success), 'failure_count': len(failure),
        'cancelled_count': len(tracked_cancelled),
        'cancelled_before_generation_count': len(tracked_cancelled_before_generation),
        'not_executed_count': len(tracked_not_executed),
        'not_executed_states': not_executed_states,
        'conversation_context_exclusion_count': context_exclusion_count,
        'execution_counts': {
            'attempted': (len(tracked_completed) + len(tracked_failed)
                + sum(row.get('id') in tagged and tagged[row['id']].get('generation_performed') is True
                      for row in tracked_cancelled)),
            'completed': len(tracked_completed), 'failed': len(tracked_failed),
            'cancelled': len(tracked_cancelled),
            'cancelled_before_generation': len(tracked_cancelled_before_generation),
            'not_executed': len(tracked_not_executed),
            'not_executed_states': not_executed_states,
        },
        'rule_agreement_rate': agreement, 'ai_accuracy': agreement,
        'ai_replacement_rate': rounded_ratio(replaced, len(final)),
        'human_correction_count': correction_count,
        'human_correction_rate': None,
        'human_correction_state': 'REVIEW_DENOMINATOR_NOT_RECORDED',
        'human_review_coverage': {
            'state': 'unknown', 'reviewed_calls': None, 'coverage_rate': None,
        },
        'confidence_distribution': {
            'low': rounded_ratio(sum(v < 0.4 for v in confidences), len(confidences)),
            'medium': rounded_ratio(sum(0.4 <= v < 0.7 for v in confidences), len(confidences)),
            'high': rounded_ratio(sum(v >= 0.7 for v in confidences), len(confidences)),
        },
        'provider_failure_rate': {name: rounded_ratio(v['failures'], v['known']) for name, v in providers.items()},
        'fallback_rate': rounded_ratio(sum((row.get('provider') or '').lower() in ('rule', 'local_rule') for row in rows), len(rows)),
        'latency': {'avg_ms': int(sum(latencies) / len(latencies)) if latencies else None,
                    'p50_ms': latencies[len(latencies) // 2] if latencies else None,
                    'p95_ms': latencies[min(int(len(latencies) * 0.95), len(latencies) - 1)] if latencies else None,
                    'max_ms': latencies[-1] if latencies else None,
                    'ambiguous_zero_samples': latency_zero_samples,
                    'unknown_samples': latency_unknown,
                    'zero_value_provenance': (
                        'unresolved_legacy_default_or_measured_zero'
                        if latency_zero_samples else 'no_zero_values'
                    )},
        'token_cost': {'total_tokens': int(sum(tokens)) if tokens else None,
                       'avg_tokens': int(sum(tokens) / len(tokens)) if tokens else None},
        'sample_counts': {'rule_comparisons': len(comparable), 'final_comparisons': len(final),
                          'confidence': len(confidences),
                          'confidence_ambiguous_zero': confidence_zero_samples,
                          'confidence_unknown': confidence_unknown,
                          'latency': len(latencies),
                          'latency_ambiguous_zero': latency_zero_samples,
                          'latency_unknown': latency_unknown,
                          'token_usage': len(tokens),
                          'human_correction_observations': correction_count},
        'period': {'since': since, 'until': rows[0].get('created_at', ''), 'sampled': len(rows)},
    }


# ============================================================
# 4) 人工修正反馈闭环
# ============================================================
def submit_human_correction(
    call_id: int,
    correction: str,
    corrected_result: str = '',
) -> bool:
    """
    提交人工修正。更新 ai_call_logs.human_correction，
    并可选择更新 final_result 为人工修正后的结果。

    这是「AI 输出 → 人工审核 → 修正沉淀」闭环的入口。
    修正后的结果可用于后续规则优化和 AI prompt 迭代。

    Args:
        call_id: ai_call_logs.id
        correction: 修正说明（人工标注）
        corrected_result: 修正后的最终结果（可选，更新 final_result）

    Returns:
        是否成功
    """
    try:
        ok = acl.record_human_correction(call_id, correction)
        if ok and corrected_result:
            conn = _conn()
            try:
                conn.execute(
                    "UPDATE ai_call_logs SET final_result = ? WHERE id = ?",
                    (str(corrected_result)[:1000], call_id),
                )
                conn.commit()
            finally:
                conn.close()
        return ok
    except Exception as e:
        print(f'[AIEvaluation] submit_human_correction failed: {e}')
        return False


def get_correction_feedback(since: str = '', limit: int = 100) -> List[Dict[str, Any]]:
    """获取人工修正记录（用于规则沉淀和 prompt 优化）。"""
    try:
        conn = _conn()
        try:
            sql = ("SELECT id, provider, model, prompt_version, output, "
                   "rule_result, final_result, human_correction, created_at "
                   "FROM ai_call_logs WHERE human_correction != '' "
                   "AND human_correction IS NOT NULL")
            params: List[Any] = []
            if since:
                sql += " AND created_at >= ?"
                params.append(since)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
    except Exception as e:
        print(f'[AIEvaluation] get_correction_feedback failed: {e}')
        return []


# ============================================================
# 5) Provider 健康评估
# ============================================================
def evaluate_provider_health(since: str = '') -> Dict[str, Any]:
    """
    评估各 Provider 的健康状况，用于 Provider 收敛决策。

    Owned Gateway outcomes are classified from their versioned execution
    payload. Pre-generation denials, budget stops and cancellations are visible
    but do not count as provider failures; a provider is only rated from actual
    generation attempts and compatible legacy observations.

    Returns:
        {provider: {total, attempted, success, failure, cancelled,
        not_executed, failure_rate, avg_latency_ms, status}}
    """
    try:
        conn = _conn()
        try:
            sql = "SELECT provider, success, latency_ms, system_result FROM ai_call_logs WHERE 1=1"
            params: List[Any] = []
            if since:
                sql += " AND created_at >= ?"
                params.append(since)
            sql += " ORDER BY id DESC"
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
    except Exception as e:
        print(f'[AIEvaluation] evaluate_provider_health failed: {e}')
        return {}

    providers = {}
    for row in rows:
        name = row.get('provider') or 'unknown'
        execution = _owned_execution_payload(row)
        record = providers.setdefault(name, {
            'total': 0, 'success': 0, 'failure': 0, 'known': 0,
            'unknown': 0, 'attempted': 0, 'cancelled': 0,
            'cancelled_before_generation': 0, 'not_executed': 0,
            'not_executed_states': {}, 'latencies': [],
            'ambiguous_zero_latency': 0,
        })
        record['total'] += 1
        generated = execution is not None and execution.get('generation_performed') is True
        state = execution.get('state') if execution is not None else ''
        success = row.get('success')
        if execution is None:
            if success == 1:
                record['success'] += 1
                record['known'] += 1
            elif success == 0:
                record['failure'] += 1
                record['known'] += 1
            else:
                record['unknown'] += 1
            if success in (0, 1):
                _add_provider_latency(record, row.get('latency_ms'))
            continue

        if state == 'CANCELLED':
            record['cancelled'] += 1
            if not generated:
                record['cancelled_before_generation'] += 1
            else:
                record['attempted'] += 1
            continue
        if not generated:
            record['not_executed'] += 1
            record['not_executed_states'][state or 'UNKNOWN'] = (
                record['not_executed_states'].get(state or 'UNKNOWN', 0) + 1)
            continue

        record['attempted'] += 1
        if state == 'COMPLETED' and success == 1:
            record['success'] += 1
            record['known'] += 1
            _add_provider_latency(record, row.get('latency_ms'))
        elif state != 'COMPLETED':
            record['failure'] += 1
            record['known'] += 1
            _add_provider_latency(record, row.get('latency_ms'))
        else:
            # A success-shaped row that no longer matches the execution
            # contract is not a measured provider success or failure.
            record['unknown'] += 1

    result = {}
    for p, r in providers.items():
        total = r['total']
        failure = r['failure']
        known_outcomes = r['known']
        failure_rate = failure / known_outcomes if known_outcomes else None
        unknown_outcomes = r['unknown']
        execution_observed = r['attempted'] > 0 or any(
            _owned_execution_payload(row) is None and (row.get('provider') or 'unknown') == p
            and row.get('success') in (0, 1) for row in rows)
        # 状态判定
        if failure_rate is None:
            status = 'UNKNOWN'
        elif failure_rate >= 0.5:
            status = 'UNHEALTHY'
        elif failure_rate >= 0.2:
            status = 'DEGRADED'
        elif not execution_observed or unknown_outcomes:
            status = 'UNKNOWN'
        else:
            status = 'HEALTHY'
        result[p] = {
            'total': total,
            'attempted': r['attempted'],
            'success': r['success'],
            'failure': failure,
            'cancelled': r['cancelled'],
            'cancelled_before_generation': r['cancelled_before_generation'],
            'not_executed': r['not_executed'],
            'not_executed_states': r['not_executed_states'],
            'failure_rate': round(failure_rate, 4) if failure_rate is not None else None,
            'known_outcomes': known_outcomes,
            'unknown_outcomes': unknown_outcomes,
            'avg_latency_ms': (int(sum(r['latencies']) / len(r['latencies']))
                               if r['latencies'] else None),
            'ambiguous_zero_latency_samples': r['ambiguous_zero_latency'],
            'status': status,
            'configured_status': acl.get_provider_status(p),
        }
    return result


def _add_provider_latency(record, raw_latency):
    if raw_latency is None or isinstance(raw_latency, bool):
        return
    try:
        latency = float(raw_latency)
    except (TypeError, ValueError, OverflowError):
        return
    if not math.isfinite(latency) or latency < 0:
        return
    if latency == 0:
        record['ambiguous_zero_latency'] += 1
    else:
        record['latencies'].append(latency)


# ============================================================
# 6) AI 不替代核心规则的验证器
# ============================================================
def verify_ai_not_replacing_rules() -> Dict[str, Any]:
    """Require observations for PASS; failed queries never certify safety."""
    quality = evaluate_ai_quality()
    checks = []; violations = []
    def add(name, value, threshold, passed, count, violation):
        state = 'UNKNOWN' if passed is None else 'PASS' if passed else 'FAIL'
        checks.append({'name': name, 'value': value, 'threshold': threshold,
                       'passed': passed, 'state': state, 'sample_count': count})
        if passed is False:
            violations.append(violation)
    replacement = quality.get('ai_replacement_rate')
    add('ai_replacement_rate_below_50pct', replacement, 0.5,
        replacement <= 0.5 if replacement is not None else None,
        quality.get('sample_counts', {}).get('final_comparisons', 0),
        'AI 替代率超过 50% 阈值，需核查规则边界')
    try:
        conn = _conn()
        try:
            rows = [dict(row) for row in conn.execute(
                "SELECT rule_result, final_result, output FROM ai_call_logs "
                "WHERE rule_result != '' AND rule_result IS NOT NULL "
                "AND final_result != '' AND final_result IS NOT NULL").fetchall()]
            subjects = [dict(row) for row in conn.execute(
                "SELECT final_result, output, rule_result FROM ai_call_logs "
                "WHERE prompt_version LIKE '%subject%'").fetchall()]
        finally:
            conn.close()
        rate = sum(_results_match(row['rule_result'], row['final_result']) for row in rows) / len(rows) if rows else None
        add('rule_result_priority', round(rate, 4) if rate is not None else None, 0.5,
            rate >= 0.5 if rate is not None else None, len(rows), '规则结果优先率低于 50%')
        checks[-1]['comparable_records'] = len(rows)
        comparable_subjects = [row for row in subjects if row.get('output') and row.get('final_result') and row.get('rule_result')]
        replaced = sum(_results_match(row['final_result'], row['output']) and
                       not _results_match(row['rule_result'], row['output']) for row in comparable_subjects)
        add('subject_filter_not_ai_replaced', replaced if comparable_subjects else None, 0,
            replaced == 0 if comparable_subjects else None, len(comparable_subjects),
            f'主体过滤被 AI 替代 {replaced} 次')
        checks[-1]['total_subject_calls'] = len(subjects)
    except Exception:
        add('rule_result_priority', None, 0.5, None, 0, '')
        checks[-1]['comparable_records'] = 0
        add('subject_filter_not_ai_replaced', None, 0, None, 0, '')
        checks[-1]['total_subject_calls'] = None
    state = 'FAIL' if violations else 'UNKNOWN' if any(c['state'] == 'UNKNOWN' for c in checks) else 'PASS'
    return {'passed': state == 'PASS', 'state': state, 'checks': checks, 'violations': violations,
            'summary': {'PASS': '已观测样本中未发现 AI 替代核心规则',
                        'FAIL': '检测到 AI 可能替代核心规则，需人工审查',
                        'UNKNOWN': '缺少可比较样本或查询失败，尚不能验证规则边界'}[state]}


# ============================================================
# 7) 评估报告生成
# ============================================================
def generate_evaluation_report(since: str = '') -> str:
    """生成可读的 AI 质量评估报告（文本）。"""
    quality = evaluate_ai_quality(since=since)
    provider_health = evaluate_provider_health(since=since)
    rule_verify = verify_ai_not_replacing_rules()

    def pct(value):
        return '未知／未测量' if value is None else f'{value:.1%}'

    def measured(value, unit=''):
        return '未知／未测量' if value is None else f'{value}{unit}'

    lines = [
        '=' * 60,
        'AI 质量评估报告',
        f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'统计周期: {since or "全量"}',
        '=' * 60,
        '',
        '【调用概况】',
        f'  总调用次数: {quality.get("total_calls", 0)}',
        f'  成功: {quality.get("success_count", 0)}',
        f'  失败: {quality.get("failure_count", 0)}',
        f'  回退率: {pct(quality.get("fallback_rate"))}',
        '',
        '【Gateway 执行状态】',
        f'  实际执行尝试: {quality.get("execution_counts", {}).get("attempted", 0)}',
        f'  执行后取消: {max(0, quality.get("cancelled_count", 0) - quality.get("cancelled_before_generation_count", 0))}',
        f'  执行前取消: {quality.get("cancelled_before_generation_count", 0)}',
        f'  未执行（未绑定/预算/权限等）: {quality.get("not_executed_count", 0)}',
        f'  后续上下文排除反馈: {quality.get("conversation_context_exclusion_count", 0)}',
        '',
        '【质量指标】',
        f'  AI与规则一致率（非独立正确率）: {pct(quality.get("rule_agreement_rate"))}',
        f'  AI 替代率: {pct(quality.get("ai_replacement_rate"))}',
        f'  人工修正率: {pct(quality.get("human_correction_rate"))}',
        f'  已记录人工修正数: {quality.get("human_correction_count", 0)}',
        '  人工复核覆盖: 未记录',
        '',
        '【置信度分布】',
        f'  低 (<0.4): {pct(quality.get("confidence_distribution", {}).get("low"))}',
        f'  中 (0.4-0.7): {pct(quality.get("confidence_distribution", {}).get("medium"))}',
        f'  高 (>=0.7): {pct(quality.get("confidence_distribution", {}).get("high"))}',
        '',
        '【延迟】',
        f'  平均: {measured(quality.get("latency", {}).get("avg_ms"), "ms")}',
        f'  P50: {measured(quality.get("latency", {}).get("p50_ms"), "ms")}',
        f'  P95: {measured(quality.get("latency", {}).get("p95_ms"), "ms")}',
        '',
        '【Token 成本】',
        f'  总用量: {measured(quality.get("token_cost", {}).get("total_tokens"))}',
        f'  平均: {measured(quality.get("token_cost", {}).get("avg_tokens"))}',
        '',
        '【Provider 健康】',
    ]
    for p, h in provider_health.items():
        lines.append(
            f'  {p}: 总量={h["total"]} 尝试={h["attempted"]} '
            f'成功={h["success"]} 失败={h["failure"]} '
            f'取消={h["cancelled"]} 未执行={h["not_executed"]} '
            f'失败率={pct(h["failure_rate"])} '
            f'状态={h["status"]} (配置={h["configured_status"]})'
        )
    lines.extend([
        '',
        '【AI 不替代规则验证】',
        f'  结果: {rule_verify["state"]}',
        f'  摘要: {rule_verify["summary"]}',
    ])
    for v in rule_verify.get('violations', []):
        lines.append(f'  违规: {v}')
    lines.append('')
    lines.append('=' * 60)
    return '\n'.join(lines)


# 模块级便捷函数
def quick_summary() -> Dict[str, Any]:
    """快速获取评估摘要（供 API 调用）。"""
    q = evaluate_ai_quality(limit=1000)
    return {
        'total_calls': q.get('total_calls', 0),
        'metric_contract': q.get('metric_contract'), 'state': q.get('state'),
        'rule_agreement_rate': q.get('rule_agreement_rate'),
        'ai_accuracy': q.get('ai_accuracy'),
        'ai_accuracy_semantics': q.get('ai_accuracy_semantics'),
        'independent_accuracy': q.get('independent_accuracy'),
        'ai_replacement_rate': q.get('ai_replacement_rate'),
        'human_correction_count': q.get('human_correction_count'),
        'human_correction_rate': q.get('human_correction_rate'),
        'human_correction_state': q.get('human_correction_state'),
        'sample_counts': q.get('sample_counts'),
        'execution_counts': q.get('execution_counts'),
        'cancelled_count': q.get('cancelled_count'),
        'cancelled_before_generation_count': q.get('cancelled_before_generation_count'),
        'not_executed_count': q.get('not_executed_count'),
        'not_executed_states': q.get('not_executed_states'),
        'conversation_context_exclusion_count': q.get('conversation_context_exclusion_count'),
        'fallback_rate': q.get('fallback_rate'),
        'provider_health': evaluate_provider_health(),
        'rule_verification': verify_ai_not_replacing_rules(),
    }


def project_synthetic_interpretability_metrics(packet, *, evidence_ref, packet_sha256):
    """Pure projection; only the authorized Gateway owner may persist these rows.

    Diagnostic experiment scores must never be interpreted as business quality.
    No filesystem loading, model execution, identity inference or DB writes here.
    """
    import re
    from lumenis.system.ai_gateway.owned_evaluation import (
        validate_synthetic_interpretability_packet, _evaluation_packet_sha256,
    )
    clean = validate_synthetic_interpretability_packet(packet)
    if (type(evidence_ref) is not str or re.fullmatch(r"app_evidence_records:[1-9][0-9]*", evidence_ref) is None
            or packet_sha256 != _evaluation_packet_sha256(clean)):
        raise ValueError("INTERPRETABILITY_PROJECTION_BINDING_INVALID")
    thresholds = {"activation_prediction_nmse": (.1, .5),
                  "intervention_prediction_error": (1e-8, 1e-4), "replay_max_error": (1e-12, 1e-8)}
    metadata = {"schema": clean["schema"], "prototype_status": "SYNTHETIC_PROTOTYPE",
                "business_acceptance": "NOT_EVALUATED", "promotion_status": "NOT_PROMOTED",
                "packet_sha256": packet_sha256, "task_id": clean["task_id"],
                "checkpoint_id": clean["checkpoint_id"], "run_id": clean["run_id"],
                "weights_sha256": clean["weights_sha256"], "inputs_sha256": clean["inputs_sha256"],
                "hypotheses_sha256": clean["hypotheses_sha256"], "capture_status": clean["capture_status"]}
    return [{"dimension": "ai", "metric_name": "synthetic_interpretability." + name,
             "metric_value": clean["metrics"][name], "pass_threshold": thresholds[name][0],
             "warn_threshold": thresholds[name][1], "higher_is_better": False,
             "source": "synthetic_interpretability", "evidence_ref": evidence_ref, "metadata": metadata}
            for name in sorted(thresholds)]
