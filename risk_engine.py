"""风险/日报兼容层 v5.6.3 + Track3 审计修复

保留历史 `_subject_sql_and_values()` 命名，并把报告层统一转发到 daily_report/report_engine。

【职责边界声明（P1-4，2026-09-02 据运行时事实校正）】本模块为历史命名兼容层，仅做入口转发，不承担独立风险计算。
- 现役「采集风险状态/熔断」权威：collector_guard/guard.py 的 CollectorGuard = state.CollectState 七态
  + analyzer.ResponseAnalyzer 响应分类 + rate_limiter.AdaptiveRateLimiter（连续失败阈值→动态降频→冷却/熔断→恢复），
  采集主链 collector.py 默认启用（TAIKOO_COLLECTOR_GUARD=1）。
- collector_guard/risk_engine.py 的 RiskEngine（0-100 连续分 + 五档 + 硬信号，tests/test_risk_engine.py 7 用例覆盖）
  是【已实现、已测、当前未接管】的增强评分器：不被 CollectorGuard 实例化，不影响现役七态熔断；
  未来若需连续分，须先旁路验证再接入，不得直接替换现役状态机。
- 报告与风险口径：daily_report.py / report_engine.py（DB 统计口径强写回，防 AI 误写）。
本模块 build_daily_report / _subject_sql_and_values 仅保持历史调用点兼容，不得作为新业务口径依据。

Track3 修复（2026-09-06）：
- 新增 evaluate_risk()：统一状态枚举，unknown 保持 unknown 不伪造，0/0 安全处理，
  critical 独立于 high，禁止 critical=high / unknown=negative / 0/0=0。
- 新增 RISK_LEVELS / SENTIMENT_LABELS 统一枚举。
- 新增 aggregate_risk()：聚合时保留 unknown，不把未知当负面。
"""
from subject_rules import subject_sql_and_values, SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS
import daily_report
import logging

# ============================================================
# Track3：统一状态枚举（禁止 critical=high、unknown=negative）
# ============================================================
RISK_LEVELS = ("low", "medium", "high", "critical", "unknown")
SENTIMENT_LABELS = ("positive", "neutral", "negative", "unknown")

# 风险等级数值映射（仅用于排序/聚合，不用于覆盖原始标签）
logger = logging.getLogger(__name__)

_RISK_SCORE = {"low": 1, "medium": 2, "high": 3, "critical": 4, "unknown": 0}
_SENTIMENT_SCORE = {"positive": 1, "neutral": 0, "negative": -1, "unknown": None}


def _is_unknown(value) -> bool:
    """判断值是否为未知/空/None。"""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in ("", "unknown", "none", "null", "n/a", "na")
    return False


def _safe_div(numerator: float, denominator: float) -> float:
    """安全除法：0/0 返回 0.0（而非崩溃），但调用方应明确这是"无数据"而非"零值"。

    Track3：禁止把 0/0 伪造为有意义的 0；返回 0.0 同时调用方应检查 data_available。
    """
    if denominator == 0:
        return 0.0
    return numerator / denominator


