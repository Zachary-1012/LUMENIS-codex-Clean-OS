"""Offline HTTP status and empty-result behavior for legacy search adapters."""

import pytest
import requests

from lumenis.adapters.baidu_search import BaiduSearchAdapter
from lumenis.adapters.bing_search import BingSearchAdapter


@pytest.fixture(params=[BaiduSearchAdapter, BingSearchAdapter])
def search_adapter(request):
    return request.param()


def _response(status_code: int, body: str) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://search.example.test/results"
    response._content = body.encode("utf-8")
    response.encoding = "utf-8"
    return response


def test_http_error_is_not_reported_as_successful_empty(search_adapter, monkeypatch):
    error_page = "<html><body>Service unavailable</body></html>"
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: _response(503, error_page))

    result = search_adapter.search("offline fixture")

    assert result.success is False
    assert result.notes == []
    assert "503" in result.error


def test_http_200_without_matches_is_a_successful_empty_result(search_adapter, monkeypatch):
    empty_page = "<html><body>No matching results</body></html>"
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: _response(200, empty_page))

    result = search_adapter.search("offline fixture")

    assert result.success is True
    assert result.notes == []
    assert result.raw_count == 0


def test_transport_error_is_not_reported_as_successful_empty(search_adapter, monkeypatch):
    def fail_transport(*args, **kwargs):
        raise requests.Timeout("offline timeout fixture")

    monkeypatch.setattr(requests, "get", fail_transport)

    result = search_adapter.search("offline fixture")

    assert result.success is False
    assert result.notes == []
    assert "offline timeout fixture" in result.error
