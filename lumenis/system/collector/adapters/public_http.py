from __future__ import annotations

import hashlib
from io import StringIO
import json
import re
import threading
from datetime import datetime
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Comment, NavigableString

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .public_source import (
    PublicResponse, PublicSourceError, fetch_public_url,
    public_source_error_metadata, public_source_provenance,
)
from .registry import register_adapter
from ..guard.rate_limiter import AdaptiveRateLimiter


MAX_PUBLIC_BODY_CHARS = 16_000
MAX_PUBLIC_LOCATOR_CHARS = 512
MAX_PUBLIC_LOCATOR_TOTAL_CHARS = 16_384
_CONTENT_SELECTORS = (
    'article, [itemprop="articleBody"], .zw, [class*="-body-"], '
    '.float100, .content_article, .block-text-only .container-sm, main, [role="main"]'
)
_CHROME_MARKERS = ("header", "footer", "menu", "navigation", "breadcrumb")


def _node_locator(node) -> str:
    """Return a stable tag/id/class path for one selected source block."""
    segments = []
    segment_chars = 0
    truncated = False
    current = node
    while getattr(current, "name", None) not in {None, "[document]"}:
        segment = str(current.name)
        element_id = str(current.get("id") or "")
        if element_id and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", element_id):
            segment += f"#{_locator_token(element_id)}"
        else:
            classes = [
                str(value) for value in (current.get("class") or [])[:8]
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", str(value))
            ]
            if classes:
                segment += "." + ".".join(sorted(_locator_token(value) for value in classes))
                if len(current.get("class") or []) > len(classes):
                    segment += ".more"
        parent = getattr(current, "parent", None)
        if parent is not None:
            siblings = parent.find_all(current.name, recursive=False)
            if len(siblings) > 1:
                sibling_index = next(
                    index for index, sibling in enumerate(siblings, start=1)
                    if sibling is current
                )
                segment += f":nth-of-type({sibling_index})"
        if len(segment) > 128:
            suffix = "~" + hashlib.sha256(segment.encode("utf-8")).hexdigest()[:12]
            segment = segment[:128 - len(suffix)] + suffix
        addition = len(segment) + (3 if segments else 0)
        path_budget = MAX_PUBLIC_LOCATOR_CHARS - len("… > ")
        if segment_chars + addition > path_budget:
            truncated = True
            break
        segments.append(segment)
        segment_chars += addition
        current = parent
    locator = " > ".join(reversed(segments))
    if truncated:
        prefix = "… > "
        locator = prefix + locator
    return locator


def _locator_token(value: str) -> str:
    if len(value) <= 80:
        return value
    suffix = "~" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return value[:80 - len(suffix)] + suffix


def _bounded_node_locators(nodes) -> tuple[list[str], bool]:
    locators: list[str] = []
    retained_chars = 0
    truncated = False
    for node in nodes:
        locator = _node_locator(node)
        separator_chars = 1 if locators else 0
        remaining = MAX_PUBLIC_LOCATOR_TOTAL_CHARS - retained_chars - separator_chars
        if remaining <= 0:
            truncated = True
            break
        if len(locator) > remaining:
            if remaining > 13:
                suffix = "~" + hashlib.sha256(locator.encode("utf-8")).hexdigest()[:12]
                locator = locator[:remaining - len(suffix)] + suffix
                locators.append(locator)
                retained_chars += separator_chars + len(locator)
            truncated = True
            break
        locators.append(locator)
        retained_chars += separator_chars + len(locator)
    if len(locators) < len(nodes):
        truncated = True
    return locators, truncated


