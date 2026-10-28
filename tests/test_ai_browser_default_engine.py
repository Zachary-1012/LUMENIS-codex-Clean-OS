"""AI Browser must never attach a caller-selected or personal browser profile."""

import threading
import struct
import hashlib
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
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


def _valid_png(width=640, height=360):
    import zlib
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\0" + b"\x80" * width * 3) * height)) + chunk(b"IEND", b""))


def _install_current_frame(session):
    png = _valid_png()
    page = MagicMock()
    page.url = "https://origin.example/work"
    page.evaluate.side_effect = lambda script, *_args: (
        {"width": 640, "height": 360, "dpr": 1}
        if "window.innerWidth" in script else "safe page text"
    )
    page.screenshot.return_value = png
    session._page = page
    session._context = MagicMock()
    session._target_id = "bt_confirmation"
    session._page_revision = 7
    binding = {
        "frame_id": "bf_confirmation",
        "target_id": session._target_id,
        "page_revision": session._page_revision,
        "viewport": {"width": 640, "height": 360, "dpr": 1},
    }
    session._latest_frame_binding = binding
    session._latest_frame_image_sha256 = hashlib.sha256(png).hexdigest()
    session._latest_frame_document_url = page.url
    return binding


def test_frame_capture_has_fresh_id_and_real_png_dimensions(isolated_runtime):
    session = isolated_runtime.create_session(owner_actor_id=101, owner_account_session_id=501)
    session.status = runtime.SessionStatus.RUNNING
    session._target_id = "bt_test"
    png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 640, 360)
    session._page = MagicMock()
    session._page.url = "https://example.org/"
    text_length = [30]
    session._page.evaluate.side_effect = lambda script: ({"width": 640, "height": 360, "dpr": 1} if "window.innerWidth" in script else text_length[0])
    session._page.screenshot.return_value = png
    first = session.capture_frame()
    second = session.capture_frame()
    assert first["image"] == png
    assert (first["width"], first["height"]) == (640, 360)
    assert first["frame_id"] != second["frame_id"]
    text_length[0] = 0
    session._last_navigation_at = runtime.time.monotonic()
    with pytest.raises(runtime.BrowserFramePending):
        session.capture_frame()
    session._last_navigation_at = runtime.time.monotonic() - 4
    with pytest.raises(runtime.BrowserFrameEmpty):
        session.capture_frame()
    text_length[0] = 30
    session._page.screenshot.return_value = b"invalid"
    with pytest.raises(RuntimeError, match="valid PNG"):
        session.capture_frame()
    isolated_runtime.close_session(session.session_id)


def test_navigation_respects_existing_browser_policy(isolated_runtime):
    session = isolated_runtime.create_session()
    session._page = MagicMock()
    with pytest.raises(runtime.BrowserNavigationPolicyError, match="BROWSER_NAVIGATION_BLOCKED"):
        session._do_execute(runtime.BrowserActionType.NAVIGATE,
                            url="file:///C:/Users/personal")
    session._page.goto.assert_not_called()


def test_human_navigation_confirmation_is_bound_one_use_and_redacted(monkeypatch, isolated_runtime):
    import browser_surface

    monkeypatch.setattr(browser_surface, "_is_internal_host", lambda _host: False)
    client, _actor = _authorized_client(monkeypatch, isolated_runtime)
    session = isolated_runtime.create_session(owner_actor_id=101, owner_account_session_id=501)
    session.status = runtime.SessionStatus.RUNNING
    binding = _install_current_frame(session)
    lease = session.acquire_human_control()["lease_token"]
    path = f"/api/browser/sessions/{session.session_id}/human-control/navigate"
    headers = {"X-LUMENIS-Human-Control-Lease": lease}
    url = "https://needs-confirmation.example/path?access_token=secret#private"
    original_navigate = session.navigate
    calls = []

    def fake_navigate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            success=True,
                error="",
            to_dict=lambda: {"success": True, "action": "navigate", "error": ""},
            before_state=None,
            after_state=None,
        )

    session.navigate = fake_navigate
    try:
        prepared = client.post(path, headers=headers, json={"url": url, "frame_binding": binding})
        assert prepared.status_code == 409
        body = prepared.get_json()
        assert body["error_code"] == "BROWSER_NAVIGATION_CONFIRMATION_REQUIRED"
        assert body["confirmation_target"] == "https://needs-confirmation.example/path"
        assert "secret" not in str(body) and "#private" not in str(body)
        assert calls == []
        assert session._page.goto.call_count == 0

        confirmed = client.post(path, headers=headers, json={
            "url": url,
            "frame_binding": binding,
            "confirmation_id": body["confirmation_id"],
        })
        assert confirmed.status_code == 200, confirmed.get_json()
        assert calls[0]["human_navigation_confirmation_url"] == url

        replay = client.post(path, headers=headers, json={
            "url": url,
            "frame_binding": binding,
            "confirmation_id": body["confirmation_id"],
        })
        assert replay.status_code == 409
        assert replay.get_json()["error_code"] == "BROWSER_NAVIGATION_CONFIRMATION_STALE"
        assert len(calls) == 1
    finally:
        session.navigate = original_navigate
        isolated_runtime.close_session(session.session_id)


