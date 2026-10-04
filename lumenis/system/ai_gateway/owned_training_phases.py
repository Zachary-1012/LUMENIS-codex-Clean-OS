"""Client binding for the existing sealed training metadata HTTP contract.

The authenticated transport and original public pin come from the existing
owner. This module supplies no host, credentials, Grant, signer or model permit.
Historical receipts are evidence only. Physical checkpoint recovery is separate.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
from dataclasses import asdict
from typing import Callable

from .owned_training import TrainingApprovalRequest, TrainingBlocked
from lumenis.system.security import training_receipts


class TrainingPhaseBlocked(TrainingBlocked):
    """A phase cannot safely continue under the current bound metadata state."""


class TrainingPublicContext:
    """Public request hashes, with no actor, session, approval or authority.

    A supervised worker can check its request without manufacturing a local
    principal. Every execution check still goes to the authenticated owner.
    """

    def __init__(self, request, context, fingerprints):
        def text(value, limit=512):
            return (type(value) is str and value and value == value.strip()
                    and len(value) <= limit and not any(ord(c) < 32 for c in value))

        if (type(request) is not TrainingApprovalRequest or request.domain_id not in {"cth", "bmp"}
                or not all(text(v) for v in (request.model_id, request.model_revision, request.recipe))
                or any(type(v) is not str or re.fullmatch(r"[0-9a-f]{64}", v) is None
                       for v in (request.manifest_sha256, request.train_sha256, request.heldout_sha256))
                or type(request.scopes) is not tuple or not request.scopes
                or any(not text(v, 256) for v in request.scopes)
                or len(set(request.scopes)) != len(request.scopes)
                or type(context) is not dict or set(context) != {"scope_descriptors"}
                or type(context["scope_descriptors"]) is not dict
                or set(context["scope_descriptors"]) != set(request.scopes)):
            raise TrainingPhaseBlocked("TRAINING_PHASE_REQUEST_CHANGED")
        descriptors = []
        for scope in request.scopes:
            value = context["scope_descriptors"][scope]
            if (type(value) is not dict
                    or set(value) != {"domain_id", "product_id", "global_scope", "subject_id", "brand_focus_id"}
                    or value["domain_id"] != request.domain_id
                    or value["product_id"] != {"cth": "CTH", "bmp": "ZBMP"}[request.domain_id]
                    or type(value["global_scope"]) is not bool):
                raise TrainingPhaseBlocked("CHECKPOINT_SCOPE_MISMATCH")
            if value["global_scope"]:
                valid = scope == "GLOBAL / ALL" and value["subject_id"] is None and value["brand_focus_id"] is None
            elif request.domain_id == "cth":
                valid = text(value["subject_id"], 256) and scope == value["subject_id"] and value["brand_focus_id"] is None
            else:
                valid = text(value["brand_focus_id"], 256) and scope == value["brand_focus_id"] and value["subject_id"] is None
            if not valid:
                raise TrainingPhaseBlocked("CHECKPOINT_SCOPE_MISMATCH")
            descriptors.append({"scope": scope, **value})
        def digest(value):
            return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
        public_request = {"schema_version": 1, "operation": "model_train", "domain_id": request.domain_id,
            "model_id": request.model_id, "model_revision": request.model_revision, "recipe": request.recipe,
            "manifest_sha256": request.manifest_sha256, "train_sha256": request.train_sha256,
            "heldout_sha256": request.heldout_sha256, "scopes": list(request.scopes), "scope_descriptors": descriptors}
        expected = {"request_sha256": digest(public_request),
            "model_identity_sha256": digest({"schema_version": 1, "model_id": request.model_id, "model_revision": request.model_revision}),
            "manifest_sha256": request.manifest_sha256, "train_sha256": request.train_sha256,
            "heldout_sha256": request.heldout_sha256, "recipe_sha256": digest({"schema_version": 1, "recipe": request.recipe}),
            "scope_sha256": digest({"schema_version": 1, "domain_id": request.domain_id,
                "scopes": list(request.scopes), "scope_descriptors": descriptors})}
        if type(fingerprints) is not dict or fingerprints != expected:
            raise TrainingPhaseBlocked("TRAINING_PHASE_REQUEST_CHANGED")
        self._request = request
        self._context = copy.deepcopy(context)
        self._fingerprints = expected

    def fingerprints_for(self, request, context):
        if type(request) is not TrainingApprovalRequest or request != self._request or context != self._context:
            raise TrainingPhaseBlocked("TRAINING_PHASE_REQUEST_CHANGED")
        # Recompute on read; mutating a public value never changes its binding.
        checked = TrainingPublicContext(request, context, self._fingerprints)
        return dict(checked._fingerprints)


class TrainingPhaseClient:
    """Serialize fresh phase checks through an owner-supplied authenticated caller.

    transport(method, relative_path, body) returns the parsed response dict and
    raises on HTTP/transport failure. It must be admitted by the current host,
    identity and Permission owners; a Python callable is not deployment proof.
    No retries or physical resume are inferred from metadata acknowledgements.
    """

    _ROOT = "/api/experience/owned-training/phase-tasks"

    def __init__(self, request: TrainingApprovalRequest, context: dict, *,
                 pinned_public_key: dict, transport: Callable | None = None,
                 actor_id: int | None = None, principal=None, public_context=None):
        from lumenis.system.security.permission import owned_training_phase_fingerprints

        if public_context is None:
            self._fingerprints = owned_training_phase_fingerprints(
                request, context=context, domain_id=request.domain_id,
                actor_id=actor_id, principal=principal)
        elif type(public_context) is TrainingPublicContext and actor_id is None and principal is None:
            self._fingerprints = public_context.fingerprints_for(request, context)
        else:
            raise TrainingPhaseBlocked("TRAINING_PHASE_REQUEST_CHANGED")
        training_receipts._validate_pinned_public_key(pinned_public_key)
        self._pin = copy.deepcopy(pinned_public_key)
        self._request = request
        material = asdict(request)
        material["scopes"] = list(request.scopes)
        self._body = {"training_request": material,
                      "scope_descriptors": copy.deepcopy(context["scope_descriptors"])}
        if transport is not None and not callable(transport):
            raise ValueError("an owner-supplied authenticated transport is required")
        self._transport = transport
        self._lock = threading.RLock()
        self._task_id = None
        self._run_digest = None
        self._task_digest = None
        self._sequence = None
        self._uncertain = False
        self._cancelled = threading.Event()
        self._last_challenge = None
        self._last_receipt = None
        self._recovery_handoff = None

    @classmethod
    def from_prepared_task(cls, request, context, *, prepared_task, pinned_public_key,
                           transport, actor_id=None, principal=None, public_context=None):
        """Reuse the exact owner-prepared Task; signed fresh phases still gate work."""
        if cls is not TrainingPhaseClient:
            raise TrainingPhaseBlocked("TRAINING_PHASE_TASK_BINDING_INVALID")
        client = cls(request, context, pinned_public_key=pinned_public_key, transport=transport,
            actor_id=actor_id, principal=principal, public_context=public_context)
        client._accept_prepared_task(copy.deepcopy(prepared_task))
        return client

    @classmethod
    def from_recovery_handoff(cls, request: TrainingApprovalRequest, context: dict, *,
                              handoff, pinned_public_key: dict, transport: Callable,
                              actor_id: int | None = None, principal=None, public_context=None):
        """Bind an explicitly loaded attempt without replaying the old run.

        The checkpoint owner supplies the signed one-use handoff. Its current
        Task, worker and Permission state is checked again by the phase owner
        before admitting the first resumed before_train action.
        """
        if cls is not TrainingPhaseClient:
            raise TrainingPhaseBlocked("CHECKPOINT_REQUEST_INVALID")
        verified_type = getattr(training_receipts, "VerifiedTrainingRecoveryHandoff", None)
        if verified_type is None:
            raise TrainingPhaseBlocked("CHECKPOINT_CONTRACT_NOT_BOUND")
        if type(handoff) is not verified_type or not callable(transport):
            raise TrainingPhaseBlocked("CHECKPOINT_REQUEST_INVALID")
        client = cls(request, context, pinned_public_key=pinned_public_key,
                     transport=transport, actor_id=actor_id, principal=principal, public_context=public_context)
        envelope = copy.deepcopy(handoff.envelope)
        payload = envelope.get("payload") if type(envelope) is dict else None
        if type(payload) is not dict or payload.get("fingerprints") != client._fingerprints:
            raise TrainingPhaseBlocked("CHECKPOINT_SCOPE_MISMATCH")
        task_id = payload.get("task_id")
        if (type(task_id) is not str
                or re.fullmatch(r"trainrelay_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", task_id) is None
                or payload.get("task_digest") != hashlib.sha256(task_id.encode("utf-8")).hexdigest()
                or type(payload.get("next_sequence")) is not int or payload["next_sequence"] < 1
                or type(payload.get("run_digest")) is not str
                or re.fullmatch(r"[0-9a-f]{64}", payload["run_digest"]) is None
                or type(payload.get("schema_version")) is not int or payload["schema_version"] != 1
                or type(payload.get("admission_version")) is not int or payload["admission_version"] != 3
                or payload.get("next_phase") != "before_train"):
            raise TrainingPhaseBlocked("CHECKPOINT_REQUEST_INVALID")
        client._recovery_handoff = envelope
        client._require_recovery_handoff()
        client._task_id = task_id
        client._task_digest = payload["task_digest"]
        client._run_digest = payload["run_digest"]
        client._sequence = payload["next_sequence"]
        return client

    def _require_recovery_handoff(self) -> None:
        verifier = getattr(training_receipts, "verify_training_recovery_handoff", None)
        verified_type = getattr(training_receipts, "VerifiedTrainingRecoveryHandoff", None)
        if not callable(verifier) or verified_type is None:
            raise TrainingPhaseBlocked("CHECKPOINT_CONTRACT_NOT_BOUND")
        try:
            verified = verifier(
                copy.deepcopy(self._recovery_handoff),
                expected_payload=copy.deepcopy(self._recovery_handoff["payload"]),
                pinned_public_key=self._pin,
            )
        except training_receipts.TrainingReceiptError:
            raise TrainingPhaseBlocked("CHECKPOINT_REQUEST_INVALID") from None
        if type(verified) is not verified_type:
            raise TrainingPhaseBlocked("CHECKPOINT_REQUEST_INVALID")

    def cancel(self) -> None:
        """Request cooperative stop at the next caller boundary; no process claim."""
        self._cancelled.set()

    def _call(self, method: str, suffix: str = "", body=None) -> dict:
        if self._transport is None:
            raise TrainingPhaseBlocked("TRAINING_PHASE_TRANSPORT_NOT_BOUND")
        try:
            reply = self._transport(method, self._ROOT + suffix, copy.deepcopy(body))
        except Exception:
            raise TrainingPhaseBlocked("TRAINING_PHASE_TRANSPORT_FAILED") from None
        if type(reply) is not dict or reply.get("ok") is not True:
            raise TrainingPhaseBlocked("TRAINING_PHASE_RESPONSE_DENIED")
        return copy.deepcopy(reply)

    def _prepare(self) -> None:
        self._accept_prepared_task(self._call("POST", body=self._body))

    def _accept_prepared_task(self, reply):
        if type(reply) is not dict or reply.get("ok") is not True:
            raise TrainingPhaseBlocked("TRAINING_PHASE_TASK_BINDING_INVALID")
        state = reply.get("public_challenge_context")
        task_id = reply.get("task_id")
        if (reply.get("state") != "PHASE_TASK_PREPARED"
                or reply.get("training_started") is not False
                or reply.get("approval_issued") is not False
                or reply.get("pinned_public_key") != self._pin
                or type(task_id) is not str
                or re.fullmatch(r"trainrelay_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", task_id) is None
                or type(state) is not dict
                or state.get("admission_version") != 2
                or state.get("fingerprints") != self._fingerprints
                or state.get("pinned_public_key") != self._pin
                or type(state.get("run_digest")) is not str
                or re.fullmatch(r"[0-9a-f]{64}", state["run_digest"]) is None
                or state.get("task_digest") != hashlib.sha256(task_id.encode("utf-8")).hexdigest()
                or type(state.get("next_sequence")) is not int):
            raise TrainingPhaseBlocked("TRAINING_PHASE_TASK_BINDING_INVALID")
        # A server-admitted phase is not proof of its completed physical action.
        # Never rewind or silently skip it on a restarted worker.
        if (state.get("last_phase") is not None or state.get("terminal") is not False
                or state.get("status") != "ready" or state["next_sequence"] != 1):
            raise TrainingPhaseBlocked("TRAINING_PHYSICAL_RECOVERY_REQUIRED")
        self._task_id = task_id
        self._task_digest = state["task_digest"]
        self._run_digest = state["run_digest"]
        self._sequence = state["next_sequence"]

    def authorize(self, request: TrainingApprovalRequest, phase: str) -> None:
        """Check one current receipt, then return immediately to the existing permit.

        A lost decision response leaves the physical action unperformed by this
        caller and its metadata outcome uncertain. Historical readback cannot
        authorize that action. The owner must reconcile recovery explicitly.
        """
        with self._lock:
            if self._cancelled.is_set():
                raise TrainingPhaseBlocked("TRAINING_CANCELLED_AT_BOUNDARY")
            if type(request) is not TrainingApprovalRequest or request != self._request:
                raise TrainingPhaseBlocked("TRAINING_PHASE_REQUEST_CHANGED")
            if self._uncertain:
                raise TrainingPhaseBlocked("TRAINING_PHYSICAL_RECOVERY_REQUIRED")
            if self._recovery_handoff is not None:
                if phase != "before_train":
                    raise TrainingPhaseBlocked("CHECKPOINT_REQUEST_INVALID")
                self._require_recovery_handoff()
                # Preparing the first resumed challenge consumes the one-use
                # owner handoff. A lost response cannot safely be retried here.
                self._uncertain = True
            if self._task_id is None:
                if phase != "initial":
                    raise TrainingPhaseBlocked("TRAINING_PHASE_INITIAL_REQUIRED")
                self._prepare()
            reply = self._call("POST", f"/{self._task_id}/challenges",
                               {**self._body, "phase": phase})
            challenge = reply.get("challenge")
            try:
                challenge = training_receipts.validate_training_phase_challenge(challenge)
            except training_receipts.TrainingReceiptError:
                raise TrainingPhaseBlocked("TRAINING_PHASE_CHALLENGE_INVALID") from None
            expected = {**self._fingerprints, "task_digest": self._task_digest,
                        "run_digest": self._run_digest, "phase": phase,
                        "sequence": self._sequence}
            if (reply.get("state") != "PHASE_CHALLENGE_PREPARED"
                    or reply.get("pinned_public_key") != self._pin
                    or reply.get("model_execution_claimed") is not False
                    or any(type(challenge.get(k)) is not type(v) or challenge[k] != v
                           for k, v in expected.items())):
                raise TrainingPhaseBlocked("TRAINING_PHASE_CHALLENGE_BINDING_INVALID")
            self._last_challenge = challenge
            self._uncertain = True
            decision = self._call("POST", f"/{self._task_id}/challenge-decisions",
                                  {**self._body, "challenge": challenge})
            if (decision.get("state") != "PHASE_RECEIPT_COMMITTED"
                    or decision.get("historical") is True
                    or decision.get("authorization_usable") is False
                    or decision.get("model_execution_claimed") is not False
                    or type(decision.get("next_sequence")) is not int
                    or decision["next_sequence"] != self._sequence + 1):
                raise TrainingPhaseBlocked("TRAINING_PHASE_FRESH_RECEIPT_REQUIRED")
            try:
                training_receipts.verify_training_phase_decision(
                    decision.get("receipt"), expected_challenge=challenge,
                    pinned_public_key=self._pin,
                )
            except training_receipts.TrainingReceiptError:
                raise TrainingPhaseBlocked("TRAINING_PHASE_RECEIPT_INVALID") from None
            if self._cancelled.is_set():
                raise TrainingPhaseBlocked("TRAINING_CANCELLED_AT_BOUNDARY")
            self._last_receipt = decision["receipt"]
            self._sequence = decision["next_sequence"]
            self._uncertain = False
            self._recovery_handoff = None

    def require_current_receipt(self) -> None:
        """Recheck expiry/cancellation after the separate live model permit check."""
        with self._lock:
            if self._cancelled.is_set():
                raise TrainingPhaseBlocked("TRAINING_CANCELLED_AT_BOUNDARY")
            if self._uncertain or self._last_receipt is None:
                raise TrainingPhaseBlocked("TRAINING_PHASE_FRESH_RECEIPT_REQUIRED")
            try:
                training_receipts.verify_training_phase_decision(
                    self._last_receipt, expected_challenge=self._last_challenge,
                    pinned_public_key=self._pin,
                )
            except training_receipts.TrainingReceiptError:
                raise TrainingPhaseBlocked("TRAINING_PHASE_RECEIPT_EXPIRED_OR_INVALID") from None

    def read_last_history(self) -> dict:
        """Recover signed bytes without authorizing any physical reexecution."""
        with self._lock:
            if self._last_challenge is None:
                raise TrainingPhaseBlocked("TRAINING_PHASE_HISTORY_NOT_AVAILABLE")
            challenge = self._last_challenge
            reply = self._call("GET", f"/{self._task_id}/receipts/{challenge['nonce']}")
            if (reply.get("historical") is not True
                    or reply.get("authorization_usable") is not False
                    or reply.get("model_execution_claimed") is not False):
                raise TrainingPhaseBlocked("TRAINING_PHASE_HISTORY_INVALID")
            if reply.get("state") == "PHASE_RECEIPT_NOT_COMMITTED" and reply.get("receipt") is None:
                return reply
            if (reply.get("challenge") != challenge
                    or reply.get("pinned_public_key") != self._pin):
                raise TrainingPhaseBlocked("TRAINING_PHASE_HISTORY_INVALID")
            try:
                training_receipts.verify_training_phase_decision(
                    reply.get("receipt"), expected_challenge=challenge,
                    pinned_public_key=self._pin, now=reply["receipt"]["issued_at"],
                )
            except (training_receipts.TrainingReceiptError, KeyError, TypeError):
                raise TrainingPhaseBlocked("TRAINING_PHASE_HISTORY_INVALID") from None
            return reply
