from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from lumenis.adapters import x_platform
from lumenis.adapters.base import AdapterResult
from lumenis.system.collector.adapters import x_platform as main_x
from lumenis.system.collector.adapters.base import CollectionStatus

_SAFE_WORKER_FAILURES = {
    "READONLY_WORKER_NOT_REGISTERED": ("X not_configured:", CollectionStatus.NOT_CONFIGURED, "NOT_CONFIGURED"),
    "READONLY_WORKER_NOT_CONFIGURED": ("X not_configured:", CollectionStatus.NOT_CONFIGURED, "NOT_CONFIGURED"),
    "BROWSER_PROFILE_OWNER_UNAVAILABLE": ("X not_configured:", CollectionStatus.NOT_CONFIGURED, "NOT_CONFIGURED"),
    "READONLY_WORKER_BOUNDARY_INVALID": ("X blocked:", CollectionStatus.BLOCKED, "BLOCKED"),
    "BROWSER_WORKER_KERNEL_OR_IDENTITY_UNVERIFIED": ("X blocked:", CollectionStatus.BLOCKED, "BLOCKED"),
    "PROTECTED_PROFILE_FORBIDDEN": ("X blocked:", CollectionStatus.BLOCKED, "BLOCKED"),
    "READONLY_WORKER_PROFILE_UNAVAILABLE": ("X provider_unavailable:", CollectionStatus.PROVIDER_UNAVAILABLE, "PROVIDER_UNAVAILABLE"),
    "READONLY_WORKER_PROFILE_OR_MODE_UNAVAILABLE": ("X provider_unavailable:", CollectionStatus.PROVIDER_UNAVAILABLE, "PROVIDER_UNAVAILABLE"),
    "READONLY_WORKER_PROFILE_MODE_OR_KERNEL_UNAVAILABLE": ("X provider_unavailable:", CollectionStatus.PROVIDER_UNAVAILABLE, "PROVIDER_UNAVAILABLE"),
    "BROWSER_WORKER_PROFILE_OR_MODE_UNAVAILABLE": ("X provider_unavailable:", CollectionStatus.PROVIDER_UNAVAILABLE, "PROVIDER_UNAVAILABLE"),
}


@pytest.mark.parametrize("code,expected", _SAFE_WORKER_FAILURES.items())
def test_allowlisted_worker_failures_are_safely_classified(code, expected):
    prefix, status, detail_state = expected
    failure = x_platform._safe_x_browser_failure(
        RuntimeError(f"{code}: secret=PRIVATE network timeout"),
    )

    assert failure.startswith(prefix)
    assert "PRIVATE" not in failure
    assert "network timeout" not in failure
    assert main_x.XAdapter._v4_status_to_main(False, [], failure) is status
    assert main_x.XAdapter._detail_failure_state(failure) == detail_state


def test_malformed_worker_configuration_stops_before_browser_construction(monkeypatch):
    monkeypatch.setenv("X_READONLY_CDP_URL", "http://127.0.0.1:9999")
    browser = Mock(side_effect=AssertionError("invalid worker config must not construct a browser"))
    monkeypatch.setattr(x_platform, "HumanBrowser", browser)
    factory = Mock(wraps=x_platform._new_browser_worker)
    monkeypatch.setattr(x_platform, "_new_browser_worker", factory)

    adapter = x_platform.XAdapter(cookie_string="test-only")
    search_result = adapter.search("term")
    assert not search_result.success
    assert search_result.error == "X not_configured: read-only worker endpoint is not configured"
    assert main_x.XAdapter._v4_status_to_main(False, [], search_result.error) is CollectionStatus.NOT_CONFIGURED
    assert factory.call_count == 1

    detail_result = adapter.detail("123")
    assert not detail_result.success
    assert detail_result.error == "X not_configured: read-only worker endpoint is not configured"
    assert main_x.XAdapter._detail_failure_state(detail_result.error) == "NOT_CONFIGURED"
    assert factory.call_count == 2
    browser.assert_not_called()


def test_unexpected_internal_exception_is_not_exposed_or_misreported_as_network(monkeypatch, caplog):
    secret = "PRIVATE-cookie-value network timeout"
    factory = Mock(side_effect=ValueError(secret))
    monkeypatch.setattr(x_platform, "_new_browser_worker", factory)
    adapter = x_platform.XAdapter(cookie_string="test-only")

    search_result = adapter.search("term")
    assert not search_result.success
    assert search_result.error == "X collection_error: ValueError"
    assert main_x.XAdapter._v4_status_to_main(False, [], search_result.error) is CollectionStatus.COLLECT_ERROR
    assert factory.call_count == 1

    detail_result = adapter.detail("123")
    assert not detail_result.success
    assert detail_result.error == "X collection_error: ValueError"
    assert main_x.XAdapter._detail_failure_state(detail_result.error) == "DETAIL_FAILED"
    assert factory.call_count == 2
    assert secret not in search_result.error
    assert secret not in detail_result.error
    assert secret not in caplog.text


