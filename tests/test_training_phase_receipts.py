"""Strict tests for derivative Ed25519 training phase receipts."""
import base64
import hashlib
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from lumenis.system.security import training_receipts as receipts


NOW = 1_800_000_000
KEY_ID = "ephemeral-training-test"


@pytest.fixture(autouse=True)
def clear_receipt_key_environment(monkeypatch):
    monkeypatch.delenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", raising=False)
    monkeypatch.delenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", raising=False)


@pytest.fixture
def ephemeral_key(monkeypatch):
    private_key = Ed25519PrivateKey.generate()
    encoded_private = _encode_private_key(private_key)
    monkeypatch.setenv(
        "LUMENIS_TRAINING_RECEIPT_KEY_RING",
        json.dumps({KEY_ID: encoded_private}),
    )
    monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", KEY_ID)
    return private_key


def _encode_private_key(private_key):
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return base64.b64encode(private_bytes).decode("ascii")


def make_challenge(**overrides):
    value = {
        "schema_version": 1,
        "run_digest": hashlib.sha256(b"run").hexdigest(),
        "task_digest": hashlib.sha256(b"task").hexdigest(),
        "request_sha256": hashlib.sha256(b"request").hexdigest(),
        "model_identity_sha256": hashlib.sha256(b"model").hexdigest(),
        "manifest_sha256": hashlib.sha256(b"manifest").hexdigest(),
        "train_sha256": hashlib.sha256(b"train").hexdigest(),
        "heldout_sha256": hashlib.sha256(b"heldout").hexdigest(),
        "recipe_sha256": hashlib.sha256(b"recipe").hexdigest(),
        "scope_sha256": hashlib.sha256(b"scope").hexdigest(),
        "nonce": hashlib.sha256(b"nonce").hexdigest(),
        "phase": "step_begin",
        "sequence": 3,
        "issued_at": NOW - 5,
        "expires_at": NOW + 55,
    }
    value.update(overrides)
    return value


def _other_public_key():
    other = Ed25519PrivateKey.generate()
    raw = other.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {
        "schema_version": 1,
        "key_id": "other-ephemeral-key",
        "algorithm": "Ed25519",
        "public_key": base64.b64encode(raw).decode("ascii"),
    }


def _signed_receipt(ephemeral_key, *, challenge=None, decision="allow", now=NOW):
    challenge = make_challenge() if challenge is None else challenge
    return receipts.sign_training_phase_decision(challenge, decision, now=now)


@pytest.mark.parametrize(
    "phase",
    [
        "initial", "before_output_dir", "before_train", "step_begin", "substep_end",
        "pre_optimizer_step", "before_adapter_save", "before_tokenizer_save",
        "after_saved_artifact_check",
    ],
)
def test_challenge_accepts_only_registered_phases_and_returns_a_copy(phase):
    challenge = make_challenge(phase=phase)
    checked = receipts.validate_training_phase_challenge(challenge, now=NOW)

    assert checked == challenge
    assert checked is not challenge
    checked["sequence"] = 4
    assert challenge["sequence"] == 3


@pytest.mark.parametrize(
    "change,code",
    [
        (lambda item: item.pop("nonce"), "SCHEMA"),
        (lambda item: item.update(unregistered=True), "SCHEMA"),
        (lambda item: item.update(schema_version=True), "SCHEMA"),
        (lambda item: item.update(sequence=True), "SEQUENCE"),
        (lambda item: item.update(sequence=0), "SEQUENCE"),
        (lambda item: item.update(sequence=1_000_000_001), "SEQUENCE"),
        (lambda item: item.update(sequence=3.0), "SEQUENCE"),
        (lambda item: item.update(phase="optimizer_step"), "PHASE"),
        (lambda item: item.update(run_digest=True), "BINDING"),
        (lambda item: item.update(scope_sha256=float("nan")), "BINDING"),
        (lambda item: item.update(train_sha256="A" * 64), "BINDING"),
        (lambda item: item.update(nonce="0" * 63), "BINDING"),
        (lambda item: item.update(issued_at=True), "TIME"),
        (lambda item: item.update(expires_at=False), "TIME"),
        (lambda item: item.update(expires_at=NOW - 5), "TIME"),
        (lambda item: item.update(expires_at=NOW + 56), "TIME"),
        (lambda item: item.update(issued_at=NOW + 1, expires_at=NOW + 20), "TIME"),
    ],
)
def test_challenge_rejects_schema_type_binding_and_time_mutations(change, code):
    challenge = make_challenge()
    change(challenge)
    with pytest.raises(receipts.TrainingReceiptError, match=f"TRAINING_PHASE_CHALLENGE_.*{code}"):
        receipts.validate_training_phase_challenge(challenge, now=NOW)


