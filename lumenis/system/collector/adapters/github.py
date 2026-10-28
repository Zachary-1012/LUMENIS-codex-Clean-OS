# -*- coding: utf-8 -*-
"""GitHub Adapter backed by the LUMENIS user-authorized connector.

The adapter is intentionally read-only and remains opt-in when the connector
is not configured.  Repository policy, credentials and transport stay inside
``github_connector``; CTH/BMP/Shared never depend on GitHub-specific fields.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict
from urllib.parse import urlsplit

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
    def _native_identity(item):
        native_id = str(item.get('id')) if type(item.get('id')) in (int, str) else ''
        url = item.get('html_url') if isinstance(item.get('html_url'), str) else ''
        parsed = urlsplit(url)
        path = parsed.path.strip('/') if parsed.scheme == 'https' and parsed.hostname == 'github.com' and not parsed.username and not parsed.password else ''
        matched = re.fullmatch(r'([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/(issues|pull)/([1-9][0-9]*)', path)
        if matched:
            kind = 'pull_request' if matched[2] == 'pull' else 'issue'
            return kind, f'{kind}:{matched[1]}:{matched[3]}', matched[1], native_id, url
        if isinstance(item.get('full_name'), str):
            return 'repository', native_id, item['full_name'], native_id, url
        if '/releases/' in path:
            return 'release', 'release:' + native_id, path.split('/releases/')[0], native_id, url
        return 'native_object', 'native_object:' + native_id if native_id else '', path, native_id, url

    @staticmethod
    def _map_item(item: Dict[str, Any]) -> Dict[str, Any]:
        from lumenis.adapters.base import optional_int
        owner = item.get("owner") if isinstance(item.get("owner"), dict) else {}
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        author = owner.get("login") or user.get("login")
        reactions = item.get("reactions") if isinstance(item.get("reactions"), dict) else {}
        kind, content_id, repo, native_id, original_url = GitHubAdapter._native_identity(item)
        return {
            "platform_content_id": content_id,
            "title": item.get("full_name") or item.get("name") or item.get("title"),
            "content": item.get("body") if isinstance(item.get("body"), str) else item.get("description"),
            "author_id": author,
            "author_nickname": author,
            "publish_datetime": item.get("published_at") or item.get("created_at"),
            "url": item.get("html_url") or item.get("url"),
            "likes": optional_int(reactions.get("+1")),
            "comments": optional_int(item.get("comments")),
            "collects": None,
            "shares": None,
            "captured_at": None,
            "raw": {**item, 'native_metrics': {name: optional_int(item.get(name)) for name in
                ('stargazers_count', 'forks_count', 'watchers_count', 'open_issues_count')},
                'native_content_id': content_id, 'native_object_kind': kind, 'native_object_id': native_id,
                'native_source_url': original_url, 'repo_full_name': repo,
                **({'repo_id': native_id} if kind == 'repository' else
                   {'repo_id': str(item['repository']['id'])} if isinstance(item.get('repository'), dict) and item['repository'].get('id') is not None else {}),
                'metric_semantics': 'STARS_FORKS_WATCHERS_OPEN_ISSUES_ARE_DISTINCT_FROM_LIKES_COLLECTS_SHARES_COMMENTS'},
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
            raw_count=None,
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
        if page.coverage_complete or page.error_code is None:
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
            'pagination': {'request_cursor': None, 'next_cursor': page.next_cursor,
                'exhausted': True if page.coverage_complete else False if page.next_cursor and not page.error_code else None,
                'page_complete': page.error_code is None, 'coverage_scope': page.coverage_scope,
                'partial_reason': page.partial_reason, 'reported_total': page.reported_total_count},
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
            items=[] if comments else mapped,
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
                max_pages=kwargs.get("max_pages", 1),
                cursor=kwargs.get("cursor"),
                cancel_check=kwargs.get("cancel_check"),
            )
            result = self._page_result(page, "search")
            result.metadata['pagination']['request_cursor'] = kwargs.get('cursor')
            return result
        except GitHubConnectorError as exc:
            return self._error(exc, "search")

    def detail(self, content_id: str, **kwargs: Any) -> CollectionResult:
        try:
            target = self._resource(content_id, kwargs.get('source_url'))
            item = self.connector.repository(target[0]) if target[1] is None else self.connector.get_json('/repos/' + target[0] + '/' + target[1] + '/' + target[2])
            if not isinstance(item, dict) or not item.get('id'):
                raise GitHubConnectorError('INVALID_PROVIDER_RESPONSE', 'GitHub resource identity was not observed')
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
        """Actual issue/PR discussion comments, never issues relabelled as comments."""
        try:
            repo, kind, number = self._resource(content_id, kwargs.get('source_url'))
            if kind not in {'issues', 'pulls'}:
                return CollectionResult(CollectionStatus.NOT_SUPPORTED, self.platform,
                    message='仓库不是评论主题；请选择原Issue或PR内容', metadata={'reason': 'EXACT_ISSUE_OR_PULL_SOURCE_REQUIRED'})
            native_parent = self.connector.get_json(f'/repos/{repo}/{kind}/{number}')
            if not isinstance(native_parent, dict) or not native_parent.get('id'):
                raise GitHubConnectorError('INVALID_PROVIDER_RESPONSE', 'GitHub parent resource identity was not observed')
            parent_item = {**native_parent, 'html_url': f'https://github.com/{repo}/' + ('pull' if kind == 'pulls' else 'issues') + '/' + number}
            parent_source_id = self._native_identity(parent_item)[1]
            review = kwargs.get('comment_kind') == 'review' and kind == 'pulls'
            suffix = f'pulls/{number}/comments' if review else f'issues/{number}/comments'
            page = self.connector.repository_collection_page_result(repo, suffix,
                limit=kwargs.get('max_comments', 20), max_pages=kwargs.get('max_pages', 1), cursor=kwargs.get('cursor'), cancel_check=kwargs.get('cancel_check'))
            result = self._page_result(page, 'comments')
            from lumenis.adapters.base import optional_int
            comments = []
            for item in page.items:
                if not item.get('id') or not isinstance(item.get('body'), str): continue
                user = item.get('user') or {}; parent = item.get('in_reply_to_id')
                comment_kind = 'pull_review_comment' if review else 'issue_comment'
                comment_id = comment_kind + ':' + str(item['id'])
                comments.append({'platform_comment_id': comment_id, 'parent_content_id': parent_source_id,
                    'parent_comment_id': comment_kind + ':' + str(parent) if parent is not None else None,
                    'reply_to_comment_id': comment_kind + ':' + str(parent) if parent is not None else None,
                    'content': item['body'], 'author_id': user.get('login') or '', 'author_nickname': user.get('login') or '',
                    'publish_datetime': item.get('created_at') or '', 'likes': optional_int((item.get('reactions') or {}).get('+1')),
                    'url': item.get('html_url') or '', 'raw': {**item, 'native_object_id': str(item['id']), 'native_object_kind': comment_kind,
                        'native_parent_id': str(native_parent['id']), 'native_parent_resource': f'{repo}/{kind}/{number}',
                        'comment_kind': 'PULL_REVIEW_COMMENT' if review else 'ISSUE_CONVERSATION_COMMENT',
                        'native_author_aliases': [{'kind': 'id', 'value': str(user['id'])}] if user.get('id') else []}})
            result.items, result.comments, result.new_count = [], comments, len(comments)
            result.metadata.update(comment_semantics='PULL_REVIEW_THREADS' if review else 'ISSUE_OR_PULL_CONVERSATION',
                native_parent_id=str(native_parent['id']), parent_source_id=parent_source_id,
                native_parent_resource=f'{repo}/{kind}/{number}', include_replies_requested=include_replies)
            result.metadata['pagination']['request_cursor'] = kwargs.get('cursor')
            return result
        except GitHubConnectorError as exc:
            return self._error(exc, 'comments')

    @staticmethod
    def _resource(value, source_url=None):
        typed = re.fullmatch(r'(issue|pull_request):([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+):([1-9][0-9]*)', str(value or ''))
        if typed and source_url is None:
            return typed[2], 'issues' if typed[1] == 'issue' else 'pulls', typed[3]
        target = source_url or value
        if isinstance(target, str) and target.startswith('https://'):
            parsed = urlsplit(target)
            if parsed.hostname != 'github.com' or parsed.username or parsed.password or parsed.port not in (None, 443):
                raise GitHubConnectorError('INVALID_REPOSITORY', 'GitHub source URL is invalid')
            target = parsed.path.strip('/')
        match = re.fullmatch(r'([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:/(issues|pull|pulls)/([1-9][0-9]*))?', str(target or '').strip('/'))
        if not match: raise GitHubConnectorError('INVALID_REPOSITORY', 'GitHub requires the original repository/issue/PR resource')
        if typed and (match[1] != typed[2] or match[3] != typed[3]
                or ('pulls' if match[2] in {'pull', 'pulls'} else match[2]) != ('issues' if typed[1] == 'issue' else 'pulls')):
            raise GitHubConnectorError('INVALID_REPOSITORY', 'GitHub typed source and original URL disagree')
        return match[1], 'pulls' if match[2] in {'pull', 'pulls'} else match[2], match[3]

    def list_issues(self, repo_full_name: str, **kwargs: Any) -> CollectionResult:
        """GitHub特有：获取仓库Issues列表。"""
        return self._collection(repo_full_name, "issues", "issues", **kwargs)

    def list_pull_requests(self, repo_full_name: str, **kwargs: Any) -> CollectionResult:
        """GitHub特有：获取仓库PR列表。"""
        return self._collection(repo_full_name, "pulls", "pull_requests", **kwargs)

    def list_releases(self, repo_full_name: str, **kwargs: Any) -> CollectionResult:
        """GitHub特有：获取仓库Releases列表。"""
        return self._collection(repo_full_name, "releases", "releases", **kwargs)

    def _collection(self, repo_full_name: str, suffix: str, capability: str, **kwargs: Any) -> CollectionResult:
        try:
            page = self.connector.repository_collection_page_result(
                repo_full_name,
                suffix,
                limit=kwargs.get("max_results", 20),
                max_pages=kwargs.get("max_pages", 1),
                cursor=kwargs.get("cursor"),
                cancel_check=kwargs.get("cancel_check"),
            )
            result = self._page_result(page, capability, comments=capability == "comments")
            result.metadata['pagination']['request_cursor'] = kwargs.get('cursor')
            return result
        except GitHubConnectorError as exc:
            return self._error(exc, capability)

    def health_check(self, *, verify_remote: bool = False, **_: Any) -> CollectionResult:
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
        if verify_remote is not True:
            return CollectionResult(CollectionStatus.NEED_VERIFY, self.platform,
                message='GitHub授权配置已存在；仅明确用户验证动作才检查远端会话',
                metadata={**snapshot, 'healthcheck_scope': 'CONFIGURATION_ONLY', 'remote_verification': 'NOT_RUN',
                          'authorization_verification': 'NOT_VERIFIED', 'repository_access_verification': 'NOT_VERIFIED'})
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
