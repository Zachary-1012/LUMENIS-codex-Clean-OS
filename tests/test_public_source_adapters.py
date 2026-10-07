from __future__ import annotations

import pytest

from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
from lumenis.system.collector.adapters.public_source import PublicResponse, PublicSourceError, validate_public_url
from lumenis.system.collector.adapters.sitemap import SitemapAdapter
from lumenis.system.collector.adapters.web_atom import AtomAdapter
from lumenis.system.collector.adapters.web_rss import WebRSSAdapter
from lumenis.system.collector.adapters.wechat import WechatPublicAdapter


class _ServerActorStub:
    actor_id = "test-server-actor"
    principal_kind = "server"


@pytest.fixture
def approved_global_request():
    return {
        "actor": _ServerActorStub(),
        "scope": {
            "domain_id": "cth", "global_scope": True,
            "subject_id": None, "brand_focus_id": None,
        },
    }


def _stub_approved_global_guard(monkeypatch, surface, request):
    def allow(actor, scope, platform, keyword, max_results, **kwargs):
        assert actor is request["actor"]
        assert scope == request["scope"]
        assert kwargs.get("max_scroll") is None
        return dict(request["scope"]), None

    monkeypatch.setattr(surface, "_manual_collection_guard", allow)


def _response(body: str, content_type: str) -> PublicResponse:
    return PublicResponse(
        url="https://public.example.test/source",
        content=body.encode("utf-8"),
        content_type=content_type,
        status_code=200,
    )


def test_public_http_normalizes_html_and_keeps_provenance():
    adapter = PublicHttpAdapter(fetcher=lambda _: _response(
        '<html><head><title>Public title</title><meta name="description" content="Public summary"></head>'
        '<body><main>Public body</main></body></html>',
        "text/html",
    ))

    result = adapter.search("https://public.example.test/article")

    assert result.status is CollectionStatus.SUCCESS
    assert result.items[0]["title"] == "Public title"
    assert result.items[0]["content"] == "Public body"
    assert result.items[0]["source_platform"] == "public_http"
    assert result.metadata["provider"] == "public_http"
    assert result.metadata["source"].startswith("https://")
    assert result.metadata["collected_at"]


def test_atom_normalizes_entry_identity_and_timestamp():
    atom = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Example feed</title>
      <entry>
        <id>tag:public.example,2026:item-1</id>
        <title>Atom entry</title>
        <link href="https://public.example.test/item-1" />
        <published>2026-09-17T04:00:00Z</published>
        <updated>2026-09-18T04:00:00Z</updated>
        <summary>Atom summary</summary>
        <author><name>Publisher</name></author>
      </entry>
    </feed>"""
    adapter = AtomAdapter(fetcher=lambda _: _response(atom, "application/atom+xml"))

    result = adapter.search("https://public.example.test/feed.atom")

    assert result.status is CollectionStatus.SUCCESS
    assert result.items[0]["platform_content_id"].startswith("atom:")
    assert result.items[0]["title"] == "Atom entry"
    assert result.items[0]["author_nickname"] == "Publisher"
    assert result.items[0]["publish_datetime"] == "Thu, 17 Sep 2026 04:00:00 +0000"
    assert result.items[0]["raw"]["source_published_at"] == "2026-09-17T04:00:00Z"
    assert result.items[0]["raw"]["source_updated_at"] == "2026-09-18T04:00:00Z"
    assert result.metadata["provider"] == "feedparser_atom"


def test_atom_updated_only_entry_keeps_publication_unknown():
    atom = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Example feed</title>
      <entry>
        <id>tag:public.example,2026:updated-only</id>
        <title>Updated only</title>
        <updated>2026-09-18T04:00:00Z</updated>
      </entry>
    </feed>"""
    adapter = AtomAdapter(fetcher=lambda _: _response(atom, "application/atom+xml"))

    result = adapter.search("https://public.example.test/feed.atom")

    assert result.status is CollectionStatus.SUCCESS
    assert result.items[0]["publish_datetime"] == ""
    assert result.items[0]["raw"]["source_updated_at"] == "2026-09-18T04:00:00Z"
    assert "source_published_at" not in result.items[0]["raw"]


