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

import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import ai_call_logger as acl
from lumenis.shared.database import get_repository

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


# ============================================================
# 3) 核心评估函数：evaluate_ai_quality
# ============================================================
def evaluate_ai_quality(since: str = '', provider: str = '', limit: int = 5000) -> Dict[str, Any]:
    """Read measured quality signals; absent denominators remain unknown.

    ``ai_accuracy`` is a compatibility alias of rule_agreement_rate, NOT an
    independent accuracy benchmark. Contract v2 makes that meaning explicit.
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
        'metric_contract': 'lumenis.ai-quality/v2', 'state': 'NO_SAMPLES',
        'total_calls': 0, 'success_count': 0, 'failure_count': 0,
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
    success = [row for row in rows if row.get('success') == 1]
    failure = [row for row in rows if row.get('success') == 0]
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
    confidence_unknown = max(0, len(success) - len(raw_confidences))
    latency_unknown = max(0, len(success) - len(raw_latencies))
    providers = {}
    for row in rows:
        name = row.get('provider') or 'unknown'
        record = providers.setdefault(name, {'total': 0, 'failures': 0, 'known': 0})
        record['total'] += 1; record['failures'] += row.get('success') == 0
        record['known'] += row.get('success') in (0, 1)
    return {
        **empty, 'state': 'OBSERVED', 'total_calls': len(rows),
        'success_count': len(success), 'failure_count': len(failure),
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

    Returns:
        {provider: {total, success, failure, failure_rate, avg_latency_ms, status}}
    """
    try:
        conn = _conn()
        try:
            sql = ("SELECT provider, COUNT(*) as total, "
                   "SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as success, "
                   "SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) as failure, "
                   "AVG(CASE WHEN latency_ms > 0 THEN latency_ms END) as avg_latency, "
                   "SUM(CASE WHEN latency_ms = 0 THEN 1 ELSE 0 END) as ambiguous_zero_latency, "
                   "SUM(CASE WHEN success IN (0,1) THEN 1 ELSE 0 END) as known_outcomes "
                   "FROM ai_call_logs WHERE 1=1")
            params: List[Any] = []
            if since:
                sql += " AND created_at >= ?"
                params.append(since)
            sql += " GROUP BY provider ORDER BY total DESC"
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
    except Exception as e:
        print(f'[AIEvaluation] evaluate_provider_health failed: {e}')
        return {}

    result = {}
    for r in rows:
        p = r.get('provider', 'unknown') or 'unknown'
        total = r.get('total', 0) or 0
        failure = r.get('failure', 0) or 0
        known_outcomes = r.get('known_outcomes', 0) or 0
        failure_rate = failure / known_outcomes if known_outcomes else None
        unknown_outcomes = total - known_outcomes
        # 状态判定
        if failure_rate is None:
            status = 'UNKNOWN'
        elif failure_rate >= 0.5:
            status = 'UNHEALTHY'
        elif failure_rate >= 0.2:
            status = 'DEGRADED'
        elif total == 0 or unknown_outcomes:
            status = 'UNKNOWN'
        else:
            status = 'HEALTHY'
        result[p] = {
            'total': total,
            'success': r.get('success', 0) or 0,
            'failure': failure,
            'failure_rate': round(failure_rate, 4) if failure_rate is not None else None,
            'known_outcomes': known_outcomes,
            'unknown_outcomes': unknown_outcomes,
            'avg_latency_ms': int(r['avg_latency']) if r.get('avg_latency') is not None else None,
            'ambiguous_zero_latency_samples': r.get('ambiguous_zero_latency', 0) or 0,
            'status': status,
            'configured_status': acl.get_provider_status(p),
        }
    return result


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
            f'  {p}: 总量={h["total"]} 失败率={pct(h["failure_rate"])} '
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
        'fallback_rate': q.get('fallback_rate'),
        'provider_health': evaluate_provider_health(),
        'rule_verification': verify_ai_not_replacing_rules(),
    }
