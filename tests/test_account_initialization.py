"""Account initialization requires injection and preserves existing owners."""
import importlib
import secrets
import sqlite3

import pytest

from account import models
from account.security import verify_password


@pytest.fixture
def connection(monkeypatch):
    monkeypatch.delenv("LUMENIS_BOOTSTRAP_OWNER_USERNAME", raising=False)
    monkeypatch.delenv("LUMENIS_BOOTSTRAP_OWNER_PASSWORD", raising=False)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(models.BASE_TABLES_SQL)
    yield conn
    conn.close()


@pytest.mark.parametrize("module_name", ["account.models", "lumenis.auth.models"])
def test_unconfigured_initialization_never_creates_default_credentials(connection, module_name):
    module = importlib.import_module(module_name)
    module._ensure_owner_account(connection)
    module._ensure_default_security_questions(connection)
    assert connection.execute("SELECT COUNT(*) FROM v4_users").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM v4_security_questions").fetchone()[0] == 0


def test_configured_owner_is_hashed_and_existing_owner_is_not_rotated(connection, monkeypatch):
    password = secrets.token_urlsafe(32)
    monkeypatch.setenv("LUMENIS_BOOTSTRAP_OWNER_USERNAME", "isolated-owner")
    monkeypatch.setenv("LUMENIS_BOOTSTRAP_OWNER_PASSWORD", password)
    models._ensure_owner_account(connection)
    before = dict(connection.execute("SELECT * FROM v4_users").fetchone())
    assert before["username"] == "isolated-owner"
    assert before["password_hash"] != password
    assert verify_password(password, before["password_hash"])
    assert before["must_change_password"] == 1
    monkeypatch.setenv("LUMENIS_BOOTSTRAP_OWNER_PASSWORD", secrets.token_urlsafe(32))
    models._ensure_owner_account(connection)
    assert dict(connection.execute("SELECT * FROM v4_users").fetchone()) == before


@pytest.mark.parametrize("username,password", [("operator", ""), ("", "a" * 24), ("operator", "short")])
def test_partial_or_weak_bootstrap_fails_without_account(connection, monkeypatch, username, password):
    monkeypatch.setenv("LUMENIS_BOOTSTRAP_OWNER_USERNAME", username)
    monkeypatch.setenv("LUMENIS_BOOTSTRAP_OWNER_PASSWORD", password)
    with pytest.raises(ValueError, match="explicit username"):
        models._ensure_owner_account(connection)
    assert connection.execute("SELECT COUNT(*) FROM v4_users").fetchone()[0] == 0


def test_legacy_configuration_has_no_default_master_key(monkeypatch):
    monkeypatch.delenv("V4_ACCESS_KEY", raising=False)
    from lumenis import config
    from account import security
    old_config = dict(config.AUTH_CONFIG)
    old_security = dict(security.AUTH_CONFIG)
    try:
        importlib.reload(config)
        importlib.reload(security)
        assert config.AUTH_CONFIG["master_access_key"] == ""
        assert security.AUTH_CONFIG["master_access_key"] == ""
        assert config.DEFAULT_SECURITY_QUESTIONS == []
    finally:
        config.AUTH_CONFIG.update(old_config)
        security.AUTH_CONFIG.update(old_security)


def test_compat_auth_initializer_upgrades_legacy_user_columns_before_explicit_owner(
    tmp_path, monkeypatch
):
    from lumenis.auth import models as compat_models

    legacy_db = tmp_path / "legacy-auth.sqlite"
    connection = sqlite3.connect(legacy_db)
    connection.execute(
        "CREATE TABLE v4_users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, "
        "password_hash TEXT NOT NULL, role TEXT NOT NULL, display_name TEXT, "
        "status TEXT DEFAULT 'active')"
    )
    connection.commit()
    connection.close()

    def get_legacy_db():
        opened = sqlite3.connect(legacy_db)
        opened.row_factory = sqlite3.Row
        return opened

    monkeypatch.setattr(compat_models, "get_db", get_legacy_db)
    monkeypatch.setenv("LUMENIS_BOOTSTRAP_OWNER_USERNAME", "isolated-owner")
    password = secrets.token_urlsafe(32)
    monkeypatch.setenv("LUMENIS_BOOTSTRAP_OWNER_PASSWORD", password)
    compat_models.init_auth_db()

    connection = get_legacy_db()
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(v4_users)")}
        assert "must_change_password" in columns
        owner = connection.execute("SELECT * FROM v4_users WHERE role='owner'").fetchone()
        assert owner["username"] == "isolated-owner"
        assert owner["must_change_password"] == 1
        assert verify_password(password, owner["password_hash"])
        assert connection.execute("SELECT COUNT(*) FROM v4_security_questions").fetchone()[0] == 0
    finally:
        connection.close()
