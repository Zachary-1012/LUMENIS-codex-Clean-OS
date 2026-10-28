from __future__ import annotations

import pytest

from lumenis.system.collector.adapters.base import AccessClass, CollectionResult, CollectionStatus
from lumenis.system.collector.adapters.routing import (
    CapabilityRoute,
    CAPABILITY_ROUTES,
    bind_collection_route,
    resolve_capability_route,
    select_explicit_fallback,
)


def test_primary_platform_routes_preserve_public_and_authorized_session_boundaries():
    public_wechat = resolve_capability_route("wechat", "search", request_value="brand")
    public_instagram = resolve_capability_route(
        "instagram", "detail", request_value="https://www.instagram.com/p/ABC123/",
    )
    session_instagram = resolve_capability_route(
        "instagram", "search", request_value="brand name",
    )
    xhs = resolve_capability_route("xhs", "search", request_value="brand")
    douyin = resolve_capability_route("douyin", "search", request_value="brand")
    facebook = resolve_capability_route("facebook", "detail", request_value="post-123")
    x_route = resolve_capability_route("x", "search", request_value="brand")

    assert public_wechat.access_class is AccessClass.Z0_PUBLIC
    assert public_instagram.access_class is AccessClass.Z0_PUBLIC
    assert session_instagram.access_class is AccessClass.Z1_AUTHORIZED_SESSION
    assert session_instagram.authorization_contract == "existing_platform_session"
    assert xhs.access_class is AccessClass.Z1_AUTHORIZED_SESSION
    assert xhs.backend == "existing_collector.search_xiaohongshu"
    assert douyin.access_class is AccessClass.Z1_AUTHORIZED_SESSION
    assert facebook.access_class is AccessClass.Z1_AUTHORIZED_SESSION
    assert x_route.access_class is AccessClass.Z1_AUTHORIZED_SESSION
    wechat_query = resolve_capability_route("wechat", "search", request_value="brand")
    wechat_article = resolve_capability_route(
        "wechat", "search", request_value="https://mp.weixin.qq.com/s/example",
    )
    assert wechat_query.backend == "public_sogou_discovery_original_fetch"
    assert wechat_article.backend == "public_original_article_fetch"
    assert not any("opencli" in route.backend.lower() for route in CAPABILITY_ROUTES)
    assert {route.platform for route in CAPABILITY_ROUTES
            if route.access_class is AccessClass.Z2_OFFICIAL_API} == {'github','youtube','reddit','linkedin'}


def test_url_selectors_do_not_reclassify_arbitrary_urls_as_session_queries_or_article_ids():
    assert resolve_capability_route(
        "instagram", "search", request_value="https://attacker.example/posts/1",
    ) is None
    assert resolve_capability_route(
        "instagram", "detail", request_value="https://attacker.example/p/ABC123",
    ) is None
    assert resolve_capability_route(
        "instagram", "comments", request_value="https://www.instagram.com/p/ABC123/",
    ) is None
    assert resolve_capability_route(
        "instagram", "creator", request_value="https://www.instagram.com/example/",
    ) is None
    assert resolve_capability_route(
        "instagram", "detail", request_value="ABC_123-x",
    ).access_class is AccessClass.Z1_AUTHORIZED_SESSION
    assert resolve_capability_route(
        "instagram", "detail", request_value="https://www.instagram.com:444/p/ABC123/",
    ) is None
    assert resolve_capability_route(
        "instagram", "detail", request_value="https://www.instagram.com:bad/p/ABC123/",
    ) is None

    assert resolve_capability_route(
        "wechat", "search", request_value="https://weixin.sogou.com/weixin?query=brand",
    ) is None
    assert resolve_capability_route(
        "wechat", "detail", request_value="https://weixin.sogou.com/article/1",
    ) is None
    assert resolve_capability_route(
        "wechat", "detail", request_value="https://mp.weixin.qq.com/not-an-article",
    ) is None
    assert resolve_capability_route(
        "wechat", "detail", request_value="https://mp.weixin.qq.com:bad/s/article",
    ) is None
    assert resolve_capability_route(
        "wechat", "detail", request_value="https://mp.weixin.qq.com:notaport/s/article",
    ) is None
    assert resolve_capability_route(
        "wechat", "detail", request_value="https://mp.weixin.qq.com/s/article_123",
    ).access_class is AccessClass.Z0_PUBLIC


