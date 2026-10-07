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
    assert not any(route.access_class is AccessClass.Z2_OFFICIAL_API for route in CAPABILITY_ROUTES)


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
    assert unknown.access_class is None
    assert unknown.provenance["route_state"] == "UNKNOWN"
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
