from __future__ import annotations

import socket
import hashlib
import json
from email.message import Message
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from types import SimpleNamespace

import pytest
import requests

import lumenis.system.collector.adapters.public_source as transport


def _streamed_media_response(monkeypatch, chunks, *, headers=None, status=200):
    monkeypatch.setattr(transport, '_resolved_addresses', lambda _: ['8.8.8.8'])
    response = SimpleNamespace(status_code=status, headers=headers or {'Content-Type': 'video/mp4'},
        url='https://media.example.test/original.mp4', closed=False)
    response.iter_content = lambda **_kwargs: iter(chunks)
    response.close = lambda: setattr(response, 'closed', True)
    calls = []
    def get(_session, url, **kwargs):
        calls.append(url)
        assert kwargs['allow_redirects'] is False and kwargs['verify'] is True and kwargs['stream'] is True
        assert 'Cookie' not in kwargs['headers'] and 'Authorization' not in kwargs['headers']
        return response
    monkeypatch.setattr(requests.Session, 'get', get)
    return response, calls


def test_media_stream_retains_hash_above_document_limit_without_buffering(monkeypatch, tmp_path):
    chunks = [b'a' * (1024 * 1024), b'b' * (1024 * 1024), b'c' * 16]
    response, calls = _streamed_media_response(monkeypatch, chunks)
    target = tmp_path / 'original.partial'
    value = transport.fetch_public_media(response.url, destination=target, max_bytes=3 * 1024 * 1024)
    assert value.size_bytes == target.stat().st_size == sum(map(len, chunks))
    assert value.sha256 == hashlib.sha256(b''.join(chunks)).hexdigest()
    assert response.closed and calls == [response.url]
    with pytest.raises(ValueError, match='safety bound'):
        transport.fetch_public_url(response.url, max_bytes=3 * 1024 * 1024)


@pytest.mark.parametrize('failure', ['oversize', 'cancelled', 'partial-response', 'truncated'])
def test_media_stream_failure_removes_partial_and_never_claims_original(monkeypatch, tmp_path, failure):
    headers = {'Content-Type': 'video/mp4'}
    if failure == 'truncated':
        headers['Content-Length'] = '8'
    response, _ = _streamed_media_response(monkeypatch, [b'1234', b'5678'] if failure != 'truncated' else [b'1234'],
                                         headers=headers, status=206 if failure == 'partial-response' else 200)
    target = tmp_path / 'failed.partial'
    checks = []
    def check():
        checks.append(True)
        if failure == 'cancelled' and len(checks) >= 4:
            raise PermissionError('TASK_CANCELLED')
    with pytest.raises((transport.PublicSourceError, PermissionError)):
        transport.fetch_public_media(response.url, destination=target,
            max_bytes=4 if failure == 'oversize' else 32, check_continue=check)
    assert not target.exists() and response.closed


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


def test_public_fetch_rechecks_before_each_request_after_redirect_validation(monkeypatch):
    start_url = "https://www.example.test/start"
    final_url = "https://www.example.test/final"
    host_pins = {"www.example.test": ("39.96.251.100",)}
    events = []

    class RedirectResponse(_FakeResponse):
        status_code = 302
        headers = {"Location": final_url}

    monkeypatch.setattr(transport, "load_public_source_host_pins", lambda: host_pins)

    def validate(url, **_kwargs):
        events.append(("validate", url))
        return url, host_pins

    monkeypatch.setattr(transport, "_validate_public_url_and_pin", validate)

    def get(_session, url, **_kwargs):
        events.append(("get", url))
        return RedirectResponse() if url == start_url else _FakeResponse()

    monkeypatch.setattr(requests.Session, "get", get)

    def before_fetch():
        events.append(("before_fetch", None))

    result = transport.fetch_public_url(start_url, before_fetch=before_fetch)

    assert result.content == b"safe"
    assert events == [
        ("validate", start_url),
        ("before_fetch", None),
        ("get", start_url),
        ("validate", final_url),
        ("before_fetch", None),
        ("get", final_url),
    ]


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


