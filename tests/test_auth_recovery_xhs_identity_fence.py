from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
import importlib.util
from pathlib import Path

import pytest


# Keep this regression test away from the workstation's persisted risk state.
_risk_module = ModuleType("lumenis.adapters.risk_controller")
_risk_module.risk_controller = SimpleNamespace(
    snapshot=lambda: [], mark_recovered=lambda _platform: None,
)
_risk_module.NEED_VERIFY = "NEED_VERIFY"
_risk_module.IP_RISK = "IP_RISK"
_risk_module.LIGHT = "LIGHT"
_risk_module.MEDIUM = "MEDIUM"
_risk_module.RECOVERING = "RECOVERING"
_previous_risk_module = sys.modules.get("lumenis.adapters.risk_controller")
sys.modules["lumenis.adapters.risk_controller"] = _risk_module
try:
    # Load a test-only module instance. Importing the production module here
    # would leave its global risk_controller bound to this fake for later tests.
    _spec = importlib.util.spec_from_file_location(
        "lumenis.adapters._auth_recovery_identity_test",
        Path(__file__).resolve().parents[1] / "lumenis/adapters/auth_recovery.py",
    )
    auth_recovery = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(auth_recovery)
finally:
    if _previous_risk_module is None:
        sys.modules.pop("lumenis.adapters.risk_controller", None)
    else:
        sys.modules["lumenis.adapters.risk_controller"] = _previous_risk_module


def _owner(monkeypatch, *, identity=None, endpoint="https://worker.example:9443", error=""):
    calls = []
    fake = ModuleType("collector")

    def policy_gate(*, region=None, account=None):
        calls.append(("policy", region, account))
        return identity if identity is not None else {
            "ok": True,
            "account": "APPROVED_IDENTITY",
            "region": "intl",
            "host": "www.rednote.com",
        }

    def resolve_endpoint(*, account=None, region=None):
        calls.append(("endpoint", account, region))
        return endpoint, error

    fake._collection_policy_gate = policy_gate
    fake._resolve_server_cdp_url = resolve_endpoint
    monkeypatch.setitem(sys.modules, "collector", fake)
    return calls


def test_xhs_profile_uses_owner_identity_and_current_endpoint(monkeypatch):
    calls = _owner(monkeypatch)

    profile, error = auth_recovery._resolve_recovery_profile("xiaohongshu")

    assert error == ""
    assert profile["region"] == "intl"
    assert profile["account"] == "APPROVED_IDENTITY"
    assert profile["cdp_url"] == "https://worker.example:9443"
    assert "port" not in profile
    assert "profile" not in profile
    assert calls == [
        ("policy", "intl", None),
        ("endpoint", "APPROVED_IDENTITY", "intl"),
    ]


@pytest.mark.parametrize("platform", ["instagram", "google"])
def test_other_authorized_profile_paths_remain_configured(platform):
    profile, error = auth_recovery._resolve_recovery_profile(platform)

    assert error == ""
    if platform == "instagram":
        from lumenis.adapters.human_browser import readonly_worker_spec

        registered = readonly_worker_spec(platform)
        assert profile["port"] == registered["port"]
        assert profile["profile"] == registered["profile"]
        assert profile["cdp_url"] == f"http://127.0.0.1:{registered['port']}"
    else:
        # Google is outside this XHS worker migration and retains its existing route.
        assert profile["port"] == 9223
        assert profile["profile"] == "edge-cdp-proxy"


