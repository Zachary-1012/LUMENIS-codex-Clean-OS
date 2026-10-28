"""Offline native-response regressions; not live platform acceptance."""
from __future__ import annotations

import json
import socket
from urllib.parse import urlencode

import pytest

from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters.kuaishou import KuaishouAdapter
from lumenis.system.collector.adapters.tiktok import TikTokAdapter


class _Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def header_value(self, _key):
        return None

    def text(self):
        return json.dumps(self.body)


class _Request:
    resource_type = 'fetch'
    method = 'GET'

    def __init__(self, url, body):
        self.url, self.body = url, body

    def response(self):
        return _Response(self.body)


class _EmptyLocator:
    def all_text_contents(self):
        return []


class _Page:
    def __init__(self, observations):
        self.observations = observations
        self.listeners = {}

    def on(self, name, handler):
        self.listeners[name] = handler

    def remove_listener(self, name, _handler):
        self.listeners.pop(name, None)

    def goto(self, _url, **_kwargs):
        for url, body in self.observations:
            self.listeners['requestfinished'](_Request(url, body))

    def locator(self, _selector):
        return _EmptyLocator()

    def wait_for_timeout(self, _ms):
        pass

    def close(self):
        pass


class _Worker:
    _context = object()

    def __init__(self, observations):
        self.page = _Page(observations)

    def connect(self):
        pass

    def new_page(self, **_kwargs):
        return self.page

    def close(self):
        pass