def test_access_route_rejects_challenge_fallback_and_requires_exact_authorized_route():
    current = resolve_capability_route("instagram", "search", request_value="brand")
    assert current is not None
    fallback = CapabilityRoute(
        "instagram.search.explicit-fallback", "instagram", "search", 3,
        AccessClass.Z0_PUBLIC, "approved_public_source",
    )
    declared = CapabilityRoute(
        current.route_id, current.platform, current.capability, current.order,
        current.access_class, current.backend, current.selector,
        current.authorization_contract, (fallback.route_id,),
    )
    assert select_explicit_fallback(
        declared,
        outcome_status="NEED_VERIFY",
        routes=[fallback],
        permission_allows=lambda _route: True,
    ) is None
    assert select_explicit_fallback(
        declared,
        outcome_status="PROVIDER_UNAVAILABLE",
        routes=[fallback],
        permission_allows=None,
    ) is None
    assert select_explicit_fallback(
        declared,
        outcome_status="PROVIDER_UNAVAILABLE",
        routes=[fallback],
        permission_allows=lambda _route: True,
    ) == fallback


def test_collection_result_carries_safe_route_provenance_without_url_query_secrets():
    result = CollectionResult(
        status=CollectionStatus.SUCCESS,
        platform="public_http",
        items=[],
        metadata={
            "provider": "public_http",
            "source": "https://public.example.test/article?token=secret#fragment",
            "requested_source_url": "https://public.example.test/article?token=secret",
            "final_source_url": "https://public.example.test/article?session=secret",
            "source_access_mode": "public_read_only",
            "commercial_license_state": "pending_review",
        },
    )

    bound = bind_collection_route(
        result,
        platform="public_http",
        capability="search",
        request_value="https://public.example.test/article?request=secret",
    )

    assert bound.access_class is AccessClass.Z0_PUBLIC
    assert bound.route_id == "public-http.search"
    assert bound.backend == "public_http"
    assert bound.provenance["source_access_mode"] == "public_read_only"
    assert bound.provenance["requested_source_url"] == "https://public.example.test/article"
    assert bound.provenance["final_source_url"] == "https://public.example.test/article"
    assert bound.provenance["source"] == "https://public.example.test/article"
    assert "secret" not in repr(bound.provenance)

    unknown = bind_collection_route(
        CollectionResult(
            status=CollectionStatus.SUCCESS,
            platform="bilibili",
            metadata={"source": "https://example.test/item?token=secret"},
        ),
        platform="bilibili",
        capability="search",
        request_value="term",
    )
    assert unknown.access_class is AccessClass.Z0_PUBLIC
    assert unknown.provenance["route_state"] == "RESOLVED"
    assert unknown.attempted_backend == 'bilibili_first_party_read_api'
    assert unknown.backend is None  # Planned route is not an observed provider.
    assert unknown.provenance["source"] == "https://example.test/item"
    assert "secret" not in repr(unknown.provenance)


def test_route_provenance_separates_attempt_from_actual_provider_and_rejects_identity_drift():
    from lumenis.system.collector.adapters.routing import RouteIdentityMismatch

    success = CollectionResult(
        status=CollectionStatus.SUCCESS,
        platform="instagram",
        items=[{"source_platform": "instagram", "id": "1"}],
        metadata={"engine": "actual-instagram-engine"},
    )
    bound = bind_collection_route(
        success, platform="instagram", capability="search", request_value="brand",
    )
    assert bound.attempted_access_class is AccessClass.Z1_AUTHORIZED_SESSION
    assert bound.attempted_backend == "v4_instagram"
    assert bound.access_class is AccessClass.Z1_AUTHORIZED_SESSION
    assert bound.backend == "actual-instagram-engine"
    assert bound.provenance["attempted_backend"] == "v4_instagram"
    assert bound.provenance["provider"] == "actual-instagram-engine"
    assert bound.provenance["actual_access_class"] == "Z1"
    assert bound.provenance["actual_access_state"] == "ITEMS_ACQUIRED"

    failed = bind_collection_route(
        CollectionResult(
            status=CollectionStatus.PROVIDER_UNAVAILABLE,
            platform="instagram",
            metadata={},
        ),
        platform="instagram", capability="search", request_value="brand",
    )
    assert failed.attempted_access_class is AccessClass.Z1_AUTHORIZED_SESSION
    assert failed.attempted_backend == "v4_instagram"
    assert failed.access_class is None
    assert failed.backend is None
    assert failed.provenance["actual_access_class"] is None
    assert failed.provenance["actual_access_state"] == "ATTEMPTED_ONLY"
    assert "provider" not in failed.provenance

    with pytest.raises(RouteIdentityMismatch):
        bind_collection_route(
            CollectionResult(CollectionStatus.SUCCESS, "x"),
            platform="instagram", capability="search", request_value="brand",
        )
    with pytest.raises(RouteIdentityMismatch):
        bind_collection_route(
            CollectionResult(
                CollectionStatus.SUCCESS, "instagram",
                items=[{"source_platform": "x", "id": "1"}],
            ),
            platform="instagram", capability="search", request_value="brand",
        )
    with pytest.raises(RouteIdentityMismatch):
        bind_collection_route(
            CollectionResult(
                CollectionStatus.SUCCESS, "instagram",
                metadata={"source_access_mode": "public_read_only"},
            ),
            platform="instagram", capability="search", request_value="brand",
        )


