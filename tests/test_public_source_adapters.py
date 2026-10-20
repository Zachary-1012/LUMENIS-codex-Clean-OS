from __future__ import annotations

import pytest

from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
from lumenis.system.collector.adapters.public_source import (
    PublicResponse, PublicSourceError, PublicSourceHTTPError, validate_public_url,
)
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
            "requested_source_url": "https://news.google.com/rss/search",
            "final_source_url": "https://news.google.com/rss/search",
            "redirect_chain": "[]",
            "resolution_trace": "[]",
            "source_access_mode": "public_read_only",
            "commercial_license_state": "pending_review",
            "items": [{
                "title": "Public RSS result",
                "url": "https://public.example.test/rss-1",
                "source": "Example Publisher",
                "source_url": "https://public.example.test/",
                "published_at": "2026-09-18T03:00:00+00:00",
                "source_published_at": "Thu, 17 Sep 2026 20:00:00 -0700",
                "publication_time_state": "KNOWN",
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
    assert result.metadata["requested_source_url"] == "https://news.google.com/rss/search"
    assert result.metadata["final_source_url"] == "https://news.google.com/rss/search"
    assert result.metadata["source_access_mode"] == "public_read_only"
    assert result.metadata["commercial_license_state"] == "pending_review"
    assert result.items[0]["raw"]["source_url"] == "https://public.example.test/"
    assert result.items[0]["raw"]["source_published_at"] == "Thu, 17 Sep 2026 20:00:00 -0700"
    assert result.items[0]["raw"]["publication_time_state"] == "KNOWN"


def test_google_news_rss_uses_bounded_public_transport_and_keeps_timezone(monkeypatch):
    import web_discovery
    from lumenis.system.collector.adapters import public_source

    xml = """<rss version="2.0"><channel><title>Google News</title><item>
      <title>Public result</title><link>https://publisher.example.test/item</link>
      <pubDate>Thu, 17 Sep 2026 04:00:00 -0700</pubDate>
      <source url="https://publisher.example.test/">Example Publisher</source>
    </item></channel></rss>"""
    response = PublicResponse(
        url="https://news.google.com/rss/search?q=lumenis",
        requested_url="https://news.google.com/rss/search?q=lumenis",
        content=xml.encode("utf-8"),
        content_type="application/rss+xml",
        status_code=200,
    )
    calls = []

    def fetch(url, **kwargs):
        calls.append((url, kwargs))
        return response

    monkeypatch.setattr(public_source, "fetch_public_url", fetch)

    outcome = web_discovery.fetch_google_news_rss("lumenis", max_results=1)

    assert outcome["ok"] is True
    assert len(calls) == 1
    requested_url, options = calls[0]
    assert requested_url.startswith("https://news.google.com/rss/search?")
    assert options["max_bytes"] == public_source.MAX_RESPONSE_BYTES
    assert options["allowed_host_suffixes"] == ("google.com",)
    assert outcome["items"][0]["published_at"] == "2026-09-17T11:00:00+00:00"
    assert outcome["items"][0]["source_published_at"] == "Thu, 17 Sep 2026 04:00:00 -0700"
    assert outcome["items"][0]["publication_time_state"] == "KNOWN"
    assert outcome["items"][0]["source_url"] == "https://publisher.example.test/"
    assert outcome["source_access_mode"] == "public_read_only"
    assert outcome["final_source_url"] == "https://news.google.com/rss/search"


def test_google_news_rss_preserves_http_failure_from_real_bounded_transport(monkeypatch):
    import web_discovery
    import requests
    from types import SimpleNamespace
    from lumenis.system.collector.adapters import public_source

    monkeypatch.setattr(public_source, "load_public_source_host_pins", lambda: {})
    monkeypatch.setattr(
        public_source, "_resolved_addresses", lambda _hostname: ["93.184.216.34"],
    )
    requests_made = []

    def offline_http_send(_adapter, request, **_kwargs):
        requests_made.append(request.url)
        response = requests.Response()
        response.status_code = 503
        response.headers = requests.structures.CaseInsensitiveDict({
            "Content-Type": "application/rss+xml",
        })
        response.url = request.url
        response.request = request
        response.reason = "Synthetic unavailable"
        response._content = b"<rss><channel></channel></rss>"
        response._content_consumed = True
        response.raw = SimpleNamespace(close=lambda: None)
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", offline_http_send)

    outcome = web_discovery.fetch_google_news_rss("lumenis", max_results=1)

    assert outcome["ok"] is False
    assert outcome["items"] == []
    assert outcome["error_type"] == "HTTP_503"
    assert outcome["http_status"] == 503
    assert len(requests_made) == 1
    assert requests_made[0].startswith("https://news.google.com/rss/search?")

    collected = WebRSSAdapter().search("lumenis", max_results=1)
    assert collected.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert collected.items == []
    assert collected.metadata["error_type"] == "HTTP_503"
    assert collected.metadata["http_status"] == 503


def test_google_news_rss_http_failure_retains_sanitized_transport_lineage(monkeypatch):
    import json
    import web_discovery
    import requests
    from types import SimpleNamespace
    from lumenis.system.collector.adapters import public_source

    monkeypatch.setattr(public_source, "load_public_source_host_pins", lambda: {})
    monkeypatch.setattr(
        public_source, "_resolved_addresses", lambda _hostname: ["93.184.216.34"],
    )
    requests_made = []

    def offline_http_send(_adapter, request, **_kwargs):
        requests_made.append(request.url)
        response = requests.Response()
        response.status_code = 302 if len(requests_made) == 1 else 503
        response.headers = requests.structures.CaseInsensitiveDict()
        if len(requests_made) == 1:
            response.headers["Location"] = "https://news.google.com/rss/final?secret=redirect-token"
        response.url = request.url
        response.request = request
        response.reason = "Synthetic response"
        response._content = b""
        response._content_consumed = True
        response.raw = SimpleNamespace(close=lambda: None)
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", offline_http_send)

    outcome = web_discovery.fetch_google_news_rss("lumenis", max_results=1)

    assert outcome["ok"] is False
    assert outcome["items"] == []
    assert outcome["error_type"] == "HTTP_503"
    assert outcome["http_status"] == 503
    assert len(requests_made) == 2
    assert outcome["requested_source_url"].startswith("https://news.google.com/rss/search")
    assert outcome["final_source_url"] == "https://news.google.com/rss/final"
    assert json.loads(outcome["redirect_chain"]) == [
        "https://news.google.com/rss/search",
    ]
    assert len(json.loads(outcome["resolution_trace"])) == 2
    assert outcome["source_access_mode"] == "public_read_only"
    assert outcome["commercial_license_state"] == "pending_review"
    assert "redirect-token" not in str(outcome)
    assert "secret" not in str(outcome)

    requests_made.clear()
    collected = WebRSSAdapter().search("lumenis", max_results=1)
    assert collected.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert collected.metadata["error_type"] == "HTTP_503"
    assert collected.metadata["final_source_url"] == outcome["final_source_url"]
    assert collected.metadata["redirect_chain"] == outcome["redirect_chain"]


@pytest.mark.parametrize("adapter,keyword,options", [
    (PublicHttpAdapter, "https://public.example.test/article", {}),
    (AtomAdapter, "https://public.example.test/feed.atom", {}),
    (SitemapAdapter, "https://public.example.test/sitemap.xml", {}),
])
def test_public_source_http_error_keeps_observed_status(adapter, keyword, options):
    def fail(_url):
        raise PublicSourceHTTPError(429)

    result = adapter(fetcher=fail).search(keyword, **options)

    assert result.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.items == []
    assert result.metadata["error_type"] == "HTTP_429"
    assert result.metadata["http_status"] == 429


@pytest.mark.parametrize("adapter", [PublicHttpAdapter, AtomAdapter, SitemapAdapter])
def test_public_source_http_error_keeps_safe_lineage(adapter):
    def fail(_url):
        raise PublicSourceHTTPError(
            503,
            requested_url="https://public.example.test/start?private=query",
            final_url="https://public.example.test/final?token=secret",
            redirect_chain=("https://public.example.test/start?private=query",),
            resolution_trace=({"host": "public.example.test", "address": "93.184.216.34"},),
        )

    result = adapter(fetcher=fail).search("https://public.example.test/start")

    assert result.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.metadata["error_type"] == "HTTP_503"
    assert result.metadata["http_status"] == 503
    assert result.metadata["requested_source_url"] == "https://public.example.test/start"
    assert result.metadata["final_source_url"] == "https://public.example.test/final"
    assert result.metadata["redirect_chain"] == '["https://public.example.test/start"]'
    assert result.metadata["resolution_trace"] == (
        '[{"host": "public.example.test", "address": "93.184.216.34"}]'
    )
    assert result.metadata["source_access_mode"] == "public_read_only"
    assert result.metadata["commercial_license_state"] == "pending_review"


def test_google_news_rss_keeps_media_type_failure_distinct_from_http_status(monkeypatch):
    import web_discovery
    from lumenis.system.collector.adapters import public_source

    response = PublicResponse(
        url="https://news.google.com/rss/search?q=lumenis",
        content=b"<html>not an RSS feed</html>",
        content_type="text/html",
        status_code=200,
    )
    monkeypatch.setattr(public_source, "fetch_public_url", lambda *_args, **_kwargs: response)

    outcome = web_discovery.fetch_google_news_rss("lumenis", max_results=1)

    assert outcome["ok"] is False
    assert outcome["items"] == []
    assert outcome["error_type"] == "RSS_RESPONSE_TYPE_UNSUPPORTED"
    assert outcome["http_status"] == 200


@pytest.mark.parametrize(("content", "content_type", "expected_error"), [
    (b"<html>not an RSS feed</html>", "text/html", "RSS_RESPONSE_TYPE_UNSUPPORTED"),
    (b"<rss><channel><item>", "application/rss+xml", "RSS_PARSE_ERROR"),
    (b"<rss><items/></rss>", "application/rss+xml", "RSS_CHANNEL_MISSING"),
])
def test_rss_parse_failures_keep_safe_transport_provenance(
    monkeypatch, content, content_type, expected_error,
):
    import json
    import web_discovery
    from lumenis.system.collector.adapters import public_source

    response = PublicResponse(
        url="https://news.google.com/rss/search?token=private",
        requested_url="https://news.google.com/rss/search?q=private-query",
        redirect_chain=("https://news.google.com/redirect?secret=1",),
        resolution_trace=({"host": "news.google.com", "address": "93.184.216.34"},),
        content=content,
        content_type=content_type,
        status_code=200,
    )
    monkeypatch.setattr(public_source, "fetch_public_url", lambda *_args, **_kwargs: response)

    outcome = web_discovery.fetch_google_news_rss("lumenis", max_results=1)
    result = WebRSSAdapter().search("lumenis", max_results=1)

    assert outcome["ok"] is False
    assert outcome["items"] == []
    assert outcome["error_type"] == expected_error
    assert outcome["http_status"] == 200
    assert outcome["requested_source_url"] == "https://news.google.com/rss/search"
    assert outcome["final_source_url"] == "https://news.google.com/rss/search"
    assert json.loads(outcome["redirect_chain"]) == ["https://news.google.com/redirect"]
    assert json.loads(outcome["resolution_trace"]) == [
        {"host": "news.google.com", "address": "93.184.216.34"},
    ]
    assert outcome["source_access_mode"] == "public_read_only"
    assert outcome["commercial_license_state"] == "pending_review"
    assert result.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.items == []
    assert result.metadata["error_type"] == expected_error
    assert result.metadata["requested_source_url"] == outcome["requested_source_url"]
    assert result.metadata["final_source_url"] == outcome["final_source_url"]
    assert result.metadata["source_access_mode"] == outcome["source_access_mode"]
    assert result.metadata["commercial_license_state"] == outcome["commercial_license_state"]
    assert "private" not in outcome["requested_source_url"]
    assert "secret" not in outcome["redirect_chain"]


def test_legacy_and_current_rss_publication_values_sort_by_actual_instant(monkeypatch):
    import web_discovery

    records = [
        {
            "id": "first-equal-instant",
            "published_at": "2026-09-18T03:00:00+00:00",
            "source_published_at": "2026-09-18T03:00:00Z",
            "publication_time_state": "KNOWN",
        },
        {
            "id": "second-equal-instant",
            "published_at": "Thu, 17 Sep 2026 20:00:00 -0700",
            "source_published_at": "Thu, 17 Sep 2026 20:00:00 -0700",
        },
        {
            "id": "later-instant",
            "published_at": "2026-09-18T04:00:00+00:00",
            "source_published_at": "2026-09-18T04:00:00+00:00",
            "publication_time_state": "KNOWN",
        },
        {
            "id": "naive-unknown",
            "published_at": "2026-09-18 05:00:00",
            "source_published_at": "2026-09-18 05:00:00",
        },
        {
            "id": "declared-unknown",
            "published_at": "",
            "source_published_at": "Thu, 17 Sep 2026 20:00:00 -0700",
            "publication_time_state": "UNKNOWN",
        },
    ]
    original_raw_publication = [record["source_published_at"] for record in records]
    monkeypatch.setattr(web_discovery, "brand_queries", lambda *_args, **_kwargs: ["query"])
    monkeypatch.setattr(
        web_discovery, "_search_google_news_rss",
        lambda _query: [dict(record) for record in records],
    )

    items, total = web_discovery.discover_brand_industry(brands=["brand"])

    assert total == 1
    assert [item["id"] for item in items] == [
        "later-instant", "first-equal-instant", "second-equal-instant",
        "naive-unknown", "declared-unknown",
    ]
    assert [record["source_published_at"] for record in records] == original_raw_publication
    assert items[-1]["publication_time_state"] == "UNKNOWN"


def test_empty_rss_is_no_new_data_but_transport_failure_is_unavailable(monkeypatch):
    import web_discovery
    from lumenis.system.collector.adapters import public_source

    response = PublicResponse(
        url="https://news.google.com/rss/search?q=lumenis",
        content=b"<rss><channel></channel></rss>",
        content_type="application/rss+xml", status_code=200,
    )
    monkeypatch.setattr(public_source, "fetch_public_url", lambda *_args, **_kwargs: response)
    empty = WebRSSAdapter().search("lumenis", max_results=1)

    def unavailable(*_args, **_kwargs):
        raise public_source.PublicSourceError("offline fixture")

    monkeypatch.setattr(public_source, "fetch_public_url", unavailable)
    failed = WebRSSAdapter().search("lumenis", max_results=1)

    assert empty.status is CollectionStatus.NO_NEW_DATA
    assert empty.metadata.get("error_type") is None
    assert failed.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert failed.items == []
    assert failed.metadata["error_type"] == "PublicSourceError"


@pytest.mark.parametrize("pub_date", ["2026-09-17 04:00:00", "not-a-date"])
def test_rss_date_without_timezone_or_parseable_value_remains_unknown(monkeypatch, pub_date):
    import web_discovery
    from lumenis.system.collector.adapters import public_source

    xml = f"""<rss><channel><item><title>Undated result</title>
      <link>https://publisher.example.test/undated</link><pubDate>{pub_date}</pubDate>
    </item></channel></rss>"""
    response = PublicResponse(
        url="https://news.google.com/rss/search?q=lumenis",
        content=xml.encode("utf-8"), content_type="application/rss+xml", status_code=200,
    )
    monkeypatch.setattr(public_source, "fetch_public_url", lambda *_args, **_kwargs: response)

    outcome = web_discovery.fetch_google_news_rss("lumenis", max_results=1)

    assert outcome["ok"] is True
    assert outcome["items"][0]["published_at"] == ""
    assert outcome["items"][0]["source_published_at"] == pub_date
    assert outcome["items"][0]["publication_time_state"] == "UNKNOWN"


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
