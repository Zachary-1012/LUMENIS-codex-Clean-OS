# -*- coding: utf-8 -*-
"""
抖音全网搜索采集适配器（DOUYIN_READONLY 专用真人浏览器 + 结构化接口双通道）
-------------------------------------------------
定位：抖音网页端强依赖登录态与 JS 渲染，纯 requests 不可行。本适配器走
“真实有头系统默认浏览器（9225 专用持久 Profile）+ connectOverCDP + 拟人操作”，
登录态由持久 Profile 与 cookie_vault 注入双通道桥接，绝不把 Cookie 写进代码。

数据主路径（准、全、稳）：拦截搜索接口 XHR
  · /aweme/v1/web/general/search/single/  —— 标准 JSON；
  · /aweme/v1/web/general/search/stream/  —— chunked 多段 JSON（剥分片头后逐段解析）；
  两者都含 aweme_info：aweme_id / create_time(精确发布时间戳) / statistics /
  author / desc。DOM 仅用于六态判断与“接口漏抓”时的文本兜底，不依赖混淆 class。

六态严格分离：解析到视频=SUCCESS；正常无结果=success=True/notes=[](EMPTY)；
登录墙=AUTH_FAILED；滑块图形验证=CAPTCHA；访问频繁=BLOCKED；加载失败=NETWORK_ERROR。
任何失败都不伪装成“0 条成功”。

时间口径：publish_date 取自 create_time（笔记真实发布日期），采集时间由入库层
统一写 captured_at，二者严格分离，绝不用采集时间冒充发布时间。
publish_date 是抖音来源的 UTC+08:00 日历日期，不是 UTC 事件时间；原始 create_time 保留。
"""
import re
import json
import logging
import datetime
import urllib.parse
import ipaddress
import os
from urllib.parse import urlsplit, urlunsplit
from .base import BaseAdapter, AdapterResult, optional_int
from .human_browser import (HumanBrowser, NativeReadCapture, PageState, NativePageWindowError,
                            native_page_window, native_read_scroll, validate_native_page_window_cursor)
from .cookie_vault import inject_into_context

logger = logging.getLogger(__name__)

_SEARCH_API_KEYS = ("general/search/single", "general/search/stream")


def _configured_browser_worker_url() -> str:
    """Require an explicit remote worker or the opted-in isolated local Douyin worker."""
    value = str(os.getenv("DOUYIN_CDP_URL") or "").strip()
    if not value:
        raise RuntimeError("DOUYIN_CDP_URL is not configured")
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        raise RuntimeError("DOUYIN_CDP_URL must be a plain worker endpoint URL")
    original_host = parsed.hostname.lower()
    host = original_host.rstrip(".")
    if host in {"localhost", "localhost.localdomain"}:
        raise RuntimeError("DOUYIN_CDP_URL must identify a remote browser worker")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and (address.is_loopback or address.is_unspecified):
        local_opt_in = str(os.getenv("DOUYIN_LOCAL_WORKER_ENABLED") or "").strip().lower()
        local_account = str(os.getenv("DOUYIN_LOCAL_WORKER_ACCOUNT") or "").strip().upper()
        exact_local = (
            parsed.scheme == "http" and original_host == "127.0.0.1" and parsed.port == 9225
            and parsed.path in {"", "/"} and not parsed.query and not parsed.fragment
            and local_opt_in in {"1", "true", "yes"}
            and local_account == "DOUYIN_READONLY"
        )
        if not exact_local:
            raise RuntimeError("DOUYIN_CDP_URL loopback is restricted to the opted-in DOUYIN_READONLY worker")
        from .cookie_vault import registered_session_data_dir
        import cdp_helper
        profile_dir = registered_session_data_dir() / "private" / "profiles" / "douyin-readonly"
        if not cdp_helper.registered_cdp_browser_for_port(
                9225, str(profile_dir), headless=True):
            raise RuntimeError("READONLY_WORKER_PROFILE_MODE_OR_KERNEL_UNAVAILABLE")
        return "http://127.0.0.1:9225"
    return value


def _new_browser_worker():
    return HumanBrowser(
        cdp_url=_configured_browser_worker_url(),
        auto_ensure=False,
        launch_url="about:blank",
    )


def _iter_json_objects(text):
    """从可能含 chunked 分片头 / 多段拼接的响应体中逐个解出 JSON 对象。"""
    dec = json.JSONDecoder()
    idx, objs = 0, []
    n = len(text)
    while idx < n:
        while idx < n and text[idx] not in "{[":
            idx += 1
        if idx >= n:
            break
        try:
            obj, end = dec.raw_decode(text, idx)
            objs.append(obj)
            idx = end
        except Exception:
            idx += 1
    return objs


