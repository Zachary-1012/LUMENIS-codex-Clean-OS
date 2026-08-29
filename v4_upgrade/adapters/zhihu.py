"""知乎采集适配器 - 搜索API+页面解析"""
import re
import urllib.parse
from .base import BaseAdapter, AdapterResult, CollectedNote


class ZhihuAdapter(BaseAdapter):
    platform_name = "zhihu"
    platform_display = "知乎"

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """知乎搜索采集"""
        try:
            import requests
            url = f"https://www.zhihu.com/api/v4/search_v3?t=general&q={urllib.parse.quote(keyword)}&limit={max_results}"
            headers = {
                "User-Agent": self.config["user_agent"],
                "Referer": "https://www.zhihu.com/",
            }
            resp = requests.get(url, headers=headers, timeout=self.config["request_timeout"])
            data = resp.json()
            notes = []
            for item in data.get("data", []):
                obj = item.get("object", {})
                if obj.get("type") == "answer":
                    question = obj.get("question", {})
                    notes.append(self._make_note(
                        title=question.get("title", ""),
                        content=re.sub(r"<[^>]+>", "", obj.get("excerpt", "")),
                        url=f"https://www.zhihu.com/question/{question.get('id')}/answer/{obj.get('id')}",
                        author=obj.get("author", {}).get("name", ""),
                        author_id=str(obj.get("author", {}).get("id", "")),
                        likes=obj.get("voteup_count", 0),
                        comments=obj.get("comment_count", 0),
                        publish_date=obj.get("created_time", ""),
                        raw_data=obj,
                    ))
                elif obj.get("type") == "article":
                    notes.append(self._make_note(
                        title=obj.get("title", ""),
                        content=re.sub(r"<[^>]+>", "", obj.get("excerpt", "")),
                        url=obj.get("url", ""),
                        author=obj.get("author", {}).get("name", ""),
                        likes=obj.get("voteup_count", 0),
                        comments=obj.get("comment_count", 0),
                        raw_data=obj,
                    ))
            return AdapterResult(success=True, notes=notes[:max_results], raw_count=len(notes))
        except Exception as e:
            return AdapterResult(success=False, error=str(e))
