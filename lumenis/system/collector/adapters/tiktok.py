# -*- coding: utf-8 -*-
"""TikTok native read responses from an explicitly registered browser.

The platform's own page creates its requests. This adapter neither signs them
nor assumes that a configured worker is authenticated or currently usable.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import quote, urlsplit

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .platform_naming import map_raw_to_normalized
from .registry import register_adapter

logger = logging.getLogger(__name__)


class TikTokAdapter(BasePlatformAdapter):
    """Native content/comment/profile pages behind the existing Session owner."""

    platform = "tiktok"
    enabled = False
    monitor_priority = "planned"

    RAW_CONTENT_TABLE = "tiktok_videos"
    RAW_COMMENT_TABLE = "tiktok_comments"
    RAW_USER_TABLE = "tiktok_users"

    def __init__(self, *, browser_factory=None, **kwargs):
        super().__init__(**kwargs)
        self.browser_factory = browser_factory

    @staticmethod
    def _time(value):
        if type(value) in {int, float}:
            try: return datetime.fromtimestamp(value, timezone.utc).isoformat()
            except (ValueError, OSError, OverflowError): pass
        return ''

    @staticmethod
    def _target(value, source_url=None):
        candidate = source_url or value
        if not isinstance(candidate, str): raise ValueError('SOURCE_PERMALINK_REQUIRED')
        parsed = urlsplit(candidate)
        match = re.fullmatch(r'/@([A-Za-z0-9_.]{1,40})/video/([1-9][0-9]{5,29})/?', parsed.path)
        if (parsed.scheme != 'https' or parsed.hostname not in {'www.tiktok.com', 'tiktok.com'}
                or parsed.username or parsed.password or parsed.port not in (None, 443) or not match):
            raise ValueError('SOURCE_PERMALINK_REQUIRED')
        if str(value).isdigit() and str(value) != match[2]: raise ValueError('NATIVE_IDENTITY_MISMATCH')
        return match[2], 'https://www.tiktok.com' + parsed.path.rstrip('/')

    def _item(self, native):
        from lumenis.adapters.base import optional_int
        if not isinstance(native, dict): return None
        vid = native.get('id')
        user = native.get('author') or {}
        username = user.get('uniqueId')
        if not isinstance(vid, str) or not vid.isdigit() or not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9_.]{1,40}', username): return None
        stats = native.get('stats') or native.get('statsV2') or {}
        video, hints = native.get('video') or {}, []
        for key, kind in (('cover', 'video_cover'), ('originCover', 'video_cover'), ('dynamicCover', 'video_cover'), ('playAddr', 'video'), ('downloadAddr', 'video')):
            value = video.get(key)
            if isinstance(value, str):
                parsed = urlsplit(value)
                if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password:
                    hints.append({'kind': kind, 'url': value, 'locator': '$.video.' + key, 'native_media_id': video.get('id'), 'bytes_state': 'NOT_ACQUIRED'})
        for image in (native.get('imagePost') or {}).get('images') or []:
            if not isinstance(image, dict): continue
            for value in (image.get('imageURL') or {}).get('urlList') or []:
                if isinstance(value, str) and value.startswith('https://'):
                    hints.append({'kind': 'image', 'url': value, 'locator': '$.imagePost.images[].imageURL.urlList[]', 'bytes_state': 'NOT_ACQUIRED'})
        return {'platform_content_id': vid, 'title': (native.get('desc') or '')[:100], 'content': native.get('desc') or '',
            'url': f'https://www.tiktok.com/@{username}/video/{vid}', 'author_id': username, 'author_nickname': user.get('nickname') or '',
            'publish_datetime': self._time(int(native['createTime']) if isinstance(native.get('createTime'), str) and native['createTime'].isdigit() else native.get('createTime')),
            'likes': optional_int(stats.get('diggCount')), 'comments': optional_int(stats.get('commentCount')),
            'collects': optional_int(stats.get('collectCount')), 'shares': optional_int(stats.get('shareCount')), 'views': optional_int(stats.get('playCount')),
            'cover': next((v['url'] for v in hints if v['kind'] in {'image', 'video_cover'}), ''),
            'raw': {'engine': 'tiktok_native_page', 'native_user_id': user.get('id'), 'sec_uid': user.get('secUid'), 'username': username,
                'source_observation': native, 'body_state': 'PLATFORM_CAPTION', 'media_hints': hints,
                'native_author_aliases': [{'kind': key, 'value': str(user[key])} for key in ('id', 'uniqueId', 'secUid') if user.get(key)]}}

    def _read(self, capability, target, *, max_results=20, cursor=None, include_replies=False, source_url=None):
        from lumenis.adapters.base import optional_int
        from lumenis.adapters.cookie_vault import inject_into_context
        from lumenis.adapters.human_browser import (HumanBrowser, NativeReadCapture, PageState, configured_readonly_worker_url,
                                                    NativePageWindowError, native_json_nodes, native_page_json,
                                                    native_page_window, native_read_scroll, validate_native_page_window_cursor)
        if type(max_results) is not int or not 1 <= max_results <= 100:
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='TIKTOK_PAGE_SIZE_INVALID')
        if cursor is not None and (not isinstance(cursor, dict) or cursor.get('mode') not in {'search', 'posts', 'roots', 'replies'}
                or not isinstance(cursor.get('cursor'), str) or len(cursor['cursor']) > 4096 or any(ord(c) < 32 for c in cursor['cursor'])):
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='TIKTOK_NATIVE_CURSOR_INVALID')
        if (cursor or {}).get('mode') == 'replies' and (not isinstance(cursor.get('root_id'), str) or not cursor['root_id'].isdigit()
                or not isinstance(cursor.get('pending_roots'), list) or len(cursor['pending_roots']) > 100
                or any(not isinstance(v, str) or not v.isdigit() for v in cursor['pending_roots'])):
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='TIKTOK_NATIVE_CURSOR_INVALID')
        expected_mode = {'search': 'search', 'author_posts': 'posts', 'comments': 'roots'}.get(capability)
        if cursor is not None and (expected_mode is None or cursor['mode'] not in (
                {'roots', 'replies'} if capability == 'comments' else {expected_mode})):
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='TIKTOK_NATIVE_CURSOR_INVALID')
        try:
            validate_native_page_window_cursor(cursor)
            if (cursor or {}).get('mode') == 'replies':
                validate_native_page_window_cursor(cursor.get('next_root'))
        except NativePageWindowError:
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, raw_count=None,
                                    message='TIKTOK_NATIVE_CURSOR_WINDOW_INVALID')
        try:
            if capability in {'detail', 'comments'}:
                native_id, url = self._target(target, source_url)
            elif capability in {'author', 'author_posts'}:
                if not isinstance(target, str) or re.fullmatch(r'[A-Za-z0-9_.]{1,40}', target.lstrip('@')) is None: raise ValueError('AUTHOR_ID_INVALID')
                target = target.lstrip('@')
                url, native_id = 'https://www.tiktok.com/@' + target, None
            else:
                if not isinstance(target, str) or not target.strip(): raise ValueError('QUERY_INVALID')
                url, native_id = 'https://www.tiktok.com/search?q=' + quote(target), None
        except (ValueError, TypeError):
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='TIKTOK_SOURCE_OR_TARGET_INVALID')
        worker, page = None, None
        capture = NativeReadCapture(hosts={'www.tiktok.com', 'm.tiktok.com'},
            paths=('/api/search/', '/api/item/detail', '/api/post/item_list', '/api/user/detail', '/api/comment/list'),
            request_keys={'keyword', 'offset', 'cursor', 'secUid', 'uniqueId', 'itemId', 'item_id', 'aweme_id', 'comment_id', 'search_id', 'count'})
        try:
            worker = self.browser_factory() if self.browser_factory else HumanBrowser(cdp_url=configured_readonly_worker_url('tiktok'), auto_ensure=False, launch_url='about:blank')
            worker.connect()
            inject_into_context(worker._context, 'tiktok')
            page = worker.new_page(stealth=False)
            capture.attach(page)
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(900)
            users = {}
            def profile(objects):
                for obj in objects:
                    for node in native_json_nodes(obj):
                        user_info = node.get('userInfo')
                        if isinstance(user_info, dict):
                            user = user_info.get('user') or {}
                            if user.get('uniqueId') == target and user.get('secUid'): users[user['secUid']] = user_info
            ssr = list(native_page_json(page))
            profile(ssr)
            def select(observation):
                request = observation['request']
                profile(observation['objects'])
                if capability == 'author' and users: return {'profile': next(iter(users.values()))}
                field = 'offset' if capability == 'search' else 'cursor'
                if str(request.get(field) or '0') != str((cursor or {}).get('cursor') or '0'): return None
                if capability == 'search' and request.get('keyword') != target: return None
                if capability == 'author_posts' and request.get('secUid') not in users: return None
                if capability in {'comments', 'detail'} and str(request.get('aweme_id') or request.get('item_id') or request.get('itemId') or '') != native_id: return None
                reply_root = (cursor or {}).get('root_id')
                if capability == 'comments' and (bool(reply_root) != ('/reply' in observation['path']) or reply_root and request.get('comment_id') != reply_root): return None
                for obj in observation['objects']:
                    if not isinstance(obj, dict): continue
                    status = obj.get('statusCode', obj.get('status_code'))
                    if status not in (0, None): observation['failure_class'] = 'PROVIDER_REJECTED'; return None
                    if capability == 'detail':
                        item = (obj.get('itemInfo') or {}).get('itemStruct') or obj.get('itemStruct')
                        if isinstance(item, dict) and item.get('id') == native_id: return {'body': obj, 'rows': [item]}
                    rows = obj.get('comments') if capability == 'comments' else obj.get('itemList') if 'itemList' in obj else obj.get('item_list')
                    if capability == 'search' and rows is None and isinstance(obj.get('data'), list):
                        rows = [row.get('item') for row in obj['data'] if isinstance(row, dict) and isinstance(row.get('item'), dict)]
                    if isinstance(rows, list): return {'body': obj, 'rows': rows}
                return None
            def advance(_step):
                state = worker.detect_state(page)
                if state in {PageState.AUTH_FAILED, PageState.BLOCKED, PageState.CAPTCHA, PageState.NETWORK_ERROR}: return False
                return native_read_scroll(page, reply_id=(cursor or {}).get('root_id'), reply_attribute='data-comment-id')
            selected = None
            if capability == 'detail':
                for obj in ssr:
                    for node in native_json_nodes(obj):
                        item = (node.get('itemInfo') or {}).get('itemStruct') if isinstance(node.get('itemInfo'), dict) else None
                        if isinstance(item, dict) and item.get('id') == native_id: selected = {'body': {}, 'rows': [item], 'observed_prior_native_responses': 0}
            if capability == 'author' and users: selected = {'profile': next(iter(users.values())), 'observed_prior_native_responses': 0}
            selected = selected or capture.seek(page, select, advance, max_steps=16)
            if selected is None:
                failure = capture.failure() or {}
                state = worker.detect_state(page)
                code = failure.get('failure_class') or {PageState.AUTH_FAILED: 'AUTH_REQUIRED', PageState.CAPTCHA: 'VERIFICATION_REQUIRED', PageState.BLOCKED: 'ACCESS_BLOCKED'}.get(state, 'NATIVE_PAGE_NOT_OBSERVED')
                status = {'AUTH_REQUIRED': CollectionStatus.SESSION_EXPIRED, 'VERIFICATION_REQUIRED': CollectionStatus.NEED_VERIFY,
                          'ACCESS_BLOCKED': CollectionStatus.BLOCKED, 'RATE_LIMITED': CollectionStatus.COOLING_DOWN}.get(code, CollectionStatus.PROVIDER_UNAVAILABLE)
                return CollectionResult(status, self.platform, raw_count=None, message='TIKTOK_' + code, metadata={
                    'provider': 'registered_browser_native_read', 'failure_class': code, 'http_status': failure.get('http_status'),
                    'retry_after_seconds': failure.get('retry_after_seconds'), 'pagination': {'request_cursor': cursor, 'next_cursor': None, 'exhausted': None, 'page_complete': False}})
            if capability == 'author':
                info = selected['profile']; user, stats = info['user'], info.get('stats') or {}
                item = {'platform_content_id': user['uniqueId'], 'title': user.get('nickname') or '', 'content': user.get('signature') or '',
                    'author_id': user['uniqueId'], 'author_nickname': user.get('nickname') or '', 'url': url,
                    'likes': None, 'comments': None, 'collects': None, 'shares': None,
                    'raw': {'username': user['uniqueId'], 'native_user_id': user.get('id'), 'sec_uid': user['secUid'],
                        'followers': optional_int(stats.get('followerCount')), 'following_count': optional_int(stats.get('followingCount')),
                        'content_count': optional_int(stats.get('videoCount')), 'received_likes_count': optional_int(stats.get('heartCount')),
                        'source_observation': info, 'native_author_aliases': [{'kind': k, 'value': str(user[k])} for k in ('id', 'uniqueId', 'secUid') if user.get(k)]}}
                return CollectionResult(CollectionStatus.SUCCESS, self.platform, items=[item], raw_count=1, new_count=1, metadata={'provider': 'registered_browser_native_read'})
            body, rows = selected['body'], selected['rows']; items, comments, pending = [], [], []
            window = native_page_window(rows, limit=max_results, cursor=cursor, identities=[
                str(row.get('cid') if capability == 'comments' else row.get('id'))
                if isinstance(row, dict) else None for row in rows])
            complete = window['page_complete']
            more = body.get('hasMore', body.get('has_more'))
            more = bool(more) if type(more) in {bool, int} and more in (0, 1) else None
            next_value = body.get('offset' if capability == 'search' else 'cursor')
            next_value = str(next_value) if type(next_value) is int or isinstance(next_value, str) else None
            base_cursor = {key: value for key, value in (cursor or {}).items()
                           if key not in {'item_offset', 'page_sha256'}}
            base_cursor.setdefault('mode', expected_mode or 'roots')
            base_cursor.setdefault('cursor', '0')
            next_cursor = ({**base_cursor, **window['next_window']} if not complete else
                           {**base_cursor, 'cursor': next_value} if more and next_value
                           and next_value != base_cursor['cursor'] else None)
            exhausted = not more if more is not None and complete else None
            if not complete:
                exhausted = False
            if capability != 'comments':
                for row in window['rows']:
                    item = self._item(row)
                    if item is None: continue
                    if capability == 'author_posts' and item['author_id'] != target:
                        return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='TIKTOK_AUTHOR_HISTORY_IDENTITY_MISMATCH')
                    if capability == 'author_posts': item['raw']['author_history_binding'] = {'requested_id': target, 'sec_uid': item['raw']['sec_uid']}
                    items.append(item)
                if capability == 'detail' and len(items) != 1:
                    return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='TIKTOK_DETAIL_IDENTITY_UNVERIFIED')
            else:
                flattened = []
                for row in window['rows']:
                    if not isinstance(row, dict): continue
                    inline = row.get('reply_comment') if isinstance(row.get('reply_comment'), list) else []
                    flattened.append((row, (cursor or {}).get('root_id')))
                    flattened.extend((child, str(row.get('cid'))) for child in inline if isinstance(child, dict))
                    count = optional_int(row.get('reply_comment_total'))
                    if count is not None and count > len(inline) and str(row.get('cid') or '').isdigit(): pending.append(str(row['cid']))
                seen = set()
                for row, parent in flattened:
                    cid = str(row.get('cid') or ''); user = row.get('user') or {}
                    if not cid.isdigit() or cid in seen: continue
                    seen.add(cid)
                    if row.get('aweme_id') is not None and str(row['aweme_id']) != native_id:
                        return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, message='TIKTOK_COMMENT_PARENT_MISMATCH')
                    comments.append({'platform_comment_id': cid, 'parent_content_id': native_id, 'parent_comment_id': parent,
                        'reply_to_comment_id': row.get('reply_to_reply_id'), 'content': row.get('text') or '', 'author_id': user.get('uid') or user.get('id') or '',
                        'author_nickname': user.get('nickname') or '', 'publish_datetime': self._time(row.get('create_time')), 'likes': optional_int(row.get('digg_count')),
                        'url': url + '?comment_id=' + cid, 'raw': {'source_observation': row}})
                if (cursor or {}).get('mode') == 'replies':
                    if next_cursor is None and exhausted is True and cursor.get('pending_roots'):
                        next_cursor = {**base_cursor, 'root_id': cursor['pending_roots'][0], 'cursor': '0', 'pending_roots': cursor['pending_roots'][1:]}
                    elif next_cursor is None and exhausted is True: next_cursor, exhausted = cursor.get('next_root'), cursor.get('root_exhausted')
                elif include_replies and pending:
                    next_cursor = {'mode': 'replies', 'root_id': pending[0], 'cursor': '0', 'pending_roots': pending[1:], 'next_root': next_cursor, 'root_exhausted': exhausted}; exhausted = False
            return CollectionResult(CollectionStatus.SUCCESS if items or comments else CollectionStatus.NO_NEW_DATA, self.platform,
                items=items, comments=comments, raw_count=len(items) + len(comments), new_count=len(items) + len(comments), metadata={
                    'provider': 'registered_browser_native_read', 'pagination': {'request_cursor': cursor, 'next_cursor': next_cursor,
                        'exhausted': exhausted, 'page_complete': complete, 'coverage_scope': 'PROVIDER_VISIBLE_NATIVE_PAGE',
                        **{key: window[key] for key in ('window_start', 'window_end', 'observed_native_rows', 'page_sha256', 'page_identity_basis')},
                        'resume_strategy': 'OFFICIAL_PAGE_NATIVE_CURSOR_SEEK', 'observed_prior_native_responses': selected['observed_prior_native_responses'],
                        'partial_reason': 'REQUESTED_LIMIT_REACHED' if not complete else
                            'NATIVE_CURSOR_DID_NOT_ADVANCE' if more and next_cursor is None else None}})
        except NativePageWindowError as exc:
            return CollectionResult(CollectionStatus.COLLECT_ERROR, self.platform, raw_count=None,
                message='TIKTOK_' + str(exc), metadata={'provider': 'registered_browser_native_read',
                    'failure_class': str(exc), 'pagination': {'request_cursor': cursor, 'next_cursor': None,
                        'exhausted': None, 'page_complete': False, 'resume_requires_fresh_page': True}})
        except RuntimeError as exc:
            code = str(exc)
            known = code if re.fullmatch(r'[A-Z_]{1,120}', code) else 'PROVIDER_UNAVAILABLE'
            return CollectionResult(CollectionStatus.NOT_CONFIGURED if 'NOT_REGISTERED' in known or 'NOT_CONFIGURED' in known else CollectionStatus.PROVIDER_UNAVAILABLE,
                self.platform, raw_count=None, message='TIKTOK_' + known, metadata={'provider': 'registered_browser_native_read', 'failure_class': known})
        except Exception as exc:
            return CollectionResult(CollectionStatus.PROVIDER_UNAVAILABLE, self.platform, raw_count=None, message='TIKTOK_PROVIDER_UNAVAILABLE', metadata={'error_type': type(exc).__name__})
        finally:
            capture.close()
            if page is not None:
                try: page.close()
                except Exception: pass
            if worker is not None: worker.close()

    def normalize_to_platform_contents(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return map_raw_to_normalized(raw_record, "tiktok")

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        return self._read('search', keyword, max_results=kwargs.get('max_results', 20), cursor=kwargs.get('cursor'))

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._read('detail', content_id, max_results=1, source_url=kwargs.get('source_url'))

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return self._read('comments', content_id, max_results=kwargs.get('max_comments', 20), cursor=kwargs.get('cursor'), include_replies=include_replies, source_url=kwargs.get('source_url'))

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return self._read('author', creator_id, max_results=1)

    def author_posts(self, author_id: str, **kwargs: Any) -> CollectionResult:
        return self._read('author_posts', author_id, max_results=kwargs.get('max_results', 20), cursor=kwargs.get('cursor'))

    def health_check(self, **_: Any) -> CollectionResult:
        from lumenis.adapters.human_browser import readonly_worker_health
        try: health = readonly_worker_health(self.platform)
        except RuntimeError: return CollectionResult(CollectionStatus.NOT_CONFIGURED, self.platform, message='TIKTOK_READONLY_WORKER_NOT_REGISTERED')
        return CollectionResult(CollectionStatus(health['status']), self.platform, message='TikTok注册只读会话状态；实际读取仍需验证', metadata=health['metadata'])


register_adapter("tiktok", TikTokAdapter)
