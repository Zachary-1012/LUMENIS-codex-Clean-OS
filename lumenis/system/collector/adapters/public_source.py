from __future__ import annotations

"""Shared safe transport for zero-auth public-source adapters.

The public-source adapters deliberately stop at acquisition.  They do not
write to a second store, accept cookies, or follow redirects into private
network ranges.  The existing ``secondary_collection`` surface remains the
only Evidence/Canonical write boundary.
"""

import hashlib
import ipaddress
import json
import os
import re
import socket
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter
from requests.adapters import select_proxy

from .platform_naming import normalize_platform


MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
PUBLIC_SCHEMES = {"http", "https"}
USER_AGENT = "LUMENIS-Public-Collector/1.0 (+read-only; evidence-bound)"
DOH_JSON_URL = "https://dns.google/resolve"
MAX_DOH_BYTES = 16 * 1024
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)
POST_COVER_MEDIA_HOSTS: dict[str, tuple[str, ...]] = {
    "douyin": ("douyinpic.com", "byteimg.com"),
    "instagram": ("cdninstagram.com", "fbcdn.net"),
    "facebook": ("fbcdn.net",),
    "x": ("pbs.twimg.com",),
    "xiaohongshu": ("xhscdn.com", "xiaohongshu.com"),
    "wechat": ("mmbiz.qpic.cn",),
}


class PublicSourceError(RuntimeError):
    """A public-source request was rejected or could not be read safely."""


class PublicSourceHTTPError(PublicSourceError):
    """A non-success HTTP response rejected by the bounded transport."""

    failure_type = "HTTP_STATUS"

    def __init__(self, status_code: int):
        self.status_code = int(status_code)
        super().__init__(f"public source returned HTTP {self.status_code}")


def public_source_error_metadata(error: BaseException) -> dict[str, str | int]:
    """Preserve an observed HTTP status while keeping other failures typed."""
    status_code = getattr(error, "status_code", None)
    if (getattr(error, "failure_type", None) == "HTTP_STATUS"
            and isinstance(status_code, int) and not isinstance(status_code, bool)):
        return {"error_type": f"HTTP_{status_code}", "http_status": status_code}
    return {"error_type": type(error).__name__}


@dataclass(frozen=True)
class PublicResponse:
    url: str
    content: bytes
    content_type: str
    status_code: int
    requested_url: str = ""
    redirect_chain: tuple[str, ...] = ()
    resolution_trace: tuple[dict[str, str], ...] = ()


