import pytest
from flask import Flask

from lumenis.system.security.permission import local_workspace_read_allowed


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    return app


def _allowed(
    app, *, host="localhost", origin=None, remote_addr="127.0.0.1",
    headers=None, module="subject_registry", action="read",
):
    request_headers = {"Host": host}
    if origin is not None:
        request_headers["Origin"] = origin
    if headers:
        request_headers.update(headers)
    with app.test_request_context(
        "/", headers=request_headers,
        environ_overrides={"REMOTE_ADDR": remote_addr},
    ):
        return local_workspace_read_allowed(module=module, action=action)


def test_local_read_requires_explicit_open_workspace(app):
    for setting in (False, 1, "true", None):
        app.config["LUMENIS_OPEN_WORKSPACE"] = setting
        assert _allowed(app) is False
    app.config.pop("LUMENIS_OPEN_WORKSPACE")
    assert _allowed(app) is False


def test_local_read_requires_request_context(app):
    with app.app_context():
        assert local_workspace_read_allowed() is False


def test_local_read_allows_only_the_two_read_modules_and_loopback_origins(app):
    cases = (
        ("subject_registry", "localhost", None, "127.0.0.1"),
        ("commercial_realtime_stream", "127.0.0.1:8201", "https://localhost:8201", "127.0.0.1"),
        ("commercial_realtime_stream", "[::1]", "http://[::1]:8201", "::1"),
    )
    for module, host, origin, remote_addr in cases:
        assert _allowed(
            app, host=host, origin=origin, remote_addr=remote_addr, module=module
        ) is True


@pytest.mark.parametrize("remote_addr", ["192.0.2.4", "not-an-ip"])
def test_local_read_rejects_non_loopback_or_invalid_client_address(app, remote_addr):
    assert _allowed(app, remote_addr=remote_addr) is False


@pytest.mark.parametrize("host", [
    "localhost:", "localhost:0", "localhost:65536", "127.0.0.2",
    "localhost/path", "user@localhost", "[::1]:abc",
])
def test_local_read_rejects_malformed_or_non_allowlisted_host(app, host):
    assert _allowed(app, host=host) is False


@pytest.mark.parametrize("origin", [
    "http://localhost/path", "https://user@localhost",
    "https://localhost:65536", "file://localhost", "null",
])
def test_local_read_rejects_invalid_origin(app, origin):
    assert _allowed(app, origin=origin) is False


@pytest.mark.parametrize("header", [
    ("Forwarded", "for=127.0.0.1"),
    ("X-Forwarded-For", "127.0.0.1"),
    ("X-Forwarded-Host", "localhost"),
])
def test_local_read_rejects_forwarded_headers(app, header):
    assert _allowed(app, headers={header[0]: header[1]}) is False


@pytest.mark.parametrize("module,action", [
    ("cth_monitoring", "read"),
    ("account", "read"),
    ("subject_registry", "write"),
    ("subject_registry", "db_write"),
    ("commercial_realtime_stream", "export"),
    ("commercial_realtime_stream", "collect"),
])
def test_local_read_rejects_unapproved_modules_and_actions(app, module, action):
    with app.test_request_context(
        "/", headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        assert local_workspace_read_allowed(module=module, action=action) is False


def test_local_read_does_not_downgrade_authenticated_requests(app):
    assert _allowed(app, headers={"Authorization": "Bearer invalid"}) is False
    assert _allowed(app, headers={"Cookie": "cth_poms_v4_session="}) is False
