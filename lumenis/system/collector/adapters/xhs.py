from __future__ import annotations

import datetime
import os
import re
from typing import Any, Callable, Optional

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .config import PLATFORM_CAPABILITIES
from .registry import register_adapter

_XHS_UPSTREAM_ERROR_CODES = frozenset({
    "IP_RISK_OR_300012",
    "SESSION_EXPIRED",
    "NEED_VERIFY",
    "COLLECTOR_ENDPOINT_NOT_CONFIGURED",
    "COLLECTOR_ENDPOINT_INVALID",
    "POLICY_BLOCKED",
    "LOCAL_COLLECTOR_ENDPOINT_FORBIDDEN",
    "COLLECTOR_ENDPOINT_UNAVAILABLE",
    "COLLECTOR_SCRIPT_UNAVAILABLE",
    "CDP_EMPTY_OR_LOAD_FAILED",
    "CDP_TIMEOUT_PARTIAL",
    "CDP_TIMEOUT_NO_CHECKPOINT",
    "COLLECTOR_PROVIDER_FAILURE",
    "CDP_CHUNK_BUDGET_NO_VERIFIED_DETAIL",
    "CDP_TIME_BUDGET_PARTIAL",
    "CDP_PORT_NOT_ALLOWED",
    "DETAIL_IDENTITY_UNVERIFIED",
    "DETAIL_IDENTITY_MISMATCH",
    "DETAIL_SOURCE_UNVERIFIED",
    "NO_DETAIL",
    "COVER_ONLY_REQUIRES_HUMAN_MODE",
    "SEARCH_STATE_UNAVAILABLE",
    "SOURCE_HOST_MISMATCH",
    "SEARCH_TRANSITION_UNVERIFIED",
    "SOURCE_NO_RESULTS",
    "LOAD_FAILED",
    "LIST_PARSE_UNAVAILABLE",
    "SEARCH_LOADING_TIMEOUT",
    "EMPTY_LIST_UNCLASSIFIED",
    "INVALID_DETAIL_MEDIA_MODE",
    "INVALID_WORKER_CHUNK_SECONDS",
    "INVALID_ACQUISITION_FINGERPRINT",
    "INVALID_TIME_BUDGET",
    "XHS_CHECKPOINT_PATH_INVALID",
})

_XHS_SEARCH_DIAGNOSTIC_VERSION = "xhs-search-state-v1"
_XHS_SEARCH_DIAGNOSTIC_PHASES = frozenset({
    "landing",
    "search_submitted",
    "search_wait_failed",
    "search_ready",
    "before_list_parse",
    "empty_list",
    "before_detail_select",
})
_XHS_SEARCH_DIAGNOSTIC_QUERY_ENCODINGS = frozenset({"literal", "percent_encoded_once", "unverified"})
_XHS_SEARCH_DIAGNOSTIC_READY_STATES = frozenset({"loading", "interactive", "complete", "unknown"})
_XHS_SEARCH_DIAGNOSTIC_SELECTORS = ("section.note-item", "a.cover", ".feeds-container")
_XHS_SEARCH_DIAGNOSTIC_EMPTY_INDICATORS = frozenset({
    "暂无搜索结果",
    "没有找到相关内容",
    "无搜索结果",
    "No results found",
})
_XHS_SEARCH_DIAGNOSTIC_ERROR_TYPES = frozenset({
    "Error",
    "TargetClosedError",
    "TimeoutError",
    "TypeError",
    "ValueError",
    "RuntimeError",
    "OSError",
    "AssertionError",
})
_XHS_SEARCH_DIAGNOSTIC_MAX_COUNT = 1_000_000
_XHS_SEARCH_DIAGNOSTIC_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?"
)


