"""A public article must not be replaced by its publisher's generic blurb."""

import hashlib

import pytest

from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
from lumenis.system.collector.adapters.public_source import PublicResponse


def test_public_dom_media_is_reopenable_in_native_projection_without_extra_fetch():
    from lumenis.system.collector.adapters.secondary_collection import _native_record
    from lumenis.system.collector.adapters.platform_naming import map_raw_to_normalized
    html = b'''<html><head><title>Media source</title></head><body>
        <header><img src="/navigation-logo.png"></header><article id="story">
        <p>Actual publisher source text.</p><img data-src="/original.png" alt="Source image">
        <video poster="/poster.jpg"><source src="https://cdn.example.test/original.mp4" type="video/mp4">
        <track src="/captions.vtt" kind="subtitles" srclang="en"></video>
        <audio src="/original.wav"></audio><iframe src="https://www.youtube.com/embed/abcdefghijk"></iframe>
        <iframe src="https://unknown-embed.example.test/page"></iframe>
        <aside><img src="/sidebar.png"></aside></article></body></html>'''
    source = 'https://publisher.example.test/news/article'
    calls = []
    def fetch(url):
        calls.append(url)
        return PublicResponse(source,html,'text/html',200)
    result = PublicHttpAdapter(fetcher=fetch).search(source)
    assert result.ok and calls == [source]
    item = result.items[0]
    record = _native_record(item,'public_http',source,item['captured_at'])
    normalized = map_raw_to_normalized(record,'public_http')
    media = normalized['media_list']
    assert item['cover'] == 'https://publisher.example.test/original.png'
    assert {entry['media_type'] for entry in media} == {'image','video','audio','timed_text','embed'}
    assert all(entry['bytes_state'] == 'NOT_ACQUIRED' for entry in media)
    assert 'navigation-logo' not in str(media) and 'sidebar.png' not in str(media)
    assert next(entry for entry in media if entry['media_type']=='video')['url'] == 'https://cdn.example.test/original.mp4'
    embed = next(entry for entry in media if entry['media_type']=='embed')
    assert embed['url'] is None and embed['observed_page_url'].startswith('https://unknown-embed.example.test/')
    player = next(entry for entry in media if entry.get('acquisition'))
    assert player['url'] == 'https://www.youtube.com/embed/abcdefghijk'
    assert player['acquisition']['representation'] == 'PLAYER_SOURCE'
    caption = next(entry for entry in media if entry['media_type']=='timed_text')
    assert caption['url'] is None and caption['observed_text_url'].endswith('/captions.vtt')
    assert item['raw']['media_observation']['copyright_license'] == 'NOT_ESTABLISHED'
    assert item['raw']['body_scope']['whole_article_verified'] is False


def test_media_v1_replay_preserves_old_observation_and_v2_declares_actual_manifest_only():
    source = PublicResponse('https://publisher.example.test/source',b'<main>Source'
        b'<video><source src="https://cdn.example.test/master.m3u8" type="application/x-mpegurl"></video>'
        b'<audio src="https://cdn.example.test/audio.mpd"></audio>'
        b'<iframe src="https://www.youtube.com/embed/abcdefghijk"></iframe>'
        b'<img src="/original.png"></main>','text/html',200)
    v1 = PublicHttpAdapter._item(source,media_schema='public-http-dom-media/v1')
    assert all('acquisition' not in item for item in v1['raw']['media_list'])
    assert v1['raw']['media_list'][2]['url'] is None
    current = PublicHttpAdapter._item(source)
    assert current['raw']['media_observation']['schema'] == 'public-http-dom-media/v2'
    assert [item.get('acquisition',{}).get('protocol') for item in current['raw']['media_list']] == ['m3u8','dash','https',None]
    assert current['content'] == v1['content'] and current['raw']['content_observation'] == v1['raw']['content_observation']


