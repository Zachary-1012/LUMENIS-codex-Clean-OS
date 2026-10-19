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


@pytest.mark.parametrize("status,allowed", [
    ("configured", True), ("active", True), ("inactive", False),
    ("disabled", False), ("deleted", False), ("archived", False),
    ("UNKNOWN", False),
])
@pytest.mark.parametrize("domain_id,subject_id,brand_focus_id", [
    ("cth", "SUBJ-CTH-A", None), ("bmp", None, "BRAND-BMP-A"),
])
def test_registry_status_controls_selected_scope_even_for_admin(
    isolated_scope_database, status, allowed, domain_id, subject_id, brand_focus_id,
):
    with sqlite3.connect(isolated_scope_database) as con:
        con.execute(
            "UPDATE lumenis_subject_registry SET status=? WHERE subject_id=?",
            (status, subject_id or "SUBJ-BMP-A"),
        )
    result = _check({"id": 2}, domain_id=domain_id,
                    subject_id=subject_id, brand_focus_id=brand_focus_id)
    assert result.allowed is allowed
    assert result.verification_state == "verified"


def test_revoking_registered_scope_is_checked_again_for_same_gate(isolated_scope_database):
    from lumenis.system.security import PermissionGate

    gate = PermissionGate()
    assert _check({"id": 2}, gate=gate).allowed
    with sqlite3.connect(isolated_scope_database) as con:
        con.execute("UPDATE lumenis_subject_registry SET status='disabled' WHERE subject_id='SUBJ-CTH-A'")
    result = _check({"id": 2}, gate=gate)
    assert result.allowed is False
    assert result.verification_state == "verified"


def test_local_workspace_rechecks_registry_revocation(isolated_scope_database):
    from flask import Flask
    from lumenis.system.security import permission as p

    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    gate = p.PermissionGate()
    with app.test_request_context("/", headers={"Host": "localhost"},
                                  environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        principal = p.resolve_local_workspace_principal(module="reports", action="read")
        assert type(principal) is p.LocalWorkspacePrincipal
        args = dict(domain_id="cth", action="read", module="reports",
                    subject_id="SUBJ-CTH-A", gate=gate)
        assert p.check_local_workspace_scope_permission(principal, **args).allowed
        with sqlite3.connect(isolated_scope_database) as con:
            con.execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE subject_id='SUBJ-CTH-A'")
        result = p.check_local_workspace_scope_permission(principal, **args)
        assert result.allowed is False
        assert result.code == "scope_not_registered"
        assert result.verification_state == "verified"


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


@pytest.fixture
def browser_snapshot_permission(isolated_scope_database, monkeypatch):
    """Exercise real signed Evidence/account/grant owners; stub only byte I/O.

    Collector/Source integration tests cover the actual artifact decoder. Here
    its pure verification boundary is replaced to isolate Permission semantics.
    """
    import hashlib
    from lumenis.system.security import permission as p
    from lumenis.shared.database import DatabaseRepository
    import lumenis.shared.database as database
    from lumenis.shared.evidence import store
    from lumenis.importer import documents

    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)
    repo = DatabaseRepository(str(isolated_scope_database))
    monkeypatch.setattr(database, "get_repository", lambda: repo)
    monkeypatch.setattr(store, "get_repository", lambda: repo)
    store.init_evidence_store(str(isolated_scope_database))
    gate = p.PermissionGate()
    monkeypatch.setattr(p, "get_permission_gate", lambda: gate)
    _grant(isolated_scope_database, 1, "CTH", "reports", "read",
           {"subject_ids": ["SUBJ-CTH-A"]})
    body = "A sanitized browser snapshot."
    raw = json.dumps({"body": body}).encode()
    fingerprint = hashlib.sha256(raw).hexdigest()
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    scope = dict(domain_id="cth", subject_id="SUBJ-CTH-A", brand_focus_id=None,
                 global_scope=False)
    metadata = {"context": {**scope, "actor_id": 1},
                "source_fingerprint": fingerprint,
                "browser_snapshot_binding": {
                    "schema": "lumenis.browser-snapshot/v1",
                    "snapshot_sha256": fingerprint, "body_sha256": body_hash}}
    evidence_id = store.record_evidence(
        source="collector", feature_id="COLLECTED_SOURCE", product="CTH",
        provider="collector-browser-snapshot", version="collected-browser-snapshot:v1",
        collection_metadata=metadata, **scope,
    )
    calls = []
    def source_bytes(con, evidence):
        calls.append(evidence["id"])
        return raw, {}
    monkeypatch.setattr(documents, "_source_bytes", source_bytes)
    con = sqlite3.connect(isolated_scope_database)
    con.row_factory = sqlite3.Row
    args = dict(scope=scope, source_evidence_ref=f"app_evidence_records:{evidence_id}",
                source_fingerprint=fingerprint, body_sha256=body_hash,
                source_version="collected-browser-snapshot:v1", purpose="quote_reference",
                connection=con)
    yield p, gate, {"id": 1}, args, calls
    con.close()


