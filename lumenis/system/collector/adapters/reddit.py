"""Reddit public web documents and explicitly selected approved OAuth Data API.

The Data API requires approved OAuth; anonymous HTML is an independent chosen
provider, never a fallback after denial. No anonymous JSON API or enrollment.
Deletion/retention obligations are carried to the existing Source owner.

Adapted public search-card identity/media helpers: OpenCLI clis/reddit/web-search.js
and read.js, Copyright 2025 jackwener, Apache-2.0, commit
aeaff2b796efabb7fd46654112418ab61fcae917 (https://github.com/jackwener/OpenCLI).
Modified for anonymous documents, full text, native IDs/cursors and signed net
votes. COOKIE/JSON-API hydration, morechildren replay, truncation and fake zero
defaults from the upstream command are not used.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import html
import json
import re
from typing import Any
from urllib.parse import quote, urlencode, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from .base import AccessClass, BasePlatformAdapter, CollectionResult, CollectionStatus
from .platform_naming import map_raw_to_normalized
from .registry import register_adapter
from .public_source import fetch_public_url, PublicSourceError, public_source_error_metadata, public_source_provenance
from .browser import read_public_document, select_public_transport


class _Failure(Exception):
    def __init__(self, status, code, **metadata):
        self.status, self.code, self.metadata = status, code, metadata
        super().__init__(code)


def _text(value):
    return value if isinstance(value, str) and value.strip() else None


def _bound(value, default, maximum):
    return max(1, min(value, maximum)) if isinstance(value, int) and not isinstance(value, bool) else default


def _utc(value):
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value, timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            return None
    return None


class RedditAdapter(BasePlatformAdapter):
    platform = "reddit"
    enabled = False
    monitor_priority = "optional"
    RAW_CONTENT_TABLE = "reddit_posts"
    RAW_COMMENT_TABLE = "reddit_comments"
    RAW_USER_TABLE = "reddit_subreddits"
    _ORIGIN = "https://oauth.reddit.com"

    def __init__(self, *, provider_config: Mapping[str, Any] | None = None,
                 oauth_token=None, http_client=None, public_fetcher=None, **kwargs):
        super().__init__(**kwargs)
        self._config = dict(provider_config or {})
        self._provider_mode = self._config.get("provider_mode") or "public"
        self._public_transport = self._config.get("public_transport")
        self._public_fetcher = public_fetcher
        self._use_server_configuration = provider_config is None and oauth_token is None
        self._configuration_error = False
        self._token = oauth_token if oauth_token is not None else self._config.get("oauth_token")
        self._client = http_client
        self._timeout = _bound(self._config.get("timeout_seconds"), 20, 60)
        self._rate = {}
        self._refresh_configuration()

    def _refresh_configuration(self):
        if not self._use_server_configuration:
            return
        try:
            from config import get_config
            owner = get_config()
            keys = {"oauth_token": "LUMENIS_REDDIT_OAUTH_TOKEN", "oauth_scopes": "LUMENIS_REDDIT_OAUTH_SCOPES",
                    "user_agent": "LUMENIS_REDDIT_USER_AGENT", "api_approval_ref": "LUMENIS_REDDIT_API_APPROVAL_REF",
                    "allowed_use": "LUMENIS_REDDIT_ALLOWED_USE", "commercial_approval_ref": "LUMENIS_REDDIT_COMMERCIAL_APPROVAL_REF",
                    "timeout_seconds": "LUMENIS_REDDIT_TIMEOUT_SECONDS"}
            self._config = {field: owner.get(key) for field, key in keys.items()}
            self._token = self._config["oauth_token"]
            self._timeout = _bound(self._config["timeout_seconds"], 20, 60)
            self._configuration_error = False
        except Exception:
            self._config, self._token = {}, None
            self._configuration_error = True

    def capability_map(self):
        return {name: "implemented" for name in
                ("search", "detail", "comments", "author", "author_posts", "healthcheck")}

    def normalize_to_platform_contents(self, raw_record):
        result = map_raw_to_normalized(raw_record, self.platform)
        result["url"] = raw_record.get("source_url") or result.get("url")
        result["published_at"] = _utc(raw_record.get("created_utc"))
        result["like_count"] = None
        result["net_votes"] = raw_record.get("score") if type(raw_record.get("score")) is int else None
        result["metric_semantics"] = {"net_votes": "UPVOTES_MINUS_DOWNVOTES_NOT_LIKES"}
        if isinstance(raw_record.get("media_list"), list):
            result["media_list"] = raw_record["media_list"]
        return result

    def _guard(self):
        self._refresh_configuration()
        if self._configuration_error:
            raise _Failure(CollectionStatus.NOT_CONFIGURED, "REDDIT_SERVER_CONFIGURATION_UNAVAILABLE")
        if not _text(self._token):
            raise _Failure(CollectionStatus.NOT_CONFIGURED, "REDDIT_OAUTH_TOKEN_NOT_CONFIGURED")
        if not _text(self._config.get("api_approval_ref")):
            raise _Failure(CollectionStatus.BLOCKED, "REDDIT_APPROVED_API_USE_REQUIRED")
        purpose = self._config.get("allowed_use")
        if purpose not in {"noncommercial", "commercial"}:
            raise _Failure(CollectionStatus.BLOCKED, "REDDIT_APPROVED_PURPOSE_NOT_CONFIGURED")
        if purpose == "commercial" and not _text(self._config.get("commercial_approval_ref")):
            raise _Failure(CollectionStatus.BLOCKED, "REDDIT_COMMERCIAL_AGREEMENT_REQUIRED")
        scopes = self._config.get("oauth_scopes", [])
        scopes = scopes.split() if isinstance(scopes, str) else scopes
        if not isinstance(scopes, (list, tuple, set)) or not ({"read", "*"} & set(scopes)):
            raise _Failure(CollectionStatus.BLOCKED, "REDDIT_READ_SCOPE_REQUIRED")
        agent = self._config.get("user_agent")
        if (not isinstance(agent, str) or len(agent) > 512
                or not re.fullmatch(r"[^\s:]+:[^\s:]+:[^\s]+ \(by /u/[A-Za-z0-9_-]+\)", agent)):
            raise _Failure(CollectionStatus.NOT_CONFIGURED, "REDDIT_DESCRIPTIVE_USER_AGENT_REQUIRED")

    def _read(self, path, params, originals):
        self._guard()
        if self._client is None:
            self._client = requests.Session()
        try:
            response = self._client.get(self._ORIGIN + path, params={**params, "raw_json": 1},
                headers={"Accept": "application/json", "Authorization": f"Bearer {self._token}",
                         "User-Agent": self._config["user_agent"]},
                auth=lambda request: request, timeout=self._timeout, allow_redirects=False)
        except requests.RequestException as exc:
            raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "REDDIT_TRANSPORT_ERROR",
                           error_type=type(exc).__name__) from None
        status = response.status_code
        if status != 200:
            state = (CollectionStatus.SESSION_EXPIRED if status == 401 else
                     CollectionStatus.COOLING_DOWN if status == 429 else
                     CollectionStatus.BLOCKED if status in {403, 451} or 300 <= status < 400 else
                     CollectionStatus.PROVIDER_UNAVAILABLE if status >= 500 else CollectionStatus.COLLECT_ERROR)
            metadata = {"http_status": status}
            retry = response.headers.get("Retry-After")
            if isinstance(retry, str) and retry.isdigit():
                metadata["retry_after_seconds"] = int(retry)
            raise _Failure(state, "REDDIT_API_REQUEST_REJECTED", **metadata)
        try:
            payload = response.json()
        except (ValueError, TypeError):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_API_JSON") from None
        if not isinstance(payload, (list, dict)):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_API_RESPONSE")
        if isinstance(payload, dict):
            if payload.get("error") or (isinstance(payload.get("json"), dict) and payload["json"].get("errors")):
                raise _Failure(CollectionStatus.BLOCKED, "REDDIT_API_ERROR_RESPONSE")
        self._rate = {}
        for header, key in (("X-Ratelimit-Remaining", "remaining"), ("X-Ratelimit-Reset", "reset_seconds"),
                            ("X-Ratelimit-Used", "used")):
            value = response.headers.get(header)
            try:
                self._rate[key] = float(value) if value is not None else None
            except (ValueError, TypeError):
                self._rate[key] = None
        originals.append(payload)
        return payload

    @staticmethod
    def _post_id(value):
        value = str(value).strip()
        if value.startswith("https://"):
            parsed = urlsplit(value)
            if parsed.hostname not in {"reddit.com", "www.reddit.com", "old.reddit.com", "redd.it"}:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_POST_ID")
            parts = parsed.path.strip("/").split("/")
            value = parts[0] if parsed.hostname == "redd.it" else (
                parts[parts.index("comments") + 1] if "comments" in parts and len(parts) > parts.index("comments") + 1 else "")
        value = value.removeprefix("t3_")
        if not re.fullmatch(r"[a-z0-9]{1,20}", value):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_POST_ID")
        return value

    @staticmethod
    def _username(value):
        value = str(value).strip().removeprefix("/u/").removeprefix("u/")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", value):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "REDDIT_USERNAME_REQUIRED")
        return value

    @staticmethod
    def _media(native):
        media, seen = [], set()
        def add(url, locator, kind):
            if not _text(url):
                return
            url = html.unescape(url)
            if url.startswith(("https://", "http://")) and url not in seen:
                seen.add(url)
                media.append({"url": url, "locator": locator, "kind": kind})
        preview = native.get("preview") if isinstance(native.get("preview"), dict) else {}
        for i, image in enumerate(preview.get("images") or []):
            if isinstance(image, dict) and isinstance(image.get("source"), dict):
                add(image["source"].get("url"), f"preview.images[{i}].source.url", "image")
        assets = native.get("media_metadata") if isinstance(native.get("media_metadata"), dict) else {}
        for ident, asset in assets.items():
            source = asset.get("s") if isinstance(asset, dict) and isinstance(asset.get("s"), dict) else {}
            for field in ("u", "gif", "mp4"):
                add(source.get(field), f"media_metadata.{ident}.s.{field}", "video" if field == "mp4" else "image")
        for field in ("secure_media", "media"):
            node = native.get(field) if isinstance(native.get(field), dict) else {}
            video = node.get("reddit_video") if isinstance(node.get("reddit_video"), dict) else {}
            for key in ("fallback_url", "hls_url", "dash_url"):
                add(video.get(key), f"{field}.reddit_video.{key}", "video")
        add(native.get("thumbnail"), "thumbnail", "thumbnail")
        if native.get("post_hint") == "image":
            add(native.get("url_overridden_by_dest"), "url_overridden_by_dest", "image")
        return media

    @classmethod
    def _post(cls, native, observed):
        ident = _text(native.get("id"))
        if not ident:
            raise _Failure(CollectionStatus.COLLECT_ERROR, "POST_NATIVE_ID_MISSING")
        deleted = native.get("selftext") in ("[deleted]", "[removed]") or native.get("removed_by_category") is not None
        author_deleted = native.get("author") in {None, "[deleted]"}
        permalink = native.get("permalink")
        source_url = "https://www.reddit.com" + permalink if isinstance(permalink, str) and permalink.startswith("/") else None
        media = [] if deleted else cls._media(native)
        raw = {**native, "post_id": ident, "source_url": source_url, "media_list": media,
               "captured_at": observed, "collected_at": observed,
               "net_votes": native.get("score") if type(native.get("score")) is int else None,
               "metric_semantics": {"score": "UPVOTES_MINUS_DOWNVOTES_NOT_LIKES"},
               "source_state": "DELETED_OR_REMOVED" if deleted else "OBSERVED"}
        if deleted:
            for field in ("title", "selftext", "selftext_html", "url_overridden_by_dest", "preview", "media",
                          "secure_media", "media_metadata", "thumbnail", "gallery_data"):
                raw[field] = None
        if author_deleted:
            for field in ("author", "author_fullname", "author_flair_text", "author_flair_richtext"):
                raw[field] = None
        return {"platform_content_id": ident, "title": raw.get("title"), "content": raw.get("selftext"),
                "author_id": raw.get("author_fullname"), "author_nickname": raw.get("author"),
                "publish_datetime": _utc(native.get("created_utc")), "url": source_url,
                "likes": None, "net_votes": raw["net_votes"], "comments": native.get("num_comments"),
                "collects": None, "shares": native.get("num_crossposts"),
                "cover": next((m["url"] for m in media if m["kind"] != "video"), None),
                "media_list": media, "captured_at": observed, "raw": raw}

    def _result(self, capability, items, originals, *, cursor=None, next_cursor=None, error=None,
                comments=False, extra=None):
        page = {"request_cursor": cursor, "next_cursor": next_cursor,
                "exhausted": next_cursor is None and error is None, "page_complete": error is None,
                "coverage_scope": "APPROVED_OAUTH_API_VISIBLE_RESOURCES", "continuation_is_authorization": False}
        return CollectionResult(error.status if error else CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
            self.platform, items=[] if comments else items, comments=items if comments else [],
            raw_count=len(items), message=error.code if error else "Reddit authorized OAuth observations returned",
            metadata={"provider": "reddit_official_oauth", "write_enabled": False,
                "source_page": page, "pagination": page,
                "coverage_complete": next_cursor is None and error is None, "rate_limit": dict(self._rate),
                "retention": "REDDIT_DELETION_AND_AUTHOR_REMOVAL_SYNC_REQUIRED",
                "usage_rights": "APPROVED_PURPOSE_ONLY_NOT_MODEL_TRAINING",
                **(extra or {}), **({"error_code": error.code, **error.metadata} if error else {})},
            access_class=AccessClass.Z2_OFFICIAL_API if originals else None,
            backend="reddit_official_oauth" if originals else None, capability=capability,
            attempted_access_class=AccessClass.Z2_OFFICIAL_API, attempted_backend="reddit_official_oauth",
            actual_access_state="SOURCE_OBSERVED" if originals else "NOT_OBSERVED", original_response=originals or None)

    @staticmethod
    def _children(payload):
        data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else None
        if data is None or not isinstance(data.get("children"), list):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_REDDIT_LISTING")
        return data

    def _listing(self, path, params, capability, **kwargs):
        originals, items, error = [], [], None
        cursor, after = kwargs.get("cursor"), None
        fingerprint = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        remaining = _bound(kwargs.get("max_results"), 25, 1000)
        try:
            if cursor is not None:
                if (not isinstance(cursor, dict) or cursor.get("kind") != "reddit.listing.v1" or cursor.get("path") != path
                        or cursor.get("query_hash") != fingerprint or not re.fullmatch(r"t[13]_[a-z0-9]+", str(cursor.get("after", "")))):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "LISTING_CURSOR_SCOPE_MISMATCH")
                after = cursor["after"]
            for _ in range(_bound(kwargs.get("max_pages"), 1, 100)):
                if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                    raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
                data = self._children(self._read(path, {**params, "limit": min(100, remaining), "after": after}, originals))
                for thing in data["children"]:
                    if not isinstance(thing, dict) or thing.get("kind") != "t3" or not isinstance(thing.get("data"), dict):
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "UNEXPECTED_LISTING_OBJECT_KIND")
                    items.append(self._post(thing["data"], datetime.now(timezone.utc).isoformat()))
                next_after = data.get("after")
                if next_after is not None and (not isinstance(next_after, str) or not re.fullmatch(r"t3_[a-z0-9]+", next_after)):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_LISTING_FULLNAME")
                if next_after is not None and after == next_after:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "REPEATED_LISTING_FULLNAME")
                after = next_after
                remaining -= len(data["children"])
                if after is None or remaining <= 0 or self._rate.get("remaining") == 0:
                    break
                if not data["children"]:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "EMPTY_PAGE_WITH_CONTINUATION")
        except _Failure as exc:
            error = exc
        next_cursor = {"kind": "reddit.listing.v1", "path": path, "query_hash": fingerprint, "after": after} if after else None
        return self._result(capability, items, originals, cursor=cursor, next_cursor=next_cursor, error=error)

    def _official_search(self, keyword: str, **kwargs):
        if not _text(keyword):
            return self._result("search", [], [], error=_Failure(CollectionStatus.COLLECT_ERROR, "SEARCH_QUERY_REQUIRED"))
        subreddit = kwargs.get("subreddit")
        if subreddit is not None and not re.fullmatch(r"[A-Za-z0-9_]{2,100}", str(subreddit)):
            return self._result("search", [], [], error=_Failure(CollectionStatus.COLLECT_ERROR, "INVALID_SUBREDDIT"))
        sort, period = kwargs.get("sort", "relevance"), kwargs.get("time_filter", "all")
        if sort not in {"relevance", "hot", "top", "new", "comments"} or period not in {"hour", "day", "week", "month", "year", "all"}:
            return self._result("search", [], [], error=_Failure(CollectionStatus.COLLECT_ERROR, "INVALID_SEARCH_ORDER_OR_PERIOD"))
        return self._listing(f"/r/{subreddit}/search" if subreddit else "/search",
            {"q": keyword, "type": "link", "sort": sort, "t": period, "restrict_sr": bool(subreddit)}, "search", **kwargs)

    def _official_detail(self, content_id: str, **kwargs):
        originals, items, error = [], [], None
        try:
            data = self._children(self._read("/api/info", {"id": "t3_" + self._post_id(content_id)}, originals))
            for thing in data["children"]:
                if not isinstance(thing, dict) or thing.get("kind") != "t3" or not isinstance(thing.get("data"), dict):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_POST_RESPONSE")
                items.append(self._post(thing["data"], datetime.now(timezone.utc).isoformat()))
        except _Failure as exc:
            error = exc
        return self._result("detail", items, originals, error=error)

    @staticmethod
    def _comment(native, link, observed):
        ident = _text(native.get("id"))
        if not ident:
            raise _Failure(CollectionStatus.COLLECT_ERROR, "COMMENT_NATIVE_ID_MISSING")
        parent = native.get("parent_id")
        deleted = native.get("body") in ("[deleted]", "[removed]")
        raw = {**native, "net_votes": native.get("score") if type(native.get("score")) is int else None,
               "metric_semantics": {"score": "UPVOTES_MINUS_DOWNVOTES_NOT_LIKES"}}
        if deleted:
            raw["body"], raw["body_html"] = None, None
        if raw.get("author") in {None, "[deleted]"}:
            raw["author"], raw["author_fullname"] = None, None
        permalink = raw.get("permalink")
        return {"platform_comment_id": native.get("name") or "t1_" + ident, "parent_content_id": link,
                "parent_comment_id": parent if isinstance(parent, str) and parent.startswith("t1_") else None,
                "reply_to_comment_id": parent if isinstance(parent, str) and parent.startswith("t1_") else None,
                "content": raw.get("body"), "author_id": raw.get("author_fullname"),
                "author_nickname": raw.get("author"), "publish_datetime": _utc(raw.get("created_utc")),
                "likes": None, "net_votes": raw["net_votes"], "url": "https://www.reddit.com" + permalink if isinstance(permalink, str) and permalink.startswith("/") else None,
                "captured_at": observed, "source_state": "DELETED_OR_REMOVED" if deleted else "OBSERVED", "raw": raw}

    def _official_comments(self, content_id: str, *, include_replies=False, **kwargs):
        originals, items, pending, seen, seen_more = [], [], [], set(), set()
        cursor, error, link = kwargs.get("cursor"), None, None
        observed = datetime.now(timezone.utc).isoformat()
        sort = kwargs.get("sort", "confidence")
        pages = _bound(kwargs.get("max_pages"), 10, 100)
        def consume(things):
            if not isinstance(things, list):
                raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_COMMENT_TREE")
            for thing in things:
                if not isinstance(thing, dict) or not isinstance(thing.get("data"), dict):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_COMMENT_OBJECT")
                native = thing["data"]
                parent = native.get("parent_id")
                eligible = include_replies or parent == link
                if thing.get("kind") == "more" and eligible:
                    children = native.get("children")
                    if not isinstance(children, list) or any(not isinstance(x, str) or not re.fullmatch(r"[a-z0-9]+", x) for x in children):
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_MORECHILDREN_IDS")
                    entry = ({"children": list(children), "parent_id": parent} if children else
                             {"comment_id": native.get("id"), "parent_id": parent})
                    key = json.dumps(entry, sort_keys=True)
                    if key in seen_more:
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "REPEATED_NATIVE_MORECHILDREN")
                    seen_more.add(key)
                    pending.append(entry)
                elif thing.get("kind") == "t1":
                    if eligible:
                        mapped = self._comment(native, link, observed)
                        if mapped["platform_comment_id"] not in seen:
                            seen.add(mapped["platform_comment_id"])
                            items.append(mapped)
                    replies = native.get("replies")
                    if include_replies and isinstance(replies, dict):
                        consume(self._children(replies)["children"])
                elif thing.get("kind") not in {"t1", "more"}:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "UNEXPECTED_COMMENT_OBJECT_KIND")
        try:
            link = "t3_" + self._post_id(content_id)
            if sort not in {"confidence", "top", "new", "controversial", "old", "random", "qa", "live"}:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_COMMENT_SORT")
            if cursor is not None:
                if (not isinstance(cursor, dict) or cursor.get("kind") != "reddit.comments.v1" or cursor.get("link_fullname") != link
                        or cursor.get("include_replies") is not include_replies or cursor.get("sort") != sort
                        or not isinstance(cursor.get("pending_more"), list) or any(not isinstance(x, dict) for x in cursor["pending_more"])):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "COMMENT_CURSOR_SCOPE_MISMATCH")
                pending = [dict(x) for x in cursor["pending_more"]]
                seen_more = {json.dumps(x, sort_keys=True) for x in pending}
            else:
                response = self._read("/comments/" + link[3:], {"sort": sort, "limit": min(500, _bound(kwargs.get("max_results"), 100, 500)),
                    }, originals)
                if not isinstance(response, list) or len(response) < 2:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_COMMENT_THREAD_RESPONSE")
                consume(self._children(response[1])["children"])
                pages -= 1
            for _ in range(pages):
                if not pending or self._rate.get("remaining") == 0:
                    break
                if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                    raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
                entry = pending[0]
                if isinstance(entry.get("children"), list) and entry["children"]:
                    children = entry["children"]
                    if any(not isinstance(x, str) or not re.fullmatch(r"[a-z0-9]+", x) for x in children):
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_MORECHILDREN_IDS")
                    batch = children[:100]
                    response = self._read("/api/morechildren", {"api_type": "json", "link_id": link,
                        "children": ",".join(batch), "sort": sort}, originals)
                    data = response.get("json", {}).get("data") if isinstance(response, dict) and isinstance(response.get("json"), dict) else None
                    if not isinstance(data, dict) or not isinstance(data.get("things"), list):
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_MORECHILDREN_RESPONSE")
                    pending.pop(0)
                    if children[100:]:
                        pending.insert(0, {**entry, "children": children[100:]})
                    try:
                        consume(data["things"])
                    except _Failure:
                        pending.insert(0, entry)
                        raise
                elif isinstance(entry.get("comment_id"), str) and re.fullmatch(r"[a-z0-9]+", entry["comment_id"]):
                    response = self._read("/comments/" + link[3:], {"comment": entry["comment_id"], "context": 0,
                        "sort": sort, "limit": 100}, originals)
                    if not isinstance(response, list) or len(response) < 2:
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_COMMENT_SUBTREE_RESPONSE")
                    pending.pop(0)
                    try:
                        consume(self._children(response[1])["children"])
                    except _Failure:
                        pending.insert(0, entry)
                        raise
                else:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_COMMENT_CONTINUATION")
        except _Failure as exc:
            error = exc
        next_cursor = {"kind": "reddit.comments.v1", "link_fullname": link, "include_replies": include_replies,
                       "sort": sort, "pending_more": pending} if pending else None
        return self._result("comments", items, originals, cursor=cursor, next_cursor=next_cursor, error=error,
            comments=True, extra={"comment_coverage": "API_VISIBLE_TREE_ONLY", "reply_scope": "NESTED" if include_replies else "TOP_LEVEL"})

    def _official_creator(self, creator_id: str, **kwargs):
        originals, items, error = [], [], None
        try:
            user = self._username(creator_id)
            payload = self._read("/user/" + quote(user, safe="") + "/about", {}, originals)
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, dict) or not _text(data.get("id")):
                raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_AUTHOR_RESPONSE")
            aliases = [value for value in (data.get("id"), "t2_" + data["id"], data.get("name")) if _text(value)]
            items.append({"platform_content_id": "t2_" + data["id"], "author_id": "t2_" + data["id"],
                "author_nickname": data.get("name"),
                "native_author_aliases": aliases,
                "title": data.get("subreddit", {}).get("title") if isinstance(data.get("subreddit"), dict) else None,
                "url": f"https://www.reddit.com/user/{user}", "publish_datetime": _utc(data.get("created_utc")),
                "captured_at": datetime.now(timezone.utc).isoformat(), "raw": {**data, "record_kind": "author",
                    "author_fullname": "t2_" + data["id"], "username": data.get("name"), "native_author_aliases": aliases}})
        except _Failure as exc:
            error = exc
        return self._result("author", items, originals, error=error, extra={"record_kind": "author"})

    def _official_author_posts(self, author_id: str, **kwargs):
        try:
            user = self._username(author_id)
            sort = kwargs.get("sort", "new")
            if sort not in {"hot", "new", "top", "controversial"}:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_AUTHOR_POST_SORT")
            return self._listing("/user/" + quote(user, safe="") + "/submitted", {"sort": sort, "t": "all"},
                                 "author_posts", **kwargs)
        except _Failure as exc:
            return self._result("author_posts", [], [], error=exc)

    def _official_health_check(self, **kwargs):
        try:
            self._guard()
        except _Failure as exc:
            return self._result("healthcheck", [], [], error=exc)
        return CollectionResult(CollectionStatus.SUCCESS, self.platform,
            message="Reddit approved OAuth configuration present; actual resource authorization remains unverified",
            metadata={"provider": "reddit_official_oauth", "can_attempt": True, "network_attempted": False,
                      "authorization_verification": "NOT_VERIFIED", "approved_use": self._config["allowed_use"]},
            capability="healthcheck")


    def _selected_mode(self, kwargs):
        explicit = kwargs.pop("provider_mode", None)
        if explicit is None and self._use_server_configuration:
            from config import get_config
            explicit = get_config().get("LUMENIS_REDDIT_PROVIDER_MODE")
        mode = explicit or self._provider_mode
        if mode not in {"public", "official"}:
            raise _Failure(CollectionStatus.COLLECT_ERROR, "PROVIDER_MODE_INVALID")
        return mode

    def _dispatch(self, capability, value=None, **kwargs):
        try:
            mode = self._selected_mode(kwargs)
        except (ImportError, _Failure) as exc:
            error = exc if isinstance(exc, _Failure) else _Failure(CollectionStatus.NOT_CONFIGURED, "SERVER_CONFIGURATION_UNAVAILABLE")
            return _RedditPublic(self._public_fetcher).result(capability, [], [], error=error)
        if mode == "official":
            method = getattr(self, "_official_" + capability)
            result = method(**kwargs) if capability == "health_check" else method(value, **kwargs)
            result.metadata["provider_mode"] = "official"
            return result
        kwargs.setdefault("_configured_public_transport", self._public_transport)
        kwargs.setdefault("_server_public_transport", self._use_server_configuration)
        return _RedditPublic(self._public_fetcher).read(capability, value, **kwargs)

    def search(self, keyword, **kwargs):
        return self._dispatch("search", keyword, **kwargs)

    def detail(self, content_id, **kwargs):
        return self._dispatch("detail", content_id, **kwargs)

    def comments(self, content_id, *, include_replies=False, **kwargs):
        return self._dispatch("comments", content_id, include_replies=include_replies, **kwargs)

    def creator(self, creator_id, **kwargs):
        return self._dispatch("creator", creator_id, **kwargs)

    def author_posts(self, author_id, **kwargs):
        return self._dispatch("author_posts", author_id, **kwargs)

    def health_check(self, **kwargs):
        return self._dispatch("health_check", **kwargs)



class _RedditPublic:
    """Anonymous web documents, not Reddit's authenticated JSON Data API."""
    backend = "reddit_public_document"

    def __init__(self, fetcher=None):
        self.fetcher = fetcher or fetch_public_url
        self.transport, self.options, self.browser_observations = "http", {}, []

    @staticmethod
    def _url(value):
        parsed = urlsplit(str(value))
        if (parsed.scheme != "https" or parsed.hostname not in {"www.reddit.com", "reddit.com", "old.reddit.com", "redd.it"}
                or parsed.username or parsed.password or parsed.port not in {None, 443}
                or parsed.path.endswith(".json") or parsed.path.startswith(("/api/", "/svc/", "/dev/api"))):
            raise _Failure(CollectionStatus.BLOCKED, "REDDIT_PUBLIC_DOCUMENT_URL_REQUIRED")
        return parsed._replace(fragment="").geturl()

    def _read(self, url, originals):
        url = self._url(url)
        try:
            response, browser = read_public_document(url, originals, fetcher=self.fetcher,
                transport=self.transport, timeout=20, allowed_host_suffixes=("reddit.com", "redd.it"),
                browser_plan={"asset_host_suffixes": ("redditstatic.com", "redditmedia.com", "redd.it"),
                    "capture_paths": (r"/svc/shreddit/(?:search|comments|more-comments)(?:/.*)?",),
                    "request_keys": ("cursor", "after", "before", "q", "post", "comment"),
                    "read_controls": ("shreddit-comment-tree button[slot='load-more']",)
                        if self.options.get("_capability") == "comments" else (),
                    "cursor": self.options.get("_browser_cursor"),
                    "max_steps": _bound(self.options.get("browser_max_steps"), 16 if self.options.get("_browser_cursor") else 2, 40),
                    "cancel_check": self.options.get("cancel_check")})
            if browser:
                self.browser_observations.append(browser)
        except PublicSourceError as exc:
            metadata = public_source_error_metadata(exc)
            status = metadata.get("http_status")
            raise _Failure(CollectionStatus.NEED_VERIFY if getattr(exc, "failure_type", None) == "PUBLIC_BROWSER_VERIFICATION" else CollectionStatus.COOLING_DOWN if status == 429 else
                CollectionStatus.BLOCKED if status in {401, 403, 451} else CollectionStatus.PROVIDER_UNAVAILABLE,
                "REDDIT_PUBLIC_SOURCE_UNAVAILABLE", **metadata) from None
        self._url(response.url)
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.get_text(" ", strip=True).lower() if soup.title else ""
        if (soup.select_one("#captcha, iframe[src*='recaptcha'], form[action*='/login']")
                and not soup.select_one("shreddit-post, .thing[data-fullname^='t3_'], shreddit-profile-header, [data-testid='profile-header']")):
            raise _Failure(CollectionStatus.NEED_VERIFY, "REDDIT_PUBLIC_LOGIN_OR_VERIFICATION_REQUIRED")
        if any(x in title for x in ("blocked", "whoa there", "just a moment", "security check", "log in to reddit")):
            raise _Failure(CollectionStatus.BLOCKED, "REDDIT_PUBLIC_ACCESS_RESTRICTED")
        return response, soup

    @staticmethod
    def _integer(value):
        if type(value) is int:
            return value
        return int(value) if isinstance(value, str) and re.fullmatch(r"-?[0-9]+", value) else None

    @staticmethod
    def _native_date(node):
        time = node.select_one("time[datetime], faceplate-timeago[ts]")
        value = time.get("datetime") or time.get("ts") if time else node.get("created-timestamp")
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return value, parsed.timestamp() if parsed.tzinfo is not None else None
            except ValueError:
                return value, None
        return None, None

    @classmethod
    def _post(cls, node, base_url, observed):
        fullname = node.get("id") or node.get("data-fullname") or node.get("post-id")
        if not isinstance(fullname, str) or not re.fullmatch(r"t3_[a-z0-9]+", fullname):
            # OpenCLI's ranked web-search identity is read from native telemetry,
            # never guessed from a title, rank or a by_id API hydration fallback.
            ids = set()
            for tracker in node.select("search-telemetry-tracker[data-faceplate-tracking-context]"):
                try:
                    ident = json.loads(tracker["data-faceplate-tracking-context"]).get("post", {}).get("id")
                except (ValueError, TypeError, AttributeError):
                    continue
                if isinstance(ident, str) and re.fullmatch(r"t3_[a-z0-9]+", ident):
                    ids.add(ident)
            if len(ids) == 1:
                fullname = next(iter(ids))
        if not isinstance(fullname, str) or not re.fullmatch(r"t3_[a-z0-9]+", fullname):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "REDDIT_PUBLIC_NATIVE_POST_ID_MISSING")
        native = dict(node.attrs)
        title_node = node.select_one("[slot='title'], a.title, [data-testid='post-title'], h1, h2, h3")
        title = node.get("post-title") or (title_node.get_text(" ", strip=True) if title_node else None)
        body = node.select_one("[slot='text-body'], [data-post-click-location='text-body'], .usertext-body .md, [data-testid='post-body']")
        text = body.get_text("\n", strip=True) if body else None
        author = node.get("author") or node.get("data-author")
        author_node = node.select_one("a[href*='/user/'], a.author")
        if author is None and author_node:
            parsed = urlsplit(urljoin(base_url, author_node.get("href", "")))
            match = re.fullmatch(r"/(?:user|u)/([^/]+)/?", parsed.path)
            author = match[1] if match else None
        author_id = node.get("author-id")
        if not isinstance(author_id, str) or not re.fullmatch(r"t2_[a-z0-9]+", author_id):
            author_id = None
        permalink = node.get("permalink") or node.get("data-permalink")
        if not permalink:
            link = node.select_one("a[slot='full-post-link'][href], a.comments[href], a[href*='/comments/']")
            permalink = link.get("href") if link else None
        source_url = cls._url(urljoin(base_url, permalink)) if permalink else "https://www.reddit.com/comments/" + fullname[3:] + "/"
        date, epoch = cls._native_date(node)
        score = cls._integer(node.get("score", node.get("data-score")))
        comment_count = cls._integer(node.get("comment-count", node.get("data-comments-count")))
        media = []
        for i, asset in enumerate(node.select("img[src], img[data-src], video[src], video source[src]")):
            url = asset.get("data-src") or asset.get("src")
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                if asset.name == "img" and ("avatar" in (asset.get("class") or []) or re.search(r"avatar|community_icon|profileIcon", url, re.I)):
                    continue
                media.append({"kind": "image" if asset.name == "img" else "video", "url": url,
                              "locator": f"public_post {asset.name}[src] index={i}"})
        removed = text in {"[removed]", "[deleted]"} or node.get("is-removed") in {"true", ""}
        if removed:
            title, text, media = None, None, []
        if author == "[deleted]":
            author, author_id = None, None
        if title is None and text is None and not media and not removed:
            raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "REDDIT_PUBLIC_POST_BODY_NOT_EXPOSED")
        raw = {"public_dom_attributes": native, "post_id": fullname[3:], "name": fullname,
            "title": title, "selftext": text, "author": author, "author_fullname": author_id,
            "permalink": urlsplit(source_url).path, "source_url": source_url, "created_utc": epoch,
            "source_native_datetime": date, "score": score, "net_votes": score,
            "metric_semantics": {"score": "UPVOTES_MINUS_DOWNVOTES_NOT_LIKES"},
            "num_comments": comment_count, "num_crossposts": None, "media_list": media,
            "captured_at": observed, "collected_at": observed,
            "body_state": "SOURCE_REMOVED" if removed else "PUBLIC_DOM_BODY" if body else "PUBLIC_TITLE_AND_METADATA",
            "publication_time_state": "NATIVE_TIME" if date else "NOT_EXPOSED"}
        return {"platform_content_id": fullname[3:], "title": title, "content": text,
            "author_id": author_id, "author_nickname": author, "publish_datetime": date,
            "url": source_url, "likes": None, "net_votes": score, "comments": comment_count,
            "shares": None, "collects": None, "media_list": media,
            "cover": next((x["url"] for x in media if x["kind"] == "image"), None), "captured_at": observed, "raw": raw}

    def result(self, capability, items, originals, *, error=None, cursor=None, next_cursor=None,
               comments=False, complete=False, extra=None):
        page = {"request_cursor": cursor, "next_cursor": next_cursor, "page_complete": error is None,
            "exhausted": complete and error is None, "coverage_scope": "PUBLIC_DOCUMENT_VISIBLE_ONLY",
            "continuation_is_authorization": False}
        provenance = public_source_provenance(originals[0], originals[0].requested_url or originals[0].url) if originals else {}
        return CollectionResult(error.status if error else CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
            "reddit", items=[] if comments else items, comments=items if comments else [], raw_count=len(items),
            message=error.code if error else "Reddit public document observations returned",
            metadata={"provider": self.backend, "provider_mode": "public", "pagination": page, "source_page": page,
                "public_transport": self.transport,
                "coverage_complete": complete and error is None, "write_enabled": False,
                "retention": "REDDIT_DELETION_AND_AUTHOR_REMOVAL_SYNC_REQUIRED",
                **(extra or {}), **({"error_code": error.code, **error.metadata} if error else {})},
            provenance=provenance, capability=capability, attempted_backend=self.backend,
            attempted_access_class=AccessClass.Z0_PUBLIC, backend=self.backend if originals else None,
            access_class=AccessClass.Z0_PUBLIC if originals else None,
            actual_access_state="SOURCE_OBSERVED" if originals else "NOT_OBSERVED", original_response=originals or None)

    def read(self, capability, value, **kwargs):
        originals, items, error, next_cursor, complete, extra = [], [], None, None, False, {}
        cursor = kwargs.get("cursor")
        observed = datetime.now(timezone.utc).isoformat()
        try:
            self.transport = select_public_transport("reddit", kwargs,
                configured=kwargs.get("_configured_public_transport"), use_server=kwargs.get("_server_public_transport", True))
            self.backend = "reddit_public_browser" if self.transport == "browser" else "reddit_public_document"
            self.options = {**kwargs, "_capability": capability}
            if capability == "health_check":
                return CollectionResult(CollectionStatus.SUCCESS, "reddit", capability="healthcheck",
                    attempted_backend=self.backend, attempted_access_class=AccessClass.Z0_PUBLIC,
                    metadata={"provider": self.backend, "provider_mode": "public", "can_attempt": True,
                        "requires_authorization": False, "network_attempted": False, "source_access": "NOT_VERIFIED"},
                    message="Reddit anonymous public document provider; no OAuth required for this path")
            if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
            is_url = isinstance(value, str) and value.startswith("https://")
            if capability in {"detail", "comments"} or capability == "search" and is_url:
                ident = RedditAdapter._post_id(value)
                url = self._url(value) if is_url else f"https://www.reddit.com/comments/{ident}/"
            elif capability == "search":
                if not _text(value):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "SEARCH_QUERY_REQUIRED")
                url = "https://www.reddit.com/search/?" + urlencode({"q": value, "type": "posts", "sort": "new"})
            else:
                if is_url:
                    selected = self._url(value)
                    match = re.fullmatch(r"/(?:user|u)/([^/]+)(?:/submitted)?/?", urlsplit(selected).path)
                    if not match:
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "REDDIT_PUBLIC_USER_URL_REQUIRED")
                    username = RedditAdapter._username(match[1])
                    url = selected
                else:
                    username = RedditAdapter._username(value)
                    url = f"https://www.reddit.com/user/{quote(username, safe='')}/"
                if capability == "author_posts" and not urlsplit(url).path.rstrip("/").endswith("/submitted"):
                    url = url.rstrip("/") + "/submitted/"
            request_hash = hashlib.sha256(json.dumps([capability, str(value), bool(kwargs.get("include_replies")), self.transport]).encode()).hexdigest()
            source_url = url
            if cursor is not None:
                if (not isinstance(cursor, dict) or cursor.get("kind") not in {"reddit.public_page.v1", "reddit.public_native.v1"}
                        or cursor.get("request_hash") != request_hash):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "REDDIT_PUBLIC_CURSOR_SCOPE_MISMATCH")
                url = self._url(cursor.get("url"))
                if cursor.get("kind") == "reddit.public_native.v1":
                    if self.transport != "browser":
                        raise _Failure(CollectionStatus.NOT_SUPPORTED, "REDDIT_NATIVE_CURSOR_REQUIRES_EXPLICIT_BROWSER_TRANSPORT")
                    if url != source_url or not isinstance(cursor.get("native"), dict) or not cursor["native"].get("request"):
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "REDDIT_NATIVE_CURSOR_INVALID")
                    self.options["_browser_cursor"] = cursor.get("native")
            response, soup = self._read(url, originals)
            if capability == "creator":
                header = soup.select_one("shreddit-profile-header, .ProfileSidebar, .side .titlebox, [data-testid='profile-header']")
                source_name = (header.get("username") or header.get("name") or header.get("prefixed-name")) if header else None
                if isinstance(source_name, str):
                    source_name = source_name.removeprefix("u/")
                if not source_name:
                    for node in soup.select("script[type='application/ld+json']"):
                        try:
                            decoded = json.loads(node.string or node.get_text())
                        except ValueError:
                            continue
                        if isinstance(decoded, dict) and decoded.get("@type") == "Person":
                            source_name = decoded.get("alternateName") or decoded.get("name")
                            break
                if not _text(source_name) or source_name.removeprefix("u/").casefold() != username.casefold():
                    raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "REDDIT_PUBLIC_PROFILE_IDENTITY_NOT_EXPOSED")
                source_name = source_name.removeprefix("u/")
                native_id = header.get("user-id") if header else None
                native_id = native_id if isinstance(native_id, str) and re.fullmatch(r"t2_[a-z0-9]+", native_id) else None
                aliases = [source_name] + ([native_id] if native_id else [])
                description = soup.select_one("[data-testid='profile-description'], .ProfileSidebar__description")
                items = [{"platform_content_id": native_id or source_name, "author_id": native_id or source_name,
                    "author_nickname": source_name, "title": source_name,
                    "content": description.get_text("\n", strip=True) if description else None,
                    "url": response.url, "captured_at": observed, "native_author_aliases": aliases,
                    "raw": {"record_kind": "author", "author_fullname": native_id, "username": source_name,
                        "native_author_aliases": aliases, "profile_url": response.url,
                        "identity_kind": "ACCOUNT_FULLNAME" if native_id else "PUBLIC_USERNAME"}}]
                complete = True
            elif capability == "comments":
                nodes = soup.select("shreddit-comment, .thing[data-fullname^='t1_']")
                seen = set()
                for node in nodes:
                    fullname = node.get("thingid") or node.get("id") or node.get("data-fullname") or node.get("comment-id")
                    if not isinstance(fullname, str) or not re.fullmatch(r"t1_[a-z0-9]+", fullname):
                        continue
                    parent_node = node.find_parent("shreddit-comment")
                    parent = node.get("parentid") or node.get("parent-id") or node.get("data-parent")
                    if parent is None and parent_node:
                        parent = parent_node.get("thingid") or parent_node.get("id")
                    nested = isinstance(parent, str) and parent.startswith("t1_")
                    if nested and not kwargs.get("include_replies"):
                        continue
                    body = node.select_one("[slot='comment'], [slot='comment-body'], .usertext-body .md")
                    if body is None or fullname in seen:
                        continue
                    seen.add(fullname)
                    date, epoch = self._native_date(node)
                    text = body.get_text("\n", strip=True)
                    deleted = text in {"[deleted]", "[removed]"}
                    score = self._integer(node.get("score", node.get("data-score")))
                    author = node.get("author") or node.get("data-author")
                    author = None if author == "[deleted]" else author
                    items.append({"platform_comment_id": fullname, "parent_content_id": "t3_" + ident,
                        "parent_comment_id": parent if nested else None, "reply_to_comment_id": parent if nested else None,
                        "content": None if deleted else text, "author_id": node.get("author-id"),
                        "author_nickname": author, "publish_datetime": date, "likes": None, "net_votes": score,
                        "url": self._url(urljoin(response.url, node["permalink"])) if node.get("permalink") else response.url,
                        "captured_at": observed, "raw": {"public_dom_attributes": dict(node.attrs), "name": fullname,
                            "parent_id": parent, "score": score, "net_votes": score, "created_utc": epoch,
                            "metric_semantics": {"score": "UPVOTES_MINUS_DOWNVOTES_NOT_LIKES"}}})
                empty = soup.select_one("[data-testid='comments-empty-state']")
                if not items and empty is None:
                    raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "REDDIT_PUBLIC_COMMENTS_REQUIRE_CONTROLLED_BROWSER")
                complete = empty is not None
                extra["reply_scope"] = "VISIBLE_NESTED" if kwargs.get("include_replies") else "VISIBLE_TOP_LEVEL"
            else:
                nodes = soup.select("shreddit-post, .thing[data-fullname^='t3_'], [data-testid='search-post-unit']")
                seen = set()
                for node in nodes:
                    item = self._post(node, response.url, observed)
                    if capability in {"detail", "search"} and is_url and item["platform_content_id"] != ident:
                        continue
                    if capability == "author_posts" and str(item["raw"].get("author") or "").casefold() != username.casefold():
                        continue
                    if item["platform_content_id"] not in seen:
                        seen.add(item["platform_content_id"])
                        items.append(item)
                if not items and not soup.select_one("[data-testid='search-no-results'], .search-result-listing .noresults"):
                    raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "REDDIT_PUBLIC_POST_BODY_NOT_EXPOSED")
                complete = capability == "detail"
            for link in soup.select("a[rel~='next'][href], .next-button a[href]"):
                next_url = self._url(urljoin(response.url, link["href"]))
                if next_url == response.url:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "REDDIT_REPEATED_PUBLIC_PAGE")
                next_cursor = {"kind": "reddit.public_page.v1", "request_hash": request_hash, "url": next_url}
                complete = False
                break
            if not complete and next_cursor is None:
                extra["continuation_state"] = "ONLY_VISIBLE_DOM_READ_BROWSER_REQUIRED_FOR_MORE"
            # Native partial URLs are not independent anonymous JSON/API
            # backends. A browser can reach only the page's own returned cursor.
            partials = []
            from urllib.parse import parse_qs
            for partial in soup.select("faceplate-partial[src]"):
                parsed = urlsplit(urljoin(response.url, partial["src"]))
                if parsed.hostname not in {"www.reddit.com", "reddit.com"} or not re.fullmatch(r"/svc/shreddit/(?:search|comments|more-comments)(?:/.*)?", parsed.path):
                    continue
                query = parse_qs(parsed.query)
                if query.get("cursor"):
                    fields = {key: values[-1] for key, values in query.items()
                        if key in {"cursor", "after", "before", "q", "post", "comment"} and values}
                    if capability == "search" and "q" in fields and fields["q"] != value:
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "REDDIT_NATIVE_CURSOR_CHANGED_QUERY")
                    partials.append({"path": parsed.path, "request": fields})
            if len({json.dumps(value, sort_keys=True) for value in partials}) > 1:
                extra["native_continuations"] = partials
            elif partials:
                extra["native_continuations"] = partials
                if self.transport == "browser":
                    next_cursor = {"kind": "reddit.public_native.v1", "request_hash": request_hash,
                        "url": url, "native": partials[0]}
                complete = False
        except (_Failure, PublicSourceError, ValueError) as exc:
            error = exc if isinstance(exc, _Failure) else _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_REDDIT_PUBLIC_INPUT")
        return self.result(capability, items, originals, error=error, cursor=cursor, next_cursor=next_cursor,
            complete=complete, comments=capability == "comments", extra=extra)


register_adapter("reddit", RedditAdapter)
