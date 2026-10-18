# -*- coding: utf-8 -*-
"""LUMENIS SYSTEM canonical Effect Fence and side-effect idempotency.

The fence is the last deterministic boundary before a handler may create an
external or persistent side effect. It never promotes Agent/AI output directly
into Production Truth.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .action_firewall import AgentAction


_PRODUCTION_TARGETS = (
    "production_db", "prod_db", "master_db", "生产库", "主库",
    "production_truth", "canonical_data", "zbc_canonical_data",
)
_MUTATING = {
    AgentAction.WRITE, AgentAction.COMMIT, AgentAction.PUSH, AgentAction.DEPLOY,
}


@dataclass
class FenceDecision:
    allowed: bool
    action: str
    fenced: bool
    reason: str
    target: str = ""
    effect_mode: str = "read_only"
    requires_staging: bool = False
    requires_manual_validation: bool = False
    auto_admit: bool = False
    idempotency_key: Optional[str] = None
    idempotent_hit: bool = False
    reservation_status: str = "none"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkillMetadataFenceDecision:
    """Immutable, current admission decision for one metadata-only skill change."""

    allowed: bool
    code: str
    state: str
    resource: Optional[str] = None
    operation_id: Optional[str] = None
    candidate_sha256: Optional[str] = None
    actor_id: Optional[int] = None
    caller: Optional[str] = None
    principal_kind: Optional[str] = None
    principal_ref: Optional[str] = None
    domain_id: Optional[str] = None
    subject_id: Optional[str] = None
    brand_focus_id: Optional[str] = None
    global_scope: bool = False
    permission_audit_id: Optional[str] = None
    scope_audit_id: Optional[str] = None
    fence_audit_id: Optional[str] = None
    approval_token_sha256: Optional[str] = None
    idempotent_hit: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrainingPhaseMetadataFenceDecision:
    """Admission of one durable task-state change, never model execution."""

    allowed: bool
    code: str
    task_id: str
    mutation: str
    resource: Optional[str] = None
    state_sha256: Optional[str] = None
    approval_token_sha256: Optional[str] = None
    permission_audit_id: Optional[str] = None
    fence_audit_id: Optional[str] = None
    effect_mode: str = "owned_training_task_metadata"
    model_execution_allowed: bool = False


_SKILL_AUDIT_ID = re.compile(r"^aud_[0-9a-f]{16}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SKILL_HISTORY_INPUTS = frozenset({
    "schema_version", "skill_id", "action", "operation_id", "before_sha256",
    "after_sha256", "config_sha256", "restore_evidence_ref", "candidate_sha256",
    "identity", "scope", "resource", "permission_audit_id", "scope_audit_id",
    "fence_audit_id", "approval_token_sha256", "commit_verification",
})


class EffectFence:
    """Single owner for side-effect admission and idempotency reservations."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._reservations: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _skill_metadata_fence_audit(gate, *, resource, caller, allowed, code) -> Optional[str]:
        """Record the fence result through the canonical gate without token material."""
        try:
            from . import permission

            if type(gate) is not permission.PermissionGate or gate is not permission.get_permission_gate():
                return None
            audit_id = gate._write_audit(
                operation_type="skill_metadata_fence",
                resource=resource,
                risk_level=permission.RiskLevel.HIGH.value,
                permission_required=permission.PermissionLevel.COMMIT.value,
                caller=caller or "anonymous",
                result="allowed" if allowed else "denied",
                reason=code,
                operation_id=None,
                approval_token=None,
            )
            return audit_id if type(audit_id) is str and _SKILL_AUDIT_ID.fullmatch(audit_id) else None
        except Exception:
            return None

    @staticmethod
    def _skill_metadata_connection_is_canonical(connection) -> bool:
        """Check only the supplied handle; never open a second database connection."""
        if type(connection) is not sqlite3.Connection or not connection.in_transaction:
            return False
        from lumenis.shared.database import get_repository, main_db_path

        expected = getattr(get_repository(), "db_path", None) or main_db_path()
        expected = os.path.normcase(os.path.abspath(expected))
        rows = connection.execute("PRAGMA database_list").fetchall()
        main_path = next((row[2] for row in rows if row[1] == "main"), None)
        if type(main_path) is not str or not main_path:
            return False
        actual = os.path.normcase(os.path.abspath(main_path))
        return actual == expected

    @staticmethod
    def _skill_metadata_candidate(candidate):
        from lumenis.shared.agents.skills import lifecycle

        lifecycle._validate_candidate(candidate)
        if candidate.action not in {"update", "uninstall", "restore", "review_mcp_contract"}:
            raise ValueError("SKILL_METADATA_ACTION_INVALID")
        lifecycle._operation_id(candidate.operation_id)
        if not all(_SHA256.fullmatch(value or "") for value in (
            candidate.before_sha256, candidate.after_sha256,
            candidate.candidate_sha256, candidate.config_sha256,
        )):
            raise ValueError("SKILL_METADATA_HASH_INVALID")
        before = json.loads(candidate._before_json)
        after = json.loads(candidate._after_json)
        lifecycle._safe_metadata(before)
        lifecycle._safe_metadata(after)
        if before["skill_id"] != candidate.skill_id or after["skill_id"] != candidate.skill_id:
            raise ValueError("SKILL_METADATA_IDENTITY_CHANGED")
        if (before["product"], before["domain"]) != (after["product"], after["domain"]):
            raise ValueError("SKILL_METADATA_OWNER_CHANGED")
        if candidate.action == "review_mcp_contract":
            mutable = {"compatibility_json", "status", "health_state"}
            if (after["status"] != "disabled" or after["health_state"] != "unknown"
                    or before["runtime"] != "mcp" or before["install_state"] != "installed"
                    or any(after[key] != before[key] for key in before if key not in mutable)):
                raise ValueError("SKILL_METADATA_EFFECT_SCOPE_INVALID")
            old = json.loads(before["compatibility_json"] or "{}")
            new = json.loads(after["compatibility_json"] or "{}")
            contract_keys = {"mcp_tool_contracts", "mcp_protocol_version", "mcp_reviewed_tools", "mcp_runtime_binding"}
            if (not isinstance(old, dict) or not isinstance(new, dict)
                    or {k: v for k, v in old.items() if k not in contract_keys} != {k: v for k, v in new.items() if k not in contract_keys}
                    or new.get("mcp_protocol_version") != "2025-11-25"):
                raise ValueError("SKILL_METADATA_MCP_CONTRACT_INVALID")
            from mcp_skill_runtime import runtime_contract_binding
            if new.get("mcp_runtime_binding") != runtime_contract_binding(before):
                raise ValueError("SKILL_METADATA_MCP_RUNTIME_CHANGED")
            from mcp_discovery import tool_contract_hash
            tools = new.get("mcp_reviewed_tools")
            if not isinstance(tools, list) or not tools or any(not isinstance(tool, dict) for tool in tools):
                raise ValueError("SKILL_METADATA_MCP_CONTRACT_INVALID")
            contracts = {tool.get("name"): tool_contract_hash(tool) for tool in tools}
            if (len(contracts) != len(tools) or set(contracts) != set(json.loads(after["tools_json"]))
                    or new.get("mcp_tool_contracts") != contracts):
                raise ValueError("SKILL_METADATA_MCP_CONTRACT_INVALID")
        else:
            if (after["status"] != "disabled" or after["permissions_granted_json"] != "[]"
                    or after["trust_level"] != "unverified" or after["health_state"] != "unknown"
                    or after["install_state"] != "not_installed" or after["install_path"] is not None
                    or after["active_version"] is not None or after["previous_version"] != before["version"]
                    or after["lifecycle_state"] != ("uninstalled" if candidate.action == "uninstall" else "validated")
                    or (candidate.action == "uninstall" and after["entrypoint"] is not None)):
                raise ValueError("SKILL_METADATA_EFFECT_SCOPE_INVALID")
        if candidate.action == "restore":
            if not isinstance(candidate.restore_evidence_ref, str) or not candidate.restore_evidence_ref:
                raise ValueError("SKILL_METADATA_RESTORE_REFERENCE_INVALID")
        elif candidate.restore_evidence_ref is not None:
            raise ValueError("SKILL_METADATA_RESTORE_REFERENCE_INVALID")
        return lifecycle, before, after

    @staticmethod
    def _skill_metadata_scope_from_decision(decision):
        return {
            "domain_id": decision.domain_id,
            "subject_id": decision.subject_id,
            "brand_focus_id": decision.brand_focus_id,
            "global_scope": decision.global_scope,
        }

    @staticmethod
    def _skill_metadata_validate_permission_decision(permission, decision, resource, candidate):
        expected_state = permission.SkillMetadataPermissionDecision
        if type(decision) is not expected_state or decision.allowed is not True:
            code = decision.code if type(decision) is expected_state else "SKILL_METADATA_PERMISSION_UNVERIFIED"
            raise PermissionError(code)
        if (decision.resource != resource or decision.operation_id != candidate.operation_id
                or decision.candidate_sha256 != candidate.candidate_sha256
                or type(decision.permission_audit_id) is not str
                or not _SKILL_AUDIT_ID.fullmatch(decision.permission_audit_id)
                or type(decision.scope_audit_id) is not str
                or not _SKILL_AUDIT_ID.fullmatch(decision.scope_audit_id)
                or type(decision.approval_token_sha256) is not str
                or not _SHA256.fullmatch(decision.approval_token_sha256)):
            raise PermissionError("SKILL_METADATA_PERMISSION_BINDING_INVALID")

    @staticmethod
    def _skill_metadata_validate_history(connection, replay_evidence_ref, candidate, identity, scope, resource):
        from lumenis.shared.agents.skills import lifecycle

        if not isinstance(replay_evidence_ref, str):
            raise ValueError("SKILL_METADATA_REPLAY_REFERENCE_INVALID")
        row, inputs, outputs = lifecycle._history_row(connection, replay_evidence_ref, candidate.skill_id)
        if (row.get("subject_scope"), row.get("capture_mode"), row.get("domain_id"),
                row.get("product_id"), row.get("subject_id"), row.get("brand_focus_id"),
                row.get("global_scope")) not in {
                ("SYSTEM", "manual_metadata_admission", None, None, None, None, None),
                ("SYSTEM", "manual_metadata_admission", None, None, None, None, 0),
        }:
            raise ValueError("SKILL_METADATA_REPLAY_OWNER_MISMATCH")
        if set(inputs) != _SKILL_HISTORY_INPUTS:
            raise ValueError("SKILL_METADATA_REPLAY_SCHEMA_INVALID")
        material = lifecycle._candidate_material(candidate)
        expected_inputs = {key: value for key, value in material.items()
                           if key not in {"before_metadata", "after_metadata"}}
        expected_inputs["candidate_sha256"] = candidate.candidate_sha256
        for key, value in expected_inputs.items():
            if inputs.get(key) != value:
                raise ValueError("SKILL_METADATA_REPLAY_CANDIDATE_MISMATCH")
        if inputs.get("identity") != identity or inputs.get("scope") != scope or inputs.get("resource") != resource:
            raise ValueError("SKILL_METADATA_REPLAY_CONTEXT_MISMATCH")
        if set(outputs) != {"before_metadata", "after_metadata", "config_sha256"}:
            raise ValueError("SKILL_METADATA_REPLAY_OUTPUT_INVALID")
        if outputs.get("before_metadata") != material["before_metadata"] \
                or outputs.get("after_metadata") != material["after_metadata"] \
                or outputs.get("config_sha256") != candidate.config_sha256:
            raise ValueError("SKILL_METADATA_REPLAY_OUTPUT_MISMATCH")

        audit_fields = ("permission_audit_id", "scope_audit_id", "fence_audit_id")
        for name in audit_fields:
            if type(inputs.get(name)) is not str or not _SKILL_AUDIT_ID.fullmatch(inputs[name]):
                raise ValueError("SKILL_METADATA_REPLAY_AUDIT_INVALID")
        if type(inputs.get("approval_token_sha256")) is not str or not _SHA256.fullmatch(inputs["approval_token_sha256"]):
            raise ValueError("SKILL_METADATA_REPLAY_APPROVAL_INVALID")
        commit = inputs.get("commit_verification")
        if type(commit) is not dict or set(commit) != {
                "permission_audit_id", "scope_audit_id", "fence_audit_id", "approval_token_sha256"}:
            raise ValueError("SKILL_METADATA_REPLAY_COMMIT_INVALID")
        for name in audit_fields:
            if type(commit.get(name)) is not str or not _SKILL_AUDIT_ID.fullmatch(commit[name]):
                raise ValueError("SKILL_METADATA_REPLAY_COMMIT_INVALID")
        if type(commit.get("approval_token_sha256")) is not str or not _SHA256.fullmatch(commit["approval_token_sha256"]):
            raise ValueError("SKILL_METADATA_REPLAY_COMMIT_INVALID")
        return row, outputs

    def check_skill_metadata_change(
        self, candidate, *, connection, gate, actor_id=None, principal=None, domain_id,
        subject_id=None, brand_focus_id=None, global_scope=False, phase="before_write",
        replay_evidence_ref=None,
    ) -> SkillMetadataFenceDecision:
        """Authorize one exact metadata-only registry transition on its caller transaction."""
        fields: Dict[str, Any] = {
            "state": "denied", "operation_id": getattr(candidate, "operation_id", None),
            "candidate_sha256": getattr(candidate, "candidate_sha256", None),
            "actor_id": actor_id, "domain_id": domain_id, "subject_id": subject_id,
            "brand_focus_id": brand_focus_id,
            "global_scope": global_scope if type(global_scope) is bool else False,
            "idempotent_hit": False,
        }
        resource = None
        caller = None
        permission_result = None
        code = "SKILL_METADATA_FENCE_UNVERIFIED"
        allowed = False
        try:
            from . import permission

            if phase not in {"before_write", "before_commit", "replay"}:
                raise ValueError("SKILL_METADATA_FENCE_PHASE_INVALID")
            lifecycle, before, after = self._skill_metadata_candidate(candidate)
            if not self._skill_metadata_connection_is_canonical(connection):
                raise PermissionError("SKILL_METADATA_CANONICAL_TRANSACTION_REQUIRED")
            fields.update(operation_id=candidate.operation_id, candidate_sha256=candidate.candidate_sha256)
            if str(before["source_type"] or "builtin").lower() == "builtin":
                raise PermissionError("BUILTIN_SKILL_METADATA_CHANGE_NOT_SUPPORTED")

            resource = permission.skill_metadata_approval_resource(
                candidate, actor_id=actor_id, principal=principal, domain_id=domain_id,
                subject_id=subject_id, brand_focus_id=brand_focus_id, global_scope=global_scope,
            )
            if phase == "replay":
                current = lifecycle._registry_row(connection, candidate.skill_id)
                if lifecycle._snapshot(current) != after or lifecycle._hash(current["config_json"]) != candidate.config_sha256:
                    raise PermissionError("SKILL_METADATA_REPLAY_CURRENT_STATE_MISMATCH")
                # The signed admission binds the original caller/scope, and replay must use that same context.
                row, outputs = self._skill_metadata_validate_history(
                    connection, replay_evidence_ref, candidate,
                    self._identity_payload(actor_id, principal, permission),
                    self._scope_payload(domain_id, subject_id, brand_focus_id, global_scope, permission),
                    resource,
                )
                identity = self._identity_payload(actor_id, principal, permission)
                scope = self._scope_payload(domain_id, subject_id, brand_focus_id, global_scope, permission)
            elif phase == "before_write":
                current = lifecycle._registry_row(connection, candidate.skill_id)
                if lifecycle._snapshot(current) != before or lifecycle._hash(current) != candidate.before_sha256 \
                        or lifecycle._hash(current["config_json"]) != candidate.config_sha256:
                    raise PermissionError("SKILL_METADATA_REGISTRY_BEFORE_MISMATCH")
                identity = self._identity_payload(actor_id, principal, permission)
                scope = self._scope_payload(domain_id, subject_id, brand_focus_id, global_scope, permission)
            else:
                current = lifecycle._registry_row(connection, candidate.skill_id)
                if lifecycle._snapshot(current) != after or lifecycle._hash(lifecycle._snapshot(current)) != candidate.after_sha256 \
                        or lifecycle._hash(current["config_json"]) != candidate.config_sha256:
                    raise PermissionError("SKILL_METADATA_REGISTRY_AFTER_MISMATCH")
                identity = self._identity_payload(actor_id, principal, permission)
                scope = self._scope_payload(domain_id, subject_id, brand_focus_id, global_scope, permission)

            caller = identity.get("caller")
            fields.update(identity, **scope)
            permission_result = permission.check_skill_metadata_change_permission(
                candidate, gate=gate, actor_id=actor_id, principal=principal,
                domain_id=domain_id, subject_id=subject_id,
                brand_focus_id=brand_focus_id, global_scope=global_scope,
            )
            self._skill_metadata_validate_permission_decision(permission, permission_result, resource, candidate)
            identity = {name: getattr(permission_result, name) for name in
                        ("actor_id", "caller", "principal_kind", "principal_ref")}
            scope = self._skill_metadata_scope_from_decision(permission_result)
            if phase == "replay":
                # Readback only: fresh approval is required, while its token may differ from the signed original.
                audit = self._skill_metadata_fence_audit(
                    gate, resource=resource, caller=identity["caller"], allowed=True,
                    code="SKILL_METADATA_ALREADY_APPLIED",
                )
                if not audit:
                    raise PermissionError("SKILL_METADATA_FENCE_AUDIT_UNAVAILABLE")
                return SkillMetadataFenceDecision(
                    allowed=True, code="SKILL_METADATA_ALREADY_APPLIED", state="already_applied",
                    resource=resource, operation_id=candidate.operation_id,
                    candidate_sha256=candidate.candidate_sha256, **identity, **scope,
                    permission_audit_id=permission_result.permission_audit_id,
                    scope_audit_id=permission_result.scope_audit_id, fence_audit_id=audit,
                    approval_token_sha256=permission_result.approval_token_sha256,
                    idempotent_hit=True,
                )

            current = lifecycle._registry_row(connection, candidate.skill_id)
            if phase == "before_write":
                exact = (lifecycle._snapshot(current) == before
                         and lifecycle._hash(current) == candidate.before_sha256)
            else:
                snapshot = lifecycle._snapshot(current)
                exact = snapshot == after and lifecycle._hash(snapshot) == candidate.after_sha256
            if not exact or lifecycle._hash(current["config_json"]) != candidate.config_sha256:
                raise PermissionError(
                    "SKILL_METADATA_REGISTRY_BEFORE_MISMATCH" if phase == "before_write"
                    else "SKILL_METADATA_REGISTRY_AFTER_MISMATCH"
                )
            state = "admitted" if phase == "before_write" else "commit_verified"
            success_code = "SKILL_METADATA_ADMITTED" if phase == "before_write" else "SKILL_METADATA_COMMIT_VERIFIED"
            audit = self._skill_metadata_fence_audit(
                gate, resource=resource, caller=identity["caller"], allowed=True,
                code=success_code,
            )
            if not audit:
                raise PermissionError("SKILL_METADATA_FENCE_AUDIT_UNAVAILABLE")
            return SkillMetadataFenceDecision(
                allowed=True, code=success_code, state=state,
                resource=resource, operation_id=candidate.operation_id,
                candidate_sha256=candidate.candidate_sha256, **identity, **scope,
                permission_audit_id=permission_result.permission_audit_id,
                scope_audit_id=permission_result.scope_audit_id, fence_audit_id=audit,
                approval_token_sha256=permission_result.approval_token_sha256,
                idempotent_hit=False,
            )
        except Exception as exc:
            code = str(exc) if isinstance(exc, (ValueError, PermissionError, RuntimeError)) else code
            if type(code) is not str or not code.startswith("SKILL_") and not code.startswith("BUILTIN_"):
                code = "SKILL_METADATA_FENCE_UNVERIFIED"
        audit = self._skill_metadata_fence_audit(
            gate, resource=resource, caller=caller, allowed=allowed, code=code,
        )
        fields["fence_audit_id"] = audit
        if permission_result is not None:
            for name in ("permission_audit_id", "scope_audit_id", "approval_token_sha256"):
                fields[name] = getattr(permission_result, name, None)
            for name in ("actor_id", "caller", "principal_kind", "principal_ref", "domain_id",
                         "subject_id", "brand_focus_id", "global_scope", "resource", "operation_id",
                         "candidate_sha256"):
                value = getattr(permission_result, name, None)
                if name == "resource":
                    resource = value
                fields[name] = value
        elif resource is not None:
            fields["resource"] = resource
        fields["allowed"] = False
        fields["code"] = code
        return SkillMetadataFenceDecision(**fields)

    @staticmethod
    def _identity_payload(actor_id, principal, permission):
        return permission._skill_metadata_identity(actor_id=actor_id, principal=principal)

    @staticmethod
    def _scope_payload(domain_id, subject_id, brand_focus_id, global_scope, permission):
        if type(global_scope) is not bool:
            raise ValueError("SKILL_METADATA_SCOPE_INVALID")
        domain = domain_id.lower() if type(domain_id) is str else domain_id
        if domain == "zbmp":
            domain = "bmp"
        return {"domain_id": domain, "subject_id": subject_id,
                "brand_focus_id": brand_focus_id, "global_scope": global_scope}

    @staticmethod
    def _digest(action: AgentAction, target: str, payload: Dict[str, Any]) -> str:
        body = json.dumps(
            {"action": action.value, "target": target, "payload": payload},
            ensure_ascii=False, sort_keys=True, default=str,
        )
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_staging(payload: Dict[str, Any]) -> bool:
        mode = str(
            payload.get("effect_mode")
            or payload.get("stage")
            or payload.get("environment")
            or ""
        ).strip().lower()
        return bool(payload.get("staging") is True or mode in {"staging", "preview", "dry_run", "dry-run"})

    def authorize_training_phase_metadata(
        self, *, connection, task_id, mutation, training_request, context,
        domain_id, gate, approval, approval_reference, expected_state,
        actor_id=None, principal=None, capture_mode,
    ) -> TrainingPhaseMetadataFenceDecision:
        """Verify the staged sealed Task row on its canonical transaction.

        The exact existing MODEL_TRAIN grant admits only this metadata change.
        This seam cannot authorize a trainer, weights, data changes or any
        external effect. Generic Production Truth denial remains independent.
        """
        fields = dict(task_id=task_id, mutation=mutation)
        try:
            from ai_task_engine import TaskEngine, get_task_engine
            from . import permission

            if (type(self) is not EffectFence or self is not get_effect_fence()
                    or capture_mode != "owned_training_task_metadata"
                    or mutation not in {"create", "challenge", "receipt", "interrupt", "resume"}
                    or type(gate) is not permission.PermissionGate
                    or gate is not permission.get_permission_gate()
                    or not gate.fail_closed or permission.is_testing_bypass_enabled()):
                raise PermissionError("OWNED_TRAINING_PHASE_FENCE_UNAVAILABLE")
            TaskEngine._require_training_receipt_connection(connection)
            engine = get_task_engine()
            if type(engine) is not TaskEngine:
                raise PermissionError("OWNED_TRAINING_PHASE_TASK_OWNER_UNAVAILABLE")
            args = {"actor_id": actor_id, "principal": principal}
            identity = permission.owned_training_identity(**args)
            resource = permission.owned_training_approval_resource(
                training_request, context=context, domain_id=domain_id, **args,
            )
            fields["resource"] = resource
            verifier = permission.make_owned_training_approval_verifier(
                gate, context=context, domain_id=domain_id, **args,
            )
            if not verifier(training_request):
                raise PermissionError("OWNED_TRAINING_PHASE_FENCE_APPROVAL_REQUIRED")
            reference = gate.owned_training_approval_reference(
                training_request=training_request, context=context, domain_id=domain_id,
                approval=approval, **args,
            )
            if reference != approval_reference:
                raise PermissionError("OWNED_TRAINING_PHASE_APPROVAL_REPLACED")
            binding = {"resource": resource, "scope_descriptors": context["scope_descriptors"],
                       "identity": {name: identity[name] for name in
                                    ("actor_id", "caller", "principal_kind", "principal_ref")}}
            material = engine.get_training_receipt_history_material(
                task_id, expected_identity=binding["identity"], connection=connection,
            )
            if (material["binding"] != binding or material["approval_reference"] != reference
                    or material["fingerprints"] != permission.owned_training_phase_fingerprints(
                        training_request, context=context, domain_id=domain_id, **args)):
                raise PermissionError("OWNED_TRAINING_PHASE_FENCE_BINDING_MISMATCH")
            state = engine.require_training_receipt_admission(
                task_id, binding, reference, material["pinned_public_key"], connection,
            )
            if type(expected_state) is not dict or state != expected_state:
                raise PermissionError("OWNED_TRAINING_PHASE_FENCE_STATE_CHANGED")
            if mutation == "interrupt" and state["status"] != "unknown":
                raise PermissionError("OWNED_TRAINING_PHASE_FENCE_STATE_CHANGED")
            if mutation == "resume" and state["status"] != "ready":
                raise PermissionError("OWNED_TRAINING_PHASE_FENCE_STATE_CHANGED")
            row = connection.execute(
                "SELECT context_json FROM ai_task WHERE task_id=?", (task_id,),
            ).fetchone()
            if row is None or type(row[0]) is not str:
                raise PermissionError("OWNED_TRAINING_PHASE_FENCE_STATE_UNAVAILABLE")
            state_sha256 = hashlib.sha256(json.dumps(
                {"state": state, "context_json": row[0]}, ensure_ascii=False,
                sort_keys=True, separators=(",", ":"), allow_nan=False,
            ).encode("utf-8")).hexdigest()
            audit = gate._write_audit(
                operation_type="owned_training_phase_metadata_fence", resource=resource,
                risk_level=permission.RiskLevel.HIGH.value,
                permission_required=permission.PermissionLevel.COMMIT.value,
                caller=identity["caller"], result="allowed",
                reason="OWNED_TRAINING_PHASE_METADATA_ADMITTED_NOT_COMMITTED",
                operation_id=None, approval_token=None,
            )
            if type(audit) is not str or not _SKILL_AUDIT_ID.fullmatch(audit):
                raise PermissionError("OWNED_TRAINING_PHASE_FENCE_AUDIT_UNAVAILABLE")
            return TrainingPhaseMetadataFenceDecision(
                allowed=True, code="OWNED_TRAINING_PHASE_METADATA_ADMITTED_NOT_COMMITTED",
                **fields, state_sha256=state_sha256,
                approval_token_sha256=reference["approval_token_sha256"],
                permission_audit_id=approval.audit_id, fence_audit_id=audit,
            )
        except Exception as exc:
            code = str(exc)
            if (type(code) is not str or not code.startswith("OWNED_TRAINING_")
                    or len(code) > 100 or re.fullmatch(r"[A-Z_0-9]+", code) is None):
                code = "OWNED_TRAINING_PHASE_FENCE_UNVERIFIED"
            return TrainingPhaseMetadataFenceDecision(allowed=False, code=code, **fields)

    def authorize_training_checkpoint_metadata(
        self, *, connection, task_id, mutation, training_request, context,
        domain_id, gate, approval, approval_reference, expected_state,
        actor_id=None, principal=None, capture_mode="owned_training_checkpoint_metadata",
    ) -> TrainingPhaseMetadataFenceDecision:
        """Admit the exact staged v3 Task/Artifact change, never GPU execution.

        expected_state is {execution: current v3 execution, operation: current
        save/load operation or None during execution initialization}. It is
        re-read through the existing sealed Task owner on this transaction.
        No existing v2 mutation is widened to admit physical checkpoint work.
        """
        fields = dict(task_id=task_id, mutation=mutation)
        try:
            from ai_task_engine import TaskEngine, get_task_engine
            from . import permission
            if (type(self) is not EffectFence or self is not get_effect_fence()
                    or capture_mode != "owned_training_checkpoint_metadata"
                    or mutation not in {"reserve", "start", "commit", "load", "renew", "recovery-phase"}
                    or type(gate) is not permission.PermissionGate or gate is not permission.get_permission_gate()
                    or not gate.fail_closed or permission.is_testing_bypass_enabled()
                    or type(expected_state) is not dict or set(expected_state) != {"execution", "operation"}):
                raise PermissionError("OWNED_TRAINING_CHECKPOINT_FENCE_UNAVAILABLE")
            TaskEngine._require_training_receipt_connection(connection)
            engine = get_task_engine()
            if type(engine) is not TaskEngine:
                raise PermissionError("OWNED_TRAINING_CHECKPOINT_TASK_OWNER_UNAVAILABLE")
            args = {"actor_id": actor_id, "principal": principal}
            identity = permission.owned_training_identity(**args)
            resource = permission.owned_training_approval_resource(
                training_request, context=context, domain_id=domain_id, **args)
            fields["resource"] = resource
            if not permission.make_owned_training_approval_verifier(
                    gate, context=context, domain_id=domain_id, **args)(training_request):
                raise PermissionError("OWNED_TRAINING_CHECKPOINT_FENCE_APPROVAL_REQUIRED")
            reference = gate.owned_training_approval_reference(
                training_request=training_request, context=context, domain_id=domain_id,
                approval=approval, **args)
            if reference != approval_reference:
                raise PermissionError("OWNED_TRAINING_CHECKPOINT_APPROVAL_REPLACED")
            binding = {"resource": resource, "scope_descriptors": context["scope_descriptors"],
                "identity": {name: identity[name] for name in
                    ("actor_id", "caller", "principal_kind", "principal_ref")}}
            material = engine.get_training_receipt_history_material(
                task_id, expected_identity=binding["identity"], connection=connection)
            fingerprints = permission.owned_training_phase_fingerprints(
                training_request, context=context, domain_id=domain_id, **args)
            if (material["binding"] != binding or material["approval_reference"] != reference
                    or material["fingerprints"] != fingerprints):
                raise PermissionError("OWNED_TRAINING_CHECKPOINT_FENCE_BINDING_MISMATCH")
            owner_args = dict(expected_binding=binding, expected_approval_reference=reference,
                pinned_public_key=material["pinned_public_key"], connection=connection)
            execution = engine.training_execution_read(task_id, **owner_args)
            if execution is None or execution != expected_state["execution"]:
                raise PermissionError("OWNED_TRAINING_CHECKPOINT_FENCE_STATE_CHANGED")
            operation = expected_state["operation"]
            if operation is None:
                if mutation != "reserve":
                    raise PermissionError("OWNED_TRAINING_CHECKPOINT_FENCE_STATE_CHANGED")
            else:
                if type(operation) is not dict or type(operation.get("operation_id")) is not str:
                    raise PermissionError("OWNED_TRAINING_CHECKPOINT_FENCE_STATE_CHANGED")
                current = engine.training_operation_read(task_id, operation_id=operation["operation_id"], **owner_args)
                allowed = {"reserve": {"RESERVED", "LOAD_ADMITTED"}, "start": {"WRITING", "LOADING"},
                    "commit": {"COMMITTED"}, "load": {"LOADED", "RUNNABLE"},
                    "renew": {"LOAD_ADMITTED"}, "recovery-phase": {"LOADED", "RUNNABLE"}}
                if current != operation or current["state"] not in allowed[mutation]:
                    raise PermissionError("OWNED_TRAINING_CHECKPOINT_FENCE_STATE_CHANGED")
            state_sha256 = hashlib.sha256(json.dumps(
                expected_state, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            audit = gate._write_audit(
                operation_type="owned_training_checkpoint_metadata_fence", resource=resource,
                risk_level=permission.RiskLevel.HIGH.value, permission_required=permission.PermissionLevel.COMMIT.value,
                caller=identity["caller"], result="allowed", reason="OWNED_TRAINING_CHECKPOINT_METADATA_ADMITTED_NOT_COMMITTED",
                operation_id=None if operation is None else operation["operation_id"], approval_token=None)
            if type(audit) is not str or not _SKILL_AUDIT_ID.fullmatch(audit):
                raise PermissionError("OWNED_TRAINING_CHECKPOINT_FENCE_AUDIT_UNAVAILABLE")
            return TrainingPhaseMetadataFenceDecision(
                allowed=True, code="OWNED_TRAINING_CHECKPOINT_METADATA_ADMITTED_NOT_COMMITTED",
                **fields, state_sha256=state_sha256, approval_token_sha256=reference["approval_token_sha256"],
                permission_audit_id=approval.audit_id, fence_audit_id=audit,
                effect_mode="owned_training_checkpoint_metadata")
        except Exception as exc:
            code = str(exc)
            if (type(code) is not str or not code.startswith("OWNED_TRAINING_")
                    or len(code) > 100 or re.fullmatch(r"[A-Z_0-9]+", code) is None):
                code = "OWNED_TRAINING_CHECKPOINT_FENCE_UNVERIFIED"
            return TrainingPhaseMetadataFenceDecision(allowed=False, code=code, **fields,
                effect_mode="owned_training_checkpoint_metadata")

    def check(
        self,
        *,
        action: AgentAction,
        target: str = "",
        payload: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None,
    ) -> FenceDecision:
        payload = dict(payload or {})
        target_text = str(target or "")
        lower_target = target_text.lower()

        if action not in _MUTATING:
            return FenceDecision(
                allowed=True,
                action=action.value,
                fenced=True,
                reason="non-mutating action passed Effect Fence",
                target=target_text,
                effect_mode="read_only",
                reservation_status="not_required",
            )

        if any(marker in lower_target for marker in _PRODUCTION_TARGETS):
            return FenceDecision(
                allowed=False,
                action=action.value,
                fenced=True,
                reason="direct mutation of Production Truth is hard-denied",
                target=target_text,
                effect_mode="blocked",
                requires_staging=True,
                requires_manual_validation=True,
                reservation_status="rejected",
            )

        if not self._is_staging(payload):
            return FenceDecision(
                allowed=False,
                action=action.value,
                fenced=True,
                reason="mutating action requires explicit staging/dry-run effect mode before execution",
                target=target_text,
                effect_mode="blocked",
                requires_staging=True,
                requires_manual_validation=True,
                reservation_status="rejected",
            )

        digest = self._digest(action, target_text, payload)
        key = str(operation_id or digest)
        with self._lock:
            existing = self._reservations.get(key)
            if existing is not None:
                if existing["digest"] != digest:
                    return FenceDecision(
                        allowed=False,
                        action=action.value,
                        fenced=True,
                        reason="idempotency key collision with different side-effect payload",
                        target=target_text,
                        effect_mode="staging",
                        requires_staging=True,
                        requires_manual_validation=True,
                        idempotency_key=key,
                        idempotent_hit=True,
                        reservation_status="conflict",
                    )
                return FenceDecision(
                    allowed=False,
                    action=action.value,
                    fenced=True,
                    reason="duplicate side-effect request blocked by idempotency reservation",
                    target=target_text,
                    effect_mode="staging",
                    requires_staging=True,
                    requires_manual_validation=True,
                    idempotency_key=key,
                    idempotent_hit=True,
                    reservation_status=existing.get("status", "reserved"),
                )

            self._reservations[key] = {
                "digest": digest,
                "status": "reserved",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        return FenceDecision(
            allowed=True,
            action=action.value,
            fenced=True,
            reason="staging side effect reserved; Production Truth admission remains manual",
            target=target_text,
            effect_mode="staging",
            requires_staging=True,
            requires_manual_validation=True,
            auto_admit=False,
            idempotency_key=key,
            reservation_status="reserved",
        )

    def check_pattern_transition(self, admission, *, connection, phase="before_write"):
        """Typed derived learning metadata only; generic production-write denial stays intact."""
        from . import permission
        import content_generation as content
        if phase not in {"before_write", "before_commit"}:
            raise PermissionError("PATTERN_FENCE_PHASE_INVALID")
        permission.validate_pattern_transition_admission(admission, connection=connection)
        binding = json.loads(admission.binding_json)
        rebuilt = content._pattern_transition_binding_from_selectors(
            binding, connection=connection, after_write=phase == "before_commit")
        if binding != rebuilt:
            raise PermissionError("PATTERN_FENCE_BINDING_CHANGED")
        return {"allowed": True, "effect_mode": "content_pattern_derived_transition",
                "binding_hash": admission.binding_hash, "approval_id": admission.approval_id,
                "activation_resource": admission.activation_resource,
                "write_resource": admission.write_resource,
                "production_truth_write": False, "model_execution_allowed": False}

    def complete(self, idempotency_key: Optional[str], *, success: bool) -> None:
        if not idempotency_key:
            return
        with self._lock:
            item = self._reservations.get(idempotency_key)
            if item is None:
                return
            item["status"] = "completed" if success else "failed"
            item["finished_at"] = datetime.now(timezone.utc).isoformat()

    def clear_for_testing(self) -> None:
        with self._lock:
            self._reservations.clear()


_default_fence = EffectFence()


def get_effect_fence() -> EffectFence:
    return _default_fence


__all__ = ["FenceDecision", "SkillMetadataFenceDecision", "TrainingPhaseMetadataFenceDecision",
           "EffectFence", "get_effect_fence"]
