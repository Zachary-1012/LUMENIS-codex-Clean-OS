"""Per-capability access routing for the existing SYSTEM Collector.

The route plan records the backend the current adapter actually owns. It is not
an authorization source: caller Permission, platform session, rate limits and
source policy continue to be checked by their existing owners. No route may be
silently substituted after a challenge, login wall, block or rate limit.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, urlsplit, urlunsplit

from .base import AccessClass, CollectionResult


class RouteIdentityMismatch(ValueError):
    """Adapter facts do not match the platform/capability dispatched by SYSTEM."""


@dataclass(frozen=True)
class CapabilityRoute:
    route_id: str
    platform: str
    capability: str
    order: int
    access_class: AccessClass
    backend: str
    selector: str = "any"
    authorization_contract: str = "none"
    fallback_route_ids: tuple[str, ...] = ()


def _route(route_id: str, platform: str, capability: str, order: int,
           access_class: AccessClass, backend: str, *, selector: str = "any",
           authorization_contract: str = "none",
           fallback_route_ids: tuple[str, ...] = ()) -> CapabilityRoute:
    return CapabilityRoute(
        route_id, platform, capability, order, access_class, backend,
        selector, authorization_contract, fallback_route_ids,
    )


# This is a projection of currently implemented adapter paths, not a list of
# planned providers. Z2 is represented by AccessClass for the canonical model,
# but no Z2 route is registered until an official API adapter is actually bound.
CAPABILITY_ROUTES: tuple[CapabilityRoute, ...] = (
    _route("public-http.search", "public_http", "search", 1,
           AccessClass.Z0_PUBLIC, "public_http"),
    _route("public-http.detail", "public_http", "detail", 1,
           AccessClass.Z0_PUBLIC, "public_http"),
    _route("rss.search", "web_rss", "search", 1,
           AccessClass.Z0_PUBLIC, "google_news_rss"),
    _route("atom.search", "web_atom", "search", 1,
           AccessClass.Z0_PUBLIC, "feedparser_atom"),
    _route("sitemap.search", "sitemap", "search", 1,
           AccessClass.Z0_PUBLIC, "public_sitemap_xml"),
    _route("wechat.search.original-url", "wechat", "search", 1,
           AccessClass.Z0_PUBLIC, "public_original_article_fetch", selector="wechat_article_url"),
    _route("wechat.search.query", "wechat", "search", 2,
           AccessClass.Z0_PUBLIC, "public_sogou_discovery_original_fetch", selector="query"),
    _route("wechat.detail", "wechat", "detail", 1,
           AccessClass.Z0_PUBLIC, "public_original_article_fetch", selector="wechat_article_url"),
    _route("instagram.search.public-url", "instagram", "search", 1,
           AccessClass.Z0_PUBLIC, "public_native_post_document", selector="public_post_url"),
    _route("instagram.search.session", "instagram", "search", 2,
           AccessClass.Z1_AUTHORIZED_SESSION, "v4_instagram", selector="query",
           authorization_contract="existing_platform_session"),
    _route("instagram.detail.public-url", "instagram", "detail", 1,
           AccessClass.Z0_PUBLIC, "public_native_post_document", selector="public_post_url"),
    _route("instagram.detail.session", "instagram", "detail", 2,
           AccessClass.Z1_AUTHORIZED_SESSION, "v4_instagram", selector="opaque_content_id",
           authorization_contract="existing_platform_session"),
    _route("instagram.comments.session", "instagram", "comments", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "v4_instagram",
           selector="opaque_content_id",
           authorization_contract="existing_platform_session"),
    _route("instagram.creator.session", "instagram", "creator", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "v4_instagram",
           selector="profile_identifier",
           authorization_contract="existing_platform_session"),
    _route("xhs.search.session", "xiaohongshu", "search", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "existing_collector.search_xiaohongshu",
           authorization_contract="existing_platform_session"),
    _route("douyin.search.session", "douyin", "search", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.douyin.DouyinAdapter",
           authorization_contract="existing_platform_session"),
    _route("douyin.detail.session", "douyin", "detail", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.douyin.DouyinAdapter",
           authorization_contract="existing_platform_session"),
    _route("douyin.comments.session", "douyin", "comments", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.douyin.DouyinAdapter",
           authorization_contract="existing_platform_session"),
    _route("douyin.creator.session", "douyin", "creator", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.douyin.DouyinAdapter",
           authorization_contract="existing_platform_session"),
    _route("facebook.search.session", "facebook", "search", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.facebook.FacebookAdapter",
           authorization_contract="existing_platform_session"),
    _route("facebook.detail.session", "facebook", "detail", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.facebook.FacebookAdapter",
           authorization_contract="existing_platform_session"),
    _route("facebook.comments.session", "facebook", "comments", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.facebook.FacebookAdapter",
           authorization_contract="existing_platform_session"),
    _route("facebook.creator.session", "facebook", "creator", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.facebook.FacebookAdapter",
           authorization_contract="existing_platform_session"),
    _route("x.search.session", "x", "search", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.x_platform.XAdapter",
           authorization_contract="existing_platform_session"),
    _route("x.detail.session", "x", "detail", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.x_platform.XAdapter",
           authorization_contract="existing_platform_session"),
    _route("x.comments.session", "x", "comments", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.x_platform.XAdapter",
           authorization_contract="existing_platform_session"),
    _route("x.creator.session", "x", "creator", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "lumenis.adapters.x_platform.XAdapter",
           authorization_contract="existing_platform_session"),
)

_PLATFORM_ALIASES = {"xhs": "xiaohongshu", "rednote": "xiaohongshu"}
_STOP_FALLBACK_STATUSES = frozenset({
    "BLOCKED", "NEED_VERIFY", "QR_REQUIRED", "SESSION_EXPIRED",
    "RISK_WARNING", "COOLING_DOWN", "RATE_LIMITED", "AUTH_REQUIRED",
})
_FALLBACK_ELIGIBLE_STATUSES = frozenset({"PROVIDER_UNAVAILABLE", "CONNECTIVITY_FAILURE"})
_PROVENANCE_KEYS = frozenset({
    "requested_source_url", "final_source_url", "redirect_chain",
    "resolution_trace", "source_access_mode", "commercial_license_state",
    "original_body_available", "index_only", "requires_auth", "cookies_used",
})


def _canonical_platform(platform: str) -> str:
    key = str(platform or "").strip().lower()
    return _PLATFORM_ALIASES.get(key, key)


def _is_public_post_url(value: Any) -> bool:
    try:
        parsed = urlsplit(str(value or ""))
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme.lower() == "https"
        and parsed.hostname in {"instagram.com", "www.instagram.com"}
        and port in (None, 443)
        and re.fullmatch(r"/(?:p|reel|tv)/[A-Za-z0-9_-]+/?", parsed.path) is not None
        and not parsed.username and not parsed.password
    )


def _is_http_url(value: Any) -> bool:
    """Recognize URL-shaped inputs so they cannot fall through as search text."""
    # Syntax errors (for example an unmatched IPv6 bracket) do not turn an
    # attempted URL into a topic query for an authenticated session worker.
    return re.match(r"^https?://", str(value or "").strip(), re.IGNORECASE) is not None


def _is_wechat_article_url(value: Any) -> bool:
    try:
        parsed = urlsplit(str(value or ""))
        query = parse_qs(parsed.query)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme.lower() == "https"
        and parsed.hostname == "mp.weixin.qq.com"
        and port in (None, 443)
        and not parsed.username and not parsed.password
        and (
            re.fullmatch(r"/s/[A-Za-z0-9_-]{1,256}/?", parsed.path) is not None
            or (parsed.path == "/s" and bool(query.get("__biz") and query.get("mid")))
        )
    )


def _route_matches(route: CapabilityRoute, request_value: Any) -> bool:
    if route.selector == "any":
        return True
    is_url = _is_http_url(request_value)
    is_public_post = _is_public_post_url(request_value)
    is_wechat_url = _is_wechat_article_url(request_value)
    if route.selector == "public_post_url":
        return is_public_post
    if route.selector == "wechat_article_url":
        return is_wechat_url
    if route.selector == "query":
        return bool(str(request_value or "").strip()) and not is_url
    if route.selector == "opaque_content_id":
        return re.fullmatch(r"[A-Za-z0-9_-]{1,128}", str(request_value or "").strip()) is not None
    if route.selector == "profile_identifier":
        return re.fullmatch(r"[A-Za-z0-9._-]{1,128}", str(request_value or "").strip()) is not None
    return False


def resolve_capability_route(
    platform: str,
    capability: str,
    *,
    request_value: Any = None,
) -> CapabilityRoute | None:
    """Resolve the exact existing adapter path for one capability call."""
    key = _canonical_platform(platform)
    candidates = sorted(
        (route for route in CAPABILITY_ROUTES
         if route.platform == key and route.capability == str(capability or "").lower()),
        key=lambda route: route.order,
    )
    return next((route for route in candidates if _route_matches(route, request_value)), None)


def select_explicit_fallback(
    current: CapabilityRoute,
    *,
    outcome_status: str,
    routes: Sequence[CapabilityRoute] = CAPABILITY_ROUTES,
    permission_allows: Any = None,
) -> CapabilityRoute | None:
    """Return only a declared, specifically authorized safe fallback route.

    No fallback is currently declared for the production paths. In particular,
    challenge, login, risk and rate-limit states can never trigger a different
    backend or identity.
    """
    status = str(outcome_status or "").upper()
    if status in _STOP_FALLBACK_STATUSES or status not in _FALLBACK_ELIGIBLE_STATUSES:
        return None
    if not current.fallback_route_ids or not callable(permission_allows):
        return None
    candidates = [route for route in routes
                  if route.route_id in current.fallback_route_ids
                  and route.platform == current.platform
                  and route.capability == current.capability]
    for candidate in sorted(candidates, key=lambda route: route.order):
        # The existing Permission owner performs this exact route check. This
        # helper never treats an ID/string or source failure as authorization.
        if permission_allows(candidate) is True:
            return candidate
    return None


def _safe_source_url(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parts = urlsplit(raw)
        if parts.scheme.lower() in {"http", "https"} and parts.hostname:
            host = parts.hostname
            if ":" in host:
                host = f"[{host}]"
            if parts.port:
                host = f"{host}:{parts.port}"
            return urlunsplit((parts.scheme, host, parts.path, "", ""))[:500]
    except ValueError:
        return None
    return raw[:180]


def _platform_identity(value: Any) -> str:
    """Normalize known platform aliases while preserving unknown IDs for comparison."""
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    try:
        from .platform_naming import normalize_platform

        return normalize_platform(raw) or raw
    except Exception:
        return _canonical_platform(raw)


def _validate_result_identity(result: CollectionResult, platform: str, *, route: CapabilityRoute | None) -> None:
    expected = _platform_identity(platform)
    actual = _platform_identity(result.platform)
    if not actual or actual != expected:
        raise RouteIdentityMismatch("adapter result platform does not match the requested platform")
    items = result.items if isinstance(result.items, list) else []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        for field in ("source_platform", "platform"):
            declared = item.get(field)
            if declared not in (None, "") and _platform_identity(declared) != expected:
                raise RouteIdentityMismatch(f"adapter item {field} does not match its platform")
    if route is None:
        return
    if result.access_class is not None:
        try:
            observed_access = AccessClass(result.access_class)
        except (TypeError, ValueError):
            raise RouteIdentityMismatch("adapter returned an unknown access class") from None
        if observed_access is not route.access_class:
            raise RouteIdentityMismatch("adapter access class contradicts the selected route")
    metadata = result.metadata if isinstance(result.metadata, Mapping) else {}
    if route.access_class is AccessClass.Z0_PUBLIC:
        mode = str(metadata.get("source_access_mode") or "").strip().lower()
        if mode in {"authorized_session", "session", "authenticated_session", "z1"}:
            raise RouteIdentityMismatch("public route returned session-only access metadata")
        if metadata.get("requires_auth") is True or metadata.get("cookies_used") is True:
            raise RouteIdentityMismatch("public route returned authenticated-access metadata")
    elif route.access_class is AccessClass.Z1_AUTHORIZED_SESSION:
        mode = str(metadata.get("source_access_mode") or "").strip().lower()
        if mode in {"public", "public_read_only", "anonymous", "z0"}:
            raise RouteIdentityMismatch("session route returned anonymous-access metadata")


def bind_collection_route(
    result: CollectionResult,
    *,
    platform: str,
    capability: str,
    request_value: Any = None,
) -> CollectionResult:
    """Attach selected route and safe source lineage to a returned result."""
    route = resolve_capability_route(platform, capability, request_value=request_value)
    _validate_result_identity(result, platform, route=route)
    result.capability = str(capability or "").lower() or None
    metadata = result.metadata if isinstance(result.metadata, Mapping) else {}
    observed_provider = metadata.get("provider") or metadata.get("engine") or result.backend
    if result.backend is None and observed_provider:
        result.backend = str(observed_provider)[:100]
    result.attempted_access_class = route.access_class if route else None
    result.attempted_backend = route.backend if route else None
    result.actual_access_state = (
        "ITEMS_ACQUIRED" if result.items or result.comments else
        "READ_COMPLETED_EMPTY" if result.ok else
        "ATTEMPTED_ONLY"
    )
    if route is None:
        result.route_id = None
        provenance = dict(result.provenance) if isinstance(result.provenance, Mapping) else {}
        provenance.update({
            "route_state": "UNKNOWN",
            "fallback_policy": "explicit_authorization_required",
            "requested_platform": str(platform)[:80],
            "source_platform": str(result.platform)[:80],
            "actual_access_state": result.actual_access_state,
        })
        if observed_provider:
            provenance["provider"] = str(observed_provider)[:100]
        source = _safe_source_url(metadata.get("source"))
        if source:
            provenance["source"] = source
        if metadata.get("collected_at"):
            provenance["collected_at"] = str(metadata["collected_at"])[:40]
        if metadata.get("error_type"):
            provenance["error_type"] = str(metadata["error_type"])[:80]
        result.provenance = provenance
        return result

    result.route_id = route.route_id
    completed_read = result.ok or bool(result.items) or bool(result.comments)
    result.access_class = route.access_class if completed_read else None
    provenance = dict(result.provenance) if isinstance(result.provenance, Mapping) else {}
    provenance.update({
        "route_state": "RESOLVED",
        "route_id": route.route_id,
        "requested_platform": str(platform)[:80],
        "source_platform": str(result.platform)[:80],
        "route_platform": route.platform,
        "capability": route.capability,
        "attempted_access_class": route.access_class.value,
        "attempted_backend": route.backend,
        "actual_access_class": result.access_class.value if result.access_class else None,
        "actual_access_state": result.actual_access_state,
        "route_order": route.order,
        "authorization_contract": route.authorization_contract,
        "fallback_policy": "explicit_authorization_required",
        "fallback_route_ids": list(route.fallback_route_ids),
    })
    for key in _PROVENANCE_KEYS:
        value = metadata.get(key)
        if value is None or isinstance(value, (dict, list)) and not value:
            continue
        if key in {"requested_source_url", "final_source_url"}:
            safe_value = _safe_source_url(value)
            if safe_value:
                provenance[key] = safe_value
        elif key in {"redirect_chain", "resolution_trace"}:
            if isinstance(value, (str, int, float, bool)):
                provenance[key] = value
        elif isinstance(value, (str, int, float, bool)):
            provenance[key] = value
    if observed_provider:
        provenance["provider"] = str(observed_provider)[:100]
    provenance["access_class"] = result.access_class.value if result.access_class else None
    if result.backend:
        provenance["backend"] = str(result.backend)[:100]
    source = _safe_source_url(
        metadata.get("source") or metadata.get("final_source_url")
    )
    if source:
        provenance["source"] = source
    if metadata.get("collected_at"):
        provenance["collected_at"] = str(metadata["collected_at"])[:40]
    if metadata.get("error_type"):
        provenance["error_type"] = str(metadata["error_type"])[:80]
    result.provenance = provenance
    return result
