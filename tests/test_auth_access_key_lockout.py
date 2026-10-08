"""Isolated regression coverage for the existing V4 login attempt owner."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import importlib
import sqlite3
from types import SimpleNamespace

from flask import Flask
import pytest


ACCESS_KEY_BUCKET = "__access_key__"
TEST_ACCESS_KEY = "synthetic-access-key-for-isolated-tests"
TEST_PASSWORD = "synthetic-password-for-isolated-tests"
TEST_OWNER = "f07-isolated-owner"
TEST_COOKIE = "f07-test-session"
TEST_IP_A = "198.51.100.17"
TEST_IP_B = "198.51.100.29"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class FixedClock:
    def __init__(self):
        self.current = datetime(2026, 10, 8, 10, 0, 0)

    def timestamp(self):
        return self.current.strftime(TIME_FORMAT)


@pytest.fixture
def auth_runtime(tmp_path, monkeypatch):
    """Bind only the auth owner to a fresh disposable SQLite file."""
    models = importlib.import_module("lumenis.auth.models")
    security = importlib.import_module("lumenis.auth.security")
    service = importlib.import_module("lumenis.auth.service")
    route_module = importlib.import_module("lumenis.blueprint")

    synthetic_config = {
        "bcrypt_rounds": 1,
        "max_login_attempts": 3,
        "lockout_minutes": 2,
        "token_expire_hours": 1,
        "session_cookie_name": TEST_COOKIE,
        "master_access_key": TEST_ACCESS_KEY,
    }
    monkeypatch.setattr(models, "get_db", lambda: None)
    monkeypatch.setattr(service, "AUTH_CONFIG", synthetic_config)
    monkeypatch.setattr(security, "AUTH_CONFIG", synthetic_config)
    monkeypatch.setattr(route_module, "AUTH_CONFIG", synthetic_config)
    monkeypatch.setattr(service, "ensure_initialized", lambda: None)
    monkeypatch.setattr(route_module, "log_audit", lambda *args, **kwargs: None)

    database_path = tmp_path / "auth-f07-isolated.sqlite3"

    def connect_test_database():
        connection = sqlite3.connect(
            str(database_path), timeout=20, check_same_thread=False
        )
        connection.row_factory = sqlite3.Row
        return connection

    monkeypatch.setattr(service, "get_db", connect_test_database)
    monkeypatch.setattr(security, "get_db", connect_test_database)

    setup = connect_test_database()
    try:
        setup.executescript(models.V4_TABLES_SQL)
        setup.execute(
            """INSERT INTO v4_users
               (username, password_hash, role, status, display_name)
               VALUES (?, ?, 'owner', 'active', 'Isolated test owner')""",
            (TEST_OWNER, security.hash_password(TEST_PASSWORD)),
        )
        setup.commit()
    finally:
        setup.close()

    clock = FixedClock()
    monkeypatch.setattr(security, "_local_timestamp", clock.timestamp)

    app = Flask("f07-isolated-auth-tests")
    app.config["TESTING"] = True
    app.register_blueprint(route_module.create_v4_blueprint())
    client = app.test_client()

    yield SimpleNamespace(
        app=app,
        client=client,
        clock=clock,
        config=synthetic_config,
        database_path=database_path,
        security=security,
        service=service,
    )


def _post(client, path, body, ip):
    return client.post(
        path,
        json=body,
        environ_overrides={"REMOTE_ADDR": ip},
    )


def _read_rows(database_path, sql, parameters=()):
    connection = sqlite3.connect(str(database_path), timeout=20)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(sql, parameters).fetchall()
    finally:
        connection.close()


def _has_expected_session_cookie(response):
    prefix = f"{TEST_COOKIE}="
    return any(
        header.startswith(prefix)
        and "HttpOnly" in header
        and "SameSite=Lax" in header
        for header in response.headers.getlist("Set-Cookie")
    )


def _has_session_cookie(response):
    prefix = f"{TEST_COOKIE}="
    return any(
        header.startswith(prefix)
        for header in response.headers.getlist("Set-Cookie")
    )


def test_access_key_lockout_is_per_ip_and_success_resets_only_its_bucket(auth_runtime):
    runtime = auth_runtime
    attempts = runtime.config["max_login_attempts"]

    for _ in range(attempts):
        response = _post(
            runtime.client,
            "/v4/auth/login-by-key",
            {"access_key": "synthetic-wrong-key"},
            TEST_IP_A,
        )
        assert response.get_json()["success"] is False
        assert not _has_session_cookie(response)

    check_a = runtime.security.check_login_attempts(ACCESS_KEY_BUCKET, TEST_IP_A)
    assert check_a["allowed"] is False
    original_lock_until = check_a["locked_until"]
    before_locked_request = len(
        _read_rows(
            runtime.database_path,
            "SELECT id FROM v4_login_attempts WHERE username=? AND ip=? AND success=0",
            (ACCESS_KEY_BUCKET, TEST_IP_A),
        )
    )

    locked_response = _post(
        runtime.client,
        "/v4/auth/login-by-key",
        {"access_key": "synthetic-wrong-key"},
        TEST_IP_A,
    )
    assert locked_response.get_json()["success"] is False
    assert not _has_session_cookie(locked_response)
    after_locked_request = len(
        _read_rows(
            runtime.database_path,
            "SELECT id FROM v4_login_attempts WHERE username=? AND ip=? AND success=0",
            (ACCESS_KEY_BUCKET, TEST_IP_A),
        )
    )
    check_a_after = runtime.security.check_login_attempts(ACCESS_KEY_BUCKET, TEST_IP_A)
    assert after_locked_request == before_locked_request
    assert check_a_after["locked_until"] == original_lock_until

    first_b_failure = _post(
        runtime.client,
        "/v4/auth/login-by-key",
        {"access_key": "synthetic-wrong-key"},
        TEST_IP_B,
    )
    assert first_b_failure.get_json()["success"] is False
    success_b = _post(
        runtime.client,
        "/v4/auth/login-by-key",
        {"access_key": TEST_ACCESS_KEY},
        TEST_IP_B,
    )
    payload = success_b.get_json()
    assert payload["success"] is True
    assert payload["login_type"] == "access_key"
    assert payload["user"]["username"] == TEST_OWNER
    assert _has_expected_session_cookie(success_b)

    owner = _read_rows(
        runtime.database_path,
        "SELECT id, failed_attempts, locked_until FROM v4_users WHERE username=?",
        (TEST_OWNER,),
    )[0]
    assert owner["failed_attempts"] == 0
    assert owner["locked_until"] is None
    assert not _read_rows(
        runtime.database_path,
        "SELECT id FROM v4_users WHERE username=?",
        (ACCESS_KEY_BUCKET,),
    )

    session = _read_rows(
        runtime.database_path,
        "SELECT user_id FROM v4_sessions ORDER BY id DESC LIMIT 1",
    )[0]
    assert session["user_id"] == owner["id"]
    assert runtime.security.check_login_attempts(ACCESS_KEY_BUCKET, TEST_IP_B)["remaining"] == attempts
    assert runtime.security.check_login_attempts(ACCESS_KEY_BUCKET, TEST_IP_A)["allowed"] is False

    audit_rows_b = _read_rows(
        runtime.database_path,
        """SELECT success FROM v4_login_attempts
           WHERE username=? AND ip=? ORDER BY id""",
        (ACCESS_KEY_BUCKET, TEST_IP_B),
    )
    assert [row["success"] for row in audit_rows_b] == [0, 1]


def test_access_key_missing_ip_uses_unknown_bucket_and_cooldown_expires(auth_runtime):
    runtime = auth_runtime
    attempts = runtime.config["max_login_attempts"]

    for index in range(attempts):
        result = runtime.service.login_by_key(
            "synthetic-wrong-key",
            ip=None if index % 2 == 0 else "   ",
        )
        assert result["success"] is False

    check = runtime.security.check_login_attempts(ACCESS_KEY_BUCKET, "")
    assert check["allowed"] is False
    assert check["locked_until"] == (
        runtime.clock.current + timedelta(minutes=runtime.config["lockout_minutes"])
    ).strftime(TIME_FORMAT)

    count_before_expiry = len(
        _read_rows(
            runtime.database_path,
            "SELECT id FROM v4_login_attempts WHERE username=? AND ip='unknown'",
            (ACCESS_KEY_BUCKET,),
        )
    )
    runtime.clock.current += timedelta(minutes=runtime.config["lockout_minutes"])
    after_cooldown = runtime.security.check_login_attempts(ACCESS_KEY_BUCKET, None)
    assert after_cooldown["allowed"] is True
    assert after_cooldown["remaining"] == attempts
    count_after_expiry = len(
        _read_rows(
            runtime.database_path,
            "SELECT id FROM v4_login_attempts WHERE username=? AND ip='unknown'",
            (ACCESS_KEY_BUCKET,),
        )
    )
    assert count_after_expiry == count_before_expiry

    next_failure = runtime.service.login_by_key("synthetic-wrong-key", ip="")
    assert next_failure["success"] is False
    assert next_failure["remaining"] == attempts - 1


def test_concurrent_access_key_failures_stop_at_the_configured_limit(auth_runtime):
    runtime = auth_runtime
    attempts = runtime.config["max_login_attempts"]

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda _: runtime.service.login_by_key(
                    "synthetic-wrong-key", ip=TEST_IP_A
                ),
                range(attempts + 5),
            )
        )

    assert all(result["success"] is False for result in results)
    failures = _read_rows(
        runtime.database_path,
        """SELECT id FROM v4_login_attempts
           WHERE username=? AND ip=? AND success=0""",
        (ACCESS_KEY_BUCKET, TEST_IP_A),
    )
    assert len(failures) == attempts
    assert not _read_rows(runtime.database_path, "SELECT id FROM v4_sessions")
    assert runtime.security.check_login_attempts(ACCESS_KEY_BUCKET, TEST_IP_A)["allowed"] is False


def test_password_lockout_cooldown_resets_and_key_failures_do_not_pollute_owner(auth_runtime):
    runtime = auth_runtime
    attempts = runtime.config["max_login_attempts"]
    key_failure = runtime.service.login_by_key("synthetic-wrong-key", ip=TEST_IP_A)
    assert key_failure["success"] is False

    owner_before_password = _read_rows(
        runtime.database_path,
        "SELECT failed_attempts, locked_until FROM v4_users WHERE username=?",
        (TEST_OWNER,),
    )[0]
    assert owner_before_password["failed_attempts"] == 0
    assert owner_before_password["locked_until"] is None

    for _ in range(attempts):
        response = _post(
            runtime.client,
            "/v4/auth/login",
            {"username": TEST_OWNER, "password": "synthetic-wrong-password"},
            TEST_IP_A,
        )
        assert response.get_json()["success"] is False

    owner_locked = _read_rows(
        runtime.database_path,
        "SELECT failed_attempts, locked_until FROM v4_users WHERE username=?",
        (TEST_OWNER,),
    )[0]
    assert owner_locked["failed_attempts"] == attempts
    locked_until = owner_locked["locked_until"]

    attempts_before_locked_request = len(
        _read_rows(
            runtime.database_path,
            "SELECT id FROM v4_login_attempts WHERE username=?",
            (TEST_OWNER,),
        )
    )
    locked_response = _post(
        runtime.client,
        "/v4/auth/login",
        {"username": TEST_OWNER, "password": TEST_PASSWORD},
        TEST_IP_A,
    )
    assert locked_response.get_json()["success"] is False
    assert not _has_session_cookie(locked_response)
    assert len(
        _read_rows(
            runtime.database_path,
            "SELECT id FROM v4_login_attempts WHERE username=?",
            (TEST_OWNER,),
        )
    ) == attempts_before_locked_request
    assert _read_rows(
        runtime.database_path,
        "SELECT locked_until FROM v4_users WHERE username=?",
        (TEST_OWNER,),
    )[0]["locked_until"] == locked_until

    runtime.clock.current = datetime.strptime(locked_until, TIME_FORMAT)
    success = _post(
        runtime.client,
        "/v4/auth/login",
        {"username": TEST_OWNER, "password": TEST_PASSWORD},
        TEST_IP_A,
    )
    assert success.get_json()["success"] is True
    assert _has_expected_session_cookie(success)
    owner_after_success = _read_rows(
        runtime.database_path,
        "SELECT failed_attempts, locked_until FROM v4_users WHERE username=?",
        (TEST_OWNER,),
    )[0]
    assert owner_after_success["failed_attempts"] == 0
    assert owner_after_success["locked_until"] is None
