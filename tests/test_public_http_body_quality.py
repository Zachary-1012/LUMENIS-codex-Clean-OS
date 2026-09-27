"""Regression for source bodies that extend past page chrome and short previews."""

from lumenis.system.collector.adapters.base import CollectionStatus
from lumenis.system.collector.adapters.public_http import (
    MAX_PUBLIC_BODY_CHARS,
    PublicHttpAdapter,
)
from lumenis.system.collector.adapters.public_source import PublicResponse


def _capture(html: str):
    adapter = PublicHttpAdapter(fetcher=lambda url: PublicResponse(
        url=url, content=html.encode("utf-8"), content_type="text/html", status_code=200,
    ))
    result = adapter.search("https://publisher.example/article")
    assert result.status is CollectionStatus.SUCCESS
    return result.items[0]["content"]


def test_official_article_keeps_late_brand_fact_without_site_chrome():
    html = (
        '<html><head><meta name="description" content="Publisher homepage"></head><body>'
        '<header class="header-body-menu">' + "MENU " * 180 + '</header>'
        '<section class="float100"><div class="float100">'
        '<nav>UNRELATED NAVIGATION</nav>'
        '<p>' + "Company results context. " * 440 + '</p>'
        '<p>Le Labo fragrance detail belongs to this release.</p>'
        '</div></section>'
        '<footer class="float100">' + "FOOTER " * 90 + '</footer>'
        '</body></html>'
    )

    content = _capture(html)

    assert "Le Labo fragrance detail" in content
    assert "UNRELATED NAVIGATION" not in content
    assert "MENU MENU" not in content
    assert "FOOTER FOOTER" not in content
    assert 1_000 < len(content) <= MAX_PUBLIC_BODY_CHARS + 1


def test_public_article_body_remains_bounded():
    content = _capture('<html><body><article>' + "A" * 20_000 + '</article></body></html>')

    assert len(content) == MAX_PUBLIC_BODY_CHARS + 1
    assert content.endswith("…")


def test_short_semantic_directory_keeps_native_names_not_site_description():
    content = _capture(
        '<html><head><meta name="description" content="Furniture for everyone"></head>'
        '<body><header>UNRELATED MENU</header><main><article>'
        '<h1>매장 안내</h1><p>전국 이케아 매장의 위치와 운영 시간을 확인해 보세요!</p>'
        '<a>광명점</a><a>고양점</a><a>기흥점</a>'
        '</article></main><footer>UNRELATED FOOTER</footer></body></html>'
    )
    assert '광명점' in content
    assert '전국 이케아' in content
    assert 'Furniture' not in content
    assert 'UNRELATED' not in content


def test_short_accessible_main_preserves_address():
    content = _capture('<html><body><div role="main"><p>서울 영등포구 여의대로 108</p></div></body></html>')
    assert content == '서울 영등포구 여의대로 108'


def test_site_homepage_canonical_does_not_merge_distinct_detail_pages():
    html = b'<html><head><link rel="canonical" href="/"></head><body><main>Actual location</main></body></html>'
    items = [PublicHttpAdapter._item(PublicResponse(
        url='https://publisher.example/' + path, content=html,
        content_type='text/html', status_code=200,
    )) for path in ('about/location', 'about/parking')]
    assert items[0]['url'] == 'https://publisher.example/about/location'
    assert items[1]['url'] == 'https://publisher.example/about/parking'
    assert items[0]['platform_content_id'] != items[1]['platform_content_id']
    assert all(item['publish_datetime'] == '' for item in items)


def test_same_page_canonical_still_removes_tracking_query():
    response = PublicResponse(
        url='https://publisher.example/article?utm_source=news',
        content=b'<link rel="canonical" href="/article"><main>Article</main>',
        content_type='text/html', status_code=200,
    )
    assert PublicHttpAdapter._item(response)['url'] == 'https://publisher.example/article'
