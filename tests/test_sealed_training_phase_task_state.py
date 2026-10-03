"""Sealed v2 owned-training TaskEngine admission and recovery contracts."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from flask import Flask
import pytest

import ai_task_engine
from ai_task_engine import TaskEngine, init_task_engine_db
from lumenis.shared.database import get_repository
from lumenis.system.ai_gateway.owned_training import TrainingApprovalRequest
from lumenis.system.security import permission as p
from lumenis.system.security import training_receipts as receipts


_OWNER = "owned_training_phase_receipts:v1"
_PHASE_PATH = (
    "initial", "before_output_dir", "before_train", "step_begin",
    "substep_end", "substep_end", "pre_optimizer_step", "step_begin",
    "pre_optimizer_step", "before_adapter_save", "before_tokenizer_save",
    "after_saved_artifact_check",
)
_ALL_PHASES = (
    "initial", "before_output_dir", "before_train", "step_begin", "substep_end",
    "pre_optimizer_step", "before_adapter_save", "before_tokenizer_save",
    "after_saved_artifact_check",
)


@pytest.fixture(autouse=True)
def strict_test_permission_mode(monkeypatch):
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
def canonical_task_db(tmp_path, monkeypatch):
    seed = Path(os.environ["LUMENIS_TEST_SEED_DB"])
    assert seed.is_file()
    db_path = tmp_path / "sealed-training-task.sqlite3"
    with sqlite3.connect(f"file:{seed.as_posix()}?mode=ro", uri=True) as source:
        with sqlite3.connect(db_path) as destination:
            source.backup(destination)
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path.resolve()))
    monkeypatch.setenv("ZBC_EVIDENCE_DB_PATH", str(db_path.resolve()))
    init_task_engine_db()
    return db_path.resolve()


@pytest.fixture
def private_key(monkeypatch):
    key_id = "sealed-training-task-test"
    value = Ed25519PrivateKey.generate()
    encoded = value.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    import base64

    monkeypatch.setenv(
        "LUMENIS_TRAINING_RECEIPT_KEY_RING",
        json.dumps({key_id: base64.b64encode(encoded).decode("ascii")}),
    )
    monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", key_id)
    return value


@pytest.fixture
def pinned_key(private_key):
    return receipts.get_training_receipt_public_key()


def _scope_context():
    return {"scope_descriptors": {"GLOBAL / ALL": {
        "domain_id": "cth",
        "product_id": "CTH",
        "global_scope": True,
        "subject_id": None,
        "brand_focus_id": None,
    }}}


def _request_data():
    return TrainingApprovalRequest(
        model_id="openai/gpt-oss-20b",
        model_revision="6cee5e81ee83917806bbde320786a8fb61efebee",
        train_sha256="1" * 64,
        heldout_sha256="2" * 64,
        domain_id="cth",
        scopes=("GLOBAL / ALL",),
        recipe="openai-h100-bf16",
        manifest_sha256="3" * 64,
    )


@pytest.fixture
def training_material(canonical_task_db, app, gate):
    request = _request_data()
    context = _scope_context()
    with app.test_request_context(
        "/", headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        principal = p.resolve_local_workspace_principal(
            module="owned_training", action="write",
        )
        assert type(principal) is p.LocalWorkspacePrincipal
        identity = p.owned_training_identity(principal=principal)
        resource = p.owned_training_approval_resource(
            request, principal=principal, domain_id="cth", context=context,
        )
        token = gate.grant_approval(
            p.OperationType.MODEL_TRAIN.value,
            resource=resource,
            granted_by="isolated-task-engine-test",
        )
        decision = gate.check(
            p.OperationType.MODEL_TRAIN,
            resource=resource,
            caller=identity["caller"],
            domain_id="cth",
            exact_approval_required=True,
        )
        reference = gate.owned_training_approval_reference(
            training_request=request,
            principal=principal,
            domain_id="cth",
            context=context,
            approval=decision,
        )
    binding = {
        "resource": resource,
        "identity": {name: identity[name] for name in (
            "actor_id", "caller", "principal_kind", "principal_ref",
        )},
        "scope_descriptors": context["scope_descriptors"],
    }
    return {
        "request": request,
        "context": context,
        "principal": principal,
        "app": app,
        "gate": gate,
        "token": token,
        "reference": reference,
        "binding": binding,
        "fingerprints": {
            "request_sha256": "a" * 64,
            "model_identity_sha256": "b" * 64,
            "manifest_sha256": "c" * 64,
            "train_sha256": "1" * 64,
            "heldout_sha256": "2" * 64,
            "recipe_sha256": "d" * 64,
            "scope_sha256": "e" * 64,
        },
    }


def _new_permission_reference(material):
    request = replace(
        material["request"],
        model_revision=material["request"].model_revision + "-replacement",
    )
    with material["app"].test_request_context(
        "/", headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        principal = p.resolve_local_workspace_principal(
            module="owned_training", action="write",
        )
        resource = p.owned_training_approval_resource(
            request, principal=principal, domain_id="cth",
            context=material["context"],
        )
        assert material["gate"].revoke_approval(material["token"]) is True
        token = material["gate"].grant_approval(
            p.OperationType.MODEL_TRAIN.value,
            resource=resource,
            granted_by="replacement-human-test",
        )
        identity = p.owned_training_identity(principal=principal)
        decision = material["gate"].check(
            p.OperationType.MODEL_TRAIN,
            resource=resource,
            caller=identity["caller"],
            domain_id="cth",
            exact_approval_required=True,
        )
        reference = material["gate"].owned_training_approval_reference(
            training_request=request, principal=principal,
            domain_id="cth", context=material["context"], approval=decision,
        )
        return {"request": request, "resource": resource, "token": token, "reference": reference}


def _connection():
    connection = get_repository().connect(timeout=10)
    connection.execute("BEGIN IMMEDIATE")
    return connection


def _create_v2(engine, material, key_pin, connection):
    return engine.create_training_receipt_task(
        binding=material["binding"],
        fingerprints=material["fingerprints"],
        approval_reference=material["reference"],
        pinned_public_key=key_pin,
        connection=connection,
    )


@pytest.fixture
def sealed_task(canonical_task_db, training_material, pinned_key):
    engine = TaskEngine()
    connection = _connection()
    try:
        state = _create_v2(engine, training_material, pinned_key, connection)
        connection.commit()
    finally:
        connection.close()
    return engine, state, training_material, pinned_key


def _phase(engine, state, material, key_pin, phase):
    connection = _connection()
    try:
        challenge = engine.prepare_training_phase_challenge(
            state["task_id"], material["binding"], material["reference"],
            key_pin, phase, connection,
        )
        signed = receipts.sign_training_phase_decision(challenge, "allow")
        receipt_sha = hashlib.sha256(receipts._canonical_json_bytes(signed)).hexdigest()
        result = engine.consume_training_phase_challenge(
            state["task_id"], expected_binding=material["binding"],
            challenge=challenge, receipt_sha256=receipt_sha,
            decision="allow", receipt=signed,
            expected_approval_reference=material["reference"],
            connection=connection,
        )
        connection.commit()
        return result, challenge, signed, receipt_sha
    finally:
        connection.close()


def _read_state(engine, state, material):
    return engine.get_training_receipt_task(
        state["task_id"], expected_binding=material["binding"],
    )


def test_v2_creation_pins_exact_permission_reference_and_public_key_without_exposing_grant(
    canonical_task_db, training_material, pinned_key,
):
    engine = TaskEngine()
    connection = _connection()
    try:
        state = _create_v2(engine, training_material, pinned_key, connection)
        assert state["status"] == "ready"
        assert state["admission_version"] == 2
        assert state["pinned_public_key"] == pinned_key
        assert state["last_phase"] is None and state["terminal"] is False
        assert set(state) == {
            "task_id", "run_digest", "task_digest", "next_sequence", "fingerprints",
            "status", "admission_version", "pinned_public_key", "last_phase", "terminal",
        }
        encoded_public = json.dumps(state, sort_keys=True)
        assert training_material["token"] not in encoded_public
        assert "approval_reference" not in encoded_public
        assert engine.require_training_receipt_admission(
            state["task_id"], training_material["binding"], training_material["reference"],
            pinned_key, connection,
        ) == state
        row = connection.execute(
            "SELECT context_json, approval_token, approved_by FROM ai_task WHERE task_id=?",
            (state["task_id"],),
        ).fetchone()
        stored = json.loads(row["context_json"])
        assert set(stored) == {
            "managed_owner", "binding", "fingerprints", "run_digest", "task_digest",
            "next_sequence", "last_receipt_sha256", "admission",
        }
        assert stored["admission"]["approval_reference"] == training_material["reference"]
        assert stored["admission"]["public_key_pin"] == pinned_key
        assert training_material["token"] not in row["context_json"]
        assert row["approval_token"] is None and row["approved_by"] is None
        connection.commit()
    finally:
        connection.close()


@pytest.mark.parametrize("missing", ["reference", "key"])
def test_v2_creation_requires_both_reference_and_public_key(
    canonical_task_db, training_material, pinned_key, missing,
):
    engine = TaskEngine()
    kwargs = {
        "binding": training_material["binding"],
        "fingerprints": training_material["fingerprints"],
    }
    if missing == "reference":
        kwargs["pinned_public_key"] = pinned_key
    else:
        kwargs["approval_reference"] = training_material["reference"]
    with pytest.raises(ValueError, match="both approval reference and public key"):
        engine.create_training_receipt_task(**kwargs)


def test_v2_creation_requires_caller_owned_canonical_transaction(
    canonical_task_db, training_material, pinned_key,
):
    engine = TaskEngine()
    with pytest.raises(RuntimeError, match="caller transaction"):
        engine.create_training_receipt_task(
            binding=training_material["binding"],
            fingerprints=training_material["fingerprints"],
            approval_reference=training_material["reference"],
            pinned_public_key=pinned_key,
        )
    connection = get_repository().connect(timeout=5)
    try:
        with pytest.raises(RuntimeError, match="active SQLite transaction"):
            _create_v2(engine, training_material, pinned_key, connection)
    finally:
        connection.close()


def test_one_grant_idempotently_returns_one_task_and_refuses_changed_material_or_key(
    canonical_task_db, training_material, pinned_key,
):
    engine = TaskEngine()
    connection = _connection()
    try:
        first = _create_v2(engine, training_material, pinned_key, connection)
        connection.commit()
    finally:
        connection.close()
    connection = _connection()
    try:
        repeated = _create_v2(engine, training_material, pinned_key, connection)
        assert repeated == first
        changed_fingerprints = dict(training_material["fingerprints"])
        changed_fingerprints["recipe_sha256"] = "f" * 64
        with pytest.raises(PermissionError, match="different task material"):
            engine.create_training_receipt_task(
                binding=training_material["binding"], fingerprints=changed_fingerprints,
                approval_reference=training_material["reference"],
                pinned_public_key=pinned_key, connection=connection,
            )
        replacement_ref = dict(training_material["reference"])
        replacement_ref["granted_by"] = "different-issuance-identity"
        with pytest.raises(PermissionError, match="different task material"):
            engine.create_training_receipt_task(
                binding=training_material["binding"],
                fingerprints=training_material["fingerprints"],
                approval_reference=replacement_ref,
                pinned_public_key=pinned_key, connection=connection,
            )
        rotated = dict(pinned_key)
        other_public = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
        )
        import base64

        rotated["public_key"] = base64.b64encode(other_public).decode("ascii")
        with pytest.raises(PermissionError, match="different task material"):
            engine.create_training_receipt_task(
                binding=training_material["binding"],
                fingerprints=training_material["fingerprints"],
                approval_reference=training_material["reference"],
                pinned_public_key=rotated, connection=connection,
            )
        rows = connection.execute(
            "SELECT COUNT(*) FROM ai_task WHERE created_by=?", (_OWNER,),
        ).fetchone()[0]
        assert rows == 1
        connection.commit()
    finally:
        connection.close()


def test_replacement_grant_cannot_reactivate_an_old_task_but_gets_its_own_task(sealed_task):
    engine, state, material, key_pin = sealed_task
    replacement_material = _new_permission_reference(material)
    replacement = replacement_material["reference"]
    assert replacement["approval_token_sha256"] != material["reference"]["approval_token_sha256"]
    new_material = dict(material)
    new_material["request"] = replacement_material["request"]
    new_material["reference"] = replacement
    new_material["binding"] = dict(material["binding"])
    new_material["binding"]["resource"] = replacement_material["resource"]
    new_material["fingerprints"] = dict(material["fingerprints"])
    new_material["fingerprints"]["request_sha256"] = "9" * 64
    connection = _connection()
    try:
        with pytest.raises(PermissionError, match="approval reference"):
            engine.require_training_receipt_admission(
                state["task_id"], material["binding"], replacement,
                key_pin, connection,
            )
        new_state = engine.create_training_receipt_task(
            binding=new_material["binding"], fingerprints=new_material["fingerprints"],
            approval_reference=replacement, pinned_public_key=key_pin,
            connection=connection,
        )
        assert new_state["task_id"] != state["task_id"]
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task WHERE created_by=?", (_OWNER,),
        ).fetchone()[0] == 2
        connection.commit()
    finally:
        connection.close()


def test_creation_fails_closed_on_malformed_existing_managed_context(
    canonical_task_db, training_material, pinned_key,
):
    connection = _connection()
    try:
        malformed_id = f"trainrelay_{uuid.uuid4()}"
        now = datetime.now().isoformat()
        connection.execute(
            """INSERT INTO ai_task
               (task_id,user_input,context_json,status,risk_level,created_at,updated_at,created_by)
               VALUES (?, ?, '{', 'ready', 'L0', ?, ?, ?)""",
            (malformed_id, "Owned training phase receipt state", now, now, _OWNER),
        )
        with pytest.raises(ValueError, match="malformed JSON"):
            _create_v2(TaskEngine(), training_material, pinned_key, connection)
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task WHERE created_by=?", (_OWNER,),
        ).fetchone()[0] == 1
        connection.commit()
    finally:
        connection.close()


def test_creation_fails_closed_when_a_grant_hash_matches_duplicate_tasks(
    canonical_task_db, training_material, pinned_key,
):
    engine = TaskEngine()
    connection = _connection()
    try:
        first = _create_v2(engine, training_material, pinned_key, connection)
        connection.commit()
    finally:
        connection.close()
    connection = _connection()
    try:
        row = connection.execute(
            "SELECT * FROM ai_task WHERE task_id=?", (first["task_id"],),
        ).fetchone()
        duplicate_id = f"trainrelay_{uuid.uuid4()}"
        duplicate_context = json.loads(row["context_json"])
        duplicate_context["task_digest"] = hashlib.sha256(
            duplicate_id.encode("utf-8")
        ).hexdigest()
        connection.execute(
            """INSERT INTO ai_task
               (task_id,user_input,context_json,status,risk_level,created_at,updated_at,created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (duplicate_id, row["user_input"], json.dumps(
                duplicate_context, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            ), row["status"], row["risk_level"], row["created_at"], row["updated_at"], row["created_by"]),
        )
        with pytest.raises(RuntimeError, match="matches multiple managed tasks"):
            _create_v2(engine, training_material, pinned_key, connection)
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task WHERE created_by=?", (_OWNER,),
        ).fetchone()[0] == 2
        connection.commit()
    finally:
        connection.close()
