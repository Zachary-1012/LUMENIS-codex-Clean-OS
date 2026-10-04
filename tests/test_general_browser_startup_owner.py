"""Production startup must use the same isolated browser as product sessions."""
import pytest

import browser_surface
from scripts import start_resident_browsers as launcher


@pytest.fixture(autouse=True)
def no_other_browser_access(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("resident launcher bypassed the product browser owner")
    monkeypatch.setattr(launcher, "launch_one", forbidden)
    monkeypatch.setattr(launcher.cdp_helper, "start_cdp_browser", forbidden)
    monkeypatch.setattr(launcher.cdp_helper, "system_default_cdp_browser", lambda: "chrome")


@pytest.mark.parametrize("action", ["started", "already_online"])
def test_launch_general_delegates_to_existing_verified_owner(monkeypatch, action):
    calls = []
    monkeypatch.setattr(browser_surface, "ensure_general_browser", lambda: calls.append("ensure") or {
        "ok": True, "online": True, "browser": "chrome", "action": action,
    })
    monkeypatch.setattr(launcher, "list_page_hosts", lambda port: calls.append(port) or ["about:blank"])
    row = launcher.launch_general()
    assert calls == ["ensure", 9224]
    assert row["online"] is True and row["action"] == action
    assert row["profile"] == browser_surface._general_profile_dir("chrome")
    assert row["home"] == "about:blank" and row["direct"] is False


@pytest.mark.parametrize("code", ["UNVERIFIED_BROWSER_SESSION", "UNSUPPORTED_DEFAULT_BROWSER", "BROWSER_START_UNVERIFIED"])
def test_launch_general_does_not_claim_open_port_or_failed_launch_is_online(monkeypatch, code):
    monkeypatch.setattr(browser_surface, "ensure_general_browser", lambda: {"ok": False, "online": False, "code": code})
    monkeypatch.setattr(launcher, "port_online", lambda port: True)
    monkeypatch.setattr(launcher, "list_page_hosts", lambda port: pytest.fail("unverified session inspected"))
    row = launcher.launch_general()
    assert row["online"] is False and row["action"] == f"failed: {code}"
    assert row["pages"] == []


@pytest.mark.parametrize("verified", [True, False])
def test_status_is_read_only_and_uses_owner_verification(monkeypatch, verified):
    monkeypatch.setattr(browser_surface, "ensure_general_browser", lambda: pytest.fail("status launched browser"))
    monkeypatch.setattr(browser_surface, "general_browser_online", lambda: verified)
    monkeypatch.setattr(launcher, "list_page_hosts", lambda port: ["about:blank"] if verified else pytest.fail("unverified session inspected"))
    row = launcher.launch_general(status_only=True)
    assert row["online"] is verified
    assert row["action"] == ("already_online" if verified else "offline_or_unverified")
