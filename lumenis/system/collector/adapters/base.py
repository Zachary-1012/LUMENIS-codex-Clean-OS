from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, Optional


class CollectionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NO_NEW_DATA = "NO_NEW_DATA"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    RISK_WARNING = "RISK_WARNING"
    NEED_VERIFY = "NEED_VERIFY"
    QR_REQUIRED = "QR_REQUIRED"  # V3.0 P0: 需要扫码恢复
    BLOCKED = "BLOCKED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    COLLECT_ERROR = "COLLECT_ERROR"
    COOLING_DOWN = "COOLING_DOWN"


class AccessClass(str, Enum):
    """How this exact adapter call obtained its source material.

    These labels describe the route. They do not grant platform or LUMENIS
    permissions; those remain owned by the existing Permission/session paths.
    """

    Z0_PUBLIC = "Z0"
    Z1_AUTHORIZED_SESSION = "Z1"
    Z2_OFFICIAL_API = "Z2"


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
    # Explicit route/provenance fields are appended for positional compatibility.
    # The secondary Collector binds these after the adapter returns, then writes
    # this record through the existing Evidence transaction.
    provenance: Dict[str, Any] = field(default_factory=dict)
    access_class: Optional[AccessClass] = None
    backend: Optional[str] = None
    capability: Optional[str] = None
    route_id: Optional[str] = None
    # Selected route and observed acquisition facts remain separate. The
    # attempted fields describe dispatch; access_class/backend describe only
    # facts the adapter actually returned or a completed read can establish.
    attempted_access_class: Optional[AccessClass] = None
    attempted_backend: Optional[str] = None
    actual_access_state: Optional[str] = None
    # Ephemeral original transport response, retained only for Source/Artifact
    # custody in the owning transaction; never metadata, API or logging output.
    original_response: Any = field(default=None, repr=False, compare=False)

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
            status=CollectionStatus.NOT_SUPPORTED,
            platform=self.platform,
            message="comments capability is not supported by this adapter",
        )

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NOT_SUPPORTED,
            platform=self.platform,
            message="author capability is not supported by this adapter",
        )

    def author(self, author_id: str, **kwargs: Any) -> CollectionResult:
        """Canonical author-profile name; ``creator`` remains a compatible alias."""
        return self.creator(author_id, **kwargs)

    def author_posts(self, author_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NOT_SUPPORTED,
            platform=self.platform,
            message="author_posts capability is not supported by this adapter",
        )

    def health_check(self, **_: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NOT_CONFIGURED,
            platform=self.platform,
            message="adapter has no configured health check",
        )

    def healthcheck(self, **kwargs: Any) -> CollectionResult:
        """Canonical spelling; keep ``health_check`` for existing callers."""
        return self.health_check(**kwargs)

    def capability_map(self) -> Dict[str, str]:
        """Describe implementation presence separately from runtime readiness."""
        cls = type(self)
        creator_implemented = cls.creator is not BasePlatformAdapter.creator
        author_implemented = cls.author is not BasePlatformAdapter.author or creator_implemented
        return {
            "search": "implemented",
            "detail": "implemented",
            "comments": "implemented" if cls.comments is not BasePlatformAdapter.comments else "not_supported",
            "author": "implemented" if author_implemented else "not_supported",
            "author_posts": "implemented" if cls.author_posts is not BasePlatformAdapter.author_posts else "not_supported",
            "healthcheck": "implemented" if cls.health_check is not BasePlatformAdapter.health_check else "not_configured",
        }

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
            "cover": item.get("cover"),
            "captured_at": item.get("captured_at"),
            "raw": item.get("raw"),
        }


def map_v4_comments(notes: Iterable[Any]) -> list[Dict[str, Any]]:
    """Map existing v4 comment notes to the canonical comments result field."""
    comments: list[Dict[str, Any]] = []
    for note in notes or []:
        raw = getattr(note, "raw_data", {})
        raw = raw if isinstance(raw, dict) else {}
        def identity(value):
            return str(value) if type(value) in (str, int) and str(value).strip() else None
        comment_id = identity(raw.get('platform_comment_id') or raw.get("rpid") or raw.get("comment_id") or raw.get('cid') or raw.get("id"))
        parent = raw.get('parent_comment_id', raw.get('parent_id', raw.get('root')))
        parent = None if parent in (None, '', 0, '0') else identity(parent)
        comments.append({
            "platform_comment_id": comment_id,
            'parent_comment_id': parent,
            'reply_to_comment_id': identity(raw.get('reply_to_comment_id', raw.get('reply_id'))),
            'parent_content_id': identity(raw.get('parent_content_id', raw.get('aweme_id', raw.get('post_id')))),
            "content": getattr(note, "content", "") or "",
            "author_id": getattr(note, "author_id", "") or "",
            "author_nickname": getattr(note, "author", "") or "",
            "publish_datetime": getattr(note, "publish_date", "") or "",
            "likes": getattr(note, "likes", None),
            'url': getattr(note, 'url', '') or '',
            'identity_state': 'NATIVE_ID_OBSERVED' if comment_id else 'NATIVE_ID_NOT_OBSERVED',
            'raw': raw,
        })
    return comments