def test_admission_rejects_replacement_binding_reference_and_key(
    sealed_task,
):
    engine, state, material, key_pin = sealed_task
    connection = _connection()
    try:
        changed_reference = dict(material["reference"])
        changed_reference["granted_by"] = "replaced"
        with pytest.raises(PermissionError, match="approval reference"):
            engine.require_training_receipt_admission(
                state["task_id"], material["binding"], changed_reference,
                key_pin, connection,
            )
        other_binding = dict(material["binding"])
        other_binding["resource"] = "owned_training:v1:" + "f" * 64
        with pytest.raises(PermissionError, match="binding"):
            engine.require_training_receipt_admission(
                state["task_id"], other_binding, material["reference"],
                key_pin, connection,
            )
        rotated = dict(key_pin)
        rotated["key_id"] = "different-key"
        with pytest.raises(PermissionError, match="public key pin"):
            engine.require_training_receipt_admission(
                state["task_id"], material["binding"], material["reference"],
                rotated, connection,
            )
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.parametrize("phase", [
    "before_output_dir", "before_train", "step_begin", "substep_end",
    "pre_optimizer_step", "before_adapter_save", "after_saved_artifact_check",
    "unregistered",
])
def test_phase_graph_rejects_skips_or_unregistered_phases_without_writes(sealed_task, phase):
    engine, state, material, key_pin = sealed_task
    connection = _connection()
    try:
        with pytest.raises((PermissionError, ValueError)):
            engine.prepare_training_phase_challenge(
                state["task_id"], material["binding"], material["reference"],
                key_pin, phase, connection,
            )
        row = connection.execute(
            "SELECT context_json FROM ai_task WHERE task_id=?", (state["task_id"],),
        ).fetchone()
        assert json.loads(row["context_json"])["admission"]["pending_step_id"] is None
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=?", (state["task_id"],),
        ).fetchone()[0] == 0
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.parametrize(("prefix", "last_phase", "allowed"), [
    (("initial",), "initial", {"before_output_dir"}),
    (("initial", "before_output_dir"), "before_output_dir", {"before_train"}),
    (("initial", "before_output_dir", "before_train"), "before_train", {"step_begin"}),
    (("initial", "before_output_dir", "before_train", "step_begin"), "step_begin",
     {"substep_end", "pre_optimizer_step"}),
    (("initial", "before_output_dir", "before_train", "step_begin", "substep_end"),
     "substep_end", {"substep_end", "pre_optimizer_step"}),
    (("initial", "before_output_dir", "before_train", "step_begin", "pre_optimizer_step"),
     "pre_optimizer_step", {"step_begin", "before_adapter_save"}),
    (("initial", "before_output_dir", "before_train", "step_begin", "pre_optimizer_step",
      "before_adapter_save"), "before_adapter_save", {"before_tokenizer_save"}),
    (("initial", "before_output_dir", "before_train", "step_begin", "pre_optimizer_step",
      "before_adapter_save", "before_tokenizer_save"), "before_tokenizer_save",
     {"after_saved_artifact_check"}),
    (_PHASE_PATH, "after_saved_artifact_check", set()),
])
def test_every_phase_rejects_transitions_outside_the_registered_graph(
    sealed_task, prefix, last_phase, allowed,
):
    engine, state, material, key_pin = sealed_task
    current = state
    for phase in prefix:
        current, _challenge_value, _receipt, _digest = _phase(
            engine, current, material, key_pin, phase,
        )
    assert current["last_phase"] == last_phase
    connection = _connection()
    try:
        for candidate in _ALL_PHASES:
            if candidate in allowed:
                continue
            with pytest.raises(PermissionError):
                engine.prepare_training_phase_challenge(
                    current["task_id"], material["binding"], material["reference"],
                    key_pin, candidate, connection,
                )
        step_count = connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=?", (current["task_id"],),
        ).fetchone()[0]
        assert step_count == len(prefix)
        connection.commit()
    finally:
        connection.close()


