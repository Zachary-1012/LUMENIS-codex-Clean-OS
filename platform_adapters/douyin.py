from __future__ import annotations

import logging
from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter

logger = logging.getLogger(__name__)


class DouyinAdapter(BasePlatformAdapter):
    """抖音主链路适配器（薄封装 v4 DouyinAdapter 引擎）。

    v4 引擎已实现浏览器+JSON拦截+DOM 解析的完整搜索采集；
    本适配器负责将 v4 AdapterResult 映射为主链路 CollectionResult，
    不重复实现采集逻辑。detail/comments/creator 待 v4 引擎补全后接入。
    """

    platform = "douyin"
    enabled = False  # 需要 cookie + 浏览器环境，默认关闭，运行时检查后启用
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _load_backend(self):
        """懒加载 v4 DouyinAdapter 引擎。"""
        if self.backend is not None:
            return self.backend
        try:
            from v4_upgrade.adapters.douyin import DouyinAdapter as V4DouyinAdapter
            return V4DouyinAdapter()
        except Exception as exc:
            raise RuntimeError(f"无法加载 v4 抖音采集引擎: {exc}") from exc

    @staticmethod
    def _v4_status_to_main(success: bool, notes: list, error: str) -> CollectionStatus:
        """v4 AdapterResult(success/notes/error) → 主链路 CollectionStatus。"""
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err_lower = (error or "").lower()
        if any(k in err_lower for k in ("登录", "login", "cookie", "session", "失效")):
            return CollectionStatus.SESSION_EXPIRED
        if any(k in err_lower for k in ("风控", "验证", "captcha", "verify", "risk", "频控", "rate")):
            return CollectionStatus.RISK_WARNING
        if any(k in err_lower for k in ("block", "封禁", "不可用")):
            return CollectionStatus.BLOCKED
        if any(k in err_lower for k in ("冷却", "cooling", "cooldown")):
            return CollectionStatus.COOLING_DOWN
        return CollectionStatus.COLLECT_ERROR

    def _v4_notes_to_items(self, notes: list) -> list[dict]:
        """v4 CollectedNote → 主链路 items dict。"""
        items = []
        for n in notes or []:
            items.append(self.normalize_item({
                "platform_content_id": getattr(n, "raw_data", {}).get("aweme_id", "") if isinstance(getattr(n, "raw_data", None), dict) else "",
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
                "raw": getattr(n, "raw_data", {}),
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
                metadata={"engine": "v4_douyin_browser", "duration_s": result.duration_seconds},
            )
        except Exception as exc:
            logger.exception("抖音主链路采集异常")
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=str(exc),
            )

    def _delegate_v4(self, method: str, *args, **kwargs) -> CollectionResult:
        try:
            backend = self._load_backend()
            fn = getattr(backend, method)
            result = fn(*args, **kwargs)
            status = self._v4_status_to_main(result.success, result.notes, result.error)
            items = self._v4_notes_to_items(result.notes)
            return CollectionResult(
                status=status, platform=self.platform, items=items,
                raw_count=result.raw_count, new_count=len(items),
                message=result.error or "",
                metadata={"engine": f"v4_douyin_{method}", "duration_s": result.duration_seconds},
            )
        except Exception as exc:
            logger.exception("抖音主链路 %s 异常", method)
            return CollectionResult(status=CollectionStatus.COLLECT_ERROR, platform=self.platform, message=str(exc))

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("detail", aweme_id=content_id)

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("comments", aweme_id=content_id, max_comments=kwargs.get("max_comments", 20))

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("creator", sec_uid=creator_id)

    def health_check(self, **kwargs: Any) -> CollectionResult:
        """检查抖音 cookie 与引擎可用性（不实际启动浏览器）。"""
        import os
        try:
            from v4_upgrade.adapters.cookie_vault import _resolve_path
            resolved = _resolve_path("douyin")
            cookie_path = str(resolved) if resolved else os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "cookies", "douyin.json",
            )
        except Exception:
            cookie_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "cookies", "douyin.json",
            )
        # Keep this filesystem check explicit and patchable for the existing
        # unit contract; runtime path resolution itself belongs to Cookie Vault.
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
                message="抖音引擎就绪，cookie 存在（浏览器采集需手动启动验证）",
                metadata={"cookie_exists": True, "engine_ok": True},
            )
        return CollectionResult(
            status=CollectionStatus.SESSION_EXPIRED if not cookie_exists else CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message=f"抖音未就绪: cookie_exists={cookie_exists}, engine_ok={engine_ok}",
            metadata={"cookie_exists": cookie_exists, "engine_ok": engine_ok},
        )


register_adapter("douyin", DouyinAdapter)
