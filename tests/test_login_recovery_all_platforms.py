"""PO rule 2026-10-13 #1: every collection platform has login-expired recovery
bound to its registered background worker, and the interrupted task resumes."""
from __future__ import annotations

import pytest

from lumenis.adapters import auth_recovery as ar

PLATFORMS = ["xiaohongshu", "douyin", "x", "instagram", "facebook", "wechat_oa"]


@pytest.mark.parametrize("platform", PLATFORMS)
def test_every_platform_has_login_recovery_profile(platform):
    cfg = ar.RECOVERY_PROFILES[platform]
    assert cfg["login_url"].startswith("https://") and cfg["auth_cookies"]


@pytest.mark.parametrize("platform", ["douyin", "x", "instagram", "facebook"])
def test_registered_worker_binding_attaches_background_worker(platform, monkeypatch):
    import lumenis.adapters.human_browser as hb
    monkeypatch.setattr(hb, "registered_browser_worker_spec",
                        lambda p, **k: {"port": 9300, "profile": f"/p/{p}"})
    cfg, err = ar._resolve_recovery_profile(platform)
    assert err == "" and cfg["cdp_url"] == "http://127.0.0.1:9300"


def test_resume_runs_after_recovery_and_only_once(monkeypatch):
    calls = []
    ar.register_resume("x", lambda: calls.append("resumed") or "ok")
    out = ar._resume_pending("x")
    assert calls == ["resumed"] and out[0]["ok"]
    assert ar._resume_pending("x") == []


def test_resume_failure_is_reported():
    def boom():
        raise RuntimeError("x")
    ar.register_resume("facebook", boom)
    assert ar._resume_pending("facebook") == [{"ok": False, "error": "RuntimeError"}]
