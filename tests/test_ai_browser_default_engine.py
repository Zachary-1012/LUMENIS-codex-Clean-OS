"""AI Browser must never attach a caller-selected or personal browser profile."""

import threading
import struct
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

import ai_browser_api
import ai_browser_runtime as runtime
import browser_surface


@pytest.fixture
def isolated_runtime(monkeypatch):
    monkeypatch.setattr(runtime, "get_evidence_store", lambda: MagicMock())
    return runtime.BrowserSessionManager()


def test_manager_rejects_personal_port_profile_and_visible_browser(isolated_runtime):
    for options in ({"cdp_port": 9222}, {"user_data_dir": r"C:\Users\personal"},
                    {"headless": False}):
        with pytest.raises(ValueError, match="isolated LUMENIS browser"):
            isolated_runtime.create_session(**options)
    assert isolated_runtime.list_sessions() == []


def test_browser_address_projection_drops_credentials_and_query_secrets():
    assert runtime.safe_browser_display_url(
        "https://user:password@example.org/path?code=secret#token"
    ) == "https://example.org/path"
    assert runtime.safe_browser_display_url("file:///C:/private") == ""
    assert runtime.safe_browser_display_url("about:blank") == "about:blank"


def test_manager_reuses_one_login_and_reports_other_login_capacity(isolated_runtime):
    first = isolated_runtime.create_session(owner_actor_id=101, owner_account_session_id=501)
    first.status = runtime.SessionStatus.RUNNING
    assert isolated_runtime.create_session(owner_actor_id=101, owner_account_session_id=501) is first
    with pytest.raises(runtime.BrowserCapacityError):
        isolated_runtime.create_session(owner_actor_id=102, owner_account_session_id=502)
    isolated_runtime.close_session(first.session_id)


def test_start_fails_closed_when_product_browser_is_unverified(isolated_runtime, monkeypatch):
    session = isolated_runtime.create_session()
    monkeypatch.setattr(browser_surface, "ensure_general_browser",
                        lambda: {"ok": False, "code": "UNVERIFIED_BROWSER_SESSION"})
    assert session.start() is False
    assert session.status == runtime.SessionStatus.ERROR
    assert session._playwright is None


def test_start_uses_fresh_context_and_closes_only_its_pages(isolated_runtime, monkeypatch):
    import playwright.sync_api

    monkeypatch.setattr(browser_surface, "ensure_general_browser", lambda: {"ok": True, "browser": "chrome"})
    monkeypatch.setattr(browser_surface, "general_browser_online", lambda: True)
    factory = MagicMock()
    monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: factory)
    session = isolated_runtime.create_session()
    browser = factory.start.return_value.chromium.connect_over_cdp.return_value

    assert session.start() is True
    browser.new_context.assert_called_once_with()
    assert browser.contexts.call_count == 0
    context = browser.new_context.return_value
    context.new_page.assert_called_once_with()
    session.close()
    context.close.assert_called_once_with()
    factory.start.return_value.stop.assert_called_once_with()
    browser.close.assert_not_called()


def test_playwright_calls_use_creation_thread_across_request_threads(isolated_runtime, monkeypatch):
    import playwright.sync_api as playwright_api

    monkeypatch.setattr(browser_surface, "ensure_general_browser", lambda: {"ok": True, "browser": "chrome"})
    monkeypatch.setattr(browser_surface, "general_browser_online", lambda: True)
    owner_threads = []

    def record(value=None):
        owner_threads.append(threading.get_ident())
        return value

    factory = MagicMock()
    playwright_instance = factory.start.return_value
    playwright_instance.chromium.connect_over_cdp.side_effect = lambda *_: record(browser)
    browser = MagicMock()
    context = browser.new_context.return_value
    context.new_page.side_effect = lambda: record(page)
    page = MagicMock()
    page.url = "https://example.org/"
    page.title.side_effect = lambda: record("Example")
    page.screenshot.side_effect = lambda **_: record(b"png")
    page.close.side_effect = lambda: record()
    context.close.side_effect = lambda: record()
    playwright_instance.stop.side_effect = lambda: record()
    monkeypatch.setattr(playwright_api, "sync_playwright", lambda: factory)
    session = isolated_runtime.create_session(owner_actor_id=101, owner_account_session_id=501)

    def request(call):
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(call).result()

    assert request(session.start) is True
    assert request(session.start) is True
    context.new_page.assert_called_once_with()
    assert request(session.get_status)["current_title"] == "Example"
    assert request(session.screenshot) == b"png"
    request(session.close)
    assert len(owner_threads) >= 6
    assert len(set(owner_threads)) == 1
    assert session._browser_worker is None


