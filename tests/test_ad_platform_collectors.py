# -*- coding: utf-8 -*-
"""广告平台数据采集器测试"""
import sys, os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestOceanEngineCollector:

    def test_health_check_no_api(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector
        c = OceanEngineCollector()
        h = c.health_check()
        assert h["platform"] == "douyin"
        assert h["ad_system"] == "ocean_engine"
        assert h["api_access"] is False
        assert h["currency"] == "CNY"
        assert h["min_deposit"] == 10000
        assert h["status"] == "blocked"
        assert any("API未配置" in b for b in h.get("blockers", []))

    def test_get_balance_no_api(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector
        c = OceanEngineCollector()
        r = c.get_balance()
        assert r["success"] is False
        assert r["status"] == "blocked"
        assert "missing credentials" in r.get("reason", "")

    def test_read_only_methods_pass_endpoint_as_first_request_argument(self, monkeypatch):
        from ad_intelligence.platforms.ocean_engine import (
            OceanEngineCollector, OceanEngineConfig, OceanEngineEndpoint,
        )

        collector = OceanEngineCollector(OceanEngineConfig(
            access_token="synthetic-token", advertiser_id="12345",
        ))
        assert collector._has_api_access() is True
        calls = []
        monkeypatch.setattr(
            collector, "_api_request",
            lambda *args, **kwargs: calls.append((args, kwargs)) or {"success": True},
        )

        collector.get_balance()
        collector.get_advertiser_info()

        assert calls == [
            ((OceanEngineEndpoint.BALANCE.value,), {}),
            ((OceanEngineEndpoint.ADVERTISER_INFO.value,), {
                "params": {"advertiser_ids": ["12345"]},
            }),
        ]

    def test_get_advertiser_info_encodes_array_contract_on_real_request_path(
            self, monkeypatch):
        from urllib.parse import parse_qs, urlsplit
        import requests
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector, OceanEngineConfig

        collector = OceanEngineCollector(OceanEngineConfig(
            access_token="synthetic-token", advertiser_id="12345",
        ))
        monkeypatch.setattr(collector, "_rate_limit_wait", lambda: None)
        captured = {}

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {"code": 0, "data": {"advertiser_id": 12345}}

        def fake_get(url, *, headers, params, timeout):
            # Let requests perform its real query encoding, but never send it.
            prepared = requests.Request("GET", url, headers=headers, params=params).prepare()
            captured["url"] = prepared.url
            captured["params"] = params
            captured["timeout"] = timeout
            return FakeResponse()

        monkeypatch.setattr(requests, "get", fake_get)

        result = collector.get_advertiser_info()

        query = parse_qs(urlsplit(captured["url"]).query)
        assert result["success"] is True
        assert query["advertiser_ids"] == ["12345"]
        assert "advertiser_id" not in query
        assert captured["params"] == {"advertiser_ids": ["12345"]}
        assert captured["timeout"] == 20

    def test_get_advertiser_info_without_credentials_stays_blocked(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector

        result = OceanEngineCollector().get_advertiser_info()

        assert result["success"] is False
        assert result["status"] == "blocked"
        assert "missing credentials" in result.get("reason", "")

    def test_actual_cost_with_rebate(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector, OceanEngineConfig
        c = OceanEngineCollector(OceanEngineConfig(agency_rebate_rate=0.10))
        assert c.calculate_actual_cost(1000) == 900.0

    def test_actual_cost_no_rebate(self):
        from ad_intelligence.platforms.ocean_engine import OceanEngineCollector
        c = OceanEngineCollector()
        assert c.calculate_actual_cost(1000) == 1000


class TestJiguangCollector:

    def test_health_check(self):
        from ad_intelligence.platforms.jiguang import JiguangCollector
        c = JiguangCollector()
        h = c.health_check()
        assert h["platform"] == "xhs"
        assert h["ad_system"] == "jiguang"
        assert h["currency"] == "CNY"
        assert h["min_deposit"] == 5000
        assert "聚光API需特批" in h["note"]


class TestMetaAdsCollector:

    # 测试隔离：这两个用例断言“无代理”前提，全量运行时 .env 可能注入代理变量，
    # 显式清除以保证确定性行为（不改变任何断言强度）。
    _PROXY_VARS = ("OPENAI_PROXY", "HTTPS_PROXY", "HTTP_PROXY",
                   "https_proxy", "http_proxy", "ALL_PROXY", "all_proxy")

    @pytest.fixture(autouse=True)
    def _isolate_no_proxy(self, monkeypatch):
        for var in self._PROXY_VARS:
            monkeypatch.delenv(var, raising=False)

    def test_health_check_no_api_no_proxy(self):
        from ad_intelligence.platforms.meta_ads import MetaAdsCollector
        c = MetaAdsCollector()
        h = c.health_check()
        assert h["platform"] == "facebook/instagram"
        assert h["api_access"] is False
        assert h["currency"] == "USD"
        assert h["min_deposit"] == 0
        assert h["status"] == "blocked"
        assert len(h["blockers"]) >= 2  # API + 代理

    def test_requires_proxy(self):
        from ad_intelligence.platforms.meta_ads import MetaAdsCollector, MetaAdsConfig
        c = MetaAdsCollector(MetaAdsConfig(access_token="test", ad_account_id="act_123"))
        h = c.health_check()
        # 有API但无代理，仍然blocked
        assert h["api_access"] is True
        assert any("代理" in b for b in h["blockers"])


class TestXAdsCollector:

    def test_health_check(self):
        from ad_intelligence.platforms.x_ads import XAdsCollector
        c = XAdsCollector()
        h = c.health_check()
        assert h["platform"] == "x"
        assert h["ad_system"] == "x_ads"
        assert h["currency"] == "USD"
        assert h["min_deposit"] == 0
        assert h["status"] == "blocked"
        assert "OAuth" in h["blockers"][0]


class TestAdCollectorFactory:

    def test_get_douyin_collector(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        c = AdCollectorFactory.get_collector("douyin")
        assert c is not None
        assert c.health_check()["platform"] == "douyin"

    def test_get_xhs_collector(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        c = AdCollectorFactory.get_collector("xhs")
        assert c is not None
        assert c.health_check()["platform"] == "xhs"

    def test_get_meta_collector(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        c = AdCollectorFactory.get_collector("facebook")
        assert c is not None

    def test_get_x_collector(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        c = AdCollectorFactory.get_collector("x")
        assert c is not None

    def test_health_check_all(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        results = AdCollectorFactory.health_check_all()
        assert "douyin" in results
        assert "xhs" in results
        assert "facebook" in results
        assert "x" in results
        for plat, h in results.items():
            assert "status" in h

    def test_singleton(self):
        from ad_intelligence.platforms.factory import AdCollectorFactory
        c1 = AdCollectorFactory.get_collector("douyin")
        c2 = AdCollectorFactory.get_collector("douyin")
        assert c1 is c2
