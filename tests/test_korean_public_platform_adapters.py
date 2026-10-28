"""Offline source/continuation contracts; fixtures do not prove live acquisition."""
from __future__ import annotations

import hashlib
import json
import socket
from urllib.parse import parse_qs, urlsplit

import pytest

from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters.daum import DaumAdapter
from lumenis.system.collector.adapters.naver import NaverAdapter
from lumenis.system.collector.adapters.public_source import PublicResponse


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail('offline regression attempted a network connection')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)


def _html(url, body):
    return PublicResponse(url, body.encode('utf-8'), 'text/html', 200)


@pytest.mark.parametrize('cls,url,selector,identity', [
    (NaverAdapter, 'https://blog.naver.com/PostView.naver?blogId=source_blog&logNo=12345', 'se-main-container', 'blog:source_blog:12345'),
    (NaverAdapter, 'https://cafe.naver.com/ca-fe/cafes/42/articles/12345', 'ContentRenderer', 'cafe:42:12345'),
    (DaumAdapter, 'https://source-blog.tistory.com/12345', 'contents_style', 'tistory:source-blog:12345'),
    (DaumAdapter, 'https://cafe.daum.net/sourcecafe/board/12345', 'article_view', 'cafe:sourcecafe:board:12345'),
])
def test_original_parser_and_actual_detail_use_identical_source_bytes(cls, url, selector, identity):
    response = _html(url, f'<html><head><meta property="og:title" content="한국어 제목"></head>'
        f'<body><div class="{selector}"><p>정상 원문 첫 문장。</p><p>보안문자에 관한 실제 기사。</p>'
        '<img src="https://cdn.example.test/native.png"></div></body></html>')
    parsed = cls.parse_original(response)
    calls = []
    def fetch(target):
        calls.append(target)
        return response
    result = cls(fetcher=fetch).detail(identity, source_url=url)
    assert result.status == CollectionStatus.SUCCESS and len(calls) == 1
    assert result.original_response is response
    item = result.items[0]
    assert item['platform_content_id'] == identity
    assert '정상 원문 첫 문장' in item['content'] and '보안문자에 관한 실제 기사' in item['content']
    assert {key: value for key, value in item.items() if key != 'captured_at'} == parsed
    observation = item['raw']['content_observation']
    assert observation['document_sha256'] == hashlib.sha256(response.content).hexdigest()
    assert observation['document_byte_length'] == len(response.content)
    assert observation['truncated'] is False
    assert item['raw']['media_list'] == item['raw']['media_hints'] == item['media_list']
    assert item['raw']['body_scope']['whole_article_verified'] is False
    assert item['publish_datetime'] == '' and item['likes'] is None


@pytest.mark.parametrize('cls,url,body,status', [
    (NaverAdapter, 'https://blog.naver.com/PostView.naver?blogId=source_blog&logNo=12345', '<h1>자동입력 방지</h1>', CollectionStatus.NEED_VERIFY),
    (DaumAdapter, 'https://cafe.daum.net/sourcecafe/board/12345', '<h1>로그인이 필요합니다</h1>', CollectionStatus.SESSION_EXPIRED),
    (NaverAdapter, 'https://cafe.naver.com/sourcecafe/12345', '<meta property="og:description" content="excerpt only">', CollectionStatus.PROVIDER_UNAVAILABLE),
])
def test_gate_or_summary_is_not_an_original_and_does_not_trigger_another_backend(cls, url, body, status):
    calls = []
    def fetch(target):
        calls.append(target)
        return _html(target, body)
    result = cls(fetcher=fetch).detail(url)
    assert result.status == status
    assert result.raw_count is None and result.items == [] and len(calls) == 1
    assert result.metadata['pagination']['next_cursor'] is None


def test_native_blog_history_keeps_remainder_zero_values_and_native_page_end():
    calls = []
    def fetch(url):
        calls.append(url)
        page = int(parse_qs(urlsplit(url).query)['page'][0])
        items = [{'logNo': 100 + i, 'title': f'Article {i}', 'addDate': 1727136000000,
                  'sympathyCnt': 0, 'commentCount': 0} for i in range(2)] if page == 1 else []
        body = json.dumps({'result': {'items': items, 'totalCount': 0}}).encode()
        return PublicResponse(url, body, 'application/json', 200)
    adapter = NaverAdapter(fetcher=fetch)
    first = adapter.author_posts('source_blog', max_results=1)
    one = first.items[0]
    assert one['likes'] == one['comments'] == 0 and one['views'] is None
    cursor = first.metadata['pagination']['next_cursor']
    assert cursor['page'] == 1 and cursor['item_offset'] == 1
    second = adapter.author_posts('source_blog', max_results=1, cursor=cursor)
    assert second.items[0]['platform_content_id'] == 'blog:source_blog:101'
    cursor = second.metadata['pagination']['next_cursor']
    assert cursor['page'] == 2 and 'item_offset' not in cursor
    last = adapter.author_posts('source_blog', max_results=1, cursor=cursor)
    assert last.status == CollectionStatus.NO_NEW_DATA
    assert last.metadata['pagination']['exhausted'] is True
    assert last.metadata['pagination']['reported_total'] is None
    assert len(calls) == 3


