# -*- coding: utf-8 -*-
"""GitHub Adapter 骨架（PLANNED，数据层+逻辑层，不进前端）。

GitHub REST API v3 可接入。按原生对象模型分 repositories/issues/pull_requests/releases 四表。
本骨架定义 schema + mapping + CRUD 接口。接入API Token后自动运行。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .platform_naming import map_raw_to_normalized
from .registry import register_adapter

logger = logging.getLogger(__name__)


class GitHubAdapter(BasePlatformAdapter):
    """GitHub主链路适配器骨架（PLANNED状态）。

    GitHub按原生对象模型设计，内容表为github_repositories，
    另有issues/pull_requests/releases三张对象表。
    """

    platform = "github"
    enabled = False
    monitor_priority = "planned"

    RAW_CONTENT_TABLE = "github_repositories"
    RAW_TABLES = ["github_repositories", "github_issues", "github_pull_requests", "github_releases"]

    def normalize_to_platform_contents(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return map_raw_to_normalized(raw_record, "github")

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="GitHub search not implemented: 待配置 REST API v3 Token",
        )

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="GitHub repository detail not implemented: 待接入",
        )

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        """GitHub的comments对应issues，非传统评论。"""
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="GitHub issues/comments not implemented: 待接入",
        )

    def list_issues(self, repo_full_name: str, **kwargs: Any) -> CollectionResult:
        """GitHub特有：获取仓库Issues列表。"""
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="GitHub issues list not implemented: 待接入",
        )

    def list_pull_requests(self, repo_full_name: str, **kwargs: Any) -> CollectionResult:
        """GitHub特有：获取仓库PR列表。"""
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="GitHub pull requests not implemented: 待接入",
        )

    def list_releases(self, repo_full_name: str, **kwargs: Any) -> CollectionResult:
        """GitHub特有：获取仓库Releases列表。"""
        return CollectionResult(
            status=CollectionStatus.COLLECT_ERROR,
            platform=self.platform,
            message="GitHub releases not implemented: 待接入",
        )

    def health_check(self, **_: Any) -> CollectionResult:
        return CollectionResult(
            status=CollectionStatus.NO_NEW_DATA,
            platform=self.platform,
            message="GitHub adapter loaded (PLANNED): REST API v3 Token待配置",
        )


register_adapter("github", GitHubAdapter)
