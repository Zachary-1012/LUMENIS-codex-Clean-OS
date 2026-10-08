# -*- coding: utf-8 -*-
"""UI View Model —— ZBC 数据→视图统一规范层（Phase 14）。

本模块定义从原始数据到 UI 可视化的完整链路契约：

    DataLayer → FunctionLayer → MetricLayer → TruthTable → ViewModel → Visualization

设计原则：
  - 纯 Python，零 Flask/DB 依赖；取数由调用方注入，本模块只做转换与校验。
  - 每个视图指标必须携带五要素：current_value / delta / freshness / confidence / evidence_refs。
  - 数据缺失显式表达（None / STALE / NO_DATA），绝不静默成 0 或假绿。
  - 时间范围统一枚举：NOW / TODAY / D7 / D30 / D90 / YTD / HISTORICAL。
  - 不修改 SUBJECT_WORDS / subject_hit()；主体过滤由调用方在 FunctionLayer 注入。

契约依据：ZBC Phase 14 UI/Visualization 审计与重建规范。
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# ============================================================
# 0. 常量与枚举
# ============================================================

class TimeRange(enum.Enum):
    """统一时间范围枚举。UI 时间切换器只允许这些值。"""
    NOW = "now"            # 实时快照（最近一次采集）
    TODAY = "today"        # 今日 00:00 至今
    D7 = "7d"              # 最近 7 天
    D30 = "30d"            # 最近 30 天
    D90 = "90d"            # 最近 90 天
    YTD = "ytd"            # 年初至今
    HISTORICAL = "historical"  # 全量历史

    @classmethod
    def from_str(cls, value: str) -> "TimeRange":
        """宽松解析：接受 '7d' / '7D' / '7天' 等。"""
        if not value:
            return cls.TODAY
        v = str(value).strip().lower()
        alias = {
            "now": cls.NOW, "realtime": cls.NOW, "实时": cls.NOW,
            "today": cls.TODAY, "今日": cls.TODAY,
            "7d": cls.D7, "7天": cls.D7, "d7": cls.D7,
            "30d": cls.D30, "30天": cls.D30, "d30": cls.D30,
            "90d": cls.D90, "90天": cls.D90, "d90": cls.D90,
            "ytd": cls.YTD, "年初至今": cls.YTD,
            "historical": cls.HISTORICAL, "all": cls.HISTORICAL, "全量": cls.HISTORICAL,
        }
        return alias.get(v, cls.TODAY)

    def to_seconds(self) -> Optional[int]:
        """返回时间窗口秒数；NOW/YTD/HISTORICAL 返回 None（需特殊处理）。"""
        return {
            TimeRange.NOW: None,
            TimeRange.TODAY: None,  # 按当日 00:00 计算
            TimeRange.D7: 7 * 86400,
            TimeRange.D30: 30 * 86400,
            TimeRange.D90: 90 * 86400,
            TimeRange.YTD: None,
            TimeRange.HISTORICAL: None,
        }[self]


class DataStatus(enum.Enum):
    """数据真值状态。与 TruthTable 配合使用。"""
    OK = "ok"                    # 数据存在且新鲜
    STALE = "stale"              # 数据存在但超过新鲜度阈值
    NO_DATA = "no_data"          # 该时间范围内无数据
    ERROR = "error"              # 取数失败
    PARTIAL = "partial"          # 部分数据可用（如部分平台缺失）
    UNAVAILABLE = "unavailable"  # 数据源不可用（如 OSAI 离线）


class ConfidenceLevel(enum.Enum):
    """置信度等级。基于数据量、新鲜度、来源可靠性综合评定。"""
    HIGH = "high"        # ≥阈值 样本量 + 新鲜 + 多源
    MEDIUM = "medium"    # 中等样本或单源或略陈旧
    LOW = "low"          # 样本不足或数据陈旧或来源不可靠
    UNKNOWN = "unknown"  # 无法评定（无数据/错误）


class ChartType(enum.Enum):
    """可视化图表类型。UI 渲染层据此选择组件。"""
    METRIC_CARD = "metric_card"      # 单值指标卡（current + delta）
    LINE = "line"                     # 趋势折线
    BAR = "bar"                       # 柱状对比
    STACKED_BAR = "stacked_bar"      # 堆叠柱状
    DONUT = "donut"                   # 环形占比
    TABLE = "table"                   # 数据表格
    TIMELINE = "timeline"             # 事件时间线
    HEATMAP = "heatmap"               # 热力图
    STATUS_LIGHT = "status_light"     # 状态灯（健康四灯）
    LIST = "list"                     # 列表（风险笔记/证据）


# ============================================================
# 1. DataLayer —— 原始数据获取抽象
# ============================================================

@dataclass
class DataQuery:
    """数据查询请求。调用方构造，DataLayer 执行。"""
    source: str                          # 数据源标识：canonical_notes / evidence / events / health
    time_range: TimeRange = TimeRange.TODAY
    filters: Dict[str, Any] = field(default_factory=dict)  # 主体词/平台/风险等级等
    limit: Optional[int] = None
    offset: int = 0
    fields: Optional[List[str]] = None  # 所需字段，None=全部


@dataclass
class DataResult:
    """DataLayer 返回的原始数据包。"""
    query: DataQuery
    records: List[Dict[str, Any]] = field(default_factory=list)
    total: Optional[int] = None          # 符合条件的总数（不限于本页）；无数据时为 None（null），禁止用 0 填充
    status: DataStatus = DataStatus.OK
    error: Optional[str] = None
    source_timestamp: Optional[str] = None  # 数据生成/采集时间（ISO）
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_empty(self) -> bool:
        return self.status == DataStatus.NO_DATA or len(self.records) == 0


class DataLayer:
    """数据获取层抽象。

    实际取数由调用方注入 fetch_fn，本层只负责：
      - 统一查询/返回结构
      - 空集/错误的显式表达
      - 不做任何业务计算（那是 FunctionLayer / MetricLayer 的职责）
    """

    def __init__(self, fetch_fn: Optional[Callable[[DataQuery], DataResult]] = None):
        self._fetch_fn = fetch_fn

    def fetch(self, query: DataQuery) -> DataResult:
        if self._fetch_fn is None:
            return DataResult(
                query=query, status=DataStatus.UNAVAILABLE,
                error="DataLayer.fetch_fn not configured",
            )
        try:
            result = self._fetch_fn(query)
            if not isinstance(result, DataResult):
                return DataResult(query=query, status=DataStatus.ERROR,
                                  error="fetch_fn returned non-DataResult: %s" % type(result).__name__)
            return result
        except Exception as exc:  # noqa: BLE001 — 取数异常必须显式捕获，不向上抛
            return DataResult(query=query, status=DataStatus.ERROR, error=str(exc))


# ============================================================
# 2. FunctionLayer —— 业务函数层（主体过滤/风险判断/去重）
# ============================================================

@dataclass
class FunctionResult:
    """FunctionLayer 处理结果。"""
    records: List[Dict[str, Any]]
    applied: List[str] = field(default_factory=list)  # 已应用的函数名
    removed: int = 0                                   # 被过滤掉的条数
    notes: Dict[str, Any] = field(default_factory=dict)


class FunctionLayer:
    """业务函数层。

    职责：在原始数据上执行业务规则（主体过滤、风险判断、去重等）。
    主体过滤函数由调用方注入（不硬编码 SUBJECT_WORDS，红线不并入本模块）。
    """

    def __init__(self):
        self._functions: Dict[str, Callable[[List[Dict[str, Any]]], Tuple[List[Dict[str, Any]], int]]] = {}

    def register(self, name: str, fn: Callable[[List[Dict[str, Any]]], Tuple[List[Dict[str, Any]], int]]) -> None:
        """注册业务函数。fn 接收 records，返回 (filtered_records, removed_count)。"""
        self._functions[name] = fn

    def apply(self, records: List[Dict[str, Any]], function_names: Optional[Sequence[str]] = None) -> FunctionResult:
        """依次执行指定函数。function_names=None 时执行全部已注册函数。"""
        current = list(records)
        applied = []
        total_removed = 0
        names = list(function_names) if function_names else list(self._functions.keys())
        for name in names:
            fn = self._functions.get(name)
            if fn is None:
                continue
            try:
                current, removed = fn(current)
                applied.append(name)
                total_removed += removed
            except Exception as exc:  # noqa: BLE001
                return FunctionResult(records=records, applied=applied,
                                      removed=total_removed,
                                      notes={"error": "function %s failed: %s" % (name, exc)})
        return FunctionResult(records=current, applied=applied, removed=total_removed)


# ============================================================
# 3. MetricLayer —— 规范指标层（基于 canonical_metrics）
# ============================================================

@dataclass
class MetricValue:
    """单个指标的计算结果。"""
    name: str
    value: Optional[float]
    unit: str = ""
    label: str = ""
    breakdown: Dict[str, Any] = field(default_factory=dict)  # 如 sentiment={positive,neutral,negative}
    status: Optional[str] = None  # JSON-safe for retained consumers of __dict__.
    reason: Optional[str] = None

    @property
    def is_known(self) -> bool:
        return self.value is not None


class MetricLayer:
    """指标计算层。

    优先委托 canonical_metrics 模块（唯一业务计算真相）。
    若 canonical_metrics 不可用，提供最小内置兜底计算，但标记 source='fallback'。
    """

    def __init__(self):
        self._canonical = None
        try:
            import canonical_metrics as cm  # type: ignore
            self._canonical = cm
        except ImportError:
            self._canonical = None

    @property
    def canonical_available(self) -> bool:
        return self._canonical is not None

    def sentiment(self, records: List[Dict[str, Any]], key: str = "sentiment") -> MetricValue:
        """情感分布。返回 total，breakdown 含 positive/neutral/negative/unknown。"""
        if self._canonical and hasattr(self._canonical, "sentiment_count"):
            raw = self._canonical.sentiment_count(records, key=key)
            return MetricValue(
                name="sentiment", value=raw.get("total"),
                label="情感分布", breakdown={k: raw.get(k, 0) for k in ("positive", "neutral", "negative", "unknown")},
            )
        # fallback
        pos = neu = neg = unk = 0
        for r in records:
            v = r.get(key) if isinstance(r, dict) else None
            if v == "positive": pos += 1
            elif v == "neutral": neu += 1
            elif v == "negative": neg += 1
            else: unk += 1
        return MetricValue(name="sentiment", value=len(records), label="情感分布",
                           breakdown={"positive": pos, "neutral": neu, "negative": neg, "unknown": unk})

    def risk_distribution(self, records: List[Dict[str, Any]], key: str = "risk_level") -> MetricValue:
        """风险等级分布。"""
        if self._canonical and hasattr(self._canonical, "risk_count"):
            raw = self._canonical.risk_count(records, key=key)
            return MetricValue(name="risk", value=raw.get("total"), label="风险分布",
                               breakdown={k: raw.get(k, 0) for k in ("high", "medium", "low", "critical", "unknown")})
        high = med = low = crit = unk = 0
        for r in records:
            v = r.get(key) if isinstance(r, dict) else None
            if v == "high": high += 1
            elif v == "medium": med += 1
            elif v == "low": low += 1
            elif v == "critical": crit += 1
            else: unk += 1
        return MetricValue(name="risk", value=len(records), label="风险分布",
                           breakdown={"high": high, "medium": med, "low": low, "critical": crit, "unknown": unk})

    def engagement_total(self, records: List[Dict[str, Any]]) -> MetricValue:
        """Complete total plus explicitly covered measured subsets from the metric owner."""
        if not self._canonical or not hasattr(self._canonical, "engagement_stats"):
            return MetricValue(name="engagement", value=None, label="互动总量",
                               status=DataStatus.UNAVAILABLE.value, reason="CANONICAL_METRICS_UNAVAILABLE")
        raw = self._canonical.engagement_stats(records)
        quality = raw.get("quality", {})
        if quality.get("version") != "2.0":
            return MetricValue(name="engagement", value=None, label="互动总量",
                               status=DataStatus.UNAVAILABLE.value, reason="ENGAGEMENT_CONTRACT_VERSION_MISMATCH")
        status = {"UNKNOWN": DataStatus.UNAVAILABLE.value, "PARTIAL": DataStatus.PARTIAL.value,
                  "NO_DATA": DataStatus.NO_DATA.value}.get(quality["state"])
        return MetricValue(
            name="engagement", value=raw["sum"], label="互动总量", status=status,
            reason=quality["reason"], breakdown={
                **raw["per_field"], "observed_sum": raw["observed_sum"],
                "observed_per_field": raw["observed_per_field"], "coverage": quality,
            },
        )

    def count(self, records: List[Dict[str, Any]], name: str = "total", label: str = "总数") -> MetricValue:
        """通用计数。"""
        return MetricValue(name=name, value=len(records), label=label)

    def compute_all(self, records: List[Dict[str, Any]]) -> Dict[str, MetricValue]:
        """一键计算核心指标集。"""
        return {
            "total": self.count(records),
            "sentiment": self.sentiment(records),
            "risk": self.risk_distribution(records),
            "engagement": self.engagement_total(records),
        }


# ============================================================
# 4. TruthTable —— 真值表（数据存在性/新鲜度/置信度）
# ============================================================

@dataclass
class TruthTable:
    """数据真值表。每个 ViewModel 必须携带一个 TruthTable。

    回答三个问题：
      1. 数据存在吗？（exists）
      2. 数据新鲜吗？（fresh / staleness_seconds）
      3. 数据可信吗？（confidence）
    """
    exists: bool = False
    status: DataStatus = DataStatus.NO_DATA
    record_count: int = 0
    source_timestamp: Optional[str] = None   # 数据采集/生成时间
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    staleness_seconds: Optional[float] = None  # 距 source_timestamp 的秒数
    freshness_threshold_seconds: int = 3600     # 默认 1 小时为新鲜
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    confidence_reasons: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def fresh(self) -> bool:
        if self.staleness_seconds is None:
            return False
        return self.staleness_seconds <= self.freshness_threshold_seconds

    @property
    def is_truthful(self) -> bool:
        """数据可用于展示：存在 + 非错误状态。"""
        return self.exists and self.status not in (DataStatus.ERROR, DataStatus.UNAVAILABLE)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exists": self.exists,
            "status": self.status.value,
            "record_count": self.record_count,
            "source_timestamp": self.source_timestamp,
            "checked_at": self.checked_at,
            "staleness_seconds": self.staleness_seconds,
            "fresh": self.fresh,
            "confidence": self.confidence.value,
            "confidence_reasons": self.confidence_reasons,
            "sources": self.sources,
            "error": self.error,
        }


def build_truth_table(
    data_result: DataResult,
    freshness_threshold_seconds: int = 3600,
    min_records_for_high_confidence: int = 50,
) -> TruthTable:
    """从 DataResult 构造 TruthTable。

    置信度规则：
      - HIGH: 记录数 ≥ min_records + 新鲜 + 状态 OK
      - MEDIUM: 记录数 ≥ 10 或 (新鲜但记录数少) 或 (记录多但略陈旧)
      - LOW: 记录数 < 10 或 数据陈旧
      - UNKNOWN: 无数据/错误
    """
    tt = TruthTable(
        freshness_threshold_seconds=freshness_threshold_seconds,
        sources=[data_result.query.source] if data_result.query.source else [],
    )

    if data_result.status in (DataStatus.ERROR, DataStatus.UNAVAILABLE):
        tt.status = data_result.status
        tt.error = data_result.error
        tt.confidence = ConfidenceLevel.UNKNOWN
        tt.confidence_reasons.append("data source error/unavailable")
        return tt

    tt.record_count = data_result.total if data_result.total is not None else len(data_result.records)
    tt.exists = (data_result.total or 0) > 0 or len(data_result.records) > 0
    tt.status = data_result.status if data_result.status != DataStatus.OK else DataStatus.OK
    tt.source_timestamp = data_result.source_timestamp

    # 计算陈旧度
    if data_result.source_timestamp:
        try:
            ts = datetime.fromisoformat(data_result.source_timestamp.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            tt.staleness_seconds = (datetime.now(timezone.utc) - ts).total_seconds()
        except (ValueError, TypeError):
            tt.staleness_seconds = None
    else:
        tt.staleness_seconds = None

    # 置信度评定
    reasons = []
    n = tt.record_count
    if n == 0:
        tt.status = DataStatus.NO_DATA
        tt.confidence = ConfidenceLevel.UNKNOWN
        reasons.append("no records in time range")
    else:
        if n >= min_records_for_high_confidence:
            reasons.append("sufficient sample size (%d)" % n)
        elif n >= 10:
            reasons.append("moderate sample size (%d)" % n)
        else:
            reasons.append("small sample size (%d)" % n)

        if tt.fresh:
            reasons.append("data fresh")
        elif tt.staleness_seconds is not None:
            reasons.append("data stale (%.0fs old)" % tt.staleness_seconds)

        if tt.status == DataStatus.PARTIAL:
            reasons.append("partial data")

        # 综合评定
        if n >= min_records_for_high_confidence and tt.fresh and tt.status == DataStatus.OK:
            tt.confidence = ConfidenceLevel.HIGH
        elif n >= 10 and (tt.fresh or tt.status == DataStatus.OK):
            tt.confidence = ConfidenceLevel.MEDIUM
        else:
            tt.confidence = ConfidenceLevel.LOW

    tt.confidence_reasons = reasons
    return tt


# ============================================================
# 5. ViewModel —— 视图模型（五要素 + 时间范围）
# ============================================================

@dataclass
class Delta:
    """环比/同比变化量。"""
    value: Optional[float] = None       # 绝对变化量
    percent: Optional[float] = None     # 百分比变化（0-100，可负）
    direction: str = "flat"             # up / down / flat
    comparison_range: Optional[str] = None  # 对比基准描述，如 "previous_period"

    @property
    def is_known(self) -> bool:
        return self.value is not None or self.percent is not None


@dataclass
class EvidenceRef:
    """证据下钻引用。"""
    evidence_id: str
    evidence_type: str = "note"         # note / comment / event / report / ai_trace
    title: str = ""
    url: str = ""
    source: str = ""
    timestamp: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ViewMetric:
    """单个视图指标——UI 渲染的最小单元。

    五要素强制：current_value / delta / freshness / confidence / evidence_refs
    """
    key: str
    label: str
    current_value: Optional[float] = None
    unit: str = ""
    delta: Delta = field(default_factory=Delta)
    freshness: str = ""                  # 人类可读，如 "5 分钟前" / "STALE"
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    breakdown: Dict[str, Any] = field(default_factory=dict)
    chart_type: ChartType = ChartType.METRIC_CARD
    status: DataStatus = DataStatus.NO_DATA
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "current_value": self.current_value,
            "unit": self.unit,
            "delta": {
                "value": self.delta.value,
                "percent": self.delta.percent,
                "direction": self.delta.direction,
            },
            "freshness": self.freshness,
            "confidence": self.confidence.value,
            "evidence_count": len(self.evidence_refs),
            "evidence_refs": [e.__dict__ for e in self.evidence_refs[:5]],  # 最多返回 5 条
            "breakdown": self.breakdown,
            "chart_type": self.chart_type.value,
            "status": self.status.value,
            "reason": self.reason,
        }


@dataclass
class ViewModel:
    """页面级视图模型。

    包含：时间范围、真值表、指标集、可视化配置、下钻入口。
    """
    view_id: str                          # 页面标识，如 "production_overview"
    title: str
    time_range: TimeRange = TimeRange.TODAY
    truth: TruthTable = field(default_factory=TruthTable)
    metrics: Dict[str, ViewMetric] = field(default_factory=dict)
    visualizations: List["VisualizationConfig"] = field(default_factory=list)
    drilldowns: Dict[str, str] = field(default_factory=dict)  # key→endpoint/url
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def get_metric(self, key: str) -> Optional[ViewMetric]:
        return self.metrics.get(key)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "view_id": self.view_id,
            "title": self.title,
            "time_range": self.time_range.value,
            "truth": self.truth.to_dict(),
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "visualizations": [v.to_dict() for v in self.visualizations],
            "drilldowns": self.drilldowns,
            "generated_at": self.generated_at,
        }


# ============================================================
# 6. Visualization —— 可视化配置
# ============================================================

@dataclass
class VisualizationConfig:
    """可视化组件配置。UI 渲染层据此选择图表类型、颜色、布局。"""
    viz_id: str
    chart_type: ChartType
    title: str
    metric_keys: List[str] = field(default_factory=list)  # 关联的 ViewMetric key
    colors: Dict[str, str] = field(default_factory=dict)  # 系列→颜色
    layout: Dict[str, Any] = field(default_factory=dict)  # 网格位置/尺寸
    options: Dict[str, Any] = field(default_factory=dict)  # 图表特定选项
    drilldown_key: Optional[str] = None                     # 点击下钻关联

    def to_dict(self) -> Dict[str, Any]:
        return {
            "viz_id": self.viz_id,
            "chart_type": self.chart_type.value,
            "title": self.title,
            "metric_keys": self.metric_keys,
            "colors": self.colors,
            "layout": self.layout,
            "options": self.options,
            "drilldown_key": self.drilldown_key,
        }


# ZBC 自有视觉系统色板（不套模板）
ZBC_COLORS: Dict[str, str] = {
    "positive": "#22c55e",
    "neutral": "#94a3b8",
    "negative": "#ef4444",
    "risk_high": "#ef4444",
    "risk_medium": "#f59e0b",
    "risk_low": "#3b82f6",
    "risk_critical": "#7c3aed",
    "accent": "#6366f1",
    "background": "#0f172a",
    "surface": "#1e293b",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "border": "#334155",
}


def default_visualization_for_metric(metric_key: str, label: str) -> VisualizationConfig:
    """根据指标 key 推断默认可视化配置。"""
    chart_map = {
        "total": ChartType.METRIC_CARD,
        "sentiment": ChartType.DONUT,
        "risk": ChartType.STACKED_BAR,
        "engagement": ChartType.METRIC_CARD,
        "trend": ChartType.LINE,
        "events": ChartType.TIMELINE,
        "health": ChartType.STATUS_LIGHT,
        "notes": ChartType.LIST,
        "evidence": ChartType.TIMELINE,
    }
    ct = chart_map.get(metric_key, ChartType.METRIC_CARD)
    colors = {}
    if metric_key == "sentiment":
        colors = {"positive": ZBC_COLORS["positive"], "neutral": ZBC_COLORS["neutral"], "negative": ZBC_COLORS["negative"]}
    elif metric_key == "risk":
        colors = {"high": ZBC_COLORS["risk_high"], "medium": ZBC_COLORS["risk_medium"],
                  "low": ZBC_COLORS["risk_low"], "critical": ZBC_COLORS["risk_critical"]}
    return VisualizationConfig(
        viz_id="viz_%s" % metric_key,
        chart_type=ct, title=label,
        metric_keys=[metric_key], colors=colors,
    )


# ============================================================
# 7. ViewModelBuilder —— 端到端构建器
# ============================================================

class ViewModelBuilder:
    """从 DataResult 到 ViewModel 的端到端构建器。

    用法：
        builder = ViewModelBuilder(data_layer, function_layer, metric_layer)
        vm = builder.build("production_overview", "生产总览", query)
    """

    def __init__(
        self,
        data_layer: Optional[DataLayer] = None,
        function_layer: Optional[FunctionLayer] = None,
        metric_layer: Optional[MetricLayer] = None,
        freshness_threshold_seconds: int = 3600,
    ):
        self.data_layer = data_layer or DataLayer()
        self.function_layer = function_layer or FunctionLayer()
        self.metric_layer = metric_layer or MetricLayer()
        self.freshness_threshold = freshness_threshold_seconds

    def build(
        self,
        view_id: str,
        title: str,
        query: DataQuery,
        function_names: Optional[Sequence[str]] = None,
        previous_records: Optional[List[Dict[str, Any]]] = None,
    ) -> ViewModel:
        """构建完整 ViewModel。

        Args:
            view_id: 页面标识
            title: 页面标题
            query: 数据查询
            function_names: 要应用的业务函数名列表
            previous_records: 上一周期记录（用于 Delta 计算），None 则不计算 Delta
        """
        # Step 1: DataLayer
        data_result = self.data_layer.fetch(query)

        # Step 2: FunctionLayer
        func_result = self.function_layer.apply(data_result.records, function_names)

        # Step 3: MetricLayer
        metric_values = self.metric_layer.compute_all(func_result.records)

        # Step 4: TruthTable
        truth = build_truth_table(data_result, self.freshness_threshold)

        # Step 5: ViewModel + ViewMetrics
        vm = ViewModel(view_id=view_id, title=title, time_range=query.time_range, truth=truth)

        for mkey, mval in metric_values.items():
            delta = self._compute_delta(mval, previous_records, mkey) if previous_records is not None else Delta()
            vm.metrics[mkey] = ViewMetric(
                key=mkey,
                label=mval.label,
                current_value=mval.value,
                unit=mval.unit,
                delta=delta,
                freshness=self._format_freshness(truth),
                confidence=truth.confidence,
                evidence_refs=self._extract_evidence(func_result.records[:5]),
                breakdown=mval.breakdown,
                chart_type=default_visualization_for_metric(mkey, mval.label).chart_type,
                status=(truth.status if truth.status in (DataStatus.ERROR, DataStatus.UNAVAILABLE)
                        else DataStatus(mval.status) if mval.status else truth.status),
                reason=mval.reason,
            )
            # Step 6: Visualization
            vm.visualizations.append(default_visualization_for_metric(mkey, mval.label))

        # Drill-down 入口
        vm.drilldowns = {
            "event": "/api/events?range=%s" % query.time_range.value,
            "evidence": "/api/evidence/list?range=%s" % query.time_range.value,
            "case": "/api/cases?range=%s" % query.time_range.value,
        }
        return vm

    def _compute_delta(self, current_metric: MetricValue, previous_records: List[Dict[str, Any]], metric_key: str) -> Delta:
        """计算与上一周期的 Delta。"""
        prev_metrics = self.metric_layer.compute_all(previous_records)
        prev = prev_metrics.get(metric_key)
        if prev is None or prev.value is None or current_metric.value is None:
            return Delta()
        diff = current_metric.value - prev.value
        pct = (diff / prev.value * 100) if prev.value != 0 else None
        direction = "up" if diff > 0 else ("down" if diff < 0 else "flat")
        return Delta(value=diff, percent=pct, direction=direction, comparison_range="previous_period")

    def _format_freshness(self, truth: TruthTable) -> str:
        if truth.staleness_seconds is None:
            return "未知"
        secs = int(truth.staleness_seconds)
        if secs < 60:
            return "%d 秒前" % secs
        if secs < 3600:
            return "%d 分钟前" % (secs // 60)
        if secs < 86400:
            return "%d 小时前" % (secs // 3600)
        return "%d 天前" % (secs // 86400)

    def _extract_evidence(self, records: List[Dict[str, Any]]) -> List[EvidenceRef]:
        refs = []
        for r in records:
            if not isinstance(r, dict):
                continue
            eid = str(r.get("id") or r.get("note_id") or r.get("evidence_id") or "")
            if not eid:
                continue
            refs.append(EvidenceRef(
                evidence_id=eid,
                evidence_type=r.get("type", "note"),
                title=str(r.get("title") or r.get("content") or "")[:80],
                url=str(r.get("url") or r.get("note_url") or ""),
                source=str(r.get("platform") or r.get("source") or ""),
                timestamp=r.get("publish_datetime") or r.get("collected_at"),
            ))
        return refs


# ============================================================
# 8. 时间范围工具函数
# ============================================================

def compute_time_bounds(time_range: TimeRange, now: Optional[datetime] = None) -> Tuple[Optional[datetime], datetime]:
    """计算时间范围的 (start, end) 边界。end 始终为 now。

    Returns:
        (start, end)；NOW 返回 (None, now)（表示取最新快照）；HISTORICAL 返回 (None, now)。
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if time_range in (TimeRange.NOW, TimeRange.HISTORICAL):
        return None, now

    if time_range == TimeRange.TODAY:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now

    if time_range == TimeRange.YTD:
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, now

    seconds = time_range.to_seconds()
    if seconds is not None:
        return now - timedelta(seconds=seconds), now

    return None, now