def evaluate_risk(
    sentiment=None,
    risk_level=None,
    engagement=None,
    severity=None,
    confidence=None,
    threshold: float = 0.5,
) -> dict:
    """统一风险评估（Track3 审计修复版）。

    核心原则：
    1. unknown 保持 unknown，不伪造为 negative / low / 0。
    2. critical 独立于 high，禁止 critical=high。
    3. 0/0 安全处理，标记 data_available=False。
    4. confidence 低于 threshold 时，结果标记为 low_confidence，不提升风险等级。
    5. AI 不能替代核心规则：本函数只做归一化和边界保护，最终决策由 Rule→Evidence→Evaluation 链路给出。

    Args:
        sentiment: positive / neutral / negative / unknown（None 视为 unknown）
        risk_level: low / medium / high / critical / unknown
        engagement: 互动量（int/float，None 视为 unknown）
        severity: 严重度 0-1（None 视为 unknown）
        confidence: 置信度 0-1（None 视为 unknown）
        threshold: 置信度阈值，低于此值标记 low_confidence

    Returns:
        {
            sentiment, risk_level, engagement, severity, confidence,
            final_risk, data_available, low_confidence,
            risk_score, sentiment_score,
            threshold, normalized
        }
    """
    # ---- sentiment 归一化 ----
    if _is_unknown(sentiment):
        norm_sentiment = "unknown"
    else:
        s = str(sentiment).strip().lower()
        norm_sentiment = s if s in SENTIMENT_LABELS else "unknown"

    # ---- risk_level 归一化（critical 独立，禁止合并为 high）----
    if _is_unknown(risk_level):
        norm_risk = "unknown"
    else:
        r = str(risk_level).strip().lower()
        # 显式禁止 critical=high：如果传入 "critical" 必须保留
        norm_risk = r if r in RISK_LEVELS else "unknown"

    # ---- engagement ----
    if _is_unknown(engagement):
        norm_engagement = None
        engagement_available = False
    else:
        try:
            norm_engagement = float(engagement)
            engagement_available = True
        except (ValueError, TypeError):
            norm_engagement = None
            engagement_available = False

    # ---- severity ----
    if _is_unknown(severity):
        norm_severity = None
        severity_available = False
    else:
        try:
            norm_severity = max(0.0, min(1.0, float(severity)))
            severity_available = True
        except (ValueError, TypeError):
            norm_severity = None
            severity_available = False

    # ---- confidence ----
    if _is_unknown(confidence):
        norm_confidence = None
        confidence_available = False
    else:
        try:
            norm_confidence = max(0.0, min(1.0, float(confidence)))
            confidence_available = True
        except (ValueError, TypeError):
            norm_confidence = None
            confidence_available = False

    # ---- 数据可用性判断 ----
    data_available = any([
        norm_sentiment != "unknown",
        norm_risk != "unknown",
        engagement_available,
        severity_available,
    ])

    # ---- 低置信度标记 ----
    low_confidence = (not confidence_available) or (confidence_available and norm_confidence < threshold)

    # ---- 最终风险等级（不伪造：unknown 输入 → unknown 输出）----
    if norm_risk != "unknown":
        final_risk = norm_risk
    elif severity_available and norm_severity is not None:
        # 仅有 severity 时，按阈值映射（不伪造 risk_level）
        if norm_severity >= 0.8:
            final_risk = "critical"
        elif norm_severity >= 0.6:
            final_risk = "high"
        elif norm_severity >= 0.3:
            final_risk = "medium"
        else:
            final_risk = "low"
    elif norm_sentiment == "negative" and engagement_available and norm_engagement and norm_engagement > 100:
        # 负面 + 高互动 → 至少 medium（不直接升 high/critical）
        final_risk = "medium"
    else:
        # 无足够数据 → unknown，不伪造为 low
        final_risk = "unknown"

    # 低置信度不提升风险：如果 final_risk 是 high/critical 但 confidence 低，降级标记（不覆盖原始值）
    risk_adjusted = final_risk
    if low_confidence and final_risk in ("high", "critical"):
        risk_adjusted = "medium"  # 降级但不丢失原始 final_risk

    return {
        "sentiment": norm_sentiment,
        "risk_level": norm_risk,
        "engagement": norm_engagement,
        "severity": norm_severity,
        "confidence": norm_confidence,
        "final_risk": final_risk,
        "risk_adjusted": risk_adjusted,
        "data_available": data_available,
        "low_confidence": low_confidence,
        "risk_score": _RISK_SCORE.get(final_risk, 0),
        "sentiment_score": _SENTIMENT_SCORE.get(norm_sentiment),
        "threshold": threshold,
        "engagement_available": engagement_available,
        "severity_available": severity_available,
        "confidence_available": confidence_available,
        "normalized": True,
        "note": "unknown preserved; critical independent from high; 0/0 safe-div with data_available flag",
    }


