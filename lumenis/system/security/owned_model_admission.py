"""Exact Permission admission for a server-bound owned model version.

This module records a high-risk runtime approval for a fully pinned model
binding. It does not load, register, publish, or execute a model. Training,
evaluation, source-use validation, and runtime execution remain with their
existing owners.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import hashlib
import json
import re
import uuid
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from lumenis.system.security import permission as _permission


_REQUEST_FIELDS = frozenset({
    "action", "model_id", "model_revision", "recipe", "domain_id", "scopes",
    "manifest_sha256", "train_sha256", "heldout_sha256",
    "candidate_identity_sha256", "adapter_sha256", "adapter_config_sha256",
    "training_run_sha256", "checkpoint_recovery_sha256", "evaluation_sha256",
    "quality_review_sha256", "source_use_sha256", "source_use_version",
    "evaluation_ref", "quality_review_ref", "runtime_sha256", "executor_sha256",
    "review_validator_sha256", "source_validator_sha256", "allowed_operations",
    "context_window_tokens", "output_token_limit", "prior_binding_sha256",
})
_HASH_FIELDS = frozenset({
    "manifest_sha256", "train_sha256", "heldout_sha256",
    "candidate_identity_sha256", "adapter_sha256", "adapter_config_sha256",
    "training_run_sha256", "checkpoint_recovery_sha256", "evaluation_sha256",
    "quality_review_sha256", "source_use_sha256", "runtime_sha256",
    "executor_sha256", "review_validator_sha256", "source_validator_sha256",
})
_HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
_OPERATION_RE = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_ACTIONS = frozenset({"admit", "rollback", "revoke"})


def _request_type():
    """Import the Gateway-owned type lazily to avoid a Gateway/security cycle."""
    from lumenis.system.ai_gateway.owned_service import OwnedModelAdmissionRequest

    return OwnedModelAdmissionRequest


def _pretrained_request_type():
    """Import the v2 mutually exclusive pretrained request lazily."""
    from lumenis.system.ai_gateway.owned_service import OwnedPretrainedInferenceAdmissionRequest

    return OwnedPretrainedInferenceAdmissionRequest


def _request_schema(request: Any) -> Tuple[int, frozenset[str]]:
    if type(request) is _request_type():
        return 1, _REQUEST_FIELDS
    pretrained_type = _pretrained_request_type()
    if type(request) is pretrained_type and is_dataclass(request):
        return 2, frozenset(item.name for item in fields(request))
    raise ValueError("a canonical owned model admission request is required")


def _clean_text(value: Any, *, limit: int = 512) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= limit
        and not any(ord(character) < 32 for character in value)
    )


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _frozen_scope_context(context: Mapping[str, Any]) -> Dict[str, Any]:
    if type(context) is not dict or set(context) != {"scope_descriptors"}:
        raise ValueError("canonical scope descriptors are required")
    descriptors = context.get("scope_descriptors")
    if type(descriptors) is not dict:
        raise ValueError("canonical scope descriptors are required")
    return {
        "scope_descriptors": {
            key: dict(value) if type(value) is dict else value
            for key, value in descriptors.items()
        }
    }


def _normalized_training_scope_payload(
    request: Any,
    *,
    actor_id: Optional[int],
    domain_id: str,
    context: Mapping[str, Any],
    principal: Optional[Any],
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """Reuse canonical business or independent Shared scope, never a grant."""
    from lumenis.system.ai_gateway.owned_training import TrainingApprovalRequest

    request_cls = _request_type()
    if type(request) is not request_cls or not is_dataclass(request):
        raise ValueError("a canonical OwnedModelAdmissionRequest is required")
    if frozenset(item.name for item in fields(request)) != _REQUEST_FIELDS:
        raise ValueError("owned model admission request schema is not exact")

    values = {name: getattr(request, name) for name in _REQUEST_FIELDS}
    if type(values["action"]) is not str or values["action"] not in _ACTIONS:
        raise ValueError("owned model admission action is invalid")
    text_limits = {
        "model_id": 256, "model_revision": 256, "recipe": 512,
        "source_use_version": 128, "evaluation_ref": 1024,
        "quality_review_ref": 1024,
    }
    for name, limit in text_limits.items():
        if not _clean_text(values[name], limit=limit):
            raise ValueError("owned model admission reference is invalid")
    for name in _HASH_FIELDS:
        if type(values[name]) is not str or _HASH_RE.fullmatch(values[name]) is None:
            raise ValueError("owned model admission digest is invalid")
    if (type(values["scopes"]) is not tuple or not values["scopes"]
            or len(values["scopes"]) > 256):
        raise ValueError("owned model admission scopes must be an explicit tuple")
    if (any(not _clean_text(scope, limit=512) for scope in values["scopes"])
            or len(set(values["scopes"])) != len(values["scopes"])):
        raise ValueError("owned model admission scopes are invalid")
    operations = values["allowed_operations"]
    if (type(operations) is not tuple or not operations or len(operations) > 256
            or any(type(operation) is not str or _OPERATION_RE.fullmatch(operation) is None
                   for operation in operations)
            or len(set(operations)) != len(operations)
            or any(operation == "*" for operation in operations)):
        raise ValueError("owned model admission operations must be explicit and unique")
    for name in ("context_window_tokens", "output_token_limit"):
        if type(values[name]) is not int or not 1 <= values[name] <= 1_000_000:
            raise ValueError("owned model admission token limits must be positive integers")
    if values["output_token_limit"] > values["context_window_tokens"]:
        raise ValueError("output token limit exceeds the context window")
    prior = values["prior_binding_sha256"]
    if prior is not None and (type(prior) is not str or _HASH_RE.fullmatch(prior) is None):
        raise ValueError("prior model binding digest is invalid")
    if values["action"] in {"rollback", "revoke"} and prior is None:
        raise ValueError("rollback and revoke require the exact prior binding digest")

    if (type(domain_id) is not str or not domain_id
            or domain_id != domain_id.strip()):
        raise ValueError("a canonical model admission domain is required")
    if type(values["domain_id"]) is not str:
        raise ValueError("owned model admission domain is invalid")
    identity = _permission.owned_training_identity(
        actor_id=actor_id, principal=principal,
    )
    normalized_domain = domain_id.lower() if type(domain_id) is str else ""
    if normalized_domain == "zbmp":
        normalized_domain = "bmp"
    if values["domain_id"] != normalized_domain:
        raise ValueError("request domain does not match the server domain")

    if normalized_domain == 'shared':
        scope_name = 'shared_workspace:v1'
        if (values['scopes'] != (scope_name,) or type(context) is not dict
                or set(context) != {'scope_descriptors'}
                or type(context['scope_descriptors']) is not dict
                or set(context['scope_descriptors']) != {scope_name}):
            raise ValueError('Shared model admission requires its exact independent workspace scope')
        scope = _permission.validate_shared_workspace_scope(context['scope_descriptors'][scope_name])
        return identity, {'scope_descriptors': [{'scope': scope_name, **scope}]}, normalized_domain

    # This helper is used only to canonicalize scopes and server identity. Its
    # MODEL_TRAIN operation and resource are deliberately discarded below.
    training_request = TrainingApprovalRequest(
        model_id=values["model_id"],
        model_revision=values["model_revision"],
        train_sha256=values["train_sha256"],
        heldout_sha256=values["heldout_sha256"],
        domain_id=normalized_domain,
        scopes=values["scopes"],
        recipe=values["recipe"],
        manifest_sha256=values["manifest_sha256"],
    )
    scope_payload = _permission._owned_training_payload(
        training_request, actor_id=actor_id, domain_id=normalized_domain,
        context=context, principal=principal,
    )
    return identity, scope_payload, normalized_domain


def _normalized_pretrained_scope_payload(
    request: Any,
    *,
    actor_id: Optional[int],
    domain_id: str,
    context: Mapping[str, Any],
    principal: Optional[Any],
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """Normalize the existing CTH/BMP or independent Shared scopes for v2."""
    identity = _permission.owned_training_identity(actor_id=actor_id, principal=principal)
    normalized_domain = domain_id.lower() if type(domain_id) is str else ""
    if normalized_domain == "zbmp":
        normalized_domain = "bmp"
    if (normalized_domain not in {"cth", "bmp", "shared"}
            or request.domain_id != normalized_domain):
        raise ValueError("pretrained admission domain does not match the server scope")
    scope_names = request.scopes
    if (type(context) is not dict or set(context) != {"scope_descriptors"}
            or type(context.get("scope_descriptors")) is not dict
            or set(context["scope_descriptors"]) != set(scope_names)):
        raise ValueError("each pretrained admission scope needs one canonical descriptor")

    if normalized_domain == "shared":
        scope_name = "shared_workspace:v1"
        if scope_names != (scope_name,):
            raise ValueError("Shared pretrained inference requires its independent workspace scope")
        scope = _permission.validate_shared_workspace_scope(context["scope_descriptors"][scope_name])
        return identity, {"scope_descriptors": [{"scope": scope_name, **scope}]}, normalized_domain

    product_id = "CTH" if normalized_domain == "cth" else "ZBMP"
    descriptor_fields = {"domain_id", "product_id", "global_scope", "subject_id", "brand_focus_id"}
    descriptors = []
    for scope_name in scope_names:
        descriptor = context["scope_descriptors"][scope_name]
        if (type(descriptor) is not dict or set(descriptor) != descriptor_fields
                or descriptor.get("domain_id") != normalized_domain
                or descriptor.get("product_id") != product_id
                or type(descriptor.get("global_scope")) is not bool):
            raise ValueError("pretrained inference scope descriptor is invalid")
        global_scope = descriptor["global_scope"]
        subject_id = descriptor.get("subject_id")
        brand_focus_id = descriptor.get("brand_focus_id")
        if global_scope:
            if scope_name != "GLOBAL / ALL" or subject_id is not None or brand_focus_id is not None:
                raise ValueError("global pretrained scope must use the exact global descriptor")
        elif normalized_domain == "cth":
            if (not _permission._is_valid_scope_id(subject_id) or brand_focus_id is not None
                    or scope_name != subject_id):
                raise ValueError("CTH pretrained scope must name its exact registered Subject")
        elif (subject_id is not None or not _permission._is_valid_scope_id(brand_focus_id)
              or scope_name != brand_focus_id):
            raise ValueError("BMP pretrained scope must name its exact registered BrandFocus")
        descriptors.append({
            "scope": scope_name, "domain_id": normalized_domain, "product_id": product_id,
            "global_scope": global_scope, "subject_id": subject_id,
            "brand_focus_id": brand_focus_id,
        })
    return identity, {"scope_descriptors": descriptors}, normalized_domain


def _resource_payload(
    request: Any,
    *,
    actor_id: Optional[int],
    domain_id: str,
    context: Mapping[str, Any],
    principal: Optional[Any],
) -> Dict[str, Any]:
    schema_version, request_fields = _request_schema(request)
    if schema_version == 1:
        identity, scope_payload, normalized_domain = _normalized_training_scope_payload(
            request, actor_id=actor_id, domain_id=domain_id, context=context,
            principal=principal,
        )
    else:
        from lumenis.system.ai_gateway.owned_service import validate_pretrained_inference_admission_request

        validate_pretrained_inference_admission_request(request)
        identity, scope_payload, normalized_domain = _normalized_pretrained_scope_payload(
            request, actor_id=actor_id, domain_id=domain_id, context=context,
            principal=principal,
        )
    values = {name: getattr(request, name) for name in request_fields}
    payload: Dict[str, Any] = {
        "schema_version": schema_version,
        "operation": _permission.OperationType.RUNTIME_OPERATION.value,
        "request": values,
        "actor_id": identity["actor_id"],
        "caller": identity["caller"],
        "identity_kind": identity["identity_kind"],
        "domain_id": normalized_domain,
        "scope_descriptors": scope_payload["scope_descriptors"],
    }
    if identity["identity_kind"] == "workspace":
        payload["principal_kind"] = identity["principal_kind"]
        payload["principal_ref"] = identity["principal_ref"]
    return payload


def owned_model_admission_resource(
    request: Any,
    *,
    actor_id: Optional[int] = None,
    domain_id: str,
    context: Mapping[str, Any],
    principal: Optional[Any] = None,
) -> str:
    """Return the exact opaque runtime-approval resource for a pinned binding.

    The request and its server-authenticated identity, domain, and normalized
    scopes all participate in the hash. Building this resource grants nothing.
    """
    payload = _resource_payload(
        request, actor_id=actor_id, domain_id=domain_id, context=context,
        principal=principal,
    )
    return f"owned_model_admission:v{payload['schema_version']}:" + _digest(payload)


@dataclass(frozen=True)
class OwnedModelAdmissionDecision:
    allowed: bool
    code: str
    resource: str
    request_sha256: str
    permission_audit_id: Optional[str] = None
    scope_audit_ids: Tuple[str, ...] = ()
    approval_token_sha256: Optional[str] = None

    @property
    def audit_hashes(self) -> Dict[str, str]:
        result: Dict[str, str] = {}
        if type(self.permission_audit_id) is str and self.permission_audit_id:
            result["permission"] = hashlib.sha256(
                self.permission_audit_id.encode("utf-8"),
            ).hexdigest()
        for index, audit_id in enumerate(self.scope_audit_ids):
            if type(audit_id) is str and audit_id:
                result[f"scope_{index}"] = hashlib.sha256(
                    audit_id.encode("utf-8"),
                ).hexdigest()
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "code": self.code,
            "resource": self.resource,
            "request_sha256": self.request_sha256,
            "permission_audit_id": self.permission_audit_id,
            "scope_audit_ids": list(self.scope_audit_ids),
            "audit_hashes": self.audit_hashes,
            "approval_token_sha256": self.approval_token_sha256,
        }


class OwnedModelAdmissionVerifier:
    """Fresh actor, scope, review, and exact human-approval verifier."""

    def __init__(
        self,
        gate: Any,
        request: Any,
        *,
        actor_id: Optional[int],
        domain_id: str,
        context: Mapping[str, Any],
        principal: Optional[Any],
        review_validator: Callable[..., Any],
        review_dependency_paths: Tuple[Any, ...],
    ) -> None:
        self._gate = gate
        self._request = request
        self._actor_id = actor_id
        self._domain_id = domain_id
        self._context = _frozen_scope_context(context)
        self._principal = principal
        self._review_validator = review_validator
        self._review_dependency_paths = review_dependency_paths
        self._identity = _permission.owned_training_identity(
            actor_id=actor_id, principal=principal,
        )
        self._payload = _resource_payload(
            request, actor_id=actor_id, domain_id=domain_id,
            context=self._context, principal=principal,
        )
        self._request_sha256 = _digest(self._payload)
        self._schema_version, request_fields = _request_schema(request)
        self._request_fields = request_fields
        self._resource = f"owned_model_admission:v{self._schema_version}:" + self._request_sha256
        recipe = request.recipe if self._schema_version == 1 else (
            f"{request.runtime_engine}:{request.quantization_format}"
        )
        self._public_identity_json = json.dumps(
            {
                "schema_version": self._schema_version,
                "action": request.action,
                "artifact_kind": getattr(request, "artifact_kind", "TRAINED_CANDIDATE"),
                "model_id": request.model_id,
                "model_revision": request.model_revision,
                "recipe": recipe,
                "domain_id": self._payload["domain_id"],
                "scopes": list(request.scopes),
                "scope_descriptors": self._payload["scope_descriptors"],
                "actor_id": self._identity["actor_id"],
                "caller": self._identity["caller"],
                "principal_kind": self._identity["principal_kind"],
                "principal_ref": self._identity["principal_ref"],
                "request": {name: getattr(request, name) for name in request_fields},
                "request_sha256": self._request_sha256,
                "resource": self._resource,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        try:
            from agent_capability.formation import implementation_identity

            self._review_identity = implementation_identity(
                review_validator, review_dependency_paths,
            )
        except Exception:
            self._review_identity = None

    @property
    def request(self) -> Any:
        return self._request

    @property
    def resource(self) -> str:
        return self._resource

    @property
    def request_sha256(self) -> str:
        return self._request_sha256

    @property
    def public_identity(self) -> Dict[str, Any]:
        return json.loads(self._public_identity_json)

    def _decision(
        self,
        allowed: bool,
        code: str,
        *,
        permission_audit_id: Optional[str] = None,
        scope_audit_ids: Tuple[str, ...] = (),
        approval_token_sha256: Optional[str] = None,
    ) -> OwnedModelAdmissionDecision:
        return OwnedModelAdmissionDecision(
            allowed=allowed,
            code=code,
            resource=self._resource,
            request_sha256=self._request_sha256,
            permission_audit_id=permission_audit_id,
            scope_audit_ids=scope_audit_ids,
            approval_token_sha256=approval_token_sha256,
        )

    def recheck(self) -> OwnedModelAdmissionDecision:
        """Recheck all live gates; each call uses a fresh Permission operation id."""
        scope_audit_ids = []
        try:
            permission = _permission
            if permission.is_testing_bypass_enabled():
                return self._decision(False, "TESTING_BYPASS_ENABLED")

            identity = permission.owned_training_identity(
                actor_id=self._actor_id, principal=self._principal,
            )
            if identity != self._identity:
                return self._decision(False, "SERVER_IDENTITY_CHANGED")

            current_payload = _resource_payload(
                self._request, actor_id=self._actor_id,
                domain_id=self._domain_id, context=self._context,
                principal=self._principal,
            )
            if _digest(current_payload) != self._request_sha256:
                return self._decision(False, "REQUEST_OR_CONTEXT_CHANGED")

            if permission.get_permission_gate() is not self._gate:
                return self._decision(False, "CANONICAL_PERMISSION_GATE_CHANGED")
            if type(self._gate) is not permission.PermissionGate or self._gate.fail_closed is not True:
                return self._decision(False, "CANONICAL_PERMISSION_GATE_UNAVAILABLE")
            if identity["identity_kind"] == "workspace":
                try:
                    current_principal = permission.resolve_local_workspace_principal(
                        module="owned_model_admission", action="write",
                    )
                except Exception:
                    current_principal = None
                if not (
                    type(self._principal) is permission.LocalWorkspacePrincipal
                    and permission._is_server_local_workspace_principal(self._principal)
                    and type(current_principal) is permission.LocalWorkspacePrincipal
                    and permission._is_server_local_workspace_principal(current_principal)
                    and current_principal.actor_id == self._identity["actor_id"]
                    and current_principal.principal_kind == self._identity["principal_kind"]
                    and current_principal.principal_ref == self._identity["principal_ref"]
                    and current_principal == self._principal
                ):
                    return self._decision(False, "WORKSPACE_ADMISSION_SCOPE_UNAVAILABLE")
            if not self._gate.has_permission(permission.PermissionLevel.COMMIT):
                return self._decision(False, "RUNTIME_COMMIT_PERMISSION_UNAVAILABLE")

            operation_spec = self._gate._registry.get(permission.OperationType.RUNTIME_OPERATION)
            if not (
                type(operation_spec) is permission.OperationSpec
                and operation_spec.permission is permission.PermissionLevel.COMMIT
                and operation_spec.risk is permission.RiskLevel.HIGH
                and operation_spec.auto_allow is False
            ):
                return self._decision(False, "RUNTIME_OPERATION_POLICY_CHANGED")

            # Re-normalize through the same Permission scope boundary while
            # keeping v1 training receipts and v2 pretrained artifacts distinct.
            scope_normalizer = (_normalized_training_scope_payload
                                if self._schema_version == 1
                                else _normalized_pretrained_scope_payload)
            _, normalized_scope_payload, _ = scope_normalizer(
                self._request, actor_id=self._actor_id, domain_id=self._domain_id,
                context=self._context, principal=self._principal,
            )
            for descriptor in normalized_scope_payload["scope_descriptors"]:
                if self._payload['domain_id'] == 'shared':
                    actor = self._principal if self._principal is not None else {'id': self._actor_id}
                    shared_scope = {key: descriptor[key] for key in ('scope_kind', 'version')}
                    try:
                        shared_context, shared_audit = permission.authorize_shared_workspace(
                            actor, shared_scope, module='owned_model_admission', action='write',
                            gate=self._gate, _return_audit=True)
                    except Exception:
                        return self._decision(False, 'ACTOR_SCOPE_DENIED', scope_audit_ids=tuple(scope_audit_ids))
                    owner = ({'actor_id': self._actor_id} if self._principal is None else {
                        'principal_kind': self._identity['principal_kind'], 'principal_ref': self._identity['principal_ref']})
                    if (shared_context != {**shared_scope, **owner}
                            or type(shared_audit) is not str or not shared_audit):
                        return self._decision(False, 'ACTOR_SCOPE_DENIED', scope_audit_ids=tuple(scope_audit_ids))
                    scope_audit_ids.append(shared_audit)
                    continue
                if identity["identity_kind"] == "workspace":
                    scope = permission.check_local_workspace_scope_permission(
                        self._principal,
                        domain_id=self._payload["domain_id"], action="write",
                        module="owned_model_admission",
                        subject_id=descriptor["subject_id"],
                        brand_focus_id=descriptor["brand_focus_id"],
                        global_scope=descriptor["global_scope"], gate=self._gate,
                    )
                else:
                    scope = permission.check_actor_scope_permission(
                        {"id": self._actor_id},
                        domain_id=self._payload["domain_id"], action="write",
                        module="owned_model_admission",
                        subject_id=descriptor["subject_id"],
                        brand_focus_id=descriptor["brand_focus_id"],
                        global_scope=descriptor["global_scope"], gate=self._gate,
                    )
                if type(scope) is permission.ActorScopePermissionResult:
                    if type(scope.audit_id) is str and scope.audit_id:
                        scope_audit_ids.append(scope.audit_id)
                if (identity["identity_kind"] == "workspace"
                        and type(scope) is permission.ActorScopePermissionResult
                        and scope.code in {
                            "invalid_scope", "workspace_unavailable", "scope_unavailable",
                            "audit_unavailable",
                        }):
                    return self._decision(
                        False, "WORKSPACE_ADMISSION_SCOPE_UNAVAILABLE",
                        scope_audit_ids=tuple(scope_audit_ids),
                    )
                expected_focus = (
                    descriptor["subject_id"]
                    if self._payload["domain_id"] == "cth"
                    else descriptor["brand_focus_id"]
                )
                expected_resource = (
                    f"{self._payload['domain_id']}:"
                    f"{'GLOBAL / ALL' if descriptor['global_scope'] else expected_focus}"
                )
                if not (
                    type(scope) is permission.ActorScopePermissionResult
                    and scope.allowed is True
                    and scope.verification_state == "verified"
                    and scope.actor_id == self._identity["actor_id"]
                    and scope.caller == self._identity["caller"]
                    and permission._canonical_business_domain_id(scope.domain_id)
                    == permission._canonical_business_domain_id(self._payload["domain_id"])
                    and scope.principal_kind == self._identity["principal_kind"]
                    and scope.principal_ref == self._identity["principal_ref"]
                    and scope.subject_id == descriptor["subject_id"]
                    and scope.brand_focus_id == descriptor["brand_focus_id"]
                    and scope.global_scope is descriptor["global_scope"]
                    and scope.scope_action == "write"
                    and scope.operation_type == "resource_scope_write"
                    and scope.resource == expected_resource
                    and type(scope.audit_id) is str and bool(scope.audit_id)
                    and scope.scope_audit_id == scope.audit_id
                ):
                    return self._decision(
                        False, "ACTOR_SCOPE_DENIED",
                        scope_audit_ids=tuple(scope_audit_ids),
                    )

            from agent_capability.formation import implementation_identity

            try:
                current_review_identity = implementation_identity(
                    self._review_validator, self._review_dependency_paths,
                )
            except Exception:
                return self._decision(
                    False, "REVIEW_VALIDATOR_IDENTITY_UNAVAILABLE",
                    scope_audit_ids=tuple(scope_audit_ids),
                )
            if (current_review_identity != self._request.review_validator_sha256
                    or current_review_identity != self._review_identity):
                return self._decision(
                    False, "REVIEW_VALIDATOR_IDENTITY_MISMATCH",
                    scope_audit_ids=tuple(scope_audit_ids),
                )
            if self._request.action != "revoke":
                try:
                    review_result = self._review_validator(self._request)
                except Exception:
                    review_result = None
                if review_result is not True:
                    return self._decision(
                        False, "QUALITY_REVIEW_UNAVAILABLE_OR_FAILED",
                        scope_audit_ids=tuple(scope_audit_ids),
                    )

            operation_id = f"owned-model-admission:{uuid.uuid4().hex}"
            if self._payload['domain_id'] == 'shared':
                actor = self._principal if self._principal is not None else {'id': self._actor_id}
                approval = permission.check_shared_workspace_effect(
                    actor, {'scope_kind': 'shared_workspace', 'version': 1},
                    permission.OperationType.RUNTIME_OPERATION, self._resource,
                    module='owned_model_admission', action='write', gate=self._gate)
            else:
                approval = self._gate.check(
                    permission.OperationType.RUNTIME_OPERATION,
                    resource=self._resource,
                    caller=self._identity["caller"],
                    operation_id=operation_id,
                    domain_id=self._payload["domain_id"],
                    exact_approval_required=True,
                )
            token = self._gate.get_valid_approval_token(
                permission.OperationType.RUNTIME_OPERATION.value,
                self._resource,
                exact=True,
            )
            if not (
                approval.allowed is True
                and approval.requires_approval is True
                and approval.operation_type == permission.OperationType.RUNTIME_OPERATION.value
                and approval.resource == self._resource
                and approval.caller == self._identity["caller"]
                and (approval.domain_id is None if self._payload['domain_id'] == 'shared' else
                     permission._canonical_business_domain_id(approval.domain_id)
                     == permission._canonical_business_domain_id(self._payload["domain_id"]))
                and approval.risk_level == permission.RiskLevel.HIGH.value
                and approval.permission_required == permission.PermissionLevel.COMMIT.value
                and type(approval.audit_id) is str
                and bool(approval.audit_id)
                and type(approval.approval_token) is str
                and bool(approval.approval_token)
                and type(token) is str
                and token == approval.approval_token
            ):
                return self._decision(
                    False, "EXACT_RUNTIME_APPROVAL_REQUIRED",
                    permission_audit_id=approval.audit_id,
                    scope_audit_ids=tuple(scope_audit_ids),
                )
            return self._decision(
                True, "EXACT_RUNTIME_APPROVAL_VERIFIED",
                permission_audit_id=approval.audit_id,
                scope_audit_ids=tuple(scope_audit_ids),
                approval_token_sha256=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            )
        except Exception:
            return self._decision(
                False, "OWNED_MODEL_ADMISSION_CHECK_UNAVAILABLE",
                scope_audit_ids=tuple(scope_audit_ids),
            )


def make_owned_model_admission_verifier(
    gate: Any,
    request: Any,
    *,
    actor_id: Optional[int] = None,
    domain_id: str,
    context: Mapping[str, Any],
    principal: Optional[Any] = None,
    review_validator: Callable[..., Any],
    review_dependency_paths: Tuple[Any, ...] = (),
) -> OwnedModelAdmissionVerifier:
    """Bind a typed admission to the canonical singleton and server review code."""
    if type(gate) is not _permission.PermissionGate:
        raise ValueError("the canonical PermissionGate is required")
    if gate is not _permission.get_permission_gate():
        raise ValueError("the canonical PermissionGate singleton is required")
    if not callable(review_validator):
        raise ValueError("a server-owned review validator is required")
    if type(review_dependency_paths) not in {tuple, list}:
        raise ValueError("review dependency paths must be an explicit sequence")
    dependencies = tuple(review_dependency_paths)
    if any(type(path) not in {str} and not hasattr(path, "__fspath__") for path in dependencies):
        raise ValueError("review dependency path is invalid")
    _request_schema(request)
    # Validate the complete typed request and freeze the exact scope snapshot.
    frozen_context = _frozen_scope_context(context)
    _resource_payload(
        request, actor_id=actor_id, domain_id=domain_id,
        context=frozen_context, principal=principal,
    )
    return OwnedModelAdmissionVerifier(
        gate, request, actor_id=actor_id, domain_id=domain_id,
        context=frozen_context, principal=principal,
        review_validator=review_validator,
        review_dependency_paths=dependencies,
    )
