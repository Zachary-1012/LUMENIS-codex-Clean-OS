# -*- coding: utf-8 -*-
"""
Bilibili（B站）视频内容采集适配器
----------------------------------
定位：服务于 Z-Brand Core 多平台内容采集。
基于 bilibili_login_manager.search_videos（cookie + requests API），
薄封装为 v4 BaseAdapter 契约，自动接入熔断器/限流/重试/降级体系。

数据主路径：B站搜索 API
  https://api.bilibili.com/x/web-interface/search/type
返回视频列表（aid/bvid/title/author/play/pubdate/duration/description）。

状态映射：
  - ok=True 且有结果  → SUCCESS
  - ok=True 但空      → EMPTY (success=True, notes=[])
  - code=-101         → cookie 失效（SESSION_EXPIRED 语义）
  - code=-352/-509    → 风控/频控（RISK_WARNING 语义）
  - 其他错误          → COLLECT_ERROR

时间口径：pubdate 为 Unix 秒级时间戳，转 ISO 8601；
采集时间由入库层写 captured_at，二者严格分离。

只读红线：不发评论、不点赞、不关注、不执行任何账号写操作；
遇到风控/验证码如实返回，不破解、不绕过、不对抗。
"""
import logging
from datetime import datetime, timezone

from .base import BaseAdapter, AdapterResult, optional_int
from .cookie_vault import to_requests_cookies, to_cookie_string, check_cookie_status

logger = logging.getLogger(__name__)