@pytest.mark.parametrize(
    ("identity", "endpoint", "resolver_error", "expected_error"),
    [
        (
            {"ok": True, "account": "MAINLAND", "region": "cn", "host": "www.xiaohongshu.com"},
            "https://worker.example:9443",
            "",
            "XHS_RECOVERY_IDENTITY_REJECTED",
        ),
        (
            {"ok": False, "account": "APPROVED_IDENTITY", "region": "intl", "host": "www.rednote.com"},
            "https://worker.example:9443",
            "",
            "XHS_RECOVERY_POLICY_BLOCKED",
        ),
        (
            {"ok": True, "account": "APPROVED_IDENTITY", "region": "intl", "host": "www.rednote.com"},
            "",
            "COLLECTOR_ENDPOINT_NOT_CONFIGURED",
            "XHS_RECOVERY_ENDPOINT_NOT_CONFIGURED",
        ),
        (
            {"ok": True, "account": "APPROVED_IDENTITY", "region": "intl", "host": "www.rednote.com"},
            "http://127.0.0.1:9222",
            "",
            "XHS_RECOVERY_POLICY_BLOCKED",
        ),
    ],
)
def test_request_rejects_wrong_or_unconfigured_xhs_owner(
    monkeypatch, identity, endpoint, resolver_error, expected_error
):
    calls = _owner(
        monkeypatch,
        identity=identity,
        endpoint=endpoint,
        error=resolver_error,
    )
    monkeypatch.setattr(auth_recovery, "_bridge_to_recovery_center", lambda *args: None)
    monkeypatch.setattr(auth_recovery.risk_controller, "snapshot", list)
    thread_starts = []

    class FakeThread:
        def __init__(self, *, target, args, daemon, name):
            self.target = target
            self.args = args

        def start(self):
            thread_starts.append((self.target, self.args))

    monkeypatch.setattr(auth_recovery, "threading", type("FakeThreading", (), {"Thread": FakeThread}))

    result = auth_recovery.request_recovery("xiaohongshu", source_state="AUTH_REQUIRED")

    assert result == {"success": False, "error": expected_error}
    assert thread_starts == []
    assert calls[0] == ("policy", "intl", None)
    if identity.get("region") == "cn":
        assert len(calls) == 1


def test_request_revalidates_owner_before_reusing_pending_session(monkeypatch):
    calls = _owner(
        monkeypatch,
        identity={"ok": False, "account": "APPROVED_IDENTITY", "region": "intl", "host": "www.rednote.com"},
    )
    monkeypatch.setattr(auth_recovery, "_bridge_to_recovery_center", lambda *args: None)
    monkeypatch.setattr(auth_recovery.risk_controller, "snapshot", list)
    monkeypatch.setitem(
        auth_recovery._sessions,
        "xiaohongshu",
        {"platform": "xiaohongshu", "state": auth_recovery.WAITING_SCAN},
    )

    result = auth_recovery.request_recovery("xiaohongshu", source_state="AUTH_REQUIRED")

    assert result == {"success": False, "error": "XHS_RECOVERY_POLICY_BLOCKED"}
    assert calls == [("policy", "intl", None)]


@pytest.mark.parametrize("platform", ["weibo", "bilibili"])
def test_request_rejects_shared_protected_profile_before_thread(monkeypatch, platform):
    monkeypatch.setattr(auth_recovery, "_bridge_to_recovery_center", lambda *args: None)
    thread_starts = []

    class FakeThread:
        def __init__(self, *, target, args, daemon, name):
            self.target = target
            self.args = args

        def start(self):
            thread_starts.append((self.target, self.args))

    monkeypatch.setattr(auth_recovery, "threading", type("FakeThreading", (), {"Thread": FakeThread}))

    result = auth_recovery.request_recovery(platform, source_state="AUTH_REQUIRED")

    assert result == {
        "success": False,
        "error": "PROTECTED_PROFILE_NOT_COLLECTION_ASSET",
    }
    assert thread_starts == []


