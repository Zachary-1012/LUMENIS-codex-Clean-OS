"""Public source URLs retain their full identity beyond the social query limit."""
import pytest

from lumenis.system.collector.adapters.secondary_collection import _validate_request


@pytest.mark.parametrize("platform", ["public_http", "web_rss", "web_atom", "sitemap"])
def test_public_source_url_is_not_truncated_to_search_keyword_length(platform):
    url = "https://publisher.example/news/" + "source-identity-" * 15 + "?edition=2026&lang=en"
    assert _validate_request(platform, url, 3) == (platform, url, 3)


def test_oversized_input_still_rejected_before_network():
    with pytest.raises(ValueError):
        _validate_request("public_http", "https://publisher.example/" + "x" * 4096, 3)
    with pytest.raises(ValueError):
        _validate_request("douyin", "x" * 257, 3)
