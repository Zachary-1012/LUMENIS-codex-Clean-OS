"""必应搜索采集适配器"""
import re
import urllib.parse
from .base import BaseAdapter, AdapterResult, CollectedNote


class BingSearchAdapter(BaseAdapter):
    platform_name = "bing_search"
    platform_display = "必应搜索"

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """必应全网搜索"""
        try:
            import requests
            url = f"https://www.bing.com/search?q={urllib.parse.quote(keyword)}&count={max_results}"
            headers = {
                "User-Agent": self.config["user_agent"],
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            resp = requests.get(url, headers=headers, timeout=self.config["request_timeout"])
            resp.raise_for_status()
            notes = self._parse_results(resp.text)
            return AdapterResult(success=True, notes=notes[:max_results], raw_count=len(notes))
        except Exception as e:
            return AdapterResult(success=False, error=str(e))

    def _parse_results(self, html: str) -> list:
        notes = []
        # 必应搜索结果
        pattern = r'<li class="b_algo">.*?<h2><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>.*?<p[^>]*>(.*?)</p>'
        for url, title, content in re.findall(pattern, html, re.DOTALL):
            clean_title = re.sub(r"<[^>]+>", "", title).strip()
            clean_content = re.sub(r"<[^>]+>", "", content).strip()
            if clean_title:
                notes.append(self._make_note(
                    title=clean_title,
                    content=clean_content,
                    url=url,
                    author="必应搜索",
                ))
        return notes
