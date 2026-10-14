"""Google/Zhihu browser adapters must use only their registered worker binding."""

from unittest.mock import patch

from lumenis.adapters.base import AdapterResult
from lumenis.adapters.google import GoogleAdapter
from lumenis.adapters.zhihu import ZhihuAdapter


def test_google_without_registered_worker_never_constructs_a_browser():
    adapter = GoogleAdapter()
    with patch("lumenis.adapters.google.configured_readonly_worker_url",
                  side_effect=RuntimeError("READONLY_WORKER_NOT_REGISTERED")), \
            patch("lumenis.adapters.google.HumanBrowser",
                  side_effect=AssertionError("unregistered browser must not be opened")):
        result = adapter.search("research query")

    assert result.success is False
    assert "READONLY_WORKER_NOT_REGISTERED" in result.error


def test_google_registered_worker_is_passed_as_endpoint_without_autostart():
    adapter = GoogleAdapter()
    instances = []

    class FakeBrowser:
        def __init__(self, **kwargs):
            instances.append(kwargs)

        def connect(self):
            raise RuntimeError("isolated connection stop")

    with patch("lumenis.adapters.google.configured_readonly_worker_url",
                  return_value="http://127.0.0.1:23457"), \
            patch("lumenis.adapters.google.HumanBrowser", FakeBrowser):
        result = adapter.search("research query")

    assert result.success is False
    assert instances == [{
        "cdp_url": "http://127.0.0.1:23457",
        "auto_ensure": False,
        "launch_url": "about:blank",
    }]


def test_zhihu_without_registered_worker_uses_existing_api_path():
    adapter = ZhihuAdapter(cookie_string="")
    api_result = AdapterResult(success=True, notes=[], raw_count=0)
    with patch("lumenis.system.collector.adapters.config.get_platform_capabilities",
               return_value={"readonly_worker": None}), \
            patch("lumenis.adapters.human_browser.configured_readonly_worker_url",
                  side_effect=AssertionError("unregistered worker resolver must not be called")), \
            patch("lumenis.adapters.human_browser.HumanBrowser",
                  side_effect=AssertionError("unregistered browser must not be opened")), \
            patch.object(adapter, "_search_api", return_value=api_result) as search_api:
        result = adapter.search("research query")

    assert result is api_result
    search_api.assert_called_once_with("research query", 20)


def test_zhihu_registered_worker_uses_resolved_endpoint_and_never_autostarts():
    adapter = ZhihuAdapter(cookie_string="")
    instances = []

    class FakeBrowser:
        def __init__(self, **kwargs):
            instances.append(kwargs)

        def connect(self):
            raise RuntimeError("isolated connection stop")

        def close(self):
            pass

    with patch("lumenis.system.collector.adapters.config.get_platform_capabilities",
               return_value={"readonly_worker": {"account": "ZHIHU", "port": 23458}}), \
            patch("lumenis.adapters.human_browser.configured_readonly_worker_url",
               return_value="http://127.0.0.1:23458"), \
            patch("lumenis.adapters.human_browser.HumanBrowser", FakeBrowser), \
            patch("lumenis.adapters.cookie_vault.inject_into_context"):
        result = adapter._search_browser("research query", 20)

    assert result.success is False
    assert "isolated connection stop" in result.error
    assert instances == [{
        "cdp_url": "http://127.0.0.1:23458",
        "auto_ensure": False,
        "launch_url": "about:blank",
    }]


def test_zhihu_registered_worker_unconfigured_does_not_fallback_to_api():
    adapter = ZhihuAdapter(cookie_string="")

    with patch("lumenis.system.collector.adapters.config.get_platform_capabilities",
               return_value={"readonly_worker": {"account": "ZHIHU", "port": 23458}}), \
            patch("lumenis.adapters.human_browser.configured_readonly_worker_url",
                  side_effect=RuntimeError("READONLY_WORKER_NOT_CONFIGURED")), \
            patch("lumenis.adapters.human_browser.HumanBrowser",
                  side_effect=AssertionError("unconfigured worker must not connect")), \
            patch("lumenis.adapters.cookie_vault.inject_into_context"), \
            patch.object(adapter, "_search_api",
                         side_effect=AssertionError("must not bypass worker configuration")):
        result = adapter.search("research query")

    assert result.success is False
    assert "READONLY_WORKER_NOT_CONFIGURED" in result.error


def test_zhihu_registered_worker_failure_does_not_fallback_to_api():
    adapter = ZhihuAdapter(cookie_string="")

    class FakeBrowser:
        def __init__(self, **kwargs):
            pass

        def connect(self):
            raise PermissionError("BROWSER_WORKER_PERMISSION_DENIED")

        def close(self):
            pass

    with patch("lumenis.adapters.human_browser.configured_readonly_worker_url",
               return_value="http://127.0.0.1:23458"), \
            patch("lumenis.system.collector.adapters.config.get_platform_capabilities",
                  return_value={"readonly_worker": {"account": "ZHIHU", "port": 23458}}), \
            patch("lumenis.adapters.human_browser.HumanBrowser", FakeBrowser), \
            patch.object(adapter, "_search_api",
                         side_effect=AssertionError("must not bypass browser denial")):
        result = adapter.search("research query")

    assert result.success is False
    assert "BROWSER_WORKER_PERMISSION_DENIED" in result.error


def test_zhihu_registered_worker_challenge_does_not_fallback_to_api():
    adapter = ZhihuAdapter(cookie_string="")

    class FakePage:
        def goto(self, *args, **kwargs):
            pass

        def close(self):
            pass

    class FakeBrowser:
        def __init__(self, **kwargs):
            self._context = object()

        def connect(self):
            pass

        def new_page(self):
            return FakePage()

        def pause(self, *args):
            pass

        def detect_state(self, page):
            from lumenis.adapters.human_browser import PageState
            return PageState.CAPTCHA

        def close(self):
            pass

    with patch("lumenis.adapters.human_browser.configured_readonly_worker_url",
               return_value="http://127.0.0.1:23458"), \
            patch("lumenis.system.collector.adapters.config.get_platform_capabilities",
                  return_value={"readonly_worker": {"account": "ZHIHU", "port": 23458}}), \
            patch("lumenis.adapters.human_browser.HumanBrowser", FakeBrowser), \
            patch("lumenis.adapters.cookie_vault.inject_into_context"), \
            patch.object(adapter, "_search_api",
                         side_effect=AssertionError("must not bypass challenge")):
        result = adapter.search("research query")

    assert result.success is False
    assert result.error == "知乎页面状态=CAPTCHA"