def test_prepare_is_server_owned_idempotent_and_rejects_forged_pending_challenge(sealed_task):
    engine, state, material, key_pin = sealed_task
    connection = _connection()
    try:
        challenge = engine.prepare_training_phase_challenge(
            state["task_id"], material["binding"], material["reference"],
            key_pin, "initial", connection,
        )
        repeated = engine.prepare_training_phase_challenge(
            state["task_id"], material["binding"], material["reference"],
            key_pin, "initial", connection,
        )
        assert repeated == challenge
        assert set(challenge) == {
            "schema_version", "run_digest", "task_digest", "request_sha256",
            "model_identity_sha256", "manifest_sha256", "train_sha256",
            "heldout_sha256", "recipe_sha256", "scope_sha256", "nonce",
            "phase", "sequence", "issued_at", "expires_at",
        }
        assert challenge["phase"] == "initial" and challenge["sequence"] == 1
        assert len(challenge["nonce"]) == 64 and challenge["nonce"].islower()
        assert challenge["expires_at"] <= challenge["issued_at"] + 60
        assert engine.get_training_phase_receipt(
            state["task_id"], material["binding"], material["reference"],
            challenge["nonce"], connection,
        ) is None
        with pytest.raises(PermissionError):
            engine.prepare_training_phase_challenge(
                state["task_id"], material["binding"], material["reference"],
                key_pin, "before_output_dir", connection,
            )
        forged = dict(challenge)
        forged["nonce"] = "0" * 64
        with pytest.raises((PermissionError, ValueError)):
            engine.require_pending_training_phase_challenge(
                state["task_id"], material["binding"], material["reference"],
                key_pin, forged, connection,
            )
        assert engine.require_pending_training_phase_challenge(
            state["task_id"], material["binding"], material["reference"],
            key_pin, challenge, connection,
        ) == challenge
        connection.commit()
    finally:
        connection.close()