def _is_blocked_youtube_feed(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    return (host == "youtube.com" or host.endswith(".youtube.com")) and parts.path == "/feeds/videos.xml"


def public_source_provenance(response: PublicResponse, requested_url: str) -> dict[str, str]:
    """Return bounded transport lineage without URL query or response body."""
    def safe_url(value: str) -> str:
        parsed = urlsplit(value)
        authority = parsed.hostname or ""
        if ":" in authority:
            authority = f"[{authority}]"
        if parsed.port:
            authority = f"{authority}:{parsed.port}"
        return urlunsplit((parsed.scheme, authority, parsed.path, "", ""))[:240]

    return {
        "requested_source_url": safe_url(response.requested_url or requested_url),
        "final_source_url": safe_url(response.url),
        "redirect_chain": json.dumps(
            [safe_url(url) for url in response.redirect_chain], ensure_ascii=False,
        ),
        "resolution_trace": json.dumps(response.resolution_trace, ensure_ascii=False),
        "source_access_mode": "public_read_only",
        "commercial_license_state": "pending_review",
    }


def _resolved_addresses(hostname: str) -> Iterable[str]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise PublicSourceError("public source hostname could not be resolved") from exc
    addresses = {str(info[4][0]) for info in infos if info and info[4]}
    if not addresses:
        raise PublicSourceError("public source hostname has no address")
    return addresses


def _doh_addresses(hostname: str) -> tuple[str, ...]:
    """Resolve one already validated public hostname over authenticated HTTPS.

    This is an opt-in fallback for workstation DNS that returns only fake or
    private addresses. The source transport still pins and TLS-verifies the
    original hostname; DNS results never authorize an unapproved source.
    """
    response = None
    try:
        response = requests.get(
            DOH_JSON_URL,
            params={"name": hostname, "type": "A"},
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
            timeout=(3, 6), allow_redirects=False, stream=True,
        )
        if response.status_code != 200:
            raise PublicSourceError("public source secure DNS unavailable")
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=4096):
            size += len(chunk)
            if size > MAX_DOH_BYTES:
                raise PublicSourceError("public source secure DNS response too large")
            chunks.append(chunk)
        payload = json.loads(b"".join(chunks))
        if not isinstance(payload, dict) or payload.get("Status") != 0:
            raise PublicSourceError("public source secure DNS did not resolve")
        answers = payload.get("Answer") or []
        if not isinstance(answers, list) or len(answers) > 32:
            raise PublicSourceError("public source secure DNS response invalid")
        names = {hostname.lower().rstrip(".")}
        for _ in range(8):
            additional = {
                _canonical_hostname(str(item.get("data") or "").rstrip("."))
                for item in answers if isinstance(item, dict)
                and item.get("type") == 5
                and str(item.get("name") or "").lower().rstrip(".") in names
            }
            if not additional - names:
                break
            names.update(additional)
        addresses = tuple(dict.fromkeys(
            str(item.get("data") or "")
            for item in answers if isinstance(item, dict)
            and item.get("type") == 1
            and str(item.get("name") or "").lower().rstrip(".") in names
        ))
        if not addresses or any(not _is_globally_routable(ip) for ip in addresses):
            raise PublicSourceError("public source secure DNS returned no public address")
        return addresses
    except (requests.RequestException, ValueError, TypeError) as exc:
        raise PublicSourceError("public source secure DNS unavailable") from exc
    finally:
        if response is not None:
            response.close()


def _canonical_hostname(hostname: str) -> str:
    """Return a strict DNS name for an exact, non-wildcard pin key."""
    raw = str(hostname or "").strip()
    if not raw or raw.endswith(".") or "\x00" in raw:
        raise PublicSourceError("public source pin hostname is invalid")
    try:
        encoded = raw.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise PublicSourceError("public source pin hostname is invalid") from exc
    try:
        ipaddress.ip_address(encoded)
    except ValueError:
        pass
    else:
        raise PublicSourceError("public source pin hostname is invalid")
    if len(encoded) > 253:
        raise PublicSourceError("public source pin hostname is invalid")
    labels = encoded.split(".")
    if any(not _HOST_LABEL.fullmatch(label) for label in labels):
        raise PublicSourceError("public source pin hostname is invalid")
    return encoded.lower()