def _iter_node_text_parts(node: Any, *, include_chrome: bool = False):
    """Yield normalized text pieces without copying the selected DOM subtree."""
    excluded_tags = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form"}
    never_content_tags = {"script", "style", "noscript", "template"}
    if getattr(node, "name", None) in never_content_tags:
        return
    first = True
    for text_node in node.descendants:
        if not isinstance(text_node, NavigableString) or isinstance(text_node, Comment):
            continue
        parent = getattr(text_node, "parent", None)
        excluded = False
        while parent is not None and parent is not node:
            parent_name = getattr(parent, "name", None)
            if parent_name in never_content_tags:
                excluded = True
                break
            if not include_chrome and (
                parent_name in excluded_tags
                or str(parent.get("role") or "").lower() == "navigation"
            ):
                excluded = True
                break
            parent = getattr(parent, "parent", None)
        if excluded:
            continue
        text = str(text_node).strip()
        if not text:
            continue
        if not first:
            yield " "
        yield text
        first = False


def _node_text_length(node: Any) -> int:
    return sum(len(part) for part in _iter_node_text_parts(node))


def _selected_substantive_nodes(soup: BeautifulSoup) -> list[Any]:
    """Select independent article roots before producing or retaining their text."""
    candidates: list[tuple[int, Any]] = []
    candidate_priority: dict[int, int] = {}
    for node in soup.select(_CONTENT_SELECTORS):
        if node.name in {"script", "style", "nav", "header", "footer", "aside", "form"}:
            continue
        # Apply the same chrome exclusions to the root itself as to its
        # descendants: forms and ARIA navigation regions are never content.
        if str(node.get("role") or "").lower() == "navigation":
            continue
        if node.find_parent(("nav", "header", "footer", "aside", "form")):
            continue
        if node.find_parent(attrs={"role": re.compile(r"^\s*navigation\s*$", re.I)}):
            continue
        labels = " ".join(str(value) for value in (
            node.get("id") or "", *(node.get("class") or []),
        )).lower()
        if any(marker in labels for marker in _CHROME_MARKERS):
            continue
        semantic = node.name in {"article", "main"} or node.get("itemprop") == "articleBody" or node.get("role") == "main"
        priority = (
            0 if node.name == "article" or node.get("itemprop") == "articleBody"
            else 1 if "content_article" in labels or node.find_parent(class_="block-text-only")
            else 2 if node.name != "main" else 3
        )
        # Deduplicate nested roots before measuring: an accepted ancestor of
        # equal or better priority always wins final selection, so measuring
        # this subtree again would only repeat work (quadratic on nesting).
        if any(
            candidate_priority.get(id(parent), 99) <= priority
            for parent in node.parents
        ):
            continue
        text_length = _node_text_length(node)
        if not text_length or text_length > 2 * 1024 * 1024 or (not semantic and text_length < 500):
            continue
        candidates.append((priority, node))
        candidate_priority[id(node)] = priority
    if not candidates:
        return []

    best_priority = min(candidate[0] for candidate in candidates)
    preferred = [node for priority, node in candidates if priority == best_priority]
    selected: list[Any] = []
    selected_ids: set[int] = set()
    for node in preferred:
        # An enclosing semantic element already contains this block. Keep the
        # enclosing source once; sibling articles remain separate selections.
        if any(id(parent) in selected_ids for parent in node.parents):
            continue
        selected.append(node)
        selected_ids.add(id(node))
    return selected


def _substantive_blocks(soup: BeautifulSoup) -> list[dict[str, str]]:
    """Compatibility projection of selected blocks, after nested-root removal."""
    return [
        {"text": "".join(_iter_node_text_parts(node)), "locator": _node_locator(node)}
        for node in _selected_substantive_nodes(soup)
    ]


def _substantive_body(soup: BeautifulSoup) -> str:
    """Compatibility projection of the selected article blocks."""
    return "\n\n".join(block["text"] for block in _substantive_blocks(soup))


def _capture_bounded_text(parts, max_chars: int) -> tuple[str, str, int]:
    """Hash/count the full normalized text while retaining only its bounded preview."""
    digest = hashlib.sha256()
    preview = StringIO()
    preview_length = 0
    full_length = 0
    for part in parts:
        if not part:
            continue
        digest.update(part.encode("utf-8"))
        full_length += len(part)
        remaining = max_chars - preview_length
        if remaining > 0:
            kept = part[:remaining]
            preview.write(kept)
            preview_length += len(kept)
    text = preview.getvalue()
    if full_length > max_chars:
        text = text.rstrip() + "…"
    return text, digest.hexdigest(), full_length