@pytest.fixture(autouse=True)
def no_external_effects(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError('network/session access is outside this offline regression')

    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr('lumenis.adapters.cookie_vault.inject_into_context', lambda *_args: 0)


def _case(platform, rows, *, capability='search', more=False, next_native='9', root=None):
    if platform == 'tiktok':
        path = '/api/search/item/full/' if capability == 'search' else '/api/comment/list/reply/' if root else '/api/comment/list/'
        query = {'keyword': 'source query', 'offset': '0'} if capability == 'search' else {'aweme_id': '123456', 'cursor': '0'}
        if root:
            query['comment_id'] = root
        body = {'itemList' if capability == 'search' else 'comments': rows, 'has_more': more,
                'offset' if capability == 'search' else 'cursor': next_native, 'status_code': 0}
        return ('https://www.tiktok.com' + path + '?' + urlencode(query), body)
    query = {'keyword': 'source query', 'pcursor': ''} if capability == 'search' else {'photoId': 'photo01', 'pcursor': ''}
    if root:
        query['rootCommentId'] = root
    key = 'feeds' if capability == 'search' else 'subCommentsV2' if root else 'rootCommentsV2'
    return ('https://www.kuaishou.com/graphql?' + urlencode(query),
            {'data': {key: rows, 'pcursor': next_native if more else 'no_more', 'result': 1}})


def _item(platform, identity):
    if platform == 'tiktok':
        return {'id': str(identity), 'desc': 'Native caption', 'author': {'uniqueId': 'source_author'}, 'stats': {'diggCount': 0}}
    return {'photo': {'id': 'photo' + str(identity), 'caption': 'Native caption', 'likeCount': 0}, 'author': {'id': 'author01'}}


def _comment(platform, identity, *, replies=None, total=None):
    if platform == 'tiktok':
        return {'cid': str(identity), 'aweme_id': '123456', 'text': 'Native comment',
                'reply_comment': replies or [], 'reply_comment_total': total}
    return {'commentId': str(identity), 'content': 'Native comment',
            'subCommentsV2': replies or [], 'subCommentCountV2': total}


def _adapter(platform, observations):
    cls = TikTokAdapter if platform == 'tiktok' else KuaishouAdapter
    return cls(browser_factory=lambda: _Worker(observations))


@pytest.mark.parametrize('platform', ['tiktok', 'kuaishou'])
def test_search_remainder_is_read_before_advancing_the_native_cursor(platform):
    rows = [_item(platform, i) for i in (123456, 123457, 123458)]
    observations = [_case(platform, rows, more=True)]
    adapter = _adapter(platform, observations)
    cursor, received = None, []
    native_key, initial = ('cursor', '0') if platform == 'tiktok' else ('pcursor', '')
    for offset in range(3):
        result = adapter.search('source query', max_results=1, cursor=cursor)
        assert result.status == CollectionStatus.SUCCESS
        received.extend(item['platform_content_id'] for item in result.items)
        page = result.metadata['pagination']
        assert page['window_start'] == offset
        assert page['observed_native_rows'] == 3
        cursor = page['next_cursor']
        if offset < 2:
            assert cursor[native_key] == initial
            assert cursor['item_offset'] == offset + 1
            # Updating counts does not invalidate an unchanged source ordering.
            if platform == 'tiktok':
                rows[0]['stats']['diggCount'] += 1
            else:
                rows[0]['photo']['likeCount'] += 1
        else:
            assert cursor[native_key] == '9'
            assert 'item_offset' not in cursor and 'page_sha256' not in cursor
    assert len(set(received)) == 3


@pytest.mark.parametrize('platform', ['tiktok', 'kuaishou'])
def test_reply_queue_returns_to_the_exact_unread_root_window(platform):
    inline = _comment(platform, 101)
    roots = [_comment(platform, 1, replies=[inline], total=3), _comment(platform, 2)]
    observations = [_case(platform, roots, capability='comments'),
                    _case(platform, [_comment(platform, 102), _comment(platform, 103)], capability='comments', root='1')]
    adapter = _adapter(platform, observations)
    target = 'https://www.tiktok.com/@source_author/video/123456' if platform == 'tiktok' else 'photo01'
    cursor, ids, pages = None, [], []
    for _ in range(4):
        result = adapter.comments(target, max_comments=1, cursor=cursor, include_replies=True)
        assert result.status == CollectionStatus.SUCCESS
        ids.extend(comment['platform_comment_id'] for comment in result.comments)
        for comment in result.comments:
            if comment['platform_comment_id'] in {'101', '102', '103'}:
                assert comment['parent_comment_id'] == '1'
        pages.append(result.metadata['pagination'])
        cursor = pages[-1]['next_cursor']
    assert ids == ['1', '101', '102', '103', '2']
    assert pages[0]['next_cursor']['next_root']['item_offset'] == 1
    assert pages[1]['next_cursor']['item_offset'] == 1
    assert pages[2]['next_cursor']['mode'] == 'roots'
    assert pages[2]['next_cursor']['item_offset'] == 1
    assert cursor is None and pages[-1]['exhausted'] is True


@pytest.mark.parametrize('platform', ['tiktok', 'kuaishou'])
def test_changed_native_order_rejects_offset_instead_of_silently_skipping(platform):
    observations = [_case(platform, [_item(platform, 123456), _item(platform, 123457)])]
    adapter = _adapter(platform, observations)
    first = adapter.search('source query', max_results=1)
    cursor = first.metadata['pagination']['next_cursor']
    key = 'itemList' if platform == 'tiktok' else 'feeds'
    body = observations[0][1] if platform == 'tiktok' else observations[0][1]['data']
    body[key].reverse()
    result = adapter.search('source query', max_results=1, cursor=cursor)
    assert result.status == CollectionStatus.COLLECT_ERROR
    assert result.message.endswith('NATIVE_CURSOR_PAGE_CHANGED')
    assert result.raw_count is None and result.items == []
    assert result.metadata['pagination']['next_cursor'] is None
    assert result.metadata['pagination']['resume_requires_fresh_page'] is True


@pytest.mark.parametrize('platform', ['tiktok', 'kuaishou'])
@pytest.mark.parametrize('window', [{'item_offset': 1}, {'item_offset': True, 'page_sha256': 'a' * 64}])
def test_malformed_window_is_rejected_before_browser_connection(platform, window):
    def forbidden():
        pytest.fail('invalid cursor connected a browser')

    cls = TikTokAdapter if platform == 'tiktok' else KuaishouAdapter
    cursor = {'mode': 'search', 'cursor' if platform == 'tiktok' else 'pcursor': '0', **window}
    result = cls(browser_factory=forbidden).search('source query', cursor=cursor)
    assert result.status == CollectionStatus.COLLECT_ERROR
    assert result.message.endswith('NATIVE_CURSOR_WINDOW_INVALID')
