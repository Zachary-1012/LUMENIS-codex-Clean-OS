import json
import sqlite3

import pytest


@pytest.fixture
def isolated_scope_database(tmp_path, monkeypatch):
    path = tmp_path / "permission-exact-scope.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"scope-fixture": "public-test-only-scope-fixture-not-production"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "scope-fixture")

    import subject_registry
    from lumenis.shared.evidence.store import ensure_evidence_schema

    with sqlite3.connect(path) as conn:
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
                action TEXT NOT NULL,
                data_scope TEXT,
                time_range TEXT,
                granted_by INTEGER,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(user_id, product_id, module, action)
            );
            INSERT INTO v4_users (id, role, status) VALUES
                (1, 'user', 'active'),
                (2, 'admin', 'active'),
                (3, 'owner', 'inactive'),
                (4, 'user', 'active');
            """
        )
        subject_registry.ensure_schema(conn)
        rows = [
            (
                "SUBJ-CTH-A", None, "CTH", "company",
                "North Center", "北区中心", "north center", "北区中心",
                "retail", "[]", "configured", "2026-09-24", "2026-09-24",
            ),
            (
                "SUBJ-CTH-B", None, "CTH", "company",
                "South Center", "南区中心", "south center", "南区中心",
                "retail", "[]", "configured", "2026-09-24", "2026-09-24",
            ),
            (
                "SUBJ-BMP-A", "BRAND-BMP-A", "BMP", "brand",
                "North Brand", "北方品牌", "north brand", "北方品牌",
                "beauty", "[]", "configured", "2026-09-24", "2026-09-24",
            ),
        ]
        conn.executemany(
            """
            INSERT INTO lumenis_subject_registry (
                subject_id, brand_focus_id, domain_id, subject_type,
                name_en, name_zh, name_en_norm, name_zh_norm, industry,
                keywords_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        ensure_evidence_schema(conn)

    return path


def _grant(path, user_id, product_id, module, action, scope, *, time_range=None):
    if scope is None or isinstance(scope, str):
        data_scope = scope
    else:
        data_scope = json.dumps(scope)
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO v4_member_authorizations (
                user_id, product_id, module, action, data_scope, time_range
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, product_id, module, action, data_scope, time_range),
        )


def _check(actor, **overrides):
    from lumenis.system.security import PermissionGate, check_actor_scope_permission

    gate = overrides.pop("gate", None)
    args = {
        "domain_id": "CTH",
        "action": "read",
        "module": "evidence",
        "subject_id": "SUBJ-CTH-A",
    }
    args.update(overrides)
    return check_actor_scope_permission(
        actor,
        gate=gate if gate is not None else PermissionGate(),
        **args,
    )


def test_user_grant_is_bound_to_one_registered_subject_and_action(isolated_scope_database):
    from lumenis.system.security import PermissionGate

    _grant(
        isolated_scope_database, 1, "CTH", "evidence", "read",
        {"subject_ids": ["SUBJ-CTH-A"]},
    )
    gate = PermissionGate()
    allowed = _check({"id": 1, "role": "user"}, gate=gate)
    other_subject = _check(
        {"id": 1, "role": "user"}, subject_id="SUBJ-CTH-B"
    )
    wrong_action = _check(
        {"id": 1, "role": "user"}, action="write"
    )
    wrong_module = _check(
        {"id": 1, "role": "user"}, module="decision"
    )
    unknown_subject = _check(
        {"id": 1, "role": "user"}, subject_id="SUBJ-CTH-MISSING"
    )

    assert allowed.allowed is True
    assert allowed.actor_id == 1
    assert allowed.subject_id == "SUBJ-CTH-A"
    assert allowed.scope_action == "read"
    assert allowed.audit_id == allowed.scope_audit_id
    assert gate.get_audit_log(
        operation_type="resource_scope_read", result_filter="allowed"
    )[-1]["resource"] == "cth:SUBJ-CTH-A"
    assert other_subject.allowed is False
    assert wrong_action.allowed is False
    assert wrong_module.allowed is False
    assert unknown_subject.allowed is False
    assert unknown_subject.verification_state == "verified"


def test_bmp_grant_uses_brand_focus_id_not_subject_id(isolated_scope_database):
    _grant(
        isolated_scope_database, 1, "ZBMP", "evidence", "read",
        {"brand_focus_ids": ["BRAND-BMP-A"]},
    )

    allowed = _check(
        {"id": 1, "role": "user"},
        domain_id="BMP",
        subject_id=None,
        brand_focus_id="BRAND-BMP-A",
    )
    wrong_focus = _check(
        {"id": 1, "role": "user"},
        domain_id="BMP",
        subject_id=None,
        brand_focus_id="BRAND-BMP-OTHER",
    )
    cth_using_brand_focus = _check(
        {"id": 1, "role": "user"},
        domain_id="CTH",
        subject_id="SUBJ-CTH-A",
    )

    assert allowed.allowed is True
    assert allowed.brand_focus_id == "BRAND-BMP-A"
    assert wrong_focus.allowed is False
    assert wrong_focus.verification_state == "verified"
    assert cth_using_brand_focus.allowed is False


