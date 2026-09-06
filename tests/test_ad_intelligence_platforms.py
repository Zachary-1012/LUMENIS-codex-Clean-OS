# -*- coding: utf-8 -*-
"""ad_intelligence 平台 API 单元测试

验证：
1. 平台注册机制正常
2. 无凭证时返回 BLOCKED 状态（禁止伪造成功/空数据）
3. 各平台 health_check 正确报告状态
4. API 请求骨架存在且可调用
5. 禁止返回空列表冒充成功
"""
import sys
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestPlatformRegistry:
    """平台注册机制测试。"""

    def test_factory_returns_collector_for_douyin(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        collector = AdCollectorFactory.get_collector("douyin")
        assert collector is not None
        assert collector.__class__.__name__ == "OceanEngineCollector"

    def test_factory_returns_collector_for_xhs(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        collector = AdCollectorFactory.get_collector("xhs")
        assert collector is not None
        assert collector.__class__.__name__ == "JiguangCollector"

    def test_factory_returns_collector_for_facebook(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        collector = AdCollectorFactory.get_collector("facebook")
        assert collector is not None
        assert collector.__class__.__name__ == "MetaAdsCollector"

    def test_factory_returns_collector_for_x(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        collector = AdCollectorFactory.get_collector("x")
        assert collector is not None
        assert collector.__class__.__name__ == "XAdsCollector"

    def test_factory_returns_none_for_unknown(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        collector = AdCollectorFactory.get_collector("unknown_platform_xyz")
        assert collector is None

    def test_factory_singleton(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        c1 = AdCollectorFactory.get_collector("douyin")
        c2 = AdCollectorFactory.get_collector("douyin")
        assert c1 is c2

    def test_health_check_all(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        results = AdCollectorFactory.health_check_all()
        assert "douyin" in results
        assert "xhs" in results
        assert "facebook" in results
        assert "x" in results


class TestJiguangBlocked:
    """聚光平台 BLOCKED 状态测试（无凭证时禁止伪造成功）。"""

    def test_no_credentials_returns_blocked_on_balance(self):
        from ad_intelligence.platforms.jiguang import JiguangCollector, JiguangConfig
        collector = JiguangCollector(JiguangConfig(use_browser_fallback=False))
        result = collector.get_balance()
        assert result["success"] is False
        assert result["status"] == "blocked"
        assert "missing" in result["reason"] or "no collection" in result["reason"]
        assert result["data"] is None

    def test_no_credentials_returns_blocked_on_daily_report(self):
        from ad_intelligence.platforms.jiguang import JiguangCollector, JiguangConfig
        collector = JiguangCollector(JiguangConfig(use_browser_fallback=False))
        result = collector.get_daily_report("2026-09-01", "2026-09-06")
        assert result["success"] is False
        assert result["status"] == "blocked"
        assert result["data"] is None

    def test_no_credentials_returns_blocked_on_campaign_list(self):
        from ad_intelligence.platforms.jiguang import JiguangCollector, JiguangConfig
        collector = JiguangCollector(JiguangConfig(use_browser_fallback=False))
        result = collector.get_campaign_list()
        assert result["success"] is False
        assert result["status"] == "blocked"
        assert result["data"] is None

    def test_health_check_reports_blocked(self):
        from ad_intelligence.platforms.jiguang import JiguangCollector, JiguangConfig
        collector = JiguangCollector(JiguangConfig(use_browser_fallback=False))
        health = collector.health_check()
        assert health["platform"] == "xhs"
        assert health["collection_mode"] == "unavailable"
        assert health["status"] == "blocked"

    def test_api_request_without_credentials_blocked(self):
        from ad_intelligence.platforms.jiguang import JiguangCollector, JiguangConfig
        collector = JiguangCollector(JiguangConfig())
        result = collector._api_request("GET", "/api/jg/account/info")
        assert result["success"] is False
        assert result["status"] == "blocked"
        assert "missing credentials" in result["reason"]

    def test_required_credentials_listed(self):
        from ad_intelligence.platforms.jiguang import JiguangCollector, JiguangConfig
        collector = JiguangCollector(JiguangConfig(use_browser_fallback=False))
        result = collector.get_balance()
        assert "required_credentials" in result
        assert len(result["required_credentials"]) > 0


class TestMetaAdsBlocked:
    """Meta Ads BLOCKED 状态测试。"""

    def test_no_credentials_returns_blocked_on_insights(self):
        from ad_intelligence.platforms.meta_ads import MetaAdsCollector, MetaAdsConfig
        collector = MetaAdsCollector(MetaAdsConfig(requires_proxy=False))
        result = collector.get_account_insights()
        assert result["success"] is False
        assert result["status"] == "blocked"
        assert result["data"] is None

    def test_no_credentials_returns_blocked_on_campaigns(self):
        from ad_intelligence.platforms.meta_ads import MetaAdsCollector, MetaAdsConfig
        collector = MetaAdsCollector(MetaAdsConfig(requires_proxy=False))
        result = collector.get_campaigns()
        assert result["success"] is False
        assert result["status"] == "blocked"
        assert result["data"] is None
        # 关键：禁止返回空列表冒充成功
        assert result["data"] != []

    def test_proxy_required_blocks_without_proxy(self):
        from ad_intelligence.platforms.meta_ads import MetaAdsCollector, MetaAdsConfig
        config = MetaAdsConfig(
            access_token="test_token",
            ad_account_id="act_123456",
            requires_proxy=True,
            proxy_url="",
        )
        # 确保环境变量中没有代理
        old_proxy = os.environ.get("HTTPS_PROXY")
        old_openai = os.environ.get("OPENAI_PROXY")
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("OPENAI_PROXY", None)
        try:
            collector = MetaAdsCollector(config)
            result = collector.get_account_insights()
            assert result["success"] is False
            assert result["status"] == "blocked"
            assert "proxy" in result["reason"].lower()
        finally:
            if old_proxy:
                os.environ["HTTPS_PROXY"] = old_proxy
            if old_openai:
                os.environ["OPENAI_PROXY"] = old_openai

    def test_health_check_reports_blocked(self):
        from ad_intelligence.platforms.meta_ads import MetaAdsCollector, MetaAdsConfig
        collector = MetaAdsCollector(MetaAdsConfig())
        health = collector.health_check()
        assert health["platform"] == "facebook/instagram"
        assert health["status"] == "blocked"
        assert len(health["blockers"]) > 0

    def test_parse_insights_response(self):
        from ad_intelligence.platforms.meta_ads import MetaAdsCollector
        collector = MetaAdsCollector()
        raw = {"data": [
            {"date_start": "2026-09-01", "impressions": "1000", "clicks": "50",
             "spend": "10.50", "ctr": "5.0", "cpc": "0.21"},
        ]}
        parsed = collector.parse_insights_response(raw)
        assert len(parsed) == 1
        assert parsed[0]["impressions"] == 1000
        assert parsed[0]["clicks"] == 50
        assert parsed[0]["spend"] == 10.50


class TestOceanEngineBlocked:
    """巨量引擎 BLOCKED 状态测试。"""

    def test_no_credentials_returns_blocked_on_balance(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector, OceanEngineConfig
        collector = OceanEngineCollector(OceanEngineConfig())
        result = collector.get_balance()
        assert result["success"] is False
        assert result["status"] == "blocked"
        assert "missing credentials" in result["reason"]
        assert result["data"] is None

    def test_no_credentials_returns_blocked_on_daily_report(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector, OceanEngineConfig
        collector = OceanEngineCollector(OceanEngineConfig())
        result = collector.get_daily_report("2026-09-01", "2026-09-06")
        assert result["success"] is False
        assert result["status"] == "blocked"
        assert result["data"] is None

    def test_no_credentials_returns_blocked_on_campaign_list(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector, OceanEngineConfig
        collector = OceanEngineCollector(OceanEngineConfig())
        result = collector.get_campaign_list()
        assert result["success"] is False
        assert result["status"] == "blocked"
        assert result["data"] is None
        # 关键：禁止返回空列表冒充成功
        assert result["data"] != []

    def test_health_check_reports_blocked(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector, OceanEngineConfig
        collector = OceanEngineCollector(OceanEngineConfig())
        health = collector.health_check()
        assert health["platform"] == "douyin"
        assert health["status"] == "blocked"
        assert "API未配置" in health["blockers"][0]

    def test_calculate_actual_cost_with_rebate(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector, OceanEngineConfig
        collector = OceanEngineCollector(OceanEngineConfig(agency_rebate_rate=0.10))
        assert collector.calculate_actual_cost(1000) == 900.0

    def test_calculate_actual_cost_no_rebate(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector, OceanEngineConfig
        collector = OceanEngineCollector(OceanEngineConfig())
        assert collector.calculate_actual_cost(1000) == 1000

    def test_parse_report_response(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector
        collector = OceanEngineCollector()
        raw = {"data": {"list": [
            {"stat_datetime": "2026-09-01", "stat_cost": 100.5, "show_cnt": 5000,
             "click_cnt": 200, "convert_cnt": 10},
        ]}}
        parsed = collector.parse_report_response(raw)
        assert len(parsed) == 1
        assert parsed[0]["cost"] == 100.5
        assert parsed[0]["impressions"] == 5000
        assert parsed[0]["clicks"] == 200


class TestXAdsBlocked:
    """X Ads BLOCKED 状态测试。"""

    def test_no_credentials_returns_blocked_on_analytics(self):
        from ad_intelligence.platforms.x_ads import XAdsCollector, XAdsConfig
        collector = XAdsCollector(XAdsConfig(requires_proxy=False))
        result = collector.get_analytics("2026-09-01T00:00:00Z", "2026-09-06T23:59:59Z")
        assert result["success"] is False
        assert result["status"] == "blocked"
        assert result["data"] is None

    def test_no_credentials_returns_blocked_on_campaigns(self):
        from ad_intelligence.platforms.x_ads import XAdsCollector, XAdsConfig
        collector = XAdsCollector(XAdsConfig(requires_proxy=False))
        result = collector.get_campaigns()
        assert result["success"] is False
        assert result["status"] == "blocked"
        assert result["data"] is None
        # 关键：禁止返回空列表冒充成功
        assert result["data"] != []

    def test_partial_credentials_still_blocked(self):
        from ad_intelligence.platforms.x_ads import XAdsCollector, XAdsConfig
        config = XAdsConfig(
            consumer_key="test",
            consumer_secret="",  # missing
            access_token="test",
            access_token_secret="test",
            account_id="test",
            requires_proxy=False,
        )
        collector = XAdsCollector(config)
        result = collector.get_campaigns()
        assert result["success"] is False
        assert result["status"] == "blocked"

    def test_oauth_signature_method_exists(self):
        from ad_intelligence.platforms.x_ads import XAdsCollector, XAdsConfig
        config = XAdsConfig(
            consumer_key="test_key",
            consumer_secret="test_secret",
            access_token="test_token",
            access_token_secret="test_token_secret",
        )
        collector = XAdsCollector(config)
        sig = collector._build_oauth_signature(
            "GET", "https://api.x.com/2/ads/campaigns",
            {"count": "100"}
        )
        assert isinstance(sig, str)
        assert len(sig) > 0  # Base64 编码的 HMAC-SHA1 签名

    def test_health_check_reports_blocked(self):
        from ad_intelligence.platforms.x_ads import XAdsCollector, XAdsConfig
        collector = XAdsCollector(XAdsConfig())
        health = collector.health_check()
        assert health["platform"] == "x"
        assert health["status"] == "blocked"
        assert health["auth_method"] == "OAuth 1.0a (HMAC-SHA1)"

    def test_parse_analytics_response(self):
        from ad_intelligence.platforms.x_ads import XAdsCollector
        collector = XAdsCollector()
        raw = {"data": {"id_data": [
            {"metrics": {"impressions": 1000, "clicks": 50, "spend": 15.0},
             "segment": {"date": "2026-09-01"}},
        ]}}
        parsed = collector.parse_analytics_response(raw)
        assert len(parsed) == 1
        assert parsed[0]["impressions"] == 1000
        assert parsed[0]["clicks"] == 50
        assert parsed[0]["spend"] == 15.0


class TestNoFakeData:
    """全局验证：无凭证时所有平台都不伪造数据。"""

    def test_all_platforms_blocked_without_credentials(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        for platform in ["douyin", "xhs", "facebook", "x"]:
            collector = AdCollectorFactory.get_collector(platform)
            assert collector is not None
            health = collector.health_check()
            # 无API凭证时 api_access 必须为 False
            assert health["api_access"] is False, \
                f"{platform} api_access should be False without credentials"
            # 状态应为 blocked / need_credentials（jiguang 可能有 browser cookie fallback 为 ready）
            if platform != "xhs":
                assert health["status"] in ("blocked", "need_credentials"), \
                    f"{platform} should be blocked without credentials, got {health['status']}"
