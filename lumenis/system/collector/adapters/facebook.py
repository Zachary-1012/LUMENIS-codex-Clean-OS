from __future__ import annotations

import logging
from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus, map_v4_comments
from .registry import register_adapter

logger = logging.getLogger(__name__)


class FacebookAdapter(BasePlatformAdapter):
    """Facebook 主链路适配器（薄封装 v4 FacebookAdapter 引擎）。

    v4 引擎使用浏览器 CDP + cookie_vault 采集 Facebook 搜索结果，
    本适配器负责 v4 AdapterResult → 主链路 CollectionResult 映射。
    """

    platform = "facebook"
    enabled = False
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _load_backend(self):
        if self.backend is not None:
            return self.backend
        try:
            from lumenis.adapters.facebook import FacebookAdapter as V4FacebookAdapter
            return V4FacebookAdapter()
        except Exception as exc:
            raise RuntimeError("Facebook provider unavailable") from exc

    @staticmethod
    def _v4_status_to_main(success: bool, notes: list, error: str) -> CollectionStatus:
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err_lower = (error or "").lower()
        if any(k in err_lower for k in ("登录", "login", "cookie", "session", "失效", "未登录")):
            return CollectionStatus.SESSION_EXPIRED
        if any(k in err_lower for k in ("风控", "验证", "captcha", "verify", "risk", "频控")):
            return CollectionStatus.RISK_WARNING
        if any(k in err_lower for k in ("block", "封禁", "不可用")):
            return CollectionStatus.BLOCKED
        if any(k in err_lower for k in ("provider_unavailable", "network", "timeout", "worker_disconnected")):
            return CollectionStatus.PROVIDER_UNAVAILABLE
        return CollectionStatus.COLLECT_ERROR

    def _v4_notes_to_items(self, notes: list) -> list[dict]:
        items = []
        for n in notes or []:
            raw = getattr(n, "raw_data", {}) or {}
            raw = raw if isinstance(raw, dict) else {}
            items.append(self.normalize_item({
                "platform_content_id": raw.get("post_id", ""),
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

    @classmethod
    def _observed_status(cls, result):
        return {'AUTH_REQUIRED': CollectionStatus.SESSION_EXPIRED, 'VERIFICATION_REQUIRED': CollectionStatus.NEED_VERIFY,
                'ACCESS_BLOCKED': CollectionStatus.BLOCKED, 'RATE_LIMITED': CollectionStatus.COOLING_DOWN,
                'CONTENT_UNAVAILABLE': CollectionStatus.PROVIDER_UNAVAILABLE, 'PROVIDER_UNAVAILABLE': CollectionStatus.PROVIDER_UNAVAILABLE}.get(
                    (getattr(result, 'metadata', None) or {}).get('failure_class')) or cls._v4_status_to_main(result.success, result.notes, result.error)

    @staticmethod
    def _post_identity_from_url(url: Any) -> dict | None:
        if not isinstance(url, str):
            return None
        try:
            from lumenis.adapters.facebook import FacebookAdapter as V4FacebookAdapter
            return V4FacebookAdapter.observed_post_permalink(url)
        except Exception:
            return None

    @classmethod
    def _observed_native_post_id(cls, item: dict) -> tuple[str | None, str | None]:
        raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        raw_id = raw.get("post_id")
        url_identity = cls._post_identity_from_url(item.get("url"))
        url_id = url_identity.get("post_id") if url_identity else None
        if raw_id in (None, "") and not url_id:
            return None, None
        if (not isinstance(raw_id, str) or not raw_id or not url_id
                or raw_id != url_id):
            return None, "IDENTITY_MISMATCH"
        return raw_id, None

    @staticmethod
    def _detail_failure_state(error: Any) -> str:
        text = error if isinstance(error, str) else ""
        lower = text.casefold()
        if any(marker in lower for marker in ("identity_mismatch", "invalid_post_permalink")):
            return "IDENTITY_MISMATCH"
        if any(marker in lower for marker in ("session_expired", "login_required", "cookie", "登录", "未登录")):
            return "SESSION_EXPIRED"
        if any(marker in lower for marker in ("risk_warning", "verification_required", "captcha", "challenge", "checkpoint", "verify", "验证", "风控")):
            return "RISK_WARNING"
        if any(marker in lower for marker in ("blocked", "blocked_access", "封禁")):
            return "BLOCKED"
        if any(marker in lower for marker in ("provider_unavailable", "network", "timeout", "worker_disconnected", "connection")):
            return "PROVIDER_UNAVAILABLE"
        if any(marker in lower for marker in ("detail_not_returned", "target_article_not_observed")):
            return "DETAIL_NOT_RETURNED"
        return "DETAIL_FAILED"

    @staticmethod
    def _has_verified_native_detail_body(item: dict | None) -> bool:
        if not isinstance(item, dict):
            return False
        raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        body = item.get("content")
        return bool(
            raw.get("detail_post_id_status") == "OBSERVED_AND_MATCHED"
            and raw.get("body_kind") == "NATIVE_POST_BODY"
            and raw.get("body_status") == "NATIVE_DETAIL_BODY_OBSERVED_COMPLETENESS_UNKNOWN"
            and isinstance(body, str) and body.strip()
        )

    @staticmethod
    def _begin_detail_observation(item: dict, native_id: str | None) -> dict:
        raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        raw = dict(raw)
        raw["search_summary_observation"] = {
            "status": "OBSERVED",
            "body_kind": "SEARCH_PREVIEW",
            "body_status": raw.get("body_status", "SEARCH_PREVIEW_ONLY"),
            "text": item.get("content") if isinstance(item.get("content"), str) else None,
            "title": item.get("title") if isinstance(item.get("title"), str) else None,
            "source_url": item.get("url") if isinstance(item.get("url"), str) else None,
            "native_post_id": native_id,
            "native_post_id_locator": raw.get("post_id_locator"),
            "native_time": item.get("publish_datetime") or None,
            "native_time_locator": raw.get("native_time_locator"),
            "metrics": {name: item.get(name) for name in ("likes", "comments", "collects", "shares")},
            "metric_display": raw.get("metric_display"),
            "metric_locators": raw.get("metric_locators"),
            "audience_observation": raw.get("audience_observation"),
            "media_hints": raw.get("media_hints"),
            "body_locator": raw.get("body_locator"),
        }
        item["raw"] = raw
        item["title"] = ""
        item["content"] = ""
        return raw

    @staticmethod
    def _record_detail_outcome(item: dict, status: str, detail_item: dict | None = None,
                               stop_reason: str | None = None) -> None:
        raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        raw = dict(raw)
        detail_raw = detail_item.get("raw") if isinstance(detail_item, dict) else None
        detail_raw = detail_raw if isinstance(detail_raw, dict) else {}
        succeeded = detail_item is not None
        body = detail_item.get("content") if succeeded else None
        body = body if isinstance(body, str) else None
        source_body_kind = detail_raw.get("body_kind") if succeeded else None
        native_body_observed = bool(
            succeeded and source_body_kind == "NATIVE_POST_BODY"
            and isinstance(body, str) and body.strip()
            and detail_raw.get("body_status") == "NATIVE_DETAIL_BODY_OBSERVED_COMPLETENESS_UNKNOWN"
            and detail_raw.get("detail_post_id_status") == "OBSERVED_AND_MATCHED"
        )
        observed_body = body if native_body_observed else None
        native_time = detail_item.get("publish_datetime") if succeeded else None
        native_time = native_time if isinstance(native_time, str) and native_time else None
        metrics = ({name: detail_item.get(name) for name in ("likes", "comments", "collects", "shares")}
                   if succeeded else None)
        media_hints = detail_raw.get("media_hints") if succeeded else None
        if not isinstance(media_hints, list):
            media_hints = [] if succeeded else None
        raw["detail_observation"] = {
            "status": status,
            "stop_reason": stop_reason or (status if status in {
                "SESSION_EXPIRED", "RISK_WARNING", "BLOCKED", "PROVIDER_UNAVAILABLE", "IDENTITY_MISMATCH"
            } else None),
            "body_kind": "NATIVE_POST_BODY" if native_body_observed else None,
            "observed_body_kind": source_body_kind,
            "body": observed_body,
            "preview_text": body if succeeded and source_body_kind == "SEARCH_PREVIEW" and body else None,
            "body_status": detail_raw.get("body_status") if succeeded else (
                "PENDING" if status == "PENDING" else "DETAIL_NOT_OBSERVED"),
            "body_locator": detail_raw.get("body_locator") if succeeded else None,
            "body_completeness": detail_raw.get("body_completeness", "UNKNOWN") if native_body_observed else (
                "NOT_OBSERVED" if succeeded else None),
            "source_url": detail_item.get("url") if succeeded else None,
            "native_post_id": detail_raw.get("post_id") if succeeded else None,
            "native_post_id_locator": detail_raw.get("post_id_locator") if succeeded else None,
            "native_time": native_time,
            "native_time_locator": detail_raw.get("native_time_locator") if succeeded else None,
            "native_time_status": ("OBSERVED" if native_time else "NOT_OBSERVED") if succeeded else (
                "PENDING" if status == "PENDING" else "DETAIL_NOT_OBSERVED"),
            "native_metrics": metrics,
            "metric_display": detail_raw.get("metric_display") if succeeded else None,
            "metric_locators": detail_raw.get("metric_locators") if succeeded else None,
            "metrics_status": ("OBSERVED" if any(value is not None for value in (metrics or {}).values())
                               else "NOT_OBSERVED") if succeeded else (
                "PENDING" if status == "PENDING" else "DETAIL_NOT_OBSERVED"),
            "audience_observation": detail_raw.get("audience_observation") if succeeded else None,
            "media_hints": media_hints,
            "media_state": detail_raw.get("media_state", "NOT_OBSERVED") if succeeded else (
                "PENDING" if status == "PENDING" else "DETAIL_NOT_OBSERVED"),
            "media_bytes_saved": False,
            "artifact_created": False,
        }
        item["raw"] = raw
        if not succeeded:
            item["title"] = ""
            item["content"] = ""
            return
        item["title"] = detail_item.get("title") if native_body_observed and isinstance(detail_item.get("title"), str) else ""
        item["content"] = observed_body or ""
        item["publish_datetime"] = native_time or ""
        item["url"] = detail_item.get("url") or item.get("url") or ""
        for field in ("likes", "comments", "collects", "shares"):
            item[field] = detail_item.get(field)
        for field in ("author_id", "author_nickname"):
            value = detail_item.get(field)
            if value not in (None, ""):
                item[field] = value

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        try:
            backend = self._load_backend()
            try:
                requested_limit = int(kwargs.get("max_results", 20))
            except (TypeError, ValueError, OverflowError):
                requested_limit = 20
            max_results = min(20, max(0, requested_limit))
            result = backend.search(keyword, max_results=max_results, **({'cursor': kwargs['cursor']} if kwargs.get('cursor') is not None else {}))
            status = self._observed_status(result)
            items = self._v4_notes_to_items((result.notes or [])[:max_results])
            detail_counts = {"attempted": 0, "succeeded": 0, "failed": 0, "pending": 0,
                             "not_attempted_no_native_id": 0, "reused_same_native_id": 0}
            detail_stop_reason = None
            detail_cache: dict[str, dict] = {}
            if not result.success:
                detail_stop_reason = self._detail_failure_state(result.error)
                if detail_stop_reason == "DETAIL_FAILED":
                    detail_stop_reason = "SEARCH_FAILED"

            for item in items:
                native_id, identity_error = self._observed_native_post_id(item)
                self._begin_detail_observation(item, native_id)
                if identity_error:
                    self._record_detail_outcome(item, "IDENTITY_MISMATCH")
                    detail_counts["failed"] += 1
                    detail_stop_reason = "IDENTITY_MISMATCH"
                    continue
                if not native_id:
                    self._record_detail_outcome(item, "NOT_ATTEMPTED_NO_NATIVE_ID")
                    detail_counts["not_attempted_no_native_id"] += 1
                    continue
                if detail_stop_reason:
                    self._record_detail_outcome(item, "PENDING", stop_reason=detail_stop_reason)
                    detail_counts["pending"] += 1
                    continue
                if native_id in detail_cache:
                    self._record_detail_outcome(item, "REUSED_SAME_NATIVE_ID", detail_cache[native_id])
                    detail_counts["succeeded"] += 1
                    detail_counts["reused_same_native_id"] += 1
                    continue

                detail_counts["attempted"] += 1
                try:
                    detail_result = backend.detail(item.get("url", ""))
                except Exception as exc:
                    logger.error("Facebook 逐帖详情失败 error_type=%s", type(exc).__name__)
                    detail_result = None
                detail_candidates = self._v4_notes_to_items(detail_result.notes or []) if detail_result else []
                matching_detail = None
                for candidate in detail_candidates:
                    candidate_id, candidate_identity_error = self._observed_native_post_id(candidate)
                    if candidate_identity_error:
                        continue
                    if candidate_id == native_id:
                        matching_detail = candidate
                        break

                if detail_result and detail_result.success and matching_detail is not None:
                    if self._has_verified_native_detail_body(matching_detail):
                        detail_cache[native_id] = matching_detail
                        self._record_detail_outcome(item, "SUCCESS", matching_detail)
                        detail_counts["succeeded"] += 1
                    else:
                        self._record_detail_outcome(item, "DETAIL_NOT_RETURNED", matching_detail)
                        detail_counts["failed"] += 1
                    continue

                if detail_candidates and matching_detail is None:
                    failure_state = "IDENTITY_MISMATCH"
                elif detail_result is None:
                    failure_state = "PROVIDER_UNAVAILABLE"
                elif detail_result.success:
                    failure_state = "DETAIL_NOT_RETURNED"
                else:
                    failure_state = self._detail_failure_state(detail_result.error)
                self._record_detail_outcome(item, failure_state)
                detail_counts["failed"] += 1
                if failure_state in {
                    "SESSION_EXPIRED", "RISK_WARNING", "BLOCKED", "PROVIDER_UNAVAILABLE", "IDENTITY_MISMATCH"
                }:
                    detail_stop_reason = failure_state

            detail_counts["pending"] = sum(
                1 for item in items
                if isinstance(item.get("raw"), dict)
                and item["raw"].get("detail_observation", {}).get("status") == "PENDING"
            )
            detail_incomplete = bool(detail_counts["failed"] or detail_counts["pending"]
                                     or detail_counts["not_attempted_no_native_id"])
            detail_metadata = {
                **detail_counts,
                "stop_reason": detail_stop_reason,
                "body_completeness": "NO_RESULTS" if not items else (
                    "COMPLETE" if not detail_incomplete else "PARTIAL"
                ),
                "media_semantics": "URL_HINTS_ONLY_NO_BYTES_OR_ARTIFACT",
            }
            if detail_stop_reason in {"SESSION_EXPIRED", "RISK_WARNING", "BLOCKED", "PROVIDER_UNAVAILABLE"}:
                status = {
                    "SESSION_EXPIRED": CollectionStatus.SESSION_EXPIRED,
                    "RISK_WARNING": CollectionStatus.RISK_WARNING,
                    "BLOCKED": CollectionStatus.BLOCKED,
                    "PROVIDER_UNAVAILABLE": CollectionStatus.PROVIDER_UNAVAILABLE,
                }[detail_stop_reason]
            elif detail_stop_reason == "IDENTITY_MISMATCH":
                status = CollectionStatus.COLLECT_ERROR
            message = ""
            if result.error:
                state = self._detail_failure_state(result.error)
                message = f"Facebook search state: {state}"
            elif detail_stop_reason:
                message = f"Facebook detail stopped: {detail_stop_reason}"
            elif detail_incomplete:
                message = "Facebook search completed with incomplete detail observations"
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=items,
                raw_count=result.raw_count,
                new_count=len(items),
                message=message,
                metadata={**(result.metadata or {}), "engine": "v4_facebook", "provider": "authorized_browser_worker",
                          "detail": detail_metadata},
            )
        except Exception as exc:
            logger.error("Facebook 主链路采集失败 error_type=%s", type(exc).__name__)
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE, platform=self.platform,
                message="Facebook provider unavailable",
                metadata={"provider": "authorized_browser_worker", "error_type": type(exc).__name__},
            )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("detail", content_id)

    def comments(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("comments", content_id, max_comments=kwargs.get("max_comments", 20),
                                 cursor=kwargs.get("cursor"), include_replies=kwargs.get("include_replies", False), source_url=kwargs.get('source_url'))

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("creator", creator_id)

    def author_posts(self, author_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("author_posts", author_id, max_results=kwargs.get("max_results", 20), cursor=kwargs.get("cursor"))

    def _delegate_v4(self, method: str, *args, **kwargs) -> CollectionResult:
        try:
            backend = self._load_backend()
            result = getattr(backend, method)(*args, **kwargs)
            status = self._observed_status(result)
            items = self._v4_notes_to_items(result.notes)
            comments = map_v4_comments(result.notes) if method == 'comments' else []
            return CollectionResult(status=status, platform=self.platform, items=[] if method == 'comments' else items,
                                    comments=comments,
                                    raw_count=result.raw_count,
                                    metadata={**(getattr(result, 'metadata', None) or {}),
                                              'provider': 'authorized_browser_worker'},
                                    message=(f"Facebook {method} state: {self._detail_failure_state(result.error)}"
                                             if result.error else ""))
        except Exception as exc:
            logger.error("Facebook %s provider failure error_type=%s", method, type(exc).__name__)
            return CollectionResult(status=CollectionStatus.PROVIDER_UNAVAILABLE, platform=self.platform,
                                    message="Facebook provider unavailable",
                                    metadata={"provider": "authorized_browser_worker",
                                              "error_type": type(exc).__name__})

    def health_check(self) -> CollectionResult:
        """Check the registered worker without reading credentials or resetting tabs."""
        from lumenis.adapters.human_browser import readonly_worker_health
        health = readonly_worker_health(self.platform)
        return CollectionResult(
            status=CollectionStatus(health["status"]), platform=self.platform,
            message="Facebook 专用只读浏览器状态；登录和采集结果仍需实际验证",
            metadata=health["metadata"],
        )


register_adapter("facebook", FacebookAdapter)
