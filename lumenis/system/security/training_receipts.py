# -*- coding: utf-8 -*-
"""Narrow Ed25519 signing and verification for training phase receipts.

This module signs a derivative decision receipt. It does not check Permission,
admit a training task, or provide replay storage; callers own those controls.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class TrainingReceiptError(ValueError):
    """Base class for rejected training receipt inputs."""


class TrainingReceiptConfigurationError(TrainingReceiptError):
    """Signing configuration is absent or invalid."""


class TrainingReceiptVerificationError(TrainingReceiptError):
    """A public receipt or its binding could not be verified."""


_KEY_RING_ENV = "LUMENIS_TRAINING_RECEIPT_KEY_RING"
_ACTIVE_KEY_ENV = "LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID"
_KEY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_LOWER_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PHASES = frozenset({
    "initial",
    "before_output_dir",
    "before_train",
    "step_begin",
    "substep_end",
    "pre_optimizer_step",
    "before_adapter_save",
    "before_tokenizer_save",
    "after_saved_artifact_check",
})
_CHALLENGE_KEYS = frozenset({
    "schema_version", "run_digest", "task_digest", "request_sha256",
    "model_identity_sha256", "manifest_sha256", "train_sha256",
    "heldout_sha256", "recipe_sha256", "scope_sha256", "nonce", "phase",
    "sequence", "issued_at", "expires_at",
})
_CHALLENGE_BINDING_KEYS = (
    "run_digest", "task_digest", "request_sha256", "model_identity_sha256",
    "manifest_sha256", "train_sha256", "heldout_sha256", "recipe_sha256",
    "scope_sha256", "nonce", "phase", "sequence",
)
_RECEIPT_KEYS = frozenset({
    "schema_version", *_CHALLENGE_BINDING_KEYS, "challenge_sha256", "decision",
    "issued_at", "expires_at", "key_id", "signature",
})
_PUBLIC_KEY_KEYS = frozenset({"schema_version", "key_id", "algorithm", "public_key"})
_RECEIPT_TTL_SECONDS = 30
_CHALLENGE_TTL_SECONDS = 60


def _now_seconds(now: Optional[int]) -> int:
    if now is None:
        return int(time.time())
    if type(now) is not int or now <= 0:
        raise TrainingReceiptError("TRAINING_RECEIPT_TIME_INVALID")
    return now


def _canonical_json_bytes(value: Dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise TrainingReceiptError("TRAINING_RECEIPT_CANONICAL_JSON_INVALID") from None


def _decode_canonical_base64(value: Any, *, size: int, error_code: str) -> bytes:
    if type(value) is not str:
        raise TrainingReceiptError(error_code)
    try:
        encoded = value.encode("ascii")
        decoded = base64.b64decode(encoded, validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError):
        raise TrainingReceiptError(error_code) from None
    if len(decoded) != size or base64.b64encode(decoded).decode("ascii") != value:
        raise TrainingReceiptError(error_code)
    return decoded


def _valid_key_id(value: Any) -> bool:
    return type(value) is str and _KEY_ID.fullmatch(value) is not None


def _reject_duplicate_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_json_constant(_value):
    raise ValueError("non-standard JSON constant")


def _load_active_private_key():
    ring_text = os.environ.get(_KEY_RING_ENV)
    active_key_id = os.environ.get(_ACTIVE_KEY_ENV)
    if (type(ring_text) is not str or not ring_text or len(ring_text) > 65536
            or not _valid_key_id(active_key_id)):
        raise TrainingReceiptConfigurationError("TRAINING_RECEIPT_SIGNING_CONFIG_INVALID")
    try:
        key_ring = json.loads(
            ring_text,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_json_constant,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        raise TrainingReceiptConfigurationError("TRAINING_RECEIPT_SIGNING_CONFIG_INVALID") from None
    if type(key_ring) is not dict or not key_ring or len(key_ring) > 64:
        raise TrainingReceiptConfigurationError("TRAINING_RECEIPT_SIGNING_CONFIG_INVALID")
    decoded_keys = {}
    for key_id, encoded_key in key_ring.items():
        if not _valid_key_id(key_id):
            raise TrainingReceiptConfigurationError("TRAINING_RECEIPT_SIGNING_CONFIG_INVALID")
        try:
            decoded_keys[key_id] = _decode_canonical_base64(
                encoded_key, size=32, error_code="TRAINING_RECEIPT_SIGNING_CONFIG_INVALID",
            )
        except TrainingReceiptError:
            raise TrainingReceiptConfigurationError("TRAINING_RECEIPT_SIGNING_CONFIG_INVALID") from None
    private_bytes = decoded_keys.get(active_key_id)
    if private_bytes is None:
        raise TrainingReceiptConfigurationError("TRAINING_RECEIPT_SIGNING_CONFIG_INVALID")
    try:
        private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
    except (TypeError, ValueError):
        raise TrainingReceiptConfigurationError("TRAINING_RECEIPT_SIGNING_CONFIG_INVALID") from None
    return active_key_id, private_key


def _public_key_dict(key_id: str, public_key: Ed25519PublicKey) -> Dict[str, Any]:
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {
        "schema_version": 1,
        "key_id": key_id,
        "algorithm": "Ed25519",
        "public_key": base64.b64encode(raw).decode("ascii"),
    }


def get_training_receipt_public_key() -> Dict[str, Any]:
    """Return public verification material for the configured active key only."""
    key_id, private_key = _load_active_private_key()
    return _public_key_dict(key_id, private_key.public_key())


def validate_training_phase_challenge(challenge, *, now: Optional[int] = None) -> Dict[str, Any]:
    """Validate and copy the exact signed challenge schema and its short TTL."""
    current_time = _now_seconds(now)
    if type(challenge) is not dict or frozenset(challenge) != _CHALLENGE_KEYS:
        raise TrainingReceiptError("TRAINING_PHASE_CHALLENGE_SCHEMA_INVALID")
    value = dict(challenge)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise TrainingReceiptError("TRAINING_PHASE_CHALLENGE_SCHEMA_INVALID")
    for name in (
        "run_digest", "task_digest", "request_sha256", "model_identity_sha256",
        "manifest_sha256", "train_sha256", "heldout_sha256", "recipe_sha256",
        "scope_sha256", "nonce",
    ):
        if type(value[name]) is not str or _LOWER_SHA256.fullmatch(value[name]) is None:
            raise TrainingReceiptError("TRAINING_PHASE_CHALLENGE_BINDING_INVALID")
    if type(value["phase"]) is not str or value["phase"] not in _PHASES:
        raise TrainingReceiptError("TRAINING_PHASE_CHALLENGE_PHASE_INVALID")
    if type(value["sequence"]) is not int or not 1 <= value["sequence"] <= 1_000_000_000:
        raise TrainingReceiptError("TRAINING_PHASE_CHALLENGE_SEQUENCE_INVALID")
    issued_at = value["issued_at"]
    expires_at = value["expires_at"]
    if (type(issued_at) is not int or type(expires_at) is not int
            or issued_at <= 0 or expires_at <= issued_at
            or expires_at - issued_at > _CHALLENGE_TTL_SECONDS
            or issued_at > current_time or current_time >= expires_at):
        raise TrainingReceiptError("TRAINING_PHASE_CHALLENGE_TIME_INVALID")
    return value


def sign_training_phase_decision(challenge, decision, *, now: Optional[int] = None) -> Dict[str, Any]:
    """Sign a derivative allow/deny receipt without performing any admission."""
    current_time = _now_seconds(now)
    validated = validate_training_phase_challenge(challenge, now=current_time)
    if type(decision) is not str or decision not in {"allow", "deny"}:
        raise TrainingReceiptError("TRAINING_PHASE_DECISION_INVALID")
    key_id, private_key = _load_active_private_key()
    canonical_challenge = _canonical_json_bytes(validated)
    receipt = {
        "schema_version": 1,
        **{name: validated[name] for name in _CHALLENGE_BINDING_KEYS},
        "challenge_sha256": hashlib.sha256(canonical_challenge).hexdigest(),
        "decision": decision,
        "issued_at": current_time,
        "expires_at": min(validated["expires_at"], current_time + _RECEIPT_TTL_SECONDS),
        "key_id": key_id,
    }
    signature = private_key.sign(_canonical_json_bytes(receipt))
    return {**receipt, "signature": base64.b64encode(signature).decode("ascii")}


def _validate_pinned_public_key(pinned_public_key):
    if (type(pinned_public_key) is not dict
            or frozenset(pinned_public_key) != _PUBLIC_KEY_KEYS
            or type(pinned_public_key.get("schema_version")) is not int
            or pinned_public_key["schema_version"] != 1
            or not _valid_key_id(pinned_public_key.get("key_id"))
            or type(pinned_public_key.get("algorithm")) is not str
            or pinned_public_key.get("algorithm") != "Ed25519"):
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_PUBLIC_KEY_INVALID")
    try:
        raw = _decode_canonical_base64(
            pinned_public_key.get("public_key"), size=32,
            error_code="TRAINING_PHASE_RECEIPT_PUBLIC_KEY_INVALID",
        )
        return pinned_public_key["key_id"], Ed25519PublicKey.from_public_bytes(raw)
    except (TrainingReceiptError, TypeError, ValueError):
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_PUBLIC_KEY_INVALID") from None


def verify_training_phase_decision(
    receipt, *, expected_challenge, pinned_public_key, now: Optional[int] = None,
) -> None:
    """Verify an exact allow receipt against a pinned public key and challenge."""
    current_time = _now_seconds(now)
    try:
        challenge = validate_training_phase_challenge(expected_challenge, now=current_time)
    except TrainingReceiptError:
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_CHALLENGE_INVALID") from None
    if type(receipt) is not dict or frozenset(receipt) != _RECEIPT_KEYS:
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_SCHEMA_INVALID")
    value = dict(receipt)
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_SCHEMA_INVALID")
    for name in _CHALLENGE_BINDING_KEYS:
        if type(value[name]) is not type(challenge[name]) or value[name] != challenge[name]:
            raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_BINDING_MISMATCH")
    expected_challenge_sha = hashlib.sha256(_canonical_json_bytes(challenge)).hexdigest()
    if type(value["challenge_sha256"]) is not str or value["challenge_sha256"] != expected_challenge_sha:
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_CHALLENGE_MISMATCH")
    if type(value["decision"]) is not str or value["decision"] != "allow":
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_DENIED")
    if not _valid_key_id(value["key_id"]):
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_KEY_MISMATCH")
    issued_at = value["issued_at"]
    expires_at = value["expires_at"]
    if (type(issued_at) is not int or type(expires_at) is not int
            or issued_at < challenge["issued_at"] or issued_at > current_time
            or expires_at != min(challenge["expires_at"], issued_at + _RECEIPT_TTL_SECONDS)
            or current_time >= expires_at):
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_TIME_INVALID")
    pinned_key_id, public_key = _validate_pinned_public_key(pinned_public_key)
    if value["key_id"] != pinned_key_id:
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_KEY_MISMATCH")
    try:
        signature = _decode_canonical_base64(
            value["signature"], size=64,
            error_code="TRAINING_PHASE_RECEIPT_SIGNATURE_INVALID",
        )
    except TrainingReceiptError:
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_SIGNATURE_INVALID") from None
    signed_payload = {name: value[name] for name in value if name != "signature"}
    try:
        public_key.verify(signature, _canonical_json_bytes(signed_payload))
    except (InvalidSignature, TypeError, ValueError):
        raise TrainingReceiptVerificationError("TRAINING_PHASE_RECEIPT_SIGNATURE_INVALID") from None
    return None


# Checkpoint envelopes are deliberately separate from phase-v2 receipts.
_CHECKPOINT_ENVELOPE_KEYS = frozenset({"schema_version", "receipt_kind", "payload",
    "payload_sha256", "issued_at", "expires_at", "key_id", "signature"})
_CHECKPOINT_FINGERPRINT_KEYS = frozenset({"request_sha256", "model_identity_sha256",
    "manifest_sha256", "train_sha256", "heldout_sha256", "recipe_sha256", "scope_sha256"})
_CHECKPOINT_ADMISSION_KEYS = frozenset({"operation_id", "task_digest", "run_digest",
    "attempt_id", "worker_epoch", "operation", "completed_step", "checkpoint_ref",
    "checkpoint_sha256", "policy_sha256", "fingerprints", "reservation_digest"})
_CHECKPOINT_COMMITTED_KEYS = frozenset({"schema_version", "operation_id", "task_digest",
    "origin_run_digest", "attempt_id", "worker_epoch", "fingerprints", "policy_sha256",
    "completed_step", "artifact_ref", "artifact_version", "parent_ref", "inventory_sha256",
    "artifact_sha256", "storage_identity", "committed_at_utc", "task_step_ref"})
_CHECKPOINT_LOADED_KEYS = frozenset({"schema_version", "operation_id", "task_digest",
    "run_digest", "checkpoint_ref", "checkpoint_sha256", "restored_state", "task_step_ref",
    "committed_at_utc", "phase_handoff"})
_CHECKPOINT_HANDOFF_KEYS = frozenset({"schema_version", "task_id", "task_digest", "run_digest",
    "attempt_id", "worker_epoch", "fingerprints", "checkpoint_ref", "checkpoint_sha256",
    "load_operation_id", "resume_receipt_sha256", "next_sequence", "next_phase",
    "admission_version", "worker_binding_sha256"})
_CHECKPOINT_KINDS = {
    "owned_training_checkpoint_admission": _CHECKPOINT_ADMISSION_KEYS,
    "owned_training_checkpoint_committed": _CHECKPOINT_COMMITTED_KEYS,
    "owned_training_resume_loaded": _CHECKPOINT_LOADED_KEYS,
    "owned_training_recovery_handoff": _CHECKPOINT_HANDOFF_KEYS,
}
_CHECKPOINT_SEAL = object()


class _VerifiedCheckpointEnvelope:
    __slots__ = ("_canonical_envelope",)

    def __init__(self, envelope=None, *, _seal=None):
        if _seal is not _CHECKPOINT_SEAL:
            raise TrainingReceiptVerificationError("CHECKPOINT_VERIFIED_CONSTRUCTION_DENIED")
        object.__setattr__(self, "_canonical_envelope", _canonical_json_bytes(envelope))

    def __setattr__(self, name, value):
        raise AttributeError("verified checkpoint envelope is immutable")

    @property
    def envelope(self):
        return json.loads(self._canonical_envelope)

    def __reduce_ex__(self, protocol):
        raise TypeError("verified authority must not be serialized as checkpoint state")


class VerifiedTrainingCheckpointAdmission(_VerifiedCheckpointEnvelope):
    __slots__ = ()


class VerifiedTrainingCheckpointReceipt(_VerifiedCheckpointEnvelope):
    __slots__ = ()


class VerifiedTrainingResumeReceipt(_VerifiedCheckpointEnvelope):
    __slots__ = ()


class VerifiedTrainingRecoveryHandoff(_VerifiedCheckpointEnvelope):
    __slots__ = ()


def _checkpoint_reject():
    raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_PAYLOAD_INVALID")


def _checkpoint_uuid(value):
    import uuid
    try:
        parsed = uuid.UUID(value) if type(value) is str else None
    except ValueError:
        _checkpoint_reject()
    if parsed is None or parsed.version != 4 or str(parsed) != value:
        _checkpoint_reject()


def _checkpoint_hash(value):
    if type(value) is not str or _LOWER_SHA256.fullmatch(value) is None:
        _checkpoint_reject()


def _checkpoint_integer(value, minimum=0):
    if type(value) is not int or not minimum <= value <= 1_000_000_000:
        _checkpoint_reject()


def _checkpoint_ref(value, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not str or re.fullmatch(r"ART-[0-9a-f]{16}", value) is None:
        _checkpoint_reject()


def _checkpoint_position(value):
    fields = {"dataset_sha256", "sampler_state_sha256", "epoch_index", "next_batch_index",
              "completed_step", "gradient_accumulation_offset"}
    if type(value) is not dict or set(value) != fields:
        _checkpoint_reject()
    for key in fields:
        (_checkpoint_hash if key.endswith("sha256") else _checkpoint_integer)(value[key])
    if value["gradient_accumulation_offset"] != 0:
        _checkpoint_reject()


def _checkpoint_payload(payload, kind):
    from datetime import datetime, timezone
    if type(payload) is not dict or kind not in _CHECKPOINT_KINDS or set(payload) != _CHECKPOINT_KINDS[kind]:
        _checkpoint_reject()
    value = json.loads(_canonical_json_bytes(payload))
    if len(_canonical_json_bytes(value)) > 1024 * 1024:
        _checkpoint_reject()
    for key, item in value.items():
        if key == "checkpoint_sha256" and kind == "owned_training_checkpoint_admission" and value["operation"] == "save" and item is None:
            continue
        if key in {"task_digest", "run_digest", "origin_run_digest"} or key.endswith("sha256") or key == "reservation_digest":
            _checkpoint_hash(item)
        elif key in {"operation_id", "attempt_id", "load_operation_id"}:
            _checkpoint_uuid(item)
        elif key in {"worker_epoch", "completed_step"}:
            _checkpoint_integer(item)
        elif key in {"artifact_version", "next_sequence"}:
            _checkpoint_integer(item, 1)
        elif key == "schema_version":
            if type(item) is not int or item != 1:
                _checkpoint_reject()
        elif key == "fingerprints":
            if type(item) is not dict or set(item) != _CHECKPOINT_FINGERPRINT_KEYS:
                _checkpoint_reject()
            for fingerprint in item.values():
                _checkpoint_hash(fingerprint)
        elif key in {"artifact_ref", "checkpoint_ref", "parent_ref"}:
            _checkpoint_ref(item, nullable=key == "parent_ref" or kind == "owned_training_checkpoint_admission")
        elif key == "committed_at_utc":
            try:
                stamp = datetime.fromisoformat(item.replace("Z", "+00:00")) if type(item) is str else None
            except ValueError:
                _checkpoint_reject()
            if stamp is None or stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
                _checkpoint_reject()
        elif key in {"storage_identity", "task_step_ref"}:
            # Shared Artifact's registered opaque identity is artifact:<ART-ref>.
            # Admit that exact bound value, not arbitrary URI/colon strings.
            registered_identity = (key == "storage_identity"
                and type(value.get("artifact_ref")) is str
                and item == "artifact:" + value["artifact_ref"])
            if (type(item) is not str or (not registered_identity
                    and re.fullmatch(r"[A-Za-z0-9_.-]{1,255}", item) is None)):
                _checkpoint_reject()
        elif key == "task_id":
            if type(item) is not str or re.fullmatch(r"trainrelay_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", item) is None:
                _checkpoint_reject()
            if hashlib.sha256(item.encode()).hexdigest() != value["task_digest"]:
                _checkpoint_reject()
        elif key == "restored_state":
            fields = {"completed_step", "data_position", "optimizer_state_sha256", "scheduler_state_sha256",
                      "rng_state_sha256", "adapter_or_model_state_sha256", "framework_lock_sha256"}
            if type(item) is not dict or set(item) != fields:
                _checkpoint_reject()
            _checkpoint_integer(item["completed_step"])
            _checkpoint_position(item["data_position"])
            if item["completed_step"] != item["data_position"]["completed_step"]:
                _checkpoint_reject()
            for name in fields - {"completed_step", "data_position"}:
                _checkpoint_hash(item[name])
        elif key == "phase_handoff":
            if type(item) is not dict or set(item) != _CHECKPOINT_ENVELOPE_KEYS:
                _checkpoint_reject()
            _checkpoint_payload(item["payload"], "owned_training_recovery_handoff")
    if kind == "owned_training_checkpoint_admission":
        if type(value["operation"]) is not str or value["operation"] not in {"save", "load"}:
            _checkpoint_reject()
        if value["operation"] == "save":
            if value["checkpoint_ref"] is not None or value["checkpoint_sha256"] is not None:
                _checkpoint_reject()
        else:
            _checkpoint_ref(value["checkpoint_ref"])
            _checkpoint_hash(value["checkpoint_sha256"])
    if kind == "owned_training_recovery_handoff":
        if value["next_phase"] != "before_train" or type(value["admission_version"]) is not int or value["admission_version"] != 3:
            _checkpoint_reject()
    return value


def sign_training_checkpoint_payload(payload, *, receipt_kind, now=None):
    """Sign a derivative owner result; this function does not grant admission."""
    current = _now_seconds(now)
    validated = _checkpoint_payload(payload, receipt_kind)
    key_id, private_key = _load_active_private_key()
    expires = current + 30 if receipt_kind in {
        "owned_training_checkpoint_admission", "owned_training_recovery_handoff"} else None
    envelope = {"schema_version": 1, "receipt_kind": receipt_kind, "payload": validated,
        "payload_sha256": hashlib.sha256(_canonical_json_bytes(validated)).hexdigest(),
        "issued_at": current, "expires_at": expires, "key_id": key_id}
    signature = private_key.sign(_canonical_json_bytes(envelope))
    return {**envelope, "signature": base64.b64encode(signature).decode("ascii")}


def _verify_checkpoint_envelope(envelope, *, expected_payload, pinned_public_key, kind, result_type, now=None):
    current = _now_seconds(now)
    if type(envelope) is not dict or set(envelope) != _CHECKPOINT_ENVELOPE_KEYS:
        raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_SCHEMA_INVALID")
    value = json.loads(_canonical_json_bytes(envelope))
    if type(value["schema_version"]) is not int or value["schema_version"] != 1 or value["receipt_kind"] != kind:
        raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_KIND_INVALID")
    payload = _checkpoint_payload(value["payload"], kind)
    expected = _checkpoint_payload(expected_payload, kind)
    if _canonical_json_bytes(payload) != _canonical_json_bytes(expected):
        raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_BINDING_MISMATCH")
    if value["payload_sha256"] != hashlib.sha256(_canonical_json_bytes(payload)).hexdigest():
        raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_HASH_MISMATCH")
    issued, expires = value["issued_at"], value["expires_at"]
    live = kind in {"owned_training_checkpoint_admission", "owned_training_recovery_handoff"}
    if type(issued) is not int or issued <= 0 or issued > current:
        raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_TIME_INVALID")
    if live:
        if type(expires) is not int or not issued < expires <= issued + 30 or current >= expires:
            raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_TIME_INVALID")
    elif expires is not None:
        raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_TIME_INVALID")
    key_id, public_key = _validate_pinned_public_key(pinned_public_key)
    if value["key_id"] != key_id:
        raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_KEY_MISMATCH")
    try:
        signature = _decode_canonical_base64(value["signature"], size=64, error_code="CHECKPOINT_RECEIPT_SIGNATURE_INVALID")
        public_key.verify(signature, _canonical_json_bytes({k: v for k, v in value.items() if k != "signature"}))
    except (TrainingReceiptError, InvalidSignature, TypeError, ValueError):
        raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_SIGNATURE_INVALID") from None
    if kind == "owned_training_resume_loaded":
        inner = payload["phase_handoff"]
        _verify_checkpoint_envelope(inner, expected_payload=inner["payload"], pinned_public_key=pinned_public_key,
            kind="owned_training_recovery_handoff", result_type=VerifiedTrainingRecoveryHandoff, now=inner["issued_at"])
        for field in ("task_digest", "run_digest", "checkpoint_ref", "checkpoint_sha256"):
            if inner["payload"][field] != payload[field]:
                raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_BINDING_MISMATCH")
        if inner["payload"]["load_operation_id"] != payload["operation_id"]:
            raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_BINDING_MISMATCH")
        record = {k: v for k, v in payload.items() if k != "phase_handoff"}
        if inner["payload"]["resume_receipt_sha256"] != hashlib.sha256(_canonical_json_bytes(record)).hexdigest():
            raise TrainingReceiptVerificationError("CHECKPOINT_RECEIPT_BINDING_MISMATCH")
    return result_type(value, _seal=_CHECKPOINT_SEAL)


def verify_training_checkpoint_admission(envelope, *, expected_payload, pinned_public_key, now=None):
    return _verify_checkpoint_envelope(envelope, expected_payload=expected_payload, pinned_public_key=pinned_public_key,
        kind="owned_training_checkpoint_admission", result_type=VerifiedTrainingCheckpointAdmission, now=now)


def verify_training_checkpoint_receipt(envelope, *, expected_payload, pinned_public_key):
    return _verify_checkpoint_envelope(envelope, expected_payload=expected_payload, pinned_public_key=pinned_public_key,
        kind="owned_training_checkpoint_committed", result_type=VerifiedTrainingCheckpointReceipt)


def verify_training_resume_receipt(envelope, *, expected_payload, pinned_public_key):
    return _verify_checkpoint_envelope(envelope, expected_payload=expected_payload, pinned_public_key=pinned_public_key,
        kind="owned_training_resume_loaded", result_type=VerifiedTrainingResumeReceipt)


def verify_training_recovery_handoff(envelope, *, expected_payload, pinned_public_key, now=None):
    return _verify_checkpoint_envelope(envelope, expected_payload=expected_payload, pinned_public_key=pinned_public_key,
        kind="owned_training_recovery_handoff", result_type=VerifiedTrainingRecoveryHandoff, now=now)
