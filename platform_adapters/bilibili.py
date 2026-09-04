from __future__ import annotations

import logging
from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter

logger = logging.getLogger(__name__)


class BilibiliAdapter(BasePlatformAdapter):
    """B站主链路适配器（薄封装 v4 BilibiliAdapter 引擎）。

    v4 引擎薄封装 bilibili_login_manager.search_videos（API+cookie），
    本适配器负责 v4 AdapterResult → 主链路 CollectionResult 映射。
    detail/comments/creator 待 v4 引擎补全后接入。
    """

    platform = "bilibili"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _load_backend(self):
        if self.backend is not None:
            return self.backend
        try:
            from v4_upgrade.adapters.bilibili import BilibiliAdapter as V4BilibiliAdapter
            return V4BilibiliAdapter()
        except Exception as exc:
            raise RuntimeError(f"无法加载 v4 B站采集引擎: {exc}") from exc

    @staticmethod
    def _v4_status_to_main(success: bool, notes: list, error: str) -> CollectionStatus:
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err_lower = (error or "").lower()
        if any(k in err_lower for k in ("登录", "login", "cookie", "session", "失效", "未登录")):
            return CollectionStatus.SESSION_EXPIRED
        if any(k in err_lower for k in ("风控", "验证", "captcha", "verify", "risk", "频控", "rate", "wbi")):
            return CollectionStatus.RISK_WARNING
        if any(k in err_lower for k in ("block", "封禁", "不可用", "412")):
            return CollectionStatus.BLOCKED
        if any(k in err_lower for k in ("冷却", "cooling", "cooldown")):
            return CollectionStatus.COOLING_DOWN
        return CollectionStatus.COLLECT_ERROR

    def _v4_notes_to_items(self, notes: list) -> list[dict]:
        items = []
        for n in notes or []:
            raw = getattr(n, "raw_data", {}) or {}
            items.append(self.normalize_item({
                "platform_content_id": raw.get("bvid", "") if isinstance(raw, dict) else "",
                "title": getattr(n, "title", ""),
                "content": getattr(n, "content", ""),
                "author_id": getattr(n, "author_id", ""),
                "author_nickname": getattr(n, "author", ""),
                "publish_datetime": getattr(n, "publish_date", ""),
                "url": getattr(n, "url", ""),
                "likes": getattr(n, "likes", 0),
                "comments": getattr(n, "comments", 0),
                "collects": getattr(n, "collects", 0),
                "shares": getattr(n, "shares", 0),
                "raw": raw,
            }))
        return items

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        try:
            backend = self._load_backend()
            max_results = int(kwargs.get("max_results", 20))
            result = backend.search(keyword, max_results=max_results)
            status = self._v4_status_to_main(result.success, result.notes, result.error)
            items = self._v4_notes_to_items(result.notes)
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=items,
                raw_count=result.raw_count,
                new_count=len(items),
                message=result.error or "",
                metadata={"engine": "v4_bilibili_api", "duration_s": result.duration_seconds},
            )
        except Exception as exc:
            logger.exception("B站主链路采集异常")
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=str(exc),
            )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="B站 detail 待 v4 引擎补全后接入",
            metadata={"content_id": content_id},
        )

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="B站 comments 待 v4 引擎补全后接入",
            metadata={"content_id": content_id},
        )

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="B站 creator 待 v4 引擎补全后接入",
            metadata={"creator_id": creator_id},
        )

    def health_check(self, **kwargs: Any) -> CollectionResult:
        import os
        cookie_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "bilibili_cookies.json",
        )
        cookie_exists = os.path.exists(cookie_path)
        try:
            backend = self._load_backend()
            engine_ok = backend is not None
        except Exception:
            engine_ok = False
        if cookie_exists and engine_ok:
            return CollectionResult(
                status=CollectionStatus.SUCCESS,
                platform=self.platform,
                message="B站引擎就绪，cookie 存在",
                metadata={"cookie_exists": True, "engine_ok": True},
            )
        return CollectionResult(
            status=CollectionStatus.SESSION_EXPIRED if not cookie_exists else CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message=f"B站未就绪: cookie_exists={cookie_exists}, engine_ok={engine_ok}",
            metadata={"cookie_exists": cookie_exists, "engine_ok": engine_ok},
        )


register_adapter("bilibili", BilibiliAdapter)
