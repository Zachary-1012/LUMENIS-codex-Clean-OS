# -*- coding: utf-8 -*-
"""
抖音全网搜索采集适配器（真人浏览器 + 结构化接口双通道）
-------------------------------------------------
定位：抖音网页端强依赖登录态与 JS 渲染，纯 requests 不可行。本适配器走
“真实有头 Edge（9222 采集专用持久 Profile）+ connectOverCDP + 拟人操作”，
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
"""
import re
import json
import time
import logging
import datetime
import urllib.parse
from .base import BaseAdapter, AdapterResult
from .human_browser import HumanBrowser, PageState
from .cookie_vault import inject_into_context

logger = logging.getLogger(__name__)

_SEARCH_API_KEYS = ("general/search/single", "general/search/stream")


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

    # 连接 9222 采集专用 Profile（与小红书共用同一套持久指纹/登录态）
    CDP_PORT = 9222

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        try:
            return self._search_browser(keyword.strip(), max_results)
        except Exception as e:
            logger.exception("抖音采集异常")
            return AdapterResult(success=False, error=f"抖音浏览器采集异常: {e}")

    def _search_browser(self, keyword, max_results) -> AdapterResult:
        hb = HumanBrowser(port=self.CDP_PORT, launch_url="about:blank")
        hb.connect()
        injected = inject_into_context(hb._context, "douyin")  # Cookie 兜底/换号
        logger.info("抖音采集：注入 Cookie %d 条", injected)
        api_bags = []

        def _on_response(resp):
            try:
                u = resp.url
                if not any(k in u for k in _SEARCH_API_KEYS):
                    return
                if resp.request.resource_type not in ("xhr", "fetch"):
                    return
                if "stream" in u:
                    api_bags.extend(_iter_json_objects(resp.text()))
                else:
                    api_bags.append(resp.json())
            except Exception:
                # 单个响应解析失败不影响整体，交由 DOM 兜底
                return

        page = None
        try:
            page = hb.new_page()
            page.on("response", _on_response)
            url = ("https://www.douyin.com/search/"
                   f"{urllib.parse.quote(keyword)}?type=general")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # 等结果真正渲染（以时长徽标为锚），最多 ~18s；同时六态判断
            rendered = True
            try:
                page.wait_for_function(
                    "()=>(document.body.innerText.match(/\\b\\d{2}:\\d{2}\\b/g)||[]).length>=1",
                    timeout=18000)
            except Exception:
                rendered = False

            state = hb.detect_state(
                page,
                extra_markers={
                    PageState.BLOCKED: ["访问频繁", "系统繁忙", "稍后再试", "操作太频繁"],
                    PageState.CAPTCHA: ["滑块", "拖动", "安全验证", "captcha_verify"],
                    PageState.AUTH_FAILED: ["登录后即可", "验证码登录", "扫码登录", "登录解锁更多"],
                },
                success_selector=".videoImage",
            )

            # 拟人滚动加载更多（变速、偶发回滚），让 stream 接口逐页返回
            for _ in range(3):
                hb.human_scroll(page, total_px=800, rounds=2)
                hb.pause(1.4, 2.4)
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
                return AdapterResult(success=True, notes=notes, raw_count=len(notes))

            # 无结果时按页面状态如实上报，绝不把风控/登录墙伪装成 0 条
            if not rendered and state in (PageState.BLOCKED, PageState.CAPTCHA,
                                          PageState.AUTH_FAILED, PageState.NETWORK_ERROR):
                hint = {
                    PageState.AUTH_FAILED: "抖音登录态失效，请在采集专用 Profile 重新登录或更新 Cookie",
                    PageState.CAPTCHA: "抖音出现人机验证，需人工通过后再采",
                    PageState.BLOCKED: "抖音访问频繁/风控，按熔断退避不硬刚",
                }.get(state, f"抖音页面状态={state}")
                return AdapterResult(success=False, error=hint)
            return AdapterResult(success=True, notes=[], raw_count=0)
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
                wid = str(ai.get("aweme_id") or "").strip()
                if not wid or wid in seen:
                    continue
                seen.add(wid)
                desc = re.sub(r"\s+", " ", (ai.get("desc") or "").strip())
                if not desc:
                    continue
                st = ai.get("statistics") or {}
                au = ai.get("author") or {}
                note = self._make_note(
                    title=desc[:80],
                    content=desc,
                    url=f"https://www.douyin.com/video/{wid}",
                    author=(au.get("nickname") or "抖音用户").strip() or "抖音用户",
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
        """Unix 秒时间戳 → YYYY-MM-DD；无效返回空串（不臆造）。"""
        try:
            ts = int(ts)
            if ts <= 0:
                return ""
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError):
            return ""

    @staticmethod
    def _to_int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _cn_num(text):
        """把 '1.2万' / '3.4亿' 等中文计数转为整数；无法解析返回 0。"""
        if not text:
            return 0
        s = str(text).strip().replace(",", "")
        m = re.search(r"([\d.]+)\s*([万亿wW]?)", s)
        if not m:
            return 0
        try:
            v = float(m.group(1))
        except ValueError:
            return 0
        unit = m.group(2)
        if unit in ("万", "w", "W"):
            v *= 1e4
        elif unit == "亿":
            v *= 1e8
        return int(v)
