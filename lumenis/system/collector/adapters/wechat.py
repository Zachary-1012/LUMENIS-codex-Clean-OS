"""Public WeChat article acquisition in the existing SYSTEM adapter registry.

Search-index dates are discovery hints. Only the original article's own time
signals can become publication fields. No account, Cookie or challenge solver
is involved; authentication failures isolate this route.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import parse_qs, quote, urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .public_source import PublicResponse, fetch_public_url, public_source_provenance
from .registry import register_adapter
from .routing import resolve_capability_route


def _challenge(soup: BeautifulSoup) -> bool:
    if soup.select_one('input[name="captcha"], #verify_code, #captcha, .verifycode'):
        return True
    text = soup.get_text(' ', strip=True)
    return any(marker in text for marker in ('访问过于频繁', '环境异常', '访问异常，请完成验证', '请输入验证码', '请完成安全验证'))


def parse_public_article(response: PublicResponse) -> dict[str, Any] | None:
    if urlsplit(response.url).hostname != 'mp.weixin.qq.com':
        return None
    soup = BeautifulSoup(response.content, 'html.parser')
    if _challenge(soup):
        return None
    node = soup.select_one('#js_content')
    if node is None:
        return None
    body_soup = BeautifulSoup(str(node), 'html.parser')
    for unwanted in body_soup.select('script, style, form, noscript'):
        unwanted.decompose()
    body = body_soup.get_text('\n', strip=True)
    if not body:
        return None
    title_node = soup.select_one('#activity-name')
    author_node = soup.select_one('#js_name, .profile_nickname')
    time_node = soup.select_one('#publish_time')
    time_literal = time_node.get_text(' ', strip=True) if time_node else None
    source_text = response.content.decode('utf-8', errors='replace')
    epoch = re.search(r'\b(?:var\s+)?ct\s*=\s*[\'"]?(\d{10,13})[\'"]?\s*;', source_text)
    published = None
    original_ct = epoch.group(1) if epoch else None
    if original_ct:
        stamp = int(original_ct) / (1000 if len(original_ct) == 13 else 1)
        try:
            published = datetime.fromtimestamp(stamp, timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            pass
    parts = urlsplit(response.url)
    query = parse_qs(parts.query)
    identity = {key: query[key][0] for key in ('__biz', 'mid', 'idx', 'sn') if query.get(key)}
    native_token = parts.path.removeprefix('/s/') if parts.path.startswith('/s/') else None
    if identity.get('__biz') and identity.get('mid'):
        native_id = '|'.join(identity.get(key, '') for key in ('__biz', 'mid', 'idx', 'sn'))
        id_kind = 'NATIVE_ARTICLE_QUERY_TUPLE'
    elif native_token:
        native_id = native_token
        id_kind = 'NATIVE_PUBLIC_SHARE_PATH'
    else:
        return None
    images = [{'url': urljoin(response.url, str(image.get('data-src') or image.get('src'))),
               'alt': image.get('alt')} for image in node.select('img') if image.get('data-src') or image.get('src')]
    title = title_node.get_text(' ', strip=True) if title_node else None
    author = author_node.get_text(' ', strip=True) if author_node else None
    raw = {'article_id': native_id, 'source_id_kind': id_kind, 'native_article_identity': identity,
           'title': title, 'content': body, 'url': response.url, 'author_name': author,
           'author_id': identity.get('__biz'), 'content_type': 'article',
           'ct': original_ct, 'publish_time_literal': time_literal, 'published_at': published,
           'native_publication_precision': 'NATIVE_EPOCH' if published else 'UNKNOWN',
           'read_num': None, 'like_num': None, 'comment_count': None, 'share_count': None,
           'images': images, 'body_locator': '#js_content', 'author_locator': '#js_name, .profile_nickname',
           'native_document_sha256': hashlib.sha256(response.content).hexdigest(),
           'body_sha256': hashlib.sha256(body.encode('utf-8')).hexdigest()}
    return {'platform': 'wechat', 'platform_content_id': native_id, 'title': title, 'content': body,
            'url': response.url, 'author_nickname': author, 'publish_datetime': published,
            'likes': None, 'comments': None, 'collects': None, 'shares': None, 'views': None,
            'raw': raw}


def parse_sogou_discovery(response: PublicResponse) -> tuple[list[dict[str, Any]], str | None]:
    soup = BeautifulSoup(response.content, 'html.parser')
    rows = []
    seen = set()
    for node in soup.select('li[id^="sogou_vr"], .news-box .txt-box'):
        link = node.select_one('h3 a')
        if link is None or not link.get('href'):
            continue
        url = urljoin(response.url, str(link['href']))
        if url in seen:
            continue
        seen.add(url)
        excerpt = node.select_one('.txt-info, .txt-box')
        date = node.select_one('.s-p, .s2')
        rows.append({'source_url': url, 'source_title': link.get_text(' ', strip=True),
                     'index_excerpt': excerpt.get_text(' ', strip=True) if excerpt else None,
                     'index_date_literal': date.get_text(' ', strip=True) if date else None,
                     'index_date_not_article_publication': True, 'native_publication': None})
    next_link = soup.select_one('#sogou_next')
    return rows, urljoin(response.url, str(next_link['href'])) if next_link and next_link.get('href') else None


class WechatPublicAdapter(BasePlatformAdapter):
    platform = 'wechat'
    enabled = False
    monitor_priority = 'secondary'

    def __init__(self, *, fetcher: Callable[[str], PublicResponse] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.fetcher = fetcher or fetch_public_url

    def health_check(self, **kwargs):
        return CollectionResult(CollectionStatus.NEED_VERIFY, self.platform,
            message='Public original-article route requires an actual source observation',
            metadata={'can_attempt': True, 'requires_auth': False, 'cookies_used': False})

    def detail(self, content_id: str, **kwargs):
        route = resolve_capability_route("wechat", "detail", request_value=content_id)
        if route is None:
            return CollectionResult(CollectionStatus.NOT_SUPPORTED, self.platform,
                message='公众号详情仅支持可识别的微信原文公开文章链接',
                metadata={'route_state': 'UNKNOWN', 'reason': 'SOURCE_URL_NOT_SUPPORTED',
                          'original_body_available': False, 'network_attempted': False,
                          'persistence_attempted': False, 'requires_auth': False,
                          'cookies_used': False})
        try:
            response = self.fetcher(content_id)
            soup = BeautifulSoup(response.content, 'html.parser')
            if _challenge(soup):
                return CollectionResult(CollectionStatus.NEED_VERIFY, self.platform,
                    message='Source verification required', metadata={'original_body_available': False})
            item = parse_public_article(response)
            return CollectionResult(CollectionStatus.SUCCESS if item else CollectionStatus.PROVIDER_UNAVAILABLE,
                self.platform, items=[item] if item else [], raw_count=1 if item else 0,
                metadata={**public_source_provenance(response, content_id),
                          'provider': route.backend,
                          'original_body_available': item is not None, 'index_only': False})
        except Exception as exc:
            return CollectionResult(CollectionStatus.PROVIDER_UNAVAILABLE, self.platform,
                metadata={'error_type': type(exc).__name__, 'original_body_available': False})

    def search(self, keyword: str, *, max_results=20, page=1, **kwargs):
        route = resolve_capability_route("wechat", "search", request_value=keyword)
        if route is None:
            return CollectionResult(CollectionStatus.NOT_SUPPORTED, self.platform,
                message='输入未匹配已实现的公众号公开来源路径',
                metadata={'route_state': 'UNKNOWN', 'reason': 'SOURCE_URL_NOT_SUPPORTED',
                          'original_body_available': False, 'network_attempted': False,
                          'persistence_attempted': False, 'requires_auth': False,
                          'cookies_used': False})
        if route.backend == "public_original_article_fetch":
            return self.detail(keyword)
        if type(page) is not int or page < 1 or type(max_results) is not int or not 1 <= max_results <= 20:
            raise ValueError('explicit positive search page and bounded per-request size required')
        url = f'https://weixin.sogou.com/weixin?type=2&query={quote(keyword)}&page={page}'
        try:
            response = self.fetcher(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            if _challenge(soup):
                return CollectionResult(CollectionStatus.NEED_VERIFY, self.platform,
                    metadata={'index_only': True, 'original_body_available': False})
            candidates, next_url = parse_sogou_discovery(response)
            items = []
            original_outcomes = []
            for candidate in candidates[:max_results]:
                result = self.detail(candidate['source_url'])
                original_outcomes.append({'source_url': candidate['source_url'], 'status': result.status.value})
                items.extend(result.items)
                if result.status in {CollectionStatus.NEED_VERIFY, CollectionStatus.BLOCKED}:
                    return CollectionResult(result.status, self.platform, items=items, raw_count=len(candidates),
                metadata={'discovery_candidates': candidates, 'original_outcomes': original_outcomes,
                          'provider': route.backend,
                          'next_search_url': next_url, 'partial': True, 'original_body_available': bool(items)})
            status = CollectionStatus.SUCCESS if items else CollectionStatus.PROVIDER_UNAVAILABLE if candidates else CollectionStatus.NO_NEW_DATA
            return CollectionResult(status, self.platform, items=items, raw_count=len(candidates),
                metadata={'discovery_candidates': candidates, 'original_outcomes': original_outcomes,
                          'provider': route.backend,
                          'next_search_url': next_url, 'index_only': not bool(items),
                          'original_body_available': bool(items), 'search_page': page,
                          'per_request_deferred_source_count': max(0, len(candidates)-max_results)})
        except Exception as exc:
            return CollectionResult(CollectionStatus.PROVIDER_UNAVAILABLE, self.platform,
                metadata={'error_type': type(exc).__name__, 'original_body_available': False})


register_adapter('wechat', WechatPublicAdapter)
