# -*- coding: utf-8 -*-
"""广告平台商业属性注册表测试"""
import sys, os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


class TestPlatformRegistry:

    def test_all_platforms_registered(self):
        from ad_intelligence.platform_registry import PLATFORM_COMMERCIAL_REGISTRY
        expected = {"xhs", "douyin", "bilibili", "weibo", "zhihu", "facebook", "instagram", "x"}
        assert set(PLATFORM_COMMERCIAL_REGISTRY.keys()) == expected

    def test_china_platforms_no_proxy(self):
        from ad_intelligence.platform_registry import get_platform_profile
        for plat in ["xhs", "douyin", "bilibili", "weibo", "zhihu"]:
            p = get_platform_profile(plat)
            assert p.accessible_from_china is True
            assert p.requires_proxy is False
            assert p.currency.value == "CNY"

    def test_overseas_platforms_require_proxy(self):
        from ad_intelligence.platform_registry import get_platform_profile
        for plat in ["facebook", "instagram", "x"]:
            p = get_platform_profile(plat)
            assert p.accessible_from_china is False
            assert p.requires_proxy is True
            assert p.currency.value == "USD"

    def test_min_deposit_realistic(self):
        """验证最低充值金额符合真实商业现实。"""
        from ad_intelligence.platform_registry import get_platform_profile
        # 中国大陆平台有最低充值
        assert get_platform_profile("douyin").min_deposit == 10000
        assert get_platform_profile("xhs").min_deposit == 5000
        # 海外平台无最低充值（信用卡后付费）
        assert get_platform_profile("facebook").min_deposit == 0
        assert get_platform_profile("x").min_deposit == 0

    def test_api_access_levels(self):
        from ad_intelligence.platform_registry import get_platform_profile, ApiAccessLevel
        # 巨量引擎有有限写权限
        assert get_platform_profile("douyin").api_access_level == ApiAccessLevel.LIMITED_WRITE
        # Meta/X 有完整API（需申请）
        assert get_platform_profile("facebook").api_access_level == ApiAccessLevel.FULL
        # B站/知乎无API
        assert get_platform_profile("bilibili").api_access_level == ApiAccessLevel.NONE
        assert get_platform_profile("zhihu").api_access_level == ApiAccessLevel.NONE

    def test_restricted_industries(self):
        from ad_intelligence.platform_registry import get_platform_profile
        # 所有平台都有受限行业
        for p in get_platform_profile("xhs"), get_platform_profile("douyin"), get_platform_profile("facebook"):
            assert len(p.restricted_industries) > 0

    def test_compliance_regulations(self):
        from ad_intelligence.platform_registry import get_platform_profile
        # 中国大陆平台适用广告法
        assert "广告法" in get_platform_profile("xhs").compliance_regulations
        # 海外平台适用GDPR
        assert "GDPR" in get_platform_profile("facebook").compliance_regulations

    def test_list_by_region(self):
        from ad_intelligence.platform_registry import list_platforms_by_region, Region
        china_platforms = list_platforms_by_region(Region.MAINLAND_CHINA)
        assert "xhs" in china_platforms
        assert "douyin" in china_platforms
        assert "facebook" not in china_platforms

    def test_list_by_access(self):
        from ad_intelligence.platform_registry import list_platforms_by_access
        accessible = list_platforms_by_access(True)
        assert "xhs" in accessible
        assert "facebook" not in accessible
        not_accessible = list_platforms_by_access(False)
        assert "facebook" in not_accessible
        assert "x" in not_accessible

    def test_check_readiness_not_opened(self):
        from ad_intelligence.platform_registry import check_platform_readiness
        result = check_platform_readiness("xhs")
        assert result["ready"] is False
        assert any("账户状态" in b for b in result["blockers"])

    def test_check_readiness_unknown_platform(self):
        from ad_intelligence.platform_registry import check_platform_readiness
        result = check_platform_readiness("unknown_platform")
        assert result["ready"] is False
        assert "不在注册表" in result["reason"]

    def test_roi_normalization(self):
        from ad_intelligence.platform_registry import get_cross_platform_roi_normalization, Currency
        rates = get_cross_platform_roi_normalization(["xhs", "facebook"], base_currency=Currency.CNY)
        assert rates["xhs"] == 1.0
        assert rates["facebook"] > 1.0  # USD -> CNY

    def test_all_profiles_have_required_fields(self):
        """确保所有平台画像都有完整的商业属性字段。"""
        from ad_intelligence.platform_registry import PLATFORM_COMMERCIAL_REGISTRY
        required_fields = [
            "platform", "display_name", "ad_system", "primary_regions",
            "accessible_from_china", "requires_proxy", "currency",
            "payment_methods", "min_deposit", "api_access_level",
            "account_status", "restricted_industries", "compliance_regulations",
            "targeting_granularity", "data_granularity",
        ]
        for name, profile in PLATFORM_COMMERCIAL_REGISTRY.items():
            for field in required_fields:
                assert hasattr(profile, field), f"{name} 缺少字段 {field}"
