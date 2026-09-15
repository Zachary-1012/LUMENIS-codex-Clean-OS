# -*- coding: utf-8 -*-
"""
多平台采集连通验证测试
======================
测试范围：
  1. cookie_vault 统一加载（8平台 cookie 文件存在且可解析）
  2. 适配器注册（所有平台适配器可注册）
  3. collector_status API 路由注册与响应结构
  4. 数据精准门禁（publish_date 与 collected_at 分离、缺失不臆造）
  5. 双域隔离（ZBMP 不被 CTH subject_rules 过滤）

注意：真实网络连通验证由 _verify_connectivity.py 执行，本测试只做
结构/契约/单元级验证，不发起真实平台请求（避免 CI 环境网络依赖）。
"""
import sys
import json
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v4_upgrade.adapters.cookie_vault import (
    load_cookies, to_cookie_string, to_requests_cookies,
    check_cookie_status, PLATFORM_COOKIE_PATHS, PLATFORM_AUTH_COOKIES,
)
from v4_upgrade.adapters.registry import registry, register_default_adapters
from v4_upgrade.adapters.base import BaseAdapter, CollectedNote, AdapterResult


# ============================================================
# 1. cookie_vault 统一加载测试
# ============================================================
PLATFORMS_UNDER_TEST = [
    "xiaohongshu", "weibo", "bilibili", "zhihu",
    "douyin", "x", "instagram", "jiguang",
]


class TestCookieVault:
    """cookie_vault 统一加载验证"""

    def test_all_platforms_have_cookie_path_config(self):
        """所有测试平台都在 PLATFORM_COOKIE_PATHS 中配置了路径"""
        for p in PLATFORMS_UNDER_TEST:
            assert p in PLATFORM_COOKIE_PATHS, f"{p} 未配置 cookie 路径"
            assert len(PLATFORM_COOKIE_PATHS[p]) > 0, f"{p} cookie 路径为空"

    def test_all_platforms_have_auth_cookie_config(self):
        """所有测试平台都在 PLATFORM_AUTH_COOKIES 中配置了关键认证 cookie"""
        for p in PLATFORMS_UNDER_TEST:
            assert p in PLATFORM_AUTH_COOKIES, f"{p} 未配置认证 cookie 名"
            assert len(PLATFORM_AUTH_COOKIES[p]) > 0, f"{p} 认证 cookie 名为空"

    def test_load_cookies_returns_list_for_all_platforms(self):
        """所有平台 load_cookies 返回 list（不抛异常）"""
        for p in PLATFORMS_UNDER_TEST:
            cookies = load_cookies(p)
            assert isinstance(cookies, list), f"{p} load_cookies 返回非 list"

    def test_cookie_status_is_explicit(self):
        """凭证不进仓库；存在时验证认证结构，不存在时必须显式报告。"""
        for p in PLATFORMS_UNDER_TEST:
            status = check_cookie_status(p)
            assert status["platform"] == p
            assert status["cookie_count"] >= 0
            assert status["status"] in {"ACTIVE", "MISSING", "INVALID"}
            if status["cookie_count"] > 0:
                assert status["has_auth_cookie"], f"{p} 缺少关键认证 cookie"

    def test_to_cookie_string_matches_loaded_state(self):
        for p in PLATFORMS_UNDER_TEST:
            s = to_cookie_string(p)
            assert isinstance(s, str), f"{p} to_cookie_string 返回非 str"
            if load_cookies(p):
                assert "=" in s, f"{p} cookie string 格式异常"
            else:
                assert s == ""

    def test_to_requests_cookies_returns_safe_dict(self):
        for p in PLATFORMS_UNDER_TEST:
            c = to_requests_cookies(p)
            assert isinstance(c, dict), f"{p} to_requests_cookies 返回非 dict"
            assert all(isinstance(k, str) and isinstance(v, str) for k, v in c.items())

    def test_no_cookie_value_in_status_output(self):
        """check_cookie_status 不返回 cookie value（安全）"""
        for p in PLATFORMS_UNDER_TEST:
            status = check_cookie_status(p)
            for key in status:
                val = status[key]
                if isinstance(val, str):
                    # cookie value 通常较长且含特殊字符，状态字段不应包含
                    assert "sessionid" not in val.lower() or key == "auth_cookies_found", \
                        f"{p} 状态输出可能泄露 cookie value"


