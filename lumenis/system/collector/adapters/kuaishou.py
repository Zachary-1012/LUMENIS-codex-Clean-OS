from __future__ import annotations

from typing import Any
import re
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter


class KuaishouAdapter(BasePlatformAdapter):
    """Kuaishou boundary for an explicitly authorized first-party/session backend.

    Native reads use the platform's own registered browser requests, including
    current REST or GraphQL pages. No signer or alternate identity is created.
    Explicitly authorized providers may also use the retained injected boundary.
    """

    platform = "kuaishou"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, browser_factory=None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend
        self.browser_factory = browser_factory

    def _delegate(self, capability: str, *args: Any, **kwargs: Any) -> CollectionResult:
        if self.backend is None:
            return self._browser_read(capability, *args, **kwargs)
        method = getattr(self.backend, capability, None)
        if not callable(method):
            return CollectionResult(
                status=CollectionStatus.NOT_SUPPORTED,
                platform=self.platform,
                message=f"configured Kuaishou provider does not support {capability}",
            )
        try:
            result = method(*args, **kwargs)
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="Kuaishou provider request failed",
                metadata={"error_type": type(exc).__name__, "provider": "authorized_session"},
            )
        if isinstance(result, CollectionResult):
            return result
        return CollectionResult(
            status=CollectionStatus.PROVIDER_UNAVAILABLE,
            platform=self.platform,
            message="Kuaishou provider returned an invalid result",
        )

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        return self._delegate("search", keyword, **kwargs)

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate("detail", content_id, **kwargs)

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return self._delegate("comments", content_id, include_replies=include_replies, **kwargs)

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate("author", creator_id, **kwargs)

    def author_posts(self, author_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate("author_posts", author_id, **kwargs)

    def health_check(self, **kwargs: Any) -> CollectionResult:
        if self.backend is None:
            from lumenis.adapters.human_browser import readonly_worker_health
            try: health = readonly_worker_health(self.platform)
            except RuntimeError: return CollectionResult(CollectionStatus.NOT_CONFIGURED, self.platform, message='KUAISHOU_READONLY_WORKER_NOT_REGISTERED')
            return CollectionResult(CollectionStatus(health['status']), self.platform, message='快手注册只读会话状态；实际读取仍需验证', metadata=health['metadata'])
        method = getattr(self.backend, "healthcheck", None) or getattr(self.backend, "health_check", None)
        if not callable(method):
            return CollectionResult(
                status=CollectionStatus.NOT_CONFIGURED,
                platform=self.platform,
                message="Kuaishou provider has no health check",
                metadata={"provider": "authorized_session", "healthcheck_scope": "configuration_only"},
            )
        return self._delegate("healthcheck" if getattr(self.backend, "healthcheck", None) else "health_check", **kwargs)

    @staticmethod
    def _time(value):
        if type(value) in {int, float}:
            try: return datetime.fromtimestamp(value / 1000 if value > 100_000_000_000 else value, timezone.utc).isoformat()
            except (ValueError, OSError, OverflowError): pass
        return ''

    def _photo(self, record):
        from lumenis.adapters.base import optional_int
        photo = record.get('photo') if isinstance(record.get('photo'), dict) else record
        pid = photo.get('id') or photo.get('photoId')
        user = record.get('author') or photo.get('author') or {}
        if not isinstance(pid, str) or re.fullmatch(r'[A-Za-z0-9_-]{6,100}', pid) is None: return None
        caption = photo.get('caption')
        if not isinstance(caption, str): return None
        hints = []
        for key, kind in (('coverUrl', 'video_cover'), ('photoUrl', 'video'), ('videoUrl', 'video')):
            value = photo.get(key)
            if isinstance(value, str):
                parsed = urlsplit(value)
                if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password:
                    hints.append({'kind': kind, 'url': value, 'locator': '$.photo.' + key, 'native_media_id': pid, 'bytes_state': 'NOT_ACQUIRED'})
        return {'platform_content_id': pid, 'title': caption[:100], 'content': caption, 'url': 'https://www.kuaishou.com/short-video/' + pid,
            'author_id': str(user.get('id') or user.get('userId') or ''), 'author_nickname': user.get('name') or user.get('userName') or '',
            'publish_datetime': self._time(photo.get('timestamp')), 'likes': optional_int(photo.get('likeCount')),
            'comments': optional_int(photo.get('commentCount')), 'collects': None, 'shares': optional_int(photo.get('shareCount')),
            'views': optional_int(photo.get('viewCount')), 'cover': photo.get('coverUrl') or '',
            'raw': {'engine': 'kuaishou_native_page', 'photo_id': pid, 'source_observation': record, 'body_state': 'PLATFORM_CAPTION', 'media_hints': hints}}

    def _browser_read(self, capability, target, **kwargs):
        from lumenis.adapters.base import optional_int
        from lumenis.adapters.cookie_vault import inject_into_context
        from lumenis.adapters.human_browser import (HumanBrowser, NativeReadCapture, PageState, configured_readonly_worker_url,
                                                    NativePageWindowError, native_page_window, native_read_scroll,
                                                    validate_native_page_window_cursor)
        limit = kwargs.get('max_comments', 20) if capability == 'comments' else kwargs.get('max_results', 20)
        cursor = kwargs.get('cursor')
        if type(limit) is not int or not 1 <= limit <= 100 or not isinstance(target, str) or not target.strip():
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='KUAISHOU_TARGET_OR_PAGE_SIZE_INVALID')
        if cursor is not None and (not isinstance(cursor, dict) or cursor.get('mode') not in {'search', 'posts', 'roots', 'replies'}
                or not isinstance(cursor.get('pcursor'), str) or len(cursor['pcursor']) > 4096
                or any(ord(c) < 32 for c in cursor['pcursor'])):
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='KUAISHOU_NATIVE_CURSOR_INVALID')
        if (cursor or {}).get('mode') == 'replies' and (not isinstance(cursor.get('root_id'), str) or not cursor['root_id'].isdigit()
                or not isinstance(cursor.get('pending_roots'), list) or len(cursor['pending_roots']) > 100
                or any(not isinstance(v, str) or not v.isdigit() for v in cursor['pending_roots'])):
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='KUAISHOU_NATIVE_CURSOR_INVALID')
        expected_mode = {'search': 'search', 'author_posts': 'posts', 'comments': 'roots'}.get(capability)
        if cursor is not None and (expected_mode is None or cursor['mode'] not in (
                {'roots', 'replies'} if capability == 'comments' else {expected_mode})):
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='KUAISHOU_NATIVE_CURSOR_INVALID')
        try:
            validate_native_page_window_cursor(cursor)
            if (cursor or {}).get('mode') == 'replies':
                validate_native_page_window_cursor(cursor.get('next_root'))
        except NativePageWindowError:
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, raw_count=None,
                                    message='KUAISHOU_NATIVE_CURSOR_WINDOW_INVALID')
        if capability == 'search':
            url = 'https://www.kuaishou.com/search/video?searchKey=' + quote(target)
        elif capability in {'detail', 'comments'}:
            if target.startswith('https://'):
                parsed = urlsplit(target)
                match = re.fullmatch(r'/short-video/([A-Za-z0-9_-]{6,100})/?', parsed.path)
                if parsed.hostname != 'www.kuaishou.com' or parsed.username or parsed.password or not match:
                    return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='KUAISHOU_SOURCE_PERMALINK_INVALID')
                target = match[1]
            if re.fullmatch(r'[A-Za-z0-9_-]{6,100}', target) is None:
                return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='KUAISHOU_CONTENT_ID_INVALID')
            url = 'https://www.kuaishou.com/short-video/' + target
        else:
            if re.fullmatch(r'[A-Za-z0-9_-]{3,100}', target) is None:
                return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='KUAISHOU_AUTHOR_ID_INVALID')
            url = 'https://www.kuaishou.com/profile/' + target
        worker, page = None, None
        capture = NativeReadCapture(hosts={'www.kuaishou.com', 'www.kuaishou.com.cn'},
            paths=('/graphql', '/rest/v/search/feed', '/rest/v/profile/feed', '/rest/v/photo/comment/'),
            request_keys={'keyword', 'pcursor', 'userId', 'user_id', 'photoId', 'rootCommentId', 'commentId', 'operationName', 'searchSessionId'})
        try:
            worker = self.browser_factory() if self.browser_factory else HumanBrowser(cdp_url=configured_readonly_worker_url('kuaishou'), auto_ensure=False, launch_url='about:blank')
            worker.connect(); inject_into_context(worker._context, 'kuaishou')
            page = worker.new_page(stealth=False); capture.attach(page)
            page.goto(url, wait_until='domcontentloaded', timeout=30000); page.wait_for_timeout(900)
            def select(observation):
                request = observation['request']
                if str(request.get('pcursor') or '') != str((cursor or {}).get('pcursor') or ''): return None
                if capability == 'search' and request.get('keyword') != target: return None
                if capability in {'detail', 'comments'} and str(request.get('photoId') or '') != target: return None
                if capability in {'author', 'author_posts'} and str(request.get('userId') or request.get('user_id') or '') != target: return None
                root_id = (cursor or {}).get('root_id')
                if capability == 'comments' and (bool(root_id) != bool(request.get('rootCommentId')) or root_id and str(request['rootCommentId']) != root_id): return None
                for obj in observation['objects']:
                    if not isinstance(obj, dict): continue
                    data = obj.get('data') if isinstance(obj.get('data'), dict) else obj
                    for name in {'search': ('visionSearchPhoto',), 'detail': ('visionVideoDetail',), 'author': ('visionProfile',),
                                 'author_posts': ('visionProfilePhotoList',), 'comments': ('visionCommentList', 'visionSubCommentList')}[capability]:
                        if isinstance(data.get(name), dict): data = data[name]; break
                    if data.get('result') not in (1, None): observation['failure_class'] = 'PROVIDER_REJECTED'; return None
                    if capability == 'author' and isinstance(data.get('userProfile'), dict): return {'body': data, 'profile': data['userProfile']}
                    if capability == 'detail' and isinstance(data.get('photo'), dict): return {'body': data, 'rows': [data]}
                    keys = ('subCommentsV2', 'subComments') if root_id else ('rootCommentsV2', 'rootComments') if capability == 'comments' else ('feeds',)
                    for key in keys:
                        if isinstance(data.get(key), list): return {'body': data, 'rows': data[key]}
                return None
            def advance(_step):
                if worker.detect_state(page) in {PageState.AUTH_FAILED, PageState.BLOCKED, PageState.CAPTCHA, PageState.NETWORK_ERROR}: return False
                return native_read_scroll(page, reply_id=(cursor or {}).get('root_id'), reply_attribute='data-comment-id')
            selected = capture.seek(page, select, advance, max_steps=16)
            if selected is None:
                failure = capture.failure() or {}; state = worker.detect_state(page)
                code = failure.get('failure_class') or {PageState.AUTH_FAILED: 'AUTH_REQUIRED', PageState.CAPTCHA: 'VERIFICATION_REQUIRED', PageState.BLOCKED: 'ACCESS_BLOCKED'}.get(state, 'NATIVE_PAGE_NOT_OBSERVED')
                status = {'AUTH_REQUIRED': CollectionStatus.SESSION_EXPIRED, 'VERIFICATION_REQUIRED': CollectionStatus.NEED_VERIFY,
                          'ACCESS_BLOCKED': CollectionStatus.BLOCKED, 'RATE_LIMITED': CollectionStatus.COOLING_DOWN}.get(code, CollectionStatus.PROVIDER_UNAVAILABLE)
                return CollectionResult(status, self.platform, raw_count=None, message='KUAISHOU_' + code,
                    metadata={'provider': 'registered_browser_native_read', 'failure_class': code, 'http_status': failure.get('http_status'), 'retry_after_seconds': failure.get('retry_after_seconds')})
            data = selected['body']
            if capability == 'author':
                profile = selected['profile']; user = profile.get('profile') or profile
                if str(user.get('userId') or user.get('id') or '') != target:
                    return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='KUAISHOU_AUTHOR_IDENTITY_MISMATCH')
                counts = profile.get('ownerCount') or {}
                return CollectionResult(CollectionStatus.SUCCESS, self.platform, items=[{'platform_content_id': target, 'author_id': target,
                    'author_nickname': user.get('userName') or '', 'title': user.get('userName') or '', 'content': user.get('userText') or '', 'url': url,
                    'likes': None, 'comments': None, 'collects': None, 'shares': None,
                    'raw': {'user_id': target, 'source_observation': profile, 'followers': optional_int(counts.get('fan')),
                            'following_count': optional_int(counts.get('follow')), 'content_count': optional_int(counts.get('photo_public'))}}], raw_count=1, new_count=1)
            rows = selected['rows']
            window = native_page_window(rows, limit=limit, cursor=cursor, identities=[
                str(row.get('commentId') if capability == 'comments' else
                    (row.get('photo') if isinstance(row.get('photo'), dict) else row).get('id') or
                    (row.get('photo') if isinstance(row.get('photo'), dict) else row).get('photoId'))
                if isinstance(row, dict) else None for row in rows])
            complete = window['page_complete']
            next_value = data.get('pcursorV2') if 'pcursorV2' in data else data.get('pcursor')
            exhausted = next_value == 'no_more' if isinstance(next_value, str) and next_value and complete else None
            base_cursor = {key: value for key, value in (cursor or {}).items()
                           if key not in {'item_offset', 'page_sha256'}}
            base_cursor.setdefault('mode', expected_mode or 'roots')
            base_cursor.setdefault('pcursor', '')
            next_cursor = ({**base_cursor, **window['next_window']} if not complete else
                           {**base_cursor, 'pcursor': next_value} if isinstance(next_value, str)
                           and next_value not in {'', 'no_more', base_cursor['pcursor']} else None)
            if not complete:
                exhausted = False
            if next_cursor and isinstance(data.get('searchSessionId'), str): next_cursor['search_session_id'] = data['searchSessionId']
            items, comments, seen, pending = [], [], set(), []
            for row in window['rows']:
                if not isinstance(row, dict): continue
                if capability != 'comments':
                    item = self._photo(row)
                    if not item: continue
                    if capability == 'author_posts' and item['author_id'] != target:
                        return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='KUAISHOU_AUTHOR_HISTORY_IDENTITY_MISMATCH')
                    if capability == 'author_posts': item['raw']['author_history_binding'] = {'requested_id': target}
                    items.append(item)
                else:
                    cid = str(row.get('commentId') or '')
                    if not cid or cid in seen: continue
                    seen.add(cid)
                    parent = row.get('rootCommentId') or (cursor or {}).get('root_id')
                    comments.append({'platform_comment_id': cid, 'parent_content_id': target, 'parent_comment_id': str(parent) if parent else None,
                        'reply_to_comment_id': str(row.get('replyToCommentId')) if row.get('replyToCommentId') else None,
                        'content': row.get('content') or '', 'author_id': str(row.get('authorId') or ''), 'author_nickname': row.get('authorName') or '',
                        'publish_datetime': self._time(row.get('timestamp')), 'likes': optional_int(row.get('likedCount')),
                        'url': url, 'raw': {'source_observation': row}})
                    inline = row.get('subCommentsV2') if isinstance(row.get('subCommentsV2'), list) else row.get('subComments') if isinstance(row.get('subComments'), list) else []
                    reported = optional_int(row.get('subCommentCountV2')) if 'subCommentCountV2' in row else optional_int(row.get('subCommentCount'))
                    if not (cursor or {}).get('root_id') and reported is not None and reported > len(inline) and cid.isdigit(): pending.append(cid)
                    for child in inline:
                        if not isinstance(child, dict) or not child.get('commentId'): continue
                        comments.append({'platform_comment_id': str(child['commentId']), 'parent_content_id': target, 'parent_comment_id': cid,
                            'reply_to_comment_id': str(child.get('replyToCommentId')) if child.get('replyToCommentId') else None, 'content': child.get('content') or '',
                            'author_id': str(child.get('authorId') or ''), 'author_nickname': child.get('authorName') or '', 'publish_datetime': self._time(child.get('timestamp')),
                            'likes': optional_int(child.get('likedCount')), 'url': url, 'raw': {'source_observation': child}})
            if capability == 'comments':
                if (cursor or {}).get('mode') == 'replies':
                    if next_cursor is None and exhausted is True and cursor['pending_roots']:
                        next_cursor = {**base_cursor, 'root_id': cursor['pending_roots'][0], 'pcursor': '', 'pending_roots': cursor['pending_roots'][1:]}
                    elif next_cursor is None and exhausted is True: next_cursor, exhausted = cursor.get('next_root'), cursor.get('root_exhausted')
                elif kwargs.get('include_replies') and pending:
                    next_cursor = {'mode': 'replies', 'root_id': pending[0], 'pcursor': '', 'pending_roots': pending[1:], 'next_root': next_cursor, 'root_exhausted': exhausted}
                    exhausted = False
            return CollectionResult(CollectionStatus.SUCCESS if items or comments else CollectionStatus.NO_NEW_DATA, self.platform,
                items=items, comments=comments, raw_count=len(items) + len(comments), new_count=len(items) + len(comments), metadata={
                    'provider': 'registered_browser_native_read', 'pagination': {'request_cursor': cursor, 'next_cursor': next_cursor,
                        'exhausted': exhausted, 'page_complete': complete, 'coverage_scope': 'PROVIDER_VISIBLE_NATIVE_PAGE',
                        **{key: window[key] for key in ('window_start', 'window_end', 'observed_native_rows', 'page_sha256', 'page_identity_basis')},
                        'resume_strategy': 'OFFICIAL_PAGE_NATIVE_CURSOR_SEEK', 'observed_prior_native_responses': selected['observed_prior_native_responses'],
                        'reported_total': optional_int(data.get('commentCountV2')), 'partial_reason': 'REQUESTED_LIMIT_REACHED' if not complete else
                            'NATIVE_CURSOR_DID_NOT_ADVANCE' if exhausted is False and next_cursor is None else None}})
        except NativePageWindowError as exc:
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, raw_count=None,
                message='KUAISHOU_' + str(exc), metadata={'provider': 'registered_browser_native_read',
                    'failure_class': str(exc), 'pagination': {'request_cursor': cursor, 'next_cursor': None,
                        'exhausted': None, 'page_complete': False, 'resume_requires_fresh_page': True}})
        except RuntimeError as exc:
            code = str(exc) if re.fullmatch(r'[A-Z_]{1,120}', str(exc)) else 'PROVIDER_UNAVAILABLE'
            return CollectionResult(CollectionStatus.NOT_CONFIGURED if 'NOT_REGISTERED' in code or 'NOT_CONFIGURED' in code else CollectionStatus.PROVIDER_UNAVAILABLE,
                self.platform, raw_count=None, message='KUAISHOU_' + code, metadata={'provider': 'registered_browser_native_read'})
        except Exception as exc:
            return CollectionResult(CollectionStatus.PROVIDER_UNAVAILABLE, self.platform, raw_count=None, message='KUAISHOU_PROVIDER_UNAVAILABLE', metadata={'error_type': type(exc).__name__})
        finally:
            capture.close()
            if page is not None:
                try: page.close()
                except Exception: pass
            if worker is not None: worker.close()


register_adapter("kuaishou", KuaishouAdapter)
