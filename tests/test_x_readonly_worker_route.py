from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from lumenis.adapters import x_platform
from lumenis.adapters.base import CollectedNote
from lumenis.system.collector.adapters import x_platform as main_x
from lumenis.system.collector.adapters.base import CollectionStatus
from scripts import start_resident_browsers as resident


def test_x_worker_requires_exact_opt_in_and_profile_binding(monkeypatch, tmp_path):
    import cdp_helper
    from lumenis.adapters import cookie_vault

    monkeypatch.setenv("X_READONLY_CDP_URL", "http://127.0.0.1:9226")
    monkeypatch.setenv("X_READONLY_LOCAL_WORKER_ENABLED", "true")
    monkeypatch.setenv("X_READONLY_LOCAL_WORKER_ACCOUNT", "X_READONLY")
    monkeypatch.setattr(cookie_vault, "_current_data_dir", lambda: str(tmp_path))
    bound = Mock(return_value=True)
    monkeypatch.setattr(cdp_helper, "is_cdp_profile_running", bound)

    assert x_platform._configured_browser_worker_url() == "http://127.0.0.1:9226"
    bound.assert_called_once_with(9226, str(tmp_path / "private" / "profiles" / "x-readonly"))

    monkeypatch.setenv("X_READONLY_LOCAL_WORKER_ACCOUNT", "GENERAL_BROWSE")
    with pytest.raises(RuntimeError, match="X_WORKER_FAILURE:NOT_CONFIGURED"):
        x_platform._configured_browser_worker_url()


def test_worker_plan_isolated_and_never_in_default_startup(monkeypatch, tmp_path):
    spec = resident.x_readonly_worker_spec(str(tmp_path))
    assert spec == {
        "account": "X_READONLY",
        "port": 9226,
        "profile": str(tmp_path / "profiles" / "x-readonly"),
        "env_prefix": "X_READONLY",
        "home": "about:blank",
        "direct": False,
    }

    start_x = Mock(side_effect=AssertionError("default startup must not start X"))
    monkeypatch.setattr(resident, "launch_x_readonly", start_x)
    monkeypatch.setattr(resident, "RESIDENT_PLAN", [])
    monkeypatch.setattr(resident, "launch_general", lambda status_only=False: {
        "account": "GENERAL_BROWSE", "online": True, "direct": True, "port": 9224,
        "profile": "general", "home": "https://example.invalid", "action": "already_online", "pages": [],
    })
    monkeypatch.setattr(sys, "argv", ["start_resident_browsers.py"])
    assert resident.main() == 0
    start_x.assert_not_called()

    chosen = Mock(return_value={"account": "X_READONLY", "online": True, "port": 9226,
                                "browser": "edge", "profile": "isolated", "home": "about:blank",
                                "action": "already_online"})
    monkeypatch.setattr(resident, "launch_x_readonly", chosen)
    monkeypatch.setattr(sys, "argv", ["start_resident_browsers.py", "--account", "X_READONLY"])
    assert resident.main() == 0
    chosen.assert_called_once_with(status_only=False)


def test_explicit_launcher_refuses_unknown_port_owner(monkeypatch):
    monkeypatch.setattr(resident, "port_online", lambda port: port == 9226)
    # A listening port whose PID/profile binding cannot be proved is rejected
    # by the registered-owner resolver before the compatibility verifier runs.
    owner = Mock(return_value=None)
    monkeypatch.setattr(resident.cdp_helper, "registered_cdp_browser_for_port", owner)
    bound = Mock(return_value=False)
    monkeypatch.setattr(resident.cdp_helper, "is_cdp_profile_running", bound)
    start = Mock(side_effect=AssertionError("unknown port owner must not be reused"))
    monkeypatch.setattr(resident.cdp_helper, "start_cdp_browser", start)

    row = resident.launch_x_readonly()
    assert row["action"] == "port_in_use_unverified"
    assert not row["online"]
    assert row["port_open"]
    owner.assert_called_once_with(9226, row["profile"], headless=True)
    bound.assert_not_called()
    start.assert_not_called()


def test_explicit_launcher_binds_exact_loopback_profile(monkeypatch, tmp_path):
    monkeypatch.setattr(resident, "bridge", SimpleNamespace(PRIVATE_DATA_DIR=str(tmp_path)))
    monkeypatch.setattr(resident.cdp_helper, "system_default_cdp_browser", lambda: "edge")
    monkeypatch.setattr(resident, "port_online", lambda port: False)
    started = Mock(return_value={"success": True, "pid": 123})
    monkeypatch.setattr(resident.cdp_helper, "start_cdp_browser", started)
    binding = Mock(return_value=True)
    monkeypatch.setattr(resident.cdp_helper, "is_cdp_profile_running", binding)

    row = resident.launch_x_readonly()
    assert row["profile"] == str(tmp_path / "profiles" / "x-readonly")
    assert row["online"] is True
    binding.assert_called_once_with(
        9226, row["profile"], headless=True, loopback_only=True, browser="edge")
    started.assert_called_once_with(
        port=9226,
        profile_dir=row["profile"],
        launch_url="about:blank",
        direct_connection=False,
        browser="edge",
        headless=True,
        loopback_only=True,
        task_id=None,
        actor_ref=None,
    )


