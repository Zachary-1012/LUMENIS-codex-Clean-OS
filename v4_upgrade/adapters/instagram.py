# -*- coding: utf-8 -*-
"""
Instagram 海外品牌内容采集适配器（真人浏览器 + 代理通道）
-------------------------------------------------
定位：服务于 Z-Brand Core 的海外品牌信息采集（ZBMP 母品牌能力基底）。
Instagram 在境内直连不可达且反爬强，本适配器走“真实有头 Edge +
独立代理持久 Profile（9223 / edge-cdp-proxy）+ connectOverCDP + 拟人操作”，
登录态由 cookie_vault 注入与持久 Profile 双通道桥接，绝不把 Cookie 写进代码。

数据主路径：话题/标签页 https://www.instagram.com/explore/tags/{tag}/
（新版会 302 到 /popular/{tag}/，属正常）。其 feed 由服务端组件直接渲染进
DOM，帖子卡片 a[href*="/p/"|"/reel/"] 的 innerText 即“作者\\n点赞\\n正文”，
img.alt 为完整文案，封面取 img.src——不依赖易变的 GraphQL doc_id。

六态严格分离：解析到帖子=SUCCESS；正常无内容=success=True/空(EMPTY)；
登录失效=AUTH_FAILED；人机/确认=CAPTCHA；try again later/风控=BLOCKED；
代理不通/加载失败=NETWORK_ERROR。无代理直接 success=False，绝不假成功。

时间口径：标签首屏不展示发布日期，publish_date 留空（不臆造），在 raw_data
标 needs_detail，需要精确时间时按 shortcode 进详情补抓；采集时间由入库层写
captured_at，二者严格分离。
"""
import os
import re
import logging
from pathlib import Path
from .base import BaseAdapter, AdapterResult
from .human_browser import HumanBrowser, PageState
from .cookie_vault import inject_into_context

logger = logging.getLogger(__name__)


