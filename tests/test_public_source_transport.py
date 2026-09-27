from __future__ import annotations

import socket
from email.message import Message
from types import SimpleNamespace

import pytest
import requests

import lumenis.system.collector.adapters.public_source as transport


def test_older_requests_transport_fails_closed(monkeypatch):
    monkeypatch.delattr(requests.adapters.HTTPAdapter, "get_connection_with_tls_context")
    with pytest.raises(transport.PublicSourceError, match="compatible Requests TLS pin APIs"):
        transport.PublicSourceHTTPAdapter(host_pins={})


def test_host_pins_are_exact_and_only_globally_routable_addresses_are_accepted():
    assert transport.load_public_source_host_pins(
        '{"www.example.com":["39.96.251.100"]}'
    ) == {"www.example.com": ("39.96.251.100",)}

    for config in (
        '{"*.example.com":["39.96.251.100"]}',
        '{"example.com":["198.18.0.102"]}',
        '{"example.com":["39.96.251.100", "10.0.0.1"]}',
        '{"example.com":"39.96.251.100"}',
        "not-json",
    ):
        with pytest.raises(transport.PublicSourceError):
            transport.load_public_source_host_pins(config)


def test_unpinned_fake_dns_address_is_rejected(monkeypatch):
    for address in ("198.18.0.102", "224.0.0.1", "192.0.2.10", "0.0.0.0"):
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *args, _address=address, **kwargs: [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (_address, 0))
            ],
        )
        with pytest.raises(transport.PublicSourceError):
            transport.validate_public_url("https://unresolved.example.test/source")


def test_opt_in_secure_dns_recovers_fake_workstation_dns_and_stays_pinned(monkeypatch):
    monkeypatch.setenv("LUMENIS_PUBLIC_SOURCE_DOH_FALLBACK", "1")
    monkeypatch.setattr(transport, "_resolved_addresses", lambda _: ("198.18.0.10",))
    looked_up = []

    def secure_lookup(host):
        looked_up.append(host)
        return ("8.8.8.8",)

    monkeypatch.setattr(transport, "_doh_addresses", secure_lookup)
    trace = []
    _, pins = transport._validate_public_url_and_pin(
        "https://www.example.test/source", resolution_trace=trace,
    )
    assert looked_up == ["www.example.test"]
    assert pins["www.example.test"] == ("8.8.8.8",)
    assert trace[0]["resolver"] == "doh_google"


def test_secure_dns_fallback_never_promotes_literal_or_mixed_private_dns(monkeypatch):
    monkeypatch.setenv("LUMENIS_PUBLIC_SOURCE_DOH_FALLBACK", "1")
    looked_up = []
    monkeypatch.setattr(transport, "_doh_addresses", lambda host: looked_up.append(host) or ("8.8.8.8",))
    monkeypatch.setattr(transport, "_resolved_addresses", lambda _: ("127.0.0.1",))
    with pytest.raises(transport.PublicSourceError):
        transport.validate_public_url("http://127.0.0.1/private")
    monkeypatch.setattr(transport, "_resolved_addresses", lambda _: ("8.8.8.8", "127.0.0.1"))
    with pytest.raises(transport.PublicSourceError):
        transport.validate_public_url("https://www.example.test/source")
    assert looked_up == []


def test_pinned_https_proxy_uses_literal_pool_and_original_tls_name():
    adapter = transport.PublicSourceHTTPAdapter(
        host_pins={"www.example.test": ("203.0.113.10",)}
    )
    request = requests.Request("GET", "https://www.example.test/source").prepare()
    pool = adapter.get_connection_with_tls_context(
        request,
        verify=True,
        proxies={"https": "http://127.0.0.1:7890"},
    )
    assert pool.host == "203.0.113.10"
    assert pool._tunnel_host == "203.0.113.10"
    assert pool.conn_kw["server_hostname"] == "www.example.test"
    assert pool.assert_hostname == "www.example.test"


def test_pinned_http_proxy_targets_literal_ip_but_keeps_original_host_header():
    adapter = transport.PublicSourceHTTPAdapter(
        host_pins={"www.example.test": ("39.96.251.100",)}
    )
    request = requests.Request("GET", "http://www.example.test:8080/source").prepare()
    request.headers["Host"] = "www.example.test:8080"
    proxy = {"http": "http://proxy.example.test:3128"}

    assert adapter.request_url(request, proxy) == "http://39.96.251.100:8080/source"
    assert request.headers["Host"] == "www.example.test:8080"


def test_transport_fails_closed_when_proxy_request_has_no_validated_pin():
    adapter = transport.PublicSourceHTTPAdapter(host_pins={})
    request = requests.Request("GET", "https://www.example.test/source").prepare()

    with pytest.raises(requests.exceptions.InvalidURL, match="validated address pin"):
        adapter.get_connection_with_tls_context(
            request, verify=True, proxies={"https": "http://proxy.example.test:3128"}
        )


