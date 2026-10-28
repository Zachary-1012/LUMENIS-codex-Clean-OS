"""YouTube public documents/feeds and an explicitly selected Data API provider.

No credential discovery, fallback provider, schedule, or original video download.
Official thumbnails are source media observations, not video-stream assets.

Public renderer/bootstrap extraction adapts OpenCLI (Copyright 2025 jackwener),
Apache-2.0, https://github.com/jackwener/OpenCLI/tree/aeaff2b796efabb7fd46654112418ab61fcae917/clis/youtube
utils.js, video.js, channel.js, search.js, feed.js and comments.js. Modified for
LUMENIS: full text/native identity/nulls, Source custody and visible continuation;
COOKIE/SAPISID/auth/writes and direct continuation replay are excluded.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlsplit

import requests
import feedparser
from bs4 import BeautifulSoup

from .base import AccessClass, BasePlatformAdapter, CollectionResult, CollectionStatus
from .platform_naming import map_raw_to_normalized
from .registry import register_adapter
from .public_source import fetch_public_url, PublicSourceError, public_source_error_metadata, public_source_provenance
from .browser import read_public_document, select_public_transport


class _Failure(Exception):
    def __init__(self, status: CollectionStatus, code: str, **metadata: Any) -> None:
        self.status, self.code, self.metadata = status, code, metadata
        super().__init__(code)


def _text(value):
    return value if isinstance(value, str) and value.strip() else None


def _number(value):
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return int(value) if isinstance(value, str) and value.isascii() and value.isdigit() else None


def _bound(value, default, maximum):
    return max(1, min(value, maximum)) if isinstance(value, int) and not isinstance(value, bool) else default


class YouTubeAdapter(BasePlatformAdapter):
    platform = "youtube"
    enabled = False
    monitor_priority = "optional"
    RAW_CONTENT_TABLE = "youtube_videos"
    RAW_COMMENT_TABLE = "youtube_comments"
    RAW_USER_TABLE = "youtube_channels"
    _ORIGIN = "https://www.googleapis.com/youtube/v3/"

    def __init__(self, *, provider_config: Mapping[str, Any] | None = None,
                 api_key: str | None = None, http_client: Any = None, public_fetcher=None, **kwargs):
        super().__init__(**kwargs)
        config = dict(provider_config or {})
        self._provider_mode = config.get("provider_mode") or "public"
        self._public_transport = config.get("public_transport")
        self._public_fetcher = public_fetcher
        self._use_server_configuration = provider_config is None and api_key is None
        self._configuration_error = False
        self._api_key = api_key if api_key is not None else config.get("api_key")
        self._client = http_client
        self._timeout = _bound(config.get("timeout_seconds"), 20, 60)
        self._refresh_configuration()

    def _refresh_configuration(self):
        """Resolve only this provider's keys through the existing SYSTEM owner.

        Config.get owns process injection / protected local configuration. Never
        use get_all, browser state, a Cookie pool, or a new credential store.
        Refresh on each read so a cached adapter honors owner key withdrawal.
        """
        if not self._use_server_configuration:
            return
        try:
            from config import get_config
            owner = get_config()
            self._api_key = owner.get("LUMENIS_YOUTUBE_API_KEY")
            self._timeout = _bound(owner.get("LUMENIS_YOUTUBE_TIMEOUT_SECONDS"), 20, 60)
            self._configuration_error = False
        except Exception:
            self._api_key = None
            self._configuration_error = True

    def capability_map(self):
        return {name: "implemented" for name in
                ("search", "detail", "comments", "author", "author_posts", "healthcheck")}

    def normalize_to_platform_contents(self, raw_record):
        result = map_raw_to_normalized(raw_record, self.platform)
        if isinstance(raw_record.get("media_list"), list):
            result["media_list"] = raw_record["media_list"]
        return result

    @staticmethod
    def _video_id(value):
        value = str(value).strip()
        if value.startswith(("https://", "http://")):
            parsed = urlsplit(value)
            if parsed.hostname in {"youtu.be", "www.youtu.be"}:
                value = parsed.path.strip("/").split("/")[0]
            elif parsed.hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
                parts = parsed.path.strip("/").split("/")
                value = (parse_qs(parsed.query).get("v", [""])[0] if parsed.path == "/watch"
                         else parts[1] if len(parts) == 2 and parts[0] in {"shorts", "embed", "live", "v"} else "")
            else:
                value = ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_VIDEO_ID")
        return value

    @staticmethod
    def _token(value):
        if value is None:
            return None
        if not isinstance(value, str) or not value or len(value) > 4096 or any(ord(c) < 32 for c in value):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_NATIVE_PAGE_TOKEN")
        return value

    def _read(self, endpoint, params, originals):
        self._refresh_configuration()
        if self._configuration_error:
            raise _Failure(CollectionStatus.NOT_CONFIGURED, "YOUTUBE_SERVER_CONFIGURATION_UNAVAILABLE")
        if not _text(self._api_key):
            raise _Failure(CollectionStatus.NOT_CONFIGURED, "YOUTUBE_DATA_API_KEY_NOT_CONFIGURED")
        if self._client is None:
            self._client = requests.Session()
        try:
            response = self._client.get(self._ORIGIN + endpoint,
                params={**{k: v for k, v in params.items() if v is not None}, "key": self._api_key},
                headers={"Accept": "application/json"}, auth=lambda request: request,
                timeout=self._timeout, allow_redirects=False)
        except requests.RequestException as exc:
            raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "YOUTUBE_TRANSPORT_ERROR",
                           error_type=type(exc).__name__) from None
        status = response.status_code
        if 300 <= status < 400:
            raise _Failure(CollectionStatus.BLOCKED, "OFFICIAL_API_REDIRECT_BLOCKED", http_status=status)
        try:
            payload = response.json()
        except (ValueError, TypeError):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_API_JSON", http_status=status) from None
        if not isinstance(payload, dict):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_API_RESPONSE", http_status=status)
        if status != 200 or "error" in payload:
            error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
            errors = error.get("errors") if isinstance(error.get("errors"), list) else []
            reason = errors[0].get("reason") if errors and isinstance(errors[0], dict) else None
            reason = reason if isinstance(reason, str) and re.fullmatch(r"[A-Za-z0-9_]{1,100}", reason) else "API_REQUEST_REJECTED"
            state = (CollectionStatus.COOLING_DOWN if status == 429 or reason in
                     {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded", "userRateLimitExceeded"}
                     else CollectionStatus.SESSION_EXPIRED if status == 401
                     else CollectionStatus.NOT_CONFIGURED if reason in {"keyInvalid", "accessNotConfigured", "ipRefererBlocked"}
                     else CollectionStatus.NOT_SUPPORTED if reason == "commentsDisabled"
                     else CollectionStatus.BLOCKED if status in {400, 403}
                     else CollectionStatus.PROVIDER_UNAVAILABLE if status >= 500 else CollectionStatus.COLLECT_ERROR)
            metadata = {"http_status": status, "provider_code": reason}
            retry = response.headers.get("Retry-After")
            if isinstance(retry, str) and retry.isdigit():
                metadata["retry_after_seconds"] = int(retry)
            raise _Failure(state, reason, **metadata)
        originals.append(payload)
        return payload

    @staticmethod
    def _video(native, observed, discovery=None):
        snippet = native.get("snippet") if isinstance(native.get("snippet"), dict) else {}
        stats = native.get("statistics") if isinstance(native.get("statistics"), dict) else {}
        details = native.get("contentDetails") if isinstance(native.get("contentDetails"), dict) else {}
        video_id = native.get("id")
        if isinstance(video_id, dict):
            video_id = video_id.get("videoId")
        video_id = video_id or details.get("videoId")
        if not _text(video_id):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "VIDEO_NATIVE_ID_MISSING")
        thumbs = snippet.get("thumbnails") if isinstance(snippet.get("thumbnails"), dict) else {}
        media = [{"kind": "image", "url": item["url"], "role": "thumbnail",
                  "width": item.get("width"), "height": item.get("height"),
                  "locator": f"snippet.thumbnails.{name}.url"}
                 for name, item in thumbs.items() if isinstance(item, dict) and _text(item.get("url"))]
        raw = {**native, "video_id": video_id, "channel_id": snippet.get("channelId"),
               "channel_title": snippet.get("channelTitle"), "title": snippet.get("title"),
               "description": snippet.get("description"), "published_at": snippet.get("publishedAt"),
               "view_count": _number(stats.get("viewCount")), "like_count": _number(stats.get("likeCount")),
               "comment_count": _number(stats.get("commentCount")), "favorite_count": None,
               "duration": details.get("duration"), "tags": snippet.get("tags"),
               "default_language": snippet.get("defaultLanguage"), "media_type": "video",
               "url": f"https://www.youtube.com/watch?v={video_id}", "media_list": media,
               "captured_at": observed, "collected_at": observed,
               "metric_availability": {"favorite_count": "DEPRECATED_NOT_MEANINGFUL", "share_count": "NOT_EXPOSED_BY_DATA_API"},
               "original_media_state": "NOT_EXPOSED_BY_DATA_API"}
        if discovery is not None:
            raw["discovery_observation"] = discovery
        return {"platform_content_id": video_id, "title": raw["title"], "content": raw["description"],
                "author_id": raw["channel_id"], "author_nickname": raw["channel_title"],
                "publish_datetime": raw["published_at"], "url": raw["url"],
                "likes": raw["like_count"], "comments": raw["comment_count"], "collects": None, "shares": None,
                "cover": media[-1]["url"] if media else None, "media_list": media,
                "captured_at": observed, "raw": raw}

    def _result(self, capability, items, originals, *, request_cursor=None, next_cursor=None,
                error=None, comments=False, extra=None):
        page = {"request_cursor": request_cursor, "next_cursor": next_cursor,
                "exhausted": next_cursor is None and error is None, "page_complete": error is None,
                "coverage_scope": "REQUESTED_OFFICIAL_API_RESOURCE", "continuation_is_authorization": False}
        return CollectionResult(status=error.status if error else CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
            platform=self.platform, items=[] if comments else items, comments=items if comments else [],
            message=error.code if error else "YouTube official API observations returned", raw_count=len(items),
            metadata={"provider": "youtube_data_api_v3", "source_page": page, "pagination": page,
                "coverage_complete": next_cursor is None and error is None, "write_enabled": False,
                **(extra or {}), **({"error_code": error.code, **error.metadata} if error else {})},
            access_class=AccessClass.Z2_OFFICIAL_API if originals else None,
            backend="youtube_data_api_v3" if originals else None, capability=capability,
            attempted_access_class=AccessClass.Z2_OFFICIAL_API, attempted_backend="youtube_data_api_v3",
            actual_access_state="SOURCE_OBSERVED" if originals else "NOT_OBSERVED", original_response=originals or None)

    def _videos_page(self, endpoint, params, capability, cursor, **kwargs):
        originals, items = [], []
        token, error = None, None
        observed = datetime.now(timezone.utc).isoformat()
        remaining = _bound(kwargs.get("max_results"), 20, 1000)
        try:
            token = self._token(cursor)
            for _ in range(_bound(kwargs.get("max_pages"), 1, 100)):
                if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                    raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
                response = self._read(endpoint, {**params, "maxResults": min(50, remaining), "pageToken": token}, originals)
                records = response.get("items")
                if not isinstance(records, list) or any(not isinstance(x, dict) for x in records):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_VIDEO_LIST_RESPONSE")
                identifiers = []
                for record in records:
                    identity = record.get("id") if endpoint == "search" else record.get("contentDetails")
                    ident = identity.get("videoId") if isinstance(identity, dict) else None
                    if not _text(ident):
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "VIDEO_NATIVE_ID_MISSING")
                    identifiers.append(ident)
                enriched = self._read("videos", {"part": "snippet,contentDetails,statistics,status",
                    "id": ",".join(identifiers)}, originals) if identifiers else {"items": []}
                if not isinstance(enriched.get("items"), list):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_VIDEO_DETAIL_RESPONSE")
                by_id = {record.get("id"): record for record in enriched["items"] if isinstance(record, dict)}
                for ident, discovery in zip(identifiers, records):
                    native = by_id.get(ident)
                    if native is None:
                        native = {**discovery, "id": ident, "detail_availability": "NOT_RETURNED_BY_API"}
                        if endpoint == "playlistItems":
                            # Playlist insertion time is not video publication time.
                            snippet = dict(discovery.get("snippet") or {})
                            snippet["publishedAt"] = (discovery.get("contentDetails") or {}).get("videoPublishedAt")
                            native["snippet"] = snippet
                    items.append(self._video(native, observed, discovery))
                previous = token
                token = self._token(response.get("nextPageToken"))
                if token is not None and token == previous:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "REPEATED_NATIVE_PAGE_TOKEN")
                remaining -= len(records)
                if token is None or remaining <= 0:
                    break
                if not records:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "EMPTY_PAGE_WITH_CONTINUATION")
        except _Failure as exc:
            error = exc
        return self._result(capability, items, originals, request_cursor=cursor, next_cursor=token, error=error)

    def _official_search(self, keyword: str, **kwargs):
        if not _text(keyword):
            return self._result("search", [], [], error=_Failure(CollectionStatus.COLLECT_ERROR, "SEARCH_QUERY_REQUIRED"))
        params = {"part": "snippet", "type": "video", "q": keyword, "order": kwargs.get("sort", "relevance")}
        if params["order"] not in {"date", "rating", "relevance", "title", "videoCount", "viewCount"}:
            return self._result("search", [], [], error=_Failure(CollectionStatus.COLLECT_ERROR, "INVALID_SEARCH_ORDER"))
        for key in ("publishedAfter", "publishedBefore", "regionCode", "relevanceLanguage", "channelId"):
            if key in kwargs:
                params[key] = kwargs[key]
        cursor = kwargs.pop("cursor", None)
        fingerprint = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        if cursor is not None and (not isinstance(cursor, dict) or cursor.get("kind") != "youtube.search.v1"
                or cursor.get("query_hash") != fingerprint):
            return self._result("search", [], [], request_cursor=cursor,
                error=_Failure(CollectionStatus.COLLECT_ERROR, "SEARCH_CURSOR_SCOPE_MISMATCH"))
        result = self._videos_page("search", params, "search", cursor.get("page_token") if cursor else None, **kwargs)
        page = result.metadata["pagination"]
        page["request_cursor"] = cursor
        if page["next_cursor"]:
            page["next_cursor"] = {"kind": "youtube.search.v1", "query_hash": fingerprint, "page_token": page["next_cursor"]}
        return result

    def _official_detail(self, content_id: str, **kwargs):
        originals, items, error = [], [], None
        try:
            response = self._read("videos", {"part": "snippet,contentDetails,statistics,status",
                                           "id": self._video_id(content_id)}, originals)
            if not isinstance(response.get("items"), list):
                raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_VIDEO_DETAIL_RESPONSE")
            items = [self._video(x, datetime.now(timezone.utc).isoformat()) for x in response["items"] if isinstance(x, dict)]
        except _Failure as exc:
            error = exc
        return self._result("detail", items, originals, error=error)

    @staticmethod
    def _comment(native, video_id, observed):
        snippet = native.get("snippet") if isinstance(native.get("snippet"), dict) else {}
        ident = _text(native.get("id"))
        if ident is None:
            raise _Failure(CollectionStatus.COLLECT_ERROR, "COMMENT_NATIVE_ID_MISSING")
        author = snippet.get("authorChannelId") if isinstance(snippet.get("authorChannelId"), dict) else {}
        return {"platform_comment_id": ident, "parent_content_id": video_id,
                "parent_comment_id": snippet.get("parentId"), "reply_to_comment_id": None,
                "content": snippet.get("textOriginal", snippet.get("textDisplay")),
                "author_id": author.get("value"), "author_nickname": snippet.get("authorDisplayName"),
                "publish_datetime": snippet.get("publishedAt"), "likes": _number(snippet.get("likeCount")),
                "url": f"https://www.youtube.com/watch?v={video_id}&lc={ident}",
                "captured_at": observed, "raw": native}

    def _official_comments(self, content_id: str, *, include_replies=False, **kwargs):
        originals, items = [], []
        cursor = kwargs.get("cursor")
        token, pending, done, error, video_id = None, [], False, None, None
        observed = datetime.now(timezone.utc).isoformat()
        remaining = _bound(kwargs.get("max_results"), 100, 2000)
        order = "time" if kwargs.get("sort") == "time" else "relevance"
        try:
            video_id = self._video_id(content_id)
            if cursor is not None:
                if (not isinstance(cursor, dict) or cursor.get("kind") != "youtube.comments.v1"
                        or cursor.get("video_id") != video_id or cursor.get("include_replies") is not include_replies
                        or cursor.get("order") != order
                        or not isinstance(cursor.get("pending_replies"), list) or type(cursor.get("threads_done")) is not bool):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "COMMENT_CURSOR_SCOPE_MISMATCH")
                token = self._token(cursor.get("page_token"))
                if any(not isinstance(x, dict) for x in cursor["pending_replies"]):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_REPLY_CURSOR")
                pending = [dict(x) for x in cursor["pending_replies"]]
                done = cursor["threads_done"]
            for _ in range(_bound(kwargs.get("max_pages"), 10, 100)):
                if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                    raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
                if pending:
                    entry = pending[0]
                    if not _text(entry.get("parent_id")):
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_REPLY_CURSOR")
                    response = self._read("comments", {"part": "snippet", "parentId": entry["parent_id"],
                        "pageToken": self._token(entry.get("page_token")), "maxResults": min(100, remaining),
                        "textFormat": "plainText"}, originals)
                    records = response.get("items")
                    if not isinstance(records, list) or any(not isinstance(x, dict) for x in records):
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_COMMENTS_RESPONSE")
                    items.extend(self._comment(x, video_id, observed) for x in records)
                    next_token = self._token(response.get("nextPageToken"))
                    if next_token and next_token == entry.get("page_token"):
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "REPEATED_REPLY_PAGE_TOKEN")
                    if next_token:
                        pending[0] = {"parent_id": entry["parent_id"], "page_token": next_token}
                    else:
                        pending.pop(0)
                elif not done:
                    response = self._read("commentThreads", {"part": "snippet", "videoId": video_id,
                        "pageToken": token, "maxResults": min(100, remaining), "textFormat": "plainText",
                        "order": order}, originals)
                    records = response.get("items")
                    if not isinstance(records, list) or any(not isinstance(x, dict) for x in records):
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_COMMENT_THREADS_RESPONSE")
                    for thread in records:
                        snippet = thread.get("snippet") if isinstance(thread.get("snippet"), dict) else {}
                        if not isinstance(snippet.get("topLevelComment"), dict):
                            raise _Failure(CollectionStatus.COLLECT_ERROR, "TOP_LEVEL_COMMENT_MISSING")
                        mapped = self._comment(snippet["topLevelComment"], video_id, observed)
                        items.append(mapped)
                        count = _number(snippet.get("totalReplyCount"))
                        if include_replies and (count is None or count > 0):
                            pending.append({"parent_id": mapped["platform_comment_id"], "page_token": None})
                    previous = token
                    token = self._token(response.get("nextPageToken"))
                    if token is not None and token == previous:
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "REPEATED_THREAD_PAGE_TOKEN")
                    done = token is None
                else:
                    break
                remaining -= len(records)
                if remaining <= 0 or (done and not pending):
                    break
        except _Failure as exc:
            error = exc
        next_cursor = ({"kind": "youtube.comments.v1", "video_id": video_id, "include_replies": include_replies,
                        "page_token": token, "threads_done": done, "pending_replies": pending, "order": order}
                       if video_id and (not done or pending) else None)
        return self._result("comments", items, originals, request_cursor=cursor, next_cursor=next_cursor,
            error=error, comments=True, extra={"reply_scope": "ALL_API_VISIBLE_REPLIES" if include_replies else "TOP_LEVEL_ONLY"})

    def _channel(self, value, originals):
        value = str(value).strip()
        if value.startswith("https://"):
            parsed = urlsplit(value)
            if parsed.hostname not in {"youtube.com", "www.youtube.com"}:
                raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_CHANNEL_ID")
            value = parsed.path.removeprefix("/channel/").strip("/")
        if value.startswith("@") and re.fullmatch(r"@[^\s/?#]{3,100}", value):
            selector = {"forHandle": value}
        elif re.fullmatch(r"UC[A-Za-z0-9_-]{22}", value):
            selector = {"id": value}
        else:
            raise _Failure(CollectionStatus.COLLECT_ERROR, "CHANNEL_ID_OR_HANDLE_REQUIRED")
        response = self._read("channels", {"part": "snippet,contentDetails,statistics,brandingSettings", **selector}, originals)
        if not isinstance(response.get("items"), list):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_CHANNEL_RESPONSE")
        if any(not isinstance(x, dict) or not _text(x.get("id")) for x in response["items"]):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "CHANNEL_NATIVE_ID_MISSING")
        return response["items"][0] if response["items"] and isinstance(response["items"][0], dict) else None

    def _official_creator(self, creator_id: str, **kwargs):
        originals, items, error = [], [], None
        try:
            channel = self._channel(creator_id, originals)
            if channel:
                snippet = channel.get("snippet") if isinstance(channel.get("snippet"), dict) else {}
                stats = channel.get("statistics") if isinstance(channel.get("statistics"), dict) else {}
                aliases = [value for value in (channel.get("id"), snippet.get("customUrl")) if _text(value)]
                items.append({"platform_content_id": channel.get("id"), "author_id": channel.get("id"),
                    "author_nickname": snippet.get("title"), "title": snippet.get("title"),
                    "content": snippet.get("description"), "publish_datetime": snippet.get("publishedAt"),
                    "url": f"https://www.youtube.com/channel/{channel['id']}" if channel.get("id") else None,
                    "native_author_aliases": aliases,
                    "captured_at": datetime.now(timezone.utc).isoformat(), "raw": {**channel, "record_kind": "author",
                        "channel_id": channel.get("id"), "native_author_aliases": aliases,
                        "subscriber_count": None if stats.get("hiddenSubscriberCount") is True else _number(stats.get("subscriberCount")),
                        "subscriber_count_precision": "YOUTUBE_ROUNDED" if stats.get("hiddenSubscriberCount") is not True else "HIDDEN"}})
        except _Failure as exc:
            error = exc
        return self._result("author", items, originals, error=error, extra={"record_kind": "author"})

    def _official_author_posts(self, author_id: str, **kwargs):
        originals, cursor = [], kwargs.get("cursor")
        try:
            channel = self._channel(author_id, originals)
            if channel is None:
                return self._result("author_posts", [], originals)
            details = channel.get("contentDetails") if isinstance(channel.get("contentDetails"), dict) else {}
            related = details.get("relatedPlaylists") if isinstance(details.get("relatedPlaylists"), dict) else {}
            playlist = _text(related.get("uploads"))
            if not playlist:
                raise _Failure(CollectionStatus.NOT_SUPPORTED, "UPLOADS_PLAYLIST_NOT_RETURNED")
            if cursor is not None and (not isinstance(cursor, dict) or cursor.get("kind") != "youtube.uploads.v1"
                    or cursor.get("channel_id") != channel.get("id") or cursor.get("playlist_id") != playlist):
                raise _Failure(CollectionStatus.COLLECT_ERROR, "UPLOADS_CURSOR_SCOPE_MISMATCH")
            result = self._videos_page("playlistItems", {"part": "snippet,contentDetails", "playlistId": playlist},
                "author_posts", cursor.get("page_token") if cursor else None,
                **{k: v for k, v in kwargs.items() if k != "cursor"})
            page = result.metadata["source_page"]
            page["request_cursor"] = cursor
            if page["next_cursor"]:
                page["next_cursor"] = {"kind": "youtube.uploads.v1", "channel_id": channel["id"],
                                       "playlist_id": playlist, "page_token": page["next_cursor"]}
            result.original_response = originals + (result.original_response or [])
            return result
        except _Failure as exc:
            return self._result("author_posts", [], originals, request_cursor=cursor, error=exc)

    def _official_health_check(self, **kwargs):
        self._refresh_configuration()
        if self._configuration_error:
            return self._result("healthcheck", [], [], error=_Failure(CollectionStatus.NOT_CONFIGURED, "YOUTUBE_SERVER_CONFIGURATION_UNAVAILABLE"))
        if not _text(self._api_key):
            return self._result("healthcheck", [], [], error=_Failure(CollectionStatus.NOT_CONFIGURED, "YOUTUBE_DATA_API_KEY_NOT_CONFIGURED"))
        if kwargs.get("verify") is True:
            originals = []
            try:
                self._read("i18nLanguages", {"part": "snippet"}, originals)
                result = self._result("healthcheck", [], originals,
                    extra={"authorization_verification": "OFFICIAL_API_READ_VERIFIED", "can_attempt": True})
                result.status = CollectionStatus.SUCCESS
                return result
            except _Failure as exc:
                return self._result("healthcheck", [], originals, error=exc)
        return CollectionResult(CollectionStatus.SUCCESS, self.platform,
            message="YouTube API key configured; authorization and quota remain unverified",
            metadata={"provider": "youtube_data_api_v3", "can_attempt": True,
                      "authorization_verification": "NOT_VERIFIED", "network_attempted": False}, capability="healthcheck")


    def _selected_mode(self, kwargs):
        explicit = kwargs.pop("provider_mode", None)
        if explicit is None and self._use_server_configuration:
            from config import get_config
            explicit = get_config().get("LUMENIS_YOUTUBE_PROVIDER_MODE")
        mode = explicit or self._provider_mode
        if mode not in {"public", "official"}:
            raise _Failure(CollectionStatus.COLLECT_ERROR, "PROVIDER_MODE_INVALID")
        return mode

    def _dispatch(self, capability, value=None, **kwargs):
        try:
            mode = self._selected_mode(kwargs)
        except (ImportError, _Failure) as exc:
            error = exc if isinstance(exc, _Failure) else _Failure(CollectionStatus.NOT_CONFIGURED, "SERVER_CONFIGURATION_UNAVAILABLE")
            return _YouTubePublic(self._public_fetcher).result(capability, [], [], error=error)
        if mode == "official":
            method = getattr(self, "_official_" + capability)
            result = method(**kwargs) if capability == "health_check" else method(value, **kwargs)
            result.metadata["provider_mode"] = "official"
            return result
        kwargs.setdefault("_configured_public_transport", self._public_transport)
        kwargs.setdefault("_server_public_transport", self._use_server_configuration)
        return _YouTubePublic(self._public_fetcher).read(capability, value, **kwargs)

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



class _YouTubePublic:
    """Read only the source's public document or explicitly selected Atom feed."""

    backend = "youtube_public_document"

    def __init__(self, fetcher=None):
        self.fetcher = fetcher or fetch_public_url
        self.transport = "http"
        self.browser_observations = []
        self.options = {}

    @staticmethod
    def _walk(value, key):
        stack, visited = [value], 0
        while stack and visited < 100_000:
            node = stack.pop()
            visited += 1
            if isinstance(node, dict):
                if isinstance(node.get(key), dict):
                    yield node[key]
                stack.extend(reversed(list(node.values())))
            elif isinstance(node, list):
                stack.extend(reversed(node))

    @staticmethod
    def _plain(value):
        if isinstance(value, str):
            return value
        if not isinstance(value, dict):
            return None
        if isinstance(value.get("simpleText"), str):
            return value["simpleText"]
        if isinstance(value.get("content"), str):
            return value["content"]
        runs = value.get("runs")
        return "".join(x["text"] for x in runs if isinstance(x, dict) and isinstance(x.get("text"), str)) if isinstance(runs, list) else None

    @staticmethod
    def _initial(soup, name):
        decoder = json.JSONDecoder()
        for script in soup.find_all("script"):
            text = script.string or script.get_text()
            for marker in (rf"\b{re.escape(name)}\s*=", rf'window\["{re.escape(name)}"\]\s*='):
                found = re.search(marker, text)
                if found:
                    try:
                        value, _ = decoder.raw_decode(text[found.end():].lstrip())
                    except ValueError:
                        continue
                    if isinstance(value, dict):
                        return value
        return {}

    @staticmethod
    def _url(value):
        parsed = urlsplit(str(value))
        if (parsed.scheme != "https" or parsed.hostname not in
                {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}
                or parsed.username or parsed.password or parsed.port not in {None, 443}):
            raise _Failure(CollectionStatus.BLOCKED, "YOUTUBE_PUBLIC_URL_OUTSIDE_PLATFORM")
        return parsed._replace(fragment="").geturl()

    def _read(self, url, originals):
        url = self._url(url)
        try:
            reply_parent = self.options.get("_reply_parent")
            reply_action = None
            if _text(reply_parent):
                reply_action = """() => { const wanted = %s;
                  for (const thread of document.querySelectorAll('ytd-comment-thread-renderer')) {
                    const data=thread.data || {}, view=data.commentViewModel?.commentViewModel || {};
                    const id=view.commentId || data.comment?.commentRenderer?.commentId;
                    if (id !== wanted) continue;
                    const control=thread.querySelector('ytd-comment-replies-renderer #more-replies button,ytd-comment-replies-renderer #continuation button');
                    if (control && control.getClientRects().length) {control.click();return true;}
                  } return false;
                }""" % json.dumps(reply_parent)
            response, browser = read_public_document(url, originals, fetcher=self.fetcher,
                transport=self.transport, timeout=20, allowed_host_suffixes=("youtube.com", "youtu.be"),
                browser_plan={"asset_host_suffixes": ("ytimg.com", "ggpht.com", "gstatic.com"),
                    "capture_paths": (r"/youtubei/v1/(?:search|browse|next)",),
                    "request_keys": ("continuation", "videoId", "browseId", "params"),
                    "read_controls": ("ytd-comments #header", "ytd-continuation-item-renderer #button button")
                        if self.options.get("_capability") == "comments" else (),
                    "cursor": self.options.get("_browser_cursor"),
                    "read_action_script": reply_action,
                    "max_steps": _bound(self.options.get("browser_max_steps"), 16 if self.options.get("_browser_cursor") else 2, 40),
                    "cancel_check": self.options.get("cancel_check"),
                    "extraction_script": "() => ({initial:window.ytInitialData || {},player:window.ytInitialPlayerResponse || {}})"})
            if browser:
                self.browser_observations.append(browser)
        except PublicSourceError as exc:
            metadata = public_source_error_metadata(exc)
            status = metadata.get("http_status")
            raise _Failure(CollectionStatus.NEED_VERIFY if getattr(exc, "failure_type", None) == "PUBLIC_BROWSER_VERIFICATION" else CollectionStatus.COOLING_DOWN if status == 429 else
                CollectionStatus.BLOCKED if status in {401, 403, 451} else CollectionStatus.PROVIDER_UNAVAILABLE,
                "YOUTUBE_PUBLIC_SOURCE_UNAVAILABLE", **metadata) from None
        self._url(response.url)
        soup = BeautifulSoup(response.content, "xml" if urlsplit(response.url).path == "/feeds/videos.xml" else "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        if (soup.select_one("form[action*='/sorry/'], #captcha, iframe[src*='recaptcha']")
                or "before you continue to youtube" in title.lower()
                or "sign in to confirm" in title.lower()):
            raise _Failure(CollectionStatus.NEED_VERIFY, "YOUTUBE_PUBLIC_VERIFICATION_REQUIRED")
        return response, soup

    @classmethod
    def _selected_grid(cls, payload):
        """OpenCLI extractSelectedRichGridContents: scope to the selected tab."""
        contents = payload.get("contents", {})
        tabs = contents.get("twoColumnBrowseResultsRenderer", {}).get("tabs", []) if isinstance(contents, dict) else []
        grids = []
        for wrapped in tabs if isinstance(tabs, list) else []:
            tab = wrapped.get("tabRenderer", {}) if isinstance(wrapped, dict) else {}
            grid = tab.get("content", {}).get("richGridRenderer", {}).get("contents") if isinstance(tab.get("content"), dict) else None
            if isinstance(grid, list):
                if tab.get("selected"):
                    return grid
                grids.append(grid)
        return next((grid for grid in grids if grid), grids[0] if grids else payload)

    @classmethod
    def _lockup_video(cls, lockup):
        """Adapt OpenCLI's modern lockup and Shorts readers without fake counts."""
        if lockup.get("contentType") != "LOCKUP_CONTENT_TYPE_VIDEO":
            return None
        ident = lockup.get("contentId")
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", ident):
            return None
        metadata = lockup.get("metadata", {}).get("lockupMetadataViewModel", {})
        rows = metadata.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
        parts = [cls._plain(part.get("text")) for row in rows if isinstance(row, dict)
            for part in row.get("metadataParts", []) if isinstance(part, dict)]
        browse = next(cls._walk(metadata, "browseEndpoint"), {})
        thumbs = lockup.get("contentImage", {}).get("thumbnailViewModel", {}).get("image", {}).get("sources", [])
        return {"videoId": ident, "title": metadata.get("title"), "ownerText": {"simpleText": parts[0] if parts else "",
                "runs": [{"text": parts[0] if parts else "", "navigationEndpoint": {"browseEndpoint": browse}}]},
            "viewCountText": {"simpleText": parts[1] if len(parts) > 1 else ""},
            "publishedTimeText": {"simpleText": parts[2] if len(parts) > 2 else ""},
            "thumbnail": {"thumbnails": thumbs}, "native_lockup_view_model": lockup}

    @classmethod
    def _native_videos(cls, payload):
        for key in ("videoRenderer", "gridVideoRenderer", "playlistVideoRenderer"):
            yield from cls._walk(payload, key)
        for lockup in cls._walk(payload, "lockupViewModel"):
            video = cls._lockup_video(lockup)
            if video:
                yield video
        for short in cls._walk(payload, "shortsLockupViewModel"):
            command = short.get("onTap", {}).get("innertubeCommand", {})
            ident = command.get("reelWatchEndpoint", {}).get("videoId")
            if not ident:
                ident = short.get("inlinePlayerData", {}).get("onVisible", {}).get("innertubeCommand", {}).get("watchEndpoint", {}).get("videoId")
            if ident:
                yield {"videoId": ident, "title": short.get("overlayMetadata", {}).get("primaryText"),
                    "viewCountText": short.get("overlayMetadata", {}).get("secondaryText"), "native_shorts_lockup": short}
        for reel in cls._walk(payload, "reelItemRenderer"):
            if reel.get("videoId"):
                yield {**reel, "title": reel.get("headline")}

    @classmethod
    def _continuations(cls, payload):
        found = []
        parents = {}
        for thread in cls._walk(payload, "commentThreadRenderer"):
            view = thread.get("commentViewModel", {})
            view = view.get("commentViewModel", view) if isinstance(view, dict) else {}
            top = thread.get("comment", {}).get("commentRenderer", {})
            parent = view.get("commentId") or top.get("commentId")
            if _text(parent):
                for continuation in cls._walk(thread.get("replies", {}), "continuationCommand"):
                    if _text(continuation.get("token")):
                        parents[continuation["token"]] = parent
        for continuation in cls._walk(payload, "continuationItemRenderer"):
            endpoint = continuation.get("continuationEndpoint", {})
            token = endpoint.get("continuationCommand", {}).get("token")
            api = endpoint.get("commandMetadata", {}).get("webCommandMetadata", {}).get("apiUrl")
            if _text(token) and len(token) <= 4096:
                found.append({"token": token, "api_path": api, "target_id": continuation.get("targetId"),
                    "parent_comment_id": parents.get(token)})
        return found

    @staticmethod
    def _exact_count(value):
        if type(value) is int:
            return value if value >= 0 else None
        if isinstance(value, str) and re.fullmatch(r"[0-9][0-9,]*", value.strip()):
            return int(value.strip().replace(",", ""))
        return None

    def _video(self, data, observed, *, player=False, micro=None):
        ident = data.get("videoId")
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", ident):
            raise _Failure(CollectionStatus.COLLECT_ERROR, "YOUTUBE_PUBLIC_NATIVE_VIDEO_ID_MISSING")
        micro = micro or {}
        thumbnail = data.get("thumbnail") if isinstance(data.get("thumbnail"), dict) else {}
        thumbs = thumbnail.get("thumbnails") if isinstance(thumbnail.get("thumbnails"), list) else []
        media = [{"kind": "image", "role": "thumbnail", "url": x["url"],
                  "locator": f"thumbnail.thumbnails[{i}].url", "width": x.get("width"), "height": x.get("height")}
                 for i, x in enumerate(thumbs) if isinstance(x, dict) and _text(x.get("url"))]
        owner = data.get("ownerText") or data.get("shortBylineText") or {}
        runs = owner.get("runs") if isinstance(owner, dict) else []
        run = runs[0] if runs and isinstance(runs[0], dict) else {}
        navigation = run.get("navigationEndpoint") if isinstance(run.get("navigationEndpoint"), dict) else {}
        browse = navigation.get("browseEndpoint") if isinstance(navigation.get("browseEndpoint"), dict) else {}
        title = data.get("title") if player else self._plain(data.get("title"))
        description = data.get("shortDescription") if player else None
        if not player:
            detailed = data.get("detailedMetadataSnippets")
            description = self._plain(detailed[0].get("snippetText")) if isinstance(detailed, list) and detailed and isinstance(detailed[0], dict) else None
        channel = data.get("channelId") if player else browse.get("browseId")
        published = micro.get("publishDate") or micro.get("uploadDate")
        raw = {"native_public_renderer": data, "microformat": micro, "video_id": ident,
            "channel_id": channel, "channel_title": data.get("author") if player else self._plain(owner),
            "title": title, "description": description, "published_at": published,
            "publication_time_state": "NATIVE_PUBLIC_DATE" if published else "NOT_EXPOSED",
            "relative_publication_display": self._plain(data.get("publishedTimeText")),
            "url": f"https://www.youtube.com/watch?v={ident}", "media_type": "video",
            "view_count": self._exact_count(data.get("viewCount")) if player else None,
            "view_count_display": self._plain(data.get("viewCountText")),
            "like_count": None, "comment_count": None, "favorite_count": None,
            "media_list": media, "cover": media[-1]["url"] if media else None,
            "captured_at": observed, "collected_at": observed,
            "body_state": "COMPLETE_PUBLIC_DESCRIPTION" if player and description is not None else "PUBLIC_NATIVE_METADATA" if player else "SEARCH_SNIPPET",
            "original_media_state": "WATCH_REFERENCE_ONLY_NO_STREAM_EXTRACTION",
            "metric_states": {"likes": "NOT_EXPOSED", "comments": "NOT_EXPOSED", "shares": "NOT_EXPOSED"}}
        return {"platform_content_id": ident, "title": title, "content": description,
            "author_id": channel, "author_nickname": raw["channel_title"], "publish_datetime": published,
            "url": raw["url"], "likes": None, "comments": None, "shares": None, "collects": None,
            "views": raw["view_count"], "cover": raw["cover"], "media_list": media, "raw": raw, "captured_at": observed}

    def _feed(self, url, originals, observed):
        response, _ = self._read(url, originals)
        parsed = feedparser.parse(response.content)
        if parsed.get("bozo") and not parsed.entries:
            raise _Failure(CollectionStatus.COLLECT_ERROR, "YOUTUBE_PUBLIC_FEED_INVALID")
        requested = parse_qs(urlsplit(url).query).get("channel_id", [None])[0]
        items = []
        for entry in parsed.entries:
            ident, channel = entry.get("yt_videoid"), entry.get("yt_channelid")
            if not _text(ident) or not _text(channel) or requested is not None and channel != requested:
                raise _Failure(CollectionStatus.BLOCKED, "YOUTUBE_PUBLIC_FEED_IDENTITY_MISMATCH")
            native = {"videoId": ident, "channelId": channel, "title": entry.get("title"),
                "shortDescription": entry.get("media_description") or entry.get("summary"),
                "author": entry.get("author"), "thumbnail": {"thumbnails": entry.get("media_thumbnail") or []}}
            stats = entry.get("media_statistics") or {}
            native["viewCount"] = stats.get("views")
            item = self._video(native, observed, player=True, micro={"publishDate": entry.get("published")})
            item["raw"]["native_feed_entry"] = dict(entry)
            item["raw"]["body_state"] = "PUBLIC_FEED_ENTRY"
            items.append(item)
        return items

    def _comment_items(self, payload, video_id, observed, include_replies):
        """OpenCLI commentEntityPayload decoding plus preserved native threading."""
        result, seen, thread_parents = [], set(), {}
        for thread in self._walk(payload, "commentThreadRenderer"):
            top = thread.get("comment", {}).get("commentRenderer") if isinstance(thread.get("comment"), dict) else None
            top_view = thread.get("commentViewModel", {})
            top_view = top_view.get("commentViewModel", top_view) if isinstance(top_view, dict) else {}
            parent = top.get("commentId") if isinstance(top, dict) else top_view.get("commentId")
            for view in self._walk(thread.get("replies", {}), "commentViewModel"):
                if _text(view.get("commentId")) and _text(parent):
                    thread_parents[view["commentId"]] = parent
            for view in self._walk(thread.get("replies", {}), "commentRenderer"):
                if _text(view.get("commentId")) and _text(parent):
                    thread_parents[view["commentId"]] = parent
        for native in self._walk(payload, "commentRenderer"):
            ident = native.get("commentId")
            if not _text(ident) or ident in seen:
                continue
            parent = native.get("parentCommentId") or thread_parents.get(ident)
            if parent and not include_replies:
                continue
            endpoint = native.get("authorEndpoint", {}).get("browseEndpoint", {})
            result.append({"platform_comment_id": ident, "parent_content_id": video_id,
                "parent_comment_id": parent, "reply_to_comment_id": native.get("replyToCommentId"),
                "author_id": endpoint.get("browseId"), "author_nickname": self._plain(native.get("authorText")),
                "content": self._plain(native.get("contentText")), "publish_datetime": None,
                "likes": self._exact_count(self._plain(native.get("voteCount"))),
                "url": f"https://www.youtube.com/watch?v={video_id}&lc={quote(ident, safe='')}",
                "captured_at": observed, "raw": {**native, "publication_time_state": "RELATIVE_DISPLAY_ONLY"}})
            seen.add(ident)
        for native in self._walk(payload, "commentEntityPayload"):
            props = native.get("properties", {})
            author, toolbar = native.get("author", {}), native.get("toolbar", {})
            ident = props.get("commentId")
            if not _text(ident) or ident in seen:
                continue
            parent = props.get("parentCommentId") or props.get("parentId") or thread_parents.get(ident) or self.options.get("_reply_parent")
            reply_level = props.get("replyLevel")
            if not include_replies and (parent or type(reply_level) is int and reply_level > 0):
                continue
            if include_replies and type(reply_level) is int and reply_level > 0 and not parent:
                raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "YOUTUBE_NATIVE_REPLY_PARENT_NOT_EXPOSED")
            result.append({"platform_comment_id": ident, "parent_content_id": video_id,
                "parent_comment_id": parent, "reply_to_comment_id": props.get("replyToCommentId"),
                "author_id": author.get("channelId"), "author_nickname": author.get("displayName"),
                "content": self._plain(props.get("content")), "publish_datetime": None,
                "likes": self._exact_count(toolbar.get("likeCountNotliked")),
                "url": f"https://www.youtube.com/watch?v={video_id}&lc={quote(ident, safe='')}",
                "captured_at": observed, "raw": {**native, "publication_time_state": "RELATIVE_DISPLAY_ONLY",
                    "native_publication_display": props.get("publishedTime"), "native_reply_count_display": toolbar.get("replyCount")}})
            seen.add(ident)
        return result

    def result(self, capability, items, originals, *, error=None, cursor=None, next_cursor=None,
               comments=False, complete=False, extra=None):
        page = {"request_cursor": cursor, "next_cursor": next_cursor, "page_complete": error is None,
            "exhausted": complete and error is None, "coverage_scope": "PUBLIC_DOCUMENT_VISIBLE_ONLY",
            "continuation_is_authorization": False}
        provenance = public_source_provenance(originals[0], originals[0].requested_url or originals[0].url) if originals else {}
        return CollectionResult(error.status if error else CollectionStatus.SUCCESS if items else CollectionStatus.NO_NEW_DATA,
            "youtube", items=[] if comments else items, comments=items if comments else [], raw_count=len(items),
            message=error.code if error else "YouTube public source observations returned",
            metadata={"provider": self.backend, "provider_mode": "public", "source_page": page, "pagination": page,
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
            self.transport = select_public_transport("youtube", kwargs,
                configured=kwargs.get("_configured_public_transport"), use_server=kwargs.get("_server_public_transport", True))
            self.backend = "youtube_public_browser" if self.transport == "browser" else "youtube_public_document"
            self.options = {**kwargs, "_capability": capability}
            if capability == "health_check":
                return CollectionResult(CollectionStatus.SUCCESS, "youtube", capability="healthcheck",
                    attempted_backend=self.backend, attempted_access_class=AccessClass.Z0_PUBLIC,
                    metadata={"provider": self.backend, "provider_mode": "public", "can_attempt": True,
                        "requires_authorization": False, "network_attempted": False, "source_access": "NOT_VERIFIED"},
                    message="YouTube public source provider; no API key required")
            if callable(kwargs.get("cancel_check")) and kwargs["cancel_check"]():
                raise _Failure(CollectionStatus.BLOCKED, "CANCELLED")
            if capability == "search" and str(value).startswith("https://"):
                parsed = urlsplit(value)
                capability_path = "feed" if parsed.path == "/feeds/videos.xml" else "detail"
            else:
                capability_path = capability
            if capability_path == "detail" or capability == "comments":
                ident = YouTubeAdapter._video_id(value)
                url = f"https://www.youtube.com/watch?v={ident}"
            elif capability_path == "feed":
                url = self._url(value)
            elif capability == "search":
                if not _text(value):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "SEARCH_QUERY_REQUIRED")
                url = "https://www.youtube.com/results?" + urlencode({"search_query": value})
            else:
                selected = kwargs.get("feed_url")
                raw = str(value).strip()
                if selected:
                    url = self._url(selected)
                    capability_path = "feed"
                elif re.fullmatch(r"UC[A-Za-z0-9_-]{22}", raw):
                    url = f"https://www.youtube.com/channel/{raw}" + ("/videos" if capability == "author_posts" else "")
                elif re.fullmatch(r"@[^\s/?#]{1,100}", raw):
                    url = "https://www.youtube.com/" + quote(raw, safe="@") + ("/videos" if capability == "author_posts" else "")
                elif raw.startswith("https://"):
                    url = self._url(raw)
                    if capability == "author_posts" and not urlsplit(url).path.rstrip("/").endswith("/videos"):
                        url = url.rstrip("/") + "/videos"
                else:
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "PUBLIC_CHANNEL_ID_HANDLE_OR_URL_REQUIRED")
            request_hash = hashlib.sha256(json.dumps([capability, str(value), kwargs.get("feed_url"), self.transport,
                bool(kwargs.get("include_replies"))], ensure_ascii=False).encode()).hexdigest()
            source_url = url
            if cursor is not None:
                if (not isinstance(cursor, dict) or cursor.get("kind") not in {"youtube.public_page.v1", "youtube.public_native.v1"}
                        or cursor.get("request_hash") != request_hash):
                    raise _Failure(CollectionStatus.COLLECT_ERROR, "PUBLIC_PAGE_CURSOR_SCOPE_MISMATCH")
                url = self._url(cursor.get("url"))
                if cursor.get("kind") == "youtube.public_native.v1":
                    if self.transport != "browser":
                        raise _Failure(CollectionStatus.NOT_SUPPORTED, "YOUTUBE_NATIVE_CURSOR_REQUIRES_EXPLICIT_BROWSER_TRANSPORT")
                    pending = cursor.get("pending") or [{"native": cursor.get("native"), "parent_comment_id": cursor.get("parent_comment_id")}]
                    if (url != source_url or not isinstance(pending, list) or not pending or any(
                            not isinstance(entry, dict) or not isinstance(entry.get("native"), dict)
                            or not isinstance(entry["native"].get("request"), dict) or not entry["native"]["request"]
                            or entry.get("parent_comment_id") is not None and not _text(entry.get("parent_comment_id"))
                            for entry in pending)):
                        raise _Failure(CollectionStatus.COLLECT_ERROR, "YOUTUBE_NATIVE_CURSOR_INVALID")
                    self.options["_browser_cursor"] = pending[0].get("native")
                    self.options["_reply_parent"] = pending[0].get("parent_comment_id")
                    self.options["_pending_continuations"] = pending[1:]
            if capability_path == "feed":
                if self.transport == "browser":
                    raise _Failure(CollectionStatus.NOT_SUPPORTED, "YOUTUBE_ATOM_FEED_SELECT_HTTP_TRANSPORT")
                if capability == "author_posts" and re.fullmatch(r"UC[A-Za-z0-9_-]{22}", str(value)):
                    if parse_qs(urlsplit(url).query).get("channel_id") != [str(value)]:
                        raise _Failure(CollectionStatus.BLOCKED, "YOUTUBE_PUBLIC_FEED_AUTHOR_SCOPE_MISMATCH")
                items = self._feed(url, originals, observed)
                complete = True
                extra["feed_scope"] = "CURRENT_PUBLIC_FEED_WINDOW_NOT_FULL_CHANNEL_HISTORY"
            else:
                response, soup = self._read(url, originals)
                initial = self._initial(soup, "ytInitialData")
                browser = self.browser_observations[-1] if self.browser_observations else None
                if browser:
                    initial = browser.extraction.get("initial") or initial
                native_payloads = [obj for page in browser.native_pages for obj in page.get("objects", [])] if browser else []
                if self.options.get("_browser_cursor") and browser:
                    target = self.options["_browser_cursor"]
                    selected = [page for page in browser.native_pages if page.get("path") == target.get("path")
                        and all(page.get("request", {}).get(key) == value for key, value in target.get("request", {}).items())]
                    native_payloads = [obj for page in selected for obj in page.get("objects", [])]
                    initial = {}
                if capability_path == "detail":
                    player = self._initial(soup, "ytInitialPlayerResponse")
                    if browser:
                        player = browser.extraction.get("player") or player
                    details = player.get("videoDetails") if isinstance(player.get("videoDetails"), dict) else {}
                    status = player.get("playabilityStatus") if isinstance(player.get("playabilityStatus"), dict) else {}
                    if status.get("status") in {"LOGIN_REQUIRED", "AGE_CHECK_REQUIRED", "CONTENT_CHECK_REQUIRED"}:
                        raise _Failure(CollectionStatus.BLOCKED, "YOUTUBE_PUBLIC_VIDEO_REQUIRES_AUTHORIZATION")
                    micro = player.get("microformat", {}).get("playerMicroformatRenderer", {}) if isinstance(player.get("microformat"), dict) else {}
                    if details.get("videoId") != ident:
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "YOUTUBE_PUBLIC_VIDEO_DETAILS_NOT_EXPOSED")
                    items = [self._video(details, observed, player=True, micro=micro)]
                    primary = initial.get("contents", {}).get("twoColumnWatchNextResults", {}).get("results", {}).get("results", {})
                    secondary = next(self._walk(primary, "videoSecondaryInfoRenderer"), {})
                    full = self._plain(secondary.get("attributedDescription")) or self._plain(secondary.get("description"))
                    if full:
                        items[0]["content"] = full
                        items[0]["raw"]["description"] = full
                    owner = next(self._walk(primary, "videoOwnerRenderer"), {})
                    members_only = any(badge.get("style") == "BADGE_STYLE_TYPE_MEMBERS_ONLY" for badge in self._walk(primary, "metadataBadgeRenderer"))
                    items[0]["raw"].update(native_public_primary_column=primary, native_playability_status=status,
                        subscriber_count_display=self._plain(owner.get("subscriberCountText")),
                        channel_avatar=(owner.get("thumbnail", {}).get("thumbnails") or [{}])[-1].get("url"),
                        members_only=True if members_only else None)
                    complete = True
                elif capability == "comments":
                    seen = set()
                    initial_comments = initial.get("contents", {}).get("twoColumnWatchNextResults", {}).get("results", {}).get("results", initial)
                    for payload in [initial_comments, *native_payloads]:
                        for item in self._comment_items(payload, ident, observed, bool(kwargs.get("include_replies"))):
                            if item["platform_comment_id"] not in seen:
                                items.append(item)
                                seen.add(item["platform_comment_id"])
                    if not items:
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "PUBLIC_COMMENT_CONTINUATION_REQUIRES_CONTROLLED_BROWSER")
                    extra["reply_scope"] = "VISIBLE_NESTED" if kwargs.get("include_replies") else "VISIBLE_TOP_LEVEL"
                elif capability == "creator":
                    metadata = next(self._walk(initial, "channelMetadataRenderer"), {})
                    channel_id = metadata.get("externalId")
                    name = metadata.get("title")
                    if not _text(channel_id) or not _text(name):
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "PUBLIC_CHANNEL_IDENTITY_NOT_EXPOSED")
                    aliases = [channel_id]
                    for owner_url in [*(metadata.get("ownerUrls") or []), metadata.get("vanityChannelUrl")]:
                        path = urlsplit(owner_url).path.strip("/") if isinstance(owner_url, str) else ""
                        if path.startswith("@"):
                            aliases.append(path)
                    items = [{"platform_content_id": channel_id, "author_id": channel_id, "author_nickname": name,
                        "title": name, "content": metadata.get("description"), "url": metadata.get("channelUrl") or response.url,
                        "captured_at": observed, "native_author_aliases": aliases,
                        "raw": {**metadata, "record_kind": "author", "channel_id": channel_id,
                            "native_author_aliases": aliases, "profile_url": response.url}}]
                    complete = True
                else:
                    seen = set()
                    for payload in [self._selected_grid(initial) if capability == "author_posts" else initial, *native_payloads]:
                        for native in self._native_videos(payload):
                            if native.get("videoId") not in seen:
                                items.append(self._video(native, observed))
                                seen.add(native.get("videoId"))
                    empty = any(re.search(r"no results found|未找到结果|没有找到.*结果|검색\s*결과가\s*없", self._plain(node.get("text")) or "", re.I)
                                for node in self._walk(initial, "messageRenderer"))
                    if not items and not empty:
                        raise _Failure(CollectionStatus.PROVIDER_UNAVAILABLE, "PUBLIC_VIDEO_LIST_NOT_EXPOSED")
                    extra["content_semantics"] = "PUBLIC_NATIVE_SEARCH_OR_CHANNEL_SNIPPETS"
                for anchor in soup.select("a[rel~='next'][href]"):
                    next_url = self._url(urljoin(response.url, anchor["href"]))
                    next_cursor = {"kind": "youtube.public_page.v1", "url": next_url, "request_hash": request_hash}
                    break
                continuation_source = (initial.get("contents", {}).get("twoColumnWatchNextResults", {}).get("results", {}).get("results", initial)
                    if capability == "comments" else self._selected_grid(initial) if capability == "author_posts" else initial)
                continuations, seen_tokens = [], set()
                consumed_tokens = {page.get("request", {}).get("continuation") for page in browser.native_pages} if browser else set()
                for payload in [continuation_source, *native_payloads]:
                    for entry in self._continuations(payload):
                        if entry["token"] not in seen_tokens and entry["token"] not in consumed_tokens:
                            seen_tokens.add(entry["token"])
                            continuations.append(entry)
                if capability == "comments" and not kwargs.get("include_replies"):
                    continuations = [entry for entry in continuations if not entry.get("parent_comment_id")]
                has_continuation = bool(continuations)
                if continuations:
                    extra["native_continuations"] = continuations
                    if self.transport == "browser":
                        pending = list(self.options.get("_pending_continuations", []))
                        for continuation in continuations:
                            path = continuation.get("api_path") or ("/youtubei/v1/next" if capability == "comments" else
                                "/youtubei/v1/search" if capability == "search" else "/youtubei/v1/browse")
                            entry = {"native": {"path": path, "request": {"continuation": continuation["token"]}},
                                "parent_comment_id": continuation.get("parent_comment_id") or self.options.get("_reply_parent")}
                            if entry not in pending:
                                pending.append(entry)
                        next_cursor = {"kind": "youtube.public_native.v1", "request_hash": request_hash,
                            "url": url, "native": pending[0]["native"], "pending": pending}
                elif self.options.get("_pending_continuations"):
                    pending = self.options["_pending_continuations"]
                    next_cursor = {"kind": "youtube.public_native.v1", "request_hash": request_hash,
                        "url": url, "native": pending[0]["native"], "pending": pending}
                    complete = False
                if has_continuation and next_cursor is None:
                    extra["continuation_state"] = "CONTROLLED_BROWSER_NATIVE_READ_REQUIRED"
                    complete = False
                elif capability in {"search", "author_posts"}:
                    complete = not has_continuation and next_cursor is None
        except (_Failure, PublicSourceError, ValueError) as exc:
            error = exc if isinstance(exc, _Failure) else _Failure(CollectionStatus.COLLECT_ERROR, "INVALID_PUBLIC_SOURCE_INPUT")
        return self.result(capability, items, originals, error=error, cursor=cursor, next_cursor=next_cursor,
            comments=capability == "comments", complete=complete, extra=extra)


register_adapter("youtube", YouTubeAdapter)