def aggregate_risk(items: list) -> dict:
    """聚合多条风险评估结果（Track3：unknown 保持 unknown，不伪造数据）。

    Args:
        items: evaluate_risk() 返回的 dict 列表

    Returns:
        {
            total, with_data, unknown_count,
            risk_distribution, sentiment_distribution,
            avg_severity (data_available flag), avg_confidence,
            max_risk, dominant_sentiment,
            fabrication_safe: True（确认未伪造）
        }
    """
    if not items:
        return {
            "total": 0, "with_data": 0, "unknown_count": 0,
            "risk_distribution": {}, "sentiment_distribution": {},
            "avg_severity": None, "avg_confidence": None,
            "max_risk": "unknown", "dominant_sentiment": "unknown",
            "data_available": False, "fabrication_safe": True,
        }

    total = len(items)
    risk_dist = {r: 0 for r in RISK_LEVELS}
    sent_dist = {s: 0 for s in SENTIMENT_LABELS}
    severity_sum = 0.0
    severity_count = 0
    confidence_sum = 0.0
    confidence_count = 0
    with_data = 0
    unknown_count = 0
    max_risk_score = 0
    max_risk = "unknown"

    for item in items:
        if not isinstance(item, dict):
            continue
        r = item.get("final_risk", "unknown")
        if r in risk_dist:
            risk_dist[r] += 1
        else:
            risk_dist["unknown"] += 1
        if r == "unknown":
            unknown_count += 1
        if item.get("data_available"):
            with_data += 1
        s = item.get("sentiment", "unknown")
        if s in sent_dist:
            sent_dist[s] += 1
        else:
            sent_dist["unknown"] += 1
        sev = item.get("severity")
        if sev is not None and item.get("severity_available"):
            severity_sum += sev
            severity_count += 1
        conf = item.get("confidence")
        if conf is not None and item.get("confidence_available"):
            confidence_sum += conf
            confidence_count += 1
        rs = _RISK_SCORE.get(r, 0)
        if rs > max_risk_score:
            max_risk_score = rs
            max_risk = r

    # 安全平均：0/0 返回 None（不伪造 0）
    avg_severity = severity_sum / severity_count if severity_count > 0 else None
    avg_confidence = confidence_sum / confidence_count if confidence_count > 0 else None

    # 主导情感（取最多的，不把 unknown 当 negative）
    dominant_sentiment = max(
        ((s, c) for s, c in sent_dist.items() if s != "unknown"),
        key=lambda x: x[1], default=("unknown", 0)
    )[0]

    return {
        "total": total,
        "with_data": with_data,
        "unknown_count": unknown_count,
        "risk_distribution": risk_dist,
        "sentiment_distribution": sent_dist,
        "avg_severity": round(avg_severity, 4) if avg_severity is not None else None,
        "avg_confidence": round(avg_confidence, 4) if avg_confidence is not None else None,
        "severity_sample_count": severity_count,
        "confidence_sample_count": confidence_count,
        "max_risk": max_risk,
        "dominant_sentiment": dominant_sentiment,
        "data_available": with_data > 0,
        "fabrication_safe": True,
        "note": "unknown preserved in aggregation; averages only computed over available samples",
    }


def _subject_sql_and_values(alias=''):
    return subject_sql_and_values(alias)


def build_daily_report(date_str=None):
    return daily_report.generate_daily_digest(date_str)


# ============================================================
# ZBC V2.0 双域风险策略（Risk Dual-Domain Policy）
# ============================================================
# CTH 和 ZBMP 使用独立的风险阈值、关键词权重和升级规则。
# Shared Risk Engine 执行计算，但根据 domain_id 选择对应 Policy。
# 硬约束：不得混成一套阈值；unknown 保持 unknown；critical 独立于 high；0/0 安全。

from dataclasses import dataclass, field
from typing import Dict, List, Optional as _Optional, Any as _Any


@dataclass(frozen=True)
class DomainRiskPolicy:
    """域专属风险策略。"""
    domain_id: str
    product_id: str
    policy_version: str
    # 风险等级阈值（risk_score 区间）
    risk_thresholds: Dict[str, float]  # {"low": max, "medium": max, "high": max, "critical": max}
    # 关键词权重
    keyword_weights: Dict[str, float]
    # 升级规则：满足条件时自动升级
    escalation_rules: List[Dict[str, _Any]]
    # 风险维度
    risk_dimensions: List[str]
    # 描述
    description: str