class DouyinAdapter(BaseAdapter):
    """抖音搜索适配器（CDP 真人浏览 + 搜索接口结构化拦截）"""

    platform_name = "douyin"
    platform_display = "抖音"

    # The deployed CDP endpoint is injected as DOUYIN_CDP_URL by the runtime.

    def search(self, keyword: str, max_results: int = 20, *, cursor=None) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        try:
            if type(max_results) is not int or not 1 <= max_results <= 100:
                return AdapterResult(success=False, error="DOUYIN_PAGE_SIZE_INVALID")
            return self._native_list("search", keyword.strip(), max_results, cursor=cursor)
        except Exception as exc:
            logger.warning("Douyin search failed error_type=%s", type(exc).__name__)
            return AdapterResult(success=False, error="DOUYIN_PROVIDER_UNAVAILABLE")

    def _search_browser(self, keyword, max_results) -> AdapterResult:
        from lumenis.system.collector.adapters.response_shape import SearchShapeDiagnostics

        shape_observer = SearchShapeDiagnostics()
        hb = _new_browser_worker()
        hb.connect()
        injected = inject_into_context(hb._context, "douyin")  # Cookie 兜底/换号
        logger.info("抖音采集：注入 Cookie %d 条", injected)
        api_bags = []

        def _on_request_finished(request):
            try:
                u = request.url
                if not any(k in u for k in _SEARCH_API_KEYS):
                    return
                if request.resource_type not in ("xhr", "fetch"):
                    return
                # Playwright's response event fires when headers arrive; reading
                # a streamed body there can block the sync dispatcher. The
                # requestfinished event means the response body is available.
                shape_observer.response_observed()
                resp = request.response()
                if resp is None:
                    return
                if "stream" in u:
                    objects = _iter_json_objects(resp.text())
                    api_bags.extend(objects)
                    if not objects:
                        shape_observer.parse_failed()
                    for obj in objects:
                        shape_observer.observe_json(obj)
                else:
                    obj = resp.json()
                    api_bags.append(obj)
                    shape_observer.observe_json(obj)
            except Exception:
                # Preserve the business fallback without exposing the response.
                shape_observer.parse_failed()
                return

        page = None
        try:
            # Use the retained browser's normal page behavior; do not patch
            # navigator/runtime properties on the authenticated collection tab.
            page = hb.new_page(stealth=False)
            page.on("requestfinished", _on_request_finished)
            url = ("https://www.douyin.com/search/"
                   f"{urllib.parse.quote(keyword)}?type=general")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # 等结果真正渲染（以时长徽标为锚），最多 ~18s；同时六态判断
            try:
                page.wait_for_function(
                    "()=>(document.body.innerText.match(/\\b\\d{2}:\\d{2}\\b/g)||[]).length>=1",
                    timeout=18000)
            except Exception as exc:
                logger.debug("Douyin search render wait ended error_type=%s", type(exc).__name__)

            def observed_search_failure():
                state = hb.detect_state(
                    page,
                    extra_markers={
                        PageState.BLOCKED: ["访问频繁", "系统繁忙", "稍后再试", "操作太频繁"],
                        PageState.CAPTCHA: ["滑块", "拖动", "安全验证", "captcha_verify"],
                        PageState.AUTH_FAILED: ["登录后即可", "验证码登录", "扫码登录", "登录解锁更多"],
                    },
                    success_selector=".videoImage",
                )
                failure = {
                    PageState.AUTH_FAILED: "抖音登录态失效，请在采集专用 Profile 重新登录或更新 Cookie",
                    PageState.CAPTCHA: "DOUYIN_CAPTCHA_REQUIRED: 抖音出现人机验证，需人工通过后再采",
                    PageState.BLOCKED: "DOUYIN_RATE_LIMITED: 抖音访问频繁/风控，按熔断退避不硬刚",
                    PageState.NETWORK_ERROR: "DOUYIN_NETWORK_UNAVAILABLE",
                }.get(state)
                if failure is None:
                    return None
                # Retain responses already observed in this attempt without
                # scrolling, reading a fallback DOM, or opening post details.
                observed = self._notes_from_bags(api_bags, max_results)
                return AdapterResult(
                    success=False, notes=observed, error=failure,
                    raw_count=len(observed), diagnostics=shape_observer.snapshot()
                )

            failure = observed_search_failure()
            if failure is not None:
                return failure

            # 拟人滚动加载更多（变速、偶发回滚），让 stream 接口逐页返回
            for _ in range(3):
                hb.human_scroll(page, total_px=800, rounds=2)
                hb.pause(1.4, 2.4)
                failure = observed_search_failure()
                if failure is not None:
                    return failure
                if len(self._notes_from_bags(api_bags, max_results)) >= max_results:
                    break

            # 主路径：结构化接口
            notes = self._notes_from_bags(api_bags, max_results)
            source = "douyin_search_api"
            # 兜底：接口漏抓时用 DOM 卡片文本（拿不到精确时间则发布日期留空）
            if not notes:
                notes = self._parse_dom(page, max_results)
                source = "douyin_dom_fallback"

            if notes:
                for nt in notes:
                    nt.raw_data = dict(nt.raw_data or {})
                    nt.raw_data["engine"] = source
                return AdapterResult(success=True, notes=notes, raw_count=len(notes), diagnostics=shape_observer.snapshot())

            # 无结果时按页面状态如实上报，绝不把风控/登录墙伪装成 0 条
            if not self._has_verified_empty_search_response(api_bags):
                return AdapterResult(
                    success=False,
                    error="抖音搜索未返回可验证的结构化结果，不能确认为无新内容", diagnostics=shape_observer.snapshot()
                )
            return AdapterResult(success=True, notes=[], raw_count=0, diagnostics=shape_observer.snapshot())
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass
            hb.close()

    # ----------------------------------------------------------
    # 主路径：搜索接口 aweme_info → CollectedNote
    # ----------------------------------------------------------
    @staticmethod
    def _has_verified_empty_search_response(bags):
        """Only a successful, explicit empty data array can mean a genuine empty search."""
        successful_empty = any(
            isinstance(bag, dict)
            and bag.get("status_code") == 0
            and isinstance(bag.get("data"), list)
            and not bag["data"]
            for bag in bags or []
        )
        has_candidates = any(
            isinstance(bag, dict)
            and isinstance(bag.get("data"), list)
            and bool(bag["data"])
            for bag in bags or []
        )
        return successful_empty and not has_candidates

    def _notes_from_bags(self, bags, max_results):
        notes, seen = [], set()
        for bag in bags:
            if not isinstance(bag, dict):
                continue
            for item in bag.get("data") or []:
                if not isinstance(item, dict):
                    continue
                ai = item.get("aweme_info")
                if not ai:
                    continue
                wid = ai.get("aweme_id")
                if (not isinstance(wid, str) or not wid or wid != wid.strip()
                        or wid in seen):
                    continue
                seen.add(wid)
                desc = re.sub(r"\s+", " ", (ai.get("desc") or "").strip())
                if not desc:
                    continue
                statistics = ai.get("statistics")
                st = statistics if isinstance(statistics, dict) else {}
                play_count = st.get("play_count")
                if type(play_count) is not int or play_count < 0:
                    play_count = None
                au = ai.get("author") or {}
                note = self._make_note(
                    title=desc[:80],
                    content=desc,
                    url=f"https://www.douyin.com/video/{wid}",
                    author=(au.get("nickname") or "抖音用户").strip() or "抖音用户",
                    author_id=str(au.get("uid") or au.get("short_id") or ""),
                    publish_date=self._ts_to_date(ai.get("create_time")),
                    likes=self._to_int(st.get("digg_count")),
                    comments=self._to_int(st.get("comment_count")),
                    collects=self._to_int(st.get("collect_count")),
                    shares=self._to_int(st.get("share_count")),
                    source_platform=self.platform_name,
                    raw_data={
                        "engine": "douyin_search_api",
                        "aweme_id": wid,
                        "author_id": au.get("uid") or au.get("short_id"),
                        "create_time": ai.get("create_time"),
                        "play_count": play_count,
                        "sec_uid": au.get("sec_uid"),
                        "author": au,
                        "source_observation": ai,
                        "body_kind": "caption",
                        "body_state": "PLATFORM_BODY",
                        "media_hints": self._detail_media_hints(ai, "$.data[].aweme_info"),
                    },
                )
                notes.append(note)
                if len(notes) >= max_results:
                    return notes
        return notes

    # ----------------------------------------------------------
    # 兜底：DOM 卡片文本（.videoImage 封面 → flex flex-col 整卡）
    # ----------------------------------------------------------
    def _parse_dom(self, page, max_results):
        rows = page.evaluate(
            r"""() => {
                const out=[], seen=new Set();
                const rootOf=el=>{let p=el;for(let i=0;i<8&&p;i++){if(p.className&&/flex\s+flex-col/.test(p.className.toString()))return p;p=p.parentElement;}return null;};
                document.querySelectorAll('.videoImage').forEach(cov=>{
                    const card=rootOf(cov); if(!card) return;
                    const parts=card.innerText.split('\n').map(s=>s.trim()).filter(Boolean);
                    const key=parts.join('|'); if(seen.has(key))return; seen.add(key);
                    out.push(parts);
                });
                return out;
            }""")
        notes = []
        for parts in rows or []:
            # 结构约为：时长 / 点赞 / 标题… / @作者 / ·日期
            segs = [p for p in parts if not re.fullmatch(r"\d{1,2}:\d{2}", p)]
            author, date_text, title_parts = "", "", []
            for p in segs:
                if p.startswith("@"):
                    author = p.lstrip("@").strip()
                elif p.startswith("·") or re.search(r"\d{1,2}月\d{1,2}日|\d{4}年", p):
                    date_text = p.lstrip("· ").strip()
                else:
                    title_parts.append(p)
            likes = self._cn_num(segs[0]) if segs else 0  # 首段通常为点赞
            title = re.sub(r"\s+", " ", " ".join(title_parts)).strip()
            if not title:
                continue
            notes.append(self._make_note(
                title=title[:80],
                content=title,
                url="",  # DOM 兜底拿不到 aweme_id，不臆造链接
                author=author or "抖音用户",
                publish_date="",  # 列表相对日期无年份，留空不臆造
                likes=likes,
                source_platform=self.platform_name,
                raw_data={"engine": "douyin_dom_fallback", "date_text": date_text},
            ))
            if len(notes) >= max_results:
                break
        return notes

    @staticmethod
    def _ts_to_date(ts):
        """Unix 秒 → 抖音 UTC+08:00 日历日期；不依赖主机时区，无效为空。"""
        try:
            ts = int(ts)
            if ts <= 0:
                return ""
            return datetime.datetime.fromtimestamp(
                ts, tz=datetime.timezone(datetime.timedelta(hours=8))
            ).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OverflowError, OSError):
            return ""

    @staticmethod
    def _to_int(v):
        return optional_int(v)

    @staticmethod
    def _cn_num(text):
        """把 '1.2万' / '3.4亿' 等中文计数转为整数；无法解析返回 0。"""
        if text is None or not str(text).strip():
            return None
        s = str(text).strip().replace(",", "")
        m = re.search(r"([\d.]+)\s*([万亿wW]?)", s)
        if not m:
            return None
        try:
            v = float(m.group(1))
        except ValueError:
            return None
        unit = m.group(2)
        if unit in ("万", "w", "W"):
            v *= 1e4
        elif unit == "亿":
            v *= 1e8
        return int(v)

    # ── detail: 视频详情（浏览器打开视频页，拦截 aweme/detail 接口）──
    def detail(self, aweme_id: str, **kwargs) -> AdapterResult:
        if (not isinstance(aweme_id, str) or not aweme_id
                or aweme_id != aweme_id.strip()):
            return AdapterResult(success=False, error="aweme_id 为空")
        if not self.rate_limiter.acquire(timeout=10.0):
            if self.metrics:
                self.metrics.record_call(False, 0, error="rate_limit_wait_timeout",
                                         rate_limited=True)
            return AdapterResult(success=False, error="rate limit wait timed out")
        try:
            return self._detail_browser(aweme_id)
        except Exception as e:
            logger.exception("抖音详情采集异常")
            return AdapterResult(success=False, error=f"抖音详情异常: {e}")

    @staticmethod
    def _detail_media_hints(aweme, source_root="$.aweme_detail"):
        """Return typed, credential-free URL hints; no media bytes are fetched."""
        hints = []
        seen = set()

        def add_urls(kind, source_path, value):
            if isinstance(value, dict):
                values = value.get("url_list")
                if not isinstance(values, (list, tuple)):
                    values = [value.get("url")]
            elif isinstance(value, (list, tuple)):
                values = value
            else:
                values = [value]
            for candidate in values or []:
                if not isinstance(candidate, str) or not candidate.strip():
                    continue
                try:
                    parsed = urlsplit(candidate.strip())
                except ValueError:
                    continue
                if (parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname
                        or parsed.username or parsed.password):
                    continue
                # Native media URLs can carry short-lived query credentials. Keep
                # a location hint without persisting those values or claiming bytes.
                safe_url = urlunsplit((parsed.scheme.lower(), parsed.netloc,
                                       parsed.path, "", ""))
                identity = (kind, safe_url)
                if identity in seen:
                    continue
                seen.add(identity)
                hints.append({"kind": kind, "url": safe_url, "locator": source_path})
                if len(hints) >= 16:
                    return

        video = aweme.get("video") if isinstance(aweme, dict) else None
        if isinstance(video, dict):
            for field, kind in (
                ("play_addr", "video_play"),
                ("download_addr", "video_download"),
                ("cover", "video_cover"),
                ("origin_cover", "video_origin_cover"),
                ("dynamic_cover", "video_dynamic_cover"),
            ):
                add_urls(kind, f"{source_root}.video.{field}", video.get(field))
                if len(hints) >= 16:
                    return hints
        images = aweme.get("images") if isinstance(aweme, dict) else None
        if isinstance(images, list):
            for index, image in enumerate(images[:12]):
                if not isinstance(image, dict):
                    continue
                add_urls("image", f"{source_root}.images[{index}].url_list",
                         image.get("url_list") or image.get("url"))
                if len(hints) >= 16:
                    break
        return hints

    def _detail_browser(self, aweme_id) -> AdapterResult:
        hb = _new_browser_worker()
        hb.connect()
        inject_into_context(hb._context, "douyin")
        detail_bags = []
        page = None
        try:
            page = hb.new_page(stealth=False)
            def capture_finished(request):
                try:
                    if ("aweme/detail" not in request.url
                            or request.resource_type not in {"xhr", "fetch"}):
                        return
                    response = request.response()
                    if response is not None:
                        self._capture(response, "aweme/detail", detail_bags)
                except Exception:
                    return
            page.on("requestfinished", capture_finished)
            # A response event carries headers, not a completed body. Waiting
            # through Playwright also keeps its dispatcher processing events;
            # a Python sleep followed by reading this list can miss them all.
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            try:
                with page.expect_event(
                    "requestfinished",
                    predicate=lambda request: "aweme/detail" in request.url
                    and request.resource_type in {"xhr", "fetch"},
                    timeout=15000,
                ):
                    page.goto(f"https://www.douyin.com/video/{aweme_id}",
                              wait_until="domcontentloaded", timeout=30000)
            except PlaywrightTimeoutError:
                # A missing response is not evidence of a login/risk failure.
                pass
            for bag in detail_bags:
                if not isinstance(bag, dict):
                    continue
                ai = (bag.get("aweme_detail") or bag.get("aweme") or {})
                if not isinstance(ai, dict):
                    continue
                response_id = ai.get("aweme_id")
                if not isinstance(response_id, str) or response_id != aweme_id:
                    continue
                st = ai.get("statistics")
                st_fields = st if isinstance(st, dict) else {}
                au = ai.get("author") or {}
                desc = ai.get("desc") if isinstance(ai.get("desc"), str) else ""
                detail_root = "$.aweme_detail" if isinstance(bag.get("aweme_detail"), dict) else "$.aweme"
                metrics = dict(st) if isinstance(st, dict) else None
                media_hints = self._detail_media_hints(ai, detail_root)
                cover_hint = next((hint["url"] for hint in media_hints
                                   if hint["kind"] in {"video_cover", "video_origin_cover",
                                                        "video_dynamic_cover", "image"}), "")
                note = self._make_note(
                    title=desc[:80],
                    content=desc,
                    url=f"https://www.douyin.com/video/{aweme_id}",
                    author=(au.get("nickname") or "抖音用户").strip(),
                    author_id=str(au.get("uid") or au.get("short_id") or ""),
                    publish_date=self._ts_to_date(ai.get("create_time")),
                    likes=self._to_int(st_fields.get("digg_count")),
                    comments=self._to_int(st_fields.get("comment_count")),
                    collects=self._to_int(st_fields.get("collect_count")),
                    shares=self._to_int(st_fields.get("share_count")),
                    cover=cover_hint,
                    source_platform=self.platform_name,
                    raw_data={
                        "engine": "douyin_detail_api",
                        "aweme_id": response_id,
                        "create_time": ai.get("create_time"),
                        "native_time_locator": f"{detail_root}.create_time",
                        "body_kind": "caption",
                        "body_locator": f"{detail_root}.desc",
                        "author_locator": f"{detail_root}.author",
                        "metrics": metrics,
                        "metrics_locator": f"{detail_root}.statistics",
                        "media_hints": media_hints,
                        "media_state": "URL_HINTS_OBSERVED" if media_hints else "NO_URL_HINTS_IN_DETAIL_RESPONSE",
                        "media_bytes_saved": False,
                        "artifact_created": False,
                    },
                )
                return AdapterResult(success=True, notes=[note], raw_count=1)
            state = hb.detect_state(page, success_selector="video")
            failure = {
                PageState.AUTH_FAILED: "抖音登录态失效",
                PageState.CAPTCHA: "抖音详情需要人工安全验证",
                PageState.BLOCKED: "抖音详情出现平台风控",
                PageState.NETWORK_ERROR: "Douyin detail network unavailable",
            }.get(state, "Douyin detail provider unavailable: native response not observed")
            return AdapterResult(success=False, error=failure)
        finally:
            if page:
                try: page.close()
                except Exception: pass
            hb.close()

    # ── comments: 视频评论（浏览器打开视频页，滚动加载，拦截 comment/list 接口）──
    def comments(self, aweme_id: str, max_comments: int = 20, **kwargs) -> AdapterResult:
        if not re.fullmatch(r"[1-9][0-9]{5,29}", str(aweme_id or "")):
            return AdapterResult(success=False, error="DOUYIN_CONTENT_ID_INVALID")
        if type(max_comments) is not int or not 1 <= max_comments <= 100:
            return AdapterResult(success=False, error="DOUYIN_PAGE_SIZE_INVALID")
        try:
            return self._native_list("comments", str(aweme_id), max_comments,
                                     cursor=kwargs.get("cursor"), include_replies=kwargs.get("include_replies", False))
        except Exception as exc:
            logger.warning("Douyin comments failed error_type=%s", type(exc).__name__)
            return AdapterResult(success=False, error="DOUYIN_PROVIDER_UNAVAILABLE")

    @staticmethod
    def _native_cursor(value):
        return (isinstance(value, str) and value.isascii() and value.isdigit()
                and 1 <= len(value) <= 30)

    def _native_list(self, capability, target, limit, *, cursor=None, include_replies=False):
        """Read one exact native page generated by the registered Douyin UI."""
        reply_root = None
        reply_scope_unknown = (cursor.get('reply_scope_unknown', True)
                               if capability == 'comments' and include_replies and isinstance(cursor, dict) else False)
        if capability == 'comments' and type(include_replies) is not bool:
            return AdapterResult(success=False, error="DOUYIN_NATIVE_CURSOR_INVALID")
        window_keys = {'item_offset', 'page_sha256'}
        try:
            validate_native_page_window_cursor(cursor)
            if isinstance(cursor, dict) and cursor.get('mode') == 'replies':
                validate_native_page_window_cursor(cursor.get('next_root'))
        except NativePageWindowError:
            return AdapterResult(success=False, error='DOUYIN_NATIVE_CURSOR_WINDOW_INVALID')
        if cursor is not None:
            if capability == "search":
                valid = (isinstance(cursor, dict) and set(cursor) <= {"offset", "search_id"} | window_keys
                         and self._native_cursor(cursor.get("offset"))
                         and ("search_id" not in cursor or isinstance(cursor["search_id"], str)
                              and re.fullmatch(r"[A-Za-z0-9_-]{1,200}", cursor["search_id"])))
            elif capability == "author_posts":
                valid = isinstance(cursor, dict) and set(cursor) - window_keys == {"max_cursor"} and self._native_cursor(cursor["max_cursor"])
            else:
                valid = isinstance(cursor, dict) and cursor.get("mode") in {"roots", "replies"} and self._native_cursor(cursor.get("cursor"))
                if valid and cursor["mode"] == "roots":
                    valid = (set(cursor) - window_keys == {"mode", "cursor"}
                             or include_replies and set(cursor) - window_keys == {"mode", "cursor", "reply_scope_unknown"}
                             and type(cursor.get('reply_scope_unknown')) is bool)
                elif valid:
                    valid = (set(cursor) - window_keys in ({"mode", "root_id", "cursor", "pending_roots", "next_root", "root_exhausted"},
                                                           {"mode", "root_id", "cursor", "pending_roots", "next_root", "root_exhausted", "reply_scope_unknown"})
                             and ('reply_scope_unknown' not in cursor or include_replies and type(cursor.get('reply_scope_unknown')) is bool)
                             and isinstance(cursor["root_id"], str) and re.fullmatch(r"[1-9][0-9]{0,29}", cursor["root_id"])
                             and isinstance(cursor["pending_roots"], list) and len(cursor["pending_roots"]) <= 100
                             and all(isinstance(v, str) and re.fullmatch(r"[1-9][0-9]{0,29}", v) for v in cursor["pending_roots"])
                             and (cursor["root_exhausted"] is None or type(cursor["root_exhausted"]) is bool)
                             and (cursor["next_root"] is None or isinstance(cursor["next_root"], dict)
                                  and set(cursor["next_root"]) - window_keys == {"mode", "cursor"}
                                  and cursor["next_root"].get("mode") == "roots"
                                  and self._native_cursor(cursor["next_root"].get("cursor"))))
                    reply_root = cursor.get("root_id") if valid else None
            if not valid:
                return AdapterResult(success=False, error="DOUYIN_NATIVE_CURSOR_INVALID")
        cursor_key = {"search": "offset", "author_posts": "max_cursor"}.get(capability, "cursor")
        desired = str((cursor or {}).get(cursor_key, "0"))
        paths = _SEARCH_API_KEYS if capability == "search" else ("/aweme/post/",) if capability == "author_posts" else ("/comment/list/",)
        hb = _new_browser_worker()
        page = None
        capture = NativeReadCapture(hosts={"www.douyin.com", "www-hj.douyin.com"}, paths=paths,
            request_keys={"aweme_id", "item_id", "comment_id", "cursor", "max_cursor", "sec_user_id", "count", "offset", "keyword", "search_id"}, object_decoder=_iter_json_objects)
        try:
            hb.connect()
            inject_into_context(hb._context, "douyin")
            page = hb.new_page(stealth=False)
            capture.attach(page)
            url = ("https://www.douyin.com/search/" + urllib.parse.quote(target) + "?type=general" if capability == "search"
                   else f"https://www.douyin.com/user/{target}" if capability == "author_posts" else f"https://www.douyin.com/video/{target}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1000)

            def select(observation):
                request = observation["request"]
                if capability == "search":
                    if request.get("keyword") != target or str(request.get("offset", "0")) != desired:
                        return None
                    if cursor and cursor.get("search_id") and request.get("search_id") != cursor["search_id"]:
                        return None
                elif capability == "author_posts":
                    if str(request.get("sec_user_id", "")) != target or str(request.get("max_cursor", "0")) != desired:
                        return None
                else:
                    is_reply = "/reply/" in observation["path"]
                    if bool(reply_root) != is_reply or str(request.get("aweme_id") or request.get("item_id") or "") != target:
                        return None
                    if reply_root and str(request.get("comment_id", "")) != reply_root:
                        return None
                    if str(request.get("cursor", "0")) != desired:
                        return None
                for bag in observation["objects"]:
                    if not isinstance(bag, dict):
                        continue
                    if bag.get("status_code") not in (0, "0"):
                        observation["failure_class"] = "PROVIDER_REJECTED"
                        return None
                    rows = bag.get({"search": "data", "author_posts": "aweme_list"}.get(capability, "comments"))
                    if isinstance(rows, list):
                        return {"observation": observation, "body": bag, "rows": rows}
                return None

            def advance(_step):
                state = hb.detect_state(page, extra_markers={PageState.AUTH_FAILED: ["登录解锁更多"]})
                if state in {PageState.AUTH_FAILED, PageState.BLOCKED, PageState.CAPTCHA, PageState.NETWORK_ERROR}:
                    return False
                return native_read_scroll(page, reply_id=reply_root, reply_attribute="data-comment-id")

            selected = capture.seek(page, select, advance, max_steps=16)
            if selected is None:
                failure = capture.failure()
                state = hb.detect_state(page)
                code = (failure or {}).get("failure_class") or {
                    PageState.AUTH_FAILED: "AUTH_REQUIRED", PageState.CAPTCHA: "VERIFICATION_REQUIRED",
                    PageState.BLOCKED: "ACCESS_BLOCKED", PageState.NETWORK_ERROR: "NETWORK_UNAVAILABLE"}.get(state, "NATIVE_PAGE_NOT_OBSERVED")
                return AdapterResult(success=False, error="DOUYIN_" + code,
                    metadata={"failure_class": code, "http_status": (failure or {}).get("http_status"),
                              "retry_after_seconds": (failure or {}).get("retry_after_seconds"),
                              "pagination": {"request_cursor": cursor, "next_cursor": None, "exhausted": None, "page_complete": False}})
            bag, rows = selected["body"], selected["rows"]
            more = bag.get("has_more")
            has_more = bool(more) if type(more) in {int, bool} and more in (0, 1) else None
            native_next = bag.get("max_cursor" if capability == "author_posts" else "cursor")
            native_next = str(native_next) if type(native_next) is int or isinstance(native_next, str) else None
            window = native_page_window(rows, limit=limit, cursor=cursor, identities=[
                str((row.get('aweme_info') or {}).get('aweme_id') if capability == 'search' else
                    row.get('aweme_id') if capability == 'author_posts' else row.get('cid'))
                if isinstance(row, dict) else None for row in rows])
            complete = window['page_complete']
            base_cursor = {key: value for key, value in (cursor or {}).items() if key not in window_keys}
            if not base_cursor:
                base_cursor = {cursor_key: '0'} if capability != 'comments' else {'mode': 'roots', 'cursor': '0'}
            can_continue = has_more is True and self._native_cursor(native_next) and native_next != desired and complete
            next_cursor = ({"offset": native_next} if capability == "search" else {"max_cursor": native_next}
                           if capability == "author_posts" else {"mode": "roots", "cursor": native_next}) if can_continue else None
            if not complete:
                next_cursor = {**base_cursor, **window['next_window']}
            elif next_cursor and reply_root:
                next_cursor = {**base_cursor, 'cursor': native_next}
            if capability == "search" and next_cursor and complete:
                search_id = (bag.get("log_pb") or {}).get("impr_id")
                if isinstance(search_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,200}", search_id):
                    next_cursor["search_id"] = search_id
            exhausted = has_more is False if has_more is not None and complete else None
            if not complete:
                exhausted = False
            notes = []
            pending = []
            if capability == "search":
                notes = self._notes_from_bags([{**bag, 'data': window['rows']}], limit)
            elif capability == "author_posts":
                bound = []
                for item in window['rows']:
                    if not isinstance(item, dict):
                        continue
                    author = item.get("author") or {}
                    if author.get("sec_uid") != target:
                        return AdapterResult(success=False, error="DOUYIN_AUTHOR_HISTORY_IDENTITY_MISMATCH")
                    bound.append({"aweme_info": item})
                notes = self._notes_from_bags([{"data": bound}], limit)
                for note in notes:
                    note.raw_data["author_history_binding"] = {"requested_id": target, "native_id_locator": "$.aweme_list[].author.sec_uid"}
            else:
                selected_comments = []
                for item in window['rows']:
                    if not isinstance(item, dict):
                        continue
                    cid = str(item.get("cid") or "")
                    if not re.fullmatch(r"[1-9][0-9]{0,29}", cid):
                        continue
                    if item.get("aweme_id") is not None and str(item["aweme_id"]) != target:
                        return AdapterResult(success=False, error="DOUYIN_COMMENT_PARENT_MISMATCH")
                    inline = item.get("reply_comment") if isinstance(item.get("reply_comment"), list) else []
                    selected_comments.append((item, reply_root))
                    selected_comments.extend((child, cid) for child in inline if isinstance(child, dict))
                    total = optional_int(item.get("reply_comment_total"))
                    if include_replies and total is None:
                        reply_scope_unknown = True
                    if not reply_root and total is not None and total > len(inline):
                        pending.append(cid)
                seen = set()
                for item, parent in selected_comments:
                    cid = str(item.get("cid") or "")
                    if not re.fullmatch(r"[1-9][0-9]{0,29}", cid) or cid in seen:
                        continue
                    seen.add(cid)
                    user = item.get("user") if isinstance(item.get("user"), dict) else {}
                    native_parent = str(item.get("reply_id") or "")
                    if native_parent in {"", "0"}:
                        native_parent = parent
                    notes.append(self._make_note(title="", content=item.get("text") if isinstance(item.get("text"), str) else "",
                        url=f"https://www.douyin.com/video/{target}#cmt{cid}", author=user.get("nickname") or "",
                        author_id=str(user.get("uid") or ""), publish_date=self._ts_to_date(item.get("create_time")),
                        likes=optional_int(item.get("digg_count")), comments=optional_int(item.get("reply_comment_total")),
                        source_platform="douyin", raw_data={"engine": "douyin_native_comments", "type": "comment", "cid": cid,
                            "parent_content_id": target, "parent_comment_id": native_parent,
                            "reply_to_comment_id": item.get("reply_to_reply_id"), "source_observation": item,
                            "native_id_locator": "$.comments[].cid", "media_hints": self._detail_media_hints(item, "$.comments[]")}))
                if reply_root:
                    if next_cursor is None and exhausted is True and cursor["pending_roots"]:
                        next_cursor = {**base_cursor, "root_id": cursor["pending_roots"][0], "cursor": "0", "pending_roots": cursor["pending_roots"][1:]}
                    elif next_cursor is None and exhausted is True:
                        next_cursor = cursor["next_root"]
                        exhausted = cursor["root_exhausted"]
                elif include_replies and pending:
                    next_cursor = {"mode": "replies", "root_id": pending[0], "cursor": "0", "pending_roots": pending[1:],
                                   "next_root": next_cursor, "root_exhausted": exhausted}
                    exhausted = False
            replies_complete = (True if exhausted is True and next_cursor is None and not reply_scope_unknown else
                                False if next_cursor is not None or exhausted is not True else None) if capability == 'comments' and include_replies else None
            if capability == 'comments' and include_replies and next_cursor is not None:
                next_cursor = {**next_cursor, 'reply_scope_unknown': reply_scope_unknown}
            return AdapterResult(success=True, notes=notes, raw_count=len(notes), metadata={
                "pagination": {"request_cursor": cursor, "next_cursor": next_cursor, "exhausted": exhausted,
                    "replies_complete": replies_complete,
                    "page_complete": complete, "reported_total": optional_int(bag.get("total")),
                    **{key: window[key] for key in ('window_start', 'window_end', 'observed_native_rows', 'page_sha256', 'page_identity_basis')},
                    "coverage_scope": "NATIVE_SEARCH_PAGE" if capability == "search" else "NATIVE_AUTHOR_POST_PAGE" if capability == "author_posts" else "NATIVE_VISIBLE_COMMENT_REPLY_PAGES",
                    "resume_strategy": "OFFICIAL_PAGE_NATIVE_CURSOR_SEEK", "observed_prior_native_responses": selected["observed_prior_native_responses"],
                    "partial_reason": "REQUESTED_LIMIT_REACHED" if not complete else "NATIVE_NEXT_CURSOR_NOT_OBSERVED" if has_more and not next_cursor else None}})
        except NativePageWindowError as exc:
            return AdapterResult(success=False, raw_count=None, error='DOUYIN_' + str(exc), metadata={
                'failure_class': str(exc), 'pagination': {'request_cursor': cursor, 'next_cursor': None,
                    'exhausted': None, 'page_complete': False, 'resume_requires_fresh_page': True}})
        finally:
            capture.close()
            if page is not None:
                try: page.close()
                except Exception: pass
            hb.close()

    def author_posts(self, author_id, *, max_results=20, cursor=None, **kwargs):
        if not isinstance(author_id, str) or re.fullmatch(r"[A-Za-z0-9_-]{6,200}", author_id) is None:
            return AdapterResult(success=False, error="DOUYIN_AUTHOR_ID_INVALID")
        if type(max_results) is not int or not 1 <= max_results <= 100:
            return AdapterResult(success=False, error="DOUYIN_PAGE_SIZE_INVALID")
        try:
            return self._native_list("author_posts", author_id, max_results, cursor=cursor)
        except Exception as exc:
            logger.warning("Douyin author history failed error_type=%s", type(exc).__name__)
            return AdapterResult(success=False, error="DOUYIN_PROVIDER_UNAVAILABLE")

    def _comments_browser(self, aweme_id, max_comments) -> AdapterResult:
        hb = _new_browser_worker()
        hb.connect()
        inject_into_context(hb._context, "douyin")
        cmt_bags = []
        page = None
        try:
            page = hb.new_page()
            page.on("response", lambda resp: self._capture(resp, "comment/list", cmt_bags))
            page.goto(f"https://www.douyin.com/video/{aweme_id}", wait_until="domcontentloaded", timeout=30000)
            hb.pause(2.0, 3.0)
            for _ in range(3):
                hb.human_scroll(page, total_px=600, rounds=1)
                hb.pause(1.2, 2.0)
                if sum(len(b.get("comments", [])) for b in cmt_bags) >= max_comments:
                    break
            notes, seen = [], set()
            for bag in cmt_bags:
                for c in bag.get("comments", []) or []:
                    cid = str(c.get("cid") or c.get("id") or "")
                    if not cid or cid in seen:
                        continue
                    seen.add(cid)
                    user = c.get("user") or {}
                    notes.append(self._make_note(
                        title="",
                        content=re.sub(r"\s+", " ", (c.get("text") or "").strip()),
                        url=f"https://www.douyin.com/video/{aweme_id}#cmt{cid}",
                        author=(user.get("nickname") or "抖音用户").strip(),
                        author_id=str(user.get("uid") or user.get("short_id") or ""),
                        publish_date=self._ts_to_date(c.get("create_time")),
                        likes=self._to_int(c.get("digg_count")),
                        comments=self._to_int(c.get("reply_comment_total")),
                        source_platform=self.platform_name,
                        raw_data={"engine": "douyin_comments_api", "cid": cid, "type": "comment"},
                    ))
                    if len(notes) >= max_comments:
                        break
                if len(notes) >= max_comments:
                    break
            return AdapterResult(success=True, notes=notes, raw_count=len(notes))
        finally:
            if page:
                try: page.close()
                except Exception: pass
            hb.close()

    # ── creator: 用户主页（浏览器打开 user 页，拦截 user/profile 接口）──
    def creator(self, sec_uid: str, **kwargs) -> AdapterResult:
        if not sec_uid or not str(sec_uid).strip():
            return AdapterResult(success=False, error="sec_uid 为空")
        try:
            return self._creator_browser(str(sec_uid).strip())
        except Exception as e:
            logger.exception("抖音用户采集异常")
            return AdapterResult(success=False, error=f"抖音用户异常: {e}")

    def _creator_browser(self, sec_uid) -> AdapterResult:
        hb = _new_browser_worker()
        hb.connect()
        inject_into_context(hb._context, "douyin")
        profile_bags = []
        page = None
        try:
            page = hb.new_page(stealth=False)
            page.on("requestfinished", lambda req: self._capture(req.response(), "user/profile", profile_bags))
            page.goto(f"https://www.douyin.com/user/{sec_uid}", wait_until="domcontentloaded", timeout=30000)
            hb.pause(2.5, 4.0)
            for bag in profile_bags:
                u = bag.get("user") or {}
                if not u:
                    continue
                if u.get("sec_uid") != sec_uid:
                    return AdapterResult(success=False, error="DOUYIN_AUTHOR_IDENTITY_MISMATCH")
                note = self._make_note(
                    title=u.get("nickname", ""),
                    content=(u.get("signature") or "").strip(),
                    url=f"https://www.douyin.com/user/{sec_uid}",
                    author=u.get("nickname", ""),
                    author_id=str(u.get("uid") or u.get("short_id") or ""),
                    publish_date="",
                    likes=None,
                    comments=None,
                    collects=None,
                    shares=None,
                    cover="",
                    source_platform=self.platform_name,
                    raw_data={
                        "engine": "douyin_user_profile_api",
                        "sec_uid": sec_uid,
                        "native_author_aliases": [{"kind": key, "value": str(u[key])} for key in ("uid", "sec_uid", "unique_id", "short_id") if u.get(key)],
                        "follower_count": u.get("follower_count"),
                        "following_count": u.get("following_count"),
                        'content_count':u.get('aweme_count'), 'received_likes_count':u.get('total_favorited'),
                        'source_observation':u,
                        "type": "creator",
                    },
                )
                return AdapterResult(success=True, notes=[note], raw_count=1)
            return AdapterResult(success=False, error="抖音用户主页接口未返回（可能需登录或风控）")
        finally:
            if page:
                try: page.close()
                except Exception: pass
            hb.close()

    @staticmethod
    def _capture(resp, key, bags):
        """CDP response 回调：拦截含 key 的 XHR/Fetch 响应并解析 JSON。"""
        try:
            if key not in resp.url:
                return
            if resp.request.resource_type not in ("xhr", "fetch"):
                return
            bags.append(resp.json())
        except Exception:
            pass