class _FakePage:
    def __init__(self, *, url="https://x.com/search", title="X", body="", articles=None, error=None, elements=None):
        self.url = url
        self.title_text = title
        self.body = body
        self.articles = articles or []
        self.elements = elements or {}
        self.error = error
        self.closed = False
        self.mouse = SimpleNamespace(wheel=Mock())

    def goto(self, *_args, **_kwargs):
        if self.error:
            raise RuntimeError(self.error)

    def locator(self, _selector):
        return SimpleNamespace(inner_text=lambda **_kwargs: self.body)

    def title(self):
        return self.title_text

    def query_selector(self, selector):
        return self.elements.get(selector)

    def query_selector_all(self, _selector):
        return self.articles

    def close(self):
        self.closed = True


class _FakeWorker:
    def __init__(self, page):
        self._context = object()
        self.page = page
        self.closed = False
        self.stealth = None

    def connect(self):
        return self

    def new_page(self, *, stealth=True):
        self.stealth = stealth
        return self.page

    def pause(self, *_args):
        pass

    def close(self):
        self.closed = True


@pytest.mark.parametrize(
    "url,body,error,expected",
    [
        ("https://x.com/i/flow/login", "", "", "X_PAGE_FAILURE:SESSION_EXPIRED"),
        ("https://x.com/challenge", "", "", "X_PAGE_FAILURE:VERIFICATION_REQUIRED"),
        ("https://x.com/search", "", "net::ERR_CONNECTION_RESET", "X_PAGE_FAILURE:NETWORK_UNAVAILABLE"),
        ("https://x.com/account/access", "", "", "X_PAGE_FAILURE:RATE_LIMITED"),
    ],
)
def test_search_classifies_failure_and_always_cleans_up(monkeypatch, url, body, error, expected):
    page = _FakePage(url=url, body=body, error=error)
    worker = _FakeWorker(page)
    monkeypatch.setattr(x_platform, "_new_browser_worker", lambda: worker)
    monkeypatch.setattr(x_platform, "inject_into_context", lambda *_: 0)
    monkeypatch.setattr(x_platform.XAdapter, "_parse_x_tweet", lambda *_: None)
    adapter = x_platform.XAdapter(cookie_string="test-only")

    result = adapter.search("term")
    assert not result.success
    assert result.error == expected
    assert worker.stealth is False
    assert page.closed and worker.closed


def test_fix_096_worker_exception_is_phase_coded_and_redacted(monkeypatch, caplog):
    def fail_worker():
        try:
            raise RuntimeError("cookie=CAUSE_SECRET")
        except RuntimeError as cause:
            raise ValueError("token=WORKER_SECRET") from cause

    monkeypatch.setattr(x_platform, "_new_browser_worker", fail_worker)
    with caplog.at_level("WARNING", logger="lumenis.adapters.x_platform"):
        result = x_platform.XAdapter(cookie_string="test-only").search("term")
    assert result.error == "X_WORKER_FAILURE:UPSTREAM_FAILURE"
    assert "WORKER_SECRET" not in result.error
    assert "CAUSE_SECRET" not in caplog.text
    assert "WORKER_SECRET" not in caplog.text


def test_fix_096_page_exception_is_phase_coded_and_redacted(monkeypatch, caplog):
    page = _FakePage()
    worker = _FakeWorker(page)
    monkeypatch.setattr(x_platform, "_new_browser_worker", lambda: worker)
    monkeypatch.setattr(x_platform, "inject_into_context", lambda *_: 0)

    def fail_goto(*_args, **_kwargs):
        try:
            raise RuntimeError("cookie=CAUSE_SECRET")
        except RuntimeError as cause:
            raise ValueError("token=PAGE_SECRET") from cause

    page.goto = fail_goto
    with caplog.at_level("WARNING", logger="lumenis.adapters.x_platform"):
        result = x_platform.XAdapter(cookie_string="test-only").search("term")
    assert result.error == "X_PAGE_FAILURE:UPSTREAM_FAILURE"
    assert "PAGE_SECRET" not in result.error
    assert "CAUSE_SECRET" not in caplog.text
    assert "PAGE_SECRET" not in caplog.text
    assert page.closed and worker.closed