def test_prepare_caps_expiry_and_replaces_an_expired_pending_nonce_without_sequence_use(sealed_task):
    engine, state, material, key_pin = sealed_task
    connection = _connection()
    try:
        challenge = engine.prepare_training_phase_challenge(
            state["task_id"], material["binding"], material["reference"],
            key_pin, "initial", connection,
        )
        reference_expiry = int(datetime.fromisoformat(
            material["reference"]["expires_at"].replace("Z", "+00:00")
        ).timestamp())
        assert challenge["expires_at"] == min(
            challenge["issued_at"] + 60, reference_expiry,
        )
        first_step_id = "trainphase_" + hashlib.sha256(
            (state["task_id"] + challenge["nonce"]).encode("utf-8")
        ).hexdigest()
        renewed = engine.prepare_training_phase_challenge(
            state["task_id"], material["binding"], material["reference"],
            key_pin, "initial", connection, now=challenge["expires_at"],
        )
        assert renewed["nonce"] != challenge["nonce"]
        assert renewed["sequence"] == challenge["sequence"] == 1
        old_step = connection.execute(
            "SELECT status, detail FROM ai_task_step WHERE step_id=?", (first_step_id,),
        ).fetchone()
        assert old_step["status"] == "expired"
        assert json.loads(old_step["detail"]) == {"challenge": challenge}
        latest = connection.execute(
            "SELECT context_json FROM ai_task WHERE task_id=?", (state["task_id"],),
        ).fetchone()
        assert json.loads(latest["context_json"])["next_sequence"] == 1
        connection.commit()
    finally:
        connection.close()


