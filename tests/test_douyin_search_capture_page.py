"""The Douyin search collector uses the authorized context without page stealth patches."""

from types import SimpleNamespace

import pytest


class _Page:
    def __init__(self, request=None):
        self.request = request
        self.request_finished = False
        self.request_finished_handler = None
        self.closed = False

    def on(self, name, handler):
        assert name == "requestfinished"
        self.request_finished_handler = handler

    def goto(self, *_args, **_kwargs):
        if self.request is not None:
            self.request_finished = True
            self.request_finished_handler(self.request)

    def wait_for_function(self, *_args, **_kwargs):
        return None

    def close(self):
        self.closed = True


class _Worker:
    def __init__(self, page, states=None):
        self._context = object()
        self.page = page
        self.new_page_options = None
        self.states = iter(states or ["SUCCESS"])
        self.last_state = "SUCCESS"
        self.scroll_calls = 0
        self.closed = False

    def connect(self):
        return self

    def new_page(self, **kwargs):
        self.new_page_options = kwargs
        return self.page

    def detect_state(self, *_args, **_kwargs):
        self.last_state = next(self.states, self.last_state)
        return self.last_state

    def human_scroll(self, *_args, **_kwargs):
        self.scroll_calls += 1

    @staticmethod
    def pause(*_args):
        return None

    def close(self):
        self.closed = True


def test_search_reads_single_and_stream_bodies_after_request_finished(monkeypatch):
    import json
    from lumenis.adapters import douyin

    def run_search(endpoint):
        bag = {"status_code": 0, "data": [{"aweme_info": {
            "aweme_id": "test-aweme-1", "desc": "public result",
            "create_time": 1789171200,
            "author": {"nickname": "public author", "uid": "public-author-id"},
            "statistics": {"digg_count": 0},
        }}]}
        url = f"https://www.douyin.com/aweme/v1/web/general/search/{endpoint}/"
        body = json.dumps(bag)
        page = _Page()
        response_reads = []
        response = SimpleNamespace(
            json=lambda: (assert_finished(page) or response_reads.append("json") or bag),
            text=lambda: (assert_finished(page) or response_reads.append("text") or body),
        )
        request = SimpleNamespace(
            url=url, resource_type="xhr",
            response=lambda: (assert_finished(page) or response),
        )
        page.request = request
        worker = _Worker(page)
        monkeypatch.setattr(douyin, "_new_browser_worker", lambda: worker)
        monkeypatch.setattr(douyin, "inject_into_context", lambda *_args: 0)

        result = douyin.DouyinAdapter().search("Guangzhou", max_results=1)
        assert worker.new_page_options == {"stealth": False}
        assert page.request_finished is True
        assert response_reads == ["text" if endpoint == "stream" else "json"]
        assert result.success is True
        assert result.raw_count == 1
        assert result.notes[0].raw_data["aweme_id"] == "test-aweme-1"
        assert result.notes[0].author_id == "public-author-id"
        assert result.notes[0].likes == 0
        assert result.notes[0].comments is None
        return result

    for endpoint in ("single", "stream"):
        result = run_search(endpoint)
        from lumenis.system.collector.adapters.douyin import DouyinAdapter as SystemDouyinAdapter
        detail_calls = []
        def exact_detail(*, aweme_id, observed=result, calls=detail_calls):
            calls.append(aweme_id)
            assert aweme_id == observed.notes[0].raw_data["aweme_id"]
            return observed
        system = SystemDouyinAdapter(backend=SimpleNamespace(
            search=lambda *_args, **_kwargs: result,
            detail=exact_detail,
        )).search("Guangzhou", max_results=1)
        assert system.status.value == "SUCCESS"
        assert system.items[0]["author_id"] == "public-author-id"
        assert system.items[0]["likes"] == 0
        assert system.items[0]["comments"] is None
        assert detail_calls == ["test-aweme-1"]


def assert_finished(page):
    assert page.request_finished is True
    return False


