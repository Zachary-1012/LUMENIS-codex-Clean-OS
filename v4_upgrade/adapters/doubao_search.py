"""
豆包AI搜索适配器
通过豆包/方舟API做全网话题检索，AI聚合后返回结构化结果
需要配置 ARK_API_KEY
"""
import json
from .base import BaseAdapter, AdapterResult, CollectedNote


class DoubaoSearchAdapter(BaseAdapter):
    platform_name = "doubao_search"
    platform_display = "豆包AI搜索"

    def __init__(self):
        super().__init__()
        self.api_key = None
        self.api_base = "https://ark.cn-beijing.volces.com/api/v3"
        self._load_config()

    def _load_config(self):
        """从环境变量或.env加载API Key"""
        import os
        self.api_key = os.environ.get("ARK_API_KEY", "")
        if not self.api_key:
            # 尝试从.env文件读取
            env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("ARK_API_KEY"):
                            self.api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break

    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """豆包AI全网搜索"""
        if not self.api_key:
            return AdapterResult(success=False, error="未配置ARK_API_KEY，豆包搜索不可用")
        try:
            import requests
            # 调用豆包搜索API（对接现有ark_llm.py的实现模式）
            url = f"{self.api_base}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            prompt = f"""请搜索全网关于「{keyword}」的最新舆情信息，返回最多{max_results}条相关内容。
要求：
1. 每条包含标题、摘要、来源URL、发布时间、来源平台
2. 优先返回社交媒体、新闻、论坛内容
3. 以JSON数组格式返回，字段：title, content, url, publish_date, source_platform, author
"""
            payload = {
                "model": "doubao-pro-32k",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            notes = self._parse_ai_response(content)
            return AdapterResult(success=True, notes=notes[:max_results], raw_count=len(notes))
        except Exception as e:
            return AdapterResult(success=False, error=str(e))

    def _parse_ai_response(self, content: str) -> list:
        """解析AI返回的JSON"""
        notes = []
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group())
                for item in items:
                    notes.append(self._make_note(
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                        url=item.get("url", ""),
                        author=item.get("author", ""),
                        publish_date=item.get("publish_date", ""),
                        source_platform=item.get("source_platform", "doubao_search"),
                        raw_data=item,
                    ))
        except Exception:
            pass
        return notes
