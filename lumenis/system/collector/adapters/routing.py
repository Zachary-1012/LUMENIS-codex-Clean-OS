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
    provider_mode: str | None = None
    public_transport: str | None = None


def _route(route_id: str, platform: str, capability: str, order: int,
           access_class: AccessClass, backend: str, *, selector: str = "any",
           authorization_contract: str = "none",
           fallback_route_ids: tuple[str, ...] = (),
           provider_mode: str | None = None, public_transport: str | None = None) -> CapabilityRoute:
    return CapabilityRoute(
        route_id, platform, capability, order, access_class, backend,
        selector, authorization_contract, fallback_route_ids, provider_mode, public_transport,
    )


# This is a projection of currently implemented adapter paths, not a list of
# planned providers. An implemented Z2 path still requires its existing official
# API credentials/scopes and does not establish configured or live access.
CAPABILITY_ROUTES: tuple[CapabilityRoute, ...] = (
    *(_route('weibo.' + capability + '.session','weibo',capability,1,
             AccessClass.Z1_AUTHORIZED_SESSION,'weibo_first_party_read_api',
             authorization_contract='existing_platform_session')
      for capability in ('search','detail','comments','creator','author_posts')),
    *(_route('zhihu.' + capability + '.public', 'zhihu', capability, 1,
             AccessClass.Z0_PUBLIC, 'zhihu_first_party_read_api')
      for capability in ('search','detail','comments','creator','author_posts')),
    *(_route('bilibili.' + capability + '.public', 'bilibili', capability, 1,
             AccessClass.Z0_PUBLIC, 'bilibili_first_party_read_api')
      for capability in ('search', 'detail', 'comments', 'creator', 'author_posts')),
    *(_route('tieba.' + capability + '.public', 'tieba', capability, 1,
             AccessClass.Z0_PUBLIC, 'tieba_public_html',provider_mode='public',public_transport='http')
      for capability in ('search', 'detail', 'comments', 'creator', 'author_posts')),
    _route('google.search.public-browser', 'google', 'search', 1,
           AccessClass.Z0_PUBLIC, 'registered_google_discovery', selector='query',
           authorization_contract='existing_registered_readonly_browser_worker'),
    *(_route('github.' + capability + '.official', 'github', capability, 1,
             AccessClass.Z2_OFFICIAL_API, 'github_app_user_authorization',
             authorization_contract='existing_github_user_authorization_and_repository_endpoint_allowlists',provider_mode='official')
      for capability in ('search', 'detail', 'comments')),
    *(_route('youtube.' + capability + '.official', 'youtube', capability, 1,
             AccessClass.Z2_OFFICIAL_API, 'youtube_data_api_v3',
             authorization_contract='existing_authorized_youtube_data_api_v3_key_and_actual_quota',
             provider_mode='official')
      for capability in ('search', 'detail', 'comments', 'creator', 'author_posts')),
    *(_route('reddit.' + capability + '.official', 'reddit', capability, 1,
             AccessClass.Z2_OFFICIAL_API, 'reddit_official_oauth',
             authorization_contract='approved_reddit_api_purpose_and_oauth_read_scope',
             provider_mode='official')
      for capability in ('search', 'detail', 'comments', 'creator', 'author_posts')),
    *(_route('linkedin.' + capability + '.official', 'linkedin', capability, 1,
             AccessClass.Z2_OFFICIAL_API, 'linkedin_official_rest',
             authorization_contract='existing_linkedin_official_rest_authorized_resources',
             provider_mode='official')
      for capability in ('detail', 'comments', 'creator', 'author_posts', 'media_detail')),
    *(_route(platform + '.' + capability + '.public', platform, capability, 1,
             AccessClass.Z0_PUBLIC, backend, provider_mode='public',public_transport='http',
             authorization_contract='public_document_current_source_permission')
      for platform, backend in (('youtube', 'youtube_public_document'),
                                ('reddit', 'reddit_public_document'),
                                ('linkedin', 'linkedin_public_document'),
                                ('channels', 'channels_public_document'))
      for capability in ('search', 'detail', 'comments', 'creator', 'author_posts')),
    *(_route(platform + '.' + capability + '.public-browser', platform, capability, 1,
             AccessClass.Z0_PUBLIC, platform + '_public_browser',provider_mode='public',public_transport='browser',
             authorization_contract='anonymous_registered_browser_public_source_permission')
      for platform in ('youtube','reddit','linkedin','channels','tieba')
      for capability in ('search','detail','comments','creator','author_posts')),
    *(_route(platform + '.' + capability + '.public',platform,capability,1,
             AccessClass.Z0_PUBLIC,'safe_public_http',provider_mode='public',public_transport='http')
      for platform in ('naver','daum')
      for capability in ('search','detail','comments','creator','author_posts')),
    *(_route(platform + '.' + capability + '.session', platform, capability, 1,
             AccessClass.Z1_AUTHORIZED_SESSION, 'registered_browser_native_read',
             authorization_contract='existing_platform_session')
      for platform in ('tiktok', 'kuaishou')
      for capability in ('search', 'detail', 'comments', 'creator', 'author_posts')),
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
    _route("instagram.author_posts.session", "instagram", "author_posts", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "v4_instagram",
           selector="profile_identifier", authorization_contract="existing_platform_session"),
    _route("xhs.search.session", "xiaohongshu", "search", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "existing_collector.search_xiaohongshu",
           authorization_contract="existing_platform_session"),
    _route("xhs.detail.session", "xiaohongshu", "detail", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "existing_collector.detail_xiaohongshu",
           authorization_contract="existing_platform_session"),
    _route("xhs.comments.session", "xiaohongshu", "comments", 1,
           AccessClass.Z1_AUTHORIZED_SESSION, "existing_collector.collect_native_xiaohongshu",
           authorization_contract="existing_platform_session"),
    *(_route('xhs.' + capability + '.session', 'xiaohongshu', capability, 1,
             AccessClass.Z1_AUTHORIZED_SESSION, 'existing_collector.collect_native_xiaohongshu',
             authorization_contract='existing_platform_session')
      for capability in ('creator', 'author_posts')),
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
    _route('douyin.author_posts.session', 'douyin', 'author_posts', 1,
           AccessClass.Z1_AUTHORIZED_SESSION, 'lumenis.adapters.douyin.DouyinAdapter',
           authorization_contract='existing_platform_session'),
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
    _route('facebook.author_posts.session', 'facebook', 'author_posts', 1,
           AccessClass.Z1_AUTHORIZED_SESSION, 'lumenis.adapters.facebook.FacebookAdapter',
           authorization_contract='existing_platform_session'),
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
    _route('x.author_posts.session', 'x', 'author_posts', 1,
           AccessClass.Z1_AUTHORIZED_SESSION, 'lumenis.adapters.x_platform.XAdapter',
           authorization_contract='existing_platform_session'),
)

