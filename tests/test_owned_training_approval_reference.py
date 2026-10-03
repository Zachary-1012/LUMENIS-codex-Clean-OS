"""Exact owned-training approval-reference and commit-lease contracts."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from flask import Flask
import pytest

from lumenis.system.ai_gateway.owned_training import TrainingApprovalRequest
from lumenis.system.security import permission as p


def _request_data(**changes):
    values = {
        "model_id": "openai/gpt-oss-20b",
        "model_revision": "6cee5e81ee83917806bbde320786a8fb61efebee",
        "train_sha256": "1" * 64,
        "heldout_sha256": "2" * 64,
        "domain_id": "cth",
        "scopes": ("GLOBAL / ALL",),
        "recipe": "openai-h100-bf16",
        "manifest_sha256": "3" * 64,
    }
    values.update(changes)
    return TrainingApprovalRequest(**values)


def _context():
    return {"scope_descriptors": {"GLOBAL / ALL": {
        "domain_id": "cth",
        "product_id": "CTH",
        "global_scope": True,
        "subject_id": None,
        "brand_focus_id": None,
    }}}


@contextmanager
def _request_context(app):
    with app.test_request_context(
        "/", headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        yield


@pytest.fixture(autouse=True)
def strict_permission_mode(monkeypatch):
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(p, "_TESTING_BYPASS_ENABLED", False)


@pytest.fixture
def app():
    value = Flask(__name__)
    value.config["LUMENIS_OPEN_WORKSPACE"] = True
    return value


@pytest.fixture
def gate(monkeypatch):
    value = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})
    monkeypatch.setattr(p, "get_permission_gate", lambda: value)
    return value


@pytest.fixture
def canonical_db(tmp_path, monkeypatch):
    seed = Path(os.environ["LUMENIS_TEST_SEED_DB"])
    assert seed.is_file()
    path = tmp_path / "owned-training-approval-reference.sqlite3"
    with sqlite3.connect(f"file:{seed.as_posix()}?mode=ro", uri=True) as source:
        with sqlite3.connect(path) as destination:
            source.backup(destination)
    monkeypatch.setenv("ZBC_DB_PATH", str(path.resolve()))
    monkeypatch.setenv("ZBC_EVIDENCE_DB_PATH", str(path.resolve()))
    return path.resolve()


def _check_training(gate, request, principal, resource):
    identity = p.owned_training_identity(principal=principal)
    decision = gate.check(
        p.OperationType.MODEL_TRAIN,
        resource=resource,
        caller=identity["caller"],
        domain_id="cth",
        exact_approval_required=True,
    )
    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.operation_type == p.OperationType.MODEL_TRAIN.value
    assert decision.resource == resource
    assert decision.domain_id == "cth"
    return decision


def _grant_workspace(app, gate, request=None):
    request = request or _request_data()
    context = _context()
    with _request_context(app):
        principal = p.resolve_local_workspace_principal(
            module="owned_training", action="write",
        )
        assert type(principal) is p.LocalWorkspacePrincipal
        resource = p.owned_training_approval_resource(
            request, principal=principal, domain_id="cth", context=context,
        )
        token = gate.grant_approval(
            p.OperationType.MODEL_TRAIN.value,
            resource=resource,
            granted_by="isolated-test-human",
        )
        decision = _check_training(gate, request, principal, resource)
    return request, context, principal, resource, token, decision


def _reference(app, gate, request, context, principal, decision, *, domain_id="cth"):
    with _request_context(app):
        return gate.owned_training_approval_reference(
            training_request=request,
            principal=principal,
            domain_id=domain_id,
            context=context,
            approval=decision,
        )


def _lease_arguments(request, context, principal, decision, connection, reference):
    return {
        "training_request": request,
        "principal": principal,
        "domain_id": "cth",
        "context": context,
        "approval": decision,
        "connection": connection,
        "expected_approval_reference": reference,
    }


def _prepare_probe(connection):
    connection.execute(
        "CREATE TABLE lease_probe (probe_id TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.commit()


def test_reference_tracks_issuance_separately_from_fresh_check_audits(app, gate):
    request, context, principal, resource, token, first = _grant_workspace(app, gate)
    first_reference = _reference(app, gate, request, context, principal, first)
    with _request_context(app):
        second = _check_training(gate, request, principal, resource)
    second_reference = _reference(app, gate, request, context, principal, second)

    grant = gate._approvals[token]
    assert first.audit_id != second.audit_id
    assert first.audit_id != grant.issuance_audit_id
    assert second.audit_id != grant.issuance_audit_id
    assert first_reference == second_reference
    assert first_reference["resource"] == resource
    assert first_reference["issuance_audit_id"] == grant.issuance_audit_id
    assert first_reference["approval_token_sha256"] == hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()
    assert token not in json.dumps(first_reference, sort_keys=True)
    assert "approval_token" not in first_reference


@pytest.mark.parametrize(("field", "value"), [
    ("caller", "different-caller"),
    ("resource", "different-resource"),
    ("approval_token", "unissued-test-token"),
    ("domain_id", "bmp"),
])
def test_reference_rejects_decisions_bound_to_other_caller_domain_or_grant(
    app, gate, field, value,
):
    request, context, principal, _resource, _token, decision = _grant_workspace(app, gate)
    changed_decision = replace(decision, **{field: value})

    with pytest.raises(PermissionError):
        _reference(app, gate, request, context, principal, changed_decision)


def test_reference_rejects_changed_training_request(app, gate):
    request, context, principal, _resource, _token, decision = _grant_workspace(app, gate)
    changed_request = replace(request, model_revision="different-reviewed-revision")

    with pytest.raises((PermissionError, ValueError)):
        _reference(app, gate, changed_request, context, principal, decision)


def test_reference_rejects_context_domain_mismatch(app, gate):
    request, context, principal, _resource, _token, decision = _grant_workspace(app, gate)

    with pytest.raises((PermissionError, ValueError)):
        _reference(app, gate, request, context, principal, decision, domain_id="bmp")


@pytest.mark.parametrize("state", ["expired", "revoked", "missing_issuance"])
def test_reference_requires_live_grant_with_original_issuance_audit(app, gate, state):
    request, context, principal, _resource, token, decision = _grant_workspace(app, gate)
    grant = gate._approvals[token]
    if state == "expired":
        with gate._approval_lock:
            grant.expires_at = datetime.now() - timedelta(seconds=1)
    elif state == "revoked":
        assert gate.revoke_approval(token) is True
    else:
        with gate._approval_lock:
            grant.issuance_audit_id = None

    with pytest.raises(PermissionError):
        _reference(app, gate, request, context, principal, decision)


def test_reference_rejects_testing_bypass(app, gate, monkeypatch):
    request, context, principal, _resource, _token, decision = _grant_workspace(app, gate)
    monkeypatch.setenv("PERMISSION_GATE_TESTING", "1")

    with pytest.raises(PermissionError):
        _reference(app, gate, request, context, principal, decision)


def test_reference_rejects_noncanonical_gate(app, gate):
    request, context, principal, _resource, _token, decision = _grant_workspace(app, gate)
    other_gate = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})

    with _request_context(app), pytest.raises(PermissionError):
        other_gate.owned_training_approval_reference(
            training_request=request,
            principal=principal,
            domain_id="cth",
            context=context,
            approval=decision,
        )


def test_expected_reference_lease_commits_when_same_exact_grant_is_live(
    app, gate, canonical_db,
):
    request, context, principal, _resource, _token, decision = _grant_workspace(app, gate)
    reference = _reference(app, gate, request, context, principal, decision)
    connection = sqlite3.connect(canonical_db, timeout=2)
    try:
        _prepare_probe(connection)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO lease_probe (probe_id, value) VALUES (?, ?)",
            ("same-grant", "committed"),
        )
        with _request_context(app):
            with gate.owned_training_phase_commit_lease(
                **_lease_arguments(request, context, principal, decision, connection, reference)
            ):
                connection.commit()
        assert connection.in_transaction is False
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()

    with sqlite3.connect(canonical_db) as verify:
        assert verify.execute(
            "SELECT value FROM lease_probe WHERE probe_id=?", ("same-grant",),
        ).fetchone() == ("committed",)


def test_expected_reference_rejects_replacement_without_committing(
    app, gate, canonical_db,
):
    request, context, principal, resource, old_token, old_decision = _grant_workspace(app, gate)
    old_reference = _reference(app, gate, request, context, principal, old_decision)
    assert gate.revoke_approval(old_token) is True
    new_token = gate.grant_approval(
        p.OperationType.MODEL_TRAIN.value,
        resource=resource,
        granted_by="replacement-test-human",
    )
    with _request_context(app):
        new_decision = _check_training(gate, request, principal, resource)
    new_reference = _reference(app, gate, request, context, principal, new_decision)
    assert new_decision.approval_token == new_token
    assert new_reference["resource"] == old_reference["resource"]
    assert new_reference["approval_token_sha256"] != old_reference["approval_token_sha256"]
    connection = sqlite3.connect(canonical_db, timeout=2)
    try:
        _prepare_probe(connection)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO lease_probe (probe_id, value) VALUES (?, ?)",
            ("replaced-grant", "must-roll-back"),
        )
        with _request_context(app):
            with pytest.raises(PermissionError, match="OWNED_TRAINING_PHASE_APPROVAL_REPLACED"):
                with gate.owned_training_phase_commit_lease(
                    **_lease_arguments(
                        request, context, principal, new_decision, connection, old_reference,
                    )
                ):
                    connection.commit()
        assert connection.in_transaction is True
        connection.rollback()
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()

    with sqlite3.connect(canonical_db) as verify:
        assert verify.execute(
            "SELECT COUNT(*) FROM lease_probe WHERE probe_id=?", ("replaced-grant",),
        ).fetchone()[0] == 0


def test_expected_reference_lease_rejects_testing_bypass_without_commit(
    app, gate, canonical_db, monkeypatch,
):
    request, context, principal, _resource, _token, decision = _grant_workspace(app, gate)
    reference = _reference(app, gate, request, context, principal, decision)
    monkeypatch.setenv("PERMISSION_GATE_TESTING", "1")
    connection = sqlite3.connect(canonical_db, timeout=2)
    try:
        _prepare_probe(connection)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO lease_probe (probe_id, value) VALUES (?, ?)",
            ("bypass", "must-roll-back"),
        )
        with _request_context(app), pytest.raises(PermissionError):
            with gate.owned_training_phase_commit_lease(
                **_lease_arguments(request, context, principal, decision, connection, reference)
            ):
                connection.commit()
        assert connection.in_transaction is True
        connection.rollback()
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()

    with sqlite3.connect(canonical_db) as verify:
        assert verify.execute(
            "SELECT COUNT(*) FROM lease_probe WHERE probe_id=?", ("bypass",),
        ).fetchone()[0] == 0


def test_expected_reference_lease_rejects_noncanonical_gate_without_commit(
    app, gate, canonical_db,
):
    request, context, principal, _resource, _token, decision = _grant_workspace(app, gate)
    reference = _reference(app, gate, request, context, principal, decision)
    other_gate = p.PermissionGate(enabled_permissions={p.PermissionLevel.COMMIT})
    connection = sqlite3.connect(canonical_db, timeout=2)
    try:
        _prepare_probe(connection)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO lease_probe (probe_id, value) VALUES (?, ?)",
            ("noncanonical", "must-roll-back"),
        )
        with _request_context(app), pytest.raises(PermissionError):
            with other_gate.owned_training_phase_commit_lease(
                **_lease_arguments(request, context, principal, decision, connection, reference)
            ):
                connection.commit()
        assert connection.in_transaction is True
        connection.rollback()
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.close()

    with sqlite3.connect(canonical_db) as verify:
        assert verify.execute(
            "SELECT COUNT(*) FROM lease_probe WHERE probe_id=?", ("noncanonical",),
        ).fetchone()[0] == 0
