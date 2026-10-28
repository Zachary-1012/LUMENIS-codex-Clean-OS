"""Caller contract tests: ephemeral keys/disposable DB, never live training."""
import base64
import copy
import hashlib
import json
import time
import uuid
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from lumenis.system.ai_gateway.owned_training import TrainingApprovalRequest, TrainingBlocked
from lumenis.system.ai_gateway.owned_training_phases import TrainingPhaseClient
from lumenis.system.security import permission as p, training_receipts as receipts


def _context(request):
    return {"scope_descriptors": {scope: {
        "domain_id": request.domain_id, "product_id": "CTH" if request.domain_id == "cth" else "ZBMP",
        "global_scope": scope == "GLOBAL / ALL",
        "subject_id": scope if request.domain_id == "cth" and scope != "GLOBAL / ALL" else None,
        "brand_focus_id": scope if request.domain_id == "bmp" and scope != "GLOBAL / ALL" else None,
    } for scope in request.scopes}}


class _UnitMetadataServer:
    """Explicit in-memory metadata fixture; it has no Permission/DB authority."""
    def __init__(self, request, context, pin):
        self.pin = pin
        self.fingerprints = p.owned_training_phase_fingerprints(
            request, actor_id=1, domain_id=request.domain_id, context=context)
        self.task_id = "trainrelay_" + str(uuid.uuid4())
        self.state = {"admission_version": 2, "fingerprints": self.fingerprints,
                      "run_digest": hashlib.sha256(uuid.uuid4().bytes).hexdigest(),
                      "task_digest": hashlib.sha256(self.task_id.encode()).hexdigest(),
                      "next_sequence": 1, "last_phase": None, "terminal": False,
                      "status": "ready", "pinned_public_key": pin}
        self.calls = []
        self.records = {}
        self.mutate = lambda reply: None
        self.drop_response = False

    def __call__(self, method, path, body):
        from ai_task_engine import _TRAINING_PHASE_TRANSITIONS
        self.calls.append((method, path, copy.deepcopy(body)))
        if path == TrainingPhaseClient._ROOT:
            reply = {"ok": True, "state": "PHASE_TASK_PREPARED", "task_id": self.task_id,
                     "public_challenge_context": copy.deepcopy(self.state),
                     "pinned_public_key": self.pin, "training_started": False, "approval_issued": False}
        elif path.endswith("/challenges"):
            phase = body["phase"]
            assert phase in _TRAINING_PHASE_TRANSITIONS[self.state["last_phase"]]
            now = int(time.time())
            challenge = {"schema_version": 1, **self.fingerprints,
                         "run_digest": self.state["run_digest"], "task_digest": self.state["task_digest"],
                         "nonce": hashlib.sha256(uuid.uuid4().bytes).hexdigest(), "phase": phase,
                         "sequence": self.state["next_sequence"], "issued_at": now, "expires_at": now + 60}
            reply = {"ok": True, "state": "PHASE_CHALLENGE_PREPARED", "challenge": challenge,
                     "pinned_public_key": self.pin, "model_execution_claimed": False}
        elif path.endswith("/challenge-decisions"):
            challenge = body["challenge"]
            signed = receipts.sign_training_phase_decision(challenge, "allow")
            self.state["next_sequence"] += 1
            self.state["last_phase"] = challenge["phase"]
            self.records[challenge["nonce"]] = {"ok": True, "state": "HISTORICAL_PHASE_RECEIPT",
                "challenge": challenge, "receipt": signed, "pinned_public_key": self.pin,
                "historical": True, "authorization_usable": False, "model_execution_claimed": False}
            reply = {"ok": True, "state": "PHASE_RECEIPT_COMMITTED", "receipt": signed,
                     "next_sequence": self.state["next_sequence"], "model_execution_claimed": False}
            if self.drop_response:
                raise ConnectionError("unit-fixture response lost after commit")
        else:
            assert method == "GET"
            reply = self.records[path.rsplit("/", 1)[-1]]
        reply = copy.deepcopy(reply)
        self.mutate(reply)
        return reply


def _unit_signer(monkeypatch):
    key = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_KEY_RING", json.dumps({"unit-callback-v3": base64.b64encode(key).decode()}))
    monkeypatch.setenv("LUMENIS_TRAINING_RECEIPT_ACTIVE_KEY_ID", "unit-callback-v3")
    return receipts.get_training_receipt_public_key()


def _unit_phase_client(request, monkeypatch=None):
    """Bind a real signer to fixture metadata for existing simulated compute tests."""
    pin = _unit_signer(monkeypatch) if monkeypatch is not None else receipts.get_training_receipt_public_key()
    context = _context(request)
    server = _UnitMetadataServer(request, context, pin)
    client = TrainingPhaseClient(request, context, actor_id=1, pinned_public_key=pin, transport=server)
    return client, server


@pytest.fixture
def bound_phase(monkeypatch):
    request = TrainingApprovalRequest("openai/gpt-oss-20b", "6cee5e81ee83917806bbde320786a8fb61efebee",
        "1" * 64, "2" * 64, ("GLOBAL / ALL",), manifest_sha256="3" * 64, domain_id="cth")
    client, server = _unit_phase_client(request, monkeypatch)
    return request, client, server


