# -*- coding: utf-8 -*-
"""
抖音主链路 adapter 单元测试（全 mock，不实际启动浏览器）。

测试当前生产契约：
- search 仍通过 v4 AdapterResult 映射六态；
- browser worker 必须显式配置，禁止把本机 cookie/file presence 当成远端会话健康；
- provider 初始化异常按 PROVIDER_UNAVAILABLE fail-closed，且不向用户泄露内部异常正文。
"""
import sys, os
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


def _search_backend(result):
    """构造只走 search() 的 backend；避免 MagicMock 虚构 breaker/safe_collect 能力。"""
    backend = MagicMock()
    backend.breaker = None
    backend.safe_collect = None
    backend.search.return_value = result
    return backend


class TestDouyinMainAdapterSearch:

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_search_success(self, mock_load):
        mock_backend = _search_backend(_make_v4_result(
            success=True, notes=[_make_v4_note()], raw_count=1))
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
        mock_load.return_value = _search_backend(
            _make_v4_result(success=True, notes=[], raw_count=0))
        result = DouyinAdapter().search("空结果")
        assert result.status == CollectionStatus.NO_NEW_DATA

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_search_session_expired(self, mock_load):
        mock_load.return_value = _search_backend(_make_v4_result(
            success=False, error="登录态失效，请重新登录"))
        result = DouyinAdapter().search("测试")
        assert result.status == CollectionStatus.SESSION_EXPIRED

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_search_risk_warning(self, mock_load):
        mock_load.return_value = _search_backend(_make_v4_result(
            success=False, error="风控验证，请稍后再试"))
        result = DouyinAdapter().search("测试")
        assert result.status == CollectionStatus.RISK_WARNING

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_search_collect_error(self, mock_load):
        mock_load.return_value = _search_backend(_make_v4_result(
            success=False, error="网络连接超时"))
        result = DouyinAdapter().search("测试")
        assert result.status == CollectionStatus.COLLECT_ERROR

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    def test_search_exception_is_provider_unavailable_without_internal_leak(self, mock_load):
        mock_load.side_effect = RuntimeError("引擎加载失败")
        result = DouyinAdapter().search("测试")
        assert result.status == CollectionStatus.PROVIDER_UNAVAILABLE
        assert result.metadata["error_type"] == "RuntimeError"
        assert "引擎加载失败" not in result.message


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

    @patch("platform_adapters.douyin.DouyinAdapter._load_backend")
    @patch("v4_upgrade.adapters.human_browser.is_cdp_url_open", return_value=True)
    @patch("v4_upgrade.adapters.douyin._configured_browser_worker_url",
           return_value="https://browser-worker.example")
    def test_health_worker_reachable_requires_runtime_verification(
            self, mock_url, mock_open, mock_load):
        mock_load.return_value = MagicMock()
        result = DouyinAdapter().health_check()
        assert result.status == CollectionStatus.NEED_VERIFY
        assert result.metadata["endpoint_configured"] is True
        assert result.metadata["session_state"] == "worker_reachable_unverified"

    @patch("v4_upgrade.adapters.douyin._configured_browser_worker_url",
           side_effect=RuntimeError("DOUYIN_CDP_URL is not configured"))
    def test_health_without_worker_configuration_is_not_configured(self, mock_url):
        result = DouyinAdapter().health_check()
        assert result.status == CollectionStatus.NOT_CONFIGURED
        assert result.metadata["endpoint_configured"] is False

    @patch("v4_upgrade.adapters.human_browser.is_cdp_url_open", return_value=False)
    @patch("v4_upgrade.adapters.douyin._configured_browser_worker_url",
           return_value="https://browser-worker.example")
    def test_health_configured_but_unreachable_is_provider_unavailable(self, mock_url, mock_open):
        result = DouyinAdapter().health_check()
        assert result.status == CollectionStatus.PROVIDER_UNAVAILABLE
        assert result.metadata["endpoint_configured"] is True


class TestDouyinMainAdapterRegistry:

    def test_registry_has_douyin(self):
        from platform_adapters import get_adapter
        ad = get_adapter("douyin")
        assert ad is not None
        assert ad.platform == "douyin"
        assert ad.enabled is False  # 默认关闭，需运行时检查
