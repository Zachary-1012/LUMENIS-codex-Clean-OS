"""Google/Zhihu browser adapters must use only their registered worker binding."""

import copy
import sys
from types import SimpleNamespace
from unittest.mock import patch

from lumenis.adapters.base import AdapterResult
from lumenis.adapters.google import GoogleAdapter
from lumenis.adapters.zhihu import ZhihuAdapter


def test_google_without_registered_worker_never_constructs_a_browser():
    adapter = GoogleAdapter()
    with patch("lumenis.adapters.google.registered_browser_worker_spec",
                  side_effect=RuntimeError("READONLY_WORKER_NOT_REGISTERED")), \
            patch("lumenis.adapters.google.HumanBrowser",
                  side_effect=AssertionError("unregistered browser must not be opened")):
        result = adapter.search("research query")

    assert result.success is False
    assert "READONLY_WORKER_NOT_REGISTERED" in result.error


def test_google_registered_worker_is_verified_without_environment_opt_in_or_autostart(
        monkeypatch, tmp_path):
    adapter = GoogleAdapter()
    instances = []
    profile = str(tmp_path / "private" / "profiles" / "google-readonly")
    worker = {"platform": "google", "account": "GOOGLE_READONLY",
              "port": 9230, "profile": profile}
    monkeypatch.delenv("GOOGLE_CDP_URL", raising=False)
    monkeypatch.delenv("GOOGLE_READONLY_CDP_URL", raising=False)
    monkeypatch.delenv("GOOGLE_READONLY_LOCAL_WORKER_ENABLED", raising=False)
    monkeypatch.delenv("GOOGLE_READONLY_LOCAL_WORKER_ACCOUNT", raising=False)

    class FakeBrowser:
        def __init__(self, **kwargs):
            instances.append(kwargs)

        def connect(self):
            raise RuntimeError("isolated connection stop")

    with patch("lumenis.adapters.google.registered_browser_worker_spec",
               return_value=worker) as worker_spec, \
            patch("cdp_helper.registered_cdp_browser_for_port",
                  return_value="chrome") as verify_worker, \
            patch("lumenis.adapters.google.HumanBrowser", FakeBrowser):
        result = adapter.search("research query")

    assert result.success is False
    assert instances == [{
        "cdp_url": "http://127.0.0.1:9230",
        "auto_ensure": False,
        "launch_url": "about:blank",
    }]
    worker_spec.assert_called_once_with("google")
    verify_worker.assert_called_once_with(9230, profile, headless=True)


def test_google_unverified_worker_never_connects_or_falls_back():
    adapter = GoogleAdapter()
    worker = {"platform": "google", "account": "GOOGLE_READONLY",
              "port": 9230, "profile": "D:/isolated/google-readonly"}
    with patch("lumenis.adapters.google.registered_browser_worker_spec",
               return_value=worker), \
            patch("cdp_helper.registered_cdp_browser_for_port", return_value=None), \
            patch("lumenis.adapters.google.HumanBrowser",
                  side_effect=AssertionError("unverified worker must not connect")):
        result = adapter.search("research query")

    assert result.success is False
    assert "GOOGLE_BACKGROUND_WORKER_UNAVAILABLE_OR_UNVERIFIED" in result.error


def test_google_worker_is_manual_only_and_uses_unique_isolated_registration():
    from lumenis.system.collector.adapters.config import PLATFORM_CAPABILITIES

    google = PLATFORM_CAPABILITIES["google"]
    worker = google["readonly_worker"]
    assert google["enabled"] is False
    assert google["manual_collection_enabled"] is True
    assert google["collection_mode"] == "human_triggered_read_only"
    assert google["search"] is True
    assert worker == {"account": "GOOGLE_READONLY", "port": 9230,
                      "profile": "google-readonly", "env_prefix": "GOOGLE_READONLY"}
    bindings = [config["readonly_worker"] for config in PLATFORM_CAPABILITIES.values()
                if isinstance(config, dict) and isinstance(config.get("readonly_worker"), dict)]
    assert sum(int(item["port"]) == 9230 for item in bindings) == 1
    assert sum(str(item["account"]).casefold() == "google_readonly".casefold()
               for item in bindings) == 1
    assert sum(str(item["profile"]).casefold() == "google-readonly".casefold()
               for item in bindings) == 1


