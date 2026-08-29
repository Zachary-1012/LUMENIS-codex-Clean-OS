"""搜狗微信采集适配器 - 公众号文章搜索"""
import re
import urllib.parse
from .base import BaseAdapter, AdapterResult, CollectedNote


class SogouWechatAdapter(BaseAdapter):
    platform_name = "sogou_wechat"
    platform_display = "搜狗微信"

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """搜狗微信公众号文章搜索"""
        try:
            import requests
            url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.parse.quote(keyword)}&num={max_results}"
            headers = {
                "User-Agent": self.config["user_agent"],
                "Referer": "https://weixin.sogou.com/",
            }
            resp = requests.get(url, headers=headers, timeout=self.config["request_timeout"])
            resp.encoding = "utf-8"
            notes = self._parse_results(resp.text)
            return AdapterResult(success=True, notes=notes[:max_results], raw_count=len(notes))
        except Exception as e:
            return AdapterResult(success=False, error=str(e))

    def _parse_results(self, html: str) -> list:
        notes = []
        # 搜狗微信搜索结果
        pattern = r'<div class="txt-box">.*?<h3>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<p class="txt-info"[^>]*>(.*?)</p>.*?<a[^>]*id="sogou_vr_11002301_box_[\d]+"[^>]*>(.*?)</a>'
        for url, title, content, account in re.findall(pattern, html, re.DOTALL):
            clean_title = re.sub(r"<[^>]+>", "", title).strip()
            clean_content = re.sub(r"<[^>]+>", "", content).strip()
            clean_account = re.sub(r"<[^>]+>", "", account).strip()
            if clean_title:
                notes.append(self._make_note(
                    title=clean_title,
                    content=clean_content,
                    url="https://weixin.sogou.com" + url if url.startswith("/") else url,
                    author=clean_account or "微信公众号",
                ))
        return notes
