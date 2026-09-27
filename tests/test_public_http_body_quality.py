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
