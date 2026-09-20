# -*- coding: utf-8 -*-
"""通用主体模块与香港 Cookie 绑定的隔离验收。"""
import json
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def test_subject_registry_supports_both_domains_and_open_industry(tmp_path, monkeypatch):
    db_path = tmp_path / "subjects.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    from subject_registry import add_subject, list_subjects

    cth, created = add_subject({
        "domain_id": "cth",
        "subject_type": "company",
        "name_en": "North Star Labs",
        "name_zh": "北辰实验室",
        "industry": "工业软件",
        "keywords": ["North Star", "北辰"],
    })
    assert created is True
    assert cth["domain_id"] == "CTH"
    assert cth["subject_type"] == "company"
    assert cth["industry"] == "工业软件"
    assert cth["keywords"] == ["North Star", "北辰"]

    bmp, created = add_subject({
        "domain_id": "zbmp",
        "subject_type": "品牌主体",
        "name_en": "North Star Labs",
        "name_zh": "北辰实验室",
        "industry": "",
    })
    assert created is True
    assert bmp["domain_id"] == "BMP"
    assert bmp["subject_type"] == "brand"
    assert {x["domain_id"] for x in list_subjects()} == {"CTH", "BMP"}

    duplicate, created = add_subject({
        "domain_id": "CTH",
        "subject_type": "company",
        "name_en": " north   star labs ",
        "name_zh": "北辰实验室",
    })
    assert created is False
    assert duplicate["subject_id"] == cth["subject_id"]


def test_subject_registry_requires_bilingual_names(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "subjects.db"))
    from subject_registry import SubjectValidationError, add_subject

    with pytest.raises(SubjectValidationError, match="name_en 与 name_zh"):
        add_subject({"domain_id": "CTH", "subject_type": "brand", "name_en": "Only English"})


@pytest.fixture
def subject_registry_client(tmp_path, monkeypatch):
    """Run the real route and account product matrix against an isolated DB."""
    import account.authorization as authorization
    import database
    import lumenis.auth.service as auth_service
    from flask import Flask
    import subject_registry

    db_path = tmp_path / "subject-registry-routes.sqlite3"

    def connect_test_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def database_test_context():
        conn = connect_test_db()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    with connect_test_db() as conn:
        conn.executescript(
            """
            CREATE TABLE v4_users (
                id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE v4_member_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                module TEXT NOT NULL,
                action TEXT NOT NULL
            );
            INSERT INTO v4_users (id, role, status) VALUES
                (1, 'user', 'active'),
                (2, 'user', 'active'),
                (3, 'user', 'active'),
                (4, 'owner', 'active'),
                (5, 'admin', 'active');
            INSERT INTO v4_member_authorizations
                (user_id, product_id, module, action) VALUES
                (1, 'CTH', 'subject_registry', 'read'),
                (2, 'ZBMP', 'subject_registry', 'read');
            """
        )

    monkeypatch.setattr(authorization, "get_db", connect_test_db)
    monkeypatch.setattr(database, "get_db", database_test_context)
    current = {"user": None}
    monkeypatch.setattr(auth_service, "get_current_user", lambda: current["user"])

    subject_registry.add_subject({
        "domain_id": "CTH", "subject_type": "company",
        "name_en": "North Star Operations", "name_zh": "北辰运营",
    })
    subject_registry.add_subject({
        "domain_id": "BMP", "subject_type": "brand",
        "name_en": "North Star Brand", "name_zh": "北辰品牌",
    })

    app = Flask(__name__)
    app.register_blueprint(subject_registry.subject_registry_bp)
    return app.test_client(), current


@pytest.mark.parametrize(
    ("user_id", "expected_domain", "hidden_domain"),
    [(1, "CTH", "BMP"), (2, "BMP", "CTH")],
)
def test_subject_registry_route_limits_implicit_listing_to_authorized_domain(
    subject_registry_client, user_id, expected_domain, hidden_domain
):
    client, current = subject_registry_client
    current["user"] = {"id": user_id, "role": "user"}

    response = client.get("/api/settings/subjects")

    assert response.status_code == 200
    body = response.get_json()
    assert [domain["id"] for domain in body["domains"]] == [expected_domain]
    assert {subject["domain_id"] for subject in body["subjects"]} == {expected_domain}
    assert all(subject["domain_id"] != hidden_domain for subject in body["subjects"])

    explicit = client.get(f"/api/settings/subjects?domain_id={expected_domain}")
    assert explicit.status_code == 200
    assert {subject["domain_id"] for subject in explicit.get_json()["subjects"]} == {
        expected_domain
    }