def test_health_does_not_report_configuration_as_live_success():
    from lumenis.system.collector.adapters.sitemap import SitemapAdapter
    from lumenis.system.collector.adapters.web_rss import WebRSSAdapter

    assert WebRSSAdapter().health_check().status is CollectionStatus.NEED_VERIFY
    sitemap = SitemapAdapter().health_check(url="https://public.example.test/sitemap.xml")
    assert sitemap.status is CollectionStatus.NEED_VERIFY
    assert sitemap.metadata["healthcheck_scope"] == "collection_required"


@pytest.mark.parametrize('platform,backend,access,capabilities', [
    ('google','registered_google_discovery',AccessClass.Z0_PUBLIC,('search',)),
    ('github','github_app_user_authorization',AccessClass.Z2_OFFICIAL_API,('search','detail','comments')),
    ('tieba','tieba_public_html',AccessClass.Z0_PUBLIC,('search','detail','comments','creator','author_posts')),
    ('youtube','youtube_data_api_v3',AccessClass.Z2_OFFICIAL_API,('search','detail','comments','creator','author_posts')),
    ('reddit','reddit_official_oauth',AccessClass.Z2_OFFICIAL_API,('search','detail','comments','creator','author_posts')),
    ('linkedin','linkedin_official_rest',AccessClass.Z2_OFFICIAL_API,('detail','comments','creator','author_posts','media_detail')),
    ('tiktok','registered_browser_native_read',AccessClass.Z1_AUTHORIZED_SESSION,('search','detail','comments','creator','author_posts')),
    ('kuaishou','registered_browser_native_read',AccessClass.Z1_AUTHORIZED_SESSION,('search','detail','comments','creator','author_posts')),
])
def test_verified_implementation_routes_keep_actual_access_unverified_on_failure(platform,backend,access,capabilities):
    mode = 'official' if platform in {'youtube','reddit','linkedin'} else None
    for capability in capabilities:
        route = resolve_capability_route(platform,capability,request_value='fixture-query',provider_mode=mode)
        assert route is not None and route.backend == backend and route.access_class is access
        assert not route.fallback_route_ids
        failed = bind_collection_route(CollectionResult(CollectionStatus.NOT_CONFIGURED,platform),
            platform=platform,capability=capability,request_value='fixture-query',provider_mode=mode)
        assert failed.attempted_backend == backend and failed.attempted_access_class is access
        assert failed.access_class is None and failed.backend is None
        assert failed.actual_access_state == 'ATTEMPTED_ONLY'
    assert resolve_capability_route(platform,'media',request_value='fixture-query') is None


def test_not_supported_boundaries_and_existing_aliases_remain_exact():
    for capability in ('search','detail','comments','creator','author_posts'):
        assert resolve_capability_route('channels',capability,request_value='fixture',provider_mode='official') is None
    assert resolve_capability_route('linkedin','search',request_value='fixture',provider_mode='official') is None
    assert resolve_capability_route('linkedin','media_detail',request_value='fixture') is None
    for capability in ('detail','comments','creator','author_posts'):
        assert resolve_capability_route('google',capability,request_value='fixture') is None
    assert resolve_capability_route('github','author_posts',request_value='fixture') is None
    assert resolve_capability_route('yt','author',request_value='UCfixture').platform == 'youtube'
    assert resolve_capability_route('谷歌','search',request_value='fixture').platform == 'google'


