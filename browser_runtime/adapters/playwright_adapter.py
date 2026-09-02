# -*- coding: utf-8 -*-
"""Zachary OS AI · Playwright Adapter（确定性浏览器执行 Provider）
对齐 CTR-BROWSER-RUNTIME-P0-01 P0-BR-10：Playwright 属于 P0，优先用于确定性执行。
本 Adapter 最小封装 Playwright 1.62，遵循 BrowserContract 接口 + BEEP 协议。

能力：navigate / snapshot(accessibility) / screenshot / click / type_text / get_text / wait_for / evaluate / health
红线：不包含 ZBC 业务规则；不读写 Cookie/Token/密钥。
"""
from __future__ import annotations
import os
import tempfile
from typing import Any, Optional

from ..contract import BrowserContract, BEEPExecutor


class PlaywrightAdapter(BrowserContract):
    """Playwright 确定性浏览器 Adapter（headless 默认，可配置 headful）。"""

    NAME = "playwright"

    def __init__(self, headless: bool = True, browser_type: str = "chromium",
                 timeout_ms: int = 15000, **kw):
        self.headless = headless
        self.browser_type = browser_type
        self.timeout_ms = timeout_ms
        self.beep = BEEPExecutor()
        self._pw = None
        self._browser = None
        self._page = None
        self._load_error = None
        self._lazy_init()

    def _lazy_init(self):
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            launcher = getattr(self._pw, self.browser_type)
            self._browser = launcher.launch(headless=self.headless)
            self._page = self._browser.new_page()
            self._page.set_default_timeout(self.timeout_ms)
        except Exception as e:
            self._load_error = str(e)

    def _require(self):
        if self._page is None:
            raise RuntimeError(f"playwright not available: {self._load_error}")

    # ---------- BrowserContract 实现 ----------
    def navigate(self, url: str, **kw) -> dict:
        self._require()
        self._page.goto(url, wait_until="domcontentloaded")
        return {"ok": True, "url": self._page.url, "title": self._page.title()}

    def snapshot(self, **kw) -> dict:
        self._require()
        try:
            # Accessibility Snapshot（确定性）
            snap = self._page.accessibility.snapshot()
        except Exception:
            snap = None
        return {"url": self._page.url, "title": self._page.title(), "accessibility": snap}

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
            return {"ok": False, "error": str(e)[:300]}

    def type_text(self, selector: str, text: str, **kw) -> dict:
        self._require()
        try:
            self._page.wait_for_selector(selector, timeout=self.timeout_ms)
            self._page.fill(selector, text)
            return {"ok": True, "selector": selector}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    def get_text(self, selector: str, **kw) -> str:
        self._require()
        try:
            return self._page.inner_text(selector)
        except Exception:
            return ""

    def wait_for(self, selector: str, timeout: int = 10, **kw) -> bool:
        self._require()
        try:
            self._page.wait_for_selector(selector, timeout=timeout * 1000)
            return True
        except Exception:
            return False

    def evaluate(self, js: str, **kw) -> Any:
        self._require()
        return self._page.evaluate(js)

    def health(self) -> dict:
        if self._page is None:
            return {"status": "down", "error": self._load_error}
        try:
            return {"status": "up", "url": self._page.url, "title": self._page.title()}
        except Exception as e:
            return {"status": "degraded", "error": str(e)[:200]}

    def close(self, **kw) -> None:
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