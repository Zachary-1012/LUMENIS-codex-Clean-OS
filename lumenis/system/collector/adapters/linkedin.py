"""LinkedIn public documents and explicitly selected official resource reads.

There is no public/global post keyword-search API in this provider. Organization
profiles, authorized authors' posts, post details, SocialActions and native media
URNs retain their real scopes; a denied resource never switches to scraping.

Visible post roots/body/media and public profile/company sections adapt OpenCLI
clis/linkedin/{post-roots,posts-core,profile-read,company}.js, Copyright 2025
jackwener, Apache-2.0, commit aeaff2b796efabb7fd46654112418ab61fcae917
(https://github.com/jackwener/OpenCLI). Modified for public-only Source custody,
full text/native IDs/nulls; no default /in/me, editor, COOKIE or auth commands.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urljoin, urlsplit

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


def _date(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            pass
    return None


class LinkedInAdapter(BasePlatformAdapter):
    platform = "linkedin"
    enabled = False
    monitor_priority = "optional"
    RAW_CONTENT_TABLE = "linkedin_posts"
    RAW_USER_TABLE = "linkedin_users"
    _ORIGIN = "https://api.linkedin.com"
    _POST = re.compile(r"urn:li:(?:share|ugcPost):[0-9]+")
    _AUTHOR = re.compile(r"urn:li:(?:organization|person):[A-Za-z0-9_-]+")
    _TARGET = re.compile(r"urn:li:(?:share|ugcPost|activity):[0-9]+|urn:li:comment:\(urn:li:(?:activity|share|ugcPost):[0-9]+,[0-9]+\)")

    def __init__(self, *, provider_config: Mapping[str, Any] | None = None,
                 access_token=None, http_client=None, public_fetcher=None, public_discovery=None, **kwargs):
        super().__init__(**kwargs)
        self._config = dict(provider_config or {})
        self._provider_mode = self._config.get("provider_mode") or "public"
        self._public_transport = self._config.get("public_transport")
        self._public_fetcher, self._public_discovery = public_fetcher, public_discovery
        self._use_server_configuration = provider_config is None and access_token is None
        self._configuration_error = False
        self._token = access_token if access_token is not None else self._config.get("access_token")
        self._version = self._config.get("api_version")
        self._client = http_client
        self._timeout = _bound(self._config.get("timeout_seconds"), 20, 60)
        self._refresh_configuration()

    def _refresh_configuration(self):
        if not self._use_server_configuration:
            return
        try:
            from config import get_config
            owner = get_config()
            keys = {"access_token": "LUMENIS_LINKEDIN_ACCESS_TOKEN", "api_version": "LUMENIS_LINKEDIN_API_VERSION",
                    "oauth_scopes": "LUMENIS_LINKEDIN_OAUTH_SCOPES", "allowed_author_urns": "LUMENIS_LINKEDIN_ALLOWED_AUTHOR_URNS",
                    "allowed_post_urns": "LUMENIS_LINKEDIN_ALLOWED_POST_URNS", "timeout_seconds": "LUMENIS_LINKEDIN_TIMEOUT_SECONDS"}
            values = {field: owner.get(key) for field, key in keys.items()}
            # Absent resource allowlists preserve official granted-resource checks;
            # an explicit empty allowlist denies every resource.
            self._config = {key: value for key, value in values.items() if value is not None}
            self._token = self._config.get("access_token")
            version = self._config.get("api_version")
            self._version = str(version) if type(version) in {str, int} else None
            self._timeout = _bound(self._config.get("timeout_seconds"), 20, 60)
            self._configuration_error = False
        except Exception:
            self._config, self._token, self._version = {}, None, None
            self._configuration_error = True

    def capability_map(self):
        return {"search": "implemented", **{name: "implemented" for name in
                ("detail", "comments", "author", "author_posts", "healthcheck")}}

    def normalize_to_platform_contents(self, raw_record):
        result = map_raw_to_normalized(raw_record, self.platform)
        result["published_at"] = (_date(raw_record.get("publishedAt", raw_record.get("createdAt")))
                                  or raw_record.get("published_at") or raw_record.get("created_at"))
        if isinstance(raw_record.get("media_list"), list):
            result["media_list"] = raw_record["media_list"]
        return result

    def _scopes(self):
        scopes = self._config.get("oauth_scopes", [])
        if isinstance(scopes, str):
            scopes = scopes.split()
        return set(scopes) if isinstance(scopes, (list, tuple, set)) and all(isinstance(x, str) for x in scopes) else set()

    def _guard(self, author=None, organization=False, refresh=True):
        if refresh:
            self._refresh_configuration()
        if self._configuration_error:
            raise _Failure(CollectionStatus.NOT_CONFIGURED, "LINKEDIN_SERVER_CONFIGURATION_UNAVAILABLE")
        if not _text(self._token):
            raise _Failure(CollectionStatus.NOT_CONFIGURED, "LINKEDIN_OAUTH_TOKEN_NOT_CONFIGURED")
        if not isinstance(self._version, str) or not re.fullmatch(r"20[0-9]{2}(?:0[1-9]|1[0-2])", self._version):
            raise _Failure(CollectionStatus.NOT_CONFIGURED, "LINKEDIN_EXPLICIT_SUPPORTED_API_VERSION_REQUIRED")
        scopes = self._scopes()
        required = ({"rw_organization_admin", "r_compliance"} if organization else
                    {"r_member_social"} if author and ":person:" in author else
                    {"r_organization_social"} if author and ":organization:" in author else
                    {"r_organization_social", "r_member_social"})
        if not required.intersection(scopes):
            raise _Failure(CollectionStatus.BLOCKED, "LINKEDIN_REQUIRED_READ_SCOPE_NOT_GRANTED",
                           required_scopes=sorted(required))
        allowlist = self._config.get("allowed_author_urns")
        if author and allowlist is not None and (not isinstance(allowlist, (list, tuple, set)) or author not in allowlist):
            raise _Failure(CollectionStatus.BLOCKED, "LINKEDIN_AUTHOR_OUTSIDE_AUTHORIZED_RESOURCES")

    @classmethod
    def _urn(cls, value, pattern):
        value = str(value).strip()
        if value.startswith("https://"):
            parsed = urlsplit(value)
            if parsed.hostname not in {"linkedin.com", "www.linkedin.com"}:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_LINKEDIN_URN")
            value = unquote(parsed.path.removeprefix("/feed/update/").strip("/"))
        if not pattern.fullmatch(value):
            raise _Failure(CollectionStatus.NOT_SUPPORTED, "DOCUMENTED_NATIVE_RESOURCE_URN_REQUIRED")
        return value

    def _read(self, path, params, originals, *, finder=False):
        if self._client is None:
            self._client = requests.Session()
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self._token}",
                   "Linkedin-Version": self._version, "X-Restli-Protocol-Version": "2.0.0"}
        if finder:
            headers["X-RestLi-Method"] = "FINDER"
        try:
            response = self._client.get(self._ORIGIN + path, params=params, headers=headers,
                                       auth=lambda request: request, timeout=self._timeout, allow_redirects=False)
        except requests.RequestException as exc:
            raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "LINKEDIN_TRANSPORT_ERROR",
                           error_type=type(exc).__name__) from None
        status = response.status_code
        if status != 200:
            state = (CollectionStatus.SESSION_EXPIRED if status == 401 else
                     CollectionStatus.COOLING_DOWN if status == 429 else
                     CollectionStatus.BLOCKED if status in {403, 451} or 300 <= status < 400 else
                     CollectionStatus.NOT_CONFIGURED if status == 426 else
                     CollectionStatus.PROVIDER_UNAVAILABLE if status >= 500 else CollectionStatus.COLLECT_ERROR)
            metadata = {"http_status": status}
            retry = response.headers.get("Retry-After")
            if isinstance(retry, str) and retry.isdigit():
                metadata["retry_after_seconds"] = int(retry)
            raise _Failure(state, "LINKEDIN_API_REQUEST_REJECTED", **metadata)
        try:
            payload = response.json()
        except (ValueError, TypeError):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_API_JSON") from None
        if (not isinstance(payload, dict) or isinstance(payload.get("status"), int)
                and payload["status"] >= 400):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_API_RESPONSE")
        originals.append(payload)
        return payload

    def _result(self, capability, items, originals, *, cursor=None, next_cursor=None,
                error=None, comments=False, extra=None, pagination_known=True):
        complete = next_cursor is None and error is None and pagination_known
        page = {"request_cursor": cursor, "next_cursor": next_cursor,
                "exhausted": complete if pagination_known else None, "page_complete": error is None,
                "coverage_scope": "AUTHORIZED_RESOURCES_ONLY", "continuation_is_authorization": False}
        return CollectionResult(error.status if error else CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
            self.platform, items=[] if comments else items, comments=items if comments else [],
            raw_count=len(items), message=error.code if error else "LinkedIn official authorized resource observations returned",
            metadata={"provider": "linkedin_official_rest", "api_version": self._version, "write_enabled": False,
                "source_page": page, "pagination": page,
                "coverage_complete": complete, "coverage_scope": "AUTHORIZED_RESOURCES_ONLY",
                **(extra or {}), **({"error_code": error.code, **error.metadata} if error else {})},
            access_class=AccessClass.Z2_OFFICIAL_API if originals else None,
            backend="linkedin_official_rest" if originals else None, capability=capability,
            attempted_access_class=AccessClass.Z2_OFFICIAL_API, attempted_backend="linkedin_official_rest",
            actual_access_state="SOURCE_OBSERVED" if originals else "NOT_OBSERVED", original_response=originals or None)

    @staticmethod
    def _media(native):
        content = native.get("content") if isinstance(native.get("content"), dict) else {}
        media = []
        single = content.get("media") if isinstance(content.get("media"), dict) else {}
        multi = content.get("multiImage") if isinstance(content.get("multiImage"), dict) else {}
        candidates = [(single, "content.media")] if single else []
        candidates += [(x, f"content.multiImage.images[{i}]") for i, x in enumerate(multi.get("images") or []) if isinstance(x, dict)]
        for node, path in candidates:
            urn = node.get("id")
            if isinstance(urn, str) and re.fullmatch(r"urn:li:(?:image|video|document):[A-Za-z0-9_-]+", urn):
                media.append({"native_media_urn": urn, "kind": urn.split(":")[2], "locator": path + ".id",
                              "url": None, "availability": "URN_OBSERVED_URL_REQUIRES_AUTHORIZED_MEDIA_READ"})
        article = content.get("article") if isinstance(content.get("article"), dict) else {}
        if _text(article.get("thumbnail")):
            media.append({"native_media_urn": article["thumbnail"], "kind": "image",
                          "url": None, "locator": "content.article.thumbnail"})
        return media

    @classmethod
    def _post(cls, native, observed):
        ident = cls._urn(native.get("id"), cls._POST)
        media = cls._media(native)
        raw = {**native, "post_id": ident, "author_id": native.get("author"),
               "created_at": _date(native.get("publishedAt", native.get("createdAt"))),
               "media_list": media, "url": f"https://www.linkedin.com/feed/update/{ident}",
               "captured_at": observed, "collected_at": observed,
               "like_count": None, "comment_count": None, "share_count": None, "impression_count": None,
               "metric_availability": "NOT_RETURNED_BY_POSTS_API"}
        return {"platform_content_id": ident, "title": None, "content": native.get("commentary"),
                "author_id": native.get("author"), "author_nickname": native.get("author_name"),
                "publish_datetime": raw["created_at"], "url": raw["url"], "likes": None,
                "comments": None, "collects": None, "shares": None, "media_list": media,
                "captured_at": observed, "raw": raw}

    @classmethod
    def _next(cls, payload, path):
        paging = payload.get("paging")
        if not isinstance(paging, dict):
            return None, False
        links = paging.get("links")
        if not isinstance(links, list):
            return None, False
        for link in links:
            if isinstance(link, dict) and link.get("rel") == "next":
                href = link.get("href")
                if not isinstance(href, str):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_NATIVE_NEXT_LINK")
                parsed = urlsplit(href)
                if (parsed.scheme not in {"", "https"} or parsed.netloc not in {"", "api.linkedin.com"}
                        or unquote(parsed.path) != unquote(path) or parsed.fragment or parsed.username):
                    raise _Failure(CollectionStatus.BLOCKED, "NATIVE_NEXT_LINK_SCOPE_MISMATCH")
                values = parse_qs(parsed.query)
                start = values.get("start", [None])[0]
                if not isinstance(start, str) or not start.isascii() or not start.isdigit():
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "NATIVE_NEXT_START_MISSING")
                return int(start), True
        return None, True

    def _official_search(self, keyword: str, **kwargs):
        return self._result("search", [], [], error=_Failure(CollectionStatus.NOT_SUPPORTED,
            "LINKEDIN_GLOBAL_KEYWORD_POST_SEARCH_NOT_PROVIDED"),
            extra={"documented_capability": "author_posts", "required_input": "authorized native author URN"})

    def _official_detail(self, content_id: str, **kwargs):
        originals, items, error = [], [], None
        try:
            self._guard()
            urn = self._urn(content_id, self._POST)
            allowed = self._config.get("allowed_post_urns")
            if allowed is not None and (not isinstance(allowed, (list, tuple, set)) or urn not in allowed):
                raise _Failure(CollectionStatus.BLOCKED, "LINKEDIN_POST_OUTSIDE_AUTHORIZED_RESOURCES")
            payload = self._read("/rest/posts/" + quote(urn, safe=""), {"viewContext": "READER"}, originals)
            author = payload.get("author")
            if not isinstance(author, str):
                raise _Failure(CollectionStatus.COLLECT_ERROR, "POST_AUTHOR_URN_MISSING")
            self._guard(author, refresh=False)
            items.append(self._post(payload, datetime.now(timezone.utc).isoformat()))
        except _Failure as exc:
            error = exc
        return self._result("detail", items, originals, error=error)

    def _official_author_posts(self, author_id: str, **kwargs):
        originals, items, error = [], [], None
        cursor, start, known, author = kwargs.get("cursor"), 0, True, None
        remaining = _bound(kwargs.get("max_results"), 25, 1000)
        sort = kwargs.get("sort", "LAST_MODIFIED")
        try:
            author = self._urn(author_id, self._AUTHOR)
            self._guard(author)
            if sort not in {"LAST_MODIFIED", "CREATED"}:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_AUTHOR_POST_ORDER")
            if cursor is not None:
                if (not isinstance(cursor, dict) or cursor.get("kind") != "linkedin.author_posts.v1"
                        or cursor.get("author_urn") != author or cursor.get("sort") != sort
                        or cursor.get("api_version") != self._version or type(cursor.get("start")) is not int or cursor["start"] < 0):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "AUTHOR_CURSOR_SCOPE_MISMATCH")
                start = cursor["start"]
            for _ in range(_bound(kwargs.get("max_pages"), 1, 100)):
                if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                    raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
                payload = self._read("/rest/posts", {"q": "author", "author": author, "sortBy": sort,
                    "count": min(100, remaining), "start": start}, originals, finder=True)
                elements = payload.get("elements")
                if not isinstance(elements, list) or any(not isinstance(x, dict) for x in elements):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_POSTS_FINDER_RESPONSE")
                for element in elements:
                    if element.get("author") != author:
                        raise _Failure(CollectionStatus.BLOCKED, "POST_AUTHOR_SCOPE_MISMATCH")
                    items.append(self._post(element, datetime.now(timezone.utc).isoformat()))
                next_start, known = self._next(payload, "/rest/posts")
                if next_start is not None and next_start <= start:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "NON_ADVANCING_NATIVE_START")
                start = next_start
                remaining -= len(elements)
                if start is None or remaining <= 0:
                    break
        except _Failure as exc:
            error = exc
        next_cursor = ({"kind": "linkedin.author_posts.v1", "author_urn": author, "sort": sort,
                        "start": start, "api_version": self._version} if start is not None and author and (originals or cursor) else None)
        return self._result("author_posts", items, originals, cursor=cursor, next_cursor=next_cursor,
                            error=error, pagination_known=known)

    @staticmethod
    def _comment(native, target, observed, parent_target=None):
        urn = native.get("commentUrn")
        if not isinstance(urn, str) or not LinkedInAdapter._TARGET.fullmatch(urn) or not urn.startswith("urn:li:comment:"):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "COMMENT_NATIVE_URN_MISSING")
        message = native.get("message") if isinstance(native.get("message"), dict) else {}
        created = native.get("created") if isinstance(native.get("created"), dict) else {}
        likes = native.get("likesSummary") if isinstance(native.get("likesSummary"), dict) else {}
        parent = native.get("parentComment") or (parent_target if isinstance(parent_target, str) and parent_target.startswith("urn:li:comment:") else None)
        return {"platform_comment_id": urn, "parent_content_id": target,
                "parent_comment_id": parent, "reply_to_comment_id": parent,
                "content": message.get("text"), "author_id": native.get("actor"), "author_nickname": None,
                "publish_datetime": _date(created.get("time")), "likes": likes.get("totalLikes"),
                "url": None, "captured_at": observed, "raw": native}

    def _official_comments(self, content_id: str, *, include_replies=False, **kwargs):
        originals, items, pending, known_targets, seen = [], [], [], set(), set()
        cursor, error, root, known = kwargs.get("cursor"), None, None, True
        try:
            self._guard()
            root = self._urn(content_id, self._TARGET)
            if cursor is not None:
                if (not isinstance(cursor, dict) or cursor.get("kind") != "linkedin.comments.v1"
                        or cursor.get("target_urn") != root or cursor.get("include_replies") is not include_replies
                        or cursor.get("api_version") != self._version or not isinstance(cursor.get("pending_targets"), list)
                        or not isinstance(cursor.get("known_targets"), list)
                        or any(not isinstance(x, str) or not self._TARGET.fullmatch(x) for x in cursor["known_targets"])):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "COMMENT_CURSOR_SCOPE_MISMATCH")
                pending = [dict(x) for x in cursor["pending_targets"] if isinstance(x, dict)]
                if len(pending) != len(cursor["pending_targets"]):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_COMMENT_CURSOR")
                known_targets = set(cursor["known_targets"])
            else:
                pending = [{"target_urn": root, "start": 0}]
                known_targets = {root}
            remaining = _bound(kwargs.get("max_results"), 100, 2000)
            for _ in range(_bound(kwargs.get("max_pages"), 10, 100)):
                if not pending or remaining <= 0:
                    break
                if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                    raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
                entry = pending[0]
                target = self._urn(entry.get("target_urn"), self._TARGET)
                start = entry.get("start")
                if type(start) is not int or start < 0:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_COMMENT_NATIVE_START")
                path = "/rest/socialActions/" + quote(target, safe="") + "/comments"
                payload = self._read(path, {"start": start, "count": min(100, remaining)}, originals)
                elements = payload.get("elements")
                if not isinstance(elements, list) or any(not isinstance(x, dict) for x in elements):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_COMMENTS_RESPONSE")
                new_entries = []
                for native in elements:
                    mapped = self._comment(native, root, datetime.now(timezone.utc).isoformat(), target)
                    if mapped["platform_comment_id"] not in seen:
                        seen.add(mapped["platform_comment_id"])
                        items.append(mapped)
                    summary = native.get("commentsSummary") if isinstance(native.get("commentsSummary"), dict) else {}
                    child = mapped["platform_comment_id"]
                    if include_replies and summary.get("totalFirstLevelComments") != 0 and child not in known_targets:
                        known_targets.add(child)
                        new_entries.append({"target_urn": child, "start": 0})
                next_start, page_known = self._next(payload, path)
                known = known and page_known
                if next_start is not None and next_start <= start:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "NON_ADVANCING_NATIVE_START")
                pending.pop(0)
                if next_start is not None:
                    pending.insert(0, {"target_urn": target, "start": next_start})
                pending.extend(new_entries)
                remaining -= len(elements)
        except _Failure as exc:
            error = exc
        next_cursor = ({"kind": "linkedin.comments.v1", "target_urn": root, "include_replies": include_replies,
                        "api_version": self._version, "pending_targets": pending, "known_targets": sorted(known_targets)}
                       if pending else None)
        return self._result("comments", items, originals, cursor=cursor, next_cursor=next_cursor,
                            error=error, comments=True, pagination_known=known)

    def _official_creator(self, creator_id: str, **kwargs):
        originals, items, error = [], [], None
        try:
            author = self._urn(creator_id, self._AUTHOR)
            if ":person:" in author:
                raise _Failure(CollectionStatus.NOT_SUPPORTED, "ARBITRARY_MEMBER_PROFILE_API_NOT_GRANTED")
            self._guard(author, organization=True)
            payload = self._read("/rest/organizations/" + author.rsplit(":", 1)[1], {}, originals)
            if str(payload.get("id")) != author.rsplit(":", 1)[1]:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "ORGANIZATION_IDENTITY_MISMATCH")
            name = payload.get("localizedName")
            aliases = [value for value in (author, str(payload["id"]), payload.get("vanityName")) if _text(value)]
            items.append({"platform_content_id": author, "author_id": author, "author_nickname": name,
                "title": name, "content": payload.get("localizedDescription"),
                "native_author_aliases": aliases,
                "url": "https://www.linkedin.com/company/" + quote(payload["vanityName"], safe="") if _text(payload.get("vanityName")) else None,
                "captured_at": datetime.now(timezone.utc).isoformat(), "raw": {**payload, "record_kind": "author",
                    "author_id": author, "username": payload.get("vanityName"), "native_author_aliases": aliases}})
        except _Failure as exc:
            error = exc
        return self._result("author", items, originals, error=error, extra={"record_kind": "organization_author"})

    def _official_media_detail(self, media_urn: str, **kwargs):
        originals, items, error = [], [], None
        try:
            self._guard()
            urn = str(media_urn).strip()
            match = re.fullmatch(r"urn:li:(image|video):[A-Za-z0-9_-]+", urn)
            if not match:
                raise _Failure(CollectionStatus.NOT_SUPPORTED, "DOCUMENTED_IMAGE_OR_VIDEO_URN_REQUIRED")
            path = "/rest/" + ("images/" if match[1] == "image" else "videos/") + quote(urn, safe="")
            payload = self._read(path, {}, originals)
            if payload.get("id") != urn:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "MEDIA_URN_IDENTITY_MISMATCH")
            items.append({"platform_content_id": urn, "media_list": [{
                "native_media_urn": urn, "kind": match[1], "url": payload.get("downloadUrl"),
                "expires_at": _date(payload.get("downloadUrlExpiresAt")), "locator": "downloadUrl",
                "availability": payload.get("status")}], "raw": payload})
        except _Failure as exc:
            error = exc
        return self._result("media_detail", items, originals, error=error)

    def _official_health_check(self, **kwargs):
        try:
            self._guard()
        except _Failure as exc:
            return self._result("healthcheck", [], [], error=exc)
        return CollectionResult(CollectionStatus.SUCCESS, self.platform,
            message="LinkedIn OAuth/version/read-scope configuration present; resource authorization unverified",
            metadata={"provider": "linkedin_official_rest", "api_version": self._version,
                      "can_attempt": True, "network_attempted": False, "authorization_verification": "NOT_VERIFIED"},
            capability="healthcheck")


    def _selected_mode(self, kwargs):
        explicit = kwargs.pop("provider_mode", None)
        if explicit is None and self._use_server_configuration:
            from config import get_config
            explicit = get_config().get("LUMENIS_LINKEDIN_PROVIDER_MODE")
        mode = explicit or self._provider_mode
        if mode not in {"public", "official"}:
            raise _Failure(CollectionStatus.COLLECT_ERROR, "PROVIDER_MODE_INVALID")
        return mode

    def _dispatch(self, capability, value=None, **kwargs):
        try:
            mode = self._selected_mode(kwargs)
        except (ImportError, _Failure) as exc:
            error = exc if isinstance(exc, _Failure) else _Failure(CollectionStatus.NOT_CONFIGURED, "SERVER_CONFIGURATION_UNAVAILABLE")
            return _LinkedInPublic(self._public_fetcher, self._public_discovery).result(capability, [], [], error=error)
        if mode == "official":
            method = getattr(self, "_official_" + capability)
            result = method(**kwargs) if capability == "health_check" else method(value, **kwargs)
            result.metadata["provider_mode"] = "official"
            return result
        kwargs.setdefault("_configured_public_transport", self._public_transport)
        kwargs.setdefault("_server_public_transport", self._use_server_configuration)
        return _LinkedInPublic(self._public_fetcher, self._public_discovery).read(capability, value, **kwargs)

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

    def media_detail(self, media_urn, **kwargs):
        return self._dispatch("media_detail", media_urn, **kwargs)

    def health_check(self, **kwargs):
        return self._dispatch("health_check", **kwargs)



_LINKEDIN_POST_ROOTS_SCRIPT = r"""() => {
function locatePostCards(document) {
  const selector = 'article, [role="article"], .feed-shared-update-v2, .occludable-update';
  const scope = document.querySelector('main, [role="main"]') || document.body;
  const visible = node => {
    for (let el = node; el; el = el.parentElement) {
      const style = document.defaultView.getComputedStyle(el);
      if (el.hidden || el.getAttribute('aria-hidden') === 'true' || style.display === 'none' || style.visibility === 'hidden') return false;
    }
    return true;
  };
  const identity = link => {
    try {
      const url = new URL(link.href, document.location.href);
      if (url.protocol !== 'https:' || !/^(?:www\.)?linkedin\.com$/.test(url.hostname) || url.username || url.password) return '';
      const activity = url.pathname.match(/\/feed\/update\/urn:li:activity:(\d+)/) || url.pathname.match(/\/posts\/[^/]*activity-(\d+)/);
      if (activity) return 'activity:' + activity[1];
      return /^\/(?:posts|feed\/update)\/[^/]+/.test(url.pathname) ? url.origin + url.pathname.replace(/\/$/, '') : '';
    } catch { return ''; }
  };
  const linksIn = root => Array.from(root.querySelectorAll('a[href]')).filter(link => identity(link) && visible(link));
  const identitiesIn = root => new Set(linksIn(root).map(identity));
  const cards = Array.from(scope.querySelectorAll(selector)).filter(visible);
  const links = linksIn(scope).filter(link => !link.closest('nav, aside, [role="navigation"], [role="complementary"]'));
  let unmatchedPermalinks = 0;
  for (const link of links) {
    if (cards.some(card => card.contains(link))) continue;
    let generic = null;
    let root = null;
    for (let node = link.parentElement, depth = 0; node && node !== scope && depth < 12; node = node.parentElement, depth++) {
      if (identitiesIn(node).size !== 1) break;
      const author = node.querySelector('a[href*="/in/"], a[href*="/company/"]');
      if (!author) continue;
      if (node.matches('li, [role="listitem"]')) { root = node; break; }
      const text = node.innerText || node.textContent || '';
      const hasBody = node.querySelector('.update-components-text, .feed-shared-text, [dir="ltr"], p');
      if (!generic && hasBody && /\b\d+\s*(?:s|m|h|d|w|mo|yr|min)\b/i.test(text)) generic = node;
    }
    root ||= generic;
    if (root) cards.push(root);
    else unmatchedPermalinks++;
  }
  // Old markup often nests two recognized card classes around the same post.
  // Prefer the outer card, retaining its complete body and metrics.
  return { cards: cards.filter(card => !cards.some(other => other !== card && other.contains(card))), unmatchedPermalinks };
}

 const result=locatePostCards(document); return {post_cards:result.cards.map(card=>card.outerHTML),unmatched_permalinks:result.unmatchedPermalinks};
}
"""


class _LinkedInPublic:
    """Guest posts/company/profile documents and existing public discovery."""
    backend = "linkedin_public_document"

    def __init__(self, fetcher=None, discovery=None):
        self.fetcher, self.discovery = fetcher or fetch_public_url, discovery
        self.transport, self.options, self.browser_observations = "http", {}, []

    @staticmethod
    def _has_type(node, expected):
        value = node.get("@type")
        values = value if isinstance(value, list) else [value]
        return any(isinstance(item, str) and item in expected for item in values)

    @staticmethod
    def _url(value):
        parsed = urlsplit(str(value))
        if (parsed.scheme != "https" or parsed.hostname not in {"linkedin.com", "www.linkedin.com", "news.linkedin.com"}
                or parsed.username or parsed.password or parsed.port not in {None, 443}
                or parsed.path.startswith(("/uas/", "/checkpoint/", "/authwall", "/voyager/", "/learning-api/"))):
            raise _Failure(CollectionStatus.BLOCKED, "LINKEDIN_PUBLIC_DOCUMENT_URL_REQUIRED")
        return parsed._replace(fragment="").geturl()

    def _read(self, url, originals):
        url = self._url(url)
        try:
            response, browser = read_public_document(url, originals, fetcher=self.fetcher,
                transport=self.transport, timeout=20, allowed_host_suffixes=("linkedin.com",),
                browser_plan={"asset_host_suffixes": ("licdn.com",), "capture_paths": (),
                    "read_controls": (".feed-shared-inline-show-more-text__see-more-less-toggle",),
                    "max_steps": _bound(self.options.get("browser_max_steps"), 2, 40),
                    "cancel_check": self.options.get("cancel_check"), "extraction_script": _LINKEDIN_POST_ROOTS_SCRIPT})
            if browser:
                self.browser_observations.append(browser)
        except PublicSourceError as exc:
            metadata = public_source_error_metadata(exc)
            status = metadata.get("http_status")
            raise _Failure(CollectionStatus.NEED_VERIFY if getattr(exc, "failure_type", None) == "PUBLIC_BROWSER_VERIFICATION" else CollectionStatus.COOLING_DOWN if status == 429 else
                CollectionStatus.BLOCKED if status in {401, 403, 451, 999} else CollectionStatus.PROVIDER_UNAVAILABLE,
                "LINKEDIN_PUBLIC_SOURCE_UNAVAILABLE", **metadata) from None
        self._url(response.url)
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.get_text(" ", strip=True).lower() if soup.title else ""
        if soup.select_one("#captcha-internal, #captcha, form[action*='/checkpoint/']") or any(x in title for x in
            ("security verification", "sign in | linkedin", "linkedin login", "linkedin: log in or sign up")):
            raise _Failure(CollectionStatus.NEED_VERIFY, "LINKEDIN_PUBLIC_AUTHWALL_OR_VERIFICATION")
        return response, soup

    @staticmethod
    def _jsonld(soup):
        stack = []
        for script in soup.select("script[type='application/ld+json']"):
            try:
                stack.append(json.loads(script.string or script.get_text()))
            except ValueError:
                continue
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                yield value
                if isinstance(value.get("@graph"), list):
                    stack.extend(value["@graph"])
            elif isinstance(value, list):
                stack.extend(value)

    @staticmethod
    def _urn(value):
        if not isinstance(value, str):
            return None
        found = re.search(r"urn:li:(?:activity|share|ugcPost):[0-9]+", unquote(value))
        if found:
            return found[0]
        found = re.search(r"(?:-|_)(activity|ugcPost|share)-([0-9]+)(?:-|/|$)", value)
        return f"urn:li:{found[1]}:{found[2]}" if found else None

    @staticmethod
    def _meta(soup, name):
        node = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        return node.get("content") if node else None

    @classmethod
    def _post_cards(cls, soup):
        """Static counterpart to OpenCLI locatePostCards, excluding navigation."""
        scope = soup.select_one("main, [role='main']") or soup
        def visible(node):
            return not any(parent.has_attr("hidden") or parent.get("aria-hidden") == "true"
                or re.search(r"(?:display\s*:\s*none|visibility\s*:\s*hidden)", parent.get("style", ""), re.I)
                for parent in [node, *node.parents] if hasattr(parent, "attrs"))
        cards = [node for node in scope.select("article, [role='article'], .feed-shared-update-v2, .occludable-update") if visible(node)]
        for link in scope.select("a[href*='/posts/'], a[href*='/feed/update/']"):
            if not visible(link) or link.find_parent(["nav", "aside"]) or any(card in link.parents for card in cards):
                continue
            for node in list(link.parents)[:12]:
                if node is scope:
                    break
                ids = {cls._urn(anchor.get("href")) for anchor in node.select("a[href]") if cls._urn(anchor.get("href"))}
                if len(ids) != 1:
                    break
                if node.select_one("a[href*='/in/'],a[href*='/company/']") and node.select_one(".update-components-text,.feed-shared-text,p"):
                    cards.append(node)
                    break
        return [card for card in cards if not any(other is not card and other in card.parents for other in cards)]

    @staticmethod
    def _section_text(soup, names):
        for heading in soup.select("main h2,main h3,section h2,section h3"):
            if heading.get_text(" ", strip=True).casefold() in names:
                section = heading.find_parent("section")
                if section:
                    return "\n".join(node.get_text(" ", strip=True) for node in section.select("p,li,dd") if node.get_text(" ", strip=True)) or None
        return None

    def _post(self, response, soup, observed):
        nodes = list(self._jsonld(soup))
        data = next((x for x in nodes if self._has_type(x,
            {"SocialMediaPosting", "DiscussionForumPosting", "Article", "NewsArticle", "BlogPosting"})), {})
        canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
        permalink = soup.select_one("a[href*='/feed/update/'], a[href*='/posts/'], a[href*='/pulse/']")
        url = self._url(urljoin(response.url, canonical["href"])) if canonical and canonical.get("href") else (
            self._url(urljoin(response.url, permalink["href"])) if permalink else response.url)
        urn = self._urn(data.get("identifier")) or self._urn(data.get("@id")) or self._urn(url)
        if not urn:
            entity = soup.select_one("[data-entity-urn]")
            urn = self._urn(entity.get("data-entity-urn")) if entity else None
        body = soup.select_one(".attributed-text-segment-list__content, .share-update-card__update-text, article .break-words, .feed-shared-update-v2__description, .update-components-text, .feed-shared-text, [class*='update-components-text']")
        text = data.get("articleBody") or data.get("text") or (body.get_text("\n", strip=True) if body else None)
        description_only = text is None
        if text is None:
            text = data.get("description") or self._meta(soup, "og:description")
        title = data.get("headline") or self._meta(soup, "og:title")
        if not _text(text) and not _text(title):
            raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "LINKEDIN_PUBLIC_POST_BODY_NOT_EXPOSED")
        author = data.get("author") if isinstance(data.get("author"), dict) else {}
        author_url = author.get("url")
        if not author_url:
            anchor = soup.select_one(".base-main-card__info a[href*='/company/'], .base-main-card__info a[href*='/in/'], a[data-tracking-control-name*='actor'], a[href*='/in/'], a[href*='/company/']")
            author_url = urljoin(response.url, anchor["href"]) if anchor and anchor.get("href") else None
            if anchor and not author.get("name"):
                author = {**author, "name": anchor.get_text(" ", strip=True)}
        author_urn = author.get("identifier") if isinstance(author.get("identifier"), str) and re.fullmatch(r"urn:li:(?:organization|person):[A-Za-z0-9_-]+", author["identifier"]) else None
        media = []
        image = data.get("image")
        images = image if isinstance(image, list) else [image] if image else []
        for index, asset in enumerate(images):
            value = asset.get("url") or asset.get("contentUrl") if isinstance(asset, dict) else asset
            if isinstance(value, str) and value.startswith(("https://", "http://")):
                media.append({"kind": "image", "url": value, "locator": f"JSONLD.image[{index}]"})
        for index, video in enumerate(soup.select("video")):
            source = video.get("data-sources")
            if source:
                try:
                    sources = json.loads(source)
                except ValueError:
                    sources = []
                for number, item in enumerate(sources if isinstance(sources, list) else []):
                    if isinstance(item, dict) and _text(item.get("src")):
                        media.append({"kind": "video", "url": item["src"],
                                      "locator": f"video[{index}].data-sources[{number}].src"})
            if _text(video.get("src")):
                media.append({"kind": "video", "url": video["src"], "locator": f"video[{index}].src"})
        for index, image in enumerate(soup.select("img[src], img[data-delayed-url]")):
            value = image.get("data-delayed-url") or image.get("src")
            alt = image.get("alt", "")
            if isinstance(value, str) and value.startswith(("https://", "http://")) and not re.search(
                    r"profile-displayphoto|profile-framedphoto|company-logo|emoji|reaction|ghost-person|100_100", value, re.I) and not re.search(r"profile|photo of|emoji|reaction", alt, re.I):
                if not any(asset["url"] == value for asset in media):
                    media.append({"kind": "image", "url": value, "locator": f"post img[{index}]"})
        cover = self._meta(soup, "og:image")
        if _text(cover) and not any(x["url"] == cover for x in media):
            media.append({"kind": "image", "role": "cover", "url": cover, "locator": "meta[property='og:image'].content"})
        source_id = urn or "public-url:" + hashlib.sha256(url.encode()).hexdigest()
        time_node = soup.select_one("time[datetime]")
        published = data.get("datePublished") or data.get("dateCreated") or (time_node.get("datetime") if time_node else None)
        raw = {"post_id": source_id, "native_post_urn": urn, "native_identity_state": "NATIVE_URN_OBSERVED" if urn else "PUBLIC_URL_IDENTITY_ONLY",
            "source_identity_kind": "NATIVE_URN" if urn else "PUBLIC_URL_SHA256", "url": url,
            "commentary": text, "title": title, "author_id": author_urn, "author_name": author.get("name"),
            "author_profile_url": author_url, "created_at": published, "published_at": published,
            "like_count": None, "comment_count": None, "share_count": None, "impression_count": None,
            "media_list": media, "cover": cover, "captured_at": observed, "collected_at": observed,
            "public_jsonld": data, "captured_from_url": response.url,
            "body_state": "PUBLIC_DESCRIPTION_EXCERPT" if description_only else "PUBLIC_POST_BODY",
            "publication_time_state": "NATIVE_DATE" if published else "NOT_EXPOSED"}
        return {"platform_content_id": source_id, "title": title, "content": text, "author_id": author_urn,
            "author_nickname": author.get("name"), "publish_datetime": published, "url": url,
            "likes": None, "comments": None, "shares": None, "collects": None, "cover": cover,
            "media_list": media, "captured_at": observed, "raw": raw}

    def result(self, capability, items, originals, *, error=None, cursor=None, next_cursor=None,
               comments=False, complete=False, extra=None):
        page = {"request_cursor": cursor, "next_cursor": next_cursor, "page_complete": error is None,
            "exhausted": complete and error is None, "coverage_scope": "PUBLIC_DOCUMENT_VISIBLE_ONLY",
            "continuation_is_authorization": False}
        provenance = public_source_provenance(originals[0], originals[0].requested_url or originals[0].url) if originals else {}
        return CollectionResult(error.status if error else CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
            "linkedin", items=[] if comments else items, comments=items if comments else [], raw_count=len(items),
            message=error.code if error else "LinkedIn public source observations returned",
            metadata={"provider": self.backend, "provider_mode": "public", "pagination": page, "source_page": page,
                "public_transport": self.transport,
                "coverage_complete": complete and error is None, "write_enabled": False,
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
            self.transport = select_public_transport("linkedin", kwargs,
                configured=kwargs.get("_configured_public_transport"), use_server=kwargs.get("_server_public_transport", True))
            self.backend = "linkedin_public_browser" if self.transport == "browser" else "linkedin_public_document"
            self.options = kwargs
            if capability == "health_check":
                return CollectionResult(CollectionStatus.SUCCESS, "linkedin", capability="healthcheck",
                    attempted_backend=self.backend, attempted_access_class=AccessClass.Z0_PUBLIC,
                    metadata={"provider": self.backend, "provider_mode": "public", "can_attempt": True,
                        "requires_authorization": False, "network_attempted": False, "source_access": "NOT_VERIFIED"},
                    message="LinkedIn public document provider; no API token required")
            if capability == "media_detail":
                raise _Failure(CollectionStatus.NOT_SUPPORTED, "PUBLIC_MEDIA_REQUIRES_OBSERVED_SOURCE_URL_NOT_PRIVATE_URN_API")
            if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
            request_hash = hashlib.sha256(json.dumps([capability, str(value), bool(kwargs.get("include_replies")), self.transport]).encode()).hexdigest()
            urls = []
            if cursor is not None:
                if (not isinstance(cursor, dict) or cursor.get("kind") != "linkedin.public_page.v1"
                        or cursor.get("request_hash") != request_hash or not isinstance(cursor.get("urls"), list)):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "LINKEDIN_PUBLIC_CURSOR_SCOPE_MISMATCH")
                urls = [self._url(url) for url in cursor["urls"]]
            elif isinstance(value, str) and value.startswith("https://"):
                urls = [self._url(value)]
            elif capability == "search":
                from .google import GoogleAdapter
                discovery = self.discovery or GoogleAdapter()
                found = discovery.search(f"site:linkedin.com/posts/ {value}", max_results=_bound(kwargs.get("max_results"), 5, 25))
                if not found.ok:
                    raise _Failure(found.status, "LINKEDIN_PUBLIC_LINK_DISCOVERY_UNAVAILABLE")
                for item in found.items:
                    url = item.get("url")
                    if isinstance(url, str) and urlsplit(url).hostname in {"linkedin.com", "www.linkedin.com"} and urlsplit(url).path.startswith(("/posts/", "/feed/update/")):
                        urls.append(self._url(url))
                extra["discovery_provider"] = "EXISTING_REGISTERED_GOOGLE_DISCOVERY"
                extra["discovery_snippets_are_original_body"] = False
                if not urls:
                    return self.result(capability, [], [], extra={**extra, "source_state": "NO_PUBLIC_LINKS_RETURNED_BY_DISCOVERY"})
            elif capability in {"creator", "author_posts"}:
                raw = str(value)
                match = re.fullmatch(r"urn:li:organization:([0-9]+)", raw)
                selected = f"https://www.linkedin.com/company/{match[1]}/" if match else None
                for prefix in ("company:", "in:"):
                    if raw.startswith(prefix) and re.fullmatch(r"[A-Za-z0-9_.-]+", raw[len(prefix):]):
                        selected = "https://www.linkedin.com/" + prefix[:-1] + "/" + raw[len(prefix):] + "/"
                if selected is None:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "PUBLIC_PROFILE_URL_OR_EXPLICIT_COMPANY_IN_REFERENCE_REQUIRED")
                urls = [selected]
            else:
                urn = self._urn(str(value))
                if urn is None:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "LINKEDIN_PUBLIC_POST_URL_OR_NATIVE_URN_REQUIRED")
                urls = ["https://www.linkedin.com/feed/update/" + urn + "/"]
            remaining_urls = list(urls)
            for url in urls[:_bound(kwargs.get("max_pages"), 5 if capability == "search" else 1, 25)]:
                response, soup = self._read(url, originals)
                if capability == "creator":
                    data = next((x for x in self._jsonld(soup) if self._has_type(x, {"Organization", "Person", "ProfilePage"})), {})
                    if self._has_type(data, {"ProfilePage"}) and isinstance(data.get("mainEntity"), dict):
                        data = data["mainEntity"]
                    name = data.get("name")
                    if not _text(name):
                        title = soup.select_one("h1")
                        name = title.get_text(" ", strip=True) if title else None
                    if not _text(name):
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "LINKEDIN_PUBLIC_PROFILE_NOT_EXPOSED")
                    identity = data.get("identifier")
                    identity = identity if isinstance(identity, str) and re.fullmatch(r"urn:li:(?:organization|person):[A-Za-z0-9_-]+", identity) else None
                    canonical = soup.find("link", rel=lambda v: v and "canonical" in v)
                    profile_url = self._url(urljoin(response.url, canonical["href"])) if canonical and canonical.get("href") else response.url
                    parts = urlsplit(profile_url).path.strip("/").split("/")
                    handle = parts[1] if len(parts) >= 2 and parts[0] in {"company", "in"} else None
                    aliases = [x for x in (identity, handle) if _text(x)]
                    if handle:
                        aliases.extend([parts[0] + ":" + handle, profile_url])
                    items.append({"platform_content_id": identity or handle or profile_url, "author_id": identity or handle,
                        "author_nickname": name, "title": name, "content": data.get("description") or self._section_text(soup, {"about", "overview", "关于", "概览"}),
                        "url": profile_url, "captured_at": observed, "native_author_aliases": aliases,
                        "raw": {**data, "author_id": identity or handle, "native_author_aliases": aliases,
                            "username": handle, "record_kind": "author", "profile_url": profile_url,
                            "identity_kind": "NATIVE_URN" if identity else "PUBLIC_PROFILE_HANDLE",
                            "public_profile_sections": {key: self._section_text(soup, names) for key, names in {
                                "about": {"about", "overview", "关于"}, "experience": {"experience", "工作经历"},
                                "education": {"education", "教育经历"}, "services": {"services", "提供服务"}}.items()},
                            "company_facts": {term.get_text(" ", strip=True): term.find_next_sibling().get_text(" ", strip=True)
                                for term in soup.select("main dt") if term.find_next_sibling() is not None}}})
                    complete = True
                elif capability == "author_posts" and not (cursor is not None and cursor.get("stage") == "post_links"):
                    links = []
                    listing = soup.select_one(".updates__list, .updates, [data-section='updates'], [data-module='updates']")
                    cards = self._post_cards(soup)
                    if self.browser_observations:
                        rendered = self.browser_observations[-1].extraction.get("post_cards", [])
                        if rendered:
                            cards = [BeautifulSoup(html, "html.parser") for html in rendered if isinstance(html, str)]
                    if cards:
                        seen = set()
                        for card in cards:
                            item = self._post(response, card, observed)
                            profile = item["raw"].get("author_profile_url")
                            if profile and urlsplit(profile).path.rstrip("/") != urlsplit(url).path.rstrip("/"):
                                continue
                            if item["platform_content_id"] not in seen:
                                seen.add(item["platform_content_id"])
                                items.append(item)
                        extra["continuation_state"] = "PUBLIC_VISIBLE_AUTHOR_CARDS_ONLY"
                        remaining_urls.pop(0)
                        continue
                    if listing is None:
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "LINKEDIN_PUBLIC_AUTHOR_POST_LIST_NOT_EXPOSED")
                    for anchor in listing.select("a[href*='/posts/'], a[href*='/feed/update/']"):
                        target = self._url(urljoin(response.url, anchor["href"]))
                        if target not in links:
                            links.append(target)
                    if not links:
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "LINKEDIN_PUBLIC_AUTHOR_POSTS_NOT_EXPOSED")
                    for target in links[:_bound(kwargs.get("max_results"), 5, 25)]:
                        post_response, post_soup = self._read(target, originals)
                        items.append(self._post(post_response, post_soup, observed))
                    if links[_bound(kwargs.get("max_results"), 5, 25):]:
                        next_cursor = {"kind": "linkedin.public_page.v1", "request_hash": request_hash,
                                       "urls": links[_bound(kwargs.get("max_results"), 5, 25):], "stage": "post_links"}
                    extra["continuation_state"] = "ONLY_PUBLIC_PROFILE_VISIBLE_LINKS"
                elif capability == "comments":
                    root = self._urn(response.url) or self._urn(str(value))
                    for node in soup.select("[data-comment-id], .comment[data-id], .comments-comment-item[data-id], .comments-comment-entity[data-id]"):
                        ident = node.get("data-comment-id") or node.get("data-id")
                        if not _text(ident):
                            continue
                        parent = node.get("data-parent-comment-id")
                        if parent and not kwargs.get("include_replies"):
                            continue
                        body = node.select_one(".comment__message, .comment__text, .commentary, .comments-comment-item__main-content, .comments-comment-item-content-body")
                        if body is None:
                            continue
                        author = node.select_one("a[href*='/in/'], a[href*='/company/']")
                        time = node.select_one("time[datetime]")
                        items.append({"platform_comment_id": ident, "parent_content_id": root,
                            "parent_comment_id": parent, "reply_to_comment_id": parent,
                            "content": body.get_text("\n", strip=True), "author_id": None,
                            "author_nickname": author.get_text(" ", strip=True) if author else None,
                            "publish_datetime": time.get("datetime") if time else None, "likes": None,
                            "url": response.url, "captured_at": observed,
                            "raw": {"public_dom_attributes": dict(node.attrs),
                                "author_profile_url": urljoin(response.url, author["href"]) if author and author.get("href") else None}})
                    if not items:
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "LINKEDIN_PUBLIC_COMMENTS_NOT_EXPOSED")
                    extra["continuation_state"] = "PUBLIC_VISIBLE_COMMENTS_ONLY"
                else:
                    items.append(self._post(response, soup, observed))
                    complete = capability == "detail"
                remaining_urls.pop(0)
                for anchor in soup.select("a[rel~='next'][href]"):
                    remaining_urls.append(self._url(urljoin(response.url, anchor["href"])))
            if remaining_urls:
                next_cursor = {"kind": "linkedin.public_page.v1", "request_hash": request_hash, "urls": remaining_urls,
                               "stage": "post_links" if capability == "author_posts" else "document"}
                complete = False
        except (_Failure, PublicSourceError, ValueError) as exc:
            error = exc if isinstance(exc, _Failure) else _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_LINKEDIN_PUBLIC_INPUT")
        return self.result(capability, items, originals, error=error, cursor=cursor, next_cursor=next_cursor,
            comments=capability == "comments", complete=complete, extra=extra)


register_adapter("linkedin", LinkedInAdapter)
