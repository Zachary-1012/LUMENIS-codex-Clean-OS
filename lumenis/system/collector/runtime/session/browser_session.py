"""
BrowserSession - 可运行的 Playwright 会话管理。
支持：
1) CDP 连接到用户已经打开的浏览器（推荐，复用真实登录态）
2) 独立持久化 Chromium（开发/备用）
不负责主体过滤。
"""
import os
from dataclasses import dataclass
from typing import Dict, Optional
from playwright.sync_api import sync_playwright

@dataclass
class SessionConfig:
    headless: bool = False
    user_data_dir: str = ''
    cdp_url: str = ''
    viewport_width: int = 1440
    viewport_height: int = 900
    timeout: int = 30000
    locale: str = 'zh-CN'

class BrowserSession:
    def __init__(self, config: SessionConfig = None, instance_name: str = 'taikoo'):
        self.config = config or SessionConfig()
        self.instance_name = instance_name
        self._pw = None
        self._browser = None
        self._context = None
        self._pages = []
        self._started = False

    def start(self):
        if self._started:
            return self
        self._pw = sync_playwright().start()
        if self.config.cdp_url:
            self._browser = self._pw.chromium.connect_over_cdp(self.config.cdp_url, timeout=self.config.timeout)
            contexts = self._browser.contexts
            if not contexts:
                raise RuntimeError('CDP 已连接，但没有可用 BrowserContext')
            self._context = contexts[0]
        else:
            if not self.config.user_data_dir:
                raise RuntimeError('未设置 user_data_dir，且未提供 cdp_url')
            self._context = self._pw.chromium.launch_persistent_context(
                self.config.user_data_dir,
                headless=self.config.headless,
                viewport={'width': self.config.viewport_width, 'height': self.config.viewport_height},
                locale=self.config.locale,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled'],
            )
        self._context.set_default_timeout(self.config.timeout)
        self._started = True
        return self

    def new_page(self):
        self.start()
        page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._pages.append(page)
        return page

    def pages(self):
        self.start()
        return self._context.pages

    def get_cookies(self) -> Dict[str, str]:
        self.start()
        return {c['name']: c['value'] for c in self._context.cookies()}

    def check_login(self) -> bool:
        try:
            page = self.new_page()
            page.goto('https://www.xiaohongshu.com/', wait_until='domcontentloaded', timeout=self.config.timeout)
            page.wait_for_timeout(1500)
            return not bool(page.locator('#login-btn, .login-btn, [class*="login-btn"]').count())
        except Exception:
            return False

    def close(self):
        # CDP 模式下不要关闭用户浏览器，只断开 Playwright
        try:
            if self.config.cdp_url:
                self._browser = None
            elif self._context:
                self._context.close()
        finally:
            self._context = None
            self._pages = []
            self._started = False
            if self._pw:
                self._pw.stop()
            self._pw = None

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
