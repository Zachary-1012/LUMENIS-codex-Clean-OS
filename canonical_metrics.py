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
    raise TypeError("notes 必须是 list[dict]（或 tuple），收到 %s" % type(notes).__name__)


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
    out.update({
        "unknown": unknown,
        "known": known,
        "total": len(rows),
        "quality": {"unknown": unknown, "empty": len(rows) == 0},
    })
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
    out.update({
        "other": other,
        "missing": missing,
        "total": len(rows),
        "quality": {"other": other, "missing": missing, "empty": len(rows) == 0},
    })
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


def engagement_stats(notes: List[dict], keys: Iterable[str] = ENGAGEMENT_KEYS) -> Dict[str, Any]:
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
    state = "NO_DATA" if not rows else "UNKNOWN" if not known else "COMPLETE" if known == expected else "PARTIAL"
    observed_sum = sum(field_sums.values()) if known else None
    complete = state == "COMPLETE"
    reason = {"NO_DATA": "NO_RECORDS", "UNKNOWN": "NO_MEASURED_ENGAGEMENT_COMPONENTS",
              "PARTIAL": "INCOMPLETE_ENGAGEMENT_COMPONENT_COVERAGE", "COMPLETE": None}[state]
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
        "per_field": {k: field_sums[k] if rows and field_known[k] == len(rows) else None for k in keys},
        "observed_sum": observed_sum,
        "observed_per_field": {k: field_sums[k] if field_known[k] else None for k in keys},
        "quality": {
            "version": "2.0", "state": state, "reason": reason, "avg_reason": average_reason,
            "missing_field_notes": missing_notes, "empty": not rows,
            "known_field_count": known, "expected_field_count": expected,
            "missing_field_count": expected - known, "invalid_field_count": invalid_fields,
            "observed_notes": observed_notes, "complete_notes": complete_notes,
            "per_field": {k: {"known": field_known[k], "expected": len(rows)} for k in keys},
        },
    }


# ============================================================
# 比率 Metric（分母 0 -> None，绝不伪装 0）
# ============================================================
def safe_ratio(part: float, whole: float, ndigits: Optional[int] = 4) -> Optional[float]:
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
    known = sent.get(SENTIMENT_POSITIVE, 0) + sent.get(SENTIMENT_NEUTRAL, 0) + sent.get(SENTIMENT_NEGATIVE, 0)
    return safe_ratio(sent.get(SENTIMENT_NEGATIVE, 0), known, ndigits)


def pos_ratio(sent: Dict[str, Any], ndigits: int = 4) -> Optional[float]:
    """MET-POS-RATIO = positive / (positive+neutral+negative)，分母不含 unknown。"""
    known = sent.get(SENTIMENT_POSITIVE, 0) + sent.get(SENTIMENT_NEUTRAL, 0) + sent.get(SENTIMENT_NEGATIVE, 0)
    return safe_ratio(sent.get(SENTIMENT_POSITIVE, 0), known, ndigits)


# ============================================================
# 维度分组工具（供按 category/brand/event/时间窗 分桶后复用同一 Canonical）
# ============================================================
def group_count(notes: List[dict], dim: str, fn: Callable[[List[dict]], Dict[str, Any]]) -> Dict[Any, Dict[str, Any]]:
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
        "function_id": "FN-SENTIMENT-COUNT", "version": "1.0", "owner": "xujing-core",
        "purpose": "情感三值分布计数，非三值隔离为 unknown",
        "inputs": "list[dict note], key=sentiment", "outputs": "positive/neutral/negative/unknown/known/total/quality",
        "formula": "按 sentiment 精确匹配三值，其余 unknown", "unit": "count",
        "error_policy": "非 list 抛 TypeError；空集全 0+empty；异常取值计 unknown", "status": "production-verified",
    },
    "FN-RISK-COUNT": {
        "function_id": "FN-RISK-COUNT", "version": "1.0", "owner": "xujing-core",
        "purpose": "风险等级分桶；方案甲 high 不含 critical",
        "inputs": "list[dict note], key=risk_level",
        "outputs": "high/medium/low/critical/other/missing/total/quality",
        "formula": "四枚举精确匹配；非空未识别 other；空 missing", "unit": "count",
        "error_policy": "critical 独立桶；high 永不并入 critical", "status": "production-verified",
    },
    "FN-ENGAGEMENT": {
        "function_id": "FN-ENGAGEMENT", "version": "2.0", "owner": "xujing-core",
        "purpose": "互动量=likes+comments+collects+shares 聚合",
        "inputs": "list[dict note]",
        "outputs": "sum/avg/count/nonzero/per_field/observed_sum/observed_per_field/quality",
        "formula": "完整四字段合计；部分实测合计附组件覆盖语义", "unit": "count",
        "error_policy": "缺测/非法计数不转0；不完整或空集sum/avg=None", "status": "implemented",
    },
    "MET-NEG-RATIO": {
        "function_id": "MET-NEG-RATIO", "version": "1.0", "owner": "xujing-core",
        "purpose": "负面率，分母为三值和不含 unknown", "inputs": "sentiment_count()",
        "outputs": "float|None", "formula": "negative/(pos+neu+neg)", "unit": "ratio",
        "error_policy": "分母0返回None", "status": "production-verified",
    },
    "MET-POS-RATIO": {
        "function_id": "MET-POS-RATIO", "version": "1.0", "owner": "xujing-core",
        "purpose": "正面率，分母为三值和不含 unknown", "inputs": "sentiment_count()",
        "outputs": "float|None", "formula": "positive/(pos+neu+neg)", "unit": "ratio",
        "error_policy": "分母0返回None", "status": "production-verified",
    },
}


def registry_snapshot() -> Dict[str, Dict[str, Any]]:
    """返回 Canonical Function/Metric 注册表副本（供 /api 或审计读取，不暴露可变内部）。"""
    return {k: dict(v) for k, v in CANONICAL_FUNCTIONS.items()}
