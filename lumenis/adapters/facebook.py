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

from .base import BaseAdapter, AdapterResult, CollectedNote

logger = logging.getLogger(__name__)


class FacebookAdapter(BaseAdapter):
    """Facebook 搜索适配器（浏览器 CDP + cookie，只读采集）"""

    platform_name = "facebook"
    platform_display = "Facebook"

    _OFFICIAL_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com"}
    _NATIVE_POST_ID = re.compile(r"[A-Za-z0-9]+")

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

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        try:
            limit = min(20, max(0, int(max_results)))
        except (TypeError, ValueError, OverflowError):
            limit = 20
        if limit == 0:
            return AdapterResult(success=True, notes=[], raw_count=0)
        return self._search_browser(keyword, limit)

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
                note = self._parse_facebook_detail_article(article, page, requested["post_id"])
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

    @staticmethod
    def _expand_detail_post_body(article) -> str:
        """Expand only an explicit read-more control inside the exact post article."""
        labels = {"see more", "see more…", "see more...", "查看更多", "查看全部", "显示更多"}
        body_locator = '[data-ad-preview="message"], [data-ad-comet-preview="message"]'
        try:
            body_element = article.query_selector(body_locator)
            before = body_element.inner_text().strip() if body_element else None
        except Exception:
            return "BODY_NOT_AVAILABLE"
        if not isinstance(before, str):
            return "BODY_NOT_AVAILABLE"
        try:
            controls = article.query_selector_all('div[role="button"], button')
        except Exception:
            return "CONTROLS_UNAVAILABLE"
        inspection_failed = False
        expansion_attempted = False
        for control in controls:
            try:
                label = control.inner_text()
                label = " ".join(label.split()).casefold() if isinstance(label, str) else ""
                aria = control.get_attribute("aria-label")
                aria = " ".join(aria.split()).casefold() if isinstance(aria, str) else ""
            except Exception:
                inspection_failed = True
                continue
            if label not in labels and aria not in labels:
                continue
            try:
                control.click()
                expansion_attempted = True
            except Exception:
                return "EXPANSION_FAILED"
            try:
                expanded_element = article.query_selector(body_locator)
                after = expanded_element.inner_text().strip() if expanded_element else None
            except Exception:
                inspection_failed = True
                continue
            # A different attachment's "See more" button is not evidence that
            # the post body expanded. Only accept a longer native message body.
            if isinstance(after, str) and len(after) > len(before):
                return "EXPANDED"
        if expansion_attempted:
            return "EXPANSION_UNVERIFIED"
        return "CONTROLS_UNAVAILABLE" if inspection_failed else "NO_EXPANSION_CONTROL"

    def _parse_facebook_detail_article(self, article, page, requested_post_id: str) -> CollectedNote | None:
        """FIX-098: observe a native body only for the exact requested post."""
        identity = self._post_permalink_from_card(article, page.url)
        if not identity or identity.get("post_id") != requested_post_id:
            return None
        expansion_state = self._expand_detail_post_body(article)
        if expansion_state not in {"EXPANDED", "NO_EXPANSION_CONTROL"}:
            return None
        body_locator = '[data-ad-preview="message"], [data-ad-comet-preview="message"]'
        try:
            body_element = article.query_selector(body_locator)
            native_body = body_element.inner_text().strip() if body_element else ""
        except Exception:
            native_body = ""
        if not native_body:
            return None

        # Reuse the existing native author, time, metrics and media observations,
        # then replace the search-preview body with the exact article's visible body.
        note = self._parse_facebook_card(article, page)
        if not note or note.raw_data.get("post_id") != requested_post_id:
            return None
        note.content = native_body
        note.title = native_body[:80].replace("\n", " ")
        raw = dict(note.raw_data or {})
        raw.update({
            "body_kind": "NATIVE_POST_BODY",
            "body_status": "NATIVE_DETAIL_BODY_OBSERVED_COMPLETENESS_UNKNOWN",
            "body_sha256": hashlib.sha256(native_body.encode("utf-8")).hexdigest(),
            "body_locator": body_locator,
            "body_state": ("EXPANDED_NATIVE_ARTICLE_DOM_COMPLETENESS_UNKNOWN"
                           if expansion_state == "EXPANDED"
                           else "NATIVE_ARTICLE_DOM_COMPLETENESS_UNKNOWN"),
            "detail_post_id_status": "OBSERVED_AND_MATCHED",
            "detail_post_id_locator": "article a[href] (exact requested native id)",
            "native_identity": {
                "post_id": requested_post_id,
                "requested_post_id": requested_post_id,
                "observed_post_id": identity["post_id"],
                "status": "OBSERVED_MATCH",
                "locator": identity.get("permalink_locator"),
            },
        })
        note.raw_data = raw
        return note

    def comments(self, post_id: str, max_comments: int = 20) -> AdapterResult:
        """Facebook 评论采集（浏览器 CDP，滚动加载）。"""
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