@pytest.mark.parametrize('platform', ['youtube', 'reddit', 'linkedin', 'channels'])
def test_public_provider_is_default_and_binding_preserves_actual_provider_facts(platform):
    backend = platform + '_public_document'
    for capability in ('search','detail','comments','creator','author_posts'):
        route = resolve_capability_route(platform,capability,request_value='fixture')
        assert route.backend == backend and route.access_class is AccessClass.Z0_PUBLIC
        assert route.provider_mode == 'public' and route.fallback_route_ids == ()
    failure = CollectionResult(CollectionStatus.NEED_VERIFY, platform,
        metadata={'provider':backend,'provider_mode':'public'}, attempted_backend=backend,
        attempted_access_class=AccessClass.Z0_PUBLIC, actual_access_state='NOT_OBSERVED')
    bound = bind_collection_route(failure,platform=platform,capability='detail',request_value='fixture')
    assert bound.route_id == platform + '.detail.public'
    assert bound.attempted_backend == backend and bound.backend is None and bound.access_class is None
    assert bound.actual_access_state == 'NOT_OBSERVED'
    assert select_explicit_fallback(route,outcome_status='NEED_VERIFY',permission_allows=lambda _:True) is None

    # A fetched document with unavailable native fields proves public access,
    # while its unsuccessful parse remains unsuccessful and keeps that scope.
    observed = CollectionResult(CollectionStatus.PROVIDER_UNAVAILABLE, platform,
        metadata={'provider':backend,'provider_mode':'public'}, attempted_backend=backend,
        attempted_access_class=AccessClass.Z0_PUBLIC, backend=backend,
        access_class=AccessClass.Z0_PUBLIC, original_response=[object()],
        actual_access_state='SOURCE_OBSERVED')
    bound = bind_collection_route(observed,platform=platform,capability='detail',request_value='fixture')
    assert bound.access_class is AccessClass.Z0_PUBLIC and bound.backend == backend
    assert bound.actual_access_state == 'SOURCE_OBSERVED' and not bound.ok


def test_explicit_provider_mode_cannot_relabel_or_fallback_after_adapter_result():
    from lumenis.system.collector.adapters.routing import RouteIdentityMismatch
    result = CollectionResult(CollectionStatus.BLOCKED,'youtube',
        metadata={'provider_mode':'public','provider':'youtube_public_document'},
        attempted_backend='youtube_public_document',attempted_access_class=AccessClass.Z0_PUBLIC)
    with pytest.raises(RouteIdentityMismatch,match='provider mode'):
        bind_collection_route(result,platform='youtube',capability='search',provider_mode='official')
    result.metadata['provider_mode'] = 'official'
    with pytest.raises(RouteIdentityMismatch,match='attempted backend'):
        bind_collection_route(result,platform='youtube',capability='search')
    result.metadata['provider_mode'] = 'invalid'
    with pytest.raises(RouteIdentityMismatch,match='unknown provider mode'):
        bind_collection_route(result,platform='youtube',capability='search')


def test_public_health_is_configuration_without_observed_access():
    from lumenis.system.collector.adapters.registry import get_adapter
    for platform in ('youtube','reddit','linkedin','channels'):
        health = get_adapter(platform).healthcheck(provider_mode='public')
        assert health.ok and health.metadata['network_attempted'] is False
        bound = bind_collection_route(health,platform=platform,capability='search',request_value='fixture')
        assert bound.access_class is None and bound.backend is None
        assert bound.actual_access_state == 'NOT_ATTEMPTED'


@pytest.mark.parametrize('platform',['youtube','reddit','linkedin','channels','tieba'])
def test_http_browser_routes_are_explicit_and_result_cannot_cross_transport(platform):
    from lumenis.system.collector.adapters.routing import RouteIdentityMismatch
    public=resolve_capability_route(platform,'search',request_value='fixture',public_transport='browser')
    assert public.backend==platform+'_public_browser' and public.access_class is AccessClass.Z0_PUBLIC
    assert public.public_transport=='browser' and not public.fallback_route_ids
    failed=CollectionResult(CollectionStatus.NEED_VERIFY,platform,
        metadata={'provider_mode':'public','public_transport':'browser'},
        attempted_backend=public.backend,attempted_access_class=AccessClass.Z0_PUBLIC)
    assert bind_collection_route(failed,platform=platform,capability='search',public_transport='browser').route_id==public.route_id
    with pytest.raises(RouteIdentityMismatch,match='transport'):
        bind_collection_route(failed,platform=platform,capability='search',public_transport='http')
    assert resolve_capability_route(platform,'search',public_transport='http').backend!=public.backend


def test_provider_selection_rejects_unsupported_modes_without_backends():
    from lumenis.system.collector.adapters.routing import normalize_provider_selection
    assert normalize_provider_selection('youtube',provider_mode='public',public_transport='browser')=={
        'provider_mode':'public','public_transport':'browser'}
    assert normalize_provider_selection('youtube',provider_mode='official')=={'provider_mode':'official'}
    for platform,options in [('youtube',{'provider_mode':'official','public_transport':'browser'}),
        ('youtube',{'provider_mode':False}),('naver',{'public_transport':'browser'}),
        ('xiaohongshu',{'public_transport':'browser'}),('tieba',{'provider_mode':'official'})]:
        with pytest.raises(ValueError):
            normalize_provider_selection(platform,**options)
    for platform in ('naver','daum'):
        route=resolve_capability_route(platform,'comments')
        assert route.backend=='safe_public_http' and route.access_class is AccessClass.Z0_PUBLIC