def test_pinned_pool_cache_separates_hosts_and_addresses():
    adapter = transport.PublicSourceHTTPAdapter(
        host_pins={
            "one.example.test": ("203.0.113.10",),
            "two.example.test": ("203.0.113.11",),
        }
    )
    first = adapter.get_connection_with_tls_context(
        requests.Request("GET", "https://one.example.test/a").prepare(), True, {}
    )
    second = adapter.get_connection_with_tls_context(
        requests.Request("GET", "https://two.example.test/a").prepare(), True, {}
    )
    assert first is not second
    assert first.host == "203.0.113.10"
    assert second.host == "203.0.113.11"


class _FakeResponse:
    status_code = 200
    headers = {"Content-Type": "text/plain", "Content-Length": "4"}

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True

    def iter_content(self, chunk_size):
        yield b"safe"


class _FakeSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.urls = []
        self.adapters = {"http://": object(), "https://": object()}

    def mount(self, prefix, adapter):
        return None

    def get(self, url, **kwargs):
        self.urls.append(url)
        return next(self.responses)


def test_body_limit_and_redirect_are_checked_before_returning_content(monkeypatch):
    monkeypatch.setattr(
        transport,
        "_resolved_addresses",
        lambda hostname: ["127.0.0.1"] if hostname == "127.0.0.1" else ["39.96.251.100"],
    )
    response = _FakeResponse()
    response.headers = {"Content-Type": "text/plain", "Content-Length": "9"}
    with pytest.raises(transport.PublicSourceError, match="size limit"):
        transport.fetch_public_url(
            "https://www.example.test/source",
            session=_FakeSession([response]),
            max_bytes=4,
        )
    assert response.closed is True

    class RedirectResponse(_FakeResponse):
        status_code = 302
        headers = {"Location": "http://127.0.0.1/private"}

    session = _FakeSession([RedirectResponse()])
    original_adapters = dict(session.adapters)
    with pytest.raises(transport.PublicSourceError):
        transport.fetch_public_url("https://www.example.test/source", session=session)
    assert session.urls == ["https://www.example.test/source"]
    assert session.adapters == original_adapters


@pytest.mark.parametrize("status", [304, 301, 302, 307, 308])
def test_not_modified_and_redirect_without_location_are_not_content(status, monkeypatch):
    monkeypatch.setattr(transport, "_resolved_addresses", lambda hostname: ["39.96.251.100"])

    class StatusResponse(_FakeResponse):
        status_code = status
        headers = {"Content-Type": "text/plain"}

    response = StatusResponse()
    with pytest.raises(transport.PublicSourceError, match=f"HTTP {status}"):
        transport.fetch_public_url(
            "https://www.example.test/source", session=_FakeSession([response])
        )
    assert response.closed is True


def test_validated_dns_answer_is_the_only_address_used_after_rebinding(monkeypatch):
    answers = iter(("39.96.251.100", "127.0.0.1"))
    lookups = []

    def rebinding_getaddrinfo(hostname, *args, **kwargs):
        address = next(answers)
        lookups.append((hostname, address))
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", rebinding_getaddrinfo)
    connected_hosts = []

    def offline_send(self, request, **kwargs):
        pool = self.get_connection_with_tls_context(
            request,
            verify=kwargs.get("verify", True),
            proxies=kwargs.get("proxies"),
            cert=kwargs.get("cert"),
        )
        connected_hosts.append((pool.host, request.headers.get("Host")))
        response = requests.Response()
        response.status_code = 200
        response.headers["Content-Type"] = "text/plain"
        response._content = b"safe"
        response._content_consumed = True
        response.url = request.url
        response.request = request
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", offline_send)
    session = requests.Session()
    session.trust_env = False
    result = transport.fetch_public_url("https://www.example.test/source", session=session)

    assert result.content == b"safe"
    assert lookups == [("www.example.test", "39.96.251.100")]
    assert connected_hosts == [("39.96.251.100", "www.example.test")]


def test_more_specific_caller_mount_cannot_bypass_transport_and_is_restored(monkeypatch):
    monkeypatch.setattr(transport, "_resolved_addresses", lambda hostname: ["39.96.251.100"])

    class BypassAdapter:
        def send(self, request, **kwargs):
            raise AssertionError("specific caller adapter must not run")

    class InspectSession(_FakeSession):
        def get(self, url, **kwargs):
            assert list(self.adapters) == ["http://", "https://"]
            return super().get(url, **kwargs)

    response = _FakeResponse()
    session = InspectSession([response])
    original_adapters = session.adapters
    session.adapters["https://specific.example.test/"] = BypassAdapter()
    transport.fetch_public_url("https://specific.example.test/source", session=session)
    assert session.adapters is original_adapters
    assert "https://specific.example.test/" in session.adapters


