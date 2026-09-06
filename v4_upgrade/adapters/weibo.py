# -*- coding: utf-8 -*-
"""
微博（Weibo）内容采集适配器
----------------------------
定位：服务于 Z-Brand Core 多平台内容采集。
基于 weibo_login_manager 的 cookie + requests 调用微博移动端搜索 API，
薄封装为 v4 BaseAdapter 契约，接入熔断器/限流/重试/降级体系。

数据主路径：微博移动端搜索 API
  https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{keyword}
返回 cards[].mblog（微博正文/作者/点赞/评论/转发/发布时间）。

状态映射：
  - ok=1 且有 mblog → SUCCESS
  - ok=1 但空      → EMPTY (success=True, notes=[])
  - 登录失效/cookie 无效 → SESSION_EXPIRED 语义
  - 风控/验证码     → RISK_WARNING 语义（如实返回，不硬刚）
  - 其他错误        → COLLECT_ERROR

时间口径：created_at 为 "%a %b %d %H:%M:%S %z %Y"，转 ISO 8601；
采集时间由入库层写 captured_at，二者严格分离。

只读红线：不发微博、不评论、不点赞、不关注、不私信、不执行任何账号写操作；
遇到风控/验证码如实返回，不破解、不绕过、不对抗。
"""
import re
import logging
from datetime import datetime

import requests

from .base import BaseAdapter, AdapterResult
from .cookie_vault import to_cookie_string, check_cookie_status

logger = logging.getLogger(__name__)