def _joined_node_text(nodes):
    for index, node in enumerate(nodes):
        if index:
            yield "\n\n"
        yield from _iter_node_text_parts(node)


def _publication_signals(soup: BeautifulSoup) -> tuple[str, str, str]:
    """Accept a declared publication date only when page signals agree by day."""
    signals: list[tuple[str, str]] = []
    for selector in (
        {"property": "article:published_time"},
        {"name": "date"},
        {"name": re.compile("^pubdate$", re.I)},
        {"itemprop": "datePublished"},
    ):
        tag = soup.find("meta", attrs=selector)
        if tag and tag.get("content"):
            signals.append(("meta", str(tag["content"]).strip()[:64]))
    for tag in soup.find_all("script", type="application/ld+json", limit=12):
        payload = tag.string or tag.get_text()
        if not payload or len(payload) > 100_000:
            continue
        try:
            parsed = json.loads(payload)
        except (TypeError, ValueError):
            continue
        records = parsed if isinstance(parsed, list) else [parsed]
        for record in records[:20]:
            if not isinstance(record, dict):
                continue
            kinds = record.get("@type")
            if isinstance(kinds, str):
                kinds = [kinds]
            if not isinstance(kinds, list) or not {item for item in kinds if isinstance(item, str)} & {"NewsArticle", "Article", "BlogPosting"}:
                continue
            value = record.get("datePublished")
            if isinstance(value, str) and value.strip():
                signals.append(("json_ld", value.strip()[:64]))
    for tag in soup.find_all("time", datetime=True, limit=3):
        signals.append(("time", str(tag["datetime"]).strip()[:64]))
    for tag in soup.select(".section-date")[:3]:
        value = tag.get_text(" ", strip=True).strip().strip(",").strip()
        try:
            normalized = datetime.strptime(value, "%b %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            continue
        signals.append(("visible_date", normalized))
    for tag in soup.select(".container-sm p.small")[:6]:
        value = tag.get_text(" ", strip=True).strip()
        try:
            normalized = datetime.strptime(value, "%d %b %Y").strftime("%Y-%m-%d")
        except ValueError:
            continue
        signals.append(("visible_date", normalized))
    if not signals:
        return "", "unknown", "unknown"

    days = set()
    for _, value in signals:
        try:
            days.add(datetime.fromisoformat(value.replace("Z", "+00:00")).date())
        except ValueError:
            # An unrecognized date is retained for review, never promoted.
            return "", "unknown", "unparseable"
    if len(days) != 1:
        return "", "unknown", "conflict"
    source, value = signals[0]
    return value, source, "declared"


class PublicHttpAdapter(BasePlatformAdapter):
    """Keyless public HTML acquisition with an auditable normalized item."""

    platform = "public_http"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, fetcher: Callable[[str], PublicResponse] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.fetcher = fetcher or fetch_public_url

    _document_lock = threading.Lock()
    _document_limiter = AdaptiveRateLimiter(jitter=False)

    def fetch_document(self, url: str, *, allowed_content_types: tuple[str, ...],
                       before_fetch: Callable[[], None] | None = None) -> PublicResponse:
        """Retain one bounded document response through the shared safe transport.

        The caller owns registered-scope and effect admission. This method adds
        no cookies, alternate network client, size override or persistence.
        """
        if not allowed_content_types or not all(isinstance(v, str) for v in allowed_content_types):
            raise ValueError("document content types required")
        # One process-wide original Collector limiter, not a fresh limiter per
        # request. Serialize wait+fetch so concurrent callers cannot burst.
        with self._document_lock:
            limiter = self._document_limiter
            if not limiter.can_run():
                raise PublicSourceError("public document collector cooling down")
            limiter.wait_slot()
            if before_fetch is not None:
                before_fetch()  # authorization may expire while waiting
            try:
                response = self.fetcher(url)
                if (type(response) is not PublicResponse or not 200 <= response.status_code < 300
                        or response.content_type not in allowed_content_types
                        or not 0 < len(response.content) <= 2 * 1024 * 1024):
                    raise PublicSourceError("unsupported or oversized public document response")
            except Exception:
                limiter.on_failure()
                raise
            limiter.on_success()
            return response

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
                # A site-wide homepage canonical must not collapse different
                # location/news pages into the same content identity.
                and not (fetched.path.strip("/") and not proposed.path.strip("/"))
            ):
                canonical_url = candidate
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
        # Semantic main/article content remains authoritative even when short;
        # a site-wide description must not replace a directory or address.
        selected_nodes = _selected_substantive_nodes(soup)
        if selected_nodes:
            selection = "semantic_blocks"
            locators, locators_truncated = _bounded_node_locators(selected_nodes)
            text, source_text_sha256, source_text_char_length = _capture_bounded_text(
                _joined_node_text(selected_nodes), MAX_PUBLIC_BODY_CHARS,
            )
        elif description and str(description.get("content") or "").strip():
            description_text = str(description.get("content") or "").strip()
            selection = "meta_description"
            locators = ["meta[name=description][content]"]
            locators_truncated = False
            text, source_text_sha256, source_text_char_length = _capture_bounded_text(
                (description_text,), MAX_PUBLIC_BODY_CHARS,
            )
        else:
            text_parts = _iter_node_text_parts(soup.body, include_chrome=True) if soup.body else ()
            text, source_text_sha256, source_text_char_length = _capture_bounded_text(
                text_parts, MAX_PUBLIC_BODY_CHARS,
            )
            selection = "document_body" if source_text_char_length else "none"
            locators = ["body"] if source_text_char_length else []
            locators_truncated = False
        truncated = source_text_char_length > MAX_PUBLIC_BODY_CHARS
        if selection == "semantic_blocks":
            completeness = "TRUNCATED_SEMANTIC_PREVIEW" if truncated else "COMPLETE_SEMANTIC_TEXT"
        elif selection == "meta_description":
            completeness = "TRUNCATED_DESCRIPTION" if truncated else "DESCRIPTION_EXCERPT"
        elif selection == "document_body":
            completeness = "TRUNCATED_DOCUMENT_BODY" if truncated else "DOCUMENT_BODY_TEXT"
        else:
            completeness = "EMPTY"
        published, date_source, date_state = _publication_signals(soup)
        item_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:32]
        return {
            "platform_content_id": f"public-http:{item_id}",
            "title": title,
            "content": str(text),
            "author_id": None,
            "author_nickname": None,
            "publish_datetime": published,
            "url": canonical_url,
            "likes": None,
            "comments": None,
            "collects": None,
            "shares": None,
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "raw": {
                "content_type": "text/html", "canonical_url": canonical_url,
                "publication_date_source": date_source,
                "publication_date_state": date_state,
                "content_observation": {
                    "selection": selection,
                    "selected_locators": locators,
                    "selected_locator_count": len(locators),
                    "selected_locators_truncated": locators_truncated,
                    "selected_block_count": len(selected_nodes),
                    "source_text_sha256": source_text_sha256,
                    "source_text_char_length": source_text_char_length,
                    "returned_text_char_length": len(text),
                    "truncated": truncated,
                    "completeness": completeness,
                    "document_sha256": hashlib.sha256(response.content).hexdigest(),
                    "document_byte_length": len(response.content),
                },
            },
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
                    "publication_date_source": item["raw"]["publication_date_source"],
                    "publication_date_state": item["raw"]["publication_date_state"],
                    **public_source_provenance(response, target),
                },
            )
        except (PublicSourceError, ValueError) as exc:
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="当前公开页面暂时无法读取，请稍后重试",
                metadata={"provider": "public_http", **public_source_error_metadata(exc)},
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