def test_json_duplicate_and_case_collision_pin_keys_are_rejected():
    with pytest.raises(transport.PublicSourceError):
        transport.load_public_source_host_pins(
            '{"example.com":["39.96.251.100"],"example.com":["39.96.251.101"]}'
        )
    with pytest.raises(transport.PublicSourceError):
        transport.load_public_source_host_pins(
            '{"Example.com":["39.96.251.100"],"example.com":["39.96.251.101"]}'
        )


def test_public_transport_rejects_prepared_auth_and_cookie_headers():
    adapter = transport.PublicSourceHTTPAdapter()
    for header in ("Authorization", "Cookie"):
        request = requests.Request(
            "GET", "https://example.test/source", headers={header: "secret"}
        ).prepare()
        with pytest.raises(requests.exceptions.InvalidHeader):
            adapter.send(request, verify=True, proxies={})


def _synthetic_response(request, status, headers, content=b""):
    response = requests.Response()
    response.status_code = status
    response.headers = requests.structures.CaseInsensitiveDict(headers)
    response.url = request.url
    response.request = request
    response.reason = "Synthetic"
    raw_headers = Message()
    for name, value in headers.items():
        raw_headers[name] = value
    response.raw = SimpleNamespace(_original_response=SimpleNamespace(msg=raw_headers))
    response._content = content
    response._content_consumed = True
    return response


def _forbid_test_network_egress(*_args, **_kwargs):
    raise AssertionError("network egress forbidden in test")


def test_anonymous_internal_session_drops_redirect_set_cookie(monkeypatch):
    monkeypatch.setattr(transport, "load_public_source_host_pins", lambda: {})
    monkeypatch.setattr(
        transport,
        "_validate_public_url_and_pin",
        lambda value, **_kwargs: (value, {"example.test": ("93.184.216.34",)}),
    )
    session_instances = []
    real_session = requests.Session

    sent_headers = []
    cookies_after_response = []

    original_get = real_session.get

    def offline_send(_adapter, request, **_kwargs):
        sent_headers.append({name.lower() for name in request.headers})
        if request.url.endswith("/start"):
            return _synthetic_response(request, 301, {
                "Location": "https://example.test/final",
                "Set-Cookie": "redirect_marker=synthetic; Path=/",
            })
        return _synthetic_response(request, 200, {"Content-Type": "text/plain"}, b"public")

    def observed_get(session, url, **kwargs):
        response = original_get(session, url, **kwargs)
        cookies_after_response.append({cookie.name for cookie in session.cookies})
        return response

    def anonymous_session():
        session = real_session()
        session.trust_env = False
        session.get = lambda url, **kwargs: observed_get(session, url, **kwargs)
        session_instances.append(session)
        return session

    monkeypatch.setattr(requests, "Session", anonymous_session)
    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", offline_send)
    result = transport.fetch_public_url("https://example.test/start")

    assert result.content == b"public"
    assert len(sent_headers) == 2
    assert "cookie" not in sent_headers[0]
    assert "cookie" not in sent_headers[1]
    assert cookies_after_response[0] == {"redirect_marker"}
    assert cookies_after_response[1] == set()
    assert not session_instances[0].cookies


@pytest.mark.parametrize(
    "header,value",
    [("Authorization", "Basic synthetic"), ("Cookie", "caller=synthetic")],
)
def test_public_fetch_rejects_explicit_caller_session_credentials(monkeypatch, header, value):
    monkeypatch.setattr(transport, "load_public_source_host_pins", lambda: {})
    monkeypatch.setattr(
        transport,
        "_validate_public_url_and_pin",
        lambda url, **_kwargs: (url, {"example.test": ("93.184.216.34",)}),
    )
    session = requests.Session()
    session.trust_env = False
    session.headers[header] = value
    monkeypatch.setattr(
        requests.adapters.HTTPAdapter,
        "send",
        _forbid_test_network_egress,
    )

    with pytest.raises(transport.PublicSourceError) as exc_info:
        transport.fetch_public_url("https://example.test/source", session=session)

    assert isinstance(exc_info.value.__cause__, requests.exceptions.InvalidHeader)


def test_public_fetch_rejects_netrc_auth_before_egress(monkeypatch, tmp_path):
    netrc_file = tmp_path / "synthetic-netrc"
    netrc_file.write_text(
        "machine example.test login synthetic-user password synthetic-password\n",
        encoding="ascii",
    )
    monkeypatch.setenv("NETRC", str(netrc_file))
    monkeypatch.setattr(transport, "load_public_source_host_pins", lambda: {})
    monkeypatch.setattr(
        transport,
        "_validate_public_url_and_pin",
        lambda url, **_kwargs: (url, {"example.test": ("93.184.216.34",)}),
    )
    session = requests.Session()
    session.trust_env = True
    monkeypatch.setattr(
        requests.adapters.HTTPAdapter,
        "send",
        _forbid_test_network_egress,
    )

    with pytest.raises(transport.PublicSourceError) as exc_info:
        transport.fetch_public_url("https://example.test/source", session=session)

    assert isinstance(exc_info.value.__cause__, requests.exceptions.InvalidHeader)