def test_atom_entry_without_timestamps_keeps_publication_unknown():
    atom = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Example feed</title>
      <entry>
        <id>tag:public.example,2026:no-time</id>
        <title>No timestamp</title>
      </entry>
    </feed>"""
    adapter = AtomAdapter(fetcher=lambda _: _response(atom, "application/atom+xml"))

    result = adapter.search("https://public.example.test/feed.atom")

    assert result.status is CollectionStatus.SUCCESS
    assert result.items[0]["publish_datetime"] == ""
    assert "source_published_at" not in result.items[0]["raw"]
    assert "source_updated_at" not in result.items[0]["raw"]


def test_atom_source_update_survives_native_bridge_without_replacing_publication():
    from lumenis.system.collector.adapters.platform_naming import to_canonical_record
    from lumenis.system.collector.adapters.secondary_collection import _native_record

    atom = """<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Example feed</title>
      <entry>
        <id>tag:public.example,2026:bridge</id>
        <title>Published and later updated</title>
        <link href="https://public.example.test/bridge" />
        <published>2026-09-17T04:00:00Z</published>
        <updated>2026-09-18T04:00:00Z</updated>
      </entry>
    </feed>"""
    adapter = AtomAdapter(fetcher=lambda _: _response(atom, "application/atom+xml"))

    result = adapter.search("https://public.example.test/feed.atom")
    item = result.items[0]
    record = _native_record(item, "web_atom", "fixture", "2026-09-19T00:00:00+00:00")
    canonical = to_canonical_record(record, "web_atom")

    assert record["published_at"] == "Thu, 17 Sep 2026 04:00:00 +0000"
    assert record["source_published_at"] == "2026-09-17T04:00:00Z"
    assert record["source_updated_at"] == "2026-09-18T04:00:00Z"
    assert record["captured_at"] == "2026-09-19T00:00:00+00:00"
    assert canonical["published_at"] == "Thu, 17 Sep 2026 04:00:00 +0000"


def test_web_rss_normalizes_existing_public_reader_and_provenance(monkeypatch):
    import web_discovery

    monkeypatch.setattr(
        web_discovery,
        "fetch_google_news_rss",
        lambda query, max_results=20: {
            "ok": True,
            "collected_at": "2026-09-18T04:00:00+00:00",
            "provider": "google_news_rss",
            "source": "news.google.com/rss/search",
            "items": [{
                "title": "Public RSS result",
                "url": "https://public.example.test/rss-1",
                "source": "Example Publisher",
                "published_at": "2026-09-18T03:00:00+00:00",
            }],
        },
    )

    result = WebRSSAdapter().search("lumenis", max_results=1)

    assert result.status is CollectionStatus.SUCCESS
    assert result.items[0]["platform_content_id"].startswith("google-news:")
    assert result.items[0]["title"] == "Public RSS result"
    assert result.items[0]["author_nickname"] == "Example Publisher"
    assert result.items[0]["url"] == "https://public.example.test/rss-1"
    assert result.metadata["provider"] == "google_news_rss"
    assert result.metadata["source"] == "news.google.com/rss/search"
    assert result.metadata["collected_at"]


def test_sitemap_discovers_urls_without_creating_content_store():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://public.example.test/a</loc><lastmod>2026-09-17</lastmod></url>
      <url><loc>https://public.example.test/b</loc></url>
    </urlset>"""
    adapter = SitemapAdapter(fetcher=lambda _: _response(xml, "application/xml"))

    result = adapter.search("https://public.example.test/sitemap.xml")

    assert result.status is CollectionStatus.SUCCESS
    assert [item["url"] for item in result.items] == [
        "https://public.example.test/a", "https://public.example.test/b",
    ]
    # Sitemap ``lastmod`` describes a source update, not publication time.
    # Publication remains unknown until the detail source declares it.
    assert result.items[0]["publish_datetime"] == ""
    assert result.items[0]["raw"]["source_updated_at"] == "2026-09-17"
    assert result.metadata["entry_kind"] == "urlset"


def test_public_url_rejects_local_network_targets():
    try:
        validate_public_url("http://127.0.0.1:8201/healthz")
    except PublicSourceError as exc:
        assert "private" in str(exc) or "local" in str(exc)
    else:  # pragma: no cover - assertion documents the SSRF boundary
        raise AssertionError("loopback source must be rejected")


