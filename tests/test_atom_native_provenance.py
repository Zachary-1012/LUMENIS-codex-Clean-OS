"""Atom source identity and native metric truth at the Collector boundary."""

from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters import public_source
from lumenis.system.collector.adapters.public_source import PublicResponse, PublicSourceError
from lumenis.system.collector.adapters.web_atom import AtomAdapter


FEED_URL = "https://public.example.test/feed.atom"


def _atom(entry_channel: str = "UCapproved") -> bytes:
    return f"""<?xml version="1.0" encoding="utf-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:yt="http://www.youtube.com/xml/schemas/2015"
          xmlns:media="http://search.yahoo.com/mrss/">
      <title>Official Brand Channel</title>
      <entry>
        <id>tag:public.example.test,2026:video-01</id>
        <yt:videoId>abc12345678</yt:videoId>
        <yt:channelId>{entry_channel}</yt:channelId>
        <title>New release</title>
        <link href="https://public.example.test/items/abc12345678" />
        <published>2026-09-24T14:02:37+00:00</published>
        <author><name>Official Brand Channel</name></author>
        <media:group>
          <media:thumbnail url="https://i.example.test/thumb.jpg" />
          <media:community>
            <media:starRating count="123" average="5.00" min="1" max="5" />
            <media:statistics views="3025" />
          </media:community>
        </media:group>
      </entry>
    </feed>""".encode()


def _adapter(xml: bytes, fetches: list[str] | None = None) -> AtomAdapter:
    def fetch(source: str) -> PublicResponse:
        if fetches is not None:
            fetches.append(source)
        return PublicResponse(
            url=source, content=xml, content_type="application/atom+xml", status_code=200,
        )

    return AtomAdapter(fetcher=fetch)


def test_atom_keeps_native_identity_views_and_unknown_interactions():
    result = _adapter(_atom()).search(FEED_URL)
    assert result.status is CollectionStatus.SUCCESS
    item = result.items[0]
    assert item["author_id"] == "UCapproved"
    assert item["raw"]["video_id"] == "abc12345678"
    assert item["raw"]["channel_id"] == "UCapproved"
    assert item["raw"]["view_count"] == 3025
    assert item["raw"]["media_list"] == [{"url": "https://i.example.test/thumb.jpg"}]
    assert item["raw"]["media_starrating"]["count"] == "123"
    assert item["likes"] is None
    assert item["comments"] is None
    assert item["shares"] is None
    assert item["publish_datetime"] != item["captured_at"]


def test_public_youtube_feed_uses_existing_atom_fetch_and_checks_channel_identity():
    fetches: list[str] = []
    result = _adapter(_atom(), fetches).search(
        "https://www.youtube.com/feeds/videos.xml?channel_id=UCapproved"
    )
    assert result.status is CollectionStatus.SUCCESS
    assert len(fetches) == 1 and result.items[0]['raw']['channel_id'] == 'UCapproved'
    mismatched = _adapter(_atom()).search('https://m.youtube.com/feeds/videos.xml?channel_id=another-channel')
    assert mismatched.status is CollectionStatus.PROVIDER_UNAVAILABLE and not mismatched.items


def test_public_source_transport_accepts_public_youtube_feed_and_retains_ssrf_guard(monkeypatch):
    from types import SimpleNamespace
    calls: list[str] = []
    monkeypatch.delenv('LUMENIS_PUBLIC_SOURCE_DOH_FALLBACK',raising=False)
    monkeypatch.setattr(public_source,'load_public_source_host_pins',lambda:{})
    monkeypatch.setattr(public_source,'_resolved_addresses',lambda _:['8.8.8.8'])
    def get(_session,url,**kwargs):
        calls.append(url)
        assert kwargs['verify'] is True and kwargs['allow_redirects'] is False
        assert 'Authorization' not in kwargs['headers'] and 'Cookie' not in kwargs['headers']
        return SimpleNamespace(status_code=200,url=url,headers={'Content-Type':'application/atom+xml'},
            iter_content=lambda **_:iter([_atom()]),close=lambda:None)
    monkeypatch.setattr(public_source.requests.Session,'get',get)
    url = 'https://m.youtube.com/feeds/videos.xml?channel_id=UCapproved'
    result = AtomAdapter().search(url)
    assert result.status is CollectionStatus.SUCCESS and calls == [url]
    monkeypatch.setattr(public_source,'_resolved_addresses',lambda _:['127.0.0.1'])
    try:
        public_source.fetch_public_url(url)
    except PublicSourceError as exc:
        assert 'private or local' in str(exc)
    else:
        raise AssertionError('a public Feed hostname must not bypass private-address rejection')
    assert calls == [url]


def test_atom_without_entry_identity_is_not_silent_empty_success():
    xml = b"""<feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Untethered</title><summary>No identity</summary></entry>
    </feed>"""
    result = _adapter(xml).search("https://example.test/feed.atom")
    assert result.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.items == []
