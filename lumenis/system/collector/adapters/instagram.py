from __future__ import annotations

import os
import re
import json
import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urlsplit
from pathlib import Path
from typing import Any, Dict, List, Optional

from lumenis.adapters.base import optional_int

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter
from .public_source import fetch_public_url, public_source_provenance
from .routing import resolve_capability_route

logger = logging.getLogger(__name__)


_TERMINAL_IG_DETAIL_STATES = frozenset({
    "VERIFICATION_REQUIRED",
    "RATE_LIMITED",
    "SESSION_UNAVAILABLE",
    "SESSION_OR_RISK_REQUIRED",
    "PLATFORM_RISK",
    "NOT_CONFIGURED",
    "BLOCKED",
    "PROVIDER_UNAVAILABLE",
    "COLLECT_ERROR",
    "IDENTITY_MISMATCH",
})

_SAFE_IG_EXCEPTION_REASONS = frozenset({
    "READONLY_WORKER_NOT_REGISTERED",
    "READONLY_WORKER_NOT_CONFIGURED",
    "READONLY_WORKER_PROFILE_UNAVAILABLE",
    "READONLY_WORKER_BOUNDARY_INVALID",
    "READONLY_WORKER_PROFILE_MODE_OR_KERNEL_UNAVAILABLE",
    "BROWSER_PROFILE_OWNER_UNAVAILABLE",
    "BROWSER_WORKER_KERNEL_OR_IDENTITY_UNVERIFIED",
    "BROWSER_WORKER_PROFILE_OR_MODE_UNAVAILABLE",
    "PROTECTED_PROFILE_FORBIDDEN",
    "INSTAGRAM_AUTH_REQUIRED",
    "INSTAGRAM_CHALLENGE_REQUIRED",
    "INSTAGRAM_RATE_LIMITED",
    "INSTAGRAM_NETWORK_UNAVAILABLE",
    "INSTAGRAM_WORKER_UNAVAILABLE",
})


def _safe_collection_error(exc: Exception) -> str:
    """Return only a known safe reason code or a non-sensitive exception class."""
    if isinstance(exc, RuntimeError):
        args = exc.args
        if len(args) == 1 and isinstance(args[0], str):
            reason = args[0]
            if reason in _SAFE_IG_EXCEPTION_REASONS:
                return reason
    name = type(exc).__name__
    safe_name = name if name.isascii() and name.isidentifier() else "Exception"
    return f"INSTAGRAM_COLLECT_ERROR:{safe_name}"


