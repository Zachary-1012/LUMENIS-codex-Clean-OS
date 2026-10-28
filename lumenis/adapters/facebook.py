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
import hashlib
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from .base import BaseAdapter, AdapterResult, CollectedNote, optional_int
from .human_browser import (HumanBrowser, NativeReadCapture, configured_readonly_worker_url,
                            NativePageWindowError, native_json_nodes, native_page_json, native_page_window,
                            native_read_scroll, validate_native_page_window_cursor)
from .cookie_vault import inject_into_context

logger = logging.getLogger(__name__)


class FacebookAdapter(BaseAdapter):
    """Facebook 搜索适配器（浏览器 CDP + cookie，只读采集）"""

    platform_name = "facebook"
    platform_display = "Facebook"

    _OFFICIAL_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com"}
    _NATIVE_POST_ID = re.compile(r"[A-Za-z0-9]+")
    _DETAIL_BODY_SELECTOR = '[data-ad-preview="message"], [data-ad-comet-preview="message"]'
    _DETAIL_EXPANDER_SELECTOR = 'button, [role="button"]'
    _DETAIL_EXPANDER_LABELS = frozenset({"see more", "see more…", "see more...", "查看更多", "查看全部", "显示更多"})
    _DETAIL_EXPANDER_SCAN_LIMIT = 20

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
        """Resolve optional saved credentials through the existing vault owner."""
        from .cookie_vault import to_cookie_string
        return to_cookie_string("facebook")

    @classmethod
    def observed_post_permalink(cls, value: str, base_url: str = "") -> dict | None:
        """Return a sanitized identity only for an observed Facebook post URL."""
        if not isinstance(value, str) or not value.strip() or len(value) > 4096:
            return None
        candidate = value.strip()
        if base_url:
            candidate = urljoin(base_url, candidate)
        try:
            parsed = urlsplit(candidate)
            host = (parsed.hostname or "").lower().rstrip(".")
            port = parsed.port
        except ValueError:
            return None
        if (parsed.scheme.lower() != "https" or host not in cls._OFFICIAL_HOSTS
                or parsed.username is not None or parsed.password is not None
                or port not in (None, 443) or "\\" in parsed.path or "//" in parsed.path):
            return None

        path = parsed.path or "/"
        if any(part in {".", ".."} for part in path.split("/")):
            return None
        post_match = re.search(r"(?:^|/)posts/([A-Za-z0-9]+)$", path.rstrip("/"))
        if post_match:
            post_id = post_match.group(1)
            canonical = urlunsplit(("https", "www.facebook.com", path.rstrip("/"), "", ""))
            return {"post_id": post_id, "url": canonical, "id_locator": "permalink_path.posts"}

        if path.rstrip("/").lower() not in {"/permalink.php", "/story.php"}:
            return None
        try:
            query = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=False)
        except ValueError:
            return None
        story_values = [item for key, item in query if key == "story_fbid"]
        page_values = [item for key, item in query if key == "id"]
        if len(story_values) != 1 or not cls._NATIVE_POST_ID.fullmatch(story_values[0]):
            return None
        if len(page_values) > 1:
            return None
        post_id = story_values[0]
        identity_query = [("story_fbid", post_id)]
        page_id = page_values[0] if page_values else ""
        if page_id and cls._NATIVE_POST_ID.fullmatch(page_id):
            identity_query.append(("id", page_id))
        canonical_path = path.rstrip("/")
        canonical = urlunsplit(("https", "www.facebook.com", canonical_path,
                                urlencode(identity_query), ""))
        return {"post_id": post_id, "url": canonical,
                "id_locator": "permalink_query.story_fbid"}

    @classmethod
    def _sanitize_public_facebook_url(cls, value: str, base_url: str = "") -> str:
        """Keep a public Facebook URL's path while dropping transport parameters."""
        if not isinstance(value, str) or not value.strip() or len(value) > 4096:
            return ""
        try:
            candidate = urljoin(base_url, value.strip()) if base_url else value.strip()
            parsed = urlsplit(candidate)
            host = (parsed.hostname or "").lower().rstrip(".")
            port = parsed.port
        except ValueError:
            return ""
        if (parsed.scheme.lower() != "https" or host not in cls._OFFICIAL_HOSTS
                or parsed.username is not None or parsed.password is not None
                or port not in (None, 443) or "\\" in parsed.path or "//" in parsed.path):
            return ""
        identity = cls.observed_post_permalink(candidate)
        if identity:
            return identity["url"]
        return urlunsplit(("https", "www.facebook.com", parsed.path or "/", "", ""))

    @staticmethod
    def _is_non_post_media_url(value: str) -> bool:
        try:
            path = urlsplit(value).path.lower()
        except ValueError:
            return False
        return (any(marker in path for marker in ("/videos/", "/photos/", "/reel/", "/reels/", "/photo/"))
                or path.endswith(("/video.php", "/photo.php"))
                or path.rstrip("/") == "/watch")

    @classmethod
    def _post_permalink_from_card(cls, card, base_url: str) -> dict | None:
        try:
            anchors = card.query_selector_all(
                'a[href*="/posts/"], a[href*="/permalink.php"], a[href*="/story.php"]'
            )
        except Exception:
            return None
        for anchor in anchors:
            try:
                href = anchor.get_attribute("href") or ""
            except Exception:
                continue
            identity = cls.observed_post_permalink(href, base_url=base_url)
            if identity:
                return {**identity, "permalink_locator": "article a[href]"}
        return None

    @staticmethod
    def _native_publish_time(card) -> tuple[str, str]:
        """Read only native time attributes; never infer a year or capture time."""
        try:
            for selector in ("time[datetime]",):
                for element in card.query_selector_all(selector):
                    value = element.get_attribute("datetime")
                    if isinstance(value, str) and value.strip():
                        return value.strip(), selector + "@datetime"
            seen = set()
            for selector in ("abbr[data-utime]", "[data-utime]"):
                for element in card.query_selector_all(selector):
                    marker = id(element)
                    if marker in seen:
                        continue
                    seen.add(marker)
                    value = element.get_attribute("data-utime")
                    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value.strip()):
                        continue
                    try:
                        epoch = int(value.strip())
                        converted = datetime.fromtimestamp(epoch, tz=timezone.utc)
                    except (OverflowError, OSError, ValueError):
                        continue
                    return converted.isoformat().replace("+00:00", "Z"), selector + "@data-utime"
        except Exception:
            return "", ""
        return "", ""

    @staticmethod
    def _audience_observation(card) -> dict:
        known = {
            "public": "PUBLIC", "shared with public": "PUBLIC", "公开": "PUBLIC",
            "公开发布": "PUBLIC", "friends": "LIMITED", "shared with friends": "LIMITED",
            "好友": "LIMITED", "仅好友": "LIMITED", "friends of friends": "LIMITED",
            "only me": "PRIVATE", "仅自己": "PRIVATE", "仅自己可见": "PRIVATE",
        }
        try:
            for element in card.query_selector_all("[aria-label], [title]"):
                label = element.get_attribute("aria-label") or element.get_attribute("title") or ""
                normalized = " ".join(label.split()).casefold()
                audience = known.get(normalized)
                if audience:
                    return {"status": "OBSERVED", "value": audience, "display": label,
                            "source_locator": "article [aria-label|title]"}
        except Exception:
            pass
        return {"status": "UNKNOWN", "value": None, "display": None, "source_locator": None}

    @classmethod
    def _sanitize_media_url(cls, value: str, base_url: str) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > 8192:
            return ""
        try:
            candidate = urljoin(base_url, value.strip())
            parsed = urlsplit(candidate)
            host = (parsed.hostname or "").lower().rstrip(".")
            port = parsed.port
        except ValueError:
            return ""
        owned_media_host = (host in cls._OFFICIAL_HOSTS or host.endswith(".fbcdn.net")
                            or host == "fbcdn.net" or host.endswith(".fbsbx.com")
                            or host == "fbsbx.com")
        if (parsed.scheme.lower() != "https" or not owned_media_host
                or parsed.username is not None or parsed.password is not None
                or port not in (None, 443)):
            return ""
        return urlunsplit(("https", host, parsed.path or "/", "", ""))

    @classmethod
    def _media_hints(cls, card, base_url: str) -> list[dict]:
        hints = []
        seen = set()
        selectors = (
            ("image", 'img[data-visualcompletion="media-vc-image"][src]', "src"),
            ("image", 'img[data-imgperflogname="FeedImage"][src]', "src"),
            ("video", "video[src]", "src"),
            ("video", "video source[src]", "src"),
            ("image", "video[poster]", "poster"),
        )
        for media_type, selector, attribute in selectors:
            try:
                elements = card.query_selector_all(selector)
            except Exception:
                continue
            for element in elements:
                try:
                    hint = cls._sanitize_media_url(element.get_attribute(attribute) or "", base_url)
                except Exception:
                    continue
                if hint and hint not in seen:
                    seen.add(hint)
                    hints.append({"type": media_type, "url_hint": hint,
                                  "source_locator": selector + "@" + attribute})
        return hints

    @staticmethod
    def _page_failure_state(page) -> str:
        try:
            current = urlsplit(page.url)
            host = (current.hostname or "").lower().rstrip(".")
            path = current.path.lower()
        except Exception:
            return "PROVIDER_UNAVAILABLE: INVALID_FINAL_URL"
        if current.scheme.lower() != "https" or host not in FacebookAdapter._OFFICIAL_HOSTS:
            return "IDENTITY_MISMATCH: FOREIGN_FINAL_URL"
        if any(part in path for part in ("/checkpoint", "/challenge", "/captcha")):
            return "RISK_WARNING: VERIFICATION_REQUIRED"
        if any(part in path for part in ("/login", "/signin")):
            return "SESSION_EXPIRED: LOGIN_REQUIRED"
        try:
            body_text = page.locator("body").inner_text(timeout=3000).casefold()
        except Exception:
            body_text = ""
        if any(term in body_text for term in (
                "security check", "confirm your identity", "unusual activity", "captcha",
                "checkpoint", "请完成安全检查", "确认你的身份", "验证你的身份", "异常活动")):
            return "RISK_WARNING: VERIFICATION_REQUIRED"
        if any(term in body_text for term in (
                "log into facebook", "log in or sign up", "you must log in",
                "登录 facebook", "登录或注册", "请先登录")):
            return "SESSION_EXPIRED: LOGIN_REQUIRED"
        if any(term in body_text for term in (
                "this content isn't available", "content isn't available right now",
                "this page isn't available", "此内容暂时不可用", "此内容目前不可用")):
            return "BLOCKED: CONTENT_UNAVAILABLE"
        return ""

    @staticmethod
    def _exception_error(exc: Exception) -> str:
        name = type(exc).__name__.upper()
        if "TIMEOUT" in name:
            return "PROVIDER_UNAVAILABLE: TIMEOUT"
        if any(marker in name for marker in ("CLOSED", "CONNECTION", "BROWSER", "TARGET")):
            return "PROVIDER_UNAVAILABLE: WORKER_DISCONNECTED"
        return "PROVIDER_UNAVAILABLE: " + (name if re.fullmatch(r"[A-Z0-9_]+", name) else "BROWSER_ERROR")

    def search(self, keyword: str, max_results: int = 20, *, cursor=None) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        try:
            limit = min(20, max(0, int(max_results)))
        except (TypeError, ValueError, OverflowError):
            limit = 20
        if limit == 0:
            return AdapterResult(success=True, notes=[], raw_count=0)
        return self._native_read('search', keyword.strip(), limit, cursor=cursor)

    def _search_browser(self, keyword: str, max_results: int) -> AdapterResult:
        """浏览器 CDP 采集 Facebook 搜索结果。"""
        hb = None
        try:
            from .human_browser import HumanBrowser, configured_readonly_worker_url
            from .cookie_vault import inject_into_context
            from urllib.parse import quote

            hb = HumanBrowser(
                cdp_url=configured_readonly_worker_url("facebook"),
                auto_ensure=False,
                launch_url="about:blank",
            )
            hb.connect()
            inject_into_context(hb._context, "facebook")
            page = hb.new_page(stealth=False)
            url = f"https://www.facebook.com/search/top?q={quote(keyword.strip())}"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            hb.pause(5.0, 5.0)

            failure = self._page_failure_state(page)
            if failure:
                return AdapterResult(success=False, error=failure)

            # 解析搜索结果（Facebook 使用 div[role="article"]）
            cards = page.query_selector_all('div[role="article"]')
            if not cards:
                # fallback: 通用内容块
                cards = page.query_selector_all(".x1yztbdb, .x1lliihq, [data-ad-preview]")

            if not cards:
                try:
                    body_text = page.locator("body").inner_text(timeout=3000).casefold()
                except Exception:
                    body_text = ""
                if any(marker in body_text for marker in (
                        "no results", "no posts found", "没有结果", "未找到结果", "没有找到相关")):
                    return AdapterResult(success=True, notes=[], raw_count=0)
                return AdapterResult(success=False,
                                     error="PROVIDER_UNAVAILABLE: SEARCH_CARDS_NOT_OBSERVED")

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

            if notes:
                return AdapterResult(success=True, notes=notes, raw_count=len(notes))
            return AdapterResult(success=False,
                                 error="PROVIDER_UNAVAILABLE: SEARCH_CARDS_WITHOUT_POST_OBSERVATIONS")

        except Exception as e:
            logger.error("Facebook 浏览器采集失败 error_type=%s", type(e).__name__)
            return AdapterResult(success=False, error=self._exception_error(e))
        finally:
            if hb is not None:
                hb.close()

    def _parse_facebook_card(self, card, page) -> CollectedNote | None:
        """解析单个 Facebook 搜索结果卡片。"""
        # 文本内容
        text_el = card.query_selector('[data-ad-preview="message"], .x1iorvi4, .x1pi30zi')
        content = text_el.inner_text().strip() if text_el else ""
        body_locator = '[data-ad-preview="message"], .x1iorvi4, .x1pi30zi'

        # 作者
        author_el = card.query_selector('h3 a, .xt0psk2 a, [role="link"] span')
        author = author_el.inner_text().strip() if author_el else ""

        # Only a true observed post permalink supplies a native post identity.
        url = ""
        post_identity = self._post_permalink_from_card(card, page.url)
        post_id = post_identity.get("post_id") if post_identity else None
        if post_identity:
            url = post_identity["url"]

        non_post_media_permalink = False
        if not post_identity:
            try:
                for link in card.query_selector_all("a[href]"):
                    href = link.get_attribute("href") or ""
                    safe_url = self._sanitize_public_facebook_url(href, page.url)
                    if not safe_url or not self._is_non_post_media_url(safe_url):
                        continue
                    url = safe_url
                    non_post_media_permalink = True
                    break
            except Exception:
                pass

        # 互动数据
        likes_selector = 'span[aria-label*="赞"], .x193iq5w span'
        comments_selector = 'a[href*="comments"], span[aria-label*="评论"]'
        shares_selector = 'span[aria-label*="分享"], a[href*="shares"]'
        likes, likes_display = self._extract_metric_observation(card, likes_selector)
        comments, comments_display = self._extract_metric_observation(card, comments_selector)
        shares, shares_display = self._extract_metric_observation(card, shares_selector)

        publish_date, publish_time_locator = self._native_publish_time(card)
        media_hints = self._media_hints(card, page.url)
        audience = self._audience_observation(card)

        # Search-card text is a preview only; it is not a detail body.
        title = content[:80].replace("\n", " ") if content else ""

        if not title and not content and not post_identity:
            return None

        return CollectedNote(
            title=title[:200],
            content=content,
            url=url,
            author=author,
            author_id="",
            publish_date=publish_date,
            likes=likes,
            comments=comments,
            collects=None,
            shares=shares,
            cover="",
            source_platform="facebook",
            raw_data={
                "author": author, "url": url,
                "post_id": post_id,
                "post_id_status": ("OBSERVED" if post_id else
                                   "UNAVAILABLE_NON_POST_PERMALINK" if non_post_media_permalink else "NOT_OBSERVED"),
                "post_id_locator": post_identity.get("id_locator") if post_identity else None,
                "post_permalink_locator": post_identity.get("permalink_locator") if post_identity else None,
                "body_kind": "SEARCH_PREVIEW",
                "body_status": "SEARCH_PREVIEW_ONLY" if content else "NOT_OBSERVED",
                "body_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest() if content else None,
                "body_locator": body_locator if content else None,
                "body_state": "VISIBLE_DOM_TEXT_COMPLETENESS_UNKNOWN" if content else "NOT_OBSERVED",
                "native_time": publish_date or None,
                "native_time_locator": publish_time_locator or None,
                "native_time_status": "OBSERVED" if publish_date else "NOT_OBSERVED",
                "audience_observation": audience,
                "metric_display": {"likes": likes_display, "comments": comments_display,
                                   "shares": shares_display},
                "metric_locators": {"likes": likes_selector, "comments": comments_selector,
                                    "shares": shares_selector},
                "media_hints": media_hints,
                "media_state": "URL_HINTS_ONLY" if media_hints else "NOT_OBSERVED",
                "media_bytes_saved": False,
                "artifact_created": False,
            },
        )

    @staticmethod
    def _parse_exact_metric(value: str) -> int | None:
        """Accept exact count labels, preserving compact displays as unknown."""
        match = re.fullmatch(
            r"(0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)"
            r"(?:\s*(?:likes?|comments?|shares?|reactions?|赞|点赞|条评论|评论|次分享|分享))?",
            value, flags=re.IGNORECASE,
        )
        return int(match.group(1).replace(",", "")) if match else None

    @classmethod
    def _extract_metric_observation(cls, card, selector: str) -> tuple[int | None, dict | None]:
        """Retain the original label without inventing a count from its digits."""
        try:
            el = card.query_selector(selector)
            if not el:
                return None, None
            label = el.get_attribute("aria-label")
            label = label.strip() if isinstance(label, str) else ""
            text = el.inner_text()
            text = text.strip() if isinstance(text, str) else ""
            display = {key: value for key, value in (("aria_label", label), ("text", text)) if value} or None
            count = cls._parse_exact_metric(label) if label else None
            if count is None and text:
                count = cls._parse_exact_metric(text)
            return count, display
        except Exception:
            return None, None

    @classmethod
    def _extract_metric(cls, card, selector: str) -> int | None:
        return cls._extract_metric_observation(card, selector)[0]

    def detail(self, post_id: str) -> AdapterResult:
        """Read one exact Facebook post permalink in the registered worker."""
        requested = self.observed_post_permalink(post_id)
        if not requested:
            return AdapterResult(success=False, error="IDENTITY_MISMATCH: INVALID_POST_PERMALINK")

        hb = None
        try:
            from .human_browser import HumanBrowser, configured_readonly_worker_url
            from .cookie_vault import inject_into_context

            hb = HumanBrowser(
                cdp_url=configured_readonly_worker_url("facebook"),
                auto_ensure=False,
                launch_url="about:blank",
            )
            hb.connect()
            inject_into_context(hb._context, "facebook")
            page = hb.new_page(stealth=False)
            page.goto(requested["url"], wait_until="domcontentloaded", timeout=30000)
            hb.pause(4.0, 4.0)

            failure = self._page_failure_state(page)
            if failure:
                return AdapterResult(success=False, error=failure)
            final_identity = self.observed_post_permalink(page.url)
            if not final_identity or final_identity["post_id"] != requested["post_id"]:
                return AdapterResult(success=False, error="IDENTITY_MISMATCH: FINAL_URL_POST_ID_MISMATCH")

            matching_note = None
            matching_article_seen = False
            articles = page.query_selector_all('div[role="article"]')
            for article in articles:
                identity = self._post_permalink_from_card(article, page.url)
                if not identity or identity["post_id"] != requested["post_id"]:
                    continue
                matching_article_seen = True
                note, parse_error = self._parse_facebook_detail_article(article, page, requested["post_id"])
                if parse_error:
                    diagnostics = ({"post_id": requested["post_id"],
                                    "body_status": "NATIVE_BODY_NOT_OBSERVED"}
                                   if parse_error.startswith("DETAIL_NOT_RETURNED:") else {})
                    return AdapterResult(success=False, error=parse_error, diagnostics=diagnostics)
                if note and note.raw_data.get("post_id") == requested["post_id"]:
                    matching_note = note
                    break

            if matching_note:
                matching_note.raw_data["detail_source_url"] = requested["url"]
                matching_note.raw_data["detail_post_id_status"] = "OBSERVED_AND_MATCHED"
                matching_note.raw_data["detail_post_id_locator"] = "article a[href] (exact requested native id)"
                return AdapterResult(success=True, notes=[matching_note], raw_count=1)
            if matching_article_seen:
                return AdapterResult(
                    success=False,
                    error="DETAIL_NOT_RETURNED: NATIVE_POST_BODY_NOT_OBSERVED",
                    diagnostics={"post_id": requested["post_id"],
                                 "body_status": "NATIVE_BODY_NOT_OBSERVED"},
                )
            if articles:
                return AdapterResult(success=False, error="IDENTITY_MISMATCH: TARGET_ARTICLE_NOT_OBSERVED")
            return AdapterResult(success=False, error="DETAIL_NOT_RETURNED: TARGET_ARTICLE_NOT_OBSERVED")
        except Exception as e:
            logger.error("Facebook 详情读取失败 error_type=%s", type(e).__name__)
            return AdapterResult(success=False, error=self._exception_error(e))
        finally:
            if hb is not None:
                hb.close()

    @classmethod
    def _detail_article_matches(cls, article, page_url: str, expected_post_id: str) -> bool:
        page_identity = cls.observed_post_permalink(page_url)
        article_identity = cls._post_permalink_from_card(article, page_url)
        return bool(
            page_identity and article_identity
            and page_identity["post_id"] == expected_post_id
            and article_identity["post_id"] == expected_post_id
        )

    @classmethod
    def _expand_detail_post_body(cls, article, page) -> tuple[str, dict]:
        """Expand one explicit control nested in the observed post body."""
        observation = {"status": "NOT_OBSERVED", "label": None, "click_count": 0}
        try:
            body_element = article.query_selector(cls._DETAIL_BODY_SELECTOR)
            before = body_element.inner_text().strip() if body_element else ""
        except Exception:  # noqa: BLE001 - optional browser-driver boundary; explicit failure state
            return "", {**observation, "status": "BODY_READ_FAILED"}
        if not isinstance(before, str) or not before:
            return "", {**observation, "status": "BODY_NOT_OBSERVED"}
        try:
            controls = body_element.query_selector_all(cls._DETAIL_EXPANDER_SELECTOR)
        except Exception:  # noqa: BLE001 - optional browser-driver boundary; explicit failure state
            return before, {**observation, "status": "EXPANDER_SCAN_FAILED"}
        controls = list(controls or [])
        if len(controls) > cls._DETAIL_EXPANDER_SCAN_LIMIT:
            return before, {**observation, "status": "EXPANDER_SCAN_LIMIT_REACHED"}
        for control in controls:
            matched_label = None
            try:
                values = (control.inner_text(), control.get_attribute("aria-label"))
            except Exception:  # noqa: BLE001 - optional browser-driver boundary; explicit failure state
                logger.debug("Facebook detail control label was not readable")
                continue
            for value in values:
                label = " ".join(value.split()).casefold().rstrip(" .…") if isinstance(value, str) else ""
                if len(label) <= 40 and label in cls._DETAIL_EXPANDER_LABELS:
                    matched_label = label
                    break
            if matched_label is None:
                continue
            try:
                control.click(timeout=2000)
            except Exception:  # noqa: BLE001 - optional browser-driver boundary; explicit failure state
                return before, {**observation, "status": "EXPANSION_FAILED", "label": matched_label}
            render_wait = "STATE_CHANGE_NOT_OBSERVED"
            try:
                changed = page.wait_for_function(
                    "([element, before]) => !element.isConnected || element.innerText.trim() !== before",
                    arg=[body_element, before], timeout=2000,
                )
                changed.dispose()
                render_wait = "BODY_CHANGED_OR_REPLACED"
            except Exception:  # noqa: BLE001 - optional browser-driver boundary; explicit failure state
                render_wait = "STATE_CHANGE_NOT_OBSERVED"
            try:
                expanded_element = article.query_selector(cls._DETAIL_BODY_SELECTOR)
                after = expanded_element.inner_text().strip() if expanded_element else ""
            except Exception:  # noqa: BLE001 - optional browser-driver boundary; explicit failure state
                return before, {
                    **observation, "status": "EXPANSION_READ_FAILED", "label": matched_label,
                    "click_count": 1, "render_wait": render_wait,
                }
            if isinstance(after, str) and len(after) > len(before):
                return after, {
                    **observation, "status": "EXPANDED", "label": matched_label,
                    "click_count": 1, "render_wait": render_wait,
                }
            return before, {
                **observation, "status": "EXPANSION_UNVERIFIED", "label": matched_label,
                "click_count": 1, "render_wait": render_wait,
            }
        try:
            article_controls = list(article.query_selector_all(cls._DETAIL_EXPANDER_SELECTOR) or [])
        except Exception:  # noqa: BLE001 - optional browser-driver boundary; explicit failure state
            return before, {**observation, "status": "EXPANDER_SCAN_FAILED"}
        if len(article_controls) > cls._DETAIL_EXPANDER_SCAN_LIMIT:
            return before, {**observation, "status": "EXPANDER_SCAN_LIMIT_REACHED"}
        for control in article_controls:
            try:
                values = (control.inner_text(), control.get_attribute("aria-label"))
            except Exception:  # noqa: BLE001 - optional browser-driver boundary; explicit failure state
                logger.debug("Facebook detail control label was not readable")
                continue
            for value in values:
                label = " ".join(value.split()).casefold().rstrip(" .…") if isinstance(value, str) else ""
                if len(label) <= 40 and label in cls._DETAIL_EXPANDER_LABELS:
                    return before, {**observation, "status": "EXPANSION_UNVERIFIED", "label": label}
        return before, {**observation, "status": "NO_EXPANSION_CONTROL"}

    def _parse_facebook_detail_article(self, article, page, requested_post_id: str) -> tuple[CollectedNote | None, str]:
        if not self._detail_article_matches(article, page.url, requested_post_id):
            return None, "IDENTITY_MISMATCH: TARGET_ARTICLE_PRE_READ_ID_MISMATCH"
        _, expansion = self._expand_detail_post_body(article, page)
        failure = self._page_failure_state(page)
        if failure:
            return None, failure
        after_identity = self._post_permalink_from_card(article, page.url)
        if (not after_identity or after_identity.get("post_id") != requested_post_id
                or not self._detail_article_matches(article, page.url, requested_post_id)):
            return None, "IDENTITY_MISMATCH: TARGET_ARTICLE_POST_READ_ID_MISMATCH"
        if expansion.get("status") not in {"EXPANDED", "NO_EXPANSION_CONTROL"}:
            return None, "DETAIL_NOT_RETURNED: NATIVE_POST_BODY_NOT_OBSERVED"
        try:
            body_element = article.query_selector(self._DETAIL_BODY_SELECTOR)
            native_body = body_element.inner_text().strip() if body_element else ""
        except Exception:  # noqa: BLE001 - optional browser-driver boundary; explicit failure state
            native_body = ""
        if not native_body:
            return None, "DETAIL_NOT_RETURNED: NATIVE_POST_BODY_NOT_OBSERVED"

        # Reuse the existing native author, time, metrics and media observations,
        # then replace the search-preview body with the exact article's visible body.
        try:
            note = self._parse_facebook_card(article, page)
        except Exception as error:  # noqa: BLE001 - driver boundary; log only the error type
            logger.debug("Facebook detail card parse failed error_type=%s", type(error).__name__)
            note = None
        if not note or note.raw_data.get("post_id") != requested_post_id:
            return None, "IDENTITY_MISMATCH: TARGET_ARTICLE_POST_ID_MISMATCH"
        if not self._detail_article_matches(article, page.url, requested_post_id):
            return None, "IDENTITY_MISMATCH: TARGET_ARTICLE_POST_READ_ID_MISMATCH"
        failure = self._page_failure_state(page)
        if failure:
            return None, failure
        note.content = native_body
        note.title = native_body[:80].replace("\n", " ")
        raw = dict(note.raw_data or {})
        expansion_state = expansion.get("status")
        raw.update({
            "body_kind": "NATIVE_POST_BODY",
            "body_status": "NATIVE_DETAIL_BODY_OBSERVED_COMPLETENESS_UNKNOWN",
            "body_sha256": hashlib.sha256(native_body.encode("utf-8")).hexdigest(),
            "body_locator": self._DETAIL_BODY_SELECTOR,
            "body_state": ("EXPANDED_NATIVE_ARTICLE_DOM_COMPLETENESS_UNKNOWN"
                           if expansion_state == "EXPANDED"
                           else "NATIVE_ARTICLE_DOM_COMPLETENESS_UNKNOWN"),
            "body_expansion": expansion,
            "body_completeness": "UNKNOWN",
            "detail_post_id_status": "OBSERVED_AND_MATCHED",
            "detail_post_id_locator": "article a[href] (exact requested native id)",
            "native_identity": {
                "post_id": requested_post_id,
                "requested_post_id": requested_post_id,
                "observed_post_id": requested_post_id,
                "status": "OBSERVED_MATCH",
                "locator": after_identity.get("permalink_locator"),
            },
        })
        note.raw_data = raw
        return note, ""

    def comments(self, post_id: str, max_comments: int = 20, *, cursor=None, include_replies=False, source_url=None) -> AdapterResult:
        """Facebook 评论采集（浏览器 CDP，滚动加载）。"""
        identity = self.observed_post_permalink(source_url or post_id)
        if not identity:
            return AdapterResult(success=False, error="FACEBOOK_INVALID_POST_PERMALINK")
        if source_url:
            original = self.observed_post_permalink(post_id) if isinstance(post_id, str) and post_id.startswith('https://') else None
            if (original and original['post_id'] != identity['post_id']
                    or original is None and str(post_id) != identity['post_id']):
                return AdapterResult(success=False, error='FACEBOOK_COMMENT_PARENT_IDENTITY_MISMATCH')
        return self._native_read("comments", identity["post_id"], max_comments,
                                 source_url=identity["url"], cursor=cursor, include_replies=include_replies)

    def _comments_dom_observation(self, post_id, max_comments):
        hb = None
        try:
            from .human_browser import HumanBrowser, configured_readonly_worker_url
            from .cookie_vault import inject_into_context

            hb = HumanBrowser(
                cdp_url=configured_readonly_worker_url("facebook"),
                auto_ensure=False,
                launch_url="about:blank",
            )
            hb.connect()
            inject_into_context(hb._context, "facebook")
            page = hb.new_page(stealth=False)
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
                    likes, likes_display = self._extract_metric_observation(cel, 'span[aria-label*="赞"]')
                    notes.append(CollectedNote(
                        title="",
                        content=content_el.inner_text().strip() if content_el else "",
                        url="",
                        author=author_el.inner_text().strip() if author_el else "",
                        author_id="",
                        publish_date="",
                        likes=likes,
                        comments=None,
                        collects=None,
                        shares=None,
                        cover="",
                        source_platform="facebook_comment",
                        raw_data={"metric_display": {"likes": likes_display}},
                    ))
                except Exception:
                    continue

            return AdapterResult(success=True, notes=notes, raw_count=len(notes))
        except Exception as e:
            logger.error("Facebook 评论读取失败 error_type=%s", type(e).__name__)
            return AdapterResult(success=False, error=self._exception_error(e))
        finally:
            if hb is not None:
                hb.close()

    def creator(self, username: str) -> AdapterResult:
        """Facebook 主页/用户信息采集。"""
        target = str(username or "").strip()
        if re.fullmatch(r"[A-Za-z0-9.]{1,100}", target) is None:
            return AdapterResult(success=False, error="FACEBOOK_AUTHOR_ID_INVALID")
        return self._native_read("author", target, 1)

    def _creator_dom_observation(self, username):
        hb = None
        try:
            from .human_browser import HumanBrowser, configured_readonly_worker_url
            from .cookie_vault import inject_into_context

            hb = HumanBrowser(
                cdp_url=configured_readonly_worker_url("facebook"),
                auto_ensure=False,
                launch_url="about:blank",
            )
            hb.connect()
            inject_into_context(hb._context, "facebook")
            page = hb.new_page(stealth=False)
            url = f"https://www.facebook.com/{username}" if not username.startswith("http") else username
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            hb.pause(4.0, 4.0)

            name_el = page.query_selector("h1, .x1heor9g")
            name = name_el.inner_text().strip() if name_el else username

            return AdapterResult(success=True, notes=[CollectedNote(
                title=name,
                content="",
                url=url,
                author=name,
                author_id=username,
                publish_date="",
                likes=None,
                comments=None,
                collects=None,
                shares=None,
                cover="",
                source_platform="facebook_creator",
                raw_data={"username": username},
            )], raw_count=1)
        except Exception as e:
            logger.error("Facebook 主页读取失败 error_type=%s", type(e).__name__)
            return AdapterResult(success=False, error=self._exception_error(e))
        finally:
            if hb is not None:
                hb.close()

    @classmethod
    def _native_post_identity(cls, node):
        for field in ("permalink_url", "url", "story_url"):
            if isinstance(node.get(field), str):
                identity = cls.observed_post_permalink(node[field])
                if identity:
                    native_id = node.get("post_id") or node.get("legacy_fbid")
                    if native_id is not None and str(native_id).split("_")[-1] != identity["post_id"]:
                        return None
                    return identity
        native_id = node.get("post_id") or node.get("legacy_fbid")
        if isinstance(native_id, str) and re.fullmatch(r"[0-9]+_[0-9]+", native_id):
            return cls.observed_post_permalink("https://www.facebook.com/" + native_id.split("_")[0] + "/posts/" + native_id.split("_")[1])
        return None

    def _native_post_note(self, node):
        identity = self._native_post_identity(node)
        if not identity:
            return None
        sections = node.get("comet_sections") or {}
        story = ((sections.get("content") or {}).get("story") or node)
        message = story.get("message") or node.get("message") or {}
        text = message.get("text") if isinstance(message, dict) else None
        if not isinstance(text, str):
            return None
        actors = story.get("actors") or node.get("actors") or []
        owner = actors[0] if actors and isinstance(actors[0], dict) else node.get("owner") or {}
        feedback = node.get("feedback") or story.get("feedback") or {}
        hints = []
        # Only media under this exact post, never recommendation/sidebar nodes.
        for attachment in story.get("attachments") or node.get("attachments") or []:
            for media in native_json_nodes(attachment):
                native_id = media.get("id")
                for key in ("playable_url", "playable_url_quality_hd", "browser_native_hd_url", "browser_native_sd_url"):
                    value = media.get(key)
                    safe = self._sanitize_media_url(value, identity["url"]) if isinstance(value, str) else ""
                    if safe: hints.append({"kind": "video", "url": safe, "native_media_id": native_id, "locator": "$.attachments[]." + key, "bytes_state": "NOT_ACQUIRED"})
                for key in ("image", "photo_image", "thumbnailImage", "preferred_thumbnail"):
                    image = media.get(key)
                    value = image.get("uri") if isinstance(image, dict) else None
                    safe = self._sanitize_media_url(value, identity["url"]) if isinstance(value, str) else ""
                    if safe: hints.append({"kind": "image", "url": safe, "native_media_id": native_id, "locator": "$.attachments[]." + key + ".uri", "bytes_state": "NOT_ACQUIRED"})
        created = node.get("creation_time") if node.get("creation_time") is not None else story.get("creation_time")
        published = ""
        if type(created) in {int, float}:
            try: published = datetime.fromtimestamp(created, timezone.utc).isoformat()
            except (ValueError, OSError, OverflowError): pass
        return CollectedNote(title=text[:100], content=text, url=identity["url"], author=owner.get("name") or "",
            author_id=str(owner.get("id") or ""), publish_date=published,
            likes=optional_int((feedback.get("reactors") or {}).get("count")),
            comments=optional_int(feedback.get("total_comment_count")), shares=optional_int((feedback.get("share_count") or {}).get("count")),
            cover=next((hint["url"] for hint in hints if hint["kind"] == "image"), ""), source_platform="facebook",
            raw_data={"engine": "facebook_native_story", "post_id": identity["post_id"], "native_story_id": node.get("id"),
                "body_state": "PLATFORM_BODY" if message.get("is_truncated") is False else "COMPLETENESS_NOT_OBSERVED",
                "body_locator": "$.message.text", "native_time": created, "author": owner, "media_hints": hints,
                "feedback_id": feedback.get("id"), "source_observation": node})

    def _native_read(self, capability, target, limit, *, source_url=None, cursor=None, include_replies=False):
        if type(limit) is not int or not 1 <= limit <= 100:
            return AdapterResult(success=False, error="FACEBOOK_NATIVE_PAGE_SIZE_INVALID")
        try:
            validate_native_page_window_cursor(cursor)
            if isinstance(cursor, dict) and cursor.get('mode') == 'replies':
                validate_native_page_window_cursor(cursor.get('next_root'))
        except NativePageWindowError:
            return AdapterResult(success=False, error='FACEBOOK_NATIVE_CURSOR_WINDOW_INVALID')
        if cursor is not None and (not isinstance(cursor, dict) or cursor.get("mode") not in {"roots", "replies", "posts", "search"}
                or not isinstance(cursor.get("after"), str) or len(cursor["after"]) > 4096
                or not cursor['after'] and cursor.get('mode') != 'replies' and 'item_offset' not in cursor
                or any(ord(c) < 32 for c in cursor["after"])):
            return AdapterResult(success=False, error="FACEBOOK_NATIVE_CURSOR_INVALID")
        if (capability == 'comments' and include_replies and cursor is not None
                and 'reply_scope_unknown' in cursor and type(cursor['reply_scope_unknown']) is not bool):
            return AdapterResult(success=False, error="FACEBOOK_NATIVE_CURSOR_INVALID")
        if cursor is not None and (capability == 'author_posts' and cursor['mode'] != 'posts'
                or capability == 'search' and cursor['mode'] != 'search'
                or capability == 'comments' and cursor['mode'] not in {'roots', 'replies'}
                or capability == 'author'):
            return AdapterResult(success=False, error='FACEBOOK_NATIVE_CURSOR_INVALID')
        worker, page = None, None
        capture = NativeReadCapture(hosts={"www.facebook.com", "web.facebook.com", "m.facebook.com"}, paths=("/api/graphql", "/graphql"),
            request_keys={"cursor", "after", "id", "nodeID", "feedbackID", "feedback_id", "postID", "post_id", "actorID", "profileID", "count", "query", "search_query", "fb_api_req_friendly_name"})
        known_posts, authors = set(), {}
        try:
            worker = HumanBrowser(cdp_url=configured_readonly_worker_url("facebook"), auto_ensure=False, launch_url="about:blank")
            worker.connect()
            inject_into_context(worker._context, "facebook")
            page = worker.new_page(stealth=False)
            capture.attach(page)
            url = source_url or ("https://www.facebook.com/search/posts/?q=" + urlencode({"q": target})[2:] if capability == "search" else "https://www.facebook.com/" + target)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1000)
            def register(objects):
                for obj in objects:
                    for node in native_json_nodes(obj):
                        identity = self._native_post_identity(node)
                        if identity and identity["post_id"] == target:
                            for value in (node.get("id"), node.get("post_id"), (node.get("feedback") or {}).get("id")):
                                if value is not None: known_posts.add(str(value))
                        if capability in {"author", "author_posts"} and node.get("id"):
                            profile_url = node.get("url") or node.get("profile_url") or ""
                            parsed = urlsplit(profile_url) if isinstance(profile_url, str) else None
                            if str(node["id"]) == target or parsed and parsed.hostname in {"www.facebook.com", "facebook.com"} and parsed.path.strip("/").casefold() == target.casefold():
                                if any(key in node for key in ("name", "username")):
                                    authors[str(node["id"])] = node
            register(native_page_json(page))
            def select(observation):
                register(observation["objects"])
                request = observation["request"]
                observed_cursor = request.get("cursor") or request.get("after")
                if str(observed_cursor or "") != str((cursor or {}).get("after") or ""):
                    return None
                if capability == "author":
                    if authors: return {"profile": next(iter(authors.values()))}
                    return None
                if capability == "comments":
                    requested = {str(request[key]) for key in ("id", "nodeID", "feedbackID", "feedback_id", "postID", "post_id") if request.get(key)}
                    expected = {str((cursor or {}).get("root_id")), str((cursor or {}).get('root_resource_id'))} if (cursor or {}).get("mode") == "replies" else known_posts | {target}
                    if not requested.intersection(expected): return None
                elif capability == "author_posts":
                    requested = {str(request[key]) for key in ("id", "profileID", "actorID") if request.get(key)}
                    if not requested.intersection(authors): return None
                elif request.get("query") != target and request.get("search_query") != target and not re.fullmatch(r'CometSearchResults[A-Za-z0-9_]*', str(request.get('fb_api_req_friendly_name') or '')):
                    return None
                for obj in observation["objects"]:
                    for node in native_json_nodes(obj):
                        for key, connection in node.items():
                            meaningful = ("comment" in key.lower()) if capability == "comments" else ("timeline" in key.lower() or "feed" in key.lower() or "search" in key.lower())
                            if meaningful and isinstance(connection, dict) and isinstance(connection.get("edges"), list):
                                return {"connection": connection, "rows": [edge.get("node") for edge in connection["edges"] if isinstance(edge, dict) and isinstance(edge.get("node"), dict)]}
                return None
            def advance(_step):
                if self._page_failure_state(page): return False
                if include_replies or (cursor or {}).get("mode") == "replies":
                    control = page.get_by_text(re.compile(r"^(?:View|See|Show) (?:\d+ |more |previous )?repl(?:y|ies)$|^查看.{0,12}(?:回复|回覆)$", re.I)).first
                    if control.count() and control.is_visible(): control.click(timeout=3000); return True
                return native_read_scroll(page, reply_id=(cursor or {}).get("root_id"), reply_attribute="data-comment-id")
            selected = {"profile": next(iter(authors.values())), "observed_prior_native_responses": 0} if capability == "author" and authors else capture.seek(page, select, advance, max_steps=16)
            if selected is None:
                failure = capture.failure() or {}
                if capability == 'search' and cursor is None and not failure and not self._page_failure_state(page):
                    notes = [note for card in page.query_selector_all('div[role="article"]')
                             if (note := self._parse_facebook_card(card, page)) is not None]
                    if notes:
                        return AdapterResult(success=True, notes=notes[:limit], raw_count=len(notes), metadata={'pagination': {
                            'request_cursor': None, 'next_cursor': None, 'exhausted': None, 'page_complete': len(notes) <= limit,
                            'coverage_scope': 'LOADED_SEARCH_CARDS_ONLY', 'partial_reason': 'NATIVE_CURSOR_NOT_OBSERVED'}})
                code = failure.get("failure_class") or self._page_failure_state(page) or "NATIVE_PAGE_NOT_OBSERVED"
                return AdapterResult(success=False, error="FACEBOOK_" + code, metadata={"failure_class": failure.get("failure_class"),
                    "http_status": failure.get("http_status"), "retry_after_seconds": failure.get("retry_after_seconds"),
                    "pagination": {"request_cursor": cursor, "next_cursor": None, "exhausted": None, "page_complete": False}})
            if capability == "author":
                profile = selected["profile"]
                return AdapterResult(success=True, notes=[CollectedNote(title=profile.get("name") or "", content=(profile.get("bio") or {}).get("text") or "",
                    url=url, author=profile.get("name") or "", author_id=str(profile["id"]), source_platform="facebook", raw_data={
                        "engine": "facebook_native_profile", "username": target, "native_user_id": str(profile["id"]), "source_observation": profile,
                        "follower_count": optional_int((profile.get("followers") or {}).get("count")),
                        "native_author_aliases": [{"kind": "requested", "value": target}, {"kind": "id", "value": str(profile["id"])}]})], raw_count=1)
            connection, rows = selected["connection"], selected["rows"]
            page_info = connection.get("page_info") or {}
            more = page_info.get("has_next_page") if type(page_info.get("has_next_page")) is bool else None
            after = page_info.get("end_cursor")
            identities = []
            for row in rows:
                identity = None
                if isinstance(row, dict):
                    identity = row.get('legacy_fbid') or row.get('id')
                    if capability != 'comments':
                        for candidate in (row, row.get('story'), row.get('node')):
                            native = self._native_post_identity(candidate) if isinstance(candidate, dict) else None
                            if native:
                                identity = native['post_id']
                                break
                identities.append(str(identity) if identity is not None else None)
            window = native_page_window(rows, limit=limit, cursor=cursor, identities=identities)
            complete = window['page_complete']
            base_cursor = {key: value for key, value in (cursor or {}).items() if key not in {'item_offset', 'page_sha256'}}
            if not base_cursor:
                base_cursor = {'mode': 'roots' if capability == 'comments' else 'posts' if capability == 'author_posts' else 'search', 'after': ''}
            native_next = ({**base_cursor, **window['next_window']} if not complete else
                           {**base_cursor, 'after': after} if more is True and isinstance(after, str)
                           and after and after != base_cursor['after'] else None)
            notes, seen, deferred = [], set(), []
            reply_scope_unknown = (cursor.get('reply_scope_unknown', True)
                                   if capability == 'comments' and include_replies and cursor is not None else False)
            flattened = []
            for row in window['rows']:
                if not isinstance(row, dict): continue
                flattened.append((row, (cursor or {}).get('root_id')))
                if capability == 'comments':
                    connection_replies = row.get('comment_replies') or row.get('replies') or {}
                    children = [edge.get('node') for edge in connection_replies.get('edges') or [] if isinstance(edge, dict) and isinstance(edge.get('node'), dict)]
                    cid = row.get('legacy_fbid') or row.get('id')
                    flattened.extend((child, cid) for child in children)
                    reply_count = optional_int(connection_replies.get('count'))
                    if include_replies and reply_count is None:
                        reply_scope_unknown = True
                    if reply_count is not None and reply_count > len(children):
                        deferred.append({'root_id': str(cid), 'root_resource_id': str((row.get('feedback') or {}).get('id') or row.get('id') or cid)})
            for row, observed_parent in flattened:
                if capability == "comments":
                    cid = row.get("legacy_fbid") or row.get("id")
                    body = row.get("body") or {}
                    if not cid or not isinstance(body.get("text"), str): continue
                    owner = row.get("author") or {}
                    parent = row.get("parent_comment") or row.get("comment_parent") or {}
                    parent_id = parent.get("legacy_fbid") or parent.get("id") or observed_parent
                    if str(cid) in seen: continue
                    seen.add(str(cid))
                    created = row.get("created_time")
                    published = ""
                    if type(created) in {int, float}:
                        try: published = datetime.fromtimestamp(created, timezone.utc).isoformat()
                        except (ValueError, OSError, OverflowError): pass
                    notes.append(CollectedNote(title="", content=body["text"], url=row.get("url") or source_url or "", author=owner.get("name") or "",
                        author_id=str(owner.get("id") or ""), publish_date=published, likes=optional_int(((row.get("feedback") or {}).get("reactors") or {}).get("count")),
                        source_platform="facebook", raw_data={"engine": "facebook_native_comments", "type": "comment", "platform_comment_id": str(cid),
                            "parent_content_id": target, "parent_comment_id": str(parent_id) if parent_id else None,
                            "reply_to_comment_id": str(parent_id) if parent_id else None, "source_observation": row}))
                else:
                    for candidate in (row, row.get("story"), row.get("node")):
                        note = self._native_post_note(candidate) if isinstance(candidate, dict) else None
                        if not note or note.raw_data["post_id"] in seen: continue
                        if capability == "author_posts" and note.author_id not in authors: continue
                        seen.add(note.raw_data["post_id"])
                        if capability == "author_posts": note.raw_data["author_history_binding"] = {"requested_id": target, "native_user_id": note.author_id}
                        notes.append(note)
            exhausted = not more if more is not None and complete else None
            if not complete:
                exhausted = False
            if capability == 'comments':
                if (cursor or {}).get('mode') == 'replies':
                    if native_next is None and exhausted is True and cursor.get('pending_roots'):
                        following = cursor['pending_roots'][0]
                        native_next = {**base_cursor, **following, 'after': '', 'pending_roots': cursor['pending_roots'][1:]}
                    elif native_next is None and exhausted is True:
                        native_next, exhausted = cursor.get('next_root'), cursor.get('root_exhausted')
                elif include_replies and deferred:
                    native_next = {'mode': 'replies', **deferred[0], 'after': '', 'pending_roots': deferred[1:],
                                   'next_root': native_next, 'root_exhausted': exhausted}
                    exhausted = False
                replies_complete = (False if native_next is not None or exhausted is False else
                                    None if exhausted is not True or reply_scope_unknown else True) if include_replies else None
                if include_replies and native_next is not None:
                    native_next = {**native_next, 'reply_scope_unknown': reply_scope_unknown}
            else:
                replies_complete = None
            if rows and not notes:
                return AdapterResult(success=False, error='FACEBOOK_NATIVE_RECORD_SHAPE_UNSUPPORTED')
            return AdapterResult(success=True, notes=notes, raw_count=len(notes), metadata={"pagination": {"request_cursor": cursor,
                "next_cursor": native_next, "exhausted": exhausted, "page_complete": complete,
                "replies_complete": replies_complete,
                "reported_total": optional_int(connection.get("count")), "coverage_scope": "PROVIDER_VISIBLE_NATIVE_PAGE",
                **{key: window[key] for key in ('window_start', 'window_end', 'observed_native_rows', 'page_sha256', 'page_identity_basis')},
                "resume_strategy": "OFFICIAL_PAGE_NATIVE_CURSOR_SEEK", "observed_prior_native_responses": selected["observed_prior_native_responses"],
                "partial_reason": "REQUESTED_LIMIT_REACHED" if not complete else None}})
        except NativePageWindowError as exc:
            return AdapterResult(success=False, raw_count=None, error='FACEBOOK_' + str(exc), metadata={
                'failure_class': str(exc), 'pagination': {'request_cursor': cursor, 'next_cursor': None,
                    'exhausted': None, 'page_complete': False, 'resume_requires_fresh_page': True}})
        except Exception as exc:
            logger.warning("Facebook native read failed error_type=%s", type(exc).__name__)
            return AdapterResult(success=False, error=self._exception_error(exc))
        finally:
            capture.close()
            if page is not None:
                try: page.close()
                except Exception: pass
            if worker is not None: worker.close()

    def author_posts(self, author_id, *, max_results=20, cursor=None, **kwargs):
        target = str(author_id or "").strip()
        if re.fullmatch(r"[A-Za-z0-9.]{1,100}", target) is None:
            return AdapterResult(success=False, error="FACEBOOK_AUTHOR_ID_INVALID")
        return self._native_read("author_posts", target, max_results, cursor=cursor)
