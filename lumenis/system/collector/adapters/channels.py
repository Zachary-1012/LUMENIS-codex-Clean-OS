"""WeChat Channels public share/profile documents; official APIs are optional.

Public acquisition never decodes protected video streams, exports sessions,
uses shop APIs as public search, or switches backend after a denial. An exact
public URL is a source identity even when its native object ID is not exposed.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import AccessClass, BasePlatformAdapter, CollectionResult, CollectionStatus
from .platform_naming import map_raw_to_normalized
from .public_source import fetch_public_url, PublicSourceError, public_source_error_metadata, public_source_provenance
from .browser import read_public_document, select_public_transport
from .registry import register_adapter


class _Failure(Exception):
    def __init__(self, status, code, **metadata):
        self.status, self.code, self.metadata = status, code, metadata
        super().__init__(code)


class ChannelsAdapter(BasePlatformAdapter):
    platform = "channels"
    enabled = False
    monitor_priority = "optional"
    RAW_CONTENT_TABLE = "channels_videos"
    RAW_COMMENT_TABLE = "channels_comments"
    _PUBLIC_BACKEND = "channels_public_document"

    def __init__(self, *, provider_config: Mapping[str, Any] | None = None,
                 public_fetcher=None, public_discovery=None, **kwargs):
        super().__init__(**kwargs)
        self._provider_mode = dict(provider_config or {}).get("provider_mode") or "public"
        self._public_transport = dict(provider_config or {}).get("public_transport")
        self._use_server_configuration = provider_config is None
        self._fetcher = public_fetcher or fetch_public_url
        self._discovery = public_discovery

    def capability_map(self):
        return {name: "implemented" for name in
                ("search", "detail", "comments", "author", "author_posts", "healthcheck")}

    def normalize_to_platform_contents(self, raw_record):
        result = map_raw_to_normalized(raw_record, self.platform)
        if result.get("platform_content_id") is None:
            result["platform_content_id"] = raw_record.get("source_content_id")
        result["native_identity_state"] = raw_record.get("native_identity_state")
        result["media_list"] = raw_record.get("media_list")
        return result

    @staticmethod
    def _url(value):
        parsed = urlsplit(str(value))
        if (parsed.scheme != "https" or parsed.hostname not in {"weixin.qq.com", "channels.weixin.qq.com"}
                or parsed.username or parsed.password or parsed.port not in {None, 443}
                or parsed.hostname == "weixin.qq.com" and not parsed.path.startswith("/sph/")
                or any(x in parsed.path for x in ("/login", "/auth/", "/cgi-bin/"))):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "CHANNELS_EXACT_PUBLIC_SHARE_OR_PROFILE_URL_REQUIRED")
        return parsed._replace(fragment="").geturl()

    @staticmethod
    def _meta(soup, name):
        node = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        return node.get("content") if node else None

    @staticmethod
    def _objects(soup):
        decoder = json.JSONDecoder()
        for script in soup.find_all("script"):
            text = script.string or script.get_text()
            if script.get("type") == "application/ld+json":
                try:
                    decoded = json.loads(text)
                except ValueError:
                    continue
            else:
                found = re.search(r"(?:window\.)?(?:cgiData|__INITIAL_STATE__|__INITIAL_DATA__)\s*=", text)
                if not found:
                    continue
                try:
                    decoded, _ = decoder.raw_decode(text[found.end():].lstrip())
                except ValueError:
                    continue
            stack = [decoded]
            while stack:
                value = stack.pop()
                if isinstance(value, dict):
                    yield value
                    stack.extend(x for x in value.values() if isinstance(x, (dict, list)))
                elif isinstance(value, list):
                    stack.extend(value)

    def _read(self, url, originals, options=None):
        options = options or {}
        url = self._url(url)
        try:
            response, browser = read_public_document(url, originals, fetcher=self._fetcher,
                transport=options.get("_selected_public_transport", "http"), timeout=20,
                allowed_host_suffixes=("weixin.qq.com",),
                browser_plan={"asset_host_suffixes": ("qpic.cn", "res.wx.qq.com", "wx.qlogo.cn"),
                    "capture_paths": (), "max_steps": 1, "cancel_check": options.get("cancel_check")})
        except PublicSourceError as exc:
            metadata = public_source_error_metadata(exc)
            status = metadata.get("http_status")
            raise _Failure(CollectionStatus.NEED_VERIFY if getattr(exc, "failure_type", None) == "PUBLIC_BROWSER_VERIFICATION" else CollectionStatus.COOLING_DOWN if status == 429 else
                CollectionStatus.BLOCKED if status in {401, 403, 451} else CollectionStatus.PROVIDER_UNAVAILABLE,
                "CHANNELS_PUBLIC_SOURCE_UNAVAILABLE", **metadata) from None
        self._url(response.url)
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        if (soup.select_one("#captcha, .verify-page, form[action*='login']")
                or any(word in title for word in ("安全验证", "环境异常", "登录微信", "扫码登录"))):
            raise _Failure(CollectionStatus.NEED_VERIFY, "CHANNELS_PUBLIC_LOGIN_OR_VERIFICATION_REQUIRED")
        return response, soup

    def _post(self, response, soup, observed):
        objects = list(self._objects(soup))
        video = next((x for x in objects if x.get("@type") == "VideoObject"), {})
        native = next((x for x in objects if any(x.get(key) is not None for key in ("objectId", "object_id", "feedId"))
                       and any(x.get(key) is not None for key in ("description", "desc", "title"))), {})
        query = parse_qs(urlsplit(response.url).query)
        ident = next((native[key] for key in ("objectId", "object_id", "feedId") if type(native.get(key)) in {str, int}), None)
        if ident is None:
            ident = next((query[key][0] for key in ("objectId", "object_id", "feedId") if query.get(key)), None)
        ident = str(ident) if ident is not None else None
        body = soup.select_one(".feed-description, .feed-desc, #feed-desc, [data-field='description']")
        text = native.get("description") or native.get("desc") or video.get("description") or (
            body.get_text("\n", strip=True) if body else self._meta(soup, "og:description"))
        title = native.get("title") or video.get("name") or self._meta(soup, "og:title")
        if not isinstance(text, str) or not text.strip():
            if not isinstance(title, str) or not title.strip():
                raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "CHANNELS_PUBLIC_SHARE_CONTENT_NOT_EXPOSED")
            text = None
        if title in {"微信视频号", "视频号", "WeChat Channels"} and text is None:
            raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "CHANNELS_PUBLIC_SHARE_REQUIRES_WECHAT_CLIENT")
        author = video.get("author") if isinstance(video.get("author"), dict) else {}
        author_id = native.get("finderUserName") or native.get("username") or native.get("authorId")
        author_name = native.get("nickname") or native.get("authorName") or author.get("name")
        media = []
        for key, value in (("coverUrl", native.get("coverUrl")), ("thumbUrl", native.get("thumbUrl")),
                           ("JSONLD.thumbnailUrl", video.get("thumbnailUrl")), ("og:image", self._meta(soup, "og:image")),
                           ("JSONLD.contentUrl", video.get("contentUrl"))):
            for candidate in value if isinstance(value, list) else [value]:
                if isinstance(candidate, str) and candidate.startswith(("https://", "http://")):
                    media.append({"kind": "video" if key == "JSONLD.contentUrl" else "image", "url": candidate, "locator": key})
        for index, node in enumerate(soup.select("video[src], video source[src]")):
            if isinstance(node.get("src"), str) and node["src"].startswith(("https://", "http://")):
                media.append({"kind": "video", "url": node["src"], "locator": f"video/source[{index}].src"})
        source_id = ident or "public-url:" + hashlib.sha256(response.url.encode()).hexdigest()
        published = video.get("uploadDate") or video.get("datePublished")
        raw = {"object_id": ident, "source_content_id": source_id, "native_identity_state":
            "NATIVE_OBJECT_ID_OBSERVED" if ident else "PUBLIC_URL_IDENTITY_ONLY",
            "source_identity_kind": "NATIVE_OBJECT_ID" if ident else "PUBLIC_URL_SHA256",
            "author_id": author_id, "author_name": author_name, "author_profile_url": author.get("url"),
            "desc": text, "title": title, "url": response.url, "create_time": published,
            "native_create_time": native.get("createTime"), "publication_time_state": "NATIVE_DATE" if published else "NOT_EXPOSED_OR_UNIT_UNKNOWN",
            "like_count": None, "comment_count": None, "share_count": None, "collect_count": None, "view_count": None,
            "media_list": media, "media_type": "video" if video or media else None,
            "captured_at": observed, "collected_at": observed,
            "body_state": "PUBLIC_DESCRIPTION" if text is not None else "PUBLIC_TITLE_ONLY"}
        return {"platform_content_id": source_id, "title": title, "content": text, "author_id": author_id,
            "author_nickname": author_name, "publish_datetime": published, "url": response.url,
            "likes": None, "comments": None, "shares": None, "collects": None,
            "cover": next((x["url"] for x in media if x["kind"] == "image"), None),
            "media_list": media, "captured_at": observed, "raw": raw}

    def _result(self, capability, items, originals, *, error=None, cursor=None, next_cursor=None, comments=False, complete=False, extra=None):
        backend = "channels_public_browser" if (extra or {}).get("public_transport") == "browser" else self._PUBLIC_BACKEND
        page = {"request_cursor": cursor, "next_cursor": next_cursor, "page_complete": error is None,
            "exhausted": complete and error is None, "coverage_scope": "PUBLIC_DOCUMENT_VISIBLE_ONLY", "continuation_is_authorization": False}
        return CollectionResult(error.status if error else CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
            self.platform, items=[] if comments else items, comments=items if comments else [], raw_count=len(items),
            message=error.code if error else "视频号公开页面来源已读取",
            metadata={"provider": backend, "provider_mode": "public", "pagination": page, "source_page": page,
                "coverage_complete": complete and error is None, "write_enabled": False,
                **(extra or {}), **({"error_code": error.code, **error.metadata} if error else {})},
            provenance=public_source_provenance(originals[0], originals[0].requested_url or originals[0].url) if originals else {},
            attempted_backend=backend, attempted_access_class=AccessClass.Z0_PUBLIC,
            backend=backend if originals else None, access_class=AccessClass.Z0_PUBLIC if originals else None,
            capability=capability, actual_access_state="SOURCE_OBSERVED" if originals else "NOT_OBSERVED", original_response=originals or None)

    def _unavailable_official(self, capability):
        return CollectionResult(CollectionStatus.NOT_SUPPORTED, self.platform, capability=capability,
            message="视频号通用公开内容官方API合同未核实；公开页面入口独立可用",
            attempted_backend="wechat_channels_official_api", attempted_access_class=AccessClass.Z2_OFFICIAL_API,
            actual_access_state="NOT_ATTEMPTED", metadata={"provider": "wechat_channels_official_api",
                "provider_mode": "official", "can_attempt": False, "network_attempted": False,
                "error_code": "OFFICIAL_PUBLIC_CONTENT_COLLECTION_API_NOT_PROVIDED",
                "own_shop_api_is_public_collection": False})

    def _dispatch(self, capability, value=None, **kwargs):
        originals, items, error, next_cursor, complete = [], [], None, None, False
        cursor, extra = kwargs.get("cursor"), {}
        try:
            mode = kwargs.pop("provider_mode", None)
            if mode is None and self._use_server_configuration:
                from config import get_config
                mode = get_config().get("LUMENIS_CHANNELS_PROVIDER_MODE")
            mode = mode or self._provider_mode
            if mode == "official":
                return self._unavailable_official(capability)
            if mode != "public":
                raise _Failure(CollectionStatus.COLLECT_ERROR, "PROVIDER_MODE_INVALID")
            transport = select_public_transport("channels", kwargs, configured=self._public_transport,
                use_server=self._use_server_configuration)
            kwargs["_selected_public_transport"] = transport
            extra["public_transport"] = transport
            if capability == "healthcheck":
                return CollectionResult(CollectionStatus.SUCCESS, self.platform, capability=capability,
                    attempted_backend=self._PUBLIC_BACKEND, attempted_access_class=AccessClass.Z0_PUBLIC,
                    message="视频号公开链接入口，不需要平台API授权",
                    metadata={"provider": self._PUBLIC_BACKEND, "provider_mode": "public", "can_attempt": True,
                        "requires_authorization": False, "network_attempted": False, "source_access": "NOT_VERIFIED"})
            if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
            request_hash = hashlib.sha256(json.dumps([capability, str(value), bool(kwargs.get("include_replies")), transport], ensure_ascii=False).encode()).hexdigest()
            if cursor is not None:
                if (not isinstance(cursor, dict) or cursor.get("kind") != "channels.public_document.v1"
                        or cursor.get("request_hash") != request_hash or not isinstance(cursor.get("urls"), list)):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "CHANNELS_PUBLIC_CURSOR_SCOPE_MISMATCH")
                urls = [self._url(url) for url in cursor["urls"]]
            elif capability == "search" and not str(value).startswith("https://"):
                from .google import GoogleAdapter
                limit = kwargs.get("max_results", 5)
                limit = max(1, min(limit, 10)) if type(limit) is int else 5
                found = (self._discovery or GoogleAdapter()).search(f"site:weixin.qq.com/sph/ {value}", max_results=limit)
                if not found.ok:
                    raise _Failure(found.status, "CHANNELS_PUBLIC_LINK_DISCOVERY_UNAVAILABLE")
                urls = [self._url(item["url"]) for item in found.items if isinstance(item.get("url"), str)
                        and urlsplit(item["url"]).hostname == "weixin.qq.com" and urlsplit(item["url"]).path.startswith("/sph/")]
                extra.update(discovery_provider="EXISTING_REGISTERED_GOOGLE_DISCOVERY", discovery_snippets_are_original_body=False)
                if not urls:
                    return self._result(capability, [], [], extra={**extra, "source_state": "NO_PUBLIC_SHARE_LINKS_RETURNED_BY_DISCOVERY"})
            else:
                urls = [self._url(value)]
            remaining = list(urls)
            budget = kwargs.get("max_pages", 5 if capability == "search" else 1)
            budget = max(1, min(budget, 25)) if type(budget) is int else 1
            for url in urls[:budget]:
                response, soup = self._read(url, originals, kwargs)
                observed = datetime.now(timezone.utc).isoformat()
                if capability == "author":
                    data = next((x for x in self._objects(soup) if x.get("@type") in {"Person", "Organization"}), {})
                    name = data.get("name")
                    native = next((x for x in self._objects(soup) if x.get("finderUserName") and x.get("nickname")), {})
                    ident = native.get("finderUserName")
                    name = native.get("nickname") or name
                    if not ident or not name:
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "CHANNELS_PUBLIC_AUTHOR_IDENTITY_NOT_EXPOSED")
                    aliases = [str(ident)]
                    items.append({"platform_content_id": str(ident), "author_id": str(ident), "author_nickname": name,
                        "title": name, "content": data.get("description"), "url": response.url, "captured_at": observed,
                        "native_author_aliases": aliases, "raw": {"record_kind": "author", "author_id": str(ident),
                            "native_author_aliases": aliases, "profile_url": response.url}})
                    complete = True
                elif capability == "author_posts" and not (cursor is not None and cursor.get("stage") == "post_links"):
                    links = []
                    for anchor in soup.select("a[href]"):
                        target = urljoin(response.url, anchor["href"])
                        parsed = urlsplit(target)
                        if parsed.hostname == "weixin.qq.com" and parsed.path.startswith("/sph/"):
                            target = self._url(target)
                            if target not in links:
                                links.append(target)
                    if not links:
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "CHANNELS_PUBLIC_AUTHOR_POSTS_NOT_EXPOSED")
                    for target in links[:5]:
                        post_response, post_soup = self._read(target, originals, kwargs)
                        items.append(self._post(post_response, post_soup, observed))
                    if links[5:]:
                        next_cursor = {"kind": "channels.public_document.v1", "request_hash": request_hash, "urls": links[5:], "stage": "post_links"}
                elif capability == "comments":
                    source_query = parse_qs(urlsplit(response.url).query)
                    parent_content = next((source_query[key][0] for key in ("objectId", "object_id", "feedId") if source_query.get(key)), None)
                    if parent_content is None:
                        parent_content = "public-url:" + hashlib.sha256(response.url.encode()).hexdigest()
                    for node in soup.select("[data-comment-id], .comment-item[data-id]"):
                        ident = node.get("data-comment-id") or node.get("data-id")
                        parent = node.get("data-parent-comment-id")
                        body = node.select_one(".comment-content, .comment-text, [data-field='content']")
                        if not ident or body is None or parent and not kwargs.get("include_replies"):
                            continue
                        author = node.select_one(".comment-author, [data-field='nickname']")
                        time = node.select_one("time[datetime]")
                        items.append({"platform_comment_id": str(ident), "parent_content_id": parent_content,
                            "parent_comment_id": str(parent) if parent else None, "reply_to_comment_id": str(parent) if parent else None,
                            "content": body.get_text("\n", strip=True), "author_id": node.get("data-author-id"),
                            "author_nickname": author.get_text(" ", strip=True) if author else None,
                            "publish_datetime": time.get("datetime") if time else None, "likes": None,
                            "url": response.url, "captured_at": observed, "raw": {"public_dom_attributes": dict(node.attrs)}})
                    if not items:
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "CHANNELS_PUBLIC_COMMENTS_NOT_EXPOSED")
                    extra["continuation_state"] = "PUBLIC_VISIBLE_COMMENTS_ONLY"
                else:
                    items.append(self._post(response, soup, observed))
                    complete = capability == "detail"
                remaining.pop(0)
                for anchor in soup.select("a[rel~='next'][href]"):
                    remaining.append(self._url(urljoin(response.url, anchor["href"])))
            if remaining:
                next_cursor = {"kind": "channels.public_document.v1", "request_hash": request_hash, "urls": remaining,
                               "stage": "post_links" if capability == "author_posts" else "document"}
                complete = False
        except (_Failure, PublicSourceError, ValueError) as exc:
            error = exc if isinstance(exc, _Failure) else _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_CHANNELS_PUBLIC_INPUT")
        return self._result(capability, items, originals, error=error, cursor=cursor, next_cursor=next_cursor,
            comments=capability == "comments", complete=complete, extra=extra)

    def search(self, keyword, **kwargs):
        return self._dispatch("search", keyword, **kwargs)

    def detail(self, content_id, **kwargs):
        return self._dispatch("detail", content_id, **kwargs)

    def comments(self, content_id, *, include_replies=False, **kwargs):
        return self._dispatch("comments", content_id, include_replies=include_replies, **kwargs)

    def creator(self, creator_id, **kwargs):
        return self._dispatch("author", creator_id, **kwargs)

    def author_posts(self, author_id, **kwargs):
        return self._dispatch("author_posts", author_id, **kwargs)

    def health_check(self, **kwargs):
        return self._dispatch("healthcheck", **kwargs)


register_adapter("channels", ChannelsAdapter)