_PLATFORM_ALIASES = {"xhs": "xiaohongshu", "rednote": "xiaohongshu"}
_PROVIDER_MODE_PLATFORMS = frozenset({'youtube', 'reddit', 'linkedin', 'channels'})
_PUBLIC_TRANSPORT_PLATFORMS = frozenset({'youtube','reddit','linkedin','channels','tieba','naver','daum'})
_MODE_SELECTION_PLATFORMS = _PUBLIC_TRANSPORT_PLATFORMS | {'github'}
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
    from .platform_naming import normalize_platform
    return normalize_platform(key) or _PLATFORM_ALIASES.get(key, key)


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
    provider_mode: str | None = None,
    public_transport: str | None = None,
) -> CapabilityRoute | None:
    """Resolve the exact existing adapter path for one capability call."""
    key = _canonical_platform(platform)
    mode = (provider_mode or ('official' if key=='github' else 'public')) if key in _MODE_SELECTION_PLATFORMS else None
    transport = (public_transport or 'http') if key in _PUBLIC_TRANSPORT_PLATFORMS and mode=='public' else None
    capability = str(capability or "").strip().lower()
    if capability == 'author':
        capability = 'creator'
    candidates = sorted(
        (route for route in CAPABILITY_ROUTES
         if route.platform == key and route.capability == capability
         and (route.provider_mode is None or route.provider_mode == mode)
         and (route.public_transport is None or route.public_transport == transport)),
        key=lambda route: route.order,
    )
    return next((route for route in candidates if _route_matches(route, request_value)), None)


