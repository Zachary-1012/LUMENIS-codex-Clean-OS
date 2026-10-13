from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlsplit

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .registry import register_adapter

logger = logging.getLogger(__name__)


def _safe_x_exception_class(exc: Exception) -> str:
    name = type(exc).__name__
    return name if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", name) else "Exception"


_TERMINAL_X_DETAIL_STATES = frozenset({
    "SESSION_EXPIRED", "RISK_WARNING", "BLOCKED", "PROVIDER_UNAVAILABLE",
    "NOT_CONFIGURED", "NOT_SUPPORTED",
})


class XAdapter(BasePlatformAdapter):
    """X (Twitter) 主链路适配器（薄封装 v4 XAdapter 引擎）。

    v4 引擎使用浏览器 CDP + cookie_vault 采集 X 搜索结果，
    本适配器负责 v4 AdapterResult → 主链路 CollectionResult 映射。
    """

    platform = "x"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _load_backend(self):
        if self.backend is not None:
            return self.backend
        try:
            from lumenis.adapters.x_platform import XAdapter as V4XAdapter
            return V4XAdapter()
        except Exception as exc:
            raise RuntimeError(
                f"X backend unavailable: {_safe_x_exception_class(exc)}"
            ) from None

    @staticmethod
    def _v4_status_to_main(success: bool, notes: list, error: str) -> CollectionStatus:
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err_lower = (error or "").lower()
        if err_lower.startswith("x not_configured:"):
            return CollectionStatus.NOT_CONFIGURED
        if err_lower.startswith("x blocked:"):
            return CollectionStatus.BLOCKED
        if err_lower.startswith("x provider_unavailable:"):
            return CollectionStatus.PROVIDER_UNAVAILABLE
        if err_lower.startswith("x collection_error:"):
            return CollectionStatus.COLLECT_ERROR
        if any(k in err_lower for k in ("not supported", "unsupported", "review required")):
            return CollectionStatus.NOT_SUPPORTED
        if any(k in err_lower for k in ("not configured", "not_configured", "未配置")):
            return CollectionStatus.NOT_CONFIGURED
        if any(k in err_lower for k in ("登录", "login", "cookie", "session", "失效", "未登录")):
            return CollectionStatus.SESSION_EXPIRED
        if any(k in err_lower for k in ("风控", "验证", "captcha", "verify", "verification", "challenge", "risk", "频控")):
            return CollectionStatus.RISK_WARNING
        if any(k in err_lower for k in ("rate limit", "rate limited", "too many", "http 429", " 429")):
            return CollectionStatus.BLOCKED
        if any(k in err_lower for k in ("block", "封禁", "不可用")):
            return CollectionStatus.BLOCKED
        if any(k in err_lower for k in ("network", "timeout", "connection", "dns", "provider unavailable", "worker unavailable")):
            return CollectionStatus.PROVIDER_UNAVAILABLE
        return CollectionStatus.COLLECT_ERROR

    def _v4_notes_to_items(self, notes: list) -> list[dict]:
        items = []
        for n in notes or []:
            raw = getattr(n, "raw_data", {}) or {}
            items.append(self.normalize_item({
                "platform_content_id": raw.get("tweet_id") if isinstance(raw, dict) else None,
                "title": getattr(n, "title", ""),
                "content": getattr(n, "content", ""),
                "author_id": getattr(n, "author_id", ""),
                "author_nickname": getattr(n, "author", ""),
                "publish_datetime": getattr(n, "publish_date", ""),
                "url": getattr(n, "url", ""),
                "likes": getattr(n, "likes", None),
                "comments": getattr(n, "comments", None),
                "collects": getattr(n, "collects", None),
                "shares": getattr(n, "shares", None),
                "raw": raw,
            }))
        return items

    @staticmethod
    def _status_id_from_url(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        try:
            parts = urlsplit(value)
            port = parts.port
        except (TypeError, ValueError):
            return None
        if (parts.scheme.lower() != "https"
                or parts.hostname not in {"x.com", "www.x.com"}
                or port not in (None, 443)
                or parts.username or parts.password):
            return None
        match = re.search(r"(?:^|/)status/([0-9]+)(?:/|$)", parts.path)
        return match.group(1) if match else None

    @classmethod
    def _observed_tweet_id(cls, item: dict) -> tuple[str | None, bool]:
        raw = item.get("raw") if isinstance(item, dict) else None
        raw = raw if isinstance(raw, dict) else {}
        value = raw.get("tweet_id")
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value):
            return None, False
        url_id = cls._status_id_from_url(item.get("url"))
        raw_url_id = cls._status_id_from_url(raw.get("url"))
        if (item.get("platform_content_id") != value
                or url_id != value or raw_url_id != value
                or not isinstance(raw.get("tweet_id_locator"), str)):
            return None, True
        identity = raw.get("native_identity")
        if (not isinstance(identity, dict) or identity.get("tweet_id") != value
                or identity.get("status") != "OBSERVED"):
            return None, True
        return value, False

    @classmethod
    def _detail_tweet_id_matches(cls, item: dict, expected: str) -> bool:
        raw = item.get("raw") if isinstance(item, dict) else None
        raw = raw if isinstance(raw, dict) else {}
        identity = raw.get("native_identity")
        return (isinstance(identity, dict)
                and identity.get("status") == "OBSERVED_MATCH"
                and identity.get("tweet_id") == expected
                and identity.get("requested_tweet_id") == expected
                and identity.get("final_tweet_id") == expected
                and raw.get("tweet_id") == expected
                and cls._status_id_from_url(item.get("url")) == expected)

    @staticmethod
    def _detail_failure_state(error: Any) -> str:
        text = str(error or "").casefold()
        if text.startswith("x not_configured:"):
            return "NOT_CONFIGURED"
        if text.startswith("x blocked:"):
            return "BLOCKED"
        if text.startswith("x provider_unavailable:"):
            return "PROVIDER_UNAVAILABLE"
        if text.startswith("x collection_error:"):
            return "DETAIL_FAILED"
        if "identity mismatch" in text or "identity_mismatch" in text:
            return "IDENTITY_MISMATCH"
        if any(marker in text for marker in ("login", "session", "cookie", "登录", "未登录", "失效")):
            return "SESSION_EXPIRED"
        if any(marker in text for marker in ("challenge", "captcha", "verification", "verify", "验证")):
            return "RISK_WARNING"
        if any(marker in text for marker in ("rate limit", "rate limited", "too many", "429", "blocked", "封禁", "频控")):
            return "BLOCKED"
        if any(marker in text for marker in ("network", "timeout", "connection", "dns", "provider", "worker", "unavailable")):
            return "PROVIDER_UNAVAILABLE"
        if any(marker in text for marker in ("not supported", "unsupported")):
            return "NOT_SUPPORTED"
        if any(marker in text for marker in ("not configured", "not_configured", "未配置")):
            return "NOT_CONFIGURED"
        if "no verifiable post" in text or "no unique matching target article" in text:
            return "DETAIL_NOT_RETURNED"
        return "DETAIL_FAILED"

    @staticmethod
    def _detail_failure_status(state: str) -> CollectionStatus:
        return {
            "SESSION_EXPIRED": CollectionStatus.SESSION_EXPIRED,
            "RISK_WARNING": CollectionStatus.RISK_WARNING,
            "BLOCKED": CollectionStatus.BLOCKED,
            "PROVIDER_UNAVAILABLE": CollectionStatus.PROVIDER_UNAVAILABLE,
            "NOT_CONFIGURED": CollectionStatus.NOT_CONFIGURED,
            "NOT_SUPPORTED": CollectionStatus.NOT_SUPPORTED,
        }.get(state, CollectionStatus.COLLECT_ERROR)

    @staticmethod
    def _begin_detail_observation(item: dict, tweet_id: str | None) -> dict:
        raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        raw = dict(raw)
        raw["search_summary_observation"] = {
            "status": "OBSERVED",
            "body_kind": "search_preview",
            "body_status": "SEARCH_PREVIEW_ONLY",
            "text": item.get("content") if isinstance(item.get("content"), str) else None,
            "title": item.get("title"),
            "author_id": item.get("author_id"),
            "author_nickname": item.get("author_nickname"),
            "publish_datetime": item.get("publish_datetime"),
            "source_url": item.get("url"),
            "native_tweet_id": tweet_id,
            "native_tweet_id_locator": raw.get("tweet_id_locator"),
            "native_time_locator": raw.get("native_time_locator"),
            "metrics": raw.get("metrics"),
            "metric_display": raw.get("metric_display"),
            "metric_locators": raw.get("metric_locators"),
            "unclassified_counter_display": raw.get("unclassified_counter_display"),
            "unclassified_counter_locator": raw.get("unclassified_counter_locator"),
            "media_hints": raw.get("media_hints"),
            "media_state": raw.get("media_state"),
        }
        for field in ("native_time_locator", "caption_locator", "metrics", "metric_display",
                      "metric_locators", "unclassified_counter_display", "media_hints",
                      "unclassified_counter_locator", "media_state", "media_bytes_saved", "artifact_created"):
            raw.pop(field, None)
        item["raw"] = raw
        item["content"] = ""
        item["title"] = ""
        item["author_id"] = ""
        item["author_nickname"] = ""
        item["publish_datetime"] = ""
        for field in ("likes", "comments", "collects", "shares"):
            item[field] = None
        return raw

    @staticmethod
    def _record_detail_outcome(item: dict, status: str,
                               detail_item: dict | None = None,
                               stop_reason: str | None = None) -> None:
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
        metrics = ({name: detail_item.get(name) for name in ("likes", "comments", "collects", "shares")}
                   if succeeded else None)
        metric_display = detail_raw.get("metric_display") if succeeded else None
        media_hints = detail_raw.get("media_hints") if succeeded else None
        media_hints = media_hints if isinstance(media_hints, list) else None
        raw["detail_observation"] = {
            "status": status,
            "stop_reason": stop_reason or (status if status in _TERMINAL_X_DETAIL_STATES else None),
            "body_kind": "native_post_text" if succeeded and body_observed else None,
            "body": body if succeeded else None,
            "body_status": "NATIVE_TEXT_DOM_COMPLETENESS_UNKNOWN" if body_observed else (
                "NATIVE_BODY_UNAVAILABLE" if succeeded else "PENDING" if status == "PENDING" else "SEARCH_ONLY"),
            "body_locator": detail_raw.get("caption_locator") if succeeded else None,
            "native_identity": detail_raw.get("native_identity") if succeeded else None,
            "source_url": detail_item.get("url") if succeeded else None,
            "native_time": native_time,
            "native_time_locator": detail_raw.get("native_time_locator") if succeeded else None,
            "native_time_status": "OBSERVED" if native_time_observed else (
                "NOT_OBSERVED" if succeeded else "PENDING" if status == "PENDING" else "SEARCH_ONLY"),
            "native_metrics": metrics,
            "metric_display": metric_display,
            "metric_locators": detail_raw.get("metric_locators") if succeeded else None,
            "unclassified_counter_display": detail_raw.get("unclassified_counter_display") if succeeded else None,
            "unclassified_counter_locator": detail_raw.get("unclassified_counter_locator") if succeeded else None,
            "metrics_status": ("OBSERVED" if isinstance(metric_display, dict)
                               and any(value is not None for value in metric_display.values())
                               else "NOT_OBSERVED") if succeeded else (
                                   "PENDING" if status == "PENDING" else "SEARCH_ONLY"),
            "media_hints": media_hints,
            "media_state": ("URL_HINTS_OBSERVED" if media_hints else "NOT_OBSERVED") if succeeded else (
                "PENDING" if status == "PENDING" else "DETAIL_NOT_OBSERVED"),
            "media_bytes_saved": False,
            "artifact_created": False,
        }
        item["raw"] = raw
        if not succeeded:
            item["content"] = ""
            item["title"] = ""
            item["author_id"] = ""
            item["author_nickname"] = ""
            item["publish_datetime"] = ""
            for field in ("likes", "comments", "collects", "shares"):
                item[field] = None
            return
        item["content"] = body if body_observed else ""
        item["title"] = body[:80].replace("\n", " ") if body_observed else ""
        item["publish_datetime"] = native_time or ""
        item["url"] = detail_item.get("url") or item.get("url") or ""
        for field in ("likes", "comments", "collects", "shares"):
            item[field] = detail_item.get(field)
        for field in ("author_id", "author_nickname"):
            value = detail_item.get(field)
            if value not in (None, ""):
                item[field] = value

    @staticmethod
    def _continuation_metadata(checkpoint_used: bool, checkpoint_key: str | None,
                               checkpoint_id_count: int) -> dict:
        return {
            "seen_checkpoint_used": checkpoint_used,
            "seen_checkpoint_key": checkpoint_key,
            "seen_checkpoint_id_count": checkpoint_id_count,
            "committed_id_count": 0,
            "bounded_observed_id_count": None,
            "committed_skip_id_count": None,
            "new_id_count": None,
            "native_cursor": None,
            "pagination_exhausted": None,
            "coverage_complete": False,
        }

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        checkpoint_used = False
        checkpoint_key = None
        checkpoint_id_count = 0
        try:
            acquisition_fingerprint = kwargs.get("acquisition_fingerprint")
            if (acquisition_fingerprint is not None
                    and (not isinstance(acquisition_fingerprint, str)
                         or re.fullmatch(r"[0-9a-f]{64}", acquisition_fingerprint) is None)):
                return CollectionResult(
                    status=CollectionStatus.COLLECT_ERROR,
                    platform=self.platform,
                    message="X acquisition fingerprint is invalid",
                    metadata={"continuation": self._continuation_metadata(False, None, 0)},
                )
            skip_tweet_ids = None
            if acquisition_fingerprint is not None:
                checkpoint_used = True
                checkpoint_key = f"scope:{acquisition_fingerprint}"
                from ..guard.checkpoint import Checkpoint
                skip_tweet_ids = Checkpoint("x").seen_ids(checkpoint_key)
                checkpoint_id_count = len(skip_tweet_ids)

            backend = self._load_backend()
            try:
                requested_limit = int(kwargs.get("max_results", 20))
            except (TypeError, ValueError, OverflowError):
                requested_limit = 20
            max_results = min(20, max(0, requested_limit))
            if checkpoint_used:
                result = backend.search(
                    keyword, max_results=max_results, skip_tweet_ids=skip_tweet_ids,
                )
            else:
                result = backend.search(keyword, max_results=max_results)
            status = self._v4_status_to_main(result.success, result.notes, result.error)
            items = self._v4_notes_to_items((result.notes or [])[:max_results])
            detail_counts = {"attempted": 0, "succeeded": 0, "failed": 0, "pending": 0,
                             "not_attempted_no_native_id": 0, "reused_same_native_id": 0}
            detail_stop_reason = None if result.success else self._detail_failure_state(result.error or "search failed")
            detail_cache = {}
            overall_status = status
            overall_message = result.error or ""

            for item in items:
                tweet_id, identity_conflict = self._observed_tweet_id(item)
                self._begin_detail_observation(item, tweet_id)
                if identity_conflict:
                    self._record_detail_outcome(item, "IDENTITY_MISMATCH")
                    detail_counts["failed"] += 1
                    continue
                if not tweet_id:
                    self._record_detail_outcome(item, "NOT_ATTEMPTED_NO_NATIVE_ID")
                    detail_counts["not_attempted_no_native_id"] += 1
                    continue
                if detail_stop_reason:
                    self._record_detail_outcome(item, "PENDING", stop_reason=detail_stop_reason)
                    detail_counts["pending"] += 1
                    continue
                if tweet_id in detail_cache:
                    cached_state, cached_item = detail_cache[tweet_id]
                    if cached_item is not None:
                        self._record_detail_outcome(item, "REUSED_SAME_NATIVE_ID", cached_item)
                        detail_counts["succeeded"] += 1
                        detail_counts["reused_same_native_id"] += 1
                    else:
                        self._record_detail_outcome(item, "REUSED_DETAIL_FAILURE", stop_reason=cached_state)
                        detail_counts["failed"] += 1
                    continue

                detail_counts["attempted"] += 1
                try:
                    detail_result = backend.detail(tweet_id)
                except Exception as exc:
                    logger.error("X 逐帖详情异常 error_type=%s", type(exc).__name__)
                    detail_result = None
                detail_candidates = self._v4_notes_to_items(detail_result.notes) if detail_result else []
                matching_detail = next((candidate for candidate in detail_candidates
                                        if self._detail_tweet_id_matches(candidate, tweet_id)), None)
                if detail_result and detail_result.success and matching_detail is not None:
                    detail_cache[tweet_id] = ("SUCCESS", matching_detail)
                    self._record_detail_outcome(item, "SUCCESS", matching_detail)
                    detail_counts["succeeded"] += 1
                    continue

                if detail_candidates and matching_detail is None:
                    failure_state = "IDENTITY_MISMATCH"
                elif detail_result is None:
                    failure_state = "PROVIDER_UNAVAILABLE"
                else:
                    failure_state = self._detail_failure_state(detail_result.error or "X detail failed")
                    if failure_state == "DETAIL_FAILED" and detail_result.success:
                        failure_state = "DETAIL_NOT_RETURNED"
                detail_cache[tweet_id] = (failure_state, None)
                self._record_detail_outcome(item, failure_state)
                detail_counts["failed"] += 1
                if failure_state in _TERMINAL_X_DETAIL_STATES:
                    detail_stop_reason = failure_state
                    overall_status = self._detail_failure_status(failure_state)
                    overall_message = (detail_result.error if detail_result and detail_result.error
                                       else "X native post detail was not verified")

            detail_counts["pending"] = sum(
                1 for item in items
                if isinstance(item.get("raw"), dict)
                and item["raw"].get("detail_observation", {}).get("status") == "PENDING"
            )
            detail_incomplete = bool(detail_counts["failed"] or detail_counts["pending"]
                                     or detail_counts["not_attempted_no_native_id"])
            body_incomplete = any(
                not isinstance(item.get("raw"), dict)
                or item["raw"].get("detail_observation", {}).get("body_status")
                != "NATIVE_TEXT_DOM_COMPLETENESS_UNKNOWN"
                or item["raw"].get("detail_observation", {}).get("native_time_status") != "OBSERVED"
                for item in items
            )
            adapter_metadata = getattr(result, "metadata", None)
            metadata = dict(adapter_metadata) if isinstance(adapter_metadata, dict) else {}
            adapter_continuation = metadata.get("continuation")
            continuation = self._continuation_metadata(
                checkpoint_used, checkpoint_key, checkpoint_id_count,
            )
            if isinstance(adapter_continuation, dict):
                continuation.update(adapter_continuation)
            continuation.update({
                "seen_checkpoint_used": checkpoint_used,
                "seen_checkpoint_key": checkpoint_key,
                "seen_checkpoint_id_count": checkpoint_id_count,
                "committed_id_count": 0,
                "native_cursor": None,
                "pagination_exhausted": None,
                "coverage_complete": False,
            })
            observed_count = result.raw_count
            if continuation.get("bounded_observed_id_count") is None:
                continuation["bounded_observed_id_count"] = (
                    observed_count if type(observed_count) is int and observed_count >= 0 else None
                )
            if continuation.get("committed_skip_id_count") is None:
                continuation["committed_skip_id_count"] = 0 if not checkpoint_used else None
            if continuation.get("new_id_count") is None:
                continuation["new_id_count"] = len(items)
            metadata["continuation"] = continuation
            adapter_detail = metadata.get("detail")
            detail_metadata = dict(adapter_detail) if isinstance(adapter_detail, dict) else {}
            verified_detail_bodies = sum(
                1 for item in items
                if isinstance(item.get("raw"), dict)
                and item["raw"].get("detail_observation", {}).get("body_kind") == "native_post_text"
                and isinstance(item["raw"].get("detail_observation", {}).get("body"), str)
                and bool(item["raw"].get("detail_observation", {}).get("body", "").strip())
            )
            if result.success and items and detail_stop_reason is None and verified_detail_bodies == 0:
                overall_status = CollectionStatus.COLLECT_ERROR
                overall_message = "X search results contained no identity-verified native post text"
            if not result.success:
                body_completeness = "NOT_OBSERVED"
            elif not items:
                body_completeness = "NO_RESULTS"
            elif detail_incomplete or body_incomplete:
                body_completeness = "PARTIAL"
            else:
                body_completeness = "DOM_COMPLETENESS_UNKNOWN"
            return CollectionResult(
                status=overall_status,
                platform=self.platform,
                items=items,
                raw_count=result.raw_count,
                new_count=len(items),
                message=overall_message,
                metadata={
                    **metadata,
                    "provider": metadata.get("provider") or "authorized_browser_worker",
                    "detail": {
                        **detail_metadata,
                        **detail_counts,
                        "stop_reason": detail_stop_reason,
                        "body_completeness": body_completeness,
                        "media_semantics": "URL_HINTS_ONLY_NO_BYTES_OR_ARTIFACT",
                    },
                },
            )
        except Exception as exc:
            exception_class = _safe_x_exception_class(exc)
            safe_display_exception = RuntimeError(
                f"REDACTED_ORIGINAL_EXCEPTION:{exception_class}"
            )
            logger.error(
                "X 主链路采集失败 error_type=%s",
                exception_class,
                exc_info=(RuntimeError, safe_display_exception, exc.__traceback__),
            )
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=f"X collection_error: {exception_class}",
                metadata={"continuation": self._continuation_metadata(
                    checkpoint_used, checkpoint_key, checkpoint_id_count,
                )},
            )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("detail", content_id)

    def comments(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("comments", content_id, max_comments=kwargs.get("max_comments", 20))

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("creator", creator_id)

    def _delegate_v4(self, method: str, *args, **kwargs) -> CollectionResult:
        try:
            backend = self._load_backend()
            result = getattr(backend, method)(*args, **kwargs)
            status = self._v4_status_to_main(result.success, result.notes, result.error)
            items = self._v4_notes_to_items(result.notes)
            return CollectionResult(status=status, platform=self.platform, items=items, raw_count=result.raw_count, message=result.error or "")
        except Exception as exc:
            exception_class = _safe_x_exception_class(exc)
            safe_display_exception = RuntimeError(
                f"REDACTED_ORIGINAL_EXCEPTION:{exception_class}"
            )
            logger.error(
                "X delegated operation failed error_type=%s",
                exception_class,
                exc_info=(RuntimeError, safe_display_exception, exc.__traceback__),
            )
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=f"X collection_error: {exception_class}",
            )

    def health_check(self) -> CollectionResult:
        """Check the existing vault's non-secret X authentication metadata."""
        from lumenis.adapters.cookie_vault import check_cookie_status

        status = check_cookie_status("x")
        if status.get("has_auth_cookie"):
            return CollectionResult(
                status=CollectionStatus.NEED_VERIFY,
                platform=self.platform,
                message="X auth-cookie metadata present; login and collection access need verification",
            )
        return CollectionResult(
            status=CollectionStatus.NOT_CONFIGURED,
            platform=self.platform,
            message="X auth-cookie metadata missing",
        )


register_adapter("x", XAdapter)
