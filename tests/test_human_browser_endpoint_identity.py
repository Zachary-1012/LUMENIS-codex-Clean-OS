import pytest

from lumenis.adapters.human_browser import (
    HumanBrowser,
    _is_local_browser_host,
    _parse_browser_endpoint,
)


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "127.1",
        "2130706433",
        "0x7f000001",
        "0177.0.0.1",
        "127.0.0.1.",
        "localhost.",
        "localhost.localdomain",
        "browser.localhost",
        "::1",
        "::ffff:127.0.0.1",
        "0.0.0.0",
        "::",
    ],
)
def test_local_browser_host_recognizes_loopback_and_unspecified_aliases(host):
    assert _is_local_browser_host(host) is True


@pytest.mark.parametrize("host", ["8.8.8.8", "203.0.113.7", "example.com", ""])
def test_local_browser_host_does_not_classify_public_or_empty_hosts_as_loopback(host):
    assert _is_local_browser_host(host) is False


@pytest.mark.parametrize(
    ("url", "error"),
    [
        ("http://127.1:9222", "PROTECTED_PROFILE_FORBIDDEN"),
        ("http://2130706433:9222", "PROTECTED_PROFILE_FORBIDDEN"),
        ("http://0x7f000001:9222", "PROTECTED_PROFILE_FORBIDDEN"),
        ("http://localhost.:9222", "PROTECTED_PROFILE_FORBIDDEN"),
        ("http://localhost.localdomain:9222", "PROTECTED_PROFILE_FORBIDDEN"),
        ("http://[::ffff:127.0.0.1]:9222", "PROTECTED_PROFILE_FORBIDDEN"),
        ("http://0.0.0.0:9222", "PROTECTED_PROFILE_FORBIDDEN"),
        ("http://127.1:9223", "REGISTERED_WORKER_ENDPOINT_REQUIRED"),
    ],
)
def test_connect_rejects_protected_worker_ports_through_loopback_aliases(url, error):
    browser = HumanBrowser(cdp_url=url, auto_ensure=False)
    with pytest.raises(RuntimeError, match=error):
        browser.connect()


@pytest.mark.parametrize(
    "url",
    [
        "ftp://127.0.0.1:9224",
        "file://localhost:9224",
        "http://user:pass@127.0.0.1:9224",
        "http://127.0.0.1:0",
        "http://127.0.0.1:65536",
        "http://127.0.0.1:not-a-port",
        "http://127.0.0.1:",
        "http://[::1]:",
    ],
)
def test_endpoint_parser_rejects_non_http_credentials_and_invalid_ports(url):
    assert _parse_browser_endpoint(url) is None


def test_endpoint_parser_accepts_http_endpoint_without_dns_lookup():
    parsed, port = _parse_browser_endpoint("HTTP://LocalHost.:9224")
    assert parsed.hostname == "localhost."
    assert port == 9224
