# -*- coding: utf-8 -*-
"""YouTube Adapter 骨架（PLANNED，数据层+逻辑层，不进前端）。

YouTube Data API v3 可接入。本骨架定义 schema + mapping + CRUD 接口。
接入API Key后，实现 search/detail/comments 即可自动运行。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .platform_naming import map_raw_to_normalized
from .registry import register_adapter

logger = logging.getLogger(__name__)


class YouTubeAdapter(BasePlatformAdapter):
    """YouTube主链路适配器骨架（PLANNED状态）。"""

    platform = "youtube"
    enabled = False
    monitor_priority = "planned"

    RAW_CONTENT_TABLE = "youtube_videos"
    RAW_COMMENT_TABLE = "youtube_comments"
    RAW_USER_TABLE = "youtube_channels"

    def normalize_to_platform_contents(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return map_raw_to_normalized(raw_record, "youtube")

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="YouTube search not implemented: 待配置 Data API v3 Key",
        )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="YouTube detail not implemented: 待接入",
        )

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="YouTube comments not implemented: 待接入",
        )

    def creator(self, creator_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="YouTube channel info not implemented: 待接入",
        )

    def health_check(self, **_: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NO_NEW_DATA,
            platform=self.platform,
            message="YouTube adapter loaded (PLANNED): Data API v3待配置",
        )


register_adapter("youtube", YouTubeAdapter)