@pytest.mark.parametrize(
    ("user_id", "requested_domain"),
    [(1, "BMP"), (2, "CTH"), (3, "CTH"), (3, None)],
)
def test_subject_registry_route_denies_unapproved_domain(
    subject_registry_client, user_id, requested_domain
):
    client, current = subject_registry_client
    current["user"] = {"id": user_id, "role": "user"}

    url = (
        f"/api/settings/subjects?domain_id={requested_domain}"
        if requested_domain
        else "/api/settings/subjects"
    )
    response = client.get(url)

    assert response.status_code == 403
    assert response.get_json()["code"] == "SUBJECT_SCOPE_DENIED"


@pytest.mark.parametrize("role", ["owner", "admin"])
def test_subject_registry_route_owner_and_admin_can_read_both_domains(
    subject_registry_client, role
):
    client, current = subject_registry_client
    user_id = 4 if role == "owner" else 5
    current["user"] = {"id": user_id, "role": role}

    response = client.get("/api/settings/subjects")

    assert response.status_code == 200
    body = response.get_json()
    assert {domain["id"] for domain in body["domains"]} == {"CTH", "BMP"}
    assert {subject["domain_id"] for subject in body["subjects"]} == {"CTH", "BMP"}


def test_subject_registry_route_requires_an_authenticated_account_session(
    subject_registry_client,
):
    client, _current = subject_registry_client

    response = client.get("/api/settings/subjects")

    assert response.status_code == 401
    assert response.get_json()["code"] == "AUTH_REQUIRED"


def test_hk_cookie_apply_targets_hk_profile_and_rejects_cn(tmp_path, monkeypatch):
    # This assertion exercises the cookie route's file/identity boundary, not
    # the application's full database migration path. The pytest database is
    # deliberately empty when no seed snapshot is configured, so bypass only
    # this unrelated startup migration before importing the large Flask app.
    from lumenis.shared.database import migrations

    monkeypatch.setattr(migrations, "migrate", lambda: True)
    monkeypatch.setattr(migrations, "_migrate_add_publish_datetime_index", lambda: None)
    import app as app_module
    import xhs_cookie_bridge as bridge

    runtime_data = tmp_path / "runtime-data"
    hk_cookie = runtime_data / "private" / "xhs_cookie_retinaut.txt"
    cn_cookie = runtime_data / "private" / "xhs_cookie_header.txt"
    monkeypatch.setattr(bridge, "DATA_DIR", str(runtime_data))
    monkeypatch.setitem(bridge.ACCOUNT_PROFILES, bridge.DEFAULT_COLLECTION_ACCOUNT,
                        (str(hk_cookie), str(runtime_data / "profiles" / "hk")))

    payload = {
        "platform": "xhs",
        "account": bridge.DEFAULT_COLLECTION_ACCOUNT,
        "apply": True,
        "cookies": [{"name": "web_session", "value": "real-session-value", "domain": ".rednote.com"}],
    }
    with app_module.app.test_request_context("/api/cookies/import/raw", method="POST", json=payload):
        response = app_module.api_cookies_import_raw()
    body = response.get_json()
    assert response.status_code == 200
    assert body["applied"] is True
    assert body["account"] == bridge.DEFAULT_COLLECTION_ACCOUNT
    assert body["secrets_returned"] is False
    assert hk_cookie.read_text(encoding="utf-8") == "web_session=real-session-value"
    assert not cn_cookie.exists()

    payload["account"] = bridge.XHS_CN_PRIMARY_NAME
    with app_module.app.test_request_context("/api/cookies/import/raw", method="POST", json=payload):
        response = app_module.api_cookies_import_raw()
    response_body, response_status = response
    assert response_status == 403
    assert response_body.get_json()["code"] == "MAINLAND_COLLECTION_DISABLED"


def test_active_resident_plan_and_orchestrator_are_hk_only():
    import scripts.start_resident_browsers as resident
    import xhs_cookie_bridge as bridge
    import xhs_p0_orchestrator as orchestrator

    plan_accounts = {account for account, _ in resident.RESIDENT_PLAN}
    assert plan_accounts == {bridge.DEFAULT_COLLECTION_ACCOUNT}
    assert bridge.XHS_CN_PRIMARY_NAME not in plan_accounts
    assert orchestrator.ALLOWED_IDENTITY_NAMES == (bridge.DEFAULT_COLLECTION_ACCOUNT,)
    assert orchestrator._identity_allowed(bridge.XHS_CN_PRIMARY_NAME) is False
    assert orchestrator._identity_allowed(bridge.DEFAULT_COLLECTION_ACCOUNT) is True
