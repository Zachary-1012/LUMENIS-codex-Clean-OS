from __future__ import annotations

import os
import re
import json
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlsplit
from pathlib import Path
from typing import Any, Dict, List, Optional

from lumenis.adapters.base import optional_int

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter
from .public_source import fetch_public_url, public_source_provenance
from .routing import resolve_capability_route


def parse_public_instagram_document(response, shortcode):
    """Inspect only the matching public post, keeping media/caption times distinct."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    matches = []
    def visit(value, locator):
        if isinstance(value, dict):
            if value.get('code') == shortcode and value.get('pk') and isinstance(value.get('if_not_gated_logged_out'), dict):
                matches.append((locator, value))
            for key, child in value.items():
                visit(child, locator + '/' + str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, locator + '/' + str(index))
    for index, script in enumerate(soup.find_all('script')):
        try:
            visit(json.loads(script.get_text()), f'script[{index}]')
        except (ValueError, TypeError):
            continue
    if len(matches) != 1:
        return None
    locator, media = matches[0]
    public = media['if_not_gated_logged_out']
    if str(public.get('pk')) != str(media['pk']) or public.get('code') != shortcode:
        return None
    caption = public.get('caption') or {}
    text = caption.get('text')
    if not isinstance(text, str) or not text.strip():
        return None
    user = public.get('user') or {}
    published = None
    taken_at = public.get('taken_at')
    if isinstance(taken_at, (int, float)) and not isinstance(taken_at, bool):
        try:
            published = datetime.fromtimestamp(taken_at, timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            pass
    def metric(key):
        value = public.get(key)
        return value if type(value) is int and value >= 0 else None
    comments = []
    for edge in (media.get('comments_connection') or {}).get('edges') or []:
        node = edge.get('node') or {}
        # Copy the public comment fields, never the surrounding viewer or tracking context.
        comment = {key: node[key] for key in ('pk', 'id', 'text', 'created_at', 'like_count') if key in node}
        comment_user = node.get('user')
        if isinstance(comment_user, dict):
            comment['user'] = {key: comment_user[key] for key in
                               ('pk', 'id', 'username', 'full_name', 'is_verified', 'profile_pic_url')
                               if key in comment_user}
        comments.append(comment)
    public_user = {key: user[key] for key in ('pk', 'username', 'full_name', 'is_verified') if key in user}
    raw = {'media_id': str(media['pk']), 'shortcode': shortcode, 'taken_at': taken_at,
           'caption': text, 'caption_created_at': caption.get('created_at'),
           'caption_is_edited': public.get('caption_is_edited'), 'author_id': str(user.get('pk')) if user.get('pk') else None,
           'author': public_user, 'like_count': metric('like_count'), 'comment_count': metric('comment_count'),
           'share_count': None, 'play_count': None, 'location': public.get('location'),
           'media_type': public.get('media_type'), 'display_uri': public.get('display_uri'),
           'video_versions': [{key: value[key] for key in ('type', 'url', 'width', 'height') if key in value}
                              for value in public.get('video_versions') or []],
           'public_comments': comments, 'comment_page_info': (media.get('comments_connection') or {}).get('page_info'),
           'native_document_sha256': hashlib.sha256(response.content).hexdigest(),
           'native_post_locator': locator, 'native_caption_locator': locator + '/if_not_gated_logged_out/caption/text',
           'native_time_locator': locator + '/if_not_gated_logged_out/taken_at',
           'native_hashtags': re.findall(r'#([^\s#]+)', text)}
    return {'platform': 'instagram', 'platform_content_id': str(media['pk']), 'url': response.url,
            'content': text, 'title': None, 'publish_datetime': published,
            'author_id': raw['author_id'], 'author_nickname': user.get('username'),
            'likes': raw['like_count'], 'comments': raw['comment_count'], 'collects': None,
            'shares': None, 'views': None, 'raw': raw}


class InstagramAdapter(BasePlatformAdapter):
    """Thin boundary layer around the v4 Instagram engine.

    Delegates all real collection to lumenis.adapters.instagram.InstagramAdapter.
    This layer only maps v4 AdapterResult -> CollectionResult and normalizes fields.
    No subject filtering, risk scoring, or business logic lives here.

    Default disabled: requires proxy + cookie. Enable at runtime after health_check
    confirms both are configured.
    """

    platform = "instagram"
    enabled = False
    monitor_priority = "secondary"

    # Compatibility override for tests/diagnostics.  The default is resolved
    # from the shared Cookie Vault at runtime, beside the canonical DB.
    COOKIE_PATH = Path(__file__).resolve().parents[1] / "data" / "cookies" / "instagram.json"
    _DEFAULT_COOKIE_PATH = COOKIE_PATH

    def __init__(self, *, engine: Any = None, public_fetcher: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._engine = engine
        self._engine_loaded = engine is not None
        self._public_fetcher = public_fetcher or fetch_public_url

    # ------------------------------------------------------------------
    # Engine lazy-load
    # ------------------------------------------------------------------
    def _get_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        from lumenis.adapters.instagram import InstagramAdapter as V4Engine
        self._engine = V4Engine()
        self._engine_loaded = True
        return self._engine

    # ------------------------------------------------------------------
    # Status mapping: v4 AdapterResult -> CollectionStatus
    # ------------------------------------------------------------------
    @staticmethod
    def _map_status(success: bool, notes: list, error: str) -> CollectionStatus:
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err = (error or "").lower()
        if "instagram_worker_not_registered" in err:
            return CollectionStatus.NOT_CONFIGURED
        if "登录态失效" in error or "session" in err and "expire" in err:
            return CollectionStatus.SESSION_EXPIRED
        if any(k in error for k in ("验证", "captcha", "人机")) or "captcha" in err:
            return CollectionStatus.NEED_VERIFY
        if any(k in error for k in ("频控", "风控", "try again later")):
            return CollectionStatus.BLOCKED
        if "代理" in error or "proxy" in err:
            return CollectionStatus.COLLECT_ERROR
        return CollectionStatus.COLLECT_ERROR

    # ------------------------------------------------------------------
    # v4 CollectedNote -> normalized item dict
    # ------------------------------------------------------------------
    def _notes_to_items(self, notes: list) -> List[Dict[str, Any]]:
        items = []
        for note in notes:
            note_dict = note.__dict__ if hasattr(note, "__dict__") else dict(note)
            items.append(self.normalize_item(note_dict))
        return items

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        route = resolve_capability_route("instagram", "search", request_value=keyword)
        if route is None:
            return CollectionResult(
                CollectionStatus.NOT_SUPPORTED, self.platform,
                message="当前输入不匹配已实现的 Instagram 搜索/公开帖子路径",
                metadata={"route_state": "UNKNOWN"},
            )
        if route.backend == "public_native_post_document":
            return self._public_detail(keyword)
        try:
            engine = self._get_engine()
            result = engine.search(keyword, max_results=kwargs.get("max_results", 20))
            items = self._notes_to_items(result.notes)
            status = self._map_status(result.success, result.notes, result.error)
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=items,
                raw_count=result.raw_count,
                new_count=len(items),
                message=result.error or "",
                metadata={
                    "engine": "v4_instagram",
                    "proxy_configured": bool(self._proxy_configured()),
                },
            )
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=str(exc),
            )

    def _public_detail(self, url):
        raw_url = str(url or "").strip()
        try:
            parts = urlsplit(raw_url)
            port = parts.port
        except (TypeError, ValueError) as exc:
            raise ValueError('exact public Instagram post URL required') from exc
        match = re.fullmatch(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)/?', parts.path)
        if (parts.scheme.lower() != 'https'
                or parts.hostname not in {'instagram.com', 'www.instagram.com'}
                or port not in (None, 443)
                or parts.username or parts.password or not match):
            raise ValueError('exact public Instagram post URL required')
        try:
            response = self._public_fetcher(raw_url)
            if urlsplit(response.url).hostname not in {'instagram.com', 'www.instagram.com'}:
                return CollectionResult(CollectionStatus.BLOCKED, self.platform, metadata={'original_body_available': False})
            item = parse_public_instagram_document(response, match.group(1))
            return CollectionResult(CollectionStatus.SUCCESS if item else CollectionStatus.PROVIDER_UNAVAILABLE,
                self.platform, items=[item] if item else [], raw_count=1 if item else 0,
                metadata={**public_source_provenance(response, raw_url), 'provider': 'public_native_post_document',
                          'original_body_available': item is not None, 'requires_auth': False})
        except Exception as exc:
            return CollectionResult(CollectionStatus.PROVIDER_UNAVAILABLE, self.platform,
                                    metadata={'error_type': type(exc).__name__, 'original_body_available': False})

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        route = resolve_capability_route("instagram", "detail", request_value=content_id)
        if route is None:
            return CollectionResult(
                CollectionStatus.NOT_SUPPORTED, self.platform,
                message="当前输入不匹配已实现的 Instagram 详情路径",
                metadata={"route_state": "UNKNOWN"},
            )
        if route.backend == "public_native_post_document":
            return self._public_detail(content_id)
        try:
            engine = self._get_engine()
            media_type = kwargs.get("media_type", "post")
            result = engine.detail(content_id, media_type=media_type)
            items = self._notes_to_items(result.notes)
            status = self._map_status(result.success, result.notes, result.error)
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=items,
                raw_count=result.raw_count,
                new_count=len(items),
                message=result.error or "",
                metadata={
                    "engine": "v4_instagram",
                    "shortcode": content_id,
                    "proxy_configured": bool(self._proxy_configured()),
                },
            )
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=str(exc),
            )

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        route = resolve_capability_route("instagram", "comments", request_value=content_id)
        if route is None:
            return CollectionResult(
                CollectionStatus.NOT_SUPPORTED, self.platform,
                message="当前输入不匹配已实现的 Instagram 评论路径",
                metadata={"route_state": "UNKNOWN"},
            )
        try:
            engine = self._get_engine()
            result = engine.comments(content_id, max_comments=kwargs.get("max_comments", 20))
            # v4 stores comments in notes[0].raw_data["comments"]
            comments_list: List[Dict[str, Any]] = []
            if result.notes:
                raw = result.notes[0].raw_data or {}
                comments_list = list(raw.get("comments", []))
            status = self._map_status(result.success, result.notes, result.error)
            # If v4 returned success but no comments, that's NO_NEW_DATA for comments
            if status == CollectionStatus.SUCCESS and not comments_list:
                status = CollectionStatus.NO_NEW_DATA
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=[],
                comments=comments_list,
                raw_count=result.raw_count,
                new_count=len(comments_list),
                message=result.error or "",
                metadata={
                    "engine": "v4_instagram",
                    "shortcode": content_id,
                    "include_replies": include_replies,
                },
            )
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=str(exc),
            )

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        route = resolve_capability_route("instagram", "creator", request_value=creator_id)
        if route is None:
            return CollectionResult(
                CollectionStatus.NOT_SUPPORTED, self.platform,
                message="当前输入不匹配已实现的 Instagram 作者路径",
                metadata={"route_state": "UNKNOWN"},
            )
        try:
            engine = self._get_engine()
            result = engine.creator(creator_id)
            items = self._notes_to_items(result.notes)
            status = self._map_status(result.success, result.notes, result.error)
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=items,
                raw_count=result.raw_count,
                new_count=len(items),
                message=result.error or "",
                metadata={
                    "engine": "v4_instagram",
                    "username": creator_id,
                },
            )
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=str(exc),
            )

    def health_check(self, **kwargs: Any) -> CollectionResult:
        """Report public-read or registered-worker readiness without reading credentials.

        Cookie/proxy file presence cannot prove a registered permitted worker,
        authentication, acquisition access or readiness. No browser is touched.
        """
        route = resolve_capability_route(
            "instagram", "detail", request_value=kwargs.get("url"),
        )
        if route is not None and route.backend == "public_native_post_document":
            return CollectionResult(CollectionStatus.NEED_VERIFY, self.platform,
                metadata={'provider': 'public_native_post_document', 'requires_auth': False,
                          'healthcheck_scope': 'public_document_requires_actual_read'})
        return CollectionResult(
            status=CollectionStatus.NOT_CONFIGURED,
            platform=self.platform,
            message="INSTAGRAM_WORKER_NOT_REGISTERED: Instagram采集入口尚未就绪",
            metadata={"availability": "UNAVAILABLE", "worker_binding_registered": False,
                      "login_and_collection_verified": False, "legacy_cookie_checked": False},
        )

    # ------------------------------------------------------------------
    # Field normalization
    # ------------------------------------------------------------------
    def normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Map v4 CollectedNote fields to main-chain normalized item fields."""
        raw_data = item.get("raw_data") or {}
        # platform_content_id: prefer raw_data.shortcode, fallback to extracting from URL
        shortcode = raw_data.get("shortcode", "")
        if not shortcode:
            url = item.get("url", "")
            m = re.search(r"/(?:p|reel|reels)/([A-Za-z0-9_\-]+)", url)
            shortcode = m.group(1) if m else ""

        return {
            "source_platform": self.platform,
            "platform_content_id": str(shortcode),
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "author_id": item.get("author_id", ""),
            "author_nickname": item.get("author", ""),
            "publish_datetime": item.get("publish_date", ""),
            "url": item.get("url", ""),
            "likes": optional_int(item.get("likes")),
            "comments": optional_int(item.get("comments")),
            "collects": optional_int(item.get("collects")),
            "shares": optional_int(item.get("shares")),
            "captured_at": item.get("captured_at"),
            "raw": raw_data,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _proxy_configured() -> str:
        return (os.environ.get("GOOGLE_PROXY") or os.environ.get("OPENAI_PROXY") or "").strip()


register_adapter("instagram", InstagramAdapter)
