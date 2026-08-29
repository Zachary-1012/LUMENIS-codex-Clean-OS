"""大众点评采集适配器 - 商场评价搜索"""
import re
import urllib.parse
from .base import BaseAdapter, AdapterResult, CollectedNote


class DianpingAdapter(BaseAdapter):
    platform_name = "dianping"
    platform_display = "大众点评"

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """
        大众点评商场/商户评价搜索
        反爬较严，建议低频+CDP模式
        """
        try:
            import requests
            # 搜索商户
            url = f"https://www.dianping.com/search/keyword/1/0_{urllib.parse.quote(keyword)}"
            headers = {
                "User-Agent": self.config["user_agent"],
                "Referer": "https://www.dianping.com/",
            }
            resp = requests.get(url, headers=headers, timeout=self.config["request_timeout"])
            notes = self._parse_shops(resp.text, keyword)
            return AdapterResult(success=True, notes=notes[:max_results], raw_count=len(notes))
        except Exception as e:
            return AdapterResult(success=False, error=str(e))

    def _parse_shops(self, html: str, keyword: str) -> list:
        notes = []
        # 解析商户列表
        pattern = r'<div class="shop-list[^"]*">.*?<div class="tit">.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<div class="star[^"]*"[^>]*>.*?<span class="score[^"]*">([^<]*)</span>'
        for url, name, score in re.findall(pattern, html, re.DOTALL)[:20]:
            clean_name = re.sub(r"<[^>]+>", "", name).strip()
            if clean_name:
                notes.append(self._make_note(
                    title=f"{clean_name} - 评分{score}",
                    content=f"大众点评商户评价，关键词: {keyword}",
                    url=url if url.startswith("http") else f"https://www.dianping.com{url}",
                    author="大众点评",
                    likes=0,
                ))
        return notes
