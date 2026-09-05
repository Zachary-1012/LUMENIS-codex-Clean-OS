# -*- coding: utf-8 -*-
"""
抖音主链路 adapter 单元测试（全 mock，不实际启动浏览器）
"""
import sys, os
import pytest
from unittest.mock import MagicMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from platform_adapters.douyin import DouyinAdapter
from platform_adapters.base import CollectionStatus


def _make_v4_note(title="测试视频", author="up主", url="https://v.douyin.com/abc/",
                  likes=100, comments=10, publish_date="2024-09-03T12:00:00+08:00"):
    note = MagicMock()
    note.title = title
    note.content = "视频描述"
    note.url = url
    note.author = author
    note.author_id = "123"
    note.publish_date = publish_date
    note.likes = likes
    note.comments = comments
    note.collects = 5
    note.shares = 3
    note.cover = ""
    note.source_platform = "douyin"
    note.raw_data = {"aweme_id": "777", "engine": "test"}
    return note


def _make_v4_result(success=True, notes=None, error="", raw_count=0, duration=0.5):
    from v4_upgrade.adapters.base import AdapterResult
    return AdapterResult(success=success, notes=notes or [], error=error,
                         raw_count=raw_count, duration_seconds=duration)


class TestDouyinMainAdapterSearch:

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_search_success(self, mock_load):
        mock_backend = MagicMock()
        mock_backend.search.return_value = _make_v4_result(
            success=True, notes=[_make_v4_note()], raw_count=1)
        mock_load.return_value = mock_backend

        ad = DouyinAdapter()
        result = ad.search("测试", max_results=10)

        assert result.status == CollectionStatus.SUCCESS
        assert result.platform == "douyin"
        assert len(result.items) == 1
        assert result.items[0]["author_nickname"] == "up主"
        assert result.items[0]["likes"] == 100
        assert result.raw_count == 1
        mock_backend.search.assert_called_once_with("测试", max_results=10)

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_search_no_new_data(self, mock_load):
        mock_backend = MagicMock()
        mock_backend.search.return_value = _make_v4_result(success=True, notes=[], raw_count=0)
        mock_load.return_value = mock_backend

        ad = DouyinAdapter()
        result = ad.search("空结果")
        assert result.status == CollectionStatus.NO_NEW_DATA

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_search_session_expired(self, mock_load):
        mock_backend = MagicMock()
        mock_backend.search.return_value = _make_v4_result(
            success=False, error="登录态失效，请重新登录")
        mock_load.return_value = mock_backend

        ad = DouyinAdapter()
        result = ad.search("测试")
        assert result.status == CollectionStatus.SESSION_EXPIRED

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_search_risk_warning(self, mock_load):
        mock_backend = MagicMock()
        mock_backend.search.return_value = _make_v4_result(
            success=False, error="风控验证，请稍后再试")
        mock_load.return_value = mock_backend

        ad = DouyinAdapter()
        result = ad.search("测试")
        assert result.status == CollectionStatus.RISK_WARNING

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_search_collect_error(self, mock_load):
        mock_backend = MagicMock()
        mock_backend.search.return_value = _make_v4_result(
            success=False, error="网络连接超时")
        mock_load.return_value = mock_backend

        ad = DouyinAdapter()
        result = ad.search("测试")
        assert result.status == CollectionStatus.COLLECT_ERROR

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_search_exception_handled(self, mock_load):
        mock_load.side_effect = RuntimeError("引擎加载失败")
        ad = DouyinAdapter()
        result = ad.search("测试")
        assert result.status == CollectionStatus.COLLECT_ERROR
        assert "引擎加载失败" in result.message


class TestDouyinMainAdapterDetailCommentsCreator:

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_detail_delegates_v4(self, mock_load):
        from v4_upgrade.adapters.base import AdapterResult
        mock_load.return_value.detail.return_value = AdapterResult(success=True, notes=[], raw_count=0)
        ad = DouyinAdapter()
        result = ad.detail("aweme123")
        assert result.status == CollectionStatus.NO_NEW_DATA
        mock_load.return_value.detail.assert_called_once_with(aweme_id="aweme123")

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_comments_delegates_v4(self, mock_load):
        from v4_upgrade.adapters.base import AdapterResult
        mock_load.return_value.comments.return_value = AdapterResult(success=True, notes=[], raw_count=0)
        ad = DouyinAdapter()
        result = ad.comments("aweme123")
        assert result.status == CollectionStatus.NO_NEW_DATA
        mock_load.return_value.comments.assert_called_once()

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_creator_delegates_v4(self, mock_load):
        from v4_upgrade.adapters.base import AdapterResult
        mock_load.return_value.creator.return_value = AdapterResult(success=True, notes=[], raw_count=0)
        ad = DouyinAdapter()
        result = ad.creator("sec123")
        assert result.status == CollectionStatus.NO_NEW_DATA
        mock_load.return_value.creator.assert_called_once_with(sec_uid="sec123")


class TestDouyinMainAdapterHealth:

    @patch("os.path.exists", return_value=True)
    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_health_ok(self, mock_load, mock_exists):
        mock_load.return_value = MagicMock()
        ad = DouyinAdapter()
        result = ad.health_check()
        assert result.status == CollectionStatus.SUCCESS
        assert result.metadata["cookie_exists"] is True

    @patch("os.path.exists", return_value=False)
    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_health_no_cookie(self, mock_load, mock_exists):
        mock_load.return_value = MagicMock()
        ad = DouyinAdapter()
        result = ad.health_check()
        assert result.status == CollectionStatus.SESSION_EXPIRED


class TestDouyinMainAdapterRegistry:

    def test_registry_has_douyin(self):
        from platform_adapters import get_adapter
        ad = get_adapter("douyin")
        assert ad is not None
        assert ad.platform == "douyin"
        assert ad.enabled is False  # 默认关闭，需运行时检查