def _is_globally_routable(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError as exc:
        raise PublicSourceError("public source pin address is invalid") from exc
    # ``is_global`` has changed edge-case classifications across Python
    # versions, so keep every non-routable category explicit as well.
    return bool(
        ip.is_global
        and not ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_multicast
        and not ip.is_reserved
        and not ip.is_unspecified
    )


def load_public_source_host_pins(value: str | None = None) -> dict[str, tuple[str, ...]]:
    """Load and validate operator-provided exact host -> public-IP pins.

    Pins are deliberately process configuration only.  They are never read
    from a source URL, response body, redirect, or adapter result.
    """
    raw = os.environ.get("LUMENIS_PUBLIC_SOURCE_HOST_PINS", "") if value is None else value
    if not str(raw or "").strip():
        return {}
    def reject_duplicate_pairs(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise PublicSourceError("public source host pin configuration is invalid")
            result[key] = item
        return result

    try:
        payload = json.loads(str(raw), object_pairs_hook=reject_duplicate_pairs)
    except (TypeError, ValueError) as exc:
        raise PublicSourceError("public source host pin configuration is invalid") from exc
    if not isinstance(payload, dict):
        raise PublicSourceError("public source host pin configuration is invalid")
    pins: dict[str, tuple[str, ...]] = {}
    for hostname, values in payload.items():
        if not isinstance(hostname, str) or not isinstance(values, list) or not values:
            raise PublicSourceError("public source host pin configuration is invalid")
        key = _canonical_hostname(hostname)
        if key in pins:
            raise PublicSourceError("public source host pin configuration is invalid")
        checked: list[str] = []
        for value_item in values:
            if not isinstance(value_item, str) or not _is_globally_routable(value_item):
                raise PublicSourceError("public source host pin configuration is invalid")
            checked.append(str(ipaddress.ip_address(value_item)))
        if len(set(checked)) != len(checked):
            raise PublicSourceError("public source host pin configuration is invalid")
        pins[key] = tuple(checked)
    return pins


def _host_pin(hostname: str, host_pins: dict[str, tuple[str, ...]]) -> str | None:
    return host_pins.get(hostname.rstrip(".").lower(), (None,))[0]


def _validate_public_url_and_pin(
    value: str,
    *,
    host_pins: dict[str, tuple[str, ...]] | None = None,
    resolution_trace: list[dict[str, str]] | None = None,
) -> tuple[str, dict[str, tuple[str, ...]]]:
    """Validate an HTTP(S) URL and reject loopback/private/link-local targets."""
    raw = str(value or "").strip()
    try:
        parsed = urlparse(raw)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise PublicSourceError("public source URL is invalid") from exc
    if scheme not in PUBLIC_SCHEMES:
        raise PublicSourceError("only http and https public sources are allowed")
    if parsed.username or parsed.password:
        raise PublicSourceError("credentials in public source URLs are not allowed")
    if not hostname or port is not None and not (1 <= port <= 65535):
        raise PublicSourceError("public source URL is invalid")
    hostname = hostname.lower()
    is_dns_name = True
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        hostname = _canonical_hostname(hostname)
    else:
        is_dns_name = False
    pins = load_public_source_host_pins() if host_pins is None else host_pins
    pinned = _host_pin(hostname, pins)
    resolver = "operator_pin" if pinned else "system_dns"
    if pinned:
        addresses = (pinned,)
    else:
        try:
            addresses = tuple(_resolved_addresses(hostname))
        except PublicSourceError:
            if not is_dns_name or os.environ.get("LUMENIS_PUBLIC_SOURCE_DOH_FALLBACK", "").lower() not in {"1", "true", "on"}:
                raise
            addresses = _doh_addresses(hostname)
            resolver = "doh_google"
    if not addresses:
        raise PublicSourceError("public source address could not be resolved")
    if (
        not pinned and is_dns_name
        and addresses
        and all(not _is_globally_routable(ip) for ip in addresses)
        and os.environ.get("LUMENIS_PUBLIC_SOURCE_DOH_FALLBACK", "").lower() in {"1", "true", "on"}
    ):
        addresses = _doh_addresses(hostname)
        resolver = "doh_google"
    for address in addresses:
        if not _is_globally_routable(address):
            raise PublicSourceError("private or local network sources are not allowed")
    # Bind this exact request authority to one address that was checked above.
    # Requests/urllib3 must never resolve the hostname again while connecting.
    canonical_hostname = hostname.rstrip(".").lower()
    selected = str(ipaddress.ip_address(addresses[0]))
    if resolution_trace is not None:
        resolution_trace.append({
            "host": canonical_hostname,
            "address": selected,
            "resolver": resolver,
            "resolved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    return raw, {**pins, canonical_hostname: (selected,)}


def validate_public_url(
    value: str,
    *,
    host_pins: dict[str, tuple[str, ...]] | None = None,
) -> str:
    """Validate an HTTP(S) URL and reject loopback/private/link-local targets."""
    validated, _ = _validate_public_url_and_pin(value, host_pins=host_pins)
    return validated


def _validate_allowed_https_host(value: str, allowed_suffixes: tuple[str, ...]) -> None:
    """Require HTTPS on an exact approved host or a subdomain of one."""
    try:
        parsed = urlsplit(str(value or ""))
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise PublicSourceError("media URL is invalid") from exc
    if scheme != "https" or parsed.username or parsed.password:
        raise PublicSourceError("media URL must use HTTPS without credentials")
    if not hostname or port not in (None, 443):
        raise PublicSourceError("media URL authority is not approved")
    hostname = _canonical_hostname(hostname)
    if not any(
        hostname == suffix or hostname.endswith("." + suffix)
        for suffix in allowed_suffixes
    ):
        raise PublicSourceError("media URL host is not approved")


class PublicSourceHTTPAdapter(HTTPAdapter):
    """Requests adapter implementing source-specific public address pins.

    urllib3's ordinary pool key already separates pinned addresses when the
    pool host is the validated literal.  HTTPS keeps the original authority
    through ``server_hostname`` and ``assert_hostname``; HTTP keeps it through
    the explicit Host header below.
    """

    def __init__(self, host_pins: dict[str, tuple[str, ...]] | None = None, **kwargs):
        if not hasattr(HTTPAdapter, "get_connection_with_tls_context") or not hasattr(
            HTTPAdapter, "build_connection_pool_key_attributes"
        ):
            raise PublicSourceError("public source transport requires compatible Requests TLS pin APIs")
        self.host_pins = host_pins if host_pins is not None else load_public_source_host_pins()
        super().__init__(**kwargs)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        """Build the standard Requests pool with a literal destination host."""
        proxy = select_proxy(request.url, proxies)
        host_params, pool_kwargs = self.build_connection_pool_key_attributes(request, verify, cert)
        hostname = (urlparse(request.url).hostname or "").lower()
        pinned = _host_pin(hostname, self.host_pins)
        if not pinned:
            raise requests.exceptions.InvalidURL("public source transport requires a validated address pin")
        # The pool connects to the literal address. For HTTPS, these kwargs
        # preserve SNI and certificate matching for the URL host.
        host_params["host"] = pinned
        if host_params["scheme"].lower() == "https":
            pool_kwargs["server_hostname"] = hostname
            pool_kwargs["assert_hostname"] = hostname
        if proxy:
            proxy = requests.adapters.prepend_scheme_if_needed(proxy, "http")
            manager = self.proxy_manager_for(proxy)
            return manager.connection_from_host(**host_params, pool_kwargs=pool_kwargs)
        return self.poolmanager.connection_from_host(**host_params, pool_kwargs=pool_kwargs)

    def request_url(self, request, proxies):
        """Make HTTP forward proxies target the pinned literal, not DNS."""
        url = super().request_url(request, proxies)
        pinned = _host_pin((urlparse(request.url).hostname or "").lower(), self.host_pins)
        proxy = select_proxy(request.url, proxies)
        if not pinned or not proxy or urlparse(request.url).scheme.lower() == "https":
            return url
        parsed = urlsplit(url)
        if not parsed.scheme or not parsed.netloc:
            return url
        netloc = pinned if ":" not in pinned else f"[{pinned}]"
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))

    def send(self, request, **kwargs):
        """Reject caller-provided credentials and preserve original Host."""
        hostname = (urlparse(request.url).hostname or "").lower()
        pinned = _host_pin(hostname, self.host_pins)
        if request.headers.get("Authorization") or request.headers.get("Cookie"):
            raise requests.exceptions.InvalidHeader("public source transport does not accept auth or cookies")
        if not pinned:
            raise requests.exceptions.InvalidURL("public source transport requires a validated address pin")
        # Keep original authority for HTTP Host and TLS identity. The pool uses
        # the literal validated address as its network destination.
        authority = f"[{hostname}]" if ":" in hostname else hostname
        port = urlparse(request.url).port
        if port:
            authority = f"{authority}:{port}"
        request.headers["Host"] = authority
        response = super().send(request, **kwargs)
        # Session response hooks run after this method returns but before
        # fetch_public_url can validate a redirect target or enforce the final
        # response size. Redirect bodies are never consumed by this transport;
        # close them here so caller hooks cannot read an unbounded 3xx body.
        if 300 <= response.status_code < 400:
            response.close()
            # Requests' Session.send calls resolve_redirects even when the
            # caller disabled automatic redirects. It reads ``response.content``
            # to prepare ``_next``; mark the dropped body as consumed so that
            # step cannot try to read the closed socket or buffer an unbounded
            # redirect body.
            response._content = b""
            response._content_consumed = True
        return response


def fetch_public_url(
    url: str,
    *,
    timeout: float = 10.0,
    max_bytes: int = MAX_RESPONSE_BYTES,
    session: requests.Session | None = None,
    allowed_host_suffixes: Iterable[str] | None = None,
) -> PublicResponse:
    """Fetch a small public response with bounded, revalidated redirects."""
    if _is_blocked_youtube_feed(url):
        raise PublicSourceError("YouTube video feeds are blocked pending an authorized access route")
    if max_bytes <= 0 or max_bytes > MAX_RESPONSE_BYTES:
        raise ValueError("max_bytes is outside the public-source safety bound")
    allowed_suffixes = None
    if allowed_host_suffixes is not None:
        if isinstance(allowed_host_suffixes, str):
            raise ValueError("allowed media host suffixes must be an iterable of host names")
        try:
            allowed_suffixes = tuple(
                _canonical_hostname(suffix) for suffix in allowed_host_suffixes
            )
        except (PublicSourceError, TypeError) as exc:
            raise ValueError("allowed media host suffixes are invalid") from exc
        if not allowed_suffixes:
            raise ValueError("allowed media host suffixes cannot be empty")
        _validate_allowed_https_host(url, allowed_suffixes)
    host_pins = load_public_source_host_pins()
    resolution_trace: list[dict[str, str]] = []
    redirect_chain: list[str] = []
    current, host_pins = _validate_public_url_and_pin(
        url, host_pins=host_pins, resolution_trace=resolution_trace,
    )
    client = session or requests.Session()
    # Caller-owned sessions retain their normal proxy configuration; only the
    # HTTP transport is replaced with the pin-aware equivalent.  Replacing the
    # entire map prevents a more-specific caller mount from bypassing guards.
    original_adapters = client.adapters if session is not None else None
    transport_adapters = (
        PublicSourceHTTPAdapter(host_pins=host_pins),
        PublicSourceHTTPAdapter(host_pins=host_pins),
    )
    client.adapters = OrderedDict((
        ("http://", transport_adapters[0]),
        ("https://", transport_adapters[1]),
    ))
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xml,application/rss+xml,application/atom+xml,*/*;q=0.1"}
    try:
        for _ in range(MAX_REDIRECTS + 1):
            if _is_blocked_youtube_feed(current):
                raise PublicSourceError("YouTube video feeds are blocked pending an authorized access route")
            response = None
            try:
                response = client.get(
                    current,
                    headers=headers,
                    timeout=(min(float(timeout), 5.0), min(float(timeout), 15.0)),
                    allow_redirects=False,
                    stream=True,
                    verify=True,
                )
                if session is None:
                    client.cookies.clear()
                if 300 <= response.status_code < 400 and response.headers.get("Location"):
                    redirect_chain.append(current)
                    redirect_target = urljoin(current, response.headers["Location"])
                    if allowed_suffixes is not None:
                        _validate_allowed_https_host(redirect_target, allowed_suffixes)
                    current, host_pins = _validate_public_url_and_pin(
                        redirect_target,
                        host_pins=host_pins,
                        resolution_trace=resolution_trace,
                    )
                    for adapter in transport_adapters:
                        adapter.host_pins = host_pins
                    continue
                if not 200 <= response.status_code < 300:
                    raise PublicSourceHTTPError(response.status_code)
                content_length = response.headers.get("Content-Length")
                if content_length:
                    try:
                        too_large = int(content_length) > max_bytes
                    except ValueError as exc:
                        raise PublicSourceError("public source response size is invalid") from exc
                    if too_large:
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
                    requested_url=url,
                    redirect_chain=tuple(redirect_chain),
                    resolution_trace=tuple(resolution_trace),
                )
            finally:
                if response is not None:
                    response.close()
        raise PublicSourceError("public source redirect limit exceeded")
    except requests.RequestException as exc:
        raise PublicSourceError("public source request failed") from exc
    finally:
        if session is None:
            client.close()
        else:
            # Do not leave a caller-owned Session mounted with this
            # source-specific transport or leak its pool resources.
            client.adapters = original_adapters
            for adapter in transport_adapters:
                adapter.close()


def _post_cover_null_result(reason: str, native_locator: dict[str, str] | None = None) -> dict:
    """Return a categorical unavailable result without manufacturing zeroes."""
    return {
        "status": "NULL",
        "reason": reason,
        "raw_bytes": None,
        "sha256": None,
        "size_bytes": None,
        "content_type": None,
        "extension": None,
        "original_url": None,
        "final_url": None,
        "native_locator": native_locator,
        "captured_at": None,
    }


def _native_cover_url(value: object) -> str | None:
    """Read a URL only from the explicitly supported native cover shapes."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    if not isinstance(value, Mapping):
        return None
    url_list = value.get("url_list")
    if isinstance(url_list, list):
        if url_list and isinstance(url_list[0], str) and url_list[0].strip():
            return url_list[0].strip()
        return None
    for key in ("url", "url_hint"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _post_cover_candidate(record: Mapping) -> tuple[str | None, dict[str, str] | None, str | None]:
    """Select one observed cover, keeping the native field path and locator."""
    sources: list[tuple[str, Mapping]] = []
    seen: set[int] = set()
    for key in ("source_raw", "raw_data", "raw"):
        value = record.get(key)
        if isinstance(value, Mapping) and id(value) not in seen:
            sources.append((key, value))
            seen.add(id(value))
    if id(record) not in seen:
        sources.append(("", record))

    for source_name, source in sources:
        prefix = f"{source_name}." if source_name else ""
        video = source.get("video")
        if isinstance(video, Mapping):
            cover = video.get("cover")
            if isinstance(cover, Mapping):
                url_list = cover.get("url_list")
                if isinstance(url_list, list) and url_list:
                    candidate = url_list[0]
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate.strip(), {"field_path": f"{prefix}video.cover.url_list[0]"}, None

        for field_name in ("video_cover", "cover"):
            if field_name in source:
                candidate = _native_cover_url(source.get(field_name))
                if candidate:
                    return candidate, {"field_path": f"{prefix}{field_name}"}, None

        if "display_uri" in source:
            candidate = _native_cover_url(source.get("display_uri"))
            if candidate:
                return candidate, {"field_path": f"{prefix}display_uri"}, None

        detail = source.get("detail_observation")
        hints = detail.get("media_hints") if isinstance(detail, Mapping) else None
        if isinstance(hints, list):
            for index, hint in enumerate(hints):
                if not isinstance(hint, Mapping) or str(hint.get("kind") or "").strip().lower() != "image":
                    continue
                locator = hint.get("locator")
                locator_text = locator.strip()[:500] if isinstance(locator, str) else ""
                native_locator = {
                    "field_path": f"{prefix}detail_observation.media_hints[{index}]",
                }
                if locator_text:
                    native_locator["source_locator"] = locator_text
                if any(token in locator_text.lower() for token in (
                    "avatar", "profile", "userpic", "user_pic", "头像", "用户头像", "个人头像",
                )):
                    return None, native_locator, "AVATAR_NOT_ELIGIBLE"
                candidate = _native_cover_url(hint.get("url_hint"))
                if candidate is None:
                    candidate = _native_cover_url(hint.get("url"))
                if candidate:
                    return candidate, native_locator, None
                return None, native_locator, "OBSERVED_COVER_URL_MISSING"
    return None, None, None


def _sanitize_post_cover_url(value: str) -> str | None:
    """Remove signed query and fragment material from a returned media URL."""
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname or ""
        authority = f"[{hostname}]" if ":" in hostname else hostname
        if parsed.port:
            authority = f"{authority}:{parsed.port}"
        return urlunsplit((parsed.scheme.lower(), authority, parsed.path, "", ""))[:2048]
    except ValueError:
        return None


def _post_cover_magic_extension(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    if len(content) >= 16 and content[4:8] == b"ftyp":
        box_size = int.from_bytes(content[:4], "big")
        if 16 <= box_size <= len(content):
            brands = [content[8:12]]
            brands.extend(content[offset:offset + 4] for offset in range(16, box_size, 4))
            if b"avis" in brands:
                return None
            if b"avif" in brands:
                return ".avif"
    return None


def fetch_observed_post_cover(platform: str, record: Mapping) -> dict:
    """Fetch at most one observed post cover through the pinned public transport.

    This helper returns raw bytes for the existing Collector intake path only.
    It performs no image decoding, storage, rights assessment, or Evidence write.
    """
    canonical_platform = normalize_platform(platform)
    allowed_hosts = POST_COVER_MEDIA_HOSTS.get(canonical_platform or "")
    if allowed_hosts is None:
        return _post_cover_null_result("UNSUPPORTED_PLATFORM")
    if not isinstance(record, Mapping):
        return _post_cover_null_result("INVALID_POST_RECORD")

    original_url, native_locator, selection_error = _post_cover_candidate(record)
    if selection_error:
        return _post_cover_null_result(selection_error, native_locator)
    if original_url is None:
        return _post_cover_null_result("NO_OBSERVED_COVER")
    try:
        _validate_allowed_https_host(original_url, allowed_hosts)
    except PublicSourceError:
        return _post_cover_null_result("UNSAFE_OR_UNAPPROVED_URL", native_locator)

    try:
        response = fetch_public_url(
            original_url,
            timeout=3.0,
            max_bytes=MAX_RESPONSE_BYTES,
            allowed_host_suffixes=allowed_hosts,
        )
    except (PublicSourceError, requests.RequestException, ValueError):
        return _post_cover_null_result("MEDIA_FETCH_FAILED", native_locator)

    mime_extensions = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/avif": ".avif",
    }
    if not response.content:
        return _post_cover_null_result("EMPTY_MEDIA_BODY", native_locator)
    extension = mime_extensions.get(response.content_type.lower())
    if extension is None:
        return _post_cover_null_result("UNSUPPORTED_MEDIA_TYPE", native_locator)
    magic_extension = _post_cover_magic_extension(response.content)
    if magic_extension is None:
        return _post_cover_null_result("UNSUPPORTED_MEDIA_BYTES", native_locator)
    if extension != magic_extension:
        return _post_cover_null_result("MEDIA_MIME_MAGIC_MISMATCH", native_locator)

    sanitized_original = _sanitize_post_cover_url(original_url)
    sanitized_final = _sanitize_post_cover_url(response.url)
    if sanitized_original is None or sanitized_final is None:
        return _post_cover_null_result("MEDIA_URL_SANITIZATION_FAILED", native_locator)
    return {
        "status": "AVAILABLE",
        "reason": None,
        "raw_bytes": response.content,
        "sha256": hashlib.sha256(response.content).hexdigest(),
        "size_bytes": len(response.content),
        "content_type": response.content_type.lower(),
        "extension": extension,
        "original_url": sanitized_original,
        "final_url": sanitized_final,
        "native_locator": native_locator,
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
