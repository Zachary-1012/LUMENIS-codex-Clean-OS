from __future__ import annotations

"""Shared safe transport for zero-auth public-source adapters.

The public-source adapters deliberately stop at acquisition.  They do not
write to a second store, accept cookies, or follow redirects into private
network ranges.  The existing ``secondary_collection`` surface remains the
only Evidence/Canonical write boundary.
"""

import ipaddress
import json
import os
import re
import socket
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter
from requests.adapters import select_proxy


MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
PUBLIC_SCHEMES = {"http", "https"}
USER_AGENT = "LUMENIS-Public-Collector/1.0 (+read-only; evidence-bound)"
DOH_JSON_URL = "https://dns.google/resolve"
MAX_DOH_BYTES = 16 * 1024
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.IGNORECASE)


class PublicSourceError(RuntimeError):
    """A public-source request was rejected or could not be read safely."""


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
        return super().send(request, **kwargs)


def fetch_public_url(
    url: str,
    *,
    timeout: float = 10.0,
    max_bytes: int = MAX_RESPONSE_BYTES,
    session: requests.Session | None = None,
) -> PublicResponse:
    """Fetch a small public response with bounded, revalidated redirects."""
    if _is_blocked_youtube_feed(url):
        raise PublicSourceError("YouTube video feeds are blocked pending an authorized access route")
    if max_bytes <= 0 or max_bytes > MAX_RESPONSE_BYTES:
        raise ValueError("max_bytes is outside the public-source safety bound")
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
                if 300 <= response.status_code < 400 and response.headers.get("Location"):
                    redirect_chain.append(current)
                    current, host_pins = _validate_public_url_and_pin(
                        urljoin(current, response.headers["Location"]),
                        host_pins=host_pins,
                        resolution_trace=resolution_trace,
                    )
                    for adapter in transport_adapters:
                        adapter.host_pins = host_pins
                    continue
                if not 200 <= response.status_code < 300:
                    raise PublicSourceError(f"public source returned HTTP {response.status_code}")
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