def test_expired_approval_reference_cannot_prepare_a_phase(sealed_task):
    engine, state, material, key_pin = sealed_task
    expired_now = int(datetime.fromisoformat(
        material["reference"]["expires_at"].replace("Z", "+00:00")
    ).timestamp())
    connection = _connection()
    try:
        with pytest.raises(PermissionError, match="approval reference has expired"):
            engine.prepare_training_phase_challenge(
                state["task_id"], material["binding"], material["reference"],
                key_pin, "initial", connection, now=expired_now,
            )
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=?", (state["task_id"],),
        ).fetchone()[0] == 0
        current = json.loads(connection.execute(
            "SELECT context_json FROM ai_task WHERE task_id=?", (state["task_id"],),
        ).fetchone()[0])
        assert current["admission"]["pending_step_id"] is None
        connection.commit()
    finally:
        connection.close()


def test_signed_full_receipt_is_stored_recovered_and_same_bytes_retry_is_idempotent(sealed_task, monkeypatch):
    engine, state, material, key_pin = sealed_task
    result, challenge, signed, receipt_sha = _phase(
        engine, state, material, key_pin, "initial",
    )
    reopened_engine = TaskEngine()
    assert result["status"] == "running" and result["next_sequence"] == 2
    assert result["last_phase"] == "initial" and result["terminal"] is False
    connection = _connection()
    try:
        step_id = "trainphase_" + hashlib.sha256(
            (state["task_id"] + challenge["nonce"]).encode("utf-8")
        ).hexdigest()
        step = connection.execute(
            "SELECT phase,status,detail FROM ai_task_step WHERE step_id=?", (step_id,),
        ).fetchone()
        detail = json.loads(step["detail"])
        assert step["phase"] == "initial" and step["status"] == "allow"
        assert set(detail) == {"challenge", "receipt_sha256", "decision", "receipt"}
        assert detail["challenge"] == challenge and detail["receipt"] == signed
        assert detail["receipt_sha256"] == receipt_sha == hashlib.sha256(
            receipts._canonical_json_bytes(signed)
        ).hexdigest()
        recovered = reopened_engine.get_training_phase_receipt(
            state["task_id"], material["binding"], material["reference"],
            challenge["nonce"], connection,
        )
        assert recovered == {
            "receipt": signed,
            "challenge": challenge,
            "state": result,
            "pinned_public_key": key_pin,
        }
        connection.commit()
    finally:
        connection.close()

    monkeypatch.setattr(ai_task_engine.time, "time", lambda: signed["expires_at"] + 1)
    connection = _connection()
    try:
        replay = reopened_engine.consume_training_phase_challenge(
            state["task_id"], expected_binding=material["binding"],
            challenge=challenge, receipt_sha256=receipt_sha, decision="allow",
            receipt=signed, expected_approval_reference=material["reference"],
            connection=connection,
        )
        assert replay == result
        with pytest.raises(PermissionError, match="different receipt bytes"):
            changed = dict(signed)
            changed["signature"] = "A" * len(signed["signature"])
            changed_sha = hashlib.sha256(receipts._canonical_json_bytes(changed)).hexdigest()
            engine.consume_training_phase_challenge(
                state["task_id"], expected_binding=material["binding"],
                challenge=challenge, receipt_sha256=changed_sha, decision="allow",
                receipt=changed, expected_approval_reference=material["reference"],
                connection=connection,
            )
        assert _read_state(reopened_engine, state, material) == result
        connection.commit()
    finally:
        connection.close()


