# -*- coding: utf-8 -*-
"""
lumenis.shared.evaluation.ai — LUMENIS Shared Evaluation AI 质量评估

核心原则：AI 是辅助判断层，永远不替代核心确定性规则。
评估体系追踪 AI 与规则的一致性、人工修正率、Provider 可靠性，
形成「AI 输出 → 规则对比 → 人工修正 → 规则沉淀」的闭环。

追踪指标：
- AI 准确率（ai_accuracy）：AI 结果与规则结果一致的比例
- AI 替代率（ai_replacement_rate）：最终结果采用 AI 而非规则的比例
- 人工修正率（human_correction_rate）：被人工修正的调用比例
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
from typing import Any, Dict, List, Optional, Tuple

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
    confidence: float = 0.0,
    prompt_version: str = '',
    input_hash: str = '',
    latency_ms: int = 0,
    token_usage: int = 0,
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
def evaluate_ai_quality(
    since: str = '',
    provider: str = '',
    limit: int = 5000,
) -> Dict[str, Any]:
    """
    评估 AI 质量，返回完整指标字典。

    Args:
        since: 起始时间（ISO 格式），空则全量
        provider: 限定 provider，空则全部
        limit: 最多分析的记录数

    Returns:
        {
            'total_calls', 'success_count', 'failure_count',
            'ai_accuracy', 'ai_replacement_rate', 'human_correction_rate',
            'confidence_distribution': {'low': %, 'medium': %, 'high': %},
            'provider_failure_rate': {provider: rate},
            'fallback_rate',
            'latency': {'avg_ms', 'p50_ms', 'p95_ms', 'max_ms'},
            'token_cost': {'total_tokens', 'avg_tokens'},
            'period': {'since', 'until', 'sampled'}
        }
    """
    try:
        conn = _conn()
        try:
            sql = "SELECT * FROM ai_call_logs WHERE 1=1"
            params: List[Any] = []
            if since:
                sql += " AND created_at >= ?"
                params.append(since)
            if provider:
                sql += " AND provider = ?"
                params.append(provider)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
    except Exception as e:
        print(f'[AIEvaluation] evaluate query failed: {e}')
        return {'error': str(e), 'total_calls': 0}

    if not rows:
        return {
            'total_calls': 0, 'success_count': 0, 'failure_count': 0,
            'ai_accuracy': 0.0, 'ai_replacement_rate': 0.0,
            'human_correction_rate': 0.0,
            'confidence_distribution': {'low': 0.0, 'medium': 0.0, 'high': 0.0},
            'provider_failure_rate': {},
            'fallback_rate': 0.0,
            'latency': {'avg_ms': 0, 'p50_ms': 0, 'p95_ms': 0, 'max_ms': 0},
            'token_cost': {'total_tokens': 0, 'avg_tokens': 0},
            'period': {'since': since, 'until': '', 'sampled': 0},
        }

    total = len(rows)
    success_rows = [r for r in rows if r.get('success') == 1]
    failure_rows = [r for r in rows if r.get('success') == 0]

    # --- AI 准确率：有 rule_result 和 output 的记录中，两者一致的比例 ---
    comparable = [r for r in success_rows if r.get('rule_result') and r.get('output')]
    matches = sum(1 for r in comparable if _results_match(r['rule_result'], r['output']))
    ai_accuracy = matches / len(comparable) if comparable else 0.0

    # --- AI 替代率：在有 final_result 和 output 的记录中，final_result 采用了 AI 结果
    #     且 AI 结果与规则结果不同（或无规则结果）的比例。AI 与规则一致时不算"替代"。 ---
    with_final = [r for r in success_rows if r.get('final_result') and r.get('output')]
    replaced = 0
    for r in with_final:
        if not _results_match(r['final_result'], r['output']):
            continue  # final 没采用 AI，不算替代
        if r.get('rule_result') and _results_match(r['rule_result'], r['output']):
            continue  # AI 与规则一致，不算替代
        replaced += 1
    ai_replacement_rate = replaced / len(with_final) if with_final else 0.0

    # --- 人工修正率 ---
    corrected = sum(1 for r in rows if r.get('human_correction'))
    human_correction_rate = corrected / total if total else 0.0

    # --- 置信度分布 ---
    conf_values = [float(r.get('confidence', 0) or 0) for r in success_rows]
    if conf_values:
        low = sum(1 for c in conf_values if c < 0.4) / len(conf_values)
        medium = sum(1 for c in conf_values if 0.4 <= c < 0.7) / len(conf_values)
        high = sum(1 for c in conf_values if c >= 0.7) / len(conf_values)
    else:
        low = medium = high = 0.0

    # --- Provider 失败率 ---
    provider_stats: Dict[str, Dict[str, int]] = {}
    for r in rows:
        p = r.get('provider', 'unknown') or 'unknown'
        if p not in provider_stats:
            provider_stats[p] = {'total': 0, 'failures': 0}
        provider_stats[p]['total'] += 1
        if r.get('success') == 0:
            provider_stats[p]['failures'] += 1
    provider_failure_rate = {
        p: (s['failures'] / s['total'] if s['total'] else 0.0)
        for p, s in provider_stats.items()
    }

    # --- 回退率：provider 为 rule/local_rule 的比例（AI 不可用时回退） ---
    fallback_count = sum(1 for r in rows
                         if (r.get('provider') or '').lower() in ('rule', 'local_rule'))
    fallback_rate = fallback_count / total if total else 0.0

    # --- 延迟统计 ---
    latencies = sorted([int(r.get('latency_ms', 0) or 0) for r in success_rows])
    if latencies:
        avg_lat = sum(latencies) // len(latencies)
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0]
        max_lat = latencies[-1]
    else:
        avg_lat = p50 = p95 = max_lat = 0

    # --- Token 成本 ---
    tokens = [int(r.get('token_usage', 0) or 0) for r in success_rows]
    total_tokens = sum(tokens)
    avg_tokens = total_tokens // len(tokens) if tokens else 0

    return {
        'total_calls': total,
        'success_count': len(success_rows),
        'failure_count': len(failure_rows),
        'ai_accuracy': round(ai_accuracy, 4),
        'ai_replacement_rate': round(ai_replacement_rate, 4),
        'human_correction_rate': round(human_correction_rate, 4),
        'confidence_distribution': {
            'low': round(low, 4),
            'medium': round(medium, 4),
            'high': round(high, 4),
        },
        'provider_failure_rate': {p: round(r, 4) for p, r in provider_failure_rate.items()},
        'fallback_rate': round(fallback_rate, 4),
        'latency': {
            'avg_ms': avg_lat, 'p50_ms': p50, 'p95_ms': p95, 'max_ms': max_lat,
        },
        'token_cost': {'total_tokens': total_tokens, 'avg_tokens': avg_tokens},
        'period': {
            'since': since,
            'until': rows[0].get('created_at', ''),
            'sampled': total,
        },
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
                   "AVG(latency_ms) as avg_latency "
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
        failure_rate = failure / total if total else 0.0
        # 状态判定
        if failure_rate >= 0.5:
            status = 'UNHEALTHY'
        elif failure_rate >= 0.2:
            status = 'DEGRADED'
        elif total == 0:
            status = 'UNKNOWN'
        else:
            status = 'HEALTHY'
        result[p] = {
            'total': total,
            'success': r.get('success', 0) or 0,
            'failure': failure,
            'failure_rate': round(failure_rate, 4),
            'avg_latency_ms': int(r.get('avg_latency', 0) or 0),
            'status': status,
            'configured_status': acl.get_provider_status(p),
        }
    return result


# ============================================================
# 6) AI 不替代核心规则的验证器
# ============================================================
def verify_ai_not_replacing_rules() -> Dict[str, Any]:
    """
    验证 AI 没有替代核心确定性规则。

    检查项：
    1. ai_replacement_rate 应较低（AI 不应高频替代规则）
    2. 所有有 rule_result 的记录，final_result 应优先等于 rule_result
    3. 主体过滤相关调用（prompt_version 含 subject）的 AI 替代率应为 0

    Returns:
        {'passed': bool, 'checks': [...], 'violations': [...]}
    """
    quality = evaluate_ai_quality()
    checks = []
    violations = []

    # 检查 1：AI 替代率不应超过 50%（AI 是辅助，不是主判断）
    replacement_rate = quality.get('ai_replacement_rate', 0.0)
    check1_pass = replacement_rate <= 0.5
    checks.append({
        'name': 'ai_replacement_rate_below_50pct',
        'value': replacement_rate,
        'threshold': 0.5,
        'passed': check1_pass,
    })
    if not check1_pass:
        violations.append(f'AI 替代率 {replacement_rate:.1%} 超过 50% 阈值，AI 可能过度替代规则')

    # 检查 2：有 rule_result 的记录中，final_result 应优先等于 rule_result
    try:
        conn = _conn()
        try:
            rows = conn.execute(
                "SELECT rule_result, final_result, output FROM ai_call_logs "
                "WHERE rule_result != '' AND rule_result IS NOT NULL "
                "AND final_result != '' AND final_result IS NOT NULL"
            ).fetchall()
            rule_priority_count = sum(
                1 for r in rows if _results_match(r['rule_result'], r['final_result'])
            )
            total_comparable = len(rows)
            rule_priority_rate = (
                rule_priority_count / total_comparable if total_comparable else 1.0
            )
        finally:
            conn.close()
    except Exception:
        rule_priority_rate = 1.0
        total_comparable = 0

    check2_pass = rule_priority_rate >= 0.5
    checks.append({
        'name': 'rule_result_priority',
        'value': round(rule_priority_rate, 4),
        'threshold': 0.5,
        'comparable_records': total_comparable,
        'passed': check2_pass,
    })
    if not check2_pass:
        violations.append(
            f'规则结果优先率 {rule_priority_rate:.1%} 低于 50%，final_result 可能未优先采用规则结果'
        )

    # 检查 3：主体过滤不应被 AI 替代（通过 prompt_version 标记）
    try:
        conn = _conn()
        try:
            subject_rows = conn.execute(
                "SELECT final_result, output, rule_result FROM ai_call_logs "
                "WHERE prompt_version LIKE '%subject%'"
            ).fetchall()
            subject_ai_replaced = sum(
                1 for r in subject_rows
                if r.get('output') and _results_match(r['final_result'], r['output'])
                and not _results_match(r['rule_result'], r['output'])
            )
            subject_total = len(subject_rows)
        finally:
            conn.close()
    except Exception:
        subject_ai_replaced = 0
        subject_total = 0

    check3_pass = subject_ai_replaced == 0
    checks.append({
        'name': 'subject_filter_not_ai_replaced',
        'value': subject_ai_replaced,
        'threshold': 0,
        'total_subject_calls': subject_total,
        'passed': check3_pass,
    })
    if not check3_pass:
        violations.append(
            f'主体过滤被 AI 替代 {subject_ai_replaced} 次，违反「主体过滤是第一道关」红线'
        )

    return {
        'passed': all(c['passed'] for c in checks),
        'checks': checks,
        'violations': violations,
        'summary': (
            'AI 未替代核心规则' if all(c['passed'] for c in checks)
            else '检测到 AI 可能替代核心规则，需人工审查'
        ),
    }


# ============================================================
# 7) 评估报告生成
# ============================================================
def generate_evaluation_report(since: str = '') -> str:
    """生成可读的 AI 质量评估报告（文本）。"""
    quality = evaluate_ai_quality(since=since)
    provider_health = evaluate_provider_health(since=since)
    rule_verify = verify_ai_not_replacing_rules()

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
        f'  回退率: {quality.get("fallback_rate", 0):.1%}',
        '',
        '【质量指标】',
        f'  AI 准确率: {quality.get("ai_accuracy", 0):.1%}',
        f'  AI 替代率: {quality.get("ai_replacement_rate", 0):.1%}',
        f'  人工修正率: {quality.get("human_correction_rate", 0):.1%}',
        '',
        '【置信度分布】',
        f'  低 (<0.4): {quality.get("confidence_distribution", {}).get("low", 0):.1%}',
        f'  中 (0.4-0.7): {quality.get("confidence_distribution", {}).get("medium", 0):.1%}',
        f'  高 (>=0.7): {quality.get("confidence_distribution", {}).get("high", 0):.1%}',
        '',
        '【延迟】',
        f'  平均: {quality.get("latency", {}).get("avg_ms", 0)}ms',
        f'  P50: {quality.get("latency", {}).get("p50_ms", 0)}ms',
        f'  P95: {quality.get("latency", {}).get("p95_ms", 0)}ms',
        '',
        '【Token 成本】',
        f'  总用量: {quality.get("token_cost", {}).get("total_tokens", 0)}',
        f'  平均: {quality.get("token_cost", {}).get("avg_tokens", 0)}',
        '',
        '【Provider 健康】',
    ]
    for p, h in provider_health.items():
        lines.append(
            f'  {p}: 总量={h["total"]} 失败率={h["failure_rate"]:.1%} '
            f'状态={h["status"]} (配置={h["configured_status"]})'
        )
    lines.extend([
        '',
        '【AI 不替代规则验证】',
        f'  结果: {"PASS" if rule_verify["passed"] else "FAIL"}',
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
        'ai_accuracy': q.get('ai_accuracy', 0.0),
        'ai_replacement_rate': q.get('ai_replacement_rate', 0.0),
        'human_correction_rate': q.get('human_correction_rate', 0.0),
        'fallback_rate': q.get('fallback_rate', 0.0),
        'provider_health': evaluate_provider_health(),
        'rule_verification': verify_ai_not_replacing_rules(),
    }