def test_global_access_requires_global_grant_or_database_owner_role(isolated_scope_database):
    _grant(
        isolated_scope_database, 1, "CTH", "evidence", "read",
        {"subject_ids": ["SUBJ-CTH-A"]},
    )
    _grant(
        isolated_scope_database, 4, "CTH", "evidence", "read",
        {"global": True},
    )

    scoped_member_global = _check(
        {"id": 1, "role": "user"},
        subject_id=None,
        global_scope=True,
    )
    explicit_global = _check(
        {"id": 4, "role": "user"},
        subject_id=None,
        global_scope=True,
    )
    explicit_global_to_subject = _check(
        {"id": 4, "role": "user"},
        subject_id="SUBJ-CTH-B",
    )
    admin_global = _check(
        {"id": 2, "role": "user"},
        subject_id=None,
        global_scope=True,
    )
    empty_scope = _check(
        {"id": 1, "role": "user"},
        subject_id="SUBJ-CTH-B",
    )

    assert scoped_member_global.allowed is False
    assert explicit_global.allowed is True
    assert explicit_global_to_subject.allowed is True
    assert admin_global.allowed is True
    assert empty_scope.allowed is False


@pytest.mark.parametrize(
    ("actor", "overrides"),
    [
        (None, {}),
        ({"id": True}, {}),
        ({"id": "1"}, {}),
        ({"id": 1}, {"domain_id": "unknown"}),
        ({"id": 1}, {"action": "delete"}),
        ({"id": 1}, {"module": "*"}),
        ({"id": 1}, {"subject_id": None}),
        ({"id": 1}, {"subject_id": "SUBJ-CTH-A", "brand_focus_id": "BRAND-BMP-A"}),
        ({"id": 1}, {"subject_id": " SUBJ-CTH-A"}),
        ({"id": 1}, {"subject_id": None, "global_scope": True, "brand_focus_id": "BRAND-BMP-A"}),
        ({"id": 1}, {"domain_id": "BMP", "subject_id": "SUBJ-BMP-A", "brand_focus_id": "BRAND-BMP-A"}),
    ],
)
def test_invalid_actor_domain_action_or_scope_fails_closed(
    isolated_scope_database, actor, overrides
):
    result = _check(actor, **overrides)
    assert result.allowed is False
    assert result.audit_id


@pytest.mark.parametrize(
    "data_scope",
    [
        None,
        "",
        "SUBJ-CTH-A",
        '{"subject_ids":["SUBJ-CTH-A"],"brand_focus_ids":["BRAND-BMP-A"]}',
        '{"subject_ids":["SUBJ-CTH-A"],"unexpected":true}',
        '{"global":"true"}',
        '{"subject_ids":[" SUBJ-CTH-A"]}',
    ],
)
def test_malformed_or_cross_domain_grants_never_authorize(isolated_scope_database, data_scope):
    _grant(
        isolated_scope_database, 1, "CTH", "evidence", "read", data_scope
    )
    result = _check({"id": 1, "role": "owner"})
    assert result.allowed is False


def test_database_role_is_authoritative_and_inactive_account_is_denied(isolated_scope_database):
    _grant(
        isolated_scope_database, 1, "CTH", "evidence", "read",
        {"subject_ids": ["SUBJ-CTH-A"]},
    )
    forged_owner = _check({"id": 1, "role": "owner"}, subject_id="SUBJ-CTH-B")
    inactive_owner = _check(
        {"id": 3, "role": "owner"}, subject_id="SUBJ-CTH-A"
    )
    database_admin = _check(
        {"id": 2, "role": "user"}, subject_id="SUBJ-CTH-A"
    )

    assert forged_owner.allowed is False
    assert inactive_owner.allowed is False
    assert database_admin.allowed is True
    assert database_admin.reason == "active account role has account-wide authority"


def test_time_restricted_grant_is_not_widened_without_a_time_contract(isolated_scope_database):
    _grant(
        isolated_scope_database, 1, "CTH", "evidence", "read",
        {"subject_ids": ["SUBJ-CTH-A"]},
        time_range='{"from":"2026-09-01","to":"2026-09-30"}',
    )
    result = _check({"id": 1, "role": "user"})
    assert result.allowed is False


