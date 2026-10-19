"""Held-out evaluation and scoped capture for an exact owned Gateway candidate.

Inference is supplied by an already loaded local runtime. Derived reports use
the existing Evidence owner; no separate store, provider, model loader,
business verdict, or promotion path is created here.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from . import owned_training

_TERMINATORS = frozenset({"<|return|>", "<|fim_suffix|>"})
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_CITATION = re.compile(r"\[\[([^\[\]\r\n]+)\]\]")
_FINAL_HEADER = re.compile(
    r"(?:<\|start\|>|<\|im_start\|>)assistant<\|channel\|>final<\|message\|>"
    r"|<\|channel\|>final<\|message\|>"
    r"|<\|assistant\|>(?:<\|channel\|>)?final(?:[ \t\r\n]|$)"
)
_CHANNEL_MARKER = re.compile(r"<\|(?:start|im_start|assistant|channel|message|meta_sep)\|>")
_STATUS_IDENTITY = (
    "status", "model_id", "model_revision", "training_recipe", "base_revision_state",
    "manifest_sha256", "train_sha256", "heldout_sha256", "train_case_count",
    "heldout_case_count", "scopes", "domain_id",
)

BUSINESS_REVIEW_RUBRIC = (
    ("TASK_AND_SCOPE", "Does the result answer the actual held-out job for this exact CTH/BMP scope?"),
    ("EVIDENCE_GROUNDING", "Does each material claim follow from the cited source Evidence, with unsupported claims marked unknown?"),
    ("DELIVERABLE_COMPLETENESS", "Does it provide the requested decision or artifact, required entities, period, and next step?"),
    ("UNKNOWN_VS_ZERO", "Does it preserve 0, NULL, UNKNOWN, NOT_COLLECTED, STALE, OFFLINE, ERROR, and BLOCKED as distinct states?"),
    ("BUSINESS_ACTIONABILITY", "Are rationale, constraints, alternatives, risks, and an executable next action clear?"),
    ("PERMISSION_AND_RIGHTS", "Does it stay within the approved scope and avoid unsupported rights or external effects?"),
    ("LIMITS_AND_RECOVERY", "Are material uncertainty, stop conditions, and failure or recovery needs explicit?"),
)

_EVALUATION_CAPTURE_VERSION = "owned-evaluation-packet:v1"
_EVALUATION_CAPTURE_RESOURCE = "owned_evaluation_capture:v1:"
_EVALUATION_FEATURE = "OWNED_MODEL_EVALUATION_PACKET"
_EVALUATION_REF = re.compile(r"^app_evidence_records:([1-9][0-9]*)$")
_EVALUATION_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_EVALUATION_PACKET_FIELDS = frozenset({
    "evaluation_status", "candidate_status", "business_acceptance",
    "runtime_verification", "generation_config", "promotion_status",
    "candidate_identity", "candidate_identity_sha256", "heldout_case_count",
    "completed_final_count", "business_review_rubric", "cases",
})
_EVALUATION_CASE_FIELDS = frozenset({
    "case_id", "domain_id", "scope", "source_evidence_refs", "heldout_origin",
    "prompt_sha256", "completion_state", "final_text", "raw_output_sha256",
    "citation_state", "termination_token", "cited_source_refs",
    "unresolved_citation_refs", "business_review",
})
_CANDIDATE_IDENTITY_FIELDS = frozenset({
    *_STATUS_IDENTITY, "execution_state", "candidate_status",
    "training_status_sha256", "adapter_sha256", "adapter_config_sha256",
})
_COMPLETION_STATES = frozenset({
    "COMPLETED_FINAL", "OUTPUT_MISSING",
    "TERMINATION_TOKEN_UNSPECIFIED_OR_UNSUPPORTED",
    "FINAL_CHANNEL_PREFILL_METADATA_INVALID", "GENERATION_NOT_COMPLETE",
    "CONFIGURED_TERMINATION_MISSING_OR_TRUNCATED", "FINAL_CHANNEL_MISSING",
    "FINAL_CHANNEL_OR_PREFILL_MISSING", "FINAL_CHANNEL_EMPTY_OR_INVALID",
})


def _evaluation_json(value: Any) -> str:
    """Serialize evaluator data without lossy key coercion or non-finite values."""
    def json_types(item: Any) -> bool:
        if item is None or type(item) in (str, bool, int):
            return True
        if type(item) is float:
            return item == item and item not in (float("inf"), float("-inf"))
        if type(item) is list:
            return all(json_types(child) for child in item)
        if type(item) is dict:
            return all(type(key) is str and json_types(child) for key, child in item.items())
        return False

    if not json_types(value):
        raise ValueError("OWNED_EVALUATION_JSON_VALUE_INVALID")
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )


def _evaluation_packet_sha256(packet: Mapping[str, Any]) -> str:
    return hashlib.sha256(_evaluation_json(packet).encode("utf-8")).hexdigest()


def _clean_packet_text(value: Any, *, limit: int = 4096, empty: bool = False) -> bool:
    return (
        type(value) is str
        and (empty or bool(value))
        and len(value) <= limit
        and not any(ord(character) < 32 and character not in "\t\n\r" for character in value)
    )


def _capture_scope(expected_scope: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reuse the existing owned-training scope normalizer, never infer GLOBAL."""
    from lumenis.shared.learning import training_cases

    try:
        scope_input = json.loads(_evaluation_json(expected_scope))
        return training_cases._scope(scope_input)
    except Exception as exc:
        raise ValueError("OWNED_EVALUATION_SCOPE_INVALID") from exc


def _capture_identity(
    authenticated_actor: Mapping[str, Any] | None,
    principal: Any,
) -> dict[str, Any]:
    from lumenis.system.security import permission

    if principal is None:
        actor_id = authenticated_actor.get("id") if isinstance(authenticated_actor, Mapping) else None
        if type(actor_id) is not int or actor_id <= 0:
            raise PermissionError("OWNED_EVALUATION_AUTHENTICATED_ACTOR_REQUIRED")
    else:
        if authenticated_actor is not None:
            raise PermissionError("OWNED_EVALUATION_IDENTITY_MIXED")
        actor_id = None
    try:
        identity = permission.owned_training_identity(actor_id=actor_id, principal=principal)
    except Exception as exc:
        raise PermissionError("OWNED_EVALUATION_SERVER_IDENTITY_REQUIRED") from exc
    if identity.get("identity_kind") == "workspace":
        try:
            current = permission.resolve_local_workspace_principal(
                module="owned_model_admission", action="write",
            )
        except Exception:
            current = None
        if not (
            type(principal) is permission.LocalWorkspacePrincipal
            and permission._is_server_local_workspace_principal(principal)
            and type(current) is permission.LocalWorkspacePrincipal
            and permission._is_server_local_workspace_principal(current)
            and current == principal
        ):
            raise PermissionError("OWNED_EVALUATION_WORKSPACE_PRINCIPAL_STALE")
    return identity


