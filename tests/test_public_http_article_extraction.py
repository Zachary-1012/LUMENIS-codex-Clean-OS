"""A public article must not be replaced by its publisher's generic blurb."""

import hashlib

from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
from lumenis.system.collector.adapters.public_source import PublicResponse


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
