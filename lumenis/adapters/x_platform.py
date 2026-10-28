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
from datetime import datetime
from urllib.parse import quote, urlsplit

from .base import BaseAdapter, AdapterResult, CollectedNote, optional_int
from .cookie_vault import inject_into_context, to_cookie_string
from .human_browser import (HumanBrowser, NativeReadCapture, NativePageWindowError, native_page_window,
                            native_read_scroll, validate_native_page_window_cursor)

logger = logging.getLogger(__name__)

_X_READONLY_CDP_URL = "http://127.0.0.1:9226"
_X_FAILURE_REASONS = frozenset({
    "NOT_CONFIGURED", "SESSION_EXPIRED", "VERIFICATION_REQUIRED", "RATE_LIMITED",
    "NETWORK_UNAVAILABLE", "PROVIDER_UNAVAILABLE", "NOT_SUPPORTED",
    "IDENTITY_MISMATCH", "DETAIL_NOT_RETURNED", "UPSTREAM_FAILURE",
})


def _x_failure_code(error, *, phase: str = "page") -> str:
    """FIX-096: collapse backend failures to a phase-bound allowlisted code."""
    phase_name = "WORKER" if str(phase).lower() == "worker" else "PAGE"
    text = str(error or "").casefold()
    match = re.fullmatch(r"x_(worker|page)_failure:([a-z_]+)", text.strip())
    if match and match.group(2).upper() in _X_FAILURE_REASONS:
        return f"X_{match.group(1).upper()}_FAILURE:{match.group(2).upper()}"
    if any(marker in text for marker in ("not configured", "not_configured", "not registered", "未配置")):
        reason = "NOT_CONFIGURED"
    elif any(marker in text for marker in ("not supported", "unsupported", "review required", "不支持")):
        reason = "NOT_SUPPORTED"
    elif any(marker in text for marker in ("identity mismatch", "identity_mismatch", "身份不匹配")):
        reason = "IDENTITY_MISMATCH"
    elif any(marker in text for marker in ("no verifiable post", "no unique matching target article")):
        reason = "DETAIL_NOT_RETURNED"
    elif any(marker in text for marker in ("login", "session", "cookie", "登录", "未登录", "失效")):
        reason = "SESSION_EXPIRED"
    elif any(marker in text for marker in ("challenge", "captcha", "verification", "verify", "验证")):
        reason = "VERIFICATION_REQUIRED"
    elif any(marker in text for marker in ("rate limit", "rate limited", "too many", "blocked", "封禁", "http 429", " 429", "频控")):
        reason = "RATE_LIMITED"
    elif any(marker in text for marker in ("network", "timeout", "connection", "dns", "net::err_", "不可达")):
        reason = "NETWORK_UNAVAILABLE"
    else:
        reason = "UPSTREAM_FAILURE"
    return f"X_{phase_name}_FAILURE:{reason}"


