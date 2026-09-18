from __future__ import annotations

import logging
from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus, map_v4_comments
from .registry import register_adapter

logger = logging.getLogger(__name__)


class WeiboAdapter(BasePlatformAdapter):
    """微博主链路适配器（薄封装 v4 WeiboAdapter 引擎）。

    v4 引擎走移动端搜索 API（m.weibo.cn）+ cookie + HTML清洗，
    本适配器负责 v4 AdapterResult → 主链路 CollectionResult 映射。
    detail/comments/creator 待 v4 引擎补全后接入。
    """

    platform = "weibo"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _load_backend(self):
        if self.backend is not None:
            return self.backend
        try:
            from lumenis.adapters.weibo import WeiboAdapter as V4WeiboAdapter
            self.backend = V4WeiboAdapter()
            return self.backend
        except Exception as exc:
            raise RuntimeError(f"无法加载 v4 微博采集引擎: {exc}") from exc

    @staticmethod
    def _v4_status_to_main(success: bool, notes: list, error: str) -> CollectionStatus:
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err_lower = (error or "").lower()
        if any(k in err_lower for k in ("not configured", "not_configured", "cookie 缺失", "cookie 为空", "未配置")):
            return CollectionStatus.NOT_CONFIGURED
        if any(k in err_lower for k in ("登录", "login", "session", "失效", "expired", "未登录")):
            return CollectionStatus.SESSION_EXPIRED
        if any(k in err_lower for k in ("风控", "验证", "captcha", "verify", "risk", "频控", "rate", "403")):
            return CollectionStatus.RISK_WARNING
        if any(k in err_lower for k in ("block", "封禁", "不可用")):
            return CollectionStatus.BLOCKED
        if any(k in err_lower for k in ("冷却", "cooling", "cooldown")):
            return CollectionStatus.COOLING_DOWN
        if any(k in err_lower for k in ("unavailable", "不可用", "timeout", "连接")):
            return CollectionStatus.PROVIDER_UNAVAILABLE
        return CollectionStatus.COLLECT_ERROR

    def _v4_notes_to_items(self, notes: list) -> list[dict]:
        items = []
        for n in notes or []:
            raw = getattr(n, "raw_data", {}) or {}
            items.append(self.normalize_item({
                "platform_content_id": raw.get("id", "") if isinstance(raw, dict) else "",
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
                metadata={"engine": "v4_weibo_mobile_api", "provider": "weibo_first_party_read_api",
                          "duration_s": result.duration_seconds},
            )
        except Exception as exc:
            logger.error("微博主链路采集异常 error_type=%s", type(exc).__name__)
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="微博采集提供方暂不可用",
                metadata={"provider": "weibo_first_party_read_api", "error_type": type(exc).__name__},
            )

    def _delegate_v4(self, method: str, *args, **kwargs) -> CollectionResult:
        try:
            backend = self._load_backend()
            fn = getattr(backend, method, None)
            if not callable(fn):
                return CollectionResult(
                    status=CollectionStatus.NOT_SUPPORTED,
                    platform=self.platform,
                    message=f"Weibo provider does not support {method}",
                    metadata={"provider": "weibo_first_party_read_api", "capability": method},
                )
            result = fn(*args, **kwargs)
            status = self._v4_status_to_main(result.success, result.notes, result.error)
            comments = map_v4_comments(result.notes) if method == "comments" else []
            items = [] if method == "comments" else self._v4_notes_to_items(result.notes)
            return CollectionResult(
                status=status, platform=self.platform, items=items, comments=comments,
                raw_count=result.raw_count, new_count=len(comments) if method == "comments" else len(items),
                message=result.error or "",
                metadata={"engine": f"v4_weibo_{method}", "provider": "weibo_first_party_read_api",
                          "duration_s": result.duration_seconds},
            )
        except Exception as exc:
            logger.exception("微博主链路 %s 异常", method)
            return CollectionResult(status=CollectionStatus.PROVIDER_UNAVAILABLE, platform=self.platform,
                                    message="微博采集提供方暂不可用",
                                    metadata={"provider": "weibo_first_party_read_api",
                                              "error_type": type(exc).__name__})

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("detail", mid=content_id)

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("comments", mid=content_id, max_comments=kwargs.get("max_comments", 20))

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("creator", uid=creator_id)

    def health_check(self, **kwargs: Any) -> CollectionResult:
        from lumenis.adapters.cookie_vault import check_cookie_status
        session_state = check_cookie_status("weibo").get("status")
        try:
            backend = self._load_backend()
            engine_ok = backend is not None
        except Exception:
            engine_ok = False
        if not engine_ok:
            status = CollectionStatus.PROVIDER_UNAVAILABLE
        elif session_state != "ACTIVE":
            status = CollectionStatus.NOT_CONFIGURED
        else:
            status = CollectionStatus.NEED_VERIFY
        return CollectionResult(
            status=status,
            platform=self.platform,
            message="微博授权态仅在本次人工请求中验证",
            metadata={"provider": "weibo_first_party_read_api",
                      "session_state": "configured_unverified" if session_state == "ACTIVE" else "not_configured",
                      "healthcheck_scope": "local_configuration", "engine_ok": engine_ok},
        )


register_adapter("weibo", WeiboAdapter)