class InstagramAdapter(BaseAdapter):
    """Instagram 标签/话题内容适配器（代理 + CDP 真人浏览 + DOM 主路径）"""

    platform_name = "instagram"
    platform_display = "Instagram"

    PROXY_CDP_PORT = 9223
    PROXY_PROFILE_DIR = str(Path(__file__).resolve().parents[2] / "edge-cdp-proxy")

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        proxy = self._proxy_addr()
        if not proxy:
            return AdapterResult(
                success=False,
                error="Instagram 需经代理访问，未配置 GOOGLE_PROXY / OPENAI_PROXY",
            )
        try:
            return self._search_browser(keyword.strip(), max_results, proxy)
        except Exception as e:
            logger.exception("Instagram 采集异常")
            return AdapterResult(success=False, error=f"Instagram 浏览器采集异常: {e}")

    def _search_browser(self, keyword, max_results, proxy) -> AdapterResult:
        tag = self._to_tag(keyword)
        hb = HumanBrowser(
            port=self.PROXY_CDP_PORT,
            profile_dir=self.PROXY_PROFILE_DIR,
            proxy_server=proxy,
            launch_url="about:blank",
        )
        hb.connect()
        injected = inject_into_context(hb._context, "instagram")
        logger.info("Instagram 采集：注入 Cookie %d 条，tag=%s", injected, tag)
        page = None
        try:
            page = hb.new_page()
            page.goto(f"https://www.instagram.com/explore/tags/{tag}/",
                      wait_until="domcontentloaded", timeout=40000)

            # 等帖子卡片出现（首屏），最多 ~18s
            rendered = True
            try:
                page.wait_for_selector('a[href*="/p/"],a[href*="/reel/"]', timeout=18000)
            except Exception:
                rendered = False
            hb.pause(1.0, 2.0)

            # 拟人滚动加载更多，直到数量够或连续两轮不增长
            last, stable = 0, 0
            for _ in range(5):
                hb.human_scroll(page, total_px=900, rounds=2)
                hb.pause(1.2, 2.2)
                cnt = page.locator('a[href*="/p/"],a[href*="/reel/"]').count()
                if cnt >= max_results:
                    break
                if cnt == last:
                    stable += 1
                    if stable >= 2:
                        break
                else:
                    stable, last = 0, cnt

            notes = self._parse_cards(page, max_results)
            if notes:
                return AdapterResult(success=True, notes=notes, raw_count=len(notes))

            # 无帖子：按页面状态如实区分登录失效 / 验证 / 风控 / 真空
            if not rendered:
                state = hb.detect_state(
                    page,
                    extra_markers={
                        PageState.AUTH_FAILED: ["log in", "sign up", "登录", "create an account", "create new account"],
                        PageState.CAPTCHA: ["confirm", "captcha", "验证", "suspicious"],
                        PageState.BLOCKED: ["try again later", "请稍等", "unusual", "rate limit", "report a problem"],
                    },
                    success_selector='a[href*="/p/"],a[href*="/reel/"]',
                )
                hint = {
                    PageState.AUTH_FAILED: "Instagram 登录态失效，请更新 Cookie 或在代理 Profile 重新登录",
                    PageState.CAPTCHA: "Instagram 出现确认/人机验证，需人工通过后再采",
                    PageState.BLOCKED: "Instagram 触发频控，按熔断退避不硬刚",
                    PageState.NETWORK_ERROR: "代理连接异常或 Instagram 不可达",
                }.get(state)
                if hint:
                    return AdapterResult(success=False, error=hint)
            return AdapterResult(success=True, notes=[], raw_count=0)
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass
            hb.close()

    def _parse_cards(self, page, max_results):
        rows = page.evaluate(
            r"""() => {
                const out=[], seen=new Set();
                document.querySelectorAll('a[href*="/p/"],a[href*="/reel/"]').forEach(a=>{
                    const href=a.getAttribute('href')||'';
                    const m=href.match(/\/(p|reel|reels)\/([A-Za-z0-9_\-]+)/);
                    if(!m) return;
                    const code=m[2]; if(seen.has(code)) return; seen.add(code);
                    // 跳过作者头像图，选真正的内容封面（alt 不含“头像/profile picture”）
                    const imgs=[...a.querySelectorAll('img')];
                    const cover=imgs.find(i=>!/头像|profile picture|头像照/i.test(i.alt||''))||imgs[0]||null;
                    const lines=(a.innerText||'').split('\n').map(s=>s.trim()).filter(Boolean);
                    out.push({kind:m[1], code:code, lines:lines,
                              alt:cover?cover.alt||'':'', cover:cover?cover.src||'':''});
                });
                return out;
            }""")
        notes = []
        for row in rows or []:
            code = row.get("code")
            if not code:
                continue
            kind = "reel" if row.get("kind") in ("reel", "reels") else "p"
            author, likes, body_parts = "", 0, []
            lines = row.get("lines") or []
            if lines:
                author = lines[0] if re.fullmatch(r"[A-Za-z0-9._]{1,40}", lines[0]) else ""
                rest = lines[1:] if author else lines
                if rest and self._looks_like_count(rest[0]):
                    likes = self._ig_num(rest[0]); rest = rest[1:]
                body_parts = rest
            alt = re.sub(r"\s+", " ", (row.get("alt") or "")).strip()
            body_text = re.sub(r"\s+", " ", " ".join(body_parts)).strip()
            # 头像占位 alt（“XX的头像”）不可用，回退到卡片文本正文
            if not alt or re.search(r"头像|profile picture", alt):
                caption = body_text
            else:
                caption = alt or body_text
            if not caption and not author:
                continue
            url = f"https://www.instagram.com/{kind}/{code}/"
            notes.append(self._make_note(
                title=caption[:80] or f"Instagram {kind} {code}",
                content=caption,
                url=url,
                author=author or "instagram_user",
                publish_date="",  # 首屏无发布日期，留空不臆造；详情补抓
                likes=likes,
                source_platform=self.platform_name,
                raw_data={
                    "engine": "instagram_tag_dom",
                    "shortcode": code,
                    "media_type": "reel" if kind == "reel" else "post",
                    "cover": (row.get("cover") or "")[:300],
                    "needs_detail": True,
                },
            ))
            if len(notes) >= max_results:
                break
        return notes

    # ---------- 工具 ----------
    @staticmethod
    def _to_tag(keyword):
        """关键词规整为 IG 标签：去 #、去空格、小写。"""
        tag = keyword.strip().lstrip("#")
        tag = re.sub(r"[\s\-]+", "", tag)
        return tag

    @staticmethod
    def _looks_like_count(text):
        return bool(re.fullmatch(r"[\d.,]+\s*[万亿kKmMbB]?", str(text).strip()))

    @staticmethod
    def _ig_num(text):
        """中文 '1.2万'/'亿' 与英文 '1.1M'/'532K' 计数统一转整数。"""
        if not text:
            return 0
        s = str(text).strip().replace(",", "")
        m = re.search(r"([\d.]+)\s*([万亿kKmMbB]?)", s)
        if not m:
            return 0
        try:
            v = float(m.group(1))
        except ValueError:
            return 0
        u = m.group(2).lower()
        if u in ("万", "k"):
            v *= 1e3 if u == "k" else 1e4
        elif u in ("亿", "m"):
            v *= 1e6 if u == "m" else 1e8
        elif u == "b":
            v *= 1e9
        return int(v)

    @staticmethod
    def _proxy_addr():
        """读取代理并去协议头；无代理返回空串。"""
        raw = (os.environ.get("GOOGLE_PROXY") or os.environ.get("OPENAI_PROXY") or "").strip()
        for pre in ("https://", "http://"):
            if raw.startswith(pre):
                raw = raw[len(pre):]
        return raw.rstrip("/")
