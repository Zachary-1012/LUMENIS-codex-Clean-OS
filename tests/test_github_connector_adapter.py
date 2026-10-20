"""GitHub connector/adapter contract tests; all network calls are injected."""

import io
import json
import urllib.parse
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from github_connector import (
    GitHubCollectionPage,
    GitHubConnector,
    GitHubConnectorConfig,
    GitHubConnectorError,
    _GitHubRedirectHandler,
)
from lumenis.system.collector.adapters.github import GitHubAdapter
from lumenis.system.collector.adapters.base import CollectionStatus


def test_github_adapter_maps_allowlisted_read_data_without_business_rules():
    class Connector:
        def search_repositories_page_result(self, keyword, **kwargs):
            assert keyword == "lumenis"
            return GitHubCollectionPage(items=[{
                    "id": 1,
                    "full_name": "owner/lumenis",
                    "description": "production truth",
                    "owner": {"login": "owner"},
                    "html_url": "https://github.com/owner/lumenis",
                    "stargazers_count": 3,
                }], pages_fetched=1, api_items_observed=1,
                coverage_complete=True, coverage_scope="FULL_QUERY")

    result = GitHubAdapter(connector=Connector()).search("lumenis")
    assert result.status == CollectionStatus.SUCCESS
    assert result.metadata["provider"] == "github_app_user_authorization"
    assert result.metadata["write_enabled"] is False
    assert result.items[0]["platform_content_id"] == "1"
    assert result.items[0]["title"] == "owner/lumenis"
    assert result.items[0]["content"] == "production truth"
    assert result.metadata["coverage_complete"] is True
    assert result.raw_count == 1


def test_github_adapter_keeps_unconfigured_state_truthful():
    adapter = GitHubAdapter(connector=GitHubConnector(
        config=GitHubConnectorConfig(), token_provider=lambda: "",
    ))
    result = adapter.search("lumenis")
    assert result.status == CollectionStatus.NOT_CONFIGURED
    assert result.items == []
    assert result.metadata["error_code"] == "NOT_CONNECTED"


