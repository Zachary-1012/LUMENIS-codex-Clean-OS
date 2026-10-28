"""Native response parsing with explicit local provider fixtures, no sessions."""
from unittest.mock import Mock

import pytest


def test_bilibili_native_page_and_inline_reply_survive_main_adapter(monkeypatch):
    from lumenis.adapters.bilibili import BilibiliAdapter as Backend
    from lumenis.system.collector.adapters.bilibili import BilibiliAdapter
    import requests
    backend = Backend()
    monkeypatch.setattr(backend, '_cookie_ok', lambda: True)
    monkeypatch.setattr(backend, '_load_cookies', lambda: {'fixture': 'disposable'})
    seen = []
    def get(url, **kwargs):
        assert url == 'https://api.bilibili.com/x/v2/reply'
        assert kwargs['params']['oid'] == 'isolated-aid'
        page = kwargs['params']['pn']
        seen.append(page)
        roots = [{'rpid': 101, 'rcount': 1, 'content': {'message': 'Native root'},
                  'like': None, 'replies': [{'rpid': 102, 'root': 101, 'parent': 101,
                    'content': {'message': 'Already loaded inline reply'}, 'like': 0}]}] if page == 1 else [
                    {'rpid': 103, 'rcount': 0, 'content': {'message': 'Later root'}, 'like': 0}]
        response = Mock()
        response.json.return_value = {'code': 0, 'data': {'replies': roots,
            'page': {'num': page, 'size': 1, 'count': 2}}}
        return response
    monkeypatch.setattr(requests, 'get', get)
    main = BilibiliAdapter()
    monkeypatch.setattr(main, '_load_backend', lambda: backend)
    # Keep the declared native aid in the test, rather than performing detail.
    original = backend.comments
    monkeypatch.setattr(backend, 'comments', lambda bvid, **kwargs: original(bvid, aid='isolated-aid', **kwargs))
    first = main.comments('BV1Q541167Qg', max_comments=1)
    assert first.items == [] and len(first.comments) == 2
    assert first.comments[0]['platform_comment_id'] == '101' and first.comments[0]['likes'] is None
    assert first.comments[1]['parent_comment_id'] == '101'
    assert first.comments[1]['reply_to_comment_id'] == '101' and first.comments[1]['likes'] == 0
    assert first.metadata['pagination']['next_cursor'] == {'page': 2}
    assert first.metadata['pagination']['exhausted'] is False
    second = main.comments('BV1Q541167Qg', max_comments=1, cursor=first.metadata['pagination']['next_cursor'])
    assert seen == [1, 2]
    assert second.metadata['pagination']['request_cursor'] == {'page': 2}
    assert second.metadata['pagination']['next_cursor'] is None
    assert second.metadata['pagination']['exhausted'] is True
    assert second.metadata['pagination']['replies_complete'] is True


@pytest.mark.parametrize('cursor', [{'page': True}, {'page': 0}, {'page': '2'}, {'page': 1, 'foreign': 1}])
def test_bilibili_rejects_unissued_native_shape_before_any_session_access(monkeypatch, cursor):
    from lumenis.adapters.bilibili import BilibiliAdapter
    backend = BilibiliAdapter()
    monkeypatch.setattr(backend, '_cookie_ok', lambda: pytest.fail('invalid cursor accessed a session'))
    result = backend.comments('BV1Q541167Qg', cursor=cursor)
    assert result.success is False and result.error == 'BILIBILI_COMMENT_CURSOR_INVALID'


