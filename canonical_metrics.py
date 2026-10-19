# -*- coding: utf-8 -*-
"""Canonical Business Metrics —— 统一数据智能管线唯一业务计算层（只读纯函数）。

契约依据：Zachary-OS-AI `contracts/CTR-CANONICAL-METRICS-P0-01.md`
设计原则（Unified Data Intelligence Pipeline V1.0）：
  一次业务计算、多处消费。UI / 表格 / 图表 / 报告 / 导出 / AI 都只能调用本模块，
  不得各自再写一份情感/风险/互动计数，避免第二数字真相。

边界：
  - 零 I/O、零第三方依赖、不连接数据库；取数由调用方完成，本模块只接收 list[dict]，
    因此可被任意层 WRAP，且可脱离运行时单测。
  - 只做"业务计算"，不做采集、不做主体过滤（主体 Gate 在 subject_rules，红线不并入）。

口径锁定（Q1 方案甲，2026-09-03 由用户拍板，永久不可静默更改）：
  - 高风险 high 桶只含 risk_level == 'high'；critical 是独立的更高桶，绝不并入 high。
  - 情感三值 positive/neutral/negative 精确匹配，其余 -> unknown，不并入任一、不伪装成 0。
  - 互动 engagement = likes + comments + collects + shares（4 字段，与 kos_metrics 现网一致）；
    "仅点赞 likes" 是另一个独立指标，禁止用"互动"指代"赞"。
  - 比率分母为有效项之和；分母为 0 返回 None（不可算/UNKNOWN），绝不返回 0 伪装。

数据五态（与 data_quality_gate 写入校验互补，本模块为读取计算层）：
  0=真实测得零；None=未采集/不可算；unknown=采集到但取值无法判定；STALE/ERROR 由调用层标注。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional
import re

# ---- 取值域常量（唯一口径来源，禁止在各业务文件另写一份）----
SENTIMENT_POSITIVE = "positive"
SENTIMENT_NEUTRAL = "neutral"
SENTIMENT_NEGATIVE = "negative"
SENTIMENT_KNOWN = (SENTIMENT_POSITIVE, SENTIMENT_NEUTRAL, SENTIMENT_NEGATIVE)

RISK_HIGH = "high"
RISK_MEDIUM = "medium"
RISK_LOW = "low"
RISK_CRITICAL = "critical"  # 方案甲：独立更高桶，不并入 high
RISK_KNOWN = (RISK_HIGH, RISK_MEDIUM, RISK_LOW, RISK_CRITICAL)

ENGAGEMENT_KEYS = ("likes", "comments", "collects", "shares")

_MISSING = object()


def _as_int(v: Any) -> int:
    """把计数字段安全转为非负 int。None/'' -> 0；数值字符串/浮点可转；布尔按 0/1。"""
    if v is None or v == "":
        return 0
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v if v >= 0 else 0
    if isinstance(v, float):
        return int(v) if v >= 0 else 0
    try:
        n = float(str(v).strip())
    except (TypeError, ValueError):
        return 0
    return int(n) if n >= 0 else 0


def _is_missing(v: Any) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _ensure_list(notes: Any) -> List[dict]:
    if notes is None:
        return []
    if isinstance(notes, list):
        return notes
    if isinstance(notes, tuple):
        return list(notes)
    raise TypeError(
        "notes 必须是 list[dict]（或 tuple），收到 %s" % type(notes).__name__
    )


# ============================================================
# FN-SENTIMENT-COUNT v1
# ============================================================
def sentiment_count(notes: List[dict], key: str = "sentiment") -> Dict[str, Any]:
    """FN-SENTIMENT-COUNT：情感分布计数。

    output: {positive, neutral, negative, unknown, known, total, quality:{unknown}}
    - 三值精确匹配；非三值（含 None/空串/异常取值）一律计入 unknown，不并入任一。
    - total = 输入条数；known = 三值之和；unknown = total - known。
    - 空集返回全 0 且 quality.empty=True（区别于 unknown）。
    """
    rows = _ensure_list(notes)
    out = {SENTIMENT_POSITIVE: 0, SENTIMENT_NEUTRAL: 0, SENTIMENT_NEGATIVE: 0}
    unknown = 0
    for n in rows:
        v = n.get(key) if isinstance(n, dict) else None
        if v in SENTIMENT_KNOWN:
            out[v] += 1
        else:
            unknown += 1
    known = out[SENTIMENT_POSITIVE] + out[SENTIMENT_NEUTRAL] + out[SENTIMENT_NEGATIVE]
    out.update(
        {
            "unknown": unknown,
            "known": known,
            "total": len(rows),
            "quality": {"unknown": unknown, "empty": len(rows) == 0},
        }
    )
    return out


# ============================================================
# FN-RISK-COUNT v1（方案甲：critical 独立，不并入 high）
# ============================================================
def risk_count(notes: List[dict], key: str = "risk_level") -> Dict[str, Any]:
    """FN-RISK-COUNT：风险等级分桶计数。

    output: {high, medium, low, critical, other, missing, total, quality:{...}}
    - high/medium/low/critical 精确匹配；**high 绝不含 critical**（Q1 方案甲）。
    - 非空但不在四枚举 -> other（采集到但无法判定到已知等级）。
    - None/空串 -> missing（未采集，区别于 other）。
    """
    rows = _ensure_list(notes)
    out = {RISK_HIGH: 0, RISK_MEDIUM: 0, RISK_LOW: 0, RISK_CRITICAL: 0}
    other = 0
    missing = 0
    for n in rows:
        v = n.get(key) if isinstance(n, dict) else None
        if v in RISK_KNOWN:
            out[v] += 1
        elif _is_missing(v):
            missing += 1
        else:
            other += 1
    out.update(
        {
            "other": other,
            "missing": missing,
            "total": len(rows),
            "quality": {"other": other, "missing": missing, "empty": len(rows) == 0},
        }
    )
    return out


# ============================================================
# FN-ENGAGEMENT v2
# ============================================================
def engagement_count(value: Any) -> Optional[int]:
    """An exact measured nonnegative count, never a guessed/rounded count."""
    if type(value) is int:
        return value if value >= 0 else None
    if type(value) is float:
        return int(value) if 0 <= value < 2**53 and value.is_integer() else None
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)", text):
            try:
                return int(text.replace(",", ""))
            except ValueError:
                # Preserve the runtime's integer-conversion safety limit.
                return None
    return None


def engagement_of(note: dict, keys: Iterable[str] = ENGAGEMENT_KEYS) -> Optional[int]:
    """Complete per-post total; use engagement_stats for measured partial sums."""
    return engagement_stats([note], keys=keys)["sum"]


def engagement_stats(
    notes: List[dict], keys: Iterable[str] = ENGAGEMENT_KEYS
) -> Dict[str, Any]:
    """FN-ENGAGEMENT：互动量聚合。

    sum/avg and per_field require complete coverage. Measured partial subtotals
    live in observed_sum/observed_per_field with explicit component coverage.
    Empty or entirely unobserved inputs never manufacture a zero total.
    """
    rows = _ensure_list(notes)
    keys = tuple(keys)
    if not keys or len(set(keys)) != len(keys):
        raise ValueError("engagement keys must be nonempty and unique")
    field_sums = {k: 0 for k in keys}
    field_known = {k: 0 for k in keys}
    missing_notes = 0
    invalid_fields = 0
    observed_notes = 0
    complete_notes = 0
    nonzero = 0
    for n in rows:
        row_known = 0
        row_sum = 0
        for k in keys:
            v = n.get(k) if isinstance(n, dict) else None
            iv = engagement_count(v)
            if iv is None:
                if not _is_missing(v):
                    invalid_fields += 1
                continue
            row_known += 1
            field_known[k] += 1
            field_sums[k] += iv
            row_sum += iv
        if row_known != len(keys):
            missing_notes += 1
        else:
            complete_notes += 1
        if row_known:
            observed_notes += 1
        if row_sum > 0:
            nonzero += 1
    known = sum(field_known.values())
    expected = len(rows) * len(keys)
    state = (
        "NO_DATA"
        if not rows
        else "UNKNOWN" if not known else "COMPLETE" if known == expected else "PARTIAL"
    )
    observed_sum = sum(field_sums.values()) if known else None
    complete = state == "COMPLETE"
    reason = {
        "NO_DATA": "NO_RECORDS",
        "UNKNOWN": "NO_MEASURED_ENGAGEMENT_COMPONENTS",
        "PARTIAL": "INCOMPLETE_ENGAGEMENT_COMPONENT_COVERAGE",
        "COMPLETE": None,
    }[state]
    average = None
    average_reason = reason
    if complete:
        try:
            average = observed_sum / len(rows)
        except OverflowError:
            average_reason = "ENGAGEMENT_AVERAGE_OUT_OF_RANGE"
    return {
        "sum": observed_sum if complete else None,
        "avg": average,
        "count": len(rows),
        "nonzero": nonzero,  # Number of posts with a measured positive component.
        "per_field": {
            k: field_sums[k] if rows and field_known[k] == len(rows) else None
            for k in keys
        },
        "observed_sum": observed_sum,
        "observed_per_field": {
            k: field_sums[k] if field_known[k] else None for k in keys
        },
        "quality": {
            "version": "2.0",
            "state": state,
            "reason": reason,
            "avg_reason": average_reason,
            "missing_field_notes": missing_notes,
            "empty": not rows,
            "known_field_count": known,
            "expected_field_count": expected,
            "missing_field_count": expected - known,
            "invalid_field_count": invalid_fields,
            "observed_notes": observed_notes,
            "complete_notes": complete_notes,
            "per_field": {
                k: {"known": field_known[k], "expected": len(rows)} for k in keys
            },
        },
    }


# ============================================================
# 比率 Metric（分母 0 -> None，绝不伪装 0）
# ============================================================
def safe_ratio(
    part: float, whole: float, ndigits: Optional[int] = 4
) -> Optional[float]:
    """安全比率。whole 为 None/0 -> None（不可算）；否则 part/whole，默认保留 4 位。"""
    try:
        w = float(whole)
        p = float(part)
    except (TypeError, ValueError):
        return None
    if w == 0:
        return None
    r = p / w
    return round(r, ndigits) if ndigits is not None else r


def neg_ratio(sent: Dict[str, Any], ndigits: int = 4) -> Optional[float]:
    """MET-NEG-RATIO = negative / (positive+neutral+negative)，分母不含 unknown。"""
    known = (
        sent.get(SENTIMENT_POSITIVE, 0)
        + sent.get(SENTIMENT_NEUTRAL, 0)
        + sent.get(SENTIMENT_NEGATIVE, 0)
    )
    return safe_ratio(sent.get(SENTIMENT_NEGATIVE, 0), known, ndigits)


def pos_ratio(sent: Dict[str, Any], ndigits: int = 4) -> Optional[float]:
    """MET-POS-RATIO = positive / (positive+neutral+negative)，分母不含 unknown。"""
    known = (
        sent.get(SENTIMENT_POSITIVE, 0)
        + sent.get(SENTIMENT_NEUTRAL, 0)
        + sent.get(SENTIMENT_NEGATIVE, 0)
    )
    return safe_ratio(sent.get(SENTIMENT_POSITIVE, 0), known, ndigits)


# ============================================================
# 维度分组工具（供按 category/brand/event/时间窗 分桶后复用同一 Canonical）
# ============================================================
def group_count(
    notes: List[dict], dim: str, fn: Callable[[List[dict]], Dict[str, Any]]
) -> Dict[Any, Dict[str, Any]]:
    """按 note[dim] 取值分组，对每组应用 Canonical 函数 fn（fn 须为上面的纯函数）。

    缺失维度值归入键 None。调用方因此不必为每个维度重写计数逻辑。
    """
    rows = _ensure_list(notes)
    buckets: Dict[Any, List[dict]] = {}
    for n in rows:
        buckets.setdefault(n.get(dim) if isinstance(n, dict) else None, []).append(n)
    return {k: fn(v) for k, v in buckets.items()}


# ============================================================
# Canonical Function Registry 元数据（审计/可观测唯一登记处）
# 与 function_registry.py（AI 语义路由）职责不同，此处是业务计算注册。
# ============================================================
CANONICAL_FUNCTIONS: Dict[str, Dict[str, Any]] = {
    "FN-SENTIMENT-COUNT": {
        "function_id": "FN-SENTIMENT-COUNT",
        "version": "1.0",
        "owner": "xujing-core",
        "purpose": "情感三值分布计数，非三值隔离为 unknown",
        "inputs": "list[dict note], key=sentiment",
        "outputs": "positive/neutral/negative/unknown/known/total/quality",
        "formula": "按 sentiment 精确匹配三值，其余 unknown",
        "unit": "count",
        "error_policy": "非 list 抛 TypeError；空集全 0+empty；异常取值计 unknown",
        "status": "production-verified",
    },
    "FN-RISK-COUNT": {
        "function_id": "FN-RISK-COUNT",
        "version": "1.0",
        "owner": "xujing-core",
        "purpose": "风险等级分桶；方案甲 high 不含 critical",
        "inputs": "list[dict note], key=risk_level",
        "outputs": "high/medium/low/critical/other/missing/total/quality",
        "formula": "四枚举精确匹配；非空未识别 other；空 missing",
        "unit": "count",
        "error_policy": "critical 独立桶；high 永不并入 critical",
        "status": "production-verified",
    },
    "FN-ENGAGEMENT": {
        "function_id": "FN-ENGAGEMENT",
        "version": "2.0",
        "owner": "xujing-core",
        "purpose": "互动量=likes+comments+collects+shares 聚合",
        "inputs": "list[dict note]",
        "outputs": "sum/avg/count/nonzero/per_field/observed_sum/observed_per_field/quality",
        "formula": "完整四字段合计；部分实测合计附组件覆盖语义",
        "unit": "count",
        "error_policy": "缺测/非法计数不转0；不完整或空集sum/avg=None",
        "status": "implemented",
    },
    "MET-NEG-RATIO": {
        "function_id": "MET-NEG-RATIO",
        "version": "1.0",
        "owner": "xujing-core",
        "purpose": "负面率，分母为三值和不含 unknown",
        "inputs": "sentiment_count()",
        "outputs": "float|None",
        "formula": "negative/(pos+neu+neg)",
        "unit": "ratio",
        "error_policy": "分母0返回None",
        "status": "production-verified",
    },
    "MET-POS-RATIO": {
        "function_id": "MET-POS-RATIO",
        "version": "1.0",
        "owner": "xujing-core",
        "purpose": "正面率，分母为三值和不含 unknown",
        "inputs": "sentiment_count()",
        "outputs": "float|None",
        "formula": "positive/(pos+neu+neg)",
        "unit": "ratio",
        "error_policy": "分母0返回None",
        "status": "production-verified",
    },
}


def registry_snapshot() -> Dict[str, Dict[str, Any]]:
    """返回 Canonical Function/Metric 注册表副本（供 /api 或审计读取，不暴露可变内部）。"""
    return {k: dict(v) for k, v in CANONICAL_FUNCTIONS.items()}


def binomial_confidence(successes, trials, *, confidence=0.95):
    """G146 Wilson score interval. Counts are Bernoulli trials, not event totals.

    Assumes independent comparable trials; interval does not repair selection bias.
    """
    from math import sqrt, isfinite
    from statistics import NormalDist

    if (
        type(successes) is not int
        or type(trials) is not int
        or not 0 <= successes <= trials <= 10**12
        or type(confidence) not in (float, int)
        or not isfinite(confidence)
        or not 0 < confidence < 1
    ):
        raise ValueError("STATISTICS_BINOMIAL_INPUT_INVALID")
    result = {
        "method": "wilson-score@1",
        "state": "READY" if trials else "NO_DATA",
        "successes": successes,
        "n": trials,
        "denominator": "comparable Bernoulli trials",
        "unit": "proportion",
        "confidence": confidence,
        "value": None,
        "interval": None,
        "limitations": [
            "Independent comparable Bernoulli trials assumed; selection bias is not covered."
        ],
    }
    if not trials:
        return result
    p, z = successes / trials, NormalDist().inv_cdf((1 + confidence) / 2)
    d = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / d
    half = z * sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / d
    result.update(value=p, interval=[max(0.0, center - half), min(1.0, center + half)])
    return result


def share_of_voice(counts, *, platform_coverage, observation_window):
    """G156 within-observed-frame share, not population market share or sales."""
    if (
        not isinstance(counts, dict)
        or not 1 <= len(counts) <= 1000
        or any(
            not isinstance(k, str)
            or not k.strip()
            or type(v) is not int
            or not 0 <= v <= 10**9
            for k, v in counts.items()
        )
        or not isinstance(platform_coverage, list)
        or not platform_coverage
        or any(not isinstance(p, str) or not p.strip() for p in platform_coverage)
        or not isinstance(observation_window, str)
        or not observation_window.strip()
    ):
        raise ValueError("STATISTICS_SOV_INPUT_INVALID")
    denominator = sum(counts.values())
    return {
        "method": "observed-frame-sov@1",
        "state": "READY" if denominator else "NO_DATA",
        "n": denominator,
        "denominator": "sum of mutually exclusive observed brand mentions",
        "unit": "proportion",
        "platform_coverage": platform_coverage,
        "observation_window": observation_window,
        "shares": {k: binomial_confidence(v, denominator) for k, v in counts.items()},
        "limitations": [
            "Counts must share scope, window and counting rule; overlapping mentions must be disambiguated.",
            "Observed-frame voice share is not sales share or population coverage.",
        ],
    }


def net_sentiment_confidence(notes, *, confidence=0.95):
    """G156 observed net sentiment with conservative simultaneous score bounds.

    This is not NPS: sentiment labels do not measure willingness to recommend.
    """
    counts = sentiment_count(notes)
    known = counts["known"]
    positive = binomial_confidence(
        counts["positive"], known, confidence=1 - (1 - confidence) / 2
    )
    negative = binomial_confidence(
        counts["negative"], known, confidence=1 - (1 - confidence) / 2
    )
    return {
        "method": "net-sentiment-bonferroni-wilson@1",
        "state": "READY" if known else "NO_DATA",
        "n": known,
        "unknown_n": counts["unknown"],
        "unit": "index points [-100,100]",
        "denominator": "known positive, neutral and negative labels; unknown excluded",
        "value": (
            100 * (counts["positive"] - counts["negative"]) / known if known else None
        ),
        "interval": (
            [
                100 * (positive["interval"][0] - negative["interval"][1]),
                100 * (positive["interval"][1] - negative["interval"][0]),
            ]
            if known
            else None
        ),
        "confidence": confidence,
        "counts": counts,
        "limitations": [
            "Conservative Bonferroni combination of two approximate Wilson intervals.",
            "Stored sentiment labels are not recommendation survey answers or NPS.",
        ],
    }


# Existing canonical function/metric metadata remains the one discovery registry.
# Status describes implementation only, never production/business acceptance.
_STATISTICS_PURPOSES = (
    (
        "plan_budgeted_schedule",
        "安排预算内资源与档期",
        "schedule",
        "tasks,resource_ids,budget_minor,currency,benefit_unit,start_at,slot_minutes,horizon,required_coverage,mandatory_tasks,prerequisites,exclusions",
        "declared benefit units",
    ),
    (
        "compare_with_synthetic_baseline",
        "比较活动与组合对照基线",
        "synthetic_control",
        "periods,frequency,treated,donors,pre_periods,max_pre_rmse,design",
        "input outcome units",
    ),
    (
        "measure_recommendation",
        "查看推荐调查结果",
        "nps",
        "question_type,responses,survey_id,sampling_frame,observation_window",
        "recommendation index",
    ),
    (
        "compare_sales_share",
        "查看同口径销售份额",
        "som",
        "numerator,market_total,sales_basis,currency,period_start,period_end,entity,geography,category,market_definition,data_basis",
        "fraction",
    ),
    (
        "assess_rate_reliability",
        "比例有多可信",
        "binomial",
        "successes,trials",
        "proportion",
    ),
    (
        "compare_voice_share",
        "比较声量份额",
        "sov",
        "counts,platform_coverage,observation_window",
        "proportion",
    ),
    (
        "understand_reputation",
        "了解口碑分布",
        "net_sentiment",
        "records",
        "index points",
    ),
    (
        "understand_change",
        "了解趋势变化",
        "trend",
        "values,dates",
        "declared measurement unit",
    ),
    (
        "understand_relationship_influence",
        "了解关系影响与桥接者",
        "network",
        "nodes,edges",
        "structural centrality",
    ),
    (
        "compare_proposals",
        "比较备选方案",
        "decision",
        "alternatives,matrix,pairwise,benefit",
        "relative preference",
    ),
    (
        "choose_budgeted_portfolio",
        "在预算内选择组合",
        "portfolio",
        "items,budget,required_coverage",
        "declared utility",
    ),
    ("check_probability_quality", "检查概率质量", "calibration", "rows", "probability"),
    (
        "choose_content_variant",
        "比较内容实验版本",
        "experiment",
        "arms,stop_probability,minimum_trials,enable_thompson,seed",
        "success probability",
    ),
    (
        "measure_information_change",
        "衡量信息变化",
        "novelty",
        "current_counts,historical_counts or same-version embeddings",
        "nats and/or separately labeled cosine distance",
    ),
    (
        "assess_prediction_uncertainty",
        "了解预测不确定性",
        "conformal",
        "rows,alpha",
        "declared outcome unit",
    ),
    (
        "compare_activity_effect",
        "比较活动前后效果",
        "did",
        "treated,control,intervention_index,pretrend_tolerance,design_assumptions_confirmed",
        "declared outcome unit",
    ),
    (
        "understand_event_diffusion",
        "了解事件扩散",
        "hawkes",
        "times,observation_end,time_unit",
        "events per declared time unit",
    ),
    (
        "resolve_entity_candidates",
        "复核实体匹配候选",
        "entity_matching",
        "rows",
        "conditional match score",
    ),
    (
        "evaluate_language_labels",
        "评估不同语言的标签质量",
        "classifier_evaluation",
        "rows,model_version,confidence_threshold,heldout_declared",
        "classification evaluation",
    ),
    (
        "rank_comparable_performance",
        "比较同口径表现",
        "beta_ranking",
        "groups",
        "conditional success probability",
    ),
    (
        "summarize_touchpoint_credit",
        "梳理行为触点贡献",
        "attribution",
        "paths",
        "descriptive conversion credit",
    ),
    (
        "plan_marketing_budget",
        "评估营销预算方案",
        "mmm",
        "periods,currency,outcome_unit,filing_entity,disclosure_scope,spend_basis; optional region,macro_controls[{evidence_ids,selection}]",
        "outcome per currency",
    ),
    (
        "understand_adoption",
        "了解采用增长",
        "bass",
        "times,cumulative,time_unit",
        "cumulative adoption",
    ),
    (
        "discover_topics",
        "发现资料中的主题",
        "topics",
        "documents,language",
        "observed lexical topics",
    ),
)
for _purpose, _label, _method, _inputs, _unit in _STATISTICS_PURPOSES:
    _function_id = "FN-STATISTICS-" + _method.upper().replace("_", "-")
    CANONICAL_FUNCTIONS[_function_id] = {
        "function_id": _function_id,
        "version": "1.0",
        "owner": "shared-reporting",
        "purpose": _label,
        "business_purpose": _purpose,
        "analysis": _method,
        "inputs": _inputs,
        "outputs": "structured result, assumptions, sample, limits, SavedWork draft",
        "formula": "versioned bounded method exposed in result.method",
        "unit": _unit,
        "error_policy": "missing/invalid/insufficient inputs never become zero or a causal claim",
        "status": "implemented-bounded-not-business-validated",
        "implementation": "lumenis.shared.reporting.business_brief.analyze_statistics_source",
        "source_contract": "lumenis.statistics-input/v1",
    }
del _purpose, _label, _method, _inputs, _unit, _function_id
CANONICAL_FUNCTIONS["FN-STATISTICS-EXPERIMENT"].update({
    "artifact_bound_api": "/api/experience/reports/artifact-experiments",
    "artifact_bound_input_contract": "lumenis.artifact-experiment/v1",
    "artifact_bound_scope": "CTH/BMP source Evidence or explicitly USER_RECORDED Shared SavedWork",
})


def recommendation_score(data):
    """G156 explicit 0–10 recommendation survey; never infer from sentiment."""
    required = {
        "question_type",
        "responses",
        "survey_id",
        "sampling_frame",
        "observation_window",
    }
    if (
        not isinstance(data, dict)
        or set(data) != required
        or data["question_type"] != "likelihood_to_recommend_0_10"
        or any(
            not isinstance(data[k], str) or not data[k].strip()
            for k in ("survey_id", "sampling_frame", "observation_window")
        )
        or not isinstance(data["responses"], list)
        or len(data["responses"]) > 10000
    ):
        raise ValueError("STATISTICS_RECOMMENDATION_SURVEY_REQUIRED")
    ids, scores = set(), []
    for row in data["responses"]:
        if (
            not isinstance(row, dict)
            or set(row) != {"response_id", "score"}
            or not isinstance(row["response_id"], str)
            or not row["response_id"].strip()
            or row["response_id"] in ids
            or (
                row["score"] is not None
                and (type(row["score"]) is not int or not 0 <= row["score"] <= 10)
            )
        ):
            raise ValueError("STATISTICS_RECOMMENDATION_RESPONSE_INVALID")
        ids.add(row["response_id"])
        if row["score"] is not None:
            scores.append(row["score"])
    n = len(scores)
    promoters, detractors = sum(s >= 9 for s in scores), sum(s <= 6 for s in scores)
    p = binomial_confidence(promoters, n, confidence=0.975)
    d = binomial_confidence(detractors, n, confidence=0.975)
    return {
        "method": "recommendation-nps-bonferroni-wilson@1",
        "state": "READY" if n else "NO_DATA",
        "n": n,
        "missing_n": len(ids) - n,
        "unit": "index points [-100,100]",
        "value": 100 * (promoters - detractors) / n if n else None,
        "interval": (
            [
                100 * (p["interval"][0] - d["interval"][1]),
                100 * (p["interval"][1] - d["interval"][0]),
            ]
            if n
            else None
        ),
        "confidence": 0.95,
        "counts": {
            "promoters": promoters,
            "passives": n - promoters - detractors,
            "detractors": detractors,
        },
        "denominator": "all nonmissing 0–10 recommendation responses, including passives",
        "survey_id": data["survey_id"],
        "sampling_frame": data["sampling_frame"],
        "observation_window": data["observation_window"],
        "limitations": [
            "Conservative Bonferroni combination of approximate Wilson intervals under independent response sampling.",
            "Unique supplied response IDs do not independently prove unique respondents or representative selection.",
            "Recommendation survey definition is user-declared; no prediction of growth or loyalty is established.",
        ],
    }


def sales_market_share(data):
    """G156 ratio of explicitly user-supplied, comparable sales amounts."""
    import math
    from datetime import date

    required = {
        "numerator",
        "market_total",
        "sales_basis",
        "currency",
        "period_start",
        "period_end",
        "entity",
        "geography",
        "category",
        "market_definition",
        "data_basis",
    }
    if (
        not isinstance(data, dict)
        or set(data) != required
        or data["data_basis"] != "user_supplied_sales"
    ):
        raise ValueError("STATISTICS_SOM_USER_SALES_REQUIRED")
    if (
        data["sales_basis"] not in {"revenue", "units"}
        or any(
            not isinstance(data[k], str) or not data[k].strip()
            for k in ("entity", "geography", "category", "market_definition")
        )
        or any(
            type(data[k]) not in {int, float}
            or not math.isfinite(data[k])
            or data[k] < 0
            for k in ("numerator", "market_total")
        )
        or data["numerator"] > data["market_total"]
    ):
        raise ValueError("STATISTICS_SOM_COMPARABLE_SALES_INVALID")
    if data["sales_basis"] == "revenue" and (
        not isinstance(data["currency"], str)
        or len(data["currency"]) != 3
        or not data["currency"].isalpha()
        or not data["currency"].isupper()
    ):
        raise ValueError("STATISTICS_SOM_CURRENCY_REQUIRED")
    if data["sales_basis"] == "units" and (
        data["currency"] is not None
        or any(type(data[k]) is not int for k in ("numerator", "market_total"))
    ):
        raise ValueError("STATISTICS_SOM_UNIT_COUNTS_INVALID")
    try:
        start, end = date.fromisoformat(data["period_start"]), date.fromisoformat(
            data["period_end"]
        )
        if (
            start > end
            or start.isoformat() != data["period_start"]
            or end.isoformat() != data["period_end"]
        ):
            raise ValueError()
    except (TypeError, ValueError) as exc:
        raise ValueError("STATISTICS_SOM_PERIOD_INVALID") from exc
    return {
        "method": "declared-comparable-sales-market-share@1",
        "state": "READY" if data["market_total"] else "NO_DATA",
        "unit": "fraction",
        "value": (
            data["numerator"] / data["market_total"] if data["market_total"] else None
        ),
        "numerator": data["numerator"],
        "denominator": data["market_total"],
        "sales_basis": data["sales_basis"],
        "currency": data["currency"],
        "scope": {
            k: data[k]
            for k in (
                "entity",
                "geography",
                "category",
                "market_definition",
                "period_start",
                "period_end",
            )
        },
        "interval": None,
        "interval_state": "NOT_ESTIMABLE_WITHOUT_MEASUREMENT_OR_SAMPLING_MODEL",
        "limitations": [
            "Both sales numerator and inclusive market denominator are explicitly user supplied.",
            "Common currency, period, product category and geography are declared, not independently verified.",
            "No voice-to-sales conversion, currency conversion, missing-market extrapolation or sampling confidence claim.",
        ],
    }
