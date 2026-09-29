# -*- coding: utf-8 -*-
"""Zachary OS AI · Playwright Adapter（确定性浏览器执行 Provider）
对齐 CTR-BROWSER-RUNTIME-P0-01 P0-BR-10：Playwright 属于 P0，优先用于确定性执行。
本 Adapter 最小封装 Playwright 1.62，遵循 BrowserContract 接口 + BEEP 协议。

能力：navigate / snapshot(accessibility) / screenshot / click / type_text / get_text / wait_for / evaluate / health
红线：不包含 ZBC 业务规则；不读写 Cookie/Token/密钥。
"""
from __future__ import annotations
import ipaddress
import os
import tempfile
from typing import Any, Optional
from urllib.parse import urlsplit

from ..contract import (
    BrowserContract,
    BEEPExecutor,
    browser_health_result,
    safe_browser_error,
    safe_browser_url,
)

_BLOCKED_CDP_PORTS = frozenset({9222})


def _validate_cdp_url(value: str) -> None:
    """CDP grants full control of a browser, so only local endpoints are valid."""
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        is_loopback = host == "localhost" or ipaddress.ip_address(host).is_loopback
        valid_scheme = parsed.scheme.lower() in ("http", "https", "ws", "wss")
        has_credentials = bool(parsed.username or parsed.password or parsed.query or parsed.fragment)
        port = parsed.port
        if (
            not valid_scheme
            or not is_loopback
            or has_credentials
            or port in _BLOCKED_CDP_PORTS
        ):
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("CDP endpoint must be a local loopback URL without embedded credentials") from None


