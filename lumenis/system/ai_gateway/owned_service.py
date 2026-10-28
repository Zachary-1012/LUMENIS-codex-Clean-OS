"""Explicitly admitted production execution through the single owned Gateway.

This module binds only server-held canonical admission and runtime objects. It
does not discover a runtime, infer caller identity, persist business truth, or
fall back to another provider. CandidateInferenceRequest remains evaluation-only.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import math
import re
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlsplit

_HASH = re.compile(r"^[0-9a-f]{64}$")
_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,95}$")
_OPERATION = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_DOMAINS = frozenset({"cth", "bmp", "shared"})
_MAX_SOURCE_REFS = 256
_MAX_USER_PAYLOAD_CHARS = 1_000_000
_MAX_SYSTEM_PROMPT_CHARS = 64_000
_MAX_SCHEMA_CHARS = 64_000
_MAX_TOKEN_LIMIT = 1_000_000
_MAX_ID_CHARS = 512
_RUNTIME_IDENTITY_FIELDS = frozenset({
    "runtime_sha256", "executor_sha256", "candidate_identity_sha256",
    "model_id", "model_revision", "recipe", "manifest_sha256",
    "train_sha256", "heldout_sha256", "adapter_sha256",
    "adapter_config_sha256", "context_window_tokens", "output_token_limit",
})
_PRETRAINED_RUNTIME_IDENTITY_FIELDS = frozenset({
    "schema_version", "artifact_kind", "runtime_sha256", "executor_sha256",
    "artifact_identity_sha256", "model_id", "model_revision", "recipe",
    "manifest_sha256", "runtime_build_sha256", "runtime_package_lock_sha256",
    "tokenizer_sha256", "chat_template_sha256", "context_window_tokens",
    "output_token_limit", "cpu_threads", "memory_limit_bytes",
    "generation_timeout_seconds", "max_concurrent_requests",
})
_REQUEST_HASH_FIELDS = (
    "source_use_policy_sha256", "source_binding_sha256", "input_revision_sha256",
)
_SCHEMA_KEYS = frozenset({
    "$schema", "title", "description", "type", "required", "properties",
    "additionalProperties", "items", "enum", "const", "minLength",
    "maxLength", "minimum", "maximum", "minItems", "maxItems",
})


class OwnedServiceBlocked(RuntimeError):
    """A safe, stable failure code; never contains model output or raw errors."""

    def __init__(self, code: str, *, status: str = "BLOCKED"):
        self.code = code if isinstance(code, str) and _CODE.fullmatch(code) else "OWNED_SERVICE_BLOCKED"
        self.status = status if status in {"INVALID_INPUT", "UNAVAILABLE", "BLOCKED", "CANCELLED", "ERROR"} else "BLOCKED"
        super().__init__(self.code)


@dataclass(frozen=True)
class OwnedModelAdmissionRequest:
    """Legacy v1 training-derived admission shape; retained for compatibility."""

    action: str
    model_id: str
    model_revision: str
    recipe: str
    domain_id: str
    scopes: tuple[str, ...]
    manifest_sha256: str
    train_sha256: str
    heldout_sha256: str
    candidate_identity_sha256: str
    adapter_sha256: str
    adapter_config_sha256: str
    training_run_sha256: str
    checkpoint_recovery_sha256: str
    evaluation_sha256: str
    quality_review_sha256: str
    source_use_sha256: str
    source_use_version: str
    evaluation_ref: str
    quality_review_ref: str
    runtime_sha256: str
    executor_sha256: str
    review_validator_sha256: str
    source_validator_sha256: str
    allowed_operations: tuple[str, ...]
    context_window_tokens: int
    output_token_limit: int
    prior_binding_sha256: str | None = None


@dataclass(frozen=True)
class OwnedPretrainedInferenceAdmissionRequest:
    """v2 admission for a fixed pretrained CPU inference artifact.

    This shape deliberately has no training, adapter, optimizer or checkpoint
    fields. Constructing the request records an identity only; Permission
    approval and model loading remain separate operations.
    """

    schema_version: int
    artifact_kind: str
    action: str
    domain_id: str
    scopes: tuple[str, ...]
    model_id: str
    model_revision: str
    source_repository: str
    license_id: str
    license_text_sha256: str
    usage_policy_sha256: str
    model_format: str
    manifest_sha256: str
    artifact_files: tuple[tuple[str, int, str], ...]
    weight_files: tuple[str, ...]
    tokenizer_file: str
    tokenizer_sha256: str
    chat_template_file: str
    chat_template_sha256: str
    quantization_format: str
    quantization_parameters_sha256: str | None
    conversion_recipe: str | None
    conversion_sha256: str | None
    runtime_engine: str
    runtime_version: str
    runtime_build_sha256: str
    runtime_packages: tuple[tuple[str, str], ...]
    runtime_package_lock_sha256: str
    evaluation_sha256: str
    quality_review_sha256: str
    source_use_sha256: str
    source_use_version: str
    evaluation_ref: str
    quality_review_ref: str
    runtime_sha256: str
    executor_sha256: str
    review_validator_sha256: str
    source_validator_sha256: str
    allowed_operations: tuple[str, ...]
    context_window_tokens: int
    output_token_limit: int
    cpu_threads: int
    memory_limit_bytes: int
    generation_timeout_seconds: int
    max_concurrent_requests: int
    prior_binding_sha256: str | None = None


def pretrained_inference_manifest_payload(request: OwnedPretrainedInferenceAdmissionRequest) -> dict:
    """Canonical v2 artifact/runtime manifest covered by Permission admission."""
    return {
        "schema_version": 2,
        "artifact_kind": "PRETRAINED_INFERENCE",
        "model": {
            "model_id": request.model_id,
            "revision": request.model_revision,
            "source_repository": request.source_repository,
            "license_id": request.license_id,
            "license_text_sha256": request.license_text_sha256,
            "usage_policy_sha256": request.usage_policy_sha256,
            "format": request.model_format,
            "artifact_files": [list(item) for item in request.artifact_files],
            "weight_files": list(request.weight_files),
            "tokenizer_file": request.tokenizer_file,
            "tokenizer_sha256": request.tokenizer_sha256,
            "chat_template_file": request.chat_template_file,
            "chat_template_sha256": request.chat_template_sha256,
            "quantization_format": request.quantization_format,
            "quantization_parameters_sha256": request.quantization_parameters_sha256,
            "conversion_recipe": request.conversion_recipe,
            "conversion_sha256": request.conversion_sha256,
        },
        "runtime": {
            "engine": request.runtime_engine,
            "version": request.runtime_version,
            "build_sha256": request.runtime_build_sha256,
            "packages": [list(item) for item in request.runtime_packages],
            "package_lock_sha256": request.runtime_package_lock_sha256,
        },
        "limits": {
            "context_window_tokens": request.context_window_tokens,
            "output_token_limit": request.output_token_limit,
            "cpu_threads": request.cpu_threads,
            "memory_limit_bytes": request.memory_limit_bytes,
            "generation_timeout_seconds": request.generation_timeout_seconds,
            "max_concurrent_requests": request.max_concurrent_requests,
        },
    }


def pretrained_inference_manifest_sha256(request: OwnedPretrainedInferenceAdmissionRequest) -> str:
    """Hash the full, path-free manifest identity without granting admission."""
    if type(request) is not OwnedPretrainedInferenceAdmissionRequest:
        raise OwnedServiceBlocked("PRETRAINED_ADMISSION_TYPE_INVALID", status="INVALID_INPUT")
    encoded = json.dumps(pretrained_inference_manifest_payload(request), ensure_ascii=False,
                         sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def pretrained_artifact_identity_sha256(request: OwnedPretrainedInferenceAdmissionRequest) -> str:
    """Digest model/source/license/files only, independent of runtime budgets."""
    payload = pretrained_inference_manifest_payload(request)["model"]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_pretrained_inference_admission_request(request: object) -> None:
    """Validate the mutually exclusive, non-training v2 request shape."""
    if type(request) is not OwnedPretrainedInferenceAdmissionRequest:
        raise OwnedServiceBlocked("PRETRAINED_ADMISSION_TYPE_INVALID", status="INVALID_INPUT")
    from dataclasses import fields
    expected_fields = frozenset(item.name for item in fields(OwnedPretrainedInferenceAdmissionRequest))
    if type(getattr(request, "__dict__", None)) is not dict or frozenset(request.__dict__) != expected_fields:
        raise OwnedServiceBlocked("PRETRAINED_ADMISSION_SCHEMA_INVALID", status="BLOCKED")
    if (type(request.schema_version) is not int or request.schema_version != 2
            or request.artifact_kind != "PRETRAINED_INFERENCE"):
        raise OwnedServiceBlocked("PRETRAINED_ARTIFACT_KIND_UNSUPPORTED", status="BLOCKED")
    if (type(request.action) is not str or request.action not in {"admit", "rollback", "revoke"}
            or type(request.domain_id) is not str or request.domain_id not in _DOMAINS):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_REQUEST_INVALID", status="BLOCKED")
    if (type(request.scopes) is not tuple or not request.scopes
            or len(request.scopes) > _MAX_SOURCE_REFS
            or any(not _safe_text(item, limit=_MAX_ID_CHARS) for item in request.scopes)
            or len(set(request.scopes)) != len(request.scopes)):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_SCOPES_INVALID", status="BLOCKED")
    if request.domain_id == "shared" and request.scopes != ("shared_workspace:v1",):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_SCOPES_INVALID", status="BLOCKED")

    model_id_ok = (type(request.model_id) is str and len(request.model_id) <= 256
                   and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}/[A-Za-z0-9][A-Za-z0-9._-]{0,127}", request.model_id))
    if (not model_id_ok or type(request.model_revision) is not str
            or not re.fullmatch(r"[0-9a-f]{40,64}", request.model_revision)
            or not _safe_text(request.source_repository, limit=512)):
        raise OwnedServiceBlocked("PRETRAINED_MODEL_SOURCE_IDENTITY_INVALID", status="BLOCKED")
    parsed = urlsplit(request.source_repository)
    if (parsed.scheme != "https" or parsed.netloc != "huggingface.co"
            or parsed.query or parsed.fragment or parsed.username or parsed.password
            or parsed.path != "/" + request.model_id):
        raise OwnedServiceBlocked("PRETRAINED_MODEL_SOURCE_IDENTITY_INVALID", status="BLOCKED")
    if (not _safe_text(request.license_id, limit=128)
            or request.license_id.strip().lower() in {"unknown", "none", "unlicensed"}):
        raise OwnedServiceBlocked("PRETRAINED_LICENSE_EVIDENCE_REQUIRED", status="BLOCKED")
    hashes = (request.license_text_sha256, request.usage_policy_sha256,
              request.tokenizer_sha256, request.chat_template_sha256,
              request.runtime_build_sha256, request.runtime_package_lock_sha256,
              request.evaluation_sha256, request.quality_review_sha256,
              request.source_use_sha256, request.runtime_sha256,
              request.executor_sha256, request.review_validator_sha256,
              request.source_validator_sha256)
    if any(type(value) is not str or not _HASH.fullmatch(value) for value in hashes):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_HASH_INVALID", status="BLOCKED")

    if request.model_format != "transformers_safetensors":
        raise OwnedServiceBlocked("PRETRAINED_MODEL_FORMAT_UNSUPPORTED", status="BLOCKED")
    if (type(request.artifact_files) is not tuple or not request.artifact_files
            or len(request.artifact_files) > 20000):
        raise OwnedServiceBlocked("PRETRAINED_ARTIFACT_FILE_SET_INVALID", status="BLOCKED")
    file_map = {}
    total_bytes = 0
    previous = None
    for item in request.artifact_files:
        if (type(item) is not tuple or len(item) != 3
                or not _safe_text(item[0], limit=1024)
                or type(item[1]) is not int or item[1] <= 0
                or type(item[2]) is not str or not _HASH.fullmatch(item[2])):
            raise OwnedServiceBlocked("PRETRAINED_ARTIFACT_FILE_SET_INVALID", status="BLOCKED")
        path = PurePosixPath(item[0])
        if ("\\" in item[0] or path.is_absolute() or str(path) != item[0]
                or any(part in {"", ".", ".."} for part in path.parts)
                or item[0] in file_map or (previous is not None and item[0] <= previous)):
            raise OwnedServiceBlocked("PRETRAINED_ARTIFACT_FILE_SET_INVALID", status="BLOCKED")
        file_map[item[0]] = (item[1], item[2])
        total_bytes += item[1]
        previous = item[0]
    if total_bytes > 80 * 1024**3 or "config.json" not in file_map:
        raise OwnedServiceBlocked("PRETRAINED_ARTIFACT_FILE_SET_INVALID", status="BLOCKED")
    if (type(request.weight_files) is not tuple or not request.weight_files
            or any(not _safe_text(name, limit=1024) for name in request.weight_files)
            or len(set(request.weight_files)) != len(request.weight_files)
            or tuple(sorted(request.weight_files)) != request.weight_files
            or any(not name.endswith(".safetensors") for name in request.weight_files)
            or any(name not in file_map for name in request.weight_files)):
        raise OwnedServiceBlocked("PRETRAINED_WEIGHT_SHARDS_INVALID", status="BLOCKED")
    if (not _safe_text(request.tokenizer_file, limit=1024)
            or not _safe_text(request.chat_template_file, limit=1024)
            or request.tokenizer_file not in file_map
            or file_map[request.tokenizer_file][1] != request.tokenizer_sha256
            or request.chat_template_file not in file_map
            or file_map[request.chat_template_file][1] != request.chat_template_sha256):
        raise OwnedServiceBlocked("PRETRAINED_TOKENIZER_IDENTITY_INVALID", status="BLOCKED")

    if (request.quantization_format != "none"
            or request.quantization_parameters_sha256 is not None
            or request.conversion_recipe is not None or request.conversion_sha256 is not None):
        raise OwnedServiceBlocked("PRETRAINED_QUANTIZATION_BACKEND_UNAVAILABLE", status="UNAVAILABLE")
    if (request.runtime_engine != "transformers-cpu"
            or not _safe_text(request.runtime_version, limit=128)):
        raise OwnedServiceBlocked("PRETRAINED_CPU_RUNTIME_UNSUPPORTED", status="UNAVAILABLE")
    packages = request.runtime_packages
    expected_package_names = ("safetensors", "tokenizers", "torch", "transformers")
    if (type(packages) is not tuple or len(packages) != len(expected_package_names)
            or any(type(item) is not tuple or len(item) != 2
                   or not _safe_text(item[0], limit=64)
                   or not _safe_text(item[1], limit=128) for item in packages)
            or tuple(name for name, _ in packages) != expected_package_names
            or any(not _safe_text(version, limit=128) for _, version in packages)
            or dict(packages).get("transformers") != request.runtime_version
            or any("cuda" in version.lower() or "+cu" in version.lower() for _, version in packages)):
        raise OwnedServiceBlocked("PRETRAINED_CPU_PACKAGE_LOCK_INVALID", status="BLOCKED")
    package_digest = hashlib.sha256(json.dumps(
        [list(item) for item in packages], sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")).hexdigest()
    if package_digest != request.runtime_package_lock_sha256:
        raise OwnedServiceBlocked("PRETRAINED_CPU_PACKAGE_LOCK_MISMATCH", status="BLOCKED")

    operations = request.allowed_operations
    if (type(operations) is not tuple or not operations
            or any(type(item) is not str or not _OPERATION.fullmatch(item) for item in operations)
            or len(set(operations)) != len(operations) or "*" in operations):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_OPERATIONS_INVALID", status="BLOCKED")
    for name in ("context_window_tokens", "output_token_limit"):
        value = getattr(request, name)
        if type(value) is not int or not 1 <= value <= _MAX_TOKEN_LIMIT:
            raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_TOKEN_LIMIT_INVALID", status="BLOCKED")
    if request.output_token_limit > request.context_window_tokens:
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_TOKEN_LIMIT_INVALID", status="BLOCKED")
    bounds = ((request.cpu_threads, 1, 128), (request.memory_limit_bytes, 1, 2**50),
              (request.generation_timeout_seconds, 1, 1800),
              (request.max_concurrent_requests, 1, 8))
    if any(type(value) is not int or not low <= value <= high for value, low, high in bounds):
        raise OwnedServiceBlocked("PRETRAINED_CPU_RESOURCE_LIMITS_INVALID", status="BLOCKED")
    if (not _safe_text(request.source_use_version, limit=128)
            or not _safe_text(request.evaluation_ref, limit=1024)
            or not _safe_text(request.quality_review_ref, limit=1024)):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_REQUEST_INVALID", status="BLOCKED")
    if request.action in {"rollback", "revoke"}:
        if type(request.prior_binding_sha256) is not str or not _HASH.fullmatch(request.prior_binding_sha256):
            raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_PRIOR_BINDING_REQUIRED", status="BLOCKED")
    elif request.prior_binding_sha256 is not None and (
            type(request.prior_binding_sha256) is not str or not _HASH.fullmatch(request.prior_binding_sha256)):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_PRIOR_BINDING_INVALID", status="BLOCKED")
    if pretrained_inference_manifest_sha256(request) != request.manifest_sha256:
        raise OwnedServiceBlocked("PRETRAINED_MODEL_MANIFEST_HASH_MISMATCH", status="BLOCKED")


@dataclass(frozen=True)
class OwnedServiceRequest:
    operation: str
    request_id: str
    job_id: str
    actor_ref: str
    domain_id: str
    scope: str
    source_use_policy_version: str
    source_use_policy_sha256: str
    source_binding_sha256: str
    source_evidence_refs: tuple[str, ...]
    input_revision_sha256: str
    system_prompt: str
    user_payload: str
    response_schema_json: str
    max_output_tokens: int


@dataclass(frozen=True)
class SourceUseDecision:
    allowed: bool
    code: str
    actor_ref: str
    domain_id: str
    scope: str
    source_use_policy_version: str
    source_use_policy_sha256: str
    source_binding_sha256: str
    source_evidence_refs: tuple[str, ...]
    scope_audit_id: str
    source_audit_id: str


@dataclass(frozen=True)
class OwnedServiceBinding:
    """Server-held objects used for one exact, independently scoped binding."""

    admission_verifier: object
    runtime: object
    source_validator: Callable[[OwnedServiceRequest], SourceUseDecision]
    source_dependency_paths: tuple[object, ...] = ()


@dataclass(frozen=True)
class OwnedPretrainedServiceProfile:
    """One already-admitted CPU model profile resolved by existing owners.

    This object is an in-memory handoff only. Callers resolve the exact
    artifact manifest, Permission verifier and SourceUse validator from their
    existing owners; this profile does not create or persist those authorities.
    """

    request: OwnedPretrainedInferenceAdmissionRequest
    artifact_root: object
    admission_verifier: object
    source_validator: Callable[[OwnedServiceRequest], SourceUseDecision]
    source_dependency_paths: tuple[object, ...] = ()


@dataclass(frozen=True)
class _BoundSlot:
    binding: OwnedServiceBinding
    binding_sha256: str


_SLOTS: dict[str, _BoundSlot] = {}
_SLOTS_LOCK = threading.RLock()


def _safe_text(value: object, *, limit: int, required: bool = True,
               multiline: bool = False) -> bool:
    if type(value) is not str or len(value) > limit or (required and not value.strip()):
        return False
    for char in value:
        code = ord(char)
        if code == 0 or (code < 32 and not (multiline and char in "\n\r\t")):
            return False
    return True


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise OwnedServiceBlocked("OWNED_SERVICE_CANONICALIZATION_FAILED", status="INVALID_INPUT") from exc


def _strict_json(raw: str | bytes) -> object:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise OwnedServiceBlocked("OWNED_SERVICE_JSON_DUPLICATE_KEY", status="INVALID_INPUT")
            result[key] = value
        return result

    def nonfinite(_value):
        raise OwnedServiceBlocked("OWNED_SERVICE_JSON_NONFINITE", status="INVALID_INPUT")

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    except OwnedServiceBlocked:
        raise
    except (ValueError, UnicodeDecodeError, TypeError) as exc:
        raise OwnedServiceBlocked("OWNED_SERVICE_JSON_INVALID", status="INVALID_INPUT") from exc
    return value


def validate_owned_service_request(request: object) -> dict | None:
    if type(request) is not OwnedServiceRequest:
        raise OwnedServiceBlocked("OWNED_SERVICE_REQUEST_REQUIRED", status="INVALID_INPUT")
    if (not _safe_text(request.operation, limit=64) or not _OPERATION.fullmatch(request.operation)
            or not _safe_text(request.request_id, limit=_MAX_ID_CHARS)
            or not _safe_text(request.job_id, limit=_MAX_ID_CHARS)
            or not _safe_text(request.actor_ref, limit=_MAX_ID_CHARS)
            or request.domain_id not in _DOMAINS
            or not _safe_text(request.scope, limit=_MAX_ID_CHARS)
            or not _safe_text(request.source_use_policy_version, limit=128)
            or not _safe_text(request.system_prompt, limit=_MAX_SYSTEM_PROMPT_CHARS, multiline=True)
            or not _safe_text(request.user_payload, limit=_MAX_USER_PAYLOAD_CHARS, multiline=True)
            or not _safe_text(request.response_schema_json, limit=_MAX_SCHEMA_CHARS, required=False)):
        raise OwnedServiceBlocked("OWNED_SERVICE_REQUEST_INVALID", status="INVALID_INPUT")
    if request.domain_id == 'shared' and request.scope != 'shared_workspace:v1':
        raise OwnedServiceBlocked('OWNED_SERVICE_SCOPE_INVALID', status='INVALID_INPUT')
    if any(type(getattr(request, field)) is not str or not _HASH.fullmatch(getattr(request, field))
           for field in _REQUEST_HASH_FIELDS):
        raise OwnedServiceBlocked("OWNED_SERVICE_HASH_INVALID", status="INVALID_INPUT")
    refs = request.source_evidence_refs
    if (type(refs) is not tuple or not refs or len(refs) > _MAX_SOURCE_REFS
            or any(not _safe_text(item, limit=_MAX_ID_CHARS) for item in refs)
            or len(set(refs)) != len(refs)):
        raise OwnedServiceBlocked("OWNED_SERVICE_EVIDENCE_REFS_INVALID", status="INVALID_INPUT")
    if (type(request.max_output_tokens) is not int
            or not 1 <= request.max_output_tokens <= _MAX_TOKEN_LIMIT):
        raise OwnedServiceBlocked("OWNED_SERVICE_TOKEN_LIMIT_INVALID", status="INVALID_INPUT")
    if not request.response_schema_json:
        return None
    schema = _strict_json(request.response_schema_json)
    if type(schema) is not dict:
        raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_INVALID", status="INVALID_INPUT")
    _validate_schema_definition(schema)
    return schema


def owned_service_request_digest(request: OwnedServiceRequest) -> str:
    from dataclasses import asdict

    validate_owned_service_request(request)
    return hashlib.sha256(_canonical_bytes(asdict(request))).hexdigest()


def _validate_schema_definition(schema: dict, *, depth: int = 0) -> None:
    if depth > 32 or set(schema) - _SCHEMA_KEYS:
        raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_UNSUPPORTED", status="INVALID_INPUT")
    schema_type = schema.get("type")
    if schema_type is not None and schema_type not in {"object", "array", "string", "number", "integer", "boolean", "null"}:
        raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_INVALID", status="INVALID_INPUT")
    required = schema.get("required", [])
    if (type(required) is not list or any(type(item) is not str or not item for item in required)
            or len(set(required)) != len(required)):
        raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_INVALID", status="INVALID_INPUT")
    properties = schema.get("properties", {})
    if type(properties) is not dict or any(type(key) is not str or not key for key in properties):
        raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_INVALID", status="INVALID_INPUT")
    for child in properties.values():
        if type(child) is not dict:
            raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_INVALID", status="INVALID_INPUT")
        _validate_schema_definition(child, depth=depth + 1)
    additional = schema.get("additionalProperties", True)
    if type(additional) is dict:
        _validate_schema_definition(additional, depth=depth + 1)
    elif type(additional) is not bool:
        raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_INVALID", status="INVALID_INPUT")
    items = schema.get("items")
    if items is not None:
        if type(items) is not dict:
            raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_INVALID", status="INVALID_INPUT")
        _validate_schema_definition(items, depth=depth + 1)
    for key in ("minLength", "maxLength", "minItems", "maxItems"):
        if key in schema and (type(schema[key]) is not int or schema[key] < 0):
            raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_INVALID", status="INVALID_INPUT")
    for key in ("minimum", "maximum"):
        if key in schema and (type(schema[key]) not in {int, float} or isinstance(schema[key], bool)
                              or not math.isfinite(schema[key])):
            raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_INVALID", status="INVALID_INPUT")
    if "enum" in schema and (type(schema["enum"]) is not list or not schema["enum"]):
        raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_INVALID", status="INVALID_INPUT")


def _matches_schema(value: object, schema: dict, *, depth: int = 0) -> bool:
    if depth > 32:
        return False
    schema_type = schema.get("type")
    checks = {
        "object": type(value) is dict,
        "array": type(value) is list,
        "string": type(value) is str,
        "integer": type(value) is int,
        "number": type(value) in {int, float} and type(value) is not bool and math.isfinite(value),
        "boolean": type(value) is bool,
        "null": value is None,
    }
    if schema_type is not None and not checks[schema_type]:
        return False
    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    if type(value) is str:
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", 1_000_000_000):
            return False
    if type(value) in {int, float} and type(value) is not bool:
        if not math.isfinite(value) or value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf):
            return False
    if type(value) is list:
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", 1_000_000_000):
            return False
        item_schema = schema.get("items")
        if item_schema is not None and any(not _matches_schema(item, item_schema, depth=depth + 1) for item in value):
            return False
    if type(value) is dict:
        required = schema.get("required", [])
        if any(key not in value for key in required):
            return False
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                if not _matches_schema(item, properties[key], depth=depth + 1):
                    return False
            elif additional is False:
                return False
            elif type(additional) is dict and not _matches_schema(item, additional, depth=depth + 1):
                return False
    return True


def _clean_reason(value: object, fallback: str) -> str:
    return value if type(value) is str and _CODE.fullmatch(value) else fallback


def _security_contract():
    try:
        module = importlib.import_module("lumenis.system.security.owned_model_admission")
        verifier_type = getattr(module, "OwnedModelAdmissionVerifier")
    except Exception as exc:
        raise OwnedServiceBlocked("OWNED_ADMISSION_CONTRACT_UNAVAILABLE", status="UNAVAILABLE") from exc
    return module, OwnedModelAdmissionRequest, verifier_type


def _runtime_type():
    try:
        module = importlib.import_module("lumenis.system.ai_gateway.owned_inference")
        runtime_type = getattr(module, "OwnedProductionRuntime")
    except Exception as exc:
        raise OwnedServiceBlocked("OWNED_PRODUCTION_RUNTIME_TYPE_UNAVAILABLE", status="UNAVAILABLE") from exc
    return runtime_type


def _runtime_type_for_admission(request: object):
    """Return the one runtime class authorized by the exact request type."""
    module, request_type, _verifier_type = _security_contract()
    if type(request) is request_type:
        raise OwnedServiceBlocked("TRAINED_CUDA_RUNTIME_WITHDRAWN_BY_PO", status="UNAVAILABLE")
    pretrained_type = getattr(module, "_pretrained_request_type")()
    if type(request) is not pretrained_type:
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_REQUEST_INVALID", status="UNAVAILABLE")
    try:
        inference = importlib.import_module("lumenis.system.ai_gateway.owned_inference")
        return getattr(inference, "OwnedPretrainedProductionRuntime")
    except Exception as exc:
        raise OwnedServiceBlocked("OWNED_PRODUCTION_RUNTIME_TYPE_UNAVAILABLE", status="UNAVAILABLE") from exc


def _validate_admission_request(request: object, expected_type: type | None = None) -> None:
    module, legacy_type, _verifier_type = _security_contract()
    pretrained_type = OwnedPretrainedInferenceAdmissionRequest
    if type(request) is legacy_type:
        if expected_type is not None and type(request) is not expected_type:
            raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_REQUEST_INVALID", status="UNAVAILABLE")
    elif type(request) is pretrained_type:
        if expected_type is not None and expected_type is not pretrained_type:
            raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_REQUEST_INVALID", status="UNAVAILABLE")
        try:
            module_owned_service = importlib.import_module("lumenis.system.ai_gateway.owned_service")
            module_owned_service.validate_pretrained_inference_admission_request(request)
        except OwnedServiceBlocked:
            raise
        except Exception as exc:
            raise OwnedServiceBlocked("PRETRAINED_ADMISSION_REQUEST_INVALID", status="BLOCKED") from exc
        return
    else:
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_REQUEST_INVALID", status="UNAVAILABLE")
    if request.action not in {"admit", "rollback", "revoke"} or request.domain_id not in _DOMAINS:
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_REQUEST_INVALID", status="BLOCKED")
    hash_fields = (
        "manifest_sha256", "train_sha256", "heldout_sha256", "candidate_identity_sha256",
        "adapter_sha256", "adapter_config_sha256", "training_run_sha256",
        "checkpoint_recovery_sha256", "evaluation_sha256", "quality_review_sha256",
        "source_use_sha256", "runtime_sha256", "executor_sha256",
        "review_validator_sha256", "source_validator_sha256",
    )
    if any(type(getattr(request, field, None)) is not str or not _HASH.fullmatch(getattr(request, field))
           for field in hash_fields):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_HASH_INVALID", status="BLOCKED")
    for field, limit in (("model_id", 256), ("model_revision", 256), ("recipe", 512),
                         ("source_use_version", 128), ("evaluation_ref", 1024),
                         ("quality_review_ref", 1024)):
        if not _safe_text(getattr(request, field, None), limit=limit):
            raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_REQUEST_INVALID", status="BLOCKED")
    if (type(request.scopes) is not tuple or not request.scopes
            or len(request.scopes) > _MAX_SOURCE_REFS
            or any(not _safe_text(scope, limit=_MAX_ID_CHARS) for scope in request.scopes)
            or len(set(request.scopes)) != len(request.scopes)):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_SCOPES_INVALID", status="BLOCKED")
    if request.domain_id == 'shared' and request.scopes != ('shared_workspace:v1',):
        raise OwnedServiceBlocked('OWNED_MODEL_ADMISSION_SCOPES_INVALID', status='BLOCKED')
    if (type(request.allowed_operations) is not tuple or not request.allowed_operations
            or any(type(item) is not str or not _OPERATION.fullmatch(item) for item in request.allowed_operations)
            or len(set(request.allowed_operations)) != len(request.allowed_operations)):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_OPERATIONS_INVALID", status="BLOCKED")
    for field in ("context_window_tokens", "output_token_limit"):
        value = getattr(request, field, None)
        if type(value) is not int or not 1 <= value <= _MAX_TOKEN_LIMIT:
            raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_TOKEN_LIMIT_INVALID", status="BLOCKED")
    if request.output_token_limit > request.context_window_tokens:
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_TOKEN_LIMIT_INVALID", status="BLOCKED")
    prior = getattr(request, "prior_binding_sha256", None)
    if request.action in {"rollback", "revoke"}:
        if type(prior) is not str or not _HASH.fullmatch(prior):
            raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_PRIOR_BINDING_REQUIRED", status="BLOCKED")
    elif prior is not None and (type(prior) is not str or not _HASH.fullmatch(prior)):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_PRIOR_BINDING_INVALID", status="BLOCKED")


def _verifier_request(binding: OwnedServiceBinding, *, actions: frozenset[str] | None = None):
    _module, request_type, verifier_type = _security_contract()
    verifier = binding.admission_verifier
    if type(verifier) is not verifier_type:
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_VERIFIER_REQUIRED", status="UNAVAILABLE")
    request = verifier.request
    _validate_admission_request(request)
    if actions is not None and request.action not in actions:
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_ACTION_INVALID", status="BLOCKED")
    return verifier, request


def _verify_admission(verifier: object) -> dict:
    try:
        expected_request_sha = verifier.request_sha256
        expected_resource = verifier.resource
        public_identity = verifier.public_identity
        if type(expected_request_sha) is not str or not _HASH.fullmatch(expected_request_sha):
            raise TypeError("request hash invalid")
        if type(public_identity) is not dict:
            raise TypeError("public identity invalid")
        public_identity_bytes = _canonical_bytes(public_identity)
        decision = verifier.recheck()
        if type(getattr(decision, "allowed", None)) is not bool:
            raise TypeError("decision invalid")
        if decision.allowed is not True:
            raise OwnedServiceBlocked(_clean_reason(getattr(decision, "code", None), "OWNED_MODEL_ADMISSION_DENIED"), status="BLOCKED")
        if (getattr(decision, "request_sha256", None) != expected_request_sha
                or getattr(decision, "resource", None) != expected_resource):
            raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_IDENTITY_MISMATCH", status="BLOCKED")
        audit_hashes = getattr(decision, "audit_hashes", None)
        if (type(audit_hashes) is not dict or not audit_hashes
                or any(type(key) is not str or not _safe_text(key, limit=128)
                       or type(value) is not str or not _HASH.fullmatch(value)
                       for key, value in audit_hashes.items())):
            raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_AUDIT_REQUIRED", status="BLOCKED")
        return {
            "request_sha256": expected_request_sha,
            "audit_hashes": dict(audit_hashes),
            "public_identity_sha256": hashlib.sha256(public_identity_bytes).hexdigest(),
            "public_identity": public_identity,
        }
    except OwnedServiceBlocked:
        raise
    except Exception as exc:
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_RECHECK_FAILED", status="BLOCKED") from exc


def _runtime_identity(binding: OwnedServiceBinding, admission_request: object) -> dict:
    runtime_type = _runtime_type_for_admission(admission_request)
    if type(binding.runtime) is not runtime_type:
        raise OwnedServiceBlocked("OWNED_PRODUCTION_RUNTIME_REQUIRED", status="UNAVAILABLE")
    if (binding.runtime._source_validator is not binding.source_validator
            or tuple(binding.runtime._source_dependency_paths) != binding.source_dependency_paths):
        raise OwnedServiceBlocked("OWNED_SOURCE_VALIDATOR_BINDING_MISMATCH", status="BLOCKED")
    try:
        _bound_runtime_method(binding.runtime, runtime_type, "generate")
        identity = _bound_runtime_method(binding.runtime, runtime_type, "identity")()
        if type(admission_request) is OwnedPretrainedInferenceAdmissionRequest:
            _bound_runtime_method(binding.runtime, runtime_type, "close")
    except Exception as exc:
        if isinstance(exc, OwnedServiceBlocked):
            raise
        raise OwnedServiceBlocked("OWNED_RUNTIME_IDENTITY_UNAVAILABLE", status="BLOCKED") from exc
    if type(admission_request) is OwnedModelAdmissionRequest:
        if type(identity) is not dict or set(identity) != _RUNTIME_IDENTITY_FIELDS:
            raise OwnedServiceBlocked("OWNED_RUNTIME_IDENTITY_INVALID", status="BLOCKED")
        hashes = _RUNTIME_IDENTITY_FIELDS - {"model_id", "model_revision", "recipe", "context_window_tokens", "output_token_limit"}
        if any(type(identity[key]) is not str or not _HASH.fullmatch(identity[key]) for key in hashes):
            raise OwnedServiceBlocked("OWNED_RUNTIME_IDENTITY_INVALID", status="BLOCKED")
        for key in ("model_id", "model_revision", "recipe"):
            if not _safe_text(identity[key], limit=512):
                raise OwnedServiceBlocked("OWNED_RUNTIME_IDENTITY_INVALID", status="BLOCKED")
        expected = {
            "runtime_sha256": admission_request.runtime_sha256,
            "executor_sha256": admission_request.executor_sha256,
            "candidate_identity_sha256": admission_request.candidate_identity_sha256,
            "model_id": admission_request.model_id,
            "model_revision": admission_request.model_revision,
            "recipe": admission_request.recipe,
            "manifest_sha256": admission_request.manifest_sha256,
            "train_sha256": admission_request.train_sha256,
            "heldout_sha256": admission_request.heldout_sha256,
            "adapter_sha256": admission_request.adapter_sha256,
            "adapter_config_sha256": admission_request.adapter_config_sha256,
            "context_window_tokens": admission_request.context_window_tokens,
            "output_token_limit": admission_request.output_token_limit,
        }
    else:
        if type(identity) is not dict or set(identity) != _PRETRAINED_RUNTIME_IDENTITY_FIELDS:
            raise OwnedServiceBlocked("OWNED_RUNTIME_IDENTITY_INVALID", status="BLOCKED")
        hashes = {
            "runtime_sha256", "executor_sha256", "artifact_identity_sha256",
            "manifest_sha256", "runtime_build_sha256", "runtime_package_lock_sha256",
            "tokenizer_sha256", "chat_template_sha256",
        }
        if any(type(identity[key]) is not str or not _HASH.fullmatch(identity[key]) for key in hashes):
            raise OwnedServiceBlocked("OWNED_RUNTIME_IDENTITY_INVALID", status="BLOCKED")
        if (identity["schema_version"] != 2 or identity["artifact_kind"] != "PRETRAINED_INFERENCE"
                or any(not _safe_text(identity[key], limit=512) for key in ("model_id", "model_revision", "recipe"))):
            raise OwnedServiceBlocked("OWNED_RUNTIME_IDENTITY_INVALID", status="BLOCKED")
        integer_fields = (
            "context_window_tokens", "output_token_limit", "cpu_threads",
            "memory_limit_bytes", "generation_timeout_seconds", "max_concurrent_requests",
        )
        if any(type(identity[key]) is not int or identity[key] <= 0 for key in integer_fields):
            raise OwnedServiceBlocked("OWNED_RUNTIME_IDENTITY_INVALID", status="BLOCKED")
        expected = {
            "schema_version": 2,
            "artifact_kind": "PRETRAINED_INFERENCE",
            "runtime_sha256": admission_request.runtime_sha256,
            "executor_sha256": admission_request.executor_sha256,
            "artifact_identity_sha256": pretrained_artifact_identity_sha256(admission_request),
            "model_id": admission_request.model_id,
            "model_revision": admission_request.model_revision,
            "recipe": f"{admission_request.runtime_engine}:{admission_request.quantization_format}",
            "manifest_sha256": admission_request.manifest_sha256,
            "runtime_build_sha256": admission_request.runtime_build_sha256,
            "runtime_package_lock_sha256": admission_request.runtime_package_lock_sha256,
            "tokenizer_sha256": admission_request.tokenizer_sha256,
            "chat_template_sha256": admission_request.chat_template_sha256,
            "context_window_tokens": admission_request.context_window_tokens,
            "output_token_limit": admission_request.output_token_limit,
            "cpu_threads": admission_request.cpu_threads,
            "memory_limit_bytes": admission_request.memory_limit_bytes,
            "generation_timeout_seconds": admission_request.generation_timeout_seconds,
            "max_concurrent_requests": admission_request.max_concurrent_requests,
        }
    for key in ("context_window_tokens", "output_token_limit"):
        if type(identity.get(key)) is not int or not 1 <= identity[key] <= _MAX_TOKEN_LIMIT:
            raise OwnedServiceBlocked("OWNED_RUNTIME_IDENTITY_INVALID", status="BLOCKED")
    if identity["output_token_limit"] > identity["context_window_tokens"]:
        raise OwnedServiceBlocked("OWNED_RUNTIME_IDENTITY_INVALID", status="BLOCKED")
    if identity != expected:
        raise OwnedServiceBlocked("OWNED_RUNTIME_ADMISSION_IDENTITY_MISMATCH", status="BLOCKED")
    return dict(identity)


def _bound_runtime_method(runtime: object, runtime_type: type, name: str):
    """Resolve an admitted method from the exact runtime class, never its instance dict."""
    if type(runtime) is not runtime_type or name not in {"identity", "generate", "measure_request", "close"}:
        raise OwnedServiceBlocked("OWNED_RUNTIME_METHOD_INVALID", status="BLOCKED")
    try:
        instance_namespace = object.__getattribute__(runtime, "__dict__")
    except AttributeError:
        instance_namespace = None
    if instance_namespace is not None:
        if type(instance_namespace) is not dict:
            raise OwnedServiceBlocked("OWNED_RUNTIME_METHOD_INVALID", status="BLOCKED")
        if name in instance_namespace:
            raise OwnedServiceBlocked("OWNED_RUNTIME_METHOD_SHADOWED", status="BLOCKED")
    method = vars(runtime_type).get(name)
    if (not inspect.isfunction(method)
            or method.__module__ != runtime_type.__module__
            or method.__qualname__ != f"{runtime_type.__qualname__}.{name}"):
        raise OwnedServiceBlocked("OWNED_RUNTIME_METHOD_INVALID", status="BLOCKED")
    try:
        bound = method.__get__(runtime, runtime_type)
    except Exception as exc:
        raise OwnedServiceBlocked("OWNED_RUNTIME_METHOD_INVALID", status="BLOCKED") from exc
    if getattr(bound, "__func__", None) is not method:
        raise OwnedServiceBlocked("OWNED_RUNTIME_METHOD_INVALID", status="BLOCKED")
    return bound


def _source_code_hash(binding: OwnedServiceBinding, admission_request: object) -> str:
    expected = admission_request.source_validator_sha256
    if not callable(binding.source_validator) or type(binding.source_dependency_paths) is not tuple:
        raise OwnedServiceBlocked("OWNED_SOURCE_VALIDATOR_REQUIRED", status="UNAVAILABLE")
    try:
        from agent_capability.formation import implementation_identity

        actual = implementation_identity(binding.source_validator, binding.source_dependency_paths)
    except Exception as exc:
        raise OwnedServiceBlocked("OWNED_SOURCE_VALIDATOR_PIN_UNAVAILABLE", status="UNAVAILABLE") from exc
    if type(actual) is not str or not _HASH.fullmatch(actual) or actual != expected:
        raise OwnedServiceBlocked("OWNED_SOURCE_VALIDATOR_HASH_MISMATCH", status="BLOCKED")
    return actual


def _binding_identity(binding: OwnedServiceBinding, verifier: object,
                      runtime_identity: dict, source_validator_sha256: str,
                      admission_result: dict) -> str:
    material = {
        "admission_request_sha256": admission_result["request_sha256"],
        "admission_public_identity_sha256": admission_result["public_identity_sha256"],
        "runtime_identity": runtime_identity,
        "source_validator_sha256": source_validator_sha256,
        "domain_id": verifier.request.domain_id,
        "scopes": list(verifier.request.scopes),
    }
    return hashlib.sha256(_canonical_bytes(material)).hexdigest()


def _validate_binding(binding: object, *, actions: frozenset[str] | None = None) -> dict:
    if type(binding) is not OwnedServiceBinding:
        raise OwnedServiceBlocked("OWNED_SERVICE_BINDING_REQUIRED", status="UNAVAILABLE")
    verifier, admission_request = _verifier_request(binding, actions=actions or frozenset({"admit", "rollback"}))
    admission_result = _verify_admission(verifier)
    identity = _runtime_identity(binding, admission_request)
    source_hash = _source_code_hash(binding, admission_request)
    binding_sha = _binding_identity(binding, verifier, identity, source_hash, admission_result)
    return {
        "verifier": verifier,
        "admission_request": admission_request,
        "admission_result": admission_result,
        "runtime_identity": identity,
        "source_validator_sha256": source_hash,
        "binding_sha256": binding_sha,
    }


def _request_matches_admission(request: OwnedServiceRequest, admission_request: object,
                               public_identity: dict) -> None:
    caller = public_identity.get("caller") if type(public_identity) is dict else None
    if type(caller) is not str or not caller or request.actor_ref != caller:
        raise OwnedServiceBlocked("OWNED_SERVICE_ACTOR_MISMATCH", status="BLOCKED")
    if request.domain_id != admission_request.domain_id:
        raise OwnedServiceBlocked("OWNED_SERVICE_DOMAIN_MISMATCH", status="BLOCKED")
    if request.scope not in admission_request.scopes:
        raise OwnedServiceBlocked("OWNED_SERVICE_SCOPE_NOT_ADMITTED", status="BLOCKED")
    if request.operation not in admission_request.allowed_operations:
        raise OwnedServiceBlocked("OWNED_SERVICE_OPERATION_NOT_ADMITTED", status="BLOCKED")
    if (request.source_use_policy_version != admission_request.source_use_version
            or request.source_use_policy_sha256 != admission_request.source_use_sha256):
        raise OwnedServiceBlocked("OWNED_SERVICE_SOURCE_POLICY_MISMATCH", status="BLOCKED")
    if request.max_output_tokens > admission_request.output_token_limit:
        raise OwnedServiceBlocked("OWNED_SERVICE_OUTPUT_BUDGET_EXCEEDED", status="BLOCKED")


def _validate_source_decision(decision: object, request: OwnedServiceRequest) -> SourceUseDecision:
    if type(decision) is not SourceUseDecision or type(decision.allowed) is not bool:
        raise OwnedServiceBlocked("OWNED_SOURCE_DECISION_INVALID", status="BLOCKED")
    if decision.allowed is not True:
        raise OwnedServiceBlocked(_clean_reason(decision.code, "OWNED_SOURCE_USE_DENIED"), status="BLOCKED")
    if (not _safe_text(decision.code, limit=96) or not _CODE.fullmatch(decision.code)
            or decision.actor_ref != request.actor_ref
            or decision.domain_id != request.domain_id
            or decision.scope != request.scope
            or decision.source_use_policy_version != request.source_use_policy_version
            or decision.source_use_policy_sha256 != request.source_use_policy_sha256
            or decision.source_binding_sha256 != request.source_binding_sha256
            or decision.source_evidence_refs != request.source_evidence_refs):
        raise OwnedServiceBlocked("OWNED_SOURCE_DECISION_MISMATCH", status="BLOCKED")
    for field in ("actor_ref", "scope", "source_use_policy_version", "scope_audit_id", "source_audit_id"):
        if not _safe_text(getattr(decision, field), limit=1024):
            raise OwnedServiceBlocked("OWNED_SOURCE_AUDIT_REQUIRED", status="BLOCKED")
    for field in ("source_use_policy_sha256", "source_binding_sha256"):
        value = getattr(decision, field)
        if type(value) is not str or not _HASH.fullmatch(value):
            raise OwnedServiceBlocked("OWNED_SOURCE_DECISION_INVALID", status="BLOCKED")
    if (type(decision.source_evidence_refs) is not tuple
            or not decision.source_evidence_refs
            or any(not _safe_text(item, limit=_MAX_ID_CHARS) for item in decision.source_evidence_refs)):
        raise OwnedServiceBlocked("OWNED_SOURCE_DECISION_INVALID", status="BLOCKED")
    if any(getattr(decision, field).strip().lower() in {"none", "null", "unknown", "test", "mock", "fixture"}
           for field in ("scope_audit_id", "source_audit_id")):
        raise OwnedServiceBlocked("OWNED_SOURCE_AUDIT_REQUIRED", status="BLOCKED")
    return decision


def _source_call(binding: OwnedServiceBinding, request: OwnedServiceRequest,
                 admission_request: object) -> SourceUseDecision:
    before_hash = _source_code_hash(binding, admission_request)
    try:
        decision = binding.source_validator(request)
    except Exception as exc:
        raise OwnedServiceBlocked("OWNED_SOURCE_VALIDATION_FAILED", status="BLOCKED") from exc
    validated = _validate_source_decision(decision, request)
    after_hash = _source_code_hash(binding, admission_request)
    if before_hash != after_hash:
        raise OwnedServiceBlocked("OWNED_SOURCE_VALIDATOR_CHANGED", status="BLOCKED")
    return validated


def _cancelled(predicate: Callable[[], bool]) -> bool:
    try:
        value = predicate()
    except Exception as exc:
        raise OwnedServiceBlocked("OWNED_SERVICE_CANCEL_CHECK_FAILED", status="BLOCKED") from exc
    if type(value) is not bool:
        raise OwnedServiceBlocked("OWNED_SERVICE_CANCEL_CHECK_INVALID", status="BLOCKED")
    return value


def _failure(request: object, *, code: str, status: str, digest: str = "",
             attempt_id: str | None = None) -> dict:
    request_id = request.request_id if type(request) is OwnedServiceRequest else ""
    result = {
        "ok": False, "status": status, "code": _clean_reason(code, "OWNED_SERVICE_FAILED"),
        "provider": "owned", "request_id": request_id,
        "request_digest": digest, "text": None, "analysis": None,
        "real_input_bound": False, "evaluation_state": "NOT_RUN",
        "quality_state": "NOT_EVALUATED", "promotion_status": "NOT_PROMOTED",
    }
    if type(attempt_id) is str and re.fullmatch(r"attempt_[0-9a-f]{32}", attempt_id):
        result["attempt_id"] = attempt_id
    return result


def _validate_raw_result(raw: object, request: OwnedServiceRequest, digest: str,
                         identity: dict, admission_request: object,
                         schema: dict | None) -> tuple[str, object, dict]:
    common_required = {
        "generated_text", "text", "finish_reason", "termination_token", "final_channel_prefill",
        "model_id", "model_revision", "recipe", "request_sha256", "request_digest", "run_id",
        "runtime_sha256", "executor_sha256", "prompt_tokens", "completion_tokens", "total_tokens",
        "context_window_tokens", "output_token_limit",
    }
    if type(admission_request) is OwnedModelAdmissionRequest:
        required = common_required | {"candidate_identity_sha256", "adapter_sha256", "adapter_config_sha256"}
        identity_keys = ("model_id", "model_revision", "recipe", "candidate_identity_sha256",
                         "adapter_sha256", "adapter_config_sha256", "runtime_sha256", "executor_sha256")
    else:
        required = common_required | {
            "artifact_kind", "artifact_identity_sha256", "manifest_sha256",
            "runtime_build_sha256", "runtime_package_lock_sha256", "tokenizer_sha256",
            "chat_template_sha256", "device_kind",
        }
        identity_keys = (
            "model_id", "model_revision", "recipe", "artifact_kind", "artifact_identity_sha256",
            "manifest_sha256", "runtime_sha256", "executor_sha256", "runtime_build_sha256",
            "runtime_package_lock_sha256", "tokenizer_sha256", "chat_template_sha256",
        )
    if type(raw) is not dict or not required.issubset(raw):
        raise OwnedServiceBlocked("OWNED_RUNTIME_RESULT_INVALID", status="ERROR")
    for key in identity_keys:
        if raw[key] != identity[key]:
            raise OwnedServiceBlocked("OWNED_RUNTIME_RESULT_IDENTITY_MISMATCH", status="BLOCKED")
    if type(admission_request) is not OwnedModelAdmissionRequest and raw["device_kind"] != "cpu":
        raise OwnedServiceBlocked("OWNED_RUNTIME_DEVICE_MISMATCH", status="BLOCKED")
    if (raw["request_sha256"] != digest or raw["request_digest"] != digest
            or not _safe_text(raw["run_id"], limit=_MAX_ID_CHARS)
            or type(raw["generated_text"]) is not str
            or raw["text"] != raw["generated_text"]
            or type(raw["finish_reason"]) is not str
            or type(raw["termination_token"]) is not str
            or type(raw["final_channel_prefill"]) is not bool):
        raise OwnedServiceBlocked("OWNED_RUNTIME_RESULT_INVALID", status="ERROR")
    counters = (raw["prompt_tokens"], raw["completion_tokens"])
    if (any(type(value) is not int or value < 0 for value in counters)
            or type(raw["total_tokens"]) is not int
            or raw["total_tokens"] != raw["prompt_tokens"] + raw["completion_tokens"]
            or raw["completion_tokens"] < 1
            or raw["completion_tokens"] > request.max_output_tokens
            or type(raw["context_window_tokens"]) is not int
            or type(raw["output_token_limit"]) is not int
            or raw["context_window_tokens"] != admission_request.context_window_tokens
            or raw["output_token_limit"] != admission_request.output_token_limit
            or raw["context_window_tokens"] != identity["context_window_tokens"]
            or raw["output_token_limit"] != identity["output_token_limit"]
            or raw["prompt_tokens"] + raw["completion_tokens"] > raw["context_window_tokens"]):
        raise OwnedServiceBlocked("OWNED_RUNTIME_TOKEN_BUDGET_INVALID", status="BLOCKED")

    from . import owned_evaluation
    final, completion_state = owned_evaluation._parse_final(
        raw["generated_text"], raw["finish_reason"], raw["termination_token"], raw["final_channel_prefill"])
    if completion_state != "COMPLETED_FINAL" or not final:
        raise OwnedServiceBlocked("OWNED_RUNTIME_FINAL_INVALID", status="ERROR")
    token_counts = {
        "prompt_tokens": raw["prompt_tokens"],
        "completion_tokens": raw["completion_tokens"],
        "total_tokens": raw["prompt_tokens"] + raw["completion_tokens"],
    }
    if schema is None:
        return final, None, token_counts
    value = _strict_json(final)
    if not _matches_schema(value, schema):
        raise OwnedServiceBlocked("OWNED_SERVICE_RESPONSE_SCHEMA_MISMATCH", status="ERROR")
    return "", value, token_counts


def measure_owned_request(request: object) -> dict:
    """Count with the bound runtime; a measurement never grants generation."""
    digest = ""
    slot = None
    try:
        validate_owned_service_request(request)
        digest = owned_service_request_digest(request)
        with _SLOTS_LOCK:
            slot = _SLOTS.get(request.domain_id)
        if slot is None:
            raise OwnedServiceBlocked("OWNED_SERVICE_EXECUTOR_NOT_BOUND", status="UNAVAILABLE")
        before = _validate_binding(slot.binding, actions=frozenset({"admit", "rollback"}))
        if before["binding_sha256"] != slot.binding_sha256:
            raise OwnedServiceBlocked("OWNED_SERVICE_BINDING_CHANGED")
        _request_matches_admission(request, before["admission_request"], before["admission_result"]["public_identity"])
        source_before = _source_call(slot.binding, request, before["admission_request"])
        runtime_type = _runtime_type_for_admission(before["admission_request"])
        measured = _bound_runtime_method(slot.binding.runtime, runtime_type, "measure_request")(request)
        after = _validate_binding(slot.binding, actions=frozenset({"admit", "rollback"}))
        source_after = _source_call(slot.binding, request, after["admission_request"])
        with _SLOTS_LOCK:
            current = _SLOTS.get(request.domain_id) is slot
        if (not current or after["binding_sha256"] != before["binding_sha256"]
                or after["runtime_identity"] != before["runtime_identity"]
                or any(getattr(source_before, field) != getattr(source_after, field) for field in (
                    "allowed", "code", "actor_ref", "domain_id", "scope", "source_use_policy_version",
                    "source_use_policy_sha256", "source_binding_sha256", "source_evidence_refs"))):
            raise OwnedServiceBlocked("OWNED_SERVICE_BINDING_CHANGED")
        identity = after["runtime_identity"]
        if (type(measured) is not dict or measured.get("request_sha256") != digest
                or type(measured.get("prompt_tokens")) is not int or measured["prompt_tokens"] < 0
                or measured.get("context_window_tokens") != identity["context_window_tokens"]
                or measured.get("output_token_limit") != identity["output_token_limit"]
                or measured.get("output_tokens_reserved") != request.max_output_tokens
                or measured.get("runtime_sha256") != identity["runtime_sha256"]
                or measured.get("tokenizer_identity") != identity["runtime_sha256"]
                or not _HASH.fullmatch(str(measured.get("formatter_sha256", "")))
                or measured.get("generation_performed") is not False
                or measured.get("count_method") != "loaded_runtime_tokenizer"):
            raise OwnedServiceBlocked("OWNED_TOKEN_MEASUREMENT_INVALID")
        return {"ok": True, **measured, "binding_sha256": slot.binding_sha256,
            "fits": measured["prompt_tokens"] + request.max_output_tokens <= identity["context_window_tokens"]}
    except OwnedServiceBlocked as exc:
        if slot is not None and (not _admission_still_allowed(slot)
                                 or _runtime_failure_requires_unload(exc.code)):
            _retire_pretrained_slot(request.domain_id, slot)
        return _failure(request, code=exc.code, status=exc.status, digest=digest)
    except Exception:
        return _failure(request, code="OWNED_TOKEN_MEASUREMENT_UNAVAILABLE", status="UNAVAILABLE", digest=digest)


def run_owned_request(request: object, *, is_cancelled: Callable[[], bool] | None = None,
                      expected_binding_sha256: str | None = None) -> dict:
    """Execute one source-authorized typed request; never accepts caller booleans."""
    digest = ""
    slot = None
    attempt_id = None
    expected_binding_mismatch = False
    try:
        if expected_binding_sha256 is not None and (type(expected_binding_sha256) is not str
                or not _HASH.fullmatch(expected_binding_sha256)):
            raise OwnedServiceBlocked("OWNED_EXPECTED_BINDING_INVALID", status="INVALID_INPUT")
        schema = validate_owned_service_request(request)
        digest = owned_service_request_digest(request)
        cancelled = is_cancelled if is_cancelled is not None else (lambda: False)
        if not callable(cancelled):
            raise OwnedServiceBlocked("OWNED_SERVICE_CANCEL_CHECK_REQUIRED", status="INVALID_INPUT")
        if _cancelled(cancelled):
            raise OwnedServiceBlocked("OWNED_SERVICE_CANCELLED", status="CANCELLED")
        with _SLOTS_LOCK:
            slot = _SLOTS.get(request.domain_id)
        if slot is None:
            raise OwnedServiceBlocked("OWNED_SERVICE_EXECUTOR_NOT_BOUND", status="UNAVAILABLE")

        before = _validate_binding(slot.binding, actions=frozenset({"admit", "rollback"}))
        if before["binding_sha256"] != slot.binding_sha256:
            raise OwnedServiceBlocked("OWNED_SERVICE_BINDING_CHANGED", status="BLOCKED")
        if expected_binding_sha256 is not None and expected_binding_sha256 != before["binding_sha256"]:
            expected_binding_mismatch = True
            raise OwnedServiceBlocked("OWNED_SERVICE_BINDING_CHANGED", status="BLOCKED")
        admission_request = before["admission_request"]
        _request_matches_admission(
            request, admission_request,
            before["admission_result"]["public_identity"],
        )
        source_before = _source_call(slot.binding, request, admission_request)
        if _cancelled(cancelled):
            raise OwnedServiceBlocked("OWNED_SERVICE_CANCELLED", status="CANCELLED")

        def execution_cancelled():
            if _cancelled(cancelled):
                return True
            with _SLOTS_LOCK:
                return _SLOTS.get(request.domain_id) is not slot

        try:
            runtime_type = _runtime_type_for_admission(admission_request)
            generate = _bound_runtime_method(slot.binding.runtime, runtime_type, "generate")
            # Allocate only at the actual generation boundary. Admission,
            # permission, cancellation and budget failures before this point
            # remain distinguishable from a model execution attempt.
            attempt_id = "attempt_" + uuid.uuid4().hex
            raw = generate(request, is_cancelled=execution_cancelled)
        except OwnedServiceBlocked:
            raise
        except Exception as exc:
            from .owned_inference import OwnedInferenceBlocked

            if type(exc) is OwnedInferenceBlocked:
                reason = _clean_reason(str(exc), "OWNED_RUNTIME_EXECUTION_FAILED")
                status = "CANCELLED" if reason == "OWNED_INFERENCE_CANCELLED" else "BLOCKED"
                raise OwnedServiceBlocked(reason, status=status) from exc
            raise OwnedServiceBlocked("OWNED_RUNTIME_EXECUTION_FAILED", status="ERROR") from exc
        if _cancelled(execution_cancelled):
            raise OwnedServiceBlocked("OWNED_SERVICE_CANCELLED", status="CANCELLED")

        after = _validate_binding(slot.binding, actions=frozenset({"admit", "rollback"}))
        if (after["binding_sha256"] != slot.binding_sha256
                or after["runtime_identity"] != before["runtime_identity"]):
            raise OwnedServiceBlocked("OWNED_SERVICE_BINDING_CHANGED", status="BLOCKED")
        source_after = _source_call(slot.binding, request, admission_request)
        if (source_before.allowed is not source_after.allowed
                or source_before.code != source_after.code
                or any(getattr(source_before, field) != getattr(source_after, field) for field in (
                    "actor_ref", "domain_id", "scope", "source_use_policy_version",
                    "source_use_policy_sha256", "source_binding_sha256", "source_evidence_refs"))):
            raise OwnedServiceBlocked("OWNED_SOURCE_DECISION_CHANGED", status="BLOCKED")
        with _SLOTS_LOCK:
            if _SLOTS.get(request.domain_id) is not slot:
                raise OwnedServiceBlocked("OWNED_SERVICE_BINDING_CHANGED", status="BLOCKED")
        text, analysis, token_counts = _validate_raw_result(
            raw, request, digest, after["runtime_identity"], admission_request, schema)
        if _cancelled(execution_cancelled):
            raise OwnedServiceBlocked("OWNED_SERVICE_CANCELLED", status="CANCELLED")
        result = {
            "ok": True, "status": "COMPLETED", "code": "OWNED_INFERENCE_COMPLETED",
            "provider": "owned", "operation": request.operation,
            "domain_id": request.domain_id, "scope": request.scope,
            "request_id": request.request_id, "attempt_id": attempt_id,
            "request_digest": digest, "run_id": raw["run_id"],
            "model_id": after["runtime_identity"]["model_id"],
            "model_revision": after["runtime_identity"]["model_revision"],
            "recipe": after["runtime_identity"]["recipe"],
            "runtime_sha256": after["runtime_identity"]["runtime_sha256"],
            "executor_sha256": after["runtime_identity"]["executor_sha256"],
            "context_window_tokens": after["runtime_identity"]["context_window_tokens"],
            "output_token_limit": after["runtime_identity"]["output_token_limit"],
            "evaluation_sha256": admission_request.evaluation_sha256,
            "quality_review_sha256": admission_request.quality_review_sha256,
            "evaluation_ref": admission_request.evaluation_ref,
            "quality_review_ref": admission_request.quality_review_ref,
            "source_use_policy_version": request.source_use_policy_version,
            "source_use_policy_sha256": request.source_use_policy_sha256,
            "source_binding_sha256": request.source_binding_sha256,
            "input_revision_sha256": request.input_revision_sha256,
            "source_evidence_refs": list(request.source_evidence_refs),
            "source_audit_ids": {
                "scope_before": source_before.scope_audit_id,
                "source_before": source_before.source_audit_id,
                "scope_after": source_after.scope_audit_id,
                "source_after": source_after.source_audit_id,
            },
            "admission_request_sha256": after["admission_result"]["request_sha256"],
            "admission_audit_hashes": after["admission_result"]["audit_hashes"],
            "text": text or None, "analysis": analysis,
            "response_schema_state": "SUBSET_VALIDATED" if schema is not None else "TEXT_ONLY",
            **token_counts,
            "real_input_bound": True,
            "evaluation_state": "NOT_RUN", "quality_state": "NOT_EVALUATED",
            "promotion_status": "NOT_PROMOTED", "product_acceptance": False,
        }
        if type(admission_request) is OwnedModelAdmissionRequest:
            result.update({
                "artifact_kind": "TRAINED_CANDIDATE",
                "candidate_identity_sha256": after["runtime_identity"]["candidate_identity_sha256"],
                "adapter_sha256": after["runtime_identity"]["adapter_sha256"],
                "adapter_config_sha256": after["runtime_identity"]["adapter_config_sha256"],
                "manifest_sha256": admission_request.manifest_sha256,
                "train_sha256": admission_request.train_sha256,
                "heldout_sha256": admission_request.heldout_sha256,
                "training_run_sha256": admission_request.training_run_sha256,
                "checkpoint_recovery_sha256": admission_request.checkpoint_recovery_sha256,
            })
        else:
            result.update({
                "artifact_kind": "PRETRAINED_INFERENCE",
                "artifact_identity_sha256": after["runtime_identity"]["artifact_identity_sha256"],
                "manifest_sha256": admission_request.manifest_sha256,
                "runtime_build_sha256": admission_request.runtime_build_sha256,
                "runtime_package_lock_sha256": admission_request.runtime_package_lock_sha256,
                "tokenizer_sha256": admission_request.tokenizer_sha256,
                "chat_template_sha256": admission_request.chat_template_sha256,
                "device_kind": "cpu",
            })
        return result
    except OwnedServiceBlocked as exc:
        if slot is not None and (not _admission_still_allowed(slot)
                or (_runtime_failure_requires_unload(exc.code) and not expected_binding_mismatch)):
            _retire_pretrained_slot(request.domain_id, slot)
        return _failure(request, code=exc.code, status=exc.status, digest=digest,
                        attempt_id=attempt_id)
    except Exception:
        return _failure(request, code="OWNED_SERVICE_FAILED", status="ERROR", digest=digest,
                        attempt_id=attempt_id)


def bind_owned_service(binding: OwnedServiceBinding) -> dict:
    """Install one exact typed binding after fresh admission and identity checks."""
    before = _validate_binding(binding, actions=frozenset({"admit", "rollback"}))
    request = before["admission_request"]
    if request.domain_id not in _DOMAINS:
        raise OwnedServiceBlocked("OWNED_SERVICE_DOMAIN_INVALID")
    with _SLOTS_LOCK:
        current = _SLOTS.get(request.domain_id)
        prior = request.prior_binding_sha256
        if current is None:
            if request.action != "admit" or prior is not None:
                raise OwnedServiceBlocked("OWNED_SERVICE_PRIOR_BINDING_MISMATCH")
        elif prior != current.binding_sha256:
            raise OwnedServiceBlocked("OWNED_SERVICE_PRIOR_BINDING_MISMATCH")
        previous = current
        slot = _BoundSlot(binding=binding, binding_sha256=before["binding_sha256"])
        _SLOTS[request.domain_id] = slot
    try:
        after = _validate_binding(binding, actions=frozenset({"admit", "rollback"}))
        if after["binding_sha256"] != slot.binding_sha256:
            raise OwnedServiceBlocked("OWNED_SERVICE_BINDING_CHANGED")
    except Exception:
        with _SLOTS_LOCK:
            if _SLOTS.get(request.domain_id) is slot:
                if previous is None:
                    _SLOTS.pop(request.domain_id, None)
                else:
                    _SLOTS[request.domain_id] = previous
        raise
    result = {
        "ok": True, "status": "BOUND", "domain_id": request.domain_id,
        "binding_sha256": slot.binding_sha256,
        "admission_request_sha256": after["admission_result"]["request_sha256"],
    }
    if previous is not None and previous.binding.runtime is not binding.runtime:
        result["previous_runtime_unload_state"] = _close_pretrained_runtime(previous.binding)["state"]
    return result


def _close_pretrained_runtime(binding: OwnedServiceBinding) -> dict:
    """Release only the exact v2 CPU runtime owned by this service binding."""
    if type(binding) is not OwnedServiceBinding:
        return {"state": "UNLOAD_FAILED"}
    try:
        request = binding.admission_verifier.request
    except (AttributeError, TypeError):
        return {"state": "UNLOAD_FAILED"}
    if type(request) is not OwnedPretrainedInferenceAdmissionRequest:
        return {"state": "NOT_REQUIRED"}
    try:
        from . import owned_inference as inference

        runtime_type = inference.OwnedPretrainedProductionRuntime
        result = _bound_runtime_method(binding.runtime, runtime_type, "close")()
        if (type(result) is dict and result.get("ok") is True
                and result.get("state") == "CLOSED"):
            return {"state": "CLOSED"}
    except (AttributeError, ImportError, RuntimeError, TypeError, ValueError):
        return {"state": "UNLOAD_FAILED"}
    return {"state": "UNLOAD_FAILED"}


def _retire_pretrained_slot(domain_id: str, slot: _BoundSlot) -> dict:
    """Remove and unload the exact stale slot, without touching a replacement."""
    with _SLOTS_LOCK:
        if _SLOTS.get(domain_id) is not slot:
            return {"state": "REPLACED"}
        _SLOTS.pop(domain_id, None)
    return _close_pretrained_runtime(slot.binding)


def _admission_still_allowed(slot: _BoundSlot) -> bool:
    try:
        _verify_admission(slot.binding.admission_verifier)
        return True
    except OwnedServiceBlocked:
        return False


def _runtime_failure_requires_unload(code: str) -> bool:
    return code.startswith((
        "OWNED_RUNTIME_HANDLE_", "OWNED_RUNTIME_IDENTITY_", "OWNED_RUNTIME_METHOD_",
        "OWNED_RUNTIME_ADMISSION_", "PRETRAINED_RUNTIME_",
    )) or code in {
        "OWNED_SERVICE_BINDING_CHANGED",
        "OWNED_SOURCE_VALIDATOR_HASH_MISMATCH",
        "OWNED_SOURCE_VALIDATOR_PIN_UNAVAILABLE",
        "PRETRAINED_CPU_GENERATION_FAILED",
        "PRETRAINED_CPU_MEMORY_BUDGET_EXCEEDED",
        "PRETRAINED_CPU_THREAD_RESTORE_FAILED",
        "PRETRAINED_CPU_OUTPUT_CONTROL_TOKEN_INVALID",
    }


def _pretrained_binding_from_profile(profile: object, *, expected_domain: str | None = None) -> OwnedServiceBinding:
    if type(profile) is not OwnedPretrainedServiceProfile:
        raise OwnedServiceBlocked("OWNED_PRETRAINED_SERVICE_PROFILE_REQUIRED", status="UNAVAILABLE")
    request = profile.request
    validate_pretrained_inference_admission_request(request)
    if request.action != "admit" or request.prior_binding_sha256 is not None:
        raise OwnedServiceBlocked("OWNED_SERVICE_RESTART_ADMISSION_REQUIRED", status="BLOCKED")
    if expected_domain is not None and request.domain_id != expected_domain:
        raise OwnedServiceBlocked("OWNED_SERVICE_DOMAIN_MISMATCH", status="BLOCKED")
    if type(profile.source_dependency_paths) is not tuple:
        raise OwnedServiceBlocked("OWNED_SOURCE_VALIDATOR_REQUIRED", status="UNAVAILABLE")
    _module, _legacy_request_type, verifier_type = _security_contract()
    if (type(profile.admission_verifier) is not verifier_type
            or profile.admission_verifier.request != request):
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_VERIFIER_REQUIRED", status="UNAVAILABLE")
    if not callable(profile.source_validator):
        raise OwnedServiceBlocked("OWNED_SOURCE_VALIDATOR_REQUIRED", status="UNAVAILABLE")
    try:
        inference = importlib.import_module("lumenis.system.ai_gateway.owned_inference")
        runtime = inference.load_owned_pretrained_production_runtime(
            request, profile.artifact_root, admission=profile.admission_verifier,
            source_validator=profile.source_validator,
            source_dependency_paths=profile.source_dependency_paths,
        )
    except Exception as exc:
        from .owned_inference import OwnedInferenceBlocked

        if type(exc) is OwnedInferenceBlocked:
            status = "UNAVAILABLE" if exc.code in {
                "PRETRAINED_CPU_DEPENDENCIES_UNAVAILABLE",
                "PRETRAINED_CPU_BUILD_REQUIRED",
                "PRETRAINED_CPU_MEMORY_BUDGET_INSUFFICIENT",
                "PRETRAINED_CPU_MEMORY_OBSERVATION_UNAVAILABLE",
            } else "BLOCKED"
            raise OwnedServiceBlocked(exc.code, status=status) from exc
        raise OwnedServiceBlocked("OWNED_PRETRAINED_SERVICE_BIND_FAILED", status="ERROR") from exc
    binding = OwnedServiceBinding(
        admission_verifier=profile.admission_verifier,
        runtime=runtime,
        source_validator=profile.source_validator,
        source_dependency_paths=profile.source_dependency_paths,
    )
    valid_runtime = False
    try:
        runtime_type = _runtime_type_for_admission(request)
        if type(runtime) is not runtime_type:
            raise OwnedServiceBlocked("OWNED_PRODUCTION_RUNTIME_REQUIRED", status="UNAVAILABLE")
        valid_runtime = True
    finally:
        if not valid_runtime:
            _close_pretrained_runtime(binding)
    return binding


def bind_owned_pretrained_service(profile: object) -> dict:
    """Load and bind one exact admitted local CPU model through the Gateway."""
    binding = _pretrained_binding_from_profile(profile)
    bound = False
    try:
        result = bind_owned_service(binding)
        bound = True
        return result
    finally:
        if not bound:
            _close_pretrained_runtime(binding)


def restore_owned_pretrained_service_bindings(
    profile_resolver: Callable[[str], OwnedPretrainedServiceProfile | None],
) -> dict:
    """Restore exact admitted profiles through the CPU loader, with no job replay.

    The resolver reads existing model configuration, Permission and SourceUse
    owners. Missing profiles remain unconfigured; no config or approval is
    inferred from the public foundation manifest.
    """
    if not callable(profile_resolver):
        raise OwnedServiceBlocked("OWNED_PRETRAINED_PROFILE_RESOLVER_REQUIRED", status="INVALID_INPUT")

    def resolve(domain_id: str) -> OwnedServiceBinding | None:
        profile = profile_resolver(domain_id)
        if profile is None:
            return None
        return _pretrained_binding_from_profile(profile, expected_domain=domain_id)

    return restore_owned_service_bindings(resolve)


def restore_owned_service_bindings(binding_resolver: Callable[[str], OwnedServiceBinding | None]) -> dict:
    """Rebuild in-memory slots from freshly resolved, exactly admitted bindings.

    The resolver must read the existing canonical model/Permission/SourceUse
    owners and return a newly constructed binding. This routine stores no
    approval token, discovers/downloads no weights and replays no job. A restart
    restore accepts only an exact fresh `admit` request with no prior slot CAS.
    """
    if not callable(binding_resolver):
        raise OwnedServiceBlocked("OWNED_SERVICE_RECOVERY_RESOLVER_REQUIRED", status="INVALID_INPUT")
    results = {}
    for domain_id in ("cth", "bmp", "shared"):
        with _SLOTS_LOCK:
            existing = _SLOTS.get(domain_id)
        if existing is not None:
            checked = owned_service_status(domain_id)
            results[domain_id] = {
                "state": "ALREADY_BOUND" if checked.get("available") is True else "BLOCKED",
                "reason": checked.get("reason", "OWNED_SERVICE_STATUS_UNAVAILABLE"),
                "binding_sha256": existing.binding_sha256 if checked.get("available") is True else None,
            }
            continue
        binding = None
        try:
            binding = binding_resolver(domain_id)
            if binding is None:
                results[domain_id] = {"state": "NOT_CONFIGURED", "reason": "OWNED_SERVICE_BINDING_NOT_CONFIGURED"}
                continue
            if type(binding) is not OwnedServiceBinding:
                raise OwnedServiceBlocked("OWNED_SERVICE_BINDING_REQUIRED", status="INVALID_INPUT")
            _verifier, request = _verifier_request(binding, actions=frozenset({"admit"}))
            if request.domain_id != domain_id or request.prior_binding_sha256 is not None:
                raise OwnedServiceBlocked("OWNED_SERVICE_RESTART_ADMISSION_REQUIRED", status="BLOCKED")
            bound = bind_owned_service(binding)
            results[domain_id] = {
                "state": "RESTORED", "reason": "OWNED_SERVICE_ADMITTED",
                "binding_sha256": bound["binding_sha256"],
                "admission_request_sha256": bound["admission_request_sha256"],
            }
        except OwnedServiceBlocked as exc:
            if type(binding) is OwnedServiceBinding:
                _close_pretrained_runtime(binding)
            results[domain_id] = {"state": exc.status, "reason": exc.code}
        except Exception:
            if type(binding) is OwnedServiceBinding:
                _close_pretrained_runtime(binding)
            results[domain_id] = {"state": "UNAVAILABLE", "reason": "OWNED_SERVICE_RECOVERY_FAILED"}
    return {
        "provider": "owned", "domains": results,
        "automatic_replay": False, "generation_probe_performed": False,
        "fallback_allowed": False,
    }


def clear_owned_service(domain_id: str, expected_binding_sha256: str) -> dict:
    """Safety stop for one slot; never restarts, retries, or replays work."""
    if domain_id not in _DOMAINS or type(expected_binding_sha256) is not str or not _HASH.fullmatch(expected_binding_sha256):
        raise OwnedServiceBlocked("OWNED_SERVICE_CLEAR_REQUEST_INVALID", status="INVALID_INPUT")
    with _SLOTS_LOCK:
        current = _SLOTS.get(domain_id)
        if current is None or current.binding_sha256 != expected_binding_sha256:
            raise OwnedServiceBlocked("OWNED_SERVICE_BINDING_MISMATCH", status="BLOCKED")
        _SLOTS.pop(domain_id, None)
    cleanup = _close_pretrained_runtime(current.binding)
    return {"ok": True, "status": "CLEARED", "domain_id": domain_id,
            "binding_sha256": expected_binding_sha256, "runtime_unload_state": cleanup["state"],
            "automatic_replay": False}


def revoke_owned_service(admission_verifier: object) -> dict:
    """Apply a fresh canonical revoke decision to exactly the named active slot."""
    _module, request_type, verifier_type = _security_contract()
    if type(admission_verifier) is not verifier_type:
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_VERIFIER_REQUIRED", status="UNAVAILABLE")
    request = admission_verifier.request
    _validate_admission_request(request)
    if request.action != "revoke":
        raise OwnedServiceBlocked("OWNED_MODEL_ADMISSION_ACTION_INVALID")
    decision = _verify_admission(admission_verifier)
    with _SLOTS_LOCK:
        current = _SLOTS.get(request.domain_id)
        if current is None or current.binding_sha256 != request.prior_binding_sha256:
            raise OwnedServiceBlocked("OWNED_SERVICE_PRIOR_BINDING_MISMATCH")
        _SLOTS.pop(request.domain_id, None)
    cleanup = _close_pretrained_runtime(current.binding)
    return {
        "ok": True, "status": "REVOKED", "domain_id": request.domain_id,
        "binding_sha256": request.prior_binding_sha256,
        "admission_request_sha256": decision["request_sha256"],
        "audit_hashes": decision["audit_hashes"],
        "runtime_unload_state": cleanup["state"], "automatic_replay": False,
    }


def owned_service_status(domain_id: str | None = None) -> dict:
    """Read a scoped binding and recheck its gate; status alone never authorizes execution."""
    if domain_id is None:
        return {"provider": "owned", "available": False, "service_binding": "SCOPE_REQUIRED",
                "state": "UNAVAILABLE", "reason": "OWNED_SERVICE_DOMAIN_REQUIRED",
                "generation_probe_performed": False, "fallback_allowed": False}
    if domain_id not in _DOMAINS:
        return {"provider": "owned", "available": False, "service_binding": "BLOCKED",
                "state": "BLOCKED", "reason": "OWNED_SERVICE_DOMAIN_INVALID",
                "generation_probe_performed": False, "fallback_allowed": False}
    with _SLOTS_LOCK:
        slot = _SLOTS.get(domain_id)
    if slot is None:
        return {"provider": "owned", "available": False, "service_binding": "NOT_BOUND",
                "state": "UNAVAILABLE", "reason": "OWNED_SERVICE_EXECUTOR_NOT_BOUND",
                "domain_id": domain_id, "generation_probe_performed": False,
                "fallback_allowed": False}
    try:
        checked = _validate_binding(slot.binding, actions=frozenset({"admit", "rollback"}))
        if checked["binding_sha256"] != slot.binding_sha256:
            raise OwnedServiceBlocked("OWNED_SERVICE_BINDING_CHANGED")
        identity = checked["runtime_identity"]
        result = {
            "provider": "owned", "available": True, "service_binding": "BOUND",
            "state": "SERVICE_BOUND", "reason": "OWNED_SERVICE_ADMITTED",
            "domain_id": domain_id,
            "model_id": identity["model_id"],
            "model_revision": identity["model_revision"],
            "recipe": identity["recipe"],
            "context_window_tokens": identity["context_window_tokens"],
            "output_token_limit": identity["output_token_limit"],
            "binding_sha256": slot.binding_sha256,
            "admission_request_sha256": checked["admission_result"]["request_sha256"],
            "allowed_operations": list(slot.binding.admission_verifier.request.allowed_operations),
            "source_use_policy_version": slot.binding.admission_verifier.request.source_use_version,
            "source_use_policy_sha256": slot.binding.admission_verifier.request.source_use_sha256,
            "generation_probe_performed": False, "fallback_allowed": False,
        }
        if type(slot.binding.admission_verifier.request) is OwnedModelAdmissionRequest:
            result["artifact_kind"] = "TRAINED_CANDIDATE"
            result["candidate_identity_sha256"] = identity["candidate_identity_sha256"]
        else:
            result.update({
                "artifact_kind": "PRETRAINED_INFERENCE",
                "artifact_identity_sha256": identity["artifact_identity_sha256"],
                "device_kind": "cpu",
            })
        return result
    except OwnedServiceBlocked as exc:
        _retire_pretrained_slot(domain_id, slot)
        return {"provider": "owned", "available": False, "service_binding": "BLOCKED",
                "state": "BLOCKED", "reason": exc.code, "domain_id": domain_id,
                "generation_probe_performed": False, "fallback_allowed": False}
    except Exception:
        _retire_pretrained_slot(domain_id, slot)
        return {"provider": "owned", "available": False, "service_binding": "BLOCKED",
                "state": "BLOCKED", "reason": "OWNED_SERVICE_STATUS_FAILED", "domain_id": domain_id,
                "generation_probe_performed": False, "fallback_allowed": False}