def test_fix_096_registered_backend_import_failure_is_sanitized(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "lumenis.adapters.x_platform", None)
    with pytest.raises(RuntimeError, match="^X_WORKER_FAILURE:UPSTREAM_FAILURE$"):
        main_x.XAdapter()._load_backend()


def test_empty_search_is_not_success(monkeypatch):
    page = _FakePage()
    worker = _FakeWorker(page)
    monkeypatch.setattr(x_platform, "_new_browser_worker", lambda: worker)
    monkeypatch.setattr(x_platform, "inject_into_context", lambda *_: 0)
    adapter = x_platform.XAdapter(cookie_string="test-only")
    result = adapter.search("term")
    assert not result.success
    assert "no verifiable posts" in result.error
    assert page.closed and worker.closed


def _note(platform="x"):
    return CollectedNote(title="Visible post", content="text", url="https://x.com/i/web/status/123",
                         author="@user", author_id="@user", publish_date="", likes=None,
                         comments=None, collects=None, shares=None, cover="", source_platform=platform,
                         raw_data={"tweet_id": "123"})


def test_detail_uses_opted_in_worker_and_closes_only_its_page(monkeypatch):
    article = object()
    page = _FakePage(url="https://x.com/i/web/status/123", articles=[article],
                     elements={"article": article})
    worker = _FakeWorker(page)
    monkeypatch.setattr(x_platform, "_new_browser_worker", lambda: worker)
    monkeypatch.setattr(x_platform, "inject_into_context", lambda *_: 0)
    monkeypatch.setattr(x_platform.XAdapter, "_parse_x_tweet",
                        lambda *_args, **_kwargs: _note())
    result = x_platform.XAdapter(cookie_string="test-only").detail("123")
    assert result.success and result.raw_count == 1
    assert worker.stealth is False
    assert page.closed and worker.closed


def test_detail_rejects_non_x_urls_before_worker_contact(monkeypatch):
    worker = Mock(side_effect=AssertionError("invalid URL must not contact worker"))
    monkeypatch.setattr(x_platform, "_new_browser_worker", worker)
    result = x_platform.XAdapter(cookie_string="test-only").detail("https://example.com/status/123")
    assert not result.success
    worker.assert_not_called()


def test_comments_wait_for_provable_parent_relationship(monkeypatch):
    worker = Mock(side_effect=AssertionError("do not expose unclassified article cards as replies"))
    monkeypatch.setattr(x_platform, "_new_browser_worker", worker)
    comments = x_platform.XAdapter(cookie_string="test-only").comments("123")
    assert not comments.success
    assert comments.notes == []
    assert "not supported" in comments.error and "relationships" in comments.error
    worker.assert_not_called()


def test_post_text_with_state_words_does_not_trigger_access_failure():
    body = "The verification challenge blocked the connection; this is just quoted post text."
    assert x_platform._x_page_failure("https://x.com/search", body) == ""
    assert x_platform._x_page_failure(
        "https://x.com/search", title="Log in to X / X"
    ) == "X_PAGE_FAILURE:SESSION_EXPIRED"



def test_creator_uses_worker_and_retains_only_verified_followers(monkeypatch):
    class Element:
        def __init__(self, text): self.text = text
        def inner_text(self): return self.text

    profile_page = _FakePage(elements={
        '[data-testid="UserName"] div, h2': Element("Creator"),
        'a[href*="/verified_followers"] span': Element("1,234 Followers"),
    })
    profile_worker = _FakeWorker(profile_page)
    monkeypatch.setattr(x_platform, "_new_browser_worker", lambda: profile_worker)
    monkeypatch.setattr(x_platform, "inject_into_context", lambda *_: 0)
    profile = x_platform.XAdapter(cookie_string="test-only").creator("@creator")
    assert profile.success
    note = profile.notes[0]
    assert note.raw_data["followers"] == 1234
    assert note.likes is None and note.comments is None
    assert note.collects is None and note.shares is None
    assert profile_worker.stealth is False
    assert profile_page.closed and profile_worker.closed


def test_existing_routes_fail_closed_on_login_page(monkeypatch):
    page = _FakePage(url="https://x.com/i/flow/login")
    worker = _FakeWorker(page)
    monkeypatch.setattr(x_platform, "_new_browser_worker", lambda: worker)
    monkeypatch.setattr(x_platform, "inject_into_context", lambda *_: 0)
    adapter = x_platform.XAdapter(cookie_string="test-only")
    result = adapter.detail("123")
    assert not result.success and result.error == "X_PAGE_FAILURE:SESSION_EXPIRED"
    assert page.closed and worker.closed


