from __future__ import annotations

import hashlib
from io import StringIO
import json
import re
import threading
import time
from datetime import datetime
from typing import Any, Callable
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Comment, NavigableString

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .public_source import (
    PublicResponse, PublicSourceError, PublicSourceHTTPError, fetch_public_url,
    public_source_error_metadata, public_source_provenance,
)
from .registry import register_adapter
from ..guard.rate_limiter import AdaptiveRateLimiter


MAX_PUBLIC_BODY_CHARS = 16_000
MAX_PUBLIC_LOCATOR_CHARS = 512
MAX_PUBLIC_LOCATOR_TOTAL_CHARS = 16_384
MAX_PUBLIC_MEDIA_REFERENCES = 256
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
                or _has_navigation_role(parent)
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


def _has_navigation_role(element: Any) -> bool:
    """ARIA role is a space-separated token list (e.g. "navigation presentation")."""
    get = getattr(element, "get", None)
    if get is None:
        return False
    return "navigation" in str(get("role") or "").lower().split()


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
        if _has_navigation_role(node):
            continue
        # A page-level <form> wrapper is common in server-rendered pages; only
        # form roots are rejected, not semantic articles inside a form.
        if node.find_parent(("nav", "header", "footer", "aside")):
            continue
        if any(_has_navigation_role(parent) for parent in node.parents):
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