def test_human_navigation_confirmation_rejects_changed_url_and_lease(monkeypatch, isolated_runtime):
    import browser_surface

    monkeypatch.setattr(browser_surface, "_is_internal_host", lambda _host: False)
    client, _actor = _authorized_client(monkeypatch, isolated_runtime)
    session = isolated_runtime.create_session(owner_actor_id=101, owner_account_session_id=501)
    session.status = runtime.SessionStatus.RUNNING
    binding = _install_current_frame(session)
    first_lease = session.acquire_human_control()["lease_token"]
    path = f"/api/browser/sessions/{session.session_id}/human-control/navigate"
    first_headers = {"X-LUMENIS-Human-Control-Lease": first_lease}
    url = "https://needs-confirmation.example/path?one=1"
    prepared = client.post(path, headers=first_headers, json={"url": url, "frame_binding": binding})
    confirmation_id = prepared.get_json()["confirmation_id"]

    changed = client.post(path, headers=first_headers, json={
        "url": "https://needs-confirmation.example/other?one=1",
        "frame_binding": binding,
        "confirmation_id": confirmation_id,
    })
    assert changed.status_code == 409
    assert changed.get_json()["error_code"] == "BROWSER_NAVIGATION_CONFIRMATION_STALE"
    assert session._page.goto.call_count == 0

    second_id = client.post(path, headers=first_headers, json={"url": url, "frame_binding": binding}).get_json()["confirmation_id"]
    assert session.release_human_control(first_lease)
    second_lease = session.acquire_human_control()["lease_token"]
    stale_lease = client.post(path, headers={"X-LUMENIS-Human-Control-Lease": second_lease}, json={
        "url": url,
        "frame_binding": binding,
        "confirmation_id": second_id,
    })
    assert stale_lease.status_code == 409
    assert stale_lease.get_json()["error_code"] == "BROWSER_NAVIGATION_CONFIRMATION_STALE"
    assert session._page.goto.call_count == 0

    third_id = client.post(path, headers={"X-LUMENIS-Human-Control-Lease": second_lease}, json={
        "url": url, "frame_binding": binding,
    }).get_json()["confirmation_id"]
    changed_binding = {
        **binding,
        "frame_id": "bf_new_revision",
        "page_revision": binding["page_revision"] + 1,
    }
    session._page_revision = changed_binding["page_revision"]
    session._latest_frame_binding = changed_binding
    stale_frame = client.post(path, headers={"X-LUMENIS-Human-Control-Lease": second_lease}, json={
        "url": url,
        "frame_binding": changed_binding,
        "confirmation_id": third_id,
    })
    assert stale_frame.status_code == 409
    assert stale_frame.get_json()["error_code"] == "BROWSER_NAVIGATION_CONFIRMATION_STALE"
    assert session._page.goto.call_count == 0
    isolated_runtime.close_session(session.session_id)


def test_confirmed_navigation_does_not_authorize_an_unapproved_redirect(monkeypatch, isolated_runtime):
    import browser_surface

    requested = "https://manual.example/confirmed?token=private"
    redirected = "https://different.example/landing"

    def policy(url, mode=None):
        if url == "https://approved.example/":
            return {"allowed": True, "status": "allowed", "mode": mode or "strict", "host": "approved.example"}
        return {"allowed": False, "status": "need_confirmation", "mode": mode or "strict", "host": "unknown.example"}

    monkeypatch.setattr(browser_surface, "evaluate_navigation", policy)

    class FakeCdp:
        def __init__(self):
            self.callback = None
            self.calls = []

        def on(self, _event, callback):
            self.callback = callback

        def send(self, method, params=None):
            self.calls.append((method, params))
            if method == "Page.getFrameTree":
                return {"frameTree": {"frame": {"id": "main-frame"}}}
            if method == "Fetch.enable":
                self.callback({
                    "requestId": "initial",
                    "resourceType": "Document",
                    "frameId": "main-frame",
                    "request": {"url": requested},
                })
                self.callback({
                    "requestId": "redirect",
                    "resourceType": "Document",
                    "frameId": "main-frame",
                    "request": {"url": redirected},
                })
            return {}

        def detach(self):
            self.calls.append(("detach", None))

    session = isolated_runtime.create_session()
    session._page = MagicMock()
    cdp = FakeCdp()
    session._context = SimpleNamespace(new_cdp_session=lambda _page: cdp)
    result = runtime.ActionExecutionResult(
        success=True, action="navigate", result=runtime.ActionResult.PASS,
    )
    guarded = session._run_with_navigation_guard(
        lambda: result,
        confirmed_target_url=requested,
    )

    assert guarded.success is False
    assert guarded.error == "BROWSER_NAVIGATION_REDIRECT_BLOCKED"
    assert ("Fetch.continueRequest", {"requestId": "initial"}) in cdp.calls
    assert any(method == "Fetch.failRequest" and params.get("requestId") == "redirect"
               for method, params in cdp.calls)
    isolated_runtime.close_session(session.session_id)


