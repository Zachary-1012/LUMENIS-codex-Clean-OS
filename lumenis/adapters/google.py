# -*- coding: utf-8 -*-
"""
Google 全网搜索采集适配器
-------------------------------------------------
定位：补足中文搜索引擎之外的国际/英文信源。页面访问只通过 SYSTEM
Browser Runtime 已注册并核验的 Google BACKGROUND worker；该 worker 负责其
受控网络配置。此适配器不启动浏览器、不选取个人 Profile，也不自行配置代理。

worker 未注册、身份无法核验或访问受到挑战时，返回明确失败状态，不改走
其他浏览器或网络路径，也不把访问失败报告为“0 条成功”。

六态：knitsail 挑战 / 人机验证 / 登录 / 网络异常分别上报，只有真正解析到
结果块才算 SUCCESS；摘要日期仅保留为候选，不能代替目标文章的发布时间。
"""
import logging
import re

from .base import AdapterResult, BaseAdapter
from .human_browser import HumanBrowser, PageState, registered_browser_worker_spec

logger = logging.getLogger(__name__)

_DATE = re.compile(r"(20\d{2})\s*[年/\-\.]\s*(\d{1,2})\s*[月/\-\.]\s*(\d{1,2})")
# Google 结果块 / 摘要候选
_RESULT_BLOCK = "div.g, div.MjjYud"
_SNIPPET_SEL = ["div.VwiC3b", "span.aCOpRe", "div[data-sncf]"]