def test_http_rate_limit_preserves_retry_after_as_safe_metadata(monkeypatch):
    monkeypatch.setattr(transport, "_resolved_addresses", lambda _hostname: ["39.96.251.100"])
    response = _FakeResponse()
    response.status_code = 429
    response.headers = {
        "Content-Type": "text/plain",
        "Retry-After": "123",
    }

    with pytest.raises(transport.PublicSourceHTTPError) as captured:
        transport.fetch_public_url(
            "https://www.example.test/rate-limited",
            session=_FakeSession([response]),
        )

    assert response.closed is True
    assert captured.value.status_code == 429
    assert captured.value.retry_after_seconds == 123
    metadata = transport.public_source_error_metadata(captured.value)
    assert metadata["http_status"] == 429
    assert metadata["retry_after_seconds"] == 123
    assert metadata["network_attempted"] is True
    assert metadata["reason_code"] == "PUBLIC_SOURCE_HTTP_RATE_LIMITED"
    assert metadata["error_kind"] == metadata["reason_code"]
    assert metadata["recovery_action"] == "RETRY_AFTER_COOLDOWN"
    assert "Retry-After" not in str(metadata)


@pytest.mark.parametrize(("status", "reason_code", "recovery_action"), [
    (401, "PUBLIC_SOURCE_HTTP_ACCESS_RESTRICTED", "CHOOSE_ANOTHER_PUBLIC_SOURCE"),
    (403, "PUBLIC_SOURCE_HTTP_ACCESS_RESTRICTED", "CHOOSE_ANOTHER_PUBLIC_SOURCE"),
    (404, "PUBLIC_SOURCE_HTTP_PAGE_NOT_FOUND", "CHECK_PUBLIC_URL"),
    (503, "PUBLIC_SOURCE_HTTP_SERVER_ERROR", "RETRY_LATER"),
])
def test_http_failures_have_safe_public_reason_and_recovery(
        monkeypatch, status, reason_code, recovery_action):
    monkeypatch.setattr(transport, "_resolved_addresses", lambda _hostname: ["39.96.251.100"])
    response = _FakeResponse()
    response.status_code = status

    with pytest.raises(transport.PublicSourceHTTPError) as captured:
        transport.fetch_public_url(
            "https://www.example.test/article", session=_FakeSession([response]),
        )

    metadata = transport.public_source_error_metadata(captured.value)
    assert metadata["reason_code"] == reason_code
    assert metadata["error_kind"] == reason_code
    assert metadata["recovery_action"] == recovery_action
    assert metadata["network_attempted"] is True


def test_dns_failure_has_a_safe_reason_without_claiming_source_request(monkeypatch):
    def unresolved(*_args, **_kwargs):
        raise socket.gaierror("internal resolver details")

    monkeypatch.setattr(socket, "getaddrinfo", unresolved)
    with pytest.raises(transport.PublicSourceError) as captured:
        transport.fetch_public_url("https://www.example.test/article")

    metadata = transport.public_source_error_metadata(captured.value)
    assert metadata["reason_code"] == "PUBLIC_SOURCE_DNS_UNRESOLVED"
    assert metadata["error_kind"] == metadata["reason_code"]
    assert metadata["recovery_action"] == "CHECK_NETWORK_AND_RETRY"
    assert metadata["network_attempted"] is False
    assert "internal resolver details" not in str(metadata)


def test_public_source_failure_projection_rejects_unknown_or_mismatched_values():
    assert transport.safe_public_source_failure_fields({
        "reason_code": "PUBLIC_SOURCE_DNS_UNRESOLVED",
        "error_kind": "PUBLIC_SOURCE_DNS_UNRESOLVED",
        "recovery_action": "CHOOSE_ANOTHER_PUBLIC_SOURCE",
    }) == {}
    assert transport.safe_public_source_failure_fields({
        "reason_code": "provider-supplied-sensitive-text",
        "error_kind": "provider-supplied-sensitive-text",
        "recovery_action": "provider-supplied-sensitive-action",
    }) == {}


def test_retry_after_http_date_is_converted_to_positive_seconds():
    future = datetime.now(timezone.utc) + timedelta(minutes=3)
    value = format_datetime(future, usegmt=True)

    seconds = transport._parse_retry_after_seconds(value)

    assert seconds is not None and 100 <= seconds <= 180
    assert transport._parse_retry_after_seconds("not a date") is None
    assert transport._parse_retry_after_seconds("0") is None


def test_public_document_transport_checks_cancellation_between_body_chunks(monkeypatch):
    monkeypatch.setattr(transport, "_resolved_addresses", lambda _hostname: ["39.96.251.100"])
    response = _FakeResponse()
    response.headers = {"Content-Type": "text/html"}
    response.iter_content = lambda chunk_size: iter((b"<main>first", b"second</main>"))
    checks = 0

    def stop_after_first_chunk():
        nonlocal checks
        checks += 1
        if checks >= 4:
            raise InterruptedError("COLLECTION_ATTEMPT_NO_LONGER_ACTIVE")

    with pytest.raises(InterruptedError, match="COLLECTION_ATTEMPT_NO_LONGER_ACTIVE") as captured:
        transport.fetch_public_url(
            "https://www.example.test/cancel-during-read",
            session=_FakeSession([response]),
            check_continue=stop_after_first_chunk,
        )

    assert checks == 4
    assert response.closed is True
    assert captured.value.network_attempted is True