def test_unknown_worker_setup_error_with_network_marker_stays_collection_error(monkeypatch):
    secret = "net::ERR_CONNECTION_RESET PRIVATE-worker-state"
    factory = Mock(side_effect=RuntimeError(secret))
    monkeypatch.setattr(x_platform, "_new_browser_worker", factory)
    adapter = x_platform.XAdapter(cookie_string="test-only")

    search_result = adapter.search("term")
    detail_result = adapter.detail("123")

    assert search_result.error == "X collection_error: RuntimeError"
    assert detail_result.error == "X collection_error: RuntimeError"
    assert main_x.XAdapter._v4_status_to_main(False, [], search_result.error) is CollectionStatus.COLLECT_ERROR
    assert main_x.XAdapter._detail_failure_state(detail_result.error) == "DETAIL_FAILED"
    assert factory.call_count == 2
    assert secret not in search_result.error
    assert secret not in detail_result.error


def test_failed_search_body_completeness_is_not_observed_and_does_not_retry():
    backend = Mock()
    backend.search.return_value = AdapterResult(
        success=False, error="X collection_error: ValueError", raw_count=0,
    )
    result = main_x.XAdapter(backend=backend).search("term")

    assert result.status is CollectionStatus.COLLECT_ERROR
    assert not result.ok
    assert result.metadata["detail"]["body_completeness"] == "NOT_OBSERVED"
    assert result.metadata["detail"]["attempted"] == 0
    backend.search.assert_called_once()
    backend.detail.assert_not_called()


def test_successful_empty_search_keeps_no_results_completeness():
    backend = Mock()
    backend.search.return_value = AdapterResult(success=True, notes=[], raw_count=0)
    result = main_x.XAdapter(backend=backend).search("term")

    assert result.status is CollectionStatus.NO_NEW_DATA
    assert result.metadata["detail"]["body_completeness"] == "NO_RESULTS"
    backend.search.assert_called_once()
    backend.detail.assert_not_called()


def _assert_redacted_exception_traceback(caplog, message_fragment, exception_class, expected_frame):
    records = [record for record in caplog.records if message_fragment in record.getMessage()]
    assert records
    for record in records:
        assert record.exc_info is not None
        logged_type, display_exception, traceback = record.exc_info
        assert logged_type is RuntimeError
        assert display_exception.args == (f"REDACTED_ORIGINAL_EXCEPTION:{exception_class}",)
        assert display_exception.__cause__ is None
        assert display_exception.__context__ is None
        assert traceback is not None
        frame_names = []
        current = traceback
        while current is not None:
            frame_names.append(current.tb_frame.f_code.co_name)
            current = current.tb_next
        assert expected_frame in frame_names


def test_low_level_internal_exception_log_keeps_only_safe_class_and_traceback(monkeypatch, caplog):
    secret = "PRIVATE-cookie-session-token network timeout"
    factory = Mock(side_effect=ValueError(secret))
    monkeypatch.setattr(x_platform, "_new_browser_worker", factory)

    result = x_platform.XAdapter(cookie_string="test-only").search("term")

    assert result.error == "X collection_error: ValueError"
    assert secret not in result.error
    assert secret not in caplog.text
    _assert_redacted_exception_traceback(
        caplog, "X 浏览器采集异常", "ValueError", "_search_browser",
    )


def test_system_search_exception_does_not_expose_private_text(caplog):
    class SessionCookieTimeoutError(Exception):
        pass

    secret = "PRIVATE-cookie-session-token timeout verify"
    backend = Mock()
    backend.search.side_effect = SessionCookieTimeoutError(secret)

    result = main_x.XAdapter(backend=backend).search("term")

    assert result.status is CollectionStatus.COLLECT_ERROR
    assert result.message == "X collection_error: SessionCookieTimeoutError"
    assert secret not in result.message
    assert secret not in caplog.text
    _assert_redacted_exception_traceback(
        caplog, "X 主链路采集失败", "SessionCookieTimeoutError", "search",
    )
    backend.search.assert_called_once()
    backend.detail.assert_not_called()


