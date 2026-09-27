"""A public article must not be replaced by its publisher's generic blurb."""

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