def test_rejected_local_public_url_reports_no_network_attempt():
    with pytest.raises(transport.PublicSourceError) as captured:
        transport.fetch_public_url("http://127.0.0.1/private")

    assert transport.public_source_error_metadata(captured.value)["network_attempted"] is False


def test_redirect_body_is_closed_before_caller_response_hooks(monkeypatch):
    monkeypatch.setattr(
        transport,
        "load_public_source_host_pins",
        lambda: {"example.test": ("93.184.216.34",)},
    )
    monkeypatch.setattr(
        transport,
        "_validate_public_url_and_pin",
        lambda value, **_kwargs: (value, {"example.test": ("93.184.216.34",)}),
    )

    class TrackingRaw:
        def __init__(self):
            self.closed = False
            self.read_calls = 0

        def close(self):
            self.closed = True

        def read(self, _chunk_size):
            self.read_calls += 1
            if self.closed:
                raise AssertionError("closed redirect body must not be read")
            return b"unbounded synthetic redirect body"

    def response(request, status, headers, content=b"", *, consumed=True):
        result = requests.Response()
        result.status_code = status
        result.headers = requests.structures.CaseInsensitiveDict(headers)
        result.url = request.url
        result.request = request
        result.raw = TrackingRaw()
        raws.append(result.raw)
        result._content = content if consumed else False
        result._content_consumed = consumed
        return result

    observations = []
    raws = []

    def inspect_response(result, **_kwargs):
        redirect_body = result.content if 300 <= result.status_code < 400 else None
        observations.append((result.status_code, result.raw.closed, redirect_body))
        return result

    def offline_send(_adapter, request, **_kwargs):
        if request.url.endswith("/start"):
            return response(
                request,
                302,
                {"Location": "https://example.test/final"},
                consumed=False,
            )
        return response(request, 200, {"Content-Type": "text/plain"}, b"safe")

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", offline_send)
    session = requests.Session()
    session.trust_env = False
    session.hooks["response"].append(inspect_response)

    result = transport.fetch_public_url("https://example.test/start", session=session)

    assert result.content == b"safe"
    assert observations == [(302, True, b""), (200, False, None)]
    assert raws[0].read_calls == 0


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


def test_anonymous_source_does_not_read_netrc_and_retains_proxy_configuration(monkeypatch):
    monkeypatch.setattr(transport,'load_public_source_host_pins',lambda:{})
    monkeypatch.setattr(transport,'_validate_public_url_and_pin',lambda url,**kw:(url,{'example.test':('93.184.216.34',)}))
    monkeypatch.setattr(requests.sessions,'get_netrc_auth',_forbid_test_network_egress)
    def send(adapter,request,**kwargs):
        assert 'Authorization' not in request.headers and 'Cookie' not in request.headers
        return _synthetic_response(request,200,{'Content-Type':'text/plain'},b'public')
    monkeypatch.setattr(requests.adapters.HTTPAdapter,'send',send)
    assert transport.fetch_public_url('https://example.test/source').content==b'public'


def _public_library_resources(monkeypatch, resources):
    calls = []
    monkeypatch.setattr(transport,'_resolved_addresses',lambda _: ['8.8.8.8'])
    def get(_session,url,**kwargs):
        calls.append(url)
        assert kwargs['allow_redirects'] is False and kwargs['verify'] is True
        assert not {'Cookie','Authorization'} & set(kwargs['headers'])
        value = resources[url]
        if isinstance(value,BaseException):
            raise value
        raw,mime = value
        return SimpleNamespace(status_code=200,headers={'Content-Type':mime,'Content-Length':str(len(raw))},
            url=url,iter_content=lambda **kw:iter([raw]),close=lambda:None)
    monkeypatch.setattr(requests.Session,'get',get)
    return calls


