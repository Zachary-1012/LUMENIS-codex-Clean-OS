# -*- coding: utf-8 -*-
"""主链路 detail/comments/creator 委托 v4 引擎测试（全 mock，不实际联网/启动浏览器）"""
import sys, os
import pytest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from platform_adapters.base import CollectionStatus


def _make_v4_result(success=True, notes=None, error="", raw_count=1, duration=0.2):
    from v4_upgrade.adapters.base import AdapterResult
    return AdapterResult(success=success, notes=notes or [], error=error,
                         raw_count=raw_count, duration_seconds=duration)


def _make_note(title="t", author="a", url="u", likes=1, comments=2, publish_date="2024-01-01", raw_id="x"):
    n = MagicMock()
    n.title = title; n.content = "c"; n.url = url
    n.author = author; n.author_id = "uid"; n.publish_date = publish_date
    n.likes = likes; n.comments = comments; n.collects = 0; n.shares = 0
    n.cover = ""; n.source_platform = "test"
    n.raw_data = {"id": raw_id, "bvid": raw_id, "mid": raw_id, "aweme_id": raw_id}
    return n


class TestBilibiliDetailCommentsCreator:

    @patch("platform_adapters.bilibili.BilibiliAdapter._load_backend")
    def test_detail_delegates_v4(self, mock_load):
        mock_load.return_value.detail.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.bilibili import BilibiliAdapter
        r = BilibiliAdapter().detail("BV1xx")
        assert r.status == CollectionStatus.SUCCESS
        assert len(r.items) == 1
        mock_load.return_value.detail.assert_called_once_with(bvid="BV1xx")

    @patch("platform_adapters.bilibili.BilibiliAdapter._load_backend")
    def test_comments_delegates_v4(self, mock_load):
        mock_load.return_value.comments.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.bilibili import BilibiliAdapter
        r = BilibiliAdapter().comments("BV1xx", max_comments=15)
        assert r.status == CollectionStatus.SUCCESS
        assert r.items == []
        assert r.comments[0]["content"] == "c"
        mock_load.return_value.comments.assert_called_once()

    @patch("platform_adapters.bilibili.BilibiliAdapter._load_backend")
    def test_creator_delegates_v4(self, mock_load):
        mock_load.return_value.creator.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.bilibili import BilibiliAdapter
        r = BilibiliAdapter().creator("123")
        assert r.status == CollectionStatus.SUCCESS
        mock_load.return_value.creator.assert_called_once_with(mid="123")


class TestWeiboDetailCommentsCreator:

    @patch("platform_adapters.weibo.WeiboAdapter._load_backend")
    def test_detail_delegates_v4(self, mock_load):
        mock_load.return_value.detail.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.weibo import WeiboAdapter
        r = WeiboAdapter().detail("mid123")
        assert r.status == CollectionStatus.SUCCESS
        mock_load.return_value.detail.assert_called_once_with(mid="mid123")

    @patch("platform_adapters.weibo.WeiboAdapter._load_backend")
    def test_comments_delegates_v4(self, mock_load):
        mock_load.return_value.comments.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.weibo import WeiboAdapter
        r = WeiboAdapter().comments("mid123")
        assert r.status == CollectionStatus.SUCCESS
        assert r.items == []
        assert r.comments[0]["content"] == "c"

    @patch("platform_adapters.weibo.WeiboAdapter._load_backend")
    def test_creator_delegates_v4(self, mock_load):
        mock_load.return_value.creator.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.weibo import WeiboAdapter
        r = WeiboAdapter().creator("uid123")
        assert r.status == CollectionStatus.SUCCESS
        mock_load.return_value.creator.assert_called_once_with(uid="uid123")


class TestZhihuDetailCommentsCreator:

    @patch("platform_adapters.zhihu.ZhihuAdapter._load_backend")
    def test_detail_delegates_v4(self, mock_load):
        mock_load.return_value.detail.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.zhihu import ZhihuAdapter
        r = ZhihuAdapter().detail("ans123", content_type="answer")
        assert r.status == CollectionStatus.SUCCESS
        mock_load.return_value.detail.assert_called_once()

    @patch("platform_adapters.zhihu.ZhihuAdapter._load_backend")
    def test_comments_delegates_v4(self, mock_load):
        mock_load.return_value.comments.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.zhihu import ZhihuAdapter
        r = ZhihuAdapter().comments("ans123")
        assert r.status == CollectionStatus.SUCCESS

    @patch("platform_adapters.zhihu.ZhihuAdapter._load_backend")
    def test_creator_delegates_v4(self, mock_load):
        mock_load.return_value.creator.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.zhihu import ZhihuAdapter
        r = ZhihuAdapter().creator("user123")
        assert r.status == CollectionStatus.SUCCESS
        mock_load.return_value.creator.assert_called_once_with(user_id="user123")


class TestDouyinDetailCommentsCreator:

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_detail_delegates_v4(self, mock_load):
        mock_load.return_value.detail.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.douyin import DouyinAdapter
        r = DouyinAdapter().detail("aweme123")
        assert r.status == CollectionStatus.SUCCESS
        mock_load.return_value.detail.assert_called_once_with(aweme_id="aweme123")

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_comments_delegates_v4(self, mock_load):
        mock_load.return_value.comments.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.douyin import DouyinAdapter
        r = DouyinAdapter().comments("aweme123")
        assert r.status == CollectionStatus.SUCCESS
        assert r.items == []
        assert r.comments[0]["content"] == "c"

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_creator_delegates_v4(self, mock_load):
        mock_load.return_value.creator.return_value = _make_v4_result(notes=[_make_note()])
        from platform_adapters.douyin import DouyinAdapter
        r = DouyinAdapter().creator("sec123")
        assert r.status == CollectionStatus.SUCCESS
        mock_load.return_value.creator.assert_called_once_with(sec_uid="sec123")


class TestCapabilityMatrix:
    """验证 config.py 中所有 secondary 平台的 detail/comments/creator 均为 True"""

    def test_all_secondary_full_capability(self):
        from platform_adapters.config import PLATFORM_CAPABILITIES
        for p in ["douyin", "bilibili", "weibo", "zhihu", "instagram"]:
            cap = PLATFORM_CAPABILITIES[p]
            assert cap["search"] is True, f"{p} search should be True"
            assert cap["detail"] is True, f"{p} detail should be True"
            assert cap["comments"] is True, f"{p} comments should be True"
            assert cap["creator"] is True, f"{p} creator should be True"


def test_search_stops_on_risk_and_never_returns_stale_fallback():
    from v4_upgrade.adapters.base import AdapterResult, BaseAdapter, CollectedNote
    from platform_adapters.bilibili import BilibiliAdapter

    class RiskBackend(BaseAdapter):
        platform_name = "bilibili"
        platform_display = "B站"

        def __init__(self):
            super().__init__(rate_per_minute=600)
            self.calls = 0
            self._last_result = AdapterResult(
                success=True,
                notes=[CollectedNote(title="stale item")],
                raw_count=1,
            )

        def search(self, keyword, max_results=20):
            self.calls += 1
            return AdapterResult(success=False, error="captcha verify required")

    backend = RiskBackend()
    result = BilibiliAdapter(backend=backend).search("广州太古汇")

    assert backend.calls == 1
    assert result.status == CollectionStatus.RISK_WARNING
    assert result.items == []