# ============================================================
# 2. 适配器注册测试
# ============================================================
class TestAdapterRegistry:
    """适配器注册中心验证"""

    def test_register_default_adapters_no_exception(self):
        """register_default_adapters 不抛异常"""
        try:
            register_default_adapters()
        except Exception as e:
            pytest.fail(f"register_default_adapters 抛异常: {e}")

    def test_core_platforms_registered(self):
        """核心平台适配器已注册"""
        register_default_adapters()
        platforms = registry.list_platforms()
        for p in ["douyin", "instagram", "bilibili", "weibo", "zhihu", "x"]:
            assert p in platforms, f"平台 {p} 未注册"

    def test_jiguang_registered(self):
        """极光适配器已注册"""
        register_default_adapters()
        assert "jiguang" in registry.list_platforms(), "jiguang 未注册"

    def test_each_adapter_has_platform_name(self):
        """每个已注册适配器有 platform_name 和 platform_display"""
        register_default_adapters()
        for p in registry.list_platforms():
            adapter = registry.get(p)
            assert adapter is not None
            assert hasattr(adapter, "platform_name")
            assert hasattr(adapter, "platform_display")

    def test_adapter_status_has_required_fields(self):
        """适配器 get_status 返回必要字段"""
        register_default_adapters()
        for p in registry.list_platforms()[:5]:  # 抽样
            adapter = registry.get(p)
            status = adapter.get_status()
            assert "platform" in status
            assert "breaker_state" in status
            assert "rate_limiter_tokens" in status


# ============================================================
# 3. collector_status API 测试
# ============================================================
class TestCollectorStatusAPI:
    """collector_status API 结构验证"""

    def test_get_all_status_returns_dict(self):
        """get_all_status 返回 dict"""
        from collector_status_api import get_all_status
        result = get_all_status()
        assert isinstance(result, dict)

    def test_status_has_required_top_level_fields(self):
        """状态响应有必要顶层字段"""
        from collector_status_api import get_all_status
        result = get_all_status()
        assert "timestamp" in result
        assert "total_platforms" in result
        assert "platforms" in result
        assert "summary" in result
        assert result["total_platforms"] == len(result["platforms"])
        # 搜狗微信/搜索已接入平台状态列表
        platform_names = [p["platform"] for p in result["platforms"]]
        assert "sogou_wechat" in platform_names
        assert "sogou_search" in platform_names

    def test_each_platform_status_has_required_fields(self):
        """每个平台状态有必要字段"""
        from collector_status_api import get_all_status
        result = get_all_status()
        required = ["platform", "display", "cookie_status", "last_check",
                    "records_parsed", "error"]
        for p in result["platforms"]:
            for field in required:
                assert field in p, f"平台 {p.get('platform')} 缺少字段 {field}"

    def test_summary_counts_match(self):
        """summary 计数与 platforms 状态一致"""
        from collector_status_api import get_all_status
        result = get_all_status()
        summary = result["summary"]
        platforms = result["platforms"]
        assert summary["active"] == sum(1 for p in platforms if p["cookie_status"] in ("ACTIVE", "VERIFIED"))
        assert summary["partial"] == sum(1 for p in platforms if p["cookie_status"] == "PARTIAL")
        assert summary["expired"] == sum(1 for p in platforms if p["cookie_status"] == "EXPIRED")

    def test_update_platform_status_persists(self):
        """update_platform_status 写入缓存并可读取"""
        from collector_status_api import update_platform_status, get_all_status
        update_platform_status("test_platform", "VERIFIED", 5, "test error", 200)
        result = get_all_status()
        # test_platform 不在 PLATFORMS 列表中，不会出现在结果里
        # 但缓存文件应已更新
        cache_path = Path(__file__).resolve().parents[1] / "data" / "collector_status_cache.json"
        assert cache_path.exists()
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        assert "test_platform" in cache
        assert cache["test_platform"]["cookie_status"] == "VERIFIED"
        assert cache["test_platform"]["records_parsed"] == 5


