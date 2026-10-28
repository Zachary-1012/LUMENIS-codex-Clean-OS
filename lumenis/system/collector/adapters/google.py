"""SYSTEM bridge to the existing registered Google discovery adapter."""
from __future__ import annotations

import hashlib
from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter


class GoogleAdapter(BasePlatformAdapter):
    platform = 'google'
    enabled = False
    monitor_priority = 'discovery'

    def __init__(self, *, backend=None, **kwargs):
        super().__init__(**kwargs)
        self.backend = backend

    def search(self, keyword, **kwargs):
        try:
            if self.backend is None:
                from lumenis.adapters.google import GoogleAdapter as Engine
                self.backend = Engine()
            options = {'max_results': kwargs.get('max_results', 10)}
            if kwargs.get('cursor') is not None: options['cursor'] = kwargs['cursor']
            result = self.backend.search(keyword, **options)
            items = []
            for note in result.notes:
                if not isinstance(note.url, str) or not note.url.startswith(('https://', 'http://')): continue
                items.append({'platform_content_id': 'google-url:' + hashlib.sha256(note.url.encode('utf-8')).hexdigest(),
                    'title': note.title, 'content': note.content, 'url': note.url, 'author_id': '',
                    'author_nickname': '', 'publish_datetime': '',
                    'likes': None, 'comments': None, 'collects': None, 'shares': None,
                    'raw': {**(note.raw_data or {}), 'body_state': 'FEED_OR_INDEX_EXCERPT', 'body_kind': 'search_snippet',
                            'original_body_available': False, 'discovery_assistance': 'REGISTERED_GOOGLE_READONLY_BROWSER',
                            'discovery_provider': 'Google', 'publication_time_state': 'NOT_OBSERVED'}})
            error = result.error or ''
            status = CollectionStatus.SUCCESS if result.success and items else CollectionStatus.NO_NEW_DATA if result.success else (
                CollectionStatus.NEED_VERIFY if 'CAPTCHA' in error or 'VERIFY' in error else
                CollectionStatus.BLOCKED if 'BLOCKED' in error else CollectionStatus.SESSION_EXPIRED if 'AUTH' in error else
                CollectionStatus.NOT_CONFIGURED if 'NOT_REGISTERED' in error or 'NOT_CONFIGURED' in error else CollectionStatus.PROVIDER_UNAVAILABLE)
            return CollectionResult(status, self.platform, items=items, raw_count=result.raw_count if result.success else None,
                new_count=len(items), message=error, metadata={**(result.metadata or {}),
                    'provider': 'registered_google_discovery', 'original_body_available': False, 'content_semantics': 'SEARCH_SNIPPET_NOT_ORIGINAL'})
        except Exception as exc:
            return CollectionResult(CollectionStatus.PROVIDER_UNAVAILABLE, self.platform, raw_count=None,
                message='GOOGLE_PROVIDER_UNAVAILABLE', metadata={'error_type': type(exc).__name__})

    def detail(self, content_id, **kwargs):
        return CollectionResult(CollectionStatus.NOT_SUPPORTED, self.platform,
            message='Google提供发现摘要；原文须由原Source URL在其获准来源能力读取',
            metadata={'capability': 'detail', 'reason': 'DISCOVERY_PROVIDER_HAS_NO_ORIGINAL_BODY'})

    def health_check(self, **kwargs):
        from lumenis.adapters.human_browser import registered_browser_worker_spec
        try:
            worker = registered_browser_worker_spec('google')
            import cdp_helper
            registered = cdp_helper.registered_cdp_browser_for_port(worker['port'], worker['profile'], headless=True)
            return CollectionResult(CollectionStatus.NEED_VERIFY if registered else CollectionStatus.PROVIDER_UNAVAILABLE, self.platform,
                message='Google注册后台浏览器状态；搜索访问仍需实际验证', metadata={'provider': 'registered_google_discovery', 'source_access_verified': False})
        except RuntimeError:
            return CollectionResult(CollectionStatus.NOT_CONFIGURED, self.platform, message='GOOGLE_READONLY_WORKER_NOT_REGISTERED')


register_adapter('google', GoogleAdapter)