def test_search_without_finished_search_response_does_not_claim_empty(monkeypatch):
    from lumenis.adapters import douyin

    page = _Page()
    worker = _Worker(page)
    monkeypatch.setattr(douyin, "_new_browser_worker", lambda: worker)
    monkeypatch.setattr(douyin, "inject_into_context", lambda *_args: 0)
    monkeypatch.setattr(douyin.DouyinAdapter, "_parse_dom", lambda *_args: [])

    result = douyin.DouyinAdapter().search("Guangzhou", max_results=1)

    assert result.success is False
    assert "不能确认为无新内容" in result.error


def _observed_search_request(bag):
    return SimpleNamespace(
        url="https://www.douyin.com/aweme/v1/web/general/search/single/",
        resource_type="xhr",
        response=lambda: SimpleNamespace(json=lambda: bag),
    )


def _partial_search_bag():
    return {"status_code": 0, "data": [{"aweme_info": {
        "aweme_id": "partial-aweme", "desc": "Already observed search caption",
        "create_time": 1789171200, "statistics": {"digg_count": 0},
    }}]}


@pytest.mark.parametrize("state,expected_status", [
    ("CAPTCHA", "RISK_WARNING"),
    ("BLOCKED", "RISK_WARNING"),
    ("AUTH_FAILED", "SESSION_EXPIRED"),
    ("NETWORK_ERROR", "PROVIDER_UNAVAILABLE"),
])
@pytest.mark.parametrize("rendered", [True, False])
@pytest.mark.parametrize("partial_observation", [True, False])
def test_search_stops_at_observed_failure_without_scrolling_or_fallback(
        monkeypatch, state, expected_status, rendered, partial_observation):
    from lumenis.adapters import douyin
    from lumenis.system.collector.adapters.douyin import DouyinAdapter as SystemAdapter

    bag = _partial_search_bag() if partial_observation else {"status_code": 0, "data": []}
    page = _Page(_observed_search_request(bag))
    if not rendered:
        def unavailable_render(*_args, **_kwargs):
            raise TimeoutError("Result duration badge was not observed")
        page.wait_for_function = unavailable_render
    worker = _Worker(page, states=[state])
    monkeypatch.setattr(douyin, "_new_browser_worker", lambda: worker)
    monkeypatch.setattr(douyin, "inject_into_context", lambda *_args: 0)

    def forbidden_followup(*_args, **_kwargs):
        pytest.fail("Observed search failure must stop DOM fallback and post-detail work")
    monkeypatch.setattr(douyin.DouyinAdapter, "_parse_dom", forbidden_followup)
    result = douyin.DouyinAdapter().search("Guangzhou", max_results=1)
    assert result.success is False
    assert result.raw_count == len(result.notes) == int(partial_observation)
    assert worker.scroll_calls == 0
    assert page.closed is True and worker.closed is True
    backend = SimpleNamespace(search=lambda *_args, **_kwargs: result, detail=forbidden_followup)
    system = SystemAdapter(backend=backend).search("Guangzhou", max_results=1)
    assert system.status.value == expected_status
    if partial_observation:
        assert result.notes[0].likes == 0 and result.notes[0].comments is None
        assert system.items[0]["raw"]["detail_observation"]["status"] == "PENDING"
        assert system.items[0]["content"] == system.items[0]["title"] == ""


@pytest.mark.parametrize("state", ["CAPTCHA", "BLOCKED", "AUTH_FAILED", "NETWORK_ERROR"])
def test_search_stops_when_failure_appears_after_first_scroll(monkeypatch, state):
    from lumenis.adapters import douyin

    page = _Page()
    worker = _Worker(page, states=["SUCCESS", state])
    def first_scroll(*_args, **_kwargs):
        worker.scroll_calls += 1
        page.request_finished_handler(_observed_search_request(_partial_search_bag()))
    worker.human_scroll = first_scroll
    monkeypatch.setattr(douyin, "_new_browser_worker", lambda: worker)
    monkeypatch.setattr(douyin, "inject_into_context", lambda *_args: 0)
    monkeypatch.setattr(douyin.DouyinAdapter, "_parse_dom",
                        lambda *_args: pytest.fail("No DOM fallback after an observed failure"))
    result = douyin.DouyinAdapter().search("Guangzhou", max_results=2)
    assert result.success is False
    assert result.raw_count == len(result.notes) == 1
    assert worker.scroll_calls == 1
    assert page.closed is True and worker.closed is True


