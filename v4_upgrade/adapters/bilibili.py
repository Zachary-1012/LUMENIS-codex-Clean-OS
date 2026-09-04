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

from .base import BaseAdapter, AdapterResult

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
        self._manager = manager

    def _get_manager(self):
        """懒加载 B站登录管理器单例。"""
        if self._manager is not None:
            return self._manager
        try:
            from bilibili_login_manager import get_bilibili_manager
            return get_bilibili_manager()
        except Exception as exc:
            raise RuntimeError(f"无法加载 B站登录管理器: {exc}") from exc

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        try:
            manager = self._get_manager()

            # 登录态前置检查：失效则如实返回，不假成功
            login_status = manager.check_login_status()
            if not login_status.get("logged_in", False):
                return AdapterResult(
                    success=False,
                    error="B站登录态失效，请更新 cookie 或重新扫码登录",
                )

            raw = manager.search_videos(keyword.strip(), page=1, page_size=max_results)
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
                    likes=0,       # 搜索API不返回点赞数
                    comments=0,    # 搜索API不返回评论数
                    collects=int(v.get("favorites", 0) or 0),
                    shares=0,
                    cover="",      # 搜索API不返回封面
                    source_platform=self.platform_name,
                    raw_data={
                        "engine": "bilibili_search_api",
                        "aid": v.get("id"),
                        "bvid": v.get("bvid"),
                        "play": v.get("play"),
                        "video_review": v.get("video_review"),
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
