"""Public WeChat article acquisition in the existing SYSTEM adapter registry.

Search-index dates are discovery hints. Only the original article's own time
signals can become publication fields. No account, Cookie or challenge solver
is involved; authentication failures isolate this route.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, parse_qsl, quote, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .public_source import (
    PublicResponse,
    PublicSourceError,
    fetch_public_url,
    public_source_provenance,
)
from .registry import register_adapter
from .routing import resolve_capability_route


def _challenge(soup: BeautifulSoup) -> bool:
    if soup.select_one('input[name="captcha"], #verify_code, #captcha, .verifycode'):
        return True
    text = soup.get_text(' ', strip=True)
    return any(marker in text for marker in ('访问过于频繁', '环境异常', '访问异常，请完成验证', '请输入验证码', '请完成安全验证'))


def _public_media_hint_url(value: Any, article_url: str) -> str | None:
    """Keep an observed public URL without invoking or resolving its target."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        url = urljoin(article_url, value.strip())
        parts = urlsplit(url)
        secret_names = {'key', 'api_key', 'apikey', 'access_key', 'appkey', 'auth_key',
                        'dis_k', 'token', 'auth', 'authorization', 'cookie', 'session',
                        'session_id', 'password', 'signature', 'sign', 'sig'}
        if (parts.scheme not in ('http', 'https') or not parts.hostname
                or parts.username or parts.password or parts.port not in (None, 80, 443)
                or any(key.lower() in secret_names or key.lower().endswith('_token')
                       for key, _ in parse_qsl(parts.query, keep_blank_values=True))):
            return None
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ''))
    except ValueError:
        return None


def _article_media_hints(node, article_url: str) -> list[dict[str, Any]]:
    """Observe original DOM media cues; no download, playback or understanding."""
    hints = []
    tags = node.select('video, audio, mpvideo, mpvoice, iframe, mp-common-videosnap')
    for index, tag in enumerate(tags):
        tag_name = tag.name
        media_type = ('audio' if tag_name in ('audio', 'mpvoice') else 'embed'
                      if tag_name == 'iframe' and not tag.get('data-mpvid') else 'video')
        locator = {'container': '#js_content', 'media_element_index': index,
                   'native_tag': tag_name}
        attributes = {key: tag[key] for key in (
            'data-mpvid', 'data-vid', 'vid', 'voice_encode_fileid', 'data-id',
            'name', 'title', 'data-title', 'data-desc', 'data-duration',
            'duration', 'width', 'height', 'type',
        ) if isinstance(tag.get(key), str) and tag[key].strip()}
        media_id = next((attributes[key] for key in (
            'data-mpvid', 'data-vid', 'vid', 'voice_encode_fileid', 'data-id',
        ) if key in attributes), None)
        # Channels' data-url is not established as a playable stream. Retain
        # its separate observed role rather than turning a cover into a video.
        src = tag.get('data-src') or tag.get('src')
        hint = {'media_type': media_type, 'native_tag': tag_name,
                'media_id': media_id, 'url': _public_media_hint_url(src, article_url),
                'url_role': 'EMBED_PAGE' if tag_name == 'iframe' else 'MEDIA_RESOURCE',
                'native_locator': locator, 'native_attributes': attributes,
                'observation_kind': 'NATIVE_EMBED_HINT'}
        poster = tag.get('poster') or tag.get('data-cover')
        if poster:
            hint['cover_url'] = _public_media_hint_url(poster, article_url)
        if tag_name == 'mp-common-videosnap':
            hint['observed_data_url'] = _public_media_hint_url(tag.get('data-url'), article_url)
            hint['observed_data_url_role'] = 'UNKNOWN'
        hints.append(hint)
        if tag_name in ('video', 'audio'):
            for source_index, source in enumerate(tag.select('source')):
                source_hint = {**hint, 'native_tag': 'source',
                               'url': _public_media_hint_url(source.get('data-src') or source.get('src'), article_url),
                               'native_locator': {**locator, 'source_element_index': source_index},
                               'native_attributes': {key: source[key] for key in ('type', 'media')
                                   if isinstance(source.get(key), str) and source[key].strip()}}
                hints.append(source_hint)
    return hints


