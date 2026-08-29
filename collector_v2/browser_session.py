"""
BrowserSession - 浏览器会话独立管理
不耦合采集逻辑，只负责浏览器启动、登录、Cookie管理
采集器不负责登录管理
"""
import os
import json
import asyncio
from typing import Optional, Dict, List
from datetime import datetime


class BrowserSession:
    """浏览器会话管理"""
    
    def __init__(self, 
                 user_data_dir: Optional[str] = None,
                 headless: bool = True,
                 cdp_port: int = 9222,
                 platform: str = "xhs"):
        self.user_data_dir = user_data_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "browser_profiles", platform
        )
        self.headless = headless
        self.cdp_port = cdp_port
        self.platform = platform
        self._browser = None
        self._context = None
        self._page = None
        self._cookies: List[Dict] = []
        self._is_running = False
    
    async def start(self):
        """启动浏览器"""
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            
            # 检查是否有CDP连接
            try:
                self._browser = await self._playwright.chromium.connect_over_cdp(
                    f"http://127.0.0.1:{self.cdp_port}"
                )
                print(f"[BrowserSession] 已连接CDP端口 {self.cdp_port}")
            except:
                # 没有CDP，启动新浏览器
                os.makedirs(self.user_data_dir, exist_ok=True)
                self._browser = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                    ]
                )
                print(f"[BrowserSession] 已启动新浏览器")
            
            self._is_running = True
            return True
        except Exception as e:
            print(f"[BrowserSession] 启动失败: {e}")
            return False
    
    async def new_page(self):
        """创建新页面"""
        if not self._browser:
            await self.start()
        
        if hasattr(self._browser, 'new_page'):
            self._page = await self._browser.new_page()
        else:
            # CDP连接的browser可能需要从context创建
            contexts = self._browser.contexts
            if contexts:
                self._page = await contexts[0].new_page()
            else:
                self._page = await self._browser.new_page()
        return self._page
    
    async def get_page(self):
        """获取当前页面，没有则创建"""
        if not self._page or self._page.is_closed():
            await self.new_page()
        return self._page
    
    async def check_login(self, check_url: str, check_selector: str) -> bool:
        """
        检查登录状态
        check_url: 登录后才能访问的URL
        check_selector: 登录成功后才存在的CSS选择器
        """
        try:
            page = await self.get_page()
            await page.goto(check_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            element = await page.query_selector(check_selector)
            self._is_logged_in = element is not None
            return self._is_logged_in
        except Exception as e:
            print(f"[BrowserSession] 登录检查失败: {e}")
            return False
    
    async def get_cookies(self) -> List[Dict]:
        """获取当前Cookie"""
        if self._page:
            self._cookies = await self._page.context.cookies()
        return self._cookies
    
    async def get_cookie_header(self) -> str:
        """获取Cookie请求头字符串"""
        cookies = await self.get_cookies()
        return "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    
    async def save_cookies(self, path: Optional[str] = None):
        """保存Cookie到文件"""
        if not path:
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "private", f"{self.platform}_cookies.json"
            )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        cookies = await self.get_cookies()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"[BrowserSession] Cookie已保存到 {path}")
    
    async def load_cookies(self, path: Optional[str] = None) -> bool:
        """从文件加载Cookie"""
        if not path:
            path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "private", f"{self.platform}_cookies.json"
            )
        if not os.path.exists(path):
            return False
        try:
            with open(path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            page = await self.get_page()
            await page.context.add_cookies(cookies)
            self._cookies = cookies
            print(f"[BrowserSession] Cookie已从 {path} 加载")
            return True
        except Exception as e:
            print(f"[BrowserSession] Cookie加载失败: {e}")
            return False
    
    async def close(self):
        """关闭浏览器"""
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
            if self._browser:
                await self._browser.close()
            if hasattr(self, '_playwright') and self._playwright:
                await self._playwright.stop()
        except Exception as e:
            print(f"[BrowserSession] 关闭失败: {e}")
        finally:
            self._is_running = False
            self._page = None
            self._browser = None