def test_public_dom_media_retains_unresolved_positions_and_blocks_sensitive_url_projection():
    response = PublicResponse('https://publisher.example.test/source',
        b'<main>Source text<img src="/image.png?token=do-not-export"><img src="data:image/png;base64,abc">'
        b'<video data-id="native-video-without-url"></video><img src="/safe.png#display"></main>', 'text/html',200)
    item = PublicHttpAdapter._item(response)
    media = item['raw']['media_list']
    assert len(media) == 4 and [entry['url'] for entry in media[:3]] == [None,None,None]
    assert media[-1]['url'] == 'https://publisher.example.test/safe.png'
    assert 'do-not-export' not in str(media)
    assert all(entry['native_locator']['element'] for entry in media)


def test_media_after_text_preview_limit_is_retained_without_claiming_full_article():
    from lumenis.system.collector.adapters.public_http import MAX_PUBLIC_BODY_CHARS
    response = PublicResponse('https://publisher.example.test/long',
        ('<article>' + 'A'*(MAX_PUBLIC_BODY_CHARS+20) + '<img src="/late-original.png"></article>').encode(),
        'text/html',200)
    item = PublicHttpAdapter._item(response)
    assert item['raw']['content_observation']['completeness'] == 'TRUNCATED_SEMANTIC_PREVIEW'
    assert item['raw']['body_scope']['returned_text_truncated'] is True
    assert item['raw']['body_scope']['selected_dom_text_complete'] is False
    assert item['raw']['body_scope']['whole_article_verified'] is False
    assert item['raw']['media_list'][0]['url'].endswith('/late-original.png')


def test_media_inventory_budget_records_actual_omissions_and_base_srcset():
    from lumenis.system.collector.adapters.public_http import MAX_PUBLIC_MEDIA_REFERENCES
    response = PublicResponse('https://publisher.example.test/source',
        ('<head><base href="https://cdn.example.test/assets/"></head><main>Source text'
         '<img srcset="one.png 1x, two.png 2x">'
         + ''.join(f'<img src="{index}.png">' for index in range(MAX_PUBLIC_MEDIA_REFERENCES)) + '</main>').encode(),
        'text/html',200)
    item = PublicHttpAdapter._item(response)
    observed = item['raw']['media_observation']
    assert observed['retained_reference_count'] == MAX_PUBLIC_MEDIA_REFERENCES
    assert observed['reference_count'] == MAX_PUBLIC_MEDIA_REFERENCES+2
    assert observed['omitted_reference_count'] == 2 and observed['truncated'] is True
    assert item['raw']['media_list'][0]['url'] == 'https://cdn.example.test/assets/one.png'


def test_substantial_article_content_and_declared_date_survive_capture():
    body = "2025年广州消费市场运行情况。" + "零售总额同比增长，统计口径见原文。" * 30
    response = PublicResponse(
        url="https://public.example.test/article",
        content=(
            '<html><head><title>广州市消费市场</title>'
            '<meta name="description" content="广州市统计局网站介绍">'
            '<meta name="PubDate" content="2026-01-30 16:00:00"></head>'
            f'<body><div class="zw">{body}</div></body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )
    item = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)

    assert item.status is CollectionStatus.SUCCESS
    assert item.items[0]["content"].startswith("2025年广州消费市场运行情况")
    assert item.items[0]["publish_datetime"] == "2026-01-30 16:00:00"


def test_cross_host_canonical_cannot_replace_the_fetched_source_identity():
    for canonical_hint in (
        "http://127.0.0.1/private",
        "http://public.example.test/article",
    ):
        response = PublicResponse(
            url="https://public.example.test/article",
            requested_url="https://public.example.test/start",
            content=(
                '<html><head><link rel="canonical" href="'
                + canonical_hint + '"></head><body>Source page</body></html>'
            ).encode("utf-8"),
            content_type="text/html",
            status_code=200,
        )
        result = PublicHttpAdapter(fetcher=lambda _: response).search(response.requested_url)

        assert result.status is CollectionStatus.SUCCESS
        assert result.items[0]["url"] == response.url
        assert result.metadata["final_source_url"] == response.url


def test_title_only_page_is_not_reported_as_captured_content():
    response = PublicResponse(
        url="https://public.example.test/identity",
        content=b"<html><head><title>Known venue</title></head><body></body></html>",
        content_type="text/html",
        status_code=200,
    )
    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)

    assert result.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.items == []
    assert result.metadata["error_type"] == "EMPTY_CONTENT"


