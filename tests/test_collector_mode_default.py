"""Collection dispatch defaults to manual and fences auto before identity I/O."""
from __future__ import annotations

import threading
from types import SimpleNamespace

from flask import Flask

import collection_api
import collector_automation
import xhs_cookie_bridge


def _dispatcher():
    obj = collector_automation.CollectorAutomation.__new__(
        collector_automation.CollectorAutomation
    )
    obj._lock = threading.Lock()
    obj.is_running = False
    return obj


def _runnable_plan(monkeypatch):
    # Identity-policy unit tests require an explicit in-scope query, independent
    # of the seed database. Plan resolution itself has separate blocking tests.
    monkeypatch.setattr(xhs_cookie_bridge, "_resolve_acquisition_plan", lambda *_: SimpleNamespace(
        is_runnable=True, keywords=("test",), to_dict=lambda: {"status": "READY"},
    ))


def test_auto_and_unknown_modes_stop_before_identity_preflight(monkeypatch):
    calls = []
    for key in (
        "REDNOTE_AUTO_RUN", "REDNOTE_AUTO_SCOPE", "REDNOTE_AUTO_SOURCE",
        "REDNOTE_AUTO_CADENCE_MINUTES",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(
        xhs_cookie_bridge, "collection_policy_gate",
        lambda **_kwargs: calls.append("identity") or {"ok": False, "reason": "blocked"},
    )
    dispatcher = _dispatcher()

    for mode in ("standard", "auto", "deep"):
        result = dispatcher.start_collection(mode=mode)
        assert result["ok"] is False
        assert result["status"] == "BLOCKED"
        assert result["code"] == "AUTO_COLLECTION_OPT_IN_REQUIRED"
    result = dispatcher.start_collection(mode="unsupported")
    assert result["ok"] is False
    assert result["code"] == "INVALID_COLLECTION_MODE"
    assert calls == []


def test_manual_dispatch_reaches_existing_identity_policy(monkeypatch):
    _runnable_plan(monkeypatch)
    calls = []
    monkeypatch.setattr(
        xhs_cookie_bridge, "collection_policy_gate",
        lambda **_kwargs: calls.append("identity") or {"ok": False, "reason": "blocked"},
    )
    result = _dispatcher().start_collection()
    assert result["ok"] is False
    assert "采集策略门禁" in result["error"]
    assert calls == ["identity"]



def test_supported_auto_opt_in_reaches_existing_identity_policy(monkeypatch):
    _runnable_plan(monkeypatch)
    calls = []
    monkeypatch.setenv("REDNOTE_AUTO_RUN", "true")
    monkeypatch.setenv("REDNOTE_AUTO_SCOPE", "GUANGZHOU_TAIKOO_HUI")
    monkeypatch.setenv("REDNOTE_AUTO_SOURCE", "rednote_hk")
    monkeypatch.setenv("REDNOTE_AUTO_CADENCE_MINUTES", "720")
    monkeypatch.setattr(
        xhs_cookie_bridge, "collection_policy_gate",
        lambda **_kwargs: calls.append("identity") or {"ok": False, "reason": "blocked"},
    )
    result = _dispatcher().start_collection(mode="auto")
    assert result["ok"] is False
    assert "采集策略门禁" in result["error"]
    assert calls == ["identity"]


def test_http_start_defaults_to_manual_and_status_has_no_auto_schedule(monkeypatch):
    modes = []

    class FakeCollector:
        def start_collection(self, **kwargs):
            modes.append(kwargs["mode"])
            return {"ok": False, "code": "DENIED_BY_TEST"}

    monkeypatch.setattr(
        collection_api.collector_automation, "get_collector_automation",
        lambda: FakeCollector(),
    )
    monkeypatch.setattr(
        collection_api.xhs_cookie_bridge, "get_account_status",
        lambda: {"cookie_configured": False, "today_runs": 0},
    )
    monkeypatch.setattr(
        collection_api.xhs_cookie_bridge, "get_circuit_state",
        lambda: {"open": False},
    )
    monkeypatch.setattr(collection_api.xhs_cookie_bridge, "_tasks", {})
    monkeypatch.setattr(
        collection_api.db, "get_db",
        lambda: (_ for _ in ()).throw(RuntimeError("no DB in policy test")),
    )
    for key in (
        "REDNOTE_AUTO_RUN", "REDNOTE_AUTO_SCOPE", "REDNOTE_AUTO_SOURCE",
        "REDNOTE_AUTO_CADENCE_MINUTES",
    ):
        monkeypatch.delenv(key, raising=False)

    flask_app = Flask(__name__)
    collection_api.register_collection_api(flask_app)
    client = flask_app.test_client()
    started = client.post("/api/collector/start", json={})
    assert started.status_code == 200
    assert started.get_json()["ok"] is False
    assert modes == ["manual"]
    status = client.get("/api/collect/schedule-status")
    assert status.status_code == 200
    body = status.get_json()
    assert body["auto_enabled"] is False
    assert body["next_collect"] == "未开启自动采集"