def test_account_registry_and_audit_failures_return_unavailable(
    isolated_scope_database, monkeypatch
):
    from lumenis.system.security import PermissionGate
    from lumenis.system.security import permission as permission_module
    import subject_registry

    _grant(
        isolated_scope_database, 1, "CTH", "evidence", "read",
        {"subject_ids": ["SUBJ-CTH-A"]},
    )

    def unavailable(*_args, **_kwargs):
        raise OSError("isolated service failure")

    original_action_check = permission_module._actor_has_scope_action
    original_registry_list = subject_registry.list_subjects
    monkeypatch.setattr(permission_module, "_actor_has_scope_action", unavailable)
    account_failure = _check({"id": 1})
    assert account_failure.allowed is False
    assert account_failure.verification_state == "unavailable"

    monkeypatch.setattr(
        permission_module, "_actor_has_scope_action", original_action_check
    )
    monkeypatch.setattr(subject_registry, "list_subjects", unavailable)
    registry_failure = _check({"id": 1})
    assert registry_failure.allowed is False
    assert registry_failure.verification_state == "unavailable"

    monkeypatch.setattr(subject_registry, "list_subjects", original_registry_list)

    class BrokenAudit(PermissionGate):
        def _write_audit(self, **_kwargs):
            raise OSError("isolated audit failure")

    audit_failure = _check({"id": 1}, gate=BrokenAudit())
    assert audit_failure.allowed is False
    assert audit_failure.audit_id is None
    assert audit_failure.verification_state == "unavailable"

    monkeypatch.setattr(permission_module, "get_permission_gate", unavailable)
    gate_lookup_failure = permission_module.check_actor_scope_permission(
        {"id": 1},
        domain_id="CTH",
        action="read",
        module="evidence",
        subject_id="SUBJ-CTH-A",
    )
    assert gate_lookup_failure.allowed is False
    assert gate_lookup_failure.audit_id is None
    assert gate_lookup_failure.verification_state == "unavailable"


def test_scope_result_keeps_permission_result_json_contract(isolated_scope_database):
    from lumenis.system.security import (
        ActorScopePermissionResult,
        PermissionResult,
    )

    _grant(
        isolated_scope_database, 1, "CTH", "evidence", "read",
        {"subject_ids": ["SUBJ-CTH-A"]},
    )
    result = _check({"id": 1, "role": "user"})
    legacy = PermissionResult(allowed=True, reason="legacy")
    scope_json = result.to_scope_dict()

    assert isinstance(result, ActorScopePermissionResult)
    assert isinstance(result, PermissionResult)
    assert result.to_dict().keys() == legacy.to_dict().keys()
    assert scope_json["actor_id"] == 1
    assert scope_json["subject_id"] == "SUBJ-CTH-A"
    assert scope_json["verification_state"] == "verified"



def _scoped_evidence_api_client(monkeypatch, actor):
    from flask import Flask
    import lumenis.auth.service as auth_service
    from lumenis.shared.evidence.api import register_evidence_api
    from lumenis.system.security import PermissionGate
    from lumenis.system.security import permission as permission_module

    monkeypatch.setattr(auth_service, "get_current_user", lambda: actor)
    monkeypatch.setattr(permission_module, "get_permission_gate", lambda: PermissionGate())
    app = Flask(__name__)
    register_evidence_api(app)
    return app.test_client()


def _focus_headers(domain, subject):
    return {
        "X-Lumenis-Context-Mode": "FOCUS",
        "X-Domain-Id": domain,
        "X-Subject-ID": subject,
    }