def _safe_xhs_search_diagnostics(value: Any) -> dict[str, Any] | None:
    """Project worker search observations into a bounded, non-secret diagnostic."""
    if type(value) is not dict:
        return None
    version = value.get("version")
    if type(version) is not str or version != _XHS_SEARCH_DIAGNOSTIC_VERSION:
        return None
    observations = value.get("observations")
    if type(observations) is not list:
        return None

    def safe_count(item: Any) -> int | None:
        if type(item) is int and 0 <= item <= _XHS_SEARCH_DIAGNOSTIC_MAX_COUNT:
            return item
        return None

    def safe_enum(item: Any, allowed: frozenset[str]) -> str | None:
        if type(item) is str and len(item) <= 64 and item in allowed:
            return item
        return None

    def safe_timestamp(item: Any) -> str | None:
        if (type(item) is not str or not 19 <= len(item) <= 40
                or _XHS_SEARCH_DIAGNOSTIC_TIMESTAMP.fullmatch(item) is None):
            return None
        try:
            datetime.datetime.fromisoformat(
                item[:-1] + "+00:00" if item.endswith("Z") else item
            )
        except ValueError:
            return None
        return item

    safe_observations: list[dict[str, Any]] = []
    for observation in observations[-12:]:
        if type(observation) is not dict:
            continue
        safe: dict[str, Any] = {
            "phase": safe_enum(observation.get("phase"), _XHS_SEARCH_DIAGNOSTIC_PHASES),
            "observed_at": safe_timestamp(observation.get("observed_at")),
        }
        for key in ("host_matches", "route_is_search", "query_matches", "input_matches"):
            item = observation.get(key)
            safe[key] = item if type(item) is bool else None
        safe["query_encoding"] = safe_enum(
            observation.get("query_encoding"), _XHS_SEARCH_DIAGNOSTIC_QUERY_ENCODINGS
        )
        safe["document_ready_state"] = safe_enum(
            observation.get("document_ready_state"), _XHS_SEARCH_DIAGNOSTIC_READY_STATES
        )

        selector_counts = observation.get("selector_counts")
        selector_counts = selector_counts if type(selector_counts) is dict else {}
        safe["selector_counts"] = {
            selector: safe_count(selector_counts.get(selector))
            for selector in _XHS_SEARCH_DIAGNOSTIC_SELECTORS
        }
        for key in ("note_link_count", "body_character_count", "loading_element_count"):
            safe[key] = safe_count(observation.get(key))

        indicators = observation.get("native_empty_indicators")
        safe_indicators: list[str] = []
        if type(indicators) is list:
            for indicator in indicators:
                if (type(indicator) is str and indicator in _XHS_SEARCH_DIAGNOSTIC_EMPTY_INDICATORS
                        and indicator not in safe_indicators):
                    safe_indicators.append(indicator)
        safe["native_empty_indicators"] = (
            safe_indicators if safe_indicators or indicators == [] else None
        )

        for key in ("wait_error_type", "diagnostic_error_type"):
            if key in observation:
                error_type = observation.get(key)
                safe[key] = (
                    error_type
                    if type(error_type) is str and len(error_type) <= 64
                    and error_type in _XHS_SEARCH_DIAGNOSTIC_ERROR_TYPES
                    else "UNRECOGNIZED_ERROR_TYPE"
                )
        safe_observations.append(safe)

    if not safe_observations:
        return None
    return {"version": _XHS_SEARCH_DIAGNOSTIC_VERSION, "observations": safe_observations}


def _xhs_failure_reason(error_code: str) -> str:
    if error_code in _XHS_UPSTREAM_ERROR_CODES:
        return error_code
    if error_code == "CDP_EXCEPTION" or error_code.startswith("CDP_EXCEPTION:"):
        return "CDP_EXCEPTION"
    return "XHS_UPSTREAM_ERROR_UNKNOWN"