def test_confirmation_does_not_override_a_new_ssrf_policy_block(monkeypatch, isolated_runtime):
    import browser_surface

    requested = "https://manual.example/confirmed"
    calls = []

    def policy(url, mode=None):
        calls.append(url)
        if len(calls) == 1:
            return {"allowed": False, "status": "need_confirmation", "mode": "strict"}
        return {"allowed": False, "status": "blocked", "mode": "strict", "reason": "SSRF"}

    monkeypatch.setattr(browser_surface, "evaluate_navigation", policy)

    class FakeCdp:
        def __init__(self):
            self.callback = None
            self.calls = []

        def on(self, _event, callback):
            self.callback = callback

        def send(self, method, params=None):
            self.calls.append((method, params))
            if method == "Page.getFrameTree":
                return {"frameTree": {"frame": {"id": "main-frame"}}}
            if method == "Fetch.enable":
                self.callback({
                    "requestId": "initial",
                    "resourceType": "Document",
                    "frameId": "main-frame",
                    "request": {"url": requested},
                })
            return {}

        def detach(self):
            self.calls.append(("detach", None))

    session = isolated_runtime.create_session()
    session._page = MagicMock()
    cdp = FakeCdp()
    session._context = SimpleNamespace(new_cdp_session=lambda _page: cdp)
    result = runtime.ActionExecutionResult(
        success=True, action="navigate", result=runtime.ActionResult.PASS,
    )
    guarded = session._run_with_navigation_guard(
        lambda: result,
        requested_target_url=requested,
        confirmed_target_url=requested,
    )

    assert guarded.success is False
    assert guarded.error == "BROWSER_NAVIGATION_BLOCKED"
    assert any(method == "Fetch.failRequest" and params.get("requestId") == "initial"
               for method, params in cdp.calls)
    isolated_runtime.close_session(session.session_id)


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


def _local_workspace_client(monkeypatch, manager=None):
    from flask import Flask
    import account.service

    if manager is not None:
        monkeypatch.setattr(runtime, "get_session_manager", lambda: manager)
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    ai_browser_api.register_ai_browser_api(app)
    monkeypatch.setattr(account.service, "get_current_user", lambda: None)
    return app.test_client()


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


def test_api_open_workspace_session_is_server_bound_and_rejects_forged_identity(monkeypatch, isolated_runtime):
    client = _local_workspace_client(monkeypatch, isolated_runtime)
    created = client.post("/api/browser/sessions", json={"auto_start": False})
    assert created.status_code == 200
    session_id = created.get_json()["session_id"]
    session = isolated_runtime.get_session(session_id)
    assert session is not None
    assert session.owner_actor_id is None
    assert session.owner_account_session_id is None
    assert session.owner_principal_ref == "workspace:local"
    assert client.get("/api/browser/sessions").get_json()["count"] == 1
    forged = client.get(
        f"/api/browser/sessions/{session_id}",
        headers={"X-Actor-Id": "101"},
    )
    assert forged.status_code == 401
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
    png = _valid_png()
    session.capture_frame = lambda: {
        "frame_id": "bf_test", "captured_at": "2026-09-27T00:00:00+00:00",
        "target_id": "bt_test", "page_revision": 3,
        "width": 640, "height": 360, "image": png,
        "viewport": {"width": 640, "height": 360, "dpr": 1},
    }
    path = f"/api/browser/sessions/{session.session_id}/frame"
    response = client.get(path)
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data == png
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


@pytest.mark.parametrize("bad_viewport", [None, 30, {}, {"width": 0, "height": 360, "dpr": 1}])
def test_frame_capture_rejects_invalid_viewport_fixture(isolated_runtime, bad_viewport):
    session = isolated_runtime.create_session(owner_actor_id=101, owner_account_session_id=501)
    session.status = runtime.SessionStatus.RUNNING
    session._target_id = "bt_negative_fixture"
    session._page = MagicMock(); session._page.url = "https://example.org/"
    session._page.screenshot.return_value = _valid_png()
    session._page.evaluate.side_effect = lambda script: bad_viewport if "window.innerWidth" in script else 30
    with pytest.raises(runtime.BrowserFrameStaleError): session.capture_frame()
    isolated_runtime.close_session(session.session_id)
