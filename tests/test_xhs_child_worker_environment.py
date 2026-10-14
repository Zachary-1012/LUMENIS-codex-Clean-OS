"""Isolated caller contract for the registered RedNote child worker."""
import sys


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
