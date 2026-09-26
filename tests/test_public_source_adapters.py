from __future__ import annotations

from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
from lumenis.system.collector.adapters.public_source import PublicResponse, PublicSourceError, validate_public_url
from lumenis.system.collector.adapters.sitemap import SitemapAdapter
from lumenis.system.collector.adapters.web_atom import AtomAdapter
from lumenis.system.collector.adapters.web_rss import WebRSSAdapter


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
    assert result.items[0]["content"] == "Public summary"
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
    assert result.items[0]["publish_datetime"]
    assert result.metadata["provider"] == "feedparser_atom"


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
    assert result.items[0]["publish_datetime"] == "2026-09-17"
    assert result.metadata["entry_kind"] == "urlset"


def test_public_url_rejects_local_network_targets():
    try:
        validate_public_url("http://127.0.0.1:8201/healthz")
    except PublicSourceError as exc:
        assert "private" in str(exc) or "local" in str(exc)
    else:  # pragma: no cover - assertion documents the SSRF boundary
        raise AssertionError("loopback source must be rejected")


def test_public_source_runs_through_existing_evidence_boundary(monkeypatch):
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

    def insert_note(payload):
        persisted.append(payload)
        return 11, True

    monkeypatch.setattr(surface, "get_adapter", lambda platform: adapter)
    monkeypatch.setattr(surface, "_daily_action_count", lambda platform, at: 0)
    monkeypatch.setitem(surface._last_action, "public_http", 0.0)
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(surface, "_write_evidence", lambda platform, keyword, result, **kwargs: captured.update(result) or 11)
    monkeypatch.setattr(db, "insert_note", insert_note)
    monkeypatch.setattr(surface, "_mark_subject_and_sync", lambda *args, **kwargs: {
        "subject_matches": 0, "canonical_synced": 1, "subjects": [],
    })

    result = surface.collect_search("public_http", "https://public.example.test/article", max_results=1, operator="human")

    assert result["ok"] is True
    assert result["imported"] == 1
    assert persisted[0]["note_id"].startswith("public-http:")
    assert persisted[0]["source_platform"] == "public_http"
    assert persisted[0]["url"] == "https://public.example.test/article"
    assert persisted[0]["publish_datetime"] == "2026-09-27T10:00:00+00:00"
    assert result["evidence_recorded"] is True
    assert result["canonical_synced"] == 1
    assert result["provenance"]["provider"] == "public_http"
    assert result["provenance"]["source"].startswith("https://")
    assert result["external_write"] is False
    assert captured["provenance"]["provider"] == "public_http"


def test_sitemap_rejects_non_sitemap_xml_before_canonical_import(monkeypatch):
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
    monkeypatch.setattr(surface, "_write_evidence", lambda *args, **kwargs: captured.update(args[2]) or 11)
    monkeypatch.setattr(surface, "_mark_subject_and_sync", fail_if_called)
    monkeypatch.setattr(importer, "import_multi_platform_records", fail_if_called)

    result = surface.collect_search(
        "sitemap", "https://public.example.test/sitemap.xml", max_results=1, operator="human",
    )

    assert result["ok"] is False
    assert result["status"] == "PROVIDER_UNAVAILABLE"
    assert result["raw_count"] == 0
    assert result["returned_count"] == 0
    assert result["imported"] == 0
    assert result["canonical_synced"] == 0
    assert result["evidence_recorded"] is True
    assert captured["status"] == "PROVIDER_UNAVAILABLE"


def test_sitemap_index_root_remains_supported():
    xml = """<?xml version=\"1.0\"?>
    <sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
      <sitemap><loc>https://public.example.test/child-sitemap.xml</loc></sitemap>
    </sitemapindex>"""
    adapter = SitemapAdapter(fetcher=lambda _: _response(xml, "application/xml"))

    result = adapter.search("https://public.example.test/sitemap-index.xml")

    assert result.status is CollectionStatus.SUCCESS
    assert result.items[0]["url"] == "https://public.example.test/child-sitemap.xml"
    assert result.items[0]["raw"]["entry_kind"] == "sitemap"
    assert result.metadata["entry_kind"] == "sitemapindex"


def test_atom_entry_without_stable_identity_fails_before_canonical_import(monkeypatch):
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
    monkeypatch.setattr(surface, "_adapter_health", lambda _platform: {
        "status": "SUCCESS", "ready": True, "can_attempt": True, "message": "ok", "metadata": {},
    })
    monkeypatch.setattr(surface, "_daily_action_count", lambda _platform, _at: 0)
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        surface, "_write_evidence",
        lambda _platform, _keyword, result, **_kwargs: evidence.update(result) or 11,
    )
    monkeypatch.setattr(surface, "_mark_subject_and_sync", fail_if_called)
    monkeypatch.setattr(importer, "import_multi_platform_records", fail_if_called)
    monkeypatch.setitem(surface._last_action, "web_atom", 0.0)

    result = surface.collect_search(
        "web_atom", "https://public.example.test/feed.atom", max_results=1, operator="human",
    )

    assert result["ok"] is False
    assert result["status"] == "PROVIDER_UNAVAILABLE"
    assert result["imported"] == 0
    assert result["canonical_synced"] == 0
    assert result["evidence_recorded"] is True
    assert evidence["status"] == "PROVIDER_UNAVAILABLE"
    assert evidence["provenance"]["source"] == response.url


def test_web_rss_missing_item_url_fails_before_canonical_import(monkeypatch):
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
    monkeypatch.setattr(surface, "_adapter_health", lambda _platform: {
        "status": "SUCCESS", "ready": True, "can_attempt": True, "message": "ok", "metadata": {},
    })
    monkeypatch.setattr(surface, "_daily_action_count", lambda _platform, _at: 0)
    monkeypatch.setattr(surface, "_write_run_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        surface, "_write_evidence",
        lambda _platform, _keyword, result, **_kwargs: evidence.update(result) or 11,
    )
    monkeypatch.setattr(surface, "_mark_subject_and_sync", fail_if_called)
    monkeypatch.setattr(importer, "import_multi_platform_records", fail_if_called)
    monkeypatch.setitem(surface._last_action, "web_rss", 0.0)

    result = surface.collect_search("web_rss", "lumenis", max_results=1, operator="human")

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
