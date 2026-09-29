"""Provider health and session-boundary tests for the canonical browser runtime."""
import sys
import types
import pytest

from lumenis.system.browser.runtime.adapters.cdp_adapter import CDPAdapter
from lumenis.system.browser.runtime.adapters.playwright_adapter import PlaywrightAdapter


class FakePage:
    def __init__(self):
        self.closed = False
        self.url = "https://www.rednote.com/explore?token=private-token"

    def set_default_timeout(self, timeout):
        self.timeout = timeout

    def is_closed(self):
        return self.closed

    def title(self):
        return "Private page title"


class FakeContext:
    def __init__(self, browser):
        self._browser = browser
        self.pages = [FakePage()]
        self.close_calls = 0

    def browser(self):
        return self._browser

    def close(self):
        self.close_calls += 1


class FakeBrowser:
    def __init__(self):
        self.connected = True
        self.close_calls = 0
        self.contexts = [FakeContext(self)]

    def is_connected(self):
        return self.connected

    def close(self):
        self.close_calls += 1
        self.connected = False


class FakeChromium:
    def __init__(self, browser=None, error=None):
        self.browser = browser or FakeBrowser()
        self.error = error
        self.calls = []

    def connect_over_cdp(self, endpoint, **kwargs):
        self.calls.append((endpoint, kwargs))
        if self.error:
            raise RuntimeError(self.error)
        return self.browser


def install_fake_playwright(monkeypatch, chromium):
    class FakeRuntime:
        def __init__(self):
            self.chromium = chromium

        def stop(self):
            pass

    class FakeStarter:
        def start(self):
            return FakeRuntime()

    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: FakeStarter()
    package = types.ModuleType("playwright")
    package.sync_api = sync_api
    monkeypatch.setitem(sys.modules, "playwright", package)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)


def test_playwright_health_reports_disconnect_without_endpoint_or_session_data(monkeypatch):
    browser = FakeBrowser()
    chromium = FakeChromium(browser=browser)
    install_fake_playwright(monkeypatch, chromium)
    endpoint = "http://127.0.0.1:9223/devtools/browser/debugger-secret"

    adapter = PlaywrightAdapter(cdp_url=endpoint)
    assert chromium.calls == [(endpoint, {"timeout": 15000})]
    assert adapter.health()["state"] == "available"

    browser.connected = False
    disconnected = adapter.health()
    assert disconnected["state"] == "unavailable"
    assert disconnected["diagnostics"]["connection_state"] == "disconnected"
    assert "debugger-secret" not in str(disconnected)
    assert "private-token" not in str(disconnected)
    assert "cdp_url" not in str(disconnected)

    adapter.close()
    assert browser.close_calls == 1
    assert browser.contexts[0].close_calls == 0
    assert adapter.health()["diagnostics"]["error_code"] == "adapter_closed"


def test_playwright_failed_connection_is_unavailable_and_redacted(monkeypatch):
    endpoint = "ws://127.0.0.1:9223/devtools/browser/debugger-secret"
    chromium = FakeChromium(error=f"connection refused at {endpoint} token=private-token")
    install_fake_playwright(monkeypatch, chromium)

    health = PlaywrightAdapter(cdp_url=endpoint).health()
    assert health["state"] == "unavailable"
    assert health["diagnostics"]["error_code"] == "connection_unavailable"
    assert "debugger-secret" not in str(health)
    assert "private-token" not in str(health)


def test_playwright_refuses_remote_or_credential_bearing_cdp_urls(monkeypatch):
    chromium = FakeChromium()
    install_fake_playwright(monkeypatch, chromium)

    health = PlaywrightAdapter(
        cdp_url="https://user:password@remote.example/devtools/browser/secret?token=private"
    ).health()
    assert health["state"] == "unavailable"
    assert chromium.calls == []
    assert "remote.example" not in str(health)
    assert "password" not in str(health)
    assert "private" not in str(health)

    mainland_endpoint = "http://127.0.0.1:9222/devtools/browser/private-profile"
    blocked_health = PlaywrightAdapter(cdp_url=mainland_endpoint).health()
    assert blocked_health["state"] == "unavailable"
    assert chromium.calls == []
    assert "private-profile" not in str(blocked_health)


