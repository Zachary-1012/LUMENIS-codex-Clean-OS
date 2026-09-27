"""The Douyin search collector uses the authorized context without page stealth patches."""

from types import SimpleNamespace


class _Page:
    def __init__(self, response):
        self.response = response
        self.response_handler = None

    def on(self, name, handler):
        assert name == "response"
        self.response_handler = handler

    def goto(self, *_args, **_kwargs):
        self.response_handler(self.response)

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


def test_search_uses_normal_context_page_and_captures_single_response(monkeypatch):
    from lumenis.adapters import douyin

    bag = {"status_code": 0, "data": [{"aweme_info": {
        "aweme_id": "test-aweme-1", "desc": "public result",
        "create_time": 1789171200,
        "author": {"nickname": "public author", "uid": "public-author-id"},
        "statistics": {"digg_count": 0},
    }}]}
    response = SimpleNamespace(
        url="https://www.douyin.com/aweme/v1/web/general/search/single/",
        request=SimpleNamespace(resource_type="xhr"),
        json=lambda: bag,
    )
    page = _Page(response)
    worker = _Worker(page)
    monkeypatch.setattr(douyin, "_new_browser_worker", lambda: worker)
    monkeypatch.setattr(douyin, "inject_into_context", lambda *_args: 0)

    result = douyin.DouyinAdapter().search("广州太古汇", max_results=1)

    assert worker.new_page_options == {"stealth": False}
    assert result.success is True
    assert result.raw_count == 1
    assert result.notes[0].raw_data["aweme_id"] == "test-aweme-1"
    assert result.notes[0].author_id == "public-author-id"
    assert result.notes[0].likes == 0
    assert result.notes[0].comments is None

    from lumenis.system.collector.adapters.douyin import DouyinAdapter as SystemDouyinAdapter

    system = SystemDouyinAdapter(backend=SimpleNamespace(
        search=lambda *_args, **_kwargs: result,
    )).search("广州太古汇", max_results=1)
    assert system.status.value == "SUCCESS"
    assert system.items[0]["author_id"] == "public-author-id"
    assert system.items[0]["likes"] == 0
    assert system.items[0]["comments"] is None
