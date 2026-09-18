from __future__ import annotations

import logging
from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus, map_v4_comments
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
            from lumenis.adapters.douyin import DouyinAdapter as V4DouyinAdapter
            self.backend = V4DouyinAdapter()
            return self.backend
        except Exception as exc:
            raise RuntimeError(f"无法加载 v4 抖音采集引擎: {exc}") from exc

    @staticmethod
    def _v4_status_to_main(success: bool, notes: list, error: str) -> CollectionStatus:
        """v4 AdapterResult(success/notes/error) → 主链路 CollectionStatus。"""
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err_lower = (error or "").lower()
        if any(k in err_lower for k in ("not configured", "not_configured", "cookie 缺失", "cookie 未配置", "未配置")):
            return CollectionStatus.NOT_CONFIGURED
        if any(k in err_lower for k in ("登录", "login", "session", "失效", "expired")):
            return CollectionStatus.SESSION_EXPIRED
        if any(k in err_lower for k in ("风控", "验证", "captcha", "verify", "risk", "频控", "rate")):
            return CollectionStatus.RISK_WARNING
        if any(k in err_lower for k in ("block", "封禁", "不可用")):
            return CollectionStatus.BLOCKED
        if any(k in err_lower for k in ("冷却", "cooling", "cooldown")):
            return CollectionStatus.COOLING_DOWN
        if any(k in err_lower for k in ("unavailable", "不可达", "暂不可用", "worker")):
            return CollectionStatus.PROVIDER_UNAVAILABLE
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
            if hasattr(backend, "breaker") and callable(getattr(backend, "safe_collect", None)):
                result = backend.safe_collect(keyword, max_results=max_results, allow_fallback=False)
            else:
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
                metadata={"engine": "v4_douyin_browser", "provider": "authorized_browser_worker",
                          "duration_s": result.duration_seconds},
            )
        except Exception as exc:
            logger.error("抖音主链路采集异常 error_type=%s", type(exc).__name__)
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="抖音采集提供方暂不可用",
                metadata={"provider": "authorized_browser_worker", "error_type": type(exc).__name__},
            )

    def _delegate_v4(self, method: str, *args, **kwargs) -> CollectionResult:
        try:
            backend = self._load_backend()
            fn = getattr(backend, method, None)
            if not callable(fn):
                return CollectionResult(
                    status=CollectionStatus.NOT_SUPPORTED,
                    platform=self.platform,
                    message=f"Douyin provider does not support {method}",
                    metadata={"provider": "authorized_browser_worker", "capability": method},
                )
            result = fn(*args, **kwargs)
            status = self._v4_status_to_main(result.success, result.notes, result.error)
            comments = map_v4_comments(result.notes) if method == "comments" else []
            items = [] if method == "comments" else self._v4_notes_to_items(result.notes)
            return CollectionResult(
                status=status, platform=self.platform, items=items, comments=comments,
                raw_count=result.raw_count, new_count=len(comments) if method == "comments" else len(items),
                message=result.error or "",
                metadata={"engine": f"v4_douyin_{method}", "provider": "authorized_browser_worker",
                          "duration_s": result.duration_seconds},
            )
        except Exception as exc:
            logger.error("抖音主链路 %s 异常 error_type=%s", method, type(exc).__name__)
            return CollectionResult(status=CollectionStatus.PROVIDER_UNAVAILABLE, platform=self.platform,
                                    message="抖音采集提供方暂不可用",
                                    metadata={"provider": "authorized_browser_worker",
                                              "error_type": type(exc).__name__})

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("detail", aweme_id=content_id)

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("comments", aweme_id=content_id, max_comments=kwargs.get("max_comments", 20))

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("creator", sec_uid=creator_id)

    def health_check(self, **kwargs: Any) -> CollectionResult:
        """Check configured worker reachability without launching a browser."""
        try:
            from lumenis.adapters.douyin import _configured_browser_worker_url
            from lumenis.adapters.human_browser import is_cdp_url_open
            cdp_url = _configured_browser_worker_url()
        except Exception:
            return CollectionResult(
                status=CollectionStatus.NOT_CONFIGURED,
                platform=self.platform,
                message="抖音远程浏览器工作器尚未配置",
                metadata={"provider": "authorized_browser_worker", "endpoint_configured": False,
                          "healthcheck_scope": "configuration_only"},
            )
        if not is_cdp_url_open(cdp_url):
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="抖音远程浏览器工作器不可达",
                metadata={"provider": "authorized_browser_worker", "endpoint_configured": True,
                          "healthcheck_scope": "worker_connectivity"},
            )
        try:
            backend = self._load_backend()
            engine_ok = backend is not None
        except Exception:
            engine_ok = False
        return CollectionResult(
            status=CollectionStatus.NEED_VERIFY if engine_ok else CollectionStatus.PROVIDER_UNAVAILABLE,
            platform=self.platform,
            message="抖音浏览器工作器可达；授权态仅在本次人工请求中验证",
            metadata={"provider": "authorized_browser_worker", "endpoint_configured": True,
                      "session_state": "worker_reachable_unverified",
                      "healthcheck_scope": "worker_connectivity", "engine_ok": engine_ok},
        )


register_adapter("douyin", DouyinAdapter)
