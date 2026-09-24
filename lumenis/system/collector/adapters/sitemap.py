from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Callable
from xml.etree import ElementTree

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .public_source import PublicResponse, PublicSourceError, fetch_public_url
from .registry import register_adapter


_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class SitemapAdapter(BasePlatformAdapter):
    """Keyless XML sitemap URL discovery; it never creates a second content store."""

    platform = "sitemap"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, fetcher: Callable[[str], PublicResponse] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.fetcher = fetcher or fetch_public_url

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        sitemap_url = str(kwargs.get("sitemap_url") or keyword or "").strip()
        try:
            response = self.fetcher(sitemap_url)
            root = ElementTree.fromstring(response.content)
            root_name = root.tag.rsplit("}", 1)[-1]
            if root_name not in {"sitemapindex", "urlset"}:
                raise ValueError("public response is not an XML Sitemap document")
            collected_at = datetime.now().isoformat(timespec="seconds")
            items = []
            for node in list(root):
                loc = node.findtext(f"{_SITEMAP_NS}loc") or node.findtext("loc") or ""
                loc = str(loc).strip()
                if not loc:
                    continue
                identity = hashlib.sha256(loc.encode("utf-8")).hexdigest()[:32]
                lastmod = node.findtext(f"{_SITEMAP_NS}lastmod") or node.findtext("lastmod") or ""
                kind = "sitemap" if root_name == "sitemapindex" else "url"
                items.append(self.normalize_item({
                    "platform_content_id": f"sitemap:{identity}",
                    "title": loc,
                    "content": "",
                    "author_id": None,
                    "author_nickname": None,
                    "publish_datetime": str(lastmod).strip(),
                    "url": loc,
                    "captured_at": collected_at,
                    "raw": {"sitemap_url": response.url, "entry_kind": kind},
                }))
            limit = max(1, min(int(kwargs.get("max_results", 100)), 5000))
            items = items[:limit]
            return CollectionResult(
                status=CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
                platform=self.platform,
                items=items,
                raw_count=len(items),
                new_count=len(items),
                metadata={"provider": "public_sitemap_xml", "source": response.url, "collected_at": collected_at, "entry_kind": root_name},
            )
        except (PublicSourceError, ElementTree.ParseError, ValueError, TypeError) as exc:
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="public Sitemap source is unavailable",
                metadata={"provider": "public_sitemap_xml", "error_type": type(exc).__name__},
            )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(status=CollectionStatus.NOT_SUPPORTED, platform=self.platform, message="Sitemap detail is not part of URL discovery")

    def health_check(self, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.SUCCESS,
            platform=self.platform,
            message="public Sitemap adapter is ready; source is checked per human-triggered collection",
            metadata={"provider": "public_sitemap_xml", "healthcheck_scope": "public_endpoint_configuration", "requires_authorization": False},
        )


register_adapter("sitemap", SitemapAdapter)
