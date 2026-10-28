# -*- coding: utf-8 -*-
"""通用主体模块与香港 Cookie 绑定的隔离验收。"""
import sqlite3
import sys
from copy import deepcopy
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
        add_subject({"domain_id": "CTH", "subject_type": "company", "name_en": "Only English"})


@pytest.mark.parametrize(
    ("domain_id", "subject_type"),
    [
        ("CTH", "brand"),
        ("CTH", "品牌主体"),
        ("BMP", "company"),
        ("ZBMP", "商业主体"),
    ],
)
def test_subject_registry_rejects_cross_domain_subject_types_before_database_open(
    tmp_path, monkeypatch, domain_id, subject_type
):
    import subject_registry

    db_path = tmp_path / "cross-pair-must-not-open.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))

    def unexpected_database_open():
        raise AssertionError("invalid domain/type pair reached database open")

    monkeypatch.setattr(subject_registry, "_db_ready", unexpected_database_open)
    with pytest.raises(
        subject_registry.SubjectValidationError,
        match="domain_id 与 subject_type",
    ):
        subject_registry.add_subject({
            "domain_id": domain_id,
            "subject_type": subject_type,
            "name_en": "Invalid Cross Pair",
            "name_zh": "错误领域类型组合",
        })

    assert not db_path.exists()


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
    subject_registry_client, user_id, expected_domain, hidden_domain, monkeypatch
):
    monkeypatch.setenv("ACCOUNT_SYSTEM_ENABLED", "on")
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
    subject_registry_client, user_id, requested_domain, monkeypatch
):
    monkeypatch.setenv("ACCOUNT_SYSTEM_ENABLED", "on")
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
    subject_registry_client, role, monkeypatch
):
    monkeypatch.setenv("ACCOUNT_SYSTEM_ENABLED", "on")
    client, current = subject_registry_client
    user_id = 4 if role == "owner" else 5
    current["user"] = {"id": user_id, "role": role}

    response = client.get("/api/settings/subjects")

    assert response.status_code == 200
    body = response.get_json()
    assert {domain["id"] for domain in body["domains"]} == {"CTH", "BMP"}
    assert {subject["domain_id"] for subject in body["subjects"]} == {"CTH", "BMP"}


def test_preloop_subject_registry_readable_without_account(subject_registry_client, monkeypatch):
    monkeypatch.setenv("ACCOUNT_SYSTEM_ENABLED", "off")
    client, current = subject_registry_client
    response = client.get("/api/settings/subjects")
    assert response.status_code == 200
    assert current["user"] is None


def test_subject_registry_route_requires_an_authenticated_account_session(
    subject_registry_client, monkeypatch,
):
    monkeypatch.setenv("ACCOUNT_SYSTEM_ENABLED", "on")
    client, _current = subject_registry_client

    response = client.get("/api/settings/subjects")

    assert response.status_code == 401
    assert response.get_json()["code"] == "AUTH_REQUIRED"


def test_explicit_local_workspace_lists_domains_without_creating_actor(subject_registry_client, monkeypatch):
    monkeypatch.setenv("ACCOUNT_SYSTEM_ENABLED", "on")
    client, current = subject_registry_client
    client.application.config["LUMENIS_OPEN_WORKSPACE"] = True
    response = client.get("/api/settings/subjects?domain_id=BMP")
    assert response.status_code == 200
    assert {item["domain_id"] for item in response.get_json()["subjects"]} == {"BMP"}
    assert current["user"] is None
    denied = client.get("/api/settings/subjects", environ_overrides={"REMOTE_ADDR": "192.0.2.1"})
    assert denied.status_code == 401
    client.application.config["LUMENIS_OPEN_WORKSPACE"] = False
    assert client.get("/api/settings/subjects").status_code == 401


def test_bmp_remove_persists_when_cn_evidence_unavailable_and_cancels_exact_scope(
    subject_registry_client, monkeypatch,
):
    import experience_runtime
    import lumenis.auth.service as auth_service
    import lumenis.shared.reporting.delivery_preferences as preferences_owner
    import subject_registry
    from lumenis.system.collector.adapters import secondary_collection
    from lumenis.system.security import permission

    monkeypatch.setenv("ACCOUNT_SYSTEM_ENABLED", "on")
    client, current = subject_registry_client
    current["user"] = {"id": 2, "role": "user"}
    monkeypatch.setattr(auth_service, "get_current_user", lambda **kwargs: current["user"])
    monkeypatch.setattr(permission, "local_workspace_read_allowed", lambda _module: False)
    monkeypatch.setattr(experience_runtime, "_content_source_same_origin", lambda: True)

    brand = subject_registry.list_subjects("BMP")[0]
    preference_state = {
        "persisted": False,
        "artifact_ref": None,
        "version": 0,
        "draft_digest": None,
        "preferences": {"subject_directory": {
            "mode": "EVIDENCED_CN", "subject_ids": [], "removed_subject_ids": [],
        }},
    }
    saved_call = {}

    def read_preferences(*, actor, scope):
        saved_call["read_actor"] = actor
        saved_call["read_scope"] = scope
        return {
            "preferences": deepcopy(preference_state["preferences"]),
            "persisted": preference_state["persisted"],
            "artifact_ref": preference_state["artifact_ref"],
            "version": preference_state["version"],
            "draft_digest": preference_state["draft_digest"],
        }

    def save_preferences(value, *, actor, scope, request_id,
                         previous_artifact_id=None, expected_draft_digest=None):
        saved_call.update(actor=actor, scope=scope, request_id=request_id)
        preference_state.update(
            persisted=True, artifact_ref="ART-0123456789abcdef", version=1,
            draft_digest="a" * 64, preferences=deepcopy(value),
        )
        return {"replayed": False,
                "artifact": {"artifact_id": preference_state["artifact_ref"]},
                "document": {"version": 1}}

    monkeypatch.setattr(preferences_owner, "read_preferences", read_preferences)
    monkeypatch.setattr(preferences_owner, "save_preferences", save_preferences)

    def missing_cn_evidence(*_args, **_kwargs):
        raise RuntimeError("isolated missing evidence")

    monkeypatch.setattr(subject_registry, "_country_subject_projection", missing_cn_evidence)
    cancellation = {"state": "CANCELLED", "matched": 1, "cancelled": 1,
                    "cancellation_pending": 0, "already_terminal": 0, "failed": 0,
                    "network_attempted": False}
    cancel_call = {}

    def cancel_requests(*, actor, scope):
        cancel_call.update(actor=actor, scope=scope)
        return cancellation

    monkeypatch.setattr(secondary_collection, "cancel_subject_collection_requests", cancel_requests)

    response = client.post("/api/settings/subjects/working-set", json={
        "domain_id": "BMP", "action": "remove", "subject_id": brand["subject_id"],
        "request_id": "0" * 32,
    })

    assert response.status_code == 200
    body = response.get_json()
    assert body["preference_save"]["persisted"] is True
    assert body["working_set"]["state"] == "EVIDENCE_UNAVAILABLE"
    assert brand["subject_id"] in body["working_set"]["removed_subject_ids"]
    assert body["task_cancellation"] == cancellation
    assert saved_call["actor"]["id"] == 2
    assert saved_call["scope"] == {
        "domain_id": "zbmp", "subject_id": None,
        "brand_focus_id": None, "global_scope": True,
    }
    assert cancel_call == {
        "actor": {"id": 2, "role": "user"},
        "scope": {"domain_id": "bmp", "subject_id": brand["subject_id"],
                  "brand_focus_id": brand["brand_focus_id"], "global_scope": False},
    }


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
