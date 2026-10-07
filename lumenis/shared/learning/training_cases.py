"""Read-only export of explicitly reviewed, rights-approved training cases.

This module consumes future signed Learning Evidence contracts. It does not
create approvals, promote report feedback, write Evidence, or start training.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

from lumenis.shared.database import get_repository
from lumenis.shared.evidence import store
from lumenis.system.security import permission

_REVIEW = "OWNED_TRAINING_TARGET_REVIEW"
_RIGHTS = "OWNED_TRAINING_RIGHTS_APPROVAL"
_REF = re.compile(r"^app_evidence_records:([1-9][0-9]*)$")
_MAX_REVIEWS = 128
_MAX_SOURCES = 64
_SCOPE_KEYS = {"product_id", "domain_id", "global", "subject_id", "brand_focus_id", "entity_label", "scope_key"}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _scope(scope: Any) -> tuple[dict, dict]:
    from lumenis.shared.reporting.operator_review import _expected_scope_marker
    from lumenis.shared.reporting.artifact import compute_scoped_scope_key

    if not isinstance(scope, dict) or set(scope) != _SCOPE_KEYS:
        raise ValueError("OWNED_TRAINING_SCOPE_INVALID")
    product, domain = scope.get("product_id"), scope.get("domain_id")
    if product not in {"CTH", "ZBMP"} or domain not in {"cth", "zbmp"}:
        raise ValueError("OWNED_TRAINING_SCOPE_INVALID")
    if (product, domain) not in {("CTH", "cth"), ("ZBMP", "zbmp")}:
        raise ValueError("OWNED_TRAINING_SCOPE_DOMAIN_MISMATCH")
    if type(scope.get("global")) is not bool:
        raise ValueError("OWNED_TRAINING_SCOPE_INVALID")
    label, key = scope.get("entity_label"), scope.get("scope_key")
    if not isinstance(label, str) or not label or label != label.strip() or len(label) > 256:
        raise ValueError("OWNED_TRAINING_SCOPE_INVALID")
    if not isinstance(key, str) or not key or key != key.strip() or len(key) > 256:
        raise ValueError("OWNED_TRAINING_SCOPE_INVALID")
    expected_key = compute_scoped_scope_key(
        domain, scope.get("subject_id"), scope.get("brand_focus_id"), scope["global"],
        None, None, "zh-CN", "markdown",
    )
    if key != expected_key:
        raise ValueError("OWNED_TRAINING_SCOPE_KEY_MISMATCH")
    marker = _expected_scope_marker(scope)
    return scope, marker


def _ref_id(ref: Any) -> int:
    match = _REF.fullmatch(ref) if isinstance(ref, str) else None
    if not match:
        raise ValueError("OWNED_TRAINING_EVIDENCE_REF_INVALID")
    return int(match.group(1))


def _row(connection, ref: str) -> dict:
    row = connection.execute("SELECT * FROM app_evidence_records WHERE id=?", (_ref_id(ref),)).fetchone()
    if row is None:
        raise LookupError("OWNED_TRAINING_EVIDENCE_NOT_FOUND")
    result = dict(row)
    if not store.verify_evidence_record_integrity(result):
        raise RuntimeError("OWNED_TRAINING_EVIDENCE_SIGNATURE_INVALID")
    return result


def _object(value: Any) -> dict:
    from lumenis.shared.reporting.operator_review import _strict_object
    return _strict_object(value)


def _bound(row: dict, *, scope: dict, marker: dict, source: str, feature: str,
           result: str, capture_mode: str | None) -> tuple[dict, dict]:
    inputs, outputs = _object(row.get("inputs_json")), _object(row.get("outputs_json"))
    if (row.get("source") != source or row.get("feature_id") != feature
            or row.get("product_id") != scope["product_id"] or row.get("domain_id") != scope["domain_id"]
            or row.get("status") != "derived" or row.get("result") != result
            or (capture_mode is not None and row.get("capture_mode") != capture_mode)
            or inputs.get("scope") != scope
            or inputs.get("_lumenis_scope") != marker):
        raise PermissionError("OWNED_TRAINING_EVIDENCE_BINDING_INVALID")
    return inputs, outputs


def _source_refs(value: Any) -> list[str]:
    if (not isinstance(value, list) or not value or len(value) > _MAX_SOURCES
            or any(not isinstance(ref, str) for ref in value) or len(set(value)) != len(value)):
        raise ValueError("OWNED_TRAINING_SOURCE_REFS_INVALID")
    for ref in value:
        _ref_id(ref)
    return value


def _audit_ref(value: Any) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > 256
            or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value)):
        raise ValueError("OWNED_TRAINING_AUDIT_REF_INVALID")
    return value


def _record(connection, review_ref: str, actor_id: str, scope: dict, marker: dict) -> tuple[dict, dict, str, dict]:
    review = _row(connection, review_ref)
    inputs, outputs = _bound(
        review, scope=scope, marker=marker, source="shared_learning", feature=_REVIEW,
        result="APPROVED", capture_mode="reviewer_submission",
    )
    review_keys = {"actor_id", "scope", "source_evidence_refs", "rights_evidence_ref",
                   "permission_audit_ref", "operation_audit_ref", "case_id", "context",
                   "prompt_messages", "_lumenis_scope"}
    identity_fields = {}
    if actor_id == "workspace:local":
        identity_fields = {"principal_kind": "local_workspace", "principal_ref": "workspace:local"}
        review_keys.update(identity_fields)
    if set(inputs) != review_keys or inputs.get("actor_id") != actor_id:
        raise PermissionError("OWNED_TRAINING_REVIEW_ACTOR_OR_SCHEMA_INVALID")
    if any(inputs.get(name) != value for name, value in identity_fields.items()):
        raise PermissionError("OWNED_TRAINING_REVIEW_WORKSPACE_IDENTITY_INVALID")
    if set(outputs) != {"review_status", "reviewer_approved_target"} or outputs.get("review_status") != "REVIEWER_APPROVED":
        raise PermissionError("OWNED_TRAINING_REVIEW_NOT_APPROVED")
    refs = _source_refs(inputs.get("source_evidence_refs"))
    rights_ref = inputs.get("rights_evidence_ref")
    _ref_id(rights_ref)
    permission_ref = _audit_ref(inputs.get("permission_audit_ref"))
    _audit_ref(inputs.get("operation_audit_ref"))
    if (not isinstance(inputs.get("case_id"), str) or not inputs["case_id"].strip()
            or inputs["case_id"] != inputs["case_id"].strip() or len(inputs["case_id"]) > 256
            or not isinstance(inputs.get("context"), str) or not inputs["context"].strip()
            or len(inputs["context"]) > 4096):
        raise ValueError("OWNED_TRAINING_REVIEW_CONTENT_INVALID")
    prompts = inputs.get("prompt_messages")
    if (not isinstance(prompts, list) or not prompts or len(prompts) > 32
            or any(not isinstance(item, dict) or set(item) != {"role", "content"}
                   or item.get("role") != "user" or not isinstance(item.get("content"), str)
                   for item in prompts)):
        raise ValueError("OWNED_TRAINING_PROMPT_MESSAGES_INVALID")

    rights = _row(connection, rights_ref)
    right_inputs, right_outputs = _bound(
        rights, scope=scope, marker=marker, source="shared_learning", feature=_RIGHTS,
        result="APPROVED", capture_mode=None,
    )
    if (set(right_inputs) != {"actor_id", "scope", "source_evidence_refs", "_lumenis_scope", *identity_fields}
            or right_inputs.get("actor_id") != actor_id or right_inputs.get("source_evidence_refs") != refs
            or any(right_inputs.get(name) != value for name, value in identity_fields.items())
            or set(right_outputs) != {"purpose", "rights_disposition"}
            or right_outputs.get("purpose") != "model_training"
            or right_outputs.get("rights_disposition") != "permitted"):
        raise PermissionError("OWNED_TRAINING_RIGHTS_NOT_PERMITTED")
    if rights_ref == review_ref or rights_ref in refs or review_ref in refs:
        raise ValueError("OWNED_TRAINING_EVIDENCE_REFERENCE_OVERLAP")
    snapshots = {review_ref: review, rights_ref: rights}
    for ref in refs:
        source = _row(connection, ref)
        if (source.get("source") == "shared_learning"
                and source.get("feature_id") in {_REVIEW, _RIGHTS}):
            raise PermissionError("OWNED_TRAINING_SOURCE_EVIDENCE_INVALID")
        source_inputs = _object(source.get("inputs_json"))
        if (source.get("product_id") != scope["product_id"] or source.get("domain_id") != scope["domain_id"]
                or source_inputs.get("_lumenis_scope") != marker):
            raise PermissionError("OWNED_TRAINING_SOURCE_SCOPE_MISMATCH")
        if source.get("result") != "PASS" or source.get("status") != "verified":
            raise PermissionError("OWNED_TRAINING_SOURCE_NOT_SUCCESSFULLY_VERIFIED")
        snapshots[ref] = source

    target = outputs.get("reviewer_approved_target")
    scope_label = "GLOBAL / ALL" if scope["global"] else (scope.get("subject_id") or scope.get("brand_focus_id"))
    if not isinstance(scope_label, str) or not scope_label.strip():
        raise ValueError("OWNED_TRAINING_SCOPE_LABEL_INVALID")
    record = {
        "case_id": inputs["case_id"], "source_evidence_refs": refs,
        "scope": scope_label, "domain": "CTH" if scope["domain_id"] == "cth" else "BMP",
        "context": inputs["context"], "permission_ref": permission_ref, "rights_ref": rights_ref,
        "review_status": "REVIEWER_APPROVED", "reviewer_approval_ref": review_ref,
        "reviewer_approved_target": target, "training_eligible": True,
        "messages": [*prompts, {"role": "assistant", "content": target, "channel": "final"}],
    }
    from lumenis.system.ai_gateway.owned_training import _validate_record
    identity, prompt = _validate_record(record)
    return record, identity, prompt, {ref: _json(row) for ref, row in snapshots.items()}


def _authorize_workspace_export(principal, gate, actor_ref: str, scope: dict, review_refs: list[str]) -> None:
    """Read admission only; the existing review and execution approvals stay distinct."""
    if type(gate) is not permission.PermissionGate or permission.is_testing_bypass_enabled():
        raise PermissionError("OWNED_TRAINING_EXPORT_CANONICAL_PERMISSION_REQUIRED")
    try:
        identity = permission.owned_training_identity(principal=principal)
    except ValueError:
        raise PermissionError("OWNED_TRAINING_EXPORT_SERVER_IDENTITY_REQUIRED") from None
    if identity["caller"] != actor_ref:
        raise PermissionError("OWNED_TRAINING_EXPORT_IDENTITY_MISMATCH")
    domain = "bmp" if scope["domain_id"] == "zbmp" else "cth"
    canonical_domain = permission._canonical_business_domain_id(domain)
    if not canonical_domain:
        raise PermissionError("OWNED_TRAINING_EXPORT_SCOPE_DENIED")
    result = permission.check_local_workspace_scope_permission(
        principal, domain_id=domain, action="read", module="owned_training", gate=gate,
        subject_id=scope["subject_id"], brand_focus_id=scope["brand_focus_id"], global_scope=scope["global"],
    )
    focus = scope["subject_id"] if domain == "cth" else scope["brand_focus_id"]
    if type(result) is not permission.ActorScopePermissionResult or (
            result.allowed, result.verification_state, result.caller, result.actor_id,
            result.principal_kind, result.principal_ref,
            result.subject_id, result.brand_focus_id, result.global_scope, result.scope_action,
            result.operation_type, result.resource,
    ) != (True, "verified", actor_ref, None, "local_workspace", "workspace:local",
          scope["subject_id"], scope["brand_focus_id"], scope["global"], "read", "resource_scope_read",
          f"{domain}:{'GLOBAL / ALL' if scope['global'] else focus}") \
            or permission._canonical_business_domain_id(result.domain_id) != canonical_domain \
            or not result.audit_id or result.scope_audit_id != result.audit_id:
        raise PermissionError("OWNED_TRAINING_EXPORT_SCOPE_DENIED")
    resource = "owned_training_case_export:v1:" + hashlib.sha256(_json({
        "identity": identity, "scope": scope, "review_evidence_refs": review_refs,
    }).encode()).hexdigest()
    read = gate.check(permission.OperationType.DATA_EXPORT, resource=resource, caller=actor_ref,
                      domain_id=domain, risk_level=permission.RiskLevel.MEDIUM)
    if (read.allowed, read.operation_type, read.resource, read.caller,
            read.permission_required, read.risk_level) != (
            True, permission.OperationType.DATA_EXPORT.value, resource, actor_ref,
            permission.PermissionLevel.VERIFY, permission.RiskLevel.MEDIUM) or not read.audit_id:
        raise PermissionError("OWNED_TRAINING_EXPORT_READ_DENIED")
    if permission._canonical_business_domain_id(read.domain_id) != canonical_domain:
        raise PermissionError("OWNED_TRAINING_EXPORT_READ_DENIED")


def export_reviewed_training_records(
    review_evidence_refs: list[str], *, actor_id: str, expected_scope: dict[str, Any], authorize: Callable[[], dict[str, Any]],
    principal: permission.LocalWorkspacePrincipal | None = None, gate: permission.PermissionGate | None = None,
) -> list[dict]:
    """Return validated JSONL-shaped records from signed review and rights Evidence only."""
    from lumenis.shared.reporting import operator_review

    if (not isinstance(actor_id, str) or not actor_id.strip() or actor_id != actor_id.strip()
            or not isinstance(review_evidence_refs, list) or not review_evidence_refs
            or len(review_evidence_refs) > _MAX_REVIEWS):
        raise ValueError("OWNED_TRAINING_EXPORT_REQUEST_INVALID")
    if any(not isinstance(ref, str) for ref in review_evidence_refs):
        raise ValueError("OWNED_TRAINING_EVIDENCE_REF_INVALID")
    if len(set(review_evidence_refs)) != len(review_evidence_refs):
        raise ValueError("OWNED_TRAINING_DUPLICATE_REVIEW_REF")
    scope, marker = _scope(expected_scope)
    workspace = actor_id == "workspace:local" or principal is not None
    if workspace:
        _authorize_workspace_export(principal, gate, actor_id, scope, review_evidence_refs)
    operator_review._authorize(authorize, actor_id, scope)
    records, snapshots, cases, prompts = [], {}, set(), set()
    with get_repository().connection(read_only=True, wal=False) as connection:
        for ref in review_evidence_refs:
            _ref_id(ref)
            record, identity, prompt, current = _record(connection, ref, actor_id, scope, marker)
            if identity["case_id"] in cases:
                raise ValueError("OWNED_TRAINING_DUPLICATE_CASE")
            if prompt in prompts:
                raise ValueError("OWNED_TRAINING_DUPLICATE_PROMPT")
            cases.add(identity["case_id"])
            prompts.add(prompt)
            records.append(record)
            snapshots.update(current)
        operator_review._authorize(authorize, actor_id, scope)
        if workspace:
            _authorize_workspace_export(principal, gate, actor_id, scope, review_evidence_refs)
        for ref, expected in snapshots.items():
            if _json(_row(connection, ref)) != expected:
                raise RuntimeError("OWNED_TRAINING_EVIDENCE_CHANGED_DURING_EXPORT")
    return records