@pytest.mark.parametrize("ttl", [0, -1, 61])
def test_challenge_rejects_nonpositive_or_overlong_ttl(ttl):
    challenge = make_challenge(issued_at=NOW, expires_at=NOW + ttl)
    with pytest.raises(receipts.TrainingReceiptError, match="TRAINING_PHASE_CHALLENGE_TIME_INVALID"):
        receipts.validate_training_phase_challenge(challenge, now=NOW)


def test_challenge_rejects_future_issue_expiry_and_invalid_now():
    challenge = make_challenge(issued_at=NOW + 1, expires_at=NOW + 20)
    with pytest.raises(receipts.TrainingReceiptError, match="TRAINING_PHASE_CHALLENGE_TIME_INVALID"):
        receipts.validate_training_phase_challenge(challenge, now=NOW)
    with pytest.raises(receipts.TrainingReceiptError, match="TRAINING_PHASE_CHALLENGE_TIME_INVALID"):
        receipts.validate_training_phase_challenge(make_challenge(), now=NOW + 55)
    for invalid_now in (True, 0, 1.5, "1800000000"):
        with pytest.raises(receipts.TrainingReceiptError, match="TRAINING_RECEIPT_TIME_INVALID"):
            receipts.validate_training_phase_challenge(make_challenge(), now=invalid_now)


def test_public_key_response_contains_only_pinned_ed25519_verification_fields(ephemeral_key):
    value = receipts.get_training_receipt_public_key()
    assert set(value) == {"schema_version", "key_id", "algorithm", "public_key"}
    assert value["schema_version"] == 1
    assert value["key_id"] == KEY_ID
    assert value["algorithm"] == "Ed25519"
    assert len(base64.b64decode(value["public_key"], validate=True)) == 32
    assert "private" not in json.dumps(value).lower()


