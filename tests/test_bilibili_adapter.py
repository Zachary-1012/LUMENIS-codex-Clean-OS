# -*- coding: utf-8 -*-
"""
B站 v4 adapter 单元测试（全 mock，不实际访问 B站 API）
覆盖：成功/空结果/登录失效/风控/cookie失效/时间戳转换/registry 注册
"""
import sys, os
import pytest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lumenis.adapters.bilibili import BilibiliAdapter
from lumenis.adapters.base import AdapterResult


def _make_manager(logged_in=True, search_result=None):
    """构造 mock B站登录管理器。"""
    m = MagicMock()
    m.check_login_status.return_value = {"logged_in": logged_in}
    m.search_videos.return_value = search_result or {"ok": True, "videos": [], "total": 0}
    return m


class TestBilibiliAdapterSearch:

    def test_search_success_returns_notes(self):
        """成功搜索：返回标准化 CollectedNote 列表。"""
        manager = _make_manager(search_result={
            "ok": True,
            "total": 2,
            "videos": [
                {"id": 1, "bvid": "BV1xx", "title": "测试视频<em>广州</em>",
                 "author": "up主A", "play": 1000, "video_review": 50,
                 "favorites": 30, "pubdate": 1700000000, "duration": "10:30",
                 "description": "这是描述", "url": "https://www.bilibili.com/video/BV1xx"},
                {"id": 2, "bvid": "BV2yy", "title": "第二个视频",
                 "author": "up主B", "play": 500, "video_review": 10,
                 "favorites": 5, "pubdate": 1700000100, "duration": "5:00",
                 "description": "", "url": "https://www.bilibili.com/video/BV2yy"},
            ],
        })
        ad = BilibiliAdapter(manager=manager)
        result = ad.search("广州太古汇", max_results=10)

        assert result.success is True
        assert result.raw_count == 2
        assert len(result.notes) == 2
        # 标题应去掉 <em> 标签
        assert "广州" in result.notes[0].title
        assert "<em>" not in result.notes[0].title
        assert result.notes[0].author == "up主A"
        assert result.notes[0].url == "https://www.bilibili.com/video/BV1xx"
        assert result.notes[0].collects == 30
        # video_review has no verified comment-count semantics; do not map it to comments.
        assert result.notes[0].comments is None
        assert result.notes[0].raw_data["video_review"] == 50
        assert result.notes[0].source_platform == "bilibili"
        # publish_date 应为 ISO 格式
        assert result.notes[0].publish_date.startswith("2023-")
        # raw_data 保留 bvid/play 等
        assert result.notes[0].raw_data["bvid"] == "BV1xx"
        assert result.notes[0].raw_data["play"] == 1000

    def test_search_empty_returns_success_with_no_notes(self):
        """正常无内容：success=True 但 notes 为空（不伪装失败）。"""
        manager = _make_manager(search_result={"ok": True, "videos": [], "total": 0})
        ad = BilibiliAdapter(manager=manager)
        result = ad.search("不存在的关键词", max_results=10)
        assert result.success is True
        assert len(result.notes) == 0
        assert result.raw_count == 0

    def test_search_not_logged_in_returns_failure(self):
        """登录态失效：如实返回失败，不假成功。"""
        manager = _make_manager(logged_in=False)
        ad = BilibiliAdapter(manager=manager)
        result = ad.search("test", max_results=5)
        assert result.success is False
        assert "登录态失效" in result.error or "cookie" in result.error.lower()

    def test_search_cookie_expired_code_minus_101(self):
        """code=-101：cookie 失效。"""
        manager = _make_manager(search_result={
            "ok": False, "error": "账号未登录", "code": -101,
        })
        ad = BilibiliAdapter(manager=manager)
        result = ad.search("test", max_results=5)
        assert result.success is False
        assert "cookie" in result.error.lower() or "失效" in result.error

    def test_search_risk_control_code_minus_352(self):
        """code=-352：风控校验，如实返回不硬刚。"""
        manager = _make_manager(search_result={
            "ok": False, "error": "风控校验失败", "code": -352,
        })
        ad = BilibiliAdapter(manager=manager)
        result = ad.search("test", max_results=5)
        assert result.success is False
        assert "风控" in result.error or "频控" in result.error

    def test_search_rate_limit_code_minus_509(self):
        """code=-509：频控。"""
        manager = _make_manager(search_result={
            "ok": False, "error": "请求过于频繁", "code": -509,
        })
        ad = BilibiliAdapter(manager=manager)
        result = ad.search("test", max_results=5)
        assert result.success is False
        assert "频控" in result.error or "风控" in result.error

    def test_search_empty_keyword_returns_failure(self):
        """空关键词：直接失败。"""
        manager = _make_manager()
        ad = BilibiliAdapter(manager=manager)
        result = ad.search("", max_results=5)
        assert result.success is False
        assert "关键词" in result.error

    def test_search_max_results_truncation(self):
        """max_results 限制返回数量。"""
        videos = [{"id": i, "bvid": f"BV{i}", "title": f"视频{i}",
                   "author": f"up{i}", "play": 10, "video_review": 1,
                   "favorites": 0, "pubdate": 1700000000, "duration": "1:00",
                   "description": "", "url": f"https://www.bilibili.com/video/BV{i}"}
                  for i in range(10)]
        manager = _make_manager(search_result={"ok": True, "videos": videos, "total": 10})
        ad = BilibiliAdapter(manager=manager)
        result = ad.search("test", max_results=3)
        assert len(result.notes) == 3

    def test_search_exception_returns_failure(self):
        """管理器抛异常：捕获并返回失败，不崩溃。"""
        manager = MagicMock()
        manager.check_login_status.return_value = {"logged_in": True}
        manager.search_videos.side_effect = RuntimeError("网络中断")
        ad = BilibiliAdapter(manager=manager)
        result = ad.search("test", max_results=5)
        assert result.success is False
        assert "异常" in result.error