def parse_public_article(response: PublicResponse) -> dict[str, Any] | None:
    if (not resolve_capability_route('wechat', 'detail', request_value=response.url)
            or not 200 <= response.status_code < 300):
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
    images = [{'url': _public_media_hint_url(image.get('data-src') or image.get('src'), response.url),
               'alt': image.get('alt'), 'media_type': 'image'}
              for image in body_soup.select('img') if image.get('data-src') or image.get('src')]
    title = title_node.get_text(' ', strip=True) if title_node else None
    author = author_node.get_text(' ', strip=True) if author_node else None
    raw = {'article_id': native_id, 'source_id_kind': id_kind, 'native_article_identity': identity,
           'title': title, 'content': body, 'url': response.url, 'author_name': author,
           'author_id': identity.get('__biz'), 'content_type': 'article',
           'ct': original_ct, 'publish_time_literal': time_literal, 'published_at': published,
           'native_publication_precision': 'NATIVE_EPOCH' if published else 'UNKNOWN',
           'read_num': None, 'like_num': None, 'comment_count': None, 'share_count': None,
            'images': images, 'media_hints': _article_media_hints(body_soup, response.url),
            'body_locator': '#js_content', 'author_locator': '#js_name, .profile_nickname',
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

    def _transport_failure(self, error: Exception):
        """Expose bounded failure categories, never arbitrary exception text."""
        reason = 'PUBLIC_TRANSPORT_UNAVAILABLE'
        status = CollectionStatus.PROVIDER_UNAVAILABLE
        http_status = None
        if isinstance(error, PublicSourceError):
            matched = re.fullmatch(r'public source returned HTTP (\d{3})', str(error))
            if matched:
                http_status = int(matched.group(1))
                reason = 'PUBLIC_HTTP_UNAVAILABLE'
                if http_status in (401, 403, 429):
                    status = CollectionStatus.BLOCKED
                    reason = ('PUBLIC_HTTP_RATE_LIMITED' if http_status == 429
                              else 'PUBLIC_HTTP_ACCESS_RESTRICTED')
        observation = {'state': status.value, 'reason': reason,
                       'error_type': type(error).__name__, 'http_status': http_status,
                       'original_body_available': False, 'accepted_native_article_count': 0}
        return CollectionResult(status, self.platform,
            metadata={**observation, 'detail': observation})

    def _original_response(self, response: PublicResponse, source_url: str, provider: str):
        soup = BeautifulSoup(response.content, 'html.parser')
        challenged = _challenge(soup)
        item = None if challenged else parse_public_article(response)
        status = (CollectionStatus.NEED_VERIFY if challenged else CollectionStatus.SUCCESS
                  if item else CollectionStatus.PROVIDER_UNAVAILABLE)
        reason = ('ORIGINAL_VERIFICATION_REQUIRED' if challenged else None if item
                  else 'ORIGINAL_ARTICLE_URL_NOT_SUPPORTED'
                  if not resolve_capability_route('wechat', 'detail', request_value=response.url)
                  else 'ORIGINAL_ARTICLE_BODY_NOT_OBSERVED')
        transport = public_source_provenance(response, source_url)
        observation = {**transport, 'state': status.value, 'reason': reason,
                       'original_body_available': item is not None,
                       'accepted_native_article_count': 1 if item else 0}
        return CollectionResult(status, self.platform, items=[item] if item else [],
            raw_count=1 if item else 0,
            metadata={**transport, 'provider': provider, 'reason': reason,
                      'original_body_available': item is not None, 'index_only': False,
                      'detail': observation})

    @staticmethod
    def _search_metadata(candidates, original_outcomes, items, next_url, route, page):
        observation = {
            'discovery_candidate_count': len(candidates),
            'attempted_original_count': len(original_outcomes),
            'accepted_native_article_count': len(items),
            'original_outcomes': original_outcomes,
        }
        return {'discovery_candidates': candidates, 'original_outcomes': original_outcomes,
                'provider': route.backend, 'next_search_url': next_url,
                'index_only': not bool(items), 'original_body_available': bool(items),
                'search_page': page, 'detail': observation,
                'discovery_candidate_count': len(candidates),
                'per_request_deferred_source_count': max(0, len(candidates)-len(original_outcomes))}

    def _discovery_original(self, source_url: str):
        """Resolve an observed public index link before parsing the article.

        Sogou redirect links are discovery locators, not WeChat article IDs.
        Use the same public fetcher and its redirect/security policy; never
        change backend or follow a verification page to manufacture a body.
        """
        if resolve_capability_route('wechat', 'detail', request_value=source_url):
            return self.detail(source_url)
        try:
            parts = urlsplit(source_url)
            if (parts.scheme != 'https' or parts.hostname != 'weixin.sogou.com'
                    or parts.path != '/link' or parts.username or parts.password
                    or parts.port not in (None, 443)):
                return CollectionResult(CollectionStatus.NOT_SUPPORTED, self.platform,
                    metadata={'reason': 'DISCOVERY_LINK_NOT_SUPPORTED',
                              'original_body_available': False, 'network_attempted': False})
            response = self.fetcher(source_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            if _challenge(soup):
                return CollectionResult(CollectionStatus.NEED_VERIFY, self.platform,
                    metadata={'reason': 'DISCOVERY_REDIRECT_VERIFICATION_REQUIRED',
                              'original_body_available': False,
                              'detail': {**public_source_provenance(response, source_url),
                                         'state': CollectionStatus.NEED_VERIFY.value,
                                         'reason': 'DISCOVERY_REDIRECT_VERIFICATION_REQUIRED',
                                         'original_body_available': False,
                                         'accepted_native_article_count': 0}})
            item = parse_public_article(response)
            if item is None and urlsplit(response.url).hostname == 'weixin.sogou.com':
                # A visible link is usable discovery. Opaque script arithmetic,
                # anti-bot tokens and verification flows remain unsupported.
                article_links = [urljoin(response.url, str(node.get('href')))
                                 for node in soup.select('a[href]')]
                article_url = next((url for url in article_links
                    if resolve_capability_route('wechat', 'detail', request_value=url)), None)
                if article_url:
                    return self.detail(article_url)
            return self._original_response(response, source_url, 'public_sogou_discovery_original_fetch')
        except (RuntimeError, OSError, TypeError, ValueError) as exc:
            return self._transport_failure(exc)

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
            return self._original_response(response, content_id, route.backend)
        except (RuntimeError, OSError, TypeError, ValueError) as exc:
            return self._transport_failure(exc)

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
                reason = 'SEARCH_INDEX_VERIFICATION_REQUIRED'
                observation = {**public_source_provenance(response, url),
                               'state': CollectionStatus.NEED_VERIFY.value,
                               'reason': reason,
                               'original_body_available': False,
                               'accepted_native_article_count': 0}
                return CollectionResult(CollectionStatus.NEED_VERIFY, self.platform,
                    metadata={'provider': route.backend, 'reason': reason,
                              'index_only': True, 'original_body_available': False,
                              'detail': observation})
            candidates, next_url = parse_sogou_discovery(response)
            items = []
            original_outcomes = []
            for candidate in candidates[:max_results]:
                result = self._discovery_original(candidate['source_url'])
                outcome = {key: result.metadata[key] for key in (
                    'reason', 'error_type', 'http_status', 'requested_source_url',
                    'final_source_url', 'redirect_chain') if key in result.metadata}
                detail = result.metadata.get('detail') or {}
                outcome.update({key: detail[key] for key in (
                    'reason', 'requested_source_url', 'final_source_url', 'redirect_chain') if key in detail})
                original_outcomes.append({**outcome, 'status': result.status.value,
                    'discovery_locator_sha256': hashlib.sha256(candidate['source_url'].encode('utf-8')).hexdigest(),
                    'original_body_available': bool(result.items),
                    'accepted_native_article_count': len(result.items)})
                items.extend(result.items)
                if result.status in {CollectionStatus.NEED_VERIFY, CollectionStatus.BLOCKED}:
                    return CollectionResult(result.status, self.platform, items=items, raw_count=len(items),
                        metadata={**self._search_metadata(candidates, original_outcomes, items,
                                  next_url, route, page), 'partial': True})
            status = CollectionStatus.SUCCESS if items else CollectionStatus.PROVIDER_UNAVAILABLE if candidates else CollectionStatus.NO_NEW_DATA
            return CollectionResult(status, self.platform, items=items, raw_count=len(items),
                metadata=self._search_metadata(candidates, original_outcomes, items,
                                               next_url, route, page))
        except (RuntimeError, OSError, TypeError, ValueError) as exc:
            return self._transport_failure(exc)


register_adapter('wechat', WechatPublicAdapter)