def test_instagram_arbitrary_urls_do_not_reach_authorized_session_engine():
    from lumenis.system.collector.adapters.instagram import InstagramAdapter

    calls = []

    class Engine:
        def search(self, *args, **kwargs):
            calls.append("search")
            raise AssertionError("arbitrary URL reached Instagram session search")

        def detail(self, *args, **kwargs):
            calls.append("detail")
            raise AssertionError("arbitrary URL reached Instagram session detail")

        def comments(self, *args, **kwargs):
            calls.append("comments")
            raise AssertionError("arbitrary URL reached Instagram session comments")

        def creator(self, *args, **kwargs):
            calls.append("creator")
            raise AssertionError("arbitrary URL reached Instagram session creator")

    adapter = InstagramAdapter(engine=Engine())
    url = "https://attacker.example/not-an-instagram-post"
    assert adapter.search(url).status is CollectionStatus.NOT_SUPPORTED
    assert adapter.detail(url).status is CollectionStatus.NOT_SUPPORTED
    assert adapter.comments(url).status is CollectionStatus.NOT_SUPPORTED
    assert adapter.creator(url).status is CollectionStatus.NOT_SUPPORTED
    assert calls == []


def test_wechat_sogou_url_is_not_treated_as_article_or_search_query():
    calls = []
    adapter = WechatPublicAdapter(fetcher=lambda url: calls.append(url) or _response("", "text/html"))
    sogou_url = "https://weixin.sogou.com/weixin?type=2&query=brand"

    assert adapter.search(sogou_url).status is CollectionStatus.NOT_SUPPORTED
    assert adapter.detail(sogou_url).status is CollectionStatus.NOT_SUPPORTED
    assert calls == []


def test_wechat_plain_query_uses_existing_public_discovery_and_original_article_path():
    calls = []
    article_url = "https://mp.weixin.qq.com/s/article_123"
    sogou_html = (
        '<ul><li id="sogou_vr_1"><div class="txt-box"><h3>'
        f'<a href="{article_url}">Public article</a></h3>'
        '<div class="txt-info">Article excerpt</div></div></li></ul>'
    )
    article_html = (
        '<html><head><title>Public article</title></head><body>'
        '<h2 id="activity-name">Public article</h2><div id="js_content">Article body</div>'
        '</body></html>'
    )

    def fetcher(url):
        calls.append(url)
        if "weixin.sogou.com" in url:
            return PublicResponse(url, sogou_html.encode(), "text/html", 200)
        return PublicResponse(url, article_html.encode(), "text/html", 200)

    result = WechatPublicAdapter(fetcher=fetcher).search("brand")

    assert result.status is CollectionStatus.SUCCESS
    assert len(result.items) == 1
    assert result.items[0]["content"] == "Article body"
    assert calls[0].startswith("https://weixin.sogou.com/weixin?")
    assert calls[1] == article_url
    assert result.metadata["provider"] == "public_sogou_discovery_original_fetch"
    assert result.metadata["original_body_available"] is True


def test_public_source_runs_through_existing_evidence_boundary(monkeypatch, approved_global_request):
    import database as db
    import lumenis.system.collector.adapters.secondary_collection as surface

    adapter = PublicHttpAdapter(fetcher=lambda _: _response(
        '<html><head><link rel="canonical" href="/article">'
        '<title>Evidence source</title><meta property="article:published_time" '
        'content="2026-09-27T10:00:00+00:00"></head><body>text</body></html>',
        "text/html",
    ))
    captured = {}
    persisted = []

    def insert_note(payload, *, connection=None):
        assert connection is not None and connection.in_transaction
        persisted.append(payload)
        return 11, True

    monkeypatch.setattr(surface, "get_adapter", lambda platform: adapter)
    monkeypatch.setattr(surface, "_daily_action_count", lambda platform, at: 0)
    monkeypatch.setitem(surface._last_action, "public_http", 0.0)
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: None)
    _stub_approved_global_guard(monkeypatch, surface, approved_global_request)
    monkeypatch.setattr(
        surface, "_write_prelaunch_evidence",
        lambda platform, keyword, result, **kwargs: captured.update(result) or 11,
    )
    monkeypatch.setattr(surface, "_prelaunch_scope_conflict", lambda records, scope, **kwargs: False)
    monkeypatch.setattr(surface, "_sync_unassigned_collection", lambda note_ids, scope, evidence_id, **kwargs: len(note_ids))
    from lumenis.shared.database import platform_content
    monkeypatch.setattr(platform_content, "platform_records_changed", lambda *args, **kwargs: True)
    def write_native(records, **kwargs):
        assert kwargs["connection"].in_transaction
        assert kwargs["scope"]["global_scope"] is True
        return len(records)
    monkeypatch.setattr(platform_content, "persist_unassigned_platform_records", write_native)
    monkeypatch.setattr(db, "insert_note", insert_note)

    result = surface.collect_search(
        "public_http", "https://public.example.test/article", max_results=1, operator="human",
        actor=approved_global_request["actor"], scope=approved_global_request["scope"],
    )

    assert result["ok"] is True
    assert result["imported"] == 1
    assert persisted[0]["note_id"].startswith("public-http:")
    assert persisted[0]["source_platform"] == "public_http"
    assert persisted[0]["url"] == "https://public.example.test/article"
    assert persisted[0]["publish_datetime"] == "2026-09-27T10:00:00+00:00"
    assert result["evidence_recorded"] is True
    assert result["canonical_synced"] == 1
    assert result["native_fields_synced"] == 1 and result["refresh_verified"] is True
    assert result["provenance"]["provider"] == "public_http"
    assert result["provenance"]["source"].startswith("https://")
    assert result["provenance"]["access_class"] == "Z0"
    assert result["provenance"]["route_id"] == "public-http.search"
    assert result["provenance"]["source_access_mode"] == "public_read_only"
    assert result["provenance"]["requested_source_url"] == "https://public.example.test/article"
    assert result["external_write"] is False
    assert captured["provenance"]["provider"] == "public_http"
    assert captured["provenance"]["access_class"] == "Z0"
    assert captured["provenance"]["final_source_url"] == "https://public.example.test/source"


