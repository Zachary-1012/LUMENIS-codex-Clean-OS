from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter


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

    def __init__(self, *, engine: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._engine = engine
        self._engine_loaded = engine is not None

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

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
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
        """Local-only health check: cookie file existence + proxy env vars.

        Does NOT start a browser or access the network.
        """
        cookie_path = self.COOKIE_PATH
        if cookie_path == self._DEFAULT_COOKIE_PATH:
            try:
                from lumenis.adapters.cookie_vault import _resolve_path
                cookie_path = _resolve_path("instagram") or cookie_path
            except Exception:
                pass
        cookie_exists = cookie_path.is_file() and cookie_path.stat().st_size > 0
        proxy_configured = bool(self._proxy_configured())

        metadata = {
            "cookie_exists": cookie_exists,
            "proxy_configured": proxy_configured,
            "cookie_path": str(cookie_path),
        }

        if cookie_exists and proxy_configured:
            return CollectionResult(
                status=CollectionStatus.SUCCESS,
                platform=self.platform,
                message="Instagram adapter ready (cookie + proxy configured)",
                metadata=metadata,
            )

        problems = []
        if not cookie_exists:
            problems.append("Instagram cookie file not found")
        if not proxy_configured:
            problems.append("Instagram requires proxy (GOOGLE_PROXY/OPENAI_PROXY not set)")

        status = CollectionStatus.SESSION_EXPIRED if not cookie_exists and proxy_configured else CollectionStatus.COLLECT_ERROR
        return CollectionResult(
            status=status,
            platform=self.platform,
            message="; ".join(problems),
            metadata=metadata,
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
            "likes": item.get("likes", 0),
            "comments": item.get("comments", 0),
            "collects": item.get("collects", 0),
            "shares": item.get("shares", 0),
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