class WeiboAdapter(BaseAdapter):
    """微博搜索适配器（移动端 API + cookie，只读采集）"""

    platform_name = "weibo"
    platform_display = "微博"

    SEARCH_URL = "https://m.weibo.cn/api/container/getIndex"
    # type=1 综合搜索；type=60 实时；type=61 关注；type=62 视频
    CONTAINER_TEMPLATE = "100103type={type}&q={keyword}"

    _MOBILE_UA = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
        "Mobile/15E148 Safari/604.1"
    )

    def __init__(self, manager=None, **kwargs):
        super().__init__(**kwargs)
        self._manager = manager  # 向后兼容：旧测试传入 manager，现统一走 cookie_vault

    @staticmethod
    def _cookie_ok() -> bool:
        """经 cookie_vault 检查微博 cookie 是否存在且含关键认证 cookie。"""
        s = check_cookie_status("weibo")
        return s["status"] == "ACTIVE"

    def _get_headers(self, cookie_string: str) -> dict:
        return {
            "User-Agent": self._MOBILE_UA,
            "Referer": "https://m.weibo.cn/",
            "Accept": "application/json, text/plain, */*",
            "Cookie": cookie_string,
            "X-Requested-With": "XMLHttpRequest",
        }

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        try:
            # 登录态前置检查（经 cookie_vault，不打印 cookie 内容）
            if not self._cookie_ok():
                return AdapterResult(
                    success=False,
                    error="微博 cookie 缺失或无关键认证 cookie，请更新 data/weibo_cookies.json",
                )

            cookie_string = to_cookie_string("weibo")
            if not cookie_string:
                return AdapterResult(success=False, error="微博 cookie 为空")

            from urllib.parse import quote

            containerid = self.CONTAINER_TEMPLATE.format(
                type=1, keyword=quote(keyword.strip())
            )
            params = {"containerid": containerid}

            resp = requests.get(
                self.SEARCH_URL,
                headers=self._get_headers(cookie_string),
                params=params,
                timeout=15,
            )
            data = resp.json()

            # 微博 API ok=1 表示成功
            if data.get("ok") != 1:
                msg = data.get("msg", "") or str(data)
                # 登录失效/风控如实返回（ok=-100 为未登录跳转SSO）
                if data.get("ok") == -100 or "登录" in msg or "login" in msg.lower() or "passport" in msg.lower():
                    return AdapterResult(success=False, error=f"微博登录失效: {msg}")
                if "验证" in msg or "captcha" in msg.lower() or "风险" in msg:
                    return AdapterResult(success=False, error=f"微博风控/验证: {msg}")
                return AdapterResult(success=False, error=f"微博搜索失败: {msg}")

            cards = (data.get("data") or {}).get("cards") or []
            notes = []
            for card in cards:
                mblog = card.get("mblog")
                if not mblog:
                    continue
                note = self._mblog_to_note(mblog)
                if note:
                    notes.append(note)
                if len(notes) >= max_results:
                    break

            if notes:
                return AdapterResult(success=True, notes=notes, raw_count=len(notes))
            # 正常无内容
            return AdapterResult(success=True, notes=[], raw_count=0)

        except Exception as exc:
            logger.exception("微博采集异常")
            return AdapterResult(success=False, error=f"微博采集异常: {exc}")

    def _mblog_to_note(self, mblog: dict):
        """将微博 mblog 转为标准化 CollectedNote。"""
        try:
            text_html = mblog.get("text", "") or ""
            content = self._clean_html(text_html)
            user = mblog.get("user") or {}
            mid = str(mblog.get("mid") or mblog.get("id") or "")
            if not mid and not content:
                return None
            url = f"https://m.weibo.cn/status/{mid}" if mid else ""
            return self._make_note(
                title=content[:80] or f"微博 {mid}",
                content=content,
                url=url,
                author=user.get("screen_name", ""),
                author_id=str(user.get("id", "")),
                publish_date=self._parse_weibo_date(mblog.get("created_at")),
                likes=int(mblog.get("attitudes_count", 0) or 0),
                comments=int(mblog.get("comments_count", 0) or 0),
                collects=0,  # 微博搜索API不返回收藏数
                shares=int(mblog.get("reposts_count", 0) or 0),
                cover="",
                source_platform=self.platform_name,
                raw_data={
                    "engine": "weibo_mobile_search_api",
                    "mid": mid,
                    "id": mblog.get("id"),
                    "is_long_text": mblog.get("isLongText", False),
                    "source": mblog.get("source", ""),
                    "region_name": mblog.get("region_name", ""),
                    "page_info": bool(mblog.get("page_info")),
                },
            )
        except Exception as exc:
            logger.warning("微博 mblog 解析失败: %s", exc)
            return None

    @staticmethod
    def _clean_html(text: str) -> str:
        """去除微博正文中的 HTML 标签及多余空白。"""
        if not text:
            return ""
        # 去掉 <a> 标签但保留链接文本（话题/ @用户 等）
        text = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", text, flags=re.DOTALL)
        # 去掉其余 HTML 标签
        text = re.sub(r"<[^>]+>", "", text)
        # HTML 实体
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _parse_weibo_date(raw: str) -> str:
        """微博 created_at → ISO 8601；无法解析返回空串（不臆造）。"""
        if not raw:
            return ""
        # 格式如 "Tue Sep 03 12:00:00 +0800 2024"
        for fmt in ("%a %b %d %H:%M:%S %z %Y", "%a %b %d %H:%M:%S %Y"):
            try:
                return datetime.strptime(raw.strip(), fmt).isoformat()
            except (ValueError, TypeError):
                continue
        # 微博有时返回 "刚刚" / "x分钟前" / "x小时前" / "昨天 HH:MM"
        return ""

    # ── detail: 单条微博详情（statuses/show API）──
    def detail(self, mid: str, **kwargs) -> AdapterResult:
        if not mid or not str(mid).strip():
            return AdapterResult(success=False, error="mid 为空")
        try:
            cookie_string = to_cookie_string("weibo")
            if not cookie_string:
                return AdapterResult(success=False, error="微博 cookie 为空")
            resp = requests.get(
                "https://m.weibo.cn/statuses/show",
                params={"id": str(mid).strip()},
                headers=self._get_headers(cookie_string),
                timeout=15,
            )
            data = resp.json()
            if data.get("ok") != 1:
                msg = data.get("msg", "") or str(data)
                if "登录" in msg or "login" in msg.lower():
                    return AdapterResult(success=False, error=f"微博登录失效: {msg}")
                return AdapterResult(success=False, error=f"微博详情失败: {msg}")
            mblog = data.get("data") or {}
            note = self._mblog_to_note(mblog)
            if note:
                return AdapterResult(success=True, notes=[note], raw_count=1)
            return AdapterResult(success=True, notes=[], raw_count=0)
        except Exception as exc:
            logger.exception("微博详情采集异常")
            return AdapterResult(success=False, error=f"微博详情异常: {exc}")

    # ── comments: 微博评论（comments/show API，只读）──
    def comments(self, mid: str, max_comments: int = 20, **kwargs) -> AdapterResult:
        if not mid or not str(mid).strip():
            return AdapterResult(success=False, error="mid 为空")
        try:
            cookie_string = to_cookie_string("weibo")
            if not cookie_string:
                return AdapterResult(success=False, error="微博 cookie 为空")
            resp = requests.get(
                "https://m.weibo.cn/api/comments/show",
                params={"id": str(mid).strip(), "page": 1},
                headers=self._get_headers(cookie_string),
                timeout=15,
            )
            data = resp.json()
            if data.get("ok") != 1:
                return AdapterResult(success=False, error=f"微博评论失败: {data.get('msg', str(data))}")
            hot = (data.get("data") or {}).get("hot_data") or []
            normal = (data.get("data") or {}).get("data") or []
            all_comments = (hot + normal)[:max_comments]
            notes = []
            for c in all_comments:
                user = c.get("user") or {}
                notes.append(self._make_note(
                    title="",
                    content=self._clean_html(c.get("text", "")),
                    url=f"https://m.weibo.cn/status/{mid}#cmt{c.get('id')}",
                    author=user.get("screen_name", ""),
                    author_id=str(user.get("id", "")),
                    publish_date=self._parse_weibo_date(c.get("created_at")),
                    likes=int(c.get("like_count", 0) or 0),
                    comments=0,
                    collects=0,
                    shares=0,
                    cover="",
                    source_platform=self.platform_name,
                    raw_data={"engine": "weibo_comments_api", "cid": c.get("id"), "type": "comment"},
                ))
            return AdapterResult(success=True, notes=notes, raw_count=len(notes))
        except Exception as exc:
            logger.exception("微博评论采集异常")
            return AdapterResult(success=False, error=f"微博评论异常: {exc}")

    # ── creator: 微博用户信息（container/getIndex INFO tab）──
    def creator(self, uid: str, **kwargs) -> AdapterResult:
        if not uid or not str(uid).strip():
            return AdapterResult(success=False, error="uid 为空")
        try:
            cookie_string = to_cookie_string("weibo")
            if not cookie_string:
                return AdapterResult(success=False, error="微博 cookie 为空")
            containerid = f"230283{uid}_-_INFO"
            resp = requests.get(
                self.SEARCH_URL,
                params={"containerid": containerid},
                headers=self._get_headers(cookie_string),
                timeout=15,
            )
            data = resp.json()
            if data.get("ok") != 1:
                return AdapterResult(success=False, error=f"微博用户信息失败: {data.get('msg', str(data))}")
            cards = (data.get("data") or {}).get("cards") or []
            user_info = {}
            for card in cards:
                if card.get("card_type") == 11 and card.get("card_group"):
                    for item in card["card_group"]:
                        if item.get("card_type") == 10:
                            user_info = item.get("user") or {}
                            break
                if card.get("card_type") == 10:
                    user_info = card.get("user") or {}
                    break
            if not user_info:
                return AdapterResult(success=True, notes=[], raw_count=0)
            note = self._make_note(
                title=user_info.get("screen_name", ""),
                content=(user_info.get("description") or "").strip(),
                url=f"https://m.weibo.cn/u/{user_info.get('id', uid)}",
                author=user_info.get("screen_name", ""),
                author_id=str(user_info.get("id", "")),
                publish_date="",
                likes=int(user_info.get("followers_count", 0) or 0),
                comments=0,
                collects=0,
                shares=int(user_info.get("statuses_count", 0) or 0),
                cover=user_info.get("avatar_hd", ""),
                source_platform=self.platform_name,
                raw_data={
                    "engine": "weibo_user_info_api",
                    "uid": user_info.get("id"),
                    "followers": user_info.get("followers_count"),
                    "follow_count": user_info.get("follow_count"),
                    "verified": user_info.get("verified"),
                    "verified_reason": user_info.get("verified_reason"),
                    "type": "creator",
                },
            )
            return AdapterResult(success=True, notes=[note], raw_count=1)
        except Exception as exc:
            logger.exception("微博用户采集异常")
            return AdapterResult(success=False, error=f"微博用户异常: {exc}")
