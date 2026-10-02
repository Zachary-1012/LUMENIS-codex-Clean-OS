"""Isolated canonical Permission/Evidence tests for explicit training review submissions."""
import json
import sqlite3
import uuid

import pytest

from lumenis.shared.evidence import store
from lumenis.shared.learning import training_cases, training_review
from lumenis.shared.reporting.source_brief_job import _scope_material
from lumenis.system.ai_gateway import owned_training
from lumenis.system.security import permission as p


@pytest.fixture(autouse=True)
def strict_permission(monkeypatch):
    previous = p._TESTING_BYPASS_ENABLED
    p.set_testing_bypass(False)
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    yield
    p.set_testing_bypass(previous)


@pytest.fixture
def review_db(tmp_path, monkeypatch):
    path = tmp_path / "training-review.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({"review-test": "ephemeral-training-review-key"}))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "review-test")
    import subject_registry
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript("""
            CREATE TABLE v4_users (id INTEGER PRIMARY KEY, role TEXT NOT NULL, status TEXT NOT NULL);
            CREATE TABLE v4_member_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, product_id TEXT NOT NULL,
                module TEXT NOT NULL, action TEXT NOT NULL, data_scope TEXT, time_range TEXT,
                granted_by INTEGER, created_at TEXT, updated_at TEXT,
                UNIQUE(user_id, product_id, module, action, data_scope)
            );
            INSERT INTO v4_users VALUES (1, 'user', 'active'), (2, 'user', 'active');
        """)
        subject_registry.ensure_schema(connection)
        rows = [
            ("SUBJ-A", None, "CTH", "company", "Subject A", "主体 A", "subject a", "主体 a", "retail", "[]", "configured", "2026-10-01", "2026-10-01"),
            ("SUBJ-B", None, "CTH", "company", "Subject B", "主体 B", "subject b", "主体 b", "retail", "[]", "configured", "2026-10-01", "2026-10-01"),
            ("SUBJ-BMP", "BRAND-A", "BMP", "brand", "Brand A", "品牌 A", "brand a", "品牌 a", "beauty", "[]", "configured", "2026-10-01", "2026-10-01"),
        ]
        connection.executemany("""
            INSERT INTO lumenis_subject_registry (
                subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh,
                name_en_norm, name_zh_norm, industry, keywords_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        store.ensure_evidence_schema(connection)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(app_evidence_records)")}
        for name, kind, default in store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if name not in columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                connection.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {name} {kind}{suffix}")
    return path


def _scope(subject="SUBJ-A", *, domain="cth", global_scope=False):
    bmp = domain in {"bmp", "zbmp"}
    return _scope_material(
        product_id="ZBMP" if bmp else "CTH", global_scope=global_scope,
        entity_label="Global" if global_scope else "Registered focus",
        subject_id=None if bmp or global_scope else subject,
        brand_focus_id=subject if bmp and not global_scope else None,
    )


def _source(connection, scope, *, name="source-a"):
    row_id = store.record_evidence(
        connection=connection, source="public_http", project="LUMENIS", product=scope["product_id"],
        feature_id="TRAINING_REVIEW_SOURCE_TEST", asset_id=name, test_name=name,
        result="PASS", status="verified", inputs={"source_id": name}, outputs={"observed": True},
        domain_id=scope["domain_id"], subject_id=scope["subject_id"],
        brand_focus_id=scope["brand_focus_id"], global_scope=scope["global"],
    )
    return f"app_evidence_records:{row_id}"


def _args(scope, source_ref, *, actor_id=1, submission_id=None, prompt="User's explicit question.", target="Reviewer-approved answer."):
    return {
        "authenticated_actor": {"id": actor_id}, "expected_scope": scope,
        "source_evidence_refs": [source_ref],
        "submission_id": submission_id or str(uuid.uuid4()),
        "prompt_messages": [{"role": "user", "content": prompt}],
        "reviewer_approved_target": target, "context": "Human reviewed CTH task context.",
        "rights_declaration": {"purpose": "model_training", "rights_disposition": "permitted"},
    }


def _grant_scope(path, actor_id, product, scope):
    with sqlite3.connect(path) as connection:
        connection.execute("""
            INSERT INTO v4_member_authorizations (user_id, product_id, module, action, data_scope)
            VALUES (?, ?, 'owned_training', 'write', ?)
        """, (actor_id, product, json.dumps(scope)))


def _gate(resource=None):
    gate = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})
    token = gate.grant_approval(
        p.OperationType.MODEL_TRAIN.value, resource=resource, granted_by="isolated-test-reviewer",
    ) if resource else None
    return gate, token


def _approved_call(path, args, *, gate=None):
    resource = training_review.training_review_approval_resource(**args)
    if gate is None:
        gate, token = _gate(resource)
    else:
        token = None
        gate.grant_approval(p.OperationType.MODEL_TRAIN.value, resource=resource,
                            granted_by="isolated-test-reviewer")
    return training_review.submit_training_review(gate=gate, **args), gate, token, resource


def _review_count(path):
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id IN (?,?)",
            ("OWNED_TRAINING_TARGET_REVIEW", "OWNED_TRAINING_RIGHTS_APPROVAL"),
        ).fetchone()[0]


def test_explicit_submission_writes_signed_rows_exports_gateway_record_and_noops(review_db):
    scope = _scope()
    _grant_scope(review_db, 1, "CTH", {"subject_ids": ["SUBJ-A"]})
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    args = _args(scope, source_ref)
    result, gate, token, review_resource = _approved_call(review_db, args)
    assert result["state"] == "recorded" and result["training_executed"] is False
    assert result["review_evidence_ref"].startswith("app_evidence_records:")
    assert result["rights_evidence_ref"].startswith("app_evidence_records:")
    assert review_resource.startswith("owned_training_target_review:v1:")
    assert p.owned_training_approval_resource(
        owned_training.TrainingApprovalRequest(
            model_id=owned_training.MODEL_ID, model_revision=owned_training.MODEL_REVISION,
            train_sha256="a" * 64, heldout_sha256="b" * 64, scopes=("SUBJ-A",),
            recipe=owned_training.H100_RECIPE, manifest_sha256="c" * 64, domain_id="cth",
        ), actor_id=1, domain_id="cth",
        context={"scope_descriptors": {"SUBJ-A": {
            "domain_id": "cth", "product_id": "CTH", "global_scope": False,
            "subject_id": "SUBJ-A", "brand_focus_id": None,
        }}},
    ) != review_resource

    def export_authorize():
        return {"actor_id": "actor:1", "scope": scope,
                "permission_audit_ref": "fresh:permission", "operation_audit_ref": "fresh:operation"}

    records = training_cases.export_reviewed_training_records(
        [result["review_evidence_ref"]], actor_id="actor:1", expected_scope=scope,
        authorize=export_authorize,
    )
    record, prompt = owned_training._validate_record(records[0])
    assert record["domain_id"] == "cth" and prompt == "user's explicit question."
    assert records[0]["messages"][-1]["content"] == args["reviewer_approved_target"]
    before = _review_count(review_db)
    noop = training_review.submit_training_review(gate=gate, **args)
    assert noop["state"] == "already_recorded"
    assert noop["review_evidence_ref"] == result["review_evidence_ref"]
    assert _review_count(review_db) == before == 2
    assert gate.get_valid_approval_token(p.OperationType.MODEL_TRAIN.value, review_resource, exact=True) == token


def test_bmp_brand_focus_scope_round_trips_to_gateway_domain(review_db):
    scope = _scope("BRAND-A", domain="zbmp")
    _grant_scope(review_db, 1, "ZBMP", {"brand_focus_ids": ["BRAND-A"]})
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope, name="bmp-source")
    args = _args(scope, source_ref)
    result, _, _, _ = _approved_call(review_db, args)
    records = training_cases.export_reviewed_training_records(
        [result["review_evidence_ref"]], actor_id="actor:1", expected_scope=scope,
        authorize=lambda: {"actor_id": "actor:1", "scope": scope,
                         "permission_audit_ref": "fresh:permission", "operation_audit_ref": "fresh:operation"},
    )
    record, _ = owned_training._validate_record(records[0])
    assert record["domain_id"] == "bmp" and record["scope"] == "BRAND-A"


@pytest.mark.parametrize("approval", ["missing", "wrong_resource", "revoked"])
def test_denied_or_revoked_exact_approval_writes_no_learning_evidence(review_db, approval):
    scope = _scope()
    _grant_scope(review_db, 1, "CTH", {"subject_ids": ["SUBJ-A"]})
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    args = _args(scope, source_ref)
    exact = training_review.training_review_approval_resource(**args)
    gate = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})
    token = None
    if approval != "missing":
        token = gate.grant_approval(p.OperationType.MODEL_TRAIN.value,
                                    resource=exact + "wrong" if approval == "wrong_resource" else exact)
    if approval == "revoked":
        assert gate.revoke_approval(token)
    with pytest.raises(PermissionError):
        training_review.submit_training_review(gate=gate, **args)
    assert _review_count(review_db) == 0


def test_exact_operation_approval_cannot_replace_missing_scope_grant(review_db):
    scope = _scope()
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    args = _args(scope, source_ref)
    gate, _ = _gate(training_review.training_review_approval_resource(**args))
    with pytest.raises(PermissionError, match="SCOPE_DENIED"):
        training_review.submit_training_review(gate=gate, **args)
    assert _review_count(review_db) == 0


def test_actor_and_scope_are_bound_to_the_exact_review_resource(review_db):
    _grant_scope(review_db, 1, "CTH", {"subject_ids": ["SUBJ-A", "SUBJ-B"]})
    _grant_scope(review_db, 2, "CTH", {"subject_ids": ["SUBJ-A", "SUBJ-B"]})
    scope_a, scope_b = _scope("SUBJ-A"), _scope("SUBJ-B")
    with sqlite3.connect(review_db) as connection:
        source_a, source_b = _source(connection, scope_a), _source(connection, scope_b, name="source-b")
    args = _args(scope_a, source_a)
    resource = training_review.training_review_approval_resource(**args)
    gate, _ = _gate(resource)
    wrong_actor = {**args, "authenticated_actor": {"id": 2}}
    wrong_scope = {**args, "expected_scope": scope_b, "source_evidence_refs": [source_b]}
    for request in (wrong_actor, wrong_scope):
        with pytest.raises(PermissionError, match="EXACT_APPROVAL_REQUIRED"):
            training_review.submit_training_review(gate=gate, **request)
    assert _review_count(review_db) == 0


def test_source_tampering_and_testing_bypass_are_rejected_without_writes(review_db):
    scope = _scope()
    _grant_scope(review_db, 1, "CTH", {"subject_ids": ["SUBJ-A"]})
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    args = _args(scope, source_ref)
    gate, token = _gate(training_review.training_review_approval_resource(**args))
    with sqlite3.connect(review_db) as connection:
        connection.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?", (int(source_ref.split(":")[1]),))
    with pytest.raises(RuntimeError, match="SIGNATURE_INVALID"):
        training_review.submit_training_review(gate=gate, **args)
    assert _review_count(review_db) == 0

    # Testing bypass stays forbidden even with a matching token.
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope, name="source-after-tamper")
    args = _args(scope, source_ref)
    gate.grant_approval(p.OperationType.MODEL_TRAIN.value,
                        resource=training_review.training_review_approval_resource(**args))
    p.set_testing_bypass(True)
    with pytest.raises(PermissionError, match="TESTING_BYPASS"):
        training_review.submit_training_review(gate=gate, **args)
    assert _review_count(review_db) == 0


def test_same_submission_id_with_changed_payload_conflicts(review_db):
    scope = _scope()
    _grant_scope(review_db, 1, "CTH", {"subject_ids": ["SUBJ-A"]})
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    args = _args(scope, source_ref, submission_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    _approved_call(review_db, args)
    changed = {**args, "reviewer_approved_target": "A different target."}
    with pytest.raises(ValueError, match="SUBMISSION_CONFLICT"):
        training_review.submit_training_review(gate=p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT}), **changed)
    assert _review_count(review_db) == 2


def test_rights_declaration_must_explicitly_permit_model_training(review_db):
    scope = _scope()
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    args = _args(scope, source_ref)
    args["rights_declaration"] = {"purpose": "model_training", "rights_disposition": "UNKNOWN"}
    with pytest.raises(PermissionError, match="RIGHTS_DECLARATION_NOT_PERMITTED"):
        training_review.training_review_approval_resource(**args)
    assert _review_count(review_db) == 0


def test_target_write_failure_rolls_back_rights_row(review_db, monkeypatch):
    scope = _scope()
    _grant_scope(review_db, 1, "CTH", {"subject_ids": ["SUBJ-A"]})
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    args = _args(scope, source_ref)
    gate, _ = _gate(training_review.training_review_approval_resource(**args))
    original = training_review.store.record_evidence

    def fail_after_rights(**kwargs):
        if kwargs.get("feature_id") == "OWNED_TRAINING_TARGET_REVIEW":
            raise RuntimeError("injected target write failure")
        return original(**kwargs)

    monkeypatch.setattr(training_review.store, "record_evidence", fail_after_rights)
    with pytest.raises(RuntimeError, match="injected target write failure"):
        training_review.submit_training_review(gate=gate, **args)
    assert _review_count(review_db) == 0


def test_approval_revoked_during_write_rolls_back_both_rows(review_db, monkeypatch):
    scope = _scope()
    _grant_scope(review_db, 1, "CTH", {"subject_ids": ["SUBJ-A"]})
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    args = _args(scope, source_ref)
    resource = training_review.training_review_approval_resource(**args)
    gate, token = _gate(resource)
    original = gate.check
    calls = {"count": 0}

    def revoke_after_second(*args, **kwargs):
        result = original(*args, **kwargs)
        calls["count"] += 1
        if calls["count"] == 2:
            gate.revoke_approval(token)
        return result

    monkeypatch.setattr(gate, "check", revoke_after_second)
    with pytest.raises(PermissionError, match="EXACT_APPROVAL_REQUIRED"):
        training_review.submit_training_review(gate=gate, **args)
    assert calls["count"] == 2
    assert _review_count(review_db) == 0


def _open_workspace():
    from flask import Flask
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    return app


def _workspace_args(scope, source_ref):
    args = _args(scope, source_ref)
    args.pop("authenticated_actor")
    args["principal"] = p.resolve_local_workspace_principal(module="owned_training", action="write")
    assert type(args["principal"]) is p.LocalWorkspacePrincipal
    return args


def _workspace_export(result, args, gate, resource):
    material = training_review._request_material(**args)

    def authorize():
        scope_audit, operation_audit = training_review._authorize(gate, material, resource)
        return {"actor_id": "workspace:local", "scope": args["expected_scope"],
                "permission_audit_ref": scope_audit, "operation_audit_ref": operation_audit}

    return training_cases.export_reviewed_training_records(
        [result["review_evidence_ref"]], actor_id="workspace:local", expected_scope=args["expected_scope"],
        authorize=authorize, principal=args["principal"], gate=gate,
    )


@pytest.mark.parametrize("domain,focus,global_scope", [
    ("cth", "SUBJ-A", False), ("zbmp", "BRAND-A", False),
    ("cth", "SUBJ-A", True), ("zbmp", "BRAND-A", True),
])
def test_explicit_local_workspace_review_and_read_export_need_no_account_rows(review_db, domain, focus, global_scope):
    scope = _scope(focus, domain=domain, global_scope=global_scope)
    with sqlite3.connect(review_db) as connection:
        connection.execute("DELETE FROM v4_users")
        source_ref = _source(connection, scope)
    app = _open_workspace()
    with app.test_request_context("/", base_url="http://localhost", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args = _workspace_args(scope, source_ref)
        resource = training_review.training_review_approval_resource(**args)
        gate, _ = _gate(resource)
        gate.grant_permission(p.PermissionLevel.VERIFY)
        result = training_review.submit_training_review(gate=gate, **args)
        records = _workspace_export(result, args, gate, resource)
        assert records[0]["messages"][-1]["content"] == args["reviewer_approved_target"]
        assert owned_training._validate_record(records[0])[0]["domain_id"] == ("bmp" if domain == "zbmp" else "cth")
        noop = training_review.submit_training_review(gate=gate, **args)
        assert noop["state"] == "already_recorded" and noop["review_evidence_ref"] == result["review_evidence_ref"]
    with sqlite3.connect(review_db) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM app_evidence_records WHERE source='shared_learning'").fetchall()
        assert len(rows) == 2
        for row in rows:
            assert store.verify_evidence_record_integrity(dict(row))
            inputs = json.loads(row["inputs_json"])
            assert inputs["actor_id"] == "workspace:local"
            assert inputs["principal_kind"] == "local_workspace" and inputs["principal_ref"] == "workspace:local"
        assert connection.execute("SELECT COUNT(*) FROM v4_users").fetchone()[0] == 0


def test_workspace_principal_does_not_replace_exact_review_approval_or_mix_with_account(review_db):
    scope = _scope()
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    app = _open_workspace()
    with app.test_request_context("/", base_url="http://localhost", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args = _workspace_args(scope, source_ref)
        exact = training_review.training_review_approval_resource(**args)
        actor_args = {key: value for key, value in args.items() if key != "principal"}
        actor_args["authenticated_actor"] = {"id": 1}
        actor_resource = training_review.training_review_approval_resource(**actor_args)
        assert actor_resource != exact
        wrong_gate, _ = _gate(actor_resource)
        with pytest.raises(PermissionError, match="EXACT_APPROVAL_REQUIRED"):
            training_review.submit_training_review(gate=wrong_gate, **args)
        with pytest.raises(PermissionError, match="IDENTITY_MIXED"):
            training_review.training_review_approval_resource(**args, authenticated_actor={"id": 1})
        forged = {**args, "principal": {"principal_ref": "workspace:local", "principal_kind": "local_workspace"}}
        with pytest.raises(PermissionError, match="SERVER_IDENTITY_REQUIRED"):
            training_review.training_review_approval_resource(**forged)
    assert _review_count(review_db) == 0


def test_workspace_identity_expires_with_request_and_export_cannot_take_json_or_lambda_true(review_db):
    scope = _scope()
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    app = _open_workspace()
    with app.test_request_context("/", base_url="http://localhost", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args = _workspace_args(scope, source_ref)
        resource = training_review.training_review_approval_resource(**args)
        gate, _ = _gate(resource)
        gate.grant_permission(p.PermissionLevel.VERIFY)
        result = training_review.submit_training_review(gate=gate, **args)
        export_args = dict(actor_id="workspace:local", expected_scope=scope, authorize=lambda: True,
                           principal=args["principal"], gate=gate)
        with pytest.raises(PermissionError, match="AUTHORIZATION_MISMATCH"):
            training_cases.export_reviewed_training_records([result["review_evidence_ref"]], **export_args)
        with pytest.raises(PermissionError, match="SERVER_IDENTITY_REQUIRED"):
            training_cases.export_reviewed_training_records([result["review_evidence_ref"]],
                **{**export_args, "principal": {"principal_ref": "workspace:local"}})
        app.config["LUMENIS_OPEN_WORKSPACE"] = False
        with pytest.raises(PermissionError, match="SERVER_IDENTITY_REQUIRED"):
            _workspace_export(result, args, gate, resource)
    with pytest.raises(PermissionError, match="SERVER_IDENTITY_REQUIRED"):
        training_review.submit_training_review(gate=gate, **args)
    assert _review_count(review_db) == 2


def test_workspace_closed_during_review_rolls_back_and_can_recover_with_fresh_request(review_db, monkeypatch):
    scope = _scope()
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    app = _open_workspace()
    original = store.record_evidence
    closed = {"once": False}

    def close_after_rights(**kwargs):
        value = original(**kwargs)
        if kwargs.get("feature_id") == "OWNED_TRAINING_RIGHTS_APPROVAL" and not closed["once"]:
            app.config["LUMENIS_OPEN_WORKSPACE"] = False
            closed["once"] = True
        return value

    with app.test_request_context("/", base_url="http://localhost", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args = _workspace_args(scope, source_ref)
        resource = training_review.training_review_approval_resource(**args)
        gate, _ = _gate(resource)
        monkeypatch.setattr(store, "record_evidence", close_after_rights)
        with pytest.raises(PermissionError, match="SERVER_IDENTITY_REQUIRED"):
            training_review.submit_training_review(gate=gate, **args)
        assert _review_count(review_db) == 0
        app.config["LUMENIS_OPEN_WORKSPACE"] = True
    with app.test_request_context("/", base_url="http://localhost", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        result = training_review.submit_training_review(gate=gate, **args)
        assert result["state"] == "recorded"
    assert _review_count(review_db) == 2


def test_review_approval_does_not_grant_export_and_revocation_remains_live(review_db):
    scope = _scope()
    with sqlite3.connect(review_db) as connection:
        source_ref = _source(connection, scope)
    app = _open_workspace()
    with app.test_request_context("/", base_url="http://localhost", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        args = _workspace_args(scope, source_ref)
        resource = training_review.training_review_approval_resource(**args)
        gate, token = _gate(resource)
        result = training_review.submit_training_review(gate=gate, **args)
        with pytest.raises(PermissionError, match="EXPORT_READ_DENIED"):
            _workspace_export(result, args, gate, resource)
        gate.grant_permission(p.PermissionLevel.VERIFY)
        assert len(_workspace_export(result, args, gate, resource)) == 1
        assert gate.revoke_approval(token)
        with pytest.raises(PermissionError, match="EXACT_APPROVAL_REQUIRED"):
            _workspace_export(result, args, gate, resource)
    assert _review_count(review_db) == 2