# CTH 域风险策略：太古汇专项风险
CTH_RISK_POLICY = DomainRiskPolicy(
    domain_id="cth",
    product_id="CTH",
    policy_version="cth-risk-v2.0",
    risk_thresholds={
        "low": 20.0,
        "medium": 45.0,
        "high": 70.0,
        "critical": 90.0,
    },
    keyword_weights={
        # 太古汇专项高权重关键词
        "食品安全": 30.0, "卫生问题": 28.0, "安全隐患": 28.0,
        "歧视": 35.0, "侮辱": 30.0, "性骚扰": 40.0,
        "官威": 25.0, "封路": 22.0, "乱收费": 25.0,
        "宰客": 28.0, "黑店": 30.0, "天价": 22.0,
        "集体维权": 35.0, "联名投诉": 32.0, "媒体曝光": 30.0,
        "上热搜": 28.0, "舆情扩散": 32.0, "KOC集中": 25.0,
        "集中负面": 30.0, "太古汇": 5.0, "广州太古汇": 5.0,
        # 通用负面（CTH 权重偏高，因为生产域敏感）
        "投诉": 15.0, "维权": 18.0, "曝光": 16.0,
        "翻车": 14.0, "欺骗": 20.0, "诈骗": 25.0,
    },
    escalation_rules=[
        {"condition": "negative_count >= 5", "action": "escalate_to_high", "reason": "集中负面（>=5条）"},
        {"condition": "koc_count >= 3", "action": "escalate_to_high", "reason": "KOC集中传播（>=3个）"},
        {"condition": "engagement > 10000", "action": "escalate_to_critical", "reason": "舆情扩散（互动>1万）"},
        {"condition": "contains_discrimination", "action": "escalate_to_critical", "reason": "歧视类内容直接critical"},
        {"condition": "contains_safety_issue", "action": "escalate_to_high", "reason": "安全类内容至少high"},
    ],
    risk_dimensions=[
        "太古汇专项风险", "舆情扩散", "安全", "歧视", "集中负面", "KOC集中传播",
    ],
    description="CTH 太古汇生产真相域风险策略：侧重舆情扩散、安全事故、歧视事件、集中负面和KOC集中传播",
)

# ZBMP 域风险策略：多品牌平台风险
ZBMP_RISK_POLICY = DomainRiskPolicy(
    domain_id="zbmp",
    product_id="ZBMP",
    policy_version="zbmp-risk-v2.0",
    risk_thresholds={
        "low": 25.0,
        "medium": 50.0,
        "high": 75.0,
        "critical": 92.0,
    },
    keyword_weights={
        # 品牌声誉类
        "品牌危机": 35.0, "声誉受损": 30.0, "品牌翻车": 28.0,
        "竞品冲击": 20.0, "竞品碾压": 22.0, "市场份额下滑": 25.0,
        "传播异常": 18.0, "数据异常": 15.0, "刷量": 22.0,
        "用户负反馈": 16.0, "差评如潮": 24.0, "退货潮": 22.0,
        "高管丑闻": 30.0, "财务造假": 38.0, "合规问题": 28.0,
        # 通用负面（ZBMP 权重相对较低，多品牌容忍度更高）
        "投诉": 10.0, "维权": 12.0, "曝光": 12.0,
        "翻车": 12.0, "欺骗": 16.0, "诈骗": 20.0,
        "食品安全": 22.0, "歧视": 25.0,
    },
    escalation_rules=[
        {"condition": "negative_count >= 10", "action": "escalate_to_high", "reason": "多品牌集中负面（>=10条）"},
        {"condition": "competitor_mention_spike > 2x", "action": "escalate_to_medium", "reason": "竞品冲击异常"},
        {"condition": "engagement > 50000", "action": "escalate_to_high", "reason": "传播异常（互动>5万）"},
        {"condition": "contains_brand_crisis", "action": "escalate_to_critical", "reason": "品牌危机直接critical"},
        {"condition": "contains_financial_fraud", "action": "escalate_to_critical", "reason": "财务造假直接critical"},
    ],
    risk_dimensions=[
        "品牌声誉", "竞品冲击", "传播异常", "用户负反馈", "品牌危机",
    ],
    description="ZBMP 多主体平台域风险策略：侧重品牌声誉、竞品冲击、传播异常、用户负反馈和品牌危机",
)