def _public_dom_media(soup, selected_nodes, document_url, media_schema='public-http-dom-media/v2'):
    """Retain media in the fetched DOM without resolving or fetching a hint."""
    from .wechat import _public_media_hint_url
    roots = selected_nodes or ([soup.body] if soup.body is not None else [])
    base_url = document_url
    base = soup.find('base', href=True)
    if base is not None:
        base_url = _public_media_hint_url(base.get('href'), document_url) or document_url
    references, total, seen_elements = [], 0, set()

    def add(tag, value, media_type, *, attribute, role='MEDIA_RESOURCE', descriptor=None):
        nonlocal total
        total += 1
        if len(references) >= MAX_PUBLIC_MEDIA_REFERENCES:
            return
        observed = _public_media_hint_url(value, base_url)
        reference = {
            'media_type': media_type, 'native_tag': tag.name,
            'url': observed if role in {'MEDIA_RESOURCE', 'COVER'} else None,
            'url_role': role, 'native_locator': {'element': _node_locator(tag), 'attribute': attribute},
            'observation_kind': 'NATIVE_DOM_MEDIA_REFERENCE', 'bytes_state': 'NOT_ACQUIRED',
            'url_state': 'OBSERVED' if observed else 'NO_USABLE_PUBLIC_URL',
        }
        if descriptor is not None:
            reference['native_locator']['srcset_descriptor'] = descriptor
        if role == 'EMBED_PAGE':
            reference['observed_page_url'] = observed
            if media_schema == 'public-http-dom-media/v2' and observed:
                parts = urlsplit(observed)
                known_player = (parts.hostname in {'youtube.com','www.youtube.com','www.youtube-nocookie.com'}
                                and parts.path.startswith('/embed/')
                                or parts.hostname == 'player.vimeo.com' and parts.path.startswith('/video/')
                                or parts.hostname == 'player.bilibili.com' and parts.path.startswith('/player'))
                if known_player:
                    reference.update(url=observed,media_type='video',
                        acquisition={'extractor_key':'Generic','representation':'PLAYER_SOURCE','protocol':'https'})
        elif role == 'TIMED_TEXT':
            reference['observed_text_url'] = observed
        if (media_schema == 'public-http-dom-media/v2' and reference['url']
                and role == 'MEDIA_RESOURCE' and media_type in {'audio','video'}):
            path = urlsplit(observed).path.lower()
            declared_type = str(tag.get('type') or '').lower()
            protocol = ('m3u8' if path.endswith('.m3u8') or declared_type in
                        {'application/vnd.apple.mpegurl','application/x-mpegurl','audio/mpegurl'}
                        else 'dash' if path.endswith('.mpd') or declared_type == 'application/dash+xml' else None)
            if protocol:
                reference['acquisition'] = {'extractor_key':'Generic','representation':'STREAM_MANIFEST','protocol':protocol}
        reference['native_attributes'] = {key: str(tag[key])[:1000]
            for key in ('id', 'alt', 'title', 'type', 'width', 'height', 'media', 'kind', 'srclang', 'label')
            if isinstance(tag.get(key), str) and tag[key].strip()}
        references.append(reference)

    def primary(tag):
        return next(((key, tag[key]) for key in ('data-src', 'data-original', 'data-lazy-src', 'src')
                     if isinstance(tag.get(key), str) and tag[key].strip()), None)

    def srcset(tag, media_type):
        attribute = 'data-srcset' if tag.get('data-srcset') else 'srcset'
        value = tag.get(attribute)
        if not isinstance(value, str) or not value.strip():
            return False
        retained = False
        cursor = 0
        while cursor < len(value):
            while cursor < len(value) and (value[cursor].isspace() or value[cursor] == ','):
                cursor += 1
            start = cursor
            while cursor < len(value) and not value[cursor].isspace():
                cursor += 1
            token = value[start:cursor]
            if not token:
                break
            trailing_separator = token.endswith(',')
            url = token.rstrip(',')
            descriptor = ''
            if not trailing_separator:
                start = cursor
                while cursor < len(value) and value[cursor] != ',':
                    cursor += 1
                descriptor = value[start:cursor].strip()
            if descriptor and re.fullmatch(
                    r'(?:[1-9][0-9]*w|(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)x)', descriptor) is None:
                continue
            add(tag, url, media_type, attribute=attribute, descriptor=descriptor or None)
            retained = True
        return retained

    def eligible(tag, root):
        current = tag
        while current is not None:
            if (current.name in {'nav', 'header', 'footer', 'aside', 'form', 'template', 'noscript'}
                    or _has_navigation_role(current) or current.get('hidden') is not None
                    or str(current.get('aria-hidden') or '').lower() == 'true'):
                return False
            if current is root:
                return True
            current = current.parent
        return False

    for root in roots:
        for tag in root.select('img, video, audio, iframe'):
            if id(tag) in seen_elements or not eligible(tag, root):
                continue
            seen_elements.add(id(tag))
            source = primary(tag)
            if tag.name == 'img':
                if source is not None:
                    add(tag, source[1], 'image', attribute=source[0])
                had_srcset = srcset(tag, 'image')
                picture = tag.find_parent('picture')
                if picture is not None:
                    for picture_source in picture.select('source'):
                        had_srcset = srcset(picture_source, 'image') or had_srcset
                if source is None and not had_srcset:
                    add(tag, None, 'image', attribute='src')
            elif tag.name in {'video', 'audio'}:
                if source is not None:
                    add(tag, source[1], tag.name, attribute=source[0])
                sources = tag.select('source')
                for child in sources:
                    candidate = primary(child)
                    add(child, candidate[1] if candidate else None, tag.name,
                        attribute=candidate[0] if candidate else 'src')
                if source is None and not sources:
                    add(tag, None, tag.name, attribute='src')
                poster = tag.get('poster') or tag.get('data-cover')
                if poster:
                    add(tag, poster, 'image', attribute='poster', role='COVER')
                for track in tag.select('track'):
                    candidate = primary(track)
                    add(track, candidate[1] if candidate else None, 'timed_text',
                        attribute=candidate[0] if candidate else 'src', role='TIMED_TEXT')
            else:
                add(tag, source[1] if source else None, 'embed',
                    attribute=source[0] if source else 'src', role='EMBED_PAGE')
    return references, {
        'schema': media_schema,
        'scope': 'SELECTED_CONTENT_DOM' if selected_nodes else 'DOCUMENT_BODY_DOM',
        'reference_count': total, 'retained_reference_count': len(references),
        'omitted_reference_count': total - len(references),
        'truncated': total > len(references), 'bytes_acquired': False,
        'dynamic_content_executed': False, 'copyright_license': 'NOT_ESTABLISHED',
    }


def has_observed_media_source(item):
    """A fetched media document may legitimately have no body text.

    This projection grants no acquisition rights. The original reader first
    recomputes the DOM fields from the retained HTTP response before using it.
    """
    raw=item.get('raw') or item.get('source_raw') or item
    observation=raw.get('media_observation')
    if (not isinstance(observation,dict) or observation.get('schema') not in {
            'public-http-dom-media/v1','public-http-dom-media/v2'}
            or observation.get('bytes_acquired') is not False):
        return False
    for media in raw.get('media_list') or []:
        if (not isinstance(media,dict) or media.get('media_type') not in {'image','video','audio'}
                or media.get('observation_kind')!='NATIVE_DOM_MEDIA_REFERENCE'
                or media.get('url_role') not in {'MEDIA_RESOURCE','EMBED_PAGE'}):
            continue
        url=media.get('url')
        if not isinstance(url,str):continue
        parts=urlsplit(url)
        if parts.scheme in {'http','https'} and parts.hostname and not parts.username and not parts.password:
            return True
    return False


