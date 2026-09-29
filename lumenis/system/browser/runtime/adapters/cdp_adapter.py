# -*- coding: utf-8 -*-
"""Zachary OS AI · CDP Adapter（对接 internal_browser，复用现有 CDP 驻场浏览器）
对齐 CTR-BROWSER-RUNTIME-P0-01：Browser Adapter 层。
本 Adapter **不修改** internal_browser.py 内部逻辑，仅做统一 BrowserContract 封装。

调用关系：BrowserContract → Router → CDPAdapter → internal_browser（Provider）
"""
from __future__ import annotations
import json
import time
from typing import Any, Optional

from ..contract import (
    BrowserContract,
    BEEPExecutor,
    browser_health_result,
    safe_browser_error,
    safe_browser_url,
)


class CDPAdapter(BrowserContract):
    """CDP 驻场浏览器 Adapter（默认 Provider，保持现有行为）。"""

    NAME = "cdp"
    ALLOWED_XHS_ACCOUNT = "XHS_RETINAUT"

    def __init__(self, account: Optional[str] = None, **kw):
        requested = str(account or "").strip().upper()
        self._account_allowed = requested in ("", "DEFAULT", self.ALLOWED_XHS_ACCOUNT)
        self.account = self.ALLOWED_XHS_ACCOUNT if self._account_allowed else None
        self.beep = BEEPExecutor()
        try:
            import internal_browser as ib
            self._ib = ib
        except Exception as e:
            self._ib = None
            self._load_error = str(e)

    # ---------- 内部校验 ----------
    def _require(self):
        if not self._account_allowed:
            raise RuntimeError("browser connection is unavailable")
        if self._ib is None:
            raise RuntimeError("browser provider is unavailable")

    # ---------- BrowserContract 实现 ----------
    def navigate(self, url: str, **kw) -> dict:
        self._require()
        try:
            result = self._ib.navigate(self.account, url)
        except Exception as e:
            raise RuntimeError(safe_browser_error(e)) from None
        if not isinstance(result, dict):
            return {"ok": False, "error": "The browser operation could not be confirmed."}
        return {
            "ok": result.get("ok") is True,
            "url": safe_browser_url(result.get("url")),
            "error": safe_browser_error(result.get("error")) if result.get("error") else None,
        }

    def snapshot(self, **kw) -> dict:
        self._require()
        try:
            result = self._ib.get_state(self.account)
        except Exception as e:
            raise RuntimeError(safe_browser_error(e)) from None
        if not isinstance(result, dict):
            return {"online": False, "page_count": 0}
        return {
            "online": result.get("online") is True,
            "page_count": result.get("page_count", 0),
            "url": safe_browser_url(result.get("url")),
            "title": result.get("title", ""),
        }

    def screenshot(self, path: Optional[str] = None, **kw) -> dict:
        self._require()
        return self._ib.capture_screenshot(self.account, **{k: v for k, v in kw.items() if k in ("quality",)})

    def click(self, selector: str, **kw) -> dict:
        """点击（BEEP 化）：内部实现仅支持坐标点击，selector 需解析。"""
        self._require()
        # 若传入坐标则直接走 CDP click_at
        x = kw.get("x"); y = kw.get("y")
        if x is not None and y is not None:
            return self._ib.click_at(self.account, float(x), float(y))
        return {"ok": False, "error": "cdp_adapter.click requires x/y coordinates"}

    def type_text(self, selector: str, text: str, **kw) -> dict:
        self._require()
        return self._ib.type_text(self.account, text)

    def get_text(self, selector: str, **kw) -> str:
        self._require()
        r = self._ib.evaluate(self.account, f"document.querySelector({selector!r})?.innerText || ''")
        return str(r.get("result", {}).get("value", "")) if isinstance(r, dict) else ""

    def wait_for(self, selector: str, timeout: int = 10, **kw) -> bool:
        self._require()
        """Poll the current document with a bounded local CDP check."""
        try:
            timeout_seconds = max(0.0, min(float(timeout), 10.0))
        except (TypeError, ValueError):
            timeout_seconds = 0.0
        deadline = time.monotonic() + timeout_seconds
        expression = f"Boolean(document.querySelector({json.dumps(selector)}) )"
        while True:
            try:
                result = self._ib.evaluate(self.account, expression)
            except Exception as e:
                raise RuntimeError(safe_browser_error(e)) from None
            if not isinstance(result, dict) or result.get("ok") is not True:
                raise RuntimeError("The browser page could not be checked.")
            if result.get("value") is True:
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(0.5, remaining))

    def evaluate(self, js: str, **kw) -> Any:
        self._require()
        return self._ib.evaluate(self.account, js)

    def health(self) -> dict:
        if not self._account_allowed:
            return browser_health_result(
                "cdp", "unavailable", error_code="account_not_allowed"
            )
        if self._ib is None:
            return browser_health_result(
                "cdp", "unavailable", error=getattr(self, "_load_error", None),
                error_code="dependency_unavailable",
            )
        try:
            result = self._ib.get_state(self.account)
        except Exception as e:
            return browser_health_result("cdp", "unavailable", error=e)
        if not isinstance(result, dict):
            return browser_health_result("cdp", "unavailable")
        if result.get("online") is True:
            return browser_health_result("cdp", "connected")
        return browser_health_result(
            "cdp", "unavailable", error=result.get("error"),
            error_code="browser_unavailable",
        )

    def close(self, **kw) -> None:
        return None