def test_pinned_media_library_extracts_captured_html_and_downloads_original_without_plugins(monkeypatch,tmp_path):
    import subprocess
    from yt_dlp import cookies
    from lumenis.system.collector.adapters import public_media as owner
    from tests.test_content_image_source import _png
    source='https://publisher.example.test/player'
    media='https://cdn.example.test/native.mp4'
    raw=b'\x00\x00\x00\x18ftypisom'+_png()
    html=f'<title>Public fixture</title><video controls src="{media}"></video>'.encode()
    calls=_public_library_resources(monkeypatch,{media:(raw,'video/mp4')})
    monkeypatch.setattr(subprocess,'Popen',_forbid_test_network_egress)
    monkeypatch.setattr(cookies,'load_cookies',_forbid_test_network_egress)
    captured=transport.PublicResponse(source,html,'text/html',200,source)
    plan=transport.extract_public_media(source,captured_response=captured)
    assert plan['source_document_sha256']==hashlib.sha256(html).hexdigest()
    assert plan['network_attempted'] is False and plan['formats']
    assert all(value['has_video'] in (True,False,None) and value['has_audio'] in (True,False,None) for value in plan['formats'])
    assert calls==[] and plan['extractor']['version']=='2026.10.21'
    selection=next(value for value in plan['formats'] if value['url']==media)
    output=tmp_path/'native.mp4'
    response=transport.fetch_extracted_public_media(plan,selection_id=selection['selection_id'],destination=output,max_bytes=4096)
    assert output.read_bytes()==raw and response.sha256==hashlib.sha256(raw).hexdigest()
    assert response.extraction['representation']=='NATIVE_FILE_BYTES' and calls==[media]
    tampered={**plan,'source_url':'https://changed.example.test/source'}
    with pytest.raises(owner.PublicMediaError,match='PLAN_BINDING_CHANGED'):
        transport.fetch_extracted_public_media(tampered,selection_id=selection['selection_id'],destination=tmp_path/'forbidden',max_bytes=4096)


def test_media_library_does_not_change_extractor_after_access_refusal(monkeypatch):
    calls=[]
    def denied(url,**kwargs):
        calls.append(url)
        raise transport.PublicSourceHTTPError(403)
    monkeypatch.setattr(transport,'fetch_public_url',denied)
    with pytest.raises(transport.PublicSourceHTTPError) as failure:
        transport.extract_public_media('https://publisher.example.test/blocked')
    assert failure.value.status_code==403 and calls==['https://publisher.example.test/blocked']


@pytest.mark.parametrize('content,mime',[
    (b'<title>Just a moment...</title><form id="challenge-form"></form>','text/html'),
    (b'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="secret-key"\n','application/x-mpegurl'),
    (b'<MPD><ContentProtection schemeIdUri="urn:uuid:drm"/></MPD>','application/dash+xml'),
])
def test_media_library_rejects_challenge_and_protection_before_other_requests(monkeypatch,content,mime):
    from lumenis.system.collector.adapters.public_media import PublicMediaError
    monkeypatch.setattr(transport,'fetch_public_url',_forbid_test_network_egress)
    source='https://publisher.example.test/protected'
    with pytest.raises(PublicMediaError):
        transport.extract_public_media(source,captured_response=transport.PublicResponse(source,content,mime,200,source))


def test_media_library_disallows_authenticated_post_range_and_unknown_extractors(monkeypatch):
    from yt_dlp.networking.common import Request
    from lumenis.system.collector.adapters.public_media import _PublicReads,PublicMediaError
    monkeypatch.setattr(transport,'fetch_public_url',_forbid_test_network_egress)
    for request in (Request('https://public.example.test/a',data=b'private'),
                    Request('https://public.example.test/a',headers={'Cookie':'private'}),
                    Request('https://public.example.test/a',headers={'Range':'bytes=0-1'})):
        with pytest.raises(PublicMediaError,match='REQUEST_BOUNDARY'):
            _PublicReads().urlopen(request)
    with pytest.raises(PublicMediaError,match='EXTRACTOR_NOT_ADMITTED'):
        transport.extract_public_media('https://public.example.test/a',extractor_key='ArbitraryPlugin')


@pytest.fixture
def public_library_tracks(tmp_path,monkeypatch):
    import shared_artifacts
    from lumenis.shared.content_creation.rendering import _run
    monkeypatch.setenv('ZBC_ARTIFACT_DIR',str(tmp_path/'artifacts'))
    ffmpeg=shared_artifacts._ffmpeg_path()
    assert ffmpeg
    video,audio=tmp_path/'native-video.mp4',tmp_path/'native-audio.m4a'
    _run([ffmpeg,'-v','error','-nostdin','-n','-f','lavfi','-i','color=c=blue:s=32x32:r=4:d=1',
        '-an','-c:v','libx264','-pix_fmt','yuv420p',str(video)],cwd=tmp_path,timeout=20)
    _run([ffmpeg,'-v','error','-nostdin','-n','-f','lavfi','-i','sine=frequency=440:duration=1',
        '-vn','-c:a','aac',str(audio)],cwd=tmp_path,timeout=20)
    return video.read_bytes(),audio.read_bytes()