def test_public_http_rate_limit_preserves_server_wait_and_blocks_followup(monkeypatch):
    from lumenis.system.collector.adapters.public_source import PublicSourceHTTPError
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter

    limiter = AdaptiveRateLimiter(
        base_interval=0, min_interval=0, max_interval=0,
        cooldown_seconds=5, jitter=False,
    )
    monkeypatch.setattr(PublicHttpAdapter, "_document_limiter", limiter)
    calls = []

    def rate_limited(url):
        calls.append(url)
        raise PublicSourceHTTPError(429, retry_after_seconds=120)

    adapter = PublicHttpAdapter(fetcher=rate_limited)
    source = "https://publisher.example.test/rate-limited"
    result = adapter.search(source)

    assert result.status is CollectionStatus.COOLING_DOWN
    assert result.metadata["http_status"] == 429
    assert result.metadata["retry_after_seconds"] >= 110
    assert result.metadata["network_attempted"] is True
    assert limiter.remaining_cooldown() >= 110

    followup = adapter.search(source)
    assert followup.status is CollectionStatus.COOLING_DOWN
    assert followup.metadata["network_attempted"] is False
    assert followup.metadata["retry_after_seconds"] >= 110
    assert calls == [source]


def test_public_http_default_transport_receives_task_cancellation(monkeypatch):
    import lumenis.system.collector.adapters.public_http as public_http
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter

    limiter = AdaptiveRateLimiter(base_interval=0, min_interval=0, jitter=False)
    monkeypatch.setattr(public_http.PublicHttpAdapter, "_document_limiter", limiter)
    calls = []
    inside_transport = False

    def stop_inside_transport():
        if inside_transport:
            raise InterruptedError("COLLECTION_ATTEMPT_NO_LONGER_ACTIVE")

    def transport_fetch(url, *, check_continue=None):
        nonlocal inside_transport
        calls.append(url)
        inside_transport = True
        check_continue()
        raise AssertionError("a cancelled public read must not continue")

    monkeypatch.setattr(public_http, "fetch_public_url", transport_fetch)
    adapter = public_http.PublicHttpAdapter()

    with pytest.raises(InterruptedError, match="COLLECTION_ATTEMPT_NO_LONGER_ACTIVE"):
        adapter.search(
            "https://publisher.example.test/cancel-during-response",
            check_continue=stop_inside_transport,
        )

    assert calls == ["https://publisher.example.test/cancel-during-response"]
    assert limiter.consecutive_fail == 0


def test_public_http_rejected_default_document_reports_network_attempt(monkeypatch):
    import lumenis.system.collector.adapters.public_http as public_http
    from lumenis.system.collector.guard.rate_limiter import AdaptiveRateLimiter

    response = PublicResponse(
        "https://publisher.example.test/non-html",
        b"%PDF-1.7", "application/pdf", 200,
    )
    monkeypatch.setattr(public_http, "fetch_public_url", lambda _url: response)
    monkeypatch.setattr(
        public_http.PublicHttpAdapter, "_document_limiter",
        AdaptiveRateLimiter(base_interval=0, min_interval=0, jitter=False),
    )

    result = public_http.PublicHttpAdapter().search(response.url)

    assert result.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.metadata["network_attempted"] is True


