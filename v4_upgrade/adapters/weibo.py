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
        self._manager = manager

    def _get_manager(self):
        """懒加载微博登录管理器单例。"""
        if self._manager is not None:
            return self._manager
        try:
            from weibo_login_manager import get_weibo_manager
            return get_weibo_manager()
        except Exception as exc:
            raise RuntimeError(f"无法加载微博登录管理器: {exc}") from exc

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
            manager = self._get_manager()

            # 登录态前置检查
            login_status = manager.check_login_status()
            if not login_status.get("logged_in", False):
                return AdapterResult(
                    success=False,
                    error="微博登录态失效，请更新 cookie 或重新扫码登录",
                )

            cookie_string = manager.get_cookie_string()
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
                # 登录失效/风控如实返回
                if "登录" in msg or "login" in msg.lower():
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