def test_native_hls_uses_library_and_safe_transport_keeps_original_components(monkeypatch,tmp_path,public_library_tracks):
    import shared_artifacts,subprocess
    media='https://cdn.example.test/part.mp4'
    source='https://cdn.example.test/vod.m3u8'
    manifest=f'#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:1\n#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:1,\n{media}\n#EXT-X-ENDLIST\n'.encode()
    calls=_public_library_resources(monkeypatch,{source:(manifest,'application/x-mpegurl'),media:(public_library_tracks[0],'video/mp4')})
    monkeypatch.setattr(subprocess,'Popen',_forbid_test_network_egress)
    plan=transport.extract_public_media(source,captured_response=transport.PublicResponse(source,manifest,'application/x-mpegurl',200,source))
    selection=plan['formats'][0]
    output=tmp_path/'assembled.media'
    response=transport.fetch_extracted_public_media(plan,selection_id=selection['selection_id'],destination=output,
        max_bytes=1024*1024,allow_segment_assembly=True)
    assert response.extraction['representation']=='SEGMENTED_STREAM_ASSEMBLY'
    assert output.read_bytes()==public_library_tracks[0]
    assert calls==[source,media]
    for item in response.extraction['components']:
        assert item['original_bytes_saved']
        assert shared_artifacts._content_original_path(item['sha256']).stat().st_size==item['size_bytes']


def test_native_dash_metadata_and_distinct_tracks_copy_mux_keep_component_hashes(monkeypatch,tmp_path,public_library_tracks):
    import shared_artifacts
    from lumenis.shared.content_creation.video_editing import _probe_media_info
    source='https://cdn.example.test/source.mpd'
    video,audio='https://cdn.example.test/video.mp4','https://cdn.example.test/audio.m4a'
    manifest=f'''<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" mediaPresentationDuration="PT1S"><Period>
      <AdaptationSet mimeType="video/mp4"><Representation id="v" codecs="avc1.42c00a" bandwidth="100000"><BaseURL>{video}</BaseURL></Representation></AdaptationSet>
      <AdaptationSet mimeType="audio/mp4"><Representation id="a" codecs="mp4a.40.2" bandwidth="64000"><BaseURL>{audio}</BaseURL></Representation></AdaptationSet>
      </Period></MPD>'''.encode()
    _public_library_resources(monkeypatch,{source:(manifest,'application/dash+xml'),video:(public_library_tracks[0],'video/mp4'),audio:(public_library_tracks[1],'audio/mp4')})
    plan=transport.extract_public_media(source,captured_response=transport.PublicResponse(source,manifest,'application/dash+xml',200,source))
    selections=[next(f['selection_id'] for f in plan['formats'] if f.get('has_video') is True and f.get('has_audio') is False),
                next(f['selection_id'] for f in plan['formats'] if f.get('has_video') is False and f.get('has_audio') is True)]
    output=tmp_path/'muxed.mp4'
    response=transport.fetch_extracted_public_media(plan,selection_ids=selections,destination=output,max_bytes=1024*1024)
    probe=_probe_media_info(output)
    assert probe.has_video and probe.audio_stream_count==1
    assert response.extraction['representation']=='COPY_MUXED_NATIVE_TRACKS'
    assert len(response.extraction['components'])==2
    for item,raw in zip(response.extraction['components'],public_library_tracks):
        assert item['sha256']==hashlib.sha256(raw).hexdigest()
        assert shared_artifacts._content_original_path(item['sha256']).read_bytes()==raw
    modified=json.loads(json.dumps(plan))
    modified['formats'][1]['native_locator']['entry_index']=99
    from lumenis.system.collector.adapters.public_media import _digest,PublicMediaError
    modified['plan_sha256']=_digest({k:v for k,v in modified.items() if k!='plan_sha256'})
    with pytest.raises(PublicMediaError,match='TRACK_IDENTITY'):
        transport.fetch_extracted_public_media(modified,selection_ids=selections,destination=tmp_path/'wrong.mp4',max_bytes=1024*1024)
