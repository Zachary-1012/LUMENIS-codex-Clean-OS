# -*- coding: utf-8 -*-
"""
知乎（Zhihu）内容采集适配器
----------------------------
定位：服务于 Z-Brand Core 多平台内容采集。
调用知乎搜索 API v4（匿名/带 cookie 均可），薄封装为 v4 BaseAdapter 契约，
接入熔断器/限流/重试/降级体系。

数据主路径：知乎搜索 API
  https://www.zhihu.com/api/v4/search_v3?t=general&q={keyword}&limit={n}
返回 data[].object（type=answer/article/question 等）。

状态映射：
  - 有结果       → SUCCESS
  - 正常空       → EMPTY (success=True, notes=[])
  - API error    → COLLECT_ERROR
  - 异常         → COLLECT_ERROR

时间口径：created_time/updated_time 为 Unix 秒级时间戳，转 ISO 8601；
采集时间由入库层写 captured_at，二者严格分离。

只读红线：不点赞、不评论、不关注、不私信、不执行任何账号写操作。
"""
import re
import logging
from datetime import datetime, timezone

import requests

from .base import BaseAdapter, AdapterResult

logger = logging.getLogger(__name__)


class ZhihuAdapter(BaseAdapter):
    """知乎搜索适配器（搜索 API v4，只读采集）"""

    platform_name = "zhihu"
    platform_display = "知乎"

    SEARCH_URL = "https://www.zhihu.com/api/v4/search_v3"

    _DEFAULT_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, cookie_string: str = "", **kwargs):
        super().__init__(**kwargs)
        self._cookie_string = cookie_string

    def _get_headers(self) -> dict:
        headers = {
            "User-Agent": self._DEFAULT_UA,
            "Referer": "https://www.zhihu.com/",
            "Accept": "application/json, text/plain, */*",
        }
        if self._cookie_string:
            headers["Cookie"] = self._cookie_string
        return headers

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        if not keyword or not keyword.strip():
            return AdapterResult(success=False, error="关键词为空")
        try:
            from urllib.parse import quote
            params = {
                "t": "general",
                "q": keyword.strip(),
                "limit": min(max_results, 20),
                "correction": 1,
            }
            resp = requests.get(
                self.SEARCH_URL,
                headers=self._get_headers(),
                params=params,
                timeout=15,
            )
            data = resp.json()

            # 知乎 API 错误响应
            if isinstance(data, dict) and data.get("error"):
                err = data["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                return AdapterResult(success=False, error=f"知乎搜索API错误: {msg}")

            items = data.get("data", []) if isinstance(data, dict) else []
            notes = []
            for item in items:
                obj = item.get("object", {}) if isinstance(item, dict) else {}
                note = self._object_to_note(obj)
                if note:
                    notes.append(note)
                if len(notes) >= max_results:
                    break

            if notes:
                return AdapterResult(success=True, notes=notes, raw_count=len(notes))
            # 正常无内容
            return AdapterResult(success=True, notes=[], raw_count=0)

        except Exception as exc:
            logger.exception("知乎采集异常")
            return AdapterResult(success=False, error=f"知乎采集异常: {exc}")

    def _object_to_note(self, obj: dict):
        """将知乎搜索结果 object 转为标准化 CollectedNote。"""
        try:
            obj_type = obj.get("type", "")
            if obj_type == "answer":
                question = obj.get("question", {}) or {}
                qid = question.get("id", "")
                aid = obj.get("id", "")
                url = f"https://www.zhihu.com/question/{qid}/answer/{aid}" if qid and aid else ""
                title = question.get("title", "") or f"知乎回答 {aid}"
                content = self._clean_html(obj.get("excerpt", ""))
                author = (obj.get("author") or {}).get("name", "")
                author_id = str((obj.get("author") or {}).get("id", ""))
                likes = int(obj.get("voteup_count", 0) or 0)
                comments = int(obj.get("comment_count", 0) or 0)
                publish_date = self._ts_to_iso(obj.get("created_time"))
            elif obj_type == "article":
                aid = obj.get("id", "")
                url = obj.get("url", "") or f"https://zhuanlan.zhihu.com/p/{aid}"
                title = obj.get("title", "") or f"知乎文章 {aid}"
                content = self._clean_html(obj.get("excerpt", ""))
                author = (obj.get("author") or {}).get("name", "")
                author_id = str((obj.get("author") or {}).get("id", ""))
                likes = int(obj.get("voteup_count", 0) or 0)
                comments = int(obj.get("comment_count", 0) or 0)
                publish_date = self._ts_to_iso(obj.get("created"))
            elif obj_type == "question":
                qid = obj.get("id", "")
                url = f"https://www.zhihu.com/question/{qid}" if qid else ""
                title = obj.get("title", "") or f"知乎问题 {qid}"
                content = self._clean_html(obj.get("excerpt", ""))
                author = (obj.get("author") or {}).get("name", "")
                author_id = str((obj.get("author") or {}).get("id", ""))
                likes = 0
                comments = int(obj.get("answer_count", 0) or 0)
                publish_date = self._ts_to_iso(obj.get("created"))
            else:
                # 其他类型（live/column 等）跳过，不臆造
                return None

            if not title and not content:
                return None

            return self._make_note(
                title=title[:120],
                content=content,
                url=url,
                author=author,
                author_id=author_id,
                publish_date=publish_date,
                likes=likes,
                comments=comments,
                collects=0,
                shares=0,
                cover="",
                source_platform=self.platform_name,
                raw_data={
                    "engine": "zhihu_search_v3",
                    "object_type": obj_type,
                    "id": obj.get("id"),
                    "updated_time": obj.get("updated_time"),
                },
            )
        except Exception as exc:
            logger.warning("知乎 object 解析失败: %s", exc)
            return None

    @staticmethod
    def _clean_html(text: str) -> str:
        """去除 HTML 标签及多余空白。"""
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", str(text))
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _ts_to_iso(ts) -> str:
        """Unix 秒级时间戳 → ISO 8601；无效返回空串（不臆造）。"""
        if not ts:
            return ""
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
        except (ValueError, TypeError, OSError):
            return ""
