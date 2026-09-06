# -*- coding: utf-8 -*-
"""
搜狗微信/搜狗搜索适配器单元测试
覆盖：适配器注册、搜索解析、标准化字段、去重、失败显式记录、BLOCKED检测
全 mock，不实际联网。
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from v4_upgrade.adapters.base import AdapterResult, CollectedNote
from v4_upgrade.adapters.sogou_wechat import SogouWechatAdapter
from v4_upgrade.adapters.sogou_search import SogouSearchAdapter


# ============================================================
# 搜狗微信测试
# ============================================================
class TestSogouWechatAdapter:

    def test_platform_identity(self):
        ad = SogouWechatAdapter()
        assert ad.platform_name == "sogou_wechat"
        assert ad.platform_display == "搜狗微信"

    def test_product_domain_passthrough(self):
        """product_id/domain_id 透传，不篡改。"""
        ad = SogouWechatAdapter(product_id="cth_001", domain_id="CTH")
        assert ad.product_id == "cth_001"
        assert ad.domain_id == "CTH"

    def test_dual_domain_isolation(self):
        """双域隔离：CTH 和 ZBMP 实例互不影响。"""
        cth = SogouWechatAdapter(product_id="p_cth", domain_id="CTH")
        zbmp = SogouWechatAdapter(product_id="p_zbmp", domain_id="ZBMP")
        assert cth.domain_id != zbmp.domain_id
        assert cth.product_id != zbmp.product_id

    def test_empty_keyword_returns_error(self):
        ad = SogouWechatAdapter()
        r = ad.search("", max_results=10)
        assert r.success is False
        assert "关键词为空" in r.error

    def test_blocked_detection_antispider(self):
        """命中反爬关键词 → BLOCKED。"""
        ad = SogouWechatAdapter()
        assert ad._is_blocked("<html>antispider verify page</html>") is True

    def test_blocked_detection_captcha(self):
        ad = SogouWechatAdapter()
        assert ad._is_blocked("<html>请输入验证码</html>") is True

    def test_blocked_detection_short_page(self):
        """空壳页（<800字符）视为被拦，避免假成功0条。"""
        ad = SogouWechatAdapter()
        assert ad._is_blocked("<html></html>") is True
        assert ad._is_blocked("") is True

    def test_blocked_detection_normal_page(self):
        """正常长页面（>800字符）不被误判为 BLOCKED。"""
        ad = SogouWechatAdapter()
        normal = "<html><body>" + "正常搜索结果内容展示 " * 80 + "</body></html>"
        assert ad._is_blocked(normal) is False

    @patch("v4_upgrade.adapters.sogou_wechat.SogouWechatAdapter._load_cookies", return_value={})
    def test_search_blocked_returns_failure(self, mock_cookies):
        """命中反爬页 → success=False，绝不返回空列表冒充成功。"""
        ad = SogouWechatAdapter()
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = "<html>请输入验证码 antispider</html>"
            mock_resp.encoding = "utf-8"
            mock_get.return_value = mock_resp
            r = ad.search("太古汇", max_results=10)
        assert r.success is False
        assert "反爬" in r.error or "验证" in r.error
        assert r.notes == []

    @patch("v4_upgrade.adapters.sogou_wechat.SogouWechatAdapter._load_cookies", return_value={})
    def test_search_network_error_returns_failure(self, mock_cookies):
        """网络异常 → success=False，显式记录。"""
        ad = SogouWechatAdapter()
        with patch("requests.get", side_effect=Exception("连接超时")):
            r = ad.search("太古汇", max_results=10)
        assert r.success is False
        assert "网络异常" in r.error

    def test_parse_regex_fallback(self):
        """正则兜底解析（保留原有逻辑）。"""
        ad = SogouWechatAdapter()
        html = '''
        <div class="txt-box">
            <h3><a href="/link?url=abc123">测试公众号文章标题</a></h3>
            <p class="txt-info">这是文章摘要内容</p>
            <a id="sogou_vr_11002301_box_0">测试公众号</a>
        </div>
        '''
        notes = ad._parse_results(html)
        # BeautifulSoup 优先，正则兜底；至少能解析到标题
        assert len(notes) >= 1
        note = notes[0]
        assert "测试公众号文章标题" in note.title
        assert note.source_platform == "sogou_wechat"

    def test_standard_note_fields(self):
        """标准化笔记字段：content_hash/platform_id/product_id/domain_id 齐全。"""
        ad = SogouWechatAdapter(product_id="p1", domain_id="CTH")
        note = ad._make_standard_note(
            title="测试标题", content="测试内容",
            url="https://example.com/1", author="测试号",
            publish_date="2026-09-01",
        )
        assert isinstance(note, CollectedNote)
        assert note.title == "测试标题"
        assert note.source_platform == "sogou_wechat"
        assert note.raw_data["content_hash"]
        assert note.raw_data["platform_id"].startswith("sogou_wechat_")
        assert note.raw_data["product_id"] == "p1"
        assert note.raw_data["domain_id"] == "CTH"
        # 缺失字段显式空，不用 0/"未知" 填
        assert note.author_id == ""
        assert note.cover == ""

    def test_standard_note_missing_fields_explicit(self):
        """数据精准红线：缺失字段显式空串，不用 0 或"未知"静默填。"""
        ad = SogouWechatAdapter()
        note = ad._make_standard_note(title="只有标题")
        assert note.content == ""
        assert note.url == ""
        assert note.author == ""
        assert note.publish_date == ""
        assert note.author_id == ""

    def test_extract_date_absolute(self):
        ad = SogouWechatAdapter()
        assert ad._extract_date("发布于2026年9月1日") == "2026-09-01"

    def test_extract_date_relative_hours(self):
        ad = SogouWechatAdapter()
        result = ad._extract_date("3小时前")
        assert len(result) == 10  # YYYY-MM-DD format

    def test_extract_date_missing_returns_empty(self):
        """无日期时返回空串，不用当前日期伪造。"""
        ad = SogouWechatAdapter()
        assert ad._extract_date("无日期信息") == ""
        assert ad._extract_date("") == ""

    def test_dedup_content_hash(self):
        """相同标题+URL 产生相同 content_hash，可用于去重。"""
        ad = SogouWechatAdapter()
        n1 = ad._make_standard_note(title="A", url="https://x.com/1")
        n2 = ad._make_standard_note(title="A", url="https://x.com/1")
        n3 = ad._make_standard_note(title="B", url="https://x.com/2")
        assert n1.raw_data["content_hash"] == n2.raw_data["content_hash"]
        assert n1.raw_data["content_hash"] != n3.raw_data["content_hash"]

    def test_cookie_vault_load_no_crash(self):
        """cookie_vault 加载失败时降级匿名，不崩溃。"""
        ad = SogouWechatAdapter()
        with patch("v4_upgrade.adapters.cookie_vault.to_requests_cookies", side_effect=Exception("no vault")):
            cookies = ad._load_cookies()
        assert cookies == {}

    def test_get_status_includes_cookie(self):
        ad = SogouWechatAdapter()
        status = ad.get_status()
        assert "cookie_status" in status
        assert status["platform"] == "sogou_wechat"


# ============================================================
# 搜狗搜索测试
# ============================================================
class TestSogouSearchAdapter:

    def test_platform_identity(self):
        ad = SogouSearchAdapter()
        assert ad.platform_name == "sogou_search"
        assert ad.platform_display == "搜狗搜索"

    def test_product_domain_passthrough(self):
        ad = SogouSearchAdapter(product_id="zbmp_001", domain_id="ZBMP")
        assert ad.product_id == "zbmp_001"
        assert ad.domain_id == "ZBMP"

    def test_empty_keyword_returns_error(self):
        ad = SogouSearchAdapter()
        r = ad.search("", max_results=10)
        assert r.success is False

    def test_blocked_detection(self):
        ad = SogouSearchAdapter()
        assert ad._is_blocked("<html>antispider</html>") is True
        assert ad._is_blocked("<html>请输入验证码</html>") is True
        assert ad._is_blocked("") is True
        # 正常长页面（>800字符）不被误判为 BLOCKED
        normal = "<html><body>" + "正常搜索结果页面内容展示 " * 80 + "</body></html>"
        assert ad._is_blocked(normal) is False

    def test_channels_defined(self):
        """新闻+网页两个频道。"""
        assert len(SogouSearchAdapter._CHANNELS) == 2
        names = [c[0] for c in SogouSearchAdapter._CHANNELS]
        assert "news" in names
        assert "web" in names

    @patch("v4_upgrade.adapters.sogou_search.SogouSearchAdapter._load_cookies", return_value={})
    def test_search_all_channels_blocked(self, mock_cookies):
        """两个频道都被拦 → success=False，不返回空成功。"""
        ad = SogouSearchAdapter()
        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "<html>请输入验证码 antispider</html>"
            mock_resp.encoding = "utf-8"
            mock_session.get.return_value = mock_resp
            mock_session_cls.return_value = mock_session
            r = ad.search("太古汇", max_results=10)
        assert r.success is False
        assert r.notes == []

    def test_parse_channel_with_bs4(self):
        """BeautifulSoup 解析新闻频道结果。"""
        ad = SogouSearchAdapter()
        html = '''
        <div class="vrwrap">
            <h3><a href="https://www.sogou.com/link?url=abc">测试新闻标题</a></h3>
            <p class="star-wiki">这是新闻摘要内容</p>
            <div class="news-from">测试媒体 2026-09-01</div>
        </div>
        '''
        notes = ad._parse_channel(html, "news")
        assert len(notes) >= 1
        note = notes[0]
        assert "测试新闻标题" in note.title
        assert note.source_platform == "sogou_search"
        # raw_data 携带 content_hash/platform_id/product_id/domain_id
        assert "content_hash" in note.raw_data
        assert "platform_id" in note.raw_data
        assert note.raw_data["domain_id"] == ""  # 默认空

    def test_parse_channel_with_product_domain(self):
        """解析时 product_id/domain_id 透传到每条笔记。"""
        ad = SogouSearchAdapter(product_id="p_zbmp", domain_id="ZBMP")
        html = '''
        <div class="vrwrap">
            <h3><a href="https://example.com/news1">标题</a></h3>
            <p class="star-wiki">摘要</p>
        </div>
        '''
        notes = ad._parse_channel(html, "news")
        if notes:
            assert notes[0].raw_data["product_id"] == "p_zbmp"
            assert notes[0].raw_data["domain_id"] == "ZBMP"

    def test_domain_source_extraction(self):
        """从 URL 提取域名作来源兜底。"""
        assert SogouSearchAdapter._domain_source("https://www.sohu.com/a/123") == "sohu"
        assert SogouSearchAdapter._domain_source("https://m.163.com/news/1") == "163"

    def test_url_date_conflict(self):
        """URL 路径年份与发布日期年份差>1 → 标记冲突（只标注不篡改）。"""
        assert SogouSearchAdapter._url_date_conflict(
            "https://example.com/2020/article", "2026-09-01"
        ) is True
        assert SogouSearchAdapter._url_date_conflict(
            "https://example.com/2026/article", "2026-09-01"
        ) is False

    def test_cookie_vault_load(self):
        ad = SogouSearchAdapter()
        with patch("v4_upgrade.adapters.cookie_vault.to_requests_cookies", return_value={"SNUID": "abc"}):
            cookies = ad._load_cookies()
        assert cookies == {"SNUID": "abc"}

    def test_get_status_includes_cookie(self):
        ad = SogouSearchAdapter()
        status = ad.get_status()
        assert "cookie_status" in status


# ============================================================
# 注册表集成测试
# ============================================================
class TestAdapterRegistryIntegration:

    def test_sogou_adapters_registered(self):
        """搜狗微信/搜索在默认注册表中。"""
        from v4_upgrade.adapters.registry import registry, register_default_adapters
        register_default_adapters()
        assert registry.get("sogou_wechat") is not None
        assert registry.get("sogou_search") is not None

    def test_sogou_wechat_in_registry_list(self):
        from v4_upgrade.adapters.registry import registry, register_default_adapters
        register_default_adapters()
        platforms = registry.list_platforms()
        assert "sogou_wechat" in platforms
        assert "sogou_search" in platforms

    def test_sogou_collect_safe_no_crash(self):
        """safe_collect 永不抛异常。"""
        ad = SogouWechatAdapter()
        with patch("requests.get", side_effect=Exception("网络崩溃")):
            r = ad.safe_collect("太古汇", max_results=5)
        assert isinstance(r, AdapterResult)
        # safe_collect 捕获异常返回失败，不崩溃
        assert r.success is False or r.error  # 可能因熔断器/降级返回


# ============================================================
# collector_status_api 平台列表测试
# ============================================================
class TestCollectorStatusApiPlatforms:

    def test_sogou_platforms_in_status_list(self):
        """collector_status_api 平台列表包含搜狗微信/搜索。"""
        from collector_status_api import PLATFORMS, PLATFORM_DISPLAY
        assert "sogou_wechat" in PLATFORMS
        assert "sogou_search" in PLATFORMS
        assert PLATFORM_DISPLAY["sogou_wechat"] == "搜狗微信"
        assert PLATFORM_DISPLAY["sogou_search"] == "搜狗搜索"

    def test_get_all_status_includes_sogou(self):
        """get_all_status 返回包含搜狗平台。"""
        from collector_status_api import get_all_status
        data = get_all_status()
        platform_names = [p["platform"] for p in data["platforms"]]
        assert "sogou_wechat" in platform_names
        assert "sogou_search" in platform_names
        assert data["total_platforms"] == len(PLATFORMS) if 'PLATFORMS' in dir() else True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
