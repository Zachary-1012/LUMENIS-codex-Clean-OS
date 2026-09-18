# -*- coding: utf-8 -*-
"""
X (Twitter) 内容采集适配器
--------------------------
定位：服务于 Z-Brand Core 多平台内容采集。
浏览器 CDP 采集 X 搜索结果，薄封装为 v4 BaseAdapter 契约，
接入熔断器/限流/重试/降级体系。

数据主路径：X 搜索页（浏览器渲染）
  https://x.com/search?q={keyword}
需登录态 cookie。

状态映射：
  - 有结果       → SUCCESS
  - 正常空       → success=True, notes=[]
  - 登录失效     → SESSION_EXPIRED 语义
  - 异常         → COLLECT_ERROR

只读红线：不点赞、不转发、不评论、不关注、不私信、不发布、不执行任何账号写操作。
"""
import re
import logging
from datetime import datetime, timezone

from .base import BaseAdapter, AdapterResult, CollectedNote
from .cookie_vault import to_cookie_string

logger = logging.getLogger(__name__)


class XAdapter(BaseAdapter):
    """X (Twitter) 搜索适配器（浏览器 CDP + cookie，只读采集）"""

    platform_name = "x"
    platform_display = "X"

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
        """经 cookie_vault 加载 X cookie 字符串。"""
        return to_cookie_string("x")

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        return self._search_browser(keyword, max_results)

    def _search_browser(self, keyword: str, max_results: int) -> AdapterResult:
        """浏览器 CDP 采集 X 搜索结果。"""
        try:
            from .human_browser import HumanBrowser
            from .cookie_vault import inject_into_context
            from urllib.parse import quote

            hb = HumanBrowser(port=9222, launch_url="about:blank")
            hb.connect()
            inject_into_context(hb._context, "x")
            page = hb.new_page()
            url = f"https://x.com/search?q={quote(keyword.strip())}&src=typed_query"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            hb.pause(5.0, 5.0)

            # 检测登录态
            if "login" in page.url.lower() or "signup" in page.url.lower():
                page.close()
                hb.close()
                return AdapterResult(success=False, error="X 登录态失效，请更新 cookie 或重新登录")

            # 滚动加载更多
            for _ in range(2):
                page.mouse.wheel(0, 2000)
                hb.pause(1.5, 1.5)

            # 解析推文（X 使用 article 标签）
            tweets = page.query_selector_all("article")
            notes = []
            for tweet in tweets:
                if len(notes) >= max_results:
                    break
                try:
                    note = self._parse_x_tweet(tweet)
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
            logger.exception("X 浏览器采集异常")
            return AdapterResult(success=False, error=f"X 采集异常: {e}")

    def _parse_x_tweet(self, tweet) -> CollectedNote | None:
        """解析单个 X 推文。"""
        # 推文文本
        text_el = tweet.query_selector('[data-testid="tweetText"]')
        content = text_el.inner_text().strip() if text_el else ""

        # 作者
        author_el = tweet.query_selector('[data-testid="User-Name"] a, [data-testid="User-Names"] a')
        author = author_el.inner_text().strip() if author_el else ""

        # 作者ID（@handle）
        handle = ""
        handle_els = tweet.query_selector_all('[data-testid="User-Name"] span')
        for hel in handle_els:
            t = hel.inner_text().strip()
            if t.startswith("@"):
                handle = t
                break

        # 链接
        url = ""
        link_el = tweet.query_selector('a[href*="/status/"]')
        if link_el:
            href = link_el.get_attribute("href") or ""
            if href.startswith("/"):
                url = "https://x.com" + href
            elif href:
                url = href

        # 互动数据
        likes = self._extract_metric(tweet, '[data-testid="like"]')
        comments = self._extract_metric(tweet, '[data-testid="reply"]')
        shares = self._extract_metric(tweet, '[data-testid="retweet"]')
        views = self._extract_metric(tweet, '[data-testid="app-text-transition-container"]')

        # 发布时间
        publish_date = ""
        time_el = tweet.query_selector("time")
        if time_el:
            publish_date = time_el.get_attribute("datetime") or ""

        # 标题取推文前80字
        title = content[:80].replace("\n", " ") if content else "X 推文"

        if not title and not content:
            return None

        return CollectedNote(
            title=title[:200],
            content=content[:500],
            url=url,
            author=author or handle,
            author_id=handle,
            publish_date=publish_date,
            likes=likes,
            comments=comments,
            collects=0,
            shares=shares,
            cover="",
            source_platform="x",
            raw_data={"handle": handle, "views": views, "url": url},
        )

    @staticmethod
    def _extract_metric(tweet, selector: str) -> int:
        """从推文中提取互动数字。"""
        try:
            el = tweet.query_selector(selector)
            if not el:
                return 0
            # X 使用 aria-label 或子元素显示数字
            label = el.get_attribute("aria-label") or ""
            digits = "".join(c for c in label if c.isdigit())
            if digits:
                return int(digits)
            text = el.inner_text().strip()
            digits = "".join(c for c in text if c.isdigit())
            return int(digits) if digits else 0
        except Exception:
            return 0

    def detail(self, tweet_id: str) -> AdapterResult:
        """X 推文详情（浏览器 CDP）。"""
        try:
            from .human_browser import HumanBrowser
            from .cookie_vault import inject_into_context

            hb = HumanBrowser(port=9222, launch_url="about:blank")
            hb.connect()
            inject_into_context(hb._context, "x")
            page = hb.new_page()
            url = tweet_id if tweet_id.startswith("http") else f"https://x.com/i/web/status/{tweet_id}"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            hb.pause(4.0, 4.0)

            article = page.query_selector("article")
            note = None
            if article:
                note = self._parse_x_tweet(article)

            page.close()
            hb.close()

            if note:
                return AdapterResult(success=True, notes=[note], raw_count=1)
            return AdapterResult(success=False, error="X 详情未返回数据")
        except Exception as e:
            return AdapterResult(success=False, error=f"X 详情异常: {e}")

    def comments(self, tweet_id: str, max_comments: int = 20) -> AdapterResult:
        """X 评论采集（浏览器 CDP，滚动加载）。"""
        try:
            from .human_browser import HumanBrowser
            from .cookie_vault import inject_into_context

            hb = HumanBrowser(port=9222, launch_url="about:blank")
            hb.connect()
            inject_into_context(hb._context, "x")
            page = hb.new_page()
            url = tweet_id if tweet_id.startswith("http") else f"https://x.com/i/web/status/{tweet_id}"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            hb.pause(3.0, 3.0)

            # 滚动加载评论
            for _ in range(2):
                page.mouse.wheel(0, 2000)
                hb.pause(1.5, 1.5)

            articles = page.query_selector_all("article")
            notes = []
            # 第一个article是原推文，后面是评论
            for article in articles[1:max_comments + 1]:
                try:
                    note = self._parse_x_tweet(article)
                    if note:
                        note.source_platform = "x_comment"
                        notes.append(note)
                except Exception:
                    continue

            page.close()
            hb.close()
            return AdapterResult(success=True, notes=notes, raw_count=len(notes))
        except Exception as e:
            return AdapterResult(success=False, error=f"X 评论异常: {e}")

    def creator(self, username: str) -> AdapterResult:
        """X 用户主页信息采集。"""
        try:
            from .human_browser import HumanBrowser
            from .cookie_vault import inject_into_context

            hb = HumanBrowser(port=9222, launch_url="about:blank")
            hb.connect()
            inject_into_context(hb._context, "x")
            page = hb.new_page()
            handle = username.lstrip("@")
            url = f"https://x.com/{handle}"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            hb.pause(4.0, 4.0)

            name_el = page.query_selector('[data-testid="UserName"] div, h2')
            name = name_el.inner_text().strip() if name_el else handle

            # 粉丝数
            followers = 0
            follower_el = page.query_selector('a[href*="/verified_followers"] span')
            if follower_el:
                digits = "".join(c for c in follower_el.inner_text() if c.isdigit())
                followers = int(digits) if digits else 0

            page.close()
            hb.close()

            return AdapterResult(success=True, notes=[CollectedNote(
                title=name,
                content="",
                url=url,
                author=name,
                author_id=f"@{handle}",
                publish_date="",
                likes=followers,
                comments=0,
                collects=0,
                shares=0,
                cover="",
                source_platform="x_creator",
                raw_data={"username": handle, "followers": followers},
            )], raw_count=1)
        except Exception as e:
            return AdapterResult(success=False, error=f"X 主页异常: {e}")