def test_registered_douyin_worker_can_queue_recovery_without_starting_browser(monkeypatch):
    from lumenis.adapters import human_browser

    monkeypatch.setattr(auth_recovery, "_bridge_to_recovery_center", lambda *args: None)
    monkeypatch.setattr(auth_recovery.risk_controller, "snapshot", list)
    auth_recovery._sessions.pop("douyin", None)
    starts = []

    class FakeThread:
        def __init__(self, *, target, args, daemon, name):
            self.target = target
            self.args = args
            self.daemon = daemon
            self.name = name

        def start(self):
            starts.append((self.target, self.args, self.daemon, self.name))

    monkeypatch.setattr(auth_recovery, "threading", type("FakeThreading", (), {"Thread": FakeThread}))
    spec = human_browser.readonly_worker_spec("douyin")
    cfg, error = auth_recovery._resolve_recovery_profile("douyin")

    assert error == ""
    assert cfg["port"] == spec["port"]
    assert cfg["profile"] == spec["profile"]
    assert cfg["cdp_url"] == f"http://127.0.0.1:{spec['port']}"
    assert cfg["port"] not in {9222, 9223, 9224}

    result = auth_recovery.request_recovery("douyin", source_state="AUTH_REQUIRED")

    assert result["success"] is True
    assert result["kind"] == auth_recovery.KIND_AUTH
    assert len(starts) == 1
    target, args, daemon, name = starts[0]
    assert target is auth_recovery._open_and_watch
    assert args == ("douyin", auth_recovery.KIND_AUTH)
    assert daemon is True
    assert name == "auth-recovery-douyin"


@pytest.mark.parametrize("field", ["platform", "account", "port", "profile"])
def test_recovery_rejects_mismatched_registered_worker_identity(monkeypatch, field, tmp_path):
    from lumenis.adapters import human_browser

    expected = human_browser.readonly_worker_spec("douyin")
    returned = {**expected, "platform": "douyin"}
    if field == "platform":
        returned[field] = "weibo"
    elif field == "account":
        returned[field] = "UNRELATED_ACCOUNT"
    elif field == "port":
        returned[field] = expected["port"] + 100
    else:
        returned[field] = str(tmp_path / "different-profile")
    monkeypatch.setattr(human_browser, "registered_browser_worker_spec", lambda _identity: returned)

    cfg, error = auth_recovery._resolve_recovery_profile("douyin")

    assert cfg is None
    assert error == "RECOVERY_WORKER_NOT_REGISTERED"


def test_unregistered_douyin_legacy_profile_fails_closed_before_thread(monkeypatch):
    from lumenis.adapters import human_browser

    monkeypatch.setattr(
        human_browser,
        "registered_browser_worker_spec",
        lambda _identity: (_ for _ in ()).throw(RuntimeError("READONLY_WORKER_NOT_REGISTERED")),
    )
    monkeypatch.setattr(auth_recovery, "_bridge_to_recovery_center", lambda *args: None)
    starts = []

    class FakeThread:
        def __init__(self, *, target, args, daemon, name):
            self.target = target
            self.args = args

        def start(self):
            starts.append((self.target, self.args))

    monkeypatch.setattr(auth_recovery, "threading", type("FakeThreading", (), {"Thread": FakeThread}))

    result = auth_recovery.request_recovery("douyin", source_state="AUTH_REQUIRED")

    assert result == {"success": False, "error": "RECOVERY_WORKER_NOT_REGISTERED"}
    assert starts == []


def test_unregistered_douyin_background_retry_never_connects(monkeypatch):
    from lumenis.adapters import human_browser

    states = []
    monkeypatch.setattr(auth_recovery, "_set", lambda platform, **kwargs: states.append((platform, kwargs)))
    monkeypatch.setattr(
        human_browser,
        "registered_browser_worker_spec",
        lambda _identity: (_ for _ in ()).throw(RuntimeError("READONLY_WORKER_NOT_REGISTERED")),
    )
    monkeypatch.setattr(
        auth_recovery,
        "_connect_hb",
        lambda *_args, **_kwargs: pytest.fail("unregistered legacy profile must never connect"),
    )

    auth_recovery._open_and_watch("douyin", auth_recovery.KIND_AUTH)

    assert states == [("douyin", {
        "state": auth_recovery.AUTH_FAILED,
        "message": "当前获准身份或浏览器端点不可用，恢复已拒绝",
    })]


