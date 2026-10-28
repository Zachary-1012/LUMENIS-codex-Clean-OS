# -*- coding: utf-8 -*-
"""
Instagram 海外品牌内容采集适配器（注册只读 Worker + CDP）
-------------------------------------------------
定位：服务于 Z-Brand Core 的海外品牌信息采集（ZBMP 母品牌能力基底）。
浏览器与网络代理由已注册的 SYSTEM Collector 只读 Worker 提供；本适配器
通过其配置的 CDP endpoint 操作，登录态仍由现有 cookie_vault owner 管理。

数据主路径：在 Instagram 官方 /explore/ 搜索框中提交用户原始关键词，
只采集该搜索结果主区域内实际观察到的帖子/短视频链接；账号发现仅在显示名
与完整关键词精确匹配时，沿实际观察到的账号链接继续查看公开内容。

六态严格分离：解析到帖子=SUCCESS；正常无内容=success=True/空(EMPTY)；
登录失效=AUTH_FAILED；人机/确认=CAPTCHA；try again later/风控=BLOCKED；
网络/只读 Worker 不可用=NETWORK_ERROR。没有明确搜索结果时返回能力不可用，
只有观察到平台的明确无结果提示才返回空结果。

时间口径：搜索预览不展示发布日期，publish_date 留空（不臆造），在 raw_data
标 needs_detail，需要精确时间时按原生帖子标识进详情补抓；采集时间由入库层写
captured_at，二者严格分离。
"""
import re
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from .base import BaseAdapter, AdapterResult, optional_int
from .human_browser import (HumanBrowser, NativeReadCapture, PageState, configured_readonly_worker_url,
                            NativePageWindowError, native_json_nodes, native_page_json, native_page_window,
                            native_read_scroll, validate_native_page_window_cursor)
from .cookie_vault import inject_into_context

logger = logging.getLogger(__name__)

_INSTAGRAM_FAILURE_CODES = frozenset({
    "AUTH_REQUIRED", "VERIFICATION_REQUIRED", "RATE_LIMITED",
    "NETWORK_UNAVAILABLE", "NOT_CONFIGURED", "PROVIDER_UNAVAILABLE",
    "UPSTREAM_FAILURE",
})


