# -*- coding: utf-8 -*-
"""Reddit Adapter 骨架（PLANNED，数据层+逻辑层，不进前端）。

Reddit 有公开 API。本骨架定义 schema + mapping + CRUD 接口。
接入API后自动运行。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .platform_naming import map_raw_to_normalized
from .registry import register_adapter

logger = logging.getLogger(__name__)


class RedditAdapter(BasePlatformAdapter):
    """Reddit主链路适配器骨架（PLANNED状态）。"""

    platform = "reddit"
    enabled = False
    monitor_priority = "planned"

    RAW_CONTENT_TABLE = "reddit_posts"
    RAW_COMMENT_TABLE = "reddit_comments"
    RAW_USER_TABLE = "reddit_subreddits"

    def normalize_to_platform_contents(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return map_raw_to_normalized(raw_record, "reddit")

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="Reddit search not implemented: 待接入公开API",
        )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="Reddit detail not implemented: 待接入",
        )

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="Reddit comments not implemented: 待接入",
        )

    def health_check(self, **_: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NO_NEW_DATA,
            platform=self.platform,
            message="Reddit adapter loaded (PLANNED): 公开API待接入",
        )


register_adapter("reddit", RedditAdapter)