def test_forged_or_wrong_key_receipts_leave_pending_state_unchanged(sealed_task):
    engine, state, material, key_pin = sealed_task
    connection = _connection()
    try:
        challenge = engine.prepare_training_phase_challenge(
            state["task_id"], material["binding"], material["reference"],
            key_pin, "initial", connection,
        )
        connection.commit()
    finally:
        connection.close()
    signed = receipts.sign_training_phase_decision(challenge, "allow")
    tampered = dict(signed)
    tampered["phase"] = "before_train"
    denied = receipts.sign_training_phase_decision(challenge, "deny")
    denied_digest = hashlib.sha256(receipts._canonical_json_bytes(denied)).hexdigest()
    altered_key = dict(key_pin)
    other = Ed25519PrivateKey.generate().public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
    )
    import base64

    altered_key["public_key"] = base64.b64encode(other).decode("ascii")
    connection = _connection()
    try:
        with pytest.raises(ValueError, match="complete signed receipt"):
            engine.consume_training_phase_challenge(
                state["task_id"], expected_binding=material["binding"],
                challenge=challenge, receipt_sha256="0" * 64, decision="allow",
                receipt=signed, expected_approval_reference=material["reference"],
                connection=connection,
            )
        with pytest.raises(PermissionError, match="must verify an allow decision"):
            engine.consume_training_phase_challenge(
                state["task_id"], expected_binding=material["binding"],
                challenge=challenge, receipt_sha256=denied_digest,
                decision="deny", receipt=denied,
                expected_approval_reference=material["reference"],
                connection=connection,
            )
        with pytest.raises(PermissionError, match="public key pin"):
            engine.require_pending_training_phase_challenge(
                state["task_id"], material["binding"], material["reference"],
                altered_key, challenge, connection,
            )
        with pytest.raises(ValueError):
            engine.consume_training_phase_challenge(
                state["task_id"], expected_binding=material["binding"],
                challenge=challenge, receipt_sha256=hashlib.sha256(
                    receipts._canonical_json_bytes(tampered)
                ).hexdigest(), decision="allow", receipt=tampered,
                expected_approval_reference=material["reference"],
                connection=connection,
            )
        check = connection.execute(
            "SELECT context_json FROM ai_task WHERE task_id=?", (state["task_id"],),
        ).fetchone()
        assert json.loads(check["context_json"])["admission"]["pending_step_id"]
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=? AND status='allow'",
            (state["task_id"],),
        ).fetchone()[0] == 0
        connection.commit()
    finally:
        connection.close()


