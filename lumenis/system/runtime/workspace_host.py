"""Serve the built Flutter Web Workspace from the canonical Flask runtime.

The adapter owns only same-origin delivery of the generated ``app/build/web``
artifact.  It does not render pages, implement Product Core APIs, or provide a
fallback application when a release artifact is unavailable.
"""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath
from typing import Optional
from urllib.parse import unquote

from flask import Flask, Response, abort, jsonify, send_file
from werkzeug.routing import PathConverter


DEFAULT_BUILD_DIR_ENV = "LUMENIS_WORKSPACE_BUILD_DIR"
ALTERNATE_BUILD_DIR_ENV = "LUMENIS_FLUTTER_WEB_BUILD_DIR"

_HASHED_ASSET = re.compile(r"(?:^|[._-])[0-9a-f]{8,}(?:[._-]|$)", re.IGNORECASE)

# A root-level catch-all is needed because Flutter's default base href is ``/``.
# Keep Product Core namespaces out of that catch-all so an artifact can never
# become an API or runtime route owner.
_RESERVED_ROOT_PREFIXES = frozenset({
    "api",
    "healthz",
    "lumenis",
    "remote",
    "v4",
    "static",
})
_RESERVED_ROOT_PATHS = frozenset({
    "healthz",
    "remote",
    "version",
    "VERSION",
    "favicon.ico",
})


class _WorkspaceAssetPath(PathConverter):
    """Leave reserved API matching, including 405/Allow, to Product Core."""

    part_isolating = False
    _prefixes = "|".join(re.escape(value) for value in sorted(_RESERVED_ROOT_PREFIXES))
    _paths = "|".join(re.escape(value) for value in sorted(_RESERVED_ROOT_PATHS))
    regex = rf"(?!(?i:{_prefixes})(?:/|$))(?!(?:{_paths})$)[^/].*?"


def default_build_dir(app: Flask) -> Path:
    """Resolve the build output without depending on a generated artifact."""

    configured = app.config.get("LUMENIS_WORKSPACE_BUILD_DIR")
    configured = configured or os.environ.get(DEFAULT_BUILD_DIR_ENV)
    configured = configured or os.environ.get(ALTERNATE_BUILD_DIR_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(app.root_path) / "app" / "build" / "web").resolve()


