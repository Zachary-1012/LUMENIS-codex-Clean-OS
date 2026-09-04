# -*- coding: utf-8 -*-
"""B站/微博/知乎主链路 adapter 单元测试（全 mock，不实际联网）"""
import sys, os
import pytest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from platform_adapters.base import CollectionStatus


def _make_v4_note(title="测试", author="作者", url="https://example.com/1",
                  likes=10, comments=2, publish_date="2024-09-03T12:00:00+08:00",
                  raw_id="123"):
    note = MagicMock()
    note.title = title
    note.content = "内容"
    note.url = url
    note.author = author
    note.author_id = "uid1"
    note.publish_date = publish_date
    note.likes = likes
    note.comments = comments
    note.collects = 1
    note.shares = 0
    note.cover = ""
    note.source_platform = "test"
    note.raw_data = {"id": raw_id, "bvid": raw_id}
    return note


def _make_v4_result(success=True, notes=None, error="", raw_count=0, duration=0.3):
    from v4_upgrade.adapters.base import AdapterResult
    return AdapterResult(success=success, notes=notes or [], error=error,
                         raw_count=raw_count, duration_seconds=duration)


class TestBilibiliMainAdapter:

    @patch("platform_adapters.bilibili.BilibiliAdapter._load_backend")
    def test_search_success(self, mock_load):
        mock_load.return_value.search.return_value = _make_v4_result(
            success=True, notes=[_make_v4_note()], raw_count=1)
        from platform_adapters.bilibili import BilibiliAdapter
        ad = BilibiliAdapter()
        r = ad.search("测试", max_results=10)
        assert r.status == CollectionStatus.SUCCESS
        assert len(r.items) == 1
        assert r.items[0]["author_nickname"] == "作者"

    @patch("platform_adapters.bilibili.BilibiliAdapter._load_backend")
    def test_search_session_expired(self, mock_load):
        mock_load.return_value.search.return_value = _make_v4_result(
            success=False, error="登录态失效")
        from platform_adapters.bilibili import BilibiliAdapter
        ad = BilibiliAdapter()
        assert ad.search("x").status == CollectionStatus.SESSION_EXPIRED

    @patch("platform_adapters.bilibili.BilibiliAdapter._load_backend")
    def test_search_risk_warning(self, mock_load):
        mock_load.return_value.search.return_value = _make_v4_result(
            success=False, error="风控验证 wbi 签名失败")
        from platform_adapters.bilibili import BilibiliAdapter
        ad = BilibiliAdapter()
        assert ad.search("x").status == CollectionStatus.RISK_WARNING

    def test_detail_not_implemented(self):
        from platform_adapters.bilibili import BilibiliAdapter
        assert BilibiliAdapter().detail("1").status == CollectionStatus.COLLECT_ERROR

    def test_registry(self):
        from platform_adapters import get_adapter
        ad = get_adapter("bilibili")
        assert ad is not None and ad.platform == "bilibili"


class TestWeiboMainAdapter:

    @patch("platform_adapters.weibo.WeiboAdapter._load_backend")
    def test_search_success(self, mock_load):
        mock_load.return_value.search.return_value = _make_v4_result(
            success=True, notes=[_make_v4_note()], raw_count=1)
        from platform_adapters.weibo import WeiboAdapter
        ad = WeiboAdapter()
        r = ad.search("测试")
        assert r.status == CollectionStatus.SUCCESS
        assert len(r.items) == 1

    @patch("platform_adapters.weibo.WeiboAdapter._load_backend")
    def test_search_no_new_data(self, mock_load):
        mock_load.return_value.search.return_value = _make_v4_result(success=True, notes=[])
        from platform_adapters.weibo import WeiboAdapter
        assert WeiboAdapter().search("x").status == CollectionStatus.NO_NEW_DATA

    @patch("platform_adapters.weibo.WeiboAdapter._load_backend")
    def test_search_collect_error(self, mock_load):
        mock_load.return_value.search.return_value = _make_v4_result(
            success=False, error="网络超时")
        from platform_adapters.weibo import WeiboAdapter
        assert WeiboAdapter().search("x").status == CollectionStatus.COLLECT_ERROR

    def test_comments_not_implemented(self):
        from platform_adapters.weibo import WeiboAdapter
        assert WeiboAdapter().comments("1").status == CollectionStatus.COLLECT_ERROR

    def test_registry(self):
        from platform_adapters import get_adapter
        assert get_adapter("weibo") is not None


class TestZhihuMainAdapter:

    @patch("platform_adapters.zhihu.ZhihuAdapter._load_backend")
    def test_search_success(self, mock_load):
        mock_load.return_value.search.return_value = _make_v4_result(
            success=True, notes=[_make_v4_note()], raw_count=1)
        from platform_adapters.zhihu import ZhihuAdapter
        ad = ZhihuAdapter()
        r = ad.search("测试")
        assert r.status == CollectionStatus.SUCCESS
        assert len(r.items) == 1

    @patch("platform_adapters.zhihu.ZhihuAdapter._load_backend")
    def test_search_risk_warning(self, mock_load):
        mock_load.return_value.search.return_value = _make_v4_result(
            success=False, error="429 频控")
        from platform_adapters.zhihu import ZhihuAdapter
        assert ZhihuAdapter().search("x").status == CollectionStatus.RISK_WARNING

    @patch("platform_adapters.zhihu.ZhihuAdapter._load_backend")
    def test_search_exception(self, mock_load):
        mock_load.side_effect = RuntimeError("引擎崩溃")
        from platform_adapters.zhihu import ZhihuAdapter
        r = ZhihuAdapter().search("x")
        assert r.status == CollectionStatus.COLLECT_ERROR
        assert "引擎崩溃" in r.message

    def test_creator_not_implemented(self):
        from platform_adapters.zhihu import ZhihuAdapter
        assert ZhihuAdapter().creator("1").status == CollectionStatus.COLLECT_ERROR

    def test_health_no_cookie_required(self):
        from platform_adapters.zhihu import ZhihuAdapter
        r = ZhihuAdapter().health_check()
        # 知乎公开搜索无需 cookie，引擎就绪即 SUCCESS
        assert r.status in (CollectionStatus.SUCCESS, CollectionStatus.COLLECT_ERROR)

    def test_registry(self):
        from platform_adapters import get_adapter
        assert get_adapter("zhihu") is not None