def test_playwright_does_not_mix_cdp_with_local_cookie_or_profile_state(monkeypatch):
    chromium = FakeChromium()
    install_fake_playwright(monkeypatch, chromium)
    storage_path = r"C:\private\storage-state.json"
    profile_path = r"C:\private\browser-profile"

    health = PlaywrightAdapter(
        cdp_url="http://127.0.0.1:9223",
        storage_state=storage_path,
        user_data_dir=profile_path,
    ).health()

    assert health["state"] == "unavailable"
    assert chromium.calls == []
    assert storage_path not in str(health)
    assert profile_path not in str(health)


def test_cdp_health_returns_shared_shape_without_page_or_account_details(monkeypatch):
    state = {"online": True}
    seen_accounts = []

    def get_state(account):
        seen_accounts.append(account)
        return {
        "account": account,
        "cdp_port": 9223,
        "home_url": "https://www.rednote.com/?session=private-session",
        "online": state["online"],
        "url": "https://www.rednote.com/item/123?token=private-token",
        "title": "Private page title",
        "page_count": 1,
        }

    monkeypatch.setitem(sys.modules, "internal_browser", types.SimpleNamespace(get_state=get_state))
    adapter = CDPAdapter()

    health = adapter.health()
    assert health["state"] == "available"
    assert health["available"] is True
    assert health["diagnostics"]["provider"] == "cdp"
    assert "XHS_PRIVATE_ACCOUNT" not in str(health)
    assert "private-session" not in str(health)
    assert "private-token" not in str(health)
    assert "Private page title" not in str(health)
    assert "9223" not in str(health)

    state["online"] = False
    assert adapter.health()["state"] == "unavailable"
    state["online"] = True
    assert adapter.health()["state"] == "available"
    assert seen_accounts and set(seen_accounts) == {"XHS_RETINAUT"}


def test_cdp_disconnected_health_and_navigation_redact_raw_details(monkeypatch):
    endpoint = "ws://127.0.0.1:9223/devtools/browser/debugger-secret"
    fake_browser = types.SimpleNamespace(
        get_state=lambda account: {"online": False, "error": f"connection refused at {endpoint}"},
        navigate=lambda account, url: {
            "ok": False,
            "account": account,
            "url": "https://www.rednote.com/login?session=private-session",
            "error": f"session expired at {endpoint} token=private-token",
        },
    )
    monkeypatch.setitem(sys.modules, "internal_browser", fake_browser)
    adapter = CDPAdapter()

    health = adapter.health()
    assert health["state"] == "unavailable"
    assert health["diagnostics"]["connection_state"] == "unavailable"
    assert "debugger-secret" not in str(health)

    result = adapter.navigate("https://www.rednote.com/login?session=private-session")
    assert result["ok"] is False
    assert result["url"] == "https://www.rednote.com/login"
    assert "private-session" not in str(result)
    assert "private-token" not in str(result)
    assert "debugger-secret" not in str(result)
    assert "account" not in result


def test_cdp_wait_for_checks_the_document_instead_of_claiming_success(monkeypatch):
    calls = []

    def evaluate(account, expression):
        calls.append(expression)
        return {"ok": True, "value": expression.endswith('"#ready") )')}

    monkeypatch.setitem(sys.modules, "internal_browser", types.SimpleNamespace(evaluate=evaluate))
    adapter = CDPAdapter()
    assert adapter.wait_for("#missing", timeout=0) is False
    assert adapter.wait_for("#ready", timeout=0) is True
    assert calls == [
        'Boolean(document.querySelector("#missing") )',
        'Boolean(document.querySelector("#ready") )',
    ]


def test_cdp_adapter_blocks_mainland_account_before_touching_provider(monkeypatch):
    calls = []
    fake_browser = types.SimpleNamespace(
        get_state=lambda account: calls.append(account),
        navigate=lambda account, url: calls.append((account, url)),
    )
    monkeypatch.setitem(sys.modules, "internal_browser", fake_browser)
    adapter = CDPAdapter(account="XHS_CN_PRIMARY")

    health = adapter.health()
    assert health["state"] == "unavailable"
    assert health["diagnostics"]["error_code"] == "account_not_allowed"
    assert calls == []
    assert "XHS_CN_PRIMARY" not in str(health)
    with pytest.raises(RuntimeError):
        adapter.navigate("https://www.rednote.com")
    assert calls == []
