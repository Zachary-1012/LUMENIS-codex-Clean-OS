from __future__ import annotations

import datetime
from typing import Any, Callable, Optional

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .config import PLATFORM_CAPABILITIES
from .registry import register_adapter


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
            backend = self._load_backend()
            fn = getattr(backend, "search_xiaohongshu")
            raw = fn(
                keyword,
                max_scroll=int(kwargs.get("max_scroll", 4)),
                output_path=kwargs.get("output_path"),
                max_details=int(kwargs.get("max_details", 10)),
            )
            notes = raw.get("notes", []) if isinstance(raw, dict) else []
            error = raw.get("error", "") if isinstance(raw, dict) else ""
            error_code = str(error or "").strip().upper()
            if error_code == "IP_RISK_OR_300012":
                status = CollectionStatus.RISK_WARNING
            elif error_code == "NEED_VERIFY":
                status = CollectionStatus.NEED_VERIFY
            elif error_code in {
                "COLLECTOR_ENDPOINT_NOT_CONFIGURED",
                "COLLECTOR_ENDPOINT_INVALID",
                "LOCAL_COLLECTOR_ENDPOINT_FORBIDDEN",
            }:
                status = CollectionStatus.NOT_CONFIGURED
            elif error_code in {
                "COLLECTOR_ENDPOINT_UNAVAILABLE",
                "COLLECTOR_SCRIPT_UNAVAILABLE",
                "CDP_EMPTY_OR_LOAD_FAILED",
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
                CollectionStatus.COLLECT_ERROR: "现有小红书采集链未能完成本次请求",
            }
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
                    **({"error_type": status.value} if status not in {CollectionStatus.SUCCESS, CollectionStatus.NO_NEW_DATA} else {}),
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
            resolve_endpoint = getattr(backend, "_resolve_server_cdp_url", None)
            if not callable(resolve_endpoint):
                return CollectionResult(
                    status=CollectionStatus.NOT_CONFIGURED,
                    platform=self.platform,
                    message="小红书远程授权 Worker 未提供配置检查",
                    metadata={"provider": "authorized_browser_worker", "endpoint_configured": False,
                              "healthcheck_scope": "configuration_only"},
                )
            cdp_url, endpoint_error = resolve_endpoint()
            if endpoint_error:
                status = (
                    CollectionStatus.NOT_CONFIGURED
                    if endpoint_error in {"COLLECTOR_ENDPOINT_NOT_CONFIGURED", "COLLECTOR_ENDPOINT_INVALID",
                                          "LOCAL_COLLECTOR_ENDPOINT_FORBIDDEN"}
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
                ok = bool(cdp(timeout=float(kwargs.get("timeout", 2)), cdp_url=cdp_url))
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
