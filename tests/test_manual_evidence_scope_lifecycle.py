"""Isolated regressions for the scoped manual Evidence compatibility owner."""
from __future__ import annotations

import json
import sqlite3
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from flask import Flask

from lumenis.shared.database import DatabaseRepository
from lumenis.system.security import permission


@pytest.fixture(params=("account", "local"))
def manual_workspace(tmp_path, monkeypatch, request):
    """Mirror the saved-document fixture's isolated DB, HMAC and real gate."""
    db_path = tmp_path / "isolated.sqlite3"
    evidence_dir = tmp_path / "app_evidence"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"test": "isolated-manual-evidence-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "test")
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)

    from lumenis.shared.evidence import manual, store
    from account import models as account_models
    from lumenis.auth import service as auth_service

    repository = DatabaseRepository(str(db_path))
    monkeypatch.setattr(manual, "get_repository", lambda: repository)
    monkeypatch.setattr(manual, "main_db_path", lambda: str(db_path))
    monkeypatch.setattr(manual, "EVIDENCE_DIR", str(evidence_dir))
    monkeypatch.setattr(store, "get_repository", lambda: repository)

    store.init_evidence_store(str(db_path))
    with repository.transaction() as connection:
        store.ensure_evidence_schema(connection)
        # Use the account owner's real schema and explicit CTH/BMP grants.
        # This is a disposable database, never a production user/session.
        connection.executescript(account_models.BASE_TABLES_SQL)
        connection.executescript(account_models.AUTHORIZATION_TABLES_SQL)
        connection.execute(
            "INSERT INTO v4_users(id, username, password_hash, role, display_name) "
            "VALUES (17, 'isolated-manual-member', 'not-a-login-password', 'user', 'Test member')"
        )
        for product in ("CTH", "ZBMP"):
            for action in ("read", "write"):
                connection.execute(
                    "INSERT INTO v4_member_authorizations(user_id, product_id, module, action, data_scope) "
                    "VALUES (17, ?, 'evidence', ?, ?)",
                    (product, action, json.dumps({"global": True})),
                )
        connection.execute(
            "INSERT INTO v4_sessions(user_id, token, expires_at) VALUES (17, ?, '2099-01-01 00:00:00')",
            ("isolated-manual-test-session",),
        )
    # Tables are initialized above; skip only account bootstrap, never session
    # authentication, scope Permission, Approval, Effect Fence or audit checks.
    monkeypatch.setattr(auth_service, "ensure_initialized", lambda: None)

    gate = permission.PermissionGate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    gate.grant_permission(permission.PermissionLevel.PUSH)
    # Normal shadow writes still need the real operation approval. Withdrawal
    # separately requires the exact row/hash/scope/actor/reason resource below.
    gate.grant_approval(permission.OperationType.DB_WRITE.value, duration_minutes=5,
                        granted_by="isolated-shadow-write-test")
    monkeypatch.setattr(permission, "get_permission_gate", lambda: gate)

    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    manual.register_app_evidence(app)

    headers = {"Host": "localhost"}
    if request.param == "account":
        headers["Authorization"] = "Bearer isolated-manual-test-session"
    with app.test_request_context(
        "/",
        headers=headers,
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        if request.param == "account":
            actor = auth_service.get_current_user()
            assert actor is not None and actor["id"] == 17
        else:
            # The local cases retain the real C6 module-admission gate.
            actor = permission.resolve_local_workspace_principal(module="evidence", action="write")
            assert actor is not None, "the real local-workspace Evidence contract is unavailable"
        scope = {
            "domain_id": "cth",
            "subject_id": None,
            "brand_focus_id": None,
            "global_scope": True,
        }
        yield {
            "root": tmp_path,
            "evidence_dir": evidence_dir,
            "repo": repository,
            "gate": gate,
            "actor": actor,
            "identity": actor.principal_ref if request.param == "local" else "actor:17",
            "identity_kind": request.param,
            "auth_headers": headers,
            "scope": scope,
            "app": app,
            "manual": manual,
            "store": store,
        }


def _seed_manual_evidence(workspace, *, scope=None, content=None, missing_file=False):
    path = None
    if content is not None or missing_file:
        workspace["evidence_dir"].mkdir(parents=True, exist_ok=True)
        path = workspace["evidence_dir"] / f"evidence-{uuid4().hex}.bin"
        if content is not None:
            path.write_bytes(content)

    scope_args = {}
    product = "CTH"
    if scope is not None:
        product = "ZBMP" if scope["domain_id"] in {"bmp", "zbmp"} else "CTH"
        scope_args = {
            "domain_id": scope["domain_id"],
            "subject_id": scope["subject_id"],
            "brand_focus_id": scope["brand_focus_id"],
            "global_scope": scope["global_scope"],
        }

    record_id = workspace["store"].record_evidence(
        source="other",
        project="LUMENIS",
        product=product,
        feature_id="APP_MANUAL_EVIDENCE",
        capture_mode="screenshot",
        result="PENDING",
        status="pending",
        inputs={
            "manual_capture": {"fixture": True},
            "source_use": "NOT_GRANTED_BY_MANUAL_CAPTURE",
        },
        metric_name="note_count",
        metric_value="0",
        evidence_path=str(path) if path else None,
        **scope_args,
    )
    assert record_id > 0
    return record_id, path


def _grant_transition(workspace, record_id, status, reason, *, scope=None):
    from lumenis.system.security.permission import OperationType

    scope = scope or workspace["scope"]
    resource = workspace["manual"].evidence_transition_resource(
        record_id,
        status,
        reason,
        actor=workspace["actor"],
        scope=scope,
    )
    operation = (
        OperationType.DATA_DELETE
        if status == "withdrawn"
        else OperationType.DB_WRITE
    )
    workspace["gate"].grant_approval(
        operation.value,
        duration_minutes=5,
        resource=resource,
        granted_by="isolated-manual-evidence-test",
    )
    return resource


def _lifecycle_count(workspace, record_id):
    return workspace["repo"].query_one(
        "SELECT COUNT(*) FROM app_evidence_records "
        "WHERE feature_id='APP_MANUAL_LIFECYCLE' "
        "AND json_extract(inputs_json, '$.record_id')=?",
        (record_id,),
    )[0]


def test_manual_reads_keep_cth_bmp_and_unassigned_rows_separate(manual_workspace):
    ws = manual_workspace
    manual = ws["manual"]
    cth_id, _ = _seed_manual_evidence(ws, scope=ws["scope"])
    bmp_scope = {
        "domain_id": "zbmp",
        "subject_id": None,
        "brand_focus_id": None,
        "global_scope": True,
    }
    bmp_id, _ = _seed_manual_evidence(ws, scope=bmp_scope)
    legacy_id, _ = _seed_manual_evidence(ws, scope=None)

    assert manual.get_evidence(cth_id, actor=ws["actor"], scope=ws["scope"])["id"] == cth_id
    assert manual.get_evidence(bmp_id, actor=ws["actor"], scope=ws["scope"]) is None
    assert manual.get_evidence(legacy_id, actor=ws["actor"], scope=ws["scope"]) is None
    assert [row["id"] for row in manual.list_evidence(actor=ws["actor"], scope=ws["scope"])["records"]] == [cth_id]
    assert manual.get_stats(actor=ws["actor"], scope=ws["scope"])["total"] == 1
    assert [row["id"] for row in manual.list_evidence(actor=ws["actor"], scope=bmp_scope)["records"]] == [bmp_id]
    assert manual.get_stats(actor=ws["actor"], scope=bmp_scope)["total"] == 1


def test_manual_read_methods_reject_missing_exact_scope(manual_workspace):
    ws = manual_workspace
    record_id, _ = _seed_manual_evidence(ws, scope=ws["scope"])
    error = ws["manual"].ManualEvidenceError

    with pytest.raises(error, match="EVIDENCE_SCOPE_REQUIRED"):
        ws["manual"].get_evidence(record_id, actor=ws["actor"], scope=None)
    with pytest.raises(error, match="EVIDENCE_SCOPE_REQUIRED"):
        ws["manual"].list_evidence(actor=ws["actor"], scope=None)
    with pytest.raises(error, match="EVIDENCE_SCOPE_REQUIRED"):
        ws["manual"].get_stats(actor=ws["actor"], scope=None)


def test_manual_file_state_reports_missing_original_bytes(manual_workspace):
    ws = manual_workspace
    record_id, path = _seed_manual_evidence(
        ws, scope=ws["scope"], missing_file=True
    )
    assert path is not None and not path.exists()

    result = ws["manual"].get_evidence(
        record_id, actor=ws["actor"], scope=ws["scope"]
    )
    assert result["file_state"] == "MISSING"
    assert result["status"] == "pending"


def test_scope_and_commit_revocation_are_rechecked(manual_workspace):
    ws = manual_workspace
    record_id, _ = _seed_manual_evidence(ws, scope=ws["scope"])

    if ws["identity_kind"] == "local":
        ws["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    else:
        with ws["repo"].transaction() as connection:
            connection.execute("DELETE FROM v4_member_authorizations WHERE user_id=17")
    with pytest.raises(PermissionError, match="EVIDENCE_SCOPE_DENIED"):
        ws["manual"].get_evidence(record_id, actor=ws["actor"], scope=ws["scope"])

    ws["app"].config["LUMENIS_OPEN_WORKSPACE"] = True
    if ws["identity_kind"] == "account":
        with ws["repo"].transaction() as connection:
            for action in ("read", "write"):
                connection.execute(
                    "INSERT INTO v4_member_authorizations(user_id, product_id, module, action, data_scope) "
                    "VALUES (17, 'CTH', 'evidence', ?, ?)", (action, json.dumps({"global": True})),
                )
    reason = "permission-revocation-check"
    resource = _grant_transition(
        ws, record_id, ws["manual"].STATUS_CONFIRMED, reason
    )
    ws["gate"].revoke_permission(permission.PermissionLevel.COMMIT)
    with pytest.raises(PermissionError, match="EVIDENCE_EFFECT_PERMISSION_DENIED"):
        ws["manual"].update_evidence_status(
            record_id,
            ws["manual"].STATUS_CONFIRMED,
            actor=ws["actor"],
            scope=ws["scope"],
            reason=reason,
        )
    assert resource
    assert ws["repo"].query_one(
        "SELECT status FROM app_evidence_records WHERE id=?", (record_id,)
    )[0] == "pending"
    assert _lifecycle_count(ws, record_id) == 0


def test_withdrawal_requires_reason_and_exact_delete_approval(manual_workspace):
    ws = manual_workspace
    record_id, path = _seed_manual_evidence(
        ws, scope=ws["scope"], content=b"source bytes stay in place"
    )
    manual = ws["manual"]

    with pytest.raises(manual.ManualEvidenceError, match="EVIDENCE_REASON_REQUIRED"):
        manual.evidence_transition_resource(
            record_id, "withdrawn", " ", actor=ws["actor"], scope=ws["scope"]
        )

    reason = "wrong-resource-approval"
    resource = manual.evidence_transition_resource(
        record_id, "withdrawn", reason, actor=ws["actor"], scope=ws["scope"]
    )
    ws["gate"].grant_approval(
        permission.OperationType.DATA_DELETE.value,
        duration_minutes=5,
        resource=resource + ":different-resource",
        granted_by="isolated-manual-evidence-test",
    )
    with pytest.raises(PermissionError, match="EVIDENCE_EFFECT_PERMISSION_DENIED"):
        manual.delete_evidence(
            record_id, actor=ws["actor"], scope=ws["scope"], reason=reason
        )

    assert path.read_bytes() == b"source bytes stay in place"
    assert ws["repo"].query_one(
        "SELECT status FROM app_evidence_records WHERE id=?", (record_id,)
    )[0] == "pending"
    assert _lifecycle_count(ws, record_id) == 0


def test_withdrawal_and_restore_retain_original_and_lifecycle_history(manual_workspace):
    ws = manual_workspace
    original_bytes = b"immutable original source bytes\x00\x01"
    record_id, path = _seed_manual_evidence(
        ws, scope=ws["scope"], content=original_bytes
    )
    manual = ws["manual"]
    reason = "owner withdrew this manual source"

    _grant_transition(ws, record_id, "withdrawn", reason)
    withdrawn, error = manual.delete_evidence(
        record_id, actor=ws["actor"], scope=ws["scope"], reason=reason
    )
    assert error is None and withdrawn is True
    current = manual.get_evidence(record_id, actor=ws["actor"], scope=ws["scope"])
    assert current["status"] == "withdrawn"
    assert current["file_state"] == "AVAILABLE"
    assert path.read_bytes() == original_bytes
    assert _lifecycle_count(ws, record_id) == 1

    audit = ws["repo"].query_one(
        "SELECT inputs_json, outputs_json FROM app_evidence_records "
        "WHERE feature_id='APP_MANUAL_LIFECYCLE' "
        "AND json_extract(inputs_json, '$.record_id')=?",
        (record_id,),
    )
    audit_inputs = json.loads(audit["inputs_json"])
    audit_outputs = json.loads(audit["outputs_json"])
    assert audit_inputs["actor"] == ws["identity"]
    assert audit_inputs["reason"] == reason
    assert audit_inputs["prior_record"]["id"] == record_id
    assert audit_inputs["prior_record"]["status"] == "pending"
    assert audit_outputs == {"status": "withdrawn", "file_state": "AVAILABLE"}

    invalid_restore_reason = "restore-must-return-to-pending"
    _grant_transition(
        ws, record_id, manual.STATUS_SHADOW, invalid_restore_reason
    )
    with pytest.raises(
        manual.ManualEvidenceError,
        match="EVIDENCE_RESTORE_TO_PENDING_REQUIRED",
    ):
        manual.update_evidence_status(
            record_id,
            manual.STATUS_SHADOW,
            actor=ws["actor"],
            scope=ws["scope"],
            reason=invalid_restore_reason,
        )
    assert _lifecycle_count(ws, record_id) == 1
    assert path.read_bytes() == original_bytes

    restore_reason = "restore-after-review"
    _grant_transition(ws, record_id, manual.STATUS_PENDING, restore_reason)
    restored, error = manual.update_evidence_status(
        record_id,
        manual.STATUS_PENDING,
        actor=ws["actor"],
        scope=ws["scope"],
        reason=restore_reason,
    )
    assert error is None
    assert restored["status"] == "pending"
    assert restored["file_state"] == "AVAILABLE"
    assert path.read_bytes() == original_bytes
    assert _lifecycle_count(ws, record_id) == 2


@pytest.mark.parametrize(
    ("table", "key_column", "key_value", "evidence_column"),
    [
        ("lumenis_cth_cases", "case_id", "case-evidence-ref", "creation_evidence_ref"),
        ("lumenis_entity_relation_assertions", "assertion_id", 1, "source_evidence_ref"),
    ],
    ids=("cth-case-fk", "entity-relation-fk"),
)
def test_withdrawal_protects_product_foreign_key_references(
    manual_workspace, table, key_column, key_value, evidence_column
):
    ws = manual_workspace
    record_id, path = _seed_manual_evidence(
        ws, scope=ws["scope"], content=b"referenced original"
    )
    with ws["repo"].transaction() as connection:
        if table == "lumenis_cth_cases":
            connection.execute(
                "CREATE TABLE lumenis_cth_cases (case_id TEXT PRIMARY KEY, "
                "creation_evidence_ref INTEGER NOT NULL "
                "REFERENCES app_evidence_records(id))"
            )
            connection.execute(
                "INSERT INTO lumenis_cth_cases(case_id, creation_evidence_ref) "
                "VALUES (?, ?)",
                (key_value, record_id),
            )
        else:
            connection.execute(
                "CREATE TABLE lumenis_entity_relation_assertions "
                "(assertion_id INTEGER PRIMARY KEY, source_evidence_ref INTEGER NOT NULL "
                "REFERENCES app_evidence_records(id))"
            )
            connection.execute(
                "INSERT INTO lumenis_entity_relation_assertions "
                "(assertion_id, source_evidence_ref) VALUES (?, ?)",
                (key_value, record_id),
            )
        foreign_keys = connection.execute(
            f"PRAGMA foreign_key_list({table})"
        ).fetchall()
        assert any(
            row[2] == "app_evidence_records"
            and row[3] == evidence_column
            and row[4] == "id"
            for row in foreign_keys
        )

    reason = f"protect-reference-{table}"
    _grant_transition(ws, record_id, "withdrawn", reason)
    with pytest.raises(
        ws["manual"].ManualEvidenceError, match="EVIDENCE_REFERENCED"
    ):
        ws["manual"].delete_evidence(
            record_id, actor=ws["actor"], scope=ws["scope"], reason=reason
        )

    assert ws["repo"].query_one(
        "SELECT status FROM app_evidence_records WHERE id=?", (record_id,)
    )[0] == "pending"
    assert path.read_bytes() == b"referenced original"
    assert _lifecycle_count(ws, record_id) == 0


def test_withdrawal_protects_explicit_scope_evidence_references(manual_workspace):
    ws = manual_workspace
    record_id, path = _seed_manual_evidence(
        ws, scope=ws["scope"], content=b"scope-bound original"
    )
    with ws["repo"].transaction() as connection:
        connection.execute(
            "CREATE TABLE notes (note_id TEXT PRIMARY KEY, scope_evidence_ref TEXT)"
        )
        connection.execute(
            "INSERT INTO notes(note_id, scope_evidence_ref) VALUES (?, ?)",
            ("manual-scope-note", f"app_evidence_records:{record_id}"),
        )

    reason = "protect-explicit-scope-reference"
    _grant_transition(ws, record_id, "withdrawn", reason)
    with pytest.raises(
        ws["manual"].ManualEvidenceError, match="EVIDENCE_REFERENCED"
    ):
        ws["manual"].delete_evidence(
            record_id, actor=ws["actor"], scope=ws["scope"], reason=reason
        )
    assert path.read_bytes() == b"scope-bound original"
    assert ws["repo"].query_one(
        "SELECT status FROM app_evidence_records WHERE id=?", (record_id,)
    )[0] == "pending"
    assert _lifecycle_count(ws, record_id) == 0


def test_failed_withdrawal_rolls_back_row_file_and_lifecycle_audit(manual_workspace):
    ws = manual_workspace
    original_bytes = b"rollback must retain this exact file"
    record_id, path = _seed_manual_evidence(
        ws, scope=ws["scope"], content=original_bytes
    )
    before = ws["repo"].query_one(
        "SELECT status, integrity_digest FROM app_evidence_records WHERE id=?",
        (record_id,),
    )
    with ws["repo"].transaction() as connection:
        connection.execute(
            f"CREATE TRIGGER force_manual_evidence_withdraw_failure "
            f"BEFORE UPDATE OF status ON app_evidence_records "
            f"WHEN OLD.id={record_id} AND NEW.status='withdrawn' "
            "BEGIN SELECT RAISE(ABORT, 'forced manual lifecycle failure'); END"
        )

    reason = "exercise-database-rollback"
    _grant_transition(ws, record_id, "withdrawn", reason)
    with pytest.raises(sqlite3.IntegrityError, match="forced manual lifecycle failure"):
        ws["manual"].delete_evidence(
            record_id, actor=ws["actor"], scope=ws["scope"], reason=reason
        )

    after = ws["repo"].query_one(
        "SELECT status, integrity_digest FROM app_evidence_records WHERE id=?",
        (record_id,),
    )
    assert tuple(after) == tuple(before)
    assert path.read_bytes() == original_bytes
    assert _lifecycle_count(ws, record_id) == 0


def test_compatibility_api_requires_scope_and_anonymous_authentication(manual_workspace):
    ws = manual_workspace
    client = ws["app"].test_client()

    missing_scope = client.get("/api/app_evidence/list", headers=ws["auth_headers"])
    assert missing_scope.status_code == 400
    assert missing_scope.get_json()["code"] == "EVIDENCE_SCOPE_REQUIRED"

    ws["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    anonymous = client.get(
        "/api/app_evidence/list",
        headers={
            "X-Lumenis-Context-Mode": "GLOBAL_ALL",
            "X-Domain-Id": "CTH",
        },
    )
    assert anonymous.status_code == 401
    assert anonymous.get_json()["code"] == "AUTH_REQUIRED"


def test_normal_capture_and_api_read_use_real_scope_permission(manual_workspace):
    ws = manual_workspace
    record, error = ws["manual"].create_evidence(
        source="other", capture_mode="manual_input", metric_name="note_count",
        metric_value=0, notes="self-authored diagnostic; source use remains ungranted",
        actor=ws["actor"], scope=ws["scope"],
    )
    assert error is None and record["metric_value"] == "0"
    assert record["status"] == "pending"
    assert json.loads(record["inputs_json"])["use_permission"] == "NOT_GRANTED_BY_MANUAL_CAPTURE"
    client = ws["app"].test_client()
    headers = {**ws["auth_headers"], "X-Lumenis-Context-Mode": "GLOBAL_ALL", "X-Domain-Id": "CTH"}
    response = client.get(f'/api/app_evidence/{record["id"]}', headers=headers)
    assert response.status_code == 200 and response.get_json()["data"]["id"] == record["id"]
    for limit in ("unknown", "0", "201"):
        invalid = client.get('/api/app_evidence/list?limit=' + limit, headers=headers)
        assert invalid.status_code == 400
        assert invalid.get_json()["code"] == "INVALID_EVIDENCE_QUERY"


def test_registered_focus_and_global_rows_never_widen_each_other(manual_workspace):
    import subject_registry
    ws = manual_workspace
    with ws["repo"].transaction() as connection:
        subject_registry.ensure_schema(connection)
        for subject_id, brand_id, domain, kind in (
            ("SUBJ-MANUAL-A", None, "CTH", "company"),
            ("SUBJ-MANUAL-B", None, "CTH", "company"),
            ("SUBJ-MANUAL-BMP", "BRAND-MANUAL-A", "BMP", "brand"),
        ):
            connection.execute(
                "INSERT INTO lumenis_subject_registry(subject_id, brand_focus_id, domain_id, subject_type, "
                "name_en, name_zh, name_en_norm, name_zh_norm, industry, keywords_json, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'retail', '[]', 'configured', '2026-10-08', '2026-10-08')",
                (subject_id, brand_id, domain, kind, subject_id, subject_id, subject_id.lower(), subject_id),
            )
    focus_a = {**ws["scope"], "subject_id": "SUBJ-MANUAL-A", "global_scope": False}
    focus_b = {**focus_a, "subject_id": "SUBJ-MANUAL-B"}
    bmp = {"domain_id": "zbmp", "subject_id": None, "brand_focus_id": "BRAND-MANUAL-A", "global_scope": False}
    global_id, _ = _seed_manual_evidence(ws, scope=ws["scope"])
    first, _ = _seed_manual_evidence(ws, scope=focus_a)
    second, _ = _seed_manual_evidence(ws, scope=focus_b)
    brand, _ = _seed_manual_evidence(ws, scope=bmp)
    for scope, expected_id in ((ws["scope"], global_id), (focus_a, first), (focus_b, second), (bmp, brand)):
        rows = ws["manual"].list_evidence(actor=ws["actor"], scope=scope)["records"]
        assert [row["id"] for row in rows] == [expected_id]
        assert ws["manual"].get_stats(actor=ws["actor"], scope=scope)["total"] == 1
    assert ws["manual"].get_evidence(second, actor=ws["actor"], scope=focus_a) is None
    with pytest.raises(PermissionError, match="EVIDENCE_SCOPE_DENIED"):
        ws["manual"].get_evidence(first, actor=ws["actor"], scope={**focus_a, "subject_id": "SUBJ-NOT-REGISTERED"})


@pytest.mark.parametrize("value", ["typed", "nested"])
def test_withdrawal_protects_json_source_references(manual_workspace, value):
    ws = manual_workspace
    record_id, path = _seed_manual_evidence(ws, scope=ws["scope"], content=b"JSON-referenced bytes")
    reference = ({"evidence_id": record_id} if value == "typed" else
                 {"sources": [f"app_evidence_records:{record_id}"]})
    with ws["repo"].transaction() as connection:
        connection.execute("CREATE TABLE cases (source_refs_json TEXT)")
        connection.execute("INSERT INTO cases VALUES (?)", (json.dumps(reference),))
    reason = "protect-json-source-reference"
    _grant_transition(ws, record_id, "withdrawn", reason)
    with pytest.raises(ws["manual"].ManualEvidenceError, match="EVIDENCE_REFERENCED"):
        ws["manual"].delete_evidence(record_id, actor=ws["actor"], scope=ws["scope"], reason=reason)
    assert path.read_bytes() == b"JSON-referenced bytes"
    assert _lifecycle_count(ws, record_id) == 0


@pytest.mark.parametrize("failure", ["readback", "fence_completion"])
def test_post_commit_upload_failure_retains_committed_bytes(manual_workspace, monkeypatch, failure):
    ws = manual_workspace
    if failure == "readback":
        def failed_readback(*args, **kwargs):
            raise RuntimeError("diagnostic lost response after commit")
        monkeypatch.setattr(ws["manual"], "get_evidence", failed_readback)
    else:
        from lumenis.system.security.effect_fence import get_effect_fence
        fence = get_effect_fence()
        original_complete = fence.complete
        def failed_completion(key, *, success):
            if success:
                raise RuntimeError("diagnostic fence completion unavailable after commit")
            return original_complete(key, success=success)
        monkeypatch.setattr(fence, "complete", failed_completion)
    headers = {**ws["auth_headers"], "X-Lumenis-Context-Mode": "GLOBAL_ALL", "X-Domain-Id": "CTH"}
    response = ws["app"].test_client().post('/api/app_evidence/upload', headers=headers, data={
        "file": (BytesIO(b"committed original bytes"), "source.txt"), "source": "other",
        "capture_mode": "manual_input", "metric_name": "note_count", "metric_value": "0",
    })
    assert response.status_code == 503
    row = ws["repo"].query_one("SELECT * FROM app_evidence_records WHERE feature_id='APP_MANUAL_EVIDENCE'")
    assert row is not None and row["status"] == "pending"
    assert Path(row["evidence_path"]).read_bytes() == b"committed original bytes"
    assert ws["store"].verify_evidence_record_integrity(dict(row))


def test_modified_original_file_reports_integrity_mismatch(manual_workspace):
    ws = manual_workspace
    ws["evidence_dir"].mkdir(parents=True)
    path = ws["evidence_dir"] / 'diagnostic.txt'
    path.write_bytes(b"original diagnostic text")
    record, _ = ws["manual"].create_evidence(source="other", capture_mode="manual_input",
        metric_name="note_count", metric_value=0, evidence_path=str(path), actor=ws["actor"], scope=ws["scope"])
    assert record["file_state"] == "AVAILABLE"
    path.write_bytes(b"changed diagnostic text")
    changed = ws["manual"].get_evidence(record["id"], actor=ws["actor"], scope=ws["scope"])
    assert changed["file_state"] == "INTEGRITY_MISMATCH"
    with pytest.raises(ws["manual"].ManualEvidenceError, match="EVIDENCE_FILE_UNAVAILABLE"):
        ws["manual"].update_evidence_status(record["id"], "confirmed", actor=ws["actor"], scope=ws["scope"], reason="must not confirm modified bytes")


def test_final_transaction_scope_revocation_rolls_back_every_write(manual_workspace, monkeypatch):
    ws = manual_workspace
    record_id, path = _seed_manual_evidence(ws, scope=ws["scope"], content=b"original final-check bytes")
    before = dict(ws["repo"].query_one("SELECT * FROM app_evidence_records WHERE id=?", (record_id,)))
    original_effect = ws["manual"]._effect
    transaction_calls = 0
    def revoke_at_final_check(actor, scope, operation, resource, connection=None):
        nonlocal transaction_calls
        if connection is not None:
            transaction_calls += 1
            if transaction_calls == 2:
                if ws["identity_kind"] == "account":
                    connection.execute("DELETE FROM v4_member_authorizations WHERE user_id=17")
                else:
                    ws["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
        return original_effect(actor, scope, operation, resource, connection)
    monkeypatch.setattr(ws["manual"], "_effect", revoke_at_final_check)
    with pytest.raises(PermissionError, match="EVIDENCE_SCOPE_DENIED"):
        ws["manual"].update_evidence_status(record_id, "confirmed", actor=ws["actor"], scope=ws["scope"], reason="final check revoked")
    after = dict(ws["repo"].query_one("SELECT * FROM app_evidence_records WHERE id=?", (record_id,)))
    assert after == before
    assert _lifecycle_count(ws, record_id) == 0
    assert path.read_bytes() == b"original final-check bytes"


def test_terminal_retry_reads_without_repeating_withdrawal(manual_workspace):
    ws = manual_workspace
    record_id, path = _seed_manual_evidence(ws, scope=ws["scope"], content=b"retry-safe original")
    reason = "withdraw once; response may be lost"
    _grant_transition(ws, record_id, "withdrawn", reason)
    ws["manual"].delete_evidence(record_id, actor=ws["actor"], scope=ws["scope"], reason=reason)
    before = dict(ws["repo"].query_one("SELECT * FROM app_evidence_records WHERE id=?", (record_id,)))
    ws["gate"].revoke_permission(permission.PermissionLevel.PUSH)
    result, error = ws["manual"].delete_evidence(record_id, actor=ws["actor"], scope=ws["scope"], reason=reason)
    assert result is True and error is None
    assert dict(ws["repo"].query_one("SELECT * FROM app_evidence_records WHERE id=?", (record_id,))) == before
    assert _lifecycle_count(ws, record_id) == 1
    assert path.read_bytes() == b"retry-safe original"


def test_withdrawal_protects_non_first_saved_work_citation(manual_workspace, monkeypatch):
    import hashlib
    import shared_artifacts
    from lumenis.shared.reporting import saved_work
    ws = manual_workspace
    monkeypatch.setattr(saved_work, "get_repository", lambda: ws["repo"])
    monkeypatch.setattr(shared_artifacts, "get_repository", lambda: ws["repo"])
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(ws["root"] / 'artifacts'))
    shared_artifacts.ensure_artifact_table()
    if ws["identity_kind"] == "account":
        with ws["repo"].transaction() as connection:
            for action in ("read", "write"):
                connection.execute(
                    "INSERT INTO v4_member_authorizations(user_id, product_id, module, action, data_scope) "
                    "VALUES (17, 'CTH', 'reports', ?, ?)", (action, json.dumps({"global": True})),
                )
    ws["gate"].grant_permission(permission.PermissionLevel.VERIFY)
    saved = saved_work.save_work(title='Retained source references', markdown='Self-authored reference fixture',
        kind='research', payload={}, citations=[], request_id='reference-guard-1', actor=ws["actor"], scope=ws["scope"])
    first, _ = _seed_manual_evidence(ws, scope=ws["scope"])
    second, path = _seed_manual_evidence(ws, scope=ws["scope"], content=b"second-citation original")
    # Model a retained historical document's complete citation list. This is
    # reference-guard data, never accepted source-use or business E2E evidence.
    document = saved['document']
    document['citations'] = [{"evidence_id": first}, {"evidence_id": second}]
    raw = saved_work._json(document)
    artifact = saved['artifact']
    artifact_path = shared_artifacts.artifact_root() / artifact['relative_path']
    artifact_path.write_bytes(raw)
    with ws['repo'].transaction() as connection:
        connection.execute("UPDATE lumenis_shared_artifacts SET evidence_id=?,size_bytes=?,sha256=? WHERE artifact_id=?",
            (str(first), len(raw), hashlib.sha256(raw).hexdigest(), artifact['artifact_id']))
    reason = 'preserve all immutable document citations'
    _grant_transition(ws, second, 'withdrawn', reason)
    with pytest.raises(ws['manual'].ManualEvidenceError, match='EVIDENCE_REFERENCED'):
        ws['manual'].delete_evidence(second, actor=ws['actor'], scope=ws['scope'], reason=reason)
    assert path.read_bytes() == b"second-citation original"
    assert _lifecycle_count(ws, second) == 0


@pytest.mark.parametrize('shape', ['case_scope_ref', 'source_brief', 'business_derivative', 'evaluation'])
def test_withdrawal_protects_retained_workflow_reference_shapes(manual_workspace, shape):
    ws = manual_workspace
    record_id, path = _seed_manual_evidence(ws, scope=ws['scope'], content=b'retained workflow source')
    if shape == 'case_scope_ref':
        table, column = 'lumenis_cth_cases', 'source_refs_json'
        value = [{'scope_evidence_ref': str(record_id)}]
    elif shape == 'evaluation':
        table, column = 'evaluation_records', 'metadata'
        value = {'source_evidence_refs': [str(record_id)]}
    else:
        table, column = 'daily_reports', 'source_snapshot'
        value = ({'source_brief': {'records': [{'scope_evidence_ref': str(record_id)}]}}
                 if shape == 'source_brief' else
                 {'business_analysis': {'evidence_ref': 'app_evidence_records:' + str(record_id)}})
    with ws['repo'].transaction() as connection:
        connection.execute(f'CREATE TABLE {table} ({column} TEXT)')
        connection.execute(f'INSERT INTO {table} VALUES (?)', (json.dumps(value),))
    reason = 'protect retained ' + shape
    _grant_transition(ws, record_id, 'withdrawn', reason)
    with pytest.raises(ws['manual'].ManualEvidenceError, match='EVIDENCE_REFERENCED'):
        ws['manual'].delete_evidence(record_id, actor=ws['actor'], scope=ws['scope'], reason=reason)
    assert path.read_bytes() == b'retained workflow source'
    assert _lifecycle_count(ws, record_id) == 0


@pytest.mark.parametrize(
    'shape',
    ['source_evidence_refs', 'rights_evidence_ref', 'nested_output_source_refs', 'review_evidence_refs'],
)
def test_withdrawal_protects_signed_evidence_row_reference_shapes(manual_workspace, shape):
    ws = manual_workspace
    record_id, path = _seed_manual_evidence(
        ws, scope=ws['scope'], content=b'signed Evidence reference source'
    )
    pointer = f'app_evidence_records:{record_id}'
    inputs, outputs = {}, {}
    if shape == 'source_evidence_refs':
        inputs = {'source_evidence_refs': [pointer]}
    elif shape == 'rights_evidence_ref':
        inputs = {'rights_evidence_ref': pointer}
    elif shape == 'nested_output_source_refs':
        outputs = {'source_refs': [{'source_id': 'canonical-source-1', 'evidence_ref': pointer}]}
    else:
        inputs = {'review_evidence_refs': [record_id]}

    with ws['repo'].transaction() as connection:
        reference_id = ws['store'].record_evidence(
            connection=connection,
            source='manual_reference_guard_test',
            project='LUMENIS',
            product='CTH',
            feature_id='MANUAL_EVIDENCE_REFERENCE_GUARD_TEST',
            test_name=f'{shape}-{record_id}',
            result='RECORDED',
            status='derived',
            inputs=inputs,
            outputs=outputs,
            domain_id=ws['scope']['domain_id'],
            subject_id=ws['scope']['subject_id'],
            brand_focus_id=ws['scope']['brand_focus_id'],
            global_scope=ws['scope']['global_scope'],
        )
    reference_row = ws['repo'].query_one(
        'SELECT * FROM app_evidence_records WHERE id=?', (reference_id,)
    )
    assert type(reference_id) is int and reference_id > 0
    assert reference_row is not None
    assert ws['store'].verify_evidence_record_integrity(dict(reference_row))

    reason = f'protect signed Evidence reference {shape}'
    _grant_transition(ws, record_id, 'withdrawn', reason)
    with pytest.raises(ws['manual'].ManualEvidenceError, match='EVIDENCE_REFERENCED'):
        ws['manual'].delete_evidence(
            record_id, actor=ws['actor'], scope=ws['scope'], reason=reason
        )

    assert path.read_bytes() == b'signed Evidence reference source'
    assert ws['repo'].query_one(
        'SELECT status FROM app_evidence_records WHERE id=?', (record_id,)
    )[0] == 'pending'
    assert _lifecycle_count(ws, record_id) == 0


@pytest.mark.parametrize('snapshot', ['untyped_metric', 'absent_legacy', 'valid_legacy', 'malformed'])
def test_reference_guard_keeps_optional_snapshot_and_failure_distinct(manual_workspace, snapshot):
    ws = manual_workspace
    record_id, path = _seed_manual_evidence(ws, scope=ws['scope'], content=b'optional snapshot source')
    stored = (json.dumps({'metrics': [str(record_id)]}) if snapshot == 'untyped_metric'
              else '' if snapshot == 'absent_legacy' else
              'notes:publish_date[2026-10-01,2026-10-08];subject:verified;stats_count=3'
              if snapshot == 'valid_legacy' else '{not-valid-json')
    with ws['repo'].transaction() as connection:
        connection.execute('CREATE TABLE daily_reports(source_snapshot TEXT)')
        connection.execute('INSERT INTO daily_reports VALUES (?)', (stored,))
    reason = 'check exact reference keys and optional snapshot'
    _grant_transition(ws, record_id, 'withdrawn', reason)
    if snapshot == 'malformed':
        with pytest.raises(ws['manual'].ManualEvidenceError, match='EVIDENCE_REFERENCE_CHECK_UNAVAILABLE'):
            ws['manual'].delete_evidence(record_id, actor=ws['actor'], scope=ws['scope'], reason=reason)
        assert _lifecycle_count(ws, record_id) == 0
    else:
        result, error = ws['manual'].delete_evidence(record_id, actor=ws['actor'], scope=ws['scope'], reason=reason)
        assert result is True and error is None
        assert _lifecycle_count(ws, record_id) == 1
    assert path.read_bytes() == b'optional snapshot source'