def test_browser_snapshot_prepare_is_not_authorization_and_grant_is_revocable(browser_snapshot_permission):
    p, gate, actor, args, calls = browser_snapshot_permission
    prepared = gate.prepare_browser_snapshot_use(actor, **args)
    assert prepared.allowed, prepared
    assert prepared.reason == "BROWSER_SNAPSHOT_PREPARED_NOT_AUTHORIZED"
    assert prepared.requires_approval and prepared.approval_token is None
    assert not gate.check_browser_snapshot_use(actor, **args).allowed
    token = gate.grant_approval(p.OperationType.COLLECTOR_SOURCE_READ.value,
                               resource=prepared.resource)
    checked = gate.check_browser_snapshot_use(actor, **args)
    assert checked.allowed and checked.approval_token is None
    assert checked.resource == prepared.resource
    gate.revoke_approval(token)
    assert not gate.check_browser_snapshot_use(actor, **args).allowed
    assert len(calls) == 4


@pytest.mark.parametrize("kind", ["wildcard", "broad", "expired", "wrong_operation", "wrong_resource"])
def test_browser_snapshot_requires_exact_unexpired_read_grant(browser_snapshot_permission, kind):
    p, gate, actor, args, _ = browser_snapshot_permission
    prepared = gate.prepare_browser_snapshot_use(actor, **args)
    assert prepared.allowed
    gate.grant_approval(
        "*" if kind == "wildcard" else (p.OperationType.DATA_EXPORT.value
             if kind == "wrong_operation" else p.OperationType.COLLECTOR_SOURCE_READ.value),
        duration_minutes=-1 if kind == "expired" else 30,
        resource=None if kind == "broad" else ("different" if kind == "wrong_resource" else prepared.resource),
    )
    assert not gate.check_browser_snapshot_use(actor, **args).allowed


@pytest.mark.parametrize("field,value", [
    ("purpose", "ANALYZE"), ("purpose", "export"),
    ("source_fingerprint", "a" * 64), ("body_sha256", "b" * 64),
    ("source_version", "collected-native-source:live-v1"),
    ("source_evidence_ref", "app_evidence_records:999999"),
    ("scope", dict(domain_id="cth", subject_id="SUBJ-CTH-B", brand_focus_id=None)),
])
def test_browser_snapshot_wrong_binding_cannot_prepare_resource(browser_snapshot_permission, field, value):
    _, gate, actor, args, _ = browser_snapshot_permission
    assert not gate.prepare_browser_snapshot_use(actor, **{**args, field: value}).allowed


def test_browser_snapshot_rechecks_account_scope_and_integrity(browser_snapshot_permission):
    p, gate, actor, args, _ = browser_snapshot_permission
    prepared = gate.prepare_browser_snapshot_use(actor, **args)
    assert prepared.allowed
    gate.grant_approval(p.OperationType.COLLECTOR_SOURCE_READ.value, resource=prepared.resource)
    assert gate.check_browser_snapshot_use(actor, **args).allowed
    assert not gate.check_browser_snapshot_use({"id": 2}, **args).allowed
    con = args["connection"]
    con.execute("DELETE FROM v4_member_authorizations WHERE user_id=1")
    assert not gate.check_browser_snapshot_use(actor, **args).allowed
    con.rollback()
    assert gate.check_browser_snapshot_use(actor, **args).allowed
    con.execute("UPDATE app_evidence_records SET provider='forged' WHERE id=?",
                (int(args["source_evidence_ref"].split(":")[1]),))
    assert not gate.check_browser_snapshot_use(actor, **args).allowed
    con.rollback()
    assert gate.check_browser_snapshot_use(actor, **args).allowed
    con.execute("UPDATE lumenis_subject_registry SET status='disabled' WHERE subject_id='SUBJ-CTH-A'")
    assert not gate.check_browser_snapshot_use(actor, **args).allowed


def test_browser_snapshot_rejects_bypass_wrong_gate_and_physical_failure(browser_snapshot_permission, monkeypatch):
    p, gate, actor, args, _ = browser_snapshot_permission
    from lumenis.importer import documents
    assert not p.PermissionGate().prepare_browser_snapshot_use(actor, **args).allowed
    monkeypatch.setenv("PERMISSION_GATE_TESTING", "1")
    assert not gate.prepare_browser_snapshot_use(actor, **args).allowed
    monkeypatch.delenv("PERMISSION_GATE_TESTING")
    monkeypatch.setattr(documents, "_source_bytes", lambda *_: (b'{"body":"tampered"}', {}))
    assert not gate.prepare_browser_snapshot_use(actor, **args).allowed