def test_sitemap_rejects_non_sitemap_xml_before_canonical_import(monkeypatch, approved_global_request):
    import lumenis.system.collector.adapters.multi_platform_import as importer
    import lumenis.system.collector.adapters.secondary_collection as surface

    xml = """<?xml version=\"1.0\"?>
    <rss><url><loc>https://public.example.test/not-a-sitemap</loc></url></rss>"""
    adapter = SitemapAdapter(fetcher=lambda _: _response(xml, "application/xml"))
    captured = {}

    def fail_if_called(*args, **kwargs):
        raise AssertionError("non-Sitemap XML must not reach Canonical import")

    monkeypatch.setattr(surface, "_get_runtime_adapter", lambda platform: adapter)
    monkeypatch.setattr(surface, "_daily_action_count", lambda platform, at: 0)
    monkeypatch.setitem(surface._last_action, "sitemap", 0.0)
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: None)
    _stub_approved_global_guard(monkeypatch, surface, approved_global_request)
    monkeypatch.setattr(
        surface, "_write_prelaunch_evidence",
        lambda platform, keyword, result, **kwargs: captured.update(result) or 11,
    )
    monkeypatch.setattr(importer, "import_multi_platform_records", fail_if_called)

    result = surface.collect_search(
        "sitemap", "https://public.example.test/sitemap.xml", max_results=1, operator="human",
        actor=approved_global_request["actor"], scope=approved_global_request["scope"],
    )

    assert result["ok"] is False
    assert result["status"] == "PROVIDER_UNAVAILABLE"
    assert result["raw_count"] is None
    assert result["returned_count"] is None
    assert result["imported"] == 0
    assert result["canonical_synced"] == 0
    assert result["evidence_recorded"] is True
    assert captured["status"] == "PROVIDER_UNAVAILABLE"


def test_sitemap_index_root_remains_supported():
    xml = """<?xml version=\"1.0\"?>
    <sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
      <sitemap><loc>https://public.example.test/child-sitemap.xml</loc><lastmod>2026-09-26T12:00:00Z</lastmod></sitemap>
    </sitemapindex>"""
    adapter = SitemapAdapter(fetcher=lambda _: _response(xml, "application/xml"))

    result = adapter.search("https://public.example.test/sitemap-index.xml")

    assert result.status is CollectionStatus.SUCCESS
    assert result.items[0]["url"] == "https://public.example.test/child-sitemap.xml"
    assert result.items[0]["publish_datetime"] == ""
    assert result.items[0]["raw"]["source_updated_at"] == "2026-09-26T12:00:00Z"
    assert result.items[0]["raw"]["entry_kind"] == "sitemap"
    assert result.metadata["entry_kind"] == "sitemapindex"