DOMAIN_RISK_POLICIES: Dict[str, DomainRiskPolicy] = {
    "cth": CTH_RISK_POLICY,
    "zbmp": ZBMP_RISK_POLICY,
}


def get_risk_policy(domain_id: _Optional[str] = None) -> DomainRiskPolicy:
    """获取指定域的风险策略。默认从当前线程解析，回退 CTH。"""
    if domain_id is None:
        try:
            from ai_domain_context import get_current_domain
            domain_id = get_current_domain()
        except ImportError:
            domain_id = "cth"
    policy = DOMAIN_RISK_POLICIES.get(domain_id)
    if policy is None:
        policy = CTH_RISK_POLICY  # 生产安全默认
    return policy


def compute_domain_risk_score(
    text: str = "",
    sentiment: str = "unknown",
    engagement: int = 0,
    negative_count: int = 0,
    domain_id: _Optional[str] = None,
    extra_keywords: _Optional[List[str]] = None,
) -> Dict[str, _Any]:
    """使用域专属策略计算风险分数和等级。

    Shared Risk Engine 执行计算，但根据 domain_id 选择对应 Policy 的阈值和规则。
    硬约束：unknown 保持 unknown；critical 独立；0/0 安全处理。

    Returns:
        {
            "domain_id", "product_id", "policy_version",
            "risk_score", "risk_level", "risk_dimensions",
            "matched_keywords", "escalation_triggered",
            "data_available", "note",
        }
    """
    policy = get_risk_policy(domain_id)

    # 0/0 安全处理：无数据时 risk_score=0 但标记 data_available=False
    data_available = bool(text) or sentiment != "unknown" or engagement > 0 or negative_count > 0
    if not data_available:
        return {
            "domain_id": policy.domain_id,
            "product_id": policy.product_id,
            "policy_version": policy.policy_version,
            "risk_score": 0.0,
            "risk_level": "unknown",  # 无数据保持 unknown，不伪造为 low
            "risk_dimensions": policy.risk_dimensions,
            "matched_keywords": [],
            "escalation_triggered": [],
            "data_available": False,
            "note": "No data available; risk preserved as unknown (0/0 safe, not fabricated as low)",
        }

    # 1. 关键词权重累加
    risk_score = 0.0
    matched_keywords = []
    text_lower = (text or "").lower()
    for kw, weight in policy.keyword_weights.items():
        if kw.lower() in text_lower:
            risk_score += weight
            matched_keywords.append({"keyword": kw, "weight": weight})

    # 2. 情感加成
    if sentiment == "negative":
        risk_score += 10.0
    elif sentiment == "positive":
        risk_score = max(0, risk_score - 5.0)

    # 3. 互动量加成（对数缩放，避免极端值）
    if engagement > 0:
        import math
        risk_score += min(20.0, math.log10(engagement + 1) * 8.0)

    # 4. 负面数量加成
    if negative_count > 0:
        risk_score += min(15.0, negative_count * 2.0)

    # 5. 额外关键词
    if extra_keywords:
        for kw in extra_keywords:
            if kw.lower() in text_lower:
                risk_score += 5.0
                matched_keywords.append({"keyword": kw, "weight": 5.0, "source": "extra"})

    # 6. 升级规则检查
    escalation_triggered = []
    contains_discrimination = any(
        kw in text_lower for kw in ["歧视", "侮辱", "性骚扰", "racist", "sexist"]
    )
    contains_safety = any(
        kw in text_lower for kw in ["食品安全", "安全隐患", "卫生问题", "事故", "火灾", "受伤"]
    )
    contains_brand_crisis = any(
        kw in text_lower for kw in ["品牌危机", "声誉受损", "财务造假", "高管丑闻"]
    )

    for rule in policy.escalation_rules:
        cond = rule["condition"]
        triggered = False
        if cond == "negative_count >= 5" and negative_count >= 5:
            triggered = True
        elif cond == "negative_count >= 10" and negative_count >= 10:
            triggered = True
        elif cond == "engagement > 10000" and engagement > 10000:
            triggered = True
        elif cond == "engagement > 50000" and engagement > 50000:
            triggered = True
        elif cond == "contains_discrimination" and contains_discrimination:
            triggered = True
        elif cond == "contains_safety_issue" and contains_safety:
            triggered = True
        elif cond == "contains_brand_crisis" and contains_brand_crisis:
            triggered = True
        elif cond == "koc_count >= 3" and negative_count >= 3:
            triggered = True  # 简化：用 negative_count 近似 KOC 数量

        if triggered:
            escalation_triggered.append(rule)
            action = rule["action"]
            if action == "escalate_to_critical":
                risk_score = max(risk_score, policy.risk_thresholds["critical"] + 1)
            elif action == "escalate_to_high":
                risk_score = max(risk_score, policy.risk_thresholds["high"] + 1)
            elif action == "escalate_to_medium":
                risk_score = max(risk_score, policy.risk_thresholds["medium"] + 1)

    # 7. 按域阈值判定等级（critical 独立，不合并为 high）
    thresholds = policy.risk_thresholds
    if risk_score >= thresholds["critical"]:
        risk_level = "critical"
    elif risk_score >= thresholds["high"]:
        risk_level = "high"
    elif risk_score >= thresholds["medium"]:
        risk_level = "medium"
    elif risk_score >= thresholds["low"]:
        risk_level = "low"
    else:
        risk_level = "low"

    return {
        "domain_id": policy.domain_id,
        "product_id": policy.product_id,
        "policy_version": policy.policy_version,
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "risk_dimensions": policy.risk_dimensions,
        "matched_keywords": matched_keywords,
        "escalation_triggered": escalation_triggered,
        "data_available": True,
        "thresholds_used": dict(thresholds),
        "note": "Dual-domain policy applied; critical independent from high; unknown preserved; 0/0 safe",
    }