def filter_records_by_time(
    records: List[Dict[str, Any]],
    time_range: TimeRange,
    time_field: str = "publish_datetime",
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """按时间范围过滤记录。NOW 不过滤（取全部）。"""
    if time_range in (TimeRange.NOW, TimeRange.HISTORICAL):
        return list(records)
    start, end = compute_time_bounds(time_range, now)
    if start is None:
        return list(records)
    result = []
    for r in records:
        if not isinstance(r, dict):
            continue
        ts_str = r.get(time_field) or r.get("collected_at")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        if start <= ts <= end:
            result.append(r)
    return result


# ============================================================
# 9. 模块公开 API
# ============================================================

__all__ = [
    # enums
    "TimeRange", "DataStatus", "ConfidenceLevel", "ChartType",
    # data layer
    "DataQuery", "DataResult", "DataLayer",
    # function layer
    "FunctionResult", "FunctionLayer",
    # metric layer
    "MetricValue", "MetricLayer",
    # truth table
    "TruthTable", "build_truth_table",
    # view model
    "Delta", "EvidenceRef", "ViewMetric", "ViewModel",
    # visualization
    "VisualizationConfig", "ZBC_COLORS", "default_visualization_for_metric",
    # builder
    "ViewModelBuilder",
    # utils
    "compute_time_bounds", "filter_records_by_time",
]