class GoogleAdapter(BaseAdapter):
    """Google 搜索适配器（SYSTEM 注册的后台只读浏览器）"""

    platform_name = "google"
    platform_display = "Google搜索"

    def search(self, keyword: str, max_results: int = 10, *, cursor=None) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")

        try:
            if cursor is not None and (not isinstance(cursor, dict) or set(cursor) != {'start'}
                    or type(cursor['start']) is not int or not 0 <= cursor['start'] <= 10000):
                return AdapterResult(success=False, error='GOOGLE_NATIVE_CURSOR_INVALID')
            return self._search_via_browser(keyword, max_results, cursor=cursor)
        except Exception as exc:
            logger.warning("Google read failed error_type=%s", type(exc).__name__)
            code = str(exc) if re.fullmatch(r'[A-Z_]{1,120}', str(exc)) else 'PROVIDER_UNAVAILABLE'
            return AdapterResult(success=False, error='GOOGLE_' + code)

    # ---------- 主流程 ----------
    def _search_via_browser(self, keyword, max_results, *, cursor=None) -> AdapterResult:
        worker = registered_browser_worker_spec("google")
        if worker.get("platform") != "google":
            raise RuntimeError("GOOGLE_READONLY_WORKER_NOT_REGISTERED")
        import cdp_helper
        browser = cdp_helper.registered_cdp_browser_for_port(
            worker["port"], worker["profile"], headless=True)
        if browser is None:
            raise RuntimeError("GOOGLE_BACKGROUND_WORKER_UNAVAILABLE_OR_UNVERIFIED")
        endpoint = f"http://127.0.0.1:{int(worker['port'])}"
        hb = HumanBrowser(cdp_url=endpoint, auto_ensure=False,
                          launch_url="about:blank")
        page = None
        try:
            hb.connect()
            page = hb.new_page()
            # 先进主页短暂停留并处理合规页，模拟真人进站
            page.goto("https://www.google.com/", wait_until="domcontentloaded", timeout=30000)
            hb.pause(0.8, 1.6)
            self._dismiss_consent(page)
            # 直接以结果页 URL 进入（等价地址栏搜索，规避首页打字回车偶发不导航）
            import urllib.parse
            q = urllib.parse.quote(keyword.strip())
            search_url = (f"https://www.google.com/search?q={q}"
                          f"&hl=zh-CN&num={max(max_results, 10)}")
            if cursor is not None:
                search_url += '&start=' + str(cursor['start'])
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            self._dismiss_consent(page)

            try:
                page.wait_for_selector("h3", timeout=15000)
            except Exception:
                state = hb.detect_state(page, success_selector="h3")
                return AdapterResult(success=False, error=f"Google 未出现结果，页面状态={state}")

            hb.pause(0.8, 1.6)
            hb.human_scroll(page, total_px=900, rounds=3)

            state = hb.detect_state(page, success_selector="h3")
            if state in (PageState.BLOCKED, PageState.CAPTCHA,
                         PageState.AUTH_FAILED, PageState.NETWORK_ERROR):
                return AdapterResult(success=False, error=f"Google 页面状态={state}")

            notes = self._parse_results(page, max_results)
            next_cursor = None
            for link in page.locator('a#pnnext, a[rel="next"]').all():
                href = link.get_attribute('href')
                if not href: continue
                parsed = urllib.parse.urlsplit(urllib.parse.urljoin('https://www.google.com', href))
                values = urllib.parse.parse_qs(parsed.query)
                start = values.get('start', [''])[-1]
                if (parsed.scheme == 'https' and parsed.hostname == 'www.google.com' and parsed.path == '/search'
                        and not parsed.username and not parsed.password and values.get('q', [None])[-1] == keyword.strip()
                        and start.isascii() and start.isdigit() and int(start) > (cursor or {}).get('start', 0)):
                    next_cursor = {'start': int(start)}
                    break
            for note in notes:
                note.raw_data = {**(note.raw_data or {}), 'body_state': 'FEED_OR_INDEX_EXCERPT',
                    'body_kind': 'search_snippet', 'original_body_available': False,
                    'discovery_source_url': search_url, 'original_target_url': note.url}
            if not notes:
                return AdapterResult(success=False, error='GOOGLE_NATIVE_RESULT_NOT_OBSERVED')
            return AdapterResult(success=True, notes=notes[:max_results], raw_count=len(notes), metadata={'pagination': {
                'request_cursor': cursor, 'next_cursor': next_cursor, 'exhausted': False if next_cursor else None,
                'page_complete': True, 'coverage_scope': 'GOOGLE_DISCOVERY_SNIPPETS_ONLY',
                'partial_reason': 'NATIVE_END_NOT_OBSERVED' if next_cursor is None else None}})
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass
            hb.close()

    @staticmethod
    def _dismiss_consent(page):
        """处理 Google 合规/同意页（中英文按钮均尝试一次）。"""
        for sel in ["button#L2AGLb", "button:has-text('全部接受')",
                    "button:has-text('Accept all')", "button:has-text('我同意')"]:
            try:
                btn = page.locator(sel).first
                if btn.count() and btn.is_visible():
                    btn.click(timeout=2000)
                    page.wait_for_timeout(800)
                    return
            except Exception:
                continue

    def _parse_results(self, page, max_results):
        # 遍历结果标题 h3：主链接为加密 /goto 中转，同时抓取结果块内首个
        # 非 Google 绝对外链作为直链候选；仍缺的用浏览器共享会话跟随重定向还原。
        rows = page.evaluate(
            """() => {
                const isExt = h => /^https?:\\/\\//.test(h) &&
                    !/google\\.com|gstatic\\.com|googleusercontent/.test(h) &&
                    !/\\/(search|url|goto|preferences|account)/.test(h);
                const out = [];
                document.querySelectorAll('h3').forEach(h => {
                    const a = h.closest('a');
                    if (!a) return;
                    // 摘要：就近向上找结果说明文本
                    let sbox = h, snip = '';
                    for (let i = 0; i < 5 && sbox; i++) {
                        sbox = sbox.parentElement;
                        if (!sbox) break;
                        const s = sbox.querySelector('.VwiC3b,[data-sncf],span.aCOpRe');
                        if (s) { snip = s.innerText || ''; break; }
                    }
                    // 真实直链：逐级向上，在“不含第二个 h3（不跨结果）”的最小祖先内找本结果外链
                    let ebox = h, direct = '';
                    for (let i = 0; i < 6 && ebox; i++) {
                        ebox = ebox.parentElement;
                        if (!ebox) break;
                        if (ebox.querySelectorAll('h3').length > 1) break; // 已跨结果，停止
                        const ext = [...ebox.querySelectorAll('a[href]')].find(x => isExt(x.getAttribute('href')));
                        if (ext) { direct = ext.getAttribute('href'); break; }
                    }
                    out.push({title: h.innerText || '', goto: a.getAttribute('href') || '',
                              direct, snippet: snip});
                });
                return out;
            }"""
        )
        import time
        notes, seen = [], set()
        for row in rows or []:
            title = (row.get("title") or "").strip()
            if not title:
                continue
            href, redirected = self._final_url(page, row.get("direct", ""), row.get("goto", ""))
            if not href or href in seen:
                continue
            snippet = re.sub(r"\s+", " ", (row.get("snippet") or "").strip())
            seen.add(href)
            notes.append(self._make_note(
                title=title,
                content=snippet,
                url=href,
                author="",
                publish_date="",
                raw_data={"engine": "google", "link_redirect": redirected,
                          'discovery_date_candidate': self._norm_date(snippet) or None,
                          'date_semantics': 'SNIPPET_DATE_NOT_VERIFIED_PUBLICATION'},
            ))
            time.sleep(0.2)  # 温和还原，避免连点
            if len(notes) >= max_results:
                break
        return notes

    @staticmethod
    def _final_url(page, direct, goto):
        """真实 URL：本结果块内直链优先；缺失时快速跟随一次 /goto；再不行保留中转链。"""
        if direct:
            return direct, False
        if not goto:
            return "", False
        g = goto if not goto.startswith("/") else "https://www.google.com" + goto
        if "google.com/goto" in g:
            try:
                resp = page.request.get(g, max_redirects=20, timeout=3500)
                final = resp.url
                if final and "google.com/goto" not in final and "google.com/search" not in final:
                    return final, False
            except Exception:
                pass
            return g, True  # 跟随失败：保留中转链并标记，不丢弃
        return g, False

    @staticmethod
    def _norm_date(text):
        m = _DATE.search(text or "")
        if not m:
            return ""
        y, mo, d = (int(x) for x in m.groups())
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"
        return ""
