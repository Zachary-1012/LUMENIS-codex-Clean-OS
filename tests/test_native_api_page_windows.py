"""Native read API continuation with disposable fixtures, no actual sessions."""
from __future__ import annotations

import socket
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('isolated native API regression reached a network socket')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)


def _response(value):
    return SimpleNamespace(status_code=200, headers={}, json=lambda: value)


def _backend(monkeypatch, platform):
    if platform == 'weibo':
        from lumenis.adapters import weibo
        value = weibo.WeiboAdapter()
        monkeypatch.setattr(value, '_cookie_ok', lambda: True)
        monkeypatch.setattr(weibo, 'to_cookie_string', lambda _platform: 'explicit-offline-session')
        return value, weibo
    from lumenis.adapters import zhihu
    monkeypatch.setattr(zhihu, 'to_cookie_string', lambda *_args: pytest.fail('public fixture read a session'))
    return zhihu.ZhihuAdapter(public_read_only=True), zhihu


def _post(platform, identity, author='99'):
    if platform == 'weibo':
        return {'mid': str(identity), 'id': str(identity), 'text': '原生微博正文',
                'user': {'id': author}, 'isLongText': False, 'attitudes_count': 0}
    return {'type': 'answer', 'id': str(identity), 'content': '<p>原生回答正文</p>',
            'question': {'title': 'Native question'}, 'author': {'id': author}}


def _comment(platform, identity, *, children=None, total=0):
    if platform == 'weibo':
        return {'id': str(identity), 'text': '原生评论', 'comments': children or [], 'total_number': total}
    return {'id': str(identity), 'content': '<p>原生评论</p>', 'child_comments': children or [], 'child_comment_count': total}


@pytest.mark.parametrize('platform', ['weibo', 'zhihu'])
def test_search_native_page_remainder_and_internal_fields_stay_out_of_request(monkeypatch, platform):
    backend, module = _backend(monkeypatch, platform)
    posts = [_post(platform, identity) for identity in (123456, 123457, 123458)]
    requests = []
    def get(_url, **kwargs):
        params = kwargs['params']
        assert 'item_offset' not in params and 'page_sha256' not in params
        requests.append(dict(params))
        if platform == 'weibo':
            # Search commonly nests actual posts in a card_group.
            return _response({'ok': 1, 'data': {'cards': [{'card_group': [{'mblog': post} for post in posts]}],
                              'cardlistInfo': {'since_id': 0, 'total': 3}}})
        return _response({'data': [{'object': post} for post in posts], 'paging': {'is_end': True}})
    monkeypatch.setattr(module.requests, 'get', get)
    cursor, ids = None, []
    for offset in range(3):
        result = backend.search('source query', max_results=1, cursor=cursor)
        assert result.success, result.error
        assert len(result.notes) == 1
        ids.extend(note.url for note in result.notes)
        cursor = result.metadata['pagination']['next_cursor']
        if offset < 2:
            assert cursor['item_offset'] == offset + 1
            assert result.metadata['pagination']['exhausted'] is False
        else:
            assert cursor is None and result.metadata['pagination']['exhausted'] is True
    assert len(requests) == len(set(ids)) == 3


@pytest.mark.parametrize('platform', ['weibo', 'zhihu'])
def test_author_branch_never_skips_unreturned_native_posts(monkeypatch, platform):
    backend, module = _backend(monkeypatch, platform)
    calls = []
    def get(url, **kwargs):
        params = kwargs['params']
        assert 'item_offset' not in params and 'page_sha256' not in params
        calls.append(dict(params))
        if platform == 'weibo':
            if 'containerid' not in params:
                return _response({'ok': 1, 'data': {'userInfo': {'id': '99'},
                    'tabsInfo': {'tabs': [{'tab_type': 'weibo', 'containerid': '10760399'}]}}})
            assert 'since_id' not in params  # Preserve the original initial native request.
            return _response({'ok': 1, 'data': {'cards': [{'mblog': _post(platform, i)} for i in (123456, 123457)],
                    'cardlistInfo': {'since_id': 0}}})
        assert url.endswith('/members/99/answers')
        return _response({'data': [_post(platform, i) for i in (123456, 123457)], 'paging': {'is_end': True}})
    monkeypatch.setattr(module.requests, 'get', get)
    first = backend.author_posts('99', max_results=1)
    assert first.success, first.error
    cursor = first.metadata['pagination']['next_cursor']
    assert cursor['item_offset'] == 1
    second = backend.author_posts('99', max_results=1, cursor=cursor)
    assert second.success, second.error
    assert first.notes[0].url != second.notes[0].url
    cursor = second.metadata['pagination']['next_cursor']
    if platform == 'weibo':
        assert cursor is None and second.metadata['pagination']['exhausted'] is True
        assert len(calls) == 3
    else:
        assert cursor == {'kind': 'article', 'page': {'offset': '0', 'limit': 1}}
        assert second.metadata['pagination']['exhausted'] is False


@pytest.mark.parametrize('platform', ['weibo', 'zhihu'])
def test_reply_windows_finish_before_the_exact_saved_root_remainder(monkeypatch, platform):
    backend, module = _backend(monkeypatch, platform)
    roots = [_comment(platform, 1, children=[_comment(platform, 101)], total=3), _comment(platform, 2)]
    children = [_comment(platform, 102), _comment(platform, 103)]
    def get(url, **kwargs):
        params = kwargs['params']
        assert not {'item_offset', 'page_sha256'} & params.keys()
        is_reply = 'hotFlowChild' in url or '/comment/1/child_comment' in url
        if platform == 'weibo':
            body = {'data': children if is_reply else roots, 'max_id': 0, 'max_id_type': 0,
                    **({'rootComment': [{'id': '1'}]} if is_reply else {})}
            return _response(body if is_reply else {'ok': 1, 'data': body})
        return _response({'data': children if is_reply else roots, 'paging': {'is_end': True}})
    monkeypatch.setattr(module.requests, 'get', get)
    cursor, ids = None, []
    for _ in range(4):
        result = backend.comments('123456', max_comments=1, cursor=cursor, include_replies=True)
        assert result.success, result.error
        ids.extend(str(note.raw_data['cid']) for note in result.notes)
        for note in result.notes:
            if str(note.raw_data['cid']) in {'101', '102', '103'}:
                assert str(note.raw_data['parent_comment_id']) == '1'
        cursor = result.metadata['pagination']['next_cursor']
    assert ids == ['1', '101', '102', '103', '2']
    assert cursor is None and result.metadata['pagination']['exhausted'] is True


@pytest.mark.parametrize('platform', ['weibo', 'zhihu'])
def test_saved_search_window_rejects_native_reorder(monkeypatch, platform):
    backend, module = _backend(monkeypatch, platform)
    posts = [_post(platform, i) for i in (123456, 123457)]
    def get(_url, **_kwargs):
        if platform == 'weibo':
            return _response({'ok': 1, 'data': {'cards': [{'mblog': post} for post in posts],
                                              'cardlistInfo': {'since_id': 0}}})
        return _response({'data': [{'object': post} for post in posts], 'paging': {'is_end': True}})
    monkeypatch.setattr(module.requests, 'get', get)
    first = backend.search('source query', max_results=1)
    posts.reverse()
    second = backend.search('source query', max_results=1, cursor=first.metadata['pagination']['next_cursor'])
    assert second.success is False and second.error.endswith('NATIVE_CURSOR_PAGE_CHANGED')
    assert second.raw_count is None and second.metadata['pagination']['resume_requires_fresh_page'] is True