class TestBilibiliAdapterTimestamp:

    def test_ts_to_iso_valid(self):
        assert BilibiliAdapter._ts_to_iso(1700000000).startswith("2023-11-14")

    def test_ts_to_iso_none(self):
        assert BilibiliAdapter._ts_to_iso(None) == ""

    def test_ts_to_iso_zero(self):
        assert BilibiliAdapter._ts_to_iso(0) == ""

    def test_ts_to_iso_invalid(self):
        assert BilibiliAdapter._ts_to_iso("not_a_number") == ""


def test_detail_keeps_verified_native_metrics_and_missing_values():
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record

    response = MagicMock()
    response.json.return_value = {"code": 0, "data": {
        "aid": 123, "bvid": "BV1xx", "title": "真实标题", "desc": "真实描述",
        "pubdate": 1700000000, "owner": {"mid": 456, "name": "UP主"},
        "stat": {"view": 120, "danmaku": 7, "coin": 3,
                 "like": 11, "reply": 2, "favorite": 5},
    }}
    adapter = BilibiliAdapter()
    with patch.object(adapter, "_cookie_ok", return_value=True), \
         patch.object(adapter, "_load_cookies", return_value={"test": "redacted"}), \
         patch("requests.get", return_value=response):
        result = adapter.detail("BV1xx")

    assert result.success is True
    note = result.notes[0]
    native = note.raw_data
    assert native["bvid"] == "BV1xx"
    assert native["mid"] == 456
    assert native["pubdate"] == 1700000000
    assert (native["view"], native["danmaku"], native["coin"]) == (120, 7, 3)
    assert (native["like"], native["reply"], native["favorite"]) == (11, 2, 5)
    assert native["share"] is None
    canonical = to_canonical_record(native, "bilibili")
    assert canonical["content_id"] == "BV1xx"
    # Raw Bilibili `mid` remains its native integer. Canonical author identity
    # is exact text, matching opaque IDs on the other supported platforms.
    assert canonical["author_id"] == "456"
    assert canonical["like_count"] == 11
    assert canonical["comment_count"] == 2
    assert canonical["collect_count"] == 5
    assert canonical["share_count"] is None


class TestBilibiliAdapterRegistry:

    def test_registry_can_get_bilibili(self):
        """register_default_adapters 后可获取 bilibili adapter。"""
        from lumenis.adapters.registry import registry, register_default_adapters
        register_default_adapters()
        ad = registry.get("bilibili")
        assert ad is not None
        assert ad.platform_name == "bilibili"
        assert ad.platform_display == "B站"

    def test_adapter_has_circuit_breaker_and_rate_limiter(self):
        """adapter 应继承 BaseAdapter 的熔断/限流能力。"""
        ad = BilibiliAdapter(manager=_make_manager())
        assert ad.breaker is not None
        assert ad.rate_limiter is not None
        assert ad.metrics is not None
