# -*- coding: utf-8 -*-
"""TikTok Adapter 骨架（PLANNED，数据层+逻辑层，不进前端）。

TikTok 国际版。本骨架定义 schema + mapping + CRUD 接口。
接入采集端口后自动运行。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .platform_naming import map_raw_to_normalized
from .registry import register_adapter

logger = logging.getLogger(__name__)


class TikTokAdapter(BasePlatformAdapter):
    """TikTok主链路适配器骨架（PLANNED状态）。"""

    platform = "tiktok"
    enabled = False
    monitor_priority = "planned"

    RAW_CONTENT_TABLE = "tiktok_videos"
    RAW_COMMENT_TABLE = "tiktok_comments"
    RAW_USER_TABLE = "tiktok_users"

    def normalize_to_platform_contents(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return map_raw_to_normalized(raw_record, "tiktok")

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="TikTok search not implemented: 待接入采集端口",
        )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="TikTok detail not implemented: 待接入",
        )

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="TikTok comments not implemented: 待接入",
        )

    def health_check(self, **_: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NO_NEW_DATA,
            platform=self.platform,
            message="TikTok adapter loaded (PLANNED): 采集端口待接入",
        )


register_adapter("tiktok", TikTokAdapter)