def test_bilibili_native_reply_pages_finish_before_next_root_page(monkeypatch):
    from lumenis.adapters.bilibili import BilibiliAdapter
    import requests
    backend = BilibiliAdapter(public_read_only=True)
    monkeypatch.setattr(backend, '_load_cookies', lambda: {})
    calls = []
    def reply(identity, *, root=None, total=0, inline=None):
        return {'rpid':identity, 'root':root, 'parent':root, 'rcount':total,
                'content':{'message':f'Native fixture {identity}'}, 'like':None,
                'replies':inline or []}
    def get(url, **kwargs):
        params = kwargs['params']
        root, page = params.get('root'), params['pn']
        calls.append((root,page))
        if root is None and page == 1:
            values = [reply(101,total=3,inline=[reply(102,root=101)]),reply(201,total=1)]
            total = 3
        elif root == '101':
            values = [reply(102,root=101),reply(103,root=101)] if page == 1 else [reply(104,root=101)]
            total = 3
        elif root == '201':
            values, total = [reply(202,root=201)], 1
        else:
            assert root is None and page == 2
            values, total = [reply(301)], 3
        assert url.endswith('/reply/reply') if root else url.endswith('/reply')
        return Mock(json=lambda:{'code':0,'data':{'replies':values,
            **({'root':{'rpid':int(root)}} if root else {}),
            'page':{'num':page,'size':2,'count':total}}})
    monkeypatch.setattr(requests,'get',get)
    cursor, pages = None, []
    for _ in range(5):
        value = backend.comments('BV1Q541167Qg',aid='fixture-aid',max_comments=2,
                                 include_replies=True,cursor=cursor)
        assert value.success, value.error
        pages.append(value)
        cursor = value.metadata['pagination']['next_cursor']
        if cursor is None:
            break
    assert calls == [(None,1),('101',1),('101',2),('201',1),(None,2)]
    assert pages[0].metadata['pagination']['exhausted'] is False
    assert pages[-1].metadata['pagination']['exhausted'] is True
    assert pages[-1].metadata['pagination']['replies_complete'] is True
    native = [note.raw_data for value in pages for note in value.notes]
    assert {str(item['rpid']) for item in native} == {'101','102','103','104','201','202','301'}
    assert all(str(item['parent_comment_id']) == '101' for item in native if item['rpid'] in {102,103,104})
    assert all(note.likes is None for value in pages for note in value.notes)


def test_bilibili_public_author_and_native_history_cursor_keep_profile_counts_separate(monkeypatch):
    from lumenis.adapters.bilibili import BilibiliAdapter
    import requests
    backend = BilibiliAdapter(public_read_only=True)
    monkeypatch.setattr('lumenis.adapters.bilibili.to_requests_cookies',
                        lambda *args:pytest.fail('public author accessed credentials'))
    calls = []
    def get(url, **kwargs):
        calls.append((url,kwargs['params']))
        assert kwargs['cookies'] == {}
        if url.endswith('/card'):
            payload = {'card':{'mid':'12345','name':'Fixture native profile','fans':0},'archive_count':3}
        else:
            page = kwargs['params']['pn']
            payload = {'page':{'pn':page,'ps':2,'count':3},'list':{'vlist':[{
                'bvid':'BV1Q541167Qg' if page==1 else 'BV1BP4y147BT','mid':12345,
                'title':'Native history fixture','created':1700000000,'description':'Observed description'}]}}
        return Mock(json=lambda:{'code':0,'data':payload})
    monkeypatch.setattr(requests,'get',get)
    profile = backend.creator('https://space.bilibili.com/12345')
    assert profile.success and profile.notes[0].raw_data['follower_count'] == 0
    assert profile.notes[0].raw_data['content_count'] == 3
    assert profile.notes[0].likes is None and profile.notes[0].comments is None
    first = backend.author_posts('12345',max_results=2)
    assert first.success and first.metadata['pagination']['next_cursor'] == {'page':2}
    second = backend.author_posts('12345',max_results=2,cursor=first.metadata['pagination']['next_cursor'])
    assert second.success and second.metadata['pagination']['exhausted'] is True
    assert second.notes[0].author_id == '12345'
    assert second.notes[0].raw_data['bvid'] == 'BV1BP4y147BT'
    assert len(calls) == 3
