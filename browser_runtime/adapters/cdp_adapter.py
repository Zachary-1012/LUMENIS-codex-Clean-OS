# -*- coding: utf-8 -*-
"""Zachary OS AI · CDP Adapter（对接 internal_browser，复用现有 CDP 驻场浏览器）
对齐 CTR-BROWSER-RUNTIME-P0-01：Browser Adapter 层。
本 Adapter **不修改** internal_browser.py 内部逻辑，仅做统一 BrowserContract 封装。

调用关系：BrowserContract → Router → CDPAdapter → internal_browser（Provider）
"""
from __future__ import annotations
from typing import Any, Optional

from ..contract import BrowserContract, BEEPExecutor


class CDPAdapter(BrowserContract):
    """CDP 驻场浏览器 Adapter（默认 Provider，保持现有行为）。"""

    NAME = "cdp"

    def __init__(self, account: Optional[str] = None, **kw):
        self.account = account
        self.beep = BEEPExecutor()
        try:
            import internal_browser as ib
            self._ib = ib
        except Exception as e:
            self._ib = None
            self._load_error = str(e)

    # ---------- 内部校验 ----------
    def _require(self):
        if self._ib is None:
            raise RuntimeError(f"internal_browser not importable: {getattr(self, '_load_error', '?')}")

    # ---------- BrowserContract 实现 ----------
    def navigate(self, url: str, **kw) -> dict:
        self._require()
        return self._ib.navigate(self.account, url)

    def snapshot(self, **kw) -> dict:
        self._require()
        return self._ib.get_state(self.account)

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
        return True  # CDP 层不阻塞等待，由上层 BEEP verify 保证

    def evaluate(self, js: str, **kw) -> Any:
        self._require()
        return self._ib.evaluate(self.account, js)

    def health(self) -> dict:
        self._require()
        return self._ib.get_state(self.account)

    def close(self, **kw) -> None:
        return None