class WorkspaceHost:
    """Bounded Flask adapter for one Flutter Web build directory."""

    def __init__(self, build_dir: Path | str):
        self.build_dir = Path(build_dir).expanduser().resolve()

    @property
    def index_path(self) -> Path:
        return self.build_dir / "index.html"

    def register(self, app: Flask) -> "WorkspaceHost":
        """Register workspace documents and artifact assets on an existing app."""

        app.url_map.converters["workspaceasset"] = _WorkspaceAssetPath
        app.add_url_rule(
            "/workspace",
            endpoint="lumenis_workspace_host.root",
            view_func=self._workspace_root,
            methods=["GET", "HEAD"],
        )
        app.add_url_rule(
            "/workspace/",
            endpoint="lumenis_workspace_host.root_slash",
            view_func=self._workspace_root,
            methods=["GET", "HEAD"],
        )
        app.add_url_rule(
            "/workspace/<path:resource>",
            endpoint="lumenis_workspace_host.resource",
            view_func=self._workspace_resource,
            methods=["GET", "HEAD"],
        )
        # Flutter's generated index normally references root-relative assets.
        # This route only serves an existing file and never rewrites a root URL.
        app.add_url_rule(
            "/<workspaceasset:resource>",
            endpoint="lumenis_workspace_host.asset",
            view_func=self._root_asset,
            methods=["GET", "HEAD"],
        )
        return self

    def _workspace_root(self):
        return self._serve_workspace_document("")

    def _workspace_resource(self, resource: str):
        return self._serve_workspace_document(resource)

    def _root_asset(self, resource: str):
        if self._is_reserved_root_path(resource):
            abort(404)
        if not self._artifact_ready():
            # A present build directory without its index is a partial/unbuilt
            # artifact. Report that state instead of returning an HTML success.
            if self.build_dir.is_dir():
                return self._error(
                    503,
                    "workspace_build_unavailable",
                    "Web Workspace build artifact is unavailable",
                )
            abort(404)

        candidate = self._safe_artifact_path(resource)
        if candidate is None or not candidate.is_file():
            abort(404)
        return self._send_artifact(candidate)

    def _serve_workspace_document(self, resource: str):
        if not self._artifact_ready():
            return self._error(
                503,
                "workspace_build_unavailable",
                "Web Workspace build artifact is unavailable",
            )

        # A trailing slash is a valid browser document deep link. Preserve
        # internal empty segments as invalid paths while resolving that one
        # document-route form without ever listing a directory.
        resource = resource.rstrip("/")
        if resource:
            candidate = self._safe_artifact_path(resource)
            if candidate is None:
                return self._error(404, "workspace_path_invalid", "Invalid Web Workspace path")
            if candidate.is_file():
                return self._send_artifact(candidate)
            if candidate.exists():
                # Directories are never listed and do not become document routes.
                return self._error(
                    404,
                    "workspace_asset_not_found",
                    "Web Workspace asset was not found",
                )
            # Extensionless paths are Flutter document routes. Asset-looking
            # paths must fail instead of silently returning index.html.
            if PurePosixPath(_decode_url_path(resource)).suffix:
                return self._error(
                    404,
                    "workspace_asset_not_found",
                    "Web Workspace asset was not found",
                )

        return self._send_artifact(self.index_path)

    def _artifact_ready(self) -> bool:
        index = self._safe_artifact_path("index.html")
        return index is not None and index.is_file()

    def _safe_artifact_path(self, resource: str) -> Optional[Path]:
        """Resolve a URL path inside the build root, rejecting traversal."""

        if not isinstance(resource, str) or not resource or "\x00" in resource:
            return None
        decoded = _decode_url_path(resource)
        if "\x00" in decoded or "\\" in decoded:
            return None

        segments = decoded.split("/")
        if any(segment in {".", ".."} for segment in segments):
            return None
        if any(not segment for segment in segments):
            return None

        relative = Path(*segments)
        candidate = (self.build_dir / relative).resolve(strict=False)
        try:
            candidate.relative_to(self.build_dir)
        except ValueError:
            return None
        return candidate

    @staticmethod
    def _is_reserved_root_path(resource: str) -> bool:
        decoded = _decode_url_path(resource).lstrip("/")
        if not decoded:
            return True
        first, _, _ = decoded.partition("/")
        return first.lower() in _RESERVED_ROOT_PREFIXES or decoded in _RESERVED_ROOT_PATHS

    def _send_artifact(self, path: Path) -> Response:
        response = send_file(
            path,
            conditional=True,
            etag=True,
            max_age=31536000 if _HASHED_ASSET.search(path.name) else 0,
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if path.name == "index.html":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif _HASHED_ASSET.search(path.name):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "max-age=0, must-revalidate"
        return response

    @staticmethod
    def _error(status: int, code: str, message: str):
        response = jsonify({"ok": False, "error": code, "message": message})
        response.status_code = status
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def register_workspace_host(app: Flask, build_dir: Path | str | None = None) -> WorkspaceHost:
    """Attach the workspace host to the canonical Flask runtime."""

    host = WorkspaceHost(build_dir or default_build_dir(app))
    return host.register(app)


__all__ = ["WorkspaceHost", "default_build_dir", "register_workspace_host"]


def _decode_url_path(resource: str) -> str:
    """Decode bounded nested escapes so encoded traversal cannot become a rewrite."""

    decoded = resource
    for _ in range(8):
        unescaped = unquote(decoded)
        if unescaped == decoded:
            break
        decoded = unescaped
    return decoded
