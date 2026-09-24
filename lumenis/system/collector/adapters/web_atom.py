from __future__ import annotations

import hashlib
from datetime import datetime
from email.utils import format_datetime
from typing import Any, Callable

import feedparser

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .public_source import PublicResponse, PublicSourceError, fetch_public_url
from .registry import register_adapter


def _entry_time(entry: Any) -> str:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            try:
                from datetime import timezone
                return format_datetime(datetime(*value[:6], tzinfo=timezone.utc))
            except (TypeError, ValueError):
                pass
    return str(entry.get("published") or entry.get("updated") or "")[:80]


class AtomAdapter(BasePlatformAdapter):
    """Keyless Atom feed adapter using the same Evidence boundary as RSS."""

    platform = "web_atom"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, fetcher: Callable[[str], PublicResponse] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.fetcher = fetcher or fetch_public_url

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        feed_url = str(kwargs.get("feed_url") or keyword or "").strip()
        source_url = feed_url
        try:
            response = self.fetcher(feed_url)
            source_url = str(response.url or feed_url).strip()
            parsed = feedparser.parse(response.content)
            if getattr(parsed, "bozo", False) and not parsed.entries:
                raise PublicSourceError("Atom feed could not be parsed")
            collected_at = datetime.now().isoformat(timespec="seconds")
            items = []
            for entry in list(parsed.entries)[: int(kwargs.get("max_results", 20))]:
                link = str(entry.get("link") or "").strip()
                identity = str(entry.get("id") or link).strip()
                if not identity:
                    raise PublicSourceError("Atom entry is missing a stable identity")
                item_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
                content = str(entry.get("summary") or "")
                if not content and entry.get("content"):
                    content = str(entry.content[0].get("value") or "")
                items.append(self.normalize_item({
                    "platform_content_id": f"atom:{item_id}",
                    "title": str(entry.get("title") or ""),
                    "content": content,
                    "author_id": str((entry.get("author_detail") or {}).get("name") or entry.get("author") or "") or None,
                    "author_nickname": str(entry.get("author") or "") or None,
                    "publish_datetime": _entry_time(entry),
                    "url": link,
                    "captured_at": collected_at,
                    "raw": {"feed_url": response.url, "entry_id": identity},
                }))
            return CollectionResult(
                status=CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
                platform=self.platform,
                items=items,
                raw_count=len(items),
                new_count=len(items),
                metadata={"provider": "feedparser_atom", "source": response.url, "collected_at": collected_at},
            )
        except (PublicSourceError, ValueError, TypeError) as exc:
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="public Atom source is unavailable",
                metadata={"provider": "feedparser_atom", "source": source_url, "error_type": type(exc).__name__},
            )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(status=CollectionStatus.NOT_SUPPORTED, platform=self.platform, message="Atom detail is not part of the feed contract")

    def health_check(self, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.SUCCESS,
            platform=self.platform,
            message="public Atom adapter is ready; source is checked per human-triggered collection",
            metadata={"provider": "feedparser_atom", "healthcheck_scope": "public_endpoint_configuration", "requires_authorization": False},
        )


register_adapter("web_atom", AtomAdapter)