class PublicHttpAdapter(BasePlatformAdapter):
    """Keyless public HTML acquisition with an auditable normalized item."""

    platform = "public_http"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, fetcher: Callable[[str], PublicResponse] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._uses_public_transport = fetcher is None
        self.fetcher = fetcher or fetch_public_url

    _document_lock = threading.Lock()
    _document_limiter = AdaptiveRateLimiter(jitter=False)

    def fetch_document(self, url: str, *, allowed_content_types: tuple[str, ...],
                       before_fetch: Callable[[], None] | None = None,
                       check_continue: Callable[[], None] | None = None) -> PublicResponse:
        """Retain one bounded document response through the shared safe transport.

        The caller owns registered-scope and effect admission. This method adds
        no cookies, alternate network client, size override or persistence.
        """
        if not allowed_content_types or not all(isinstance(v, str) for v in allowed_content_types):
            raise ValueError("document content types required")
        if check_continue is not None and not callable(check_continue):
            raise ValueError("document continuation check must be callable")
        # One process-wide original Collector limiter, not a fresh limiter per
        # request. Serialize wait+fetch so concurrent callers cannot burst.
        with self._document_lock:
            limiter = self._document_limiter
            if check_continue is not None:
                check_continue()
            if not limiter.can_run():
                error = PublicSourceError(
                    "public document collector cooling down",
                    reason_code="PUBLIC_SOURCE_LOCAL_COOLDOWN",
                )
                error.failure_type = "LOCAL_COOLDOWN"
                error.retry_after_seconds = max(1, int(limiter.remaining_cooldown() + 0.999))
                raise error

            def is_cancelled() -> bool:
                if check_continue is None:
                    return False
                try:
                    check_continue()
                except InterruptedError:
                    return True
                return False

            def cancellable_sleep(seconds: float) -> None:
                deadline = time.monotonic() + max(0.0, float(seconds))
                while True:
                    check_continue()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return
                    time.sleep(min(0.25, remaining))

            try:
                if check_continue is None:
                    limiter.wait_slot()
                else:
                    limiter.wait_slot(sleep=cancellable_sleep, cancelled=is_cancelled)
            except InterruptedError:
                if check_continue is not None:
                    check_continue()
                raise
            if before_fetch is not None:
                before_fetch()  # authorization may expire while waiting
            if check_continue is not None:
                check_continue()
            try:
                response = (
                    self.fetcher(
                        url, check_continue=check_continue, before_fetch=before_fetch,
                    )
                    if self._uses_public_transport and (
                        check_continue is not None or before_fetch is not None
                    )
                    else self.fetcher(url)
                )
                if (type(response) is PublicResponse
                        and not 200 <= response.status_code < 300):
                    raise PublicSourceHTTPError(response.status_code)
                if (type(response) is not PublicResponse or not 200 <= response.status_code < 300
                        or response.content_type not in allowed_content_types
                        or not 0 < len(response.content) <= 2 * 1024 * 1024):
                    raise PublicSourceError(
                        "unsupported or oversized public document response",
                        network_attempted=self._uses_public_transport and type(response) is PublicResponse,
                    )
            except (PermissionError, InterruptedError):
                raise
            except Exception as exc:
                status_code = getattr(exc, "status_code", None)
                retry_after = getattr(exc, "retry_after_seconds", None)
                is_http_429 = (
                    getattr(exc, "failure_type", None) == "HTTP_STATUS"
                    and status_code == 429
                )
                limiter.on_failure(
                    force_cooldown=is_http_429 and retry_after is None,
                    retry_after=retry_after,
                )
                raise
            limiter.on_success()
            return response

    @staticmethod
    def _item(response: PublicResponse, *, media_schema='public-http-dom-media/v2') -> dict[str, Any]:
        if media_schema not in {'public-http-dom-media/v1','public-http-dom-media/v2'}:
            raise ValueError('PUBLIC_SOURCE_MEDIA_SCHEMA_UNSUPPORTED')
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
        media, media_observation = _public_dom_media(soup, selected_nodes, response.url,media_schema)
        cover = next((entry['url'] for entry in media
                      if entry['media_type'] == 'image' and entry['url']), None)
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
            "cover": cover,
            "media_list": media,
            "captured_at": datetime.now().isoformat(timespec="seconds"),
            "raw": {
                "content_type": "text/html", "canonical_url": canonical_url,
                "publication_date_source": date_source,
                "publication_date_state": date_state,
                "body_state": completeness,
                "body_kind": ("SELECTED_SEMANTIC_DOM_TEXT" if selection == "semantic_blocks"
                              else "DESCRIPTION_EXCERPT" if selection == "meta_description"
                              else "DOCUMENT_BODY_TEXT" if selection == "document_body" else "NO_TEXT"),
                "body_scope": {
                    "representation": "NORMALIZED_TEXT_FROM_FETCHED_HTML",
                    "selection": selection,
                    "selected_dom_text_complete": not truncated and selection != "none",
                    "returned_text_truncated": truncated,
                    "whole_article_verified": False,
                    "dynamic_content_executed": False,
                    "description_is_original_body": False,
                },
                "cover": cover,
                "media_list": media,
                "media_hints": media,
                "media_observation": media_observation,
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
            before_fetch = kwargs.get("before_fetch")
            if before_fetch is not None and not callable(before_fetch):
                raise ValueError("public document admission check must be callable")
            check_continue = kwargs.get("check_continue")
            if check_continue is not None and not callable(check_continue):
                raise ValueError("public document continuation check must be callable")
            response = self.fetch_document(
                target,
                allowed_content_types=("text/html", "application/xhtml+xml"),
                before_fetch=before_fetch,
                check_continue=check_continue,
            )
            item = self._item(response)
            if not item["content"].strip() and not has_observed_media_source(item):
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
                original_response=response,
                metadata={
                    "provider": "public_http",
                    "source": response.url,
                    "collected_at": collected_at,
                    "publication_date_source": item["raw"]["publication_date_source"],
                    "publication_date_state": item["raw"]["publication_date_state"],
                    "body_state": item["raw"]["body_state"],
                    "body_scope": item["raw"]["body_scope"],
                    "media_observation": item["raw"]["media_observation"],
                    "source_representation": "MEDIA_DOCUMENT_WITHOUT_BODY_TEXT" if not item['content'].strip()
                        else "OBSERVED_DOCUMENT_TEXT",
                    **public_source_provenance(response, target),
                },
            )
        except (PermissionError, InterruptedError):
            # Caller-owned Permission and attempt fences must reach the
            # Collector transaction unchanged; they are not provider errors.
            raise
        except (PublicSourceError, ValueError) as exc:
            metadata = {"provider": "public_http", **public_source_error_metadata(exc)}
            if getattr(exc, "failure_type", None) == "LOCAL_COOLDOWN":
                metadata.update(
                    error_type="PUBLIC_DOCUMENT_COOLDOWN",
                    retry_after_seconds=exc.retry_after_seconds,
                    network_attempted=False,
                )
                return CollectionResult(
                    status=CollectionStatus.COOLING_DOWN,
                    platform=self.platform,
                    message="公开来源处于本地冷却时间内，系统已暂缓请求",
                    metadata=metadata,
                )
            status_code = getattr(exc, "status_code", None)
            retry_after = getattr(exc, "retry_after_seconds", None)
            is_retryable_http_wait = (
                getattr(exc, "failure_type", None) == "HTTP_STATUS"
                and (status_code == 429 or type(retry_after) is int and retry_after > 0)
            )
            if is_retryable_http_wait:
                if type(retry_after) is not int or retry_after <= 0:
                    retry_after = max(
                        1, int(self._document_limiter.remaining_cooldown() + 0.999)
                    )
                metadata.update(
                    retry_after_seconds=retry_after,
                    network_attempted=True,
                )
                return CollectionResult(
                    status=CollectionStatus.COOLING_DOWN,
                    platform=self.platform,
                    message="来源暂缓当前请求，系统会按来源给出的等待时间继续",
                    metadata=metadata,
                )
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="当前公开页面暂时无法读取，请稍后重试",
                metadata=metadata,
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
        return self.search(target, **kwargs)

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
