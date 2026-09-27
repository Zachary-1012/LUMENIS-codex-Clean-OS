"""AI Browser must never attach a caller-selected or personal browser profile."""

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


def test_start_fails_closed_when_product_browser_is_unverified(isolated_runtime, monkeypatch):
    session = isolated_runtime.create_session()
    monkeypatch.setattr(browser_surface, "ensure_general_browser",
                        lambda: {"ok": False, "code": "UNVERIFIED_BROWSER_SESSION"})
    assert session.start() is False
    assert session.status == runtime.SessionStatus.ERROR
    assert session._playwright is None


def test_start_uses_fresh_context_and_closes_only_its_pages(isolated_runtime, monkeypatch):
    import playwright.sync_api

    monkeypatch.setattr(browser_surface, "ensure_general_browser", lambda: {"ok": True})
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


def test_navigation_respects_existing_browser_policy(isolated_runtime):
    session = isolated_runtime.create_session()
    session._page = MagicMock()
    with pytest.raises(PermissionError, match="browser policy"):
        session._do_execute(runtime.BrowserActionType.NAVIGATE,
                            url="file:///C:/Users/personal")
    session._page.goto.assert_not_called()


def _authorized_client(monkeypatch):
    from flask import Flask
    import account.service
    import account.authorization

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
    client, actor = _authorized_client(monkeypatch)
    monkeypatch.setattr(runtime, "get_session_manager", lambda: isolated_runtime)

    created = client.post("/api/browser/sessions", json={"auto_start": False})
    assert created.status_code == 200
    session_id = created.get_json()["session_id"]
    assert client.get("/api/browser/sessions").get_json()["count"] == 1

    actor["session_id"] = 502
    assert client.get("/api/browser/sessions").get_json()["count"] == 0
    assert client.get(f"/api/browser/sessions/{session_id}").status_code == 404
    assert client.post(f"/api/browser/sessions/{session_id}/stop").status_code == 404

    actor["session_id"] = 501
    assert client.post(f"/api/browser/sessions/{session_id}/stop").get_json()["closed"] is True


def test_api_reports_unverified_start_as_unavailable(monkeypatch, isolated_runtime):
    client, _actor = _authorized_client(monkeypatch)
    monkeypatch.setattr(runtime, "get_session_manager", lambda: isolated_runtime)
    monkeypatch.setattr(browser_surface, "ensure_general_browser",
                        lambda: {"ok": False, "code": "UNVERIFIED_BROWSER_SESSION"})
    response = client.post("/api/browser/sessions", json={})
    assert response.status_code == 503
    assert response.get_json()["ok"] is False
    assert response.get_json()["error_code"] == "BROWSER_START_UNAVAILABLE"
    assert isolated_runtime.list_sessions() == []
