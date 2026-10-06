from __future__ import annotations

import logging
from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter

logger = logging.getLogger(__name__)


class FacebookAdapter(BasePlatformAdapter):
    """Facebook 主链路适配器（薄封装 v4 FacebookAdapter 引擎）。

    v4 引擎使用浏览器 CDP + cookie_vault 采集 Facebook 搜索结果，
    本适配器负责 v4 AdapterResult → 主链路 CollectionResult 映射。
    """

    platform = "facebook"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _load_backend(self):
        if self.backend is not None:
            return self.backend
        try:
            from lumenis.adapters.facebook import FacebookAdapter as V4FacebookAdapter
            return V4FacebookAdapter()
        except Exception as exc:
            raise RuntimeError(f"无法加载 v4 Facebook 采集引擎: {exc}") from exc

    @staticmethod
    def _v4_status_to_main(success: bool, notes: list, error: str) -> CollectionStatus:
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err_lower = (error or "").lower()
        if any(k in err_lower for k in ("登录", "login", "cookie", "session", "失效", "未登录")):
            return CollectionStatus.SESSION_EXPIRED
        if any(k in err_lower for k in ("风控", "验证", "captcha", "verify", "risk", "频控")):
            return CollectionStatus.RISK_WARNING
        if any(k in err_lower for k in ("block", "封禁", "不可用")):
            return CollectionStatus.BLOCKED
        return CollectionStatus.COLLECT_ERROR

    def _v4_notes_to_items(self, notes: list) -> list[dict]:
        items = []
        for n in notes or []:
            raw = getattr(n, "raw_data", {}) or {}
            items.append(self.normalize_item({
                "platform_content_id": raw.get("post_id", "") if isinstance(raw, dict) else "",
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
                message=result.error or "",
            )
        except Exception as exc:
            logger.exception("Facebook 主链路采集失败")
            return CollectionResult(status=CollectionStatus.COLLECT_ERROR, platform=self.platform, message=str(exc))

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("detail", content_id)

    def comments(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("comments", content_id, max_comments=kwargs.get("max_comments", 20))

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("creator", creator_id)

    def _delegate_v4(self, method: str, *args, **kwargs) -> CollectionResult:
        try:
            backend = self._load_backend()
            result = getattr(backend, method)(*args, **kwargs)
            status = self._v4_status_to_main(result.success, result.notes, result.error)
            items = self._v4_notes_to_items(result.notes)
            return CollectionResult(status=status, platform=self.platform, items=items,
                                    raw_count=result.raw_count, message=result.error or "")
        except Exception as exc:
            return CollectionResult(status=CollectionStatus.COLLECT_ERROR, platform=self.platform, message=str(exc))

    def health_check(self) -> CollectionResult:
        """Inspect non-secret auth metadata without claiming a live session."""
        from lumenis.adapters.cookie_vault import check_cookie_status

        try:
            status = check_cookie_status(self.platform)
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=f"Facebook auth metadata unavailable: {type(exc).__name__}",
            )
        if status.get("has_auth_cookie") is True:
            return CollectionResult(
                status=CollectionStatus.NEED_VERIFY,
                platform=self.platform,
                message="Facebook auth-cookie metadata present; session and collection access need verification",
            )
        return CollectionResult(
            status=CollectionStatus.NOT_CONFIGURED,
            platform=self.platform,
            message="Facebook auth-cookie metadata missing",
        )


register_adapter("facebook", FacebookAdapter)
