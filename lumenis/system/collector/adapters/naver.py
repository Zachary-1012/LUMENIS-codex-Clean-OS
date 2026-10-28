"""Naver public Blog/Cafe sources through the existing Collector transport.

SE3/PostView selectors are adapted from sipher, MIT, commit
2c3470f973d47842a13b70c552872a6ceabd7a9b. See
vendor/lumenis-reuse-notices/sipher-2c3470f9-MIT.txt. Its HTTP clients, identity,
AI, media download and summary-as-body fallback are deliberately not imported.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlsplit

import feedparser
from bs4 import BeautifulSoup

from lumenis.adapters.base import optional_int
from lumenis.adapters.human_browser import (
    NativePageWindowError, native_page_window, validate_native_page_window_cursor,
)

from .base import AccessClass, BasePlatformAdapter, CollectionResult, CollectionStatus
from .public_http import _public_dom_media, _publication_signals
from .public_source import (
    PublicResponse, PublicSourceError, fetch_public_url,
    public_source_error_metadata, public_source_provenance,
)
from .registry import register_adapter


class KoreanSourceError(ValueError):
    """A public page did not supply the requested native source."""


def _https_parts(value):
    if not isinstance(value, str) or not value or len(value) > 4096 or any(ord(c) < 32 for c in value):
        raise KoreanSourceError('SOURCE_URL_INVALID')
    try:
        parts = urlsplit(value)
        if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
                or parts.port not in (None, 443)):
            raise ValueError
        if any(re.search(r'token|auth|secret|session|password|cookie|signature|^sig$|^art$', key, re.I)
               for key in parse_qs(parts.query)):
            raise ValueError
    except ValueError:
        raise KoreanSourceError('SOURCE_URL_INVALID') from None
    return parts


def _meta(soup, name):
    node = soup.find('meta', attrs={'property': name}) or soup.find('meta', attrs={'name': name})
    return str(node.get('content') or '').strip() if node else ''


def _page_problem(soup, *, has_article=False):
    # A real article may discuss login or CAPTCHA. Only structural challenges,
    # or a gate page without an article, are classified as access failures.
    if soup.select_one('input[name*="captcha" i], iframe[src*="captcha" i], #captcha'):
        return 'VERIFICATION_REQUIRED'
    if has_article:
        return None
    text = soup.get_text(' ', strip=True)[:12000]
    if any(value in text for value in ('자동입력 방지', '자동입력방지', '보안문자', '로봇이 아닙니다')):
        return 'VERIFICATION_REQUIRED'
    if any(value in text for value in ('로그인이 필요', '로그인 후 이용', '회원만', '가입한 멤버만', '등급 이상')):
        return 'AUTH_REQUIRED'
    if any(value in text for value in ('비정상적인 접근', '접근이 제한', '접근 권한이 없', '이용이 제한')):
        return 'ACCESS_BLOCKED'
    return None


class _KoreanPublicPageAdapter(BasePlatformAdapter):
    """Shared parsing inside the original platform adapters, with no new store."""

    body_selectors = ()
    search_host = ''
    search_path = ''
    search_parameter = ''
    original_schema = 'korean-public-dom/v1'

    def __init__(self, *, fetcher=None, **kwargs):
        super().__init__(**kwargs)
        self.fetcher = fetcher or fetch_public_url

    @classmethod
    def identity(cls, value):
        raise NotImplementedError

    @classmethod
    def _detail_target(cls, content_id, source_url=None):
        identity = cls.identity(source_url or content_id)
        if source_url and not str(content_id).startswith('https://') and content_id != identity['native_content_id']:
            raise KoreanSourceError('NATIVE_IDENTITY_MISMATCH')
        if source_url and str(content_id).startswith('https://') and cls.identity(content_id)['native_content_id'] != identity['native_content_id']:
            raise KoreanSourceError('NATIVE_IDENTITY_MISMATCH')
        return identity

    @classmethod
    def parse_original(cls, response):
        """Pure byte-to-source parser, reusable by the original Artifact owner."""
        if (type(response) is not PublicResponse or response.content_type not in {'text/html', 'application/xhtml+xml'}
                or not 200 <= response.status_code < 300 or not 0 < len(response.content) <= 2 * 1024 * 1024):
            raise KoreanSourceError('ORIGINAL_RESPONSE_INVALID')
        identity = cls.identity(response.url)
        soup = BeautifulSoup(response.content, 'html.parser')
        root = next((soup.select_one(selector) for selector in cls.body_selectors
                     if soup.select_one(selector) is not None), None)
        problem = _page_problem(soup, has_article=root is not None)
        if problem:
            raise KoreanSourceError(problem)
        if root is None:
            raise KoreanSourceError('ORIGINAL_BODY_NOT_OBSERVED')
        for tag in root.select('script,style,noscript,form,nav'):
            tag.decompose()
        text = root.get_text('\n', strip=True)
        if not text:
            raise KoreanSourceError('ORIGINAL_BODY_EMPTY')
        published, date_source, date_state = _publication_signals(soup)
        date_node = soup.select_one('.se_publishDate, .blog_date, .date, time')
        media, media_observation = _public_dom_media(soup, [root], response.url)
        title = _meta(soup, 'og:title') or (soup.title.get_text(' ', strip=True) if soup.title else '')
        author = _meta(soup, 'article:author') or _meta(soup, 'author')
        return {
            'platform_content_id': identity['native_content_id'], 'title': title, 'content': text,
            'url': identity['url'], 'author_id': identity.get('author_id'), 'author_nickname': author or None,
            'publish_datetime': published, 'likes': None, 'comments': None, 'collects': None, 'shares': None,
            'cover': next((value.get('url') for value in media if value.get('media_type') == 'image' and value.get('url')), None),
            'media_list': media,
            'raw': {
                **identity, 'original_schema': cls.original_schema, 'native_kind': identity['kind'],
                'body_state': 'COMPLETE_SELECTED_NATIVE_DOM', 'body_kind': 'NATIVE_ARTICLE_DOM_TEXT',
                'body_scope': {'representation': 'NORMALIZED_TEXT_FROM_FETCHED_HTML', 'selection': 'native_article_dom',
                               'selected_dom_text_complete': True, 'returned_text_truncated': False, 'whole_article_verified': False,
                               'dynamic_content_executed': False, 'description_is_original_body': False},
                'body_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                'document_sha256': hashlib.sha256(response.content).hexdigest(),
                'document_byte_length': len(response.content), 'body_selector': next(
                    selector for selector in cls.body_selectors if soup.select_one(selector) is root),
                'content_observation': {
                    'document_sha256': hashlib.sha256(response.content).hexdigest(),
                    'document_byte_length': len(response.content), 'selection': 'native_article_dom',
                    'selected_locators': [next(selector for selector in cls.body_selectors if soup.select_one(selector) is root)],
                    'source_text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'source_text_char_length': len(text), 'returned_text_char_length': len(text),
                    'completeness': 'COMPLETE_SELECTED_NATIVE_DOM', 'truncated': False},
                'publication_date_source': date_source, 'publication_date_state': date_state,
                'publication_native_text': date_node.get_text(' ', strip=True) if date_node else None,
                'media_list': media, 'media_hints': media, 'media_observation': media_observation,
                'source_use': 'NOT_GRANTED', 'source_claim_type': 'PLATFORM_AUTHOR_SOURCE_CLAIM',
            },
        }

    def _failure(self, exc, *, capability, cursor=None):
        code = str(exc) if isinstance(exc, (KoreanSourceError, NativePageWindowError)) else None
        code = code if code and re.fullmatch(r'[A-Z_]{1,100}', code) else 'PUBLIC_SOURCE_UNAVAILABLE'
        transport = public_source_error_metadata(exc)
        http = transport.get('http_status')
        status = {'VERIFICATION_REQUIRED': CollectionStatus.NEED_VERIFY,
                  'AUTH_REQUIRED': CollectionStatus.SESSION_EXPIRED,
                  'ACCESS_BLOCKED': CollectionStatus.BLOCKED}.get(code, CollectionStatus.PROVIDER_UNAVAILABLE)
        if http == 429:
            status, code = CollectionStatus.COOLING_DOWN, 'RATE_LIMITED'
        elif http in (401, 403):
            status, code = CollectionStatus.BLOCKED, 'ACCESS_BLOCKED'
        elif code in {'SOURCE_URL_INVALID', 'NATIVE_IDENTITY_MISMATCH', 'NATIVE_CURSOR_WINDOW_INVALID',
                      'NATIVE_CURSOR_PAGE_CHANGED', 'PAGE_CURSOR_INVALID', 'PAGE_SIZE_INVALID'}:
            status = CollectionStatus.COLLECT_ERROR
        return CollectionResult(status, self.platform, raw_count=None,
            message=self.platform.upper() + '_' + code, capability=capability,
            access_class=AccessClass.Z0_PUBLIC, backend='safe_public_http',
            metadata={'provider': self.platform + '_public_page', 'failure_class': code, **transport,
                'pagination': {'request_cursor': cursor, 'next_cursor': None, 'exhausted': None,
                    'page_complete': False, 'continuation_blocked': status in {
                        CollectionStatus.NEED_VERIFY, CollectionStatus.BLOCKED, CollectionStatus.SESSION_EXPIRED,
                        CollectionStatus.COOLING_DOWN}, 'resume_requires_fresh_page': code == 'NATIVE_CURSOR_PAGE_CHANGED'}})

    def _fetch(self, url):
        response = self.fetcher(url)
        if (type(response) is not PublicResponse or not 200 <= response.status_code < 300
                or not 0 < len(response.content) <= 2 * 1024 * 1024):
            raise KoreanSourceError('PUBLIC_RESPONSE_INVALID')
        return response

    def detail(self, content_id, **kwargs):
        try:
            expected = self._detail_target(content_id, kwargs.get('source_url'))
            response = self._fetch(expected.get('read_url') or expected['url'])
            item = self.parse_original(response)
            if item['platform_content_id'] != expected['native_content_id']:
                raise KoreanSourceError('NATIVE_IDENTITY_MISMATCH')
            item['captured_at'] = datetime.now(timezone.utc).isoformat()
            return CollectionResult(CollectionStatus.SUCCESS, self.platform, items=[item], raw_count=1, new_count=1,
                original_response=response, access_class=AccessClass.Z0_PUBLIC, backend='safe_public_http', capability='detail',
                metadata={'provider': self.platform + '_public_page', 'original_schema': self.original_schema,
                    'body_state': item['raw']['body_state'], **public_source_provenance(response, expected['url'])})
        except (PublicSourceError, KoreanSourceError, ValueError, TypeError) as exc:
            return self._failure(exc, capability='detail')

    @classmethod
    def _same_page_family(cls, value, base, *, mode):
        parts, original = _https_parts(value), _https_parts(base)
        if parts.hostname != original.hostname or parts.path != original.path:
            return False
        if mode == 'search':
            return parse_qs(parts.query).get(cls.search_parameter) == parse_qs(original.query).get(cls.search_parameter)
        if mode in {'author_posts', 'feed'}:
            return True
        try:
            return cls.identity(value)['native_content_id'] == cls.identity(base)['native_content_id']
        except KoreanSourceError:
            return False

    @classmethod
    def _next_page(cls, soup, response_url, *, mode):
        for anchor in soup.select('a[rel~=next], a.next, a.btn_next, a.link_next, a[aria-label="다음"]'):
            if anchor.get('aria-disabled') == 'true' or 'disabled' in (anchor.get('class') or []):
                continue
            candidate = urljoin(response_url, str(anchor.get('href') or ''))
            try:
                if candidate != response_url and cls._same_page_family(candidate, response_url, mode=mode):
                    return candidate
            except KoreanSourceError:
                continue
        return None

    def _listing(self, target, *, mode, base_url, max_results, cursor=None):
        try:
            if type(max_results) is not int or not 1 <= max_results <= 100:
                raise KoreanSourceError('PAGE_SIZE_INVALID')
            fingerprint = hashlib.sha256(target.encode('utf-8')).hexdigest()
            validate_native_page_window_cursor(cursor)
            if cursor is not None and (not isinstance(cursor, dict) or cursor.get('mode') != mode
                    or cursor.get('target_sha256') != fingerprint or not isinstance(cursor.get('page_url'), str)
                    or not self._same_page_family(cursor['page_url'], base_url, mode=mode)):
                raise KoreanSourceError('PAGE_CURSOR_INVALID')
            url = cursor['page_url'] if cursor else base_url
            response = self._fetch(url)
            if not self._same_page_family(response.url, base_url, mode=mode):
                raise KoreanSourceError('NATIVE_IDENTITY_MISMATCH')
            soup = BeautifulSoup(response.content, 'html.parser')
            items, seen = [], set()
            for anchor in soup.select('a[href]'):
                try:
                    native = self.identity(urljoin(response.url, str(anchor['href'])))
                except KoreanSourceError:
                    continue
                if native['native_content_id'] in seen:
                    continue
                if mode == 'author_posts' and native.get('author_id') != target:
                    continue
                seen.add(native['native_content_id'])
                label = anchor.get_text(' ', strip=True)
                items.append({'platform_content_id': native['native_content_id'], 'url': native['url'],
                    'title': label, 'content': '', 'author_id': native.get('author_id'), 'author_nickname': None,
                    'publish_datetime': '', 'likes': None, 'comments': None, 'collects': None, 'shares': None,
                    'raw': {**native, 'native_kind': native['kind'], 'body_state': 'DISCOVERY_LINK_ONLY',
                        'discovery_snippet': label, 'description_is_original_body': False,
                        'discovery_document_sha256': hashlib.sha256(response.content).hexdigest()}})
            problem = _page_problem(soup, has_article=bool(items))
            if problem:
                raise KoreanSourceError(problem)
            window = native_page_window(items, limit=max_results, cursor=cursor,
                                        identities=[value['platform_content_id'] for value in items])
            next_url = self._next_page(soup, response.url, mode=mode)
            base_cursor = {'mode': mode, 'target_sha256': fingerprint, 'page_url': url}
            next_cursor = ({**base_cursor, **window['next_window']} if not window['page_complete'] else
                           {**base_cursor, 'page_url': next_url} if next_url else None)
            known_empty = soup.select_one('.not_found, .no_result, .api_noresult, [data-empty="true"]') is not None
            if not items and not known_empty:
                raise KoreanSourceError('NATIVE_RESULT_LIST_NOT_OBSERVED')
            return CollectionResult(CollectionStatus.SUCCESS if window['rows'] else CollectionStatus.NO_NEW_DATA,
                self.platform, items=window['rows'], raw_count=len(window['rows']), new_count=len(window['rows']),
                access_class=AccessClass.Z0_PUBLIC, backend='safe_public_http', capability=mode,
                metadata={'provider': self.platform + '_public_page', **public_source_provenance(response, url),
                    'pagination': {'request_cursor': cursor, 'next_cursor': next_cursor,
                        'exhausted': False if next_cursor else True if known_empty else None,
                        'page_complete': window['page_complete'], 'coverage_scope': 'VISIBLE_NATIVE_LINKS',
                        'observed_native_rows': len(items), 'native_next_page_url': next_url,
                        'partial_reason': 'REQUESTED_LIMIT_REACHED' if not window['page_complete'] else
                            'NATIVE_END_NOT_DECLARED' if not next_url and not known_empty else None}})
        except (PublicSourceError, KoreanSourceError, NativePageWindowError, ValueError, TypeError) as exc:
            return self._failure(exc, capability=mode, cursor=cursor)

    def search(self, keyword, **kwargs):
        if not isinstance(keyword, str) or not keyword.strip() or len(keyword) > 512:
            return self._failure(KoreanSourceError('QUERY_INVALID'), capability='search')
        url = 'https://' + self.search_host + self.search_path + '?' + urlencode({self.search_parameter: keyword})
        return self._listing(keyword, mode='search', base_url=url,
                             max_results=kwargs.get('max_results', 20), cursor=kwargs.get('cursor'))

    def _feed(self, url, *, owner, kind, max_results, cursor=None):
        """Read an explicitly selected native feed; never retry a blocked HTML route."""
        try:
            if type(max_results) is not int or not 1 <= max_results <= 100:
                raise KoreanSourceError('PAGE_SIZE_INVALID')
            validate_native_page_window_cursor(cursor)
            if cursor is not None and (not isinstance(cursor, dict) or cursor.get('mode') != 'feed'
                    or cursor.get('owner_id') != owner or not self._same_page_family(cursor.get('page_url'), url, mode='feed')):
                raise KoreanSourceError('PAGE_CURSOR_INVALID')
            selected_url = cursor['page_url'] if cursor else url
            response = self._fetch(selected_url)
            if not self._same_page_family(response.url, url, mode='feed'):
                raise KoreanSourceError('NATIVE_IDENTITY_MISMATCH')
            parsed = feedparser.parse(response.content)
            if parsed.bozo and not parsed.entries or not parsed.get('version'):
                problem = _page_problem(BeautifulSoup(response.content, 'html.parser'))
                raise KoreanSourceError(problem or 'NATIVE_FEED_NOT_OBSERVED')
            rows = list(parsed.entries)
            identities = []
            for row in rows:
                native = self.identity(str(row.get('link') or ''))
                if native['kind'] != kind or native.get('author_id') != owner:
                    raise KoreanSourceError('NATIVE_IDENTITY_MISMATCH')
                identities.append(native['native_content_id'])
            window = native_page_window(rows, limit=max_results, cursor=cursor, identities=identities)
            items = []
            for row in window['rows']:
                native = self.identity(str(row['link']))
                content_values = row.get('content') or []
                declared_body = next((value.get('value') for value in content_values
                                      if isinstance(value, dict) and isinstance(value.get('value'), str)), None)
                fragment = declared_body if declared_body is not None else str(row.get('summary') or '')
                text = BeautifulSoup(fragment, 'html.parser').get_text('\n', strip=True)
                source_time = str(row.get('published') or '')
                published = ''
                if row.get('published_parsed'):
                    published = datetime(*row['published_parsed'][:6], tzinfo=timezone.utc).isoformat()
                items.append({'platform_content_id': native['native_content_id'], 'title': str(row.get('title') or ''),
                    'content': text, 'url': native['url'], 'author_id': owner, 'author_nickname': row.get('author'),
                    'publish_datetime': published, 'likes': None, 'comments': None, 'shares': None, 'collects': None,
                    'raw': {**native, 'native_kind': kind, 'entry_id': str(row.get('id') or row['link']),
                        'body_state': 'FEED_DECLARED_CONTENT' if declared_body is not None else 'FEED_EXCERPT',
                        'whole_article_verified': False, 'source_published_at': source_time,
                        'feed_document_sha256': hashlib.sha256(response.content).hexdigest(),
                        'feed_url': selected_url, 'source_use': 'NOT_GRANTED'}})
            next_url = None
            for link in parsed.feed.get('links') or []:
                if link.get('rel') == 'next' and isinstance(link.get('href'), str):
                    candidate = urljoin(response.url, link['href'])
                    if candidate != selected_url and self._same_page_family(candidate, url, mode='feed'):
                        next_url = candidate
                        break
            base = {'mode': 'feed', 'owner_id': owner, 'page_url': selected_url}
            next_cursor = ({**base, **window['next_window']} if not window['page_complete'] else
                           {**base, 'page_url': next_url} if next_url else None)
            return CollectionResult(CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
                self.platform, items=items, raw_count=len(items), new_count=len(items), access_class=AccessClass.Z0_PUBLIC,
                backend='safe_public_http', capability='search', metadata={'provider': self.platform + '_native_public_feed',
                    **public_source_provenance(response, selected_url), 'pagination': {'request_cursor': cursor,
                        'next_cursor': next_cursor, 'exhausted': False if next_cursor else None,
                        'page_complete': window['page_complete'], 'coverage_scope': 'PROVIDER_EXPOSED_FEED',
                        'partial_reason': 'REQUESTED_LIMIT_REACHED' if not window['page_complete'] else
                            'FEED_DOES_NOT_ESTABLISH_COMPLETE_HISTORY' if not next_url else None}})
        except (PublicSourceError, KoreanSourceError, NativePageWindowError, ValueError, TypeError) as exc:
            return self._failure(exc, capability='search', cursor=cursor)

    def _public_profile(self, owner, *, url, kind):
        try:
            response = self._fetch(url)
            expected, actual = _https_parts(url), _https_parts(response.url)
            if expected.hostname != actual.hostname or expected.path.rstrip('/') != actual.path.rstrip('/'):
                raise KoreanSourceError('NATIVE_IDENTITY_MISMATCH')
            soup = BeautifulSoup(response.content, 'html.parser')
            problem = _page_problem(soup)
            if problem:
                raise KoreanSourceError(problem)
            title = _meta(soup, 'og:title')
            if not title:
                raise KoreanSourceError('NATIVE_PROFILE_NOT_OBSERVED')
            return CollectionResult(CollectionStatus.SUCCESS, self.platform, items=[{
                'platform_content_id': f'profile:{kind}:{owner}', 'author_id': owner, 'author_nickname': title,
                'title': title, 'content': _meta(soup, 'og:description'), 'url': url,
                'likes': None, 'comments': None, 'shares': None, 'collects': None,
                'raw': {'native_content_id': f'profile:{kind}:{owner}', 'native_kind': kind + '_profile',
                    'blog_id': owner, 'followers': None, 'following_count': None, 'content_count': None,
                    'document_sha256': hashlib.sha256(response.content).hexdigest()}}], raw_count=1, new_count=1,
                access_class=AccessClass.Z0_PUBLIC, backend='safe_public_http', capability='author',
                metadata={'provider': self.platform + '_public_profile', **public_source_provenance(response, url)})
        except (PublicSourceError, KoreanSourceError, ValueError, TypeError) as exc:
            return self._failure(exc, capability='author')

    def comments(self, content_id, *, include_replies=False, **kwargs):
        cursor, limit = kwargs.get('cursor'), kwargs.get('max_comments', 20)
        try:
            expected = self._detail_target(content_id, kwargs.get('source_url'))
            if type(limit) is not int or not 1 <= limit <= 100:
                raise KoreanSourceError('PAGE_SIZE_INVALID')
            validate_native_page_window_cursor(cursor)
            if cursor is not None and (not isinstance(cursor, dict) or cursor.get('mode') != 'comments'
                    or cursor.get('content_id') != expected['native_content_id']
                    or not self._same_page_family(cursor.get('page_url'), expected['read_url'], mode='comments')):
                raise KoreanSourceError('PAGE_CURSOR_INVALID')
            url = cursor['page_url'] if cursor else expected['read_url']
            response = self._fetch(url)
            if self.identity(response.url)['native_content_id'] != expected['native_content_id']:
                raise KoreanSourceError('NATIVE_IDENTITY_MISMATCH')
            soup = BeautifulSoup(response.content, 'html.parser')
            problem = _page_problem(soup, has_article=any(soup.select_one(v) for v in self.body_selectors))
            if problem:
                raise KoreanSourceError(problem)
            comments, seen = [], set()
            for node in soup.select('[data-comment-id], [data-comment-no], li[id^="comment"]'):
                native = node.get('data-comment-id') or node.get('data-comment-no')
                if not native:
                    match = re.fullmatch(r'comment[_-]?([0-9]+)', str(node.get('id') or ''))
                    native = match[1] if match else None
                if not isinstance(native, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', native) or native in seen:
                    continue
                text_node = node.select_one('[data-comment-body], .u_cbox_contents, .text, .comment-text, .desc')
                if text_node is None:
                    continue
                text_owner = text_node.find_parent(attrs={'data-comment-id': True}) or text_node.find_parent(
                    attrs={'data-comment-no': True}) or text_node.find_parent('li', id=re.compile(r'^comment[_-]?[0-9]+$'))
                if text_owner is not None and text_owner is not node:
                    continue
                parent = node.get('data-parent-comment-id') or node.get('data-parent-comment-no')
                if not parent:
                    ancestor = node.find_parent(attrs={'data-comment-id': True}) or node.find_parent('li', id=re.compile(r'^comment[_-]?[0-9]+$'))
                    if ancestor:
                        parent = ancestor.get('data-comment-id') or re.sub(r'^comment[_-]?', '', ancestor['id'])
                author = node.select_one('[data-author-id], .u_cbox_nick, .nickname, .name')
                date = node.select_one('time[datetime]')
                seen.add(native)
                comments.append({'platform_comment_id': native, 'parent_content_id': expected['native_content_id'],
                    'parent_comment_id': str(parent) if parent not in (None, '', '0') else None,
                    'reply_to_comment_id': node.get('data-reply-to-comment-id'),
                    'content': text_node.get_text(' ', strip=True),
                    'author_id': author.get('data-author-id') if author else None,
                    'author_nickname': author.get_text(' ', strip=True) if author else None,
                    'publish_datetime': date.get('datetime') if date else '',
                    'likes': optional_int(node.get('data-like-count')), 'url': expected['url'] + '#comment' + native,
                    'raw': {'native_kind': expected['kind'], 'native_comment_id': native,
                        'document_sha256': hashlib.sha256(response.content).hexdigest(), 'capture_mode': 'PUBLIC_NATIVE_COMMENT_DOM'}})
            count_node = soup.select_one('[data-comment-count]')
            reported = optional_int(count_node.get('data-comment-count')) if count_node else None
            if not comments and reported != 0:
                raise KoreanSourceError('NATIVE_COMMENTS_NOT_OBSERVED')
            window = native_page_window(comments, limit=limit, cursor=cursor,
                                        identities=[row['platform_comment_id'] for row in comments])
            next_url = self._next_page(soup, response.url, mode='comments')
            continuation = {'mode': 'comments', 'content_id': expected['native_content_id'], 'page_url': url}
            next_cursor = ({**continuation, **window['next_window']} if not window['page_complete'] else
                           {**continuation, 'page_url': next_url} if next_url else None)
            return CollectionResult(CollectionStatus.SUCCESS if window['rows'] else CollectionStatus.NO_NEW_DATA,
                self.platform, comments=window['rows'], raw_count=len(window['rows']), new_count=len(window['rows']),
                access_class=AccessClass.Z0_PUBLIC, backend='safe_public_http', capability='comments',
                metadata={'provider': self.platform + '_public_comment_dom', 'include_replies_requested': bool(include_replies),
                    'returned_reply_relationships_preserved': True, **public_source_provenance(response, url),
                    'pagination': {'request_cursor': cursor, 'next_cursor': next_cursor,
                        'exhausted': False if next_cursor else True if reported == 0 else None,
                        'reported_total': reported, 'page_complete': window['page_complete'],
                        'coverage_scope': 'OBSERVED_NATIVE_COMMENT_DOM',
                        'partial_reason': 'REQUESTED_LIMIT_REACHED' if not window['page_complete'] else
                            None if reported == 0 else 'NATIVE_END_NOT_DECLARED'}})
        except (PublicSourceError, KoreanSourceError, NativePageWindowError, ValueError, TypeError) as exc:
            return self._failure(exc, capability='comments', cursor=cursor)

    def health_check(self, **_kwargs):
        return CollectionResult(CollectionStatus.NEED_VERIFY, self.platform,
            message='公开来源只在用户本次采集时验证，不在状态页联网',
            metadata={'provider': self.platform + '_public_page', 'healthcheck_scope': 'configuration_only',
                      'network_performed': False, 'requires_authorization': False})


class NaverAdapter(_KoreanPublicPageAdapter):
    platform = 'naver'
    enabled = False
    monitor_priority = 'secondary'
    body_selectors = ('.se-main-container', '#postViewArea', '.post-view', '.ContentRenderer', '#tbody')
    search_host, search_path, search_parameter = 'search.naver.com', '/search.naver', 'query'

    @classmethod
    def identity(cls, value):
        if isinstance(value, str) and not value.startswith('https://'):
            match = re.fullmatch(r'(blog|cafe):([A-Za-z0-9_-]{1,64}):([0-9]{1,20})', value)
            if match:
                value = f'https://{"blog" if match[1] == "blog" else "cafe"}.naver.com/{match[2]}/{match[3]}'
        parts = _https_parts(value)
        query, segments = parse_qs(parts.query), [value for value in parts.path.split('/') if value]
        if parts.hostname in {'blog.naver.com', 'm.blog.naver.com'}:
            if parts.path == '/PostView.naver':
                owner, post = query.get('blogId', [''])[0], query.get('logNo', [''])[0]
            else:
                owner, post = segments if len(segments) == 2 else ('', '')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', owner) or not re.fullmatch(r'[0-9]{1,20}', post):
                raise KoreanSourceError('SOURCE_URL_INVALID')
            return {'kind': 'blog', 'native_content_id': f'blog:{owner}:{post}', 'blog_id': owner,
                    'log_no': post, 'author_id': owner, 'url': f'https://blog.naver.com/{owner}/{post}',
                    'read_url': 'https://blog.naver.com/PostView.naver?' + urlencode({'blogId': owner, 'logNo': post})}
        if parts.hostname in {'cafe.naver.com', 'm.cafe.naver.com'}:
            if len(segments) == 5 and segments[:2] == ['ca-fe', 'cafes'] and segments[3] == 'articles':
                owner, post = segments[2], segments[4]
            else:
                owner, post = segments if len(segments) == 2 else ('', '')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', owner) or not re.fullmatch(r'[0-9]{1,20}', post):
                raise KoreanSourceError('SOURCE_URL_INVALID')
            canonical = (f'https://cafe.naver.com/ca-fe/cafes/{owner}/articles/{post}' if owner.isdigit()
                         else f'https://cafe.naver.com/{owner}/{post}')
            return {'kind': 'cafe', 'native_content_id': f'cafe:{owner}:{post}', 'cafe_id': owner,
                    'article_id': post, 'author_id': None, 'url': canonical, 'read_url': canonical}
        raise KoreanSourceError('SOURCE_URL_INVALID')

    def creator(self, creator_id, **kwargs):
        owner = str(creator_id).removeprefix('blog:')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', owner):
            return self._failure(KoreanSourceError('AUTHOR_ID_INVALID'), capability='author')
        return self._public_profile(owner, url='https://blog.naver.com/' + owner, kind='blog')

    def search(self, keyword, **kwargs):
        if isinstance(keyword, str) and keyword.startswith('https://rss.blog.naver.com/'):
            try:
                parts = _https_parts(keyword)
                match = re.fullmatch(r'/([A-Za-z0-9_-]{1,64})\.xml', parts.path)
                if not match or parts.hostname != 'rss.blog.naver.com' or parts.query:
                    raise KoreanSourceError('SOURCE_URL_INVALID')
            except KoreanSourceError as exc:
                return self._failure(exc, capability='search')
            return self._feed(keyword, owner=match[1], kind='blog', max_results=kwargs.get('max_results', 20), cursor=kwargs.get('cursor'))
        return super().search(keyword, **kwargs)

    def author_posts(self, author_id, **kwargs):
        owner = str(author_id).removeprefix('blog:')
        cursor, limit = kwargs.get('cursor'), kwargs.get('max_results', 20)
        try:
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', owner):
                raise KoreanSourceError('AUTHOR_ID_INVALID')
            if type(limit) is not int or not 1 <= limit <= 100:
                raise KoreanSourceError('PAGE_SIZE_INVALID')
            validate_native_page_window_cursor(cursor)
            if cursor is not None and (not isinstance(cursor, dict) or cursor.get('mode') != 'blog_history'
                    or cursor.get('blog_id') != owner or type(cursor.get('page')) is not int or not 1 <= cursor['page'] <= 100000):
                raise KoreanSourceError('PAGE_CURSOR_INVALID')
            if cursor is not None and 'previous_page_sha256' in cursor and (
                    not isinstance(cursor['previous_page_sha256'], str)
                    or re.fullmatch(r'[0-9a-f]{64}', cursor['previous_page_sha256']) is None):
                raise KoreanSourceError('PAGE_CURSOR_INVALID')
            page = cursor['page'] if cursor else 1
            url = f'https://m.blog.naver.com/api/blogs/{quote(owner)}/post-list?' + urlencode({'categoryNo': 0, 'itemCount': 30, 'page': page})
            response = self._fetch(url)
            if response.url != url or response.content_type != 'application/json':
                problem = _page_problem(BeautifulSoup(response.content, 'html.parser'))
                raise KoreanSourceError(problem or 'NATIVE_HISTORY_RESPONSE_INVALID')
            result = json.loads(response.content)
            result = result.get('result') if isinstance(result, dict) else None
            if not isinstance(result, dict) or not isinstance(result.get('items'), list):
                raise KoreanSourceError('NATIVE_HISTORY_RESPONSE_INVALID')
            rows = result['items']
            window = native_page_window(rows, limit=limit, cursor=cursor, identities=[
                str(row.get('logNo')) if isinstance(row, dict) else None for row in rows])
            if rows and window['page_sha256'] == (cursor or {}).get('previous_page_sha256'):
                raise KoreanSourceError('NATIVE_HISTORY_PAGE_REPEATED')
            items = []
            for row in window['rows']:
                if not isinstance(row, dict) or not re.fullmatch(r'[0-9]{1,20}', str(row.get('logNo') or '')):
                    raise KoreanSourceError('NATIVE_HISTORY_IDENTITY_INVALID')
                native = self.identity(f'https://blog.naver.com/{owner}/{row["logNo"]}')
                millis = row.get('addDate')
                published = datetime.fromtimestamp(millis / 1000, timezone.utc).isoformat() if type(millis) is int else ''
                items.append({'platform_content_id': native['native_content_id'], 'title': BeautifulSoup(
                    str(row.get('titleWithInspectMessage') or row.get('title') or ''), 'html.parser').get_text(' ', strip=True),
                    'content': '', 'url': native['url'], 'author_id': owner, 'author_nickname': None,
                    'publish_datetime': published, 'likes': optional_int(row.get('sympathyCnt')) if 'sympathyCnt' in row else optional_int(row.get('likeItCnt')),
                    'comments': optional_int(row.get('commentCount')), 'views': optional_int(row.get('readCount')),
                    'collects': None, 'shares': None, 'raw': {**native, 'native_kind': 'blog',
                        'body_state': 'HISTORY_METADATA_ONLY', 'source_observation': row,
                        'author_history_binding': {'requested_id': owner, 'kind': 'blog_id'}}})
            base = {'mode': 'blog_history', 'blog_id': owner, 'page': page}
            if 'previous_page_sha256' in (cursor or {}):
                base['previous_page_sha256'] = cursor['previous_page_sha256']
            next_cursor = ({**base, **window['next_window']} if not window['page_complete'] else
                           {**base, 'page': page + 1, 'previous_page_sha256': window['page_sha256']} if rows else None)
            return CollectionResult(CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
                self.platform, items=items, raw_count=len(items), new_count=len(items), access_class=AccessClass.Z0_PUBLIC,
                backend='safe_public_http', capability='author_posts', metadata={'provider': 'naver_public_blog_history',
                    **public_source_provenance(response, url), 'pagination': {'request_cursor': cursor,
                        'next_cursor': next_cursor, 'exhausted': not rows, 'page_complete': window['page_complete'],
                        'native_page': page, 'native_page_size': 30, 'reported_total': None,
                        'coverage_scope': 'PUBLIC_BLOG_HISTORY', 'partial_reason': 'REQUESTED_LIMIT_REACHED' if not window['page_complete'] else None}})
        except (PublicSourceError, KoreanSourceError, NativePageWindowError, ValueError, TypeError, OverflowError, OSError) as exc:
            return self._failure(exc, capability='author_posts', cursor=cursor)


register_adapter('naver', NaverAdapter)