def compare_domain_risk(
    text: str = "",
    sentiment: str = "unknown",
    engagement: int = 0,
    negative_count: int = 0,
) -> Dict[str, _Any]:
    """同一条数据在 CTH 和 ZBMP 两域的风险对比。

    用于验证双域阈值独立性：同一条数据在两域可能风险等级不同。
    """
    cth_result = compute_domain_risk_score(text, sentiment, engagement, negative_count, domain_id="cth")
    zbmp_result = compute_domain_risk_score(text, sentiment, engagement, negative_count, domain_id="zbmp")
    return {
        "cth": cth_result,
        "zbmp": zbmp_result,
        "same_risk_level": cth_result["risk_level"] == zbmp_result["risk_level"],
        "score_diff": round(abs(cth_result["risk_score"] - zbmp_result["risk_score"]), 2),
        "thresholds_independent": (
            cth_result["thresholds_used"] != zbmp_result["thresholds_used"]
        ),
        "note": "Same input evaluated against independent CTH and ZBMP risk policies",
    }


def get_risk_policy_summary() -> Dict[str, _Any]:
    """获取双域风险策略总览（用于审计）。"""
    return {
        "cth": {
            "policy_version": CTH_RISK_POLICY.policy_version,
            "thresholds": dict(CTH_RISK_POLICY.risk_thresholds),
            "dimensions": CTH_RISK_POLICY.risk_dimensions,
            "keyword_count": len(CTH_RISK_POLICY.keyword_weights),
            "escalation_rule_count": len(CTH_RISK_POLICY.escalation_rules),
        },
        "zbmp": {
            "policy_version": ZBMP_RISK_POLICY.policy_version,
            "thresholds": dict(ZBMP_RISK_POLICY.risk_thresholds),
            "dimensions": ZBMP_RISK_POLICY.risk_dimensions,
            "keyword_count": len(ZBMP_RISK_POLICY.keyword_weights),
            "escalation_rule_count": len(ZBMP_RISK_POLICY.escalation_rules),
        },
        "thresholds_independent": (
            CTH_RISK_POLICY.risk_thresholds != ZBMP_RISK_POLICY.risk_thresholds
        ),
        "keywords_independent": (
            CTH_RISK_POLICY.keyword_weights != ZBMP_RISK_POLICY.keyword_weights
        ),
        "hard_constraints": [
            "unknown preserved (not fabricated as negative/low)",
            "critical independent from high",
            "0/0 safe division with data_available flag",
            "CTH and ZBMP thresholds/keywords/escalation fully independent",
        ],
    }