def test_registered_cdp_resolver_accepts_only_unique_configured_worker_port(
        monkeypatch, tmp_path):
    import cdp_helper
    from lumenis.adapters import cookie_vault
    from lumenis.system.collector.adapters import config

    monkeypatch.setattr(cookie_vault, "_current_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cdp_helper, "_registered_xhs_binding", lambda *_args: None)
    monkeypatch.setattr(cdp_helper, "resolve_registered_xhs_worker",
                        lambda **_kwargs: {"available": False})
    expected = str(tmp_path / "private" / "profiles" / "google-readonly")

    assert cdp_helper.registered_cdp_profile_for_port(9230) == expected
    assert cdp_helper.registered_cdp_profile_for_port(9225) == str(
        tmp_path / "private" / "profiles" / "douyin-readonly")
    assert cdp_helper._profile_binding_allowed(9230, expected) is True
    assert cdp_helper._profile_binding_allowed(
        9230, str(tmp_path / "private" / "profiles" / "other")) is False
    assert cdp_helper.registered_cdp_profile_for_port(9231) is None
    assert cdp_helper.registered_cdp_profile_for_port(9222) is None
    assert cdp_helper.registered_cdp_profile_for_port(9223) is None
    assert cdp_helper._profile_binding_allowed(9222, expected) is False
    assert cdp_helper._profile_binding_allowed(9223, expected) is False

    duplicate = copy.deepcopy(config.PLATFORM_CAPABILITIES)
    duplicate["another_google_worker"] = {
        "readonly_worker": {"account": "OTHER", "port": 9230,
                             "profile": "other-profile"}}
    monkeypatch.setattr(config, "PLATFORM_CAPABILITIES", duplicate)
    assert cdp_helper.registered_cdp_profile_for_port(9230) is None

    duplicate = copy.deepcopy(config.PLATFORM_CAPABILITIES)
    duplicate.pop("another_google_worker")
    duplicate["duplicate_google_account"] = {
        "readonly_worker": {"account": "GOOGLE_READONLY", "port": 9231,
                             "profile": "other-profile"}}
    monkeypatch.setattr(config, "PLATFORM_CAPABILITIES", duplicate)
    assert cdp_helper.registered_cdp_profile_for_port(9230) is None

    duplicate = copy.deepcopy(config.PLATFORM_CAPABILITIES)
    duplicate.pop("duplicate_google_account")
    duplicate["duplicate_google_profile"] = {
        "readonly_worker": {"account": "OTHER", "port": 9231,
                             "profile": "google-readonly"}}
    monkeypatch.setattr(config, "PLATFORM_CAPABILITIES", duplicate)
    assert cdp_helper.registered_cdp_profile_for_port(9230) is None

    invalid_path = copy.deepcopy(config.PLATFORM_CAPABILITIES)
    invalid_path.pop("duplicate_google_profile")
    invalid_path["google"]["readonly_worker"]["profile"] = "../google-readonly"
    monkeypatch.setattr(config, "PLATFORM_CAPABILITIES", invalid_path)
    assert cdp_helper.registered_cdp_profile_for_port(9230) is None

    xhs_profile = str(tmp_path / "private" / "profiles" / "xhs-hk")
    monkeypatch.setattr(cdp_helper, "_registered_xhs_binding",
                        lambda *_args: {"profile": xhs_profile})
    monkeypatch.setattr(cdp_helper, "resolve_registered_xhs_worker",
                        lambda **_kwargs: {"available": True, "port": 45678,
                                           "profile": xhs_profile, "browser": "edge"})
    assert cdp_helper.registered_cdp_profile_for_port(0) == xhs_profile
    assert cdp_helper.registered_cdp_profile_for_port(45678) == xhs_profile
    assert cdp_helper._profile_binding_allowed(0, xhs_profile, browser="edge") is True
    assert cdp_helper._profile_binding_allowed(
        45678, xhs_profile, browser="edge") is True
    assert cdp_helper.registered_cdp_browser_for_port(
        0, xhs_profile, headless=True) == "edge"


def test_registered_cdp_browser_requires_exact_registered_profile_pid_and_headless(
        monkeypatch, tmp_path):
    import cdp_helper
    from lumenis.adapters import cookie_vault

    monkeypatch.setattr(cookie_vault, "_current_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(cdp_helper, "_registered_xhs_binding", lambda *_args: None)
    monkeypatch.setattr(cdp_helper, "resolve_registered_xhs_worker",
                        lambda **_kwargs: {"available": False})
    profile = str(tmp_path / "private" / "profiles" / "google-readonly")
    command = ["chrome.exe", "--remote-debugging-port=9230",
               "--remote-debugging-address=127.0.0.1",
               f"--user-data-dir={profile}", "--headless=new"]

    class FakeProcess:
        def name(self):
            return "chrome.exe"

        def create_time(self):
            return 123.0

        def cmdline(self):
            return list(command)

    monkeypatch.setitem(sys.modules, "psutil", SimpleNamespace(Process=lambda _pid: FakeProcess()))
    monkeypatch.setattr(cdp_helper, "_cdp_listener_pids", lambda _port: ({321}, True))
    assert cdp_helper.registered_cdp_browser_for_port(
        9230, profile, headless=True) == "chrome"

    legacy_profile = str(tmp_path / "private" / "profiles" / "douyin-readonly")
    command[:] = ["chrome.exe", "--remote-debugging-port=9225",
                  "--remote-debugging-address=127.0.0.1",
                  f"--user-data-dir={legacy_profile}", "--headless=new"]
    assert cdp_helper.registered_cdp_browser_for_port(
        9225, legacy_profile, headless=True) == "chrome"

    command.remove("--headless=new")
    assert cdp_helper.registered_cdp_browser_for_port(
        9225, legacy_profile, headless=True) is None


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
