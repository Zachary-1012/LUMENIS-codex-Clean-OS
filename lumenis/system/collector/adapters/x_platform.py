from __future__ import annotations

import logging
from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter

logger = logging.getLogger(__name__)


class XAdapter(BasePlatformAdapter):
    """X (Twitter) 主链路适配器（薄封装 v4 XAdapter 引擎）。

    v4 引擎使用浏览器 CDP + cookie_vault 采集 X 搜索结果，
    本适配器负责 v4 AdapterResult → 主链路 CollectionResult 映射。
    """

    platform = "x"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _load_backend(self):
        if self.backend is not None:
            return self.backend
        try:
            from lumenis.adapters.x_platform import XAdapter as V4XAdapter
            return V4XAdapter()
        except Exception as exc:
            raise RuntimeError(f"无法加载 v4 X 采集引擎: {exc}") from exc

    @staticmethod
    def _v4_status_to_main(success: bool, notes: list, error: str) -> CollectionStatus:
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err_lower = (error or "").lower()
        if any(k in err_lower for k in ("not supported", "unsupported", "review required")):
            return CollectionStatus.NOT_SUPPORTED
        if any(k in err_lower for k in ("登录", "login", "cookie", "session", "失效", "未登录")):
            return CollectionStatus.SESSION_EXPIRED
        if any(k in err_lower for k in ("风控", "验证", "captcha", "verify", "verification", "challenge", "risk", "频控")):
            return CollectionStatus.RISK_WARNING
        if any(k in err_lower for k in ("block", "封禁", "不可用")):
            return CollectionStatus.BLOCKED
        if any(k in err_lower for k in ("network error", "timeout", "connection", "dns")):
            return CollectionStatus.PROVIDER_UNAVAILABLE
        return CollectionStatus.COLLECT_ERROR

    def _v4_notes_to_items(self, notes: list) -> list[dict]:
        items = []
        for n in notes or []:
            raw = getattr(n, "raw_data", {}) or {}
            items.append(self.normalize_item({
                "platform_content_id": raw.get("tweet_id") if isinstance(raw, dict) else None,
                "title": getattr(n, "title", ""),
                "content": getattr(n, "content", ""),
                "author_id": getattr(n, "author_id", ""),
                "author_nickname": getattr(n, "author", ""),
                "publish_datetime": getattr(n, "publish_date", ""),
                "url": getattr(n, "url", ""),
                "likes": getattr(n, "likes", None),
                "comments": getattr(n, "comments", None),
                "collects": getattr(n, "collects", None),
                "shares": getattr(n, "shares", None),
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
            logger.exception("X 主链路采集失败")
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
            return CollectionResult(status=status, platform=self.platform, items=items, raw_count=result.raw_count, message=result.error or "")
        except Exception as exc:
            return CollectionResult(status=CollectionStatus.COLLECT_ERROR, platform=self.platform, message=str(exc))

    def health_check(self) -> CollectionResult:
        """Check the existing vault's non-secret X authentication metadata."""
        from lumenis.adapters.cookie_vault import check_cookie_status

        status = check_cookie_status("x")
        if status.get("has_auth_cookie"):
            return CollectionResult(
                status=CollectionStatus.NEED_VERIFY,
                platform=self.platform,
                message="X auth-cookie metadata present; login and collection access need verification",
            )
        return CollectionResult(
            status=CollectionStatus.NOT_CONFIGURED,
            platform=self.platform,
            message="X auth-cookie metadata missing",
        )


register_adapter("x", XAdapter)