def test_all_registered_phase_transitions_and_terminal_reuse(sealed_task):
    engine, state, material, key_pin = sealed_task
    current = state
    for next_phase in _PHASE_PATH:
        current, _challenge_value, _receipt, _digest = _phase(
            engine, current, material, key_pin, next_phase,
        )
    assert current["status"] == "completed"
    assert current["terminal"] is True
    assert current["last_phase"] == "after_saved_artifact_check"
    assert current["next_sequence"] == len(_PHASE_PATH) + 1
    connection = _connection()
    try:
        reused = _create_v2(engine, material, key_pin, connection)
        assert reused == current
        with pytest.raises(PermissionError):
            engine.prepare_training_phase_challenge(
                current["task_id"], material["binding"], material["reference"],
                key_pin, "initial", connection,
            )
        connection.commit()
    finally:
        connection.close()


def test_interruption_marks_pending_nonce_and_resume_preserves_history_but_rotates_epoch(sealed_task):
    engine, state, material, key_pin = sealed_task
    accepted, first_challenge, first_receipt, _ = _phase(
        engine, state, material, key_pin, "initial",
    )
    connection = _connection()
    try:
        pending = engine.prepare_training_phase_challenge(
            state["task_id"], material["binding"], material["reference"],
            key_pin, "before_output_dir", connection,
        )
        connection.commit()
    finally:
        connection.close()
    connection = _connection()
    try:
        interrupted = engine.interrupt_training_receipt_task(
            state["task_id"], expected_binding=material["binding"], connection=connection,
        )
        assert interrupted["status"] == "unknown"
        assert interrupted["next_sequence"] == accepted["next_sequence"] == 2
        assert interrupted["last_phase"] == "initial"
        assert interrupted["terminal"] is False
        old_step_id = "trainphase_" + hashlib.sha256(
            (state["task_id"] + pending["nonce"]).encode("utf-8")
        ).hexdigest()
        old_step = connection.execute(
            "SELECT status,detail FROM ai_task_step WHERE step_id=?", (old_step_id,),
        ).fetchone()
        assert old_step["status"] == "interrupted"
        assert json.loads(old_step["detail"]) == {"challenge": pending}
        unknown_context = json.loads(connection.execute(
            "SELECT context_json FROM ai_task WHERE task_id=?", (state["task_id"],),
        ).fetchone()[0])
        assert unknown_context["admission"]["pending_step_id"] is None
        resumed = engine.resume_training_receipt_task(
            state["task_id"], expected_binding=material["binding"], connection=connection,
        )
        assert resumed["status"] == "ready"
        assert resumed["next_sequence"] == 2 and resumed["last_phase"] == "initial"
        assert resumed["run_digest"] != accepted["run_digest"]
        with pytest.raises((PermissionError, ValueError)):
            engine.require_pending_training_phase_challenge(
                state["task_id"], material["binding"], material["reference"],
                key_pin, pending, connection,
            )
        recovered = engine.get_training_phase_receipt(
            state["task_id"], material["binding"], material["reference"],
            first_challenge["nonce"], connection,
        )
        assert recovered["receipt"] == first_receipt
        fresh = engine.prepare_training_phase_challenge(
            state["task_id"], material["binding"], material["reference"],
            key_pin, "before_output_dir", connection,
        )
        assert fresh["nonce"] != pending["nonce"]
        assert fresh["run_digest"] == resumed["run_digest"]
        assert fresh["sequence"] == 2
        connection.commit()
    finally:
        connection.close()


def test_caller_rollback_restores_full_pending_state_and_receipt_write_savepoint(sealed_task):
    engine, state, material, key_pin = sealed_task
    connection = _connection()
    try:
        challenge = engine.prepare_training_phase_challenge(
            state["task_id"], material["binding"], material["reference"],
            key_pin, "initial", connection,
        )
        connection.rollback()
    finally:
        connection.close()
    reopened = _read_state(engine, state, material)
    assert reopened["next_sequence"] == 1 and reopened["last_phase"] is None
    connection = _connection()
    try:
        with pytest.raises(PermissionError):
            engine.require_pending_training_phase_challenge(
                state["task_id"], material["binding"], material["reference"],
                key_pin, challenge, connection,
            )
        count = connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=?", (state["task_id"],),
        ).fetchone()[0]
        assert count == 0
        challenge = engine.prepare_training_phase_challenge(
            state["task_id"], material["binding"], material["reference"],
            key_pin, "initial", connection,
        )
        signed = receipts.sign_training_phase_decision(challenge, "allow")
        digest = hashlib.sha256(receipts._canonical_json_bytes(signed)).hexdigest()
        connection.execute(
            """CREATE TRIGGER deny_sealed_task_update BEFORE UPDATE ON ai_task
               WHEN OLD.task_id = '%s' BEGIN SELECT RAISE(ABORT, 'injected task update failure'); END"""
            % state["task_id"]
        )
        with pytest.raises(sqlite3.IntegrityError, match="injected task update failure"):
            engine.consume_training_phase_challenge(
                state["task_id"], expected_binding=material["binding"],
                challenge=challenge, receipt_sha256=digest, decision="allow",
                receipt=signed, expected_approval_reference=material["reference"],
                connection=connection,
            )
        step_id = "trainphase_" + hashlib.sha256(
            (state["task_id"] + challenge["nonce"]).encode("utf-8")
        ).hexdigest()
        step = connection.execute(
            "SELECT status,detail FROM ai_task_step WHERE step_id=?", (step_id,),
        ).fetchone()
        assert step["status"] == "pending"
        assert json.loads(step["detail"]) == {"challenge": challenge}
        current = connection.execute(
            "SELECT context_json,status FROM ai_task WHERE task_id=?", (state["task_id"],),
        ).fetchone()
        assert current["status"] == "ready"
        assert json.loads(current["context_json"])["admission"]["pending_step_id"] == step_id
        connection.execute("DROP TRIGGER deny_sealed_task_update")
        connection.rollback()
    finally:
        connection.close()
    after_rollback = _read_state(engine, state, material)
    assert after_rollback["next_sequence"] == 1 and after_rollback["status"] == "ready"
    with get_repository().connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=?", (state["task_id"],),
        ).fetchone()[0] == 0