def test_frame_capture_has_fresh_id_and_real_png_dimensions(isolated_runtime):
    session = isolated_runtime.create_session(owner_actor_id=101, owner_account_session_id=501)
    session.status = runtime.SessionStatus.RUNNING
    session._target_id = "bt_test"
    png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 640, 360)
    session._page = MagicMock()
    session._page.url = "https://example.org/"
    session._page.evaluate.return_value = 30
    session._page.screenshot.return_value = png
    first = session.capture_frame()
    second = session.capture_frame()
    assert first["image"] == png
    assert (first["width"], first["height"]) == (640, 360)
    assert first["frame_id"] != second["frame_id"]
    session._page.evaluate.return_value = 0
    session._last_navigation_at = runtime.time.monotonic()
    with pytest.raises(runtime.BrowserFramePending):
        session.capture_frame()
    session._last_navigation_at = runtime.time.monotonic() - 4
    with pytest.raises(runtime.BrowserFrameEmpty):
        session.capture_frame()
    session._page.evaluate.return_value = 30
    session._page.screenshot.return_value = b"invalid"
    with pytest.raises(RuntimeError, match="valid PNG"):
        session.capture_frame()
    isolated_runtime.close_session(session.session_id)


def test_navigation_respects_existing_browser_policy(isolated_runtime):
    session = isolated_runtime.create_session()
    session._page = MagicMock()
    with pytest.raises(PermissionError, match="browser policy"):
        session._do_execute(runtime.BrowserActionType.NAVIGATE,
                            url="file:///C:/Users/personal")
    session._page.goto.assert_not_called()


def _authorized_client(monkeypatch, manager=None):
    from flask import Flask
    import account.service
    import account.authorization

    if manager is not None:
        monkeypatch.setattr(runtime, "get_session_manager", lambda: manager)
    app = Flask(__name__)
    ai_browser_api.register_ai_browser_api(app)
    actor = {"id": 101, "session_id": 501}
    monkeypatch.setattr(account.service, "get_current_user", lambda: actor)
    monkeypatch.setattr(account.authorization, "check_dual_domain_permission",
                        lambda *_args, **_kwargs: True)
    return app.test_client(), actor


def test_api_rejects_caller_selected_browser_before_creating_session(monkeypatch):
    client, _actor = _authorized_client(monkeypatch)
    for body in ({"cdp_port": 9222}, {"user_data_dir": r"C:\Users\personal"},
                 {"headless": False}):
        response = client.post("/api/browser/sessions", json=body)
        assert response.status_code == 400
        assert response.get_json()["error_code"] == "BROWSER_SESSION_BLOCKED"


def test_api_requires_actor_and_exact_system_browser_grant(monkeypatch):
    import account.service
    import account.authorization

    client, actor = _authorized_client(monkeypatch)
    actor.clear()
    assert client.get("/api/browser/sessions").status_code == 401
    actor.update(id=101, session_id=501)
    monkeypatch.setattr(account.authorization, "check_dual_domain_permission",
                        lambda *_args, **_kwargs: False)
    response = client.get("/api/browser/sessions")
    assert response.status_code == 403
    assert response.get_json()["error_code"] == "BROWSER_PERMISSION_DENIED"


def test_api_session_is_visible_only_to_creating_login(monkeypatch, isolated_runtime):
    client, actor = _authorized_client(monkeypatch, isolated_runtime)

    created = client.post("/api/browser/sessions", json={"auto_start": False})
    assert created.status_code == 200
    session_id = created.get_json()["session_id"]
    assert "cdp_port" not in created.get_json()
    assert "headless" not in created.get_json()
    assert client.get("/api/browser/sessions").get_json()["count"] == 1

    actor["session_id"] = 502
    assert client.get("/api/browser/sessions").get_json()["count"] == 0
    assert client.get(f"/api/browser/sessions/{session_id}").status_code == 404
    assert client.post(f"/api/browser/sessions/{session_id}/stop").status_code == 404

    actor["session_id"] = 501
    assert client.post(f"/api/browser/sessions/{session_id}/stop").get_json()["closed"] is True