def test_verified_empty_search_remains_successful_without_failure(monkeypatch):
    from lumenis.adapters import douyin

    page = _Page(_observed_search_request({"status_code": 0, "data": []}))
    worker = _Worker(page, states=["EMPTY"])
    monkeypatch.setattr(douyin, "_new_browser_worker", lambda: worker)
    monkeypatch.setattr(douyin, "inject_into_context", lambda *_args: 0)
    monkeypatch.setattr(douyin.DouyinAdapter, "_parse_dom", lambda *_args: [])
    result = douyin.DouyinAdapter().search("Guangzhou", max_results=1)
    assert result.success is True and result.notes == [] and result.raw_count == 0
    assert page.closed is True and worker.closed is True


@pytest.mark.parametrize(("statistics", "expected"), [
    ({"play_count": 41}, 41),
    ({"play_count": 0}, 0),
    ({}, None),
    ({"play_count": None}, None),
    ({"play_count": True}, None),
    ({"play_count": -1}, None),
    ({"play_count": "41"}, None),
])
def test_search_play_count_is_optional_native_metric(statistics, expected):
    from lumenis.adapters.douyin import DouyinAdapter as V4DouyinAdapter
    from lumenis.system.collector.adapters.douyin import (
        DouyinAdapter as SystemDouyinAdapter,
    )

    bag = {"data": [{"aweme_info": {
        "aweme_id": "native-aweme-1", "desc": "Observed search caption",
        "create_time": 1789171200, "statistics": statistics,
    }}]}
    note = V4DouyinAdapter()._notes_from_bags([bag], max_results=1)[0]
    item = SystemDouyinAdapter()._v4_notes_to_items([note])[0]

    assert note.raw_data["play_count"] == expected
    assert item["views"] == expected


def _douyin_note(raw, *, content, publish_date, url="https://www.douyin.com/video/native-aweme-1"):
    return SimpleNamespace(
        raw_data=raw,
        title=content[:80],
        content=content,
        author_id="native-author-1",
        author="Native author",
        publish_date=publish_date,
        url=url,
        likes=3,
        comments=2,
        collects=1,
        shares=4,
    )


def _douyin_result(success, notes, error=""):
    return SimpleNamespace(
        success=success,
        notes=notes,
        error=error,
        raw_count=len(notes),
        duration_seconds=0.1,
    )