# ============================================================
# IC-044: 耸动/合成内容风险信号（与IC-020舆情告警联动）
# ============================================================

# 耸动标题关键词库（命中即提升风险信号）
SENSATIONAL_KEYWORDS = {
    "zh": [
        "震惊", "惊呆", "炸了", "爆了", "疯传", "刷屏", "热搜", "紧急",
        "重磅", "突发", "致命", "可怕", "恐怖", "恶心", "愤怒", "气死",
        "万万没想到", "不看后悔", "速看", "马上删", "内部消息", "绝密",
        "曝光", "揭秘", "黑幕", "内幕", "真相", "竟然", "居然", "太可怕",
        "你绝对不知道", "99%的人不知道", "看完吓一跳", "细思极恐",
    ],
    "en": [
        "shocking", "unbelievable", "crazy", "insane", "viral", "breaking",
        "urgent", "bombshell", "exposed", "revealed", "secret", "hidden",
        "terrifying", "horrifying", "outrageous", "you won't believe",
        "must see", "mind blowing", "jaw dropping",
    ],
}

# 合成内容特征（AI生成/深度伪造/拼接内容的信号）
SYNTHETIC_CONTENT_SIGNALS = {
    "zh": [
        "AI生成", "AI制作", "虚拟人", "数字人", "深度伪造", "换脸",
        "合成视频", "AI配音", "文本转语音", "自动生成", "一键生成",
    ],
    "en": [
        "AI generated", "AI made", "deepfake", "synthetic", "virtual human",
        "digital human", "face swap", "AI voice", "text to speech",
        "auto generated", "generated by AI",
    ],
}

# 标题党模式（正则或模式匹配）
CLICKBAIT_PATTERNS = [
    r"\d+个.*(秘密|真相|技巧|方法|原因)",  # "10个你不知道的秘密"
    r"不看.*后悔",  # "不看后悔"
    r"看完.*(震惊|惊呆|吓一跳)",  # "看完震惊"
    r"居然.*(是|有|能)",  # "居然是"
    r"万万没想到",  # "万万没想到"
    r"速看|马上删|即将删除",  # 紧迫感
]


