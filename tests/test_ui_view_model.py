# -*- coding: utf-8 -*-
"""UI View Model 测试 —— ZBC Phase 14 数据链规范验证。

覆盖：
  - TimeRange 枚举与解析
  - DataLayer 取数（含空集/错误显式表达）
  - FunctionLayer 业务函数（主体过滤注入式）
  - MetricLayer 指标计算（sentiment/risk/engagement/count）
  - TruthTable 真值表（存在性/新鲜度/置信度）
  - Delta 计算（环比变化量/百分比/方向）
  - Evidence Drill-down（证据引用提取）
  - ViewModelBuilder 端到端构建
  - 时间范围过滤
"""
import sys
import os
from datetime import datetime, timedelta, timezone

import pytest

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui_view_model import (
    TimeRange, DataStatus, ConfidenceLevel, ChartType,
    DataQuery, DataResult, DataLayer,
    FunctionResult, FunctionLayer,
    MetricValue, MetricLayer,
    TruthTable, build_truth_table,
    Delta, EvidenceRef, ViewMetric, ViewModel,
    VisualizationConfig, ZBC_COLORS, default_visualization_for_metric,
    ViewModelBuilder,
    compute_time_bounds, filter_records_by_time,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def sample_notes():
    """示例笔记数据（10 条，覆盖各种情感/风险/互动）。"""
    now = datetime.now(timezone.utc)
    return [
        {"id": "n001", "title": "太古汇探店", "sentiment": "positive", "risk_level": "low",
         "likes": 100, "comments": 20, "collects": 15, "shares": 5,
         "publish_datetime": now.isoformat(), "platform": "xiaohongshu", "url": "https://x.com/n001"},
        {"id": "n002", "title": "服务态度差", "sentiment": "negative", "risk_level": "high",
         "likes": 10, "comments": 50, "collects": 2, "shares": 8,
         "publish_datetime": (now - timedelta(hours=2)).isoformat(), "platform": "xiaohongshu", "url": "https://x.com/n002"},
        {"id": "n003", "title": "环境不错", "sentiment": "positive", "risk_level": "low",
         "likes": 50, "comments": 10, "collects": 5, "shares": 1,
         "publish_datetime": (now - timedelta(hours=5)).isoformat(), "platform": "xiaohongshu", "url": "https://x.com/n003"},
        {"id": "n004", "title": "排队太久", "sentiment": "neutral", "risk_level": "medium",
         "likes": 30, "comments": 15, "collects": 3, "shares": 2,
         "publish_datetime": (now - timedelta(days=1)).isoformat(), "platform": "xiaohongshu", "url": "https://x.com/n004"},
        {"id": "n005", "title": "品牌活动精彩", "sentiment": "positive", "risk_level": "low",
         "likes": 200, "comments": 40, "collects": 30, "shares": 10,
         "publish_datetime": (now - timedelta(days=2)).isoformat(), "platform": "xiaohongshu", "url": "https://x.com/n005"},
        {"id": "n006", "title": "价格偏高", "sentiment": "negative", "risk_level": "medium",
         "likes": 5, "comments": 30, "collects": 1, "shares": 3,
         "publish_datetime": (now - timedelta(days=3)).isoformat(), "platform": "xiaohongshu", "url": "https://x.com/n006"},
        {"id": "n007", "title": "停车方便", "sentiment": "positive", "risk_level": "low",
         "likes": 80, "comments": 12, "collects": 8, "shares": 4,
         "publish_datetime": (now - timedelta(days=5)).isoformat(), "platform": "xiaohongshu", "url": "https://x.com/n007"},
        {"id": "n008", "title": "普通逛一下", "sentiment": "neutral", "risk_level": "low",
         "likes": 20, "comments": 5, "collects": 2, "shares": 0,
         "publish_datetime": (now - timedelta(days=8)).isoformat(), "platform": "xiaohongshu", "url": "https://x.com/n008"},
        {"id": "n009", "title": "严重安全隐患", "sentiment": "negative", "risk_level": "critical",
         "likes": 2, "comments": 100, "collects": 0, "shares": 20,
         "publish_datetime": (now - timedelta(days=10)).isoformat(), "platform": "xiaohongshu", "url": "https://x.com/n009"},
        {"id": "n010", "title": "美食推荐", "sentiment": "positive", "risk_level": "low",
         "likes": 150, "comments": 25, "collects": 20, "shares": 6,
         "publish_datetime": (now - timedelta(days=15)).isoformat(), "platform": "xiaohongshu", "url": "https://x.com/n010"},
    ]


@pytest.fixture
def previous_period_notes():
    """上一周期数据（用于 Delta 计算，5 条）。"""
    return [
        {"id": "p001", "sentiment": "positive", "risk_level": "low", "likes": 50, "comments": 10, "collects": 5, "shares": 2},
        {"id": "p002", "sentiment": "negative", "risk_level": "high", "likes": 5, "comments": 20, "collects": 1, "shares": 3},
        {"id": "p003", "sentiment": "neutral", "risk_level": "medium", "likes": 20, "comments": 8, "collects": 2, "shares": 1},
        {"id": "p004", "sentiment": "positive", "risk_level": "low", "likes": 80, "comments": 15, "collects": 10, "shares": 3},
        {"id": "p005", "sentiment": "negative", "risk_level": "low", "likes": 10, "comments": 5, "collects": 1, "shares": 0},
    ]


@pytest.fixture
def subject_filter_fn():
    """注入式主体过滤函数（模拟 subject_hit，不硬编码词表）。"""
    subject_keywords = ["太古汇", "taikoo"]
    def _filter(records):
        kept = []
        removed = 0
        for r in records:
            title = str(r.get("title", "")).lower()
            if any(kw.lower() in title for kw in subject_keywords):
                kept.append(r)
            else:
                removed += 1
        return kept, removed
    return _filter


# ============================================================
# 1. TimeRange 测试
# ============================================================

class TestTimeRange:
    def test_enum_values(self):
        assert TimeRange.NOW.value == "now"
        assert TimeRange.TODAY.value == "today"
        assert TimeRange.D7.value == "7d"
        assert TimeRange.D30.value == "30d"
        assert TimeRange.D90.value == "90d"
        assert TimeRange.YTD.value == "ytd"
        assert TimeRange.HISTORICAL.value == "historical"

    def test_from_str_standard(self):
        assert TimeRange.from_str("now") == TimeRange.NOW
        assert TimeRange.from_str("today") == TimeRange.TODAY
        assert TimeRange.from_str("7d") == TimeRange.D7
        assert TimeRange.from_str("30d") == TimeRange.D30
        assert TimeRange.from_str("90d") == TimeRange.D90
        assert TimeRange.from_str("ytd") == TimeRange.YTD
        assert TimeRange.from_str("historical") == TimeRange.HISTORICAL

    def test_from_str_alias(self):
        assert TimeRange.from_str("7天") == TimeRange.D7
        assert TimeRange.from_str("30天") == TimeRange.D30
        assert TimeRange.from_str("实时") == TimeRange.NOW
        assert TimeRange.from_str("今日") == TimeRange.TODAY
        assert TimeRange.from_str("全量") == TimeRange.HISTORICAL
        assert TimeRange.from_str("年初至今") == TimeRange.YTD

    def test_from_str_case_insensitive(self):
        assert TimeRange.from_str("7D") == TimeRange.D7
        assert TimeRange.from_str("YTD") == TimeRange.YTD
        assert TimeRange.from_str("Now") == TimeRange.NOW

    def test_from_str_empty_defaults_today(self):
        assert TimeRange.from_str("") == TimeRange.TODAY
        assert TimeRange.from_str(None) == TimeRange.TODAY

    def test_from_str_unknown_defaults_today(self):
        assert TimeRange.from_str("unknown_range") == TimeRange.TODAY

    def test_to_seconds(self):
        assert TimeRange.D7.to_seconds() == 7 * 86400
        assert TimeRange.D30.to_seconds() == 30 * 86400
        assert TimeRange.D90.to_seconds() == 90 * 86400
        assert TimeRange.NOW.to_seconds() is None
        assert TimeRange.TODAY.to_seconds() is None
        assert TimeRange.YTD.to_seconds() is None
        assert TimeRange.HISTORICAL.to_seconds() is None


# ============================================================
# 2. DataLayer 测试
# ============================================================

class TestDataLayer:
    def test_fetch_with_fn(self, sample_notes):
        def mock_fetch(query):
            return DataResult(query=query, records=sample_notes, total=len(sample_notes), status=DataStatus.OK)
        layer = DataLayer(fetch_fn=mock_fetch)
        query = DataQuery(source="canonical_notes", time_range=TimeRange.D7)
        result = layer.fetch(query)
        assert result.status == DataStatus.OK
        assert result.total == 10
        assert len(result.records) == 10
        assert result.query.source == "canonical_notes"

    def test_fetch_no_fn_returns_unavailable(self):
        layer = DataLayer()
        query = DataQuery(source="test")
        result = layer.fetch(query)
        assert result.status == DataStatus.UNAVAILABLE
        assert "not configured" in result.error

    def test_fetch_exception_returns_error(self):
        def bad_fetch(query):
            raise RuntimeError("DB connection failed")
        layer = DataLayer(fetch_fn=bad_fetch)
        query = DataQuery(source="test")
        result = layer.fetch(query)
        assert result.status == DataStatus.ERROR
        assert "DB connection failed" in result.error

    def test_empty_result_is_empty(self):
        result = DataResult(query=DataQuery(source="test"), records=[], total=0, status=DataStatus.NO_DATA)
        assert result.is_empty is True

    def test_nonempty_result_not_empty(self, sample_notes):
        result = DataResult(query=DataQuery(source="test"), records=sample_notes, total=10, status=DataStatus.OK)
        assert result.is_empty is False


# ============================================================
# 3. FunctionLayer 测试
# ============================================================

class TestFunctionLayer:
    def test_register_and_apply(self, sample_notes, subject_filter_fn):
        layer = FunctionLayer()
        layer.register("subject_filter", subject_filter_fn)
        result = layer.apply(sample_notes)
        assert isinstance(result, FunctionResult)
        assert "subject_filter" in result.applied
        # 只有含"太古汇"的笔记保留（n001, n002 标题含太古汇/服务态度差不含... 实际只有 n001 含"太古汇"）
        assert result.removed > 0
        assert len(result.records) + result.removed == len(sample_notes)

    def test_apply_specific_functions(self, sample_notes, subject_filter_fn):
        layer = FunctionLayer()
        layer.register("subject_filter", subject_filter_fn)
        layer.register("no_op", lambda r: (r, 0))
        result = layer.apply(sample_notes, function_names=["no_op"])
        assert result.applied == ["no_op"]
        assert len(result.records) == len(sample_notes)
        assert result.removed == 0

    def test_apply_empty_records(self, subject_filter_fn):
        layer = FunctionLayer()
        layer.register("subject_filter", subject_filter_fn)
        result = layer.apply([])
        assert len(result.records) == 0
        assert result.removed == 0

    def test_function_exception_captured(self, sample_notes):
        def bad_fn(records):
            raise ValueError("filter error")
        layer = FunctionLayer()
        layer.register("bad", bad_fn)
        result = layer.apply(sample_notes)
        assert "error" in result.notes
        assert "filter error" in result.notes["error"]


# ============================================================
# 4. MetricLayer 测试
# ============================================================

class TestMetricLayer:
    def test_sentiment_count(self, sample_notes):
        layer = MetricLayer()
        mv = layer.sentiment(sample_notes)
        assert mv.name == "sentiment"
        assert mv.value == 10
        assert mv.breakdown["positive"] == 5  # n001,n003,n005,n007,n010
        assert mv.breakdown["negative"] == 3  # n002,n006,n009
        assert mv.breakdown["neutral"] == 2   # n004,n008
        assert mv.breakdown["unknown"] == 0

    def test_sentiment_empty(self):
        layer = MetricLayer()
        mv = layer.sentiment([])
        assert mv.value == 0
        assert mv.breakdown["positive"] == 0

    def test_sentiment_unknown_values(self):
        layer = MetricLayer()
        records = [{"sentiment": "happy"}, {"sentiment": None}, {"sentiment": ""}]
        mv = layer.sentiment(records)
        assert mv.breakdown["unknown"] == 3
        assert mv.breakdown["positive"] == 0

    def test_risk_distribution(self, sample_notes):
        layer = MetricLayer()
        mv = layer.risk_distribution(sample_notes)
        assert mv.name == "risk"
        assert mv.value == 10
        assert mv.breakdown["high"] == 1       # n002
        assert mv.breakdown["medium"] == 2     # n004,n006
        assert mv.breakdown["low"] == 6        # n001,n003,n005,n007,n008,n010
        assert mv.breakdown["critical"] == 1   # n009

    def test_risk_critical_not_merged_into_high(self):
        """方案甲：critical 是独立更高桶，绝不并入 high。"""
        layer = MetricLayer()
        records = [{"risk_level": "critical"}, {"risk_level": "high"}]
        mv = layer.risk_distribution(records)
        assert mv.breakdown["critical"] == 1
        assert mv.breakdown["high"] == 1

    def test_engagement_total(self, sample_notes):
        layer = MetricLayer()
        mv = layer.engagement_total(sample_notes)
        assert mv.name == "engagement"
        # 手动计算：likes=100+10+50+30+200+5+80+20+2+150=647
        # comments=20+50+10+15+40+30+12+5+100+25=307
        # collects=15+2+5+3+30+1+8+2+0+20=86
        # shares=5+8+1+2+10+3+4+0+20+6=59
        # total=647+307+86+59=1099
        assert mv.value == 1099
        assert mv.breakdown["likes"] == 647
        assert mv.breakdown["comments"] == 307

    def test_count(self, sample_notes):
        layer = MetricLayer()
        mv = layer.count(sample_notes, name="total", label="笔记总数")
        assert mv.value == 10
        assert mv.label == "笔记总数"

    def test_compute_all(self, sample_notes):
        layer = MetricLayer()
        all_metrics = layer.compute_all(sample_notes)
        assert "total" in all_metrics
        assert "sentiment" in all_metrics
        assert "risk" in all_metrics
        assert "engagement" in all_metrics
        assert all_metrics["total"].value == 10

    def test_metric_value_is_known(self):
        mv = MetricValue(name="test", value=42)
        assert mv.is_known is True
        mv_none = MetricValue(name="test", value=None)
        assert mv_none.is_known is False


# ============================================================
# 5. TruthTable 测试
# ============================================================

class TestTruthTable:
    def test_build_with_data(self, sample_notes):
        now = datetime.now(timezone.utc)
        query = DataQuery(source="canonical_notes", time_range=TimeRange.D7)
        data_result = DataResult(
            query=query, records=sample_notes, total=len(sample_notes),
            status=DataStatus.OK, source_timestamp=now.isoformat(),
        )
        tt = build_truth_table(data_result, freshness_threshold_seconds=3600)
        assert tt.exists is True
        assert tt.status == DataStatus.OK
        assert tt.record_count == 10
        assert tt.fresh is True  # 刚刚采集
        assert tt.sources == ["canonical_notes"]

    def test_build_empty_data(self):
        query = DataQuery(source="canonical_notes", time_range=TimeRange.D7)
        data_result = DataResult(query=query, records=[], total=0, status=DataStatus.NO_DATA)
        tt = build_truth_table(data_result)
        assert tt.exists is False
        assert tt.status == DataStatus.NO_DATA
        assert tt.confidence == ConfidenceLevel.UNKNOWN
        assert "no records" in tt.confidence_reasons[0]

    def test_build_error_data(self):
        query = DataQuery(source="canonical_notes", time_range=TimeRange.D7)
        data_result = DataResult(query=query, records=[], total=0, status=DataStatus.ERROR, error="DB fail")
        tt = build_truth_table(data_result)
        assert tt.status == DataStatus.ERROR
        assert tt.confidence == ConfidenceLevel.UNKNOWN
        assert tt.error == "DB fail"

    def test_stale_data(self, sample_notes):
        old = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        query = DataQuery(source="test", time_range=TimeRange.D7)
        data_result = DataResult(query=query, records=sample_notes, total=10,
                                  status=DataStatus.OK, source_timestamp=old)
        tt = build_truth_table(data_result, freshness_threshold_seconds=3600)
        assert tt.fresh is False
        assert tt.staleness_seconds > 3600

    def test_confidence_high(self, sample_notes):
        """≥50 条 + 新鲜 + OK → HIGH。"""
        many = sample_notes * 6  # 60 条
        now = datetime.now(timezone.utc)
        query = DataQuery(source="test", time_range=TimeRange.D7)
        data_result = DataResult(query=query, records=many, total=60,
                                  status=DataStatus.OK, source_timestamp=now.isoformat())
        tt = build_truth_table(data_result, min_records_for_high_confidence=50)
        assert tt.confidence == ConfidenceLevel.HIGH

    def test_confidence_low_small_sample(self):
        """<10 条 → LOW。"""
        few = [{"id": "1"}] * 3
        now = datetime.now(timezone.utc)
        query = DataQuery(source="test", time_range=TimeRange.D7)
        data_result = DataResult(query=query, records=few, total=3,
                                  status=DataStatus.OK, source_timestamp=now.isoformat())
        tt = build_truth_table(data_result)
        assert tt.confidence == ConfidenceLevel.LOW

    def test_truth_table_to_dict(self):
        tt = TruthTable(exists=True, status=DataStatus.OK, record_count=5)
        d = tt.to_dict()
        assert d["exists"] is True
        assert d["status"] == "ok"
        assert d["record_count"] == 5
        assert "confidence" in d

    def test_is_truthful(self):
        tt_ok = TruthTable(exists=True, status=DataStatus.OK)
        assert tt_ok.is_truthful is True
        tt_err = TruthTable(exists=True, status=DataStatus.ERROR)
        assert tt_err.is_truthful is False
        tt_no = TruthTable(exists=False, status=DataStatus.NO_DATA)
        assert tt_no.is_truthful is False


# ============================================================
# 6. Delta 测试
# ============================================================

class TestDelta:
    def test_delta_up(self):
        d = Delta(value=10, percent=25.0, direction="up")
        assert d.value == 10
        assert d.percent == 25.0
        assert d.direction == "up"
        assert d.is_known is True

    def test_delta_down(self):
        d = Delta(value=-5, percent=-12.5, direction="down")
        assert d.direction == "down"

    def test_delta_flat(self):
        d = Delta(value=0, percent=0, direction="flat")
        assert d.direction == "flat"

    def test_delta_unknown(self):
        d = Delta()
        assert d.is_known is False

    def test_view_model_builder_delta(self, sample_notes, previous_period_notes):
        """端到端 Delta 计算：当前 10 条 vs 上期 5 条 → total delta +5。"""
        def mock_fetch(query):
            return DataResult(query=query, records=sample_notes, total=len(sample_notes),
                              status=DataStatus.OK, source_timestamp=datetime.now(timezone.utc).isoformat())
        builder = ViewModelBuilder(data_layer=DataLayer(fetch_fn=mock_fetch))
        query = DataQuery(source="canonical_notes", time_range=TimeRange.D7)
        vm = builder.build("test_view", "测试", query, previous_records=previous_period_notes)
        total_metric = vm.get_metric("total")
        assert total_metric is not None
        assert total_metric.current_value == 10
        assert total_metric.delta.value == 5  # 10 - 5
        assert total_metric.delta.direction == "up"
        assert total_metric.delta.percent == 100.0  # 5/5*100

    def test_delta_no_previous_records(self, sample_notes):
        def mock_fetch(query):
            return DataResult(query=query, records=sample_notes, total=10, status=DataStatus.OK,
                              source_timestamp=datetime.now(timezone.utc).isoformat())
        builder = ViewModelBuilder(data_layer=DataLayer(fetch_fn=mock_fetch))
        query = DataQuery(source="test", time_range=TimeRange.D7)
        vm = builder.build("test", "测试", query)  # 无 previous_records
        total_metric = vm.get_metric("total")
        assert total_metric.delta.is_known is False


# ============================================================
# 7. Evidence Drill-down 测试
# ============================================================

class TestEvidenceDrilldown:
    def test_evidence_ref_creation(self):
        ref = EvidenceRef(
            evidence_id="n001", evidence_type="note",
            title="太古汇探店", url="https://x.com/n001",
            source="xiaohongshu", timestamp="2026-09-06T10:00:00",
        )
        assert ref.evidence_id == "n001"
        assert ref.evidence_type == "note"

    def test_builder_extracts_evidence(self, sample_notes):
        def mock_fetch(query):
            return DataResult(query=query, records=sample_notes, total=10, status=DataStatus.OK,
                              source_timestamp=datetime.now(timezone.utc).isoformat())
        builder = ViewModelBuilder(data_layer=DataLayer(fetch_fn=mock_fetch))
        query = DataQuery(source="canonical_notes", time_range=TimeRange.D7)
        vm = builder.build("test", "测试", query)
        total_metric = vm.get_metric("total")
        assert len(total_metric.evidence_refs) > 0
        # 第一条证据应来自 n001
        assert total_metric.evidence_refs[0].evidence_id == "n001"
        assert total_metric.evidence_refs[0].source == "xiaohongshu"

    def test_evidence_refs_limited_to_5(self, sample_notes):
        """to_dict 中 evidence_refs 最多返回 5 条。"""
        def mock_fetch(query):
            return DataResult(query=query, records=sample_notes, total=10, status=DataStatus.OK,
                              source_timestamp=datetime.now(timezone.utc).isoformat())
        builder = ViewModelBuilder(data_layer=DataLayer(fetch_fn=mock_fetch))
        query = DataQuery(source="test", time_range=TimeRange.D7)
        vm = builder.build("test", "测试", query)
        d = vm.to_dict()
        assert d["metrics"]["total"]["evidence_count"] == 5  # builder 只取前 5 条
        assert len(d["metrics"]["total"]["evidence_refs"]) <= 5

    def test_view_model_has_drilldowns(self, sample_notes):
        def mock_fetch(query):
            return DataResult(query=query, records=sample_notes, total=10, status=DataStatus.OK,
                              source_timestamp=datetime.now(timezone.utc).isoformat())
        builder = ViewModelBuilder(data_layer=DataLayer(fetch_fn=mock_fetch))
        query = DataQuery(source="test", time_range=TimeRange.D7)
        vm = builder.build("test", "测试", query)
        assert "event" in vm.drilldowns
        assert "evidence" in vm.drilldowns
        assert "case" in vm.drilldowns
        assert "7d" in vm.drilldowns["evidence"]


# ============================================================
# 8. ViewModel 与 ViewMetric 测试
# ============================================================

class TestViewModel:
    def test_view_metric_five_elements(self):
        """每个 ViewMetric 必须有五要素。"""
        vm = ViewMetric(
            key="total", label="笔记总数", current_value=42,
            delta=Delta(value=5, percent=13.5, direction="up"),
            freshness="5 分钟前", confidence=ConfidenceLevel.HIGH,
            evidence_refs=[EvidenceRef(evidence_id="e1")],
        )
        assert vm.current_value == 42
        assert vm.delta.value == 5
        assert vm.freshness == "5 分钟前"
        assert vm.confidence == ConfidenceLevel.HIGH
        assert len(vm.evidence_refs) == 1

    def test_view_metric_to_dict(self):
        vm = ViewMetric(key="total", label="总数", current_value=10, confidence=ConfidenceLevel.MEDIUM)
        d = vm.to_dict()
        assert d["key"] == "total"
        assert d["current_value"] == 10
        assert d["confidence"] == "medium"
        assert "delta" in d
        assert "freshness" in d
        assert "evidence_count" in d

    def test_view_model_to_dict(self, sample_notes):
        def mock_fetch(query):
            return DataResult(query=query, records=sample_notes, total=10, status=DataStatus.OK,
                              source_timestamp=datetime.now(timezone.utc).isoformat())
        builder = ViewModelBuilder(data_layer=DataLayer(fetch_fn=mock_fetch))
        query = DataQuery(source="test", time_range=TimeRange.D7)
        vm = builder.build("production_overview", "生产总览", query)
        d = vm.to_dict()
        assert d["view_id"] == "production_overview"
        assert d["title"] == "生产总览"
        assert d["time_range"] == "7d"
        assert "truth" in d
        assert "metrics" in d
        assert "visualizations" in d
        assert "drilldowns" in d

    def test_get_metric(self, sample_notes):
        def mock_fetch(query):
            return DataResult(query=query, records=sample_notes, total=10, status=DataStatus.OK,
                              source_timestamp=datetime.now(timezone.utc).isoformat())
        builder = ViewModelBuilder(data_layer=DataLayer(fetch_fn=mock_fetch))
        query = DataQuery(source="test", time_range=TimeRange.D7)
        vm = builder.build("test", "测试", query)
        assert vm.get_metric("total") is not None
        assert vm.get_metric("sentiment") is not None
        assert vm.get_metric("nonexistent") is None


# ============================================================
# 9. Visualization 测试
# ============================================================

class TestVisualization:
    def test_zbc_colors(self):
        assert ZBC_COLORS["positive"] == "#22c55e"
        assert ZBC_COLORS["negative"] == "#ef4444"
        assert ZBC_COLORS["risk_critical"] == "#7c3aed"
        assert ZBC_COLORS["accent"] == "#6366f1"

    def test_default_viz_for_sentiment(self):
        viz = default_visualization_for_metric("sentiment", "情感分布")
        assert viz.chart_type == ChartType.DONUT
        assert "positive" in viz.colors
        assert viz.colors["positive"] == "#22c55e"

    def test_default_viz_for_risk(self):
        viz = default_visualization_for_metric("risk", "风险分布")
        assert viz.chart_type == ChartType.STACKED_BAR
        assert "high" in viz.colors

    def test_default_viz_for_total(self):
        viz = default_visualization_for_metric("total", "总数")
        assert viz.chart_type == ChartType.METRIC_CARD

    def test_default_viz_for_trend(self):
        viz = default_visualization_for_metric("trend", "趋势")
        assert viz.chart_type == ChartType.LINE

    def test_viz_to_dict(self):
        viz = VisualizationConfig(viz_id="v1", chart_type=ChartType.LINE, title="测试")
        d = viz.to_dict()
        assert d["viz_id"] == "v1"
        assert d["chart_type"] == "line"


# ============================================================
# 10. 时间范围工具测试
# ============================================================

class TestTimeBounds:
    def test_compute_d7(self):
        now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
        start, end = compute_time_bounds(TimeRange.D7, now=now)
        assert end == now
        assert start == now - timedelta(days=7)

    def test_compute_today(self):
        now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
        start, end = compute_time_bounds(TimeRange.TODAY, now=now)
        assert start.hour == 0
        assert start.minute == 0
        assert start.day == 6

    def test_compute_ytd(self):
        now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
        start, end = compute_time_bounds(TimeRange.YTD, now=now)
        assert start.month == 1
        assert start.day == 1

    def test_compute_now_returns_none_start(self):
        start, end = compute_time_bounds(TimeRange.NOW)
        assert start is None

    def test_compute_historical_returns_none_start(self):
        start, end = compute_time_bounds(TimeRange.HISTORICAL)
        assert start is None

    def test_filter_records_d7(self, sample_notes):
        """D7 应只保留最近 7 天的笔记。"""
        filtered = filter_records_by_time(sample_notes, TimeRange.D7)
        # sample_notes 中 n008(8天前), n009(10天前), n010(15天前) 应被过滤
        assert len(filtered) == 7  # 10 - 3
        ids = [r["id"] for r in filtered]
        assert "n008" not in ids
        assert "n009" not in ids
        assert "n010" not in ids

    def test_filter_records_today(self, sample_notes):
        filtered = filter_records_by_time(sample_notes, TimeRange.TODAY)
        # n001(now), n002(2小时前), n003(5小时前) 都是今天的
        assert len(filtered) == 3
        ids = {r["id"] for r in filtered}
        assert ids == {"n001", "n002", "n003"}

    def test_filter_records_now_no_filter(self, sample_notes):
        """NOW 不过滤。"""
        filtered = filter_records_by_time(sample_notes, TimeRange.NOW)
        assert len(filtered) == len(sample_notes)

    def test_filter_records_historical_no_filter(self, sample_notes):
        filtered = filter_records_by_time(sample_notes, TimeRange.HISTORICAL)
        assert len(filtered) == len(sample_notes)

    def test_filter_records_d30(self, sample_notes):
        """D30 应保留全部（最远 15 天前）。"""
        filtered = filter_records_by_time(sample_notes, TimeRange.D30)
        assert len(filtered) == 10


# ============================================================
# 11. 端到端集成测试
# ============================================================

class TestEndToEnd:
    def test_full_pipeline(self, sample_notes, previous_period_notes, subject_filter_fn):
        """完整数据链：DataLayer → FunctionLayer → MetricLayer → TruthTable → ViewModel。"""
        def mock_fetch(query):
            return DataResult(query=query, records=sample_notes, total=len(sample_notes),
                              status=DataStatus.OK, source_timestamp=datetime.now(timezone.utc).isoformat())

        data_layer = DataLayer(fetch_fn=mock_fetch)
        function_layer = FunctionLayer()
        function_layer.register("subject_filter", subject_filter_fn)
        metric_layer = MetricLayer()

        builder = ViewModelBuilder(
            data_layer=data_layer, function_layer=function_layer, metric_layer=metric_layer,
        )
        query = DataQuery(source="canonical_notes", time_range=TimeRange.D7)
        vm = builder.build("production_overview", "生产总览", query,
                           function_names=["subject_filter"],
                           previous_records=previous_period_notes)

        # 验证 ViewModel 结构完整
        assert vm.view_id == "production_overview"
        assert vm.time_range == TimeRange.D7
        assert vm.truth.exists is True
        assert vm.truth.status == DataStatus.OK

        # 验证指标存在
        for key in ("total", "sentiment", "risk", "engagement"):
            metric = vm.get_metric(key)
            assert metric is not None, "missing metric: %s" % key
            # 五要素
            assert metric.current_value is not None or key != "total"
            assert metric.freshness != ""
            assert metric.confidence != ConfidenceLevel.UNKNOWN or metric.current_value in (0, None)

        # 验证可视化配置
        assert len(vm.visualizations) >= 4

        # 验证下钻入口
        assert "evidence" in vm.drilldowns

    def test_pipeline_with_error(self):
        """数据层错误时，ViewModel 仍能构建且 truth 显式表达错误。"""
        def bad_fetch(query):
            raise RuntimeError("DB down")
        builder = ViewModelBuilder(data_layer=DataLayer(fetch_fn=bad_fetch))
        query = DataQuery(source="test", time_range=TimeRange.TODAY)
        vm = builder.build("test", "测试", query)
        assert vm.truth.status == DataStatus.ERROR
        assert vm.truth.exists is False
        assert vm.truth.confidence == ConfidenceLevel.UNKNOWN

    def test_pipeline_empty_data(self):
        """空数据时，ViewModel 显式 NO_DATA，不伪装成 0。"""
        def empty_fetch(query):
            return DataResult(query=query, records=[], total=0, status=DataStatus.NO_DATA)
        builder = ViewModelBuilder(data_layer=DataLayer(fetch_fn=empty_fetch))
        query = DataQuery(source="test", time_range=TimeRange.TODAY)
        vm = builder.build("test", "测试", query)
        assert vm.truth.status == DataStatus.NO_DATA
        assert vm.truth.exists is False
        total = vm.get_metric("total")
        assert total.current_value == 0
        assert total.status == DataStatus.NO_DATA


# ============================================================
# 12. 数据状态枚举测试
# ============================================================

class TestEnums:
    def test_data_status_values(self):
        assert DataStatus.OK.value == "ok"
        assert DataStatus.STALE.value == "stale"
        assert DataStatus.NO_DATA.value == "no_data"
        assert DataStatus.ERROR.value == "error"
        assert DataStatus.PARTIAL.value == "partial"
        assert DataStatus.UNAVAILABLE.value == "unavailable"

    def test_confidence_levels(self):
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"
        assert ConfidenceLevel.UNKNOWN.value == "unknown"

    def test_chart_types(self):
        assert ChartType.METRIC_CARD.value == "metric_card"
        assert ChartType.LINE.value == "line"
        assert ChartType.BAR.value == "bar"
        assert ChartType.DONUT.value == "donut"
        assert ChartType.TABLE.value == "table"
        assert ChartType.TIMELINE.value == "timeline"
        assert ChartType.STATUS_LIGHT.value == "status_light"
        assert ChartType.LIST.value == "list"
