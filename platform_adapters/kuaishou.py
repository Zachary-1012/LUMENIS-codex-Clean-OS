from __future__ import annotations

from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter


class KuaishouAdapter(BasePlatformAdapter):
    """Kuaishou boundary for an explicitly authorized first-party/session backend.

    No anonymous search or undocumented endpoint is assumed.  A provider may be
    injected behind this adapter later without changing the CTH/Evidence contract.
    """

    platform = "kuaishou"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _delegate(self, capability: str, *args: Any, **kwargs: Any) -> CollectionResult:
        if self.backend is None:
            return CollectionResult(
                status=CollectionStatus.NOT_CONFIGURED,
                platform=self.platform,
                message="No authorized Kuaishou provider/session is configured",
                metadata={"provider": "authorized_session", "healthcheck_scope": "configuration_only"},
            )
        method = getattr(self.backend, capability, None)
        if not callable(method):
            return CollectionResult(
                status=CollectionStatus.NOT_SUPPORTED,
                platform=self.platform,
                message=f"configured Kuaishou provider does not support {capability}",
            )
        try:
            result = method(*args, **kwargs)
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="Kuaishou provider request failed",
                metadata={"error_type": type(exc).__name__, "provider": "authorized_session"},
            )
        if isinstance(result, CollectionResult):
            return result
        return CollectionResult(
            status=CollectionStatus.PROVIDER_UNAVAILABLE,
            platform=self.platform,
            message="Kuaishou provider returned an invalid result",
        )

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        return self._delegate("search", keyword, **kwargs)

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate("detail", content_id, **kwargs)

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return self._delegate("comments", content_id, include_replies=include_replies, **kwargs)

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate("author", creator_id, **kwargs)

    def author_posts(self, author_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate("author_posts", author_id, **kwargs)

    def health_check(self, **kwargs: Any) -> CollectionResult:
        if self.backend is None:
            return self._delegate("health_check", **kwargs)
        method = getattr(self.backend, "healthcheck", None) or getattr(self.backend, "health_check", None)
        if not callable(method):
            return CollectionResult(
                status=CollectionStatus.NOT_CONFIGURED,
                platform=self.platform,
                message="Kuaishou provider has no health check",
                metadata={"provider": "authorized_session", "healthcheck_scope": "configuration_only"},
            )
        return self._delegate("healthcheck" if getattr(self.backend, "healthcheck", None) else "health_check", **kwargs)


register_adapter("kuaishou", KuaishouAdapter)