@pytest.mark.parametrize(
    "kind",
    [
        "missing_ring", "malformed_json", "array", "empty", "duplicate_key",
        "nonstandard_nan", "bad_key_id", "bad_base64", "wrong_key_size",
        "noncanonical_base64", "unknown_active_key", "nonstring_key",
    ],
)
def test_missing_or_malformed_signing_configuration_fails_closed(monkeypatch, ephemeral_key, kind):
    encoded = _encode_private_key(ephemeral_key)
    if kind == "missing_ring":
        monkeypatch.delenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", raising=False)
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", KEY_ID)
    elif kind == "malformed_json":
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", "{malformed")
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", KEY_ID)
    elif kind == "array":
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", "[]")
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", KEY_ID)
    elif kind == "empty":
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", "{}")
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", KEY_ID)
    elif kind == "duplicate_key":
        monkeypatch.setenv(
            "LUMENIS_TRAINING_RECEIPT_KEY_RING",
            f'{{"test":"{encoded}","test":"{encoded}"}}',
        )
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", "test")
    elif kind == "nonstandard_nan":
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", '{"test":NaN}')
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", "test")
    elif kind == "bad_key_id":
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", json.dumps({"bad key": encoded}))
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", "bad key")
    elif kind == "bad_base64":
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", '{"test":"%%%"}')
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", "test")
    elif kind == "wrong_key_size":
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", '{"test":"AA=="}')
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", "test")
    elif kind == "noncanonical_base64":
        monkeypatch.setenv(
            "LUMENIS_TRAINING_RECEIPT_KEY_RING", json.dumps({"test": encoded + "\n"}),
        )
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", "test")
    elif kind == "unknown_active_key":
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", json.dumps({"test": encoded}))
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", "missing")
    else:
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", '{"test":true}')
        monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", "test")
    with pytest.raises(receipts.TrainingReceiptConfigurationError):
        receipts.get_training_receipt_public_key()


def test_missing_active_key_id_fails_closed(monkeypatch):
    monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", "{}")
    monkeypatch.delenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", raising=False)
    with pytest.raises(receipts.TrainingReceiptConfigurationError):
        receipts.get_training_receipt_public_key()


def test_sign_and_verify_allow_receipt_with_canonical_ed25519_signature(ephemeral_key):
    challenge = make_challenge()
    receipt = receipts.sign_training_phase_decision(challenge, "allow", now=NOW)
    pinned = receipts.get_training_receipt_public_key()
    expected_keys = {
        "schema_version", "run_digest", "task_digest", "request_sha256",
        "model_identity_sha256", "manifest_sha256", "train_sha256", "heldout_sha256",
        "recipe_sha256", "scope_sha256", "nonce", "phase", "sequence",
        "challenge_sha256", "decision", "issued_at", "expires_at", "key_id", "signature",
    }
    assert set(receipt) == expected_keys
    assert receipt["decision"] == "allow"
    assert receipt["expires_at"] == NOW + 30
    unsigned = {name: value for name, value in receipt.items() if name != "signature"}
    signature = base64.b64decode(receipt["signature"], validate=True)
    ephemeral_key.public_key().verify(
        signature,
        json.dumps(unsigned, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                   allow_nan=False).encode("utf-8"),
    )
    assert receipts.verify_training_phase_decision(
        receipt, expected_challenge=challenge, pinned_public_key=pinned, now=NOW,
    ) is None


def test_receipt_expiry_is_capped_by_challenge_expiry(ephemeral_key):
    challenge = make_challenge(expires_at=NOW + 10)
    receipt = receipts.sign_training_phase_decision(challenge, "allow", now=NOW)
    assert receipt["expires_at"] == NOW + 10
    assert receipts.verify_training_phase_decision(
        receipt, expected_challenge=challenge,
        pinned_public_key=receipts.get_training_receipt_public_key(), now=NOW,
    ) is None


def test_deny_receipt_is_signed_but_never_verifies_as_admission(ephemeral_key):
    challenge = make_challenge()
    receipt = receipts.sign_training_phase_decision(challenge, "deny", now=NOW)
    with pytest.raises(receipts.TrainingReceiptVerificationError, match="TRAINING_PHASE_RECEIPT_DENIED"):
        receipts.verify_training_phase_decision(
            receipt, expected_challenge=challenge,
            pinned_public_key=receipts.get_training_receipt_public_key(), now=NOW,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(extra="field"),
        lambda value: value.pop("task_digest"),
        lambda value: value.update(run_digest="0" * 64),
        lambda value: value.update(challenge_sha256="0" * 64),
        lambda value: value.update(phase="before_train"),
        lambda value: value.update(sequence=True),
        lambda value: value.update(schema_version=True),
        lambda value: value.update(issued_at=True),
        lambda value: value.update(expires_at=False),
        lambda value: value.update(decision="deny"),
        lambda value: value.update(signature="not base64"),
        lambda value: value.update(expires_at=NOW + 29),
    ],
)
def test_receipt_schema_binding_types_and_tampering_are_rejected(ephemeral_key, mutation):
    challenge = make_challenge()
    receipt = receipts.sign_training_phase_decision(challenge, "allow", now=NOW)
    mutation(receipt)
    with pytest.raises(receipts.TrainingReceiptVerificationError):
        receipts.verify_training_phase_decision(
            receipt, expected_challenge=challenge,
            pinned_public_key=receipts.get_training_receipt_public_key(), now=NOW,
        )


def test_signature_bit_flip_and_wrong_pinned_key_are_rejected(ephemeral_key):
    challenge = make_challenge()
    receipt = receipts.sign_training_phase_decision(challenge, "allow", now=NOW)
    pinned = receipts.get_training_receipt_public_key()
    raw = bytearray(base64.b64decode(receipt["signature"], validate=True))
    raw[0] ^= 1
    receipt["signature"] = base64.b64encode(raw).decode("ascii")
    with pytest.raises(receipts.TrainingReceiptVerificationError, match="SIGNATURE_INVALID"):
        receipts.verify_training_phase_decision(
            receipt, expected_challenge=challenge, pinned_public_key=pinned, now=NOW,
        )

    receipt = receipts.sign_training_phase_decision(challenge, "allow", now=NOW)
    with pytest.raises(receipts.TrainingReceiptVerificationError, match="KEY_MISMATCH|SIGNATURE_INVALID"):
        receipts.verify_training_phase_decision(
            receipt, expected_challenge=challenge, pinned_public_key=_other_public_key(), now=NOW,
        )


