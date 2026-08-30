from __future__ import annotations

from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter


class DouyinAdapter(BasePlatformAdapter):
    """Douyin adapter contract.

    The current repository does not expose a verified production Douyin collector in
    the same way as the XHS collector. Therefore this adapter is deliberately a safe
    extension point rather than a fake implementation. Once a compliant backend is
    selected and locally tested, inject it through ``backend`` without changing the
    upper business layer.
    """

    platform = "douyin"
    enabled = True
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _not_ready(self, operation: str, content_id: str | None = None) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message=(
                f"Douyin {operation} backend is not installed in this release. "
                "Do not silently fall back to another platform or report zero data."
            ),
            metadata={"content_id": content_id, "ready_for_backend": True},
        )

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        if self.backend is None:
            return self._not_ready("search")
        return self.backend.search(keyword, **kwargs)

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        if self.backend is None:
            return self._not_ready("detail", content_id)
        return self.backend.detail(content_id, **kwargs)

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        if self.backend is None:
            return self._not_ready("comments", content_id)
        return self.backend.comments(content_id, include_replies=include_replies, **kwargs)

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        if self.backend is None:
            return self._not_ready("creator", creator_id)
        return self.backend.creator(creator_id, **kwargs)


register_adapter("douyin", DouyinAdapter)
