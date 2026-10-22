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
from tests.test_owned_training_phase_http_v2 import phase_http, strict_permission_mode

pytestmark = pytest.mark.usefixtures("strict_permission_mode")


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


def test_plain_allow_without_phase_client_cannot_start_compute(tmp_path, monkeypatch):
    from tests.test_owned_ai_training import _inputs
    from lumenis.system.ai_gateway import owned_training as training
    paths = _inputs(tmp_path, monkeypatch)
    monkeypatch.setattr(training, "_require_cuda", lambda: pytest.fail("compute before phase binding"))
    with pytest.raises(TrainingBlocked, match="TRANSPORT_NOT_BOUND"):
        training.run_owned_lora_training(paths[0], paths[2], paths[3], paths[4], manifest_path=paths[1], execute=True,
                                        approval_verifier=lambda request: True)
    assert not paths[-1].exists()


def _real_http_client(case):
    grant = case["grant"]("account")
    material = case["request_data"]
    request = TrainingApprovalRequest(**{**material, "scopes": tuple(material["scopes"])})
    calls = []
    def transport(method, path, body):
        calls.append((method, path, copy.deepcopy(body)))
        response = case["client"].open(path, method=method,
            json=body if body is not None else None,
            headers={"Host": "localhost", "X-Domain-Id": "CTH", "X-Product-Id": "CTH",
                     "X-Lumenis-Context-Mode": "GLOBAL_ALL", "Authorization": grant["identity"]},
            environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
        if response.status_code not in {200, 202}: raise ConnectionError("isolated HTTP denied")
        return response.get_json()
    client = TrainingPhaseClient(request, {"scope_descriptors": case["body"]["scope_descriptors"]},
        actor_id=grant["actor_id"], pinned_public_key=case["initial_public_key"], transport=transport)
    return request, client, grant, calls


def test_actual_metadata_routes_accept_full_nine_phase_chain(phase_http):
    request, client, grant, calls = _real_http_client(phase_http)
    phases = ["initial", "before_output_dir", "before_train", "step_begin", "substep_end",
              "substep_end", "pre_optimizer_step", "step_begin", "pre_optimizer_step",
              "before_adapter_save", "before_tokenizer_save", "after_saved_artifact_check"]
    for phase in phases: client.authorize(request, phase)
    assert client._sequence == len(phases) + 1
    for method, path, body in calls:
        assert set(body) <= {"training_request", "scope_descriptors", "phase", "challenge"}
        assert grant["approval_token"] not in json.dumps(body)
    assert client.read_last_history()["authorization_usable"] is False


def test_actual_grant_revocation_denies_next_caller_phase(phase_http):
    request, client, grant, calls = _real_http_client(phase_http)
    client.authorize(request, "initial")
    assert phase_http["gate"].revoke_approval(grant["approval_token"])
    with pytest.raises(TrainingBlocked, match="TRANSPORT_FAILED"):
        client.authorize(request, "before_output_dir")
    assert client._sequence == 2


def _simulated_training_with_actual_metadata(case, tmp_path, monkeypatch, boundary=None):
    """Real owners/DB/signatures; synthetic snapshot and compute are explicitly fixtures."""
    from dataclasses import asdict
    from tests.test_owned_ai_training import _inputs, _mock_training_stack
    from lumenis.system.ai_gateway import owned_training as training
    paths = _inputs(tmp_path, monkeypatch)
    data = training.run_owned_lora_training(paths[0], paths[2], paths[3], paths[4], manifest_path=paths[1])
    request = TrainingApprovalRequest(data["model_id"], data["model_revision"], data["train_sha256"],
        data["heldout_sha256"], tuple(data["scopes"]), data["training_recipe"], data["manifest_sha256"], data["domain_id"])
    material = asdict(request)
    material["scopes"] = list(request.scopes)
    case["request_data"].clear()
    case["request_data"].update(material)
    observed = _mock_training_stack(monkeypatch, boundary=boundary)
    request, client, grant, calls = _real_http_client(case)
    verifier = p.make_owned_training_approval_verifier(case["gate"], actor_id=grant["actor_id"],
        domain_id=request.domain_id, context=_context(request))
    def execute():
        with case["app"].test_request_context("/", headers={"Authorization": grant["identity"]},
                environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
            return training.run_owned_lora_training(paths[0], paths[2], paths[3], paths[4],
                manifest_path=paths[1], execute=True, approval_verifier=verifier, phase_client=client)
    return execute, client, calls, observed, paths


def test_simulated_compute_composes_all_nine_boundaries_with_actual_metadata(phase_http, tmp_path, monkeypatch):
    execute, client, calls, observed, paths = _simulated_training_with_actual_metadata(phase_http, tmp_path, monkeypatch)
    result = execute()
    assert result["execution_state"] == "TRAINED_NOT_EVALUATED"
    assert result["candidate_status"] == "NOT_EVALUATED"
    phases = [body["phase"] for method, path, body in calls if path.endswith("/challenges")]
    assert phases == ["initial", "before_output_dir", "before_train", "step_begin", "substep_end",
                      "pre_optimizer_step", "before_adapter_save", "before_tokenizer_save", "after_saved_artifact_check"]
    assert observed["optimizer_steps"] == observed["save_calls"] == 1
    assert (paths[-1] / "adapter_model.safetensors").read_bytes() == b"synthetic-unit-artifact"


def test_simulated_worker_cancel_with_actual_metadata_stops_before_optimizer(phase_http, tmp_path, monkeypatch):
    client_box = []
    def boundary(name):
        if name == "0:on_pre_optimizer_step": client_box[0].cancel()
    execute, client, calls, observed, paths = _simulated_training_with_actual_metadata(
        phase_http, tmp_path, monkeypatch, boundary=boundary)
    client_box.append(client)
    with pytest.raises(TrainingBlocked, match="CANCELLED_AT_BOUNDARY"): execute()
    assert observed["optimizer_steps"] == observed["save_calls"] == 0
    assert not (paths[-1] / "adapter_model.safetensors").exists()
    assert json.loads((paths[-1] / "training_status.json").read_text())["execution_state"] == "TRAINING_CANCELLED_AT_BOUNDARY"


def test_actual_metadata_lost_response_prevents_output_write_and_physical_retry(phase_http, tmp_path, monkeypatch):
    execute, client, calls, observed, paths = _simulated_training_with_actual_metadata(phase_http, tmp_path, monkeypatch)
    actual_transport = client._transport
    def lost_reply(method, path, body):
        reply = actual_transport(method, path, body)
        if path.endswith("/challenge-decisions") and body["challenge"]["phase"] == "before_output_dir":
            raise ConnectionError("isolated response loss after actual metadata commit")
        return reply
    client._transport = lost_reply
    with pytest.raises(TrainingBlocked, match="TRANSPORT_FAILED"): execute()
    assert not paths[-1].exists() and observed["train_calls"] == 0
    history = client.read_last_history()
    assert history["authorization_usable"] is False and history["challenge"]["phase"] == "before_output_dir"
    with pytest.raises(TrainingBlocked, match="PHYSICAL_RECOVERY_REQUIRED"):
        client.authorize(client._request, "before_output_dir")
    assert not paths[-1].exists()
