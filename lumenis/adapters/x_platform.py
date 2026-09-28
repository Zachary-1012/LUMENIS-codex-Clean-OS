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
  - 空/未验证    → success=False（不把不可验证结果报告为空成功）
  - 登录失效     → SESSION_EXPIRED 语义
  - 异常         → COLLECT_ERROR

只读红线：不点赞、不转发、不评论、不关注、不私信、不发布、不执行任何账号写操作。
"""
import re
import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .base import BaseAdapter, AdapterResult, CollectedNote
from .cookie_vault import inject_into_context, to_cookie_string
from .human_browser import HumanBrowser

logger = logging.getLogger(__name__)

_X_READONLY_CDP_URL = "http://127.0.0.1:9226"


def _configured_browser_worker_url() -> str:
    """Require the explicitly opted-in, process-bound X read-only worker."""
    value = str(os.getenv("X_READONLY_CDP_URL") or "").strip()
    enabled = str(os.getenv("X_READONLY_LOCAL_WORKER_ENABLED") or "").strip().lower()
    account = str(os.getenv("X_READONLY_LOCAL_WORKER_ACCOUNT") or "").strip().upper()
    if value != _X_READONLY_CDP_URL:
        raise RuntimeError("X_READONLY_CDP_URL must be the fixed loopback worker endpoint")
    if enabled not in {"1", "true", "yes"} or account != "X_READONLY":
        raise RuntimeError("X_READONLY worker requires explicit account opt-in")

    from pathlib import Path
    from .cookie_vault import _current_data_dir
    import cdp_helper

    profile_dir = Path(_current_data_dir()) / "private" / "profiles" / "x-readonly"
    if not cdp_helper.is_cdp_profile_running(9226, str(profile_dir)):
        raise RuntimeError("X_READONLY worker profile is not bound to the configured loopback port")
    return _X_READONLY_CDP_URL


def _new_browser_worker():
    return HumanBrowser(
        cdp_url=_configured_browser_worker_url(),
        auto_ensure=False,
        launch_url="about:blank",
    )


def _x_page_failure(url: str, _body: str = "", error: str = "", *, title: str = "") -> str:
    """Classify page state from route/title/browser errors, never arbitrary post text."""
    route = (urlsplit(str(url or "")).path or "").lower()
    page_title = str(title or "").lower().strip()
    browser_error = str(error or "").lower()
    if "/i/flow/login" in route or route.rstrip("/") == "/login" or any(
        marker in page_title for marker in ("log in to x", "sign in to x", "login to x")
    ):
        return "X login/session required or expired"
    if "/challenge" in route or any(
        marker in page_title for marker in ("captcha challenge", "verify your account", "verification required")
    ):
        return "X verification challenge detected"
    if any(marker in route for marker in ("/blocked", "/account/access")) or any(
        marker in page_title for marker in ("account suspended", "account locked", "temporarily blocked")
    ):
        return "X access blocked or rate limited"
    if any(value in browser_error for value in ("net::err_", "timed out", "timeout", "connection", "dns", "network", "无法访问此网站")):
        return "X network error"
    return ""


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
        """Collect search results only through the opted-in isolated X worker."""
        hb = None
        page = None
        try:
            from urllib.parse import quote

            hb = _new_browser_worker()
            hb.connect()
            inject_into_context(hb._context, "x")
            page = hb.new_page(stealth=False)
            url = f"https://x.com/search?q={quote(keyword.strip())}&src=typed_query"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as exc:
                message = _x_page_failure("", "", str(exc)) or f"X network error: {exc}"
                return AdapterResult(success=False, error=message)
            hb.pause(5.0, 5.0)

            page_url = str(getattr(page, "url", "") or "")
            try:
                page_title = page.title()
            except Exception:
                page_title = ""
            failure = _x_page_failure(page_url, title=page_title)
            if failure:
                return AdapterResult(success=False, error=failure)

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

            if notes:
                return AdapterResult(success=True, notes=notes, raw_count=len(notes))
            return AdapterResult(success=False, error="X search returned no verifiable posts")

        except Exception as e:
            logger.exception("X 浏览器采集异常")
            failure = _x_page_failure("", "", str(e))
            return AdapterResult(success=False, error=failure or f"X collection error: {e}")
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass
            if hb is not None:
                try:
                    hb.close()
                except Exception:
                    pass

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
        tweet_id = None
        link_el = tweet.query_selector('a[href*="/status/"]')
        if link_el:
            href = link_el.get_attribute("href") or ""
            if href.startswith("/"):
                url = "https://x.com" + href
            elif href:
                url = href
            status_match = re.search(r"/status/(\d+)(?:/|$)", urlsplit(href).path)
            if status_match:
                tweet_id = status_match.group(1)

        # 互动数据
        likes, likes_display = self._extract_metric_observation(tweet, '[data-testid="like"]')
        comments, comments_display = self._extract_metric_observation(tweet, '[data-testid="reply"]')
        shares, shares_display = self._extract_metric_observation(tweet, '[data-testid="retweet"]')
        _, views_display = self._extract_metric_observation(
            tweet, '[data-testid="app-text-transition-container"]',
        )

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
            collects=None,
            shares=shares,
            cover="",
            source_platform="x",
            raw_data={
                "tweet_id": tweet_id,
                "handle": handle,
                "views": None,
                "unclassified_counter_display": views_display,
                "url": url,
                "metric_display": {
                    "likes": likes_display,
                    "comments": comments_display,
                    "shares": shares_display,
                    "views": None,
                },
            },
        )

    @staticmethod
    def _parse_exact_metric(value: str) -> int | None:
        """Parse an exact integer label, rejecting compact and malformed groups."""
        match = re.match(r"^(?:0|[1-9]\d*|[1-9]\d{0,2}(?:,\d{3})+)(?=\s|$)", value)
        if not match:
            return None
        return int(match.group(0).replace(",", ""))

    @classmethod
    def _extract_metric_observation(cls, tweet, selector: str) -> tuple[int | None, dict | None]:
        """Keep the observed label while returning only exact counts as metrics."""
        try:
            el = tweet.query_selector(selector)
            if not el:
                return None, None
            aria_label = el.get_attribute("aria-label")
            aria_label = aria_label.strip() if isinstance(aria_label, str) else ""
            text = el.inner_text()
            text = text.strip() if isinstance(text, str) else ""
            display = {
                key: value for key, value in (("aria_label", aria_label), ("text", text))
                if value
            } or None
            count = cls._parse_exact_metric(aria_label) if aria_label else None
            if count is None and text:
                count = cls._parse_exact_metric(text)
            return count, display
        except Exception:
            return None, None

    @classmethod
    def _extract_metric(cls, tweet, selector: str) -> int | None:
        """Return an exact count; retain non-exact labels only in raw observations."""
        return cls._extract_metric_observation(tweet, selector)[0]

    @staticmethod
    def _canonical_status_url(tweet_id: str) -> str | None:
        value = str(tweet_id or "").strip()
        if value.isdigit():
            return f"https://x.com/i/web/status/{value}"
        parsed = urlsplit(value)
        if parsed.scheme != "https" or parsed.hostname not in {"x.com", "www.x.com"}:
            return None
        match = re.search(r"/status/(\d+)(?:/|$)", parsed.path)
        return f"https://x.com/i/web/status/{match.group(1)}" if match else None

    @staticmethod
    def _close_worker_page(worker, page) -> None:
        if page is not None:
            try:
                page.close()
            except Exception:
                pass
        if worker is not None:
            try:
                worker.close()
            except Exception:
                pass

    def _open_readonly_page(self, url: str, wait_seconds: float):
        worker = None
        page = None
        try:
            worker = _new_browser_worker()
            worker.connect()
            inject_into_context(worker._context, "x")
            page = worker.new_page(stealth=False)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            worker.pause(wait_seconds, wait_seconds)
            page_title = page.title()
            failure = _x_page_failure(str(getattr(page, "url", "") or ""), title=page_title)
            return worker, page, failure
        except Exception as exc:
            self._close_worker_page(worker, page)
            failure = _x_page_failure(str(getattr(page, "url", "") or ""), "", str(exc))
            return None, None, failure or "X network error"

    def detail(self, tweet_id: str) -> AdapterResult:
        """Read a post through the explicitly configured X read-only worker."""
        url = self._canonical_status_url(tweet_id)
        if not url:
            return AdapterResult(success=False, error="X detail requires a numeric post ID or canonical x.com status URL")
        worker, page, failure = self._open_readonly_page(url, 4.0)
        if failure:
            self._close_worker_page(worker, page)
            return AdapterResult(success=False, error=failure)
        try:
            article = page.query_selector("article")
            note = self._parse_x_tweet(article) if article else None
            if note:
                return AdapterResult(success=True, notes=[note], raw_count=1)
            return AdapterResult(success=False, error="X detail returned no verifiable post")
        except Exception as exc:
            failure = _x_page_failure(str(getattr(page, "url", "") or ""), "", str(exc))
            return AdapterResult(success=False, error=failure or "X detail collection failed")
        finally:
            self._close_worker_page(worker, page)

    def comments(self, tweet_id: str, max_comments: int = 20) -> AdapterResult:
        """Replies stay unavailable until parent relationships can be verified."""
        return AdapterResult(
            success=False,
            error="X comments not supported: reply-to-post relationships cannot be verified from the current page",
        )

    def creator(self, username: str) -> AdapterResult:
        """Read a creator profile through the explicitly configured X worker."""
        handle = str(username or "").strip().lstrip("@")
        if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", handle):
            return AdapterResult(success=False, error="X creator requires a valid handle")
        url = f"https://x.com/{handle}"
        worker, page, failure = self._open_readonly_page(url, 4.0)
        if failure:
            self._close_worker_page(worker, page)
            return AdapterResult(success=False, error=failure)
        try:
            name_el = page.query_selector('[data-testid="UserName"] div, h2')
            follower_el = page.query_selector('a[href*="/verified_followers"] span')
            if not name_el and not follower_el:
                return AdapterResult(success=False, error="X creator profile returned no verifiable profile fields")
            name = name_el.inner_text().strip() if name_el else ""
            follower_text = follower_el.inner_text().strip() if follower_el else ""
            followers = self._parse_exact_metric(follower_text)
            return AdapterResult(success=True, notes=[CollectedNote(
                title=name or f"@{handle}", content="", url=url, author=name or f"@{handle}",
                author_id=f"@{handle}", publish_date="", likes=None, comments=None,
                collects=None, shares=None, cover="", source_platform="x_creator",
                raw_data={"username": handle, "followers": followers,
                           "followers_display": follower_text or None},
            )], raw_count=1)
        except Exception as exc:
            failure = _x_page_failure(str(getattr(page, "url", "") or ""), "", str(exc))
            return AdapterResult(success=False, error=failure or "X creator collection failed")
        finally:
            self._close_worker_page(worker, page)