class PlaywrightAdapter(BrowserContract):
    """Playwright 确定性浏览器 Adapter（headless 默认，可配置 headful）。"""

    NAME = "playwright"

    def __init__(self, headless: bool = True, browser_type: str = "chromium",
                 timeout_ms: int = 15000,
                 user_data_dir: Optional[str] = None,
                 storage_state: Optional[str] = None,
                 cdp_url: Optional[str] = None,
                 **kw):
        """P0-BR-06 Session/Profile 隔离：user_data_dir 提供时用持久化 context，
        否则保持默认 launch()+new_page()。storage_state 可用于恢复登录态。
        cdp_url 提供时用 connect_over_cdp 连接已运行的 CDP 浏览器（接入生产采集链），
        不启动新浏览器，close() 只断开连接不关闭外部浏览器。
        默认行为不变，仅新增可选参数。"""
        self.headless = headless
        self.browser_type = browser_type
        self.timeout_ms = timeout_ms
        self.user_data_dir = user_data_dir
        self.storage_state = storage_state
        self.cdp_url = cdp_url
        self._cdp_connected = False
        self.beep = BEEPExecutor()
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._load_error = None
        self._load_error_type = None
        self._closed = False
        self._lazy_init()

    def _lazy_init(self):
        try:
            if self.cdp_url:
                if self.user_data_dir or self.storage_state:
                    raise ValueError("CDP connection cannot use a separate browser profile or storage state")
                _validate_cdp_url(self.cdp_url)
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            if self.cdp_url:
                # 接入生产采集链：connect_over_cdp 连接已运行的 CDP 浏览器
                self._browser = self._pw.chromium.connect_over_cdp(
                    self.cdp_url, timeout=self.timeout_ms
                )
                self._cdp_connected = True
                ctxs = self._browser.contexts
                self._context = ctxs[0] if ctxs else self._browser.new_context()
                pages = self._context.pages
                self._page = pages[0] if pages else self._context.new_page()
            else:
                launcher = getattr(self._pw, self.browser_type)
                if self.user_data_dir:
                    # P0-BR-06: 持久化 context，profile 隔离
                    self._context = launcher.launch_persistent_context(
                        user_data_dir=self.user_data_dir,
                        headless=self.headless,
                        storage_state=self.storage_state,
                    )
                    self._browser = None  # persistent context 自带 browser
                    self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
                else:
                    # 默认行为：launch + new_page（无 profile 隔离）
                    self._browser = launcher.launch(headless=self.headless)
                    self._context = self._browser.new_context(storage_state=self.storage_state)
                    self._page = self._context.new_page()
            self._page.set_default_timeout(self.timeout_ms)
        except Exception as e:
            self._load_error = e
            self._load_error_type = type(e).__name__
            self._cleanup_failed_init()

    def _cleanup_failed_init(self) -> None:
        """Release partially-created local resources without closing external contexts."""
        try:
            if self._context is not None and not self._cdp_connected:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser is not None:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass
        self._page = None
        self._context = None
        self._browser = None
        self._pw = None

    def _require(self):
        if self._page is None:
            raise RuntimeError("browser provider is unavailable")

    # ---------- BrowserContract 实现 ----------
    def navigate(self, url: str, **kw) -> dict:
        self._require()
        self._page.goto(url, wait_until="domcontentloaded")
        return {"ok": True, "url": safe_browser_url(self._page.url), "title": self._page.title()}

    def snapshot(self, **kw) -> dict:
        self._require()
        try:
            # Accessibility Snapshot（确定性）
            snap = self._page.accessibility.snapshot()
        except Exception:
            snap = None
        return {"url": safe_browser_url(self._page.url), "title": self._page.title(), "accessibility": snap}

    def screenshot(self, path: Optional[str] = None, **kw) -> dict:
        self._require()
        if path is None:
            path = os.path.join(tempfile.gettempdir(), f"browser_runtime_shot_{id(self)}.png")
        self._page.screenshot(path=path)
        return {"ok": True, "path": path}

    def click(self, selector: str, **kw) -> dict:
        """点击（BEEP：Locate→Confirm→Click→Observe→Verify）"""
        self._require()
        try:
            self._page.wait_for_selector(selector, timeout=self.timeout_ms)  # Locate/Confirm
            self._page.click(selector)  # Click
            return {"ok": True, "selector": selector}
        except Exception as e:
            return {"ok": False, "error": safe_browser_error(e)}

    def type_text(self, selector: str, text: str, **kw) -> dict:
        self._require()
        try:
            self._page.wait_for_selector(selector, timeout=self.timeout_ms)
            self._page.fill(selector, text)
            return {"ok": True, "selector": selector}
        except Exception as e:
            return {"ok": False, "error": safe_browser_error(e)}

    def get_text(self, selector: str, **kw) -> str:
        self._require()
        try:
            return self._page.inner_text(selector)
        except Exception as e:
            raise RuntimeError(safe_browser_error(e)) from None

    def wait_for(self, selector: str, timeout: int = 10, **kw) -> bool:
        self._require()
        try:
            self._page.wait_for_selector(selector, timeout=timeout * 1000)
            return True
        except Exception as e:
            if type(e).__name__ == "TimeoutError":
                return False
            raise RuntimeError(safe_browser_error(e)) from None

    def evaluate(self, js: str, **kw) -> Any:
        self._require()
        return self._page.evaluate(js)

    def health(self) -> dict:
        if self._closed:
            return browser_health_result(
                "playwright", "unavailable", error_code="adapter_closed"
            )
        if self._load_error is not None:
            code = "dependency_unavailable" if self._load_error_type in ("ImportError", "ModuleNotFoundError") else None
            return browser_health_result(
                "playwright", "unavailable", error=self._load_error, error_code=code
            )
        if self._page is None or self._context is None:
            return browser_health_result("playwright", "unavailable")
        try:
            browser = self._browser
            if browser is None:
                get_browser = getattr(self._context, "browser", None)
                browser = get_browser() if callable(get_browser) else None
            is_connected = getattr(browser, "is_connected", None)
            if callable(is_connected) and not is_connected():
                return browser_health_result("playwright", "disconnected")
            is_closed = getattr(self._page, "is_closed", None)
            if callable(is_closed) and is_closed():
                return browser_health_result(
                    "playwright", "degraded", error_code="page_unavailable"
                )
            return browser_health_result("playwright", "connected")
        except Exception as e:
            return browser_health_result("playwright", "degraded", error=e)

    def close(self, **kw) -> None:
        if self._closed:
            return None
        self._closed = True
        try:
            if self._context is not None and not self._cdp_connected:
                # cdp 连接时不关闭外部 context（属于外部浏览器）
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser is not None:
                if self._cdp_connected:
                    # cdp 连接时只断开，不关闭外部浏览器
                    self._browser.close()  # disconnect
                else:
                    self._browser.close()
        except Exception:
            pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass
