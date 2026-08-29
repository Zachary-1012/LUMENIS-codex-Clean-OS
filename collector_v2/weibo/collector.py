"""
微博采集器 V2
继承PlatformCollector基类
通过浏览器登录态采集微博搜索结果
不占用小红书采集次数
"""
import os
import re
import asyncio
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta

from ..base import PlatformCollector, RawNote, RawComment


class WeiboCollector(PlatformCollector):
    """微博采集器"""
    
    SEARCH_URL = "https://s.weibo.com/weibo"
    
    def __init__(self, cookie: str = "", config: Optional[Dict] = None):
        super().__init__(config)
        self.cookie = cookie
        self.platform = "weibo"
        self._browser = None
        self._page = None
    
    async def search(self, keyword: str, page: int = 1, 
                     max_scroll: int = 2) -> List[RawNote]:
        """
        搜索微博
        keyword: 搜索关键词
        page: 页码
        max_scroll: 最大页数（微博每页约20条）
        """
        all_notes = []
        
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                
                if self.cookie:
                    cookies = self._parse_cookie(self.cookie)
                    await context.add_cookies(cookies)
                
                page_obj = await context.new_page()
                
                for current_page in range(1, max_scroll + 1):
                    try:
                        url = f"{self.SEARCH_URL}?q={keyword}&page={current_page}"
                        await page_obj.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(2)
                        
                        content = await page_obj.content()
                        if "登录" in content and "weibo.com/login" in content:
                            print(f"[WeiboCollector] 未登录，无法采集关键词: {keyword}")
                            break
                        
                        notes = await self._parse_search_page(page_obj, keyword)
                        all_notes.extend(notes)
                        
                        next_btn = await page_obj.query_selector('.next')
                        if not next_btn:
                            break
                            
                    except Exception as e:
                        print(f"[WeiboCollector] 第{current_page}页采集失败: {e}")
                        break
                
                await browser.close()
                
        except ImportError:
            print("[WeiboCollector] playwright未安装，无法使用浏览器采集")
        except Exception as e:
            print(f"[WeiboCollector] 采集异常: {e}")
        
        self._is_logged_in = len(all_notes) > 0
        print(f"[WeiboCollector] 关键词'{keyword}'采集到{len(all_notes)}条微博")
        return all_notes
    
    def _parse_cookie(self, cookie_str: str) -> List[Dict]:
        """解析Cookie字符串为playwright格式"""
        cookies = []
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.weibo.com',
                    'path': '/'
                })
        return cookies
    
    async def _parse_search_page(self, page, keyword: str) -> List[RawNote]:
        """解析微博搜索结果页"""
        notes = []
        try:
            cards = await page.query_selector_all('.card-wrap')
            for card in cards:
                try:
                    note = await self._parse_card(card, keyword)
                    if note:
                        notes.append(note)
                except:
                    continue
        except Exception as e:
            print(f"[WeiboCollector] 解析页面失败: {e}")
        return notes
    
    async def _parse_card(self, card, keyword: str) -> Optional[RawNote]:
        """解析单条微博卡片"""
        try:
            mid = await card.get_attribute('mid')
            if not mid:
                return None
            
            content_el = await card.query_selector('.txt')
            content = ""
            title = ""
            if content_el:
                content = await content_el.inner_text()
                title = content[:30].replace('\n', ' ')
            
            author_el = await card.query_selector('.name')
            author_id = ""
            author_nickname = ""
            if author_el:
                author_nickname = await author_el.inner_text()
                href = await author_el.get_attribute('href')
                if href:
                    match = re.search(r'/(\d+)/', href)
                    if match:
                        author_id = match.group(1)
            
            time_el = await card.query_selector('.from a')
            publish_date = ""
            if time_el:
                time_text = await time_el.inner_text()
                publish_date = self._parse_weibo_time(time_text)
            
            likes = comments = shares = 0
            
            like_el = await card.query_selector('.card-act ul li:nth-child(4) a')
            if like_el:
                likes = self._parse_count(await like_el.inner_text())
            
            comment_el = await card.query_selector('.card-act ul li:nth-child(3) a')
            if comment_el:
                comments = self._parse_count(await comment_el.inner_text())
            
            share_el = await card.query_selector('.card-act ul li:nth-child(2) a')
            if share_el:
                shares = self._parse_count(await share_el.inner_text())
            
            url = f"https://weibo.com/{author_id}/{mid}" if author_id else f"https://weibo.com/{mid}"
            
            return RawNote(
                note_id=f"weibo_{mid}",
                title=title,
                content=content,
                author_id=author_id,
                author_nickname=author_nickname,
                likes=likes,
                comments=comments,
                collects=0,
                shares=shares,
                publish_date=publish_date,
                url=url,
                xsec_token="",
                source_platform=self.platform,
                raw_data={'keyword': keyword, 'mid': mid}
            )
        except:
            return None
    
    def _parse_weibo_time(self, time_str: str) -> str:
        """解析微博时间格式"""
        now = datetime.now()
        if '分钟前' in time_str:
            try:
                minutes = int(re.search(r'(\d+)', time_str).group())
                return (now - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
            except: pass
        elif '小时前' in time_str:
            try:
                hours = int(re.search(r'(\d+)', time_str).group())
                return (now - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            except: pass
        elif '昨天' in time_str:
            return (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        elif '前天' in time_str:
            return (now - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', time_str)
        if match:
            return match.group(0)
        match = re.search(r'(\d{2})月(\d{2})日', time_str)
        if match:
            month, day = match.groups()
            return f"{now.year}-{month}-{day}"
        return now.strftime('%Y-%m-%d %H:%M:%S')
    
    def _parse_count(self, text: str) -> int:
        """解析互动量"""
        text = text.strip()
        if not text or text in ('赞', '评论', '转发'):
            return 0
        if '万' in text:
            try:
                num = float(re.sub(r'[^\d.]', '', text))
                return int(num * 10000)
            except: return 0
        try:
            return int(re.sub(r'[^\d]', '', text))
        except: return 0
    
    async def get_detail(self, note_id: str, xsec_token: str = "") -> Optional[RawNote]:
        """获取微博详情（搜索结果已有正文，一般不需要）"""
        return None
    
    async def get_comments(self, note_id: str, xsec_token: str = "",
                            cursor: str = "") -> tuple:
        """获取微博评论（单页）"""
        return [], False, ""
    
    async def check_login(self) -> bool:
        """检查微博登录状态"""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                if self.cookie:
                    await context.add_cookies(self._parse_cookie(self.cookie))
                page = await context.new_page()
                await page.goto("https://weibo.com", wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
                content = await page.content()
                self._is_logged_in = "登录" not in content or "我的首页" in content
                await browser.close()
                return self._is_logged_in
        except:
            self._is_logged_in = False
            return False
    
    def update_cookie(self, cookie: str):
        """更新Cookie"""
        self.cookie = cookie
    
    async def close(self):
        """关闭采集器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