@pytest.mark.parametrize("local", [False, True])
def test_browser_snapshot_supports_exact_global_and_local_scope(browser_snapshot_permission, local):
    from flask import Flask
    from lumenis.shared.evidence import store
    p, gate, actor, args, _ = browser_snapshot_permission
    con = args["connection"]
    old = dict(con.execute("SELECT * FROM app_evidence_records WHERE id=?",
                           (int(args["source_evidence_ref"].split(":")[1]),)).fetchone())
    metadata = json.loads(old["collection_metadata"])
    scope = dict(domain_id="cth", subject_id=None, brand_focus_id=None, global_scope=True)
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with app.test_request_context("/", headers={"Host": "localhost"},
                                  environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        if local:
            actor = p.resolve_local_workspace_principal(module="reports", action="read")
            identity = dict(actor_id=None, principal_kind=actor.principal_kind,
                            principal_ref=actor.principal_ref)
        else:
            con.execute("UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1",
                        (json.dumps({"global": True}),))
            con.commit()
            identity = {"actor_id": 1}
        metadata["context"] = {**scope, **identity}
        evidence_id = store.record_evidence(
            source="collector", feature_id="COLLECTED_SOURCE", product="CTH",
            provider="collector-browser-snapshot", version=args["source_version"],
            collection_metadata=metadata, **scope,
        )
        args = {**args, "scope": scope, "source_evidence_ref": f"app_evidence_records:{evidence_id}"}
        prepared = gate.prepare_browser_snapshot_use(actor, **args)
        assert prepared.allowed, prepared
        gate.grant_approval(p.OperationType.COLLECTOR_SOURCE_READ.value, resource=prepared.resource)
        assert gate.check_browser_snapshot_use(actor, **args).allowed
        if local:
            app.config["LUMENIS_OPEN_WORKSPACE"] = False
        else:
            con.execute("UPDATE v4_users SET status='inactive' WHERE id=1")
        assert not gate.check_browser_snapshot_use(actor, **args).allowed


def test_browser_snapshot_audit_failure_cannot_authorize(browser_snapshot_permission, monkeypatch):
    p, gate, actor, args, _ = browser_snapshot_permission
    prepared = gate.prepare_browser_snapshot_use(actor, **args)
    assert prepared.allowed
    gate.grant_approval(p.OperationType.COLLECTOR_SOURCE_READ.value, resource=prepared.resource)
    original = gate._write_audit
    def failed_audit(**kwargs):
        if kwargs.get("permission_required") == "browser_snapshot_exact_quote_use":
            raise OSError("isolated audit failure")
        return original(**kwargs)
    monkeypatch.setattr(gate, "_write_audit", failed_audit)
    checked = gate.check_browser_snapshot_use(actor, **args)
    assert not checked.allowed and checked.audit_id is None
    assert checked.reason == "BROWSER_SNAPSHOT_AUDIT_UNAVAILABLE"


@pytest.mark.parametrize("restriction", [
    {"revoked": True}, {"private": True}, {"restricted": True},
    {"confidential": True}, {"use_prohibited": True},
    {"use_status": "DENIED"}, {"use_status": "REVOKED"},
    {"use_status": "WITHDRAWN"}, {"privacy_status": "PRIVATE"},
])
def test_browser_snapshot_honors_signed_explicit_restrictions(browser_snapshot_permission, restriction):
    from lumenis.shared.evidence import store
    _, gate, actor, args, _ = browser_snapshot_permission
    con = args["connection"]
    old = dict(con.execute("SELECT * FROM app_evidence_records WHERE id=?",
                           (int(args["source_evidence_ref"].split(":")[1]),)).fetchone())
    metadata = json.loads(old["collection_metadata"])
    metadata["provenance"] = {"rights": restriction}
    evidence_id = store.record_evidence(
        source="collector", feature_id="COLLECTED_SOURCE", product="CTH",
        provider="collector-browser-snapshot", version=args["source_version"],
        collection_metadata=metadata, **args["scope"],
    )
    args = {**args, "source_evidence_ref": f"app_evidence_records:{evidence_id}"}
    assert not gate.prepare_browser_snapshot_use(actor, **args).allowed


@pytest.mark.parametrize('change', ['token', 'scope'])
def test_browser_snapshot_revocation_during_audit_is_not_admitted(browser_snapshot_permission,monkeypatch,change):
    p,gate,actor,args,_=browser_snapshot_permission
    prepared=gate.prepare_browser_snapshot_use(actor,**args)
    token=gate.grant_approval(p.OperationType.COLLECTOR_SOURCE_READ.value,resource=prepared.resource)
    audit=gate._write_audit
    def revoke(**kw):
        result=audit(**kw)
        if kw.get('permission_required')=='browser_snapshot_exact_quote_use' and kw.get('result')=='allowed':
            if change=='token':gate.revoke_approval(token)
            else:args['connection'].execute('DELETE FROM v4_member_authorizations WHERE user_id=1')
        return result
    monkeypatch.setattr(gate,'_write_audit',revoke)
    decision=gate.check_browser_snapshot_use(actor,**args)
    assert not decision.allowed
    assert decision.reason=='BROWSER_SNAPSHOT_APPROVAL_OR_SCOPE_CHANGED'
