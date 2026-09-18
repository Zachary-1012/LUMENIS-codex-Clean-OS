from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Callable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .public_source import PublicResponse, PublicSourceError, fetch_public_url, validate_public_url
from .registry import register_adapter


class PublicHttpAdapter(BasePlatformAdapter):
    """Keyless public HTML acquisition with an auditable normalized item."""

    platform = "public_http"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, fetcher: Callable[[str], PublicResponse] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.fetcher = fetcher or fetch_public_url

    @staticmethod
    def _item(response: PublicResponse) -> dict[str, Any]:
        soup = BeautifulSoup(response.content, "html.parser")
        canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
        canonical_url = urljoin(response.url, str(canonical.get("href"))) if canonical and canonical.get("href") else response.url
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
        text = soup.get_text(" ", strip=True)
        if len(text) > 1000:
            text = text[:1000].rstrip() + "…"
        published = ""
        for selector in (
            {"property": "article:published_time"},
            {"name": "date"},
            {"itemprop": "datePublished"},
        ):
            tag = soup.find("meta", attrs=selector)
            if tag and tag.get("content"):
                published = str(tag["content"]).strip()
                break
        item_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:32]
        return {
            "platform_content_id": f"public-http:{item_id}",
            "title": title,
            "content": str(description.get("content") if description else text),
            "author_id": None,
            "author_nickname": None,
            "publish_datetime": published,
            "url": canonical_url,
            "likes": None,
            "comments": None,
            "collects": None,
            "shares": None,
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "raw": {"content_type": "text/html", "canonical_url": canonical_url},
        }

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        target = str(kwargs.get("url") or keyword or "").strip()
        try:
            response = self.fetcher(target)
            item = self._item(response)
            collected_at = item["captured_at"]
            return CollectionResult(
                status=CollectionStatus.SUCCESS,
                platform=self.platform,
                items=[self.normalize_item(item)],
                raw_count=1,
                new_count=1,
                metadata={"provider": "public_http", "source": response.url, "collected_at": collected_at},
            )
        except (PublicSourceError, ValueError) as exc:
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="public HTTP source is unavailable",
                metadata={"provider": "public_http", "error_type": type(exc).__name__},
            )
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message="public HTTP response could not be normalized",
                metadata={"provider": "public_http", "error_type": type(exc).__name__},
            )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        target = str(kwargs.get("url") or content_id or "").strip()
        if not target.lower().startswith(("http://", "https://")):
            return CollectionResult(status=CollectionStatus.NOT_SUPPORTED, platform=self.platform, message="detail requires a public URL")
        return self.search(target)

    def health_check(self, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.SUCCESS,
            platform=self.platform,
            message="public HTTP adapter is ready; source is checked per human-triggered collection",
            metadata={"provider": "public_http", "healthcheck_scope": "public_endpoint_configuration", "requires_authorization": False},
        )


register_adapter("public_http", PublicHttpAdapter)
