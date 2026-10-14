"""Bounded XHS human-login lifetime; all browser effects are isolated mocks."""

import os
import sys
import threading
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module
from lumenis.adapters import collector_service, human_browser
from lumenis.system.security import OperationType


def _session(*, actor="actor-1", created_at=None):
    return {
        "status": "pending",
        "created_at": (time.time() - 3600) if created_at is None else created_at,
        "platform": "rednote_hk",
        "account": "XHS_RETINAUT",
        "task_id": "task-1",
        "actor_ref": actor,
    }


def test_expired_status_returns_same_leased_task_and_reports_expired(monkeypatch):
    session = _session()
    app_module.app._xhs_login_sessions = {"session-1": session}
    returned = []
    monkeypatch.setattr(app_module, "_collector_browser_actor_ref", lambda: "actor-1")
    monkeypatch.setattr(human_browser, "_authorize_human_browser_return", lambda *args: "xiaohongshu")
    monkeypatch.setattr(
        human_browser,
        "return_registered_worker_to_background",
        lambda account, **kwargs: returned.append((account, kwargs)) or {
            "worker_verified": True, "status": "RETURNED_BACKGROUND",
        },
    )
    monkeypatch.setattr(
        app_module, "_xhs_login_capture",
        lambda endpoint: (_ for _ in ()).throw(AssertionError("expired session must not inspect the page")),
    )

    with app_module.app.test_request_context("/api/xhs/login/status?session_id=session-1"):
        response, status = app_module.api_xhs_login_status()

    assert status == 410
    assert response.get_json()["status"] == "EXPIRED"
    assert returned == [("XHS_RETINAUT", {"task_id": "task-1", "actor_ref": "actor-1"})]
    assert "session-1" not in app_module.app._xhs_login_sessions


def test_wrong_actor_cannot_expire_or_cancel_another_session(monkeypatch):
    session = _session(actor="actor-1")
    app_module.app._xhs_login_sessions = {"session-1": session}
    called = []
    monkeypatch.setattr(app_module, "_collector_browser_actor_ref", lambda: "actor-2")
    monkeypatch.setattr(
        human_browser, "return_registered_worker_to_background",
        lambda *args, **kwargs: called.append((args, kwargs)),
    )

    with app_module.app.test_request_context(
        "/api/xhs/login/cancel", method="POST", json={"session_id": "session-1"},
    ):
        outcome = app_module.api_xhs_login_cancel()
        if isinstance(outcome, tuple):
            response, status = outcome
        else:
            response, status = outcome, outcome.status_code

    assert status == 403
    assert response.get_json()["status"] == "BLOCKED"
    assert called == []
    assert app_module.app._xhs_login_sessions["session-1"] is session


def test_cancel_reuses_existing_authorized_task_and_removes_only_after_verified_return(monkeypatch):
    session = _session(created_at=time.time())
    app_module.app._xhs_login_sessions = {"session-1": session}
    returned = []
    monkeypatch.setattr(app_module, "_collector_browser_actor_ref", lambda: "actor-1")
    monkeypatch.setattr(human_browser, "_authorize_human_browser_return", lambda *args: "xiaohongshu")
    monkeypatch.setattr(
        human_browser,
        "return_registered_worker_to_background",
        lambda account, **kwargs: returned.append((account, kwargs)) or {"worker_verified": True},
    )

    with app_module.app.test_request_context(
        "/api/xhs/login/cancel", method="POST", json={"session_id": "session-1"},
    ):
        outcome = app_module.api_xhs_login_cancel()
        if isinstance(outcome, tuple):
            response, status = outcome
        else:
            response, status = outcome, outcome.status_code

    assert status == 200
    assert response.get_json()["status"] == "CANCELLED_RETURNED_BACKGROUND"
    assert returned == [("XHS_RETINAUT", {"task_id": "task-1", "actor_ref": "actor-1"})]
    assert "session-1" not in app_module.app._xhs_login_sessions


def test_unverified_background_return_keeps_session_for_recovery(monkeypatch):
    session = _session(created_at=time.time())
    app_module.app._xhs_login_sessions = {"session-1": session}
    monkeypatch.setattr(app_module, "_collector_browser_actor_ref", lambda: "actor-1")
    monkeypatch.setattr(human_browser, "_authorize_human_browser_return", lambda *args: "xiaohongshu")
    monkeypatch.setattr(
        human_browser, "return_registered_worker_to_background",
        lambda *args, **kwargs: {"worker_verified": False},
    )

    with app_module.app.test_request_context(
        "/api/xhs/login/cancel", method="POST", json={"session_id": "session-1"},
    ):
        response, status = app_module.api_xhs_login_cancel()

    assert status == 409
    assert response.get_json()["code"] == "HUMAN_LOGIN_BACKGROUND_RETURN_UNVERIFIED"
    assert app_module.app._xhs_login_sessions["session-1"] is session
    assert session["status"] == "return_blocked"


