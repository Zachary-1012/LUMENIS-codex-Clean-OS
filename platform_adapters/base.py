from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, Optional


class CollectionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NO_NEW_DATA = "NO_NEW_DATA"
    RISK_WARNING = "RISK_WARNING"
    NEED_VERIFY = "NEED_VERIFY"
    QR_REQUIRED = "QR_REQUIRED"  # V3.0 P0: 需要扫码恢复
    BLOCKED = "BLOCKED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    COLLECT_ERROR = "COLLECT_ERROR"
    COOLING_DOWN = "COOLING_DOWN"


@dataclass
class CollectionResult:
    status: CollectionStatus
    platform: str
    items: list[Dict[str, Any]] = field(default_factory=list)
    comments: list[Dict[str, Any]] = field(default_factory=list)
    message: str = ""
    raw_count: int = 0
    new_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in {
            CollectionStatus.SUCCESS,
            CollectionStatus.NO_NEW_DATA,
        }


class BasePlatformAdapter(ABC):
    """Stable contract between platform collectors and the monitoring core.

    Implementations must not contain business decisions such as Guangzhou Taikoo Hui
    subject filtering, risk scoring, event aggregation or report-period filtering.
    Those remain in the existing core modules.
    """

    platform: str = "unknown"
    enabled: bool = False
    monitor_priority: str = "event"

    def __init__(self, *, session_manager: Any = None, proxy_manager: Any = None, **_: Any) -> None:
        self.session_manager = session_manager
        self.proxy_manager = proxy_manager

    @abstractmethod
    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        raise NotImplementedError

    @abstractmethod
    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        raise NotImplementedError

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="comments() is not implemented for this adapter",
        )

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="creator() is not implemented for this adapter",
        )

    def health_check(self, **_: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.SUCCESS,
            platform=self.platform,
            message="adapter loaded; live platform health check is adapter-specific",
        )

    def normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize only transport/platform fields; do not apply business filters."""
        return {
            "source_platform": self.platform,
            "platform_content_id": str(item.get("platform_content_id") or item.get("id") or ""),
            "title": item.get("title"),
            "content": item.get("content"),
            "author_id": item.get("author_id"),
            "author_nickname": item.get("author_nickname"),
            "publish_datetime": item.get("publish_datetime"),
            "url": item.get("url"),
            "likes": item.get("likes"),
            "comments": item.get("comments"),
            "collects": item.get("collects"),
            "shares": item.get("shares"),
            "captured_at": item.get("captured_at"),
            "raw": item.get("raw"),
        }
