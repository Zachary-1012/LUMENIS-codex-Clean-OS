"""LUMENIS UI/Data Reality Audit（V2 P0-17，ZBC侧）

UI 数据真实性审计：检查页面是否使用假数据、假状态、假实时。
每个页面必须标注连接状态：CONNECTED / PARTIALLY_CONNECTED / UI_ONLY / NOT_IMPLEMENTED / NO_DATA。
禁止把 UI_ONLY 伪装成 CONNECTED。
"""
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PageRealityStatus:
    """页面真实性状态。"""
    page_id: str
    page_name: str
    route: str
    connection_status: str  # CONNECTED / PARTIALLY_CONNECTED / UI_ONLY / NOT_IMPLEMENTED / NO_DATA
    api_endpoints: List[str] = field(default_factory=list)
    real_data_sources: List[str] = field(default_factory=list)
    fake_data_indicators: List[str] = field(default_factory=list)
    hardcoded_values: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "page_name": self.page_name,
            "route": self.route,
            "connection_status": self.connection_status,
            "api_endpoints": self.api_endpoints,
            "real_data_sources": self.real_data_sources,
            "fake_data_indicators": self.fake_data_indicators,
            "hardcoded_values": self.hardcoded_values,
            "notes": self.notes,
        }


# 假数据检测模式
FAKE_DATA_PATTERNS = [
    (r"sample[_-]?data", "sample_data 变量"),
    (r"mock[_-]?data", "mock_data 变量"),
    (r"fake[_-]?data", "fake_data 变量"),
    (r"dummy[_-]?data", "dummy_data 变量"),
    (r"placeholder", "placeholder 文本"),
    (r"TODO.*data", "TODO 数据"),
    (r"FIXME.*data", "FIXME 数据"),
]

# 真实 API 调用模式
REAL_API_PATTERNS = [
    r"fetch\(",
    r"axios\.",
    r"\.get\(",
    r"\.post\(",
    r"url_for\(",
    r"/api/",
    r"/lumenis/api/",
]


class UIRealityAuditor:
    """UI 数据真实性审计器。"""

    def __init__(self, templates_dir: str, static_dir: str):
        self._templates_dir = templates_dir
        self._static_dir = static_dir
        self._pages: Dict[str, PageRealityStatus] = {}

    def audit_page(self, page_id: str, page_name: str, route: str,
                   template_file: str = None) -> PageRealityStatus:
        """审计单个页面。"""
        status = PageRealityStatus(
            page_id=page_id, page_name=page_name, route=route,
            connection_status="UNKNOWN",
        )

        content = ""
        if template_file:
            path = os.path.join(self._templates_dir, template_file)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    pass

        # 检测真实 API 调用
        for pattern in REAL_API_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                status.api_endpoints.extend(matches[:5])

        # 检测假数据
        for pattern, desc in FAKE_DATA_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                status.fake_data_indicators.append(desc)

        # 检测硬编码数字（排除CSS值）
        hardcoded = re.findall(r'(?<!\w)(\d{4,})(?!\w)', content)
        if hardcoded:
            status.hardcoded_values = list(set(hardcoded))[:5]

        # 判定连接状态
        if status.api_endpoints and not status.fake_data_indicators:
            status.connection_status = "CONNECTED"
        elif status.api_endpoints and status.fake_data_indicators:
            status.connection_status = "PARTIALLY_CONNECTED"
            status.notes = "有真实API但也存在假数据标记"
        elif not content:
            status.connection_status = "NOT_IMPLEMENTED"
        elif status.fake_data_indicators:
            status.connection_status = "UI_ONLY"
            status.notes = "仅UI，无真实API绑定"
        else:
            status.connection_status = "NO_DATA"
            status.notes = "页面存在但无数据"

        self._pages[page_id] = status
        return status

    def audit_all(self, page_registry: List[Dict[str, str]]) -> List[PageRealityStatus]:
        """批量审计所有页面。"""
        results = []
        for page in page_registry:
            result = self.audit_page(
                page_id=page["page_id"],
                page_name=page["page_name"],
                route=page["route"],
                template_file=page.get("template"),
            )
            results.append(result)
        return results

    def summary(self) -> Dict[str, Any]:
        by_status = {}
        for p in self._pages.values():
            by_status[p.connection_status] = by_status.get(p.connection_status, 0) + 1
        fake_pages = [p.page_name for p in self._pages.values()
                      if p.fake_data_indicators]
        return {
            "total_pages": len(self._pages),
            "by_status": by_status,
            "pages_with_fake_data": fake_pages,
            "fully_connected": by_status.get("CONNECTED", 0),
            "needs_attention": sum(v for k, v in by_status.items()
                                   if k in ("UI_ONLY", "PARTIALLY_CONNECTED")),
        }

    def get_page(self, page_id: str) -> Optional[PageRealityStatus]:
        return self._pages.get(page_id)