def test_github_connector_rejects_non_allowlisted_repo_before_network():
    calls = []

    def opener(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("network must not run for a non-allowlisted repository")

    connector = GitHubConnector(
        config=GitHubConnectorConfig(repositories=("owner/allowed",)),
        token_provider=lambda: "token",
        opener=opener,
    )
    try:
        connector.repository("owner/blocked")
    except GitHubConnectorError as exc:
        assert exc.code == "REPOSITORY_NOT_ALLOWLISTED"
    else:
        raise AssertionError("expected repository allowlist failure")
    assert calls == []


class _Response:
    def __init__(self, payload, headers=None):
        self.payload = json.dumps(payload).encode("utf-8")
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        return self.payload if size < 0 else self.payload[:size]


def _page(items, *, total=None, headers=None):
    body = {"items": items, "total_count": total, "incomplete_results": False}
    return _Response(body, headers)


def _http_error(status, *, headers=None, message="synthetic response"):
    return HTTPError(
        "https://api.github.com/search/repositories", status, message,
        headers or {}, io.BytesIO(json.dumps({"message": message}).encode()),
    )


def _connector(opener, *, sleep=None, repositories=("owner/allowed",)):
    return GitHubConnector(
        config=GitHubConnectorConfig(repositories=repositories),
        token_provider=lambda: "synthetic-token",
        opener=opener,
        sleep=sleep,
    )


def _link(page, *, query="lumenis", per_page=50):
    return {
        "Link": (
            f'<https://api.github.com/search/repositories?q={query}'
            f'&per_page={per_page}&page={page}>; rel="next"'
        ),
    }


def test_search_paginates_over_50_and_reports_actual_coverage():
    calls = []
    page_one = [{"id": i, "full_name": f"owner/repo-{i}"} for i in range(50)]
    page_two = [{"id": 50, "full_name": "owner/repo-50"}]

    def opener(request, timeout):
        calls.append(request.full_url)
        if "page=1" in request.full_url:
            return _page(page_one, total=51, headers=_link(2))
        return _page(page_two, total=51)

    result = _connector(
        opener, repositories=tuple(f"owner/repo-{i}" for i in range(51)),
    ).search_repositories_page_result("lumenis", limit=60)
    assert len(calls) == 2
    assert "per_page=50" in calls[0]
    assert len(result.items) == 51
    assert result.pages_fetched == 2
    assert result.api_items_observed == 51
    assert result.reported_total_count == 51
    assert result.coverage_complete is True
    assert result.next_cursor is None


def test_search_filters_allowlist_without_relabeling_api_item_count():
    connector = _connector(lambda request, timeout: _page([
        {"id": 1, "full_name": "owner/allowed"},
        {"id": 2, "full_name": "owner/not-selected"},
    ], total=2))
    result = connector.search_repositories_page_result("lumenis", limit=10)
    assert [item["full_name"] for item in result.items] == ["owner/allowed"]
    assert result.api_items_observed == 2
    assert result.reported_total_count == 2


@pytest.mark.parametrize(
    "total, expected_reason",
    [(None, "PROVIDER_TOTAL_UNAVAILABLE"),
     (0, "PROVIDER_TOTAL_BELOW_OBSERVED_ITEMS"),
     (2, "PROVIDER_TOTAL_EXCEEDS_OBSERVED_ITEMS")],
)
def test_search_does_not_claim_complete_when_reported_total_is_unknown_or_inconsistent(total, expected_reason):
    connector = _connector(lambda request, timeout: _page(
        [{"id": 1, "full_name": "owner/allowed"}], total=total,
    ))
    result = connector.search_repositories_page_result("lumenis", limit=10)
    assert result.coverage_complete is False
    assert result.partial_reason == expected_reason


def test_result_limit_is_partial_when_provider_has_another_page():
    calls = []
    items = [{"id": i, "full_name": "owner/allowed"} for i in range(10)]
    connector = _connector(lambda request, timeout: (calls.append(request.full_url) or _page(
        items, total=20, headers=_link(2, per_page=10),
    )))
    result = connector.search_repositories_page_result("lumenis", limit=10)
    adapted = GitHubAdapter._page_result(result, "search")
    assert len(calls) == 1
    assert result.partial_reason == "RESULT_LIMIT_REACHED"
    assert result.coverage_complete is False
    assert result.next_cursor["page"] == 2
    assert adapted.ok is False
    assert adapted.status == CollectionStatus.COLLECT_ERROR


def test_result_limit_resumes_inside_provider_page_without_gaps_or_duplicates():
    page_one = [{"id": i, "full_name": f"owner/repo-{i}"} for i in range(50)]
    page_two = [{"id": i, "full_name": f"owner/repo-{i}"} for i in range(50, 100)]
    page_three = [{"id": i, "full_name": f"owner/repo-{i}"} for i in range(100, 105)]
    repos = tuple(f"owner/repo-{i}" for i in range(105))

    def opener_for(pages):
        def opener(request, timeout):
            url = urllib.parse.urlsplit(request.full_url)
            page = int(urllib.parse.parse_qs(url.query)["page"][0])
            headers = _link(page + 1) if page < 3 else None
            return _page(pages[page], total=105, headers=headers)
        return opener

    pages = {1: page_one, 2: page_two, 3: page_three}
    first = _connector(opener_for(pages), repositories=repos).search_repositories_page_result(
        "lumenis", limit=60,
    )
    assert [item["id"] for item in first.items] == list(range(60))
    assert first.next_cursor == {
        "version": 1, "request_fingerprint": first.next_cursor["request_fingerprint"],
        "page": 2, "offset": 10,
    }

    second = _connector(opener_for(pages), repositories=repos).search_repositories_page_result(
        "lumenis", limit=60, cursor=first.next_cursor,
    )
    assert [item["id"] for item in second.items] == list(range(60, 105))
    assert second.coverage_complete is True
    assert second.next_cursor is None


def test_limit_60_with_100_results_resumes_page_tail_exactly_once():
    page_one = [{"id": i, "full_name": f"owner/repo-{i}"} for i in range(50)]
    page_two = [{"id": i, "full_name": f"owner/repo-{i}"} for i in range(50, 100)]
    repos = tuple(f"owner/repo-{i}" for i in range(100))

    def opener(request, timeout):
        page = int(urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)["page"][0])
        return _page(page_one, total=100, headers=_link(2)) if page == 1 else _page(page_two, total=100)

    connector = _connector(opener, repositories=repos)
    first = connector.search_repositories_page_result("lumenis", limit=60)
    assert [item["id"] for item in first.items] == list(range(60))
    assert first.coverage_complete is False
    assert first.next_cursor["page"] == 2 and first.next_cursor["offset"] == 10

    resumed = connector.search_repositories_page_result(
        "lumenis", limit=60, cursor=first.next_cursor,
    )
    assert [item["id"] for item in resumed.items] == list(range(60, 100))
    assert resumed.coverage_complete is True
    assert resumed.next_cursor is None
    all_ids = [item["id"] for item in first.items + resumed.items]
    assert all_ids == list(range(100))


