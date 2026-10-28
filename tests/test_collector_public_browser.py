"""Bounded Source/Browser regressions; fixtures are never live acceptance.

The browser checks launch only a fresh anonymous installed SYSTEM runtime. All
transport bytes are local test fixtures; no platform, account or DB is touched.
"""
import json
import unittest
from unittest.mock import patch

from lumenis.system.collector.adapters import browser as transport
from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters.channels import ChannelsAdapter
from lumenis.system.collector.adapters.linkedin import LinkedInAdapter
from lumenis.system.collector.adapters.public_source import PublicResponse, PublicSourceError, PublicSourceHTTPError
from lumenis.system.collector.adapters.reddit import RedditAdapter
from lumenis.system.collector.adapters.tieba import TiebaAdapter
from lumenis.system.collector.adapters.youtube import YouTubeAdapter


def document(url, text, mime="text/html"):
    return PublicResponse(url, text.encode(), mime, 200, requested_url=url)


class PublicBrowserBoundaryTests(unittest.TestCase):
    def test_installed_runtime_visible_native_read_and_original_custody(self):
        url = "https://www.youtube.com/watch?v=abcdefghijk"
        html = """<html><title>Public source fixture</title><body>
          <button id="read-more">More comments</button><script>
          document.querySelector('#read-more').onclick=async()=>{
            const r=await fetch('/youtubei/v1/next',{method:'POST',headers:{'Content-Type':'application/json'},
              body:JSON.stringify({context:{client:{clientName:'WEB'}},continuation:'native-next'})});
            window.observed=await r.json();
          };</script></body></html>"""
        original = document(url, html)
        native = document("https://www.youtube.com/youtubei/v1/next", '{"source":"native-read"}', "application/json")
        with patch("lumenis.system.collector.adapters.public_source._resolved_addresses", return_value=("93.184.216.34",)), \
                patch.object(transport, "fetch_public_url", return_value=original) as get, \
                patch.object(transport, "_native_post", return_value=native) as post:
            observed = transport.fetch_public_browser(url, allowed_host_suffixes=("youtube.com",),
                capture_paths=(r"/youtubei/v1/next",), request_keys=("continuation",),
                cursor={"path": "/youtubei/v1/next", "request": {"continuation": "native-next"}},
                read_controls=("#read-more",), max_steps=2,
                extraction_script="() => ({native:window.observed || null})")
        self.assertTrue(observed.cursor_reached)
        self.assertEqual(observed.native_pages[0]["request"], {"continuation": "native-next"})
        self.assertEqual(observed.extraction["native"], {"source": "native-read"})
        self.assertEqual(observed.originals, (original, native))
        self.assertNotEqual(observed.document.content, original.content)
        self.assertEqual(get.call_count, 1)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(set(post.call_args.kwargs), {"allowed_host_suffixes", "timeout", "max_bytes"})

    def test_denial_and_private_subrequests_stop_without_backend_switch(self):
        url = "https://www.youtube.com/watch?v=abcdefghijk"
        # A document navigation reaches the routing guard. Chromium can block
        # a mixed-content fetch before the Source callback, which would test
        # the browser's own PNA policy rather than this helper's boundary.
        html = """<html><title>Public document</title><body>Source body
          <iframe src="https://127.0.0.1/private"></iframe></body></html>"""
        with patch("lumenis.system.collector.adapters.public_source._resolved_addresses", return_value=("93.184.216.34",)), \
                patch.object(transport, "fetch_public_url", return_value=document(url, html)) as read:
            with self.assertRaises(PublicSourceError):
                transport.fetch_public_browser(url, allowed_host_suffixes=("youtube.com",), max_steps=1)
        self.assertEqual(read.call_count, 1)
        calls = []
        def denied(*args, **kwargs):
            calls.append(args[0])
            raise PublicSourceHTTPError(403)
        with patch.object(transport, "fetch_public_browser", side_effect=AssertionError("fallback forbidden")):
            result = YouTubeAdapter(provider_config={}, public_fetcher=denied).detail("abcdefghijk")
        self.assertEqual(result.status, CollectionStatus.BLOCKED)
        self.assertEqual(len(calls), 1)
        self.assertIsNone(result.backend)

    def test_cursor_requires_named_read_fields_and_public_source_scope(self):
        factory = unittest.mock.Mock()
        with self.assertRaises(PublicSourceError):
            transport.fetch_public_browser("https://www.youtube.com/watch?v=abcdefghijk",
                allowed_host_suffixes=("youtube.com",), capture_paths=(r"/youtubei/v1/next",),
                cursor={"path": "/youtubei/v1/next", "request": {"Authorization": "forbidden"}},
                browser_factory=factory)
        factory.assert_not_called()