def test_system_delegate_exception_does_not_expose_private_text(caplog):
    class VerificationError(Exception):
        pass

    secret = "PRIVATE-browser-session-cookie challenge timeout"
    backend = Mock()
    backend.detail.side_effect = VerificationError(secret)

    result = main_x.XAdapter(backend=backend).detail("123")

    assert result.status is CollectionStatus.COLLECT_ERROR
    assert result.message == "X collection_error: VerificationError"
    assert secret not in result.message
    assert secret not in caplog.text
    _assert_redacted_exception_traceback(
        caplog, "X delegated operation failed", "VerificationError", "_delegate_v4",
    )
    backend.detail.assert_called_once_with("123")


class _FakePage:
    def __init__(self, *, final_url="https://x.com/search", title="X", navigation_error=None):
        self.url = final_url
        self.title_text = title
        self.navigation_error = navigation_error
        self.closed = False
        self.mouse = SimpleNamespace(wheel=Mock())

    def goto(self, url, **_kwargs):
        if self.navigation_error:
            raise RuntimeError(self.navigation_error)
        if self.url == "https://x.com/search":
            self.url = url

    def title(self):
        return self.title_text

    def query_selector_all(self, _selector):
        return []

    def close(self):
        self.closed = True


class _FakeWorker:
    def __init__(self, page):
        self._context = object()
        self.page = page
        self.closed = False

    def connect(self):
        return self

    def new_page(self, *, stealth=True):
        assert stealth is False
        return self.page

    def pause(self, *_args):
        pass

    def close(self):
        self.closed = True


@pytest.mark.parametrize(
    "final_url,title,error,expected",
    [
        ("https://x.com/i/flow/login", "X", None, "X login/session required or expired"),
        ("https://x.com/challenge", "X", None, "X verification challenge detected"),
        ("https://x.com/account/access", "X", None, "X access blocked or rate limited"),
        ("https://x.com/search", "X", "net::ERR_CONNECTION_RESET", "X network error"),
    ],
)
@pytest.mark.parametrize("route", ["search", "detail"])
def test_observed_access_and_network_failures_remain_distinct(
    monkeypatch, final_url, title, error, expected, route,
):
    page = _FakePage(final_url=final_url, title=title, navigation_error=error)
    worker = _FakeWorker(page)
    monkeypatch.setattr(x_platform, "_new_browser_worker", lambda: worker)
    monkeypatch.setattr(x_platform, "inject_into_context", lambda *_args: None)
    adapter = x_platform.XAdapter(cookie_string="test-only")

    result = adapter.search("term") if route == "search" else adapter.detail("123")

    assert not result.success
    assert result.error == expected
    assert page.closed and worker.closed
    assert main_x.XAdapter._v4_status_to_main(False, [], result.error) in {
        CollectionStatus.SESSION_EXPIRED,
        CollectionStatus.RISK_WARNING,
        CollectionStatus.BLOCKED,
        CollectionStatus.PROVIDER_UNAVAILABLE,
    }


@pytest.mark.parametrize(
    "failure,status,detail_state",
    [
        ("X not_configured: safe config state", CollectionStatus.NOT_CONFIGURED, "NOT_CONFIGURED"),
        ("X blocked: safe boundary state", CollectionStatus.BLOCKED, "BLOCKED"),
        ("X provider_unavailable: safe worker state", CollectionStatus.PROVIDER_UNAVAILABLE, "PROVIDER_UNAVAILABLE"),
        ("X collection_error: TimeoutError", CollectionStatus.COLLECT_ERROR, "DETAIL_FAILED"),
        ("X collection_error: SessionCookieTimeoutError", CollectionStatus.COLLECT_ERROR, "DETAIL_FAILED"),
        ("X collection_error: VerificationError", CollectionStatus.COLLECT_ERROR, "DETAIL_FAILED"),
        ("X not_configured: session cookie missing", CollectionStatus.NOT_CONFIGURED, "NOT_CONFIGURED"),
        ("X blocked: verification challenge", CollectionStatus.BLOCKED, "BLOCKED"),
        ("X provider_unavailable: session cookie timeout", CollectionStatus.PROVIDER_UNAVAILABLE, "PROVIDER_UNAVAILABLE"),
    ],
)
def test_system_prefix_mappings_precede_generic_network_words(failure, status, detail_state):
    assert main_x.XAdapter._v4_status_to_main(False, [], failure) is status
    assert main_x.XAdapter._detail_failure_state(failure) == detail_state