def test_evidence_api_exact_subject_paging_stats_timeline_and_hidden_detail(
    isolated_scope_database, monkeypatch
):
    from lumenis.shared.database import DatabaseRepository
    from lumenis.shared.evidence import store

    _grant(
        isolated_scope_database, 1, "CTH", "evidence", "read",
        {"subject_ids": ["SUBJ-CTH-A"]},
    )
    repository = DatabaseRepository(str(isolated_scope_database))
    monkeypatch.setattr(store, "get_repository", lambda: repository)
    store.init_evidence_store(str(isolated_scope_database))
    target_ids = [
        store.record_evidence(
            source="fixture", product="CTH", feature_id="API_BULK",
            result="PASS" if index else None, level="L4" if index else None,
            metric_value="PASS" if index else "unknown", account="cth-a",
            inputs={"index": index}, domain_id="cth", subject_id="SUBJ-CTH-A",
        )
        for index in range(205)
    ]
    health_id = store.record_evidence(
        source="health", product="CTH", feature_id="RESIDENT_HEALTH",
        result="PASS", account="cth-a", domain_id="cth", subject_id="SUBJ-CTH-A",
    )
    collection_id = store.record_evidence(
        source="collector", product="CTH", feature_id="XHS_COLLECT",
        result="PASS", account="cth-a", domain_id="cth", subject_id="SUBJ-CTH-A",
    )
    other_scope_id = store.record_evidence(
        source="fixture", product="CTH", feature_id="API_BULK",
        result="PASS", domain_id="cth", subject_id="SUBJ-CTH-B",
    )
    store.record_evidence(source="legacy", product="CTH", feature_id="API_BULK")
    client = _scoped_evidence_api_client(monkeypatch, {"id": 1, "role": "user"})
    headers = _focus_headers("CTH", "SUBJ-CTH-A")
    page = client.get("/api/evidence/list?feature_id=API_BULK&limit=10&offset=200", headers=headers)
    assert page.status_code == 200
    assert set(row["id"] for row in page.get_json()["records"]) == set(target_ids[:5])

    stats = client.get("/api/evidence/stats", headers=headers)
    assert stats.status_code == 200
    assert stats.get_json()["stats"]["total"] == 207
    assert stats.get_json()["stats"]["null_counts"] == {"result": 1, "level": 1}
    timeline = client.get("/api/evidence/timeline?limit=10", headers=headers)
    assert timeline.status_code == 200
    assert [row["id"] for row in timeline.get_json()["health"]] == [health_id]
    assert [row["id"] for row in timeline.get_json()["collection"]] == [collection_id]

    assert client.get(f"/api/evidence/{target_ids[0]}", headers=headers).status_code == 200
    assert client.get(f"/api/evidence/{other_scope_id}", headers=headers).status_code == 404
    denied = client.get(
        "/api/evidence/list", headers=_focus_headers("CTH", "SUBJ-CTH-B")
    )
    assert denied.status_code == 403

    failed_read = lambda **kwargs: (_ for _ in ()).throw(OSError("isolated read failure"))
    monkeypatch.setattr(store, "query_scoped_evidence", failed_read)
    unavailable = client.get("/api/evidence/stats", headers=headers)
    assert unavailable.status_code == 503
    assert unavailable.get_json()["code"] == "EVIDENCE_READ_UNAVAILABLE"


def test_evidence_api_resolves_bmp_subject_to_authorized_brand_focus(
    isolated_scope_database, monkeypatch
):
    from lumenis.shared.database import DatabaseRepository
    from lumenis.shared.evidence import store

    _grant(
        isolated_scope_database, 1, "ZBMP", "evidence", "read",
        {"brand_focus_ids": ["BRAND-BMP-A"]},
    )
    repository = DatabaseRepository(str(isolated_scope_database))
    monkeypatch.setattr(store, "get_repository", lambda: repository)
    store.init_evidence_store(str(isolated_scope_database))
    record_id = store.record_evidence(
        source="fixture", product="BMP", feature_id="BMP_READ",
        domain_id="bmp", brand_focus_id="BRAND-BMP-A",
    )
    client = _scoped_evidence_api_client(monkeypatch, {"id": 1, "role": "user"})
    response = client.get(
        "/api/evidence/list", headers=_focus_headers("BMP", "SUBJ-BMP-A")
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.get_json()["records"]] == [record_id]
    assert response.get_json()["scope"]["brand_focus_id"] == "BRAND-BMP-A"


def test_evidence_api_global_requires_grant_and_returns_only_global_rows(
    isolated_scope_database, monkeypatch
):
    from lumenis.shared.database import DatabaseRepository
    from lumenis.shared.evidence import store

    _grant(
        isolated_scope_database, 1, "CTH", "evidence", "read",
        {"global": True},
    )
    repository = DatabaseRepository(str(isolated_scope_database))
    monkeypatch.setattr(store, "get_repository", lambda: repository)
    store.init_evidence_store(str(isolated_scope_database))
    global_id = store.record_evidence(
        source="fixture", product="CTH", feature_id="GLOBAL_READ",
        domain_id="cth", global_scope=True,
    )
    store.record_evidence(
        source="fixture", product="CTH", feature_id="FOCUSED_READ",
        domain_id="cth", subject_id="SUBJ-CTH-A",
    )

    headers = {
        "X-Lumenis-Context-Mode": "GLOBAL_ALL",
        "X-Domain-Id": "CTH",
    }
    client = _scoped_evidence_api_client(monkeypatch, {"id": 1, "role": "user"})
    response = client.get("/api/evidence/list", headers=headers)
    assert response.status_code == 200
    assert [row["id"] for row in response.get_json()["records"]] == [global_id]
    assert response.get_json()["scope"]["evidence_scope"] == (
        "EXPLICIT_GLOBAL_MARKED_EVIDENCE_ONLY"
    )
    assert client.get(
        "/api/evidence/list", headers={**headers, "X-Subject-ID": "SUBJ-CTH-A"}
    ).status_code == 400
    assert client.get("/api/evidence/list").status_code == 400

    denied = _scoped_evidence_api_client(monkeypatch, {"id": 4, "role": "user"})
    assert denied.get("/api/evidence/list", headers=headers).status_code == 403
