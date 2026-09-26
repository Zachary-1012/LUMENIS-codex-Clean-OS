# -*- coding: utf-8 -*-
"""投流策略与广告数据分析测试"""
import sys, os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestStrategyGenerator:

    def test_generate_xhs_strategy(self):
        from ad_intelligence.strategy.generator import StrategyGenerator
        gen = StrategyGenerator()
        s = gen.generate_strategy("xhs", "consideration", 10000)
        assert s.platform == "xhs"
        assert s.budget.total_budget == 10000
        assert s.requires_human_approval is True
        assert s.status == "draft"
        assert len(s.creative_directions) > 0

    def test_generate_douyin_strategy(self):
        from ad_intelligence.strategy.generator import StrategyGenerator
        gen = StrategyGenerator()
        s = gen.generate_strategy("douyin", "conversion", 20000)
        assert s.platform == "douyin"
        assert "短视频种草" in s.creative_directions

    def test_strategy_with_historical_data(self):
        from ad_intelligence.strategy.generator import StrategyGenerator
        gen = StrategyGenerator()
        s = gen.generate_strategy(
            "xhs", "conversion", 10000,
            historical_data={"avg_ctr": 0.05, "avg_cvr": 0.02, "avg_roas": 2.5}
        )
        assert s.expected_ctr == 0.05
        assert s.expected_roas == 2.5
        assert s.confidence > 0.5

    def test_compare_strategies(self):
        from ad_intelligence.strategy.generator import StrategyGenerator
        gen = StrategyGenerator()
        s1 = gen.generate_strategy("xhs", "conversion", 10000, historical_data={"avg_roas": 3.0})
        s2 = gen.generate_strategy("douyin", "conversion", 10000, historical_data={"avg_roas": 1.5})
        s1.confidence = 0.8
        s2.confidence = 0.8
        result = gen.compare_strategies([s1, s2])
        assert result["total_strategies"] == 2
        assert result["recommendation"]["platform"] == "xhs"

    def test_list_strategies(self):
        from ad_intelligence.strategy.generator import StrategyGenerator
        gen = StrategyGenerator()
        gen.generate_strategy("xhs", "conversion", 10000)
        gen.generate_strategy("douyin", "conversion", 20000)
        assert len(gen.list_strategies()) == 2
        assert len(gen.list_strategies(status="draft")) == 2

    def test_audience_target(self):
        from ad_intelligence.strategy.generator import StrategyGenerator
        gen = StrategyGenerator()
        s = gen.generate_strategy(
            "xhs", "conversion", 10000,
            target_audience={"age_range": (25, 35), "gender": "female", "regions": ["广州", "深圳"]}
        )
        assert s.audience.age_range == (25, 35)
        assert s.audience.gender == "female"
        assert "广州" in s.audience.regions


class TestAdAnalytics:

    def test_roas_analysis_good(self):
        from ad_intelligence.analytics.analyzer import AdAnalytics
        analyzer = AdAnalytics()
        spend = [{"spend": 1000, "revenue": 3000, "campaign": "A"}]
        revenue = [{"revenue": 3000}]
        result = analyzer.analyze_roas("xhs", spend, revenue, target_roas=2.0)
        assert result.roas == 3.0
        assert result.status == "good"

    def test_roas_analysis_bad(self):
        from ad_intelligence.analytics.analyzer import AdAnalytics
        analyzer = AdAnalytics()
        spend = [{"spend": 1000, "revenue": 500, "campaign": "A"}]
        revenue = [{"revenue": 500}]
        result = analyzer.analyze_roas("xhs", spend, revenue, target_roas=2.0)
        assert result.roas == 0.5
        assert result.status == "bad"

    def test_funnel_analysis(self):
        from ad_intelligence.analytics.analyzer import AdAnalytics
        analyzer = AdAnalytics()
        funnel = {
            "impressions": 10000,
            "clicks": 500,
            "landings": 400,
            "engagements": 100,
            "conversions": 20,
        }
        result = analyzer.analyze_funnel("xhs", funnel)
        assert result.stages["impression"] == 10000
        assert result.stages["conversion"] == 20
        assert "click_to_landing" in result.rates
        assert result.bottleneck

    def test_creative_analysis(self):
        from ad_intelligence.analytics.analyzer import AdAnalytics
        analyzer = AdAnalytics()
        creatives = [
            {"type": "video", "ctr": 0.05, "cvr": 0.02},
            {"type": "image", "ctr": 0.02, "cvr": 0.01},
            {"type": "video", "ctr": 0.08, "cvr": 0.03},
        ]
        result = analyzer.analyze_creatives("xhs", creatives)
        assert result.total_creatives == 3
        assert "video" in result.avg_ctr_by_type
        assert result.avg_ctr_by_type["video"] > result.avg_ctr_by_type["image"]

    def test_creative_analysis_empty(self):
        from ad_intelligence.analytics.analyzer import AdAnalytics
        analyzer = AdAnalytics()
        result = analyzer.analyze_creatives("xhs", [])
        assert result.total_creatives == 0
        assert result.recommendation == "无素材数据"

    def test_public_creatives_without_metrics_are_not_ranked(self):
        from ad_intelligence.analytics.analyzer import AdAnalytics

        creatives = [
            {"type": "video", "title": "Observed public creative"},
            {"type": "image", "ctr": None, "cvr": None},
            {"type": "video", "ctr": "unknown", "cvr": float("nan")},
        ]
        result = AdAnalytics().analyze_creatives("meta_library", creatives)
        assert result.total_creatives == 3
        assert result.best_performing == result.worst_performing == []
        assert result.avg_ctr_by_type == result.avg_cvr_by_type == {}
        assert result.recommendation == "未提供真实CTR，无法判断素材表现"

    def test_missing_metrics_do_not_dilute_observed_rates(self):
        from ad_intelligence.analytics.analyzer import AdAnalytics

        measured = {"type": "video", "ctr": 0.05, "cvr": 0.02}
        creatives = [measured, {"type": "video"}, {"type": "image", "ctr": 0.0}]
        result = AdAnalytics().analyze_creatives("authorized_account", creatives)
        assert result.best_performing[0] is measured
        assert result.avg_ctr_by_type == {"video": 0.05, "image": 0.0}
        assert result.avg_cvr_by_type == {"video": 0.02}
        assert "真实业务结果" in result.recommendation


class TestJiguangBrowserMode:

    def test_health_check_browser_mode(self):
        from ad_intelligence.platforms.jiguang import JiguangCollector, JiguangConfig
        c = JiguangCollector(JiguangConfig(cookie_path="data/cookies/jiguang.json"))
        h = c.health_check()
        assert h["collection_mode"] in ("browser_cookie", "unavailable")
        assert h["cookie_count"] >= 0
        assert "has_web_session" in h

    def test_calculate_actual_cost(self):
        from ad_intelligence.platforms.jiguang import JiguangCollector, JiguangConfig
        c = JiguangCollector(JiguangConfig(agency_rebate_rate=0.05))
        assert c.calculate_actual_cost(1000) == 950.0