def test_fix094_sibling_article_selection_scales_linearly(monkeypatch):
    """FIX-094: sibling article dedup checks selected ancestors in linear work."""
    import lumenis.system.collector.adapters.public_http as public_http
    from bs4 import BeautifulSoup

    article_count = 500
    soup = BeautifulSoup(
        "<html><body>" + "".join(
            f"<article>article {index}</article>" for index in range(article_count)
        ) + "</body></html>",
        "html.parser",
    )
    yielded = 0

    def counting_any(values):
        nonlocal yielded
        for value in values:
            yielded += 1
            if value:
                return True
        return False

    monkeypatch.setattr(public_http, "any", counting_any, raising=False)
    selected = public_http._selected_substantive_nodes(soup)

    assert len(selected) == article_count
    assert yielded < article_count * 25


def test_meta_description_is_marked_as_an_excerpt():
    response = PublicResponse(
        url="https://public.example.test/description-only",
        content=(
            '<html><head><title>Public title</title>'
            '<meta name="description" content="Publisher summary only"></head>'
            '<body><p>Navigation and other non-article text.</p></body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )

    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)
    item = result.items[0]
    observation = item["raw"]["content_observation"]

    assert result.status is CollectionStatus.SUCCESS
    assert item["content"] == "Publisher summary only"
    assert observation["selection"] == "meta_description"
    assert observation["selected_block_count"] == 0
    assert observation["completeness"] == "DESCRIPTION_EXCERPT"
    assert observation["truncated"] is False


def test_json_ld_publication_time_is_preserved_with_timezone():
    from data_quality_gate import DataQualityGate

    response = PublicResponse(
        url="https://public.example.test/news",
        content=(
            '<html><head><title>Brand news</title>'
            '<script type="application/ld+json">'
            '{"@type":"NewsArticle","datePublished":"2026-09-09T07:00:00-07:00"}'
            '</script></head><body>Brand release body.</body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )
    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)

    assert result.status is CollectionStatus.SUCCESS
    assert result.items[0]["publish_datetime"] == "2026-09-09T07:00:00-07:00"
    assert result.metadata["publication_date_state"] == "declared"
    assert DataQualityGate().validate("note", {
        "title": "Brand news", "url": response.url, "risk_level": "low",
        "publish_date": result.items[0]["publish_datetime"],
    })["valid"] is True


def test_conflicting_visible_and_structured_publication_dates_remain_unknown():
    response = PublicResponse(
        url="https://public.example.test/news",
        content=(
            '<html><head><title>Brand news</title>'
            '<script type="application/ld+json">'
            '{"@type":"NewsArticle","datePublished":"2026-08-25"}'
            '</script></head><body><span class="section-date">, \n Aug 19, 2026</span>'
            'Brand release body.</body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )
    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)

    assert result.status is CollectionStatus.SUCCESS
    assert result.items[0]["publish_datetime"] == ""
    assert result.metadata["publication_date_state"] == "conflict"


def test_adapter_health_distinguishes_missing_source_from_a_manual_attempt():
    adapter = PublicHttpAdapter(fetcher=lambda _: None)

    assert adapter.health_check().status is CollectionStatus.NOT_CONFIGURED
    assert adapter.health_check(url="https://public.example.test/article").status is CollectionStatus.NEED_VERIFY
    assert adapter.search("").status is CollectionStatus.NOT_CONFIGURED


def test_publisher_article_body_and_visible_date_beat_a_generic_description():
    article = "Taikoo Hui Guangzhou's tenant programme. " * 20
    response = PublicResponse(
        url="https://public.example.test/news",
        content=(
            '<html><head><title>Venue update</title>'
            '<meta name="description" content="Publisher home page"></head><body>'
            '<div class="block-text-only"><div class="container-sm">'
            '<p class="small">10 Sep 2021</p><p>' + article + '</p>'
            '</div></div></body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )
    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)

    assert result.status is CollectionStatus.SUCCESS
    assert result.items[0]["content"].startswith("10 Sep 2021 Taikoo Hui Guangzhou")
    assert result.items[0]["publish_datetime"] == "2021-09-10"


def test_independent_semantic_articles_keep_both_bodies_and_locators():
    first = "First publisher block carries the original report."
    second = "Second publisher block carries the correction and context."
    response = PublicResponse(
        url="https://public.example.test/multi-article",
        content=(
            '<html><head><title>Multi-source page</title>'
            '<meta property="article:published_time" '
            'content="2026-09-18T04:00:00-07:00"></head><body><main>'
            f'<article id="story-one"><p>{first}</p></article>'
            f'<article id="story-two"><p>{second}</p></article>'
            '</main></body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )

    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)
    item = result.items[0]
    observation = item["raw"]["content_observation"]
    expected = first + "\n\n" + second

    assert result.status is CollectionStatus.SUCCESS
    assert item["content"] == expected
    assert item["publish_datetime"] == "2026-09-18T04:00:00-07:00"
    assert observation["selection"] == "semantic_blocks"
    assert observation["selected_block_count"] == 2
    assert len(observation["selected_locators"]) == 2
    assert any("#story-one" in locator for locator in observation["selected_locators"])
    assert any("#story-two" in locator for locator in observation["selected_locators"])
    assert observation["source_text_sha256"] == hashlib.sha256(expected.encode("utf-8")).hexdigest()
    assert observation["source_text_char_length"] == len(expected)
    assert observation["returned_text_char_length"] == len(expected)
    assert observation["truncated"] is False
    assert observation["completeness"] == "COMPLETE_SEMANTIC_TEXT"


def test_nested_semantic_article_is_not_counted_twice():
    outer = "Outer publisher text appears once."
    inner = "Nested publisher correction appears once."
    response = PublicResponse(
        url="https://public.example.test/nested-article",
        content=(
            '<html><head><title>Nested article</title></head><body>'
            f'<article id="outer"><p>{outer}</p><section>'
            f'<article id="nested"><p>{inner}</p></article>'
            '</section></article></body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )

    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)
    item = result.items[0]
    observation = item["raw"]["content_observation"]

    assert result.status is CollectionStatus.SUCCESS
    assert item["content"].count(outer) == 1
    assert item["content"].count(inner) == 1
    assert observation["selected_block_count"] == 1
    assert len(observation["selected_locators"]) == 1
    assert "#outer" in observation["selected_locators"][0]


def test_nested_page_chrome_does_not_enter_article_text_or_attestation():
    article = "Verified publisher article text remains the selected source. " * 20
    chrome = {
        "nav": "NAVIGATION LEAK " * 120,
        "footer": "FOOTER LEAK " * 120,
        "header": "HEADER LEAK " * 120,
        "aside": "ASIDE LEAK " * 120,
        "form": "FORM LEAK " * 120,
        "noscript": "NOSCRIPT LEAK " * 120,
        "role-nav": "ARIA NAVIGATION LEAK " * 120,
    }
    response = PublicResponse(
        url="https://public.example.test/article-with-page-chrome",
        content=(
            '<html><head><title>Article with page chrome</title></head><body>'
            '<article id="story"><p>' + article + '</p>'
            '<div><nav><div><span>' + chrome["nav"] + '</span></div></nav></div>'
            '<div><footer><div><span>' + chrome["footer"] + '</span></div></footer></div>'
            '<div><header><div><span>' + chrome["header"] + '</span></div></header></div>'
            '<div><aside><div><span>' + chrome["aside"] + '</span></div></aside></div>'
            '<div><form><div><span>' + chrome["form"] + '</span></div></form></div>'
            '<div><noscript><div><span>' + chrome["noscript"] + '</span></div></noscript></div>'
            '<div role="navigation"><div><span>' + chrome["role-nav"] + '</span></div></div>'
            '<script>SECRET_JS_PAYLOAD</script><style>STYLE_PAYLOAD</style>'
            '<template>TEMPLATE_PAYLOAD</template>'
            '</article></body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )

    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)
    item = result.items[0]
    observation = item["raw"]["content_observation"]

    assert result.status is CollectionStatus.SUCCESS
    assert item["content"] == article.strip()
    assert all(marker not in item["content"] for marker in (
        "NAVIGATION LEAK", "FOOTER LEAK", "HEADER LEAK", "ASIDE LEAK",
        "FORM LEAK", "NOSCRIPT LEAK", "ARIA NAVIGATION LEAK",
        "SECRET_JS_PAYLOAD", "STYLE_PAYLOAD", "TEMPLATE_PAYLOAD",
    ))
    assert observation["source_text_sha256"] == hashlib.sha256(article.strip().encode("utf-8")).hexdigest()
    assert observation["source_text_char_length"] == len(article.strip())
    assert observation["returned_text_char_length"] == len(article.strip())
    assert observation["truncated"] is False
    assert observation["completeness"] == "COMPLETE_SEMANTIC_TEXT"


def test_script_style_and_template_only_body_stays_empty_in_document_fallback():
    response = PublicResponse(
        url="https://public.example.test/script-only",
        content=(
            "<html><head><title>Publisher title</title></head><body>"
            "<script>SECRET_JS_PAYLOAD</script>"
            "<style>STYLE_PAYLOAD</style>"
            "<noscript>NOSCRIPT_PAYLOAD</noscript>"
            "<template>TEMPLATE_PAYLOAD</template>"
            "</body></html>"
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )

    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)

    assert result.status is CollectionStatus.PROVIDER_UNAVAILABLE
    assert result.items == []
    assert result.metadata["error_type"] == "EMPTY_CONTENT"


def test_document_fallback_keeps_visible_layout_text_but_excludes_executable_markup():
    response = PublicResponse(
        url="https://public.example.test/layout-fallback",
        content=(
            "<html><head><title>Fallback source</title></head><body>"
            "<header>Visible publisher heading</header>"
            "<p>Visible page copy</p>"
            "<script>SECRET_JS_PAYLOAD</script><style>STYLE_PAYLOAD</style>"
            "</body></html>"
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )

    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)
    item = result.items[0]
    observation = item["raw"]["content_observation"]

    assert result.status is CollectionStatus.SUCCESS
    assert observation["selection"] == "document_body"
    assert "Visible publisher heading" in item["content"]
    assert "Visible page copy" in item["content"]
    assert "SECRET_JS_PAYLOAD" not in item["content"]
    assert "STYLE_PAYLOAD" not in item["content"]


def test_never_content_roots_are_excluded_even_when_chrome_is_included():
    from lumenis.system.collector.adapters import public_http

    soup = public_http.BeautifulSoup(
        "<script>SECRET_JS_PAYLOAD</script><style>STYLE_PAYLOAD</style>"
        "<noscript>NOSCRIPT_PAYLOAD</noscript><template>TEMPLATE_PAYLOAD</template>",
        "html.parser",
    )

    for root in soup.find_all(("script", "style", "noscript", "template")):
        assert "".join(public_http._iter_node_text_parts(root, include_chrome=True)) == ""


def test_selected_locators_have_bounded_per_item_and_total_metadata():
    from lumenis.system.collector.adapters.public_http import (
        MAX_PUBLIC_LOCATOR_CHARS,
        MAX_PUBLIC_LOCATOR_TOTAL_CHARS,
    )

    shared_id = "shared" * 900
    articles = "".join(f"<article>Story {index}.</article>" for index in range(200))
    response = PublicResponse(
        url="https://public.example.test/locator-budget",
        content=(
            f'<html><body><section id="{shared_id}">{articles}</section></body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )

    item = PublicHttpAdapter(fetcher=lambda _: response).search(response.url).items[0]
    observation = item["raw"]["content_observation"]
    locators = observation["selected_locators"]

    assert observation["selected_block_count"] == 200
    assert observation["selected_locator_count"] == len(locators)
    assert observation["selected_locators_truncated"] is True
    assert all(len(locator) <= MAX_PUBLIC_LOCATOR_CHARS for locator in locators)
    assert sum(map(len, locators)) + max(0, len(locators) - 1) <= MAX_PUBLIC_LOCATOR_TOTAL_CHARS
    assert "Story 199." in item["content"]


def test_long_semantic_preview_records_full_hash_length_and_truncation():
    first = ("alpha " * 1800).strip()
    second = ("beta " * 1800).strip()
    expected = first + "\n\n" + second
    response = PublicResponse(
        url="https://public.example.test/long-article",
        content=(
            '<html><head><title>Long article</title></head><body>'
            f'<article id="part-one">{first}</article>'
            f'<article id="part-two">{second}</article>'
            '</body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )

    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)
    item = result.items[0]
    observation = item["raw"]["content_observation"]

    assert result.status is CollectionStatus.SUCCESS
    assert len(item["content"]) <= 16_001
    assert item["content"].endswith("…")
    assert item["content"] != expected
    assert observation["selected_block_count"] == 2
    assert observation["source_text_sha256"] == hashlib.sha256(expected.encode("utf-8")).hexdigest()
    assert observation["source_text_char_length"] == len(expected)
    assert observation["returned_text_char_length"] == len(item["content"])
    assert observation["truncated"] is True
    assert observation["completeness"] == "TRUNCATED_SEMANTIC_PREVIEW"
    assert observation["document_sha256"] == hashlib.sha256(response.content).hexdigest()
    assert observation["document_byte_length"] == len(response.content)


def test_fix_094_nested_blocks_are_deduplicated_before_any_subtree_reparse(monkeypatch):
    import lumenis.system.collector.adapters.public_http as public_http

    original_parser = public_http.BeautifulSoup
    parsed_inputs = []

    def count_parser(source, *args, **kwargs):
        parsed_inputs.append(source)
        return original_parser(source, *args, **kwargs)

    monkeypatch.setattr(public_http, "BeautifulSoup", count_parser)
    outer = "Outer report text. " * 80
    inner = "Nested correction text. " * 80
    response = PublicResponse(
        url="https://public.example.test/nested-large-article",
        content=(
            '<html><head><title>Nested report</title></head><body>'
            f'<article id="outer">{outer}<section><article id="inner">{inner}'
            '</article></section></article></body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )

    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)

    assert result.status is CollectionStatus.SUCCESS
    assert len(parsed_inputs) == 1
    observation = result.items[0]["raw"]["content_observation"]
    assert observation["selected_block_count"] == 1
    assert "Outer report text." in result.items[0]["content"]
    assert result.items[0]["content"].count(inner.strip()) == 1


def test_fix_094_article_aggregate_retains_only_bounded_output():
    from lumenis.system.collector.adapters.public_http import MAX_PUBLIC_BODY_CHARS

    first = "alpha " * 40_000
    second = "beta " * 40_000
    expected = first.strip() + "\n\n" + second.strip()
    response = PublicResponse(
        url="https://public.example.test/large-aggregate",
        content=(
            '<html><head><title>Large aggregate</title></head><body>'
            f'<article>{first}</article><article>{second}</article>'
            '</body></html>'
        ).encode("utf-8"),
        content_type="text/html",
        status_code=200,
    )

    result = PublicHttpAdapter(fetcher=lambda _: response).search(response.url)
    item = result.items[0]
    observation = item["raw"]["content_observation"]

    assert len(item["content"]) <= MAX_PUBLIC_BODY_CHARS + 1
    assert observation["source_text_char_length"] == len(expected)
    assert observation["source_text_sha256"] == hashlib.sha256(expected.encode("utf-8")).hexdigest()
    assert observation["returned_text_char_length"] == len(item["content"])
    assert observation["truncated"] is True
    assert observation["completeness"] == "TRUNCATED_SEMANTIC_PREVIEW"


def test_form_or_navigation_root_is_never_selected_as_article():
    import lumenis.system.collector.adapters.public_http as public_http
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        "<html><body>"
        "<article role='navigation'>menu home about contact</article>"
        "<article role=' navigation '>padded menu</article>"
        "<form class='content_article'>" + "login field " * 80 + "</form>"
        "<article>real story body</article>"
        "</body></html>",
        "html.parser",
    )
    texts = [
        "".join(public_http._iter_node_text_parts(node))
        for node in public_http._selected_substantive_nodes(soup)
    ]
    assert texts == ["real story body"]


def test_deeply_nested_articles_measure_only_the_outer_root(monkeypatch):
    import lumenis.system.collector.adapters.public_http as public_http
    from bs4 import BeautifulSoup

    depth = 60
    soup = BeautifulSoup(
        "<html><body>" + "<article>x " * depth + "</article>" * depth + "</body></html>",
        "html.parser",
    )
    measured = []
    original = public_http._node_text_length

    def counting(node):
        measured.append(node)
        return original(node)

    monkeypatch.setattr(public_http, "_node_text_length", counting)
    selected = public_http._selected_substantive_nodes(soup)
    assert len(selected) == 1
    assert len(measured) == 1


def test_semantic_article_inside_page_level_form_is_selected():
    import lumenis.system.collector.adapters.public_http as public_http
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        "<html><body><form id='aspnetForm'><article>wrapped story body</article></form></body></html>",
        "html.parser",
    )
    nodes = public_http._selected_substantive_nodes(soup)
    assert len(nodes) == 1 and nodes[0].name == "article"


def test_multi_token_navigation_role_on_ancestor_or_descendant_is_chrome():
    import lumenis.system.collector.adapters.public_http as public_http
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        "<html><body>"
        "<div role='navigation presentation'><article>nav article menu</article></div>"
        "<article>real story body"
        "<div role='presentation navigation'><span>NAV_TOKEN_TEXT</span></div>"
        "</article>"
        "</body></html>",
        "html.parser",
    )
    nodes = public_http._selected_substantive_nodes(soup)
    assert [n.get_text(" ", strip=True).startswith("real story body") for n in nodes] == [True]
    text = "".join(public_http._iter_node_text_parts(nodes[0]))
    assert "NAV_TOKEN_TEXT" not in text


def test_media_only_document_keeps_empty_text_and_exact_manifest_without_fetching_it():
    source='https://publisher.example.test/native-player'
    manifest='https://cdn.example.test/declared-source.mpd'
    original=('<html><head><title>Official player</title></head><body><video src="'
              +manifest+'"></video></body></html>').encode()
    calls=[]
    def fetch(url):
        calls.append(url)
        return PublicResponse(source,original,'text/html',200,source)
    result=PublicHttpAdapter(fetcher=fetch).search(source)
    assert result.ok and result.original_response.content==original and calls==[source]
    item=result.items[0]
    assert item['content']=='' and item['raw']['body_state']=='EMPTY'
    assert item['raw']['content_observation']['source_text_char_length']==0
    assert not item['raw']['body_scope']['selected_dom_text_complete']
    assert result.metadata['source_representation']=='MEDIA_DOCUMENT_WITHOUT_BODY_TEXT'
    media=item['raw']['media_hints'][0]
    assert media['url']==manifest and media['bytes_state']=='NOT_ACQUIRED'
    assert media['acquisition']=={'extractor_key':'Generic','representation':'STREAM_MANIFEST','protocol':'dash'}


def test_empty_document_without_usable_native_media_remains_unavailable():
    for body in ('<video></video>','<iframe src="https://unknown.example.test/embed"></iframe>',
                 '<header><img src="/logo.png"></header>','<img src="data:image/png;base64,AA==">'):
        source='https://publisher.example.test/empty'
        response=PublicResponse(source,('<html><body>'+body+'</body></html>').encode(),'text/html',200,source)
        result=PublicHttpAdapter(fetcher=lambda url:response).search(source)
        assert not result.ok and result.metadata['error_type']=='EMPTY_CONTENT' and not result.items
