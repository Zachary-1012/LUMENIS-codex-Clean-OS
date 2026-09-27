"""The Douyin search collector uses the authorized context without page stealth patches."""

from types import SimpleNamespace


class _Page:
    def __init__(self, request=None):
        self.request = request
        self.request_finished = False
        self.request_finished_handler = None

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
        return None


class _Worker:
    def __init__(self, page):
        self._context = object()
        self.page = page
        self.new_page_options = None

    def connect(self):
        return self

    def new_page(self, **kwargs):
        self.new_page_options = kwargs
        return self.page

    def detect_state(self, *_args, **_kwargs):
        return "SUCCESS"

    def human_scroll(self, *_args, **_kwargs):
        return None

    @staticmethod
    def pause(*_args):
        return None

    def close(self):
        return None


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
        system = SystemDouyinAdapter(backend=SimpleNamespace(
            search=lambda *_args, **_kwargs: result,
        )).search("Guangzhou", max_results=1)
        assert system.status.value == "SUCCESS"
        assert system.items[0]["author_id"] == "public-author-id"
        assert system.items[0]["likes"] == 0
        assert system.items[0]["comments"] is None


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
