"""Main adapter/caller window regressions with explicit offline native fixtures."""
from __future__ import annotations

import importlib
import socket

import pytest


class _Locator:
    def all_text_contents(self):
        return []


class _Page:
    def on(self, *_args):
        pass

    def remove_listener(self, *_args):
        pass

    def goto(self, *_args, **_kwargs):
        pass

    def wait_for_timeout(self, *_args):
        pass

    def locator(self, *_args):
        return _Locator()

    def close(self):
        pass


class _Worker:
    _context = object()

    def connect(self):
        pass

    def new_page(self, **_kwargs):
        return _Page()

    def close(self):
        pass


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('offline window regression touched the network')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)


def _backend(monkeypatch, platform, selected):
    from lumenis.adapters.human_browser import NativeReadCapture
    module_name = 'x_platform' if platform == 'x' else platform
    module = importlib.import_module('lumenis.adapters.' + module_name)
    monkeypatch.setattr(module, 'inject_into_context', lambda *_args: 0)
    if platform in {'douyin', 'x'}:
        monkeypatch.setattr(module, '_new_browser_worker', _Worker)
    else:
        monkeypatch.setattr(module, 'configured_readonly_worker_url', lambda _platform: 'https://registered-fixture.example.test')
        monkeypatch.setattr(module, 'HumanBrowser', lambda **_kwargs: _Worker())
    monkeypatch.setattr(NativeReadCapture, 'seek', lambda *_args, **_kwargs: selected)
    cls = {'douyin': 'DouyinAdapter', 'instagram': 'InstagramAdapter',
           'facebook': 'FacebookAdapter', 'x': 'XAdapter'}[platform]
    return getattr(module, cls)()


def _tweet(identity):
    return {'rest_id': str(identity), 'legacy': {'full_text': 'Native post', 'truncated': False},
            'core': {'user_results': {'result': {'rest_id': '99', 'legacy': {'screen_name': 'source_author'}}}}}


def _search_page(platform):
    if platform == 'douyin':
        rows = [{'aweme_info': {'aweme_id': str(i), 'desc': 'Native caption',
                               'author': {'sec_uid': 'source_author'}, 'statistics': {'digg_count': 0}}}
                for i in (123456, 123457, 123458)]
        return {'body': {'status_code': 0, 'has_more': 1, 'cursor': 9, 'data': rows,
                         'log_pb': {'impr_id': 'next-search-context'}}, 'rows': rows,
                'observed_prior_native_responses': 0}
    if platform == 'instagram':
        rows = [{'id': str(i), 'shortcode': 'code' + str(i), 'caption': {'text': 'Native caption'},
                 'owner': {'id': '99', 'username': 'source_author'}} for i in (123456, 123457, 123458)]
        return {'container': {'page_info': {'has_next_page': True, 'end_cursor': 'native-next'}},
                'rows': rows, 'media_id': '99', 'observed_prior_native_responses': 0}
    if platform == 'facebook':
        rows = [{'post_id': '99_' + str(i), 'url': 'https://www.facebook.com/99/posts/' + str(i),
                 'message': {'text': 'Native post', 'is_truncated': False}, 'owner': {'id': '99'}}
                for i in (123456, 123457, 123458)]
        return {'connection': {'page_info': {'has_next_page': True, 'end_cursor': 'native-next'}},
                'rows': rows, 'observed_prior_native_responses': 0}
    return {'tweets': [_tweet(i) for i in (123456, 123457, 123458)],
            'cursors': [{'cursor': 'native-next', 'kind': 'Bottom', 'entry_id': 'bottom'}],
            'terminated': False, 'request': {}, 'observed_prior_native_responses': 0}


@pytest.mark.parametrize('platform', ['douyin', 'instagram', 'facebook', 'x'])
def test_main_callable_returns_every_native_item_before_next_page(monkeypatch, platform):
    selected = _search_page(platform)
    backend = _backend(monkeypatch, platform, selected)
    cursor, ids = None, []
    for offset in range(3):
        # Instagram's native author timeline shares this window path; its
        # keyword discovery DOM is a different, explicitly partial capability.
        if platform == 'instagram':
            result = backend.author_posts('source_author', max_results=1, cursor=cursor)
        else:
            result = backend.search('source query', max_results=1, cursor=cursor)
        assert result.success, result.error
        assert len(result.notes) == 1
        ids.append(result.notes[0].url)
        page = result.metadata['pagination']
        assert page['window_start'] == offset
        cursor = page['next_cursor']
        if offset < 2:
            assert cursor['item_offset'] == offset + 1
            if platform == 'douyin':
                assert cursor['offset'] == '0' and 'search_id' not in cursor
        else:
            assert 'item_offset' not in cursor and 'page_sha256' not in cursor
    assert len(set(ids)) == 3


