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

_SAFE_X_WORKER_FAILURES = {
    "READONLY_WORKER_NOT_REGISTERED": "X not_configured: read-only worker is not registered",
    "READONLY_WORKER_NOT_CONFIGURED": "X not_configured: read-only worker is not configured",
    "BROWSER_PROFILE_OWNER_UNAVAILABLE": "X not_configured: browser worker profile owner is unavailable",
    "READONLY_WORKER_BOUNDARY_INVALID": "X blocked: read-only worker boundary is invalid",
    "BROWSER_WORKER_KERNEL_OR_IDENTITY_UNVERIFIED": "X blocked: browser worker identity or kernel is unverified",
    "PROTECTED_PROFILE_FORBIDDEN": "X blocked: protected browser profile is forbidden",
    "READONLY_WORKER_PROFILE_UNAVAILABLE": "X provider_unavailable: read-only worker profile is unavailable",
    "READONLY_WORKER_PROFILE_OR_MODE_UNAVAILABLE": "X provider_unavailable: read-only worker profile or mode is unavailable",
    "READONLY_WORKER_PROFILE_MODE_OR_KERNEL_UNAVAILABLE": "X provider_unavailable: read-only worker profile, mode, or kernel is unavailable",
    "BROWSER_WORKER_PROFILE_OR_MODE_UNAVAILABLE": "X provider_unavailable: browser worker profile or mode is unavailable",
}

_SAFE_X_CONFIGURATION_FAILURES = {
    "X_READONLY_CDP_URL must be the fixed loopback worker endpoint":
        "X not_configured: read-only worker endpoint is not configured",
    "X_READONLY worker requires explicit account opt-in":
        "X not_configured: read-only worker requires explicit account opt-in",
    "X_READONLY worker profile is not bound to the configured loopback port":
        "X provider_unavailable: read-only worker profile is unavailable",
}


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


def _safe_x_exception_class(exc: Exception) -> str:
    name = type(exc).__name__
    return name if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", name) else "Exception"


def _safe_x_worker_failure(exc: Exception) -> str:
    """Map only known worker codes and fixed local configuration errors."""
    if not isinstance(exc, RuntimeError):
        return ""
    args = getattr(exc, "args", ())
    message = args[0] if len(args) == 1 and isinstance(args[0], str) else ""
    match = re.match(r"^([A-Z][A-Z0-9_]*)(?::|\s|$)", message)
    if match:
        failure = _SAFE_X_WORKER_FAILURES.get(match.group(1))
        if failure:
            return failure
    return _SAFE_X_CONFIGURATION_FAILURES.get(message, "")


def _safe_x_browser_failure(exc: Exception, *, url: str = "", title: str = "",
                            classify_navigation_error: bool = False) -> str:
    """Return a classified X failure without exposing arbitrary exception text."""
    worker_failure = _safe_x_worker_failure(exc)
    if worker_failure:
        return worker_failure

    page_failure = _x_page_failure(url, title=title)
    if page_failure:
        return page_failure

    browser_error = ""
    if classify_navigation_error:
        exception_type = type(exc)
        exception_module = getattr(exception_type, "__module__", "")
        if isinstance(exception_module, str) and exception_module.startswith("playwright."):
            browser_error = str(exc)
        elif isinstance(exc, RuntimeError):
            args = getattr(exc, "args", ())
            message = args[0] if len(args) == 1 and isinstance(args[0], str) else ""
            if re.search(r"\bnet::ERR_[A-Z0-9_]+\b", message, flags=re.IGNORECASE):
                browser_error = message
    if browser_error:
        page_failure = _x_page_failure(url, error=browser_error, title=title)
        if page_failure:
            return page_failure

    return f"X collection_error: {_safe_x_exception_class(exc)}"


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
               skip_tweet_ids=None) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        try:
            skip_tweet_ids = self._normalize_skip_tweet_ids(skip_tweet_ids)
        except ValueError as exc:
            return AdapterResult(success=False, error=str(exc))
        return self._search_browser(
            keyword, max_results, skip_tweet_ids=skip_tweet_ids,
        )

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
                message = _safe_x_browser_failure(
                    exc, url=str(getattr(page, "url", "") or ""),
                    classify_navigation_error=True,
                )
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
            exception_class = _safe_x_exception_class(e)
            safe_display_exception = RuntimeError(
                f"REDACTED_ORIGINAL_EXCEPTION:{exception_class}"
            )
            logger.error(
                "X 浏览器采集异常 error_type=%s",
                exception_class,
                exc_info=(RuntimeError, safe_display_exception, e.__traceback__),
            )
            failure = _safe_x_browser_failure(e, url=str(getattr(page, "url", "") or ""))
            return attach_continuation_metadata(
                AdapterResult(success=False, notes=notes, error=failure,
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

    def _open_readonly_page(self, url: str, wait_seconds: float, *, safe_error_classification: bool = False):
        worker = None
        page = None
        failure_stage = "worker_setup"
        try:
            worker = _new_browser_worker()
            worker.connect()
            inject_into_context(worker._context, "x")
            page = worker.new_page(stealth=False)
            failure_stage = "navigation"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            failure_stage = "post_navigation"
            worker.pause(wait_seconds, wait_seconds)
            page_title = page.title()
            failure = _x_page_failure(str(getattr(page, "url", "") or ""), title=page_title)
            return worker, page, failure
        except Exception as exc:
            page_url = str(getattr(page, "url", "") or "")
            self._close_worker_page(worker, page)
            if safe_error_classification:
                failure = _safe_x_browser_failure(
                    exc, url=page_url, classify_navigation_error=(failure_stage == "navigation"),
                )
            else:
                failure = _x_page_failure(page_url, "", str(exc)) or "X network error"
            return None, None, failure

    def detail(self, tweet_id: str) -> AdapterResult:
        """Read a post through the explicitly configured X read-only worker."""
        url = self._canonical_status_url(tweet_id)
        if not url:
            return AdapterResult(success=False, error="X detail requires a numeric post ID or canonical x.com status URL")
        requested_tweet_id = self._status_id_from_url(url)
        if not requested_tweet_id:
            return AdapterResult(success=False, error="X detail requires the exact observed numeric post ID")
        worker, page, failure = self._open_readonly_page(url, 4.0, safe_error_classification=True)
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
            failure = _safe_x_browser_failure(exc, url=str(getattr(page, "url", "") or ""))
            return AdapterResult(success=False, error=failure)
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
