"""Isolated caller contract for the registered RedNote child worker."""
import os
import sys

import pytest


def _configure_bridge(monkeypatch, tmp_path):
    import xhs_cookie_bridge as bridge

    private = tmp_path / "private"
    profile = private / "profiles" / "xhs-retinaut"
    profile.mkdir(parents=True)
    cookie = private / "xhs_cookie_retinaut.txt"
    cookie.write_text("synthetic-test-cookie", encoding="utf-8")
    monkeypatch.setattr(bridge, "PRIVATE_DATA_DIR", str(private))
    monkeypatch.setattr(bridge, "DEFAULT_COLLECTION_ACCOUNT", "XHS_RETINAUT")
    monkeypatch.setattr(bridge, "XHS_RETINAUT_NAME", "XHS_RETINAUT")
    monkeypatch.setattr(bridge, "XHS_RETINAUT", "synthetic-approved-user")
    monkeypatch.setattr(bridge, "ACCOUNT_PROFILES", {
        "XHS_RETINAUT": (str(cookie), str(profile)),
    })
    monkeypatch.setattr(bridge, "_ACTIVE_ACCOUNT", None)
    monkeypatch.setattr(
        bridge, "_extract_user_id_from_cookie_text",
        lambda _value: "synthetic-approved-user",
    )
    monkeypatch.setattr(
        bridge, "collection_policy_gate",
        lambda **_kwargs: {"ok": True},
    )
    monkeypatch.setattr(
        bridge, "cdp_url_for",
        lambda **_kwargs: "http://127.0.0.1:9234",
    )
    monkeypatch.setattr(
        bridge.network_adaptive, "get_adaptive_settings",
        lambda: {"current_scroll_limit": 6, "current_delay_seconds": 0},
    )
    monkeypatch.setattr(bridge.time, "sleep", lambda _seconds: None)
    return bridge

def test_remote_worker_env_carries_registered_profile_and_service_python_without_cookie_read(
        monkeypatch, tmp_path):
    import collector
    import xhs_cookie_bridge as bridge

    private = tmp_path / "private"
    profile = private / "profiles" / "xhs-retinaut"
    profile.mkdir(parents=True)
    cookie = private / "xhs_cookie_retinaut.txt"
    monkeypatch.setattr(bridge, "PRIVATE_DATA_DIR", str(private))
    monkeypatch.setattr(bridge, "DEFAULT_COLLECTION_ACCOUNT", "XHS_RETINAUT")
    monkeypatch.setattr(bridge, "XHS_RETINAUT_NAME", "XHS_RETINAUT")
    monkeypatch.setattr(bridge, "XHS_RETINAUT", "synthetic-approved-user")
    monkeypatch.setattr(bridge, "ACCOUNT_PROFILES", {
        "XHS_RETINAUT": (str(cookie), str(profile)),
    })
    monkeypatch.setattr(
        bridge, "_extract_user_id_from_cookie_text",
        lambda _value: (_ for _ in ()).throw(AssertionError("Cookie must not be read")),
    )
    monkeypatch.setattr(
        collector, "_resolve_server_cdp_url",
        lambda _url, **_kwargs: ("http://127.0.0.1:9234", ""),
    )
    monkeypatch.setenv("XHS_PROFILE_DIR", str(tmp_path / "unregistered"))
    monkeypatch.setenv("XHS_COOKIE_FILE", str(tmp_path / "unregistered-cookie"))
    monkeypatch.setenv("LUMENIS_SERVICE_PYTHON", "untrusted-inherited-value")

    child_env = collector._collection_env(
        account="XHS_RETINAUT", region="intl",
        cdp_url="http://127.0.0.1:9234", require_local_cookie=False,
    )

    assert child_env["XHS_PROFILE_DIR"] == str(profile.resolve())
    assert child_env["LUMENIS_SERVICE_PYTHON"] == sys.executable
    assert child_env["XHS_CDP_URL"] == "http://127.0.0.1:9234"
    assert "XHS_COOKIE_FILE" not in child_env
    assert not cookie.exists()


def test_sync_search_overrides_inherited_service_python_with_absolute_runtime(
        monkeypatch, tmp_path):
    bridge = _configure_bridge(monkeypatch, tmp_path)
    monkeypatch.setenv("LUMENIS_SERVICE_PYTHON", "untrusted-inherited-value")
    captured = {}

    class ChildLaunchCaptured(Exception):
        pass

    def capture_child(command, *, cwd, env, stdout, stderr):
        captured.update(command=command, cwd=cwd, env=dict(env))
        raise ChildLaunchCaptured

    monkeypatch.setattr(bridge.subprocess, "Popen", capture_child)
    with pytest.raises(ChildLaunchCaptured):
        bridge._run_search("synthetic query")

    assert captured["env"]["LUMENIS_SERVICE_PYTHON"] == sys.executable
    assert os.path.isabs(captured["env"]["LUMENIS_SERVICE_PYTHON"])
    assert captured["env"]["XHS_CDP_URL"] == "http://127.0.0.1:9234"
    assert captured["env"]["XHS_PROFILE_DIR"].endswith(
        os.path.join("profiles", "xhs-retinaut"),
    )


def test_sync_search_rejects_nonabsolute_service_python_before_child_launch(
        monkeypatch, tmp_path):
    bridge = _configure_bridge(monkeypatch, tmp_path)
    monkeypatch.setattr(bridge.sys, "executable", "relative/python.exe")
    monkeypatch.setattr(
        bridge.subprocess, "Popen",
        lambda *_args, **_kwargs: pytest.fail("child must not launch"),
    )

    with pytest.raises(RuntimeError, match="LUMENIS_SERVICE_PYTHON_INVALID"):
        bridge._run_search("synthetic query")
