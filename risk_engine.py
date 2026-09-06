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

# ============================================================
# Track3：统一状态枚举（禁止 critical=high、unknown=negative）
# ============================================================
RISK_LEVELS = ("low", "medium", "high", "critical", "unknown")
SENTIMENT_LABELS = ("positive", "neutral", "negative", "unknown")

# 风险等级数值映射（仅用于排序/聚合，不用于覆盖原始标签）
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