def test_api_reuses_owned_running_session_and_reports_other_login_busy(monkeypatch, isolated_runtime):
    client, actor = _authorized_client(monkeypatch, isolated_runtime)
    session = isolated_runtime.create_session(owner_actor_id=101, owner_account_session_id=501)
    session.status = runtime.SessionStatus.RUNNING

    response = client.post("/api/browser/sessions", json={})
    assert response.status_code == 200
    assert response.get_json()["session_id"] == session.session_id
    assert response.get_json()["started"] is True
    actor.update(id=102, session_id=502)
    busy = client.post("/api/browser/sessions", json={})
    assert busy.status_code == 409
    assert busy.get_json()["error_code"] == "BROWSER_CAPACITY_OCCUPIED"
    isolated_runtime.close_session(session.session_id)


def test_frame_api_returns_only_owned_uncached_image(monkeypatch, isolated_runtime):
    client, actor = _authorized_client(monkeypatch, isolated_runtime)
    session = isolated_runtime.create_session(owner_actor_id=101, owner_account_session_id=501)
    session.status = runtime.SessionStatus.RUNNING
    session.capture_frame = lambda: {
        "frame_id": "bf_test", "captured_at": "2026-09-27T00:00:00+00:00",
        "target_id": "bt_test", "page_revision": 3,
        "width": 640, "height": 360, "image": b"png-bytes",
    }
    path = f"/api/browser/sessions/{session.session_id}/frame"
    response = client.get(path)
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data == b"png-bytes"
    assert response.headers["X-LUMENIS-Frame-Id"] == "bf_test"
    assert response.headers["X-LUMENIS-Target-Id"] == "bt_test"
    assert response.headers["X-LUMENIS-Page-Revision"] == "3"
    assert response.headers["X-LUMENIS-Frame-Width"] == "640"
    assert response.headers["Cache-Control"] == "no-store, private"
    actor["session_id"] = 502
    assert client.get(path).status_code == 404
    actor["session_id"] = 501
    session.status = runtime.SessionStatus.CREATED
    assert client.get(path).get_json()["error_code"] == "BROWSER_FRAME_UNAVAILABLE"
    isolated_runtime.close_session(session.session_id)


def test_frame_api_reports_pending_instead_of_blank_success(monkeypatch, isolated_runtime):
    client, _actor = _authorized_client(monkeypatch, isolated_runtime)
    session = isolated_runtime.create_session(owner_actor_id=101, owner_account_session_id=501)
    session.status = runtime.SessionStatus.RUNNING
    def pending():
        raise runtime.BrowserFramePending("painting")
    session.capture_frame = pending
    response = client.get(f"/api/browser/sessions/{session.session_id}/frame")
    assert response.status_code == 202
    assert response.get_json()["error_code"] == "BROWSER_FRAME_PENDING"
    assert response.headers["Cache-Control"] == "no-store, private"
    session.capture_frame = lambda: (_ for _ in ()).throw(runtime.BrowserFrameEmpty("empty"))
    empty = client.get(f"/api/browser/sessions/{session.session_id}/frame")
    assert empty.status_code == 503
    assert empty.get_json()["error_code"] == "BROWSER_FRAME_EMPTY"
    isolated_runtime.close_session(session.session_id)


def test_api_reports_unverified_start_as_unavailable(monkeypatch, isolated_runtime):
    client, _actor = _authorized_client(monkeypatch, isolated_runtime)
    monkeypatch.setattr(browser_surface, "ensure_general_browser",
                        lambda: {"ok": False, "code": "UNVERIFIED_BROWSER_SESSION"})
    response = client.post("/api/browser/sessions", json={})
    assert response.status_code == 503
    assert response.get_json()["ok"] is False
    assert response.get_json()["error_code"] == "BROWSER_START_UNAVAILABLE"
    assert isolated_runtime.list_sessions() == []
