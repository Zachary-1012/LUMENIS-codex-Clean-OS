"""Explicit, Permission-gated target and rights submissions for owned training."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping
from typing import Any

from lumenis.shared.database import get_repository
from lumenis.shared.evidence import store
from lumenis.shared.learning import training_cases
from lumenis.system.security import permission

_VERSION = "owned-training-review:v1"
_RESOURCE = "owned_training_target_review:v1:"
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_TARGET = "OWNED_TRAINING_TARGET_REVIEW"
_RIGHTS = "OWNED_TRAINING_RIGHTS_APPROVAL"


def _request_material(*, authenticated_actor: Mapping[str, Any] | None = None, expected_scope: dict,
                      source_evidence_refs: list[str], submission_id: str,
                      prompt_messages: list[dict], reviewer_approved_target: str,
                      context: str, rights_declaration: dict,
                      principal: permission.LocalWorkspacePrincipal | None = None) -> dict:
    from lumenis.system.ai_gateway.owned_training import _validate_record

    actor_id = authenticated_actor.get("id") if isinstance(authenticated_actor, Mapping) else None
    if principal is None:
        if type(actor_id) is not int or actor_id <= 0:
            raise PermissionError("OWNED_TRAINING_REVIEW_AUTHENTICATED_ACTOR_REQUIRED")
    elif authenticated_actor is not None:
        raise PermissionError("OWNED_TRAINING_REVIEW_IDENTITY_MIXED")
    try:
        identity = permission.owned_training_identity(actor_id=actor_id, principal=principal)
    except ValueError:
        raise PermissionError("OWNED_TRAINING_REVIEW_SERVER_IDENTITY_REQUIRED") from None
    if (not isinstance(submission_id, str) or not _UUID.fullmatch(submission_id)
            or str(uuid.UUID(submission_id)) != submission_id):
        raise ValueError("OWNED_TRAINING_REVIEW_SUBMISSION_ID_INVALID")
    scope, marker = training_cases._scope(json.loads(training_cases._json(expected_scope)))
    refs = training_cases._source_refs(json.loads(training_cases._json(source_evidence_refs)))
    if type(rights_declaration) is not dict:
        raise PermissionError("OWNED_TRAINING_RIGHTS_DECLARATION_NOT_PERMITTED")
    rights_declaration = json.loads(training_cases._json(rights_declaration))
    if rights_declaration != {"purpose": "model_training", "rights_disposition": "permitted"}:
        raise PermissionError("OWNED_TRAINING_RIGHTS_DECLARATION_NOT_PERMITTED")
    if not isinstance(prompt_messages, list) or len(prompt_messages) > 32:
        raise ValueError("OWNED_TRAINING_REVIEW_PROMPTS_INVALID")
    prompt_messages = json.loads(training_cases._json(prompt_messages))
    if not isinstance(context, str) or not context.strip() or len(context) > 4096:
        raise ValueError("OWNED_TRAINING_REVIEW_CONTEXT_INVALID")
    scope_label = "GLOBAL / ALL" if scope["global"] else scope.get("subject_id") or scope.get("brand_focus_id")
    record = {"case_id": submission_id, "source_evidence_refs": refs, "scope": scope_label,
              "domain": "CTH" if scope["domain_id"] == "cth" else "BMP", "context": context,
              "permission_ref": "permission:pending", "rights_ref": "app_evidence_records:1",
              "review_status": "REVIEWER_APPROVED", "reviewer_approval_ref": "app_evidence_records:1",
              "reviewer_approved_target": reviewer_approved_target, "training_eligible": True,
              "messages": [*prompt_messages, {"role": "assistant", "content": reviewer_approved_target, "channel": "final"}]}
    _validate_record(record)
    return {"actor_id": identity["actor_id"], "actor_ref": identity["caller"],
            "identity": identity, "principal": principal, "scope": scope, "marker": marker,
            "source_refs": refs, "submission_id": submission_id,
            "prompt_messages": prompt_messages, "target": reviewer_approved_target,
            "context": context, "rights": rights_declaration}


def _source_hashes(connection, material: dict) -> list[dict[str, str]]:
    scope, marker = material["scope"], material["marker"]
    hashes = []
    for ref in material["source_refs"]:
        row = training_cases._row(connection, ref)
        inputs = training_cases._object(row.get("inputs_json"))
        if row.get("source") == "shared_learning" and row.get("feature_id") in {_TARGET, _RIGHTS}:
            raise PermissionError("OWNED_TRAINING_REVIEW_SOURCE_NOT_ORIGINAL")
        if (row.get("product_id"), row.get("domain_id"), inputs.get("_lumenis_scope")) != (
                scope["product_id"], scope["domain_id"], marker):
            raise PermissionError("OWNED_TRAINING_REVIEW_SOURCE_SCOPE_MISMATCH")
        if (row.get("result"), row.get("status")) != ("PASS", "verified"):
            raise PermissionError("OWNED_TRAINING_REVIEW_SOURCE_NOT_VERIFIED")
        hashes.append({"evidence_ref": ref, "integrity_digest": row["integrity_digest"]})
    return hashes


def _resource(material: dict, source_hashes: list[dict[str, str]]) -> str:
    scope = material["scope"]
    payload = {"schema_version": 1, "operation": permission.OperationType.MODEL_TRAIN.value,
               "purpose": "reviewed_training_target", "actor_id": material["actor_id"],
               "actor_ref": material["actor_ref"], "domain_id": "bmp" if scope["domain_id"] == "zbmp" else "cth",
               "scope": scope, "source_evidence": source_hashes, "prompt_messages": material["prompt_messages"],
               "reviewer_approved_target": material["target"], "context": material["context"],
               "rights_declaration": material["rights"], "submission_id": material["submission_id"]}
    if material["identity"]["identity_kind"] == "workspace":
        payload.update(principal_kind=material["identity"]["principal_kind"],
                       principal_ref=material["identity"]["principal_ref"])
    return _RESOURCE + hashlib.sha256(training_cases._json(payload).encode()).hexdigest()


def training_review_approval_resource(*, authenticated_actor: Mapping[str, Any] | None = None, expected_scope: dict,
                                      source_evidence_refs: list[str], submission_id: str,
                                      prompt_messages: list[dict], reviewer_approved_target: str,
                                      context: str, rights_declaration: dict,
                                      principal: permission.LocalWorkspacePrincipal | None = None) -> str:
    """Build the distinct exact MODEL_TRAIN resource for human review approval."""
    material = _request_material(
        authenticated_actor=authenticated_actor, expected_scope=expected_scope, source_evidence_refs=source_evidence_refs,
        submission_id=submission_id, prompt_messages=prompt_messages,
        reviewer_approved_target=reviewer_approved_target, context=context,
        rights_declaration=rights_declaration, principal=principal,
    )
    with get_repository().connection(read_only=True, wal=False) as connection:
        return _resource(material, _source_hashes(connection, material))


def _authorize(gate: permission.PermissionGate, material: dict, resource: str) -> tuple[str, str]:
    if permission.is_testing_bypass_enabled():
        raise PermissionError("OWNED_TRAINING_REVIEW_TESTING_BYPASS_FORBIDDEN")
    scope, actor_id = material["scope"], material["actor_id"]
    try:
        identity = permission.owned_training_identity(actor_id=actor_id, principal=material["principal"])
    except ValueError:
        raise PermissionError("OWNED_TRAINING_REVIEW_SERVER_IDENTITY_REQUIRED") from None
    if identity != material["identity"]:
        raise PermissionError("OWNED_TRAINING_REVIEW_IDENTITY_CHANGED")
    domain = "bmp" if scope["domain_id"] == "zbmp" else "cth"
    scope_args = dict(domain_id=domain, action="write", module="owned_training",
                      subject_id=scope["subject_id"], brand_focus_id=scope["brand_focus_id"],
                      global_scope=scope["global"], gate=gate)
    if identity["identity_kind"] == "workspace":
        scoped = permission.check_local_workspace_scope_permission(material["principal"], **scope_args)
    else:
        scoped = permission.check_actor_scope_permission({"id": actor_id}, **scope_args)
    caller = identity["caller"]
    focus = scope["subject_id"] if domain == "cth" else scope["brand_focus_id"]
    scope_resource = f"{domain}:{'GLOBAL / ALL' if scope['global'] else focus}"
    if type(scoped) is not permission.ActorScopePermissionResult or (
            scoped.allowed, scoped.verification_state, scoped.actor_id, scoped.caller,
            scoped.domain_id, scoped.subject_id, scoped.brand_focus_id, scoped.global_scope,
            scoped.scope_action, scoped.operation_type, scoped.resource,
    ) != (True, "verified", actor_id, caller, domain, scope["subject_id"],
          scope["brand_focus_id"], scope["global"], "write", "resource_scope_write", scope_resource) \
            or not scoped.audit_id or scoped.scope_audit_id != scoped.audit_id:
        raise PermissionError("OWNED_TRAINING_REVIEW_SCOPE_DENIED")
    if (scoped.principal_kind, scoped.principal_ref) != (identity["principal_kind"], identity["principal_ref"]):
        raise PermissionError("OWNED_TRAINING_REVIEW_SCOPE_DENIED")
    approval = gate.check(
        permission.OperationType.MODEL_TRAIN, resource=resource, risk_level=permission.RiskLevel.HIGH,
        caller=caller, domain_id=domain, exact_approval_required=True,
    )
    token = gate.get_valid_approval_token(permission.OperationType.MODEL_TRAIN.value, resource, exact=True)
    if (approval.allowed, approval.requires_approval, approval.operation_type, approval.resource,
            approval.caller, approval.domain_id, approval.risk_level, approval.permission_required) != (
            True, True, permission.OperationType.MODEL_TRAIN.value, resource, caller, domain,
            permission.RiskLevel.HIGH, permission.PermissionLevel.COMMIT,
    ) or not approval.audit_id or not approval.approval_token or token != approval.approval_token:
        raise PermissionError("OWNED_TRAINING_REVIEW_EXACT_APPROVAL_REQUIRED")
    return scoped.audit_id, approval.audit_id


def _existing(connection, material: dict, resource: str) -> dict | None:
    sid = material["submission_id"]
    rows = connection.execute("SELECT * FROM app_evidence_records WHERE source='shared_learning' "
                              "AND feature_id IN (?,?) AND (asset_id=? OR test_name=?) ORDER BY id LIMIT 3",
                              (_TARGET, _RIGHTS, sid, sid)).fetchall()
    if not rows:
        return None
    if len(rows) != 2 or {row["feature_id"] for row in rows} != {_TARGET, _RIGHTS}:
        raise RuntimeError("OWNED_TRAINING_REVIEW_SUBMISSION_INCOMPLETE_OR_DUPLICATE")
    target = dict(next(row for row in rows if row["feature_id"] == _TARGET))
    rights = dict(next(row for row in rows if row["feature_id"] == _RIGHTS))
    expected_version = _VERSION + ":" + resource.removeprefix(_RESOURCE)
    if target.get("version") != expected_version or rights.get("version") != expected_version:
        raise ValueError("OWNED_TRAINING_REVIEW_SUBMISSION_CONFLICT")
    review_ref = f"app_evidence_records:{target['id']}"
    record, identity, _prompt, _snapshots = training_cases._record(
        connection, review_ref, material["actor_ref"], material["scope"], material["marker"])
    expected_messages = [*material["prompt_messages"], {"role": "assistant", "content": material["target"], "channel": "final"}]
    if (identity["case_id"], record["messages"], record["context"], record["source_evidence_refs"],
            rights.get("capture_mode"), target.get("asset_id"), rights.get("asset_id")) != (
            material["submission_id"], expected_messages, material["context"], material["source_refs"],
            "reviewer_submission", material["submission_id"], material["submission_id"]):
        raise ValueError("OWNED_TRAINING_REVIEW_SUBMISSION_CONFLICT")
    return {"state": "already_recorded", "review_evidence_ref": review_ref,
            "rights_evidence_ref": record["rights_ref"], "submission_id": material["submission_id"],
            "training_executed": False}


def submit_training_review(*, gate: permission.PermissionGate, authenticated_actor: Mapping[str, Any] | None = None, expected_scope: dict,
                           source_evidence_refs: list[str], submission_id: str, prompt_messages: list[dict],
                           reviewer_approved_target: str, context: str, rights_declaration: dict,
                           principal: permission.LocalWorkspacePrincipal | None = None) -> dict:
    """Persist an explicit review; authenticated_actor must come from the server auth context."""
    if type(gate) is not permission.PermissionGate:
        raise ValueError("the canonical PermissionGate is required")
    material = _request_material(
        authenticated_actor=authenticated_actor, expected_scope=expected_scope, source_evidence_refs=source_evidence_refs,
        submission_id=submission_id, prompt_messages=prompt_messages,
        reviewer_approved_target=reviewer_approved_target, context=context,
        rights_declaration=rights_declaration, principal=principal,
    )
    with get_repository().connection(read_only=True, wal=False) as connection:
        source_hashes = _source_hashes(connection, material)
        resource = _resource(material, source_hashes)
        existing = _existing(connection, material, resource)
    if existing is not None:
        _authorize(gate, material, resource)
        return existing

    with get_repository().transaction(timeout=10) as connection:
        connection.execute("BEGIN IMMEDIATE")
        current_hashes = _source_hashes(connection, material)
        if current_hashes != source_hashes:
            raise RuntimeError("OWNED_TRAINING_REVIEW_SOURCE_CHANGED")
        existing = _existing(connection, material, resource)
        if existing is not None:
            _authorize(gate, material, resource)
            return existing
        permission_ref, operation_ref = _authorize(gate, material, resource)
        scope, sid = material["scope"], material["submission_id"]
        identity_fields = {}
        if material["identity"]["identity_kind"] == "workspace":
            identity_fields = {name: material["identity"][name] for name in ("principal_kind", "principal_ref")}
        version = _VERSION + ":" + resource.removeprefix(_RESOURCE)
        common = dict(connection=connection, source="shared_learning", project="LUMENIS",
                      product=scope["product_id"], asset_id=sid, test_name=sid, version=version,
                      capture_mode="reviewer_submission", result="APPROVED", status="derived",
                      domain_id=scope["domain_id"], subject_id=scope["subject_id"],
                      brand_focus_id=scope["brand_focus_id"], global_scope=scope["global"])
        rights_id = store.record_evidence(
            **common, feature_id=_RIGHTS,
            inputs={"actor_id": material["actor_ref"], "scope": scope, **identity_fields,
                    "source_evidence_refs": material["source_refs"]},
            outputs=material["rights"],
            notes="Explicit permitted model-training rights declaration; no training effect performed.",
        )
        if type(rights_id) is not int or rights_id < 1:
            raise RuntimeError("OWNED_TRAINING_REVIEW_RIGHTS_WRITE_FAILED")
        review_id = store.record_evidence(
            **common, feature_id=_TARGET,
            inputs={"actor_id": material["actor_ref"], "scope": scope, **identity_fields,
                    "source_evidence_refs": material["source_refs"],
                    "rights_evidence_ref": f"app_evidence_records:{rights_id}",
                    "permission_audit_ref": permission_ref, "operation_audit_ref": operation_ref,
                    "case_id": sid, "context": material["context"],
                    "prompt_messages": material["prompt_messages"]},
            outputs={"review_status": "REVIEWER_APPROVED", "reviewer_approved_target": material["target"]},
            notes="Explicit reviewer-submitted target; model output/report feedback was not promoted.",
        )
        if type(review_id) is not int or review_id < 1:
            raise RuntimeError("OWNED_TRAINING_REVIEW_TARGET_WRITE_FAILED")
        result = _existing(connection, material, resource)
        if result is None:
            raise RuntimeError("OWNED_TRAINING_REVIEW_REOPEN_FAILED")
        _authorize(gate, material, resource)
        result["state"] = "recorded"
        return result