class PlatformOpenCliAdoptionTests(unittest.TestCase):
    def test_youtube_modern_selected_channel_grid_and_complete_description(self):
        item = {"richItemRenderer": {"content": {"lockupViewModel": {
            "contentType": "LOCKUP_CONTENT_TYPE_VIDEO", "contentId": "abcdefghijk",
            "metadata": {"lockupMetadataViewModel": {"title": {"content": "Native title"}}}}}}}
        initial = {"contents": {"twoColumnBrowseResultsRenderer": {"tabs": [
            {"tabRenderer": {"selected": False, "content": {"richGridRenderer": {"contents": [
                {"videoRenderer": {"videoId": "zzzzzzzzzzz", "title": {"simpleText": "Other tab"}}}]}}}},
            {"tabRenderer": {"selected": True, "content": {"richGridRenderer": {"contents": [item]}}}}]}}}
        def fetch(url, **kwargs):
            return document(url, '<script>window["ytInitialData"] = ' + json.dumps(initial) + ';</script>')
        result = YouTubeAdapter(provider_config={}, public_fetcher=fetch).author_posts("@source")
        self.assertEqual(result.status, CollectionStatus.SUCCESS)
        self.assertEqual([x["platform_content_id"] for x in result.items], ["abcdefghijk"])
        self.assertIsNone(result.items[0]["likes"])
        full = "complete public description " * 300
        player = {"videoDetails": {"videoId": "abcdefghijk", "title": "Title", "shortDescription": "short"}}
        primary = {"contents": {"twoColumnWatchNextResults": {"results": {"results": {
            "contents": [{"videoSecondaryInfoRenderer": {"attributedDescription": {"content": full}}}]}}}}}
        body = '<script>var ytInitialData=' + json.dumps(primary) + '; var ytInitialPlayerResponse=' + json.dumps(player) + ';</script>'
        result = YouTubeAdapter(provider_config={}, public_fetcher=lambda url, **kw: document(url, body)).detail("abcdefghijk")
        self.assertEqual(result.items[0]["content"], full)

    def test_youtube_browser_comment_entities_keep_native_reply_cursor(self):
        full = "Full comment body " * 100
        thread = {"commentThreadRenderer": {"commentViewModel": {"commentViewModel": {"commentId": "top"}},
            "replies": {"continuationItemRenderer": {"continuationEndpoint": {
                "continuationCommand": {"token": "reply-next"},
                "commandMetadata": {"webCommandMetadata": {"apiUrl": "/youtubei/v1/next"}}}}}}}
        entity = {"commentEntityPayload": {"properties": {"commentId": "top", "content": {"content": full}},
            "author": {"channelId": "UC_native", "displayName": "Source"}, "toolbar": {}}}
        initial = {"thread": thread, "entity": entity}
        original = document("https://www.youtube.com/watch?v=abcdefghijk", "<html>source original</html>")
        observed = transport.PublicBrowserDocument(original, (original,), (), {"initial": initial}, 1, True)
        with patch.object(transport, "fetch_public_browser", return_value=observed):
            result = YouTubeAdapter(provider_config={}).comments("abcdefghijk", include_replies=True, public_transport="browser")
        self.assertEqual(result.comments[0]["content"], full)
        self.assertIsNone(result.comments[0]["likes"])
        cursor = result.metadata["pagination"]["next_cursor"]
        self.assertEqual(cursor["pending"][0]["parent_comment_id"], "top")
        reply = {"frameworkUpdates": {"entityBatchUpdate": {"mutations": [{"payload": {
            "commentEntityPayload": {"properties": {"commentId": "reply", "replyLevel": 1, "content": {"content": "Native reply"}}}}}]}}}
        observed = transport.PublicBrowserDocument(original, (original,), ({"path": "/youtubei/v1/next",
            "request": {"continuation": "reply-next"}, "objects": [reply]},), {"initial": {}}, 2, True)
        with patch.object(transport, "fetch_public_browser", return_value=observed):
            resumed = YouTubeAdapter(provider_config={}).comments("abcdefghijk", include_replies=True,
                public_transport="browser", cursor=cursor)
        self.assertEqual(resumed.comments[0]["parent_comment_id"], "top")
        self.assertIsNone(resumed.metadata["pagination"]["next_cursor"])

    def test_reddit_ranked_public_identity_and_negative_net_votes(self):
        tracking = json.dumps({"post": {"id": "t3_ab123"}})
        html = '<div data-testid="search-post-unit" score="-12"><h2>Public title</h2><search-telemetry-tracker data-faceplate-tracking-context=\'' + tracking + '\'></search-telemetry-tracker><a href="/r/test/comments/ab123/title/">source</a></div>'
        result = RedditAdapter(provider_config={}, public_fetcher=lambda url, **kw: document(url, html)).search("term")
        self.assertEqual(result.status, CollectionStatus.SUCCESS)
        self.assertEqual(result.items[0]["platform_content_id"], "ab123")
        self.assertEqual(result.items[0]["net_votes"], -12)
        self.assertIsNone(result.items[0]["likes"])
        self.assertEqual(result.items[0]["raw"]["score"], -12)

    def test_linkedin_post_root_scope_keeps_author_identity_and_full_body(self):
        text = "Full public post " * 200
        html = '<main><article><a href="https://www.linkedin.com/company/source/">Source</a><a href="https://www.linkedin.com/posts/source_activity-12345-ab/">Permalink</a><div class="update-components-text">' + text + '</div><time datetime="2026-10-25T12:00:00Z"></time></article><aside><a href="https://www.linkedin.com/posts/other_activity-55555-ab/">Navigation</a></aside></main>'
        result = LinkedInAdapter(provider_config={}, public_fetcher=lambda url, **kw: document(url, html)).author_posts("company:source")
        self.assertEqual(result.status, CollectionStatus.SUCCESS)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0]["platform_content_id"], "urn:li:activity:12345")
        self.assertEqual(result.items[0]["content"], text.strip())
        self.assertEqual(result.items[0]["publish_datetime"], "2026-10-25T12:00:00Z")

    def test_tieba_modern_public_thread_does_not_invent_floor_id_or_time(self):
        url = "https://tieba.baidu.com/p/12345?pn=1"
        original = document(url, "<html><title>Public thread</title></html>")
        payload = {"page_meta": {"pathname": "/p/12345", "pn": "1"},
            "main": {"title": "Source thread", "content": "Public original body", "author": "User", "media": []}, "replies": []}
        observed = transport.PublicBrowserDocument(original, (original,), (), payload, 1, True)
        with patch.object(transport, "fetch_public_browser", return_value=observed):
            result = TiebaAdapter(provider_config={}).detail("12345", public_transport="browser")
        self.assertEqual(result.status, CollectionStatus.SUCCESS)
        self.assertEqual(result.items[0]["platform_content_id"], "12345")
        self.assertIsNone(result.items[0]["raw"]["post_id"])
        self.assertIsNone(result.items[0]["publish_datetime"])

    def test_channels_public_url_identity_works_without_platform_api(self):
        url = "https://weixin.qq.com/sph/example"
        html = '<script type="application/ld+json">{"@type":"VideoObject","name":"Public share","description":"Observed body"}</script>'
        result = ChannelsAdapter(provider_config={}, public_fetcher=lambda target, **kw: document(target, html)).detail(url)
        self.assertEqual(result.status, CollectionStatus.SUCCESS)
        self.assertIsNone(result.items[0]["raw"]["object_id"])
        self.assertEqual(result.items[0]["raw"]["source_identity_kind"], "PUBLIC_URL_SHA256")

    def test_public_only_platform_does_not_ignore_explicit_official_mode(self):
        fetcher = unittest.mock.Mock(side_effect=AssertionError("public fallback forbidden"))
        adapter = TiebaAdapter(provider_config={}, public_fetcher=fetcher)
        for operation, target in ((adapter.search, "term"), (adapter.detail, "12345"),
                (adapter.comments, "12345"), (adapter.author, "un:user"), (adapter.author_posts, "un:user")):
            result = operation(target, provider_mode="official")
            self.assertEqual(result.status, CollectionStatus.NOT_SUPPORTED)
            self.assertEqual(result.attempted_backend, "tieba_official_api")
            self.assertIsNone(result.backend)
        fetcher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