class XiaohongshuAdapter(BasePlatformAdapter):
    """Adapter around the existing production XHS collector.

    This is intentionally a thin boundary layer. The existing collector remains the
    source of truth until local regression tests prove a safe migration. No subject
    filtering or business logic is duplicated here.
    """

    platform = "xhs"
    enabled = True
    monitor_priority = "primary"

    def __init__(self, *, backend: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.backend = backend

    def _load_backend(self) -> Any:
        if self.backend is not None:
            return self.backend
        try:
            import collector  # existing production collector.py
            return collector
        except Exception as exc:
            raise RuntimeError(f"Unable to load existing XHS collector: {exc}") from exc

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        try:
            detail_media_mode = kwargs.get("detail_media_mode", "legacy")
            if not isinstance(detail_media_mode, str) or detail_media_mode not in {"legacy", "cover_only"}:
                return self._failed_result("INVALID_DETAIL_MEDIA_MODE")
            effective_detail_media_mode = detail_media_mode
            detail_media_mode_reason = "requested"
            backend = self._load_backend()
            fn = getattr(backend, "search_xiaohongshu")
            acquisition_fingerprint = kwargs.get("acquisition_fingerprint")
            if (acquisition_fingerprint is not None
                    and (not isinstance(acquisition_fingerprint, str)
                         or re.fullmatch(r"[0-9a-f]{64}", acquisition_fingerprint) is None)):
                return self._failed_result("INVALID_ACQUISITION_FINGERPRINT")

            if acquisition_fingerprint is not None:
                requested_limit = kwargs.get("max_results")
                if requested_limit is None:
                    requested_limit = kwargs.get("max_details", 10)
                if isinstance(requested_limit, bool):
                    return self._failed_result("INVALID_MAX_RESULTS")
                try:
                    detail_limit = int(requested_limit)
                except (TypeError, ValueError, OverflowError):
                    return self._failed_result("INVALID_MAX_RESULTS")
                if detail_limit <= 0:
                    return self._failed_result("INVALID_MAX_RESULTS")
                detail_limit = min(detail_limit, 20)
                region = kwargs.get("region") or "intl"
                account = kwargs.get("account")
            else:
                # Preserve the pre-existing legacy contract: zero means all
                # observed cards for this invocation, and account/region remain
                # selected by the existing collector policy owner.
                try:
                    detail_limit = int(kwargs.get("max_details", 10))
                except (TypeError, ValueError, OverflowError):
                    return self._failed_result("INVALID_MAX_DETAILS")
                region = "intl"
                account = None
            output_path = kwargs.get("output_path")
            resume_path = kwargs.get("resume_path") if acquisition_fingerprint is None else None
            checkpoint_owner = None
            resume_snapshot = None
            prior = None
            expected_identity_fingerprint = None
            if acquisition_fingerprint is not None:
                from ..guard.checkpoint import Checkpoint

                checkpoint_owner = Checkpoint("xhs")
                expected_identity_fingerprint = backend.xhs_expected_identity_fingerprint(
                    account=account, region=region)
                prior = checkpoint_owner.get_operational_resume(keyword, acquisition_fingerprint)
                caller_resume_path = kwargs.get("resume_path")
                if prior is not None and prior.get("continuation_required") is True:
                    resume_snapshot = backend.verify_xhs_raw_checkpoint_reference(
                        prior, acquisition_fingerprint=acquisition_fingerprint, keyword=keyword)
                    if (resume_snapshot.get("complete") is True
                            or resume_snapshot.get("continuation_required") is not True
                            or resume_snapshot.get("identity_fingerprint") != expected_identity_fingerprint):
                        return self._failed_result("XHS_CHECKPOINT_BINDING_MISMATCH")
                    effective_detail_media_mode = resume_snapshot.get("detail_media_mode", "legacy")
                    if (not isinstance(effective_detail_media_mode, str)
                            or effective_detail_media_mode not in {"legacy", "cover_only"}):
                        return self._failed_result("XHS_CHECKPOINT_MEDIA_MODE_INVALID")
                    detail_media_mode_reason = (
                        "checkpoint_resume"
                        if effective_detail_media_mode == detail_media_mode
                        else "legacy_resume" if effective_detail_media_mode == "legacy"
                        else "checkpoint_mode_resume"
                    )
                    if (caller_resume_path
                            and os.path.normcase(os.path.abspath(caller_resume_path))
                            != os.path.normcase(resume_snapshot["raw_path"])):
                        return self._failed_result("XHS_CHECKPOINT_REFERENCE_MISMATCH")
                    resume_path = resume_snapshot["raw_path"]
                elif caller_resume_path:
                    # Purpose-bound resume is accepted only through the existing
                    # metadata checkpoint owner and its exact task binding.
                    return self._failed_result("XHS_CHECKPOINT_REFERENCE_MISSING")

                try:
                    output_path = output_path or backend.new_xhs_raw_checkpoint_path(
                        acquisition_fingerprint, keyword)
                    output_path = backend.validate_xhs_raw_checkpoint_path(
                        output_path, must_be_new=True)
                    if resume_path:
                        resume_path = backend.validate_xhs_raw_checkpoint_path(
                            resume_path, must_exist=True)
                        if os.path.normcase(resume_path) == os.path.normcase(output_path):
                            raise ValueError("XHS_CHECKPOINT_PATH_REUSED")
                except (OSError, ValueError):
                    return self._failed_result("XHS_CHECKPOINT_PATH_INVALID")

            call_kwargs = {
                "max_scroll": int(kwargs.get("max_scroll", 4)),
                "output_path": output_path,
                "max_details": detail_limit,
                "region": region,
                "account": account,
                "worker_chunk_seconds": kwargs.get("worker_chunk_seconds", 300),
                "acquisition_fingerprint": acquisition_fingerprint,
                "detail_media_mode": effective_detail_media_mode,
            }
            if resume_path:
                call_kwargs["resume_path"] = resume_path
            if "time_budget" in kwargs:
                call_kwargs["time_budget"] = kwargs.get("time_budget")
            raw = fn(
                keyword,
                **call_kwargs,
            )
            raw = raw if isinstance(raw, dict) else {}
            notes = raw.get("notes", [])
            notes = [item for item in notes if isinstance(item, dict)] if isinstance(notes, list) else []
            error = raw.get("error", "") if isinstance(raw, dict) else ""
            error_code = str(error or "").strip().upper()
            actual_media_mode = raw.get("detail_media_mode")
            if isinstance(actual_media_mode, str) and actual_media_mode in {"legacy", "cover_only"}:
                if resume_snapshot is not None and actual_media_mode != effective_detail_media_mode:
                    return self._failed_result(
                        "XHS_CHECKPOINT_MEDIA_MODE_MISMATCH",
                        items=[item for item in notes
                               if raw.get("identity_verified") is True
                               and item.get("detail_fetched") is True
                               and item.get("detail_identity_verified") is True],
                        continuation_required=True,
                    )
                if resume_snapshot is None and not resume_path and actual_media_mode != effective_detail_media_mode:
                    return self._failed_result(
                        "XHS_DETAIL_MEDIA_MODE_MISMATCH",
                        items=[item for item in notes
                               if raw.get("identity_verified") is True
                               and item.get("detail_fetched") is True
                               and item.get("detail_identity_verified") is True],
                    )
                effective_detail_media_mode = actual_media_mode
                if resume_path and resume_snapshot is None and actual_media_mode != detail_media_mode:
                    detail_media_mode_reason = "terminal_replay"

            continuation_snapshot = None
            continuation_persisted = None
            if acquisition_fingerprint is not None:
                if not os.path.isfile(output_path):
                    # A provider/configuration failure before the worker writes
                    # a new Raw chunk leaves the previously verified pointer intact.
                    continuation_snapshot = resume_snapshot
                    continuation_persisted = bool(resume_snapshot and prior)
                else:
                    try:
                        continuation_snapshot = backend.inspect_xhs_raw_checkpoint(output_path)
                        if (continuation_snapshot.get("identity_verified") is not True
                                or continuation_snapshot.get("task_binding") != acquisition_fingerprint
                                or continuation_snapshot.get("keyword") != keyword
                                or continuation_snapshot.get("source_host") != "www.rednote.com"
                                or continuation_snapshot.get("identity_fingerprint") != expected_identity_fingerprint):
                            raise ValueError("XHS_CHECKPOINT_BINDING_MISMATCH")
                    except Exception as exc:
                        safe_code = str(exc).strip()
                        if re.fullmatch(r"[A-Z][A-Z0-9_]{0,100}", safe_code) is None:
                            safe_code = type(exc).__name__
                        return self._failed_result(
                            safe_code,
                            items=[item for item in notes
                                   if raw.get("identity_verified") is True
                                   and item.get("detail_fetched") is True
                                   and item.get("detail_identity_verified") is True],
                            continuation_required=bool(resume_snapshot and resume_snapshot.get("continuation_required")),
                        )

                    saved = checkpoint_owner.save_operational_resume(
                        keyword,
                        acquisition_fingerprint,
                        continuation_snapshot,
                    )
                    continuation_persisted = bool(saved)
                    if (not saved and (continuation_snapshot.get("continuation_required")
                                       or (resume_snapshot and resume_snapshot.get("continuation_required")))):
                        return self._failed_result(
                            "XHS_CHECKPOINT_SAVE_FAILED",
                            items=[item for item in notes
                                   if raw.get("identity_verified") is True
                                   and item.get("detail_fetched") is True
                                   and item.get("detail_identity_verified") is True],
                            pending_note_ids=continuation_snapshot.get("pending_note_ids", []),
                            continuation_required=bool(continuation_snapshot.get("continuation_required")),
                        )

            if acquisition_fingerprint is not None:
                notes = [item for item in notes
                         if raw.get("identity_verified") is True
                         and item.get("detail_fetched") is True
                         and item.get("detail_identity_verified") is True]

            summary = raw.get("summary") if isinstance(raw.get("summary"), dict) else {}
            raw_pending = summary.get("pending_note_ids", [])
            pending_note_ids = [note_id for note_id in raw_pending
                                if isinstance(note_id, str)
                                and re.fullmatch(r"[0-9a-fA-F]{24}", note_id)] \
                if isinstance(raw_pending, list) else []
            if continuation_snapshot is not None:
                pending_note_ids = list(continuation_snapshot.get("pending_note_ids", []))
            continuation_required = bool(
                continuation_snapshot.get("continuation_required")
                if continuation_snapshot is not None else summary.get("continuation_required", False)
            )
            checkpoint_complete = (
                continuation_snapshot.get("complete")
                if continuation_snapshot is not None else None
            )
            checkpoint_identity_verified = bool(
                continuation_snapshot.get("identity_verified")
                if continuation_snapshot is not None else raw.get("identity_verified")
            )
            captured_at = (
                continuation_snapshot.get("captured_at")
                if continuation_snapshot is not None
                else next((item.get("collected_at") for item in reversed(notes)
                           if item.get("collected_at")), None)
            )

            if error_code == "IP_RISK_OR_300012":
                status = CollectionStatus.RISK_WARNING
            elif error_code == "SESSION_EXPIRED":
                status = CollectionStatus.SESSION_EXPIRED
            elif error_code == "NEED_VERIFY":
                status = CollectionStatus.NEED_VERIFY
            elif error_code in {
                "COLLECTOR_ENDPOINT_NOT_CONFIGURED",
                "COLLECTOR_ENDPOINT_INVALID",
                "POLICY_BLOCKED",
                "LOCAL_COLLECTOR_ENDPOINT_FORBIDDEN",
            }:
                status = CollectionStatus.NOT_CONFIGURED
            elif error_code in {
                "COLLECTOR_ENDPOINT_UNAVAILABLE",
                "COLLECTOR_SCRIPT_UNAVAILABLE",
                "CDP_EMPTY_OR_LOAD_FAILED",
                "CDP_TIMEOUT_PARTIAL",
                "CDP_TIMEOUT_NO_CHECKPOINT",
                "COLLECTOR_PROVIDER_FAILURE",
            }:
                status = CollectionStatus.PROVIDER_UNAVAILABLE
            elif error_code:
                status = CollectionStatus.COLLECT_ERROR
            elif notes:
                status = CollectionStatus.SUCCESS
            else:
                status = CollectionStatus.NO_NEW_DATA
            channel = raw.get("channel") if isinstance(raw, dict) else None
            collected_at = (
                (raw.get("collected_at") if isinstance(raw, dict) else None)
                or next((item.get("captured_at") for item in notes if isinstance(item, dict) and item.get("captured_at")), None)
                or datetime.datetime.now().isoformat(timespec="seconds")
            )
            provider = "authorized_browser_worker" if channel in {"worker", "authorized_browser_worker", "cdp"} else "existing_xhs_collector"
            message_by_status = {
                CollectionStatus.NOT_CONFIGURED: "香港/国际小红书授权浏览器 Worker 尚未配置",
                CollectionStatus.PROVIDER_UNAVAILABLE: "香港/国际小红书采集 Worker 暂不可用",
                CollectionStatus.RISK_WARNING: "平台返回风险信号，已停止采集",
                CollectionStatus.NEED_VERIFY: "平台要求人工完成安全验证",
                CollectionStatus.SESSION_EXPIRED: "小红书登录会话失效或设备登录受限，请在获准的香港/国际账号上重新登录",
                CollectionStatus.COLLECT_ERROR: "现有小红书采集链未能完成本次请求",
            }
            failure_detail = None
            if status not in {CollectionStatus.SUCCESS, CollectionStatus.NO_NEW_DATA}:
                failure_detail = {
                    "state": status.value,
                    "reason": _xhs_failure_reason(error_code),
                }
                search_diagnostics = _safe_xhs_search_diagnostics(raw.get("search_diagnostics"))
                if search_diagnostics is not None:
                    failure_detail["search_diagnostics"] = search_diagnostics
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=notes,
                raw_count=int(raw.get("total", len(notes))) if isinstance(raw, dict) else len(notes),
                new_count=len(notes),
                message=message_by_status.get(status, ""),
                metadata={
                    "channel": channel,
                    "provider": provider,
                    "source": "www.rednote.com",
                    "source_platform": "xhs",
                    "collected_at": str(collected_at)[:40],
                    "region": raw.get("region", "intl") if isinstance(raw, dict) else "intl",
                    "detail_media_mode": (
                        raw.get("detail_media_mode")
                        if isinstance(raw.get("detail_media_mode"), str)
                        and raw.get("detail_media_mode") in {"legacy", "cover_only"}
                        else effective_detail_media_mode
                    ),
                    "detail_media_mode_requested": detail_media_mode,
                    "detail_media_mode_effective": effective_detail_media_mode,
                    "detail_media_mode_reason": detail_media_mode_reason,
                    "partial": bool(raw.get("partial")),
                    "pending_note_ids": pending_note_ids,
                    "pagination_exhausted": False,
                    "continuation_required": continuation_required,
                    "continuation": {
                        "keyword": keyword,
                        "source_host": "www.rednote.com",
                        "identity_verified": checkpoint_identity_verified,
                        "partial": bool(raw.get("partial")),
                        "pending_note_ids": pending_note_ids,
                        "pagination_exhausted": False,
                        "continuation_required": continuation_required,
                        "checkpoint_complete": checkpoint_complete,
                        "checkpoint_run_id": (
                            continuation_snapshot.get("run_id")
                            if continuation_snapshot is not None
                            else (raw.get("checkpoint") or {}).get("run_id")
                        ),
                        "captured_at": captured_at,
                    },
                    "continuation_persisted": continuation_persisted,
                    "checkpoint_complete": checkpoint_complete,
                    "checkpoint_identity_verified": checkpoint_identity_verified,
                    "checkpoint_run_id": (
                        continuation_snapshot.get("run_id")
                        if continuation_snapshot is not None
                        else (raw.get("checkpoint") or {}).get("run_id")
                    ),
                    "captured_at": captured_at,
                    **({"error_type": status.value, "detail": failure_detail}
                       if failure_detail is not None else {}),
                },
            )
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="现有小红书采集 Worker 暂不可用",
                metadata={
                    "provider": "existing_xhs_collector",
                    "source": "www.rednote.com",
                    "source_platform": "xhs",
                    "collected_at": datetime.datetime.now().isoformat(timespec="seconds"),
                    "error_type": type(exc).__name__,
                },
            )

    def _failed_result(self, error_code: str, *, items: Optional[list[dict[str, Any]]] = None,
                       pending_note_ids: Optional[list[str]] = None,
                       continuation_required: bool = False) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            items=items or [],
            raw_count=len(items or []),
            new_count=len(items or []),
            message="现有小红书采集链未能完成本次请求",
            metadata={
                "provider": "existing_xhs_collector",
                "source": "www.rednote.com",
                "source_platform": "xhs",
                "collected_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "error_type": error_code,
                "partial": bool(items),
                "pagination_exhausted": False,
                "pending_note_ids": pending_note_ids or [],
                "continuation_required": continuation_required,
                "continuation_persisted": False if continuation_required else None,
            },
        )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NOT_SUPPORTED,
            platform=self.platform,
            message=(
                "现有香港/国际小红书搜索链会在采集时读取详情；独立详情读取接口尚未接入。"
            ),
            metadata={"content_id": content_id},
        )

    def health_check(self, **kwargs: Any) -> CollectionResult:
        try:
            backend = self._load_backend()
            region = kwargs.get("region") or "intl"
            account = kwargs.get("account")
            policy_gate = getattr(backend, "_collection_policy_gate", None)
            if not callable(policy_gate):
                return CollectionResult(
                    status=CollectionStatus.NOT_CONFIGURED,
                    platform=self.platform,
                    message="小红书生产身份策略不可用",
                    metadata={"provider": "authorized_browser_worker",
                              "endpoint_configured": False,
                              "healthcheck_scope": "configuration_only",
                              "error_type": "policy_unavailable"},
                )
            gate = policy_gate(region=region, account=account)
            if not gate.get("ok"):
                return CollectionResult(
                    status=CollectionStatus.NOT_CONFIGURED,
                    platform=self.platform,
                    message="小红书生产身份或区域策略拒绝当前健康检查",
                    metadata={"provider": "authorized_browser_worker",
                              "endpoint_configured": False,
                              "healthcheck_scope": "configuration_only",
                              "error_type": str(gate.get("code") or "policy_blocked")},
                )
            resolve_endpoint = getattr(backend, "_resolve_server_cdp_url", None)
            if not callable(resolve_endpoint):
                return CollectionResult(
                    status=CollectionStatus.NOT_CONFIGURED,
                    platform=self.platform,
                    message="小红书远程授权 Worker 未提供配置检查",
                    metadata={"provider": "authorized_browser_worker", "endpoint_configured": False,
                              "healthcheck_scope": "configuration_only"},
                )
            selected_account = gate.get("account") or account
            selected_region = gate.get("region") or region
            cdp_url, endpoint_error = resolve_endpoint(
                account=selected_account, region=selected_region)
            if endpoint_error:
                status = (
                    CollectionStatus.NOT_CONFIGURED
                    if endpoint_error in {"COLLECTOR_ENDPOINT_NOT_CONFIGURED", "COLLECTOR_ENDPOINT_INVALID",
                                          "LOCAL_COLLECTOR_ENDPOINT_FORBIDDEN", "POLICY_BLOCKED"}
                    else CollectionStatus.PROVIDER_UNAVAILABLE
                )
                return CollectionResult(
                    status=status,
                    platform=self.platform,
                    message="小红书远程授权 Worker 未配置或配置不可用",
                    metadata={"provider": "authorized_browser_worker", "endpoint_configured": False,
                              "healthcheck_scope": "configuration_only", "error_type": endpoint_error},
                )
            cdp = getattr(backend, "_cdp_online", None)
            if callable(cdp):
                ok = bool(cdp(timeout=float(kwargs.get("timeout", 2)), cdp_url=cdp_url,
                              account=selected_account, region=selected_region))
                return CollectionResult(
                    status=CollectionStatus.NEED_VERIFY if ok else CollectionStatus.PROVIDER_UNAVAILABLE,
                    platform=self.platform,
                    message="远程 Worker 可达，平台登录态需由本次人工请求验证" if ok else "远程 Worker 不可达",
                    metadata={"provider": "authorized_browser_worker", "source": "www.rednote.com",
                              "endpoint_configured": True,
                              "healthcheck_scope": "worker_connectivity",
                              "session_state": "worker_reachable_unverified" if ok else "worker_unavailable"},
                )
            return CollectionResult(
                status=CollectionStatus.NOT_CONFIGURED,
                platform=self.platform,
                message="小红书远程授权 Worker 缺少连通性探针",
                metadata={"provider": "authorized_browser_worker", "endpoint_configured": True,
                          "healthcheck_scope": "configuration_only"},
            )
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.PROVIDER_UNAVAILABLE,
                platform=self.platform,
                message="小红书远程授权 Worker 健康检查失败",
                metadata={"provider": "authorized_browser_worker", "error_type": type(exc).__name__,
                          "healthcheck_scope": "worker_connectivity"},
            )


register_adapter("xhs", XiaohongshuAdapter)
