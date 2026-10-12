"""Real cryptographic/isolated Task checks; no GPU or model quality claim."""
import base64
import copy
from datetime import datetime, timezone
import json
import pickle
import time
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from lumenis.system.security import training_receipts as r


@pytest.fixture
def signing(monkeypatch):
    private = Ed25519PrivateKey.generate()
    raw = private.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                serialization.NoEncryption())
    monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", json.dumps({"checkpoint-test": base64.b64encode(raw).decode()}))
    monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", "checkpoint-test")
    return r.get_training_receipt_public_key()


def admission_payload():
    return {"operation_id": str(uuid.uuid4()), "task_digest": "a" * 64, "run_digest": "b" * 64,
        "attempt_id": str(uuid.uuid4()), "worker_epoch": 1, "operation": "save", "completed_step": 1,
        "checkpoint_ref": None, "checkpoint_sha256": None, "policy_sha256": "c" * 64,
        "fingerprints": {key: "d" * 64 for key in r._CHECKPOINT_FINGERPRINT_KEYS}, "reservation_digest": "e" * 64}


def test_verified_admission_is_detached_immutable_and_not_checkpoint_state(signing):
    payload = admission_payload()
    envelope = r.sign_training_checkpoint_payload(payload, receipt_kind="owned_training_checkpoint_admission")
    verified = r.verify_training_checkpoint_admission(envelope, expected_payload=payload, pinned_public_key=signing)
    assert type(verified) is r.VerifiedTrainingCheckpointAdmission
    detached = verified.envelope
    detached["payload"]["fingerprints"]["train_sha256"] = "0" * 64
    assert verified.envelope == envelope
    with pytest.raises(AttributeError):
        verified.envelope = detached
    with pytest.raises(AttributeError):
        verified._canonical_envelope = b"{}"
    with pytest.raises(TypeError):
        pickle.dumps(verified)
    with pytest.raises(r.TrainingReceiptError):
        r.VerifiedTrainingCheckpointAdmission(envelope)


@pytest.mark.parametrize("change", [
    ("worker_epoch", True), ("completed_step", False), ("completed_step", -1),
    ("operation", "inference"), ("operation", []), ("operation_id", "not-a-uuid"),
    ("attempt_id", "00000000-0000-0000-0000-000000000000"), ("task_digest", "A" * 64),
    ("run_digest", "short"), ("checkpoint_ref", "ART-" + "0" * 16),
    ("checkpoint_sha256", "0" * 64), ("policy_sha256", None), ("reservation_digest", "x" * 64),
    ("fingerprints", {}), ("fingerprints", {**{k: "1" * 64 for k in r._CHECKPOINT_FINGERPRINT_KEYS}, "extra": "1" * 64}),
])
def test_signer_rejects_malformed_admission_before_minting(signing, change):
    payload = admission_payload()
    payload[change[0]] = change[1]
    with pytest.raises(r.TrainingReceiptError):
        r.sign_training_checkpoint_payload(payload, receipt_kind="owned_training_checkpoint_admission")


@pytest.mark.parametrize("field", sorted(r._CHECKPOINT_ADMISSION_KEYS))
def test_current_exact_binding_cannot_be_changed(signing, field):
    payload = admission_payload()
    envelope = r.sign_training_checkpoint_payload(payload, receipt_kind="owned_training_checkpoint_admission")
    changed = copy.deepcopy(payload)
    if field in {"operation_id", "attempt_id"}:
        changed[field] = str(uuid.uuid4())
    elif field == "fingerprints":
        changed[field]["heldout_sha256"] = "f" * 64
    elif field in {"worker_epoch", "completed_step"}:
        changed[field] += 1
    elif field in {"operation", "checkpoint_ref", "checkpoint_sha256"}:
        changed.update(operation="load", checkpoint_ref="ART-" + "f" * 16, checkpoint_sha256="f" * 64)
    else:
        changed[field] = "f" * 64
    with pytest.raises(r.TrainingReceiptError):
        r.verify_training_checkpoint_admission(envelope, expected_payload=changed, pinned_public_key=signing)


@pytest.mark.parametrize("mutation", ["extra", "future", "expired", "signature", "kind", "hash", "bool-schema", "no-expiry"])
def test_envelope_tampering_or_stale_start_denies(signing, mutation):
    now = int(time.time())
    payload = admission_payload()
    envelope = r.sign_training_checkpoint_payload(payload, receipt_kind="owned_training_checkpoint_admission", now=now)
    if mutation == "extra": envelope["extra"] = 1
    elif mutation == "future": envelope["issued_at"] = now + 1
    elif mutation == "expired": now += 30
    elif mutation == "signature": envelope["signature"] = base64.b64encode(b"x" * 64).decode()
    elif mutation == "kind": envelope["receipt_kind"] = "owned_training_checkpoint_committed"
    elif mutation == "hash": envelope["payload_sha256"] = "f" * 64
    elif mutation == "bool-schema": envelope["schema_version"] = True
    elif mutation == "no-expiry": envelope["expires_at"] = None
    with pytest.raises(r.TrainingReceiptError):
        r.verify_training_checkpoint_admission(envelope, expected_payload=payload, pinned_public_key=signing, now=now)


def test_committed_signature_is_historical_and_cannot_start_io(signing):
    payload = admission_payload()
    record = {"schema_version": 1, "operation_id": payload["operation_id"], "task_digest": payload["task_digest"],
        "origin_run_digest": payload["run_digest"], "attempt_id": payload["attempt_id"],
        "worker_epoch": 1, "fingerprints": payload["fingerprints"], "policy_sha256": payload["policy_sha256"],
        "completed_step": 1, "artifact_ref": "ART-" + "a" * 16, "artifact_version": 1, "parent_ref": None,
        "inventory_sha256": "3" * 64, "artifact_sha256": "4" * 64, "storage_identity": "training-storage-1",
        "committed_at_utc": datetime.now(timezone.utc).isoformat(), "task_step_ref": "trainop_" + "5" * 64}
    envelope = r.sign_training_checkpoint_payload(record, receipt_kind="owned_training_checkpoint_committed", now=int(time.time()) - 3600)
    verified = r.verify_training_checkpoint_receipt(envelope, expected_payload=record, pinned_public_key=signing)
    assert type(verified) is r.VerifiedTrainingCheckpointReceipt and envelope["expires_at"] is None
    with pytest.raises(r.TrainingReceiptError):
        r.verify_training_checkpoint_admission(envelope, expected_payload=payload, pinned_public_key=signing)


def test_existing_phase_verifier_rejects_checkpoint_schema(signing):
    payload = admission_payload()
    envelope = r.sign_training_checkpoint_payload(payload, receipt_kind="owned_training_checkpoint_admission")
    with pytest.raises(r.TrainingReceiptError):
        r.verify_training_phase_decision(envelope, expected_challenge={}, pinned_public_key=signing)