@pytest.mark.parametrize('platform', ['douyin', 'instagram', 'facebook', 'x'])
def test_main_callable_rejects_changed_page_without_advancing_saved_position(monkeypatch, platform):
    selected = _search_page(platform)
    backend = _backend(monkeypatch, platform, selected)
    call = backend.author_posts if platform == 'instagram' else backend.search
    first = call('source_author' if platform == 'instagram' else 'source query', max_results=1)
    rows = selected['tweets'] if platform == 'x' else selected['rows']
    rows.reverse()
    result = call('source_author' if platform == 'instagram' else 'source query', max_results=1,
                  cursor=first.metadata['pagination']['next_cursor'])
    assert result.success is False and result.error.endswith('NATIVE_CURSOR_PAGE_CHANGED')
    assert result.raw_count is None and result.notes == []
    assert result.metadata['pagination']['resume_requires_fresh_page'] is True


@pytest.mark.parametrize('platform', ['douyin', 'instagram', 'facebook'])
def test_reply_native_window_returns_to_unread_roots(monkeypatch, platform):
    if platform == 'douyin':
        rows = [{'cid': '102', 'aweme_id': '123456', 'text': 'reply one'},
                {'cid': '103', 'aweme_id': '123456', 'text': 'reply two'}]
        selected = {'body': {'has_more': 0, 'cursor': '9'}, 'rows': rows, 'observed_prior_native_responses': 0}
        root_cursor = {'mode': 'roots', 'cursor': '0', 'item_offset': 1, 'page_sha256': 'a' * 64}
        cursor = {'mode': 'replies', 'root_id': '1', 'cursor': '0', 'pending_roots': [],
                  'next_root': root_cursor, 'root_exhausted': False}
        target = '123456'
    elif platform == 'instagram':
        selected = {'container': {'has_more_comments': False}, 'rows': [{'pk': '102', 'text': 'reply one'},
                    {'pk': '103', 'text': 'reply two'}], 'media_id': '99', 'observed_prior_native_responses': 0}
        root_cursor = {'mode': 'roots', 'media_id': '99', 'page': {}, 'item_offset': 1, 'page_sha256': 'a' * 64}
        cursor = {'mode': 'replies', 'media_id': '99', 'root_id': '1', 'page': {}, 'pending_roots': [],
                  'next_root': root_cursor, 'root_exhausted': False}
        target = 'sourceCode'
    else:
        selected = {'connection': {'page_info': {'has_next_page': False}}, 'rows': [
                    {'legacy_fbid': '102', 'body': {'text': 'reply one'}},
                    {'legacy_fbid': '103', 'body': {'text': 'reply two'}}], 'observed_prior_native_responses': 0}
        root_cursor = {'mode': 'roots', 'after': '', 'item_offset': 1, 'page_sha256': 'a' * 64}
        cursor = {'mode': 'replies', 'root_id': '1', 'root_resource_id': 'feedback-1', 'after': '',
                  'pending_roots': [], 'next_root': root_cursor, 'root_exhausted': False}
        target = 'https://www.facebook.com/99/posts/123456'
    backend = _backend(monkeypatch, platform, selected)
    first = backend.comments(target, max_comments=1, cursor=cursor, include_replies=True)
    assert first.success, first.error
    next_cursor = first.metadata['pagination']['next_cursor']
    assert next_cursor['mode'] == 'replies' and next_cursor['item_offset'] == 1
    second = backend.comments(target, max_comments=1, cursor=next_cursor, include_replies=True)
    assert second.success, second.error
    returned_root = second.metadata['pagination']['next_cursor']
    assert {key: value for key, value in returned_root.items() if key != 'reply_scope_unknown'} == root_cursor
    assert returned_root['reply_scope_unknown'] is True
    assert second.metadata['pagination']['exhausted'] is False


@pytest.mark.parametrize('platform', ['douyin', 'instagram', 'facebook'])
@pytest.mark.parametrize(('reply_count', 'expected'), [(0, True), (None, None)])
def test_reply_completion_requires_observed_native_root_totals(monkeypatch, platform, reply_count, expected):
    if platform == 'douyin':
        row = {'cid': '101', 'aweme_id': '123456', 'text': 'Native top level comment',
               'reply_comment': [], 'reply_comment_total': reply_count}
        selected = {'body': {'status_code': 0, 'has_more': 0, 'cursor': '0', 'total': 1},
                    'rows': [row], 'observed_prior_native_responses': 0}
        backend = _backend(monkeypatch, platform, selected)
        target = '123456'
    elif platform == 'instagram':
        row = {'pk': '101', 'text': 'Native top level comment', 'owner': {'pk': '99', 'username': 'author'},
               'child_comment_count': reply_count, 'edge_threaded_comments': {'edges': []}}
        selected = {'container': {'page_info': {'has_next_page': False}, 'count': 1},
                    'rows': [row], 'media_id': '99', 'observed_prior_native_responses': 0}
        backend = _backend(monkeypatch, platform, selected)
        target = 'sourceCode'
    else:
        row = {'legacy_fbid': '101', 'body': {'text': 'Native top level comment'},
               'comment_replies': {'edges': [], 'count': reply_count}}
        selected = {'connection': {'page_info': {'has_next_page': False}, 'count': 1},
                    'rows': [row], 'observed_prior_native_responses': 0}
        backend = _backend(monkeypatch, platform, selected)
        target = 'https://www.facebook.com/99/posts/123456'

    result = backend.comments(target, max_comments=10, include_replies=True)
    assert result.success, result.error
    pagination = result.metadata['pagination']
    assert pagination['exhausted'] is True
    assert pagination['replies_complete'] is expected