def test_no_transport_fails_without_request_or_implicit_host(bound_phase):
    request, client, server = bound_phase
    client._transport = None
    with pytest.raises(TrainingBlocked, match="TRANSPORT_NOT_BOUND"):
        client.authorize(request, "initial")
    assert not server.calls


@pytest.mark.parametrize("field,value", [("domain_id", "bmp"), ("train_sha256", "4" * 64),
    ("model_revision", "different"), ("recipe", "different")])
def test_changed_frozen_request_is_rejected_before_transport(bound_phase, field, value):
    request, client, server = bound_phase
    with pytest.raises(TrainingBlocked, match="REQUEST_CHANGED"):
        client.authorize(replace(request, **{field: value}), "initial")
    assert not server.calls


@pytest.mark.parametrize("mutation", ["nonce-signature", "history", "missing-receipt", "sequence", "expired"])
def test_unusable_receipts_never_return_phase_authority(bound_phase, mutation):
    request, client, server = bound_phase
    def change(reply):
        if reply.get("state") != "PHASE_RECEIPT_COMMITTED": return
        if mutation == "nonce-signature": reply["receipt"]["nonce"] = "f" * 64
        elif mutation == "history": reply.update(state="PHASE_RECEIPT_ALREADY_COMMITTED", historical=True, authorization_usable=False)
        elif mutation == "missing-receipt": reply.pop("receipt")
        elif mutation == "sequence": reply["next_sequence"] = 99
        elif mutation == "expired": reply["receipt"]["expires_at"] = int(time.time()) - 1
    server.mutate = change
    with pytest.raises(TrainingBlocked): client.authorize(request, "initial")
    calls = len(server.calls)
    with pytest.raises(TrainingBlocked, match="PHYSICAL_RECOVERY_REQUIRED"):
        client.authorize(request, "before_output_dir")
    assert len(server.calls) == calls


def test_lost_response_history_is_verified_but_never_renewed(bound_phase):
    request, client, server = bound_phase
    server.drop_response = True
    with pytest.raises(TrainingBlocked, match="TRANSPORT_FAILED"):
        client.authorize(request, "initial")
    history = client.read_last_history()
    assert history["authorization_usable"] is False and history["historical"] is True
    assert server.state["next_sequence"] == 2
    with pytest.raises(TrainingBlocked, match="PHYSICAL_RECOVERY_REQUIRED"):
        client.authorize(request, "before_output_dir")
    assert len(server.records) == 1


def test_already_admitted_initial_never_rewinds_new_worker(bound_phase):
    request, client, server = bound_phase
    client.authorize(request, "initial")
    restarted = TrainingPhaseClient(request, _context(request), actor_id=1,
        pinned_public_key=server.pin, transport=server)
    with pytest.raises(TrainingBlocked, match="PHYSICAL_RECOVERY_REQUIRED"):
        restarted.authorize(request, "initial")
    assert len(server.records) == 1


def test_cooperative_cancel_has_no_next_boundary_transport(bound_phase):
    request, client, server = bound_phase
    client.authorize(request, "initial")
    client.cancel()
    calls = len(server.calls)
    with pytest.raises(TrainingBlocked, match="CANCELLED_AT_BOUNDARY"):
        client.authorize(request, "before_output_dir")
    assert len(server.calls) == calls


def test_receipt_expiring_during_final_permit_check_blocks_action(bound_phase, monkeypatch):
    request, client, server = bound_phase
    client.authorize(request, "initial")
    later = client._last_receipt["expires_at"]
    monkeypatch.setattr(receipts, "_now_seconds", lambda now: later if now is None else now)
    with pytest.raises(TrainingBlocked, match="EXPIRED_OR_INVALID"):
        client.require_current_receipt()


@pytest.mark.parametrize("mutation", ["scope", "run", "pin", "task"])
def test_wrong_challenge_binding_never_requests_decision(bound_phase, mutation):
    request, client, server = bound_phase
    def change(reply):
        if reply.get("state") != "PHASE_CHALLENGE_PREPARED": return
        if mutation == "scope": reply["challenge"]["scope_sha256"] = "f" * 64
        elif mutation == "run": reply["challenge"]["run_digest"] = "f" * 64
        elif mutation == "task": reply["challenge"]["task_digest"] = "f" * 64
        else: reply["pinned_public_key"]["key_id"] = "substituted-key"
    server.mutate = change
    with pytest.raises(TrainingBlocked, match="CHALLENGE_BINDING_INVALID"):
        client.authorize(request, "initial")
    assert not any(path.endswith("/challenge-decisions") for _, path, _ in server.calls)


def test_withdrawn_gpu_training_never_starts_from_plain_allow(tmp_path, monkeypatch):
    from tests.test_owned_ai_training import _inputs
    from lumenis.system.ai_gateway import owned_training as training
    paths = _inputs(tmp_path, monkeypatch)
    monkeypatch.setattr(training, "_require_cuda", lambda: pytest.fail("compute before phase binding"))
    with pytest.raises(TrainingBlocked, match="GPU_TRAINING_WITHDRAWN_BY_PO"):
        training.run_owned_lora_training(paths[0], paths[2], paths[3], paths[4], manifest_path=paths[1], execute=True,
                                        approval_verifier=lambda request: True)
    assert not paths[-1].exists()
