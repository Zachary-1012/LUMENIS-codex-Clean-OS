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

    # ---------- 详情 ----------
    def detail(self, shortcode: str, media_type: str = "post") -> AdapterResult:
        """进帖子详情页补抓真实发布时间、完整 caption、评论数、位置。

        时间口径：publish_date 必须从 <time datetime> 取真实 ISO，取不到留空
        并标 needs_detail=True，绝不臆造。只读，不硬刚风控。
        """
        if not shortcode or not shortcode.strip():
            return AdapterResult(success=False, error="shortcode 为空")
        proxy = self._proxy_addr()
        if not proxy:
            return AdapterResult(
                success=False,
                error="Instagram 需经代理访问，未配置 GOOGLE_PROXY / OPENAI_PROXY",
            )
        try:
            return self._detail_browser(shortcode.strip(), media_type, proxy)
        except Exception as e:
            logger.exception("Instagram 详情采集异常")
            return AdapterResult(success=False, error=f"Instagram 详情采集异常: {e}")

    def _detail_browser(self, shortcode, media_type, proxy) -> AdapterResult:
        kind = "reel" if media_type == "reel" else "p"
        url = f"https://www.instagram.com/{kind}/{shortcode}/"
        hb = HumanBrowser(
            port=self.PROXY_CDP_PORT,
            profile_dir=self.PROXY_PROFILE_DIR,
            proxy_server=proxy,
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

            data = page.evaluate(
                r"""() => {
                    const out = {publish_time:'', caption:'', comment_count:0, likes:0, location:'', media_type:'post', author:''};
                    if (window.location.pathname.startsWith('/reel/')) out.media_type = 'reel';
                    const t = document.querySelector('time[datetime]');
                    if (t) out.publish_time = t.getAttribute('datetime') || '';
                    const imgs = document.querySelectorAll('article img, img');
                    for (const img of imgs) {
                        const alt = (img.alt || '').trim();
                        if (alt && !/头像|profile picture|头像照/i.test(alt) && alt.length > 3) {
                            out.caption = alt; break;
                        }
                    }
                    if (!out.caption) {
                        const h1 = document.querySelector('article h1, h1');
                        if (h1) out.caption = (h1.innerText || '').trim();
                    }
                    const authorLinks = document.querySelectorAll('a[href^="/"]');
                    for (const a of authorLinks) {
                        const href = a.getAttribute('href') || '';
                        const m = href.match(/^\/([A-Za-z0-9._]{1,40})\/?$/);
                        if (m && !['p','reel','explore','accounts','direct','stories','tags'].includes(m[1])) {
                            out.author = m[1]; break;
                        }
                    }
                    const body = document.body.innerText || '';
                    const cm = body.match(/(\d[\d,.]*)\s*(comments?|条评论)/i);
                    if (cm) out.comment_count = parseInt(cm[1].replace(/[,.]/g,'')) || 0;
                    const lm = body.match(/(\d[\d,.]*)\s*(likes?|次赞)/i);
                    if (lm) out.likes = parseInt(lm[1].replace(/[,.]/g,'')) || 0;
                    const loc = document.querySelector('a[href*="/explore/locations/"]');
                    if (loc) out.location = (loc.innerText || '').trim();
                    return out;
                }""")

            publish_date = (data.get("publish_time") or "").strip()
            needs_detail = not bool(publish_date)
            caption = (data.get("caption") or "").strip()
            author = (data.get("author") or "").strip() or "instagram_user"

            if not caption and not publish_date and not rendered:
                state = hb.detect_state(
                    page,
                    extra_markers={
                        PageState.AUTH_FAILED: ["log in", "sign up", "登录", "create an account", "create new account"],
                        PageState.CAPTCHA: ["confirm", "captcha", "验证", "suspicious"],
                        PageState.BLOCKED: ["try again later", "请稍等", "unusual", "rate limit", "report a problem"],
                    },
                    success_selector="time[datetime], article",
                )
                hint = {
                    PageState.AUTH_FAILED: "Instagram 登录态失效，请更新 Cookie 或在代理 Profile 重新登录",
                    PageState.CAPTCHA: "Instagram 出现确认/人机验证，需人工通过后再采",
                    PageState.BLOCKED: "Instagram 触发频控，按熔断退避不硬刚",
                    PageState.NETWORK_ERROR: "代理连接异常或 Instagram 不可达",
                }.get(state)
                if hint:
                    return AdapterResult(success=False, error=hint)

            note = self._make_note(
                title=caption[:80] or f"Instagram {shortcode}",
                content=caption,
                url=url,
                author=author,
                publish_date=publish_date,
                likes=int(data.get("likes", 0) or 0),
                comments=int(data.get("comment_count", 0) or 0),
                source_platform=self.platform_name,
                raw_data={
                    "engine": "instagram_detail_dom",
                    "shortcode": shortcode,
                    "media_type": data.get("media_type", "post"),
                    "comment_count": int(data.get("comment_count", 0) or 0),
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
    def comments(self, shortcode: str, max_comments: int = 20) -> AdapterResult:
        """进详情页解析评论区（只读，绝不发表评论）。

        评论列表放在返回 note 的 raw_data["comments"] 中，每条含
        author / content / publish_time / likes。评论区需滚动加载。
        """
        if not shortcode or not shortcode.strip():
            return AdapterResult(success=False, error="shortcode 为空")
        proxy = self._proxy_addr()
        if not proxy:
            return AdapterResult(
                success=False,
                error="Instagram 需经代理访问，未配置 GOOGLE_PROXY / OPENAI_PROXY",
            )
        try:
            return self._comments_browser(shortcode.strip(), max_comments, proxy)
        except Exception as e:
            logger.exception("Instagram 评论采集异常")
            return AdapterResult(success=False, error=f"Instagram 评论采集异常: {e}")

    def _comments_browser(self, shortcode, max_comments, proxy) -> AdapterResult:
        url = f"https://www.instagram.com/p/{shortcode}/"
        hb = HumanBrowser(
            port=self.PROXY_CDP_PORT,
            profile_dir=self.PROXY_PROFILE_DIR,
            proxy_server=proxy,
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
                        let likes = 0;
                        const likeText = el.innerText || '';
                        const lm = likeText.match(/(\d[\d,.]*)\s*(likes?|次赞)/i);
                        if (lm) likes = parseInt(lm[1].replace(/[,.]/g,'')) || 0;
                        out.push({
                            author: author,
                            content: content,
                            publish_time: timeEl.getAttribute('datetime') || '',
                            likes: likes,
                        });
                    }
                    return out;
                }""")

            comments_list = raw_comments or []
            if len(comments_list) > max_comments:
                comments_list = comments_list[:max_comments]

            if not comments_list and not rendered:
                state = hb.detect_state(
                    page,
                    extra_markers={
                        PageState.AUTH_FAILED: ["log in", "sign up", "登录", "create an account"],
                        PageState.CAPTCHA: ["confirm", "captcha", "验证", "suspicious"],
                        PageState.BLOCKED: ["try again later", "请稍等", "unusual", "rate limit"],
                    },
                    success_selector="time[datetime], article",
                )
                hint = {
                    PageState.AUTH_FAILED: "Instagram 登录态失效，请更新 Cookie 或在代理 Profile 重新登录",
                    PageState.CAPTCHA: "Instagram 出现确认/人机验证，需人工通过后再采",
                    PageState.BLOCKED: "Instagram 触发频控，按熔断退避不硬刚",
                    PageState.NETWORK_ERROR: "代理连接异常或 Instagram 不可达",
                }.get(state)
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
            return AdapterResult(success=True, notes=[note], raw_count=len(comments_list))
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
        proxy = self._proxy_addr()
        if not proxy:
            return AdapterResult(
                success=False,
                error="Instagram 需经代理访问，未配置 GOOGLE_PROXY / OPENAI_PROXY",
            )
        try:
            return self._creator_browser(username.strip().lstrip("@"), proxy)
        except Exception as e:
            logger.exception("Instagram 作者采集异常")
            return AdapterResult(success=False, error=f"Instagram 作者采集异常: {e}")

    def _creator_browser(self, username, proxy) -> AdapterResult:
        url = f"https://www.instagram.com/{username}/"
        hb = HumanBrowser(
            port=self.PROXY_CDP_PORT,
            profile_dir=self.PROXY_PROFILE_DIR,
            proxy_server=proxy,
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
                state = hb.detect_state(
                    page,
                    extra_markers={
                        PageState.AUTH_FAILED: ["log in", "sign up", "登录", "create an account"],
                        PageState.CAPTCHA: ["confirm", "captcha", "验证", "suspicious"],
                        PageState.BLOCKED: ["try again later", "请稍等", "unusual", "rate limit"],
                    },
                    success_selector="header, section",
                )
                hint = {
                    PageState.AUTH_FAILED: "Instagram 登录态失效，请更新 Cookie 或在代理 Profile 重新登录",
                    PageState.CAPTCHA: "Instagram 出现确认/人机验证，需人工通过后再采",
                    PageState.BLOCKED: "Instagram 触发频控，按熔断退避不硬刚",
                    PageState.NETWORK_ERROR: "代理连接异常或 Instagram 不可达",
                }.get(state)
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
