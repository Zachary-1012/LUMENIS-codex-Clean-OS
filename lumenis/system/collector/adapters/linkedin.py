# -*- coding: utf-8 -*-
"""LinkedIn Adapter 骨架（PLANNED，目录状态可见，采集能力未实现）。

LinkedIn 需官方API权限。本骨架定义 schema + mapping + CRUD 接口。
API 权限与提供方实现均需验证，不能据此自动启用采集。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .platform_naming import map_raw_to_normalized
from .registry import register_adapter

logger = logging.getLogger(__name__)


class LinkedInAdapter(BasePlatformAdapter):
    """LinkedIn主链路适配器骨架（PLANNED状态）。"""

    platform = "linkedin"
    enabled = False
    monitor_priority = "planned"

    RAW_CONTENT_TABLE = "linkedin_posts"
    RAW_USER_TABLE = "linkedin_users"

    def capability_map(self) -> Dict[str, str]:
        """Schema and callable placeholders are not implemented acquisition."""
        return {name: "not_supported" for name in
                ("search", "detail", "comments", "author", "author_posts")} | {
                    "healthcheck": "not_configured"}

    def normalize_to_platform_contents(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return map_raw_to_normalized(raw_record, "linkedin")

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NOT_SUPPORTED,
            platform=self.platform,
            message="LinkedIn search not implemented: 待申请官方API权限",
        )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NOT_SUPPORTED,
            platform=self.platform,
            message="LinkedIn detail not implemented: 待接入",
        )

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NOT_SUPPORTED,
            platform=self.platform,
            message="LinkedIn comments not implemented: 待接入",
        )

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NOT_SUPPORTED,
            platform=self.platform,
            message="LinkedIn profile info not implemented: 待接入",
        )

    def health_check(self, **_: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NOT_CONFIGURED,
            platform=self.platform,
            message="LinkedIn adapter loaded (PLANNED): 官方API权限待申请",
        )


register_adapter("linkedin", LinkedInAdapter)
