"""什么值得买采集适配器"""
import re
import urllib.parse
from .base import BaseAdapter, AdapterResult, CollectedNote


class SmzdmAdapter(BaseAdapter):
    platform_name = "smzdm"
    platform_display = "什么值得买"

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """什么值得买搜索"""
        try:
            import requests
            url = f"https://search.smzdm.com/?c=home&s={urllib.parse.quote(keyword)}&v=b"
            headers = {"User-Agent": self.config["user_agent"]}
            resp = requests.get(url, headers=headers, timeout=self.config["request_timeout"])
            notes = self._parse_results(resp.text)
            return AdapterResult(success=True, notes=notes[:max_results], raw_count=len(notes))
        except Exception as e:
            return AdapterResult(success=False, error=str(e))

    def _parse_results(self, html: str) -> list:
        notes = []
        pattern = r'<h5 class="feed-block__title">.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
        for url, title in re.findall(pattern, html, re.DOTALL)[:20]:
            clean = re.sub(r"<[^>]+>", "", title).strip()
            if clean:
                notes.append(self._make_note(
                    title=clean,
                    url=url,
                    author="什么值得买",
                ))
        return notes