def test_continuation_total_count_still_detects_missing_provider_pages():
    repos = tuple(f"owner/repo-{i}" for i in range(150))
    first = _connector(lambda request, timeout: _page(
        [{"id": i, "full_name": f"owner/repo-{i}"} for i in range(50)],
        total=150, headers=_link(2),
    ), repositories=repos).search_repositories_page_result("lumenis", limit=60)
    assert first.next_cursor["page"] == 2
    assert first.next_cursor["offset"] == 10

    second = _connector(lambda request, timeout: _page(
        [{"id": i, "full_name": f"owner/repo-{i}"} for i in range(50, 100)],
        total=150,
    ), repositories=repos).search_repositories_page_result(
        "lumenis", limit=60, cursor=first.next_cursor,
    )
    assert second.coverage_complete is False
    assert second.partial_reason == "PROVIDER_TOTAL_EXCEEDS_OBSERVED_ITEMS"
    assert second.next_cursor is None


def test_page_budget_returns_partial_cursor_and_resume_is_segment_scoped():
    page_one = [{"id": i, "full_name": f"owner/repo-{i}"} for i in range(50)]
    page_two = [{"id": i + 50, "full_name": f"owner/repo-{i + 50}"} for i in range(50)]

    repos = tuple(f"owner/repo-{i}" for i in range(100))
    first = _connector(lambda request, timeout: _page(
        page_one, total=100, headers=_link(2),
    ), repositories=repos).search_repositories_page_result("lumenis", limit=100, max_pages=1)
    assert first.coverage_complete is False
    assert first.partial_reason == "PAGE_BUDGET_REACHED"
    assert first.next_cursor["page"] == 2
    assert first.api_items_observed == 50

    second = _connector(lambda request, timeout: _page(page_two, total=100), repositories=repos).search_repositories_page_result(
        "lumenis", limit=100, max_pages=1, cursor=first.next_cursor,
    )
    assert len(second.items) == 50
    assert second.start_page == 2
    assert second.coverage_scope == "CONTINUATION_SEGMENT"
    assert second.coverage_complete is True
    assert second.api_items_observed == 50


