"""Anonymous Tieba HTML behind the existing bounded public transport.

Only returned public HTML, data-field attributes and native pager links are
read. A login/challenge, changed DOM, private endpoint or missing author history
is an explicit unavailable state. Public DOM/Vue-prop extraction adapts OpenCLI
clis/tieba/read.js, search.js and utils.js, Copyright 2025 jackwener,
Apache-2.0, commit aeaff2b796efabb7fd46654112418ab61fcae917
(https://github.com/jackwener/OpenCLI). Modified for full text/native IDs/nulls,
public native pager URLs and Source custody. Signed page_pc, COOKIE exports,
floor-as-comment-identity and fake zero defaults are excluded.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import json
import re
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlsplit

from bs4 import BeautifulSoup, Comment

from .base import AccessClass, BasePlatformAdapter, CollectionResult, CollectionStatus
from .public_source import (PublicSourceError, fetch_public_url,
                            public_source_error_metadata, public_source_provenance)
from .registry import register_adapter
from .browser import read_public_document, select_public_transport


# Adapted from OpenCLI buildExtractReadEvaluate/buildExtractSearchResultsEvaluate.
# These are read-only source-owned expressions, not user-supplied JavaScript.
_TIEBA_PUBLIC_DOM_SCRIPT = r"""() => {
  const text = node => node ? (node.innerText || node.textContent || '').trim() : null;
  const props = node => node?.__vue__ ? (node.__vue__._props || node.__vue__.$props || {}) : {};
  const nativeId = value => /^(?:\d+)$/.test(String(value ?? '')) ? String(value) : null;
  const postId = value => nativeId(value.post_id ?? value.postId ?? value.pid);
  const structuredText = content => Array.isArray(content)
    ? content.map(part => typeof part?.text === 'string' ? part.text : '').join('') : null;
  const contentNode = document.querySelector('.pb-content-wrap');
  const contentProps = props(contentNode);
  const mainUser = document.querySelector('.head-line.user-info:not(.no-extra-margin)');
  const mainProps = props(mainUser);
  const titleNode = document.querySelector('.pb-title-wrap.pc-pb-title');
  const media = node => Array.from(node?.querySelectorAll('img[src],img[data-original],video[src],video source[src]') || [])
    .map(asset => ({kind:asset.tagName === 'IMG' ? 'image' : 'video',url:asset.getAttribute('data-original') || asset.getAttribute('src')}));
  const main = contentNode ? {title:props(titleNode).title || text(titleNode),
    content:text(contentNode.querySelector('.pb-content-item .text')) || text(contentNode) || structuredText(contentProps.content),
    post_id:postId(contentProps),author:text(mainUser?.querySelector('.head-name')) || mainProps.userShowInfo?.[0]?.text?.text || null,
    user_id:nativeId(mainProps.user_id ?? mainProps.userInfo?.user_id),
    native_time:mainProps.descInfo?.time ?? null,visible_time:text(mainUser?.querySelector('.time')),
    media:media(contentNode)} : null;
  const replies = Array.from(document.querySelectorAll('.pb-comment-item')).map(node => {
    const own = props(node),content = node.querySelector('.comment-content'),author = node.querySelector('.head-name');
    const business = props(node.querySelector('.action-bar-container')).businessInfo || {};
    return {post_id:postId(own) || postId(business),author:text(author),
      user_id:nativeId(own.user_id ?? own.userInfo?.user_id),content:text(content),media:media(content),
      floor:(text(node.querySelector('.comment-desc-left')) || '').match(/第(\d+)楼/)?.[1] || null,
      visible_time:text(node.querySelector('.comment-desc-left')),native_time:own.time ?? null};
  });
  const search = Array.from(document.querySelectorAll('.threadcardclass.thread-new3.index-feed-cards')).map(node => {
    const business = props(node.querySelector('.action-bar-container.search-action-bar')).businessInfo || {};
    const forum = text(node.querySelector('.forum-name-text,.forum-name'));
    const meta = text(node.querySelector('.user-forum-info')) || '';
    const withoutForum = forum && meta.startsWith(forum) ? meta.slice(forum.length).trim() : meta;
    const match = withoutForum.match(/^(.*?)\s*发布于\s*(.+)$/);
    return {thread_id:nativeId(business.thread_id),url:node.querySelector('a[href*="/p/"]')?.href || null,
      title:text(node.querySelector('.title-wrap,.title-content-wrap')),
      content:text(node.querySelector('.title-content-wrap,.abstract-wrap')),
      author:match ? match[1].trim() : withoutForum || null,time:match ? match[2].trim() : null,forum};
  });
  return {page_meta:{pathname:location.pathname,pn:new URLSearchParams(location.search).get('pn')},main,replies,search};
}"""


class _Failure(Exception):
    def __init__(self, status, code, **metadata):
        self.status, self.code, self.metadata = status, code, metadata
        super().__init__(code)


def _text(value):
    return value if isinstance(value, str) and value.strip() else None


def _bound(value, default, maximum):
    return max(1, min(value, maximum)) if isinstance(value, int) and not isinstance(value, bool) else default


def _native_id(value):
    return str(value) if type(value) in {str, int} and re.fullmatch(r"[0-9]+", str(value)) else None


class TiebaAdapter(BasePlatformAdapter):
    platform = "tieba"
    enabled = False
    monitor_priority = "optional"
    _ORIGIN = "https://tieba.baidu.com"

    def __init__(self, *, public_fetcher=None, provider_config: Mapping[str, Any] | None = None, **kwargs):
        super().__init__(**kwargs)
        self._fetcher = public_fetcher or fetch_public_url
        self._public_transport = dict(provider_config or {}).get("public_transport")
        self._provider_mode = dict(provider_config or {}).get("provider_mode") or "public"
        self._use_server_configuration = provider_config is None
        self._timeout = _bound(dict(provider_config or {}).get("timeout_seconds"), 20, 60)

    def capability_map(self):
        return {name: "implemented" for name in
                ("search", "detail", "comments", "author", "author_posts", "healthcheck")}

    @staticmethod
    def normalize_to_platform_contents(raw_record):
        return {"platform": "tieba", "platform_content_id": raw_record.get("tid"),
                "author_id": raw_record.get("user_id"), "author_name": raw_record.get("user_name"),
                "title": raw_record.get("title"), "content": raw_record.get("content"),
                "published_at": raw_record.get("create_time"), "url": raw_record.get("url"),
                "like_count": raw_record.get("agree_count"), "comment_count": raw_record.get("reply_num"),
                "collect_count": None, "share_count": None, "view_count": None,
                "media_list": raw_record.get("media_list"), "collected_at": raw_record.get("captured_at"),
                "raw_data": raw_record}

    @classmethod
    def _url(cls, value, path=None):
        parsed = urlsplit(urljoin(cls._ORIGIN, str(value)))
        if (parsed.scheme != "https" or parsed.hostname != "tieba.baidu.com" or parsed.port not in {None, 443}
                or parsed.username or parsed.password or parsed.fragment and not parsed.fragment.isdigit()
                or path is not None and parsed.path != path):
            raise _Failure(CollectionStatus.BLOCKED, "TIEBA_PUBLIC_URL_SCOPE_MISMATCH")
        return parsed._replace(fragment="").geturl()

    @classmethod
    def _thread_id(cls, value):
        value = str(value).strip()
        if value.startswith(("https://", "/p/")):
            parsed = urlsplit(cls._url(value))
            match = re.fullmatch(r"/p/([0-9]+)", parsed.path)
            value = match[1] if match else ""
        if not re.fullmatch(r"[0-9]{1,30}", value):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_THREAD_ID_REQUIRED")
        return value

    def _read(self, url, originals, options=None):
        options = options if options is not None else {}
        url = self._url(url)
        try:
            mode = options.get("provider_mode") or self._provider_mode
            if mode != "public":
                raise _Failure(CollectionStatus.NOT_SUPPORTED if mode == "official" else CollectionStatus.COLLECT_ERROR,
                    "TIEBA_OFFICIAL_PROVIDER_NOT_IMPLEMENTED" if mode == "official" else "PROVIDER_MODE_INVALID")
            if "_selected_public_transport" not in options:
                options["_selected_public_transport"] = select_public_transport("tieba", options,
                    configured=self._public_transport, use_server=self._use_server_configuration)
            response, browser = read_public_document(url, originals, fetcher=self._fetcher,
                transport=options["_selected_public_transport"], timeout=self._timeout, max_bytes=2 * 1024 * 1024,
                allowed_host_suffixes=("tieba.baidu.com",), browser_plan={
                    "asset_host_suffixes": ("bdstatic.com", "baidustatic.com", "tbimg.com", "hiphotos.baidu.com"),
                    "capture_paths": (r"/p/(?:comment|totalComment)",),
                    "request_keys": ("tid", "pid", "pn"), "max_steps": 1,
                    "cancel_check": options.get("cancel_check"), "extraction_script": _TIEBA_PUBLIC_DOM_SCRIPT})
            if browser:
                options.setdefault("_browser_observations", []).append(browser)
        except PublicSourceError as exc:
            metadata = public_source_error_metadata(exc)
            status = metadata.get("http_status")
            raise _Failure(CollectionStatus.NEED_VERIFY if getattr(exc, "failure_type", None) == "PUBLIC_BROWSER_VERIFICATION" else CollectionStatus.COOLING_DOWN if status == 429 else
                           CollectionStatus.BLOCKED if status in {401, 403, 451} else
                           CollectionStatus.PROVIDER_UNAVAILABLE, "TIEBA_PUBLIC_SOURCE_UNAVAILABLE", **metadata) from None
        final = self._url(response.url)
        if urlsplit(final).path != urlsplit(url).path:
            raise _Failure(CollectionStatus.NEED_VERIFY, "TIEBA_PUBLIC_PAGE_REDIRECTED")
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        if (soup.select_one("form[action*='wappass'], form[action*='verify'], #captcha, .verify-page")
                or any(x in title for x in ("安全验证", "百度安全验证", "访问验证", "登录百度帐号"))):
            raise _Failure(CollectionStatus.NEED_VERIFY, "TIEBA_LOGIN_OR_VERIFICATION_REQUIRED")
        # Tieba can place the same returned public markup inside HTML comments.
        # This only parses bytes already returned, and never executes scripts.
        for node in list(soup.find_all(string=lambda x: isinstance(x, Comment))):
            if any(token in str(node) for token in ('class="l_post ', 'class="s_post"', 'class="thread_name"')):
                node.replace_with(BeautifulSoup(str(node), "html.parser"))
        return soup, response

    @staticmethod
    def _data(node):
        value = node.get("data-field") if node else None
        if not value:
            return {}
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_INVALID_NATIVE_DATA_FIELD") from None
        if not isinstance(decoded, dict):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_INVALID_NATIVE_DATA_FIELD")
        return decoded

    @classmethod
    def _next(cls, soup, current, *, path, query_key=None, query_value=None):
        for anchor in soup.select("a[href]"):
            text = anchor.get_text(" ", strip=True)
            rel = anchor.get("rel") or []
            classes = anchor.get("class") or []
            if not ("next" in rel or "j_pager_next" in classes or "pager_next" in classes or text in {"下一页", "下页", "下一页>"}):
                continue
            value = cls._url(urljoin(current, anchor["href"]), path)
            query = parse_qs(urlsplit(value).query)
            if query_key and query.get(query_key, [None])[0] != query_value:
                raise _Failure(CollectionStatus.BLOCKED, "TIEBA_PAGER_QUERY_SCOPE_MISMATCH")
            if value == current:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_REPEATED_NATIVE_PAGE")
            return value
        return None

    @staticmethod
    def _media(node):
        media = []
        for i, image in enumerate(node.select("img[src], img[data-original]")):
            src = image.get("data-original") or image.get("src")
            if isinstance(src, str) and src.startswith(("https://", "http://")):
                media.append({"kind": "image", "url": src, "locator": f"content img[{i}]." +
                              ("data-original" if image.get("data-original") else "src")})
        for i, video in enumerate(node.select("video[src], video source[src]")):
            src = video.get("src")
            if isinstance(src, str) and src.startswith(("https://", "http://")):
                media.append({"kind": "video", "url": src, "locator": f"content video/source[{i}].src"})
        return media

    @classmethod
    def _floors(cls, soup, tid, observed, modern=None):
        floors = []
        for node in soup.select(".l_post[data-field]"):
            data = cls._data(node)
            content = data.get("content") if isinstance(data.get("content"), dict) else {}
            author = data.get("author") if isinstance(data.get("author"), dict) else {}
            ident = _native_id(content.get("post_id"))
            body = node.select_one(".d_post_content, .j_d_post_content")
            if not ident or body is None:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_NATIVE_POST_OR_BODY_MISSING")
            tail = node.select(".tail-info")
            # Only an actual source timestamp is retained; capture time is separate.
            date = content.get("date") or next((x.get_text(" ", strip=True) for x in tail
                if re.fullmatch(r"\d{4}-\d\d-\d\d(?:\s+\d\d:\d\d(?::\d\d)?)?", x.get_text(" ", strip=True))), None)
            media = cls._media(body)
            raw = {**data, "native_data_field": data, "tid": tid, "post_id": ident, "user_id": _native_id(author.get("user_id")),
                   "user_name": author.get("user_name"), "content": body.get_text("\n", strip=True),
                   "create_time": date, "media_list": media, "captured_at": observed,
                   "source_locator": f'.l_post[data-field] content.post_id={ident}',
                   "post_no": content.get("post_no"), "comment_num": content.get("comment_num"),
                   "url": f"https://tieba.baidu.com/p/{tid}?pid={ident}#{ident}"}
            floors.append({"platform_comment_id": ident, "parent_content_id": tid,
                "parent_comment_id": None, "reply_to_comment_id": None, "author_id": raw["user_id"],
                "author_nickname": author.get("user_name"), "content": raw["content"], "publish_datetime": date,
                "likes": None, "url": raw["url"], "media_list": media, "captured_at": observed, "raw": raw})
        if not floors and isinstance(modern, dict):
            meta = modern.get("page_meta", {})
            if meta.get("pathname") != f"/p/{tid}":
                raise _Failure(CollectionStatus.BLOCKED, "TIEBA_RENDERED_THREAD_IDENTITY_MISMATCH")
            rows = [(modern.get("main"), True), *((row, False) for row in modern.get("replies", []))]
            for native, is_main in rows:
                if not isinstance(native, dict):
                    continue
                ident = _native_id(native.get("post_id"))
                if not ident:
                    continue
                body = _text(native.get("content"))
                media = [asset for asset in native.get("media", []) if isinstance(asset, dict)
                    and isinstance(asset.get("url"), str) and asset["url"].startswith(("http://", "https://"))]
                date = native.get("visible_time")
                raw = {"native_public_vue_fields": native, "tid": tid, "post_id": ident,
                    "user_id": _native_id(native.get("user_id")), "user_name": native.get("author"),
                    "content": body, "create_time": date, "native_time": native.get("native_time"),
                    "post_no": 1 if is_main else native.get("floor"), "comment_num": None,
                    "media_list": media, "captured_at": observed, "url": f"https://tieba.baidu.com/p/{tid}?pid={ident}",
                    "source_locator": ".pb-content-wrap" if is_main else ".pb-comment-item"}
                floors.append({"platform_comment_id": ident, "parent_content_id": tid,
                    "parent_comment_id": None, "reply_to_comment_id": None, "author_id": raw["user_id"],
                    "author_nickname": raw["user_name"], "content": body, "publish_datetime": date,
                    "likes": None, "url": raw["url"], "media_list": media, "captured_at": observed, "raw": raw})
        return floors

    @staticmethod
    def _modern(options):
        reads = options.get("_browser_observations", [])
        return reads[-1].extraction if reads else {}

    def _result(self, capability, items, originals, *, cursor=None, next_cursor=None,
                error=None, comments=False, extra=None, pagination_known=True, options=None):
        transport = (options or {}).get("_selected_public_transport", "http")
        mode = (options or {}).get("provider_mode") or self._provider_mode
        official = mode == "official"
        backend = "tieba_official_api" if official else "tieba_public_browser" if transport == "browser" else "tieba_public_html"
        complete = next_cursor is None and error is None and pagination_known
        page = {"request_cursor": cursor, "next_cursor": next_cursor,
                "exhausted": complete if pagination_known else None, "page_complete": error is None,
                "coverage_scope": "ANONYMOUS_PUBLIC_HTML_VISIBLE", "continuation_is_authorization": False}
        provenance = public_source_provenance(originals[0], originals[0].requested_url or originals[0].url) if originals else {}
        return CollectionResult(error.status if error else CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
            self.platform, items=[] if comments else items, comments=items if comments else [], raw_count=len(items),
            message=error.code if error else "Tieba public HTML observations returned",
            metadata={"provider": backend, "provider_mode": mode, "public_transport": transport if not official else None, "pagination": page, "source_page": page,
                "coverage_complete": complete, "write_enabled": False,
                **(extra or {}), **({"error_code": error.code, **error.metadata} if error else {})},
            provenance=provenance, access_class=AccessClass.Z0_PUBLIC if originals else None,
            backend=backend if originals else None, capability=capability,
            attempted_access_class=AccessClass.Z2_OFFICIAL_API if official else AccessClass.Z0_PUBLIC, attempted_backend=backend,
            actual_access_state="SOURCE_OBSERVED" if originals else "NOT_OBSERVED", original_response=originals or None)

    def search(self, keyword: str, **kwargs):
        originals, items, cursor, error = [], [], kwargs.get("cursor"), None
        next_url, known = None, True
        try:
            if not _text(keyword) or len(keyword) > 512:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_SEARCH_QUERY_REQUIRED")
            if cursor is not None:
                if not isinstance(cursor, dict) or cursor.get("kind") != "tieba.search.v1" or cursor.get("keyword") != keyword:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_SEARCH_CURSOR_SCOPE_MISMATCH")
                url = self._url(cursor.get("url"), "/f/search/res")
                if parse_qs(urlsplit(url).query).get("qw") != [keyword]:
                    raise _Failure(CollectionStatus.BLOCKED, "TIEBA_SEARCH_CURSOR_QUERY_MISMATCH")
            else:
                url = self._ORIGIN + "/f/search/res?" + urlencode({"isnew": 1, "qw": keyword, "only_thread": 1,
                    "rn": min(30, _bound(kwargs.get("max_results"), 10, 1000)), "pn": 1})
            for _ in range(_bound(kwargs.get("max_pages"), 1, 50)):
                if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                    raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
                next_url = url
                soup, response = self._read(url, originals, kwargs)
                rows = soup.select(".s_post")
                modern = self._modern(kwargs).get("search", [])
                if not rows and not modern and not soup.select_one(".s_post_list, .s_empty, .s_noresult, .search-no-result, .search-nodata, .no-result"):
                    raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "TIEBA_SEARCH_NOT_EXPOSED_IN_PUBLIC_HTML")
                for row in rows:
                    anchor = row.select_one(".p_title a[href], a.bluelink[href]")
                    if anchor is None:
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_SEARCH_NATIVE_LINK_MISSING")
                    source_url = self._url(anchor["href"])
                    tid = self._thread_id(source_url)
                    body = row.select_one(".p_content")
                    author = row.select_one(".p_author a[href*='/home/'], a[href*='/home/main']")
                    date = row.select_one(".p_date")
                    raw = {"tid": tid, "title": anchor.get_text(" ", strip=True),
                        "content": body.get_text("\n", strip=True) if body else None,
                        "user_id": None, "user_name": author.get_text(" ", strip=True) if author else None,
                        "author_profile_url": self._url(author["href"]) if author else None,
                        "create_time": date.get_text(" ", strip=True) if date else None,
                        "url": source_url, "captured_at": datetime.now(timezone.utc).isoformat(),
                        "content_coverage": "PUBLIC_SEARCH_SNIPPET", "source_locator": ".s_post"}
                    items.append({"platform_content_id": tid, "title": raw["title"], "content": raw["content"],
                        "author_id": None, "author_nickname": raw["user_name"], "publish_datetime": raw["create_time"],
                        "url": source_url, "captured_at": raw["captured_at"], "raw": raw})
                if not rows:
                    for row in modern:
                        if not isinstance(row, dict):
                            continue
                        tid = _native_id(row.get("thread_id"))
                        source_url = self._url(row["url"]) if row.get("url") else f"{self._ORIGIN}/p/{tid}" if tid else None
                        if source_url:
                            source_tid = self._thread_id(source_url)
                            if tid and source_tid != tid:
                                raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_SEARCH_NATIVE_IDENTITY_MISMATCH")
                            tid = source_tid
                        if not tid or not _text(row.get("title")):
                            raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "TIEBA_SEARCH_NATIVE_IDENTITY_NOT_EXPOSED")
                        observed = datetime.now(timezone.utc).isoformat()
                        raw = {"tid": tid, "title": row["title"], "content": row.get("content"),
                            "user_id": None, "user_name": row.get("author"), "create_time": row.get("time"),
                            "forum_name": row.get("forum"), "url": source_url, "captured_at": observed,
                            "native_public_vue_fields": row, "content_coverage": "PUBLIC_SEARCH_SNIPPET",
                            "source_locator": ".threadcardclass.thread-new3.index-feed-cards"}
                        items.append({"platform_content_id": tid, "title": raw["title"], "content": raw["content"],
                            "author_id": None, "author_nickname": raw["user_name"], "publish_datetime": raw["create_time"],
                            "url": source_url, "captured_at": observed, "raw": raw})
                next_url = self._next(soup, response.url, path="/f/search/res", query_key="qw", query_value=keyword)
                # Current Vue search has no proven public next-page control.
                # Do not invent pn+1 or present the visible window as coverage.
                known = not modern and bool(rows or soup.select_one(".s_post_list, .s_empty, .s_noresult"))
                if next_url is None or len(items) >= _bound(kwargs.get("max_results"), 10, 1000):
                    break
                url = next_url
        except _Failure as exc:
            error = exc
        continuation = {"kind": "tieba.search.v1", "keyword": keyword, "url": next_url} if next_url else None
        return self._result("search", items, originals, cursor=cursor, next_cursor=continuation, error=error, pagination_known=known, options=kwargs)

    def detail(self, content_id: str, **kwargs):
        originals, items, error = [], [], None
        try:
            tid = self._thread_id(content_id)
            soup, _ = self._read(f"{self._ORIGIN}/p/{tid}?pn=1", originals, kwargs)
            modern = self._modern(kwargs)
            floors = self._floors(soup, tid, datetime.now(timezone.utc).isoformat(), modern)
            first = next((x for x in floors if str(x["raw"].get("post_no")) == "1"), None)
            if first is None:
                native = modern.get("main", {})
                if (modern.get("page_meta", {}).get("pathname") != f"/p/{tid}" or not isinstance(native, dict)
                        or not _text(native.get("content"))):
                    raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "TIEBA_ORIGINAL_POST_NOT_EXPOSED_PUBLICLY")
                # The thread ID is observed in the exact public page URL. A
                # hidden floor pid remains unknown; it is never synthesized.
                observed = datetime.now(timezone.utc).isoformat()
                first = {"content": native["content"], "author_id": _native_id(native.get("user_id")),
                    "author_nickname": native.get("author"), "publish_datetime": native.get("visible_time"),
                    "media_list": native.get("media") or [], "captured_at": observed,
                    "raw": {"tid": tid, "post_id": None, "user_id": _native_id(native.get("user_id")),
                        "user_name": native.get("author"), "content": native["content"], "create_time": native.get("visible_time"),
                        "native_time": native.get("native_time"), "captured_at": observed,
                        "native_public_vue_fields": native, "source_locator": ".pb-content-wrap"}}
            title = soup.select_one("h3.core_title_txt, h1.core_title_txt, .core_title_txt")
            title_text = (title.get("title") or title.get_text(" ", strip=True)) if title else modern.get("main", {}).get("title")
            raw = {**first["raw"], "title": title_text, "reply_num": None, "agree_count": None,
                   "url": f"{self._ORIGIN}/p/{tid}"}
            reply = soup.select_one(".l_reply_num")
            if reply:
                match = re.search(r"([0-9]+)\s*(?:回复贴|回复)", reply.get_text(" ", strip=True))
                if match:
                    raw["reply_num"] = int(match[1])
            items.append({"platform_content_id": tid, "title": title_text, "content": first["content"],
                "author_id": first["author_id"], "author_nickname": first["author_nickname"],
                "publish_datetime": first["publish_datetime"], "url": raw["url"], "likes": None,
                "comments": raw["reply_num"], "shares": None, "collects": None,
                "cover": first["media_list"][0]["url"] if first["media_list"] else None,
                "media_list": first["media_list"], "captured_at": first["captured_at"], "raw": raw})
        except _Failure as exc:
            error = exc
        return self._result("detail", items, originals, error=error, options=kwargs)

    def _replies(self, tid, entry, originals, options=None):
        pid, pn = _native_id(entry.get("post_id")), entry.get("pn")
        if not pid or type(pn) is not int or pn < 1:
            raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_INVALID_NATIVE_REPLY_CURSOR")
        soup, _ = self._read(self._ORIGIN + "/p/comment?" + urlencode({"tid": tid, "pid": pid, "pn": pn}), originals, options)
        rows = soup.select(".lzl_single_post[data-field]")
        if not rows and not soup.select_one(".lzl_cnt, .lzl_content_main"):
            raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "TIEBA_REPLIES_NOT_EXPOSED_PUBLICLY")
        result = []
        for row in rows:
            data = self._data(row)
            ident = _native_id(data.get("spid") or data.get("comment_id"))
            body = row.select_one(".lzl_content_main")
            author = row.select_one(".j_user_card, .lzl_p_p a")
            date = row.select_one(".lzl_time")
            if not ident or body is None:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_NATIVE_REPLY_ID_OR_BODY_MISSING")
            name = author.get_text(" ", strip=True) if author else data.get("user_name")
            result.append({"platform_comment_id": ident, "parent_content_id": tid, "parent_comment_id": pid,
                "reply_to_comment_id": _native_id(data.get("reply_to_comment_id")), "author_id": _native_id(data.get("user_id")),
                "author_nickname": name, "content": body.get_text("\n", strip=True),
                "publish_datetime": date.get_text(" ", strip=True) if date else None, "likes": None,
                "url": f"{self._ORIGIN}/p/{tid}?pid={pid}#{pid}", "captured_at": datetime.now(timezone.utc).isoformat(),
                "raw": {**data, "tid": tid, "parent_post_id": pid, "source_locator": ".lzl_single_post[data-field]"}})
        next_page = None
        for anchor in soup.select(".lzl_pager a[data-index], a.j_pager_next[data-index]"):
            if anchor.get_text(" ", strip=True) in {"下一页", "下页", ">"} or "j_pager_next" in (anchor.get("class") or []):
                value = anchor.get("data-index")
                if not isinstance(value, str) or not value.isdigit() or int(value) <= pn:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_INVALID_NEXT_REPLY_PAGE")
                next_page = int(value)
                break
        return result, {"post_id": pid, "pn": next_page} if next_page else None

    def comments(self, content_id: str, *, include_replies=False, **kwargs):
        originals, items, pending, cursor, error = [], [], [], kwargs.get("cursor"), None
        url, done, tid = None, False, None
        try:
            tid = self._thread_id(content_id)
            url = f"{self._ORIGIN}/p/{tid}?pn=1"
            if cursor is not None:
                if (not isinstance(cursor, dict) or cursor.get("kind") != "tieba.comments.v1" or cursor.get("tid") != tid
                        or cursor.get("include_replies") is not include_replies or type(cursor.get("thread_done")) is not bool
                        or not isinstance(cursor.get("pending_replies"), list) or any(not isinstance(x, dict) for x in cursor["pending_replies"])):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_COMMENT_CURSOR_SCOPE_MISMATCH")
                url = self._url(cursor.get("thread_url"), f"/p/{tid}") if cursor.get("thread_url") else None
                done = cursor["thread_done"]
                pending = [dict(x) for x in cursor["pending_replies"]]
            for _ in range(_bound(kwargs.get("max_pages"), 10, 100)):
                if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                    raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
                if pending:
                    replies, continuation = self._replies(tid, pending[0], originals, kwargs)
                    items.extend(replies)
                    pending.pop(0)
                    if continuation:
                        pending.insert(0, continuation)
                elif not done:
                    if not url:
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_THREAD_PAGE_CURSOR_MISSING")
                    soup, response = self._read(url, originals, kwargs)
                    modern = self._modern(kwargs)
                    floors = self._floors(soup, tid, datetime.now(timezone.utc).isoformat(), modern)
                    if not floors:
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "TIEBA_COMMENT_FLOORS_NOT_EXPOSED")
                    items.extend(x for x in floors if str(x["raw"].get("post_no")) != "1")
                    if include_replies:
                        for floor in floors:
                            count = floor["raw"].get("comment_num")
                            if count is None or str(count).isdigit() and int(count) > 0:
                                pending.append({"post_id": floor["platform_comment_id"], "pn": 1})
                    url = self._next(soup, response.url, path=f"/p/{tid}")
                    done = url is None
                else:
                    break
                if len(items) >= _bound(kwargs.get("max_results"), 100, 2000):
                    break
        except _Failure as exc:
            error = exc
        next_cursor = ({"kind": "tieba.comments.v1", "tid": tid, "include_replies": include_replies,
                        "thread_url": url, "thread_done": done, "pending_replies": pending}
                       if tid and (not done or pending) else None)
        return self._result("comments", items, originals, cursor=cursor, next_cursor=next_cursor,
                            error=error, comments=True, options=kwargs,
                            pagination_known=not bool(self._modern(kwargs)))

    def _profile_url(self, value):
        value = str(value).strip()
        if value.startswith(("https://", "/home/")):
            url = self._url(value, "/home/main")
            params = parse_qs(urlsplit(url).query)
            if not (params.get("id") or params.get("un")):
                raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_NATIVE_PROFILE_ID_REQUIRED")
            return url
        if value.startswith("un:") and _text(value[3:]) and len(value) <= 128:
            return self._ORIGIN + "/home/main?un=" + quote(value[3:], safe="")
        raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_NATIVE_PROFILE_URL_OR_EXPLICIT_USERNAME_REQUIRED")

    def creator(self, creator_id: str, **kwargs):
        originals, items, error = [], [], None
        try:
            url = self._profile_url(creator_id)
            soup, _ = self._read(url, originals, kwargs)
            profile = soup.select_one(".userinfo, .userinfo_wrap, .user_wrap")
            if profile is None:
                raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "TIEBA_AUTHOR_NOT_EXPOSED_PUBLICLY")
            name = profile.select_one(".userinfo_username, .userinfo_title, .user_name")
            data = self._data(profile)
            identity = _native_id(data.get("user_id"))
            native_name = data.get("user_name")
            username_node = profile.select_one(".userinfo_username, .user_name")
            if native_name is None and username_node is not None:
                native_name = username_node.get_text(" ", strip=True)
            aliases = [value for value in (identity, data.get("portrait"), native_name) if _text(value)]
            if _text(native_name):
                aliases.append("un:" + native_name)
            items.append({"platform_content_id": identity if identity is not None else url, "author_id": identity,
                "author_nickname": name.get_text(" ", strip=True) if name else None, "title": None,
                "native_author_aliases": aliases,
                "content": None, "url": url, "captured_at": datetime.now(timezone.utc).isoformat(),
                "raw": {**data, "record_kind": "author", "profile_url": url, "native_author_aliases": aliases,
                        "username": native_name,
                        "source_locator": ".userinfo, .userinfo_wrap, .user_wrap"}})
        except _Failure as exc:
            error = exc
        return self._result("author", items, originals, error=error, extra={"record_kind": "author"}, options=kwargs)

    def author_posts(self, author_id: str, **kwargs):
        originals, items, cursor, error, next_url = [], [], kwargs.get("cursor"), None, None
        try:
            base_url = self._profile_url(author_id)
            if cursor is not None and (not isinstance(cursor, dict) or cursor.get("kind") != "tieba.author_posts.v1"
                    or cursor.get("profile_url") != base_url):
                raise _Failure(CollectionStatus.COLLECT_ERROR, "TIEBA_AUTHOR_CURSOR_SCOPE_MISMATCH")
            url = self._url(cursor["url"], "/home/main") if cursor else base_url
            base_query = parse_qs(urlsplit(base_url).query)
            for key in ("id", "un"):
                if key in base_query and parse_qs(urlsplit(url).query).get(key) != base_query[key]:
                    raise _Failure(CollectionStatus.BLOCKED, "TIEBA_AUTHOR_PAGER_IDENTITY_MISMATCH")
            for _ in range(_bound(kwargs.get("max_pages"), 1, 50)):
                if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                    raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
                next_url = url
                soup, response = self._read(url, originals, kwargs)
                nodes = soup.select(".thread_name a[href], .n_title a[href], .thread_list a[href*='/p/']")
                if not nodes:
                    raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "TIEBA_AUTHOR_HISTORY_NOT_EXPOSED_PUBLICLY")
                seen = set()
                for anchor in nodes:
                    target = self._url(anchor["href"])
                    tid = self._thread_id(target)
                    if tid in seen:
                        continue
                    seen.add(tid)
                    raw = {"tid": tid, "title": anchor.get_text(" ", strip=True), "content": None,
                        "user_id": None, "user_name": None, "url": target,
                        "captured_at": datetime.now(timezone.utc).isoformat(), "profile_url": base_url,
                        "content_coverage": "PUBLIC_AUTHOR_HISTORY_LINK", "source_locator": ".thread_name/.n_title/.thread_list a"}
                    items.append({"platform_content_id": tid, "title": raw["title"], "content": None,
                        "author_id": None, "author_nickname": None, "publish_datetime": None,
                        "url": target, "captured_at": raw["captured_at"], "raw": raw})
                identity_key = "id" if "id" in base_query else "un"
                next_url = self._next(soup, response.url, path="/home/main",
                    query_key=identity_key, query_value=base_query[identity_key][0])
                if next_url is None or len(items) >= _bound(kwargs.get("max_results"), 20, 1000):
                    break
                url = next_url
        except _Failure as exc:
            error = exc
        continuation = {"kind": "tieba.author_posts.v1", "profile_url": base_url, "url": next_url} if next_url else None
        return self._result("author_posts", items, originals, cursor=cursor, next_cursor=continuation, error=error, options=kwargs)

    def health_check(self, **kwargs):
        if (kwargs.get("provider_mode") or self._provider_mode) == "official":
            return self._result("healthcheck", [], [], error=_Failure(CollectionStatus.NOT_SUPPORTED,
                "TIEBA_OFFICIAL_PROVIDER_NOT_IMPLEMENTED"), options=kwargs)
        return CollectionResult(CollectionStatus.SUCCESS, self.platform,
            message="Tieba anonymous public HTML provider available; current page access remains unverified",
            metadata={"provider": "tieba_public_html", "provider_mode": "public", "can_attempt": True, "network_attempted": False,
                      "authorization_verification": "NOT_VERIFIED", "write_enabled": False}, capability="healthcheck")


register_adapter("tieba", TiebaAdapter)
