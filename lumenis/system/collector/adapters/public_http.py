from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .public_source import PublicResponse, PublicSourceError, fetch_public_url, public_source_provenance
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
        canonical_url = response.url
        if canonical and canonical.get("href"):
            candidate = urljoin(response.url, str(canonical.get("href")))
            fetched, proposed = urlsplit(response.url), urlsplit(candidate)
            if (
                proposed.scheme.lower() == fetched.scheme.lower()
                and proposed.hostname == fetched.hostname
                and proposed.port == fetched.port
                and not proposed.username and not proposed.password
            ):
                canonical_url = candidate
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
        # A site-wide meta description can describe the publisher rather than
        # the article. Prefer a substantial content container when one exists;
        # otherwise retain the short-page/description behavior.
        candidates = []
        for node in soup.select(
            'article, [itemprop="articleBody"], .zw, [class*="-body-"], .float100, main'
        ):
            if node.name in {"script", "style", "nav", "header", "footer"}:
                continue
            body = node.get_text(" ", strip=True)
            if 500 <= len(body) <= 100_000:
                candidates.append(body)
        article_text = min(candidates, key=len) if candidates else ""
        text = article_text or (soup.body.get_text(" ", strip=True) if soup.body else "")
        if len(text) > 1000:
            text = text[:1000].rstrip() + "…"
        published = ""
        for selector in (
            {"property": "article:published_time"},
            {"name": "date"},
            {"name": re.compile("^pubdate$", re.I)},
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
            "content": str(text if article_text or not description else description.get("content")),
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
        if not target:
            return CollectionResult(
                status=CollectionStatus.NOT_CONFIGURED,
                platform=self.platform,
                message="请先提供本次要读取的公开页面地址",
                metadata={"healthcheck_scope": "source_input_required"},
            )
        try:
            response = self.fetcher(target)
            item = self._item(response)
            if not item["content"].strip():
                return CollectionResult(
                    status=CollectionStatus.PROVIDER_UNAVAILABLE,
                    platform=self.platform,
                    message="公开页面没有可提取的正文内容",
                    metadata={
                        "provider": "public_http",
                        "error_type": "EMPTY_CONTENT",
                        **public_source_provenance(response, target),
                    },
                )
            collected_at = item["captured_at"]
            return CollectionResult(
                status=CollectionStatus.SUCCESS,
                platform=self.platform,
                items=[self.normalize_item(item)],
                raw_count=1,
                new_count=1,
                metadata={
                    "provider": "public_http",
                    "source": response.url,
                    "collected_at": collected_at,
                    **public_source_provenance(response, target),
                },
            )
        except (PublicSourceError, ValueError) as exc:
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="当前公开页面暂时无法读取，请稍后重试",
                metadata={"provider": "public_http", "error_type": type(exc).__name__},
            )
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message="公开页面内容暂时无法整理，请稍后重试",
                metadata={"provider": "public_http", "error_type": type(exc).__name__},
            )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        target = str(kwargs.get("url") or content_id or "").strip()
        if not target.lower().startswith(("http://", "https://")):
            return CollectionResult(status=CollectionStatus.NOT_SUPPORTED, platform=self.platform, message="detail requires a public URL")
        return self.search(target)

    def health_check(self, **kwargs: Any) -> CollectionResult:
        if not str(kwargs.get("url") or "").strip():
            return CollectionResult(
                status=CollectionStatus.NOT_CONFIGURED,
                platform=self.platform,
                message="尚未提供本次读取所需的公开页面地址",
                metadata={"healthcheck_scope": "source_input_required", "requires_authorization": False},
            )
        return CollectionResult(
            status=CollectionStatus.NEED_VERIFY,
            platform=self.platform,
            message="当前公开页面需要在本次人工读取中验证可用性",
            metadata={"provider": "public_http", "healthcheck_scope": "source_requires_live_check", "requires_authorization": False},
        )


register_adapter("public_http", PublicHttpAdapter)
