# -*- coding: utf-8 -*-
"""视频号 Channels Adapter 骨架（PLANNED，数据层+逻辑层，不进前端）。

视频号无公开API，可采集字段有限。不存在的公开字段标unavailable。
本骨架仅定义 schema + mapping + CRUD 接口，不实现真实采集逻辑。
接入采集端口后，只需实现 search/detail/comments 即可自动运行。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .platform_naming import map_raw_to_normalized, get_raw_table
from .registry import register_adapter

logger = logging.getLogger(__name__)


class ChannelsAdapter(BasePlatformAdapter):
    """视频号主链路适配器骨架（PLANNED状态）。"""

    platform = "channels"
    enabled = False  # 无公开API，默认关闭
    monitor_priority = "planned"

    # Raw 层表名
    RAW_CONTENT_TABLE = "channels_videos"
    RAW_COMMENT_TABLE = "channels_comments"

    def normalize_to_platform_contents(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """将视频号 Raw 记录映射为 platform_contents 统一字段。"""
        return map_raw_to_normalized(raw_record, "channels")

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="Channels search not implemented: 视频号无公开API，待接入采集端口",
        )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="Channels detail not implemented: 待接入",
        )

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="Channels comments not implemented: 待接入",
        )

    def health_check(self, **_: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NO_NEW_DATA,
            platform=self.platform,
            message="Channels adapter loaded (PLANNED): 无公开API，采集端口待接入",
        )


register_adapter("channels", ChannelsAdapter)
