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

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional


GITHUB_API_BASE = "https://api.github.com"
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_PATH_RE = re.compile(r"^/repos/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/|$)")
_STATE_RE = re.compile(r"^[A-Za-z0-9._~-]{16,256}$")


class GitHubConnectorError(RuntimeError):
    """A safe, non-secret connector failure with a stable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


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


class GitHubConnector:
    """Small REST client behind a strict GitHub connector policy."""

    def __init__(
        self,
        *,
        config: Optional[GitHubConnectorConfig] = None,
        token_provider: Optional[Callable[[], str]] = None,
        opener: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.config = config or GitHubConnectorConfig.from_environment()
        self._token_provider = token_provider or _environment_token
        self._opener = opener or urllib.request.urlopen

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
        if path == "/user" or path.startswith("/search/repositories"):
            return
        match = _PATH_RE.match(path)
        if not match:
            raise GitHubConnectorError("ENDPOINT_NOT_ALLOWLISTED", "GitHub endpoint is not allowlisted")
        repo = f"{match.group(1)}/{match.group(2)}".lower()
        if repo not in set(self.config.repositories):
            raise GitHubConnectorError("REPOSITORY_NOT_ALLOWLISTED", "repository is not in the connector allowlist")

    def get_json(self, path: str, *, query: Optional[Dict[str, Any]] = None) -> Any:
        if not path.startswith("/") or "?" in path or "#" in path:
            raise GitHubConnectorError("INVALID_ENDPOINT", "GitHub endpoint must be a relative path")
        self._assert_path_allowed(path)
        token = self._token()
        url = f"{self.config.api_base}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"
        request = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {token}",
            "User-Agent": "LUMENIS-GitHub-Connector/1.0",
        }, method="GET")
        try:
            with self._opener(request, timeout=15) as response:
                payload = response.read(_MAX_RESPONSE_BYTES)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise GitHubConnectorError("AUTHENTICATION_OR_PERMISSION_FAILED", "GitHub authorization or permission failed") from exc
            if exc.code == 404:
                raise GitHubConnectorError("NOT_FOUND", "GitHub resource was not found or is not visible") from exc
            raise GitHubConnectorError("PROVIDER_UNAVAILABLE", "GitHub API returned an unavailable response") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise GitHubConnectorError("PROVIDER_UNAVAILABLE", "GitHub API is unavailable") from exc
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise GitHubConnectorError("INVALID_PROVIDER_RESPONSE", "GitHub API returned invalid JSON") from exc

    def search_repositories(self, keyword: str, *, limit: int = 20) -> list[Dict[str, Any]]:
        raw = self.get_json("/search/repositories", query={"q": str(keyword or "").strip(), "per_page": min(max(int(limit), 1), 50)})
        if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
            raise GitHubConnectorError("INVALID_PROVIDER_RESPONSE", "GitHub repository search payload is invalid")
        allowlist = set(self.config.repositories)
        return [item for item in raw["items"] if isinstance(item, dict) and str(item.get("full_name") or "").lower() in allowlist]

    def repository(self, repo_full_name: str) -> Dict[str, Any]:
        repo = str(repo_full_name or "").strip().strip("/")
        if not _REPO_RE.match(repo):
            raise GitHubConnectorError("INVALID_REPOSITORY", "repository must be owner/name")
        payload = self.get_json(f"/repos/{repo}")
        if not isinstance(payload, dict):
            raise GitHubConnectorError("INVALID_PROVIDER_RESPONSE", "GitHub repository payload is invalid")
        return payload

    def repository_collection(self, repo_full_name: str, suffix: str) -> list[Dict[str, Any]]:
        repo = str(repo_full_name or "").strip().strip("/")
        if not _REPO_RE.match(repo):
            raise GitHubConnectorError("INVALID_REPOSITORY", "repository must be owner/name")
        payload = self.get_json(f"/repos/{repo}/{suffix.lstrip('/')}", query={"per_page": 50})
        if not isinstance(payload, list):
            raise GitHubConnectorError("INVALID_PROVIDER_RESPONSE", "GitHub collection payload is invalid")
        return [item for item in payload if isinstance(item, dict)]


_MAX_RESPONSE_BYTES = 2 * 1024 * 1024


__all__ = [
    "GitHubConnector",
    "GitHubConnectorConfig",
    "GitHubConnectorError",
]
