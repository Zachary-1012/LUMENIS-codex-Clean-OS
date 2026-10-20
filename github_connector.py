# -*- coding: utf-8 -*-
"""LUMENIS GitHub connector boundary.

This is a user-authorized, repository-allowlisted, read-only connector.  It is
deliberately separate from the Skill registry and from the platform Adapter:

    User authorization / GitHub App installation
        -> external secret provider
        -> repository policy
        -> GitHub REST API
        -> platform_adapters.github

The module never stores, prints, or returns token material.  It does not fall
back to a personal access token, browser cookies, or an unbounded URL fetch.
Without an external credential provider and an explicit repository allowlist,
requests fail closed with a truthful status.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Dict, Iterable, Optional


GITHUB_API_BASE = "https://api.github.com"
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_PATH_RE = re.compile(r"^/repos/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/|$)")
_STATE_RE = re.compile(r"^[A-Za-z0-9._~-]{16,256}$")
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_PAGE_SIZE = 50
_DEFAULT_PAGE_BUDGET = 5
_MAX_PAGE_BUDGET = 20
_MAX_AUTO_RATE_LIMIT_WAIT_SECONDS = 3.0


class GitHubConnectorError(RuntimeError):
    """A safe, non-secret connector failure with a stable code."""

    def __init__(self, code: str, message: str, *, retry_after_seconds: Optional[float] = None):
        super().__init__(message)
        self.code = code
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class GitHubCollectionPage:
    """Bounded page collection facts; a cursor is only a source-page resume hint."""

    items: list[Dict[str, Any]] = field(default_factory=list)
    start_page: int = 1
    pages_fetched: int = 0
    api_items_observed: int = 0
    reported_total_count: Optional[int] = None
    coverage_complete: bool = False
    coverage_scope: str = "FULL_QUERY"
    next_cursor: Optional[Dict[str, Any]] = None
    partial_reason: Optional[str] = None
    error_code: Optional[str] = None
    retry_after_seconds: Optional[float] = None


@dataclass(frozen=True)
class GitHubConnectorConfig:
    """Non-secret connector configuration.

    GitHub App permissions are intentionally read-only.  Repository selection
    is an explicit allowlist rather than an implicit account-wide grant.
    """

    client_id: str = ""
    redirect_uri: str = ""
    repositories: tuple[str, ...] = ()
    api_base: str = GITHUB_API_BASE

    @classmethod
    def from_environment(cls) -> "GitHubConnectorConfig":
        raw_repositories = os.environ.get("LUMENIS_GITHUB_REPOSITORIES", "")
        repositories = tuple(
            item.strip().lower()
            for item in re.split(r"[,;\n]", raw_repositories)
            if item.strip() and _REPO_RE.match(item.strip())
        )
        api_base = os.environ.get("LUMENIS_GITHUB_API_BASE", GITHUB_API_BASE).strip().rstrip("/")
        if api_base != GITHUB_API_BASE:
            # A test/local proxy may be injected by code, but production
            # configuration cannot silently redirect GitHub credentials.
            api_base = GITHUB_API_BASE
        return cls(
            client_id=os.environ.get("LUMENIS_GITHUB_APP_CLIENT_ID", "").strip(),
            redirect_uri=os.environ.get("LUMENIS_GITHUB_APP_REDIRECT_URI", "").strip(),
            repositories=repositories,
            api_base=api_base,
        )

    def snapshot(self, *, token_available: bool) -> Dict[str, Any]:
        if token_available:
            # Presence is configuration, never proof of live authorization.
            state = "PROVIDER_UNAVAILABLE"
        elif self.client_id and self.redirect_uri:
            state = "READY_FOR_AUTHORIZATION"
        else:
            state = "NOT_CONFIGURED"
        return {
            "provider": "github",
            "state": state,
            "authorization_model": "github_app_user_to_server",
            "repository_selection": "explicit_allowlist",
            "repositories": list(self.repositories),
            "requested_permissions": {
                "metadata": "read",
                "contents": "read",
            },
            "write_enabled": False,
            "write_policy": "human_approval_required_and_disabled_by_default",
            "secret_material_exposed": False,
            "token_available": bool(token_available),
            "authorization_verification": "NOT_VERIFIED",
            "code": "HEALTH_CHECK_REQUIRED" if token_available else "AUTHORIZATION_REQUIRED",
            "authorization_ready": bool(self.client_id and self.redirect_uri),
        }


def _environment_token() -> str:
    """Read a process-injected secret without exposing it to callers/logs."""
    return os.environ.get("LUMENIS_GITHUB_ACCESS_TOKEN", "").strip()


class _GitHubRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject a redirect before urllib can resend the bearer token."""

    def __init__(self, connector: "GitHubConnector") -> None:
        super().__init__()
        self.connector = connector

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        self.connector._assert_api_url_allowed(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


class GitHubConnector:
    """Small REST client behind a strict GitHub connector policy."""

    def __init__(
        self,
        *,
        config: Optional[GitHubConnectorConfig] = None,
        token_provider: Optional[Callable[[], str]] = None,
        opener: Optional[Callable[..., Any]] = None,
        sleep: Optional[Callable[[float], None]] = None,
    ) -> None:
        self.config = config or GitHubConnectorConfig.from_environment()
        self._token_provider = token_provider or _environment_token
        self._opener = opener or urllib.request.build_opener(
            _GitHubRedirectHandler(self),
        ).open
        self._sleep = sleep or time.sleep

    def status(self) -> Dict[str, Any]:
        try:
            token_available = bool(self._token_provider())
        except Exception:
            return {**self.config.snapshot(token_available=False),
                    "state": "PROVIDER_UNAVAILABLE", "code": "CREDENTIAL_PROVIDER_ERROR"}
        return self.config.snapshot(token_available=token_available)

    def authorization_url(self, state: str) -> str:
        """Build an OAuth request only after the caller supplies a CSRF state.

        State generation/storage and callback exchange belong to the host
        account/session layer.  This helper never accepts or embeds a secret.
        """
        if not self.config.client_id or not self.config.redirect_uri:
            raise GitHubConnectorError("NOT_CONFIGURED", "GitHub App authorization is not configured")
        if not _STATE_RE.match(str(state or "")):
            raise GitHubConnectorError("INVALID_OAUTH_STATE", "authorization state must be a high-entropy nonce")
        query = urllib.parse.urlencode({
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "state": state,
            "allow_signup": "false",
        })
        return f"https://github.com/login/oauth/authorize?{query}"

    def _token(self) -> str:
        try:
            token = str(self._token_provider() or "").strip()
        except Exception as exc:
            raise GitHubConnectorError("CREDENTIAL_PROVIDER_ERROR", "GitHub credential provider unavailable") from exc
        if not token:
            raise GitHubConnectorError("NOT_CONNECTED", "GitHub user authorization is not connected")
        return token

    def _assert_path_allowed(self, path: str) -> None:
        if path == "/user" or path == "/search/repositories":
            return
        match = _PATH_RE.match(path)
        if not match:
            raise GitHubConnectorError("ENDPOINT_NOT_ALLOWLISTED", "GitHub endpoint is not allowlisted")
        repo = f"{match.group(1)}/{match.group(2)}".lower()
        if repo not in set(self.config.repositories):
            raise GitHubConnectorError("REPOSITORY_NOT_ALLOWLISTED", "repository is not in the connector allowlist")

    def _assert_api_url_allowed(self, url: str) -> None:
        if self.config.api_base != GITHUB_API_BASE:
            raise GitHubConnectorError(
                "API_ORIGIN_NOT_ALLOWLISTED", "GitHub API origin is not allowlisted",
            )
        try:
            target = urllib.parse.urlsplit(url)
            api = urllib.parse.urlsplit(self.config.api_base)
            target_port = target.port
        except ValueError as exc:
            raise GitHubConnectorError("REDIRECT_BLOCKED", "GitHub redirect URL is invalid") from exc
        if (target.scheme != "https" or target.hostname != api.hostname
                or target_port not in (None, 443) or target.username is not None
                or target.password is not None or target.fragment):
            raise GitHubConnectorError("REDIRECT_BLOCKED", "GitHub redirect left the approved API origin")
        self._assert_path_allowed(target.path)

    @staticmethod
    def _header(headers: Any, name: str) -> Optional[str]:
        if headers is None:
            return None
        try:
            value = headers.get(name)
        except AttributeError:
            return None
        return str(value).strip() if value is not None else None

    @staticmethod
    def _retry_after_seconds(headers: Any) -> Optional[float]:
        retry_after = GitHubConnector._header(headers, "Retry-After")
        if retry_after:
            try:
                seconds = float(retry_after)
                return max(0.0, seconds) if math.isfinite(seconds) else None
            except (TypeError, ValueError, OverflowError):
                try:
                    retry_time = parsedate_to_datetime(retry_after)
                    if retry_time.tzinfo is None:
                        retry_time = retry_time.replace(tzinfo=timezone.utc)
                    return max(0.0, (retry_time - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError, OverflowError):
                    pass
        remaining = GitHubConnector._header(headers, "X-RateLimit-Remaining")
        reset = GitHubConnector._header(headers, "X-RateLimit-Reset")
        if remaining == "0" and reset:
            try:
                reset_at = float(reset)
                return max(0.0, reset_at - time.time()) if math.isfinite(reset_at) else None
            except (TypeError, ValueError, OverflowError):
                return None
        return None

    @staticmethod
    def _error_body(exc: urllib.error.HTTPError) -> str:
        try:
            raw = exc.read(64 * 1024)
            parsed = json.loads(raw.decode("utf-8"))
            message = parsed.get("message") if isinstance(parsed, dict) else None
            return message.lower() if isinstance(message, str) else ""
        except Exception:
            return ""

    def _request_json(self, url: str) -> tuple[Any, Any]:
        self._assert_api_url_allowed(url)
        token = self._token()
        request = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {token}",
            "User-Agent": "LUMENIS-GitHub-Connector/1.0",
        }, method="GET")
        for attempt in range(2):
            try:
                with self._opener(request, timeout=15) as response:
                    payload = response.read(_MAX_RESPONSE_BYTES + 1)
                    if len(payload) > _MAX_RESPONSE_BYTES:
                        raise GitHubConnectorError(
                            "INVALID_PROVIDER_RESPONSE", "GitHub API response exceeded the size limit",
                        )
                    headers = getattr(response, "headers", None)
                    if headers is None and callable(getattr(response, "getheader", None)):
                        headers = {"Link": response.getheader("Link")}
                try:
                    return json.loads(payload.decode("utf-8")), headers
                except (UnicodeError, json.JSONDecodeError) as exc:
                    raise GitHubConnectorError(
                        "INVALID_PROVIDER_RESPONSE", "GitHub API returned invalid JSON",
                    ) from exc
            except urllib.error.HTTPError as exc:
                headers = getattr(exc, "headers", None)
                retry_after = self._retry_after_seconds(headers)
                body_message = self._error_body(exc)
                rate_limited = (
                    exc.code == 429
                    or (exc.code == 403 and (
                        retry_after is not None
                        or self._header(headers, "X-RateLimit-Remaining") == "0"
                        or any(marker in body_message for marker in (
                            "rate limit", "secondary rate", "abuse detection",
                        ))
                    ))
                )
                if rate_limited:
                    if (attempt == 0 and retry_after is not None
                            and retry_after <= _MAX_AUTO_RATE_LIMIT_WAIT_SECONDS):
                        self._sleep(retry_after)
                        continue
                    raise GitHubConnectorError(
                        "RATE_LIMITED", "GitHub rate limit reached",
                        retry_after_seconds=retry_after,
                    ) from exc
                if exc.code == 401:
                    raise GitHubConnectorError("AUTHENTICATION_FAILED", "GitHub authorization is invalid or expired") from exc
                if exc.code == 403:
                    raise GitHubConnectorError("PERMISSION_DENIED", "GitHub denied access to the requested resource") from exc
                if exc.code == 404:
                    raise GitHubConnectorError("NOT_FOUND", "GitHub resource was not found or is not visible") from exc
                raise GitHubConnectorError("PROVIDER_UNAVAILABLE", "GitHub API returned an unavailable response") from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                raise GitHubConnectorError("PROVIDER_UNAVAILABLE", "GitHub API is unavailable") from exc
        raise GitHubConnectorError("RATE_LIMITED", "GitHub rate limit remains active")

    def get_json(self, path: str, *, query: Optional[Dict[str, Any]] = None) -> Any:
        if not path.startswith("/") or "?" in path or "#" in path:
            raise GitHubConnectorError("INVALID_ENDPOINT", "GitHub endpoint must be a relative path")
        self._assert_path_allowed(path)
        url = f"{self.config.api_base}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"
        payload, _headers = self._request_json(url)
        return payload

    @staticmethod
    def _next_link(headers: Any) -> Optional[str]:
        link_header = GitHubConnector._header(headers, "Link")
        if not link_header:
            return None
        for entry in link_header.split(","):
            match = re.match(r"\s*<([^>]+)>\s*;(.*)$", entry)
            if not match:
                if re.search(r'(?:^|;)\s*rel\s*=\s*"?next\b', entry):
                    raise GitHubConnectorError(
                        "INVALID_PAGINATION_LINK", "GitHub pagination link is malformed",
                    )
                continue
            attrs = match.group(2)
            rel_match = re.search(
                r'(?:^|;)\s*rel\s*=\s*(?:"([^"]+)"|([^;\s]+))(?:\s*;|$)', attrs,
            )
            if rel_match:
                relation_values = rel_match.group(1) or rel_match.group(2)
                if "next" in relation_values.split():
                    return match.group(1)
            elif re.search(r'(?:^|;)\s*rel\s*=\s*"?next\b', attrs):
                raise GitHubConnectorError(
                    "INVALID_PAGINATION_LINK", "GitHub pagination relation is malformed",
                )
        return None

    @staticmethod
    def _query_map(query: Dict[str, Any]) -> Dict[str, list[str]]:
        encoded = urllib.parse.urlencode(query, doseq=True)
        return urllib.parse.parse_qs(encoded, keep_blank_values=True)

    def _next_page_number(
        self,
        next_url: str,
        *,
        path: str,
        query: Dict[str, Any],
        current_page: int,
    ) -> int:
        self._assert_api_url_allowed(next_url)
        parsed = urllib.parse.urlsplit(next_url)
        if parsed.path != path:
            raise GitHubConnectorError("INVALID_PAGINATION_LINK", "GitHub pagination changed the approved endpoint")
        next_query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        try:
            page_values = next_query.pop("page")
            if len(page_values) != 1 or not re.fullmatch(r"[0-9]+", page_values[0]):
                raise ValueError("page must be a single decimal value")
            next_page = int(page_values[0])
        except (KeyError, IndexError, TypeError, ValueError, OverflowError) as exc:
            raise GitHubConnectorError("INVALID_PAGINATION_LINK", "GitHub pagination page is invalid") from exc
        expected = self._query_map(query)
        expected.pop("page", None)
        if next_query != expected or next_page != current_page + 1:
            raise GitHubConnectorError("INVALID_PAGINATION_LINK", "GitHub pagination changed the approved query")
        return next_page

    @staticmethod
    def _cursor(fingerprint: str, page: int, offset: int = 0) -> Dict[str, Any]:
        cursor = {"version": 1, "request_fingerprint": fingerprint, "page": page}
        if offset:
            cursor["offset"] = offset
        return cursor

    def _collect_pages(
        self,
        path: str,
        query: Dict[str, Any],
        *,
        limit: int,
        max_pages: int = _DEFAULT_PAGE_BUDGET,
        cursor: Optional[Dict[str, Any]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        filter_to_allowlist: bool = False,
    ) -> GitHubCollectionPage:
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise GitHubConnectorError("INVALID_PAGINATION_LIMIT", "GitHub result limit must be between 1 and 1000")
        if type(max_pages) is not int or not 1 <= max_pages <= _MAX_PAGE_BUDGET:
            raise GitHubConnectorError("INVALID_PAGE_BUDGET", "GitHub page budget must be between 1 and 20")
        if cancel_check is not None and not callable(cancel_check):
            raise GitHubConnectorError("INVALID_CANCELLATION_CHECK", "GitHub cancellation check is invalid")
        page_size = min(_PAGE_SIZE, limit)
        base_query = dict(query)
        base_query["per_page"] = page_size
        binding = {
            "path": path,
            "query": self._query_map(base_query),
            "limit": limit,
            "repositories": sorted(self.config.repositories),
            "filter_to_allowlist": filter_to_allowlist,
        }
        fingerprint = hashlib.sha256(
            json.dumps(binding, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        page = 1
        offset = 0
        if cursor is not None:
            base_cursor_fields = {"version", "request_fingerprint", "page"}
            if (not isinstance(cursor, dict)
                    or not base_cursor_fields <= set(cursor)
                    or set(cursor) - base_cursor_fields - {"offset"}
                    or cursor.get("version") != 1
                    or cursor.get("request_fingerprint") != fingerprint
                    or type(cursor.get("page")) is not int
                    or cursor["page"] < 1):
                raise GitHubConnectorError("INVALID_CURSOR", "GitHub continuation does not match this query and allowlist")
            page = cursor["page"]
            offset = cursor.get("offset", 0)
            if type(offset) is not int or not 0 <= offset < page_size:
                raise GitHubConnectorError("INVALID_CURSOR", "GitHub continuation offset is invalid")
        start_page = page
        start_offset = offset

        items: list[Dict[str, Any]] = []
        pages_fetched = 0
        api_items_observed = 0
        reported_total_count = None
        provider_total_valid = True
        provider_total_changed = False
        incomplete_results = False
        invalid_page_item = False
        next_page = page
        next_offset = offset
        partial_reason = None
        error_code = None
        retry_after_seconds = None
        pagination_exhausted = False

        while pages_fetched < max_pages and len(items) < limit:
            if cancel_check is not None:
                try:
                    cancellation_signal = cancel_check()
                except Exception:
                    error_code = "CANCELLATION_CHECK_FAILED"
                    partial_reason = "CANCELLATION_CHECK_FAILED"
                    break
                if cancellation_signal is True:
                    partial_reason = "CANCELLED"
                    break
                if cancellation_signal is not False:
                    error_code = "INVALID_CANCELLATION_SIGNAL"
                    partial_reason = "INVALID_CANCELLATION_SIGNAL"
                    break
            page_query = {**base_query, "page": next_page}
            current_page = next_page
            current_offset = next_offset
            url = f"{self.config.api_base}{path}?{urllib.parse.urlencode(page_query, doseq=True)}"
            try:
                raw, headers = self._request_json(url)
            except GitHubConnectorError as exc:
                if pages_fetched == 0:
                    raise
                error_code = exc.code
                retry_after_seconds = exc.retry_after_seconds
                partial_reason = "PAGE_REQUEST_FAILED"
                break

            if path == "/search/repositories":
                if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
                    if pages_fetched == 0:
                        raise GitHubConnectorError("INVALID_PROVIDER_RESPONSE", "GitHub repository search payload is invalid")
                    error_code = "INVALID_PROVIDER_RESPONSE"
                    partial_reason = "INVALID_PAGE_RESPONSE"
                    break
                page_items = raw["items"]
                total = raw.get("total_count")
                if type(total) is int and total >= 0:
                    if (reported_total_count is not None
                            and total != reported_total_count):
                        provider_total_changed = True
                    reported_total_count = total
                else:
                    provider_total_valid = False
                incomplete_results = incomplete_results or raw.get("incomplete_results") is True
            else:
                if not isinstance(raw, list):
                    if pages_fetched == 0:
                        raise GitHubConnectorError("INVALID_PROVIDER_RESPONSE", "GitHub collection payload is invalid")
                    error_code = "INVALID_PROVIDER_RESPONSE"
                    partial_reason = "INVALID_PAGE_RESPONSE"
                    break
                page_items = raw

            pages_fetched += 1
            api_items_observed += len(page_items)
            invalid_page_item = invalid_page_item or any(
                not isinstance(item, dict) for item in page_items
            )
            allowlist = set(self.config.repositories)
            resume_offset = None
            for item_index, item in enumerate(page_items):
                if current_page == start_page and item_index < start_offset:
                    continue
                if not isinstance(item, dict):
                    continue
                if filter_to_allowlist and str(item.get("full_name") or "").lower() not in allowlist:
                    continue
                if len(items) >= limit:
                    resume_offset = item_index
                    break
                items.append(item)

            if resume_offset is not None:
                # Keep the unread provider-page remainder in the same query
                # cursor; advancing to the next page here would drop results.
                next_page = current_page
                next_offset = resume_offset
                partial_reason = "RESULT_LIMIT_REACHED"
                break

            try:
                next_url = self._next_link(headers)
            except GitHubConnectorError as exc:
                error_code = exc.code
                partial_reason = "PAGINATION_LINK_REJECTED"
                next_page = None
                break
            if next_url is None:
                pagination_exhausted = True
                next_page = None
                next_offset = 0
                break
            try:
                next_page = self._next_page_number(
                    next_url, path=path, query=page_query, current_page=next_page,
                )
            except GitHubConnectorError as exc:
                error_code = exc.code
                partial_reason = "PAGINATION_LINK_REJECTED"
                next_page = None
                next_offset = 0
                break
            next_offset = 0

            if len(items) >= limit:
                partial_reason = "RESULT_LIMIT_REACHED"
                break

        if next_page is not None and partial_reason is None:
            partial_reason = "PAGE_BUDGET_REACHED"
        if incomplete_results:
            partial_reason = partial_reason or "PROVIDER_MARKED_INCOMPLETE"
        if invalid_page_item:
            error_code = error_code or "INVALID_PROVIDER_RESPONSE"
            partial_reason = partial_reason or "INVALID_PAGE_ITEM"
        if (path == "/search/repositories" and pagination_exhausted
                and partial_reason is None):
            # Search totals are global, while a resumed segment may begin after
            # earlier pages. Compare against the global page offset plus this
            # call's raw provider rows, including any re-read cursor page.
            observed_through = (start_page - 1) * page_size + api_items_observed
            if provider_total_changed:
                partial_reason = "PROVIDER_TOTAL_CHANGED_DURING_PAGING"
            elif not provider_total_valid:
                partial_reason = "PROVIDER_TOTAL_UNAVAILABLE"
            elif reported_total_count > observed_through:
                partial_reason = "PROVIDER_TOTAL_EXCEEDS_OBSERVED_ITEMS"
            elif reported_total_count < observed_through:
                partial_reason = "PROVIDER_TOTAL_BELOW_OBSERVED_ITEMS"

        complete = pagination_exhausted and partial_reason is None and error_code is None
        next_cursor = self._cursor(fingerprint, next_page, next_offset) if next_page is not None else None
        return GitHubCollectionPage(
            items=items,
            start_page=start_page,
            pages_fetched=pages_fetched,
            api_items_observed=api_items_observed,
            reported_total_count=reported_total_count,
            coverage_complete=complete,
            coverage_scope="FULL_QUERY" if start_page == 1 else "CONTINUATION_SEGMENT",
            next_cursor=next_cursor,
            partial_reason=partial_reason,
            error_code=error_code,
            retry_after_seconds=retry_after_seconds,
        )

    def search_repositories_page_result(
        self,
        keyword: str,
        *,
        limit: int = 20,
        max_pages: int = _DEFAULT_PAGE_BUDGET,
        cursor: Optional[Dict[str, Any]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> GitHubCollectionPage:
        return self._collect_pages(
            "/search/repositories", {"q": str(keyword or "").strip()},
            limit=limit, max_pages=max_pages, cursor=cursor,
            cancel_check=cancel_check, filter_to_allowlist=True,
        )

    def search_repositories(self, keyword: str, *, limit: int = 20) -> list[Dict[str, Any]]:
        """Compatibility list API; the adapter uses the coverage-aware method."""
        return self.search_repositories_page_result(keyword, limit=limit).items

    def repository(self, repo_full_name: str) -> Dict[str, Any]:
        repo = str(repo_full_name or "").strip().strip("/")
        if not _REPO_RE.match(repo):
            raise GitHubConnectorError("INVALID_REPOSITORY", "repository must be owner/name")
        payload = self.get_json(f"/repos/{repo}")
        if not isinstance(payload, dict):
            raise GitHubConnectorError("INVALID_PROVIDER_RESPONSE", "GitHub repository payload is invalid")
        return payload

    def repository_collection_page_result(
        self,
        repo_full_name: str,
        suffix: str,
        *,
        limit: int = 250,
        max_pages: int = _DEFAULT_PAGE_BUDGET,
        cursor: Optional[Dict[str, Any]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> GitHubCollectionPage:
        repo = str(repo_full_name or "").strip().strip("/")
        if not _REPO_RE.match(repo):
            raise GitHubConnectorError("INVALID_REPOSITORY", "repository must be owner/name")
        path = f"/repos/{repo}/{suffix.lstrip('/')}"
        self._assert_path_allowed(path)
        return self._collect_pages(
            path, {}, limit=limit, max_pages=max_pages, cursor=cursor,
            cancel_check=cancel_check,
        )

    def repository_collection(self, repo_full_name: str, suffix: str) -> list[Dict[str, Any]]:
        """Compatibility list API; the adapter uses the coverage-aware method."""
        return self.repository_collection_page_result(repo_full_name, suffix).items


__all__ = [
    "GitHubConnector",
    "GitHubConnectorConfig",
    "GitHubConnectorError",
    "GitHubCollectionPage",
]
