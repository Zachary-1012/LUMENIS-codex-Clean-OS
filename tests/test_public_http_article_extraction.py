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