def test_committed_receipt_detail_tampering_fails_recovery(sealed_task):
    engine, state, material, key_pin = sealed_task
    _result, challenge, signed, _digest = _phase(engine, state, material, key_pin, "initial")
    step_id = "trainphase_" + hashlib.sha256(
        (state["task_id"] + challenge["nonce"]).encode("utf-8")
    ).hexdigest()
    connection = _connection()
    try:
        detail = json.loads(connection.execute(
            "SELECT detail FROM ai_task_step WHERE step_id=?", (step_id,),
        ).fetchone()[0])
        detail["receipt"]["signature"] = "A" * len(signed["signature"])
        connection.execute(
            "UPDATE ai_task_step SET detail=? WHERE step_id=?",
            (json.dumps(detail, sort_keys=True, separators=(",", ":")), step_id),
        )
        with pytest.raises(ValueError, match="historical verification"):
            engine.get_training_phase_receipt(
                state["task_id"], material["binding"], material["reference"],
                challenge["nonce"], connection,
            )
        connection.rollback()
    finally:
        connection.close()


def test_wrong_binding_and_old_generic_task_guards_remain_effective(sealed_task):
    engine, state, material, key_pin = sealed_task
    changed = dict(material["binding"])
    changed["scope_descriptors"] = {}
    with pytest.raises(ValueError):
        engine.get_training_receipt_task(state["task_id"], expected_binding=changed)
    for method in (
        "get_task", "get_steps", "get_evidence", "parse_task", "select_agent_and_skill",
        "check_permission", "execute_task", "approve_task", "cancel_task", "run_task", "get_trace",
    ):
        with pytest.raises(PermissionError, match="training receipt tasks"):
            getattr(engine, method)(state["task_id"])
    assert all(item["task_id"] != state["task_id"] for item in engine.list_tasks())


def test_concurrent_same_grant_creation_and_phase_prepare_converge_to_one_task_and_nonce(
    canonical_task_db, training_material, pinned_key,
):
    engine = TaskEngine()
    barrier = threading.Barrier(2)
    results = []
    errors = []

    def create_worker():
        connection = None
        try:
            connection = get_repository().connect(timeout=10)
            barrier.wait(timeout=5)
            connection.execute("BEGIN IMMEDIATE")
            results.append(_create_v2(engine, training_material, pinned_key, connection))
            connection.commit()
        except Exception as exc:
            errors.append(exc)
            if connection is not None:
                connection.rollback()
        finally:
            if connection is not None:
                connection.close()

    workers = [threading.Thread(target=create_worker) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=12)
    assert all(not worker.is_alive() for worker in workers)
    assert not errors
    assert len(results) == 2 and results[0]["task_id"] == results[1]["task_id"]
    state = results[0]

    barrier = threading.Barrier(2)
    challenges = []
    errors.clear()

    def prepare_worker():
        connection = None
        try:
            connection = get_repository().connect(timeout=10)
            barrier.wait(timeout=5)
            connection.execute("BEGIN IMMEDIATE")
            challenges.append(engine.prepare_training_phase_challenge(
                state["task_id"], training_material["binding"], training_material["reference"],
                pinned_key, "initial", connection,
            ))
            connection.commit()
        except Exception as exc:
            errors.append(exc)
            if connection is not None:
                connection.rollback()
        finally:
            if connection is not None:
                connection.close()

    workers = [threading.Thread(target=prepare_worker) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=12)
    assert all(not worker.is_alive() for worker in workers)
    assert not errors
    assert len(challenges) == 2 and challenges[0] == challenges[1]
    with get_repository().connection() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task WHERE created_by=?", (_OWNER,),
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_task_step WHERE task_id=? AND status='pending'",
            (state["task_id"],),
        ).fetchone()[0] == 1