def test_repeated_native_history_page_stops_without_claiming_exhaustion():
    def fetch(url):
        return PublicResponse(url, b'{"result":{"items":[{"logNo":12345,"title":"one"}]}}', 'application/json', 200)
    adapter = NaverAdapter(fetcher=fetch)
    first = adapter.author_posts('source_blog')
    result = adapter.author_posts('source_blog', cursor=first.metadata['pagination']['next_cursor'])
    assert result.status == CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.message == 'NAVER_NATIVE_HISTORY_PAGE_REPEATED'
    assert result.metadata['pagination']['exhausted'] is None


@pytest.mark.parametrize('cls,search_url,post_url', [
    (NaverAdapter, 'https://search.naver.com/search.naver?query=brand', 'https://blog.naver.com/source_blog/12345'),
    (DaumAdapter, 'https://search.daum.net/search?q=brand', 'https://source-blog.tistory.com/12345'),
])
def test_search_preserves_native_link_pagination_and_does_not_promote_snippets(cls, search_url, post_url):
    response = _html(search_url, f'<a href="{post_url}">Source title</a>'
                     f'<a rel="next" href="{search_url}&amp;page=2">다음</a>')
    result = cls(fetcher=lambda _url: response).search('brand', max_results=1)
    assert result.status == CollectionStatus.SUCCESS
    assert result.items[0]['content'] == ''
    assert result.items[0]['raw']['body_state'] == 'DISCOVERY_LINK_ONLY'
    assert result.metadata['pagination']['next_cursor']['page_url'].endswith('&page=2')
    assert result.metadata['pagination']['exhausted'] is False


@pytest.mark.parametrize('cls,url', [
    (NaverAdapter, 'https://blog.naver.com/PostView.naver?blogId=source_blog&logNo=12345'),
    (DaumAdapter, 'https://source-blog.tistory.com/12345'),
])
def test_observed_replies_survive_default_flag_and_page_budget(cls, url):
    response = _html(url, '<ul data-comment-count="2"><li id="comment1"><p class="text">root</p>'
        '<ul><li id="comment2"><p class="text">reply</p></li></ul></li></ul>')
    adapter = cls(fetcher=lambda _url: response)
    first = adapter.comments(url, max_comments=1)
    assert first.status == CollectionStatus.SUCCESS
    assert first.comments[0]['platform_comment_id'] == '1'
    second = adapter.comments(url, max_comments=1, cursor=first.metadata['pagination']['next_cursor'])
    assert second.comments[0]['platform_comment_id'] == '2'
    assert second.comments[0]['parent_comment_id'] == '1'
    assert second.metadata['returned_reply_relationships_preserved'] is True
    assert second.metadata['pagination']['exhausted'] is None


def test_explicit_native_rss_is_not_complete_history_or_original_body():
    url = 'https://rss.blog.naver.com/source_blog.xml'
    body = ('<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><title>Source</title>'
            '<link>https://blog.naver.com/source_blog</link><description>Source</description>'
            '<item><title>한국어</title><link>https://blog.naver.com/source_blog/12345</link>'
            '<description>공개 RSS 요약</description></item></channel></rss>')
    response = PublicResponse(url, body.encode(), 'application/rss+xml', 200)
    result = NaverAdapter(fetcher=lambda _url: response).search(url)
    assert result.status == CollectionStatus.SUCCESS
    assert result.items[0]['raw']['body_state'] == 'FEED_EXCERPT'
    assert result.items[0]['raw']['whole_article_verified'] is False
    assert result.metadata['pagination']['exhausted'] is None


@pytest.mark.parametrize('cls,bad_url', [
    (NaverAdapter, 'https://blog.naver.com/source_blog/12345?access_token=secret'),
    (NaverAdapter, 'https://blog.naver.com:444/source_blog/12345'),
    (DaumAdapter, 'https://source-blog.tistory.com.evil.test/12345'),
])
def test_unapproved_target_shape_is_rejected_before_transport(cls, bad_url):
    def forbidden(_url):
        pytest.fail('invalid source reached transport')
    result = cls(fetcher=forbidden).detail(bad_url)
    assert result.status == CollectionStatus.COLLECT_ERROR
    assert result.raw_count is None


@pytest.mark.parametrize('platform,kind,identity', [
    ('naver', 'blog', 'blog:source_blog:12345'),
    ('naver', 'cafe', 'cafe:sourcecafe:12345'),
    ('daum', 'tistory', 'tistory:source-blog:12345'),
    ('daum', 'cafe', 'cafe:sourcecafe:board:12345'),
])
def test_original_field_contract_keeps_typed_identity_and_unknown_metrics(platform, kind, identity):
    from lumenis.system.collector.adapters.platform_naming import map_raw_to_normalized, to_canonical_record

    raw = {'native_content_id': identity, 'native_kind': kind, 'author_id': None,
           'publish_datetime': '', 'url': 'https://source.example.test/original', 'likes': 0,
           'comments': None, 'views': None}
    canonical = to_canonical_record(raw, platform)
    normalized = map_raw_to_normalized(raw, platform)
    assert canonical['content_id'] == normalized['platform_content_id'] == identity
    assert canonical['like_count'] == normalized['like_count'] == 0
    assert canonical['comment_count'] is normalized['comment_count'] is None
    assert canonical['published_at'] is normalized['published_at'] is None
    mismatched = {**raw, 'native_kind': 'tistory' if platform == 'naver' else 'blog'}
    assert to_canonical_record(mismatched, platform)['content_id'] is None
    assert map_raw_to_normalized(mismatched, platform)['platform_content_id'] is None