def _configured_browser_worker_url() -> str:
    """Require the explicitly opted-in, process-bound X read-only worker."""
    value = str(os.getenv("X_READONLY_CDP_URL") or "").strip()
    enabled = str(os.getenv("X_READONLY_LOCAL_WORKER_ENABLED") or "").strip().lower()
    account = str(os.getenv("X_READONLY_LOCAL_WORKER_ACCOUNT") or "").strip().upper()
    if value != _X_READONLY_CDP_URL:
        raise RuntimeError("X_WORKER_FAILURE:NOT_CONFIGURED")
    if enabled not in {"1", "true", "yes"} or account != "X_READONLY":
        raise RuntimeError("X_WORKER_FAILURE:NOT_CONFIGURED")

    from .cookie_vault import registered_session_data_dir
    import cdp_helper

    profile_dir = registered_session_data_dir() / "private" / "profiles" / "x-readonly"
    if not cdp_helper.is_cdp_profile_running(9226, str(profile_dir)):
        raise RuntimeError("X_WORKER_FAILURE:NOT_CONFIGURED")
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
        return "X_PAGE_FAILURE:SESSION_EXPIRED"
    if "/challenge" in route or any(
        marker in page_title for marker in ("captcha challenge", "verify your account", "verification required")
    ):
        return "X_PAGE_FAILURE:VERIFICATION_REQUIRED"
    if any(marker in route for marker in ("/blocked", "/account/access")) or any(
        marker in page_title for marker in ("account suspended", "account locked", "temporarily blocked")
    ):
        return "X_PAGE_FAILURE:RATE_LIMITED"
    if any(value in browser_error for value in ("net::err_", "timed out", "timeout", "connection", "dns", "network", "无法访问此网站")):
        return "X_PAGE_FAILURE:NETWORK_UNAVAILABLE"
    if browser_error:
        return _x_failure_code(browser_error, phase="page")
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

    @staticmethod
    def _normalize_skip_tweet_ids(skip_tweet_ids):
        if skip_tweet_ids is None:
            return None
        if (isinstance(skip_tweet_ids, (str, bytes))
                or not isinstance(skip_tweet_ids, (list, tuple, set, frozenset))
                or len(skip_tweet_ids) > 5000
                or any(not isinstance(tweet_id, str)
                       or re.fullmatch(r"[0-9]+", tweet_id) is None
                       for tweet_id in skip_tweet_ids)):
            raise ValueError("X seen-ID checkpoint must contain at most 5000 numeric string IDs")
        return frozenset(skip_tweet_ids)

    def search(self, keyword: str, max_results: int = 20, *,
               skip_tweet_ids=None, cursor=None) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        try:
            skip_tweet_ids = self._normalize_skip_tweet_ids(skip_tweet_ids)
        except ValueError as exc:
            return AdapterResult(success=False, error=str(exc))
        result = self._native_read("search", keyword.strip(), max_results, cursor=cursor)
        if skip_tweet_ids and result.success:
            result.notes = [note for note in result.notes if note.raw_data.get("tweet_id") not in skip_tweet_ids]
        return result

    def _search_browser(self, keyword: str, max_results: int, *,
                        skip_tweet_ids=None) -> AdapterResult:
        """Collect one bounded batch through the opted-in isolated X worker."""
        try:
            result_limit = min(20, max(0, int(max_results)))
        except (TypeError, ValueError, OverflowError):
            return AdapterResult(success=False, error="X search result limit is invalid")
        try:
            skip_tweet_ids = self._normalize_skip_tweet_ids(skip_tweet_ids)
        except ValueError as exc:
            return AdapterResult(success=False, error=str(exc))
        checkpoint_used = skip_tweet_ids is not None
        skipped_ids = skip_tweet_ids or frozenset()
        notes = []
        visited_tweet_ids = set()
        native_id_list_limit = 1000

        def bounded_native_ids(values):
            if len(values) > native_id_list_limit:
                return None, "LIMIT_EXCEEDED_LIST_OMITTED"

            def numeric_key(value):
                normalized = value.lstrip("0") or "0"
                return len(normalized), normalized, value
            return sorted(values, key=numeric_key), "OBSERVED_SET_RETURNED"

        def attach_continuation_metadata(result):
            observed_native_ids, observed_native_ids_state = bounded_native_ids(visited_tweet_ids)
            committed_skipped_ids, committed_skipped_ids_state = bounded_native_ids(
                visited_tweet_ids.intersection(skipped_ids)
            )
            result.metadata = {
                "continuation": {
                    "seen_checkpoint_used": checkpoint_used,
                    "seen_checkpoint_id_count": len(skipped_ids),
                    "committed_id_count": 0,
                    "bounded_observed_id_count": len(visited_tweet_ids),
                    "bounded_observed_native_ids": observed_native_ids,
                    "bounded_observed_native_ids_state": observed_native_ids_state,
                    "committed_skip_id_count": len(visited_tweet_ids.intersection(skipped_ids)),
                    "committed_skipped_native_ids": committed_skipped_ids,
                    "committed_skipped_native_ids_state": committed_skipped_ids_state,
                    "native_id_list_limit": native_id_list_limit,
                    "new_id_count": len(result.notes or []),
                    "native_cursor": None,
                    "pagination_exhausted": None,
                    "coverage_complete": False,
                }
            }
            return result

        hb = None
        page = None
        phase = "worker"
        try:
            from urllib.parse import quote

            hb = _new_browser_worker()
            hb.connect()
            inject_into_context(hb._context, "x")
            page = hb.new_page(stealth=False)
            phase = "page"
            url = f"https://x.com/search?q={quote(keyword.strip())}&src=typed_query"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as exc:
                message = _x_page_failure("", "", str(exc)) or _x_failure_code(exc, phase="page")
                return attach_continuation_metadata(
                    AdapterResult(success=False, error=message),
                )
            hb.pause(5.0, 5.0)

            page_url = str(getattr(page, "url", "") or "")
            try:
                page_title = page.title()
            except Exception:
                page_title = ""
            failure = _x_page_failure(page_url, title=page_title)
            if failure:
                return attach_continuation_metadata(
                    AdapterResult(success=False, error=failure),
                )

            def collect_visible_tweets():
                added = 0
                for tweet in page.query_selector_all("article"):
                    if len(notes) >= result_limit:
                        break
                    try:
                        note = self._parse_x_tweet(tweet)
                    except Exception:
                        continue
                    if note is None:
                        continue
                    raw_data = getattr(note, "raw_data", None)
                    tweet_id = raw_data.get("tweet_id") if isinstance(raw_data, dict) else None
                    if (not isinstance(tweet_id, str)
                            or re.fullmatch(r"[0-9]+", tweet_id) is None
                            or tweet_id in visited_tweet_ids):
                        continue
                    visited_tweet_ids.add(tweet_id)
                    added += 1
                    if tweet_id in skipped_ids:
                        continue
                    notes.append(note)
                return added

            collect_visible_tweets()
            no_new_scroll_rounds = 0
            scroll_rounds = 0
            while (len(notes) < result_limit and scroll_rounds < 8
                   and no_new_scroll_rounds < 2):
                page.mouse.wheel(0, 2000)
                hb.pause(1.5, 1.5)
                scroll_rounds += 1
                page_url = str(getattr(page, "url", "") or "")
                try:
                    page_title = page.title()
                except Exception:
                    page_title = ""
                failure = _x_page_failure(page_url, title=page_title)
                if failure:
                    return attach_continuation_metadata(
                        AdapterResult(success=False, notes=notes, error=failure,
                                      raw_count=len(visited_tweet_ids)),
                    )
                added = collect_visible_tweets()
                no_new_scroll_rounds = 0 if added else no_new_scroll_rounds + 1

            if notes:
                return attach_continuation_metadata(
                    AdapterResult(success=True, notes=notes,
                                  raw_count=len(visited_tweet_ids)),
                )
            if (checkpoint_used and visited_tweet_ids
                    and visited_tweet_ids.issubset(skipped_ids)):
                return attach_continuation_metadata(
                    AdapterResult(success=True, notes=[],
                                  raw_count=len(visited_tweet_ids)),
                )
            return attach_continuation_metadata(
                AdapterResult(success=False,
                              error="X search returned no verifiable posts",
                              raw_count=len(visited_tweet_ids)),
            )

        except Exception as e:
            failure = _x_failure_code(e, phase=phase)
            logger.warning("X browser collection failed phase=%s code=%s", phase, failure)
            return attach_continuation_metadata(
                AdapterResult(success=False, notes=notes,
                              error=failure,
                              raw_count=len(visited_tweet_ids)),
            )
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

    def _parse_x_tweet(self, tweet, expected_tweet_id: str | None = None) -> CollectedNote | None:
        """解析单个 X 推文。"""
        primary = self._primary_timestamp_permalink(tweet)
        tweet_id = primary.get("tweet_id") if primary else None
        url = primary.get("url") if primary else ""
        if expected_tweet_id is not None and tweet_id != expected_tweet_id:
            return None

        # Main-post text only. Quoted-post text remains a separate native post
        # and must never become this article's caption/body.
        text_el = None
        for candidate in tweet.query_selector_all('[data-testid="tweetText"]'):
            if not self._inside_quoted_post(candidate):
                text_el = candidate
                break
        content = text_el.inner_text().strip() if text_el else ""
        caption_locator = 'article [data-testid="tweetText"] outside quote container' if text_el else None

        # 作者
        author_el = next((candidate for candidate in tweet.query_selector_all(
            '[data-testid="User-Name"] a, [data-testid="User-Names"] a'
        ) if not self._inside_quoted_post(candidate)), None)
        author = author_el.inner_text().strip() if author_el else ""

        # 作者ID（@handle）
        handle = ""
        handle_els = tweet.query_selector_all('[data-testid="User-Name"] span')
        for hel in handle_els:
            if self._inside_quoted_post(hel):
                continue
            t = hel.inner_text().strip()
            if t.startswith("@"):
                handle = t
                break

        # 互动数据
        likes, likes_display = self._extract_metric_observation(tweet, '[data-testid="like"]')
        comments, comments_display = self._extract_metric_observation(tweet, '[data-testid="reply"]')
        shares, shares_display = self._extract_metric_observation(tweet, '[data-testid="retweet"]')
        _, views_display = self._extract_metric_observation(
            tweet, '[data-testid="app-text-transition-container"]',
        )

        publish_date = primary.get("publish_datetime", "") if primary else ""
        media_hints = self._extract_post_media_hints(tweet)

        # 标题取推文前80字
        title = content[:80].replace("\n", " ") if content else "X 推文"

        if not title and not content:
            return None

        return CollectedNote(
            title=title[:200],
            content=content,
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
                "tweet_id_locator": primary.get("tweet_id_locator") if primary else None,
                "native_time_locator": primary.get("native_time_locator") if primary else None,
                "caption_locator": caption_locator,
                "handle": handle,
                "views": None,
                "unclassified_counter_display": views_display,
                "unclassified_counter_locator": ('[data-testid="app-text-transition-container"]'
                                                   if views_display else None),
                "url": url,
                "native_identity": {
                    "tweet_id": tweet_id,
                    "locator": primary.get("tweet_id_locator") if primary else None,
                    "status": "OBSERVED" if tweet_id else "NOT_OBSERVED",
                },
                "metrics": {"likes": likes, "comments": comments, "shares": shares, "views": None},
                "metric_display": {
                    "likes": likes_display,
                    "comments": comments_display,
                    "shares": shares_display,
                    "views": None,
                },
                "metric_locators": {
                    "likes": '[data-testid="like"]',
                    "comments": '[data-testid="reply"]',
                    "shares": '[data-testid="retweet"]',
                },
                "media_hints": media_hints,
                "media_state": "URL_HINTS_OBSERVED" if media_hints else "NOT_OBSERVED",
                "media_bytes_saved": False,
                "artifact_created": False,
            },
        )

    @staticmethod
    def _status_id_from_url(value: str) -> str | None:
        if not isinstance(value, str):
            return None
        try:
            parts = urlsplit(value)
            port = parts.port
        except (TypeError, ValueError):
            return None
        if (parts.scheme.lower() != "https"
                or parts.hostname not in {"x.com", "www.x.com"}
                or port not in (None, 443)
                or parts.username or parts.password):
            return None
        match = re.search(r"(?:^|/)status/([0-9]+)(?:/|$)", parts.path)
        return match.group(1) if match else None

    @classmethod
    def _canonical_post_permalink(cls, href: str) -> tuple[str | None, str | None]:
        if not isinstance(href, str) or not href:
            return None, None
        value = href if not href.startswith("//") else "https:" + href
        try:
            parts = urlsplit(value)
            port = parts.port
        except (TypeError, ValueError):
            return None, None
        if parts.scheme:
            if (parts.scheme.lower() != "https"
                    or parts.hostname not in {"x.com", "www.x.com"}
                    or port not in (None, 443)
                    or parts.username or parts.password):
                return None, None
            path = parts.path
        else:
            if parts.netloc or not parts.path.startswith("/"):
                return None, None
            path = parts.path
        match = re.search(r"(?:^|/)status/([0-9]+)(?:/|$)", path)
        if not match:
            return None, None
        return "https://x.com" + path, match.group(1)

    @staticmethod
    def _inside_quoted_post(element) -> bool:
        try:
            return bool(element.evaluate("el => !!el.closest('[data-testid=quoteTweet]')"))
        except Exception:
            return False

    def _primary_timestamp_permalink(self, tweet) -> dict | None:
        """Use the post's own timestamp anchor, excluding quoted-post timestamps."""
        for anchor in tweet.query_selector_all('a[href*="/status/"]'):
            time_el = anchor.query_selector("time[datetime]")
            if not time_el or self._inside_quoted_post(anchor):
                continue
            permalink, tweet_id = self._canonical_post_permalink(anchor.get_attribute("href") or "")
            if not permalink or not tweet_id:
                continue
            publish_datetime = time_el.get_attribute("datetime") or ""
            return {
                "tweet_id": tweet_id,
                "url": permalink,
                "publish_datetime": publish_datetime,
                "tweet_id_locator": "article a[href*='/status/'] time[datetime] (primary, outside quote container)",
                "native_time_locator": "article a[href*='/status/'] time[datetime] (datetime attribute)",
            }
        return None

    @staticmethod
    def _sanitize_media_hint_url(value: str) -> str | None:
        if not isinstance(value, str) or not value:
            return None
        url_value = value if not value.startswith("//") else "https:" + value
        try:
            parts = urlsplit(url_value)
            port = parts.port
        except (TypeError, ValueError):
            return None
        host = (parts.hostname or "").lower()
        if (parts.scheme.lower() != "https"
                or (host != "twimg.com" and not host.endswith(".twimg.com"))
                or port not in (None, 443)
                or parts.username or parts.password):
            return None
        return f"https://{host}{parts.path}"

    def _extract_post_media_hints(self, tweet) -> list[dict]:
        hints = []
        seen = set()

        def add(element, kind, src):
            safe_url = self._sanitize_media_hint_url(src)
            if not safe_url:
                return
            try:
                locator = element.evaluate("""el => {
                    const parts=[];
                    while (el && el.tagName.toLowerCase() !== 'article') {
                        const tag=el.tagName.toLowerCase(); let n=1, prev=el.previousElementSibling;
                        while (prev) { if (prev.tagName === el.tagName) n++; prev=prev.previousElementSibling; }
                        parts.unshift(`${tag}:nth-of-type(${n})`); el=el.parentElement;
                    }
                    return 'article' + (parts.length ? ' > ' + parts.join(' > ') : '');
                }""")
            except Exception:
                locator = None
            key = (kind, safe_url)
            if key not in seen:
                seen.add(key)
                hints.append({"kind": kind, "url_hint": safe_url, "locator": locator})

        for image in tweet.query_selector_all("img[src]"):
            if self._inside_quoted_post(image):
                continue
            alt = (image.get_attribute("alt") or "").lower()
            try:
                is_avatar = bool(image.evaluate(
                    "el => !!(el.closest('[data-testid=Tweet-User-Avatar]') || el.closest('[data-testid=UserAvatar-Container]'))"
                ))
            except Exception:
                is_avatar = False
            if is_avatar or any(marker in alt for marker in ("profile picture", "avatar", "头像")):
                continue
            try:
                src = image.evaluate("el => el.currentSrc || el.src || el.getAttribute('src') || ''")
            except Exception:
                src = image.get_attribute("src") or ""
            add(image, "image", src)

        for video in tweet.query_selector_all("video"):
            if self._inside_quoted_post(video):
                continue
            try:
                src = video.evaluate("el => el.currentSrc || el.src || el.getAttribute('src') || ''")
            except Exception:
                src = video.get_attribute("src") or ""
            add(video, "video", src)
            poster = video.get_attribute("poster") or ""
            add(video, "image", poster)
            for source in video.query_selector_all("source[src]"):
                try:
                    src = source.evaluate("el => el.src || el.getAttribute('src') || ''")
                except Exception:
                    src = source.get_attribute("src") or ""
                add(source, "video", src)
        return hints

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
            el = next((candidate for candidate in tweet.query_selector_all(selector)
                       if not cls._inside_quoted_post(candidate)), None)
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
            if display is not None:
                display["locator"] = selector
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
        if not isinstance(tweet_id, str):
            return None
        if re.fullmatch(r"[0-9]+", tweet_id):
            return f"https://x.com/i/web/status/{tweet_id}"
        observed_id = XAdapter._status_id_from_url(tweet_id)
        return f"https://x.com/i/web/status/{observed_id}" if observed_id else None

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
        phase = "worker"
        try:
            worker = _new_browser_worker()
            worker.connect()
            inject_into_context(worker._context, "x")
            page = worker.new_page(stealth=False)
            phase = "page"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            worker.pause(wait_seconds, wait_seconds)
            page_title = page.title()
            failure = _x_page_failure(str(getattr(page, "url", "") or ""), title=page_title)
            return worker, page, failure
        except Exception as exc:
            self._close_worker_page(worker, page)
            failure = _x_page_failure(str(getattr(page, "url", "") or ""), "", str(exc))
            return None, None, failure or _x_failure_code(exc, phase=phase)

    def detail(self, tweet_id: str) -> AdapterResult:
        """Read a post through the explicitly configured X read-only worker."""
        url = self._canonical_status_url(tweet_id)
        if not url:
            return AdapterResult(success=False, error="X detail requires a numeric post ID or canonical x.com status URL")
        requested_tweet_id = self._status_id_from_url(url)
        if not requested_tweet_id:
            return AdapterResult(success=False, error="X detail requires the exact observed numeric post ID")
        return self._native_read("detail", requested_tweet_id, 1)

    def _detail_dom_observation(self, url, requested_tweet_id):
        worker, page, failure = self._open_readonly_page(url, 4.0)
        if failure:
            self._close_worker_page(worker, page)
            return AdapterResult(success=False, error=failure)
        try:
            final_url = str(getattr(page, "url", "") or "")
            final_tweet_id = self._status_id_from_url(final_url)
            if final_tweet_id != requested_tweet_id:
                return AdapterResult(success=False, error="X detail identity mismatch: final official URL does not match requested post ID")

            matching_notes = []
            for article in page.query_selector_all("article"):
                note = self._parse_x_tweet(article, expected_tweet_id=requested_tweet_id)
                if not note:
                    continue
                raw = dict(note.raw_data or {})
                permalink_id = self._status_id_from_url(note.url)
                if raw.get("tweet_id") != requested_tweet_id or permalink_id != requested_tweet_id:
                    continue
                raw["native_identity"] = {
                    "tweet_id": requested_tweet_id,
                    "requested_tweet_id": requested_tweet_id,
                    "final_tweet_id": final_tweet_id,
                    "final_url_path": urlsplit(final_url).path,
                    "tweet_id_locator": raw.get("tweet_id_locator"),
                    "status": "OBSERVED_MATCH",
                }
                note.raw_data = raw
                matching_notes.append(note)

            if len(matching_notes) == 1:
                return AdapterResult(success=True, notes=matching_notes, raw_count=1)
            return AdapterResult(success=False, error="X detail identity mismatch: target article was not unique by timestamp permalink ID")
        except Exception as exc:
            failure = _x_page_failure(str(getattr(page, "url", "") or ""), "", str(exc))
            return AdapterResult(success=False, error=failure or _x_failure_code(exc, phase="page"))
        finally:
            self._close_worker_page(worker, page)

    def comments(self, tweet_id: str, max_comments: int = 20, *, cursor=None, include_replies=False) -> AdapterResult:
        url = self._canonical_status_url(tweet_id)
        target = self._status_id_from_url(url) if url else None
        if not target:
            return AdapterResult(success=False, error="X_PAGE_FAILURE:IDENTITY_MISMATCH")
        return self._native_read("comments", target, max_comments, cursor=cursor, include_replies=include_replies)

    @staticmethod
    def _native_entries(value):
        entries, terminated = [], False
        def visit(node):
            nonlocal terminated
            if isinstance(node, dict):
                if node.get("type") in {"TimelineTerminateTimeline", "TimelineTerminateInstruction"}:
                    terminated = True
                if isinstance(node.get("entries"), list):
                    entries.extend(item for item in node["entries"] if isinstance(item, dict))
                elif isinstance(node.get("entry"), dict):
                    entries.append(node["entry"])
                for key, child in node.items():
                    if key not in {"entries", "entry", "quoted_status_result", "retweeted_status_result"}:
                        visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)
        visit(value)
        return entries, terminated

    @classmethod
    def _native_timeline(cls, value):
        """Only timeline items; embedded quoted/reposted posts are not results."""
        entries, terminated = cls._native_entries(value)
        tweets, cursors = [], []
        def item(content, entry_id):
            if not isinstance(content, dict) or content.get("promotedMetadata"):
                return
            if content.get("cursorType") and isinstance(content.get("value"), str):
                cursors.append({"cursor": content["value"], "kind": content["cursorType"], "entry_id": entry_id})
            candidate = (content.get("tweet_results") or {}).get("result")
            if isinstance(candidate, dict) and isinstance(candidate.get("tweet"), dict):
                candidate = candidate["tweet"]
            if isinstance(candidate, dict) and isinstance(candidate.get("legacy"), dict):
                tweets.append(candidate)
            for key in ("itemContent", "content", "item"):
                if isinstance(content.get(key), dict):
                    item(content[key], entry_id)
            for child in content.get("items") or []:
                if isinstance(child, dict):
                    item(child, entry_id)
        for entry in entries:
            item(entry.get("content"), entry.get("entryId"))
        return tweets, cursors, terminated, bool(entries)

    @staticmethod
    def _native_user(tweet):
        user = ((tweet.get("core") or {}).get("user_results") or {}).get("result")
        return user if isinstance(user, dict) else {}

    def _native_note(self, tweet):
        legacy = tweet.get("legacy") or {}
        tid = tweet.get("rest_id") or legacy.get("id_str")
        if not isinstance(tid, str) or not re.fullmatch(r"[1-9][0-9]{0,29}", tid):
            return None
        user = self._native_user(tweet)
        profile = user.get("legacy") if isinstance(user.get("legacy"), dict) else {}
        core = user.get("core") if isinstance(user.get("core"), dict) else {}
        handle = core.get("screen_name") or profile.get("screen_name") or ""
        name = core.get("name") or profile.get("name") or ""
        long_form = ((tweet.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result") or {}
        text = long_form.get("text") if isinstance(long_form.get("text"), str) else legacy.get("full_text")
        if not isinstance(text, str):
            return None
        published = ""
        if isinstance(legacy.get("created_at"), str):
            try: published = datetime.strptime(legacy["created_at"], "%a %b %d %H:%M:%S %z %Y").isoformat()
            except ValueError: pass
        hints = []
        for media in (legacy.get("extended_entities") or legacy.get("entities") or {}).get("media") or []:
            if not isinstance(media, dict):
                continue
            urls = [(media.get("media_url_https"), "image" if media.get("type") == "photo" else "video_cover", None)]
            urls.extend((variant.get("url"), "video", variant.get("content_type")) for variant in
                        (media.get("video_info") or {}).get("variants") or [] if isinstance(variant, dict))
            for value, kind, mime in urls:
                safe = self._sanitize_media_hint_url(value) if isinstance(value, str) else None
                if safe:
                    hints.append({"kind": kind, "url": safe, "native_media_id": str(media.get("id_str") or media.get("id") or "") or None,
                                  "content_type": mime, "locator": "$.legacy.extended_entities.media[]", "bytes_state": "NOT_ACQUIRED"})
        raw = {"engine": "x_native_timeline", "tweet_id": tid, "username": handle,
               "native_user_id": user.get("rest_id"), "source_observation": {"rest_id": tid, "legacy": legacy,
                    "note_tweet": tweet.get("note_tweet"), "user": {"rest_id": user.get("rest_id"), "legacy": profile, "core": core}},
               "body_state": "PLATFORM_BODY" if long_form.get("text") or legacy.get("truncated") is False else "COMPLETENESS_NOT_OBSERVED",
               "body_locator": "$.note_tweet.note_tweet_results.result.text" if long_form.get("text") else "$.legacy.full_text",
               "native_time": legacy.get("created_at"), "parent_comment_id": legacy.get("in_reply_to_status_id_str"),
               "conversation_id": legacy.get("conversation_id_str"), "media_hints": hints,
               "metric_observations": {"views": optional_int((tweet.get("views") or {}).get("count"))}}
        return CollectedNote(title=text[:100], content=text, url=f"https://x.com/i/status/{tid}", author=name,
            author_id="@" + handle if handle else str(user.get("rest_id") or ""), publish_date=published,
            likes=optional_int(legacy.get("favorite_count")), comments=optional_int(legacy.get("reply_count")),
            collects=optional_int(legacy.get("bookmark_count")), shares=optional_int(legacy.get("retweet_count")),
            cover=next((h["url"] for h in hints if h["kind"] in {"image", "video_cover"}), ""), source_platform="x", raw_data=raw)

    def _native_read(self, capability, target, limit, *, cursor=None, include_replies=False):
        if type(limit) is not int or not 1 <= limit <= 100:
            return AdapterResult(success=False, error="X_NATIVE_PAGE_SIZE_INVALID")
        try:
            validate_native_page_window_cursor(cursor)
        except NativePageWindowError:
            return AdapterResult(success=False, error='X_NATIVE_CURSOR_WINDOW_INVALID')
        if cursor is not None and (not isinstance(cursor, dict) or not {"cursor"} <= set(cursor) <= {"cursor", "kind", "entry_id", "item_offset", "page_sha256"}
                or not isinstance(cursor["cursor"], str) or len(cursor["cursor"]) > 4096
                or not cursor['cursor'] and 'item_offset' not in cursor
                or any(ord(c) < 32 for c in cursor["cursor"])):
            return AdapterResult(success=False, error="X_NATIVE_CURSOR_INVALID")
        if capability in {"author_posts", "author"} and not re.fullmatch(r"[A-Za-z0-9_]{1,15}", target):
            return AdapterResult(success=False, error="X_AUTHOR_ID_INVALID")
        url = (f"https://x.com/search?q={quote(target)}&f=live" if capability == "search" else
               f"https://x.com/i/status/{target}" if capability in {"detail", "comments"} else f"https://x.com/{target}")
        operations = {"search": ("/SearchTimeline",), "comments": ("/TweetDetail",), "detail": ("/TweetDetail",),
                      "author": ("/UserByScreenName",), "author_posts": ("/UserTweets", "/UserByScreenName")}[capability]
        capture = NativeReadCapture(hosts={"x.com", "api.x.com", "twitter.com", "api.twitter.com"}, paths=operations,
            request_keys={"cursor", "rawQuery", "focalTweetId", "tweetId", "userId", "screen_name", "count"})
        worker, page = None, None
        try:
            worker = _new_browser_worker()
            worker.connect()
            inject_into_context(worker._context, "x")
            page = worker.new_page(stealth=False)
            capture.attach(page)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1200)
            observed_users = {}
            def select(observation):
                request = observation["request"]
                for obj in observation["objects"]:
                    data = obj.get("data") if isinstance(obj, dict) else None
                    if not isinstance(data, dict):
                        continue
                    user = ((data.get("user") or {}).get("result") or {})
                    if isinstance(user, dict) and user.get("rest_id"):
                        native_handle = (user.get("core") or {}).get("screen_name") or (user.get("legacy") or {}).get("screen_name")
                        if isinstance(native_handle, str) and native_handle.casefold() == target.casefold():
                            observed_users[str(user["rest_id"])] = user
                            if capability == "author":
                                return {"user": user}
                    if capability == "author":
                        continue
                    if capability == "search" and request.get("rawQuery") != target:
                        continue
                    if capability in {"comments", "detail"} and str(request.get("focalTweetId") or request.get("tweetId") or "") != target:
                        continue
                    if capability == "author_posts" and request.get("userId") is None:
                        continue
                    if str(request.get("cursor") or "") != str((cursor or {}).get("cursor") or ""):
                        continue
                    tweets, cursors, terminated, timeline_seen = self._native_timeline(data)
                    if timeline_seen or terminated:
                        return {"tweets": tweets, "cursors": cursors, "terminated": terminated, "request": request}
                return None
            def advance(_step):
                if _x_page_failure(str(page.url), title=page.title()):
                    return False
                if include_replies and capability == "comments":
                    control = page.get_by_text(re.compile(r"^(?:Show|View|See) (?:more )?replies$|^显示更多回复$|^查看回复$", re.I)).first
                    if control.count() and control.is_visible():
                        control.click(timeout=3000)
                        return True
                return native_read_scroll(page)
            selected = capture.seek(page, select, advance, max_steps=16)
            if selected is None:
                failure = capture.failure() or {}
                code = failure.get("failure_class") or _x_page_failure(str(page.url), title=page.title()) or "NATIVE_PAGE_NOT_OBSERVED"
                return AdapterResult(success=False, error="X_" + code, metadata={
                    "failure_class": failure.get("failure_class"), "http_status": failure.get("http_status"),
                    "retry_after_seconds": failure.get("retry_after_seconds"), "pagination": {
                        "request_cursor": cursor, "next_cursor": None, "exhausted": None, "page_complete": False}})
            if capability == "author":
                user = selected["user"]
                legacy = user.get("legacy") or {}
                core = user.get("core") or {}
                return AdapterResult(success=True, notes=[CollectedNote(title=core.get("name") or legacy.get("name") or "",
                    content=legacy.get("description") or "", url=url, author_id="@" + target, author=core.get("name") or legacy.get("name") or "",
                    source_platform="x", raw_data={"engine": "x_native_profile", "username": target, "native_user_id": user.get("rest_id"),
                        "followers": optional_int(legacy.get("followers_count")), "following_count": optional_int(legacy.get("friends_count")),
                        "content_count": optional_int(legacy.get("statuses_count")), "source_observation": {"legacy": legacy, "core": core, "rest_id": user.get("rest_id")},
                        "native_author_aliases": [{"kind": "rest_id", "value": str(user["rest_id"])}, {"kind": "username", "value": target}]})], raw_count=1)
            notes, seen = [], set()
            for tweet in selected["tweets"]:
                note = self._native_note(tweet)
                if note is None or note.raw_data["tweet_id"] in seen:
                    continue
                tid = note.raw_data["tweet_id"]
                if capability == "detail" and tid != target:
                    continue
                if capability == "comments":
                    parent = note.raw_data.get("parent_comment_id")
                    if tid == target or not parent or (parent != target and note.raw_data.get("conversation_id") != target):
                        continue
                    note.title = ""
                    note.raw_data.update({"type": "comment", "platform_comment_id": tid, "parent_content_id": target,
                                          "parent_comment_id": None if parent == target else parent, "reply_to_comment_id": None if parent == target else parent})
                if capability == "author_posts":
                    if note.raw_data.get("username", "").casefold() != target.casefold():
                        continue
                    request_id = str(selected["request"].get("userId") or "")
                    if request_id != str(note.raw_data.get("native_user_id") or ""):
                        return AdapterResult(success=False, error="X_AUTHOR_HISTORY_IDENTITY_MISMATCH")
                    note.raw_data["author_history_binding"] = {"requested_id": target, "native_user_id": request_id}
                seen.add(tid)
                notes.append(note)
            if capability == "detail" and len(notes) != 1:
                return AdapterResult(success=False, error="X_PAGE_FAILURE:DETAIL_NOT_RETURNED")
            if capability == "author_posts" and not notes and str(selected["request"].get("userId") or "") not in observed_users:
                return AdapterResult(success=False, error="X_PAGE_FAILURE:IDENTITY_MISMATCH")
            window = native_page_window(notes, limit=limit, cursor=cursor,
                                        identities=[note.raw_data['tweet_id'] for note in notes])
            complete = window['page_complete']
            native_next = next((item for item in selected["cursors"] if item.get("kind") == "Bottom"), None)
            if native_next and cursor and native_next["cursor"] == cursor["cursor"]:
                native_next = None
            base_cursor = {key: value for key, value in (cursor or {}).items() if key not in {'item_offset', 'page_sha256'}}
            base_cursor.setdefault('cursor', '')
            return AdapterResult(success=True, notes=window['rows'], raw_count=len(window['rows']), metadata={"pagination": {
                "request_cursor": cursor, "next_cursor": native_next if complete else {**base_cursor, **window['next_window']},
                "exhausted": False if not complete else True if selected["terminated"] and native_next is None else False if native_next else None,
                "page_complete": complete, "native_thread_cursors": selected["cursors"] if capability == "comments" else [],
                **{key: window[key] for key in ('window_start', 'window_end', 'observed_native_rows', 'page_sha256', 'page_identity_basis')},
                "coverage_scope": "PROVIDER_VISIBLE_NATIVE_TIMELINE_PAGE", "resume_strategy": "OFFICIAL_PAGE_NATIVE_CURSOR_SEEK",
                "observed_prior_native_responses": selected["observed_prior_native_responses"], "partial_reason": "REQUESTED_LIMIT_REACHED" if not complete else None}})
        except NativePageWindowError as exc:
            return AdapterResult(success=False, raw_count=None, error='X_' + str(exc), metadata={
                'failure_class': str(exc), 'pagination': {'request_cursor': cursor, 'next_cursor': None,
                    'exhausted': None, 'page_complete': False, 'resume_requires_fresh_page': True}})
        except Exception as exc:
            logger.warning("X native read failed error_type=%s", type(exc).__name__)
            return AdapterResult(success=False, error=_x_failure_code(exc, phase="worker" if page is None else "page"))
        finally:
            capture.close()
            self._close_worker_page(worker, page)

    def author_posts(self, author_id, *, max_results=20, cursor=None, **kwargs):
        return self._native_read("author_posts", str(author_id or "").lstrip("@"), max_results, cursor=cursor)

    def creator(self, username: str) -> AdapterResult:
        """Read a creator profile through the explicitly configured X worker."""
        handle = str(username or "").strip().lstrip("@")
        if not re.fullmatch(r"[A-Za-z0-9_]{1,15}", handle):
            return AdapterResult(success=False, error="X creator requires a valid handle")
        return self._native_read("author", handle, 1)

    def _creator_dom_observation(self, handle):
        """Retained DOM field parser; native author identity owns admission."""
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
            return AdapterResult(success=False, error=failure or _x_failure_code(exc, phase="page"))
        finally:
            self._close_worker_page(worker, page)
