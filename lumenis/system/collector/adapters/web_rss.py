from __future__ import annotations

import hashlib
from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter


class WebRSSAdapter(BasePlatformAdapter):
    """Keyless public RSS adapter backed by LUMENIS's existing Google News reader."""

    platform = "web_rss"
    enabled = False
    monitor_priority = "secondary"

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        query = str(keyword or "").strip()
        if not query:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message="keyword is required",
            )
        try:
            from web_discovery import fetch_google_news_rss

            outcome = fetch_google_news_rss(query, max_results=kwargs.get("max_results", 20))
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="public RSS provider is unavailable",
                metadata={"error_type": type(exc).__name__, "provider": "google_news_rss"},
            )

        collected_at = str(outcome.get("collected_at") or "")
        metadata = {
            "provider": "google_news_rss",
            "source": "news.google.com/rss/search",
            "collected_at": collected_at,
            "healthcheck_scope": "public_endpoint_configuration",
        }
        if not outcome.get("ok"):
            metadata["error_type"] = outcome.get("error_type") or "PROVIDER_UNAVAILABLE"
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="public RSS provider is unavailable",
                metadata=metadata,
            )

        source_items = outcome.get("items") or []
        items = []
        for source_item in source_items:
            url = str(source_item.get("url") or "").strip()
            if not url:
                metadata["error_type"] = "MISSING_SOURCE_IDENTITY"
                return CollectionResult(
                    status=CollectionStatus.PROVIDER_UNAVAILABLE,
                    platform=self.platform,
                    message="public RSS item is missing a stable source URL",
                    raw_count=len(source_items),
                    new_count=0,
                    metadata=metadata,
                )
            item_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
            source_name = str(source_item.get("source") or "").strip()
            items.append(self.normalize_item({
                "platform_content_id": f"google-news:{item_id}",
                "title": source_item.get("title") or "",
                "content": "",
                "author_id": source_name or None,
                "author_nickname": source_name,
                "publish_datetime": source_item.get("published_at") or "",
                "url": url,
                "likes": None,
                "comments": None,
                "collects": None,
                "shares": None,
                "captured_at": collected_at,
                "raw": {
                    "provider": "google_news_rss",
                    "source_name": source_item.get("source") or "",
                    "source_keyword": query,
                },
            }))
        return CollectionResult(
            status=CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
            platform=self.platform,
            items=items,
            raw_count=len(items),
            new_count=len(items),
            metadata=metadata,
        )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NOT_SUPPORTED,
            platform=self.platform,
            message="RSS detail retrieval is not part of the configured public-feed contract",
        )

    def capability_map(self) -> dict[str, str]:
        capabilities = super().capability_map()
        capabilities["detail"] = "not_supported"
        return capabilities

    def health_check(self, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.SUCCESS,
            platform=self.platform,
            message="public RSS provider is configured; network is checked during collection",
            metadata={
                "provider": "google_news_rss",
                "healthcheck_scope": "configuration_only",
                "requires_authorization": False,
            },
        )


register_adapter("web_rss", WebRSSAdapter)
