"""Private readback contract for sealed owned-training task history material."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

import ai_task_engine
from ai_task_engine import TaskEngine, init_task_engine_db
from lumenis.shared.database import get_repository


_OWNER = "owned_training_phase_receipts:v1"
_USER_INPUT = "Owned training phase receipt state"


@pytest.fixture
def canonical_task_db(tmp_path, monkeypatch, request):
    # This history contract needs a new empty Task store, independently of the
    # schema-populated seed used by the rest of the clean-checkout suite.
    seed = (tmp_path / "empty-history-seed.sqlite3").resolve()
    seed.touch(exist_ok=False)
    assert seed.is_relative_to(Path(tempfile.gettempdir()).resolve())
    assert seed != (Path(__file__).resolve().parents[1] / "data/monitor.db").resolve()
    assert seed.is_file() and seed.stat().st_size == 0
    db_path = (tmp_path / "training-history-canonical.sqlite3").resolve()
    db_path.write_bytes(seed.read_bytes())
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("ZBC_EVIDENCE_DB_PATH", str(db_path))
    init_task_engine_db()
    request.node.user_properties.append(("canonical_task_db_path", str(db_path)))
    return db_path


def _identity(actor_id):
    if actor_id is None:
        return {
            "actor_id": None,
            "caller": "workspace:local",
            "principal_kind": "local_workspace",
            "principal_ref": "workspace:local",
        }
    return {
        "actor_id": actor_id,
        "caller": f"actor:{actor_id}",
        "principal_kind": None,
        "principal_ref": None,
    }


def _binding(actor_id):
    return {
        "resource": "owned_training:v1:" + "a" * 64,
        "identity": _identity(actor_id),
        "scope_descriptors": {
            "GLOBAL / ALL": {
                "domain_id": "cth",
                "product_id": "CTH",
                "global_scope": True,
                "subject_id": None,
                "brand_focus_id": None,
            },
        },
    }


def _fingerprints():
    return {
        "request_sha256": "1" * 64,
        "model_identity_sha256": "2" * 64,
        "manifest_sha256": "3" * 64,
        "train_sha256": "4" * 64,
        "heldout_sha256": "5" * 64,
        "recipe_sha256": "6" * 64,
        "scope_sha256": "7" * 64,
    }


def _approval_reference(resource):
    return {
        "schema_version": 1,
        "operation": "model_train",
        "resource": resource,
        "approval_token_sha256": hashlib.sha256(b"test-only approval token").hexdigest(),
        "issuance_audit_id": "aud_0123456789abcdef",
        "granted_by": "test-only-existing-grant-owner",
        "granted_at": "2026-10-01T00:00:00+00:00",
        "expires_at": "2026-10-03T00:00:00+00:00",
    }


def _public_key_pin():
    public = Ed25519PrivateKey.generate().public_key()
    raw = public.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {
        "schema_version": 1,
        "key_id": "history-material-test",
        "algorithm": "Ed25519",
        "public_key": base64.b64encode(raw).decode("ascii"),
    }


def _create(engine, actor_id):
    binding = _binding(actor_id)
    reference = _approval_reference(binding["resource"])
    connection = get_repository().connect(timeout=10)
    try:
        connection.execute("BEGIN IMMEDIATE")
        state = engine.create_training_receipt_task(
            binding=binding,
            fingerprints=_fingerprints(),
            approval_reference=reference,
            pinned_public_key=_public_key_pin(),
            connection=connection,
        )
        connection.commit()
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
    return state, binding, reference


def _begin_read():
    connection = get_repository().connect(timeout=10)
    connection.execute("BEGIN")
    return connection


def _file_snapshot(db_path):
    result = {}
    for path in (db_path, Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm")):
        if path.exists():
            result[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            result[path.name] = None
    return result


def _snapshot(connection, db_path, task_id):
    row = connection.execute("SELECT * FROM ai_task WHERE task_id=?", (task_id,)).fetchone()
    steps = connection.execute(
        "SELECT * FROM ai_task_step WHERE task_id=? ORDER BY step_id", (task_id,),
    ).fetchall()
    counts = {}
    for table in ("ai_task", "ai_task_step", "ai_task_evidence", "ai_task_trace"):
        counts[table] = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    sequence = None
    status = None
    if row is not None:
        status = row["status"]
        try:
            sequence = json.loads(row["context_json"]).get("next_sequence")
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return {
        "task_row": None if row is None else tuple(row),
        "step_rows": tuple(tuple(step) for step in steps),
        "table_counts": counts,
        "status": status,
        "next_sequence": sequence,
        "connection_changes": connection.total_changes,
        "database_files": _file_snapshot(db_path),
    }


def _unchanged_around(connection, db_path, task_id, action):
    before = _snapshot(connection, db_path, task_id)
    result = None
    try:
        result = action()
    finally:
        assert _snapshot(connection, db_path, task_id) == before
        assert connection.in_transaction
    return result


@pytest.mark.parametrize("actor_id", [41, None], ids=["account", "workspace"])
def test_returns_exact_private_material_as_deep_copies_without_writes(canonical_task_db, actor_id):
    engine = TaskEngine()
    state, binding, reference = _create(engine, actor_id)
    connection = _begin_read()
    try:
        returned = _unchanged_around(
            connection, canonical_task_db, state["task_id"],
            lambda: engine.get_training_receipt_history_material(
                state["task_id"], expected_identity=_identity(actor_id), connection=connection,
            ),
        )
        assert set(returned) == {
            "binding", "fingerprints", "approval_reference", "pinned_public_key",
        }
        assert returned["binding"] == binding
        assert returned["fingerprints"] == _fingerprints()
        assert returned["approval_reference"] == reference
        assert "approval_token" not in returned["approval_reference"]
        assert returned["pinned_public_key"]["algorithm"] == "Ed25519"
        returned["binding"]["scope_descriptors"]["GLOBAL / ALL"]["product_id"] = "MUTATED"
        returned["fingerprints"]["request_sha256"] = "f" * 64
        returned["approval_reference"]["approval_token_sha256"] = "e" * 64
        returned["pinned_public_key"]["public_key"] = "MUTATED"
        again = _unchanged_around(
            connection, canonical_task_db, state["task_id"],
            lambda: engine.get_training_receipt_history_material(
                state["task_id"], expected_identity=_identity(actor_id), connection=connection,
            ),
        )
        assert again["binding"] == binding
        assert again["fingerprints"] == _fingerprints()
        assert again["approval_reference"] == reference
        assert again["pinned_public_key"]["algorithm"] == "Ed25519"
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.parametrize("identity, error", [
    (_identity(42), PermissionError),
    ({**_identity(41), "unexpected": "field"}, ValueError),
    ({"actor_id": 41, "caller": "workspace:local", "principal_kind": None, "principal_ref": None}, ValueError),
])
def test_rejects_wrong_or_malformed_identity_without_changes(canonical_task_db, identity, error):
    engine = TaskEngine()
    state, _, _ = _create(engine, 41)
    connection = _begin_read()
    try:
        with pytest.raises(error):
            _unchanged_around(
                connection, canonical_task_db, state["task_id"],
                lambda: engine.get_training_receipt_history_material(
                    state["task_id"], expected_identity=identity, connection=connection,
                ),
            )
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.parametrize("damage, error", [
    ("malformed_json", ValueError),
    ("legacy_v1", ValueError),
    ("wrong_schema", ValueError),
    ("wrong_owner", KeyError),
])
def test_rejects_malformed_legacy_schema_and_wrong_owner_rows_without_changes(
    canonical_task_db, damage, error,
):
    engine = TaskEngine()
    state, _, _ = _create(engine, 41)
    connection = get_repository().connect(timeout=10)
    try:
        connection.execute("BEGIN IMMEDIATE")
        if damage == "malformed_json":
            connection.execute("UPDATE ai_task SET context_json=? WHERE task_id=?", ("{bad", state["task_id"]))
        elif damage == "legacy_v1":
            row = connection.execute("SELECT context_json FROM ai_task WHERE task_id=?", (state["task_id"],)).fetchone()
            value = json.loads(row["context_json"])
            value.pop("admission")
            connection.execute("UPDATE ai_task SET context_json=? WHERE task_id=?", (json.dumps(value), state["task_id"]))
        elif damage == "wrong_schema":
            row = connection.execute("SELECT context_json FROM ai_task WHERE task_id=?", (state["task_id"],)).fetchone()
            value = json.loads(row["context_json"])
            value["admission"]["schema_version"] = 1
            connection.execute("UPDATE ai_task SET context_json=? WHERE task_id=?", (json.dumps(value), state["task_id"]))
        else:
            connection.execute("UPDATE ai_task SET created_by=? WHERE task_id=?", ("other_owner", state["task_id"]))
        connection.commit()
    finally:
        connection.close()

    connection = _begin_read()
    try:
        with pytest.raises(error):
            _unchanged_around(
                connection, canonical_task_db, state["task_id"],
                lambda: engine.get_training_receipt_history_material(
                    state["task_id"], expected_identity=_identity(41), connection=connection,
                ),
            )
    finally:
        connection.rollback()
        connection.close()


@pytest.mark.parametrize("task_id, error", [
    ("trainrelay_not-a-uuid", ValueError),
    ("trainrelay_00000000-0000-4000-8000-000000000001", KeyError),
])
def test_rejects_malformed_or_missing_task_ids_without_changes(canonical_task_db, task_id, error):
    engine = TaskEngine()
    connection = _begin_read()
    try:
        with pytest.raises(error):
            _unchanged_around(
                connection, canonical_task_db, task_id,
                lambda: engine.get_training_receipt_history_material(
                    task_id, expected_identity=_identity(41), connection=connection,
                ),
            )
    finally:
        connection.rollback()
        connection.close()


def test_requires_active_transaction_on_canonical_connection(canonical_task_db, tmp_path):
    engine = TaskEngine()
    state, _, _ = _create(engine, 41)
    connection = get_repository().connect(timeout=10)
    before = _file_snapshot(canonical_task_db)
    try:
        with pytest.raises(RuntimeError, match="active SQLite transaction"):
            engine.get_training_receipt_history_material(
                state["task_id"], expected_identity=_identity(41), connection=connection,
            )
        assert not connection.in_transaction
        assert _file_snapshot(canonical_task_db) == before
        assert connection.total_changes == 0
    finally:
        connection.close()

    wrong_path = tmp_path / "noncanonical.sqlite3"
    wrong = sqlite3.connect(wrong_path)
    wrong.execute("BEGIN")
    wrong_before = _file_snapshot(wrong_path)
    try:
        with pytest.raises(RuntimeError, match="canonical TaskEngine database"):
            engine.get_training_receipt_history_material(
                state["task_id"], expected_identity=_identity(41), connection=wrong,
            )
        assert wrong.in_transaction
        assert _file_snapshot(wrong_path) == wrong_before
        assert wrong.total_changes == 0
    finally:
        wrong.rollback()
        wrong.close()
