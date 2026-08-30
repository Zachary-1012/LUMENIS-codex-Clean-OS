from __future__ import annotations

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
            if error in {"IP_RISK_OR_300012", "NEED_VERIFY"}:
                status = CollectionStatus.RISK_WARNING if error == "IP_RISK_OR_300012" else CollectionStatus.NEED_VERIFY
            elif error:
                status = CollectionStatus.COLLECT_ERROR
            elif notes:
                status = CollectionStatus.SUCCESS
            else:
                status = CollectionStatus.NO_NEW_DATA
            return CollectionResult(
                status=status,
                platform=self.platform,
                items=notes,
                raw_count=int(raw.get("total", len(notes))) if isinstance(raw, dict) else len(notes),
                new_count=len(notes),
                message=error,
                metadata={"channel": raw.get("channel") if isinstance(raw, dict) else None},
            )
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=str(exc),
            )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message=(
                "Detail retrieval remains delegated to the existing XHS detail path. "
                "Wire that path here only after its current regression contract is verified."
            ),
            metadata={"content_id": content_id},
        )

    def health_check(self, **kwargs: Any) -> CollectionResult:
        try:
            backend = self._load_backend()
            cdp = getattr(backend, "_cdp_online", None)
            if callable(cdp):
                ok = bool(cdp(timeout=float(kwargs.get("timeout", 2))))
                return CollectionResult(
                    status=CollectionStatus.SUCCESS if ok else CollectionStatus.SESSION_EXPIRED,
                    platform=self.platform,
                    message="XHS CDP online" if ok else "XHS CDP offline",
                )
            return super().health_check(**kwargs)
        except Exception as exc:
            return CollectionResult(
                status=CollectionStatus.COLLECT_ERROR,
                platform=self.platform,
                message=str(exc),
            )


register_adapter("xhs", XiaohongshuAdapter)