def parse_public_instagram_document(response, shortcode):
    """Inspect only the matching public post, keeping media/caption times distinct."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    matches = []
    def visit(value, locator):
        if isinstance(value, dict):
            if value.get('code') == shortcode and value.get('pk') and isinstance(value.get('if_not_gated_logged_out'), dict):
                matches.append((locator, value))
            for key, child in value.items():
                visit(child, locator + '/' + str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, locator + '/' + str(index))
    for index, script in enumerate(soup.find_all('script')):
        try:
            visit(json.loads(script.get_text()), f'script[{index}]')
        except (ValueError, TypeError):
            continue
    if len(matches) != 1:
        return None
    locator, media = matches[0]
    public = media['if_not_gated_logged_out']
    if str(public.get('pk')) != str(media['pk']) or public.get('code') != shortcode:
        return None
    caption = public.get('caption') or {}
    text = caption.get('text')
    if not isinstance(text, str) or not text.strip():
        return None
    user = public.get('user') or {}
    published = None
    taken_at = public.get('taken_at')
    if isinstance(taken_at, (int, float)) and not isinstance(taken_at, bool):
        try:
            published = datetime.fromtimestamp(taken_at, timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            pass
    def metric(key):
        value = public.get(key)
        return value if type(value) is int and value >= 0 else None
    comments = []
    for edge in (media.get('comments_connection') or {}).get('edges') or []:
        node = edge.get('node') or {}
        # Copy the public comment fields, never the surrounding viewer or tracking context.
        comment = {key: node[key] for key in ('pk', 'id', 'text', 'created_at', 'like_count') if key in node}
        comment_user = node.get('user')
        if isinstance(comment_user, dict):
            comment['user'] = {key: comment_user[key] for key in
                               ('pk', 'id', 'username', 'full_name', 'is_verified', 'profile_pic_url')
                               if key in comment_user}
        comments.append(comment)
    public_user = {key: user[key] for key in ('pk', 'username', 'full_name', 'is_verified') if key in user}
    raw = {'media_id': str(media['pk']), 'shortcode': shortcode, 'taken_at': taken_at,
           'caption': text, 'caption_created_at': caption.get('created_at'),
           'caption_is_edited': public.get('caption_is_edited'), 'author_id': str(user.get('pk')) if user.get('pk') else None,
           'author': public_user, 'like_count': metric('like_count'), 'comment_count': metric('comment_count'),
           'share_count': None, 'play_count': None, 'location': public.get('location'),
           'media_type': public.get('media_type'), 'display_uri': public.get('display_uri'),
           'video_versions': [{key: value[key] for key in ('type', 'url', 'width', 'height') if key in value}
                              for value in public.get('video_versions') or []],
           'public_comments': comments, 'comment_page_info': (media.get('comments_connection') or {}).get('page_info'),
           'native_document_sha256': hashlib.sha256(response.content).hexdigest(),
           'native_post_locator': locator, 'native_caption_locator': locator + '/if_not_gated_logged_out/caption/text',
           'native_time_locator': locator + '/if_not_gated_logged_out/taken_at',
           'native_hashtags': re.findall(r'#([^\s#]+)', text)}
    return {'platform': 'instagram', 'platform_content_id': str(media['pk']), 'url': response.url,
            'content': text, 'title': None, 'publish_datetime': published,
            'author_id': raw['author_id'], 'author_nickname': user.get('username'),
            'likes': raw['like_count'], 'comments': raw['comment_count'], 'collects': None,
            'shares': None, 'views': None, 'raw': raw}


class InstagramAdapter(BasePlatformAdapter):
    """Thin boundary layer around the v4 Instagram engine.

    Delegates all real collection to lumenis.adapters.instagram.InstagramAdapter.
    This layer only maps v4 AdapterResult -> CollectionResult and normalizes fields.
    No subject filtering, risk scoring, or business logic lives here.

    Default disabled: readiness is resolved from the registered read-only worker;
    actual session and source access remain separate runtime observations.
    """

    platform = "instagram"
    enabled = False
    monitor_priority = "secondary"

    # Compatibility override for tests/diagnostics.  The default is resolved
    # from the shared Cookie Vault at runtime, beside the canonical DB.
    COOKIE_PATH = Path(__file__).resolve().parents[1] / "data" / "cookies" / "instagram.json"
    _DEFAULT_COOKIE_PATH = COOKIE_PATH

    def __init__(self, *, engine: Any = None, public_fetcher: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._engine = engine
        self._engine_loaded = engine is not None
        self._public_fetcher = public_fetcher or fetch_public_url

    # ------------------------------------------------------------------
    # Engine lazy-load
    # ------------------------------------------------------------------
    def _get_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        from lumenis.adapters.instagram import InstagramAdapter as V4Engine
        self._engine = V4Engine()
        self._engine_loaded = True
        return self._engine

    @staticmethod
    def _verify_native_topic_reference(reference: Any) -> Optional[Dict[str, Any]]:
        """Resolve one exact Instagram topic reference from the unchanged seed."""
        if not isinstance(reference, dict):
            return None
        from ..acquisition_plan import (
            APPROVED_TOPIC_SEED_SHA256, AcquisitionPlanError, load_approved_topic_seed,
        )
        from .platform_naming import normalize_platform

        if reference.get("input_sha256") != APPROVED_TOPIC_SEED_SHA256:
            return None
        try:
            seed = load_approved_topic_seed()
        except (AcquisitionPlanError, OSError, TypeError, ValueError):
            return None
        topics = seed.get("topics") if isinstance(seed, dict) else None
        if not isinstance(topics, list):
            return None
        topic = next((row for row in topics
                      if isinstance(row, dict) and row.get("id") == reference.get("topic_id")), None)
        if (topic is None or normalize_platform(topic.get("platform")) != "instagram"
                or any(reference.get(key) != topic.get(field) for key, field in (
                    ("source_id", "source_id"), ("source_url", "source_url"),
                    ("term_preserved", "topic"), ("literal", "observed_literal")))):
            return None
        literal = topic.get("observed_literal")
        if not isinstance(literal, str) or not literal:
            return None
        native_hashtag = None
        reference_kind = "VALID_NON_HASHTAG"
        if topic.get("term_type") == "原生话题标签":
            if not literal.startswith("#") or literal.startswith("##"):
                return None
            native_hashtag = literal[1:]
            if (not native_hashtag or native_hashtag in {".", ".."}
                    or any(char.isspace() or char in r"\\/?#" for char in native_hashtag)):
                return None
            reference_kind = "VALID_NATIVE_HASHTAG"
        return {
            "topic_id": topic["id"],
            "input_sha256": APPROVED_TOPIC_SEED_SHA256,
            "source_id": topic["source_id"],
            "source_url": topic["source_url"],
            "term_preserved": topic["topic"],
            "literal": literal,
            "term_type": topic["term_type"],
            "recommended_use": topic.get("recommended_use"),
            "native_hashtag": native_hashtag,
            "reference_kind": reference_kind,
            "search_route": "NATIVE_HASHTAG" if native_hashtag is not None else "EXACT_QUERY",
            "verification": "APPROVED_SEED_ROW_MATCH",
        }

    # ------------------------------------------------------------------
    # Status mapping: v4 AdapterResult -> CollectionStatus
    # ------------------------------------------------------------------
    @staticmethod
    def _map_status(success: bool, notes: list, error: str) -> CollectionStatus:
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err = (error or "").lower()
        if err in {
            "readonly_worker_not_registered",
            "readonly_worker_not_configured",
            "browser_profile_owner_unavailable",
        } or "instagram_worker_not_registered" in err:
            return CollectionStatus.NOT_CONFIGURED
        if err in {
            "readonly_worker_boundary_invalid",
            "browser_worker_kernel_or_identity_unverified",
            "protected_profile_forbidden",
        }:
            return CollectionStatus.BLOCKED
        if err in {
            "readonly_worker_profile_unavailable",
            "readonly_worker_profile_mode_or_kernel_unavailable",
            "browser_worker_profile_or_mode_unavailable",
        }:
            return CollectionStatus.PROVIDER_UNAVAILABLE
        if err == "instagram_auth_required":
            return CollectionStatus.SESSION_EXPIRED
        if err == "instagram_challenge_required":
            return CollectionStatus.NEED_VERIFY
        if err == "instagram_rate_limited":
            return CollectionStatus.BLOCKED
        if err == "instagram_network_unavailable" or err == "instagram_worker_unavailable":
            return CollectionStatus.PROVIDER_UNAVAILABLE
        if re.fullmatch(r"instagram_collect_error:[a-z_][a-z0-9_]{0,63}", err):
            return CollectionStatus.COLLECT_ERROR
        if "登录态失效" in error or "session" in err and "expire" in err:
            return CollectionStatus.SESSION_EXPIRED
        if any(k in error for k in ("验证", "captcha", "人机")) or "captcha" in err:
            return CollectionStatus.NEED_VERIFY
        if any(k in error for k in ("频控", "风控", "try again later")):
            return CollectionStatus.BLOCKED
        if any(k in err for k in ("network", "provider unavailable", "worker unavailable", "不可达", "暂不可用")):
            return CollectionStatus.PROVIDER_UNAVAILABLE
        if "代理" in error or "proxy" in err:
            return CollectionStatus.COLLECT_ERROR
        return CollectionStatus.COLLECT_ERROR

    # ------------------------------------------------------------------
    # v4 CollectedNote -> normalized item dict
    # ------------------------------------------------------------------
    def _notes_to_items(self, notes: list) -> List[Dict[str, Any]]:
        items = []
        for note in notes:
            note_dict = note.__dict__ if hasattr(note, "__dict__") else dict(note)
            items.append(self.normalize_item(note_dict))
        return items

    @staticmethod
    def _shortcode_from_url(url: Any) -> Optional[str]:
        if not isinstance(url, str):
            return None
        try:
            parts = urlsplit(url)
            port = parts.port
        except (TypeError, ValueError):
            return None
        if (parts.scheme.lower() != "https"
                or parts.hostname not in {"instagram.com", "www.instagram.com"}
                or port not in (None, 443)
                or parts.username or parts.password):
            return None
        match = re.fullmatch(r"/(?:p|reel|reels)/([A-Za-z0-9_-]+)/?", parts.path)
        return match.group(1) if match else None

    @classmethod
    def _observed_shortcode(cls, item: Dict[str, Any]) -> tuple[Optional[str], Optional[str], bool]:
        raw = item.get("raw") if isinstance(item, dict) else None
        raw = raw if isinstance(raw, dict) else {}
        raw_code = raw.get("shortcode")
        if not isinstance(raw_code, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", raw_code):
            raw_code = None
        url_code = cls._shortcode_from_url(item.get("url"))
        if raw_code and url_code and raw_code != url_code:
            return None, None, True
        if raw_code:
            return raw_code, "raw_data.shortcode", False
        if url_code:
            return url_code, "source_url.pathname", False
        return None, None, False

    @classmethod
    def _detail_shortcode_matches(cls, item: Dict[str, Any], expected: str) -> bool:
        raw = item.get("raw") if isinstance(item, dict) else None
        raw = raw if isinstance(raw, dict) else {}
        identity = raw.get("native_identity")
        observed = identity.get("shortcode") if isinstance(identity, dict) else None
        return (isinstance(observed, str) and observed == expected
                and identity.get("requested_shortcode") == expected
                and identity.get("status") == "OBSERVED_MATCH"
                and raw.get("shortcode") == expected
                and cls._shortcode_from_url(item.get("url")) == expected)

    @staticmethod
    def _detail_failure_state(error: Any) -> str:
        text = str(error or "").casefold()
        if text in {"readonly_worker_not_registered", "readonly_worker_not_configured",
                    "browser_profile_owner_unavailable"}:
            return "NOT_CONFIGURED"
        if text in {"readonly_worker_boundary_invalid",
                    "browser_worker_kernel_or_identity_unverified",
                    "protected_profile_forbidden"}:
            return "BLOCKED"
        if text in {"readonly_worker_profile_unavailable",
                    "readonly_worker_profile_mode_or_kernel_unavailable",
                    "browser_worker_profile_or_mode_unavailable",
                    "instagram_network_unavailable", "instagram_worker_unavailable"}:
            return "PROVIDER_UNAVAILABLE"
        if text == "instagram_auth_required":
            return "SESSION_UNAVAILABLE"
        if text == "instagram_challenge_required":
            return "VERIFICATION_REQUIRED"
        if text == "instagram_rate_limited":
            return "RATE_LIMITED"
        if re.fullmatch(r"instagram_collect_error:[a-z_][a-z0-9_]{0,63}", text):
            return "COLLECT_ERROR"
        if any(marker in text for marker in ("identity_mismatch", "identity mismatch", "身份不匹配")):
            return "IDENTITY_MISMATCH"
        if any(marker in text for marker in ("captcha", "验证码", "安全验证", "人机", "confirm", "need_verify")):
            return "VERIFICATION_REQUIRED"
        if any(marker in text for marker in ("rate limit", "rate_limit", "频控", "访问频繁", "too many", "http 429", " 429")):
            return "RATE_LIMITED"
        has_session = any(marker in text for marker in ("login", "登录", "cookie", "session", "会话", "失效", "expired"))
        has_risk = any(marker in text for marker in ("风控", "risk", "blocked", "封禁", "http 403", " 403"))
        if has_session and has_risk:
            return "SESSION_OR_RISK_REQUIRED"
        if has_session:
            return "SESSION_UNAVAILABLE"
        if has_risk:
            return "PLATFORM_RISK"
        if any(marker in text for marker in ("not configured", "not_configured", "未配置")):
            return "NOT_CONFIGURED"
        if any(marker in text for marker in ("network", "timeout", "不可达", "worker", "provider", "unavailable", "连接异常")):
            return "PROVIDER_UNAVAILABLE"
        return "DETAIL_FAILED"

    @staticmethod
    def _begin_detail_observation(item: Dict[str, Any], shortcode: Optional[str],
                                  id_locator: Optional[str]) -> Dict[str, Any]:
        raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        raw = dict(raw)
        raw["search_summary_observation"] = {
            "status": "OBSERVED",
            "body_kind": "search_preview",
            "body_status": "SEARCH_PREVIEW_ONLY",
            "text": item.get("content") if isinstance(item.get("content"), str) else None,
            "title": item.get("title") if isinstance(item.get("title"), str) else None,
            "author_id": item.get("author_id"),
            "author_nickname": item.get("author_nickname"),
            "publish_datetime": item.get("publish_datetime"),
            "source_url": item.get("url") if isinstance(item.get("url"), str) else None,
            "native_shortcode": shortcode,
            "native_shortcode_locator": id_locator,
            "body_locator": "search_result.content",
            "discovery_body_text": raw.get("discovery_body_text"),
            "discovery_body_locator": "raw_data.discovery_body_text" if raw.get("discovery_body_text") is not None else None,
            "image_alt": raw.get("image_alt"),
            "metric_display": raw.get("metric_display"),
            "metrics": {name: item.get(name) for name in ("likes", "comments", "collects", "shares")},
        }
        item["raw"] = raw
        # A preview remains in its explicit observation above; it is never the
        # canonical full-body field when detail is missing or incomplete.
        item["content"] = ""
        item["title"] = ""
        item["author_id"] = ""
        item["author_nickname"] = ""
        item["publish_datetime"] = ""
        for field in ("likes", "comments", "collects", "shares"):
            item[field] = None
        return raw

    @staticmethod
    def _record_detail_outcome(item: Dict[str, Any], status: str,
                               detail_item: Optional[Dict[str, Any]] = None,
                               stop_reason: Optional[str] = None) -> None:
        raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        raw = dict(raw)
        detail_raw = detail_item.get("raw") if isinstance(detail_item, dict) else None
        detail_raw = detail_raw if isinstance(detail_raw, dict) else {}
        body = detail_item.get("content") if isinstance(detail_item, dict) else None
        body = body if isinstance(body, str) else None
        body_observed = isinstance(body, str) and bool(body.strip())
        succeeded = detail_item is not None
        native_time = detail_item.get("publish_datetime") if succeeded else None
        native_time_observed = isinstance(native_time, str) and bool(native_time.strip())
        metrics = ({name: detail_item.get(name) for name in ("likes", "comments")}
                   if succeeded else None)
        metric_observations = detail_raw.get("metric_observations") if succeeded else None
        if not isinstance(metric_observations, dict):
            metric_observations = {}
        media_hints = detail_raw.get("media_hints") if succeeded else None
        media_hints = media_hints if isinstance(media_hints, list) else None
        media_id = detail_raw.get("media_id") if succeeded else None
        media_id_observed = isinstance(media_id, str) and media_id.isdigit()
        body_state = detail_raw.get("caption_completeness") if succeeded else None
        body_status = ("CAPTION_OBSERVED_COMPLETENESS_UNKNOWN" if body_observed
                       else "NATIVE_BODY_UNAVAILABLE") if succeeded else (
                           "PENDING" if status == "PENDING" else "SEARCH_ONLY")
        raw["detail_observation"] = {
            "status": status,
            "stop_reason": stop_reason or (status if status in _TERMINAL_IG_DETAIL_STATES else None),
            "body_kind": "native_caption" if succeeded and body_observed else None,
            "body": body if succeeded else None,
            "body_status": body_status,
            "body_completeness": body_state if succeeded else None,
            "body_locator": detail_raw.get("caption_locator") if succeeded else None,
            "source_url": detail_item.get("url") if succeeded else None,
            "native_time": native_time,
            "native_time_locator": detail_raw.get("native_time_locator") if succeeded else None,
            "native_time_status": ("OBSERVED" if native_time_observed else "NOT_OBSERVED") if succeeded else (
                "PENDING" if status == "PENDING" else "SEARCH_ONLY"),
            "native_metrics": metrics,
            "metric_observations": metric_observations if succeeded else None,
            "metrics_status": ("OBSERVED" if any(
                isinstance(value, dict) and value.get("display") is not None
                for value in metric_observations.values()) else "NOT_OBSERVED") if succeeded else (
                    "PENDING" if status == "PENDING" else "SEARCH_ONLY"),
            "media_hints": media_hints,
            "media_state": ("URL_HINTS_OBSERVED" if media_hints else "NOT_OBSERVED") if succeeded else (
                "PENDING" if status == "PENDING" else "DETAIL_NOT_OBSERVED"),
            "media_bytes_saved": False,
            "artifact_created": False,
            "native_media_id": media_id if media_id_observed else None,
            "native_media_id_status": "OBSERVED" if media_id_observed else "NOT_OBSERVED",
            "native_media_id_locator": detail_raw.get("media_id_locator") if media_id_observed else None,
        }
        item["raw"] = raw
        if not succeeded:
            item["content"] = ""
            item["title"] = ""
            return
        item["content"] = body if body_observed else ""
        item["title"] = body[:80] if body_observed else ""
        item["publish_datetime"] = native_time or ""
        item["url"] = detail_item.get("url") or item.get("url") or ""
        for field in ("likes", "comments", "collects", "shares"):
            item[field] = detail_item.get(field)
        for field in ("author_id", "author_nickname"):
            value = detail_item.get(field)
            if value not in (None, ""):
                item[field] = value

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        raw_topic_reference = kwargs.get("native_topic_reference")
        verified_topic_reference = None
        if raw_topic_reference is not None:
            verified_topic_reference = self._verify_native_topic_reference(raw_topic_reference)
            if verified_topic_reference is None:
                return CollectionResult(
                    CollectionStatus.NOT_SUPPORTED, self.platform,
                    message="Instagram topic reference is not an exact approved seed row",
                    metadata={"native_topic_reference_status": "INVALID"},
                )
        route = resolve_capability_route("instagram", "search", request_value=keyword)
        if route is None:
            return CollectionResult(
                CollectionStatus.NOT_SUPPORTED, self.platform,
                message="当前输入不匹配已实现的 Instagram 搜索/公开帖子路径",
                metadata={"route_state": "UNKNOWN"},
            )
        if (verified_topic_reference is not None
                and (route.backend != "v4_instagram" or route.selector != "query")):
            return CollectionResult(
                CollectionStatus.NOT_SUPPORTED, self.platform,
                message="Instagram seed topic reference requires the existing session query route",
                metadata={"native_topic_reference_status": "ROUTE_MISMATCH"},
            )
        if route.backend == "public_native_post_document":
            return self._public_detail(keyword)
        try:
            engine = self._get_engine()
            try:
                requested_limit = int(kwargs.get("max_results", 20))
            except (TypeError, ValueError, OverflowError):
                requested_limit = 20
            max_results = min(20, max(0, requested_limit))
            if (verified_topic_reference is None
                    or verified_topic_reference["native_hashtag"] is None):
                result = engine.search(keyword, max_results=max_results)
            else:
                result = engine.search(
                    keyword, max_results=max_results,
                    native_hashtag=verified_topic_reference["native_hashtag"],
                    native_topic_reference=verified_topic_reference,
                )
            items = self._notes_to_items((result.notes or [])[:max_results])
            if verified_topic_reference is not None:
                for item in items:
                    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
                    raw = dict(raw)
                    raw["verified_native_topic_reference"] = verified_topic_reference
                    item["raw"] = raw
            status = self._map_status(result.success, result.notes, result.error)
            detail_counts = {"attempted": 0, "succeeded": 0, "failed": 0, "pending": 0,
                             "not_attempted_no_native_id": 0, "reused_same_native_id": 0}
            detail_stop_reason = None if result.success else self._detail_failure_state(result.error or "search failed")
            detail_cache = {}
            detail_exception_reason = None
            for item in items:
                shortcode, id_locator, identity_conflict = self._observed_shortcode(item)
                self._begin_detail_observation(item, shortcode, id_locator)
                if identity_conflict:
                    self._record_detail_outcome(item, "IDENTITY_MISMATCH")
                    detail_counts["failed"] += 1
                    detail_stop_reason = "IDENTITY_MISMATCH"
                    continue
                if not shortcode:
                    self._record_detail_outcome(item, "NOT_ATTEMPTED_NO_NATIVE_ID")
                    detail_counts["not_attempted_no_native_id"] += 1
                    continue
                if detail_stop_reason:
                    self._record_detail_outcome(item, "PENDING", stop_reason=detail_stop_reason)
                    detail_counts["pending"] += 1
                    continue
                if shortcode in detail_cache:
                    self._record_detail_outcome(item, "REUSED_SAME_NATIVE_ID", detail_cache[shortcode])
                    detail_counts["succeeded"] += 1
                    detail_counts["reused_same_native_id"] += 1
                    continue

                search_raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
                media_type = "reel" if search_raw.get("media_type") == "reel" else "post"
                detail_counts["attempted"] += 1
                detail_error = None
                try:
                    detail_result = engine.detail(shortcode, media_type=media_type)
                except Exception as exc:
                    logger.error(
                        "Instagram per-post detail failed error_type=%s",
                        type(exc).__name__,
                    )
                    detail_error = _safe_collection_error(exc)
                    detail_exception_reason = detail_error
                    detail_result = None
                detail_candidates = self._notes_to_items(detail_result.notes) if detail_result else []
                matching_detail = next((candidate for candidate in detail_candidates
                                        if self._detail_shortcode_matches(candidate, shortcode)), None)
                if detail_result and detail_result.success and matching_detail is not None:
                    detail_cache[shortcode] = matching_detail
                    self._record_detail_outcome(item, "SUCCESS", matching_detail)
                    detail_counts["succeeded"] += 1
                    continue

                if detail_candidates and matching_detail is None:
                    failure_state = "IDENTITY_MISMATCH"
                elif detail_result is None:
                    failure_state = self._detail_failure_state(
                        detail_error or "PROVIDER_UNAVAILABLE"
                    )
                else:
                    failure_state = self._detail_failure_state(
                        detail_result.error or "detail returned no matching native post"
                    )
                    if failure_state == "DETAIL_FAILED" and detail_result.success:
                        failure_state = "DETAIL_NOT_RETURNED"
                self._record_detail_outcome(item, failure_state)
                detail_counts["failed"] += 1
                if (failure_state in _TERMINAL_IG_DETAIL_STATES
                        or (detail_result is not None and not detail_result.success)):
                    detail_stop_reason = failure_state

            detail_counts["pending"] = sum(
                1 for item in items
                if isinstance(item.get("raw"), dict)
                and item["raw"].get("detail_observation", {}).get("status") == "PENDING"
            )
            detail_incomplete = bool(detail_counts["failed"] or detail_counts["pending"]
                                     or detail_counts["not_attempted_no_native_id"])
            body_observation_incomplete = any(
                not isinstance(item.get("raw"), dict)
                or item["raw"].get("detail_observation", {}).get("body_status")
                != "CAPTION_OBSERVED_COMPLETENESS_UNKNOWN"
                or item["raw"].get("detail_observation", {}).get("native_time_status") != "OBSERVED"
                for item in items
            )
            detail_metadata = {
                **detail_counts,
                "stop_reason": detail_stop_reason,
                "exception_reason": detail_exception_reason,
                "body_completeness": (
                    ("NO_RESULTS" if result.success else "NOT_OBSERVED")
                    if not items else (
                        "PARTIAL" if detail_incomplete or body_observation_incomplete
                        else "DOM_COMPLETENESS_UNKNOWN"
                    )
                ),
                "media_semantics": "URL_HINTS_ONLY_NO_BYTES_OR_ARTIFACT",
            }
            if detail_stop_reason:
                status = {
                    "VERIFICATION_REQUIRED": CollectionStatus.NEED_VERIFY,
                    "RATE_LIMITED": CollectionStatus.COOLING_DOWN,
                    "SESSION_UNAVAILABLE": CollectionStatus.SESSION_EXPIRED,
                    "PLATFORM_RISK": CollectionStatus.RISK_WARNING,
                    "NOT_CONFIGURED": CollectionStatus.NOT_CONFIGURED,
                    "BLOCKED": CollectionStatus.BLOCKED,
                    "PROVIDER_UNAVAILABLE": CollectionStatus.PROVIDER_UNAVAILABLE,
                    "COLLECT_ERROR": CollectionStatus.COLLECT_ERROR,
                }.get(detail_stop_reason, CollectionStatus.COLLECT_ERROR)
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=items,
                raw_count=result.raw_count,
                new_count=len(items),
                message=(result.error or ("Instagram搜索成功；部分原生详情未完成" if detail_incomplete else "")),
                metadata={
                    "engine": "v4_instagram",
                    "provider": "authorized_browser_worker",
                    "detail": detail_metadata,
                    "original_query": keyword if verified_topic_reference is not None else None,
                    "native_topic_reference": verified_topic_reference,
                    "native_topic_reference_status": (
                        verified_topic_reference["reference_kind"]
                        if verified_topic_reference is not None else None
                    ),
                },
            )
        except Exception as exc:
            message = _safe_collection_error(exc)
            return CollectionResult(
                status=self._map_status(False, [], message),
                platform=self.platform,
                message=message,
            )

    def _public_detail(self, url):
        raw_url = str(url or "").strip()
        try:
            parts = urlsplit(raw_url)
            port = parts.port
        except (TypeError, ValueError) as exc:
            raise ValueError('exact public Instagram post URL required') from exc
        match = re.fullmatch(r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)/?', parts.path)
        if (parts.scheme.lower() != 'https'
                or parts.hostname not in {'instagram.com', 'www.instagram.com'}
                or port not in (None, 443)
                or parts.username or parts.password or not match):
            raise ValueError('exact public Instagram post URL required')
        try:
            response = self._public_fetcher(raw_url)
            if urlsplit(response.url).hostname not in {'instagram.com', 'www.instagram.com'}:
                return CollectionResult(CollectionStatus.BLOCKED, self.platform, metadata={'original_body_available': False})
            item = parse_public_instagram_document(response, match.group(1))
            return CollectionResult(CollectionStatus.SUCCESS if item else CollectionStatus.PROVIDER_UNAVAILABLE,
                self.platform, items=[item] if item else [], raw_count=1 if item else 0,
                metadata={**public_source_provenance(response, raw_url), 'provider': 'public_native_post_document',
                          'original_body_available': item is not None, 'requires_auth': False})
        except Exception as exc:
            return CollectionResult(CollectionStatus.PROVIDER_UNAVAILABLE, self.platform,
                                    metadata={'error_type': type(exc).__name__, 'original_body_available': False})

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        route = resolve_capability_route("instagram", "detail", request_value=content_id)
        if route is None:
            return CollectionResult(
                CollectionStatus.NOT_SUPPORTED, self.platform,
                message="当前输入不匹配已实现的 Instagram 详情路径",
                metadata={"route_state": "UNKNOWN"},
            )
        if route.backend == "public_native_post_document":
            return self._public_detail(content_id)
        try:
            engine = self._get_engine()
            media_type = "reel" if kwargs.get("media_type") == "reel" else "post"
            result = engine.detail(content_id, media_type=media_type)
            items = self._notes_to_items(result.notes)
            status = self._map_status(result.success, result.notes, result.error)
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=items,
                raw_count=result.raw_count,
                new_count=len(items),
                message=result.error or "",
                metadata={
                    "engine": "v4_instagram",
                    "shortcode": content_id,
                    "provider": "authorized_browser_worker",
                },
            )
        except Exception as exc:
            message = _safe_collection_error(exc)
            return CollectionResult(
                status=self._map_status(False, [], message),
                platform=self.platform,
                message=message,
            )

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        route = resolve_capability_route("instagram", "comments", request_value=content_id)
        if route is None:
            return CollectionResult(
                CollectionStatus.NOT_SUPPORTED, self.platform,
                message="当前输入不匹配已实现的 Instagram 评论路径",
                metadata={"route_state": "UNKNOWN"},
            )
        try:
            engine = self._get_engine()
            result = engine.comments(content_id, max_comments=kwargs.get("max_comments", 20))
            # v4 stores comments in notes[0].raw_data["comments"]
            comments_list: List[Dict[str, Any]] = []
            if result.notes:
                raw = result.notes[0].raw_data or {}
                comments_list = list(raw.get("comments", []))
            status = self._map_status(result.success, result.notes, result.error)
            # If v4 returned success but no comments, that's NO_NEW_DATA for comments
            if status == CollectionStatus.SUCCESS and not comments_list:
                status = CollectionStatus.NO_NEW_DATA
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=[],
                comments=comments_list,
                raw_count=result.raw_count,
                new_count=len(comments_list),
                message=result.error or "",
                metadata={
                    "engine": "v4_instagram",
                    "shortcode": content_id,
                    "include_replies": include_replies,
                },
            )
        except Exception as exc:
            message = _safe_collection_error(exc)
            return CollectionResult(
                status=self._map_status(False, [], message),
                platform=self.platform,
                message=message,
            )

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        route = resolve_capability_route("instagram", "creator", request_value=creator_id)
        if route is None:
            return CollectionResult(
                CollectionStatus.NOT_SUPPORTED, self.platform,
                message="当前输入不匹配已实现的 Instagram 作者路径",
                metadata={"route_state": "UNKNOWN"},
            )
        try:
            engine = self._get_engine()
            result = engine.creator(creator_id)
            items = self._notes_to_items(result.notes)
            status = self._map_status(result.success, result.notes, result.error)
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=items,
                raw_count=result.raw_count,
                new_count=len(items),
                message=result.error or "",
                metadata={
                    "engine": "v4_instagram",
                    "username": creator_id,
                },
            )
        except Exception as exc:
            message = _safe_collection_error(exc)
            return CollectionResult(
                status=self._map_status(False, [], message),
                platform=self.platform,
                message=message,
            )

    def health_check(self, **kwargs: Any) -> CollectionResult:
        """Report public-read or registered-worker readiness without reading credentials.

        Cookie/proxy file presence cannot prove a registered permitted worker,
        authentication, acquisition access or readiness. No browser is touched.
        """
        route = resolve_capability_route(
            "instagram", "detail", request_value=kwargs.get("url"),
        )
        if route is not None and route.backend == "public_native_post_document":
            return CollectionResult(CollectionStatus.NEED_VERIFY, self.platform,
                metadata={'provider': 'public_native_post_document', 'requires_auth': False,
                          'healthcheck_scope': 'public_document_requires_actual_read'})
        from lumenis.adapters.human_browser import readonly_worker_health
        health = readonly_worker_health(self.platform)
        return CollectionResult(
            status=CollectionStatus(health["status"]), platform=self.platform,
            message="Instagram 专用只读浏览器状态；登录和采集结果仍需实际验证",
            metadata=health["metadata"],
        )

    # ------------------------------------------------------------------
    # Field normalization
    # ------------------------------------------------------------------
    def normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Map v4 CollectedNote fields to main-chain normalized item fields."""
        raw_data = item.get("raw_data") or {}
        # platform_content_id: prefer raw_data.shortcode, fallback to extracting from URL
        shortcode = raw_data.get("shortcode", "")
        if not shortcode:
            url = item.get("url", "")
            m = re.search(r"/(?:p|reel|reels)/([A-Za-z0-9_\-]+)", url)
            shortcode = m.group(1) if m else ""

        return {
            "source_platform": self.platform,
            "platform_content_id": str(shortcode),
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "author_id": item.get("author_id", ""),
            "author_nickname": item.get("author", ""),
            "publish_datetime": item.get("publish_date", ""),
            "url": item.get("url", ""),
            "likes": optional_int(item.get("likes")),
            "comments": optional_int(item.get("comments")),
            "collects": optional_int(item.get("collects")),
            "shares": optional_int(item.get("shares")),
            "captured_at": item.get("captured_at"),
            "raw": raw_data,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _proxy_configured() -> str:
        return (os.environ.get("GOOGLE_PROXY") or os.environ.get("OPENAI_PROXY") or "").strip()


register_adapter("instagram", InstagramAdapter)