class BilibiliAdapter(BaseAdapter):
    """B站视频搜索适配器（API + cookie，薄封装 bilibili_login_manager）"""

    platform_name = "bilibili"
    platform_display = "B站"

    # B站 API 错误码 → 人类可读说明（仅记录，不做绕过）
    _ERROR_HINTS = {
        -101: "账号未登录或 cookie 失效",
        -352: "风控校验失败，需人工验证",
        -404: "无搜索结果",
        -509: "请求过于频繁，已触发频控",
        6000: "搜索词包含敏感内容",
    }

    def __init__(self, manager=None, **kwargs):
        super().__init__(**kwargs)
        self._manager = manager  # 向后兼容：旧测试传入 manager，现统一走 cookie_vault

    @staticmethod
    def _cookie_ok() -> bool:
        s = check_cookie_status("bilibili")
        return s["status"] == "ACTIVE"

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        # 向后兼容：测试传入 mock manager 时走 manager 路径
        if self._manager is not None:
            try:
                login_status = self._manager.check_login_status()
                if not login_status.get("logged_in", False):
                    return AdapterResult(success=False, error="登录态失效：B站 cookie 未配置或已过期")
                raw = self._manager.search_videos(keyword, max_results=max_results)
            except Exception as _e:
                return AdapterResult(success=False, error=f"manager搜索异常: {_e}")
            if not isinstance(raw, dict):
                return AdapterResult(success=False, error=f"manager返回异常: {raw!r}")
            if not raw.get("ok", False):
                code = raw.get("code")
                error = raw.get("error", "搜索失败")
                if code == -101:
                    return AdapterResult(success=False, error=f"B站 cookie 失效: {error}")
                if code in (-352, -509):
                    return AdapterResult(success=False, error=f"B站风控/频控: {error}")
                return AdapterResult(success=False, error=f"B站搜索失败: {error} (code={code})")
            videos = raw.get("videos", []) or []
            notes = []
            for v in videos[:max_results]:
                notes.append(self._make_note(
                    title=self._clean_title(v.get("title")),
                    content=(v.get("description") or "").strip(),
                    url=v.get("url", ""),
                    author=v.get("author", ""),
                    author_id="",
                    publish_date=self._ts_to_iso(v.get("pubdate")),
                    likes=None,
                    comments=None,  # Search review fields lack verified comment semantics.
                    collects=optional_int(v.get("favorites")),
                    shares=None,
                    source_platform="bilibili",
                    raw_data=v,
                ))
            return AdapterResult(success=True, notes=notes, raw_count=len(videos))
        try:
            import requests as _req
            # 登录态前置检查（经 cookie_vault）
            if not self._cookie_ok():
                return AdapterResult(
                    success=False,
                    error="B站 cookie 缺失或无关键认证 cookie，请更新 data/bilibili_cookies.json",
                )
            cookies = to_requests_cookies("bilibili")
            resp = _req.get(
                "https://api.bilibili.com/x/web-interface/search/type",
                params={"search_type": "video", "keyword": keyword.strip(),
                        "page": 1, "page_size": max_results},
                cookies=cookies,
                headers=self._api_headers(),
                timeout=15,
            )
            data = resp.json()
            if data.get("code") != 0:
                raw = {"ok": False, "error": data.get("message", "搜索失败"), "code": data.get("code")}
            else:
                result = data.get("data", {})
                videos = []
                for ri in result.get("result", []):
                    videos.append({
                        "id": ri.get("aid"), "bvid": ri.get("bvid"),
                        "title": ri.get("title", ""), "author": ri.get("author"),
                        "play": ri.get("play"), "video_review": ri.get("video_review"),
                        "favorites": ri.get("favorites"), "pubdate": ri.get("pubdate"),
                        "duration": ri.get("duration"), "description": ri.get("description", ""),
                        "url": f"https://www.bilibili.com/video/{ri.get('bvid', '')}",
                    })
                raw = {"ok": True, "videos": videos, "total": result.get("numResults", 0)}
            if not isinstance(raw, dict):
                return AdapterResult(success=False, error=f"B站搜索返回异常: {raw!r}")

            if not raw.get("ok", False):
                code = raw.get("code")
                error = raw.get("error", "搜索失败")
                hint = self._ERROR_HINTS.get(code, "")
                # 风控/未登录如实返回，不硬刚、不绕过
                if code == -101:
                    return AdapterResult(
                        success=False,
                        error=f"B站 cookie 失效: {hint or error}",
                    )
                if code in (-352, -509):
                    return AdapterResult(
                        success=False,
                        error=f"B站风控/频控: {hint or error}",
                    )
                return AdapterResult(
                    success=False,
                    error=f"B站搜索失败: {error} (code={code})",
                )

            videos = raw.get("videos", []) or []
            notes = []
            for v in videos[:max_results]:
                notes.append(self._make_note(
                    title=self._clean_title(v.get("title")),
                    content=(v.get("description") or "").strip(),
                    url=v.get("url", ""),
                    author=v.get("author", ""),
                    author_id="",  # 搜索API不返回mid，留空不臆造
                    publish_date=self._ts_to_iso(v.get("pubdate")),
                    likes=None,    # 搜索API不返回点赞数
                    comments=None,  # Search review fields lack verified comment semantics.
                    collects=optional_int(v.get("favorites")),
                    shares=None,
                    cover="",      # 搜索API不返回封面
                    source_platform=self.platform_name,
                    raw_data={
                        "engine": "bilibili_search_api",
                        "aid": v.get("id"),
                        "bvid": v.get("bvid"),
                        "play": v.get("play"),
                        "video_review": v.get("video_review"),
                        "review": v.get("review"),
                        "duration": v.get("duration"),
                        "pubdate_ts": v.get("pubdate"),
                        "media_type": v.get("type", "video"),
                    },
                ))

            if notes:
                return AdapterResult(success=True, notes=notes, raw_count=len(notes))
            # 正常无内容：success=True 但空，调用方按 EMPTY 处理，绝不伪装成 0 条失败
            return AdapterResult(success=True, notes=[], raw_count=0)

        except Exception as exc:
            logger.exception("B站采集异常")
            return AdapterResult(success=False, error=f"B站采集异常: {exc}")

    @staticmethod
    def _clean_title(raw):
        """去除 B站搜索结果标题中的 <em class='keyword'> 高亮标签及多余空白。"""
        if not raw:
            return ""
        import re
        text = re.sub(r"</?em[^>]*>", "", str(raw))
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _ts_to_iso(ts):
        """Unix 秒级时间戳 → ISO 8601；无效返回空串（不臆造时间）。"""
        if not ts:
            return ""
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
        except (ValueError, TypeError, OSError):
            return ""

    # ── detail: 视频详情（B站 view API，补全搜索API缺失的点赞/评论/UP主mid）──
    def detail(self, bvid: str, **kwargs) -> AdapterResult:
        if not bvid or not str(bvid).strip():
            return AdapterResult(success=False, error="bvid 为空")
        try:
            import json as _json, requests as _req
            if not self._cookie_ok():
                return AdapterResult(success=False, error="B站 cookie 缺失或无关键认证 cookie，请更新 data/bilibili_cookies.json")
            cookies = self._load_cookies()
            if not cookies:
                return AdapterResult(success=False, error="B站 cookie 不存在，无法获取详情")
            resp = _req.get(
                "https://api.bilibili.com/x/web-interface/view",
                params={"bvid": str(bvid).strip()},
                cookies=cookies,
                headers=self._api_headers(),
                timeout=15,
            )
            data = resp.json()
            if data.get("code") != 0:
                code = data.get("code")
                msg = data.get("message", "详情获取失败")
                if code == -101:
                    return AdapterResult(success=False, error=f"B站 cookie 失效: {msg}")
                if code in (-352, -509, 412):
                    return AdapterResult(success=False, error=f"B站风控/频控: {msg}")
                return AdapterResult(success=False, error=f"B站详情失败: {msg} (code={code})")
            v = data.get("data", {}) or {}
            stat = v.get("stat", {}) or {}
            owner = v.get("owner", {}) or {}
            note = self._make_note(
                title=v.get("title", ""),
                content=(v.get("desc") or "").strip(),
                url=f"https://www.bilibili.com/video/{v.get('bvid', bvid)}",
                author=owner.get("name", ""),
                author_id=str(owner.get("mid", "")),
                publish_date=self._ts_to_iso(v.get("pubdate")),
                likes=optional_int(stat.get("like")),
                comments=optional_int(stat.get("reply")),
                collects=optional_int(stat.get("favorite")),
                shares=optional_int(stat.get("share")),
                cover=v.get("pic", ""),
                source_platform=self.platform_name,
                raw_data={
                    "engine": "bilibili_view_api",
                    "aid": v.get("aid"),
                    "bvid": v.get("bvid"),
                    "mid": owner.get("mid"),
                    "pubdate": v.get("pubdate"),
                    "like": stat.get("like"),
                    "reply": stat.get("reply"),
                    "favorite": stat.get("favorite"),
                    "share": stat.get("share"),
                    "view": stat.get("view"),
                    "danmaku": stat.get("danmaku"),
                    "coin": stat.get("coin"),
                    "duration": v.get("duration"),
                    "tname": v.get("tname"),
                    "pubdate_ts": v.get("pubdate"),
                },
            )
            return AdapterResult(success=True, notes=[note], raw_count=1)
        except Exception as exc:
            logger.exception("B站详情采集异常")
            return AdapterResult(success=False, error=f"B站详情异常: {exc}")

    # ── comments: 视频评论（B站 reply API，只读）──
    def comments(self, bvid: str, max_comments: int = 20, **kwargs) -> AdapterResult:
        if not bvid or not str(bvid).strip():
            return AdapterResult(success=False, error="bvid 为空")
        try:
            import requests as _req
            if not self._cookie_ok():
                return AdapterResult(success=False, error="B站 cookie 缺失或无关键认证 cookie，请更新 data/bilibili_cookies.json")
            cookies = self._load_cookies()
            if not cookies:
                return AdapterResult(success=False, error="B站 cookie 不存在，无法获取评论")
            # 先取详情拿 aid（评论API需要oid=aid）
            aid = kwargs.get("aid")
            if not aid:
                det = self.detail(bvid)
                if det.success and det.notes:
                    aid = det.notes[0].raw_data.get("aid")
            if not aid:
                return AdapterResult(success=False, error="无法获取 aid，评论需 aid 参数")
            resp = _req.get(
                "https://api.bilibili.com/x/v2/reply",
                params={"type": 1, "oid": aid, "pn": 1, "ps": max_comments, "sort": 1},
                cookies=cookies,
                headers=self._api_headers(),
                timeout=15,
            )
            data = resp.json()
            if data.get("code") != 0:
                return AdapterResult(success=False, error=f"B站评论失败: {data.get('message')} (code={data.get('code')})")
            replies = (data.get("data", {}) or {}).get("replies", []) or []
            notes = []
            for r in replies[:max_comments]:
                member = r.get("member", {}) or {}
                content = r.get("content", {}) or {}
                notes.append(self._make_note(
                    title="",
                    content=(content.get("message") or "").strip(),
                    url=f"https://www.bilibili.com/video/{bvid}#reply{r.get('rpid')}",
                    author=member.get("uname", ""),
                    author_id=str(member.get("mid", "")),
                    publish_date=self._ts_to_iso(r.get("ctime")),
                    likes=optional_int(r.get("like")),
                    comments=None,
                    collects=None,
                    shares=None,
                    cover="",
                    source_platform=self.platform_name,
                    raw_data={"engine": "bilibili_reply_api", "rpid": r.get("rpid"), "type": "comment"},
                ))
            return AdapterResult(success=True, notes=notes, raw_count=len(notes))
        except Exception as exc:
            logger.exception("B站评论采集异常")
            return AdapterResult(success=False, error=f"B站评论异常: {exc}")

    # ── creator: UP主信息（B站 space API）──
    def creator(self, mid: str, **kwargs) -> AdapterResult:
        if not mid or not str(mid).strip():
            return AdapterResult(success=False, error="mid 为空")
        try:
            import requests as _req
            cookies = self._load_cookies()
            if not cookies:
                return AdapterResult(success=False, error="B站 cookie 不存在，无法获取UP主信息")
            resp = _req.get(
                "https://api.bilibili.com/x/space/acc/info",
                params={"mid": str(mid).strip()},
                cookies=cookies,
                headers=self._api_headers(),
                timeout=15,
            )
            data = resp.json()
            if data.get("code") != 0:
                return AdapterResult(success=False, error=f"B站UP主信息失败: {data.get('message')} (code={data.get('code')})")
            u = data.get("data", {}) or {}
            note = self._make_note(
                title=u.get("name", ""),
                content=(u.get("sign") or "").strip(),
                url=f"https://space.bilibili.com/{u.get('mid', mid)}",
                author=u.get("name", ""),
                author_id=str(u.get("mid", "")),
                publish_date="",
                likes=None,
                comments=None,
                collects=None,
                shares=None,
                cover=u.get("face", ""),
                source_platform=self.platform_name,
                raw_data={
                    "engine": "bilibili_space_api",
                    "mid": u.get("mid"),
                    "level": u.get("level"),
                    "sex": u.get("sex"),
                    "silence": u.get("silence"),
                    "vip_type": (u.get("vip") or {}).get("type"),
                    "type": "creator",
                },
            )
            return AdapterResult(success=True, notes=[note], raw_count=1)
        except Exception as exc:
            logger.exception("B站UP主采集异常")
            return AdapterResult(success=False, error=f"B站UP主异常: {exc}")

    def _load_cookies(self):
        """经 cookie_vault 读取 B站 cookie dict；失败返回 None。"""
        c = to_requests_cookies("bilibili")
        return c if c else None

    @staticmethod
    def _api_headers():
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
        }