def instagram_failure_diagnostic(error, existing=None) -> dict:
    """FIX-105: return a bounded code and source locations without exception text.

    This deliberately ignores exception causes/contexts and traceback source
    lines so credentials or page text cannot enter the API response or logs.
    """
    text = str(error or "").casefold()
    name = type(error).__name__.casefold() if isinstance(error, BaseException) else ""
    prior = re.fullmatch(r"instagram_failure:([a-z_]+)", text.strip())
    if prior and prior.group(1).upper() in _INSTAGRAM_FAILURE_CODES:
        reason = prior.group(1).upper()
    elif any(marker in text for marker in ("login", "session", "cookie", "登录", "会话", "失效")):
        reason = "AUTH_REQUIRED"
    elif any(marker in text for marker in ("captcha", "challenge", "verify", "验证", "人机")):
        reason = "VERIFICATION_REQUIRED"
    elif any(marker in text for marker in ("rate limit", "429", "频控", "try again later", "blocked")):
        reason = "RATE_LIMITED"
    elif any(marker in text for marker in (
            "not configured", "not_configured", "worker not registered",
            "worker_not_registered", "not registered", "未配置")):
        reason = "NOT_CONFIGURED"
    elif any(marker in text for marker in (
            "network", "timeout", "connection", "dns", "proxy", "不可达", "连接异常")) \
            or "timeout" in name:
        reason = "NETWORK_UNAVAILABLE"
    elif any(marker in text for marker in (
            "provider unavailable", "provider_unavailable", "worker unavailable",
            "worker_unavailable", "unavailable", "不可用")):
        reason = "PROVIDER_UNAVAILABLE"
    else:
        reason = "UPSTREAM_FAILURE"

    frames = []
    if isinstance(existing, dict) and existing.get("error_code") == f"INSTAGRAM_FAILURE:{reason}":
        for frame in existing.get("stack", [])[:8] if isinstance(existing.get("stack"), list) else []:
            if not isinstance(frame, dict):
                continue
            file_name = frame.get("file")
            function = frame.get("function")
            line = frame.get("line")
            if (isinstance(file_name, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", file_name)
                    and isinstance(function, str) and re.fullmatch(r"[A-Za-z0-9_<>.]{1,80}", function)
                    and isinstance(line, int) and 0 < line < 10_000_000):
                frames.append({"file": file_name, "line": line, "function": function})
    if not frames and isinstance(error, BaseException) and error.__traceback__ is not None:
        for frame in traceback.extract_tb(error.__traceback__)[-8:]:
            file_name = Path(frame.filename).name
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", file_name):
                file_name = "unknown"
            function = frame.name if re.fullmatch(r"[A-Za-z0-9_<>.]{1,80}", frame.name) else "unknown"
            frames.append({"file": file_name, "line": int(frame.lineno), "function": function})
    return {"error_code": f"INSTAGRAM_FAILURE:{reason}", "stack": frames}


def log_instagram_failure(operation: str, error) -> dict:
    diagnostic = instagram_failure_diagnostic(error)
    operation_name = operation if operation in {"comments", "creator"} else "adapter"
    logger.warning("Instagram %s failed code=%s stack=%s",
                   operation_name, diagnostic["error_code"], diagnostic["stack"])
    return diagnostic


class InstagramAdapter(BaseAdapter):
    """Instagram 精确关键词搜索适配器（注册只读 Worker + CDP DOM 主路径）"""

    platform_name = "instagram"
    platform_display = "Instagram"

    SEARCH_HOME = "https://www.instagram.com/"
    SEARCH_INPUT_SELECTOR = (
        'input[placeholder="搜索"],input[aria-label="搜索输入"],'
        'input[placeholder="Search"],input[aria-label="Search input"],'
        'input[placeholder="검색"],input[aria-label="검색 입력"]'
    )
    _SEARCH_BUTTON_SCRIPT = r"""() => {
        const visible = el => {
            if (!el) return false;
            const style=window.getComputedStyle(el), rect=el.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden'
                && Number(style.opacity || 1) > 0 && rect.width > 0 && rect.height > 0;
        };
        const normalize = value => (value || '').replace(/\s+/g, ' ').trim().toLowerCase();
        const labels = new Set([
            'search', 'search input', '搜索', '搜索输入', '搜寻', '搜尋',
            '搜尋輸入', '查找', '검색', '검색 입력'
        ]);
        const matches=[];
        const controls=[...document.querySelectorAll('button,[role="button"]')];
        for (let index=0; index<controls.length; index++) {
            const control=controls[index];
            if (!visible(control) || control.closest('main,[role="main"]')) continue;
            const values=[control.getAttribute('aria-label'), control.getAttribute('title'), control.innerText];
            for (const svg of control.querySelectorAll('svg,[aria-label],[title]')) {
                values.push(svg.getAttribute('aria-label'), svg.getAttribute('title'));
                for (const title of svg.querySelectorAll('title')) values.push(title.textContent || '');
            }
            if (values.some(value => labels.has(normalize(value)))) matches.push(index);
        }
        return {match_count: matches.length, index: matches.length === 1 ? matches[0] : null};
    }"""
    _SEARCH_DOM_SCRIPT = r"""() => {
        const main = document.querySelector('main');
        if (!main) return {main_observed:false, media:[], profiles:[], no_results:false};
        const allowedHost = host => host === 'instagram.com' || host === 'www.instagram.com';
        const cssPath = el => {
            if (!el) return null;
            const parts=[];
            while (el && el !== main) {
                const tag=el.tagName.toLowerCase();
                let index=1, sibling=el.previousElementSibling;
                while (sibling) { if (sibling.tagName === el.tagName) index++; sibling=sibling.previousElementSibling; }
                parts.unshift(`${tag}:nth-of-type(${index})`);
                el=el.parentElement;
            }
            return 'main' + (parts.length ? ' > ' + parts.join(' > ') : '');
        };
        const safeImage = src => {
            if (!src) return null;
            try {
                const u=new URL(src, window.location.href), host=u.hostname.toLowerCase();
            const allowed=host === 'instagram.com' || host.endsWith('.instagram.com')
                    || host === 'cdninstagram.com' || host.endsWith('.cdninstagram.com')
                    || host === 'fbcdn.net' || host.endsWith('.fbcdn.net');
                return u.protocol === 'https:' && !u.username && !u.password && allowed ? u.origin + u.pathname : null;
            } catch (_) { return null; }
        };
        const media=[], profiles=[], seenMedia=new Set(), seenProfiles=new Set();
        for (const a of main.querySelectorAll('a[href]')) {
            let u;
            try { u=new URL(a.href, window.location.href); } catch (_) { continue; }
            if (u.protocol !== 'https:' || u.username || u.password || !allowedHost(u.hostname.toLowerCase())) continue;
            const mediaMatch=u.pathname.match(/^\/(p|reel|reels)\/([A-Za-z0-9_-]+)\/?$/);
            if (mediaMatch) {
                const kind=mediaMatch[1], code=mediaMatch[2], key=kind + '/' + code;
                if (seenMedia.has(key)) continue;
                seenMedia.add(key);
                const imgs=[...a.querySelectorAll('img')];
                const cover=imgs.find(i=>!/头像|profile picture|头像照/i.test(i.alt||'')) || imgs[0] || null;
                const lines=(a.innerText||'').split('\n').map(s=>s.trim()).filter(Boolean).slice(0,24);
                media.push({kind, code, href_ref:u.pathname, observed_origin:u.origin, locator:cssPath(a), lines,
                    alt:cover ? (cover.alt||'') : '', cover:cover ? safeImage(cover.currentSrc||cover.src) : null,
                    cover_locator:cover ? cssPath(cover) : null});
                continue;
            }
            const profileMatch=u.pathname.match(/^\/([A-Za-z0-9._]{1,40})\/?$/);
            if (!profileMatch) continue;
            const handle=profileMatch[1];
            if (/^(explore|accounts|direct|stories|p|reel|reels|tags|about|developer|legal)$/i.test(handle)) continue;
            const hrefRef='/' + handle + '/';
            if (seenProfiles.has(hrefRef)) continue;
            seenProfiles.add(hrefRef);
            const labels=[];
            for (const el of a.querySelectorAll('span,p,strong')) {
                const text=(el.innerText||'').replace(/\s+/g,' ').trim();
                if (text && text.length <= 160) labels.push(text);
            }
            for (const line of (a.innerText||'').split('\n')) {
                const text=line.replace(/\s+/g,' ').trim();
                if (text && text.length <= 160) labels.push(text);
            }
            profiles.push({handle, href_ref:hrefRef, observed_origin:u.origin, locator:cssPath(a), labels:[...new Set(labels)]});
        }
        const noResultsPhrases=[
            'no results found','no results','没有找到任何结果','没有找到结果','未找到结果','没有结果','검색 결과가 없습니다','결과 없음'
        ];
        const normalizeUiText=value=>(value||'').replace(/[.!。！]+$/g,'').replace(/\s+/g,' ').trim().toLowerCase();
        const visibleNoResults=[...main.querySelectorAll('span,p,div')].some(el=>{
            const style=window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
            const text=normalizeUiText(el.innerText);
            return noResultsPhrases.includes(text);
        });
        return {main_observed:true, media, profiles,
            no_results:visibleNoResults};
    }"""

    def search(self, keyword: str, max_results: int = 20, *,
               native_hashtag: str | None = None,
               native_topic_reference: dict | None = None) -> AdapterResult:
        if not isinstance(keyword, str) or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        if native_hashtag is not None or native_topic_reference is not None:
            reference = native_topic_reference if isinstance(native_topic_reference, dict) else None
            literal = reference.get("literal") if reference else None
            observed_tag = self._to_tag(literal)
            if (not isinstance(native_hashtag, str) or not isinstance(literal, str)
                    or not observed_tag or observed_tag != native_hashtag
                    or literal != "#" + native_hashtag):
                return AdapterResult(success=False, error="INSTAGRAM_NATIVE_HASHTAG_REFERENCE_INVALID")
            # Keep only the already verified, seed-backed trace fields. The tag
            # is search provenance, never post-body text or a factual claim.
            native_topic_reference = {
                key: reference.get(key) for key in (
                    "topic_id", "input_sha256", "source_id", "source_url",
                    "term_preserved", "literal", "term_type", "recommended_use",
                )
            }
        try:
            return self._search_browser(
                keyword, max_results, native_hashtag=native_hashtag,
                native_topic_reference=native_topic_reference,
            )
        except Exception as e:
            logger.error("Instagram search failed error_type=%s", type(e).__name__)
            safe_worker_codes = {
                "READONLY_WORKER_NOT_REGISTERED", "READONLY_WORKER_NOT_CONFIGURED",
                "READONLY_WORKER_PROFILE_UNAVAILABLE", "READONLY_WORKER_BOUNDARY_INVALID",
            }
            code = str(e) if isinstance(e, RuntimeError) else ""
            if code in safe_worker_codes:
                return AdapterResult(success=False, error="INSTAGRAM_WORKER_UNAVAILABLE: registered read-only worker is unavailable")
            return AdapterResult(success=False, error="INSTAGRAM_NETWORK_OR_PROVIDER_UNAVAILABLE")

    def _search_browser(self, keyword, max_results, proxy=None, *,
                        native_hashtag=None, native_topic_reference=None) -> AdapterResult:
        try:
            result_limit = min(20, int(max_results))
        except (TypeError, ValueError):
            return AdapterResult(success=False, error="INSTAGRAM_SEARCH_CAPABILITY_UNAVAILABLE: invalid result limit")
        if result_limit < 1:
            return AdapterResult(success=False, error="INSTAGRAM_SEARCH_CAPABILITY_UNAVAILABLE: invalid result limit")

        hb = None
        page = None
        try:
            hb = HumanBrowser(
                cdp_url=configured_readonly_worker_url("instagram"),
                auto_ensure=False,
                launch_url="about:blank",
            )
            hb.connect()
            page = hb.new_page(stealth=False)
            if native_hashtag is not None:
                return self._search_by_hashtag(
                    hb, page, keyword, result_limit, native_hashtag,
                    native_topic_reference,
                )
            try:
                page.goto(self.SEARCH_HOME, wait_until="domcontentloaded", timeout=40000)
            except Exception:
                state_error = self._search_state_error(hb, page)
                return AdapterResult(success=False, error=state_error or "INSTAGRAM_NETWORK_UNAVAILABLE")

            if not self._is_official_search_route(page.url):
                state_error = self._search_state_error(hb, page)
                return AdapterResult(success=False, error=state_error or "INSTAGRAM_SEARCH_CAPABILITY_UNAVAILABLE: official search route not observed")

            hb.pause(0.3, 0.7)
            try:
                page.wait_for_selector(self.SEARCH_INPUT_SELECTOR, state="visible", timeout=5000)
            except Exception:
                pass
            input_locator = self._visible_search_input(page)
            search_entry = "OBSERVED_VISIBLE_SEARCH_INPUT"
            if input_locator is None and self._click_observed_search_button(page):
                search_entry = "OBSERVED_PUBLIC_SEARCH_BUTTON"
                try:
                    page.wait_for_selector(self.SEARCH_INPUT_SELECTOR, state="visible", timeout=5000)
                except Exception:
                    pass
                input_locator = self._visible_search_input(page)
            if input_locator is None:
                state_error = self._search_state_error(hb, page)
                return AdapterResult(success=False, error=state_error or "INSTAGRAM_SEARCH_CAPABILITY_UNAVAILABLE: official search input not observed")

            input_attributes = {
                "placeholder": input_locator.get_attribute("placeholder"),
                "aria_label": input_locator.get_attribute("aria-label"),
                "type": input_locator.get_attribute("type"),
            }
            search_scope = {
                "surface": "OFFICIAL_INSTAGRAM_SEARCH_UI",
                "entry_action": search_entry,
                "observed_path": urlsplit(page.url).path,
                "input_locator": "input[placeholder|aria-label] observed visible",
                "input_attributes": input_attributes,
                "result_scope": "main",
                "submitted_by": "Enter",
            }
            before = page.evaluate(self._SEARCH_DOM_SCRIPT) or {}
            before_media = {row.get("href_ref") for row in before.get("media", []) if row.get("href_ref")}
            try:
                input_locator.fill(keyword)
                input_locator.press("Enter")
            except Exception:
                state_error = self._search_state_error(hb, page)
                return AdapterResult(success=False, error=state_error or "INSTAGRAM_SEARCH_CAPABILITY_UNAVAILABLE: exact query submission failed")
            # Observe asynchronous search results, rather than assuming a short
            # Python sleep establishes that the browser has finished searching.
            try:
                page.wait_for_function(
                    "arg => { const d=(" + self._SEARCH_DOM_SCRIPT + ")(); "
                    "const norm=s=>(s||'').replace(/\\s+/g,' ').trim().toLowerCase(); "
                    "return d.no_results || d.media.some(r=>!arg.before.includes(r.href_ref)) "
                    "|| d.profiles.some(r=>r.labels.some(s=>norm(s)===norm(arg.query))); }",
                    arg={"before": list(before_media), "query": keyword}, timeout=12000,
                )
            except Exception:
                # An absent exact result is classified from the actual page
                # below; timeout itself neither invents an empty result nor login.
                pass

            if not self._is_official_search_route(page.url):
                state_error = self._search_state_error(hb, page)
                return AdapterResult(success=False, error=state_error or "INSTAGRAM_SEARCH_CAPABILITY_UNAVAILABLE: search left official search route")

            observed = page.evaluate(self._SEARCH_DOM_SCRIPT) or {}
            if not observed.get("main_observed"):
                state_error = self._search_state_error(hb, page)
                return AdapterResult(success=False, error=state_error or "INSTAGRAM_SEARCH_CAPABILITY_UNAVAILABLE: result main not observed")
            state_error = self._search_state_error(hb, page)
            if state_error:
                return AdapterResult(success=False, error=state_error)

            metadata = {"query": keyword, "search_ui_scope": search_scope}
            media_rows = self._validated_media_rows(observed.get("media", []))
            media_rows = [row for row in media_rows if row.get("href_ref") not in before_media]
            if media_rows:
                notes = self._parse_cards(media_rows, result_limit, metadata)
                if notes:
                    return AdapterResult(success=True, notes=notes, raw_count=len(notes))
                return AdapterResult(success=False, error="INSTAGRAM_EXACT_TOPIC_DISCOVERY_UNAVAILABLE: native post links had no usable preview")

            matching_profiles = self._matching_profile_results(
                observed.get("profiles", []), keyword
            )
            if matching_profiles:
                notes = []
                for profile in matching_profiles[:3]:
                    profile_url = profile["url"]
                    try:
                        page.goto(profile_url, wait_until="domcontentloaded", timeout=40000)
                    except Exception:
                        state_error = self._search_state_error(hb, page)
                        return AdapterResult(success=False, error=state_error or "INSTAGRAM_NETWORK_UNAVAILABLE: matched public profile could not be opened")
                    if not self._is_observed_profile_url(page.url, profile["handle"]):
                        state_error = self._search_state_error(hb, page)
                        return AdapterResult(success=False, error=state_error or "INSTAGRAM_PROFILE_IDENTITY_MISMATCH: final profile path did not match observed href")
                    hb.pause(0.6, 1.1)
                    try:
                        page.wait_for_selector('main a[href*="/p/"],main a[href*="/reel/"]',
                                               timeout=12000)
                    except Exception:
                        pass
                    profile_dom = page.evaluate(self._SEARCH_DOM_SCRIPT) or {}
                    if not profile_dom.get("main_observed"):
                        state_error = self._search_state_error(hb, page)
                        return AdapterResult(success=False, error=state_error or "INSTAGRAM_SEARCH_CAPABILITY_UNAVAILABLE: matched profile content scope unavailable")
                    state_error = self._search_state_error(hb, page)
                    if state_error:
                        return AdapterResult(success=False, error=state_error)
                    profile_media = self._validated_media_rows(profile_dom.get("media", []))
                    discovery = {
                        "native_profile_ref": profile["url"],
                        "observed_href_ref": profile["href_ref"],
                        "observed_display_name": profile["display_name"],
                        "display_name_claim": "EXACT_NORMALIZED_QUERY_MATCH",
                        "query": keyword,
                        "source_locator": profile.get("locator"),
                        "profile_path_observed": urlsplit(page.url).path,
                    }
                    profile_meta = {**metadata, "native_profile_discovery": discovery}
                    notes.extend(self._parse_cards(profile_media, result_limit - len(notes), profile_meta))
                    if len(notes) >= result_limit:
                        break
                if notes:
                    return AdapterResult(success=True, notes=notes[:result_limit], raw_count=min(len(notes), result_limit))
                return AdapterResult(success=False, error="INSTAGRAM_EXACT_TOPIC_DISCOVERY_UNAVAILABLE: matching public profile exposed no native post links")

            if observed.get("no_results"):
                return AdapterResult(success=True, notes=[], raw_count=0)

            state_error = self._search_state_error(hb, page)
            if state_error:
                return AdapterResult(success=False, error=state_error)
            if observed.get("profiles"):
                return AdapterResult(success=False, error="INSTAGRAM_EXACT_TOPIC_DISCOVERY_UNAVAILABLE: no complete display-name match or native post link observed")
            return AdapterResult(success=False, error="INSTAGRAM_SEARCH_CAPABILITY_UNAVAILABLE: no result or explicit no-results state observed")
        finally:
            if hb is not None:
                hb.close()

    def _search_by_hashtag(self, hb, page, keyword, max_results,
                           native_hashtag, native_topic_reference):
        reference = native_topic_reference if isinstance(native_topic_reference, dict) else {}
        literal = reference.get("literal")
        tag = self._to_tag(literal)
        if (not isinstance(native_hashtag, str) or not tag or tag != native_hashtag
                or literal != "#" + native_hashtag):
            return AdapterResult(success=False, error="INSTAGRAM_NATIVE_HASHTAG_REFERENCE_INVALID")

        encoded_tag = quote(native_hashtag, safe="._~-")
        target_url = f"https://www.instagram.com/explore/tags/{encoded_tag}/"
        tag_observation = {
            "original_query": keyword,
            "native_hashtag_literal": literal,
            "native_hashtag": native_hashtag,
            "reference": dict(reference),
            "claim_scope": "REVIEWED_SEED_SEARCH_TERM_ONLY_NOT_POST_FACT",
        }
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=40000)
        except Exception:
            state_error = self._search_state_error(hb, page)
            return AdapterResult(success=False, error=state_error or "INSTAGRAM_NETWORK_UNAVAILABLE")

        state_error = self._search_state_error(hb, page)
        if state_error:
            return AdapterResult(success=False, error=state_error)
        if not self._is_official_hashtag_results_url(page.url, native_hashtag):
            return AdapterResult(success=False, error="INSTAGRAM_HASHTAG_IDENTITY_MISMATCH")

        try:
            page.wait_for_function(
                "() => { const d=(" + self._SEARCH_DOM_SCRIPT + ")(); "
                "return d.no_results || d.media.length > 0; }",
                timeout=12000,
            )
        except Exception:
            # Classify the resulting page below; a timeout is not evidence of
            # an empty result and does not trigger a keyword-search fallback.
            pass

        state_error = self._search_state_error(hb, page)
        if state_error:
            return AdapterResult(success=False, error=state_error)
        if not self._is_official_hashtag_results_url(page.url, native_hashtag):
            return AdapterResult(success=False, error="INSTAGRAM_HASHTAG_IDENTITY_MISMATCH")
        observed = page.evaluate(self._SEARCH_DOM_SCRIPT) or {}
        if not observed.get("main_observed"):
            return AdapterResult(success=False, error="INSTAGRAM_HASHTAG_RESULTS_UNAVAILABLE")

        metadata = {
            "query": keyword,
            "native_hashtag_observation": tag_observation,
            "search_ui_scope": {
                "surface": "OFFICIAL_INSTAGRAM_NATIVE_HASHTAG_RESULTS",
                "requested_path": urlsplit(target_url).path,
                "observed_path": urlsplit(page.url).path,
                "result_scope": "main",
            },
        }
        rows = self._validated_media_rows(observed.get("media", []))
        if rows:
            notes = self._parse_cards(rows, max_results, metadata)
            if notes:
                return AdapterResult(success=True, notes=notes, raw_count=len(notes))
            return AdapterResult(success=False, error="INSTAGRAM_HASHTAG_POST_PREVIEWS_UNAVAILABLE")
        if observed.get("no_results"):
            return AdapterResult(success=True, notes=[], raw_count=0)
        return AdapterResult(success=False, error="INSTAGRAM_HASHTAG_RESULTS_UNAVAILABLE")

    def _parse_cards(self, rows, max_results, metadata=None):
        notes = []
        for row in rows or []:
            code = row.get("code")
            if not code:
                continue
            kind = "reel" if row.get("kind") in ("reel", "reels") else "p"
            author, likes, body_parts, likes_display = "", None, [], None
            lines = row.get("lines") or []
            if lines:
                author = lines[0] if re.fullmatch(r"[A-Za-z0-9._]{1,40}", lines[0]) else ""
                rest = lines[1:] if author else lines
                if rest and self._looks_like_count(rest[0]):
                    likes_display = rest[0]
                    likes = self._ig_num(likes_display); rest = rest[1:]
                body_parts = rest
            alt = re.sub(r"\s+", " ", (row.get("alt") or "")).strip()
            body_text = re.sub(r"\s+", " ", " ".join(body_parts)).strip()
            # 头像占位 alt（“XX的头像”）不可用，回退到卡片文本正文
            if not alt or re.search(r"头像|profile picture", alt):
                caption = body_text
            else:
                caption = body_text or alt
            url = f"https://www.instagram.com/{kind}/{code}/"
            discovery = {
                "query": (metadata or {}).get("query"),
                "search_ui_scope": (metadata or {}).get("search_ui_scope"),
                "native_hashtag_observation": (metadata or {}).get("native_hashtag_observation"),
                "native_profile_discovery": (metadata or {}).get("native_profile_discovery"),
                "native_post_ref": url,
                "native_post_locator": row.get("locator"),
                "body_source": "anchor.innerText" if body_text else ("image.alt" if caption else None),
                "body_source_locator": (row.get("locator") + "@innerText" if body_text and row.get("locator")
                                        else (row.get("cover_locator") + "@alt" if caption and row.get("cover_locator") else None)),
                "preview_limitation": "Search or public profile grid preview only; full caption and publication time require exact post detail.",
            }
            notes.append(self._make_note(
                title=caption[:80] or f"Instagram {kind} {code}",
                content=caption,
                url=url,
                author=author,
                publish_date="",  # 首屏无发布日期，留空不臆造；详情补抓
                likes=likes,
                source_platform=self.platform_name,
                raw_data={
                    "engine": "instagram_explore_search_dom",
                    "shortcode": code,
                    "media_type": "reel" if kind == "reel" else "post",
                    "cover": row.get("cover") or "",
                    "media_hints": ([{"kind": "image", "url_hint": row.get("cover"),
                                      "locator": row.get("cover_locator")}] if row.get("cover") else []),
                    "search_discovery": discovery,
                    "native_hashtag_observation": (metadata or {}).get("native_hashtag_observation"),
                    "image_alt": alt,
                    "discovery_body_text": body_text,
                    "body_kind": "SEARCH_PREVIEW",
                    "body_state": "SEARCH_PREVIEW_ONLY_NOT_NATIVE_FULL_POST",
                    "metric_display": {"likes": likes_display},
                    "needs_detail": True,
                    "media_bytes_saved": False,
                    "artifact_created": False,
                },
            ))
            if len(notes) >= max_results:
                break
        return notes

    @staticmethod
    def _official_instagram_path(url):
        try:
            parsed = urlsplit(str(url or ""))
        except Exception:
            return None
        if (parsed.scheme.lower() != "https" or parsed.username or parsed.password
                or (parsed.hostname or "").lower() not in {"instagram.com", "www.instagram.com"}):
            return None
        return parsed.path

    @classmethod
    def _is_official_search_route(cls, url):
        path = cls._official_instagram_path(url)
        normalized = path.rstrip("/") if path else ""
        return normalized in {"", "/", "/explore", "/explore/search"} or normalized.startswith("/explore/search/")

    @classmethod
    def _is_official_hashtag_results_url(cls, url, native_hashtag):
        try:
            parts = urlsplit(str(url or ""))
            port = parts.port
        except (TypeError, ValueError):
            return False
        if (parts.scheme.lower() != "https" or parts.username or parts.password
                or (parts.hostname or "").lower() not in {"instagram.com", "www.instagram.com"}
                or port not in (None, 443)):
            return False
        pieces = parts.path.rstrip("/").split("/")
        if len(pieces) == 4 and pieces[1:3] == ["explore", "tags"]:
            observed_tag = pieces[3]
        elif len(pieces) == 3 and pieces[1] == "popular":
            observed_tag = pieces[2]
        else:
            return False
        return unquote(observed_tag).casefold() == str(native_hashtag).casefold()

    @classmethod
    def _is_observed_profile_url(cls, url, handle):
        path = cls._official_instagram_path(url)
        return bool(path and path.rstrip("/") == f"/{handle}")

    def _visible_search_input(self, page):
        inputs = page.locator(self.SEARCH_INPUT_SELECTOR)
        for index in range(inputs.count()):
            candidate = inputs.nth(index)
            try:
                if candidate.is_visible() and candidate.is_enabled():
                    return candidate
            except Exception:
                continue
        return None

    def _click_observed_search_button(self, page):
        """Click one uniquely observed official search button if no input exists."""
        try:
            observed = page.evaluate(self._SEARCH_BUTTON_SCRIPT) or {}
            if observed.get("match_count") != 1:
                return False
            index = observed.get("index")
            if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                return False
            controls = page.locator('button,[role="button"]')
            button = controls.nth(index)
            if not button.is_visible() or not button.is_enabled():
                return False
            button.click(timeout=5000)
            return True
        except Exception:
            return False

    @classmethod
    def _validated_media_rows(cls, rows):
        output, seen = [], set()
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            if row.get("observed_origin") not in {"https://instagram.com", "https://www.instagram.com"}:
                continue
            href_ref = row.get("href_ref")
            if not isinstance(href_ref, str):
                continue
            match = re.fullmatch(r"/(p|reel|reels)/([A-Za-z0-9_-]+)/?", href_ref)
            if not match:
                continue
            kind = "reel" if match.group(1) in {"reel", "reels"} else "p"
            code = match.group(2)
            key = (kind, code)
            if key in seen:
                continue
            seen.add(key)
            output.append({
                "kind": kind,
                "code": code,
                "href_ref": f"/{kind}/{code}/",
                "locator": row.get("locator"),
                "lines": [line for line in row.get("lines", []) if isinstance(line, str)][:24],
                "alt": row.get("alt") if isinstance(row.get("alt"), str) else "",
                "cover": cls._safe_media_url_hint(row.get("cover")),
                "cover_locator": row.get("cover_locator"),
            })
        return output

    @staticmethod
    def _safe_media_url_hint(url):
        if not isinstance(url, str) or not url:
            return None
        try:
            parsed = urlsplit(url)
        except Exception:
            return None
        host = (parsed.hostname or "").lower()
        allowed = (host in {"instagram.com", "cdninstagram.com", "fbcdn.net"}
                   or host.endswith(".instagram.com") or host.endswith(".cdninstagram.com")
                   or host.endswith(".fbcdn.net"))
        if parsed.scheme.lower() != "https" or not allowed or parsed.username or parsed.password:
            return None
        return f"https://{host}{parsed.path}"

    @staticmethod
    def _matching_profile_results(rows, keyword):
        normalized_query = re.sub(r"\s+", " ", keyword).strip().casefold()
        results, seen = [], set()
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            handle = row.get("handle")
            href_ref = row.get("href_ref")
            if (not isinstance(handle, str) or not re.fullmatch(r"[A-Za-z0-9._]{1,40}", handle)
                    or handle.lower() in {"explore", "accounts", "direct", "stories", "p", "reel", "reels", "tags", "about", "developer", "legal"}
                    or row.get("observed_origin") not in {"https://instagram.com", "https://www.instagram.com"}
                    or href_ref != f"/{handle}/"):
                continue
            url = f"https://www.instagram.com/{handle}/"
            if url in seen:
                continue
            labels = row.get("labels") if isinstance(row.get("labels"), list) else []
            exact_label = next((label for label in labels if isinstance(label, str)
                                and re.sub(r"\s+", " ", label).strip().casefold() == normalized_query), None)
            if exact_label is None:
                continue
            seen.add(url)
            results.append({"handle": handle, "href_ref": href_ref, "url": url,
                            "display_name": exact_label, "locator": row.get("locator")})
        return results

    @staticmethod
    def _search_state_error(hb, page, *, success_selector=None):
        """Classify explicit Instagram auth evidence and shared page failures.

        Generic footer/navigation copy such as ``登录`` or ``Log in`` is not
        evidence that the current session expired.  Authentication is known
        only from Instagram's official login route, visible credential fields,
        or an explicit login-required/expired prompt.
        """
        official_page = False
        login_path = False
        try:
            parts = urlsplit(str(page.url or ""))
            try:
                port = parts.port
            except ValueError:
                port = -1
            official_page = bool(
                parts.scheme.lower() == "https"
                and (parts.hostname or "").lower() in {"instagram.com", "www.instagram.com"}
                and port in (None, 443)
                and not parts.username and not parts.password
            )
            login_path = official_page and parts.path.rstrip("/") == "/accounts/login"
        except Exception:
            pass
        if login_path:
            return "INSTAGRAM_AUTH_REQUIRED"

        if official_page:
            try:
                fields = page.locator('input[name="username"],input[name="password"]')
                for index in range(fields.count()):
                    try:
                        if fields.nth(index).is_visible():
                            return "INSTAGRAM_AUTH_REQUIRED"
                    except Exception:
                        continue
            except Exception:
                pass

        try:
            state = hb.detect_state(
                page,
                extra_markers={
                    PageState.AUTH_FAILED: [
                        "log in to continue", "please log in to continue",
                        "sign in to continue", "登录后查看", "登录后即可",
                        "会话已过期", "登录态失效",
                    ],
                    PageState.CAPTCHA: ["confirm", "captcha", "验证", "suspicious", "challenge", "安全验证"],
                    PageState.BLOCKED: ["try again later", "请稍等", "unusual", "rate limit", "report a problem", "暂时限制"],
                },
                success_selector=success_selector,
            )
        except Exception:
            return None
        return {
            PageState.AUTH_FAILED: "INSTAGRAM_AUTH_REQUIRED",
            PageState.CAPTCHA: "INSTAGRAM_CHALLENGE_REQUIRED",
            PageState.BLOCKED: "INSTAGRAM_RATE_LIMITED",
            PageState.NETWORK_ERROR: "INSTAGRAM_NETWORK_UNAVAILABLE",
        }.get(state)

    # ---------- 详情 ----------
    def detail(self, shortcode: str, media_type: str = "post") -> AdapterResult:
        """进帖子详情页补抓真实发布时间、完整 caption、评论数、位置。

        时间口径：publish_date 必须从 <time datetime> 取真实 ISO，取不到留空
        并标 needs_detail=True，绝不臆造。只读，不硬刚风控。
        """
        if (not isinstance(shortcode, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]+", shortcode)):
            return AdapterResult(success=False, error="shortcode 为空")
        try:
            return self._detail_browser(shortcode, "reel" if media_type == "reel" else "post")
        except Exception as e:
            logger.error("Instagram 详情采集异常 error_type=%s", type(e).__name__)
            return AdapterResult(success=False, error="Instagram provider unavailable")

    def _detail_browser(self, shortcode, media_type, proxy=None) -> AdapterResult:
        kind = "reel" if media_type == "reel" else "p"
        url = f"https://www.instagram.com/{kind}/{shortcode}/"
        hb = HumanBrowser(
            cdp_url=configured_readonly_worker_url("instagram"),
            auto_ensure=False,
            launch_url="about:blank",
        )
        hb.connect()
        inject_into_context(hb._context, "instagram")
        page = None
        try:
            page = hb.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=40000)

            rendered = True
            try:
                page.wait_for_selector("time[datetime], article", timeout=18000)
            except Exception:
                rendered = False
            hb.pause(1.0, 2.0)

            try:
                final_parts = urlsplit(page.url)
                final_port = final_parts.port
            except (TypeError, ValueError):
                final_parts = None
                final_port = None
            final_match = (re.fullmatch(r"/(p|reel|reels)/([A-Za-z0-9_-]+)/?", final_parts.path)
                           if final_parts else None)
            final_url_is_official = bool(
                final_parts
                and final_parts.scheme.lower() == "https"
                and final_parts.hostname in {"instagram.com", "www.instagram.com"}
                and final_port in (None, 443)
                and not final_parts.username and not final_parts.password
            )

            def observed_page_failure():
                state_error = self._search_state_error(
                    hb, page, success_selector="time[datetime], article",
                )
                return {
                    "INSTAGRAM_AUTH_REQUIRED": "Instagram 登录态失效，详情页未能读取",
                    "INSTAGRAM_CHALLENGE_REQUIRED": "Instagram 出现确认/人机验证，详情读取停止",
                    "INSTAGRAM_RATE_LIMITED": "Instagram 触发频控，详情读取停止",
                    "INSTAGRAM_NETWORK_UNAVAILABLE": "Instagram 网络或只读 Worker 暂不可用",
                }.get(state_error)

            if (not final_url_is_official or not final_match
                    or final_match.group(2) != shortcode):
                hint = observed_page_failure()
                if hint:
                    return AdapterResult(success=False, error=hint)
                return AdapterResult(
                    success=False,
                    error="INSTAGRAM_IDENTITY_MISMATCH: final post path did not match requested shortcode",
                )
            actual_kind = "reel" if final_match.group(1) in ("reel", "reels") else "post"
            canonical_url = f"https://www.instagram.com/{'reel' if actual_kind == 'reel' else 'p'}/{shortcode}/"

            data = page.evaluate(
                r"""() => {
                    const out = {publish_time:'', native_time_locator:null, caption:'', caption_source:null,
                        caption_locator:null, image_alts:[], media_hints:[], native_media_id:null,
                        media_id_locator:null, comment_count:null, likes:null, comment_count_display:null,
                        likes_display:null, comment_count_locator:null, likes_locator:null,
                        location:'', media_type:'post', author:''};
                    const article = document.querySelector('article');
                    const cssPath = (el, root) => {
                        if (!el) return null;
                        const parts=[];
                        while (el && el !== root) {
                            const tag=el.tagName.toLowerCase();
                            let index=1, sibling=el.previousElementSibling;
                            while (sibling) { if (sibling.tagName === el.tagName) index++; sibling=sibling.previousElementSibling; }
                            parts.unshift(`${tag}:nth-of-type(${index})`);
                            el=el.parentElement;
                        }
                        return (root && root.tagName ? root.tagName.toLowerCase() : 'document')
                            + (parts.length ? ' > ' + parts.join(' > ') : '');
                    };
                    const t = (article && article.querySelector('time[datetime]')) || document.querySelector('time[datetime]');
                    if (t) {
                        out.publish_time = t.getAttribute('datetime') || '';
                        out.native_time_locator = cssPath(t, article || document.body);
                    }
                    const h1 = article && article.querySelector('h1');
                    if (h1) {
                        out.caption = h1.innerText || '';
                        if (out.caption.trim()) { out.caption_source = 'article h1'; out.caption_locator = cssPath(h1, article); }
                    }
                    const safeMediaHint = (src, kind, el) => {
                        if (!src) return null;
                        try {
                            const u = new URL(src, window.location.href);
                            const host = u.hostname.toLowerCase();
                            const allowed = host === 'instagram.com' || host.endsWith('.instagram.com')
                                || host === 'cdninstagram.com' || host.endsWith('.cdninstagram.com')
                                || host === 'fbcdn.net' || host.endsWith('.fbcdn.net');
                            if (u.protocol !== 'https:' || !allowed) return null;
                            return {kind, url_hint:u.origin + u.pathname, locator:cssPath(el, article)};
                        } catch (_) { return null; }
                    };
                    const seenHints = new Set();
                    const addHint = hint => {
                        if (!hint) return;
                        const key = hint.kind + '|' + hint.url_hint;
                        if (seenHints.has(key)) return;
                        seenHints.add(key); out.media_hints.push(hint);
                    };
                    const imgs = article ? article.querySelectorAll('img') : [];
                    for (const img of imgs) {
                        const alt = (img.alt || '').trim();
                        const isProfile = /头像|profile picture|头像照/i.test(alt);
                        if (alt && !isProfile && alt.length > 3) {
                            out.image_alts.push(alt);
                        }
                        if (!isProfile && !img.closest('header')) addHint(safeMediaHint(img.currentSrc || img.src, 'image', img));
                    }
                    if (article) {
                        for (const video of article.querySelectorAll('video')) {
                            addHint(safeMediaHint(video.currentSrc || video.src, 'video', video));
                            if (video.poster) addHint(safeMediaHint(video.poster, 'image', video));
                            for (const source of video.querySelectorAll('source[src]')) {
                                addHint(safeMediaHint(source.src, 'video', source));
                            }
                        }
                        const mediaIdNode = (article.matches('[data-media-id]') && article)
                            || article.querySelector('[data-media-id]');
                        if (mediaIdNode) {
                            const value = mediaIdNode.getAttribute('data-media-id') || '';
                            if (/^[0-9]+$/.test(value)) {
                                out.native_media_id = value;
                                out.media_id_locator = cssPath(mediaIdNode, article) + '@data-media-id';
                            }
                        }
                    }
                    const authorLinks = article ? article.querySelectorAll('a[href^="/"]') : [];
                    for (const a of authorLinks) {
                        const href = a.getAttribute('href') || '';
                        const m = href.match(/^\/([A-Za-z0-9._]{1,40})\/?$/);
                        if (m && !['p','reel','explore','accounts','direct','stories','tags'].includes(m[1])) {
                            out.author = m[1]; break;
                        }
                    }
                    const body = article ? article.innerText || '' : '';
                    const findMetric = (pattern, label) => {
                        if (!article) return null;
                        let best = null;
                        for (const el of article.querySelectorAll('span,button,a,div')) {
                            const text = (el.innerText || '').trim();
                            const match = text.match(pattern);
                            if (match && (!best || text.length < best.display.length)) {
                                best = {value:match[1].trim(), display:text, locator:cssPath(el, article)};
                            }
                        }
                        if (best) return best;
                        const match = body.match(new RegExp('(?:^|\\n)([0-9][0-9,.]*(?:\\s*[kKmMbB万亿])?)\\s*(' + label + ')(?=\\n|$)', 'i'));
                        return match ? {value:match[1].trim(), display:match[0].trim(), locator:'article.innerText'} : null;
                    };
                    const cm = findMetric(/^([0-9][0-9,.]*(?:\s*[kKmMbB万亿])?)\s*(comments?|条评论)$/i, 'comments?|条评论');
                    if (cm) { out.comment_count = cm.value; out.comment_count_display = cm.display; out.comment_count_locator = cm.locator; }
                    const lm = findMetric(/^([0-9][0-9,.]*(?:\s*[kKmMbB万亿])?)\s*(likes?|次赞)$/i, 'likes?|次赞');
                    if (lm) { out.likes = lm.value; out.likes_display = lm.display; out.likes_locator = lm.locator; }
                    const loc = article && article.querySelector('a[href*="/explore/locations/"]');
                    if (loc) out.location = (loc.innerText || '').trim();
                    out.article_observed = !!article;
                    return out;
                }""")

            if not data.get("article_observed") or not rendered:
                hint = observed_page_failure()
                if hint:
                    return AdapterResult(success=False, error=hint)

            publish_date = data.get("publish_time") if isinstance(data.get("publish_time"), str) else ""
            caption = data.get("caption") if isinstance(data.get("caption"), str) else ""
            needs_detail = not bool(publish_date.strip() and caption.strip())
            author = (data.get("author") or "").strip()
            likes = self._ig_num(data.get("likes"))
            comments = self._ig_num(data.get("comment_count"))
            metric_observations = {
                "likes": {
                    "value": likes,
                    "display": data.get("likes_display"),
                    "locator": data.get("likes_locator"),
                    "status": "OBSERVED" if data.get("likes_display") is not None else "NOT_OBSERVED",
                },
                "comments": {
                    "value": comments,
                    "display": data.get("comment_count_display"),
                    "locator": data.get("comment_count_locator"),
                    "status": "OBSERVED" if data.get("comment_count_display") is not None else "NOT_OBSERVED",
                },
            }
            native_media_id = data.get("native_media_id")
            if not isinstance(native_media_id, str) or not re.fullmatch(r"[0-9]+", native_media_id):
                native_media_id = None

            note = self._make_note(
                title=caption[:80] or f"Instagram {shortcode}",
                content=caption,
                url=canonical_url,
                author=author,
                publish_date=publish_date,
                likes=likes,
                comments=comments,
                source_platform=self.platform_name,
                raw_data={
                    "engine": "instagram_detail_dom",
                    "shortcode": shortcode,
                    "native_identity": {
                        "shortcode": shortcode,
                        "requested_shortcode": shortcode,
                        "locator": "final_url.pathname",
                        "status": "OBSERVED_MATCH",
                    },
                    "media_type": actual_kind,
                    "native_publish_time": publish_date or None,
                    "native_time_locator": data.get("native_time_locator"),
                    "comment_count": comments,
                    "likes": likes,
                    "metrics": {"likes": likes, "comments": comments},
                    "metric_display": {"likes": data.get("likes_display"),
                                       "comments": data.get("comment_count_display")},
                    "metric_observations": metric_observations,
                    "image_alts": data.get("image_alts") or [],
                    "media_hints": data.get("media_hints") or [],
                    "media_state": "URL_HINTS_OBSERVED" if data.get("media_hints") else "NOT_OBSERVED",
                    "media_bytes_saved": False,
                    "artifact_created": False,
                    "media_id": native_media_id,
                    "media_id_locator": data.get("media_id_locator") if native_media_id else None,
                    "caption_source": data.get("caption_source"),
                    "caption_locator": data.get("caption_locator"),
                    "caption_completeness": ("NATIVE_CAPTION_DOM_COMPLETENESS_UNKNOWN" if caption.strip()
                                             else "NATIVE_CAPTION_NOT_OBSERVED"),
                    "body_state": ("NATIVE_CAPTION_DOM_COMPLETENESS_UNKNOWN" if caption.strip()
                                   else "NATIVE_BODY_UNAVAILABLE"),
                    "location": data.get("location", ""),
                    "needs_detail": needs_detail,
                },
            )
            return AdapterResult(success=True, notes=[note], raw_count=1)
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass
            hb.close()

    # ---------- 评论 ----------
    def comments(self, shortcode: str, max_comments: int = 20, *, cursor=None, include_replies=False) -> AdapterResult:
        """进详情页解析评论区（只读，绝不发表评论）。

        评论列表放在返回 note 的 raw_data["comments"] 中，每条含
        author / content / publish_time / likes。评论区需滚动加载。
        """
        if not shortcode or not shortcode.strip():
            return AdapterResult(success=False, error="shortcode 为空")
        try:
            return self._native_read("comments", shortcode.strip(), max_comments, cursor=cursor, include_replies=include_replies)
        except Exception as e:
            diagnostic = log_instagram_failure("comments", e)
            return AdapterResult(success=False, error=diagnostic["error_code"], diagnostics=diagnostic)

    def _comments_browser(self, shortcode, max_comments, proxy=None) -> AdapterResult:
        url = f"https://www.instagram.com/p/{shortcode}/"
        hb = HumanBrowser(
            cdp_url=configured_readonly_worker_url("instagram"),
            auto_ensure=False,
            launch_url="about:blank",
        )
        hb.connect()
        inject_into_context(hb._context, "instagram")
        page = None
        try:
            page = hb.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=40000)

            rendered = True
            try:
                page.wait_for_selector("time[datetime], article", timeout=18000)
            except Exception:
                rendered = False
            hb.pause(1.0, 2.0)

            for _ in range(4):
                hb.human_scroll(page, total_px=600, rounds=2)
                hb.pause(1.0, 2.0)
                cnt = page.evaluate(
                    r"""() => {
                        const candidates = document.querySelectorAll('ul li, div[role="button"]');
                        let n = 0;
                        for (const el of candidates) {
                            if (el.querySelector('time[datetime]') && el.querySelector('a[href^="/"]')) n++;
                        }
                        return n;
                    }""")
                if cnt >= max_comments:
                    break

            raw_comments = page.evaluate(
                r"""() => {
                    const out = [];
                    const seen = new Set();
                    const all = document.querySelectorAll('*');
                    for (const el of all) {
                        const timeEl = el.querySelector(':scope > time[datetime], time[datetime]');
                        if (!timeEl) continue;
                        const authorLink = el.querySelector('a[href^="/"]');
                        if (!authorLink) continue;
                        const href = authorLink.getAttribute('href') || '';
                        const m = href.match(/^\/([A-Za-z0-9._]{1,40})\/?$/);
                        if (!m) continue;
                        const author = m[1];
                        if (['p','reel','explore','accounts','direct','stories','tags'].includes(author)) continue;
                        const textNodes = [];
                        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
                        let node;
                        while ((node = walker.nextNode())) {
                            const t = (node.textContent || '').trim();
                            if (t && t !== author) textNodes.push(t);
                        }
                        const content = textNodes.join(' ').trim();
                        const key = author + '|' + content.slice(0, 40);
                        if (seen.has(key)) continue;
                        seen.add(key);
                        let likes = null;
                        const likeText = el.innerText || '';
                        const lm = likeText.match(/(\d[\d,.]*)\s*(likes?|次赞)/i);
                        if (lm && /^\d[\d,]*$/.test(lm[1])) likes = Number(lm[1].replace(/,/g,''));
                        const native = el.getAttribute('data-comment-id') || '';
                        const parent = el.getAttribute('data-parent-comment-id') || '';
                        out.push({
                            author: author,
                            content: content,
                            publish_time: timeEl.getAttribute('datetime') || '',
                            likes: likes,
                            platform_comment_id: /^\d+$/.test(native) ? native : null,
                            parent_comment_id: /^\d+$/.test(parent) ? parent : null,
                        });
                    }
                    return out;
                }""")

            comments_list = raw_comments or []
            if len(comments_list) > max_comments:
                comments_list = comments_list[:max_comments]

            if not comments_list and not rendered:
                state_error = self._search_state_error(
                    hb, page, success_selector="time[datetime], article",
                )
                hint = {
                    "INSTAGRAM_AUTH_REQUIRED": "Instagram 登录态失效，请更新 Cookie 或在代理 Profile 重新登录",
                    "INSTAGRAM_CHALLENGE_REQUIRED": "Instagram 出现确认/人机验证，需人工通过后再采",
                    "INSTAGRAM_RATE_LIMITED": "Instagram 触发频控，按熔断退避不硬刚",
                    "INSTAGRAM_NETWORK_UNAVAILABLE": "代理连接异常或 Instagram 不可达",
                }.get(state_error)
                if hint:
                    return AdapterResult(success=False, error=hint)

            note = self._make_note(
                title="comments",
                content=f"{len(comments_list)} comments",
                url=url,
                author="instagram_user",
                source_platform=self.platform_name,
                raw_data={
                    "engine": "instagram_comments_dom",
                    "shortcode": shortcode,
                    "comments": comments_list,
                },
            )
            return AdapterResult(success=True, notes=[note], raw_count=len(comments_list),
                metadata={'pagination': {'request_cursor': None, 'next_cursor': None,
                    'exhausted': None, 'page_complete': True,
                    'coverage_scope': 'LOADED_COMMENT_DOM_ONLY',
                    'partial_reason': 'NATIVE_CURSOR_AND_TOTAL_NOT_OBSERVED'}})
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass
            hb.close()

    # ---------- 作者主页 ----------
    def creator(self, username: str) -> AdapterResult:
        """进作者主页解析粉丝/关注/帖子数、简介、是否认证（只读）。

        遇到私有账号/风控如实返回，不硬刚。
        """
        if not username or not username.strip():
            return AdapterResult(success=False, error="username 为空")
        try:
            return self._native_read("author", username.strip().lstrip("@"), 1)
        except Exception as e:
            diagnostic = log_instagram_failure("creator", e)
            return AdapterResult(success=False, error=diagnostic["error_code"], diagnostics=diagnostic)

    def _creator_browser(self, username, proxy=None) -> AdapterResult:
        url = f"https://www.instagram.com/{username}/"
        hb = HumanBrowser(
            cdp_url=configured_readonly_worker_url("instagram"),
            auto_ensure=False,
            launch_url="about:blank",
        )
        hb.connect()
        inject_into_context(hb._context, "instagram")
        page = None
        try:
            page = hb.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=40000)

            rendered = True
            try:
                page.wait_for_selector("header, section", timeout=18000)
            except Exception:
                rendered = False
            hb.pause(1.0, 2.0)

            data = page.evaluate(
                r"""() => {
                    const out = {followers_str:'', following_str:'', posts_str:'', bio:'', verified:false, is_private:false};
                    const body = document.body.innerText || '';
                    const fm = body.match(/(\d[\d,.]*[kKmM]?)\s*(followers|粉丝)/i);
                    if (fm) out.followers_str = fm[1];
                    const fg = body.match(/(\d[\d,.]*[kKmM]?)\s*(following|关注)/i);
                    if (fg) out.following_str = fg[1];
                    const pm = body.match(/(\d[\d,.]*[kKmM]?)\s*(posts|帖子)/i);
                    if (pm) out.posts_str = pm[1];
                    const header = document.querySelector('header');
                    if (header) {
                        const spans = header.querySelectorAll('span, h1');
                        const texts = [];
                        for (const s of spans) {
                            const t = (s.innerText || '').trim();
                            if (t && t.length > 2 && !/^\d/.test(t)) texts.push(t);
                        }
                        out.bio = texts.slice(-3).join(' ').trim();
                    }
                    const verifiedSvg = document.querySelector('svg[aria-label*="Verified"], svg[aria-label*="认证"]');
                    out.verified = !!verifiedSvg || /Verified|已认证/.test(body);
                    out.is_private = /This Account is Private|此账号为私密|私密账号/.test(body);
                    return out;
                }""")

            if not rendered:
                state_error = self._search_state_error(
                    hb, page, success_selector="header, section",
                )
                hint = {
                    "INSTAGRAM_AUTH_REQUIRED": "Instagram 登录态失效，请更新 Cookie 或在代理 Profile 重新登录",
                    "INSTAGRAM_CHALLENGE_REQUIRED": "Instagram 出现确认/人机验证，需人工通过后再采",
                    "INSTAGRAM_RATE_LIMITED": "Instagram 触发频控，按熔断退避不硬刚",
                    "INSTAGRAM_NETWORK_UNAVAILABLE": "代理连接异常或 Instagram 不可达",
                }.get(state_error)
                if hint:
                    return AdapterResult(success=False, error=hint)

            bio = (data.get("bio") or "").strip()
            note = self._make_note(
                title=username,
                content=bio,
                url=url,
                author=username,
                source_platform=self.platform_name,
                raw_data={
                    "engine": "instagram_creator_dom",
                    "username": username,
                    "followers_str": data.get("followers_str", ""),
                    "following_str": data.get("following_str", ""),
                    "posts_str": data.get("posts_str", ""),
                    "followers": self._ig_num(data.get("followers_str", "")),
                    "following": self._ig_num(data.get("following_str", "")),
                    "posts": self._ig_num(data.get("posts_str", "")),
                    "verified": bool(data.get("verified")),
                    "is_private": bool(data.get("is_private")),
                    "creator_type": "instagram_user",
                },
            )
            return AdapterResult(success=True, notes=[note], raw_count=1)
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass
            hb.close()

    @staticmethod
    def _native_time(value):
        if type(value) in {int, float}:
            try: return datetime.fromtimestamp(value, timezone.utc).isoformat()
            except (ValueError, OSError, OverflowError): pass
        return ""

    @staticmethod
    def _native_count(node, key, edge):
        return optional_int(node.get(key)) if node.get(key) is not None else optional_int((node.get(edge) or {}).get("count"))

    def _native_media_note(self, item):
        code = item.get("shortcode") or item.get("code")
        mid = item.get("pk") or item.get("id")
        if not isinstance(code, str) or re.fullmatch(r"[A-Za-z0-9_-]{3,64}", code) is None or not mid:
            return None
        owner = item.get("owner") or item.get("user") or {}
        caption = item.get("caption") or {}
        caption = caption.get("text") if isinstance(caption, dict) else caption if isinstance(caption, str) else None
        if caption is None:
            edges = (item.get("edge_media_to_caption") or {}).get("edges") or []
            caption = "\n".join(edge["node"]["text"] for edge in edges if isinstance(edge, dict)
                                and isinstance(edge.get("node"), dict) and isinstance(edge["node"].get("text"), str))
        hints = []
        def media_hints(media, locator):
            candidates = [(media.get("display_url") or media.get("display_uri"), "image"), (media.get("video_url"), "video")]
            candidates.extend((value.get("url"), "image") for value in (media.get("image_versions2") or {}).get("candidates") or [] if isinstance(value, dict))
            candidates.extend((value.get("url"), "video") for value in media.get("video_versions") or [] if isinstance(value, dict))
            for url, kind in candidates:
                safe = self._safe_media_url_hint(url) if isinstance(url, str) else None
                if safe:
                    hints.append({"kind": kind, "url": safe, "native_media_id": str(media.get("pk") or media.get("id") or mid),
                                  "locator": locator, "bytes_state": "NOT_ACQUIRED"})
        media_hints(item, "$.media")
        for child in item.get("carousel_media") or []:
            if isinstance(child, dict): media_hints(child, "$.media.carousel_media[]")
        for edge in (item.get("edge_sidecar_to_children") or {}).get("edges") or []:
            if isinstance(edge, dict) and isinstance(edge.get("node"), dict): media_hints(edge["node"], "$.media.edge_sidecar_to_children.edges[].node")
        return self._make_note(title=(caption or "")[:100], content=caption or "", url=f"https://www.instagram.com/p/{code}/",
            author=owner.get("username") or "", author_id=str(owner.get("pk") or owner.get("id") or ""),
            publish_date=self._native_time(item.get("taken_at") or item.get("taken_at_timestamp")),
            likes=self._native_count(item, "like_count", "edge_media_preview_like"),
            comments=self._native_count(item, "comment_count", "edge_media_to_comment"),
            cover=next((value["url"] for value in hints if value["kind"] == "image"), ""), source_platform="instagram",
            raw_data={"engine": "instagram_native_media", "shortcode": code, "media_id": str(mid), "author": owner,
                      "source_observation": item, "body_state": "PLATFORM_CAPTION", "media_hints": hints})

    def _native_read(self, capability, target, limit, *, cursor=None, include_replies=False):
        if re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", str(target)) is None or type(limit) is not int or not 1 <= limit <= 100:
            return AdapterResult(success=False, error="INSTAGRAM_INPUT_INVALID")
        try:
            validate_native_page_window_cursor(cursor)
            if isinstance(cursor, dict) and cursor.get('mode') == 'replies':
                validate_native_page_window_cursor(cursor.get('next_root'))
        except NativePageWindowError:
            return AdapterResult(success=False, error='INSTAGRAM_NATIVE_CURSOR_WINDOW_INVALID')
        if cursor is not None:
            if (not isinstance(cursor, dict) or cursor.get("mode") not in {"roots", "replies", "posts"}
                    or not isinstance(cursor.get("page"), dict) or len(cursor["page"]) > 1
                    or any(key not in {"after", "min_id", "max_id"} or not isinstance(value, str)
                           or not 1 <= len(value) <= 4096 or any(ord(c) < 32 for c in value) for key, value in cursor["page"].items())
                    or not isinstance(cursor.get("media_id"), str) or re.fullmatch(r"[0-9]{1,30}", cursor["media_id"]) is None):
                return AdapterResult(success=False, error="INSTAGRAM_NATIVE_CURSOR_INVALID")
            if cursor["mode"] == "replies" and (not isinstance(cursor.get("root_id"), str)
                    or re.fullmatch(r"[0-9]{1,30}", cursor["root_id"]) is None or not isinstance(cursor.get("pending_roots"), list)
                    or len(cursor["pending_roots"]) > 100 or any(not isinstance(v, str) or re.fullmatch(r"[0-9]{1,30}", v) is None for v in cursor["pending_roots"])):
                return AdapterResult(success=False, error="INSTAGRAM_NATIVE_CURSOR_INVALID")
            if (capability == 'author_posts' and cursor['mode'] != 'posts'
                    or capability == 'comments' and cursor['mode'] not in {'roots', 'replies'}
                    or capability == 'author'):
                return AdapterResult(success=False, error='INSTAGRAM_NATIVE_CURSOR_INVALID')
            if (capability == 'comments' and include_replies and 'reply_scope_unknown' in cursor
                    and type(cursor['reply_scope_unknown']) is not bool):
                return AdapterResult(success=False, error='INSTAGRAM_NATIVE_CURSOR_INVALID')
        worker, page = None, None
        capture = NativeReadCapture(hosts={"www.instagram.com", "i.instagram.com"}, paths=("/api/v1/", "/graphql"),
            request_keys={"shortcode", "code", "media_id", "mediaId", "id", "user_id", "username", "after", "before", "min_id", "max_id", "parent_comment_id", "comment_id", "first", "count"})
        try:
            worker = HumanBrowser(cdp_url=configured_readonly_worker_url("instagram"), auto_ensure=False, launch_url="about:blank")
            worker.connect()
            inject_into_context(worker._context, "instagram")
            page = worker.new_page(stealth=False)
            capture.attach(page)
            url = f"https://www.instagram.com/p/{target}/" if capability == "comments" else f"https://www.instagram.com/{target}/"
            page.goto(url, wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(1000)
            known_media, known_users = set(), {}
            def register(objects):
                for obj in objects:
                    for node in native_json_nodes(obj):
                        mid = node.get("pk") or node.get("id")
                        if capability == "comments" and (node.get("shortcode") or node.get("code")) == target and mid:
                            known_media.add(str(mid).split("_")[0])
                        if capability != "comments" and isinstance(node.get("username"), str) and node["username"].casefold() == target.casefold() and mid:
                            known_users[str(mid)] = node
            register(native_page_json(page))
            def select(observation):
                register(observation["objects"])
                if capability == "author" and known_users:
                    profiles = [node for node in known_users.values() if any(key in node for key in ("biography", "follower_count", "edge_followed_by", "edge_owner_to_timeline_media"))]
                    if profiles: return {"profile": profiles[0]}
                request = observation["request"]
                if any(str(request.get(key) or "") != value for key, value in (cursor or {}).get("page", {}).items()):
                    return None
                if cursor is None and any(request.get(key) for key in ("after", "min_id", "max_id")):
                    return None
                root = (cursor or {}).get("root_id")
                path = observation["path"]
                if capability == "comments":
                    match = re.search(r"/media/([0-9]+)(?:_[0-9]+)?/comments(?:/([0-9]+)/child_comments)?/?$", path)
                    requested_media = str(request.get("media_id") or request.get("mediaId") or request.get("id") or "").split("_")[0]
                    short_bound = (request.get("shortcode") or request.get("code")) == target
                    if match:
                        requested_media = match[1]
                    if not short_bound and requested_media not in known_media:
                        return None
                    media_id = requested_media if requested_media in known_media else next(iter(known_media), None)
                    if cursor and cursor["media_id"] != media_id:
                        return None
                    observed_parent = (match[2] if match else None) or request.get("parent_comment_id") or request.get("comment_id")
                    if bool(root) != bool(observed_parent) or root and str(observed_parent) != root:
                        return None
                else:
                    match = re.search(r"/feed/user/([0-9]+)/?$", path)
                    uid = str(request.get("id") or request.get("user_id") or (match[1] if match else ""))
                    if uid not in known_users:
                        return None
                    media_id = uid
                    if cursor and cursor["media_id"] != uid:
                        return None
                for obj in observation["objects"]:
                    for node in native_json_nodes(obj):
                        if capability == "comments" and isinstance(node.get("comments"), list):
                            return {"rows": node["comments"], "container": node, "media_id": media_id}
                        if capability == "author_posts" and isinstance(node.get("items"), list):
                            return {"rows": node["items"], "container": node, "media_id": media_id}
                        for key, connection in node.items():
                            allowed = ("comment" in key.lower()) if capability == "comments" else ("timeline" in key.lower() or "edge_owner_to_timeline_media" == key)
                            if allowed and isinstance(connection, dict) and isinstance(connection.get("edges"), list):
                                return {"rows": [edge.get("node") for edge in connection["edges"] if isinstance(edge, dict) and isinstance(edge.get("node"), dict)],
                                        "container": connection, "media_id": media_id}
                return None
            def advance(_step):
                if self._search_state_error(worker, page) in {"INSTAGRAM_AUTH_REQUIRED", "INSTAGRAM_CHALLENGE_REQUIRED", "INSTAGRAM_RATE_LIMITED", "INSTAGRAM_NETWORK_UNAVAILABLE"}:
                    return False
                return native_read_scroll(page, reply_id=(cursor or {}).get("root_id"), reply_attribute="data-comment-id")
            # SSR profile is already an actual native response, not an empty
            # placeholder requiring another request to count as observed.
            profile = next((node for node in known_users.values() if any(k in node for k in ("biography", "follower_count", "edge_followed_by"))), None)
            selected = {"profile": profile, "observed_prior_native_responses": 0} if capability == "author" and profile else capture.seek(page, select, advance, max_steps=16)
            if selected is None:
                failure = capture.failure() or {}
                code = failure.get("failure_class") or self._search_state_error(worker, page) or "NATIVE_PAGE_NOT_OBSERVED"
                return AdapterResult(success=False, error="INSTAGRAM_" + code, metadata={"failure_class": failure.get("failure_class"),
                    "http_status": failure.get("http_status"), "retry_after_seconds": failure.get("retry_after_seconds"),
                    "pagination": {"request_cursor": cursor, "next_cursor": None, "exhausted": None, "page_complete": False}})
            if capability == "author":
                profile = selected["profile"]
                uid = str(profile.get("pk") or profile.get("id"))
                return AdapterResult(success=True, notes=[self._make_note(title=profile.get("full_name") or target, content=profile.get("biography") or "",
                    url=url, author=target, author_id=uid, source_platform="instagram", raw_data={"engine": "instagram_native_profile", "username": target,
                        "native_user_id": uid, "followers": self._native_count(profile, "follower_count", "edge_followed_by"),
                        "following": self._native_count(profile, "following_count", "edge_follow"),
                        "content_count": self._native_count(profile, "media_count", "edge_owner_to_timeline_media"),
                        "verified": profile.get("is_verified") if type(profile.get("is_verified")) is bool else None,
                        "is_private": profile.get("is_private") if type(profile.get("is_private")) is bool else None,
                        "native_author_aliases": [{"kind": "username", "value": target}, {"kind": "id", "value": uid}], "source_observation": profile})], raw_count=1)
            container, rows, media_id = selected["container"], selected["rows"], selected["media_id"]
            page_info = container.get("page_info") or {}
            has_more = page_info.get("has_next_page")
            if type(has_more) is not bool:
                has_more = next((container[key] for key in ("has_more_comments", "has_more", "more_available") if type(container.get(key)) is bool), None)
            next_page = None
            for source_key, request_key in (("next_min_id", "min_id"), ("next_max_id", "max_id")):
                if isinstance(container.get(source_key), str) and container[source_key]: next_page = {request_key: container[source_key]}; break
            if next_page is None and isinstance(page_info.get("end_cursor"), str) and page_info["end_cursor"]:
                next_page = {"after": page_info["end_cursor"]}
            window = native_page_window(rows, limit=limit, cursor=cursor, identities=[
                str(row.get('pk') or row.get('id')) if isinstance(row, dict) else None for row in rows])
            complete = window['page_complete']
            base_cursor = {key: value for key, value in (cursor or {}).items() if key not in {'item_offset', 'page_sha256'}}
            if not base_cursor:
                base_cursor = {'mode': 'posts' if capability == 'author_posts' else 'roots', 'media_id': media_id, 'page': {}}
            next_cursor = ({**base_cursor, **window['next_window']} if not complete else
                           {**base_cursor, 'page': next_page} if has_more is True and next_page
                           and next_page != base_cursor['page'] else None)
            exhausted = not has_more if type(has_more) is bool and complete else None
            if not complete:
                exhausted = False
            notes, comments, pending, seen = [], [], [], set()
            reply_scope_unknown = (cursor.get('reply_scope_unknown', True)
                                   if capability == 'comments' and include_replies and cursor is not None else False)
            if capability == "author_posts":
                for item in window['rows']:
                    note = self._native_media_note(item) if isinstance(item, dict) else None
                    if not note: continue
                    owner = note.raw_data["author"]
                    if str(owner.get("pk") or owner.get("id") or "") != media_id:
                        return AdapterResult(success=False, error="INSTAGRAM_AUTHOR_HISTORY_IDENTITY_MISMATCH")
                    note.raw_data["author_history_binding"] = {"requested_id": target, "native_user_id": media_id}
                    notes.append(note)
                replies_complete = None
            else:
                flattened = []
                for node in window['rows']:
                    if not isinstance(node, dict): continue
                    cid = str(node.get("pk") or node.get("id") or "")
                    flattened.append((node, (cursor or {}).get("root_id")))
                    child_connection = node.get("edge_threaded_comments") or {}
                    inline = node.get("preview_child_comments") or node.get("child_comments") or [edge.get("node") for edge in child_connection.get("edges") or [] if isinstance(edge, dict)]
                    inline = inline if isinstance(inline, list) else []
                    flattened.extend((child, cid) for child in inline if isinstance(child, dict))
                    count = optional_int(node.get("child_comment_count")) if node.get("child_comment_count") is not None else optional_int(child_connection.get("count"))
                    if include_replies and count is None:
                        reply_scope_unknown = True
                    if count is not None and count > len(inline) and cid.isdigit(): pending.append(cid)
                for node, parent in flattened:
                    cid = str(node.get("pk") or node.get("id") or "")
                    if not cid or cid in seen: continue
                    seen.add(cid)
                    owner = node.get("owner") or node.get("user") or {}
                    comments.append({"platform_comment_id": cid, "parent_content_id": target,
                        "parent_comment_id": str(node.get("parent_comment_id") or parent) if node.get("parent_comment_id") or parent else None,
                        "reply_to_comment_id": str(node.get("replied_to_comment_id")) if node.get("replied_to_comment_id") else None,
                        "content": node.get("text") if isinstance(node.get("text"), str) else "", "author_id": str(owner.get("pk") or owner.get("id") or ""),
                        "author_nickname": owner.get("username") or "", "publish_datetime": self._native_time(node.get("created_at")),
                        "likes": self._native_count(node, "comment_like_count", "edge_liked_by") if node.get("like_count") is None else optional_int(node.get("like_count")),
                        "url": url + "c/" + cid + "/", "raw": {"source_observation": node, "media_id": media_id, "native_id_locator": "$.comments[].pk|id"}})
                if (cursor or {}).get("mode") == "replies":
                    if next_cursor is None and exhausted is True and cursor["pending_roots"]:
                        next_cursor = {**base_cursor, "root_id": cursor["pending_roots"][0], "page": {}, "pending_roots": cursor["pending_roots"][1:]}
                    elif next_cursor is None and exhausted is True:
                        next_cursor, exhausted = cursor.get("next_root"), cursor.get("root_exhausted")
                elif include_replies and pending:
                    next_cursor = {"mode": "replies", "media_id": media_id, "root_id": pending[0], "page": {}, "pending_roots": pending[1:],
                                   "next_root": next_cursor, "root_exhausted": exhausted}
                    exhausted = False
                replies_complete = (True if exhausted is True and next_cursor is None and not reply_scope_unknown else
                                    False if next_cursor is not None or exhausted is not True else None) if include_replies else None
                if include_replies and next_cursor is not None:
                    next_cursor = {**next_cursor, 'reply_scope_unknown': reply_scope_unknown}
                notes = [self._make_note(title="comments", content="", url=url, source_platform="instagram",
                    raw_data={"engine": "instagram_native_comments", "shortcode": target, "media_id": media_id, "comments": comments})]
            return AdapterResult(success=True, notes=notes, raw_count=len(comments) if capability == "comments" else len(notes), metadata={"pagination": {
                "request_cursor": cursor, "next_cursor": next_cursor, "exhausted": exhausted, "page_complete": complete,
                "replies_complete": replies_complete,
                "reported_total": optional_int(container.get("count")), "coverage_scope": "PROVIDER_VISIBLE_NATIVE_PAGE",
                **{key: window[key] for key in ('window_start', 'window_end', 'observed_native_rows', 'page_sha256', 'page_identity_basis')},
                "resume_strategy": "OFFICIAL_PAGE_NATIVE_CURSOR_SEEK", "observed_prior_native_responses": selected["observed_prior_native_responses"],
                "partial_reason": "REQUESTED_LIMIT_REACHED" if not complete else "NATIVE_NEXT_CURSOR_NOT_OBSERVED" if has_more and not next_cursor else None}})
        except NativePageWindowError as exc:
            return AdapterResult(success=False, raw_count=None, error='INSTAGRAM_' + str(exc), metadata={
                'failure_class': str(exc), 'pagination': {'request_cursor': cursor, 'next_cursor': None,
                    'exhausted': None, 'page_complete': False, 'resume_requires_fresh_page': True}})
        except Exception as exc:
            diagnostic = log_instagram_failure(capability, exc)
            return AdapterResult(success=False, error=diagnostic["error_code"], diagnostics=diagnostic)
        finally:
            capture.close()
            if page is not None:
                try: page.close()
                except Exception: pass
            if worker is not None: worker.close()

    def author_posts(self, author_id, *, max_results=20, cursor=None, **kwargs):
        return self._native_read("author_posts", str(author_id or "").lstrip("@"), max_results, cursor=cursor)

    # ---------- 工具 ----------
    @staticmethod
    def _to_tag(keyword):
        """Return only a literally supplied, single hashtag; never invent one."""
        if not isinstance(keyword, str):
            return ""
        value = keyword.strip()
        if not value.startswith("#") or value.startswith("##"):
            return ""
        tag = value[1:]
        if not tag or re.search(r"\s|[\\/?#]", tag):
            return ""
        return tag

    @staticmethod
    def _looks_like_count(text):
        return bool(re.fullmatch(r"[\d.,]+\s*[万亿kKmMbB]?", str(text).strip()))

    @staticmethod
    def _ig_num(text):
        """Return only exact observed counts; retain compact labels separately."""
        if text is None or isinstance(text, bool):
            return None
        if isinstance(text, int):
            return text if text >= 0 else None
        if not isinstance(text, str):
            return None
        value = text.strip()
        if not re.fullmatch(r"(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)", value):
            return None
        return int(value.replace(",", ""))
