# -*- coding: utf-8 -*-
"""GitHub Adapter backed by the LUMENIS user-authorized connector.

The adapter is intentionally read-only and remains opt-in when the connector
is not configured.  Repository policy, credentials and transport stay inside
``github_connector``; CTH/BMP/Shared never depend on GitHub-specific fields.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .base import BasePlatformAdapter, CollectionResult, CollectionStatus
from .platform_naming import map_raw_to_normalized
from .registry import register_adapter
from github_connector import GitHubCollectionPage, GitHubConnector, GitHubConnectorError

logger = logging.getLogger(__name__)


class GitHubAdapter(BasePlatformAdapter):
    """GitHub read adapter; it never grants permissions or writes to GitHub."""

    platform = "github"
    enabled = False
    monitor_priority = "optional"

    RAW_CONTENT_TABLE = "github_repositories"
    RAW_TABLES = ["github_repositories", "github_issues", "github_pull_requests", "github_releases"]

    def __init__(self, *, connector: GitHubConnector | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.connector = connector or GitHubConnector()

    @staticmethod
    def _map_item(item: Dict[str, Any]) -> Dict[str, Any]:
        owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        author = owner.get("login") or user.get("login")
        reactions = item.get("reactions") if isinstance(item.get("reactions"), dict) else {}
        return {
            "platform_content_id": str(item.get("id") or item.get("full_name") or item.get("number") or ""),
            "title": item.get("full_name") or item.get("name") or item.get("title"),
            "content": item.get("description") or item.get("body"),
            "author_id": author,
            "author_nickname": author,
            "publish_datetime": item.get("created_at") or item.get("published_at"),
            "url": item.get("html_url") or item.get("url"),
            "likes": item.get("stargazers_count") or reactions.get("total_count"),
            "comments": item.get("open_issues_count") or item.get("comments"),
            "collects": item.get("forks_count") or item.get("forks"),
            "shares": item.get("watchers_count") or item.get("watchers"),
            "captured_at": None,
            "raw": item,
        }

    @staticmethod
    def _error(exc: GitHubConnectorError, capability: str) -> CollectionResult:
        status_map = {
            "NOT_CONNECTED": CollectionStatus.NOT_CONFIGURED,
            "NOT_CONFIGURED": CollectionStatus.NOT_CONFIGURED,
            "REPOSITORY_NOT_ALLOWLISTED": CollectionStatus.BLOCKED,
            "ENDPOINT_NOT_ALLOWLISTED": CollectionStatus.BLOCKED,
            "API_ORIGIN_NOT_ALLOWLISTED": CollectionStatus.BLOCKED,
            "REDIRECT_BLOCKED": CollectionStatus.BLOCKED,
            "AUTHENTICATION_FAILED": CollectionStatus.SESSION_EXPIRED,
            "AUTHENTICATION_OR_PERMISSION_FAILED": CollectionStatus.SESSION_EXPIRED,
            "PERMISSION_DENIED": CollectionStatus.BLOCKED,
            "RATE_LIMITED": CollectionStatus.COOLING_DOWN,
            "PROVIDER_UNAVAILABLE": CollectionStatus.PROVIDER_UNAVAILABLE,
        }
        metadata = {
            "provider": "github_app_user_authorization",
            "capability": capability,
            "error_code": exc.code,
            "write_enabled": False,
        }
        if exc.retry_after_seconds is not None:
            metadata["retry_after_seconds"] = exc.retry_after_seconds
        return CollectionResult(
            status=status_map.get(exc.code, CollectionStatus.COLLECT_ERROR),
            platform="github",
            message=str(exc),
            metadata=metadata,
        )

    @staticmethod
    def _page_result(
        page: GitHubCollectionPage,
        capability: str,
        *,
        comments: bool = False,
    ) -> CollectionResult:
        mapped = [GitHubAdapter._map_item(item) for item in page.items]
        if page.coverage_complete:
            status = CollectionStatus.SUCCESS if mapped else CollectionStatus.NO_NEW_DATA
        else:
            status = {
                "AUTHENTICATION_FAILED": CollectionStatus.SESSION_EXPIRED,
                "PERMISSION_DENIED": CollectionStatus.BLOCKED,
                "REPOSITORY_NOT_ALLOWLISTED": CollectionStatus.BLOCKED,
                "ENDPOINT_NOT_ALLOWLISTED": CollectionStatus.BLOCKED,
                "API_ORIGIN_NOT_ALLOWLISTED": CollectionStatus.BLOCKED,
                "REDIRECT_BLOCKED": CollectionStatus.BLOCKED,
                "RATE_LIMITED": CollectionStatus.COOLING_DOWN,
                "PROVIDER_UNAVAILABLE": CollectionStatus.PROVIDER_UNAVAILABLE,
            }.get(page.error_code, CollectionStatus.COLLECT_ERROR)
        metadata = {
            "provider": "github_app_user_authorization",
            "capability": capability,
            "write_enabled": False,
            "coverage_complete": page.coverage_complete,
            "coverage_scope": page.coverage_scope,
            "start_page": page.start_page,
            "pages_fetched": page.pages_fetched,
            "api_items_observed": page.api_items_observed,
            "reported_total_count": page.reported_total_count,
            "next_cursor": page.next_cursor,
            "partial_reason": page.partial_reason,
        }
        if page.error_code:
            metadata["error_code"] = page.error_code
        if page.retry_after_seconds is not None:
            metadata["retry_after_seconds"] = page.retry_after_seconds
        message = ""
        if not page.coverage_complete:
            message = f"GitHub returned partial results ({page.partial_reason or page.error_code or 'incomplete coverage'})"
        return CollectionResult(
            status=status,
            platform="github",
            items=mapped,
            comments=mapped if comments else [],
            message=message,
            raw_count=page.api_items_observed,
            new_count=len(mapped),
            metadata=metadata,
        )

    def normalize_to_platform_contents(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        return map_raw_to_normalized(raw_record, "github")

    def search(self, keyword: str, **kwargs: Any) -> CollectionResult:
        try:
            page = self.connector.search_repositories_page_result(
                keyword,
                limit=kwargs.get("max_results", 20),
                max_pages=kwargs.get("max_pages", 5),
                cursor=kwargs.get("cursor"),
                cancel_check=kwargs.get("cancel_check"),
            )
            return self._page_result(page, "search")
        except GitHubConnectorError as exc:
            return self._error(exc, "search")

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        try:
            item = self.connector.repository(content_id)
            mapped = self._map_item(item)
            return CollectionResult(
                status=CollectionStatus.SUCCESS,
                platform=self.platform,
                items=[mapped],
                raw_count=1,
                new_count=1,
                metadata={"provider": "github_app_user_authorization", "write_enabled": False},
            )
        except GitHubConnectorError as exc:
            return self._error(exc, "detail")

    def comments(self, content_id: str, *, include_replies: bool = False, **kwargs: Any) -> CollectionResult:
        """GitHub的comments对应issues，非传统评论。"""
        return self._collection(content_id, "issues", "comments", **kwargs)

    def list_issues(self, repo_full_name: str, **kwargs: Any) -> CollectionResult:
        """GitHub特有：获取仓库Issues列表。"""
        return self._collection(repo_full_name, "issues", "issues", **kwargs)

    def list_pull_requests(self, repo_full_name: str, **kwargs: Any) -> CollectionResult:
        """GitHub特有：获取仓库PR列表。"""
        return self._collection(repo_full_name, "pulls", "author_posts", **kwargs)

    def list_releases(self, repo_full_name: str, **kwargs: Any) -> CollectionResult:
        """GitHub特有：获取仓库Releases列表。"""
        return self._collection(repo_full_name, "releases", "releases", **kwargs)

    def _collection(self, repo_full_name: str, suffix: str, capability: str, **kwargs: Any) -> CollectionResult:
        try:
            page = self.connector.repository_collection_page_result(
                repo_full_name,
                suffix,
                limit=kwargs.get("max_results", 250),
                max_pages=kwargs.get("max_pages", 5),
                cursor=kwargs.get("cursor"),
                cancel_check=kwargs.get("cancel_check"),
            )
            return self._page_result(page, capability, comments=capability == "comments")
        except GitHubConnectorError as exc:
            return self._error(exc, capability)

    def health_check(self, **_: Any) -> CollectionResult:
        snapshot = self.connector.status()
        if not snapshot.get("token_available"):
            status = (CollectionStatus.NOT_CONFIGURED if snapshot["state"] == "NOT_CONFIGURED"
                      else CollectionStatus.PROVIDER_UNAVAILABLE if snapshot["state"] == "PROVIDER_UNAVAILABLE"
                      else CollectionStatus.NEED_VERIFY)
            return CollectionResult(
                status=status,
                platform=self.platform,
                message=f"GitHub connector state: {snapshot['state']}",
                metadata=snapshot,
            )
        try:
            user = self.connector.get_json("/user")
            if (not isinstance(user, dict) or not isinstance(user.get("login"), str)
                    or not user["login"].strip()):
                raise GitHubConnectorError("INVALID_PROVIDER_RESPONSE", "GitHub user payload is invalid")
            return CollectionResult(
                status=CollectionStatus.SUCCESS,
                platform=self.platform,
                message="GitHub user authorization verified",
                metadata={**snapshot, "state": "CONNECTED",
                          "authorization_verification": "CURRENT_USER_VERIFIED",
                          "repository_access_verification": "NOT_VERIFIED",
                          "code": None,
                          "login": user["login"]},
            )
        except GitHubConnectorError as exc:
            return self._error(exc, "healthcheck")


register_adapter("github", GitHubAdapter)
