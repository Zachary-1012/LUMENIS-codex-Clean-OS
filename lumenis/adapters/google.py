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
结果块才算 SUCCESS；发布时间从结果摘要中尽力归一，取不到留空、不臆造。
"""
import logging
import re

from .base import AdapterResult, BaseAdapter
from .human_browser import HumanBrowser, PageState, configured_readonly_worker_url

logger = logging.getLogger(__name__)

_DATE = re.compile(r"(20\d{2})\s*[年/\-\.]\s*(\d{1,2})\s*[月/\-\.]\s*(\d{1,2})")
# Google 结果块 / 摘要候选
_RESULT_BLOCK = "div.g, div.MjjYud"
_SNIPPET_SEL = ["div.VwiC3b", "span.aCOpRe", "div[data-sncf]"]


class GoogleAdapter(BaseAdapter):
    """Google 搜索适配器（SYSTEM 注册的后台只读浏览器）"""

    platform_name = "google"
    platform_display = "Google搜索"

    def search(self, keyword: str, max_results: int = 10) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")

        try:
            return self._search_via_browser(keyword, max_results)
        except Exception as e:
            logger.exception("Google 采集异常")
            return AdapterResult(success=False, error=f"Google 浏览器采集异常: {e}")

    # ---------- 主流程 ----------
    def _search_via_browser(self, keyword, max_results) -> AdapterResult:
        endpoint = configured_readonly_worker_url("google", mode="BACKGROUND")
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
            if not notes:
                # 页面正常但确实没解析到 -> EMPTY（success=True 空列表，由注册中心判 EMPTY）
                return AdapterResult(success=True, notes=[], raw_count=0)
            return AdapterResult(success=True, notes=notes[:max_results], raw_count=len(notes))
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
                author="Google",
                publish_date=self._norm_date(snippet),
                raw_data={"engine": "google", "link_redirect": redirected},
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