def test_atom_entry_without_stable_identity_fails_before_canonical_import(monkeypatch, approved_global_request):
    import lumenis.system.collector.adapters.multi_platform_import as importer
    import lumenis.system.collector.adapters.secondary_collection as surface

    atom = """<?xml version=\"1.0\" encoding=\"utf-8\"?>
    <feed xmlns=\"http://www.w3.org/2005/Atom\">
      <title>Example feed</title>
      <id>https://public.example.test/feed.atom</id>
      <updated>2026-09-18T04:00:00Z</updated>
      <author><name>Publisher</name></author>
      <entry>
        <title>Identity-less entry</title>
        <updated>2026-09-18T04:00:00Z</updated>
        <content>Entry content</content>
      </entry>
    </feed>"""
    response = _response(atom, "application/atom+xml")
    adapter = AtomAdapter(fetcher=lambda _: response)
    evidence = {}

    def fail_if_called(*args, **kwargs):
        raise AssertionError("an entry without source identity must not reach Canonical")

    monkeypatch.setattr(surface, "_get_runtime_adapter", lambda _platform: adapter)
    monkeypatch.setattr(surface, "_adapter_health", lambda _platform, **_source: {
        "status": "SUCCESS", "ready": True, "can_attempt": True, "message": "ok", "metadata": {},
    })
    monkeypatch.setattr(surface, "_daily_action_count", lambda _platform, _at: 0)
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: None)
    _stub_approved_global_guard(monkeypatch, surface, approved_global_request)
    monkeypatch.setattr(
        surface, "_write_prelaunch_evidence",
        lambda _platform, _keyword, result, **_kwargs: evidence.update(result) or 11,
    )
    monkeypatch.setattr(importer, "import_multi_platform_records", fail_if_called)
    monkeypatch.setitem(surface._last_action, "web_atom", 0.0)

    result = surface.collect_search(
        "web_atom", "https://public.example.test/feed.atom", max_results=1, operator="human",
        actor=approved_global_request["actor"], scope=approved_global_request["scope"],
    )

    assert result["ok"] is False
    assert result["status"] == "PROVIDER_UNAVAILABLE"
    assert result["imported"] == 0
    assert result["canonical_synced"] == 0
    assert result["evidence_recorded"] is True
    assert evidence["status"] == "PROVIDER_UNAVAILABLE"
    assert evidence["provenance"]["source"] == response.url


def test_web_rss_missing_item_url_fails_before_canonical_import(monkeypatch, approved_global_request):
    import web_discovery
    import lumenis.system.collector.adapters.multi_platform_import as importer
    import lumenis.system.collector.adapters.secondary_collection as surface

    outcome = {
        "ok": True,
        "collected_at": "2026-09-24T04:00:00+00:00",
        "provider": "google_news_rss",
        "source": "news.google.com/rss/search",
        "items": [{
            "title": "RSS item without stable URL",
            "url": "",
            "source": "Example Publisher",
            "published_at": "2026-09-24T03:00:00+00:00",
        }],
    }
    monkeypatch.setattr(
        web_discovery, "fetch_google_news_rss", lambda _query, max_results=20: outcome,
    )
    adapter = WebRSSAdapter()
    evidence = {}

    def fail_if_called(*args, **kwargs):
        raise AssertionError("an RSS item without a source URL must not reach Canonical")

    monkeypatch.setattr(surface, "_get_runtime_adapter", lambda _platform: adapter)
    monkeypatch.setattr(surface, "_adapter_health", lambda _platform, **_source: {
        "status": "SUCCESS", "ready": True, "can_attempt": True, "message": "ok", "metadata": {},
    })
    monkeypatch.setattr(surface, "_daily_action_count", lambda _platform, _at: 0)
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: None)
    _stub_approved_global_guard(monkeypatch, surface, approved_global_request)
    monkeypatch.setattr(
        surface, "_write_prelaunch_evidence",
        lambda _platform, _keyword, result, **_kwargs: evidence.update(result) or 11,
    )
    monkeypatch.setattr(importer, "import_multi_platform_records", fail_if_called)
    monkeypatch.setitem(surface._last_action, "web_rss", 0.0)

    result = surface.collect_search(
        "web_rss", "lumenis", max_results=1, operator="human",
        actor=approved_global_request["actor"], scope=approved_global_request["scope"],
    )

    assert result["ok"] is False
    assert result["status"] == "PROVIDER_UNAVAILABLE"
    assert result["raw_count"] == 1
    assert result["returned_count"] == 0
    assert result["imported"] == 0
    assert result["canonical_synced"] == 0
    assert result["evidence_recorded"] is True
    assert result["provenance"]["error_type"] == "MISSING_SOURCE_IDENTITY"
    assert evidence["status"] == "PROVIDER_UNAVAILABLE"
    assert evidence["provenance"]["source"] == "news.google.com/rss/search"
