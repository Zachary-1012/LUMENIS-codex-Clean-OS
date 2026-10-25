from __future__ import annotations

import logging
from typing import Any

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus, map_v4_comments
from .registry import register_adapter
from .response_shape import validate_acquisition_diagnostics

logger = logging.getLogger(__name__)

_TERMINAL_DETAIL_STATES = frozenset({
    "VERIFICATION_REQUIRED",
    "RATE_LIMITED",
    "SESSION_UNAVAILABLE",
    "SESSION_OR_RISK_REQUIRED",
    "PLATFORM_RISK",
    "NOT_CONFIGURED",
    "PROVIDER_UNAVAILABLE",
    "IDENTITY_MISMATCH",
})


class DouyinAdapter(BasePlatformAdapter):
    """抖音主链路适配器（薄封装 v4 DouyinAdapter 引擎）。

    v4 引擎已实现浏览器+JSON拦截+DOM 解析的完整搜索采集；
    本适配器负责将 v4 AdapterResult 映射为主链路 CollectionResult，
    不重复实现采集逻辑。detail/comments/creator 待 v4 引擎补全后接入。
    """

    platform = "douyin"
    enabled = False  # 需要 cookie + 浏览器环境，默认关闭，运行时检查后启用
    monitor_priority = "secondary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _load_backend(self):
        """懒加载 v4 DouyinAdapter 引擎。"""
        if self.backend is not None:
            return self.backend
        try:
            from lumenis.adapters.douyin import DouyinAdapter as V4DouyinAdapter
            self.backend = V4DouyinAdapter()
            return self.backend
        except Exception as exc:
            raise RuntimeError(f"无法加载 v4 抖音采集引擎: {exc}") from exc

    @staticmethod
    def _v4_status_to_main(success: bool, notes: list, error: str) -> CollectionStatus:
        """v4 AdapterResult(success/notes/error) → 主链路 CollectionStatus。"""
        if success:
            return CollectionStatus.SUCCESS if notes else CollectionStatus.NO_NEW_DATA
        err_lower = (error or "").lower()
        if any(k in err_lower for k in ("not configured", "not_configured", "cookie 缺失", "cookie 未配置", "未配置")):
            return CollectionStatus.NOT_CONFIGURED
        if any(k in err_lower for k in ("登录", "login", "session", "失效", "expired")):
            return CollectionStatus.SESSION_EXPIRED
        if any(k in err_lower for k in ("风控", "验证", "captcha", "verify", "risk", "频控", "rate")):
            return CollectionStatus.RISK_WARNING
        if any(k in err_lower for k in ("block", "封禁", "不可用")):
            return CollectionStatus.BLOCKED
        if any(k in err_lower for k in ("冷却", "cooling", "cooldown")):
            return CollectionStatus.COOLING_DOWN
        if any(k in err_lower for k in ("unavailable", "不可达", "暂不可用", "worker")):
            return CollectionStatus.PROVIDER_UNAVAILABLE
        return CollectionStatus.COLLECT_ERROR

    def _v4_notes_to_items(self, notes: list) -> list[dict]:
        """v4 CollectedNote → 主链路 items dict。"""
        items = []
        for n in notes or []:
            raw = getattr(n, "raw_data", {})
            raw = raw if isinstance(raw, dict) else {}
            if raw.get("engine") == "douyin_detail_api" or "metrics" in raw:
                metrics = raw.get("metrics")
                play_count = metrics.get("play_count") if isinstance(metrics, dict) else None
            else:
                play_count = raw.get("play_count")
            views = play_count if type(play_count) is int and play_count >= 0 else None
            item = self.normalize_item({
                "platform_content_id": raw.get("aweme_id", ""),
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
                "views": views,
                "raw": raw,
            })
            # The shared transport normalizer intentionally keeps only its
            # cross-platform fields. Restore this native optional metric on
            # the Douyin item so its search observation can be archived before
            # exact-ID detail replaces the current value.
            item["views"] = views
            items.append(item)
        return items

    @staticmethod
    def _native_aweme_id(item: dict) -> str | None:
        raw = item.get("raw") if isinstance(item, dict) else None
        value = raw.get("aweme_id") if isinstance(raw, dict) else None
        if not isinstance(value, str) or not value or value != value.strip():
            return None
        return value

    @staticmethod
    def _detail_failure_state(error: str) -> str:
        text = str(error or "").lower()
        verification = ("captcha", "验证码", "安全验证", "need_verify", "verify")
        rate_limit = ("rate limit", "rate_limit", "频控", "访问频繁", "too many", "http 429", " 429")
        session = ("login", "登录", "cookie", "session", "会话", "失效", "expired")
        risk = ("风控", "risk", "blocked", "封禁", "http 403", " 403")
        if any(marker in text for marker in verification):
            return "VERIFICATION_REQUIRED"
        if any(marker in text for marker in rate_limit):
            return "RATE_LIMITED"
        has_session = any(marker in text for marker in session)
        has_risk = any(marker in text for marker in risk)
        if has_session and has_risk:
            return "SESSION_OR_RISK_REQUIRED"
        if has_session:
            return "SESSION_UNAVAILABLE"
        if has_risk:
            return "PLATFORM_RISK"
        if "not configured" in text or "not_configured" in text or "未配置" in text:
            return "NOT_CONFIGURED"
        if any(marker in text for marker in ("worker", "network", "timeout", "不可达", "provider")):
            return "PROVIDER_UNAVAILABLE"
        return "DETAIL_FAILED"

    @staticmethod
    def _begin_detail_observation(item: dict, native_id: str | None) -> dict:
        raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        raw = dict(raw)
        raw["search_summary_observation"] = {
            "status": "OBSERVED",
            "body_kind": "search_summary",
            "text": item.get("content") if isinstance(item.get("content"), str) else None,
            "title": item.get("title") if isinstance(item.get("title"), str) else None,
            "source_url": item.get("url") if isinstance(item.get("url"), str) else None,
            "native_id": native_id,
            "native_id_locator": "$.data[].aweme_info.aweme_id",
            "body_locator": "$.data[].aweme_info.desc",
            "native_time": raw.get("create_time"),
            "native_time_locator": "$.data[].aweme_info.create_time",
            "metrics": {name: item.get(name) for name in ("likes", "comments", "collects", "shares", "views")},
            "metrics_locator": "$.data[].aweme_info.statistics",
        }
        item["raw"] = raw
        return raw

    @staticmethod
    def _record_detail_outcome(item: dict, status: str, detail_item: dict | None = None,
                               stop_reason: str | None = None) -> None:
        raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        raw = dict(raw)
        detail_raw = detail_item.get("raw") if isinstance(detail_item, dict) else None
        detail_raw = detail_raw if isinstance(detail_raw, dict) else {}
        body = detail_item.get("content") if isinstance(detail_item, dict) else None
        body = body if isinstance(body, str) else None
        success = detail_item is not None
        body_status = ("DETAIL_BODY_AVAILABLE" if body else "DETAIL_BODY_EMPTY") if success else (
            "PENDING" if status == "PENDING" else "SUMMARY_ONLY"
        )
        media_hints = detail_raw.get("media_hints") if success else None
        media_state = detail_raw.get("media_state") if success else (
            "PENDING" if status == "PENDING" else "DETAIL_NOT_OBSERVED"
        )
        raw["detail_observation"] = {
            "status": status,
            "stop_reason": stop_reason or (status if status in _TERMINAL_DETAIL_STATES else None),
            "body_kind": "caption" if success else None,
            "body": body,
            "body_status": body_status,
            "body_locator": detail_raw.get("body_locator") if success else None,
            "source_url": detail_item.get("url") if success else None,
            "native_time": detail_raw.get("create_time") if success else None,
            "native_time_locator": detail_raw.get("native_time_locator") if success else None,
            "native_time_status": ("OBSERVED" if detail_raw.get("create_time") is not None else "NOT_RETURNED_BY_DETAIL") if success else (
                "PENDING" if status == "PENDING" else "SEARCH_ONLY"
            ),
            "native_metrics": detail_raw.get("metrics") if success else None,
            "metrics_locator": detail_raw.get("metrics_locator") if success else None,
            "metrics_status": ("OBSERVED" if detail_raw.get("metrics") is not None else "NOT_RETURNED_BY_DETAIL") if success else (
                "PENDING" if status == "PENDING" else "SEARCH_ONLY"
            ),
            "media_hints": media_hints,
            "media_state": media_state,
            "media_bytes_saved": False,
            "artifact_created": False,
            "author_locator": detail_raw.get("author_locator") if success else None,
        }
        item["raw"] = raw
        if not success:
            # Keep the search text only in its explicitly labeled summary locator.
            # The native-record caller falls back from an empty body to title,
            # so clear both fields to prevent promoting a search summary as body.
            item["content"] = ""
            item["title"] = ""
            item["views"] = None
            raw["play_count"] = None
            return
        detail_metrics = detail_raw.get("metrics")
        play_count = detail_metrics.get("play_count") if isinstance(detail_metrics, dict) else None
        if type(play_count) is not int or play_count < 0:
            play_count = None
        item["views"] = play_count
        raw["play_count"] = play_count
        # Search time remains archived in search_summary_observation; the
        # current native field follows this successful exact-ID detail only.
        raw["create_time"] = detail_raw.get("create_time")
        item["content"] = body or ""
        item["publish_datetime"] = detail_item.get("publish_datetime") or ""
        item["url"] = detail_item.get("url") or item.get("url") or ""
        item["title"] = detail_item.get("title") or ""
        for field in ("likes", "comments", "collects", "shares"):
            # None means the detail response did not supply a value; zero remains zero.
            item[field] = detail_item.get(field)
        for field in ("author_id", "author_nickname"):
            value = detail_item.get(field)
            if value not in (None, ""):
                item[field] = value

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        try:
            backend = self._load_backend()
            max_results = int(kwargs.get("max_results", 20))
            if hasattr(backend, "breaker") and callable(getattr(backend, "safe_collect", None)):
                result = backend.safe_collect(keyword, max_results=max_results, allow_fallback=False)
            else:
                result = backend.search(keyword, max_results=max_results)
            status = self._v4_status_to_main(result.success, result.notes, result.error)
            search_failure_state = self._detail_failure_state(result.error) if not result.success else None
            if search_failure_state == "DETAIL_FAILED":
                search_failure_state = "SEARCH_FAILED"
            items = self._v4_notes_to_items(result.notes)
            detail_counts = {"attempted": 0, "succeeded": 0, "failed": 0, "pending": 0,
                             "not_attempted_no_native_id": 0, "reused_same_native_id": 0}
            detail_stop_reason = None
            detail_cache = {}
            for item in items:
                native_id = self._native_aweme_id(item)
                self._begin_detail_observation(item, native_id)
                if not native_id:
                    self._record_detail_outcome(item, "NOT_ATTEMPTED_NO_NATIVE_ID")
                    detail_counts["not_attempted_no_native_id"] += 1
                    continue
                if item.get("platform_content_id") != native_id:
                    self._record_detail_outcome(item, "IDENTITY_MISMATCH")
                    detail_counts["failed"] += 1
                    detail_stop_reason = "IDENTITY_MISMATCH"
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
                if not result.success:
                    detail_stop_reason = self._detail_failure_state(result.error)
                    self._record_detail_outcome(item, "PENDING", stop_reason=detail_stop_reason)
                    detail_counts["pending"] += 1
                    continue

                detail_counts["attempted"] += 1
                try:
                    detail_result = backend.detail(aweme_id=native_id)
                except Exception as exc:
                    logger.error("抖音逐帖详情异常 error_type=%s", type(exc).__name__)
                    detail_result = None
                detail_candidates = self._v4_notes_to_items(detail_result.notes) if detail_result else []
                matching_detail = next((candidate for candidate in detail_candidates
                                        if self._native_aweme_id(candidate) == native_id), None)
                if detail_result and detail_result.success and matching_detail is not None:
                    detail_cache[native_id] = matching_detail
                    self._record_detail_outcome(item, "SUCCESS", matching_detail)
                    detail_counts["succeeded"] += 1
                    continue

                if detail_candidates and matching_detail is None:
                    failure_state = "IDENTITY_MISMATCH"
                else:
                    failure_state = self._detail_failure_state(
                        detail_result.error if detail_result else "provider unavailable"
                    )
                self._record_detail_outcome(item, failure_state)
                detail_counts["failed"] += 1
                if failure_state in _TERMINAL_DETAIL_STATES:
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
                "search_state": status.value,
                "search_failure_state": search_failure_state,
                "body_completeness": ("NO_RESULTS" if result.success else "NOT_OBSERVED") if not items else (
                    "COMPLETE" if not detail_incomplete else "PARTIAL"
                ),
                "media_semantics": "URL_HINTS_ONLY_NO_BYTES_OR_ARTIFACT",
            }
            if detail_stop_reason and result.success:
                # An unsuccessful search keeps its original access state even
                # when already observed search cards remain pending detail.
                status = {
                    "VERIFICATION_REQUIRED": CollectionStatus.NEED_VERIFY,
                    "RATE_LIMITED": CollectionStatus.COOLING_DOWN,
                    "SESSION_UNAVAILABLE": CollectionStatus.SESSION_EXPIRED,
                    "SESSION_OR_RISK_REQUIRED": CollectionStatus.RISK_WARNING,
                    "PLATFORM_RISK": CollectionStatus.RISK_WARNING,
                    "NOT_CONFIGURED": CollectionStatus.NOT_CONFIGURED,
                    "PROVIDER_UNAVAILABLE": CollectionStatus.PROVIDER_UNAVAILABLE,
                }.get(detail_stop_reason, CollectionStatus.COLLECT_ERROR)
            try:
                acquisition_diagnostics = validate_acquisition_diagnostics(
                    getattr(result, "diagnostics", {}))
            except Exception:
                # A malformed optional diagnostic never changes business truth.
                acquisition_diagnostics = {}
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=items,
                raw_count=result.raw_count,
                new_count=len(items),
                message=(result.error or ("抖音搜索成功；部分原生详情未完成" if detail_incomplete else "")),
                metadata={"engine": "v4_douyin_browser", "provider": "authorized_browser_worker",
                          "duration_s": result.duration_seconds, "detail": detail_metadata,
                          **({"acquisition_diagnostics": acquisition_diagnostics}
                             if acquisition_diagnostics else {}),
                          **({"error_type": detail_stop_reason or search_failure_state}
                             if detail_stop_reason or search_failure_state else {})},
            )
        except Exception as exc:
            logger.error("抖音主链路采集异常 error_type=%s", type(exc).__name__)
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="抖音采集提供方暂不可用",
                metadata={"provider": "authorized_browser_worker", "error_type": type(exc).__name__},
            )

    def _delegate_v4(self, method: str, *args, **kwargs) -> CollectionResult:
        try:
            backend = self._load_backend()
            fn = getattr(backend, method, None)
            if not callable(fn):
                return CollectionResult(
                    status=CollectionStatus.NOT_SUPPORTED,
                    platform=self.platform,
                    message=f"Douyin provider does not support {method}",
                    metadata={"provider": "authorized_browser_worker", "capability": method},
                )
            result = fn(*args, **kwargs)
            status = self._v4_status_to_main(result.success, result.notes, result.error)
            comments = map_v4_comments(result.notes) if method == "comments" else []
            items = [] if method == "comments" else self._v4_notes_to_items(result.notes)
            return CollectionResult(
                status=status, platform=self.platform, items=items, comments=comments,
                raw_count=result.raw_count, new_count=len(comments) if method == "comments" else len(items),
                message=result.error or "",
                metadata={**(result.metadata if isinstance(getattr(result, "metadata", None), dict) else {}),
                          "engine": f"v4_douyin_{method}", "provider": "authorized_browser_worker",
                          "duration_s": result.duration_seconds},
            )
        except Exception as exc:
            logger.error("抖音主链路 %s 异常 error_type=%s", method, type(exc).__name__)
            return CollectionResult(status=CollectionStatus.PROVIDER_UNAVAILABLE, platform=self.platform,
                                    message="抖音采集提供方暂不可用",
                                    metadata={"provider": "authorized_browser_worker",
                                              "error_type": type(exc).__name__})

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("detail", aweme_id=content_id)

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        options = {}
        if kwargs.get('cursor') is not None:
            options['cursor'] = kwargs['cursor']
        if include_replies:
            options['include_replies'] = True
        return self._delegate_v4("comments", aweme_id=content_id, max_comments=kwargs.get("max_comments", 20), **options)

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return self._delegate_v4("creator", sec_uid=creator_id)

    def health_check(self, **kwargs: Any) -> CollectionResult:
        """Check configured worker reachability without launching a browser."""
        try:
            from lumenis.adapters.douyin import _configured_browser_worker_url
            from lumenis.adapters.human_browser import is_cdp_url_open
            cdp_url = _configured_browser_worker_url()
        except Exception as exc:
            profile_unavailable = (
                isinstance(exc, RuntimeError)
                and str(exc) in {
                    "DOUYIN_READONLY worker profile is not bound to the configured loopback port",
                    "READONLY_WORKER_PROFILE_MODE_OR_KERNEL_UNAVAILABLE",
                }
            )
            if profile_unavailable:
                return CollectionResult(
                    status=CollectionStatus.PROVIDER_UNAVAILABLE,
                    platform=self.platform,
                    message="抖音远程浏览器工作器不可达",
                    metadata={"provider": "authorized_browser_worker", "endpoint_configured": True,
                              "binding_reason": "READONLY_WORKER_PROFILE_MODE_OR_KERNEL_UNAVAILABLE",
                              "healthcheck_scope": "worker_connectivity"},
                )

            error_message = str(exc) if isinstance(exc, RuntimeError) else ""
            boundary_errors = {
                "DOUYIN_CDP_URL must be a plain worker endpoint URL",
                "DOUYIN_CDP_URL must identify a remote browser worker",
                "DOUYIN_CDP_URL loopback is restricted to the opted-in DOUYIN_READONLY worker",
            }
            binding_reason = (
                "READONLY_WORKER_BOUNDARY_INVALID"
                if error_message in boundary_errors
                else "READONLY_WORKER_NOT_CONFIGURED"
            )
            return CollectionResult(
                status=CollectionStatus.NOT_CONFIGURED,
                platform=self.platform,
                message="抖音远程浏览器工作器尚未配置",
                metadata={"provider": "authorized_browser_worker", "endpoint_configured": False,
                          "binding_reason": binding_reason,
                          "healthcheck_scope": "configuration_only"},
            )
        if not is_cdp_url_open(cdp_url):
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="抖音远程浏览器工作器不可达",
                metadata={"provider": "authorized_browser_worker", "endpoint_configured": True,
                          "healthcheck_scope": "worker_connectivity"},
            )
        try:
            backend = self._load_backend()
            engine_ok = backend is not None
        except Exception:
            engine_ok = False
        return CollectionResult(
            status=CollectionStatus.NEED_VERIFY if engine_ok else CollectionStatus.PROVIDER_UNAVAILABLE,
            platform=self.platform,
            message="抖音浏览器工作器可达；授权态仅在本次人工请求中验证",
            metadata={"provider": "authorized_browser_worker", "endpoint_configured": True,
                      "session_state": "worker_reachable_unverified",
                      "healthcheck_scope": "worker_connectivity", "engine_ok": engine_ok},
        )


register_adapter("douyin", DouyinAdapter)