def test_search_marks_total_changing_during_pagination_incomplete():
    calls = 0

    def opener(request, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            return _page(
                [{"id": i, "full_name": f"owner/repo-{i}"} for i in range(50)],
                total=51, headers=_link(2),
            )
        return _page([{"id": 50, "full_name": "owner/repo-50"}], total=52)

    connector = _connector(opener, repositories=tuple(f"owner/repo-{i}" for i in range(51)))
    result = connector.search_repositories_page_result("lumenis", limit=60)
    assert result.api_items_observed == 51
    assert result.reported_total_count == 52
    assert result.coverage_complete is False
    assert result.partial_reason == "PROVIDER_TOTAL_CHANGED_DURING_PAGING"


def test_cursor_is_bound_to_query_and_allowlist_before_network():
    first = _connector(lambda request, timeout: _page(
        [{"id": 1, "full_name": "owner/allowed"}], total=20,
        headers=_link(2, per_page=10),
    )).search_repositories_page_result("lumenis", limit=10, max_pages=1)
    calls = []

    def forbidden_network(request, timeout):
        calls.append(request.full_url)
        pytest.fail("invalid cursors must be rejected before the provider call")

    changed_query = _connector(forbidden_network)
    with pytest.raises(GitHubConnectorError) as error:
        changed_query.search_repositories_page_result(
            "different query", limit=10, cursor=first.next_cursor,
        )
    assert error.value.code == "INVALID_CURSOR"
    changed_allowlist = _connector(forbidden_network, repositories=("owner/other",))
    with pytest.raises(GitHubConnectorError) as error:
        changed_allowlist.search_repositories_page_result(
            "lumenis", limit=10, cursor=first.next_cursor,
        )
    assert error.value.code == "INVALID_CURSOR"
    assert calls == []


def test_cancel_preserves_partial_items_and_resume_page():
    checks = iter((False, True))
    result = _connector(lambda request, timeout: _page(
        [{"id": 1, "full_name": "owner/allowed"}], total=2, headers=_link(2, per_page=10),
    )).search_repositories_page_result(
        "lumenis", limit=10, cancel_check=lambda: next(checks),
    )
    assert result.items == [{"id": 1, "full_name": "owner/allowed"}]
    assert result.coverage_complete is False
    assert result.partial_reason == "CANCELLED"
    assert result.next_cursor["page"] == 2
    adapted = GitHubAdapter._page_result(result, "search")
    assert adapted.status == CollectionStatus.COLLECT_ERROR
    assert adapted.ok is False
    assert len(adapted.items) == 1
    assert adapted.metadata["coverage_complete"] is False


def test_cancel_check_failure_is_reported_with_resumable_partial_result():
    checks = iter((False, RuntimeError("synthetic cancellation failure")))

    def cancel_check():
        value = next(checks)
        if isinstance(value, Exception):
            raise value
        return value

    page = _connector(lambda request, timeout: _page(
        [{"id": 1, "full_name": "owner/allowed"}], total=2,
        headers=_link(2, per_page=10),
    )).search_repositories_page_result(
        "lumenis", limit=10, cancel_check=cancel_check,
    )
    assert page.items == [{"id": 1, "full_name": "owner/allowed"}]
    assert page.coverage_complete is False
    assert page.partial_reason == "CANCELLATION_CHECK_FAILED"
    assert page.error_code == "CANCELLATION_CHECK_FAILED"
    assert page.next_cursor["page"] == 2


def test_invalid_page_item_or_next_link_cannot_be_reported_complete():
    invalid_item = _connector(lambda request, timeout: _page(
        [{"id": 1, "full_name": "owner/allowed"}, "invalid"], total=2,
    )).search_repositories_page_result("lumenis", limit=10)
    assert invalid_item.api_items_observed == 2
    assert len(invalid_item.items) == 1
    assert invalid_item.coverage_complete is False
    assert invalid_item.partial_reason == "INVALID_PAGE_ITEM"
    assert invalid_item.error_code == "INVALID_PROVIDER_RESPONSE"

    malformed_link = _connector(lambda request, timeout: _page(
        [{"id": 1, "full_name": "owner/allowed"}], total=2,
        headers={"Link": 'not-a-url; rel="next'},
    )).search_repositories_page_result("lumenis", limit=10)
    assert len(malformed_link.items) == 1
    assert malformed_link.coverage_complete is False
    assert malformed_link.partial_reason == "PAGINATION_LINK_REJECTED"
    assert malformed_link.error_code == "INVALID_PAGINATION_LINK"


def test_later_page_failure_preserves_partial_items_without_success_status():
    calls = 0

    def opener(request, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            return _page(
                [{"id": 1, "full_name": "owner/allowed"}], total=2, headers=_link(2, per_page=10),
            )
        raise _http_error(429, headers={"Retry-After": "10"})

    page = _connector(opener).search_repositories_page_result("lumenis", limit=10)
    result = GitHubAdapter._page_result(page, "search")
    assert result.status == CollectionStatus.COOLING_DOWN
    assert result.ok is False
    assert len(result.items) == 1
    assert result.metadata["coverage_complete"] is False
    assert result.metadata["error_code"] == "RATE_LIMITED"
    assert result.metadata["retry_after_seconds"] == 10.0


def test_rate_limit_retries_only_short_wait_and_permission_is_not_auth_expiry(monkeypatch):
    calls = []
    sleeps = []

    def short_retry_opener(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise _http_error(429, headers={"Retry-After": "1"})
        return _Response({"ok": True})

    assert _connector(short_retry_opener, sleep=sleeps.append).get_json("/user") == {"ok": True}
    assert len(calls) == 2
    assert sleeps == [1.0]

    rate = _connector(lambda request, timeout: (_ for _ in ()).throw(
        _http_error(429, headers={"Retry-After": "10"}),
    ))
    with pytest.raises(GitHubConnectorError) as error:
        rate.get_json("/user")
    assert error.value.code == "RATE_LIMITED"
    assert error.value.retry_after_seconds == 10.0

    primary_rate_limit_without_reset = _connector(lambda request, timeout: (_ for _ in ()).throw(
        _http_error(403, headers={"X-RateLimit-Remaining": "0"}),
    ))
    with pytest.raises(GitHubConnectorError) as error:
        primary_rate_limit_without_reset.get_json("/user")
    assert error.value.code == "RATE_LIMITED"
    assert error.value.retry_after_seconds is None

    permission = _connector(lambda request, timeout: (_ for _ in ()).throw(
        _http_error(403, message="Resource not accessible by integration"),
    ))
    with pytest.raises(GitHubConnectorError) as error:
        permission.get_json("/user")
    assert error.value.code == "PERMISSION_DENIED"
    assert GitHubAdapter._error(error.value, "healthcheck").status == CollectionStatus.BLOCKED

    expired = GitHubAdapter._error(
        GitHubConnectorError("AUTHENTICATION_FAILED", "expired"), "healthcheck",
    )
    assert expired.status == CollectionStatus.SESSION_EXPIRED

    rate_limited_forbidden = _connector(lambda request, timeout: (_ for _ in ()).throw(
        _http_error(403, headers={"Retry-After": "20"}),
    ))
    with pytest.raises(GitHubConnectorError) as error:
        rate_limited_forbidden.get_json("/user")
    assert error.value.code == "RATE_LIMITED"
    assert error.value.retry_after_seconds == 20.0

    monkeypatch.setattr("github_connector.time.time", lambda: 100.0)
    primary_rate_limit = _connector(lambda request, timeout: (_ for _ in ()).throw(
        _http_error(403, headers={
            "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "110",
        }),
    ))
    with pytest.raises(GitHubConnectorError) as error:
        primary_rate_limit.get_json("/user")
    assert error.value.code == "RATE_LIMITED"
    assert error.value.retry_after_seconds == 10.0

    unauthenticated = _connector(lambda request, timeout: (_ for _ in ()).throw(
        _http_error(401),
    ))
    with pytest.raises(GitHubConnectorError) as error:
        unauthenticated.get_json("/user")
    assert error.value.code == "AUTHENTICATION_FAILED"


def test_noncanonical_api_origin_is_rejected_before_tokenized_request():
    calls = []
    connector = GitHubConnector(
        config=GitHubConnectorConfig(
            repositories=("owner/allowed",), api_base="https://api.example.test",
        ),
        token_provider=lambda: "synthetic-token",
        opener=lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    with pytest.raises(GitHubConnectorError) as error:
        connector.get_json("/user")
    assert error.value.code == "API_ORIGIN_NOT_ALLOWLISTED"
    assert calls == []


def test_redirect_requires_same_github_api_origin_and_allowlisted_repo():
    connector = _connector(lambda *args, **kwargs: pytest.fail("no network expected"))
    default_connector = GitHubConnector(token_provider=lambda: "synthetic-token")
    default_opener = default_connector._opener.__self__
    assert any(isinstance(item, _GitHubRedirectHandler) for item in default_opener.handlers)
    handler = _GitHubRedirectHandler(connector)
    request = Request("https://api.github.com/user", headers={"Authorization": "Bearer synthetic"})

    with pytest.raises(GitHubConnectorError) as error:
        handler.redirect_request(request, None, 302, "Found", {}, "https://evil.example/user")
    assert error.value.code == "REDIRECT_BLOCKED"
    with pytest.raises(GitHubConnectorError) as error:
        handler.redirect_request(
            request, None, 302, "Found", {},
            "https://api.github.com/repos/owner/blocked/issues",
        )
    assert error.value.code == "REPOSITORY_NOT_ALLOWLISTED"

    page = _connector(lambda *args, **kwargs: _page(
        [{"id": 1, "full_name": "owner/allowed"}], total=2,
        headers={"Link": (
            '<https://evil.example/search/repositories?q=lumenis&per_page=10&page=2>; rel="next"'
        )},
    )).search_repositories_page_result("lumenis", limit=10)
    result = GitHubAdapter._page_result(page, "search")
    assert result.status == CollectionStatus.BLOCKED
    assert result.ok is False
    assert result.metadata["error_code"] == "REDIRECT_BLOCKED"
    assert len(result.items) == 1


@pytest.mark.parametrize(
    "options, expected_code",
    [({"limit": 0}, "INVALID_PAGINATION_LIMIT"),
     ({"limit": 1001}, "INVALID_PAGINATION_LIMIT"),
     ({"max_pages": 21}, "INVALID_PAGE_BUDGET")],
)
def test_pagination_bounds_reject_invalid_values_before_network(options, expected_code):
    calls = []
    connector = _connector(lambda *args, **kwargs: calls.append((args, kwargs)))
    with pytest.raises(GitHubConnectorError) as error:
        connector.search_repositories_page_result("lumenis", **options)
    assert error.value.code == expected_code
    assert calls == []


def test_malformed_port_in_pagination_link_is_a_bounded_connector_failure():
    result = _connector(lambda request, timeout: _page(
        [{"id": 1, "full_name": "owner/allowed"}], total=2,
        headers={"Link": '<https://api.github.com:bad/search/repositories?q=lumenis&per_page=10&page=2>; rel="next"'},
    )).search_repositories_page_result("lumenis", limit=10)
    assert result.coverage_complete is False
    assert result.error_code == "REDIRECT_BLOCKED"
    assert result.partial_reason == "PAGINATION_LINK_REJECTED"


def test_user_health_probe_does_not_claim_repository_permission():
    connector = GitHubConnector(token_provider=lambda: "synthetic-token")
    connector.get_json = lambda path: {"login": "fixture-owner"}
    result = GitHubAdapter(connector=connector).health_check()
    assert result.metadata["authorization_verification"] == "CURRENT_USER_VERIFIED"
    assert result.metadata["repository_access_verification"] == "NOT_VERIFIED"