def test_mismatched_expected_challenge_and_key_id_are_rejected(ephemeral_key):
    challenge = make_challenge()
    receipt = receipts.sign_training_phase_decision(challenge, "allow", now=NOW)
    changed = make_challenge(request_sha256=hashlib.sha256(b"different request").hexdigest())
    pinned = receipts.get_training_receipt_public_key()
    with pytest.raises(receipts.TrainingReceiptVerificationError, match="CHALLENGE_MISMATCH|BINDING_MISMATCH"):
        receipts.verify_training_phase_decision(
            receipt, expected_challenge=changed, pinned_public_key=pinned, now=NOW,
        )
    changed_key = {**pinned, "key_id": "other-ephemeral-key"}
    with pytest.raises(receipts.TrainingReceiptVerificationError, match="KEY_MISMATCH"):
        receipts.verify_training_phase_decision(
            receipt, expected_challenge=challenge, pinned_public_key=changed_key, now=NOW,
        )


@pytest.mark.parametrize("mutation", ["extra", "schema_bool", "wrong_algorithm", "noncanonical_base64"])
def test_pinned_public_key_schema_is_strict(ephemeral_key, mutation):
    challenge = make_challenge()
    receipt = receipts.sign_training_phase_decision(challenge, "allow", now=NOW)
    pinned = receipts.get_training_receipt_public_key()
    if mutation == "extra":
        pinned["private_key"] = "must never be accepted"
    elif mutation == "schema_bool":
        pinned["schema_version"] = True
    elif mutation == "wrong_algorithm":
        pinned["algorithm"] = "Ed25519ph"
    else:
        pinned["public_key"] += "\n"
    with pytest.raises(receipts.TrainingReceiptVerificationError):
        receipts.verify_training_phase_decision(
            receipt, expected_challenge=challenge, pinned_public_key=pinned, now=NOW,
        )


def test_receipt_rejects_expired_future_and_delayed_verification(ephemeral_key):
    challenge = make_challenge()
    receipt = receipts.sign_training_phase_decision(challenge, "allow", now=NOW)
    pinned = receipts.get_training_receipt_public_key()
    with pytest.raises(receipts.TrainingReceiptVerificationError, match="TIME_INVALID"):
        receipts.verify_training_phase_decision(
            receipt, expected_challenge=challenge, pinned_public_key=pinned, now=NOW + 30,
        )

    future = dict(receipt)
    future["issued_at"] = NOW + 1
    future["expires_at"] = NOW + 31
    with pytest.raises(receipts.TrainingReceiptVerificationError, match="TIME_INVALID"):
        receipts.verify_training_phase_decision(
            future, expected_challenge=challenge, pinned_public_key=pinned, now=NOW,
        )

    delayed = dict(receipt)
    with pytest.raises(receipts.TrainingReceiptVerificationError, match="CHALLENGE_INVALID"):
        receipts.verify_training_phase_decision(
            delayed, expected_challenge=challenge, pinned_public_key=pinned, now=NOW + 55,
        )


@pytest.mark.parametrize("decision", [None, True, "ALLOW", "approve", "" ])
def test_signer_rejects_undeclared_decision_values(ephemeral_key, decision):
    with pytest.raises(receipts.TrainingReceiptError, match="TRAINING_PHASE_DECISION_INVALID"):
        receipts.sign_training_phase_decision(make_challenge(), decision, now=NOW)


def test_signer_rejects_missing_and_malformed_keys_without_creating_material(monkeypatch):
    monkeypatch.delenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", raising=False)
    monkeypatch.delenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", raising=False)
    with pytest.raises(receipts.TrainingReceiptConfigurationError):
        receipts.sign_training_phase_decision(make_challenge(), "allow", now=NOW)
