"""Regression: TOTP removed, account routes still register, key list needs login,
workspace unlock never grants an owner session without login and is rate limited."""
import pytest


@pytest.fixture
def client():
    # Database isolation comes from tests/conftest.py (per-test disposable DB);
    # this module never selects or inherits a database path itself.
    import app as app_module
    from account.models import init_account_db
    init_account_db()
    return app_module.app.test_client(), app_module.app


def test_account_routes_register_and_totp_gone(client):
    c, app = client
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/api/system/account/profile" in rules
    assert not any("/totp" in r for r in rules)
    for path in ("status", "setup", "confirm", "verify", "reset"):
        method = "get" if path == "status" else "post"
        r = getattr(c, method)(f"/api/system/account/totp/{path}", json={"user_id": 1, "code": "123456"})
        # The global auth gate answers 401 before routing; logged-in callers get 404.
        assert r.status_code in (401, 404)
        assert "token" not in (r.get_json(silent=True) or {})


def test_api_keys_single_registration_and_login_required(client):
    c, app = client
    endpoints = [r.endpoint for r in app.url_map.iter_rules() if r.rule == "/api/v4/api-keys"]
    assert endpoints == ["account_compat.compat_api_keys_list"]
    assert c.get("/api/v4/api-keys").status_code == 401
    assert c.post("/api/v4/api-keys/generate", json={"label": "x"}).status_code == 401
    assert c.post("/api/v4/api-keys/revoke", json={"key_id": 1}).status_code == 401


def test_workspace_unlock_requires_login_and_never_sets_session(client):
    c, _ = client
    for _ in range(8):
        r = c.post("/v4/auth/workspace/unlock", json={"workspace": "ZBMP", "key": "guess"})
        assert r.status_code == 401
        assert "Set-Cookie" not in r.headers
        assert r.get_json()["success"] is False


def test_workspace_keys_list_is_owner_only(client):
    c, _ = client
    assert c.get("/v4/auth/workspace/keys").status_code in (401, 403)


def test_workspace_key_bucket_locks_after_max_failures(tmp_path, monkeypatch):
    import sqlite3
    from lumenis.auth import security
    db = tmp_path / "b.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE v4_login_attempts(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, ip TEXT, success INTEGER, created_at TEXT)")
    conn.execute("CREATE TABLE v4_users(username TEXT, failed_attempts INTEGER, locked_until TEXT)")
    monkeypatch.setitem(security.AUTH_CONFIG, "max_login_attempts", 3)
    for _ in range(3):
        assert security.check_login_attempts("__workspace_key__", "203.0.113.5", conn=conn)["allowed"]
        security.record_login_attempt("__workspace_key__", "203.0.113.5", False, conn=conn)
    assert security.check_login_attempts("__workspace_key__", "203.0.113.5", conn=conn)["allowed"] is False
    assert security.check_login_attempts("__workspace_key__", "203.0.113.6", conn=conn)["allowed"] is True


def test_reserved_looking_username_keeps_account_lockout():
    from lumenis.auth import security
    assert security._is_ip_bucket("__access_key__")
    assert security._is_ip_bucket("__workspace_key__")
    assert not security._is_ip_bucket("__alice__")


def test_account_init_retains_legacy_totp_rows():
    """TOTP removal must not silently destroy existing security data."""
    from account.models import get_db, init_account_db
    conn = get_db()
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS v4_totp_secrets (id INTEGER PRIMARY KEY, "
            "user_id INTEGER, secret TEXT, enabled INTEGER)"
        )
        conn.execute("INSERT INTO v4_totp_secrets(user_id, secret, enabled) VALUES (1, 'legacy', 1)")
        conn.commit()
    finally:
        conn.close()
    init_account_db()
    conn = get_db()
    try:
        assert conn.execute("SELECT COUNT(*) FROM v4_totp_secrets").fetchone()[0] >= 1
    finally:
        conn.close()


def test_reserved_bucket_usernames_cannot_become_accounts(monkeypatch):
    from lumenis.auth import security
    from account import service as account_service
    from account import models as account_models
    for name in ("__workspace_key__", "__access_key__", "__alice__"):
        assert security.is_reserved_username(name)
        assert account_service.create_member(name, "x" * 20, role="user")["success"] is False
    from lumenis.auth import service as auth_service
    assert auth_service.create_user("__workspace_key__", "x" * 20)["success"] is False
    monkeypatch.setenv("LUMENIS_BOOTSTRAP_OWNER_USERNAME", "__workspace_key__")
    monkeypatch.setenv("LUMENIS_BOOTSTRAP_OWNER_PASSWORD", "y" * 20)

    class _NoOwner:
        def execute(self, *a, **k):
            class _C:
                def fetchone(self_inner):
                    return {"cnt": 0}
            return _C()
    with pytest.raises(ValueError):
        account_models._ensure_owner_account(_NoOwner())


def test_owner_bearer_reaches_compat_key_routes_under_basic_auth(client, monkeypatch):
    import app as app_module
    c, _ = client
    monkeypatch.setattr(app_module, "_auth_enabled", lambda: True)
    from account import service as account_service
    monkeypatch.setattr(account_service, "get_current_user",
                        lambda *a, **k: {"id": 1, "username": "o", "role": "owner"})
    r = c.get("/api/v4/api-keys", headers={"Authorization": "Bearer synthetic"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
