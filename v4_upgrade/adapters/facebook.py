# -*- coding: utf-8 -*-
"""
Facebook 内容采集适配器
------------------------
定位：服务于 Z-Brand Core 多平台内容采集。
浏览器 CDP 采集 Facebook 搜索结果，薄封装为 v4 BaseAdapter 契约，
接入熔断器/限流/重试/降级体系。

数据主路径：Facebook 搜索页（浏览器渲染）
  https://www.facebook.com/search/top?q={keyword}
需代理 + 登录态 cookie。

状态映射：
  - 有结果       → SUCCESS
  - 正常空       → success=True, notes=[]
  - 登录失效     → SESSION_EXPIRED 语义
  - 异常         → COLLECT_ERROR

只读红线：不点赞、不评论、不关注、不私信、不发布、不执行任何账号写操作。
"""
import re
import logging
from datetime import datetime, timezone

from .base import BaseAdapter, AdapterResult, CollectedNote

logger = logging.getLogger(__name__)


class FacebookAdapter(BaseAdapter):
    """Facebook 搜索适配器（浏览器 CDP + cookie，只读采集）"""

    platform_name = "facebook"
    platform_display = "Facebook"

    _DEFAULT_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, cookie_string: str = "", **kwargs):
        super().__init__(**kwargs)
        self._cookie_string = cookie_string
        if not self._cookie_string:
            self._cookie_string = self._auto_load_cookie()

    @staticmethod
    def _auto_load_cookie() -> str:
        """从 data/cookies/facebook.json 自动加载 cookie 字符串。"""
        try:
            import json as _json
            from pathlib import Path
            p = Path(__file__).parent.parent.parent / "data" / "cookies" / "facebook.json"
            if not p.exists():
                return ""
            raw = _json.loads(p.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return "; ".join(f"{c['name']}={c['value']}" for c in raw if "name" in c)
            if isinstance(raw, dict):
                cookies = raw.get("cookies", raw)
                if isinstance(cookies, list):
                    return "; ".join(f"{c['name']}={c['value']}" for c in cookies if "name" in c)
                if isinstance(cookies, dict):
                    return "; ".join(f"{k}={v}" for k, v in cookies.items())
            return ""
        except Exception:
            return ""

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        return self._search_browser(keyword, max_results)

    def _search_browser(self, keyword: str, max_results: int) -> AdapterResult:
        """浏览器 CDP 采集 Facebook 搜索结果。"""
        try:
            from .human_browser import HumanBrowser
            from .cookie_vault import inject_into_context
            from urllib.parse import quote

            hb = HumanBrowser(port=9222, launch_url="about:blank")
            hb.connect()
            inject_into_context(hb._context, "facebook")
            page = hb.new_page()
            url = f"https://www.facebook.com/search/top?q={quote(keyword.strip())}"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            hb.pause(5.0, 5.0)

            # 检测登录态
            page_text = page.content()
            if "login" in page.url.lower() or "signin" in page.url.lower():
                page.close()
                hb.close()
                return AdapterResult(success=False, error="Facebook 登录态失效，请更新 cookie 或重新登录")

            # 解析搜索结果（Facebook 使用 div[role="article"]）
            cards = page.query_selector_all('div[role="article"]')
            if not cards:
                # fallback: 通用内容块
                cards = page.query_selector_all(".x1yztbdb, .x1lliihq, [data-ad-preview]")

            notes = []
            for card in cards:
                if len(notes) >= max_results:
                    break
                try:
                    note = self._parse_facebook_card(card, page)
                    if note:
                        notes.append(note)
                except Exception:
                    continue

            page.close()
            hb.close()

            if notes:
                return AdapterResult(success=True, notes=notes, raw_count=len(notes))
            return AdapterResult(success=True, notes=[], raw_count=0)

        except Exception as e:
            logger.exception("Facebook 浏览器采集异常")
            return AdapterResult(success=False, error=f"Facebook 采集异常: {e}")

    def _parse_facebook_card(self, card, page) -> CollectedNote | None:
        """解析单个 Facebook 搜索结果卡片。"""
        # 文本内容
        text_el = card.query_selector('[data-ad-preview="message"], .x1iorvi4, .x1pi30zi')
        content = text_el.inner_text().strip() if text_el else ""

        # 作者
        author_el = card.query_selector('h3 a, .xt0psk2 a, [role="link"] span')
        author = author_el.inner_text().strip() if author_el else ""

        # 链接
        url = ""
        link_el = card.query_selector('a[href*="/posts/"], a[href*="/videos/"], a[href*="/photos/"]')
        if link_el:
            href = link_el.get_attribute("href") or ""
            if href.startswith("/"):
                url = "https://www.facebook.com" + href
            elif href:
                url = href

        # 互动数据
        likes = self._extract_metric(card, 'span[aria-label*="赞"], .x193iq5w span')
        comments = self._extract_metric(card, 'a[href*="comments"], span[aria-label*="评论"]')
        shares = self._extract_metric(card, 'span[aria-label*="分享"], a[href*="shares"]')

        # 标题取内容前50字
        title = content[:80].replace("\n", " ") if content else f"Facebook 帖子"

        if not title and not content:
            return None

        return CollectedNote(
            title=title[:200],
            content=content[:500],
            url=url,
            author=author,
            author_id="",
            publish_date="",
            likes=likes,
            comments=comments,
            collects=0,
            shares=shares,
            cover="",
            source_platform="facebook",
            raw_data={"author": author, "url": url},
        )

    @staticmethod
    def _extract_metric(card, selector: str) -> int:
        """从卡片中提取互动数字。"""
        try:
            el = card.query_selector(selector)
            if not el:
                return 0
            text = el.inner_text().strip()
            digits = "".join(c for c in text if c.isdigit())
            return int(digits) if digits else 0
        except Exception:
            return 0

    def detail(self, post_id: str) -> AdapterResult:
        """Facebook 帖子详情（浏览器 CDP）。"""
        try:
            from .human_browser import HumanBrowser
            from .cookie_vault import inject_into_context

            hb = HumanBrowser(port=9222, launch_url="about:blank")
            hb.connect()
            inject_into_context(hb._context, "facebook")
            page = hb.new_page()
            url = f"https://www.facebook.com/{post_id}" if not post_id.startswith("http") else post_id
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            hb.pause(4.0, 4.0)

            article = page.query_selector('div[role="article"]')
            note = None
            if article:
                note = self._parse_facebook_card(article, page)

            page.close()
            hb.close()

            if note:
                return AdapterResult(success=True, notes=[note], raw_count=1)
            return AdapterResult(success=False, error="Facebook 详情未返回数据")
        except Exception as e:
            return AdapterResult(success=False, error=f"Facebook 详情异常: {e}")

    def comments(self, post_id: str, max_comments: int = 20) -> AdapterResult:
        """Facebook 评论采集（浏览器 CDP，滚动加载）。"""
        try:
            from .human_browser import HumanBrowser
            from .cookie_vault import inject_into_context

            hb = HumanBrowser(port=9222, launch_url="about:blank")
            hb.connect()
            inject_into_context(hb._context, "facebook")
            page = hb.new_page()
            url = f"https://www.facebook.com/{post_id}" if not post_id.startswith("http") else post_id
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            hb.pause(3.0, 3.0)

            # 点击展开评论
            try:
                view_more = page.query_selector('div[role="button"]:has-text("查看更多评论"), span:has-text("更多评论")')
                if view_more:
                    view_more.click()
                    hb.pause(2.0, 2.0)
            except Exception:
                pass

            comment_els = page.query_selector_all('ul[role="list"] > li, .x1y1aw1k')
            notes = []
            for cel in comment_els[:max_comments]:
                try:
                    author_el = cel.query_selector("h3 a, .xt0psk2 a")
                    content_el = cel.query_selector('.x193iq5w, [dir="auto"]')
                    notes.append(CollectedNote(
                        title="",
                        content=content_el.inner_text().strip()[:300] if content_el else "",
                        url="",
                        author=author_el.inner_text().strip() if author_el else "",
                        author_id="",
                        publish_date="",
                        likes=self._extract_metric(cel, 'span[aria-label*="赞"]'),
                        comments=0,
                        collects=0,
                        shares=0,
                        cover="",
                        source_platform="facebook_comment",
                        raw_data={},
                    ))
                except Exception:
                    continue

            page.close()
            hb.close()
            return AdapterResult(success=True, notes=notes, raw_count=len(notes))
        except Exception as e:
            return AdapterResult(success=False, error=f"Facebook 评论异常: {e}")

    def creator(self, username: str) -> AdapterResult:
        """Facebook 主页/用户信息采集。"""
        try:
            from .human_browser import HumanBrowser
            from .cookie_vault import inject_into_context

            hb = HumanBrowser(port=9222, launch_url="about:blank")
            hb.connect()
            inject_into_context(hb._context, "facebook")
            page = hb.new_page()
            url = f"https://www.facebook.com/{username}" if not username.startswith("http") else username
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            hb.pause(4.0, 4.0)

            name_el = page.query_selector("h1, .x1heor9g")
            name = name_el.inner_text().strip() if name_el else username

            page.close()
            hb.close()

            return AdapterResult(success=True, notes=[CollectedNote(
                title=name,
                content="",
                url=url,
                author=name,
                author_id=username,
                publish_date="",
                likes=0,
                comments=0,
                collects=0,
                shares=0,
                cover="",
                source_platform="facebook_creator",
                raw_data={"username": username},
            )], raw_count=1)
        except Exception as e:
            return AdapterResult(success=False, error=f"Facebook 主页异常: {e}")
