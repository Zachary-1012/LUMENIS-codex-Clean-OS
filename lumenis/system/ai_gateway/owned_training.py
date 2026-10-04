"""Local-only, approval-gated LoRA training owned by the SYSTEM AI Gateway."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
APPROVED_MANIFEST_PATH = REPO_ROOT / "config" / "ai-owned-foundation.json"
MODEL_ID = "openai/gpt-oss-20b"
MODEL_REVISION = "6cee5e81ee83917806bbde320786a8fb61efebee"
H100_RECIPE = "openai-h100-bf16"
T4_RECIPE = "unsloth-t4-nf4"
ADA_RECIPE = "unsloth-rtx4090-nf4"
BLACKWELL_RECIPE = "unsloth-rtx5090-nf4"
NF4_RECIPES = frozenset({T4_RECIPE, ADA_RECIPE, BLACKWELL_RECIPE})
NATIVE_BF16_NF4_RECIPES = frozenset({ADA_RECIPE, BLACKWELL_RECIPE})
T4_MODEL_ID = "unsloth/gpt-oss-20b-unsloth-bnb-4bit"
T4_MODEL_REVISION = "093fba6992ef5a7152481afec0bdfca1ac486998"
ADA_RECIPE_POLICY = {
    "foundation_variant": T4_RECIPE,
    "gpu_names": ["NVIDIA GeForce RTX 4090"],
    "compute_capability": [8, 9],
    "minimum_vram_bytes": 22 * 1024**3,
    "visible_device_count": 1,
    "compute_dtype": "bfloat16",
    "max_sequence_length": 4096,
    "gradient_accumulation_steps": 1,
    "quantization": "bitsandbytes_nf4",
    "status": "APPROVED_COMPATIBILITY_NOT_LIVE_VERIFIED",
}
BLACKWELL_RECIPE_POLICY = {
    "foundation_variant": T4_RECIPE,
    "gpu_names": ["NVIDIA GeForce RTX 5090"],
    "compute_capability": [12, 0],
    "minimum_vram_bytes": 30 * 1024**3,
    "visible_device_count": 1,
    "compute_dtype": "bfloat16",
    "cuda_runtime": "12.8",
    "required_cuda_arch": "sm_120",
    "max_sequence_length": 16384,
    "gradient_accumulation_steps": 1,
    "quantization": "bitsandbytes_nf4",
    "status": "APPROVED_COMPATIBILITY_NOT_LIVE_VERIFIED",
}
_MIN_CUDA_MEMORY = 75 * 1024**3
_MODEL_FILES = frozenset({
    "LICENSE", "USAGE_POLICY", "chat_template.jinja", "config.json",
    "model-00000-of-00002.safetensors", "model-00001-of-00002.safetensors",
    "model-00002-of-00002.safetensors", "model.safetensors.index.json",
    "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json",
})
_RECORD_FIELDS = frozenset({
    "case_id", "source_evidence_refs", "scope", "domain", "context",
    "permission_ref", "rights_ref", "review_status", "reviewer_approval_ref",
    "reviewer_approved_target", "training_eligible", "messages",
})
_SECRET_KEY = re.compile(r"(?:api[_-]?key|authorization|cookie|session|password|secret|private[_-]?key|access[_-]?token|refresh[_-]?token)", re.I)
_SECRET_VALUE = re.compile(
    r"(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{12,}|[-]{5}BEGIN [A-Z ]*PRIVATE KEY[-]{5}|\bBearer\s+\S+)", re.I)
_UNKNOWN = frozenset({"", "UNKNOWN", "UNVERIFIED", "NOT_AVAILABLE", "NOT_COLLECTED", "N/A", "NA", "NONE", "PENDING", "DENIED", "REJECTED", "REVOKED"})
_OFFLINE_ENV = {
    "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1", "WANDB_DISABLED": "true", "DO_NOT_TRACK": "1",
}


class TrainingBlocked(RuntimeError):
    """Training cannot proceed without the local safety gates."""


@dataclass(frozen=True)
class TrainingApprovalRequest:
    model_id: str
    model_revision: str
    train_sha256: str
    heldout_sha256: str
    scopes: tuple[str, ...]
    recipe: str = H100_RECIPE
    manifest_sha256: str = ""
    domain_id: str = ""


@dataclass(frozen=True)
class TrainingResumeRequest:
    """Exact checkpoint references; this value confers no execution authority."""
    operation_id: str
    checkpoint_ref: str
    expected_checkpoint_sha256: str
    replay_through_step: int


def _validate_resume_request(value):
    if (type(value) is not TrainingResumeRequest
            or type(value.operation_id) is not str
            or re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", value.operation_id) is None
            or type(value.checkpoint_ref) is not str
            or re.fullmatch(r"ART-[0-9a-f]{16}", value.checkpoint_ref) is None
            or type(value.expected_checkpoint_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", value.expected_checkpoint_sha256) is None
            or type(value.replay_through_step) is not int or value.replay_through_step < 0):
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")


def _local_path(value: str | os.PathLike[str], *, exists: bool = True) -> Path:
    raw = os.fspath(value)
    if not raw or "://" in raw or raw.startswith(("\\\\", "//")):
        raise ValueError("Only absolute local filesystem paths are accepted")
    path = Path(raw)
    if not path.is_absolute():
        raise ValueError("Only absolute local filesystem paths are accepted")
    resolved = path.resolve(strict=exists)
    if str(resolved).startswith(("\\\\", "//")):
        raise ValueError("Network paths are not accepted")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _overlaps(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _manifest(model_dir: Path, manifest_path: str | os.PathLike[str], recipe: str = H100_RECIPE) -> tuple[str, str]:
    supplied = _local_path(manifest_path)
    canonical = APPROVED_MANIFEST_PATH.resolve(strict=True)
    if Path(manifest_path).is_symlink() or supplied != canonical:
        raise TrainingBlocked("APPROVED_FOUNDATION_MANIFEST_REQUIRED")
    raw = supplied.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or any((
        data.get("schema_version") != 1, data.get("owner") != "SYSTEM AI Gateway",
        data.get("model_id") != MODEL_ID, data.get("revision") != MODEL_REVISION,
        data.get("license") != "Apache-2.0", data.get("capability") != "text",
        data.get("format") != "transformers_safetensors",
        data.get("status") != "APPROVED_FOUNDATION_NOT_TRAINED",
        data.get("source_url") != f"https://huggingface.co/{MODEL_ID}/tree/{MODEL_REVISION}",
        data.get("usage_policy_url") != f"https://huggingface.co/{MODEL_ID}/blob/{MODEL_REVISION}/USAGE_POLICY",
        data.get("fine_tune_reference") != "https://developers.openai.com/cookbook/articles/gpt-oss/fine-tune-transfomers",
        not isinstance(data.get("files"), dict) or set(data["files"]) != _MODEL_FILES,
    )):
        raise TrainingBlocked("APPROVED_FOUNDATION_MANIFEST_INVALID")
    if recipe in NF4_RECIPES:
        if recipe == ADA_RECIPE:
            policies = data.get("training_recipes")
            if not isinstance(policies, dict) or policies.get(ADA_RECIPE) != ADA_RECIPE_POLICY:
                raise TrainingBlocked("APPROVED_ADA_RECIPE_POLICY_REQUIRED")
        elif recipe == BLACKWELL_RECIPE:
            policies = data.get("training_recipes")
            if not isinstance(policies, dict) or policies.get(BLACKWELL_RECIPE) != BLACKWELL_RECIPE_POLICY:
                raise TrainingBlocked("APPROVED_BLACKWELL_RECIPE_POLICY_REQUIRED")
        variants = data.get("training_variants", {})
        if not isinstance(variants, dict) or not isinstance(variants.get(T4_RECIPE), dict):
            raise TrainingBlocked("APPROVED_T4_DERIVATIVE_MANIFEST_INVALID")
        data = variants[T4_RECIPE]
        expected_names = {
            "chat_template.json", "config.json", "generation_config.json",
            "model.safetensors.index.json", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json",
            *(f"model-{i:05d}-of-00004.safetensors" for i in range(1, 5)),
        }
        if any((
            data.get("model_id") != T4_MODEL_ID, data.get("revision") != T4_MODEL_REVISION,
            data.get("license") != "Apache-2.0", data.get("base_model") != MODEL_ID,
            data.get("base_revision_state") != "UPSTREAM_UNSPECIFIED",
            data.get("format") != "bitsandbytes_nf4",
            data.get("source_url") != f"https://huggingface.co/{T4_MODEL_ID}/tree/{T4_MODEL_REVISION}",
            not isinstance(data.get("files"), dict) or set(data["files"]) != expected_names,
        )):
            raise TrainingBlocked("APPROVED_T4_DERIVATIVE_MANIFEST_INVALID")
    elif recipe == H100_RECIPE:
        expected_names = _MODEL_FILES
    else:
        raise TrainingBlocked("UNKNOWN_TRAINING_RECIPE_NO_AUTOMATIC_FALLBACK")
    entries = list(model_dir.iterdir())
    if any(not item.is_file() for item in entries) or {item.name for item in entries} != expected_names:
        raise TrainingBlocked("LOCAL_MODEL_SNAPSHOT_FILE_SET_MISMATCH")
    for name, expected in data["files"].items():
        if Path(name).name != name or not isinstance(expected, dict) or set(expected) != {"size_bytes", "sha256"}:
            raise TrainingBlocked("APPROVED_FOUNDATION_MANIFEST_INVALID")
        file = model_dir / name
        resolved = file.resolve(strict=True)
        if str(resolved).startswith(("\\\\", "//")) or model_dir not in resolved.parents:
            raise TrainingBlocked("LOCAL_MODEL_SYMLINK_ESCAPES_SNAPSHOT")
        if not file.is_file():
            raise TrainingBlocked("LOCAL_MODEL_FILE_UNAVAILABLE")
        size = file.stat().st_size
        if type(expected.get("size_bytes")) is not int or expected["size_bytes"] != size:
            raise TrainingBlocked("LOCAL_MODEL_FILE_HASH_MISMATCH")
        if not re.fullmatch(r"[0-9a-f]{64}", str(expected.get("sha256", ""))) or _sha256(file) != expected["sha256"]:
            raise TrainingBlocked("LOCAL_MODEL_FILE_HASH_MISMATCH")
    return hashlib.sha256(raw).hexdigest(), data["revision"]


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value.strip().upper() in _UNKNOWN:
        raise ValueError(f"Invalid or unknown {field}")
    return value.strip()


def _has_secret(value: object) -> bool:
    if isinstance(value, dict):
        return any(_SECRET_KEY.search(str(key)) or _has_secret(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_secret(item) for item in value)
    return isinstance(value, str) and bool(_SECRET_VALUE.search(value))


def _validate_record(record: object) -> tuple[dict, str]:
    if not isinstance(record, dict) or set(record) != _RECORD_FIELDS or _has_secret(record):
        raise ValueError("Record schema or secret scan failed")
    _text(record["case_id"], "case_id")
    for field in ("scope", "domain", "context", "permission_ref", "rights_ref", "reviewer_approval_ref", "reviewer_approved_target"):
        _text(record[field], field)
    domain_id = record["domain"].strip().lower()
    if domain_id == "zbmp":
        domain_id = "bmp"
    if domain_id not in {"cth", "bmp"}:
        raise ValueError("Training records must identify the canonical CTH or BMP domain")
    refs = record["source_evidence_refs"]
    if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref.strip() or ref.strip().upper() in _UNKNOWN for ref in refs):
        raise ValueError("Source Evidence references must be explicit")
    if record["training_eligible"] is not True or str(record["review_status"]).upper() not in {"APPROVED", "REVIEWER_APPROVED"}:
        raise ValueError("Only reviewer-approved eligible records can be trained")
    messages = record["messages"]
    if not isinstance(messages, list) or len(messages) < 2:
        raise ValueError("At least one user message and one final answer are required")
    users, assistants = [], []
    canonical = []
    for message in messages:
        if not isinstance(message, dict) or set(message) - {"role", "content", "channel"}:
            raise ValueError("Messages may contain only user input and final answer text")
        role = message.get("role")
        content = _text(message.get("content"), "message content")
        if role == "user" and "channel" not in message:
            users.append(content)
            canonical.append({"role": "user", "content": content})
        elif role == "assistant" and message.get("channel", "final") == "final":
            assistants.append(content)
            canonical.append({"role": "assistant", "content": content, "channel": "final"})
        else:
            raise ValueError("Only user messages and one final assistant answer are allowed")
    if not users or len(assistants) != 1 or messages[-1].get("role") != "assistant" or assistants[0] != record["reviewer_approved_target"].strip():
        raise ValueError("The sole final answer must match its reviewer-approved target")
    prompt = " ".join(unicodedata.normalize("NFKC", " ".join(users)).casefold().split())
    return {"case_id": record["case_id"], "scope": record["scope"].strip(), "domain_id": domain_id, "messages": canonical}, prompt


def _read_jsonl(path: Path) -> tuple[list[tuple[dict, str]], str]:
    if path.suffix.lower() != ".jsonl" or not path.is_file():
        raise ValueError("Training inputs must be local JSONL files")
    records = []
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for line_number, line in enumerate(stream, 1):
            digest.update(line)
            if line.strip():
                try:
                    records.append(_validate_record(json.loads(line.decode("utf-8"))))
                except (json.JSONDecodeError, ValueError) as exc:
                    raise ValueError(f"Invalid approved dataset record at line {line_number}") from exc
    if not records:
        raise ValueError("Training and held-out datasets must both be non-empty")
    return records, digest.hexdigest()


def _output_path(value: str | os.PathLike[str], protected: list[Path]) -> Path:
    raw = os.fspath(value)
    if not raw or "://" in raw or raw.startswith(("\\\\", "//")) or not Path(raw).is_absolute():
        raise ValueError("The output must be an absolute local path")
    requested = Path(raw)
    if os.path.lexists(raw) or not requested.name:
        raise ValueError("The output directory must be new and must not be a symlink")
    parent = requested.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("The output parent must already exist")
    candidate = parent / requested.name
    if any(_overlaps(candidate, path.resolve(strict=False)) for path in protected):
        raise ValueError("The output overlaps protected model, input, manifest, repository, or database paths")
    return candidate


@contextmanager
def _offline_hf(recipe: str = H100_RECIPE):
    environment = dict(_OFFLINE_ENV)
    if recipe == T4_RECIPE:
        environment.update(UNSLOTH_FORCE_FLOAT32="1", UNSLOTH_DISABLE_STATISTICS="1")
    elif recipe in NATIVE_BF16_NF4_RECIPES:
        environment.update(UNSLOTH_FORCE_FLOAT32="0", UNSLOTH_DISABLE_STATISTICS="1")
    previous = {key: os.environ.get(key) for key in environment}
    os.environ.update(environment)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _require_cuda(recipe: str = H100_RECIPE) -> tuple[object, str, int]:
    try:
        import torch
    except ImportError as exc:
        raise TrainingBlocked("CUDA_TRAINING_DEPENDENCIES_UNAVAILABLE") from exc
    if not torch.cuda.is_available() or not torch.cuda.device_count():
        raise TrainingBlocked("CUDA_REQUIRED_NO_CPU_FALLBACK")
    device = torch.cuda.get_device_properties(0)
    if recipe == T4_RECIPE:
        if (device.major, device.minor) != (7, 5) or int(device.total_memory) < 14 * 1024**3:
            raise TrainingBlocked("T4_NF4_RECIPE_REQUIRES_VERIFIED_SM75_AND_MEMORY")
    elif recipe == ADA_RECIPE:
        if ((device.major, device.minor) != (8, 9)
                or str(device.name) not in ADA_RECIPE_POLICY["gpu_names"]
                or int(device.total_memory) < ADA_RECIPE_POLICY["minimum_vram_bytes"]
                or torch.cuda.device_count() != ADA_RECIPE_POLICY["visible_device_count"]
                or not torch.cuda.is_bf16_supported()):
            raise TrainingBlocked("ADA_NF4_RECIPE_REQUIRES_VERIFIED_RTX4090_SM89_MEMORY_AND_BF16")
    elif recipe == BLACKWELL_RECIPE:
        count = torch.cuda.device_count()
        if ((device.major, device.minor) != (12, 0)
                or str(device.name) not in BLACKWELL_RECIPE_POLICY["gpu_names"]
                or int(device.total_memory) < BLACKWELL_RECIPE_POLICY["minimum_vram_bytes"]
                or type(count) is not int or count != 1
                or torch.cuda.is_bf16_supported(including_emulation=False) is not True):
            raise TrainingBlocked("BLACKWELL_NF4_RECIPE_REQUIRES_VERIFIED_RTX5090_SM120_MEMORY_AND_NATIVE_BF16")
        if (getattr(torch.version, "cuda", None) != BLACKWELL_RECIPE_POLICY["cuda_runtime"]
                or BLACKWELL_RECIPE_POLICY["required_cuda_arch"] not in torch.cuda.get_arch_list()):
            raise TrainingBlocked("BLACKWELL_NF4_RECIPE_REQUIRES_CUDA128_AND_COMPILED_SM120")
    elif recipe != H100_RECIPE:
        raise TrainingBlocked("UNKNOWN_TRAINING_RECIPE_NO_AUTOMATIC_FALLBACK")
    elif int(device.total_memory) < _MIN_CUDA_MEMORY or not torch.cuda.is_bf16_supported():
        raise TrainingBlocked("CUDA_MEMORY_OR_BFLOAT16_BELOW_H100_RECIPE_GATE")
    return torch, str(device.name), int(device.total_memory)


def recipe_sequence_length(recipe: str) -> int:
    """Return the audited recipe limit; never silently fall back to another GPU."""
    if recipe == T4_RECIPE:
        return 1024
    if recipe == ADA_RECIPE:
        return ADA_RECIPE_POLICY["max_sequence_length"]
    if recipe == BLACKWELL_RECIPE:
        return BLACKWELL_RECIPE_POLICY["max_sequence_length"]
    if recipe == H100_RECIPE:
        return 2048
    raise TrainingBlocked("UNKNOWN_TRAINING_RECIPE_NO_AUTOMATIC_FALLBACK")


def recipe_gradient_accumulation_steps(recipe: str) -> int:
    if recipe == ADA_RECIPE:
        return ADA_RECIPE_POLICY["gradient_accumulation_steps"]
    if recipe == BLACKWELL_RECIPE:
        return BLACKWELL_RECIPE_POLICY["gradient_accumulation_steps"]
    if recipe in {T4_RECIPE, H100_RECIPE}:
        return 4
    raise TrainingBlocked("UNKNOWN_TRAINING_RECIPE_NO_AUTOMATIC_FALLBACK")


def _verify_approval(verifier: Callable[[TrainingApprovalRequest], bool] | None, request: TrainingApprovalRequest) -> None:
    if not callable(verifier):
        raise TrainingBlocked("TRAINING_APPROVAL_REQUIRED")
    try:
        approved = verifier(request)
    except Exception as exc:
        raise TrainingBlocked("TRAINING_APPROVAL_VERIFIER_FAILED") from exc
    if approved is not True:
        raise TrainingBlocked("TRAINING_APPROVAL_REQUIRED")


def _verify_training_boundary(verifier, phase_client, request, phase) -> None:
    from .owned_training_phases import TrainingPhaseClient

    _verify_approval(verifier, request)
    if type(phase_client) is not TrainingPhaseClient:
        raise TrainingBlocked("TRAINING_PHASE_TRANSPORT_NOT_BOUND")
    phase_client.authorize(request, phase)
    # Metadata receipt is no model permit. Retain a live original MODEL_TRAIN
    # check after transport/signature verification, immediately before action.
    _verify_approval(verifier, request)
    phase_client.require_current_receipt()


def run_owned_lora_training(
    model_snapshot_dir: str | os.PathLike[str], train_jsonl_path: str | os.PathLike[str],
    heldout_jsonl_path: str | os.PathLike[str], output_dir: str | os.PathLike[str], *,
    manifest_path: str | os.PathLike[str], execute: bool = False,
    approval_verifier: Callable[[TrainingApprovalRequest], bool] | None = None,
    recipe: str = H100_RECIPE,
    phase_client=None,
    checkpoint_adapter=None,
    resume_request: TrainingResumeRequest | None = None,
    recovery_phase_transport=None,
    stop_after_checkpoint_step: int | None = None,
) -> dict[str, object]:
    """Validate explicit local inputs; train only after Learning approval and CUDA gates."""
    if type(execute) is not bool:
        raise ValueError("execute must be an explicit boolean")
    if resume_request is not None:
        _validate_resume_request(resume_request)
        if phase_client is not None or not callable(recovery_phase_transport):
            raise TrainingBlocked("CHECKPOINT_CONTRACT_NOT_BOUND")
    elif recovery_phase_transport is not None:
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    if stop_after_checkpoint_step is not None and (
            type(stop_after_checkpoint_step) is not int or stop_after_checkpoint_step < 1):
        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    if Path(model_snapshot_dir).is_symlink():
        raise TrainingBlocked("LOCAL_MODEL_SYMLINK_ESCAPES_SNAPSHOT")
    model_dir = _local_path(model_snapshot_dir)
    if not model_dir.is_dir():
        raise ValueError("A local model snapshot directory is required")
    if Path(train_jsonl_path).is_symlink() or Path(heldout_jsonl_path).is_symlink():
        raise TrainingBlocked("LOCAL_DATASET_SYMLINK_NOT_ALLOWED")
    train_path, heldout_path = _local_path(train_jsonl_path), _local_path(heldout_jsonl_path)
    manifest_file = _local_path(manifest_path)
    checkpoint_policy = None
    base_recipe = recipe
    if type(recipe) is str and any(recipe.startswith(base + "+checkpoint-v1:") for base in NF4_RECIPES):
        from .owned_training_checkpoints import load_recovery_policy
        checkpoint_policy = load_recovery_policy(recipe, manifest_file)
        base_recipe = checkpoint_policy.document["base_recipe"]
    elif checkpoint_adapter is not None or resume_request is not None or stop_after_checkpoint_step is not None:
        raise TrainingBlocked("CHECKPOINT_RECIPE_NOT_AUTHORIZED")
    manifest_hash, revision = _manifest(model_dir, manifest_file, base_recipe)
    model_id = T4_MODEL_ID if base_recipe in NF4_RECIPES else MODEL_ID
    train, train_hash = _read_jsonl(train_path)
    heldout, heldout_hash = _read_jsonl(heldout_path)
    case_ids, prompts = set(), set()
    for record, prompt in train + heldout:
        if record["case_id"] in case_ids or prompt in prompts:
            raise ValueError("Training and held-out inputs overlap by case_id or normalized prompt")
        case_ids.add(record["case_id"])
        prompts.add(prompt)
    domains = {record["domain_id"] for record, _ in train + heldout}
    if len(domains) != 1:
        raise TrainingBlocked("MIXED_DOMAIN_TRAINING_REQUIRES_EXPLICIT_CROSS_DOMAIN_CONTRACT")
    domain_id = next(iter(domains))
    db_value = os.environ.get("ZBC_DB_PATH", str(REPO_ROOT / "data" / "monitor.db"))
    db_path = Path(db_value) if Path(db_value).is_absolute() else Path.cwd() / db_value
    output = _output_path(output_dir, [model_dir, train_path, heldout_path, manifest_file, REPO_ROOT, db_path])
    scopes = tuple(sorted({record["scope"] for record, _ in train + heldout}))
    result: dict[str, object] = {
        "status": "VALIDATED_LOCAL_INPUTS_NOT_PRODUCTION_ACCEPTANCE",
        "execution_state": "PREFLIGHT_ONLY", "candidate_status": "NOT_EVALUATED",
        "permission_evidence_state": "LOCAL_ATTESTATIONS_ONLY_NOT_VERIFIED",
        "model_id": model_id, "model_revision": revision, "training_recipe": recipe,
        "base_training_recipe": base_recipe,
        "base_revision_state": "UPSTREAM_UNSPECIFIED" if base_recipe in NF4_RECIPES else "EXACT_PINNED",
        "manifest_sha256": manifest_hash, "train_sha256": train_hash,
        "heldout_sha256": heldout_hash, "train_case_count": len(train),
        "heldout_case_count": len(heldout), "scopes": list(scopes),
        "domain_id": domain_id,
    }
    if checkpoint_policy is not None:
        result["checkpoint_policy_sha256"] = checkpoint_policy.sha256
        accumulation = recipe_gradient_accumulation_steps(base_recipe)
        total_steps = (len(train) + accumulation - 1) // accumulation
        if stop_after_checkpoint_step is not None and (
                stop_after_checkpoint_step >= total_steps
                or stop_after_checkpoint_step % checkpoint_policy.document["checkpoint_interval_steps"]):
            raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
    if not execute:
        return result
    request = TrainingApprovalRequest(model_id, revision, train_hash, heldout_hash, scopes, recipe, manifest_hash, domain_id)
    if checkpoint_policy is not None:
        from .owned_training_checkpoints import TrainingCheckpointAdapter
        if type(checkpoint_adapter) is not TrainingCheckpointAdapter:
            raise TrainingBlocked("CHECKPOINT_CONTRACT_NOT_BOUND")
        if checkpoint_adapter.policy != checkpoint_policy:
            raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
        checkpoint_adapter.bind_request(request, approval_verifier)
    if resume_request is None:
        _verify_training_boundary(approval_verifier, phase_client, request, "initial")
    else:
        # v1.3 allows preparation under the original current MODEL_TRAIN check.
        # Physical load and resumed training still require the separate owner
        # admission and sealed recovery handoff; never replay the old initial.
        _verify_approval(approval_verifier, request)
    torch, device_name, memory_bytes = _require_cuda(base_recipe) if base_recipe in NF4_RECIPES else _require_cuda()
    with _offline_hf(base_recipe):
        try:
            low_memory = base_recipe in NF4_RECIPES
            if low_memory:
                from importlib.metadata import version
                pins = {"unsloth": "2026.9.12", "unsloth_zoo": "2026.9.8", "transformers": "4.56.2", "trl": "0.22.2",
                        "torch": "2.11.0+cu128", "bitsandbytes": "0.50.2", "tokenizers": "0.22.2", "triton": "3.6.0"}
                installed = {name: version(name) for name in pins}
                if installed != pins:
                    raise TrainingBlocked("T4_TRAINING_STACK_VERSION_MISMATCH")
                result["training_packages"] = installed
                from unsloth import FastLanguageModel
                model, tokenizer = FastLanguageModel.from_pretrained(
                    model_name=str(model_dir), max_seq_length=recipe_sequence_length(base_recipe),
                    dtype=torch.bfloat16 if base_recipe in NATIVE_BF16_NF4_RECIPES else None,
                    load_in_4bit=True, full_finetuning=False, local_files_only=True,
                    trust_remote_code=False, token=False,
                )
                if Path(str(getattr(model.config, "_name_or_path", ""))).resolve() != model_dir:
                    raise TrainingBlocked("T4_LOADER_CHANGED_PINNED_MODEL_PATH")
                quantization = getattr(model.config, "quantization_config", {})
                if not isinstance(quantization, dict) or quantization.get("bnb_4bit_quant_type") != "nf4":
                    raise TrainingBlocked("T4_LOADER_QUANTIZATION_MISMATCH")
            from datasets import Dataset
            from peft import LoraConfig, get_peft_model
            from transformers import AutoModelForCausalLM, AutoTokenizer, Mxfp4Config, TrainerCallback
            from trl import SFTConfig, SFTTrainer
            if not low_memory:
                tokenizer = AutoTokenizer.from_pretrained(str(model_dir), revision=revision, local_files_only=True, trust_remote_code=False)
            max_length = recipe_sequence_length(base_recipe)
            rows = []
            for record, _ in train:
                text = tokenizer.apply_chat_template(record["messages"], tokenize=False)
                if len(tokenizer(text, add_special_tokens=False, truncation=False)["input_ids"]) > max_length:
                    raise TrainingBlocked("TRAINING_EXAMPLE_EXCEEDS_MAX_LENGTH")
                rows.append({"text": text})
            dataset = Dataset.from_list(rows)
            if low_memory:
                model = FastLanguageModel.get_peft_model(
                    model, r=8, lora_alpha=16, lora_dropout=0, bias="none",
                    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
                    use_gradient_checkpointing="unsloth", random_state=3407,
                )
            else:
                model = AutoModelForCausalLM.from_pretrained(
                    str(model_dir), revision=revision, local_files_only=True, trust_remote_code=False,
                    attn_implementation="eager", torch_dtype=torch.bfloat16,
                    quantization_config=Mxfp4Config(dequantize=True), use_cache=False, device_map="auto", use_safetensors=True,
                )
                config = LoraConfig(
                    r=8, lora_alpha=16, target_modules="all-linear",
                    target_parameters=[f"{layer}.mlp.experts.{projection}" for layer in (7, 15, 23) for projection in ("gate_up_proj", "down_proj")],
                )
                model = get_peft_model(model, config)

            active_phase_client = phase_client
            interrupted_at_checkpoint = False

            class ApprovalCallback(TrainerCallback):
                def on_step_begin(self, args, state, control, **kwargs):
                    nonlocal active_phase_client
                    if resume_request is not None and active_phase_client is None:
                        # Pinned Trainer restores RNG before its first step_begin.
                        # The adapter must already have committed the measured
                        # load; this admits before_train once, then this step.
                        active_phase_client = checkpoint_adapter.recovered_phase_client(
                            transport=recovery_phase_transport)
                    _verify_training_boundary(approval_verifier, active_phase_client, request, "step_begin")
                    return control

                def on_substep_end(self, args, state, control, **kwargs):
                    _verify_training_boundary(approval_verifier, active_phase_client, request, "substep_end")
                    return control

                def on_pre_optimizer_step(self, args, state, control, **kwargs):
                    _verify_training_boundary(approval_verifier, active_phase_client, request, "pre_optimizer_step")
                    return control

                def on_step_end(self, args, state, control, **kwargs):
                    if checkpoint_adapter is not None:
                        return checkpoint_adapter.complete_optimizer_step(trainer, control)
                    return control

                def on_save(self, args, state, control, **kwargs):
                    nonlocal interrupted_at_checkpoint
                    if stop_after_checkpoint_step is not None and state.global_step == stop_after_checkpoint_step:
                        committed = checkpoint_adapter.last_committed_checkpoint
                        if committed is None or committed["completed_step"] != state.global_step:
                            raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
                        interrupted_at_checkpoint = True
                        control.should_training_stop = True
                    return control

            checkpoint_settings = {}
            if checkpoint_policy is not None:
                checkpoint_settings = {
                    "save_steps": checkpoint_policy.document["checkpoint_interval_steps"],
                    "save_total_limit": None, "save_only_model": False,
                    "restore_callback_states_from_checkpoint": True, "ignore_data_skip": False,
                    "dataloader_num_workers": 0, "dataloader_drop_last": False,
                    "remove_unused_columns": False, "packing": False, "seed": 3407, "data_seed": 3407,
                }

            args = SFTConfig(
                learning_rate=2e-4, gradient_checkpointing=True, num_train_epochs=1,
                logging_steps=1, per_device_train_batch_size=1 if low_memory else 4,
                gradient_accumulation_steps=recipe_gradient_accumulation_steps(base_recipe),
                max_length=max_length, warmup_ratio=0.03, lr_scheduler_type="cosine_with_min_lr",
                lr_scheduler_kwargs={"min_lr_rate": 0.1}, output_dir=str(output),
                report_to="none", push_to_hub=False,
                save_strategy="steps" if checkpoint_policy is not None else "no", bf16=base_recipe != T4_RECIPE,
                fp16=False, optim="adamw_8bit" if low_memory else "adamw_torch",
                **checkpoint_settings,
            )
            if resume_request is None:
                _verify_training_boundary(approval_verifier, active_phase_client, request, "before_output_dir")
            else:
                _verify_approval(approval_verifier, request)
            output.mkdir(exist_ok=False)
            result.update({"execution_state": "TRAINING_IN_PROGRESS", "cuda_device": device_name, "cuda_memory_bytes": memory_bytes})
            _write_status(output, result)
            try:
                trainer_class = SFTTrainer if checkpoint_adapter is None else checkpoint_adapter.trainer_type(SFTTrainer)
                trainer = trainer_class(model=model, args=args, train_dataset=dataset, processing_class=tokenizer,
                                        callbacks=[ApprovalCallback()])
                resume_path, previous_steps = None, 0
                if resume_request is None:
                    _verify_training_boundary(approval_verifier, active_phase_client, request, "before_train")
                else:
                    resume_path = checkpoint_adapter.prepare_load(
                        operation_id=resume_request.operation_id, checkpoint_ref=resume_request.checkpoint_ref,
                        expected_checkpoint_sha256=resume_request.expected_checkpoint_sha256,
                        replay_through_step=resume_request.replay_through_step)
                    if _overlaps(output, resume_path):
                        raise TrainingBlocked("CHECKPOINT_SCOPE_MISMATCH")
                    previous_steps = checkpoint_adapter.resume_completed_step
                    if stop_after_checkpoint_step is not None and stop_after_checkpoint_step <= previous_steps:
                        raise TrainingBlocked("CHECKPOINT_REQUEST_INVALID")
                if base_recipe in NATIVE_BF16_NF4_RECIPES:
                    torch.cuda.synchronize(0)
                    torch.cuda.reset_peak_memory_stats(0)
                started = time.monotonic()
                train_result = trainer.train() if resume_path is None else trainer.train(resume_from_checkpoint=str(resume_path))
                if base_recipe in NATIVE_BF16_NF4_RECIPES:
                    torch.cuda.synchronize(0)
                    allocated = torch.cuda.max_memory_allocated(0)
                    reserved = torch.cuda.max_memory_reserved(0)
                    if (type(allocated) is not int or type(reserved) is not int
                            or not 0 < allocated <= reserved <= memory_bytes):
                        raise TrainingBlocked("CUDA_TRAINING_MEMORY_MEASUREMENT_INVALID")
                    result.update({"training_peak_allocated_bytes": allocated,
                                   "training_peak_reserved_bytes": reserved})
                completed_steps = getattr(train_result, "global_step", None)
                if type(completed_steps) is not int or completed_steps <= previous_steps:
                    raise TrainingBlocked("TRAINING_COMPLETED_WITHOUT_OPTIMIZER_STEPS")
                if low_memory and not math.isfinite(float(getattr(train_result, "metrics", {}).get("train_loss", float("nan")))):
                    raise TrainingBlocked("TRAINING_LOSS_UNAVAILABLE_OR_NONFINITE")
                result.update({"optimizer_steps": completed_steps, "optimizer_steps_this_attempt": completed_steps - previous_steps,
                    "resume_completed_step": previous_steps, "training_wall_seconds": time.monotonic() - started,
                    "reported_train_loss": getattr(train_result, "metrics", {}).get("train_loss"),
                    "checkpoint": checkpoint_adapter.last_committed_checkpoint if checkpoint_adapter is not None else None})
                result["training_loss_history"] = [
                    {"optimizer_step": row["step"], "loss": float(row["loss"])}
                    for row in getattr(getattr(trainer, "state", None), "log_history", [])
                    if type(row) is dict and type(row.get("step")) is int
                    and type(row.get("loss")) in {int, float} and math.isfinite(row["loss"])
                ]
                if interrupted_at_checkpoint:
                    result["execution_state"] = "CHECKPOINT_SAVED_TRAINING_INTERRUPTED"
                    result["worker_stop_state"] = "OWNER_STOP_AND_REAP_REQUIRED"
                    _write_status(output, result)
                    return result
                if resume_request is not None and active_phase_client is None:
                    raise TrainingBlocked("CHECKPOINT_NOT_COMMITTED")
                _verify_training_boundary(approval_verifier, active_phase_client, request, "before_adapter_save")
                trainer.save_model(str(output))
                _verify_training_boundary(approval_verifier, active_phase_client, request, "before_tokenizer_save")
                tokenizer.save_pretrained(str(output))
                for artifact in ("adapter_config.json", "adapter_model.safetensors"):
                    path = output / artifact
                    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
                        raise TrainingBlocked("TRAINED_ADAPTER_ARTIFACT_MISSING_OR_EMPTY")
                _verify_training_boundary(approval_verifier, active_phase_client, request, "after_saved_artifact_check")
                result["adapter_sha256"] = _sha256(output / "adapter_model.safetensors")
                result["adapter_config_sha256"] = _sha256(output / "adapter_config.json")
            except TrainingBlocked as exc:
                result["execution_state"] = str(exc)
                _write_status(output, result)
                raise
            except Exception:
                result["execution_state"] = "TRAINING_FAILED"
                _write_status(output, result)
                raise
            result["execution_state"] = "TRAINED_NOT_EVALUATED"
            _write_status(output, result)
            return result
        except ImportError as exc:
            raise TrainingBlocked("LOCAL_TRAINING_DEPENDENCIES_UNAVAILABLE") from exc


def _write_status(output: Path, result: dict[str, object]) -> None:
    (output / "training_status.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
