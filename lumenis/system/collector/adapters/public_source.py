from __future__ import annotations

"""Shared safe transport for zero-auth public-source adapters.

The public-source adapters deliberately stop at acquisition.  They do not
write to a second store, accept cookies, or follow redirects into private
network ranges.  The existing ``secondary_collection`` surface remains the
only Evidence/Canonical write boundary.
"""

import ipaddress
import socket
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests


MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
PUBLIC_SCHEMES = {"http", "https"}
USER_AGENT = "LUMENIS-Public-Collector/1.0 (+read-only; evidence-bound)"


class PublicSourceError(RuntimeError):
    """A public-source request was rejected or could not be read safely."""


@dataclass(frozen=True)
class PublicResponse:
    url: str
    content: bytes
    content_type: str
    status_code: int


def _resolved_addresses(hostname: str) -> Iterable[str]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise PublicSourceError("public source hostname could not be resolved") from exc
    addresses = {str(info[4][0]) for info in infos if info and info[4]}
    if not addresses:
        raise PublicSourceError("public source hostname has no address")
    return addresses


def validate_public_url(value: str) -> str:
    """Validate an HTTP(S) URL and reject loopback/private/link-local targets."""
    raw = str(value or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in PUBLIC_SCHEMES:
        raise PublicSourceError("only http and https public sources are allowed")
    if parsed.username or parsed.password:
        raise PublicSourceError("credentials in public source URLs are not allowed")
    if not parsed.hostname or parsed.port and not (1 <= parsed.port <= 65535):
        raise PublicSourceError("public source URL is invalid")
    for address in _resolved_addresses(parsed.hostname):
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise PublicSourceError("public source address is invalid") from exc
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise PublicSourceError("private or local network sources are not allowed")
    return raw


def fetch_public_url(
    url: str,
    *,
    timeout: float = 10.0,
    max_bytes: int = MAX_RESPONSE_BYTES,
    session: requests.Session | None = None,
) -> PublicResponse:
    """Fetch a small public response with bounded, revalidated redirects."""
    if max_bytes <= 0 or max_bytes > MAX_RESPONSE_BYTES:
        raise ValueError("max_bytes is outside the public-source safety bound")
    client = session or requests.Session()
    current = validate_public_url(url)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xml,application/rss+xml,application/atom+xml,*/*;q=0.1"}
    try:
        for _ in range(MAX_REDIRECTS + 1):
            response = client.get(
                current,
                headers=headers,
                timeout=(min(float(timeout), 5.0), min(float(timeout), 15.0)),
                allow_redirects=False,
                stream=True,
            )
            if 300 <= response.status_code < 400 and response.headers.get("Location"):
                current = validate_public_url(urljoin(current, response.headers["Location"]))
                response.close()
                continue
            if response.status_code >= 400:
                raise PublicSourceError(f"public source returned HTTP {response.status_code}")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                raise PublicSourceError("public source response exceeds size limit")
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > max_bytes:
                    raise PublicSourceError("public source response exceeds size limit")
                chunks.append(chunk)
            return PublicResponse(
                url=current,
                content=b"".join(chunks),
                content_type=str(response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower(),
                status_code=response.status_code,
            )
        raise PublicSourceError("public source redirect limit exceeded")
    except requests.RequestException as exc:
        raise PublicSourceError("public source request failed") from exc
    finally:
        if session is None:
            client.close()