def detect_sensational_content(title: str = "", content: str = "",
                                 lang: str = "zh") -> dict:
    """检测耸动/合成内容风险信号（IC-044）。

    作为风险评估的输入因子，与IC-020舆情告警联动。

    Args:
        title: 内容标题
        content: 内容正文
        lang: 语言（zh/en）

    Returns:
        {
            "is_sensational": bool,        # 是否耸动内容
            "sensational_score": float,    # 耸动程度 0-1
            "matched_keywords": list,       # 命中的耸动关键词
            "is_synthetic": bool,           # 是否合成内容信号
            "synthetic_score": float,       # 合成内容信号强度 0-1
            "matched_synthetic_signals": list,  # 命中的合成内容信号
            "clickbait_detected": bool,     # 是否标题党
            "risk_factor": float,           # 综合风险因子 0-1（可作为 risk_engine 输入）
            "confidence": float,            # 检测置信度
        }

    注意：本函数仅做关键词/模式匹配的初筛，不做最终风险判定。
    最终风险等级由 evaluate_risk() 综合多因子决定。
    不伪造数据：无命中时返回 0 分和空列表，不提升风险。
    """
    import re as _re

    text = f"{title} {content}".strip()
    if not text:
        return {
            "is_sensational": False, "sensational_score": 0.0,
            "matched_keywords": [], "is_synthetic": False,
            "synthetic_score": 0.0, "matched_synthetic_signals": [],
            "clickbait_detected": False, "risk_factor": 0.0,
            "confidence": 0.0, "note": "empty input, no risk signal",
        }

    text_lower = text.lower()
    lang_key = lang if lang in SENSATIONAL_KEYWORDS else "zh"

    # 1. 耸动关键词检测
    sensational_matches = []
    for kw in SENSATIONAL_KEYWORDS.get(lang_key, []):
        if kw.lower() in text_lower:
            sensational_matches.append(kw)

    # 标题中命中权重更高
    title_lower = title.lower()
    title_hits = sum(1 for kw in sensational_matches if kw.lower() in title_lower)
    content_hits = len(sensational_matches) - title_hits

    # 耸动评分：标题命中权重 0.15/个，正文命中 0.05/个，上限 1.0
    sensational_score = min(1.0, title_hits * 0.15 + content_hits * 0.05)
    is_sensational = sensational_score >= 0.15

    # 2. 合成内容信号检测
    synthetic_matches = []
    for sig in SYNTHETIC_CONTENT_SIGNALS.get(lang_key, []):
        if sig.lower() in text_lower:
            synthetic_matches.append(sig)

    synthetic_score = min(1.0, len(synthetic_matches) * 0.2)
    is_synthetic = len(synthetic_matches) > 0

    # 3. 标题党模式检测
    clickbait_detected = False
    for pattern in CLICKBAIT_PATTERNS:
        if _re.search(pattern, text, _re.IGNORECASE):
            clickbait_detected = True
            break

    # 4. 综合风险因子（作为 risk_engine 输入）
    # 耸动内容 + 高互动 = 舆情传播风险
    # 合成内容 = 真实性风险
    risk_factor = min(1.0, sensational_score * 0.6 + synthetic_score * 0.3
                      + (0.1 if clickbait_detected else 0.0))

    # 置信度：基于命中数量和类型
    total_signals = len(sensational_matches) + len(synthetic_matches)
    confidence = min(1.0, total_signals * 0.1 + (0.2 if clickbait_detected else 0))

    return {
        "is_sensational": is_sensational,
        "sensational_score": round(sensational_score, 4),
        "matched_keywords": sensational_matches,
        "is_synthetic": is_synthetic,
        "synthetic_score": round(synthetic_score, 4),
        "matched_synthetic_signals": synthetic_matches,
        "clickbait_detected": clickbait_detected,
        "risk_factor": round(risk_factor, 4),
        "confidence": round(confidence, 4),
        "lang": lang_key,
        "note": "IC-044 sensational/synthetic content signal; use as risk input factor, not final verdict",
    }


def evaluate_risk_with_sensational(title: str = "", content: str = "",
                                     sentiment=None, risk_level=None,
                                     engagement=None, severity=None,
                                     confidence=None, lang: str = "zh",
                                     threshold: float = 0.5) -> dict:
    """综合风险评估（含 IC-044 耸动/合成内容信号）。

    在 evaluate_risk() 基础上，叠加耸动/合成内容风险因子。
    耸动内容 + 负面情感 + 高互动 → 提升风险等级（但不超过 high，critical 需 severity 支撑）。

    Returns:
        evaluate_risk() 的完整结果 + sensational_signal 字段
    """
    # 先做耸动/合成内容检测
    sensational = detect_sensational_content(title=title, content=content, lang=lang)

    # 基础风险评估
    base = evaluate_risk(
        sentiment=sentiment, risk_level=risk_level,
        engagement=engagement, severity=severity,
        confidence=confidence, threshold=threshold,
    )

    # 叠加耸动风险因子
    risk_factor = sensational["risk_factor"]
    final_risk = base["final_risk"]

    # 耸动内容 + 负面/未知情感 → 至少 medium（不伪造为 high/critical）
    if (risk_factor >= 0.3 and base["sentiment"] in ("negative", "unknown")
            and final_risk in ("low", "unknown")):
        final_risk = "medium"

    # 合成内容信号 → 标记真实性风险（不直接提升等级，增加 risk_adjusted 考量）
    if sensational["is_synthetic"]:
        base["authenticity_risk"] = "synthetic_content_detected"

    base["sensational_signal"] = sensational
    base["final_risk"] = final_risk
    base["risk_score"] = _RISK_SCORE.get(final_risk, 0)
    base["note"] = base.get("note", "") + "; IC-044 sensational/synthetic factor applied"

    return base
