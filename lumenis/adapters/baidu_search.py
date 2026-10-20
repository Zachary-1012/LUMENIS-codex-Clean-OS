"""百度搜索采集适配器 - 搜索结果页解析"""
import re
import urllib.parse
from .base import BaseAdapter, AdapterResult, CollectedNote


class BaiduSearchAdapter(BaseAdapter):
    platform_name = "baidu_search"
    platform_display = "百度搜索"

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """百度全网搜索"""
        try:
            import requests
            url = f"https://www.baidu.com/s?wd={urllib.parse.quote(keyword)}&rn={max_results}"
            headers = {
                "User-Agent": self.config["user_agent"],
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            resp = requests.get(url, headers=headers, timeout=self.config["request_timeout"])
            resp.raise_for_status()
            resp.encoding = "utf-8"
            notes = self._parse_search_results(resp.text, keyword)
            return AdapterResult(success=True, notes=notes[:max_results], raw_count=len(notes))
        except Exception as e:
            return AdapterResult(success=False, error=str(e))

    def _parse_search_results(self, html: str, keyword: str) -> list:
        """解析百度搜索结果页"""
        notes = []
        # 百度搜索结果容器
        pattern = r'<div class="result[^"]*"[^>]*>.*?<h3[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<span class="content-right_8Zs40">(.*?)</span>'
        matches = re.findall(pattern, html, re.DOTALL)
        for url, title, content in matches:
            clean_title = re.sub(r"<[^>]+>", "", title).strip()
            clean_content = re.sub(r"<[^>]+>", "", content).strip()
            if clean_title:
                notes.append(self._make_note(
                    title=clean_title,
                    content=clean_content,
                    url=url,
                    author="百度搜索",
                    source_platform="baidu_search",
                ))
        # 备用解析：简单提取所有搜索结果链接
        if not notes:
            link_pattern = r'<h3[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
            for url, title in re.findall(link_pattern, html, re.DOTALL)[:20]:
                clean = re.sub(r"<[^>]+>", "", title).strip()
                if clean and "baidu.com" not in url:
                    notes.append(self._make_note(title=clean, url=url, author="百度搜索"))
        return notes