def _validate_evaluation_packet(
    packet: Any,
    *,
    expected_scope: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    if type(packet) is not dict or set(packet) != _EVALUATION_PACKET_FIELDS:
        raise ValueError("OWNED_EVALUATION_PACKET_SCHEMA_INVALID")
    packet_json = _evaluation_json(packet)
    frozen_packet = json.loads(packet_json)
    if type(expected_scope) is not dict:
        raise ValueError("OWNED_EVALUATION_SCOPE_INVALID")
    scope, _marker = _capture_scope(expected_scope)
    scope_domain = "bmp" if scope["domain_id"] == "zbmp" else "cth"
    scope_label = (
        "GLOBAL / ALL" if scope["global"]
        else scope.get("subject_id") or scope.get("brand_focus_id")
    )

    identity = frozen_packet["candidate_identity"]
    if type(identity) is not dict or set(identity) != _CANDIDATE_IDENTITY_FIELDS:
        raise ValueError("OWNED_EVALUATION_CANDIDATE_IDENTITY_INVALID")
    identity_domain = identity.get("domain_id")
    if identity_domain == "zbmp":
        identity_domain = "bmp"
    if identity_domain != scope_domain:
        raise ValueError("OWNED_EVALUATION_CANDIDATE_SCOPE_MISMATCH")
    identity_scopes = identity.get("scopes")
    if (
        type(identity_scopes) is not list
        or not identity_scopes
        or any(not _clean_packet_text(item, limit=512) for item in identity_scopes)
        or len(set(identity_scopes)) != len(identity_scopes)
        or scope_label not in identity_scopes
    ):
        raise ValueError("OWNED_EVALUATION_CANDIDATE_SCOPE_MISMATCH")
    for field in (
        "model_id", "model_revision", "training_recipe", "base_revision_state",
        "status", "execution_state", "candidate_status",
    ):
        if not _clean_packet_text(identity.get(field), limit=512):
            raise ValueError("OWNED_EVALUATION_CANDIDATE_IDENTITY_INVALID")
    for field in (
        "manifest_sha256", "train_sha256", "heldout_sha256", "training_status_sha256",
        "adapter_sha256", "adapter_config_sha256",
    ):
        if type(identity.get(field)) is not str or _DIGEST.fullmatch(identity[field]) is None:
            raise ValueError("OWNED_EVALUATION_CANDIDATE_IDENTITY_INVALID")
    for field in ("train_case_count", "heldout_case_count"):
        if type(identity.get(field)) is not int or identity[field] < 1:
            raise ValueError("OWNED_EVALUATION_CANDIDATE_IDENTITY_INVALID")
    if (identity["execution_state"], identity["candidate_status"]) != (
        "TRAINED_NOT_EVALUATED", "NOT_EVALUATED",
    ):
        raise ValueError("OWNED_EVALUATION_CANDIDATE_STATUS_CONTRADICTORY")
    candidate_identity_sha256 = hashlib.sha256(json.dumps(
        identity, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()
    if frozen_packet.get("candidate_identity_sha256") != candidate_identity_sha256:
        raise ValueError("OWNED_EVALUATION_CANDIDATE_IDENTITY_HASH_MISMATCH")

    generation = frozen_packet["generation_config"]
    accepted_terminators = sorted(_TERMINATORS)
    if (
        type(generation) is not dict
        or set(generation) != {"max_new_tokens", "accepted_termination_tokens"}
        or type(generation.get("max_new_tokens")) is not int
        or not 1 <= generation["max_new_tokens"] <= 4096
        or generation.get("accepted_termination_tokens") != accepted_terminators
    ):
        raise ValueError("OWNED_EVALUATION_GENERATION_CONFIG_INVALID")
    expected_rubric = [
        {"criterion": key, "question": question}
        for key, question in BUSINESS_REVIEW_RUBRIC
    ]
    if frozen_packet.get("business_review_rubric") != expected_rubric:
        raise ValueError("OWNED_EVALUATION_REVIEW_RUBRIC_INVALID")
    if (
        frozen_packet.get("candidate_status") != "NOT_ACCEPTED"
        or frozen_packet.get("business_acceptance") != "HUMAN_REVIEW_REQUIRED"
        or frozen_packet.get("runtime_verification") != "CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED"
        or frozen_packet.get("promotion_status") != "NOT_PROMOTED"
    ):
        raise ValueError("OWNED_EVALUATION_ACCEPTANCE_STATUS_CONTRADICTORY")

    cases = frozen_packet.get("cases")
    if (
        type(cases) is not list or not cases
        or type(frozen_packet.get("heldout_case_count")) is not int
        or frozen_packet["heldout_case_count"] != len(cases)
        or type(frozen_packet.get("completed_final_count")) is not int
    ):
        raise ValueError("OWNED_EVALUATION_CASE_COUNT_INVALID")
    case_ids: set[str] = set()
    completed = 0
    for case in cases:
        if type(case) is not dict or set(case) != _EVALUATION_CASE_FIELDS:
            raise ValueError("OWNED_EVALUATION_CASE_SCHEMA_INVALID")
        case_id = case.get("case_id")
        if not _clean_packet_text(case_id, limit=512) or case_id in case_ids:
            raise ValueError("OWNED_EVALUATION_CASE_ID_INVALID")
        case_ids.add(case_id)
        if case.get("domain_id") != scope_domain or case.get("scope") != scope_label:
            raise ValueError("OWNED_EVALUATION_MIXED_OR_MISMATCHED_SCOPE")
        refs = case.get("source_evidence_refs")
        if (
            type(refs) is not list or not refs
            or any(not _clean_packet_text(ref, limit=1024) for ref in refs)
            or len(set(refs)) != len(refs)
        ):
            raise ValueError("OWNED_EVALUATION_SOURCE_REFS_INVALID")
        origin = case.get("heldout_origin")
        if (
            type(origin) is not dict
            or set(origin) != {"dataset_role", "dataset_sha256", "record_sha256"}
            or origin.get("dataset_role") != "heldout"
            or any(type(origin.get(name)) is not str or _DIGEST.fullmatch(origin[name]) is None
                   for name in ("dataset_sha256", "record_sha256"))
            or origin["dataset_sha256"] != identity["heldout_sha256"]
        ):
            raise ValueError("OWNED_EVALUATION_HELDOUT_ORIGIN_INVALID")
        if any(type(case.get(name)) is not str or _DIGEST.fullmatch(case[name]) is None
               for name in ("prompt_sha256",)):
            raise ValueError("OWNED_EVALUATION_CASE_HASH_INVALID")
        state = case.get("completion_state")
        if not (
            (type(state) is str and state in _COMPLETION_STATES)
            or (type(state) is str and re.fullmatch(r"INFERENCE_ERROR:[A-Za-z][A-Za-z0-9_]{0,127}", state))
        ):
            raise ValueError("OWNED_EVALUATION_COMPLETION_STATE_INVALID")
        if type(case.get("final_text")) is not str or not _clean_packet_text(
            case["final_text"], limit=65536, empty=True,
        ):
            raise ValueError("OWNED_EVALUATION_FINAL_TEXT_INVALID")
        raw_hash = case.get("raw_output_sha256")
        if type(raw_hash) is not str or (raw_hash and _DIGEST.fullmatch(raw_hash) is None):
            raise ValueError("OWNED_EVALUATION_RAW_OUTPUT_HASH_INVALID")
        terminator = case.get("termination_token")
        if not _clean_packet_text(terminator, limit=128, empty=True):
            raise ValueError("OWNED_EVALUATION_TERMINATION_METADATA_INVALID")
        if state == "COMPLETED_FINAL":
            if not case["final_text"] or not raw_hash or terminator not in _TERMINATORS:
                raise ValueError("OWNED_EVALUATION_COMPLETED_OUTPUT_INVALID")
            completed += 1
        elif case["final_text"]:
            raise ValueError("OWNED_EVALUATION_INCOMPLETE_OUTPUT_CONTRADICTORY")

        citations = _CITATION.findall(case["final_text"])
        expected_known = sorted({ref for ref in citations if ref in refs})
        expected_unknown = sorted({ref for ref in citations if ref not in refs})
        if (
            case.get("cited_source_refs") != expected_known
            or case.get("unresolved_citation_refs") != expected_unknown
            or case.get("citation_state") != (
                "PRESENT" if expected_known else "UNRESOLVED" if citations else "MISSING"
            )
        ):
            raise ValueError("OWNED_EVALUATION_CITATION_STATE_INVALID")
        review = case.get("business_review")
        expected_criteria = {key: "PENDING" for key, _ in BUSINESS_REVIEW_RUBRIC}
        if (
            type(review) is not dict or set(review) != {"state", "criteria"}
            or review.get("state") != "HUMAN_REVIEW_REQUIRED"
            or review.get("criteria") != expected_criteria
        ):
            raise ValueError("OWNED_EVALUATION_BUSINESS_REVIEW_NOT_PENDING")

    if (
        frozen_packet["completed_final_count"] != completed
        or identity["heldout_case_count"] != len(cases)
    ):
        raise ValueError("OWNED_EVALUATION_COMPLETED_COUNT_MISMATCH")
    expected_status = "STRUCTURAL_OUTPUTS_CAPTURED" if completed == len(cases) else "INCOMPLETE_OUTPUTS_RECORDED"
    if frozen_packet.get("evaluation_status") != expected_status:
        raise ValueError("OWNED_EVALUATION_STATUS_MISMATCH")
    return frozen_packet, packet_json


def _evaluation_capture_material(
    *,
    authenticated_actor: Mapping[str, Any] | None,
    expected_scope: dict[str, Any],
    submission_id: str,
    evaluation_packet: Any,
    principal: Any,
) -> dict[str, Any]:
    if (
        type(submission_id) is not str
        or _EVALUATION_UUID.fullmatch(submission_id) is None
        or str(uuid.UUID(submission_id)) != submission_id
    ):
        raise ValueError("OWNED_EVALUATION_SUBMISSION_ID_INVALID")
    identity = _capture_identity(authenticated_actor, principal)
    scope, marker = _capture_scope(expected_scope)
    packet, packet_json = _validate_evaluation_packet(
        evaluation_packet, expected_scope=scope,
    )
    packet_sha256 = hashlib.sha256(packet_json.encode("utf-8")).hexdigest()
    return {
        "identity": identity,
        "principal": principal,
        "scope": scope,
        "scope_marker": marker,
        "submission_id": submission_id,
        "packet": packet,
        "packet_json": packet_json,
        "packet_sha256": packet_sha256,
        "candidate_identity_sha256": packet["candidate_identity_sha256"],
    }


def _evaluation_capture_resource(material: Mapping[str, Any]) -> str:
    identity = material["identity"]
    scope = material["scope"]
    payload = {
        "schema_version": 1,
        "operation": "db_write",
        "purpose": ("synthetic_interpretability_capture" if material.get("interpretability") is True
                    else "derived_owned_evaluation_packet_capture"),
        "candidate_identity_sha256": material["candidate_identity_sha256"],
        "evaluation_packet_sha256": material["packet_sha256"],
        "submission_id": material["submission_id"],
        "actor_id": identity["actor_id"],
        "caller": identity["caller"],
        "identity_kind": identity["identity_kind"],
        "domain_id": scope["domain_id"],
        "scope": scope,
    }
    if identity["identity_kind"] == "workspace":
        payload["principal_kind"] = identity["principal_kind"]
        payload["principal_ref"] = identity["principal_ref"]
    resource_hash = hashlib.sha256(_evaluation_json(payload).encode("utf-8")).hexdigest()
    return _EVALUATION_CAPTURE_RESOURCE + resource_hash


def owned_evaluation_capture_approval_resource(
    *,
    authenticated_actor: Mapping[str, Any] | None = None,
    expected_scope: dict[str, Any],
    submission_id: str,
    evaluation_packet: Any,
    principal: Any = None,
) -> str:
    """Build the exact capture-only DB_WRITE resource; this grants no permission."""
    material = _evaluation_capture_material(
        authenticated_actor=authenticated_actor,
        expected_scope=expected_scope,
        submission_id=submission_id,
        evaluation_packet=evaluation_packet,
        principal=principal,
    )
    return _evaluation_capture_resource(material)


def _authorize_evaluation_capture(
    gate: Any,
    material: Mapping[str, Any],
    resource: str,
    *,
    connection: Any = None,
) -> dict[str, str]:
    from lumenis.system.security import permission

    if (
        type(gate) is not permission.PermissionGate
        or permission.get_permission_gate() is not gate
        or gate.fail_closed is not True
        or permission.is_testing_bypass_enabled()
        or not gate.has_permission(permission.PermissionLevel.COMMIT)
    ):
        raise PermissionError("OWNED_EVALUATION_PERMISSION_GATE_UNAVAILABLE")
    operation_spec = gate._registry.get(permission.OperationType.DB_WRITE)
    if not (
        type(operation_spec) is permission.OperationSpec
        and operation_spec.permission is permission.PermissionLevel.COMMIT
        and operation_spec.risk is permission.RiskLevel.HIGH
        and operation_spec.auto_allow is False
    ):
        raise PermissionError("OWNED_EVALUATION_DB_WRITE_POLICY_CHANGED")

    identity = _capture_identity(
        {"id": material["identity"]["actor_id"]}
        if material["identity"]["identity_kind"] == "account" else None,
        material["principal"],
    )
    if identity != material["identity"]:
        raise PermissionError("OWNED_EVALUATION_IDENTITY_CHANGED")
    scope = material["scope"]
    domain = "bmp" if scope["domain_id"] == "zbmp" else "cth"
    scope_args = {
        "domain_id": domain,
        "action": "write",
        "module": "owned_model_admission",
        "subject_id": scope.get("subject_id"),
        "brand_focus_id": scope.get("brand_focus_id"),
        "global_scope": scope["global"],
        "gate": gate,
    }
    if connection is not None:
        scope_args["connection"] = connection
    if identity["identity_kind"] == "workspace":
        scoped = permission.check_local_workspace_scope_permission(
            material["principal"], **scope_args,
        )
    else:
        scoped = permission.check_actor_scope_permission(
            {"id": identity["actor_id"]}, **scope_args,
        )
    canonical_domain = permission._canonical_business_domain_id(domain)
    focus = scope.get("subject_id") if domain == "cth" else scope.get("brand_focus_id")
    expected_scope_resource = f"{domain}:{'GLOBAL / ALL' if scope['global'] else focus}"
    if not (
        type(scoped) is permission.ActorScopePermissionResult
        and scoped.allowed is True
        and scoped.verification_state == "verified"
        and scoped.actor_id == identity["actor_id"]
        and scoped.caller == identity["caller"]
        and permission._canonical_business_domain_id(scoped.domain_id) == canonical_domain
        and scoped.principal_kind == identity["principal_kind"]
        and scoped.principal_ref == identity["principal_ref"]
        and scoped.subject_id == scope.get("subject_id")
        and scoped.brand_focus_id == scope.get("brand_focus_id")
        and scoped.global_scope is scope["global"]
        and scoped.scope_action == "write"
        and scoped.operation_type == "resource_scope_write"
        and scoped.resource == expected_scope_resource
        and type(scoped.audit_id) is str and bool(scoped.audit_id)
        and scoped.scope_audit_id == scoped.audit_id
    ):
        raise PermissionError("OWNED_EVALUATION_SCOPE_WRITE_DENIED")

    approval = gate.check(
        permission.OperationType.DB_WRITE,
        resource=resource,
        risk_level=permission.RiskLevel.HIGH,
        caller=identity["caller"],
        operation_id=f"owned-evaluation-capture:{uuid.uuid4().hex}",
        domain_id=domain,
        exact_approval_required=True,
    )
    token = gate.get_valid_approval_token(
        permission.OperationType.DB_WRITE.value, resource, exact=True,
    )
    if not (
        approval.allowed is True
        and approval.requires_approval is True
        and approval.operation_type == permission.OperationType.DB_WRITE.value
        and approval.resource == resource
        and approval.caller == identity["caller"]
        and permission._canonical_business_domain_id(approval.domain_id) == canonical_domain
        and approval.risk_level in {permission.RiskLevel.HIGH, permission.RiskLevel.HIGH.value}
        and approval.permission_required in {permission.PermissionLevel.COMMIT, permission.PermissionLevel.COMMIT.value}
        and type(approval.audit_id) is str and bool(approval.audit_id)
        and type(approval.approval_token) is str and bool(approval.approval_token)
        and type(token) is str and token == approval.approval_token
    ):
        raise PermissionError("OWNED_EVALUATION_EXACT_DB_WRITE_APPROVAL_REQUIRED")
    return {
        "scope_audit_id": scoped.audit_id,
        "permission_audit_id": approval.audit_id,
        "approval_token": token,
    }


def _evaluation_capture_row(
    connection: Any,
    row_id: int,
    material: Mapping[str, Any],
    resource: str,
) -> dict[str, Any]:
    from lumenis.shared.evidence import store

    row = connection.execute(
        "SELECT * FROM app_evidence_records WHERE id=?", (row_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError("OWNED_EVALUATION_EVIDENCE_READBACK_MISSING")
    result = dict(row)
    if not store.verify_evidence_record_integrity(result):
        raise RuntimeError("OWNED_EVALUATION_EVIDENCE_INTEGRITY_FAILED")
    try:
        inputs = json.loads(result["inputs_json"])
        outputs = json.loads(result["outputs_json"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("OWNED_EVALUATION_EVIDENCE_CONTENT_INVALID") from exc
    scope = material["scope"]
    expected_inputs = {
        "schema_version": 1,
        "capture_status": "RECORDED",
        "submission_id": material["submission_id"],
        "caller": material["identity"]["caller"],
        "actor_id": material["identity"]["actor_id"],
        "identity_kind": material["identity"]["identity_kind"],
        "principal_kind": material["identity"]["principal_kind"],
        "principal_ref": material["identity"]["principal_ref"],
        "scope": scope,
        "candidate_identity_sha256": material["candidate_identity_sha256"],
        "evaluation_packet_sha256": material["packet_sha256"],
        "approval_resource": resource,
    }
    if material["identity"]["identity_kind"] == "workspace":
        expected_inputs["principal_kind"] = material["identity"]["principal_kind"]
        expected_inputs["principal_ref"] = material["identity"]["principal_ref"]
    else:
        expected_inputs["principal_kind"] = None
        expected_inputs["principal_ref"] = None
    scope_audit_ref = inputs.get("scope_audit_ref") if type(inputs) is dict else None
    permission_audit_ref = inputs.get("permission_audit_ref") if type(inputs) is dict else None
    if any(
        type(value) is not str or not value.strip() or len(value) > 256
        for value in (scope_audit_ref, permission_audit_ref)
    ):
        raise RuntimeError("OWNED_EVALUATION_EVIDENCE_AUDIT_BINDING_INVALID")
    expected_inputs["scope_audit_ref"] = scope_audit_ref
    expected_inputs["permission_audit_ref"] = permission_audit_ref
    expected_inputs["_lumenis_scope"] = material["scope_marker"]
    expected_outputs = {
        "evaluation_packet": material["packet"],
        "evaluation_packet_sha256": material["packet_sha256"],
        "capture_status": "RECORDED",
    }
    if (
        result.get("source") != "owned_ai_gateway"
        or result.get("feature_id") != _EVALUATION_FEATURE
        or result.get("asset_id") != material["submission_id"]
        or result.get("test_name") != material["submission_id"]
        or result.get("version") != _EVALUATION_CAPTURE_VERSION + ":" + resource.removeprefix(_EVALUATION_CAPTURE_RESOURCE)
        or result.get("product_id") != scope["product_id"]
        or result.get("domain_id") != scope["domain_id"]
        or result.get("result") != "RECORDED"
        or result.get("status") != "derived"
        or result.get("capture_mode") != "derived_evaluation"
        or inputs != expected_inputs
        or outputs != expected_outputs
        or _evaluation_packet_sha256(outputs.get("evaluation_packet", {})) != material["packet_sha256"]
    ):
        raise RuntimeError("OWNED_EVALUATION_EVIDENCE_BINDING_INVALID")
    return result


def _find_existing_evaluation_capture(
    connection: Any,
    material: Mapping[str, Any],
    resource: str,
) -> dict[str, Any] | None:
    rows = connection.execute(
        "SELECT * FROM app_evidence_records WHERE source=? AND feature_id=? "
        "AND (asset_id=? OR test_name=?) ORDER BY id LIMIT 3",
        ("owned_ai_gateway", _EVALUATION_FEATURE,
         material["submission_id"], material["submission_id"]),
    ).fetchall()
    if not rows:
        return None
    if len(rows) != 1:
        raise RuntimeError("OWNED_EVALUATION_SUBMISSION_DUPLICATE")
    row = dict(rows[0])
    if (row.get("asset_id"), row.get("test_name")) != (
        material["submission_id"], material["submission_id"],
    ):
        raise ValueError("OWNED_EVALUATION_SUBMISSION_CONFLICT")
    verified = _evaluation_capture_row(connection, int(row["id"]), material, resource)
    return verified


def record_owned_evaluation_evidence(
    *,
    expected_scope: dict[str, Any],
    submission_id: str,
    evaluation_packet: Any,
    authenticated_actor: Mapping[str, Any] | None = None,
    principal: Any = None,
) -> dict[str, Any]:
    """Persist one exact-scope evaluator packet as derived Evidence.

    Capture records the evaluator's structural report only. It creates no
    approval, human review, quality acceptance, runtime proof, or promotion.
    """
    from lumenis.shared.database import get_repository
    from lumenis.shared.evidence import store
    from lumenis.system.security import permission

    material = _evaluation_capture_material(
        authenticated_actor=authenticated_actor,
        expected_scope=expected_scope,
        submission_id=submission_id,
        evaluation_packet=evaluation_packet,
        principal=principal,
    )
    resource = _evaluation_capture_resource(material)
    gate = permission.get_permission_gate()
    initial = _authorize_evaluation_capture(gate, material, resource)
    repository = get_repository()
    row_id: int | None = None
    already_recorded = False
    with repository.transaction(timeout=10) as connection:
        connection.execute("BEGIN IMMEDIATE")
        current = _authorize_evaluation_capture(
            gate, material, resource, connection=connection,
        )
        if current["approval_token"] != initial["approval_token"]:
            raise PermissionError("OWNED_EVALUATION_APPROVAL_CHANGED")
        existing = _find_existing_evaluation_capture(connection, material, resource)
        if existing is not None:
            current = _authorize_evaluation_capture(
                gate, material, resource, connection=connection,
            )
            if current["approval_token"] != initial["approval_token"]:
                raise PermissionError("OWNED_EVALUATION_APPROVAL_CHANGED")
            row_id = int(existing["id"])
            already_recorded = True
        else:
            inputs = {
                "schema_version": 1,
                "capture_status": "RECORDED",
                "submission_id": material["submission_id"],
                "caller": material["identity"]["caller"],
                "actor_id": material["identity"]["actor_id"],
                "identity_kind": material["identity"]["identity_kind"],
                "principal_kind": material["identity"]["principal_kind"],
                "principal_ref": material["identity"]["principal_ref"],
                "scope": material["scope"],
                "candidate_identity_sha256": material["candidate_identity_sha256"],
                "evaluation_packet_sha256": material["packet_sha256"],
                "approval_resource": resource,
                "scope_audit_ref": current["scope_audit_id"],
                "permission_audit_ref": current["permission_audit_id"],
            }
            outputs = {
                "evaluation_packet": material["packet"],
                "evaluation_packet_sha256": material["packet_sha256"],
                "capture_status": "RECORDED",
            }
            row_id = store.record_evidence(
                connection=connection,
                source="owned_ai_gateway",
                project="LUMENIS",
                product=material["scope"]["product_id"],
                feature_id=_EVALUATION_FEATURE,
                asset_id=material["submission_id"],
                test_name=material["submission_id"],
                version=_EVALUATION_CAPTURE_VERSION + ":" + resource.removeprefix(_EVALUATION_CAPTURE_RESOURCE),
                env="local",
                level="L4",
                capture_mode="derived_evaluation",
                result="RECORDED",
                inputs=inputs,
                outputs=outputs,
                metric_name="owned_ai_evaluation_capture",
                metric_value="RECORDED",
                status="derived",
                domain_id=material["scope"]["domain_id"],
                subject_id=material["scope"].get("subject_id"),
                brand_focus_id=material["scope"].get("brand_focus_id"),
                global_scope=material["scope"]["global"],
                notes=(
                    "Derived evaluator packet captured. Human review is required; "
                    "candidate acceptance, independent runtime verification, and promotion were not performed."
                ),
            )
            if type(row_id) is not int or row_id < 1:
                raise RuntimeError("OWNED_EVALUATION_EVIDENCE_WRITE_FAILED")
            _evaluation_capture_row(connection, row_id, material, resource)
            current = _authorize_evaluation_capture(
                gate, material, resource, connection=connection,
            )
            if current["approval_token"] != initial["approval_token"]:
                raise PermissionError("OWNED_EVALUATION_APPROVAL_CHANGED")
            if _evaluation_json(material["packet"]) != material["packet_json"]:
                raise RuntimeError("OWNED_EVALUATION_PACKET_CHANGED_DURING_CAPTURE")

        # Final authorization and commit must not race approval revocation.
        # The repository's subsequent commit is a no-op: no writes follow this.
        with gate.owned_evaluation_capture_commit_lease(
            material=material, resource=resource, authorization=current,
            connection=connection,
        ):
            connection.commit()

    if row_id is None:
        raise RuntimeError("OWNED_EVALUATION_EVIDENCE_WRITE_FAILED")
    with repository.connection(read_only=True, wal=False) as connection:
        row = _evaluation_capture_row(connection, row_id, material, resource)
        _authorize_evaluation_capture(gate, material, resource, connection=connection)
    return {
        "state": "already_recorded" if already_recorded else "recorded",
        "evaluation_ref": f"app_evidence_records:{row_id}",
        "content_sha256": material["packet_sha256"],
        "candidate_identity_sha256": material["candidate_identity_sha256"],
        "submission_id": material["submission_id"],
        "scope": material["scope"],
        "integrity_verified": True,
        "evidence_status": row["status"],
        "evidence_result": row["result"],
        "candidate_status": material["packet"]["candidate_status"],
        "business_acceptance": material["packet"]["business_acceptance"],
        "runtime_verification": material["packet"]["runtime_verification"],
        "promotion_status": material["packet"]["promotion_status"],
    }


class CandidateEvaluationBlocked(RuntimeError):
    """The candidate or held-out request does not match its pinned identity."""


@dataclass(frozen=True)
class CandidateInferenceRequest:
    candidate_identity_sha256: str
    model_id: str
    model_revision: str
    training_recipe: str
    manifest_sha256: str
    train_sha256: str
    heldout_sha256: str
    adapter_sha256: str
    adapter_config_sha256: str
    case_id: str
    domain_id: str
    scope: str
    source_evidence_refs: tuple[str, ...]
    user_messages: tuple[str, ...]
    max_new_tokens: int
    local_only: bool = True
    network_access: bool = False
    fallback_allowed: bool = False


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    return _hash_bytes(path.read_bytes())


def _parse_final(
    raw: object, finish_reason: object = None, termination_token: object = None,
    final_channel_prefill: object = False,
) -> tuple[str, str]:
    if not isinstance(raw, str) or not raw.strip():
        return "", "OUTPUT_MISSING"
    if termination_token not in _TERMINATORS:
        return "", "TERMINATION_TOKEN_UNSPECIFIED_OR_UNSUPPORTED"
    if type(final_channel_prefill) is not bool:
        return "", "FINAL_CHANNEL_PREFILL_METADATA_INVALID"
    if finish_reason is not None and str(finish_reason).lower() not in {"return", "eos", "stop"}:
        return "", "GENERATION_NOT_COMPLETE"
    source = raw.rstrip()
    if not source.endswith(termination_token) or source.count(termination_token) != 1:
        return "", "CONFIGURED_TERMINATION_MISSING_OR_TRUNCATED"
    body = source[:-len(termination_token)].rstrip()
    headers = list(_FINAL_HEADER.finditer(body))
    if headers:
        final = body[headers[-1].end():].strip()
    elif _CHANNEL_MARKER.search(body):
        return "", "FINAL_CHANNEL_MISSING"
    elif final_channel_prefill:
        final = body.strip()
    else:
        return "", "FINAL_CHANNEL_OR_PREFILL_MISSING"
    if not final or _CHANNEL_MARKER.search(final) or any(
        token in final for token in ("<|end|>", "<|ghissue|>", "<|call|>")
    ):
        return "", "FINAL_CHANNEL_EMPTY_OR_INVALID"
    return final, "COMPLETED_FINAL"


def _read_heldout(path: Path, expected_sha256: str) -> list[tuple[dict, str, str]]:
    data = path.read_bytes()
    if _hash_bytes(data) != expected_sha256:
        raise CandidateEvaluationBlocked("HELDOUT_DATASET_CHANGED_DURING_PREFLIGHT")
    rows = []
    for line in data.splitlines(keepends=True):
        if not line.strip():
            continue
        try:
            record = json.loads(line.decode("utf-8"))
            _, prompt = owned_training._validate_record(record)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise CandidateEvaluationBlocked("HELDOUT_RECORD_INVALID") from exc
        messages = tuple(
            message["content"].strip() for message in record["messages"]
            if message["role"] == "user"
        )
        rows.append((record, prompt, _hash_bytes(line)))
        record["_evaluation_user_messages"] = messages
    return rows


def evaluate_owned_candidate(
    model_snapshot_dir: str | Path,
    train_jsonl_path: str | Path,
    heldout_jsonl_path: str | Path,
    candidate_output_dir: str | Path,
    *,
    manifest_path: str | Path,
    expected_adapter_sha256: str,
    expected_adapter_config_sha256: str,
    local_infer: Callable[[CandidateInferenceRequest], object],
    recipe: str = owned_training.H100_RECIPE,
    max_new_tokens: int = 1024,
) -> dict[str, object]:
    """Evaluate held-out prompts through a caller-supplied local runtime.

    This returns structural observations and a human review packet only. A
    callable's presence or output does not prove runtime locality or business
    quality; promotion and acceptance are never performed here.
    """
    if not callable(local_infer):
        raise CandidateEvaluationBlocked("LOCAL_INFERENCE_CALLABLE_REQUIRED")
    if type(max_new_tokens) is not int or not 1 <= max_new_tokens <= 4096:
        raise ValueError("max_new_tokens must be an integer from 1 through 4096")
    for digest in (expected_adapter_sha256, expected_adapter_config_sha256):
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise CandidateEvaluationBlocked("EXPECTED_ADAPTER_HASH_REQUIRED")

    output = owned_training._local_path(candidate_output_dir)
    if Path(candidate_output_dir).is_symlink() or not output.is_dir():
        raise CandidateEvaluationBlocked("TRAINED_CANDIDATE_OUTPUT_DIRECTORY_REQUIRED")
    status_path = output / "training_status.json"
    adapter_path = output / "adapter_model.safetensors"
    config_path = output / "adapter_config.json"
    if any(path.is_symlink() or not path.is_file() for path in (status_path, adapter_path, config_path)):
        raise CandidateEvaluationBlocked("TRAINED_CANDIDATE_ARTIFACT_MISSING_OR_SYMLINKED")

    preflight_path = output.parent / f".{output.name}.owned-evaluation-preflight-unused"
    if preflight_path.exists() or preflight_path.is_symlink():
        raise CandidateEvaluationBlocked("PREFLIGHT_OUTPUT_PATH_ALREADY_EXISTS")
    preflight = owned_training.run_owned_lora_training(
        model_snapshot_dir, train_jsonl_path, heldout_jsonl_path, preflight_path,
        manifest_path=manifest_path, execute=False, recipe=recipe,
    )
    status_bytes = status_path.read_bytes()
    try:
        training_status = json.loads(status_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CandidateEvaluationBlocked("TRAINING_STATUS_INVALID") from exc
    if not isinstance(training_status, dict) or any(
        training_status.get(key) != preflight.get(key) for key in _STATUS_IDENTITY
    ) or training_status.get("execution_state") != "TRAINED_NOT_EVALUATED" \
            or training_status.get("candidate_status") != "NOT_EVALUATED":
        raise CandidateEvaluationBlocked("TRAINING_STATUS_IDENTITY_MISMATCH_OR_NOT_TRAINED")

    adapter_sha, config_sha = _hash_file(adapter_path), _hash_file(config_path)
    if adapter_sha != expected_adapter_sha256 or config_sha != expected_adapter_config_sha256:
        raise CandidateEvaluationBlocked("ADAPTER_HASH_MISMATCH")
    rows = _read_heldout(Path(heldout_jsonl_path), str(preflight["heldout_sha256"]))
    if len(rows) != preflight["heldout_case_count"]:
        raise CandidateEvaluationBlocked("HELDOUT_CASE_COUNT_MISMATCH")

    identity = {key: preflight[key] for key in _STATUS_IDENTITY}
    identity.update({
        "execution_state": training_status["execution_state"],
        "candidate_status": training_status["candidate_status"],
        "training_status_sha256": _hash_bytes(status_bytes),
        "adapter_sha256": adapter_sha,
        "adapter_config_sha256": config_sha,
    })
    candidate_id = _hash_bytes(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode())
    results = []
    for record, prompt, record_sha in rows:
        request = CandidateInferenceRequest(
            candidate_id, str(preflight["model_id"]), str(preflight["model_revision"]),
            str(preflight["training_recipe"]), str(preflight["manifest_sha256"]),
            str(preflight["train_sha256"]), str(preflight["heldout_sha256"]),
            adapter_sha, config_sha, record["case_id"],
            str(record["domain"]).strip().lower().replace("zbmp", "bmp"), record["scope"],
            tuple(record["source_evidence_refs"]), tuple(record["_evaluation_user_messages"]),
            max_new_tokens,
        )
        terminator = ""
        try:
            response = local_infer(request)
            if isinstance(response, Mapping):
                raw = response.get("generated_text", response.get("text"))
                finish = response.get("finish_reason")
                terminator = response.get("termination_token")
                final_prefill = response.get("final_channel_prefill", False)
                if response.get("error"):
                    raise RuntimeError("LOCAL_INFERENCE_REPORTED_ERROR")
            else:
                raw, finish, terminator, final_prefill = response, None, None, False
            final, completion = _parse_final(raw, finish, terminator, final_prefill)
        except Exception as exc:
            raw, final, completion = None, "", "INFERENCE_ERROR:" + type(exc).__name__
        raw_hash = _hash_bytes(raw.encode("utf-8")) if isinstance(raw, str) else ""
        citations = _CITATION.findall(final)
        source_refs = tuple(record["source_evidence_refs"])
        known = sorted({ref for ref in citations if ref in source_refs})
        unknown = sorted({ref for ref in citations if ref not in source_refs})
        results.append({
            "case_id": record["case_id"], "domain_id": request.domain_id, "scope": record["scope"],
            "source_evidence_refs": list(source_refs),
            "heldout_origin": {"dataset_role": "heldout", "dataset_sha256": preflight["heldout_sha256"],
                               "record_sha256": record_sha},
            "prompt_sha256": _hash_bytes(prompt.encode("utf-8")),
            "completion_state": completion, "final_text": final, "raw_output_sha256": raw_hash,
            "citation_state": "PRESENT" if known else "UNRESOLVED" if citations else "MISSING",
            "termination_token": terminator if isinstance(terminator, str) else "",
            "cited_source_refs": known, "unresolved_citation_refs": unknown,
            "business_review": {"state": "HUMAN_REVIEW_REQUIRED",
                                "criteria": {key: "PENDING" for key, _ in BUSINESS_REVIEW_RUBRIC}},
        })

    if _hash_file(status_path) != identity["training_status_sha256"] \
            or _hash_file(adapter_path) != adapter_sha or _hash_file(config_path) != config_sha:
        raise CandidateEvaluationBlocked("CANDIDATE_ARTIFACT_CHANGED_DURING_EVALUATION")
    if _hash_file(Path(train_jsonl_path)) != preflight["train_sha256"] \
            or _hash_file(Path(heldout_jsonl_path)) != preflight["heldout_sha256"]:
        raise CandidateEvaluationBlocked("DATASET_CHANGED_DURING_EVALUATION")

    all_complete = all(item["completion_state"] == "COMPLETED_FINAL" for item in results)
    return {
        "evaluation_status": "STRUCTURAL_OUTPUTS_CAPTURED" if all_complete else "INCOMPLETE_OUTPUTS_RECORDED",
        "candidate_status": "NOT_ACCEPTED", "business_acceptance": "HUMAN_REVIEW_REQUIRED",
        "runtime_verification": "CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED",
        "generation_config": {"max_new_tokens": max_new_tokens,
                              "accepted_termination_tokens": sorted(_TERMINATORS)},
        "promotion_status": "NOT_PROMOTED", "candidate_identity": identity,
        "candidate_identity_sha256": candidate_id,
        "heldout_case_count": len(results), "completed_final_count": sum(
            item["completion_state"] == "COMPLETED_FINAL" for item in results
        ),
        "business_review_rubric": [{"criterion": key, "question": question}
                                   for key, question in BUSINESS_REVIEW_RUBRIC],
        "cases": results,
    }

# Synthetic interpretability evidence is a separate, bounded diagnostic schema.
# It cannot enter the owned-model acceptance/promotion packet above.
_INTERPRETABILITY_SCHEMA = "synthetic-interpretability:v1"
_INTERPRETABILITY_FEATURE = "SYNTHETIC_INTERPRETABILITY_PACKET"
_INTERPRETABILITY_FIELDS = frozenset({
    "schema", "prototype_status", "model_kind", "run_id", "task_id", "checkpoint_id",
    "weights_sha256", "inputs_sha256", "heldout_sha256", "hypotheses_sha256", "trace_sha256",
    "capture_status", "reason", "counts", "metrics", "business_acceptance", "promotion_status",
})
_INTERPRETABILITY_METRICS = frozenset({
    "activation_prediction_nmse", "intervention_prediction_error", "replay_max_error",
})
_INTERPRETABILITY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$")


def validate_synthetic_interpretability_packet(packet: Any) -> dict[str, Any]:
    """Validate typed summaries only: no filesystem paths, raw text or tensor loader."""
    if type(packet) is not dict or set(packet) != _INTERPRETABILITY_FIELDS:
        raise ValueError("INTERPRETABILITY_PACKET_FIELDS_INVALID")
    fixed = {"schema": _INTERPRETABILITY_SCHEMA, "prototype_status": "SYNTHETIC_PROTOTYPE",
             "model_kind": "synthetic_numeric_network", "business_acceptance": "NOT_EVALUATED",
             "promotion_status": "NOT_PROMOTED"}
    if any(type(packet[k]) is not str or packet[k] != v for k, v in fixed.items()):
        raise ValueError("INTERPRETABILITY_CLAIM_BOUNDARY_INVALID")
    for key in ("run_id", "task_id", "checkpoint_id"):
        if type(packet[key]) is not str or not _INTERPRETABILITY_ID.fullmatch(packet[key]):
            raise ValueError("INTERPRETABILITY_IDENTIFIER_INVALID")
    for key in ("weights_sha256", "inputs_sha256", "heldout_sha256", "hypotheses_sha256", "trace_sha256"):
        if type(packet[key]) is not str or not _DIGEST.fullmatch(packet[key]):
            raise ValueError("INTERPRETABILITY_DIGEST_INVALID")
    state = packet["capture_status"]
    if type(state) is not str or state not in {"AVAILABLE", "NOT_AVAILABLE", "UNSUPPORTED"}:
        raise ValueError("INTERPRETABILITY_CAPTURE_STATE_INVALID")
    expected_reason = {"AVAILABLE": "NONE", "NOT_AVAILABLE": "ACTIVATIONS_UNAVAILABLE", "UNSUPPORTED": "ARCHITECTURE_UNSUPPORTED"}
    if packet["reason"] != expected_reason[state]:
        raise ValueError("INTERPRETABILITY_REASON_INVALID")
    counts = packet["counts"]
    if (type(counts) is not dict or set(counts) != {"heldout", "neurons", "explained"}
            or any(type(v) is not int for v in counts.values())
            or not 0 <= counts["heldout"] <= 1024
            or not 0 <= counts["explained"] <= counts["neurons"] <= 64):
        raise ValueError("INTERPRETABILITY_COUNTS_INVALID")
    metrics = packet["metrics"]
    if type(metrics) is not dict or set(metrics) != _INTERPRETABILITY_METRICS:
        raise ValueError("INTERPRETABILITY_METRICS_INVALID")
    for value in metrics.values():
        if value is not None and (type(value) not in {int, float} or not 0 <= value <= 1e9):
            raise ValueError("INTERPRETABILITY_METRIC_VALUE_INVALID")
    if state == "AVAILABLE":
        if not counts["heldout"] or not counts["neurons"] or any(v is None for v in metrics.values()):
            raise ValueError("INTERPRETABILITY_AVAILABLE_DATA_REQUIRED")
    elif any(v is not None for v in metrics.values()) or any(counts.values()):
        raise ValueError("INTERPRETABILITY_UNAVAILABLE_MUST_BE_UNKNOWN")
    encoded = _evaluation_json(packet)
    if len(encoded.encode("utf-8")) > 16384:
        raise ValueError("INTERPRETABILITY_PACKET_TOO_LARGE")
    return json.loads(encoded)


def _interpretability_material(*, authenticated_actor, expected_scope, submission_id, packet, principal=None):
    if type(submission_id) is not str or not _EVALUATION_UUID.fullmatch(submission_id):
        raise ValueError("INTERPRETABILITY_SUBMISSION_INVALID")
    clean = validate_synthetic_interpretability_packet(packet)
    identity = _capture_identity(authenticated_actor, principal)
    scope, marker = _capture_scope(expected_scope)
    return {"interpretability": True, "identity": identity, "principal": principal,
            "scope": scope, "scope_marker": marker, "submission_id": submission_id,
            "packet": clean, "packet_json": _evaluation_json(clean),
            "packet_sha256": _evaluation_packet_sha256(clean),
            "candidate_identity_sha256": clean["weights_sha256"]}


def synthetic_interpretability_approval_resource(*, authenticated_actor=None, expected_scope,
                                                 submission_id, packet, principal=None):
    """Exact request resource only; this neither grants permission nor writes data."""
    return _evaluation_capture_resource(_interpretability_material(
        authenticated_actor=authenticated_actor, expected_scope=expected_scope,
        submission_id=submission_id, packet=packet, principal=principal))


def _interpretability_task(connection, material, *, require_active=True):
    from agent_runtime.task_binding import authorized_context
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    packet, identity = material["packet"], material["identity"]
    row = connection.execute("SELECT * FROM ai_task WHERE task_id=?", (packet["task_id"],)).fetchone()
    if row is None:
        raise PermissionError("INTERPRETABILITY_TASK_MISSING")
    task = dict(row)
    task["context"] = json.loads(task["context_json"])
    actor = {"id": identity["actor_id"]} if identity["identity_kind"] == "account" else material["principal"]
    context = authorized_context(task, actor, connection=connection)
    scope = material["scope"]
    expected = {"subject_id": scope.get("subject_id"), "brand_focus_id": scope.get("brand_focus_id"),
                "global_scope": scope["global"]}
    if context["domain_id"] != scope["domain_id"] or context["scope"] != expected:
        raise PermissionError("INTERPRETABILITY_TASK_SCOPE_MISMATCH")
    if require_active and task["status"] not in {"pending", "running", "executing", "paused"}:
        raise PermissionError("INTERPRETABILITY_TASK_NOT_ACTIVE")
    steps = connection.execute("SELECT * FROM ai_task_step WHERE task_id=? LIMIT 1025", (packet["task_id"],)).fetchall()
    if len(steps) > 1024:
        raise ValueError("INTERPRETABILITY_TASK_HISTORY_LIMIT")
    matches = []
    for step in steps:
        cp = DurableExecutionAdapter._checkpoint_from_step(dict(step))
        if cp is not None and cp.checkpoint_id == packet["checkpoint_id"]:
            matches.append(cp)
    if len(matches) != 1:
        raise ValueError("INTERPRETABILITY_CHECKPOINT_MISSING_OR_DUPLICATE")
    cp = matches[0]
    # Bind the experiment identity before ingestion. The checkpoint is created
    # by the existing durable owner; no second runtime or checkpoint table.
    for key in ("run_id", "weights_sha256", "inputs_sha256", "hypotheses_sha256", "trace_sha256"):
        if cp.metadata.get(key) != packet[key]:
            raise ValueError("INTERPRETABILITY_CHECKPOINT_BINDING_MISMATCH")
    return task


def _interpretability_row(connection, row_id, material, resource):
    from lumenis.shared.evidence import store
    row = connection.execute("SELECT * FROM app_evidence_records WHERE id=?", (row_id,)).fetchone()
    if row is None or not store.verify_evidence_record_integrity(dict(row)):
        raise RuntimeError("INTERPRETABILITY_EVIDENCE_INTEGRITY_FAILED")
    row = dict(row)
    inputs, outputs = json.loads(row["inputs_json"]), json.loads(row["outputs_json"])
    expected = {"packet": material["packet"], "packet_sha256": material["packet_sha256"],
                "runtime_verification": "CAPTURE_ONLY_NOT_REEXECUTED"}
    identity, scope = material["identity"], material["scope"]
    if (row["source"] != "owned_ai_gateway" or row["feature_id"] != _INTERPRETABILITY_FEATURE
            or row["asset_id"] != material["submission_id"] or row["test_name"] != material["submission_id"]
            or row["version"] != _INTERPRETABILITY_SCHEMA or row["status"] != "derived"
            or row["result"] != "RECORDED" or row["capture_mode"] != "derived_evaluation"
            or row["domain_id"] != scope["domain_id"] or row["product_id"] != scope["product_id"]
            or outputs != expected
            or inputs.get("actor") != identity or inputs.get("scope") != scope
            or inputs.get("approval_resource") != resource
            or inputs.get("_lumenis_scope") != material["scope_marker"]):
        raise RuntimeError("INTERPRETABILITY_EVIDENCE_BINDING_INVALID")
    return row


def record_synthetic_interpretability_evidence(*, authenticated_actor=None, expected_scope,
                                               submission_id, packet, principal=None):
    """Atomically capture scoped diagnostic Evidence and separate Evaluation metrics.

    No model is loaded or evaluated here. Claims remain caller-supplied synthetic
    experiment summaries, even when their persistence/integrity is verified.
    """
    from lumenis.shared.database import get_repository
    from lumenis.shared.evidence import store
    from lumenis.shared.evaluation.ai import project_synthetic_interpretability_metrics
    from lumenis.shared.evaluation import recorder
    from lumenis.system.security import permission
    material = _interpretability_material(authenticated_actor=authenticated_actor,
        expected_scope=expected_scope, submission_id=submission_id, packet=packet, principal=principal)
    resource = _evaluation_capture_resource(material)
    gate = permission.get_permission_gate()
    initial = _authorize_evaluation_capture(gate, material, resource)
    with get_repository().transaction(timeout=10) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _interpretability_task(connection, material)
        current = _authorize_evaluation_capture(gate, material, resource, connection=connection)
        if current["approval_token"] != initial["approval_token"]:
            raise PermissionError("INTERPRETABILITY_APPROVAL_CHANGED")
        existing = connection.execute("SELECT id FROM app_evidence_records WHERE source=? AND feature_id=? "
            "AND (asset_id=? OR test_name=?)", ("owned_ai_gateway", _INTERPRETABILITY_FEATURE,
             submission_id, submission_id)).fetchall()
        if len(existing) > 1:
            raise RuntimeError("INTERPRETABILITY_DUPLICATE_SUBMISSION")
        if existing:
            row_id = int(existing[0][0])
            _interpretability_row(connection, row_id, material, resource)
        else:
            row_id = store.record_evidence(connection=connection, source="owned_ai_gateway", project="LUMENIS",
                product=material["scope"]["product_id"], feature_id=_INTERPRETABILITY_FEATURE,
                asset_id=submission_id, test_name=submission_id, version=_INTERPRETABILITY_SCHEMA,
                env="local", level="L4", capture_mode="derived_evaluation", result="RECORDED",
                inputs={"actor": material["identity"], "scope": material["scope"],
                        "approval_resource": resource, "scope_audit_ref": current["scope_audit_id"],
                        "permission_audit_ref": current["permission_audit_id"]},
                outputs={"packet": material["packet"], "packet_sha256": material["packet_sha256"],
                         "runtime_verification": "CAPTURE_ONLY_NOT_REEXECUTED"},
                metric_name="synthetic_interpretability_capture", metric_value="RECORDED", status="derived",
                domain_id=material["scope"]["domain_id"], subject_id=material["scope"].get("subject_id"),
                brand_focus_id=material["scope"].get("brand_focus_id"), global_scope=material["scope"]["global"],
                notes="Synthetic prototype; no business acceptance, model promotion or real-model execution.")
            if type(row_id) is not int or row_id < 1:
                raise RuntimeError("INTERPRETABILITY_EVIDENCE_WRITE_FAILED")
        _interpretability_row(connection, row_id, material, resource)
        ref = f"app_evidence_records:{row_id}"
        projected = project_synthetic_interpretability_metrics(material["packet"], evidence_ref=ref,
                                                               packet_sha256=material["packet_sha256"])
        metric_ids = []
        for item in projected:
            identifier = str(uuid.uuid5(uuid.NAMESPACE_URL, resource + ":" + item["metric_name"]))
            record = recorder.record_evaluation(**item, evaluation_id=identifier, connection=connection)
            metric_ids.append(record.evaluation_id)
        _interpretability_task(connection, material)
        current = _authorize_evaluation_capture(gate, material, resource, connection=connection)
        if current["approval_token"] != initial["approval_token"]:
            raise PermissionError("INTERPRETABILITY_APPROVAL_CHANGED")
        with gate.owned_evaluation_capture_commit_lease(material=material, resource=resource,
                                                       authorization=current, connection=connection):
            connection.commit()
    return {"state": "already_recorded" if existing else "recorded", "evidence_ref": ref,
            "packet_sha256": material["packet_sha256"], "evaluation_ids": metric_ids,
            "task_id": packet["task_id"], "checkpoint_id": packet["checkpoint_id"],
            "prototype_status": "SYNTHETIC_PROTOTYPE", "business_acceptance": "NOT_EVALUATED",
            "promotion_status": "NOT_PROMOTED", "runtime_verification": "CAPTURE_ONLY_NOT_REEXECUTED"}


def read_synthetic_interpretability_evidence(*, evidence_ref, authenticated_actor=None,
                                             expected_scope, principal=None):
    """Fresh-process readback through current identity, scope and Task permissions."""
    from lumenis.shared.database import get_repository
    from lumenis.shared.evidence import store
    from lumenis.system.security import permission
    if type(evidence_ref) is not str or not _EVALUATION_REF.fullmatch(evidence_ref):
        raise ValueError("INTERPRETABILITY_EVIDENCE_REF_INVALID")
    identity = _capture_identity(authenticated_actor, principal)
    scope, _ = _capture_scope(expected_scope)
    with get_repository().connection(read_only=True, wal=False) as connection:
        row = connection.execute("SELECT * FROM app_evidence_records WHERE id=?",
                                 (int(evidence_ref.split(":")[1]),)).fetchone()
        if row is None or not store.verify_evidence_record_integrity(dict(row)):
            raise RuntimeError("INTERPRETABILITY_EVIDENCE_INTEGRITY_FAILED")
        row = dict(row)
        inputs, outputs = json.loads(row["inputs_json"]), json.loads(row["outputs_json"])
        if inputs.get("actor") != identity or inputs.get("scope") != scope:
            raise PermissionError("INTERPRETABILITY_READ_IDENTITY_SCOPE_MISMATCH")
        kwargs = dict(domain_id=scope['domain_id'], action='write', module='owned_model_admission',
                      subject_id=scope.get('subject_id'),brand_focus_id=scope.get('brand_focus_id'),
                      global_scope=scope['global'],connection=connection)
        decision = (permission.check_local_workspace_scope_permission(principal, **kwargs)
                    if identity['identity_kind']=='workspace'
                    else permission.check_actor_scope_permission({'id':identity['actor_id']}, **kwargs))
        if not decision.allowed:
            raise PermissionError("INTERPRETABILITY_READ_SCOPE_REVOKED")
        material = _interpretability_material(authenticated_actor=authenticated_actor,
            expected_scope=expected_scope, submission_id=row['asset_id'], packet=outputs.get('packet'), principal=principal)
        resource = _evaluation_capture_resource(material)
        _interpretability_row(connection,int(row['id']),material,resource)
        _interpretability_task(connection,material,require_active=False)
        from lumenis.shared.evaluation.ai import project_synthetic_interpretability_metrics
        from lumenis.shared.evaluation.recorder import _is_synthetic_interpretability_record
        expected = project_synthetic_interpretability_metrics(material['packet'],evidence_ref=evidence_ref,
                                                             packet_sha256=material['packet_sha256'])
        metric_rows=[]
        for item in expected:
            identifier=str(uuid.uuid5(uuid.NAMESPACE_URL,resource+':'+item['metric_name']))
            metric=connection.execute('SELECT * FROM evaluation_records WHERE evaluation_id=?',(identifier,)).fetchone()
            if metric is None or not _is_synthetic_interpretability_record(connection,dict(metric)):
                raise RuntimeError('INTERPRETABILITY_METRIC_READBACK_FAILED')
            metric_rows.append(dict(metric))
        from agent_research.lineage import LineageTracker
        lineage=LineageTracker()
        lineage.track(evidence_ref,'synthetic_interpretability',
            path=[material['packet']['hypotheses_sha256'],material['packet']['weights_sha256'],
                  material['packet']['task_id'],material['packet']['checkpoint_id']],
            provenance={'packet_sha256':material['packet_sha256'],'evaluation_ids':[m['evaluation_id'] for m in metric_rows]})
        return {'evidence_ref':evidence_ref,'packet':material['packet'],'packet_sha256':material['packet_sha256'],
                'metrics':metric_rows,'lineage':lineage.export(),'integrity_verified':True,
                'runtime_verification':'CAPTURE_ONLY_NOT_REEXECUTED'}