@pytest.mark.parametrize(("detail_metrics", "detail_time_state", "expected_views"), [
    ({"play_count": 0}, "native", 0),
    ({"play_count": 9}, "native", 9),
    ({}, "native", None),
    ({"play_count": None}, "native", None),
    ({"play_count": True}, "native", None),
    ({"play_count": -1}, "native", None),
    ({"play_count": "9"}, "native", None),
    ({"play_count": 0}, "missing", 0),
    ({"play_count": 0}, "null", 0),
])
def test_exact_detail_replaces_search_metrics_and_native_time_without_losing_summary(
        detail_metrics, detail_time_state, expected_views):
    from copy import deepcopy

    from lumenis.system.collector.adapters.douyin import (
        DouyinAdapter as SystemDouyinAdapter,
    )
    from lumenis.system.collector.adapters.platform_naming import (
        map_raw_to_normalized,
        to_canonical_record,
    )
    from lumenis.system.collector.adapters.secondary_collection import _native_record

    search_time = 1789171200
    search_raw = {
        "engine": "douyin_search_api", "aweme_id": "native-aweme-1",
        "create_time": search_time, "play_count": 41,
    }
    detail_raw = {
        "engine": "douyin_detail_api", "aweme_id": "native-aweme-1",
        "metrics": detail_metrics, "native_time_locator": "$.aweme_detail.create_time",
        "metrics_locator": "$.aweme_detail.statistics",
        "body_locator": "$.aweme_detail.desc",
    }
    detail_time = 1789257600
    if detail_time_state == "native":
        detail_raw["create_time"] = detail_time
    elif detail_time_state == "null":
        detail_raw["create_time"] = None
    original_search_raw = deepcopy(search_raw)
    original_detail_raw = deepcopy(detail_raw)
    search_note = _douyin_note(search_raw, content="Search summary", publish_date="search-date")
    detail_note = _douyin_note(
        detail_raw, content="Native detail body", publish_date="detail-date",
    )
    search_result = _douyin_result(True, [search_note])
    detail_result = _douyin_result(True, [detail_note])
    backend = SimpleNamespace(
        search=lambda *_args, **_kwargs: search_result,
        detail=lambda *, aweme_id: detail_result,
    )

    result = SystemDouyinAdapter(backend=backend).search("topic", max_results=1)
    item = result.items[0]
    raw = item["raw"]
    summary = raw["search_summary_observation"]
    detail = raw["detail_observation"]

    assert result.status.value == "SUCCESS"
    assert item["content"] == "Native detail body"
    assert item["publish_datetime"] == "detail-date"
    assert item["views"] == expected_views
    assert raw["play_count"] == expected_views
    expected_time = detail_time if detail_time_state == "native" else None
    assert raw["create_time"] == expected_time
    assert summary["metrics"]["views"] == 41
    assert summary["native_time"] == search_time
    assert detail["native_time"] == expected_time
    assert detail["native_time_status"] == (
        "OBSERVED" if detail_time_state == "native" else "NOT_RETURNED_BY_DETAIL"
    )
    native_record = _native_record(item, "douyin", "topic", "capture-time")
    canonical = to_canonical_record(native_record, "douyin")
    assert map_raw_to_normalized(native_record, "douyin")["view_count"] == expected_views
    assert canonical["raw"]["play_count"] == expected_views
    assert canonical["published_at"] == expected_time
    assert detail["native_time_locator"] == "$.aweme_detail.create_time"
    assert detail["metrics_locator"] == "$.aweme_detail.statistics"
    assert search_raw == original_search_raw
    assert detail_raw == original_detail_raw


@pytest.mark.parametrize("failure_stage", ["partial_search", "detail_failure"])
def test_unfinished_detail_keeps_search_metrics_archived_but_current_values_unknown(failure_stage):
    from copy import deepcopy

    from lumenis.system.collector.adapters.douyin import (
        DouyinAdapter as SystemDouyinAdapter,
    )

    search_raw = {
        "engine": "douyin_search_api", "aweme_id": "native-aweme-1",
        "create_time": 1789171200, "play_count": 41,
    }
    original_search_raw = deepcopy(search_raw)
    search_note = _douyin_note(search_raw, content="Search summary", publish_date="search-date")
    if failure_stage == "partial_search":
        search_result = _douyin_result(False, [search_note], "provider unavailable")
        detail_calls = []

        def detail(**_kwargs):
            detail_calls.append(True)
            return _douyin_result(True, [])
    else:
        search_result = _douyin_result(True, [search_note])
        detail_calls = []

        def detail(**_kwargs):
            detail_calls.append(True)
            return _douyin_result(False, [], "provider unavailable")

    result = SystemDouyinAdapter(backend=SimpleNamespace(
        search=lambda *_args, **_kwargs: search_result,
        detail=detail,
    )).search("topic", max_results=1)
    item = result.items[0]
    raw = item["raw"]

    assert raw["detail_observation"]["status"] == (
        "PENDING" if failure_stage == "partial_search" else "PROVIDER_UNAVAILABLE"
    )
    assert item["views"] is None
    assert raw["play_count"] is None
    assert raw["create_time"] == 1789171200
    assert raw["search_summary_observation"]["metrics"]["views"] == 41
    assert raw["search_summary_observation"]["native_time"] == 1789171200
    assert detail_calls == ([] if failure_stage == "partial_search" else [True])
    assert search_raw == original_search_raw
