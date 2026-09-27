from __future__ import annotations

import hashlib
from datetime import datetime
from email.utils import format_datetime
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit, urlunsplit

import feedparser

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .public_source import PublicResponse, PublicSourceError, fetch_public_url, public_source_provenance
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


def _is_blocked_youtube_feed(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    return (host == "youtube.com" or host.endswith(".youtube.com")) and parts.path == "/feeds/videos.xml"


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
        if not feed_url:
            return CollectionResult(
                status=CollectionStatus.NOT_CONFIGURED,
                platform=self.platform,
                message="请先提供本次要读取的 Atom 订阅地址",
                metadata={"healthcheck_scope": "source_input_required"},
            )
        parts = urlsplit(feed_url)
        source_url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        if _is_blocked_youtube_feed(feed_url):
            return CollectionResult(
                status=CollectionStatus.BLOCKED,
                platform=self.platform,
                message="This YouTube feed is blocked pending an authorized access route.",
                metadata={"provider": "feedparser_atom", "blocked_reason": "source_policy"},
            )
        try:
            response = self.fetcher(feed_url)
            if _is_blocked_youtube_feed(response.url):
                return CollectionResult(
                    status=CollectionStatus.BLOCKED,
                    platform=self.platform,
                    message="This YouTube feed is blocked pending an authorized access route.",
                    metadata={"provider": "feedparser_atom", "blocked_reason": "source_policy"},
                )
            parts = urlsplit(response.url)
            source_url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
            parsed = feedparser.parse(response.content)
            if getattr(parsed, "bozo", False) and not parsed.entries:
                raise PublicSourceError("Atom feed could not be parsed")
            collected_at = datetime.now().isoformat(timespec="seconds")
            items = []
            feed_parts = urlsplit(feed_url)
            expected_channel = (
                parse_qs(feed_parts.query).get("channel_id", [None])[0]
                if feed_parts.hostname == "www.youtube.com" and feed_parts.path == "/feeds/videos.xml"
                else None
            )
            for entry in list(parsed.entries)[: int(kwargs.get("max_results", 20))]:
                link = str(entry.get("link") or "").strip()
                identity = str(entry.get("id") or link).strip()
                if not identity:
                    raise PublicSourceError("Atom entry is missing a stable identity")
                video_id = str(entry.get("yt_videoid") or "").strip()
                channel_id = str(entry.get("yt_channelid") or "").strip()
                if expected_channel and channel_id != expected_channel:
                    raise PublicSourceError("Atom entry channel does not match the requested feed")
                item_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
                content = str(entry.get("summary") or "")
                if not content and entry.get("content"):
                    content = str(entry.content[0].get("value") or "")
                raw: dict[str, Any] = {"feed_url": response.url, "entry_id": identity}
                if video_id and channel_id:
                    statistics = entry.get("media_statistics") or {}
                    views = str(statistics.get("views") or "").strip()
                    thumbnails = entry.get("media_thumbnail") or []
                    raw.update({
                        "video_id": video_id,
                        "channel_id": channel_id,
                        "feed_title": str(parsed.feed.get("title") or ""),
                        "view_count": int(views) if views.isdecimal() else None,
                        "media_list": [
                            {"url": thumb["url"]} for thumb in thumbnails
                            if isinstance(thumb, dict) and thumb.get("url")
                        ],
                        "media_statistics": dict(statistics),
                        "media_starrating": dict(entry.get("media_starrating") or {}),
                    })
                items.append(self.normalize_item({
                    "platform_content_id": f"atom:{item_id}",
                    "title": str(entry.get("title") or ""),
                    "content": content,
                    "author_id": channel_id or str((entry.get("author_detail") or {}).get("name") or entry.get("author") or "") or None,
                    "author_nickname": str(entry.get("author") or "") or None,
                    "publish_datetime": _entry_time(entry),
                    "url": link,
                    "captured_at": collected_at,
                    "raw": raw,
                }))
            return CollectionResult(
                status=CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
                platform=self.platform,
                items=items,
                raw_count=len(items),
                new_count=len(items),
                metadata={
                    "provider": "feedparser_atom", "source": response.url,
                    "collected_at": collected_at,
                    **public_source_provenance(response, feed_url),
                },
            )
        except (PublicSourceError, ValueError, TypeError) as exc:
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="当前 Atom 订阅暂时无法读取，请稍后重试",
                metadata={"provider": "feedparser_atom", "source": source_url, "error_type": type(exc).__name__},
            )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(status=CollectionStatus.NOT_SUPPORTED, platform=self.platform, message="Atom detail is not part of the feed contract")

    def health_check(self, **kwargs: Any) -> CollectionResult:
        if not str(kwargs.get("feed_url") or kwargs.get("url") or "").strip():
            return CollectionResult(
                status=CollectionStatus.NOT_CONFIGURED,
                platform=self.platform,
                message="尚未提供本次读取所需的 Atom 订阅地址",
                metadata={"healthcheck_scope": "source_input_required", "requires_authorization": False},
            )
        return CollectionResult(
            status=CollectionStatus.NEED_VERIFY,
            platform=self.platform,
            message="当前 Atom 订阅需要在本次人工读取中验证可用性",
            metadata={"provider": "feedparser_atom", "healthcheck_scope": "source_requires_live_check", "requires_authorization": False},
        )


register_adapter("web_atom", AtomAdapter)