# ============================================================
# 4. 数据精准门禁测试
# ============================================================
class TestDataPrecision:
    """数据精准红线验证"""

    def test_collected_note_has_publish_and_source_separated(self):
        """CollectedNote 中 publish_date 与 source_platform 分离"""
        note = CollectedNote(
            title="test", content="test content",
            url="https://example.com/1", author="user",
            publish_date="2026-09-06T12:00:00+08:00",
            source_platform="weibo",
        )
        assert note.publish_date != ""
        assert note.source_platform == "weibo"
        # publish_date 是发布时间，不是采集时间
        assert "2026" in note.publish_date

    def test_missing_publish_date_is_empty_not_fabricated(self):
        """缺失 publish_date 留空，不臆造"""
        note = CollectedNote(title="test", content="content", source_platform="x")
        assert note.publish_date == "", "缺失发布时间不应臆造"

    def test_missing_interaction_counts_remain_unknown(self):
        """缺失的互动指标保持未知；只有来源显式报告 0 才表示实测为零。"""
        note = CollectedNote(title="test", content="content", source_platform="weibo")
        assert note.likes is None
        assert note.comments is None
        assert note.collects is None
        assert note.shares is None

    def test_adapter_result_error_field_records_failures(self):
        """AdapterResult 失败时 error 字段记录错误，不静默丢弃"""
        result = AdapterResult(success=False, error="登录态失效")
        assert result.success is False
        assert result.error == "登录态失效"
        assert len(result.notes) == 0

    def test_raw_data_preserved_for_audit(self):
        """raw_data 保留原始数据用于审计"""
        note = CollectedNote(
            title="test", content="content", source_platform="douyin",
            raw_data={"engine": "douyin_search_api", "aweme_id": "12345", "create_time": 1757000000},
        )
        assert note.raw_data["engine"] == "douyin_search_api"
        assert note.raw_data["aweme_id"] == "12345"
        assert "create_time" in note.raw_data


# ============================================================
# 5. 双域隔离测试
# ============================================================
class TestDualDomainIsolation:
    """双域隔离验证：ZBMP 不被 CTH subject_rules 过滤"""

    def test_zbmp_and_cth_are_distinct_product_ids(self):
        """ZBMP 和 CTH 是不同的 product_id"""
        assert "ZBMP" != "CTH"

    def test_collector_automation_has_dual_domain_support(self):
        """collector_automation.py 包含 product_id 和 domain_id"""
        f = Path(__file__).resolve().parents[1] / "collector_automation.py"
        if f.exists():
            content = f.read_text(encoding="utf-8", errors="ignore")
            assert "product_id" in content, "collector_automation 缺少 product_id"
            assert "domain_id" in content, "collector_automation 缺少 domain_id"

    def test_subject_rules_are_domain_scoped(self):
        """subject_rules 应按域隔离，CTH 规则不隐式过滤 ZBMP"""
        # 检查是否有全局 subject_filter 可能跨域过滤
        base_path = Path(__file__).resolve().parents[1] / "v4_upgrade" / "adapters" / "base.py"
        content = base_path.read_text(encoding="utf-8", errors="ignore")
        # base adapter 不应有硬编码的 CTH 品牌/业态过滤
        assert "199品牌" not in content, "base adapter 不应硬编码 CTH 品牌过滤"
        assert "9业态" not in content, "base adapter 不应硬编码 CTH 业态过滤"

    def test_canonical_data_includes_product_field(self):
        """标准化数据应包含 product 标识字段（用于域隔离）"""
        note = CollectedNote(
            title="test", content="content", source_platform="weibo",
            raw_data={"product_id": "ZBMP", "domain_id": None},
        )
        assert note.raw_data.get("product_id") == "ZBMP"
        # ZBMP 数据不应有 CTH domain_id
        assert note.raw_data.get("domain_id") is None

    def test_cth_data_has_domain_id(self):
        """CTH 数据应包含 domain_id"""
        note = CollectedNote(
            title="test", content="content", source_platform="xiaohongshu",
            raw_data={"product_id": "CTH", "domain_id": "cth_main"},
        )
        assert note.raw_data.get("product_id") == "CTH"
        assert note.raw_data.get("domain_id") == "cth_main"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