def test_network_failure_has_distinct_main_status():
    assert main_x.XAdapter._v4_status_to_main(False, [], "X network error") == CollectionStatus.PROVIDER_UNAVAILABLE
    assert main_x.XAdapter._v4_status_to_main(False, [], "X login/session required") == CollectionStatus.SESSION_EXPIRED
    assert main_x.XAdapter._v4_status_to_main(False, [], "X verification challenge") == CollectionStatus.RISK_WARNING
    assert main_x.XAdapter._v4_status_to_main(False, [], "X access blocked") == CollectionStatus.BLOCKED
    assert main_x.XAdapter._v4_status_to_main(False, [], "X comments not supported: relationship unclear") == CollectionStatus.NOT_SUPPORTED


@pytest.mark.parametrize(
    "metadata,expected",
    [({"has_auth_cookie": True}, CollectionStatus.NEED_VERIFY),
     ({"has_auth_cookie": False}, CollectionStatus.NOT_CONFIGURED)],
)
def test_health_metadata_never_claims_live_session(monkeypatch, metadata, expected):
    from lumenis.adapters import cookie_vault

    monkeypatch.setattr(cookie_vault, "check_cookie_status", lambda _platform: metadata)
    result = main_x.XAdapter().health_check()
    assert result.status == expected
    assert result.status != CollectionStatus.SUCCESS


def test_generic_transition_counter_is_not_persisted_as_views():
    class Counter:
        def get_attribute(self, name):
            return "1.2K" if name == "aria-label" else None

        def inner_text(self):
            return "1.2K"

        def evaluate(self, _expression):
            return False

    class Tweet:
        def query_selector_all(self, selector):
            if selector == '[data-testid="app-text-transition-container"]':
                return [Counter()]
            return []

    note = x_platform.XAdapter(cookie_string="test-only")._parse_x_tweet(Tweet())
    assert note.likes is None
    assert note.raw_data["views"] is None
    assert note.raw_data["metric_display"]["views"] is None
    assert note.raw_data["unclassified_counter_display"] == {
        "aria_label": "1.2K",
        "text": "1.2K",
        "locator": '[data-testid="app-text-transition-container"]',
    }



def test_system_search_and_delegate_results_use_real_platform_contract():
    from lumenis.adapters.base import AdapterResult, CollectedNote

    note = CollectedNote(
        title="Native X post", content="source text", url="https://x.com/user/status/123",
        author="@user", author_id="@user", publish_date="2026-09-28T00:00:00Z",
        likes=7, comments=2, collects=None, shares=1, cover="", source_platform="x",
        raw_data={"tweet_id": "123", "metric_display": {"likes": "7 Likes"}},
    )

    class Backend:
        def search(self, _keyword, **_kwargs):
            return AdapterResult(success=False, error="X network error", raw_count=0)

        def detail(self, _content_id):
            return AdapterResult(success=True, notes=[note], raw_count=1)

        def creator(self, _creator_id):
            raise RuntimeError("source parse failed")

    adapter = main_x.XAdapter(backend=Backend())
    search_result = adapter.search("term")
    assert isinstance(search_result, main_x.CollectionResult)
    assert search_result.platform == "x"
    assert search_result.status == CollectionStatus.PROVIDER_UNAVAILABLE
    assert search_result.message == "X_PAGE_FAILURE:NETWORK_UNAVAILABLE"

    detail_result = adapter.detail("123")
    assert isinstance(detail_result, main_x.CollectionResult)
    assert detail_result.platform == "x"
    assert detail_result.items[0]["platform_content_id"] == "123"
    assert detail_result.items[0]["content"] == "source text"
    assert detail_result.items[0]["likes"] == 7
    assert detail_result.items[0]["comments"] == 2

    delegate_error = adapter.creator("user")
    assert isinstance(delegate_error, main_x.CollectionResult)
    assert delegate_error.platform == "x"
    assert delegate_error.status == CollectionStatus.COLLECT_ERROR
    assert delegate_error.message == "X_PAGE_FAILURE:UPSTREAM_FAILURE"


def test_fix_096_registered_adapter_redacts_backend_error_text():
    from lumenis.adapters.base import AdapterResult

    secret = "token=PAGE_SECRET; source body=PRIVATE_SOURCE_TEXT"

    class Backend:
        def search(self, _keyword, **_kwargs):
            return AdapterResult(success=False, error=secret)

    result = main_x.XAdapter(backend=Backend()).search("term")
    assert result.status == CollectionStatus.COLLECT_ERROR
    assert result.message == "X_PAGE_FAILURE:UPSTREAM_FAILURE"
    assert "PAGE_SECRET" not in result.message
    assert "PRIVATE_SOURCE_TEXT" not in repr(result.metadata)