def test_expired_same_actor_session_is_swept_before_new_login(monkeypatch):
    session = _session()
    app_module.app._xhs_login_sessions = {"session-1": session}
    returned = []
    monkeypatch.setattr(
        human_browser, "return_registered_worker_to_background",
        lambda account, **kwargs: returned.append((account, kwargs)) or {"worker_verified": True},
    )

    app_module._sweep_expired_xhs_login_sessions("actor-1")

    assert returned == [("XHS_RETINAUT", {"task_id": "task-1", "actor_ref": "actor-1"})]
    assert "session-1" not in app_module.app._xhs_login_sessions


def test_restart_missing_in_memory_session_fails_without_browser_or_lease_access(monkeypatch):
    if hasattr(app_module.app, "_xhs_login_sessions"):
        delattr(app_module.app, "_xhs_login_sessions")
    called = []
    monkeypatch.setattr(app_module, "_collector_browser_actor_ref", lambda: "actor-1")
    monkeypatch.setattr(
        human_browser, "return_registered_worker_to_background",
        lambda *args, **kwargs: called.append((args, kwargs)),
    )
    monkeypatch.setattr(
        human_browser, "_authorize_human_interactive",
        lambda *args: (_ for _ in ()).throw(AssertionError("no session means no worker lookup")),
    )

    with app_module.app.test_request_context(
        "/api/xhs/login/cancel", method="POST", json={"session_id": "orphaned"},
    ):
        response, status = app_module.api_xhs_login_cancel()

    assert status == 404
    assert response.get_json()["error"] == "HUMAN_LOGIN_SESSION_NOT_FOUND"
    assert called == []


def test_cancel_route_remains_a_browser_operation():
    assert app_module._pg_resolve_operation_type(
        "/api/xhs/login/cancel", "POST",
    ) == OperationType.BROWSER_OPERATION


@pytest.mark.parametrize(
    ("expired", "path", "method", "expected_status", "expected_body_status"),
    [
        (False, "/api/xhs/login/cancel", "POST", 200,
         "CANCELLED_RETURNED_BACKGROUND"),
        (True, "/api/xhs/login/status?session_id=session-1", "GET", 410,
         "EXPIRED"),
    ],
)
def test_cancel_and_expiry_release_same_lease_after_task_state_changes(
        monkeypatch, expired, path, method, expected_status, expected_body_status):
    """Return cleanup uses the existing actor/task lease, not the stale NEED_VERIFY state."""
    lock = threading.Lock()
    assert lock.acquire(blocking=False)
    task = {
        "task_id": "task-1", "manual": True, "status": "cancelled",
        "platforms": ["xiaohongshu"],
        "per_platform": {"xiaohongshu": {"state": "SUCCESS"}},
        "human_browser": {"platform": "xiaohongshu", "status": "ACTIVE"},
        "_actor_ref": "actor-1",
    }
    monkeypatch.setattr(collector_service, "_TASKS", {"task-1": task})
    monkeypatch.setattr(collector_service, "_browser_lock", lock)
    monkeypatch.setattr(
        collector_service, "_HUMAN_BROWSER_LEASE", ("task-1", "xiaohongshu"))
    app_module.app._xhs_login_sessions = {
        "session-1": _session(
            created_at=(time.time() - 3600 if expired else time.time()))
    }
    monkeypatch.setattr(app_module, "_collector_browser_actor_ref", lambda: "actor-1")
    monkeypatch.setattr(
        human_browser, "registered_browser_worker_spec",
        lambda *_args, **_kwargs: {
            "platform": "xiaohongshu", "account": "XHS_RETINAUT",
            "profile": "registered-profile", "port": 0, "browser": "edge",
        },
    )

    class AllowBrowserOperation:
        def check(self, **_kwargs):
            return SimpleNamespace(allowed=True)

    monkeypatch.setattr(
        "lumenis.system.security.get_permission_gate",
        lambda: AllowBrowserOperation(),
    )
    monkeypatch.setattr(human_browser, "_worker_endpoint", lambda _spec: "verified")
    monkeypatch.setattr(
        human_browser, "_switch_registered_worker_mode",
        lambda *_args, **_kwargs: {"online": True, "browser": "edge"},
    )

    @contextmanager
    def _activity_lock(_platform):
        yield True

    monkeypatch.setattr(collector_service, "platform_activity_lock", _activity_lock)

    # Opening remains fail-closed when the original task verification has changed.
    with pytest.raises(PermissionError, match="HUMAN_INTERACTIVE_COLLECTOR_TASK_UNVERIFIED"):
        human_browser._authorize_human_interactive(
            "XHS_RETINAUT", "task-1", "actor-1")

    with app_module.app.test_request_context(path, method=method,
            json={"session_id": "session-1"} if method == "POST" else None):
        response = app_module.api_xhs_login_cancel() if method == "POST" else app_module.api_xhs_login_status()
        if isinstance(response, tuple):
            response, status = response
        else:
            status = response.status_code

    assert status == expected_status
    assert response.get_json()["status"] == expected_body_status
    assert collector_service._HUMAN_BROWSER_LEASE is None
    assert not collector_service._browser_lock.locked()
    assert "session-1" not in app_module.app._xhs_login_sessions
    assert task["human_browser"]["status"] == "RETURNED_BACKGROUND"
