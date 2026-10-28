from __future__ import annotations

import logging
from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus, map_v4_comments
from .registry import register_adapter

logger = logging.getLogger(__name__)


class ZhihuAdapter(BasePlatformAdapter):
    """知乎主链路适配器（薄封装 v4 ZhihuAdapter 引擎）。

    v4 引擎支持 answer/article/question 三类内容搜索，
    本适配器负责 v4 AdapterResult → 主链路 CollectionResult 映射。
    detail/comments/creator 待 v4 引擎补全后接入。
    """

    platform = "zhihu"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _load_backend(self):
        if self.backend is not None:
            return self.backend
        try:
            from lumenis.adapters.zhihu import ZhihuAdapter as V4ZhihuAdapter
            self.backend = V4ZhihuAdapter(public_read_only=True)
            return self.backend
        except Exception as exc:
            raise RuntimeError(f"无法加载 v4 知乎采集引擎: {exc}") from exc

    @staticmethod
    def _v4_status_to_main(success: bool, notes: list, error: str) -> CollectionStatus:
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err_lower = (error or "").lower()
        if any(k in err_lower for k in ("登录", "login", "cookie", "session", "失效", "未登录")):
            return CollectionStatus.SESSION_EXPIRED
        if any(k in err_lower for k in ("风控", "验证", "captcha", "verify", "risk", "频控", "rate", "403", "429")):
            return CollectionStatus.RISK_WARNING
        if any(k in err_lower for k in ("block", "封禁", "不可用")):
            return CollectionStatus.BLOCKED
        if any(k in err_lower for k in ("冷却", "cooling", "cooldown")):
            return CollectionStatus.COOLING_DOWN
        return CollectionStatus.COLLECT_ERROR

    @classmethod
    def _observed_status(cls,result):
        kind=(getattr(result,'metadata',None) or {}).get('failure_class')
        return {'AUTH_REQUIRED':CollectionStatus.SESSION_EXPIRED,'ACCESS_BLOCKED':CollectionStatus.BLOCKED,
            'RATE_LIMITED':CollectionStatus.COOLING_DOWN,'CONTENT_UNAVAILABLE':CollectionStatus.PROVIDER_UNAVAILABLE,
            'PROVIDER_UNAVAILABLE':CollectionStatus.PROVIDER_UNAVAILABLE}.get(kind) or cls._v4_status_to_main(
                result.success,result.notes,result.error)

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
                'cover':getattr(n,'cover',None),
                "raw": raw,
            }))
        return items

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        try:
            backend = self._load_backend()
            max_results = int(kwargs.get("max_results", 20))
            result = backend.search(keyword, max_results=max_results,
                **({'cursor':kwargs['cursor']} if kwargs.get('cursor') is not None else {}))
            status = self._observed_status(result)
            items = self._v4_notes_to_items(result.notes)
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=items,
                raw_count=result.raw_count,
                new_count=len(items),
                message=result.error or "",
                metadata={**(getattr(result,'metadata',None) or {}), "engine": "v4_zhihu_search",
                    'provider':'zhihu_first_party_read_api','source_access_mode':'public_read_only',
                    'cookies_used':False,'requires_auth':False,"duration_s": result.duration_seconds},
            )
        except Exception as exc:
            logger.exception("知乎主链路采集异常")
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
            status = self._observed_status(result)
            items = self._v4_notes_to_items(result.notes)
            comments = map_v4_comments(result.notes) if method == 'comments' else []
            return CollectionResult(
                status=status, platform=self.platform, items=[] if method == 'comments' else items, comments=comments,
                raw_count=result.raw_count, new_count=len(items),
                message=result.error or "",
                metadata={**(getattr(result, 'metadata', None) or {}),
                          "engine": f"v4_zhihu_{method}", "duration_s": result.duration_seconds},
            )
        except Exception as exc:
            logger.exception("知乎主链路 %s 异常", method)
            return CollectionResult(status=CollectionStatus.COLLECT_ERROR, platform=self.platform, message=str(exc))

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("detail", content_id=content_id, content_type=kwargs.get("content_type", "answer"))

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("comments", content_id=content_id,
            content_type=kwargs.get("content_type", "answer"), max_comments=kwargs.get("max_comments", 20),
            include_replies=include_replies,**({'cursor':kwargs['cursor']} if kwargs.get('cursor') is not None else {}))

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("creator", user_id=creator_id)

    def author_posts(self, author_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4('author_posts',author_id,max_results=kwargs.get('max_results',20),
                                 **({'cursor':kwargs['cursor']} if kwargs.get('cursor') is not None else {}))

    def health_check(self, **kwargs: Any) -> CollectionResult:
        try:
            backend = self._load_backend()
            engine_ok = backend is not None
        except Exception:
            engine_ok = False
        if engine_ok:
            return CollectionResult(
                status=CollectionStatus.NEED_VERIFY,
                platform=self.platform,
                message="知乎公开只读引擎已加载；实际来源可用性由用户请求验证",
                metadata={"engine_ok": True, "cookie_required": False,'healthcheck_scope':'local_engine_only'},
            )
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="知乎引擎未就绪",
            metadata={"engine_ok": False},
        )


register_adapter("zhihu", ZhihuAdapter)