def normalize_provider_selection(platform, *, provider_mode=None, public_transport=None):
    """Resolve explicit/server defaults once, then pin these in the request.

    This configuration projection supplies no Permission or session. A saved
    task reuses its explicit values instead of reading changing server defaults.
    """
    from .config import get_platform_capabilities
    if provider_mode is not None and (type(provider_mode) is not str or provider_mode not in {'public','official'}):
        raise ValueError('COLLECTION_PROVIDER_MODE_NOT_SUPPORTED')
    if public_transport is not None and (type(public_transport) is not str or public_transport not in {'http','browser'}):
        raise ValueError('COLLECTION_PUBLIC_TRANSPORT_NOT_SUPPORTED')
    key = _canonical_platform(platform)
    capabilities = get_platform_capabilities(key)
    modes = capabilities.get('provider_modes')
    if not modes:
        if provider_mode is not None or public_transport is not None:
            raise ValueError('COLLECTION_PROVIDER_SELECTION_NOT_SUPPORTED')
        return {}
    from config import get_config
    configured = get_config()
    mode = provider_mode if provider_mode is not None else configured.get('LUMENIS_'+key.upper()+'_PROVIDER_MODE')
    mode = capabilities.get('default_provider_mode','public') if mode in (None,'') else mode
    if type(mode) is not str or mode not in modes:
        raise ValueError('COLLECTION_PROVIDER_MODE_NOT_SUPPORTED')
    if mode != 'public':
        if public_transport not in (None,'http'):
            raise ValueError('COLLECTION_OFFICIAL_PROVIDER_CANNOT_USE_PUBLIC_BROWSER')
        return {'provider_mode':mode}
    transport = public_transport if public_transport is not None else configured.get('LUMENIS_'+key.upper()+'_PUBLIC_TRANSPORT')
    transport = capabilities.get('default_public_transport','http') if transport in (None,'') else transport
    if type(transport) is not str or transport not in capabilities.get('public_transports',('http',)):
        raise ValueError('COLLECTION_PUBLIC_TRANSPORT_NOT_SUPPORTED')
    return {'provider_mode':mode,'public_transport':transport}


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
    provider_mode: str | None = None,
    public_transport: str | None = None,
) -> CollectionResult:
    """Attach selected route and safe source lineage to a returned result."""
    metadata = result.metadata if isinstance(result.metadata, Mapping) else {}
    selected_mode = provider_mode
    mode_platform = _canonical_platform(platform) in _MODE_SELECTION_PLATFORMS
    selected_transport = public_transport
    if mode_platform:
        observed_mode = metadata.get('provider_mode')
        if observed_mode is not None and observed_mode not in {'public', 'official'}:
            raise RouteIdentityMismatch('adapter returned an unknown provider mode')
        if selected_mode is not None and selected_mode not in {'public', 'official'}:
            raise RouteIdentityMismatch('requested provider mode is unknown')
        if selected_mode and observed_mode and selected_mode != observed_mode:
            raise RouteIdentityMismatch('adapter provider mode contradicts the selected provider')
        selected_mode = selected_mode or observed_mode
        if selected_mode is None and result.attempted_backend:
            modes = {candidate.provider_mode for candidate in CAPABILITY_ROUTES
                     if candidate.platform == _canonical_platform(platform)
                     and candidate.backend == result.attempted_backend and candidate.provider_mode}
            if len(modes) == 1:
                selected_mode = modes.pop()
        observed_transport = metadata.get('public_transport')
        if observed_transport is not None and observed_transport not in {'http','browser'}:
            raise RouteIdentityMismatch('adapter returned an unknown public transport')
        if selected_transport is not None and selected_transport not in {'http','browser'}:
            raise RouteIdentityMismatch('requested public transport is unknown')
        if selected_transport and observed_transport and selected_transport != observed_transport:
            raise RouteIdentityMismatch('adapter transport contradicts the selected transport')
        selected_transport = selected_transport or observed_transport
        if selected_transport is None and result.attempted_backend:
            transports = {candidate.public_transport for candidate in CAPABILITY_ROUTES
                if candidate.platform == _canonical_platform(platform) and candidate.backend == result.attempted_backend
                and candidate.public_transport}
            if len(transports)==1:
                selected_transport = transports.pop()
    route = resolve_capability_route(platform, capability, request_value=request_value,
                                     provider_mode=selected_mode,public_transport=selected_transport)
    _validate_result_identity(result, platform, route=route)
    if mode_platform and route:
        if (result.attempted_backend is not None and result.attempted_backend != route.backend):
            raise RouteIdentityMismatch('adapter attempted backend contradicts its provider mode')
        if (result.attempted_access_class is not None
                and result.attempted_access_class != route.access_class):
            raise RouteIdentityMismatch('adapter attempted access class contradicts its provider mode')
    if mode_platform and route is None and (result.items or result.comments):
        raise RouteIdentityMismatch('unsupported provider capability returned content')
    result.capability = str(capability or "").lower() or None
    observed_provider = metadata.get("provider") or metadata.get("engine") or result.backend
    source_observed = bool(result.original_response) and result.access_class is not None
    configuration_only = (metadata.get('network_attempted') is False
                          or metadata.get('authorization_verification') == 'NOT_VERIFIED')
    completed_read = (bool(result.items or result.comments) or source_observed
                      or (result.ok and not configuration_only
                          and result.actual_access_state not in {'NOT_OBSERVED', 'NOT_ATTEMPTED'}))
    if result.backend is None and observed_provider and completed_read:
        result.backend = str(observed_provider)[:100]
    if not completed_read:
        result.backend = None
        result.access_class = None
    if route:
        result.attempted_access_class = route.access_class
        result.attempted_backend = route.backend
    result.actual_access_state = (
        "ITEMS_ACQUIRED" if result.items or result.comments else
        "READ_COMPLETED_EMPTY" if completed_read and result.ok else
        "SOURCE_OBSERVED" if source_observed else
        "NOT_ATTEMPTED" if configuration_only or result.actual_access_state == 'NOT_ATTEMPTED' else
        "NOT_OBSERVED" if result.actual_access_state == 'NOT_OBSERVED' else 'ATTEMPTED_ONLY'
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
            "provider_mode": selected_mode,
            "public_transport": selected_transport,
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
        "provider_mode": route.provider_mode,
        "public_transport": route.public_transport,
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