def test_check_recovery_uses_fake_owner_bound_browser_only(monkeypatch):
    calls = _owner(monkeypatch)
    seen = []

    def fake_read(platform, *, launch, cfg):
        seen.append((platform, launch, cfg.get("cdp_url"), cfg.get("region")))
        return auth_recovery.AUTH_VALID, {"web_session": "fake", "a1": "fake"}

    monkeypatch.setattr(auth_recovery, "_read_auth_cookies", fake_read)
    monkeypatch.setattr(auth_recovery.risk_controller, "mark_recovered", lambda platform: None)

    result = auth_recovery.check_recovery("xiaohongshu")

    assert result["success"] is True
    assert result["recovered"] is True
    assert result["status"] == auth_recovery.AUTH_VALID
    assert seen == [("xiaohongshu", True, "https://worker.example:9443", "intl")]
    assert calls[-1] == ("endpoint", "APPROVED_IDENTITY", "intl")


def test_background_watch_revalidates_owner_before_browser_access(monkeypatch):
    _owner(
        monkeypatch,
        identity={"ok": False, "account": "APPROVED_IDENTITY", "region": "intl", "host": "www.rednote.com"},
    )
    states = []
    monkeypatch.setattr(auth_recovery, "_set", lambda platform, **kwargs: states.append((platform, kwargs)))
    monkeypatch.setattr(
        auth_recovery,
        "_connect_hb",
        lambda *_args, **_kwargs: pytest.fail("blocked owner must not connect a browser"),
    )

    auth_recovery._open_and_watch("xiaohongshu", auth_recovery.KIND_AUTH)

    assert states == [("xiaohongshu", {
        "state": auth_recovery.AUTH_FAILED,
        "message": "当前获准身份或浏览器端点不可用，恢复已拒绝",
    })]


def test_approved_xhs_endpoint_failure_has_no_legacy_port_assumption(monkeypatch):
    _owner(monkeypatch)
    states = []
    monkeypatch.setattr(auth_recovery, "_set", lambda platform, **kwargs: states.append((platform, kwargs)))
    monkeypatch.setattr(auth_recovery, "WATCH_TIMEOUT", -1)

    class FakeBrowser:
        def connect(self):
            raise RuntimeError("fake endpoint unavailable")

        def close(self):
            pass

    monkeypatch.setattr(auth_recovery, "_connect_hb", lambda *_args, **_kwargs: FakeBrowser())

    auth_recovery._open_and_watch("xiaohongshu", auth_recovery.KIND_AUTH)

    failures = [values for platform, values in states
                if platform == "xiaohongshu" and values.get("state") == auth_recovery.QR_FAILED]
    assert failures
    assert "获准浏览器端点" in failures[0]["message"]


def test_health_check_refuses_when_owner_identity_is_unavailable(monkeypatch):
    _owner(
        monkeypatch,
        identity={"ok": False, "account": "APPROVED_IDENTITY", "region": "intl", "host": "www.rednote.com"},
    )
    monkeypatch.setattr(
        auth_recovery,
        "_read_auth_cookies",
        lambda *_args, **_kwargs: pytest.fail("unavailable owner must not read cookies"),
    )

    result = auth_recovery.health_check("xiaohongshu")

    assert result["success"] is False
    assert result["status"] == auth_recovery.UNKNOWN
    assert result["error"] == "XHS_RECOVERY_POLICY_BLOCKED"


def test_recovery_platforms_do_not_advertise_xhs_legacy_port_or_profile():
    xhs = next(item for item in auth_recovery.recovery_platforms()
               if item["platform"] == "xiaohongshu")

    assert xhs["port"] is None
    assert xhs["profile"] is None


def test_human_browser_receives_owner_endpoint_without_profile_or_port(monkeypatch):
    captured = {}
    fake_module = ModuleType("lumenis.adapters.human_browser")

    class FakeHumanBrowser:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_module.HumanBrowser = FakeHumanBrowser
    monkeypatch.setitem(sys.modules, "lumenis.adapters.human_browser", fake_module)

    browser = auth_recovery._connect_hb({"cdp_url": "https://worker.example:9443"})

    assert isinstance(browser, FakeHumanBrowser)
    assert captured == {
        "cdp_url": "https://worker.example:9443",
        "launch_url": "about:blank",
        "auto_ensure": False,
    }
